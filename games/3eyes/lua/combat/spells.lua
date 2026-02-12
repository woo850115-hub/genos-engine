-- spells.lua — 3eyes spell system (63 spells, realm-based damage)

-- Offensive spells with realm association
-- From source ospell[26]: { spell_id, realm, mp, ndice, sdice, pdice }
-- realm: 0=none, 1=EARTH, 2=WIND, 3=FIRE, 4=WATER (1-indexed in source)
local OFFENSIVE_SPELLS = {
    {id=1,  name="상처",       realm=2, mp=3,  ndice=1, sdice=8, pdice=0},   -- hurt/WIND
    {id=6,  name="화염구",     realm=3, mp=8,  ndice=2, sdice=8, pdice=2},   -- fireball/FIRE
    {id=13, name="번개",       realm=2, mp=12, ndice=3, sdice=6, pdice=3},   -- lightning/WIND
    {id=14, name="얼음폭발",   realm=4, mp=15, ndice=3, sdice=8, pdice=5},   -- ice_blast/WATER
    {id=25, name="충격",       realm=2, mp=5,  ndice=1, sdice=12, pdice=1},  -- shock/WIND
    {id=26, name="지진파",     realm=1, mp=7,  ndice=2, sdice=6, pdice=2},   -- rumble/EARTH
    {id=27, name="화상",       realm=3, mp=6,  ndice=1, sdice=10, pdice=2},  -- burn/FIRE
    {id=28, name="수포",       realm=3, mp=10, ndice=2, sdice=8, pdice=3},   -- blister/FIRE
    {id=29, name="먼지돌풍",   realm=2, mp=8,  ndice=2, sdice=6, pdice=2},   -- dust_gust/WIND
    {id=30, name="물화살",     realm=4, mp=6,  ndice=1, sdice=10, pdice=1},  -- water_bolt/WATER
    {id=31, name="분쇄",       realm=1, mp=12, ndice=3, sdice=6, pdice=4},   -- crush/EARTH
    {id=32, name="삼킴",       realm=4, mp=15, ndice=3, sdice=8, pdice=5},   -- engulf/WATER
    {id=33, name="폭발",       realm=3, mp=18, ndice=4, sdice=6, pdice=5},   -- burst/FIRE
    {id=34, name="증기",       realm=4, mp=16, ndice=3, sdice=10, pdice=4},  -- steam/WATER
    {id=35, name="파쇄",       realm=1, mp=20, ndice=4, sdice=8, pdice=6},   -- shatter/EARTH
    {id=36, name="소각",       realm=3, mp=25, ndice=5, sdice=8, pdice=8},   -- immolate/FIRE
    {id=37, name="혈액비등",   realm=3, mp=30, ndice=6, sdice=8, pdice=10},  -- blood_boil/FIRE
    {id=38, name="천둥",       realm=2, mp=28, ndice=5, sdice=10, pdice=8},  -- thunder/WIND
    {id=39, name="지진",       realm=1, mp=35, ndice=6, sdice=10, pdice=10}, -- earthquake/EARTH
    {id=40, name="대홍수",     realm=4, mp=35, ndice=6, sdice=10, pdice=10}, -- flood_fill/WATER
    {id=47, name="경험흡수",   realm=0, mp=20, ndice=3, sdice=8, pdice=5},   -- drain_exp
    {id=56, name="드래곤슬레이브", realm=3, mp=60, ndice=10, sdice=12, pdice=20}, -- dragon_slave/FIRE
    {id=57, name="기가슬레이브", realm=0, mp=100, ndice=15, sdice=12, pdice=30}, -- giga_slave
    {id=58, name="플라즈마",   realm=3, mp=50, ndice=8, sdice=10, pdice=15},  -- plasma/FIRE
    {id=59, name="메기도",     realm=1, mp=55, ndice=8, sdice=12, pdice=15},  -- megiddo/EARTH
    {id=60, name="지옥불",     realm=3, mp=45, ndice=7, sdice=10, pdice=12},  -- hellfire/FIRE
    {id=61, name="아쿠아레이", realm=4, mp=45, ndice=7, sdice=10, pdice=12},  -- aqua_ray/WATER
}

-- Non-offensive spells
local UTILITY_SPELLS = {
    {id=0,  name="활력",     mp=3,  effect="heal",   value=15},
    {id=2,  name="빛",       mp=2,  effect="light",  value=0},
    {id=3,  name="해독",     mp=5,  effect="cure",   value=0},
    {id=4,  name="축복",     mp=5,  effect="buff",   value=0, affect_id=1004},
    {id=5,  name="보호",     mp=5,  effect="buff",   value=0, affect_id=1005},
    {id=7,  name="투명",     mp=8,  effect="buff",   value=0, affect_id=1007},
    {id=8,  name="회복",     mp=15, effect="heal",   value=50},
    {id=9,  name="투명감지", mp=5,  effect="buff",   value=0, affect_id=1009},
    {id=10, name="마법감지", mp=3,  effect="buff",   value=0, affect_id=1010},
    {id=11, name="텔레포트", mp=10, effect="teleport",value=0},
    {id=15, name="마법부여", mp=20, effect="enchant", value=0},
    {id=16, name="귀환",     mp=5,  effect="recall",  value=0},
    {id=17, name="소환",     mp=15, effect="summon",  value=0},
    {id=18, name="치료",     mp=10, effect="heal",    value=30},
    {id=19, name="대치료",   mp=30, effect="heal",    value=100},
    {id=20, name="추적",     mp=8,  effect="track",   value=0},
    {id=21, name="공중부양", mp=8,  effect="buff",    value=0, affect_id=1021},
    {id=22, name="화염저항", mp=10, effect="buff",    value=0, affect_id=1022},
    {id=23, name="비행",     mp=12, effect="buff",    value=0, affect_id=1023},
    {id=24, name="마법저항", mp=15, effect="buff",    value=0, affect_id=1024},
    {id=41, name="성향감지", mp=3,  effect="detect",  value=0},
    {id=42, name="저주해제", mp=10, effect="cure",    value=0},
    {id=43, name="냉기저항", mp=10, effect="buff",    value=0, affect_id=1043},
    {id=44, name="수중호흡", mp=8,  effect="buff",    value=0, affect_id=1044},
    {id=45, name="돌방패",   mp=12, effect="buff",    value=0, affect_id=1045},
    {id=46, name="위치감지", mp=5,  effect="locate",  value=0},
    {id=48, name="질병치료", mp=8,  effect="cure",    value=0},
    {id=49, name="실명치료", mp=8,  effect="cure",    value=0},
    {id=50, name="공포",     mp=12, effect="debuff",  value=0},
    {id=51, name="방활력",   mp=15, effect="room_heal", value=20},
    {id=52, name="전송",     mp=20, effect="transport", value=0},
    {id=53, name="실명",     mp=10, effect="debuff",  value=0},
    {id=54, name="침묵",     mp=12, effect="debuff",  value=0},
    {id=55, name="매혹",     mp=15, effect="charm",   value=0},
    {id=62, name="강화",     mp=25, effect="upgrade", value=0},
}

-- Build name→spell lookup
local ALL_SPELLS = {}
for _, sp in ipairs(OFFENSIVE_SPELLS) do ALL_SPELLS[sp.id] = sp end
for _, sp in ipairs(UTILITY_SPELLS) do ALL_SPELLS[sp.id] = sp end

local function find_spell(name)
    name = name:lower()
    for id, sp in pairs(ALL_SPELLS) do
        if type(sp) == "table" and sp.name then
            if sp.name == name then return id, sp end
        end
    end
    -- Prefix match
    for id, sp in pairs(ALL_SPELLS) do
        if type(sp) == "table" and sp.name then
            if sp.name:find(name, 1, true) == 1 then return id, sp end
        end
    end
    return nil, nil
end

-- Class spell level limits (simplified: Mage=all, Cleric=heal/buff, others=limited)
local function can_cast(mob, spell_id)
    local class_id = mob.class_id or 4
    -- Mage can cast everything
    if class_id == 5 then return true end
    -- Cleric can cast heals and buffs
    if class_id == 3 or class_id == 6 then
        local sp = ALL_SPELLS[spell_id]
        if sp and sp.effect and (sp.effect == "heal" or sp.effect == "buff" or sp.effect == "cure") then
            return true
        end
        -- Cleric can also cast offensive spells of EARTH/WATER realms
        if sp and sp.realm and (sp.realm == 1 or sp.realm == 4) then return true end
        return spell_id <= 20
    end
    -- Assassin/Ranger: limited spells
    if class_id == 1 or class_id == 7 then
        return spell_id <= 10
    end
    -- Fighter/Barbarian/Thief: minimal
    return spell_id <= 3
end

-- Calculate spell damage with realm bonus
local function calc_spell_damage(caster, spell)
    local base = spell.pdice or 0
    for i = 1, (spell.ndice or 1) do
        base = base + math.random(1, math.max(1, spell.sdice or 4))
    end
    -- Realm bonus: up to +50% damage at 100% realm proficiency
    if spell.realm and spell.realm > 0 then
        local realm_pct = te_realm_percent(caster, spell.realm - 1)  -- 0-indexed realm
        base = base + math.floor(base * realm_pct / 200)
    end
    -- INT bonus for casters
    local int_val = te_stat(caster, "int", 13)
    base = base + te_bonus(int_val)
    return math.max(1, base)
end

-- Cast command
register_command("cast", function(ctx, args)
    if not args or args == "" then
        ctx:send("무슨 주문을 시전하시겠습니까?")
        return
    end
    local ch = ctx.char
    local spell_name, target_name = args:match("^(%S+)%s+(.+)$")
    if not spell_name then
        spell_name = args
    end

    local spell_id, spell = find_spell(spell_name)
    if not spell then
        ctx:send("그런 주문은 없습니다.")
        return
    end

    if not can_cast(ch, spell_id) then
        ctx:send("당신의 직업으로는 시전할 수 없는 주문입니다.")
        return
    end

    local mp_cost = spell.mp or 5
    if ch.mana < mp_cost then
        ctx:send("마력이 부족합니다. (필요: " .. mp_cost .. ")")
        return
    end
    ch.mana = ch.mana - mp_cost

    -- Offensive spell
    if spell.ndice and spell.ndice > 0 and not spell.effect then
        local target
        if target_name then
            target = ctx:find_char(target_name)
        else
            target = ch.fighting
        end
        if not target then
            ctx:send("대상을 찾을 수 없습니다.")
            ch.mana = ch.mana + mp_cost  -- refund
            return
        end
        if target == ch then
            ctx:send("자기 자신에게 공격 주문을 시전할 수 없습니다!")
            ch.mana = ch.mana + mp_cost
            return
        end

        local dmg = calc_spell_damage(ch, spell)
        target.hp = target.hp - dmg

        local realm_name = ""
        if spell.realm and spell.realm > 0 then
            realm_name = THREEEYES_REALM[spell.realm - 1] or ""
            if realm_name ~= "" then realm_name = "[" .. realm_name .. "] " end
        end

        ctx:send("{bright_cyan}" .. spell.name .. "! " .. realm_name ..
            target.name .. "에게 " .. dmg .. "의 피해!{reset}")
        if target.session then
            ctx:send_to(target, "{red}" .. ch.name .. "이(가) " .. spell.name ..
                "을(를) 시전합니다! [" .. dmg .. "]{reset}")
        end

        if not ch.fighting then
            ctx:start_combat(target)
        end
        if target.hp <= 0 then
            ctx:stop_combat(ch)
            ctx:defer_death(target, ch)
        end
        return
    end

    -- Utility spells
    if spell.effect == "heal" then
        local heal = spell.value or 15
        ch.hp = math.min(ch.max_hp, ch.hp + heal)
        ctx:send("{bright_green}" .. spell.name .. " — HP +" .. heal .. "{reset}")
    elseif spell.effect == "buff" then
        local dur = 5 + math.floor(ch.level / 10)
        ctx:apply_affect(ch, spell.affect_id or 1000, dur)
        ctx:send("{bright_cyan}" .. spell.name .. "의 효과가 당신을 감쌉니다.{reset}")
    elseif spell.effect == "cure" then
        ctx:send("{bright_green}" .. spell.name .. " — 상태이상이 치유됩니다.{reset}")
    elseif spell.effect == "recall" then
        ctx:recall()
        ctx:send("{bright_cyan}귀환!{reset}")
    else
        ctx:send("{cyan}" .. spell.name .. "을(를) 시전합니다.{reset}")
    end
end, "시전")

-- Practice command
register_command("practice", function(ctx, args)
    local ch = ctx.char
    local lines = {"{bright_cyan}-- 주문 목록 --{reset}"}
    local class_id = ch.class_id or 4
    local count = 0

    for id = 0, 62 do
        local sp = ALL_SPELLS[id]
        if sp and can_cast(ch, id) then
            local mp_str = sp.mp and (" [마력:" .. sp.mp .. "]") or ""
            lines[#lines + 1] = string.format("  %3d) %-12s%s", id, sp.name, mp_str)
            count = count + 1
        end
    end

    if count == 0 then
        lines[#lines + 1] = "  사용 가능한 주문이 없습니다."
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "수련")
