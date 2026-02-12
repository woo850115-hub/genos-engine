-- thac0.lua — 3eyes THAC0 combat system
-- d30 hit roll, 8x20 THAC0 table, proficiency bonus, stat bonus

-- THAC0 table: thaco_list[class][level/10+1] (1-indexed Lua)
-- From global.c thaco_list[18][20]
local THAC0_TABLE = {
    [1] = {18,18,18,17,17,16,16,15,15,14,14,13,13,12,12,11,10,10,9,9},  -- Assassin
    [2] = {20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,3,2},        -- Barbarian
    [3] = {20,20,19,18,18,17,16,16,15,14,14,13,13,12,12,11,10,10,9,8},  -- Cleric
    [4] = {20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,3,3},        -- Fighter
    [5] = {20,20,19,19,18,18,18,17,17,16,16,16,15,15,14,14,14,13,13,11},-- Mage
    [6] = {19,19,18,18,17,16,16,15,15,14,14,13,13,12,11,11,10,9,8,7},  -- Paladin
    [7] = {19,19,18,17,16,16,15,15,14,14,13,12,12,11,11,10,9,9,8,7},   -- Ranger
    [8] = {20,20,19,19,18,18,17,17,16,16,15,15,14,14,13,13,12,12,11,11},-- Thief
}

local ATTACK_TYPES = {
    [0]="때림", [1]="베기", [2]="으스러뜨림", [3]="찌름",
    [4]="두드림", [5]="할퀴기", [6]="난타", [7]="물기",
}

-- Get base THAC0 from class/level table
local function get_base_thac0(class_id, level)
    local row = THAC0_TABLE[class_id]
    if not row then return 20 end
    -- level/10 + 1 for Lua indexing, clamped 1-20
    local idx = math.min(20, math.max(1, math.floor(level / 10) + 1))
    return row[idx] or 20
end

-- Get effective THAC0 for a mob
local function get_thac0(mob)
    if mob.is_npc then
        return 20
    end
    local base = get_base_thac0(mob.class_id or 4, mob.level or 1)
    -- STR bonus
    local str_val = te_stat(mob, "str", 13)
    base = base - te_bonus(str_val)
    -- Proficiency bonus (weapon type from equipped weapon, default 0=SHARP)
    local prof_bonus = math.floor(te_prof_percent(mob, 0) / 20)
    base = base - prof_bonus
    return math.max(1, base)
end

-- d30-based hit determination (3eyes uses d30, not d20!)
-- From source: mrand(1,30) >= thaco - AC/10
local function check_hit(thac0, target_ac)
    local needed = thac0 - math.floor(target_ac / 10)
    local roll = math.random(1, 30)
    return roll >= needed, roll
end

-- Calculate damage
local function calc_damage(attacker, defender)
    local str_val = te_stat(attacker, "str", 13)
    local str_bonus = te_bonus(str_val)
    local base_dmg

    if attacker.is_npc then
        -- NPC: parse damage_dice "NdS+B" from proto
        local dice_str = ""
        local ok, dd = pcall(function() return attacker.proto.damage_dice end)
        if ok and dd then dice_str = dd end
        local ndice, sdice, pdice = 1, 4, 0
        local n, s, p = dice_str:match("(%d+)d(%d+)%+(%d+)")
        if n then ndice, sdice, pdice = tonumber(n), tonumber(s), tonumber(p) end
        base_dmg = pdice
        for i = 1, ndice do
            base_dmg = base_dmg + math.random(1, math.max(1, sdice))
        end
    else
        -- PC: weapon damage + STR bonus + proficiency/10
        local weapon_dmg = 0
        local ok, weapon = pcall(function() return attacker.equipment["weapon"] end)
        if not ok or not weapon then
            ok, weapon = pcall(function() return attacker.equipment[16] end)
        end
        if ok and weapon and weapon.proto then
            local dice_str = "1d4+0"
            local ok2, dmg = pcall(function() return weapon.proto.values["damage"] end)
            if ok2 and dmg then dice_str = dmg end
            local n, s, p = dice_str:match("(%d+)d(%d+)%+(-?%d+)")
            local wnd = tonumber(n) or 1
            local wsd = tonumber(s) or 4
            local wpd = tonumber(p) or 0
            weapon_dmg = wpd
            for i = 1, wnd do
                weapon_dmg = weapon_dmg + math.random(1, math.max(1, wsd))
            end
        else
            -- Barehanded: class dice
            weapon_dmg = math.random(1, 3) + math.floor(attacker.level / 10)
        end
        base_dmg = weapon_dmg + str_bonus + math.floor(te_prof_percent(attacker, 0) / 10)
    end

    return math.max(1, base_dmg)
end

-- Number of attacks (3eyes multi-attack)
-- From source: base 1 + level/flag based extras
local function num_attacks(mob)
    if mob.is_npc then return 1 end
    local attacks = 1
    local level = mob.level or 1
    -- Level-based extra attacks
    if level >= 100 then
        attacks = attacks + 1
    end
    if level >= 50 then
        attacks = attacks + 1
    end
    -- Random chance for bonus attack
    if math.random(0, 3) > 2 then
        attacks = attacks + 1
    end
    return math.min(5, attacks)
end

-- Get damage message
local function damage_msg(dmg)
    if dmg <= 0 then return "빗나감", "{white}"
    elseif dmg <= 5 then return "긁힘", "{white}"
    elseif dmg <= 15 then return "타격", "{yellow}"
    elseif dmg <= 30 then return "강타", "{bright_yellow}"
    elseif dmg <= 50 then return "난타", "{bright_red}"
    elseif dmg <= 80 then return "맹타", "{red}"
    elseif dmg <= 120 then return "폭타", "{bright_magenta}"
    else return "치명타", "{bright_magenta}"
    end
end

-- Combat round hook
register_hook("combat_round", function(ctx, attacker, defender)
    local attacks = num_attacks(attacker)
    local total_dmg = 0

    for i = 1, attacks do
        local thac0 = get_thac0(attacker)
        local ac = defender.armor_class or 100
        local hit, roll = check_hit(thac0, ac)

        if hit then
            local dmg = calc_damage(attacker, defender)
            -- Critical hit: proficiency-based chance
            local crit_chance = te_prof_percent(attacker, 0) / 2
            if math.random(1, 100) <= crit_chance then
                local crit_mult = math.random(3, 6)
                dmg = dmg * crit_mult
                if attacker.session then
                    ctx:send_to(attacker, "{bright_magenta}급소 명중! (x" .. crit_mult .. "){reset}")
                end
            end

            total_dmg = total_dmg + dmg
            defender.hp = defender.hp - dmg

            local msg_text, msg_color = damage_msg(dmg)
            if attacker.session then
                ctx:send_to(attacker, msg_color .. defender.name .. "에게 " ..
                    msg_text .. " [" .. dmg .. "]{reset}")
            end
            if defender.session then
                ctx:send_to(defender, "{red}" .. attacker.name .. "이(가) 당신을 공격합니다! [" ..
                    dmg .. "]{reset}")
            end

            if defender.hp <= 0 then
                ctx:stop_combat(attacker)
                ctx:defer_death(defender, attacker)
                return
            end
        else
            if attacker.session then
                ctx:send_to(attacker, "{white}" .. defender.name .. "을(를) 빗맞힙니다.{reset}")
            end
        end
    end
end)
