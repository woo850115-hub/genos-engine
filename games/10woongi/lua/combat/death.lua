-- death.lua — 10woongi death handling (exp gain calculation)
-- Actual death processing is deferred to Python via ctx:defer_death()

-- Global function used by combat hooks
function woongi_calculate_exp_gain(killer_level, victim_level)
    local base = calc_adj_exp(victim_level)
    local diff = victim_level - killer_level
    local modifier = 1.0
    if diff > 5 then
        modifier = 1.5
    elseif diff > 0 then
        modifier = 1.2
    elseif diff < -10 then
        modifier = 0.1
    elseif diff < -5 then
        modifier = 0.5
    end
    return math.floor(base * modifier)
end
