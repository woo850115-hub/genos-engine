"""Level and experience system — from exp_tables.lua and classes.lua."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.world import MobInstance

# ── Experience tables (from exp_tables.lua) ──────────────────────
# EXP_TABLE[class_id][level] → exp needed to reach that level
EXP_TABLE: dict[int, dict[int, int]] = {
    0: {  # Magic User
        0: 0, 1: 1, 2: 2500, 3: 5000, 4: 10000, 5: 20000, 6: 40000,
        7: 60000, 8: 90000, 9: 135000, 10: 250000, 11: 375000, 12: 750000,
        13: 1125000, 14: 1500000, 15: 1875000, 16: 2250000, 17: 2625000,
        18: 3000000, 19: 3375000, 20: 3750000, 21: 4000000, 22: 4300000,
        23: 4600000, 24: 4900000, 25: 5200000, 26: 5500000, 27: 5950000,
        28: 6400000, 29: 6850000, 30: 7400000, 31: 8000000,
    },
    1: {  # Cleric
        0: 0, 1: 1, 2: 1500, 3: 3000, 4: 6000, 5: 13000, 6: 27500,
        7: 55000, 8: 110000, 9: 225000, 10: 450000, 11: 675000, 12: 900000,
        13: 1125000, 14: 1350000, 15: 1575000, 16: 1800000, 17: 2100000,
        18: 2400000, 19: 2700000, 20: 3000000, 21: 3250000, 22: 3500000,
        23: 3800000, 24: 4100000, 25: 4400000, 26: 4800000, 27: 5200000,
        28: 5600000, 29: 6000000, 30: 6400000, 31: 7000000,
    },
    2: {  # Thief
        0: 0, 1: 1, 2: 1250, 3: 2500, 4: 5000, 5: 10000, 6: 20000,
        7: 40000, 8: 70000, 9: 110000, 10: 160000, 11: 220000, 12: 440000,
        13: 660000, 14: 880000, 15: 1100000, 16: 1500000, 17: 2000000,
        18: 2500000, 19: 3000000, 20: 3500000, 21: 3650000, 22: 3800000,
        23: 4100000, 24: 4400000, 25: 4700000, 26: 5100000, 27: 5500000,
        28: 5900000, 29: 6300000, 30: 6650000, 31: 7000000,
    },
    3: {  # Warrior
        0: 0, 1: 1, 2: 2000, 3: 4000, 4: 8000, 5: 16000, 6: 32000,
        7: 64000, 8: 125000, 9: 250000, 10: 500000, 11: 750000, 12: 1000000,
        13: 1250000, 14: 1500000, 15: 1850000, 16: 2200000, 17: 2550000,
        18: 2900000, 19: 3250000, 20: 3600000, 21: 3900000, 22: 4200000,
        23: 4500000, 24: 4800000, 25: 5150000, 26: 5500000, 27: 5950000,
        28: 6400000, 29: 6850000, 30: 7400000, 31: 8000000,
    },
}

# ── Class HP/Mana gains (from classes.lua) ───────────────────────
CLASS_GAINS: dict[int, dict[str, tuple[int, int]]] = {
    0: {"hp": (3, 8), "mana": (5, 10), "move": (0, 0)},   # Magic User
    1: {"hp": (5, 10), "mana": (3, 8), "move": (0, 0)},   # Cleric
    2: {"hp": (6, 11), "mana": (0, 0), "move": (0, 0)},   # Thief
    3: {"hp": (10, 15), "mana": (0, 0), "move": (0, 0)},   # Warrior
}

CLASS_NAMES = {0: "마법사", 1: "성직자", 2: "도적", 3: "전사"}

MAX_LEVEL = 34


def exp_for_level(class_id: int, level: int) -> int:
    """Get experience required to reach a given level."""
    tbl = EXP_TABLE.get(class_id, EXP_TABLE[0])
    return tbl.get(min(level, MAX_LEVEL), tbl.get(MAX_LEVEL, 8000000))


def check_level_up(char: MobInstance) -> bool:
    """Check if character has enough exp to level up."""
    if char.is_npc:
        return False
    if char.level >= MAX_LEVEL:
        return False
    needed = exp_for_level(char.class_id, char.level + 1)
    return char.experience >= needed


async def do_level_up(char: MobInstance, send_fn=None) -> dict[str, int]:
    """Perform level up. Returns dict of gains."""
    if char.level >= MAX_LEVEL:
        return {}

    char.level = char.level + 1
    gains = CLASS_GAINS.get(char.class_id, CLASS_GAINS[0])

    hp_lo, hp_hi = gains["hp"]
    hp_gain = random.randint(hp_lo, hp_hi) if hp_hi > 0 else 0
    # Constitution bonus
    con_bonus = _con_hp_bonus(char.con)
    hp_gain = max(1, hp_gain + con_bonus)

    mana_lo, mana_hi = gains["mana"]
    mana_gain = random.randint(mana_lo, mana_hi) if mana_hi > 0 else 0

    move_lo, move_hi = gains["move"]
    move_gain = random.randint(move_lo, move_hi) if move_hi > 0 else 0

    char.max_hp += hp_gain
    char.hp = char.max_hp
    char.max_mana += mana_gain
    char.mana = char.max_mana
    char.max_move += move_gain
    char.move = char.max_move

    result = {"hp": hp_gain, "mana": mana_gain, "move": move_gain}

    if send_fn:
        class_name = CLASS_NAMES.get(char.class_id, "모험가")
        await send_fn(
            f"\r\n{{bright_yellow}}*** 레벨 업! ***{{reset}}\r\n"
            f"{{bright_cyan}}레벨 {char.level} {class_name}{{reset}}\r\n"
            f"HP: +{hp_gain}  마나: +{mana_gain}  이동: +{move_gain}\r\n"
        )

    return result


def _con_hp_bonus(con: int) -> int:
    """Constitution HP bonus per level."""
    bonuses = {
        0: -4, 1: -3, 2: -2, 3: -2, 4: -1, 5: -1, 6: -1,
        7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0,
        15: 1, 16: 2, 17: 2, 18: 3, 19: 3, 20: 4, 21: 5,
        22: 5, 23: 5, 24: 6, 25: 6,
    }
    return bonuses.get(min(max(con, 0), 25), 0)


def exp_to_next(char: MobInstance) -> int:
    """Experience remaining to next level."""
    if char.level >= MAX_LEVEL:
        return 0
    needed = exp_for_level(char.class_id, char.level + 1)
    return max(0, needed - char.experience)
