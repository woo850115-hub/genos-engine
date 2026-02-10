"""Session management — login state machine + playing state."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol, runtime_checkable

import bcrypt

from core.ansi import colorize
from core.net import TelnetConnection
from core.world import MobInstance, Room, World, _next_id

log = logging.getLogger(__name__)


@runtime_checkable
class SessionState(Protocol):
    """Protocol for login flow states."""

    async def on_input(self, session: Session, text: str) -> SessionState | None:
        """Process input, return next state or None to stay."""
        ...

    def prompt(self) -> str:
        """Return the prompt to show."""
        ...


class Session:
    """Represents a connected player session."""

    def __init__(
        self,
        conn: TelnetConnection,
        engine: Any,
    ) -> None:
        self.conn = conn
        self.engine = engine
        self.db = engine.db
        self.world: World = engine.world
        self.config: dict = engine.config
        self.state: SessionState | None = None
        self.character: MobInstance | None = None
        self.player_data: dict[str, Any] = {}
        self._closed = False

    async def send(self, text: str) -> None:
        await self.conn.send(colorize(text))

    async def send_line(self, text: str = "") -> None:
        await self.conn.send_line(colorize(text))

    async def run(self) -> None:
        """Main session loop — drives the state machine."""
        # Set initial state (login)
        self.state = GetNameState()
        await self.send_line(self._welcome_banner())
        await self.send(self.state.prompt())

        while not self._closed and not self.conn.closed:
            try:
                text = await asyncio.wait_for(self.conn.get_input(), timeout=300)
            except asyncio.TimeoutError:
                await self.send_line("\r\n연결 시간이 초과되었습니다. 안녕히 가세요.")
                break

            text = text.strip()
            if self.state is None:
                break

            next_state = await self.state.on_input(self, text)
            if next_state is not None:
                self.state = next_state
                await self.send(self.state.prompt())

        await self._disconnect()

    async def enter_game(self) -> None:
        """Transition from login to playing state."""
        pd = self.player_data
        start_room = pd.get("room_vnum", self.config.get("world", {}).get("start_room", 3001))

        # Create MobInstance for player
        from core.world import MobProto
        dummy_proto = MobProto(
            vnum=-1, keywords=pd["name"], short_description=pd["name"],
            long_description=f"{pd['name']}이(가) 서 있습니다.",
            detailed_description="", level=pd.get("level", 1),
            hitroll=pd.get("hitroll", 0), armor_class=pd.get("armor_class", 100),
            hp_dice="0d0+0", damage_dice="1d4+0",
            gold=pd.get("gold", 0), experience=pd.get("experience", 0),
            action_flags=[], affect_flags=[], alignment=pd.get("alignment", 0),
            sex=pd.get("sex", 0), trigger_vnums=[],
        )
        char = MobInstance(
            id=_next_id(), proto=dummy_proto, room_vnum=start_room,
            hp=pd.get("hp", 20), max_hp=pd.get("max_hp", 20),
            mana=pd.get("mana", 100), gold=pd.get("gold", 0),
            player_id=pd.get("id"), player_name=pd["name"],
            session=self,
        )
        self.character = char

        # Place character in room
        self.world.char_to_room(char, start_room)

        # Register with engine
        self.engine.sessions[self.conn.id] = self
        self.engine.players[pd["name"].lower()] = self

        await self.send_line(f"\r\n{{{pd['name']}}}님이 게임에 입장합니다.\r\n")
        self.state = PlayingState()

        # Show room
        await self.engine.do_look(self, "")

        await self.send(self.state.prompt())

    async def _disconnect(self) -> None:
        if self.character:
            await self.save_character()
            self.world.char_from_room(self.character)
            self.engine.sessions.pop(self.conn.id, None)
            if self.player_data.get("name"):
                self.engine.players.pop(self.player_data["name"].lower(), None)
            log.info("Player %s disconnected", self.character.name)
        self._closed = True

    async def save_character(self) -> None:
        """Save character state to DB."""
        if not self.character or not self.character.player_id:
            return
        c = self.character
        data = {
            "hp": c.hp, "max_hp": c.max_hp,
            "mana": c.mana, "room_vnum": c.room_vnum,
            "gold": c.gold,
        }
        await self.db.save_player(c.player_id, data)

    def _welcome_banner(self) -> str:
        return (
            "\r\n{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n"
            "   {bold}{yellow}GenOS tbaMUD-KR{reset}\r\n"
            "   한국어 머드 게임 서버\r\n"
            "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}\r\n\r\n"
        )


# ── Login states ─────────────────────────────────────────────────


class GetNameState:
    def prompt(self) -> str:
        return "이름을 입력해주세요: "

    async def on_input(self, session: Session, text: str) -> SessionState | None:
        name = text.strip()
        if not name or len(name.encode("utf-8")) > 15:
            await session.send_line("이름은 UTF-8 15바이트 이내로 입력해주세요.")
            return None

        # Check if player exists
        row = await session.db.fetch_player(name)
        if row:
            session.player_data = dict(row)
            await session.send_line(f"\r\n{name}님 돌아오셨군요!")
            return GetPasswordState()
        else:
            session.player_data = {"name": name}
            await session.send_line(f"\r\n{name}... 새로운 모험가이시군요!")
            return NewPasswordState()


class GetPasswordState:
    def prompt(self) -> str:
        return "비밀번호를 입력해주세요: "

    async def on_input(self, session: Session, text: str) -> SessionState | None:
        await session.conn.set_echo(False)
        stored_hash = session.player_data.get("password_hash", "")
        if bcrypt.checkpw(text.encode("utf-8"), stored_hash.encode("utf-8")):
            await session.conn.set_echo(True)
            await session.send_line("\r\n인증 성공!")
            # Update last_login
            await session.db.save_player(session.player_data["id"], {})
            await session.enter_game()
            return session.state
        else:
            await session.conn.set_echo(True)
            await session.send_line("\r\n비밀번호가 틀렸습니다.")
            return GetNameState()


class NewPasswordState:
    def prompt(self) -> str:
        return "비밀번호를 설정해주세요: "

    async def on_input(self, session: Session, text: str) -> SessionState | None:
        if len(text) < 4:
            await session.send_line("비밀번호는 4자 이상이어야 합니다.")
            return None
        session.player_data["_password"] = text
        return ConfirmPasswordState()


class ConfirmPasswordState:
    def prompt(self) -> str:
        return "비밀번호를 다시 입력해주세요: "

    async def on_input(self, session: Session, text: str) -> SessionState | None:
        if text != session.player_data.get("_password"):
            await session.send_line("비밀번호가 일치하지 않습니다. 다시 설정해주세요.")
            session.player_data.pop("_password", None)
            return NewPasswordState()
        # Hash password
        pw_hash = bcrypt.hashpw(text.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        session.player_data["password_hash"] = pw_hash
        session.player_data.pop("_password", None)
        return SelectSexState()


class SelectSexState:
    def prompt(self) -> str:
        return (
            "\r\n성별을 선택해주세요:\r\n"
            "  [1] 중성\r\n"
            "  [2] 남성\r\n"
            "  [3] 여성\r\n"
            "선택: "
        )

    async def on_input(self, session: Session, text: str) -> SessionState | None:
        if text in ("1", "2", "3"):
            session.player_data["sex"] = int(text) - 1  # 0=neutral, 1=male, 2=female
            return SelectClassState()
        await session.send_line("1, 2, 또는 3을 입력해주세요.")
        return None


class SelectClassState:
    def prompt(self) -> str:
        return (
            "\r\n직업을 선택해주세요:\r\n"
            "  [1] 마법사 (Magic User)\r\n"
            "  [2] 성직자 (Cleric)\r\n"
            "  [3] 도적 (Thief)\r\n"
            "  [4] 전사 (Warrior)\r\n"
            "선택: "
        )

    async def on_input(self, session: Session, text: str) -> SessionState | None:
        if text in ("1", "2", "3", "4"):
            class_id = int(text) - 1  # 0~3
            session.player_data["class_id"] = class_id
            start_room = session.config.get("world", {}).get("start_room", 3001)

            # Create player in DB
            row = await session.db.create_player(
                name=session.player_data["name"],
                password_hash=session.player_data["password_hash"],
                sex=session.player_data["sex"],
                class_id=class_id,
                start_room=start_room,
            )
            session.player_data = dict(row)

            await session.send_line(f"\r\n{session.player_data['name']} 캐릭터가 생성되었습니다!")
            await session.enter_game()
            return session.state

        await session.send_line("1~4 중에서 선택해주세요.")
        return None


# ── Playing state ────────────────────────────────────────────────


class PlayingState:
    def prompt(self) -> str:
        return "\r\n> "

    async def on_input(self, session: Session, text: str) -> SessionState | None:
        if not text:
            return None
        await session.engine.process_command(session, text)
        return None
