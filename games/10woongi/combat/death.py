"""10woongi death handling — void room respawn, experience, corpse."""

from __future__ import annotations

import importlib
from typing import Any

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


async def handle_death(engine: Any, victim: Any, killer: Any | None = None) -> None:
    """Handle character death.

    NPC death: award exp to killer, create corpse.
    PC death: teleport to void room (대기실), restore partial HP.
    """
    constants = _import("constants")
    stats = _import("stats")

    world = engine.world

    if victim.is_npc:
        # NPC death — award exp
        exp = stats.calc_adj_exp(victim.level)

        if killer and not killer.is_npc:
            killer.experience += exp
            killer.gold += victim.gold
            if killer.session:
                await killer.session.send_line(
                    f"{{bright_yellow}}경험치 {exp}을(를) 획득했습니다.{{reset}}"
                )
                if victim.gold > 0:
                    await killer.session.send_line(
                        f"{{yellow}}{victim.gold} 골드를 획득했습니다.{{reset}}"
                    )

        # Remove NPC from room
        room = world.get_room(victim.room_vnum)
        if room and victim in room.characters:
            room.characters.remove(victim)

        # Notify room
        if room:
            for ch in room.characters:
                if ch.session:
                    await ch.session.send_line(
                        f"\r\n{{red}}{victim.name}이(가) 쓰러졌습니다!{{reset}}"
                    )
    else:
        # PC death — teleport to void room
        void_room = engine.config.get("world", {}).get("void_room", constants.VOID_ROOM)

        # Notify death
        if victim.session:
            await victim.session.send_line("{red}당신은 사망했습니다!{reset}")
            await victim.session.send_line("잠시 후 대기실에서 깨어납니다...")

        # Remove from current room
        world.char_from_room(victim)

        # Restore partial HP
        victim.hp = max(1, victim.max_hp // 4)
        victim.move = max(1, getattr(victim, "max_move", 80) // 4)  # SP

        # Clear combat state
        victim.fighting = None
        victim.position = 8  # POS_STANDING

        # Place in void room
        world.char_to_room(victim, void_room)

        if victim.session:
            await victim.session.send_line("\r\n대기실에서 깨어났습니다.")
            await engine.do_look(victim.session, "")
