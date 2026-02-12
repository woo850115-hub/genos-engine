"""Simoon login state machine — race(5) + class(7) character creation."""

from __future__ import annotations

import random
from typing import Any

import bcrypt

from games.simoon.constants import (
    CLASS_ABBREV, CLASS_INITIAL_HP, CLASS_INITIAL_MANA, CLASS_NAMES,
    MORTAL_START_ROOM, RACE_ALLOWED_CLASSES, RACE_NAMES, RACE_STAT_MODS,
)


class SimoonGetNameState:
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
            return SimoonGetPasswordState()
        else:
            session.player_data = {"name": name}
            await session.send_line(f"\r\n{name}... 새로운 모험가이시군요!")
            return SimoonNewPasswordState()


class SimoonGetPasswordState:
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
            return SimoonGetNameState()


class SimoonNewPasswordState:
    """Step 3: Set password for new character."""

    def prompt(self) -> str:
        return "비밀번호를 설정해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        if len(text) < 4:
            await session.send_line("비밀번호는 4자 이상이어야 합니다.")
            return None
        session.player_data["_password"] = text
        return SimoonConfirmPasswordState()


class SimoonConfirmPasswordState:
    """Step 4: Confirm password."""

    def prompt(self) -> str:
        return "비밀번호를 다시 입력해주세요: "

    async def on_input(self, session: Any, text: str) -> Any:
        if text != session.player_data.get("_password"):
            await session.send_line("비밀번호가 일치하지 않습니다. 다시 설정해주세요.")
            session.player_data.pop("_password", None)
            return SimoonNewPasswordState()
        pw_hash = bcrypt.hashpw(text.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        session.player_data["password_hash"] = pw_hash
        session.player_data.pop("_password", None)
        return SimoonSelectGenderState()


class SimoonSelectGenderState:
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
            session.player_data["sex"] = int(text)  # 1=male, 2=female
            return SimoonSelectRaceState()
        await session.send_line("1 또는 2를 입력해주세요.")
        return None


class SimoonSelectRaceState:
    """Step 6: Race selection (5 races)."""

    def prompt(self) -> str:
        lines = ["\r\n종족을 선택해주세요:"]
        for rid in sorted(RACE_NAMES):
            lines.append(f"  [{rid + 1}] {RACE_NAMES[rid]}")
        lines.append("선택: ")
        return "\r\n".join(lines)

    async def on_input(self, session: Any, text: str) -> Any:
        try:
            choice = int(text) - 1
        except ValueError:
            await session.send_line("숫자를 입력해주세요.")
            return None

        if choice not in RACE_NAMES:
            await session.send_line("1~5 중에서 선택해주세요.")
            return None

        session.player_data["race_id"] = choice
        return SimoonSelectClassState(choice)


class SimoonSelectClassState:
    """Step 7: Class selection (7 classes, race-restricted)."""

    def __init__(self, race_id: int) -> None:
        self._race_id = race_id
        self._allowed = RACE_ALLOWED_CLASSES.get(race_id, list(range(7)))

    def prompt(self) -> str:
        race_name = RACE_NAMES.get(self._race_id, "?")
        lines = [f"\r\n{race_name}이(가) 선택할 수 있는 직업:"]
        for i, cid in enumerate(self._allowed, 1):
            lines.append(f"  [{i}] {CLASS_NAMES[cid]} ({CLASS_ABBREV[cid]})")
        lines.append("선택: ")
        return "\r\n".join(lines)

    async def on_input(self, session: Any, text: str) -> Any:
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

        # Roll stats (4d6 drop lowest)
        def roll_stat() -> int:
            rolls = sorted(random.randint(1, 6) for _ in range(4))
            return sum(rolls[1:])

        stats = {
            "str": roll_stat(), "dex": roll_stat(), "con": roll_stat(),
            "int": roll_stat(), "wis": roll_stat(), "cha": roll_stat(),
        }

        # Apply race stat mods
        for key, mod in RACE_STAT_MODS.get(self._race_id, {}).items():
            stats[key] = max(3, min(25, stats.get(key, 13) + mod))

        # Class stat emphasis
        emphasis = {0: "int", 1: "wis", 2: "dex", 3: "str", 4: "int", 5: "str", 6: "int"}
        if class_id in emphasis:
            k = emphasis[class_id]
            stats[k] = min(18, stats[k] + 2)

        start_room = session.config.get("world", {}).get("start_room", MORTAL_START_ROOM)
        initial_hp = CLASS_INITIAL_HP.get(class_id, 14)
        initial_mana = CLASS_INITIAL_MANA.get(class_id, 50)

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
        session.player_data["mana"] = initial_mana
        session.player_data["max_mana"] = initial_mana
        session.player_data["practices"] = 5

        race_name = RACE_NAMES.get(self._race_id, "?")
        class_name = CLASS_NAMES.get(class_id, "?")
        await session.send_line(f"\r\n{session.player_data['name']} 캐릭터가 생성되었습니다!")
        await session.send_line(f"종족: {race_name}  직업: {class_name}")
        await session.send_line(
            f"스탯: 힘 {stats['str']} 민첩 {stats['dex']} 체력 {stats['con']} "
            f"지능 {stats['int']} 지혜 {stats['wis']} 매력 {stats['cha']}"
        )
        await session.enter_game()
        return session.state
