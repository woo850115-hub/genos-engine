-- death.lua — experience gain calculation
-- Actual death handling (respawn, items, gold) is in Python via ctx:defer_death()

function calculate_exp_gain(killer, victim)
    local base = 0
    if victim.proto then
        base = victim.proto.experience or 0
    end
    if base <= 0 then
        base = victim.level * victim.level * 10
    end

    local diff = victim.level - killer.level
    local modifier
    if diff >= 5 then
        modifier = 1.5
    elseif diff >= 2 then
        modifier = 1.2
    elseif diff >= -2 then
        modifier = 1.0
    elseif diff >= -5 then
        modifier = 0.5
    else
        modifier = 0.1
    end

    return math.max(1, math.floor(base * modifier))
end
