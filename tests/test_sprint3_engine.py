"""Sprint 3 tests — engine combat integration (cast, combat round, score)."""

import pytest
import random
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine
from core.world import (
    Exit, GameClass, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World,
)


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


def _make_world():
    w = World()
    room = RoomProto(
        vnum=3001, name="신전", description="넓은 신전입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[],
    )
    w.rooms[3001] = Room(proto=room)
    # Add tbaMUD classes for score tests
    w.classes = {
        0: GameClass(id=0, name="마법사", abbrev="마법", hp_gain=(3, 8)),
        1: GameClass(id=1, name="성직자", abbrev="성직", hp_gain=(5, 10)),
        2: GameClass(id=2, name="도적", abbrev="도적", hp_gain=(6, 11)),
        3: GameClass(id=3, name="전사", abbrev="전사", hp_gain=(10, 15)),
    }
    return w


def _make_engine_session(world=None):
    if world is None:
        world = _make_world()
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 3001}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    _load_common_lua(eng)
    eng._load_korean_mappings()
    eng.game_name = "tbamud"

    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.engine = eng
    session.player_data = {"id": 1, "name": "테스터", "level": 10, "sex": 1, "aliases": {}}

    proto = MobProto(
        vnum=-1, keywords="테스터", short_desc="테스터",
        long_desc="", detail_desc="",
        level=10, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0,
        scripts=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=3001, hp=100, max_hp=100,
        mana=100, max_mana=100, player_id=1, player_name="테스터",
        class_id=0, player_level=10, session=session,
    )
    session.character = char
    world.rooms[3001].characters.append(char)
    return eng, session


def _add_mob(world, vnum=50, level=5, hp=20, room_vnum=3001):
    proto = MobProto(
        vnum=vnum, keywords="goblin 고블린", short_desc="고블린",
        long_desc="고블린이 서 있습니다.", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=2,
        damage_dice="1d4+0", gold=10, experience=100,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[],
    )
    mob = MobInstance(id=vnum, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=hp)
    world.rooms[room_vnum].characters.append(mob)
    return mob


class TestCastCommand:
    @pytest.mark.asyncio
    async def test_cast_no_args(self):
        eng, session = _make_engine_session()
        await eng.do_cast(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("주문" in c for c in calls)

    @pytest.mark.asyncio
    async def test_cast_unknown_spell(self):
        eng, session = _make_engine_session()
        await eng.do_cast(session, "xyzzy")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("모릅니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_cast_offensive_spell(self):
        eng, session = _make_engine_session()
        mob = _add_mob(eng.world)
        await eng.do_cast(session, "매직미사일 goblin")
        assert mob.hp < 20

    @pytest.mark.asyncio
    async def test_cast_heal_self(self):
        eng, session = _make_engine_session()
        session.character.class_id = 1  # Cleric
        session.character.player_level = 16
        session.character.hp = 50
        await eng.do_cast(session, "치유")
        assert session.character.hp > 50

    @pytest.mark.asyncio
    async def test_cast_not_enough_mana(self):
        eng, session = _make_engine_session()
        session.character.mana = 0
        await eng.do_cast(session, "매직미사일 goblin")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("마나" in c for c in calls)

    @pytest.mark.asyncio
    async def test_cast_word_of_recall(self):
        w = _make_world()
        room2 = RoomProto(
            vnum=3002, name="들판", description="들판.",
            zone_vnum=30, sector=0, flags=[],
            exits=[], extra_descs=[], scripts=[],
        )
        w.rooms[3002] = Room(proto=room2)

        eng, session = _make_engine_session(w)
        session.character.class_id = 1
        session.character.player_level = 12
        # Move to room 3002
        char = session.character
        w.rooms[3001].characters.remove(char)
        char.room_vnum = 3002
        w.rooms[3002].characters.append(char)

        await eng.do_cast(session, "귀환")
        assert char.room_vnum == 3001


class TestCombatRound:
    @pytest.mark.asyncio
    async def test_combat_round_deals_damage(self):
        eng, session = _make_engine_session()
        mob = _add_mob(eng.world, hp=1000)
        session.character.fighting = mob
        mob.fighting = session.character

        random.seed(42)
        await eng._combat_round()
        # At least one round should do something
        assert mob.hp <= 1000 or session.character.hp <= 100

    @pytest.mark.asyncio
    async def test_combat_round_kills_mob(self):
        eng, session = _make_engine_session()
        mob = _add_mob(eng.world, hp=1)
        session.character.fighting = mob
        mob.fighting = session.character
        session.character.player_level = 20

        # Ensure hit
        orig = random.randint
        random.randint = lambda a, b: 20 if b == 20 else orig(a, b)
        try:
            await eng._combat_round()
        finally:
            random.randint = orig

        assert session.character.fighting is None
        assert mob not in eng.world.rooms[3001].characters


class TestPracticeCommand:
    @pytest.mark.asyncio
    async def test_practice_shows_spells(self):
        eng, session = _make_engine_session()
        session.character.class_id = 0
        session.character.player_level = 10
        await eng.do_practice(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("주문" in c or "매직미사일" in c for c in calls)


class TestScoreCommand:
    @pytest.mark.asyncio
    async def test_score_shows_info(self):
        eng, session = _make_engine_session()
        await eng.cmd_handlers["score"](session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("테스터" in c for c in calls)
        assert any("레벨" in c for c in calls)

    @pytest.mark.asyncio
    async def test_score_shows_class(self):
        eng, session = _make_engine_session()
        session.character.class_id = 3
        await eng.cmd_handlers["score"](session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("전사" in c for c in calls)
