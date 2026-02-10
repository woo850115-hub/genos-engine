-- GenOS Game Configuration
-- Auto-generated from UIR

local Config = {}

Config.corpse = {
    max_npc_corpse_time = 5,
    max_pc_corpse_time = 10,
}

Config.economy = {
    max_exp_gain = 100000,
    max_exp_loss = 500000,
}

Config.game = {
    script_players = false,
    level_can_shout = 1,
    holler_move_cost = 20,
    tunnel_size = 2,
    dts_are_dumps = true,
    load_into_inventory = true,
    track_through_doors = true,
    no_mort_to_immort = true,
    diagonal_dirs = false,
    auto_pwipe = false,
    selfdelete_fastwipe = true,
    bitwarning = false,
    bitsavetodisk = true,
    max_filesize = 50000,
    max_bad_pws = 3,
    siteok_everyone = true,
    nameserver_is_slow = false,
    auto_save_olc = true,
    use_new_socials = true,
    use_autowiz = true,
    min_wizlist_lev = 32,
    display_closed_doors = true,
    map_option = 2,
    default_map_size = 6,
    default_minimap_size = 2,
    medit_advanced_stats = true,
    ibt_autosave = true,
    protocol_negotiation = true,
    special_in_comm = true,
    debug_mode = 0,
}

Config.idle = {
    idle_void = 8,
    idle_rent_time = 48,
    idle_max_level = 31,
}

Config.pk = {
    pk_setting = 0,
    pt_setting = 0,
}

Config.port = {
    DFLT_PORT = 4000,
    max_playing = 300,
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
    mortal_start_room = "3001",
    immort_start_room = "1204",
    frozen_start_room = "1202",
    donation_room_1 = "3063",
    donation_room_2 = "5510",
    donation_room_3 = "235",
}

return Config
