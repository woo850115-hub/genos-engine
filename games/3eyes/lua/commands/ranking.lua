-- ranking.lua — 3eyes ranking system
-- Original: kyk7.c, rank.c (level/exp/martial arts ranking)
-- Calculates rankings from online players in real-time

-- ══════════════════════════════════════════════════════════════════
-- 서열 — 순위표 (kyk7.c rank, rank.c)
-- ══════════════════════════════════════════════════════════════════

register_command("서열", function(ctx, args)
    local sub = (args or ""):lower()
    local players = ctx:get_online_players()

    if not players then
        ctx:send("접속자가 없습니다.")
        return
    end

    -- Collect player data
    local plist = {}
    for i = 0, 200 do
        local ok, p = pcall(function() return players[i] end)
        if not ok or not p then break end
        -- Skip DM+ level (class >= 13)
        local cls = p.class_id or 0
        if cls < 13 then
            plist[#plist + 1] = {
                name = p.name or "???",
                level = p.level or 0,
                class_id = cls,
                experience = p.experience or 0,
                hp = p.max_hp or 0,
                mp = p.max_mana or 0,
            }
        end
    end

    if #plist == 0 then
        ctx:send("순위를 표시할 플레이어가 없습니다.")
        return
    end

    local max_show = 20

    if sub == "" or sub == "level" or sub == "레벨" then
        -- Level ranking
        table.sort(plist, function(a, b)
            if a.level ~= b.level then return a.level > b.level end
            return a.experience > b.experience
        end)

        local lines = {
            "{bright_cyan}━━━━━━━━━━━━ 레벨 순위 ━━━━━━━━━━━━{reset}",
            "{bright_cyan}  순위   이름            레벨    직업{reset}",
            "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        }
        for i, p in ipairs(plist) do
            if i > max_show then break end
            local class_name = THREEEYES_CLASSES[p.class_id] or "?"
            lines[#lines + 1] = string.format("  %3d    %-14s  %3d   %s",
                i, p.name, p.level, class_name)
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    if sub == "exp" or sub == "경험치" then
        -- Exp ranking
        table.sort(plist, function(a, b) return a.experience > b.experience end)

        local lines = {
            "{bright_cyan}━━━━━━━━━━ 경험치 순위 ━━━━━━━━━━{reset}",
            "{bright_cyan}  순위   이름            경험치{reset}",
            "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        }
        for i, p in ipairs(plist) do
            if i > max_show then break end
            lines[#lines + 1] = string.format("  %3d    %-14s  %d",
                i, p.name, p.experience)
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    if sub == "hp" or sub == "체력" then
        -- HP ranking (indicates combat prowess)
        table.sort(plist, function(a, b) return a.hp > b.hp end)

        local lines = {
            "{bright_cyan}━━━━━━━━━━ HP 순위 ━━━━━━━━━━{reset}",
            "{bright_cyan}  순위   이름            HP       MP{reset}",
            "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        }
        for i, p in ipairs(plist) do
            if i > max_show then break end
            lines[#lines + 1] = string.format("  %3d    %-14s  %6d  %6d",
                i, p.name, p.hp, p.mp)
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    if sub == "martial" or sub == "무술" or sub == "prof" or sub == "숙련" then
        -- Proficiency ranking (sum of all weapon + realm proficiencies)
        for _, p in ipairs(plist) do
            local total_prof = 0
            local player = ctx:find_player(p.name)
            if player then
                for pi = 0, 4 do
                    total_prof = total_prof + te_prof_percent(player, pi)
                end
                for ri = 0, 3 do
                    total_prof = total_prof + te_realm_percent(player, ri)
                end
            end
            p.prof_total = total_prof
        end
        table.sort(plist, function(a, b) return (a.prof_total or 0) > (b.prof_total or 0) end)

        local lines = {
            "{bright_cyan}━━━━━━━━━━ 무술 순위 ━━━━━━━━━━{reset}",
            "{bright_cyan}  순위   이름            숙련합계{reset}",
            "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        }
        for i, p in ipairs(plist) do
            if i > max_show then break end
            lines[#lines + 1] = string.format("  %3d    %-14s  %d%%",
                i, p.name, p.prof_total or 0)
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    ctx:send("사용법: 서열 [level|exp|hp|martial]")
    ctx:send("  서열 level   — 레벨 순위")
    ctx:send("  서열 exp     — 경험치 순위")
    ctx:send("  서열 hp      — HP 순위")
    ctx:send("  서열 martial — 무술/숙련도 순위")
end)


-- ══════════════════════════════════════════════════════════════════
-- 무술대회서열 (view_musul_rank) — 무술 랭킹 보기 (별칭)
-- ══════════════════════════════════════════════════════════════════

register_command("무술대회서열", function(ctx, args)
    ctx:call_command("서열", "martial")
end)
