"""3eyes login state machine — 8 races, 8 classes, stat rolling."""

from __future__ import annotations

import importlib
import random
from typing import Any

import bcrypt

_PKG = "games.3eyes"


def _const():
    return importlib.import_module(f"{_PKG}.constants")


class ThreeEyesGetNameState:
    """Step 1: Name input."""

    def prompt(self) -> str:
        return "이름을 입력해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        name = text.strip()
        if not name or len(name.encode("utf-8")) > 15:
            await session.send_line("이름은 UTF-8 15바이트 이내로 입력해주세요.")
            return None

        row = await session.db.fetch_player(name)
        if row:
            session.player_data = dict(row)
            await session.send_line(f"\r\n{name}님 돌아오셨군요!")
            return ThreeEyesGetPasswordState()
        else:
            session.player_data = {"name": name}
            await session.send_line(f"\r\n{name}... 새로운 모험가이시군요!")
            return ThreeEyesNewPasswordState()


class ThreeEyesGetPasswordState:
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
            return ThreeEyesGetNameState()


class ThreeEyesNewPasswordState:
    """Step 3: Set password for new character."""

    def prompt(self) -> str:
        return "비밀번호를 설정해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        if len(text) < 4:
            await session.send_line("비밀번호는 4자 이상이어야 합니다.")
            return None
        session.player_data["_password"] = text
        return ThreeEyesConfirmPasswordState()


class ThreeEyesConfirmPasswordState:
    """Step 4: Confirm password."""

    def prompt(self) -> str:
        return "비밀번호를 다시 입력해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        if text != session.player_data.get("_password"):
            await session.send_line("비밀번호가 일치하지 않습니다. 다시 설정해주세요.")
            session.player_data.pop("_password", None)
            return ThreeEyesNewPasswordState()
        pw_hash = bcrypt.hashpw(text.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        session.player_data["password_hash"] = pw_hash
        session.player_data.pop("_password", None)
        return ThreeEyesSelectGenderState()


class ThreeEyesSelectGenderState:
    """Step 5: Gender selection."""

    def prompt(self) -> str:
        return (
            "\r\n성별을 선택해주세요:\r\n"
            "  [1] 남성\r\n"
            "  [2] 여성\r\n"
            "선택: "
        )

    async def on_input(self, session: Any, text: str) -> Any:
        if text in ("1", "2"):
            session.player_data["sex"] = int(text)
            return ThreeEyesSelectRaceState()
        await session.send_line("1 또는 2를 입력해주세요.")
        return None


class ThreeEyesSelectRaceState:
    """Step 6: Race selection (8 races)."""

    def prompt(self) -> str:
        c = _const()
        lines = ["\r\n종족을 선택해주세요:"]
        for rid in sorted(c.RACE_NAMES):
            lines.append(f"  [{rid}] {c.RACE_NAMES[rid]}")
        lines.append("선택: ")
        return "\r\n".join(lines)

    async def on_input(self, session: Any, text: str) -> Any:
        c = _const()
        try:
            choice = int(text)
        except ValueError:
            await session.send_line("숫자를 입력해주세요.")
            return None

        if choice not in c.RACE_NAMES:
            await session.send_line("1~8 중에서 선택해주세요.")
            return None

        session.player_data["race_id"] = choice
        return ThreeEyesSelectClassState(choice)


class ThreeEyesSelectClassState:
    """Step 7: Class selection (8 classes, race allows all)."""

    def __init__(self, race_id: int) -> None:
        c = _const()
        self._race_id = race_id
        self._allowed = c.RACE_ALLOWED_CLASSES.get(race_id, list(range(1, 9)))

    def prompt(self) -> str:
        c = _const()
        race_name = c.RACE_NAMES.get(self._race_id, "?")
        lines = [f"\r\n{race_name}의 직업을 선택해주세요:"]
        for i, cid in enumerate(self._allowed, 1):
            lines.append(f"  [{i}] {c.CLASS_NAMES[cid]} ({c.CLASS_ABBREV[cid]})")
        lines.append("선택: ")
        return "\r\n".join(lines)

    async def on_input(self, session: Any, text: str) -> Any:
        c = _const()
        try:
            idx = int(text) - 1
        except ValueError:
            await session.send_line("숫자를 입력해주세요.")
            return None

        if idx < 0 or idx >= len(self._allowed):
            await session.send_line(f"1~{len(self._allowed)} 중에서 선택해주세요.")
            return None

        class_id = self._allowed[idx]
        session.player_data["class_id"] = class_id

        # Roll stats (4d6 drop lowest, 5 stats: str/dex/con/int/pie)
        def roll_stat() -> int:
            rolls = sorted(random.randint(1, 6) for _ in range(4))
            return sum(rolls[1:])

        stats = {
            "str": roll_stat(), "dex": roll_stat(), "con": roll_stat(),
            "int": roll_stat(), "pie": roll_stat(),
        }

        # Apply race stat mods
        for key, mod in c.RACE_STAT_MODS.get(self._race_id, {}).items():
            stats[key] = max(3, min(63, stats.get(key, 13) + mod))

        start_room = session.config.get("world", {}).get(
            "start_room", c.MORTAL_START_ROOM,
        )
        cls = c.CLASS_STATS.get(class_id, c.CLASS_STATS[4])
        initial_hp = cls["hp_start"]
        initial_mp = cls["mp_start"]

        # Create player in DB
        row = await session.db.create_player(
            name=session.player_data["name"],
            password_hash=session.player_data["password_hash"],
            sex=session.player_data["sex"],
            class_id=class_id,
            start_room=start_room,
        )
        session.player_data = dict(row)
        session.player_data["stats"] = stats
        session.player_data["race_id"] = self._race_id
        session.player_data["hp"] = initial_hp
        session.player_data["max_hp"] = initial_hp
        session.player_data["mana"] = initial_mp
        session.player_data["max_mana"] = initial_mp
        # Initialize proficiency/realm in ext
        session.player_data.setdefault("extensions", {})
        session.player_data["extensions"]["proficiency"] = [0, 0, 0, 0, 0]
        session.player_data["extensions"]["realm"] = [0, 0, 0, 0]

        race_name = c.RACE_NAMES.get(self._race_id, "?")
        class_name = c.CLASS_NAMES.get(class_id, "?")
        await session.send_line(f"\r\n{session.player_data['name']} 캐릭터가 생성되었습니다!")
        await session.send_line(f"종족: {race_name}  직업: {class_name}")
        await session.send_line(
            f"스탯: 힘 {stats['str']} 민첩 {stats['dex']} 체력 {stats['con']} "
            f"지능 {stats['int']} 신앙 {stats['pie']}"
        )
        await session.enter_game()
        return session.state
