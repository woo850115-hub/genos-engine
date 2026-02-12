-- shops.lua — tbaMUD shop commands (buy, sell, list, appraise)

local ITEM_TYPE_NAMES = {
    [1]="빛", [2]="두루마리", [3]="지팡이", [4]="막대기", [5]="무기",
    [6]="방화", [7]="투사체", [8]="보물", [9]="갑옷", [10]="물약",
    [11]="쓸모없음", [12]="기타", [13]="쓰레기", [14]="컨테이너",
    [15]="메모", [16]="음료", [17]="열쇠", [18]="음식",
    [19]="돈", [20]="배", [21]="샘물",
}

-- ── buy ─────────────────────────────────────────────────────────

register_command("buy", function(ctx, args)
    local shop, keeper = ctx:find_shop()
    if not shop then
        ctx:send("여기에는 상점이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send(keeper.name .. "이(가) '뭘 사시겠습니까?'라고 말합니다.")
        return
    end

    local ch = ctx.char
    if not ch then return end
    local target_kw = args:lower()

    -- Search shop's permanent selling items
    local selling = shop.selling_items
    if selling then
        for i = 1, #selling do
            local item_vnum = selling[i]
            if item_vnum then
                local obj = ctx:create_obj(item_vnum)
                if obj and obj.proto.keywords:lower():find(target_kw, 1, true) then
                    local price = math.floor(obj.proto.cost * shop.profit_buy)
                    if ch.gold < price then
                        ctx:send(keeper.name .. "이(가) '그건 " .. price ..
                                 " 골드입니다. 돈이 부족합니다.'라고 말합니다.")
                        return
                    end
                    ch.gold = ch.gold - price
                    ctx:obj_to_char(obj, ch)
                    ctx:send("{bright_yellow}" .. obj.proto.short_description ..
                             "을(를) " .. price .. " 골드에 구입했습니다.{reset}")
                    return
                end
            end
        end
    end

    -- Check keeper's inventory
    local keeper_inv = ctx:get_char_inventory(keeper)
    for i = 1, #keeper_inv do
        local obj = keeper_inv[i]
        if obj and obj.proto.keywords:lower():find(target_kw, 1, true) then
            local price = math.floor(obj.proto.cost * shop.profit_buy)
            if ch.gold < price then
                ctx:send(keeper.name .. "이(가) '돈이 부족합니다.'라고 말합니다.")
                return
            end
            ctx:obj_from_char(obj)
            ch.gold = ch.gold - price
            ctx:obj_to_char(obj, ch)
            ctx:send("{bright_yellow}" .. obj.name .. "을(를) " .. price ..
                     " 골드에 구입했습니다.{reset}")
            return
        end
    end

    ctx:send(keeper.name .. "이(가) '그런 물건은 없습니다.'라고 말합니다.")
end, "사")

-- ── sell ────────────────────────────────────────────────────────

register_command("sell", function(ctx, args)
    local shop, keeper = ctx:find_shop()
    if not shop then
        ctx:send("여기에는 상점이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send(keeper.name .. "이(가) '뭘 파시겠습니까?'라고 말합니다.")
        return
    end

    local ch = ctx.char
    if not ch then return end
    local obj = ctx:find_obj_inv(args)
    if not obj then
        ctx:send(keeper.name .. "이(가) '그런 물건을 가지고 있지 않습니다.'라고 말합니다.")
        return
    end

    local price = math.floor(obj.proto.cost * shop.profit_sell)
    if price < 1 then price = 1 end
    ctx:obj_from_char(obj)
    ch.gold = ch.gold + price
    ctx:send("{bright_yellow}" .. obj.name .. "을(를) " .. price .. " 골드에 판매했습니다.{reset}")
end, "팔")

-- ── list ────────────────────────────────────────────────────────

register_command("list", function(ctx, args)
    local shop, keeper = ctx:find_shop()
    if not shop then
        ctx:send("여기에는 상점이 없습니다.")
        return
    end

    local lines = {"{bright_cyan}" .. keeper.name .. "의 상점 물품 목록:{reset}"}
    local idx = 1

    -- Permanent stock items
    local selling = shop.selling_items
    if selling then
        for i = 1, #selling do
            local item_vnum = selling[i]
            if item_vnum then
                local obj = ctx:create_obj(item_vnum)
                if obj then
                    local price = math.floor(obj.proto.cost * shop.profit_buy)
                    local type_name = ITEM_TYPE_NAMES[obj.proto.item_type] or "기타"
                    table.insert(lines, "  " .. idx .. ". " ..
                                 obj.proto.short_description .. " [" .. type_name ..
                                 "] — " .. price .. " 골드 (무한)")
                    idx = idx + 1
                end
            end
        end
    end

    -- Keeper's inventory
    local keeper_inv = ctx:get_char_inventory(keeper)
    for i = 1, #keeper_inv do
        local obj = keeper_inv[i]
        if obj then
            local price = math.floor(obj.proto.cost * shop.profit_buy)
            local type_name = ITEM_TYPE_NAMES[obj.proto.item_type] or "기타"
            table.insert(lines, "  " .. idx .. ". " .. obj.name ..
                         " [" .. type_name .. "] — " .. price .. " 골드")
            idx = idx + 1
        end
    end

    if idx == 1 then
        table.insert(lines, "  (판매 중인 물건이 없습니다)")
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "목록")

-- ── appraise ────────────────────────────────────────────────────

register_command("appraise", function(ctx, args)
    local shop, keeper = ctx:find_shop()
    if not shop then
        ctx:send("여기에는 상점이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("뭘 감정하시겠습니까?")
        return
    end

    local obj = ctx:find_obj_inv(args)
    if not obj then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end

    local price = math.floor(obj.proto.cost * shop.profit_sell)
    if price < 1 then price = 1 end
    ctx:send(keeper.name .. "이(가) '" .. obj.name .. "은(는) " .. price ..
             " 골드에 사겠습니다.'라고 말합니다.")
end, "감정")
