"""10woongi integration tests — E2E scenarios without DB."""

import importlib
import random

import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine
from core.world import (
    Exit, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World, Zone, _next_id,
)
from core.ansi import colorize
from core.korean import has_batchim, particle, render_message


def _import(submodule: str):
    return importlib.import_module(f"games.10woongi.{submodule}")


# ── Helper factories ───────────────────────────────────────────────


def _make_10w_world():
    """World with 10woongi-style rooms (SHA-256 VNUMs + dir/dest exits)."""
    w = World()

    START = 1392841419
    VOID = 1854941986
    ROOM_B = 998877665

    r1 = RoomProto(
        vnum=START, name="장백성 마을 광장",
        description="드넓은 광장 한가운데 커다란 느티나무가 서 있습니다.",
        zone_vnum=1, sector=0, flags=[],
        exits=[Exit(direction=1, to_vnum=ROOM_B)],  # east
        extra_descs=[], scripts=[], ext={})
    r2 = RoomProto(
        vnum=ROOM_B, name="장백성 무기점 앞",
        description="무기점 앞 대로입니다.",
        zone_vnum=1, sector=0, flags=[],
        exits=[Exit(direction=3, to_vnum=START)],  # west
        extra_descs=[], scripts=[], ext={})
    r_void = RoomProto(
        vnum=VOID, name="대기실",
        description="영혼이 머무는 공간입니다.",
        zone_vnum=0, sector=0, flags=[],
        exits=[], extra_descs=[], scripts=[], ext={})

    w.rooms[START] = Room(proto=r1)
    w.rooms[ROOM_B] = Room(proto=r2)
    w.rooms[VOID] = Room(proto=r_void)

    # Zone (zones is a list, not dict)
    w.zones.append(Zone(
        vnum=1, name="장백성", builders="", lifespan=30, reset_mode=2, flags=[],
        resets=[], ext={}))

    # Mob: 산적
    bandit = MobProto(
        vnum=500, keywords="산적 bandit", short_desc="산적",
        long_desc="산적이 어슬렁거리고 있습니다.",
        detail_desc="험악한 인상의 산적입니다.",
        level=8, hitroll=3, armor_class=60,
        max_hp=25, damage_dice="1d6+2",
        gold=50, experience=300,
        act_flags=["ISNPC"], aff_flags=[], alignment=-200, sex=1,
        scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
    w.mob_protos[500] = bandit

    bandit_mob = MobInstance(
        id=_next_id(), proto=bandit, room_vnum=ROOM_B,
        hp=30, max_hp=30,
    )
    w.rooms[ROOM_B].characters.append(bandit_mob)

    # Item: 단검
    dagger = ItemProto(
        vnum=600, keywords="단검 dagger",
        short_desc="녹슨 단검",
        long_desc="녹슨 단검이 바닥에 놓여 있습니다.",
        item_type="weapon", flags=[], wear_slots=["13"],  # wield
        values={}, weight=3, cost=20,
        affects=[], extra_descs=[], scripts=[], min_level=0, ext={})
    w.item_protos[600] = dagger

    dagger_obj = ObjInstance(
        id=_next_id(), proto=dagger, values=dict(dagger.values),
    )
    dagger_obj.room_vnum = START
    w.rooms[START].objects.append(dagger_obj)

    return w


def _make_pc(room_vnum=1392841419, level=10, class_id=1):
    proto = MobProto(
        vnum=-1, keywords="무사 player", short_desc="무사",
        long_desc="", detail_desc="",
        level=level, hitroll=5, armor_class=50,
        max_hp=100, damage_dice="1d6+3",
        gold=1000, experience=5000,
        act_flags=[], aff_flags=[], alignment=0, sex=1, scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
    char = MobInstance(
        id=_next_id(), proto=proto, room_vnum=room_vnum,
        hp=200, max_hp=200, player_id=1, player_name="무사",
    )
    char.player_level = level
    char.mana = 80
    char.max_mana = 80
    char.move = 100
    char.max_move = 100
    char.class_id = class_id
    char.extensions = {
        "stats": {
            "stamina": 16, "agility": 14, "wisdom": 13,
            "bone": 18, "inner": 15, "spirit": 12,
        }
    }
    return char


def _make_engine_session(world=None, char=None, admin=False):
    """Create a mock engine + session pair for 10woongi testing."""
    constants = _import("constants")
    engine = MagicMock(spec=Engine)
    engine.world = world or World()
    engine.cmd_handlers = {}
    engine.cmd_korean = {}
    engine.players = {}
    engine.POS_FIGHTING = 8
    engine.POS_STANDING = 6
    engine.do_look = AsyncMock()
    engine._send_to_char = AsyncMock()

    session = MagicMock()
    session.send_line = AsyncMock()
    session.character = char
    session.player_data = {"level": 100 if admin else 1, "sex": 1}
    session.config = {
        "world": {
            "start_room": constants.START_ROOM,
            "void_room": constants.VOID_ROOM,
        }
    }
    session.engine = engine

    return engine, session


# ── Combat E2E ────────────────────────────────────────────────

class TestCombatE2E:
    async def test_sigma_dual_damage(self):
        sigma = _import("combat.sigma")
        char = _make_pc(level=15)
        char.session = None  # No session for send_to_char guard
        target = MobInstance(
            id=_next_id(),
            proto=MobProto(
                vnum=500, keywords="산적", short_desc="산적",
                long_desc="", detail_desc="",
                level=8, hitroll=3, armor_class=60,
                max_hp=25, damage_dice="1d6+2",
                gold=50, experience=300,
                act_flags=["ISNPC"], aff_flags=[], alignment=0, sex=1,
                scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={}),
            room_vnum=1,
            hp=100, max_hp=100,
        )
        target.move = 80
        target.max_move = 80
        target.session = None

        # No send_to_char — try multiple attacks to ensure at least one hits
        random.seed(0)
        total_hp_dmg = 0
        total_sp_dmg = 0
        for _ in range(10):
            hp_dmg, sp_dmg = await sigma.perform_attack(char, target)
            total_hp_dmg += hp_dmg
            total_sp_dmg += sp_dmg

        # Over 10 attacks, at least some should hit
        assert total_hp_dmg > 0 or total_sp_dmg > 0
        assert target.hp < 100 or target.move < 80

    async def test_death_e2e(self):
        death = _import("combat.death")
        constants = _import("constants")
        world = _make_10w_world()

        killer = _make_pc(room_vnum=998877665)
        killer.session = MagicMock()
        killer.session.send_line = AsyncMock()
        world.rooms[998877665].characters.append(killer)

        bandit = world.rooms[998877665].characters[0]
        bandit.hp = 0
        bandit.gold = 50  # Set instance gold (proto.gold doesn't auto-propagate)
        bandit.session = None
        old_gold = killer.gold
        old_exp = killer.experience

        engine, _ = _make_engine_session(world=world, char=killer)
        await death.handle_death(engine, bandit, killer=killer)

        assert killer.experience > old_exp
        assert killer.gold > old_gold
        assert bandit not in world.rooms[998877665].characters


# ── Level/Promotion E2E ──────────────────────────────────────

class TestLevelE2E:
    async def test_level_up_with_promotion(self):
        level_mod = _import("level")
        constants = _import("constants")

        char = _make_pc(level=29, class_id=1)
        # Give enough exp for level 30
        char.experience = level_mod.exp_to_next(char)

        send_fn = AsyncMock()
        random.seed(42)
        await level_mod.do_level_up(char, send_fn=send_fn)

        assert char.player_level == 30
        assert char.class_id == 2  # 투사 → 전사

        msgs = [c[0][0] for c in send_fn.call_args_list]
        assert any("레벨" in m for m in msgs)
        assert any("승급" in m for m in msgs)

    async def test_exp_formula(self):
        level_mod = _import("level")
        char = _make_pc(level=1)
        assert level_mod.exp_to_next(char) == 600  # 1*1*100 + 1*500
        char.player_level = 50
        assert level_mod.exp_to_next(char) == 275000  # 50*50*100 + 50*500


# ── Stats/Sigma E2E ───────────────────────────────────────────

class TestSigmaStatsE2E:
    def test_sigma_edge_cases(self):
        stats = _import("stats")
        assert stats.sigma(0) == 0
        assert stats.sigma(1) == 0
        assert stats.sigma(2) == 1
        assert stats.sigma(10) == 45
        # n=150: sum(1..149) = 149*150/2 = 11175
        assert stats.sigma(150) == 11175
        # n=200: sigma(150) + (200-150)*150 = 11175 + 7500 = 18675
        assert stats.sigma(200) == 18675

    def test_hp_sp_mp_formulas(self):
        stats = _import("stats")
        hp = stats.calc_hp(13)  # bone=13
        sp = stats.calc_sp(13, 13)  # inner=13, wisdom=13
        mp = stats.calc_mp(13)  # agility=13
        assert hp > 80  # 80 + bonus
        assert sp > 80  # 80 + bonus
        assert mp > 50  # 50 + bonus


# ── Skills E2E ────────────────────────────────────────────────

class TestSkillsE2E:
    def test_all_51_skills(self):
        skills = _import("combat.skills")
        assert len(skills.SKILLS) == 51

    def test_skill_categories(self):
        skills = _import("combat.skills")
        categories = set(s.category for s in skills.SKILLS.values())
        expected = {"defense", "attack", "recovery", "stealth", "magic", "utility"}
        assert categories == expected

    async def test_use_skill_sp_cost(self):
        skills = _import("combat.skills")
        char = _make_pc(level=50)
        char.move = 100
        char.max_move = 100

        target = MobInstance(
            id=_next_id(),
            proto=MobProto(
                vnum=500, keywords="적", short_desc="적",
                long_desc="", detail_desc="",
                level=5, hitroll=0, armor_class=80,
                max_hp=50, damage_dice="1d4+1",
                gold=0, experience=0,
                act_flags=["ISNPC"], aff_flags=[], alignment=0, sex=0,
                scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={}),
            room_vnum=1, hp=50, max_hp=50,
        )
        target.move = 50
        target.max_move = 50

        send_fn = AsyncMock()
        # Find an attack skill that doesn't need high level
        attack_skills = [s for s in skills.SKILLS.values()
                         if s.category == "attack" and s.min_level <= 50]
        if attack_skills:
            skill = attack_skills[0]
            # use_skill(char, skill_id, target, send_to_char)
            result = await skills.use_skill(char, skill.id, target, send_fn)
            assert result > 0  # Should deal damage
            # SP should be consumed
            assert char.move < 100


# ── Healing Tick E2E ──────────────────────────────────────────

class TestHealingTickE2E:
    async def test_tick_heals_hp_sp_mp(self):
        game = _import("game")
        constants = _import("constants")
        plugin = game.create_plugin()

        world = _make_10w_world()
        char = _make_pc(room_vnum=1392841419)
        char.hp = 50
        char.move = 40
        char.mana = 30
        world.rooms[1392841419].characters.append(char)

        engine = MagicMock()
        engine.world = world
        await plugin.tick_affects(engine)

        assert char.hp > 50
        assert char.move > 40
        assert char.mana > 30


# ── Config/Data Files E2E ─────────────────────────────────────

class TestConfigE2E:
    def test_10woongi_config_loads(self):
        config_path = Path(__file__).parent.parent / "config" / "10woongi.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        assert config["game"] == "10woongi"
        assert config["network"]["telnet_port"] == 4001
        assert config["world"]["start_room"] == 1392841419
        assert config["engine"]["combat_round"] == 10

    def test_system_messages_load(self):
        msg_path = Path(__file__).parent.parent / "data" / "10woongi" / "messages" / "system.yaml"
        with open(msg_path) as f:
            msgs = yaml.safe_load(f)
        assert "login" in msgs
        assert "combat" in msgs

    def test_sql_files_exist(self):
        data_dir = Path(__file__).parent.parent / "data" / "10woongi"
        assert (data_dir / "sql" / "schema.sql").exists()
        assert (data_dir / "sql" / "seed_data.sql").exists()

    def test_lua_files_exist(self):
        data_dir = Path(__file__).parent.parent / "data" / "10woongi"
        for lua_file in ["classes.lua", "combat.lua", "config.lua",
                         "korean_nlp.lua", "korean_commands.lua"]:
            assert (data_dir / "lua" / lua_file).exists()


# ── Docker Compose E2E ────────────────────────────────────────

class TestDockerCompose:
    def test_docker_compose_has_10woongi(self):
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        with open(compose_path) as f:
            compose = yaml.safe_load(f)
        assert "10woongi" in compose["services"]
        svc = compose["services"]["10woongi"]
        assert svc["environment"]["GAME"] == "10woongi"
        assert "4001:4001" in svc["ports"]

    def test_docker_compose_db_init(self):
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        with open(compose_path) as f:
            compose = yaml.safe_load(f)
        pg_volumes = compose["services"]["postgres"]["volumes"]
        assert any("init-db" in v for v in pg_volumes)


# ── Plugin E2E ────────────────────────────────────────────────

class TestPluginE2E:
    def test_plugin_creation(self):
        game = _import("game")
        plugin = game.create_plugin()
        assert plugin.name == "10woongi"

    def test_plugin_welcome_banner(self):
        game = _import("game")
        plugin = game.create_plugin()
        banner = plugin.welcome_banner()
        assert "호랭이" in banner or "십웅기" in banner

    def test_plugin_register_commands(self):
        """register_commands is now no-op (Lua provides all commands)."""
        game = _import("game")
        plugin = game.create_plugin()
        engine = MagicMock()
        engine.register_command = MagicMock()
        plugin.register_commands(engine)
        # Should be no-op — Lua handles all commands now
        assert engine.register_command.call_count == 0

    def test_plugin_initial_state(self):
        game = _import("game")
        plugin = game.create_plugin()
        state = plugin.get_initial_state()
        assert state is not None
        assert hasattr(state, "on_input")
        assert hasattr(state, "prompt")


# ── tbaMUD Compatibility ─────────────────────────────────────

class TestTbamudCompat:
    """Verify tbaMUD patterns still work alongside 10woongi."""

    def test_exit_direction_key(self):
        """tbaMUD-style exit with 'direction' key."""
        w = World()
        r = RoomProto(
            vnum=1, name="Test", description="",
            zone_vnum=0, sector=0, flags=[],
            exits=[Exit(direction=1, to_vnum=2)],
            extra_descs=[], scripts=[], ext={})
        w.rooms[1] = Room(proto=r)
        assert w.rooms[1].proto.exits[0].direction == 1
        assert w.rooms[1].proto.exits[0].to_room == 2

    def test_large_vnum_dict(self):
        """SHA-256 VNUMs don't break World dict ops."""
        w = World()
        big_vnums = [1392841419, 1854941986, 1958428208, 998877665]
        for v in big_vnums:
            w.rooms[v] = Room(proto=RoomProto(
                vnum=v, name=f"Room{v}", description="",
                zone_vnum=0, sector=0, flags=[],
                exits=[], extra_descs=[], scripts=[], ext={}))
        for v in big_vnums:
            assert w.get_room(v) is not None
