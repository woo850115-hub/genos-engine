-- items.lua — 10woongi item commands (get, drop, wear, remove)
-- 22-slot equipment system with sequential ring filling

-- Ring slots: 9, 13~21 (10 total)
local RING_SLOTS  = {9, 13, 14, 15, 16, 17, 18, 19, 20, 21}
-- Armlet slots: 8, 22
local ARMLET_SLOTS = {8, 22}

local function find_wear_slot(ch, wear_flags)
    if not wear_flags then return nil end
    local ring_set  = {}
    for _, s in ipairs(RING_SLOTS) do ring_set[s] = true end
    local armlet_set = {}
    for _, s in ipairs(ARMLET_SLOTS) do armlet_set[s] = true end

    local flag_count = 0
    while true do
        local ok, flag = pcall(function() return wear_flags[flag_count] end)
        if not ok or not flag then break end
        flag = tonumber(flag) or 0
        if flag ~= 0 then
            if ring_set[flag] then
                for _, rs in ipairs(RING_SLOTS) do
                    local ok2, existing = pcall(function() return ch.equipment[rs] end)
                    if not ok2 or not existing then
                        return rs
                    end
                end
            elseif armlet_set[flag] then
                for _, ars in ipairs(ARMLET_SLOTS) do
                    local ok2, existing = pcall(function() return ch.equipment[ars] end)
                    if not ok2 or not existing then
                        return ars
                    end
                end
            else
                local ok2, existing = pcall(function() return ch.equipment[flag] end)
                if not ok2 or not existing then
                    return flag
                end
            end
        end
        flag_count = flag_count + 1
    end
    return nil
end

register_command("get", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 주우시겠습니까?")
        return
    end

    local obj = ctx:find_obj_room(args)
    if not obj then
        ctx:send("그런 것은 여기에 없습니다.")
        return
    end

    ctx:obj_from_room(obj)
    ctx:obj_to_char(obj, ch)
    ctx:send(obj.name .. "을(를) 주웠습니다.")
end, "주워")

register_command("drop", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 버리시겠습니까?")
        return
    end

    local obj = ctx:find_obj_inv(args)
    if not obj then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end

    ctx:obj_from_char(obj)
    ctx:obj_to_room(obj, ch.room_vnum)
    ctx:send(obj.name .. "을(를) 버렸습니다.")
end, "놔")

register_command("wear", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 착용하시겠습니까?")
        return
    end

    local obj = ctx:find_obj_inv(args)
    if not obj then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end

    local wear_flags = obj.proto.wear_flags
    if not wear_flags then
        ctx:send("착용할 수 없는 물건입니다.")
        return
    end

    local slot = find_wear_slot(ch, wear_flags)
    if not slot then
        ctx:send("착용할 수 있는 빈 슬롯이 없습니다.")
        return
    end

    ctx:obj_from_char(obj)
    ctx:equip(obj, slot)
    local slot_name = WEAR_SLOTS[slot] or ("슬롯" .. slot)
    ctx:send("<" .. slot_name .. ">에 " .. obj.name .. "을(를) 착용했습니다.")
end, "착용")

register_command("wield", function(ctx, args)
    ctx:call_command("wear", args)
end, "챙기")

register_command("remove", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 벗으시겠습니까?")
        return
    end

    local obj, slot = ctx:find_obj_equip(args)
    if not obj then
        ctx:send("그런 장비를 착용하고 있지 않습니다.")
        return
    end

    ctx:unequip(slot)
    ctx:obj_to_char(obj, ch)
    local slot_name = WEAR_SLOTS[slot] or ("슬롯" .. slot)
    ctx:send("<" .. slot_name .. ">에서 " .. obj.name .. "을(를) 벗었습니다.")
end, "벗")
