"""10woongi sigma combat — hit/damage calculation with dual HP+SP damage."""

from __future__ import annotations

import importlib
import random
from typing import Any, Callable

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


def get_wuxia_stats(char: Any) -> dict[str, int]:
    """Extract wuxia stats from character extensions or defaults."""
    ext = getattr(char, "extensions", None) or {}
    stats = ext.get("stats", {})
    return {
        "stamina": stats.get("stamina", 13),
        "agility": stats.get("agility", 13),
        "wisdom": stats.get("wisdom", 13),
        "bone": stats.get("bone", 13),
        "inner": stats.get("inner", 13),
        "spirit": stats.get("spirit", 13),
    }


def calc_hit_chance(attacker: Any, defender: Any) -> int:
    """Calculate hit chance (0~100).

    Based on attacker's spirit + hitroll vs defender's agility.
    """
    atk_stats = get_wuxia_stats(attacker)
    def_stats = get_wuxia_stats(defender)

    base = 50 + attacker.hitroll
    spirit_bonus = atk_stats["spirit"] // 2
    agi_penalty = def_stats["agility"] // 3

    return max(5, min(95, base + spirit_bonus - agi_penalty))


def calc_hp_damage(attacker: Any, defender: Any) -> int:
    """Calculate HP damage.

    Based on weapon damage + stamina bonus.
    """
    atk_stats = get_wuxia_stats(attacker)

    # Base weapon damage from damage_dice
    base = 0
    if attacker.proto and attacker.proto.damage_dice:
        base = _roll_dice(attacker.proto.damage_dice)
    else:
        base = random.randint(1, 4) + attacker.damroll

    stamina_bonus = atk_stats["stamina"] // 5
    return max(1, base + stamina_bonus + attacker.damroll)


def calc_sp_damage(attacker: Any, defender: Any) -> int:
    """Calculate SP damage (inner energy damage).

    Based on inner stat, roughly 40-60% of HP damage.
    """
    atk_stats = get_wuxia_stats(attacker)
    inner_bonus = atk_stats["inner"] // 4
    base = random.randint(1, 3) + inner_bonus
    return max(0, base)


async def perform_attack(
    attacker: Any,
    defender: Any,
    send_to_char: Callable | None = None,
) -> tuple[int, int]:
    """Execute one attack: hit check → HP damage + SP damage.

    Returns (hp_damage, sp_damage).
    """
    hit_chance = calc_hit_chance(attacker, defender)
    roll = random.randint(1, 100)

    if roll > hit_chance:
        # Miss
        if send_to_char:
            if attacker.session:
                await send_to_char(attacker, f"{{yellow}}{defender.name}에 대한 공격이 빗나갔습니다.{{reset}}")
            if defender.session:
                await send_to_char(defender, f"\r\n{{yellow}}{attacker.name}의 공격이 빗나갔습니다.{{reset}}")
        return (0, 0)

    hp_dmg = calc_hp_damage(attacker, defender)
    sp_dmg = calc_sp_damage(attacker, defender)

    defender.hp -= hp_dmg

    # SP damage: reduce move points (mapped to SP in 10woongi)
    current_sp = getattr(defender, "move", 0)
    defender.move = max(0, current_sp - sp_dmg)

    if send_to_char:
        if attacker.session:
            msg = f"{{red}}{defender.name}에게 {hp_dmg} 데미지를 입혔습니다."
            if sp_dmg > 0:
                msg += f" (내공 -{sp_dmg})"
            msg += "{reset}"
            await send_to_char(attacker, msg)
        if defender.session:
            msg = f"\r\n{{red}}{attacker.name}이(가) 당신에게 {hp_dmg} 데미지를 입혔습니다."
            if sp_dmg > 0:
                msg += f" (내공 -{sp_dmg})"
            msg += "{reset}"
            await send_to_char(defender, msg)

    return (hp_dmg, sp_dmg)


def _roll_dice(dice_str: str) -> int:
    """Roll NdS+B dice."""
    if "d" not in dice_str:
        return int(dice_str)
    left, rest = dice_str.split("d", 1)
    n = int(left) if left else 0
    if "+" in rest:
        s_str, b_str = rest.split("+", 1)
        s, b = int(s_str), int(b_str)
    elif "-" in rest:
        s_str, b_str = rest.split("-", 1)
        s, b = int(s_str), -int(b_str)
    else:
        s, b = int(rest), 0
    total = b
    for _ in range(n):
        total += random.randint(1, max(1, s))
    return max(1, total)
