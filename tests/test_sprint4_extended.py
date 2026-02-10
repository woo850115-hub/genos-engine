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
from core.engine import Engine
from core.world import (
    MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World,
)


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


class TestWhereCommand:
    @pytest.mark.asyncio
    async def test_where_no_players(self):
        from games.tbamud.commands.info import do_where
        w = World()
        room = RoomProto(
            vnum=1, name="방", description="", zone_number=0, sector_type=0,
            room_flags=[], exits=[], extra_descs=[], trigger_vnums=[],
        )
        w.rooms[1] = Room(proto=room)

        eng = Engine.__new__(Engine)
        eng.world = w
        eng.config = {"world": {"start_room": 1}}
        eng.sessions = {}
        eng.players = {}
        eng.cmd_handlers = {}
        eng.cmd_korean = {}
        eng._register_core_commands()
        eng.game_name = "tbamud"

        session = MagicMock()
        session.send_line = AsyncMock()
        session.engine = eng
        proto = MobProto(
            vnum=-1, keywords="t", short_description="t",
            long_description="", detailed_description="",
            level=1, hitroll=0, armor_class=100, hp_dice="0d0+0",
            damage_dice="1d4+0", gold=0, experience=0,
            action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
        )
        session.character = MobInstance(
            id=1, proto=proto, room_vnum=1, hp=20, max_hp=20,
            player_id=1, player_name="테스터", session=session,
        )
        w.rooms[1].characters.append(session.character)

        await do_where(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("없습니다" in c for c in calls)


class TestConsiderCommand:
    @pytest.mark.asyncio
    async def test_consider_easy(self):
        from games.tbamud.commands.info import do_consider
        w = World()
        room = RoomProto(
            vnum=1, name="방", description="", zone_number=0, sector_type=0,
            room_flags=[], exits=[], extra_descs=[], trigger_vnums=[],
        )
        w.rooms[1] = Room(proto=room)

        eng = Engine.__new__(Engine)
        eng.world = w
        eng.config = {"world": {"start_room": 1}}
        eng.sessions = {}
        eng.players = {}
        eng.cmd_handlers = {}
        eng.cmd_korean = {}
        eng._register_core_commands()
        eng.game_name = "tbamud"

        session = MagicMock()
        session.send_line = AsyncMock()
        session.engine = eng
        proto = MobProto(
            vnum=-1, keywords="t", short_description="t",
            long_description="", detailed_description="",
            level=20, hitroll=0, armor_class=100, hp_dice="0d0+0",
            damage_dice="1d4+0", gold=0, experience=0,
            action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
        )
        session.character = MobInstance(
            id=1, proto=proto, room_vnum=1, hp=100, max_hp=100,
            player_id=1, player_name="테스터", player_level=20,
        )
        w.rooms[1].characters.append(session.character)

        # Add weak mob
        mob_proto = MobProto(
            vnum=50, keywords="rat 쥐", short_description="쥐",
            long_description="", detailed_description="",
            level=1, hitroll=0, armor_class=100, hp_dice="1d1+1",
            damage_dice="1d1+0", gold=0, experience=10,
            action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
        )
        mob = MobInstance(id=50, proto=mob_proto, room_vnum=1, hp=5, max_hp=5)
        w.rooms[1].characters.append(mob)

        await do_consider(session, "rat")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("눈을 감고" in c for c in calls)
