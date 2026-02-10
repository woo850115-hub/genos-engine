"""Spell system — 34 spells (20 core + 14 extended)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.world import MobInstance

# ── Spell definitions ────────────────────────────────────────────

SPELL_NONE = 0
# Attack spells
SPELL_MAGIC_MISSILE = 1
SPELL_BURNING_HANDS = 2
SPELL_CHILL_TOUCH = 3
SPELL_LIGHTNING_BOLT = 4
SPELL_FIREBALL = 5
SPELL_COLOR_SPRAY = 6
# Healing spells
SPELL_CURE_LIGHT = 7
SPELL_CURE_CRITIC = 8
SPELL_HEAL = 9
# Buff spells
SPELL_ARMOR = 10
SPELL_BLESS = 11
SPELL_STRENGTH = 12
SPELL_INVISIBILITY = 13
SPELL_SANCTUARY = 14
# Debuff/utility
SPELL_BLINDNESS = 15
SPELL_CURSE = 16
SPELL_POISON = 17
SPELL_SLEEP = 18
SPELL_DETECT_INVIS = 19
SPELL_WORD_OF_RECALL = 20
# Sprint 4: Extended spells
SPELL_EARTHQUAKE = 21
SPELL_DISPEL_EVIL = 22
SPELL_DISPEL_GOOD = 23
SPELL_SUMMON = 24
SPELL_LOCATE_OBJECT = 25
SPELL_CHARM = 26
SPELL_REMOVE_CURSE = 27
SPELL_REMOVE_POISON = 28
SPELL_GROUP_HEAL = 29
SPELL_GROUP_ARMOR = 30
SPELL_INFRAVISION = 31
SPELL_WATERWALK = 32
SPELL_TELEPORT = 33
SPELL_ENCHANT_WEAPON = 34


@dataclass
class SpellDef:
    id: int
    name: str
    korean_name: str
    min_level: dict[int, int]  # class_id → min_level
    mana_cost: int
    target_type: str  # "offensive", "defensive", "self", "utility"
    max_level: int = 34


# All spell definitions
SPELLS: dict[int, SpellDef] = {}


def _reg(spell_id, name, kr_name, levels, mana, target):
    SPELLS[spell_id] = SpellDef(
        id=spell_id, name=name, korean_name=kr_name,
        min_level=levels, mana_cost=mana, target_type=target,
    )


# Attack spells
_reg(SPELL_MAGIC_MISSILE, "magic missile", "매직미사일", {0: 1, 1: 34, 2: 34, 3: 34}, 15, "offensive")
_reg(SPELL_BURNING_HANDS, "burning hands", "불꽃손", {0: 5, 1: 34, 2: 34, 3: 34}, 20, "offensive")
_reg(SPELL_CHILL_TOUCH, "chill touch", "냉기의손길", {0: 3, 1: 34, 2: 34, 3: 34}, 15, "offensive")
_reg(SPELL_LIGHTNING_BOLT, "lightning bolt", "번개", {0: 9, 1: 34, 2: 34, 3: 34}, 25, "offensive")
_reg(SPELL_FIREBALL, "fireball", "화염구", {0: 15, 1: 34, 2: 34, 3: 34}, 40, "offensive")
_reg(SPELL_COLOR_SPRAY, "color spray", "색광선", {0: 11, 1: 34, 2: 34, 3: 34}, 30, "offensive")
# Healing
_reg(SPELL_CURE_LIGHT, "cure light", "가벼운치유", {0: 34, 1: 1, 2: 34, 3: 34}, 10, "defensive")
_reg(SPELL_CURE_CRITIC, "cure critic", "심각한치유", {0: 34, 1: 9, 2: 34, 3: 34}, 20, "defensive")
_reg(SPELL_HEAL, "heal", "치유", {0: 34, 1: 16, 2: 34, 3: 34}, 50, "defensive")
# Buffs
_reg(SPELL_ARMOR, "armor", "갑옷", {0: 4, 1: 1, 2: 34, 3: 34}, 10, "defensive")
_reg(SPELL_BLESS, "bless", "축복", {0: 34, 1: 5, 2: 34, 3: 34}, 15, "defensive")
_reg(SPELL_STRENGTH, "strength", "힘", {0: 6, 1: 34, 2: 34, 3: 34}, 20, "defensive")
_reg(SPELL_INVISIBILITY, "invisibility", "투명", {0: 4, 1: 34, 2: 34, 3: 34}, 20, "self")
_reg(SPELL_SANCTUARY, "sanctuary", "보호막", {0: 34, 1: 15, 2: 34, 3: 34}, 75, "defensive")
# Debuff / utility
_reg(SPELL_BLINDNESS, "blindness", "실명", {0: 9, 1: 6, 2: 34, 3: 34}, 25, "offensive")
_reg(SPELL_CURSE, "curse", "저주", {0: 14, 1: 7, 2: 34, 3: 34}, 40, "offensive")
_reg(SPELL_POISON, "poison", "독", {0: 14, 1: 8, 2: 34, 3: 34}, 25, "offensive")
_reg(SPELL_SLEEP, "sleep", "수면", {0: 8, 1: 34, 2: 34, 3: 34}, 30, "offensive")
_reg(SPELL_DETECT_INVIS, "detect invisibility", "투명감지", {0: 2, 1: 6, 2: 34, 3: 34}, 10, "self")
_reg(SPELL_WORD_OF_RECALL, "word of recall", "귀환", {0: 34, 1: 12, 2: 34, 3: 34}, 20, "utility")
# Extended spells (Sprint 4)
_reg(SPELL_EARTHQUAKE, "earthquake", "지진", {0: 34, 1: 12, 2: 34, 3: 34}, 40, "offensive")
_reg(SPELL_DISPEL_EVIL, "dispel evil", "사악퇴치", {0: 34, 1: 14, 2: 34, 3: 34}, 40, "offensive")
_reg(SPELL_DISPEL_GOOD, "dispel good", "선량퇴치", {0: 34, 1: 14, 2: 34, 3: 34}, 40, "offensive")
_reg(SPELL_SUMMON, "summon", "소환", {0: 34, 1: 10, 2: 34, 3: 34}, 50, "utility")
_reg(SPELL_LOCATE_OBJECT, "locate object", "물건탐지", {0: 6, 1: 10, 2: 34, 3: 34}, 25, "utility")
_reg(SPELL_CHARM, "charm person", "매혹", {0: 16, 1: 34, 2: 34, 3: 34}, 60, "offensive")
_reg(SPELL_REMOVE_CURSE, "remove curse", "저주해제", {0: 34, 1: 9, 2: 34, 3: 34}, 20, "defensive")
_reg(SPELL_REMOVE_POISON, "remove poison", "해독", {0: 34, 1: 6, 2: 34, 3: 34}, 20, "defensive")
_reg(SPELL_GROUP_HEAL, "group heal", "그룹치유", {0: 34, 1: 22, 2: 34, 3: 34}, 80, "defensive")
_reg(SPELL_GROUP_ARMOR, "group armor", "그룹갑옷", {0: 34, 1: 9, 2: 34, 3: 34}, 30, "defensive")
_reg(SPELL_INFRAVISION, "infravision", "적외선시야", {0: 3, 1: 7, 2: 34, 3: 34}, 10, "self")
_reg(SPELL_WATERWALK, "waterwalk", "수면보행", {0: 34, 1: 4, 2: 34, 3: 34}, 15, "self")
_reg(SPELL_TELEPORT, "teleport", "순간이동", {0: 9, 1: 34, 2: 34, 3: 34}, 50, "utility")
_reg(SPELL_ENCHANT_WEAPON, "enchant weapon", "무기강화", {0: 16, 1: 34, 2: 34, 3: 34}, 100, "utility")


def spell_damage(spell_id: int, caster_level: int) -> int:
    """Calculate spell damage based on spell and level."""
    level = max(1, caster_level)
    if spell_id == SPELL_MAGIC_MISSILE:
        return random.randint(1, 8) + min(level, 5)
    elif spell_id == SPELL_BURNING_HANDS:
        return random.randint(3, 8) + level
    elif spell_id == SPELL_CHILL_TOUCH:
        return random.randint(1, 6) + level
    elif spell_id == SPELL_LIGHTNING_BOLT:
        return random.randint(7, 7 * min(level, 9))
    elif spell_id == SPELL_FIREBALL:
        return random.randint(level, level * 8)
    elif spell_id == SPELL_COLOR_SPRAY:
        return random.randint(level, level * 6)
    elif spell_id == SPELL_EARTHQUAKE:
        return random.randint(level, level * 4)
    elif spell_id == SPELL_DISPEL_EVIL:
        return random.randint(level, level * 6)
    elif spell_id == SPELL_DISPEL_GOOD:
        return random.randint(level, level * 6)
    return random.randint(1, 8)


def spell_heal_amount(spell_id: int, caster_level: int) -> int:
    """Calculate healing amount."""
    level = max(1, caster_level)
    if spell_id == SPELL_CURE_LIGHT:
        return random.randint(1, 8) + min(level // 4, 5)
    elif spell_id == SPELL_CURE_CRITIC:
        return random.randint(3, 8) + min(level // 2, 10)
    elif spell_id == SPELL_HEAL:
        return 100 + random.randint(0, level)
    return random.randint(1, 8)


def can_cast(caster: MobInstance, spell_id: int) -> tuple[bool, str]:
    """Check if caster can cast this spell."""
    spell = SPELLS.get(spell_id)
    if not spell:
        return False, "알 수 없는 주문입니다."

    min_lv = spell.min_level.get(caster.class_id, 34)
    if caster.level < min_lv:
        return False, f"그 주문은 레벨 {min_lv} 이상이어야 시전할 수 있습니다."

    if caster.mana < spell.mana_cost:
        return False, "마나가 부족합니다."

    return True, ""


def find_spell(name: str) -> SpellDef | None:
    """Find a spell by name or Korean name (prefix match)."""
    name_lower = name.lower()
    # Exact match first
    for spell in SPELLS.values():
        if spell.name == name_lower or spell.korean_name == name:
            return spell
    # Prefix match
    for spell in SPELLS.values():
        if spell.name.startswith(name_lower) or spell.korean_name.startswith(name):
            return spell
    return None


def apply_buff(target: MobInstance, spell_id: int, duration: int, **kwargs: Any) -> None:
    """Apply a buff/debuff affect to target."""
    # Remove existing same-type affect
    target.affects = [a for a in target.affects if a.get("spell_id") != spell_id]
    affect = {"spell_id": spell_id, "duration": duration, **kwargs}
    target.affects.append(affect)


def has_affect(char: MobInstance, spell_id: int) -> bool:
    """Check if character has an active affect from a spell."""
    return any(a.get("spell_id") == spell_id for a in char.affects)


async def cast_spell(caster: MobInstance, spell_id: int, target: MobInstance,
                     send_to_char=None) -> int:
    """Cast a spell. Returns damage dealt (0 for non-damage spells)."""
    spell = SPELLS.get(spell_id)
    if not spell:
        return 0

    caster.mana -= spell.mana_cost
    damage = 0

    # Offensive spells
    if spell.target_type == "offensive":
        if spell_id in (SPELL_MAGIC_MISSILE, SPELL_BURNING_HANDS, SPELL_CHILL_TOUCH,
                        SPELL_LIGHTNING_BOLT, SPELL_FIREBALL, SPELL_COLOR_SPRAY,
                        SPELL_EARTHQUAKE, SPELL_DISPEL_EVIL, SPELL_DISPEL_GOOD):
            damage = spell_damage(spell_id, caster.level)
            # Sanctuary halves damage
            if has_affect(target, SPELL_SANCTUARY):
                damage //= 2
            target.hp -= damage
            if send_to_char:
                await send_to_char(
                    caster,
                    f"{{bright_magenta}}{spell.korean_name}이(가) {target.name}에게 "
                    f"{damage}의 피해를 입힙니다!{{reset}}"
                )
                if target.session:
                    await send_to_char(
                        target,
                        f"{{bright_magenta}}{caster.name}의 {spell.korean_name}이(가) "
                        f"당신에게 {damage}의 피해를 입힙니다!{{reset}}"
                    )
        elif spell_id == SPELL_BLINDNESS:
            apply_buff(target, SPELL_BLINDNESS, 2 + caster.level // 4)
            if send_to_char:
                await send_to_char(caster, f"{target.name}의 눈이 먼 것 같습니다!")
        elif spell_id == SPELL_CURSE:
            apply_buff(target, SPELL_CURSE, 3 + caster.level // 5, hitroll=-2, damroll=-2)
            if send_to_char:
                await send_to_char(caster, f"{target.name}에게 저주가 내렸습니다!")
        elif spell_id == SPELL_POISON:
            apply_buff(target, SPELL_POISON, 3 + caster.level // 5, damage_per_tick=2)
            if send_to_char:
                await send_to_char(caster, f"{target.name}이(가) 중독되었습니다!")
        elif spell_id == SPELL_SLEEP:
            if target.level <= caster.level + 3:
                target.position = 6  # POS_SLEEPING
                target.fighting = None
                if send_to_char:
                    await send_to_char(caster, f"{target.name}이(가) 잠에 빠집니다...")

        elif spell_id == SPELL_CHARM:
            if target.level <= caster.level:
                apply_buff(target, SPELL_CHARM, 3 + caster.level // 5)
                if send_to_char:
                    await send_to_char(caster, f"{target.name}이(가) 당신에게 매혹되었습니다!")

    # Defensive/healing spells
    elif spell.target_type == "defensive":
        if spell_id in (SPELL_CURE_LIGHT, SPELL_CURE_CRITIC, SPELL_HEAL):
            heal = spell_heal_amount(spell_id, caster.level)
            target.hp = min(target.max_hp, target.hp + heal)
            if send_to_char:
                await send_to_char(
                    caster if caster is target else target,
                    f"{{bright_green}}{heal}만큼 회복됩니다!{{reset}}"
                )
        elif spell_id == SPELL_ARMOR:
            apply_buff(target, SPELL_ARMOR, 24, ac_bonus=-20)
            if send_to_char:
                await send_to_char(target, "마법 갑옷이 감싸줍니다.")
        elif spell_id == SPELL_BLESS:
            apply_buff(target, SPELL_BLESS, 6 + caster.level // 2, hitroll=2, damroll=2)
            if send_to_char:
                await send_to_char(target, "축복받은 느낌이 듭니다.")
        elif spell_id == SPELL_STRENGTH:
            apply_buff(target, SPELL_STRENGTH, 6 + caster.level // 3, str_bonus=2)
            if send_to_char:
                await send_to_char(target, "힘이 솟구칩니다!")
        elif spell_id == SPELL_SANCTUARY:
            apply_buff(target, SPELL_SANCTUARY, 4, damage_reduction=0.5)
            if send_to_char:
                await send_to_char(target, "{bright_white}하얀 빛이 몸을 감쌉니다!{reset}")
        elif spell_id == SPELL_REMOVE_CURSE:
            target.affects = [a for a in target.affects if a.get("spell_id") != SPELL_CURSE]
            if send_to_char:
                await send_to_char(target, "저주가 풀렸습니다.")
        elif spell_id == SPELL_REMOVE_POISON:
            target.affects = [a for a in target.affects if a.get("spell_id") != SPELL_POISON]
            if send_to_char:
                await send_to_char(target, "독이 해독되었습니다.")
        elif spell_id == SPELL_GROUP_ARMOR:
            apply_buff(target, SPELL_ARMOR, 24, ac_bonus=-20)
            if send_to_char:
                await send_to_char(target, "마법 갑옷이 감싸줍니다.")
        elif spell_id == SPELL_GROUP_HEAL:
            heal = spell_heal_amount(SPELL_HEAL, caster.level)
            target.hp = min(target.max_hp, target.hp + heal)
            if send_to_char:
                await send_to_char(target, f"{{bright_green}}{heal}만큼 회복됩니다!{{reset}}")

    # Self-target
    elif spell.target_type == "self":
        if spell_id == SPELL_INVISIBILITY:
            apply_buff(target, SPELL_INVISIBILITY, 12 + caster.level // 4)
            if send_to_char:
                await send_to_char(caster, "몸이 투명해집니다!")
        elif spell_id == SPELL_DETECT_INVIS:
            apply_buff(target, SPELL_DETECT_INVIS, 12 + caster.level // 4)
            if send_to_char:
                await send_to_char(caster, "눈이 밝아집니다.")
        elif spell_id == SPELL_INFRAVISION:
            apply_buff(target, SPELL_INFRAVISION, 12 + caster.level // 4)
            if send_to_char:
                await send_to_char(caster, "어둠 속에서도 볼 수 있습니다.")
        elif spell_id == SPELL_WATERWALK:
            apply_buff(target, SPELL_WATERWALK, 24)
            if send_to_char:
                await send_to_char(caster, "물 위를 걸을 수 있습니다.")

    # Utility
    elif spell.target_type == "utility":
        if spell_id == SPELL_WORD_OF_RECALL:
            # Teleport handled by caller
            pass

    return damage


def tick_affects(char: MobInstance) -> list[str]:
    """Tick down affect durations. Returns list of expiry messages."""
    messages = []
    remaining = []
    for affect in char.affects:
        affect["duration"] = affect.get("duration", 0) - 1
        if affect["duration"] <= 0:
            spell = SPELLS.get(affect.get("spell_id", 0))
            if spell:
                messages.append(f"{spell.korean_name} 효과가 사라졌습니다.")
            # Apply poison damage tick
        else:
            # Poison damage tick
            if affect.get("spell_id") == SPELL_POISON and affect.get("damage_per_tick"):
                char.hp -= affect["damage_per_tick"]
                messages.append(f"{{green}}독이 퍼져 {affect['damage_per_tick']}의 피해를 입습니다!{{reset}}")
            remaining.append(affect)
    char.affects = remaining
    return messages
