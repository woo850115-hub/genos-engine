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

-- ── 주문해제 (clear_cast) — 현재 주문 취소 ────────────────────
register_command("주문해제", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    pcall(function()
        ch.extensions.casting = nil
        ch.extensions.cast_target = nil
        ch.extensions.cast_spell = nil
    end)
    ctx:send("현재 주문 시전을 취소합니다.")
end)

-- ── 해제 (clear) — 전투/주문 상태 해제 ────────────────────────
register_command("해제", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.fighting then
        ctx:send("전투 중에는 해제할 수 없습니다!")
        return
    end
    pcall(function()
        ch.extensions.casting = nil
        ch.extensions.cast_target = nil
        ch.extensions.cast_spell = nil
    end)
    ctx:send("모든 행동 대기를 해제합니다.")
end)


-- ══════════════════════════════════════════════════════════════════
-- 일격필살 (oneshot_kill) — Invincible+ 전용 즉사기
-- 원본: kyk8.c oneshot_kill() — 대상 HP 비례 확률
-- ══════════════════════════════════════════════════════════════════

register_command("일격필살", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local cls = ch.class_id or CLASS_FIGHTER
    if cls < CLASS_INVINCIBLE then
        ctx:send("{yellow}무적자 이상만 사용할 수 있습니다.{reset}")
        return
    end
    local target = ch.fighting
    if not target then
        if not args or args == "" then
            ctx:send("누구에게 사용하시겠습니까?")
            return
        end
        target = ctx:find_char(args)
    end
    if not target then
        ctx:send("여기에 그런 것은 없군요")
        return
    end
    if ch.move < 50 then
        ctx:send("움직일 체력이 부족합니다.")
        return
    end
    local cd = ctx:check_cooldown(24)
    if cd > 0 then
        ctx:send("{yellow}아직 사용할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end
    ctx:add_move(-50)
    ctx:set_cooldown(24, 120)
    -- 확률: 레벨 차이 + 스탯
    local chance = 15 + math.floor(ch.level / 5) - math.floor((target.level or 1) / 10)
    if math.random(1, 100) <= chance then
        local dmg = target.hp  -- 즉사
        ctx:send("{bright_red}일격필살!! " .. target.name .. "에게 치명타! [" .. dmg .. "]{reset}")
        ctx:send_room("{bright_red}" .. ch.name .. "이(가) " .. target.name .. "에게 일격필살!{reset}")
        ctx:damage(target, dmg)
    else
        local dmg = math.floor(ch.level * 3 + te_stat(ch, "str", 13) * 5)
        ctx:send("{bright_yellow}일격필살 실패! 하지만 " .. dmg .. "의 피해를 줍니다.{reset}")
        ctx:damage(target, dmg)
    end
    if not ch.fighting then ctx:start_combat(target) end
end)


-- ══════════════════════════════════════════════════════════════════
-- 그림자공격 (shadow_attack) — 그림자 추가 공격 발동
-- 원본: kyk8.c shadow_attack()
-- ══════════════════════════════════════════════════════════════════

register_command("그림자공격", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not ch.fighting then
        ctx:send("전투 중이 아닙니다.")
        return
    end
    if ch.mana < 20 then
        ctx:send("마력이 부족합니다.")
        return
    end
    local cd = ctx:check_cooldown(25)
    if cd > 0 then
        ctx:send("{yellow}아직 사용할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end
    ch.mana = ch.mana - 20
    ctx:set_cooldown(25, 15)
    local target = ch.fighting
    local dmg = math.floor(ch.level * 1.5 + te_stat(ch, "dex", 13) * 2)
    ctx:send("{bright_white}그림자가 " .. target.name .. "을(를) 공격합니다! [" .. dmg .. "]{reset}")
    ctx:send_room(ch.name .. "의 그림자가 " .. target.name .. "을(를) 공격합니다!")
    ctx:damage(target, dmg)
end)


-- ══════════════════════════════════════════════════════════════════
-- 그림자대기 (shadow_wait) — 그림자 공격 대기 모드 토글
-- 원본: kyk8.c shadow_wait()
-- ══════════════════════════════════════════════════════════════════

register_command("그림자대기", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local shadow_mode = false
    pcall(function() shadow_mode = ch.extensions.shadow_mode end)
    if shadow_mode then
        pcall(function() ch.extensions.shadow_mode = false end)
        ctx:send("{white}그림자 대기 모드를 해제합니다.{reset}")
    else
        pcall(function() ch.extensions.shadow_mode = true end)
        ctx:send("{bright_white}그림자 대기 모드를 활성화합니다.{reset}")
    end
end)


-- ══════════════════════════════════════════════════════════════════
-- 던져 (throw) — 투척 아이템 사용
-- 원본: command3.c throw()
-- ══════════════════════════════════════════════════════════════════

register_command("던져", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("무엇을 던지시겠습니까?")
        return
    end
    local parts = {}
    for w in args:gmatch("%S+") do table.insert(parts, w) end
    local item_kw = parts[1]
    local target_name = parts[2]

    local item = ctx:find_inv_item(item_kw)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end
    local target = ch.fighting
    if target_name and target_name ~= "" then
        target = ctx:find_char(target_name)
    end
    if not target then
        ctx:send("누구에게 던지시겠습니까?")
        return
    end
    -- Damage based on item cost + str
    local cost = 0
    pcall(function() cost = item.proto.cost or 0 end)
    local dmg = math.max(1, math.floor(cost / 100) + te_stat(ch, "str", 13))
    ctx:obj_from_char(item)
    ctx:send("{bright_yellow}" .. item.name .. "을(를) " .. target.name .. "에게 던집니다! [" .. dmg .. "]{reset}")
    ctx:send_room(ch.name .. "이(가) " .. item.name .. "을(를) " .. target.name .. "에게 던집니다!")
    ctx:damage(target, dmg)
    if not ch.fighting then ctx:start_combat(target) end
end)
