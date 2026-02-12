-- info.lua — Simoon information commands (score, who, equipment, etc.)
-- Overrides common/lua score and who with Simoon-specific format

register_command("score", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local class_name = SIMOON_CLASSES[ch.class_id] or "모험가"
    local race_name = SIMOON_RACES[ch.race_id or 0] or "인간"
    local sex_name = ({[0]="중성",[1]="남성",[2]="여성"})[ch.sex or 0] or "중성"

    local lines = {
        "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        "  {bright_white}" .. ch.name .. "{reset} — " .. race_name .. " " .. class_name,
        "  레벨: {bright_yellow}" .. ch.level .. "{reset}  성별: " .. sex_name,
        "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        "  체력: {green}" .. ch.hp .. "/" .. ch.max_hp .. "{reset}" ..
        "  마나: {cyan}" .. ch.mana .. "/" .. ch.max_mana .. "{reset}" ..
        "  이동: {yellow}" .. (ch.move or 0) .. "/" .. (ch.max_move or 0) .. "{reset}",
        "  골드: {bright_yellow}" .. ch.gold .. "{reset}" ..
        "  경험치: " .. ch.experience,
    }

    -- Crystal/killmark (Simoon-specific, stored in ext)
    local ok, ext = pcall(function() return ch.ext end)
    if ok and ext then
        local crystal = 0
        local killmark = 0
        pcall(function() crystal = ext.crystal or 0 end)
        pcall(function() killmark = ext.killmark or 0 end)
        if crystal > 0 or killmark > 0 then
            lines[#lines + 1] = "  크리스탈: {bright_cyan}" .. crystal ..
                "{reset}  킬마크: {bright_red}" .. killmark .. "{reset}"
        end
    end

    -- Stats
    local str_v = simoon_stat(ch, "str", 13)
    local dex_v = simoon_stat(ch, "dex", 13)
    local con_v = simoon_stat(ch, "con", 13)
    local int_v = simoon_stat(ch, "int", 13)
    local wis_v = simoon_stat(ch, "wis", 13)
    local cha_v = simoon_stat(ch, "cha", 13)
    lines[#lines + 1] = "  힘:" .. str_v .. " 민첩:" .. dex_v .. " 체력:" .. con_v ..
        " 지능:" .. int_v .. " 지혜:" .. wis_v .. " 매력:" .. cha_v

    -- Alignment and AC
    lines[#lines + 1] = "  성향: " .. (ch.alignment or 0) ..
        "  방어도: " .. (ch.armor_class or 100)

    -- Combat stats
    if ch.fighting then
        lines[#lines + 1] = "  {red}전투 중: " .. ch.fighting.name .. "{reset}"
    end

    lines[#lines + 1] = "{cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end, "스코어")

register_command("who", function(ctx, args)
    local players = ctx:get_players()
    if not players then
        ctx:send("현재 접속자가 없습니다.")
        return
    end

    local lines = {
        "{cyan}━━━━━━ 시문 접속자 목록 ━━━━━━{reset}",
    }
    local count = 0
    for i = 0, 200 do
        local ok, p = pcall(function() return players[i] end)
        if not ok or not p then break end
        local ch = p.character
        if ch then
            local cls = SIMOON_CLASSES[ch.class_id] or "?"
            local race = SIMOON_RACES[ch.race_id or 0] or "?"
            lines[#lines + 1] = string.format(
                "  [%3d %s %s] %s",
                ch.level, race, cls, ch.name)
            count = count + 1
        end
    end
    lines[#lines + 1] = "{cyan}━━━━━━ 총 " .. count .. "명 접속 중 ━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end, "누구")

register_command("equipment", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local SLOT_NAMES = {
        [0]="머리", [1]="목", [2]="가슴", [3]="몸통",
        [4]="다리", [5]="발", [6]="오른손", [7]="왼손",
        [8]="오른팔", [9]="왼팔", [10]="방패", [11]="허리",
        [12]="오른손목", [13]="왼손목", [14]="오른손가락", [15]="왼손가락",
        [16]="무기", [17]="보조무기",
    }

    local lines = {"{bright_cyan}-- 장비 --{reset}"}
    local found = false
    for slot = 0, 17 do
        local slot_name = SLOT_NAMES[slot] or ("슬롯" .. slot)
        local ok, item = pcall(function() return ch.equipment[slot] end)
        if ok and item then
            lines[#lines + 1] = "  <" .. slot_name .. "> " .. item.name
            found = true
        else
            lines[#lines + 1] = "  <" .. slot_name .. "> 비어있음"
        end
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "장비")
register_command("eq", function(ctx, args)
    ctx:execute("equipment", args)
end, nil)

register_command("inventory", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local count = ctx:get_inv_count()
    if count == 0 then
        ctx:send("아무것도 가지고 있지 않습니다.")
        return
    end
    local lines = {"{bright_cyan}-- 소지품 --{reset}"}
    for i = 0, count - 1 do
        local ok, item = pcall(function() return ch.inventory[i] end)
        if ok and item then
            lines[#lines + 1] = "  " .. item.name
        end
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "소지품")
register_command("i", function(ctx, args)
    ctx:execute("inventory", args)
end, nil)

register_command("affects", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local affects = ch.affects
    if not affects or #affects == 0 then
        ctx:send("현재 적용 중인 효과가 없습니다.")
        return
    end
    local lines = {"{bright_cyan}-- 적용 효과 --{reset}"}
    for i = 0, 50 do
        local ok, a = pcall(function() return affects[i] end)
        if not ok or not a then break end
        local ok2, sid = pcall(function() return a.spell_id end)
        local ok3, dur = pcall(function() return a.duration end)
        if ok2 and sid then
            lines[#lines + 1] = "  효과 #" .. sid ..
                (ok3 and dur and (" — " .. dur .. "틱 남음") or "")
        end
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "효과")

register_command("consider", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 관찰하시겠습니까?")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    local diff = target.level - ctx.char.level
    local msg
    if diff <= -10 then msg = "눈을 감고도 이길 수 있습니다."
    elseif diff <= -5 then msg = "쉽게 이길 수 있습니다."
    elseif diff <= -2 then msg = "유리한 싸움입니다."
    elseif diff <= 2 then msg = "비등한 상대입니다."
    elseif diff <= 5 then msg = "조심해야 합니다."
    elseif diff <= 10 then msg = "매우 위험합니다!"
    else msg = "{bright_red}자살 행위입니다!{reset}"
    end
    ctx:send(target.name .. ": " .. msg)
end, "관찰")

register_command("time", function(ctx, args)
    ctx:send("시문 세계의 시간이 흐르고 있습니다.")
end, "시간")

register_command("weather", function(ctx, args)
    ctx:send("하늘은 맑습니다.")
end, "날씨")

register_command("prompt", function(ctx, args)
    if not args or args == "" then
        ctx:send("현재 프롬프트 설정을 사용 중입니다.\r\n")
        ctx:send("사용법: prompt <%h/%H %m/%M %v/%V>")
        return
    end
    ctx:set_player_data("prompt", args)
    ctx:send("프롬프트가 설정되었습니다: " .. args)
end, "프롬프트")

register_command("toggle", function(ctx, args)
    if not args or args == "" then
        ctx:send("{bright_cyan}-- 토글 설정 --{reset}")
        local toggles = ctx:get_player_data("toggles") or {}
        ctx:send("  자동줍기 (autoloot): " .. (toggles.autoloot and "켜짐" or "꺼짐"))
        ctx:send("  자동골드 (autogold): " .. (toggles.autogold and "켜짐" or "꺼짐"))
        ctx:send("  간략보기 (brief): " .. (toggles.brief and "켜짐" or "꺼짐"))
        return
    end
    local key = args:lower()
    local toggles = ctx:get_player_data("toggles") or {}
    local current = toggles[key]
    if current == nil then current = false end
    toggles[key] = not current
    ctx:set_player_data("toggles", toggles)
    ctx:send(key .. ": " .. (toggles[key] and "켜짐" or "꺼짐"))
end, "토글")
