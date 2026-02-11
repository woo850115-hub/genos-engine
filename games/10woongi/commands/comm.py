"""10woongi communication commands — tell, shout, whisper."""

from __future__ import annotations

from typing import Any


def register(engine: Any) -> None:
    engine.register_command("tell", do_tell, korean="귓")
    engine.register_command("shout", do_shout, korean="외치")
    engine.register_command("whisper", do_whisper, korean="속삭이")


async def do_tell(session: Any, args: str) -> None:
    if not args:
        await session.send_line("누구에게 무엇을 말하시겠습니까?")
        return
    parts = args.split(None, 1)
    if len(parts) < 2:
        await session.send_line("무엇을 말하시겠습니까?")
        return
    target_name, message = parts
    target_session = session.engine.players.get(target_name.lower())
    if not target_session:
        await session.send_line("그런 사람을 찾을 수 없습니다.")
        return
    char = session.character
    await session.send_line(
        f"{{magenta}}{target_name}에게 귓속말: '{message}'{{reset}}"
    )
    await target_session.send_line(
        f"\r\n{{magenta}}{char.name}이(가) 귓속말합니다: '{message}'{{reset}}"
    )


async def do_shout(session: Any, args: str) -> None:
    if not args:
        await session.send_line("무엇을 외치시겠습니까?")
        return
    char = session.character
    await session.send_line(f"{{yellow}}당신이 외칩니다: '{args}'{{reset}}")
    for name, s in session.engine.players.items():
        if s is not session and s.character:
            await s.send_line(
                f"\r\n{{yellow}}{char.name}이(가) 외칩니다: '{args}'{{reset}}"
            )


async def do_whisper(session: Any, args: str) -> None:
    if not args:
        await session.send_line("누구에게 무엇을 속삭이시겠습니까?")
        return
    parts = args.split(None, 1)
    if len(parts) < 2:
        await session.send_line("무엇을 속삭이시겠습니까?")
        return
    target_name, message = parts
    char = session.character
    room = session.engine.world.get_room(char.room_vnum) if char else None
    if not room:
        return
    for mob in room.characters:
        if mob is char:
            continue
        name_match = (
            mob.player_name and target_name.lower() in mob.player_name.lower()
        ) or (target_name.lower() in mob.proto.keywords.lower())
        if name_match and mob.session:
            await session.send_line(
                f"{{magenta}}{mob.name}에게 속삭입니다: '{message}'{{reset}}"
            )
            await mob.session.send_line(
                f"\r\n{{magenta}}{char.name}이(가) 속삭입니다: '{message}'{{reset}}"
            )
            return
    await session.send_line("그런 사람을 찾을 수 없습니다.")
