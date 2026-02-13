-- info.lua — 3eyes 정보 명령어 (원본 cmdlist 기반)
-- 점수, 누구, 장비, 소지품, 마법, 비교, 시간

-- ══════════════════════════════════════════════════════════════════
-- 점수 — 캐릭터 정보 (command1.c score, expanded)
-- ══════════════════════════════════════════════════════════════════

register_command("점수", function(ctx, args)
    local ch = ctx.char
    local cls = ch.class_id or CLASS_FIGHTER
    local class_name = THREEEYES_CLASSES[cls] or "모험가"
    local race_name = THREEEYES_RACES[ch.race_id] or "인간"

    local str_val = te_stat(ch, "str", 13)
    local dex_val = te_stat(ch, "dex", 13)
    local con_val = te_stat(ch, "con", 13)
    local int_val = te_stat(ch, "int", 13)
    local pie_val = te_stat(ch, "pie", 13)

    local lines = {
        "{bright_cyan}━━━━━━━━━━━━━━━ 캐릭터 정보 ━━━━━━━━━━━━━━━{reset}",
        string.format("  이름: {bright_white}%s{reset}  종족: %s  직업: {bright_yellow}%s{reset}",
            ch.name, race_name, class_name),
        string.format("  레벨: {bright_yellow}%d{reset}  경험치: %s",
            ch.level, tostring(ch.experience or 0)),
    }

    -- Advancement status
    if cls >= CLASS_INVINCIBLE and cls <= CLASS_CARE_III then
        local adv_names = {
            [CLASS_INVINCIBLE]="무적자", [CLASS_CARETAKER]="보살핌자",
            [CLASS_CARE_II]="보살핌II", [CLASS_CARE_III]="보살핌III",
        }
        lines[#lines + 1] = "  전직등급: {bright_yellow}" ..
            (adv_names[cls] or "?") .. "{reset}"
    end

    lines[#lines + 1] = ""
    lines[#lines + 1] = string.format(
        "  HP: {green}%d{reset}/{green}%d{reset}  MP: {cyan}%d{reset}/{cyan}%d{reset}  MV: {yellow}%d{reset}/{yellow}%d{reset}",
        ch.hp, ch.max_hp, ch.mana, ch.max_mana, ch.move or 0, ch.max_move or 0)

    lines[#lines + 1] = ""
    lines[#lines + 1] = string.format(
        "  힘: %d(%+d) 민첩: %d(%+d) 체력: %d(%+d)",
        str_val, te_bonus(str_val), dex_val, te_bonus(dex_val), con_val, te_bonus(con_val))
    lines[#lines + 1] = string.format(
        "  지능: %d(%+d) 신앙: %d(%+d)",
        int_val, te_bonus(int_val), pie_val, te_bonus(pie_val))

    lines[#lines + 1] = ""
    lines[#lines + 1] = string.format(
        "  AC: %d  THAC0: %d  골드: %d원",
        ch.armor_class or 100, ch.hitroll or 0, ch.gold or 0)

    -- Bank balance
    local bank_gold = ctx:get_player_data("bank_gold") or 0
    if bank_gold > 0 then
        lines[#lines + 1] = "  은행: {yellow}" .. bank_gold .. "원{reset}"
    end

    -- Proficiency display
    lines[#lines + 1] = ""
    lines[#lines + 1] = "{bright_cyan}-- 무기숙련 --{reset}"
    local prof_line = " "
    for i = 0, 4 do
        local pct = te_prof_percent(ch, i)
        local color = pct >= 80 and "{bright_green}" or pct >= 40 and "{yellow}" or "{white}"
        prof_line = prof_line .. " " .. THREEEYES_PROF[i] .. "=" ..
            color .. pct .. "%{reset}"
    end
    lines[#lines + 1] = prof_line

    -- Realm display
    lines[#lines + 1] = "{bright_cyan}-- 마법영역 --{reset}"
    local realm_line = " "
    for i = 0, 3 do
        local pct = te_realm_percent(ch, i)
        local color = pct >= 80 and "{bright_green}" or pct >= 40 and "{yellow}" or "{white}"
        realm_line = realm_line .. " " .. THREEEYES_REALM[i] .. "=" ..
            color .. pct .. "%{reset}"
    end
    lines[#lines + 1] = realm_line

    -- Marriage status
    local partner = ctx:get_player_data("partner") or ""
    if partner ~= "" then
        lines[#lines + 1] = ""
        lines[#lines + 1] = "  결혼: {bright_magenta}" .. partner .. "{reset}"
    end

    -- Family status
    local family_id = ctx:get_player_data("family_id")
    if family_id and family_id > 0 then
        local family_rank = ctx:get_player_data("family_rank") or "식구"
        lines[#lines + 1] = "  가족: ID=" .. family_id .. " 직위=" .. family_rank
    end

    -- PK stats
    local pk_kills = ctx:get_player_data("pk_kills") or 0
    local pk_deaths = ctx:get_player_data("pk_deaths") or 0
    if pk_kills > 0 or pk_deaths > 0 then
        lines[#lines + 1] = "  PK: 킬 " .. pk_kills .. " / 데스 " .. pk_deaths
    end

    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

register_command("정보", function(ctx, args)
    ctx:call_command("점수", args or "")
end)

-- ══════════════════════════════════════════════════════════════════
-- 누구 — 접속자 목록 (command5.c who, expanded)
-- ══════════════════════════════════════════════════════════════════

register_command("누구", function(ctx, args)
    local players = ctx:get_online_players()
    local lines = {
        "{bright_cyan}━━━━━━━━━━━━━━━ 접속자 목록 ━━━━━━━━━━━━━━━{reset}",
        "{bright_cyan}  레벨  종족     직업       이름{reset}",
        "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
    }
    local count = 0
    local viewer_cls = ctx.char.class_id or 0
    if players then
        local nplayers = #players
        for i = 1, nplayers do
            local p = players[i]
            if not p then break end

            -- Skip DM-invisible players (PDIRTY flag) unless viewer is DM
            local hidden = false
            pcall(function()
                if p.flags then
                    for _, f in ipairs(p.flags) do
                        if f == PDIRTY or f == PDMINV then
                            hidden = true; break
                        end
                    end
                end
            end)
            if hidden and viewer_cls < CLASS_DM then
                -- skip hidden
            else
                local class_name = THREEEYES_CLASSES[p.class_id] or "?"
                local race_name = THREEEYES_RACES[p.race_id] or "?"

                -- Coloring based on class tier
                local cls = p.class_id or 0
                local name_color = "{white}"
                if cls >= CLASS_DM then name_color = "{bright_red}"
                elseif cls >= CLASS_CARETAKER then name_color = "{bright_yellow}"
                elseif cls >= CLASS_INVINCIBLE then name_color = "{bright_cyan}"
                end

                -- PK indicator
                local pk_mark = ""
                pcall(function()
                    if p.flags then
                        for _, f in ipairs(p.flags) do
                            if f == PCHAOS then
                                pk_mark = " {red}[PK]{reset}"; break
                            end
                        end
                    end
                end)

                lines[#lines + 1] = string.format(
                    "  [%3d] %-6s  %-10s %s%s{reset}%s",
                    p.level, race_name, class_name, name_color, p.name, pk_mark)
                count = count + 1
            end
        end
    end
    if count == 0 then
        lines[#lines + 1] = "  아무도 접속해 있지 않습니다."
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    lines[#lines + 1] = "  총 " .. count .. "명 접속 중"
    ctx:send(table.concat(lines, "\r\n"))
end)

register_command("who", function(ctx, args)
    ctx:call_command("누구", args or "")
end)

-- ══════════════════════════════════════════════════════════════════
-- 장비 — 장비 목록 (command1.c equipment)
-- ══════════════════════════════════════════════════════════════════

local EQUIP_SLOTS = {
    [0]="<머리>",       [1]="<목>",        [2]="<가슴>",      [3]="<몸통>",
    [4]="<다리>",       [5]="<발>",        [6]="<오른손>",    [7]="<왼손>",
    [8]="<오른팔>",     [9]="<왼팔>",      [10]="<방패>",     [11]="<허리>",
    [12]="<오른손목>",  [13]="<왼손목>",   [14]="<오른손가락>", [15]="<왼손가락>",
    [16]="<무기>",      [17]="<보조무기>",
}

register_command("장비", function(ctx, args)
    local ch = ctx.char
    local lines = {"{bright_cyan}━━━━━━━━━━ 장비 목록 ━━━━━━━━━━{reset}"}
    local found = false
    for slot = 0, 17 do
        local slot_name = EQUIP_SLOTS[slot] or ("<슬롯" .. slot .. ">")
        local ok, item = pcall(function() return ch.equipment[slot] end)
        if ok and item then
            local adj = ""
            pcall(function()
                local a = item.adjustment or 0
                if a > 0 then adj = " {bright_green}+" .. a .. "{reset}" end
            end)
            lines[#lines + 1] = string.format("  %-12s %s%s", slot_name, item.name, adj)
            found = true
        else
            lines[#lines + 1] = string.format("  %-12s {bright_black}비어있음{reset}", slot_name)
        end
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ══════════════════════════════════════════════════════════════════
-- 소지품 — 인벤토리 (command1.c inventory)
-- ══════════════════════════════════════════════════════════════════

register_command("소지품", function(ctx, args)
    local ch = ctx.char
    local inv = ctx:get_inventory()
    local lines = {"{bright_cyan}━━━━━━━━━━ 소지품 ━━━━━━━━━━{reset}"}
    if #inv == 0 then
        lines[#lines + 1] = "  아무것도 소지하고 있지 않습니다."
    else
        for i = 1, #inv do
            local item = inv[i]
            local adj = ""
            pcall(function()
                local a = item.adjustment or 0
                if a > 0 then adj = " {bright_green}+" .. a .. "{reset}" end
            end)
            lines[#lines + 1] = "  " .. item.name .. adj
        end
    end
    lines[#lines + 1] = string.format("\r\n  소지금: {yellow}%d{reset}원", ch.gold or 0)
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ══════════════════════════════════════════════════════════════════
-- 마법 — 현재 효과 (command1.c affects)
-- ══════════════════════════════════════════════════════════════════

register_command("마법", function(ctx, args)
    local ch = ctx.char
    local lines = {"{bright_cyan}━━━━━━━━━━ 현재 효과 ━━━━━━━━━━{reset}"}
    local found = false

    -- Check player flags for buff effects
    local flag_names = {
        [PBLESS]="{green}축복{reset} (THAC0 -3)",
        [PHIDDN]="{white}은신{reset}",
        [PINVIS]="{white}투명{reset}",
        [PBLIND]="{red}실명{reset}",
        [PCHARM]="{magenta}매혹{reset}",
        [PFEARS]="{red}공포{reset} (THAC0 +2)",
        [PHASTE]="{cyan}가속{reset} (공격 간격 1초)",
        [PPOISN]="{green}중독{reset}",
        [PDISEA]="{yellow}질병{reset}",
        [PDINVI]="{cyan}투명감지{reset}",
        [PDMAGC]="{cyan}마법감지{reset}",
        [PFLY]="{cyan}비행{reset}",
        [PLEVIT]="{cyan}공중부양{reset}",
        [PWATER]="{blue}수중호흡{reset}",
        [PSHIEL]="{yellow}돌방패{reset}",
        [PRFIRE]="{red}화염저항{reset}",
        [PRCOLD]="{blue}냉기저항{reset}",
        [PRMAGI]="{magenta}마법저항{reset}",
        [PLIGHT]="{yellow}빛{reset}",
        [PSILNC]="{red}침묵{reset}",
        [PTRACK]="{green}추적{reset}",
        [PUPDMG]="{bright_red}파워업그레이드{reset}",
    }

    pcall(function()
        if ch.flags then
            for _, f in ipairs(ch.flags) do
                if flag_names[f] then
                    lines[#lines + 1] = "  " .. flag_names[f]
                    found = true
                end
            end
        end
    end)

    -- Extensions bonuses
    pcall(function()
        if ch.extensions then
            if ch.extensions.bonus_power and ch.extensions.bonus_power > 0 then
                lines[#lines + 1] = "  {bright_red}공격력 부스트 +" ..
                    ch.extensions.bonus_power .. "{reset}"
                found = true
            end
            if ch.extensions.accuracy_bonus and ch.extensions.accuracy_bonus > 0 then
                lines[#lines + 1] = "  {bright_white}명중률 부스트 +" ..
                    ch.extensions.accuracy_bonus .. "{reset}"
                found = true
            end
        end
    end)

    if not found then
        lines[#lines + 1] = "  현재 어떤 효과도 받고 있지 않습니다."
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ══════════════════════════════════════════════════════════════════
-- 비교 — 아이템 비교 (command8.c compare)
-- ══════════════════════════════════════════════════════════════════

register_command("비교", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 비교 <아이템1> <아이템2>")
        return
    end
    local name1, name2 = args:match("^(%S+)%s+(%S+)$")
    if not name1 then
        ctx:send("사용법: 비교 <아이템1> <아이템2>")
        return
    end
    local item1 = ctx:find_inv_item(name1) or ctx:find_equip_item(name1)
    local item2 = ctx:find_inv_item(name2) or ctx:find_equip_item(name2)
    if not item1 then
        ctx:send(name1 .. "을(를) 찾을 수 없습니다.")
        return
    end
    if not item2 then
        ctx:send(name2 .. "을(를) 찾을 수 없습니다.")
        return
    end

    local lines = {"{bright_cyan}━━━━━━ 아이템 비교 ━━━━━━{reset}"}
    lines[#lines + 1] = string.format("  %-20s  vs  %-20s", item1.name, item2.name)

    local ok1, cost1 = pcall(function() return item1.proto.cost or 0 end)
    local ok2, cost2 = pcall(function() return item2.proto.cost or 0 end)
    if ok1 and ok2 then
        lines[#lines + 1] = string.format("  가격: %d원  vs  %d원", cost1 or 0, cost2 or 0)
    end

    local ok_a1, adj1 = pcall(function() return item1.adjustment or 0 end)
    local ok_a2, adj2 = pcall(function() return item2.adjustment or 0 end)
    if ok_a1 and ok_a2 then
        lines[#lines + 1] = string.format("  강화: +%d  vs  +%d", adj1, adj2)
    end

    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ══════════════════════════════════════════════════════════════════
-- 시간 — 게임 시간 (command8.c time)
-- ══════════════════════════════════════════════════════════════════

register_command("시간", function(ctx, args)
    local game_time = ctx:get_game_time()
    if game_time then
        local hour = game_time.hour or 0
        local day = game_time.day or 1
        local month = game_time.month or 1
        local year = game_time.year or 1

        local period = "새벽"
        if hour >= 6 and hour < 12 then period = "아침"
        elseif hour >= 12 and hour < 18 then period = "오후"
        elseif hour >= 18 and hour < 22 then period = "저녁"
        elseif hour >= 22 then period = "밤"
        end

        ctx:send(string.format("{bright_cyan}%d년 %d월 %d일 %d시 (%s){reset}",
            year, month, day, hour, period))
    else
        ctx:send("{bright_cyan}현재 시각을 알 수 없습니다.{reset}")
    end
end)
