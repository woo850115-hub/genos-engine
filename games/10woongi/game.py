"""10woongi (십웅기) Game Plugin — LP-MUD/FluffOS wuxia game."""

from __future__ import annotations

import importlib
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
        """Register 10woongi-specific commands."""
        _import("commands.info").register(engine)
        _import("commands.comm").register(engine)
        _import("commands.items").register(engine)
        _import("commands.movement").register(engine)
        _import("commands.admin").register(engine)

    def get_initial_state(self) -> Any:
        """Return 10woongi-specific login initial state."""
        login = _import("login")
        return login.WoongiGetNameState()

    def welcome_banner(self) -> str:
        """Return 10woongi welcome banner."""
        return (
            "\r\n{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n"
            "   {bold}{yellow}십웅기 (10woongi){reset}\r\n"
            "   무협 머드 게임 서버\r\n"
            "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n\r\n"
        )

    async def combat_round(self, engine: Engine) -> None:
        """Process one sigma-based combat round (1 second)."""
        sigma = _import("combat.sigma")
        death = _import("combat.death")

        processed: set[int] = set()
        for room in engine.world.rooms.values():
            for char in list(room.characters):
                if char.id in processed or not char.fighting:
                    continue
                if char.position < engine.POS_FIGHTING:
                    char.fighting = None
                    continue
                if char.fighting.hp <= 0:
                    char.fighting = None
                    continue

                processed.add(char.id)
                char.position = engine.POS_FIGHTING
                target = char.fighting

                await sigma.perform_attack(
                    char, target,
                    send_to_char=engine._send_to_char,
                )

                if target.hp <= 0:
                    char.fighting = None
                    char.position = engine.POS_STANDING
                    await death.handle_death(engine, target, killer=char)

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
