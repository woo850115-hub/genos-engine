-- GenOS Character Classes
-- Auto-generated from UIR

local Classes = {}

Classes[1] = {
    name = "투사",
    abbrev = "투사",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 6, 26 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[2] = {
    name = "전사",
    abbrev = "전사",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 10, 30 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[3] = {
    name = "기사",
    abbrev = "기사",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 12, 32 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[4] = {
    name = "상급기사",
    abbrev = "상급",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 10, 40 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[5] = {
    name = "신관기사",
    abbrev = "신관",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 12, 32 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[6] = {
    name = "사제",
    abbrev = "사제",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 6, 26 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[7] = {
    name = "성직자",
    abbrev = "성직",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 10, 30 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[8] = {
    name = "아바타",
    abbrev = "아바",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 12, 52 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[9] = {
    name = "도둑",
    abbrev = "도둑",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 6, 26 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[10] = {
    name = "사냥꾼",
    abbrev = "사냥",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 10, 30 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[11] = {
    name = "암살자",
    abbrev = "암살",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 10, 40 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[12] = {
    name = "마술사",
    abbrev = "마술",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 6, 26 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[13] = {
    name = "마법사",
    abbrev = "마법",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 10, 30 },
    mana_gain = { 0, 0 },
    move_gain = { 0, 0 },
}

Classes[14] = {
    name = "시공술사",
    abbrev = "시공",
    base_thac0 = 20,
    thac0_gain = 1.0,
    hp_gain = { 12, 52 },
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
