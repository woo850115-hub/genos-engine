-- combat_core.lua — kill, flee (generic stubs)
-- Game-specific combat scripts override these with proper THAC0/sigma systems.

register_command("kill", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("누구를 공격하시겠습니까?")
        return
    end

    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    if not target.is_npc then
        ctx:send("다른 플레이어를 공격할 수 없습니다.")
        return
    end

    ctx:send("{red}" .. target.name .. "을(를) 공격합니다!{reset}")
    ctx:start_combat(target)
end, "죽이")

register_command("attack", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("누구를 공격하시겠습니까?")
        return
    end

    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    if not target.is_npc then
        ctx:send("다른 플레이어를 공격할 수 없습니다.")
        return
    end

    ctx:send("{red}" .. target.name .. "을(를) 공격합니다!{reset}")
    ctx:start_combat(target)
end, "공격")

register_command("flee", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not ch.fighting then
        ctx:send("전투 중이 아닙니다.")
        return
    end

    -- Skill-based success rate: base 40% + level bonus + class bonus
    local chance = 40 + math.min(ch.level, 30)
    if ch.class_id == 2 then  -- Thief: flee expert
        chance = chance + 25
    elseif ch.class_id == 3 then  -- Warrior: harder to flee (heavy armor)
        chance = chance - 10
    end
    chance = math.max(10, math.min(chance, 95))

    local roll = ctx:random(1, 100)
    if roll > chance then
        -- Failed flee: opponent gets a free hit
        ctx:send("{red}도망치려 했지만 실패했습니다!{reset}")
        local enemy = ch.fighting
        if enemy and enemy.hp > 0 then
            -- Free attack damage (simplified: level-based)
            local free_dmg = ctx:random(1, math.max(1, math.floor(enemy.level / 2)))
            ch.hp = ch.hp - free_dmg
            ctx:send("{red}" .. enemy.name .. "이(가) 도망치는 당신을 공격합니다! [" .. free_dmg .. "]{reset}")
            if enemy.session then
                ctx:send_to(enemy, "{yellow}" .. ch.name .. "이(가) 도망치려다 실패합니다!{reset}")
            end
        end
        return
    end

    -- Try a random direction
    local exits = ctx:get_exits()
    if #exits == 0 then
        ctx:send("도망칠 곳이 없습니다!")
        return
    end

    -- Try up to 3 random exits
    for attempt = 1, math.min(3, #exits) do
        local idx = ctx:random(1, #exits)
        local ex = exits[idx]
        local room = ctx:get_room()
        if room and ex.to_room >= 0 and not room:is_door_closed(ex.direction) then
            -- Exp penalty for fleeing (1% of level^2 * 10)
            local exp_loss = math.floor(ch.level * ch.level)
            if exp_loss > 0 and not ch.is_npc then
                ch.experience = math.max(0, ch.experience - exp_loss)
                ctx:send("{yellow}" .. exp_loss .. " 경험치를 잃었습니다!{reset}")
            end
            ctx:stop_combat(ch)
            ctx:send("{yellow}도망칩니다!{reset}")
            ctx:move_to(ex.to_room)
            ctx:defer_look()
            return
        end
    end

    ctx:send("도망칠 곳이 없습니다!")
end, "떠나")
