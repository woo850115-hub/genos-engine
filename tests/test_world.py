"""Tests for world model — prototypes, instances, dice rolling."""

import pytest
from core.world import (
    Exit, ExtraDesc, ItemProto, MobInstance, MobProto, ObjInstance,
    Room, RoomProto, World, _roll_dice,
)


class TestDiceRolling:
    def test_simple_dice(self):
        for _ in range(100):
            result = _roll_dice("1d6+0")
            assert 1 <= result <= 6

    def test_dice_with_bonus(self):
        for _ in range(100):
            result = _roll_dice("2d6+10")
            assert 12 <= result <= 22

    def test_zero_dice(self):
        result = _roll_dice("0d0+100")
        assert result == 100

    def test_negative_bonus(self):
        result = _roll_dice("0d0+1")
        assert result == 1

    def test_plain_number(self):
        result = _roll_dice("42")
        assert result == 42


class TestRoomProto:
    def test_create(self):
        exit1 = Exit(direction=0, to_vnum=3002)
        room = RoomProto(
            vnum=3001, name="Temple", description="A large temple.",
            zone_vnum=30, sector=0, flags=[],
            exits=[exit1], extra_descs=[], scripts=[], ext={},
        )
        assert room.vnum == 3001
        assert room.name == "Temple"
        assert len(room.exits) == 1
        assert room.exits[0].to_vnum == 3002


class TestMobInstance:
    def test_npc_detection(self):
        proto = MobProto(
            vnum=100, keywords="goblin", short_desc="A goblin",
            long_desc="A goblin stands here.", detail_desc="",
            level=5, max_hp=54, max_mana=0, max_move=0,
            armor_class=90, hitroll=3, damroll=0,
            damage_dice="1d6+2", gold=10, experience=100,
            alignment=-500, sex=1, position=8,
            class_id=0, race_id=0,
            act_flags=[], aff_flags=[], stats={}, skills={},
            scripts=[], ext={},
        )
        mob = MobInstance(id=1, proto=proto, room_vnum=3001, hp=30, max_hp=30)
        assert mob.is_npc is True
        assert mob.name == "A goblin"

    def test_player_detection(self):
        proto = MobProto(
            vnum=-1, keywords="player", short_desc="Player",
            long_desc="", detail_desc="",
            level=1, max_hp=1, max_mana=0, max_move=0,
            armor_class=100, hitroll=0, damroll=0,
            damage_dice="1d4+0", gold=0, experience=0,
            alignment=0, sex=0, position=8,
            class_id=0, race_id=0,
            act_flags=[], aff_flags=[], stats={}, skills={},
            scripts=[], ext={},
        )
        mob = MobInstance(
            id=2, proto=proto, room_vnum=3001, hp=20, max_hp=20,
            player_id=1, player_name="TestPlayer",
        )
        assert mob.is_npc is False
        assert mob.name == "TestPlayer"


class TestWorld:
    def test_init(self):
        w = World()
        assert len(w.rooms) == 0
        assert len(w.item_protos) == 0

    def test_get_room_missing(self):
        w = World()
        assert w.get_room(9999) is None

    def test_create_mob(self):
        w = World()
        proto = MobProto(
            vnum=100, keywords="rat", short_desc="A rat",
            long_desc="A rat scurries here.", detail_desc="",
            level=1, max_hp=5, max_mana=0, max_move=0,
            armor_class=100, hitroll=0, damroll=0,
            damage_dice="1d2+0", gold=0, experience=10,
            alignment=0, sex=0, position=8,
            class_id=0, race_id=0,
            act_flags=[], aff_flags=[], stats={}, skills={},
            scripts=[], ext={},
        )
        w.mob_protos[100] = proto
        room_proto = RoomProto(
            vnum=3001, name="Test", description="Test room",
            zone_vnum=30, sector=0, flags=[],
            exits=[], extra_descs=[], scripts=[], ext={},
        )
        w.rooms[3001] = Room(proto=room_proto)

        mob = w.create_mob(100, 3001)
        assert mob is not None
        assert mob.proto.vnum == 100
        assert mob.room_vnum == 3001
        assert mob in w.rooms[3001].characters

    def test_create_obj(self):
        w = World()
        proto = ItemProto(
            vnum=200, keywords="sword", short_desc="A sword",
            long_desc="A sword lies here.", item_type="weapon",
            weight=5, cost=100, min_level=0,
            wear_slots=["wield"], flags=["magic"],
            values={"damage": "3d6+0", "weapon_type": "slash"},
            affects=[], extra_descs=[], scripts=[], ext={},
        )
        w.item_protos[200] = proto
        obj = w.create_obj(200)
        assert obj is not None
        assert obj.proto.vnum == 200

    def test_char_to_room(self):
        w = World()
        room1 = RoomProto(vnum=1, name="Room 1", description="",
                          zone_vnum=0, sector=0, flags=[],
                          exits=[], extra_descs=[], scripts=[], ext={})
        room2 = RoomProto(vnum=2, name="Room 2", description="",
                          zone_vnum=0, sector=0, flags=[],
                          exits=[], extra_descs=[], scripts=[], ext={})
        w.rooms[1] = Room(proto=room1)
        w.rooms[2] = Room(proto=room2)

        proto = MobProto(
            vnum=1, keywords="test", short_desc="Test",
            long_desc="", detail_desc="",
            level=1, max_hp=2, max_mana=0, max_move=0,
            armor_class=100, hitroll=0, damroll=0,
            damage_dice="1d1+0", gold=0, experience=0,
            alignment=0, sex=0, position=8,
            class_id=0, race_id=0,
            act_flags=[], aff_flags=[], stats={}, skills={},
            scripts=[], ext={},
        )
        mob = MobInstance(id=99, proto=proto, room_vnum=1, hp=10, max_hp=10)
        w.rooms[1].characters.append(mob)

        w.char_to_room(mob, 2)
        assert mob.room_vnum == 2
        assert mob not in w.rooms[1].characters
        assert mob in w.rooms[2].characters
