"""10woongi (십웅기) Game Plugin — LP-MUD/FluffOS wuxia game."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine

# 10woongi는 숫자 시작 패키지명이므로 정적 import 불가 → importlib 사용
_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


class WoongiPlugin:
    """10woongi game plugin."""

    name = "10woongi"

    def register_commands(self, engine: Engine) -> None:
        """No-op — all commands now provided by Lua scripts."""
        pass

    def get_initial_state(self) -> Any:
        """Return 10woongi-specific login initial state."""
        login = _import("login")
        return login.WoongiGetNameState()

    def welcome_banner(self) -> str:
        """Return original 10woongi getLogo() ASCII art banner."""
        banner_file = Path(__file__).resolve().parent.parent.parent / "data" / "10woongi" / "banner.txt"
        try:
            return "\r\n" + banner_file.read_text(encoding="utf-8") + "\r\n"
        except FileNotFoundError:
            return (
                "\r\n{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n"
                "   {bold}{yellow}십웅기 (10woongi){reset}\r\n"
                "   무협 머드 게임 서버\r\n"
                "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n\r\n"
            )

    def playing_prompt(self, session: Any) -> str:
        """10woongi wuxia-style prompt: < 체력:20/20 내력:80/80 이동:50/50 >"""
        c = session.character
        # 10woongi: move=SP(내력), mana=MP(이동력)
        return (
            f"\n< {{red}}체력:{c.hp}/{c.max_hp}{{reset}} "
            f"{{cyan}}내력:{c.move}/{c.max_move}{{reset}} "
            f"{{yellow}}이동:{c.mana}/{c.max_mana}{{reset}} > "
        )

    async def handle_death(self, engine: Engine, victim: Any, killer: Any = None) -> None:
        """Delegate to 10woongi death handler (called by deferred death)."""
        death = _import("combat.death")
        await death.handle_death(engine, victim, killer=killer)
        # Level up check for killer
        if killer and not killer.is_npc:
            level_mod = _import("level")
            if level_mod.check_level_up(killer):
                send_fn = killer.session.send_line if killer.session else None
                await level_mod.do_level_up(killer, send_fn=send_fn)

    async def tick_affects(self, engine: Engine) -> None:
        """Tick healing for all characters — HP 8%, SP 9%, MP 13%."""
        constants = _import("constants")

        for room in engine.world.rooms.values():
            for char in list(room.characters):
                # HP healing
                if char.hp < char.max_hp:
                    heal_hp = max(1, int(char.max_hp * constants.HEAL_RATE_HP))
                    char.hp = min(char.max_hp, char.hp + heal_hp)

                # SP healing (move = SP)
                max_sp = getattr(char, "max_move", 0)
                current_sp = getattr(char, "move", 0)
                if current_sp < max_sp:
                    heal_sp = max(1, int(max_sp * constants.HEAL_RATE_SP))
                    char.move = min(max_sp, current_sp + heal_sp)

                # MP healing (mana = MP)
                if char.mana < char.max_mana:
                    heal_mp = max(1, int(char.max_mana * constants.HEAL_RATE_MP))
                    char.mana = min(char.max_mana, char.mana + heal_mp)


def create_plugin() -> WoongiPlugin:
    return WoongiPlugin()
