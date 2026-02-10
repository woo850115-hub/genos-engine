-- GenOS Database Schema
-- Auto-generated from UIR

BEGIN;

CREATE TABLE IF NOT EXISTS rooms (
    vnum        INTEGER PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    zone_number INTEGER NOT NULL DEFAULT 0,
    sector_type INTEGER NOT NULL DEFAULT 0,
    room_flags  JSONB NOT NULL DEFAULT '[]',
    exits       JSONB NOT NULL DEFAULT '[]',
    extra_descs JSONB NOT NULL DEFAULT '[]',
    trigger_vnums JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS items (
    vnum              INTEGER PRIMARY KEY,
    keywords          TEXT NOT NULL DEFAULT '',
    short_description TEXT NOT NULL DEFAULT '',
    long_description  TEXT NOT NULL DEFAULT '',
    item_type         INTEGER NOT NULL DEFAULT 0,
    extra_flags       JSONB NOT NULL DEFAULT '[]',
    wear_flags        JSONB NOT NULL DEFAULT '[]',
    values            JSONB NOT NULL DEFAULT '[0,0,0,0]',
    weight            INTEGER NOT NULL DEFAULT 0,
    cost              INTEGER NOT NULL DEFAULT 0,
    rent              INTEGER NOT NULL DEFAULT 0,
    affects           JSONB NOT NULL DEFAULT '[]',
    extra_descs       JSONB NOT NULL DEFAULT '[]',
    trigger_vnums     JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS monsters (
    vnum                 INTEGER PRIMARY KEY,
    keywords             TEXT NOT NULL DEFAULT '',
    short_description    TEXT NOT NULL DEFAULT '',
    long_description     TEXT NOT NULL DEFAULT '',
    detailed_description TEXT NOT NULL DEFAULT '',
    level                INTEGER NOT NULL DEFAULT 1,
    hitroll              INTEGER NOT NULL DEFAULT 0,
    armor_class          INTEGER NOT NULL DEFAULT 100,
    hp_dice              TEXT NOT NULL DEFAULT '0d0+0',
    damage_dice          TEXT NOT NULL DEFAULT '0d0+0',
    gold                 INTEGER NOT NULL DEFAULT 0,
    experience           INTEGER NOT NULL DEFAULT 0,
    action_flags         JSONB NOT NULL DEFAULT '[]',
    affect_flags         JSONB NOT NULL DEFAULT '[]',
    alignment            INTEGER NOT NULL DEFAULT 0,
    sex                  INTEGER NOT NULL DEFAULT 0,
    trigger_vnums        JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS classes (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    abbreviation TEXT NOT NULL DEFAULT '',
    hp_gain_min  INTEGER NOT NULL DEFAULT 1,
    hp_gain_max  INTEGER NOT NULL DEFAULT 10,
    extensions   JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS zones (
    vnum           INTEGER PRIMARY KEY,
    name           TEXT NOT NULL DEFAULT '',
    builders       TEXT NOT NULL DEFAULT '',
    lifespan       INTEGER NOT NULL DEFAULT 30,
    bot            INTEGER NOT NULL DEFAULT 0,
    top            INTEGER NOT NULL DEFAULT 0,
    reset_mode     INTEGER NOT NULL DEFAULT 2,
    zone_flags     JSONB NOT NULL DEFAULT '[]',
    reset_commands JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS shops (
    vnum          INTEGER PRIMARY KEY,
    keeper_vnum   INTEGER NOT NULL DEFAULT -1,
    selling_items JSONB NOT NULL DEFAULT '[]',
    profit_buy    REAL NOT NULL DEFAULT 1.0,
    profit_sell   REAL NOT NULL DEFAULT 1.0,
    shop_room     INTEGER NOT NULL DEFAULT -1,
    open1         INTEGER NOT NULL DEFAULT 0,
    close1        INTEGER NOT NULL DEFAULT 0,
    open2         INTEGER NOT NULL DEFAULT 0,
    close2        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS triggers (
    vnum         INTEGER PRIMARY KEY,
    name         TEXT NOT NULL DEFAULT '',
    attach_type  INTEGER NOT NULL DEFAULT 0,
    trigger_type INTEGER NOT NULL DEFAULT 0,
    numeric_arg  INTEGER NOT NULL DEFAULT 0,
    arg_list     TEXT NOT NULL DEFAULT '',
    script       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS quests (
    vnum               INTEGER PRIMARY KEY,
    name               TEXT NOT NULL DEFAULT '',
    keywords           TEXT NOT NULL DEFAULT '',
    description        TEXT NOT NULL DEFAULT '',
    completion_message TEXT NOT NULL DEFAULT '',
    quest_flags        INTEGER NOT NULL DEFAULT 0,
    quest_type         INTEGER NOT NULL DEFAULT 0,
    target_vnum        INTEGER NOT NULL DEFAULT -1,
    mob_vnum           INTEGER NOT NULL DEFAULT -1,
    reward_gold        INTEGER NOT NULL DEFAULT 0,
    reward_exp         INTEGER NOT NULL DEFAULT 0,
    reward_obj         INTEGER NOT NULL DEFAULT -1
);

CREATE TABLE IF NOT EXISTS socials (
    command              TEXT PRIMARY KEY,
    min_victim_position  INTEGER NOT NULL DEFAULT 0,
    flags                INTEGER NOT NULL DEFAULT 0,
    no_arg_to_char       TEXT NOT NULL DEFAULT '',
    no_arg_to_room       TEXT NOT NULL DEFAULT '',
    found_to_char        TEXT NOT NULL DEFAULT '',
    found_to_room        TEXT NOT NULL DEFAULT '',
    found_to_victim      TEXT NOT NULL DEFAULT '',
    not_found            TEXT NOT NULL DEFAULT '',
    self_to_char         TEXT NOT NULL DEFAULT '',
    self_to_room         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS help_entries (
    id       SERIAL PRIMARY KEY,
    keywords JSONB NOT NULL DEFAULT '[]',
    min_level INTEGER NOT NULL DEFAULT 0,
    text     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS commands (
    name         TEXT PRIMARY KEY,
    min_position INTEGER NOT NULL DEFAULT 0,
    min_level    INTEGER NOT NULL DEFAULT 0,
    min_match    TEXT NOT NULL DEFAULT '',
    handler      TEXT NOT NULL DEFAULT '',
    subcmd       INTEGER NOT NULL DEFAULT 0,
    category     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS skills (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL DEFAULT '',
    spell_type   TEXT NOT NULL DEFAULT '',
    max_mana     INTEGER NOT NULL DEFAULT 0,
    min_mana     INTEGER NOT NULL DEFAULT 0,
    mana_change  INTEGER NOT NULL DEFAULT 0,
    min_position INTEGER NOT NULL DEFAULT 0,
    targets      INTEGER NOT NULL DEFAULT 0,
    violent      BOOLEAN NOT NULL DEFAULT FALSE,
    routines     INTEGER NOT NULL DEFAULT 0,
    wearoff_msg  TEXT NOT NULL DEFAULT '',
    class_levels JSONB NOT NULL DEFAULT '{}',
    extensions   JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS races (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL DEFAULT '',
    abbreviation    TEXT NOT NULL DEFAULT '',
    stat_modifiers  JSONB NOT NULL DEFAULT '{}',
    allowed_classes JSONB NOT NULL DEFAULT '[]',
    extensions      JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS game_configs (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    value_type  TEXT NOT NULL DEFAULT 'int',
    category    TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS experience_table (
    class_id     INTEGER NOT NULL DEFAULT 0,
    level        INTEGER NOT NULL,
    exp_required BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (class_id, level)
);

CREATE TABLE IF NOT EXISTS thac0_table (
    class_id INTEGER NOT NULL DEFAULT 0,
    level    INTEGER NOT NULL,
    thac0    INTEGER NOT NULL DEFAULT 20,
    PRIMARY KEY (class_id, level)
);

CREATE TABLE IF NOT EXISTS saving_throws (
    class_id   INTEGER NOT NULL DEFAULT 0,
    save_type  INTEGER NOT NULL DEFAULT 0,
    level      INTEGER NOT NULL,
    save_value INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (class_id, save_type, level)
);

CREATE TABLE IF NOT EXISTS level_titles (
    class_id INTEGER NOT NULL DEFAULT 0,
    level    INTEGER NOT NULL,
    gender   TEXT NOT NULL DEFAULT 'male',
    title    TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (class_id, level, gender)
);

CREATE TABLE IF NOT EXISTS attribute_modifiers (
    stat_name TEXT NOT NULL,
    score     INTEGER NOT NULL,
    modifiers JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (stat_name, score)
);

CREATE TABLE IF NOT EXISTS practice_params (
    class_id         INTEGER PRIMARY KEY,
    learned_level    INTEGER NOT NULL DEFAULT 0,
    max_per_practice INTEGER NOT NULL DEFAULT 0,
    min_per_practice INTEGER NOT NULL DEFAULT 0,
    prac_type        TEXT NOT NULL DEFAULT 'skill',
    extensions       JSONB NOT NULL DEFAULT '{}'
);

COMMIT;
