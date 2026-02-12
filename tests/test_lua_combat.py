"""Tests for Lua combat system — thac0, spells, cast, practice, combat_round hook."""

import pytest
import random
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine
from core.lua_commands import LuaCommandRuntime, CommandContext, HookContext
from core.world import (
    Exit, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World,
)


# ── Helpers ───────────────────────────────────────────────────


def _load_lua(eng):
    """Load all Lua scripts including combat."""
    eng.lua = LuaCommandRuntime(eng)
    base = Path(__file__).resolve().parent.parent / "games"
    for scope in ("common", "tbamud"):
        lua_dir = base / scope / "lua"
        lib = lua_dir / "lib.lua"
        if lib.exists():
            eng.lua.load_source(lib.read_text(encoding="utf-8"), f"{scope}/lib")
        for subdir in ("commands", "combat"):
            sub_path = lua_dir / subdir
            if sub_path.exists():
                for f in sorted(sub_path.glob("*.lua")):
                    eng.lua.load_source(f.read_text(encoding="utf-8"),
                                        f"{scope}/{subdir}/{f.stem}")
    eng.lua.register_all_commands()


def _make_world():
    w = World()
    room1 = RoomProto(
        vnum=3001, name="신전", description="넓은 신전입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[], ext={})
    room2 = RoomProto(
        vnum=3002, name="들판", description="넓은 들판입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[], ext={})
    w.rooms[3001] = Room(proto=room1)
    w.rooms[3002] = Room(proto=room2)
    return w


def _make_engine(world=None):
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
    eng.game_name = "tbamud"
    _load_lua(eng)
    return eng


def _make_session(eng, char):
    session = MagicMock()
    session.send_line = AsyncMock()
    session.character = char
    session.engine = eng
    session.player_data = {"level": char.level}
    char.session = session
    return session


def _player(level=10, class_id=0, mana=200, hp=100, max_hp=100,
            exp=0, gold=50, room_vnum=3002):
    proto = MobProto(
        vnum=-1, keywords="테스터", short_desc="테스터",
        long_desc="", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
    ch = MobInstance(
        id=1, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=max_hp,
        mana=mana, max_mana=mana, gold=gold, experience=exp,
        player_id=1, player_name="테스터", class_id=class_id,
        player_level=level,
    )
    return ch


def _npc(level=5, hp=50, gold=20, exp=100, room_vnum=3002):
    proto = MobProto(
        vnum=50, keywords="goblin 고블린", short_desc="고블린",
        long_desc="", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=2,
        damage_dice="1d4+0", gold=gold, experience=exp,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
    return MobInstance(
        id=50, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=hp, gold=gold,
    )


def _get_sent(session):
    """Extract all sent messages from mock session."""
    return [str(c) for c in session.send_line.call_args_list]


# ── Combat round hook tests ───────────────────────────────────


class TestLuaCombatRoundHook:
    def test_hook_registered(self):
        eng = _make_engine()
        assert eng.lua.has_hook("combat_round")

    @pytest.mark.asyncio
    async def test_combat_round_deals_damage(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=20, class_id=3, room_vnum=3002)
        mob = _npc(level=1, hp=100, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7  # POS_FIGHTING

        await eng._lua_combat_round()

        # Some damage should have been dealt (or missed)
        msgs = _get_sent(session)
        assert any("빗나" in m or "입힙니다" in m for m in msgs) or mob.hp < 100

    @pytest.mark.asyncio
    async def test_combat_round_kills_npc(self):
        """When mob dies from combat, defer_death should trigger."""
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=30, class_id=3, room_vnum=3002, exp=0)
        ch.hitroll = 20
        mob = _npc(level=1, hp=1, gold=10, exp=200, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        # Force roll 20 to guarantee hit
        orig = random.randint
        random.randint = lambda a, b: 20 if b == 20 else orig(a, b)
        try:
            await eng._lua_combat_round()
        finally:
            random.randint = orig

        # After death: combat cleared, mob removed from room
        assert ch.fighting is None
        assert mob not in w.rooms[3002].characters
        # Exp awarded
        assert ch.experience > 0


# ── Cast command tests ────────────────────────────────────────


class TestLuaCastCommand:
    @pytest.mark.asyncio
    async def test_cast_registered(self):
        eng = _make_engine()
        assert "cast" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_cast_no_args(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, mana=100, room_vnum=3002)
        session = _make_session(eng, ch)
        eng.world.rooms[3002].characters.append(ch)

        await eng.process_command(session, "cast")
        msgs = _get_sent(session)
        assert any("주문" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_unknown_spell(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, mana=100, room_vnum=3002)
        session = _make_session(eng, ch)
        eng.world.rooms[3002].characters.append(ch)

        await eng.process_command(session, "cast xyzzy")
        msgs = _get_sent(session)
        assert any("모릅니다" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_magic_missile(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=0, mana=100, room_vnum=3002)
        mob = _npc(level=5, hp=100, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.extend([ch, mob])

        initial_mana = ch.mana
        await eng.process_command(session, "cast magic 고블린")
        assert ch.mana < initial_mana
        # Offensive spell starts combat
        assert ch.fighting is mob or mob.hp < 100

    @pytest.mark.asyncio
    async def test_cast_heal_self(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=16, class_id=1, mana=200, hp=50, max_hp=200,
                     room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.append(ch)

        await eng.process_command(session, "cast heal")
        assert ch.hp > 50

    @pytest.mark.asyncio
    async def test_cast_armor(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=5, class_id=0, mana=100, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.append(ch)

        await eng.process_command(session, "cast armor")
        has_buff = any(a.get("spell_id") == 10 for a in ch.affects)
        assert has_buff

    @pytest.mark.asyncio
    async def test_cast_not_enough_mana(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=0, mana=0, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.append(ch)

        await eng.process_command(session, "cast magic 고블린")
        msgs = _get_sent(session)
        assert any("마나" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_warrior_cannot(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=3, mana=100, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.append(ch)

        await eng.process_command(session, "cast magic 고블린")
        msgs = _get_sent(session)
        assert any("레벨" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_word_of_recall(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=12, class_id=1, mana=100, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.append(ch)

        await eng.process_command(session, "cast 귀환")
        assert ch.room_vnum == 3001
        msgs = _get_sent(session)
        assert any("순간이동" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_korean(self):
        """Test Korean command alias."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=5, class_id=0, mana=100, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.append(ch)

        await eng.process_command(session, "시전 armor")
        has_buff = any(a.get("spell_id") == 10 for a in ch.affects)
        assert has_buff

    @pytest.mark.asyncio
    async def test_cast_kills_target(self):
        """Cast that kills a mob defers death properly."""
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=30, class_id=0, mana=500, room_vnum=3002, exp=0)
        mob = _npc(level=1, hp=1, gold=10, exp=200, room_vnum=3002)
        session = _make_session(eng, ch)
        w.rooms[3002].characters.extend([ch, mob])

        await eng.process_command(session, "cast fireball 고블린")
        # Mob should be dead and removed
        assert mob not in w.rooms[3002].characters
        assert ch.experience > 0


# ── Practice command tests ────────────────────────────────────


class TestLuaPracticeCommand:
    @pytest.mark.asyncio
    async def test_practice_mage(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, mana=100, room_vnum=3002)
        session = _make_session(eng, ch)
        eng.world.rooms[3002].characters.append(ch)

        await eng.process_command(session, "practice")
        msgs = _get_sent(session)
        assert any("매직미사일" in m for m in msgs)
        assert any("화염구" not in m for m in msgs)  # Level 15 required

    @pytest.mark.asyncio
    async def test_practice_warrior_no_spells(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=3, mana=0, room_vnum=3002)
        session = _make_session(eng, ch)
        eng.world.rooms[3002].characters.append(ch)

        await eng.process_command(session, "practice")
        msgs = _get_sent(session)
        # Warriors have no castable spells
        assert any("주문" in m for m in msgs)
        assert not any("매직미사일" in m for m in msgs)


# ── Spell affect helpers ──────────────────────────────────────


class TestSpellAffectHelpers:
    def test_has_spell_affect(self):
        eng = _make_engine()
        ch = _player(room_vnum=3002)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng, eng.lua._lua)

        ch.affects.append({"spell_id": 14, "duration": 5})
        assert ctx.has_spell_affect(ch, 14)
        assert not ctx.has_spell_affect(ch, 15)

    def test_apply_spell_buff(self):
        eng = _make_engine()
        ch = _player(room_vnum=3002)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng, eng.lua._lua)

        ctx.apply_spell_buff(ch, 10, 24, {"ac_bonus": -20})
        assert len(ch.affects) == 1
        assert ch.affects[0]["spell_id"] == 10
        assert ch.affects[0]["ac_bonus"] == -20

    def test_apply_spell_buff_replaces(self):
        eng = _make_engine()
        ch = _player(room_vnum=3002)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng, eng.lua._lua)

        ctx.apply_spell_buff(ch, 10, 24)
        ctx.apply_spell_buff(ch, 10, 5)
        assert len(ch.affects) == 1
        assert ch.affects[0]["duration"] == 5

    def test_remove_spell_affect(self):
        eng = _make_engine()
        ch = _player(room_vnum=3002)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng, eng.lua._lua)

        ch.affects.append({"spell_id": 16, "duration": 10})
        ctx.remove_spell_affect(ch, 16)
        assert len(ch.affects) == 0

    def test_get_start_room(self):
        eng = _make_engine()
        ch = _player(room_vnum=3002)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng, eng.lua._lua)

        assert ctx.get_start_room() == 3001

    def test_move_char_to(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(room_vnum=3002)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng, eng.lua._lua)
        w.rooms[3002].characters.append(ch)

        ctx.move_char_to(ch, 3001)
        assert ch.room_vnum == 3001
        assert ch in w.rooms[3001].characters
        assert ch not in w.rooms[3002].characters
