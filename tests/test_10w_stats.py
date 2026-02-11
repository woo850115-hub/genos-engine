"""Tests for 10woongi sigma stat system."""

import importlib

import pytest


def _import_stats():
    return importlib.import_module("games.10woongi.stats")


class TestSigma:
    def setup_method(self):
        self.s = _import_stats()

    def test_sigma_zero(self):
        assert self.s.sigma(0) == 0

    def test_sigma_one(self):
        assert self.s.sigma(1) == 0

    def test_sigma_two(self):
        assert self.s.sigma(2) == 1

    def test_sigma_ten(self):
        # sigma(10) = sum(1..9) = 45
        assert self.s.sigma(10) == 45

    def test_sigma_thirteen(self):
        # Default stat 13: sigma(13) = sum(1..12) = 78
        assert self.s.sigma(13) == 78

    def test_sigma_hundred(self):
        # sigma(100) = sum(1..99) = 99*100/2 = 4950
        assert self.s.sigma(100) == 4950

    def test_sigma_150(self):
        # sigma(150) = sum(1..149) = 149*150/2 = 11175
        assert self.s.sigma(150) == 11175

    def test_sigma_151_linear(self):
        # sigma(151) = 11175 + (151-150)*150 = 11175 + 150 = 11325
        assert self.s.sigma(151) == 11325

    def test_sigma_200(self):
        # sigma(200) = 11175 + (200-150)*150 = 11175 + 7500 = 18675
        assert self.s.sigma(200) == 18675

    def test_sigma_negative(self):
        assert self.s.sigma(-5) == 0


class TestCalcHP:
    def setup_method(self):
        self.s = _import_stats()

    def test_hp_default_stat(self):
        # bone=13: hp = 80 + 6*sigma(13)/30 = 80 + 6*78/30 = 80 + 15 = 95
        # (integer division: 6*78=468, 468/30=15)
        assert self.s.calc_hp(13) == 95

    def test_hp_zero(self):
        # bone=0: hp = 80 + 0 = 80
        assert self.s.calc_hp(0) == 80

    def test_hp_high_stat(self):
        # bone=100: hp = 80 + 6*4950/30 = 80 + 990 = 1070
        assert self.s.calc_hp(100) == 1070

    def test_hp_one(self):
        # bone=1: sigma(1)=0, hp = 80
        assert self.s.calc_hp(1) == 80


class TestCalcSP:
    def setup_method(self):
        self.s = _import_stats()

    def test_sp_default_stats(self):
        # inner=13, wisdom=13
        # sp = 80 + (sigma(13)*2 + sigma(13))/30 = 80 + (78*2+78)/30 = 80 + 234/30 = 80 + 7 = 87
        assert self.s.calc_sp(13, 13) == 87

    def test_sp_zero(self):
        assert self.s.calc_sp(0, 0) == 80

    def test_sp_high_inner(self):
        # inner=100, wisdom=13
        # sp = 80 + (4950*2 + 78)/30 = 80 + 9978/30 = 80 + 332 = 412
        assert self.s.calc_sp(100, 13) == 412


class TestCalcMP:
    def setup_method(self):
        self.s = _import_stats()

    def test_mp_default_stat(self):
        # agility=13: mp = 50 + sigma(13)/15 = 50 + 78/15 = 50 + 5 = 55
        assert self.s.calc_mp(13) == 55

    def test_mp_zero(self):
        assert self.s.calc_mp(0) == 50

    def test_mp_high(self):
        # agility=100: mp = 50 + 4950/15 = 50 + 330 = 380
        assert self.s.calc_mp(100) == 380


class TestRandomStat:
    def setup_method(self):
        self.s = _import_stats()

    def test_range(self):
        for _ in range(100):
            val = self.s.random_stat()
            assert 11 <= val <= 15


class TestAdjExp:
    def setup_method(self):
        self.s = _import_stats()

    def test_level_1(self):
        # 1*1*10 + 1*50 = 60
        assert self.s.calc_adj_exp(1) == 60

    def test_level_10(self):
        # 100*10 + 500 = 1500
        assert self.s.calc_adj_exp(10) == 1500

    def test_level_50(self):
        # 2500*10 + 2500 = 27500
        assert self.s.calc_adj_exp(50) == 27500
