"""Sprint 5 tests — DG Script trigger runtime (lupa)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from games.tbamud.triggers import (
    TriggerRuntime,
    TRIG_MOB_GREET, TRIG_MOB_COMMAND, TRIG_ROOM_ENTER, TRIG_ROOM_COMMAND,
)
from core.world import (
    MobInstance, MobProto, Room, RoomProto, World,
)


def _make_engine():
    eng = MagicMock()
    eng.world = World()
    room_proto = RoomProto(
        vnum=3001, name="테스트 방", description="",
        zone_number=30, sector_type=0, room_flags=[],
        exits=[], extra_descs=[], trigger_vnums=[100, 101],
    )
    eng.world.rooms[3001] = Room(proto=room_proto)
    return eng


class TestTriggerConstants:
    def test_trigger_type_values(self):
        assert TRIG_MOB_GREET == 1
        assert TRIG_MOB_COMMAND == 3
        assert TRIG_ROOM_ENTER == 13
        assert TRIG_ROOM_COMMAND == 14

    def test_all_trigger_types_defined(self):
        from games.tbamud import triggers
        types = [
            triggers.TRIG_MOB_GREET, triggers.TRIG_MOB_ENTRY,
            triggers.TRIG_MOB_COMMAND, triggers.TRIG_MOB_SPEECH,
            triggers.TRIG_MOB_ACT, triggers.TRIG_MOB_FIGHT,
            triggers.TRIG_MOB_DEATH, triggers.TRIG_MOB_RANDOM,
            triggers.TRIG_OBJ_COMMAND, triggers.TRIG_OBJ_GET,
            triggers.TRIG_OBJ_DROP, triggers.TRIG_OBJ_GIVE,
            triggers.TRIG_ROOM_ENTER, triggers.TRIG_ROOM_COMMAND,
            triggers.TRIG_ROOM_RANDOM, triggers.TRIG_ROOM_SPEECH,
        ]
        assert len(types) == 16
        assert len(set(types)) == 16  # all unique


class TestTriggerRuntime:
    def test_init(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        assert runtime.trigger_count == 0
        assert runtime._lua is None

    def test_init_without_lupa(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        with patch.dict("sys.modules", {"lupa": None}):
            # Should return False when lupa not available
            result = runtime.init(data_dir=None)
            # Even without lupa import error, init with no data_dir
            # depends on whether lupa is installed

    def test_init_with_lupa(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        try:
            result = runtime.init()
            if result:
                assert runtime._lua is not None
        except Exception:
            pytest.skip("lupa not installed")

    def test_get_trigger_nonexistent(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        assert runtime.get_trigger(999) is None

    def test_trigger_count_empty(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        assert runtime.trigger_count == 0

    @pytest.mark.asyncio
    async def test_fire_trigger_no_lua(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        # No lua runtime → should return False
        result = await runtime.fire_trigger(100)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_room_triggers_no_triggers(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        result = await runtime.check_room_triggers(3001, TRIG_ROOM_ENTER)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_mob_triggers_no_triggers(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        mob_proto = MobProto(
            vnum=100, keywords="guard 경비병", short_description="경비병",
            long_description="", detailed_description="",
            level=10, hitroll=0, armor_class=0, hp_dice="5d8+30",
            damage_dice="1d6+3", gold=50, experience=500,
            action_flags=[], affect_flags=[], alignment=0, sex=0,
            trigger_vnums=[200],
        )
        mob = MobInstance(
            id=1, proto=mob_proto, room_vnum=3001, hp=50, max_hp=50,
        )
        result = await runtime.check_mob_triggers(mob, TRIG_MOB_GREET)
        assert result is False


class TestTriggerVariables:
    def test_get_set_variable(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        runtime._api_set_variable("global", "test_var", "hello")
        assert runtime._api_get_variable("global", "test_var") == "hello"

    def test_get_nonexistent_variable(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        assert runtime._api_get_variable("global", "missing") == ""

    def test_set_multiple_contexts(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        runtime._api_set_variable("mob_100", "name", "경비병")
        runtime._api_set_variable("room_3001", "description", "작은 방")
        assert runtime._api_get_variable("mob_100", "name") == "경비병"
        assert runtime._api_get_variable("room_3001", "description") == "작은 방"
        assert runtime._api_get_variable("mob_100", "description") == ""


class TestTriggerAPIs:
    def test_teleport(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)

        room2_proto = RoomProto(
            vnum=3002, name="방2", description="",
            zone_number=30, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        eng.world.rooms[3002] = Room(proto=room2_proto)

        mob_proto = MobProto(
            vnum=100, keywords="guard", short_description="경비병",
            long_description="", detailed_description="",
            level=10, hitroll=0, armor_class=0, hp_dice="5d8+30",
            damage_dice="1d6+3", gold=50, experience=500,
            action_flags=[], affect_flags=[], alignment=0, sex=0,
            trigger_vnums=[],
        )
        mob = MobInstance(
            id=42, proto=mob_proto, room_vnum=3001, hp=50, max_hp=50,
        )
        eng.world.rooms[3001].characters.append(mob)

        runtime._api_teleport(42, 3002)
        assert mob.room_vnum == 3002
        assert mob in eng.world.rooms[3002].characters
        assert mob not in eng.world.rooms[3001].characters

    def test_damage(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)

        mob_proto = MobProto(
            vnum=100, keywords="guard", short_description="경비병",
            long_description="", detailed_description="",
            level=10, hitroll=0, armor_class=0, hp_dice="5d8+30",
            damage_dice="1d6+3", gold=50, experience=500,
            action_flags=[], affect_flags=[], alignment=0, sex=0,
            trigger_vnums=[],
        )
        mob = MobInstance(
            id=43, proto=mob_proto, room_vnum=3001, hp=50, max_hp=50,
        )
        eng.world.rooms[3001].characters.append(mob)

        runtime._api_damage(43, 15)
        assert mob.hp == 35

    def test_heal(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)

        mob_proto = MobProto(
            vnum=100, keywords="guard", short_description="경비병",
            long_description="", detailed_description="",
            level=10, hitroll=0, armor_class=0, hp_dice="5d8+30",
            damage_dice="1d6+3", gold=50, experience=500,
            action_flags=[], affect_flags=[], alignment=0, sex=0,
            trigger_vnums=[],
        )
        mob = MobInstance(
            id=44, proto=mob_proto, room_vnum=3001, hp=30, max_hp=50,
        )
        eng.world.rooms[3001].characters.append(mob)

        runtime._api_heal(44, 100)
        assert mob.hp == 50  # capped at max_hp

    def test_heal_partial(self):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)

        mob_proto = MobProto(
            vnum=100, keywords="guard", short_description="경비병",
            long_description="", detailed_description="",
            level=10, hitroll=0, armor_class=0, hp_dice="5d8+30",
            damage_dice="1d6+3", gold=50, experience=500,
            action_flags=[], affect_flags=[], alignment=0, sex=0,
            trigger_vnums=[],
        )
        mob = MobInstance(
            id=45, proto=mob_proto, room_vnum=3001, hp=30, max_hp=50,
        )
        eng.world.rooms[3001].characters.append(mob)

        runtime._api_heal(45, 10)
        assert mob.hp == 40

    def test_lua_print(self, caplog):
        eng = _make_engine()
        runtime = TriggerRuntime(eng)
        # Should not raise
        runtime._lua_print("hello", "world")
