"""10woongi skill system — 51 skills from 기술.h mapping."""

from __future__ import annotations

import importlib
import random
from dataclasses import dataclass
from typing import Any

_PKG = "games.10woongi"


def _import(submodule: str) -> Any:
    return importlib.import_module(f"{_PKG}.{submodule}")


@dataclass
class WoongiSkill:
    id: int
    name: str
    korean_name: str
    category: str  # defense, attack, recovery, stealth, magic, utility
    sp_cost: int
    min_level: int
    class_ids: list[int]  # allowed class IDs
    description: str = ""


# ── Skill definitions (51 skills from 기술.h) ──────────────────

SKILLS: dict[int, WoongiSkill] = {}


def _def(id: int, name: str, kr: str, cat: str, sp: int, lv: int,
         classes: list[int], desc: str = "") -> None:
    SKILLS[id] = WoongiSkill(id, name, kr, cat, sp, lv, classes, desc)


# Defense skills (방어)
_def(1, "parry_l1", "패리1", "defense", 0, 1, [1, 2, 3, 4, 5], "기본 방어")
_def(2, "parry_l2", "패리2", "defense", 0, 20, [2, 3, 4, 5], "중급 방어")
_def(3, "parry_l3", "패리3", "defense", 0, 50, [3, 4, 5], "상급 방어")
_def(4, "shield_block", "방패방어", "defense", 5, 10, [1, 2, 3, 4, 5, 6, 7], "방패 방어")
_def(5, "absolute_defense", "절대방어", "defense", 30, 80, [4, 8], "절대 방어")

# Attack skills (공격)
_def(6, "counter_l1", "카운터1", "attack", 10, 15, [1, 2, 3, 4, 5, 9, 10, 11], "반격")
_def(7, "counter_l2", "카운터2", "attack", 20, 40, [3, 4, 5, 11], "강화 반격")
_def(8, "multi_attack", "연타", "attack", 15, 25, [1, 2, 3, 4, 5], "연속 공격")
_def(9, "final_attack", "파이널어택", "attack", 50, 70, [4, 11, 14], "최종 일격")
_def(10, "critical_hit", "크리티컬", "attack", 20, 30, [1, 2, 3, 4, 5, 9, 10, 11], "치명타")
_def(11, "backstab", "백스탭", "attack", 25, 20, [9, 10, 11], "기습 공격")
_def(12, "bash", "강타", "attack", 15, 15, [1, 2, 3, 4, 5], "강타")

# Recovery skills (회복)
_def(13, "heal_l1", "치료1", "recovery", 20, 1, [6, 7, 8, 5], "기본 치료")
_def(14, "heal_l2", "치료2", "recovery", 40, 30, [7, 8, 5], "중급 치료")
_def(15, "heal_l3", "치료3", "recovery", 80, 60, [8], "상급 치료")
_def(16, "pray_l1", "기도1", "recovery", 30, 10, [6, 7, 8], "기본 기도")
_def(17, "pray_l2", "기도2", "recovery", 60, 40, [7, 8], "중급 기도")
_def(18, "pray_l3", "기도3", "recovery", 100, 70, [8], "상급 기도")
_def(19, "resurrect", "부활", "recovery", 200, 90, [8], "사망 PC 부활")

# Stealth skills (은신)
_def(20, "steal", "훔치기", "stealth", 10, 5, [9, 10, 11], "아이템 훔치기")
_def(21, "stealth", "스텔스", "stealth", 15, 15, [9, 10, 11], "은신")
_def(22, "escape", "도주술", "stealth", 5, 10, [9, 10, 11], "도주")
_def(23, "detect_hidden", "감지", "stealth", 20, 25, [9, 10, 11, 12, 13, 14], "은신 감지")

# Magic skills (마법)
_def(24, "magic_missile", "매직미셜", "magic", 15, 1, [12, 13, 14], "마법 화살")
_def(25, "fireball", "파이어볼", "magic", 30, 20, [12, 13, 14], "화염구")
_def(26, "lightning_bolt", "라이트닝볼트", "magic", 35, 30, [13, 14], "번개")
_def(27, "ice_storm", "아이스스톰", "magic", 40, 40, [13, 14], "빙풍")
_def(28, "meteor", "메테오", "magic", 80, 70, [14], "운석 낙하")
_def(29, "energy_drain", "에너지드레인", "magic", 50, 50, [13, 14], "에너지 흡수")
_def(30, "sleep_spell", "슬립", "magic", 25, 15, [12, 13, 14], "수면")
_def(31, "blindness", "블라인드", "magic", 25, 15, [12, 13, 14], "실명")
_def(32, "dispel_magic", "디스펠", "magic", 30, 25, [12, 13, 14], "마법 해제")

# Utility skills (유틸)
_def(33, "recall", "귀환", "utility", 20, 1, list(range(1, 15)), "시작 위치 귀환")
_def(34, "enchant", "인첸트", "utility", 50, 40, [12, 13, 14], "장비 강화")
_def(35, "haste", "헤이스트", "utility", 40, 30, [12, 13, 14, 8], "이동속도 증가")
_def(36, "summon", "소환", "utility", 60, 50, [12, 13, 14, 8], "대상 소환")
_def(37, "cooking", "요리", "utility", 5, 1, list(range(1, 15)), "음식 제작")
_def(38, "identify", "감정", "utility", 10, 10, [12, 13, 14], "아이템 감정")
_def(39, "teleport", "텔레포트", "utility", 40, 35, [13, 14], "순간 이동")
_def(40, "cure_poison", "해독", "recovery", 20, 15, [6, 7, 8, 5], "독 치료")
_def(41, "bless", "축복", "recovery", 25, 20, [6, 7, 8], "축복 부여")
_def(42, "sanctuary", "성역", "recovery", 80, 60, [8], "성역 보호막")
_def(43, "armor_spell", "아머", "utility", 15, 5, [12, 13, 14, 6, 7, 8], "방어력 증가")
_def(44, "strength", "스트렝스", "utility", 20, 10, [12, 13, 14], "공격력 증가")
_def(45, "invisibility", "인비저", "stealth", 30, 20, [12, 13, 14], "투명화")
_def(46, "fly", "플라이", "utility", 25, 25, [12, 13, 14], "비행")
_def(47, "poison", "독", "magic", 25, 20, [9, 10, 11, 12, 13, 14], "독 부여")
_def(48, "earthquake", "어스퀘이크", "magic", 60, 55, [14], "지진")
_def(49, "word_of_recall", "귀환술", "utility", 30, 5, list(range(1, 15)), "즉시 귀환")
_def(50, "group_heal", "집단치료", "recovery", 100, 70, [8], "그룹 치료")
_def(51, "charm", "매혹", "magic", 50, 45, [13, 14], "NPC 매혹")


def find_skill(name: str) -> WoongiSkill | None:
    """Find skill by name or korean_name."""
    name_lower = name.lower()
    for skill in SKILLS.values():
        if skill.name == name_lower or skill.korean_name == name:
            return skill
    # Prefix match
    matches = [s for s in SKILLS.values()
               if s.name.startswith(name_lower) or s.korean_name.startswith(name)]
    if len(matches) == 1:
        return matches[0]
    return None


def can_use_skill(char: Any, skill_id: int) -> tuple[bool, str]:
    """Check if character can use a skill."""
    skill = SKILLS.get(skill_id)
    if not skill:
        return False, "그런 기술은 없습니다."
    if char.level < skill.min_level:
        return False, f"레벨 {skill.min_level} 이상이어야 합니다."
    if char.class_id not in skill.class_ids:
        return False, "해당 직업은 이 기술을 사용할 수 없습니다."
    # SP cost check (SP = move points)
    current_sp = getattr(char, "move", 0)
    if current_sp < skill.sp_cost:
        return False, "내공이 부족합니다."
    return True, ""


async def use_skill(
    char: Any, skill_id: int, target: Any,
    send_to_char: Any = None,
) -> int:
    """Use a skill on target. Returns damage dealt (or healing amount)."""
    skill = SKILLS.get(skill_id)
    if not skill:
        return 0

    # Deduct SP cost
    char.move = max(0, getattr(char, "move", 0) - skill.sp_cost)

    damage = 0

    if skill.category == "attack":
        damage = _calc_attack_skill_damage(char, skill)
        target.hp -= damage
        if send_to_char and char.session:
            await send_to_char(char,
                f"{{bright_red}}{skill.korean_name}! {target.name}에게 {damage} 데미지!{{reset}}")
        if send_to_char and target.session:
            await send_to_char(target,
                f"\r\n{{red}}{char.name}의 {skill.korean_name}에 {damage} 데미지를 받았습니다!{{reset}}")

    elif skill.category == "magic":
        damage = _calc_magic_skill_damage(char, skill)
        target.hp -= damage
        if send_to_char and char.session:
            await send_to_char(char,
                f"{{bright_magenta}}{skill.korean_name}! {target.name}에게 {damage} 데미지!{{reset}}")
        if send_to_char and target.session:
            await send_to_char(target,
                f"\r\n{{magenta}}{char.name}의 {skill.korean_name}에 {damage} 데미지를 받았습니다!{{reset}}")

    elif skill.category == "recovery":
        heal = _calc_heal_amount(char, skill)
        target.hp = min(target.max_hp, target.hp + heal)
        damage = -heal  # negative = healing
        if send_to_char and char.session:
            await send_to_char(char,
                f"{{bright_green}}{skill.korean_name}! {target.name}을(를) {heal}만큼 치료했습니다.{{reset}}")

    elif skill.category == "defense":
        if send_to_char and char.session:
            await send_to_char(char,
                f"{{cyan}}{skill.korean_name}! 방어 태세를 갖춥니다.{{reset}}")

    elif skill.category == "utility":
        if send_to_char and char.session:
            await send_to_char(char,
                f"{{white}}{skill.korean_name}을(를) 사용합니다.{{reset}}")

    return damage


def _calc_attack_skill_damage(char: Any, skill: WoongiSkill) -> int:
    """Calculate attack skill damage."""
    stats = _import("stats")
    wstats = importlib.import_module(f"{_PKG}.combat.sigma").get_wuxia_stats(char)

    base = skill.sp_cost // 2 + random.randint(1, char.level)
    spirit_bonus = wstats["spirit"] // 3
    return max(1, base + spirit_bonus + char.damroll)


def _calc_magic_skill_damage(char: Any, skill: WoongiSkill) -> int:
    """Calculate magic skill damage."""
    wstats = importlib.import_module(f"{_PKG}.combat.sigma").get_wuxia_stats(char)

    base = skill.sp_cost + random.randint(1, char.level * 2)
    wisdom_bonus = wstats["wisdom"] // 2
    return max(1, base + wisdom_bonus)


def _calc_heal_amount(char: Any, skill: WoongiSkill) -> int:
    """Calculate healing amount."""
    wstats = importlib.import_module(f"{_PKG}.combat.sigma").get_wuxia_stats(char)

    base = skill.sp_cost + random.randint(1, char.level)
    wisdom_bonus = wstats["wisdom"] // 2
    return max(1, base + wisdom_bonus)
