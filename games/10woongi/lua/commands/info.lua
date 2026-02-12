-- info.lua — 10woongi info commands (score, who, inventory, equipment, consider)
-- Based on lib/명령어/플레이어/{상태,누구,가진거,장비}.c

-- ── Score (상태.c format — box-drawing table) ──────────────────

register_command("score", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local cls_name = CLASS_NAMES[ch.class_id] or "무림인"
    local ext = ch.extensions or {}
    local ok_stats, wstats = pcall(function() return ext.stats end)
    wstats = (ok_stats and wstats) or {}
    local ok_fac, faction = pcall(function() return ext.faction end)
    faction = (ok_fac and faction and tostring(faction) ~= "") and tostring(faction) or "낭인"

    local function g(key)
        local ok2, v = pcall(function() return wstats[key] end)
        return (ok2 and v) and tonumber(v) or 13
    end

    local stamina = g("stamina")
    local agility = g("agility")
    local wisdom  = g("wisdom")
    local bone    = g("bone")
    local inner   = g("inner")
    local spirit  = g("spirit")

    local ok_h, history_id = pcall(function() return ext.history end)
    history_id = (ok_h and history_id) and tonumber(history_id) or 0
    local history = HISTORY_NAMES[history_id] or "없음"

    local ok_fame, fame = pcall(function() return ext.fame end)
    fame = (ok_fame and fame) and tonumber(fame) or 0

    local sp = ch.move or 0
    local max_sp = ch.max_move or 0

    local spirit_display = spirit >= 600 and "極盛" or tostring(spirit)

    local exp = ch.experience
    local needed = ch.level * ch.level * 100 + ch.level * 500

    -- HP/SP/MP bars
    local hp_bar = draw_graph(ch.hp, ch.max_hp)
    local sp_bar = draw_graph(sp, max_sp)
    local mp_bar = draw_graph(ch.mana, ch.max_mana)

    ctx:send("{cyan}┌──────────────────────────────────────────────────────────┐{reset}")
    ctx:send("{cyan}│{reset}" .. string.format("%30s", "· " .. ch.name .. " ·") .. string.format("%28s", "") .. "{cyan}│{reset}")
    ctx:send("{cyan}├──────────────┬──────────────┬──────────────┬──────────────┤{reset}")
    ctx:send("{cyan}│{reset}" .. string.format(" 이름:%-8s", ch.name) .. "{cyan}│{reset}"
        .. string.format(" 무공: %6d ", ch.level) .. "{cyan}│{reset}"
        .. string.format(" 직업: %-6s", cls_name) .. "{cyan}│{reset}"
        .. string.format(" 출신: %-6s", history) .. "{cyan}│{reset}")
    ctx:send("{cyan}├──────────────┼──────────────┼──────────────┼──────────────┤{reset}")

    -- Stats row
    ctx:send("{cyan}│{reset}" .. string.format(" 힘:%4d     ", stamina) .. "{cyan}│{reset}"
        .. string.format(" 민첩:%3d     ", agility) .. "{cyan}│{reset}"
        .. string.format(" 기골:%3d     ", bone) .. "{cyan}│{reset}"
        .. string.format(" 투지:%-4s   ", spirit_display) .. "{cyan}│{reset}")
    ctx:send("{cyan}│{reset}" .. string.format(" 내공:%3d     ", inner) .. "{cyan}│{reset}"
        .. string.format(" 지혜:%3d     ", wisdom) .. "{cyan}│{reset}"
        .. string.format(" 문파: %-6s", faction) .. "{cyan}│{reset}"
        .. string.format(" 명성: %5d ", fame) .. "{cyan}│{reset}")
    ctx:send("{cyan}├──────────────┴──────────────┴──────────────┴──────────────┤{reset}")

    -- HP/SP/MP bars
    ctx:send("{cyan}│{reset} {red}체력{reset} [" .. hp_bar .. "] "
        .. string.format("%5d/%-5d", ch.hp, ch.max_hp) .. "  수련치: "
        .. string.format("%-10d", exp) .. "  {cyan}│{reset}")
    ctx:send("{cyan}│{reset} {cyan}내력{reset} [" .. sp_bar .. "] "
        .. string.format("%5d/%-5d", sp, max_sp) .. "  다음:   "
        .. string.format("%-10d", needed) .. "  {cyan}│{reset}")
    ctx:send("{cyan}│{reset} {yellow}이동{reset} [" .. mp_bar .. "] "
        .. string.format("%5d/%-5d", ch.mana, ch.max_mana)
        .. string.format("%24s", "") .. "{cyan}│{reset}")
    ctx:send("{cyan}└──────────────────────────────────────────────────────────┘{reset}")
end, "점수")

register_command("wscore", function(ctx, args)
    -- Alias for score
    local ch = ctx.char
    if not ch then return end
    local score_fn = nil
    -- Just call the same score logic
    ctx:call_command("score", args)
end, "정보")

-- ── Who (누구.c format — 강호인 명단) ──────────────────────────

register_command("who", function(ctx, args)
    local players = ctx:get_players()
    ctx:send("{cyan}·─── 강호인(江湖人) 명단 ───·{reset}")
    ctx:send("")

    local by_faction = {}
    local admins = {}

    for i = 1, #players do
        local p = players[i]
        local ext = p.extensions or {}
        local ok, faction = pcall(function() return ext.faction end)
        faction = (ok and faction and tostring(faction) ~= "") and tostring(faction) or "낭인"

        local flags = ""
        if p.fighting then flags = flags .. "*" end

        local display = flags .. p.name .. "【" .. faction .. "】"

        if p.level >= 100 then
            admins[#admins + 1] = display
        else
            if not by_faction[faction] then by_faction[faction] = {} end
            by_faction[faction][#by_faction[faction] + 1] = display
        end
    end

    for faction, plist in pairs(by_faction) do
        for i = 1, #plist, 2 do
            local col1 = plist[i] or ""
            local col2 = plist[i + 1] or ""
            ctx:send("  " .. string.format("%-28s", col1) .. col2)
        end
    end

    if #admins > 0 then
        ctx:send("")
        ctx:send("{yellow}운영자:{reset}")
        for i = 1, #admins do
            ctx:send("  " .. admins[i])
        end
    end

    ctx:send("")
    local total = 0
    for _, plist in pairs(by_faction) do total = total + #plist end
    total = total + #admins
    ctx:send("현재 " .. total .. "명의 무림인이 강호에 나와 있습니다.")
end, "누구")

-- ── Inventory (가진거.c format — grouped 3-column) ─────────────

register_command("inventory", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    ctx:send("{cyan}·" .. ch.name .. "님의 소지품 목록·{reset}")

    local count = ctx:get_inv_count()
    if count == 0 then
        ctx:send("당신은 아무것도 가지고 있지 않습니다.")
        if ch.gold > 0 then
            ctx:send("{yellow}" .. ch.gold .. "냥{reset} 가지고 있습니다.")
        end
        return
    end

    ctx:send("현재 {red}" .. count .. "{reset}개의 물품을 가지고 있습니다.")

    -- Group by short description (Python list uses 0-based indexing)
    local inv = ch.inventory
    local counts = {}
    local order = {}
    for i = 0, count - 1 do
        local ok, obj = pcall(function() return inv[i] end)
        if ok and obj then
            local desc = obj.proto.short_desc
            if not counts[desc] then
                counts[desc] = 0
                order[#order + 1] = desc
            end
            counts[desc] = counts[desc] + 1
        end
    end

    local items = {}
    for _, desc in ipairs(order) do
        local qty = counts[desc]
        if qty > 1 then
            items[#items + 1] = qty .. "개의 " .. desc
        else
            items[#items + 1] = desc
        end
    end

    for i = 1, #items, 3 do
        local row = "  "
        for j = 0, 2 do
            if items[i + j] then
                row = row .. string.format("%-22s", items[i + j])
            end
        end
        ctx:send(row)
    end

    if ch.gold > 0 then
        ctx:send("{yellow}" .. ch.gold .. "냥{reset} 가지고 있습니다.")
    end
end, "소지품")
register_command("i", function(ctx, args)
    ctx:call_command("inventory", args)
end)

-- ── Equipment (장비.c format — slot list with stats) ───────────

register_command("equipment", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    ctx:send("{cyan}ㆍ" .. ch.name .. "의 장비ㆍ{reset}")

    local found = false
    local total_ac = 0
    local total_wc = 0
    local equip = ch.equipment

    for slot_id = 1, NUM_WEAR_SLOTS do
        local ok, obj = pcall(function() return equip[slot_id] end)
        if ok and obj then
            found = true
            local ac = 0
            local wc = 0
            local ok2, affs = pcall(function() return obj.proto.affects end)
            if ok2 and affs then
                local j = 0
                while true do
                    local ok3, aff = pcall(function() return affs[j] end)
                    if not ok3 or not aff then break end
                    local ok4, loc = pcall(function() return aff.location end)
                    local ok5, mod = pcall(function() return aff.modifier end)
                    loc = (ok4 and loc) and tostring(loc) or ""
                    mod = (ok5 and mod) and tonumber(mod) or 0
                    if loc == "ARMOR" or loc == "AC" then
                        ac = ac + mod
                    elseif loc == "DAMROLL" or loc == "HITROLL" then
                        wc = wc + mod
                    end
                    j = j + 1
                end
            end
            total_ac = total_ac + ac
            total_wc = total_wc + wc

            local stat_str = ""
            if ac ~= 0 then
                stat_str = stat_str .. "({cyan}" .. string.format("%+d", ac) .. "{reset})"
            end
            if wc ~= 0 then
                stat_str = stat_str .. "({red}" .. string.format("%+d", wc) .. "{reset})"
            end

            local slot_name = WEAR_SLOTS[slot_id] or ("슬롯" .. slot_id)
            ctx:send("  " .. string.format("%-6s", slot_name) .. " : " .. obj.proto.short_desc .. " " .. stat_str)
        end
    end

    if not found then
        ctx:send("  착용중인 장비가 없습니다.")
    else
        ctx:send("")
        ctx:send("  방어력 합계: {cyan}" .. total_ac .. "{reset}  공격력 합계: {red}" .. total_wc .. "{reset}")
    end
end, "장비")

-- ── Consider (판별) ────────────────────────────────────────────

register_command("consider", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("누구를 판별하시겠습니까?")
        return
    end

    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end

    local diff = target.level - ch.level
    local msg
    if diff <= -10 then msg = "웃음이 나올 정도입니다."
    elseif diff <= -5 then msg = "쉬운 상대입니다."
    elseif diff <= 0 then msg = "비슷한 수준입니다."
    elseif diff <= 5 then msg = "조심해야 합니다."
    elseif diff <= 10 then msg = "매우 위험합니다!"
    else msg = "상대가 되지 않습니다. 도망치세요!"
    end

    ctx:send(target.name .. ": " .. msg)
end, "판별")
