-- level.lua — 10woongi experience and level tables
-- Level formulas exposed as globals for use by other Lua scripts

-- Exp needed for next level: level^2 * 100 + level * 500
function woongi_exp_to_next(level)
    return level * level * 100 + level * 500
end

-- HP gain per level by class
-- class_id → {min, max} dice roll for HP gain
WOONGI_HP_GAINS = {
    [1]  = {6,  26},   -- 투사
    [2]  = {10, 30},   -- 전사
    [3]  = {12, 32},   -- 기사
    [4]  = {10, 40},   -- 상급기사
    [5]  = {12, 32},   -- 신관기사
    [6]  = {6,  26},   -- 사제
    [7]  = {10, 30},   -- 성직자
    [8]  = {12, 52},   -- 아바타
    [9]  = {6,  26},   -- 도둑
    [10] = {10, 30},   -- 사냥꾼
    [11] = {10, 40},   -- 암살자
    [12] = {6,  26},   -- 마술사
    [13] = {10, 30},   -- 마법사
    [14] = {12, 52},   -- 시공술사
}
