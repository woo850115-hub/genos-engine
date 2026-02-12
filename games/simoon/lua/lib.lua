-- lib.lua — Simoon utility functions

-- Simoon class names (Korean)
SIMOON_CLASSES = {
    [0] = "마법사",
    [1] = "성직자",
    [2] = "도적",
    [3] = "전사",
    [4] = "흑마법사",
    [5] = "버서커",
    [6] = "소환사",
}

SIMOON_RACES = {
    [0] = "인간",
    [1] = "드워프",
    [2] = "엘프",
    [3] = "호빗",
    [4] = "하프엘프",
}

-- Caster classes (get mana combat bonus)
SIMOON_CASTER = {[0]=true, [1]=true, [4]=true, [6]=true}

-- Get stat value safely
function simoon_stat(mob, key, default)
    default = default or 13
    local ok, val = pcall(function() return mob.stats[key] end)
    if ok and val then return val end
    return default
end
