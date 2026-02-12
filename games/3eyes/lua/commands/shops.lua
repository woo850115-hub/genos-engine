-- shops.lua — 3eyes shop commands (buy, sell, list, appraise)

register_command("buy", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 구매하시겠습니까?")
        return
    end
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

    local target_name = args:lower()
    for i = 0, 100 do
        local ok, item = pcall(function() return items[i] end)
        if not ok or not item then break end
        local name_lower = item.name:lower()
        if name_lower:find(target_name, 1, true) then
            local price = ctx:get_buy_price(item)
            if ctx.char.gold < price then
                ctx:send("골드가 부족합니다. (" .. price .. "원 필요)")
                return
            end
            ctx.char.gold = ctx.char.gold - price
            local obj = ctx:buy_item(item)
            if obj then
                ctx:send("{green}" .. obj.name .. "을(를) " .. price .. "원에 구입했습니다.{reset}")
            end
            return
        end
    end
    ctx:send("그런 물건은 팔지 않습니다.")
end, "구매")

register_command("sell", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 판매하시겠습니까?")
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
    local price = ctx:get_sell_price(item)
    if price <= 0 then
        ctx:send("그 물건은 팔 수 없습니다.")
        return
    end
    ctx:sell_item(item)
    ctx.char.gold = ctx.char.gold + price
    ctx:send("{green}" .. item.name .. "을(를) " .. price .. "원에 팔았습니다.{reset}")
end, "판매")

register_command("list", function(ctx, args)
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
    local lines = {"{bright_cyan}-- 판매 목록 --{reset}"}
    for i = 0, 100 do
        local ok, item = pcall(function() return items[i] end)
        if not ok or not item then break end
        local price = ctx:get_buy_price(item)
        lines[#lines + 1] = string.format("  %3d) %-20s %8d원",
            i + 1, item.name, price)
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "목록")

register_command("appraise", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 감정하시겠습니까?")
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
    local price = ctx:get_sell_price(item)
    ctx:send(item.name .. "의 판매가: " .. price .. "원")
end, "감정")
