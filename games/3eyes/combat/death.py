"""3eyes death system — exp penalty, proficiency gain, PK tracking, corpse decay."""

from __future__ import annotations

import importlib
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine
    from core.world import MobInstance

_PKG = "games.3eyes"


def _const():
    return importlib.import_module(f"{_PKG}.constants")


def _level():
    return importlib.import_module(f"{_PKG}.level")


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


def _add_proficiency(char: MobInstance, exp_gain: int) -> None:
    """Distribute proficiency points from combat exp (add_prof formula).

    From source: exp/20 split equally to 5 weapon + 4 realm types.
    """
    if exp_gain <= 0:
        return
    points = exp_gain // 20
    if points <= 0:
        return

    ext = getattr(char, "extensions", None)
    if ext is None:
        return

    # 5 weapon proficiency types
    prof = ext.get("proficiency", [0, 0, 0, 0, 0])
    if not isinstance(prof, list) or len(prof) < 5:
        prof = [0, 0, 0, 0, 0]
    for i in range(5):
        prof[i] += points
    ext["proficiency"] = prof

    # 4 magic realm types
    realm = ext.get("realm", [0, 0, 0, 0])
    if not isinstance(realm, list) or len(realm) < 4:
        realm = [0, 0, 0, 0]
    for i in range(4):
        realm[i] += points
    ext["realm"] = realm


async def handle_death(engine: Engine, victim: MobInstance,
                       killer: MobInstance | None = None) -> None:
    """3eyes death handler — exp penalty + proficiency gain."""
    c = _const()
    lv = _level()
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
                f"{{bright_yellow}}{victim.gold}원을 획득합니다.{{reset}}"
            )
        victim.gold = 0

    if victim.is_npc:
        # Award exp (contribution-based in original, simplified here)
        if killer:
            exp_gain = calculate_exp_gain(killer, victim)
            if not killer.is_npc:
                killer.experience += exp_gain
                if killer.session:
                    await killer.session.send_line(
                        f"{{bright_cyan}}{victim.name}의 시체로 "
                        f"{exp_gain}만큼의 경험치를 얻었습니다.{{reset}}"
                    )
                # Proficiency gain from combat
                _add_proficiency(killer, exp_gain)

        # Remove NPC from room
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
        # ── Player death ─────────────────────────────────────
        is_pk = killer is not None and not killer.is_npc

        if victim.session:
            await victim.session.send_line(
                "\r\n{bright_red}당신은 죽었습니다!{reset}\r\n"
            )

            # Experience penalty: (current_level_exp - prev_level_exp) * 3/4
            # PK death: half penalty (kyk5.c)
            cur_exp = lv.exp_for_level(victim.level)
            prev_exp = lv.exp_for_level(max(1, victim.level - 1))
            penalty_ratio = 3 if not is_pk else 1  # PvE 3/4, PvP 1/4
            exp_loss = max(0, (cur_exp - prev_exp) * penalty_ratio // 4)
            if exp_loss > 0:
                victim.experience = max(0, victim.experience - exp_loss)
                await victim.session.send_line(
                    f"{{red}}경험치 -{exp_loss}{{reset}}"
                )

        # PK tracking (kyk5.c)
        if is_pk:
            # Killer PK kill count
            if killer.session:
                pd = killer.session.player_data
                pk_kills = pd.get("pk_kills", 0) + 1
                pd["pk_kills"] = pk_kills
                await killer.session.send_line(
                    f"{{bright_red}}PK 킬 카운트: {pk_kills}{{reset}}"
                )
                if pk_kills >= 10:
                    await killer.session.send_line(
                        "{bright_red}경고: 킬러 상태입니다! 자수(surrender)를 고려하세요.{reset}"
                    )
            # Victim PK death count
            if victim.session:
                pd = victim.session.player_data
                pd["pk_deaths"] = pd.get("pk_deaths", 0) + 1
                await victim.session.send_line(
                    f"{{yellow}}{killer.name}에게 살해되었습니다.{{reset}}"
                )
            # Global PK announcement
            for s in engine.sessions:
                if hasattr(s, "send_line"):
                    await s.send_line(
                        f"{{bright_red}}[PK] {killer.name}이(가) "
                        f"{victim.name}을(를) 살해했습니다!{{reset}}"
                    )

        # Respawn to spirit room (11971)
        start_room = c.SPIRIT_ROOM
        if room and victim in room.characters:
            room.characters.remove(victim)

        # Full HP, 10% MP recovery (PvE death), PK: 50% HP/MP
        if is_pk:
            victim.hp = max(1, victim.max_hp // 2)
            victim.mana = max(1, victim.max_mana // 4)
        else:
            victim.hp = victim.max_hp
            victim.mana = max(1, victim.max_mana // 10)
        victim.position = 8  # POS_STANDING
        victim.room_vnum = start_room

        dest = world.get_room(start_room)
        if dest:
            dest.characters.append(victim)
            if victim.session:
                await victim.session.send_line(
                    "\r\n{yellow}죽음에서 벗어나 정신을 차립니다.{reset}\r\n"
                )
                await engine.do_look(victim.session, "")


async def decay_corpses(engine: Engine) -> None:
    """Tick-based corpse decay — removes corpses when timer reaches 0.

    Called from engine tick. Each corpse has values["timer"] that decrements
    every tick. When timer <= 0, corpse dissolves and remaining items drop to room.
    """
    world = engine.world
    for room in list(world.rooms.values()):
        for obj in list(room.objects):
            vals = getattr(obj, "values", None)
            if not vals or not isinstance(vals, dict):
                continue
            if not vals.get("corpse"):
                continue
            # Decrement timer
            timer = vals.get("timer", 0)
            timer -= 1
            vals["timer"] = timer
            if timer > 0:
                continue
            # Corpse decays: drop items to room
            for item in list(getattr(obj, "contains", [])):
                item.in_obj = None
                item.room_vnum = room.vnum
                room.objects.append(item)
            if hasattr(obj, "contains"):
                obj.contains.clear()
            # Remove corpse
            room.objects.remove(obj)
            # Notify room
            name = getattr(obj, "name", "시체")
            if not name:
                name = obj.proto.short_desc if obj.proto else "시체"
            for ch in room.characters:
                if ch.session:
                    await ch.session.send_line(
                        f"{{yellow}}{name}가 부패하여 사라집니다.{{reset}}"
                    )


def calculate_exp_gain(killer: MobInstance, victim: MobInstance) -> int:
    """3eyes exp gain — contribution-based (simplified)."""
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
