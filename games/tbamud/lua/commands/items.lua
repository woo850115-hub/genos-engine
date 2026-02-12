-- items.lua — tbaMUD item commands (overrides common get/drop, adds wear/remove)

-- Wear position names (tbaMUD 18 slots)
local WEAR_NAMES = {
    [0]  = "머리 위에",
    [1]  = "왼쪽 손가락에",
    [2]  = "오른쪽 손가락에",
    [3]  = "목에 (1)",
    [4]  = "목에 (2)",
    [5]  = "몸통에",
    [6]  = "머리에",
    [7]  = "다리에",
    [8]  = "발에",
    [9]  = "손에",
    [10] = "팔에",
    [11] = "방패로",
    [12] = "몸 주위에",
    [13] = "허리에",
    [14] = "왼팔에",
    [15] = "오른팔에",
    [16] = "오른손에",
    [17] = "왼손에",
}

-- ── get/take (override common — adds "all" support) ─────────────

register_command("get", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 주우시겠습니까?")
        return
    end

    local target = args:lower()
    local room = ctx:get_room()
    if not room then return end
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

-- ── wear/wield ──────────────────────────────────────────────────

register_command("wear", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 착용하시겠습니까?")
        return
    end

    local obj = ctx:find_obj_inv(args)
    if not obj then
        ctx:send("그런 것을 갖고 있지 않습니다.")
        return
    end

    local wear_flags = obj.proto.wear_flags
    if not wear_flags then
        ctx:send("그것은 착용할 수 없습니다.")
        return
    end

    -- Find first available wear position > 0
    local pos = -1
    local ok, len = pcall(function() return #wear_flags end)
    if ok then
        for i = 0, len - 1 do
            local fok, flag = pcall(function() return wear_flags[i] end)
            if fok and flag and flag > 0 and flag < 18 then
                local equip = ctx:get_equipment()
                local occupied = false
                for j = 1, #equip do
                    if equip[j].slot == flag then
                        occupied = true
                        break
                    end
                end
                if not occupied then
                    pos = flag
                    break
                end
            end
        end
    end

    if pos < 0 then
        ctx:send("이미 그 위치에 뭔가를 착용하고 있습니다.")
        return
    end

    ctx:obj_from_char(obj)
    ctx:equip(obj, pos)
    local pos_name = WEAR_NAMES[pos] or "어딘가에"
    ctx:send(obj.name .. "을(를) " .. pos_name .. " 착용했습니다.")
end, "입")

register_command("wield", function(ctx, args)
    ctx:call_command("wear", args or "")
end)

-- ── remove ──────────────────────────────────────────────────────

register_command("remove", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 벗으시겠습니까?")
        return
    end

    local target = args:lower()
    local equip = ctx:get_equipment()
    for i = 1, #equip do
        local obj = equip[i].obj
        if obj.proto.keywords:lower():find(target, 1, true) then
            ctx:unequip(equip[i].slot)
            ctx:send(obj.name .. "을(를) 벗었습니다.")
            return
        end
    end
    ctx:send("그런 것을 착용하고 있지 않습니다.")
end, "벗")

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
