-- position.lua — rest, sit, stand, sleep, wake

register_command("rest", function(ctx, args)
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
end, "쉬")

register_command("sit", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_SITTING then
        ctx:send("이미 앉아 있습니다.")
        return
    end
    if ch.fighting then
        ctx:send("전투 중에는 앉을 수 없습니다!")
        return
    end
    ch.position = POS_SITTING
    ctx:send("앉았습니다.")
end, "앉")

register_command("stand", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_STANDING then
        ctx:send("이미 서 있습니다.")
        return
    end
    ch.position = POS_STANDING
    ctx:send("일어섰습니다.")
end, "서")

register_command("sleep", function(ctx, args)
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
end, "자")

register_command("wake", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_STANDING then
        ctx:send("이미 서 있습니다.")
        return
    end
    ch.position = POS_STANDING
    ctx:send("일어섰습니다.")
end, "일어나")

-- ── recall — teleport to start room ──────────────────────────────
register_command("recall", function(ctx, args)
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
end, "돌아가")

-- ── wimpy — auto-flee threshold ──────────────────────────────────
register_command("wimpy", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        local current = ch.wimpy or 0
        ctx:send("현재 자동 도망 HP: " .. current)
        ctx:send("사용법: wimpy <HP> (0 = 비활성)")
        return
    end
    local val = tonumber(args)
    if not val or val < 0 then
        ctx:send("올바른 HP 값을 입력하세요.")
        return
    end
    if val > ch.max_hp / 2 then
        ctx:send("최대 HP의 절반 이하로 설정해야 합니다.")
        return
    end
    ch.wimpy = math.floor(val)
    if val == 0 then
        ctx:send("자동 도망이 비활성화되었습니다.")
    else
        ctx:send("HP가 " .. ch.wimpy .. " 이하가 되면 자동으로 도망칩니다.")
    end
end, "겁쟁이")

-- ── visible — remove invisibility ────────────────────────────────
register_command("visible", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local removed = false
    if ctx:has_spell_affect(ch, 13) then  -- SPELL_INVISIBILITY
        ctx:remove_spell_affect(ch, 13)
        removed = true
    end
    if ctx:has_affect(ch, 1002) then  -- hide
        ctx:remove_affect(ch, 1002)
        removed = true
    end
    if removed then
        ctx:send("다시 모습을 드러냅니다.")
        ctx:send_room(ch.name .. "이(가) 모습을 드러냅니다.")
    else
        ctx:send("이미 보이는 상태입니다.")
    end
end, "보여")

-- ── stat — show stats for admins ─────────────────────────────────
register_command("stat", function(ctx, args)
    if not ctx:is_admin() then
        ctx:send("권한이 없습니다.")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: stat <대상>")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        -- Try finding object
        local obj = ctx:find_obj_room(args)
        if not obj then obj = ctx:find_obj_inv(args) end
        if obj then
            ctx:send("{cyan}=== 아이템 정보 ==={reset}")
            ctx:send("이름: " .. obj.proto.short_desc)
            ctx:send("VNUM: " .. obj.proto.vnum)
            ctx:send("종류: " .. obj.proto.item_type)
            ctx:send("무게: " .. obj.proto.weight .. "  가치: " .. obj.proto.cost)
            ctx:send("키워드: " .. obj.proto.keywords)
            return
        end
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    ctx:send("{cyan}=== 캐릭터 정보 ==={reset}")
    ctx:send("이름: " .. target.name .. "  VNUM: " .. target.proto.vnum)
    ctx:send("레벨: " .. target.level .. "  직업: " .. target.class_id)
    ctx:send("HP: " .. target.hp .. "/" .. target.max_hp ..
             "  마나: " .. target.mana .. "/" .. target.max_mana)
    ctx:send("히트롤: " .. target.hitroll .. "  댐롤: " .. target.damroll ..
             "  AC: " .. target.armor_class)
    ctx:send("골드: " .. target.gold .. "  경험치: " .. target.experience)
    if target.is_npc then
        ctx:send("NPC 플래그: " .. table.concat(target.proto.act_flags or {}, ", "))
    end
end, "정보")
