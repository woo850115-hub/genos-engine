-- doors.lua — open, close, lock, unlock

register_command("open", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 여시겠습니까?")
        return
    end

    local direction = ctx:find_door(args)
    if direction < 0 or not ctx:has_door(direction) then
        ctx:send("그런 것을 찾을 수 없습니다.")
        return
    end
    if not ctx:is_door_closed(direction) then
        ctx:send("이미 열려 있습니다.")
        return
    end
    if ctx:is_door_locked(direction) then
        ctx:send("잠겨 있습니다.")
        return
    end

    ctx:set_door_state(direction, false)
    ctx:send("문을 열었습니다.")

    -- Notify other side
    local room = ctx:get_room()
    local exits = ctx:get_exits()
    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction == direction then
            local other_room = ctx:get_room(ex.to_room)
            if other_room then
                local chars = ctx:get_characters(other_room)
                for j = 1, #chars do
                    if chars[j].session then
                        ctx:send_to(chars[j], "\r\n문이 열렸습니다.")
                    end
                end
            end
            break
        end
    end
end, "열")

register_command("close", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 닫으시겠습니까?")
        return
    end

    local direction = ctx:find_door(args)
    if direction < 0 or not ctx:has_door(direction) then
        ctx:send("그런 것을 찾을 수 없습니다.")
        return
    end
    if ctx:is_door_closed(direction) then
        ctx:send("이미 닫혀 있습니다.")
        return
    end

    ctx:set_door_state(direction, true)
    ctx:send("문을 닫았습니다.")
end, "닫")

register_command("lock", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 잠그시겠습니까?")
        return
    end

    local direction = ctx:find_door(args)
    if direction < 0 or not ctx:has_door(direction) then
        ctx:send("그런 것을 찾을 수 없습니다.")
        return
    end
    if not ctx:is_door_closed(direction) then
        ctx:send("먼저 닫아야 합니다.")
        return
    end
    if ctx:is_door_locked(direction) then
        ctx:send("이미 잠겨 있습니다.")
        return
    end
    if not ctx:has_key(direction) then
        ctx:send("열쇠가 없습니다.")
        return
    end

    ctx:set_door_state(direction, true, true)
    ctx:send("문을 잠갔습니다.")
end, "잠가")

register_command("unlock", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 여시겠습니까?")
        return
    end

    local direction = ctx:find_door(args)
    if direction < 0 or not ctx:has_door(direction) then
        ctx:send("그런 것을 찾을 수 없습니다.")
        return
    end
    if not ctx:is_door_locked(direction) then
        ctx:send("잠겨 있지 않습니다.")
        return
    end
    if not ctx:has_key(direction) then
        ctx:send("열쇠가 없습니다.")
        return
    end

    ctx:set_door_state(direction, true, false)
    ctx:send("자물쇠를 열었습니다.")
end, "풀")
