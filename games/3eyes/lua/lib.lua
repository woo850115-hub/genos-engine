-- lib.lua — 3eyes utility functions
-- Original: player.c (profic/mprofic/compute_thaco/mod_profic), kyk3.c (comp_chance)

-- ── Class/Race names (1-indexed) ──────────────────────────────
THREEEYES_CLASSES = {
    [1]="암살자", [2]="야만인", [3]="성직자", [4]="전사",
    [5]="마법사", [6]="팔라딘", [7]="광전사", [8]="도적",
    [9]="무적자", [10]="보살핌자", [11]="보살핌II", [12]="보살핌III",
    [13]="존메이커", [14]="리얼존메이커", [15]="부관리자", [16]="관리자", [17]="최고관리자",
}

THREEEYES_RACES = {
    [1]="드워프", [2]="엘프", [3]="하프엘프", [4]="호빗",
    [5]="인간", [6]="오크", [7]="반거인", [8]="노움",
}

-- Caster classes
THREEEYES_CASTER = {[3]=true, [5]=true}

-- Proficiency type names (Korean)
THREEEYES_PROF = {[0]="날붙이", [1]="찌르기", [2]="둔기", [3]="장병기", [4]="원거리"}

-- Realm names (Korean)
THREEEYES_REALM = {[0]="대지", [1]="바람", [2]="화염", [3]="물"}

-- ── Class ID constants ────────────────────────────────────────
CLASS_ASSASSIN   = 1
CLASS_BARBARIAN  = 2
CLASS_CLERIC     = 3
CLASS_FIGHTER    = 4
CLASS_MAGE       = 5
CLASS_PALADIN    = 6
CLASS_RANGER     = 7
CLASS_THIEF      = 8
CLASS_INVINCIBLE = 9
CLASS_CARETAKER  = 10
CLASS_CARE_II    = 11
CLASS_CARE_III   = 12
CLASS_ZONEMAKER  = 13
CLASS_REALZONEMAKER = 14
CLASS_SUB_DM     = 15
CLASS_DM         = 16
CLASS_ME         = 17

-- ── Player Flags ──────────────────────────────────────────────
PBLESS  = 0
PHIDDN  = 1
PINVIS  = 2
PNOSUM  = 4
PBLIND  = 5
PCHARM  = 6
PFEARS  = 7
PHASTE  = 9
PCHAOS  = 10
PPOISN  = 12
PDISEA  = 13
PDINVI  = 18
PDMAGC  = 19
PFLY    = 22
PLEVIT  = 23
PWATER  = 24
PSHIEL  = 25
PRFIRE  = 26
PRCOLD  = 27
PRMAGI  = 28
PMARRI  = 29
PFAMIL  = 30
PUPDMG  = 36
PSILNC  = 37
PLIGHT  = 42
PTRACK  = 43

-- ── Monster Flags ─────────────────────────────────────────────
MAGGRE = 0
MFLEER = 1
MUNKIL = 2
MMGONL = 3
MENONL = 4
MMALES = 7
MMAGIC = 15

-- ── Cooldown Slots ────────────────────────────────────────────
LT_ATTCK = 0
LT_SPELL = 1
LT_HEALS = 2
LT_STEAL = 3
LT_PICKL = 4
LT_SEARC = 5
LT_TRACK = 6
LT_HIDE  = 8
LT_SNEAK = 20
LT_TRAIN = 30
LT_FORGE = 31

-- ── Position constants ────────────────────────────────────────
-- (also defined in common/lua/lib.lua, re-exported for convenience)
TE_POS_DEAD     = 0
TE_POS_SLEEPING = 4
TE_POS_RESTING  = 5
TE_POS_SITTING  = 6
TE_POS_FIGHTING = 7
TE_POS_STANDING = 8

-- ── Stat bonus table (global.c bonus[35]) ─────────────────────
local STAT_BONUS = {
    [0]=-4,[1]=-4,[2]=-4,[3]=-3,[4]=-3,[5]=-2,[6]=-2,[7]=-1,[8]=-1,[9]=-1,
    [10]=0,[11]=0,[12]=0,[13]=0,[14]=1,[15]=1,[16]=1,[17]=2,[18]=2,[19]=2,
    [20]=3,[21]=3,[22]=3,[23]=3,[24]=4,[25]=4,[26]=4,[27]=4,[28]=4,
    [29]=5,[30]=5,[31]=5,[32]=5,[33]=5,[34]=5,
}

-- ── Stat access ───────────────────────────────────────────────

function te_stat(mob, key, default)
    default = default or 13
    local ok, val = pcall(function() return mob.stats[key] end)
    if ok and val then return val end
    return default
end

function te_bonus(stat_value)
    local v = math.min(math.max(stat_value or 0, 0), 34)
    return STAT_BONUS[v] or 0
end

-- ── Proficiency raw value access ──────────────────────────────

function te_proficiency(mob, prof_type)
    local ok, ext = pcall(function() return mob.extensions end)
    if not ok or not ext then return 0 end
    local ok2, prof = pcall(function() return ext.proficiency end)
    if not ok2 or not prof then return 0 end
    local ok3, val = pcall(function() return prof[prof_type] end)
    if ok3 and val then return val end
    return 0
end

function te_realm(mob, realm_type)
    local ok, ext = pcall(function() return mob.extensions end)
    if not ok or not ext then return 0 end
    local ok2, realm = pcall(function() return ext.realm end)
    if not ok2 or not realm then return 0 end
    local ok3, val = pcall(function() return realm[realm_type] end)
    if ok3 and val then return val end
    return 0
end

-- ── Proficiency experience→percent tables (from player.c) ─────

local PROF_TABLES = {
    -- Fighter/Invincible/Caretaker/Care_II/Care_III/ZM/RZM/SUB_DM/DM/ME
    fighter = {0, 768, 1024, 1440, 1910, 16000, 31214, 167000, 268488, 695000, 934808, 500000000},
    barbarian = {0, 1536, 2048, 2880, 3820, 32000, 62428, 334000, 536976, 1390000, 1869616, 500000000},
    thief_ranger = {0, 2304, 3072, 4320, 5730, 48000, 93642, 501000, 805464, 2085000, 2804424, 500000000},
    cleric_paladin_assassin = {0, 3072, 4096, 5076, 7640, 64000, 124856, 668000, 1073952, 2780000, 3939232, 500000000},
    mage = {0, 5376, 7168, 10080, 13370, 112000, 218498, 1169000, 1879416, 4865000, 6543656, 500000000},
}

local REALM_TABLES = {
    mage = {0, 1024, 2048, 4096, 8192, 16384, 35768, 85536, 140000, 459410, 2073306, 500000000},
    cleric = {0, 1024, 4092, 8192, 16384, 32768, 70536, 119000, 226410, 709410, 2973307, 500000000},
    paladin_ranger = {0, 1024, 8192, 16384, 32768, 65536, 105000, 165410, 287306, 809410, 3538232, 500000000},
    default = {0, 1024, 40000, 80000, 120000, 160000, 205000, 222000, 380000, 965410, 5495000, 500000000},
}

local function get_prof_table(class_id)
    if class_id == CLASS_FIGHTER or class_id >= CLASS_INVINCIBLE then
        return PROF_TABLES.fighter
    elseif class_id == CLASS_BARBARIAN then
        return PROF_TABLES.barbarian
    elseif class_id == CLASS_THIEF or class_id == CLASS_RANGER then
        return PROF_TABLES.thief_ranger
    elseif class_id == CLASS_CLERIC or class_id == CLASS_PALADIN or class_id == CLASS_ASSASSIN then
        return PROF_TABLES.cleric_paladin_assassin
    else
        return PROF_TABLES.mage
    end
end

local function get_realm_table(class_id)
    if class_id == CLASS_MAGE or class_id >= CLASS_INVINCIBLE then
        return REALM_TABLES.mage
    elseif class_id == CLASS_CLERIC then
        return REALM_TABLES.cleric
    elseif class_id == CLASS_PALADIN or class_id == CLASS_RANGER then
        return REALM_TABLES.paladin_ranger
    else
        return REALM_TABLES.default
    end
end

-- Raw experience → percentage (0-100)
-- Original: player.c profic()/mprofic() algorithm
local function raw_to_percent(raw, tbl)
    if raw < 0 then raw = 0 end
    if raw > 500000000 then raw = 500000000 end
    local prof = 0
    local i = 0
    for idx = 1, 11 do
        if raw < tbl[idx + 1] then
            prof = 10 * (idx - 1)
            i = idx
            break
        end
    end
    if i == 0 then return 100 end
    local denom = tbl[i + 1] - tbl[i]
    if denom > 0 then
        prof = prof + math.floor(((raw - tbl[i]) * 10) / denom)
    end
    return math.min(100, prof)
end

-- ── profic() — weapon proficiency percent (player.c:1261-1345) ─

function te_profic(mob, index)
    local raw = te_proficiency(mob, index)
    local tbl = get_prof_table(mob.class_id or CLASS_FIGHTER)
    return raw_to_percent(raw, tbl)
end

-- Alias for backward compat
function te_prof_percent(mob, prof_type)
    return te_profic(mob, prof_type)
end

-- ── mprofic() — realm proficiency percent (player.c:1353-1419) ─
-- Note: original uses 1-indexed realm (1=EARTH..4=WATER), we use 0-indexed

function te_mprofic(mob, realm_index)
    local raw = te_realm(mob, realm_index)
    local tbl = get_realm_table(mob.class_id or CLASS_FIGHTER)
    return raw_to_percent(raw, tbl)
end

function te_realm_percent(mob, realm_type)
    return te_mprofic(mob, realm_type)
end

-- ── comp_chance() — kyk3.c:757-769 ───────────────────────────

function te_comp_chance(mob)
    local lev = mob.level or 1
    local cls = mob.class_id or CLASS_FIGHTER
    if cls >= CLASS_INVINCIBLE then lev = lev + 150 end
    if cls >= CLASS_CARETAKER then lev = lev + 150 end
    return math.min(80, math.floor(lev / 6))
end

-- ── mod_profic() — weapon proficiency / class_divisor (player.c:1170-1203) ─

function te_mod_profic(mob)
    local cls = mob.class_id or CLASS_FIGHTER
    local amt
    if cls == CLASS_FIGHTER or cls == CLASS_BARBARIAN or
       cls >= CLASS_INVINCIBLE then
        amt = 20
    elseif cls == CLASS_RANGER or cls == CLASS_PALADIN then
        amt = 25
    elseif cls == CLASS_THIEF or cls == CLASS_ASSASSIN or cls == CLASS_CLERIC then
        amt = 30
    else
        amt = 40
    end

    -- Determine weapon type: default BLUNT(2)
    local weapon_type = 2
    local ok, weapon = pcall(function() return mob.equipment[16] end)
    if ok and weapon and weapon.proto then
        local ok2, wtype = pcall(function() return weapon.proto.values["weapon_type"] end)
        if ok2 and wtype and tonumber(wtype) then
            weapon_type = math.min(4, tonumber(wtype))
        end
    end

    return math.floor(te_profic(mob, weapon_type) / amt)
end

-- ── compute_thaco() — THAC0 calculation (player.c:1131-1162) ──

-- THAC0 table: [class][level/10] (0-indexed level bracket, 1-indexed class)
local THAC0_TABLE = {
    [1] = {18,18,18,17,17,16,16,15,15,14,14,13,13,12,12,11,10,10,9,9},  -- Assassin
    [2] = {20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,3,2},        -- Barbarian
    [3] = {20,20,19,18,18,17,16,16,15,14,14,13,13,12,12,11,10,10,9,8},  -- Cleric
    [4] = {20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,3,3},        -- Fighter
    [5] = {20,20,19,19,18,18,18,17,17,16,16,16,15,15,14,14,14,13,13,11},-- Mage
    [6] = {19,19,18,18,17,16,16,15,15,14,14,13,13,12,11,11,10,9,8,7},  -- Paladin
    [7] = {19,19,18,17,16,16,15,15,14,14,13,12,12,11,11,10,9,9,8,7},   -- Ranger
    [8] = {20,20,19,19,18,18,17,17,16,16,15,15,14,14,13,13,12,12,11,11},-- Thief
}

function te_compute_thaco(mob)
    if mob.is_npc then
        -- NPC: use level-based estimate (level/10 index into Fighter table)
        local n = math.min(19, math.floor((mob.level or 1) / 10))
        local cls_table = THAC0_TABLE[mob.class_id or 4]
        if not cls_table then cls_table = THAC0_TABLE[4] end
        return cls_table[n + 1] or 20
    end

    local cls = mob.class_id or 4
    local level = mob.level or 1
    local n = math.min(19, math.floor(level / 10))

    -- Base from table (use Fighter table for advanced classes)
    local cls_table = THAC0_TABLE[cls]
    if not cls_table then cls_table = THAC0_TABLE[4] end
    local thaco = cls_table[n + 1] or 20

    -- Weapon adjustment
    local ok, weapon = pcall(function() return mob.equipment[16] end)
    if ok and weapon and weapon.proto then
        local ok2, adj = pcall(function() return weapon.proto.values["adjustment"] end)
        if ok2 and adj then
            thaco = thaco - (tonumber(adj) or 0)
        end
    end

    -- Weapon proficiency bonus
    thaco = thaco - te_mod_profic(mob)

    -- STR bonus (clamped to -4..+7)
    local str_val = te_stat(mob, "str", 13)
    local str_bonus = math.min(7, math.max(-4, te_bonus(str_val)))
    thaco = thaco - str_bonus

    -- Class-based final range
    if cls < CLASS_INVINCIBLE then
        thaco = math.max(0, math.min(20, thaco))
    elseif cls < CLASS_CARETAKER then
        thaco = math.max(-5, math.min(10, thaco))
    else
        thaco = math.max(-10, math.min(0, thaco))
    end

    -- PBLESS bonus
    if mob.session then
        local ok3, has = pcall(function() return mob.session.player_data end)
        if ok3 and has then
            local ok4, flags = pcall(function() return has.flags end)
            if ok4 and flags then
                -- Python list: 0-indexed pcall loop
                local fi = 0
                while true do
                    local ok5, f = pcall(function() return flags[fi] end)
                    if not ok5 or f == nil then break end
                    if f == PBLESS then
                        thaco = thaco - 3
                        break
                    end
                    fi = fi + 1
                end
            end
        end
    end

    return thaco
end

-- ── spell_fail() — magic8.c:837-943 ──────────────────────────
-- Returns true if spell SUCCEEDS, false if it fails

local SPELL_FAIL_PARAMS = {
    [CLASS_ASSASSIN]  = {5, 30},
    [CLASS_BARBARIAN] = {5, 0},
    [CLASS_CLERIC]    = {5, 65},
    [CLASS_FIGHTER]   = {5, 10},
    [CLASS_MAGE]      = {5, 75},
    [CLASS_PALADIN]   = {5, 50},
    [CLASS_RANGER]    = {4, 56},
    [CLASS_THIEF]     = {6, 22},
}

function te_spell_fail(mob)
    local cls = mob.class_id or CLASS_FIGHTER
    -- Advanced classes always succeed
    if cls >= CLASS_INVINCIBLE then return false end

    local params = SPELL_FAIL_PARAMS[cls]
    if not params then return false end

    local mult, base = params[1], params[2]
    local cc = te_comp_chance(mob)
    local int_bonus = te_bonus(te_stat(mob, "int", 13))
    local chance = (cc + int_bonus) * mult + base

    local roll = math.random(1, 100)
    return roll > chance  -- true = failed
end

-- ── dice() utility ────────────────────────────────────────────

function te_dice(ndice, sdice, pdice)
    local total = pdice or 0
    for i = 1, (ndice or 1) do
        total = total + math.random(1, math.max(1, sdice or 4))
    end
    return total
end

-- mrand(a,b) equivalent
function te_mrand(a, b)
    if a >= b then return a end
    return a + math.random(0, b - a)
end

-- ── Room flag check (DB stores TEXT[] as "flag_N" or named strings) ──

-- Map numeric room flag IDs to possible DB string names
local ROOM_FLAG_NAMES = {
    [0]  = {"dark", "flag_0"},               -- RDARKR
    [1]  = {"dark_night", "flag_1"},         -- RDARKN
    [2]  = {"peaceful", "no_kill", "flag_2"},-- RNOKIL
    [3]  = {"no_magic", "flag_3"},           -- RNOMAG
    [4]  = {"no_teleport", "flag_4"},        -- RNOTEL
    [5]  = {"healing", "flag_5"},            -- RHEALR
    [6]  = {"bank", "flag_6"},               -- RBANK
    [7]  = {"shop", "flag_7"},               -- RSHOP
    [8]  = {"train", "flag_8"},              -- RTRAIN
    [9]  = {"repair", "flag_9"},             -- RREPAI
    [10] = {"forge", "flag_10"},             -- RFORGE
    [11] = {"poker", "flag_11"},             -- RPOKER
    [12] = {"earth", "flag_12"},             -- REARTH
    [13] = {"wind", "flag_13"},              -- RWINDR
    [14] = {"fire", "flag_14"},              -- RFIRER
    [15] = {"water", "flag_15"},             -- RWATER
    [17] = {"survival", "flag_17"},          -- RSUVIV
    [19] = {"harmful", "flag_19"},           -- RPHARM
    [20] = {"poison", "flag_20"},            -- RPPOIS
    [21] = {"mp_drain", "flag_21"},          -- RPMPDR
    [22] = {"no_map", "flag_22"},            -- RNOMAP
    [23] = {"event", "flag_23"},             -- REVENT
    [24] = {"family", "flag_24"},            -- RFAMIL
    [27] = {"marriage", "flag_27"},          -- RMARRI
    [28] = {"killer_jail", "flag_28"},       -- RKILLR
}

function te_room_has_flag(ctx, flag_id)
    local names = ROOM_FLAG_NAMES[flag_id]
    if names then
        for _, name in ipairs(names) do
            if ctx:has_room_flag(name) then return true end
        end
    end
    -- Fallback: try "flag_N"
    return ctx:has_room_flag("flag_" .. flag_id)
end

-- ── Room realm detection (for spell bonus) ──────────────────────

function te_get_room_realm(ctx)
    -- Returns realm index (0-3) or nil if no realm flag
    -- 0=EARTH, 1=WIND, 2=FIRE, 3=WATER
    if te_room_has_flag(ctx, 12) then return 0 end  -- REARTH
    if te_room_has_flag(ctx, 13) then return 1 end  -- RWINDR
    if te_room_has_flag(ctx, 14) then return 2 end  -- RFIRER
    if te_room_has_flag(ctx, 15) then return 3 end  -- RWATER
    return nil
end

-- ── Realm opposition (WATER↔FIRE, WIND↔EARTH) ──────────────────

function te_realm_opposite(realm)
    -- Returns the opposing realm index
    -- EARTH(0)↔WIND(1), FIRE(2)↔WATER(3)
    if realm == 0 then return 1 end  -- EARTH → WIND
    if realm == 1 then return 0 end  -- WIND → EARTH
    if realm == 2 then return 3 end  -- FIRE → WATER
    if realm == 3 then return 2 end  -- WATER → FIRE
    return nil
end
