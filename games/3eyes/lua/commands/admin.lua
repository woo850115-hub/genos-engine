-- admin.lua — 3eyes DM/admin commands (~60 commands)
-- Original: dm1.c ~ dm6.c, command5.c (admin section)
-- DM levels: ZONEMAKER(13) < REALZONEMAKER(14) < SUB_DM(15) < DM(16) < ME(17)

-- ══════════════════════════════════════════════════════════════════
-- Helper: DM level check
-- ══════════════════════════════════════════════════════════════════

local function is_dm(ctx, min_class)
    min_class = min_class or CLASS_DM
    local cls = ctx.char.class_id or 0
    return cls >= min_class
end

local function dm_deny(ctx)
    ctx:send("관리자 전용 명령어입니다.")
end

-- ══════════════════════════════════════════════════════════════════
-- 1. TELEPORT / MOVEMENT
-- ══════════════════════════════════════════════════════════════════

-- *순간이동 — 방 이동 (dm1.c)
register_command("*순간이동", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *순간이동 <방번호|플레이어이름>")
        return
    end
    local vnum = tonumber(args)
    if not vnum then
        -- Try to find player by name
        local target = ctx:find_player(args)
        if target and target.room then
            vnum = target.room.vnum
        else
            ctx:send("그런 방이나 플레이어를 찾을 수 없습니다.")
            return
        end
    end
    local ok = ctx:teleport_to(vnum)
    if ok then
        ctx:send("{bright_cyan}" .. vnum .. "번 방으로 이동합니다.{reset}")
        ctx:defer_look()
    else
        ctx:send("그런 방이 존재하지 않습니다.")
    end
end)

-- *소환 — 대상 소환 (dm1.c)
register_command("*소환", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *소환 <대상> [방번호]")
        return
    end
    local target_name, dest_str = args:match("^(%S+)%s*(%S*)$")
    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("플레이어 " .. (target_name or "?") .. "을(를) 찾을 수 없습니다.")
        return
    end
    local dest_vnum = tonumber(dest_str)
    if not dest_vnum then
        dest_vnum = ctx:get_room_vnum()
    end
    ctx:move_char_to(target, dest_vnum)
    ctx:send("{green}" .. target.name .. "을(를) " .. dest_vnum .. "번 방으로 소환했습니다.{reset}")
    ctx:send_to(target, "{bright_cyan}관리자에 의해 이동되었습니다.{reset}")
end)

-- *원격 — 원격 명령 실행 (dm1.c)
register_command("*원격", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *원격 <방번호> <명령어>")
        return
    end
    local vnum_str, cmd = args:match("^(%d+)%s+(.+)$")
    if not vnum_str or not cmd then
        ctx:send("사용법: *원격 <방번호> <명령어>")
        return
    end
    local orig_room = ctx:get_room_vnum()
    local vnum = tonumber(vnum_str)
    local ok = ctx:teleport_to(vnum)
    if ok then
        ctx:call_command(cmd)
        ctx:teleport_to(orig_room)
    else
        ctx:send("그런 방이 존재하지 않습니다.")
    end
end)

-- *텔레포트 — 대상을 특정 방으로 (dm2.c)
register_command("*텔레포트", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *텔레포트 <대상> <방번호>")
        return
    end
    local target_name, vnum_str = args:match("^(%S+)%s+(%d+)$")
    if not target_name or not vnum_str then
        ctx:send("사용법: *텔레포트 <대상> <방번호>")
        return
    end
    local target = ctx:find_player(target_name) or ctx:find_char(target_name)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    local vnum = tonumber(vnum_str)
    ctx:move_char_to(target, vnum)
    ctx:send("{green}" .. target.name .. "을(를) " .. vnum .. "번 방으로 텔레포트시켰습니다.{reset}")
end)

-- ══════════════════════════════════════════════════════════════════
-- 2. LOAD / CREATE / DESTROY
-- ══════════════════════════════════════════════════════════════════

-- *로드 — 몬스터/아이템 생성 (dm1.c)
register_command("*로드", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *로드 mob|obj <vnum> [수량]")
        return
    end
    local kind, vnum_str, count_str = args:match("^(%S+)%s+(%d+)%s*(%d*)$")
    if not kind or not vnum_str then
        ctx:send("사용법: *로드 mob|obj <vnum> [수량]")
        return
    end
    local vnum = tonumber(vnum_str)
    local count = tonumber(count_str) or 1
    count = math.min(count, 20)  -- Safety cap

    if kind == "mob" or kind == "몬스터" or kind == "m" then
        for _ = 1, count do
            local mob = ctx:load_mob(vnum)
            if not mob then
                ctx:send("몬스터 #" .. vnum .. " 생성 실패.")
                return
            end
        end
        ctx:send("{green}몬스터 #" .. vnum .. " ×" .. count .. " 소환 완료.{reset}")
    elseif kind == "obj" or kind == "아이템" or kind == "o" then
        for _ = 1, count do
            local obj = ctx:load_obj(vnum)
            if not obj then
                ctx:send("아이템 #" .. vnum .. " 생성 실패.")
                return
            end
        end
        ctx:send("{green}아이템 #" .. vnum .. " ×" .. count .. " 생성 완료.{reset}")
    else
        ctx:send("사용법: *로드 mob|obj <vnum> [수량]")
    end
end)

-- *제거 — 방 정리 (dm1.c)
register_command("*제거", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    if args and args ~= "" then
        -- Purge specific target
        local target = ctx:find_char(args)
        if target and target.is_npc then
            ctx:extract_char(target)
            ctx:send("{yellow}" .. target.name .. "을(를) 제거했습니다.{reset}")
        else
            ctx:send("NPC만 제거할 수 있습니다.")
        end
    else
        ctx:purge_room()
        ctx:send("{yellow}방을 정리했습니다.{reset}")
    end
end)

-- *파괴 — 아이템 파괴 (dm2.c)
register_command("*파괴", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *파괴 <아이템>")
        return
    end
    local item = ctx:find_inv_item(args)
    if item then
        ctx:obj_from_char(item)
        ctx:send("{yellow}" .. item.name .. "을(를) 파괴했습니다.{reset}")
    else
        ctx:send("그런 아이템을 가지고 있지 않습니다.")
    end
end)

-- ══════════════════════════════════════════════════════════════════
-- 3. PLAYER MANAGEMENT
-- ══════════════════════════════════════════════════════════════════

-- *회복 — 완전 회복 (dm1.c)
register_command("*회복", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    local target = ctx.char
    if args and args ~= "" then
        target = ctx:find_char(args) or ctx:find_player(args)
        if not target then
            ctx:send("대상을 찾을 수 없습니다.")
            return
        end
    end
    target.hp = target.max_hp
    target.mana = target.max_mana
    target.move = target.max_move
    ctx:send("{bright_green}" .. target.name .. "을(를) 완전 회복시켰습니다.{reset}")
    if target ~= ctx.char then
        ctx:send_to(target, "{bright_green}관리자에 의해 완전 회복되었습니다.{reset}")
    end
end)

-- *승급 — 레벨 설정 (dm2.c)
register_command("*승급", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *승급 <대상> <레벨>")
        return
    end
    local target_name, level_str = args:match("^(%S+)%s+(%d+)$")
    if not target_name or not level_str then
        ctx:send("사용법: *승급 <대상> <레벨>")
        return
    end
    local target = ctx:find_char(target_name) or ctx:find_player(target_name)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    local new_level = tonumber(level_str)
    target.level = new_level
    ctx:send("{bright_yellow}" .. target.name .. "의 레벨을 " .. new_level .. "로 설정했습니다.{reset}")
    ctx:send_to(target, "{bright_yellow}레벨이 " .. new_level .. "로 설정되었습니다.{reset}")
end)

-- *설정 — 속성 설정 (dm3.c — major multi-purpose command)
register_command("*설정", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *설정 <대상> <속성> <값>")
        ctx:send("  속성: level, class, hp, maxhp, mana, maxmana, gold, exp,")
        ctx:send("        str, dex, con, int, pie, alignment, race")
        return
    end
    local target_name, attr, value_str = args:match("^(%S+)%s+(%S+)%s+(.+)$")
    if not target_name or not attr then
        ctx:send("사용법: *설정 <대상> <속성> <값>")
        return
    end
    local target = ctx:find_char(target_name) or ctx:find_player(target_name)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    local value = tonumber(value_str)
    if not value and attr ~= "name" then
        ctx:send("값은 숫자여야 합니다.")
        return
    end

    local attr_map = {
        level = function(t, v) t.level = v end,
        class = function(t, v) t.class_id = v end,
        hp = function(t, v) t.hp = v end,
        maxhp = function(t, v) t.max_hp = v end,
        mana = function(t, v) t.mana = v end,
        maxmana = function(t, v) t.max_mana = v end,
        gold = function(t, v) t.gold = v end,
        exp = function(t, v) t.experience = v end,
        alignment = function(t, v) t.alignment = v end,
        race = function(t, v) t.race_id = v end,
        str = function(t, v) if t.stats then t.stats.str = v end end,
        dex = function(t, v) if t.stats then t.stats.dex = v end end,
        con = function(t, v) if t.stats then t.stats.con = v end end,
        int = function(t, v) if t.stats then t.stats["int"] = v end end,
        pie = function(t, v) if t.stats then t.stats.pie = v end end,
    }

    local setter = attr_map[attr:lower()]
    if not setter then
        ctx:send("알 수 없는 속성: " .. attr)
        return
    end
    pcall(function() setter(target, value) end)
    ctx:send("{green}" .. target.name .. "의 " .. attr .. "을(를) " .. tostring(value_str) .. "로 설정했습니다.{reset}")
end)

-- *강제 — 대상에게 명령 강제 (dm2.c)
register_command("*강제", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *강제 <대상> <명령어>")
        return
    end
    local target_name, cmd = args:match("^(%S+)%s+(.+)$")
    if not target_name or not cmd then
        ctx:send("사용법: *강제 <대상> <명령어>")
        return
    end

    if target_name:lower() == "all" or target_name == "모두" then
        -- Force all players
        ctx:force_all(cmd)
        ctx:send("{yellow}모든 플레이어에게 '" .. cmd .. "' 명령을 강제합니다.{reset}")
        return
    end

    local target = ctx:find_player(target_name) or ctx:find_char(target_name)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    ctx:force_char(target, cmd)
    ctx:send("{yellow}" .. target.name .. "에게 '" .. cmd .. "' 명령을 강제합니다.{reset}")
end)

-- *냉동 — 동결 (dm3.c)
register_command("*냉동", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *냉동 <대상>")
        return
    end
    local target = ctx:find_player(args)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    local frozen = ctx:get_player_data_for(target, "frozen")
    if frozen then
        ctx:set_player_data_for(target, "frozen", false)
        ctx:send("{green}" .. target.name .. "의 동결을 해제합니다.{reset}")
        ctx:send_to(target, "{green}동결이 해제되었습니다.{reset}")
    else
        ctx:set_player_data_for(target, "frozen", true)
        ctx:send("{yellow}" .. target.name .. "을(를) 동결합니다.{reset}")
        ctx:send_to(target, "{bright_red}관리자에 의해 동결되었습니다! 명령어를 사용할 수 없습니다.{reset}")
    end
end)

-- *감옥 — 감옥 이송 (dm3.c)
register_command("*감옥", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *감옥 <대상>")
        return
    end
    local target = ctx:find_player(args)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    ctx:move_char_to(target, 11971)  -- SPIRIT_ROOM as jail
    ctx:send("{yellow}" .. target.name .. "을(를) 감옥에 가뒀습니다.{reset}")
    ctx:send_to(target, "{bright_red}관리자에 의해 감옥에 갇혔습니다!{reset}")
end)

-- *밴 — 접속 차단 (dm4.c)
register_command("*밴", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *밴 <대상>")
        return
    end
    local target = ctx:find_player(args)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    ctx:send_to(target, "{bright_red}접속이 차단되었습니다.{reset}")
    ctx:disconnect(target)
    ctx:send("{yellow}" .. args .. "을(를) 차단했습니다.{reset}")
end)

-- *침묵 — 채팅 금지 (dm3.c)
register_command("*침묵", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *침묵 <대상>")
        return
    end
    local target = ctx:find_player(args)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    local muted = ctx:get_player_data_for(target, "muted")
    if muted then
        ctx:set_player_data_for(target, "muted", false)
        ctx:send("{green}" .. target.name .. "의 채팅금지를 해제합니다.{reset}")
    else
        ctx:set_player_data_for(target, "muted", true)
        ctx:send("{yellow}" .. target.name .. "을(를) 채팅금지합니다.{reset}")
        ctx:send_to(target, "{bright_red}채팅이 금지되었습니다.{reset}")
    end
end)

-- ══════════════════════════════════════════════════════════════════
-- 4. INFORMATION / STAT
-- ══════════════════════════════════════════════════════════════════

-- *스탯 — 상세 정보 (dm1.c — room/mob/obj/player)
register_command("*스탯", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    if not args or args == "" then
        -- Default: stat room
        args = "room"
    end

    local sub, target_str = args:match("^(%S+)%s*(.*)$")
    sub = (sub or ""):lower()

    if sub == "room" or sub == "방" then
        local room = ctx:get_room()
        if not room then
            ctx:send("방 정보를 가져올 수 없습니다.")
            return
        end
        local lines = {
            "{bright_cyan}━━━━━━━━━━ 방 정보 ━━━━━━━━━━{reset}",
            "  VNUM: " .. (room.vnum or "?"),
            "  이름: " .. (room.name or "?"),
            "  존: " .. (room.zone_id or "?"),
        }
        local ok_flags, flags = pcall(function() return room.flags end)
        if ok_flags and flags then
            local flag_strs = {}
            for i = 0, 50 do
                local ok, f = pcall(function() return flags[i] end)
                if not ok or f == nil then break end
                flag_strs[#flag_strs + 1] = tostring(f)
            end
            lines[#lines + 1] = "  플래그: " .. table.concat(flag_strs, ", ")
        end
        local ok_exits, exits = pcall(function() return room.exits end)
        if ok_exits and exits then
            local exit_strs = {}
            for i = 0, 10 do
                local ok, ex = pcall(function() return exits[i] end)
                if not ok or not ex then break end
                local dir_name = ({"북","동","남","서","위","아래"})[i + 1] or tostring(i)
                exit_strs[#exit_strs + 1] = dir_name .. "→" .. (ex.to_vnum or "?")
            end
            lines[#lines + 1] = "  출구: " .. table.concat(exit_strs, ", ")
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    if sub == "mob" or sub == "몬스터" or sub == "char" then
        local target = ctx:find_char(target_str)
        if not target then
            ctx:send("대상을 찾을 수 없습니다.")
            return
        end
        local lines = {
            "{bright_cyan}━━━━━━━━━━ 캐릭터 정보 ━━━━━━━━━━{reset}",
            "  이름: " .. (target.name or "?"),
            "  VNUM: " .. (target.vnum or "N/A"),
            "  레벨: " .. (target.level or 0),
            "  클래스: " .. (target.class_id or 0) ..
                " (" .. (THREEEYES_CLASSES[target.class_id] or "?") .. ")",
            "  HP: " .. (target.hp or 0) .. "/" .. (target.max_hp or 0),
            "  MP: " .. (target.mana or 0) .. "/" .. (target.max_mana or 0),
            "  골드: " .. (target.gold or 0),
            "  경험치: " .. (target.experience or 0),
            "  AC: " .. (target.armor_class or 100),
            "  THAC0: " .. (target.hitroll or 0),
            "  NPC: " .. (target.is_npc and "예" or "아니오"),
        }
        -- Stats
        if target.stats then
            local stat_line = "  스탯:"
            for _, s in ipairs({"str","dex","con","int","pie"}) do
                stat_line = stat_line .. " " .. s .. "=" .. (target.stats[s] or "?")
            end
            lines[#lines + 1] = stat_line
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    if sub == "obj" or sub == "아이템" then
        local item = ctx:find_inv_item(target_str)
        if not item then
            item = ctx:find_equip_item(target_str)
        end
        if not item then
            ctx:send("아이템을 찾을 수 없습니다.")
            return
        end
        local lines = {
            "{bright_cyan}━━━━━━━━━━ 아이템 정보 ━━━━━━━━━━{reset}",
            "  이름: " .. (item.name or "?"),
        }
        if item.proto then
            lines[#lines + 1] = "  VNUM: " .. (item.proto.vnum or "?")
            lines[#lines + 1] = "  타입: " .. tostring(item.proto.item_type or "?")
            lines[#lines + 1] = "  무게: " .. (item.proto.weight or 0)
            lines[#lines + 1] = "  가격: " .. (item.proto.cost or 0)
            local ok_adj, adj = pcall(function() return item.adjustment or 0 end)
            if ok_adj then
                lines[#lines + 1] = "  강화: +" .. adj
            end
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    if sub == "player" or sub == "플레이어" then
        local target = ctx:find_player(target_str)
        if not target then
            ctx:send("플레이어를 찾을 수 없습니다.")
            return
        end
        -- Use stat char for basic info + player_data
        ctx:call_command("*스탯", "char " .. target.name)
        return
    end

    ctx:send("사용법: *스탯 room|mob|obj|player [대상]")
end)

-- 어디 — 모든 플레이어 위치 (cmdno=210, 유저 레벨 명령어)
register_command("어디", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    local players = ctx:get_online_players()
    if not players then
        ctx:send("접속자가 없습니다.")
        return
    end
    local lines = {"{bright_cyan}━━━━━━━━━━ 접속자 위치 ━━━━━━━━━━{reset}"}
    for i = 0, 200 do
        local ok, p = pcall(function() return players[i] end)
        if not ok or not p then break end
        local room_vnum = "?"
        pcall(function()
            if p.room then room_vnum = tostring(p.room.vnum) end
        end)
        lines[#lines + 1] = string.format("  %-14s  방 %s  레벨 %d",
            p.name or "?", room_vnum, p.level or 0)
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- *존스탯 — 존 정보 (dm4.c)
register_command("*존스탯", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    local zone = ctx:get_zone()
    if not zone then
        ctx:send("존 정보를 가져올 수 없습니다.")
        return
    end
    local lines = {
        "{bright_cyan}━━━━━━━━━━ 존 정보 ━━━━━━━━━━{reset}",
        "  ID: " .. (zone.id or "?"),
        "  이름: " .. (zone.name or "?"),
    }
    pcall(function()
        lines[#lines + 1] = "  레벨범위: " .. (zone.level_min or "?") .. "-" .. (zone.level_max or "?")
        lines[#lines + 1] = "  리셋시간: " .. (zone.reset_interval or "?") .. "분"
    end)
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ══════════════════════════════════════════════════════════════════
-- 5. VISIBILITY
-- ══════════════════════════════════════════════════════════════════

-- *투명 — DM 투명 (dm2.c)
register_command("*투명", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if ctx:has_flag(PDMINV) then
        ctx:clear_flag(PDMINV)
        ctx:send("{green}DM 투명을 해제합니다. 이제 다른 플레이어에게 보입니다.{reset}")
    else
        ctx:set_flag(PDMINV)
        ctx:send("{yellow}DM 투명을 활성화합니다. 다른 플레이어에게 보이지 않습니다.{reset}")
    end
end)

-- *투명해제 — 투명 해제 (dm2.c)
register_command("*투명해제", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    ctx:clear_flag(PDMINV)
    ctx:clear_flag(PINVIS)
    ctx:clear_flag(PHIDDN)
    ctx:send("{green}모든 투명 효과를 해제합니다.{reset}")
end)

-- *엿보기 — 엿보기 (dm3.c)
register_command("*엿보기", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:stop_snooping()
        ctx:send("엿보기를 중지합니다.")
        return
    end
    local target = ctx:find_player(args)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    ctx:start_snooping(target)
    ctx:send("{yellow}" .. target.name .. "을(를) 엿봅니다.{reset}")
end)

-- ══════════════════════════════════════════════════════════════════
-- 6. SYSTEM
-- ══════════════════════════════════════════════════════════════════

-- *종료 — 서버 종료 (dm1.c)
register_command("*종료", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    ctx:send_all("{bright_red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send_all("{bright_red}  [시스템] 서버가 곧 종료됩니다...{reset}")
    ctx:send_all("{bright_red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:shutdown()
end)

-- *재부팅 — 서버 재시작 (dm1.c)
register_command("*재부팅", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    ctx:send_all("{bright_yellow}[시스템] 서버가 재시작됩니다...{reset}")
    ctx:reboot()
end)

-- *리로드 — Lua 스크립트 리로드 (dm1.c)
register_command("*리로드", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    ctx:reload_lua()
    ctx:send("{bright_green}Lua 스크립트를 다시 불러왔습니다.{reset}")
end)

-- *월드저장 — 월드 저장 (dm1.c)
register_command("*월드저장", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    ctx:save_world()
    ctx:send("{green}월드 데이터를 저장했습니다.{reset}")
end)

-- *공지 — 공지 (dm2.c)
register_command("*공지", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *공지 <메시지>")
        return
    end
    ctx:send_all("{bright_red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send_all("{bright_yellow}  [공지] " .. args .. "{reset}")
    ctx:send_all("{bright_red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
end)

-- ══════════════════════════════════════════════════════════════════
-- 7. ZONE MANAGEMENT
-- ══════════════════════════════════════════════════════════════════

-- *존리셋 — 존 리셋 (dm4.c)
register_command("*존리셋", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    local zone_id = tonumber(args)
    if zone_id then
        ctx:reset_zone(zone_id)
        ctx:send("{green}존 " .. zone_id .. "을(를) 리셋했습니다.{reset}")
    else
        ctx:reset_current_zone()
        ctx:send("{green}현재 존을 리셋했습니다.{reset}")
    end
end)

-- ══════════════════════════════════════════════════════════════════
-- 8. UTILITY DM COMMANDS
-- ══════════════════════════════════════════════════════════════════

-- *처형 — 즉사 (dm2.c)
register_command("*처형", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *처형 <대상>")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    if not target.is_npc and not is_dm(ctx, CLASS_ME) then
        ctx:send("{yellow}플레이어를 즉사시키려면 최고관리자(ME) 권한이 필요합니다.{reset}")
        return
    end
    target.hp = -10
    ctx:send("{bright_red}" .. target.name .. "을(를) 즉사시켰습니다!{reset}")
    ctx:send_room("{bright_red}" .. ctx.char.name .. "이(가) " ..
        target.name .. "을(를) 한 방에 죽입니다!{reset}")
    ctx:defer_death(target)
end)

-- *평화 — 전투 중지 (dm2.c)
register_command("*평화", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    ctx:peace_room()
    ctx:send("{green}이 방의 모든 전투를 중지합니다.{reset}")
    ctx:send_room("{bright_cyan}관리자가 평화를 선언합니다. 모든 전투가 중지됩니다.{reset}")
end)

-- *치료 — 치유 (DM shortcut)
register_command("*치료", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *치료 <대상> [HP량]")
        return
    end
    local target_name, amount_str = args:match("^(%S+)%s*(%S*)$")
    local target = ctx:find_char(target_name) or ctx:find_player(target_name)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    local amount = tonumber(amount_str) or target.max_hp
    target.hp = math.min(target.max_hp, target.hp + amount)
    ctx:send("{green}" .. target.name .. "을(를) " .. amount .. " HP 치유했습니다.{reset}")
end)

-- *지급 — DM이 아이템 지급 (dm2.c)
register_command("*지급", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *지급 <대상> <아이템vnum>")
        return
    end
    local target_name, vnum_str = args:match("^(%S+)%s+(%d+)$")
    if not target_name or not vnum_str then
        ctx:send("사용법: *지급 <대상> <아이템vnum>")
        return
    end
    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("플레이어를 찾을 수 없습니다.")
        return
    end
    local vnum = tonumber(vnum_str)
    local obj = ctx:create_obj(vnum)
    if obj then
        ctx:obj_to_char(obj, target)
        ctx:send("{green}" .. target.name .. "에게 " .. obj.name .. "을(를) 지급했습니다.{reset}")
        ctx:send_to(target, "{bright_green}관리자에게서 " .. obj.name .. "을(를) 받았습니다.{reset}")
    else
        ctx:send("아이템 #" .. vnum .. "을(를) 생성할 수 없습니다.")
    end
end)

-- *에코 — 방 메시지 (dm2.c)
register_command("*에코", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *에코 <메시지>")
        return
    end
    ctx:send_room(args)
end)

-- *전체에코 — 전체 메시지 (dm2.c)
register_command("*전체에코", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *전체에코 <메시지>")
        return
    end
    ctx:send_all(args)
end)

-- *플래그설정 — 대상 플래그 설정 (dm5.c)
register_command("*플래그설정", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *플래그설정 <대상> <플래그번호>")
        return
    end
    local target_name, flag_str = args:match("^(%S+)%s+(%d+)$")
    if not target_name or not flag_str then
        ctx:send("사용법: *플래그설정 <대상> <플래그번호>")
        return
    end
    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    local flag = tonumber(flag_str)
    pcall(function()
        local flags = target.flags or {}
        local found = false
        for _, f in ipairs(flags) do if f == flag then found = true; break end end
        if not found then flags[#flags + 1] = flag end
        target.flags = flags
    end)
    ctx:send("{green}" .. target.name .. "에 플래그 " .. flag .. " 설정.{reset}")
end)

-- *플래그해제 — 대상 플래그 해제 (dm5.c)
register_command("*플래그해제", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *플래그해제 <대상> <플래그번호>")
        return
    end
    local target_name, flag_str = args:match("^(%S+)%s+(%d+)$")
    if not target_name or not flag_str then
        ctx:send("사용법: *플래그해제 <대상> <플래그번호>")
        return
    end
    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("대상을 찾을 수 없습니다.")
        return
    end
    local flag = tonumber(flag_str)
    pcall(function()
        local flags = target.flags or {}
        local new_flags = {}
        for _, f in ipairs(flags) do
            if f ~= flag then new_flags[#new_flags + 1] = f end
        end
        target.flags = new_flags
    end)
    ctx:send("{green}" .. target.name .. "에서 플래그 " .. flag .. " 해제.{reset}")
end)

-- *가르침 — DM이 주문 가르치기 (dm5.c)
register_command("*가르침", function(ctx, args)
    if not is_dm(ctx) then dm_deny(ctx); return end
    if not args or args == "" then
        ctx:send("사용법: *가르침 <대상> <주문ID>")
        return
    end
    local target_name, spell_str = args:match("^(%S+)%s+(%d+)$")
    if not target_name or not spell_str then
        ctx:send("사용법: *가르침 <대상> <주문ID>")
        return
    end
    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("플레이어를 찾을 수 없습니다.")
        return
    end
    local spell_id = tonumber(spell_str)
    ctx:learn_spell_for(target, spell_id)
    ctx:send("{green}" .. target.name .. "에게 주문 #" .. spell_id .. "을(를) 가르쳤습니다.{reset}")
end)

-- *업타임 — 서버 가동시간 (dm6.c)
register_command("*업타임", function(ctx, args)
    if not is_dm(ctx, CLASS_ZONEMAKER) then dm_deny(ctx); return end
    local uptime = ctx:get_uptime() or 0
    local hours = math.floor(uptime / 3600)
    local mins = math.floor((uptime % 3600) / 60)
    local secs = math.floor(uptime % 60)
    ctx:send("{bright_cyan}서버 가동시간: " .. hours .. "시간 " .. mins .. "분 " .. secs .. "초{reset}")
end)

-- *접속자 — 접속자 상세 (dm6.c)
register_command("*접속자", function(ctx, args)
    if not is_dm(ctx, CLASS_SUB_DM) then dm_deny(ctx); return end
    local players = ctx:get_online_players()
    if not players then
        ctx:send("접속자가 없습니다.")
        return
    end
    local lines = {
        "{bright_cyan}━━━━━━━━━━ 접속자 상세 ━━━━━━━━━━{reset}",
        "{bright_cyan}  이름              레벨  클래스     IP{reset}",
        "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
    }
    for i = 0, 200 do
        local ok, p = pcall(function() return players[i] end)
        if not ok or not p then break end
        local class_name = THREEEYES_CLASSES[p.class_id] or "?"
        local ip = "?"
        pcall(function() ip = p.session.ip or "?" end)
        lines[#lines + 1] = string.format("  %-16s  %3d   %-10s %s",
            p.name or "?", p.level or 0, class_name, ip)
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)
