-- admin.lua — tbaMUD admin commands (level >= 31)

local MIN_ADMIN_LEVEL = 31

local function is_admin(ctx)
    local ch = ctx.char
    return ch and ch.level >= MIN_ADMIN_LEVEL
end

-- ── goto ────────────────────────────────────────────────────────

register_command("goto", function(ctx, args)
    if not is_admin(ctx) then
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
    local dest = ctx:get_room(room_vnum)
    if not dest then
        ctx:send("그런 방이 없습니다.")
        return
    end
    ctx:move_to(room_vnum)
    ctx:defer_look()
end)

-- ── load ────────────────────────────────────────────────────────

register_command("load", function(ctx, args)
    if not is_admin(ctx) then
        ctx:send("권한이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: load mob <vnum> / load obj <vnum>")
        return
    end
    local parts = split(args)
    if #parts < 2 then
        ctx:send("사용법: load mob <vnum> / load obj <vnum>")
        return
    end
    local load_type = parts[1]:lower()
    local vnum = tonumber(parts[2])
    if not vnum then
        ctx:send("올바른 VNUM을 입력하세요.")
        return
    end
    local ch = ctx.char
    if not ch then return end

    if load_type == "mob" or load_type == "m" then
        local mob = ctx:create_mob(vnum, ch.room_vnum)
        if mob then
            ctx:send(mob.name .. "을(를) 소환했습니다.")
        else
            ctx:send("몹 #" .. vnum .. "이(가) 없습니다.")
        end
    elseif load_type == "obj" or load_type == "o" then
        local obj = ctx:create_obj(vnum)
        if obj then
            ctx:obj_to_char(obj, ch)
            ctx:send(obj.name .. "을(를) 생성했습니다.")
        else
            ctx:send("아이템 #" .. vnum .. "이(가) 없습니다.")
        end
    else
        ctx:send("사용법: load mob <vnum> / load obj <vnum>")
    end
end)

-- ── purge ───────────────────────────────────────────────────────

register_command("purge", function(ctx, args)
    if not is_admin(ctx) then
        ctx:send("권한이 없습니다.")
        return
    end
    local ch = ctx.char
    if not ch then return end
    local room = ctx:get_room()
    if not room then return end

    -- Remove NPCs from room
    local chars = ctx:get_characters()
    for i = 1, #chars do
        local mob = chars[i]
        if mob.is_npc then
            ctx:remove_char_from_room(mob)
        end
    end
    -- Remove objects
    local objects = ctx:get_objects()
    local obj_count = #objects
    for i = 1, obj_count do
        ctx:obj_from_room(objects[i])
    end
    ctx:send("방이 정화되었습니다. (NPC 및 " .. obj_count .. "개 아이템 제거)")
end)

-- ── stat ────────────────────────────────────────────────────────

register_command("stat", function(ctx, args)
    if not is_admin(ctx) then
        ctx:send("권한이 없습니다.")
        return
    end

    if not args or args == "" then
        local ch = ctx.char
        if not ch then return end
        local room = ctx:get_room()
        if not room then return end
        ctx:send("{bright_cyan}[방 정보] #" .. room.proto.vnum .. " — " .. room.proto.name .. "{reset}")
        ctx:send("  Zone: " .. room.proto.zone_number .. "  Sector: " .. room.proto.sector_type)
        local exits = ctx:get_exits()
        local chars = ctx:get_characters()
        local objects = ctx:get_objects()
        ctx:send("  Exits: " .. #exits .. "  Characters: " .. #chars)
        ctx:send("  Objects: " .. #objects)
        return
    end

    local target = ctx:find_char(args)
    if target then
        ctx:send("{bright_cyan}[캐릭터] #" .. target.proto.vnum .. " — " .. target.name .. "{reset}")
        ctx:send("  Level: " .. target.level .. "  HP: " .. target.hp .. "/" .. target.max_hp ..
                 "  AC: " .. target.proto.armor_class)
        ctx:send("  Hitroll: " .. target.proto.hitroll .. "  Damage: " .. target.proto.damage_dice)
        ctx:send("  Gold: " .. target.gold .. "  Exp: " .. target.proto.experience)
        return
    end
    ctx:send("대상을 찾을 수 없습니다.")
end)

-- ── set ─────────────────────────────────────────────────────────

register_command("set", function(ctx, args)
    if not is_admin(ctx) then
        ctx:send("권한이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: set <이름> <필드> <값>")
        return
    end
    local parts = split(args)
    if #parts < 3 then
        ctx:send("사용법: set <이름> <필드> <값>")
        return
    end
    local target_name = parts[1]
    local field = parts[2]:lower()
    local value = parts[3]

    local target = ctx:find_world_char(target_name)
    if not target then
        ctx:send("'" .. target_name .. "' 플레이어를 찾을 수 없습니다.")
        return
    end

    local num_val = tonumber(value)
    if not num_val then
        ctx:send("올바른 값을 입력하세요.")
        return
    end

    if field == "level" then
        target.level = num_val
        ctx:send(target.name .. "의 레벨을 " .. value .. "(으)로 설정했습니다.")
    elseif field == "hp" then
        target.hp = num_val
        ctx:send(target.name .. "의 HP를 " .. value .. "(으)로 설정했습니다.")
    elseif field == "gold" then
        target.gold = num_val
        ctx:send(target.name .. "의 골드를 " .. value .. "(으)로 설정했습니다.")
    elseif field == "exp" then
        target.experience = num_val
        ctx:send(target.name .. "의 경험치를 " .. value .. "(으)로 설정했습니다.")
    else
        ctx:send("알 수 없는 필드: " .. field)
    end
end)

-- ── advance ─────────────────────────────────────────────────────

register_command("advance", function(ctx, args)
    if not is_admin(ctx) then
        ctx:send("권한이 없습니다.")
        return
    end
    ctx:send("advance → set <이름> level <값> 을 사용하세요.")
end)

-- ── restore ─────────────────────────────────────────────────────

register_command("restore", function(ctx, args)
    if not is_admin(ctx) then
        ctx:send("권한이 없습니다.")
        return
    end

    if args and args ~= "" then
        local target = ctx:find_world_char(args)
        if not target then
            ctx:send("대상을 찾을 수 없습니다.")
            return
        end
        target.hp = target.max_hp
        target.mana = target.max_mana
        target.move = target.max_move
        ctx:send(target.name .. "을(를) 완전히 회복시켰습니다.")
        ctx:send_to(target, "{bright_green}완전히 회복되었습니다!{reset}")
    else
        local ch = ctx.char
        if not ch then return end
        ch.hp = ch.max_hp
        ch.mana = ch.max_mana
        ch.move = ch.max_move
        ctx:send("{bright_green}완전히 회복되었습니다!{reset}")
    end
end)

-- ── reload ──────────────────────────────────────────────────────

register_command("reload", function(ctx, args)
    if not is_admin(ctx) then
        ctx:send("권한이 없습니다.")
        return
    end
    ctx:defer_reload()
end)

-- ── shutdown ────────────────────────────────────────────────────

register_command("shutdown", function(ctx, args)
    if not is_admin(ctx) then
        ctx:send("권한이 없습니다.")
        return
    end
    ctx:send("{red}서버를 종료합니다...{reset}")
    ctx:defer_shutdown()
end)
