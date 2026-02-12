-- GenOS Races Data
-- Auto-generated from UIR

local Races = {}

Races[0] = {
    name = "Human",
    abbrev = "Hu",
    stat_mods = {charisma=3},
    allowed_classes = {0,1,2,3,4,5,6},
    korean_name = "인간",
}

Races[1] = {
    name = "Dwarf",
    abbrev = "Dw",
    stat_mods = {constitution=1, dexterity=-1, strength=2},
    allowed_classes = {1,2,3,5},
    korean_name = "드워프",
}

Races[2] = {
    name = "Elf",
    abbrev = "El",
    stat_mods = {charisma=3, dexterity=2, intelligence=2, strength=-1},
    allowed_classes = {0,1,2,4,6},
    korean_name = "엘프",
}

Races[3] = {
    name = "Hobbit",
    abbrev = "Ho",
    stat_mods = {dexterity=1, strength=-1},
    allowed_classes = {1,2,3},
    korean_name = "호빗",
}

Races[4] = {
    name = "Half-Elf",
    abbrev = "He",
    allowed_classes = {0,1,2,3,4,5,6},
    korean_name = "하프엘프",
}

return Races
