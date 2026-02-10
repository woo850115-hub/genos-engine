"""Communication commands — tell, shout, whisper, etc."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine import Engine
    from core.session import Session


def register(engine: Engine) -> None:
    engine.register_command("tell", do_tell, korean="귓말")
    engine.register_command("shout", do_shout, korean="외쳐")
    engine.register_command("whisper", do_whisper, korean="속삭여")


async def do_tell(session: Session, args: str) -> None:
    if not args:
        await session.send_line("누구에게 무엇을 말하시겠습니까?")
        return
    parts = args.split(None, 1)
    if len(parts) < 2:
        await session.send_line("무엇이라고 말하시겠습니까?")
        return
    target_name, message = parts
    target = session.engine.players.get(target_name.lower())
    if not target:
        await session.send_line(f"{target_name}은(는) 접속 중이 아닙니다.")
        return
    char = session.character
    if not char:
        return
    await session.send_line(f"{{magenta}}{target_name}에게 귓속말합니다, '{message}'{{reset}}")
    await target.send_line(f"\r\n{{magenta}}{char.name}이(가) 귓속말합니다, '{message}'{{reset}}")


async def do_shout(session: Session, args: str) -> None:
    if not args:
        await session.send_line("무엇을 외치시겠습니까?")
        return
    char = session.character
    if not char:
        return
    await session.send_line(f"{{yellow}}당신이 외칩니다, '{args}'{{reset}}")
    for name, s in session.engine.players.items():
        if s is not session and s.character:
            await s.send_line(f"\r\n{{yellow}}{char.name}이(가) 외칩니다, '{args}'{{reset}}")


async def do_whisper(session: Session, args: str) -> None:
    await do_tell(session, args)
