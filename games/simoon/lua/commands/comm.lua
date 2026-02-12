-- comm.lua — Simoon communication commands

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

register_command("gossip", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 잡담하시겠습니까?")
        return
    end
    local ch = ctx.char
    ctx:send("{yellow}[잡담] 당신: " .. args .. "{reset}")
    local players = ctx:get_players()
    if players then
        for i = 0, 200 do
            local ok, p = pcall(function() return players[i] end)
            if not ok or not p then break end
            if p ~= ctx.session then
                ctx:send_to_session(p, "\r\n{yellow}[잡담] " .. ch.name .. ": " .. args .. "{reset}")
            end
        end
    end
end, "잡담")

register_command("emote", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 표현하시겠습니까?")
        return
    end
    local ch = ctx.char
    ctx:send_room(ch.name .. " " .. args)
end, "표현")

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

register_command("follow", function(ctx, args)
    if not args or args == "" then
        local following = ctx:get_following()
        if following then
            ctx:unfollow()
            ctx:send("더 이상 아무도 따라가지 않습니다.")
        else
            ctx:send("누구를 따라가시겠습니까?")
        end
        return
    end
    if args == "self" or args == "나" then
        ctx:unfollow()
        ctx:send("더 이상 아무도 따라가지 않습니다.")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end
    if target == ctx.char then
        ctx:unfollow()
        ctx:send("더 이상 아무도 따라가지 않습니다.")
        return
    end
    ctx:follow(target)
    ctx:send(target.name .. "을(를) 따라갑니다.")
end, "따라가")

register_command("group", function(ctx, args)
    local ch = ctx.char
    local followers = ctx:get_followers()
    local lines = {"{cyan}[ " .. ch.name .. "의 그룹 ]{reset}"}
    table.insert(lines, "  " .. ch.name ..
        " — HP:" .. ch.hp .. "/" .. ch.max_hp ..
        " MN:" .. ch.mana .. "/" .. ch.max_mana ..
        " MV:" .. (ch.move or 0) .. "/" .. (ch.max_move or 0))
    if followers then
        for i = 0, 50 do
            local ok, f = pcall(function() return followers[i] end)
            if not ok or not f then break end
            table.insert(lines, "  " .. f.name ..
                " — HP:" .. f.hp .. "/" .. f.max_hp ..
                " MN:" .. f.mana .. "/" .. f.max_mana ..
                " MV:" .. (f.move or 0) .. "/" .. (f.max_move or 0))
        end
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "그룹")
