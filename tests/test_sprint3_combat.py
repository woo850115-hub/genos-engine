"""Sprint 3 tests — THAC0 combat system."""

import pytest
import random
from unittest.mock import AsyncMock, MagicMock

from games.tbamud.combat.thac0 import (
    ATTACK_TYPES, THAC0_TABLE, STR_TOHIT, STR_TODAM, DEX_DEFENSIVE,
    get_thac0, compute_ac, roll_hit, roll_damage, get_attack_type,
    damage_message, perform_attack, extra_attacks,
)
from core.world import MobInstance, MobProto, ObjInstance, ItemProto


def _mob(level=5, hp=50, armor_class=100, hitroll=0, damage_dice="1d4+0",
         vnum=1, keywords="goblin 고블린", is_player=False, class_id=3):
    proto = MobProto(
        vnum=vnum, keywords=keywords, short_description="고블린",
        long_description="", detailed_description="",
        level=level, hitroll=hitroll, armor_class=armor_class,
        hp_dice="1d1+1", damage_dice=damage_dice, gold=10, experience=100,
        action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    mob = MobInstance(
        id=vnum, proto=proto, room_vnum=1, hp=hp, max_hp=hp,
    )
    if is_player:
        mob.player_id = 1
        mob.player_name = "테스터"
        mob.class_id = class_id
        mob.player_level = level
        mob.session = MagicMock()
        mob.session.send_line = AsyncMock()
    return mob


class TestTHAC0Table:
    def test_warrior_level1(self):
        assert get_thac0(3, 1) == 20

    def test_warrior_level20(self):
        assert get_thac0(3, 20) == 2

    def test_mage_level1(self):
        assert get_thac0(0, 1) == 20

    def test_mage_level34(self):
        assert get_thac0(0, 34) == 9

    def test_unknown_class_defaults(self):
        assert get_thac0(99, 1) == 20

    def test_all_classes_have_tables(self):
        for cls_id in range(4):
            assert cls_id in THAC0_TABLE


class TestComputeAC:
    def test_base_ac_npc(self):
        mob = _mob(armor_class=50)
        ac = compute_ac(mob)
        assert ac <= 50  # dex might lower it

    def test_dex_bonus(self):
        mob = _mob(armor_class=100)
        mob.dex = 18
        ac = compute_ac(mob)
        assert ac < 100  # dex 18 gives -4

    def test_ac_clamp(self):
        mob = _mob(armor_class=-50)
        ac = compute_ac(mob)
        assert ac >= -10


class TestRollHit:
    def test_natural_20_always_hits(self):
        random.seed(42)
        attacker = _mob(level=1, hitroll=0)
        defender = _mob(armor_class=-10)
        # Force roll=20
        orig = random.randint
        random.randint = lambda a, b: 20
        try:
            assert roll_hit(attacker, defender)
        finally:
            random.randint = orig

    def test_natural_1_always_misses(self):
        attacker = _mob(level=30, hitroll=50)
        defender = _mob(armor_class=100)
        orig = random.randint
        random.randint = lambda a, b: 1
        try:
            assert not roll_hit(attacker, defender)
        finally:
            random.randint = orig

    def test_hit_probability_increases_with_level(self):
        random.seed(12345)
        low = _mob(level=1, hitroll=0)
        high = _mob(level=20, hitroll=10)
        defender = _mob(armor_class=50)
        low_hits = sum(1 for _ in range(200) if roll_hit(low, defender))
        high_hits = sum(1 for _ in range(200) if roll_hit(high, defender))
        assert high_hits >= low_hits


class TestRollDamage:
    def test_min_damage_1(self):
        mob = _mob(damage_dice="0d0+0")
        dmg = roll_damage(mob)
        assert dmg >= 1

    def test_damage_with_bonus(self):
        mob = _mob(damage_dice="1d6+5")
        random.seed(42)
        dmg = roll_damage(mob)
        assert dmg >= 6  # 1+5 minimum

    def test_player_str_bonus(self):
        player = _mob(is_player=True, damage_dice="1d4+0")
        player.str = 18
        random.seed(42)
        dmg = roll_damage(player)
        assert dmg >= 1 + STR_TODAM[18]


class TestAttackType:
    def test_barehanded(self):
        mob = _mob()
        atk_type, name = get_attack_type(mob)
        assert atk_type == 0
        assert name == "때림"

    def test_attack_types_complete(self):
        assert len(ATTACK_TYPES) == 15


class TestDamageMessage:
    def test_miss(self):
        assert "빗나감" in damage_message(0)

    def test_light(self):
        assert damage_message(2) != damage_message(20)

    def test_devastating(self):
        assert "파괴" in damage_message(50)


class TestPerformAttack:
    @pytest.mark.asyncio
    async def test_attack_deals_damage_or_misses(self):
        random.seed(42)
        attacker = _mob(level=10, hitroll=5, damage_dice="2d6+3")
        defender = _mob(level=5, hp=100, armor_class=80)

        async def send(char, msg):
            pass

        total = 0
        for _ in range(10):
            total += await perform_attack(attacker, defender, send_to_char=send)
        # After 10 rounds, some damage should have been dealt
        assert total > 0

    @pytest.mark.asyncio
    async def test_messages_sent(self):
        random.seed(42)
        attacker = _mob(level=20, hitroll=20, damage_dice="2d6+10")
        defender = _mob(level=1, hp=100, armor_class=100, is_player=True)
        msgs = []

        async def send(char, msg):
            msgs.append(msg)

        # Force a hit
        orig = random.randint
        random.randint = lambda a, b: 20 if b == 20 else orig(a, b)
        try:
            await perform_attack(attacker, defender, send_to_char=send)
        finally:
            random.randint = orig
        assert len(msgs) > 0


class TestExtraAttacks:
    def test_npc_low_level(self):
        mob = _mob(level=5)
        assert extra_attacks(mob) == 0

    def test_npc_high_level(self):
        mob = _mob(level=25)
        assert extra_attacks(mob) == 2

    def test_warrior_level_20(self):
        player = _mob(is_player=True, level=20, class_id=3)
        assert extra_attacks(player) == 2

    def test_warrior_level_10(self):
        player = _mob(is_player=True, level=10, class_id=3)
        assert extra_attacks(player) == 1

    def test_mage_no_extra(self):
        player = _mob(is_player=True, level=20, class_id=0)
        assert extra_attacks(player) == 0

    def test_npc_capped_at_3(self):
        mob = _mob(level=50)
        assert extra_attacks(mob) == 3
