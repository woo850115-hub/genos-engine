"""Tests for 10woongi foundation — config, plugin, constants."""

import importlib
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


def _import_10w(submodule: str):
    return importlib.import_module(f"games.10woongi.{submodule}")


# ── Config ──────────────────────────────────────────────────────


class TestConfig:
    def setup_method(self):
        with open(BASE_DIR / "config" / "10woongi.yaml", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def test_game_name(self):
        assert self.config["game"] == "10woongi"

    def test_telnet_port(self):
        assert self.config["network"]["telnet_port"] == 4001

    def test_api_port(self):
        assert self.config["network"]["api_port"] == 8081

    def test_database_name(self):
        assert self.config["database"]["database"] == "genos_10woongi"

    def test_start_room(self):
        assert self.config["world"]["start_room"] == 1392841419

    def test_void_room(self):
        assert self.config["world"]["void_room"] == 1854941986

    def test_frozen_room(self):
        assert self.config["world"]["frozen_start_room"] == 1958428208

    def test_combat_round_ticks(self):
        assert self.config["engine"]["combat_round"] == 10  # 1 sec

    def test_tick_rate(self):
        assert self.config["engine"]["tick_rate"] == 10


# ── Plugin ──────────────────────────────────────────────────────


class TestPlugin:
    def test_create_plugin(self):
        game = _import_10w("game")
        plugin = game.create_plugin()
        assert plugin.name == "10woongi"

    def test_welcome_banner(self):
        game = _import_10w("game")
        plugin = game.create_plugin()
        banner = plugin.welcome_banner()
        assert "십웅기" in banner
        assert "10woongi" in banner

    def test_register_commands_no_error(self):
        """register_commands should not raise even with a mock engine."""

        class MockEngine:
            cmd_handlers = {}
            cmd_korean = {}

            def register_command(self, name, handler, korean=None):
                self.cmd_handlers[name] = handler
                if korean:
                    self.cmd_korean[korean] = name

        game = _import_10w("game")
        plugin = game.create_plugin()
        plugin.register_commands(MockEngine())


# ── Constants ───────────────────────────────────────────────────


class TestConstants:
    def setup_method(self):
        self.c = _import_10w("constants")

    def test_wear_slots_count(self):
        assert len(self.c.WEAR_SLOTS) == 22

    def test_wear_slots_all_named(self):
        for slot_id, name in self.c.WEAR_SLOTS.items():
            assert isinstance(slot_id, int)
            assert isinstance(name, str)
            assert len(name) > 0

    def test_stat_names(self):
        assert len(self.c.STAT_NAMES) == 6
        assert "체력" in self.c.STAT_NAMES
        assert "내공" in self.c.STAT_NAMES

    def test_stat_keys(self):
        assert len(self.c.STAT_KEYS) == 6
        assert "bone" in self.c.STAT_KEYS
        assert "inner" in self.c.STAT_KEYS

    def test_class_names_count(self):
        assert len(self.c.CLASS_NAMES) == 14

    def test_starting_class(self):
        assert 1 in self.c.STARTING_CLASSES
        assert self.c.STARTING_CLASSES[1] == "투사"

    def test_promotion_chain(self):
        # 투사(1) → 전사(2) → 기사(3) → 상급기사(4)
        assert self.c.PROMOTION_CHAIN[1] == (30, 2)
        assert self.c.PROMOTION_CHAIN[2] == (60, 3)
        assert self.c.PROMOTION_CHAIN[3] == (100, 4)

    def test_promotion_chain_priest(self):
        # 사제(6) → 성직자(7) → 아바타(8)
        assert self.c.PROMOTION_CHAIN[6] == (30, 7)
        assert self.c.PROMOTION_CHAIN[7] == (60, 8)

    def test_promotion_chain_thief(self):
        # 도둑(9) → 사냥꾼(10) → 암살자(11)
        assert self.c.PROMOTION_CHAIN[9] == (30, 10)
        assert self.c.PROMOTION_CHAIN[10] == (60, 11)

    def test_promotion_chain_mage(self):
        # 마술사(12) → 마법사(13) → 시공술사(14)
        assert self.c.PROMOTION_CHAIN[12] == (30, 13)
        assert self.c.PROMOTION_CHAIN[13] == (60, 14)

    def test_special_promotion(self):
        # 기사(3) → 신관기사(5) alternative
        assert self.c.SPECIAL_PROMOTIONS[3] == (80, 5)

    def test_key_rooms(self):
        assert self.c.START_ROOM == 1392841419
        assert self.c.VOID_ROOM == 1854941986
        assert self.c.FREEZER_ROOM == 1958428208

    def test_combat_round_ticks(self):
        assert self.c.COMBAT_ROUND_TICKS == 10

    def test_heal_rates(self):
        assert self.c.HEAL_RATE_HP == 0.08
        assert self.c.HEAL_RATE_SP == 0.09
        assert self.c.HEAL_RATE_MP == 0.13

    def test_critical_types(self):
        assert len(self.c.CRITICAL_TYPES) == 8
        assert self.c.CRITICAL_TYPES[8] == "KILL"

    def test_class_families(self):
        assert len(self.c.CLASS_FAMILIES) == 4
        all_classes = []
        for family in self.c.CLASS_FAMILIES.values():
            all_classes.extend(family)
        # All 14 classes are covered
        assert len(set(all_classes)) == 14


# ── Data Files ──────────────────────────────────────────────────


class TestDataFiles:
    def test_schema_sql_exists(self):
        assert (BASE_DIR / "data" / "10woongi" / "sql" / "schema.sql").is_file()

    def test_seed_data_exists(self):
        assert (BASE_DIR / "data" / "10woongi" / "sql" / "seed_data.sql").is_file()

    def test_lua_files_exist(self):
        lua_dir = BASE_DIR / "data" / "10woongi" / "lua"
        assert (lua_dir / "classes.lua").is_file()
        assert (lua_dir / "combat.lua").is_file()
        assert (lua_dir / "config.lua").is_file()
        assert (lua_dir / "korean_nlp.lua").is_file()
        assert (lua_dir / "korean_commands.lua").is_file()

    def test_system_yaml_exists(self):
        path = BASE_DIR / "data" / "10woongi" / "messages" / "system.yaml"
        assert path.is_file()

    def test_system_yaml_parseable(self):
        path = BASE_DIR / "data" / "10woongi" / "messages" / "system.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "login" in data
        assert "combat" in data
        assert "sp_damage" in data["combat"]

    def test_schema_sql_has_rooms_table(self):
        path = BASE_DIR / "data" / "10woongi" / "sql" / "schema.sql"
        content = path.read_text(encoding="utf-8")
        assert "CREATE TABLE" in content
        assert "rooms" in content
