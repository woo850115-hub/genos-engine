-- movement.lua — Simoon movement commands (enter, leave, scan, title)

register_command("enter", function(ctx, args)
    if not args or args == "" then
        ctx:send("어디로 들어가시겠습니까?")
        return
    end
    -- Try to find a portal or special exit
    local target = ctx:find_portal(args)
    if target then
        ctx:move_to(target)
        ctx:send("안으로 들어갑니다.")
        ctx:defer_look()
    else
        ctx:send("들어갈 수 있는 곳이 없습니다.")
    end
end, "들어가")

register_command("scan", function(ctx, args)
    local dirs = {"north", "east", "south", "west", "up", "down"}
    local kr_dirs = {"북", "동", "남", "서", "위", "아래"}
    local lines = {"{bright_cyan}-- 주변 탐색 --{reset}"}
    local found = false

    for i, dir in ipairs(dirs) do
        local exit_room = ctx:peek_exit(dir)
        if exit_room then
            local chars = ctx:get_room_chars(exit_room)
            if chars and #chars > 0 then
                lines[#lines + 1] = "  " .. kr_dirs[i] .. "쪽:"
                for _, ch in ipairs(chars) do
                    lines[#lines + 1] = "    " .. ch.name
                end
                found = true
            end
        end
    end

    if not found then
        lines[#lines + 1] = "  주변에 아무도 보이지 않습니다."
    end
    ctx:send(table.concat(lines, "\r\n"))
end, "탐색")

register_command("title", function(ctx, args)
    if not args or args == "" then
        ctx:send("칭호를 입력해주세요.")
        return
    end
    ctx:set_player_data("title", args)
    ctx:send("칭호가 '" .. args .. "'(으)로 설정되었습니다.")
end, "칭호")
