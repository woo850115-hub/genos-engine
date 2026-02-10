"""Tests for session management — login state machine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from core.session import (
    GetNameState, GetPasswordState, NewPasswordState,
    ConfirmPasswordState, SelectSexState, SelectClassState,
    PlayingState, Session,
)


def _make_session():
    """Create a mock session for testing."""
    conn = MagicMock()
    conn.send = AsyncMock()
    conn.send_line = AsyncMock()
    conn.set_echo = AsyncMock()
    conn.closed = False
    conn.id = 1

    engine = MagicMock()
    engine.db = MagicMock()
    engine.db.fetch_player = AsyncMock(return_value=None)
    engine.db.create_player = AsyncMock(return_value={"id": 1, "name": "테스트", "level": 1})
    engine.db.save_player = AsyncMock()
    engine.world = MagicMock()
    engine.world.get_room = MagicMock(return_value=None)
    engine.world.char_to_room = MagicMock()
    engine.config = {"world": {"start_room": 3001}}
    engine.sessions = {}
    engine.players = {}
    engine.do_look = AsyncMock()

    session = Session(conn, engine)
    return session


class TestGetNameState:
    @pytest.mark.asyncio
    async def test_new_player(self):
        state = GetNameState()
        session = _make_session()
        next_state = await state.on_input(session, "테스트")
        assert isinstance(next_state, NewPasswordState)
        assert session.player_data["name"] == "테스트"

    @pytest.mark.asyncio
    async def test_existing_player(self):
        state = GetNameState()
        session = _make_session()
        session.db.fetch_player = AsyncMock(return_value={
            "id": 1, "name": "기존유저", "password_hash": "xxx", "level": 5
        })
        next_state = await state.on_input(session, "기존유저")
        assert isinstance(next_state, GetPasswordState)

    @pytest.mark.asyncio
    async def test_empty_name(self):
        state = GetNameState()
        session = _make_session()
        next_state = await state.on_input(session, "")
        assert next_state is None  # stays in same state

    @pytest.mark.asyncio
    async def test_name_too_long(self):
        state = GetNameState()
        session = _make_session()
        # 16 bytes in UTF-8 (over 15 byte limit)
        next_state = await state.on_input(session, "가나다라마바")
        assert next_state is None

    def test_prompt(self):
        state = GetNameState()
        assert "이름" in state.prompt()


class TestNewPasswordState:
    @pytest.mark.asyncio
    async def test_password_too_short(self):
        state = NewPasswordState()
        session = _make_session()
        next_state = await state.on_input(session, "ab")
        assert next_state is None

    @pytest.mark.asyncio
    async def test_valid_password(self):
        state = NewPasswordState()
        session = _make_session()
        next_state = await state.on_input(session, "goodpass")
        assert isinstance(next_state, ConfirmPasswordState)
        assert session.player_data["_password"] == "goodpass"


class TestConfirmPasswordState:
    @pytest.mark.asyncio
    async def test_mismatch(self):
        state = ConfirmPasswordState()
        session = _make_session()
        session.player_data["_password"] = "good"
        next_state = await state.on_input(session, "bad")
        assert isinstance(next_state, NewPasswordState)

    @pytest.mark.asyncio
    async def test_match(self):
        state = ConfirmPasswordState()
        session = _make_session()
        session.player_data["_password"] = "goodpass"
        next_state = await state.on_input(session, "goodpass")
        assert isinstance(next_state, SelectSexState)
        assert "password_hash" in session.player_data


class TestSelectSexState:
    @pytest.mark.asyncio
    async def test_valid_selection(self):
        state = SelectSexState()
        session = _make_session()
        next_state = await state.on_input(session, "2")
        assert isinstance(next_state, SelectClassState)
        assert session.player_data["sex"] == 1  # male

    @pytest.mark.asyncio
    async def test_invalid_selection(self):
        state = SelectSexState()
        session = _make_session()
        next_state = await state.on_input(session, "5")
        assert next_state is None


class TestSelectClassState:
    @pytest.mark.asyncio
    async def test_valid_selection(self):
        state = SelectClassState()
        session = _make_session()
        session.player_data = {
            "name": "테스트", "password_hash": "xxx", "sex": 1,
        }
        # Mock create_player to return full player data
        session.db.create_player = AsyncMock(return_value={
            "id": 1, "name": "테스트", "level": 1, "hp": 20, "max_hp": 20,
            "mana": 100, "max_mana": 100, "move_points": 82, "max_move": 82,
            "gold": 0, "experience": 0, "room_vnum": 3001,
            "alignment": 0, "armor_class": 100, "hitroll": 0,
            "class_id": 3, "sex": 1, "password_hash": "xxx",
        })
        next_state = await state.on_input(session, "4")
        # Should enter game → PlayingState
        assert isinstance(session.state, PlayingState)

    @pytest.mark.asyncio
    async def test_invalid_selection(self):
        state = SelectClassState()
        session = _make_session()
        next_state = await state.on_input(session, "9")
        assert next_state is None


class TestPlayingState:
    def test_prompt(self):
        state = PlayingState()
        assert ">" in state.prompt()

    @pytest.mark.asyncio
    async def test_empty_input(self):
        state = PlayingState()
        session = _make_session()
        next_state = await state.on_input(session, "")
        assert next_state is None
