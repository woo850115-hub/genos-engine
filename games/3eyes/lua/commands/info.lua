-- info.lua — 3eyes info commands (score, who, equipment, inventory, etc.)
-- Overrides common info for 3eyes-specific display

register_command("score", function(ctx, args)
    local ch = ctx.char
    local class_name = THREEEYES_CLASSES[ch.class_id] or "모험가"
    local race_name = THREEEYES_RACES[ch.race_id] or "인간"
    local str_val = te_stat(ch, "str", 13)
    local dex_val = te_stat(ch, "dex", 13)
    local con_val = te_stat(ch, "con", 13)
    local int_val = te_stat(ch, "int", 13)
    local pie_val = te_stat(ch, "pie", 13)

    local lines = {
        "{bright_cyan}━━━━━━━━━━ 캐릭터 정보 ━━━━━━━━━━{reset}",
        string.format("  이름: {bold}%s{reset}  종족: %s  직업: %s",
            ch.name, race_name, class_name),
        string.format("  레벨: {bright_yellow}%d{reset}  경험치: %d",
            ch.level, ch.experience or 0),
        "",
        string.format("  HP: {green}%d/%d{reset}  MP: {cyan}%d/%d{reset}  MV: {yellow}%d/%d{reset}",
            ch.hp, ch.max_hp, ch.mana, ch.max_mana, ch.move or 0, ch.max_move or 0),
        "",
        string.format("  힘: %d(%+d) 민첩: %d(%+d) 체력: %d(%+d)",
            str_val, te_bonus(str_val), dex_val, te_bonus(dex_val), con_val, te_bonus(con_val)),
        string.format("  지능: %d(%+d) 신앙: %d(%+d)",
            int_val, te_bonus(int_val), pie_val, te_bonus(pie_val)),
        "",
        string.format("  AC: %d  THAC0: %d  골드: %d원",
            ch.armor_class or 100, ch.hitroll or 0, ch.gold or 0),
    }

    -- Proficiency display
    local prof_line = "  무기숙련:"
    for i = 0, 4 do
        prof_line = prof_line .. " " .. THREEEYES_PROF[i] .. "=" .. te_prof_percent(ch, i) .. "%"
    end
    lines[#lines + 1] = prof_line

    -- Realm display
    local realm_line = "  마법영역:"
    for i = 0, 3 do
        realm_line = realm_line .. " " .. THREEEYES_REALM[i] .. "=" .. te_realm_percent(ch, i) .. "%"
    end
    lines[#lines + 1] = realm_line

    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end, "건강")

register_command("who", function(ctx, args)
    local players = ctx:get_online_players()
    local lines = {"{bright_cyan}━━━━━━━━━━ 접속자 목록 ━━━━━━━━━━{reset}"}
    if not players or #players == 0 then
        lines[#lines + 1] = "  아무도 접속해 있지 않습니다."
    else
        for _, p in ipairs(players) do
            local class_name = THREEEYES_CLASSES[p.class_id] or "?"
            local race_name = THREEEYES_RACES[p.race_id] or "?"
            lines[#lines + 1] = string.format("  [%3d %s %s] %s",
                p.level, race_name, class_name, p.name)
        end
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end, "누구")

local EQUIP_SLOTS = {
    [0]="머리", [1]="목", [2]="가슴", [3]="몸통",
    [4]="다리", [5]="발", [6]="오른손", [7]="왼손",
    [8]="오른팔", [9]="왼팔", [10]="방패", [11]="허리",
    [12]="오른손목", [13]="왼손목", [14]="오른손가락", [15]="왼손가락",
    [16]="무기", [17]="보조무기",
}

register_command("equipment", function(ctx, args)
    local ch = ctx.char
    local lines = {"{bright_cyan}-- 장비 목록 --{reset}"}
    local found = false
    for slot = 0, 17 do
        local slot_name = EQUIP_SLOTS[slot] or ("슬롯 " .. slot)
        local ok, item = pcall(function() return ch.equipment[slot] end)
        if ok and item then
            lines[#lines + 1] = string.format("  <%s> %s", slot_name, item.name)
            found = true
        end
    end
    if not found then
        lines[#lines + 1] = "  장착한 장비가 없습니다."
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "장비")

register_command("affects", function(ctx, args)
    local ch = ctx.char
    local affects = ctx:get_affects(ch)
    if not affects or #affects == 0 then
        ctx:send("현재 어떤 효과도 받고 있지 않습니다.")
        return
    end
    local lines = {"{bright_cyan}-- 현재 효과 --{reset}"}
    for _, aff in ipairs(affects) do
        lines[#lines + 1] = string.format("  %s (남은 시간: %d)", aff.name or "?", aff.duration or 0)
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "효과")

register_command("consider", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 살펴보시겠습니까?")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    local diff = target.level - ctx.char.level
    local msg
    if diff <= -10 then msg = "{green}어린아이도 이길 수 있겠습니다.{reset}"
    elseif diff <= -5 then msg = "{green}쉬운 상대입니다.{reset}"
    elseif diff <= -2 then msg = "{bright_green}만만한 상대입니다.{reset}"
    elseif diff <= 2 then msg = "{yellow}비슷한 수준입니다.{reset}"
    elseif diff <= 5 then msg = "{bright_yellow}강한 상대입니다.{reset}"
    elseif diff <= 10 then msg = "{red}매우 위험한 상대입니다!{reset}"
    else msg = "{bright_red}자살 행위입니다!{reset}"
    end
    ctx:send(target.name .. " - " .. msg)
end, "판단")

register_command("time", function(ctx, args)
    ctx:send("{bright_cyan}현재 게임 시간을 알 수 없습니다.{reset}")
end, "시간")

register_command("weather", function(ctx, args)
    ctx:send("{bright_cyan}날씨 정보를 알 수 없습니다.{reset}")
end, "날씨")

register_command("toggle", function(ctx, args)
    if not args or args == "" then
        local toggles = ctx:get_toggles()
        local lines = {"{bright_cyan}-- 설정 --{reset}"}
        for k, v in pairs(toggles) do
            lines[#lines + 1] = string.format("  %-12s : %s", k, v and "켜짐" or "꺼짐")
        end
        ctx:send(table.concat(lines, "\r\n"))
        return
    end
    local new_val = ctx:toggle(args)
    if new_val == nil then
        ctx:send("그런 설정은 없습니다.")
    else
        ctx:send(args .. " → " .. (new_val and "켜짐" or "꺼짐"))
    end
end, "설정")
