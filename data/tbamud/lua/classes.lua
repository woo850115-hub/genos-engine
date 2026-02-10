-- GenOS Character Classes
-- Auto-generated from UIR

local Classes = {}

Classes[0] = {
    name = "Magic User",
    abbrev = "Mu",
    base_thac0 = 20,
    thac0_gain = 0.66,
    hp_gain = { 3, 8 },
    mana_gain = { 5, 10 },
    move_gain = { 0, 0 },
}

Classes[1] = {
    name = "Cleric",
    abbrev = "Cl",
    base_thac0 = 20,
    thac0_gain = 0.66,
    hp_gain = { 5, 10 },
    mana_gain = { 3, 8 },
    move_gain = { 0, 0 },
}

Classes[2] = {
    name = "Thief",
    abbrev = "Th",
    base_thac0 = 20,
    thac0_gain = 0.75,
    hp_gain = { 6, 11 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[3] = {
    name = "Warrior",
    abbrev = "Wa",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 10, 15 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

-- Level up a character
function Classes.level_up(character)
    local cls = Classes[character.class_id]
    if not cls then return end

    character.level = character.level + 1
    local hp_gain = math.random(cls.hp_gain[1], cls.hp_gain[2])
    local mana_gain = math.random(cls.mana_gain[1], cls.mana_gain[2])
    local move_gain = math.random(cls.move_gain[1], cls.move_gain[2])

    character.max_hp = character.max_hp + hp_gain
    character.max_mana = character.max_mana + mana_gain
    character.max_move = character.max_move + move_gain

    return hp_gain, mana_gain, move_gain
end

return Classes
