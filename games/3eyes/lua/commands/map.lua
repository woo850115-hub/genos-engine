-- map.lua — 3eyes 지도 명령어 (original: show_map in map.c)
-- "지도" = compass-style adjacent rooms, "지도 전체" = BFS zone overview

-- ── Truncate helper ───────────────────────────────────────────────
local function trunc(name, maxlen)
    if not name or name == "" then return "" end
    maxlen = maxlen or 14
    if #name > maxlen then
        return name:sub(1, maxlen) .. ".."
    end
    return name
end

-- ── BFS zone map (original: "지도 전체" → view_file "전체지도") ───
local function show_full_map(ctx)
    local ch = ctx.char
    if not ch then return end
    local start_vnum = ch.room_vnum
    local start_room = ctx:get_room()
    if not start_room then
        ctx:send("현재 방 정보를 찾을 수 없습니다.")
        return
    end

    -- BFS with depth limit
    local MAX_DEPTH = 7
    local visited = {}
    local queue = {{vnum = start_vnum, depth = 0, x = 0, y = 0}}
    local grid = {}   -- grid[y][x] = room_name
    local min_x, max_x, min_y, max_y = 0, 0, 0, 0
    visited[start_vnum] = true

    local dir_offsets = {
        north = {0, -1}, south = {0, 1},
        east  = {1, 0},  west  = {-1, 0},
    }

    local qi = 1
    while qi <= #queue do
        local cur = queue[qi]
        qi = qi + 1

        -- Record in grid
        if not grid[cur.y] then grid[cur.y] = {} end
        local rname = ctx:get_room_name(cur.vnum) or "?"
        grid[cur.y][cur.x] = trunc(rname, 8)

        if cur.x < min_x then min_x = cur.x end
        if cur.x > max_x then max_x = cur.x end
        if cur.y < min_y then min_y = cur.y end
        if cur.y > max_y then max_y = cur.y end

        if cur.depth < MAX_DEPTH then
            for dir, off in pairs(dir_offsets) do
                local dest = ctx:peek_exit_at(cur.vnum, dir)
                if dest and not visited[dest] then
                    visited[dest] = true
                    queue[#queue + 1] = {
                        vnum = dest,
                        depth = cur.depth + 1,
                        x = cur.x + off[1],
                        y = cur.y + off[2],
                    }
                end
            end
        end
    end

    -- Render grid
    local zone_vnum = math.floor(start_vnum / 100)
    local lines = {}
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━ 전체 지도 (존 " .. zone_vnum .. ") ━━━━━━━━━━━━{reset}"

    for y = min_y, max_y do
        local row = ""
        for x = min_x, max_x do
            local cell = (grid[y] and grid[y][x]) or ""
            if cell == "" then
                row = row .. string.format("%-10s", "")
            elseif x == 0 and y == 0 then
                row = row .. string.format("{bright_white}[%-8s]{reset}", cell)
            else
                row = row .. string.format("{green}[%-8s]{reset}", cell)
            end
        end
        if row:find("[^%s]") then
            lines[#lines + 1] = row
        end
    end

    lines[#lines + 1] = ""
    lines[#lines + 1] = string.format("  총 %d개 방 탐색 (깊이 %d)", qi - 1, MAX_DEPTH)
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end

-- ── Compass map (original: "지도" → limited adjacent view) ────────
local function show_compass_map(ctx)
    local ch = ctx.char
    if not ch then return end

    local dirs = {"north", "east", "south", "west", "up", "down"}
    local kr = {"북", "동", "남", "서", "위", "아래"}

    local room = ctx:get_room()
    local center_name = room and room.proto.name or "?"

    -- Get adjacent room names
    local adj = {}
    for i, dir in ipairs(dirs) do
        local vnum = ctx:peek_exit(dir)
        if vnum then
            adj[kr[i]] = ctx:get_room_name(vnum)
        end
    end

    -- Named exits
    local exits = ctx:get_exits()
    local named = {}
    for i = 1, #exits do
        local ex = exits[i]
        if ex.direction >= 6 and ex.keywords and ex.keywords ~= "" then
            named[#named + 1] = ex.keywords
        end
    end

    -- Build map display
    local lines = {}
    lines[#lines + 1] = "{bright_cyan}━━━━━ 지 도 ━━━━━{reset}"

    if adj["위"] then
        lines[#lines + 1] = "  {yellow}[위]{reset} " .. trunc(adj["위"])
        lines[#lines + 1] = "    |"
    end
    if adj["북"] then
        lines[#lines + 1] = "  {green}[북]{reset} " .. trunc(adj["북"])
        lines[#lines + 1] = "    |"
    end

    local w_str = ""
    local e_str = ""
    if adj["서"] then
        w_str = trunc(adj["서"], 10) .. " {green}[서]{reset}──"
    else
        w_str = "           "
    end
    if adj["동"] then
        e_str = "──{green}[동]{reset} " .. trunc(adj["동"], 10)
    end
    lines[#lines + 1] = w_str .. "{bright_white}[" .. trunc(center_name, 10) .. "]{reset}" .. e_str

    if adj["남"] then
        lines[#lines + 1] = "    |"
        lines[#lines + 1] = "  {green}[남]{reset} " .. trunc(adj["남"])
    end
    if adj["아래"] then
        lines[#lines + 1] = "    |"
        lines[#lines + 1] = "  {yellow}[아래]{reset} " .. trunc(adj["아래"])
    end

    if #named > 0 then
        lines[#lines + 1] = ""
        lines[#lines + 1] = "  {cyan}특수 출구:{reset} " .. table.concat(named, ", ")
    end

    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end

-- ── Main command: "지도" / "지도 전체" ────────────────────────────
register_command("지도", function(ctx, args)
    if args and (args:find("전체") or args:lower() == "full" or args:lower() == "all") then
        show_full_map(ctx)
    else
        show_compass_map(ctx)
    end
end)
