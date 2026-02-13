"""Tests for 3eyes game plugin — combat, spells, commands, login, death, proficiency."""

import pytest
import random
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine
from core.lua_commands import LuaCommandRuntime, CommandContext
from core.world import (
    Exit, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World, GameClass,
)


# ── Helpers ───────────────────────────────────────────────────


def _load_lua(eng):
    """Load all Lua scripts: common + 3eyes."""
    eng.lua = LuaCommandRuntime(eng)
    base = Path(__file__).resolve().parent.parent / "games"
    for scope in ("common", "3eyes"):
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
        vnum=1, name="시작의 방", description="모험의 시작입니다.",
        zone_vnum=0, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[], ext={})
    room2 = RoomProto(
        vnum=100, name="광장", description="넓은 광장입니다.",
        zone_vnum=1, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[], ext={})
    spirit = RoomProto(
        vnum=11971, name="영혼의 방", description="사후 세계입니다.",
        zone_vnum=119, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[], ext={})
    w.rooms[1] = Room(proto=room1)
    w.rooms[100] = Room(proto=room2)
    w.rooms[11971] = Room(proto=spirit)
    # Add 3eyes classes (1-indexed)
    w.classes = {
        1: GameClass(id=1, name="암살자", abbrev="As", hp_gain=(4, 8)),
        2: GameClass(id=2, name="야만인", abbrev="Ba", hp_gain=(5, 10)),
        3: GameClass(id=3, name="성직자", abbrev="Cl", hp_gain=(3, 8)),
        4: GameClass(id=4, name="전사", abbrev="Fi", hp_gain=(6, 12)),
        5: GameClass(id=5, name="마법사", abbrev="Ma", hp_gain=(2, 6)),
        6: GameClass(id=6, name="팔라딘", abbrev="Pa", hp_gain=(5, 10)),
        7: GameClass(id=7, name="광전사", abbrev="Ra", hp_gain=(7, 14)),
        8: GameClass(id=8, name="도적", abbrev="Th", hp_gain=(3, 8)),
    }
    return w


def _make_engine(world=None):
    if world is None:
        world = _make_world()
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 1}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    eng.game_name = "3eyes"
    import importlib
    game_mod = importlib.import_module("games.3eyes.game")
    eng._plugin = game_mod.ThreeEyesPlugin()
    _load_lua(eng)
    eng._load_korean_mappings()
    return eng


def _make_session(eng, char):
    # IMPORTANT: Use SimpleNamespace, NOT MagicMock.
    # lupa uses __getitem__ on MagicMock → returns non-nil MagicMock children
    # for ANY attribute, causing Lua pcall+nil-check loops to never terminate (OOM).
    # SimpleNamespace uses __getattr__ which lupa handles correctly.
    session = SimpleNamespace()
    session.send_line = AsyncMock()
    session.character = char
    session.engine = eng
    session.player_data = {
        "level": char.level, "name": char.name,
        "flags": [], "spells_known": [], "cooldowns": {},
        "toggles": {},
    }
    session._engine = eng
    char.session = session
    return session


def _player(level=10, class_id=4, race_id=5, mana=100, hp=100, max_hp=100,
            exp=0, gold=50, room_vnum=100):
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
    ch.stats = {"str": 15, "dex": 14, "con": 16, "int": 12, "pie": 13}
    ch.extensions = {"proficiency": [0, 0, 0, 0, 0], "realm": [0, 0, 0, 0]}
    return ch


def _npc(level=5, hp=50, gold=20, exp=100, room_vnum=100):
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


class TestThreeEyesPlugin:
    def test_plugin_name(self):
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        p = game_mod.ThreeEyesPlugin()
        assert p.name == "3eyes"

    def test_welcome_banner(self):
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        p = game_mod.ThreeEyesPlugin()
        banner = p.welcome_banner()
        assert "3eyes" in banner or "검눈" in banner or "검제" in banner or "3의 눈" in banner

    def test_get_initial_state(self):
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        login_mod = importlib.import_module("games.3eyes.login")
        p = game_mod.ThreeEyesPlugin()
        state = p.get_initial_state()
        assert isinstance(state, login_mod.ThreeEyesGetNameState)

    def test_playing_prompt(self):
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        p = game_mod.ThreeEyesPlugin()
        ch = _player(hp=45, max_hp=200, mana=30)
        session = MagicMock()
        session.character = ch
        session.player_data = {}
        prompt = p.playing_prompt(session)
        assert "45" in prompt
        assert "200" in prompt

    def test_playing_prompt_combat(self):
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        p = game_mod.ThreeEyesPlugin()
        ch = _player(hp=100, max_hp=200)
        enemy = _npc(hp=10)
        enemy.max_hp = 100
        ch.fighting = enemy
        session = MagicMock()
        session.character = ch
        session.player_data = {}
        prompt = p.playing_prompt(session)
        # Low HP enemy → should show condition
        assert "빈사" in prompt or "심각" in prompt

    def test_regen_char(self):
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        p = game_mod.ThreeEyesPlugin()
        ch = _player(hp=50, max_hp=200, mana=30, class_id=4)
        ch.max_mana = 200
        ch.move = 50
        ch.max_move = 100
        p.regen_char(None, ch)
        assert ch.hp > 50
        assert ch.mana > 30
        assert ch.move > 50

    def test_regen_barbarian_bonus(self):
        """Barbarian (class_id=2) gets +2 HP regen."""
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        p = game_mod.ThreeEyesPlugin()
        ch_barb = _player(hp=100, max_hp=500, mana=50, class_id=2)
        ch_barb.max_mana = 200
        ch_barb.move = 50
        ch_barb.max_move = 100
        ch_fighter = _player(hp=100, max_hp=500, mana=50, class_id=4)
        ch_fighter.max_mana = 200
        ch_fighter.move = 50
        ch_fighter.max_move = 100
        p.regen_char(None, ch_barb)
        p.regen_char(None, ch_fighter)
        assert ch_barb.hp > ch_fighter.hp  # Barbarian gets +2 HP

    def test_regen_mage_bonus(self):
        """Mage (class_id=5) gets +2 MP regen."""
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        p = game_mod.ThreeEyesPlugin()
        ch_mage = _player(hp=100, max_hp=500, mana=50, class_id=5)
        ch_mage.max_mana = 500
        ch_mage.move = 50
        ch_mage.max_move = 100
        ch_fighter = _player(hp=100, max_hp=500, mana=50, class_id=4)
        ch_fighter.max_mana = 500
        ch_fighter.move = 50
        ch_fighter.max_move = 100
        p.regen_char(None, ch_mage)
        p.regen_char(None, ch_fighter)
        assert ch_mage.mana > ch_fighter.mana  # Mage gets +2 MP


# ── Constants tests ───────────────────────────────────────────


class TestThreeEyesConstants:
    def test_classes(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        # 8 base + 9 advanced/admin = 17 total
        assert len(c.CLASS_NAMES) >= 8
        assert c.CLASS_NAMES[1] == "암살자"
        assert c.CLASS_NAMES[4] == "전사"
        assert c.CLASS_NAMES[5] == "마법사"
        assert c.CLASS_NAMES[8] == "도적"
        # Advanced classes
        assert c.CLASS_NAMES[c.INVINCIBLE] == "무적자"
        assert c.CLASS_NAMES[c.CARETAKER] == "보살핌자"

    def test_8_races(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        assert len(c.RACE_NAMES) == 8
        assert c.RACE_NAMES[1] == "드워프"
        assert c.RACE_NAMES[2] == "엘프"
        assert c.RACE_NAMES[5] == "인간"

    def test_proficiency_types(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        assert len(c.PROF_NAMES) == 5
        assert c.PROF_NAMES[0] == "날붙이"
        assert c.PROF_NAMES[4] == "원거리"

    def test_realm_types(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        assert len(c.REALM_NAMES) == 4
        assert c.REALM_NAMES[0] == "대지"
        assert c.REALM_NAMES[2] == "화염"

    def test_stat_bonus(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        assert c.get_stat_bonus(0) == -4
        assert c.get_stat_bonus(13) == 0
        assert c.get_stat_bonus(18) == 2
        assert c.get_stat_bonus(24) == 4
        assert c.get_stat_bonus(34) == 5

    def test_stat_bonus_out_of_range(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        # Values outside 0-34 should be clamped
        assert c.get_stat_bonus(-5) == -4  # clamped to 0
        assert c.get_stat_bonus(100) == 5  # clamped to 34 → STAT_BONUS[34]=5

    def test_level_cycle(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        # Fighter (4): mostly str/con with some dex
        assert c.LEVEL_CYCLE[4][0] == "str"
        assert c.LEVEL_CYCLE[4][1] == "con"
        # Mage (5): alternating int/pie
        assert c.LEVEL_CYCLE[5][0] == "int"
        assert c.LEVEL_CYCLE[5][1] == "pie"

    def test_class_stats(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        # Ranger (7) has highest HP
        assert c.CLASS_STATS[7]["hp_lv"] == 9
        assert c.CLASS_STATS[7]["mp_lv"] == 1
        # Mage (5) has highest MP
        assert c.CLASS_STATS[5]["mp_lv"] == 4
        assert c.CLASS_STATS[5]["hp_lv"] == 4

    def test_spirit_room(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        assert c.SPIRIT_ROOM == 11971
        assert c.MAX_MORTAL_LEVEL == 201

    def test_all_races_allow_all_classes(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        for race_id in range(1, 9):
            assert c.RACE_ALLOWED_CLASSES[race_id] == list(range(1, 9))


# ── Level system tests ────────────────────────────────────────


class TestThreeEyesLevel:
    def test_exp_table(self):
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        assert lv.exp_for_level(1) == 132
        assert lv.exp_for_level(10) == 1536
        assert lv.exp_for_level(100) == 1955600
        assert lv.exp_for_level(201) == 16000000

    def test_exp_table_level0(self):
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        # Level 0 is not in table → returns 0
        assert lv.exp_for_level(0) == 0

    def test_check_level_up(self):
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        ch = _player(level=1, exp=300)
        ch.level = 1
        ch.experience = 300  # Need 256 for level 2
        assert lv.check_level_up(ch)

    def test_check_level_up_not_enough(self):
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        ch = _player(level=1, exp=100)
        ch.level = 1
        ch.experience = 100  # Need 256 for level 2
        assert not lv.check_level_up(ch)

    def test_check_level_up_max_level(self):
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        ch = _player(level=201, exp=99999999)
        ch.level = 201
        ch.experience = 99999999
        assert not lv.check_level_up(ch)

    def test_check_level_up_npc(self):
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        mob = _npc(level=1, exp=99999)
        mob.experience = 99999
        assert not lv.check_level_up(mob)

    @pytest.mark.asyncio
    async def test_do_level_up(self):
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        ch = _player(level=1, class_id=4, exp=10000)
        ch.level = 1
        ch.stats = {"str": 15, "dex": 14, "con": 16, "int": 12, "pie": 13}
        send_fn = AsyncMock()
        gains = await lv.do_level_up(ch, send_fn=send_fn)
        assert ch.level == 2
        assert gains["hp"] > 0
        assert send_fn.called

    @pytest.mark.asyncio
    async def test_do_level_up_stat_cycling(self):
        """Fighter level 1→2: cycle[4][0] = 'str', so STR should increase."""
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        ch = _player(level=1, class_id=4, exp=10000)
        ch.level = 1
        ch.stats = {"str": 15, "dex": 14, "con": 16, "int": 12, "pie": 13}
        send_fn = AsyncMock()
        gains = await lv.do_level_up(ch, send_fn=send_fn)
        assert ch.level == 2
        # level 2 → (2-1) % 10 = 1 → cycle[4][1] = "con"
        # Actually level 1→2: char.level becomes 2, then stat_key = cycle[(2-1)%10] = cycle[1] = "con"
        assert gains.get("stat") == "con"
        assert ch.stats["con"] == 17  # was 16, +1

    @pytest.mark.asyncio
    async def test_do_level_up_mage_stat_cycling(self):
        """Mage level 1→2: cycle[5][0] = 'int'."""
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        ch = _player(level=1, class_id=5, exp=10000)
        ch.level = 1
        ch.stats = {"str": 10, "dex": 12, "con": 11, "int": 18, "pie": 16}
        send_fn = AsyncMock()
        gains = await lv.do_level_up(ch, send_fn=send_fn)
        # level becomes 2 → stat_key = cycle[5][(2-1)%10] = cycle[5][1] = "pie"
        assert gains.get("stat") == "pie"
        assert ch.stats["pie"] == 17

    def test_exp_to_next(self):
        import importlib
        lv = importlib.import_module("games.3eyes.level")
        ch = _player(level=1, exp=100)
        ch.level = 1
        ch.experience = 100
        needed = lv.exp_to_next(ch)
        # Level 2 needs 256, already have 100 → 156
        assert needed == 156


# ── Death system tests ────────────────────────────────────────


class TestThreeEyesDeath:
    @pytest.mark.asyncio
    async def test_npc_death_awards_exp(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=4, room_vnum=100, exp=0)
        mob = _npc(level=5, hp=1, gold=10, exp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        import importlib
        death = importlib.import_module("games.3eyes.combat.death")
        await death.handle_death(eng, mob, killer=ch)

        assert ch.experience > 0
        assert mob not in w.rooms[100].characters

    @pytest.mark.asyncio
    async def test_npc_death_gold_transfer(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=4, room_vnum=100, gold=50)
        mob = _npc(level=5, hp=1, gold=30, exp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        import importlib
        death = importlib.import_module("games.3eyes.combat.death")
        await death.handle_death(eng, mob, killer=ch)

        assert ch.gold == 80  # 50 + 30
        assert mob.gold == 0

    @pytest.mark.asyncio
    async def test_npc_death_proficiency_gain(self):
        """Killing NPC should increase proficiency values."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=4, room_vnum=100, exp=0)
        ch.extensions = {"proficiency": [0, 0, 0, 0, 0], "realm": [0, 0, 0, 0]}
        mob = _npc(level=5, hp=1, gold=0, exp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        import importlib
        death = importlib.import_module("games.3eyes.combat.death")
        await death.handle_death(eng, mob, killer=ch)

        # exp_gain = 200 * 0.5 (diff=-5) = 100. points = 100/20 = 5
        # Each proficiency type should have gained 5
        assert ch.extensions["proficiency"][0] > 0
        assert ch.extensions["proficiency"][4] > 0
        assert ch.extensions["realm"][0] > 0
        assert ch.extensions["realm"][3] > 0

    @pytest.mark.asyncio
    async def test_player_death_exp_penalty(self):
        """Player PvE death: exp penalty = (cur - prev) * 3/4."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=4, room_vnum=100, hp=0, max_hp=200,
                     exp=5000)
        ch.max_mana = 100
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        import importlib
        death = importlib.import_module("games.3eyes.combat.death")
        await death.handle_death(eng, ch, killer=None)

        assert ch.experience < 5000  # Lost exp
        assert ch.room_vnum == 11971  # Spirit room
        assert ch.hp == ch.max_hp  # Full HP recovery
        assert ch.mana == max(1, ch.max_mana // 10)  # 10% MP

    @pytest.mark.asyncio
    async def test_player_death_respawn(self):
        """Player death respawns to spirit room 11971."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=5, class_id=4, room_vnum=100, hp=0, max_hp=100)
        ch.max_mana = 50
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        import importlib
        death = importlib.import_module("games.3eyes.combat.death")
        await death.handle_death(eng, ch, killer=None)

        assert ch.room_vnum == 11971
        assert ch in w.rooms[11971].characters
        assert ch not in w.rooms[100].characters

    @pytest.mark.asyncio
    async def test_exp_gain_formula(self):
        """Test level difference modifiers."""
        import importlib
        death = importlib.import_module("games.3eyes.combat.death")

        killer = _player(level=10)
        # Higher level victim = more exp (1.5x)
        victim_high = _npc(level=20, exp=1000)
        assert death.calculate_exp_gain(killer, victim_high) == 1500

        # Same level = 1.0x
        victim_same = _npc(level=10, exp=1000)
        assert death.calculate_exp_gain(killer, victim_same) == 1000

        # Much lower level = 0.1x
        victim_low = _npc(level=1, exp=1000)
        assert death.calculate_exp_gain(killer, victim_low) == 100


# ── Combat system tests (THAC0/d30) ──────────────────────────


class TestThreeEyesCombat:
    def test_combat_round_hook_registered(self):
        eng = _make_engine()
        assert eng.lua.has_hook("combat_round")

    @pytest.mark.asyncio
    async def test_combat_round_deals_damage(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=50, class_id=4, room_vnum=100)
        mob = _npc(level=1, hp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        await eng._lua_combat_round()

        msgs = _get_sent(session)
        assert any("빗맞" in m or "에게" in m for m in msgs) or mob.hp < 200

    @pytest.mark.asyncio
    async def test_multi_attack_backswing(self):
        """Over many rounds, backswing (25%) should produce multi-attacks sometimes."""
        w = _make_world()
        eng = _make_engine(w)
        multi_attack_rounds = 0
        for _ in range(40):
            ch = _player(level=100, class_id=4, room_vnum=100)
            mob = _npc(level=1, hp=10000, room_vnum=100)
            session = _make_session(eng, ch)
            w.rooms[100].characters = [ch, mob]
            ch.fighting = mob
            mob.fighting = ch
            ch.position = 7
            await eng._lua_combat_round()
            msgs = _get_sent(session)
            # Count attack messages (타격 or 빗맞)
            atk_msgs = [m for m in msgs if "타격" in m or "빗맞" in m]
            if len(atk_msgs) >= 2:
                multi_attack_rounds += 1
            ch.fighting = None
        # Backswing is ~25%, so over 40 rounds we expect at least a few
        assert multi_attack_rounds >= 1

    @pytest.mark.asyncio
    async def test_combat_kills_npc(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=30, class_id=4, room_vnum=100, exp=0)
        mob = _npc(level=1, hp=1, gold=10, exp=200, room_vnum=100)
        # Set extremely bad AC so any d30 roll guarantees a hit
        # THAC0 needed = thac0 - AC/10 = ~16 - 1000 = -984, always hit
        mob.armor_class = 10000
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        await eng._lua_combat_round()

        assert ch.fighting is None
        assert mob not in w.rooms[100].characters
        assert ch.experience > 0


# ── Cast command tests ────────────────────────────────────────


class TestThreeEyesCast:
    @pytest.mark.asyncio
    async def test_cast_registered(self):
        eng = _make_engine()
        assert "cast" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_cast_no_args(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "cast")
        msgs = _get_sent(session)
        assert any("주문" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_unknown_spell(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "cast xyzzy")
        msgs = _get_sent(session)
        assert any("없습니다" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_fireball(self):
        """Mage casting fireball on target."""
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        # Seed Lua random for deterministic spell-fail check
        eng.lua._lua.execute("math.randomseed(42)")
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        mob = _npc(level=5, hp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        initial_mana = ch.mana
        await eng.process_command(session, "cast 화염구 고블린")
        assert ch.mana < initial_mana
        msgs = _get_sent(session)
        # Spell may succeed (damage) or fail (te_spell_fail check)
        assert ch.fighting is mob or mob.hp < 200 or any("실패" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_heal(self):
        """Cleric casting heal on self."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=20, class_id=3, mana=200, hp=50, max_hp=500,
                     room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "cast 활력")
        assert ch.hp > 50

    @pytest.mark.asyncio
    async def test_cast_not_enough_mana(self):
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=5, mana=0, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "cast 화염구 고블린")
        msgs = _get_sent(session)
        assert any("마력" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_fighter_limited(self):
        """Fighter can only cast spells with id <= 3."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=50, class_id=4, mana=100, room_vnum=100)
        mob = _npc(level=5, hp=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        await eng.process_command(session, "cast 화염구 고블린")
        msgs = _get_sent(session)
        assert any("직업" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_buff(self):
        """Casting a buff spell applies affect."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=15, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "cast 축복")
        has_buff = any(a.get("id") == 1004 for a in ch.affects)
        assert has_buff

    @pytest.mark.asyncio
    async def test_recall_command(self):
        """Recall command (귀환) teleports to start room."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=20, class_id=3, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        # "귀환" is registered as both a standalone command and a spell.
        # Standalone command takes priority in process_command.
        await eng.process_command(session, "귀환")
        msgs = _get_sent(session)
        # Player should be moved to start room
        assert ch.room_vnum != 100 or any("돌아" in m or "신전" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_realm_bonus_damage(self):
        """High realm proficiency should increase average spell damage.

        We cast many times and compare averages to account for randomness.
        """
        w = _make_world()
        eng = _make_engine(w)

        total_high = 0
        total_low = 0
        iterations = 100

        for _ in range(iterations):
            # With very high fire realm (2M exp → ~99%)
            ch = _player(level=20, class_id=5, mana=200, room_vnum=100)
            ch.extensions = {"proficiency": [0, 0, 0, 0, 0], "realm": [0, 0, 2000000, 0]}
            mob1 = _npc(level=1, hp=10000, room_vnum=100)
            session = _make_session(eng, ch)
            w.rooms[100].characters = [ch, mob1]
            await eng.process_command(session, "cast 화염구 고블린")
            total_high += 10000 - mob1.hp

            # Without realm
            ch2 = _player(level=20, class_id=5, mana=200, room_vnum=100)
            ch2.extensions = {"proficiency": [0, 0, 0, 0, 0], "realm": [0, 0, 0, 0]}
            mob2 = _npc(level=1, hp=10000, room_vnum=100)
            session2 = _make_session(eng, ch2)
            w.rooms[100].characters = [ch2, mob2]
            await eng.process_command(session2, "cast 화염구 고블린")
            total_low += 10000 - mob2.hp

        # Over 20 iterations, high realm should average more damage
        assert total_high > total_low

    @pytest.mark.asyncio
    async def test_teach_command(self):
        """Mage can teach spell to another player."""
        w = _make_world()
        eng = _make_engine(w)
        teacher = _player(level=30, class_id=5, mana=200, room_vnum=100)
        student = _player(level=10, class_id=3, mana=100, room_vnum=100)
        student.player_name = "학생"
        student.id = 2
        t_session = _make_session(eng, teacher)
        s_session = _make_session(eng, student)
        # Teacher must know the spell
        t_session.player_data["spells_known"] = [6]  # 화염구
        w.rooms[100].characters.extend([teacher, student])

        await eng.process_command(t_session, "가르쳐 화염구 학생")
        msgs = _get_sent(t_session)
        assert any("가르" in m for m in msgs)
        assert 6 in s_session.player_data["spells_known"]

    @pytest.mark.asyncio
    async def test_teach_fighter_cannot(self):
        """Fighter cannot teach spells."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=30, class_id=4, mana=200, room_vnum=100)
        target = _player(level=10, class_id=3, mana=100, room_vnum=100)
        target.player_name = "학생"
        target.id = 2
        session = _make_session(eng, ch)
        _make_session(eng, target)
        session.player_data["spells_known"] = [6]
        w.rooms[100].characters.extend([ch, target])

        await eng.process_command(session, "가르쳐 화염구 학생")
        msgs = _get_sent(session)
        assert any("마법사" in m or "성직자" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_study_scroll(self):
        """Study a scroll to learn a spell."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        # Create a scroll item
        scroll_proto = ItemProto(
            vnum=200, keywords="스크롤 화염", short_desc="화염구의 스크롤",
            long_desc="",
            item_type="scroll", weight=1, cost=100,
            values={"spell_id": 6, "level": 5},
            wear_slots=[], flags=[])
        scroll = ObjInstance(id=200, proto=scroll_proto, room_vnum=None)
        ch.inventory.append(scroll)

        await eng.process_command(session, "공부 스크롤")
        msgs = _get_sent(session)
        assert any("배우" in m or "능력" in m for m in msgs)
        assert 6 in session.player_data["spells_known"]

    @pytest.mark.asyncio
    async def test_study_not_scroll(self):
        """Cannot study non-scroll items."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        # Regular weapon, not a scroll
        sword_proto = ItemProto(
            vnum=300, keywords="검 장검", short_desc="장검",
            long_desc="",
            item_type="weapon", weight=5, cost=200,
            values={"damage": "2d4+1"},
            wear_slots=["wield"], flags=[])
        sword = ObjInstance(id=300, proto=sword_proto, room_vnum=None)
        ch.inventory.append(sword)

        await eng.process_command(session, "공부 검")
        msgs = _get_sent(session)
        assert any("스크롤" in m for m in msgs)


# ── Score/Info command tests ──────────────────────────────────


class TestThreeEyesInfo:
    @pytest.mark.asyncio
    async def test_score_shows_class(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=1, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        # Use 3eyes-specific "점수" command (detailed score with race/stats)
        await eng.process_command(session, "점수")
        msgs = _get_sent(session)
        assert any("암살자" in m for m in msgs)
        assert any("테스터" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_score_shows_race(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, race_id=2, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "점수")
        msgs = _get_sent(session)
        assert any("엘프" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_score_shows_proficiency(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)
        ch.extensions = {"proficiency": [200, 100, 0, 0, 0], "realm": [0, 0, 0, 0]}
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "점수")
        msgs = _get_sent(session)
        assert any("무기숙련" in m for m in msgs)
        assert any("날붙이" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_score_shows_realm(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        ch.extensions = {"proficiency": [0, 0, 0, 0, 0], "realm": [500, 0, 300, 0]}
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "점수")
        msgs = _get_sent(session)
        assert any("마법영역" in m for m in msgs)
        assert any("대지" in m for m in msgs)
        assert any("화염" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_score_shows_stats_with_bonus(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)
        ch.stats = {"str": 18, "dex": 14, "con": 16, "int": 12, "pie": 13}
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "점수")
        msgs = _get_sent(session)
        # STR 18 has bonus +2
        assert any("18" in m and "+2" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_practice_shows_header(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "practice")
        msgs = _get_sent(session)
        assert any("수련" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_practice_with_skills(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        session.player_data["skills"] = {"화염구": 75, "활력": 50}
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "practice")
        msgs = _get_sent(session)
        assert any("화염구" in m for m in msgs)
        assert any("활력" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_equipment_command(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "장비")
        msgs = _get_sent(session)
        assert any("장비" in m or "착용" in m for m in msgs)


# ── Login state tests ─────────────────────────────────────────


class TestThreeEyesLogin:
    def test_login_states_exist(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        assert login.ThreeEyesGetNameState().prompt()
        assert login.ThreeEyesSelectRaceState().prompt()

    def test_name_state_prompt(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesGetNameState()
        prompt = state.prompt()
        assert "이름" in prompt

    def test_gender_state(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesSelectGenderState()
        prompt = state.prompt()
        assert "남" in prompt
        assert "여" in prompt

    def test_class_selection_4_classes(self):
        """Original 4 classes: 도둑, 권법가, 마법사, 검사."""
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesSelectClassState()
        prompt = state.prompt()
        assert "도  둑" in prompt or "도둑" in prompt.replace(" ", "")
        assert "권법가" in prompt
        assert "마법사" in prompt
        assert "검  사" in prompt or "검사" in prompt.replace(" ", "")

    def test_race_selection_4_races(self):
        """Original 4 races: 요정족, 드래곤족, 인간족, 마족."""
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesSelectRaceState()
        prompt = state.prompt()
        assert "요정족" in prompt
        assert "드래곤족" in prompt
        assert "인간족" in prompt
        assert "마족" in prompt

    def test_confirm_new_state(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesConfirmNewState("테스터")
        prompt = state.prompt()
        assert "테스터" in prompt
        assert "만드시겠습니까" in prompt

    def test_password_state_prompt(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesGetPasswordState()
        prompt = state.prompt()
        assert "암호" in prompt

    def test_set_password_state_prompt(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesSetPasswordState()
        prompt = state.prompt()
        assert "암호" in prompt
        assert "5자" in prompt

    def test_main_menu_state(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesMainMenuState()
        prompt = state.prompt()
        assert "제3의눈" in prompt or "메뉴" in prompt


# ── Stealth command tests ─────────────────────────────────────


class TestThreeEyesStealth:
    @pytest.mark.asyncio
    async def test_backstab_registered(self):
        eng = _make_engine()
        assert "기습" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_backstab_class_restriction(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)  # Fighter
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "기습 test")
        msgs = _get_sent(session)
        assert any("암살자" in m or "도적" in m or "기습" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_sneak_registered(self):
        eng = _make_engine()
        assert "숨어" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_steal_registered(self):
        eng = _make_engine()
        assert "훔쳐" in eng.cmd_handlers


# ── Shop command tests ────────────────────────────────────────


class TestThreeEyesShops:
    @pytest.mark.asyncio
    async def test_sell_command_registered(self):
        eng = _make_engine()
        assert "팔아" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_list_command_registered(self):
        eng = _make_engine()
        assert "품목" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_appraise_command_registered(self):
        eng = _make_engine()
        assert "가치" in eng.cmd_handlers


# ── Korean command mapping tests ──────────────────────────────


class TestThreeEyesKorean:
    @pytest.mark.asyncio
    async def test_korean_score(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "건강")
        msgs = _get_sent(session)
        assert any("전사" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_korean_cast(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "시전")
        msgs = _get_sent(session)
        assert any("주문" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_korean_practice(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        # "배워" is the 3eyes practice command
        await eng.process_command(session, "배워")
        msgs = _get_sent(session)
        assert any("수련" in m for m in msgs)


# ── Phase 0: Infrastructure tests ───────────────────────────


class TestPhase0SpellKnown:
    """S_ISSET/S_SET/S_CLR spell bitfield system."""

    @pytest.mark.asyncio
    async def test_knows_spell_false_by_default(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        assert not ctx.knows_spell(6)  # fireball

    @pytest.mark.asyncio
    async def test_learn_and_check_spell(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        ctx.learn_spell(6)
        assert ctx.knows_spell(6)
        assert not ctx.knows_spell(7)

    @pytest.mark.asyncio
    async def test_forget_spell(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        ctx.learn_spell(6)
        ctx.learn_spell(8)
        ctx.forget_spell(6)
        assert not ctx.knows_spell(6)
        assert ctx.knows_spell(8)

    @pytest.mark.asyncio
    async def test_learn_spell_idempotent(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        ctx.learn_spell(6)
        ctx.learn_spell(6)
        assert session.player_data["spells_known"].count(6) == 1


class TestPhase0Cooldown:
    """Lasttime cooldown system (45 slots)."""

    @pytest.mark.asyncio
    async def test_no_cooldown_initially(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        assert ctx.check_cooldown(1) == 0  # LT_SPELL

    @pytest.mark.asyncio
    async def test_set_and_check_cooldown(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        ctx.set_cooldown(1, 5)
        remaining = ctx.check_cooldown(1)
        assert 4 <= remaining <= 5  # within 1 sec tolerance

    @pytest.mark.asyncio
    async def test_clear_cooldown(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        ctx.set_cooldown(1, 60)
        ctx.clear_cooldown(1)
        assert ctx.check_cooldown(1) == 0


class TestPhase0Flags:
    """Creature flags system (F_ISSET/F_SET/F_CLR)."""

    @pytest.mark.asyncio
    async def test_no_flags_initially(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        assert not ctx.has_flag(0)  # PBLESS

    @pytest.mark.asyncio
    async def test_set_and_check_flag(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        ctx.set_flag(0)  # PBLESS
        assert ctx.has_flag(0)
        assert not ctx.has_flag(1)  # PHIDDN

    @pytest.mark.asyncio
    async def test_clear_flag(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        ctx.set_flag(0)
        ctx.set_flag(5)  # PBLIND
        ctx.clear_flag(0)
        assert not ctx.has_flag(0)
        assert ctx.has_flag(5)

    @pytest.mark.asyncio
    async def test_set_flag_idempotent(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        ctx = CommandContext(session, eng)
        ctx.set_flag(0)
        ctx.set_flag(0)
        assert session.player_data["flags"].count(0) == 1


class TestPhase0ProficCalc:
    """Proficiency/realm percent calculation from raw experience."""

    def test_raw_to_percent_zero(self):
        import importlib; c = importlib.import_module("games.3eyes.constants")
        assert c.raw_to_percent(0, c.PROF_TABLE_FIGHTER) == 0

    def test_raw_to_percent_max(self):
        import importlib; c = importlib.import_module("games.3eyes.constants")
        assert c.raw_to_percent(500000000, c.PROF_TABLE_FIGHTER) == 100

    def test_raw_to_percent_mid_fighter(self):
        import importlib; c = importlib.import_module("games.3eyes.constants")
        # 768 is boundary of first tier → exactly 10%
        assert c.raw_to_percent(768, c.PROF_TABLE_FIGHTER) == 10

    def test_raw_to_percent_interpolated(self):
        import importlib; c = importlib.import_module("games.3eyes.constants")
        # Between 0 and 768, midpoint 384 → 5%
        pct = c.raw_to_percent(384, c.PROF_TABLE_FIGHTER)
        assert pct == 5

    def test_comp_chance_low_level(self):
        import importlib; c = importlib.import_module("games.3eyes.constants")
        assert c.comp_chance(10, c.FIGHTER) == 1  # 10/6 = 1

    def test_comp_chance_invincible(self):
        import importlib; c = importlib.import_module("games.3eyes.constants")
        # Invincible level 100: (100+150)/6 = 41
        assert c.comp_chance(100, c.INVINCIBLE) == 41

    def test_comp_chance_caretaker(self):
        import importlib; c = importlib.import_module("games.3eyes.constants")
        # Caretaker level 100: (100+150+150)/6 = 66
        assert c.comp_chance(100, c.CARETAKER) == 66

    def test_comp_chance_cap_80(self):
        import importlib; c = importlib.import_module("games.3eyes.constants")
        # Very high level should cap at 80
        assert c.comp_chance(200, c.CARETAKER) == 80


class TestPhase0LibLua:
    """Test lib.lua functions via engine Lua runtime."""

    @pytest.mark.asyncio
    async def test_te_compute_thaco_fighter(self):
        eng = _make_engine()
        ch = _player(level=50, class_id=4, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)
        # Invoke thaco via Lua
        thaco = eng.lua._lua.eval("""
            (function()
                local mob = {level=50, class_id=4, is_npc=false,
                    stats={str=15}, equipment={}}
                return te_compute_thaco(mob)
            end)()
        """)
        # Fighter level 50: table index 5 → 15, minus STR bonus 1 = 14
        assert thaco <= 15

    @pytest.mark.asyncio
    async def test_te_spell_fail_mage(self):
        """Mage has high base chance, should succeed often."""
        eng = _make_engine()
        ch = _player(level=100, class_id=5, room_vnum=100)
        session = _make_session(eng, ch)
        # Test over many trials
        successes = 0
        for _ in range(100):
            result = eng.lua._lua.eval("""
                (function()
                    local mob = {level=100, class_id=5,
                        stats={int=18}, session={player_data={}}}
                    return te_spell_fail(mob)
                end)()
            """)
            if not result:
                successes += 1
        # Mage level 100 with INT 18: (16+2)*5+75 = 165 → always succeeds
        assert successes > 90

    @pytest.mark.asyncio
    async def test_te_profic_zero_raw(self):
        eng = _make_engine()
        result = eng.lua._lua.eval("""
            (function()
                local mob = {class_id=4, extensions={proficiency={[0]=0,[1]=0,[2]=0,[3]=0,[4]=0}}}
                return te_profic(mob, 0)
            end)()
        """)
        assert result == 0

    @pytest.mark.asyncio
    async def test_te_profic_high_raw(self):
        eng = _make_engine()
        result = eng.lua._lua.eval("""
            (function()
                local mob = {class_id=4, extensions={proficiency={[0]=500000000,[1]=0,[2]=0,[3]=0,[4]=0}}}
                return te_profic(mob, 0)
            end)()
        """)
        assert result == 100


# ── Phase 1: Combat system tests ────────────────────────────


class TestPhase1CombatOriginal:
    """Test original-faithful combat formulas from attack_crt()."""

    @pytest.mark.asyncio
    async def test_npc_thaco_uses_table(self):
        """NPC THAC0 should use class table, not always 20."""
        eng = _make_engine()
        result = eng.lua._lua.eval("""
            (function()
                local npc = {level=100, class_id=4, is_npc=true}
                return te_compute_thaco(npc)
            end)()
        """)
        # Fighter NPC level 100: index 10 → 10, not 20
        assert result < 20

    @pytest.mark.asyncio
    async def test_pfears_penalty(self):
        """PFEARS flag should add +2 to needed hit roll (harder to hit)."""
        w = _make_world()
        eng = _make_engine(w)
        total_dmg_normal = 0
        total_dmg_feared = 0

        for _ in range(150):
            # Normal vs negative AC → need=18+8=26, hit ~17%
            ch = _player(level=20, class_id=4, room_vnum=100)
            mob = _npc(level=1, hp=5000, room_vnum=100)
            mob.armor_class = -80
            session = _make_session(eng, ch)
            w.rooms[100].characters = [ch, mob]
            ch.fighting = mob; mob.fighting = ch; ch.position = 7
            await eng._lua_combat_round()
            total_dmg_normal += 5000 - mob.hp
            ch.fighting = None

            # Feared: +2 penalty → need=28, hit ~10%
            ch2 = _player(level=20, class_id=4, room_vnum=100)
            mob2 = _npc(level=1, hp=5000, room_vnum=100)
            mob2.armor_class = -80
            session2 = _make_session(eng, ch2)
            session2.player_data["flags"] = [7]  # PFEARS=7
            w.rooms[100].characters = [ch2, mob2]
            ch2.fighting = mob2; mob2.fighting = ch2; ch2.position = 7
            await eng._lua_combat_round()
            total_dmg_feared += 5000 - mob2.hp
            ch2.fighting = None

        # Over 150 rounds, feared should deal less damage (10% vs 17% hit)
        assert total_dmg_normal > total_dmg_feared

    @pytest.mark.asyncio
    async def test_mage_no_profic_bonus(self):
        """Mage should not get proficiency bonus on weapon damage."""
        eng = _make_engine()
        # Mage with weapon but high proficiency
        result_mage = eng.lua._lua.eval("""
            (function()
                local weapon = {proto={damage_dice="1d4+0", values={weapon_type=0}, act_flags={}}, name="단검"}
                local mob = {level=50, class_id=5, is_npc=false,
                    stats={str=13}, equipment={[16]=weapon},
                    extensions={proficiency={[0]=500000000,[1]=0,[2]=0,[3]=0,[4]=0}}}
                return te_compute_thaco(mob)
            end)()
        """)
        result_fighter = eng.lua._lua.eval("""
            (function()
                local weapon = {proto={damage_dice="1d4+0", values={weapon_type=0}, act_flags={}}, name="단검"}
                local mob = {level=50, class_id=4, is_npc=false,
                    stats={str=13}, equipment={[16]=weapon},
                    extensions={proficiency={[0]=500000000,[1]=0,[2]=0,[3]=0,[4]=0}}}
                return te_compute_thaco(mob)
            end)()
        """)
        # Mage gets no proficiency reduction, fighter does (100/20 = 5)
        assert result_mage > result_fighter

    @pytest.mark.asyncio
    async def test_pbless_thaco_bonus(self):
        """PBLESS should give -3 THAC0 bonus."""
        eng = _make_engine()
        ch = _player(level=50, class_id=4, room_vnum=100)
        session_normal = _make_session(eng, ch)

        ch2 = _player(level=50, class_id=4, room_vnum=100)
        session_blessed = _make_session(eng, ch2)
        session_blessed.player_data["flags"] = [0]  # PBLESS=0

        # Can't easily test via Lua eval since it needs session mock,
        # but we can test over many combat rounds
        w = _make_world()
        eng2 = _make_engine(w)
        total_dmg_normal = 0
        total_dmg_blessed = 0

        for _ in range(100):
            # Normal vs negative AC (hard to hit)
            ch_n = _player(level=20, class_id=4, room_vnum=100)
            mob_n = _npc(level=1, hp=5000, room_vnum=100)
            mob_n.armor_class = -60  # Good AC → need=18+6=24, hit ~20%
            s_n = _make_session(eng2, ch_n)
            w.rooms[100].characters = [ch_n, mob_n]
            ch_n.fighting = mob_n; mob_n.fighting = ch_n; ch_n.position = 7
            await eng2._lua_combat_round()
            total_dmg_normal += 5000 - mob_n.hp
            ch_n.fighting = None

            # Blessed: thaco-3 → need=15+6=21, hit ~33%
            ch_b = _player(level=20, class_id=4, room_vnum=100)
            mob_b = _npc(level=1, hp=5000, room_vnum=100)
            mob_b.armor_class = -60
            s_b = _make_session(eng2, ch_b)
            s_b.player_data["flags"] = [0]
            w.rooms[100].characters = [ch_b, mob_b]
            ch_b.fighting = mob_b; mob_b.fighting = ch_b; ch_b.position = 7
            await eng2._lua_combat_round()
            total_dmg_blessed += 5000 - mob_b.hp
            ch_b.fighting = None

        # Blessed should deal more total damage (33% vs 20% hit rate)
        assert total_dmg_blessed > total_dmg_normal

    @pytest.mark.asyncio
    async def test_combat_death_message(self):
        """Death should produce << 죽었습니다 >> message."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=50, class_id=4, room_vnum=100)
        mob = _npc(level=1, hp=1, room_vnum=100)
        mob.armor_class = 10000
        session = _make_session(eng, ch)
        w.rooms[100].characters = [ch, mob]
        ch.fighting = mob; mob.fighting = ch; ch.position = 7
        await eng._lua_combat_round()
        msgs = _get_sent(session)
        assert any("죽었습니다" in m for m in msgs)


# ══════════════════════════════════════════════════════════════════════
# Phase: New Batch Commands (방향, 소셜, 별칭, 핵심, KYK, 편지, DM)
# ══════════════════════════════════════════════════════════════════════


class TestBatchEmotes:
    """Batch 2: 소셜/감정 명령어."""

    @pytest.mark.asyncio
    async def test_emote_no_target(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters = [ch]
        await eng.process_command(session, "미소")
        msgs = _get_sent(session)
        assert any("미소" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_emote_with_target(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        mob = _npc(room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters = [ch, mob]
        await eng.process_command(session, "절 고블린")
        msgs = _get_sent(session)
        assert any("절" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_emote_target_only_no_args(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters = [ch]
        await eng.process_command(session, "안아")
        msgs = _get_sent(session)
        assert any("누구" in m for m in msgs)


class TestBatchAliases:
    """Batch 3: 단순 별칭."""

    @pytest.mark.asyncio
    async def test_bwa_alias(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters = [ch]
        await eng.process_command(session, "봐")
        msgs = _get_sent(session)
        assert any("광장" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_news_alias(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        await eng.process_command(session, "뉴스")
        msgs = _get_sent(session)
        assert any("3eyes" in m or "GenOS" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_title_delete(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        session.player_data["title"] = "용사"
        await eng.process_command(session, "칭호삭제")
        assert session.player_data.get("title") == ""


class TestBatchCoreCommands:
    """Batch 4: 핵심 미구현 명령어."""

    @pytest.mark.asyncio
    async def test_ignore_add_remove(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        # 추가
        await eng.process_command(session, "듣기거부 badplayer")
        msgs = _get_sent(session)
        assert any("수신거부합니다" in m for m in msgs)
        # 해제 (같은 명령 재실행)
        session.send_line.reset_mock()
        await eng.process_command(session, "듣기거부 badplayer")
        msgs = _get_sent(session)
        assert any("해제했습니다" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_clear_cast(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        ch.extensions["casting"] = True
        session = _make_session(eng, ch)
        await eng.process_command(session, "주문해제")
        msgs = _get_sent(session)
        assert any("취소" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_description_set(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        await eng.process_command(session, "묘사 용감한 전사입니다.")
        assert session.player_data.get("description") == "용감한 전사입니다."

    @pytest.mark.asyncio
    async def test_item_appraise(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        proto = ItemProto(
            vnum=101, keywords="검 sword", short_desc="강철검", long_desc="",
            item_type="weapon", wear_slots=["wield"], weight=5, cost=1000,
            values={"damage": "2d6"}, flags=[], scripts=[], ext={},
        )
        item = ObjInstance(id=201, proto=proto, room_vnum=-1)
        ch.inventory = [item]
        await eng.process_command(session, "감정 검")
        msgs = _get_sent(session)
        assert any("감정" in m for m in msgs)


class TestBatchKYK:
    """Batch 5: KYK 특수 시스템."""

    @pytest.mark.asyncio
    async def test_stat_upgrade(self):
        eng = _make_engine()
        ch = _player(level=50, gold=300000, room_vnum=100)
        session = _make_session(eng, ch)
        await eng.process_command(session, "향상 str")
        msgs = _get_sent(session)
        assert any("향상되었습니다" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_pray_cleric(self):
        eng = _make_engine()
        ch = _player(level=30, class_id=3, mana=100, hp=50, max_hp=200, room_vnum=100)
        session = _make_session(eng, ch)
        session.player_data["cooldowns"] = {}
        old_hp = ch.hp
        await eng.process_command(session, "신원법")
        assert ch.hp > old_hp

    @pytest.mark.asyncio
    async def test_memo_save(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        await eng.process_command(session, "메모 중요한내용")
        msgs = _get_sent(session)
        assert any("저장되었습니다" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_exp_transfer(self):
        eng = _make_engine()
        ch = _player(level=50, exp=10000, room_vnum=100)
        session = _make_session(eng, ch)
        # 대상 없이 테스트 - 메시지만 확인
        await eng.process_command(session, "경험치전수 없는사람 1000")
        msgs = _get_sent(session)
        assert any("없" in m or "전수" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_item_destroy(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        proto = ItemProto(
            vnum=102, keywords="쓰레기 trash", short_desc="쓰레기",
            long_desc="", item_type="misc", wear_slots=[], weight=1, cost=0,
            values={}, flags=[], scripts=[], ext={},
        )
        item = ObjInstance(id=202, proto=proto, room_vnum=-1)
        ch.inventory = [item]
        await eng.process_command(session, "긁어 쓰레기")
        msgs = _get_sent(session)
        assert any("긁어" in m or "부숩" in m for m in msgs)


class TestBatchMail:
    """Batch 7: 편지 시스템."""

    @pytest.mark.asyncio
    async def test_mail_send_and_read(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        # 편지 보내기
        await eng.process_command(session, "편지보내기 친구 인사 안녕하세요!")
        msgs = _get_sent(session)
        assert any("편지" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_mail_read_empty(self):
        eng = _make_engine()
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        import lupa
        lupa.LuaRuntime().execute("_G._3eyes_mailbox = nil")
        await eng.process_command(session, "편지받기")
        msgs = _get_sent(session)
        assert any("없습니다" in m for m in msgs)


class TestBatchDMCommands:
    """Batch 6: DM 관리 명령어."""

    @pytest.mark.asyncio
    async def test_dm_alias_echo(self):
        eng = _make_engine()
        ch = _player(level=100, class_id=16, room_vnum=100)  # DM
        session = _make_session(eng, ch)
        eng.sessions["s1"] = session  # send_all needs session in sessions
        await eng.process_command(session, "*공지 테스트메시지")
        msgs = _get_sent(session)
        assert any("테스트메시지" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_dm_system(self):
        eng = _make_engine()
        ch = _player(level=100, class_id=16, room_vnum=100)
        session = _make_session(eng, ch)
        await eng.process_command(session, "*dm_system")
        msgs = _get_sent(session)
        assert any("Lua" in m or "시스템" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_dm_denied_for_non_dm(self):
        eng = _make_engine()
        ch = _player(level=50, class_id=4, room_vnum=100)
        session = _make_session(eng, ch)
        await eng.process_command(session, "*순간이동 999")
        msgs = _get_sent(session)
        assert any("관리자" in m for m in msgs)


class TestBatchMovement:
    """Batch 1: 방향 이동 별칭 & 나가/나가는길."""

    @pytest.mark.asyncio
    async def test_exit_list(self):
        eng = _make_engine()
        w = eng.world
        # Add an exit to room 100
        room100 = w.rooms[100]
        room100.proto.exits.append(
            Exit(direction=0, to_vnum=1, keywords="", flags=[])
        )
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters = [ch]
        await eng.process_command(session, "나가는길")
        msgs = _get_sent(session)
        assert any("북" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_leave_command(self):
        eng = _make_engine()
        w = eng.world
        room100 = w.rooms[100]
        room100.proto.exits.append(
            Exit(direction=2, to_vnum=1, keywords="", flags=[])
        )
        ch = _player(room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters = [ch]
        w.rooms[1].characters = []
        await eng.process_command(session, "나가")
        assert ch.room_vnum == 1

    def test_dir_map_has_diagonals(self):
        from core.engine import DIR_NAMES_KR_MAP
        assert DIR_NAMES_KR_MAP["남동"] == 6
        assert DIR_NAMES_KR_MAP["북서"] == 9
        assert DIR_NAMES_KR_MAP["밑"] == 5
        assert DIR_NAMES_KR_MAP["8"] == 0  # numpad north
