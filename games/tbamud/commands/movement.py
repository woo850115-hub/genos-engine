"""Movement commands — extended door interactions, enter/leave."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine import Engine
    from core.session import Session


def register(engine: Engine) -> None:
    engine.register_command("enter", do_enter, korean="들어가")
    engine.register_command("leave", do_leave, korean="나와")
    engine.register_command("follow", do_follow, korean="따라가")
    engine.register_command("group", do_group, korean="무리")


async def do_enter(session: Session, args: str) -> None:
    if not args:
        await session.send_line("어디로 들어가시겠습니까?")
        return
    await session.send_line("구현 예정입니다.")


async def do_leave(session: Session, args: str) -> None:
    await session.send_line("구현 예정입니다.")


async def do_follow(session: Session, args: str) -> None:
    if not args:
        await session.send_line("누구를 따라가시겠습니까?")
        return
    await session.send_line("구현 예정입니다.")


async def do_group(session: Session, args: str) -> None:
    if not args:
        await session.send_line("파티원이 없습니다.")
        return
    await session.send_line("구현 예정입니다.")
