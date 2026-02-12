-- lib.lua — shared utility functions for all Lua commands
-- Loaded before any command scripts, provides common helpers.

-- Direction constants
DIR_NORTH = 0
DIR_EAST = 1
DIR_SOUTH = 2
DIR_WEST = 3
DIR_UP = 4
DIR_DOWN = 5

DIR_NAMES = {"북", "동", "남", "서", "위", "아래"}

-- Position constants
POS_DEAD = 0
POS_MORTALLYW = 1
POS_INCAP = 2
POS_STUNNED = 3
POS_SLEEPING = 4
POS_RESTING = 5
POS_SITTING = 6
POS_FIGHTING = 7
POS_STANDING = 8

-- Check if character can act (not sleeping/stunned/etc)
function can_act(ctx)
    local ch = ctx.char
    if not ch then return false end
    if ch.position <= POS_SLEEPING then
        ctx:send("잠들어 있습니다. 먼저 일어나세요.")
        return false
    end
    return true
end

-- Check if character is standing
function is_standing(ctx)
    local ch = ctx.char
    if not ch then return false end
    return ch.position >= POS_STANDING
end

-- Format a number with commas (e.g. 1234567 -> "1,234,567")
function format_number(n)
    local s = tostring(n)
    local len = #s
    if len <= 3 then return s end
    local parts = {}
    local i = len
    while i > 0 do
        local start = math.max(1, i - 2)
        table.insert(parts, 1, s:sub(start, i))
        i = start - 1
    end
    return table.concat(parts, ",")
end

-- Split a string by whitespace
function split(str)
    local parts = {}
    for word in str:gmatch("%S+") do
        table.insert(parts, word)
    end
    return parts
end

-- String trim
function trim(s)
    return s:match("^%s*(.-)%s*$")
end
