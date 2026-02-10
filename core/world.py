"""World model — Prototype/Instance data structures + boot-time loading."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from core.db import Database

log = logging.getLogger(__name__)


# ── Prototypes (immutable templates from DB) ────────────────────

@dataclass(frozen=True, slots=True)
class Exit:
    direction: int  # 0=N, 1=E, 2=S, 3=W, 4=U, 5=D
    to_room: int
    keywords: str = ""
    description: str = ""
    door_flags: int = 0
    key_vnum: int = -1


@dataclass(frozen=True, slots=True)
class ExtraDesc:
    keywords: str
    description: str


@dataclass(slots=True)
class RoomProto:
    vnum: int
    name: str
    description: str
    zone_number: int
    sector_type: int
    room_flags: list[int]
    exits: list[Exit]
    extra_descs: list[ExtraDesc]
    trigger_vnums: list[int]


@dataclass(slots=True)
class ItemProto:
    vnum: int
    keywords: str
    short_description: str
    long_description: str
    item_type: int
    extra_flags: list[int]
    wear_flags: list[int]
    values: list[int]
    weight: int
    cost: int
    rent: int
    affects: list[dict[str, Any]]
    extra_descs: list[ExtraDesc]
    trigger_vnums: list[int]


@dataclass(slots=True)
class MobProto:
    vnum: int
    keywords: str
    short_description: str
    long_description: str
    detailed_description: str
    level: int
    hitroll: int
    armor_class: int
    hp_dice: str  # "NdS+B"
    damage_dice: str
    gold: int
    experience: int
    action_flags: list[int]
    affect_flags: list[int]
    alignment: int
    sex: int
    trigger_vnums: list[int]


@dataclass(slots=True)
class Zone:
    vnum: int
    name: str
    builders: str
    lifespan: int
    bot: int
    top: int
    reset_mode: int
    zone_flags: list[int]
    reset_commands: list[dict[str, Any]]
    age: int = 0  # ticks since last reset


@dataclass(slots=True)
class Shop:
    vnum: int
    keeper_vnum: int
    selling_items: list[int]
    profit_buy: float
    profit_sell: float
    shop_room: int
    open1: int
    close1: int
    open2: int
    close2: int


@dataclass(slots=True)
class GameClass:
    id: int
    name: str
    abbreviation: str
    hp_gain_min: int
    hp_gain_max: int
    extensions: dict[str, Any]


@dataclass(slots=True)
class Skill:
    id: int
    name: str
    spell_type: str
    max_mana: int
    min_mana: int
    mana_change: int
    min_position: int
    targets: int
    violent: bool
    routines: int
    wearoff_msg: str
    class_levels: dict[str, int]
    extensions: dict[str, Any]


# ── Runtime instances (mutable state) ────────────────────────────

_next_instance_id = 0


def _next_id() -> int:
    global _next_instance_id
    _next_instance_id += 1
    return _next_instance_id


@dataclass(slots=True)
class MobInstance:
    id: int
    proto: MobProto
    room_vnum: int
    hp: int
    max_hp: int
    mana: int = 0
    max_mana: int = 0
    move: int = 0
    max_move: int = 0
    gold: int = 0
    experience: int = 0
    class_id: int = 0
    player_level: int = 1
    position: int = 8  # POS_STANDING
    fighting: MobInstance | None = None
    inventory: list[ObjInstance] = field(default_factory=list)
    equipment: dict[int, ObjInstance] = field(default_factory=dict)
    affects: list[dict[str, Any]] = field(default_factory=list)
    skills: dict[int, int] = field(default_factory=dict)  # skill_id → proficiency
    # Stats (str/int/wis/dex/con/cha)
    str: int = 13
    intel: int = 13
    wis: int = 13
    dex: int = 13
    con: int = 13
    cha: int = 13
    hitroll: int = 0
    damroll: int = 0
    # For players
    player_id: int | None = None
    player_name: str = ""
    session: Any = None  # back-reference to Session

    @property
    def is_npc(self) -> bool:
        return self.player_id is None

    @property
    def name(self) -> str:
        if self.player_name:
            return self.player_name
        return self.proto.short_description if self.proto else "someone"

    @property
    def level(self) -> int:
        if not self.is_npc:
            return self.player_level
        return self.proto.level if self.proto else 1

    @level.setter
    def level(self, value: int) -> None:
        self.player_level = value


@dataclass(slots=True)
class ObjInstance:
    id: int
    proto: ItemProto
    room_vnum: int | None = None
    carried_by: MobInstance | None = None
    worn_by: MobInstance | None = None
    wear_pos: int = -1
    in_obj: ObjInstance | None = None
    contains: list[ObjInstance] = field(default_factory=list)
    values: list[int] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.proto.short_description if self.proto else "something"


# ── Room (live state) ────────────────────────────────────────────

@dataclass(slots=True)
class Room:
    proto: RoomProto
    characters: list[MobInstance] = field(default_factory=list)
    objects: list[ObjInstance] = field(default_factory=list)
    # Mutable door states: direction → {"closed": bool, "locked": bool}
    door_states: dict[int, dict[str, bool]] = field(default_factory=dict)

    @property
    def vnum(self) -> int:
        return self.proto.vnum

    @property
    def name(self) -> str:
        return self.proto.name

    def init_doors(self) -> None:
        """Initialize mutable door states from proto exits."""
        for ex in self.proto.exits:
            if ex.door_flags & 1:  # has door
                self.door_states[ex.direction] = {
                    "closed": bool(ex.door_flags & 2),
                    "locked": bool(ex.door_flags & 4),
                }

    def is_door_closed(self, direction: int) -> bool:
        ds = self.door_states.get(direction)
        return ds is not None and ds.get("closed", False)

    def is_door_locked(self, direction: int) -> bool:
        ds = self.door_states.get(direction)
        return ds is not None and ds.get("locked", False)

    def has_door(self, direction: int) -> bool:
        return direction in self.door_states


# ── World singleton ──────────────────────────────────────────────

class World:
    """In-memory game world — loaded from DB at boot."""

    def __init__(self) -> None:
        self.rooms: dict[int, Room] = {}
        self.item_protos: dict[int, ItemProto] = {}
        self.mob_protos: dict[int, MobProto] = {}
        self.zones: list[Zone] = []
        self.shops: dict[int, Shop] = {}
        self.classes: dict[int, GameClass] = {}
        self.skills: dict[int, Skill] = {}
        self.socials: dict[str, dict[str, Any]] = {}
        self.help_entries: list[dict[str, Any]] = []
        self.commands: dict[str, dict[str, Any]] = {}
        self.game_configs: dict[str, Any] = {}
        self.exp_table: dict[tuple[int, int], int] = {}   # (class_id, level) → exp
        self.thac0_table: dict[tuple[int, int], int] = {}  # (class_id, level) → thac0
        self.saving_throws: dict[tuple[int, int, int], int] = {}  # (class,save,lv) → val
        self.triggers_lua: str = ""  # raw Lua source for lupa

    async def load_from_db(self, db: Database, data_dir: Any = None) -> None:
        """Load all 21 tables into memory."""
        log.info("Loading world from database...")

        # Rooms
        rows = await db.fetch_all("rooms")
        for r in rows:
            exits_data = json.loads(r["exits"]) if isinstance(r["exits"], str) else r["exits"]
            exits = []
            for e in exits_data:
                exits.append(Exit(
                    direction=e.get("direction", 0),
                    to_room=e.get("to_room", -1),
                    keywords=e.get("keywords", ""),
                    description=e.get("description", ""),
                    door_flags=e.get("door_flags", 0),
                    key_vnum=e.get("key_vnum", -1),
                ))
            extra_descs_data = (
                json.loads(r["extra_descs"]) if isinstance(r["extra_descs"], str)
                else r["extra_descs"]
            )
            extra_descs = [ExtraDesc(e["keywords"], e["description"]) for e in extra_descs_data]
            flags = json.loads(r["room_flags"]) if isinstance(r["room_flags"], str) else r["room_flags"]
            tvnums = json.loads(r["trigger_vnums"]) if isinstance(r["trigger_vnums"], str) else r["trigger_vnums"]
            proto = RoomProto(
                vnum=r["vnum"], name=r["name"], description=r["description"],
                zone_number=r["zone_number"], sector_type=r["sector_type"],
                room_flags=flags, exits=exits, extra_descs=extra_descs,
                trigger_vnums=tvnums,
            )
            self.rooms[r["vnum"]] = Room(proto=proto)
        # Initialize mutable door states
        for room in self.rooms.values():
            room.init_doors()
        log.info("  Rooms: %d", len(self.rooms))

        # Items
        rows = await db.fetch_all("items")
        for r in rows:
            extra_descs_data = (
                json.loads(r["extra_descs"]) if isinstance(r["extra_descs"], str)
                else r["extra_descs"]
            )
            extra_descs = [ExtraDesc(e["keywords"], e["description"]) for e in extra_descs_data]
            self.item_protos[r["vnum"]] = ItemProto(
                vnum=r["vnum"], keywords=r["keywords"],
                short_description=r["short_description"],
                long_description=r["long_description"],
                item_type=r["item_type"],
                extra_flags=_jload(r["extra_flags"]),
                wear_flags=_jload(r["wear_flags"]),
                values=_jload(r["values"]),
                weight=r["weight"], cost=r["cost"], rent=r["rent"],
                affects=_jload(r["affects"]),
                extra_descs=extra_descs,
                trigger_vnums=_jload(r["trigger_vnums"]),
            )
        log.info("  Items: %d", len(self.item_protos))

        # Monsters
        rows = await db.fetch_all("monsters")
        for r in rows:
            self.mob_protos[r["vnum"]] = MobProto(
                vnum=r["vnum"], keywords=r["keywords"],
                short_description=r["short_description"],
                long_description=r["long_description"],
                detailed_description=r["detailed_description"],
                level=r["level"], hitroll=r["hitroll"],
                armor_class=r["armor_class"],
                hp_dice=r["hp_dice"], damage_dice=r["damage_dice"],
                gold=r["gold"], experience=r["experience"],
                action_flags=_jload(r["action_flags"]),
                affect_flags=_jload(r["affect_flags"]),
                alignment=r["alignment"], sex=r["sex"],
                trigger_vnums=_jload(r["trigger_vnums"]),
            )
        log.info("  Monsters: %d", len(self.mob_protos))

        # Zones
        rows = await db.fetch_all("zones")
        for r in rows:
            self.zones.append(Zone(
                vnum=r["vnum"], name=r["name"], builders=r["builders"],
                lifespan=r["lifespan"], bot=r["bot"], top=r["top"],
                reset_mode=r["reset_mode"],
                zone_flags=_jload(r["zone_flags"]),
                reset_commands=_jload(r["reset_commands"]),
            ))
        self.zones.sort(key=lambda z: z.vnum)
        log.info("  Zones: %d", len(self.zones))

        # Shops
        rows = await db.fetch_all("shops")
        for r in rows:
            self.shops[r["keeper_vnum"]] = Shop(
                vnum=r["vnum"], keeper_vnum=r["keeper_vnum"],
                selling_items=_jload(r["selling_items"]),
                profit_buy=r["profit_buy"], profit_sell=r["profit_sell"],
                shop_room=r["shop_room"],
                open1=r["open1"], close1=r["close1"],
                open2=r["open2"], close2=r["close2"],
            )
        log.info("  Shops: %d", len(self.shops))

        # Classes
        rows = await db.fetch_all("classes")
        for r in rows:
            self.classes[r["id"]] = GameClass(
                id=r["id"], name=r["name"], abbreviation=r["abbreviation"],
                hp_gain_min=r["hp_gain_min"], hp_gain_max=r["hp_gain_max"],
                extensions=_jload(r["extensions"]),
            )
        log.info("  Classes: %d", len(self.classes))

        # Skills
        rows = await db.fetch_all("skills")
        for r in rows:
            self.skills[r["id"]] = Skill(
                id=r["id"], name=r["name"], spell_type=r["spell_type"],
                max_mana=r["max_mana"], min_mana=r["min_mana"],
                mana_change=r["mana_change"], min_position=r["min_position"],
                targets=r["targets"], violent=r["violent"],
                routines=r["routines"], wearoff_msg=r["wearoff_msg"],
                class_levels=_jload(r["class_levels"]),
                extensions=_jload(r["extensions"]),
            )
        log.info("  Skills: %d", len(self.skills))

        # Socials
        rows = await db.fetch_all("socials")
        for r in rows:
            self.socials[r["command"]] = dict(r)
        log.info("  Socials: %d", len(self.socials))

        # Help entries
        rows = await db.fetch_all("help_entries")
        for r in rows:
            self.help_entries.append({
                "keywords": _jload(r["keywords"]),
                "min_level": r["min_level"],
                "text": r["text"],
            })
        log.info("  Help entries: %d", len(self.help_entries))

        # Commands
        rows = await db.fetch_all("commands")
        for r in rows:
            self.commands[r["name"]] = dict(r)
        log.info("  Commands: %d", len(self.commands))

        # Game configs
        rows = await db.fetch_all("game_configs")
        for r in rows:
            self.game_configs[r["key"]] = r["value"]
        log.info("  Game configs: %d", len(self.game_configs))

        # Experience table
        rows = await db.fetch_all("experience_table")
        for r in rows:
            self.exp_table[(r["class_id"], r["level"])] = r["exp_required"]
        log.info("  Exp table entries: %d", len(self.exp_table))

        # THAC0 table
        rows = await db.fetch_all("thac0_table")
        for r in rows:
            self.thac0_table[(r["class_id"], r["level"])] = r["thac0"]
        log.info("  THAC0 table entries: %d", len(self.thac0_table))

        # Saving throws
        rows = await db.fetch_all("saving_throws")
        for r in rows:
            self.saving_throws[(r["class_id"], r["save_type"], r["level"])] = r["save_value"]
        log.info("  Saving throws: %d", len(self.saving_throws))

        log.info("World loaded: %d rooms, %d items, %d mobs",
                 len(self.rooms), len(self.item_protos), len(self.mob_protos))

    def get_room(self, vnum: int) -> Room | None:
        return self.rooms.get(vnum)

    def create_mob(self, vnum: int, room_vnum: int) -> MobInstance | None:
        proto = self.mob_protos.get(vnum)
        if proto is None:
            return None
        hp = _roll_dice(proto.hp_dice)
        mob = MobInstance(
            id=_next_id(), proto=proto, room_vnum=room_vnum,
            hp=hp, max_hp=hp, gold=proto.gold,
        )
        room = self.rooms.get(room_vnum)
        if room:
            room.characters.append(mob)
        return mob

    def create_obj(self, vnum: int) -> ObjInstance | None:
        proto = self.item_protos.get(vnum)
        if proto is None:
            return None
        return ObjInstance(
            id=_next_id(), proto=proto, values=list(proto.values),
        )

    def obj_to_room(self, obj: ObjInstance, room_vnum: int) -> None:
        obj.room_vnum = room_vnum
        room = self.rooms.get(room_vnum)
        if room:
            room.objects.append(obj)

    def char_to_room(self, mob: MobInstance, room_vnum: int) -> None:
        # Remove from old room
        old_room = self.rooms.get(mob.room_vnum)
        if old_room and mob in old_room.characters:
            old_room.characters.remove(mob)
        mob.room_vnum = room_vnum
        new_room = self.rooms.get(room_vnum)
        if new_room:
            new_room.characters.append(mob)

    def char_from_room(self, mob: MobInstance) -> None:
        room = self.rooms.get(mob.room_vnum)
        if room and mob in room.characters:
            room.characters.remove(mob)


def _jload(val: Any) -> Any:
    """Load JSON if string, otherwise return as-is."""
    if isinstance(val, str):
        return json.loads(val)
    return val


def _roll_dice(dice_str: str) -> int:
    """Roll NdS+B dice. E.g. '3d8+100' → random value."""
    import random
    if "d" not in dice_str:
        return int(dice_str)
    left, rest = dice_str.split("d", 1)
    n = int(left) if left else 0
    if "+" in rest:
        s_str, b_str = rest.split("+", 1)
        s, b = int(s_str), int(b_str)
    elif "-" in rest:
        s_str, b_str = rest.split("-", 1)
        s, b = int(s_str), -int(b_str)
    else:
        s, b = int(rest), 0
    total = b
    for _ in range(n):
        total += random.randint(1, max(1, s))
    return max(1, total)
