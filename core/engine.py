"""GenOS Engine — main game loop, boot sequence, command dispatcher."""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import random
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
    "밑": 5,
    # 대각선 (3eyes 10-dir exits)
    "남동": 6, "남서": 7, "북동": 8, "북서": 9,
    # 초성 약어 — 방향
    "ㅂ": 0, "ㄷ": 1, "ㄴ": 2, "ㅅ": 3, "ㅇ": 4, "ㅁ": 5,
    "ㅂㄷ": 8, "ㅂㅅ": 9, "ㄴㄷ": 6, "ㄴㅅ": 7,
    # 숫자패드
    "8": 0, "6": 1, "2": 2, "4": 3, "9": 8, "3": 6,
}
REVERSE_DIRS = [2, 3, 0, 1, 5, 4]  # north↔south, east↔west, up↔down

# ── Korean Choseong (초성) abbreviation table ────────────────────

CHOSEONG_MAP: dict[str, str] = {
    "ㄱ": "공격", "ㄹ": "look",
    "ㅈ": "저장", "ㅊ": "착용", "ㅎ": "help",
}

# ── Korean verb → English action mapping (default, extensible by plugin) ──

_DEFAULT_KOREAN_VERB_MAP: dict[str, str] = {
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
    "나가": "quit", "나가기": "quit", "소지품": "inventory", "장비": "equipment",
    "출구": "exits", "명령어": "commands", "점수": "score",
}

# Active verb map — merged from default + plugin at boot time
KOREAN_VERB_MAP: dict[str, str] = dict(_DEFAULT_KOREAN_VERB_MAP)

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

        # Game time / weather
        self.game_hour: int = 8       # 0-23 MUD hours
        self.game_day: int = 1        # 1-35
        self.game_month: int = 1      # 1-16
        self.game_year: int = 650
        self.weather: str = "sunny"   # sunny, cloudy, rainy, stormy

    # ── Boot sequence ────────────────────────────────────────────

    async def boot(self) -> None:
        log.info("=== GenOS Engine booting: %s ===", self.config.get("name", self.game_name))

        # 1. Connect to DB
        await self.db.connect()

        # 2. Auto-init DB (REINIT_DB=1 forces drop+recreate from seed_data.sql)
        data_dir = BASE_DIR / "data" / self.game_name
        force_reinit = os.environ.get("REINIT_DB", "").strip() in ("1", "true", "yes")
        await self.db.auto_init(data_dir, force=force_reinit)
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
        # Always reseed from files (upsert) so updated/new scripts are picked up
        seeded = await self.lua.seed_from_files(self.db, self.game_name)
        if seeded:
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
        """Load Korean → English command mappings from verb map.

        Merges default + plugin-provided Korean verb mappings.
        """
        # Let plugin extend the verb map
        plugin = getattr(self, "_plugin", None)
        if plugin and hasattr(plugin, "korean_verb_map"):
            extra = plugin.korean_verb_map()
            if extra:
                KOREAN_VERB_MAP.update(extra)

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

            # Game time + affect ticks (every 75 seconds ≈ 1 "MUD hour" at 10Hz)
            if self._tick % 750 == 0:
                self._advance_game_time()
                await self._tick_affects()
                self._tick_corpse_decay()

            # NPC AI (every 100 ticks = 10 seconds at 10Hz)
            if self._tick % 100 == 0:
                await self._mobile_activity()

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
        """Process one combat round for all fighting characters.

        Delegates to: plugin.combat_round > Lua hook > no-op.
        All combat logic MUST be in Lua scripts (web-editable).
        """
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

        # No combat system loaded — just clear stale fights
        for room in self.world.rooms.values():
            for char in list(room.characters):
                if char.fighting and char.fighting.hp <= 0:
                    char.fighting = None

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

                # Wimpy auto-flee check (for player chars after taking damage)
                if char.hp > 0 and char.fighting and char.wimpy > 0:
                    if char.hp <= char.wimpy and char.session:
                        await char.session.send_line(
                            "{yellow}체력이 위험합니다! 자동으로 도망칩니다!{reset}"
                        )
                        # Trigger flee command
                        flee_handler = self.cmd_handlers.get("flee")
                        if flee_handler:
                            await flee_handler(char.session, "")

    async def _send_to_char(self, char, message: str) -> None:
        """Send message to a character if they have a session."""
        if char.session:
            await char.session.send_line(message)

    async def _tick_affects(self) -> None:
        """Tick down affects + natural HP/mana/move regeneration."""
        # Plugin can override affect ticking
        plugin = getattr(self, "_plugin", None)
        if plugin and hasattr(plugin, "tick_affects"):
            await plugin.tick_affects(self)
            return

        for room in self.world.rooms.values():
            for char in list(room.characters):
                if char.affects:
                    messages = self._tick_char_affects(char)
                    if char.session:
                        for msg in messages:
                            await char.session.send_line(msg)

                # Natural regeneration (every MUD hour)
                if char.position >= self.POS_RESTING and not char.fighting:
                    self._regen_char(char)

    @staticmethod
    def _tick_char_affects(char: Any) -> list[str]:
        """Tick down affect durations. Returns expiry messages. Generic engine version."""
        messages: list[str] = []
        remaining = []
        for affect in char.affects:
            affect["duration"] = affect.get("duration", 0) - 1
            if affect["duration"] <= 0:
                name = affect.get("name", "")
                if name:
                    messages.append(f"{name} 효과가 사라졌습니다.")
                else:
                    spell_id = affect.get("spell_id", affect.get("id", 0))
                    if spell_id:
                        messages.append(f"효과 #{spell_id}이(가) 사라졌습니다.")
            else:
                # Poison damage tick
                dmg = affect.get("damage_per_tick", 0)
                if dmg and dmg > 0:
                    char.hp -= dmg
                    messages.append(f"{{green}}독이 퍼져 {dmg}의 피해를 입습니다!{{reset}}")
                remaining.append(affect)
        char.affects = remaining
        return messages

    def _regen_char(self, char: Any) -> None:
        """Regenerate HP/mana/move based on position.

        Default rates: standing=1x, resting=2x, sleeping=4x.
        Plugin can override via regen_char(engine, char) hook.
        """
        # Plugin override
        plugin = getattr(self, "_plugin", None)
        if plugin and hasattr(plugin, "regen_char"):
            plugin.regen_char(self, char)
            return

        lv = char.level
        pos = char.position

        # Position multiplier
        if pos == self.POS_SLEEPING:
            mult = 4
        elif pos == self.POS_RESTING:
            mult = 2
        else:
            mult = 1

        # HP regen
        base_hp = max(1, lv // 3 + 1) * mult
        if char.hp < char.max_hp:
            char.hp = min(char.max_hp, char.hp + base_hp)

        # Mana regen (generic: all classes same rate)
        base_mana = max(1, lv // 5 + 1) * mult
        if char.mana < char.max_mana:
            char.mana = min(char.max_mana, char.mana + base_mana)

        # Move regen
        base_move = max(1, lv // 4 + 1) * mult
        if char.move < char.max_move:
            char.move = min(char.max_move, char.move + base_move)

    def _tick_corpse_decay(self) -> None:
        """Tick down corpse timers and remove expired corpses."""
        for room in self.world.rooms.values():
            for obj in list(room.objects):
                if obj.values.get("corpse"):
                    timer = obj.values.get("timer", 0)
                    if timer <= 1:
                        # Corpse decays — drop contents to room
                        for item in list(obj.contains):
                            item.in_obj = None
                            item.room_vnum = room.proto.vnum
                            room.objects.append(item)
                        obj.contains.clear()
                        room.objects.remove(obj)
                    else:
                        obj.values["timer"] = timer - 1

    # ── Game time / weather ──────────────────────────────────────

    def _advance_game_time(self) -> None:
        """Advance game clock by 1 MUD hour. Update weather."""
        self.game_hour += 1
        if self.game_hour >= 24:
            self.game_hour = 0
            self.game_day += 1
            if self.game_day > 35:
                self.game_day = 1
                self.game_month += 1
                if self.game_month > 16:
                    self.game_month = 1
                    self.game_year += 1

        # Weather changes (~15% chance each MUD hour)
        if random.random() < 0.15:
            transitions = {
                "sunny": ["sunny", "sunny", "cloudy"],
                "cloudy": ["sunny", "cloudy", "rainy"],
                "rainy": ["cloudy", "rainy", "stormy"],
                "stormy": ["rainy", "stormy", "cloudy"],
            }
            choices = transitions.get(self.weather, ["sunny"])
            self.weather = random.choice(choices)

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

        # Position-based command restrictions
        char = session.character
        if char:
            # Sleeping: only allow wake, quit
            if char.position == self.POS_SLEEPING:
                first = text.split()[0].lower()
                wake_cmds = {"wake", "일어나", "quit", "나가기", "save", "저장"}
                eng_first = self.cmd_korean.get(first, first)
                if eng_first not in wake_cmds and first not in wake_cmds:
                    await session.send_line("잠든 상태에서는 할 수 없습니다. 먼저 일어나세요.")
                    return
            # Fighting: restrict movement
            if char.fighting:
                first = text.split()[0].lower()
                if (first in DIR_ABBREV or first in DIRS or first in DIR_NAMES_KR_MAP):
                    await session.send_line("전투 중에는 이동할 수 없습니다! flee를 사용하세요.")
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

        # 8. Named exit — check if input matches any exit keyword in current room
        if handler is None and char:
            if char.fighting:
                pass  # Can't move through named exits while fighting
            else:
                room = self.world.get_room(char.room_vnum)
                if room:
                    input_lower = text.strip()
                    for ex in room.proto.exits:
                        if ex.direction >= 6 and ex.keywords == input_lower:
                            await self._do_named_move(session, ex)
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

        # Direct handler lookup first (game-specific overrides take priority)
        handler = self.cmd_handlers.get(token)
        if handler:
            return token, args_str, handler

        # Korean → English mapping (fallback for aliases like 건강→score)
        eng = self.cmd_korean.get(token)
        if eng:
            handler = self.cmd_handlers.get(eng)
            if handler:
                return eng, args_str, handler

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

        if dir_idx is None or dir_idx < 0 or dir_idx > 9:
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

        # Check sneak — if sneaking, suppress movement messages
        is_sneaking = any(a.get("id") == 1001 for a in char.affects)

        # Leave message
        if not is_sneaking:
            leave_dir = DIR_NAMES_KR[dir_idx] if dir_idx < 6 else "어딘가"
            for other in room.characters:
                if other is char:
                    continue
                if other.session:
                    await other.session.send_line(f"\r\n{char.name}이(가) {leave_dir}쪽으로 떠났습니다.")

        # Move
        self.world.char_to_room(char, exit_found.to_room)

        # Arrive message
        if not is_sneaking:
            arrive_dir = DIR_NAMES_KR[REVERSE_DIRS[dir_idx]] if dir_idx < 6 else "어딘가"
            for other in dest.characters:
                if other is char:
                    continue
                if other.session:
                    await other.session.send_line(f"\r\n{char.name}이(가) {arrive_dir}쪽에서 왔습니다.")

        # Show room
        await self.do_look(session, "")

        # Followers auto-follow
        followers = getattr(char, "_followers", None)
        if followers:
            for follower in list(followers):
                if follower.room_vnum != char.room_vnum:
                    # Check follower is in the room we just left
                    old_room = self.world.get_room(room.proto.vnum)
                    if old_room and follower in old_room.characters:
                        self.world.char_to_room(follower, exit_found.to_room)
                        if follower.session:
                            await follower.session.send_line(
                                f"\r\n{char.name}을(를) 따라갑니다."
                            )
                            await self.do_look(follower.session, "")

    async def _do_named_move(self, session: Session, exit_obj: Any) -> None:
        """Move through a named exit (direction >= 6)."""
        char = session.character
        if not char:
            return

        room = self.world.get_room(char.room_vnum)
        if not room:
            return

        dest = self.world.get_room(exit_obj.to_vnum)
        if not dest:
            await session.send_line("그쪽으로는 갈 수 없습니다.")
            return

        # Check door
        if room.has_door(exit_obj.direction):
            if room.is_door_closed(exit_obj.direction):
                await session.send_line("문이 닫혀있습니다.")
                return

        kw = exit_obj.keywords or "어딘가"
        is_sneaking = any(a.get("id") == 1001 for a in char.affects)

        # Leave message
        if not is_sneaking:
            for other in room.characters:
                if other is not char and other.session:
                    await other.session.send_line(f"\r\n{char.name}이(가) {kw}(으)로 떠났습니다.")

        # Move
        self.world.char_to_room(char, exit_obj.to_vnum)

        # Arrive message
        if not is_sneaking:
            for other in dest.characters:
                if other is not char and other.session:
                    await other.session.send_line(f"\r\n{char.name}이(가) 나타났습니다.")

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
        """Cast a spell — delegates to Lua 'cast' command."""
        handler = self.cmd_handlers.get("cast")
        if handler:
            await handler(session, args or "")
        else:
            await session.send_line("주문 시스템이 로드되지 않았습니다.")

    async def do_practice(self, session: Session, args: str) -> None:
        """Practice — delegates to Lua 'practice' command."""
        handler = self.cmd_handlers.get("practice")
        if handler:
            await handler(session, args or "")
        else:
            await session.send_line("연습 시스템이 로드되지 않았습니다.")

    # ── Social commands ──────────────────────────────────────────

    @staticmethod
    def _subst_social(msg: str, actor: Any, target: Any = None) -> str:
        """Substitute social message variables.

        $n/$m/$e/$s → actor, $N/$M/$E/$S → target.
        Korean: gender-neutral, so $m/$M → 그, $e/$E → 그, $s/$S → 그의.
        """
        if not msg:
            return msg
        msg = msg.replace("$n", actor.name)
        msg = msg.replace("$m", "그")     # him/her (actor)
        msg = msg.replace("$e", "그")     # he/she (actor)
        msg = msg.replace("$s", "그의")   # his/her (actor)
        if target:
            msg = msg.replace("$N", target.name)
            msg = msg.replace("$M", "그")     # him/her (target)
            msg = msg.replace("$E", "그")     # he/she (target)
            msg = msg.replace("$S", "그의")   # his/her (target)
        return msg

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

        # Access messages dict (socials store messages in "messages" JSONB)
        msgs = social.get("messages", social)

        target_name = args.strip() if args else ""

        if not target_name:
            # No target
            msg_char = msgs.get("no_arg_to_char", "")
            msg_room = msgs.get("no_arg_to_room", "")
            if msg_char:
                await session.send_line(self._subst_social(msg_char, char))
            if msg_room:
                formatted = self._subst_social(msg_room, char)
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
            not_found = msgs.get("not_found", "그런 사람을 찾을 수 없습니다.")
            await session.send_line(not_found)
            return

        # Check self-target
        if target_mob is char:
            msg_char = msgs.get("self_to_char", "")
            msg_room = msgs.get("self_to_room", "")
            if msg_char:
                await session.send_line(self._subst_social(msg_char, char))
            if msg_room:
                formatted = self._subst_social(msg_room, char)
                for other in room.characters:
                    if other is not char and other.session:
                        await other.session.send_line(f"\r\n{formatted}")
            return

        # Found target
        msg_char = msgs.get("found_to_char", "")
        msg_room = msgs.get("found_to_room", "")
        msg_victim = msgs.get("found_to_victim", "")

        if msg_char:
            await session.send_line(self._subst_social(msg_char, char, target_mob))
        if msg_victim and target_mob.session:
            await target_mob.session.send_line(
                f"\r\n{self._subst_social(msg_victim, char, target_mob)}"
            )
        if msg_room:
            formatted = self._subst_social(msg_room, char, target_mob)
            for other in room.characters:
                if other is char or other is target_mob:
                    continue
                if other.session:
                    await other.session.send_line(f"\r\n{formatted}")

    # ── NPC AI (mobile_activity) ─────────────────────────────────

    async def _mobile_activity(self) -> None:
        """Process NPC autonomous behavior — scavenger, movement, aggro, memory, helper, wimpy."""
        # Plugin can override NPC AI
        plugin = getattr(self, "_plugin", None)
        if plugin and hasattr(plugin, "mobile_activity"):
            await plugin.mobile_activity(self)
            return
        for room in list(self.world.rooms.values()):
            for mob in list(room.characters):
                if not mob.is_npc:
                    continue
                if mob.fighting:
                    # Wimpy: flee at <20% HP
                    if "wimpy" in mob.proto.act_flags and mob.hp < mob.max_hp // 5:
                        await self._mob_flee(mob, room)
                    continue
                if mob.position < self.POS_STANDING:
                    continue

                # 1. Scavenger — pick up most valuable item in room
                if "scavenger" in mob.proto.act_flags and room.objects:
                    if random.random() < 0.10:
                        best = max(room.objects, key=lambda o: o.proto.cost)
                        room.objects.remove(best)
                        best.room_vnum = None
                        best.carried_by = mob
                        mob.inventory.append(best)
                        await self._act_room(room, f"{mob.name}이(가) {best.name}을(를) 주워 담습니다.", exclude=None)

                # 2. Memory — attack remembered PCs
                if "memory" in mob.proto.act_flags and mob.memory:
                    found_enemy = None
                    for ch in room.characters:
                        if not ch.is_npc and ch.player_id in mob.memory:
                            found_enemy = ch
                            break
                    if found_enemy:
                        await self._act_room(room, f"'이봐! 날 공격한 놈이잖아!!!' {mob.name}이(가) 외칩니다.")
                        self._start_npc_combat(mob, found_enemy)
                        continue

                # 3. Helper — assist fighting NPC ally
                if "helper" in mob.proto.act_flags:
                    for ally in room.characters:
                        if ally is mob or not ally.is_npc:
                            continue
                        if ally.fighting and not ally.fighting.is_npc:
                            await self._act_room(room, f"{mob.name}이(가) {ally.name}을(를) 돕기 위해 뛰어듭니다!")
                            self._start_npc_combat(mob, ally.fighting)
                            break
                    if mob.fighting:
                        continue

                # 4. Aggressive — attack PCs in room
                act_flags = mob.proto.act_flags
                is_aggr = ("aggressive" in act_flags or "aggr_evil" in act_flags or
                           "aggr_good" in act_flags or "aggr_neutral" in act_flags)
                if is_aggr:
                    victims = [ch for ch in room.characters if not ch.is_npc]
                    if "wimpy" in act_flags:
                        victims = [v for v in victims if v.position >= self.POS_STANDING and v.position != self.POS_SLEEPING]
                    for victim in victims:
                        if "aggr_evil" in act_flags and victim.alignment >= 0:
                            continue
                        if "aggr_good" in act_flags and victim.alignment <= 0:
                            continue
                        if "aggr_neutral" in act_flags and (victim.alignment < -350 or victim.alignment > 350):
                            continue
                        self._start_npc_combat(mob, victim)
                        break
                    if mob.fighting:
                        continue

                # 5. Movement — wander randomly
                if "sentinel" not in mob.proto.act_flags:
                    if random.randint(0, 18) < 6:
                        await self._mob_wander(mob, room)

    def _start_npc_combat(self, attacker: Any, victim: Any) -> None:
        """Start combat between NPC attacker and victim."""
        attacker.fighting = victim
        attacker.position = self.POS_FIGHTING
        if not victim.fighting:
            victim.fighting = attacker
            victim.position = self.POS_FIGHTING

    async def _mob_wander(self, mob: Any, room: Any) -> None:
        """Move NPC to a random adjacent room."""
        exits = room.proto.exits
        if not exits:
            return
        ex = random.choice(exits)
        dest = self.world.get_room(ex.to_vnum)
        if not dest:
            return
        # Check room flags
        dest_flags = dest.proto.flags
        if "nomob" in dest_flags or "death" in dest_flags:
            return
        # Check door
        if room.has_door(ex.direction) and room.is_door_closed(ex.direction):
            return
        # Stay in zone check
        if "stay_zone" in mob.proto.act_flags:
            if dest.proto.zone_vnum != room.proto.zone_vnum:
                return
        # Move
        self.world.char_to_room(mob, ex.to_vnum)

    async def _mob_flee(self, mob: Any, room: Any) -> None:
        """NPC flees from combat."""
        exits = room.proto.exits
        if not exits:
            return
        ex = random.choice(exits)
        dest = self.world.get_room(ex.to_vnum)
        if not dest:
            return
        if room.has_door(ex.direction) and room.is_door_closed(ex.direction):
            return
        # Stop combat
        if mob.fighting:
            if mob.fighting.fighting is mob:
                mob.fighting.fighting = None
                mob.fighting.position = self.POS_STANDING
            mob.fighting = None
            mob.position = self.POS_STANDING
        await self._act_room(room, f"{mob.name}이(가) 도망갑니다!")
        self.world.char_to_room(mob, ex.to_vnum)

    async def _act_room(self, room: Any, msg: str, exclude: Any = None) -> None:
        """Send a message to all players in a room (optionally excluding one)."""
        for ch in room.characters:
            if ch is exclude:
                continue
            if ch.session:
                await ch.session.send_line(f"\r\n{msg}")

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
                    for room in self.world.rooms.values():
                        if room.proto.zone_vnum != zone.vnum:
                            continue
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

        for cmd in zone.resets:
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
                wear_slot = str(cmd.get("arg3", "0"))
                if last_mob:
                    obj = self.world.create_obj(vnum)
                    if obj:
                        obj.worn_by = last_mob
                        obj.wear_slot = wear_slot
                        last_mob.equipment[wear_slot] = obj
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
