-- thac0.lua — tbaMUD THAC0 combat system
-- Registers combat_round hook for engine._combat_round

local ATTACK_TYPES = {
    [0]="때림", [1]="찌름(쏘아)", [2]="채찍질", [3]="베기",
    [4]="물기", [5]="타격", [6]="으스러뜨림", [7]="두드림",
    [8]="할퀴기", [9]="난타", [10]="강타", [11]="관통",
    [12]="폭발", [13]="주먹질", [14]="찌르기",
}

local THAC0_TABLE = {
    [0] = {[0]=100,[1]=20,[2]=20,[3]=20,[4]=19,[5]=19,[6]=19,[7]=18,[8]=18,[9]=18,
        [10]=17,[11]=17,[12]=17,[13]=16,[14]=16,[15]=16,[16]=15,[17]=15,[18]=15,
        [19]=14,[20]=14,[21]=14,[22]=13,[23]=13,[24]=13,[25]=12,[26]=12,[27]=12,
        [28]=11,[29]=11,[30]=11,[31]=10,[32]=10,[33]=10,[34]=9},
    [1] = {[0]=100,[1]=20,[2]=20,[3]=20,[4]=18,[5]=18,[6]=18,[7]=16,[8]=16,[9]=16,
        [10]=14,[11]=14,[12]=14,[13]=12,[14]=12,[15]=12,[16]=10,[17]=10,[18]=10,
        [19]=8,[20]=8,[21]=8,[22]=6,[23]=6,[24]=6,[25]=4,[26]=4,[27]=4,
        [28]=2,[29]=2,[30]=2,[31]=1,[32]=1,[33]=1,[34]=1},
    [2] = {[0]=100,[1]=20,[2]=20,[3]=19,[4]=19,[5]=18,[6]=18,[7]=17,[8]=17,[9]=16,
        [10]=16,[11]=15,[12]=15,[13]=14,[14]=14,[15]=13,[16]=13,[17]=12,[18]=12,
        [19]=11,[20]=11,[21]=10,[22]=10,[23]=9,[24]=9,[25]=8,[26]=8,[27]=7,
        [28]=7,[29]=6,[30]=6,[31]=5,[32]=5,[33]=4,[34]=4},
    [3] = {[0]=100,[1]=20,[2]=19,[3]=18,[4]=17,[5]=16,[6]=15,[7]=14,[8]=14,[9]=13,
        [10]=12,[11]=11,[12]=10,[13]=9,[14]=8,[15]=7,[16]=6,[17]=5,[18]=4,
        [19]=3,[20]=2,[21]=1,[22]=1,[23]=1,[24]=1,[25]=1,[26]=1,[27]=1,
        [28]=1,[29]=1,[30]=1,[31]=1,[32]=1,[33]=1,[34]=1},
}

local STR_TOHIT = {
    [0]=-5,[1]=-5,[2]=-3,[3]=-3,[4]=-2,[5]=-2,[6]=-1,[7]=-1,[8]=0,[9]=0,
    [10]=0,[11]=0,[12]=0,[13]=0,[14]=0,[15]=0,[16]=0,[17]=1,[18]=1,
    [19]=3,[20]=3,[21]=4,[22]=4,[23]=5,[24]=6,[25]=7,
    [26]=1,[27]=2,[28]=2,[29]=2,[30]=3,
}

local STR_TODAM = {
    [0]=-4,[1]=-4,[2]=-2,[3]=-1,[4]=-1,[5]=-1,[6]=0,[7]=0,[8]=0,[9]=0,
    [10]=0,[11]=0,[12]=0,[13]=0,[14]=0,[15]=0,[16]=1,[17]=1,[18]=2,
    [19]=7,[20]=8,[21]=9,[22]=10,[23]=11,[24]=12,[25]=14,
    [26]=3,[27]=3,[28]=4,[29]=5,[30]=6,
}

local DEX_DEFENSIVE = {
    [0]=6,[1]=5,[2]=5,[3]=4,[4]=3,[5]=2,[6]=1,[7]=0,[8]=0,[9]=0,
    [10]=0,[11]=0,[12]=0,[13]=0,[14]=0,[15]=-1,[16]=-2,[17]=-3,[18]=-4,
    [19]=-4,[20]=-4,[21]=-5,[22]=-5,[23]=-5,[24]=-6,[25]=-6,
}


local function get_thac0(class_id, level)
    local tbl = THAC0_TABLE[class_id] or THAC0_TABLE[0]
    local clamped = math.min(level, 34)
    return tbl[clamped] or 20
end

local function get_stat(mob, key, default)
    default = default or 13
    local ok, val = pcall(function() return mob.stats[key] end)
    if ok and val then return val end
    return default
end

local function compute_ac(char)
    local ac
    if char.is_npc then
        ac = char.proto.armor_class
    else
        ac = 100
    end
    -- Dex bonus
    local dex = math.min(math.max(get_stat(char, "dex", 13), 0), 25)
    ac = ac + (DEX_DEFENSIVE[dex] or 0)
    return math.max(-10, math.min(ac, 100))
end

local function roll_hit(ctx, attacker, defender)
    local thac0, hr
    if attacker.is_npc then
        thac0 = math.max(1, 20 - attacker.level)
        hr = attacker.proto.hitroll
    else
        thac0 = get_thac0(attacker.class_id, attacker.level)
        hr = (attacker.hitroll or 0) + (STR_TOHIT[math.min(get_stat(attacker, "str", 13), 30)] or 0)
    end
    local ac = compute_ac(defender)
    local roll = ctx:random(1, 20)
    local needed = thac0 - hr
    if roll == 20 then return true end
    if roll == 1 then return false end
    return roll >= needed - ac
end

local function roll_damage(ctx, attacker)
    local dice_str = attacker.proto.damage_dice
    local num, rest = dice_str:match("(%d+)d(.+)")
    num = tonumber(num) or 1
    local size, bonus
    if rest:find("+", 1, true) then
        size, bonus = rest:match("(%d+)%+(-?%d+)")
    elseif rest:find("%-") then
        size, bonus = rest:match("(%d+)%-(%d+)")
        if bonus then bonus = "-" .. bonus end
    else
        size = rest
        bonus = "0"
    end
    size = tonumber(size) or 4
    bonus = tonumber(bonus) or 0

    local total = bonus
    for i = 1, num do
        total = total + ctx:random(1, size)
    end

    if not attacker.is_npc then
        total = total + (STR_TODAM[math.min(get_stat(attacker, "str", 13), 30)] or 0)
        total = total + (attacker.damroll or 0)
    end

    return math.max(1, total)
end

local function get_attack_type(attacker)
    local atk_type = 0
    local equip = attacker.equipment
    if equip then
        local ok, weapon = pcall(function() return equip[16] end)
        if ok and weapon and weapon.proto then
            local ok2, v = pcall(function() return weapon.proto.values[3] end)
            if ok2 and v then atk_type = tonumber(v) or 0 end
        end
    end
    return atk_type, ATTACK_TYPES[atk_type] or "때림"
end

local function damage_message(damage)
    -- Original tbaMUD-style 23-level damage messages
    if damage <= 0 then return "빗나감", "{cyan}"
    elseif damage == 1 then return "간신히 긁힘", "{cyan}"
    elseif damage <= 2 then return "긁힘", "{cyan}"
    elseif damage <= 4 then return "약간 상처", "{yellow}"
    elseif damage <= 6 then return "상처", "{yellow}"
    elseif damage <= 8 then return "꽤 큰 상처", "{yellow}"
    elseif damage <= 10 then return "타격", "{yellow}"
    elseif damage <= 13 then return "강한 타격", "{bright_yellow}"
    elseif damage <= 16 then return "매우 강한 타격", "{bright_yellow}"
    elseif damage <= 20 then return "극심한 타격", "{bright_yellow}"
    elseif damage <= 25 then return "참혹한 타격", "{red}"
    elseif damage <= 30 then return "치명적 타격", "{red}"
    elseif damage <= 40 then return "파괴적 타격", "{red}"
    elseif damage <= 50 then return "분쇄", "{bright_red}"
    elseif damage <= 65 then return "황폐화", "{bright_red}"
    elseif damage <= 80 then return "절멸", "{bright_red}"
    elseif damage <= 100 then return "소멸", "{bright_magenta}"
    elseif damage <= 130 then return "말살", "{bright_magenta}"
    elseif damage <= 170 then return "섬멸", "{bright_magenta}"
    elseif damage <= 220 then return "전멸", "{bright_white}"
    elseif damage <= 280 then return "천벌", "{bright_white}"
    else return "신의 일격", "{bright_white}"
    end
end

local function extra_attacks(attacker)
    if attacker.is_npc then
        return math.min(math.floor(attacker.level / 10), 3)
    end
    if attacker.class_id == 3 then -- Warrior
        if attacker.level >= 20 then return 2
        elseif attacker.level >= 10 then return 1
        end
    end
    return 0
end

-- ── Combat round hook ─────────────────────────────────────────

register_hook("combat_round", function(ctx, attacker, defender)
    attacker.position = 7  -- POS_FIGHTING
    local _, atk_name = get_attack_type(attacker)

    local n = 1 + extra_attacks(attacker)
    for i = 1, n do
        if defender.hp <= 0 then break end

        if not roll_hit(ctx, attacker, defender) then
            ctx:send_to(attacker,
                "{yellow}" .. defender.name .. "에게 " .. atk_name ..
                "을 시도하지만 빗나갑니다!{reset}")
            if defender.session then
                ctx:send_to(defender,
                    "{yellow}" .. attacker.name .. "의 " .. atk_name ..
                    "이 빗나갑니다!{reset}")
            end
        else
            local dmg = roll_damage(ctx, attacker)

            -- Sanctuary: halve damage
            if ctx:has_spell_affect(defender, 14) then
                dmg = math.max(1, math.floor(dmg / 2))
            end

            local severity, color = damage_message(dmg)
            ctx:send_to(attacker,
                color .. defender.name .. "에게 " .. atk_name ..
                "으로 " .. severity .. "을 입힙니다! [" .. dmg .. "]{reset}")
            if defender.session then
                ctx:send_to(defender,
                    color .. attacker.name .. "의 " .. atk_name ..
                    "이 " .. severity .. "을 입힙니다! [" .. dmg .. "]{reset}")
            end
            defender.hp = defender.hp - dmg

            -- Hide breaks on damage taken
            if ctx:has_affect(defender, 1002) then
                ctx:remove_affect(defender, 1002)
                if defender.session then
                    ctx:send_to(defender, "공격을 받아 모습이 드러납니다!")
                end
            end
        end
    end

    -- Show defender condition to attacker
    if defender.hp > 0 and attacker.session then
        local ratio = defender.hp / math.max(1, defender.max_hp)
        local condition
        if ratio >= 1.0 then condition = "완벽한 상태"
        elseif ratio >= 0.75 then condition = "약간의 상처"
        elseif ratio >= 0.50 then condition = "상당한 부상"
        elseif ratio >= 0.30 then condition = "{red}심각한 부상{reset}"
        elseif ratio >= 0.15 then condition = "{bright_red}거의 죽어감{reset}"
        else condition = "{bright_red}치명적 상태!{reset}"
        end
        ctx:send_to(attacker, "[" .. defender.name .. ": " .. condition .. "]")
    end

    -- Check death
    if defender.hp <= 0 then
        ctx:stop_combat(attacker)
        ctx:defer_death(defender, attacker)
    end
end)
