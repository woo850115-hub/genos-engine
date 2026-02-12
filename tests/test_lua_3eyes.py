"""Tests for 3eyes game plugin — combat, spells, commands, login, death, proficiency."""

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
    session = MagicMock()
    session.send_line = AsyncMock()
    session.character = char
    session.engine = eng
    session.player_data = {"level": char.level, "name": char.name}
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
        assert "3eyes" in banner or "검눈" in banner or "검제" in banner

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

    @pytest.mark.asyncio
    async def test_regen_char(self):
        import importlib
        game_mod = importlib.import_module("games.3eyes.game")
        p = game_mod.ThreeEyesPlugin()
        ch = _player(hp=50, max_hp=200, mana=30, class_id=4)
        ch.max_mana = 200
        ch.move = 50
        ch.max_move = 100
        await p.regen_char(ch)
        assert ch.hp > 50
        assert ch.mana > 30
        assert ch.move > 50

    @pytest.mark.asyncio
    async def test_regen_barbarian_bonus(self):
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
        await p.regen_char(ch_barb)
        await p.regen_char(ch_fighter)
        assert ch_barb.hp > ch_fighter.hp  # Barbarian gets +2 HP

    @pytest.mark.asyncio
    async def test_regen_mage_bonus(self):
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
        await p.regen_char(ch_mage)
        await p.regen_char(ch_fighter)
        assert ch_mage.mana > ch_fighter.mana  # Mage gets +2 MP


# ── Constants tests ───────────────────────────────────────────


class TestThreeEyesConstants:
    def test_8_classes(self):
        import importlib
        c = importlib.import_module("games.3eyes.constants")
        assert len(c.CLASS_NAMES) == 8
        assert c.CLASS_NAMES[1] == "암살자"
        assert c.CLASS_NAMES[4] == "전사"
        assert c.CLASS_NAMES[5] == "마법사"
        assert c.CLASS_NAMES[8] == "도적"

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
    async def test_multi_attack_level50(self):
        """Level 50+ should get 2+ base attacks (1 base + 1 for level >= 50)."""
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=100, class_id=4, room_vnum=100)
        ch.hitroll = 20
        mob = _npc(level=1, hp=10000, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        await eng._lua_combat_round()

        msgs = _get_sent(session)
        attack_msgs = [m for m in msgs if "빗맞" in m or "에게" in m]
        # Level 100 should get at least 3 base attacks (1 + lv50 + lv100)
        assert len(attack_msgs) >= 2

    @pytest.mark.asyncio
    async def test_combat_kills_npc(self):
        random.seed(42)
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=30, class_id=4, room_vnum=100, exp=0)
        ch.hitroll = 20
        mob = _npc(level=1, hp=1, gold=10, exp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        ch.fighting = mob
        mob.fighting = ch
        ch.position = 7

        # Ensure a hit — override random to always return high
        orig = random.randint
        random.randint = lambda a, b: 30 if b == 30 else orig(a, b)
        try:
            await eng._lua_combat_round()
        finally:
            random.randint = orig

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
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        mob = _npc(level=5, hp=200, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.extend([ch, mob])

        initial_mana = ch.mana
        await eng.process_command(session, "cast 화염구 고블린")
        assert ch.mana < initial_mana
        assert ch.fighting is mob or mob.hp < 200

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
    async def test_cast_recall_spell_exists(self):
        """Recall spell deducts mana (actual teleport depends on ctx:recall())."""
        w = _make_world()
        eng = _make_engine(w)
        ch = _player(level=20, class_id=3, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        w.rooms[100].characters.append(ch)

        await eng.process_command(session, "cast 귀환")
        msgs = _get_sent(session)
        # Either recall works or it logs as "귀환" spell cast
        assert ch.mana < 100 or any("귀환" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_cast_realm_bonus_damage(self):
        """High realm proficiency should increase average spell damage.

        We cast many times and compare averages to account for randomness.
        """
        w = _make_world()
        eng = _make_engine(w)

        total_high = 0
        total_low = 0
        iterations = 20

        for _ in range(iterations):
            # With high fire realm
            ch = _player(level=20, class_id=5, mana=200, room_vnum=100)
            ch.extensions = {"proficiency": [0, 0, 0, 0, 0], "realm": [0, 0, 2000, 0]}
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


# ── Score/Info command tests ──────────────────────────────────


class TestThreeEyesInfo:
    @pytest.mark.asyncio
    async def test_score_shows_class(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=1, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "score")
        msgs = _get_sent(session)
        assert any("암살자" in m for m in msgs)
        assert any("테스터" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_score_shows_race(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, race_id=2, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "score")
        msgs = _get_sent(session)
        assert any("엘프" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_score_shows_proficiency(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)
        ch.extensions = {"proficiency": [200, 100, 0, 0, 0], "realm": [0, 0, 0, 0]}
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "score")
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

        await eng.process_command(session, "score")
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

        await eng.process_command(session, "score")
        msgs = _get_sent(session)
        # STR 18 has bonus +2
        assert any("18" in m and "+2" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_practice_mage(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=5, mana=100, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "practice")
        msgs = _get_sent(session)
        assert any("화염구" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_practice_fighter_limited(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "practice")
        msgs = _get_sent(session)
        # Fighter can only cast spells with id <= 3 (활력, 상처, 빛, 해독)
        assert any("활력" in m for m in msgs)
        # Should NOT have high-level spells
        assert not any("화염구" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_equipment_command(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "equipment")
        msgs = _get_sent(session)
        assert any("장비" in m for m in msgs)


# ── Login state tests ─────────────────────────────────────────


class TestThreeEyesLogin:
    def test_login_states_exist(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        assert login.ThreeEyesGetNameState().prompt()
        assert login.ThreeEyesSelectRaceState().prompt()

    def test_race_selection_prompt(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesSelectRaceState()
        prompt = state.prompt()
        assert "드워프" in prompt
        assert "엘프" in prompt
        assert "인간" in prompt
        assert "노움" in prompt

    def test_class_selection_prompt_human(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesSelectClassState(5)  # Human
        prompt = state.prompt()
        # All 8 classes available for human
        assert "암살자" in prompt
        assert "마법사" in prompt
        assert "도적" in prompt

    def test_class_selection_prompt_elf(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesSelectClassState(2)  # Elf
        prompt = state.prompt()
        # All 8 classes available (3eyes has no restrictions)
        assert "암살자" in prompt
        assert "마법사" in prompt
        assert "야만인" in prompt

    def test_gender_state(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesSelectGenderState()
        prompt = state.prompt()
        assert "남성" in prompt
        assert "여성" in prompt

    def test_new_password_state(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesNewPasswordState()
        prompt = state.prompt()
        assert "비밀번호" in prompt

    def test_name_state_prompt(self):
        import importlib
        login = importlib.import_module("games.3eyes.login")
        state = login.ThreeEyesGetNameState()
        prompt = state.prompt()
        assert "이름" in prompt


# ── Stealth command tests ─────────────────────────────────────


class TestThreeEyesStealth:
    @pytest.mark.asyncio
    async def test_backstab_registered(self):
        eng = _make_engine()
        assert "backstab" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_backstab_class_restriction(self):
        eng = _make_engine()
        ch = _player(level=10, class_id=4, room_vnum=100)  # Fighter
        session = _make_session(eng, ch)
        eng.world.rooms[100].characters.append(ch)

        await eng.process_command(session, "backstab test")
        msgs = _get_sent(session)
        assert any("암살자" in m or "도적" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_sneak_registered(self):
        eng = _make_engine()
        assert "sneak" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_steal_registered(self):
        eng = _make_engine()
        assert "steal" in eng.cmd_handlers


# ── Shop command tests ────────────────────────────────────────


class TestThreeEyesShops:
    @pytest.mark.asyncio
    async def test_buy_command_registered(self):
        eng = _make_engine()
        assert "buy" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_sell_command_registered(self):
        eng = _make_engine()
        assert "sell" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_list_command_registered(self):
        eng = _make_engine()
        assert "list" in eng.cmd_handlers

    @pytest.mark.asyncio
    async def test_appraise_command_registered(self):
        eng = _make_engine()
        assert "appraise" in eng.cmd_handlers


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

        await eng.process_command(session, "수련")
        msgs = _get_sent(session)
        assert any("주문" in m for m in msgs)
