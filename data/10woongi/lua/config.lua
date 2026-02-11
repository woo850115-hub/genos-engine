-- GenOS Game Configuration
-- Auto-generated from UIR

local Config = {}

Config.armor_slot = {
    HELMET = 1,
    EARRING = 2,
    PENDANT = 3,
    BODY_ARMOR = 4,
    BELT = 5,
    ARM_ARMOR = 6,
    GAUNTLET = 7,
    ARMLET = 8,
    RING = 9,
    LEG_ARMOR = 10,
    SHOES = 11,
    EARRING2 = 12,
    RING2 = 13,
    RING3 = 14,
    RING4 = 15,
    RING5 = 16,
    RING6 = 17,
    RING7 = 18,
    RING8 = 19,
    RING9 = 20,
    RING10 = 21,
    ARMLET2 = 22,
    MAX_ARMOR_NUM = 22,
}

Config.critical_type = {
    HIT_SELF = 1,
    HIT_GROUP = 2,
    DROP_WEAPON = 3,
    BREAK_WEAPON = 4,
    BREAK_ARMOR = 5,
    STUN = 6,
    DAMAGE_X = 7,
    KILL = 8,
}

Config.damage_type = {
    NONE = 0,
    PIECING = 1,
    SLASH = 2,
    BLUDGE = 3,
    SHOOT = 4,
}

Config.formula = {
    sigma_formula = "sum(1..n-1), cap at 150 then linear: sigma(150)+((n-150)*150)",
    hp_formula = "hp = 80 + 6 * (sigma(기골) / 30); defense_type: x2, attack_type: x4",
    sp_formula = "sp = 80 + ((sigma(내공)*2 + sigma(지혜)) / 30)",
    mp_formula = "mp = 50 + (sigma(민첩) / 15)",
    random_stat_formula = "stat = (level - level/10) + random(level/5); ArmorClass = level/4; WeaponClass = level/4",
    adj_exp_formula = "exp = ((avg_stat^2) / 12) * adjust",
    heal_rates_normal = "hp: 8%, sp: 9%, mp: 13% per tick",
    heal_rates_fast = "hp: 16%, sp: 18%, mp: 26% per tick",
}

Config.game = {
    LOGIN_DAEMON = "/로긴",
    SEFUN_OB = "/가상함수",
    VOID_OB = "허공",
    YEAR_TIME = 86400,
    name = "십웅기",
    ["address server ip"] = "localhost",
    ["include directories"] = "/삽입파일",
    ["time to clean up"] = 300,
    ["time to swap"] = 900,
    ["time to reset"] = 900,
    ["default fail message"] = "·잘못된 명령입니다·",
    ["default error message"] = "에러입니다.",
}

Config.limits = {
    ["maximum users"] = 50,
    ["maximum bits in a bitfield"] = 1200,
    ["maximum local variables"] = 50,
    ["maximum evaluation cost"] = 1000000,
    ["maximum array size"] = 15000,
    ["maximum buffer size"] = 1000000,
    ["maximum mapping size"] = 30000,
    ["inherit chain size"] = 30,
    ["maximum string length"] = 200000,
    ["maximum read file size"] = 200000,
    ["maximum byte transfer"] = 200000,
    ["reserved size"] = 0,
    ["hash table size"] = 29999,
    ["object table size"] = 1501,
    ["maximum users"] = 50,
    ["evaluator stack size"] = 10000,
    ["compiler stack size"] = 200,
    ["maximum call depth"] = 30,
    ["living hash table size"] = 100,
}

Config.paths = {
    ["mudlib directory"] = "../lib",
    ["binary directory"] = "./",
    ["log directory"] = "/기록",
    ["save binaries directory"] = "/이진저장",
    ["master file"] = "/관리자/마스터",
    ["simulated efun file"] = "/관리자/가상함수",
    ["swap file"] = "/관리자/저장/스왑",
    ["debug log file"] = "디버그",
    ["global include file"] = "\"/삽입파일/전역.h\"",
}

Config.port = {
    ["address server port"] = 2994,
    external_port_1 = "telnet 9999",
}

Config.room = {
    START_ROOM = "장백성/마을광장",
    NOVICE_ROOM = "초보지역/선택의방",
    FREEZER_ROOM = "냉동실",
    REVITAL_ROOM = "파르티타/병원",
}

Config.unbalanced_type = {
    SHIELD_UNBALANCED = 1,
    PARRY_UNBALANCED = 2,
    TWO_HAND_UNBALANCED = 3,
}

Config.weapon_size = {
    TINY = 1,
    SMALL = 2,
    MEDIUM = 3,
    LARGE = 4,
    HUGE = 5,
}

return Config
