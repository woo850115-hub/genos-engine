"""THAC0 combat engine — hit/damage rolls, combat rounds, attack types."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.world import MobInstance

# ── Attack type names (from combat.lua) ──────────────────────────
ATTACK_TYPES = {
    0: "때림", 1: "찌름(쏘아)", 2: "채찍질", 3: "베기",
    4: "물기", 5: "타격", 6: "으스러뜨림", 7: "두드림",
    8: "할퀴기", 9: "난타", 10: "강타", 11: "관통",
    12: "폭발", 13: "주먹질", 14: "찌르기",
}

# ── THAC0 tables (from stat_tables.lua) ──────────────────────────
# thac0[class_id][level] → THAC0 value
THAC0_TABLE: dict[int, dict[int, int]] = {
    0: {0: 100, 1: 20, 2: 20, 3: 20, 4: 19, 5: 19, 6: 19, 7: 18, 8: 18, 9: 18,
        10: 17, 11: 17, 12: 17, 13: 16, 14: 16, 15: 16, 16: 15, 17: 15, 18: 15,
        19: 14, 20: 14, 21: 14, 22: 13, 23: 13, 24: 13, 25: 12, 26: 12, 27: 12,
        28: 11, 29: 11, 30: 11, 31: 10, 32: 10, 33: 10, 34: 9},
    1: {0: 100, 1: 20, 2: 20, 3: 20, 4: 18, 5: 18, 6: 18, 7: 16, 8: 16, 9: 16,
        10: 14, 11: 14, 12: 14, 13: 12, 14: 12, 15: 12, 16: 10, 17: 10, 18: 10,
        19: 8, 20: 8, 21: 8, 22: 6, 23: 6, 24: 6, 25: 4, 26: 4, 27: 4,
        28: 2, 29: 2, 30: 2, 31: 1, 32: 1, 33: 1, 34: 1},
    2: {0: 100, 1: 20, 2: 20, 3: 19, 4: 19, 5: 18, 6: 18, 7: 17, 8: 17, 9: 16,
        10: 16, 11: 15, 12: 15, 13: 14, 14: 14, 15: 13, 16: 13, 17: 12, 18: 12,
        19: 11, 20: 11, 21: 10, 22: 10, 23: 9, 24: 9, 25: 8, 26: 8, 27: 7,
        28: 7, 29: 6, 30: 6, 31: 5, 32: 5, 33: 4, 34: 4},
    3: {0: 100, 1: 20, 2: 19, 3: 18, 4: 17, 5: 16, 6: 15, 7: 14, 8: 14, 9: 13,
        10: 12, 11: 11, 12: 10, 13: 9, 14: 8, 15: 7, 16: 6, 17: 5, 18: 4,
        19: 3, 20: 2, 21: 1, 22: 1, 23: 1, 24: 1, 25: 1, 26: 1, 27: 1,
        28: 1, 29: 1, 30: 1, 31: 1, 32: 1, 33: 1, 34: 1},
}

# Strength bonuses (indices 0–30)
STR_TOHIT = {
    0: -5, 1: -5, 2: -3, 3: -3, 4: -2, 5: -2, 6: -1, 7: -1, 8: 0, 9: 0,
    10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 1, 18: 1,
    19: 3, 20: 3, 21: 4, 22: 4, 23: 5, 24: 6, 25: 7,
    26: 1, 27: 2, 28: 2, 29: 2, 30: 3,
}
STR_TODAM = {
    0: -4, 1: -4, 2: -2, 3: -1, 4: -1, 5: -1, 6: 0, 7: 0, 8: 0, 9: 0,
    10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 1, 17: 1, 18: 2,
    19: 7, 20: 8, 21: 9, 22: 10, 23: 11, 24: 12, 25: 14,
    26: 3, 27: 3, 28: 4, 29: 5, 30: 6,
}

# Dexterity defensive bonus
DEX_DEFENSIVE = {
    0: 6, 1: 5, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1, 7: 0, 8: 0, 9: 0,
    10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: -1, 16: -2, 17: -3, 18: -4,
    19: -4, 20: -4, 21: -5, 22: -5, 23: -5, 24: -6, 25: -6,
}

# Saving throw types
SAVE_PARA = 0
SAVE_ROD = 1
SAVE_PETRI = 2
SAVE_BREATH = 3
SAVE_SPELL = 4


def get_thac0(class_id: int, level: int) -> int:
    """Get THAC0 for class and level."""
    tbl = THAC0_TABLE.get(class_id, THAC0_TABLE[0])
    clamped = min(level, max(tbl.keys()))
    return tbl.get(clamped, 20)


def compute_ac(char: MobInstance) -> int:
    """Compute effective armor class (lower = better)."""
    ac = char.proto.armor_class if char.is_npc else 100
    # Equipment AC bonuses
    for obj in char.equipment.values():
        if obj.proto and obj.proto.affects:
            for aff in obj.proto.affects:
                if isinstance(aff, dict) and aff.get("location") == "AC":
                    ac += aff.get("modifier", 0)
    # Dex bonus
    dex = min(max(char.dex, 0), 25)
    ac += DEX_DEFENSIVE.get(dex, 0)
    return max(-10, min(ac, 100))


def roll_hit(attacker: MobInstance, defender: MobInstance) -> bool:
    """THAC0 hit roll. Returns True if hit lands."""
    # NPC: use proto hitroll + level-based THAC0 estimate
    if attacker.is_npc:
        thac0 = max(1, 20 - attacker.level)
        hr = attacker.proto.hitroll
    else:
        thac0 = get_thac0(attacker.class_id, attacker.level)
        hr = attacker.hitroll + STR_TOHIT.get(min(attacker.str, 30), 0)

    ac = compute_ac(defender)
    roll = random.randint(1, 20)
    needed = thac0 - hr
    # Natural 20 always hits, natural 1 always misses
    if roll == 20:
        return True
    if roll == 1:
        return False
    return roll >= needed - ac


def roll_damage(attacker: MobInstance) -> int:
    """Roll damage for a physical attack."""
    dice_str = attacker.proto.damage_dice
    num, rest = dice_str.split("d")
    if "+" in rest:
        size, bonus = rest.split("+")
    elif "-" in rest:
        size, bonus = rest.split("-")
        bonus = f"-{bonus}"
    else:
        size, bonus = rest, "0"

    total = int(bonus)
    for _ in range(int(num)):
        total += random.randint(1, int(size))

    # Strength damage bonus
    if not attacker.is_npc:
        total += STR_TODAM.get(min(attacker.str, 30), 0)
        total += attacker.damroll

    return max(1, total)


def get_attack_type(attacker: MobInstance) -> tuple[int, str]:
    """Get attack type index and name for display."""
    # Check weapon in WIELD slot (slot 16)
    weapon = attacker.equipment.get(16)
    if weapon and weapon.proto:
        atk_type = weapon.proto.values[3] if len(weapon.proto.values) > 3 else 0
    else:
        atk_type = 0  # bare-hand hit
    name = ATTACK_TYPES.get(atk_type, "때림")
    return atk_type, name


def damage_message(damage: int) -> str:
    """Get Korean damage severity message."""
    if damage <= 0:
        return "빗나감"
    elif damage <= 2:
        return "긁힘"
    elif damage <= 5:
        return "약한 타격"
    elif damage <= 10:
        return "타격"
    elif damage <= 15:
        return "강한 타격"
    elif damage <= 20:
        return "매우 강한 타격"
    elif damage <= 30:
        return "치명적 타격"
    else:
        return "파괴적 타격"


async def perform_attack(attacker: MobInstance, defender: MobInstance,
                         send_to_char=None, send_to_room=None) -> int:
    """Perform one attack round. Returns damage dealt."""
    _, atk_name = get_attack_type(attacker)

    if not roll_hit(attacker, defender):
        if send_to_char:
            await send_to_char(
                attacker, f"{{yellow}}{defender.name}에게 {atk_name}을 시도하지만 빗나갑니다!{{reset}}"
            )
        if send_to_char and defender.session:
            await send_to_char(
                defender, f"{{yellow}}{attacker.name}의 {atk_name}이 빗나갑니다!{{reset}}"
            )
        return 0

    damage = roll_damage(attacker)
    severity = damage_message(damage)

    if send_to_char:
        await send_to_char(
            attacker,
            f"{{red}}{defender.name}에게 {atk_name}으로 {severity}을 입힙니다! [{damage}]{{reset}}"
        )
    if send_to_char and defender.session:
        await send_to_char(
            defender,
            f"{{red}}{attacker.name}의 {atk_name}이 {severity}을 입힙니다! [{damage}]{{reset}}"
        )

    defender.hp -= damage
    return damage


def extra_attacks(attacker: MobInstance) -> int:
    """Number of extra attacks per round (0 = 1 total attack)."""
    if attacker.is_npc:
        # NPCs: 1 extra per 10 levels, max 3 extra
        return min(attacker.level // 10, 3)
    # Players: warriors get extra attacks at level 10 and 20
    if attacker.class_id == 3:  # Warrior
        if attacker.level >= 20:
            return 2
        elif attacker.level >= 10:
            return 1
    return 0
