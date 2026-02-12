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
    ["방호"] = 1,
    ["방열"] = 74,
    ["방한"] = 79,
    ["정화"] = 3,
    ["실명"] = 4,
    ["불꽃"] = 5,
    ["라이트닝"] = 6,
    ["매혹"] = 7,
    ["냉기접촉"] = 8,
    ["복제"] = 9,
    ["오로라"] = 10,
    ["날씨조절"] = 11,
    ["음식창조"] = 12,
    ["식수창조"] = 13,
    ["환명"] = 14,
    ["치료"] = 15,
    ["상처치료"] = 16,
    ["저주"] = 17,
    ["선악감지"] = 18,
    ["투명감지"] = 19,
    ["마법감지"] = 20,
    ["독감지"] = 21,
    ["악의소멸"] = 22,
    ["선의소멸"] = 46,
    ["지진"] = 23,
    ["스피드"] = 71,
    ["웨이브"] = 61,
    ["마하킬라"] = 57,
    ["루시펠"] = 60,
    ["무기강화"] = 24,
    ["정기흡수"] = 25,
    ["그룹성호"] = 47,
    ["화이어볼"] = 26,
    ["역중력"] = 52,
    ["혼란"] = 53,
    ["썬더볼"] = 54,
    ["펜리스"] = 55,
    ["켈베로스"] = 56,
    ["키마이라"] = 58,
    ["하데스"] = 59,
    ["폭풍"] = 64,
    ["그룹치료"] = 48,
    ["내상"] = 27,
    ["힐링"] = 28,
    ["완치"] = 62,
    ["마나회복"] = 68,
    ["암흑감지"] = 50,
    ["투명장막"] = 29,
    ["베라이트닝"] = 30,
    ["물체감지"] = 31,
    ["번개화살"] = 32,
    ["독"] = 33,
    ["악에서보호"] = 34,
    ["저주정화"] = 35,
    ["빛의방패"] = 36,
    ["충격파"] = 37,
    ["슬립"] = 38,
    ["힘"] = 39,
    ["소환"] = 40,
    ["귀환"] = 42,
    ["해독"] = 43,
    ["생명의빛"] = 44,
    ["죽음의단어"] = 63,
    ["레드드래곤"] = 65,
    ["사랑의빛"] = 66,
    ["엘리나"] = 67,
    ["골렘창조"] = 69,
    ["안개"] = 72,
    ["합체"] = 201,
    ["베기라마"] = 202,
    ["다크하우져"] = 203,
    ["블리자드"] = 204,
    ["산화"] = 205,
    ["썬더스토엄"] = 206,
    ["부상"] = 75,
    ["수중호흡"] = 80,
    ["그룹부상"] = 76,
    ["정령소환"] = 77,
    ["그룹투명"] = 78,
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
