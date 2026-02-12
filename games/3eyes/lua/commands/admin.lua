-- admin.lua — 3eyes admin commands

register_command("goto", function(ctx, args)
    if not args or args == "" then
        ctx:send("어디로 가시겠습니까? (방 번호)")
        return
    end
    if ctx.char.level < 200 then
        ctx:send("관리자 전용 명령어입니다.")
        return
    end
    local vnum = tonumber(args)
    if not vnum then
        ctx:send("방 번호를 입력해주세요.")
        return
    end
    local ok = ctx:teleport_to(vnum)
    if ok then
        ctx:send("{bright_cyan}" .. vnum .. "번 방으로 이동합니다.{reset}")
        ctx:defer_look()
    else
        ctx:send("그런 방이 존재하지 않습니다.")
    end
end, nil)

register_command("load", function(ctx, args)
    if ctx.char.level < 200 then
        ctx:send("관리자 전용 명령어입니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: load mob|obj <vnum>")
        return
    end
    local kind, vnum_str = args:match("^(%S+)%s+(%d+)$")
    if not kind or not vnum_str then
        ctx:send("사용법: load mob|obj <vnum>")
        return
    end
    local vnum = tonumber(vnum_str)
    if kind == "mob" or kind == "몬스터" then
        local mob = ctx:load_mob(vnum)
        if mob then
            ctx:send("{green}" .. mob.name .. "을(를) 소환했습니다.{reset}")
        else
            ctx:send("그런 몬스터가 없습니다.")
        end
    elseif kind == "obj" or kind == "아이템" then
        local obj = ctx:load_obj(vnum)
        if obj then
            ctx:send("{green}" .. obj.name .. "을(를) 생성했습니다.{reset}")
        else
            ctx:send("그런 아이템이 없습니다.")
        end
    else
        ctx:send("사용법: load mob|obj <vnum>")
    end
end, nil)

register_command("purge", function(ctx, args)
    if ctx.char.level < 200 then
        ctx:send("관리자 전용 명령어입니다.")
        return
    end
    ctx:purge_room()
    ctx:send("{yellow}방을 정리했습니다.{reset}")
end, nil)

register_command("restore", function(ctx, args)
    if ctx.char.level < 200 then
        ctx:send("관리자 전용 명령어입니다.")
        return
    end
    local target = ctx.char
    if args and args ~= "" then
        target = ctx:find_char(args)
        if not target then
            ctx:send("그런 대상을 찾을 수 없습니다.")
            return
        end
    end
    target.hp = target.max_hp
    target.mana = target.max_mana
    target.move = target.max_move
    ctx:send("{bright_green}" .. target.name .. "을(를) 완전 회복시켰습니다.{reset}")
end, nil)

register_command("advance", function(ctx, args)
    if ctx.char.level < 200 then
        ctx:send("관리자 전용 명령어입니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: advance <대상> <레벨>")
        return
    end
    local target_name, level_str = args:match("^(%S+)%s+(%d+)$")
    if not target_name or not level_str then
        ctx:send("사용법: advance <대상> <레벨>")
        return
    end
    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    local new_level = tonumber(level_str)
    target.level = new_level
    ctx:send("{bright_yellow}" .. target.name .. "의 레벨을 " .. new_level .. "로 설정했습니다.{reset}")
end, nil)

register_command("shutdown", function(ctx, args)
    if ctx.char.level < 200 then
        ctx:send("관리자 전용 명령어입니다.")
        return
    end
    ctx:send_all("{bright_red}[시스템] 서버가 곧 종료됩니다...{reset}")
    ctx:shutdown()
end, nil)

register_command("reload", function(ctx, args)
    if ctx.char.level < 200 then
        ctx:send("관리자 전용 명령어입니다.")
        return
    end
    ctx:reload_lua()
    ctx:send("{bright_green}Lua 스크립트를 다시 불러왔습니다.{reset}")
end, nil)
