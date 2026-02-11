-- GenOS Korean Command System (SOV parser)
-- Auto-generated — do not edit

local KoreanNLP = require("korean_nlp")
local Commands = {}

-- ═══ Standard Korean verb → action mapping ═══
Commands.VERBS = {
    ["가"] = "go",
    ["가져"] = "get",
    ["건강"] = "score",
    ["공격"] = "attack",
    ["구원"] = "rescue",
    ["구해"] = "rescue",
    ["귓"] = "tell",
    ["그만"] = "quit",
    ["꺼내"] = "equipment",
    ["날씨"] = "weather",
    ["넣"] = "put",
    ["놔"] = "drop",
    ["누가"] = "who",
    ["누구"] = "who",
    ["닫"] = "close",
    ["도움"] = "help",
    ["들"] = "hold",
    ["따라가"] = "follow",
    ["떠나"] = "flee",
    ["마시"] = "drink",
    ["말"] = "say",
    ["말하"] = "say",
    ["먹"] = "eat",
    ["무리"] = "group",
    ["배우"] = "practice",
    ["버려"] = "drop",
    ["벗"] = "remove",
    ["별칭"] = "alias",
    ["보"] = "look",
    ["봐"] = "look",
    ["빼"] = "drop",
    ["사"] = "buy",
    ["서"] = "stand",
    ["속삭이"] = "whisper",
    ["쉬"] = "rest",
    ["습득"] = "get",
    ["시간"] = "time",
    ["시전"] = "cast",
    ["싸우"] = "attack",
    ["앉"] = "sit",
    ["열"] = "open",
    ["외치"] = "shout",
    ["일어나"] = "stand",
    ["입"] = "wear",
    ["자"] = "sleep",
    ["잠가"] = "lock",
    ["잠그"] = "lock",
    ["저장"] = "save",
    ["정보"] = "info",
    ["주"] = "give",
    ["주머니"] = "inventory",
    ["주문"] = "cast",
    ["주워"] = "get",
    ["죽"] = "kill",
    ["죽이"] = "kill",
    ["줘"] = "give",
    ["집"] = "get",
    ["착용"] = "wear",
    ["찾"] = "search",
    ["챙기"] = "wield",
    ["팔"] = "sell",
    ["풀"] = "unlock",
    ["피하"] = "flee",
    ["학습"] = "practice",
}

-- ═══ Direction mapping ═══
Commands.DIRECTIONS = {
    ["북"] = 0,
    ["북쪽"] = 0,
    ["동"] = 1,
    ["동쪽"] = 1,
    ["남"] = 2,
    ["남쪽"] = 2,
    ["서"] = 3,
    ["서쪽"] = 3,
    ["위"] = 4,
    ["위쪽"] = 4,
    ["아래"] = 5,
    ["아래쪽"] = 5,
    ["북서"] = 6,
    ["북동"] = 7,
    ["남동"] = 8,
    ["남서"] = 9,
    ["8"] = 0,
    ["6"] = 1,
    ["2"] = 2,
    ["4"] = 3,
    ["9"] = 7,
    ["3"] = 8,
}

-- ═══ Skill / spell name mapping (from UIR) ═══
Commands.SPELL_NAMES = {
    ["패리L1"] = 1,
    ["패리L2"] = 2,
    ["패리L3"] = 3,
    ["방패방어L1"] = 4,
    ["양손무장L1"] = 5,
    ["카운터L1"] = 6,
    ["카운터L2"] = 7,
    ["전술L1"] = 8,
    ["전술L2"] = 9,
    ["집중L1"] = 10,
    ["집중L2"] = 11,
    ["치료L1"] = 12,
    ["치료L2"] = 13,
    ["치료L3"] = 14,
    ["기도L1"] = 15,
    ["기도L2"] = 16,
    ["기도L3"] = 17,
    ["부활L1"] = 18,
    ["훔치기L1"] = 19,
    ["스텔스L1"] = 20,
    ["도주술L1"] = 21,
    ["백스탭L1"] = 22,
    ["백스탭L2"] = 23,
    ["연타L1"] = 24,
    ["파이널어택L1"] = 25,
    ["마법방어L1"] = 26,
    ["마법방어L2"] = 27,
    ["마법방어L3"] = 28,
    ["요리L1"] = 29,
    ["크리티컬L1"] = 30,
    ["멘탈피스L1"] = 31,
    ["멘탈피스L2"] = 32,
    ["멘탈피스L3"] = 33,
    ["일루젼소드L1"] = 34,
    ["파이어싱L1"] = 35,
    ["현혹L1"] = 36,
    ["매직미셜L1"] = 37,
    ["파이어볼L1"] = 38,
    ["라이트닝볼트L1"] = 39,
    ["아이스스톰L1"] = 40,
    ["인첸트L1"] = 41,
    ["디멘젼도어L1"] = 42,
    ["텔레실드L1"] = 43,
    ["헤이스트L1"] = 44,
    ["소환L1"] = 45,
    ["사일런스L1"] = 46,
    ["스탑L1"] = 47,
    ["홀리실드L1"] = 48,
    ["절대방어L1"] = 49,
    ["홀리워드L1"] = 50,
    ["귀환L1"] = 51,
}

-- ═══ Verb lookup (direct match → stem extraction → match) ═══
function Commands.find_verb(token)
    if Commands.VERBS[token] then return Commands.VERBS[token] end
    local stem = KoreanNLP.extract_stem(token)
    if stem and Commands.VERBS[stem] then return Commands.VERBS[stem] end
    return nil
end

-- ═══ SOV parser ═══
function Commands.parse(input)
    local tokens = {}
    for token in input:gmatch("%S+") do table.insert(tokens, token) end
    if #tokens == 0 then return nil end

    -- Single token: direction or verb
    if #tokens == 1 then
        local stripped, _role = KoreanNLP.strip_particle(tokens[1])
        if Commands.DIRECTIONS[stripped] then
            return {handler = "go", direction = Commands.DIRECTIONS[stripped]}
        end
        local action = Commands.find_verb(tokens[1])
        if action then return {handler = action, ordered = {}} end
        if Commands.SPELL_NAMES[tokens[1]] then
            return {handler = "cast", spell_id = Commands.SPELL_NAMES[tokens[1]]}
        end
        return nil
    end

    -- Multi-token: search verb from the end (SOV)
    local verb_handler, verb_idx = nil, nil
    for i = #tokens, 1, -1 do
        verb_handler = Commands.find_verb(tokens[i])
        if verb_handler then verb_idx = i; break end
    end

    -- SVO fallback: first token as verb
    if not verb_handler then
        verb_handler = Commands.find_verb(tokens[1])
        verb_idx = 1
    end
    if not verb_handler then return nil end

    -- Remaining tokens: strip particles and assign semantic roles
    local args = {handler = verb_handler, roles = {}, ordered = {}}
    for i, token in ipairs(tokens) do
        if i ~= verb_idx then
            local noun, role = KoreanNLP.strip_particle(token)
            if Commands.DIRECTIONS[noun] then
                args.roles["direction"] = Commands.DIRECTIONS[noun]
            elseif role then
                args.roles[role] = noun
            end
            table.insert(args.ordered, noun)
        end
    end
    return args
end

return Commands
