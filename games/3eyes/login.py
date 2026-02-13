"""3eyes login state machine — original-faithful 10-state flow.

Matches command1.c login()/create_ply() from the original 3eyes source:
  접속 → 로고 → 이름 → (기존: 암호→메뉴→게임 / 신규: 확인→성별→직업(4)→종족(4)→암호→끊기)
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import Any

import bcrypt

_PKG = "games.3eyes"


def _const():
    return importlib.import_module(f"{_PKG}.constants")


# ── State 1: GetName ─────────────────────────────────────────────


class ThreeEyesGetNameState:
    """Ask player name (Korean only, 1-5 chars)."""

    def prompt(self) -> str:
        return "\n당신의 {bright_green}이름{white}은? "

    async def on_input(self, session: Any, text: str) -> Any:
        name = text.strip()
        if not name:
            await session.send_line("")
            return None

        # Validate: Korean only, 1-5 chars
        korean_chars = re.findall(r'[\uac00-\ud7af]', name)
        if len(korean_chars) != len(name):
            await session.send_line("{bright_green}한글{white}이름만 됩니다.")
            return None
        if len(korean_chars) < 1 or len(korean_chars) > 5:
            await session.send_line("한글로 1글자 ~ 5글자 이하로 입력하세요.")
            return None

        row = await session.db.fetch_player(name)
        if row:
            session.player_data = dict(row)
            return ThreeEyesGetPasswordState()
        else:
            session.player_data = {"name": name}
            return ThreeEyesConfirmNewState(name)


# ── State 2: ConfirmNew ──────────────────────────────────────────


class ThreeEyesConfirmNewState:
    """Confirm new character creation: '이름으로 새 ID를 만드시겠습니까?'"""

    def __init__(self, name: str = "") -> None:
        self._prompt_text = (
            f"\n{{bright_green}}{name}{{white}}이라는 이름으로 "
            "새 ID를 만드시겠습니까?\n\n"
            "{bright_green}1{white}.예    "
            "{bright_green}2{white}.아니오\n\n:"
        )

    def prompt(self) -> str:
        return self._prompt_text

    async def on_input(self, session: Any, text: str) -> Any:
        choice = text.strip()
        if choice == "1" or choice.lower() == "y":
            return ThreeEyesSelectGenderState()
        else:
            session.player_data = {}
            return ThreeEyesGetNameState()


# ── State 3: GetPassword (existing player, 3 tries) ─────────────


class ThreeEyesGetPasswordState:
    """Password check for existing player (max 3 attempts)."""

    def __init__(self) -> None:
        self._attempts = 0

    def prompt(self) -> str:
        return "당신의 {bright_green}암호{white}는? "

    async def on_input(self, session: Any, text: str) -> Any:
        stored_hash = session.player_data.get("password_hash", "")
        if stored_hash and bcrypt.checkpw(
            text.encode("utf-8"), stored_hash.encode("utf-8")
        ):
            return ThreeEyesMainMenuState()
        else:
            self._attempts += 1
            await session.send_line("\r\n암호가 맞지 않습니다.")
            if self._attempts >= 3:
                await session.send_line(
                    "암호를 다시 생각한 뒤 접속해 주시기 바랍니다."
                )
                await session.disconnect()
                return None
            return None  # re-prompt


# ── State 4: MainMenu ───────────────────────────────────────────


class ThreeEyesMainMenuState:
    """Main menu (6 options) — original menu display."""

    def prompt(self) -> str:
        menu_file = (
            Path(__file__).resolve().parent.parent.parent
            / "data" / "3eyes" / "menu.txt"
        )
        try:
            menu_text = menu_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            menu_text = (
                "\n1.제3의눈으로..\n2.\n3.비밀번호변경\n"
                "4.비밀번호분실\n5.캐릭터삭제\n6.종료\n"
            )
        return menu_text + "\n원하는 메뉴번호를 선택하세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        choice = text.strip()
        if choice == "1":
            return ThreeEyesNewsState()
        elif choice == "3":
            return ThreeEyesChangePasswordState()
        elif choice == "6":
            await session.disconnect()
            return None
        elif choice in ("2", "4", "5"):
            await session.send_line("이 기능은 현재 지원되지 않습니다.")
            return None  # re-prompt menu
        else:
            return None  # re-prompt menu


# ── State 5: News → Enter Game ───────────────────────────────────


class ThreeEyesNewsState:
    """Show news, then enter game on ENTER."""

    def __init__(self) -> None:
        self._shown = False

    def prompt(self) -> str:
        if not self._shown:
            self._shown = True
            news_file = (
                Path(__file__).resolve().parent.parent.parent
                / "data" / "3eyes" / "news.txt"
            )
            try:
                news_text = news_file.read_text(encoding="utf-8")
            except FileNotFoundError:
                news_text = "뉴스가 없습니다.\n"
            return news_text + "\n{bright_green}[ENTER]{white}를 누르세요"
        return "{bright_green}[ENTER]{white}를 누르세요"

    async def on_input(self, session: Any, text: str) -> Any:
        # Show last login time
        last_login = session.player_data.get("last_login")
        if last_login:
            try:
                await session.send_line(
                    f"\n마지막 게임시간: {last_login.month}월 "
                    f"{last_login.day}일 {last_login.hour}시 "
                    f"{last_login.minute}분."
                )
            except (AttributeError, TypeError):
                pass

        await session.db.save_player(session.player_data["id"], {})
        await session.enter_game()
        return session.state


# ── State 6: ChangePassword ──────────────────────────────────────


class ThreeEyesChangePasswordState:
    """Change password: current → new."""

    def __init__(self) -> None:
        self._step = 0  # 0=current pw, 1=new pw

    def prompt(self) -> str:
        if self._step == 0:
            return "\n현재 암호를 입력하세요: "
        return "\n새로운 암호를 입력하세요 (5자~14자): "

    async def on_input(self, session: Any, text: str) -> Any:
        if self._step == 0:
            stored_hash = session.player_data.get("password_hash", "")
            if stored_hash and bcrypt.checkpw(
                text.encode("utf-8"), stored_hash.encode("utf-8")
            ):
                self._step = 1
                return None  # re-prompt for new password
            else:
                await session.send_line("암호가 맞지 않습니다.")
                return ThreeEyesMainMenuState()
        else:
            if len(text) < 5:
                await session.send_line("5자이상 입력하셔야 합니다.")
                return None
            if len(text) > 14:
                await session.send_line("14자이상 초과하면 안됩니다.")
                return None
            pw_hash = bcrypt.hashpw(
                text.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            session.player_data["password_hash"] = pw_hash
            await session.db.save_player(
                session.player_data["id"],
                {"password_hash": pw_hash},
            )
            await session.send_line("암호가 변경되었습니다.")
            return ThreeEyesMainMenuState()


# ── State 7: SelectGender ────────────────────────────────────────


class ThreeEyesSelectGenderState:
    """Gender selection: 남/여."""

    def prompt(self) -> str:
        return (
            "당신은 남자인가요? 여자인가요?\n"
            "{bright_green}1{white}. 남   "
            "{bright_green}2{white}. 여\n\n:"
        )

    async def on_input(self, session: Any, text: str) -> Any:
        choice = text.strip()
        if choice in ("1", "남"):
            session.player_data["sex"] = 1
            return ThreeEyesSelectClassState()
        elif choice in ("2", "여"):
            session.player_data["sex"] = 2
            return ThreeEyesSelectClassState()
        else:
            return None  # re-prompt


# ── State 8: SelectClass (4 classes) ─────────────────────────────


class ThreeEyesSelectClassState:
    """Class selection from original 4 classes."""

    def prompt(self) -> str:
        return (
            "{bright_green}1{white}.도  둑    "
            "{bright_green}2{white}.권법가\n"
            "{bright_green}3{white}.마법사    "
            "{bright_green}4{white}.검  사\n"
            "\n어떤 직업으로 하시겠습니까?.\n:"
        )

    async def on_input(self, session: Any, text: str) -> Any:
        c = _const()
        choice = text.strip()
        if choice in ("1", "2", "3", "4"):
            idx = int(choice) - 1
            class_id, _ = c.CREATE_CLASSES[idx]
            session.player_data["class_id"] = class_id
            # Initialize stats to 10 (original: all stats = 10)
            session.player_data["_stats"] = {
                "str": 10, "dex": 10, "con": 10, "int": 10, "pie": 10,
            }
            return ThreeEyesSelectRaceState()
        else:
            await session.send_line("잘못된 선택입니다. 다시 선택하세요: ")
            return None


# ── State 9: SelectRace (4 races) ────────────────────────────────


class ThreeEyesSelectRaceState:
    """Race selection from original 4 races."""

    def prompt(self) -> str:
        return (
            "\n{bright_green}1.{white}요정족    "
            "{bright_green}2{white}.드래곤족\n"
            "{bright_green}3.{white}인간족    "
            "{bright_green}4{white}.마족\n"
            "\n어떤 종족으로 하시겠습니까? : "
        )

    async def on_input(self, session: Any, text: str) -> Any:
        c = _const()
        choice = text.strip()
        if choice in ("1", "2", "3", "4"):
            idx = int(choice) - 1
            race_id, _ = c.CREATE_RACES[idx]
            session.player_data["race_id"] = race_id

            # Apply race stat mods to base 10 stats
            stats = session.player_data["_stats"]
            for key, mod in c.RACE_STAT_MODS.get(race_id, {}).items():
                stats[key] = max(3, min(63, stats.get(key, 10) + mod))
            session.player_data["_stats"] = stats

            return ThreeEyesSetPasswordState()
        else:
            await session.send_line("\n잘못되었습니다. 다시 선택하세요: ")
            return None


# ── State 10: SetPassword (new character) ────────────────────────


class ThreeEyesSetPasswordState:
    """Set password for new character (5-14 chars)."""

    def prompt(self) -> str:
        return "\n암호를 입력하세요 (5자~14자): "

    async def on_input(self, session: Any, text: str) -> Any:
        c = _const()
        pw = text.strip()

        if len(pw) > 14:
            await session.send_line("14자이상 초과하면 안됩니다.")
            return None
        if len(pw) < 5:
            await session.send_line("5자이상 입력하셔야 합니다.")
            return None
        # Check password != name (too easy)
        if pw == session.player_data.get("name", ""):
            await session.send_line(
                "암호가 너무 쉽습니다 영문자(abc...)를 섞어 주세요"
            )
            return None
        if "1234" in pw or "1111" in pw:
            await session.send_line(
                "암호가 너무 쉽습니다 영문자(abc...)를 섞어 주세요"
            )
            return None

        pw_hash = bcrypt.hashpw(
            pw.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        stats = session.player_data.pop("_stats", {
            "str": 10, "dex": 10, "con": 10, "int": 10, "pie": 10,
        })
        class_id = session.player_data.get("class_id", 4)
        race_id = session.player_data.get("race_id", 5)

        start_room = getattr(session, "config", {}).get(
            "world", {}
        ).get("start_room", c.MORTAL_START_ROOM)

        cls = c.CLASS_STATS.get(class_id, c.CLASS_STATS[4])
        initial_hp = cls["hp_start"]
        initial_mp = cls["mp_start"]

        # Create player in DB
        row = await session.db.create_player(
            name=session.player_data["name"],
            password_hash=pw_hash,
            sex=session.player_data.get("sex", 1),
            class_id=class_id,
            start_room=start_room,
        )
        session.player_data = dict(row)
        session.player_data["stats"] = stats
        session.player_data["race_id"] = race_id
        session.player_data["hp"] = initial_hp
        session.player_data["max_hp"] = initial_hp
        session.player_data["mana"] = initial_mp
        session.player_data["max_mana"] = initial_mp
        session.player_data["gold"] = c.INITIAL_GOLD

        # Initialize proficiency/realm
        session.player_data.setdefault("extensions", {})
        session.player_data["extensions"]["proficiency"] = [0, 0, 0, 0, 0]
        session.player_data["extensions"]["realm"] = [0, 0, 0, 0]

        # Give initial items (original create_ply case 100)
        session.player_data.setdefault("inventory", [])
        for item_vnum in c.INITIAL_ITEMS:
            session.player_data["inventory"].append(item_vnum)

        await session.send_line(
            "\r\n\nID를 만드셨습니다. "
            "새로 만든 ID로 다시 접속해 주십시요"
        )
        await session.send_line(
            "{bright_green}[ENTER]{white}를 누르세요"
        )

        return ThreeEyesDisconnectState()


# ── Disconnect state (after new char creation) ───────────────────


class ThreeEyesDisconnectState:
    """Wait for ENTER then disconnect (original create_ply case 100)."""

    def prompt(self) -> str:
        return ""

    async def on_input(self, session: Any, text: str) -> Any:
        await session.disconnect()
        return None
