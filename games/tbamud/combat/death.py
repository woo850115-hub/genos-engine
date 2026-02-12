"""Death and respawn system."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine import Engine
    from core.world import MobInstance, ObjInstance, World


def _make_corpse(victim: MobInstance, world: Any = None) -> ObjInstance:
    """Create a corpse container object holding victim's belongings."""
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
    corpse = ObjInstance(
        id=_next_id(), proto=proto, values=dict(proto.values),
    )

    # Transfer inventory + equipment into corpse
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


# need Any for type hint in _make_corpse
from typing import Any


async def handle_death(engine: Engine, victim: MobInstance,
                       killer: MobInstance | None = None) -> None:
    """Handle character death — drop corpse, award exp, respawn player."""
    world = engine.world
    room = world.get_room(victim.room_vnum)

    # Stop combat
    if victim.fighting:
        victim.fighting.fighting = None
        victim.fighting = None

    # Create corpse container with victim's belongings
    corpse = _make_corpse(victim)

    # Place corpse in room
    if room:
        corpse.room_vnum = victim.room_vnum
        room.objects.append(corpse)

    # Gold drop
    if victim.gold > 0 and room:
        # Gold goes to room floor (simplified: just transfers to killer)
        if killer and not killer.is_npc:
            killer.gold += victim.gold
            if killer.session:
                await killer.session.send_line(
                    f"{{bright_yellow}}{victim.gold} 골드를 획득합니다.{{reset}}"
                )
        victim.gold = 0

    if victim.is_npc:
        # Award experience to killer
        if killer:
            exp_gain = calculate_exp_gain(killer, victim)
            if not killer.is_npc:
                killer.experience += exp_gain
                if killer.session:
                    await killer.session.send_line(
                        f"{{bright_cyan}}{exp_gain} 경험치를 획득합니다.{{reset}}"
                    )

        # Remove NPC from room
        if room:
            if victim in room.characters:
                room.characters.remove(victim)

        # Notify room
        if room:
            for ch in room.characters:
                if ch.session and ch is not killer:
                    await ch.session.send_line(
                        f"{{red}}{victim.name}이(가) 쓰러집니다.{{reset}}"
                    )

        # Auto-loot: if killer has autoloot toggle, take items from corpse
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
            if toggles.get("autogold") and victim.gold > 0 and not toggles.get("autoloot"):
                # autogold already handled above if killer got gold
                pass
    else:
        # Player death
        if victim.session:
            await victim.session.send_line(
                "\r\n{bright_red}당신은 죽었습니다!{reset}\r\n"
            )
            # Exp penalty (10% of needed for next level)
            from games.tbamud.level import exp_for_level
            penalty = exp_for_level(victim.class_id, victim.level + 1) // 10
            victim.experience = max(0, victim.experience - penalty)
            await victim.session.send_line(
                f"{{red}}{penalty} 경험치를 잃었습니다.{{reset}}"
            )

        # Respawn at start room
        start_room = engine.config.get("world", {}).get("start_room", 3001)
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
    """Calculate experience gained from killing a mob."""
    base = victim.proto.experience if victim.proto else 0
    if base <= 0:
        # Fallback: level-based calculation
        base = victim.level * victim.level * 10

    # Level difference modifier
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
        modifier = 0.1  # Much lower level mob → minimal exp

    return max(1, int(base * modifier))
