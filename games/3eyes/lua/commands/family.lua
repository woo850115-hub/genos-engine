-- family.lua — 3eyes family (guild) system
-- Original: kyk6.c, command4.c (family commands)
-- DB table: organizations (unified schema v1.0)
-- cmdno: 92(패거리가입), 94(가입허가), 95(패거리탈퇴), 96(패거리추방),
--        97(]), 99(모든패거리), 100(패거리원)

-- ══════════════════════════════════════════════════════════════════
-- Family storage (runtime — module-level state)
-- In production would use DB organizations table
-- ══════════════════════════════════════════════════════════════════

local MAX_FAMILIES = 16
local MAX_MEMBERS = 30

-- families[family_id] = { name, leader, members={name1, name2, ...} }
local families = {}

local function get_player_family_id(ctx)
    return ctx:get_player_data("family_id")
end

local function get_family(fid)
    return families[fid]
end

local function find_family_by_name(name)
    name = name:lower()
    for fid, fam in pairs(families) do
        if fam.name:lower() == name or fam.name:lower():find(name, 1, true) then
            return fid, fam
        end
    end
    return nil, nil
end

local function count_families()
    local n = 0
    for _ in pairs(families) do n = n + 1 end
    return n
end

-- ── 패거리가입 (cmdno=92, kyk6.c:35-100) ────────────────────────
register_command("패거리가입", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 패거리가입 <패거리이름>")
        return
    end
    local ch = ctx.char
    local family_id = get_player_family_id(ctx)
    if family_id and family_id > 0 then
        ctx:send("{yellow}이미 가족에 소속되어 있습니다.{reset}")
        return
    end
    if count_families() >= MAX_FAMILIES then
        ctx:send("{yellow}더 이상 가족을 만들 수 없습니다. (최대 " .. MAX_FAMILIES .. "개){reset}")
        return
    end

    -- Check name uniqueness
    local dup_id = find_family_by_name(args)
    if dup_id then
        ctx:send("{yellow}이미 같은 이름의 가족이 있습니다.{reset}")
        return
    end

    -- Cost: 100000 gold (kyk6.c:52)
    local COST = 100000
    if ch.gold < COST then
        ctx:send("{yellow}가족 생성에 " .. COST .. "원이 필요합니다.{reset}")
        return
    end
    ch.gold = ch.gold - COST

    -- Create new family
    local new_id = 1
    while families[new_id] do new_id = new_id + 1 end

    families[new_id] = {
        name = args,
        leader = ch.name,
        members = {ch.name},
    }
    ctx:set_player_data("family_id", new_id)
    ctx:set_player_data("family_rank", "가장")
    ctx:set_flag(PFAMIL)

    ctx:send("{bright_green}가족 '" .. args .. "'을(를) 창설했습니다!{reset}")
    ctx:send_all("{bright_yellow}[가족] " .. ch.name .. "이(가) '" .. args .. "' 가족을 창설합니다!{reset}")
end)

-- ── 가입허가 (cmdno=94, kyk6.c:142-195) ─────────────────────────
register_command("가입허가", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 가입허가 <가족이름>")
        return
    end
    local ch = ctx.char
    local cur_fid = get_player_family_id(ctx)
    if cur_fid and cur_fid > 0 then
        ctx:send("{yellow}이미 가족에 소속되어 있습니다. 먼저 탈퇴하세요.{reset}")
        return
    end

    local fid, fam = find_family_by_name(args)
    if not fam then
        ctx:send("그런 가족을 찾을 수 없습니다.")
        return
    end
    if #fam.members >= MAX_MEMBERS then
        ctx:send("{yellow}가족 인원이 가득 찼습니다. (최대 " .. MAX_MEMBERS .. "명){reset}")
        return
    end

    -- Auto-join (original requires leader approval, simplified)
    fam.members[#fam.members + 1] = ch.name
    ctx:set_player_data("family_id", fid)
    ctx:set_player_data("family_rank", "식구")
    ctx:set_flag(PFAMIL)

    ctx:send("{bright_green}'" .. fam.name .. "' 가족에 가입했습니다!{reset}")
    -- Notify family members
    for _, mname in ipairs(fam.members) do
        local member = ctx:find_player(mname)
        if member and member.session and member ~= ch then
            ctx:send_to(member, "{bright_green}" .. ch.name ..
                "이(가) 가족에 가입했습니다!{reset}")
        end
    end
end)

-- ── 패거리탈퇴 (cmdno=95, kyk6.c:197-240) ──────────────────────
register_command("패거리탈퇴", function(ctx, args)
    local ch = ctx.char
    local fid = get_player_family_id(ctx)
    if not fid or fid <= 0 then
        ctx:send("가족에 소속되어 있지 않습니다.")
        return
    end
    local fam = get_family(fid)
    if not fam then
        ctx:send("가족 정보를 찾을 수 없습니다.")
        ctx:set_player_data("family_id", 0)
        ctx:clear_flag(PFAMIL)
        return
    end
    if fam.leader == ch.name then
        ctx:send("{yellow}가장은 탈퇴할 수 없습니다. 가족을 해체하세요.{reset}")
        return
    end

    -- Remove from members list
    local new_members = {}
    for _, m in ipairs(fam.members) do
        if m ~= ch.name then new_members[#new_members + 1] = m end
    end
    fam.members = new_members

    ctx:set_player_data("family_id", 0)
    ctx:set_player_data("family_rank", "")
    ctx:clear_flag(PFAMIL)

    ctx:send("{green}'" .. fam.name .. "' 가족에서 탈퇴했습니다.{reset}")
    for _, mname in ipairs(fam.members) do
        local member = ctx:find_player(mname)
        if member and member.session then
            ctx:send_to(member, "{yellow}" .. ch.name ..
                "이(가) 가족에서 탈퇴했습니다.{reset}")
        end
    end
end)

-- ── 패거리추방 (cmdno=96, kyk6.c:242-290) ──────────────────────
register_command("패거리추방", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 패거리추방 <대상>")
        return
    end
    local ch = ctx.char
    local fid = get_player_family_id(ctx)
    if not fid or fid <= 0 then
        ctx:send("가족에 소속되어 있지 않습니다.")
        return
    end
    local fam = get_family(fid)
    if not fam or fam.leader ~= ch.name then
        ctx:send("{yellow}가장만 추방할 수 있습니다.{reset}")
        return
    end
    if args == ch.name then
        ctx:send("자기 자신을 추방할 수 없습니다.")
        return
    end

    -- Find target in members
    local found = false
    local new_members = {}
    for _, m in ipairs(fam.members) do
        if m == args then
            found = true
        else
            new_members[#new_members + 1] = m
        end
    end
    if not found then
        ctx:send("{yellow}" .. args .. "은(는) 가족 구성원이 아닙니다.{reset}")
        return
    end
    fam.members = new_members

    -- Clear target's family data if online
    local target = ctx:find_player(args)
    if target and target.session then
        pcall(function()
            target.session.player_data.family_id = 0
            target.session.player_data.family_rank = ""
        end)
        ctx:send_to(target, "{bright_red}'" .. fam.name ..
            "' 가족에서 추방당했습니다.{reset}")
    end

    ctx:send("{green}" .. args .. "을(를) 가족에서 추방했습니다.{reset}")
end)

-- ── ] (cmdno=97, kyk6.c:335-380) — 패거리 채팅 ─────────────────
register_command("]", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 말하시겠습니까?")
        return
    end
    local ch = ctx.char
    local fid = get_player_family_id(ctx)
    if not fid or fid <= 0 then
        ctx:send("가족에 소속되어 있지 않습니다.")
        return
    end
    local fam = get_family(fid)
    if not fam then
        ctx:send("가족 정보를 찾을 수 없습니다.")
        return
    end

    -- Send to all family members online
    for _, mname in ipairs(fam.members) do
        local member = ctx:find_player(mname)
        if member and member.session then
            if member == ch then
                ctx:send("{bright_magenta}[가족] 당신: " .. args .. "{reset}")
            else
                ctx:send_to(member, "{bright_magenta}[가족] " ..
                    ch.name .. ": " .. args .. "{reset}")
            end
        end
    end
end)

-- ── 모든패거리 (cmdno=99, kyk6.c:292-333) ──────────────────────
register_command("모든패거리", function(ctx, args)
    if count_families() == 0 then
        ctx:send("존재하는 가족이 없습니다.")
        return
    end

    local lines = {
        "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        "{bright_cyan}  번호  가족명           가장        인원{reset}",
        "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
    }
    for fid, fam in pairs(families) do
        lines[#lines + 1] = string.format("  %3d)  %-14s %-10s %3d명",
            fid, fam.name, fam.leader, #fam.members)
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ── 패거리원 (cmdno=100, kyk6.c:380-430) ────────────────────────
register_command("패거리원", function(ctx, args)
    local fid
    if args and args ~= "" then
        local f_id, f = find_family_by_name(args)
        fid = f_id
    else
        fid = get_player_family_id(ctx)
    end

    if not fid or fid <= 0 then
        ctx:send("가족 정보를 찾을 수 없습니다.")
        return
    end
    local fam = get_family(fid)
    if not fam then
        ctx:send("가족 정보를 찾을 수 없습니다.")
        return
    end

    local lines = {
        "{bright_cyan}━━ 가족 정보 ━━{reset}",
        "  이름: {bright_white}" .. fam.name .. "{reset}",
        "  가장: " .. fam.leader,
        "  인원: " .. #fam.members .. "/" .. MAX_MEMBERS .. "명",
        "{bright_cyan}━━ 구성원 ━━{reset}",
    }
    for i, mname in ipairs(fam.members) do
        local status = "오프라인"
        local member = ctx:find_player(mname)
        if member and member.session then
            status = "{green}접속중{reset}"
        end
        local rank = (mname == fam.leader) and "{bright_yellow}가장{reset}" or "식구"
        lines[#lines + 1] = string.format("  %2d) %-10s %s  %s", i, mname, rank, status)
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ══════════════════════════════════════════════════════════════════
-- 추가 stub 명령어 (원본 cmdlist에 있으나 미구현)
-- ══════════════════════════════════════════════════════════════════

register_command("패거리누구", function(ctx, args)
    ctx:send("현재 준비 중입니다.")
end)

register_command("패거리공지", function(ctx, args)
    ctx:send("현재 준비 중입니다.")
end)

register_command("패거리기부", function(ctx, args)
    ctx:send("현재 준비 중입니다.")
end)

register_command("패거리출금", function(ctx, args)
    ctx:send("현재 준비 중입니다.")
end)

register_command("가입축하금", function(ctx, args)
    ctx:send("현재 준비 중입니다.")
end)

register_command("기부자명단", function(ctx, args)
    ctx:send("현재 준비 중입니다.")
end)


-- ══════════════════════════════════════════════════════════════════
-- 선전포고 (call_war) — 패거리 전쟁 선포
-- 원본: kyk6.c call_war()
-- ══════════════════════════════════════════════════════════════════

register_command("선전포고", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 선전포고 <패거리이름>")
        return
    end
    local ch = ctx.char
    local fid = get_player_family_id(ctx)
    if not fid or fid <= 0 then
        ctx:send("가족에 소속되어 있지 않습니다.")
        return
    end
    local fam = get_family(fid)
    if not fam or fam.leader ~= ch.name then
        ctx:send("{yellow}가장만 선전포고를 할 수 있습니다.{reset}")
        return
    end
    local target_fid, target_fam = find_family_by_name(args)
    if not target_fam then
        ctx:send("그런 가족을 찾을 수 없습니다.")
        return
    end
    if target_fid == fid then
        ctx:send("자기 가족에게 선전포고할 수 없습니다.")
        return
    end
    ctx:send_all("{bright_red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send_all("{bright_red}  '" .. fam.name .. "' 가족이 '" ..
        target_fam.name .. "' 가족에게 선전포고합니다!{reset}")
    ctx:send_all("{bright_red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
end)
