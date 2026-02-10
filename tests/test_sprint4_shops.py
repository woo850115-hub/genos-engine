"""Sprint 4 tests — shop system."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine
from core.world import (
    MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, Shop, World,
)
from games.tbamud.shops import _find_shop, _is_open


def _make_shop_world():
    """World with a shop: keeper vnum=100 in room 3001."""
    w = World()
    room = RoomProto(
        vnum=3001, name="상점", description="작은 상점입니다.",
        zone_number=30, sector_type=0, room_flags=[],
        exits=[], extra_descs=[], trigger_vnums=[],
    )
    w.rooms[3001] = Room(proto=room)

    # Item proto for sale
    sword_proto = ItemProto(
        vnum=200, keywords="sword 검 장검", short_description="멋진 장검",
        long_description="멋진 장검이 놓여있습니다.", item_type=5,
        extra_flags=[], wear_flags=[], values=[0, 0, 0, 3],
        weight=10, cost=100, rent=10, affects=[], extra_descs=[], trigger_vnums=[],
    )
    shield_proto = ItemProto(
        vnum=201, keywords="shield 방패", short_description="튼튼한 방패",
        long_description="", item_type=9,
        extra_flags=[], wear_flags=[], values=[0, 0, 0, 0],
        weight=15, cost=200, rent=20, affects=[], extra_descs=[], trigger_vnums=[],
    )
    w.item_protos[200] = sword_proto
    w.item_protos[201] = shield_proto

    # Shop
    shop = Shop(
        vnum=1, keeper_vnum=100, selling_items=[200, 201],
        profit_buy=1.0, profit_sell=0.5,
        shop_room=3001, open1=0, close1=28, open2=0, close2=0,
    )
    w.shops[100] = shop

    # Shopkeeper NPC
    keeper_proto = MobProto(
        vnum=100, keywords="shopkeeper 상인", short_description="상인",
        long_description="상인이 서 있습니다.", detailed_description="",
        level=20, hitroll=0, armor_class=0, hp_dice="10d10+100",
        damage_dice="1d8+5", gold=10000, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    keeper = MobInstance(
        id=100, proto=keeper_proto, room_vnum=3001, hp=200, max_hp=200,
    )
    w.rooms[3001].characters.append(keeper)
    return w


def _make_engine_session(world):
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 3001}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    eng.game_name = "tbamud"
    # Register shop commands
    from games.tbamud.shops import register
    register(eng)

    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.engine = eng
    session.player_data = {"id": 1, "name": "테스터", "level": 10, "aliases": {}}

    proto = MobProto(
        vnum=-1, keywords="테스터", short_description="테스터",
        long_description="", detailed_description="",
        level=10, hitroll=0, armor_class=100, hp_dice="0d0+0",
        damage_dice="1d4+0", gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=3001, hp=100, max_hp=100,
        player_id=1, player_name="테스터", session=session,
        gold=500,
    )
    session.character = char
    world.rooms[3001].characters.append(char)
    return eng, session


class TestFindShop:
    def test_finds_shop_in_room(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)
        shop, keeper = _find_shop(eng, session)
        assert shop is not None
        assert keeper is not None
        assert shop.keeper_vnum == 100

    def test_no_shop_empty_room(self):
        w = World()
        room = RoomProto(
            vnum=3001, name="방", description="", zone_number=0, sector_type=0,
            room_flags=[], exits=[], extra_descs=[], trigger_vnums=[],
        )
        w.rooms[3001] = Room(proto=room)
        eng, session = _make_engine_session(w)
        shop, keeper = _find_shop(eng, session)
        assert shop is None


class TestIsOpen:
    def test_open_during_hours(self):
        shop = Shop(vnum=1, keeper_vnum=1, selling_items=[], profit_buy=1.0,
                    profit_sell=0.5, shop_room=1, open1=6, close1=20, open2=0, close2=0)
        assert _is_open(shop, hour=12)

    def test_closed_after_hours(self):
        shop = Shop(vnum=1, keeper_vnum=1, selling_items=[], profit_buy=1.0,
                    profit_sell=0.5, shop_room=1, open1=6, close1=20, open2=0, close2=0)
        assert not _is_open(shop, hour=22)


class TestBuyCommand:
    @pytest.mark.asyncio
    async def test_buy_item(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)
        char = session.character
        char.gold = 500

        from games.tbamud.shops import do_buy
        await do_buy(session, "검")
        assert char.gold == 400  # 100 gold for sword
        assert len(char.inventory) == 1
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("구입" in c for c in calls)

    @pytest.mark.asyncio
    async def test_buy_not_enough_gold(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)
        char = session.character
        char.gold = 10

        from games.tbamud.shops import do_buy
        await do_buy(session, "방패")
        assert len(char.inventory) == 0
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("부족" in c for c in calls)

    @pytest.mark.asyncio
    async def test_buy_no_args(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)

        from games.tbamud.shops import do_buy
        await do_buy(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("사시겠습니까" in c for c in calls)

    @pytest.mark.asyncio
    async def test_buy_nonexistent(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)

        from games.tbamud.shops import do_buy
        await do_buy(session, "unicorn")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("없습니다" in c for c in calls)


class TestSellCommand:
    @pytest.mark.asyncio
    async def test_sell_item(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)
        char = session.character

        obj = ObjInstance(id=99, proto=w.item_protos[200])
        char.inventory.append(obj)
        initial_gold = char.gold

        from games.tbamud.shops import do_sell
        await do_sell(session, "검")
        assert char.gold > initial_gold
        assert len(char.inventory) == 0
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("판매" in c for c in calls)

    @pytest.mark.asyncio
    async def test_sell_no_item(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)

        from games.tbamud.shops import do_sell
        await do_sell(session, "검")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("가지고 있지 않" in c for c in calls)


class TestListCommand:
    @pytest.mark.asyncio
    async def test_list_shows_items(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)

        from games.tbamud.shops import do_list
        await do_list(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("장검" in c for c in calls)
        assert any("방패" in c for c in calls)

    @pytest.mark.asyncio
    async def test_list_no_shop(self):
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
            player_id=1, player_name="t", session=session,
        )
        w.rooms[1].characters.append(session.character)

        from games.tbamud.shops import do_list
        await do_list(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("상점이 없습니다" in c for c in calls)


class TestAppraiseCommand:
    @pytest.mark.asyncio
    async def test_appraise_item(self):
        w = _make_shop_world()
        eng, session = _make_engine_session(w)
        char = session.character

        obj = ObjInstance(id=99, proto=w.item_protos[200])
        char.inventory.append(obj)

        from games.tbamud.shops import do_appraise
        await do_appraise(session, "검")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("골드" in c for c in calls)
