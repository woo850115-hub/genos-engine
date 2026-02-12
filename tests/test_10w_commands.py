"""Tests for 10woongi general commands — movement, info, comm, admin."""

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.world import (
    ItemProto, MobInstance, MobProto, ObjInstance, Room, RoomProto, World,
    _next_id,
)


def _import_movement():
    return importlib.import_module("games.10woongi.commands.movement")


def _import_info():
    return importlib.import_module("games.10woongi.commands.info")


def _import_comm():
    return importlib.import_module("games.10woongi.commands.comm")


def _import_admin():
    return importlib.import_module("games.10woongi.commands.admin")


def _import_constants():
    return importlib.import_module("games.10woongi.constants")


def _make_world_with_rooms(*vnums):
    world = World()
    for vnum in vnums:
        room_proto = RoomProto(
            vnum=vnum, name=f"Room{vnum}", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        world.rooms[vnum] = Room(proto=room_proto)
    return world


def _make_char(room_vnum=1, level=10, is_npc=False):
    proto = MobProto(
        vnum=-1, keywords="player", short_description="테스터",
        long_description="", detailed_description="",
        level=level, hitroll=0, armor_class=50,
        hp_dice="0d0+100", damage_dice="1d6+2",
        gold=500, experience=1000,
        action_flags=[], affect_flags=[], alignment=0, sex=1, trigger_vnums=[],
    )
    char = MobInstance(
        id=_next_id(), proto=proto, room_vnum=room_vnum,
        hp=100, max_hp=100,
        player_id=None if is_npc else 1,
        player_name=None if is_npc else "테스터",
    )
    char.player_level = level
    char.mana = 50
    char.max_mana = 50
    char.move = 80
    char.max_move = 80
    char.class_id = 1
    char.extensions = {
        "stats": {
            "stamina": 15, "agility": 14, "wisdom": 13,
            "bone": 16, "inner": 12, "spirit": 11,
        }
    }
    return char


def _make_npc(room_vnum=1, vnum=100, keywords="오크", level=5):
    proto = MobProto(
        vnum=vnum, keywords=keywords, short_description=keywords,
        long_description="", detailed_description="",
        level=level, hitroll=0, armor_class=50,
        hp_dice="0d0+50", damage_dice="1d4+1",
        gold=100, experience=200,
        action_flags=["ISNPC"], affect_flags=[], alignment=0, sex=0, trigger_vnums=[],
    )
    return MobInstance(
        id=_next_id(), proto=proto, room_vnum=room_vnum,
        hp=50, max_hp=50,
    )


def _make_session(char=None, world=None, admin=False):
    session = MagicMock()
    session.send_line = AsyncMock()
    session.character = char
    session.player_data = {"level": 100 if admin else 1, "sex": 1}
    c = _import_constants()
    session.config = {"world": {"start_room": c.START_ROOM}}
    engine = MagicMock()
    engine.world = world or World()
    engine.players = {}
    engine.do_look = AsyncMock()
    session.engine = engine
    return session


# ─── Movement ────────────────────────────────────────────────────

class TestRecall:
    async def test_recall_teleports(self):
        mv = _import_movement()
        c = _import_constants()
        world = _make_world_with_rooms(1, c.START_ROOM)
        char = _make_char(room_vnum=1)
        world.rooms[1].characters.append(char)

        session = _make_session(char=char, world=world)
        await mv.do_recall(session, "")

        assert char.room_vnum == c.START_ROOM
        session.engine.do_look.assert_called_once()

    async def test_recall_fighting_denied(self):
        mv = _import_movement()
        char = _make_char()
        char.fighting = _make_npc()

        session = _make_session(char=char)
        await mv.do_recall(session, "")

        session.send_line.assert_called()
        msg = session.send_line.call_args[0][0]
        assert "전투" in msg


# ─── Info ─────────────────────────────────────────────────────────

class TestWscore:
    async def test_wscore_shows_stats(self):
        info = _import_info()
        char = _make_char()
        session = _make_session(char=char)
        await info.do_score(session, "")

        calls = session.send_line.call_args_list
        output = calls[0][0][0]
        assert "체력" in output
        assert "민첩" in output
        assert "기골" in output
        assert "내공" in output

    async def test_wscore_shows_hp_sp_mp(self):
        info = _import_info()
        char = _make_char()
        session = _make_session(char=char)
        await info.do_score(session, "")
        output = session.send_line.call_args[0][0]
        # Original box-drawing format uses Korean labels
        assert "체력" in output or "내력" in output or "이동" in output


class TestConsider:
    async def test_consider_easy(self):
        info = _import_info()
        world = _make_world_with_rooms(1)
        char = _make_char(room_vnum=1, level=20)
        npc = _make_npc(room_vnum=1, level=5)
        world.rooms[1].characters.extend([char, npc])

        session = _make_session(char=char, world=world)
        await info.do_consider(session, "오크")

        msg = session.send_line.call_args[0][0]
        assert "쉬운" in msg or "웃음" in msg

    async def test_consider_no_target(self):
        info = _import_info()
        world = _make_world_with_rooms(1)
        char = _make_char(room_vnum=1)
        world.rooms[1].characters.append(char)

        session = _make_session(char=char, world=world)
        await info.do_consider(session, "없는놈")
        msg = session.send_line.call_args[0][0]
        assert "찾을 수 없습니다" in msg


class TestEquipmentCmd:
    async def test_equipment_empty(self):
        info = _import_info()
        char = _make_char()
        session = _make_session(char=char)
        await info.do_equipment(session, "")

        calls = [c[0][0] for c in session.send_line.call_args_list]
        assert any("없" in c or "장비" in c for c in calls)


# ─── Comm ─────────────────────────────────────────────────────────

class TestTell:
    async def test_tell_sends_message(self):
        comm = _import_comm()
        char = _make_char()
        session = _make_session(char=char)

        target_session = MagicMock()
        target_session.send_line = AsyncMock()
        session.engine.players = {"상대방": target_session}

        await comm.do_tell(session, "상대방 안녕하세요")

        session.send_line.assert_called()
        target_session.send_line.assert_called()

    async def test_tell_no_target(self):
        comm = _import_comm()
        char = _make_char()
        session = _make_session(char=char)
        session.engine.players = {}

        await comm.do_tell(session, "없는사람 테스트")
        msg = session.send_line.call_args[0][0]
        assert "찾을 수 없습니다" in msg


class TestShout:
    async def test_shout_broadcasts(self):
        comm = _import_comm()
        char = _make_char()
        session = _make_session(char=char)

        other_session = MagicMock()
        other_session.send_line = AsyncMock()
        other_session.character = _make_char()
        session.engine.players = {"other": other_session}

        await comm.do_shout(session, "안녕!")
        other_session.send_line.assert_called()


# ─── Admin ────────────────────────────────────────────────────────

class TestAdminGoto:
    async def test_goto_success(self):
        admin = _import_admin()
        world = _make_world_with_rooms(1, 100)
        char = _make_char(room_vnum=1)
        session = _make_session(char=char, world=world, admin=True)
        await admin.do_goto(session, "100")
        session.engine.do_look.assert_called()

    async def test_goto_non_admin(self):
        admin = _import_admin()
        char = _make_char()
        session = _make_session(char=char, admin=False)
        await admin.do_goto(session, "100")
        msg = session.send_line.call_args[0][0]
        assert "권한" in msg


class TestAdminRestore:
    async def test_restore_self(self):
        admin = _import_admin()
        char = _make_char()
        char.hp = 10
        session = _make_session(char=char, admin=True)
        await admin.do_restore(session, "")
        assert char.hp == char.max_hp
