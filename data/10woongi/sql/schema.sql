-- GenOS Unified Database Schema v1.0
-- Auto-generated from UIR

BEGIN;

-- ── Proto Tables (immutable templates, migration tool generates) ──

CREATE TABLE IF NOT EXISTS rooms (
    vnum        INTEGER PRIMARY KEY,
    zone_vnum   INTEGER NOT NULL DEFAULT 0,
    name        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    sector      INTEGER NOT NULL DEFAULT 0,
    flags       TEXT[] NOT NULL DEFAULT '{}',
    extra_descs JSONB NOT NULL DEFAULT '[]',
    scripts     JSONB NOT NULL DEFAULT '[]',
    ext         JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_rooms_zone ON rooms (zone_vnum);
CREATE INDEX IF NOT EXISTS idx_rooms_flags ON rooms USING GIN (flags);

CREATE TABLE IF NOT EXISTS room_exits (
    from_vnum   INTEGER NOT NULL REFERENCES rooms(vnum),
    direction   SMALLINT NOT NULL,
    to_vnum     INTEGER NOT NULL DEFAULT -1,
    description TEXT NOT NULL DEFAULT '',
    keywords    TEXT NOT NULL DEFAULT '',
    key_vnum    INTEGER NOT NULL DEFAULT -1,
    flags       TEXT[] NOT NULL DEFAULT '{}',
    ext         JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (from_vnum, direction)
);
CREATE INDEX IF NOT EXISTS idx_exits_to ON room_exits (to_vnum);

CREATE TABLE IF NOT EXISTS mob_protos (
    vnum        INTEGER PRIMARY KEY,
    zone_vnum   INTEGER NOT NULL DEFAULT 0,
    keywords    TEXT NOT NULL DEFAULT '',
    short_desc  TEXT NOT NULL DEFAULT '',
    long_desc   TEXT NOT NULL DEFAULT '',
    detail_desc TEXT NOT NULL DEFAULT '',
    level       INTEGER NOT NULL DEFAULT 1,
    max_hp      INTEGER NOT NULL DEFAULT 1,
    max_mana    INTEGER NOT NULL DEFAULT 0,
    max_move    INTEGER NOT NULL DEFAULT 0,
    armor_class INTEGER NOT NULL DEFAULT 100,
    hitroll     INTEGER NOT NULL DEFAULT 0,
    damroll     INTEGER NOT NULL DEFAULT 0,
    damage_dice TEXT NOT NULL DEFAULT '1d4+0',
    gold        INTEGER NOT NULL DEFAULT 0,
    experience  BIGINT NOT NULL DEFAULT 0,
    alignment   INTEGER NOT NULL DEFAULT 0,
    sex         SMALLINT NOT NULL DEFAULT 0,
    position    SMALLINT NOT NULL DEFAULT 8,
    class_id    INTEGER NOT NULL DEFAULT 0,
    race_id     INTEGER NOT NULL DEFAULT 0,
    act_flags   TEXT[] NOT NULL DEFAULT '{}',
    aff_flags   TEXT[] NOT NULL DEFAULT '{}',
    stats       JSONB NOT NULL DEFAULT '{}',
    skills      JSONB NOT NULL DEFAULT '{}',
    scripts     JSONB NOT NULL DEFAULT '[]',
    ext         JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_mobs_zone ON mob_protos (zone_vnum);
CREATE INDEX IF NOT EXISTS idx_mobs_level ON mob_protos (level);
CREATE INDEX IF NOT EXISTS idx_mobs_act ON mob_protos USING GIN (act_flags);

CREATE TABLE IF NOT EXISTS item_protos (
    vnum        INTEGER PRIMARY KEY,
    zone_vnum   INTEGER NOT NULL DEFAULT 0,
    keywords    TEXT NOT NULL DEFAULT '',
    short_desc  TEXT NOT NULL DEFAULT '',
    long_desc   TEXT NOT NULL DEFAULT '',
    item_type   TEXT NOT NULL DEFAULT 'other',
    weight      INTEGER NOT NULL DEFAULT 0,
    cost        INTEGER NOT NULL DEFAULT 0,
    min_level   INTEGER NOT NULL DEFAULT 0,
    wear_slots  TEXT[] NOT NULL DEFAULT '{}',
    flags       TEXT[] NOT NULL DEFAULT '{}',
    values      JSONB NOT NULL DEFAULT '{}',
    affects     JSONB NOT NULL DEFAULT '[]',
    extra_descs JSONB NOT NULL DEFAULT '[]',
    scripts     JSONB NOT NULL DEFAULT '[]',
    ext         JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_items_zone ON item_protos (zone_vnum);
CREATE INDEX IF NOT EXISTS idx_items_type ON item_protos (item_type);
CREATE INDEX IF NOT EXISTS idx_items_flags ON item_protos USING GIN (flags);
CREATE INDEX IF NOT EXISTS idx_items_wear ON item_protos USING GIN (wear_slots);

CREATE TABLE IF NOT EXISTS zones (
    vnum        INTEGER PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    builders    TEXT NOT NULL DEFAULT '',
    lifespan    INTEGER NOT NULL DEFAULT 30,
    reset_mode  SMALLINT NOT NULL DEFAULT 2,
    level_range INT4RANGE,
    flags       TEXT[] NOT NULL DEFAULT '{}',
    resets      JSONB NOT NULL DEFAULT '[]',
    ext         JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS skills (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    skill_type  TEXT NOT NULL DEFAULT 'spell',
    mana_cost   INTEGER NOT NULL DEFAULT 0,
    target      TEXT NOT NULL DEFAULT 'ignore',
    violent     BOOLEAN NOT NULL DEFAULT false,
    min_position SMALLINT NOT NULL DEFAULT 0,
    routines    TEXT[] NOT NULL DEFAULT '{}',
    wearoff_msg TEXT NOT NULL DEFAULT '',
    class_levels JSONB NOT NULL DEFAULT '{}',
    ext         JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS classes (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    abbrev      TEXT NOT NULL DEFAULT '',
    hp_gain     INT4RANGE NOT NULL DEFAULT '[1,10)',
    mana_gain   INT4RANGE NOT NULL DEFAULT '[0,0)',
    move_gain   INT4RANGE NOT NULL DEFAULT '[0,0)',
    base_stats  JSONB NOT NULL DEFAULT '{}',
    ext         JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS races (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    abbrev      TEXT NOT NULL DEFAULT '',
    stat_mods   JSONB NOT NULL DEFAULT '{}',
    body_parts  TEXT[] NOT NULL DEFAULT '{}',
    size        TEXT NOT NULL DEFAULT 'medium',
    ext         JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS shops (
    vnum          INTEGER PRIMARY KEY,
    keeper_vnum   INTEGER NOT NULL,
    room_vnum     INTEGER NOT NULL DEFAULT 0,
    buy_types     TEXT[] NOT NULL DEFAULT '{}',
    buy_profit    REAL NOT NULL DEFAULT 1.1,
    sell_profit   REAL NOT NULL DEFAULT 0.9,
    hours         JSONB NOT NULL DEFAULT '{}',
    inventory     JSONB NOT NULL DEFAULT '[]',
    messages      JSONB NOT NULL DEFAULT '{}',
    ext           JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS quests (
    vnum        INTEGER PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    quest_type  TEXT NOT NULL DEFAULT 'kill',
    level_range INT4RANGE,
    giver_vnum  INTEGER NOT NULL DEFAULT 0,
    target      JSONB NOT NULL DEFAULT '{}',
    rewards     JSONB NOT NULL DEFAULT '{}',
    chain       JSONB NOT NULL DEFAULT '{}',
    flags       TEXT[] NOT NULL DEFAULT '{}',
    ext         JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS socials (
    command     TEXT PRIMARY KEY,
    min_victim_position SMALLINT NOT NULL DEFAULT 0,
    messages    JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS help_entries (
    id          SERIAL PRIMARY KEY,
    keywords    TEXT[] NOT NULL DEFAULT '{}',
    category    TEXT NOT NULL DEFAULT 'general',
    min_level   INTEGER NOT NULL DEFAULT 0,
    body        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_help_keywords ON help_entries USING GIN (keywords);

CREATE TABLE IF NOT EXISTS combat_messages (
    id          SERIAL PRIMARY KEY,
    skill_id    INTEGER NOT NULL,
    hit_type    TEXT NOT NULL,
    to_char     TEXT NOT NULL DEFAULT '',
    to_victim   TEXT NOT NULL DEFAULT '',
    to_room     TEXT NOT NULL DEFAULT '',
    ext         JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_cmsg_skill ON combat_messages (skill_id);

CREATE TABLE IF NOT EXISTS text_files (
    name        TEXT PRIMARY KEY,
    category    TEXT NOT NULL DEFAULT 'system',
    content     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS game_tables (
    table_name  TEXT NOT NULL,
    key         JSONB NOT NULL,
    value       JSONB NOT NULL,
    PRIMARY KEY (table_name, key)
);
CREATE INDEX IF NOT EXISTS idx_gtables_name ON game_tables (table_name);

CREATE TABLE IF NOT EXISTS game_configs (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    description TEXT NOT NULL DEFAULT ''
);

-- ── Instance Tables (runtime mutable, engine manages) ──

CREATE TABLE IF NOT EXISTS players (
    id            SERIAL PRIMARY KEY,
    name          TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    class_id      INTEGER NOT NULL DEFAULT 0,
    race_id       INTEGER NOT NULL DEFAULT 0,
    sex           SMALLINT NOT NULL DEFAULT 0,
    level         INTEGER NOT NULL DEFAULT 1,
    experience    BIGINT NOT NULL DEFAULT 0,
    hp            INTEGER NOT NULL DEFAULT 100,
    max_hp        INTEGER NOT NULL DEFAULT 100,
    mana          INTEGER NOT NULL DEFAULT 100,
    max_mana      INTEGER NOT NULL DEFAULT 100,
    move          INTEGER NOT NULL DEFAULT 100,
    max_move      INTEGER NOT NULL DEFAULT 100,
    gold          INTEGER NOT NULL DEFAULT 0,
    bank_gold     INTEGER NOT NULL DEFAULT 0,
    armor_class   INTEGER NOT NULL DEFAULT 100,
    alignment     INTEGER NOT NULL DEFAULT 0,
    stats         JSONB NOT NULL DEFAULT '{}',
    equipment     JSONB NOT NULL DEFAULT '{}',
    inventory     JSONB NOT NULL DEFAULT '[]',
    affects       JSONB NOT NULL DEFAULT '[]',
    skills        JSONB NOT NULL DEFAULT '{}',
    flags         TEXT[] NOT NULL DEFAULT '{}',
    aliases       JSONB NOT NULL DEFAULT '{}',
    title         TEXT NOT NULL DEFAULT '',
    description   TEXT NOT NULL DEFAULT '',
    room_vnum     INTEGER NOT NULL DEFAULT 0,
    org_id        INTEGER NOT NULL DEFAULT 0,
    org_rank      INTEGER NOT NULL DEFAULT 0,
    ext           JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_players_name ON players (name);
CREATE INDEX IF NOT EXISTS idx_players_level ON players (level);

CREATE TABLE IF NOT EXISTS organizations (
    id          SERIAL PRIMARY KEY,
    org_type    TEXT NOT NULL DEFAULT 'clan',
    name        TEXT NOT NULL DEFAULT '',
    leader      TEXT NOT NULL DEFAULT '',
    treasury    INTEGER NOT NULL DEFAULT 0,
    room_vnum   INTEGER NOT NULL DEFAULT 0,
    ext         JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS lua_scripts (
    id          SERIAL PRIMARY KEY,
    game        TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '',
    name        TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT '',
    version     INTEGER NOT NULL DEFAULT 1,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (game, category, name)
);

COMMIT;
