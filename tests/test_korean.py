"""Tests for Korean language utilities."""

import pytest
from core.korean import has_batchim, particle, render_message


class TestHasBatchim:
    def test_with_batchim(self):
        assert has_batchim("한") is True  # ㄴ batchim
        assert has_batchim("낚") is True  # ㄱ batchim

    def test_without_batchim(self):
        assert has_batchim("나") is False
        assert has_batchim("머") is False

    def test_rieul_batchim(self):
        assert has_batchim("갈") is True  # ㄹ batchim

    def test_empty(self):
        assert has_batchim("") is False

    def test_english(self):
        # Non-Hangul characters
        assert has_batchim("a") is False

    def test_number_batchim(self):
        # Numbers ending in 1,3,6,7,8,0 have "batchim-like" pronunciation
        assert has_batchim("1") is True
        assert has_batchim("2") is False
        assert has_batchim("3") is True


class TestParticle:
    def test_subject_with_batchim(self):
        assert particle("검", "이/가") == "이"

    def test_subject_without_batchim(self):
        assert particle("나", "이/가") == "가"

    def test_object_with_batchim(self):
        assert particle("검", "을/를") == "을"

    def test_object_without_batchim(self):
        assert particle("나", "을/를") == "를"

    def test_topic_with_batchim(self):
        assert particle("검", "은/는") == "은"

    def test_topic_without_batchim(self):
        assert particle("나", "은/는") == "는"

    def test_direction_rieul(self):
        # ㄹ batchim uses 로 (not 으로)
        assert particle("갈", "으로/로") == "로"

    def test_direction_other_batchim(self):
        assert particle("검", "으로/로") == "으로"

    def test_direction_no_batchim(self):
        assert particle("나", "으로/로") == "로"

    def test_unknown_particle(self):
        assert particle("검", "unknown") == "unknown"


class TestRenderMessage:
    def test_simple_substitution(self):
        result = render_message("{name} 안녕", name="철수")
        assert result == "철수 안녕"

    def test_particle_subject(self):
        result = render_message("{name}이(가) 왔습니다", name="철수")
        assert "철수가" in result

    def test_particle_subject_batchim(self):
        result = render_message("{name}이(가) 왔습니다", name="민준")
        assert "민준이" in result

    def test_particle_object(self):
        result = render_message("{item}을(를) 주웠습니다", item="검")
        assert "검을" in result

    def test_particle_object_no_batchim(self):
        result = render_message("{item}을(를) 주웠습니다", item="도끼")
        assert "도끼를" in result
