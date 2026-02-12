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

    -- Try a random direction
    local exits = ctx:get_exits()
    if #exits == 0 then
        ctx:send("도망칠 곳이 없습니다!")
        return
    end

    -- Pick random exit
    local idx = ctx:random(1, #exits)
    local ex = exits[idx]
    local room = ctx:get_room()
    if room and ex.to_room >= 0 and not room:is_door_closed(ex.direction) then
        ctx:stop_combat(ch)
        ctx:send("{yellow}도망칩니다!{reset}")
        ctx:move_to(ex.to_room)
        ctx:defer_look()
        return
    end

    ctx:send("도망칠 곳이 없습니다!")
end, "떠나")
