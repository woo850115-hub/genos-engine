"""Information commands — time, weather, consider, examine, score, who, inventory, etc.

Overrides core engine commands with original tbaMUD-style output (한글화).
Based on act.informative.c from CircleMUD/tbaMUD.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine import Engine
    from core.session import Session


def register(engine: Engine) -> None:
    engine.register_command("time", do_time, korean="시간")
    engine.register_command("weather", do_weather, korean="날씨")
    engine.register_command("examine", do_examine, korean="조사")
    engine.register_command("consider", do_consider, korean="평가")
    engine.register_command("where", do_where, korean="어디")
    # Override core commands with original tbaMUD format
    engine.register_command("score", do_score, korean="점수")
    engine.register_command("who", do_who, korean="누구")
    engine.register_command("inventory", do_inventory, korean="소지품")
    engine.register_command("i", do_inventory)
    engine.register_command("equipment", do_equipment, korean="장비")
    engine.register_command("eq", do_equipment)
    engine.register_command("exits", do_exits, korean="출구")


async def do_time(session: Session, args: str) -> None:
    await session.send_line("현재 시각을 알 수 없습니다. (구현 예정)")


async def do_weather(session: Session, args: str) -> None:
    await session.send_line("날씨는 맑습니다. (구현 예정)")


async def do_examine(session: Session, args: str) -> None:
    if not args:
        await session.send_line("무엇을 조사하시겠습니까?")
        return
    # For now, same as look
    await session.engine.do_look(session, args)


async def do_consider(session: Session, args: str) -> None:
    if not args:
        await session.send_line("누구를 평가하시겠습니까?")
        return
    char = session.character
    if not char:
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
                msg = "이제 눈을 감고도 이길 수 있습니다."
            elif diff <= -5:
                msg = "쉬운 상대입니다."
            elif diff <= -2:
                msg = "어렵지 않은 상대입니다."
            elif diff <= 2:
                msg = "꽤 대등한 상대입니다."
            elif diff <= 5:
                msg = "조금 힘든 싸움이 될 것 같습니다."
            elif diff <= 10:
                msg = "매우 위험한 상대입니다!"
            else:
                msg = "자살 행위입니다!!!"
            await session.send_line(msg)
            return
    await session.send_line("그런 대상을 찾을 수 없습니다.")


async def do_where(session: Session, args: str) -> None:
    """Show location of players or named mobs in the same zone."""
    char = session.character
    if not char:
        return
    room = session.engine.world.get_room(char.room_vnum)
    if not room:
        return
    zone = room.proto.zone_vnum

    if not args:
        # Show all players in same zone
        lines = ["{bright_cyan}-- 주변 플레이어 --{reset}"]
        found = False
        for rm in session.engine.world.rooms.values():
            if rm.proto.zone_vnum != zone:
                continue
            for ch in rm.characters:
                if not ch.is_npc and ch is not char:
                    lines.append(f"  {ch.name} — {rm.proto.name}")
                    found = True
        if not found:
            lines.append("  주변에 다른 플레이어가 없습니다.")
        await session.send_line("\r\n".join(lines))
    else:
        target_kw = args.strip().lower()
        lines = [f"{{bright_cyan}}-- '{args}' 탐색 결과 --{{reset}}"]
        found = False
        for rm in session.engine.world.rooms.values():
            if rm.proto.zone_vnum != zone:
                continue
            for ch in rm.characters:
                if target_kw in ch.proto.keywords.lower() or (ch.player_name and target_kw in ch.player_name.lower()):
                    lines.append(f"  {ch.name} — {rm.proto.name}")
                    found = True
        if not found:
            lines.append("  찾을 수 없습니다.")
        await session.send_line("\r\n".join(lines))


# ── Original tbaMUD format overrides ─────────────────────────────

# Position names (from tbaMUD act.informative.c)
_POS_NAMES = {
    0: "죽어 있습니다",
    1: "빈사 상태입니다",
    2: "의식불명입니다",
    3: "기절해 있습니다",
    4: "잠들어 있습니다",
    5: "쉬고 있습니다",
    6: "앉아 있습니다",
    7: "전투 중입니다",
    8: "서 있습니다",
}

# tbaMUD 18 wear positions (from constants.c wear_where[])
_WEAR_WHERE = [
    "<머리 위에>        ",  # 0 WEAR_LIGHT
    "<왼손 손가락에>    ",  # 1 WEAR_FINGER_R
    "<오른손 손가락에>  ",  # 2 WEAR_FINGER_L
    "<목에>             ",  # 3 WEAR_NECK_1
    "<목에>             ",  # 4 WEAR_NECK_2
    "<몸통에>           ",  # 5 WEAR_BODY
    "<머리에>           ",  # 6 WEAR_HEAD
    "<다리에>           ",  # 7 WEAR_LEGS
    "<발에>             ",  # 8 WEAR_FEET
    "<손에>             ",  # 9 WEAR_HANDS
    "<팔에>             ",  # 10 WEAR_ARMS
    "<방패로>           ",  # 11 WEAR_SHIELD
    "<몸 주위에>        ",  # 12 WEAR_ABOUT
    "<허리에>           ",  # 13 WEAR_WAIST
    "<왼쪽 손목에>      ",  # 14 WEAR_WRIST_R
    "<오른쪽 손목에>    ",  # 15 WEAR_WRIST_L
    "<오른손에 들고>    ",  # 16 WEAR_WIELD
    "<왼손에 들고>      ",  # 17 WEAR_HOLD
]


def _obj_modifiers(obj) -> str:
    """Return modifier string for object display (original show_obj_modifiers)."""
    mods = []
    extra_flags = getattr(obj.proto, "extra_flags", [])
    if 1 in extra_flags:  # ITEM_GLOW
        mods.append("..빛나고 있습니다!")
    if 2 in extra_flags:  # ITEM_HUM
        mods.append("..윙윙거리는 소리가 납니다!")
    if 3 in extra_flags:  # ITEM_INVISIBLE
        mods.append("(투명)")
    return " ".join(mods)


async def do_score(session: Session, args: str) -> None:
    """tbaMUD original do_score format (한글화).

    Based on act.informative.c ACMD(do_score).
    """
    from games.tbamud.level import CLASS_NAMES, exp_to_next

    char = session.character
    if not char:
        return

    cls_name = CLASS_NAMES.get(char.class_id, "모험가")
    sex_name = ["중성", "남성", "여성"][session.player_data.get("sex", 0)]
    age = session.player_data.get("age", 17)
    title = session.player_data.get("title", "")

    # Compute AC from base + equipment affects
    ac = 100
    for obj in char.equipment.values():
        for aff in getattr(obj.proto, "affects", []):
            loc = aff.get("location", "")
            if loc == "ARMOR" or loc == "AC":
                ac += aff.get("modifier", 0)

    alignment = getattr(char, "alignment", getattr(char.proto, "alignment", 0))

    lines = []

    # Age
    lines.append(f"당신은 {age}살입니다.")

    # HP / Mana / Move
    lines.append(
        f"체력 {{green}}{char.hp}({char.max_hp}){{reset}}, "
        f"마나 {{cyan}}{char.mana}({char.max_mana}){{reset}}, "
        f"이동력 {char.move}({char.max_move})입니다."
    )

    # AC / Alignment
    lines.append(f"방어도 {ac // 10}/10, 성향 {alignment}입니다.")

    # Experience / Gold
    lines.append(
        f"경험치 {{yellow}}{char.experience:,}{{reset}}, "
        f"골드 {{yellow}}{char.gold:,}{{reset}}입니다."
    )

    # Next level (only for mortals)
    if char.level < 31:
        needed = exp_to_next(char)
        lines.append(f"다음 레벨까지 {{yellow}}{needed:,}{{reset}} 경험치가 필요합니다.")

    # Stats
    lines.append(
        f"힘: {char.str}  민첩: {char.dex}  체력: {char.con}  "
        f"지능: {char.intel}  지혜: {char.wis}  매력: {char.cha}"
    )

    # Hitroll / Damroll
    lines.append(f"히트롤: {char.hitroll}  댐롤: {char.damroll}")

    # Rank line
    rank_line = f"당신은 레벨 {char.level} {cls_name} {char.name}"
    if title:
        rank_line += f" {title}"
    rank_line += "입니다."
    lines.append(rank_line)

    # Position
    if char.position == 7 and char.fighting:
        lines.append(f"현재 {char.fighting.name}과(와) 전투 중입니다!")
    else:
        pos_msg = _POS_NAMES.get(char.position, "서 있습니다")
        lines.append(f"현재 {pos_msg}.")

    # Active affects
    affect_names = []
    for aff in char.affects:
        name = aff.get("name", aff.get("spell", ""))
        if name:
            dur = aff.get("duration", 0)
            affect_names.append(f"{name}({dur})")
    if affect_names:
        lines.append(f"활성 효과: {', '.join(affect_names)}")

    await session.send_line("\r\n".join(lines))


async def do_who(session: Session, args: str) -> None:
    """tbaMUD original do_who format — Immortals/Mortals split.

    Based on act.informative.c ACMD(do_who).
    """
    from games.tbamud.level import CLASS_NAMES

    engine = session.engine

    immortals = []
    mortals = []

    for name, s in engine.players.items():
        if not s.character:
            continue
        c = s.character
        cls_id = s.player_data.get("class_id", 0)
        cls_name = CLASS_NAMES.get(cls_id, "모험")[:3]
        lvl = s.player_data.get("level", 1)
        title = s.player_data.get("title", "")
        display = f"[{lvl:3d} {cls_name:3s}] {c.name}"
        if title:
            display += f" {title}"
        # Flags
        flags = []
        if c.position == 8:
            pass
        elif c.position == 4:
            flags.append("잠듦")
        elif c.position == 5:
            flags.append("휴식")
        elif c.position == 7:
            flags.append("전투")
        if flags:
            display += f" ({', '.join(flags)})"

        if lvl >= 31:
            immortals.append(display)
        else:
            mortals.append(display)

    lines = []
    if immortals:
        lines.append("{yellow}신들{reset}")
        lines.append("{yellow}────{reset}")
        lines.extend(f"  {{yellow}}{im}{{reset}}" for im in immortals)
        lines.append("")

    if mortals:
        lines.append("모험가들")
        lines.append("────────")
        lines.extend(f"  {m}" for m in mortals)
        lines.append("")

    total = len(immortals) + len(mortals)
    lines.append(f"{total}명의 모험가가 접속 중입니다.")

    await session.send_line("\r\n".join(lines))


async def do_inventory(session: Session, args: str) -> None:
    """tbaMUD original do_inventory — grouped items with count.

    Based on act.informative.c ACMD(do_inventory).
    """
    char = session.character
    if not char:
        return

    await session.send_line("소지품:")
    if not char.inventory:
        await session.send_line("  아무것도 없습니다.")
        return

    # Group by short_description
    counts: Counter[str] = Counter()
    name_map: dict[str, str] = {}
    for obj in char.inventory:
        desc = obj.proto.short_desc
        counts[desc] += 1
        if desc not in name_map:
            mods = _obj_modifiers(obj)
            name_map[desc] = f"{desc} {mods}".rstrip() if mods else desc

    for desc, count in counts.items():
        display = name_map[desc]
        if count > 1:
            await session.send_line(f"  ({count}) {display}")
        else:
            await session.send_line(f"  {display}")


async def do_equipment(session: Session, args: str) -> None:
    """tbaMUD original do_equipment — wear_where labels + 18 slots.

    Based on act.informative.c ACMD(do_equipment).
    """
    char = session.character
    if not char:
        return

    await session.send_line("착용 장비:")
    found = False
    for pos in range(len(_WEAR_WHERE)):
        obj = char.equipment.get(pos)
        if obj:
            mods = _obj_modifiers(obj)
            name = obj.proto.short_desc
            if mods:
                name = f"{name} {mods}"
            await session.send_line(f"  {_WEAR_WHERE[pos]}{name}")
            found = True

    if not found:
        await session.send_line("  아무것도 착용하고 있지 않습니다.")


async def do_exits(session: Session, args: str) -> None:
    """tbaMUD original do_exits — direction labels with room names.

    Based on act.informative.c ACMD(do_exits).
    """
    from core.engine import DIR_NAMES_KR

    char = session.character
    if not char:
        return
    room = session.engine.world.get_room(char.room_vnum)
    if not room:
        return

    lines = ["확인 가능한 출구:"]
    found = False
    for ex in room.proto.exits:
        if ex.direction >= 6:
            continue
        dir_name = DIR_NAMES_KR[ex.direction]
        if room.has_door(ex.direction):
            if room.is_door_closed(ex.direction):
                kw = ex.keywords.strip() if ex.keywords else "문"
                lines.append(f"  {dir_name:4s} - {kw}이(가) 닫혀 있습니다.")
                found = True
                continue

        dest = session.engine.world.get_room(ex.to_room)
        dest_name = dest.name if dest else "알 수 없음"
        lines.append(f"  {dir_name:4s} - {dest_name}")
        found = True

    if not found:
        lines.append("  없습니다.")

    await session.send_line("\r\n".join(lines))
