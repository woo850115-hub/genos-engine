"""Tests for database layer — mock-based (no real PostgreSQL required)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.db import Database


@pytest.fixture
def db_config():
    return {
        "host": "localhost",
        "port": 5432,
        "user": "test",
        "password": "test",
        "database": "test_db",
        "min_connections": 1,
        "max_connections": 5,
    }


class TestDatabase:
    def test_init(self, db_config):
        db = Database(db_config)
        assert db._pool is None
        assert db._config == db_config

    def test_pool_not_connected(self, db_config):
        db = Database(db_config)
        with pytest.raises(AssertionError):
            _ = db.pool

    @pytest.mark.asyncio
    async def test_connect(self, db_config):
        db = Database(db_config)
        mock_pool = MagicMock()
        with patch("core.db.asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)):
            await db.connect()
        assert db._pool is mock_pool

    @pytest.mark.asyncio
    async def test_close(self, db_config):
        db = Database(db_config)
        mock_pool = AsyncMock()
        db._pool = mock_pool
        await db.close()
        mock_pool.close.assert_called_once()
        assert db._pool is None

    @pytest.mark.asyncio
    async def test_auto_init_already_exists(self, db_config):
        db = Database(db_config)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=True)  # rooms table exists

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        db._pool = mock_pool

        from pathlib import Path
        await db.auto_init(Path("/tmp"))
        # Should not execute any schema
        mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_player_not_found(self, db_config):
        db = Database(db_config)
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        db._pool = mock_pool

        result = await db.fetch_player("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_player_empty(self, db_config):
        db = Database(db_config)
        mock_conn = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        db._pool = mock_pool

        await db.save_player(1, {})
        # Empty data should not trigger query
        mock_conn.execute.assert_not_called()
