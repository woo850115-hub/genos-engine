-- core.lua — core commands: look, quit, save, who, score, inventory, help, exits, commands, alias
-- These are generic implementations that game-specific scripts can override.

-- ── look ─────────────────────────────────────────────────────────

register_command("look", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local room = ctx:get_room()
    if not room then
        ctx:send("허공에 떠 있습니다...")
        return
    end

    -- Look at something specific
    if args and args ~= "" then
        local target = args:lower()

        -- "look in <container>"
        local in_target = target:match("^in%s+(.+)$") or target:match("^안%s+(.+)$")
        if in_target then
            -- Search inventory, then room for container
            local container = ctx:find_obj_inv(in_target)
            if not container then container = ctx:find_obj_room(in_target) end
            if container then
                if container.proto.item_type == "container" then
                    local contents = container.contains
                    if contents then
                        local ok, len = pcall(function() return #contents end)
                        if ok and len > 0 then
                            ctx:send("{yellow}" .. container.proto.short_desc .. " 안:{reset}")
                            for ci = 0, len - 1 do
                                local ok2, item = pcall(function() return contents[ci] end)
                                if ok2 and item then
                                    ctx:send("  " .. item.proto.short_desc)
                                end
                            end
                        else
                            ctx:send(container.proto.short_desc .. " 안에는 아무것도 없습니다.")
                        end
                    else
                        ctx:send(container.proto.short_desc .. " 안에는 아무것도 없습니다.")
                    end
                else
                    ctx:send("그것은 용기가 아닙니다.")
                end
            else
                ctx:send("그런 것을 찾을 수 없습니다.")
            end
            return
        end

        -- Check extra descs
        local eds = ctx:get_extra_descs()
        for i = 1, #eds do
            local ed = eds[i]
            if ed.keywords:lower():find(target, 1, true) then
                ctx:send(ed.description)
                return
            end
        end

        -- Check characters
        local chars = ctx:get_characters()
        for i = 1, #chars do
            local mob = chars[i]
            if mob ~= ch then
                local is_match = false
                if mob.proto.keywords:lower():find(target, 1, true) then
                    is_match = true
                end
                if not is_match and mob.player_name and mob.player_name ~= "" and mob.player_name:lower():find(target, 1, true) then
                    is_match = true
                end
                if is_match then
                    if mob.proto.detail_desc and mob.proto.detail_desc ~= "" then
                        ctx:send(mob.proto.detail_desc)
                    else
                        ctx:send(mob.name .. "을(를) 바라봅니다.")
                    end
                    -- Show equipment of target
                    if not mob.is_npc or mob.equipment then
                        local equip = mob.equipment
                        if equip then
                            local has_items = false
                            for slot, obj in pairs(equip) do
                                if not has_items then
                                    ctx:send("{cyan}" .. mob.name .. "의 장비:{reset}")
                                    has_items = true
                                end
                                ctx:send("  <" .. tostring(slot) .. "> " .. obj.proto.short_desc)
                            end
                        end
                    end
                    -- Show condition
                    local ratio = mob.hp / math.max(1, mob.max_hp)
                    local condition
                    if ratio >= 1.0 then condition = "완벽한 상태입니다."
                    elseif ratio >= 0.75 then condition = "약간의 상처가 있습니다."
                    elseif ratio >= 0.50 then condition = "상당한 부상을 입고 있습니다."
                    elseif ratio >= 0.25 then condition = "심각한 부상 상태입니다."
                    else condition = "거의 죽어가고 있습니다!"
                    end
                    ctx:send(mob.name .. ": " .. condition)
                    return
                end
            end
        end

        -- Check objects in room
        local objs = ctx:get_objects()
        for i = 1, #objs do
            local obj = objs[i]
            if obj.proto.keywords:lower():find(target, 1, true) then
                ctx:send(obj.proto.short_desc)
                return
            end
        end

        -- Check inventory
        local inv = ctx:get_inventory()
        for i = 1, #inv do
            local obj = inv[i]
            if obj.proto.keywords:lower():find(target, 1, true) then
                ctx:send(obj.proto.short_desc)
                return
            end
        end

        ctx:send("그런 것을 볼 수 없습니다.")
        return
    end

    -- Room display
    ctx:send("\r\n{cyan}" .. room.proto.name .. "{reset}")
    -- Brief mode: skip room description if already visited
    local brief = ctx:get_player_data("toggles")
    local is_brief = false
    if brief then
        local ok, val = pcall(function() return brief.brief end)
        if ok and val then is_brief = true end
    end
    if not is_brief and room.proto.description and room.proto.description ~= "" then
        ctx:send("   " .. room.proto.description:gsub("%s+$", ""))
    end

    -- Exits
    local exits = ctx:get_exits()
    local exit_names = {}
    local named_exits = {}
    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction < 6 then
            local dir_name = DIR_NAMES[ex.direction + 1]
            if room:is_door_closed(ex.direction) then
                dir_name = "(" .. dir_name .. ")"
            end
            table.insert(exit_names, dir_name)
        elseif ex.keywords and ex.keywords ~= "" then
            table.insert(named_exits, ex.keywords)
        end
    end
    local exit_str = ""
    if #exit_names > 0 then
        exit_str = table.concat(exit_names, " ")
    end
    if #named_exits > 0 then
        if exit_str ~= "" then exit_str = exit_str .. " | " end
        exit_str = exit_str .. table.concat(named_exits, " ")
    end
    if exit_str ~= "" then
        ctx:send("{green}[ 출구: " .. exit_str .. " ]{reset}")
    end

    -- Objects in room
    local objs = ctx:get_objects()
    for i = 1, #objs do
        local obj = objs[i]
        if obj.proto.long_desc and obj.proto.long_desc ~= "" then
            ctx:send("{yellow}" .. obj.proto.long_desc:gsub("%s+$", "") .. "{reset}")
        end
    end

    -- Characters in room
    local chars = ctx:get_characters()
    for i = 1, #chars do
        local mob = chars[i]
        if mob ~= ch then
            -- Check if hidden (affect id 1002)
            local hidden = false
            local aff = mob.affects
            if aff then
                local aok, alen = pcall(function() return #aff end)
                if aok then
                    for ai = 0, alen - 1 do
                        local ok2, a = pcall(function() return aff[ai] end)
                        if ok2 and a then
                            local ok3, aid = pcall(function() return a.id end)
                            if ok3 and aid == 1002 then
                                hidden = true
                                break
                            end
                        end
                    end
                end
            end
            if not hidden then
                if mob.is_npc then
                    ctx:send("{bright_cyan}" .. mob.proto.long_desc:gsub("%s+$", "") .. "{reset}")
                else
                    ctx:send(mob.name .. "이(가) 서 있습니다.")
                end
            end
        end
    end
end, "봐")

-- ── quit ─────────────────────────────────────────────────────────

register_command("quit", function(ctx, args)
    local ch = ctx.char
    if ch and ch.fighting then
        ctx:send("전투 중에는 나갈 수 없습니다!")
        return
    end
    ctx:defer_save()
    ctx:send("저장되었습니다. 안녕히 가세요!")
    ctx:close_session()
end, "나가기")

-- ── save ─────────────────────────────────────────────────────────

register_command("save", function(ctx, args)
    ctx:defer_save()
    ctx:send("저장되었습니다.")
end, "저장")

-- ── who ──────────────────────────────────────────────────────────

register_command("who", function(ctx, args)
    local players = ctx:get_players()
    ctx:send("{cyan}━━━━━━ 현재 접속 중인 플레이어 ━━━━━━{reset}")
    local count = #players
    for i = 1, count do
        local p = players[i]
        local cls = ctx:get_class(p.class_id)
        local cls_name = "모험가"
        if cls then cls_name = cls.name end
        local title = ""
        ctx:send("  [" .. string.format("%3d", p.level) .. " " ..
                 string.format("%-6s", cls_name) .. "] " .. p.name .. title)
    end
    ctx:send("{cyan}━━━━━━ 총 " .. count .. "명 접속 중 ━━━━━━{reset}")
end, "누구")

-- ── score ────────────────────────────────────────────────────────

register_command("score", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local cls = ctx:get_class(ch.class_id)
    local cls_name = "모험가"
    if cls then cls_name = cls.name end

    ctx:send("{cyan}━━━━━━ " .. ch.name .. " ━━━━━━{reset}")
    ctx:send("  레벨: " .. ch.level .. "  직업: " .. cls_name)
    ctx:send("  HP: {green}" .. ch.hp .. "/" .. ch.max_hp .. "{reset}  " ..
             "마나: {blue}" .. ch.mana .. "/" .. ch.max_mana .. "{reset}  " ..
             "이동력: " .. ch.move .. "/" .. ch.max_move)
    ctx:send("  골드: {yellow}" .. ch.gold .. "{reset}  경험치: " .. ch.experience)
    ctx:send("{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
end, "점수")

-- ── inventory ────────────────────────────────────────────────────

register_command("inventory", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local inv = ctx:get_inventory()
    if #inv == 0 then
        ctx:send("아무것도 들고 있지 않습니다.")
        return
    end
    ctx:send("소지품:")
    for i = 1, #inv do
        ctx:send("  " .. inv[i].name)
    end
end, "소지품")

-- ── help ─────────────────────────────────────────────────────────

register_command("help", function(ctx, args)
    local keyword = "help"
    if args and args ~= "" then keyword = args:lower() end
    local text = ctx:get_help(keyword)
    if not text then
        ctx:send("'" .. keyword .. "'에 대한 도움말이 없습니다.")
    elseif text:sub(1, 12) == "__MULTIPLE__" then
        local list = text:sub(14)
        ctx:send("여러 도움말이 발견되었습니다: " .. list)
    else
        ctx:send(text)
    end
end, "도움")

-- ── exits ────────────────────────────────────────────────────────

register_command("exits", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local room = ctx:get_room()
    if not room then return end

    local exits = ctx:get_exits()
    if #exits == 0 then
        ctx:send("출구가 없습니다!")
        return
    end

    ctx:send("사용 가능한 출구:")
    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction < 6 then
            local dir_name = DIR_NAMES[ex.direction + 1]
            local dest = ctx:get_room(ex.to_room)
            local dest_name = "알 수 없음"
            if dest then dest_name = dest.name end
            local status = ""
            if room:has_door(ex.direction) then
                if room:is_door_closed(ex.direction) then
                    status = " (닫힘)"
                else
                    status = " (열림)"
                end
            end
            ctx:send("  " .. string.format("%-4s", dir_name) .. " - " .. dest_name .. status)
        end
    end
end, "출구")

-- ── commands ─────────────────────────────────────────────────────

register_command("commands", function(ctx, args)
    local cmds = ctx:get_all_commands()
    local entries = {}
    for i = 1, #cmds do
        local c = cmds[i]
        if c.kr and c.kr ~= "" then
            table.insert(entries, c.kr .. "(" .. c.eng .. ")")
        else
            table.insert(entries, c.eng)
        end
    end

    ctx:send("{cyan}사용 가능한 명령어:{reset}")
    local line = "  "
    for i = 1, #entries do
        if #line + #entries[i] + 2 > 78 then
            ctx:send(line)
            line = "  "
        end
        line = line .. entries[i] .. "  "
    end
    if #line > 2 then
        ctx:send(line)
    end
    ctx:send("\r\n총 " .. #entries .. "개 명령어")
end, "명령어")

-- ── alias ────────────────────────────────────────────────────────

register_command("alias", function(ctx, args)
    if not args or args == "" then
        local aliases = ctx:get_aliases()
        if #aliases == 0 then
            ctx:send("설정된 별칭이 없습니다.")
            return
        end
        ctx:send("설정된 별칭:")
        for i = 1, #aliases do
            ctx:send("  " .. aliases[i].name .. " = " .. aliases[i].cmd)
        end
        return
    end

    local parts = split(args)
    if #parts < 2 then
        ctx:send("사용법: alias <이름> <명령어>")
        return
    end

    local alias_name = parts[1]
    local alias_cmd = args:match("^%S+%s+(.+)$")
    if not alias_cmd then
        ctx:send("사용법: alias <이름> <명령어>")
        return
    end

    if ctx:get_alias_count() >= 20 then
        ctx:send("별칭은 최대 20개까지 설정할 수 있습니다.")
        return
    end

    ctx:set_alias(alias_name, alias_cmd)
    ctx:send("별칭 설정: " .. alias_name .. " = " .. alias_cmd)
end, "별칭")

-- ── say ──────────────────────────────────────────────────────────

-- ── junk — destroy an item immediately ──────────────────────────
register_command("junk", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 폐기하시겠습니까?")
        return
    end
    local obj = ctx:find_obj_inv(args)
    if not obj then
        ctx:send("그런 것을 갖고 있지 않습니다.")
        return
    end
    ctx:obj_from_char(obj)
    ctx:send(obj.name .. "을(를) 폐기했습니다.")
end, "폐기")

-- ── donate — donate item to donation room ───────────────────────
register_command("donate", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 기부하시겠습니까?")
        return
    end
    local obj = ctx:find_obj_inv(args)
    if not obj then
        ctx:send("그런 것을 갖고 있지 않습니다.")
        return
    end
    ctx:obj_from_char(obj)
    -- Place in donation room (vnum 3003, tbaMUD default)
    ctx:obj_to_room(obj, 3003)
    ctx:send(obj.name .. "을(를) 기부했습니다.")
    ctx:send_all("{cyan}" .. ch.name .. "이(가) " .. obj.name .. "을(를) 기부합니다.{reset}")
end, "기부")

-- ── unalias ─────────────────────────────────────────────────────
register_command("unalias", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: unalias <이름>")
        return
    end
    local aliases = ctx:get_aliases()
    local found = false
    for i = 1, #aliases do
        if aliases[i].name == args then
            found = true
            break
        end
    end
    if not found then
        ctx:send("'" .. args .. "' 별칭이 없습니다.")
        return
    end
    ctx:set_alias(args, nil)
    ctx:send("별칭 '" .. args .. "'이(가) 삭제되었습니다.")
end)

register_command("say", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇이라고 말하시겠습니까?")
        return
    end
    local ch = ctx.char
    if not ch then return end

    ctx:send("{green}당신이 말합니다, '" .. args .. "'{reset}")
    ctx:send_room("{green}" .. ch.name .. "이(가) 말합니다, '" .. args .. "'{reset}")
end, "말")
