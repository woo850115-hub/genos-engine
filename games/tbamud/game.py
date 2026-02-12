"""tbaMUD-KR Game Plugin — minimal plugin protocol only.

All game commands are implemented in Lua scripts (games/tbamud/lua/).
This file only contains plugin protocol methods required by the engine.
"""

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
        """All commands are registered via Lua scripts — nothing to do here."""
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
        """tbaMUD-style prompt with custom format support."""
        c = session.character
        custom_fmt = session.player_data.get("prompt", "") if session.player_data else ""
        if custom_fmt:
            result = custom_fmt
            result = result.replace("%h", str(c.hp)).replace("%H", str(c.max_hp))
            result = result.replace("%m", str(c.mana)).replace("%M", str(c.max_mana))
            result = result.replace("%v", str(c.move)).replace("%V", str(c.max_move))
            result = result.replace("%g", str(c.gold))
            result = result.replace("%x", str(c.experience))
            return f"\n{result}"
        base = (
            f"\n< {{green}}{c.hp}{{reset}}/{{green}}{c.max_hp}hp{{reset}} "
            f"{{cyan}}{c.mana}{{reset}}/{{cyan}}{c.max_mana}mn{{reset}} "
            f"{{yellow}}{c.move}{{reset}}/{{yellow}}{c.max_move}mv{{reset}} > "
        )
        # Combat prompt: show enemy condition
        if c.fighting and c.fighting.hp > 0:
            enemy = c.fighting
            ratio = enemy.hp / max(1, enemy.max_hp)
            if ratio >= 0.75:
                condition = "{green}양호{reset}"
            elif ratio >= 0.50:
                condition = "{yellow}부상{reset}"
            elif ratio >= 0.25:
                condition = "{red}심각{reset}"
            else:
                condition = "{bright_red}빈사{reset}"
            base += f"\n[{enemy.name}: {condition}] "
        return base


def create_plugin() -> TbaMudPlugin:
    return TbaMudPlugin()
