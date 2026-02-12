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
    if not args or args == "" then
        ctx:send("무엇을 누구에게 주시겠습니까?")
        return
    end
    ctx:send("구현 예정입니다.")
end, "줘")

-- ── put ─────────────────────────────────────────────────────────

register_command("put", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 어디에 넣으시겠습니까?")
        return
    end
    ctx:send("구현 예정입니다.")
end, "넣")
