-- comm.lua — 3eyes communication commands

register_command("tell", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구에게 무엇을 말하시겠습니까?")
        return
    end
    local target_name, msg = args:match("^(%S+)%s+(.+)$")
    if not target_name or not msg then
        ctx:send("사용법: tell <대상> <메시지>")
        return
    end
    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("그런 사람이 접속해 있지 않습니다.")
        return
    end
    ctx:send("{magenta}[" .. target.name .. "에게] " .. msg .. "{reset}")
    ctx:send_to(target, "{magenta}[" .. ctx.char.name .. "] " .. msg .. "{reset}")
end, "귓속말")

register_command("say", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 말하시겠습니까?")
        return
    end
    ctx:send("{white}" .. ctx.char.name .. "이(가) 말합니다: '" .. args .. "'{reset}")
    ctx:send_room("{white}" .. ctx.char.name .. "이(가) 말합니다: '" .. args .. "'{reset}")
end, "말")

register_command("shout", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 외치시겠습니까?")
        return
    end
    ctx:send("{bright_yellow}[외침] " .. ctx.char.name .. ": " .. args .. "{reset}")
    ctx:send_all("{bright_yellow}[외침] " .. ctx.char.name .. ": " .. args .. "{reset}")
end, "외치")

register_command("gossip", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 방송하시겠습니까?")
        return
    end
    ctx:send("{bright_green}[방송] " .. ctx.char.name .. ": " .. args .. "{reset}")
    ctx:send_all("{bright_green}[방송] " .. ctx.char.name .. ": " .. args .. "{reset}")
end, "방송")

register_command("emote", function(ctx, args)
    if not args or args == "" then
        ctx:send("어떤 행동을 하시겠습니까?")
        return
    end
    ctx:send(ctx.char.name .. " " .. args)
    ctx:send_room(ctx.char.name .. " " .. args)
end, "행동")

register_command("follow", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 따라가시겠습니까?")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end
    if target == ctx.char then
        ctx:stop_following()
        ctx:send("혼자 다닙니다.")
        return
    end
    ctx:follow(target)
    ctx:send(target.name .. "을(를) 따라갑니다.")
end, "따라가")

register_command("group", function(ctx, args)
    local members = ctx:get_group_members()
    if not members or #members == 0 then
        ctx:send("그룹에 속해 있지 않습니다.")
        return
    end
    local lines = {"{bright_cyan}-- 그룹원 --{reset}"}
    for _, m in ipairs(members) do
        lines[#lines + 1] = string.format("  %s (레벨 %d, HP %d/%d)",
            m.name, m.level, m.hp, m.max_hp)
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "그룹")
