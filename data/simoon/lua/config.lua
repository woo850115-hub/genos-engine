-- GenOS Game Configuration
-- Auto-generated from UIR

local Config = {}

Config.corpse = {
    max_npc_corpse_time = 5,
    max_pc_corpse_time = 10,
}

Config.economy = {
    max_exp_gain = 2100000000,
    max_exp_loss = 50,
}

Config.game = {
    pk_allowed = false,
    summon_allowed = true,
    charm_allowed = true,
    sleep_allowed = true,
    roomaffect_allowed = true,
    czon_flag = 0,
    pt_allowed = false,
    level_can_shout = 1,
    holler_move_cost = 80,
    lastnedcfg = 0,
    dts_are_dumps = true,
    jailed_start_room = 0,
    MAX_PLAYERS = 100,
    max_filesize = 50000,
    max_bad_pws = 5,
    nameserver_is_slow = true,
    use_autowiz = true,
    min_wizlist_lev = 32,
}

Config.port = {
    DFLT_PORT = 8130,
}

Config.rent = {
    free_rent = true,
    max_obj_save = 30,
    min_rent_cost = 100,
    auto_save = true,
    autosave_time = 5,
    crash_file_timeout = 10,
    rent_file_timeout = 30,
}

Config.room = {
    mortal_start_room = 3093,
    immort_start_room = 700,
    frozen_start_room = 1202,
    donation_room_1 = 3063,
    donation_room_2 = -1,
    donation_room_3 = -1,
}

return Config
