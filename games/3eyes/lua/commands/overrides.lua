-- overrides.lua — 3eyes common 명령어 한글 override + 비원본 비활성화
-- common/lua에서 등록된 명령어를 3eyes 원본 이름으로 재등록하거나 비활성화

-- ══════════════════════════════════════════════════════════════════
-- 원본에 없는 common 명령어 비활성화
-- ══════════════════════════════════════════════════════════════════

register_command("exits", nil)      -- 원본에 없음
register_command("commands", nil)   -- 원본에 없음
register_command("junk", nil)       -- 원본에 없음
register_command("donate", nil)     -- 원본에 없음
register_command("unalias", nil)    -- 원본에 없음 (줄임말 해제는 줄임말 내에서 처리)
register_command("attack", nil)     -- 원본에 없음 (공격은 combat.lua에서 등록)
register_command("put", nil)        -- 원본에 없음 (넣어=버려에 매핑)
register_command("wimpy", nil)      -- 원본에 없음
register_command("sit", nil)        -- 원본에 없음

-- common의 영어 이름 제거 (3eyes game Lua에서 한글로 재등록됨)
register_command("kill", nil)       -- combat.lua: 공격
register_command("take", nil)       -- items.lua: 주워
register_command("get", nil)        -- items.lua: 주워
register_command("drop", nil)       -- items.lua: 버려
register_command("give", nil)       -- items.lua: 줘
register_command("say", nil)        -- comm.lua: 말
register_command("open", nil)       -- movement.lua: 열어
register_command("close", nil)      -- movement.lua: 닫아
register_command("lock", nil)       -- movement.lua: 잠궈
register_command("unlock", nil)     -- movement.lua: 풀어

-- ══════════════════════════════════════════════════════════════════
-- 끝 (quit, cmdno=51) — 원본: "끝"=quit (NOT "나가"!)
-- ══════════════════════════════════════════════════════════════════

local function do_quit(ctx, args)
    local ch = ctx.char
    if ch and ch.fighting then
        ctx:send("전투 중에는 나갈 수 없습니다!")
        return
    end
    ctx:defer_save()
    ctx:send("저장되었습니다. 안녕히 가세요!")
    ctx:close_session()
end

register_command("끝", do_quit)
register_command("quit", do_quit)   -- engine compat
register_command("save", function(ctx, args)
    ctx:defer_save()
    ctx:send("저장되었습니다.")
end)

-- ══════════════════════════════════════════════════════════════════
-- 도움말 (help, cmdno=53)
-- ══════════════════════════════════════════════════════════════════

local function do_help(ctx, args)
    local keyword = "help"
    if args and args ~= "" then keyword = args:lower() end
    local text = ctx:get_help(keyword)
    if not text then
        ctx:send("'" .. keyword .. "'에 대한 도움말이 없습니다.")
    elseif text:sub(1, 12) == "__MULTIPLE__" then
        local list = text:sub(14)
        ctx:send("여러 도움말이 발견되었습니다: " .. list)
    else
        ctx:send(text)
    end
end

register_command("도움말", do_help)
register_command("?", do_help)
register_command("help", do_help)   -- engine compat

-- ══════════════════════════════════════════════════════════════════
-- 자세 명령어 (position commands)
-- ══════════════════════════════════════════════════════════════════

-- ── 쉬어 (rest, cmdno=17) ───────────────────────────────────────
register_command("쉬어", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_RESTING then
        ctx:send("이미 쉬고 있습니다.")
        return
    end
    if ch.fighting then
        ctx:send("전투 중에는 쉴 수 없습니다!")
        return
    end
    ch.position = POS_RESTING
    ctx:send("쉬기 시작합니다.")
end)
register_command("rest", nil)  -- common 영어 제거

-- ── 일어서 (stand, cmdno=18) ────────────────────────────────────
register_command("일어서", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_STANDING then
        ctx:send("이미 서 있습니다.")
        return
    end
    ch.position = POS_STANDING
    ctx:send("일어섰습니다.")
end)
register_command("stand", nil)  -- common 영어 제거

-- ── 깨어 (wake, cmdno=19) ──────────────────────────────────────
register_command("깨어", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_STANDING then
        ctx:send("이미 서 있습니다.")
        return
    end
    ch.position = POS_STANDING
    ctx:send("일어섰습니다.")
end)
register_command("wake", nil)  -- common 영어 제거

-- ── 자 (sleep, cmdno=20) ───────────────────────────────────────
register_command("자", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_SLEEPING then
        ctx:send("이미 잠들어 있습니다.")
        return
    end
    if ch.fighting then
        ctx:send("전투 중에는 잠들 수 없습니다!")
        return
    end
    ch.position = POS_SLEEPING
    ctx:send("잠들기 시작합니다.")
end)
register_command("sleep", nil)  -- common 영어 제거

-- ── 귀환 (recall, cmdno=22) ────────────────────────────────────
register_command("귀환", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.fighting then
        ctx:send("전투 중에는 귀환할 수 없습니다!")
        return
    end
    local start = ctx:get_start_room()
    ctx:send("{white}눈부신 빛과 함께 신전으로 돌아옵니다.{reset}")
    ctx:send_room(ch.name .. "이(가) 사라집니다.")
    ctx:move_to(start)
    ctx:defer_look()
end)
register_command("recall", nil)  -- common 영어 제거
