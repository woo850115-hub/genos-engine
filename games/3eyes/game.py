"""검제3의 검눈 (3eyes) Game Plugin — Mordor 2.0 binary C struct MUD.

All game commands are implemented in Lua scripts (games/3eyes/lua/).
This file only contains plugin protocol methods required by the engine.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine

_PKG = "games.3eyes"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


class ThreeEyesPlugin:
    """3eyes game plugin."""

    name = "3eyes"

    def welcome_banner(self) -> str:
        banner_file = Path(__file__).resolve().parent.parent.parent / "data" / "3eyes" / "banner.txt"
        try:
            return banner_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return (
                "\r\n{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n"
                "   {bold}{yellow}검제3의 검눈 (3eyes){reset}\r\n"
                "   Mordor 2.0 머드\r\n"
                "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n\r\n"
            )

    def get_initial_state(self) -> Any:
        login = _import("login")
        return login.ThreeEyesGetNameState()

    def register_commands(self, engine: Engine) -> None:
        """All commands are registered via Lua scripts."""
        pass

    async def handle_death(self, engine: Engine, victim: Any, killer: Any = None) -> None:
        """3eyes death — exp penalty + proficiency gain."""
        death = _import("combat.death")
        level = _import("level")
        await death.handle_death(engine, victim, killer=killer)
        # Check level up for killer
        if killer and not killer.is_npc and level.check_level_up(killer):
            send_fn = killer.session.send_line if killer.session else None
            await level.do_level_up(killer, send_fn=send_fn)

    def playing_prompt(self, session: Any) -> str:
        """3eyes prompt — HP/MP/MV with combat condition."""
        c = session.character
        base = (
            f"\n< {{green}}{c.hp}{{reset}}/{{green}}{c.max_hp}hp{{reset}} "
            f"{{cyan}}{c.mana}{{reset}}/{{cyan}}{c.max_mana}mp{{reset}} "
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

    async def regen_char(self, char: Any) -> None:
        """3eyes regen — class-based HP/MP recovery per tick.

        From source: base 5 + CON bonus per 5s tick.
        Barbarian +2 HP, Mage +2 MP.
        """
        c = _import("constants")
        con = char.stats.get("con", 13) if char.stats else 13
        intel = char.stats.get("int", 13) if char.stats else 13
        con_bonus = c.get_stat_bonus(con)

        hp_regen = max(1, 5 + con_bonus)
        mp_regen = max(1, 5 + (1 if intel > 17 else 0))

        # Barbarian +2 HP
        if char.class_id == 2:
            hp_regen += 2
        # Mage +2 MP
        if char.class_id == 5:
            mp_regen += 2

        char.hp = min(char.max_hp, char.hp + hp_regen)
        char.mana = min(char.max_mana, char.mana + mp_regen)
        char.move = min(char.max_move, char.move + max(1, 3))


def create_plugin() -> ThreeEyesPlugin:
    return ThreeEyesPlugin()
