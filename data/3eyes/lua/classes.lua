-- GenOS Character Classes
-- Auto-generated from UIR

local Classes = {}

Classes[1] = {
    name = "Assassin",
    abbrev = "As",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 8, 12 },
    mana_gain = { 2, 6 },
    move_gain = { 0, 0 },
}

Classes[2] = {
    name = "Barbarian",
    abbrev = "Ba",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 12, 18 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[3] = {
    name = "Cleric",
    abbrev = "Cl",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 6, 10 },
    mana_gain = { 4, 8 },
    move_gain = { 0, 0 },
}

Classes[4] = {
    name = "Fighter",
    abbrev = "Fi",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 10, 15 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[5] = {
    name = "Mage",
    abbrev = "Ma",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 4, 8 },
    mana_gain = { 6, 12 },
    move_gain = { 0, 0 },
}

Classes[6] = {
    name = "Paladin",
    abbrev = "Pa",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 8, 14 },
    mana_gain = { 2, 6 },
    move_gain = { 0, 0 },
}

Classes[7] = {
    name = "Ranger",
    abbrev = "Ra",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 9, 14 },
    mana_gain = { 1, 4 },
    move_gain = { 0, 0 },
}

Classes[8] = {
    name = "Thief",
    abbrev = "Th",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 7, 11 },
    mana_gain = { 1, 3 },
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
