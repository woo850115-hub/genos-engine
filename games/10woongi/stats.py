"""10woongi stat system — sigma formula, HP/SP/MP calculation."""

from __future__ import annotations


def sigma(n: int) -> int:
    """Sum of 1..n-1, capped at 150 then linear.

    sigma(n) = sum(1..n-1) for n <= 150
    sigma(n) = sigma(150) + (n-150)*150 for n > 150
    """
    if n <= 0:
        return 0
    if n == 1:
        return 0
    if n <= 150:
        return (n - 1) * n // 2
    # sigma(150) = 149*150/2 = 11175
    return 11175 + (n - 150) * 150


def calc_hp(bone: int) -> int:
    """Calculate max HP from 기골 (bone) stat.

    hp = 80 + 6 * (sigma(bone) / 30)
    """
    return 80 + 6 * sigma(bone) // 30


def calc_sp(inner: int, wisdom: int) -> int:
    """Calculate max SP from 내공 (inner) + 지혜 (wisdom) stats.

    sp = 80 + ((sigma(inner)*2 + sigma(wisdom)) / 30)
    """
    return 80 + (sigma(inner) * 2 + sigma(wisdom)) // 30


def calc_mp(agility: int) -> int:
    """Calculate max MP from 민첩 (agility) stat.

    mp = 50 + (sigma(agility) / 15)
    """
    return 50 + sigma(agility) // 15


def random_stat() -> int:
    """Generate a random starting stat value (11~15, weighted center)."""
    import random
    return random.randint(11, 15)


def calc_adj_exp(level: int) -> int:
    """Calculate adjusted experience reward for killing a mob of given level.

    adj_exp = level * level * 10 + level * 50
    """
    return level * level * 10 + level * 50
