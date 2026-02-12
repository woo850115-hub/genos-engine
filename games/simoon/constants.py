"""Simoon constants — 7 classes, 5 races, death penalty, wear slots."""

from __future__ import annotations

# ── Classes (7) ─────────────────────────────────────────────────
CLASS_NAMES = {
    0: "마법사",
    1: "성직자",
    2: "도적",
    3: "전사",
    4: "흑마법사",
    5: "버서커",
    6: "소환사",
}

CLASS_ABBREV = {
    0: "Mu", 1: "Cl", 2: "Th", 3: "Wa", 4: "Dk", 5: "Be", 6: "Su",
}

# hp_gain, mana_gain per level
CLASS_GAINS: dict[int, dict[str, tuple[int, int]]] = {
    0: {"hp": (3, 8),   "mana": (5, 10), "move": (0, 0)},   # Magic User
    1: {"hp": (5, 10),  "mana": (3, 8),  "move": (0, 0)},   # Cleric
    2: {"hp": (6, 11),  "mana": (0, 0),  "move": (0, 0)},   # Thief
    3: {"hp": (10, 15), "mana": (0, 0),  "move": (0, 0)},   # Warrior
    4: {"hp": (3, 8),   "mana": (5, 10), "move": (0, 0)},   # Dark Mage
    5: {"hp": (12, 18), "mana": (0, 0),  "move": (0, 0)},   # Berserker
    6: {"hp": (4, 9),   "mana": (4, 9),  "move": (0, 0)},   # Summoner
}

# Initial HP/mana for new characters
CLASS_INITIAL_HP = {0: 12, 1: 14, 2: 14, 3: 18, 4: 12, 5: 20, 6: 13}
CLASS_INITIAL_MANA = {0: 100, 1: 80, 2: 50, 3: 30, 4: 100, 5: 20, 6: 90}

# Caster classes (get mana-based combat bonus)
CASTER_CLASSES = {0, 1, 4, 6}

# ── Races (5) ───────────────────────────────────────────────────
RACE_NAMES = {
    0: "인간",
    1: "드워프",
    2: "엘프",
    3: "호빗",
    4: "하프엘프",
}

RACE_STAT_MODS: dict[int, dict[str, int]] = {
    0: {"cha": 3},
    1: {"con": 1, "dex": -1, "str": 2},
    2: {"cha": 3, "dex": 2, "int": 2, "str": -1},
    3: {"dex": 1, "str": -1},
    4: {},
}

RACE_ALLOWED_CLASSES: dict[int, list[int]] = {
    0: [0, 1, 2, 3, 4, 5, 6],  # Human — all
    1: [1, 2, 3, 5],            # Dwarf
    2: [0, 1, 2, 4, 6],         # Elf
    3: [1, 2, 3],               # Hobbit
    4: [0, 1, 2, 3, 4, 5, 6],  # Half-Elf — all
}

# ── Death penalty (PvM, level 50+) ─────────────────────────────
DEATH_PENALTY_MIN_LEVEL = 50
DEATH_PENALTY_MIN_STAT = 200  # Don't reduce below this
DEATH_STAT_LOSS_MIN = 10
DEATH_STAT_LOSS_MAX = 30
DEATH_GOLD_LOSS_MIN = 30000
DEATH_GOLD_LOSS_MAX = 90000
DEATH_CRYSTAL_LOSS_MIN = 30
DEATH_CRYSTAL_LOSS_MAX = 90

# ── Rooms ───────────────────────────────────────────────────────
MORTAL_START_ROOM = 3093
IMMORT_START_ROOM = 700
FROZEN_START_ROOM = 1202
DONATION_ROOM = 3063

# ── Level cap ───────────────────────────────────────────────────
MAX_MORTAL_LEVEL = 300
MAX_LEVEL = 313
