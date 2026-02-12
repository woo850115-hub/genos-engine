-- info.lua — tbaMUD information commands (overrides common score/who/etc.)
-- Based on act.informative.c from CircleMUD/tbaMUD, 한글화.

-- Position names (from tbaMUD act.informative.c)
local POS_NAMES = {
    [0] = "죽어 있습니다",
    [1] = "빈사 상태입니다",
    [2] = "의식불명입니다",
    [3] = "기절해 있습니다",
    [4] = "잠들어 있습니다",
    [5] = "쉬고 있습니다",
    [6] = "앉아 있습니다",
    [7] = "전투 중입니다",
    [8] = "서 있습니다",
}

-- Wear position labels (18 slots, from constants.c wear_where[])
local WEAR_WHERE = {
    [0]  = "<머리 위에>        ",
    [1]  = "<왼손 손가락에>    ",
    [2]  = "<오른손 손가락에>  ",
    [3]  = "<목에>             ",
    [4]  = "<목에>             ",
    [5]  = "<몸통에>           ",
    [6]  = "<머리에>           ",
    [7]  = "<다리에>           ",
    [8]  = "<발에>             ",
    [9]  = "<손에>             ",
    [10] = "<팔에>             ",
    [11] = "<방패로>           ",
    [12] = "<몸 주위에>        ",
    [13] = "<허리에>           ",
    [14] = "<왼쪽 손목에>      ",
    [15] = "<오른쪽 손목에>    ",
    [16] = "<오른손에 들고>    ",
    [17] = "<왼손에 들고>      ",
}

-- Class names
local CLASS_NAMES = {
    [0] = "마법사", [1] = "성직자", [2] = "도적", [3] = "전사",
}

-- Experience tables (per class, per level)
local EXP_TABLE = {
    [0] = {
        [0]=0, [1]=1, [2]=2500, [3]=5000, [4]=10000, [5]=20000, [6]=40000,
        [7]=60000, [8]=90000, [9]=135000, [10]=250000, [11]=375000, [12]=750000,
        [13]=1125000, [14]=1500000, [15]=1875000, [16]=2250000, [17]=2625000,
        [18]=3000000, [19]=3375000, [20]=3750000, [21]=4000000, [22]=4300000,
        [23]=4600000, [24]=4900000, [25]=5200000, [26]=5500000, [27]=5950000,
        [28]=6400000, [29]=6850000, [30]=7400000, [31]=8000000,
    },
    [1] = {
        [0]=0, [1]=1, [2]=1500, [3]=3000, [4]=6000, [5]=13000, [6]=27500,
        [7]=55000, [8]=110000, [9]=225000, [10]=450000, [11]=675000, [12]=900000,
        [13]=1125000, [14]=1350000, [15]=1575000, [16]=1800000, [17]=2100000,
        [18]=2400000, [19]=2700000, [20]=3000000, [21]=3250000, [22]=3500000,
        [23]=3800000, [24]=4100000, [25]=4400000, [26]=4800000, [27]=5200000,
        [28]=5600000, [29]=6000000, [30]=6400000, [31]=7000000,
    },
    [2] = {
        [0]=0, [1]=1, [2]=1250, [3]=2500, [4]=5000, [5]=10000, [6]=20000,
        [7]=40000, [8]=70000, [9]=110000, [10]=160000, [11]=220000, [12]=440000,
        [13]=660000, [14]=880000, [15]=1100000, [16]=1500000, [17]=2000000,
        [18]=2500000, [19]=3000000, [20]=3500000, [21]=3650000, [22]=3800000,
        [23]=4100000, [24]=4400000, [25]=4700000, [26]=5100000, [27]=5500000,
        [28]=5900000, [29]=6300000, [30]=6650000, [31]=7000000,
    },
    [3] = {
        [0]=0, [1]=1, [2]=2000, [3]=4000, [4]=8000, [5]=16000, [6]=32000,
        [7]=64000, [8]=125000, [9]=250000, [10]=500000, [11]=750000, [12]=1000000,
        [13]=1250000, [14]=1500000, [15]=1850000, [16]=2200000, [17]=2550000,
        [18]=2900000, [19]=3250000, [20]=3600000, [21]=3900000, [22]=4200000,
        [23]=4500000, [24]=4800000, [25]=5150000, [26]=5500000, [27]=5950000,
        [28]=6400000, [29]=6850000, [30]=7400000, [31]=8000000,
    },
}

local MAX_LEVEL = 34

local function get_class_name(class_id)
    return CLASS_NAMES[class_id] or "모험가"
end

local function exp_for_level(class_id, level)
    local tbl = EXP_TABLE[class_id] or EXP_TABLE[0]
    level = math.min(level, 31)
    return tbl[level] or tbl[31] or 8000000
end

local function exp_to_next(ch)
    if ch.level >= 31 then return 0 end
    local needed = exp_for_level(ch.class_id, ch.level + 1)
    return math.max(0, needed - ch.experience)
end

local function obj_modifiers(obj)
    local mods = {}
    local flags = obj.proto.flags
    if not flags then return "" end
    -- Iterate flags list
    local ok, len = pcall(function() return #flags end)
    if not ok then return "" end
    for i = 0, len - 1 do
        local ok2, flag = pcall(function() return flags[i] end)
        if ok2 then
            if flag == 1 then table.insert(mods, "..빛나고 있습니다!") end
            if flag == 2 then table.insert(mods, "..윙윙거리는 소리가 납니다!") end
            if flag == 3 then table.insert(mods, "(투명)") end
        end
    end
    return table.concat(mods, " ")
end

local function format_number(n)
    local s = tostring(math.floor(n))
    local result = ""
    local len = #s
    for i = 1, len do
        if i > 1 and (len - i + 1) % 3 == 0 then
            result = result .. ","
        end
        result = result .. s:sub(i, i)
    end
    return result
end

-- ── time ────────────────────────────────────────────────────────

register_command("time", function(ctx, args)
    local hour = ctx:get_game_hour()
    local day = ctx:get_game_day()
    local month = ctx:get_game_month()
    local year = ctx:get_game_year()
    local desc
    if hour < 6 or hour >= 21 then desc = "밤"
    elseif hour < 9 then desc = "새벽"
    elseif hour < 12 then desc = "아침"
    elseif hour < 17 then desc = "낮"
    else desc = "저녁" end
    ctx:send("현재 시간: " .. year .. "년 " .. month .. "월 " .. day .. "일 " ..
             hour .. "시 (" .. desc .. ")")
end, "시간")

-- ── weather ─────────────────────────────────────────────────────

local WEATHER_KR = {
    sunny = "맑음 ☀", cloudy = "흐림 ☁",
    rainy = "비 ☔", stormy = "폭풍 ⛈",
}

register_command("weather", function(ctx, args)
    local w = ctx:get_weather()
    local desc = WEATHER_KR[w] or w
    ctx:send("현재 날씨: " .. desc)
end, "날씨")

-- ── prompt ──────────────────────────────────────────────────────

register_command("prompt", function(ctx, args)
    if not args or args == "" then
        ctx:set_player_data("prompt", "")
        ctx:send("프롬프트가 기본값으로 초기화되었습니다.")
        return
    end
    local fmt = args
    if fmt == "all" then
        fmt = "< %h/%Hhp %m/%Mmn %v/%Vmv > "
    end
    ctx:set_player_data("prompt", fmt)
    ctx:send("프롬프트가 설정되었습니다: " .. fmt)
end, "프롬프트")

-- ── toggle ──────────────────────────────────────────────────────

local TOGGLE_OPTS = {
    {key="autoloot", desc="자동 줍기"},
    {key="autogold", desc="자동 골드"},
    {key="autosplit", desc="자동 분배"},
    {key="brief", desc="간략 모드"},
    {key="compact", desc="압축 모드"},
    {key="color", desc="컬러"},
}

register_command("toggle", function(ctx, args)
    if not args or args == "" then
        ctx:send("{bright_cyan}--- 설정 ---{reset}")
        for _, opt in ipairs(TOGGLE_OPTS) do
            local val = ctx:get_player_data("toggle_" .. opt.key)
            local status
            if val then
                status = "{green}켜짐{reset}"
            else
                status = "{red}꺼짐{reset}"
            end
            ctx:send("  " .. string.format("%-10s", opt.desc) ..
                     " (" .. string.format("%-10s", opt.key) .. "): " .. status)
        end
        return
    end
    local opt = args:lower()
    local valid = false
    for _, o in ipairs(TOGGLE_OPTS) do
        if o.key == opt then valid = true; break end
    end
    if not valid then
        local keys = {}
        for _, o in ipairs(TOGGLE_OPTS) do table.insert(keys, o.key) end
        ctx:send("사용 가능: " .. table.concat(keys, ", "))
        return
    end
    local current = ctx:get_player_data("toggle_" .. opt)
    if current then
        ctx:set_player_data("toggle_" .. opt, false)
        ctx:send(opt .. ": 꺼짐")
    else
        ctx:set_player_data("toggle_" .. opt, true)
        ctx:send(opt .. ": 켜짐")
    end
end, "설정")

-- ── practice ────────────────────────────────────────────────────

local function proficiency_bar(prof)
    local filled = math.floor(prof / 10)
    local empty = 10 - filled
    return "[" .. string.rep("#", filled) .. string.rep("-", empty) .. "]"
end

register_command("practice", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local practices_left = ctx:get_player_data("practices") or 0

    if not args or args == "" then
        ctx:send("{bright_cyan}--- 스킬/주문 목록 ---{reset}")
        local skills = ch.skills
        if not skills then
            ctx:send("  배운 스킬이 없습니다.")
            ctx:send("\r\n연습 횟수: " .. practices_left .. "회 남음")
            return
        end
        local found = false
        local ok, pairs_fn = pcall(function() return pairs(skills) end)
        if ok then
            for sid, prof in pairs_fn do
                local info = ctx:get_skill(tonumber(sid))
                local name
                if info then
                    local ok2, n = pcall(function() return info.name end)
                    name = ok2 and n or ("스킬#" .. tostring(sid))
                else
                    name = "스킬#" .. tostring(sid)
                end
                ctx:send("  " .. string.format("%-20s", name) .. " " ..
                         proficiency_bar(prof) .. " (" .. prof .. "%)")
                found = true
            end
        end
        if not found then
            ctx:send("  배운 스킬이 없습니다.")
        end
        ctx:send("\r\n연습 횟수: " .. practices_left .. "회 남음")
        return
    end

    -- Practice a specific skill
    if practices_left <= 0 then
        ctx:send("연습 횟수가 없습니다. 레벨을 올려야 합니다.")
        return
    end

    -- Check guildmaster in room
    local chars = ctx:get_characters()
    local has_teacher = false
    for i = 1, #chars do
        local mob = chars[i]
        if mob.is_npc then
            local flags = mob.proto.act_flags
            local ok, len = pcall(function() return #flags end)
            if ok then
                for j = 0, len - 1 do
                    local ok2, f = pcall(function() return flags[j] end)
                    if ok2 and (f == "teacher" or f == "guildmaster") then
                        has_teacher = true
                        break
                    end
                end
            end
            if has_teacher then break end
        end
    end
    if not has_teacher then
        ctx:send("여기서는 연습할 수 없습니다. 길드마스터를 찾아가세요.")
        return
    end

    local target = args:lower()
    local all_skills = ctx:get_all_skills()
    local found_id = nil
    local found_name = ""
    for i = 1, #all_skills do
        local s = all_skills[i]
        local sname = (s.name or ""):lower()
        local skr = (s.korean_name or ""):lower()
        if target == sname or target == skr or sname:find(target, 1, true) then
            found_id = s.id
            found_name = s.name
            break
        end
    end

    if not found_id then
        ctx:send("그런 스킬을 찾을 수 없습니다.")
        return
    end

    local current = ctx:get_skill_proficiency(ch, found_id)
    if current >= 85 then
        ctx:send("이미 충분히 숙련되어 있습니다. 실전에서 더 배우세요.")
        return
    end

    local gain = ctx:random(10, 15)
    local new_prof = ctx:practice_skill(found_id, gain)
    ctx:set_player_data("practices", practices_left - 1)
    ctx:send(found_name .. "을(를) 연습합니다. (" .. current .. "% → " .. new_prof .. "%)")
end, "연습")

-- ── examine — inspect item/mob with condition + container view ──

register_command("examine", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 조사하시겠습니까?")
        return
    end
    local ch = ctx.char
    if not ch then return end

    -- Check inventory first for items
    local obj = ctx:find_obj_inv(args)
    if not obj then
        obj = ctx:find_obj_room(args)
    end
    if not obj then
        obj = ctx:find_obj_equip(args)
    end

    if obj then
        -- Show item info
        ctx:send("{bright_cyan}" .. obj.proto.short_desc .. "{reset}")
        if obj.proto.long_desc and obj.proto.long_desc ~= "" then
            ctx:send(obj.proto.long_desc)
        end
        ctx:send("종류: " .. obj.proto.item_type .. "  무게: " .. tostring(obj.proto.weight) .. "  가치: " .. tostring(obj.proto.cost))

        -- Show condition
        local conditions = {"최상", "양호", "보통", "낡음", "파손"}
        local cost = obj.proto.cost or 1
        local cond_idx = 1
        if cost < 10 then cond_idx = 4
        elseif cost < 50 then cond_idx = 3
        elseif cost < 200 then cond_idx = 2 end
        ctx:send("상태: " .. conditions[cond_idx])

        -- Show affects
        local affects = obj.proto.affects
        if affects then
            local ok, len = pcall(function() return #affects end)
            if ok and len > 0 then
                for i = 0, len - 1 do
                    local ok2, aff = pcall(function() return affects[i] end)
                    if ok2 and aff then
                        local ok3, loc = pcall(function() return aff.location end)
                        local ok4, mod = pcall(function() return aff.modifier end)
                        if ok3 and ok4 then
                            local sign = mod > 0 and "+" or ""
                            ctx:send("  " .. tostring(loc) .. " " .. sign .. tostring(mod))
                        end
                    end
                end
            end
        end

        -- Container contents
        if obj.proto.item_type == "container" then
            local contents = obj.contains
            if contents then
                local ok, len = pcall(function() return #contents end)
                if ok and len > 0 then
                    ctx:send("{yellow}안에 들어있는 것:{reset}")
                    for i = 0, len - 1 do
                        local ok2, item = pcall(function() return contents[i] end)
                        if ok2 and item then
                            ctx:send("  " .. item.proto.short_desc)
                        end
                    end
                else
                    ctx:send("안에는 아무것도 없습니다.")
                end
            else
                ctx:send("안에는 아무것도 없습니다.")
            end
        end
        return
    end

    -- Not an item, try look at char/room
    ctx:call_command("look", args)
end, "조사")

-- ── consider — with HP comparison ──────────────────────────────

register_command("consider", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 평가하시겠습니까?")
        return
    end
    local ch = ctx.char
    if not ch then return end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    local diff = target.level - ch.level
    local msg
    if diff <= -10 then
        msg = "{cyan}이제 눈을 감고도 이길 수 있습니다.{reset}"
    elseif diff <= -5 then
        msg = "{green}쉬운 상대입니다.{reset}"
    elseif diff <= -2 then
        msg = "{green}어렵지 않은 상대입니다.{reset}"
    elseif diff <= 2 then
        msg = "{yellow}꽤 대등한 상대입니다.{reset}"
    elseif diff <= 5 then
        msg = "{red}조금 힘든 싸움이 될 것 같습니다.{reset}"
    elseif diff <= 10 then
        msg = "{bright_red}매우 위험한 상대입니다!{reset}"
    else
        msg = "{bright_red}자살 행위입니다!!!{reset}"
    end
    ctx:send(msg)

    -- HP comparison
    local hp_ratio = target.hp / math.max(1, target.max_hp)
    local hp_msg
    if hp_ratio >= 1.0 then
        hp_msg = "완벽한 상태입니다."
    elseif hp_ratio >= 0.75 then
        hp_msg = "약간의 상처가 있습니다."
    elseif hp_ratio >= 0.50 then
        hp_msg = "상당한 부상을 입고 있습니다."
    elseif hp_ratio >= 0.25 then
        hp_msg = "심각한 부상 상태입니다."
    else
        hp_msg = "거의 죽어가고 있습니다!"
    end
    ctx:send(target.name .. ": " .. hp_msg)
end, "평가")

-- ── where ───────────────────────────────────────────────────────

register_command("where", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    if not args or args == "" then
        local results = ctx:get_zone_chars()
        ctx:send("{bright_cyan}-- 주변 플레이어 --{reset}")
        local found = false
        for i = 1, #results do
            local r = results[i]
            if not r.char.is_npc then
                ctx:send("  " .. r.char.name .. " — " .. r.room_name)
                found = true
            end
        end
        if not found then
            ctx:send("  주변에 다른 플레이어가 없습니다.")
        end
    else
        local results = ctx:get_zone_chars(nil, args)
        ctx:send("{bright_cyan}-- '" .. args .. "' 탐색 결과 --{reset}")
        if #results == 0 then
            ctx:send("  찾을 수 없습니다.")
        else
            for i = 1, #results do
                local r = results[i]
                ctx:send("  " .. r.char.name .. " — " .. r.room_name)
            end
        end
    end
end, "어디")

-- ── score (tbaMUD original format) ──────────────────────────────

register_command("score", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local cls_name = get_class_name(ch.class_id)
    local sex_name = "중성"
    local sex = ctx:get_player_data("sex") or 0
    if sex == 1 then sex_name = "남성"
    elseif sex == 2 then sex_name = "여성" end
    local age = ctx:get_player_data("age") or 17
    local title = ctx:get_player_data("title") or ""

    -- Compute AC from base + equipment
    local ac = 100
    local equip = ctx:get_equipment()
    for i = 1, #equip do
        local obj = equip[i].obj
        local affects = obj.proto.affects
        if affects then
            local ok, len = pcall(function() return #affects end)
            if ok then
                for j = 0, len - 1 do
                    local aff_ok, aff = pcall(function() return affects[j] end)
                    if aff_ok and aff then
                        local loc = aff.location or ""
                        if loc == "ARMOR" or loc == "AC" then
                            ac = ac + (aff.modifier or 0)
                        end
                    end
                end
            end
        end
    end

    local alignment = ch.proto.alignment or 0

    -- Age
    ctx:send("당신은 " .. age .. "살입니다.")

    -- HP / Mana / Move
    ctx:send("체력 {green}" .. ch.hp .. "(" .. ch.max_hp .. "){reset}, " ..
             "마나 {cyan}" .. ch.mana .. "(" .. ch.max_mana .. "){reset}, " ..
             "이동력 " .. ch.move .. "(" .. ch.max_move .. ")입니다.")

    -- AC / Alignment
    ctx:send("방어도 " .. math.floor(ac / 10) .. "/10, 성향 " .. alignment .. "입니다.")

    -- Experience / Gold
    ctx:send("경험치 {yellow}" .. format_number(ch.experience) .. "{reset}, " ..
             "골드 {yellow}" .. format_number(ch.gold) .. "{reset}입니다.")

    -- Next level
    if ch.level < 31 then
        local needed = exp_to_next(ch)
        ctx:send("다음 레벨까지 {yellow}" .. format_number(needed) .. "{reset} 경험치가 필요합니다.")
    end

    -- Stats
    local stats = ch.stats or {}
    local function gs(k) local ok, v = pcall(function() return stats[k] end); return ok and v or 0 end
    ctx:send("힘: " .. gs("str") .. "  민첩: " .. gs("dex") .. "  체력: " .. gs("con") ..
             "  지능: " .. gs("int") .. "  지혜: " .. gs("wis") .. "  매력: " .. gs("cha"))

    -- Hitroll / Damroll
    ctx:send("히트롤: " .. ch.hitroll .. "  댐롤: " .. ch.damroll)

    -- Rank line
    local rank = "당신은 레벨 " .. ch.level .. " " .. cls_name .. " " .. ch.name
    if title and title ~= "" then
        rank = rank .. " " .. title
    end
    rank = rank .. "입니다."
    ctx:send(rank)

    -- Position
    if ch.position == 7 and ch.fighting then
        ctx:send("현재 " .. ch.fighting.name .. "과(와) 전투 중입니다!")
    else
        local pos_msg = POS_NAMES[ch.position] or "서 있습니다"
        ctx:send("현재 " .. pos_msg .. ".")
    end

    -- Active affects
    local aff_names = {}
    local affects = ch.affects
    if affects then
        local ok, len = pcall(function() return #affects end)
        if ok then
            for i = 0, len - 1 do
                local aff_ok, aff = pcall(function() return affects[i] end)
                if aff_ok and aff then
                    local name = aff.name or aff.spell or ""
                    if name ~= "" then
                        local dur = aff.duration or 0
                        table.insert(aff_names, name .. "(" .. dur .. ")")
                    end
                end
            end
        end
    end
    if #aff_names > 0 then
        ctx:send("활성 효과: " .. table.concat(aff_names, ", "))
    end
end, "점수")

-- ── who (tbaMUD original format — Immortals/Mortals split) ──────

register_command("who", function(ctx, args)
    local players = ctx:get_players()
    local immortals = {}
    local mortals = {}

    for i = 1, #players do
        local p = players[i]
        local cls_name = get_class_name(p.class_id)
        if #cls_name > 3 then cls_name = cls_name:sub(1, 3) end
        local level = p.level
        local display = "[" .. string.format("%3d", level) .. " " ..
                        string.format("%-3s", cls_name) .. "] " .. p.name

        -- Flags
        local flags = {}
        if p.position == 4 then table.insert(flags, "잠듦") end
        if p.position == 5 then table.insert(flags, "휴식") end
        if p.position == 7 then table.insert(flags, "전투") end
        if #flags > 0 then
            display = display .. " (" .. table.concat(flags, ", ") .. ")"
        end

        if level >= 31 then
            table.insert(immortals, display)
        else
            table.insert(mortals, display)
        end
    end

    local lines = {}
    if #immortals > 0 then
        table.insert(lines, "{yellow}신들{reset}")
        table.insert(lines, "{yellow}────{reset}")
        for _, im in ipairs(immortals) do
            table.insert(lines, "  {yellow}" .. im .. "{reset}")
        end
        table.insert(lines, "")
    end
    if #mortals > 0 then
        table.insert(lines, "모험가들")
        table.insert(lines, "────────")
        for _, m in ipairs(mortals) do
            table.insert(lines, "  " .. m)
        end
        table.insert(lines, "")
    end
    local total = #immortals + #mortals
    table.insert(lines, total .. "명의 모험가가 접속 중입니다.")
    ctx:send(table.concat(lines, "\r\n"))
end, "누구")

-- ── inventory (tbaMUD grouped items) ────────────────────────────

register_command("inventory", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local inv = ctx:get_inventory()

    ctx:send("소지품:")
    if #inv == 0 then
        ctx:send("  아무것도 없습니다.")
        return
    end

    -- Group by short_description
    local counts = {}
    local order = {}
    local display_map = {}
    for i = 1, #inv do
        local obj = inv[i]
        local desc = obj.proto.short_desc
        if not counts[desc] then
            counts[desc] = 0
            table.insert(order, desc)
            local mods = obj_modifiers(obj)
            if mods ~= "" then
                display_map[desc] = desc .. " " .. mods
            else
                display_map[desc] = desc
            end
        end
        counts[desc] = counts[desc] + 1
    end

    for _, desc in ipairs(order) do
        local display = display_map[desc]
        if counts[desc] > 1 then
            ctx:send("  (" .. counts[desc] .. ") " .. display)
        else
            ctx:send("  " .. display)
        end
    end
end, "소지품")

-- i → inventory alias
register_command("i", function(ctx, args)
    ctx:call_command("inventory", args or "")
end)

-- ── equipment (tbaMUD 18-slot display) ──────────────────────────

register_command("equipment", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local equip = ctx:get_equipment()

    ctx:send("착용 장비:")
    if #equip == 0 then
        ctx:send("  아무것도 착용하고 있지 않습니다.")
        return
    end

    for i = 1, #equip do
        local slot = equip[i].slot
        local obj = equip[i].obj
        local label = WEAR_WHERE[slot] or "<어딘가에>          "
        local mods = obj_modifiers(obj)
        local name = obj.proto.short_desc
        if mods ~= "" then name = name .. " " .. mods end
        ctx:send("  " .. label .. name)
    end
end, "장비")

-- eq → equipment alias
register_command("eq", function(ctx, args)
    ctx:call_command("equipment", args or "")
end)

-- ── exits (tbaMUD format with room names) ───────────────────────

register_command("exits", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local room = ctx:get_room()
    if not room then return end

    local exits = ctx:get_exits()
    local lines = {"확인 가능한 출구:"}
    local found = false

    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction < 6 then
            local dir_name = DIR_NAMES[ex.direction + 1]
            if room:has_door(ex.direction) and room:is_door_closed(ex.direction) then
                local kw = ex.keywords or "문"
                if kw == "" then kw = "문" end
                kw = kw:match("^%S+") or kw
                table.insert(lines, "  " .. string.format("%-4s", dir_name) ..
                             " - " .. kw .. "이(가) 닫혀 있습니다.")
            else
                local dest = ctx:get_room(ex.to_room)
                local dest_name = "알 수 없음"
                if dest then dest_name = dest.name end
                table.insert(lines, "  " .. string.format("%-4s", dir_name) ..
                             " - " .. dest_name)
            end
            found = true
        end
    end

    if not found then
        table.insert(lines, "  없습니다.")
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "출구")

-- ── affects — show active spell/skill effects ────────────────────

local SPELL_NAMES = {
    [1]="매직미사일", [2]="불꽃손", [3]="냉기의손길", [4]="번개",
    [5]="화염구", [6]="색광선", [7]="가벼운치유", [8]="심각한치유",
    [9]="치유", [10]="갑옷", [11]="축복", [12]="힘", [13]="투명",
    [14]="보호막", [15]="실명", [16]="저주", [17]="독", [18]="수면",
    [19]="투명감지", [20]="귀환", [21]="지진", [22]="사악퇴치",
    [23]="선량퇴치", [24]="소환", [25]="물건탐지", [26]="매혹",
    [27]="저주해제", [28]="해독", [29]="그룹치유", [30]="그룹갑옷",
    [31]="적외선시야", [32]="수면보행", [33]="순간이동", [34]="무기강화",
    [1001]="은신", [1002]="숨기",
}

register_command("affects", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local affects = ch.affects
    if not affects then
        ctx:send("활성 효과가 없습니다.")
        return
    end

    local ok, len = pcall(function() return #affects end)
    if not ok or len == 0 then
        ctx:send("활성 효과가 없습니다.")
        return
    end

    ctx:send("{bright_cyan}--- 활성 효과 ---{reset}")
    local found = false
    for i = 0, len - 1 do
        local aok, aff = pcall(function() return affects[i] end)
        if aok and aff then
            local spell_id = aff.spell_id or aff.id or 0
            local name = SPELL_NAMES[spell_id] or ("효과 #" .. tostring(spell_id))
            local dur = aff.duration or 0
            local detail = name .. " — " .. dur .. " 틱 남음"
            if dur == -1 then
                detail = name .. " — 영구"
            end
            ctx:send("  " .. detail)
            found = true
        end
    end
    if not found then
        ctx:send("활성 효과가 없습니다.")
    end
end, "효과")

-- ── levels — show experience table for current class ─────────────

register_command("levels", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local cls = ch.class_id or 0
    local tbl = EXP_TABLE[cls] or EXP_TABLE[0]
    local cls_name = get_class_name(cls)

    ctx:send("{bright_cyan}--- " .. cls_name .. " 경험치 표 ---{reset}")
    for lv = 1, 31 do
        local exp_needed = tbl[lv] or 0
        local marker = ""
        if lv == ch.level then marker = " {bright_yellow}<-- 현재{reset}" end
        ctx:send(string.format("  레벨 %2d: %12s%s", lv, format_number(exp_needed), marker))
    end
end, "레벨표")
