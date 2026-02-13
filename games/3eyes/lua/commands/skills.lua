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
