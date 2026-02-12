# GenOS tbaMUD-KR 엔진 구현 보고서

**Phase A-1 완료 | 2026-02-12 (아키텍처 리팩토링 v2)**

---

## 1. 개요

GenOS 마이그레이션 도구의 출력물(21 SQL 테이블 + 8 Lua 스크립트)을 **무수정 소비**하여
한국어 MUD 게임서버를 구현한 Phase A-1 (tbaMUD-KR) 구현 결과를 보고한다.

| 항목 | 수치 |
|------|------|
| 엔진 코어 (Python) | 11 모듈, 4,584줄 |
| 게임 로직 (Lua) | 18 파일, 4,322줄 (common 1,228 + tbamud 3,094) |
| 게임 플러그인 (Python) | 6 파일, 958줄 (최소 브릿지) |
| 테스트 코드 | 34 파일, 8,572줄 |
| 테스트 수 | **640개** (전체 통과) |
| Lua 명령어 | **99종** (Python 명령어 0종) |
| 설정 파일 | 5 파일 (YAML, Dockerfile, docker-compose, pyproject) |

### 기술 스택

- Python 3.12 + asyncio (단일 스레드 이벤트 루프)
- PostgreSQL 16 + asyncpg (비동기 커넥션 풀)
- FastAPI + uvicorn (REST API + WebSocket, 단일 포트 8080)
- lupa (Lua 5.4, 명령어/전투/스킬 런타임 — **웹 에디터 실시간 수정 가능**)
- watchfiles (개발 모드 핫 리로드)
- bcrypt (비밀번호 해싱)

### 아키텍처 원칙

> **엔진은 최소한. 기능은 플러그인식으로 추가 가능. 기능 코드는 Lua로 작성하여 웹 화면에서 개발자가 실시간 수정 가능하게 한다.**

- `core/` 디렉토리에 `games.*` import **0건** — 완전한 게임 무관성
- 모든 명령어/전투/스킬은 **Lua 스크립트**로 구현 (DB `lua_scripts` 테이블 저장)
- 게임 플러그인(Python)은 프로토콜 브릿지 역할만 수행 (81줄)
- Lua 핫 리로드: 관리자 `reload` 명령 또는 REST API로 무중단 갱신

---

## 2. 프로젝트 구조

```
genos-engine/
├── core/                            # 엔진 코어 (11 모듈, 4,584줄) — 게임 무관
│   ├── engine.py          (1,226줄)  # 게임 루프 + 명령어 디스패처 + NPC AI
│   ├── lua_commands.py    (1,132줄)  # Lua↔Python 브릿지 (CommandContext)
│   ├── world.py             (725줄)  # Prototype/Instance 월드 모델
│   ├── session.py           (420줄)  # 로그인 상태 머신 + 캐릭터 저장/복원
│   ├── api.py               (295줄)  # REST API + WebSocket
│   ├── net.py               (265줄)  # Telnet 서버 (asyncio)
│   ├── db.py                (232줄)  # asyncpg 커넥션 풀
│   ├── ansi.py              (112줄)  # {컬러코드} → ANSI 이스케이프
│   ├── korean.py             (85줄)  # 받침 기반 조사 자동 선택
│   ├── reload.py             (48줄)  # 핫 리로드 매니저
│   └── watcher.py            (44줄)  # watchfiles 파일 감지
│
├── games/common/lua/                # 공용 Lua 명령어 (6 파일, 1,228줄)
│   ├── lib.lua              (70줄)  # 공용 유틸리티
│   ├── commands/core.lua   (468줄)  # look, who, say, tell 등 기본 명령어
│   ├── commands/items.lua  (285줄)  # get, drop, wear, remove, give, put, eat, drink
│   ├── commands/position.lua(171줄) # sit, rest, stand, sleep, wake
│   ├── commands/doors.lua  (124줄)  # open, close, lock, unlock
│   └── commands/combat_core.lua(110줄) # kill, flee
│
├── games/tbamud/                    # tbaMUD-KR 플러그인 (Python 958줄 + Lua 3,094줄)
│   ├── game.py              (81줄)  # GamePlugin (프로토콜 브릿지만)
│   ├── combat/
│   │   ├── spells.py       (345줄)  # 스펠 데이터 정의
│   │   ├── thac0.py        (213줄)  # THAC0 데이터 테이블
│   │   └── death.py        (175줄)  # 사망/부활 핸들러
│   ├── shops.py            (219줄)  # 상점 시스템
│   ├── triggers.py         (227줄)  # DG Script 트리거
│   ├── level.py            (144줄)  # 레벨/경험치
│   └── lua/                         # Lua 게임 로직 (12 파일, 3,094줄)
│       ├── combat/
│       │   ├── thac0.lua   (243줄)  # THAC0 전투 라운드 (combat_round 훅)
│       │   ├── spells.lua  (388줄)  # 34 스펠 시스템 (cast 명령)
│       │   ├── skills.lua  (234줄)  # backstab, bash, kick, rescue
│       │   ├── level.lua    (61줄)  # 레벨업 알림
│       │   └── death.lua    (28줄)  # 사망 처리 훅
│       └── commands/
│           ├── info.lua    (841줄)  # score, time, weather, prompt, toggle, practice 등
│           ├── admin.lua   (392줄)  # goto, load, purge, stat, set, reload, shutdown 등
│           ├── comm.lua    (254줄)  # gossip, follow, group
│           ├── stealth.lua (187줄)  # sneak, hide
│           ├── shops.lua   (175줄)  # buy, sell, list, appraise
│           ├── items.lua   (174줄)  # tbaMUD 전용 아이템 확장
│           └── movement.lua(117줄)  # 이동 확장 (enter, leave)
│
├── data/tbamud/                     # 마이그레이션 출력 (무수정 소비)
│   ├── sql/schema.sql                # DDL 20 테이블
│   ├── sql/seed_data.sql             # INSERT ~16MB
│   ├── lua/                          # 8 Lua 스크립트
│   └── messages/system.yaml          # 한글 시스템 메시지 10 카테고리
│
├── config/tbamud.yaml               # 게임 서버 설정
├── tests/                           # 640 테스트 (34 파일, 8,572줄)
├── Dockerfile                       # Multi-stage 빌드
├── docker-compose.yml               # PostgreSQL + 게임 서버
└── pyproject.toml                   # 빌드/의존성 정의
```

---

## 3. 스프린트별 구현 내용

### Sprint 1: 기반 구축 (91 테스트)

| 모듈 | 내용 |
|------|------|
| `core/db.py` | asyncpg 커넥션 풀, DB 자동 초기화 (schema.sql + seed_data.sql), 플레이어 CRUD |
| `core/world.py` | Prototype/Instance 패턴 (RoomProto→Room, MobProto→MobInstance, ItemProto→ObjInstance), 21 테이블 전체 로드 |
| `core/net.py` | asyncio Telnet 서버, IAC 처리, UTF-8/EUC-KR 자동 감지 |
| `core/session.py` | SessionState 상태 머신, 신규/기존 로그인, bcrypt, 클래스 선택 |
| `core/engine.py` | 10Hz 게임 루프, tick 구조, 5분 자동 저장, graceful shutdown |
| `core/reload.py` | importlib.reload 큐, tick 경계 안전 적용 |
| `core/watcher.py` | watchfiles 자동 감지 (개발 모드) |
| `core/ansi.py` | `{red}`/`{bright_cyan}` → ANSI 이스케이프 변환, 16/256/트루컬러 |
| `core/korean.py` | `has_batchim()`, `particle()`, `render_message()` — 6종 조사 자동 선택 |

### Sprint 2: 핵심 게임플레이 (51 테스트)

| 기능 | 상세 |
|------|------|
| **명령어 디스패처** | 7단계 해석: alias → 초성 → SOV → SVO → 어간추출 → prefix → social |
| **한국어 파서** | 65개 동사 매핑, `_extract_korean_stem()` 어미 제거, 초성 약칭(ㄱ~ㅎ) |
| **이동** | 6방향 + look + door(open/close/lock/unlock) + exits |
| **아이템** | get/drop/wear/remove/equipment, 18슬롯 장착 |
| **정보/통신** | who/score/time, say/tell/shout/whisper, help |
| **소셜** | 4가지 메시지 변형 ($n/$N 치환), DB 로드 104개 |

**명령어 해석 전략 (7단계):**
```
1. Alias 확장 (1 레벨, 최대 20개)
2. 초성 약칭 (ㄱ→공격, ㅂ→봐, ㅅ→소지품)
3. SOV 시도: 마지막 토큰=명령어 ("고블린 공격")
4. SVO 시도: 첫 토큰=명령어 ("attack goblin")
5. 한국어 어간 추출 ("저장해라"→"저장"→save)
6. Prefix 매칭 ("sco"→score)
7. Social 명령어 검색
```

### Sprint 3: 전투 시스템 (97 테스트)

| 기능 | 상세 |
|------|------|
| **THAC0 전투** | 4클래스 × 35레벨 테이블, 힘/민첩 보너스, 15종 공격 타입 |
| **전투 라운드** | 2초 주기 (20 tick), 멀티어택 (전사 L10/L20, NPC 10레벨당 1회) |
| **20 스펠** | 공격 6종, 회복 3종, 버프 4종, 디버프 4종, 유틸 3종 |
| **사망/부활** | NPC: 제거+경험치, PC: 경험치 패널티+시작방 부활(HP 50%) |
| **레벨/경험치** | 4클래스 × 32레벨 경험치 테이블, HP/마나 증가, 체력 보너스 |
| **어펙트** | 75초 주기 tick, 지속시간 감소, 독 데미지 |

**대미지 심각도 메시지:**
```
0:     빗나갔습니다
1-2:   긁었습니다
3-5:   약하게 때렸습니다
6-10:  때렸습니다
11-15: 강하게 때렸습니다
16-20: 매우 강하게 때렸습니다
21-30: 치명적으로 때렸습니다
31+:   파괴적으로 때렸습니다
```

### Sprint 4: 게임 시스템 (28 테스트)

| 기능 | 상세 |
|------|------|
| **상점** | buy/sell/list/appraise, 가격 배율, 영업시간, 상시 재고 + 상인 인벤토리 |
| **확장 스펠 14종** | earthquake, dispel, summon, charm, remove curse/poison, group heal/armor, infravision, waterwalk, teleport, enchant weapon |
| **where** | 같은 Zone 내 플레이어/몹 위치 표시 |
| **consider** | 대상 레벨 비교 (8단계 난이도 평가) |

### Sprint 5: 스크립팅 + 관리 (66 테스트)

| 기능 | 상세 |
|------|------|
| **DG Script 트리거** | lupa Lua 런타임, 16종 트리거 타입, 8종 엔진 API |
| **관리자 명령어 9종** | goto, load, purge, stat, set, reload, shutdown, advance, restore |
| **REST API** | GET /api/who, /api/stats, /api/room/{vnum}, POST /api/reload |
| **WebSocket** | /ws 엔드포인트, WebSocketSession 어댑터 |

**트리거 엔진 API (Lua→Python):**
| API | 기능 |
|-----|------|
| `send_to_char(id, msg)` | 캐릭터에게 메시지 전송 |
| `send_to_room(vnum, msg)` | 방 전체에 메시지 전송 |
| `get_variable(ctx, name)` | DG Script 변수 읽기 |
| `set_variable(ctx, name, val)` | DG Script 변수 쓰기 |
| `teleport(id, vnum)` | 캐릭터 순간이동 |
| `damage(id, amount)` | 데미지 적용 |
| `heal(id, amount)` | 회복 (max_hp 캡) |
| `force_command(id, cmd)` | 명령어 강제 실행 |

### Sprint 6: 안정화 + 통합 (40 테스트)

| 기능 | 상세 |
|------|------|
| **한글 메시지** | system.yaml 10개 카테고리, ~60개 메시지 키 |
| **Docker** | Multi-stage Dockerfile + docker-compose (PostgreSQL 16 + 게임 서버) |
| **통합 테스트** | E2E 시나리오 40종 (이동/look/아이템/상점/전투/한국어/관리자/소셜) |

### Sprint 7: Lua 전환 + NPC AI + 95% Fidelity

| 기능 | 상세 |
|------|------|
| **Lua 명령어 전환** | Python 명령어 99종 → 전부 Lua로 재구현 (Python 0종) |
| **Python 명령어 삭제** | `games/tbamud/commands/` 전체 삭제 (~964줄) |
| **game.py 최소화** | 306줄 → 81줄 (프로토콜 브릿지만 보유) |
| **engine.py 정화** | core/ 내 `from games.*` import 0건 달성 |
| **NPC AI** | scavenger, wander, aggressive, memory, helper, wimpy (6종 행동) |
| **장비 스탯 적용** | wear/remove 시 hitroll/damroll/AC 자동 재계산 |
| **캐릭터 저장 강화** | 장비/인벤토리/스킬/경험치/어펙트 전체 저장/복원 |
| **소셜 완성** | $n/$N/$m/$M/$e/$E/$s/$S 전체 치환 |
| **give/put/eat/drink** | 컨테이너, 음식/음료 소비 |
| **클래스 스킬** | backstab(도적), bash/kick/rescue(전사), sneak/hide(도적) |

### 아키텍처 리팩토링 상세

**변경 전 (v1)**:
- engine.py에 tbaMUD 전용 로직 혼재 (combat_round Python 폴백, do_cast 100줄 등)
- `from games.tbamud.combat.spells import tick_affects` 등 5곳 직접 import
- Python 명령어 파일 5개 (admin.py, info.py, items.py, comm.py, movement.py)

**변경 후 (v2)**:
- engine.py에서 모든 `games.*` import 제거 → **0건**
- `_combat_round()`: Lua 훅 전용 (plugin.combat_round > lua hook > 안전 폴백)
- `do_cast()`, `do_practice()`: 3줄 Lua 위임
- `_regen_char()`: plugin.regen_char() 훅 패턴
- `_tick_char_affects()`: 게임 무관 generic 구현
- `KOREAN_VERB_MAP`: `_DEFAULT_KOREAN_VERB_MAP` + plugin.korean_verb_map() 확장

**삭제된 파일** (~1,992줄):
| 파일 | 줄 수 | 사유 |
|------|-------|------|
| `games/tbamud/commands/admin.py` | 274 | Lua `admin.lua`로 대체 |
| `games/tbamud/commands/info.py` | 415 | Lua `info.lua`로 대체 |
| `games/tbamud/commands/items.py` | 182 | Lua `items.lua`로 대체 |
| `games/tbamud/commands/comm.py` | 52 | Lua `comm.lua`로 대체 |
| `games/tbamud/commands/movement.py` | 41 | Lua `movement.lua`로 대체 |
| `tests/test_sprint5_admin.py` | 437 | 삭제된 코드 테스트 |

---

## 4. 명령어 체계 총괄

### 등록된 명령어: 99종 (전부 Lua)

| 카테고리 | 영문 명령어 | 한국어 매핑 | 수 | 파일 |
|----------|------------|------------|-----|------|
| 이동/방향 | north, south, east, west, up, down | 북, 남, 동, 서, 위, 아래 + 축약 | 6 | core.lua |
| 정보 | look, exits, who, score, help, commands, time, weather, examine, consider, where, prompt, toggle | 봐, 출구, 누구, 점수, 도움, 명령어, 시간, 날씨, 조사, 평가, 어디 | 13 | core.lua, info.lua |
| 아이템 | get, take, drop, wear, wield, remove, equipment, give, put, eat, drink | 줍, 버려, 입, 벗, 장비, 줘, 넣, 먹, 마셔 | 11 | items.lua |
| 통신 | say, tell, shout, whisper, gossip | 말, 귓말, 외쳐, 속삭여, 잡담 | 5 | core.lua, comm.lua |
| 전투 | kill, attack, flee, cast, practice | 죽이, 공격, 떠나, 시전, 연습 | 5 | combat_core.lua, spells.lua, info.lua |
| 스킬 | backstab, bash, kick, rescue, sneak, hide | 뒤치기, 밀치기, 차기, 구출, 은신, 숨기 | 6 | skills.lua, stealth.lua |
| 포지션 | rest, sit, stand, sleep, wake | 쉬, 앉, 서, 자 | 5 | position.lua |
| 상점 | buy, sell, list, appraise | 사, 팔, 목록, 감정 | 4 | shops.lua |
| 문 | open, close, lock, unlock | 열, 닫, 잠가, 풀 | 4 | doors.lua |
| 시스템 | quit, save, alias, inventory, i | 나가기, 저장, 별칭, 소지품 | 5 | core.lua |
| 이동확장 | enter, leave, follow, group | 들어가, 나와, 따라가, 무리 | 4 | movement.lua, comm.lua |
| 관리자 | goto, load, purge, stat, set, reload, shutdown, advance, restore | — | 9 | admin.lua |

**모든 명령어가 Lua 스크립트**이므로 DB `lua_scripts` 테이블에 저장되며,
웹 에디터에서 실시간 수정 후 `reload` 명령으로 무중단 갱신 가능.

**한국어 동사 매핑**: 65+ 항목 (SOV 어순 + 어간 추출 포함, plugin 확장 가능)

---

## 5. 스펠 시스템

### 34종 스펠 목록

| ID | 영문 | 한국어 | 타입 | 마나 |
|----|------|--------|------|------|
| 1 | Magic Missile | 마법 화살 | 공격 | 15 |
| 2 | Burning Hands | 불타는 손 | 공격 | 20 |
| 3 | Chill Touch | 냉기의 손길 | 공격 | 15 |
| 4 | Lightning Bolt | 번개 | 공격 | 25 |
| 5 | Fireball | 화염구 | 공격 | 30 |
| 6 | Color Spray | 색채 분사 | 공격 | 20 |
| 7 | Cure Light | 가벼운 치료 | 회복 | 10 |
| 8 | Cure Critic | 심각한 치료 | 회복 | 20 |
| 9 | Heal | 치료 | 회복 | 40 |
| 10 | Armor | 갑옷 | 방어버프 | 10 |
| 11 | Bless | 축복 | 방어버프 | 10 |
| 12 | Strength | 힘 강화 | 자기버프 | 15 |
| 13 | Invisibility | 투명 | 자기 | 15 |
| 14 | Sanctuary | 보호막 | 방어버프 | 30 |
| 15 | Blindness | 실명 | 디버프 | 25 |
| 16 | Curse | 저주 | 디버프 | 30 |
| 17 | Poison | 독 | 디버프 | 20 |
| 18 | Sleep | 수면 | 디버프 | 25 |
| 19 | Detect Invis | 투명 감지 | 자기 | 10 |
| 20 | Word of Recall | 귀환 | 유틸 | 10 |
| 21 | Earthquake | 지진 | 공격 | 25 |
| 22 | Dispel Evil | 악 퇴치 | 공격 | 30 |
| 23 | Dispel Good | 선 퇴치 | 공격 | 30 |
| 24 | Summon | 소환 | 유틸 | 40 |
| 25 | Locate Object | 물체 탐지 | 유틸 | 20 |
| 26 | Charm | 매혹 | 디버프 | 50 |
| 27 | Remove Curse | 저주 해제 | 회복 | 25 |
| 28 | Remove Poison | 해독 | 회복 | 20 |
| 29 | Group Heal | 집단 치료 | 회복 | 60 |
| 30 | Group Armor | 집단 갑옷 | 방어버프 | 30 |
| 31 | Infravision | 적외선 시야 | 자기 | 10 |
| 32 | Waterwalk | 수면 보행 | 자기 | 15 |
| 33 | Teleport | 순간이동 | 유틸 | 50 |
| 34 | Enchant Weapon | 무기 마법부여 | 유틸 | 100 |

---

## 6. 데이터 규모 (마이그레이션 출력)

| 데이터 | 수량 |
|--------|------|
| 방 (rooms) | 12,700 |
| 아이템 (items) | 4,765 |
| 몬스터 (monsters) | 3,705 |
| 존 (zones) | 189 |
| 상점 (shops) | 334 |
| 도움말 (help) | 721 |
| 직업 (classes) | 4 |
| 스킬 (skills) | 54 |
| 소셜 (socials) | 104 |
| 트리거 (triggers) | 1,461 |
| 게임 설정 (configs) | 54 |

---

## 7. 한국어 지원 상세

### 입력 처리

1. **SOV 어순 파서**: "고블린 공격" → kill goblin
2. **SVO 폴백**: "attack goblin" → kill goblin
3. **어간 추출**: "저장해라" → "저장" → save
4. **초성 약칭**: ㄱ→공격, ㅂ→봐, ㅅ→소지품 등 10개
5. **Prefix 매칭**: "sco" → score (유일 매칭 시)

### 출력 처리

- **받침 기반 조사 선택**: 6종 (이/가, 을/를, 은/는, 과/와, 으로/로, 이다/다)
- **ㄹ 받침 특수 처리**: "으로/로" → ㄹ 받침은 "로" (예: "물로")
- **render_message()**: 템플릿 `{target}을(를) 공격합니다` → 받침 자동 판별

### 시스템 메시지 (system.yaml)

| 카테고리 | 메시지 수 | 예시 |
|----------|----------|------|
| login | 11 | 환영 문구, 직업 선택, 비밀번호 |
| system | 5 | 종료 경고, 저장, 재접속 |
| movement | 4 | 출구 없음, 문 닫힘/잠김 |
| combat | 6 | 명중/빗나감, 사망, 경험치 |
| items | 6 | 줍기/버리기/착용/벗기 |
| communication | 5 | 말/귓말/외침/속삭임 |
| shop | 10 | 구매/판매/부족/영업시간 |
| admin | 9 | 권한/goto/reload/shutdown |
| spell | 5 | 시전/대상/마나/귀환 |
| position | 8 | 앉기/쉬기/서기/잠자기 |
| error | 4 | 미인식/미발견/허공 |

---

## 8. 아키텍처

### 게임 루프 (10Hz)

```
┌──────────────────────────────────────┐
│             10Hz Tick Loop            │
├──────────┬───────────────────────────┤
│ 매 tick  │ 핫 리로드 적용             │
│ 20 tick  │ 전투 라운드 (2초) — Lua 훅 │
│ 100 tick │ NPC AI (10초)             │
│ 750 tick │ 어펙트 tick (75초)         │
│ 600 tick │ Zone 리셋 체크 (60초)      │
│ 자동저장  │ 5분 주기                  │
└──────────┴───────────────────────────┘
```

### 5계층 아키텍처 (Lua-first)

```
Client (Telnet/WebSocket)
    ↓
Network (core/net.py, core/api.py)
    ↓
Session/Command (core/session.py, core/engine.py)
    ↓                      ↓
Lua Runtime            Plugin Protocol
(core/lua_commands.py)  (games/*/game.py)
    ↓                      ↓
Game Logic (games/*/lua/*.lua) ← 웹 에디터 수정 가능
    ↓
Persistence (core/db.py → PostgreSQL)
```

### 핵심 원칙: 엔진 최소화

| 원칙 | 검증 결과 |
|------|----------|
| core/ 내 games.* import | **0건** |
| Python 명령어 | **0종** |
| Lua 명령어 | **99종** |
| game.py 크기 | **81줄** (프로토콜만) |
| 게임 로직 Lua 비율 | **100%** |

### Plugin Protocol

```python
class GamePlugin:
    def welcome_banner() -> str          # 접속 배너
    def register_commands(engine)        # (no-op, Lua가 전담)
    def handle_death(engine, victim, killer)  # 사망 처리
    def playing_prompt(engine, session) -> str  # 프롬프트
    def regen_char(engine, char)         # 클래스별 리젠 (선택)
    def korean_verb_map() -> dict        # 한국어 매핑 확장 (선택)
```

### 핫 리로드

- **Lua 스크립트**: `reload` 명령 또는 REST API → 무중단 즉시 갱신
- `games/` Python: importlib.reload (tick 경계에서 안전 적용)
- `core/` Python: 서버 재시작 필요
- watchfiles 자동 감지 (개발), 관리자 `reload` 명령 (운영)

### Zone 리셋

7종 리셋 명령어 처리:
- **M**: 몹 스폰 (max_existing 체크)
- **O**: 오브젝트 배치
- **G**: 몹 인벤토리에 아이템
- **E**: 몹 장비 착용
- **P**: 컨테이너에 아이템
- **D**: 문 상태 설정
- **T**: 트리거 부착

---

## 9. 배포

### Docker Compose

```yaml
services:
  postgres:   # PostgreSQL 16-alpine, healthcheck
  tbamud:     # Python 3.12-slim, multi-stage build
```

| 포트 | 용도 |
|------|------|
| 4000 | Telnet 게임 접속 |
| 8080 | REST API + WebSocket |

### DB 자동 초기화

서버 최초 부팅 시:
1. `rooms` 테이블 존재 확인
2. 없으면 `schema.sql` → `seed_data.sql` 자동 실행
3. `players` 테이블 별도 보장

---

## 10. 테스트 요약

| 카테고리 | 테스트 수 | 대상 |
|----------|----------|------|
| 코어 인프라 (ansi/db/net/reload/session/watcher/world) | ~63 | 엔진 코어 모듈 |
| 한국어 (korean) | 17 | 받침, 조사, 메시지 렌더링 |
| Sprint 2: 명령어/파서 | ~51 | 명령어 디스패치, 한국어, 포지션, 도어 |
| Sprint 3: 전투 | ~97 | THAC0, 스펠, 사망, 레벨 |
| Sprint 4: 상점/확장 | ~28 | 상점, 확장 스펠 |
| Sprint 5: 트리거/API | ~32 | DG Script, REST API |
| Sprint 6: E2E 통합 | ~40 | 통합 시나리오 |
| Lua 프레임워크 | ~48 | LuaCommandRuntime, CommandContext |
| Lua 전투 | ~40 | combat_round 훅, cast, practice |
| 10woongi | ~140 | 시그마 전투, 직업, 스킬 |
| 엔진 통합 | ~84 | 엔진 루프, NPC AI, 명령어 |
| **합계** | **640** | **34 파일, 8,572줄** |

---

## 11. 주요 기술 이슈 및 해결

### Python 바운드 메서드 비교 불가

**문제**: `handler is self._direction_handler`가 항상 `False` (Python이 바운드 메서드를 매번 새로 생성)

**해결**: `_DIRECTION_SENTINEL = object()` 클래스 속성으로 sentinel 객체 사용

### async 콜백 필수

**문제**: `do_level_up(char, send_fn=lambda m: msgs.append(m))` → TypeError (await 불가)

**해결**: `send_fn`은 반드시 async 함수여야 함. `async def capture(m): msgs.append(m)` 사용

### World.create_mob() 인자

**문제**: `create_mob(vnum)` 호출 시 `room_vnum` 누락

**해결**: `create_mob(vnum, room_vnum)` — room_vnum은 필수 인자. 내부에서 방에 자동 배치

### Lua↔Python 상호운용

**문제**: Lua에서 Python list의 `#` 연산자 사용 불가, dict 접근시 nil 오류

**해결**: `ctx:get_inv_count()` 등 래퍼 메서드 제공, `pcall` 감싸기 패턴 사용

### 사망 처리 비동기 문제

**문제**: Lua에서 직접 사망 처리시 async 호출 불가 + 컬렉션 수정 충돌

**해결**: `ctx:defer_death(victim, killer)` → Python `execute_deferred()`에서 `plugin.handle_death()` 호출

### engine.py 게임 종속성 제거

**문제**: core/engine.py에 `from games.tbamud.*` import 5곳 → 다른 게임에서 재사용 불가

**해결**: 모든 게임 로직을 plugin 훅 또는 Lua 훅으로 위임. `getattr(self, "_plugin", None)` 안전 접근 패턴

---

## 12. 향후 계획

| Phase | 내용 | 상태 |
|-------|------|------|
| A-1 | tbaMUD-KR (Lua-first 아키텍처) | **완료** (640 테스트) |
| A-2 | 10woongi-KR (시그마 전투) | **완료** (Lua + Python 플러그인) |
| A-3 | Simoon-KR | 플러그인 등록 완료, 게임 로직 미착수 |
| A-4 | 3eyes-KR | 플러그인 등록 완료, 게임 로직 미착수 |
| A-5~7 | muhan13, murim, 99hunter | 미착수 |
| B | 프레임워크 추출 | 미착수 |
| C | 웹 디자이너 + 게임 생성 마법사 | 미착수 |

**현재 아키텍처**:
- `core/` = 게임 무관 인프라 (4,584줄, `games.*` import 0건)
- `games/*/lua/` = 웹 에디터에서 실시간 편집 가능한 게임 로직
- `games/*/game.py` = 최소 프로토콜 브릿지 (50~93줄)

Phase A-5~7은 각 게임의 플러그인 + Lua 스크립트를 추가하는 것만으로 구현 가능.
Phase B에서 공용 패턴을 더 추출하고, Phase C에서 웹 기반 게임 디자이너 도구를 구축.
