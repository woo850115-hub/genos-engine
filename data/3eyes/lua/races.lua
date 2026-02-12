-- GenOS Races Data
-- Auto-generated from UIR

local Races = {}

Races[1] = {
    name = "Dwarf",
    abbrev = "Dw",
    stat_mods = {constitution=1, intelligence=-1, strength=2},
    allowed_classes = {1,2,3,4,5,6,7,8},
}

Races[2] = {
    name = "Elf",
    abbrev = "El",
    stat_mods = {constitution=-1, dexterity=2, intelligence=1},
    allowed_classes = {1,2,3,4,5,6,7,8},
}

Races[3] = {
    name = "Half-Elf",
    abbrev = "He",
    stat_mods = {dexterity=1, intelligence=1},
    allowed_classes = {1,2,3,4,5,6,7,8},
}

Races[4] = {
    name = "Hobbit",
    abbrev = "Ho",
    stat_mods = {dexterity=2, strength=-1},
    allowed_classes = {1,2,3,4,5,6,7,8},
}

Races[5] = {
    name = "Human",
    abbrev = "Hu",
    allowed_classes = {1,2,3,4,5,6,7,8},
}

Races[6] = {
    name = "Orc",
    abbrev = "Or",
    stat_mods = {constitution=1, intelligence=-2, strength=2},
    allowed_classes = {1,2,3,4,5,6,7,8},
}

Races[7] = {
    name = "Half-Giant",
    abbrev = "Hg",
    stat_mods = {constitution=2, dexterity=-1, intelligence=-2, strength=3},
    allowed_classes = {1,2,3,4,5,6,7,8},
}

Races[8] = {
    name = "Gnome",
    abbrev = "Gn",
    stat_mods = {dexterity=1, intelligence=2, strength=-1},
    allowed_classes = {1,2,3,4,5,6,7,8},
}

return Races
