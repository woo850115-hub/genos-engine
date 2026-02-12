-- stealth.lua — tbaMUD stealth commands: sneak, hide

local function do_sneak(ctx, args)
    local char = ctx.char
    if not char then return end

    if char.class_id ~= 2 then
        ctx:send("{red}은밀이동은 도적만 사용할 수 있습니다.{reset}")
        return
    end

    -- Toggle sneak affect
    if ctx:has_affect(char, 1001) then
        ctx:remove_affect(char, 1001)
        ctx:send("은밀이동을 중단합니다.")
        return
    end

    local skill = ctx:random(1, 101)
    local chance = math.min(90, char.player_level * 3 + 15)

    if skill > chance then
        ctx:send("{yellow}은밀하게 움직이려 했지만 실패했습니다.{reset}")
        return
    end

    ctx:apply_affect(char, 1001, char.player_level * 2)
    ctx:send("{cyan}조용히 움직이기 시작합니다...{reset}")
end

register_command("sneak", do_sneak, "은밀")

local function do_hide(ctx, args)
    local char = ctx.char
    if not char then return end

    if char.class_id ~= 2 then
        ctx:send("{red}숨기는 도적만 사용할 수 있습니다.{reset}")
        return
    end

    if char.fighting then
        ctx:send("{red}전투 중에는 숨을 수 없습니다!{reset}")
        return
    end

    -- Toggle hide affect
    if ctx:has_affect(char, 1002) then
        ctx:remove_affect(char, 1002)
        ctx:send("숨기를 중단합니다.")
        return
    end

    local skill = ctx:random(1, 101)
    local chance = math.min(85, char.player_level * 3 + 10)

    if skill > chance then
        ctx:send("{yellow}숨으려 했지만 실패했습니다.{reset}")
        return
    end

    ctx:apply_affect(char, 1002, char.player_level)
    ctx:send("{cyan}주변의 그림자 속에 몸을 숨깁니다...{reset}")
end

register_command("hide", do_hide, "숨기")

-- ── pick (Thief, class_id=2) — pick locks ────────────────────────

local function do_pick(ctx, args)
    local char = ctx.char
    if not char then return end

    if char.class_id ~= 2 then
        ctx:send("{red}자물쇠 따기는 도적만 사용할 수 있습니다.{reset}")
        return
    end

    if not args or args == "" then
        ctx:send("어떤 문의 자물쇠를 따시겠습니까?")
        return
    end

    local dir = ctx:find_door(args)
    if dir < 0 then
        ctx:send("그런 방향의 문을 찾을 수 없습니다.")
        return
    end

    if not ctx:has_door(dir) then
        ctx:send("그쪽에는 문이 없습니다.")
        return
    end

    if not ctx:is_door_locked(dir) then
        ctx:send("그 문은 잠겨있지 않습니다.")
        return
    end

    local skill = ctx:random(1, 101)
    local chance = math.min(90, char.player_level * 3 + 15)

    if skill > chance then
        ctx:send("{yellow}자물쇠를 따는 데 실패했습니다.{reset}")
        return
    end

    ctx:set_door_state(dir, true, false)  -- closed but unlocked
    ctx:send("{green}자물쇠를 성공적으로 땄습니다!{reset}")
    ctx:send_room(char.name .. "이(가) 자물쇠를 따고 있습니다.")
end

register_command("pick", do_pick, "따기")

-- ── steal (Thief, class_id=2) — steal from NPC ──────────────────

local function do_steal(ctx, args)
    local char = ctx.char
    if not char then return end

    if char.class_id ~= 2 then
        ctx:send("{red}훔치기는 도적만 사용할 수 있습니다.{reset}")
        return
    end

    if not args or args == "" then
        ctx:send("사용법: steal <아이템/gold> <대상>")
        return
    end

    local parts = split(args)
    if #parts < 2 then
        ctx:send("사용법: steal <아이템/gold> <대상>")
        return
    end

    local what = parts[1]:lower()
    local target_name = parts[2]
    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end

    if not target.is_npc then
        ctx:send("다른 플레이어에게서 훔칠 수 없습니다.")
        return
    end

    local skill = ctx:random(1, 101)
    local chance = math.min(85, char.player_level * 3 + 10)

    if skill > chance then
        -- Caught!
        ctx:send("{red}훔치려다 들켰습니다!{reset}")
        ctx:send_room(char.name .. "이(가) " .. target.name .. "의 물건을 훔치려다 들킵니다!")
        ctx:start_combat(target)
        return
    end

    if what == "gold" or what == "골드" or what == "coins" then
        local stolen = ctx:random(1, math.max(1, math.floor(target.gold / 4)))
        if target.gold <= 0 then
            ctx:send(target.name .. "은(는) 골드가 없습니다.")
            return
        end
        stolen = math.min(stolen, target.gold)
        target.gold = target.gold - stolen
        char.gold = char.gold + stolen
        ctx:send("{yellow}" .. target.name .. "에게서 " .. stolen .. " 골드를 훔쳤습니다!{reset}")
    else
        -- Steal an item
        local inv = ctx:get_char_inventory(target)
        for i = 1, #inv do
            local obj = inv[i]
            if obj.proto.keywords:lower():find(what, 1, true) then
                ctx:obj_from_char(obj)
                ctx:obj_to_char(obj, char)
                ctx:send("{yellow}" .. target.name .. "에게서 " .. obj.name .. "을(를) 훔쳤습니다!{reset}")
                return
            end
        end
        ctx:send(target.name .. "에게는 그런 것이 없습니다.")
    end
end

register_command("steal", do_steal, "훔치")
