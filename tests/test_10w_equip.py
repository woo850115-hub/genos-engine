"""Tests for 10woongi equipment system (22 slots)."""

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.world import (
    ItemProto, MobInstance, MobProto, ObjInstance, Room, RoomProto, World,
    _next_id,
)


def _import_items():
    return importlib.import_module("games.10woongi.commands.items")


def _import_constants():
    return importlib.import_module("games.10woongi.constants")


def _make_session(char=None, world=None, engine=None):
    session = MagicMock()
    session.send_line = AsyncMock()
    session.character = char
    session.player_data = {"level": 1}
    session.config = {"world": {"start_room": 1392841419}}
    if engine:
        session.engine = engine
    else:
        session.engine = MagicMock()
        session.engine.world = world or World()
    return session


def _make_item(vnum=100, wear_flags=None, keywords="검"):
    proto = ItemProto(
        vnum=vnum, keywords=keywords,
        short_description=f"테스트 {keywords}",
        long_description=f"테스트 {keywords}이(가) 놓여 있습니다.",
        item_type=5, extra_flags=[], wear_flags=wear_flags or [4],
        values=[0, 3, 8, 0], weight=5, cost=100, rent=10,
        affects=[], extra_descs=[], trigger_vnums=[],
    )
    return ObjInstance(id=_next_id(), proto=proto, values=list(proto.values))


def _make_char(room_vnum=1):
    proto = MobProto(
        vnum=-1, keywords="player", short_description="테스터",
        long_description="", detailed_description="",
        level=10, hitroll=5, armor_class=50,
        hp_dice="0d0+100", damage_dice="1d6+2",
        gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=1, trigger_vnums=[],
    )
    return MobInstance(
        id=_next_id(), proto=proto, room_vnum=room_vnum,
        hp=100, max_hp=100, player_id=1, player_name="테스터",
    )


class TestEquipmentSlots:
    def test_22_slots(self):
        c = _import_constants()
        assert len(c.WEAR_SLOTS) == 22

    def test_ring_slots(self):
        c = _import_constants()
        ring_count = sum(1 for name in c.WEAR_SLOTS.values() if "반지" in name)
        assert ring_count == 10  # 반지1~10


class TestWearCommand:
    async def test_wear_item(self):
        items = _import_items()
        char = _make_char()
        sword = _make_item(wear_flags=[4])  # 갑옷 슬롯
        char.inventory.append(sword)
        sword.carried_by = char

        session = _make_session(char=char)
        await items.do_wear(session, "검")

        assert 4 in char.equipment
        assert char.equipment[4] is sword
        assert sword not in char.inventory

    async def test_wear_nothing_in_inventory(self):
        items = _import_items()
        char = _make_char()
        session = _make_session(char=char)
        await items.do_wear(session, "검")
        session.send_line.assert_called()

    async def test_wear_rings_sequential(self):
        """Multiple rings should fill slots 9, 13, 14, ..."""
        items = _import_items()
        char = _make_char()

        ring_slots = [9, 13, 14, 15, 16, 17, 18, 19, 20, 21]
        for i, expected_slot in enumerate(ring_slots):
            ring = _make_item(vnum=200 + i, wear_flags=[9], keywords=f"반지{i+1}")
            char.inventory.append(ring)
            ring.carried_by = char

            session = _make_session(char=char)
            await items.do_wear(session, f"반지{i+1}")
            assert expected_slot in char.equipment

        # All 10 ring slots filled
        assert len([s for s in char.equipment if s in ring_slots]) == 10


class TestRemoveCommand:
    async def test_remove_item(self):
        items = _import_items()
        char = _make_char()
        sword = _make_item()
        char.equipment[4] = sword
        sword.worn_by = char
        sword.wear_pos = 4

        session = _make_session(char=char)
        await items.do_remove(session, "검")

        assert 4 not in char.equipment
        assert sword in char.inventory

    async def test_remove_nothing(self):
        items = _import_items()
        char = _make_char()
        session = _make_session(char=char)
        await items.do_remove(session, "없는물건")
        session.send_line.assert_called()


class TestGetDropCommands:
    async def test_get_from_room(self):
        items = _import_items()
        world = World()
        room_proto = RoomProto(
            vnum=1, name="Test", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        world.rooms[1] = Room(proto=room_proto)

        char = _make_char(room_vnum=1)
        world.rooms[1].characters.append(char)

        sword = _make_item()
        sword.room_vnum = 1
        world.rooms[1].objects.append(sword)

        session = _make_session(char=char, world=world)
        session.engine.world = world

        await items.do_get(session, "검")
        assert sword in char.inventory
        assert sword not in world.rooms[1].objects

    async def test_drop_to_room(self):
        items = _import_items()
        world = World()
        room_proto = RoomProto(
            vnum=1, name="Test", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        world.rooms[1] = Room(proto=room_proto)

        char = _make_char(room_vnum=1)
        sword = _make_item()
        char.inventory.append(sword)
        sword.carried_by = char

        session = _make_session(char=char, world=world)
        session.engine.world = world

        await items.do_drop(session, "검")
        assert sword not in char.inventory
        assert sword in world.rooms[1].objects
