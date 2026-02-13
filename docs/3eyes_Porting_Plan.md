# 3eyes MUD 완전 이식 — 단계별 실행 계획

**Phase A-3 | 2026-02-13 | 상태: 진행 중**

---

## 현재 구현 현황 요약

### 이미 구현된 것 (이식 전 기반)

| 파일 | 줄수 | 내용 |
|------|------|------|
| `game.py` | 107 | Plugin protocol, regen, prompt |
| `login.py` | 418 | 로그인 상태머신 |
| `level.py` | 137 | 경험치 테이블 201레벨, 레벨업 |
| `constants.py` | 452 | 클래스/종족/플래그/쿨다운/숙련도 테이블 |
| `combat/death.py` | 212 | 사망처리, 시체, 경험치 배분, 숙련도 |
| `lua/lib.lua` | 407 | profic/mprofic/thaco/comp_chance/spell_fail/dice |
| `lua/combat/thac0.lua` | 438 | 전투 라운드 (다중공격/크리티컬/그림자) |
| `lua/combat/spells.lua` | 250 | cast/practice (26공격+36유틸 정의) |
| `lua/commands/combat.lua` | 164 | kill, flee, search |
| `lua/commands/comm.lua` | 456 | say/tell/yell/gsay/broadcast/emote 등 |
| `lua/commands/info.lua` | 206 | score/who/equipment/inventory |
| `lua/commands/items.lua` | 426 | get/drop/put/give/wear/wield/remove/eat/drink |
| `lua/commands/shops.lua` | 105 | buy/sell/list/appraise |
| `lua/commands/skills.lua` | 296 | bash/kick/trip/berserk/rescue |
| `lua/commands/stealth.lua` | 156 | sneak/hide/pick/steal/backstab |
| `lua/commands/movement.lua` | 173 | open/close/enter/scan/title |
| `lua/commands/admin.lua` | 128 | goto/transfer/shutdown 등 ~10개 |
| `lua/commands/map.lua` | 93 | ASCII 지도 |

**총 ~40개 명령어 구현 완료** (목표 356개 중 약 11%)

---

## 단계별 실행 계획

### Step 1: 마법 시스템 원본 충실 재작성 ⬜
> `spells.lua` 재작성 — offensive_spell() 원본 공식 복원

**목표**: 62개 주문 전체의 원본 충실 효과 구현

**작업 내용**:
1. **offensive_spell() 원본 공식 복원** (magic1.c:819-1050)
   - bonus_type 1/2/3 분기 (INT + mprofic/realm)
   - 방 영역 보너스 (같은 영역 2배, 반대 영역 역보너스)
   - 영역 대립쌍: WATER↔FIRE, WIND↔EARTH
   - spell_fail() 검사 + 마나 차감
   - 영역 숙련도 자동 성장 (addrealm)
2. **cast() 원본 흐름** (magic1.c:24-129)
   - spllist[] 부분일치 + PBLIND/RNOMAG 검사
   - LT_SPELL 쿨다운 (클래스별 3~5초, 특수주문 추가)
   - PHIDDN 해제
3. **유틸리티 주문 36개 효과 구현**
   - buff: 플래그 설정 + 지속시간 쿨다운 연동
   - heal: 활력(+15), 치료(+30), 회복(+50), 대치료(+100)
   - cure: 해독(PPOISN), 질병치료(PDISEA), 실명치료(PBLIND), 저주해제(OCURSE)
   - debuff: 공포(PFEARS), 실명(PBLIND), 침묵(PSILNC), 매혹(PCHARM)
   - teleport/recall/summon/transport/locate/track
   - 방활력(room_vigor): 방 전체 HP+20
   - 마법부여(enchant): 무기 adjustment+1
   - 강화(upgrade): 장비 업그레이드
4. **teach/study 시스템** (magic1.c)
   - teach: 주문을 다른 플레이어에게 가르치기
   - study: NPC에게서 주문 배우기

**수정 파일**: `lua/combat/spells.lua` (재작성)

---

### Step 2: 전투 시스템 보강 ⬜
> NPC AI + 결혼 파워 + 무기파손/드롭 실체화

**목표**: thac0.lua에 누락된 원본 전투 로직 보완

**작업 내용**:
1. **NPC AI 시스템** (creature.c + tick 훅)
   - MAGGRE: 비전투 중 NPC가 방에 있는 플레이어 자동 공격
   - MFLEER: HP < 20%일 때 도주 (현재 기본 구현 → 개선)
   - MMAGIC: 전투 중 랜덤 공격 주문 시전
2. **결혼 파워** (command5.c:350-360)
   - 배우자가 같은 방에 있으면 데미지 2배
3. **무기 파손 실체화** (command5.c:249-258)
   - shots_remaining < 1 → 무기 해제 + 인벤토리/방 드롭
   - shots_remaining 감소 (25% 확률/타격)
4. **무기 떨어뜨림 실체화** (command5.c:333-345)
   - unequip + 방 바닥 드롭
5. **flee 원본 공식** (creature.c check_for_flee)
   - 도주 성공 확률: DEX 기반
   - 경험치 패널티

**수정 파일**: `lua/combat/thac0.lua`, `game.py` (NPC AI tick)

---

### Step 3: 경제 시스템 ⬜
> 은행 + 경매 + 상점 원본 충실

**목표**: bank.c, kyk1.c 완전 이식 + shops.lua 재작성

**작업 내용**:
1. **은행** (bank.c) → `lua/commands/economy.lua`
   - 입금(deposit) / 출금(withdraw) / 잔고확인(balance)
   - 보관함(locker): 아이템 맡기기/찾기 (최대 10개)
   - 온라인 송금(transfer): 접속 중인 다른 플레이어에게
   - RBANK 방 플래그 검사
2. **경매** (kyk1.c) → `lua/commands/economy.lua`
   - 경매시작(auction) / 입찰(bid) / 경매종료(sold)
   - 전역 경매 채널 (전체 채팅)
   - 최저가/최고가 제한
3. **상점 원본 충실** (command7.c buy/sell/list/value/repair)
   - buy: 재고 검사 + 가격 계산 (buy_profit 반영)
   - sell: sell_profit 반영 + 아이템 타입 제한
   - list: 상점 인벤토리 표시 (가격 포함)
   - value: 판매 예상가 표시
   - repair: RREPAI 방에서 무기 수리 (shots 복구)
   - trade: 아이템 교환

**신규 파일**: `lua/commands/economy.lua`
**수정 파일**: `lua/commands/shops.lua` (재작성)

---

### Step 4: 커뮤니티 시스템 ⬜
> 게시판 18개 + 가족(길드) + 결혼

**목표**: board.c, kyk6.c, comm11.c 완전 이식

**작업 내용**:
1. **게시판 18개** (board.c) → `lua/commands/board.lua`
   - 글쓰기(write) / 보기(read) / 삭제(delete) / 목록(list)
   - DB `boards` + `board_posts` 테이블 활용
   - 게시판별 접근 권한 (DM 전용, 가족 전용 등)
   - 새 글 알림 (접속 시)
2. **가족(길드) 시스템** (kyk6.c) → `lua/commands/family.lua`
   - 가족생성(fcreate) / 해체(fdisband)
   - 가족가입(fjoin) / 탈퇴(fleave) / 추방(fkick)
   - 가족채팅(ftalk) / 가족목록(flist) / 가족정보(finfo)
   - 가족방(RFAMIL) 접근 제한
   - DB `organizations` 테이블 활용
3. **결혼** (comm11.c, kyk3.c) → `lua/commands/social.lua`
   - 청혼(propose) / 수락(accept) / 결혼식(marry)
   - 이혼(divorce)
   - RMARRI 방에서만 결혼식 가능
   - 결혼 효과: 같은 방에서 데미지 2배 (전투 연동)

**신규 파일**: `lua/commands/board.lua`, `lua/commands/family.lua`, `lua/commands/social.lua`

---

### Step 5: 성장 시스템 ⬜
> 전직 + 숙련도 자동성장 + 특수 훈련

**목표**: command7.c train, power/meditate/accurate 완전 이식

**작업 내용**:
1. **전직 시스템** (command7.c train) → `lua/commands/training.lua`
   - 전직 경로: 일반 lv200 → Invincible → Caretaker → Care_II → Care_III
   - 전직 조건: RTRAIN 방 + 경험치(aim_exp) + 골드 + 60초 쿨다운
   - Invincible 특성: HP/MP dice 3배, THAC0 [-5,10], 경험치 5배
   - Caretaker 특성: HP+2000, MP+900, THAC0 [-10,0], 경험치 25배
   - Care_II/III: 필요경험치 = hpmax*1500 + mpmax*1000
   - `level.py` 수정: Invincible/Caretaker 레벨업 공식 반영
2. **숙련도 자동성장 확인**
   - 무기숙련: 이미 thac0.lua에서 처리 (addprof)
   - 영역숙련: spells.lua에서 addrealm 추가 (Step 1)
3. **특수 훈련 명령어**
   - power: 공격력 임시 부스트 (60초 쿨다운)
   - meditate: MP 회복 부스트 (60초 쿨다운)
   - accurate: 명중률 임시 부스트 (60초 쿨다운)

**신규 파일**: `lua/commands/training.lua`
**수정 파일**: `level.py`, `game.py`

---

### Step 6: 기타 시스템 ⬜
> 제련 + 포커 + 킬러/PK + 순위 + 별명

**목표**: 특수 컨텐츠 완전 이식

**작업 내용**:
1. **제련** (command7.c forge) → `lua/commands/forge.lua`
   - RFORGE 방에서 무기/방어구 강화
   - 성공/실패/파괴 확률 (레벨 + 클래스 기반)
   - 60초 쿨다운 (LT_FORGE)
2. **포커** (poker.c, poker2.c) → `lua/commands/poker.lua`
   - RPOKER 방에서만 가능
   - 참가(join) / 베팅(bet) / 콜(call) / 폴드(fold) / 쇼다운(show)
   - 5장 카드, 패 판정 (원페어~로열스트레이트플러쉬)
3. **킬러/PK 시스템** (kyk1.c, kyk5.c) → `lua/commands/misc.lua`
   - PCHAOS 플래그 + RSUVIV 방
   - 킬러 감옥 (RKILLR) 이송
   - PK 카운트 + 페널티
4. **순위** (kyk7.c, rank.c) → `lua/commands/ranking.lua`
   - 레벨/경험치/무술 순위 표시
   - 실시간 순위 계산
5. **별명** (alias.c) → `lua/commands/misc.lua`
   - 별명 설정/해제/목록
   - player_data에 저장

**신규 파일**: `lua/commands/forge.lua`, `lua/commands/poker.lua`, `lua/commands/ranking.lua`
**수정 파일**: `lua/commands/misc.lua`

---

### Step 7: DM(관리자) 명령어 ⬜
> dm1-6.c 약 60개 명령어 이식

**목표**: 관리자 도구 완전 이식

**작업 내용**:
1. **월드 관리**: create/destroy room/mob/obj, set room/mob/obj attrs
2. **플레이어 관리**: advance, set level/class/stats, ban, jail, freeze
3. **텔레포트**: goto, transfer, teleport, at
4. **정보**: stat room/mob/obj/player, where, zstat, sstat
5. **시스템**: shutdown, reboot, purge, reload, force
6. **가시성**: invis, visible, snoop, switch
7. **존 관리**: zedit, zreset, zsave

**수정 파일**: `lua/commands/admin.lua` (대폭 확장)

---

### Step 8: 방 특수효과 + NPC 특수행동 + info 확장 ⬜
> 방 플래그 효과 + NPC 스크립트 + 출력 정비

**목표**: 원본 세계 시뮬레이션 완성

**작업 내용**:
1. **방 특수효과** (game.py tick)
   - RHEALR: 자동 HP 회복
   - RPHARM: HP 감소
   - RPPOIS: 중독 부여
   - RPMPDR: MP 감소
   - RDARKR/RDARKN: 어둠 (look 제한, 빛 필요)
2. **NPC 특수행동**
   - 상점 NPC: 자동 인사, 물건 추천
   - 가드 NPC: 킬러 자동 공격
   - 퀘스트 NPC: 대화 트리거
3. **info 명령어 확장** (info.lua 재작성)
   - score: 숙련도/영역 백분율 + 전직 상태 + 가족 + 결혼
   - who: 클래스 표시 개선 (전직 등급 포함)
   - equipment: 슬롯별 한글 표시
   - time/weather: 원본 시간/날씨 시스템
4. **ANSI 색상 GenOS 변환 확인**
   - 원본 3eyes는 ANSI ESC 코드 직접 사용
   - GenOS `{color}` 포맷으로 통일 확인

**수정 파일**: `game.py`, `lua/commands/info.lua` (재작성), `lua/commands/movement.lua`

---

## 진행 상태 추적

| Step | 이름 | 상태 | 완료일 |
|------|------|------|--------|
| 1 | 마법 시스템 원본 충실 재작성 | ✅ 완료 | 2026-02-14 |
| 2 | 전투 시스템 보강 | ✅ 완료 | 2026-02-14 |
| 3 | 경제 시스템 | ✅ 완료 | 2026-02-14 |
| 4 | 커뮤니티 시스템 | ✅ 완료 | 2026-02-14 |
| 5 | 성장 시스템 | ✅ 완료 | 2026-02-14 |
| 6 | 기타 시스템 | ✅ 완료 | 2026-02-14 |
| 7 | DM 명령어 | ✅ 완료 | 2026-02-14 |
| 8 | 방 특수효과 + 출력 정비 | ✅ 완료 | 2026-02-14 |

---

## 명령어 추적 — 209개 구현 완료

### 파일별 분포 (21개 Lua 파일)
| 파일 | 명령어 수 | 주요 내용 |
|------|-----------|-----------|
| admin.lua | 38 | DM 명령어 (*감옥, *강제, *소환, *정보 등) |
| overrides.lua | 35 | 기본 명령어 재정의 (look, score, who 등) |
| comm.lua | 16 | 통신 (say, tell, yell, gsay, broadcast 등) |
| items.lua | 15 | 아이템 (get, drop, wear, eat, drink 등) |
| family.lua | 13 | 가문 시스템 (fcreate, fjoin, ftalk 등) |
| poker.lua | 12 | 포커 게임 (join, bet, call, fold 등) |
| combat.lua | 9 | 전투 (kill, flee, bash, kick 등) |
| info.lua | 9 | 정보 (score, who, equipment 등) |
| shops.lua | 8 | 상점 (buy, sell, list, value, repair, trade) |
| movement.lua | 7 | 이동 (방향, open, close, enter) |
| economy.lua | 7 | 경제 (bank, auction, bid) |
| spells.lua | 6 | 마법 (cast, teach, study) — 62개 스펠 |
| misc.lua | 6 | 기타 (chaos, alias, color 등) |
| skills.lua | 6 | 스킬 (bash, kick, trip, backstab 등) |
| social.lua | 5 | 결혼 (propose, accept, marry, divorce) |
| stealth.lua | 5 | 은신 (sneak, hide, pick, steal) |
| board.lua | 4 | 게시판 18개 (write, read, delete, blist) |
| training.lua | 4 | 성장 (train, power, meditate, accurate) |
| forge.lua | 2 | 제련 (forge) |
| map.lua | 1 | 지도 |
| ranking.lua | 1 | 랭킹 |

**총 209개 register_command** (한국어 명령어 + 영어 별칭 포함)
