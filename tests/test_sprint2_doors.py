"""Sprint 2 tests — door system (open, close, lock, unlock)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine, REVERSE_DIRS
from core.world import (
    Exit, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World,
)


def _make_door_world():
    """World with a door between rooms 1 and 2 (north/south)."""
    w = World()
    # Room 1 has a closed, locked door to the north → Room 2
    room1 = RoomProto(
        vnum=1, name="남쪽 방", description="남쪽 방입니다.",
        zone_vnum=0, sector=0, flags=[],
        exits=[Exit(direction=0, to_vnum=2, keywords="door", flags=("door", "closed", "locked"), key_vnum=100)],
        extra_descs=[], scripts=[],
    )
    # Room 2 has a closed, locked door to the south → Room 1
    room2 = RoomProto(
        vnum=2, name="북쪽 방", description="북쪽 방입니다.",
        zone_vnum=0, sector=0, flags=[],
        exits=[Exit(direction=2, to_vnum=1, keywords="door", flags=("door", "closed", "locked"), key_vnum=100)],
        extra_descs=[], scripts=[],
    )
    w.rooms[1] = Room(proto=room1)
    w.rooms[2] = Room(proto=room2)
    w.rooms[1].init_doors()
    w.rooms[2].init_doors()

    # Create a key item
    key_proto = ItemProto(
        vnum=100, keywords="key 열쇠", short_desc="작은 열쇠",
        long_desc="작은 열쇠가 놓여있습니다.", item_type="key",
        flags=[], wear_slots=[], values={},
        weight=1, cost=0, affects=[], extra_descs=[], scripts=[],
    )
    w.item_protos[100] = key_proto
    return w


def _load_common_lua(eng):
    """Load common Lua commands into engine for testing."""
    from core.lua_commands import LuaCommandRuntime
    from pathlib import Path
    eng.lua = LuaCommandRuntime(eng)
    lua_dir = Path(__file__).resolve().parent.parent / "games" / "common" / "lua"
    lib = lua_dir / "lib.lua"
    if lib.exists():
        eng.lua.load_source(lib.read_text(encoding="utf-8"), "lib")
    cmd_dir = lua_dir / "commands"
    if cmd_dir.exists():
        for f in sorted(cmd_dir.glob("*.lua")):
            eng.lua.load_source(f.read_text(encoding="utf-8"), f"cmd/{f.stem}")
    eng.lua.register_all_commands()


def _make_session(eng, room_vnum=1):
    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.engine = eng
    session.player_data = {"id": 1, "name": "테스터", "level": 1, "aliases": {}}

    proto = MobProto(
        vnum=-1, keywords="테스터", short_desc="테스터",
        long_desc="", detail_desc="",
        level=1, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0,
        scripts=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=room_vnum, hp=20, max_hp=20,
        player_id=1, player_name="테스터", session=session,
    )
    session.character = char
    eng.world.rooms[room_vnum].characters.append(char)
    return session


def _make_engine(world):
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 1}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    _load_common_lua(eng)
    eng.game_name = "tbamud"
    return eng


class TestDoorState:
    def test_init_doors(self):
        w = _make_door_world()
        room = w.rooms[1]
        assert room.has_door(0)
        assert room.is_door_closed(0)
        assert room.is_door_locked(0)

    def test_no_door_direction(self):
        w = _make_door_world()
        room = w.rooms[1]
        assert not room.has_door(1)  # east — no door
        assert not room.is_door_closed(1)

    def test_both_sides(self):
        w = _make_door_world()
        assert w.rooms[1].is_door_locked(0)
        assert w.rooms[2].is_door_locked(2)


class TestMoveBlockedByDoor:
    @pytest.mark.asyncio
    async def test_cannot_pass_closed_door(self):
        w = _make_door_world()
        eng = _make_engine(w)
        session = _make_session(eng)
        char = session.character

        await eng.do_move(session, "north")
        assert char.room_vnum == 1  # didn't move
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("닫혀" in c for c in calls)

    @pytest.mark.asyncio
    async def test_can_pass_open_door(self):
        w = _make_door_world()
        eng = _make_engine(w)
        # Manually open door
        w.rooms[1].door_states[0]["closed"] = False
        w.rooms[1].door_states[0]["locked"] = False
        session = _make_session(eng)
        char = session.character

        await eng.do_move(session, "north")
        assert char.room_vnum == 2


class TestOpenCommand:
    @pytest.mark.asyncio
    async def test_open_locked_door(self):
        w = _make_door_world()
        eng = _make_engine(w)
        session = _make_session(eng)

        await eng.cmd_handlers["open"](session, "북")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("잠겨" in c for c in calls)

    @pytest.mark.asyncio
    async def test_open_unlocked_door(self):
        w = _make_door_world()
        eng = _make_engine(w)
        w.rooms[1].door_states[0]["locked"] = False
        session = _make_session(eng)

        await eng.cmd_handlers["open"](session, "북")
        assert not w.rooms[1].is_door_closed(0)
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("열었습니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_open_already_open(self):
        w = _make_door_world()
        eng = _make_engine(w)
        w.rooms[1].door_states[0]["closed"] = False
        w.rooms[1].door_states[0]["locked"] = False
        session = _make_session(eng)

        await eng.cmd_handlers["open"](session, "북")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("이미 열려" in c for c in calls)


class TestCloseCommand:
    @pytest.mark.asyncio
    async def test_close_open_door(self):
        w = _make_door_world()
        eng = _make_engine(w)
        w.rooms[1].door_states[0]["closed"] = False
        w.rooms[1].door_states[0]["locked"] = False
        session = _make_session(eng)

        await eng.cmd_handlers["close"](session, "북")
        assert w.rooms[1].is_door_closed(0)

    @pytest.mark.asyncio
    async def test_close_already_closed(self):
        w = _make_door_world()
        eng = _make_engine(w)
        session = _make_session(eng)

        await eng.cmd_handlers["close"](session, "북")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("이미 닫혀" in c for c in calls)


class TestLockUnlock:
    @pytest.mark.asyncio
    async def test_unlock_with_key(self):
        w = _make_door_world()
        eng = _make_engine(w)
        session = _make_session(eng)
        char = session.character

        # Give player the key
        key_obj = ObjInstance(id=99, proto=w.item_protos[100])
        char.inventory.append(key_obj)

        await eng.cmd_handlers["unlock"](session, "북")
        assert not w.rooms[1].is_door_locked(0)
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("자물쇠" in c for c in calls)

    @pytest.mark.asyncio
    async def test_unlock_without_key(self):
        w = _make_door_world()
        eng = _make_engine(w)
        session = _make_session(eng)

        await eng.cmd_handlers["unlock"](session, "북")
        assert w.rooms[1].is_door_locked(0)  # still locked
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("열쇠" in c for c in calls)

    @pytest.mark.asyncio
    async def test_lock_closed_door(self):
        w = _make_door_world()
        eng = _make_engine(w)
        w.rooms[1].door_states[0]["locked"] = False
        session = _make_session(eng)
        char = session.character

        key_obj = ObjInstance(id=99, proto=w.item_protos[100])
        char.inventory.append(key_obj)

        await eng.cmd_handlers["lock"](session, "북")
        assert w.rooms[1].is_door_locked(0)

    @pytest.mark.asyncio
    async def test_lock_open_door(self):
        w = _make_door_world()
        eng = _make_engine(w)
        w.rooms[1].door_states[0]["closed"] = False
        w.rooms[1].door_states[0]["locked"] = False
        session = _make_session(eng)

        await eng.cmd_handlers["lock"](session, "북")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("닫아야" in c for c in calls)
