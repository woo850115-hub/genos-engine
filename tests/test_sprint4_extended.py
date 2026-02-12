"""Sprint 4 tests — extended spells, where/consider commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from games.tbamud.combat.spells import (
    SPELLS, SPELL_EARTHQUAKE, SPELL_REMOVE_CURSE, SPELL_REMOVE_POISON,
    SPELL_GROUP_HEAL, SPELL_GROUP_ARMOR, SPELL_INFRAVISION,
    SPELL_WATERWALK, SPELL_TELEPORT, SPELL_ENCHANT_WEAPON,
    SPELL_CHARM, SPELL_DISPEL_EVIL, SPELL_SUMMON, SPELL_LOCATE_OBJECT,
    SPELL_CURSE, SPELL_POISON,
    find_spell, can_cast, cast_spell, apply_buff, has_affect,
)
from core.world import (
    MobInstance, MobProto, ObjInstance, ItemProto,
)


def _char(level=10, class_id=0, mana=200, hp=100, max_hp=100):
    proto = MobProto(
        vnum=-1, keywords="테스터", short_desc="테스터",
        long_desc="", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[],
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
        vnum=50, keywords="goblin 고블린", short_desc="고블린",
        long_desc="", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=2,
        damage_dice="1d4+0", gold=10, experience=100,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[],
    )
    return MobInstance(
        id=50, proto=proto, room_vnum=1, hp=hp, max_hp=hp,
    )


class TestExtendedSpellCount:
    def test_total_spells(self):
        assert len(SPELLS) == 34


class TestExtendedSpellFind:
    def test_earthquake(self):
        sp = find_spell("지진")
        assert sp is not None
        assert sp.id == SPELL_EARTHQUAKE

    def test_remove_curse(self):
        sp = find_spell("저주해제")
        assert sp is not None
        assert sp.id == SPELL_REMOVE_CURSE

    def test_group_heal(self):
        sp = find_spell("그룹치유")
        assert sp is not None
        assert sp.id == SPELL_GROUP_HEAL

    def test_enchant_weapon(self):
        sp = find_spell("무기강화")
        assert sp is not None

    def test_prefix_search(self):
        sp = find_spell("tele")
        assert sp is not None
        assert sp.id == SPELL_TELEPORT


class TestExtendedSpellEffects:
    @pytest.mark.asyncio
    async def test_remove_curse(self):
        caster = _char(level=10, class_id=1, mana=200)
        target = _char()
        apply_buff(target, SPELL_CURSE, 10)
        assert has_affect(target, SPELL_CURSE)

        async def send(char, msg): pass
        await cast_spell(caster, SPELL_REMOVE_CURSE, target, send_to_char=send)
        assert not has_affect(target, SPELL_CURSE)

    @pytest.mark.asyncio
    async def test_remove_poison(self):
        caster = _char(level=10, class_id=1, mana=200)
        target = _char()
        apply_buff(target, SPELL_POISON, 10, damage_per_tick=5)
        assert has_affect(target, SPELL_POISON)

        async def send(char, msg): pass
        await cast_spell(caster, SPELL_REMOVE_POISON, target, send_to_char=send)
        assert not has_affect(target, SPELL_POISON)

    @pytest.mark.asyncio
    async def test_group_heal(self):
        caster = _char(level=22, class_id=1, mana=200)
        target = _char(hp=50, max_hp=200)

        async def send(char, msg): pass
        await cast_spell(caster, SPELL_GROUP_HEAL, target, send_to_char=send)
        assert target.hp > 50

    @pytest.mark.asyncio
    async def test_infravision(self):
        caster = _char(level=10, class_id=0, mana=200)
        await cast_spell(caster, SPELL_INFRAVISION, caster)
        assert has_affect(caster, SPELL_INFRAVISION)

    @pytest.mark.asyncio
    async def test_waterwalk(self):
        caster = _char(level=10, class_id=1, mana=200)
        await cast_spell(caster, SPELL_WATERWALK, caster)
        assert has_affect(caster, SPELL_WATERWALK)

    @pytest.mark.asyncio
    async def test_earthquake_damage(self):
        caster = _char(level=12, class_id=1, mana=200)
        target = _npc(hp=100)
        dmg = await cast_spell(caster, SPELL_EARTHQUAKE, target)
        assert dmg > 0
        assert target.hp < 100

    @pytest.mark.asyncio
    async def test_charm(self):
        caster = _char(level=16, class_id=0, mana=200)
        target = _npc(level=10)

        async def send(char, msg): pass
        await cast_spell(caster, SPELL_CHARM, target, send_to_char=send)
        assert has_affect(target, SPELL_CHARM)


