-- training.lua — 3eyes 전직/훈련 시스템 (원본 cmdlist 기반)
-- 원본: command7.c (train), kyk3.c (aim_exp, comp_chance), kyk8.c (power/meditate/accurate)

-- ══════════════════════════════════════════════════════════════════
-- aim_exp() — 전직 필요 경험치 (kyk3.c:802-830)
-- ══════════════════════════════════════════════════════════════════

local function aim_exp(mob)
    local cls = mob.class_id or CLASS_FIGHTER
    local level = mob.level or 1
    local hpmax = mob.max_hp or 100
    local mpmax = mob.max_mana or 50

    if cls == CLASS_CARE_II or cls == CLASS_CARE_III then
        return hpmax * 1500 + mpmax * 1000
    end

    if cls >= CLASS_INVINCIBLE and cls < CLASS_CARE_II then
        return hpmax * 1500 + mpmax * 1000
    end

    local base_exp = (level * level * 10) + 10000
    return base_exp
end

-- ── 수련 (cmdno=46, train) ────────────────────────────────────
register_command("수련", function(ctx, args)
    if not te_room_has_flag(ctx, 8) then  -- RTRAIN
        ctx:send("{yellow}여기에서는 전직할 수 없습니다. 전직 방을 찾아가세요.{reset}")
        return
    end

    local ch = ctx.char
    local cls = ch.class_id or CLASS_FIGHTER
    local level = ch.level or 1

    local cd = ctx:check_cooldown(LT_TRAIN)
    if cd > 0 then
        ctx:send("{yellow}아직 전직할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end

    -- ── Normal → Invincible (class 1-8, level >= 200)
    if cls >= 1 and cls <= 8 then
        if level < 200 then
            ctx:send("{yellow}200레벨 이상이어야 전직할 수 있습니다. (현재: " .. level .. "){reset}")
            return
        end

        local needed_exp = aim_exp(ch)
        local needed_gold = math.floor(needed_exp / 123) + level * 23
        if ch.experience < needed_exp then
            ctx:send("{yellow}경험치가 부족합니다. (필요: " .. needed_exp ..
                ", 현재: " .. ch.experience .. "){reset}")
            return
        end
        if ch.gold < needed_gold then
            ctx:send("{yellow}골드가 부족합니다. (필요: " .. needed_gold ..
                ", 현재: " .. ch.gold .. "){reset}")
            return
        end

        ch.experience = ch.experience - needed_exp
        ch.gold = ch.gold - needed_gold
        ch.class_id = CLASS_INVINCIBLE
        ch.level = 1

        ch.max_hp = ch.max_hp * 3
        ch.max_mana = ch.max_mana * 3
        ch.hp = ch.max_hp
        ch.mana = ch.max_mana

        ctx:set_cooldown(LT_TRAIN, 60)

        ctx:send("{bright_yellow}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
        ctx:send("{bright_yellow}  전직 성공! 무적자(Invincible)가 되었습니다!{reset}")
        ctx:send("{bright_yellow}  레벨이 1로 초기화됩니다.{reset}")
        ctx:send("{bright_yellow}  HP/MP가 3배로 증가합니다!{reset}")
        ctx:send("{bright_yellow}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
        ctx:send_all("{bright_yellow}" .. ch.name .. "이(가) 무적자(Invincible)로 전직합니다!{reset}")
        return
    end

    -- ── Invincible → Caretaker (class 9, level >= 200)
    if cls == CLASS_INVINCIBLE then
        if level < 200 then
            ctx:send("{yellow}200레벨 이상이어야 전직할 수 있습니다.{reset}")
            return
        end

        local needed_exp = aim_exp(ch)
        local needed_gold = math.floor(needed_exp / 123) + level * 23
        if ch.experience < needed_exp then
            ctx:send("{yellow}경험치가 부족합니다. (필요: " .. needed_exp .. "){reset}")
            return
        end
        if ch.gold < needed_gold then
            ctx:send("{yellow}골드가 부족합니다. (필요: " .. needed_gold .. "){reset}")
            return
        end

        ch.experience = ch.experience - needed_exp
        ch.gold = ch.gold - needed_gold
        ch.class_id = CLASS_CARETAKER
        ch.level = 1

        ch.max_hp = ch.max_hp + 2000
        ch.max_mana = ch.max_mana + 900
        ch.hp = ch.max_hp
        ch.mana = ch.max_mana

        ctx:set_cooldown(LT_TRAIN, 60)

        ctx:send("{bright_yellow}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
        ctx:send("{bright_yellow}  전직 성공! 보살핌자(Caretaker)가 되었습니다!{reset}")
        ctx:send("{bright_yellow}  HP +2000, MP +900!{reset}")
        ctx:send("{bright_yellow}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
        ctx:send_all("{bright_yellow}" .. ch.name .. "이(가) 보살핌자(Caretaker)로 전직합니다!{reset}")
        return
    end

    -- ── Caretaker → Care_II (class 10)
    if cls == CLASS_CARETAKER then
        local needed_exp = aim_exp(ch)
        if ch.experience < needed_exp then
            ctx:send("{yellow}경험치가 부족합니다. (필요: " .. needed_exp .. "){reset}")
            return
        end
        ch.experience = ch.experience - needed_exp
        ch.class_id = CLASS_CARE_II
        ch.hp = ch.max_hp
        ch.mana = ch.max_mana

        ctx:set_cooldown(LT_TRAIN, 60)

        ctx:send("{bright_yellow}보살핌II로 전직 성공!{reset}")
        ctx:send_all("{bright_yellow}" .. ch.name .. "이(가) 보살핌II로 전직합니다!{reset}")
        return
    end

    -- ── Care_II → Care_III (class 11)
    if cls == CLASS_CARE_II then
        local needed_exp = aim_exp(ch)
        if ch.experience < needed_exp then
            ctx:send("{yellow}경험치가 부족합니다. (필요: " .. needed_exp .. "){reset}")
            return
        end
        ch.experience = ch.experience - needed_exp
        ch.class_id = CLASS_CARE_III
        ch.hp = ch.max_hp
        ch.mana = ch.max_mana

        ctx:set_cooldown(LT_TRAIN, 60)

        ctx:send("{bright_yellow}보살핌III로 전직 성공!{reset}")
        ctx:send_all("{bright_yellow}" .. ch.name .. "이(가) 보살핌III로 전직합니다!{reset}")
        return
    end

    ctx:send("{yellow}더 이상 전직할 수 없습니다.{reset}")
end)

-- ══════════════════════════════════════════════════════════════════
-- 기공집결 (cmdno=87, power) — 공격력 임시 부스트
-- ══════════════════════════════════════════════════════════════════

local LT_POWER = 18

register_command("기공집결", function(ctx, args)
    local ch = ctx.char

    local cd = ctx:check_cooldown(LT_POWER)
    if cd > 0 then
        ctx:send("{yellow}아직 집중할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end

    local cls = ch.class_id or CLASS_FIGHTER
    local level = ch.level or 1
    local bonus = math.min(50, math.floor(level / 4) + te_comp_chance(ch))

    pcall(function()
        ch.extensions.bonus_power = (ch.extensions.bonus_power or 0) + bonus
    end)

    ctx:set_cooldown(LT_POWER, 60)
    ctx:send("{bright_red}힘을 집중합니다! 공격력 +" .. bonus .. "{reset}")
    ctx:send_room(ch.name .. "이(가) 힘을 집중합니다!")
end)

-- ══════════════════════════════════════════════════════════════════
-- 명상 (cmdno=88, meditate) — MP 회복 부스트
-- ══════════════════════════════════════════════════════════════════

local LT_MEDITATE = 17

register_command("명상", function(ctx, args)
    local ch = ctx.char

    local cd = ctx:check_cooldown(LT_MEDITATE)
    if cd > 0 then
        ctx:send("{yellow}아직 명상할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end

    if ch.fighting then
        ctx:send("{yellow}전투 중에는 명상할 수 없습니다!{reset}")
        return
    end

    local cls = ch.class_id or CLASS_FIGHTER
    local level = ch.level or 1
    local int_bonus = te_bonus(te_stat(ch, "int", 13))

    local recovery = math.floor(level / 3) + int_bonus + math.floor(te_comp_chance(ch) / 2)
    recovery = math.max(5, recovery)

    ch.mana = math.min(ch.max_mana, ch.mana + recovery)

    ctx:set_cooldown(LT_MEDITATE, 60)
    ctx:send("{bright_cyan}명상으로 마력이 회복됩니다! MP +" .. recovery ..
        " (" .. ch.mana .. "/" .. ch.max_mana .. "){reset}")
    ctx:send_room(ch.name .. "이(가) 명상에 잠깁니다.")
end)

-- ══════════════════════════════════════════════════════════════════
-- 혈운무검술 (cmdno=91, accurate) — 명중률 임시 부스트
-- ══════════════════════════════════════════════════════════════════

local LT_ACCUR = 19

register_command("혈운무검술", function(ctx, args)
    local ch = ctx.char

    local cd = ctx:check_cooldown(LT_ACCUR)
    if cd > 0 then
        ctx:send("{yellow}아직 집중할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end

    local level = ch.level or 1
    local dex_bonus = te_bonus(te_stat(ch, "dex", 13))
    local acc_bonus = math.min(5, math.floor(level / 40) + dex_bonus)

    pcall(function()
        ch.extensions.accuracy_bonus = (ch.extensions.accuracy_bonus or 0) + acc_bonus
    end)

    ctx:set_cooldown(LT_ACCUR, 60)
    ctx:send("{bright_white}집중력을 높입니다! 명중률 +" .. acc_bonus .. "{reset}")
    ctx:send_room(ch.name .. "이(가) 집중력을 높입니다!")
end)


-- ══════════════════════════════════════════════════════════════════
-- 직업전환 (change_class) — 기본 직업 변경 (특수 방+비용)
-- 원본: kyk3.c change_class() — 전직방(RTRAIN) + 레벨50+ + 비용
-- ══════════════════════════════════════════════════════════════════

register_command("직업전환", function(ctx, args)
    if not te_room_has_flag(ctx, 8) then  -- RTRAIN
        ctx:send("{yellow}여기에서는 직업전환을 할 수 없습니다.{reset}")
        return
    end
    if not args or args == "" then
        ctx:send("사용법: 직업전환 <직업번호>")
        ctx:send("  1=암살자 2=야만인 3=성직자 4=전사 5=마법사 6=팔라딘 7=광전사 8=도적")
        return
    end
    local ch = ctx.char
    local cls = ch.class_id or CLASS_FIGHTER
    if cls >= CLASS_INVINCIBLE then
        ctx:send("{yellow}전직 캐릭터는 직업전환이 불가합니다.{reset}")
        return
    end
    if ch.level < 50 then
        ctx:send("{yellow}50레벨 이상이어야 직업전환을 할 수 있습니다.{reset}")
        return
    end
    local new_cls = tonumber(args)
    if not new_cls or new_cls < 1 or new_cls > 8 then
        ctx:send("유효한 직업 번호를 입력하세요. (1-8)")
        return
    end
    if new_cls == cls then
        ctx:send("이미 해당 직업입니다.")
        return
    end
    local cost = 200000
    if ch.gold < cost then
        ctx:send("{yellow}직업전환에 " .. cost .. "원이 필요합니다.{reset}")
        return
    end
    ch.gold = ch.gold - cost
    ch.class_id = new_cls
    local class_name = THREEEYES_CLASSES[new_cls] or "?"
    ctx:send("{bright_yellow}직업이 " .. class_name .. "(으)로 전환되었습니다!{reset}")
    ctx:send_all("{bright_yellow}" .. ch.name .. "이(가) " .. class_name .. "(으)로 직업전환합니다!{reset}")
end)


-- ══════════════════════════════════════════════════════════════════
-- 향상 (buy_states) — 골드로 스탯 포인트 구매
-- 원본: kyk3.c buy_states()
-- ══════════════════════════════════════════════════════════════════

register_command("향상", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 향상 <str|dex|con|int|pie>")
        return
    end
    local ch = ctx.char
    local stat_name = args:lower()
    local valid = {str=true, dex=true, con=true, int=true, pie=true}
    if not valid[stat_name] then
        ctx:send("유효한 스탯: str, dex, con, int, pie")
        return
    end
    local current = te_stat(ch, stat_name, 13)
    if current >= 25 then
        ctx:send("{yellow}이미 최대치에 도달했습니다. (25){reset}")
        return
    end
    local cost = current * current * 1000
    if ch.gold < cost then
        ctx:send("{yellow}향상에 " .. cost .. "원이 필요합니다. (현재: " .. ch.gold .. "원){reset}")
        return
    end
    ch.gold = ch.gold - cost
    local new_val = current + 1
    pcall(function()
        if not ch.stats then ch.stats = {} end
        ch.stats[stat_name] = new_val
    end)
    local kr_names = {str="힘", dex="민첩", con="체력", int="지능", pie="신앙"}
    ctx:send("{bright_green}" .. (kr_names[stat_name] or stat_name) .. "이(가) " ..
        new_val .. "(으)로 향상되었습니다! (-" .. cost .. "원){reset}")
end)


-- ══════════════════════════════════════════════════════════════════
-- 혈도봉쇄 (magic_stop) — 마법 사용 봉인
-- 원본: kyk8.c magic_stop()
-- ══════════════════════════════════════════════════════════════════

register_command("혈도봉쇄", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if not args or args == "" then
        ctx:send("누구의 마법을 봉쇄하시겠습니까?")
        return
    end
    local cls = ch.class_id or CLASS_FIGHTER
    if cls < CLASS_INVINCIBLE then
        ctx:send("{yellow}무적자 이상만 사용할 수 있습니다.{reset}")
        return
    end
    if ch.mana < 50 then
        ctx:send("마력이 부족합니다.")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("여기에 그런 사람은 없습니다.")
        return
    end
    if target == ch then
        ctx:send("자기 자신에게는 사용할 수 없습니다.")
        return
    end
    ch.mana = ch.mana - 50
    -- Apply silence effect (PSILNC flag)
    pcall(function()
        local flags = target.flags or {}
        local found = false
        for _, f in ipairs(flags) do
            if f == PSILNC then found = true; break end
        end
        if not found then flags[#flags + 1] = PSILNC end
        target.flags = flags
    end)
    ctx:send("{bright_red}" .. target.name .. "의 마법을 봉쇄합니다!{reset}")
    ctx:send_to(target, "{bright_red}" .. ch.name .. "이(가) 당신의 마법을 봉쇄합니다!{reset}")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "의 마법을 봉쇄합니다!")
end)


-- ══════════════════════════════════════════════════════════════════
-- 흡성대법 (absorb) — MP 흡수 공격, Invincible+ 전용
-- 원본: kyk8.c absorb()
-- ══════════════════════════════════════════════════════════════════

register_command("흡성대법", function(ctx, args)
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
    local cd = ctx:check_cooldown(21)
    if cd > 0 then
        ctx:send("{yellow}아직 사용할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end
    local absorb_amt = math.floor(ch.level * 2 + te_stat(ch, "int", 13) * 3)
    local actual = math.min(absorb_amt, target.mana or 0)
    target.mana = math.max(0, (target.mana or 0) - actual)
    ch.mana = math.min(ch.max_mana, ch.mana + actual)
    ctx:set_cooldown(21, 30)
    ctx:send("{bright_cyan}흡성대법! " .. target.name .. "에게서 MP " .. actual .. " 흡수!{reset}")
    ctx:send_to(target, "{bright_red}" .. ch.name .. "이(가) 당신의 마력을 흡수합니다!{reset}")
    if not ch.fighting then ctx:start_combat(target) end
end)


-- ══════════════════════════════════════════════════════════════════
-- 경공술 (haste) — 이동/공격속도 자기 버프
-- 원본: kyk8.c haste_self()
-- ══════════════════════════════════════════════════════════════════

register_command("경공술", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.mana < 30 then
        ctx:send("마력이 부족합니다.")
        return
    end
    local cd = ctx:check_cooldown(22)
    if cd > 0 then
        ctx:send("{yellow}아직 사용할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end
    ch.mana = ch.mana - 30
    -- Apply haste flag
    pcall(function()
        local flags = ch.flags or {}
        local found = false
        for _, f in ipairs(flags) do
            if f == PHASTE then found = true; break end
        end
        if not found then flags[#flags + 1] = PHASTE end
        ch.flags = flags
    end)
    ctx:set_cooldown(22, 120)
    ctx:send("{bright_cyan}경공술! 몸이 가벼워집니다!{reset}")
    ctx:send_room(ch.name .. "이(가) 경공술을 사용합니다!")
end)


-- ══════════════════════════════════════════════════════════════════
-- 신원법 (pray) — Cleric/Paladin HP 회복
-- 원본: kyk8.c pray()
-- ══════════════════════════════════════════════════════════════════

register_command("신원법", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    local cls = ch.class_id or CLASS_FIGHTER
    if cls ~= 3 and cls ~= 6 then
        ctx:send("성직자나 팔라딘만 신원법을 사용할 수 있습니다.")
        return
    end
    if ch.mana < 25 then
        ctx:send("마력이 부족합니다.")
        return
    end
    local cd = ctx:check_cooldown(23)
    if cd > 0 then
        ctx:send("{yellow}아직 사용할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end
    ch.mana = ch.mana - 25
    local pie = te_stat(ch, "pie", 13)
    local heal = math.floor(pie * 3 + ch.level * 2)
    ch.hp = math.min(ch.max_hp, ch.hp + heal)
    ctx:set_cooldown(23, 45)
    ctx:send("{bright_green}신원법! HP +" .. heal ..
        " (" .. ch.hp .. "/" .. ch.max_hp .. "){reset}")
    ctx:send_room(ch.name .. "이(가) 기도합니다.")
end)
