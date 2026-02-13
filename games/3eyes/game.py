"""검제3의 검눈 (3eyes) Game Plugin — Mordor 2.0 binary C struct MUD.

All game commands are implemented in Lua scripts (games/3eyes/lua/).
This file only contains plugin protocol methods required by the engine.
"""

from __future__ import annotations

import importlib
import random
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

    async def on_tick(self, engine: Engine) -> None:
        """3eyes per-tick hook — corpse decay."""
        death = _import("combat.death")
        await death.decay_corpses(engine)

    async def mobile_activity(self, engine: Engine) -> None:
        """3eyes NPC AI — MAGGRE auto-aggro with lowest-piety targeting.

        From source: update.c update_crt() — MAGGRE attacks lowest-piety player,
        DEX check: target.dex > mob.dex → 30% skip.
        """
        c = _import("constants")
        for room in list(engine.world.rooms.values()):
            for mob in list(room.characters):
                if not mob.is_npc or mob.fighting:
                    continue
                flags = mob.proto.act_flags
                # Check MAGGRE flag (numeric 0 or text "aggressive"/"flag_0")
                is_aggr = (
                    "aggressive" in flags
                    or "flag_0" in flags
                    or 0 in flags
                    or "0" in flags
                )
                if not is_aggr:
                    continue
                # Find lowest-level player in room (proxy for lowest piety)
                victims = [ch for ch in room.characters if not ch.is_npc and ch.hp > 0]
                if not victims:
                    continue
                target = min(victims, key=lambda v: v.level)
                # DEX check: if target.dex > mob.dex → 30% skip (update.c:941)
                tgt_dex = target.stats.get("dex", 13) if target.stats else 13
                mob_dex = mob.stats.get("dex", 13) if mob.stats else 13
                if tgt_dex > mob_dex and random.randint(1, 10) < 4:
                    continue
                # Start combat
                if target.session:
                    await target.session.send_line(
                        f"\r\n{{bright_white}}{mob.name}이(가) 갑자기 당신에게 공격을 해옵니다{{reset}}"
                    )
                for other in room.characters:
                    if other is not target and other.session:
                        await other.session.send_line(
                            f"\r\n{mob.name}이(가) {target.name}에게 공격을 시작합니다."
                        )
                mob.fighting = target
                mob.position = 7  # POS_FIGHTING
                if not target.fighting:
                    target.fighting = mob
                    target.position = 7

    async def room_tick_effects(self, engine: Engine) -> None:
        """3eyes room tick effects — RHEALR/RPHARM/RPPOIS/RPMPDR.

        From source: update.c update_room() — per-tick room flag effects.
        """
        c = _import("constants")
        for room in list(engine.world.rooms.values()):
            if not room.characters:
                continue
            flags = room.flags if room.flags else []
            has_heal = (
                "flag_5" in flags or c.RHEALR in flags
                or "healing" in flags or "heal" in flags
            )
            has_harm = (
                "flag_19" in flags or c.RPHARM in flags or "harmful" in flags
            )
            has_poison = (
                "flag_20" in flags or c.RPPOIS in flags or "poison" in flags
            )
            has_mpdrain = (
                "flag_21" in flags or c.RPMPDR in flags or "mpdrain" in flags
            )
            if not (has_heal or has_harm or has_poison or has_mpdrain):
                continue
            for ch in list(room.characters):
                if ch.is_npc or ch.hp <= 0:
                    continue
                if has_heal:
                    heal = random.randint(5, 15)
                    ch.hp = min(ch.max_hp, ch.hp + heal)
                    ch.mana = min(ch.max_mana, ch.mana + max(1, heal // 2))
                if has_harm:
                    dmg = random.randint(3, 10)
                    ch.hp = max(1, ch.hp - dmg)
                    if ch.session:
                        await ch.session.send_line(
                            "\r\n{red}이 방의 유독한 기운이 당신을 해칩니다! "
                            f"(-{dmg} HP){{reset}}"
                        )
                if has_poison and not ch.fighting:
                    # 20% chance to poison per tick
                    if random.randint(1, 5) == 1:
                        pf = ch.flags if hasattr(ch, "flags") and ch.flags else []
                        already = (c.PPOISN in pf or "flag_12" in pf)
                        if not already and ch.session:
                            if hasattr(ch, "flags") and isinstance(ch.flags, list):
                                ch.flags.append(c.PPOISN)
                            await ch.session.send_line(
                                "\r\n{green}이 방의 독기에 중독되었습니다!{reset}"
                            )
                if has_mpdrain:
                    drain = random.randint(5, 15)
                    ch.mana = max(0, ch.mana - drain)
                    if ch.session:
                        await ch.session.send_line(
                            f"\r\n{{yellow}}이 방의 기운이 마력을 흡수합니다! (-{drain} MP){{reset}}"
                        )

    def regen_char(self, engine: Any, char: Any) -> None:
        """3eyes regen — class-based HP/MP recovery per tick.

        From source: base 5 + CON bonus per 5s tick.
        Barbarian +2 HP, Mage +2 MP.
        RHEALR bonus is handled in room_tick_effects().
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
        # Invincible+ gets base +3 (kyk3.c regen bonus)
        if char.class_id and char.class_id >= c.INVINCIBLE:
            hp_regen += 3
            mp_regen += 2

        char.hp = min(char.max_hp, char.hp + hp_regen)
        char.mana = min(char.max_mana, char.mana + mp_regen)
        char.move = min(char.max_move, char.move + max(1, 3))


def create_plugin() -> ThreeEyesPlugin:
    return ThreeEyesPlugin()
