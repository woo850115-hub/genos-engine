"""Tests for Lua command framework — Sprint 1 PoC.

Tests:
- LuaCommandRuntime initialization
- CommandContext message buffering / deferred actions
- register_command / register_hook from Lua
- Lua-Python async bridge (wrap_command)
- PoC commands: say, who, exits
- DB seed/load cycle (mocked)
- API endpoints for Lua scripts (mocked)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.lua_commands import LuaCommandRuntime, CommandContext, HookContext
from core.world import (
    Exit, GameClass, MobInstance, MobProto, ObjInstance, ItemProto,
    Room, RoomProto, World,
)


# ── Helpers ──────────────────────────────────────────────────────


def _make_world():
    """Create a minimal world with two connected rooms."""
    world = World()
    room1_proto = RoomProto(
        vnum=3001, name="신전", description="광대한 신전입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[Exit(direction=0, to_vnum=3002)],
        extra_descs=[], scripts=[], ext={})
    room2_proto = RoomProto(
        vnum=3002, name="길", description="좁은 길입니다.",
        zone_vnum=30, sector=0, flags=[],
        exits=[Exit(direction=2, to_vnum=3001)],
        extra_descs=[], scripts=[], ext={})
    world.rooms[3001] = Room(proto=room1_proto)
    world.rooms[3002] = Room(proto=room2_proto)
    world.classes[0] = GameClass(
        id=0, name="마법사", abbrev="마법",
        hp_gain=(3, 8),
    )
    return world


def _make_engine(world=None):
    """Create a mock engine for testing."""
    engine = MagicMock()
    engine.world = world or _make_world()
    engine.config = {"world": {"start_room": 3001}}
    engine.sessions = {}
    engine.players = {}
    engine.cmd_handlers = {}
    engine.cmd_korean = {}
    engine.game_name = "tbamud"

    def register_command(name, handler, korean=None):
        engine.cmd_handlers[name] = handler
        if korean:
            engine.cmd_korean[korean] = name

    engine.register_command = register_command
    return engine


def _make_session(engine, room_vnum=3001):
    """Create a mock session with a character in a room."""
    session = MagicMock()
    session.send_line = AsyncMock()
    session.send = AsyncMock()
    session.save_character = AsyncMock()
    session.engine = engine
    session.player_data = {"id": 1, "name": "테스터", "level": 1, "class_id": 0}

    proto = MobProto(
        vnum=-1, keywords="테스터", short_desc="테스터",
        long_desc="", detail_desc="",
        level=1, hitroll=0, armor_class=100, max_hp=1,
        damage_dice="1d4+0", gold=0, experience=0,
        act_flags=[], aff_flags=[], alignment=0, sex=0,
        scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
    char = MobInstance(
        id=1, proto=proto, room_vnum=room_vnum,
        hp=20, max_hp=20, mana=100, max_mana=100,
        player_id=1, player_name="테스터",
        session=session,
    )
    session.character = char
    engine.world.rooms[room_vnum].characters.append(char)
    return session


# ── LuaCommandRuntime basic tests ────────────────────────────────


class TestLuaCommandRuntime:
    def test_init(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        assert runtime.command_count == 0
        assert runtime.hook_count == 0

    def test_register_command_from_lua(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("test_cmd", function(ctx, args)
                ctx:send("hello " .. args)
            end, "테스트")
        """)
        assert runtime.has_command("test_cmd")
        assert runtime.get_korean_cmd("테스트") == "test_cmd"
        assert runtime.command_count == 1

    def test_register_hook_from_lua(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_hook("combat_round", function(ctx, attacker, defender)
                ctx:send("combat!")
            end)
        """)
        assert runtime.has_hook("combat_round")
        assert runtime.hook_count == 1

    def test_register_all_commands(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("greet", function(ctx, args) ctx:send("hi") end, "인사")
        """)
        runtime.register_all_commands()
        assert "greet" in engine.cmd_handlers
        assert engine.cmd_korean.get("인사") == "greet"

    def test_multiple_scripts(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("cmd_a", function(ctx, args) end)
        """)
        runtime.load_source("""
            register_command("cmd_b", function(ctx, args) end)
        """)
        assert runtime.command_count == 2

    def test_load_invalid_lua_raises(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        with pytest.raises(Exception):
            runtime.load_source("this is not valid lua @@@@")

    def test_reload_script(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("mutable", function(ctx, args)
                ctx:send("version1")
            end)
        """)
        assert runtime.has_command("mutable")
        # Reload with new version
        runtime.reload_script("""
            register_command("mutable", function(ctx, args)
                ctx:send("version2")
            end)
        """)
        assert runtime.has_command("mutable")


# ── CommandContext tests ─────────────────────────────────────────


class TestCommandContext:
    def test_send_buffers(self):
        engine = _make_engine()
        session = _make_session(engine)
        ctx = CommandContext(session, engine)
        ctx.send("hello")
        ctx.send("world")
        assert len(ctx._messages) == 2

    @pytest.mark.asyncio
    async def test_flush_sends_messages(self):
        engine = _make_engine()
        session = _make_session(engine)
        ctx = CommandContext(session, engine)
        ctx.send("hello")
        ctx.send("world")
        await ctx.flush()
        assert session.send_line.call_count == 2
        assert len(ctx._messages) == 0

    def test_send_room(self):
        engine = _make_engine()
        session1 = _make_session(engine, 3001)
        # Add another character
        session2 = MagicMock()
        session2.send_line = AsyncMock()
        proto2 = MobProto(
            vnum=-1, keywords="동료", short_desc="동료",
            long_desc="", detail_desc="",
            level=1, hitroll=0, armor_class=100, max_hp=1,
            damage_dice="1d4+0", gold=0, experience=0,
            act_flags=[], aff_flags=[], alignment=0, sex=0,
            scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
        char2 = MobInstance(
            id=2, proto=proto2, room_vnum=3001,
            hp=20, max_hp=20, player_id=2, player_name="동료",
            session=session2,
        )
        engine.world.rooms[3001].characters.append(char2)

        ctx = CommandContext(session1, engine)
        ctx.send_room("방 메시지")
        # Should buffer for char2 but not char1
        assert len(ctx._messages) == 1
        assert ctx._messages[0][0] == session2

    def test_char_property(self):
        engine = _make_engine()
        session = _make_session(engine)
        ctx = CommandContext(session, engine)
        assert ctx.char is session.character
        assert ctx.char.name == "테스터"

    def test_get_room(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        room = ctx.get_room()
        assert room is not None
        assert room.proto.name == "신전"

    def test_get_room_by_vnum(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        room = ctx.get_room(3002)
        assert room is not None
        assert room.proto.name == "길"

    def test_find_char(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        # Add NPC
        npc_proto = MobProto(
            vnum=100, keywords="고블린 goblin", short_desc="고블린",
            long_desc="", detail_desc="",
            level=3, hitroll=0, armor_class=100, max_hp=9,
            damage_dice="1d4+0", gold=10, experience=50,
            act_flags=[], aff_flags=[], alignment=-300, sex=0,
            scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
        npc = MobInstance(
            id=99, proto=npc_proto, room_vnum=3001,
            hp=10, max_hp=10,
        )
        engine.world.rooms[3001].characters.append(npc)

        ctx = CommandContext(session, engine)
        found = ctx.find_char("고블린")
        assert found is not None
        assert found.proto.vnum == 100

    def test_find_char_not_found(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        assert ctx.find_char("드래곤") is None

    def test_find_player(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        engine.players["테스터"] = session
        ctx = CommandContext(session, engine)
        found = ctx.find_player("테스터")
        assert found is session.character

    def test_get_class(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        cls = ctx.get_class(0)
        assert cls is not None
        assert cls.name == "마법사"

    def test_get_players(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        engine.players["테스터"] = session
        ctx = CommandContext(session, engine)
        players = ctx.get_players()
        assert len(players) == 1
        assert players[0].name == "테스터"

    def test_random(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        val = ctx.random(1, 10)
        assert 1 <= val <= 10

    def test_roll_dice(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        val = ctx.roll_dice("2d6+3")
        assert 5 <= val <= 15

    def test_is_admin(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        assert not ctx.is_admin()
        session.player_data["level"] = 34
        assert ctx.is_admin()

    def test_particle(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        assert ctx.particle("검", "을", "를") == "을"
        assert ctx.particle("마나", "을", "를") == "를"

    def test_deal_damage(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        char = ctx.char
        char.hp = 20
        ctx.deal_damage(char, 5)
        assert char.hp == 15

    def test_heal(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        char = ctx.char
        char.hp = 10
        ctx.heal(char, 5)
        assert char.hp == 15
        # Don't exceed max
        ctx.heal(char, 100)
        assert char.hp == char.max_hp

    def test_affect_operations(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        char = ctx.char
        assert not ctx.has_affect(char, 42)
        ctx.apply_affect(char, 42, 10)
        assert ctx.has_affect(char, 42)
        ctx.remove_affect(char, 42)
        assert not ctx.has_affect(char, 42)

    def test_start_stop_combat(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        npc_proto = MobProto(
            vnum=100, keywords="몬스터", short_desc="몬스터",
            long_desc="", detail_desc="",
            level=3, hitroll=0, armor_class=100, max_hp=9,
            damage_dice="1d4+0", gold=10, experience=50,
            act_flags=[], aff_flags=[], alignment=0, sex=0,
            scripts=[], max_mana=0, max_move=0, damroll=0, position=8, class_id=0, race_id=0, stats={}, skills={}, ext={})
        npc = MobInstance(id=99, proto=npc_proto, room_vnum=3001, hp=10, max_hp=10)
        engine.world.rooms[3001].characters.append(npc)

        ctx = CommandContext(session, engine)
        ctx.start_combat(npc)
        assert ctx.char.fighting is npc
        assert npc.fighting is ctx.char
        ctx.stop_combat(ctx.char)
        assert ctx.char.fighting is None

    def test_move_to(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        ctx.move_to(3002)
        assert ctx.char.room_vnum == 3002

    def test_find_obj_inv(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        item_proto = ItemProto(
            vnum=1000, keywords="검 sword", short_desc="빛나는 검",
            long_desc="검이 바닥에 놓여 있다.", item_type="weapon",
            flags=[], wear_slots=[], values={},
            weight=5, cost=100, affects=[], extra_descs=[],
            scripts=[], min_level=0, ext={})
        obj = ObjInstance(id=500, proto=item_proto, values={})
        obj.carried_by = session.character
        session.character.inventory.append(obj)

        ctx = CommandContext(session, engine)
        found = ctx.find_obj_inv("검")
        assert found is not None
        assert found.proto.vnum == 1000

    def test_equip_unequip(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        item_proto = ItemProto(
            vnum=1001, keywords="갑옷 armor", short_desc="가죽 갑옷",
            long_desc="", item_type="potion", flags=[], wear_slots=[],
            values={}, weight=10, cost=200,
            affects=[], extra_descs=[], scripts=[], min_level=0, ext={})
        obj = ObjInstance(id=501, proto=item_proto, values={})

        ctx = CommandContext(session, engine)
        ctx.equip(obj, 3)
        assert 3 in session.character.equipment
        assert session.character.equipment[3] is obj

        returned = ctx.unequip(3)
        assert returned is obj
        assert 3 not in session.character.equipment
        assert obj in session.character.inventory

    @pytest.mark.asyncio
    async def test_deferred_look(self):
        engine = _make_engine()
        look_handler = AsyncMock()
        engine.cmd_handlers["look"] = look_handler
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        ctx.defer_look()
        assert len(ctx._deferred) == 1
        await ctx.execute_deferred()
        look_handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deferred_save(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        ctx.defer_save()
        await ctx.execute_deferred()
        session.save_character.assert_awaited_once()


# ── Lua command execution (wrap_command) ─────────────────────────


class TestLuaCommandExecution:
    @pytest.mark.asyncio
    async def test_wrap_command_basic(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("ping", function(ctx, args)
                ctx:send("pong " .. args)
            end)
        """)
        handler = runtime.wrap_command("ping")
        assert handler is not None
        await handler(session, "test")
        # Check that message was sent
        calls = session.send_line.call_args_list
        assert any("pong test" in str(c) for c in calls)

    @pytest.mark.asyncio
    async def test_wrap_command_error_handling(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("broken", function(ctx, args)
                error("intentional error")
            end)
        """)
        handler = runtime.wrap_command("broken")
        # Should not raise — error caught and user gets error message
        await handler(session, "")
        calls = session.send_line.call_args_list
        assert any("오류" in str(c) for c in calls)

    @pytest.mark.asyncio
    async def test_lua_char_access(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("myname", function(ctx, args)
                local ch = ctx.char
                ctx:send("이름: " .. ch.name)
                ctx:send("HP: " .. ch.hp .. "/" .. ch.max_hp)
                ctx:send("레벨: " .. ch.level)
            end)
        """)
        handler = runtime.wrap_command("myname")
        await handler(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("이름: 테스터" in c for c in calls)
        assert any("HP: 20/20" in c for c in calls)

    @pytest.mark.asyncio
    async def test_lua_modify_char(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("givegold", function(ctx, args)
                ctx.char.gold = ctx.char.gold + 100
                ctx:send("골드 100 획득!")
            end)
        """)
        handler = runtime.wrap_command("givegold")
        assert session.character.gold == 0
        await handler(session, "")
        assert session.character.gold == 100

    @pytest.mark.asyncio
    async def test_lua_ctx_methods(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        engine.players["테스터"] = session
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_command("test_ctx", function(ctx, args)
                local room = ctx:get_room()
                ctx:send("방: " .. room.proto.name)
                local cls = ctx:get_class(0)
                ctx:send("직업: " .. cls.name)
                local players = ctx:get_players()
                ctx:send("접속: " .. #players)
                local r = ctx:random(1, 1)
                ctx:send("랜덤: " .. r)
            end)
        """)
        handler = runtime.wrap_command("test_ctx")
        await handler(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("방: 신전" in c for c in calls)
        assert any("직업: 마법사" in c for c in calls)
        assert any("접속: 1" in c for c in calls)
        assert any("랜덤: 1" in c for c in calls)


# ── Hook tests ───────────────────────────────────────────────────


class TestLuaHooks:
    def test_fire_hook(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_hook("test_hook", function(ctx, value)
                ctx:send("hook fired: " .. tostring(value))
            end)
        """)
        ctx = CommandContext(session, engine)
        runtime.fire_hook("test_hook", ctx, 42)
        assert any("hook fired: 42" in msg for _, msg in ctx._messages)

    def test_fire_nonexistent_hook(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        ctx = CommandContext(session, engine)
        # Should not raise
        runtime.fire_hook("nonexistent", ctx)

    def test_multiple_hooks(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        runtime.load_source("""
            register_hook("multi", function(ctx) ctx:send("hook1") end)
            register_hook("multi", function(ctx) ctx:send("hook2") end)
        """)
        ctx = CommandContext(session, engine)
        runtime.fire_hook("multi", ctx)
        msgs = [msg for _, msg in ctx._messages]
        assert "hook1" in msgs
        assert "hook2" in msgs


# ── PoC commands (say, who, exits from Lua seed files) ───────────


class TestPoCSayCommand:
    @pytest.mark.asyncio
    async def test_say_no_args(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        lua_src = (
            Path(__file__).parent.parent / "games" / "common" / "lua" / "commands" / "core.lua"
        ).read_text(encoding="utf-8")
        runtime.load_source(lua_src)
        handler = runtime.wrap_command("say")
        await handler(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("무엇이라고" in c for c in calls)

    @pytest.mark.asyncio
    async def test_say_with_message(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        lua_src = (
            Path(__file__).parent.parent / "games" / "common" / "lua" / "commands" / "core.lua"
        ).read_text(encoding="utf-8")
        runtime.load_source(lua_src)
        handler = runtime.wrap_command("say")
        await handler(session, "안녕하세요")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("안녕하세요" in c for c in calls)
        assert any("말합니다" in c for c in calls)


class TestPoCWhoCommand:
    @pytest.mark.asyncio
    async def test_who_lists_players(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        engine.players["테스터"] = session
        runtime = LuaCommandRuntime(engine)
        lua_src = (
            Path(__file__).parent.parent / "games" / "common" / "lua" / "commands" / "core.lua"
        ).read_text(encoding="utf-8")
        runtime.load_source(lua_src)
        handler = runtime.wrap_command("who")
        await handler(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("테스터" in c for c in calls)
        assert any("1명" in c for c in calls)
        assert any("마법사" in c for c in calls)


class TestPoCExitsCommand:
    @pytest.mark.asyncio
    async def test_exits_shows_directions(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        runtime = LuaCommandRuntime(engine)
        # Load lib.lua first (provides DIR_NAMES etc.)
        lib_src = (
            Path(__file__).parent.parent / "games" / "common" / "lua" / "lib.lua"
        ).read_text(encoding="utf-8")
        runtime.load_source(lib_src)
        lua_src = (
            Path(__file__).parent.parent / "games" / "common" / "lua" / "commands" / "core.lua"
        ).read_text(encoding="utf-8")
        runtime.load_source(lua_src)
        handler = runtime.wrap_command("exits")
        await handler(session, "")
        calls = [str(c) for c in session.send_line.call_args_list]
        assert any("출구" in c or "사용 가능" in c for c in calls)
        assert any("북" in c for c in calls)
        assert any("길" in c for c in calls)


# ── Seed / Load cycle (mocked DB) ───────────────────────────────


class TestSeedAndLoad:
    @pytest.mark.asyncio
    async def test_seed_from_files(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        # Mock DB
        db = MagicMock()
        upserted = []

        async def mock_upsert(**kwargs):
            upserted.append(kwargs)
            return {"game": kwargs["game"], "category": kwargs["category"],
                    "name": kwargs["name"], "source": kwargs["source"],
                    "version": 1, "updated_at": "now"}

        db.upsert_lua_script = mock_upsert

        count = await runtime.seed_from_files(db, "tbamud")
        # Should have seeded at least lib.lua and commands/core.lua from common
        assert count >= 2
        names = [u["name"] for u in upserted]
        assert "lib" in names
        assert "core" in names

    @pytest.mark.asyncio
    async def test_load_from_db(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        db = MagicMock()

        # Return lib.lua and core.lua from "DB"
        from pathlib import Path
        lib_src = (
            Path(__file__).parent.parent / "games" / "common" / "lua" / "lib.lua"
        ).read_text(encoding="utf-8")
        core_src = (
            Path(__file__).parent.parent / "games" / "common" / "lua" / "commands" / "core.lua"
        ).read_text(encoding="utf-8")

        async def mock_fetch(game):
            if game == "common":
                return [
                    {"game": "common", "category": "lib", "name": "lib",
                     "source": lib_src, "version": 1},
                    {"game": "common", "category": "commands", "name": "core",
                     "source": core_src, "version": 1},
                ]
            return []

        db.fetch_lua_scripts = mock_fetch

        count = await runtime.load_from_db(db, "tbamud")
        assert count == 2
        assert runtime.has_command("say")
        assert runtime.has_command("who")
        assert runtime.has_command("exits")
        assert runtime.get_korean_cmd("말") == "say"
        assert runtime.get_korean_cmd("누구") == "who"
        assert runtime.get_korean_cmd("출구") == "exits"


# ── HookContext tests ────────────────────────────────────────────


class TestHookContext:
    def test_send_broadcasts_to_room(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        room = engine.world.rooms[3001]
        ctx = HookContext(engine, room)
        ctx.send("전체 메시지")
        # Should have 1 message (to the one character in room)
        assert len(ctx._messages) == 1

    @pytest.mark.asyncio
    async def test_flush(self):
        engine = _make_engine()
        session = _make_session(engine, 3001)
        room = engine.world.rooms[3001]
        ctx = HookContext(engine, room)
        ctx.send("hello")
        await ctx.flush()
        session.send_line.assert_awaited_once_with("hello")


# ── Integration: lib.lua loaded before commands ──────────────────


class TestLibLuaIntegration:
    def test_lib_functions_available(self):
        engine = _make_engine()
        runtime = LuaCommandRuntime(engine)
        lib_src = (
            Path(__file__).parent.parent / "games" / "common" / "lua" / "lib.lua"
        ).read_text(encoding="utf-8")
        runtime.load_source(lib_src)

        # Test lib functions are available in Lua
        runtime.load_source("""
            register_command("test_lib", function(ctx, args)
                ctx:send("format: " .. format_number(1234567))
                local parts = split("hello world")
                ctx:send("split: " .. #parts)
                ctx:send("trim: [" .. trim("  hi  ") .. "]")
                ctx:send("POS: " .. tostring(POS_STANDING))
            end)
        """)

        session = _make_session(engine, 3001)
        ctx = CommandContext(session, engine)
        lua_fn = runtime._commands["test_lib"]
        lua_fn(ctx, "")

        msgs = [msg for _, msg in ctx._messages]
        assert "format: 1,234,567" in msgs
        assert "split: 2" in msgs
        assert "trim: [hi]" in msgs
        assert "POS: 8" in msgs


# need pathlib for reading Lua files
from pathlib import Path
