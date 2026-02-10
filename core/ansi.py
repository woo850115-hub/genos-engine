"""ANSI color code converter — {color_name} → ANSI escape sequences.

Supports: 16-color, 256-color ({fg_NNN}, {bg_NNN}), 24-bit truecolor ({rgb_R_G_B}).
"""

from __future__ import annotations

import re

# Standard 16-color foreground
_FG = {
    "black": "30", "red": "31", "green": "32", "yellow": "33",
    "blue": "34", "magenta": "35", "cyan": "36", "white": "37",
    "bright_black": "90", "bright_red": "91", "bright_green": "92",
    "bright_yellow": "93", "bright_blue": "94", "bright_magenta": "95",
    "bright_cyan": "96", "bright_white": "97",
}

# Standard 16-color background
_BG = {
    "bg_black": "40", "bg_red": "41", "bg_green": "42", "bg_yellow": "43",
    "bg_blue": "44", "bg_magenta": "45", "bg_cyan": "46", "bg_white": "47",
    "bg_bright_black": "100", "bg_bright_red": "101", "bg_bright_green": "102",
    "bg_bright_yellow": "103", "bg_bright_blue": "104", "bg_bright_magenta": "105",
    "bg_bright_cyan": "106", "bg_bright_white": "107",
}

# Format codes
_FMT = {
    "bold": "1", "dim": "2", "italic": "3", "underline": "4",
    "blink": "5", "reverse": "7", "strikethrough": "9",
}

_ESC = "\033["
_RESET = f"{_ESC}0m"

# Precompiled code map for named colors
_CODE_MAP: dict[str, str] = {}
_CODE_MAP["reset"] = _RESET
_CODE_MAP["normal"] = _RESET
for name, code in _FG.items():
    _CODE_MAP[name] = f"{_ESC}{code}m"
for name, code in _BG.items():
    _CODE_MAP[name] = f"{_ESC}{code}m"
for name, code in _FMT.items():
    _CODE_MAP[name] = f"{_ESC}{code}m"

# Extended color patterns: {fg_NNN}, {bg_NNN}, {rgb_R_G_B}, {bgrgb_R_G_B}
_FG256_RE = re.compile(r"fg_(\d{1,3})")
_BG256_RE = re.compile(r"bg_(\d{1,3})")
_FGRGB_RE = re.compile(r"rgb_(\d{1,3})_(\d{1,3})_(\d{1,3})")
_BGRGB_RE = re.compile(r"bgrgb_(\d{1,3})_(\d{1,3})_(\d{1,3})")

_COLOR_RE = re.compile(r"\{([\w]+)\}")


def _resolve_code(tag: str) -> str | None:
    """Resolve a color tag to ANSI escape sequence."""
    # Named color
    code = _CODE_MAP.get(tag)
    if code is not None:
        return code

    # 256-color foreground: fg_NNN
    m = _FG256_RE.fullmatch(tag)
    if m:
        n = int(m.group(1))
        if 0 <= n <= 255:
            return f"{_ESC}38;5;{n}m"

    # 256-color background: bg_NNN (where NNN > 107 to avoid conflict with named bg_*)
    m = _BG256_RE.fullmatch(tag)
    if m:
        n = int(m.group(1))
        if 0 <= n <= 255:
            return f"{_ESC}48;5;{n}m"

    # 24-bit truecolor foreground: rgb_R_G_B
    m = _FGRGB_RE.fullmatch(tag)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if all(0 <= c <= 255 for c in (r, g, b)):
            return f"{_ESC}38;2;{r};{g};{b}m"

    # 24-bit truecolor background: bgrgb_R_G_B
    m = _BGRGB_RE.fullmatch(tag)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if all(0 <= c <= 255 for c in (r, g, b)):
            return f"{_ESC}48;2;{r};{g};{b}m"

    return None


def colorize(text: str) -> str:
    """Convert {color_name} tags to ANSI escape sequences."""
    def _replace(m: re.Match) -> str:
        code = _resolve_code(m.group(1))
        if code is not None:
            return code
        return m.group(0)  # leave unknown tags as-is
    return _COLOR_RE.sub(_replace, text)


def strip_colors(text: str) -> str:
    """Remove all {color} tags from text."""
    return _COLOR_RE.sub("", text)


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    return re.sub(r"\033\[[0-9;]*m", "", text)
