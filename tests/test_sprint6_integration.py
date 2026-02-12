"""Sprint 6 — Integration tests (E2E scenarios without DB)."""

import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from core.engine import Engine, _extract_korean_stem, _resolve_korean_verb
from core.world import (
    Exit, ExtraDesc, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, Shop, World, Zone,
)
from core.ansi import colorize
from core.korean import has_batchim, particle, render_message


# ── Helper factories ───────────────────────────────────────────────

def _make_multi_room_world():
    """World with 3 connected rooms, mobs, items, shop, zone."""
    w = World()

    # Room 3001 → 3002 (east) → 3003 (south)
    r1 = RoomProto(
        vnum=3001, name="광장", description="넓은 광장입니다.",
        zone_number=30, sector_type=0, room_flags=[],
        exits=[Exit(direction=1, to_room=3002)],  # east
        extra_descs=[ExtraDesc("분수 fountain", "아름다운 분수가 있습니다.")],
        trigger_vnums=[],
    )
    r2 = RoomProto(
        vnum=3002, name="상점거리", description="상점이 늘어서 있습니다.",
        zone_number=30, sector_type=0, room_flags=[],
        exits=[Exit(direction=3, to_room=3001), Exit(direction=2, to_room=3003)],
        extra_descs=[], trigger_vnums=[],
    )
    r3 = RoomProto(
        vnum=3003, name="숲", description="어두운 숲입니다.",
        zone_number=30, sector_type=3, room_flags=[],
        exits=[Exit(direction=0, to_room=3002)],
        extra_descs=[], trigger_vnums=[],
    )
    w.rooms[3001] = Room(proto=r1)
    w.rooms[3002] = Room(proto=r2)
    w.rooms[3003] = Room(proto=r3)

    # Mob protos
    guard = MobProto(
        vnum=100, keywords="guard 경비병", short_description="경비병",
        long_description="경비병이 서 있습니다.", detailed_description="강인한 경비병입니다.",
        level=10, hitroll=5, armor_class=50, hp_dice="5d8+30",
        damage_dice="1d6+3", gold=50, experience=500,
        action_flags=[], affect_flags=[], alignment=0, sex=1, trigger_vnums=[],
    )
    wolf = MobProto(
        vnum=101, keywords="wolf 늑대", short_description="사나운 늑대",
        long_description="사나운 늑대가 으르렁거립니다.", detailed_description="",
        level=5, hitroll=3, armor_class=80, hp_dice="3d6+10",
        damage_dice="1d4+2", gold=5, experience=100,
        action_flags=[], affect_flags=[], alignment=-500, sex=0, trigger_vnums=[],
    )
    w.mob_protos[100] = guard
    w.mob_protos[101] = wolf

    # Place mobs
    guard_mob = MobInstance(
        id=50, proto=guard, room_vnum=3002, hp=60, max_hp=60,
    )
    wolf_mob = MobInstance(
        id=51, proto=wolf, room_vnum=3003, hp=25, max_hp=25,
    )
    w.rooms[3002].characters.append(guard_mob)
    w.rooms[3003].characters.append(wolf_mob)

    # Item protos
    sword = ItemProto(
        vnum=200, keywords="sword 장검 검", short_description="멋진 장검",
        long_description="멋진 장검이 바닥에 놓여 있습니다.", item_type=5,
        extra_flags=[], wear_flags=[13], values=[0, 2, 6, 3],
        weight=10, cost=100, rent=10, affects=[], extra_descs=[], trigger_vnums=[],
    )
    potion = ItemProto(
        vnum=201, keywords="potion 물약", short_description="빨간 물약",
        long_description="빨간 물약이 놓여 있습니다.", item_type=10,
        extra_flags=[], wear_flags=[], values=[10, 0, 0, 0],
        weight=1, cost=50, rent=5, affects=[], extra_descs=[], trigger_vnums=[],
    )
    w.item_protos[200] = sword
    w.item_protos[201] = potion

    # Place item in room
    sword_inst = ObjInstance(id=80, proto=sword)
    w.rooms[3001].objects.append(sword_inst)

    # Shop (guard as shopkeeper)
    shop = Shop(
        vnum=1, keeper_vnum=100, selling_items=[201],
        profit_buy=1.5, profit_sell=0.5,
        shop_room=3002, open1=0, close1=28, open2=0, close2=0,
    )
    w.shops[100] = shop

    # Zone
    zone = Zone(
        vnum=30, name="마을", builders="GenOS", lifespan=15,
        bot=3001, top=3003, reset_mode=2, zone_flags=[],
        reset_commands=[],
    )
    w.zones.append(zone)

    # Socials
    w.socials["bow"] = {
        "command": "bow",
        "no_arg_to_char": "$n이(가) 정중히 인사합니다.",
        "no_arg_to_room": "$n이(가) 정중히 인사합니다.",
    }

    return w


def _load_common_lua(eng):
    """Load common + game-specific Lua commands/combat into engine for testing."""
    from core.lua_commands import LuaCommandRuntime
    eng.lua = LuaCommandRuntime(eng)
    base = Path(__file__).resolve().parent.parent / "games"
    # Load common first, then game-specific (order: common → tbamud)
    for scope in ("common", "tbamud"):
        lua_dir = base / scope / "lua"
        lib = lua_dir / "lib.lua"
        if lib.exists():
            eng.lua.load_source(lib.read_text(encoding="utf-8"), f"{scope}/lib")
        for subdir in ("commands", "combat"):
            sub_path = lua_dir / subdir
            if sub_path.exists():
                for f in sorted(sub_path.glob("*.lua")):
                    eng.lua.load_source(f.read_text(encoding="utf-8"),
                                        f"{scope}/{subdir}/{f.stem}")
    eng.lua.register_all_commands()


def _make_engine(world=None):
    if world is None:
        world = _make_multi_room_world()
    eng = Engine.__new__(Engine)
    eng.world = world
    eng.config = {"world": {"start_room": 3001}}
    eng.sessions = {}
    eng.players = {}
    eng.cmd_handlers = {}
    eng.cmd_korean = {}
    eng._register_core_commands()
    _load_common_lua(eng)
    eng.game_name = "tbamud"

    # Register game plugin commands
    from games.tbamud.game import TbaMudPlugin
    plugin = TbaMudPlugin()
    plugin.register_commands(eng)
    eng._plugin = plugin

    eng._load_korean_mappings()
    return eng


def _make_player_session(eng, name="테스터", level=10, room=3001, gold=500):
    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.engine = eng
    session.player_data = {
        "id": 1, "name": name, "level": level, "sex": 1,
        "class_id": 0, "aliases": {},
    }

    proto = MobProto(
        vnum=-1, keywords=name, short_description=name,
        long_description="", detailed_description="",
        level=level, hitroll=0, armor_class=100, hp_dice="0d0+0",
        damage_dice="1d4+0", gold=0, experience=0,
        action_flags=[], affect_flags=[], alignment=0, sex=1, trigger_vnums=[],
    )
    char = MobInstance(
        id=1, proto=proto, room_vnum=room, hp=100, max_hp=100,
        mana=100, max_mana=100, move=100, max_move=100,
        player_id=1, player_name=name, player_level=level,
        session=session, gold=gold, class_id=0,
    )
    session.character = char
    eng.world.rooms[room].characters.append(char)
    return session


# ── Integration test scenarios ──────────────────────────────────────


class TestMovementE2E:
    """Test complete movement flow through multiple rooms."""

    @pytest.mark.asyncio
    async def test_walk_east_and_back(self):
        eng = _make_engine()
        session = _make_player_session(eng)
        char = session.character

        assert char.room_vnum == 3001
        await eng.process_command(session, "east")
        assert char.room_vnum == 3002

        await eng.process_command(session, "west")
        assert char.room_vnum == 3001

    @pytest.mark.asyncio
    async def test_korean_direction(self):
        eng = _make_engine()
        session = _make_player_session(eng)
        char = session.character

        await eng.process_command(session, "동쪽")
        assert char.room_vnum == 3002

    @pytest.mark.asyncio
    async def test_no_exit_direction(self):
        eng = _make_engine()
        session = _make_player_session(eng)
        char = session.character

        await eng.process_command(session, "north")
        assert char.room_vnum == 3001  # didn't move
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("갈 수 없습니다" in c for c in calls)

    @pytest.mark.asyncio
    async def test_traverse_three_rooms(self):
        eng = _make_engine()
        session = _make_player_session(eng)
        char = session.character

        await eng.process_command(session, "e")
        assert char.room_vnum == 3002
        await eng.process_command(session, "s")
        assert char.room_vnum == 3003
        await eng.process_command(session, "n")
        assert char.room_vnum == 3002


class TestLookE2E:
    """Test look command in various contexts."""

    @pytest.mark.asyncio
    async def test_look_room(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "look")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("광장" in c for c in calls)

    @pytest.mark.asyncio
    async def test_look_extra_desc(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "look 분수")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("분수" in c for c in calls)

    @pytest.mark.asyncio
    async def test_look_at_mob(self):
        eng = _make_engine()
        session = _make_player_session(eng, room=3002)

        await eng.process_command(session, "look 경비병")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("경비병" in c for c in calls)

    @pytest.mark.asyncio
    async def test_look_at_object(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "look 검")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("장검" in c for c in calls)


class TestItemsE2E:
    """Test item pickup, drop, inventory flow."""

    @pytest.mark.asyncio
    async def test_get_and_inventory(self):
        eng = _make_engine()
        session = _make_player_session(eng)
        char = session.character

        await eng.process_command(session, "get 검")
        assert len(char.inventory) == 1
        assert char.inventory[0].proto.vnum == 200

        session.send_line.reset_mock()
        await eng.process_command(session, "i")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("장검" in c for c in calls)

    @pytest.mark.asyncio
    async def test_get_and_drop(self):
        eng = _make_engine()
        session = _make_player_session(eng)
        char = session.character

        await eng.process_command(session, "get 검")
        assert len(char.inventory) == 1

        await eng.process_command(session, "drop 검")
        assert len(char.inventory) == 0
        assert len(eng.world.rooms[3001].objects) == 1


class TestShopE2E:
    """Test shop flow — list, buy, sell."""

    @pytest.mark.asyncio
    async def test_list_buy_sell(self):
        eng = _make_engine()
        session = _make_player_session(eng, room=3002, gold=500)
        char = session.character

        # List
        await eng.process_command(session, "list")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("물약" in c for c in calls)

        # Buy
        session.send_line.reset_mock()
        await eng.process_command(session, "buy 물약")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("구입" in c for c in calls)
        assert len(char.inventory) == 1
        assert char.gold < 500

        # Sell back
        session.send_line.reset_mock()
        initial_gold = char.gold
        await eng.process_command(session, "sell 물약")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("판매" in c for c in calls)
        assert char.gold > initial_gold
        assert len(char.inventory) == 0


class TestCombatE2E:
    """Test combat initiation, kill target."""

    @pytest.mark.asyncio
    async def test_attack_target(self):
        eng = _make_engine()
        session = _make_player_session(eng, room=3003)
        char = session.character

        await eng.process_command(session, "kill 늑대")
        assert char.fighting is not None
        assert char.fighting.proto.vnum == 101
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("공격" in c for c in calls)

    @pytest.mark.asyncio
    async def test_attack_no_target(self):
        eng = _make_engine()
        session = _make_player_session(eng)  # room 3001, no mobs
        char = session.character

        # Remove all NPCs from room
        eng.world.rooms[3001].characters = [
            ch for ch in eng.world.rooms[3001].characters if not ch.is_npc
        ]

        await eng.process_command(session, "kill 고블린")
        assert char.fighting is None
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("찾을 수 없습니다" in c for c in calls)


class TestKoreanCommandE2E:
    """Test Korean command parsing in full E2E."""

    @pytest.mark.asyncio
    async def test_korean_look(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "봐")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("광장" in c for c in calls)

    @pytest.mark.asyncio
    async def test_korean_inventory(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "소지품")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("아무것도" in c for c in calls)

    @pytest.mark.asyncio
    async def test_korean_sov_attack(self):
        eng = _make_engine()
        session = _make_player_session(eng, room=3003)
        char = session.character

        await eng.process_command(session, "늑대 공격")
        assert char.fighting is not None

    @pytest.mark.asyncio
    async def test_choseong_abbreviation(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "ㅂ")  # → 봐 → look
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("광장" in c for c in calls)

    @pytest.mark.asyncio
    async def test_korean_verb_stem(self):
        eng = _make_engine()
        session = _make_player_session(eng, room=3003)
        char = session.character

        await eng.process_command(session, "늑대 죽이해")
        # "죽이해" → stem "죽이" → kill
        assert char.fighting is not None


class TestAdminE2E:
    """Test admin commands through engine.process_command."""

    @pytest.mark.asyncio
    async def test_goto_via_command(self):
        eng = _make_engine()
        session = _make_player_session(eng, level=34)
        char = session.character

        await eng.process_command(session, "goto 3002")
        assert char.room_vnum == 3002

    @pytest.mark.asyncio
    async def test_stat_via_command(self):
        eng = _make_engine()
        session = _make_player_session(eng, level=34)

        await eng.process_command(session, "stat")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("방 정보" in c for c in calls)


class TestPositionCommands:
    """Test sit/rest/stand/sleep cycle."""

    @pytest.mark.asyncio
    async def test_position_cycle(self):
        eng = _make_engine()
        session = _make_player_session(eng)
        char = session.character

        await eng.process_command(session, "sit")
        assert char.position == eng.POS_SITTING

        await eng.process_command(session, "stand")
        assert char.position == eng.POS_STANDING

        await eng.process_command(session, "rest")
        assert char.position == eng.POS_RESTING

        await eng.process_command(session, "sleep")
        assert char.position == eng.POS_SLEEPING

        await eng.process_command(session, "wake")
        assert char.position == eng.POS_STANDING


class TestScoreCommand:
    @pytest.mark.asyncio
    async def test_score_shows_info(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "score")
        calls = [str(c) for c in session.send_line.call_args_list]
        joined = " ".join(calls)
        assert "테스터" in joined
        assert "체력" in joined or "HP" in joined


class TestANSIColorize:
    def test_basic_colors(self):
        assert "\033[31m" in colorize("{red}test")
        assert "\033[0m" in colorize("{reset}")

    def test_bright_colors(self):
        result = colorize("{bright_cyan}hello{reset}")
        assert "\033[96m" in result
        assert "\033[0m" in result

    def test_no_codes(self):
        assert colorize("plain text") == "plain text"

    def test_nested(self):
        result = colorize("{red}damage {yellow}gold{reset}")
        assert "\033[31m" in result
        assert "\033[33m" in result


class TestKoreanPostpositions:
    def test_has_batchim(self):
        assert has_batchim("검") is True   # ㅁ 받침
        assert has_batchim("물") is True   # ㄹ 받침
        assert has_batchim("나") is False  # 없음
        assert has_batchim("마나") is False  # 없음

    def test_particle(self):
        assert particle("검", "을/를") == "을"
        assert particle("마나", "을/를") == "를"
        assert particle("검", "이/가") == "이"
        assert particle("마나", "이/가") == "가"

    def test_render_message(self):
        msg = render_message("{target}을(를) 공격합니다.", target="검")
        assert "검을" in msg
        msg2 = render_message("{target}을(를) 공격합니다.", target="마나")
        assert "마나를" in msg2


class TestSystemMessages:
    """Verify system message YAML is loadable and complete."""

    def test_load_messages_yaml(self):
        path = Path(__file__).parent.parent / "data" / "tbamud" / "messages" / "system.yaml"
        with open(path, encoding="utf-8") as f:
            msgs = yaml.safe_load(f)
        assert "login" in msgs
        assert "system" in msgs
        assert "combat" in msgs
        assert "items" in msgs
        assert "communication" in msgs
        assert "shop" in msgs
        assert "admin" in msgs
        assert "spell" in msgs
        assert "position" in msgs
        assert "error" in msgs

    def test_login_messages(self):
        path = Path(__file__).parent.parent / "data" / "tbamud" / "messages" / "system.yaml"
        with open(path, encoding="utf-8") as f:
            msgs = yaml.safe_load(f)
        login = msgs["login"]
        assert "welcome" in login
        assert "password_prompt" in login
        assert "select_class" in login
        assert "마법사" in login["select_class"]

    def test_combat_messages(self):
        path = Path(__file__).parent.parent / "data" / "tbamud" / "messages" / "system.yaml"
        with open(path, encoding="utf-8") as f:
            msgs = yaml.safe_load(f)
        combat = msgs["combat"]
        assert "you_hit" in combat
        assert "you_die" in combat
        assert "target_dies" in combat


class TestConfigYAML:
    """Verify config YAML is loadable and valid."""

    def test_load_config(self):
        path = Path(__file__).parent.parent / "config" / "tbamud.yaml"
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert config["game"] == "tbamud"
        assert config["network"]["telnet_port"] == 4000
        assert config["network"]["api_port"] == 8080
        assert config["world"]["start_room"] == 3001
        assert config["engine"]["tick_rate"] == 10

    def test_database_config(self):
        path = Path(__file__).parent.parent / "config" / "tbamud.yaml"
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        db = config["database"]
        assert "host" in db
        assert "port" in db
        assert "user" in db
        assert "database" in db


class TestPrefixMatching:
    """Test command prefix matching works correctly."""

    @pytest.mark.asyncio
    async def test_prefix_match(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "sco")  # → score
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("테스터" in c for c in calls)

    @pytest.mark.asyncio
    async def test_exits_command(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "exits")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("출구" in c or "동" in c for c in calls)


class TestKoreanVerbResolution:
    def test_direct_verb(self):
        assert _resolve_korean_verb("봐") == "look"
        assert _resolve_korean_verb("공격") == "attack"
        assert _resolve_korean_verb("죽이") == "kill"

    def test_stem_extraction(self):
        assert _extract_korean_stem("공격해") == "공격"
        assert _extract_korean_stem("죽이해") == "죽이"
        assert _extract_korean_stem("저장하다") == "저장"

    def test_full_resolution_with_stem(self):
        assert _resolve_korean_verb("저장해") == "save"
        assert _resolve_korean_verb("죽이해") == "kill"


class TestSocialE2E:
    @pytest.mark.asyncio
    async def test_social_command(self):
        eng = _make_engine()
        session = _make_player_session(eng)

        await eng.process_command(session, "bow")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("인사" in c for c in calls)
