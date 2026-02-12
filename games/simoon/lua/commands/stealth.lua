-- stealth.lua — Simoon thief/stealth commands (sneak, hide, pick, steal)

register_command("sneak", function(ctx, args)
    local ch = ctx.char
    if ch.class_id ~= 2 and ch.class_id ~= 4 then
        ctx:send("도적이나 흑마법사만 숨어 다닐 수 있습니다.")
        return
    end
    if ctx:has_affect(ch, 1001) then
        ctx:remove_affect(ch, 1001)
        ctx:send("더 이상 소리를 죽이지 않습니다.")
        return
    end
    local dex = simoon_stat(ch, "dex", 13)
    local chance = 30 + dex * 2 + ch.level
    if math.random(1, 100) <= chance then
        ctx:apply_affect(ch, 1001, 3 + math.floor(ch.level / 5))
        ctx:send("소리를 죽이며 움직입니다.")
    else
        ctx:send("발걸음 소리를 줄이지 못했습니다.")
    end
end, "숨어가")

register_command("hide", function(ctx, args)
    local ch = ctx.char
    if ch.class_id ~= 2 and ch.class_id ~= 4 then
        ctx:send("도적이나 흑마법사만 숨을 수 있습니다.")
        return
    end
    if ctx:has_affect(ch, 1002) then
        ctx:remove_affect(ch, 1002)
        ctx:send("모습을 드러냅니다.")
        return
    end
    local dex = simoon_stat(ch, "dex", 13)
    local chance = 25 + dex * 2 + ch.level
    if math.random(1, 100) <= chance then
        ctx:apply_affect(ch, 1002, 3 + math.floor(ch.level / 5))
        ctx:send("어둠 속에 모습을 감춥니다.")
    else
        ctx:send("숨을 수 있는 곳을 찾지 못했습니다.")
    end
end, "숨")

register_command("pick", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 따시겠습니까?")
        return
    end
    local ch = ctx.char
    if ch.class_id ~= 2 then
        ctx:send("도적만 잠금장치를 딸 수 있습니다.")
        return
    end
    local dex = simoon_stat(ch, "dex", 13)
    local chance = 20 + dex * 3 + ch.level
    if math.random(1, 100) <= chance then
        ctx:pick_lock(args)
        ctx:send("잠금장치를 땄습니다!")
    else
        ctx:send("잠금장치를 따는 데 실패했습니다.")
    end
end, "따")

register_command("steal", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구에게서 무엇을 훔치시겠습니까?")
        return
    end
    local ch = ctx.char
    if ch.class_id ~= 2 then
        ctx:send("도적만 물건을 훔칠 수 있습니다.")
        return
    end
    local item_name, target_name = args:match("^(%S+)%s+(.+)$")
    if not item_name or not target_name then
        ctx:send("사용법: steal <물건> <대상>")
        return
    end
    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end
    if not target.is_npc then
        ctx:send("다른 플레이어에게서는 훔칠 수 없습니다.")
        return
    end
    local dex = simoon_stat(ch, "dex", 13)
    local chance = 15 + dex * 2 + ch.level - target.level * 2
    if math.random(1, 100) <= chance then
        local stolen = ctx:steal_item(target, item_name)
        if stolen then
            ctx:send("{green}" .. stolen.name .. "을(를) 훔쳤습니다!{reset}")
        else
            ctx:send("그런 물건을 가지고 있지 않습니다.")
        end
    else
        ctx:send("실패! " .. target.name .. "이(가) 당신을 발견했습니다!")
        ctx:start_combat(target)
    end
end, "훔치")

register_command("backstab", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 기습하시겠습니까?")
        return
    end
    local ch = ctx.char
    if ch.class_id ~= 2 then
        ctx:send("도적만 기습할 수 있습니다.")
        return
    end
    if ch.fighting then
        ctx:send("전투 중에는 기습할 수 없습니다!")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 대상을 찾을 수 없습니다.")
        return
    end
    if target == ch then
        ctx:send("자기 자신을 기습할 수 없습니다!")
        return
    end
    if target.fighting then
        ctx:send("전투 중인 대상은 기습할 수 없습니다!")
        return
    end

    local dex = simoon_stat(ch, "dex", 13)
    local chance = 20 + dex * 2 + ch.level - target.level
    if math.random(1, 100) <= chance then
        local dmg = math.max(1, ch.level * 2 + dex)
        target.hp = target.hp - dmg
        ctx:send("{bright_red}" .. target.name .. "을(를) 기습합니다! [" .. dmg .. "]{reset}")
        ctx:start_combat(target)
        if target.hp <= 0 then
            ctx:stop_combat(ch)
            ctx:defer_death(target, ch)
        end
    else
        ctx:send("기습에 실패했습니다!")
        ctx:start_combat(target)
    end
end, "기습")
