"""DG Script trigger runtime — Lua-based trigger execution via lupa."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine
    from core.world import MobInstance, ObjInstance, Room

log = logging.getLogger(__name__)

# Trigger types (matching DG Script)
TRIG_MOB_GREET = 1
TRIG_MOB_ENTRY = 2
TRIG_MOB_COMMAND = 3
TRIG_MOB_SPEECH = 4
TRIG_MOB_ACT = 5
TRIG_MOB_FIGHT = 6
TRIG_MOB_DEATH = 7
TRIG_MOB_RANDOM = 8
TRIG_OBJ_COMMAND = 9
TRIG_OBJ_GET = 10
TRIG_OBJ_DROP = 11
TRIG_OBJ_GIVE = 12
TRIG_ROOM_ENTER = 13
TRIG_ROOM_COMMAND = 14
TRIG_ROOM_RANDOM = 15
TRIG_ROOM_SPEECH = 16


class TriggerRuntime:
    """Manage DG Script triggers via lupa Lua runtime."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self._lua = None
        self._triggers: dict[int, dict[str, Any]] = {}  # vnum → trigger data
        self._variables: dict[str, dict[str, str]] = {}  # context → variables

    def init(self, data_dir: Path | None = None) -> bool:
        """Initialize Lua runtime and load triggers."""
        try:
            from lupa import LuaRuntime
        except ImportError:
            log.warning("lupa not installed — triggers disabled")
            return False

        self._lua = LuaRuntime(unpack_returned_tuples=True)

        # Set up sandbox
        g = self._lua.globals()
        g.print = self._lua_print

        # Register engine API functions
        g.send_to_char = self._api_send_to_char
        g.send_to_room = self._api_send_to_room
        g.get_variable = self._api_get_variable
        g.set_variable = self._api_set_variable
        g.teleport = self._api_teleport
        g.damage = self._api_damage
        g.heal = self._api_heal
        g.force_command = self._api_force_command

        # Load triggers Lua source
        if data_dir:
            triggers_path = data_dir / "lua" / "triggers.lua"
            if triggers_path.exists():
                try:
                    source = triggers_path.read_text(encoding="utf-8")
                    self._lua.execute(source)
                    # Get trigger registry from Lua
                    triggers_table = g.Triggers
                    if triggers_table:
                        self._load_trigger_table(triggers_table)
                    log.info("Loaded %d triggers from Lua", len(self._triggers))
                except Exception as e:
                    log.error("Failed to load triggers.lua: %s", e)
                    return False

        return True

    def _load_trigger_table(self, lua_table: Any) -> None:
        """Extract trigger definitions from Lua table."""
        if not self._lua:
            return
        try:
            for key in lua_table:
                trig = lua_table[key]
                if trig:
                    self._triggers[int(key)] = {
                        "vnum": int(key),
                        "type": int(trig.trigger_type or 0),
                        "name": str(trig.name or ""),
                        "arg": str(trig.arg or ""),
                    }
        except Exception as e:
            log.warning("Error loading trigger table: %s", e)

    @property
    def trigger_count(self) -> int:
        return len(self._triggers)

    def get_trigger(self, vnum: int) -> dict[str, Any] | None:
        return self._triggers.get(vnum)

    # ── Trigger execution ────────────────────────────────────────

    async def fire_trigger(self, trig_vnum: int, actor: Any = None,
                           target: Any = None, arg: str = "") -> bool:
        """Execute a trigger by vnum. Returns True if trigger was found and run."""
        if not self._lua:
            return False

        trig = self._triggers.get(trig_vnum)
        if not trig:
            return False

        try:
            g = self._lua.globals()
            execute_fn = g.execute_trigger
            if execute_fn:
                result = execute_fn(trig_vnum, arg)
                return bool(result)
        except Exception as e:
            log.warning("Trigger %d execution error: %s", trig_vnum, e)

        return False

    async def check_room_triggers(self, room_vnum: int, trig_type: int,
                                  actor: Any = None, arg: str = "") -> bool:
        """Check and fire room triggers of given type."""
        room = self.engine.world.get_room(room_vnum)
        if not room:
            return False

        for trig_vnum in room.proto.trigger_vnums:
            trig = self._triggers.get(trig_vnum)
            if trig and trig["type"] == trig_type:
                return await self.fire_trigger(trig_vnum, actor=actor, arg=arg)
        return False

    async def check_mob_triggers(self, mob: Any, trig_type: int,
                                 actor: Any = None, arg: str = "") -> bool:
        """Check and fire mob triggers of given type."""
        for trig_vnum in mob.proto.trigger_vnums:
            trig = self._triggers.get(trig_vnum)
            if trig and trig["type"] == trig_type:
                return await self.fire_trigger(trig_vnum, actor=actor, arg=arg)
        return False

    # ── Engine API (exposed to Lua) ──────────────────────────────

    def _lua_print(self, *args: Any) -> None:
        log.debug("[Lua] %s", " ".join(str(a) for a in args))

    def _api_send_to_char(self, char_id: int, message: str) -> None:
        """Send message to a character by ID."""
        # Find character
        for room in self.engine.world.rooms.values():
            for ch in room.characters:
                if ch.id == char_id and ch.session:
                    import asyncio
                    asyncio.ensure_future(ch.session.send_line(str(message)))
                    return

    def _api_send_to_room(self, room_vnum: int, message: str) -> None:
        """Send message to all characters in a room."""
        room = self.engine.world.get_room(room_vnum)
        if room:
            import asyncio
            for ch in room.characters:
                if ch.session:
                    asyncio.ensure_future(ch.session.send_line(str(message)))

    def _api_get_variable(self, context: str, name: str) -> str:
        """Get a DG Script variable."""
        return self._variables.get(str(context), {}).get(str(name), "")

    def _api_set_variable(self, context: str, name: str, value: str) -> None:
        """Set a DG Script variable."""
        ctx = str(context)
        if ctx not in self._variables:
            self._variables[ctx] = {}
        self._variables[ctx][str(name)] = str(value)

    def _api_teleport(self, char_id: int, room_vnum: int) -> None:
        """Teleport a character to a room."""
        world = self.engine.world
        for room in world.rooms.values():
            for ch in room.characters:
                if ch.id == char_id:
                    room.characters.remove(ch)
                    ch.room_vnum = room_vnum
                    dest = world.get_room(room_vnum)
                    if dest:
                        dest.characters.append(ch)
                    return

    def _api_damage(self, char_id: int, amount: int) -> None:
        """Deal damage to a character."""
        for room in self.engine.world.rooms.values():
            for ch in room.characters:
                if ch.id == char_id:
                    ch.hp -= int(amount)
                    return

    def _api_heal(self, char_id: int, amount: int) -> None:
        """Heal a character."""
        for room in self.engine.world.rooms.values():
            for ch in room.characters:
                if ch.id == char_id:
                    ch.hp = min(ch.max_hp, ch.hp + int(amount))
                    return

    def _api_force_command(self, char_id: int, command: str) -> None:
        """Force a character to execute a command."""
        for room in self.engine.world.rooms.values():
            for ch in room.characters:
                if ch.id == char_id and ch.session:
                    import asyncio
                    asyncio.ensure_future(
                        self.engine.process_command(ch.session, str(command))
                    )
                    return
