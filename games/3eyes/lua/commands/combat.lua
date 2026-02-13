-- combat.lua — 3eyes 전투 명령어 (원본 cmdlist 기반)
-- 원본: command5.c (공격/검색), command7.c (도망)

-- ── 공격 (cmdno=2, kill) ──────────────────────────────────────
local function do_kill(ctx, args)
    local ch = ctx.char
    if not ch then return end

    if not args or args == "" then
        ctx:send("누구를 공격하시려구요?")
        return
    end

    if ch.fighting then
        ctx:send("당신은 지금 전투중입니다!")
        return
    end

    local target = ctx:find_char(args)
    if not target then
        ctx:send("여기에 그런 것은 없군요")
        return
    end

    if target == ch then
        ctx:send("자기 자신을 공격하다니!")
        return
    end

    if not target.is_npc then
        ctx:send("다른 플레이어를 공격할 수 없습니다.")
        return
    end

    ctx:start_combat(target)
    ctx:send("당신은 " .. target.name .. "을(를) 공격합니다.")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "을(를) 공격합니다!")
    ctx:send_to(target, ch.name .. "이(가) 당신을 공격합니다!")
end

register_command("공격", do_kill)
-- 원본 별칭: 공, 쳐, 때려
register_command("공", function(ctx, args) ctx:call_command("공격", args or "") end)
register_command("쳐", function(ctx, args) ctx:call_command("공격", args or "") end)
register_command("때려", function(ctx, args) ctx:call_command("공격", args or "") end)

-- ── 도망 (cmdno=3, flee) ──────────────────────────────────────
-- 원본: command7.c flee()
local function do_flee(ctx, args)
    local ch = ctx.char
    if not ch then return end

    if not ch.fighting then
        ctx:send("전투중도 아닌데 도망을 가시려구요?")
        return
    end

    local exits = ctx:get_exits()
    local viable = {}
    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction < 6 then
            local room = ctx:get_room()
            if room and not room:is_door_closed(ex.direction) then
                table.insert(viable, ex)
            end
        end
    end

    if #viable == 0 then
        ctx:send("당신은 도망가려 애를 쓰지만 다리가 굳어 움직여지지가 않습니다!")
        return
    end

    local dex = 13
    local ok_s, stats = pcall(function() return ch.stats end)
    if ok_s and stats then
        local ok_d, d = pcall(function() return stats.dex end)
        if ok_d and d then dex = d end
    end
    local bonus = math.max(-4, math.min(5, math.floor((dex - 10) / 3)))
    local chance = 65 + bonus * 5

    if ctx:random(1, 100) > chance then
        ctx:send("도망치려 했으나 실패하였습니다.")
        return
    end

    local exit = viable[ctx:random(1, #viable)]
    local dir_name = DIR_NAMES[exit.direction + 1] or "?"

    ctx:stop_combat(ch)
    ctx:send_room(ch.name .. "이(가) " .. dir_name .. "쪽으로 도망을 갑니다.")
    ctx:move_to(exit.to_room)
    ctx:send("당신은 " .. dir_name .. "쪽으로 도망갑니다!")
    ctx:defer_look()
end

register_command("도망", do_flee)
register_command("도", function(ctx, args) ctx:call_command("도망", args or "") end)
register_command("flee", do_flee)  -- engine compat

-- ── 찾아 / 검색 (cmdno=50, search) ───────────────────────────
local function do_search(ctx, args)
    local ch = ctx.char
    if not ch then return end

    ctx:send_room(ch.name .. "이(가) 주변을 샅샅이 뒤져봅니다.")

    local found = false

    local exits = ctx:get_exits()
    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction < 6 then
            local flags = ex.flags
            if flags then
                local has_secret = false
                local ok, len = pcall(function() return #flags end)
                if ok then
                    for fi = 0, len - 1 do
                        local ok2, f = pcall(function() return flags[fi] end)
                        if ok2 and f == "secret" then
                            has_secret = true
                            break
                        end
                    end
                end
                if has_secret then
                    local dir_name = DIR_NAMES[ex.direction + 1] or "?"
                    ctx:send("출구를 찾았습니다: " .. dir_name .. ".")
                    found = true
                end
            end
        end
    end

    local chars = ctx:get_characters()
    for i = 1, #chars do
        local mob = chars[i]
        if mob ~= ch then
            local hidden = ctx:has_affect(mob, 1002)
            if hidden then
                ctx:remove_affect(mob, 1002)
                ctx:send("당신은 숨어있는 " .. mob.name .. "을(를) 찾아내었습니다.")
                found = true
            end
        end
    end

    if not found then
        ctx:send("당신은 아무것도 찾지 못했습니다.")
    end
end

register_command("찾아", do_search)
register_command("검색", function(ctx, args) ctx:call_command("찾아", args or "") end)
