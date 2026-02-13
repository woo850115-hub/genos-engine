-- economy.lua — 3eyes economy system: Bank + Auction
-- Original: bank.c (deposit/withdraw/locker/transfer), kyk1.c (auction/bid)

-- ══════════════════════════════════════════════════════════════════
-- Bank System — bank.c (RBANK room flag required)
-- player_data keys: "bank_gold" (int), "bank_items" (list of vnum)
-- ══════════════════════════════════════════════════════════════════

local BANK_LOCKER_MAX = 10     -- max items in bank locker
local GOLD_MAX = 2000000000    -- 20억 limit (bank.c:284)

-- ── 입금 — 은행 입금 (bank.c:272-310) ───────────────────────────
register_command("입금", function(ctx, args)
    if not te_room_has_flag(ctx, 6) then  -- RBANK
        ctx:send("여기에는 은행이 없습니다.")
        return
    end
    local ch = ctx.char
    if not args or args == "" then
        ctx:send("얼마를 입금하시겠습니까? (입금 <금액> / 입금 전부)")
        return
    end

    local amount
    if args == "전부" or args == "all" then
        amount = ch.gold
    else
        amount = tonumber(args)
    end

    if not amount or amount <= 0 then
        ctx:send("올바른 금액을 입력하세요.")
        return
    end
    if amount > ch.gold then
        ctx:send("{yellow}소지금이 부족합니다.{reset}")
        return
    end

    local bank_gold = ctx:get_player_data("bank_gold") or 0
    if bank_gold + amount > GOLD_MAX then
        ctx:send("{yellow}은행에 더 이상 보관할 수 없습니다. (한도: 20억){reset}")
        return
    end

    ch.gold = ch.gold - amount
    ctx:set_player_data("bank_gold", bank_gold + amount)
    ctx:send("{green}" .. amount .. "원을 입금했습니다.{reset}")
    ctx:send("잔고: " .. (bank_gold + amount) .. "원")
end)

-- ── 출금 — 은행 출금 (bank.c:318-355) ─────────────────────────
register_command("출금", function(ctx, args)
    if not te_room_has_flag(ctx, 6) then
        ctx:send("여기에는 은행이 없습니다.")
        return
    end
    local ch = ctx.char
    if not args or args == "" then
        ctx:send("얼마를 출금하시겠습니까? (출금 <금액> / 출금 전부)")
        return
    end

    local bank_gold = ctx:get_player_data("bank_gold") or 0
    local amount
    if args == "전부" or args == "all" then
        amount = bank_gold
    else
        amount = tonumber(args)
    end

    if not amount or amount <= 0 then
        ctx:send("올바른 금액을 입력하세요.")
        return
    end
    if amount > bank_gold then
        ctx:send("{yellow}잔고가 부족합니다. (잔고: " .. bank_gold .. "원){reset}")
        return
    end
    if ch.gold + amount > GOLD_MAX then
        ctx:send("{yellow}소지금 한도 초과입니다.{reset}")
        return
    end

    ctx:set_player_data("bank_gold", bank_gold - amount)
    ch.gold = ch.gold + amount
    ctx:send("{green}" .. amount .. "원을 출금했습니다.{reset}")
    ctx:send("잔고: " .. (bank_gold - amount) .. "원")
end)

-- ── 잔액 — 잔고확인 (bank.c:135-150) ──────────────────────────
register_command("잔액", function(ctx, args)
    if not te_room_has_flag(ctx, 6) then
        ctx:send("여기에는 은행이 없습니다.")
        return
    end
    local bank_gold = ctx:get_player_data("bank_gold") or 0
    ctx:send("{cyan}━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send("{cyan}  은행 잔고: {bright_white}" .. bank_gold .. "원{reset}")
    ctx:send("{cyan}━━━━━━━━━━━━━━━━━━{reset}")
end)

-- ── 보관물 — 보관함 (bank.c:155-270) ─────────────────────────────
register_command("보관물", function(ctx, args)
    if not te_room_has_flag(ctx, 6) then
        ctx:send("여기에는 은행이 없습니다.")
        return
    end
    local ch = ctx.char

    if not args or args == "" then
        -- Show locker contents
        local items = ctx:get_player_data("bank_items") or {}
        if type(items) ~= "table" then items = {} end
        local count = 0
        -- Count items (Lua table from Python list)
        if items.values then
            for _ in items.values() do count = count + 1 end
        else
            for _ in pairs(items) do count = count + 1 end
        end
        if count == 0 then
            ctx:send("보관함이 비어 있습니다.")
            return
        end
        local lines = {"{cyan}━━ 은행 보관함 ━━{reset}"}
        local idx = 0
        local iter = items.values and items.values() or ipairs(items)
        if items.values then
            for v in items.values() do
                idx = idx + 1
                local vnum = tonumber(v) or 0
                local obj = ctx:create_obj(vnum)
                local name = obj and obj.name or ("아이템#" .. vnum)
                lines[#lines + 1] = string.format("  %2d) %s", idx, name)
            end
        else
            for _, v in ipairs(items) do
                idx = idx + 1
                local vnum = tonumber(v) or 0
                local obj = ctx:create_obj(vnum)
                local name = obj and obj.name or ("아이템#" .. vnum)
                lines[#lines + 1] = string.format("  %2d) %s", idx, name)
            end
        end
        lines[#lines + 1] = "{cyan}(" .. count .. "/" .. BANK_LOCKER_MAX .. "){reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    local subcmd, target = args:match("^(%S+)%s*(.*)$")
    subcmd = subcmd:lower()

    if subcmd == "맡기기" or subcmd == "store" then
        if not target or target == "" then
            ctx:send("무엇을 맡기시겠습니까?")
            return
        end
        local item = ctx:find_inv_item(target)
        if not item then
            ctx:send("그런 물건을 가지고 있지 않습니다.")
            return
        end
        local items = ctx:get_player_data("bank_items") or {}
        if type(items) ~= "table" then items = {} end
        -- Convert to plain Lua table
        local plain = {}
        if items.values then
            for v in items.values() do plain[#plain + 1] = v end
        else
            for _, v in ipairs(items) do plain[#plain + 1] = v end
        end
        if #plain >= BANK_LOCKER_MAX then
            ctx:send("{yellow}보관함이 가득 찼습니다. (최대 " .. BANK_LOCKER_MAX .. "개){reset}")
            return
        end
        plain[#plain + 1] = item.proto.vnum
        ctx:set_player_data("bank_items", plain)
        ctx:obj_from_char(item)
        ctx:send("{green}" .. item.name .. "을(를) 보관함에 맡겼습니다.{reset}")

    elseif subcmd == "찾기" or subcmd == "retrieve" then
        if not target or target == "" then
            ctx:send("몇 번 아이템을 찾으시겠습니까?")
            return
        end
        local idx = tonumber(target)
        local items = ctx:get_player_data("bank_items") or {}
        if type(items) ~= "table" then items = {} end
        local plain = {}
        if items.values then
            for v in items.values() do plain[#plain + 1] = v end
        else
            for _, v in ipairs(items) do plain[#plain + 1] = v end
        end
        if not idx or idx < 1 or idx > #plain then
            ctx:send("올바른 번호를 입력하세요. (1-" .. #plain .. ")")
            return
        end
        local vnum = plain[idx]
        table.remove(plain, idx)
        ctx:set_player_data("bank_items", plain)
        local obj = ctx:load_obj(vnum)
        if obj then
            ctx:send("{green}" .. obj.name .. "을(를) 보관함에서 찾았습니다.{reset}")
        else
            ctx:send("아이템을 꺼내는데 실패했습니다.")
        end
    else
        ctx:send("사용법: 보관물 / 보관물 맡기기 <아이템> / 보관물 찾기 <번호>")
    end
end)

-- ── 송금 — 온라인 송금 (comm11.c:422-471) ────────────────────
register_command("송금", function(ctx, args)
    if not te_room_has_flag(ctx, 6) then
        ctx:send("여기에는 은행이 없습니다.")
        return
    end
    local ch = ctx.char
    if not args or args == "" then
        ctx:send("사용법: 송금 <대상> <금액>")
        return
    end

    local target_name, amount_str = args:match("^(%S+)%s+(%S+)$")
    if not target_name or not amount_str then
        ctx:send("사용법: 송금 <대상> <금액>")
        return
    end

    local amount = tonumber(amount_str)
    if not amount or amount <= 0 then
        ctx:send("올바른 금액을 입력하세요.")
        return
    end

    local bank_gold = ctx:get_player_data("bank_gold") or 0
    if amount > bank_gold then
        ctx:send("{yellow}잔고가 부족합니다. (잔고: " .. bank_gold .. "원){reset}")
        return
    end

    -- Find online target
    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("{yellow}" .. target_name .. "은(는) 접속 중이 아닙니다.{reset}")
        return
    end
    if target == ch then
        ctx:send("자기 자신에게 송금할 수 없습니다.")
        return
    end

    -- Check target bank gold limit
    local target_bank = 0
    if target.session then
        local ok, tpd = pcall(function() return target.session.player_data end)
        if ok and tpd then
            target_bank = tpd.bank_gold or 0
        end
    end
    if target_bank + amount > GOLD_MAX then
        ctx:send("{yellow}상대방의 은행 한도 초과입니다.{reset}")
        return
    end

    -- Execute transfer
    ctx:set_player_data("bank_gold", bank_gold - amount)
    if target.session then
        pcall(function()
            target.session.player_data.bank_gold = (target.session.player_data.bank_gold or 0) + amount
        end)
    end

    ctx:send("{green}" .. target.name .. "에게 " .. amount .. "원을 송금했습니다.{reset}")
    ctx:send("잔고: " .. (bank_gold - amount) .. "원")
    ctx:send_to(target, "{green}" .. ch.name .. "이(가) " .. amount .. "원을 송금했습니다.{reset}")
end)

-- ══════════════════════════════════════════════════════════════════
-- Auction System — kyk1.c:72-290
-- Global state (runtime only — resets on server restart)
-- ══════════════════════════════════════════════════════════════════

-- Auction global state (module-level)
local auction_state = {
    active = false,
    item_vnum = 0,
    item_name = "",
    seller_name = "",
    bidder_name = "",
    price = 0,
    min_bid = 1000,         -- minimum bid increment
}

-- Broadcast auction message to all players
local function broadcast_auction(ctx, msg)
    ctx:send_all("{bright_yellow}[경매] " .. msg .. "{reset}")
end

register_command("경매", function(ctx, args)
    local ch = ctx.char
    if not args or args == "" then
        -- Show current auction status
        if not auction_state.active then
            ctx:send("{yellow}현재 진행 중인 경매가 없습니다.{reset}")
        else
            local lines = {"{bright_yellow}━━ 현재 경매 ━━{reset}"}
            lines[#lines + 1] = "  물품: " .. auction_state.item_name
            lines[#lines + 1] = "  판매자: " .. auction_state.seller_name
            if auction_state.bidder_name ~= "" then
                lines[#lines + 1] = "  최고 입찰자: " .. auction_state.bidder_name
                lines[#lines + 1] = "  현재가: " .. auction_state.price .. "원"
            else
                lines[#lines + 1] = "  시작가: " .. auction_state.price .. "원"
            end
            ctx:send(table.concat(lines, "\r\n"))
        end
        return
    end

    local subcmd, rest = args:match("^(%S+)%s*(.*)$")
    subcmd = subcmd:lower()

    -- ── 경매 시작 <item> <price> ─────────────────────────────
    if subcmd == "시작" or subcmd == "start" then
        if auction_state.active then
            ctx:send("{yellow}이미 경매가 진행 중입니다.{reset}")
            return
        end
        local item_name, price_str = rest:match("^(%S+)%s+(%S+)$")
        if not item_name or not price_str then
            ctx:send("사용법: 경매 시작 <아이템> <시작가>")
            return
        end
        local price = tonumber(price_str)
        if not price or price < 100 then
            ctx:send("시작가는 최소 100원 이상이어야 합니다.")
            return
        end
        local item = ctx:find_inv_item(item_name)
        if not item then
            ctx:send("그런 물건을 가지고 있지 않습니다.")
            return
        end
        -- Remove item from inventory
        ctx:obj_from_char(item)

        auction_state.active = true
        auction_state.item_vnum = item.proto.vnum
        auction_state.item_name = item.name
        auction_state.seller_name = ch.name
        auction_state.bidder_name = ""
        auction_state.price = price

        broadcast_auction(ctx, ch.name .. "이(가) " .. item.name ..
            "을(를) " .. price .. "원에 경매를 시작합니다!")

    -- ── 경매 취소 ───────────────────────────────────────────
    elseif subcmd == "취소" or subcmd == "cancel" then
        if not auction_state.active then
            ctx:send("{yellow}진행 중인 경매가 없습니다.{reset}")
            return
        end
        if auction_state.seller_name ~= ch.name then
            ctx:send("{yellow}본인의 경매만 취소할 수 있습니다.{reset}")
            return
        end
        if auction_state.bidder_name ~= "" then
            ctx:send("{yellow}이미 입찰자가 있어 취소할 수 없습니다.{reset}")
            return
        end
        -- Return item to seller
        local obj = ctx:load_obj(auction_state.item_vnum)
        if obj then
            ctx:send("{green}" .. auction_state.item_name .. "이(가) 반환됩니다.{reset}")
        end
        broadcast_auction(ctx, ch.name .. "이(가) 경매를 취소합니다.")
        auction_state.active = false

    -- ── 경매 확정 / sold ───────────────────────────────────
    elseif subcmd == "확정" or subcmd == "sold" or subcmd == "confirm" then
        if not auction_state.active then
            ctx:send("{yellow}진행 중인 경매가 없습니다.{reset}")
            return
        end
        if auction_state.seller_name ~= ch.name then
            ctx:send("{yellow}본인의 경매만 확정할 수 있습니다.{reset}")
            return
        end
        if auction_state.bidder_name == "" then
            ctx:send("{yellow}아직 입찰자가 없습니다.{reset}")
            return
        end

        -- Find bidder
        local bidder = ctx:find_player(auction_state.bidder_name)
        if not bidder then
            ctx:send("{yellow}낙찰자(" .. auction_state.bidder_name .. ")가 접속 중이 아닙니다.{reset}")
            return
        end

        -- Transfer gold: bidder pays, seller receives
        local price = auction_state.price
        bidder.gold = bidder.gold - price
        ch.gold = ch.gold + price

        -- Give item to bidder
        local obj = nil
        pcall(function()
            obj = ctx:create_obj(auction_state.item_vnum)
            if obj then
                ctx:obj_to_char(obj, bidder)
            end
        end)

        broadcast_auction(ctx, auction_state.item_name .. "이(가) " ..
            auction_state.bidder_name .. "에게 " .. price .. "원에 낙찰됩니다!")

        ctx:send_to(bidder, "{bright_green}" .. auction_state.item_name ..
            "을(를) " .. price .. "원에 낙찰 받았습니다!{reset}")

        auction_state.active = false
    else
        ctx:send("사용법: 경매 / 경매 시작 <아이템> <시작가> / 경매 취소 / 경매 확정")
    end
end)

-- ── 입찰 — 입찰 (kyk1.c:180-240) ──────────────────────────────────
register_command("입찰", function(ctx, args)
    local ch = ctx.char
    if not auction_state.active then
        ctx:send("{yellow}진행 중인 경매가 없습니다.{reset}")
        return
    end
    if auction_state.seller_name == ch.name then
        ctx:send("{yellow}자기 경매에 입찰할 수 없습니다.{reset}")
        return
    end

    local amount = tonumber(args)
    if not amount then
        ctx:send("사용법: 입찰 <금액>")
        return
    end

    local min_next = auction_state.price + auction_state.min_bid
    if amount < min_next then
        ctx:send("{yellow}최소 " .. min_next .. "원 이상 입찰해야 합니다. (현재가 " ..
            auction_state.price .. " + 최소증가 " .. auction_state.min_bid .. "){reset}")
        return
    end

    if amount > ch.gold then
        ctx:send("{yellow}골드가 부족합니다. (소지금: " .. ch.gold .. "원){reset}")
        return
    end

    -- Refund previous bidder's hold (we don't hold gold, just track)
    auction_state.bidder_name = ch.name
    auction_state.price = amount

    broadcast_auction(ctx, ch.name .. "이(가) " .. auction_state.item_name ..
        "에 " .. amount .. "원을 입찰합니다!")
end)
