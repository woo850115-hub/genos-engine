-- sigma.lua — 10woongi sigma combat system
-- Dual HP+SP damage, hit chance based on spirit/agility
-- Registers combat_round hook

local function calc_hit_chance(ctx, attacker, defender)
    local atk_stats = get_wuxia_stats(attacker)
    local def_stats = get_wuxia_stats(defender)

    local base = 50 + (attacker.hitroll or 0)
    local spirit_bonus = math.floor(atk_stats.spirit / 2)
    local agi_penalty = math.floor(def_stats.agility / 3)

    return math.max(5, math.min(95, base + spirit_bonus - agi_penalty))
end

local function calc_hp_damage(ctx, attacker, defender)
    local atk_stats = get_wuxia_stats(attacker)

    local base = 0
    if attacker.proto and attacker.proto.damage_dice then
        base = roll_dice_str(ctx, attacker.proto.damage_dice)
    else
        base = ctx:random(1, 4) + (attacker.damroll or 0)
    end

    local stamina_bonus = math.floor(atk_stats.stamina / 5)
    return math.max(1, base + stamina_bonus + (attacker.damroll or 0))
end

local function calc_sp_damage(ctx, attacker, defender)
    local atk_stats = get_wuxia_stats(attacker)
    local inner_bonus = math.floor(atk_stats.inner / 4)
    local base = ctx:random(1, 3) + inner_bonus
    return math.max(0, base)
end

-- ── Combat round hook ─────────────────────────────────────────

register_hook("combat_round", function(ctx, attacker, defender)
    attacker.position = 7  -- POS_FIGHTING

    local hit_chance = calc_hit_chance(ctx, attacker, defender)
    local roll = ctx:random(1, 100)

    if roll > hit_chance then
        -- Miss
        ctx:send_to(attacker,
            "{yellow}" .. defender.name .. "에 대한 공격이 빗나갔습니다.{reset}")
        if defender.session then
            ctx:send_to(defender,
                "\r\n{yellow}" .. attacker.name .. "의 공격이 빗나갔습니다.{reset}")
        end
        return
    end

    -- Hit
    local hp_dmg = calc_hp_damage(ctx, attacker, defender)
    local sp_dmg = calc_sp_damage(ctx, attacker, defender)

    defender.hp = defender.hp - hp_dmg

    -- SP damage (move = SP in 10woongi)
    local current_sp = defender.move or 0
    defender.move = math.max(0, current_sp - sp_dmg)

    -- Messages
    local atk_msg = "{red}" .. defender.name .. "에게 " .. hp_dmg .. " 데미지를 입혔습니다."
    if sp_dmg > 0 then
        atk_msg = atk_msg .. " (내공 -" .. sp_dmg .. ")"
    end
    atk_msg = atk_msg .. "{reset}"
    ctx:send_to(attacker, atk_msg)

    if defender.session then
        local def_msg = "\r\n{red}" .. attacker.name .. "이(가) 당신에게 " .. hp_dmg .. " 데미지를 입혔습니다."
        if sp_dmg > 0 then
            def_msg = def_msg .. " (내공 -" .. sp_dmg .. ")"
        end
        def_msg = def_msg .. "{reset}"
        ctx:send_to(defender, def_msg)
    end

    -- Check death
    if defender.hp <= 0 then
        ctx:stop_combat(attacker)
        ctx:defer_death(defender, attacker)
    end
end)
