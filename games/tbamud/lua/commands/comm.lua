-- comm.lua — tbaMUD communication commands (tell, shout, whisper)

register_command("tell", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구에게 무엇을 말하시겠습니까?")
        return
    end
    local parts = split(args)
    if #parts < 2 then
        ctx:send("무엇이라고 말하시겠습니까?")
        return
    end
    local target_name = parts[1]
    local message = args:match("^%S+%s+(.+)$")
    if not message then
        ctx:send("무엇이라고 말하시겠습니까?")
        return
    end

    local target = ctx:find_player(target_name)
    if not target then
        ctx:send(target_name .. "은(는) 접속 중이 아닙니다.")
        return
    end
    local ch = ctx.char
    if not ch then return end
    ctx:send("{magenta}" .. target_name .. "에게 귓속말합니다, '" .. message .. "'{reset}")
    ctx:send_to(target, "\r\n{magenta}" .. ch.name .. "이(가) 귓속말합니다, '" .. message .. "'{reset}")
end, "귓말")

register_command("shout", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 외치시겠습니까?")
        return
    end
    local ch = ctx.char
    if not ch then return end
    ctx:send("{yellow}당신이 외칩니다, '" .. args .. "'{reset}")
    ctx:send_all("\r\n{yellow}" .. ch.name .. "이(가) 외칩니다, '" .. args .. "'{reset}")
end, "외쳐")

register_command("whisper", function(ctx, args)
    -- Whisper is same as tell
    ctx:call_command("tell", args or "")
end, "속삭여")
