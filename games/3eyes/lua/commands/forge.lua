-- forge.lua — 3eyes forging system
-- Original: command7.c forge (380-420)
-- RFORGE room required, LT_FORGE 60s cooldown

-- ══════════════════════════════════════════════════════════════════
-- 제련 (command7.c forge)
-- Success/fail/destroy based on level + class + item adjustment
-- ══════════════════════════════════════════════════════════════════

local LT_FORGE = 31

register_command("제련", function(ctx, args)
    -- RFORGE room check
    if not te_room_has_flag(ctx, 10) then  -- RFORGE
        ctx:send("{yellow}제련소에서만 제련할 수 있습니다.{reset}")
        return
    end

    if not args or args == "" then
        ctx:send("사용법: forge <아이템>")
        return
    end

    local ch = ctx.char
    local cd = ctx:check_cooldown(LT_FORGE)
    if cd > 0 then
        ctx:send("{yellow}아직 제련할 수 없습니다. (" .. cd .. "초){reset}")
        return
    end

    -- Find item in inventory or equipment
    local item = ctx:find_inv_item(args)
    if not item then
        item = ctx:find_equip_item(args)
    end
    if not item or not item.proto then
        ctx:send("그런 아이템을 가지고 있지 않습니다.")
        return
    end

    -- Check if forgeable (weapon or armor only)
    local ok_type, item_type = pcall(function() return item.proto.item_type end)
    local is_forgeable = false
    if ok_type and item_type then
        if item_type == "weapon" or item_type == "armor" then
            is_forgeable = true
        end
    end
    -- Also check wear_slots for weapon/armor detection
    if not is_forgeable then
        local ok_ws, ws = pcall(function() return item.proto.wear_slots end)
        if ok_ws and ws then
            for _, s in ipairs(ws) do
                if s == 16 or s == "weapon" or s == "wield" or
                   s == "body" or s == "head" or s == "legs" or
                   s == "feet" or s == "arms" or s == "shield" then
                    is_forgeable = true
                    break
                end
            end
        end
    end

    if not is_forgeable then
        ctx:send("{yellow}무기나 방어구만 제련할 수 있습니다.{reset}")
        return
    end

    -- Current adjustment (enhancement level)
    local ok_adj, adjustment = pcall(function() return item.adjustment or 0 end)
    if not ok_adj then adjustment = 0 end

    -- Cost: 5000 * (adjustment+1)^2 gold (command7.c:395)
    local cost = 5000 * (adjustment + 1) * (adjustment + 1)
    if ch.gold < cost then
        ctx:send("{yellow}제련 비용이 부족합니다. (필요: " .. cost .. "원, 소지금: " .. ch.gold .. "원){reset}")
        return
    end

    -- Success chance: base 80% - adjustment*10 + comp_chance/4
    -- Higher enhancement = lower chance
    local base_chance = 80 - adjustment * 10 + math.floor(te_comp_chance(ch) / 4)
    base_chance = math.max(5, math.min(95, base_chance))

    ch.gold = ch.gold - cost
    ctx:set_cooldown(LT_FORGE, 60)

    local roll = te_mrand(1, 100)

    if roll <= base_chance then
        -- Success: +1 adjustment
        pcall(function() item.adjustment = adjustment + 1 end)
        ctx:send("{bright_green}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
        ctx:send("{bright_green}  제련 성공!{reset}")
        ctx:send("{bright_green}  " .. item.name .. " → +" .. (adjustment + 1) .. "{reset}")
        ctx:send("{bright_green}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
        ctx:send_room(ch.name .. "이(가) " .. item.name .. "을(를) 제련에 성공합니다!")
    elseif roll <= base_chance + math.floor((100 - base_chance) / 2) then
        -- Failure: no change
        ctx:send("{yellow}제련 실패! 아이템에 변화가 없습니다.{reset}")
        ctx:send_room(ch.name .. "이(가) 제련에 실패합니다.")
    else
        -- Destruction: adjustment reduced by 1 (or destroyed if +0)
        if adjustment <= 0 then
            -- Destroy the item
            ctx:obj_from_char(item)
            ctx:send("{bright_red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
            ctx:send("{bright_red}  제련 대실패! " .. item.name .. "이(가) 부서졌습니다!{reset}")
            ctx:send("{bright_red}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
            ctx:send_room(ch.name .. "의 " .. item.name .. "이(가) 제련 중 부서집니다!")
        else
            pcall(function() item.adjustment = adjustment - 1 end)
            ctx:send("{red}제련 대실패! " .. item.name ..
                "의 강화가 +" .. adjustment .. " → +" .. (adjustment - 1) .. "로 하락했습니다!{reset}")
            ctx:send_room(ch.name .. "이(가) 제련에 대실패합니다!")
        end
    end
end)

-- ── 무기만들기 — 제련 별칭 ───────────────────────────────────────
register_command("무기만들기", function(ctx, args) ctx:call_command("제련", args or "") end)
