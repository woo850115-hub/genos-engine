-- items.lua — 3eyes 아이템 명령어 (원본 cmdlist 기반)
-- 주워, 버려/넣어, 줘, 마셔/먹어, 입어/착용, 무장, 벗어, 쥐어/잡아

local SLOT_NAMES = {
    [0]="머리", [1]="목", [2]="가슴", [3]="몸통",
    [4]="다리", [5]="발", [6]="오른손", [7]="왼손",
    [8]="오른팔", [9]="왼팔", [10]="방패", [11]="허리",
    [12]="오른손목", [13]="왼손목", [14]="오른손가락", [15]="왼손가락",
    [16]="무기", [17]="보조무기",
}

-- ── 주워 (get) ──────────────────────────────────────────────────
register_command("주워", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("주우실 물건이 뭔데요?")
        return
    end

    local parts = split(args)

    -- 2+ parts: get from container (주워 <item> <container>)
    if #parts >= 2 then
        local item_kw = parts[1]
        local cont_kw = parts[#parts]

        -- "모두 <container>" — get all from container
        if item_kw == "all" or item_kw == "모두" then
            local container = ctx:find_obj_inv(cont_kw)
            if not container then container = ctx:find_obj_room(cont_kw) end
            if not container then
                ctx:send("그것은 보이지 않는데요")
                return
            end
            if container.proto.item_type ~= "container" then
                ctx:send("그것은 물건을 넣어두는 종류가 아닙니다")
                return
            end
            local contents = container.contains
            local count = 0
            if contents then
                local items = {}
                for ci = 0, 100 do
                    local ok, item = pcall(function() return contents[ci] end)
                    if not ok or not item then break end
                    table.insert(items, item)
                end
                for _, item in ipairs(items) do
                    ctx:obj_from_obj(item)
                    ctx:obj_to_char(item, ch)
                    count = count + 1
                end
            end
            if count == 0 then
                ctx:send("그안에는 그런것이 들어 있지 않습니다.")
            else
                ctx:send("당신은 " .. container.name .. "에서 물건들을 꺼냅니다.")
                ctx:send_room(ch.name .. "이(가) " .. container.name .. "에서 물건들을 꺼냅니다.")
            end
            return
        end

        -- Single item from container
        local container = ctx:find_obj_inv(cont_kw)
        if not container then container = ctx:find_obj_room(cont_kw) end
        if not container then
            ctx:send("그것은 보이지 않는데요")
            return
        end
        if container.proto.item_type ~= "container" then
            ctx:send("그것은 물건을 넣어두는 종류가 아닙니다")
            return
        end
        local contents = container.contains
        if contents then
            local kw_lower = item_kw:lower()
            for ci = 0, 100 do
                local ok, item = pcall(function() return contents[ci] end)
                if not ok or not item then break end
                if item.proto.keywords:lower():find(kw_lower, 1, true) then
                    ctx:obj_from_obj(item)
                    ctx:obj_to_char(item, ch)
                    ctx:send("당신은 " .. container.name .. "에서 " .. item.name .. "을(를) 꺼냅니다.")
                    ctx:send_room(ch.name .. "이(가) " .. container.name .. "에서 " .. item.name .. "을(를) 꺼냅니다.")
                    return
                end
            end
        end
        ctx:send("그것에는 그런것이 들어 있지 않습니다.")
        return
    end

    -- 1 part: get from room
    local kw = parts[1]

    -- "모두" / "all" — get all from room
    if kw == "all" or kw == "모두" then
        local objs = ctx:get_objects()
        local count = 0
        for i = 1, #objs do
            local obj = objs[i]
            ctx:obj_from_room(obj)
            ctx:obj_to_char(obj, ch)
            ctx:send("당신은 " .. obj.name .. "을(를) 줍습니다.")
            count = count + 1
        end
        if count == 0 then
            ctx:send("여기에 그런것은 보이지 않습니다.")
        else
            ctx:send_room(ch.name .. "이(가) 바닥의 물건들을 주워 가집니다.")
        end
        return
    end

    -- Single item from room
    local obj = ctx:find_obj_room(kw)
    if not obj then
        ctx:send("여기에 그런것은 보이지 않습니다.")
        return
    end
    -- Money type: auto-convert to gold
    if obj.proto.item_type == "money" then
        local amount = obj.proto.cost or 0
        if amount > 0 then
            ch.gold = ch.gold + amount
            ctx:obj_from_room(obj)
            ctx:send("당신이 가진돈은 이제 " .. format_number(ch.gold) .. "냥입니다.")
            ctx:send_room(ch.name .. "이(가) 돈을 주워 가집니다.")
            return
        end
    end
    ctx:obj_from_room(obj)
    ctx:obj_to_char(obj, ch)
    ctx:send("당신은 " .. obj.name .. "을(를) 주웠습니다.")
    ctx:send_room(ch.name .. "이(가) " .. obj.name .. "을(를) 주워 가집니다.")
end)
register_command("집어", function(ctx, args) ctx:call_command("주워", args or "") end)
register_command("가져", function(ctx, args) ctx:call_command("주워", args or "") end)
register_command("꺼내", function(ctx, args) ctx:call_command("주워", args or "") end)

-- ── 버려 (drop) / 넣어 (put, alias) ────────────────────────────
register_command("버려", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("버리실 물건은?")
        return
    end

    local parts = split(args)

    -- 2+ parts: put in container (버려/넣어 <item> <container>)
    if #parts >= 2 then
        local item_kw = parts[1]
        local cont_kw = parts[#parts]

        -- Find container in inventory or room
        local container = ctx:find_obj_inv(cont_kw)
        if not container then container = ctx:find_obj_room(cont_kw) end
        if not container then
            ctx:send("그런 물건은 가지고 있지 않습니다.")
            return
        end
        if container.proto.item_type ~= "container" then
            ctx:send(container.name .. "는 담는 종류가 아닙니다.")
            return
        end

        -- "모두 <container>"
        if item_kw == "all" or item_kw == "모두" then
            local inv = ctx:get_inventory()
            local count = 0
            for i = 1, #inv do
                local item = inv[i]
                if item ~= container then
                    ctx:obj_from_char(item)
                    ctx:obj_to_obj(item, container)
                    count = count + 1
                end
            end
            if count == 0 then
                ctx:send("당신 소지품에는 그런것이 없습니다")
            else
                ctx:send("당신은 물건들을 " .. container.name .. "안에 넣습니다.")
                ctx:send_room(ch.name .. "이(가) 물건들을 " .. container.name .. "안에 넣습니다.")
            end
            return
        end

        -- Single item into container
        local item = ctx:find_obj_inv(item_kw)
        if not item then
            ctx:send("당신은 그런 것을 갖고 있지 않군요.")
            return
        end
        if item == container then
            ctx:send(container.name .. "안에 " .. item.name .. "를 넣을 수는 없습니다.")
            return
        end
        ctx:obj_from_char(item)
        ctx:obj_to_obj(item, container)
        ctx:send("당신은 " .. item.name .. "을(를) " .. container.name .. " 안에 넣습니다.")
        ctx:send_room(ch.name .. "이(가) " .. item.name .. "을(를) " .. container.name .. "안에 넣었습니다.")
        return
    end

    -- 1 part: drop to room floor
    local kw = parts[1]

    -- "모두" / "all" — drop all
    if kw == "all" or kw == "모두" then
        local inv = ctx:get_inventory()
        local count = 0
        for i = 1, #inv do
            local obj = inv[i]
            ctx:obj_from_char(obj)
            ctx:obj_to_room(obj, ch.room_vnum)
            count = count + 1
        end
        if count == 0 then
            ctx:send("당신은 그런것을 소지하고 있지 않습니다.")
        else
            ctx:send("당신은 소지품을 모두 버렸습니다.")
            ctx:send_room(ch.name .. "이(가) 소지품을 모두 버렸습니다.")
        end
        return
    end

    -- Single item drop
    local obj = ctx:find_obj_inv(kw)
    if not obj then
        ctx:send("당신 소지품에 그런것은 없습니다.")
        return
    end
    ctx:obj_from_char(obj)
    ctx:obj_to_room(obj, ch.room_vnum)
    ctx:send("당신은 " .. obj.name .. "을(를) 버렸습니다.")
    ctx:send_room(ch.name .. "이(가) " .. obj.name .. "을(를) 버렸습니다.")
end)
register_command("넣어", function(ctx, args) ctx:call_command("버려", args or "") end)

-- ── 줘 (give) ───────────────────────────────────────────────────
register_command("줘", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("누구에게 주시려구요?")
        return
    end

    local parts = split(args)
    if #parts < 2 then
        ctx:send("누구에게 주시려구요?")
        return
    end

    local item_kw = parts[1]
    local target_name = parts[2]

    -- Money: "줘 <N>냥 <target>"
    local amount = item_kw:match("^(%d+)냥$")
    if amount then
        amount = tonumber(amount)
        local target = ctx:find_char(target_name)
        if not target then
            target = ctx:find_player(target_name)
        end
        if not target then
            ctx:send("그런 사람은 여기 없어요!")
            return
        end
        if target == ch then
            ctx:send("자기자신에게 물건을 주시다뇨?")
            return
        end
        if ch.gold < amount then
            ctx:send("당신은 그만큼의 돈을 가지고 있지 않습니다.")
            return
        end
        ch.gold = ch.gold - amount
        target.gold = target.gold + amount
        ctx:send("당신은 " .. target.name .. "에게 " .. format_number(amount) .. "냥을 주었습니다.")
        ctx:send_to(target, ch.name .. "이(가) 당신에게 " .. format_number(amount) .. "냥을 주었습니다.")
        ctx:send_room(ch.name .. "이(가) " .. target.name .. "에게 " .. format_number(amount) .. "냥을 주었습니다.")
        return
    end

    -- Item give
    local item = ctx:find_obj_inv(item_kw)
    if not item then
        ctx:send("당신 소지품에는 그런것이 없습니다")
        return
    end

    local target = ctx:find_char(target_name)
    if not target then
        target = ctx:find_player(target_name)
    end
    if not target then
        ctx:send("그런 사람은 여기 없어요!")
        return
    end
    if target == ch then
        ctx:send("자기자신에게 물건을 주시다뇨?")
        return
    end

    ctx:obj_from_char(item)
    ctx:obj_to_char(item, target)
    ctx:send("당신은 " .. target.name .. "에게 " .. item.name .. "을(를) 줍니다.")
    ctx:send_to(target, ch.name .. "이(가) 당신에게 " .. item.name .. "을(를) 줍니다.")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "에게 " .. item.name .. "을(를) 줍니다.")
end)

-- ── 마셔 (drink/eat merged) / 먹어 (alias) ─────────────────────
-- Original: drink() in magic1.c — both 먹어 and 마셔 map to same function, POTION/FOOD/DRINK
register_command("마셔", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("먹을 것의 이름을 다시한번 확인해 보세요?")
        return
    end

    local item = ctx:find_obj_inv(args)
    if not item then
        ctx:send("잘못된 이름인것 같습니다.")
        return
    end

    -- Only POTION/FOOD/DRINK type items can be consumed in 3eyes
    if item.proto.item_type ~= "potion" and item.proto.item_type ~= "food"
       and item.proto.item_type ~= "drink" then
        ctx:send("그것은 먹을수 없는 물건이군요.")
        return
    end

    -- Apply spell effects from potion values
    local vals = item.proto.values or {}
    local spell_id = vals.spell1 or vals.spell or vals[1]
    if spell_id and tonumber(spell_id) then
        spell_id = tonumber(spell_id)
        if spell_id > 0 then
            ctx:apply_spell_buff(ch, spell_id, 20)
        end
    end

    -- HP restore from food
    local hp_gain = vals.hp or vals.heal or 0
    if tonumber(hp_gain) and tonumber(hp_gain) > 0 then
        ctx:heal(ch, tonumber(hp_gain))
    end

    ctx:obj_from_char(item)
    ctx:send("당신은 " .. item.name .. "을(를) 먹었습니다.")
    ctx:send_room(ch.name .. "이(가) " .. item.name .. "을(를) 먹었습니다.")
end)
register_command("먹어", function(ctx, args) ctx:call_command("마셔", args or "") end)

-- ── 입어 (wear) / 착용 (alias) ─────────────────────────────────
register_command("입어", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 착용하시겠습니까?")
        return
    end
    if args == "all" or args == "전부" then
        ctx:wear_all()
        return
    end
    local item = ctx:find_inv_item(args)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end
    local slot = ctx:wear_item(item)
    if slot then
        local slot_name = SLOT_NAMES[slot] or ("슬롯 " .. slot)
        ctx:send(item.name .. "을(를) <" .. slot_name .. ">에 착용합니다.")
    end
end)
register_command("착용", function(ctx, args) ctx:call_command("입어", args or "") end)

-- ── 무장 (wield) ────────────────────────────────────────────────
register_command("무장", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 들으시겠습니까?")
        return
    end
    local item = ctx:find_inv_item(args)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end
    local slot = ctx:wield_item(item)
    if slot then
        ctx:send(item.name .. "을(를) 무기로 장비합니다.")
    end
end)

-- ── 벗어 (remove) ──────────────────────────────────────────────
register_command("벗어", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 벗으시겠습니까?")
        return
    end
    local item = ctx:find_equip_item(args)
    if not item then
        ctx:send("그런 장비를 착용하고 있지 않습니다.")
        return
    end
    ctx:remove_item(item)
    ctx:send(item.name .. "을(를) 벗습니다.")
end)

-- ── 쥐어 / 잡아 (cmdno=12, hold) — stub
register_command("쥐어", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 쥐시겠습니까?")
        return
    end
    -- hold는 wield와 유사하지만 보조무기/방패 슬롯 사용
    local item = ctx:find_inv_item(args)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end
    local slot = ctx:hold_item(item)
    if slot then
        ctx:send(item.name .. "을(를) 쥡니다.")
    end
end)
register_command("잡아", function(ctx, args) ctx:call_command("쥐어", args or "") end)
