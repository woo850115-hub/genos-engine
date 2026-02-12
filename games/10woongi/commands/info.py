"""10woongi info commands — original format overrides.

Based on 10woongi LP-MUD source:
- 상태.c: Box-drawing table with 6 wuxia stats, HP/SP/MP bars
- 누구.c: 강호인 명단 with faction grouping
- 가진거.c: Inventory with quantity and gold display
- 장비.c: Equipment with armor/weapon stats
"""

from __future__ import annotations

import importlib
from collections import Counter
from typing import Any

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


def register(engine: Any) -> None:
    # Override core commands with original 10woongi format
    engine.register_command("score", do_score, korean="점수")
    engine.register_command("wscore", do_score, korean="정보")
    engine.register_command("consider", do_consider, korean="판별")
    engine.register_command("equipment", do_equipment, korean="장비")
    engine.register_command("who", do_who, korean="누구")
    engine.register_command("inventory", do_inventory, korean="소지품")
    engine.register_command("i", do_inventory)


# ── Original 상태.c score format ──────────────────────────────────

# History origins (from 10woongi 상태.c)
_HISTORY_NAMES = {
    0: "없음", 1: "철방", 2: "무영루", 3: "성유림", 4: "비검산장",
    5: "환마궁", 6: "천하제일상회", 7: "객잔", 8: "도적소굴",
    9: "사막오아시스", 10: "은둔촌",
}


def _draw_graph(current: int, max_val: int, width: int = 10) -> str:
    """Draw a progress bar like original draw_graph()."""
    if max_val <= 0:
        return "░" * width
    ratio = min(current / max_val, 1.0)
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _format_stat(val: int, mod: int = 0) -> str:
    """Format a stat value with optional modifier."""
    if mod > 0:
        return f"{val}{{green}}+{mod}{{reset}}"
    elif mod < 0:
        return f"{val}{{red}}{mod}{{reset}}"
    return str(val)


async def do_score(session: Any, args: str) -> None:
    """10woongi original 상태.c format — box-drawing table with 6 wuxia stats.

    Based on lib/명령어/플레이어/상태.c.
    """
    constants = _import("constants")
    level_mod = _import("level")

    char = session.character
    if not char:
        return

    cls_name = constants.CLASS_NAMES.get(char.class_id, "무림인")
    sex_name = ["중성", "남", "여"][session.player_data.get("sex", 0)]
    age = session.player_data.get("age", 17)
    ext = getattr(char, "extensions", {}) or {}
    wstats = ext.get("stats", {})
    faction = ext.get("faction", "낭인")
    if not faction:
        faction = "낭인"
    history_id = ext.get("history", 0)
    history = _HISTORY_NAMES.get(history_id, "없음")
    fame = ext.get("fame", 0)
    pk_kills = ext.get("pk_kills", 0)
    pk_deaths = ext.get("pk_deaths", 0)

    sp = getattr(char, "move", 0)
    max_sp = getattr(char, "max_move", 0)

    # Stats
    stamina = wstats.get("stamina", 13)
    agility = wstats.get("agility", 13)
    wisdom = wstats.get("wisdom", 13)
    bone = wstats.get("bone", 13)
    inner = wstats.get("inner", 13)
    spirit = wstats.get("spirit", 13)

    # Spirit display: 極盛 at 600+
    spirit_display = "極盛" if spirit >= 600 else str(spirit)

    # Win rate in 할/푼 format
    total_pk = pk_kills + pk_deaths
    if total_pk > 0:
        win_rate = pk_kills / total_pk * 10
        hal = int(win_rate)
        pun = int((win_rate - hal) * 10)
    else:
        hal, pun = 0, 0

    # Hunger/thirst display
    hunger_val = ext.get("hunger", 100)
    if hunger_val >= 80:
        hunger_str = "든든함"
    elif hunger_val >= 40:
        hunger_str = "배고픔"
    else:
        hunger_str = "굶주림"

    drunk_val = ext.get("drunk", 0)
    if drunk_val <= 0:
        drunk_str = "정상"
    elif drunk_val < 50:
        drunk_str = "약간 취함"
    else:
        drunk_str = "만취"

    # Exp
    exp = char.experience
    needed = level_mod.exp_to_next(char)

    # Build the box-drawing table
    W = 60  # total width
    name_centered = f"· {char.name} ·"

    lines = []
    lines.append(f"┌{'─' * (W - 2)}┐")
    lines.append(f"│{name_centered:^{W - 2}}│")
    lines.append(f"├{'─' * 14}┬{'─' * 14}┬{'─' * 14}┬{'─' * (W - 46)}┤")

    # Row 1: Name, Age, Level(무공), Sex
    r1 = [
        f"이름:{char.name:<8s}",
        f"나이: {age:>4d}세",
        f"무공:{char.level:>6d} ",
        f"성별: {sex_name}",
    ]
    lines.append(f"│{r1[0]:^14s}│{r1[1]:^14s}│{r1[2]:^14s}│{r1[3]:^{W - 46}s}│")
    lines.append(f"├{'─' * 14}┼{'─' * 14}┼{'─' * 14}┼{'─' * (W - 46)}┤")

    # Row 2: Faction, Position, Master, Spouse
    r2 = [
        f"문파:{faction:<8s}",
        f"직책: {'없음':<6s}",
        f"{'':^14s}",
        "",
    ]
    lines.append(f"│{r2[0]:^14s}│{r2[1]:^14s}│{r2[2]}│{r2[3]:^{W - 46}s}│")
    lines.append(f"├{'─' * 14}┼{'─' * 14}┼{'─' * 14}┼{'─' * (W - 46)}┤")

    # Row 3: Origin
    r3 = f"출신지: {history:<6s}"
    lines.append(f"│{r3:^14s}│{'':^14s}│{'':^14s}│{'':^{W - 46}s}│")
    lines.append(f"├{'─' * 9}┬{'─' * 9}┬{'─' * 9}┬{'─' * 9}┬{'─' * 9}┬{'─' * (W - 49)}┤")

    # Stats row
    stats = [
        f"힘:{stamina:>4d}",
        f"민첩:{agility:>3d}",
        f"기골:{bone:>3d}",
        f"투지:{spirit_display:>4s}",
        f"내공:{inner:>3d}",
        f"지혜:{wisdom:>3d}",
    ]
    lines.append(
        f"│{stats[0]:^9s}│{stats[1]:^9s}│{stats[2]:^9s}│"
        f"{stats[3]:^9s}│{stats[4]:^9s}│{stats[5]:^{W - 49}s}│"
    )
    lines.append(f"├{'─' * 19}┬{'─' * 19}┬{'─' * (W - 41)}┤")

    # Fame / Exp
    lines.append(f"│{'명성: ' + str(fame):^19s}│{'수련치: ' + str(exp):^19s}│{'다음: ' + str(needed):^{W - 41}s}│")
    lines.append(f"├{'─' * 22}┬{'─' * 11}┬{'─' * (W - 37)}┤")

    # HP bar
    hp_bar = _draw_graph(char.hp, char.max_hp)
    hp_num = f"{char.hp:>5d}/{char.max_hp:<5d}"
    lines.append(f"│ {{red}}체력{{reset}} [{hp_bar}] │{hp_num:^11s}│{'공복: ' + hunger_str:^{W - 37}s}│")

    # SP bar
    sp_bar = _draw_graph(sp, max_sp)
    sp_num = f"{sp:>5d}/{max_sp:<5d}"
    lines.append(f"│ {{cyan}}내력{{reset}} [{sp_bar}] │{sp_num:^11s}│{'취함: ' + drunk_str:^{W - 37}s}│")

    # MP bar
    mp_bar = _draw_graph(char.mana, char.max_mana)
    mp_num = f"{char.mana:>5d}/{char.max_mana:<5d}"
    win_str = f"{hal}할 {pun}푼"
    lines.append(f"│ {{yellow}}이동{{reset}} [{mp_bar}] │{mp_num:^11s}│{'승률: ' + win_str:^{W - 37}s}│")

    lines.append(f"└{'─' * 22}┴{'─' * 11}┴{'─' * (W - 37)}┘")

    await session.send_line("\r\n".join(lines))


# ── Original 누구.c who format ────────────────────────────────────

async def do_who(session: Any, args: str) -> None:
    """10woongi original 누구.c format — 강호인 명단 with faction grouping.

    Based on lib/명령어/플레이어/누구.c.
    """
    constants = _import("constants")
    engine = session.engine

    lines = []
    lines.append("{cyan}·─── 강호인(江湖人) 명단 ───·{reset}")
    lines.append("")

    # Group players by faction
    by_faction: dict[str, list[str]] = {}
    admins: list[str] = []

    for name, s in engine.players.items():
        if not s.character:
            continue
        c = s.character
        ext = getattr(c, "extensions", {}) or {}
        faction = ext.get("faction", "낭인")
        if not faction:
            faction = "낭인"

        # Flags
        flags = ""
        if c.fighting:
            flags += "*"

        display = f"{flags}{c.name}【{faction}】"

        lvl = s.player_data.get("level", 1)
        if lvl >= 100:
            admins.append(display)
        else:
            by_faction.setdefault(faction, []).append(display)

    # Display by faction
    for faction, players in sorted(by_faction.items()):
        # 2-column layout
        for i in range(0, len(players), 2):
            col1 = players[i] if i < len(players) else ""
            col2 = players[i + 1] if i + 1 < len(players) else ""
            lines.append(f"  {col1:<28s}{col2}")

    if admins:
        lines.append("")
        lines.append("{yellow}운영자:{reset}")
        for a in admins:
            lines.append(f"  {a}")

    lines.append("")
    total = sum(len(v) for v in by_faction.values()) + len(admins)
    lines.append(f"현재 {total}명의 무림인이 강호에 나와 있습니다.")

    await session.send_line("\r\n".join(lines))


# ── Original 가진거.c inventory format ─────────────────────────────

async def do_inventory(session: Any, args: str) -> None:
    """10woongi original 가진거.c format — grouped items with quantity + gold.

    Based on lib/명령어/플레이어/가진거.c.
    """
    char = session.character
    if not char:
        return

    lines = []
    lines.append(f"{{cyan}}·{char.name}님의 소지품 목록·{{reset}}")

    if not char.inventory:
        lines.append("당신은 아무것도 가지고 있지 않습니다.")
        if char.gold > 0:
            lines.append(f"{{yellow}}{char.gold:,}냥{{reset}} 가지고 있습니다.")
        await session.send_line("\r\n".join(lines))
        return

    count = len(char.inventory)
    lines.append(f"현재 {{red}}{count}{{reset}}개의 물품을 가지고 있습니다.")

    # Group by short description
    counts: Counter[str] = Counter()
    for obj in char.inventory:
        counts[obj.proto.short_description] += 1

    # Display in 3-column layout
    items = []
    for desc, qty in counts.items():
        if qty > 1:
            items.append(f"{qty}개의 {desc}")
        else:
            items.append(desc)

    for i in range(0, len(items), 3):
        cols = items[i:i + 3]
        row = "  ".join(f"{c:<22s}" for c in cols)
        lines.append(f"  {row}")

    if char.gold > 0:
        lines.append(f"{{yellow}}{char.gold:,}냥{{reset}} 가지고 있습니다.")

    await session.send_line("\r\n".join(lines))


# ── Original 장비.c equipment format ──────────────────────────────

async def do_equipment(session: Any, args: str) -> None:
    """10woongi original 장비.c format — grouped by slot with armor/weapon stats.

    Based on lib/명령어/플레이어/장비.c.
    """
    constants = _import("constants")
    char = session.character
    if not char:
        return

    lines = []
    lines.append(f"{{cyan}}ㆍ{char.name}의 장비ㆍ{{reset}}")

    found = False
    total_ac = 0
    total_wc = 0

    # Group by slot type
    for slot_id, slot_name in constants.WEAR_SLOTS.items():
        obj = char.equipment.get(slot_id)
        if obj:
            found = True
            # Calculate armor/weapon values from item
            ac = 0
            wc = 0
            for aff in getattr(obj.proto, "affects", []):
                loc = aff.get("location", "")
                mod = aff.get("modifier", 0)
                if loc in ("ARMOR", "AC"):
                    ac += mod
                elif loc in ("DAMROLL", "HITROLL"):
                    wc += mod
            total_ac += ac
            total_wc += wc

            stat_str = ""
            if ac != 0:
                stat_str += f"({{cyan}}{ac:+d}{{reset}})"
            if wc != 0:
                stat_str += f"({{red}}{wc:+d}{{reset}})"

            lines.append(f"  {slot_name:6s} : {obj.proto.short_description} {stat_str}")

    if not found:
        lines.append("  착용중인 장비가 없습니다.")
    else:
        lines.append("")
        lines.append(f"  방어력 합계: {{cyan}}{total_ac}{{reset}}  공격력 합계: {{red}}{total_wc}{{reset}}")

    await session.send_line("\r\n".join(lines))


# ── Original consider ─────────────────────────────────────────────

async def do_consider(session: Any, args: str) -> None:
    """Estimate target difficulty."""
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("누구를 판별하시겠습니까?")
        return

    room = session.engine.world.get_room(char.room_vnum)
    if not room:
        return

    target_kw = args.strip().lower()
    for mob in room.characters:
        if mob is char:
            continue
        if mob.is_npc and target_kw in mob.proto.keywords.lower():
            diff = mob.level - char.level
            if diff <= -10:
                msg = "웃음이 나올 정도입니다."
            elif diff <= -5:
                msg = "쉬운 상대입니다."
            elif diff <= 0:
                msg = "비슷한 수준입니다."
            elif diff <= 5:
                msg = "조심해야 합니다."
            elif diff <= 10:
                msg = "매우 위험합니다!"
            else:
                msg = "상대가 되지 않습니다. 도망치세요!"
            await session.send_line(f"{mob.name}: {msg}")
            return

    await session.send_line("그런 대상을 찾을 수 없습니다.")
