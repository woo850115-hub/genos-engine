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

-- ── 칭호 (cmdno=48, title) ────────────────────────────────────
register_command("칭호", function(ctx, args)
    if not args or args == "" then
        ctx:send("칭호를 입력해주세요.")
        return
    end
    ctx:set_player_data("title", args)
    ctx:send("칭호가 '" .. args .. "'(으)로 설정되었습니다.")
end)
