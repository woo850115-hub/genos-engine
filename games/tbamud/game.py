"""tbaMUD-KR Game Plugin — command registration and game-specific setup."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine


class TbaMudPlugin:
    """tbaMUD-KR game plugin."""

    name = "tbamud"

    def welcome_banner(self) -> str:
        """Return original tbaMUD greetings screen."""
        banner_file = Path(__file__).resolve().parent.parent.parent / "data" / "tbamud" / "banner.txt"
        try:
            return banner_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return (
                "\r\n{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n"
                "   {bold}{yellow}GenOS tbaMUD-KR{reset}\r\n"
                "   한국어 머드 게임 서버\r\n"
                "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n\r\n"
            )

    def register_commands(self, engine: Engine) -> None:
        """All tbaMUD commands are now provided by Lua scripts.

        Lua scripts in games/tbamud/lua/commands/ are loaded by the engine's
        Lua runtime after this method is called, overriding common commands
        with tbaMUD-specific implementations.
        """
        pass


    async def handle_death(self, engine: Engine, victim: Any, killer: Any = None) -> None:
        """Delegate to tbaMUD death handler (called by deferred death)."""
        from games.tbamud.combat.death import handle_death
        from games.tbamud.level import check_level_up, do_level_up
        await handle_death(engine, victim, killer=killer)
        if killer and not killer.is_npc and check_level_up(killer):
            send_fn = killer.session.send_line if killer.session else None
            await do_level_up(killer, send_fn=send_fn)

    def playing_prompt(self, session: Any) -> str:
        """tbaMUD-style prompt: < 20hp 100mn 82mv >"""
        c = session.character
        return (
            f"\n< {{green}}{c.hp}{{reset}}/{{green}}{c.max_hp}hp{{reset}} "
            f"{{cyan}}{c.mana}{{reset}}/{{cyan}}{c.max_mana}mn{{reset}} "
            f"{{yellow}}{c.move}{{reset}}/{{yellow}}{c.max_move}mv{{reset}} > "
        )


def create_plugin() -> TbaMudPlugin:
    return TbaMudPlugin()
