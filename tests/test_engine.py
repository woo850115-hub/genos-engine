"""Tests for engine — command dispatch, direction handling, zone resets."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.engine import (
    DIR_ABBREV, DIR_NAMES_KR, DIR_NAMES_KR_MAP, DIRS, REVERSE_DIRS, Engine,
)
from core.world import (
    Exit, MobInstance, MobProto, Room, RoomProto, World, Zone,
)


class TestDirectionConstants:
    def test_dir_count(self):
        assert len(DIRS) == 6
        assert len(DIR_NAMES_KR) == 6

    def test_abbreviations(self):
        assert DIR_ABBREV["n"] == 0
        assert DIR_ABBREV["s"] == 2

    def test_korean_map(self):
        assert DIR_NAMES_KR_MAP["북"] == 0
        assert DIR_NAMES_KR_MAP["남"] == 2
        assert DIR_NAMES_KR_MAP["위"] == 4

    def test_reverse_dirs(self):
        assert REVERSE_DIRS[0] == 2  # north ↔ south
        assert REVERSE_DIRS[1] == 3  # east ↔ west
        assert REVERSE_DIRS[4] == 5  # up ↔ down


def _make_engine_with_rooms():
    """Create a minimal engine with two connected rooms for testing."""
    world = World()

    # Room 1 → Room 2 via north
    room1_proto = RoomProto(
        vnum=3001, name="신전", description="광대한 신전입니다.",
        zone_number=30, sector_type=0, room_flags=[],
        exits=[Exit(direction=0, to_room=3002)],
        extra_descs=[], trigger_vnums=[],
    )
    room2_proto = RoomProto(
        vnum=3002, name="길", description="좁은 길입니다.",
        zone_number=30, sector_type=0, room_flags=[],
        exits=[Exit(direction=2, to_room=3001)],
        extra_descs=[], trigger_vnums=[],
    )
    world.rooms[3001] = Room(proto=room1_proto)
    world.rooms[3002] = Room(proto=room2_proto)
    return world


def _make_session(engine, room_vnum=3001):
    """Create a mock session with a character."""
    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.engine = engine
    session.player_data = {"id": 1, "name": "테스터", "level": 1, "class_id": 0}

    proto = MobProto(
        vnum=-1, keywords="테스터", short_description="테스터",
        long_description="", detailed_description="",
        level=1, hitroll=0, armor_class=100, hp_dice="0d0+0",
        damage_dice="1d4+0", gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=0,
        trigger_vnums=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=room_vnum,
        hp=20, max_hp=20, player_id=1, player_name="테스터",
        session=session,
    )
    session.character = char
    engine.world.rooms[room_vnum].characters.append(char)
    return session


class TestCommandDispatch:
    @pytest.fixture
    def engine(self):
        world = _make_engine_with_rooms()
        eng = MagicMock(spec=Engine)
        eng.world = world
        eng.config = {"world": {"start_room": 3001}}
        eng.sessions = {}
        eng.players = {}
        eng.cmd_handlers = {}
        eng.cmd_korean = {}
        return eng

    def test_register_command(self, engine):
        real_engine = Engine.__new__(Engine)
        real_engine.cmd_handlers = {}
        real_engine.cmd_korean = {}
        handler = AsyncMock()
        real_engine.register_command("test", handler, korean="테스트")
        assert "test" in real_engine.cmd_handlers
        assert real_engine.cmd_korean["테스트"] == "test"


class TestDoLook:
    @pytest.mark.asyncio
    async def test_look_shows_room_name(self):
        world = _make_engine_with_rooms()
        eng = MagicMock()
        eng.world = world
        eng.config = {}
        eng.sessions = {}
        eng.players = {}

        real_engine = Engine.__new__(Engine)
        real_engine.world = world
        real_engine.config = {}
        real_engine.sessions = {}
        real_engine.players = {}
        real_engine.cmd_handlers = {}
        real_engine.cmd_korean = {}
        real_engine._register_core_commands()

        session = _make_session(real_engine)

        await real_engine.do_look(session, "")
        # Check that room name was sent
        calls = session.send_line.call_args_list
        found_name = any("신전" in str(c) for c in calls)
        assert found_name


class TestDoMove:
    def _make_engine(self):
        world = _make_engine_with_rooms()
        real_engine = Engine.__new__(Engine)
        real_engine.world = world
        real_engine.cmd_handlers = {}
        return real_engine

    @pytest.mark.asyncio
    async def test_move_north(self):
        real_engine = self._make_engine()
        session = _make_session(real_engine)
        char = session.character

        assert char.room_vnum == 3001
        await real_engine.do_move(session, "north")
        assert char.room_vnum == 3002

    @pytest.mark.asyncio
    async def test_move_korean(self):
        real_engine = self._make_engine()
        session = _make_session(real_engine)
        char = session.character

        await real_engine.do_move(session, "북")
        assert char.room_vnum == 3002

    @pytest.mark.asyncio
    async def test_move_abbreviation(self):
        real_engine = self._make_engine()
        session = _make_session(real_engine)
        char = session.character

        await real_engine.do_move(session, "n")
        assert char.room_vnum == 3002

    @pytest.mark.asyncio
    async def test_move_no_exit(self):
        real_engine = self._make_engine()
        session = _make_session(real_engine)
        char = session.character

        await real_engine.do_move(session, "east")
        assert char.room_vnum == 3001  # didn't move
        calls = session.send_line.call_args_list
        found_msg = any("갈 수 없습니다" in str(c) for c in calls)
        assert found_msg


class TestZoneReset:
    def test_execute_zone_commands_mob(self):
        world = _make_engine_with_rooms()
        # Add mob proto
        mob_proto = MobProto(
            vnum=100, keywords="rat", short_description="A rat",
            long_description="A rat scurries.", detailed_description="",
            level=1, hitroll=0, armor_class=100, hp_dice="1d4+2",
            damage_dice="1d2+0", gold=0, experience=5,
            action_flags=[], affect_flags=[], alignment=0, sex=0,
            trigger_vnums=[],
        )
        world.mob_protos[100] = mob_proto

        zone = Zone(
            vnum=30, name="Test Zone", builders="", lifespan=30,
            bot=3001, top=3002, reset_mode=2, zone_flags=[],
            reset_commands=[
                {"command": "M", "if_flag": 0, "arg1": 100, "arg2": 5, "arg3": 3001},
            ],
        )
        world.zones.append(zone)

        real_engine = Engine.__new__(Engine)
        real_engine.world = world
        real_engine._execute_zone_commands(zone)

        # Should have spawned a mob in room 3001
        assert len(world.rooms[3001].characters) == 1
        assert world.rooms[3001].characters[0].proto.vnum == 100
