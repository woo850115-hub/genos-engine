"""시문 (Simoon) Game Plugin — CircleMUD 3.0 Korean custom.

All game commands are implemented in Lua scripts (games/simoon/lua/).
This file only contains plugin protocol methods required by the engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine


class SimoonPlugin:
    """Simoon game plugin."""

    name = "simoon"

    def welcome_banner(self) -> str:
        banner_file = Path(__file__).resolve().parent.parent.parent / "data" / "simoon" / "banner.txt"
        try:
            return banner_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return (
                "\r\n{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n"
                "   {bold}{yellow}시문 (Simoon){reset}\r\n"
                "   CircleMUD 3.0 한국어 머드\r\n"
                "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n\r\n"
            )

    def get_initial_state(self) -> Any:
        from games.simoon.login import SimoonGetNameState
        return SimoonGetNameState()

    def register_commands(self, engine: Engine) -> None:
        """All commands are registered via Lua scripts."""
        pass

    async def handle_death(self, engine: Engine, victim: Any, killer: Any = None) -> None:
        """Simoon death — stat penalty for PvM at level 50+."""
        from games.simoon.combat.death import handle_death
        from games.simoon.level import check_level_up, do_level_up
        await handle_death(engine, victim, killer=killer)
        if killer and not killer.is_npc and check_level_up(killer):
            send_fn = killer.session.send_line if killer.session else None
            await do_level_up(killer, send_fn=send_fn)

    def playing_prompt(self, session: Any) -> str:
        """Simoon-style prompt with combat condition."""
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

    def regen_char(self, engine: Any, char: Any) -> None:
        """Simoon regen — class-based HP/mana recovery per tick."""
        from games.simoon.constants import CASTER_CLASSES
        # Base regen: 8% HP, 8% mana, 8% move
        hp_regen = max(1, char.max_hp * 8 // 100)
        mana_regen = max(1, char.max_mana * 8 // 100)
        move_regen = max(1, char.max_move * 8 // 100)

        # Casters get slightly better mana regen
        if char.class_id in CASTER_CLASSES:
            mana_regen = max(1, char.max_mana * 12 // 100)

        char.hp = min(char.max_hp, char.hp + hp_regen)
        char.mana = min(char.max_mana, char.mana + mana_regen)
        char.move = min(char.max_move, char.move + move_regen)


def create_plugin() -> SimoonPlugin:
    return SimoonPlugin()
