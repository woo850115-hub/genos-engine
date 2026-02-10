"""Tests for ANSI color code converter."""

from core.ansi import colorize, strip_ansi, strip_colors


class TestColorize:
    def test_basic_color(self):
        result = colorize("{red}hello{reset}")
        assert "\033[31m" in result
        assert "\033[0m" in result
        assert "hello" in result

    def test_bold(self):
        result = colorize("{bold}text{reset}")
        assert "\033[1m" in result

    def test_background(self):
        result = colorize("{bg_blue}text{reset}")
        assert "\033[44m" in result

    def test_unknown_tag(self):
        result = colorize("{unknown}text")
        assert "{unknown}" in result

    def test_no_tags(self):
        assert colorize("plain text") == "plain text"

    def test_multiple_colors(self):
        result = colorize("{red}hello {green}world{reset}")
        assert "\033[31m" in result
        assert "\033[32m" in result

    def test_bright_colors(self):
        result = colorize("{bright_red}text{reset}")
        assert "\033[91m" in result


class TestStripColors:
    def test_strip(self):
        assert strip_colors("{red}hello{reset}") == "hello"

    def test_no_tags(self):
        assert strip_colors("plain") == "plain"


class TestStripAnsi:
    def test_strip(self):
        assert strip_ansi("\033[31mhello\033[0m") == "hello"
