"""10woongi admin commands — goto, load, purge, stat, set, reload, shutdown."""

from __future__ import annotations

import importlib
from typing import Any

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


# Admin level threshold
ADMIN_LEVEL = 100


def register(engine: Any) -> None:
    engine.register_command("goto", do_goto)
    engine.register_command("wload", do_load)
    engine.register_command("purge", do_purge)
    engine.register_command("stat", do_stat)
    engine.register_command("wset", do_set)
    engine.register_command("restore", do_restore)
    engine.register_command("advance", do_advance)


def _is_admin(session: Any) -> bool:
    return session.player_data.get("level", 1) >= ADMIN_LEVEL


async def do_goto(session: Any, args: str) -> None:
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return
    if not args:
        await session.send_line("어디로 가시겠습니까? (goto <방번호>)")
        return
    try:
        room_vnum = int(args.strip())
    except ValueError:
        await session.send_line("올바른 방 번호를 입력하세요.")
        return

    engine = session.engine
    dest = engine.world.get_room(room_vnum)
    if not dest:
        await session.send_line("그런 방은 없습니다.")
        return

    char = session.character
    engine.world.char_to_room(char, room_vnum)
    await engine.do_look(session, "")


async def do_load(session: Any, args: str) -> None:
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return
    if not args:
        await session.send_line("사용법: wload mob <vnum> / wload obj <vnum>")
        return

    parts = args.strip().split()
    if len(parts) < 2:
        await session.send_line("사용법: wload mob <vnum> / wload obj <vnum>")
        return

    obj_type = parts[0].lower()
    try:
        vnum = int(parts[1])
    except ValueError:
        await session.send_line("올바른 VNUM을 입력하세요.")
        return

    engine = session.engine
    char = session.character

    if obj_type == "mob":
        mob = engine.world.create_mob(vnum, char.room_vnum)
        if mob:
            await session.send_line(f"{mob.name}을(를) 소환했습니다.")
        else:
            await session.send_line(f"VNUM {vnum} 몬스터를 찾을 수 없습니다.")
    elif obj_type == "obj":
        obj = engine.world.create_obj(vnum)
        if obj:
            engine.world.obj_to_room(obj, char.room_vnum)
            await session.send_line(f"{obj.name}을(를) 생성했습니다.")
        else:
            await session.send_line(f"VNUM {vnum} 아이템을 찾을 수 없습니다.")
    else:
        await session.send_line("사용법: wload mob <vnum> / wload obj <vnum>")


async def do_purge(session: Any, args: str) -> None:
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return
    char = session.character
    room = session.engine.world.get_room(char.room_vnum)
    if not room:
        return

    # Remove all NPCs and objects from room
    room.characters = [ch for ch in room.characters if not ch.is_npc]
    room.objects.clear()
    await session.send_line("방이 정화되었습니다.")


async def do_stat(session: Any, args: str) -> None:
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return
    if not args:
        await session.send_line("사용법: stat <대상>")
        return

    char = session.character
    room = session.engine.world.get_room(char.room_vnum)
    if not room:
        return

    target_kw = args.strip().lower()
    for mob in room.characters:
        if mob is char:
            continue
        if target_kw in mob.proto.keywords.lower() or (
            mob.player_name and target_kw in mob.player_name.lower()
        ):
            lines = [
                f"{{cyan}}━━━ {mob.name} 상세 정보 ━━━{{reset}}",
                f"  VNUM: {mob.proto.vnum}  레벨: {mob.level}",
                f"  HP: {mob.hp}/{mob.max_hp}  SP: {mob.move}/{mob.max_move}",
                f"  골드: {mob.gold}  경험치: {mob.experience}",
                f"  히트롤: {mob.hitroll}  댐롤: {mob.damroll}",
                f"  NPC: {mob.is_npc}",
            ]
            await session.send_line("\r\n".join(lines))
            return

    await session.send_line("그런 대상을 찾을 수 없습니다.")


async def do_set(session: Any, args: str) -> None:
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return
    if not args:
        await session.send_line("사용법: wset <이름> <필드> <값>")
        return

    parts = args.strip().split()
    if len(parts) < 3:
        await session.send_line("사용법: wset <이름> <필드> <값>")
        return

    target_name, field, value = parts[0], parts[1], parts[2]
    target_session = session.engine.players.get(target_name.lower())
    if not target_session or not target_session.character:
        await session.send_line("그런 플레이어를 찾을 수 없습니다.")
        return

    char = target_session.character
    try:
        int_val = int(value)
    except ValueError:
        await session.send_line("올바른 숫자를 입력하세요.")
        return

    if field == "level":
        char.player_level = int_val
    elif field == "hp":
        char.hp = int_val
        char.max_hp = int_val
    elif field == "gold":
        char.gold = int_val
    elif field == "exp":
        char.experience = int_val
    else:
        await session.send_line(f"알 수 없는 필드: {field}")
        return

    await session.send_line(f"{target_name}의 {field}을(를) {value}(으)로 설정했습니다.")


async def do_restore(session: Any, args: str) -> None:
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return

    char = session.character
    if args:
        target_session = session.engine.players.get(args.strip().lower())
        if target_session and target_session.character:
            char = target_session.character

    char.hp = char.max_hp
    char.mana = char.max_mana
    char.move = getattr(char, "max_move", 80)
    await session.send_line(f"{char.name}이(가) 완전히 회복되었습니다!")


async def do_advance(session: Any, args: str) -> None:
    """Force level up for testing."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return
    if not args:
        await session.send_line("사용법: advance <이름> <레벨>")
        return

    parts = args.strip().split()
    if len(parts) < 2:
        await session.send_line("사용법: advance <이름> <레벨>")
        return

    target_name = parts[0]
    try:
        target_level = int(parts[1])
    except ValueError:
        await session.send_line("올바른 숫자를 입력하세요.")
        return

    target_session = session.engine.players.get(target_name.lower())
    if not target_session or not target_session.character:
        await session.send_line("그런 플레이어를 찾을 수 없습니다.")
        return

    target_session.character.player_level = target_level
    await session.send_line(
        f"{target_name}을(를) 레벨 {target_level}(으)로 설정했습니다."
    )
