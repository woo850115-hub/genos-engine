"""3eyes level / experience system — single exp table, stat cycling on level up."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.world import MobInstance

import importlib

_PKG = "games.3eyes"


def _const():
    return importlib.import_module(f"{_PKG}.constants")


# ── Experience table from global.c level_exp[202] ────────────────
# Single table shared by all classes (class_id 0 = universal)
EXP_TABLE: dict[int, int] = {
    1: 132, 2: 256, 3: 384, 4: 512, 5: 640, 6: 768, 7: 896, 8: 1024,
    9: 1280, 10: 1536, 11: 1792, 12: 2048, 13: 2560, 14: 3072,
    15: 3584, 16: 4096, 17: 5120, 18: 6144, 19: 7168, 20: 8192,
    21: 10240, 22: 12288, 23: 14336, 24: 16384, 25: 20480,
    26: 24576, 27: 28672, 28: 32768, 29: 37960, 30: 45152,
    31: 50344, 32: 57503, 33: 65342, 34: 72504, 35: 80342,
    36: 87504, 37: 95045, 38: 102504, 39: 110004, 40: 117503,
    41: 125003, 42: 132505, 43: 140050, 44: 147560, 45: 155003,
    46: 162520, 47: 170344, 48: 177505, 49: 185006, 50: 192543,
    51: 200000, 52: 226003, 53: 252030, 54: 278030, 55: 304034,
    56: 330043, 57: 356300, 58: 382004, 59: 408004, 60: 434230,
    61: 460340, 62: 486040, 63: 512005, 64: 538005, 65: 564004,
    66: 590002, 67: 616003, 68: 642045, 69: 668056, 70: 694004,
    71: 720004, 72: 746040, 73: 772005, 74: 798007, 75: 824340,
    76: 850040, 77: 876003, 78: 902004, 79: 928040, 80: 954004,
    81: 1000340, 82: 1050034, 83: 1100004, 84: 1150000, 85: 1200020,
    86: 1250343, 87: 1300021, 88: 1350450, 89: 1400003, 90: 1450340,
    91: 1500006, 92: 1550234, 93: 1600004, 94: 1650000, 95: 1700008,
    96: 1750230, 97: 1800643, 98: 1850030, 99: 1900037, 100: 1955600,
    101: 2000340, 102: 2066045, 103: 2132023, 104: 2198004, 105: 2264060,
    106: 2330520, 107: 2396050, 108: 2462003, 109: 2528040, 110: 2594006,
    111: 2660030, 112: 2726006, 113: 2792030, 114: 2858004, 115: 2924600,
    116: 2930033, 117: 2996234, 118: 3062004, 119: 3128020, 120: 3194050,
    121: 3260000, 122: 3326033, 123: 3392030, 124: 3458060, 125: 3524006,
    126: 3590320, 127: 3656034, 128: 3722004, 129: 3788004, 130: 3854500,
    131: 4000330, 132: 4100040, 133: 4200023, 134: 4300004, 135: 4400060,
    136: 4500230, 137: 4600300, 138: 4700420, 139: 4800034, 140: 4900004,
    141: 5000033, 142: 5100230, 143: 5200003, 144: 5304200, 145: 5400560,
    146: 5500320, 147: 5600430, 148: 5700230, 149: 5800003, 150: 5900060,
    151: 6000430, 152: 6130030, 153: 6260342, 154: 6390000, 155: 6520800,
    156: 6650030, 157: 6780034, 158: 6910004, 159: 7040000, 160: 7170060,
    161: 7300032, 162: 7430320, 163: 7560340, 164: 7690040, 165: 7820040,
    166: 7950004, 167: 8080005, 168: 8210040, 169: 8340004, 170: 8470006,
    171: 8600004, 172: 8730034, 173: 8860002, 174: 8990340, 175: 9120400,
    176: 9250030, 177: 9380050, 178: 9510340, 179: 9640004, 180: 9770000,
    181: 10000030, 182: 10200030, 183: 10400030, 184: 10600000,
    185: 10800560, 186: 11003030, 187: 11204520, 188: 11403400,
    189: 11602400, 190: 11800006, 191: 12004040, 192: 12200532,
    193: 12400233, 194: 12600004, 195: 12800640, 196: 13000320,
    197: 13503334, 198: 14004342, 199: 14500060, 200: 15000005,
    201: 16000000,
}


def exp_for_level(level: int) -> int:
    """Get experience required to reach a given level."""
    c = _const()
    return EXP_TABLE.get(min(level, c.MAX_MORTAL_LEVEL), 0)


def check_level_up(char: MobInstance) -> bool:
    if char.is_npc:
        return False
    c = _const()
    if char.level >= c.MAX_MORTAL_LEVEL:
        return False
    needed = exp_for_level(char.level + 1)
    return char.experience >= needed


async def do_level_up(char: MobInstance, send_fn=None) -> dict[str, int | str]:
    """Perform level up — 3eyes style with stat cycling."""
    c = _const()
    if char.level >= c.MAX_MORTAL_LEVEL:
        return {}

    char.level = char.level + 1
    cls = c.CLASS_STATS.get(char.class_id, c.CLASS_STATS[4])

    hp_gain = max(1, cls["hp_lv"])
    mp_gain = max(0, cls["mp_lv"])

    # CON bonus to HP
    con = char.stats.get("con", 13) if char.stats else 13
    con_bonus = c.get_stat_bonus(con)
    hp_gain = max(1, hp_gain + con_bonus)

    char.max_hp += hp_gain
    char.max_mana += mp_gain
    char.hp = char.max_hp
    char.mana = char.max_mana

    # Stat cycling: level_cycle[class][level % 10]
    cycle = c.LEVEL_CYCLE.get(char.class_id, c.LEVEL_CYCLE[4])
    stat_key = cycle[(char.level - 1) % 10]
    stat_gained = ""
    if char.stats:
        old_val = char.stats.get(stat_key, 13)
        char.stats[stat_key] = min(63, old_val + 1)
        stat_gained = stat_key

    result: dict[str, int | str] = {"hp": hp_gain, "mana": mp_gain}
    if stat_gained:
        result["stat"] = stat_gained

    if send_fn:
        class_name = c.CLASS_NAMES.get(char.class_id, "모험가")
        stat_kr = {"str": "힘", "dex": "민첩", "con": "체력",
                   "int": "지능", "pie": "신앙"}.get(stat_gained, stat_gained)
        await send_fn(
            f"\r\n{{bright_yellow}}*** 레벨 업! ***{{reset}}\r\n"
            f"{{bright_cyan}}레벨 {char.level} {class_name}{{reset}}\r\n"
            f"HP: +{hp_gain}  마나: +{mp_gain}"
            + (f"  {stat_kr}: +1" if stat_gained else "")
            + "\r\n"
        )

    return result


def exp_to_next(char: MobInstance) -> int:
    c = _const()
    if char.level >= c.MAX_MORTAL_LEVEL:
        return 0
    needed = exp_for_level(char.level + 1)
    return max(0, needed - char.experience)
