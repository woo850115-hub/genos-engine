-- GenOS Combat System
-- Auto-generated from UIR

local Combat = {}

Combat.ATTACK_TYPES = {
    [0] = "slash",
    [1] = "pierce",
    [2] = "bludgeon",
    [3] = "shoot",
}

-- Calculate hit roll (THAC0 system)
-- thac0: attacker's THAC0 value
-- ac: defender's armor class
-- hitroll: attacker's hitroll bonus
function Combat.calculate_hit(thac0, ac, hitroll)
    local roll = math.random(1, 20)
    local needed = thac0 - ac - hitroll
    return roll >= needed, roll
end

-- Calculate damage
-- dice_num: number of dice
-- dice_size: size of each die
-- bonus: flat bonus
function Combat.roll_damage(dice_num, dice_size, bonus)
    local total = bonus
    for i = 1, dice_num do
        total = total + math.random(1, dice_size)
    end
    return math.max(1, total)
end

-- Get THAC0 for class and level
function Combat.get_thac0(class_id, level)
    local thac0_table = {
        [1] = { base = 20, gain = 1.0 },  -- 투사
        [2] = { base = 20, gain = 1.0 },  -- 전사
        [3] = { base = 20, gain = 1.0 },  -- 기사
        [4] = { base = 20, gain = 1.0 },  -- 상급기사
        [5] = { base = 20, gain = 1.0 },  -- 신관기사
        [6] = { base = 20, gain = 1.0 },  -- 사제
        [7] = { base = 20, gain = 1.0 },  -- 성직자
        [8] = { base = 20, gain = 1.0 },  -- 아바타
        [9] = { base = 20, gain = 1.0 },  -- 도둑
        [10] = { base = 20, gain = 1.0 },  -- 사냥꾼
        [11] = { base = 20, gain = 1.0 },  -- 암살자
        [12] = { base = 20, gain = 1.0 },  -- 마술사
        [13] = { base = 20, gain = 1.0 },  -- 마법사
        [14] = { base = 20, gain = 1.0 },  -- 시공술사
    }
    local entry = thac0_table[class_id]
    if not entry then return 20 end
    return math.max(1, math.floor(entry.base - (level * entry.gain)))
end

return Combat
