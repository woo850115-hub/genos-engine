"""Admin commands — goto, load, purge, set, stat, reload, shutdown."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine import Engine
    from core.session import Session

MIN_ADMIN_LEVEL = 31


def register(engine: Engine) -> None:
    engine.register_command("goto", do_goto)
    engine.register_command("load", do_load)
    engine.register_command("purge", do_purge)
    engine.register_command("stat", do_stat)
    engine.register_command("set", do_set)
    engine.register_command("reload", do_reload)
    engine.register_command("shutdown", do_shutdown)
    engine.register_command("advance", do_advance)
    engine.register_command("restore", do_restore)


def _is_admin(session) -> bool:
    char = session.character
    if not char:
        return False
    return char.level >= MIN_ADMIN_LEVEL


async def do_goto(session, args: str) -> None:
    """Teleport to a room."""
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
        await session.send_line("그런 방이 없습니다.")
        return

    char = session.character
    old_room = engine.world.get_room(char.room_vnum)
    if old_room and char in old_room.characters:
        old_room.characters.remove(char)
    char.room_vnum = room_vnum
    dest.characters.append(char)
    await engine.do_look(session, "")


async def do_load(session, args: str) -> None:
    """Load a mob or object: load mob <vnum> / load obj <vnum>."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return

    parts = args.strip().split()
    if len(parts) < 2:
        await session.send_line("사용법: load mob <vnum> / load obj <vnum>")
        return

    load_type = parts[0].lower()
    try:
        vnum = int(parts[1])
    except ValueError:
        await session.send_line("올바른 VNUM을 입력하세요.")
        return

    engine = session.engine
    char = session.character

    if load_type in ("mob", "m"):
        proto = engine.world.mob_protos.get(vnum)
        if not proto:
            await session.send_line(f"몹 #{vnum}이(가) 없습니다.")
            return
        mob = engine.world.create_mob(vnum, char.room_vnum)
        if mob:
            await session.send_line(f"{mob.name}을(를) 소환했습니다.")
    elif load_type in ("obj", "o"):
        obj = engine.world.create_obj(vnum)
        if not obj:
            await session.send_line(f"아이템 #{vnum}이(가) 없습니다.")
            return
        char.inventory.append(obj)
        await session.send_line(f"{obj.name}을(를) 생성했습니다.")
    else:
        await session.send_line("사용법: load mob <vnum> / load obj <vnum>")


async def do_purge(session, args: str) -> None:
    """Remove all NPCs and objects from current room."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return

    engine = session.engine
    char = session.character
    room = engine.world.get_room(char.room_vnum)
    if not room:
        return

    # Remove NPCs
    removed = 0
    room.characters = [ch for ch in room.characters if not ch.is_npc]
    # Remove objects
    removed_obj = len(room.objects)
    room.objects.clear()

    await session.send_line(f"방이 정화되었습니다. (NPC 및 {removed_obj}개 아이템 제거)")


async def do_stat(session, args: str) -> None:
    """Show detailed info about a mob/obj/room."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return

    if not args:
        # Stat current room
        char = session.character
        room = session.engine.world.get_room(char.room_vnum)
        if room:
            lines = [
                f"{{bright_cyan}}[방 정보] #{room.proto.vnum} — {room.proto.name}{{reset}}",
                f"  Zone: {room.proto.zone_vnum}  Sector: {room.proto.sector}",
                f"  Exits: {len(room.proto.exits)}  Characters: {len(room.characters)}",
                f"  Objects: {len(room.objects)}  Triggers: {room.proto.scripts}",
            ]
            await session.send_line("\r\n".join(lines))
        return

    # Stat target
    target_kw = args.strip().lower()
    char = session.character
    room = session.engine.world.get_room(char.room_vnum)
    if not room:
        return

    for mob in room.characters:
        if target_kw in mob.proto.keywords.lower():
            lines = [
                f"{{bright_cyan}}[캐릭터] #{mob.proto.vnum} — {mob.name}{{reset}}",
                f"  Level: {mob.level}  HP: {mob.hp}/{mob.max_hp}  AC: {mob.proto.armor_class}",
                f"  Hitroll: {mob.proto.hitroll}  Damage: {mob.proto.damage_dice}",
                f"  Gold: {mob.gold}  Exp: {mob.proto.experience}",
                f"  Triggers: {mob.proto.scripts}",
            ]
            await session.send_line("\r\n".join(lines))
            return

    await session.send_line("대상을 찾을 수 없습니다.")


async def do_set(session, args: str) -> None:
    """Set character attributes: set <player> <field> <value>."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return

    parts = args.strip().split()
    if len(parts) < 3:
        await session.send_line("사용법: set <이름> <필드> <값>")
        return

    target_name = parts[0].lower()
    field = parts[1].lower()
    value = parts[2]

    # Find target
    engine = session.engine
    target = None
    for room in engine.world.rooms.values():
        for ch in room.characters:
            if ch.player_name and ch.player_name.lower() == target_name:
                target = ch
                break
        if target:
            break

    if not target:
        await session.send_line(f"'{parts[0]}' 플레이어를 찾을 수 없습니다.")
        return

    try:
        if field == "level":
            target.player_level = int(value)
            await session.send_line(f"{target.name}의 레벨을 {value}(으)로 설정했습니다.")
        elif field == "hp":
            target.hp = int(value)
            await session.send_line(f"{target.name}의 HP를 {value}(으)로 설정했습니다.")
        elif field == "gold":
            target.gold = int(value)
            await session.send_line(f"{target.name}의 골드를 {value}(으)로 설정했습니다.")
        elif field == "exp":
            target.experience = int(value)
            await session.send_line(f"{target.name}의 경험치를 {value}(으)로 설정했습니다.")
        else:
            await session.send_line(f"알 수 없는 필드: {field}")
    except ValueError:
        await session.send_line("올바른 값을 입력하세요.")


async def do_advance(session, args: str) -> None:
    """Advance a player to a level."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return
    await session.send_line("advance → set <이름> level <값> 을 사용하세요.")


async def do_restore(session, args: str) -> None:
    """Fully restore a character."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return

    char = session.character
    if args:
        # Find target
        target_name = args.strip().lower()
        for room in session.engine.world.rooms.values():
            for ch in room.characters:
                if ch.player_name and ch.player_name.lower() == target_name:
                    ch.hp = ch.max_hp
                    ch.mana = ch.max_mana
                    ch.move = ch.max_move
                    await session.send_line(f"{ch.name}을(를) 완전히 회복시켰습니다.")
                    if ch.session:
                        await ch.session.send_line("{bright_green}완전히 회복되었습니다!{reset}")
                    return
        await session.send_line("대상을 찾을 수 없습니다.")
    else:
        char.hp = char.max_hp
        char.mana = char.max_mana
        char.move = char.max_move
        await session.send_line("{bright_green}완전히 회복되었습니다!{reset}")


async def do_reload(session, args: str) -> None:
    """Reload game modules."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return

    engine = session.engine
    engine.reload_mgr.queue_game_reload(engine.game_name)
    reloaded = engine.reload_mgr.apply_pending()
    if reloaded:
        engine._plugin.register_commands(engine)
        await session.send_line(f"리로드 완료: {', '.join(reloaded)}")
    else:
        await session.send_line("리로드할 모듈이 없습니다.")


async def do_shutdown(session, args: str) -> None:
    """Shutdown the server."""
    if not _is_admin(session):
        await session.send_line("권한이 없습니다.")
        return
    await session.send_line("{red}서버를 종료합니다...{reset}")
    await session.engine.shutdown()
