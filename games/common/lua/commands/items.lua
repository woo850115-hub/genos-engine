-- items.lua — basic item commands (get, drop, give, put)
-- Game-specific scripts can override these with enhanced versions.

-- ── get/take ────────────────────────────────────────────────────

register_command("get", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 주우시겠습니까?")
        return
    end

    local target = args:lower()

    -- "get <item> from <container>" or "get <item> <container>"
    local item_kw, container_kw
    local from_match = target:match("^(.-)%s+from%s+(.+)$") or target:match("^(.-)%s+에서%s+(.+)$")
    if from_match then
        item_kw = target:match("^(.-)%s+from%s+") or target:match("^(.-)%s+에서%s+")
        container_kw = target:match("%s+from%s+(.+)$") or target:match("%s+에서%s+(.+)$")
    end

    if item_kw and container_kw then
        -- Get from container
        local container = ctx:find_obj_inv(container_kw)
        if not container then container = ctx:find_obj_room(container_kw) end
        if not container then
            ctx:send("그런 용기를 찾을 수 없습니다.")
            return
        end
        if container.proto.item_type ~= "container" and container.proto.item_type ~= "corpse" then
            ctx:send(container.name .. "은(는) 용기가 아닙니다.")
            return
        end

        local contents = container.contains
        if not contents then
            ctx:send(container.name .. " 안에는 아무것도 없습니다.")
            return
        end
        local ok, len = pcall(function() return #contents end)
        if not ok or len == 0 then
            ctx:send(container.name .. " 안에는 아무것도 없습니다.")
            return
        end

        if item_kw == "all" or item_kw == "모두" then
            local picked = {}
            for i = 0, len - 1 do
                local ok2, item = pcall(function() return contents[i] end)
                if ok2 and item then
                    table.insert(picked, item)
                end
            end
            for _, item in ipairs(picked) do
                ctx:obj_from_obj(item)
                ctx:obj_to_char(item, ch)
                ctx:send(container.name .. "에서 " .. item.name .. "을(를) 꺼냅니다.")
            end
            return
        end

        -- Find specific item in container
        for i = 0, len - 1 do
            local ok2, item = pcall(function() return contents[i] end)
            if ok2 and item and item.proto.keywords:lower():find(item_kw, 1, true) then
                ctx:obj_from_obj(item)
                ctx:obj_to_char(item, ch)
                ctx:send(container.name .. "에서 " .. item.name .. "을(를) 꺼냅니다.")
                return
            end
        end
        ctx:send(container.name .. " 안에 그런 것은 없습니다.")
        return
    end

    -- Standard get from room
    local objects = ctx:get_objects()

    if target == "all" or target == "모두" then
        if #objects == 0 then
            ctx:send("여기에는 아무것도 없습니다.")
            return
        end
        for i = 1, #objects do
            local obj = objects[i]
            ctx:obj_from_room(obj)
            ctx:obj_to_char(obj, ch)
            ctx:send(obj.name .. "을(를) 주웠습니다.")
        end
        return
    end

    for i = 1, #objects do
        local obj = objects[i]
        if obj.proto.keywords:lower():find(target, 1, true) then
            ctx:obj_from_room(obj)
            ctx:obj_to_char(obj, ch)
            ctx:send(obj.name .. "을(를) 주웠습니다.")
            return
        end
    end
    ctx:send("그런 것은 여기에 없습니다.")
end, "줍")

register_command("take", function(ctx, args)
    ctx:call_command("get", args or "")
end)

-- ── drop ────────────────────────────────────────────────────────

register_command("drop", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 버리시겠습니까?")
        return
    end

    local target = args:lower()

    -- Drop all
    if target == "all" or target == "모두" then
        local inv = ctx:get_inventory()
        if #inv == 0 then
            ctx:send("아무것도 갖고 있지 않습니다.")
            return
        end
        for i = 1, #inv do
            local obj = inv[i]
            ctx:obj_from_char(obj)
            ctx:obj_to_room(obj, ch.room_vnum)
            ctx:send(obj.name .. "을(를) 버렸습니다.")
        end
        return
    end

    local obj = ctx:find_obj_inv(args)
    if not obj then
        ctx:send("그런 것을 갖고 있지 않습니다.")
        return
    end
    ctx:obj_from_char(obj)
    ctx:obj_to_room(obj, ch.room_vnum)
    ctx:send(obj.name .. "을(를) 버렸습니다.")
end, "버려")

-- ── give ────────────────────────────────────────────────────────

register_command("give", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("사용법: give <아이템> <대상>")
        return
    end

    -- Parse "item target" or "gold amount target"
    local parts = split(args)
    if #parts < 2 then
        ctx:send("사용법: give <아이템> <대상>")
        return
    end

    -- Check for gold transfer: "give 100 gold <target>" or "give 100 <target>"
    local amount = tonumber(parts[1])
    if amount and #parts >= 2 then
        local target_name
        if #parts >= 3 and (parts[2]:lower() == "gold" or parts[2]:lower() == "골드" or parts[2]:lower() == "coins") then
            target_name = parts[3]
        else
            target_name = parts[2]
        end
        local target = ctx:find_char(target_name)
        if not target then
            ctx:send("그런 대상을 찾을 수 없습니다.")
            return
        end
        amount = math.floor(amount)
        if amount <= 0 then
            ctx:send("0보다 큰 금액을 지정하세요.")
            return
        end
        if ch.gold < amount then
            ctx:send("그만큼의 골드가 없습니다.")
            return
        end
        ch.gold = ch.gold - amount
        target.gold = target.gold + amount
        ctx:send(target.name .. "에게 " .. amount .. " 골드를 줍니다.")
        if target.session then
            ctx:send_to(target, "\r\n" .. ch.name .. "이(가) 당신에게 " .. amount .. " 골드를 줍니다.")
        end
        return
    end

    -- Item transfer: "give <item_keyword> <target_name>"
    local item_keyword = parts[1]
    local target_name = parts[2]

    local obj = ctx:find_obj_inv(item_keyword)
    if not obj then
        ctx:send("그런 아이템을 갖고 있지 않습니다.")
        return
    end

    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end

    -- Transfer item
    ctx:obj_from_char(obj)
    ctx:obj_to_char(obj, target)
    ctx:send(target.name .. "에게 " .. obj.name .. "을(를) 줍니다.")
    if target.session then
        ctx:send_to(target, "\r\n" .. ch.name .. "이(가) 당신에게 " .. obj.name .. "을(를) 줍니다.")
    end
end, "줘")

-- ── put ─────────────────────────────────────────────────────────

register_command("put", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("사용법: put <아이템> <용기>")
        return
    end

    -- Parse "item_keyword container_keyword" or "item in container"
    local item_kw, container_kw
    local in_match = args:match("^(.-)%s+in%s+(.+)$") or args:match("^(.-)%s+안에?%s+(.+)$")
    if in_match then
        item_kw = args:match("^(.-)%s+in%s+")
        container_kw = args:match("%s+in%s+(.+)$")
        if not item_kw then
            item_kw = args:match("^(.-)%s+안에?%s+")
            container_kw = args:match("%s+안에?%s+(.+)$")
        end
    else
        local parts = split(args)
        if #parts < 2 then
            ctx:send("사용법: put <아이템> <용기>")
            return
        end
        item_kw = parts[1]
        container_kw = parts[2]
    end

    if not item_kw or not container_kw then
        ctx:send("사용법: put <아이템> <용기>")
        return
    end

    local obj = ctx:find_obj_inv(item_kw)
    if not obj then
        ctx:send("그런 아이템을 갖고 있지 않습니다.")
        return
    end

    -- Find container in inventory or room
    local container = ctx:find_obj_inv(container_kw)
    if not container then container = ctx:find_obj_room(container_kw) end
    if not container then
        ctx:send("그런 용기를 찾을 수 없습니다.")
        return
    end
    if container.proto.item_type ~= "container" then
        ctx:send(container.name .. "은(는) 용기가 아닙니다.")
        return
    end
    if obj == container then
        ctx:send("자기 자신에게 넣을 수 없습니다.")
        return
    end

    -- Move item from inventory to container
    ctx:obj_from_char(obj)
    ctx:obj_to_obj(obj, container)
    ctx:send(container.name .. "에 " .. obj.name .. "을(를) 넣습니다.")
    ctx:send_room(ch.name .. "이(가) " .. container.name .. "에 무언가를 넣습니다.")
end, "넣")
