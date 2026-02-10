-- GenOS Combat System
-- Auto-generated from UIR

local Combat = {}

Combat.ATTACK_TYPES = {
    [0] = "hit",
    [1] = "sting",
    [2] = "whip",
    [3] = "slash",
    [4] = "bite",
    [5] = "bludgeon",
    [6] = "crush",
    [7] = "pound",
    [8] = "claw",
    [9] = "maul",
    [10] = "thrash",
    [11] = "pierce",
    [12] = "blast",
    [13] = "punch",
    [14] = "stab",
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
        [0] = { base = 20, gain = 0.66 },  -- Magic User
        [1] = { base = 20, gain = 0.66 },  -- Cleric
        [2] = { base = 20, gain = 0.75 },  -- Thief
        [3] = { base = 20, gain = 1.0 },  -- Warrior
    }
    local entry = thac0_table[class_id]
    if not entry then return 20 end
    return math.max(1, math.floor(entry.base - (level * entry.gain)))
end

return Combat
