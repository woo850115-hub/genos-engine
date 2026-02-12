-- admin.lua — 10woongi admin commands (goto, wload, purge, stat, wset, restore, advance)

local ADMIN_LEVEL = 100

register_command("goto", function(ctx, args)
    if not ctx:is_admin() then
        ctx:send("권한이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("어디로 가시겠습니까? (goto <방번호>)")
        return
    end
    local room_vnum = tonumber(args)
    if not room_vnum then
        ctx:send("올바른 방 번호를 입력하세요.")
        return
    end
    local room = ctx:get_room(room_vnum)
    if not room then
        ctx:send("그런 방은 없습니다.")
        return
    end
    ctx:move_char_to(ctx.char, room_vnum)
    ctx:defer_look()
end)

register_command("wload", function(ctx, args)
    if not ctx:is_admin() then
        ctx:send("권한이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: wload mob <vnum> / wload obj <vnum>")
        return
    end
    local obj_type, vnum_str = args:match("^(%S+)%s+(%S+)")
    if not obj_type or not vnum_str then
        ctx:send("사용법: wload mob <vnum> / wload obj <vnum>")
        return
    end
    local vnum = tonumber(vnum_str)
    if not vnum then
        ctx:send("올바른 VNUM을 입력하세요.")
        return
    end

    obj_type = obj_type:lower()
    if obj_type == "mob" then
        local mob = ctx:create_mob(vnum, ctx.char.room_vnum)
        if mob then
            ctx:send(mob.name .. "을(를) 소환했습니다.")
        else
            ctx:send("VNUM " .. vnum .. " 몬스터를 찾을 수 없습니다.")
        end
    elseif obj_type == "obj" then
        local obj = ctx:create_obj(vnum)
        if obj then
            ctx:obj_to_room(obj, ctx.char.room_vnum)
            ctx:send(obj.name .. "을(를) 생성했습니다.")
        else
            ctx:send("VNUM " .. vnum .. " 아이템을 찾을 수 없습니다.")
        end
    else
        ctx:send("사용법: wload mob <vnum> / wload obj <vnum>")
    end
end)

register_command("purge", function(ctx, args)
    if not ctx:is_admin() then
        ctx:send("권한이 없습니다.")
        return
    end
    ctx:purge_room()
    ctx:send("방이 정화되었습니다.")
end)

register_command("stat", function(ctx, args)
    if not ctx:is_admin() then
        ctx:send("권한이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: stat <대상>")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end

    ctx:send("{cyan}━━━ " .. target.name .. " 상세 정보 ━━━{reset}")
    ctx:send("  VNUM: " .. target.proto.vnum .. "  레벨: " .. target.level)
    ctx:send("  HP: " .. target.hp .. "/" .. target.max_hp
        .. "  SP: " .. (target.move or 0) .. "/" .. (target.max_move or 0))
    ctx:send("  골드: " .. target.gold .. "  경험치: " .. target.experience)
    ctx:send("  히트롤: " .. target.hitroll .. "  댐롤: " .. target.damroll)
    ctx:send("  NPC: " .. tostring(target.is_npc))
end)

register_command("wset", function(ctx, args)
    if not ctx:is_admin() then
        ctx:send("권한이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: wset <이름> <필드> <값>")
        return
    end
    local name, field, value = args:match("^(%S+)%s+(%S+)%s+(%S+)")
    if not name or not field or not value then
        ctx:send("사용법: wset <이름> <필드> <값>")
        return
    end
    local target = ctx:find_player(name)
    if not target then
        ctx:send("그런 플레이어를 찾을 수 없습니다.")
        return
    end

    local int_val = tonumber(value)
    if not int_val then
        ctx:send("올바른 숫자를 입력하세요.")
        return
    end

    if field == "level" then
        target.player_level = int_val
    elseif field == "hp" then
        target.hp = int_val
        target.max_hp = int_val
    elseif field == "gold" then
        target.gold = int_val
    elseif field == "exp" then
        target.experience = int_val
    else
        ctx:send("알 수 없는 필드: " .. field)
        return
    end

    ctx:send(name .. "의 " .. field .. "을(를) " .. value .. "(으)로 설정했습니다.")
end)

register_command("restore", function(ctx, args)
    if not ctx:is_admin() then
        ctx:send("권한이 없습니다.")
        return
    end
    local ch = ctx.char
    if args and args ~= "" then
        local target = ctx:find_player(args)
        if target then ch = target end
    end
    ch.hp = ch.max_hp
    ch.mana = ch.max_mana
    ch.move = ch.max_move or 80
    ctx:send(ch.name .. "이(가) 완전히 회복되었습니다!")
end)

register_command("advance", function(ctx, args)
    if not ctx:is_admin() then
        ctx:send("권한이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: advance <이름> <레벨>")
        return
    end
    local name, level_str = args:match("^(%S+)%s+(%S+)")
    if not name or not level_str then
        ctx:send("사용법: advance <이름> <레벨>")
        return
    end
    local target_level = tonumber(level_str)
    if not target_level then
        ctx:send("올바른 숫자를 입력하세요.")
        return
    end
    local target = ctx:find_player(name)
    if not target then
        ctx:send("그런 플레이어를 찾을 수 없습니다.")
        return
    end
    target.player_level = target_level
    ctx:send(name .. "을(를) 레벨 " .. target_level .. "(으)로 설정했습니다.")
end)
