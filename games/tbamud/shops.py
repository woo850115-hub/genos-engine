"""Shop system — buy, sell, list, appraise."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine import Engine
    from core.session import Session


# Item type names for display
ITEM_TYPE_NAMES = {
    1: "빛", 2: "두루마리", 3: "지팡이", 4: "막대기", 5: "무기",
    6: "방화", 7: "투사체", 8: "보물", 9: "갑옷", 10: "물약",
    11: "쓸모없음", 12: "기타", 13: "쓰레기", 14: "컨테이너",
    15: "메모", 16: "음료", 17: "열쇠", 18: "음식",
    19: "돈", 20: "배", 21: "샘물",
}


def register(engine: Engine) -> None:
    engine.register_command("buy", do_buy, korean="사")
    engine.register_command("sell", do_sell, korean="팔")
    engine.register_command("list", do_list, korean="목록")
    engine.register_command("appraise", do_appraise, korean="감정")


def _find_shop(engine: Engine, session) -> tuple:
    """Find shop in current room. Returns (shop, keeper_mob) or (None, None)."""
    char = session.character
    if not char:
        return None, None

    room = engine.world.get_room(char.room_vnum)
    if not room:
        return None, None

    # Find shopkeeper NPC in room
    for mob in room.characters:
        if mob.is_npc and mob.proto.vnum in engine.world.shops:
            return engine.world.shops[mob.proto.vnum], mob

    return None, None


def _is_open(shop, hour: int = 12) -> bool:
    """Check if shop is open at given hour."""
    if shop.open1 <= hour < shop.close1:
        return True
    if shop.open2 <= hour < shop.close2:
        return True
    return False


async def do_buy(session, args: str) -> None:
    """Buy an item from a shop."""
    engine = session.engine
    shop, keeper = _find_shop(engine, session)
    if not shop:
        await session.send_line("여기에는 상점이 없습니다.")
        return

    if not _is_open(shop):
        await session.send_line(f"{keeper.name}이(가) '지금은 영업시간이 아닙니다.'라고 말합니다.")
        return

    if not args:
        await session.send_line(f"{keeper.name}이(가) '뭘 사시겠습니까?'라고 말합니다.")
        return

    char = session.character
    target_kw = args.strip().lower()

    # Search shop's selling items
    for item_vnum in shop.selling_items:
        proto = engine.world.item_protos.get(item_vnum)
        if not proto:
            continue
        if target_kw in proto.keywords.lower():
            price = int(proto.cost * shop.profit_buy)
            if char.gold < price:
                await session.send_line(
                    f"{keeper.name}이(가) '그건 {price} 골드입니다. 돈이 부족합니다.'라고 말합니다."
                )
                return
            # Create item instance
            obj = engine.world.create_obj(proto.vnum)
            char.gold -= price
            char.inventory.append(obj)
            await session.send_line(
                f"{{bright_yellow}}{proto.short_description}을(를) {price} 골드에 구입했습니다.{{reset}}"
            )
            return

    # Also check keeper's inventory
    for obj in keeper.inventory:
        if target_kw in obj.proto.keywords.lower():
            price = int(obj.proto.cost * shop.profit_buy)
            if char.gold < price:
                await session.send_line(
                    f"{keeper.name}이(가) '돈이 부족합니다.'라고 말합니다."
                )
                return
            keeper.inventory.remove(obj)
            char.gold -= price
            char.inventory.append(obj)
            await session.send_line(
                f"{{bright_yellow}}{obj.name}을(를) {price} 골드에 구입했습니다.{{reset}}"
            )
            return

    await session.send_line(f"{keeper.name}이(가) '그런 물건은 없습니다.'라고 말합니다.")


async def do_sell(session, args: str) -> None:
    """Sell an item to a shop."""
    engine = session.engine
    shop, keeper = _find_shop(engine, session)
    if not shop:
        await session.send_line("여기에는 상점이 없습니다.")
        return

    if not _is_open(shop):
        await session.send_line(f"{keeper.name}이(가) '영업시간이 아닙니다.'라고 말합니다.")
        return

    if not args:
        await session.send_line(f"{keeper.name}이(가) '뭘 파시겠습니까?'라고 말합니다.")
        return

    char = session.character
    target_kw = args.strip().lower()

    for obj in char.inventory:
        if target_kw in obj.proto.keywords.lower():
            price = int(obj.proto.cost * shop.profit_sell)
            price = max(1, price)
            char.inventory.remove(obj)
            char.gold += price
            keeper.inventory.append(obj)
            await session.send_line(
                f"{{bright_yellow}}{obj.name}을(를) {price} 골드에 판매했습니다.{{reset}}"
            )
            return

    await session.send_line(f"{keeper.name}이(가) '그런 물건을 가지고 있지 않습니다.'라고 말합니다.")


async def do_list(session, args: str) -> None:
    """List items for sale in a shop."""
    engine = session.engine
    shop, keeper = _find_shop(engine, session)
    if not shop:
        await session.send_line("여기에는 상점이 없습니다.")
        return

    if not _is_open(shop):
        await session.send_line(f"{keeper.name}이(가) '영업시간이 아닙니다.'라고 말합니다.")
        return

    lines = [f"{{bright_cyan}}{keeper.name}의 상점 물품 목록:{{reset}}"]

    # Permanent stock items
    idx = 1
    for item_vnum in shop.selling_items:
        proto = engine.world.item_protos.get(item_vnum)
        if not proto:
            continue
        price = int(proto.cost * shop.profit_buy)
        type_name = ITEM_TYPE_NAMES.get(proto.item_type, "기타")
        lines.append(f"  {idx}. {proto.short_description} [{type_name}] — {price} 골드 (무한)")
        idx += 1

    # Keeper's inventory
    for obj in keeper.inventory:
        price = int(obj.proto.cost * shop.profit_buy)
        type_name = ITEM_TYPE_NAMES.get(obj.proto.item_type, "기타")
        lines.append(f"  {idx}. {obj.name} [{type_name}] — {price} 골드")
        idx += 1

    if idx == 1:
        lines.append("  (판매 중인 물건이 없습니다)")

    await session.send_line("\r\n".join(lines))


async def do_appraise(session, args: str) -> None:
    """Appraise an item's sell value."""
    engine = session.engine
    shop, keeper = _find_shop(engine, session)
    if not shop:
        await session.send_line("여기에는 상점이 없습니다.")
        return

    if not args:
        await session.send_line("뭘 감정하시겠습니까?")
        return

    char = session.character
    target_kw = args.strip().lower()

    for obj in char.inventory:
        if target_kw in obj.proto.keywords.lower():
            price = int(obj.proto.cost * shop.profit_sell)
            price = max(1, price)
            await session.send_line(
                f"{keeper.name}이(가) '{obj.name}은(는) {price} 골드에 사겠습니다.'라고 말합니다."
            )
            return

    await session.send_line("그런 물건을 가지고 있지 않습니다.")
