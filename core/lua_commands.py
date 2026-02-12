"""Lua command runtime — bridge between Lua scripts and the Python engine.

Provides LuaCommandRuntime for loading/executing Lua commands,
CommandContext as the ctx object exposed to Lua, and async bridging.
"""

from __future__ import annotations

import logging
import random
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lupa import LuaRuntime

from core.korean import has_batchim, particle

if TYPE_CHECKING:
    from core.db import Database
    from core.engine import Engine
    from core.session import Session
    from core.world import MobInstance, ObjInstance, Room

log = logging.getLogger(__name__)

# ── CommandContext — the `ctx` object available to Lua ────────────


class CommandContext:
    """Context object passed to every Lua command/hook as first argument.

    All methods are synchronous (Lua is single-threaded sync).
    Messages are buffered and flushed after Lua returns.
    """

    def __init__(self, session: Session, engine: Engine, lua_runtime: LuaRuntime | None = None) -> None:
        self._session = session
        self._engine = engine
        self._lua = lua_runtime
        self._messages: list[tuple[Session | None, str]] = []
        self._deferred: list[tuple[str, tuple]] = []

    def _to_lua_table(self, items: list) -> Any:
        """Convert a Python list to a Lua table (1-indexed) for # and ipairs."""
        if self._lua is None:
            return items
        tbl = self._lua.table_from(items)
        return tbl

    # ── Character proxy (direct attribute access from Lua) ────────

    @property
    def char(self) -> MobInstance | None:
        return self._session.character

    # ── Output (message buffering) ────────────────────────────────

    def send(self, msg: str) -> None:
        """Send message to current character."""
        self._messages.append((self._session, str(msg)))

    def send_to(self, target: Any, msg: str) -> None:
        """Send message to a specific character."""
        if hasattr(target, "session") and target.session:
            self._messages.append((target.session, str(msg)))

    def send_room(self, msg: str) -> None:
        """Send message to all in room except current character."""
        char = self._session.character
        if not char:
            return
        room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return
        for other in room.characters:
            if other is not char and other.session:
                self._messages.append((other.session, f"\r\n{msg}"))

    def send_all(self, msg: str) -> None:
        """Send message to all connected players."""
        for session in self._engine.sessions.values():
            self._messages.append((session, str(msg)))

    # ── Room / World queries ──────────────────────────────────────

    def get_room(self, vnum: int | None = None) -> Room | None:
        if vnum is None:
            char = self._session.character
            if char:
                return self._engine.world.get_room(char.room_vnum)
            return None
        return self._engine.world.get_room(int(vnum))

    def find_char(self, keyword: str) -> MobInstance | None:
        """Find a character in the current room by keyword."""
        char = self._session.character
        if not char:
            return None
        room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return None
        kw = str(keyword).lower()
        for mob in room.characters:
            if mob is char:
                continue
            if kw in mob.proto.keywords.lower():
                return mob
            if mob.player_name and kw in mob.player_name.lower():
                return mob
        return None

    def find_obj_inv(self, keyword: str) -> ObjInstance | None:
        """Find an item in current character's inventory."""
        char = self._session.character
        if not char:
            return None
        kw = str(keyword).lower()
        for obj in char.inventory:
            if kw in obj.proto.keywords.lower():
                return obj
        return None

    def find_obj_room(self, keyword: str) -> ObjInstance | None:
        """Find an item on the ground in current room."""
        char = self._session.character
        if not char:
            return None
        room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return None
        kw = str(keyword).lower()
        for obj in room.objects:
            if kw in obj.proto.keywords.lower():
                return obj
        return None

    def find_obj_equip(self, keyword: str) -> ObjInstance | None:
        """Find an equipped item on current character."""
        char = self._session.character
        if not char:
            return None
        kw = str(keyword).lower()
        for obj in char.equipment.values():
            if kw in obj.proto.keywords.lower():
                return obj
        return None

    def find_player(self, name: str) -> MobInstance | None:
        """Find an online player by name."""
        session = self._engine.players.get(str(name).lower())
        if session and session.character:
            return session.character
        return None

    def find_exit(self, dir_or_kw: str) -> Any:
        """Find an exit in current room."""
        from core.engine import DIR_ABBREV, DIR_NAMES_KR_MAP, DIRS
        char = self._session.character
        if not char:
            return None
        room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return None
        token = str(dir_or_kw).lower()
        # Try direction resolution
        dir_idx = None
        if token in DIR_ABBREV:
            dir_idx = DIR_ABBREV[token]
        elif token in DIRS:
            dir_idx = DIRS.index(token)
        elif token in DIR_NAMES_KR_MAP:
            dir_idx = DIR_NAMES_KR_MAP[token]
        if dir_idx is not None:
            for ex in room.proto.exits:
                if ex.direction == dir_idx:
                    return ex
        # Try keyword match
        for ex in room.proto.exits:
            if ex.keywords and token in ex.keywords.lower():
                return ex
        return None

    def get_exits(self, room: Room | None = None) -> Any:
        """Get room exits as a Lua table (1-indexed)."""
        if room is None:
            char = self._session.character
            if not char:
                return self._to_lua_table([])
            room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return self._to_lua_table([])
        return self._to_lua_table(list(room.proto.exits))

    def get_class(self, class_id: int) -> Any:
        """Get a GameClass by id."""
        return self._engine.world.classes.get(int(class_id))

    def get_skill(self, skill_id: int) -> Any:
        """Get a Skill by id."""
        return self._engine.world.skills.get(int(skill_id))

    def get_config(self, key: str) -> Any:
        """Get a game config value."""
        return self._engine.world.game_configs.get(str(key))

    def get_players(self) -> Any:
        """Get list of online player characters as a Lua table."""
        result = []
        for session in self._engine.players.values():
            if session.character:
                result.append(session.character)
        return self._to_lua_table(result)

    # ── Room content queries (Lua tables) ────────────────────────

    def get_extra_descs(self, room: Room | None = None) -> Any:
        """Get room extra descriptions as Lua table."""
        if room is None:
            char = self._session.character
            if not char:
                return self._to_lua_table([])
            room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return self._to_lua_table([])
        return self._to_lua_table(list(room.proto.extra_descs))

    def get_characters(self, room: Room | None = None) -> Any:
        """Get characters in room as Lua table."""
        if room is None:
            char = self._session.character
            if not char:
                return self._to_lua_table([])
            room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return self._to_lua_table([])
        return self._to_lua_table(list(room.characters))

    def get_objects(self, room: Room | None = None) -> Any:
        """Get objects in room as Lua table."""
        if room is None:
            char = self._session.character
            if not char:
                return self._to_lua_table([])
            room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return self._to_lua_table([])
        return self._to_lua_table(list(room.objects))

    def get_inventory(self) -> Any:
        """Get current char inventory as Lua table."""
        char = self._session.character
        if not char:
            return self._to_lua_table([])
        return self._to_lua_table(list(char.inventory))

    def get_char_inventory(self, char: Any) -> Any:
        """Get any character's inventory as Lua table."""
        if not char or not hasattr(char, "inventory"):
            return self._to_lua_table([])
        return self._to_lua_table(list(char.inventory))

    def get_equipment(self) -> Any:
        """Get current char equipment as Lua table of {slot, obj} pairs."""
        char = self._session.character
        if not char:
            return self._to_lua_table([])
        items = []
        for slot in sorted(char.equipment.keys()):
            items.append({"slot": slot, "obj": char.equipment[slot]})
        return self._to_lua_table(items)

    # ── Help / Commands / Alias ───────────────────────────────────

    def get_help(self, keyword: str) -> str | None:
        """Search help entries and return text or None."""
        kw = str(keyword).lower()
        for entry in self._engine.world.help_entries:
            keywords = entry.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            for k in keywords:
                if k.lower() == kw:
                    return entry.get("text", "")
        # Partial match
        matches = []
        for entry in self._engine.world.help_entries:
            keywords = entry.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            for k in keywords:
                if kw in k.lower():
                    matches.append(entry)
                    break
        if len(matches) == 1:
            return matches[0].get("text", "")
        if len(matches) > 1:
            kw_list = []
            for m in matches[:10]:
                kws = m.get("keywords", [])
                if isinstance(kws, str):
                    kws = [kws]
                kw_list.append(kws[0] if kws else "?")
            return f"__MULTIPLE__:{','.join(kw_list)}"
        return None

    def get_all_commands(self) -> Any:
        """Get all registered command names as Lua table."""
        eng_to_kr: dict[str, str] = {}
        for kr, eng in self._engine.cmd_korean.items():
            if eng not in eng_to_kr or len(kr) < len(eng_to_kr[eng]):
                eng_to_kr[eng] = kr

        seen: set[int] = set()
        entries = []
        for eng_cmd in sorted(self._engine.cmd_handlers.keys()):
            handler_id = id(self._engine.cmd_handlers[eng_cmd])
            if handler_id in seen:
                continue
            seen.add(handler_id)
            kr = eng_to_kr.get(eng_cmd, "")
            entries.append({"eng": eng_cmd, "kr": kr})
        return self._to_lua_table(entries)

    def get_aliases(self) -> Any:
        """Get player aliases as Lua table of {name, cmd} pairs."""
        import json as _json
        aliases = self._session.player_data.get("aliases", {})
        if isinstance(aliases, str):
            try:
                aliases = _json.loads(aliases)
            except (_json.JSONDecodeError, TypeError):
                aliases = {}
        items = [{"name": k, "cmd": v} for k, v in aliases.items()]
        return self._to_lua_table(items)

    def set_alias(self, name: str, cmd: str) -> bool:
        """Set a player alias. Returns False if max reached."""
        import json as _json
        aliases = self._session.player_data.get("aliases", {})
        if isinstance(aliases, str):
            try:
                aliases = _json.loads(aliases)
            except (_json.JSONDecodeError, TypeError):
                aliases = {}
        if len(aliases) >= 20 and str(name) not in aliases:
            return False
        aliases[str(name)] = str(cmd)
        self._session.player_data["aliases"] = aliases
        return True

    def get_alias_count(self) -> int:
        """Get number of aliases."""
        import json as _json
        aliases = self._session.player_data.get("aliases", {})
        if isinstance(aliases, str):
            try:
                aliases = _json.loads(aliases)
            except (_json.JSONDecodeError, TypeError):
                return 0
        return len(aliases)

    # ── Door helpers ──────────────────────────────────────────────

    def find_door(self, target: str) -> int:
        """Find door direction from keyword or direction name. Returns -1 if not found."""
        from core.engine import DIR_ABBREV, DIR_NAMES_KR_MAP, DIRS
        char = self._session.character
        if not char:
            return -1
        room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return -1
        token = str(target).lower()
        if token in DIR_ABBREV:
            return DIR_ABBREV[token]
        if token in DIR_NAMES_KR_MAP:
            return DIR_NAMES_KR_MAP[token]
        if token in DIRS:
            return DIRS.index(token)
        for ex in room.proto.exits:
            if ex.keywords and token in ex.keywords.lower():
                return ex.direction
        return -1

    def has_door(self, direction: int) -> bool:
        char = self._session.character
        if not char:
            return False
        room = self._engine.world.get_room(char.room_vnum)
        return room.has_door(int(direction)) if room else False

    def is_door_closed(self, direction: int) -> bool:
        char = self._session.character
        if not char:
            return False
        room = self._engine.world.get_room(char.room_vnum)
        return room.is_door_closed(int(direction)) if room else False

    def is_door_locked(self, direction: int) -> bool:
        char = self._session.character
        if not char:
            return False
        room = self._engine.world.get_room(char.room_vnum)
        return room.is_door_locked(int(direction)) if room else False

    def set_door_state(self, direction: int, closed: bool, locked: bool | None = None) -> None:
        """Set door state for current room and sync other side."""
        from core.engine import REVERSE_DIRS
        char = self._session.character
        if not char:
            return
        direction = int(direction)
        room = self._engine.world.get_room(char.room_vnum)
        if not room or not room.has_door(direction):
            return
        room.door_states[direction]["closed"] = bool(closed)
        if locked is not None:
            room.door_states[direction]["locked"] = bool(locked)
        # Sync other side
        for ex in room.proto.exits:
            if ex.direction == direction:
                other_room = self._engine.world.get_room(ex.to_room)
                if other_room:
                    rev = REVERSE_DIRS[direction]
                    if other_room.has_door(rev):
                        other_room.door_states[rev]["closed"] = bool(closed)
                        if locked is not None:
                            other_room.door_states[rev]["locked"] = bool(locked)
                break

    def has_key(self, direction: int) -> bool:
        """Check if current char has the key for a door."""
        char = self._session.character
        if not char:
            return False
        room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return False
        key_vnum = -1
        for ex in room.proto.exits:
            if ex.direction == int(direction):
                key_vnum = ex.key_vnum
                break
        if key_vnum <= 0:
            return True  # No key required
        return (any(o.proto.vnum == key_vnum for o in char.inventory) or
                any(o.proto.vnum == key_vnum for o in char.equipment.values()))

    # ── Session helpers ───────────────────────────────────────────

    def get_player_data(self, key: str) -> Any:
        """Get a value from player_data dict."""
        return self._session.player_data.get(str(key))

    def close_session(self) -> None:
        """Mark session as closed (for quit)."""
        self._session._closed = True
        self._deferred.append(("close_conn", ()))

    # ── State changes ─────────────────────────────────────────────

    def move_to(self, room_vnum: int) -> None:
        """Move current character to a room."""
        char = self._session.character
        if char:
            self._engine.world.char_to_room(char, int(room_vnum))

    def create_obj(self, vnum: int) -> ObjInstance | None:
        return self._engine.world.create_obj(int(vnum))

    def create_mob(self, vnum: int, room_vnum: int) -> MobInstance | None:
        return self._engine.world.create_mob(int(vnum), int(room_vnum))

    def obj_to_char(self, obj: Any, char: Any) -> None:
        if obj and char:
            obj.carried_by = char
            char.inventory.append(obj)

    def obj_from_char(self, obj: Any) -> None:
        if obj and obj.carried_by:
            if obj in obj.carried_by.inventory:
                obj.carried_by.inventory.remove(obj)
            obj.carried_by = None

    def obj_to_room(self, obj: Any, room_vnum: int) -> None:
        if obj:
            self._engine.world.obj_to_room(obj, int(room_vnum))

    def obj_from_room(self, obj: Any) -> None:
        """Remove object from room floor."""
        if not obj:
            return
        room_vnum = getattr(obj, "room_vnum", None)
        if room_vnum is not None:
            room = self._engine.world.get_room(room_vnum)
            if room and obj in room.objects:
                room.objects.remove(obj)
            obj.room_vnum = None
        else:
            # Fallback: search current character's room
            char = self._session.character
            if char:
                room = self._engine.world.get_room(char.room_vnum)
                if room and obj in room.objects:
                    room.objects.remove(obj)

    def purge_room(self) -> None:
        """Remove all NPCs and objects from current character's room."""
        char = self._session.character if self._session else None
        if not char:
            return
        room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return
        room.characters = [ch for ch in room.characters if not ch.is_npc]
        room.objects.clear()

    def get_inv_count(self) -> int:
        """Get inventory count for current character (Lua # workaround)."""
        char = self._session.character if self._session else None
        if not char:
            return 0
        return len(char.inventory)

    def remove_char_from_room(self, char: Any) -> None:
        """Remove a character from their current room."""
        if not char:
            return
        room = self._engine.world.get_room(char.room_vnum)
        if room and char in room.characters:
            room.characters.remove(char)

    def equip(self, obj: Any, slot: int) -> None:
        char = self._session.character
        if char and obj:
            obj.worn_by = char
            obj.wear_pos = int(slot)
            char.equipment[int(slot)] = obj

    def unequip(self, slot: int) -> Any:
        char = self._session.character
        if not char:
            return None
        slot = int(slot)
        obj = char.equipment.pop(slot, None)
        if obj:
            obj.worn_by = None
            obj.wear_pos = -1
            char.inventory.append(obj)
        return obj

    def apply_affect(self, target: Any, affect_id: int, duration: int, mods: Any = None) -> None:
        if target:
            affect = {
                "id": int(affect_id),
                "duration": int(duration),
            }
            if mods:
                affect["modifiers"] = dict(mods) if hasattr(mods, "items") else {}
            target.affects.append(affect)

    def remove_affect(self, target: Any, affect_id: int) -> None:
        if target:
            target.affects = [a for a in target.affects if a.get("id") != int(affect_id)]

    def has_affect(self, target: Any, affect_id: int) -> bool:
        if not target:
            return False
        return any(a.get("id") == int(affect_id) for a in target.affects)

    def deal_damage(self, target: Any, amount: int) -> None:
        if target:
            target.hp -= int(amount)

    def heal(self, target: Any, amount: int) -> None:
        if target:
            target.hp = min(target.max_hp, target.hp + int(amount))

    # ── Spell affect system (spell_id key, matches spells.py) ───

    def has_spell_affect(self, target: Any, spell_id: int) -> bool:
        """Check if target has spell affect (using spell_id key)."""
        if not target:
            return False
        sid = int(spell_id)
        return any(a.get("spell_id") == sid for a in target.affects)

    def apply_spell_buff(self, target: Any, spell_id: int, duration: int,
                         mods: Any = None) -> None:
        """Apply spell buff. Replaces existing same-spell affect.

        mods can be a Lua table or dict of modifiers.
        """
        if not target:
            return
        sid = int(spell_id)
        dur = int(duration)
        target.affects = [a for a in target.affects if a.get("spell_id") != sid]
        affect: dict[str, Any] = {"spell_id": sid, "duration": dur}
        if mods is not None:
            try:
                for k, v in mods.items():
                    affect[str(k)] = v
            except (AttributeError, TypeError):
                pass
        target.affects.append(affect)

    def remove_spell_affect(self, target: Any, spell_id: int) -> None:
        """Remove spell affect by spell_id."""
        if target:
            sid = int(spell_id)
            target.affects = [a for a in target.affects
                              if a.get("spell_id") != sid]

    def get_skill_proficiency(self, char: Any, skill_id: int) -> int:
        """Get skill proficiency for a character."""
        if not char or not hasattr(char, "skills"):
            return 0
        return char.skills.get(int(skill_id), 0)

    def get_start_room(self) -> int:
        """Get the configured start room vnum."""
        return self._engine.config.get("world", {}).get("start_room", 3001)

    def move_char_to(self, char: Any, room_vnum: int) -> None:
        """Move any character to a room (not just ctx.char)."""
        if not char:
            return
        rv = int(room_vnum)
        old_room = self._engine.world.get_room(char.room_vnum)
        if old_room and char in old_room.characters:
            old_room.characters.remove(char)
        char.room_vnum = rv
        new_room = self._engine.world.get_room(rv)
        if new_room:
            new_room.characters.append(char)

    def start_combat(self, target: Any) -> None:
        char = self._session.character
        if char and target:
            char.fighting = target
            char.position = 7  # POS_FIGHTING
            if not target.fighting:
                target.fighting = char
                target.position = 7

    def stop_combat(self, char: Any) -> None:
        if char:
            if char.fighting:
                if char.fighting.fighting is char:
                    char.fighting.fighting = None
                    char.fighting.position = 8  # POS_STANDING
                char.fighting = None
                char.position = 8

    # ── Deferred actions ──────────────────────────────────────────

    def defer_look(self) -> None:
        self._deferred.append(("look", ()))

    def defer_death(self, victim: Any, killer: Any) -> None:
        self._deferred.append(("death", (victim, killer)))

    def defer_save(self) -> None:
        self._deferred.append(("save", ()))

    # ── Utilities ─────────────────────────────────────────────────

    def random(self, a: int, b: int) -> int:
        return random.randint(int(a), int(b))

    def roll_dice(self, dice_str: str) -> int:
        from core.world import _roll_dice
        return _roll_dice(str(dice_str))

    def is_admin(self) -> bool:
        pd = self._session.player_data
        return pd.get("level", 1) >= 34

    def particle(self, word: str, p1: str, p2: str) -> str:
        """Select Korean particle based on batchim."""
        return p1 if has_batchim(str(word)) else p2

    def log(self, msg: str) -> None:
        log.info("[Lua] %s", msg)

    def call_command(self, cmd: str, args: str = "") -> None:
        """Call another Lua command synchronously within the same context."""
        lua_rt = self._engine.lua
        if lua_rt and lua_rt.has_command(str(cmd)):
            fn = lua_rt._commands.get(str(cmd))
            if fn:
                fn(self, str(args))

    # ── Zone / World search ────────────────────────────────────────

    def get_zone_chars(self, zone_number: int | None = None, keyword: str | None = None) -> Any:
        """Get characters in the same zone. Returns Lua table of {char, room_name}."""
        char = self._session.character
        if not char:
            return self._to_lua_table([])
        if zone_number is None:
            room = self._engine.world.get_room(char.room_vnum)
            if not room:
                return self._to_lua_table([])
            zone_number = room.proto.zone_number
        kw = str(keyword).lower() if keyword else None
        results = []
        for rm in self._engine.world.rooms.values():
            if rm.proto.zone_number != int(zone_number):
                continue
            for ch in rm.characters:
                if ch is char:
                    continue
                if kw:
                    if kw not in ch.proto.keywords.lower() and \
                       (not ch.player_name or kw not in ch.player_name.lower()):
                        continue
                results.append({"char": ch, "room_name": rm.proto.name})
        return self._to_lua_table(results)

    def find_world_char(self, name: str) -> MobInstance | None:
        """Find a character anywhere in the world by player name."""
        name_lower = str(name).lower()
        for room in self._engine.world.rooms.values():
            for ch in room.characters:
                if ch.player_name and ch.player_name.lower() == name_lower:
                    return ch
        return None

    def find_shop(self) -> Any:
        """Find shop in current room. Returns (shop_info_table, keeper_mob) or (nil, nil).

        shop_info is a Lua-friendly table with selling_items as Lua table.
        """
        char = self._session.character
        if not char:
            return None, None
        room = self._engine.world.get_room(char.room_vnum)
        if not room:
            return None, None
        for mob in room.characters:
            if mob.is_npc and mob.proto.vnum in self._engine.world.shops:
                shop = self._engine.world.shops[mob.proto.vnum]
                # Build Lua-friendly table
                info = {
                    "selling_items": self._to_lua_table(list(shop.selling_items)),
                    "profit_buy": shop.profit_buy,
                    "profit_sell": shop.profit_sell,
                    "open1": shop.open1,
                    "close1": shop.close1,
                    "open2": shop.open2,
                    "close2": shop.close2,
                }
                if self._lua:
                    return self._lua.table_from(info), mob
                return info, mob
        return None, None

    def defer_reload(self) -> None:
        self._deferred.append(("reload", ()))

    def defer_shutdown(self) -> None:
        self._deferred.append(("shutdown", ()))

    # ── Flush (called from Python after Lua returns) ──────────────

    async def flush(self) -> None:
        """Send all buffered messages."""
        for target_session, text in self._messages:
            if target_session:
                await target_session.send_line(text)
        self._messages.clear()

    async def execute_deferred(self) -> None:
        """Execute deferred actions after Lua completes."""
        for action, args in self._deferred:
            if action == "look":
                # Call Lua look command via engine's command handler
                handler = self._engine.cmd_handlers.get("look")
                if handler:
                    await handler(self._session, "")
            elif action == "death":
                victim, killer = args
                # Use plugin death handler if available
                plugin = getattr(self._engine, "_plugin", None)
                if plugin and hasattr(plugin, "handle_death"):
                    await plugin.handle_death(self._engine, victim, killer)
                else:
                    # Fallback: game-specific death handler + level up
                    try:
                        from games.tbamud.combat.death import handle_death
                        from games.tbamud.level import check_level_up, do_level_up
                        await handle_death(self._engine, victim, killer=killer)
                        if killer and not killer.is_npc and check_level_up(killer):
                            send_fn = killer.session.send_line if killer.session else None
                            await do_level_up(killer, send_fn=send_fn)
                    except ImportError:
                        log.warning("No death handler available for deferred death")
            elif action == "save":
                await self._session.save_character()
            elif action == "reload":
                engine = self._engine
                if hasattr(engine, "reload_mgr"):
                    engine.reload_mgr.queue_game_reload(engine.game_name)
                    reloaded = engine.reload_mgr.apply_pending()
                    if reloaded and self._session:
                        await self._session.send_line(
                            f"리로드 완료: {', '.join(reloaded)}"
                        )
                    elif self._session:
                        await self._session.send_line("리로드할 모듈이 없습니다.")
            elif action == "shutdown":
                if hasattr(self._engine, "shutdown"):
                    await self._engine.shutdown()
            elif action == "close_conn":
                await self._session.conn.close()
        self._deferred.clear()


# ── HookContext (for combat hooks, similar to CommandContext) ─────


class HookContext(CommandContext):
    """Context for hook calls (combat, tick, etc.) where there may be no single session."""

    def __init__(self, engine: Engine, room: Room) -> None:
        # Create a dummy session-like object
        self._engine = engine
        self._room = room
        self._session = None  # type: ignore[assignment]
        self._messages: list[tuple[Session | None, str]] = []
        self._deferred: list[tuple[str, tuple]] = []

    @property
    def char(self) -> None:
        return None

    def send(self, msg: str) -> None:
        """In hook context, send to all in room."""
        for ch in self._room.characters:
            if ch.session:
                self._messages.append((ch.session, str(msg)))


# ── LuaCommandRuntime ────────────────────────────────────────────


class LuaCommandRuntime:
    """Manages Lua runtime, command registration, and hook dispatching."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._lua = LuaRuntime(unpack_returned_tuples=True)
        self._commands: dict[str, Any] = {}       # cmd_name → lua function
        self._korean_cmds: dict[str, str] = {}    # korean_name → cmd_name
        self._hooks: dict[str, list[Any]] = {}    # hook_name → [lua functions]
        self._loaded_scripts: dict[str, str] = {} # "game/category/name" → source

        # Set up Lua globals
        self._setup_lua_env()

    def _setup_lua_env(self) -> None:
        """Initialize Lua environment with register_command/register_hook globals."""
        lua = self._lua
        runtime = self

        # register_command(name, func, korean_name?)
        def register_command(name: str, func: Any, korean_name: str | None = None) -> None:
            name = str(name)
            runtime._commands[name] = func
            if korean_name:
                korean_name = str(korean_name)
                runtime._korean_cmds[korean_name] = name
            log.debug("Lua command registered: %s%s",
                      name, f" ({korean_name})" if korean_name else "")

        lua.globals()["register_command"] = register_command

        # register_hook(hook_name, func)
        def register_hook(hook_name: str, func: Any) -> None:
            hook_name = str(hook_name)
            if hook_name not in runtime._hooks:
                runtime._hooks[hook_name] = []
            runtime._hooks[hook_name].append(func)
            log.debug("Lua hook registered: %s", hook_name)

        lua.globals()["register_hook"] = register_hook

    # ── Loading from DB ──────────────────────────────────────────

    async def load_from_db(self, db: Database, game_name: str) -> int:
        """Load Lua scripts from DB. Loads common first, then game-specific."""
        count = 0
        for scope in ("common", game_name):
            rows = await db.fetch_lua_scripts(scope)
            for row in rows:
                key = f"{row['game']}/{row['category']}/{row['name']}"
                try:
                    self._lua.execute(row["source"])
                    self._loaded_scripts[key] = row["source"]
                    count += 1
                except Exception as e:
                    log.error("Failed to load Lua script %s: %s", key, e)
        return count

    async def seed_from_files(self, db: Database, game_name: str) -> int:
        """Import seed Lua files from games/*/lua/ into DB."""
        from core.engine import BASE_DIR
        count = 0
        for scope in ("common", game_name):
            lua_dir = BASE_DIR / "games" / scope / "lua"
            if not lua_dir.exists():
                continue
            for lua_file in sorted(lua_dir.rglob("*.lua")):
                rel = lua_file.relative_to(lua_dir)
                parts = list(rel.parts)
                name = parts[-1].replace(".lua", "")
                category = "/".join(parts[:-1]) if len(parts) > 1 else "lib"
                source = lua_file.read_text(encoding="utf-8")
                await db.upsert_lua_script(
                    game=scope, category=category, name=name, source=source,
                )
                count += 1
                log.debug("Seeded Lua: %s/%s/%s", scope, category, name)
        return count

    def load_source(self, source: str, key: str = "<inline>") -> None:
        """Execute a Lua source string (registers commands/hooks)."""
        try:
            self._lua.execute(source)
            self._loaded_scripts[key] = source
        except Exception as e:
            log.error("Failed to load Lua source %s: %s", key, e)
            raise

    def reload_script(self, source: str, key: str = "<inline>") -> None:
        """Reload a single script — re-execute to update registrations."""
        self.load_source(source, key)

    # ── Command dispatch ─────────────────────────────────────────

    def has_command(self, name: str) -> bool:
        return name in self._commands

    def get_korean_cmd(self, korean: str) -> str | None:
        return self._korean_cmds.get(korean)

    def wrap_command(self, cmd_name: str) -> Any:
        """Create an async Python handler that wraps a Lua command function."""
        lua_fn = self._commands.get(cmd_name)
        if lua_fn is None:
            return None

        async def handler(session: Session, args: str) -> None:
            ctx = CommandContext(session, self.engine, lua_runtime=self._lua)
            try:
                lua_fn(ctx, args)
            except Exception as e:
                log.error("Lua command '%s' error: %s", cmd_name, e)
                ctx.send("{red}명령어 실행 중 오류가 발생했습니다.{reset}")
            await ctx.flush()
            await ctx.execute_deferred()

        return handler

    def register_all_commands(self) -> None:
        """Register all Lua commands with the engine's command dispatcher."""
        for cmd_name in self._commands:
            handler = self.wrap_command(cmd_name)
            if handler:
                korean = None
                # Check if this command has a Korean mapping
                for kr, eng in self._korean_cmds.items():
                    if eng == cmd_name:
                        korean = kr
                        break
                self.engine.register_command(cmd_name, handler, korean=korean)

    # ── Hook dispatch ────────────────────────────────────────────

    def fire_hook(self, hook_name: str, ctx: CommandContext, *args: Any) -> None:
        """Fire all registered hooks for the given name (synchronous)."""
        hooks = self._hooks.get(hook_name, [])
        for hook_fn in hooks:
            try:
                hook_fn(ctx, *args)
            except Exception as e:
                log.error("Lua hook '%s' error: %s", hook_name, e)

    def has_hook(self, hook_name: str) -> bool:
        return bool(self._hooks.get(hook_name))

    # ── Info ─────────────────────────────────────────────────────

    @property
    def command_count(self) -> int:
        return len(self._commands)

    @property
    def hook_count(self) -> int:
        return sum(len(v) for v in self._hooks.values())

    @property
    def loaded_scripts(self) -> dict[str, str]:
        return dict(self._loaded_scripts)
