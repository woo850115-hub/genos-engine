-- comm.lua — 3eyes 통신 명령어 (원본 cmdlist 기반)
-- 말, 얘기/이야기, //대답, 잡담/잡, 환호, 대화, 그룹말/무리말/=, 표현, 따라, 그룹/무리

----------------------------------------------------------------
-- 전역 상태
----------------------------------------------------------------
_G._3eyes_reply = _G._3eyes_reply or {}     -- reply 대상: name → sender_name
_G._3eyes_spam  = _G._3eyes_spam  or {}     -- 안티스팸 추적

----------------------------------------------------------------
-- 한글 조사 유틸
----------------------------------------------------------------
local function particle_iga(name)
    -- UTF-8 한글 받침 여부 → 이/가 결정
    if #name < 3 then return "이(가)" end
    local b1, b2, b3 = name:byte(#name - 2, #name)
    if b1 and b2 and b3 and b1 >= 0xEA and b1 <= 0xED then
        local code = (b1 - 0xE0) * 4096 + (b2 - 0x80) * 64 + (b3 - 0x80)
        if code >= 0xAC00 and code <= 0xD7A3 then
            return ((code - 0xAC00) % 28 > 0) and "이" or "가"
        end
    end
    return "이(가)"
end

----------------------------------------------------------------
-- 안티스팸 (원본 3중 구조: command4.c broadsend)
-- 1) 동일 메시지 10초 내 2회 → 자동채금 5분
-- 2) 누적 9회 → 자동채금 5분
-- 3) 4초 내 4회 연속 → 자동채금 5분
----------------------------------------------------------------
local function spam_check(ctx, message)
    local name = ctx.char.name
    local now = os.time()
    local s = _G._3eyes_spam[name]
    if not s then
        s = { msg = "", cnt = 0, t = 0, q = {} }
        _G._3eyes_spam[name] = s
    end

    -- 검사 1: 동일 메시지 반복
    if message == s.msg then
        s.cnt = s.cnt + 1
        if now - s.t < 10 and s.cnt >= 2 then
            ctx:send("말하는속 속도를 줄여줘요!")
            ctx:send("10초안에 잡담을 3번이면 자동벙어립니다!")
            s.msg = "TEMP"
            return false
        end
    else
        s.cnt = 0
        s.t = now
    end

    -- 검사 2: 누적 9회
    if s.cnt >= 9 then
        ctx:send("말하는속 속도를 줄여줘요!")
        ctx:send("10분 이상 같은 잡담만 하면 자동벙어립니다!")
        s.msg = "TEMP"
        return false
    end

    -- 검사 3: 도배 (4초 내 4회)
    table.insert(s.q, now)
    if #s.q > 4 then table.remove(s.q, 1) end
    if #s.q >= 4 and now - s.q[1] <= 4 then
        ctx:send("말하는속 속도를 줄여줘요!")
        return false
    end

    s.msg = message
    return true
end


-- ================================================================
-- 말 (say) — 같은 방 전체
-- 원본: command2.c:609 say()
-- 출력: \n이름: {cyan}"내용"{white}
-- ================================================================
register_command("말", function(ctx, args)
    if not args or args == "" then
        ctx:send("무슨 말을 하시렵니까?")
        return
    end
    -- send_room 은 Python에서 \r\n 자동 추가
    local msg = string.format('%s: {cyan}"%s"{white}', ctx.char.name, args)
    ctx:send(msg)
    ctx:send_room(msg)
end)


-- ================================================================
-- 귓속말/이야기 (send) — 1:1 개인 메시지
-- 원본: command4.c:429 send()
-- 발신: 이름에게에 {bright_white}"내용"{white}라는 메세지를 보냈습니다
-- 수신: \n이름의 메세지: {bright_white}"내용"{white}
-- ================================================================
local function do_tell(ctx, args)
    if not args or args == "" then
        ctx:send("누구에게 메세지를 보냅니까?")
        return
    end

    local target_name, msg = args:match("^(%S+)%s+(.+)$")
    if not target_name then
        ctx:send("누구에게 메세지를 보냅니까?")
        return
    end
    if not msg or msg == "" then
        ctx:send("보내실 메세지의 내용인데요?")
        return
    end

    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("누구에게 메세지를 보냅니까?")
        return
    end

    -- 발신자 확인 메시지
    ctx:send(string.format('%s에게에 {bright_white}"%s"{white}라는 메세지를 보냈습니다',
        target.name, msg))
    ctx:send('대답을 하고싶은 땐 그 뒤에 {bright_white}/{white} 를 누이면 됩니다')

    -- 수신자 메시지
    ctx:send_to(target, string.format('\r\n%s의 메세지: {bright_white}"%s"{white}',
        ctx.char.name, msg))

    -- reply 대상 저장
    _G._3eyes_reply[target.name] = ctx.char.name
end

register_command("얘기", do_tell)
register_command("이야기", function(ctx, args) ctx:call_command("얘기", args or "") end)


-- ================================================================
-- 대답 (resend/reply) — 마지막 귓속말에 답장
-- 원본: comm12.c:85 resend()
-- "/" 또는 "대답" 명령어
-- ================================================================
local function do_reply(ctx, args)
    local target_name = _G._3eyes_reply[ctx.char.name]
    if not target_name then
        ctx:send("그 분은 접속중이 아닙니다")
        return
    end

    if not args or args == "" then
        ctx:send("보내실 건요?")
        return
    end

    local target = ctx:find_player(target_name)
    if not target then
        ctx:send("그 분은 접속중이 아닙니다")
        return
    end

    -- 발신자 확인
    ctx:send(string.format('%s에게에 {bright_white}"%s"{white}라는 메세지를 보냈습니다',
        target.name, args))

    -- 수신자 메시지
    ctx:send_to(target, string.format('\r\n%s의 메세지: {bright_white}"%s"{white}',
        ctx.char.name, args))

    -- 상호 reply 갱신
    _G._3eyes_reply[target.name] = ctx.char.name
end

register_command("/", do_reply)
register_command("대답", function(ctx, args) ctx:call_command("/", args or "") end)


-- ================================================================
-- 잡담 (broadsend/gossip) — 전체 서버 방송
-- 원본: command4.c:727 broadsend()
-- 출력: {bright_red}[이름] 내용 (방번호){reset}
-- 레벨 15+ 필요, 안티스팸 3중 검사
-- ================================================================
local function do_gossip(ctx, args)
    if not args or args == "" then
        ctx:send("무엇이라고 하는 건가요?")
        return
    end
    if ctx.char.level < 15 then
        ctx:send("레벨 15 이하는 잡담이 불가합니다.")
        return
    end
    if not spam_check(ctx, args) then return end

    local room_vnum = ctx.char.room_vnum or 0
    local msg = string.format('\r\n{bright_red}[%s] %s (%d){reset}',
        ctx.char.name, args, room_vnum)
    ctx:send_all(msg)
end

register_command("잡담", do_gossip)
register_command("잡", function(ctx, args) ctx:call_command("잡담", args or "") end)


-- ================================================================
-- 환호 (broadsend2/cheer) — 전체 서버 방송
-- 원본: command4.c:816 broadsend2()
-- 출력: {bright_green}이름님이 "내용"{bright_green}라며 환호를을 올립니다. (방번호){reset}
-- 레벨 15+ 필요, 안티스팸 공유
-- ================================================================
register_command("환호", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 환호하시렵니까요?")
        return
    end
    if ctx.char.level < 15 then
        ctx:send("레벨 부족으로 환호는 불가능 합니다.")
        return
    end
    if not spam_check(ctx, args) then return end

    local room_vnum = ctx.char.room_vnum or 0
    local msg = string.format(
        '\r\n{bright_green}%s님이 "%s"{bright_green}라며 환호를을 올립니다. (%d){reset}',
        ctx.char.name, args, room_vnum)
    ctx:send_all(msg)
end)


-- ================================================================
-- 대화 (talk) — NPC 대화
-- 원본: command8.c:788 talk()
-- 키워드 없이: NPC 기본 대화 텍스트
-- 키워드 있을 때: NPC talk 키워드 매칭
-- ================================================================
register_command("대화", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구에게 이야기하시렵니까?")
        return
    end

    local parts = {}
    for w in args:gmatch("%S+") do table.insert(parts, w) end
    local target_name = parts[1]
    local keyword = parts[2]

    local target = ctx:find_char(target_name)
    if not target then
        ctx:send("그런 사람 여기 없습니다.")
        return
    end

    local npc_name = target.short_desc or target.name or "누군가"
    local np = particle_iga(npc_name)
    local cp = particle_iga(ctx.char.name)

    if not keyword then
        -- 키워드 없이 기본 대화
        ctx:send_room(string.format('%s%s %s에게 이야기를 합니다.',
            ctx.char.name, cp, npc_name))

        local talk_text = nil
        pcall(function()
            if target.proto and target.proto.ext then
                local ext = target.proto.ext
                if type(ext) == "table" and ext.talk then
                    talk_text = ext.talk
                elseif type(ext) == "string" then
                    local ok2, parsed = pcall(require("json" or "cjson").decode, ext)
                    if ok2 and parsed and parsed.talk then
                        talk_text = parsed.talk
                    end
                end
            end
        end)

        if talk_text and talk_text ~= "" then
            ctx:send(string.format('%s%s 당신에게 "%s"라고 이야기합니다.',
                npc_name, np, talk_text))
            ctx:send_room(string.format('%s%s %s에게 "%s"라고 이야기합니다.',
                npc_name, np, ctx.char.name, talk_text))
        else
            local msg = string.format('%s%s 아무 관심도 없다는 바라봅니다.',
                npc_name, np)
            ctx:send(msg)
            ctx:send_room(msg)
        end
    else
        -- 키워드 기반 대화
        ctx:send_room(string.format('%s%s %s에게 "%s"에 대해 묻습니다.',
            ctx.char.name, cp, npc_name, keyword))

        local response = nil
        pcall(function()
            if target.proto and target.proto.ext then
                local ext = target.proto.ext
                if type(ext) == "table" and ext.talks then
                    for _, t in pairs(ext.talks) do
                        if t.key == keyword then
                            response = t.response
                            break
                        end
                    end
                end
            end
        end)

        if response then
            ctx:send(string.format('%s%s 당신에게 "%s"라고 이야기합니다.',
                npc_name, np, response))
            ctx:send_room(string.format('%s%s %s에게 "%s"라고 이야기합니다.',
                npc_name, np, ctx.char.name, response))
        else
            ctx:send(string.format('%s%s 당신을 무시 꺼려합니다.', npc_name, np))
        end
    end
end)


-- ================================================================
-- 그룹말 (gtalk) — 파티 채팅
-- 원본: comm10.c:259 gtalk()
-- 출력: 그룹말(이름): {bright_cyan}내용{white}
-- 별칭: 그룹말, 무리말, =
-- ================================================================
local function do_gtalk(ctx, args)
    local followers = ctx:get_followers()
    local has_group = false
    if followers then
        for i = 0, 50 do
            local ok, m = pcall(function() return followers[i] end)
            if not ok or not m then break end
            has_group = true
            break
        end
    end
    if not has_group then
        ctx:send("당신은 그룹에 속한 것이 않습니다.")
        return
    end

    if not args or args == "" then
        ctx:send("그룹원들에게 하실 건요?")
        return
    end

    local msg = string.format('그룹말(%s): {bright_cyan}%s{white}',
        ctx.char.name, args)
    ctx:send(msg)
    if followers then
        for i = 0, 50 do
            local ok, m = pcall(function() return followers[i] end)
            if not ok or not m then break end
            if m ~= ctx.char then
                pcall(function() ctx:send_to(m, '\r\n' .. msg) end)
            end
        end
    end
end

register_command("그룹말", do_gtalk)
register_command("무리말", function(ctx, args) ctx:call_command("그룹말", args or "") end)
register_command("=", function(ctx, args) ctx:call_command("그룹말", args or "") end)


-- ================================================================
-- 표현 (emote) — 감정표현
-- 원본: comm11.c:34 emote()
-- 자신: {cyan}:이름이(가) 내용.{white}
-- 같은방: :이름이(가) 내용.
-- ================================================================
register_command("표현", function(ctx, args)
    if not args or args == "" then
        ctx:send("표현하실 건요?")
        return
    end

    local p = particle_iga(ctx.char.name)
    ctx:send(string.format('{cyan}:%s%s %s.{white}', ctx.char.name, p, args))
    ctx:send_room(string.format(':%s%s %s.', ctx.char.name, p, args))
end)


-- ================================================================
-- 따라가기 (follow)
-- ================================================================
register_command("따라", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 따라가시겠습니까?")
        return
    end
    local target = ctx:find_char(args)
    if not target then
        ctx:send("그런 사람을 찾을 수 없습니다.")
        return
    end
    if target == ctx.char then
        ctx:unfollow()
        ctx:send("혼자 다닙니다.")
        return
    end
    ctx:follow(target)
    ctx:send(target.name .. "을(를) 따라갑니다.")
end)


-- ================================================================
-- 그룹 (group) — 파티 목록
-- ================================================================
register_command("그룹", function(ctx, args)
    local ch = ctx.char
    local followers = ctx:get_followers()
    local lines = {"{bright_cyan}-- 그룹원 --{reset}"}
    lines[#lines + 1] = string.format("  %s (레벨 %d, HP %d/%d)",
        ch.name, ch.level, ch.hp, ch.max_hp)
    if followers then
        for i = 0, 50 do
            local ok, m = pcall(function() return followers[i] end)
            if not ok or not m then break end
            lines[#lines + 1] = string.format("  %s (레벨 %d, HP %d/%d)",
                m.name, m.level, m.hp, m.max_hp)
        end
    end
    ctx:send(table.concat(lines, "\r\n"))
end)

register_command("무리", function(ctx, args) ctx:call_command("그룹", args or "") end)


-- ================================================================
-- 내보내 (lose/unfollow) — 따라오는 자를 내보냄
-- 원본: command5.c lose()
-- ================================================================
register_command("내보내", function(ctx, args)
    if not args or args == "" then
        ctx:send("누구를 내보내시겠습니까?")
        return
    end
    local ch = ctx.char
    local followers = ctx:get_followers()
    if not followers then
        ctx:send("따라오는 사람이 없습니다.")
        return
    end
    local target_name = args:lower()
    for i = 0, 50 do
        local ok, m = pcall(function() return followers[i] end)
        if not ok or not m then break end
        if m.name:lower():find(target_name, 1, true) then
            ctx:unfollow_target(m)
            ctx:send(m.name .. "을(를) 내보냈습니다.")
            pcall(function() ctx:send_to(m, ch.name .. "이(가) 당신을 내보냈습니다.") end)
            return
        end
    end
    ctx:send("그런 사람이 따라오고 있지 않습니다.")
end)


-- ================================================================
-- 듣기거부 / 수신거부 (ignore) — 특정 플레이어 메시지 차단
-- 원본: comm12.c ignore()
-- player_data: "ignore_list" = {name1, name2, ...}
-- ================================================================
local function do_ignore(ctx, args)
    local ignore_list = ctx:get_player_data("ignore_list") or {}
    if type(ignore_list) ~= "table" then ignore_list = {} end

    if not args or args == "" then
        -- 목록 표시
        local lines = {"{bright_cyan}━━ 수신거부 목록 ━━{reset}"}
        local count = 0
        for _, name in ipairs(ignore_list) do
            lines[#lines + 1] = "  " .. name
            count = count + 1
        end
        if count == 0 then
            lines[#lines + 1] = "  수신거부 대상이 없습니다."
        end
        lines[#lines + 1] = "{bright_cyan}━━━━━━━━━━━━━━━━━━{reset}"
        ctx:send(table.concat(lines, "\r\n"))
        return
    end

    local target_name = args
    -- 이미 있으면 해제
    for i, name in ipairs(ignore_list) do
        if name:lower() == target_name:lower() then
            table.remove(ignore_list, i)
            ctx:set_player_data("ignore_list", ignore_list)
            ctx:send("{green}" .. target_name .. "의 수신거부를 해제했습니다.{reset}")
            return
        end
    end
    -- 추가
    if #ignore_list >= 20 then
        ctx:send("{yellow}수신거부 목록이 가득 찼습니다. (최대 20명){reset}")
        return
    end
    ignore_list[#ignore_list + 1] = target_name
    ctx:set_player_data("ignore_list", ignore_list)
    ctx:send("{green}" .. target_name .. "을(를) 수신거부합니다.{reset}")
end

register_command("듣기거부", do_ignore)
register_command("수신거부", function(ctx, args) ctx:call_command("듣기거부", args or "") end)
