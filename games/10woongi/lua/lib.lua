-- lib.lua — 10woongi shared utilities (wuxia stats, constants)

-- ── 22 Equipment Slots ─────────────────────────────────────────
WEAR_SLOTS = {
    [1]="투구", [2]="귀걸이1", [3]="목걸이", [4]="갑옷",
    [5]="허리띠", [6]="팔갑", [7]="장갑", [8]="팔찌1",
    [9]="반지1", [10]="각반", [11]="신발", [12]="귀걸이2",
    [13]="반지2", [14]="반지3", [15]="반지4", [16]="반지5",
    [17]="반지6", [18]="반지7", [19]="반지8", [20]="반지9",
    [21]="반지10", [22]="팔찌2",
}

NUM_WEAR_SLOTS = 22

-- ── 6 Wuxia Stat Names ────────────────────────────────────────
STAT_NAMES = {"체력", "민첩", "지혜", "기골", "내공", "투지"}
STAT_KEYS  = {"stamina", "agility", "wisdom", "bone", "inner", "spirit"}
STAT_DEFAULT = 13

-- ── 14 Classes + Promotion Chains ─────────────────────────────
CLASS_NAMES = {
    [1]="투사", [2]="전사", [3]="기사", [4]="상급기사",
    [5]="신관기사", [6]="사제", [7]="성직자", [8]="아바타",
    [9]="도둑", [10]="사냥꾼", [11]="암살자",
    [12]="마술사", [13]="마법사", [14]="시공술사",
}

PROMOTION_CHAIN = {
    [1]={30, 2},  [2]={60, 3},   [3]={100, 4},
    [6]={30, 7},  [7]={60, 8},
    [9]={30, 10}, [10]={60, 11},
    [12]={30, 13},[13]={60, 14},
}

-- ── Key Rooms ──────────────────────────────────────────────────
WOONGI_START_ROOM = 1392841419
WOONGI_VOID_ROOM  = 1854941986

-- ── History origins ────────────────────────────────────────────
HISTORY_NAMES = {
    [0]="없음", [1]="철방", [2]="무영루", [3]="성유림", [4]="비검산장",
    [5]="환마궁", [6]="천하제일상회", [7]="객잔", [8]="도적소굴",
    [9]="사막오아시스", [10]="은둔촌",
}

-- ── Sigma formula ──────────────────────────────────────────────
function sigma(n)
    if n <= 0 then return 0 end
    if n == 1 then return 0 end
    if n <= 150 then
        return math.floor((n - 1) * n / 2)
    end
    return 11175 + (n - 150) * 150
end

function calc_hp(bone)
    return 80 + math.floor(6 * sigma(bone) / 30)
end

function calc_sp(inner, wisdom)
    return 80 + math.floor((sigma(inner) * 2 + sigma(wisdom)) / 30)
end

function calc_mp(agility)
    return 50 + math.floor(sigma(agility) / 15)
end

function calc_adj_exp(level)
    return level * level * 10 + level * 50
end

-- ── Get wuxia stats from character extensions ──────────────────
function get_wuxia_stats(char)
    local ext = char.extensions
    if not ext then
        return {stamina=13, agility=13, wisdom=13, bone=13, inner=13, spirit=13}
    end
    local ok, stats = pcall(function() return ext.stats end)
    if not ok or not stats then
        return {stamina=13, agility=13, wisdom=13, bone=13, inner=13, spirit=13}
    end
    local function g(key)
        local ok2, v = pcall(function() return stats[key] end)
        return (ok2 and v) and tonumber(v) or 13
    end
    return {
        stamina = g("stamina"),
        agility = g("agility"),
        wisdom  = g("wisdom"),
        bone    = g("bone"),
        inner   = g("inner"),
        spirit  = g("spirit"),
    }
end

-- ── Roll dice "NdS+B" ──────────────────────────────────────────
function roll_dice_str(ctx, dice_str)
    if not dice_str or not dice_str:find("d") then
        return tonumber(dice_str) or 0
    end
    local num, rest = dice_str:match("(%d+)d(.+)")
    num = tonumber(num) or 1
    local size, bonus
    if rest:find("+", 1, true) then
        size, bonus = rest:match("(%d+)%+(-?%d+)")
    elseif rest:find("%-") then
        size, bonus = rest:match("(%d+)%-(%d+)")
        if bonus then bonus = "-" .. bonus end
    else
        size = rest
        bonus = "0"
    end
    size = tonumber(size) or 4
    bonus = tonumber(bonus) or 0
    local total = bonus
    for i = 1, num do
        total = total + ctx:random(1, math.max(1, size))
    end
    return math.max(1, total)
end

-- ── Progress bar drawing ───────────────────────────────────────
function draw_graph(current, max_val, width)
    width = width or 10
    if max_val <= 0 then
        local s = ""
        for i = 1, width do s = s .. "░" end
        return s
    end
    local ratio = math.min(current / max_val, 1.0)
    local filled = math.floor(ratio * width)
    local s = ""
    for i = 1, filled do s = s .. "█" end
    for i = 1, width - filled do s = s .. "░" end
    return s
end
