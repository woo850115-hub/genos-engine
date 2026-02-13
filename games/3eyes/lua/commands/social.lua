-- social.lua — 3eyes marriage system
-- Original: comm11.c, kyk3.c (propose/accept/marry/divorce)
-- player_data keys: "partner" (str), flag PMARRI (29)

-- ══════════════════════════════════════════════════════════════════
-- Marriage state (module-level for proposals)
-- ══════════════════════════════════════════════════════════════════

-- Pending proposals: proposer_name → target_name
local proposals = {}

-- ── 청혼 (comm11.c:178-230) ─────────────────────────────────────
register_command("청혼", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 청혼 <대상>")
        return
    end
    local ch = ctx.char

    -- Already married?
    if ctx:has_flag(PMARRI) then
        ctx:send("{yellow}이미 결혼한 상태입니다.{reset}")
        return
    end

    local target = ctx:find_char(args)
    if not target or not target.session then
        ctx:send("대상 플레이어를 찾을 수 없습니다. (같은 방에 있어야 합니다)")
        return
    end
    if target == ch then
        ctx:send("자기 자신에게 청혼할 수 없습니다.")
        return
    end

    -- Check RMARRI room flag (marriage room only)
    if not te_room_has_flag(ctx, 27) then  -- RMARRI
        ctx:send("{yellow}결혼식장에서만 청혼할 수 있습니다.{reset}")
        return
    end

    -- Store proposal
    proposals[ch.name] = target.name

    ctx:send("{bright_magenta}" .. target.name .. "에게 청혼합니다!{reset}")
    ctx:send_to(target, "{bright_magenta}" .. ch.name ..
        "이(가) 당신에게 청혼합니다! (초대 " .. ch.name .. " 으로 수락){reset}")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "에게 청혼합니다!")
end)

-- ── 초대 — 청혼 수락 (comm11.c:232-280) ─────────────────────────
register_command("초대", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 초대 <청혼자이름>")
        return
    end
    local ch = ctx.char

    if ctx:has_flag(PMARRI) then
        ctx:send("{yellow}이미 결혼한 상태입니다.{reset}")
        return
    end

    -- Check if there's a proposal from this person
    local proposer_name = args
    if proposals[proposer_name] ~= ch.name then
        ctx:send("{yellow}" .. proposer_name .. "의 청혼이 없습니다.{reset}")
        return
    end

    -- Must be in marriage room
    if not te_room_has_flag(ctx, 27) then
        ctx:send("{yellow}결혼식장에서만 수락할 수 있습니다.{reset}")
        return
    end

    -- Find proposer (must be in same room)
    local proposer = ctx:find_char(proposer_name)
    if not proposer or not proposer.session then
        ctx:send("{yellow}" .. proposer_name .. "이(가) 같은 방에 없습니다.{reset}")
        return
    end

    -- Execute marriage
    proposals[proposer_name] = nil

    -- Set marriage flags and partner data
    ctx:set_flag(PMARRI)
    ctx:set_player_data("partner", proposer.name)

    -- Set on proposer too
    pcall(function()
        local pd = proposer.session.player_data
        local flags = pd.flags or {}
        local found = false
        for _, f in ipairs(flags) do
            if f == PMARRI then found = true; break end
        end
        if not found then flags[#flags + 1] = PMARRI end
        pd.flags = flags
        pd.partner = ch.name
    end)

    -- Store in extensions for combat check
    pcall(function() ch.extensions.partner = proposer.name end)
    pcall(function() proposer.extensions.partner = ch.name end)

    ctx:send_all("{bright_magenta}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send_all("{bright_magenta}  " .. proposer.name .. "과(와) " ..
        ch.name .. "이(가) 결혼했습니다!{reset}")
    ctx:send_all("{bright_magenta}  축하합니다!{reset}")
    ctx:send_all("{bright_magenta}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
end)

-- ── 결혼 — 결혼식 진행 (DM only, comm11.c:282-350) ──────────────
register_command("결혼", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 결혼 <신랑> <신부>")
        return
    end
    local ch = ctx.char
    local cls = ch.class_id or CLASS_FIGHTER
    if cls < CLASS_DM then
        ctx:send("{yellow}관리자만 결혼식을 진행할 수 있습니다.{reset}")
        return
    end

    local name1, name2 = args:match("^(%S+)%s+(%S+)$")
    if not name1 or not name2 then
        ctx:send("사용법: 결혼 <신랑> <신부>")
        return
    end

    local p1 = ctx:find_char(name1)
    local p2 = ctx:find_char(name2)
    if not p1 or not p1.session then
        ctx:send(name1 .. "을(를) 찾을 수 없습니다.")
        return
    end
    if not p2 or not p2.session then
        ctx:send(name2 .. "을(를) 찾을 수 없습니다.")
        return
    end

    -- Set marriage on both
    pcall(function()
        local pd1 = p1.session.player_data
        local flags1 = pd1.flags or {}
        local found1 = false
        for _, f in ipairs(flags1) do if f == PMARRI then found1 = true; break end end
        if not found1 then flags1[#flags1 + 1] = PMARRI end
        pd1.flags = flags1
        pd1.partner = p2.name
        p1.extensions.partner = p2.name
    end)
    pcall(function()
        local pd2 = p2.session.player_data
        local flags2 = pd2.flags or {}
        local found2 = false
        for _, f in ipairs(flags2) do if f == PMARRI then found2 = true; break end end
        if not found2 then flags2[#flags2 + 1] = PMARRI end
        pd2.flags = flags2
        pd2.partner = p1.name
        p2.extensions.partner = p1.name
    end)

    ctx:send_all("{bright_magenta}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send_all("{bright_magenta}  " .. p1.name .. "과(와) " ..
        p2.name .. "이(가) 결혼했습니다!{reset}")
    ctx:send_all("{bright_magenta}  " .. ch.name .. " 관리자의 주례로 결혼식이 진행됩니다!{reset}")
    ctx:send_all("{bright_magenta}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
end)

-- ── 이혼 (comm11.c:352-410) ─────────────────────────────────────
register_command("이혼", function(ctx, args)
    local ch = ctx.char

    if not ctx:has_flag(PMARRI) then
        ctx:send("{yellow}결혼한 상태가 아닙니다.{reset}")
        return
    end

    local partner_name = ctx:get_player_data("partner") or ""
    if partner_name == "" then
        -- Just clear the flag
        ctx:clear_flag(PMARRI)
        ctx:set_player_data("partner", "")
        pcall(function() ch.extensions.partner = nil end)
        ctx:send("{yellow}이혼 처리되었습니다.{reset}")
        return
    end

    -- Clear self
    ctx:clear_flag(PMARRI)
    ctx:set_player_data("partner", "")
    pcall(function() ch.extensions.partner = nil end)

    -- Clear partner if online
    local partner = ctx:find_player(partner_name)
    if partner and partner.session then
        pcall(function()
            local pd = partner.session.player_data
            local flags = pd.flags or {}
            local new_flags = {}
            for _, f in ipairs(flags) do
                if f ~= PMARRI then new_flags[#new_flags + 1] = f end
            end
            pd.flags = new_flags
            pd.partner = ""
            partner.extensions.partner = nil
        end)
        ctx:send_to(partner, "{yellow}" .. ch.name .. "이(가) 이혼을 요청했습니다.{reset}")
    end

    ctx:send_all("{yellow}" .. ch.name .. "과(와) " .. partner_name ..
        "이(가) 이혼했습니다.{reset}")
end)

-- ── 사랑말 — 배우자에게 메시지 전달 ─────────────────────────────
register_command("사랑말", function(ctx, args)
    if not args or args == "" then
        ctx:send("무슨 말을 하시겠습니까?")
        return
    end
    local ch = ctx.char
    -- check married status
    local ok, married = pcall(function() return ch.extensions.married_to end)
    if not ok or not married then
        ctx:send("결혼을 하셔야 합니다.")
        return
    end
    local spouse = ctx:find_player(married)
    if not spouse then
        ctx:send("배우자가 접속해 있지 않습니다.")
        return
    end
    ctx:send("{bright_magenta}[사랑] " .. args .. "{reset}")
    ctx:send_to(spouse, "{bright_magenta}" .. ch.name .. "의 사랑말: " .. args .. "{reset}")
end)
