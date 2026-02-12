-- skills.lua — tbaMUD class skills: backstab, bash, kick, rescue
-- Registers as commands, not hooks.

-- ── backstab (Thief, class_id=2) ────────────────────────────────

local function do_backstab(ctx, args)
    local char = ctx.char
    if not char then return end

    -- Must be thief (class_id 2)
    if char.class_id ~= 2 then
        ctx:send("{red}뒤치기는 도적만 사용할 수 있습니다.{reset}")
        return
    end

    -- Cannot backstab while fighting
    if char.fighting then
        ctx:send("{red}전투 중에는 뒤치기를 할 수 없습니다!{reset}")
        return
    end

    if not args or args == "" then
        ctx:send("누구를 뒤치기 하시겠습니까?")
        return
    end

    local victim = ctx:find_char(args)
    if not victim then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end

    -- Must have a piercing weapon (dagger)
    local wield = nil
    local equip = char.equipment
    -- Check common wield slot names
    for slot, obj in pairs(equip) do
        local st = tostring(slot)
        if st == "16" or st == "wield" or st == "13" then
            wield = obj
            break
        end
    end

    if not wield then
        ctx:send("{red}뒤치기를 하려면 무기를 들어야 합니다.{reset}")
        return
    end

    -- Skill check: success = level * 2 + random
    local skill = ctx:random(1, 101)
    local chance = math.min(95, char.player_level * 3 + 10)

    if skill > chance then
        -- Miss
        ctx:send("{yellow}뒤치기에 실패했습니다!{reset}")
        ctx:send_room(char.name .. "이(가) 뒤치기에 실패합니다!")
        ctx:start_combat(victim)
        return
    end

    -- Hit! Multiplier based on level
    local mult = 2
    if char.player_level >= 10 then mult = 3 end
    if char.player_level >= 20 then mult = 4 end
    if char.player_level >= 30 then mult = 5 end

    local base_dam = ctx:roll_dice(char.proto.damage_dice)
    local damage = base_dam * mult + char.damroll

    ctx:send("{bright_yellow}뒤에서 " .. victim.name .. "을(를) 기습합니다! [" .. damage .. " 데미지]{reset}")
    ctx:send_to(victim, "{red}" .. char.name .. "이(가) 뒤에서 기습합니다! [" .. damage .. " 데미지]{reset}")
    ctx:send_room(char.name .. "이(가) " .. victim.name .. "을(를) 뒤에서 기습합니다!")

    ctx:deal_damage(victim, damage)
    ctx:start_combat(victim)

    if victim.hp <= 0 then
        ctx:defer_death(victim, char)
    end
end

register_command("backstab", do_backstab, "뒤치기")

-- ── bash (Warrior, class_id=3) ──────────────────────────────────

local function do_bash(ctx, args)
    local char = ctx.char
    if not char then return end

    if char.class_id ~= 3 then
        ctx:send("{red}밀치기는 전사만 사용할 수 있습니다.{reset}")
        return
    end

    local victim = nil
    if args and args ~= "" then
        victim = ctx:find_char(args)
    elseif char.fighting then
        victim = char.fighting
    end

    if not victim then
        ctx:send("누구를 밀치시겠습니까?")
        return
    end

    local skill = ctx:random(1, 101)
    local chance = math.min(90, char.player_level * 2 + 20)

    if skill > chance then
        -- Fail: basher falls
        ctx:send("{yellow}밀치기에 실패하여 넘어졌습니다!{reset}")
        ctx:send_room(char.name .. "이(가) 밀치기에 실패하여 넘어집니다!")
        char.position = 6  -- POS_SITTING
        ctx:start_combat(victim)
        return
    end

    -- Success: victim sits
    local damage = ctx:random(1, char.player_level)
    ctx:send("{bright_cyan}" .. victim.name .. "을(를) 밀쳐 넘어뜨렸습니다! [" .. damage .. " 데미지]{reset}")
    ctx:send_to(victim, "{red}" .. char.name .. "이(가) 밀쳐서 넘어졌습니다! [" .. damage .. " 데미지]{reset}")
    ctx:send_room(char.name .. "이(가) " .. victim.name .. "을(를) 밀쳐 넘어뜨립니다!")

    victim.position = 6  -- POS_SITTING
    ctx:deal_damage(victim, damage)
    ctx:start_combat(victim)

    if victim.hp <= 0 then
        ctx:defer_death(victim, char)
    end
end

register_command("bash", do_bash, "밀치기")

-- ── kick (Warrior, class_id=3) ──────────────────────────────────

local function do_kick(ctx, args)
    local char = ctx.char
    if not char then return end

    if char.class_id ~= 3 then
        ctx:send("{red}차기는 전사만 사용할 수 있습니다.{reset}")
        return
    end

    local victim = nil
    if args and args ~= "" then
        victim = ctx:find_char(args)
    elseif char.fighting then
        victim = char.fighting
    end

    if not victim then
        ctx:send("누구를 차시겠습니까?")
        return
    end

    local skill = ctx:random(1, 101)
    local chance = math.min(85, char.player_level * 2 + 30)

    if skill > chance then
        ctx:send("{yellow}차기에 실패했습니다!{reset}")
        ctx:start_combat(victim)
        return
    end

    local damage = ctx:random(1, char.player_level) + char.damroll
    ctx:send("{bright_red}" .. victim.name .. "을(를) 걷어찼습니다! [" .. damage .. " 데미지]{reset}")
    ctx:send_to(victim, "{red}" .. char.name .. "이(가) 걷어찹니다! [" .. damage .. " 데미지]{reset}")
    ctx:send_room(char.name .. "이(가) " .. victim.name .. "을(를) 걷어찹니다!")

    ctx:deal_damage(victim, damage)
    ctx:start_combat(victim)

    if victim.hp <= 0 then
        ctx:defer_death(victim, char)
    end
end

register_command("kick", do_kick, "차기")

-- ── rescue (Warrior, class_id=3) ────────────────────────────────

local function do_rescue(ctx, args)
    local char = ctx.char
    if not char then return end

    if char.class_id ~= 3 then
        ctx:send("{red}구출은 전사만 사용할 수 있습니다.{reset}")
        return
    end

    if not args or args == "" then
        ctx:send("누구를 구출하시겠습니까?")
        return
    end

    local ally = ctx:find_char(args)
    if not ally then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end

    if not ally.fighting then
        ctx:send(ally.name .. "은(는) 전투 중이 아닙니다.")
        return
    end

    local enemy = ally.fighting

    local skill = ctx:random(1, 101)
    local chance = math.min(90, char.player_level * 2 + 20)

    if skill > chance then
        ctx:send("{yellow}구출에 실패했습니다!{reset}")
        return
    end

    -- Redirect enemy to attacker
    ctx:send("{bright_white}" .. ally.name .. "을(를) 구출합니다!{reset}")
    ctx:send_to(ally, "{bright_white}" .. char.name .. "이(가) 구출해줍니다!{reset}")
    ctx:send_room(char.name .. "이(가) " .. ally.name .. "을(를) 구출합니다!")

    -- Swap fighting targets
    enemy.fighting = char
    char.fighting = enemy
    char.position = 7  -- POS_FIGHTING
    ally.fighting = nil
    ally.position = 8  -- POS_STANDING
end

register_command("rescue", do_rescue, "구출")
