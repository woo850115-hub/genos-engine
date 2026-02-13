-- movement.lua — 3eyes 이동 명령어 (원본 cmdlist 기반)
-- 원본: command6.c (enter/open/close/lock/unlock/title)

-- ── 열어 (cmdno=23, open) ─────────────────────────────────────
register_command("열어", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 열고 싶으세요?")
        return
    end
    local dir = ctx:find_door(args)
    if dir < 0 then
        ctx:send("그런 출구는 없습니다.")
        return
    end
    if not ctx:has_door(dir) then
        ctx:send("그런 출구는 없습니다.")
        return
    end
    if ctx:is_door_locked(dir) then
        ctx:send("그것은 잠겨져 있습니다.")
        return
    end
    if not ctx:is_door_closed(dir) then
        ctx:send("벌써 열려져 있습니다.")
        return
    end
    ctx:set_door_state(dir, false)
    local dir_name = DIR_NAMES[dir + 1] or "?"
    ctx:send("당신은 " .. dir_name .. "쪽 출구를 열었습니다.")
    ctx:send_room(ch.name .. "이(가) " .. dir_name .. "쪽 출구를 열었습니다.")
end)

-- ── 닫아 (cmdno=24, close) ────────────────────────────────────
register_command("닫아", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 닫고 싶으세요?")
        return
    end
    local dir = ctx:find_door(args)
    if dir < 0 then
        ctx:send("그런 출구는 없습니다.")
        return
    end
    if not ctx:has_door(dir) then
        ctx:send("그런 출구는 없습니다.")
        return
    end
    if ctx:is_door_closed(dir) then
        ctx:send("벌써 닫혀져 있습니다.")
        return
    end
    ctx:set_door_state(dir, true)
    local dir_name = DIR_NAMES[dir + 1] or "?"
    ctx:send("당신은 " .. dir_name .. "쪽 출구를 닫습니다.")
    ctx:send_room(ch.name .. "이(가) " .. dir_name .. "쪽 출구를 닫습니다.")
end)

-- ── 잠궈 (cmdno=25, lock) — 원본 철자 ────────────────────────
register_command("잠궈", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 잠그고 싶으세요?")
        return
    end
    local dir = ctx:find_door(args)
    if dir < 0 or not ctx:has_door(dir) then
        ctx:send("그런 출구는 없습니다.")
        return
    end
    if not ctx:is_door_closed(dir) then
        ctx:send("먼저 닫아야 합니다.")
        return
    end
    if ctx:is_door_locked(dir) then
        ctx:send("이미 잠겨져 있습니다.")
        return
    end
    if not ctx:has_key(dir) then
        ctx:send("열쇠가 없습니다.")
        return
    end
    ctx:set_door_state(dir, true, true)
    local dir_name = DIR_NAMES[dir + 1] or "?"
    ctx:send("당신은 " .. dir_name .. "쪽 출구를 잠급니다.")
end)

-- ── 풀어 (cmdno=38, unlock) — 원본 철자 ──────────────────────
register_command("풀어", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 열고 싶으세요?")
        return
    end
    local dir = ctx:find_door(args)
    if dir < 0 or not ctx:has_door(dir) then
        ctx:send("그런 출구는 없습니다.")
        return
    end
    if not ctx:is_door_locked(dir) then
        ctx:send("잠겨져 있지 않습니다.")
        return
    end
    if not ctx:has_key(dir) then
        ctx:send("열쇠가 없습니다.")
        return
    end
    ctx:set_door_state(dir, true, false)
    local dir_name = DIR_NAMES[dir + 1] or "?"
    ctx:send("당신은 " .. dir_name .. "쪽 출구의 잠금을 풀었습니다.")
end)

-- ── 가 / 들어가 (cmdno=28, enter) ────────────────────────────
local function do_enter(ctx, args)
    if not args or args == "" then
        ctx:send("어디로 들어가시겠습니까?")
        return
    end
    local target = ctx:find_portal(args)
    if target then
        ctx:move_to(target)
        ctx:send("안으로 들어갑니다.")
        ctx:defer_look()
    else
        ctx:send("들어갈 수 있는 곳이 없습니다.")
    end
end

register_command("가", do_enter)
register_command("들어가", function(ctx, args) ctx:call_command("가", args or "") end)

-- ── 나가 (leave) — 방 나가기 (첫 번째 열린 출구로) ─────────────
register_command("나가", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.fighting then
        ctx:send("전투 중에는 나갈 수 없습니다!")
        return
    end
    local exits = ctx:get_exits()
    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction < 10 then
            local room = ctx:get_room()
            if room and not room:is_door_closed(ex.direction) then
                local dir_name = DIR_NAMES[ex.direction + 1] or "?"
                ctx:send_room(ch.name .. "이(가) " .. dir_name .. "쪽으로 나갑니다.")
                ctx:move_to(ex.to_room)
                ctx:send("당신은 " .. dir_name .. "쪽으로 나갑니다.")
                ctx:defer_look()
                return
            end
        end
    end
    ctx:send("나갈 수 있는 출구가 없습니다.")
end)
register_command("밖", function(ctx, args) ctx:call_command("나가", args or "") end)

-- ── 나가는길 (exits) — 출구 목록 표시 ──────────────────────────
register_command("나가는길", function(ctx, args)
    local exits = ctx:get_exits()
    if #exits == 0 then
        ctx:send("출구가 없습니다.")
        return
    end
    local dir_full = {"북쪽","동쪽","남쪽","서쪽","위","아래","남동","남서","북동","북서"}
    local lines = {"{bright_cyan}━━━ 나가는 길 ━━━{reset}"}
    for i = 1, #exits do
        local ex = exits[i]
        local dname = dir_full[ex.direction + 1] or ("방향" .. ex.direction)
        local room = ctx:get_room()
        local status = ""
        if room and room:is_door_closed(ex.direction) then status = " {red}(잠김){reset}" end
        lines[#lines + 1] = "  " .. dname .. status
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ── 칭호 (cmdno=48, title) ────────────────────────────────────
register_command("칭호", function(ctx, args)
    if not args or args == "" then
        ctx:send("칭호를 입력해주세요.")
        return
    end
    ctx:set_player_data("title", args)
    ctx:send("칭호가 '" .. args .. "'(으)로 설정되었습니다.")
end)
