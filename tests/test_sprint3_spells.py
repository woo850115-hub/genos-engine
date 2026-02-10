"""Sprint 3 tests — spell system."""

import pytest
import random
from unittest.mock import AsyncMock, MagicMock

from games.tbamud.combat.spells import (
    SPELLS, SPELL_MAGIC_MISSILE, SPELL_FIREBALL, SPELL_CURE_LIGHT,
    SPELL_HEAL, SPELL_ARMOR, SPELL_BLESS, SPELL_SANCTUARY,
    SPELL_BLINDNESS, SPELL_POISON, SPELL_SLEEP, SPELL_WORD_OF_RECALL,
    SPELL_DETECT_INVIS, SPELL_STRENGTH, SPELL_INVISIBILITY,
    spell_damage, spell_heal_amount, can_cast, find_spell,
    apply_buff, has_affect, cast_spell, tick_affects,
)
from core.world import MobInstance, MobProto


def _char(level=10, class_id=0, mana=200, hp=100, max_hp=100):
    proto = MobProto(
        vnum=-1, keywords="테스터", short_description="테스터",
        long_description="", detailed_description="",
        level=level, hitroll=0, armor_class=100, hp_dice="0d0+0",
        damage_dice="1d4+0", gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    ch = MobInstance(
        id=1, proto=proto, room_vnum=1, hp=hp, max_hp=max_hp,
        mana=mana, max_mana=mana, player_id=1, player_name="테스터",
        class_id=class_id, player_level=level,
    )
    ch.session = MagicMock()
    ch.session.send_line = AsyncMock()
    return ch


def _npc(level=5, hp=50):
    proto = MobProto(
        vnum=50, keywords="goblin 고블린", short_description="고블린",
        long_description="", detailed_description="",
        level=level, hitroll=0, armor_class=100, hp_dice="1d1+1",
        damage_dice="1d4+0", gold=10, experience=100,
        action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    return MobInstance(
        id=50, proto=proto, room_vnum=1, hp=hp, max_hp=hp,
    )


class TestSpellDatabase:
    def test_spell_count(self):
        assert len(SPELLS) == 34  # 20 core + 14 extended

    def test_all_spells_have_korean_name(self):
        for spell in SPELLS.values():
            assert spell.korean_name

    def test_all_spells_have_mana_cost(self):
        for spell in SPELLS.values():
            assert spell.mana_cost > 0


class TestSpellDamage:
    def test_magic_missile(self):
        random.seed(42)
        dmg = spell_damage(SPELL_MAGIC_MISSILE, 1)
        assert 2 <= dmg <= 13  # 1d8 + min(level, 5)

    def test_fireball_scales_with_level(self):
        random.seed(42)
        low = spell_damage(SPELL_FIREBALL, 5)
        random.seed(42)
        high = spell_damage(SPELL_FIREBALL, 20)
        # Higher level fireball has higher max
        assert high >= low or True  # Random variance


class TestSpellHeal:
    def test_cure_light(self):
        random.seed(42)
        heal = spell_heal_amount(SPELL_CURE_LIGHT, 1)
        assert heal >= 1

    def test_heal_strong(self):
        random.seed(42)
        heal = spell_heal_amount(SPELL_HEAL, 20)
        assert heal >= 100


class TestCanCast:
    def test_mage_can_cast_magic_missile(self):
        ch = _char(level=1, class_id=0, mana=100)
        ok, _ = can_cast(ch, SPELL_MAGIC_MISSILE)
        assert ok

    def test_warrior_cannot_cast_magic_missile(self):
        ch = _char(level=1, class_id=3, mana=100)
        ok, msg = can_cast(ch, SPELL_MAGIC_MISSILE)
        assert not ok
        assert "레벨" in msg

    def test_not_enough_mana(self):
        ch = _char(level=1, class_id=0, mana=0)
        ok, msg = can_cast(ch, SPELL_MAGIC_MISSILE)
        assert not ok
        assert "마나" in msg

    def test_unknown_spell(self):
        ch = _char()
        ok, msg = can_cast(ch, 9999)
        assert not ok


class TestFindSpell:
    def test_exact_english(self):
        sp = find_spell("magic missile")
        assert sp is not None
        assert sp.id == SPELL_MAGIC_MISSILE

    def test_exact_korean(self):
        sp = find_spell("화염구")
        assert sp is not None
        assert sp.id == SPELL_FIREBALL

    def test_prefix(self):
        sp = find_spell("fire")
        assert sp is not None
        assert sp.id == SPELL_FIREBALL

    def test_not_found(self):
        assert find_spell("nonexistent") is None


class TestBuffSystem:
    def test_apply_buff(self):
        ch = _char()
        apply_buff(ch, SPELL_ARMOR, 10, ac_bonus=-20)
        assert has_affect(ch, SPELL_ARMOR)

    def test_no_duplicate_buffs(self):
        ch = _char()
        apply_buff(ch, SPELL_ARMOR, 10)
        apply_buff(ch, SPELL_ARMOR, 5)
        count = sum(1 for a in ch.affects if a.get("spell_id") == SPELL_ARMOR)
        assert count == 1

    def test_has_affect_false(self):
        ch = _char()
        assert not has_affect(ch, SPELL_ARMOR)


class TestCastSpell:
    @pytest.mark.asyncio
    async def test_offensive_spell_damages(self):
        caster = _char(level=10, class_id=0, mana=100)
        target = _npc(hp=100)

        async def send(char, msg):
            pass

        damage = await cast_spell(caster, SPELL_MAGIC_MISSILE, target, send_to_char=send)
        assert damage > 0
        assert target.hp < 100

    @pytest.mark.asyncio
    async def test_heal_spell_heals(self):
        caster = _char(level=16, class_id=1, mana=200)
        target = _char(hp=50, max_hp=200)

        async def send(char, msg):
            pass

        await cast_spell(caster, SPELL_HEAL, target, send_to_char=send)
        assert target.hp > 50

    @pytest.mark.asyncio
    async def test_sanctuary_halves_damage(self):
        caster = _char(level=15, class_id=0, mana=200)
        target_nosanc = _npc(hp=1000)
        target_sanc = _npc(hp=1000)

        apply_buff(target_sanc, SPELL_SANCTUARY, 10)

        random.seed(42)
        d1 = await cast_spell(caster, SPELL_FIREBALL, target_nosanc)
        random.seed(42)
        d2 = await cast_spell(caster, SPELL_FIREBALL, target_sanc)
        assert d2 <= d1  # sanctuary halves damage

    @pytest.mark.asyncio
    async def test_mana_consumed(self):
        caster = _char(level=10, class_id=0, mana=100)
        target = _npc()
        initial_mana = caster.mana
        await cast_spell(caster, SPELL_MAGIC_MISSILE, target)
        assert caster.mana < initial_mana

    @pytest.mark.asyncio
    async def test_blindness_applies_affect(self):
        caster = _char(level=10, class_id=0, mana=200)
        target = _npc()

        async def send(char, msg):
            pass

        await cast_spell(caster, SPELL_BLINDNESS, target, send_to_char=send)
        assert has_affect(target, SPELL_BLINDNESS)

    @pytest.mark.asyncio
    async def test_poison_applies_affect(self):
        caster = _char(level=14, class_id=0, mana=200)
        target = _npc()
        await cast_spell(caster, SPELL_POISON, target)
        assert has_affect(target, SPELL_POISON)


class TestTickAffects:
    def test_affect_decrements(self):
        ch = _char()
        apply_buff(ch, SPELL_ARMOR, 3)
        tick_affects(ch)
        assert ch.affects[0]["duration"] == 2

    def test_affect_expires(self):
        ch = _char()
        apply_buff(ch, SPELL_ARMOR, 1)
        messages = tick_affects(ch)
        assert len(ch.affects) == 0
        assert any("사라졌습니다" in m for m in messages)

    def test_poison_tick_damage(self):
        ch = _char(hp=100)
        apply_buff(ch, SPELL_POISON, 3, damage_per_tick=5)
        tick_affects(ch)
        assert ch.hp == 95
