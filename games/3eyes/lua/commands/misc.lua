-- misc.lua — 3eyes miscellaneous systems
-- alias (kyk2.c), killer/PK (kyk5.c), rename, version
-- player_data keys: "aliases" (dict), "pk_kills" (int), "pk_deaths" (int)

-- ══════════════════════════════════════════════════════════════════
-- 줄임말 — 별명 시스템 (alias.c, kyk2.c)
-- Max 20 aliases per player, stored in player_data
-- ══════════════════════════════════════════════════════════════════

local MAX_ALIASES = 20

register_command("줄임말", function(ctx, args)
    local aliases = ctx:get_player_data("aliases") or {}
    if type(aliases) ~= "table" then aliases = {} end

    if not args or args == "" then
        -- List all aliases
        local lines = {"{bright_cyan}━━━━━━━━ 별명 목록 ━━━━━━━━{reset}"}
        local count = 0
        local ok2, _ = pcall(function()
            for name, cmd in pairs(aliases) do
                lines[#lines + 1] = string.format("  %-12s → %s", name, cmd)
                count = count + 1
            end
        end)
        if count == 0 then
            lines[#lines + 1] = "  등록된 별명이 없습니다."
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    -- Parse: alias <name> [command...]
    local name, cmd = args:match("^(%S+)%s+(.+)$")
    if not name then
        name = args:match("^(%S+)$")
    end

    if not name then
        ctx:send("사용법: 줄임말 <이름> [명령어]  또는  줄임말 <이름> (삭제)")
        return
    end

    if not cmd or cmd == "" then
        -- Delete alias
        local ok_get, existing = pcall(function() return aliases[name] end)
        if ok_get and existing then
            pcall(function() aliases[name] = nil end)
            ctx:set_player_data("aliases", aliases)
            ctx:send("{green}별명 '" .. name .. "'을(를) 삭제했습니다.{reset}")
        else
            ctx:send("그런 별명은 없습니다.")
        end
        return
    end

    -- Count existing aliases
    local count = 0
    pcall(function()
        for _ in pairs(aliases) do count = count + 1 end
    end)
    if count >= MAX_ALIASES then
        local ok_exist, existing = pcall(function() return aliases[name] end)
        if not (ok_exist and existing) then
            ctx:send("{yellow}별명은 최대 " .. MAX_ALIASES .. "개까지 등록할 수 있습니다.{reset}")
            return
        end
    end

    -- Prevent recursive aliases
    local first_word = cmd:match("^(%S+)")
    if first_word == name then
        ctx:send("{yellow}재귀 별명은 허용되지 않습니다.{reset}")
        return
    end

    pcall(function() aliases[name] = cmd end)
    ctx:set_player_data("aliases", aliases)
    ctx:send("{green}별명 등록: " .. name .. " → " .. cmd .. "{reset}")
end)

-- ── 줄 — 줄임말 별칭 ────────────────────────────────────────────
register_command("줄", function(ctx, args) ctx:call_command("줄임말", args or "") end)

-- ══════════════════════════════════════════════════════════════════
-- 고용 — PK 전적 확인 (kyk5.c)
-- ══════════════════════════════════════════════════════════════════

register_command("고용", function(ctx, args)
    local pk_kills = ctx:get_player_data("pk_kills") or 0
    local pk_deaths = ctx:get_player_data("pk_deaths") or 0

    local lines = {
        "{bright_cyan}━━━━━━━━ PK 전적 ━━━━━━━━{reset}",
        "  PK 킬: {bright_red}" .. pk_kills .. "{reset}",
        "  PK 데스: {yellow}" .. pk_deaths .. "{reset}",
    }

    -- Killer status
    if pk_kills >= 10 then
        lines[#lines + 1] = "  상태: {bright_red}킬러 (현상수배){reset}"
    elseif pk_kills >= 5 then
        lines[#lines + 1] = "  상태: {red}위험 인물{reset}"
    elseif pk_kills >= 1 then
        lines[#lines + 1] = "  상태: {yellow}PK 경험자{reset}"
    else
        lines[#lines + 1] = "  상태: {green}평화{reset}"
    end

    -- Chaos status
    if ctx:has_flag(PCHAOS) then
        lines[#lines + 1] = "  카오스: {bright_red}활성{reset}"
    else
        lines[#lines + 1] = "  카오스: {green}비활성{reset}"
    end

    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ══════════════════════════════════════════════════════════════════
-- 명명 — 이름 변경 (kyk8.c rename, DM or self with cost)
-- ══════════════════════════════════════════════════════════════════

register_command("명명", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 명명 <새이름>")
        return
    end
    local ch = ctx.char

    -- Name validation
    local new_name = args:match("^(%S+)$")
    if not new_name then
        ctx:send("이름은 공백 없이 입력해주세요.")
        return
    end
    if #new_name < 2 or #new_name > 16 then
        ctx:send("{yellow}이름은 2~16자여야 합니다.{reset}")
        return
    end

    -- Cost: 500000 gold (or free for DM+)
    local cls = ch.class_id or 0
    if cls < CLASS_DM then
        local cost = 500000
        if ch.gold < cost then
            ctx:send("{yellow}이름 변경에 " .. cost .. "원이 필요합니다. (소지금: " .. ch.gold .. "원){reset}")
            return
        end
        ch.gold = ch.gold - cost
    end

    local old_name = ch.name
    ch.name = new_name
    ctx:send("{bright_green}이름이 변경되었습니다: " .. old_name .. " → " .. new_name .. "{reset}")
    ctx:send_all("{bright_yellow}" .. old_name .. "이(가) " .. new_name .. "(으)로 이름을 변경합니다.{reset}")
end)

-- ══════════════════════════════════════════════════════════════════
-- 버젼 — 버전 정보 (comm12.c)
-- ══════════════════════════════════════════════════════════════════

register_command("버젼", function(ctx, args)
    ctx:send("{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send("{bright_white}  제3의 눈 (3eyes MUD){reset}")
    ctx:send("  Mordor 2.0 기반 한국어 MUD")
    ctx:send("  GenOS Engine v1.0")
    ctx:send("{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
end)

-- ── version — 버젼 별칭 (원본 영어 별칭) ────────────────────────
register_command("version", function(ctx, args) ctx:call_command("버젼", args or "") end)


-- ══════════════════════════════════════════════════════════════════
-- 경험치전수 (trans_exp) — 다른 플레이어에게 경험치 전달
-- 원본: kyk3.c trans_exp()
-- ══════════════════════════════════════════════════════════════════

register_command("경험치전수", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 경험치전수 <대상> <양>")
        return
    end
    local ch = ctx.char
    local target_name, amount_str = args:match("^(%S+)%s+(%d+)$")
    if not target_name or not amount_str then
        ctx:send("사용법: 경험치전수 <대상> <양>")
        return
    end
    local amount = tonumber(amount_str) or 0
    if amount <= 0 then
        ctx:send("유효한 경험치 양을 입력하세요.")
        return
    end
    if ch.experience < amount then
        ctx:send("{yellow}경험치가 부족합니다. (현재: " .. ch.experience .. "){reset}")
        return
    end
    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("그런 플레이어를 찾을 수 없습니다.")
        return
    end
    if target == ch then
        ctx:send("자기 자신에게는 전수할 수 없습니다.")
        return
    end
    -- 10% 수수료
    local fee = math.floor(amount * 0.1)
    local received = amount - fee
    ch.experience = ch.experience - amount
    target.experience = (target.experience or 0) + received
    ctx:send("{green}" .. target.name .. "에게 경험치 " .. received ..
        "을 전수합니다. (수수료: " .. fee .. "){reset}")
    ctx:send_to(target, "{green}" .. ch.name .. "이(가) 당신에게 경험치 " ..
        received .. "을 전수합니다!{reset}")
end)


-- ══════════════════════════════════════════════════════════════════
-- 메모 (notepad) — 개인 메모장
-- player_data: "notes" = string
-- ══════════════════════════════════════════════════════════════════

register_command("메모", function(ctx, args)
    if not args or args == "" then
        local notes = ctx:get_player_data("notes") or ""
        if notes == "" then
            ctx:send("메모가 비어 있습니다.")
            ctx:send("사용법: 메모 <내용>  또는  메모 삭제")
        else
            ctx:send("{bright_cyan}━━ 메모 ━━{reset}")
            ctx:send(notes)
            ctx:send("{bright_cyan}━━━━━━━━━━{reset}")
        end
        return
    end
    if args == "삭제" or args == "지워" then
        ctx:set_player_data("notes", "")
        ctx:send("{green}메모를 삭제했습니다.{reset}")
        return
    end
    -- 기존 메모에 추가
    local notes = ctx:get_player_data("notes") or ""
    if notes ~= "" then notes = notes .. "\r\n" end
    notes = notes .. args
    ctx:set_player_data("notes", notes)
    ctx:send("{green}메모가 저장되었습니다.{reset}")
end)


-- ══════════════════════════════════════════════════════════════════
-- 투체변신술 (up_dmg) — 전투력 강화 변신
-- 원본: kyk8.c up_dmg()
-- ══════════════════════════════════════════════════════════════════

register_command("투체변신술", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.mana < 40 then
        ctx:send("마력이 부족합니다.")
        return
    end
    local cd = ctx:check_cooldown(26)
    if cd > 0 then
        ctx:send("{yellow}아직 사용할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end
    ch.mana = ch.mana - 40
    local bonus = math.floor(ch.level / 5) + te_bonus(te_stat(ch, "str", 13))
    pcall(function()
        ch.extensions.bonus_power = (ch.extensions.bonus_power or 0) + bonus
        ch.extensions.transform_rounds = 20
    end)
    ctx:set_flag(PUPDMG)
    ctx:set_cooldown(26, 180)
    ctx:send("{bright_red}투체변신! 전투력 +" .. bonus .. " (20라운드){reset}")
    ctx:send_room("{bright_red}" .. ch.name .. "이(가) 몸이 변합니다!{reset}")
end)


-- ══════════════════════════════════════════════════════════════════
-- 긁어 (burn/scratch) — 아이템 파괴
-- 원본: kyk3.c burn()
-- ══════════════════════════════════════════════════════════════════

register_command("긁어", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 긁으시겠습니까?")
        return
    end
    local ch = ctx.char
    local item = ctx:find_inv_item(args)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end
    ctx:obj_from_char(item)
    ctx:send("{yellow}" .. item.name .. "을(를) 긁어 부숩니다.{reset}")
    ctx:send_room(ch.name .. "이(가) " .. item.name .. "을(를) 파괴합니다.")
end)
