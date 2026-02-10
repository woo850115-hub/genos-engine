"""Sprint 5 tests — admin commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine
from core.world import (
    MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World,
)
from games.tbamud.commands.admin import (
    MIN_ADMIN_LEVEL, _is_admin,
    do_goto, do_load, do_purge, do_stat, do_set,
    do_advance, do_restore, do_reload, do_shutdown,
)


def _make_world():
    w = World()
    room1 = RoomProto(
        vnum=3001, name="광장", description="넓은 광장입니다.",
        zone_number=30, sector_type=0, room_flags=[],
        exits=[], extra_descs=[], trigger_vnums=[100],
    )
    room2 = RoomProto(
        vnum=3002, name="상점", description="작은 상점입니다.",
        zone_number=30, sector_type=0, room_flags=[],
        exits=[], extra_descs=[], trigger_vnums=[],
    )
    w.rooms[3001] = Room(proto=room1)
    w.rooms[3002] = Room(proto=room2)

    mob_proto = MobProto(
        vnum=100, keywords="guard 경비병", short_description="경비병",
        long_description="경비병이 서 있습니다.", detailed_description="",
        level=10, hitroll=0, armor_class=0, hp_dice="5d8+30",
        damage_dice="1d6+3", gold=50, experience=500,
        action_flags=[], affect_flags=[], alignment=0, sex=0,
        trigger_vnums=[],
    )
    w.mob_protos[100] = mob_proto

    item_proto = ItemProto(
        vnum=200, keywords="sword 검", short_description="멋진 검",
        long_description="멋진 검이 놓여있습니다.", item_type=5,
        extra_flags=[], wear_flags=[], values=[0, 0, 0, 3],
        weight=10, cost=100, rent=10, affects=[], extra_descs=[], trigger_vnums=[],
    )
    w.item_protos[200] = item_proto
    return w


def _make_engine_session(world, level=34):
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 3001}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    eng.game_name = "tbamud"
    eng.reload_mgr = MagicMock()
    eng.reload_mgr.queue_game_reload = MagicMock()
    eng.reload_mgr.apply_pending = MagicMock(return_value=[])
    eng._plugin = MagicMock()

    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.engine = eng
    session.player_data = {"id": 1, "name": "관리자", "level": level, "aliases": {}}

    proto = MobProto(
        vnum=-1, keywords="관리자", short_description="관리자",
        long_description="", detailed_description="",
        level=level, hitroll=0, armor_class=100, hp_dice="0d0+0",
        damage_dice="1d4+0", gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=3001, hp=100, max_hp=100,
        mana=100, max_mana=100, move=100, max_move=100,
        player_id=1, player_name="관리자", player_level=level,
        session=session,
    )
    session.character = char
    world.rooms[3001].characters.append(char)
    return eng, session


class TestIsAdmin:
    def test_admin_level(self):
        assert MIN_ADMIN_LEVEL == 31

    def test_is_admin_true(self):
        session = MagicMock()
        proto = MobProto(
            vnum=-1, keywords="t", short_description="t",
            long_description="", detailed_description="",
            level=34, hitroll=0, armor_class=100, hp_dice="0d0+0",
            damage_dice="1d4+0", gold=0, experience=0,
            action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
        )
        session.character = MobInstance(
            id=1, proto=proto, room_vnum=3001, hp=100, max_hp=100,
            player_id=1, player_name="admin", player_level=34,
        )
        assert _is_admin(session)

    def test_is_admin_false(self):
        session = MagicMock()
        proto = MobProto(
            vnum=-1, keywords="t", short_description="t",
            long_description="", detailed_description="",
            level=10, hitroll=0, armor_class=100, hp_dice="0d0+0",
            damage_dice="1d4+0", gold=0, experience=0,
            action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
        )
        session.character = MobInstance(
            id=1, proto=proto, room_vnum=3001, hp=100, max_hp=100,
            player_id=1, player_name="noob", player_level=10,
        )
        assert not _is_admin(session)

    def test_is_admin_no_char(self):
        session = MagicMock()
        session.character = None
        assert not _is_admin(session)


class TestGoto:
    @pytest.mark.asyncio
    async def test_goto_success(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        char = session.character

        await do_goto(session, "3002")
        assert char.room_vnum == 3002
        assert char in w.rooms[3002].characters

    @pytest.mark.asyncio
    async def test_goto_not_admin(self):
        w = _make_world()
        eng, session = _make_engine_session(w, level=10)
        await do_goto(session, "3002")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("권한" in c for c in calls)

    @pytest.mark.asyncio
    async def test_goto_no_args(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_goto(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("어디" in c for c in calls)

    @pytest.mark.asyncio
    async def test_goto_invalid_room(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_goto(session, "99999")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("없습니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_goto_invalid_number(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_goto(session, "abc")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("올바른" in c for c in calls)


class TestLoad:
    @pytest.mark.asyncio
    async def test_load_mob(self):
        w = _make_world()
        eng, session = _make_engine_session(w)

        await do_load(session, "mob 100")
        # Should have created a mob in the room
        npcs = [ch for ch in w.rooms[3001].characters if ch.is_npc]
        assert len(npcs) == 1
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("소환" in c for c in calls)

    @pytest.mark.asyncio
    async def test_load_obj(self):
        w = _make_world()
        eng, session = _make_engine_session(w)

        await do_load(session, "obj 200")
        char = session.character
        assert len(char.inventory) == 1
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("생성" in c for c in calls)

    @pytest.mark.asyncio
    async def test_load_no_args(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_load(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("사용법" in c for c in calls)

    @pytest.mark.asyncio
    async def test_load_invalid_vnum(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_load(session, "mob 99999")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("없습니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_load_not_admin(self):
        w = _make_world()
        eng, session = _make_engine_session(w, level=5)
        await do_load(session, "mob 100")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("권한" in c for c in calls)


class TestPurge:
    @pytest.mark.asyncio
    async def test_purge_room(self):
        w = _make_world()
        eng, session = _make_engine_session(w)

        # Add NPC and object
        mob_proto = w.mob_protos[100]
        npc = MobInstance(
            id=50, proto=mob_proto, room_vnum=3001, hp=50, max_hp=50,
        )
        w.rooms[3001].characters.append(npc)

        item = ObjInstance(id=51, proto=w.item_protos[200])
        w.rooms[3001].objects.append(item)

        await do_purge(session, "")
        # NPC removed, player stays
        npcs = [ch for ch in w.rooms[3001].characters if ch.is_npc]
        assert len(npcs) == 0
        assert len(w.rooms[3001].objects) == 0
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("정화" in c for c in calls)


class TestStat:
    @pytest.mark.asyncio
    async def test_stat_room(self):
        w = _make_world()
        eng, session = _make_engine_session(w)

        await do_stat(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("방 정보" in c for c in calls)
        assert any("3001" in c for c in calls)

    @pytest.mark.asyncio
    async def test_stat_mob(self):
        w = _make_world()
        eng, session = _make_engine_session(w)

        mob_proto = w.mob_protos[100]
        npc = MobInstance(
            id=50, proto=mob_proto, room_vnum=3001, hp=50, max_hp=50,
        )
        w.rooms[3001].characters.append(npc)

        await do_stat(session, "경비병")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("캐릭터" in c for c in calls)

    @pytest.mark.asyncio
    async def test_stat_not_found(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_stat(session, "unicorn")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("찾을 수 없습니다" in c for c in calls)


class TestSet:
    @pytest.mark.asyncio
    async def test_set_level(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        char = session.character

        await do_set(session, "관리자 level 20")
        assert char.player_level == 20
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("레벨" in c for c in calls)

    @pytest.mark.asyncio
    async def test_set_gold(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        char = session.character

        await do_set(session, "관리자 gold 5000")
        assert char.gold == 5000

    @pytest.mark.asyncio
    async def test_set_hp(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        char = session.character

        await do_set(session, "관리자 hp 500")
        assert char.hp == 500

    @pytest.mark.asyncio
    async def test_set_unknown_field(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_set(session, "관리자 unknown 10")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("알 수 없는" in c for c in calls)

    @pytest.mark.asyncio
    async def test_set_not_found(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_set(session, "nobody level 10")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("찾을 수 없습니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_set_no_args(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_set(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("사용법" in c for c in calls)


class TestRestore:
    @pytest.mark.asyncio
    async def test_restore_self(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        char = session.character
        char.hp = 10
        char.mana = 5
        char.move = 3

        await do_restore(session, "")
        assert char.hp == char.max_hp
        assert char.mana == char.max_mana
        assert char.move == char.max_move

    @pytest.mark.asyncio
    async def test_restore_target(self):
        w = _make_world()
        eng, session = _make_engine_session(w)

        # Add another player character
        proto2 = MobProto(
            vnum=-1, keywords="테스터", short_description="테스터",
            long_description="", detailed_description="",
            level=10, hitroll=0, armor_class=100, hp_dice="0d0+0",
            damage_dice="1d4+0", gold=0, experience=0,
            action_flags=[], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
        )
        target = MobInstance(
            id=2, proto=proto2, room_vnum=3001, hp=10, max_hp=100,
            mana=5, max_mana=50, move=3, max_move=80,
            player_id=2, player_name="테스터", session=MagicMock(send_line=AsyncMock()),
        )
        w.rooms[3001].characters.append(target)

        await do_restore(session, "테스터")
        assert target.hp == 100
        assert target.mana == 50
        assert target.move == 80

    @pytest.mark.asyncio
    async def test_restore_not_found(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_restore(session, "존재하지않는")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("찾을 수 없습니다" in c for c in calls)


class TestReload:
    @pytest.mark.asyncio
    async def test_reload_no_modules(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_reload(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("없습니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_reload_with_modules(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        eng.reload_mgr.apply_pending.return_value = ["games.tbamud.shops"]
        await do_reload(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("리로드 완료" in c for c in calls)


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        eng.shutdown = AsyncMock()

        await do_shutdown(session, "")
        eng.shutdown.assert_called_once()
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("종료" in c for c in calls)

    @pytest.mark.asyncio
    async def test_shutdown_not_admin(self):
        w = _make_world()
        eng, session = _make_engine_session(w, level=5)
        eng.shutdown = AsyncMock()

        await do_shutdown(session, "")
        eng.shutdown.assert_not_called()


class TestAdvance:
    @pytest.mark.asyncio
    async def test_advance_redirects(self):
        w = _make_world()
        eng, session = _make_engine_session(w)
        await do_advance(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("set" in c for c in calls)
