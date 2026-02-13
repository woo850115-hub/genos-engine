-- poker.lua — 3eyes poker system (original-faithful)
-- Original: poker.c, poker2.c (kyk4.c)
-- RPOKER room required, LT_POKER=32 (3s cooldown)

-- ══════════════════════════════════════════════════════════════════
-- Card definitions (standard 52-card deck)
-- ══════════════════════════════════════════════════════════════════

local SUITS = {"♠", "♥", "♦", "♣"}
local RANKS = {"A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"}
local RANK_VALUES = {A=14, ["2"]=2, ["3"]=3, ["4"]=4, ["5"]=5, ["6"]=6,
    ["7"]=7, ["8"]=8, ["9"]=9, ["10"]=10, J=11, Q=12, K=13}

-- ══════════════════════════════════════════════════════════════════
-- Runtime poker game state (module-level)
-- ══════════════════════════════════════════════════════════════════

-- games[room_vnum] = { players={}, deck={}, pot=0, phase="waiting",
--   current_bet=0, current_player=0 }
local games = {}

local MIN_BET = 100
local MAX_PLAYERS = 6

local function new_deck()
    local deck = {}
    for _, suit in ipairs(SUITS) do
        for _, rank in ipairs(RANKS) do
            deck[#deck + 1] = {rank=rank, suit=suit, value=RANK_VALUES[rank]}
        end
    end
    -- Shuffle (Fisher-Yates)
    for i = #deck, 2, -1 do
        local j = te_mrand(1, i)
        deck[i], deck[j] = deck[j], deck[i]
    end
    return deck
end

local function draw_card(deck)
    if #deck == 0 then return nil end
    return table.remove(deck)
end

local function card_str(card)
    return card.suit .. card.rank
end

local function hand_str(hand)
    local parts = {}
    for _, c in ipairs(hand) do
        parts[#parts + 1] = card_str(c)
    end
    return table.concat(parts, " ")
end

-- ── Hand evaluation (poker.c eval_hand) ─────────────────────────

local HAND_NAMES = {
    [0]="노페어", [1]="원페어", [2]="투페어", [3]="트리플",
    [4]="스트레이트", [5]="플러쉬", [6]="풀하우스",
    [7]="포카드", [8]="스트레이트플러쉬", [9]="로얄스트레이트플러쉬",
}

local function evaluate_hand(hand)
    -- Sort by value descending
    local sorted = {}
    for _, c in ipairs(hand) do sorted[#sorted + 1] = c end
    table.sort(sorted, function(a, b) return a.value > b.value end)

    -- Count ranks and suits
    local rank_count = {}
    local suit_count = {}
    for _, c in ipairs(sorted) do
        rank_count[c.value] = (rank_count[c.value] or 0) + 1
        suit_count[c.suit] = (suit_count[c.suit] or 0) + 1
    end

    -- Check flush
    local is_flush = false
    for _, cnt in pairs(suit_count) do
        if cnt >= 5 then is_flush = true; break end
    end

    -- Check straight
    local is_straight = false
    local high_straight = 0
    if #sorted >= 5 then
        -- Check consecutive (using unique values)
        local vals = {}
        local seen = {}
        for _, c in ipairs(sorted) do
            if not seen[c.value] then
                vals[#vals + 1] = c.value
                seen[c.value] = true
            end
        end
        table.sort(vals, function(a, b) return a > b end)
        -- Check A-2-3-4-5 (wheel)
        if vals[1] == 14 then vals[#vals + 1] = 1 end
        for i = 1, #vals - 4 do
            if vals[i] - vals[i+4] == 4 then
                is_straight = true
                high_straight = vals[i]
                break
            end
        end
    end

    -- Count pairs/triples/quads
    local pairs_found = 0
    local triple_found = false
    local quad_found = false
    local pair_high = 0
    for val, cnt in pairs(rank_count) do
        if cnt == 4 then quad_found = true
        elseif cnt == 3 then triple_found = true
        elseif cnt == 2 then
            pairs_found = pairs_found + 1
            if val > pair_high then pair_high = val end
        end
    end

    -- Determine hand rank
    local rank, score
    if is_straight and is_flush then
        if high_straight == 14 then
            rank = 9  -- Royal Straight Flush
            score = 9000
        else
            rank = 8  -- Straight Flush
            score = 8000 + high_straight
        end
    elseif quad_found then
        rank = 7; score = 7000
    elseif triple_found and pairs_found > 0 then
        rank = 6; score = 6000
    elseif is_flush then
        rank = 5; score = 5000 + sorted[1].value
    elseif is_straight then
        rank = 4; score = 4000 + high_straight
    elseif triple_found then
        rank = 3; score = 3000
    elseif pairs_found >= 2 then
        rank = 2; score = 2000 + pair_high
    elseif pairs_found == 1 then
        rank = 1; score = 1000 + pair_high
    else
        rank = 0; score = sorted[1].value
    end

    return rank, score, HAND_NAMES[rank] or "?"
end

local function get_game(ctx)
    local room_vnum = ctx:get_room_vnum()
    return games[room_vnum], room_vnum
end

-- ── 베팅 — 포커 참가/시작 (poker.c, cmdno=73) ──────────────────

register_command("베팅", function(ctx, args)
    if not te_room_has_flag(ctx, 11) then  -- RPOKER
        ctx:send("{yellow}포커룸에서만 포커를 할 수 있습니다.{reset}")
        return
    end

    local ch = ctx.char
    local sub = (args or ""):lower()

    if sub == "" or sub == "join" or sub == "참가" then
        local game, rv = get_game(ctx)
        if not game then
            -- Create new game
            game = {
                players = {},
                deck = {},
                pot = 0,
                phase = "waiting",
                current_bet = 0,
                turn = 0,
            }
            games[rv] = game
        end

        if game.phase ~= "waiting" then
            ctx:send("{yellow}현재 게임이 진행 중입니다. 다음 판을 기다려주세요.{reset}")
            return
        end

        -- Check if already joined
        for _, p in ipairs(game.players) do
            if p.name == ch.name then
                ctx:send("{yellow}이미 참가한 상태입니다.{reset}")
                return
            end
        end

        if #game.players >= MAX_PLAYERS then
            ctx:send("{yellow}인원이 가득 찼습니다. (최대 " .. MAX_PLAYERS .. "명){reset}")
            return
        end

        -- Ante: 500 gold
        local ante = 500
        if ch.gold < ante then
            ctx:send("{yellow}참가비 " .. ante .. "원이 필요합니다.{reset}")
            return
        end
        ch.gold = ch.gold - ante
        game.pot = game.pot + ante

        game.players[#game.players + 1] = {
            name = ch.name,
            hand = {},
            bet = ante,
            folded = false,
        }

        ctx:send("{bright_green}포커 게임에 참가했습니다! (참가비: " .. ante .. "원){reset}")
        ctx:send_room(ch.name .. "이(가) 포커 게임에 참가합니다.")

        if #game.players >= 2 then
            ctx:send("{bright_cyan}[포커] 2인 이상 참가! '게임시작'으로 게임을 시작하세요.{reset}")
        end
        return
    end

    if sub == "start" or sub == "시작" then
        local game, rv = get_game(ctx)
        if not game or game.phase ~= "waiting" then
            ctx:send("시작할 수 있는 게임이 없습니다.")
            return
        end
        if #game.players < 2 then
            ctx:send("{yellow}최소 2명이 필요합니다.{reset}")
            return
        end

        -- Deal 5 cards to each player
        game.deck = new_deck()
        game.phase = "betting"
        game.current_bet = 0
        game.turn = 1

        for _, p in ipairs(game.players) do
            p.hand = {}
            for _ = 1, 5 do
                local card = draw_card(game.deck)
                if card then p.hand[#p.hand + 1] = card end
            end
        end

        -- Show cards to each player
        for _, p in ipairs(game.players) do
            local player = ctx:find_player(p.name)
            if player and player.session then
                ctx:send_to(player, "{bright_cyan}━━━━━ 포커 ━━━━━{reset}")
                ctx:send_to(player, "당신의 패: {bright_white}" .. hand_str(p.hand) .. "{reset}")
                local _, _, hand_name = evaluate_hand(p.hand)
                ctx:send_to(player, "핸드: {bright_yellow}" .. hand_name .. "{reset}")
                ctx:send_to(player, "{bright_cyan}━━━━━━━━━━━━━━━━{reset}")
            end
        end

        ctx:send_room("{bright_yellow}[포커] 게임 시작! 카드가 배분됩니다.{reset}")
        ctx:send_room("{bright_yellow}[포커] bet <금액> / call / 포기 / 카드보기{reset}")
        return
    end

    if sub == "status" or sub == "상태" then
        local game = get_game(ctx)
        if not game then
            ctx:send("진행 중인 게임이 없습니다.")
            return
        end
        local lines = {"{bright_cyan}━━━━━ 포커 현황 ━━━━━{reset}"}
        lines[#lines + 1] = "  판돈: " .. game.pot .. "원  상태: " .. game.phase
        for i, p in ipairs(game.players) do
            local status = p.folded and "{red}폴드{reset}" or "{green}참가중{reset}"
            lines[#lines + 1] = string.format("  %d) %s  베팅: %d원  %s",
                i, p.name, p.bet, status)
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    ctx:send("사용법: 베팅 [참가|시작|상태]")
end)

-- 별칭: poker → 베팅
register_command("poker", function(ctx, args) ctx:call_command("베팅", args or "") end)

-- ── bet — 베팅 금액 지정 ────────────────────────────────────────

register_command("bet", function(ctx, args)
    local game = get_game(ctx)
    if not game or game.phase ~= "betting" then
        ctx:send("베팅할 수 있는 게임이 없습니다.")
        return
    end

    local ch = ctx.char
    local amount = tonumber(args or "")
    if not amount or amount < MIN_BET then
        ctx:send("사용법: bet <금액> (최소 " .. MIN_BET .. "원)")
        return
    end

    -- Find player in game
    local player_data = nil
    for _, p in ipairs(game.players) do
        if p.name == ch.name and not p.folded then
            player_data = p; break
        end
    end
    if not player_data then
        ctx:send("{yellow}게임에 참가하지 않았거나 이미 폴드했습니다.{reset}")
        return
    end

    if ch.gold < amount then
        ctx:send("{yellow}골드가 부족합니다.{reset}")
        return
    end

    ch.gold = ch.gold - amount
    player_data.bet = player_data.bet + amount
    game.pot = game.pot + amount
    if amount > game.current_bet then
        game.current_bet = amount
    end

    ctx:send("{green}" .. amount .. "원을 베팅합니다. (총 판돈: " .. game.pot .. "원){reset}")
    ctx:send_room(ch.name .. "이(가) " .. amount .. "원을 베팅합니다!")
end)

-- ── call — 콜 ───────────────────────────────────────────────────

register_command("call", function(ctx, args)
    local game = get_game(ctx)
    if not game or game.phase ~= "betting" then
        ctx:send("콜할 수 있는 게임이 없습니다.")
        return
    end

    local ch = ctx.char
    local player_data = nil
    for _, p in ipairs(game.players) do
        if p.name == ch.name and not p.folded then
            player_data = p; break
        end
    end
    if not player_data then
        ctx:send("{yellow}게임에 참가하지 않았거나 이미 폴드했습니다.{reset}")
        return
    end

    local need = game.current_bet
    if need <= 0 then
        ctx:send("아직 아무도 베팅하지 않았습니다.")
        return
    end
    if ch.gold < need then
        ctx:send("{yellow}골드가 부족합니다. (필요: " .. need .. "원){reset}")
        return
    end

    ch.gold = ch.gold - need
    player_data.bet = player_data.bet + need
    game.pot = game.pot + need

    ctx:send("{green}콜! " .. need .. "원을 맞춥니다.{reset}")
    ctx:send_room(ch.name .. "이(가) 콜합니다!")
end)

-- ── 포기 — 폴드 (cmdno=76, 포커 전용) ──────────────────────────

register_command("포기", function(ctx, args)
    local game = get_game(ctx)
    if not game or game.phase ~= "betting" then
        ctx:send("폴드할 수 있는 게임이 없습니다.")
        return
    end

    local ch = ctx.char
    for _, p in ipairs(game.players) do
        if p.name == ch.name and not p.folded then
            p.folded = true
            ctx:send("{yellow}포기합니다.{reset}")
            ctx:send_room(ch.name .. "이(가) 포기합니다.")

            -- Check if only one player left
            local active = 0
            local last_active = nil
            for _, pp in ipairs(game.players) do
                if not pp.folded then
                    active = active + 1
                    last_active = pp
                end
            end
            if active <= 1 and last_active then
                -- Auto-win
                local winner = ctx:find_player(last_active.name)
                if winner then
                    winner.gold = winner.gold + game.pot
                    ctx:send_room("{bright_yellow}[포커] " .. last_active.name ..
                        "이(가) " .. game.pot .. "원을 획득합니다! (상대 전원 폴드){reset}")
                end
                local rv = ctx:get_room_vnum()
                games[rv] = nil
            end
            return
        end
    end
    ctx:send("{yellow}게임에 참가하지 않았습니다.{reset}")
end)

-- 별칭: fold → 포기
register_command("fold", function(ctx, args) ctx:call_command("포기", args or "") end)

-- ── 카드보기 — 쇼다운 (cmdno=77) ───────────────────────────────

register_command("카드보기", function(ctx, args)
    local game, rv = get_game(ctx)
    if not game or game.phase ~= "betting" then
        ctx:send("쇼다운할 수 있는 게임이 없습니다.")
        return
    end

    -- Any active player can call showdown
    local ch = ctx.char
    local is_player = false
    for _, p in ipairs(game.players) do
        if p.name == ch.name and not p.folded then
            is_player = true; break
        end
    end
    if not is_player then
        ctx:send("{yellow}게임에 참가하지 않았습니다.{reset}")
        return
    end

    -- Showdown: reveal all hands, determine winner
    game.phase = "showdown"

    local lines = {
        "{bright_yellow}━━━━━━━━━━━ 쇼다운! ━━━━━━━━━━━{reset}",
    }

    local best_score = -1
    local winner = nil

    for _, p in ipairs(game.players) do
        if not p.folded then
            local rank, score, hand_name = evaluate_hand(p.hand)
            lines[#lines + 1] = string.format("  %s: %s — {bright_white}%s{reset}",
                p.name, hand_str(p.hand), hand_name)
            if score > best_score then
                best_score = score
                winner = p
            end
        else
            lines[#lines + 1] = "  " .. p.name .. ": {red}폴드{reset}"
        end
    end

    if winner then
        lines[#lines + 1] = ""
        lines[#lines + 1] = "{bright_yellow}  승자: " .. winner.name ..
            " — " .. game.pot .. "원 획득!{reset}"

        local winner_char = ctx:find_player(winner.name)
        if winner_char then
            winner_char.gold = winner_char.gold + game.pot
        end
    end

    lines[#lines + 1] = "{bright_yellow}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{reset}"

    -- Send to all in room
    for _, p in ipairs(game.players) do
        local player = ctx:find_player(p.name)
        if player and player.session then
            ctx:send_to(player, table.concat(lines, "\r\n"))
        end
    end
    ctx:send_room(table.concat(lines, "\r\n"))

    -- Clean up game
    games[rv] = nil
end)

-- 별칭: show → 카드보기
register_command("show", function(ctx, args) ctx:call_command("카드보기", args or "") end)

-- ══════════════════════════════════════════════════════════════════
-- Stub commands (준비 중)
-- ══════════════════════════════════════════════════════════════════

-- ── 게임시작 — 포커 게임 시작 (stub) ────────────────────────────

register_command("게임시작", function(ctx, args)
    ctx:send("{yellow}현재 준비 중입니다.{reset}")
end)

-- ── open — 포커 오픈 (stub) ─────────────────────────────────────

register_command("open", function(ctx, args)
    ctx:send("{yellow}현재 준비 중입니다.{reset}")
end)

-- ── raise — 포커 레이즈 (stub) ──────────────────────────────────

register_command("raise", function(ctx, args)
    ctx:send("{yellow}현재 준비 중입니다.{reset}")
end)

-- ── stay — 포커 스테이 (stub) ───────────────────────────────────

register_command("stay", function(ctx, args)
    ctx:send("{yellow}현재 준비 중입니다.{reset}")
end)
