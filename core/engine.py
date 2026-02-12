"""GenOS Engine — main game loop, boot sequence, command dispatcher."""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml

from core.db import Database
from core.lua_commands import LuaCommandRuntime
from core.net import TelnetConnection, TelnetServer
from core.reload import ReloadManager
from core.session import Session
from core.world import World

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
        self.lua: LuaCommandRuntime | None = None

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

        # 5. Register core commands (Python — directions, base fallbacks)
        self._register_core_commands()
        self._plugin.register_commands(self)

        # 6. Load Lua runtime
        self.lua = LuaCommandRuntime(self)
        await self.db.ensure_lua_scripts_table()
        lua_count = await self.db.lua_scripts_count()
        if lua_count == 0:
            seeded = await self.lua.seed_from_files(self.db, self.game_name)
            log.info("Lua scripts seeded from files: %d", seeded)
        loaded = await self.lua.load_from_db(self.db, self.game_name)
        self.lua.register_all_commands()
        log.info("Lua commands loaded: %d scripts, %d commands, %d hooks",
                 loaded, self.lua.command_count, self.lua.hook_count)

        # 7. Load Korean verb mapping into cmd_korean
        self._load_korean_mappings()

        # 8. Initial zone resets
        self._do_zone_resets(initial=True)

        # 9. Start network
        net_cfg = self.config.get("network", {})
        self._telnet = TelnetServer(
            host=net_cfg.get("telnet_host", "0.0.0.0"),
            port=net_cfg.get("telnet_port", 4000),
            on_connect=self._on_new_connection,
        )
        await self._telnet.start()

        # 10. Start file watcher (dev mode)
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

        # Lua combat_round hook (thac0.lua registers this)
        lua = getattr(self, "lua", None)
        if lua and lua.has_hook("combat_round"):
            await self._lua_combat_round()
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

    async def _lua_combat_round(self) -> None:
        """Run combat round via Lua hook."""
        from core.lua_commands import HookContext

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
                target = char.fighting
                ctx = HookContext(self, room)
                self.lua.fire_hook("combat_round", ctx, char, target)
                await ctx.flush()
                await ctx.execute_deferred()

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
        """Register Python-only commands (direction movement).

        All other commands are provided by Lua scripts (games/common/lua/).
        """
        self.register_command("north", lambda s, a: self.do_move(s, "north"))
        self.register_command("south", lambda s, a: self.do_move(s, "south"))
        self.register_command("east", lambda s, a: self.do_move(s, "east"))
        self.register_command("west", lambda s, a: self.do_move(s, "west"))
        self.register_command("up", lambda s, a: self.do_move(s, "up"))
        self.register_command("down", lambda s, a: self.do_move(s, "down"))

        # cast/practice — now provided by Lua (games/tbamud/lua/combat/spells.lua)

        # Look fallback — Lua overwrites this with full implementation
        async def _look_fallback(session: Session, args: str) -> None:
            char = session.character
            if not char:
                return
            room = self.world.get_room(char.room_vnum)
            if room:
                await session.send_line(f"\r\n{{cyan}}{room.proto.name}{{reset}}")
            else:
                await session.send_line("허공에 떠 있습니다...")
        self.register_command("look", _look_fallback, korean="봐")

    async def do_look(self, session: Session, args: str) -> None:
        """Delegate to registered look command handler."""
        handler = self.cmd_handlers.get("look")
        if handler:
            await handler(session, args)

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

    # ── Position constants ────────────────────────────────────────

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

    # ── Combat commands (tbaMUD-specific, Sprint 4 → Lua) ────────

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
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

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
