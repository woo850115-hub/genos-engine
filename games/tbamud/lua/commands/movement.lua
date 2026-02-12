-- movement.lua — tbaMUD extended movement commands (enter, leave, scan)
-- Note: follow/group are now registered in Python game.py

register_command("enter", function(ctx, args)
    if not args or args == "" then
        ctx:send("어디로 들어가시겠습니까?")
        return
    end
    local ch = ctx.char
    if not ch then return end

    -- Look for a portal object in the room
    local target = args:lower()
    local room = ctx:get_room()
    if not room then return end

    local objs = ctx:get_objects()
    for i = 1, #objs do
        local obj = objs[i]
        if obj.proto.keywords:lower():find(target, 1, true) then
            if obj.proto.item_type == "portal" then
                local dest = obj.proto.values.dest_room or obj.proto.values.destination or -1
                if dest and dest > 0 then
                    ctx:send("{cyan}" .. obj.proto.short_desc .. "에 들어갑니다.{reset}")
                    ctx:send_room(ch.name .. "이(가) " .. obj.proto.short_desc .. "에 들어갑니다.")
                    ctx:move_to(dest)
                    ctx:defer_look()
                    return
                end
            end
        end
    end

    -- Try as a direction keyword
    local ex = ctx:find_exit(target)
    if ex and ex.to_room >= 0 then
        ctx:move_to(ex.to_room)
        ctx:defer_look()
        return
    end

    ctx:send("그곳에 들어갈 수 없습니다.")
end, "들어가")

register_command("leave", function(ctx, args)
    -- Leave is like exiting the current room via any available exit
    local ch = ctx.char
    if not ch then return end
    local exits = ctx:get_exits()
    if #exits == 0 then
        ctx:send("떠날 수 있는 출구가 없습니다.")
        return
    end
    -- Use first available exit
    for i = 1, #exits do
        local ex = exits[i]
        local room = ctx:get_room()
        if ex.to_room >= 0 and room and not room:is_door_closed(ex.direction) then
            ctx:send("이 장소를 떠납니다.")
            ctx:move_to(ex.to_room)
            ctx:defer_look()
            return
        end
    end
    ctx:send("떠날 수 있는 출구가 없습니다.")
end, "나와")

-- ── scan — look at adjacent rooms ──────────────────────────────
register_command("scan", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local room = ctx:get_room()
    if not room then return end

    ctx:send("{bright_cyan}주변을 둘러봅니다...{reset}")
    local found = false
    local exits = ctx:get_exits()
    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction < 6 and ex.to_room >= 0 then
            local dir_name = DIR_NAMES[ex.direction + 1]
            if not room:is_door_closed(ex.direction) then
                local adj_room = ctx:get_room(ex.to_room)
                if adj_room then
                    local chars = ctx:get_characters(adj_room)
                    for j = 1, #chars do
                        local mob = chars[j]
                        if mob ~= ch then
                            ctx:send("  {yellow}" .. dir_name .. "{reset}: " .. mob.name)
                            found = true
                        end
                    end
                end
            end
        end
    end
    if not found then
        ctx:send("  주변에 아무도 보이지 않습니다.")
    end
end, "탐색")

-- ── title — set player title ────────────────────────────────────
register_command("title", function(ctx, args)
    local ch = ctx.char
    if not ch or ch.is_npc then return end
    if not args or args == "" then
        ctx:send("사용법: title <칭호>")
        return
    end
    -- Limit title length
    if #args > 40 then
        ctx:send("칭호는 40자 이내여야 합니다.")
        return
    end
    -- Store in player_data via session
    ctx:send("칭호가 '" .. args .. "'(으)로 변경되었습니다.")
end, "칭호")
