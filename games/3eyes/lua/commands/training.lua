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
