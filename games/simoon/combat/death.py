"""Simoon death system — permanent stat penalty for PvM at level 50+."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine
    from core.world import MobInstance

from games.simoon.constants import (
    DEATH_CRYSTAL_LOSS_MAX, DEATH_CRYSTAL_LOSS_MIN,
    DEATH_GOLD_LOSS_MAX, DEATH_GOLD_LOSS_MIN,
    DEATH_PENALTY_MIN_LEVEL, DEATH_PENALTY_MIN_STAT,
    DEATH_STAT_LOSS_MAX, DEATH_STAT_LOSS_MIN,
    MORTAL_START_ROOM,
)


def _make_corpse(victim: MobInstance) -> Any:
    """Create a corpse container holding victim's belongings."""
    from core.world import ItemProto, ObjInstance, _next_id

    corpse_name = f"{victim.name}의 시체"
    proto = ItemProto(
        vnum=-victim.proto.vnum if victim.proto else -1,
        keywords=f"시체 corpse {victim.proto.keywords}",
        short_desc=corpse_name,
        long_desc=f"{corpse_name}가 바닥에 놓여 있습니다.",
        item_type="container",
        weight=50, cost=0, min_level=0,
        wear_slots=[], flags=[], values={"corpse": True, "timer": 5},
        affects=[], extra_descs=[], scripts=[], ext={},
    )
    corpse = ObjInstance(id=_next_id(), proto=proto, values=dict(proto.values))

    for obj in victim.inventory:
        obj.carried_by = None
        obj.in_obj = corpse
        corpse.contains.append(obj)
    for slot, obj in victim.equipment.items():
        obj.worn_by = None
        obj.wear_slot = ""
        obj.in_obj = corpse
        corpse.contains.append(obj)

    victim.inventory.clear()
    victim.equipment.clear()
    return corpse


async def handle_death(engine: Engine, victim: MobInstance,
                       killer: MobInstance | None = None) -> None:
    """Simoon death handler — stat penalty + respawn."""
    world = engine.world
    room = world.get_room(victim.room_vnum)

    # Stop combat
    if victim.fighting:
        victim.fighting.fighting = None
        victim.fighting = None

    # Create corpse
    corpse = _make_corpse(victim)
    if room:
        corpse.room_vnum = victim.room_vnum
        room.objects.append(corpse)

    # Gold transfer to killer
    if victim.gold > 0 and killer and not killer.is_npc:
        killer.gold += victim.gold
        if killer.session:
            await killer.session.send_line(
                f"{{bright_yellow}}{victim.gold} 골드를 획득합니다.{{reset}}"
            )
        victim.gold = 0

    if victim.is_npc:
        # Award exp
        if killer:
            exp_gain = calculate_exp_gain(killer, victim)
            if not killer.is_npc:
                killer.experience += exp_gain
                if killer.session:
                    await killer.session.send_line(
                        f"{{bright_cyan}}{exp_gain} 경험치를 획득합니다.{{reset}}"
                    )

        # Remove NPC
        if room and victim in room.characters:
            room.characters.remove(victim)

        # Notify room
        if room:
            for ch in room.characters:
                if ch.session and ch is not killer:
                    await ch.session.send_line(
                        f"{{red}}{victim.name}이(가) 쓰러집니다.{{reset}}"
                    )

        # Auto-loot
        if killer and not killer.is_npc and killer.session and room:
            toggles = killer.session.player_data.get("toggles", {})
            if toggles.get("autoloot") and corpse.contains:
                picked = list(corpse.contains)
                for obj in picked:
                    corpse.contains.remove(obj)
                    obj.in_obj = None
                    obj.carried_by = killer
                    killer.inventory.append(obj)
                    await killer.session.send_line(
                        f"{{yellow}}{obj.name}을(를) 자동으로 주웠습니다.{{reset}}"
                    )
    else:
        # ── Player death — Simoon unique penalty ──────────
        if victim.session:
            await victim.session.send_line(
                "\r\n{bright_red}당신은 죽었습니다!{reset}\r\n"
            )

            # PvM stat penalty (level 50+)
            if victim.level >= DEATH_PENALTY_MIN_LEVEL and (killer is None or killer.is_npc):
                penalties = []
                if victim.max_hp > DEATH_PENALTY_MIN_STAT:
                    loss = random.randint(DEATH_STAT_LOSS_MIN, DEATH_STAT_LOSS_MAX)
                    victim.max_hp = max(DEATH_PENALTY_MIN_STAT, victim.max_hp - loss)
                    penalties.append(f"최대HP -{loss}")
                if victim.max_mana > DEATH_PENALTY_MIN_STAT:
                    loss = random.randint(DEATH_STAT_LOSS_MIN, DEATH_STAT_LOSS_MAX)
                    victim.max_mana = max(DEATH_PENALTY_MIN_STAT, victim.max_mana - loss)
                    penalties.append(f"최대마나 -{loss}")
                if victim.max_move > DEATH_PENALTY_MIN_STAT:
                    loss = random.randint(DEATH_STAT_LOSS_MIN, DEATH_STAT_LOSS_MAX)
                    victim.max_move = max(DEATH_PENALTY_MIN_STAT, victim.max_move - loss)
                    penalties.append(f"최대이동 -{loss}")

                gold_loss = random.randint(DEATH_GOLD_LOSS_MIN, DEATH_GOLD_LOSS_MAX)
                victim.gold = max(0, victim.gold - gold_loss)
                penalties.append(f"골드 -{gold_loss}")

                # Crystal loss (stored in extensions)
                ext = getattr(victim, "ext", {}) or {}
                crystal = ext.get("crystal", 0)
                if crystal > 0:
                    c_loss = random.randint(DEATH_CRYSTAL_LOSS_MIN, DEATH_CRYSTAL_LOSS_MAX)
                    ext["crystal"] = max(0, crystal - c_loss)
                    penalties.append(f"크리스탈 -{c_loss}")

                if penalties:
                    await victim.session.send_line(
                        "{red}사망 패널티: " + ", ".join(penalties) + "{reset}"
                    )

        # Respawn
        start_room = engine.config.get("world", {}).get("start_room", MORTAL_START_ROOM)
        if room and victim in room.characters:
            room.characters.remove(victim)

        victim.hp = max(1, victim.max_hp // 2)
        victim.mana = max(0, victim.max_mana // 2)
        victim.position = 8  # POS_STANDING
        victim.room_vnum = start_room

        dest = world.get_room(start_room)
        if dest:
            dest.characters.append(victim)
            if victim.session:
                await victim.session.send_line(
                    "\r\n{yellow}정신을 차려보니 신전에 있습니다.{reset}\r\n"
                )
                await engine.do_look(victim.session, "")


def calculate_exp_gain(killer: MobInstance, victim: MobInstance) -> int:
    """Simoon exp gain — same formula as tbaMUD."""
    base = victim.proto.experience if victim.proto else 0
    if base <= 0:
        base = victim.level * victim.level * 10

    diff = victim.level - killer.level
    if diff >= 5:
        modifier = 1.5
    elif diff >= 2:
        modifier = 1.2
    elif diff >= -2:
        modifier = 1.0
    elif diff >= -5:
        modifier = 0.5
    else:
        modifier = 0.1

    return max(1, int(base * modifier))
