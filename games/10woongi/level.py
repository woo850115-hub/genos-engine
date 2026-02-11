"""10woongi level/promotion system — experience, level-up, class advancement."""

from __future__ import annotations

import importlib
import random
from typing import Any, Callable

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


def exp_to_next(char: Any) -> int:
    """Calculate exp needed for next level."""
    level = char.level
    return level * level * 100 + level * 500


def check_level_up(char: Any) -> bool:
    """Check if character has enough exp to level up."""
    return char.experience >= exp_to_next(char)


async def do_level_up(char: Any, send_fn: Callable | None = None) -> None:
    """Process level up — increase stats, recalculate HP/SP/MP."""
    stats_mod = _import("stats")
    constants = _import("constants")

    while char.experience >= exp_to_next(char):
        char.player_level += 1
        level = char.player_level

        # HP gain from class
        cls = constants.CLASS_NAMES.get(char.class_id, "투사")
        hp_gain = random.randint(6, 26)  # Default, refined per class below
        if char.class_id in (2, 7, 10, 13):
            hp_gain = random.randint(10, 30)
        elif char.class_id in (3, 5):
            hp_gain = random.randint(12, 32)
        elif char.class_id in (4, 11):
            hp_gain = random.randint(10, 40)
        elif char.class_id in (8, 14):
            hp_gain = random.randint(12, 52)

        char.max_hp += hp_gain
        char.hp = char.max_hp

        # Recalculate SP/MP from stats
        ext = getattr(char, "extensions", {}) or {}
        wstats = ext.get("stats", {})
        if wstats:
            new_sp = stats_mod.calc_sp(
                wstats.get("inner", 13), wstats.get("wisdom", 13)
            )
            new_mp = stats_mod.calc_mp(wstats.get("agility", 13))
            char.max_move = new_sp
            char.move = new_sp
            char.max_mana = new_mp
            char.mana = new_mp

        if send_fn:
            await send_fn(
                f"{{bright_yellow}}레벨 {level}이(가) 되었습니다! "
                f"(HP +{hp_gain}){{reset}}"
            )

        # Check promotion
        promo = constants.PROMOTION_CHAIN.get(char.class_id)
        if promo:
            req_level, next_class = promo
            if level >= req_level:
                old_cls = constants.CLASS_NAMES.get(char.class_id, "?")
                char.class_id = next_class
                new_cls = constants.CLASS_NAMES.get(next_class, "?")
                if send_fn:
                    await send_fn(
                        f"{{bright_green}}{old_cls}에서 {new_cls}(으)로 승급했습니다!{{reset}}"
                    )
