"""10woongi item commands — 22-slot wear/remove, get/drop."""

from __future__ import annotations

import importlib
from typing import Any

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


def register(engine: Any) -> None:
    engine.register_command("get", do_get, korean="주워")
    engine.register_command("drop", do_drop, korean="놔")
    engine.register_command("wear", do_wear, korean="착용")
    engine.register_command("remove", do_remove, korean="벗")
    engine.register_command("wield", do_wear, korean="챙기")


async def do_get(session: Any, args: str) -> None:
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("무엇을 주우시겠습니까?")
        return
    room = session.engine.world.get_room(char.room_vnum)
    if not room:
        return
    target_kw = args.strip().lower()
    for obj in list(room.objects):
        if target_kw in obj.proto.keywords.lower():
            room.objects.remove(obj)
            obj.room_vnum = None
            obj.carried_by = char
            char.inventory.append(obj)
            await session.send_line(f"{obj.name}을(를) 주웠습니다.")
            return
    await session.send_line("그런 것은 여기에 없습니다.")


async def do_drop(session: Any, args: str) -> None:
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("무엇을 버리시겠습니까?")
        return
    target_kw = args.strip().lower()
    for obj in list(char.inventory):
        if target_kw in obj.proto.keywords.lower():
            char.inventory.remove(obj)
            obj.carried_by = None
            session.engine.world.obj_to_room(obj, char.room_vnum)
            await session.send_line(f"{obj.name}을(를) 버렸습니다.")
            return
    await session.send_line("그런 물건을 가지고 있지 않습니다.")


async def do_wear(session: Any, args: str) -> None:
    """Wear an item from inventory into a 22-slot equipment slot."""
    constants = _import("constants")
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("무엇을 착용하시겠습니까?")
        return

    target_kw = args.strip().lower()
    for obj in list(char.inventory):
        if target_kw in obj.proto.keywords.lower():
            # Find available slot from wear_flags
            wear_flags = obj.proto.wear_flags
            if not wear_flags:
                await session.send_line("착용할 수 없는 물건입니다.")
                return

            # Find first empty slot matching wear flags
            slot = _find_wear_slot(char, wear_flags)
            if slot is None:
                await session.send_line("착용할 수 있는 빈 슬롯이 없습니다.")
                return

            char.inventory.remove(obj)
            obj.carried_by = None
            obj.worn_by = char
            obj.wear_pos = slot
            char.equipment[slot] = obj

            slot_name = constants.WEAR_SLOTS.get(slot, f"슬롯{slot}")
            await session.send_line(f"<{slot_name}>에 {obj.name}을(를) 착용했습니다.")
            return

    await session.send_line("그런 물건을 가지고 있지 않습니다.")


def _find_wear_slot(char: Any, wear_flags: list[int]) -> int | None:
    """Find first available equipment slot from wear flags.

    Wear flag values map to slot IDs. Ring slots (9, 13~21) fill sequentially.
    """
    constants = _import("constants")

    # Ring slots: try all 10 ring positions
    ring_slots = [9, 13, 14, 15, 16, 17, 18, 19, 20, 21]
    # Armlet slots: 8, 22
    armlet_slots = [8, 22]

    for flag in wear_flags:
        if flag == 0:
            continue
        # Map wear flag to slot ID(s)
        # Simple mapping: flag value = slot ID for most slots
        if flag in ring_slots:
            for rs in ring_slots:
                if rs not in char.equipment:
                    return rs
        elif flag in armlet_slots:
            for ars in armlet_slots:
                if ars not in char.equipment:
                    return ars
        elif flag not in char.equipment:
            return flag

    return None


async def do_remove(session: Any, args: str) -> None:
    """Remove equipped item."""
    constants = _import("constants")
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("무엇을 벗으시겠습니까?")
        return

    target_kw = args.strip().lower()
    for slot_id, obj in list(char.equipment.items()):
        if target_kw in obj.proto.keywords.lower():
            del char.equipment[slot_id]
            obj.worn_by = None
            obj.wear_pos = -1
            obj.carried_by = char
            char.inventory.append(obj)
            slot_name = constants.WEAR_SLOTS.get(slot_id, f"슬롯{slot_id}")
            await session.send_line(f"<{slot_name}>에서 {obj.name}을(를) 벗었습니다.")
            return

    await session.send_line("그런 장비를 착용하고 있지 않습니다.")
