"""3eyes constants — 8 classes, 8 races, proficiency, realm, stat cycling."""

from __future__ import annotations

# ── Classes (8) ─────────────────────────────────────────────────
CLASS_NAMES = {
    1: "암살자", 2: "야만인", 3: "성직자", 4: "전사",
    5: "마법사", 6: "팔라딘", 7: "광전사", 8: "도적",
}

CLASS_ABBREV = {
    1: "As", 2: "Ba", 3: "Cl", 4: "Fi",
    5: "Ma", 6: "Pa", 7: "Ra", 8: "Th",
}

# From global.c class_stats[13]: hp_start, mp_start, hp_per_level, mp_per_level
CLASS_STATS: dict[int, dict[str, int]] = {
    1: {"hp_start": 55, "mp_start": 50, "hp_lv": 6, "mp_lv": 2},
    2: {"hp_start": 60, "mp_start": 40, "hp_lv": 7, "mp_lv": 1},
    3: {"hp_start": 50, "mp_start": 55, "hp_lv": 5, "mp_lv": 3},
    4: {"hp_start": 65, "mp_start": 35, "hp_lv": 8, "mp_lv": 1},
    5: {"hp_start": 45, "mp_start": 60, "hp_lv": 4, "mp_lv": 4},
    6: {"hp_start": 60, "mp_start": 45, "hp_lv": 7, "mp_lv": 2},
    7: {"hp_start": 70, "mp_start": 30, "hp_lv": 9, "mp_lv": 1},
    8: {"hp_start": 50, "mp_start": 45, "hp_lv": 5, "mp_lv": 2},
}

# Caster classes (get mana regen bonus)
CASTER_CLASSES = {3, 5}  # Cleric, Mage

# ── Races (8) ───────────────────────────────────────────────────
RACE_NAMES = {
    1: "드워프", 2: "엘프", 3: "하프엘프", 4: "호빗",
    5: "인간", 6: "오크", 7: "반거인", 8: "노움",
}

# From source code create_ply() / create_killer() race adjustments
RACE_STAT_MODS: dict[int, dict[str, int]] = {
    1: {"str": 1, "pie": -1},               # Dwarf
    2: {"int": 2, "con": -1, "str": -1},    # Elf
    3: {"int": 1, "con": -1},               # Half-Elf
    4: {"dex": 1, "str": -1},               # Hobbit
    5: {"con": 1},                           # Human
    6: {"str": 1, "con": 1, "dex": -1, "int": -1},  # Orc
    7: {"str": 2, "int": -1, "pie": -1},    # Half-Giant
    8: {"pie": 1, "str": -1},               # Gnome
}

# All races can be all classes (no restrictions in 3eyes source)
RACE_ALLOWED_CLASSES: dict[int, list[int]] = {
    i: list(range(1, 9)) for i in range(1, 9)
}

# ── Proficiency (5 weapon types) ────────────────────────────────
PROF_SHARP = 0
PROF_THRUST = 1
PROF_BLUNT = 2
PROF_POLE = 3
PROF_MISSILE = 4
PROF_NAMES = {0: "날붙이", 1: "찌르기", 2: "둔기", 3: "장병기", 4: "원거리"}

# ── Realm (4 magic domains) ─────────────────────────────────────
REALM_EARTH = 0
REALM_WIND = 1
REALM_FIRE = 2
REALM_WATER = 3
REALM_NAMES = {0: "대지", 1: "바람", 2: "화염", 3: "물"}

# ── Rooms ────────────────────────────────────────────────────────
MORTAL_START_ROOM = 1
SPIRIT_ROOM = 11971  # Death respawn room

# ── Level ────────────────────────────────────────────────────────
MAX_MORTAL_LEVEL = 201

# ── Stat cycle: which stat increases at level up (level % 10) ───
# STR/DEX/CON/INT/PIE — from global.c level_cycle[14][10]
LEVEL_CYCLE: dict[int, list[str]] = {
    1: ["con", "pie", "str", "int", "dex", "int", "dex", "pie", "str", "dex"],
    2: ["str", "con", "str", "con", "dex", "str", "con", "str", "con", "dex"],
    3: ["pie", "int", "con", "pie", "int", "con", "pie", "int", "con", "pie"],
    4: ["str", "con", "str", "dex", "str", "con", "str", "dex", "str", "con"],
    5: ["int", "pie", "int", "pie", "int", "pie", "int", "pie", "int", "pie"],
    6: ["str", "pie", "con", "str", "dex", "pie", "con", "str", "dex", "pie"],
    7: ["str", "str", "con", "str", "str", "con", "str", "str", "con", "str"],
    8: ["dex", "int", "dex", "str", "dex", "int", "dex", "str", "dex", "int"],
}

# ── Stat bonus table — from global.c bonus[35] ──────────────────
STAT_BONUS: dict[int, int] = {
    0: -4, 1: -4, 2: -4, 3: -3, 4: -3, 5: -2, 6: -2, 7: -1, 8: -1, 9: -1,
    10: 0, 11: 0, 12: 0, 13: 0, 14: 1, 15: 1, 16: 1, 17: 2, 18: 2, 19: 2,
    20: 3, 21: 3, 22: 3, 23: 3, 24: 4, 25: 4, 26: 4, 27: 4, 28: 4,
    29: 5, 30: 5, 31: 5, 32: 5, 33: 5, 34: 5,
}


def get_stat_bonus(stat_value: int) -> int:
    """Get bonus from stat value (0-63 range, capped at table)."""
    return STAT_BONUS.get(min(max(stat_value, 0), 34), 7)
