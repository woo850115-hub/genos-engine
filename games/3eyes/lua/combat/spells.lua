-- spells.lua — 3eyes spell system (62 spells, realm-based damage)
-- Original-faithful rewrite from: magic1.c (cast/offensive_spell/teach),
-- magic2-8.c (individual spell effects), magic8.c (spell_fail)
-- Uses: te_* functions from lib.lua

-- ══════════════════════════════════════════════════════════════════
-- Offensive spells (ospell[26]) — from global.c
-- realm: 0=none, 1=EARTH, 2=WIND, 3=FIRE, 4=WATER (1-indexed as in source)
-- bonus_type: 1=mprofic/10, 2=mprofic/6, 3=mprofic/4 (magic1.c:844-858)
-- ══════════════════════════════════════════════════════════════════
local OFFENSIVE_SPELLS = {
    {id=1,  name="상처",           realm=2, mp=3,   ndice=1, sdice=8,  pdice=0,  btype=1},
    {id=6,  name="화염구",         realm=3, mp=8,   ndice=2, sdice=8,  pdice=2,  btype=1},
    {id=13, name="번개",           realm=2, mp=12,  ndice=3, sdice=6,  pdice=3,  btype=1},
    {id=14, name="얼음폭발",       realm=4, mp=15,  ndice=3, sdice=8,  pdice=5,  btype=1},
    {id=25, name="충격",           realm=2, mp=5,   ndice=1, sdice=12, pdice=1,  btype=1},
    {id=26, name="지진파",         realm=1, mp=7,   ndice=2, sdice=6,  pdice=2,  btype=1},
    {id=27, name="화상",           realm=3, mp=6,   ndice=1, sdice=10, pdice=2,  btype=1},
    {id=28, name="수포",           realm=3, mp=10,  ndice=2, sdice=8,  pdice=3,  btype=2},
    {id=29, name="먼지돌풍",       realm=2, mp=8,   ndice=2, sdice=6,  pdice=2,  btype=2},
    {id=30, name="물화살",         realm=4, mp=6,   ndice=1, sdice=10, pdice=1,  btype=1},
    {id=31, name="분쇄",           realm=1, mp=12,  ndice=3, sdice=6,  pdice=4,  btype=2},
    {id=32, name="삼킴",           realm=4, mp=15,  ndice=3, sdice=8,  pdice=5,  btype=2},
    {id=33, name="폭발",           realm=3, mp=18,  ndice=4, sdice=6,  pdice=5,  btype=2},
    {id=34, name="증기",           realm=4, mp=16,  ndice=3, sdice=10, pdice=4,  btype=2},
    {id=35, name="파쇄",           realm=1, mp=20,  ndice=4, sdice=8,  pdice=6,  btype=3},
    {id=36, name="소각",           realm=3, mp=25,  ndice=5, sdice=8,  pdice=8,  btype=3},
    {id=37, name="혈액비등",       realm=3, mp=30,  ndice=6, sdice=8,  pdice=10, btype=3},
    {id=38, name="천둥",           realm=2, mp=28,  ndice=5, sdice=10, pdice=8,  btype=3},
    {id=39, name="지진",           realm=1, mp=35,  ndice=6, sdice=10, pdice=10, btype=3},
    {id=40, name="대홍수",         realm=4, mp=35,  ndice=6, sdice=10, pdice=10, btype=3},
    {id=47, name="경험흡수",       realm=0, mp=20,  ndice=3, sdice=8,  pdice=5,  btype=1},
    {id=56, name="드래곤슬레이브", realm=3, mp=60,  ndice=10,sdice=12, pdice=20, btype=3},
    {id=57, name="기가슬레이브",   realm=0, mp=100, ndice=15,sdice=12, pdice=30, btype=3},
    {id=58, name="플라즈마",       realm=3, mp=50,  ndice=8, sdice=10, pdice=15, btype=3},
    {id=59, name="메기도",         realm=1, mp=55,  ndice=8, sdice=12, pdice=15, btype=3},
    {id=60, name="지옥불",         realm=3, mp=45,  ndice=7, sdice=10, pdice=12, btype=3},
    {id=61, name="아쿠아레이",     realm=4, mp=45,  ndice=7, sdice=10, pdice=12, btype=3},
}

-- ══════════════════════════════════════════════════════════════════
-- Utility spells (36) — from magic2-7.c
-- flag: player flag to set (from lib.lua constants)
-- ══════════════════════════════════════════════════════════════════
local UTILITY_SPELLS = {
    -- Heals
    {id=0,  name="활력",     mp=3,  effect="heal",      value=15},
    {id=8,  name="회복",     mp=15, effect="heal",      value=50},
    {id=18, name="치료",     mp=10, effect="heal",      value=30},
    {id=19, name="대치료",   mp=30, effect="heal",      value=100},
    -- Buffs (set player flag)
    {id=2,  name="빛",       mp=2,  effect="flag_buff", flag=PLIGHT, lt=11, dur_base=300},
    {id=4,  name="축복",     mp=5,  effect="flag_buff", flag=PBLESS, lt=15, dur_base=300},
    {id=5,  name="보호",     mp=5,  effect="ac_buff",   ac_mod=-10, lt=16, dur_base=300},
    {id=7,  name="투명",     mp=8,  effect="flag_buff", flag=PINVIS, lt=12, dur_base=300},
    {id=9,  name="투명감지", mp=5,  effect="flag_buff", flag=PDINVI, lt=14, dur_base=300},
    {id=10, name="마법감지", mp=3,  effect="flag_buff", flag=PDMAGC, lt=14, dur_base=300},
    {id=21, name="공중부양", mp=8,  effect="flag_buff", flag=PLEVIT, lt=14, dur_base=300},
    {id=22, name="화염저항", mp=10, effect="flag_buff", flag=PRFIRE, lt=14, dur_base=300},
    {id=23, name="비행",     mp=12, effect="flag_buff", flag=PFLY,   lt=14, dur_base=300},
    {id=24, name="마법저항", mp=15, effect="flag_buff", flag=PRMAGI, lt=14, dur_base=300},
    {id=41, name="성향감지", mp=3,  effect="flag_buff", flag=PKNOWA, lt=14, dur_base=300},
    {id=43, name="냉기저항", mp=10, effect="flag_buff", flag=PRCOLD, lt=14, dur_base=300},
    {id=44, name="수중호흡", mp=8,  effect="flag_buff", flag=PWATER, lt=14, dur_base=300},
    {id=45, name="돌방패",   mp=12, effect="flag_buff", flag=PSHIEL, lt=14, dur_base=300},
    -- Cures
    {id=3,  name="해독",     mp=5,  effect="cure_flag", flag=PPOISN},
    {id=42, name="저주해제", mp=10, effect="remove_curse"},
    {id=48, name="질병치료", mp=8,  effect="cure_flag", flag=PDISEA},
    {id=49, name="실명치료", mp=8,  effect="cure_flag", flag=PBLIND},
    -- Debuffs (applied to target)
    {id=50, name="공포",     mp=12, effect="debuff_flag", flag=PFEARS, target_req=true},
    {id=53, name="실명",     mp=10, effect="debuff_flag", flag=PBLIND, target_req=true},
    {id=54, name="침묵",     mp=12, effect="debuff_flag", flag=PSILNC, target_req=true},
    {id=55, name="매혹",     mp=15, effect="charm",       target_req=true},
    -- Movement
    {id=11, name="텔레포트", mp=10, effect="teleport"},
    {id=16, name="귀환",     mp=5,  effect="recall"},
    {id=17, name="소환",     mp=15, effect="summon",    target_req=true},
    {id=52, name="전송",     mp=20, effect="transport", target_req=true},
    -- Info
    {id=20, name="추적",     mp=8,  effect="track",     target_req=true},
    {id=46, name="위치감지", mp=5,  effect="locate",    target_req=true},
    -- Special
    {id=15, name="마법부여", mp=20, effect="enchant"},
    {id=51, name="방활력",   mp=15, effect="room_heal", value=20},
    {id=62, name="강화",     mp=25, effect="upgrade"},
}

-- ══════════════════════════════════════════════════════════════════
-- Spell registry (id → spell data)
-- ══════════════════════════════════════════════════════════════════
local ALL_SPELLS = {}
for _, sp in ipairs(OFFENSIVE_SPELLS) do
    sp.is_offensive = true
    ALL_SPELLS[sp.id] = sp
end
for _, sp in ipairs(UTILITY_SPELLS) do ALL_SPELLS[sp.id] = sp end

-- ── Player flag check helper (for spells targeting players) ──────────
local function player_has_flag_spells(mob, flag_id)
    if not mob.session then return false end
    local ok, pd = pcall(function() return mob.session.player_data end)
    if not ok or not pd then return false end
    local ok2, flags = pcall(function() return pd.flags end)
    if not ok2 or not flags then return false end
    local i = 0
    while true do
        local ok3, f = pcall(function() return flags[i] end)
        if not ok3 or f == nil then break end
        if f == flag_id then return true end
        i = i + 1
    end
    return false
end

-- ── Spell lookup by name (spllist[] partial match, magic1.c:26-40) ──

local function find_spell(name)
    -- Exact match first
    for id, sp in pairs(ALL_SPELLS) do
        if type(sp) == "table" and sp.name == name then
            return id, sp
        end
    end
    -- Prefix match (partial, as in original spllist[] search)
    for id, sp in pairs(ALL_SPELLS) do
        if type(sp) == "table" and sp.name and sp.name:find(name, 1, true) == 1 then
            return id, sp
        end
    end
    return nil, nil
end

-- ══════════════════════════════════════════════════════════════════
-- offensive_spell() — Original magic1.c:819-1050
-- ══════════════════════════════════════════════════════════════════

-- ── Mage-only spell IDs (magic1.c:901-920) ───────────────────────
-- 얼음폭발(14), 천둥(38), 지진(39), 대홍수(40) — Mage or Invincible+ only
local MAGE_ONLY_SPELLS = {[14]=true, [38]=true, [39]=true, [40]=true}

local function offensive_spell(ctx, caster, target, spell, how)
    -- how: "cast" or "wand" or "scroll" (affects bonus calculation)
    how = how or "cast"
    local spell_realm = spell.realm or 0      -- 1-indexed in source
    local realm_idx = spell_realm - 1          -- 0-indexed for te_mprofic()

    -- 0. Mage-only spell check (magic1.c:901-920)
    if MAGE_ONLY_SPELLS[spell.id] then
        local cls = caster.class_id or CLASS_FIGHTER
        if cls ~= CLASS_MAGE and cls < CLASS_INVINCIBLE then
            ctx:send("{yellow}마법사만 쓸 수 있는 주문입니다.{reset}")
            return 0, false
        end
    end

    -- 1. Bonus calculation (magic1.c:844-858) — only when CAST
    local bns = 0
    if how == "cast" then
        local int_bonus = te_bonus(te_stat(caster, "int", 13))
        if spell.btype == 1 then
            bns = int_bonus + math.floor(te_mprofic(caster, realm_idx) / 10)
        elseif spell.btype == 2 then
            bns = int_bonus + math.floor(te_mprofic(caster, realm_idx) / 6)
        elseif spell.btype == 3 then
            bns = int_bonus + math.floor(te_mprofic(caster, realm_idx) / 4)
        end
    end

    -- 2. Room realm bonus (magic1.c:874-897)
    local room_realm = te_get_room_realm(ctx)
    if room_realm ~= nil and spell_realm > 0 then
        if room_realm == realm_idx then
            -- Same realm: bonus doubled
            bns = bns * 2
        elseif te_realm_opposite(room_realm) == realm_idx then
            -- Opposite realm: negative
            bns = math.min(-bns, -5)
        end
    end

    -- 3. Spell fail check (magic1.c:1005) — BEFORE damage roll
    if how == "cast" and te_spell_fail(caster) then
        ctx:send("{yellow}주문 시전에 실패했습니다!{reset}")
        return 0, false
    end

    -- 4. Roll damage: dice(ndice, sdice, pdice + bns)
    local dmg = te_dice(spell.ndice, spell.sdice, (spell.pdice or 0) + bns)
    dmg = math.max(1, dmg)

    -- 4a. Giga Slave special (magic1.c:1038-1041): self-damage = 90% HP
    if spell.id == 57 then
        dmg = math.floor(caster.hp * 0.9)
        caster.hp = caster.hp - dmg
    end

    -- 5. Magic resistance (magic1.c:1033-1036): PRMAGI reduces damage
    if not target.is_npc and player_has_flag_spells(target, PRMAGI) then
        local pie_val = te_stat(target, "pie", 13)
        local int_val = te_stat(target, "int", 13)
        local resist = math.min(50, pie_val + int_val)
        dmg = dmg - math.floor((dmg * 2 * resist) / 200)
        dmg = math.max(1, dmg)
    elseif target.is_npc then
        -- NPC magic resistance: check MRMAGI flag (Python list — pcall + index)
        local has_rmagi = false
        pcall(function()
            local flags = target.proto.act_flags
            if flags then
                for i = 0, 100 do
                    local ok, f = pcall(function() return flags[i] end)
                    if not ok or f == nil then break end
                    if f == "resist_magic" or f == "flag_28" then has_rmagi = true; break end
                end
            end
        end)
        if has_rmagi then
            local pie_val = te_stat(target, "pie", 13)
            local int_val = te_stat(target, "int", 13)
            local resist = math.min(50, pie_val + int_val)
            dmg = dmg - math.floor((dmg * 2 * resist) / 200)
            dmg = math.max(1, dmg)
        end
    end

    -- 6. Apply damage
    target.hp = target.hp - dmg

    -- 6. Realm proficiency growth (magic1.c:1020-1040)
    -- addrealm = (dmg * mob_exp) / mob_max_hp
    if not caster.is_npc and target.is_npc and spell_realm > 0 then
        local ok_exp, mon_exp = pcall(function() return target.proto.experience end)
        if ok_exp and mon_exp and mon_exp > 0 then
            local ok_hp, hpmax = pcall(function() return target.max_hp end)
            if ok_hp and hpmax and hpmax > 0 then
                local dealt = math.min(dmg, math.max(0, target.hp + dmg))
                local addrealm = math.floor((dealt * mon_exp) / hpmax)
                addrealm = math.min(addrealm, mon_exp)
                if addrealm > 0 then
                    local ok_ext, ext = pcall(function() return caster.extensions end)
                    if ok_ext and ext then
                        local ok_r, realm_arr = pcall(function() return ext.realm end)
                        if ok_r and realm_arr then
                            local ok_v, cur = pcall(function() return realm_arr[realm_idx] end)
                            if ok_v and cur then
                                pcall(function()
                                    realm_arr[realm_idx] = cur + addrealm
                                end)
                            end
                        end
                    end
                end
            end
        end
    end

    -- 7. Output messages (original Korean format)
    local realm_name = ""
    if spell_realm > 0 then
        realm_name = THREEEYES_REALM[realm_idx] or ""
        if realm_name ~= "" then realm_name = "[" .. realm_name .. "] " end
    end

    ctx:send("{bright_cyan}" .. spell.name .. "! " .. realm_name ..
        target.name .. "에게 {bright_white}" .. dmg .. "{bright_cyan}의 피해를 입혔습니다!{reset}")
    if target.session then
        ctx:send_to(target, "{bright_red}" .. caster.name .. "이(가) " .. spell.name ..
            "을(를) 시전! {bright_white}[" .. dmg .. "]{reset}")
    end
    ctx:send_room(caster.name .. "이(가) " .. target.name .. "에게 " ..
        spell.name .. "을(를) 시전합니다!")

    -- 8. Experience drain special (id=47)
    if spell.id == 47 and not caster.is_npc and target.is_npc then
        local drain = math.floor(dmg / 2)
        if drain > 0 then
            caster.experience = (caster.experience or 0) + drain
            ctx:send("{bright_green}경험치 +" .. drain .. "{reset}")
        end
    end

    return dmg, true
end

-- ══════════════════════════════════════════════════════════════════
-- Utility spell effects — from magic2-7.c
-- ══════════════════════════════════════════════════════════════════

local function do_utility_spell(ctx, caster, spell, target_name)
    local effect = spell.effect
    local ch = caster

    -- ── Healing spells ──
    if effect == "heal" then
        local heal = spell.value or 15
        ch.hp = math.min(ch.max_hp, ch.hp + heal)
        ctx:send("{bright_green}" .. spell.name .. " — HP +" .. heal ..
            " (" .. ch.hp .. "/" .. ch.max_hp .. "){reset}")
        return true
    end

    -- ── Flag buffs (set player flag + cooldown duration) ──
    if effect == "flag_buff" then
        if ctx:has_flag(spell.flag) then
            ctx:send("{yellow}이미 " .. spell.name .. "의 효과를 받고 있습니다.{reset}")
            return false
        end
        -- Duration: base + comp_chance * base (original: 300 + comp_chance*300)
        local dur = (spell.dur_base or 300) + te_comp_chance(ch) * (spell.dur_base or 300)
        ctx:set_flag(spell.flag)
        if spell.lt then
            ctx:set_cooldown(spell.lt, dur)
        end
        -- Also apply affect for tracking (affect_id = 1000 + spell.id)
        local affect_id = spell.affect_id or (1000 + spell.id)
        ctx:apply_affect(ch, affect_id, math.floor(dur / 5))
        ctx:send("{bright_cyan}" .. spell.name .. "의 효과가 당신을 감쌉니다.{reset}")
        ctx:send_room(ch.name .. "이(가) " .. spell.name .. " 주문을 시전합니다.")
        return true
    end

    -- ── AC buff (protection spell, id=5) ──
    if effect == "ac_buff" then
        local ac_mod = spell.ac_mod or -10
        ch.armor_class = (ch.armor_class or 100) + ac_mod
        local dur = (spell.dur_base or 300) + te_comp_chance(ch) * (spell.dur_base or 300)
        ctx:apply_affect(ch, 1005, math.floor(dur / 5), {armor_class = ac_mod})
        if spell.lt then
            ctx:set_cooldown(spell.lt, dur)
        end
        ctx:send("{bright_cyan}보호의 장막이 당신을 감쌉니다.{reset}")
        return true
    end

    -- ── Cure flags ──
    if effect == "cure_flag" then
        if not ctx:has_flag(spell.flag) then
            ctx:send("{yellow}치유할 상태이상이 없습니다.{reset}")
            return false
        end
        ctx:clear_flag(spell.flag)
        ctx:send("{bright_green}" .. spell.name .. " — 상태이상이 치유됩니다.{reset}")
        return true
    end

    -- ── Remove curse (id=42) — removes OCURSE from all equipment ──
    if effect == "remove_curse" then
        local equip = ctx:get_equipment()
        local removed = 0
        if equip then
            for i = 1, #equip do
                local entry = equip[i]
                if entry and entry.obj and entry.obj.proto then
                    local ok, flags = pcall(function() return entry.obj.proto.flags end)
                    if ok and flags then
                        -- Check for cursed flag and remove it
                        local new_flags = {}
                        local had_curse = false
                        for fi = 0, 100 do
                            local ok2, f = pcall(function() return flags[fi] end)
                            if not ok2 or f == nil then break end
                            if f == "cursed" or f == "flag_2" then
                                had_curse = true
                            else
                                new_flags[#new_flags + 1] = f
                            end
                        end
                        if had_curse then
                            -- Mark curse removed in per-instance values
                            pcall(function() entry.obj.values["cursed_removed"] = true end)
                            removed = removed + 1
                        end
                    end
                end
            end
        end
        if removed > 0 then
            ctx:send("{bright_green}저주가 해제됩니다! " .. removed .. "개의 장비에서 저주를 풀었습니다.{reset}")
        else
            ctx:send("{bright_green}저주가 해제됩니다.{reset}")
        end
        ctx:send_room(ch.name .. "이(가) 저주 해제 주문을 시전합니다.")
        return true
    end

    -- ── Debuff flags (target required) ──
    if effect == "debuff_flag" then
        local target = target_name and ctx:find_char(target_name) or ch.fighting
        if not target then
            ctx:send("대상을 찾을 수 없습니다.")
            return false
        end
        if target == ch then
            ctx:send("자기 자신에게 해로운 주문을 시전할 수 없습니다!")
            return false
        end
        -- Debuff on NPC: set flag via proto.act_flags or session.player_data
        if target.session then
            -- Player target: set flag via session
            local pd = target.session.player_data
            if pd then
                local flags = pd.flags or {}
                local fid = spell.flag
                local found = false
                for _, f in ipairs(flags) do
                    if f == fid then found = true; break end
                end
                if not found then
                    flags[#flags + 1] = fid
                    pd.flags = flags
                end
            end
        end
        ctx:send("{bright_magenta}" .. spell.name .. "! " ..
            target.name .. "에게 효과 적용!{reset}")
        if target.session then
            ctx:send_to(target, "{red}" .. ch.name .. "이(가) " ..
                spell.name .. "을(를) 시전! 효과를 받습니다.{reset}")
        end
        if not ch.fighting and target.is_npc then
            ctx:start_combat(target)
        end
        return true
    end

    -- ── Charm (id=55) ──
    if effect == "charm" then
        local target = target_name and ctx:find_char(target_name) or ch.fighting
        if not target or not target.is_npc then
            ctx:send("NPC 대상을 찾을 수 없습니다.")
            return false
        end
        -- Charm level check: target level must be < caster level
        if (target.level or 1) >= (ch.level or 1) then
            ctx:send("{yellow}" .. target.name .. "이(가) 매혹에 저항합니다!{reset}")
            return false
        end
        -- Stop combat if fighting the caster
        if target.fighting == ch then
            ctx:stop_combat(target)
        end
        -- Set charmed flag on NPC
        pcall(function()
            target.extensions = target.extensions or {}
            target.extensions.charmed_by = ch.name
        end)
        -- Make NPC follow caster
        pcall(function() ctx:defer_force(target, "follow " .. ch.name) end)
        ctx:send("{bright_magenta}" .. target.name .. "이(가) 매혹되었습니다!{reset}")
        ctx:send_room(ch.name .. "이(가) " .. target.name .. "을(를) 매혹합니다.")
        return true
    end

    -- ── Teleport (id=11) — random room ──
    if effect == "teleport" then
        if te_room_has_flag(ctx, 4) then  -- RNOTEL
            ctx:send("{yellow}이 방에서는 텔레포트 할 수 없습니다.{reset}")
            return false
        end
        if ch.fighting then
            ctx:send("{yellow}전투 중에는 텔레포트 할 수 없습니다!{reset}")
            return false
        end
        local dest = ctx:get_random_room_vnum()
        if not dest or dest == ch.room_vnum then
            ctx:send("{yellow}공간이 왜곡되었지만... 아무 일도 일어나지 않았습니다.{reset}")
            return false
        end
        ctx:send_room(ch.name .. "이(가) 사라집니다!")
        ctx:move_char_to(ch, dest)
        ctx:send("{bright_cyan}공간이 왜곡되며 당신이 순간이동합니다!{reset}")
        ctx:defer_look()
        return true
    end

    -- ── Recall (id=16) ──
    if effect == "recall" then
        if ch.fighting then
            ctx:send("{yellow}전투 중에는 귀환할 수 없습니다!{reset}")
            return false
        end
        local start_room = ctx:get_start_room()
        ctx:send_room(ch.name .. "이(가) 사라집니다!")
        ctx:move_char_to(ch, start_room)
        ctx:send("{bright_cyan}귀환! 당신은 시작 지점으로 돌아갑니다.{reset}")
        ctx:defer_look()
        return true
    end

    -- ── Summon (id=17) ──
    if effect == "summon" then
        if te_room_has_flag(ctx, 4) then  -- RNOTEL
            ctx:send("{yellow}이 방에서는 소환할 수 없습니다.{reset}")
            return false
        end
        local target = target_name and ctx:find_char(target_name)
        if not target then
            ctx:send("소환 대상을 찾을 수 없습니다.")
            return false
        end
        if target == ch then
            ctx:send("자기 자신을 소환할 수 없습니다.")
            return false
        end
        -- Check target PNOSUM
        if target.session then
            local pd = target.session.player_data or {}
            local flags = pd.flags or {}
            for _, f in ipairs(flags) do
                if f == PNOSUM then
                    ctx:send("{yellow}" .. target.name .. "이(가) 소환을 거부합니다.{reset}")
                    return false
                end
            end
        end
        ctx:move_char_to(target, ch.room_vnum)
        ctx:send("{bright_cyan}" .. target.name .. "을(를) 소환했습니다!{reset}")
        if target.session then
            ctx:send_to(target, "{bright_cyan}" .. ch.name ..
                "이(가) 당신을 소환합니다!{reset}")
        end
        return true
    end

    -- ── Transport (id=52) — move caster to target's room ──
    if effect == "transport" then
        local target = target_name and ctx:find_char(target_name)
        if not target then
            ctx:send("대상을 찾을 수 없습니다.")
            return false
        end
        if target == ch then
            ctx:send("자기 자신에게 전송할 수 없습니다.")
            return false
        end
        ctx:send_room(ch.name .. "이(가) 사라집니다!")
        ctx:move_char_to(ch, target.room_vnum)
        ctx:send("{bright_cyan}" .. target.name .. "이(가) 있는 곳으로 이동합니다!{reset}")
        ctx:defer_look()
        return true
    end

    -- ── Track (id=20) ──
    if effect == "track" then
        local target = target_name and ctx:find_char(target_name)
        if not target then
            ctx:send("추적 대상을 찾을 수 없습니다.")
            return false
        end
        if target.room_vnum == ch.room_vnum then
            ctx:send("{bright_cyan}" .. target.name .. "이(가) 바로 이 방에 있습니다!{reset}")
        else
            -- Simplified: just show target is somewhere
            ctx:send("{bright_cyan}" .. target.name .. "의 기운이 느껴집니다...{reset}")
            ctx:set_flag(PTRACK)
            ctx:set_cooldown(LT_TRACK, 10)
        end
        return true
    end

    -- ── Locate (id=46) ──
    if effect == "locate" then
        local target = target_name and ctx:find_char(target_name)
        if not target then
            ctx:send("대상을 찾을 수 없습니다.")
            return false
        end
        local room = nil
        pcall(function()
            room = ctx._engine.world.rooms[target.room_vnum]
        end)
        local room_name = room and room.proto and room.proto.name or "알 수 없는 곳"
        ctx:send("{bright_cyan}" .. target.name .. "의 위치: " .. room_name .. "{reset}")
        return true
    end

    -- ── Enchant (id=15) — weapon adjustment +1 ──
    if effect == "enchant" then
        local weapon = nil
        pcall(function() weapon = ch.equipment[16] end)
        if not weapon then
            pcall(function() weapon = ch.equipment["weapon"] end)
        end
        if not weapon or not weapon.proto then
            ctx:send("{yellow}마법을 부여할 무기를 장비하고 있지 않습니다.{reset}")
            return false
        end
        -- Increment adjustment in values
        local ok, vals = pcall(function() return weapon.values end)
        if ok and vals then
            local ok2, adj = pcall(function() return vals["adjustment"] end)
            local cur_adj = (ok2 and tonumber(adj)) or 0
            pcall(function() weapon.values["adjustment"] = cur_adj + 1 end)
            ctx:send("{bright_cyan}" .. (weapon.name or "무기") ..
                "에 마법이 부여됩니다! (+" .. (cur_adj + 1) .. "){reset}")
        else
            ctx:send("{bright_cyan}무기에 마법이 부여됩니다!{reset}")
        end
        return true
    end

    -- ── Room heal (id=51) — heal all in room ──
    if effect == "room_heal" then
        local heal = spell.value or 20
        local room = ctx:get_room()
        if room then
            local healed = 0
            for _, c in ipairs(room.characters) do
                if c.hp < c.max_hp then
                    c.hp = math.min(c.max_hp, c.hp + heal)
                    healed = healed + 1
                    if c.session and c ~= ch then
                        ctx:send_to(c, "{bright_green}" .. ch.name ..
                            "의 방활력! HP +" .. heal .. "{reset}")
                    end
                end
            end
            ctx:send("{bright_green}방활력! 방 안의 모두에게 HP +" .. heal .. "{reset}")
        end
        return true
    end

    -- ── Upgrade (id=62) — weapon upgrade (magic4.c:528-598) ──
    if effect == "upgrade" then
        local cls = ch.class_id or CLASS_FIGHTER
        -- Care_III+ only (magic4.c:546)
        if cls < CLASS_CARE_III then
            ctx:send("{yellow}보살핌III 이상만 강화 주문을 쓸 수 있습니다.{reset}")
            return false
        end
        -- Find weapon from args
        if not target_name or target_name == "" then
            ctx:send("강화할 무기의 이름을 지정하세요.")
            return false
        end
        local weapon = ctx:find_inv_item(target_name)
        if not weapon then
            weapon = ctx:find_equip_item(target_name)
        end
        if not weapon or not weapon.proto then
            ctx:send("{yellow}그런 물건은 가지고 있지 않습니다.{reset}")
            return false
        end
        -- Must be a weapon (WIELD type)
        local is_weapon = false
        local ok_ws, ws = pcall(function() return weapon.proto.wear_slots end)
        if ok_ws and ws then
            for _, s in ipairs(ws) do
                if s == 16 or s == "weapon" or s == "wield" then
                    is_weapon = true; break
                end
            end
        end
        if not is_weapon then
            ctx:send("{yellow}무기만 강화할 수 있습니다.{reset}")
            return false
        end
        -- Check upgrade count (max 10, stored in values.upgrade_count)
        local ok_v, vals = pcall(function() return weapon.values end)
        local upgrade_count = 0
        if ok_v and vals then
            local ok_uc, uc = pcall(function() return vals["upgrade_count"] end)
            if ok_uc and uc then upgrade_count = tonumber(uc) or 0 end
        end
        local MAX_UPGRADE = 10
        if upgrade_count >= MAX_UPGRADE then
            ctx:send("{yellow}이미 최고로 강화되어 있습니다.{reset}")
            return false
        end
        -- Calculate cost: (ndice*sdice + pdice) * shotscur * 3 + 1000
        -- + upgrade_count * base_cost * 0.1
        local ok_dd, dd = pcall(function() return weapon.proto.damage_dice end)
        local ndice, sdice, pdice = 1, 4, 0
        if ok_dd and dd then
            local n, s, p = dd:match("(%d+)d(%d+)([%+%-]?%d*)")
            ndice = tonumber(n) or 1
            sdice = tonumber(s) or 4
            pdice = tonumber(p) or 0
        end
        local ok_sc, shots = pcall(function() return weapon.shots_remaining end)
        local shotscur = (ok_sc and shots) and shots or 100
        local base_cost = (ndice * sdice + pdice) * shotscur * 3 + 1000
        local exp_cost = math.floor(base_cost + upgrade_count * base_cost * 0.1)
        -- Check experience
        local cur_exp = ch.experience or 0
        if cur_exp < exp_cost then
            ctx:send("{yellow}이 무기를 강화하는데는 " .. exp_cost ..
                "만큼의 경험치가 필요합니다.{reset}")
            return false
        end
        -- Apply upgrade
        ch.experience = cur_exp - exp_cost
        local new_pdice = pdice + math.floor((ndice * sdice + pdice) * 0.1)
        pcall(function()
            weapon.values["upgrade_count"] = upgrade_count + 1
        end)
        -- Update damage string
        local new_dd = ndice .. "d" .. sdice .. "+" .. new_pdice
        pcall(function()
            weapon.values["damage"] = new_dd
        end)
        ctx:send("{bright_cyan}" .. (weapon.name or "무기") ..
            "에 주문이 걸려 잠깐 빛나더니 강해졌습니다.{reset}")
        ctx:send("경험치 " .. exp_cost .. " 소모.")
        ctx:send_room(ch.name .. "이(가) " .. (weapon.name or "무기") ..
            "에 강화 주문을 걸었습니다.")
        return true
    end

    -- Fallback
    ctx:send("{cyan}" .. spell.name .. "을(를) 시전합니다.{reset}")
    return true
end

-- Class-based spell permission (fallback when spell learning not tracked)
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

-- ══════════════════════════════════════════════════════════════════
-- cast() — Original magic1.c:24-129
-- ══════════════════════════════════════════════════════════════════

register_command("주문", function(ctx, args)
    if not args or args == "" then
        ctx:send("무슨 주문을 시전하시겠습니까?")
        return
    end

    local ch = ctx.char

    -- 1. Parse: "주문이름 [대상]"
    local spell_name, target_name = args:match("^(%S+)%s+(.+)$")
    if not spell_name then spell_name = args end

    -- 2. Find spell (spllist[] partial match)
    local spell_id, spell = find_spell(spell_name)
    if not spell then
        ctx:send("그런 주문은 없습니다.")
        return
    end

    -- 3. PBLIND check (magic1.c:46)
    if ctx:has_flag(PBLIND) then
        ctx:send("{yellow}실명 상태에서는 주문을 시전할 수 없습니다!{reset}")
        return
    end

    -- 4. RNOMAG room check (magic1.c:50)
    if te_room_has_flag(ctx, 3) then  -- RNOMAG
        ctx:send("{yellow}이 방에서는 마법을 사용할 수 없습니다.{reset}")
        return
    end

    -- 5. S_ISSET check (magic1.c:54) — player must know the spell
    --    Fallback: can_cast() class-based check when spell-learning is not tracked
    if not ch.is_npc then
        local known = ctx:knows_spell(spell_id)
        if not known and not can_cast(ch, spell_id) then
            ctx:send("{yellow}당신의 직업으로는 시전할 수 없는 주문입니다.{reset}")
            return
        end
    end

    -- 6. LT_SPELL cooldown check (magic1.c:58)
    local cd = ctx:check_cooldown(LT_SPELL)
    if cd > 0 then
        ctx:send("{yellow}아직 주문을 시전할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end

    -- 7. PSILNC check
    if ctx:has_flag(PSILNC) then
        ctx:send("{yellow}침묵 상태에서는 주문을 시전할 수 없습니다!{reset}")
        return
    end

    -- 7a. Giga Slave cannot be used in survival rooms (magic1.c:994-1000)
    if spell_id == 57 and te_room_has_flag(ctx, 17) then  -- RSUVIV
        ctx:send("{yellow}서바이벌방에서는 사용할 수 없습니다!{reset}")
        return
    end

    -- 8. MP check
    local mp_cost = spell.mp or 5
    if ch.mana < mp_cost then
        ctx:send("{yellow}마력이 부족합니다. (필요: " .. mp_cost ..
            ", 현재: " .. ch.mana .. "){reset}")
        return
    end

    -- 9. Deduct MP
    ch.mana = ch.mana - mp_cost

    -- 10. PHIDDN clear (magic1.c:70)
    if ctx:has_flag(PHIDDN) then
        ctx:clear_flag(PHIDDN)
        ctx:send("은신이 해제되었습니다.")
    end

    -- 11. Dispatch: offensive or utility
    if spell.is_offensive then
        -- Find target
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
        -- MUNKIL check (act_flags is Python list — pcall + index loop)
        if target.is_npc then
            local is_unkillable = false
            pcall(function()
                local af = target.proto.act_flags
                if af then
                    for i = 0, 100 do
                        local ok, f = pcall(function() return af[i] end)
                        if not ok or f == nil then break end
                        if f == "unkillable" or f == tostring(MUNKIL) or f == "flag_2" then
                            is_unkillable = true
                            break
                        end
                    end
                end
            end)
            if is_unkillable then
                ctx:send("{yellow}" .. target.name .. "에게는 공격할 수 없습니다.{reset}")
                ch.mana = ch.mana + mp_cost
                return
            end
        end

        local dmg, success = offensive_spell(ctx, ch, target, spell, "cast")

        if success then
            -- Start combat if not fighting
            if not ch.fighting then
                ctx:start_combat(target)
            end
            -- Death check
            if target.hp <= 0 then
                ctx:stop_combat(ch)
                ctx:defer_death(target, ch)
            end
        end
    else
        do_utility_spell(ctx, ch, spell, target_name)
    end

    -- 12. Set LT_SPELL cooldown (magic1.c:115-129)
    local cls = ch.class_id or CLASS_FIGHTER
    local spell_cd = 5  -- default
    if cls == CLASS_CLERIC or cls == CLASS_MAGE or cls >= CLASS_CARETAKER then
        spell_cd = 3
    end
    if cls >= CLASS_DM then
        spell_cd = 1
    end
    -- Special spell extra cooldown
    if spell_id == 56 then spell_cd = spell_cd + 3 end  -- 드래곤슬레이브
    if spell_id == 57 then spell_cd = spell_cd + 25 end  -- 기가슬레이브
    -- Advanced spells (id >= 35): +1
    if spell_id >= 35 and spell_id ~= 56 and spell_id ~= 57 then
        spell_cd = spell_cd + 1
    end
    ctx:set_cooldown(LT_SPELL, spell_cd)

end)

register_command("cast", function(ctx, args)
    ctx:call_command("주문", args or "")
end)

-- ══════════════════════════════════════════════════════════════════
-- teach — 다른 플레이어에게 주문 가르치기 (magic1.c)
-- ══════════════════════════════════════════════════════════════════

register_command("가르쳐", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: teach <주문이름> <대상>")
        return
    end

    local ch = ctx.char

    -- Class restriction: only Mage/Cleric or Invincible+ can teach
    local cls = ch.class_id or CLASS_FIGHTER
    if cls ~= CLASS_MAGE and cls ~= CLASS_CLERIC and cls < CLASS_INVINCIBLE then
        ctx:send("{yellow}마법사나 성직자만 기술을 가르칠 수 있습니다.{reset}")
        return
    end

    local spell_name, target_name = args:match("^(%S+)%s+(.+)$")
    if not spell_name or not target_name then
        ctx:send("사용법: teach <주문이름> <대상>")
        return
    end

    local spell_id, spell = find_spell(spell_name)
    if not spell then
        ctx:send("그런 주문은 없습니다.")
        return
    end

    -- Must know the spell
    if not ctx:knows_spell(spell_id) then
        ctx:send("{yellow}당신이 모르는 주문은 가르칠 수 없습니다.{reset}")
        return
    end

    local target = ctx:find_char(target_name)
    if not target or not target.session then
        ctx:send("대상 플레이어를 찾을 수 없습니다.")
        return
    end

    if target == ch then
        ctx:send("자기 자신에게 주문을 가르칠 수 없습니다.")
        return
    end

    -- Check if target already knows it (Python dict+list — pcall + 0-indexed)
    local ok_pd, t_pd = pcall(function() return target.session.player_data end)
    if ok_pd and t_pd then
        local ok_k, t_known = pcall(function() return t_pd["spells_known"] end)
        if ok_k and t_known then
            local i = 0
            while true do
                local ok, sid = pcall(function() return t_known[i] end)
                if not ok or sid == nil then break end
                if sid == spell_id then
                    ctx:send("{yellow}" .. target.name ..
                        "은(는) 이미 그 주문을 알고 있습니다.{reset}")
                    return
                end
                i = i + 1
            end
        end
    end

    -- Teach — use Python helper to append spell (lupa can't call list.append)
    ctx:learn_spell_for(target, spell_id)

    ctx:send("{bright_cyan}" .. target.name .. "에게 " .. spell.name ..
        " 주문을 가르쳤습니다.{reset}")
    ctx:send_to(target, "{bright_cyan}" .. ch.name .. "이(가) " .. spell.name ..
        " 주문을 가르쳐 줍니다!{reset}")
    ctx:send_room(ch.name .. "이(가) " .. target.name .. "에게 " ..
        spell.name .. " 마법을 가르쳐주고 있습니다.")
end)

register_command("teach", function(ctx, args)
    ctx:call_command("가르쳐", args or "")
end)

-- ══════════════════════════════════════════════════════════════════
-- study — 스크롤(두루마리)로 주문 배우기 (magic1.c:242-343)
-- ══════════════════════════════════════════════════════════════════

register_command("공부", function(ctx, args)
    if not args or args == "" then
        ctx:send("스크롤을 지정하여 공부하시기 바랍니다.")
        return
    end

    local ch = ctx.char

    -- PBLIND check
    if ctx:has_flag(PBLIND) then
        ctx:send("{red}눈이 멀어있어서 아무것도 볼 수 없습니다.{reset}")
        return
    end

    -- Find scroll in inventory
    local scroll = ctx:find_inv_item(args)
    if not scroll then
        scroll = ctx:find_equip_item(args)
    end
    if not scroll then
        ctx:send("그런 물건은 가지고 있지 않습니다.")
        return
    end

    -- Must be a scroll (item_type == "scroll")
    local item_type = nil
    pcall(function() item_type = scroll.proto.item_type end)
    if item_type ~= "scroll" then
        ctx:send("그것은 스크롤이 아닙니다.")
        return
    end

    -- Get spell id from scroll proto.values or instance.values (magicpower in original)
    local scroll_spell_id = nil
    pcall(function() scroll_spell_id = scroll.proto.values["spell_id"] end)
    if not scroll_spell_id then
        pcall(function() scroll_spell_id = scroll.proto.values["magicpower"] end)
    end
    -- Also check instance values (mutable copy)
    if not scroll_spell_id then
        pcall(function() scroll_spell_id = scroll.values["spell_id"] end)
    end
    if not scroll_spell_id then
        ctx:send("이 스크롤에는 배울 수 있는 주문이 없습니다.")
        return
    end
    scroll_spell_id = tonumber(scroll_spell_id)

    local spell = ALL_SPELLS[scroll_spell_id]
    if not spell then
        ctx:send("이 스크롤의 주문을 해독할 수 없습니다.")
        return
    end

    -- Level check: player effective level vs scroll required level
    local plev = ch.level or 1
    local cls = ch.class_id or CLASS_FIGHTER
    if cls == CLASS_INVINCIBLE then plev = plev + 1000
    elseif cls == CLASS_CARETAKER then plev = plev + 2000
    elseif cls == CLASS_CARE_II then plev = plev + 3000
    elseif cls > CLASS_CARE_II then plev = plev + 4000
    end

    local scroll_level = 0
    pcall(function() scroll_level = tonumber(scroll.proto.values["level"]) or 0 end)
    if scroll_level == 0 then
        pcall(function() scroll_level = tonumber(scroll.values["level"]) or 0 end)
    end
    local scroll_class = 0
    pcall(function() scroll_class = tonumber(scroll.proto.values["class_req"]) or 0 end)
    if scroll_class == 0 then
        pcall(function() scroll_class = tonumber(scroll.values["class_req"]) or 0 end)
    end

    local olev = scroll_level or 0
    if scroll_class == CLASS_INVINCIBLE then olev = olev + 1000
    elseif scroll_class == CLASS_CARETAKER then olev = olev + 2000
    elseif scroll_class == CLASS_CARE_II then olev = olev + 3000
    elseif scroll_class > CLASS_CARE_II then olev = olev + 4000
    end

    -- Class restriction (original: special field)
    if cls < CLASS_INVINCIBLE and scroll_class > 0 and scroll_class ~= cls then
        local cls_name = THREEEYES_CLASSES[scroll_class] or "알 수 없는"
        ctx:send("이 스크롤은 \"" .. cls_name .. "\" 직업만 공부할 수 있습니다.")
        return
    end

    if plev < olev then
        ctx:send("당신의 현재 레벨로는 이 마법서를 공부할 수 없습니다.")
        return
    end

    -- Already know check
    if ctx:knows_spell(scroll_spell_id) then
        ctx:send("{yellow}이미 " .. spell.name .. " 주문을 알고 있습니다.{reset}")
        return
    end

    -- PHIDDN clear
    if ctx:has_flag(PHIDDN) then
        ctx:clear_flag(PHIDDN)
    end

    -- Learn the spell
    ctx:learn_spell(scroll_spell_id)

    -- Consume the scroll
    ctx:remove_item(scroll)

    ctx:send("{bright_cyan}당신은 " .. spell.name ..
        " 마법을 배우기 시작합니다.\n" ..
        "시간이 흘러가면서 기묘한 힘이 흘러가고 있습니다.\n" ..
        "당신의 정신에 새로운 능력이 깃듭니다!{reset}")
    ctx:send_room(ch.name .. "이(가) 마법서를 묵상하며 공부하기 시작합니다.")
end)

register_command("study", function(ctx, args)
    ctx:call_command("공부", args or "")
end)

