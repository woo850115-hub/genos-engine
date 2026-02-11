"""10woongi info commands — score (6 wuxia stats), consider, examine."""

from __future__ import annotations

import importlib
from typing import Any

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


def register(engine: Any) -> None:
    engine.register_command("wscore", do_wscore, korean="정보")
    engine.register_command("consider", do_consider, korean="판별")
    engine.register_command("equipment", do_equipment, korean="장비")


async def do_wscore(session: Any, args: str) -> None:
    """Show wuxia score with 6 martial stats."""
    constants = _import("constants")
    level_mod = _import("level")

    char = session.character
    if not char:
        return

    cls_name = constants.CLASS_NAMES.get(char.class_id, "무림인")
    sex_name = ["중성", "남성", "여성"][session.player_data.get("sex", 0)]

    ext = getattr(char, "extensions", {}) or {}
    wstats = ext.get("stats", {})

    sp = getattr(char, "move", 0)
    max_sp = getattr(char, "max_move", 0)

    lines = [
        f"{{cyan}}━━━━━━ {char.name}의 정보 ━━━━━━{{reset}}",
        f"  레벨: {char.level}  직업: {cls_name}  성별: {sex_name}",
        f"  HP: {{green}}{char.hp}/{char.max_hp}{{reset}}  "
        f"SP: {{blue}}{sp}/{max_sp}{{reset}}  "
        f"MP: {{magenta}}{char.mana}/{char.max_mana}{{reset}}",
        f"  체력: {wstats.get('stamina', 13)}  민첩: {wstats.get('agility', 13)}  "
        f"지혜: {wstats.get('wisdom', 13)}",
        f"  기골: {wstats.get('bone', 13)}  내공: {wstats.get('inner', 13)}  "
        f"투지: {wstats.get('spirit', 13)}",
        f"  골드: {{yellow}}{char.gold}{{reset}}  경험치: {char.experience}",
        f"  다음 레벨까지: {level_mod.exp_to_next(char)}",
        f"{{cyan}}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{{reset}}",
    ]
    await session.send_line("\r\n".join(lines))


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


async def do_equipment(session: Any, args: str) -> None:
    """Show equipped items in 22 slots."""
    constants = _import("constants")
    char = session.character
    if not char:
        return

    await session.send_line("{cyan}━━━━━━ 착용 장비 ━━━━━━{reset}")
    for slot_id, slot_name in constants.WEAR_SLOTS.items():
        obj = char.equipment.get(slot_id)
        if obj:
            await session.send_line(f"  <{slot_name}> {obj.name}")
        else:
            await session.send_line(f"  <{slot_name}> (없음)")
    await session.send_line("{cyan}━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
