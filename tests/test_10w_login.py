"""Tests for 10woongi login state machine."""

import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _import_login():
    return importlib.import_module("games.10woongi.login")


def _make_session(player_data=None, config=None):
    """Create a mock session for login tests."""
    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.player_data = player_data or {}
    session.config = config or {"world": {"start_room": 1392841419}}
    session.db = MagicMock()
    session.db.fetch_player = AsyncMock(return_value=None)
    session.db.create_player = AsyncMock()
    session.db.save_player = AsyncMock()
    session.state = None
    session.character = None
    session.enter_game = AsyncMock()
    return session


class TestWoongiGetNameState:
    @pytest.fixture
    def login(self):
        return _import_login()

    async def test_prompt(self, login):
        state = login.WoongiGetNameState()
        assert "새로" in state.prompt()

    async def test_empty_name(self, login):
        state = login.WoongiGetNameState()
        session = _make_session()
        result = await state.on_input(session, "")
        assert result is None
        session.send_line.assert_called()

    async def test_saero_keyword(self, login):
        """'새로' should transition to new name state."""
        state = login.WoongiGetNameState()
        session = _make_session()
        result = await state.on_input(session, "새로")
        assert isinstance(result, login.WoongiNewNameState)

    async def test_existing_player(self, login):
        """Existing player name → password state."""
        state = login.WoongiGetNameState()
        session = _make_session()
        session.db.fetch_player = AsyncMock(return_value={
            "id": 1, "name": "테스터", "password_hash": "xxx",
        })
        result = await state.on_input(session, "테스터")
        assert isinstance(result, login.WoongiGetPasswordState)
        assert session.player_data["name"] == "테스터"

    async def test_nonexistent_player(self, login):
        """Non-existent name → stay (not auto-create like tbaMUD)."""
        state = login.WoongiGetNameState()
        session = _make_session()
        session.db.fetch_player = AsyncMock(return_value=None)
        result = await state.on_input(session, "없는이름")
        assert result is None  # Stay, tell user to type "새로"

    async def test_long_name_rejected(self, login):
        state = login.WoongiGetNameState()
        session = _make_session()
        # 16 bytes in UTF-8
        result = await state.on_input(session, "가나다라마바")
        assert result is None


class TestWoongiNewNameState:
    @pytest.fixture
    def login(self):
        return _import_login()

    async def test_valid_name(self, login):
        state = login.WoongiNewNameState()
        session = _make_session()
        session.db.fetch_player = AsyncMock(return_value=None)
        result = await state.on_input(session, "신규유저")
        assert isinstance(result, login.WoongiNewPasswordState)
        assert session.player_data["name"] == "신규유저"

    async def test_duplicate_name(self, login):
        state = login.WoongiNewNameState()
        session = _make_session()
        session.db.fetch_player = AsyncMock(return_value={"id": 1, "name": "중복"})
        result = await state.on_input(session, "중복")
        assert result is None


class TestWoongiPasswordStates:
    @pytest.fixture
    def login(self):
        return _import_login()

    async def test_new_password_short(self, login):
        state = login.WoongiNewPasswordState()
        session = _make_session()
        result = await state.on_input(session, "ab")
        assert result is None

    async def test_new_password_ok(self, login):
        state = login.WoongiNewPasswordState()
        session = _make_session()
        result = await state.on_input(session, "mypassword")
        assert isinstance(result, login.WoongiConfirmPasswordState)
        assert session.player_data["_password"] == "mypassword"

    async def test_confirm_mismatch(self, login):
        state = login.WoongiConfirmPasswordState()
        session = _make_session(player_data={"name": "test", "_password": "abcd"})
        result = await state.on_input(session, "wrong")
        assert isinstance(result, login.WoongiNewPasswordState)

    async def test_confirm_match(self, login):
        state = login.WoongiConfirmPasswordState()
        session = _make_session(player_data={"name": "test", "_password": "abcd"})
        result = await state.on_input(session, "abcd")
        assert isinstance(result, login.WoongiSelectGenderState)
        assert "password_hash" in session.player_data


class TestWoongiGetPasswordState:
    @pytest.fixture
    def login(self):
        return _import_login()

    async def test_wrong_password(self, login):
        import bcrypt
        pw_hash = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()
        state = login.WoongiGetPasswordState()
        session = _make_session(player_data={
            "id": 1, "name": "테스터", "password_hash": pw_hash,
        })
        result = await state.on_input(session, "wrong")
        assert isinstance(result, login.WoongiGetNameState)

    async def test_correct_password(self, login):
        import bcrypt
        pw_hash = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()
        state = login.WoongiGetPasswordState()
        session = _make_session(player_data={
            "id": 1, "name": "테스터", "password_hash": pw_hash,
        })
        session.state = MagicMock()
        result = await state.on_input(session, "correct")
        session.enter_game.assert_called_once()


class TestWoongiSelectGenderState:
    @pytest.fixture
    def login(self):
        return _import_login()

    async def test_male(self, login):
        state = login.WoongiSelectGenderState()
        session = _make_session(player_data={"name": "test"})
        result = await state.on_input(session, "1")
        assert isinstance(result, login.WoongiSelectClassState)
        assert session.player_data["sex"] == 1

    async def test_female(self, login):
        state = login.WoongiSelectGenderState()
        session = _make_session(player_data={"name": "test"})
        result = await state.on_input(session, "2")
        assert isinstance(result, login.WoongiSelectClassState)
        assert session.player_data["sex"] == 2

    async def test_invalid(self, login):
        state = login.WoongiSelectGenderState()
        session = _make_session(player_data={"name": "test"})
        result = await state.on_input(session, "3")
        assert result is None


class TestWoongiSelectClassState:
    @pytest.fixture
    def login(self):
        return _import_login()

    async def test_class_1_creates_character(self, login):
        state = login.WoongiSelectClassState()
        session = _make_session(player_data={
            "name": "무림인",
            "password_hash": "hash",
            "sex": 1,
        })
        session.db.create_player = AsyncMock(return_value={
            "id": 42, "name": "무림인", "password_hash": "hash",
            "class_id": 1, "sex": 1, "level": 1,
            "hp": 20, "max_hp": 20, "mana": 100,
            "room_vnum": 1392841419,
            "gold": 0, "experience": 0,
        })
        session.state = MagicMock()
        result = await state.on_input(session, "1")

        # Should have called create_player
        session.db.create_player.assert_called_once()

        # Should have entered game
        session.enter_game.assert_called_once()

        # Extensions should have stats
        ext = session.player_data.get("extensions", {})
        assert "stats" in ext
        assert "sp" in ext
        assert ext.get("faction") is None

    async def test_invalid_class(self, login):
        state = login.WoongiSelectClassState()
        session = _make_session(player_data={"name": "test"})
        result = await state.on_input(session, "2")
        assert result is None


class TestSessionPluginHooks:
    """Test that core/session.py respects plugin hooks."""

    async def test_plugin_initial_state(self):
        from core.session import Session

        # Mock a plugin with get_initial_state
        class MockPlugin:
            name = "test"

            def get_initial_state(self):
                return MagicMock(prompt=MagicMock(return_value="custom> "))

            def welcome_banner(self):
                return "CUSTOM BANNER"

        engine = MagicMock()
        engine._plugin = MockPlugin()
        engine.config = {"world": {"start_room": 1}}
        engine.db = MagicMock()

        conn = MagicMock()
        conn.send = AsyncMock()
        conn.send_line = AsyncMock()
        conn.closed = True  # Close immediately
        conn.get_input = AsyncMock(side_effect=asyncio.TimeoutError)

        session = Session(conn, engine)
        # The _welcome_banner should use plugin
        banner = session._welcome_banner()
        assert "CUSTOM BANNER" in banner

    async def test_default_banner_without_plugin(self):
        from core.session import Session

        engine = MagicMock()
        engine._plugin = None
        engine.config = {}
        engine.db = MagicMock()

        conn = MagicMock()
        session = Session(conn, engine)
        banner = session._welcome_banner()
        assert "tbaMUD-KR" in banner

    async def test_default_banner_without_welcome_method(self):
        from core.session import Session

        class MinimalPlugin:
            name = "minimal"

        engine = MagicMock()
        engine._plugin = MinimalPlugin()
        engine.config = {}
        engine.db = MagicMock()

        conn = MagicMock()
        session = Session(conn, engine)
        banner = session._welcome_banner()
        assert "tbaMUD-KR" in banner  # Falls back to default
