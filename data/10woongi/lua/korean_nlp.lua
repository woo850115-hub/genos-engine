-- GenOS Korean NLP Utilities
-- Auto-generated — do not edit
-- UTF-8 hangul analysis, particle handling, verb stem extraction

local KoreanNLP = {}

-- ═══ UTF-8 helpers ═══

--- Decode a single UTF-8 character starting at position *i* in *s*.
--- Returns (codepoint, next_index).
function KoreanNLP.utf8_decode(s, i)
    local b = s:byte(i)
    if not b then return nil, i end
    if b < 0x80 then return b, i + 1 end
    if b < 0xE0 then
        return (b - 0xC0) * 64 + (s:byte(i + 1) - 0x80), i + 2
    end
    if b < 0xF0 then
        return (b - 0xE0) * 4096 + (s:byte(i + 1) - 0x80) * 64 + (s:byte(i + 2) - 0x80), i + 3
    end
    return (b - 0xF0) * 262144 + (s:byte(i + 1) - 0x80) * 4096
        + (s:byte(i + 2) - 0x80) * 64 + (s:byte(i + 3) - 0x80), i + 4
end

--- Return the codepoint of the *last* character in *s*.
function KoreanNLP.last_codepoint(s)
    local cp, last_cp = nil, nil
    local i = 1
    while i <= #s do
        cp, i = KoreanNLP.utf8_decode(s, i)
        if cp then last_cp = cp end
    end
    return last_cp
end

--- True if codepoint is a Hangul syllable (U+AC00..U+D7A3).
function KoreanNLP.is_hangul_syllable(cp)
    return cp >= 0xAC00 and cp <= 0xD7A3
end

-- ═══ 받침 (final consonant) detection ═══

--- True if the last Hangul syllable in *str* has a final consonant.
function KoreanNLP.has_batchim(str)
    local cp = KoreanNLP.last_codepoint(str)
    if not cp or not KoreanNLP.is_hangul_syllable(cp) then return false end
    return (cp - 0xAC00) % 28 ~= 0
end

-- ═══ Output particle selection ═══

KoreanNLP.PARTICLE_TYPES = {
    subject = {"이", "가"},
    object = {"을", "를"},
    topic = {"은", "는"},
    comit = {"과", "와"},
    dir = {"으로", "로"},
    copula = {"이다", "다"},
}

--- Select the correct output particle for *noun* of type *ptype*.
function KoreanNLP.particle(noun, ptype)
    local pair = KoreanNLP.PARTICLE_TYPES[ptype]
    if not pair then return "" end
    if KoreanNLP.has_batchim(noun) then return pair[1] else return pair[2] end
end

-- ═══ Input particle stripping ═══

KoreanNLP.INPUT_PARTICLES = {
    {"에게서", "from_target"},
    {"에게", "target"},
    {"한테", "target"},
    {"에서", "from_loc"},
    {"으로", "dir"},
    {"로", "dir"},
    {"을", "object"},
    {"를", "object"},
    {"이", "subject"},
    {"가", "subject"},
    {"은", "topic"},
    {"는", "topic"},
    {"과", "comit"},
    {"와", "comit"},
    {"에", "location"},
    {"의", "possess"},
}

--- Strip a trailing particle from *token*.
--- Returns stem, role (or token, nil if no particle found).
function KoreanNLP.strip_particle(token)
    for _, pair in ipairs(KoreanNLP.INPUT_PARTICLES) do
        local suffix, role = pair[1], pair[2]
        local slen = #suffix
        if #token > slen and token:sub(-slen) == suffix then
            local stem = token:sub(1, -(slen + 1))
            -- verify stem ends with a hangul syllable
            local cp = KoreanNLP.last_codepoint(stem)
            if cp and KoreanNLP.is_hangul_syllable(cp) then
                return stem, role
            end
        end
    end
    return token, nil
end

-- ═══ Verb stem extraction ═══

KoreanNLP.VERB_ENDINGS = {
    "해줘",
    "해라",
    "하다",
    "하자",
    "하지",
    "해",
    "어",
    "아",
    "기",
}

--- Remove conjugation endings from *verb*, returning the stem.
function KoreanNLP.extract_stem(verb)
    for _, ending in ipairs(KoreanNLP.VERB_ENDINGS) do
        local elen = #ending
        if #verb > elen and verb:sub(-elen) == ending then
            return verb:sub(1, -(elen + 1))
        end
    end
    return verb
end

return KoreanNLP
