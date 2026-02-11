"""Tests for 10woongi world loading — Exit key compat, large VNUM dicts."""

import json

import pytest
from core.world import (
    Exit, ExtraDesc, MobInstance, MobProto, ObjInstance, Room, RoomProto,
    World, ItemProto,
)


class TestExitKeyCompat:
    """Exit JSON key compatibility: dir/dest (10woongi) vs direction/to_room (tbaMUD)."""

    def test_tbamud_style_exit(self):
        """Traditional direction/to_room keys still work."""
        exit_data = {"direction": 0, "to_room": 3002, "keywords": "door", "description": "A door."}
        ex = Exit(
            direction=exit_data.get("direction", exit_data.get("dir", 0)),
            to_room=exit_data.get("to_room", exit_data.get("dest", -1)),
            keywords=exit_data.get("keywords", exit_data.get("keyword", "")),
            description=exit_data.get("description", exit_data.get("desc", "")),
        )
        assert ex.direction == 0
        assert ex.to_room == 3002
        assert ex.keywords == "door"
        assert ex.description == "A door."

    def test_10woongi_style_exit(self):
        """10woongi dir/dest keys work via fallback."""
        exit_data = {"dir": 3, "dest": 964618230, "desc": "", "keyword": ""}
        ex = Exit(
            direction=exit_data.get("direction", exit_data.get("dir", 0)),
            to_room=exit_data.get("to_room", exit_data.get("dest", -1)),
            keywords=exit_data.get("keywords", exit_data.get("keyword", "")),
            description=exit_data.get("description", exit_data.get("desc", "")),
        )
        assert ex.direction == 3
        assert ex.to_room == 964618230
        assert ex.keywords == ""
        assert ex.description == ""

    def test_mixed_keys(self):
        """Mix of both styles (direction + dest) — direction takes priority."""
        exit_data = {"direction": 1, "dest": 12345, "keywords": "gate"}
        ex = Exit(
            direction=exit_data.get("direction", exit_data.get("dir", 0)),
            to_room=exit_data.get("to_room", exit_data.get("dest", -1)),
            keywords=exit_data.get("keywords", exit_data.get("keyword", "")),
        )
        assert ex.direction == 1
        assert ex.to_room == 12345


class TestLargeVnumDict:
    """Test that World handles large SHA-256 based VNUMs (31-bit integers)."""

    def test_large_vnum_room(self):
        """Rooms with large VNUM values (SHA-256 hash) work correctly."""
        w = World()
        large_vnum = 1392841419  # START_ROOM
        proto = RoomProto(
            vnum=large_vnum, name="장백성 마을 광장",
            description="장백성의 마을 광장입니다.",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        w.rooms[large_vnum] = Room(proto=proto)
        room = w.get_room(large_vnum)
        assert room is not None
        assert room.vnum == large_vnum
        assert room.name == "장백성 마을 광장"

    def test_large_vnum_mob(self):
        """Mobs with large VNUM values work correctly."""
        w = World()
        large_vnum = 2000000000
        proto = MobProto(
            vnum=large_vnum, keywords="용사", short_description="용사",
            long_description="용사가 서 있습니다.", detailed_description="",
            level=10, hitroll=5, armor_class=50,
            hp_dice="5d10+50", damage_dice="2d6+3",
            gold=100, experience=500,
            action_flags=[], affect_flags=[], alignment=0, sex=1,
            trigger_vnums=[],
        )
        w.mob_protos[large_vnum] = proto
        room_proto = RoomProto(
            vnum=1, name="Test", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        w.rooms[1] = Room(proto=room_proto)
        mob = w.create_mob(large_vnum, 1)
        assert mob is not None
        assert mob.proto.vnum == large_vnum

    def test_large_vnum_item(self):
        """Items with large VNUM values work correctly."""
        w = World()
        large_vnum = 1800000000
        proto = ItemProto(
            vnum=large_vnum, keywords="검",
            short_description="명검", long_description="명검이 놓여 있습니다.",
            item_type=5, extra_flags=[], wear_flags=[16],
            values=[0, 3, 8, 0], weight=5, cost=500, rent=10,
            affects=[], extra_descs=[], trigger_vnums=[],
        )
        w.item_protos[large_vnum] = proto
        obj = w.create_obj(large_vnum)
        assert obj is not None
        assert obj.proto.vnum == large_vnum

    def test_many_rooms_performance(self):
        """Create 1000 rooms with large VNUMs — dict handles it fine."""
        w = World()
        for i in range(1000):
            vnum = 1000000000 + i * 13579
            proto = RoomProto(
                vnum=vnum, name=f"Room {i}", description="",
                zone_number=0, sector_type=0, room_flags=[],
                exits=[], extra_descs=[], trigger_vnums=[],
            )
            w.rooms[vnum] = Room(proto=proto)
        assert len(w.rooms) == 1000

    def test_exit_dest_navigation(self):
        """Navigate between rooms using 10woongi-style exits."""
        w = World()
        vnum_a = 1392841419
        vnum_b = 964618230

        exit_ab = Exit(direction=0, to_room=vnum_b)
        exit_ba = Exit(direction=2, to_room=vnum_a)

        room_a = RoomProto(
            vnum=vnum_a, name="A", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[exit_ab], extra_descs=[], trigger_vnums=[],
        )
        room_b = RoomProto(
            vnum=vnum_b, name="B", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[exit_ba], extra_descs=[], trigger_vnums=[],
        )
        w.rooms[vnum_a] = Room(proto=room_a)
        w.rooms[vnum_b] = Room(proto=room_b)

        # Navigate A → B
        room = w.get_room(vnum_a)
        assert room is not None
        dest_vnum = room.proto.exits[0].to_room
        dest = w.get_room(dest_vnum)
        assert dest is not None
        assert dest.name == "B"

        # Navigate B → A
        back_vnum = dest.proto.exits[0].to_room
        back = w.get_room(back_vnum)
        assert back is not None
        assert back.name == "A"


class TestDoorStatesWithLargeVnums:
    def test_door_init(self):
        """Door initialization works with large VNUMs."""
        ex = Exit(
            direction=0, to_room=964618230,
            door_flags=3, key_vnum=1500000000,
        )
        proto = RoomProto(
            vnum=1392841419, name="Test", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[ex], extra_descs=[], trigger_vnums=[],
        )
        room = Room(proto=proto)
        room.init_doors()
        assert room.has_door(0)
        assert room.is_door_closed(0)

    def test_no_door(self):
        """Exits without doors don't create door_states."""
        ex = Exit(direction=1, to_room=100000000, door_flags=0)
        proto = RoomProto(
            vnum=200000000, name="Open", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[ex], extra_descs=[], trigger_vnums=[],
        )
        room = Room(proto=proto)
        room.init_doors()
        assert not room.has_door(1)


class TestExitDirection36:
    """10woongi has direction 36 (밖) for custom exits via keyword."""

    def test_exit_direction_beyond_5(self):
        """Directions > 5 are allowed and stored correctly."""
        ex = Exit(direction=36, to_room=500000000, keywords="밖")
        proto = RoomProto(
            vnum=100000000, name="Room", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[ex], extra_descs=[], trigger_vnums=[],
        )
        room = Room(proto=proto)
        assert room.proto.exits[0].direction == 36
        assert room.proto.exits[0].keywords == "밖"

    def test_multiple_custom_exits(self):
        """Multiple custom direction exits coexist."""
        exits = [
            Exit(direction=0, to_room=100000001),
            Exit(direction=36, to_room=100000002, keywords="밖"),
            Exit(direction=37, to_room=100000003, keywords="안"),
        ]
        proto = RoomProto(
            vnum=100000000, name="Hub", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=exits, extra_descs=[], trigger_vnums=[],
        )
        room = Room(proto=proto)
        assert len(room.proto.exits) == 3
