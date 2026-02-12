"""Sprint 5 tests — REST API + WebSocket adapter."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.world import (
    MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World,
)


def _make_engine_with_players():
    """Create a minimal engine mock with players."""
    eng = MagicMock()
    eng.game_name = "tbamud"
    eng._tick = 12345
    eng.cmd_handlers = {"look": None, "say": None, "who": None}
    eng.world = World()

    room_proto = RoomProto(
        vnum=3001, name="광장", description="넓은 광장입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[],
    )
    eng.world.rooms[3001] = Room(proto=room_proto)

    # Add a player
    proto = MobProto(
        vnum=-1, keywords="테스터", short_desc="테스터",
        long_desc="", detail_desc="",
        level=10, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=3001, hp=100, max_hp=100,
        player_id=1, player_name="테스터", player_level=10,
    )
    eng.world.rooms[3001].characters.append(char)

    session = MagicMock()
    session.character = char
    eng.players = {"테스터": session}
    eng.sessions = {1: session}

    eng.reload_mgr = MagicMock()
    eng.reload_mgr.queue_game_reload = MagicMock()
    eng.reload_mgr.apply_pending = MagicMock(return_value=[])
    eng._plugin = MagicMock()

    return eng


class TestAPIWho:
    @pytest.mark.asyncio
    async def test_who_endpoint(self):
        from core.api import api_who, _engine
        import core.api as api_mod
        eng = _make_engine_with_players()
        api_mod._engine = eng

        response = await api_who()
        data = response.body
        import json
        result = json.loads(data)
        assert result["count"] == 1
        assert result["players"][0]["name"] == "테스터"
        assert result["players"][0]["level"] == 10

        api_mod._engine = None

    @pytest.mark.asyncio
    async def test_who_empty(self):
        import core.api as api_mod
        eng = _make_engine_with_players()
        eng.players = {}
        api_mod._engine = eng

        from core.api import api_who
        response = await api_who()
        import json
        result = json.loads(response.body)
        assert result["count"] == 0
        assert result["players"] == []

        api_mod._engine = None


class TestAPIStats:
    @pytest.mark.asyncio
    async def test_stats_endpoint(self):
        import core.api as api_mod
        eng = _make_engine_with_players()
        api_mod._engine = eng

        from core.api import api_stats
        response = await api_stats()
        import json
        result = json.loads(response.body)
        assert result["game"] == "tbamud"
        assert result["uptime_ticks"] == 12345
        assert result["players_online"] == 1
        assert result["rooms_loaded"] == 1
        assert result["commands_registered"] == 3

        api_mod._engine = None


class TestAPIReload:
    @pytest.mark.asyncio
    async def test_reload_no_changes(self):
        import core.api as api_mod
        eng = _make_engine_with_players()
        api_mod._engine = eng

        from core.api import api_reload
        response = await api_reload()
        import json
        result = json.loads(response.body)
        assert result["status"] == "ok"
        assert result["reloaded"] == []

        api_mod._engine = None

    @pytest.mark.asyncio
    async def test_reload_with_changes(self):
        import core.api as api_mod
        eng = _make_engine_with_players()
        eng.reload_mgr.apply_pending.return_value = ["games.tbamud.shops"]
        api_mod._engine = eng

        from core.api import api_reload
        response = await api_reload()
        import json
        result = json.loads(response.body)
        assert result["status"] == "ok"
        assert "games.tbamud.shops" in result["reloaded"]
        eng._plugin.register_commands.assert_called_once()

        api_mod._engine = None


class TestAPIRoom:
    @pytest.mark.asyncio
    async def test_room_found(self):
        import core.api as api_mod
        eng = _make_engine_with_players()
        api_mod._engine = eng

        from core.api import api_room
        response = await api_room(3001)
        import json
        result = json.loads(response.body)
        assert result["vnum"] == 3001
        assert result["name"] == "광장"
        assert result["zone"] == 30
        assert len(result["characters"]) == 1

        api_mod._engine = None

    @pytest.mark.asyncio
    async def test_room_not_found(self):
        import core.api as api_mod
        eng = _make_engine_with_players()
        api_mod._engine = eng

        from core.api import api_room
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await api_room(99999)
        assert exc_info.value.status_code == 404

        api_mod._engine = None


class TestWebSocketSession:
    def test_ws_session_init(self):
        from core.api import WebSocketSession
        ws = MagicMock()
        sess = WebSocketSession(ws, 100001)
        assert sess.id == 100001
        assert not sess.closed
        assert sess.addr == ("ws", 0)

    @pytest.mark.asyncio
    async def test_ws_session_send(self):
        from core.api import WebSocketSession
        ws = AsyncMock()
        sess = WebSocketSession(ws, 100001)
        await sess.send("안녕하세요")
        ws.send_text.assert_called_once_with("안녕하세요")

    @pytest.mark.asyncio
    async def test_ws_session_send_line(self):
        from core.api import WebSocketSession
        ws = AsyncMock()
        sess = WebSocketSession(ws, 100001)
        await sess.send_line("테스트")
        ws.send_text.assert_called_once_with("테스트\r\n")

    @pytest.mark.asyncio
    async def test_ws_session_send_closed(self):
        from core.api import WebSocketSession
        ws = AsyncMock()
        sess = WebSocketSession(ws, 100001)
        sess.closed = True
        await sess.send("test")
        ws.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_ws_session_input_queue(self):
        from core.api import WebSocketSession
        ws = MagicMock()
        sess = WebSocketSession(ws, 100001)
        assert not sess.has_input()
        await sess._input_queue.put("look")
        assert sess.has_input()
        result = await sess.get_input()
        assert result == "look"

    @pytest.mark.asyncio
    async def test_ws_session_echo_noop(self):
        from core.api import WebSocketSession
        ws = MagicMock()
        sess = WebSocketSession(ws, 100001)
        # Should not raise
        await sess.set_echo(True)
        await sess.set_echo(False)

    @pytest.mark.asyncio
    async def test_ws_session_close(self):
        from core.api import WebSocketSession
        ws = AsyncMock()
        sess = WebSocketSession(ws, 100001)
        await sess.close()
        assert sess.closed
        ws.close.assert_called_once()


class TestGetEngine:
    def test_get_engine_none(self):
        import core.api as api_mod
        api_mod._engine = None
        from core.api import get_engine
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_engine()
        assert exc_info.value.status_code == 503

    def test_get_engine_present(self):
        import core.api as api_mod
        eng = MagicMock()
        api_mod._engine = eng
        from core.api import get_engine
        assert get_engine() is eng
        api_mod._engine = None
