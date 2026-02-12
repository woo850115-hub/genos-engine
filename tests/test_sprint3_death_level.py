"""Sprint 3 tests — death, respawn, level, experience."""

import pytest
import random
from unittest.mock import AsyncMock, MagicMock

from games.tbamud.combat.death import handle_death, calculate_exp_gain
from games.tbamud.level import (
    EXP_TABLE, CLASS_GAINS, CLASS_NAMES, MAX_LEVEL,
    exp_for_level, check_level_up, do_level_up, exp_to_next, _con_hp_bonus,
)
from core.engine import Engine
from core.world import (
    Exit, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World,
)


def _make_world():
    w = World()
    room1 = RoomProto(
        vnum=3001, name="신전", description="넓은 신전입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[],
    )
    room2 = RoomProto(
        vnum=3002, name="들판", description="넓은 들판입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[],
    )
    w.rooms[3001] = Room(proto=room1)
    w.rooms[3002] = Room(proto=room2)
    return w


def _make_engine(world):
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 3001}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    eng.game_name = "tbamud"
    return eng


def _player(level=10, exp=0, class_id=3, hp=100, gold=50, room_vnum=3002):
    proto = MobProto(
        vnum=-1, keywords="플레이어", short_desc="플레이어",
        long_desc="", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[],
    )
    ch = MobInstance(
        id=1, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=hp,
        mana=50, max_mana=50, gold=gold, experience=exp,
        player_id=1, player_name="플레이어", class_id=class_id,
        player_level=level,
    )
    session = MagicMock()
    session.send_line = AsyncMock()
    ch.session = session
    return ch


def _npc(level=5, hp=50, gold=20, exp=100, room_vnum=3002):
    proto = MobProto(
        vnum=50, keywords="goblin 고블린", short_desc="고블린",
        long_desc="", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=2,
        damage_dice="1d4+0", gold=gold, experience=exp,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[],
    )
    return MobInstance(
        id=50, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=hp, gold=gold,
    )


# ── Experience tables ────────────────────────────────────────────

class TestExpTable:
    def test_all_classes_present(self):
        for cls_id in range(4):
            assert cls_id in EXP_TABLE

    def test_level_1_minimal(self):
        assert exp_for_level(0, 1) == 1

    def test_level_31_max(self):
        assert exp_for_level(0, 31) == 8000000

    def test_exp_increases_with_level(self):
        for cls_id in range(4):
            for lv in range(2, 31):
                assert exp_for_level(cls_id, lv) >= exp_for_level(cls_id, lv - 1)


class TestClassGains:
    def test_all_classes(self):
        for cls_id in range(4):
            assert cls_id in CLASS_GAINS

    def test_warrior_highest_hp(self):
        w_hp = CLASS_GAINS[3]["hp"]
        m_hp = CLASS_GAINS[0]["hp"]
        assert w_hp[1] > m_hp[1]

    def test_mage_has_mana(self):
        assert CLASS_GAINS[0]["mana"][1] > 0

    def test_warrior_no_mana(self):
        assert CLASS_GAINS[3]["mana"][1] == 0


class TestCheckLevelUp:
    def test_enough_exp(self):
        ch = _player(level=1, exp=5000, class_id=0)
        # Level 2 requires 2500 for mage
        assert check_level_up(ch)

    def test_not_enough_exp(self):
        ch = _player(level=1, exp=100, class_id=0)
        assert not check_level_up(ch)

    def test_max_level(self):
        ch = _player(level=MAX_LEVEL, exp=99999999, class_id=0)
        assert not check_level_up(ch)

    def test_npc_never_levels(self):
        mob = _npc()
        assert not check_level_up(mob)


class TestDoLevelUp:
    @pytest.mark.asyncio
    async def test_level_increases(self):
        random.seed(42)
        ch = _player(level=5, exp=500000, class_id=3)
        msgs = []

        async def capture(m):
            msgs.append(m)

        await do_level_up(ch, send_fn=capture)
        assert ch.level == 6

    @pytest.mark.asyncio
    async def test_hp_increases(self):
        random.seed(42)
        ch = _player(level=5, exp=500000, class_id=3, hp=100)
        old_hp = ch.max_hp
        gains = await do_level_up(ch)
        assert ch.max_hp > old_hp
        assert gains["hp"] > 0

    @pytest.mark.asyncio
    async def test_mage_gets_mana(self):
        random.seed(42)
        ch = _player(level=5, exp=500000, class_id=0, hp=50)
        ch.max_mana = 50
        gains = await do_level_up(ch)
        assert gains["mana"] > 0
        assert ch.max_mana > 50

    @pytest.mark.asyncio
    async def test_full_heal_on_levelup(self):
        ch = _player(level=5, exp=500000, class_id=3, hp=10)
        ch.max_hp = 100
        await do_level_up(ch)
        assert ch.hp == ch.max_hp

    @pytest.mark.asyncio
    async def test_max_level_no_change(self):
        ch = _player(level=MAX_LEVEL, class_id=3)
        gains = await do_level_up(ch)
        assert gains == {}


class TestConHpBonus:
    def test_low_con(self):
        assert _con_hp_bonus(3) < 0

    def test_mid_con(self):
        assert _con_hp_bonus(13) == 0

    def test_high_con(self):
        assert _con_hp_bonus(18) > 0


class TestExpToNext:
    def test_normal(self):
        ch = _player(level=5, exp=10000, class_id=3)
        remaining = exp_to_next(ch)
        needed = exp_for_level(3, 6) - 10000
        assert remaining == needed

    def test_max_level(self):
        ch = _player(level=MAX_LEVEL, exp=999999999, class_id=3)
        assert exp_to_next(ch) == 0


# ── Death system ─────────────────────────────────────────────────

class TestCalculateExpGain:
    def test_same_level(self):
        killer = _player(level=10)
        victim = _npc(level=10, exp=500)
        gain = calculate_exp_gain(killer, victim)
        assert gain == 500  # 1.0 modifier

    def test_higher_victim(self):
        killer = _player(level=5)
        victim = _npc(level=15, exp=500)
        gain = calculate_exp_gain(killer, victim)
        assert gain == 750  # 1.5 modifier

    def test_much_lower_victim(self):
        killer = _player(level=20)
        victim = _npc(level=5, exp=500)
        gain = calculate_exp_gain(killer, victim)
        assert gain == 50  # 0.1 modifier

    def test_zero_exp_fallback(self):
        killer = _player(level=10)
        victim = _npc(level=5, exp=0)
        gain = calculate_exp_gain(killer, victim)
        assert gain > 0  # fallback calc


class TestHandleDeath:
    @pytest.mark.asyncio
    async def test_npc_death_awards_exp(self):
        w = _make_world()
        eng = _make_engine(w)
        killer = _player(level=10, exp=0, room_vnum=3002)
        victim = _npc(level=5, exp=200, gold=50, room_vnum=3002)
        killer.fighting = victim
        victim.fighting = killer
        w.rooms[3002].characters.extend([killer, victim])

        await handle_death(eng, victim, killer=killer)
        assert killer.experience > 0
        assert killer.gold >= 50
        assert victim not in w.rooms[3002].characters

    @pytest.mark.asyncio
    async def test_npc_death_drops_items(self):
        w = _make_world()
        eng = _make_engine(w)
        killer = _player(level=10, room_vnum=3002)
        victim = _npc(room_vnum=3002)
        item_proto = ItemProto(
            vnum=1, keywords="sword 검", short_desc="검",
            long_desc="검이 있습니다.", item_type="weapon",
            flags=[], wear_slots=[], values={},
            weight=5, cost=100, affects=[], extra_descs=[], scripts=[],
        )
        victim.inventory.append(ObjInstance(id=1, proto=item_proto))
        w.rooms[3002].characters.extend([killer, victim])

        await handle_death(eng, victim, killer=killer)
        assert len(w.rooms[3002].objects) == 1

    @pytest.mark.asyncio
    async def test_player_death_respawns(self):
        w = _make_world()
        eng = _make_engine(w)
        victim = _player(level=10, exp=100000, room_vnum=3002, hp=0)
        w.rooms[3002].characters.append(victim)

        await handle_death(eng, victim)
        assert victim.room_vnum == 3001
        assert victim.hp > 0
        assert victim in w.rooms[3001].characters
        assert victim not in w.rooms[3002].characters

    @pytest.mark.asyncio
    async def test_player_death_exp_penalty(self):
        w = _make_world()
        eng = _make_engine(w)
        initial_exp = 100000
        victim = _player(level=10, exp=initial_exp, room_vnum=3002, hp=0)
        w.rooms[3002].characters.append(victim)

        await handle_death(eng, victim)
        assert victim.experience < initial_exp

    @pytest.mark.asyncio
    async def test_combat_state_cleared(self):
        w = _make_world()
        eng = _make_engine(w)
        killer = _player(level=10, room_vnum=3002)
        victim = _npc(room_vnum=3002)
        killer.fighting = victim
        victim.fighting = killer
        w.rooms[3002].characters.extend([killer, victim])

        await handle_death(eng, victim, killer=killer)
        assert killer.fighting is None
