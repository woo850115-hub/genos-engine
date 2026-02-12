"""Simoon level / experience system — single exp table for all classes."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.world import MobInstance

from games.simoon.constants import (
    CLASS_GAINS, CLASS_NAMES, MAX_LEVEL, MAX_MORTAL_LEVEL,
)

# ── Single experience table (class-independent) ────────────────
# From data/simoon/lua/exp_tables.lua — class 0 used for all classes
EXP_TABLE: dict[int, int] = {
    0: 0, 1: 2000, 2: 5200, 3: 8400, 4: 12600, 5: 15000,
    6: 23000, 7: 32000, 8: 36000, 9: 40000, 10: 46000,
    11: 50000, 12: 55000, 13: 60000, 14: 65000, 15: 70000,
    16: 75500, 17: 86000, 18: 96500, 19: 107000, 20: 117500,
    21: 128000, 22: 138500, 23: 149000, 24: 159500, 25: 170000,
    26: 180500, 27: 191000, 28: 201500, 29: 206000, 30: 210000,
    40: 350000, 50: 430000, 60: 530000, 70: 680000, 80: 930000,
    90: 1330000, 100: 2920000, 110: 3670000, 120: 4420000,
    130: 5170000, 140: 5920000, 150: 13500000, 160: 15000000,
    170: 17000000, 180: 20000000, 190: 25000000, 200: 43100000,
    210: 50000000, 220: 60000000, 230: 75000000, 240: 95000000,
    250: 117100000, 260: 140000000, 270: 165000000, 280: 190000000,
    290: 210000000, 300: 220100000, 301: 250000000, 302: 300000000,
    303: 350000000, 304: 380000000, 305: 401000000,
    306: 500000000, 307: 600000000, 308: 700000000,
    309: 900000000, 310: 1100000000, 311: 1400000000,
    312: 1700000000, 313: 2000000000,
}


def _interpolate_exp(level: int) -> int:
    """Get exp for a level, interpolating between known checkpoints."""
    if level in EXP_TABLE:
        return EXP_TABLE[level]
    # Find surrounding known levels
    lower = max(k for k in EXP_TABLE if k <= level)
    upper = min(k for k in EXP_TABLE if k > level)
    lo_exp = EXP_TABLE[lower]
    hi_exp = EXP_TABLE[upper]
    frac = (level - lower) / (upper - lower)
    return int(lo_exp + (hi_exp - lo_exp) * frac)


def exp_for_level(level: int) -> int:
    """Get experience required to reach a given level."""
    return _interpolate_exp(min(level, MAX_LEVEL))


def check_level_up(char: MobInstance) -> bool:
    if char.is_npc:
        return False
    if char.level >= MAX_MORTAL_LEVEL:
        return False
    needed = exp_for_level(char.level + 1)
    return char.experience >= needed


async def do_level_up(char: MobInstance, send_fn=None) -> dict[str, int]:
    """Perform level up — Simoon style (no class-specific exp table)."""
    if char.level >= MAX_MORTAL_LEVEL:
        return {}

    char.level = char.level + 1
    gains = CLASS_GAINS.get(char.class_id, CLASS_GAINS[3])

    hp_lo, hp_hi = gains["hp"]
    hp_gain = random.randint(hp_lo, hp_hi) if hp_hi > 0 else 0
    # CON bonus
    con = char.stats.get("con", 13) if char.stats else 13
    con_bonus = _con_hp_bonus(con)
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

    # Practice sessions (WIS-based)
    wis = char.stats.get("wis", 13) if char.stats else 13
    prac_gain = max(1, wis // 5)
    result["practices"] = prac_gain

    if char.session:
        pd = char.session.player_data
        pd["practices"] = pd.get("practices", 0) + prac_gain

    if send_fn:
        class_name = CLASS_NAMES.get(char.class_id, "모험가")
        await send_fn(
            f"\r\n{{bright_yellow}}*** 레벨 업! ***{{reset}}\r\n"
            f"{{bright_cyan}}레벨 {char.level} {class_name}{{reset}}\r\n"
            f"HP: +{hp_gain}  마나: +{mana_gain}  이동: +{move_gain}"
            f"  연습: +{prac_gain}회\r\n"
        )

    return result


def exp_to_next(char: MobInstance) -> int:
    if char.level >= MAX_MORTAL_LEVEL:
        return 0
    needed = exp_for_level(char.level + 1)
    return max(0, needed - char.experience)


def _con_hp_bonus(con: int) -> int:
    bonuses = {
        0: -4, 1: -3, 2: -2, 3: -2, 4: -1, 5: -1, 6: -1,
        7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0,
        15: 1, 16: 2, 17: 2, 18: 3, 19: 3, 20: 4, 21: 5,
        22: 5, 23: 5, 24: 6, 25: 6,
    }
    return bonuses.get(min(max(con, 0), 25), 0)
