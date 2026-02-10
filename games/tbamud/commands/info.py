"""Information commands — time, weather, consider, examine, etc."""

from __future__ import annotations

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
    zone = room.proto.zone_number

    if not args:
        # Show all players in same zone
        lines = ["{bright_cyan}-- 주변 플레이어 --{reset}"]
        found = False
        for rm in session.engine.world.rooms.values():
            if rm.proto.zone_number != zone:
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
            if rm.proto.zone_number != zone:
                continue
            for ch in rm.characters:
                if target_kw in ch.proto.keywords.lower() or (ch.player_name and target_kw in ch.player_name.lower()):
                    lines.append(f"  {ch.name} — {rm.proto.name}")
                    found = True
        if not found:
            lines.append("  찾을 수 없습니다.")
        await session.send_line("\r\n".join(lines))
