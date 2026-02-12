-- movement.lua — tbaMUD extended movement commands

register_command("enter", function(ctx, args)
    if not args or args == "" then
        ctx:send("어디로 들어가시겠습니까?")
        return
    end
    ctx:send("구현 예정입니다.")
end, "들어가")

register_command("leave", function(ctx, args)
    ctx:send("구현 예정입니다.")
end, "나와")

register_command("follow", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 따라가시겠습니까?")
        return
    end
    ctx:send("구현 예정입니다.")
end, "따라가")

register_command("group", function(ctx, args)
    if not args or args == "" then
        ctx:send("파티원이 없습니다.")
        return
    end
    ctx:send("구현 예정입니다.")
end, "무리")
