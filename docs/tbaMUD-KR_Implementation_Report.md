# GenOS tbaMUD-KR 엔진 구현 보고서

**Phase A-1 완료 | 2026-02-11**

---

## 1. 개요

GenOS 마이그레이션 도구의 출력물(21 SQL 테이블 + 8 Lua 스크립트)을 **무수정 소비**하여
한국어 MUD 게임서버를 구현한 Phase A-1 (tbaMUD-KR) 구현 결과를 보고한다.

| 항목 | 수치 |
|------|------|
| 소스 코드 | 27 파일, 5,146줄 |
| 테스트 코드 | 22 파일, 4,607줄 |
| 테스트 수 | **373개** (전체 통과) |
| 설정 파일 | 5 파일 (YAML, Dockerfile, docker-compose, pyproject) |
| 개발 기간 | Sprint 1~6 (12주 설계) |

### 기술 스택

- Python 3.12 + asyncio (단일 스레드 이벤트 루프)
- PostgreSQL 16 + asyncpg (비동기 커넥션 풀)
- FastAPI + uvicorn (REST API + WebSocket, 단일 포트 8080)
- lupa (Lua 5.4, DG Script 트리거 런타임)
- watchfiles (개발 모드 핫 리로드)
- bcrypt (비밀번호 해싱)

---

## 2. 프로젝트 구조

```
genos-engine/
├── core/                          # 엔진 코어 (10 모듈, 3,271줄)
│   ├── engine.py        (1,503줄)  # 메인 게임 루프 + 명령어 디스패처
│   ├── world.py           (535줄)  # Prototype/Instance 월드 모델
│   ├── session.py         (289줄)  # 로그인 상태 머신
│   ├── api.py             (219줄)  # REST API + WebSocket
│   ├── net.py             (197줄)  # Telnet 서버 (asyncio)
│   ├── db.py              (163줄)  # asyncpg 커넥션 풀
│   ├── ansi.py            (112줄)  # {컬러코드} → ANSI 이스케이프
│   ├── korean.py           (85줄)  # 받침 기반 조사 자동 선택
│   ├── reload.py           (48줄)  # 핫 리로드 매니저
│   └── watcher.py          (34줄)  # watchfiles 파일 감지
│
├── games/tbamud/                  # tbaMUD-KR 게임 플러그인 (1,875줄)
│   ├── game.py             (33줄)  # GamePlugin 등록
│   ├── commands/
│   │   ├── admin.py       (274줄)  # 관리자 명령어 9종
│   │   ├── items.py       (183줄)  # 아이템 명령어 10종
│   │   ├── info.py        (108줄)  # 정보 명령어 5종
│   │   ├── comm.py         (52줄)  # 통신 명령어 3종
│   │   └── movement.py     (37줄)  # 이동 명령어 4종
│   ├── combat/
│   │   ├── spells.py      (345줄)  # 34 스펠 시스템
│   │   ├── thac0.py       (213줄)  # THAC0 전투 엔진
│   │   └── death.py       (128줄)  # 사망/부활 시스템
│   ├── shops.py           (212줄)  # 상점 (buy/sell/list/appraise)
│   ├── triggers.py        (227줄)  # DG Script Lua 런타임
│   └── level.py           (133줄)  # 레벨/경험치 시스템
│
├── data/tbamud/                   # 마이그레이션 출력 (무수정 소비)
│   ├── sql/schema.sql              # DDL 20 테이블
│   ├── sql/seed_data.sql           # INSERT ~16MB
│   ├── lua/                        # 8 Lua 스크립트
│   └── messages/system.yaml        # 한글 시스템 메시지 10 카테고리
│
├── config/tbamud.yaml             # 게임 서버 설정
├── tests/                         # 373 테스트 (22 파일)
├── Dockerfile                     # Multi-stage 빌드
├── docker-compose.yml             # PostgreSQL + 게임 서버
└── pyproject.toml                 # 빌드/의존성 정의
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

---

## 4. 명령어 체계 총괄

### 등록된 명령어: 72종+

| 카테고리 | 영문 명령어 | 한국어 매핑 | 수 |
|----------|------------|------------|-----|
| 이동/방향 | north, south, east, west, up, down | 북, 남, 동, 서, 위, 아래 + 축약 | 6 |
| 정보 | look, l, exits, who, score, help, commands, time, weather, examine, consider, where | 봐, 출구, 누구, 점수, 도움, 명령어, 시간, 날씨, 조사, 평가, 어디 | 12 |
| 아이템 | get, take, drop, wear, wield, remove, equipment, eq, give, put | 줍, 버려, 입, 벗, 장비, 줘, 넣 | 10 |
| 통신 | say, tell, shout, whisper | 말, 귓말, 외쳐, 속삭여 | 4 |
| 전투 | kill, attack, flee, cast, practice | 죽이, 공격, 떠나, 시전, 연습 | 5 |
| 포지션 | rest, sit, stand, sleep, wake | 쉬, 앉, 서, 자 | 5 |
| 상점 | buy, sell, list, appraise | 사, 팔, 목록, 감정 | 4 |
| 문 | open, close, lock, unlock | 열, 닫, 잠가, 풀 | 4 |
| 시스템 | quit, save, alias, inventory, i | 나가기, 저장, 별칭, 소지품 | 5 |
| 이동확장 | enter, leave, follow, group | 들어가, 나와, 따라가, 무리 | 4 |
| 관리자 | goto, load, purge, stat, set, reload, shutdown, advance, restore | — | 9 |

**한국어 동사 매핑**: 65개 항목 (SOV 어순 + 어간 추출 포함)

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
┌─────────────────────────────────────┐
│             10Hz Tick Loop           │
├──────────┬──────────────────────────┤
│ 매 tick  │ 핫 리로드 적용            │
│ 20 tick  │ 전투 라운드 (2초)         │
│ 750 tick │ 어펙트 tick (75초)        │
│ 600 tick │ Zone 리셋 체크 (60초)     │
│ 자동저장  │ 5분 주기                 │
└──────────┴──────────────────────────┘
```

### 5계층 아키텍처

```
Client (Telnet/WebSocket)
    ↓
Network (core/net.py, core/api.py)
    ↓
Session/Command (core/session.py, core/engine.py)
    ↓
Game Logic (games/tbamud/*)
    ↓
Persistence (core/db.py → PostgreSQL)
```

### 핫 리로드

- `games/` 디렉토리: importlib.reload (tick 경계에서 안전 적용)
- `core/` 디렉토리: 서버 재시작 필요
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

| 파일 | 테스트 수 | 대상 |
|------|----------|------|
| test_ansi.py | 10 | ANSI 컬러 변환 |
| test_db.py | 6 | DB 연결/초기화 |
| test_engine.py | 7 | 명령어 디스패치, 이동, Zone 리셋 |
| test_korean.py | 17 | 받침, 조사, 메시지 렌더링 |
| test_net.py | 6 | Telnet 프로토콜 |
| test_reload.py | 4 | 핫 리로드 |
| test_session.py | 6 | 로그인 상태 머신 |
| test_watcher.py | 2 | 파일 감지 |
| test_world.py | 12 | 월드 모델, 주사위 |
| test_sprint2_*.py | 51 | 명령어 파서, 한국어, 포지션 |
| test_sprint3_*.py | 97 | 전투, 스펠, 사망, 레벨, 엔진 통합 |
| test_sprint4_*.py | 28 | 상점, 확장 스펠 |
| test_sprint5_*.py | 66 | 트리거, 관리자, API |
| test_sprint6_integration.py | 40 | E2E 통합 시나리오 |
| **합계** | **373** | |

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

---

## 12. 향후 계획

| Phase | 내용 | 상태 |
|-------|------|------|
| A-1 | tbaMUD-KR | **완료** |
| A-2 | Simoon-KR | 미착수 |
| A-3 | 3eyes-KR | 미착수 |
| A-4 | 10woongi-KR | 미착수 |
| B | 프레임워크 추출 | 미착수 |
| C | 게임 생성 마법사 | 미착수 |

Phase A-2부터는 `games/simoon/` 디렉토리를 추가하여 동일한 `core/` 위에 게임별 플러그인을 구현한다.
Phase B에서 4개 게임의 공통 패턴을 Protocol 기반 플러그형 시스템으로 추출한다.
