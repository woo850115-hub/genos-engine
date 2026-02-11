"""GenOS Engine — main game loop, boot sequence, command dispatcher."""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml

from core.ansi import colorize
from core.db import Database
from core.korean import has_batchim, particle, render_message
from core.net import TelnetConnection, TelnetServer
from core.reload import ReloadManager
from core.session import Session
from core.world import Room, World

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Direction constants ──────────────────────────────────────────

DIRS = ["north", "east", "south", "west", "up", "down"]
DIR_NAMES_KR = ["북", "동", "남", "서", "위", "아래"]
DIR_ABBREV = {"n": 0, "e": 1, "s": 2, "w": 3, "u": 4, "d": 5}
DIR_NAMES_KR_MAP = {
    "북": 0, "북쪽": 0, "동": 1, "동쪽": 1, "남": 2, "남쪽": 2,
    "서": 3, "서쪽": 3, "위": 4, "위쪽": 4, "아래": 5, "아래쪽": 5,
}
REVERSE_DIRS = [2, 3, 0, 1, 5, 4]  # north↔south, east↔west, up↔down

# ── Korean Choseong (초성) abbreviation table ────────────────────

CHOSEONG_MAP: dict[str, str] = {
    "ㄱ": "공격", "ㄴ": "누구", "ㄷ": "도움", "ㄹ": "look",
    "ㅁ": "말", "ㅂ": "봐", "ㅅ": "소지품", "ㅈ": "저장",
    "ㅊ": "착용", "ㅎ": "help",
}

# ── Korean verb → English action mapping (from korean_commands.lua) ──

KOREAN_VERB_MAP: dict[str, str] = {
    "가": "go", "가져": "get", "건강": "score", "공격": "attack",
    "구원": "rescue", "구해": "rescue", "귓": "tell", "그만": "quit",
    "꺼내": "equipment", "날씨": "weather", "넣": "put", "놔": "drop",
    "누가": "who", "누구": "who", "닫": "close", "도움": "help",
    "들": "hold", "따라가": "follow", "떠나": "flee", "마시": "drink",
    "말": "say", "말하": "say", "먹": "eat", "무리": "group",
    "배우": "practice", "버려": "drop", "벗": "remove", "별칭": "alias",
    "보": "look", "봐": "look", "빼": "drop", "사": "buy",
    "서": "stand", "속삭이": "whisper", "쉬": "rest", "습득": "get",
    "시간": "time", "시전": "cast", "싸우": "attack", "앉": "sit",
    "열": "open", "외치": "shout", "일어나": "stand", "입": "wear",
    "자": "sleep", "잠가": "lock", "잠그": "lock", "저장": "save",
    "정보": "score", "주": "give", "주머니": "inventory", "주문": "cast",
    "주워": "get", "죽": "kill", "죽이": "kill", "줘": "give",
    "집": "get", "착용": "wear", "찾": "search", "챙기": "wield",
    "팔": "sell", "풀": "unlock", "피하": "flee", "학습": "practice",
    # Extra common aliases
    "나가": "quit", "나가기": "quit", "소지품": "inventory", "장비": "equipment",
    "출구": "exits", "명령어": "commands", "점수": "score",
}

# Korean verb stem endings to strip for matching
_VERB_ENDINGS = ["해줘", "해라", "하다", "하자", "하지", "해", "어", "아", "기"]


def _extract_korean_stem(word: str) -> str | None:
    """Try to extract verb stem by removing endings."""
    for ending in _VERB_ENDINGS:
        if word.endswith(ending) and len(word) > len(ending):
            return word[: -len(ending)]
    return None


def _resolve_korean_verb(token: str) -> str | None:
    """Resolve a Korean token to an English command name."""
    # Direct match
    eng = KOREAN_VERB_MAP.get(token)
    if eng:
        return eng
    # Stem extraction
    stem = _extract_korean_stem(token)
    if stem:
        eng = KOREAN_VERB_MAP.get(stem)
        if eng:
            return eng
    return None


# ── GamePlugin Protocol ──────────────────────────────────────────

@runtime_checkable
class GamePlugin(Protocol):
    name: str

    def register_commands(self, engine: Engine) -> None: ...


# ── Engine ───────────────────────────────────────────────────────

class Engine:
    """Main game engine — owns world, DB, network, game loop."""

    def __init__(self, config_path: str | Path) -> None:
        with open(config_path, encoding="utf-8") as f:
            self.config: dict[str, Any] = yaml.safe_load(f)

        self.game_name: str = self.config["game"]
        self.db = Database(self.config["database"])
        self.world = World()
        self.reload_mgr = ReloadManager()

        self.sessions: dict[int, Session] = {}   # conn_id → Session
        self.players: dict[str, Session] = {}     # lowercase name → Session

        # Command registry: command_name → handler coroutine
        self.cmd_handlers: dict[str, Any] = {}
        self.cmd_korean: dict[str, str] = {}  # korean_cmd → english_cmd

        self._telnet: TelnetServer | None = None
        self._running = False
        self._tick = 0
        self._last_save = 0.0
        self._plugin: Any = None
        self._watcher_task: asyncio.Task | None = None

    # ── Boot sequence ────────────────────────────────────────────

    async def boot(self) -> None:
        log.info("=== GenOS Engine booting: %s ===", self.config.get("name", self.game_name))

        # 1. Connect to DB
        await self.db.connect()

        # 2. Auto-init DB
        data_dir = BASE_DIR / "data" / self.game_name
        await self.db.auto_init(data_dir)
        await self.db.ensure_players_table()

        # 3. Load world
        await self.world.load_from_db(self.db, data_dir)

        # 4. Load game plugin
        mod = importlib.import_module(f"games.{self.game_name}.game")
        self._plugin = mod.create_plugin()
        log.info("Game plugin loaded: %s", self._plugin.name)

        # 5. Register commands
        self._register_core_commands()
        self._plugin.register_commands(self)

        # 6. Load Korean verb mapping into cmd_korean
        self._load_korean_mappings()

        # 7. Initial zone resets
        self._do_zone_resets(initial=True)

        # 8. Start network
        net_cfg = self.config.get("network", {})
        self._telnet = TelnetServer(
            host=net_cfg.get("telnet_host", "0.0.0.0"),
            port=net_cfg.get("telnet_port", 4000),
            on_connect=self._on_new_connection,
        )
        await self._telnet.start()

        # 9. Start file watcher (dev mode)
        if self.config.get("dev", {}).get("hot_reload", False):
            from core.watcher import start_watcher
            games_dir = BASE_DIR / "games"
            self._watcher_task = await start_watcher(games_dir, self.reload_mgr)

        self._running = True
        self._last_save = time.monotonic()
        log.info("=== Boot complete: %d cmds, %d korean mappings ===",
                 len(self.cmd_handlers), len(self.cmd_korean))

    def _load_korean_mappings(self) -> None:
        """Load Korean → English command mappings from KOREAN_VERB_MAP."""
        for kr_verb, eng_cmd in KOREAN_VERB_MAP.items():
            if eng_cmd in self.cmd_handlers and kr_verb not in self.cmd_korean:
                self.cmd_korean[kr_verb] = eng_cmd

    async def shutdown(self) -> None:
        log.info("Shutting down...")
        self._running = False

        # Notify players
        for session in list(self.sessions.values()):
            await session.send_line("\r\n{red}서버가 종료됩니다. 안녕히 가세요.{reset}")
            await session.save_character()

        # Stop watcher
        if self._watcher_task:
            self._watcher_task.cancel()

        # Stop network
        if self._telnet:
            await self._telnet.stop()

        # Close DB
        await self.db.close()
        log.info("Shutdown complete")

    # ── Game loop ────────────────────────────────────────────────

    async def run_loop(self) -> None:
        """Main game loop — 10Hz tick."""
        tick_interval = 1.0 / self.config.get("engine", {}).get("tick_rate", 10)
        save_interval = self.config.get("engine", {}).get("save_interval", 300)

        while self._running:
            tick_start = time.monotonic()
            self._tick += 1

            # Apply hot reloads at tick boundary
            reloaded = self.reload_mgr.apply_pending()
            if reloaded:
                if any(r.startswith(f"games.{self.game_name}") for r in reloaded):
                    self._plugin.register_commands(self)

            # Combat rounds (configurable: 20 ticks=2sec for tbaMUD, 10 ticks=1sec for 10woongi)
            combat_interval = self.config.get("engine", {}).get("combat_round", 20)
            if self._tick % combat_interval == 0:
                await self._combat_round()

            # Affect ticks (every 75 seconds ≈ 1 "MUD hour" at 10Hz)
            if self._tick % 750 == 0:
                await self._tick_affects()

            # Zone resets (every zone.lifespan minutes)
            if self._tick % 600 == 0:  # every minute at 10Hz
                self._do_zone_resets()

            # Auto-save
            now = time.monotonic()
            if now - self._last_save >= save_interval:
                await self._auto_save()
                self._last_save = now

            # Sleep until next tick
            elapsed = time.monotonic() - tick_start
            sleep_time = tick_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    async def _auto_save(self) -> None:
        count = 0
        for session in list(self.sessions.values()):
            if session.character:
                await session.save_character()
                count += 1
        if count:
            log.info("Auto-saved %d players", count)

    # ── Combat round ─────────────────────────────────────────────

    async def _combat_round(self) -> None:
        """Process one combat round for all fighting characters."""
        # Plugin can override entire combat round
        plugin = getattr(self, "_plugin", None)
        if plugin and hasattr(plugin, "combat_round"):
            await plugin.combat_round(self)
            return

        from games.tbamud.combat.thac0 import perform_attack, extra_attacks
        from games.tbamud.combat.death import handle_death
        from games.tbamud.level import check_level_up, do_level_up

        # Collect all fighting pairs
        processed: set[int] = set()
        for room in self.world.rooms.values():
            for char in list(room.characters):
                if char.id in processed or not char.fighting:
                    continue
                if char.position < self.POS_FIGHTING:
                    char.fighting = None
                    continue
                if char.fighting.hp <= 0:
                    char.fighting = None
                    continue

                processed.add(char.id)
                char.position = self.POS_FIGHTING
                target = char.fighting

                # Number of attacks this round
                n_attacks = 1 + extra_attacks(char)
                for _ in range(n_attacks):
                    if target.hp <= 0:
                        break
                    await perform_attack(
                        char, target,
                        send_to_char=self._send_to_char,
                    )

                # Check death
                if target.hp <= 0:
                    char.fighting = None
                    char.position = self.POS_STANDING
                    await handle_death(self, target, killer=char)
                    # Check level up
                    if not char.is_npc and check_level_up(char):
                        send_fn = char.session.send_line if char.session else None
                        await do_level_up(char, send_fn=send_fn)

    async def _send_to_char(self, char, message: str) -> None:
        """Send message to a character if they have a session."""
        if char.session:
            await char.session.send_line(message)

    async def _tick_affects(self) -> None:
        """Tick down affects for all characters."""
        # Plugin can override affect ticking
        plugin = getattr(self, "_plugin", None)
        if plugin and hasattr(plugin, "tick_affects"):
            await plugin.tick_affects(self)
            return

        from games.tbamud.combat.spells import tick_affects

        for room in self.world.rooms.values():
            for char in list(room.characters):
                if char.affects:
                    messages = tick_affects(char)
                    if char.session:
                        for msg in messages:
                            await char.session.send_line(msg)

    # ── Network callbacks ────────────────────────────────────────

    async def _on_new_connection(self, conn: TelnetConnection) -> None:
        session = Session(conn, self)
        await session.run()

    # ── Command system ───────────────────────────────────────────

    def register_command(self, name: str, handler: Any, korean: str | None = None) -> None:
        """Register a command handler."""
        self.cmd_handlers[name] = handler
        if korean:
            self.cmd_korean[korean] = name

    async def process_command(self, session: Session, text: str) -> None:
        """Parse and execute a command.

        Strategy:
        1. Expand aliases (1 level, max 20 expansions)
        2. Try choseong abbreviation (single char ㄱ~ㅎ)
        3. Try last token as command (Korean SOV: "고블린 공격")
        4. Try first token as command (English SVO: "attack goblin")
        5. Korean verb resolution (stem extraction)
        6. Prefix matching (exactly 1 match)
        7. Social commands (from DB)
        """
        if not text:
            return

        # 1. Alias expansion
        text = self._expand_alias(session, text)

        parts = text.split()
        if not parts:
            return

        # 2. Choseong abbreviation (single character input)
        if len(parts) == 1 and parts[0] in CHOSEONG_MAP:
            mapped = CHOSEONG_MAP[parts[0]]
            # Re-resolve the mapped command
            eng = self.cmd_korean.get(mapped) or mapped
            handler = self.cmd_handlers.get(eng)
            if handler:
                await handler(session, "")
                return

        # 3. Try last token first (Korean SOV: "고블린 공격")
        cmd_name, args_str, handler = self._resolve_command(parts, sov=True)
        if handler is self._DIRECTION_SENTINEL:
            await self.do_move(session, cmd_name)
            return

        # 4. If SOV failed, try first token (SVO: "attack goblin")
        if handler is None:
            cmd_name, args_str, handler = self._resolve_command(parts, sov=False)
            if handler is self._DIRECTION_SENTINEL:
                await self.do_move(session, cmd_name)
                return

        # 5. Korean verb resolution with stem extraction
        if handler is None:
            for try_sov in (True, False):
                token = parts[-1] if try_sov else parts[0]
                eng = _resolve_korean_verb(token)
                if eng:
                    handler = self.cmd_handlers.get(eng)
                    if handler:
                        cmd_name = eng
                        args_str = " ".join(parts[:-1]) if try_sov else " ".join(parts[1:])
                        break

        # 6. Prefix matching
        if handler is None:
            for try_token in (parts[-1].lower(), parts[0].lower()):
                matches = [k for k in self.cmd_handlers if k.startswith(try_token)]
                if len(matches) == 1:
                    handler = self.cmd_handlers[matches[0]]
                    cmd_name = matches[0]
                    idx = -1 if try_token == parts[-1].lower() else 0
                    args_str = " ".join(parts[:-1]) if idx == -1 else " ".join(parts[1:])
                    break
                elif len(matches) > 1:
                    await session.send_line(f"어떤 명령어를 의미하시나요? {', '.join(sorted(matches)[:5])}")
                    return

        # 7. Social commands
        if handler is None:
            token = parts[-1].lower() if len(parts) >= 1 else ""
            if token in self.world.socials:
                await self._do_social(session, token, " ".join(parts[:-1]))
                return
            token = parts[0].lower()
            if token in self.world.socials:
                await self._do_social(session, token, " ".join(parts[1:]))
                return

        if handler is None:
            await session.send_line("무슨 말인지 모르겠습니다.")
            return

        await handler(session, args_str)

    def _resolve_command(self, parts: list[str], sov: bool) -> tuple[str, str, Any]:
        """Try to resolve a command from parts. Returns (cmd_name, args_str, handler)."""
        if sov:
            token = parts[-1].lower()
            args_str = " ".join(parts[:-1]) if len(parts) > 1 else ""
        else:
            token = parts[0].lower()
            args_str = " ".join(parts[1:])

        # Direction check
        if token in DIR_ABBREV or token in DIRS or token in DIR_NAMES_KR_MAP:
            return token, args_str, self._DIRECTION_SENTINEL

        # Korean → English mapping
        eng = self.cmd_korean.get(token)
        if eng:
            handler = self.cmd_handlers.get(eng)
            if handler:
                return eng, args_str, handler

        # Direct handler lookup
        handler = self.cmd_handlers.get(token)
        if handler:
            return token, args_str, handler

        return token, args_str, None

    # Sentinel object for direction commands (bound methods can't use `is`)
    _DIRECTION_SENTINEL = object()

    def _expand_alias(self, session: Session, text: str) -> str:
        """Expand player aliases (1 level, max 20 commands)."""
        if not session.player_data:
            return text
        aliases = session.player_data.get("aliases", {})
        if isinstance(aliases, str):
            import json
            try:
                aliases = json.loads(aliases)
            except (json.JSONDecodeError, TypeError):
                return text
        if not aliases:
            return text
        parts = text.split(None, 1)
        if not parts:
            return text
        cmd = parts[0]
        if cmd in aliases:
            expansion = aliases[cmd]
            if isinstance(expansion, list):
                # Multi-command alias — return first, queue rest
                return expansion[0] if expansion else text
            return str(expansion)
        return text

    # ── Core commands (always available) ─────────────────────────

    def _register_core_commands(self) -> None:
        self.register_command("look", self.do_look, korean="봐")
        self.register_command("l", self.do_look)
        self.register_command("north", lambda s, a: self.do_move(s, "north"))
        self.register_command("south", lambda s, a: self.do_move(s, "south"))
        self.register_command("east", lambda s, a: self.do_move(s, "east"))
        self.register_command("west", lambda s, a: self.do_move(s, "west"))
        self.register_command("up", lambda s, a: self.do_move(s, "up"))
        self.register_command("down", lambda s, a: self.do_move(s, "down"))
        self.register_command("quit", self.do_quit, korean="나가기")
        self.register_command("save", self.do_save, korean="저장")
        self.register_command("who", self.do_who, korean="누구")
        self.register_command("score", self.do_score, korean="점수")
        self.register_command("say", self.do_say, korean="말")
        self.register_command("inventory", self.do_inventory, korean="소지품")
        self.register_command("i", self.do_inventory)
        self.register_command("help", self.do_help, korean="도움")
        self.register_command("exits", self.do_exits, korean="출구")
        self.register_command("commands", self.do_commands, korean="명령어")
        self.register_command("alias", self.do_alias, korean="별칭")
        self.register_command("open", self.do_open, korean="열")
        self.register_command("close", self.do_close, korean="닫")
        self.register_command("lock", self.do_lock, korean="잠가")
        self.register_command("unlock", self.do_unlock, korean="풀")
        self.register_command("kill", self.do_kill, korean="죽이")
        self.register_command("attack", self.do_kill, korean="공격")
        self.register_command("flee", self.do_flee, korean="떠나")
        self.register_command("rest", self.do_rest, korean="쉬")
        self.register_command("stand", self.do_stand, korean="서")
        self.register_command("sit", self.do_sit, korean="앉")
        self.register_command("sleep", self.do_sleep, korean="자")
        self.register_command("wake", self.do_stand)
        self.register_command("cast", self.do_cast, korean="시전")
        self.register_command("practice", self.do_practice, korean="연습")

    async def do_look(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        room = self.world.get_room(char.room_vnum)
        if not room:
            await session.send_line("허공에 떠 있습니다...")
            return

        if args:
            # Look at something specific
            await self._look_at(session, room, args.strip().lower())
            return

        # Room name
        await session.send_line(f"\r\n{{cyan}}{room.proto.name}{{reset}}")
        # Description
        if room.proto.description:
            await session.send_line(f"   {room.proto.description.rstrip()}")

        # Exits
        exit_names = []
        for ex in room.proto.exits:
            if ex.direction < 6:
                dir_name = DIR_NAMES_KR[ex.direction]
                if room.is_door_closed(ex.direction):
                    dir_name = f"({dir_name})"
                exit_names.append(dir_name)
        if exit_names:
            await session.send_line(f"{{green}}[ 출구: {' '.join(exit_names)} ]{{reset}}")

        # Objects in room
        for obj in room.objects:
            await session.send_line(f"{{yellow}}{obj.proto.long_description.rstrip()}{{reset}}")

        # Characters in room
        for mob in room.characters:
            if mob is char:
                continue
            if mob.is_npc:
                await session.send_line(f"{{bright_cyan}}{mob.proto.long_description.rstrip()}{{reset}}")
            else:
                await session.send_line(f"{mob.name}이(가) 서 있습니다.")

    async def _look_at(self, session: Session, room: Room, target: str) -> None:
        """Look at a specific object, mob, or extra desc."""
        char = session.character
        if not char:
            return

        # Check extra descs
        for ed in room.proto.extra_descs:
            if target in ed.keywords.lower():
                await session.send_line(ed.description)
                return

        # Check mobs
        for mob in room.characters:
            if mob is char:
                continue
            if target in mob.proto.keywords.lower():
                if mob.proto.detailed_description:
                    await session.send_line(mob.proto.detailed_description.rstrip())
                else:
                    await session.send_line(f"{mob.name}을(를) 바라봅니다.")
                # Show equipment
                if mob.equipment:
                    await session.send_line("착용 중인 장비:")
                    for pos in sorted(mob.equipment.keys()):
                        obj = mob.equipment[pos]
                        await session.send_line(f"  {obj.name}")
                return

        # Check objects in room
        for obj in room.objects:
            if target in obj.proto.keywords.lower():
                await session.send_line(obj.proto.short_description)
                for ed in obj.proto.extra_descs:
                    if target in ed.keywords.lower():
                        await session.send_line(ed.description)
                        return
                return

        # Check inventory
        for obj in char.inventory:
            if target in obj.proto.keywords.lower():
                await session.send_line(obj.proto.short_description)
                return

        await session.send_line("그런 것을 볼 수 없습니다.")

    async def do_move(self, session: Session, direction: str) -> None:
        char = session.character
        if not char:
            return

        # Resolve direction to index
        dir_idx: int | None = None
        if direction in DIR_ABBREV:
            dir_idx = DIR_ABBREV[direction]
        elif direction in DIRS:
            dir_idx = DIRS.index(direction)
        elif direction in DIR_NAMES_KR_MAP:
            dir_idx = DIR_NAMES_KR_MAP[direction]
        else:
            try:
                dir_idx = int(direction)
            except ValueError:
                pass

        if dir_idx is None or dir_idx < 0 or dir_idx > 5:
            await session.send_line("그쪽으로는 갈 수 없습니다.")
            return

        room = self.world.get_room(char.room_vnum)
        if not room:
            return

        # Find exit
        exit_found = None
        for ex in room.proto.exits:
            if ex.direction == dir_idx:
                exit_found = ex
                break

        if not exit_found or exit_found.to_room < 0:
            await session.send_line("그쪽으로는 갈 수 없습니다.")
            return

        dest = self.world.get_room(exit_found.to_room)
        if not dest:
            await session.send_line("그쪽으로는 갈 수 없습니다.")
            return

        # Check door
        if room.has_door(dir_idx):
            if room.is_door_closed(dir_idx):
                await session.send_line("문이 닫혀있습니다.")
                return

        # Leave message
        leave_dir = DIR_NAMES_KR[dir_idx] if dir_idx < 6 else "어딘가"
        for other in room.characters:
            if other is char:
                continue
            if other.session:
                await other.session.send_line(f"\r\n{char.name}이(가) {leave_dir}쪽으로 떠났습니다.")

        # Move
        self.world.char_to_room(char, exit_found.to_room)

        # Arrive message
        arrive_dir = DIR_NAMES_KR[REVERSE_DIRS[dir_idx]] if dir_idx < 6 else "어딘가"
        for other in dest.characters:
            if other is char:
                continue
            if other.session:
                await other.session.send_line(f"\r\n{char.name}이(가) {arrive_dir}쪽에서 왔습니다.")

        # Show room
        await self.do_look(session, "")

    # ── Door commands ────────────────────────────────────────────

    def _find_door_direction(self, room: Room, target: str) -> int | None:
        """Find door direction from keyword or direction name."""
        if target in DIR_ABBREV:
            return DIR_ABBREV[target]
        if target in DIR_NAMES_KR_MAP:
            return DIR_NAMES_KR_MAP[target]
        if target in DIRS:
            return DIRS.index(target)
        # Try matching exit keywords
        for ex in room.proto.exits:
            if ex.keywords and target in ex.keywords.lower():
                return ex.direction
        return None

    async def do_open(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        room = self.world.get_room(char.room_vnum)
        if not room:
            return
        if not args:
            await session.send_line("무엇을 여시겠습니까?")
            return

        direction = self._find_door_direction(room, args.strip().lower())
        if direction is None or not room.has_door(direction):
            await session.send_line("그런 것을 찾을 수 없습니다.")
            return

        if not room.is_door_closed(direction):
            await session.send_line("이미 열려 있습니다.")
            return
        if room.is_door_locked(direction):
            await session.send_line("잠겨 있습니다.")
            return

        room.door_states[direction]["closed"] = False
        await session.send_line("문을 열었습니다.")

        # Open the other side too
        for ex in room.proto.exits:
            if ex.direction == direction:
                other_room = self.world.get_room(ex.to_room)
                if other_room:
                    rev_dir = REVERSE_DIRS[direction]
                    if other_room.has_door(rev_dir):
                        other_room.door_states[rev_dir]["closed"] = False
                    for other in other_room.characters:
                        if other.session:
                            await other.session.send_line("\r\n문이 열렸습니다.")
                break

    async def do_close(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        room = self.world.get_room(char.room_vnum)
        if not room:
            return
        if not args:
            await session.send_line("무엇을 닫으시겠습니까?")
            return

        direction = self._find_door_direction(room, args.strip().lower())
        if direction is None or not room.has_door(direction):
            await session.send_line("그런 것을 찾을 수 없습니다.")
            return

        if room.is_door_closed(direction):
            await session.send_line("이미 닫혀 있습니다.")
            return

        room.door_states[direction]["closed"] = True
        await session.send_line("문을 닫았습니다.")

        for ex in room.proto.exits:
            if ex.direction == direction:
                other_room = self.world.get_room(ex.to_room)
                if other_room:
                    rev_dir = REVERSE_DIRS[direction]
                    if other_room.has_door(rev_dir):
                        other_room.door_states[rev_dir]["closed"] = True
                break

    async def do_lock(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        room = self.world.get_room(char.room_vnum)
        if not room:
            return
        if not args:
            await session.send_line("무엇을 잠그시겠습니까?")
            return

        direction = self._find_door_direction(room, args.strip().lower())
        if direction is None or not room.has_door(direction):
            await session.send_line("그런 것을 찾을 수 없습니다.")
            return

        if not room.is_door_closed(direction):
            await session.send_line("먼저 닫아야 합니다.")
            return
        if room.is_door_locked(direction):
            await session.send_line("이미 잠겨 있습니다.")
            return

        # Check for key
        key_vnum = -1
        for ex in room.proto.exits:
            if ex.direction == direction:
                key_vnum = ex.key_vnum
                break
        if key_vnum > 0:
            has_key = any(o.proto.vnum == key_vnum for o in char.inventory)
            if not has_key:
                has_key = any(o.proto.vnum == key_vnum for o in char.equipment.values())
            if not has_key:
                await session.send_line("열쇠가 없습니다.")
                return

        room.door_states[direction]["locked"] = True
        await session.send_line("문을 잠갔습니다.")

    async def do_unlock(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        room = self.world.get_room(char.room_vnum)
        if not room:
            return
        if not args:
            await session.send_line("무엇을 여시겠습니까?")
            return

        direction = self._find_door_direction(room, args.strip().lower())
        if direction is None or not room.has_door(direction):
            await session.send_line("그런 것을 찾을 수 없습니다.")
            return

        if not room.is_door_locked(direction):
            await session.send_line("잠겨 있지 않습니다.")
            return

        key_vnum = -1
        for ex in room.proto.exits:
            if ex.direction == direction:
                key_vnum = ex.key_vnum
                break
        if key_vnum > 0:
            has_key = any(o.proto.vnum == key_vnum for o in char.inventory)
            if not has_key:
                has_key = any(o.proto.vnum == key_vnum for o in char.equipment.values())
            if not has_key:
                await session.send_line("열쇠가 없습니다.")
                return

        room.door_states[direction]["locked"] = False
        await session.send_line("자물쇠를 열었습니다.")

    # ── Position commands ────────────────────────────────────────

    # Position constants
    POS_DEAD = 0
    POS_MORTALLYW = 1
    POS_INCAP = 2
    POS_STUNNED = 3
    POS_SLEEPING = 4
    POS_RESTING = 5
    POS_SITTING = 6
    POS_FIGHTING = 7
    POS_STANDING = 8

    async def do_rest(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        if char.position == self.POS_RESTING:
            await session.send_line("이미 쉬고 있습니다.")
            return
        if char.fighting:
            await session.send_line("전투 중에는 쉴 수 없습니다!")
            return
        char.position = self.POS_RESTING
        await session.send_line("쉬기 시작합니다.")

    async def do_sit(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        if char.position == self.POS_SITTING:
            await session.send_line("이미 앉아 있습니다.")
            return
        if char.fighting:
            await session.send_line("전투 중에는 앉을 수 없습니다!")
            return
        char.position = self.POS_SITTING
        await session.send_line("앉았습니다.")

    async def do_stand(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        if char.position == self.POS_STANDING:
            await session.send_line("이미 서 있습니다.")
            return
        char.position = self.POS_STANDING
        await session.send_line("일어섰습니다.")

    async def do_sleep(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        if char.position == self.POS_SLEEPING:
            await session.send_line("이미 잠들어 있습니다.")
            return
        if char.fighting:
            await session.send_line("전투 중에는 잠들 수 없습니다!")
            return
        char.position = self.POS_SLEEPING
        await session.send_line("잠들기 시작합니다.")

    # ── Combat stubs ─────────────────────────────────────────────

    async def do_kill(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        if not args:
            await session.send_line("누구를 공격하시겠습니까?")
            return
        room = self.world.get_room(char.room_vnum)
        if not room:
            return
        target_kw = args.strip().lower()
        for mob in room.characters:
            if mob is char:
                continue
            if mob.is_npc and target_kw in mob.proto.keywords.lower():
                await session.send_line(f"{{red}}{mob.name}을(를) 공격합니다!{{reset}}")
                char.fighting = mob
                mob.fighting = char
                return
        await session.send_line("그런 대상을 찾을 수 없습니다.")

    async def do_flee(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        if not char.fighting:
            await session.send_line("전투 중이 아닙니다.")
            return
        # Try random direction
        import random
        room = self.world.get_room(char.room_vnum)
        if room and room.proto.exits:
            ex = random.choice(room.proto.exits)
            if ex.to_room >= 0 and not room.is_door_closed(ex.direction):
                char.fighting.fighting = None
                char.fighting = None
                await session.send_line("{yellow}도망칩니다!{reset}")
                await self.do_move(session, DIRS[ex.direction] if ex.direction < 6 else "north")
                return
        await session.send_line("도망칠 곳이 없습니다!")

    async def do_cast(self, session: Session, args: str) -> None:
        """Cast a spell: cast <spell> [target]."""
        from games.tbamud.combat.spells import (
            find_spell, can_cast, cast_spell, SPELL_WORD_OF_RECALL,
        )
        from games.tbamud.combat.death import handle_death
        from games.tbamud.level import check_level_up, do_level_up

        char = session.character
        if not char:
            return
        if char.position < self.POS_STANDING and char.position != self.POS_FIGHTING:
            await session.send_line("일어서야 합니다.")
            return

        if not args:
            await session.send_line("어떤 주문을 시전하시겠습니까?")
            return

        parts = args.split(None, 1)
        spell_name = parts[0]
        target_name = parts[1].strip() if len(parts) > 1 else ""

        spell = find_spell(spell_name)
        if not spell:
            await session.send_line("그런 주문은 모릅니다.")
            return

        ok, msg = can_cast(char, spell.id)
        if not ok:
            await session.send_line(msg)
            return

        # Find target
        room = self.world.get_room(char.room_vnum)
        target = None

        if spell.target_type in ("self", "utility"):
            target = char
        elif spell.target_type == "defensive" and not target_name:
            target = char
        elif target_name:
            if room:
                for mob in room.characters:
                    kw = target_name.lower()
                    if mob is not char and kw in mob.proto.keywords.lower():
                        target = mob
                        break
                    if mob is not char and mob.player_name and kw in mob.player_name.lower():
                        target = mob
                        break
            if target is None and spell.target_type == "defensive":
                target = char
        elif spell.target_type == "offensive":
            target = char.fighting

        if target is None:
            await session.send_line("대상을 찾을 수 없습니다.")
            return

        # Word of Recall special
        if spell.id == SPELL_WORD_OF_RECALL:
            char.mana -= spell.mana_cost
            start_room = self.config.get("world", {}).get("start_room", 3001)
            if room and char in room.characters:
                room.characters.remove(char)
            char.room_vnum = start_room
            dest = self.world.get_room(start_room)
            if dest:
                dest.characters.append(char)
            char.fighting = None
            await session.send_line("{bright_white}몸이 가벼워지며 순간이동합니다!{reset}")
            await self.do_look(session, "")
            return

        # Start combat if offensive
        if spell.target_type == "offensive" and target is not char:
            if not char.fighting:
                char.fighting = target
                char.position = self.POS_FIGHTING
            if not target.fighting:
                target.fighting = char
                target.position = self.POS_FIGHTING

        damage = await cast_spell(
            char, spell.id, target,
            send_to_char=self._send_to_char,
        )

        # Check death
        if target.hp <= 0 and target is not char:
            char.fighting = None
            char.position = self.POS_STANDING
            await handle_death(self, target, killer=char)
            if not char.is_npc and check_level_up(char):
                await do_level_up(char, send_fn=session.send_line)

    async def do_practice(self, session: Session, args: str) -> None:
        """Show or improve skills/spells."""
        from games.tbamud.combat.spells import SPELLS

        char = session.character
        if not char:
            return

        await session.send_line("{bright_cyan}-- 시전 가능한 주문 --{reset}")
        for spell in sorted(SPELLS.values(), key=lambda s: s.id):
            min_lv = spell.min_level.get(char.class_id, 34)
            if min_lv <= char.level:
                prof = char.skills.get(spell.id, 0)
                await session.send_line(
                    f"  {spell.korean_name:<12s} ({spell.name:<20s}) 숙련도: {prof}%"
                )

    # ── Info commands ────────────────────────────────────────────

    async def do_quit(self, session: Session, args: str) -> None:
        if session.character and session.character.fighting:
            await session.send_line("전투 중에는 나갈 수 없습니다!")
            return
        await session.save_character()
        await session.send_line("저장되었습니다. 안녕히 가세요!")
        session._closed = True
        await session.conn.close()

    async def do_save(self, session: Session, args: str) -> None:
        await session.save_character()
        await session.send_line("저장되었습니다.")

    async def do_who(self, session: Session, args: str) -> None:
        await session.send_line("{cyan}━━━━━━ 현재 접속 중인 플레이어 ━━━━━━{reset}")
        for name, s in self.players.items():
            if s.character:
                c = s.character
                cls_id = s.player_data.get("class_id", 0)
                cls = self.world.classes.get(cls_id)
                cls_name = cls.name if cls else "모험가"
                lvl = s.player_data.get("level", 1)
                title = s.player_data.get("title", "")
                line = f"  [{lvl:3d} {cls_name:6s}] {c.name}"
                if title:
                    line += f" {title}"
                await session.send_line(line)
        await session.send_line(f"{{cyan}}━━━━━━ 총 {len(self.players)}명 접속 중 ━━━━━━{{reset}}")

    async def do_score(self, session: Session, args: str) -> None:
        from games.tbamud.level import CLASS_NAMES, exp_to_next
        c = session.character
        if not c:
            return
        cls_name = CLASS_NAMES.get(c.class_id, "모험가")

        lines = [
            f"{{cyan}}━━━━━━ {c.name}의 정보 ━━━━━━{{reset}}",
            f"  레벨: {c.level}  직업: {cls_name}  성별: {['중성','남성','여성'][session.player_data.get('sex',0)]}",
            f"  HP: {{green}}{c.hp}/{c.max_hp}{{reset}}  "
            f"마나: {{blue}}{c.mana}/{c.max_mana}{{reset}}  "
            f"이동력: {c.move}/{c.max_move}",
            f"  힘: {c.str}  민첩: {c.dex}  체력: {c.con}  "
            f"지능: {c.intel}  지혜: {c.wis}  매력: {c.cha}",
            f"  골드: {{yellow}}{c.gold}{{reset}}  경험치: {c.experience}",
            f"  다음 레벨까지: {exp_to_next(c)}",
            f"  히트롤: {c.hitroll}  댐롤: {c.damroll}  AC: {c.proto.armor_class if c.is_npc else 100}",
            f"{{cyan}}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{{reset}}",
        ]
        await session.send_line("\r\n".join(lines))

    async def do_say(self, session: Session, args: str) -> None:
        if not args:
            await session.send_line("무엇이라고 말하시겠습니까?")
            return
        char = session.character
        if not char:
            return
        await session.send_line(f"{{green}}당신이 말합니다, '{args}'{{reset}}")
        room = self.world.get_room(char.room_vnum)
        if room:
            for other in room.characters:
                if other is not char and other.session:
                    await other.session.send_line(
                        f"\r\n{{green}}{char.name}이(가) 말합니다, '{args}'{{reset}}"
                    )

    async def do_inventory(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        if not char.inventory:
            await session.send_line("아무것도 들고 있지 않습니다.")
            return
        await session.send_line("소지품:")
        for obj in char.inventory:
            await session.send_line(f"  {obj.name}")

    async def do_help(self, session: Session, args: str) -> None:
        keyword = args.strip().lower() if args else "help"

        # Exact match first
        for entry in self.world.help_entries:
            keywords = entry.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            for kw in keywords:
                if kw.lower() == keyword:
                    await session.send_line(entry.get("text", "도움말이 없습니다."))
                    return

        # Partial match
        matches = []
        for entry in self.world.help_entries:
            keywords = entry.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            for kw in keywords:
                if keyword in kw.lower():
                    matches.append(entry)
                    break
        if len(matches) == 1:
            await session.send_line(matches[0].get("text", "도움말이 없습니다."))
        elif len(matches) > 1:
            kw_list = []
            for m in matches[:10]:
                kws = m.get("keywords", [])
                if isinstance(kws, str):
                    kws = [kws]
                kw_list.append(kws[0] if kws else "?")
            await session.send_line(f"여러 도움말이 발견되었습니다: {', '.join(kw_list)}")
        else:
            await session.send_line(f"'{keyword}'에 대한 도움말이 없습니다.")

    async def do_exits(self, session: Session, args: str) -> None:
        char = session.character
        if not char:
            return
        room = self.world.get_room(char.room_vnum)
        if not room:
            return
        if not room.proto.exits:
            await session.send_line("출구가 없습니다!")
            return
        await session.send_line("사용 가능한 출구:")
        for ex in room.proto.exits:
            if ex.direction >= 6:
                continue
            dir_name = DIR_NAMES_KR[ex.direction]
            dest = self.world.get_room(ex.to_room)
            dest_name = dest.name if dest else "알 수 없음"
            status = ""
            if room.has_door(ex.direction):
                if room.is_door_closed(ex.direction):
                    status = " (닫힘)"
                else:
                    status = " (열림)"
            await session.send_line(f"  {dir_name:4s} - {dest_name}{status}")

    async def do_commands(self, session: Session, args: str) -> None:
        cmds = sorted(self.cmd_handlers.keys())
        await session.send_line("사용 가능한 명령어:")
        line = "  "
        for cmd in cmds:
            if len(line) + len(cmd) + 2 > 78:
                await session.send_line(line)
                line = "  "
            line += cmd + "  "
        if line.strip():
            await session.send_line(line)
        # Show Korean mappings count
        await session.send_line(f"\r\n한국어 매핑: {len(self.cmd_korean)}개")

    async def do_alias(self, session: Session, args: str) -> None:
        """Set or show aliases."""
        if not args:
            aliases = session.player_data.get("aliases", {})
            if isinstance(aliases, str):
                import json
                try:
                    aliases = json.loads(aliases)
                except (json.JSONDecodeError, TypeError):
                    aliases = {}
            if not aliases:
                await session.send_line("설정된 별칭이 없습니다.")
                return
            await session.send_line("설정된 별칭:")
            for k, v in aliases.items():
                await session.send_line(f"  {k} = {v}")
            return

        parts = args.split(None, 1)
        if len(parts) < 2:
            await session.send_line("사용법: alias <이름> <명령어>")
            return

        alias_name, alias_cmd = parts
        aliases = session.player_data.get("aliases", {})
        if isinstance(aliases, str):
            import json
            try:
                aliases = json.loads(aliases)
            except (json.JSONDecodeError, TypeError):
                aliases = {}
        if len(aliases) >= 20:
            await session.send_line("별칭은 최대 20개까지 설정할 수 있습니다.")
            return
        aliases[alias_name] = alias_cmd
        session.player_data["aliases"] = aliases
        await session.send_line(f"별칭 설정: {alias_name} = {alias_cmd}")

    # ── Social commands ──────────────────────────────────────────

    async def _do_social(self, session: Session, social_name: str, args: str) -> None:
        """Execute a social command from the socials DB table."""
        char = session.character
        if not char:
            return
        social = self.world.socials.get(social_name)
        if not social:
            return

        room = self.world.get_room(char.room_vnum)
        if not room:
            return

        target_name = args.strip() if args else ""

        if not target_name:
            # No target
            msg_char = social.get("no_arg_to_char", "")
            msg_room = social.get("no_arg_to_room", "")
            if msg_char:
                await session.send_line(msg_char.replace("$n", char.name))
            if msg_room:
                formatted = msg_room.replace("$n", char.name)
                for other in room.characters:
                    if other is not char and other.session:
                        await other.session.send_line(f"\r\n{formatted}")
            return

        # Find target
        target_mob = None
        for mob in room.characters:
            if mob is char:
                continue
            kw = mob.player_name.lower() if mob.player_name else mob.proto.keywords.lower()
            if target_name.lower() in kw:
                target_mob = mob
                break

        if target_mob is None:
            not_found = social.get("not_found", "그런 사람을 찾을 수 없습니다.")
            await session.send_line(not_found)
            return

        # Check self-target
        if target_mob is char:
            msg_char = social.get("self_to_char", "")
            msg_room = social.get("self_to_room", "")
            if msg_char:
                await session.send_line(msg_char.replace("$n", char.name))
            if msg_room:
                formatted = msg_room.replace("$n", char.name)
                for other in room.characters:
                    if other is not char and other.session:
                        await other.session.send_line(f"\r\n{formatted}")
            return

        # Found target
        target_name_display = target_mob.name
        msg_char = social.get("found_to_char", "")
        msg_room = social.get("found_to_room", "")
        msg_victim = social.get("found_to_victim", "")

        if msg_char:
            await session.send_line(
                msg_char.replace("$n", char.name).replace("$N", target_name_display)
            )
        if msg_victim and target_mob.session:
            await target_mob.session.send_line(
                f"\r\n{msg_victim.replace('$n', char.name).replace('$N', target_name_display)}"
            )
        if msg_room:
            formatted = msg_room.replace("$n", char.name).replace("$N", target_name_display)
            for other in room.characters:
                if other is char or other is target_mob:
                    continue
                if other.session:
                    await other.session.send_line(f"\r\n{formatted}")

    # ── Zone resets ──────────────────────────────────────────────

    def _do_zone_resets(self, initial: bool = False) -> None:
        """Execute zone reset commands."""
        for zone in self.world.zones:
            if not initial:
                zone.age += 1
                if zone.age < zone.lifespan:
                    continue
                if zone.reset_mode == 1:
                    has_players = False
                    for vnum in range(zone.bot, zone.top + 1):
                        room = self.world.get_room(vnum)
                        if room:
                            for ch in room.characters:
                                if not ch.is_npc:
                                    has_players = True
                                    break
                        if has_players:
                            break
                    if has_players:
                        continue

            zone.age = 0
            self._execute_zone_commands(zone)

    def _execute_zone_commands(self, zone: Any) -> None:
        """Execute reset commands for a zone."""
        last_mob = None
        last_obj = None
        if_flag_ok = True

        for cmd in zone.reset_commands:
            cmd_type = cmd.get("command", "")
            if_flag = cmd.get("if_flag", 0)

            if if_flag and not if_flag_ok:
                continue

            if cmd_type == "M":
                vnum = cmd.get("arg1", 0)
                max_existing = cmd.get("arg2", 1)
                room_vnum = cmd.get("arg3", 0)
                count = sum(
                    1 for r in self.world.rooms.values()
                    for ch in r.characters
                    if ch.is_npc and ch.proto.vnum == vnum
                )
                if count < max_existing:
                    mob = self.world.create_mob(vnum, room_vnum)
                    last_mob = mob
                    if_flag_ok = mob is not None
                else:
                    if_flag_ok = False
                    last_mob = None

            elif cmd_type == "O":
                vnum = cmd.get("arg1", 0)
                room_vnum = cmd.get("arg3", 0)
                obj = self.world.create_obj(vnum)
                if obj:
                    self.world.obj_to_room(obj, room_vnum)
                    last_obj = obj
                    if_flag_ok = True
                else:
                    if_flag_ok = False

            elif cmd_type == "G":
                vnum = cmd.get("arg1", 0)
                if last_mob:
                    obj = self.world.create_obj(vnum)
                    if obj:
                        obj.carried_by = last_mob
                        last_mob.inventory.append(obj)
                        last_obj = obj
                        if_flag_ok = True
                    else:
                        if_flag_ok = False
                else:
                    if_flag_ok = False

            elif cmd_type == "E":
                vnum = cmd.get("arg1", 0)
                wear_pos = cmd.get("arg3", 0)
                if last_mob:
                    obj = self.world.create_obj(vnum)
                    if obj:
                        obj.worn_by = last_mob
                        obj.wear_pos = wear_pos
                        last_mob.equipment[wear_pos] = obj
                        last_obj = obj
                        if_flag_ok = True
                    else:
                        if_flag_ok = False
                else:
                    if_flag_ok = False

            elif cmd_type == "P":
                vnum = cmd.get("arg1", 0)
                if last_obj:
                    obj = self.world.create_obj(vnum)
                    if obj:
                        obj.in_obj = last_obj
                        last_obj.contains.append(obj)
                        if_flag_ok = True
                    else:
                        if_flag_ok = False
                else:
                    if_flag_ok = False

            elif cmd_type == "D":
                room_vnum = cmd.get("arg1", 0)
                direction = cmd.get("arg2", 0)
                state = cmd.get("arg3", 0)
                room = self.world.get_room(room_vnum)
                if room and room.has_door(direction):
                    room.door_states[direction]["closed"] = state in (1, 2)
                    room.door_states[direction]["locked"] = state == 2
                if_flag_ok = True

            elif cmd_type == "T":
                # Trigger attachment — handled by trigger system
                if_flag_ok = True

    # ── Entry point ──────────────────────────────────────────────

    async def run(self) -> None:
        """Boot and run the engine."""
        await self.boot()
        try:
            await self.run_loop()
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()


# ── Main ─────────────────────────────────────────────────────────

def main() -> None:
    game = os.environ.get("GAME", "tbamud")
    config_path = BASE_DIR / "config" / f"{game}.yaml"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    engine = Engine(config_path)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _signal_handler() -> None:
        engine._running = False

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    try:
        loop.run_until_complete(engine.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
