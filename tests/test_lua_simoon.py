"""Tests for Simoon game plugin — combat, spells, commands, login, death."""

import pytest
import random
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine
from core.lua_commands import LuaCommandRuntime, CommandContext
from core.world import (
    Exit, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World, GameClass,
)


# ── Helpers ───────────────────────────────────────────────────


def _load_lua(eng):
    """Load all Lua scripts: common + simoon."""
    eng.lua = LuaCommandRuntime(eng)
    base = Path(__file__).resolve().parent.parent / "games"
    for scope in ("common", "simoon"):
        lua_dir = base / scope / "lua"
        lib = lua_dir / "lib.lua"
        if lib.exists():
            eng.lua.load_source(lib.read_text(encoding="utf-8"), f"{scope}/lib")
        for subdir in ("commands", "combat"):
            sub_path = lua_dir / subdir
            if sub_path.exists():
                for f in sorted(sub_path.glob("*.lua")):
                    eng.lua.load_source(f.read_text(encoding="utf-8"),
                                        f"{scope}/{subdir}/{f.stem}")
    eng.lua.register_all_commands()


def _make_world():
    w = World()
    room1 = RoomProto(
        vnum=3093, name="시문 신전", description="넓은 신전입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[], ext={})
    room2 = RoomProto(
        vnum=3094, name="광장", description="넓은 광장입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[], ext={})
    w.rooms[3093] = Room(proto=room1)
    w.rooms[3094] = Room(proto=room2)
    # Add Simoon classes
    w.classes = {
        0: GameClass(id=0, name="마법사", abbrev="Mu", hp_gain=(3, 8)),
        1: GameClass(id=1, name="성직자", abbrev="Cl", hp_gain=(5, 10)),
        2: GameClass(id=2, name="도적", abbrev="Th", hp_gain=(6, 11)),
        3: GameClass(id=3, name="전사", abbrev="Wa", hp_gain=(10, 15)),
        4: GameClass(id=4, name="흑마법사", abbrev="Dk", hp_gain=(3, 8)),
        5: GameClass(id=5, name="버서커", abbrev="Be", hp_gain=(12, 18)),
        6: GameClass(id=6, name="소환사", abbrev="Su", hp_gain=(4, 9)),
    }
    return w


def _make_engine(world=None):
    if world is None:
        world = _make_world()
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 3093}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    eng.game_name = "simoon"
    from games.simoon.game import SimoonPlugin
    eng._plugin = SimoonPlugin()
    _load_lua(eng)
    eng._load_korean_mappings()
    return eng


def _make_session(eng, char):
    session = MagicMock()
    session.send_line = AsyncMock()
    session.character = char
    session.engine = eng
    session.player_data = {"level": char.level, "name": char.name}
    char.session = session
    return session


def _player(level=10, class_id=0, race_id=0, mana=200, hp=100, max_hp=100,
            exp=0, gold=50, room_vnum=3094):
    proto = MobProto(
        vnum=-1, keywords="테스터", short_desc="테스터",
        long_desc="", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[],
        max_mana=0, max_move=0, damroll=0, position=8,
        class_id=0, race_id=0, stats={}, skills={}, ext={})
    ch = MobInstance(
        id=1, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=max_hp,
        mana=mana, max_mana=mana, gold=gold, experience=exp,
        player_id=1, player_name="테스터", class_id=class_id,
        player_level=level, race_id=race_id,
    )
    return ch


def _npc(level=5, hp=50, gold=20, exp=100, room_vnum=3094):
    proto = MobProto(
        vnum=50, keywords="goblin 고블린", short_desc="고블린",
        long_desc="", detail_desc="",
        level=level, hitroll=0, armor_class=100, max_hp=2,
        damage_dice="1d4+0", gold=gold, experience=exp,
        act_flags=[], aff_flags=[], alignment=0, sex=0, scripts=[],
        max_mana=0, max_move=0, damroll=0, position=8,
        class_id=0, race_id=0, stats={}, skills={}, ext={})
    return MobInstance(
        id=50, proto=proto, room_vnum=room_vnum, hp=hp, max_hp=hp, gold=gold,
    )


def _get_sent(session):
    return [str(c) for c in session.send_line.call_args_list]


# ── Plugin tests ──────────────────────────────────────────────


class TestSimoonPlugin:
    def test_plugin_name(self):
        from games.simoon.game import SimoonPlugin
        p = SimoonPlugin()
        assert p.name == "simoon"

    def test_welcome_banner(self):
        from games.simoon.game import SimoonPlugin
        p = SimoonPlugin()
        banner = p.welcome_banner()
        assert "시문" in banner or "Simoon" in banner

    def test_get_initial_state(self):
        from games.simoon.game import SimoonPlugin
        from games.simoon.login import SimoonGetNameState
        p = SimoonPlugin()
        state = p.get_initial_state()
        assert isinstance(state, SimoonGetNameState)

    def test_playing_prompt(self):
        from games.simoon.game import SimoonPlugin
        p = SimoonPlugin()
        ch = _player(hp=50, max_hp=100, mana=80)
        session = MagicMock()
        session.character = ch
        session.player_data = {}
        prompt = p.playing_prompt(session)
        assert "50" in prompt
        assert "100" in prompt

    def test_regen_char(self):
        from games.simoon.game import SimoonPlugin
        p = SimoonPlugin()
        ch = _player(hp=50, max_hp=200, mana=30, class_id=0)
        ch.max_mana = 200
        ch.move = 50
        ch.max_move = 100
        p.regen_char(None, ch)
        assert ch.hp > 50
        assert ch.mana > 30
        assert ch.move > 50

    def test_regen_caster_bonus(self):
        from games.simoon.game import SimoonPlugin
        p = SimoonPlugin()
        # Mage (caster) gets better mana regen
        ch_mage = _player(hp=100, max_hp=200, mana=50, class_id=0)
        ch_mage.max_mana = 200
        ch_mage.move = 50
        ch_mage.max_move = 100
        ch_war = _player(hp=100, max_hp=200, mana=50, class_id=3)
        ch_war.max_mana = 200
        ch_war.move = 50
        ch_war.max_move = 100
        p.regen_char(None, ch_mage)
        p.regen_char(None, ch_war)
        assert ch_mage.mana > ch_war.mana  # Caster mana regen > warrior


# ── Constants tests ───────────────────────────────────────────


class TestSimoonConstants:
    def test_7_classes(self):
        from games.simoon.constants import CLASS_NAMES
        assert len(CLASS_NAMES) == 7
        assert CLASS_NAMES[0] == "마법사"
        assert CLASS_NAMES[5] == "버서커"
        assert CLASS_NAMES[6] == "소환사"

    def test_5_races(self):
        from games.simoon.constants import RACE_NAMES
        assert len(RACE_NAMES) == 5
        assert RACE_NAMES[0] == "인간"
        assert RACE_NAMES[2] == "엘프"

    def test_race_class_restrictions(self):
        from games.simoon.constants import RACE_ALLOWED_CLASSES
        # Dwarf can't be MU(0), DK(4), SU(6)
        assert 0 not in RACE_ALLOWED_CLASSES[1]
        assert 4 not in RACE_ALLOWED_CLASSES[1]
        # Hobbit can only be CL(1), TH(2), WA(3)
        assert RACE_ALLOWED_CLASSES[3] == [1, 2, 3]

    def test_death_penalty_constants(self):
        from games.simoon.constants import (
            DEATH_PENALTY_MIN_LEVEL, DEATH_STAT_LOSS_MIN, DEATH_STAT_LOSS_MAX,
        )
        assert DEATH_PENALTY_MIN_LEVEL == 50
        assert DEATH_STAT_LOSS_MIN == 10
        assert DEATH_STAT_LOSS_MAX == 30


# ── Level system tests ────────────────────────────────────────


class TestSimoonLevel:
    def test_exp_table(self):
        from games.simoon.level import exp_for_level
        assert exp_for_level(0) == 0
        assert exp_for_level(1) == 2000
        assert exp_for_level(10) == 46000
        assert exp_for_level(300) == 220100000

    def test_exp_interpolation(self):
        from games.simoon.level import exp_for_level
        # Level 35 should be between level 30 and 40
        exp30 = exp_for_level(30)
        exp35 = exp_for_level(35)
        exp40 = exp_for_level(40)
        assert exp30 < exp35 < exp40

    def test_check_level_up(self):
        from games.simoon.level import check_level_up, exp_for_level
        ch = _player(level=1, exp=5200)
        ch.level = 1
        ch.experience = 5200
        assert check_level_up(ch)

    @pytest.mark.asyncio
    async def test_do_level_up(self):
        from games.simoon.level import do_level_up
        ch = _player(level=1, class_id=0, exp=10000)
        ch.level = 1
        ch.stats = {"con": 15, "wis": 15}
        send_fn = AsyncMock()
        gains = await do_level_up(ch, send_fn=send_fn)
        assert ch.level == 2
        assert gains["hp"] > 0
        assert send_fn.called


# ── Death system tests ────────────────────────────────────────


class TestSimoonDeath:
    @pytest.mark.asyncio
    async def test_npc_death_awards_exp(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=3, room_vnum=3094, exp=0)
        mob = _npc(level=5, hp=1, gold=10, exp=200, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.extend([ch, mob])

        from games.simoon.combat.death import handle_death
        await handle_death(eng, mob, killer=ch)

        assert ch.experience > 0
        assert mob not in w.rooms[3094].characters

    @pytest.mark.asyncio
    async def test_player_death_stat_penalty_high_level(self):
        """Level 50+ player gets permanent stat reduction on PvM death."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=60, class_id=3, room_vnum=3094, hp=0, max_hp=500)
        ch.max_mana = 300
        ch.max_move = 300
        ch.gold = 100000
        session = _make_session(eng, ch)
        w.rooms[3094].characters.append(ch)

        random.seed(42)
        from games.simoon.combat.death import handle_death
        await handle_death(eng, ch, killer=None)

        # Stats should have been reduced
        assert ch.max_hp < 500
        assert ch.max_mana < 300
        assert ch.max_move < 300
        assert ch.gold < 100000
        # Respawned at start room
        assert ch.room_vnum == 3093

    @pytest.mark.asyncio
    async def test_player_death_no_penalty_low_level(self):
        """Level < 50 player gets no stat penalty."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=3, room_vnum=3094, hp=0, max_hp=100)
        ch.max_mana = 100
        ch.max_move = 100
        ch.gold = 1000
        session = _make_session(eng, ch)
        w.rooms[3094].characters.append(ch)

        from games.simoon.combat.death import handle_death
        await handle_death(eng, ch, killer=None)

        # No stat penalty for low level
        assert ch.max_hp == 100
        assert ch.max_mana == 100
        assert ch.room_vnum == 3093


# ── Combat system tests (THAC0) ──────────────────────────────


class TestSimoonCombat:
    def test_combat_round_hook_registered(self):
        eng = _make_engine()
        assert eng.lua.has_hook("combat_round")

    @pytest.mark.asyncio
    async def test_combat_round_deals_damage(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=50, class_id=3, room_vnum=3094)
        mob = _npc(level=1, hp=100, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        await eng._lua_combat_round()

        msgs = _get_sent(session)
        assert any("빗나" in m or "입힙니다" in m for m in msgs) or mob.hp < 100

    @pytest.mark.asyncio
    async def test_multi_attack_high_level(self):
        """Level 150+ should get 5+ attacks per round."""
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=150, class_id=3, room_vnum=3094)
        ch.hitroll = 30
        mob = _npc(level=1, hp=10000, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        await eng._lua_combat_round()

        msgs = _get_sent(session)
        # Count hit/miss messages
        attack_msgs = [m for m in msgs if "빗나" in m or "입힙니다" in m]
        assert len(attack_msgs) >= 5

    @pytest.mark.asyncio
    async def test_combat_kills_npc(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=30, class_id=3, room_vnum=3094, exp=0)
        ch.hitroll = 20
        mob = _npc(level=1, hp=1, gold=10, exp=200, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        orig = random.randint
        random.randint = lambda a, b: 20 if b == 20 else orig(a, b)
        try:
            await eng._lua_combat_round()
        finally:
            random.randint = orig

        assert ch.fighting is None
        assert mob not in w.rooms[3094].characters
        assert ch.experience > 0


# ── Cast command tests ────────────────────────────────────────


class TestSimoonCast:
    @pytest.mark.asyncio
    async def test_cast_registered(self):
        eng = _make_engine()
        assert "cast" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_cast_no_args(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, mana=100, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)

        await eng.process_command(session, "cast")
        msgs = _get_sent(session)
        assert any("주문" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_unknown_spell(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, mana=100, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)

        await eng.process_command(session, "cast xyzzy")
        msgs = _get_sent(session)
        assert any("모릅니다" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_magic_missile(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=0, mana=100, room_vnum=3094)
        mob = _npc(level=5, hp=100, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.extend([ch, mob])

        initial_mana = ch.mana
        await eng.process_command(session, "cast magic 고블린")
        assert ch.mana < initial_mana
        assert ch.fighting is mob or mob.hp < 100

    @pytest.mark.asyncio
    async def test_cast_heal_cleric(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=100, class_id=1, mana=200, hp=50, max_hp=500,
                     room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.append(ch)

        await eng.process_command(session, "cast heal")
        assert ch.hp > 50

    @pytest.mark.asyncio
    async def test_cast_not_enough_mana(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=0, mana=0, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.append(ch)

        await eng.process_command(session, "cast magic 고블린")
        msgs = _get_sent(session)
        assert any("마나" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_warrior_cannot(self):
        """Warriors can't cast offensive spells."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=3, mana=100, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.append(ch)

        await eng.process_command(session, "cast magic 고블린")
        msgs = _get_sent(session)
        assert any("레벨" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_armor(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=15, class_id=0, mana=100, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.append(ch)

        await eng.process_command(session, "cast armor")
        has_buff = any(a.get("spell_id") == 1 for a in ch.affects)
        assert has_buff

    @pytest.mark.asyncio
    async def test_cast_word_of_recall(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=20, class_id=1, mana=100, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.append(ch)

        await eng.process_command(session, "cast 귀환")
        assert ch.room_vnum == 3093


# ── Score/Info command tests ──────────────────────────────────


class TestSimoonInfo:
    @pytest.mark.asyncio
    async def test_score_shows_class(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)

        await eng.process_command(session, "score")
        msgs = _get_sent(session)
        assert any("흑마법사" in m for m in msgs)
        assert any("테스터" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_score_shows_race(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, race_id=2, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)

        await eng.process_command(session, "score")
        msgs = _get_sent(session)
        assert any("엘프" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_practice_mage(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, mana=100, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)

        await eng.process_command(session, "practice")
        msgs = _get_sent(session)
        assert any("번개화살" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_practice_warrior_no_spells(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=3, mana=0, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)

        await eng.process_command(session, "practice")
        msgs = _get_sent(session)
        assert any("주문" in m for m in msgs)
        assert not any("번개화살" in m for m in msgs)


# ── Login state tests ─────────────────────────────────────────


class TestSimoonLogin:
    def test_login_states_exist(self):
        from games.simoon.login import (
            SimoonGetNameState, SimoonGetPasswordState,
            SimoonNewPasswordState, SimoonConfirmPasswordState,
            SimoonSelectGenderState, SimoonSelectRaceState,
            SimoonSelectClassState,
        )
        assert SimoonGetNameState().prompt()
        assert SimoonSelectRaceState().prompt()

    def test_race_selection_prompt(self):
        from games.simoon.login import SimoonSelectRaceState
        state = SimoonSelectRaceState()
        prompt = state.prompt()
        assert "인간" in prompt
        assert "엘프" in prompt
        assert "드워프" in prompt

    def test_class_selection_prompt_human(self):
        from games.simoon.login import SimoonSelectClassState
        state = SimoonSelectClassState(0)  # Human
        prompt = state.prompt()
        # Human can choose all 7 classes
        assert "마법사" in prompt
        assert "버서커" in prompt
        assert "소환사" in prompt

    def test_class_selection_prompt_dwarf(self):
        from games.simoon.login import SimoonSelectClassState
        state = SimoonSelectClassState(1)  # Dwarf
        prompt = state.prompt()
        # Dwarf can only be CL, TH, WA, BE
        assert "성직자" in prompt
        assert "전사" in prompt
        assert "마법사" not in prompt
        assert "소환사" not in prompt


# ── New CommandContext method tests ─────────────────────────


class TestSimoonNewMethods:
    """Tests for newly added CommandContext methods used by Simoon/3eyes."""

    @pytest.mark.asyncio
    async def test_find_inv_item(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        from core.world import ItemProto, ObjInstance, _next_id
        proto = ItemProto(
            vnum=100, keywords="검 sword", short_desc="날카로운 검",
            long_desc="", item_type="weapon", weight=5, cost=100, min_level=1,
            wear_slots=[16], flags=[], values={}, affects=[],
            extra_descs=[], scripts=[], ext={})
        obj = ObjInstance(id=_next_id(), proto=proto, values={})
        obj.carried_by = ch
        ch.inventory.append(obj)
        session = _make_session(eng, ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        found = ctx.find_inv_item("검")
        assert found is obj

    @pytest.mark.asyncio
    async def test_find_equip_item(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        from core.world import ItemProto, ObjInstance, _next_id
        proto = ItemProto(
            vnum=101, keywords="방패 shield", short_desc="튼튼한 방패",
            long_desc="", item_type="armor", weight=10, cost=200, min_level=1,
            wear_slots=[10], flags=[], values={}, affects=[],
            extra_descs=[], scripts=[], ext={})
        obj = ObjInstance(id=_next_id(), proto=proto, values={})
        obj.worn_by = ch
        ch.equipment[10] = obj
        session = _make_session(eng, ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        found = ctx.find_equip_item("방패")
        assert found is obj

    @pytest.mark.asyncio
    async def test_wear_and_remove_item(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        from core.world import ItemProto, ObjInstance, _next_id
        proto = ItemProto(
            vnum=102, keywords="투구 helm", short_desc="철투구",
            long_desc="", item_type="armor", weight=3, cost=50, min_level=1,
            wear_slots=[0], flags=[], values={}, affects=[],
            extra_descs=[], scripts=[], ext={})
        obj = ObjInstance(id=_next_id(), proto=proto, values={})
        obj.carried_by = ch
        ch.inventory.append(obj)
        session = _make_session(eng, ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        slot = ctx.wear_item(obj)
        assert slot == 0
        assert obj not in ch.inventory
        assert ch.equipment.get(0) is obj
        # Now remove
        ctx.remove_item(obj)
        assert obj in ch.inventory
        assert 0 not in ch.equipment

    @pytest.mark.asyncio
    async def test_wield_item(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=3, room_vnum=3094)
        from core.world import ItemProto, ObjInstance, _next_id
        proto = ItemProto(
            vnum=103, keywords="검 sword", short_desc="강철검",
            long_desc="", item_type="weapon", weight=5, cost=100, min_level=1,
            wear_slots=[16], flags=[], values={}, affects=[],
            extra_descs=[], scripts=[], ext={})
        obj = ObjInstance(id=_next_id(), proto=proto, values={})
        obj.carried_by = ch
        ch.inventory.append(obj)
        session = _make_session(eng, ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        slot = ctx.wield_item(obj)
        assert slot == 16
        assert ch.equipment.get(16) is obj

    @pytest.mark.asyncio
    async def test_get_toggles(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        session = _make_session(eng, ch)
        session.player_data["toggles"] = {"autoloot": True, "brief": False}
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        toggles = ctx.get_toggles()
        assert toggles["autoloot"] is True
        assert toggles["brief"] is False

    @pytest.mark.asyncio
    async def test_toggle(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        session = _make_session(eng, ch)
        session.player_data["toggles"] = {}
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        result = ctx.toggle("autoloot")
        assert result is True
        result2 = ctx.toggle("autoloot")
        assert result2 is False

    @pytest.mark.asyncio
    async def test_get_affects(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        ch.affects.append({"id": 42, "duration": 5})
        session = _make_session(eng, ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        affects = ctx.get_affects(ch)
        assert len(affects) == 1

    @pytest.mark.asyncio
    async def test_room_exists(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        session = _make_session(eng, ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        assert ctx.room_exists(3093) is True
        assert ctx.room_exists(99999) is False

    @pytest.mark.asyncio
    async def test_teleport_to(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        ok = ctx.teleport_to(3093)
        assert ok is True
        assert ch.room_vnum == 3093

    @pytest.mark.asyncio
    async def test_peek_exit(self):
        eng = _make_engine()
        # Add exit from 3094 → 3093 (north)
        from core.world import Exit
        eng.world.rooms[3094].proto.exits.append(
            Exit(direction=0, to_vnum=3093, keywords="", flags=[], key_vnum=-1))
        ch = _player(level=10, class_id=0, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        dest = ctx.peek_exit("north")
        assert dest == 3093

    @pytest.mark.asyncio
    async def test_steal_item(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=2, room_vnum=3094)  # Thief
        mob = _npc(level=5, hp=50, room_vnum=3094)
        from core.world import ItemProto, ObjInstance, _next_id
        proto = ItemProto(
            vnum=200, keywords="보석 gem", short_desc="빛나는 보석",
            long_desc="", item_type="treasure", weight=1, cost=500, min_level=1,
            wear_slots=[], flags=[], values={}, affects=[],
            extra_descs=[], scripts=[], ext={})
        gem = ObjInstance(id=_next_id(), proto=proto, values={})
        gem.carried_by = mob
        mob.inventory.append(gem)
        session = _make_session(eng, ch)
        from core.lua_commands import CommandContext
        ctx = CommandContext(session, eng)
        stolen = ctx.steal_item(mob, "보석")
        assert stolen is gem
        assert gem in ch.inventory
        assert gem not in mob.inventory

    @pytest.mark.asyncio
    async def test_execute_alias(self):
        """Test ctx:execute() calls another Lua command."""
        eng = _make_engine()
        ch = _player(level=10, class_id=0, room_vnum=3094)
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)
        # eq should call equipment
        await eng.process_command(session, "eq")
        msgs = _get_sent(session)
        assert any("장비" in m or "비어있음" in m or "착용" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_simoon_score_shows_crystal(self):
        """Score shows crystal/killmark from extensions."""
        eng = _make_engine()
        ch = _player(level=50, class_id=4, room_vnum=3094)
        ch.extensions = {"crystal": 100, "killmark": 5}
        session = _make_session(eng, ch)
        eng.world.rooms[3094].characters.append(ch)
        await eng.process_command(session, "score")
        msgs = _get_sent(session)
        assert any("크리스탈" in m for m in msgs)
        assert any("킬마크" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_simoon_death_crystal_loss(self):
        """Crystal loss on death for level 50+ player."""
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=60, class_id=3, room_vnum=3094, hp=0, max_hp=500)
        ch.max_mana = 300
        ch.max_move = 300
        ch.gold = 100000
        ch.extensions = {"crystal": 500}
        session = _make_session(eng, ch)
        w.rooms[3094].characters.append(ch)
        from games.simoon.combat.death import handle_death
        await handle_death(eng, ch, killer=None)
        assert ch.extensions.get("crystal", 0) < 500

    @pytest.mark.asyncio
    async def test_simoon_thac0_pc_weapon_damage(self):
        """PC damage uses weapon, not proto.damage_dice."""
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=3, room_vnum=3094)
        # Give PC a weapon
        from core.world import ItemProto, ObjInstance, _next_id
        wpn_proto = ItemProto(
            vnum=500, keywords="검 sword", short_desc="강철검",
            long_desc="", item_type="weapon", weight=5, cost=100, min_level=1,
            wear_slots=["wield"], flags=[], values={"damage": "3d6+5", "weapon_type": 3},
            affects=[], extra_descs=[], scripts=[], ext={})
        wpn = ObjInstance(id=_next_id(), proto=wpn_proto, values={})
        ch.equipment[16] = wpn
        mob = _npc(level=1, hp=10000, room_vnum=3094)
        session = _make_session(eng, ch)
        w.rooms[3094].characters.extend([ch, mob])
        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7
        # Run combat round
        await eng._lua_combat_round()
        # Should have hit messages (not errors)
        msgs = _get_sent(session)
        assert any("빗나" in m or "입힙니다" in m for m in msgs)
