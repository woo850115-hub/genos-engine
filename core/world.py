"""World model — Prototype/Instance data structures + boot-time loading.

GenOS Unified Schema v1.0:
  - Proto/Instance separation
  - TEXT[] tag flags (not int bitfields)
  - JSONB stats/values (dynamic, game-specific)
  - room_exits separate table (graph model)
  - wear_slots TEXT[] (dynamic equipment slots)
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from typing import Any

from core.db import Database

log = logging.getLogger(__name__)


# ── Prototypes (immutable templates from DB) ────────────────────

@dataclass(frozen=True, slots=True)
class Exit:
    direction: int  # 0=N, 1=E, 2=S, 3=W, 4=U, 5=D, 6~10=extended
    to_vnum: int
    keywords: str = ""
    description: str = ""
    key_vnum: int = -1
    flags: tuple[str, ...] = ()  # ("door","locked","pickproof")

    @property
    def has_door(self) -> bool:
        return "door" in self.flags

    @property
    def to_room(self) -> int:
        """Backward-compat alias."""
        return self.to_vnum


@dataclass(frozen=True, slots=True)
class ExtraDesc:
    keywords: str
    description: str


@dataclass(slots=True)
class RoomProto:
    vnum: int
    name: str = ""
    description: str = ""
    zone_vnum: int = 0
    sector: int = 0
    flags: list[str] = field(default_factory=list)
    exits: list[Exit] = field(default_factory=list)
    extra_descs: list[ExtraDesc] = field(default_factory=list)
    scripts: list[int] = field(default_factory=list)
    ext: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ItemProto:
    vnum: int
    keywords: str = ""
    short_desc: str = ""
    long_desc: str = ""
    item_type: str = "other"     # "weapon","armor","potion",...
    weight: int = 0
    cost: int = 0
    min_level: int = 0
    wear_slots: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)
    affects: list[dict[str, Any]] = field(default_factory=list)
    extra_descs: list[ExtraDesc] = field(default_factory=list)
    scripts: list[int] = field(default_factory=list)
    ext: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MobProto:
    vnum: int
    keywords: str = ""
    short_desc: str = ""
    long_desc: str = ""
    detail_desc: str = ""
    level: int = 1
    max_hp: int = 1
    max_mana: int = 0
    max_move: int = 0
    armor_class: int = 100
    hitroll: int = 0
    damroll: int = 0
    damage_dice: str = "1d4+0"   # "NdS+B"
    gold: int = 0
    experience: int = 0
    alignment: int = 0
    sex: int = 0
    position: int = 8
    class_id: int = 0
    race_id: int = 0
    act_flags: list[str] = field(default_factory=list)
    aff_flags: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    skills: dict[str, Any] = field(default_factory=dict)
    scripts: list[int] = field(default_factory=list)
    ext: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Zone:
    vnum: int
    name: str = ""
    builders: str = ""
    lifespan: int = 30
    reset_mode: int = 2
    flags: list[str] = field(default_factory=list)
    resets: list[dict[str, Any]] = field(default_factory=list)
    ext: dict[str, Any] = field(default_factory=dict)
    age: int = 0  # ticks since last reset


@dataclass(slots=True)
class Shop:
    vnum: int = 0
    keeper_vnum: int = 0
    room_vnum: int = 0
    buy_types: list[str] = field(default_factory=list)
    buy_profit: float = 1.1
    sell_profit: float = 0.9
    hours: dict[str, int] = field(default_factory=dict)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    messages: dict[str, str] = field(default_factory=dict)
    ext: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GameClass:
    id: int = 0
    name: str = ""
    abbrev: str = ""
    hp_gain: tuple[int, int] = (1, 10)
    mana_gain: tuple[int, int] = (0, 0)
    move_gain: tuple[int, int] = (0, 0)
    base_stats: dict[str, Any] = field(default_factory=dict)
    ext: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SkillProto:
    id: int = 0
    name: str = ""
    skill_type: str = "spell"    # "spell","skill","martial"
    mana_cost: int = 0
    target: str = "ignore"       # "char_room","self_only",...
    violent: bool = False
    min_position: int = 0
    routines: list[str] = field(default_factory=list)
    wearoff_msg: str = ""
    class_levels: dict[str, int] = field(default_factory=dict)
    ext: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RaceProto:
    id: int = 0
    name: str = ""
    abbrev: str = ""
    stat_mods: dict[str, int] = field(default_factory=dict)
    body_parts: list[str] = field(default_factory=list)
    size: str = "medium"
    ext: dict[str, Any] = field(default_factory=dict)


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
    race_id: int = 0
    player_level: int = 1
    position: int = 8  # POS_STANDING
    fighting: MobInstance | None = None
    inventory: list[ObjInstance] = field(default_factory=list)
    equipment: dict[str, ObjInstance] = field(default_factory=dict)  # slot_name → obj
    affects: list[dict[str, Any]] = field(default_factory=list)
    skills: dict[str, int] = field(default_factory=dict)  # skill_name → proficiency
    stats: dict[str, int] = field(default_factory=dict)    # dynamic stats
    flags: list[str] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
    # For players
    player_id: int | None = None
    player_name: str = ""
    session: Any = None  # back-reference to Session
    # Computed combat stats
    hitroll: int = 0
    damroll: int = 0
    armor_class: int = 100
    alignment: int = 0
    sex: int = 0

    @property
    def is_npc(self) -> bool:
        return self.player_id is None

    @property
    def name(self) -> str:
        if self.player_name:
            return self.player_name
        return self.proto.short_desc if self.proto else "someone"

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
    wear_slot: str = ""           # slot name ("wield","body",...)
    in_obj: ObjInstance | None = None
    contains: list[ObjInstance] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)  # mutable copy

    @property
    def name(self) -> str:
        return self.proto.short_desc if self.proto else "something"


# ── Room (live state) ────────────────────────────────────────────

@dataclass(slots=True)
class Room:
    proto: RoomProto
    characters: list[MobInstance] = field(default_factory=list)
    objects: list[ObjInstance] = field(default_factory=list)
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
            if ex.has_door:
                self.door_states[ex.direction] = {
                    "closed": "closed" in ex.flags,
                    "locked": "locked" in ex.flags,
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
        self.skills: dict[int, SkillProto] = {}
        self.races: dict[int, RaceProto] = {}
        self.socials: dict[str, dict[str, Any]] = {}
        self.help_entries: list[dict[str, Any]] = []
        self.game_configs: dict[str, Any] = {}
        self.game_tables: dict[str, dict[str, Any]] = {}  # table_name → {key_json → value}

    async def load_from_db(self, db: Database, data_dir: Any = None) -> None:
        """Load all proto tables into memory."""
        log.info("Loading world from database...")

        await self._load_rooms(db)
        await self._load_room_exits(db)
        await self._load_items(db)
        await self._load_mobs(db)
        await self._load_zones(db)
        await self._load_shops(db)
        await self._load_classes(db)
        await self._load_skills(db)
        await self._load_races(db)
        await self._load_socials(db)
        await self._load_help(db)
        await self._load_game_configs(db)
        await self._load_game_tables(db)

        log.info("World loaded: %d rooms, %d items, %d mobs",
                 len(self.rooms), len(self.item_protos), len(self.mob_protos))

    # ── Loaders ─────────────────────────────────────────────

    async def _load_rooms(self, db: Database) -> None:
        rows = await db.fetch_all("rooms")
        for r in rows:
            extra_descs_data = _jload(r["extra_descs"])
            extra_descs = [ExtraDesc(e["keywords"], e["description"]) for e in extra_descs_data]
            flags = _ensure_list(r.get("flags", []))
            scripts = _jload(r.get("scripts", "[]"))
            ext = _jload(r.get("ext", "{}"))
            proto = RoomProto(
                vnum=r["vnum"], name=r["name"], description=r["description"],
                zone_vnum=r.get("zone_vnum", 0), sector=r.get("sector", 0),
                flags=flags, exits=[], extra_descs=extra_descs,
                scripts=scripts, ext=ext,
            )
            self.rooms[r["vnum"]] = Room(proto=proto)
        log.info("  Rooms: %d", len(self.rooms))

    async def _load_room_exits(self, db: Database) -> None:
        rows = await db.fetch_all("room_exits")
        for r in rows:
            room = self.rooms.get(r["from_vnum"])
            if room is None:
                continue
            flags = _ensure_list(r.get("flags", []))
            ex = Exit(
                direction=r["direction"],
                to_vnum=r["to_vnum"],
                keywords=r.get("keywords", ""),
                description=r.get("description", ""),
                key_vnum=r.get("key_vnum", -1),
                flags=tuple(flags),
            )
            room.proto.exits.append(ex)
        # Initialize door states
        for room in self.rooms.values():
            room.init_doors()
        total_exits = sum(len(rm.proto.exits) for rm in self.rooms.values())
        log.info("  Exits: %d", total_exits)

    async def _load_items(self, db: Database) -> None:
        rows = await db.fetch_all("item_protos")
        for r in rows:
            extra_descs_data = _jload(r.get("extra_descs", "[]"))
            extra_descs = [ExtraDesc(e["keywords"], e["description"]) for e in extra_descs_data]
            self.item_protos[r["vnum"]] = ItemProto(
                vnum=r["vnum"], keywords=r.get("keywords", ""),
                short_desc=r.get("short_desc", ""),
                long_desc=r.get("long_desc", ""),
                item_type=r.get("item_type", "other"),
                weight=r.get("weight", 0), cost=r.get("cost", 0),
                min_level=r.get("min_level", 0),
                wear_slots=_ensure_list(r.get("wear_slots", [])),
                flags=_ensure_list(r.get("flags", [])),
                values=_jload(r.get("values", "{}")),
                affects=_jload(r.get("affects", "[]")),
                extra_descs=extra_descs,
                scripts=_jload(r.get("scripts", "[]")),
                ext=_jload(r.get("ext", "{}")),
            )
        log.info("  Items: %d", len(self.item_protos))

    async def _load_mobs(self, db: Database) -> None:
        rows = await db.fetch_all("mob_protos")
        for r in rows:
            self.mob_protos[r["vnum"]] = MobProto(
                vnum=r["vnum"], keywords=r.get("keywords", ""),
                short_desc=r.get("short_desc", ""),
                long_desc=r.get("long_desc", ""),
                detail_desc=r.get("detail_desc", ""),
                level=r.get("level", 1),
                max_hp=r.get("max_hp", 1),
                max_mana=r.get("max_mana", 0),
                max_move=r.get("max_move", 0),
                armor_class=r.get("armor_class", 100),
                hitroll=r.get("hitroll", 0),
                damroll=r.get("damroll", 0),
                damage_dice=r.get("damage_dice", "1d4+0"),
                gold=r.get("gold", 0),
                experience=r.get("experience", 0),
                alignment=r.get("alignment", 0),
                sex=r.get("sex", 0),
                position=r.get("position", 8),
                class_id=r.get("class_id", 0),
                race_id=r.get("race_id", 0),
                act_flags=_ensure_list(r.get("act_flags", [])),
                aff_flags=_ensure_list(r.get("aff_flags", [])),
                stats=_jload(r.get("stats", "{}")),
                skills=_jload(r.get("skills", "{}")),
                scripts=_jload(r.get("scripts", "[]")),
                ext=_jload(r.get("ext", "{}")),
            )
        log.info("  Mobs: %d", len(self.mob_protos))

    async def _load_zones(self, db: Database) -> None:
        rows = await db.fetch_all("zones")
        for r in rows:
            self.zones.append(Zone(
                vnum=r["vnum"], name=r["name"],
                builders=r.get("builders", ""),
                lifespan=r.get("lifespan", 30),
                reset_mode=r.get("reset_mode", 2),
                flags=_ensure_list(r.get("flags", [])),
                resets=_jload(r.get("resets", "[]")),
                ext=_jload(r.get("ext", "{}")),
            ))
        self.zones.sort(key=lambda z: z.vnum)
        log.info("  Zones: %d", len(self.zones))

    async def _load_shops(self, db: Database) -> None:
        rows = await db.fetch_all("shops")
        for r in rows:
            shop = Shop(
                vnum=r["vnum"], keeper_vnum=r["keeper_vnum"],
                room_vnum=r.get("room_vnum", 0),
                buy_types=_ensure_list(r.get("buy_types", [])),
                buy_profit=r.get("buy_profit", 1.1),
                sell_profit=r.get("sell_profit", 0.9),
                hours=_jload(r.get("hours", "{}")),
                inventory=_jload(r.get("inventory", "[]")),
                messages=_jload(r.get("messages", "{}")),
                ext=_jload(r.get("ext", "{}")),
            )
            self.shops[shop.keeper_vnum] = shop
        log.info("  Shops: %d", len(self.shops))

    async def _load_classes(self, db: Database) -> None:
        rows = await db.fetch_all("classes")
        for r in rows:
            # INT4RANGE comes as asyncpg Range object or string "[min,max)"
            hp = _parse_range(r.get("hp_gain"), (1, 10))
            mana = _parse_range(r.get("mana_gain"), (0, 0))
            move = _parse_range(r.get("move_gain"), (0, 0))
            self.classes[r["id"]] = GameClass(
                id=r["id"], name=r["name"],
                abbrev=r.get("abbrev", ""),
                hp_gain=hp, mana_gain=mana, move_gain=move,
                base_stats=_jload(r.get("base_stats", "{}")),
                ext=_jload(r.get("ext", "{}")),
            )
        log.info("  Classes: %d", len(self.classes))

    async def _load_skills(self, db: Database) -> None:
        rows = await db.fetch_all("skills")
        for r in rows:
            self.skills[r["id"]] = SkillProto(
                id=r["id"], name=r["name"],
                skill_type=r.get("skill_type", "spell"),
                mana_cost=r.get("mana_cost", 0),
                target=r.get("target", "ignore"),
                violent=r.get("violent", False),
                min_position=r.get("min_position", 0),
                routines=_ensure_list(r.get("routines", [])),
                wearoff_msg=r.get("wearoff_msg", ""),
                class_levels=_jload(r.get("class_levels", "{}")),
                ext=_jload(r.get("ext", "{}")),
            )
        log.info("  Skills: %d", len(self.skills))

    async def _load_races(self, db: Database) -> None:
        rows = await db.fetch_all("races")
        for r in rows:
            self.races[r["id"]] = RaceProto(
                id=r["id"], name=r["name"],
                abbrev=r.get("abbrev", ""),
                stat_mods=_jload(r.get("stat_mods", "{}")),
                body_parts=_ensure_list(r.get("body_parts", [])),
                size=r.get("size", "medium"),
                ext=_jload(r.get("ext", "{}")),
            )
        log.info("  Races: %d", len(self.races))

    async def _load_socials(self, db: Database) -> None:
        rows = await db.fetch_all("socials")
        for r in rows:
            self.socials[r["command"]] = {
                "command": r["command"],
                "min_victim_position": r.get("min_victim_position", 0),
                "messages": _jload(r.get("messages", "{}")),
            }
        log.info("  Socials: %d", len(self.socials))

    async def _load_help(self, db: Database) -> None:
        rows = await db.fetch_all("help_entries")
        for r in rows:
            self.help_entries.append({
                "keywords": _ensure_list(r.get("keywords", [])),
                "category": r.get("category", "general"),
                "min_level": r.get("min_level", 0),
                "body": r.get("body", ""),
            })
        log.info("  Help entries: %d", len(self.help_entries))

    async def _load_game_configs(self, db: Database) -> None:
        rows = await db.fetch_all("game_configs")
        for r in rows:
            val = _jload(r["value"])
            self.game_configs[r["key"]] = val
        log.info("  Game configs: %d", len(self.game_configs))

    async def _load_game_tables(self, db: Database) -> None:
        rows = await db.fetch_all("game_tables")
        for r in rows:
            table = r["table_name"]
            key = json.dumps(_jload(r["key"]), sort_keys=True)
            value = _jload(r["value"])
            if table not in self.game_tables:
                self.game_tables[table] = {}
            self.game_tables[table][key] = value
        total = sum(len(v) for v in self.game_tables.values())
        log.info("  Game tables: %d entries across %d tables",
                 total, len(self.game_tables))

    # ── Convenience lookups ─────────────────────────────────

    def get_exp_required(self, class_id: int, level: int) -> int:
        """Look up experience required for a level."""
        tbl = self.game_tables.get("exp_table", {})
        key = json.dumps({"class_id": class_id, "level": level}, sort_keys=True)
        return tbl.get(key, 0)

    def get_thac0(self, class_id: int, level: int) -> int:
        tbl = self.game_tables.get("thac0", {})
        key = json.dumps({"class_id": class_id, "level": level}, sort_keys=True)
        return tbl.get(key, 20)

    def get_saving_throw(self, class_id: int, save_type: int, level: int) -> int:
        tbl = self.game_tables.get("saving_throw", {})
        key = json.dumps({"class_id": class_id, "level": level, "type": save_type}, sort_keys=True)
        return tbl.get(key, 0)

    # ── Room access ─────────────────────────────────────────

    def get_room(self, vnum: int) -> Room | None:
        return self.rooms.get(vnum)

    # ── Instance creation ───────────────────────────────────

    def create_mob(self, vnum: int, room_vnum: int) -> MobInstance | None:
        proto = self.mob_protos.get(vnum)
        if proto is None:
            return None
        mob = MobInstance(
            id=_next_id(), proto=proto, room_vnum=room_vnum,
            hp=proto.max_hp, max_hp=proto.max_hp,
            mana=proto.max_mana, max_mana=proto.max_mana,
            move=proto.max_move, max_move=proto.max_move,
            gold=proto.gold, experience=proto.experience,
            class_id=proto.class_id, race_id=proto.race_id,
            hitroll=proto.hitroll, damroll=proto.damroll,
            armor_class=proto.armor_class,
            alignment=proto.alignment, sex=proto.sex,
            stats=dict(proto.stats),
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
            id=_next_id(), proto=proto, values=dict(proto.values),
        )

    def obj_to_room(self, obj: ObjInstance, room_vnum: int) -> None:
        obj.room_vnum = room_vnum
        room = self.rooms.get(room_vnum)
        if room:
            room.objects.append(obj)

    def char_to_room(self, mob: MobInstance, room_vnum: int) -> None:
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


# ── Utility functions ────────────────────────────────────────────

def _jload(val: Any) -> Any:
    """Load JSON if string, otherwise return as-is."""
    if isinstance(val, str):
        return json.loads(val)
    return val


def _ensure_list(val: Any) -> list:
    """Ensure val is a list (TEXT[] from asyncpg comes as list already)."""
    if val is None:
        return []
    if isinstance(val, str):
        return json.loads(val)
    if isinstance(val, (list, tuple)):
        return list(val)
    return []


def _parse_range(val: Any, default: tuple[int, int]) -> tuple[int, int]:
    """Parse INT4RANGE (asyncpg Range or string) to (min, max) tuple."""
    if val is None:
        return default
    # String format "[1,10)"
    if isinstance(val, str) and val.startswith("["):
        inner = val.strip("[)")
        parts = inner.split(",")
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]) - 1)
    # asyncpg Range object (has .lower/.upper as int|None, not methods)
    lo = getattr(val, "lower", None)
    hi = getattr(val, "upper", None)
    if isinstance(lo, int) or isinstance(hi, int):
        lo_val = lo if isinstance(lo, int) else default[0]
        hi_val = (hi - 1) if isinstance(hi, int) else default[1]
        return (lo_val, hi_val)
    return default


def _roll_dice(dice_str: str) -> int:
    """Roll NdS+B dice. E.g. '3d8+100' → random value."""
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
