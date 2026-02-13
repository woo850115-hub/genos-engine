-- shops.lua — 3eyes 상점 명령어 (원본 cmdlist 기반)
-- 구매, 팔아, 품목, 가치/가격, 수리, 교환

-- ══════════════════════════════════════════════════════════════════
-- buy — 물건 구매 (command7.c buy, 46-69)
-- ══════════════════════════════════════════════════════════════════

register_command("구매", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 구매하시겠습니까? (품목 명령으로 목록 확인)")
        return
    end
    local shop = ctx:get_shop()
    if not shop then
        ctx:send("여기에는 상점이 없습니다.")
        return
    end
    local ch = ctx.char

    -- Find item by name or number in shop
    local item = ctx:find_shop_item(args)
    if not item then
        ctx:send("상점에 그런 물건은 없습니다.")
        return
    end

    local price = ctx:get_buy_price(item)
    if ch.gold < price then
        ctx:send("{yellow}골드가 부족합니다. (가격: " .. price .. "원, 소지금: " .. ch.gold .. "원){reset}")
        return
    end

    local obj = ctx:buy_item(item)
    if not obj then
        ctx:send("{yellow}구매에 실패했습니다.{reset}")
        return
    end

    ch.gold = ch.gold - price
    ctx:send("{green}" .. obj.name .. "을(를) " .. price .. "원에 구매했습니다.{reset}")
    ctx:send_room(ch.name .. "이(가) " .. obj.name .. "을(를) 구매합니다.")
end)

register_command("buy", function(ctx, args)
    ctx:call_command("구매", args or "")
end)

-- ══════════════════════════════════════════════════════════════════
-- sell — 물건 판매 (command7.c sell, 174-225)
-- Original: sell price = value/2, max 100000 gold
-- ══════════════════════════════════════════════════════════════════

local SELL_MAX = 100000  -- command7.c:206

register_command("팔아", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 판매하시겠습니까?")
        return
    end
    local shop = ctx:get_shop()
    if not shop then
        ctx:send("여기에는 상점이 없습니다.")
        return
    end
    local ch = ctx.char
    local item = ctx:find_inv_item(args)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end

    local price = ctx:get_sell_price(item)
    price = math.min(price, SELL_MAX)
    if price <= 0 then
        ctx:send("{yellow}그 물건은 살 수 없는 물건입니다.{reset}")
        return
    end

    ctx:sell_item(item)
    ch.gold = ch.gold + price
    ctx:send("{green}" .. item.name .. "을(를) " .. price .. "원에 팔았습니다.{reset}")
    ctx:send_room(ch.name .. "이(가) " .. item.name .. "을(를) 판매합니다.")
end)

-- ══════════════════════════════════════════════════════════════════
-- list — 상점 목록 (command7.c list, 70-93)
-- ══════════════════════════════════════════════════════════════════

register_command("품목", function(ctx, args)
    local shop = ctx:get_shop()
    if not shop then
        ctx:send("여기에는 상점이 없습니다.")
        return
    end
    local items = ctx:get_shop_items()
    if not items then
        ctx:send("판매 중인 물건이 없습니다.")
        return
    end

    local lines = {
        "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        "{bright_cyan}  번호   물품명                      가격{reset}",
        "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
    }

    local idx = 0
    if items.values then
        for item in items.values() do
            idx = idx + 1
            local price = ctx:get_buy_price(item)
            local name = item.name or "???"
            lines[#lines + 1] = string.format("  %3d)  %-24s %8d원", idx, name, price)
        end
    else
        for i = 0, 100 do
            local ok, item = pcall(function() return items[i] end)
            if not ok or not item then break end
            idx = idx + 1
            local price = ctx:get_buy_price(item)
            local name = item.name or "???"
            lines[#lines + 1] = string.format("  %3d)  %-24s %8d원", idx, name, price)
        end
    end

    if idx == 0 then
        ctx:send("판매 중인 물건이 없습니다.")
    else
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
    end
end)

-- ══════════════════════════════════════════════════════════════════
-- value — 판매 예상가 (command7.c value, 227-245)
-- pawn: 50% of cost, repair: 25% of cost
-- ══════════════════════════════════════════════════════════════════

register_command("가치", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇의 가치를 알아보시겠습니까?")
        return
    end
    local shop = ctx:get_shop()
    if not shop then
        ctx:send("여기에는 상점이 없습니다.")
        return
    end
    local item = ctx:find_inv_item(args)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end

    local sell_price = ctx:get_sell_price(item)
    sell_price = math.min(sell_price, SELL_MAX)
    local cost = (item.proto and item.proto.cost) or 0

    ctx:send("{cyan}━━ 물품 가치 ━━{reset}")
    ctx:send("  물품: " .. item.name)
    ctx:send("  원가: " .. cost .. "원")
    ctx:send("  판매가: " .. sell_price .. "원")

    -- Show repair cost if weapon
    local ok_ws, ws = pcall(function() return item.proto.wear_slots end)
    local is_weapon = false
    if ok_ws and ws then
        for _, s in ipairs(ws) do
            if s == 16 or s == "weapon" or s == "wield" then
                is_weapon = true; break
            end
        end
    end
    if is_weapon then
        local ok_shots, shots = pcall(function() return item.shots_remaining end)
        local ok_max, smax = pcall(function() return item.proto.shots_max end)
        if ok_shots and shots and ok_max and smax and smax > 0 then
            local repair_cost = math.floor(cost * (smax - shots) / smax / 4)
            ctx:send("  수리비: " .. repair_cost .. "원 (내구도: " .. shots .. "/" .. smax .. ")")
        end
    end
end)

register_command("가격", function(ctx, args)
    ctx:call_command("가치", args or "")
end)

-- ══════════════════════════════════════════════════════════════════
-- repair — 무기 수리 (command7.c repair, 247-280)
-- RREPAI room flag required
-- ══════════════════════════════════════════════════════════════════

register_command("수리", function(ctx, args)
    if not te_room_has_flag(ctx, 9) then  -- RREPAI
        ctx:send("여기에서는 수리할 수 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("무엇을 수리하시겠습니까?")
        return
    end

    local ch = ctx.char
    local item = ctx:find_inv_item(args)
    if not item then
        item = ctx:find_equip_item(args)
    end
    if not item or not item.proto then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end

    -- Must be a weapon
    local ok_ws, ws = pcall(function() return item.proto.wear_slots end)
    local is_weapon = false
    if ok_ws and ws then
        for _, s in ipairs(ws) do
            if s == 16 or s == "weapon" or s == "wield" then
                is_weapon = true; break
            end
        end
    end
    if not is_weapon then
        ctx:send("{yellow}무기만 수리할 수 있습니다.{reset}")
        return
    end

    local ok_shots, shots = pcall(function() return item.shots_remaining end)
    local ok_max, smax = pcall(function() return item.proto.shots_max end)
    if not ok_shots or not shots or not ok_max or not smax or smax <= 0 then
        ctx:send("{yellow}이 무기는 수리가 필요하지 않습니다.{reset}")
        return
    end
    if shots >= smax then
        ctx:send("{yellow}이미 최상의 상태입니다.{reset}")
        return
    end

    -- Repair cost: cost * (max - cur) / max / 4 (command7.c:265)
    local cost = (item.proto.cost or 0)
    local repair_cost = math.floor(cost * (smax - shots) / smax / 4)
    repair_cost = math.max(1, repair_cost)

    if ch.gold < repair_cost then
        ctx:send("{yellow}골드가 부족합니다. (수리비: " .. repair_cost .. "원){reset}")
        return
    end

    ch.gold = ch.gold - repair_cost
    pcall(function() item.shots_remaining = smax end)
    ctx:send("{green}" .. item.name .. "을(를) " .. repair_cost ..
        "원에 수리했습니다. (내구도: " .. smax .. "/" .. smax .. "){reset}")
end)

-- ══════════════════════════════════════════════════════════════════
-- trade — 아이템 교환 (command7.c trade, 282-340)
-- ══════════════════════════════════════════════════════════════════

register_command("교환", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: trade <대상> <내아이템> <상대아이템>")
        return
    end
    local ch = ctx.char

    local target_name, my_item_name, their_item_name = args:match("^(%S+)%s+(%S+)%s+(%S+)$")
    if not target_name then
        ctx:send("사용법: trade <대상> <내아이템> <상대아이템>")
        return
    end

    local target = ctx:find_char(target_name)
    if not target or not target.session then
        ctx:send("대상 플레이어를 찾을 수 없습니다. (같은 방에 있어야 합니다)")
        return
    end
    if target == ch then
        ctx:send("자기 자신과 교환할 수 없습니다.")
        return
    end

    local my_item = ctx:find_inv_item(my_item_name)
    if not my_item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end

    -- Find target's item
    local their_item = nil
    local kw = their_item_name:lower()
    local inv = ctx:get_char_inventory(target)
    if inv then
        if inv.values then
            for obj in inv.values() do
                if obj.proto and obj.proto.keywords:lower():find(kw, 1, true) then
                    their_item = obj; break
                end
            end
        else
            for i = 0, 100 do
                local ok, obj = pcall(function() return inv[i] end)
                if not ok or not obj then break end
                if obj.proto and obj.proto.keywords:lower():find(kw, 1, true) then
                    their_item = obj; break
                end
            end
        end
    end
    if not their_item then
        ctx:send("{yellow}" .. target.name .. "은(는) 그런 물건을 가지고 있지 않습니다.{reset}")
        return
    end

    -- Execute trade: swap items
    -- Remove my_item from my inventory
    ctx:obj_from_char(my_item)
    -- Remove their_item from target inventory (Python list interop)
    pcall(function()
        local found_idx = nil
        for i = 0, 100 do
            local ok, obj = pcall(function() return target.inventory[i] end)
            if not ok or obj == nil then break end
            if obj == their_item then found_idx = i; break end
        end
        if found_idx ~= nil then
            target.inventory:pop(found_idx)
        end
        their_item.carried_by = nil
    end)

    -- Give items
    ctx:obj_to_char(their_item, ch)
    ctx:obj_to_char(my_item, target)

    ctx:send("{green}" .. my_item.name .. "을(를) " .. target.name ..
        "의 " .. their_item.name .. "과(와) 교환했습니다.{reset}")
    ctx:send_to(target, "{green}" .. ch.name .. "이(가) " ..
        their_item.name .. "을(를) " .. my_item.name .. "과(와) 교환합니다.{reset}")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "과(와) 물건을 교환합니다.")
end)
