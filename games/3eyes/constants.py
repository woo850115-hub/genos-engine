"""3eyes constants — classes, races, spells, flags, cooldowns, proficiency, realm.

From original source: mstruct.h, global.c, player.c, kyk3.c
"""

from __future__ import annotations

# ── Class IDs (from mstruct.h) ────────────────────────────────
ASSASSIN = 1
BARBARIAN = 2
CLERIC = 3
FIGHTER = 4
MAGE = 5
PALADIN = 6
RANGER = 7
THIEF = 8
# Advanced classes (train / 전직)
INVINCIBLE = 9
CARETAKER = 10
CARE_II = 11
CARE_III = 12
ZONEMAKER = 13
REALZONEMAKER = 14
SUB_DM = 15
DM = 16
ME = 17

CLASS_NAMES = {
    1: "암살자", 2: "야만인", 3: "성직자", 4: "전사",
    5: "마법사", 6: "팔라딘", 7: "광전사", 8: "도적",
    9: "무적자", 10: "보살핌자", 11: "보살핌II", 12: "보살핌III",
    13: "존메이커", 14: "리얼존메이커", 15: "부관리자", 16: "관리자", 17: "최고관리자",
}

# Character creation classes (4) — original create_ply() order
CREATE_CLASSES = [
    (8, "도  둑"),      # THIEF
    (2, "권법가"),      # BARBARIAN
    (5, "마법사"),      # MAGE
    (4, "검  사"),      # FIGHTER
]

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

# Character creation races (4) — original create_ply() order with custom names
CREATE_RACES = [
    (1, "요정족"),      # DWARF
    (2, "드래곤족"),    # ELF
    (5, "인간족"),      # HUMAN
    (6, "마족"),        # ORC
]

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

# Initial items given to new characters (original create_ply case 100)
INITIAL_ITEMS = [1140, 1141, 1143, 1144]
INITIAL_GOLD = 5000

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


# ── Creature Flags (from mstruct.h, F_ISSET bits 0-63) ────────
# Player flags (P prefix)
PBLESS = 0      # Blessed (THAC0-3)
PHIDDN = 1      # Hidden
PINVIS = 2      # Invisible
PNOSUM = 4      # No-summon
PBLIND = 5      # Blinded
PCHARM = 6      # Charmed
PFEARS = 7      # Feared (+2 THAC0)
PHASTE = 9      # Haste (attack interval 1)
PCHAOS = 10     # Chaos (PK enabled)
PPOISN = 12     # Poisoned
PDISEA = 13     # Diseased
PANSIC = 14     # ANSI color enabled
PBRIGH = 15     # Bright color
PDINVI = 18     # Detect invisible
PDMAGC = 19     # Detect magic
PKNOWA = 20     # Know alignment
PSALIG = 21     # Sense alignment
PFLY = 22       # Flying
PLEVIT = 23     # Levitating
PWATER = 24     # Water breathing
PSHIEL = 25     # Earth shield
PRFIRE = 26     # Resist fire
PRCOLD = 27     # Resist cold
PRMAGI = 28     # Resist magic
PMARRI = 29     # Married
PFAMIL = 30     # Family member
PNOHPGRAPH = 33  # No HP graph
PDMINV = 34     # DM invisible
PDIRTY = 35     # Dirty (hidden from who)
PUPDMG = 36     # Power upgrade (extra attacks)
PSILNC = 37     # Silenced
PNOMSG = 40     # No messages
PLIGHT = 42     # Light spell
PTRACK = 43     # Tracking

# Monster flags (M prefix)
MAGGRE = 0      # Aggressive (auto-attack)
MFLEER = 1      # Flee when HP < 20%
MUNKIL = 2      # Unkillable
MMGONL = 3      # Magic only (물리 공격 면역)
MENONL = 4      # Enchant only
MMALES = 7      # Male
MMAGIC = 15     # Casts spells in combat

# ── Room Flags (from mstruct.h, R prefix) ─────────────────────
RDARKR = 0      # Dark (always)
RDARKN = 1      # Dark (at night)
RNOKIL = 2      # No kill
RNOMAG = 3      # No magic
RNOTEL = 4      # No teleport
RHEALR = 5      # Healing room
RBANK = 6       # Bank
RSHOP = 7       # Shop
RTRAIN = 8      # Training room (전직)
RREPAI = 9      # Repair shop
RFORGE = 10     # Forge
RPOKER = 11     # Poker room
REARTH = 12     # Earth realm bonus
RWINDR = 13     # Wind realm bonus
RFIRER = 14     # Fire realm bonus
RWATER = 15     # Water realm bonus
RNOLOG = 16     # No log
RSUVIV = 17     # Survival (PK area)
RELECT = 18     # Election room
RPHARM = 19     # Harmful (HP damage)
RPPOIS = 20     # Poison room
RPMPDR = 21     # MP drain room
RNOMAP = 22     # No map
REVENT = 23     # Event room
RFAMIL = 24     # Family hall
RONFML = 25     # Only family members
RONMAR = 26     # Marriage room (start)
RMARRI = 27     # Marriage room (ceremony)
RKILLR = 28     # Killer jail

# ── Object Flags (from mstruct.h, O prefix) ───────────────────
OINVIS = 0      # Invisible
ONODRP = 1      # No drop
OCURSE = 2      # Cursed (no remove, no weapon drop)
OWTLES = 3      # Weightless
OTEMPP = 4      # Temp permanent
OCLIMB = 5      # Climbing gear
OLIGHT = 6      # Light source
OPOISN = 10     # Poisoned
ONSHAT = 41     # Never shatters
OALCRT = 42     # Always critical
OSHADO = 50     # Shadow attack object

# ── Lasttime Cooldown Slots (from mstruct.h) ──────────────────
LT_ATTCK = 0    # Attack
LT_SPELL = 1    # Spellcast
LT_HEALS = 2    # Healing
LT_STEAL = 3    # Steal
LT_PICKL = 4    # Pick lock
LT_SEARC = 5    # Search
LT_TRACK = 6    # Track
LT_PLYER = 7    # Player interaction
LT_HIDE = 8     # Hide
LT_TURNS = 9    # Turn undead
LT_RENEW = 10   # Renew
LT_LIGHT = 11   # Light spell
LT_INVIS = 12   # Invisibility
LT_VIGOR = 13   # Vigor
LT_DETCT = 14   # Detect
LT_BLESS = 15   # Bless
LT_PROTE = 16   # Protection
LT_MEDITATE = 17  # Meditate
LT_POWER = 18   # Power
LT_ACCUR = 19   # Accurate
LT_SNEAK = 20   # Sneak
LT_TRAIN = 30   # Train
LT_FORGE = 31   # Forge
LT_POKER = 32   # Poker
LT_TOTAL = 45   # Total slots

# ── Position (from mstruct.h) ─────────────────────────────────
POS_DEAD = 0
POS_MORTALLYW = 1
POS_INCAP = 2
POS_STUNNED = 3
POS_SLEEPING = 4
POS_RESTING = 5
POS_SITTING = 6
POS_FIGHTING = 7
POS_STANDING = 8

# ── Spell IDs (62 spells from ospell[] / spllist[]) ────────────
# Name: (id, korean_name, mp_cost, realm, is_offensive)
SPELL_LIST: dict[int, dict] = {
    0:  {"name": "vigor",         "kr": "활력",       "mp": 3},
    1:  {"name": "hurt",          "kr": "상처",       "mp": 3},
    2:  {"name": "light",         "kr": "빛",         "mp": 2},
    3:  {"name": "curepoison",    "kr": "해독",       "mp": 5},
    4:  {"name": "bless",         "kr": "축복",       "mp": 5},
    5:  {"name": "protection",    "kr": "보호",       "mp": 5},
    6:  {"name": "fireball",      "kr": "화염구",     "mp": 8},
    7:  {"name": "invisibility",  "kr": "투명",       "mp": 8},
    8:  {"name": "heal",          "kr": "회복",       "mp": 15},
    9:  {"name": "detect_invis",  "kr": "투명감지",   "mp": 5},
    10: {"name": "detect_magic",  "kr": "마법감지",   "mp": 3},
    11: {"name": "teleport",      "kr": "텔레포트",   "mp": 10},
    13: {"name": "lightning",     "kr": "번개",       "mp": 12},
    14: {"name": "ice_blast",     "kr": "얼음폭발",   "mp": 15},
    15: {"name": "enchant",       "kr": "마법부여",   "mp": 20},
    16: {"name": "recall",        "kr": "귀환",       "mp": 5},
    17: {"name": "summon",        "kr": "소환",       "mp": 15},
    18: {"name": "cure_light",    "kr": "치료",       "mp": 10},
    19: {"name": "cure_critical", "kr": "대치료",     "mp": 30},
    20: {"name": "track",         "kr": "추적",       "mp": 8},
    21: {"name": "levitate",      "kr": "공중부양",   "mp": 8},
    22: {"name": "resist_fire",   "kr": "화염저항",   "mp": 10},
    23: {"name": "fly",           "kr": "비행",       "mp": 12},
    24: {"name": "resist_magic",  "kr": "마법저항",   "mp": 15},
    25: {"name": "shock",         "kr": "충격",       "mp": 5},
    26: {"name": "rumble",        "kr": "지진파",     "mp": 7},
    27: {"name": "burn",          "kr": "화상",       "mp": 6},
    28: {"name": "blister",       "kr": "수포",       "mp": 10},
    29: {"name": "dust_gust",     "kr": "먼지돌풍",   "mp": 8},
    30: {"name": "water_bolt",    "kr": "물화살",     "mp": 6},
    31: {"name": "crush",         "kr": "분쇄",       "mp": 12},
    32: {"name": "engulf",        "kr": "삼킴",       "mp": 15},
    33: {"name": "burst",         "kr": "폭발",       "mp": 18},
    34: {"name": "steam",         "kr": "증기",       "mp": 16},
    35: {"name": "shatter",       "kr": "파쇄",       "mp": 20},
    36: {"name": "immolate",      "kr": "소각",       "mp": 25},
    37: {"name": "blood_boil",    "kr": "혈액비등",   "mp": 30},
    38: {"name": "thunder",       "kr": "천둥",       "mp": 28},
    39: {"name": "earthquake",    "kr": "지진",       "mp": 35},
    40: {"name": "flood_fill",    "kr": "대홍수",     "mp": 35},
    41: {"name": "know_alignment","kr": "성향감지",   "mp": 3},
    42: {"name": "remove_curse",  "kr": "저주해제",   "mp": 10},
    43: {"name": "resist_cold",   "kr": "냉기저항",   "mp": 10},
    44: {"name": "breathe_water", "kr": "수중호흡",   "mp": 8},
    45: {"name": "earth_shield",  "kr": "돌방패",     "mp": 12},
    46: {"name": "locate_player", "kr": "위치감지",   "mp": 5},
    47: {"name": "drain_exp",     "kr": "경험흡수",   "mp": 20},
    48: {"name": "rm_disease",    "kr": "질병치료",   "mp": 8},
    49: {"name": "rm_blind",      "kr": "실명치료",   "mp": 8},
    50: {"name": "fear",          "kr": "공포",       "mp": 12},
    51: {"name": "room_vigor",    "kr": "방활력",     "mp": 15},
    52: {"name": "transport",     "kr": "전송",       "mp": 20},
    53: {"name": "blind",         "kr": "실명",       "mp": 10},
    54: {"name": "silence",       "kr": "침묵",       "mp": 12},
    55: {"name": "charm",         "kr": "매혹",       "mp": 15},
    56: {"name": "dragon_slave",  "kr": "드래곤슬레이브", "mp": 60},
    57: {"name": "giga_slave",    "kr": "기가슬레이브", "mp": 100},
    58: {"name": "plasma",        "kr": "플라즈마",   "mp": 50},
    59: {"name": "megiddo",       "kr": "메기도",     "mp": 55},
    60: {"name": "hellfire",      "kr": "지옥불",     "mp": 45},
    61: {"name": "aqua_ray",      "kr": "아쿠아레이", "mp": 45},
    62: {"name": "upgrade",       "kr": "강화",       "mp": 25},
}

# ── spell_fail() base chance per class (from magic8.c) ─────────
# Formula: success = (comp_chance + INT_bonus) * multiplier + base_chance
SPELL_FAIL_PARAMS: dict[int, tuple[int, int]] = {
    # class_id: (multiplier, base_chance)
    ASSASSIN:  (5, 30),
    BARBARIAN: (5, 0),
    CLERIC:    (5, 65),
    FIGHTER:   (5, 10),
    MAGE:      (5, 75),
    PALADIN:   (5, 50),
    RANGER:    (4, 56),
    THIEF:     (6, 22),
}

# ── mod_profic() class divisors (from player.c) ───────────────
MOD_PROFIC_DIVISOR: dict[int, int] = {
    FIGHTER: 20, BARBARIAN: 20,
    INVINCIBLE: 20, CARETAKER: 20, CARE_II: 20, CARE_III: 20,
    RANGER: 25, PALADIN: 25,
    THIEF: 30, ASSASSIN: 30, CLERIC: 30,
    # Default (Mage and others): 40
}

# ── Proficiency experience tables (from player.c profic()) ─────
# Each entry is prof_array[0..11] for the class group
PROF_TABLE_FIGHTER = [
    0, 768, 1024, 1440, 1910, 16000, 31214, 167000, 268488, 695000, 934808, 500000000,
]
PROF_TABLE_BARBARIAN = [
    0, 1536, 2048, 2880, 3820, 32000, 62428, 334000, 536976, 1390000, 1869616, 500000000,
]
PROF_TABLE_THIEF_RANGER = [
    0, 2304, 3072, 4320, 5730, 48000, 93642, 501000, 805464, 2085000, 2804424, 500000000,
]
PROF_TABLE_CLERIC_PALADIN_ASSASSIN = [
    0, 3072, 4096, 5076, 7640, 64000, 124856, 668000, 1073952, 2780000, 3939232, 500000000,
]
PROF_TABLE_MAGE = [
    0, 5376, 7168, 10080, 13370, 112000, 218498, 1169000, 1879416, 4865000, 6543656, 500000000,
]

def get_prof_table(class_id: int) -> list[int]:
    """Get proficiency exp→percent table for a class."""
    if class_id in (FIGHTER, INVINCIBLE, CARETAKER, CARE_II, CARE_III,
                    ZONEMAKER, REALZONEMAKER, SUB_DM, DM, ME):
        return PROF_TABLE_FIGHTER
    if class_id == BARBARIAN:
        return PROF_TABLE_BARBARIAN
    if class_id in (THIEF, RANGER):
        return PROF_TABLE_THIEF_RANGER
    if class_id in (CLERIC, PALADIN, ASSASSIN):
        return PROF_TABLE_CLERIC_PALADIN_ASSASSIN
    return PROF_TABLE_MAGE

# ── Realm proficiency tables (from player.c mprofic()) ─────────
REALM_TABLE_MAGE = [
    0, 1024, 2048, 4096, 8192, 16384, 35768, 85536, 140000, 459410, 2073306, 500000000,
]
REALM_TABLE_CLERIC = [
    0, 1024, 4092, 8192, 16384, 32768, 70536, 119000, 226410, 709410, 2973307, 500000000,
]
REALM_TABLE_PALADIN_RANGER = [
    0, 1024, 8192, 16384, 32768, 65536, 105000, 165410, 287306, 809410, 3538232, 500000000,
]
REALM_TABLE_DEFAULT = [
    0, 1024, 40000, 80000, 120000, 160000, 205000, 222000, 380000, 965410, 5495000, 500000000,
]

def get_realm_table(class_id: int) -> list[int]:
    """Get realm exp→percent table for a class."""
    if class_id in (MAGE, INVINCIBLE, CARETAKER, CARE_II, CARE_III,
                    REALZONEMAKER, ZONEMAKER, SUB_DM, DM, ME):
        return REALM_TABLE_MAGE
    if class_id == CLERIC:
        return REALM_TABLE_CLERIC
    if class_id in (PALADIN, RANGER):
        return REALM_TABLE_PALADIN_RANGER
    return REALM_TABLE_DEFAULT

MAX_PROF = 500000000

# ── comp_chance() — from kyk3.c ───────────────────────────────
def comp_chance(level: int, class_id: int) -> int:
    """Compute chance value (level-based, class-adjusted).
    Original: kyk3.c:757-769
    """
    lev = level
    if class_id >= INVINCIBLE:
        lev += 150
    if class_id >= CARETAKER:
        lev += 150
    return min(80, lev // 6)

# ── Proficiency/Realm percentage from raw exp ──────────────────
def raw_to_percent(raw: int, table: list[int]) -> int:
    """Convert raw proficiency/realm exp to 0-100 percent.
    Original: player.c profic()/mprofic() algorithm.
    """
    raw = max(0, min(raw, MAX_PROF))
    prof = 0
    i = 0
    for i in range(11):
        if raw < table[i + 1]:
            prof = 10 * i
            break
    else:
        return 100
    denom = table[i + 1] - table[i]
    if denom > 0:
        prof += ((raw - table[i]) * 10) // denom
    return min(100, prof)
