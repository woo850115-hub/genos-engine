-- lib.lua — 3eyes utility functions

-- 3eyes class names (Korean) — 1-indexed
THREEEYES_CLASSES = {
    [1]="암살자", [2]="야만인", [3]="성직자", [4]="전사",
    [5]="마법사", [6]="팔라딘", [7]="광전사", [8]="도적",
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

-- Stat bonus table (global.c bonus[35])
local STAT_BONUS = {
    [0]=-4,[1]=-4,[2]=-4,[3]=-3,[4]=-3,[5]=-2,[6]=-2,[7]=-1,[8]=-1,[9]=-1,
    [10]=0,[11]=0,[12]=0,[13]=0,[14]=1,[15]=1,[16]=1,[17]=2,[18]=2,[19]=2,
    [20]=3,[21]=3,[22]=3,[23]=3,[24]=4,[25]=4,[26]=4,[27]=4,[28]=4,
    [29]=5,[30]=5,[31]=5,[32]=5,[33]=5,[34]=5,
}

-- Get stat value safely (5 stats: str/dex/con/int/pie)
function te_stat(mob, key, default)
    default = default or 13
    local ok, val = pcall(function() return mob.stats[key] end)
    if ok and val then return val end
    return default
end

-- Get stat bonus from value
function te_bonus(stat_value)
    local v = math.min(math.max(stat_value or 0, 0), 34)
    return STAT_BONUS[v] or 7
end

-- Get proficiency value for a weapon type (0-4) from char ext
function te_proficiency(mob, prof_type)
    local ok, ext = pcall(function() return mob.extensions end)
    if not ok or not ext then return 0 end
    local ok2, prof = pcall(function() return ext.proficiency end)
    if not ok2 or not prof then return 0 end
    local ok3, val = pcall(function() return prof[prof_type] end)
    if ok3 and val then return val end
    return 0
end

-- Get realm value for a realm type (0-3) from char ext
function te_realm(mob, realm_type)
    local ok, ext = pcall(function() return mob.extensions end)
    if not ok or not ext then return 0 end
    local ok2, realm = pcall(function() return ext.realm end)
    if not ok2 or not realm then return 0 end
    local ok3, val = pcall(function() return realm[realm_type] end)
    if ok3 and val then return val end
    return 0
end

-- Proficiency percent (0-100): proficiency / 20
function te_prof_percent(mob, prof_type)
    local raw = te_proficiency(mob, prof_type)
    return math.min(100, math.floor(raw / 20))
end

-- Realm percent (0-100): realm / 20
function te_realm_percent(mob, realm_type)
    local raw = te_realm(mob, realm_type)
    return math.min(100, math.floor(raw / 20))
end
