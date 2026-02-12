"""Tests for 10woongi sigma combat system."""

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.world import MobInstance, MobProto, Room, RoomProto, World


def _import_sigma():
    return importlib.import_module("games.10woongi.combat.sigma")


def _import_death():
    return importlib.import_module("games.10woongi.combat.death")


def _import_game():
    return importlib.import_module("games.10woongi.game")


def _make_mob(vnum=100, level=10, hp=100, is_player=False, **kwargs):
    proto = MobProto(
        vnum=vnum, keywords="test mob", short_description="테스트 몬스터",
        long_description="테스트 몬스터가 서 있습니다.", detailed_description="",
        level=level, hitroll=kwargs.get("hitroll", 5), armor_class=50,
        hp_dice=f"0d0+{hp}", damage_dice=kwargs.get("damage_dice", "2d6+3"),
        gold=kwargs.get("gold", 100), experience=kwargs.get("exp", 500),
        action_flags=[], affect_flags=[], alignment=0, sex=1, trigger_vnums=[],
    )
    mob = MobInstance(
        id=vnum, proto=proto, room_vnum=1,
        hp=hp, max_hp=hp, mana=50, max_mana=50,
        move=80, max_move=80,
        gold=kwargs.get("gold", 100),
        damroll=kwargs.get("damroll", 3),
    )
    if is_player:
        mob.player_id = vnum
        mob.player_name = kwargs.get("name", "테스터")
        mob.session = MagicMock()
        mob.session.send_line = AsyncMock()
    mob.extensions = kwargs.get("extensions", {
        "stats": {"stamina": 13, "agility": 13, "wisdom": 13,
                  "bone": 13, "inner": 13, "spirit": 13}
    })
    return mob


class TestSigmaHitChance:
    def test_base_hit_chance(self):
        sigma = _import_sigma()
        atk = _make_mob(hitroll=5)
        dfn = _make_mob()
        chance = sigma.calc_hit_chance(atk, dfn)
        # MobInstance.hitroll defaults to 0, so:
        # base=50+0=50, spirit_bonus=13//2=6, agi_penalty=13//3=4
        assert chance == 52

    def test_high_spirit_bonus(self):
        sigma = _import_sigma()
        atk = _make_mob(hitroll=10, extensions={
            "stats": {"spirit": 50, "stamina": 13, "agility": 13,
                      "wisdom": 13, "bone": 13, "inner": 13}
        })
        dfn = _make_mob()
        chance = sigma.calc_hit_chance(atk, dfn)
        assert chance > 70

    def test_hit_chance_capped_at_95(self):
        sigma = _import_sigma()
        atk = _make_mob(hitroll=100, extensions={
            "stats": {"spirit": 200, "stamina": 13, "agility": 13,
                      "wisdom": 13, "bone": 13, "inner": 13}
        })
        dfn = _make_mob()
        assert sigma.calc_hit_chance(atk, dfn) == 95

    def test_hit_chance_min_5(self):
        sigma = _import_sigma()
        atk = _make_mob(hitroll=0, extensions={
            "stats": {"spirit": 1, "stamina": 13, "agility": 13,
                      "wisdom": 13, "bone": 13, "inner": 13}
        })
        dfn = _make_mob(extensions={
            "stats": {"agility": 200, "stamina": 13, "wisdom": 13,
                      "bone": 13, "inner": 13, "spirit": 13}
        })
        assert sigma.calc_hit_chance(atk, dfn) == 5


class TestSigmaDamage:
    def test_hp_damage_positive(self):
        sigma = _import_sigma()
        atk = _make_mob(damroll=5)
        dfn = _make_mob()
        for _ in range(20):
            dmg = sigma.calc_hp_damage(atk, dfn)
            assert dmg >= 1

    def test_sp_damage_non_negative(self):
        sigma = _import_sigma()
        atk = _make_mob()
        dfn = _make_mob()
        for _ in range(20):
            dmg = sigma.calc_sp_damage(atk, dfn)
            assert dmg >= 0


class TestPerformAttack:
    async def test_attack_reduces_hp(self):
        sigma = _import_sigma()
        atk = _make_mob(vnum=1, hitroll=100, extensions={
            "stats": {"spirit": 100, "stamina": 20, "agility": 13,
                      "wisdom": 13, "bone": 13, "inner": 20}
        })
        dfn = _make_mob(vnum=2, hp=1000)
        # Force high hit chance
        initial_hp = dfn.hp
        total_dmg = 0
        for _ in range(20):
            hp_d, sp_d = await sigma.perform_attack(atk, dfn)
            total_dmg += hp_d
        assert total_dmg > 0
        assert dfn.hp < initial_hp

    async def test_attack_dual_damage(self):
        """Attack should reduce both HP and SP (move)."""
        sigma = _import_sigma()
        atk = _make_mob(vnum=1, hitroll=100, extensions={
            "stats": {"spirit": 100, "stamina": 20, "agility": 13,
                      "wisdom": 13, "bone": 13, "inner": 50}
        })
        dfn = _make_mob(vnum=2, hp=10000)
        dfn.move = 500
        dfn.max_move = 500

        initial_sp = dfn.move
        total_sp_dmg = 0
        for _ in range(50):
            _, sp_d = await sigma.perform_attack(atk, dfn)
            total_sp_dmg += sp_d
        # SP should have been reduced
        assert total_sp_dmg > 0
        assert dfn.move < initial_sp

    async def test_miss_no_damage(self):
        """Very low hit chance should sometimes miss."""
        sigma = _import_sigma()
        atk = _make_mob(vnum=1, hitroll=0, extensions={
            "stats": {"spirit": 1, "stamina": 1, "agility": 1,
                      "wisdom": 1, "bone": 1, "inner": 1}
        })
        dfn = _make_mob(vnum=2, hp=100, extensions={
            "stats": {"agility": 200, "stamina": 13, "wisdom": 13,
                      "bone": 13, "inner": 13, "spirit": 13}
        })
        misses = 0
        for _ in range(100):
            hp_d, _ = await sigma.perform_attack(atk, dfn)
            if hp_d == 0:
                misses += 1
        assert misses > 50  # Should miss most of the time


class TestHandleDeath:
    async def test_npc_death_awards_exp(self):
        death = _import_death()
        world = World()
        room_proto = RoomProto(
            vnum=1, name="Test", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        world.rooms[1] = Room(proto=room_proto)

        victim = _make_mob(vnum=10, level=5, hp=0, gold=50)
        world.rooms[1].characters.append(victim)

        killer = _make_mob(vnum=20, is_player=True, name="영웅")

        engine = MagicMock()
        engine.world = world
        engine.config = {"world": {"void_room": 1854941986}}

        initial_exp = killer.experience
        initial_gold = killer.gold
        await death.handle_death(engine, victim, killer=killer)

        assert killer.experience > initial_exp
        assert killer.gold > initial_gold
        assert victim not in world.rooms[1].characters

    async def test_pc_death_teleports_to_void(self):
        death = _import_death()
        world = World()

        for vnum in (1, 1854941986):
            room_proto = RoomProto(
                vnum=vnum, name=f"Room {vnum}", description="",
                zone_number=0, sector_type=0, room_flags=[],
                exits=[], extra_descs=[], trigger_vnums=[],
            )
            world.rooms[vnum] = Room(proto=room_proto)

        victim = _make_mob(vnum=30, is_player=True, name="희생자", hp=0)
        victim.max_hp = 100
        victim.max_move = 80
        victim.room_vnum = 1
        world.rooms[1].characters.append(victim)

        engine = MagicMock()
        engine.world = world
        engine.config = {"world": {"void_room": 1854941986}}
        engine.do_look = AsyncMock()

        await death.handle_death(engine, victim)

        assert victim.room_vnum == 1854941986
        assert victim.hp > 0
        assert victim.fighting is None
        assert victim in world.rooms[1854941986].characters


class TestCombatRound:
    async def test_plugin_handle_death(self):
        """WoongiPlugin.handle_death awards exp and removes NPC."""
        game = _import_game()
        plugin = game.create_plugin()

        world = World()
        room_proto = RoomProto(
            vnum=1, name="Arena", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        world.rooms[1] = Room(proto=room_proto)

        killer = _make_mob(vnum=1, level=10, hp=500)
        killer.player_id = 1
        killer.player_name = "테스터"
        killer.session = MagicMock()
        killer.session.send_line = AsyncMock()

        victim = _make_mob(vnum=2, level=5, hp=0)
        victim.gold = 50

        world.rooms[1].characters.extend([killer, victim])

        engine = MagicMock()
        engine.world = world
        engine.config = {"world": {"void_room": 1854941986}}
        engine.do_look = AsyncMock()

        initial_exp = killer.experience
        await plugin.handle_death(engine, victim, killer=killer)

        # NPC should be removed from room
        assert victim not in world.rooms[1].characters
        # Killer should gain exp and gold
        assert killer.experience > initial_exp
        assert killer.gold >= 50


class TestHealingTick:
    async def test_hp_healing(self):
        game = _import_game()
        plugin = game.create_plugin()

        world = World()
        room_proto = RoomProto(
            vnum=1, name="Rest", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        world.rooms[1] = Room(proto=room_proto)

        char = _make_mob(vnum=1, hp=50)
        char.max_hp = 100
        char.mana = 20
        char.max_mana = 50
        char.move = 30
        char.max_move = 80
        world.rooms[1].characters.append(char)

        engine = MagicMock()
        engine.world = world

        await plugin.tick_affects(engine)

        # HP should heal 8% of 100 = 8
        assert char.hp == 58
        # SP should heal 9% of 80 = 7
        assert char.move == 37
        # MP should heal 13% of 50 = 6
        assert char.mana == 26

    async def test_no_overheal(self):
        game = _import_game()
        plugin = game.create_plugin()

        world = World()
        room_proto = RoomProto(
            vnum=1, name="Rest", description="",
            zone_number=0, sector_type=0, room_flags=[],
            exits=[], extra_descs=[], trigger_vnums=[],
        )
        world.rooms[1] = Room(proto=room_proto)

        char = _make_mob(vnum=1, hp=99)
        char.max_hp = 100
        world.rooms[1].characters.append(char)

        engine = MagicMock()
        engine.world = world

        await plugin.tick_affects(engine)
        assert char.hp == 100  # Capped at max
