"""10woongi movement commands — directions + dir36 (밖) + recall."""

from __future__ import annotations

import importlib
from typing import Any

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


def register(engine: Any) -> None:
    engine.register_command("recall", do_recall, korean="귀환")


async def do_recall(session: Any, args: str) -> None:
    """Teleport to start room (귀환)."""
    char = session.character
    if not char:
        return
    if char.fighting:
        await session.send_line("전투 중에는 귀환할 수 없습니다!")
        return

    constants = _import("constants")
    start_room = session.config.get("world", {}).get("start_room", constants.START_ROOM)

    engine = session.engine
    room = engine.world.get_room(char.room_vnum)

    # Leave message
    if room:
        for other in room.characters:
            if other is not char and other.session:
                await other.session.send_line(
                    f"\r\n{char.name}이(가) 사라졌습니다."
                )

    engine.world.char_to_room(char, start_room)
    await session.send_line("{bright_white}몸이 가벼워지며 순간이동합니다!{reset}")
    await engine.do_look(session, "")
