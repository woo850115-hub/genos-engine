-- thac0.lua — 3eyes combat system (original-faithful rewrite)
-- From source: command5.c (attack_crt), player.c (compute_thaco, mod_profic)
-- Uses: te_compute_thaco, te_mod_profic, te_profic, te_bonus from lib.lua

-- ── Attack type messages ────────────────────────────────────────
local ATTACK_TYPES = {
    [0]="때림", [1]="베기", [2]="으스러뜨림", [3]="찌름",
    [4]="두드림", [5]="할퀴기", [6]="난타", [7]="물기",
}

-- ── mdice() — roll weapon/creature dice ─────────────────────────
local function mdice(obj_or_crt)
    -- Parse "NdS+P" from damage_dice or weapon values
    local dice_str = ""
    if obj_or_crt.proto then
        local ok, dd = pcall(function() return obj_or_crt.proto.damage_dice end)
        if ok and dd then dice_str = dd end
        if dice_str == "" then
            local ok2, vals = pcall(function() return obj_or_crt.proto.values end)
            if ok2 and vals then
                local ok3, dmg = pcall(function() return vals["damage"] end)
                if ok3 and dmg then dice_str = dmg end
            end
        end
    end
    local n, s, p = dice_str:match("(%d+)d(%d+)([%+%-]?%d*)")
    local ndice = tonumber(n) or 1
    local sdice = tonumber(s) or 4
    local pdice = tonumber(p) or 0
    local total = pdice
    for i = 1, ndice do
        total = total + math.random(1, math.max(1, sdice))
    end
    return math.max(1, total)
end

-- ── Get equipped weapon ─────────────────────────────────────────
local function get_weapon(mob)
    -- Try slot 16 (WIELD) or "weapon"
    local ok, weapon = pcall(function() return mob.equipment[16] end)
    if ok and weapon and weapon.proto then return weapon end
    ok, weapon = pcall(function() return mob.equipment["weapon"] end)
    if ok and weapon and weapon.proto then return weapon end
    return nil
end

-- ── Get weapon type (proficiency index: 0-4) ────────────────────
local function get_weapon_type(weapon)
    if not weapon or not weapon.proto then return 2 end  -- default BLUNT
    local ok, vals = pcall(function() return weapon.proto.values end)
    if not ok or not vals then return 2 end
    local ok2, wtype = pcall(function() return vals["weapon_type"] end)
    if ok2 and wtype then
        local t = tonumber(wtype)
        if t then return math.min(4, math.max(0, t)) end
    end
    return 2
end

-- ── Object flag constants ──────────────────────────────────────
OALCRT = 10   -- Always critical
OCURSE = 3    -- Cursed (can't drop)
OSHADO = 50   -- Shadow attack

-- ── Check weapon object flag ────────────────────────────────────
local function obj_has_flag(obj, flag_bit)
    if not obj or not obj.proto then return false end
    local ok, flags = pcall(function() return obj.proto.act_flags end)
    if not ok or not flags then
        -- Also try obj.proto.flags
        ok, flags = pcall(function() return obj.proto.flags end)
        if not ok or not flags then return false end
    end
    if type(flags) == "table" then
        for _, f in ipairs(flags) do
            if f == flag_bit or f == tostring(flag_bit) or
               f == "flag_" .. flag_bit then return true end
        end
    end
    return false
end

-- ── Check if NPC mob has act_flag ───────────────────────────────
local function mob_has_flag(mob, flag_id)
    if not mob or not mob.proto then return false end
    local ok, flags = pcall(function() return mob.proto.act_flags end)
    if not ok or not flags then return false end
    if type(flags) == "table" then
        for _, f in ipairs(flags) do
            if f == flag_id or f == tostring(flag_id) or
               f == "flag_" .. flag_id then return true end
        end
    end
    return false
end

-- ── Check if player has flag via session.player_data ────────────
local function player_has_flag(mob, flag_id)
    if not mob.session then return false end
    local ok, pd = pcall(function() return mob.session.player_data end)
    if not ok or not pd then return false end
    local ok2, flags = pcall(function() return pd.flags end)
    if not ok2 or not flags then return false end
    -- Python list: 0-indexed pcall loop
    local i = 0
    while true do
        local ok3, f = pcall(function() return flags[i] end)
        if not ok3 or f == nil then break end
        if f == flag_id then return true end
        i = i + 1
    end
    return false
end

-- ── check_couple_exist — command5.c:22-51 ───────────────────────
-- Returns true if spouse is in the same room → 2x damage bonus
local function check_couple_exist(mob)
    if mob.is_npc then return false end
    if not player_has_flag(mob, PMARRI) then return false end
    -- Advanced classes don't get marriage power
    local cls = mob.class_id or CLASS_FIGHTER
    if cls > CLASS_INVINCIBLE then return false end
    -- Get partner name from extensions
    local partner_name = nil
    pcall(function()
        partner_name = mob.extensions.partner
    end)
    if not partner_name or partner_name == "" then return false end
    -- Check if partner is in same room
    local room = nil
    pcall(function()
        room = mob.session._engine.world.rooms[mob.room_vnum]
    end)
    if not room then return false end
    local ok, chars = pcall(function() return room.characters end)
    if not ok or not chars then return false end
    local i = 0
    while true do
        local ok2, ch = pcall(function() return chars[i] end)
        if not ok2 or ch == nil then break end
        if not ch.is_npc and ch.name == partner_name then
            return true
        end
        i = i + 1
    end
    return false
end

-- ── unequip_weapon — remove weapon from slot 16, add to inventory ─
local function unequip_weapon(mob)
    local weapon = nil
    pcall(function()
        weapon = mob.equipment[16]
    end)
    if not weapon then return end
    -- Remove from equipment slot
    pcall(function()
        mob.equipment[16] = nil
    end)
    -- Add to inventory
    pcall(function()
        weapon.worn_by = nil
        weapon.wear_slot = ""
        weapon.carried_by = mob
        mob.inventory:append(weapon)
    end)
    -- Recalculate stats
    pcall(function()
        local recalc = require("core.world").recalc_equip_bonuses
        recalc(mob)
    end)
end

-- ── Count attacks (original command5.c:223-236) ─────────────────
local function count_attacks(mob)
    if mob.is_npc then return 1 end

    local count = 1
    local cls = mob.class_id or CLASS_FIGHTER
    local level = mob.level or 1

    -- PUPDMG bonus attacks (command5.c:225-232)
    if player_has_flag(mob, PUPDMG) then
        if (cls == CLASS_INVINCIBLE and level > 100) or cls > CLASS_INVINCIBLE then
            if math.floor((level - 97) / 10) + te_mrand(0, 3) > 2 then
                count = count + 1
            end
        end
        if cls > CLASS_INVINCIBLE and te_mrand(1, 4) == 1 then
            count = count + 1
        end
    end

    -- Backswing (command5.c:233-236): 25% +1, then 25% +1
    if te_mrand(0, 3) > 2 then
        count = count + 1
        if te_mrand(1, 4) == 1 then
            count = count + 1
        end
    end

    return count
end

-- ── Damage message (Korean) ─────────────────────────────────────
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

-- ── NPC offensive spell list (for MMAGIC) ─────────────────────
-- Subset of offensive spells NPCs can cast (from crt_spell in update.c)
local NPC_SPELLS = {
    {name="매직미사일", dmg_dice="2d4+2"},
    {name="전기충격", dmg_dice="3d4+3"},
    {name="화구", dmg_dice="3d6+4"},
    {name="번개", dmg_dice="4d6+6"},
    {name="얼음폭풍", dmg_dice="5d6+8"},
    {name="산성비", dmg_dice="6d6+10"},
}

-- ── NPC MMAGIC spellcast (update.c:645) ─────────────────────────
-- Returns true if NPC cast a spell (skip melee), false otherwise
local function npc_try_spellcast(ctx, attacker, defender)
    if not attacker.is_npc then return false end
    if not mob_has_flag(attacker, MMAGIC) then return false end
    -- 20% chance to cast (original: n=20, mrand(1,100) <= n)
    if te_mrand(1, 100) > 20 then return false end
    -- Pick random spell
    local spell = NPC_SPELLS[te_mrand(1, #NPC_SPELLS)]
    -- Roll damage from dice string
    local n, s, p = spell.dmg_dice:match("(%d+)d(%d+)([%+%-]?%d*)")
    local dmg = te_dice(tonumber(n) or 2, tonumber(s) or 4, tonumber(p) or 0)
    -- Apply damage
    defender.hp = defender.hp - dmg
    -- Messages
    if defender.session then
        ctx:send_to(defender, "{bright_magenta}\n" .. attacker.name ..
            "이(가) " .. spell.name .. "을(를) 시전합니다!{reset}")
        ctx:send_to(defender, "{red}" .. attacker.name ..
            "의 마법 공격으로 {bright_cyan}" .. dmg .. "{red}의 피해를 받았습니다.{reset}")
    end
    ctx:send_room(attacker.name .. "이(가) " .. spell.name ..
        " 주문을 시전합니다!")
    -- Death check
    if defender.hp <= 0 then
        ctx:send_room("<< " .. defender.name .. "이(가) 죽었습니다 >>")
        ctx:stop_combat(attacker)
        ctx:defer_death(defender, attacker)
        return true
    end
    return true  -- spell cast, skip melee for this round
end

-- ── Combat round hook (original attack_crt) ─────────────────────
register_hook("combat_round", function(ctx, attacker, defender)
    local cls = attacker.class_id or CLASS_FIGHTER
    local level = attacker.level or 1

    -- NPC MMAGIC: try spellcast before melee (update.c:645)
    if attacker.is_npc and npc_try_spellcast(ctx, attacker, defender) then
        return  -- spell was cast, skip melee
    end

    -- Compute attack count
    local attacks = count_attacks(attacker)

    if attacks > 1 then
        local swing_name = attacks == 2 and "연격" or "연격!!!"
        if attacker.session then
            ctx:send_to(attacker, "{bright_white}\n당신은 " .. defender.name ..
                "에게 " .. attacks .. "번의 연타공격을 합니다. " .. swing_name .. "{reset}")
        end
    end

    -- Get thaco (use lib.lua te_compute_thaco for player, table for NPC)
    local thaco
    if attacker.is_npc then
        thaco = te_compute_thaco(attacker)
    else
        thaco = te_compute_thaco(attacker)
    end

    -- Get weapon and type
    local weapon = get_weapon(attacker)
    local weapon_type = weapon and get_weapon_type(weapon) or 2

    for j = 1, attacks do
        -- Weapon durability check (command5.c:249-258)
        if weapon and weapon.proto then
            local ok, shots = pcall(function() return weapon.shots_remaining end)
            if ok and shots and shots < 1 then
                local wname = weapon.name or "무기"
                if attacker.session then
                    ctx:send_to(attacker, "\n{red}" .. wname ..
                        "이(가) 무리한 사용으로 부서져 버렸습니다.{reset}")
                end
                ctx:send_room(attacker.name .. "의 " .. wname ..
                    "이(가) 무리한 사용으로 부서져 버렸습니다.")
                -- Unequip weapon (back to inventory) + recompute thaco
                unequip_weapon(attacker)
                weapon = nil
                break
            end
        end

        -- Hit calculation: n = thaco - AC/10 (command5.c:260-262)
        local ac = defender.armor_class or 100
        local n = thaco - math.floor(ac / 10)
        if player_has_flag(attacker, PFEARS) then n = n + 2 end
        if player_has_flag(attacker, PBLIND) then n = n + 5 end

        local roll = te_mrand(1, 30)
        if roll >= n then
            -- ── HIT ──
            local base_dmg
            local shadow_dmg = 0

            if weapon then
                -- With weapon: mdice(weapon) + STR bonus + profic/10
                base_dmg = mdice(weapon)
                    + te_bonus(te_stat(attacker, "str", 13))
                    + math.floor(te_profic(attacker, weapon_type) / 10)
                shadow_dmg = mdice(weapon) + te_bonus(te_stat(attacker, "str", 13))
            elseif cls == CLASS_BARBARIAN or cls >= CLASS_INVINCIBLE then
                -- Barbarian/Invincible+ bare: mdice + STR bonus + comp_chance
                base_dmg = mdice(attacker)
                    + te_bonus(te_stat(attacker, "str", 13))
                    + te_comp_chance(attacker)
                shadow_dmg = base_dmg
            else
                -- Other bare: mdice + STR bonus
                base_dmg = mdice(attacker)
                    + te_bonus(te_stat(attacker, "str", 13))
                shadow_dmg = base_dmg
            end

            -- Mage/Cleric override: no proficiency bonus (command5.c:283-291)
            if cls == CLASS_MAGE or cls == CLASS_CLERIC then
                if weapon then
                    base_dmg = mdice(weapon) + te_bonus(te_stat(attacker, "str", 13))
                else
                    base_dmg = mdice(attacker) + te_bonus(te_stat(attacker, "str", 13))
                end
            end

            -- DM target: 0 damage (command5.c:293)
            if (defender.class_id or 0) >= CLASS_DM then
                base_dmg = 0
            end

            base_dmg = math.max(1, base_dmg)

            -- Paladin alignment (command5.c:299-308)
            if cls == CLASS_PALADIN then
                local align = attacker.alignment or 0
                if align < 0 then
                    base_dmg = math.floor(base_dmg / 2)
                    if attacker.session then
                        ctx:send_to(attacker, "\n당신의 순수한 마음이 흔들립니다.")
                    end
                elseif align > 250 then
                    base_dmg = base_dmg + te_mrand(1, 3)
                    if attacker.session then
                        ctx:send_to(attacker, "\n당신의 정의의 힘이 강가해집니다.")
                    end
                end
            end

                    -- Bonus damage
            local bonus_dmg = 0

            -- Bonus power (command5.c:310-313): accumulated training bonus
            if not attacker.is_npc and cls < CLASS_INVINCIBLE then
                local bonus_power = 0
                pcall(function()
                    bonus_power = attacker.extensions.bonus_power or 0
                end)
                if bonus_power > 0 then
                    bonus_dmg = bonus_dmg + math.floor(base_dmg * bonus_power / 100 / 5)
                    pcall(function()
                        attacker.extensions.bonus_power = math.max(0, bonus_power - 8)
                    end)
                end
            end

            -- Marriage power (command5.c:314-321): spouse in same room → 2x damage
            local lovepower = check_couple_exist(attacker)
            if lovepower then
                bonus_dmg = bonus_dmg + base_dmg
                if attacker.session then
                    ctx:send_to(attacker, "{magenta}\n당신의 사랑의 힘으로 공격력이 두배로 올라갑니다.{white}")
                end
                ctx:send_room(attacker.name .. "의 사랑의 힘으로 공격력이 두배로 올라갑니다.")
            end

            -- Critical hit: mod_profic% chance (command5.c:322-331)
            local p = te_mod_profic(attacker)
            local crit = false
            if te_mrand(1, 100) <= p or (weapon and obj_has_flag(weapon, OALCRT)) then
                crit = true
                bonus_dmg = bonus_dmg + base_dmg * te_mrand(3, 6) - base_dmg
                if attacker.session then
                    ctx:send_to(attacker, "{bright_white}\n당신은 " ..
                        defender.name .. "의 급소를 맞혔습니다.{reset}")
                end
                ctx:send_room(attacker.name .. "이(가) " ..
                    defender.name .. "의 급소를 맞혔습니다.")
            elseif weapon and not obj_has_flag(weapon, OCURSE) then
                -- Weapon drop chance: (5-p)/300 (command5.c:333-345)
                if te_mrand(1, 300) <= (5 - p) and (5 - p) > 0 then
                    if attacker.session then
                        ctx:send_to(attacker, "{bright_white}\n당신은 쥐고 있는 무기를 놓았습니다{reset}")
                    end
                    ctx:send_room(attacker.name .. "이(가) 쥐고 있는 무기를 놓았습니다.")
                    base_dmg = 0
                    bonus_dmg = 0
                    -- Unequip weapon (back to inventory) + recompute
                    unequip_weapon(attacker)
                    weapon = nil
                end
            end

            -- Weapon durability: 25% chance per hit (command5.c:370-371)
            if weapon then
                local ok, shots = pcall(function() return weapon.shots_remaining end)
                if ok and shots then
                    if te_mrand(0, 3) == 0 then
                        pcall(function() weapon.shots_remaining = shots - 1 end)
                    end
                end
            end

            -- Shadow attack (command5.c:373-400): only on first hit
            local shadow_total = 0
            if j == 1 and not attacker.is_npc then
                -- Check for shadow attack equipment flag (OSHADO = 50)
                local has_shadow = false
                local ok_eq, equip = pcall(function() return attacker.equipment end)
                if ok_eq and equip then
                    -- Check each equipment slot for OSHADO
                    for slot = 0, 20 do
                        local ok_s, item = pcall(function() return equip[slot] end)
                        if ok_s and item and obj_has_flag(item, OSHADO) then
                            has_shadow = true
                            break
                        end
                    end
                end
                if has_shadow then
                    -- Shadow critical
                    local shadow_crit = false
                    if te_mrand(1, 100) <= p or (weapon and obj_has_flag(weapon, OALCRT)) then
                        shadow_crit = true
                        shadow_dmg = shadow_dmg + shadow_dmg * te_mrand(3, 6) - shadow_dmg
                        if attacker.session then
                            ctx:send_to(attacker, "{green}\n당신의 그림자가 " ..
                                defender.name .. "의 급소를 맞혔습니다.{reset}")
                        end
                    end
                    if attacker.session then
                        ctx:send_to(attacker, "\n당신의 그림자가 " ..
                            defender.name .. "을(를) {yellow}" .. shadow_dmg ..
                            "{reset} 의 타격을 합니다.")
                    end
                    shadow_total = shadow_dmg
                end
            end

            -- Total damage
            local total_dmg = base_dmg + bonus_dmg + shadow_total
            total_dmg = math.max(1, total_dmg)

            -- Apply damage
            defender.hp = defender.hp - total_dmg

            -- Output messages (original format)
            local msg_text, msg_color = damage_msg(total_dmg)
            if attacker.session then
                if weapon then
                    ctx:send_to(attacker, "\n당신은 " .. (weapon.name or "무기") ..
                        "으로 " .. defender.name .. "에게 {bright_cyan}" ..
                        total_dmg .. "{reset} 의 타격을 합니다.")
                else
                    ctx:send_to(attacker, "\n당신은 맨주먹으로 " .. defender.name ..
                        "에게 {bright_cyan}" .. total_dmg .. "{reset} 의 타격을 합니다.")
                end
            end
            if defender.session then
                ctx:send_to(defender, "{red}\n" .. attacker.name ..
                    "이(가) 당신에게 {bright_cyan}" .. total_dmg ..
                    "{red} 의 타격을 합니다.{reset}")
            end

            -- Room message (to bystanders)
            ctx:send_room(attacker.name .. "이(가) " .. defender.name ..
                "에게 " .. total_dmg .. "의 타격을 합니다.")

            -- Proficiency gain (command5.c:406-414): monster only
            if not attacker.is_npc and defender.is_npc and weapon then
                local ok_exp, mon_exp = pcall(function() return defender.proto.experience end)
                if ok_exp and mon_exp and mon_exp > 0 then
                    local ok_hpmax, hpmax = pcall(function() return defender.max_hp end)
                    if ok_hpmax and hpmax and hpmax > 0 then
                        local dealt = math.min(total_dmg, math.max(0, defender.hp + total_dmg))
                        local addprof = math.floor((dealt * mon_exp) / hpmax)
                        addprof = math.min(addprof, mon_exp)
                        if addprof > 0 then
                            -- Add to proficiency via extensions
                            local ok_ext, ext = pcall(function() return attacker.extensions end)
                            if ok_ext and ext then
                                local ok_prof, prof_arr = pcall(function() return ext.proficiency end)
                                if ok_prof and prof_arr then
                                    local ok_v, cur = pcall(function() return prof_arr[weapon_type] end)
                                    if ok_v and cur then
                                        -- Direct Lua→Python attr set may not work; use pcall
                                        pcall(function()
                                            prof_arr[weapon_type] = cur + addprof
                                        end)
                                    end
                                end
                            end
                        end
                    end
                end
            end

            -- HP status display
            if attacker.session and not player_has_flag(attacker, PNOHPGRAPH) then
                ctx:send_to(attacker, " ({bright_cyan}" ..
                    math.max(0, defender.hp) .. "{reset}/" .. (defender.max_hp or 1) .. ")")
            end

            -- Death check
            if defender.hp <= 0 then
                ctx:send_room("<< " .. defender.name .. "이(가) 죽었습니다 >>")
                ctx:stop_combat(attacker)
                ctx:defer_death(defender, attacker)
                return
            end

            -- Check for flee (MFLEER NPC: HP < 20%)
            if defender.is_npc and mob_has_flag(defender, MFLEER) then
                if defender.hp < math.floor(defender.max_hp * 0.2) then
                    -- DEX check: defender.dex > attacker.dex → 30% skip (update.c:941)
                    local def_dex = te_stat(defender, "dex", 13)
                    local att_dex = te_stat(attacker, "dex", 13)
                    local flee_ok = true
                    if def_dex > att_dex and te_mrand(1, 10) < 4 then
                        flee_ok = false
                    end
                    if flee_ok then
                        local room = nil
                        pcall(function()
                            room = ctx._engine.world.rooms[defender.room_vnum]
                        end)
                        if room and room.proto and room.proto.exits then
                            for _, ex in ipairs(room.proto.exits) do
                                if ex.to_vnum and ex.to_vnum > 0 then
                                    ctx:stop_combat(attacker)
                                    ctx:send_room(defender.name .. "이(가) 도주합니다!")
                                    if attacker.session then
                                        ctx:send_to(attacker, defender.name .. "이(가) 도주합니다!")
                                    end
                                    pcall(function()
                                        ctx:move_char(defender, ex.to_vnum)
                                    end)
                                    return
                                end
                            end
                        end
                    end
                end
            end
        else
            -- ── MISS ──
            if attacker.session then
                ctx:send_to(attacker, "\n당신은 " .. defender.name .. "을(를) 빗맞힙니다.")
            end
            if defender.session then
                ctx:send_to(defender, "\n" .. attacker.name ..
                    "이(가) " .. defender.name .. "을(를) 빗맞힙니다.")
            end
        end
    end  -- for j=1,attacks
end)
