"""Tests for 10woongi Lua commands and combat — sigma, skills, info, items."""

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

START_ROOM = 1392841419
VOID_ROOM = 1854941986


def _load_lua(eng):
    """Load all Lua scripts for 10woongi."""
    eng.lua = LuaCommandRuntime(eng)
    base = Path(__file__).resolve().parent.parent / "games"
    for scope in ("common", "10woongi"):
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
        vnum=START_ROOM, name="장백성 마을 광장", description="넓은 광장입니다.",
        zone_number=100, sector_type=0, room_flags=[],
        exits=[], extra_descs=[], trigger_vnums=[],
    )
    room2 = RoomProto(
        vnum=VOID_ROOM, name="대기실", description="대기실입니다.",
        zone_number=100, sector_type=0, room_flags=[],
        exits=[], extra_descs=[], trigger_vnums=[],
    )
    room3 = RoomProto(
        vnum=100, name="들판", description="넓은 들판입니다.",
        zone_number=1, sector_type=0, room_flags=[],
        exits=[], extra_descs=[], trigger_vnums=[],
    )
    w.rooms[START_ROOM] = Room(proto=room1)
    w.rooms[VOID_ROOM] = Room(proto=room2)
    w.rooms[100] = Room(proto=room3)
    return w


def _make_engine(world=None):
    if world is None:
        world = _make_world()
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": START_ROOM, "void_room": VOID_ROOM}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    eng.game_name = "10woongi"
    _load_lua(eng)
    return eng


def _make_session(eng, char):
    session = MagicMock()
    session.send_line = AsyncMock()
    session.character = char
    session.engine = eng
    session.player_data = {"level": char.level, "sex": 1, "age": 20}
    session.config = eng.config
    char.session = session
    return session


def _player(level=10, class_id=1, hp=200, max_hp=200, move=80, max_move=80,
            mana=50, exp=0, gold=100, room_vnum=100, wuxia_stats=None):
    proto = MobProto(
        vnum=-1, keywords="테스터", short_description="테스터",
        long_description="", detailed_description="",
        level=level, hitroll=5, armor_class=100, hp_dice="0d0+0",
        damage_dice="1d6+2", gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    ch = MobInstance(
        id=1, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=max_hp,
        mana=mana, max_mana=mana, gold=gold, experience=exp,
        player_id=1, player_name="테스터", class_id=class_id,
        player_level=level,
    )
    ch.move = move
    ch.max_move = max_move
    if wuxia_stats is None:
        wuxia_stats = {"stamina": 20, "agility": 15, "wisdom": 15,
                       "bone": 18, "inner": 16, "spirit": 22}
    ch.extensions = {"stats": wuxia_stats, "faction": "무영루"}
    return ch


def _npc(level=5, hp=50, gold=20, exp=100, room_vnum=100, damroll=0):
    proto = MobProto(
        vnum=50, keywords="goblin 고블린", short_description="고블린",
        long_description="", detailed_description="",
        level=level, hitroll=0, armor_class=100, hp_dice="1d1+1",
        damage_dice="1d4+0", gold=gold, experience=exp,
        action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    mob = MobInstance(
        id=50, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=hp, gold=gold,
    )
    mob.damroll = damroll
    return mob


def _get_sent(session):
    return [str(c) for c in session.send_line.call_args_list]


# ── Lib.lua tests (sigma formula, wuxia stats) ──────────────


class TestWoongiLib:
    def test_sigma_formula(self):
        eng = _make_engine()
        lua = eng.lua._lua
        # sigma(1) = 0, sigma(10) = 45, sigma(150) = 11175
        assert lua.eval("sigma(1)") == 0
        assert lua.eval("sigma(10)") == 45
        assert lua.eval("sigma(150)") == 11175
        # sigma(151) = 11175 + 150 = 11325
        assert lua.eval("sigma(151)") == 11325

    def test_calc_hp(self):
        eng = _make_engine()
        lua = eng.lua._lua
        # calc_hp(13) = 80 + 6 * sigma(13) / 30 = 80 + 6*78/30 = 80 + 15 = 95
        result = lua.eval("calc_hp(13)")
        assert result == 80 + 6 * (12 * 13 // 2) // 30

    def test_calc_adj_exp(self):
        eng = _make_engine()
        lua = eng.lua._lua
        # calc_adj_exp(5) = 25*10 + 5*50 = 250 + 250 = 500
        assert lua.eval("calc_adj_exp(5)") == 500

    def test_class_names(self):
        eng = _make_engine()
        lua = eng.lua._lua
        assert lua.eval('CLASS_NAMES[1]') == "투사"
        assert lua.eval('CLASS_NAMES[14]') == "시공술사"

    def test_wear_slots(self):
        eng = _make_engine()
        lua = eng.lua._lua
        assert lua.eval('WEAR_SLOTS[1]') == "투구"
        assert lua.eval('WEAR_SLOTS[9]') == "반지1"
        assert lua.eval('NUM_WEAR_SLOTS') == 22


# ── Sigma combat hook tests ──────────────────────────────────


class TestSigmaCombatHook:
    def test_hook_registered(self):
        eng = _make_engine()
        assert eng.lua.has_hook("combat_round")

    @pytest.mark.asyncio
    async def test_combat_round_deals_damage(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=20, class_id=4, room_vnum=100)
        mob = _npc(level=1, hp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        await eng._lua_combat_round()

        msgs = _get_sent(session)
        assert any("빗나" in m or "데미지" in m for m in msgs) or mob.hp < 200

    @pytest.mark.asyncio
    async def test_combat_round_sp_damage(self):
        """Sigma combat deals both HP and SP damage."""
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=30, class_id=4, room_vnum=100)
        mob = _npc(level=1, hp=500, room_vnum=100)
        mob.move = 100
        mob.max_move = 100
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        # Run multiple rounds to guarantee a hit
        for _ in range(20):
            if mob.hp < 500:
                break
            await eng._lua_combat_round()

        # At least one hit should have landed
        assert mob.hp < 500 or mob.move < 100

    @pytest.mark.asyncio
    async def test_combat_round_kills_npc(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=30, class_id=4, room_vnum=100, exp=0)
        ch.hitroll = 50
        mob = _npc(level=1, hp=1, gold=10, exp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        # Force high hit chance
        orig = random.randint
        random.randint = lambda a, b: 1 if b == 100 else orig(a, b)
        try:
            await eng._lua_combat_round()
        finally:
            random.randint = orig

        assert ch.fighting is None
        assert mob not in w.rooms[100].characters


# ── Skill command tests ──────────────────────────────────────


class TestWoongiSkillCommand:
    @pytest.mark.asyncio
    async def test_use_registered(self):
        eng = _make_engine()
        assert "use" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_use_no_args(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=1, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "use")
        msgs = _get_sent(session)
        assert any("사용법" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_use_unknown_skill(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=1, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "use xyzzy")
        msgs = _get_sent(session)
        assert any("없습니다" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_use_attack_skill(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=25, class_id=2, move=100, room_vnum=100)
        mob = _npc(level=5, hp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        await eng.process_command(session, "use 연타 고블린")
        msgs = _get_sent(session)
        assert any("데미지" in m for m in msgs)
        assert ch.move < 100  # SP deducted

    @pytest.mark.asyncio
    async def test_use_recovery_skill(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=6, hp=50, max_hp=200, move=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "use 치료1")
        assert ch.hp > 50

    @pytest.mark.asyncio
    async def test_use_not_enough_sp(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=1, move=0, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "use 방패방어")
        msgs = _get_sent(session)
        assert any("내공" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_use_class_restriction(self):
        w = _make_world()
        eng = _make_engine(w)
        # Class 1 (투사) can't use magic skills
        ch = _player(level=10, class_id=1, move=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "use 매직미셜")
        msgs = _get_sent(session)
        assert any("직업" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_skills_list(self):
        eng = _make_engine()
        ch = _player(level=20, class_id=2, room_vnum=100)  # 전사
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "skills")
        msgs = _get_sent(session)
        assert any("패리" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_use_korean_alias(self):
        eng = _make_engine()
        ch = _player(level=20, class_id=2, move=100, room_vnum=100)
        mob = _npc(level=5, hp=200, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.extend([ch, mob])

        await eng.process_command(session, "기술 강타 고블린")
        msgs = _get_sent(session)
        assert any("강타" in m for m in msgs)


# ── Info command tests ───────────────────────────────────────


class TestWoongiInfoCommands:
    @pytest.mark.asyncio
    async def test_score(self):
        eng = _make_engine()
        ch = _player(level=15, class_id=2, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "score")
        msgs = _get_sent(session)
        assert any("테스터" in m for m in msgs)
        assert any("전사" in m or "무공" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_who(self):
        eng = _make_engine()
        ch = _player(level=15, class_id=2, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)
        eng.players["테스터"] = session

        await eng.process_command(session, "who")
        msgs = _get_sent(session)
        assert any("강호인" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_consider(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, room_vnum=100)
        mob = _npc(level=5, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        await eng.process_command(session, "consider 고블린")
        msgs = _get_sent(session)
        assert any("쉬운" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_inventory_empty(self):
        eng = _make_engine()
        ch = _player(level=10, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "inventory")
        msgs = _get_sent(session)
        assert any("아무것도" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_equipment_empty(self):
        eng = _make_engine()
        ch = _player(level=10, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "equipment")
        msgs = _get_sent(session)
        assert any("착용중인 장비가 없습니다" in m for m in msgs)


# ── Movement command tests ───────────────────────────────────


class TestWoongiMovement:
    @pytest.mark.asyncio
    async def test_recall(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "recall")
        assert ch.room_vnum == START_ROOM
        msgs = _get_sent(session)
        assert any("순간이동" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_recall_in_combat(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, room_vnum=100)
        mob = _npc(level=5, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])
        ch.fighting = mob

        await eng.process_command(session, "recall")
        assert ch.room_vnum == 100  # Should NOT have moved
        msgs = _get_sent(session)
        assert any("전투 중" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_recall_korean(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "귀환")
        assert ch.room_vnum == START_ROOM


# ── Comm command tests ───────────────────────────────────────


class TestWoongiCommCommands:
    @pytest.mark.asyncio
    async def test_tell(self):
        eng = _make_engine()
        ch = _player(level=10, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        # Create target player
        target_ch = _player(level=10, room_vnum=100)
        target_ch.id = 2
        target_ch.player_name = "상대"
        target_session = _make_session(eng, target_ch)
        eng.players["상대"] = target_session

        await eng.process_command(session, "tell 상대 안녕")
        msgs = _get_sent(session)
        assert any("귓속말" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_shout(self):
        eng = _make_engine()
        ch = _player(level=10, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "shout 안녕하세요!")
        msgs = _get_sent(session)
        assert any("외칩니다" in m for m in msgs)


# ── Admin command tests ──────────────────────────────────────


class TestWoongiAdminCommands:
    @pytest.mark.asyncio
    async def test_goto(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, f"goto {START_ROOM}")
        assert ch.room_vnum == START_ROOM

    @pytest.mark.asyncio
    async def test_goto_no_admin(self):
        eng = _make_engine()
        ch = _player(level=10, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, f"goto {START_ROOM}")
        assert ch.room_vnum == 100  # Should not move
        msgs = _get_sent(session)
        assert any("권한" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_restore(self):
        eng = _make_engine()
        ch = _player(level=100, hp=50, max_hp=200, move=10, max_move=80, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "restore")
        assert ch.hp == 200
        assert ch.move == 80

    @pytest.mark.asyncio
    async def test_purge(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=100, room_vnum=100)
        mob = _npc(level=5, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        await eng.process_command(session, "purge")
        # NPC should be removed
        npcs = [c for c in w.rooms[100].characters if c.is_npc]
        assert len(npcs) == 0
        msgs = _get_sent(session)
        assert any("정화" in m for m in msgs)
