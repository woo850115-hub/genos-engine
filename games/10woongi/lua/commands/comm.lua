-- comm.lua — 10woongi communication commands (tell, shout, whisper)

register_command("tell", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구에게 무엇을 말하시겠습니까?")
        return
    end
    local target_name, message = args:match("^(%S+)%s+(.+)$")
    if not target_name or not message then
        ctx:send("무엇을 말하시겠습니까?")
        return
    end

    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end

    ctx:send("{magenta}" .. target_name .. "에게 귓속말: '" .. message .. "'{reset}")
    ctx:send_to(target, "\r\n{magenta}" .. ctx.char.name .. "이(가) 귓속말합니다: '" .. message .. "'{reset}")
end, "귓")

register_command("shout", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 외치시겠습니까?")
        return
    end
    local ch = ctx.char
    ctx:send("{yellow}당신이 외칩니다: '" .. args .. "'{reset}")
    ctx:send_all("\r\n{yellow}" .. ch.name .. "이(가) 외칩니다: '" .. args .. "'{reset}")
end, "외치")

register_command("whisper", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구에게 무엇을 속삭이시겠습니까?")
        return
    end
    local target_name, message = args:match("^(%S+)%s+(.+)$")
    if not target_name or not message then
        ctx:send("무엇을 속삭이시겠습니까?")
        return
    end

    local target = ctx:find_char(target_name)
    if not target or not target.session then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end

    ctx:send("{magenta}" .. target.name .. "에게 속삭입니다: '" .. message .. "'{reset}")
    ctx:send_to(target, "\r\n{magenta}" .. ctx.char.name .. "이(가) 속삭입니다: '" .. message .. "'{reset}")
end, "속삭이")
