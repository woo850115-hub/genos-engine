-- movement.lua — 10woongi movement commands (recall)

register_command("recall", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    if ch.fighting then
        ctx:send("전투 중에는 귀환할 수 없습니다!")
        return
    end

    local start_room = ctx:get_start_room()

    -- Leave message to room
    ctx:send_room(ch.name .. "이(가) 사라졌습니다.")

    ctx:move_char_to(ch, start_room)
    ctx:send("{bright_white}몸이 가벼워지며 순간이동합니다!{reset}")
    ctx:defer_look()
end, "귀환")
