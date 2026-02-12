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
    -- Store for reply
    if target.session then
        ctx:set_player_data_on(target, "last_tell_from", ch.player_name or ch.name)
    end
end, "귓말")

-- ── reply ────────────────────────────────────────────────────
register_command("reply", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇이라고 답하시겠습니까?")
        return
    end
    local last_tell = ctx:get_player_data("last_tell_from")
    if not last_tell or last_tell == "" then
        ctx:send("답장할 대상이 없습니다.")
        return
    end
    ctx:call_command("tell", last_tell .. " " .. args)
end, "답")

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

-- ── auction ───────────────────────────────────────────────────
register_command("auction", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 경매하시겠습니까?")
        return
    end
    local ch = ctx.char
    if not ch then return end
    ctx:send("{bright_yellow}[경매] 당신: " .. args .. "{reset}")
    ctx:send_all("\r\n{bright_yellow}[경매] " .. ch.name .. ": " .. args .. "{reset}")
end, "경매")

-- ── grats ─────────────────────────────────────────────────────
register_command("grats", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 축하하시겠습니까?")
        return
    end
    local ch = ctx.char
    if not ch then return end
    ctx:send("{green}[축하] 당신: " .. args .. "{reset}")
    ctx:send_all("\r\n{green}[축하] " .. ch.name .. ": " .. args .. "{reset}")
end, "축하")

-- ── emote ────────────────────────────────────────────────────
register_command("emote", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 하시겠습니까?")
        return
    end
    ctx:send(ch.name .. " " .. args)
    ctx:send_room(ch.name .. " " .. args)
end, "행동")

-- ── split ────────────────────────────────────────────────────
register_command("split", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("사용법: split <금액>")
        return
    end
    local amount = tonumber(args)
    if not amount or amount <= 0 then
        ctx:send("0보다 큰 금액을 입력하세요.")
        return
    end
    amount = math.floor(amount)
    if ch.gold < amount then
        ctx:send("그만큼의 골드가 없습니다.")
        return
    end

    -- Count group members in same room
    local room = ctx:get_room()
    if not room then return end
    local members = {ch}
    local chars = ctx:get_characters()
    for i = 1, #chars do
        local mob = chars[i]
        if mob ~= ch and not mob.is_npc and mob.session then
            -- Check if following leader or in same group
            table.insert(members, mob)
        end
    end

    if #members <= 1 then
        ctx:send("같은 방에 나눌 대상이 없습니다.")
        return
    end

    local share = math.floor(amount / #members)
    local remainder = amount - (share * #members)

    ch.gold = ch.gold - amount + share + remainder
    ctx:send(amount .. " 골드를 " .. #members .. "명에게 나눕니다. (1인당 " .. share .. " 골드)")
    for i = 2, #members do
        local member = members[i]
        member.gold = member.gold + share
        if member.session then
            ctx:send_to(member, "\r\n" .. ch.name .. "이(가) " .. share .. " 골드를 나눠줍니다.")
        end
    end
end, "분배")

-- ── assist ───────────────────────────────────────────────────
register_command("assist", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.fighting then
        ctx:send("이미 전투 중입니다!")
        return
    end
    if not args or args == "" then
        ctx:send("누구를 도와드릴까요?")
        return
    end

    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    if not target.fighting then
        ctx:send(target.name .. "은(는) 전투 중이 아닙니다.")
        return
    end

    local enemy = target.fighting
    ctx:send("{red}" .. target.name .. "을(를) 도와 " .. enemy.name .. "을(를) 공격합니다!{reset}")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "을(를) 도와 전투에 합류합니다!")
    if target.session then
        ctx:send_to(target, "\r\n{green}" .. ch.name .. "이(가) 당신을 도와줍니다!{reset}")
    end
    ctx:start_combat(enemy)
end, "도와")

-- ── gossip (global channel) ─────────────────────────────────────

register_command("gossip", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 알리시겠습니까?")
        return
    end
    ctx:send("{bright_magenta}[잡담] 당신: " .. args .. "{reset}")
    local players = ctx:get_players()
    for i = 1, #players do
        local p = players[i]
        if p ~= ch and p.session then
            ctx:send_to(p, "\r\n{bright_magenta}[잡담] " .. ch.name .. ": " .. args .. "{reset}")
        end
    end
end, "잡담")

-- ── follow ──────────────────────────────────────────────────────

register_command("follow", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("누구를 따라가시겠습니까?")
        return
    end
    local target_name = args:lower()
    if target_name == "self" or target_name == "본인" or target_name == ch.name:lower() then
        local following = ctx:get_following()
        if following then
            ctx:unfollow()
            ctx:send("더 이상 따라가지 않습니다.")
        else
            ctx:send("아무도 따라가고 있지 않습니다.")
        end
        return
    end

    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end
    ctx:follow(target)
    ctx:send(target.name .. "을(를) 따라갑니다.")
    if target.session then
        ctx:send_to(target, "\r\n" .. ch.name .. "이(가) 당신을 따라갑니다.")
    end
end, "따라가")

-- ── group ───────────────────────────────────────────────────────

register_command("group", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local followers = ctx:get_followers()
    if #followers == 0 then
        ctx:send("그룹 멤버가 없습니다.")
        return
    end
    ctx:send("{bright_cyan}--- 그룹 ---{reset}")
    ctx:send("  [리더] " .. ch.name .. " HP:" .. ch.hp .. "/" .. ch.max_hp)
    for i = 1, #followers do
        local f = followers[i]
        ctx:send("  " .. f.name .. " HP:" .. f.hp .. "/" .. f.max_hp)
    end
end, "그룹")
