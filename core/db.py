"""Database layer — asyncpg connection pool, auto-init, CRUD."""

from __future__ import annotations

import json
import logging
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
        dsn = (
            f"postgresql://{self._config['user']}:{self._config['password']}"
            f"@{self._config['host']}:{self._config['port']}"
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
        """Auto-initialize DB if rooms table doesn't exist."""
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS("
                "SELECT FROM information_schema.tables "
                "WHERE table_name='rooms'"
                ")"
            )
            if exists:
                log.info("Database already initialized")
                return

            log.info("Initializing database from schema + seed data...")
            schema_path = data_dir / "sql" / "schema.sql"
            seed_path = data_dir / "sql" / "seed_data.sql"

            schema_sql = schema_path.read_text(encoding="utf-8")
            await conn.execute(schema_sql)
            log.info("Schema applied")

            seed_sql = seed_path.read_text(encoding="utf-8")
            await conn.execute(seed_sql)
            log.info("Seed data loaded")

    async def ensure_players_table(self) -> None:
        """Create players table if not exists (not in migration output)."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id              SERIAL PRIMARY KEY,
                    name            TEXT UNIQUE NOT NULL,
                    password_hash   TEXT NOT NULL,
                    class_id        INTEGER NOT NULL DEFAULT 0,
                    race_id         INTEGER NOT NULL DEFAULT 0,
                    sex             INTEGER NOT NULL DEFAULT 0,
                    level           INTEGER NOT NULL DEFAULT 1,
                    hp              INTEGER NOT NULL DEFAULT 20,
                    max_hp          INTEGER NOT NULL DEFAULT 20,
                    mana            INTEGER NOT NULL DEFAULT 100,
                    max_mana        INTEGER NOT NULL DEFAULT 100,
                    move_points     INTEGER NOT NULL DEFAULT 82,
                    max_move        INTEGER NOT NULL DEFAULT 82,
                    room_vnum       INTEGER NOT NULL DEFAULT 3001,
                    gold            INTEGER NOT NULL DEFAULT 0,
                    experience      BIGINT NOT NULL DEFAULT 0,
                    strength        INTEGER NOT NULL DEFAULT 13,
                    dexterity       INTEGER NOT NULL DEFAULT 13,
                    constitution    INTEGER NOT NULL DEFAULT 13,
                    intelligence    INTEGER NOT NULL DEFAULT 13,
                    wisdom          INTEGER NOT NULL DEFAULT 13,
                    charisma        INTEGER NOT NULL DEFAULT 13,
                    hitroll         INTEGER NOT NULL DEFAULT 0,
                    damroll         INTEGER NOT NULL DEFAULT 0,
                    armor_class     INTEGER NOT NULL DEFAULT 100,
                    alignment       INTEGER NOT NULL DEFAULT 0,
                    practices       INTEGER NOT NULL DEFAULT 0,
                    equipment       JSONB NOT NULL DEFAULT '{}',
                    inventory       JSONB NOT NULL DEFAULT '[]',
                    affects         JSONB NOT NULL DEFAULT '[]',
                    skills          JSONB NOT NULL DEFAULT '{}',
                    quest_progress  JSONB NOT NULL DEFAULT '{}',
                    aliases         JSONB NOT NULL DEFAULT '{}',
                    title           TEXT NOT NULL DEFAULT '',
                    description     TEXT NOT NULL DEFAULT '',
                    flags           JSONB NOT NULL DEFAULT '[]',
                    extensions      JSONB NOT NULL DEFAULT '{}',
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_login      TIMESTAMPTZ
                )
            """)
            log.info("Players table ensured")

    # ── Query helpers ───────────────────────────────────────────────

    async def fetch_all(self, table: str) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(f"SELECT * FROM {table}")  # noqa: S608

    async def fetch_one(self, table: str, key_col: str, key_val: Any) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                f"SELECT * FROM {table} WHERE {key_col} = $1", key_val  # noqa: S608
            )

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
