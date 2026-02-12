"""검제3의 검눈 (3eyes) Game Plugin — Mordor 2.0 binary C struct MUD."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine


class ThreeEyesPlugin:
    """3eyes game plugin."""

    name = "3eyes"

    def welcome_banner(self) -> str:
        return (
            "\r\n{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n"
            "   {bold}{yellow}검제3의 검눈 (3eyes){reset}\r\n"
            "   Mordor 2.0 머드\r\n"
            "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n\r\n"
        )

    def register_commands(self, engine: Engine) -> None:
        pass

    async def handle_death(self, engine: Engine, victim: Any, killer: Any = None) -> None:
        """Basic death handler — transfer to start room, restore HP."""
        world = engine.world
        start_vnum = engine.config.get("world", {}).get("start_room", 1)
        start_room = world.rooms.get(start_vnum)
        if start_room and victim.room:
            victim.room.characters.discard(victim)
            start_room.characters.add(victim)
            victim.room = start_room
        victim.hp = max(1, victim.max_hp // 2)
        if victim.session:
            await victim.session.send_line("{red}당신은 죽었습니다!{reset}\r\n")

    def playing_prompt(self, session: Any) -> str:
        c = session.character
        return (
            f"\n< {{green}}{c.hp}{{reset}}/{{green}}{c.max_hp}hp{{reset}} "
            f"{{cyan}}{c.mana}{{reset}}/{{cyan}}{c.max_mana}mn{{reset}} "
            f"{{yellow}}{c.move}{{reset}}/{{yellow}}{c.max_move}mv{{reset}} > "
        )


def create_plugin() -> ThreeEyesPlugin:
    return ThreeEyesPlugin()
