"""Sprint 2 tests — command dispatcher enhancements."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.engine import (
    CHOSEONG_MAP, KOREAN_VERB_MAP, DIR_NAMES_KR_MAP, Engine,
    _extract_korean_stem, _resolve_korean_verb,
)
from core.world import (
    Exit, MobInstance, MobProto, Room, RoomProto, World,
)


# ── Helper ───────────────────────────────────────────────────────

def _make_world():
    w = World()
    room1 = RoomProto(
        vnum=3001, name="신전", description="넓은 신전입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[Exit(direction=0, to_vnum=3002)],
        extra_descs=[], scripts=[], ext={})
    room2 = RoomProto(
        vnum=3002, name="길", description="좁은 길입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[Exit(direction=2, to_vnum=3001)],
        extra_descs=[], scripts=[], ext={})
    w.rooms[3001] = Room(proto=room1)
    w.rooms[3002] = Room(proto=room2)
    return w


def _load_common_lua(eng):
    """Load common Lua commands into engine for testing."""
    from core.lua_commands import LuaCommandRuntime
    from pathlib import Path
    eng.lua = LuaCommandRuntime(eng)
    lua_dir = Path(__file__).resolve().parent.parent / "games" / "common" / "lua"
    lib = lua_dir / "lib.lua"
    if lib.exists():
        eng.lua.load_source(lib.read_text(encoding="utf-8"), "lib")
    cmd_dir = lua_dir / "commands"
    if cmd_dir.exists():
        for f in sorted(cmd_dir.glob("*.lua")):
            eng.lua.load_source(f.read_text(encoding="utf-8"), f"cmd/{f.stem}")
    eng.lua.register_all_commands()


def _make_engine_and_session(world=None):
    if world is None:
        world = _make_world()
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 3001}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    _load_common_lua(eng)
    eng._load_korean_mappings()
    eng.game_name = "tbamud"

    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.engine = eng
    session.player_data = {"id": 1, "name": "테스터", "level": 1, "aliases": {}}

    proto = MobProto(
        vnum=-1, keywords="테스터", short_desc="테스터",
        long_desc="", detail_desc="",
        level=1, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0,
        scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
    char = MobInstance(
        id=1, proto=proto, room_vnum=3001, hp=20, max_hp=20,
        player_id=1, player_name="테스터", session=session,
    )
    session.character = char
    world.rooms[3001].characters.append(char)
    return eng, session


# ── Korean verb resolution ───────────────────────────────────────

class TestKoreanVerbResolution:
    def test_direct_match(self):
        assert _resolve_korean_verb("공격") == "attack"
        assert _resolve_korean_verb("봐") == "look"
        assert _resolve_korean_verb("저장") == "save"

    def test_stem_extraction(self):
        assert _extract_korean_stem("공격해") == "공격"
        assert _extract_korean_stem("공격하다") == "공격"
        assert _extract_korean_stem("저장해라") == "저장"  # "해라" stripped

    def test_stem_match(self):
        assert _resolve_korean_verb("공격해") == "attack"
        assert _resolve_korean_verb("공격하다") == "attack"

    def test_no_match(self):
        assert _resolve_korean_verb("xyz") is None

    def test_short_word_no_extract(self):
        # Single char word with ending → no stem (word too short)
        assert _extract_korean_stem("해") is None


class TestKoreanVerbMap:
    def test_all_values_are_strings(self):
        for kr, eng in KOREAN_VERB_MAP.items():
            assert isinstance(kr, str)
            assert isinstance(eng, str)

    def test_common_verbs(self):
        assert KOREAN_VERB_MAP["공격"] == "attack"
        assert KOREAN_VERB_MAP["봐"] == "look"
        assert KOREAN_VERB_MAP["줘"] == "give"
        assert KOREAN_VERB_MAP["열"] == "open"


# ── Choseong abbreviation ───────────────────────────────────────

class TestChoseong:
    def test_map_exists(self):
        assert "ㄱ" in CHOSEONG_MAP
        assert "ㅂ" in CHOSEONG_MAP

    def test_choseong_resolves(self):
        assert CHOSEONG_MAP["ㄱ"] == "공격"
        assert CHOSEONG_MAP["ㅂ"] == "봐"
        assert CHOSEONG_MAP["ㄷ"] == "도움"

    @pytest.mark.asyncio
    async def test_choseong_dispatch(self):
        eng, session = _make_engine_and_session()
        # ㅂ → 봐 → look
        await eng.process_command(session, "ㅂ")
        calls = [str(c) for c in session.send_line.call_args_list]
        found_room = any("신전" in c for c in calls)
        assert found_room


# ── Direction map extended ───────────────────────────────────────

class TestDirectionMapExtended:
    def test_extended_directions(self):
        assert DIR_NAMES_KR_MAP["북쪽"] == 0
        assert DIR_NAMES_KR_MAP["남쪽"] == 2
        assert DIR_NAMES_KR_MAP["위쪽"] == 4
        assert DIR_NAMES_KR_MAP["아래쪽"] == 5


# ── Alias system ─────────────────────────────────────────────────

class TestAlias:
    @pytest.mark.asyncio
    async def test_alias_expansion(self):
        eng, session = _make_engine_and_session()
        session.player_data["aliases"] = {"순찰": "north"}
        result = eng._expand_alias(session, "순찰")
        assert result == "north"

    @pytest.mark.asyncio
    async def test_alias_no_match(self):
        eng, session = _make_engine_and_session()
        session.player_data["aliases"] = {"순찰": "north"}
        result = eng._expand_alias(session, "공격")
        assert result == "공격"

    @pytest.mark.asyncio
    async def test_alias_command(self):
        eng, session = _make_engine_and_session()
        await eng.cmd_handlers["alias"](session, "gg look")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("별칭 설정" in c for c in calls)
        assert session.player_data["aliases"]["gg"] == "look"

    @pytest.mark.asyncio
    async def test_alias_list_empty(self):
        eng, session = _make_engine_and_session()
        session.player_data["aliases"] = {}
        await eng.cmd_handlers["alias"](session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("없습니다" in c for c in calls)


# ── Command resolution (SOV/SVO) ────────────────────────────────

class TestCommandResolution:
    @pytest.mark.asyncio
    async def test_sov_korean(self):
        """'고블린 봐' → look with args='고블린'."""
        eng, session = _make_engine_and_session()
        # Add a mob for "look at"
        await eng.process_command(session, "고블린 봐")
        calls = [str(c) for c in session.send_line.call_args_list]
        # Should try to look at "고블린"
        found_msg = any("볼 수 없습니다" in c or "신전" in c for c in calls)
        assert found_msg

    @pytest.mark.asyncio
    async def test_svo_english(self):
        """'look goblin' → look with args='goblin'."""
        eng, session = _make_engine_and_session()
        await eng.process_command(session, "look goblin")
        calls = [str(c) for c in session.send_line.call_args_list]
        found_msg = any("볼 수 없습니다" in c for c in calls)
        assert found_msg

    @pytest.mark.asyncio
    async def test_unknown_command(self):
        eng, session = _make_engine_and_session()
        await eng.process_command(session, "xyzzy")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("모르겠습니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_direction_korean_extended(self):
        """'북쪽' → move north."""
        eng, session = _make_engine_and_session()
        char = session.character
        await eng.process_command(session, "북쪽")
        assert char.room_vnum == 3002
