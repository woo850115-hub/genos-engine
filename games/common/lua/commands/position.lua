-- position.lua — rest, sit, stand, sleep, wake

register_command("rest", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_RESTING then
        ctx:send("이미 쉬고 있습니다.")
        return
    end
    if ch.fighting then
        ctx:send("전투 중에는 쉴 수 없습니다!")
        return
    end
    ch.position = POS_RESTING
    ctx:send("쉬기 시작합니다.")
end, "쉬")

register_command("sit", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_SITTING then
        ctx:send("이미 앉아 있습니다.")
        return
    end
    if ch.fighting then
        ctx:send("전투 중에는 앉을 수 없습니다!")
        return
    end
    ch.position = POS_SITTING
    ctx:send("앉았습니다.")
end, "앉")

register_command("stand", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_STANDING then
        ctx:send("이미 서 있습니다.")
        return
    end
    ch.position = POS_STANDING
    ctx:send("일어섰습니다.")
end, "서")

register_command("sleep", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_SLEEPING then
        ctx:send("이미 잠들어 있습니다.")
        return
    end
    if ch.fighting then
        ctx:send("전투 중에는 잠들 수 없습니다!")
        return
    end
    ch.position = POS_SLEEPING
    ctx:send("잠들기 시작합니다.")
end, "자")

register_command("wake", function(ctx, args)
    local ch = ctx.char
    if not ch then return end
    if ch.position == POS_STANDING then
        ctx:send("이미 서 있습니다.")
        return
    end
    ch.position = POS_STANDING
    ctx:send("일어섰습니다.")
end)
