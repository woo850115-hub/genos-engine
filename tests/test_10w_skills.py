"""Tests for 10woongi skill system."""

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.world import MobInstance, MobProto


def _import_skills():
    return importlib.import_module("games.10woongi.combat.skills")


def _make_char(level=10, class_id=1, sp=100, **kwargs):
    proto = MobProto(
        vnum=-1, keywords="player", short_description="테스터",
        long_description="", detailed_description="",
        level=level, hitroll=5, armor_class=50,
        hp_dice="0d0+100", damage_dice="1d6+2",
        gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=1, trigger_vnums=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=1,
        hp=100, max_hp=100, mana=50, max_mana=50,
        move=sp, max_move=sp,
        player_id=1, player_name="테스터",
        damroll=kwargs.get("damroll", 3),
    )
    char.class_id = class_id
    char.player_level = level
    char.session = MagicMock()
    char.session.send_line = AsyncMock()
    char.extensions = kwargs.get("extensions", {
        "stats": {"stamina": 13, "agility": 13, "wisdom": 13,
                  "bone": 13, "inner": 13, "spirit": 13}
    })
    return char


class TestSkillDefinitions:
    def test_51_skills_defined(self):
        skills = _import_skills()
        assert len(skills.SKILLS) == 51

    def test_all_skills_have_names(self):
        skills = _import_skills()
        for s in skills.SKILLS.values():
            assert s.name
            assert s.korean_name
            assert s.category in ("defense", "attack", "recovery",
                                  "stealth", "magic", "utility")

    def test_skill_categories(self):
        skills = _import_skills()
        categories = {}
        for s in skills.SKILLS.values():
            categories.setdefault(s.category, []).append(s)
        assert "defense" in categories
        assert "attack" in categories
        assert "recovery" in categories
        assert "magic" in categories
        assert "utility" in categories
        assert "stealth" in categories

    def test_parry_progression(self):
        skills = _import_skills()
        p1 = skills.SKILLS[1]
        p2 = skills.SKILLS[2]
        p3 = skills.SKILLS[3]
        assert p1.min_level < p2.min_level < p3.min_level
        assert p1.korean_name == "패리1"

    def test_heal_progression(self):
        skills = _import_skills()
        h1 = skills.SKILLS[13]
        h2 = skills.SKILLS[14]
        h3 = skills.SKILLS[15]
        assert h1.sp_cost < h2.sp_cost < h3.sp_cost

    def test_recall_available_to_all(self):
        skills = _import_skills()
        recall = skills.SKILLS[33]
        assert recall.name == "recall"
        assert len(recall.class_ids) == 14


class TestFindSkill:
    def test_find_by_name(self):
        skills = _import_skills()
        s = skills.find_skill("parry_l1")
        assert s is not None
        assert s.id == 1

    def test_find_by_korean(self):
        skills = _import_skills()
        s = skills.find_skill("패리1")
        assert s is not None
        assert s.id == 1

    def test_find_prefix(self):
        skills = _import_skills()
        s = skills.find_skill("fire")
        assert s is not None
        assert s.korean_name == "파이어볼"

    def test_find_nonexistent(self):
        skills = _import_skills()
        assert skills.find_skill("존재하지않는기술") is None


class TestCanUseSkill:
    def test_success(self):
        skills = _import_skills()
        char = _make_char(level=10, class_id=1, sp=100)
        ok, msg = skills.can_use_skill(char, 1)  # parry_l1
        assert ok is True

    def test_level_too_low(self):
        skills = _import_skills()
        char = _make_char(level=5, class_id=3, sp=100)
        ok, msg = skills.can_use_skill(char, 3)  # parry_l3 requires level 50
        assert ok is False
        assert "레벨" in msg

    def test_wrong_class(self):
        skills = _import_skills()
        char = _make_char(level=50, class_id=6, sp=100)  # 사제
        ok, msg = skills.can_use_skill(char, 11)  # backstab - thief only
        assert ok is False
        assert "직업" in msg

    def test_not_enough_sp(self):
        skills = _import_skills()
        char = _make_char(level=80, class_id=14, sp=5)  # low SP, high level
        ok, msg = skills.can_use_skill(char, 28)  # meteor costs 80 SP
        assert ok is False
        assert "내공" in msg

    def test_nonexistent_skill(self):
        skills = _import_skills()
        char = _make_char()
        ok, msg = skills.can_use_skill(char, 9999)
        assert ok is False


class TestUseSkill:
    async def test_attack_skill_deals_damage(self):
        skills = _import_skills()
        char = _make_char(level=20, class_id=1, sp=100)
        target = _make_char(level=5, class_id=1, sp=50)
        target.player_id = 2
        target.player_name = "대상"

        send_fn = AsyncMock()

        initial_hp = target.hp
        dmg = await skills.use_skill(char, 10, target, send_to_char=send_fn)  # critical_hit
        assert dmg > 0
        assert target.hp < initial_hp
        # SP should have been deducted
        assert char.move < 100

    async def test_heal_skill_restores_hp(self):
        skills = _import_skills()
        char = _make_char(level=10, class_id=6, sp=100)  # 사제
        target = _make_char(level=5, class_id=1)
        target.hp = 30
        target.max_hp = 100

        send_fn = AsyncMock()
        dmg = await skills.use_skill(char, 13, target, send_to_char=send_fn)  # heal_l1
        assert dmg < 0  # Negative = healing
        assert target.hp > 30

    async def test_magic_skill_deals_damage(self):
        skills = _import_skills()
        char = _make_char(level=30, class_id=13, sp=200)  # 마법사
        target = _make_char(level=5, class_id=1)

        send_fn = AsyncMock()
        initial_hp = target.hp
        dmg = await skills.use_skill(char, 25, target, send_to_char=send_fn)  # fireball
        assert dmg > 0
        assert target.hp < initial_hp

    async def test_defense_skill(self):
        skills = _import_skills()
        char = _make_char(level=5, class_id=1, sp=50)
        send_fn = AsyncMock()
        dmg = await skills.use_skill(char, 1, char, send_to_char=send_fn)  # parry_l1
        assert dmg == 0  # Defense skill doesn't deal damage

    async def test_sp_deduction(self):
        skills = _import_skills()
        char = _make_char(level=30, class_id=13, sp=100)
        target = _make_char(level=5, class_id=1)
        send_fn = AsyncMock()

        skill = skills.SKILLS[25]  # fireball, costs 30 SP
        await skills.use_skill(char, 25, target, send_to_char=send_fn)
        assert char.move == 100 - skill.sp_cost
