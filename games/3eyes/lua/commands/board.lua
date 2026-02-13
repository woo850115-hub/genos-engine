-- board.lua — 3eyes board system (18 boards)
-- Original: board.c (write/read/delete/list)
-- DB tables: boards, board_posts (unified schema v1.0)
-- player_data keys: "board_read" (dict: board_id → last_read_post_id)

-- ══════════════════════════════════════════════════════════════════
-- Board definitions — 18 boards from board.c
-- Access levels: 0=all, 1=DM only, 2=family only
-- ══════════════════════════════════════════════════════════════════

local BOARDS = {
    {id=1,  name="자유게시판",   access=0},
    {id=2,  name="질문게시판",   access=0},
    {id=3,  name="건의게시판",   access=0},
    {id=4,  name="공지게시판",   access=1},
    {id=5,  name="버그게시판",   access=0},
    {id=6,  name="가족게시판1",  access=2, family=1},
    {id=7,  name="가족게시판2",  access=2, family=2},
    {id=8,  name="가족게시판3",  access=2, family=3},
    {id=9,  name="가족게시판4",  access=2, family=4},
    {id=10, name="가족게시판5",  access=2, family=5},
    {id=11, name="가족게시판6",  access=2, family=6},
    {id=12, name="가족게시판7",  access=2, family=7},
    {id=13, name="가족게시판8",  access=2, family=8},
    {id=14, name="가족게시판9",  access=2, family=9},
    {id=15, name="가족게시판10", access=2, family=10},
    {id=16, name="가족게시판11", access=2, family=11},
    {id=17, name="가족게시판12", access=2, family=12},
    {id=18, name="이벤트게시판", access=0},
}

-- Board data storage (runtime — posts stored in player_data as flat list per board)
-- Using player_data global: "board_posts_<id>" = list of {author, title, body, time}
-- In production this would use DB board_posts table via ctx:db_query()
-- For now: engine-level global state via a Lua module table

local board_posts = {}  -- [board_id] = {post1, post2, ...}
local MAX_POSTS_PER_BOARD = 50
local next_post_id = 1

for _, b in ipairs(BOARDS) do
    board_posts[b.id] = {}
end

local function get_board_by_name(name)
    name = name:lower()
    for _, b in ipairs(BOARDS) do
        if b.name:lower():find(name, 1, true) then
            return b
        end
    end
    -- Try by number
    local num = tonumber(name)
    if num then
        for _, b in ipairs(BOARDS) do
            if b.id == num then return b end
        end
    end
    return nil
end

local function can_access_board(ctx, board)
    if board.access == 0 then return true end
    if board.access == 1 then
        local cls = ctx.char.class_id or CLASS_FIGHTER
        return cls >= CLASS_DM
    end
    if board.access == 2 then
        -- Family board: check if player is in the right family
        if not ctx:has_flag(PFAMIL) then return false end
        local family_id = ctx:get_player_data("family_id")
        return family_id and family_id == board.family
    end
    return false
end

-- ── 게시판 — 게시판 목록 ──────────────────────────────────────────
register_command("게시판", function(ctx, args)
    local lines = {
        "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        "{bright_cyan}  번호  게시판명            글수  접근{reset}",
        "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
    }
    for _, b in ipairs(BOARDS) do
        local access_str = "공개"
        if b.access == 1 then access_str = "DM전용" end
        if b.access == 2 then access_str = "가족전용" end
        local post_count = #(board_posts[b.id] or {})
        -- New post indicator
        local new_mark = ""
        local board_read = ctx:get_player_data("board_read") or {}
        if type(board_read) ~= "table" then board_read = {} end
        local last_read = 0
        pcall(function() last_read = board_read[tostring(b.id)] or 0 end)
        if post_count > 0 and board_posts[b.id][post_count] then
            local last_post = board_posts[b.id][post_count]
            if last_post.id > last_read then
                new_mark = " {bright_yellow}[새글]{reset}"
            end
        end
        lines[#lines + 1] = string.format("  %3d)  %-18s %3d  %s%s",
            b.id, b.name, post_count, access_str, new_mark)
    end
    lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
    ctx:send(table.concat(lines, "\r\n"))
end)

-- ── 읽어 — 글 보기 (board.c read) ────────────────────────────────
register_command("읽어", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 읽어 <게시판번호|이름> [글번호]")
        return
    end

    local board_name, post_num_str = args:match("^(%S+)%s*(%S*)$")
    local board = get_board_by_name(board_name)
    if not board then
        ctx:send("그런 게시판은 없습니다. (게시판 으로 목록 확인)")
        return
    end
    if not can_access_board(ctx, board) then
        ctx:send("{yellow}이 게시판에 접근할 권한이 없습니다.{reset}")
        return
    end

    local posts = board_posts[board.id] or {}
    local post_num = tonumber(post_num_str)

    if not post_num or post_num_str == "" then
        -- Show post list
        local lines = {
            "{bright_cyan}━━ " .. board.name .. " ━━{reset}",
            "{bright_cyan}  번호  제목                       작성자{reset}",
            "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}",
        }
        if #posts == 0 then
            lines[#lines + 1] = "  글이 없습니다."
        else
            for i, post in ipairs(posts) do
                lines[#lines + 1] = string.format("  %3d)  %-25s %s",
                    i, post.title or "(무제)", post.author or "???")
            end
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        -- Mark as read
        local board_read = ctx:get_player_data("board_read") or {}
        if type(board_read) ~= "table" then board_read = {} end
        if #posts > 0 then
            board_read[tostring(board.id)] = posts[#posts].id
        end
        ctx:set_player_data("board_read", board_read)
        return
    end

    -- Read specific post
    if post_num < 1 or post_num > #posts then
        ctx:send("그런 글 번호는 없습니다. (1-" .. #posts .. ")")
        return
    end

    local post = posts[post_num]
    ctx:send("{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send("{bright_white}  제목: " .. (post.title or "(무제)") .. "{reset}")
    ctx:send("  작성자: " .. (post.author or "???"))
    ctx:send("{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
    ctx:send(post.body or "")
    ctx:send("{bright_cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}")
end)

-- ── 써 — 글쓰기 (board.c write) ───────────────────────────────
register_command("써", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 써 <게시판번호|이름> <제목> <내용>")
        return
    end

    local board_name, title, body = args:match("^(%S+)%s+(%S+)%s+(.+)$")
    if not board_name or not title then
        -- Try two-arg form: 써 <board> <title>
        board_name, title = args:match("^(%S+)%s+(.+)$")
        body = ""
    end
    if not board_name then
        ctx:send("사용법: 써 <게시판번호|이름> <제목> [내용]")
        return
    end

    local board = get_board_by_name(board_name)
    if not board then
        ctx:send("그런 게시판은 없습니다.")
        return
    end
    if not can_access_board(ctx, board) then
        ctx:send("{yellow}이 게시판에 글을 쓸 권한이 없습니다.{reset}")
        return
    end

    local posts = board_posts[board.id]
    if #posts >= MAX_POSTS_PER_BOARD then
        -- Remove oldest
        table.remove(posts, 1)
    end

    local post = {
        id = next_post_id,
        author = ctx.char.name,
        title = title,
        body = body or "",
    }
    next_post_id = next_post_id + 1
    posts[#posts + 1] = post

    ctx:send("{green}" .. board.name .. "에 글을 올렸습니다. [" .. title .. "]{reset}")
    ctx:send_room(ctx.char.name .. "이(가) " .. board.name .. "에 글을 올립니다.")
end)

-- ── 글삭제 — 글 삭제 (board.c delete) ────────────────────────────
register_command("글삭제", function(ctx, args)
    if not args or args == "" then
        ctx:send("사용법: 글삭제 <게시판번호|이름> <글번호>")
        return
    end

    local board_name, post_num_str = args:match("^(%S+)%s+(%S+)$")
    if not board_name or not post_num_str then
        ctx:send("사용법: 글삭제 <게시판번호|이름> <글번호>")
        return
    end

    local board = get_board_by_name(board_name)
    if not board then
        ctx:send("그런 게시판은 없습니다.")
        return
    end

    local posts = board_posts[board.id]
    local post_num = tonumber(post_num_str)
    if not post_num or post_num < 1 or post_num > #posts then
        ctx:send("그런 글 번호는 없습니다.")
        return
    end

    local post = posts[post_num]
    local ch = ctx.char
    -- Only author or DM can delete
    if post.author ~= ch.name and (ch.class_id or 0) < CLASS_DM then
        ctx:send("{yellow}자신이 쓴 글만 삭제할 수 있습니다.{reset}")
        return
    end

    table.remove(posts, post_num)
    ctx:send("{green}" .. board.name .. "의 글 #" .. post_num .. "을(를) 삭제했습니다.{reset}")
end)
