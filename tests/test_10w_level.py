"""Tests for 10woongi level/promotion system."""

import importlib
import random
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.world import MobInstance, MobProto, _next_id


def _import_level():
    return importlib.import_module("games.10woongi.level")


def _import_constants():
    return importlib.import_module("games.10woongi.constants")


def _make_char(level=1, exp=0, class_id=1):
    proto = MobProto(
        vnum=-1, keywords="player", short_description="테스터",
        long_description="", detailed_description="",
        level=level, hitroll=0, armor_class=50,
        hp_dice="0d0+100", damage_dice="1d6+2",
        gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=1, trigger_vnums=[],
    )
    char = MobInstance(
        id=_next_id(), proto=proto, room_vnum=1,
        hp=100, max_hp=100, player_id=1, player_name="테스터",
    )
    char.player_level = level
    char.experience = exp
    char.class_id = class_id
    char.mana = 50
    char.max_mana = 50
    char.move = 80
    char.max_move = 80
    char.extensions = {
        "stats": {
            "stamina": 13, "agility": 13, "wisdom": 13,
            "bone": 13, "inner": 13, "spirit": 13,
        }
    }
    return char


class TestExpToNext:
    def test_level_1(self):
        lv = _import_level()
        char = _make_char(level=1)
        assert lv.exp_to_next(char) == 1 * 1 * 100 + 1 * 500  # 600

    def test_level_10(self):
        lv = _import_level()
        char = _make_char(level=10)
        assert lv.exp_to_next(char) == 10 * 10 * 100 + 10 * 500  # 15000

    def test_level_50(self):
        lv = _import_level()
        char = _make_char(level=50)
        assert lv.exp_to_next(char) == 50 * 50 * 100 + 50 * 500  # 275000


class TestCheckLevelUp:
    def test_not_enough(self):
        lv = _import_level()
        char = _make_char(level=1, exp=500)
        assert not lv.check_level_up(char)

    def test_exact(self):
        lv = _import_level()
        char = _make_char(level=1, exp=600)
        assert lv.check_level_up(char)

    def test_over(self):
        lv = _import_level()
        char = _make_char(level=1, exp=1000)
        assert lv.check_level_up(char)


class TestDoLevelUp:
    async def test_level_up_increases_level(self):
        lv = _import_level()
        char = _make_char(level=1, exp=600)
        random.seed(42)
        await lv.do_level_up(char)
        assert char.player_level == 2

    async def test_level_up_hp_increases(self):
        lv = _import_level()
        char = _make_char(level=1, exp=600)
        old_max_hp = char.max_hp
        random.seed(42)
        await lv.do_level_up(char)
        assert char.max_hp > old_max_hp

    async def test_level_up_sends_message(self):
        lv = _import_level()
        char = _make_char(level=1, exp=600)
        send_fn = AsyncMock()
        random.seed(42)
        await lv.do_level_up(char, send_fn=send_fn)
        send_fn.assert_called()
        msg = send_fn.call_args_list[0][0][0]
        assert "레벨" in msg
        assert "2" in msg

    async def test_multi_level_up(self):
        lv = _import_level()
        # Enough exp for multiple levels: level 1 needs 600, level 2 needs 2400
        char = _make_char(level=1, exp=5000)
        random.seed(42)
        await lv.do_level_up(char)
        assert char.player_level >= 3


class TestPromotion:
    async def test_warrior_to_fighter(self):
        """투사(1) → 전사(2) at level 30."""
        lv = _import_level()
        c = _import_constants()
        # class_id=1 (투사), promote at level 30
        char = _make_char(level=29, exp=0, class_id=1)
        # enough for level 30
        needed = lv.exp_to_next(char)
        char.experience = needed
        send_fn = AsyncMock()
        random.seed(42)
        await lv.do_level_up(char, send_fn=send_fn)
        assert char.player_level == 30
        assert char.class_id == 2  # 전사
        # Check promotion message
        msgs = [call[0][0] for call in send_fn.call_args_list]
        assert any("승급" in m for m in msgs)

    async def test_priest_to_cleric(self):
        """사제(6) → 성직자(7) at level 30."""
        lv = _import_level()
        char = _make_char(level=29, exp=0, class_id=6)
        needed = lv.exp_to_next(char)
        char.experience = needed
        random.seed(42)
        await lv.do_level_up(char)
        assert char.class_id == 7  # 성직자

    async def test_no_promotion_wrong_level(self):
        """투사(1) shouldn't promote at level 20."""
        lv = _import_level()
        char = _make_char(level=19, exp=0, class_id=1)
        needed = lv.exp_to_next(char)
        char.experience = needed
        random.seed(42)
        await lv.do_level_up(char)
        assert char.player_level == 20
        assert char.class_id == 1  # still 투사

    async def test_sp_mp_recalculated(self):
        """Level up should recalculate SP/MP from stats."""
        lv = _import_level()
        char = _make_char(level=1, exp=600)
        char.extensions["stats"]["inner"] = 20
        char.extensions["stats"]["wisdom"] = 18
        old_sp = char.max_move
        random.seed(42)
        await lv.do_level_up(char)
        # SP should be recalculated from sigma formula
        assert char.max_move > 0
        assert char.move == char.max_move
