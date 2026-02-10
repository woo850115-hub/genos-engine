"""Korean language utilities — batchim detection, particle selection, message rendering."""

from __future__ import annotations

# Unicode Hangul syllable block: U+AC00..U+D7A3
_HANGUL_BASE = 0xAC00
_HANGUL_END = 0xD7A3
_JONGSEONG_COUNT = 28  # number of final consonants (0 = no batchim)

# Particle pairs: (with_batchim, without_batchim)
PARTICLES = {
    "이/가": ("이", "가"),
    "을/를": ("을", "를"),
    "은/는": ("은", "는"),
    "과/와": ("과", "와"),
    "으로/로": ("으로", "로"),
    "이다/다": ("이다", "다"),
    "아/야": ("아", "야"),
}


def has_batchim(char: str) -> bool:
    """Check if a single Hangul character has a final consonant (받침)."""
    if not char:
        return False
    code = ord(char[-1])
    if _HANGUL_BASE <= code <= _HANGUL_END:
        return (code - _HANGUL_BASE) % _JONGSEONG_COUNT != 0
    # Non-Hangul: treat numbers ending in certain consonants
    if char[-1].isdigit():
        return char[-1] in "013678"
    return False


def particle(word: str, particle_type: str) -> str:
    """Select correct particle for the given word.

    particle_type should be one of: "이/가", "을/를", "은/는", "과/와", "으로/로", "이다/다", "아/야"
    """
    pair = PARTICLES.get(particle_type)
    if pair is None:
        return particle_type
    with_bat, without_bat = pair
    # Special: 으로/로 — ㄹ batchim uses 로 not 으로
    if particle_type == "으로/로" and word:
        code = ord(word[-1])
        if _HANGUL_BASE <= code <= _HANGUL_END:
            jongseong = (code - _HANGUL_BASE) % _JONGSEONG_COUNT
            if jongseong == 8:  # ㄹ
                return without_bat
    return with_bat if has_batchim(word) else without_bat


def render_message(template: str, **kwargs: str) -> str:
    """Render a message template with automatic Korean particles.

    Template format: "{name}이(가)" or "{name}{이/가}"
    Supports: 이(가), 을(를), 은(는), 과(와), (으)로, 이다(다), 아(야)
    """
    # First pass: substitute variables
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", value)

    # Second pass: resolve particles — {word}이(가) pattern
    import re

    # Pattern: word + particle options like 이(가), 을(를), 은(는), 과(와), (으)로, 이다(다)
    particle_patterns = [
        (r"(\S+)이\(가\)", "이/가"),
        (r"(\S+)을\(를\)", "을/를"),
        (r"(\S+)은\(는\)", "은/는"),
        (r"(\S+)과\(와\)", "과/와"),
        (r"(\S+)\(으\)로", "으로/로"),
        (r"(\S+)이다\(다\)", "이다/다"),
        (r"(\S+)아\(야\)", "아/야"),
    ]

    for pattern, ptype in particle_patterns:
        def _replace(m: re.Match, pt: str = ptype) -> str:
            word = m.group(1)
            return word + particle(word, pt)
        result = re.sub(pattern, _replace, result)

    return result
