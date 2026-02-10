"""Item commands — get, drop, put, give, wear, remove, equipment."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine import Engine
    from core.session import Session
    from core.world import ObjInstance


# Wear position names (tbaMUD standard 18 slots)
WEAR_NAMES = [
    "머리 위에", "왼쪽 손가락에", "오른쪽 손가락에", "목에 (1)",
    "목에 (2)", "몸통에", "머리에", "다리에",
    "발에", "손에", "팔에", "방패로",
    "몸 주위에", "허리에", "왼팔에", "오른팔에",
    "오른손에", "왼손에",
]


def register(engine: Engine) -> None:
    engine.register_command("get", do_get, korean="줍")
    engine.register_command("take", do_get)
    engine.register_command("drop", do_drop, korean="버려")
    engine.register_command("wear", do_wear, korean="입")
    engine.register_command("wield", do_wear)
    engine.register_command("remove", do_remove, korean="벗")
    engine.register_command("equipment", do_equipment, korean="장비")
    engine.register_command("eq", do_equipment)
    engine.register_command("give", do_give, korean="줘")
    engine.register_command("put", do_put, korean="넣")


async def do_get(session: Session, args: str) -> None:
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("무엇을 주우시겠습니까?")
        return

    room = session.engine.world.get_room(char.room_vnum)
    if not room:
        return

    target = args.strip().lower()

    if target == "all" or target == "모두":
        if not room.objects:
            await session.send_line("여기에는 아무것도 없습니다.")
            return
        picked = list(room.objects)
        for obj in picked:
            room.objects.remove(obj)
            obj.room_vnum = None
            obj.carried_by = char
            char.inventory.append(obj)
            await session.send_line(f"{obj.name}을(를) 주웠습니다.")
        return

    for obj in room.objects:
        if target in obj.proto.keywords.lower():
            room.objects.remove(obj)
            obj.room_vnum = None
            obj.carried_by = char
            char.inventory.append(obj)
            await session.send_line(f"{obj.name}을(를) 주웠습니다.")
            return

    await session.send_line("그런 것은 여기에 없습니다.")


async def do_drop(session: Session, args: str) -> None:
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("무엇을 버리시겠습니까?")
        return

    target = args.strip().lower()

    for obj in char.inventory:
        if target in obj.proto.keywords.lower():
            char.inventory.remove(obj)
            obj.carried_by = None
            session.engine.world.obj_to_room(obj, char.room_vnum)
            await session.send_line(f"{obj.name}을(를) 버렸습니다.")
            return

    await session.send_line("그런 것을 갖고 있지 않습니다.")


async def do_wear(session: Session, args: str) -> None:
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("무엇을 착용하시겠습니까?")
        return

    target = args.strip().lower()

    for obj in char.inventory:
        if target in obj.proto.keywords.lower():
            # Find first available wear position from obj's wear_flags
            wear_flags = obj.proto.wear_flags
            if not wear_flags or wear_flags == [0]:
                await session.send_line("그것은 착용할 수 없습니다.")
                return
            # Simple: use first wear flag > 0 as position
            pos = -1
            for flag in wear_flags:
                if flag > 0 and flag < len(WEAR_NAMES):
                    if flag not in char.equipment:
                        pos = flag
                        break
            if pos < 0:
                await session.send_line("이미 그 위치에 뭔가를 착용하고 있습니다.")
                return
            char.inventory.remove(obj)
            obj.carried_by = None
            obj.worn_by = char
            obj.wear_pos = pos
            char.equipment[pos] = obj
            pos_name = WEAR_NAMES[pos] if pos < len(WEAR_NAMES) else "어딘가에"
            await session.send_line(f"{obj.name}을(를) {pos_name} 착용했습니다.")
            return

    await session.send_line("그런 것을 갖고 있지 않습니다.")


async def do_remove(session: Session, args: str) -> None:
    char = session.character
    if not char:
        return
    if not args:
        await session.send_line("무엇을 벗으시겠습니까?")
        return

    target = args.strip().lower()

    for pos, obj in list(char.equipment.items()):
        if target in obj.proto.keywords.lower():
            del char.equipment[pos]
            obj.worn_by = None
            obj.wear_pos = -1
            obj.carried_by = char
            char.inventory.append(obj)
            await session.send_line(f"{obj.name}을(를) 벗었습니다.")
            return

    await session.send_line("그런 것을 착용하고 있지 않습니다.")


async def do_equipment(session: Session, args: str) -> None:
    char = session.character
    if not char:
        return
    if not char.equipment:
        await session.send_line("아무것도 착용하고 있지 않습니다.")
        return
    await session.send_line("착용 중인 장비:")
    for pos in sorted(char.equipment.keys()):
        obj = char.equipment[pos]
        pos_name = WEAR_NAMES[pos] if pos < len(WEAR_NAMES) else "어딘가"
        await session.send_line(f"  <{pos_name}> {obj.name}")


async def do_give(session: Session, args: str) -> None:
    if not args:
        await session.send_line("무엇을 누구에게 주시겠습니까?")
        return
    await session.send_line("구현 예정입니다.")


async def do_put(session: Session, args: str) -> None:
    if not args:
        await session.send_line("무엇을 어디에 넣으시겠습니까?")
        return
    await session.send_line("구현 예정입니다.")
