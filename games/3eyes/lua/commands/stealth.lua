-- stealth.lua — 3eyes 은신 명령어 (원본 cmdlist 기반)
-- 원본: command3.c (hide/pick/steal/backstab)

-- ── 숨어 / 숨겨 (cmdno=26, hide) ─────────────────────────────
local function do_hide(ctx, args)
    local ch = ctx.char
    if ch.class_id ~= 1 and ch.class_id ~= 8 then
        ctx:send("암살자나 도적만 숨을 수 있습니다.")
        return
    end
    if ctx:has_affect(ch, 1002) then
        ctx:remove_affect(ch, 1002)
        ctx:send("모습을 드러냅니다.")
        return
    end
    local dex = te_stat(ch, "dex", 13)
    local chance = 25 + dex * 2 + ch.level
    if math.random(1, 100) <= chance then
        ctx:apply_affect(ch, 1002, 3 + math.floor(ch.level / 5))
        ctx:send("어둠 속에 모습을 감춥니다.")
    else
        ctx:send("숨을 수 있는 곳을 찾지 못했습니다.")
    end
end

register_command("숨어", do_hide)
register_command("숨겨", function(ctx, args) ctx:call_command("숨어", args or "") end)

-- ── 따 (cmdno=35, pick) ──────────────────────────────────────
register_command("따", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 따시겠습니까?")
        return
    end
    local ch = ctx.char
    if ch.class_id ~= 1 and ch.class_id ~= 8 then
        ctx:send("암살자나 도적만 잠금장치를 딸 수 있습니다.")
        return
    end
    local dex = te_stat(ch, "dex", 13)
    local chance = 20 + dex * 3 + ch.level
    if math.random(1, 100) <= chance then
        ctx:pick_lock(args)
        ctx:send("잠금장치를 땄습니다!")
    else
        ctx:send("잠금장치를 따는 데 실패했습니다.")
    end
end)

-- ── 훔쳐 (cmdno=36, steal) ───────────────────────────────────
register_command("훔쳐", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구에게서 무엇을 훔치시겠습니까?")
        return
    end
    local ch = ctx.char
    if ch.class_id ~= 1 and ch.class_id ~= 8 then
        ctx:send("암살자나 도적만 물건을 훔칠 수 있습니다.")
        return
    end
    local item_name, target_name = args:match("^(%S+)%s+(.+)$")
    if not item_name or not target_name then
        ctx:send("사용법: 훔쳐 <물건> <대상>")
        return
    end
    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end
    if not target.is_npc then
        ctx:send("다른 플레이어에게서는 훔칠 수 없습니다.")
        return
    end
    local dex = te_stat(ch, "dex", 13)
    local chance = 15 + dex * 2 + ch.level - target.level * 2
    if math.random(1, 100) <= chance then
        local stolen = ctx:steal_item(target, item_name)
        if stolen then
            ctx:send("{green}" .. stolen.name .. "을(를) 훔쳤습니다!{reset}")
        else
            ctx:send("그런 물건을 가지고 있지 않습니다.")
        end
    else
        ctx:send("실패! " .. target.name .. "이(가) 당신을 발견했습니다!")
        ctx:start_combat(target)
    end
end)

-- ── 엿봐 (peek) — 대상 인벤토리 훔쳐보기 ─────────────────────
register_command("엿봐", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 엿보시겠습니까?")
        return
    end
    local ch = ctx.char
    if ch.class_id ~= 1 and ch.class_id ~= 8 then
        ctx:send("암살자나 도적만 엿볼 수 있습니다.")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end
    if target == ch then
        ctx:send("자기 자신을 엿볼 필요는 없습니다.")
        return
    end
    local dex = te_stat(ch, "dex", 13)
    local chance = 30 + dex * 2 + ch.level - target.level
    if math.random(1, 100) > chance then
        ctx:send("실패! " .. target.name .. "이(가) 당신의 시선을 느꼈습니다.")
        ctx:send_to(target, ch.name .. "이(가) 당신을 엿보려 합니다!")
        return
    end
    -- 성공: 대상 인벤토리 표시
    local lines = {"{bright_cyan}━━ " .. target.name .. "의 소지품 ━━{reset}"}
    local inv = ctx:get_char_inventory(target)
    if inv and #inv > 0 then
        for i = 1, #inv do
            lines[#lines + 1] = "  " .. inv[i].name
        end
    else
        lines[#lines + 1] = "  아무것도 가지고 있지 않습니다."
    end
    lines[#lines + 1] = string.format("  소지금: {yellow}%d{reset}원", target.gold or 0)
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ── 기습 (cmdno=45, backstab) ─────────────────────────────────
register_command("기습", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 뒤치기하시겠습니까?")
        return
    end
    local ch = ctx.char
    if ch.class_id ~= 1 and ch.class_id ~= 8 then
        ctx:send("암살자나 도적만 뒤치기를 할 수 있습니다.")
        return
    end
    if ch.fighting then
        ctx:send("전투 중에는 뒤치기를 할 수 없습니다!")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    if target == ch then
        ctx:send("자기 자신을 뒤치기할 수 없습니다!")
        return
    end
    if target.fighting then
        ctx:send("전투 중인 대상은 뒤치기할 수 없습니다!")
        return
    end

    local dex = te_stat(ch, "dex", 13)
    local chance = 20 + dex * 2 + ch.level - target.level
    if math.random(1, 100) <= chance then
        local dmg = math.max(1, ch.level * 2 + dex)
        if ch.class_id == 1 then
            dmg = dmg * math.random(3, 5)
        else
            dmg = dmg * math.random(2, 4)
        end
        target.hp = target.hp - dmg
        ctx:send("{bright_red}" .. target.name .. "을(를) 뒤치기합니다! [" .. dmg .. "]{reset}")
        ctx:start_combat(target)
        if target.hp <= 0 then
            ctx:stop_combat(ch)
            ctx:defer_death(target, ch)
        end
    else
        ctx:send("뒤치기에 실패했습니다!")
        ctx:start_combat(target)
    end
end)
