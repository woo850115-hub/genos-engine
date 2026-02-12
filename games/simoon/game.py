"""시문 (Simoon) Game Plugin — CircleMUD 3.0 Korean custom."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine


class SimoonPlugin:
    """Simoon game plugin."""

    name = "simoon"

    def welcome_banner(self) -> str:
        return (
            "\r\n{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n"
            "   {bold}{yellow}시문 (Simoon){reset}\r\n"
            "   CircleMUD 3.0 한국어 머드\r\n"
            "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n\r\n"
        )

    def register_commands(self, engine: Engine) -> None:
        pass

    async def handle_death(self, engine: Engine, victim: Any, killer: Any = None) -> None:
        """Basic death handler — transfer to void room, restore HP."""
        world = engine.world
        void_vnum = engine.config.get("world", {}).get("void_room", 0)
        void_room = world.rooms.get(void_vnum)
        if void_room and victim.room:
            victim.room.characters.discard(victim)
            void_room.characters.add(victim)
            victim.room = void_room
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


def create_plugin() -> SimoonPlugin:
    return SimoonPlugin()
