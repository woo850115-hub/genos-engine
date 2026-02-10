"""Sprint 2 tests — social commands, help search, position commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine
from core.world import (
    Exit, MobInstance, MobProto, Room, RoomProto, World,
)


def _make_world_with_socials():
    w = World()
    room = RoomProto(
        vnum=1, name="방", description="방입니다.",
        zone_number=0, sector_type=0, room_flags=[],
        exits=[], extra_descs=[], trigger_vnums=[],
    )
    w.rooms[1] = Room(proto=room)
    w.socials = {
        "smile": {
            "command": "smile",
            "no_arg_to_char": "You smile happily.",
            "no_arg_to_room": "$n smiles happily.",
            "found_to_char": "You smile at $N.",
            "found_to_room": "$n smiles at $N.",
            "found_to_victim": "$n smiles at you.",
            "not_found": "Smile at whom?",
            "self_to_char": "You smile at yourself.",
            "self_to_room": "$n smiles at $nself.",
        },
        "nod": {
            "command": "nod",
            "no_arg_to_char": "You nod solemnly.",
            "no_arg_to_room": "$n nods solemnly.",
            "found_to_char": "You nod at $N.",
            "found_to_room": "$n nods at $N.",
            "found_to_victim": "$n nods at you.",
            "not_found": "Nod at whom?",
            "self_to_char": "",
            "self_to_room": "",
        },
    }
    w.help_entries = [
        {"keywords": ["HELP", "help"], "min_level": 0, "text": "This is the help system."},
        {"keywords": ["LOOK", "look"], "min_level": 0, "text": "Look around the room."},
        {"keywords": ["SCORE"], "min_level": 0, "text": "View your stats."},
        {"keywords": ["ATTACK", "KILL"], "min_level": 0, "text": "Attack a target."},
    ]
    return w


def _make_engine_session(world):
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 1}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    eng._load_korean_mappings()
    eng.game_name = "tbamud"

    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.engine = eng
    session.player_data = {"id": 1, "name": "플레이어", "level": 1, "aliases": {}}

    proto = MobProto(
        vnum=-1, keywords="플레이어", short_description="플레이어",
        long_description="", detailed_description="",
        level=1, hitroll=0, armor_class=100, hp_dice="0d0+0",
        damage_dice="1d4+0", gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=0,
        trigger_vnums=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=1, hp=20, max_hp=20,
        player_id=1, player_name="플레이어", session=session,
    )
    session.character = char
    world.rooms[1].characters.append(char)
    return eng, session


class TestSocialCommands:
    @pytest.mark.asyncio
    async def test_social_no_target(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng._do_social(session, "smile", "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("smile happily" in c for c in calls)

    @pytest.mark.asyncio
    async def test_social_target_not_found(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng._do_social(session, "smile", "nobody")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("Smile at whom" in c for c in calls)

    @pytest.mark.asyncio
    async def test_social_with_target(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)

        # Add NPC target
        mob_proto = MobProto(
            vnum=50, keywords="goblin 고블린", short_description="고블린",
            long_description="고블린이 서 있습니다.", detailed_description="",
            level=1, hitroll=0, armor_class=100, hp_dice="1d1+1",
            damage_dice="1d1+0", gold=0, experience=5,
            action_flags=[], affect_flags=[], alignment=0, sex=0,
            trigger_vnums=[],
        )
        mob = MobInstance(id=50, proto=mob_proto, room_vnum=1, hp=5, max_hp=5)
        w.rooms[1].characters.append(mob)

        await eng._do_social(session, "smile", "goblin")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("smile at" in c for c in calls)

    @pytest.mark.asyncio
    async def test_social_dispatch_via_command(self):
        """Social commands should be dispatched by process_command."""
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.process_command(session, "nod")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("nod" in c.lower() for c in calls)


class TestHelpSearch:
    @pytest.mark.asyncio
    async def test_exact_match(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_help(session, "help")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("help system" in c for c in calls)

    @pytest.mark.asyncio
    async def test_partial_match_single(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_help(session, "scor")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("stats" in c for c in calls)

    @pytest.mark.asyncio
    async def test_partial_match_multiple(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        # "l" matches LOOK and KILL → multiple
        await eng.do_help(session, "l")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("여러 도움말" in c or "Look" in c for c in calls)

    @pytest.mark.asyncio
    async def test_no_match(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_help(session, "nonexistent")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("없습니다" in c for c in calls)


class TestPositionCommands:
    @pytest.mark.asyncio
    async def test_rest(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_rest(session, "")
        assert session.character.position == Engine.POS_RESTING
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("쉬기" in c for c in calls)

    @pytest.mark.asyncio
    async def test_sit(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_sit(session, "")
        assert session.character.position == Engine.POS_SITTING

    @pytest.mark.asyncio
    async def test_stand_from_rest(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        session.character.position = Engine.POS_RESTING
        await eng.do_stand(session, "")
        assert session.character.position == Engine.POS_STANDING

    @pytest.mark.asyncio
    async def test_sleep(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_sleep(session, "")
        assert session.character.position == Engine.POS_SLEEPING

    @pytest.mark.asyncio
    async def test_rest_while_fighting(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        session.character.fighting = MagicMock()
        await eng.do_rest(session, "")
        assert session.character.position != Engine.POS_RESTING
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("전투 중" in c for c in calls)

    @pytest.mark.asyncio
    async def test_already_standing(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_stand(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("이미 서" in c for c in calls)


class TestCombatStubs:
    @pytest.mark.asyncio
    async def test_kill_no_args(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_kill(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("누구를" in c for c in calls)

    @pytest.mark.asyncio
    async def test_kill_target(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)

        mob_proto = MobProto(
            vnum=50, keywords="goblin 고블린", short_description="고블린",
            long_description="고블린이 서 있습니다.", detailed_description="",
            level=1, hitroll=0, armor_class=100, hp_dice="1d1+1",
            damage_dice="1d1+0", gold=0, experience=5,
            action_flags=[], affect_flags=[], alignment=0, sex=0,
            trigger_vnums=[],
        )
        mob = MobInstance(id=50, proto=mob_proto, room_vnum=1, hp=5, max_hp=5)
        w.rooms[1].characters.append(mob)

        await eng.do_kill(session, "goblin")
        assert session.character.fighting is mob
        assert mob.fighting is session.character

    @pytest.mark.asyncio
    async def test_flee_not_fighting(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        await eng.do_flee(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("전투 중이 아닙니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_quit_while_fighting(self):
        w = _make_world_with_socials()
        eng, session = _make_engine_session(w)
        session.character.fighting = MagicMock()
        session.save_character = AsyncMock()
        session.conn = MagicMock()
        session.conn.close = AsyncMock()
        await eng.do_quit(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("전투 중" in c for c in calls)
