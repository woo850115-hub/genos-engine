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
    ctx:send("현재 시각을 알 수 없습니다. (구현 예정)")
end, "시간")

-- ── weather ─────────────────────────────────────────────────────

register_command("weather", function(ctx, args)
    ctx:send("날씨는 맑습니다. (구현 예정)")
end, "날씨")

-- ── examine ─────────────────────────────────────────────────────

register_command("examine", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 조사하시겠습니까?")
        return
    end
    ctx:call_command("look", args)
end, "조사")

-- ── consider ────────────────────────────────────────────────────

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
        msg = "이제 눈을 감고도 이길 수 있습니다."
    elseif diff <= -5 then
        msg = "쉬운 상대입니다."
    elseif diff <= -2 then
        msg = "어렵지 않은 상대입니다."
    elseif diff <= 2 then
        msg = "꽤 대등한 상대입니다."
    elseif diff <= 5 then
        msg = "조금 힘든 싸움이 될 것 같습니다."
    elseif diff <= 10 then
        msg = "매우 위험한 상대입니다!"
    else
        msg = "자살 행위입니다!!!"
    end
    ctx:send(msg)
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
