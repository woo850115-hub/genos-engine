"""Database layer — asyncpg connection pool, auto-init, CRUD.

GenOS Unified Schema v1.0: 20 tables in DDL, players/lua_scripts included.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import asyncpg

log = logging.getLogger(__name__)


class Database:
    """Async PostgreSQL database wrapper."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        assert self._pool is not None, "Database not connected"
        return self._pool

    async def connect(self) -> None:
        host = os.environ.get("DB_HOST", self._config["host"])
        dsn = (
            f"postgresql://{self._config['user']}:{self._config['password']}"
            f"@{host}:{self._config['port']}"
            f"/{self._config['database']}"
        )
        self._pool = await asyncpg.create_pool(
            dsn,
            min_size=self._config.get("min_connections", 2),
            max_size=self._config.get("max_connections", 10),
        )
        log.info("Database pool created: %s", self._config["database"])

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            log.info("Database pool closed")

    async def auto_init(self, data_dir: Path) -> None:
        """Auto-initialize DB if rooms table doesn't exist or is empty."""
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS("
                "SELECT FROM information_schema.tables "
                "WHERE table_name='rooms'"
                ")"
            )
            if exists:
                count = await conn.fetchval("SELECT COUNT(*) FROM rooms")
                if count and count > 0:
                    log.info("Database already initialized (%d rooms)", count)
                    return
                # Tables exist but empty (partial init) — drop and recreate
                log.warning("Tables exist but rooms empty, dropping schema...")
                await conn.execute(
                    "DROP SCHEMA public CASCADE; "
                    "CREATE SCHEMA public;"
                )

            log.info("Initializing database from schema + seed data...")
            schema_path = data_dir / "sql" / "schema.sql"
            seed_path = data_dir / "sql" / "seed_data.sql"

            schema_sql = schema_path.read_text(encoding="utf-8")
            await conn.execute(schema_sql)
            log.info("Schema applied")

            seed_sql = seed_path.read_text(encoding="utf-8")
            await conn.execute(seed_sql)
            log.info("Seed data loaded")

    # ── Query helpers ───────────────────────────────────────────────

    async def fetch_all(self, table: str) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(f"SELECT * FROM {table}")  # noqa: S608

    async def fetch_one(self, table: str, key_col: str, key_val: Any) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                f"SELECT * FROM {table} WHERE {key_col} = $1", key_val  # noqa: S608
            )

    # ── Player CRUD ────────────────────────────────────────────────

    async def fetch_player(self, name: str) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM players WHERE LOWER(name) = LOWER($1)", name
            )

    async def create_player(self, *, name: str, password_hash: str, sex: int,
                            class_id: int, start_room: int) -> asyncpg.Record:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "INSERT INTO players (name, password_hash, sex, class_id, room_vnum) "
                "VALUES ($1, $2, $3, $4, $5) RETURNING *",
                name, password_hash, sex, class_id, start_room,
            )

    async def save_player(self, player_id: int, data: dict[str, Any]) -> None:
        """Save player data. Only updates specified columns."""
        if not data:
            return
        cols = []
        vals = []
        for i, (k, v) in enumerate(data.items(), start=2):
            cols.append(f"{k} = ${i}")
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v, ensure_ascii=False))
            else:
                vals.append(v)
        query = f"UPDATE players SET {', '.join(cols)}, last_login = NOW() WHERE id = $1"  # noqa: S608
        async with self.pool.acquire() as conn:
            await conn.execute(query, player_id, *vals)

    async def execute(self, query: str, *args: Any) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    # ── Lua scripts CRUD ─────────────────────────────────────────────

    async def lua_scripts_count(self) -> int:
        """Return total number of lua_scripts rows."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM lua_scripts") or 0

    async def fetch_lua_scripts(self, game: str) -> list[asyncpg.Record]:
        """Fetch all Lua scripts for a game, ordered by category/name."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM lua_scripts WHERE game = $1 "
                "ORDER BY category, name",
                game,
            )

    async def fetch_lua_script(self, game: str, category: str, name: str
                               ) -> asyncpg.Record | None:
        """Fetch a single Lua script by game/category/name."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM lua_scripts "
                "WHERE game = $1 AND category = $2 AND name = $3",
                game, category, name,
            )

    async def upsert_lua_script(self, *, game: str, category: str, name: str,
                                source: str, updated_by: str = "system"
                                ) -> asyncpg.Record:
        """Insert or update a Lua script."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "INSERT INTO lua_scripts (game, category, name, source) "
                "VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (game, category, name) DO UPDATE "
                "SET source = $4, version = lua_scripts.version + 1, "
                "    updated_at = NOW() "
                "RETURNING *",
                game, category, name, source,
            )
