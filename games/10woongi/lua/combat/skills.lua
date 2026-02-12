-- skills.lua — 10woongi 51 skills from 기술.h
-- Registers 'use' command for skill usage

local SKILLS = {}

local function def(id, name, kr, cat, sp, lv, classes, desc)
    SKILLS[id] = {
        id = id,
        name = name,
        korean_name = kr,
        category = cat,
        sp_cost = sp,
        min_level = lv,
        class_ids = classes,
        description = desc or "",
    }
end

-- Defense skills
def(1,  "parry_l1",         "패리1",        "defense",  0,   1,  {1,2,3,4,5}, "기본 방어")
def(2,  "parry_l2",         "패리2",        "defense",  0,  20,  {2,3,4,5}, "중급 방어")
def(3,  "parry_l3",         "패리3",        "defense",  0,  50,  {3,4,5}, "상급 방어")
def(4,  "shield_block",     "방패방어",     "defense",  5,  10,  {1,2,3,4,5,6,7}, "방패 방어")
def(5,  "absolute_defense", "절대방어",     "defense", 30,  80,  {4,8}, "절대 방어")

-- Attack skills
def(6,  "counter_l1",       "카운터1",      "attack",  10,  15,  {1,2,3,4,5,9,10,11}, "반격")
def(7,  "counter_l2",       "카운터2",      "attack",  20,  40,  {3,4,5,11}, "강화 반격")
def(8,  "multi_attack",     "연타",         "attack",  15,  25,  {1,2,3,4,5}, "연속 공격")
def(9,  "final_attack",     "파이널어택",   "attack",  50,  70,  {4,11,14}, "최종 일격")
def(10, "critical_hit",     "크리티컬",     "attack",  20,  30,  {1,2,3,4,5,9,10,11}, "치명타")
def(11, "backstab",         "백스탭",       "attack",  25,  20,  {9,10,11}, "기습 공격")
def(12, "bash",             "강타",         "attack",  15,  15,  {1,2,3,4,5}, "강타")

-- Recovery skills
def(13, "heal_l1",          "치료1",        "recovery", 20,   1,  {6,7,8,5}, "기본 치료")
def(14, "heal_l2",          "치료2",        "recovery", 40,  30,  {7,8,5}, "중급 치료")
def(15, "heal_l3",          "치료3",        "recovery", 80,  60,  {8}, "상급 치료")
def(16, "pray_l1",          "기도1",        "recovery", 30,  10,  {6,7,8}, "기본 기도")
def(17, "pray_l2",          "기도2",        "recovery", 60,  40,  {7,8}, "중급 기도")
def(18, "pray_l3",          "기도3",        "recovery",100,  70,  {8}, "상급 기도")
def(19, "resurrect",        "부활",         "recovery",200,  90,  {8}, "사망 PC 부활")

-- Stealth skills
def(20, "steal",            "훔치기",       "stealth",  10,   5,  {9,10,11}, "아이템 훔치기")
def(21, "stealth",          "스텔스",       "stealth",  15,  15,  {9,10,11}, "은신")
def(22, "escape",           "도주술",       "stealth",   5,  10,  {9,10,11}, "도주")
def(23, "detect_hidden",    "감지",         "stealth",  20,  25,  {9,10,11,12,13,14}, "은신 감지")

-- Magic skills
def(24, "magic_missile",    "매직미셜",     "magic",    15,   1,  {12,13,14}, "마법 화살")
def(25, "fireball",         "파이어볼",     "magic",    30,  20,  {12,13,14}, "화염구")
def(26, "lightning_bolt",   "라이트닝볼트", "magic",    35,  30,  {13,14}, "번개")
def(27, "ice_storm",        "아이스스톰",   "magic",    40,  40,  {13,14}, "빙풍")
def(28, "meteor",           "메테오",       "magic",    80,  70,  {14}, "운석 낙하")
def(29, "energy_drain",     "에너지드레인", "magic",    50,  50,  {13,14}, "에너지 흡수")
def(30, "sleep_spell",      "슬립",         "magic",    25,  15,  {12,13,14}, "수면")
def(31, "blindness",        "블라인드",     "magic",    25,  15,  {12,13,14}, "실명")
def(32, "dispel_magic",     "디스펠",       "magic",    30,  25,  {12,13,14}, "마법 해제")

-- Utility skills
def(33, "recall",           "귀환",         "utility",  20,   1,  {1,2,3,4,5,6,7,8,9,10,11,12,13,14})
def(34, "enchant",          "인첸트",       "utility",  50,  40,  {12,13,14}, "장비 강화")
def(35, "haste",            "헤이스트",     "utility",  40,  30,  {12,13,14,8}, "이동속도 증가")
def(36, "summon",           "소환",         "utility",  60,  50,  {12,13,14,8}, "대상 소환")
def(37, "cooking",          "요리",         "utility",   5,   1,  {1,2,3,4,5,6,7,8,9,10,11,12,13,14})
def(38, "identify",         "감정",         "utility",  10,  10,  {12,13,14}, "아이템 감정")
def(39, "teleport",         "텔레포트",     "utility",  40,  35,  {13,14}, "순간 이동")
def(40, "cure_poison",      "해독",         "recovery", 20,  15,  {6,7,8,5}, "독 치료")
def(41, "bless",            "축복",         "recovery", 25,  20,  {6,7,8}, "축복 부여")
def(42, "sanctuary",        "성역",         "recovery", 80,  60,  {8}, "성역 보호막")
def(43, "armor_spell",      "아머",         "utility",  15,   5,  {12,13,14,6,7,8}, "방어력 증가")
def(44, "strength",         "스트렝스",     "utility",  20,  10,  {12,13,14}, "공격력 증가")
def(45, "invisibility",     "인비저",       "stealth",  30,  20,  {12,13,14}, "투명화")
def(46, "fly",              "플라이",       "utility",  25,  25,  {12,13,14}, "비행")
def(47, "poison",           "독",           "magic",    25,  20,  {9,10,11,12,13,14}, "독 부여")
def(48, "earthquake",       "어스퀘이크",   "magic",    60,  55,  {14}, "지진")
def(49, "word_of_recall",   "귀환술",       "utility",  30,   5,  {1,2,3,4,5,6,7,8,9,10,11,12,13,14})
def(50, "group_heal",       "집단치료",     "recovery",100,  70,  {8}, "그룹 치료")
def(51, "charm",            "매혹",         "magic",    50,  45,  {13,14}, "NPC 매혹")


-- ── Skill lookup ─────────────────────────────────────────────

local function find_skill(name)
    if not name or name == "" then return nil end
    local name_lower = name:lower()
    -- Exact match
    for id, sk in pairs(SKILLS) do
        if sk.name == name_lower or sk.korean_name == name then
            return sk
        end
    end
    -- Prefix match
    local matches = {}
    for id, sk in pairs(SKILLS) do
        if sk.name:sub(1, #name_lower) == name_lower or
           sk.korean_name:sub(1, #name) == name then
            matches[#matches + 1] = sk
        end
    end
    if #matches == 1 then return matches[1] end
    return nil
end

local function can_use_skill(ch, skill)
    if ch.level < skill.min_level then
        return false, "레벨 " .. skill.min_level .. " 이상이어야 합니다."
    end
    local allowed = false
    for _, cid in ipairs(skill.class_ids) do
        if cid == ch.class_id then
            allowed = true
            break
        end
    end
    if not allowed then
        return false, "해당 직업은 이 기술을 사용할 수 없습니다."
    end
    local current_sp = ch.move or 0
    if current_sp < skill.sp_cost then
        return false, "내공이 부족합니다."
    end
    return true, ""
end

-- ── Damage/heal calculations ─────────────────────────────────

local function calc_attack_skill_damage(ctx, ch, skill)
    local wstats = get_wuxia_stats(ch)
    local base = math.floor(skill.sp_cost / 2) + ctx:random(1, ch.level)
    local spirit_bonus = math.floor(wstats.spirit / 3)
    return math.max(1, base + spirit_bonus + (ch.damroll or 0))
end

local function calc_magic_skill_damage(ctx, ch, skill)
    local wstats = get_wuxia_stats(ch)
    local base = skill.sp_cost + ctx:random(1, ch.level * 2)
    local wisdom_bonus = math.floor(wstats.wisdom / 2)
    return math.max(1, base + wisdom_bonus)
end

local function calc_heal_amount(ctx, ch, skill)
    local wstats = get_wuxia_stats(ch)
    local base = skill.sp_cost + ctx:random(1, ch.level)
    local wisdom_bonus = math.floor(wstats.wisdom / 2)
    return math.max(1, base + wisdom_bonus)
end

-- ── Use skill command ────────────────────────────────────────

register_command("use", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    if not args or args == "" then
        ctx:send("사용법: use <기술명> [대상]")
        return
    end

    -- Parse: "use <skill> [target]"
    local skill_name, target_name = args:match("^(%S+)%s*(.*)")
    if not skill_name then
        ctx:send("사용법: use <기술명> [대상]")
        return
    end
    target_name = (target_name and target_name ~= "") and target_name or nil

    local skill = find_skill(skill_name)
    if not skill then
        ctx:send("그런 기술은 없습니다.")
        return
    end

    local ok, err = can_use_skill(ch, skill)
    if not ok then
        ctx:send(err)
        return
    end

    -- Deduct SP cost
    ch.move = math.max(0, (ch.move or 0) - skill.sp_cost)

    -- Find target
    local target = ch  -- default self
    if target_name then
        target = ctx:find_char(target_name)
        if not target then
            ctx:send("그런 대상을 찾을 수 없습니다.")
            return
        end
    end

    if skill.category == "attack" then
        if target == ch then
            -- Need a combat target
            if ch.fighting then
                target = ch.fighting
            else
                ctx:send("공격 대상을 지정하세요.")
                return
            end
        end
        local damage = calc_attack_skill_damage(ctx, ch, skill)
        target.hp = target.hp - damage
        ctx:send("{bright_red}" .. skill.korean_name .. "! " .. target.name .. "에게 " .. damage .. " 데미지!{reset}")
        if target.session then
            ctx:send_to(target,
                "\r\n{red}" .. ch.name .. "의 " .. skill.korean_name .. "에 " .. damage .. " 데미지를 받았습니다!{reset}")
        end
        if not ch.fighting then ctx:start_combat(target) end
        if target.hp <= 0 then
            ctx:stop_combat(ch)
            ctx:defer_death(target, ch)
        end

    elseif skill.category == "magic" then
        if target == ch then
            if ch.fighting then
                target = ch.fighting
            else
                ctx:send("마법 대상을 지정하세요.")
                return
            end
        end
        local damage = calc_magic_skill_damage(ctx, ch, skill)
        target.hp = target.hp - damage
        ctx:send("{bright_magenta}" .. skill.korean_name .. "! " .. target.name .. "에게 " .. damage .. " 데미지!{reset}")
        if target.session then
            ctx:send_to(target,
                "\r\n{magenta}" .. ch.name .. "의 " .. skill.korean_name .. "에 " .. damage .. " 데미지를 받았습니다!{reset}")
        end
        if not ch.fighting then ctx:start_combat(target) end
        if target.hp <= 0 then
            ctx:stop_combat(ch)
            ctx:defer_death(target, ch)
        end

    elseif skill.category == "recovery" then
        local heal = calc_heal_amount(ctx, ch, skill)
        target.hp = math.min(target.max_hp, target.hp + heal)
        ctx:send("{bright_green}" .. skill.korean_name .. "! " .. target.name .. "을(를) " .. heal .. "만큼 치료했습니다.{reset}")

    elseif skill.category == "defense" then
        ctx:send("{cyan}" .. skill.korean_name .. "! 방어 태세를 갖춥니다.{reset}")

    elseif skill.category == "stealth" then
        ctx:send("{white}" .. skill.korean_name .. "을(를) 사용합니다.{reset}")

    else -- utility
        ctx:send("{white}" .. skill.korean_name .. "을(를) 사용합니다.{reset}")
    end
end, "기술")

-- ── Skills list command ──────────────────────────────────────

register_command("skills", function(ctx, args)
    local ch = ctx.char
    if not ch then return end

    ctx:send("{cyan}━━━ 사용 가능한 기술 목록 ━━━{reset}")

    local found = false
    -- Iterate by ID for stable order
    for id = 1, 51 do
        local skill = SKILLS[id]
        if skill then
            local allowed = false
            for _, cid in ipairs(skill.class_ids) do
                if cid == ch.class_id then allowed = true; break end
            end
            if allowed and ch.level >= skill.min_level then
                found = true
                ctx:send(string.format("  [%2d] %-12s %-6s  내공: %3d  레벨: %3d",
                    skill.id, skill.korean_name, skill.category, skill.sp_cost, skill.min_level))
            end
        end
    end

    if not found then
        ctx:send("  사용 가능한 기술이 없습니다.")
    end
end, "기술목록")
