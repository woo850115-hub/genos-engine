-- admin.lua — Simoon admin commands (goto, load, purge, stat, set, etc.)

register_command("goto", function(ctx, args)
    if not args or args == "" then
        ctx:send("어디로 이동하시겠습니까? (방 번호)")
        return
    end
    local vnum = tonumber(args)
    if not vnum then
        ctx:send("방 번호를 입력해주세요.")
        return
    end
    if not ctx:room_exists(vnum) then
        ctx:send("그런 방은 존재하지 않습니다.")
        return
    end
    ctx:move_to(vnum)
    ctx:send("{cyan}순간이동!{reset}")
    ctx:defer_look()
end, nil)

register_command("load", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: load mob <vnum> / load obj <vnum>")
        return
    end
    local kind, vnum_str = args:match("^(%S+)%s+(%d+)$")
    if not kind or not vnum_str then
        ctx:send("사용법: load mob <vnum> / load obj <vnum>")
        return
    end
    local vnum = tonumber(vnum_str)
    if kind == "mob" or kind == "몬스터" then
        local mob = ctx:create_mob(vnum)
        if mob then
            ctx:send("{green}" .. mob.name .. " 생성됨.{reset}")
        else
            ctx:send("그런 몬스터는 없습니다.")
        end
    elseif kind == "obj" or kind == "물건" then
        local obj = ctx:create_obj(vnum)
        if obj then
            ctx:send("{green}" .. obj.name .. " 생성됨.{reset}")
        else
            ctx:send("그런 물건은 없습니다.")
        end
    else
        ctx:send("사용법: load mob <vnum> / load obj <vnum>")
    end
end, nil)

register_command("purge", function(ctx, args)
    if not args or args == "" then
        ctx:purge_room()
        ctx:send("{red}방의 NPC와 물건을 제거했습니다.{reset}")
        return
    end
    local target = ctx:find_char(args)
    if target and target.is_npc then
        ctx:extract_char(target)
        ctx:send("{red}" .. target.name .. " 제거됨.{reset}")
    else
        ctx:send("그런 NPC를 찾을 수 없습니다.")
    end
end, nil)

register_command("restore", function(ctx, args)
    local target
    if args and args ~= "" then
        target = ctx:find_char(args)
    else
        target = ctx.char
    end
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    target.hp = target.max_hp
    target.mana = target.max_mana
    target.move = target.max_move
    ctx:send("{bright_green}" .. target.name .. "의 체력이 회복되었습니다.{reset}")
end, nil)

register_command("advance", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: advance <이름> <레벨>")
        return
    end
    local name, level_str = args:match("^(%S+)%s+(%d+)$")
    if not name or not level_str then
        ctx:send("사용법: advance <이름> <레벨>")
        return
    end
    local target = ctx:find_player(name)
    if not target then
        ctx:send("그런 플레이어를 찾을 수 없습니다.")
        return
    end
    local new_level = tonumber(level_str)
    target.character.level = new_level
    ctx:send(target.character.name .. "의 레벨이 " .. new_level .. "로 설정되었습니다.")
end, nil)

register_command("shutdown", function(ctx, args)
    ctx:send("{bright_red}서버를 종료합니다...{reset}")
    ctx:shutdown()
end, nil)

register_command("reload", function(ctx, args)
    ctx:reload_lua()
    ctx:send("{bright_green}Lua 스크립트가 리로드되었습니다.{reset}")
end, nil)
