"""10woongi constants — equipment slots, stats, classes, promotion paths."""

from __future__ import annotations

# ── 22 Equipment Slots ─────────────────────────────────────────

WEAR_SLOTS: dict[int, str] = {
    1: "투구",
    2: "귀걸이1",
    3: "목걸이",
    4: "갑옷",
    5: "허리띠",
    6: "팔갑",
    7: "장갑",
    8: "팔찌1",
    9: "반지1",
    10: "각반",
    11: "신발",
    12: "귀걸이2",
    13: "반지2",
    14: "반지3",
    15: "반지4",
    16: "반지5",
    17: "반지6",
    18: "반지7",
    19: "반지8",
    20: "반지9",
    21: "반지10",
    22: "팔찌2",
}

NUM_WEAR_SLOTS = 22

# ── 6 Wuxia Stats ──────────────────────────────────────────────

STAT_NAMES = ["체력", "민첩", "지혜", "기골", "내공", "투지"]
STAT_KEYS = ["stamina", "agility", "wisdom", "bone", "inner", "spirit"]
STAT_DEFAULT = 13

# ── 14 Classes + Promotion Paths ───────────────────────────────

CLASS_NAMES: dict[int, str] = {
    1: "투사",
    2: "전사",
    3: "기사",
    4: "상급기사",
    5: "신관기사",
    6: "사제",
    7: "성직자",
    8: "아바타",
    9: "도둑",
    10: "사냥꾼",
    11: "암살자",
    12: "마술사",
    13: "마법사",
    14: "시공술사",
}

# Starting classes (available at character creation)
STARTING_CLASSES = {1: "투사"}

# Promotion chains: current_class_id → (required_level, next_class_id)
PROMOTION_CHAIN: dict[int, tuple[int, int]] = {
    1: (30, 2),     # 투사 → 전사
    2: (60, 3),     # 전사 → 기사
    3: (100, 4),    # 기사 → 상급기사
    6: (30, 7),     # 사제 → 성직자
    7: (60, 8),     # 성직자 → 아바타
    9: (30, 10),    # 도둑 → 사냥꾼
    10: (60, 11),   # 사냥꾼 → 암살자
    12: (30, 13),   # 마술사 → 마법사
    13: (60, 14),   # 마법사 → 시공술사
}

# Special promotion: 신관기사(5) is hybrid — accessed from 기사(3) at specific conditions
SPECIAL_PROMOTIONS: dict[int, tuple[int, int]] = {
    3: (80, 5),     # 기사 → 신관기사 (alternative path)
}

# Class families for grouping
CLASS_FAMILIES = {
    "전사 계열": [1, 2, 3, 4, 5],
    "사제 계열": [6, 7, 8],
    "도둑 계열": [9, 10, 11],
    "마법 계열": [12, 13, 14],
}

# ── Key Room VNUMs ──────────────────────────────────────────────

START_ROOM = 1392841419       # 장백성 마을 광장
VOID_ROOM = 1854941986        # 대기실
FREEZER_ROOM = 1958428208     # 냉동실

# ── Combat ──────────────────────────────────────────────────────

COMBAT_ROUND_TICKS = 10  # 1 second at 10Hz

CRITICAL_TYPES = {
    1: "HIT_SELF",
    2: "HIT_GROUP",
    3: "DROP_WEAPON",
    4: "BREAK_WEAPON",
    5: "BREAK_ARMOR",
    6: "STUN",
    7: "DAMAGE_X",
    8: "KILL",
}

# Heal rates per tick (normal / fast healing rooms)
HEAL_RATE_HP = 0.08      # 8%
HEAL_RATE_SP = 0.09      # 9%
HEAL_RATE_MP = 0.13      # 13%
HEAL_RATE_FAST_HP = 0.16  # 16%
HEAL_RATE_FAST_SP = 0.18  # 18%
HEAL_RATE_FAST_MP = 0.26  # 26%
