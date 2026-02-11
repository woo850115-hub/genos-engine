"""10woongi login state machine — "새로" keyword for new characters."""

from __future__ import annotations

import importlib
from typing import Any

import bcrypt

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


class WoongiGetNameState:
    """Step 1: Name input. "새로" triggers new character creation."""

    def prompt(self) -> str:
        return '이름을 입력해주세요 ("새로" = 새 캐릭터): '

    async def on_input(self, session: Any, text: str) -> Any:
        name = text.strip()
        if not name:
            await session.send_line("이름을 입력해주세요.")
            return None

        # "새로" keyword → new character
        if name == "새로":
            await session.send_line("\r\n새로운 무림인이시군요!")
            return WoongiNewNameState()

        if len(name.encode("utf-8")) > 15:
            await session.send_line("이름은 UTF-8 15바이트 이내로 입력해주세요.")
            return None

        # Check if player exists
        row = await session.db.fetch_player(name)
        if row:
            session.player_data = dict(row)
            await session.send_line(f"\r\n{name}님 돌아오셨군요!")
            return WoongiGetPasswordState()
        else:
            await session.send_line(f"\r\n'{name}'이라는 이름의 무림인은 없습니다.")
            await session.send_line('새로 시작하려면 "새로"를 입력해주세요.')
            return None


class WoongiNewNameState:
    """Step 1b: Enter name for new character."""

    def prompt(self) -> str:
        return "새 캐릭터의 이름을 입력해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        name = text.strip()
        if not name or len(name.encode("utf-8")) > 15:
            await session.send_line("이름은 UTF-8 15바이트 이내로 입력해주세요.")
            return None

        # Check duplicate
        row = await session.db.fetch_player(name)
        if row:
            await session.send_line("이미 존재하는 이름입니다. 다른 이름을 입력해주세요.")
            return None

        session.player_data = {"name": name}
        return WoongiNewPasswordState()


class WoongiGetPasswordState:
    """Step 2: Password for existing player."""

    def prompt(self) -> str:
        return "비밀번호를 입력해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        stored_hash = session.player_data.get("password_hash", "")
        if bcrypt.checkpw(text.encode("utf-8"), stored_hash.encode("utf-8")):
            await session.send_line("\r\n인증 성공!")
            await session.db.save_player(session.player_data["id"], {})
            await session.enter_game()
            return session.state
        else:
            await session.send_line("\r\n비밀번호가 틀렸습니다.")
            return WoongiGetNameState()


class WoongiNewPasswordState:
    """Step 3: Set password for new character."""

    def prompt(self) -> str:
        return "비밀번호를 설정해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        if len(text) < 4:
            await session.send_line("비밀번호는 4자 이상이어야 합니다.")
            return None
        session.player_data["_password"] = text
        return WoongiConfirmPasswordState()


class WoongiConfirmPasswordState:
    """Step 4: Confirm password."""

    def prompt(self) -> str:
        return "비밀번호를 다시 입력해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        if text != session.player_data.get("_password"):
            await session.send_line("비밀번호가 일치하지 않습니다. 다시 설정해주세요.")
            session.player_data.pop("_password", None)
            return WoongiNewPasswordState()
        pw_hash = bcrypt.hashpw(text.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        session.player_data["password_hash"] = pw_hash
        session.player_data.pop("_password", None)
        return WoongiSelectGenderState()


class WoongiSelectGenderState:
    """Step 5: Gender selection (1=남, 2=여)."""

    def prompt(self) -> str:
        return (
            "\r\n성별을 선택해주세요:\r\n"
            "  [1] 남성\r\n"
            "  [2] 여성\r\n"
            "선택: "
        )

    async def on_input(self, session: Any, text: str) -> Any:
        if text in ("1", "2"):
            session.player_data["sex"] = int(text)  # 1=male, 2=female
            return WoongiSelectClassState()
        await session.send_line("1 또는 2를 입력해주세요.")
        return None


class WoongiSelectClassState:
    """Step 6: Class selection (only 투사 at start)."""

    def prompt(self) -> str:
        return (
            "\r\n직업을 선택해주세요:\r\n"
            "  [1] 투사\r\n"
            "선택: "
        )

    async def on_input(self, session: Any, text: str) -> Any:
        if text == "1":
            session.player_data["class_id"] = 1  # 투사
            stats = _import("stats")

            # Generate random starting stats
            starting_stats = {
                "stamina": stats.random_stat(),   # 체력
                "agility": stats.random_stat(),   # 민첩
                "wisdom": stats.random_stat(),    # 지혜
                "bone": stats.random_stat(),      # 기골
                "inner": stats.random_stat(),     # 내공
                "spirit": stats.random_stat(),    # 투지
            }

            hp = stats.calc_hp(starting_stats["bone"])
            sp = stats.calc_sp(starting_stats["inner"], starting_stats["wisdom"])
            mp = stats.calc_mp(starting_stats["agility"])

            start_room = session.config.get("world", {}).get("start_room", 1392841419)

            extensions = {
                "sp": sp,
                "max_sp": sp,
                "stats": starting_stats,
                "faction": None,
            }

            # Create player in DB
            row = await session.db.create_player(
                name=session.player_data["name"],
                password_hash=session.player_data["password_hash"],
                sex=session.player_data["sex"],
                class_id=1,
                start_room=start_room,
            )
            player_data = dict(row)

            # Set calculated stats
            player_data["hp"] = hp
            player_data["max_hp"] = hp
            player_data["mana"] = mp  # MP mapped to mana column
            player_data["max_mana"] = mp
            player_data["move_points"] = sp
            player_data["max_move"] = sp

            # Save extensions
            await session.db.save_player(player_data["id"], {
                "hp": hp,
                "max_hp": hp,
                "mana": mp,
                "max_mana": mp,
                "move_points": sp,
                "max_move": sp,
                "extensions": extensions,
            })

            session.player_data = player_data
            session.player_data["extensions"] = extensions

            await session.send_line(
                f"\r\n{session.player_data['name']} 캐릭터가 생성되었습니다!"
            )
            await session.send_line(
                f"  HP: {hp}  SP: {sp}  MP: {mp}"
            )
            await session.enter_game()
            return session.state

        await session.send_line("1을 입력해주세요.")
        return None
