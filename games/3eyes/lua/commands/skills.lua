-- skills.lua — 3eyes 전투기술 명령어 (원본 cmdlist 기반)
-- 맹공, 차기, 교란, 배워/연마

-- ── 맹공 (bash) ─────────────────────────────────────────────
register_command("맹공", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local target = ch.fighting
    if not target then
        if not args or args == "" then
            ctx:send("누구를 밟으시겠습니까?")
            return
        end
        target = ctx:find_char(args)
    end
    if not target then
        ctx:send("여기에 그런 것은 없군요")
        return
    end
    if target == ch then
        ctx:send("자기 자신을 밟다니!")
        return
    end

    -- Check skill proficiency (skill id 40 = bash in 3eyes)
    local prof = ctx:get_skill_proficiency("bash")
    if prof <= 0 then
        ctx:send("당신은 밟기를 배우지 못했습니다.")
        return
    end

    -- Move cost
    if ch.move < 10 then
        ctx:send("움직일 체력이 부족합니다.")
        return
    end
    ctx:add_move(-10)

    -- Hit chance: base 50% + prof/2 + str bonus - target dex bonus
    local chance = 50 + math.floor(prof / 2)
    local roll = ctx:random(1, 100)
    if roll > chance then
        ctx:send("밟기에 실패하였습니다.")
        ctx:send_room(ch.name .. "이(가) " .. target.name .. "을(를) 밟으려 했으나 실패합니다.")
        if not ch.fighting then ctx:start_combat(target) end
        return
    end

    -- Success: damage + stun
    local dmg = ctx:random(1, ch.level) + 5
    ctx:send("{bright_yellow}당신이 " .. target.name .. "을(를) 세게 밟습니다!{reset}")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "을(를) 세게 밟습니다!")
    ctx:send_to(target, ch.name .. "이(가) 당신을 세게 밟습니다!")
    ctx:damage(target, dmg)
    if not ch.fighting then ctx:start_combat(target) end
end)

-- ── 차기 (kick) ─────────────────────────────────────────────
register_command("차기", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local target = ch.fighting
    if not target then
        if not args or args == "" then
            ctx:send("누구를 차시겠습니까?")
            return
        end
        target = ctx:find_char(args)
    end
    if not target then
        ctx:send("여기에 그런 것은 없군요")
        return
    end
    if target == ch then
        ctx:send("자기 자신을 차다니!")
        return
    end

    local prof = ctx:get_skill_proficiency("kick")
    if prof <= 0 then
        ctx:send("당신은 차기를 배우지 못했습니다.")
        return
    end

    if ch.move < 5 then
        ctx:send("움직일 체력이 부족합니다.")
        return
    end
    ctx:add_move(-5)

    local chance = 60 + math.floor(prof / 2)
    if ctx:random(1, 100) > chance then
        ctx:send("발차기에 실패하였습니다.")
        if not ch.fighting then ctx:start_combat(target) end
        return
    end

    local dmg = ctx:random(1, math.floor(ch.level / 2)) + 3
    ctx:send("{bright_yellow}당신이 " .. target.name .. "을(를) 세게 찹니다!{reset}")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "을(를) 발로 찹니다!")
    ctx:damage(target, dmg)
    if not ch.fighting then ctx:start_combat(target) end
end)

-- ── 교란 (trip) ─────────────────────────────────────────────
register_command("교란", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    local target = ch.fighting
    if not target then
        if not args or args == "" then
            ctx:send("누구를 넘어뜨리겠습니까?")
            return
        end
        target = ctx:find_char(args)
    end
    if not target then
        ctx:send("여기에 그런 것은 없군요")
        return
    end

    local prof = ctx:get_skill_proficiency("trip")
    if prof <= 0 then
        ctx:send("당신은 교란을 배우지 못했습니다.")
        return
    end

    if ch.move < 8 then
        ctx:send("움직일 체력이 부족합니다.")
        return
    end
    ctx:add_move(-8)

    local chance = 55 + math.floor(prof / 2)
    if ctx:random(1, 100) > chance then
        ctx:send("교란에 실패하였습니다.")
        if not ch.fighting then ctx:start_combat(target) end
        return
    end

    local dmg = ctx:random(1, 4) + 2
    ctx:send("{bright_yellow}당신이 " .. target.name .. "을(를) 넘어뜨렸습니다!{reset}")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "을(를) 넘어뜨렸습니다!")
    ctx:damage(target, dmg)
    if not ch.fighting then ctx:start_combat(target) end
end)

-- ── 배워 (practice) ─────────────────────────────────────────
local do_practice = function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    if not args or args == "" then
        -- Show list of practiced skills
        local lines = {"{bright_cyan}━━━ 수련 현황 ━━━{reset}"}
        local skills = ctx:get_player_data("skills")
        if skills then
            local found = false
            for name, prof in pairs(skills) do
                found = true
                local bar = ""
                local pct = math.floor(prof)
                if pct >= 100 then
                    bar = "{bright_green}[마스터]{reset}"
                elseif pct >= 75 then
                    bar = "{green}[숙련]{reset}"
                elseif pct >= 50 then
                    bar = "{yellow}[보통]{reset}"
                elseif pct >= 25 then
                    bar = "{red}[미숙]{reset}"
                else
                    bar = "{bright_red}[초보]{reset}"
                end
                lines[#lines + 1] = string.format("  %-12s %3d%% %s", name, pct, bar)
            end
            if not found then
                lines[#lines + 1] = "  배운 기술이 없습니다."
            end
        else
            lines[#lines + 1] = "  배운 기술이 없습니다."
        end

        -- Show available practices
        local pracs = ctx:get_player_data("practices")
        lines[#lines + 1] = ""
        lines[#lines + 1] = "수련 포인트: {bright_white}" .. (pracs or 0) .. "{reset}"
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    -- Practice a specific skill
    local pracs = ctx:get_player_data("practices")
    if not pracs or pracs <= 0 then
        ctx:send("수련 포인트가 부족합니다.")
        return
    end

    -- Find skill by name (Korean or English)
    local skill_name = args:lower()
    local skills = ctx:get_player_data("skills") or {}
    local current = skills[skill_name] or 0

    if current >= 100 then
        ctx:send("이미 마스터했습니다.")
        return
    end

    -- Increase proficiency
    local gain = ctx:random(5, 15)
    local new_prof = math.min(100, current + gain)
    skills[skill_name] = new_prof
    ctx:set_player_data("skills", skills)
    ctx:set_player_data("practices", pracs - 1)

    ctx:send("당신은 " .. skill_name .. "을(를) 수련합니다. (" .. new_prof .. "%)")
end

register_command("배워", do_practice)
register_command("연마", function(ctx, args) ctx:call_command("배워", args or "") end)
register_command("practice", do_practice)

-- ── 추적 (track) — 대상 방향 추적, Ranger/Thief 전용 ──────────
register_command("추적", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("누구를 추적하시겠습니까?")
        return
    end
    -- Class check: Ranger(7), Thief(8), Assassin(1)
    local cls = ch.class_id or CLASS_FIGHTER
    if cls ~= 7 and cls ~= 8 and cls ~= 1 then
        ctx:send("광전사, 도적, 암살자만 추적할 수 있습니다.")
        return
    end
    if ch.move < 15 then
        ctx:send("움직일 체력이 부족합니다.")
        return
    end
    ctx:add_move(-15)
    local target = ctx:find_player(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    local dir_names = {"북쪽", "동쪽", "남쪽", "서쪽", "위쪽", "아래쪽"}
    local dex = te_stat(ch, "dex", 13)
    local chance = 40 + dex * 2 + ch.level
    if math.random(1, 100) > chance then
        ctx:send("추적에 실패했습니다.")
        return
    end
    -- Simplified: show random direction (실제로는 경로탐색 필요)
    local dir = ctx:track_target(target)
    if dir and dir >= 0 and dir < 6 then
        ctx:send("{green}" .. target.name .. "의 흔적이 " .. dir_names[dir + 1] .. "으로 이어집니다.{reset}")
    else
        ctx:send("흔적을 찾을 수 없습니다.")
    end
end)

-- ── 독살포 (poison_mon) — 무기에 독 도포, Assassin/Thief 전용 ─
register_command("독살포", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local cls = ch.class_id or CLASS_FIGHTER
    if cls ~= 1 and cls ~= 8 then
        ctx:send("암살자나 도적만 독을 바를 수 있습니다.")
        return
    end
    -- 무기 장착 확인
    local ok, weapon = pcall(function() return ch.equipment[16] end)
    if not ok or not weapon then
        ctx:send("무기를 장비하고 있지 않습니다.")
        return
    end
    local dex = te_stat(ch, "dex", 13)
    local chance = 30 + dex * 2 + ch.level
    if math.random(1, 100) > chance then
        ctx:send("독을 바르는 데 실패했습니다!")
        return
    end
    pcall(function()
        weapon.adjustment = (weapon.adjustment or 0)  -- keep existing
        ch.extensions.poison_weapon = true
        ch.extensions.poison_rounds = 5 + math.floor(ch.level / 10)
    end)
    ctx:send("{green}무기에 독을 발랐습니다! (독 효과 " ..
        (5 + math.floor(ch.level / 10)) .. "라운드){reset}")
end)

-- ── 경계 (prepare) — 방어 자세, AC 임시 보너스 ─────────────────
register_command("경계", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local cd = ctx:check_cooldown(20)
    if cd > 0 then
        ctx:send("{yellow}아직 경계 자세를 취할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end
    local dex = te_stat(ch, "dex", 13)
    local ac_bonus = math.max(5, math.floor(dex / 2) + math.floor(ch.level / 10))
    ch.armor_class = (ch.armor_class or 100) - ac_bonus
    ctx:set_cooldown(20, 60)
    ctx:send("{bright_white}방어 자세를 취합니다! AC -" .. ac_bonus .. "{reset}")
    ctx:send_room(ch.name .. "이(가) 경계 자세를 취합니다.")
end)

-- ── 멸혼술 (turn) — 언데드 퇴마, Cleric/Paladin 전용 ──────────
register_command("멸혼술", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local cls = ch.class_id or CLASS_FIGHTER
    -- Cleric(3), Paladin(6)
    if cls ~= 3 and cls ~= 6 then
        ctx:send("성직자나 팔라딘만 멸혼술을 사용할 수 있습니다.")
        return
    end
    if ch.mana < 20 then
        ctx:send("마력이 부족합니다.")
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
    ch.mana = ch.mana - 20
    -- Check if target is undead (flag or race)
    local is_undead = false
    pcall(function()
        if target.race_id == 7 then is_undead = true end  -- undead race
        if target.flags then
            for _, f in ipairs(target.flags) do
                if f == "undead" then is_undead = true; break end
            end
        end
    end)
    local pie = te_stat(ch, "pie", 13)
    local dmg = math.floor(pie * 2 + ch.level)
    if is_undead then dmg = dmg * 3 end
    ctx:send("{bright_yellow}멸혼술! " .. target.name .. "에게 " .. dmg .. "의 피해!{reset}")
    ctx:damage(target, dmg)
    if not ch.fighting then ctx:start_combat(target) end
end)
