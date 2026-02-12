-- spells.lua — Simoon spell definitions + cast/practice commands
-- 7 classes: 0=MU, 1=CL, 2=TH, 3=WA, 4=DK, 5=BE, 6=SU

-- ── Spell IDs (from data/simoon/lua/skills.lua) ─────────────

local SPELL_ARMOR        = 1
local SPELL_BLESS        = 3
local SPELL_BLINDNESS    = 4
local SPELL_BURNING      = 5
local SPELL_CALL_LIGHT   = 6
local SPELL_CHARM        = 7
local SPELL_CHILL_TOUCH  = 8
local SPELL_CURE_BLIND   = 14
local SPELL_CURE_CRITIC  = 15
local SPELL_CURE_LIGHT   = 16
local SPELL_CURSE        = 17
local SPELL_DETECT_INVIS = 19
local SPELL_DETECT_MAGIC = 20
local SPELL_DISP_EVIL    = 22
local SPELL_EARTHQUAKE   = 23
local SPELL_ENCHANT      = 24
local SPELL_FIREBALL     = 26
local SPELL_HEAL         = 28
local SPELL_INVIS        = 29
local SPELL_LIGHTNING    = 30
local SPELL_MAGIC_MISSILE= 32
local SPELL_POISON       = 33
local SPELL_REMOVE_CURSE = 36
local SPELL_REMOVE_POISON= 37
local SPELL_SANCTUARY    = 38
local SPELL_SLEEP        = 41
local SPELL_STRENGTH     = 42
local SPELL_SUMMON       = 43
local SPELL_WORD_RECALL  = 47
local SPELL_GROUP_HEAL   = 52
local SPELL_GROUP_ARMOR  = 53
local SPELL_FLY          = 73
local SPELL_INFRAVISION  = 27
local SPELL_WATERWALK    = 45
local SPELL_TELEPORT     = 46
-- Simoon-unique summons
local SPELL_PENLIS       = 55
local SPELL_CELEB        = 56
local SPELL_MAHA         = 57

-- ── Spell definitions ───────────────────────────────────────

local SPELLS = {}

local function reg(id, name, kr_name, levels, mana, target_type)
    SPELLS[id] = {
        id=id, name=name, korean_name=kr_name,
        min_level=levels, mana_cost=mana, target_type=target_type,
    }
end

-- 7-class levels: {[0]=MU,[1]=CL,[2]=TH,[3]=WA,[4]=DK,[5]=BE,[6]=SU}
local X = 999  -- not available

-- Offensive spells
reg(SPELL_MAGIC_MISSILE, "magic missile",  "번개화살", {[0]=1,[1]=36,[2]=X,[3]=X,[4]=1,[5]=X,[6]=1},    25, "offensive")
reg(SPELL_BURNING,       "burning hands",  "불꽃",     {[0]=15,[1]=X,[2]=X,[3]=X,[4]=10,[5]=X,[6]=X},    30, "offensive")
reg(SPELL_CHILL_TOUCH,   "chill touch",    "냉기접촉", {[0]=8,[1]=X,[2]=X,[3]=X,[4]=5,[5]=X,[6]=X},      30, "offensive")
reg(SPELL_LIGHTNING,     "lightning bolt",  "라이트닝", {[0]=20,[1]=X,[2]=X,[3]=X,[4]=15,[5]=X,[6]=20},   40, "offensive")
reg(SPELL_FIREBALL,      "fireball",       "화이어볼", {[0]=300,[1]=X,[2]=X,[3]=X,[4]=25,[5]=X,[6]=X},   10000, "offensive")
reg(SPELL_CALL_LIGHT,    "call lightning",  "콜라이트", {[0]=X,[1]=100,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},    40, "offensive")
reg(SPELL_EARTHQUAKE,    "earthquake",      "지진",     {[0]=X,[1]=28,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     40, "offensive")
reg(SPELL_DISP_EVIL,     "dispel evil",    "사악퇴치", {[0]=X,[1]=41,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     40, "offensive")
-- Simoon-unique offensive (high level summons)
reg(SPELL_PENLIS,        "penlis",         "펜리스",   {[0]=40,[1]=X,[2]=X,[3]=X,[4]=30,[5]=X,[6]=35},   50, "offensive")
reg(SPELL_CELEB,         "celeb",          "켈베로스", {[0]=80,[1]=X,[2]=X,[3]=X,[4]=60,[5]=X,[6]=70},   100, "offensive")
reg(SPELL_MAHA,          "maha",           "마하킬라", {[0]=120,[1]=X,[2]=X,[3]=X,[4]=100,[5]=X,[6]=110},100, "offensive")

-- Healing
reg(SPELL_CURE_LIGHT,    "cure light",     "상처치료", {[0]=60,[1]=1,[2]=80,[3]=100,[4]=X,[5]=X,[6]=X},  30, "defensive")
reg(SPELL_CURE_CRITIC,   "cure critic",    "치료",     {[0]=X,[1]=50,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     30, "defensive")
reg(SPELL_HEAL,          "heal",           "힐링",     {[0]=X,[1]=100,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},    60, "defensive")
reg(SPELL_CURE_BLIND,    "cure blind",     "환명",     {[0]=X,[1]=14,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     30, "defensive")
reg(SPELL_GROUP_HEAL,    "group heal",     "그룹힐",   {[0]=X,[1]=140,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},    80, "defensive")

-- Buffs
reg(SPELL_ARMOR,         "armor",          "방호",     {[0]=13,[1]=1,[2]=X,[3]=X,[4]=10,[5]=X,[6]=15},   30, "defensive")
reg(SPELL_BLESS,         "bless",          "정화",     {[0]=X,[1]=16,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     35, "defensive")
reg(SPELL_STRENGTH,      "strength",       "힘강화",   {[0]=18,[1]=X,[2]=X,[3]=X,[4]=15,[5]=X,[6]=X},    30, "defensive")
reg(SPELL_SANCTUARY,     "sanctuary",      "보호막",   {[0]=X,[1]=70,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     75, "defensive")
reg(SPELL_GROUP_ARMOR,   "group armor",    "그룹방호", {[0]=X,[1]=30,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     30, "defensive")
reg(SPELL_REMOVE_CURSE,  "remove curse",   "저주해제", {[0]=X,[1]=45,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     20, "defensive")
reg(SPELL_REMOVE_POISON, "remove poison",  "해독",     {[0]=X,[1]=16,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     20, "defensive")

-- Self-target
reg(SPELL_INVIS,         "invisibility",   "투명",     {[0]=10,[1]=X,[2]=X,[3]=X,[4]=8,[5]=X,[6]=10},    20, "self")
reg(SPELL_DETECT_INVIS,  "detect invis",   "투명감지", {[0]=5,[1]=30,[2]=X,[3]=X,[4]=3,[5]=X,[6]=5},     20, "self")
reg(SPELL_DETECT_MAGIC,  "detect magic",   "마법감지", {[0]=6,[1]=X,[2]=X,[3]=X,[4]=4,[5]=X,[6]=X},      20, "self")
reg(SPELL_INFRAVISION,   "infravision",    "어둠감지", {[0]=8,[1]=30,[2]=X,[3]=X,[4]=5,[5]=X,[6]=X},     10, "self")
reg(SPELL_WATERWALK,     "waterwalk",      "수면보행", {[0]=X,[1]=20,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     15, "self")
reg(SPELL_FLY,           "fly",            "부상",     {[0]=25,[1]=X,[2]=X,[3]=X,[4]=20,[5]=X,[6]=25},   30, "self")

-- Debuffs
reg(SPELL_BLINDNESS,     "blindness",      "실명",     {[0]=26,[1]=33,[2]=X,[3]=X,[4]=20,[5]=X,[6]=X},   35, "offensive")
reg(SPELL_CURSE,         "curse",          "저주",     {[0]=37,[1]=X,[2]=X,[3]=X,[4]=25,[5]=X,[6]=X},    80, "offensive")
reg(SPELL_POISON,        "poison",         "독",       {[0]=X,[1]=X,[2]=X,[3]=X,[4]=20,[5]=X,[6]=X},     50, "offensive")
reg(SPELL_SLEEP,         "sleep",          "수면",     {[0]=20,[1]=X,[2]=X,[3]=X,[4]=15,[5]=X,[6]=X},    30, "offensive")
reg(SPELL_CHARM,         "charm",          "매혹",     {[0]=46,[1]=X,[2]=X,[3]=X,[4]=X,[5]=X,[6]=10},    75, "offensive")

-- Utility
reg(SPELL_WORD_RECALL,   "word of recall", "귀환",     {[0]=X,[1]=20,[2]=X,[3]=X,[4]=X,[5]=X,[6]=X},     20, "utility")
reg(SPELL_TELEPORT,      "teleport",       "순간이동", {[0]=30,[1]=X,[2]=X,[3]=X,[4]=25,[5]=X,[6]=X},    50, "utility")
reg(SPELL_SUMMON,        "summon",         "소환",     {[0]=X,[1]=40,[2]=X,[3]=X,[4]=X,[5]=X,[6]=6},     50, "utility")

-- ── Spell helpers ───────────────────────────────────────────

local DAMAGE_SPELL_IDS = {
    [SPELL_MAGIC_MISSILE]=true, [SPELL_BURNING]=true, [SPELL_CHILL_TOUCH]=true,
    [SPELL_LIGHTNING]=true, [SPELL_FIREBALL]=true, [SPELL_CALL_LIGHT]=true,
    [SPELL_EARTHQUAKE]=true, [SPELL_DISP_EVIL]=true,
    [SPELL_PENLIS]=true, [SPELL_CELEB]=true, [SPELL_MAHA]=true,
}

local function find_spell(name)
    local name_lower = name:lower()
    for _, sp in pairs(SPELLS) do
        if sp.name == name_lower or sp.korean_name == name then
            return sp
        end
    end
    for _, sp in pairs(SPELLS) do
        if sp.name:sub(1, #name_lower) == name_lower or
           sp.korean_name:sub(1, #name) == name then
            return sp
        end
    end
    return nil
end

local function can_cast(char, spell)
    local min_lv = spell.min_level[char.class_id] or 999
    if min_lv >= 999 or char.level < min_lv then
        return false, "그 주문은 레벨 " .. min_lv .. " 이상이어야 시전할 수 있습니다."
    end
    if char.mana < spell.mana_cost then
        return false, "마나가 부족합니다."
    end
    return true, ""
end

local function spell_damage(ctx, spell_id, level)
    level = math.max(1, level)
    if spell_id == SPELL_MAGIC_MISSILE then return ctx:random(1, 8) + math.min(level, 5)
    elseif spell_id == SPELL_BURNING then   return ctx:random(3, 8) + level
    elseif spell_id == SPELL_CHILL_TOUCH then return ctx:random(1, 6) + level
    elseif spell_id == SPELL_LIGHTNING then return ctx:random(7, 7 * math.min(level, 9))
    elseif spell_id == SPELL_FIREBALL then return ctx:random(level, level * 8)
    elseif spell_id == SPELL_CALL_LIGHT then return ctx:random(level, level * 6)
    elseif spell_id == SPELL_EARTHQUAKE then return ctx:random(level, level * 4)
    elseif spell_id == SPELL_DISP_EVIL then return ctx:random(level, level * 6)
    -- Simoon unique: higher damage tiers
    elseif spell_id == SPELL_PENLIS then return ctx:random(level * 2, level * 10)
    elseif spell_id == SPELL_CELEB then  return ctx:random(level * 3, level * 12)
    elseif spell_id == SPELL_MAHA then   return ctx:random(level * 4, level * 15)
    end
    return ctx:random(1, 8)
end

local function spell_heal_amount(ctx, spell_id, level)
    level = math.max(1, level)
    if spell_id == SPELL_CURE_LIGHT then
        return ctx:random(1, 8) + math.min(math.floor(level / 4), 5)
    elseif spell_id == SPELL_CURE_CRITIC then
        return ctx:random(3, 8) + math.min(math.floor(level / 2), 10)
    elseif spell_id == SPELL_HEAL then
        return 100 + ctx:random(0, level)
    end
    return ctx:random(1, 8)
end

local function cast_spell_effect(ctx, caster, spell, target)
    local spell_id = spell.id
    local damage = 0

    -- Offensive
    if spell.target_type == "offensive" then
        if DAMAGE_SPELL_IDS[spell_id] then
            damage = spell_damage(ctx, spell_id, caster.level)
            if ctx:has_spell_affect(target, SPELL_SANCTUARY) then
                damage = math.floor(damage / 2)
            end
            -- Damage cap
            damage = math.min(damage, 10000)
            target.hp = target.hp - damage
            ctx:send("{bright_magenta}" .. spell.korean_name .. "이(가) " ..
                     target.name .. "에게 " .. damage .. "의 피해를 입힙니다!{reset}")
            if target.session then
                ctx:send_to(target,
                    "{bright_magenta}" .. caster.name .. "의 " .. spell.korean_name ..
                    "이(가) 당신에게 " .. damage .. "의 피해를 입힙니다!{reset}")
            end
        elseif spell_id == SPELL_BLINDNESS then
            ctx:apply_spell_buff(target, SPELL_BLINDNESS, 2 + math.floor(caster.level / 4))
            ctx:send(target.name .. "의 눈이 먼 것 같습니다!")
        elseif spell_id == SPELL_CURSE then
            ctx:apply_spell_buff(target, SPELL_CURSE, 3 + math.floor(caster.level / 5), {hitroll=-2, damroll=-2})
            ctx:send(target.name .. "에게 저주가 내렸습니다!")
        elseif spell_id == SPELL_POISON then
            ctx:apply_spell_buff(target, SPELL_POISON, 3 + math.floor(caster.level / 5), {damage_per_tick=2})
            ctx:send(target.name .. "이(가) 중독되었습니다!")
        elseif spell_id == SPELL_SLEEP then
            if target.level <= caster.level + 3 then
                target.position = 6
                target.fighting = nil
                ctx:send(target.name .. "이(가) 잠에 빠집니다...")
            end
        elseif spell_id == SPELL_CHARM then
            if target.level <= caster.level then
                ctx:apply_spell_buff(target, SPELL_CHARM, 3 + math.floor(caster.level / 5))
                ctx:send(target.name .. "이(가) 당신에게 매혹되었습니다!")
            end
        end

    -- Defensive/healing
    elseif spell.target_type == "defensive" then
        if spell_id == SPELL_CURE_LIGHT or spell_id == SPELL_CURE_CRITIC or spell_id == SPELL_HEAL then
            local heal = spell_heal_amount(ctx, spell_id, caster.level)
            target.hp = math.min(target.max_hp, target.hp + heal)
            ctx:send_to(target, "{bright_green}" .. heal .. "만큼 회복됩니다!{reset}")
        elseif spell_id == SPELL_CURE_BLIND then
            ctx:remove_spell_affect(target, SPELL_BLINDNESS)
            ctx:send_to(target, "시야가 돌아옵니다!")
        elseif spell_id == SPELL_ARMOR or spell_id == SPELL_GROUP_ARMOR then
            ctx:apply_spell_buff(target, SPELL_ARMOR, 24, {ac_bonus=-20})
            ctx:send_to(target, "마법 갑옷이 감싸줍니다.")
        elseif spell_id == SPELL_BLESS then
            ctx:apply_spell_buff(target, SPELL_BLESS, 6 + math.floor(caster.level / 2), {hitroll=2, damroll=2})
            ctx:send_to(target, "축복받은 느낌이 듭니다.")
        elseif spell_id == SPELL_STRENGTH then
            ctx:apply_spell_buff(target, SPELL_STRENGTH, 6 + math.floor(caster.level / 3), {str_bonus=2})
            ctx:send_to(target, "힘이 솟구칩니다!")
        elseif spell_id == SPELL_SANCTUARY then
            ctx:apply_spell_buff(target, SPELL_SANCTUARY, 4, {damage_reduction=0.5})
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
        if spell_id == SPELL_INVIS then
            ctx:apply_spell_buff(target, SPELL_INVIS, 12 + math.floor(caster.level / 4))
            ctx:send("몸이 투명해집니다!")
        elseif spell_id == SPELL_DETECT_INVIS then
            ctx:apply_spell_buff(target, SPELL_DETECT_INVIS, 12 + math.floor(caster.level / 4))
            ctx:send("눈이 밝아집니다.")
        elseif spell_id == SPELL_DETECT_MAGIC then
            ctx:apply_spell_buff(target, SPELL_DETECT_MAGIC, 12 + math.floor(caster.level / 4))
            ctx:send("마법의 기운을 느낄 수 있습니다.")
        elseif spell_id == SPELL_INFRAVISION then
            ctx:apply_spell_buff(target, SPELL_INFRAVISION, 12 + math.floor(caster.level / 4))
            ctx:send("어둠 속에서도 볼 수 있습니다.")
        elseif spell_id == SPELL_WATERWALK then
            ctx:apply_spell_buff(target, SPELL_WATERWALK, 24)
            ctx:send("물 위를 걸을 수 있습니다.")
        elseif spell_id == SPELL_FLY then
            ctx:apply_spell_buff(target, SPELL_FLY, 12 + math.floor(caster.level / 4))
            ctx:send("몸이 공중으로 떠오릅니다!")
        end
    end

    return damage
end

-- ── cast command ────────────────────────────────────────────

register_command("cast", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position < 8 and ch.position ~= 7 then
        ctx:send("일어서야 합니다.")
        return
    end

    if not args or args == "" then
        ctx:send("어떤 주문을 시전하시겠습니까?")
        return
    end

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

    -- Word of Recall
    if spell.id == SPELL_WORD_RECALL then
        ch.mana = ch.mana - spell.mana_cost
        local start_room = ctx:get_start_room()
        ctx:stop_combat(ch)
        ctx:move_to(start_room)
        ctx:send("{bright_white}몸이 가벼워지며 순간이동합니다!{reset}")
        ctx:defer_look()
        return
    end

    ch.mana = ch.mana - spell.mana_cost

    if spell.target_type == "offensive" and target ~= ch then
        ctx:start_combat(target)
    end

    local damage = cast_spell_effect(ctx, ch, spell, target)

    if target.hp <= 0 and target ~= ch then
        ctx:stop_combat(ch)
        ctx:defer_death(target, ch)
    end
end, "시전")

-- ── practice command ────────────────────────────────────────

register_command("practice", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local lines = {"{bright_cyan}-- 시전 가능한 주문 --{reset}"}

    local sorted = {}
    for _, sp in pairs(SPELLS) do
        sorted[#sorted + 1] = sp
    end
    table.sort(sorted, function(a, b) return a.id < b.id end)

    local found = false
    for _, spell in ipairs(sorted) do
        local min_lv = spell.min_level[ch.class_id] or 999
        if min_lv < 999 and min_lv <= ch.level then
            local prof = ctx:get_skill_proficiency(ch, spell.id)
            lines[#lines + 1] = "  " .. spell.korean_name ..
                string.rep(" ", math.max(1, 12 - #spell.korean_name)) ..
                " (" .. spell.name ..
                string.rep(" ", math.max(1, 20 - #spell.name)) ..
                ") 레벨 " .. min_lv .. " 숙련: " .. prof .. "%"
            found = true
        end
    end

    if not found then
        lines[#lines + 1] = "  시전할 수 있는 주문이 없습니다."
    end

    ctx:send(table.concat(lines, "\r\n"))
end, "학습")
