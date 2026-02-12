-- spells.lua — 34 spell definitions + cast/practice commands + tick_affects hook

-- ── Spell IDs ─────────────────────────────────────────────────

local SPELL_NONE = 0
local SPELL_MAGIC_MISSILE = 1
local SPELL_BURNING_HANDS = 2
local SPELL_CHILL_TOUCH = 3
local SPELL_LIGHTNING_BOLT = 4
local SPELL_FIREBALL = 5
local SPELL_COLOR_SPRAY = 6
local SPELL_CURE_LIGHT = 7
local SPELL_CURE_CRITIC = 8
local SPELL_HEAL = 9
local SPELL_ARMOR = 10
local SPELL_BLESS = 11
local SPELL_STRENGTH = 12
local SPELL_INVISIBILITY = 13
local SPELL_SANCTUARY = 14
local SPELL_BLINDNESS = 15
local SPELL_CURSE = 16
local SPELL_POISON = 17
local SPELL_SLEEP = 18
local SPELL_DETECT_INVIS = 19
local SPELL_WORD_OF_RECALL = 20
local SPELL_EARTHQUAKE = 21
local SPELL_DISPEL_EVIL = 22
local SPELL_DISPEL_GOOD = 23
local SPELL_SUMMON = 24
local SPELL_LOCATE_OBJECT = 25
local SPELL_CHARM = 26
local SPELL_REMOVE_CURSE = 27
local SPELL_REMOVE_POISON = 28
local SPELL_GROUP_HEAL = 29
local SPELL_GROUP_ARMOR = 30
local SPELL_INFRAVISION = 31
local SPELL_WATERWALK = 32
local SPELL_TELEPORT = 33
local SPELL_ENCHANT_WEAPON = 34

-- ── Spell definitions ─────────────────────────────────────────

local SPELLS = {}

local function reg(id, name, kr_name, levels, mana, target_type)
    SPELLS[id] = {
        id=id, name=name, korean_name=kr_name,
        min_level=levels, mana_cost=mana, target_type=target_type,
    }
end

-- Attack spells
reg(1,  "magic missile",    "매직미사일",  {[0]=1,[1]=34,[2]=34,[3]=34},  15, "offensive")
reg(2,  "burning hands",    "불꽃손",      {[0]=5,[1]=34,[2]=34,[3]=34},  20, "offensive")
reg(3,  "chill touch",      "냉기의손길",  {[0]=3,[1]=34,[2]=34,[3]=34},  15, "offensive")
reg(4,  "lightning bolt",   "번개",        {[0]=9,[1]=34,[2]=34,[3]=34},  25, "offensive")
reg(5,  "fireball",         "화염구",      {[0]=15,[1]=34,[2]=34,[3]=34}, 40, "offensive")
reg(6,  "color spray",      "색광선",      {[0]=11,[1]=34,[2]=34,[3]=34}, 30, "offensive")
-- Healing
reg(7,  "cure light",       "가벼운치유",  {[0]=34,[1]=1,[2]=34,[3]=34},  10, "defensive")
reg(8,  "cure critic",      "심각한치유",  {[0]=34,[1]=9,[2]=34,[3]=34},  20, "defensive")
reg(9,  "heal",             "치유",        {[0]=34,[1]=16,[2]=34,[3]=34}, 50, "defensive")
-- Buffs
reg(10, "armor",            "갑옷",        {[0]=4,[1]=1,[2]=34,[3]=34},   10, "defensive")
reg(11, "bless",            "축복",        {[0]=34,[1]=5,[2]=34,[3]=34},  15, "defensive")
reg(12, "strength",         "힘",          {[0]=6,[1]=34,[2]=34,[3]=34},  20, "defensive")
reg(13, "invisibility",     "투명",        {[0]=4,[1]=34,[2]=34,[3]=34},  20, "self")
reg(14, "sanctuary",        "보호막",      {[0]=34,[1]=15,[2]=34,[3]=34}, 75, "defensive")
-- Debuff/utility
reg(15, "blindness",        "실명",        {[0]=9,[1]=6,[2]=34,[3]=34},   25, "offensive")
reg(16, "curse",            "저주",        {[0]=14,[1]=7,[2]=34,[3]=34},  40, "offensive")
reg(17, "poison",           "독",          {[0]=14,[1]=8,[2]=34,[3]=34},  25, "offensive")
reg(18, "sleep",            "수면",        {[0]=8,[1]=34,[2]=34,[3]=34},  30, "offensive")
reg(19, "detect invisibility","투명감지",  {[0]=2,[1]=6,[2]=34,[3]=34},   10, "self")
reg(20, "word of recall",   "귀환",        {[0]=34,[1]=12,[2]=34,[3]=34}, 20, "utility")
-- Extended
reg(21, "earthquake",       "지진",        {[0]=34,[1]=12,[2]=34,[3]=34}, 40, "offensive")
reg(22, "dispel evil",      "사악퇴치",    {[0]=34,[1]=14,[2]=34,[3]=34}, 40, "offensive")
reg(23, "dispel good",      "선량퇴치",    {[0]=34,[1]=14,[2]=34,[3]=34}, 40, "offensive")
reg(24, "summon",           "소환",        {[0]=34,[1]=10,[2]=34,[3]=34}, 50, "utility")
reg(25, "locate object",    "물건탐지",    {[0]=6,[1]=10,[2]=34,[3]=34},  25, "utility")
reg(26, "charm person",     "매혹",        {[0]=16,[1]=34,[2]=34,[3]=34}, 60, "offensive")
reg(27, "remove curse",     "저주해제",    {[0]=34,[1]=9,[2]=34,[3]=34},  20, "defensive")
reg(28, "remove poison",    "해독",        {[0]=34,[1]=6,[2]=34,[3]=34},  20, "defensive")
reg(29, "group heal",       "그룹치유",    {[0]=34,[1]=22,[2]=34,[3]=34}, 80, "defensive")
reg(30, "group armor",      "그룹갑옷",    {[0]=34,[1]=9,[2]=34,[3]=34},  30, "defensive")
reg(31, "infravision",      "적외선시야",  {[0]=3,[1]=7,[2]=34,[3]=34},   10, "self")
reg(32, "waterwalk",        "수면보행",    {[0]=34,[1]=4,[2]=34,[3]=34},  15, "self")
reg(33, "teleport",         "순간이동",    {[0]=9,[1]=34,[2]=34,[3]=34},  50, "utility")
reg(34, "enchant weapon",   "무기강화",    {[0]=16,[1]=34,[2]=34,[3]=34}, 100,"utility")

-- ── Spell helpers ─────────────────────────────────────────────

local DAMAGE_SPELL_IDS = {
    [1]=true, [2]=true, [3]=true, [4]=true, [5]=true, [6]=true,
    [21]=true, [22]=true, [23]=true,
}

local function find_spell(name)
    local name_lower = name:lower()
    -- Exact match
    for _, sp in pairs(SPELLS) do
        if sp.name == name_lower or sp.korean_name == name then
            return sp
        end
    end
    -- Prefix match
    for _, sp in pairs(SPELLS) do
        if sp.name:sub(1, #name_lower) == name_lower or
           sp.korean_name:sub(1, #name) == name then
            return sp
        end
    end
    return nil
end

local function can_cast(char, spell)
    local min_lv = spell.min_level[char.class_id] or 34
    if char.level < min_lv then
        return false, "그 주문은 레벨 " .. min_lv .. " 이상이어야 시전할 수 있습니다."
    end
    if char.mana < spell.mana_cost then
        return false, "마나가 부족합니다."
    end
    return true, ""
end

local function spell_damage(ctx, spell_id, level)
    level = math.max(1, level)
    if spell_id == 1 then      return ctx:random(1, 8) + math.min(level, 5)
    elseif spell_id == 2 then  return ctx:random(3, 8) + level
    elseif spell_id == 3 then  return ctx:random(1, 6) + level
    elseif spell_id == 4 then  return ctx:random(7, 7 * math.min(level, 9))
    elseif spell_id == 5 then  return ctx:random(level, level * 8)
    elseif spell_id == 6 then  return ctx:random(level, level * 6)
    elseif spell_id == 21 then return ctx:random(level, level * 4)
    elseif spell_id == 22 then return ctx:random(level, level * 6)
    elseif spell_id == 23 then return ctx:random(level, level * 6)
    end
    return ctx:random(1, 8)
end

local function spell_heal_amount(ctx, spell_id, level)
    level = math.max(1, level)
    if spell_id == 7 then
        return ctx:random(1, 8) + math.min(math.floor(level / 4), 5)
    elseif spell_id == 8 then
        return ctx:random(3, 8) + math.min(math.floor(level / 2), 10)
    elseif spell_id == 9 then
        return 100 + ctx:random(0, level)
    end
    return ctx:random(1, 8)
end

-- Cast spell effect on target; returns damage dealt
local function cast_spell_effect(ctx, caster, spell, target)
    local spell_id = spell.id
    local damage = 0

    -- Offensive spells
    if spell.target_type == "offensive" then
        if DAMAGE_SPELL_IDS[spell_id] then
            damage = spell_damage(ctx, spell_id, caster.level)
            -- Sanctuary halves damage
            if ctx:has_spell_affect(target, SPELL_SANCTUARY) then
                damage = math.floor(damage / 2)
            end
            target.hp = target.hp - damage
            ctx:send("{bright_magenta}" .. spell.korean_name .. "이(가) " ..
                     target.name .. "에게 " .. damage .. "의 피해를 입힙니다!{reset}")
            if target.session then
                ctx:send_to(target,
                    "{bright_magenta}" .. caster.name .. "의 " .. spell.korean_name ..
                    "이(가) 당신에게 " .. damage .. "의 피해를 입힙니다!{reset}")
            end
        elseif spell_id == SPELL_BLINDNESS then
            ctx:apply_spell_buff(target, SPELL_BLINDNESS,
                2 + math.floor(caster.level / 4))
            ctx:send(target.name .. "의 눈이 먼 것 같습니다!")
        elseif spell_id == SPELL_CURSE then
            ctx:apply_spell_buff(target, SPELL_CURSE,
                3 + math.floor(caster.level / 5),
                {hitroll=-2, damroll=-2})
            ctx:send(target.name .. "에게 저주가 내렸습니다!")
        elseif spell_id == SPELL_POISON then
            ctx:apply_spell_buff(target, SPELL_POISON,
                3 + math.floor(caster.level / 5),
                {damage_per_tick=2})
            ctx:send(target.name .. "이(가) 중독되었습니다!")
        elseif spell_id == SPELL_SLEEP then
            if target.level <= caster.level + 3 then
                target.position = 6  -- POS_SLEEPING
                target.fighting = nil
                ctx:send(target.name .. "이(가) 잠에 빠집니다...")
            end
        elseif spell_id == SPELL_CHARM then
            if target.level <= caster.level then
                ctx:apply_spell_buff(target, SPELL_CHARM,
                    3 + math.floor(caster.level / 5))
                ctx:send(target.name .. "이(가) 당신에게 매혹되었습니다!")
            end
        end

    -- Defensive/healing
    elseif spell.target_type == "defensive" then
        if spell_id == SPELL_CURE_LIGHT or spell_id == SPELL_CURE_CRITIC or
           spell_id == SPELL_HEAL then
            local heal = spell_heal_amount(ctx, spell_id, caster.level)
            target.hp = math.min(target.max_hp, target.hp + heal)
            ctx:send_to(target, "{bright_green}" .. heal .. "만큼 회복됩니다!{reset}")
        elseif spell_id == SPELL_ARMOR or spell_id == SPELL_GROUP_ARMOR then
            ctx:apply_spell_buff(target, SPELL_ARMOR, 24, {ac_bonus=-20})
            ctx:send_to(target, "마법 갑옷이 감싸줍니다.")
        elseif spell_id == SPELL_BLESS then
            ctx:apply_spell_buff(target, SPELL_BLESS,
                6 + math.floor(caster.level / 2),
                {hitroll=2, damroll=2})
            ctx:send_to(target, "축복받은 느낌이 듭니다.")
        elseif spell_id == SPELL_STRENGTH then
            ctx:apply_spell_buff(target, SPELL_STRENGTH,
                6 + math.floor(caster.level / 3),
                {str_bonus=2})
            ctx:send_to(target, "힘이 솟구칩니다!")
        elseif spell_id == SPELL_SANCTUARY then
            ctx:apply_spell_buff(target, SPELL_SANCTUARY, 4,
                {damage_reduction=0.5})
            ctx:send_to(target, "{bright_white}하얀 빛이 몸을 감쌉니다!{reset}")
        elseif spell_id == SPELL_REMOVE_CURSE then
            ctx:remove_spell_affect(target, SPELL_CURSE)
            ctx:send_to(target, "저주가 풀렸습니다.")
        elseif spell_id == SPELL_REMOVE_POISON then
            ctx:remove_spell_affect(target, SPELL_POISON)
            ctx:send_to(target, "독이 해독되었습니다.")
        elseif spell_id == SPELL_GROUP_HEAL then
            local heal = spell_heal_amount(ctx, SPELL_HEAL, caster.level)
            target.hp = math.min(target.max_hp, target.hp + heal)
            ctx:send_to(target, "{bright_green}" .. heal .. "만큼 회복됩니다!{reset}")
        end

    -- Self-target
    elseif spell.target_type == "self" then
        if spell_id == SPELL_INVISIBILITY then
            ctx:apply_spell_buff(target, SPELL_INVISIBILITY,
                12 + math.floor(caster.level / 4))
            ctx:send("몸이 투명해집니다!")
        elseif spell_id == SPELL_DETECT_INVIS then
            ctx:apply_spell_buff(target, SPELL_DETECT_INVIS,
                12 + math.floor(caster.level / 4))
            ctx:send("눈이 밝아집니다.")
        elseif spell_id == SPELL_INFRAVISION then
            ctx:apply_spell_buff(target, SPELL_INFRAVISION,
                12 + math.floor(caster.level / 4))
            ctx:send("어둠 속에서도 볼 수 있습니다.")
        elseif spell_id == SPELL_WATERWALK then
            ctx:apply_spell_buff(target, SPELL_WATERWALK, 24)
            ctx:send("물 위를 걸을 수 있습니다.")
        end

    -- Utility
    elseif spell.target_type == "utility" then
        -- Word of Recall handled before this function
        -- Others: just consume mana (no additional effect)
    end

    return damage
end

-- ── cast command ──────────────────────────────────────────────

register_command("cast", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    -- Must be standing (8) or fighting (7) to cast
    if ch.position < 8 and ch.position ~= 7 then
        ctx:send("일어서야 합니다.")
        return
    end

    if not args or args == "" then
        ctx:send("어떤 주문을 시전하시겠습니까?")
        return
    end

    -- Parse: cast <spell> [target]
    local spell_name, target_name
    local space = args:find(" ")
    if space then
        spell_name = args:sub(1, space - 1)
        target_name = args:sub(space + 1):match("^%s*(.-)%s*$")
    else
        spell_name = args
        target_name = ""
    end

    local spell = find_spell(spell_name)
    if not spell then
        ctx:send("그런 주문은 모릅니다.")
        return
    end

    local ok, msg = can_cast(ch, spell)
    if not ok then
        ctx:send(msg)
        return
    end

    -- Find target
    local target = nil
    if spell.target_type == "self" or spell.target_type == "utility" then
        target = ch
    elseif spell.target_type == "defensive" and target_name == "" then
        target = ch
    elseif target_name ~= "" then
        target = ctx:find_char(target_name)
        if not target and spell.target_type == "defensive" then
            target = ch
        end
    elseif spell.target_type == "offensive" then
        target = ch.fighting
    end

    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end

    -- Word of Recall special
    if spell.id == SPELL_WORD_OF_RECALL then
        ch.mana = ch.mana - spell.mana_cost
        local start_room = ctx:get_start_room()
        ctx:stop_combat(ch)
        ctx:move_to(start_room)
        ctx:send("{bright_white}몸이 가벼워지며 순간이동합니다!{reset}")
        ctx:defer_look()
        return
    end

    -- Deduct mana
    ch.mana = ch.mana - spell.mana_cost

    -- Start combat for offensive spells
    if spell.target_type == "offensive" and target ~= ch then
        ctx:start_combat(target)
    end

    -- Cast spell
    local damage = cast_spell_effect(ctx, ch, spell, target)

    -- Check death
    if target.hp <= 0 and target ~= ch then
        ctx:stop_combat(ch)
        ctx:defer_death(target, ch)
    end
end, "시전")

-- ── practice command ──────────────────────────────────────────

register_command("practice", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local lines = {"{bright_cyan}-- 시전 가능한 주문 --{reset}"}

    -- Sort spells by id
    local sorted = {}
    for _, sp in pairs(SPELLS) do
        sorted[#sorted + 1] = sp
    end
    table.sort(sorted, function(a, b) return a.id < b.id end)

    for _, spell in ipairs(sorted) do
        local min_lv = spell.min_level[ch.class_id] or 34
        if min_lv <= ch.level then
            local prof = ctx:get_skill_proficiency(ch, spell.id)
            -- Left-pad Korean name and English name for alignment
            lines[#lines + 1] = "  " .. spell.korean_name ..
                string.rep(" ", math.max(1, 12 - #spell.korean_name)) ..
                " (" .. spell.name ..
                string.rep(" ", math.max(1, 20 - #spell.name)) ..
                ") 숙련도: " .. prof .. "%"
        end
    end

    ctx:send(table.concat(lines, "\r\n"))
end, "학습")

-- tick_affects stays in Python (core/engine.py → games/tbamud/combat/spells.py)
-- because modifying Python list (char.affects) from Lua has interop issues.
