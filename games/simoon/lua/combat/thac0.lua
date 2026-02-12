-- thac0.lua — Simoon THAC0 combat system
-- KEY DIFFERENCE: PC THAC0 = 1 (fixed!), NPC THAC0 = 20
-- Multi-attack by level bands, reflect damage

local ATTACK_TYPES = {
    [0]="때림", [1]="찌름", [2]="채찍질", [3]="베기",
    [4]="물기", [5]="타격", [6]="으스러뜨림", [7]="두드림",
    [8]="할퀴기", [9]="난타", [10]="강타", [11]="관통",
    [12]="폭발", [13]="주먹질", [14]="찌르기",
}

local STR_TOHIT = {
    [0]=-5,[1]=-5,[2]=-3,[3]=-3,[4]=-2,[5]=-2,[6]=-1,[7]=-1,[8]=0,[9]=0,
    [10]=0,[11]=0,[12]=0,[13]=0,[14]=0,[15]=0,[16]=0,[17]=1,[18]=1,
    [19]=3,[20]=3,[21]=4,[22]=4,[23]=5,[24]=6,[25]=7,
}

local STR_TODAM = {
    [0]=-4,[1]=-4,[2]=-2,[3]=-1,[4]=-1,[5]=-1,[6]=0,[7]=0,[8]=0,[9]=0,
    [10]=0,[11]=0,[12]=0,[13]=0,[14]=0,[15]=0,[16]=1,[17]=1,[18]=2,
    [19]=7,[20]=8,[21]=9,[22]=10,[23]=11,[24]=12,[25]=14,
}

local DEX_DEFENSIVE = {
    [0]=6,[1]=5,[2]=5,[3]=4,[4]=3,[5]=2,[6]=1,[7]=0,[8]=0,[9]=0,
    [10]=0,[11]=0,[12]=0,[13]=0,[14]=0,[15]=-1,[16]=-2,[17]=-3,[18]=-4,
    [19]=-4,[20]=-4,[21]=-5,[22]=-5,[23]=-5,[24]=-6,[25]=-6,
}


-- PC THAC0 = 1 (Simoon's biggest difference from tbaMUD)
-- NPC THAC0 = 20 - level (clamped)
local function get_thac0(mob)
    if mob.is_npc then
        local base = 20
        if mob.level < 30 then
            base = base + (20 - mob.level)
        end
        return math.max(1, base)
    end
    -- PC: fixed base 1, with INT/WIS bonuses
    local thac0 = 1
    if mob.level < 30 then
        thac0 = thac0 + (20 - mob.level)
    end
    -- INT/WIS reduce THAC0
    local int_val = simoon_stat(mob, "int", 13)
    local wis_val = simoon_stat(mob, "wis", 13)
    thac0 = thac0 - math.floor((int_val - 13) / 1.5)
    thac0 = thac0 - math.floor((wis_val - 13) / 1.5)
    return math.max(1, thac0)
end

local function compute_ac(char)
    local ac
    if char.is_npc then
        ac = char.proto.armor_class
    else
        ac = 100
    end
    local dex = math.min(math.max(simoon_stat(char, "dex", 13), 0), 25)
    ac = ac + (DEX_DEFENSIVE[dex] or 0)
    return math.max(-10, math.min(ac, 100))
end

local function roll_hit(ctx, attacker, defender)
    local thac0 = get_thac0(attacker)
    local hr
    if attacker.is_npc then
        hr = attacker.proto.hitroll
    else
        hr = (attacker.hitroll or 0) +
            (STR_TOHIT[math.min(simoon_stat(attacker, "str", 13), 25)] or 0)
    end
    local ac = compute_ac(defender)
    local roll = ctx:random(1, 20)
    if roll == 20 then return true end
    if roll == 1 then return false end
    local needed = thac0 - hr
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
        total = total + (STR_TODAM[math.min(simoon_stat(attacker, "str", 13), 25)] or 0)
        total = total + (attacker.damroll or 0)

        -- Caster bonus: if mana-based class AND max_mana < max_hp AND dam > 2
        if SIMOON_CASTER[attacker.class_id] and
           attacker.max_mana < attacker.max_hp and total > 2 then
            total = total + math.floor(total / 2)
        end
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
    elseif damage <= 150 then return "말살", "{bright_magenta}"
    elseif damage <= 250 then return "섬멸", "{bright_magenta}"
    elseif damage <= 400 then return "전멸", "{bright_white}"
    elseif damage <= 600 then return "천벌", "{bright_white}"
    else return "신의 일격", "{bright_white}"
    end
end

-- Simoon multi-attack: level-based bands + 10% random bonus
local function num_attacks(attacker)
    if attacker.is_npc then
        return math.min(math.floor(attacker.level / 10), 3) + 1
    end
    local lv = attacker.level
    local base
    if lv >= 150 then base = 5
    elseif lv >= 100 then base = 4
    elseif lv >= 50 then base = 3
    elseif lv >= 30 then base = 3
    elseif lv >= 20 then base = 2
    elseif lv >= 5 then base = 2
    else base = 1
    end
    -- 10% chance for bonus attack
    if math.random(1, 10) == 1 then
        base = base + 1
    end
    return base
end

-- ── Combat round hook ─────────────────────────────────────────

register_hook("combat_round", function(ctx, attacker, defender)
    attacker.position = 7  -- POS_FIGHTING
    local _, atk_name = get_attack_type(attacker)

    local n = num_attacks(attacker)
    local total_dmg = 0
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

            -- Damage cap: 10000 (15000 with sanctuary)
            local cap = ctx:has_spell_affect(defender, 14) and 15000 or 10000
            dmg = math.min(dmg, cap)

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
            total_dmg = total_dmg + dmg

            -- Reflect damage (10% chance, requires defender level >= attacker level)
            if not defender.is_npc and defender.level >= attacker.level and
               ctx:random(1, 10) == 1 and attacker.hp > 0 then
                local reflect = math.floor(dmg / 2)
                if reflect > 0 then
                    attacker.hp = attacker.hp - reflect
                    ctx:send_to(attacker,
                        "{red}" .. defender.name .. "의 반격! " .. reflect .. " 피해!{reset}")
                    if defender.session then
                        ctx:send_to(defender,
                            "{cyan}반사 공격으로 " .. reflect .. " 피해를 입혔습니다!{reset}")
                    end
                end
            end
        end
    end

    -- Show defender condition
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
    if attacker.hp <= 0 then
        ctx:stop_combat(defender)
        ctx:defer_death(attacker, defender)
    end
end)
