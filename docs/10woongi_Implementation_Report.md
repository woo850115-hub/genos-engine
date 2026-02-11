# GenOS 10woongi (십웅기) 엔진 구현 보고서

**Phase A-2 완료 | 2026-02-11**

---

## 1. 개요

GenOS 마이그레이션 도구의 10woongi 출력물(21 SQL 테이블 + 5 Lua 스크립트)을 **무수정 소비**하여
LP-MUD/FluffOS 기반 한국어 무협 MUD 게임서버를 구현한 Phase A-2 (10woongi) 구현 결과를 보고한다.

| 항목 | 수치 |
|------|------|
| 소스 코드 | 17 파일, 1,620줄 (games/10woongi/) |
| 테스트 코드 | 10 파일, 2,667줄 |
| 테스트 수 | **196개** (전체 통과) |
| 데이터 | 22,681줄 (SQL 21,881 + Lua 704 + YAML 96) |
| 총 테스트 | **569개** (tbaMUD 373 + 10woongi 196, 전체 통과) |
| core 수정 | 4개 파일, ~35줄 (tbaMUD 완전 호환) |

### tbaMUD 대비 핵심 차이점

| 항목 | tbaMUD (Phase A-1) | 10woongi (Phase A-2) |
|------|-------------------|---------------------|
| 전투 공식 | THAC0 + dice | **Sigma 공식** + 스탯 기반 |
| 데미지 | HP만 | **HP + SP 이중 데미지** |
| 전투 라운드 | 2초 (20 tick) | **1초 (10 tick)** |
| 클래스 | 4 (고정) | **14** (4 계열 승급 체계) |
| 스킬 | 54 (spello) | **51** (기술.h 매핑) |
| 장비 슬롯 | 18 | **22** (반지 10개) |
| 스탯 | D&D 6스탯 | **무협 6스탯** (체력/민첩/지혜/기골/내공/투지) |
| 상점/트리거 | 334/1,461 | **0/0** (LPC 코드 내장) |
| VNUM 형식 | 순차 정수 | **SHA-256 해시** (31-bit) |
| 로그인 | 이름 자동 감지 | **"새로" 키워드** 기반 분기 |
| Exit JSON 키 | direction/to_room | **dir/dest** (호환 폴백) |

---

## 2. 프로젝트 구조

```
genos-engine/
├── core/                              # 엔진 코어 (10 모듈, 3,217줄) — 공유
│   ├── engine.py        (1,516줄)     # 메인 게임 루프 + 플러그인 훅
│   ├── world.py           (536줄)     # Prototype/Instance + extensions 필드
│   ├── session.py         (296줄)     # 플러그인 로그인 훅
│   ├── api.py             (219줄)     # REST API + WebSocket
│   ├── net.py             (197줄)     # Telnet 서버 (asyncio)
│   ├── db.py              (164줄)     # asyncpg + extensions JSONB
│   ├── ansi.py            (112줄)     # {컬러코드} → ANSI 이스케이프
│   ├── korean.py           (85줄)     # 받침 기반 조사 자동 선택
│   ├── reload.py           (48줄)     # 핫 리로드 매니저
│   └── watcher.py          (44줄)     # watchfiles 파일 감지
│
├── games/10woongi/                    # 10woongi 게임 플러그인 (1,620줄)
│   ├── game.py            (102줄)     # WoongiPlugin 등록 + combat/heal 훅
│   ├── constants.py       (115줄)     # 22슬롯, 14클래스, 6스탯, 키 룸
│   ├── stats.py            (57줄)     # sigma(), calc_hp/sp/mp
│   ├── login.py           (220줄)     # 7단계 로그인 상태 머신
│   ├── level.py            (81줄)     # 경험치/레벨업/클래스 승급
│   ├── commands/
│   │   ├── admin.py       (234줄)     # 관리자 명령어 7종
│   │   ├── items.py       (154줄)     # 22슬롯 착용/해제 + get/drop
│   │   ├── info.py        (107줄)     # wscore(6무협스탯), consider, equipment
│   │   ├── comm.py         (76줄)     # tell, shout, whisper
│   │   └── movement.py     (44줄)     # recall(귀환)
│   └── combat/
│       ├── skills.py      (213줄)     # 51개 기술 정의 + 사용
│       ├── sigma.py       (138줄)     # 시그마 명중/데미지 계산
│       └── death.py        (79줄)     # 사망/부활/경험치/코퍼스
│
├── data/10woongi/                     # 마이그레이션 출력 (무수정 소비)
│   ├── sql/schema.sql     (224줄)     # DDL 21 테이블
│   ├── sql/seed_data.sql (21,657줄)   # INSERT ~14MB
│   ├── lua/classes.lua    (163줄)     # 14 클래스 정의
│   ├── lua/combat.lua      (58줄)     # 전투 테이블
│   ├── lua/config.lua     (137줄)     # 게임 설정
│   ├── lua/korean_nlp.lua (132줄)     # 한글 유틸
│   ├── lua/korean_commands.lua (214줄)# 한국어 SOV 파서
│   └── messages/system.yaml (96줄)    # 한글 시스템 메시지
│
├── config/10woongi.yaml    (34줄)     # 게임 서버 설정
├── scripts/init-db.sh       (7줄)     # 멀티 DB 초기화
├── tests/test_10w_*.py    (2,667줄)   # 196 테스트 (10 파일)
├── docker-compose.yml                 # tbaMUD + 10woongi + PostgreSQL
└── Dockerfile                         # Multi-stage (GAME env 변수)
```

---

## 3. 스프린트별 구현 내용

### Sprint 1: 기반 + 월드 로드 (46 테스트)

| 모듈 | 내용 |
|------|------|
| `config/10woongi.yaml` | 포트 4001/8081, DB genos_10woongi, start_room 1392841419, combat_round 10 |
| `data/10woongi/` | 마이그레이션 출력 복사 (SQL 2 + Lua 5 + YAML 1) |
| `games/10woongi/game.py` | WoongiPlugin 스캐폴드, `create_plugin()` |
| `games/10woongi/constants.py` | 22 장비슬롯, 6 무협스탯, 14 클래스, 승급 체계, 키 룸 |
| `core/world.py` | Exit 키 호환: `dir`/`dest`/`keyword`/`desc` 폴백 |

**핵심 이슈 — 숫자 시작 패키지명:**
```python
# 불가: from games.10woongi.login import WoongiGetNameState  # SyntaxError
# 해결: importlib.import_module("games.10woongi.login")
_PKG = "games.10woongi"
def _import(submodule):
    return importlib.import_module(f"{_PKG}.{submodule}")
```
모든 10woongi 모듈에서 동일한 `_import()` 헬퍼 패턴 사용.

### Sprint 2: 시그마 스탯 + 로그인 (46 테스트)

| 기능 | 상세 |
|------|------|
| **시그마 공식** | `sigma(n) = sum(1..n-1)`, n>150이면 `sigma(150)+(n-150)*150` |
| **HP 계산** | `80 + 6*(sigma(기골)/30)` |
| **SP 계산** | `80 + (sigma(내공)*2 + sigma(지혜))/30` |
| **MP 계산** | `50 + sigma(민첩)/15` |
| **로그인 플로우** | 7단계 상태 머신 (이름 → "새로" 분기 → 비밀번호 → 성별 → 클래스 → 입장) |
| **플러그인 훅** | `get_initial_state()`, `welcome_banner()` → core/session.py에서 호출 |
| **DB 확장** | players 테이블에 `extensions JSONB` 컬럼 추가 (SP, 무협 스탯) |

**로그인 상태 머신:**
```
WoongiGetNameState
  ├─ 기존 이름 → WoongiGetPasswordState → enter_game()
  └─ "새로" → WoongiNewNameState
               → WoongiNewPasswordState
               → WoongiConfirmPasswordState
               → WoongiSelectGenderState (남1/여2)
               → WoongiSelectClassState (투사 1)
               → enter_game()
```

**players.extensions JSONB 구조:**
```json
{
  "sp": 80, "max_sp": 80,
  "stats": {"stamina":13, "agility":13, "wisdom":13,
            "bone":13, "inner":13, "spirit":13},
  "faction": null
}
```

### Sprint 3: 시그마 전투 + 사망 (34 테스트)

| 기능 | 상세 |
|------|------|
| **명중 계산** | `50 + hitroll + 투지//2 - 상대민첩//3` (5~95 범위) |
| **HP 데미지** | `weapon_dice + 체력//5 + damroll` |
| **SP 데미지** | `random(1,3) + 내공//4` (이중 데미지) |
| **NPC 사망** | `calc_adj_exp(level)` 경험치 + 골드 획득, 방에서 제거 |
| **PC 사망** | 대기실(1854941986) 텔레포트, HP/SP 25% 복원, 전투 해제 |
| **51 스킬** | 6 카테고리 (방어/공격/회복/은신/마법/유틸), SP 소모, 클래스 제한 |
| **전투 라운드** | 1초 주기 (10 tick), 플러그인 `combat_round()` 훅 |
| **힐링 틱** | HP 8%, SP 9%, MP 13% 자연 회복 |

**시그마 전투 vs THAC0 비교:**
```
tbaMUD (THAC0):  d20 ≥ THAC0[class][level] - AC  →  HP 단일 데미지
10woongi (Sigma): rand(1,100) ≤ 명중률          →  HP + SP 이중 데미지
```

**core/engine.py 플러그인 훅 패턴:**
```python
# 안전한 플러그인 접근 — Engine 미부팅 시 AttributeError 방지
plugin = getattr(self, "_plugin", None)
if plugin and hasattr(plugin, "combat_round"):
    await plugin.combat_round(self)
    return
# 폴백: 기존 tbaMUD THAC0 로직
```

### Sprint 4: 장비(22슬롯) + 레벨/승급 + 명령어 (36 테스트)

| 기능 | 상세 |
|------|------|
| **22 장비 슬롯** | 투구, 귀걸이×2, 목걸이, 갑옷, 허리띠, 팔갑, 장갑, 팔찌×2, 반지×10, 각반, 신발 |
| **반지 순차 슬롯** | 9→13→14→15→16→17→18→19→20→21 (10개 순차 채움) |
| **14 클래스 승급** | 투사→전사→기사→상급기사, 사제→성직자→아바타, 도둑→사냥꾼→암살자, 마술사→마법사→시공술사 |
| **경험치 공식** | `level² × 100 + level × 500` |
| **명령어 29종** | 5개 모듈 (admin, items, info, comm, movement) |
| **한국어 매핑** | 주워/놔/착용/벗/챙기/정보/판별/장비/귓/외치/속삭이/귀환 |

**22 장비 슬롯 맵:**
```
 1: 투구        2: 귀걸이1      3: 목걸이      4: 갑옷
 5: 허리띠      6: 팔갑         7: 장갑        8: 팔찌1
 9: 반지1      10: 각반        11: 신발       12: 귀걸이2
13: 반지2      14: 반지3       15: 반지4      16: 반지5
17: 반지6      18: 반지7       19: 반지8      20: 반지9
21: 반지10     22: 팔찌2
```

**4대 승급 계열:**
```
투사(1) ─L30→ 전사(2) ─L60→ 기사(3) ─L90→ 상급기사(4)
사제(6) ─L30→ 성직자(7) ─L60→ 아바타(8)
도둑(9) ─L30→ 사냥꾼(10) ─L60→ 암살자(11)
마술사(12) ─L30→ 마법사(13) ─L60→ 시공술사(14)
신관기사(5): 특수 하이브리드
```

### Sprint 5: Docker + 통합 테스트 (34 테스트)

| 기능 | 상세 |
|------|------|
| **docker-compose.yml** | 10woongi 서비스 추가 (포트 4001/8081) |
| **scripts/init-db.sh** | `CREATE DATABASE genos_10woongi` 자동 생성 |
| **통합 테스트 34종** | E2E 시나리오 (이동/전투/아이템/레벨/승급/스킬/힐링/설정/Docker/호환) |
| **tbaMUD 호환성** | 기존 373 테스트 전체 통과 확인 |

---

## 4. 명령어 체계

### 등록된 명령어: 29종

| 카테고리 | 영문 명령어 | 한국어 매핑 | 수 |
|----------|------------|------------|-----|
| 아이템 | get, drop, wear, wield, remove | 주워, 놔, 착용, 챙기, 벗 | 5 |
| 정보 | wscore, consider, equipment | 정보, 판별, 장비 | 3 |
| 통신 | tell, shout, whisper | 귓, 외치, 속삭이 | 3 |
| 이동 | recall | 귀환 | 1 |
| 관리자 | goto, wload, purge, stat, wset, restore, advance | — | 7 |

**참고**: 6방향 이동(north~down), look, say 등 기본 명령어는 core/engine.py에서 처리 (공유).
10woongi 전용 명령어만 게임 플러그인에서 등록한다.

---

## 5. 스킬 시스템

### 51종 스킬 (6 카테고리)

| 카테고리 | 수 | 대표 스킬 |
|----------|-----|----------|
| **방어** (defense) | 8 | 패리L1~L3, 방패방어, 절대방어, 강철방패, 수련방어, 수정방어 |
| **공격** (attack) | 11 | 카운터L1~L2, 연타, 파이널어택, 크리티컬, 백스탭, 킥, 세컨드어택, 더블어택, 트리플어택, 파워스트라이크 |
| **회복** (recovery) | 7 | 치료L1~L3, 기도L1~L3, 집단치료 |
| **은신** (stealth) | 5 | 훔치기, 스텔스, 도주술, 은신, 잠행 |
| **마법** (magic) | 13 | 매직미셜, 파이어볼, 라이트닝볼트, 아이스스톰, 매혹, 어스퀘이크, 독 등 |
| **유틸** (utility) | 7 | 귀환술, 인첸트, 헤이스트, 소환, 요리, 감정, 플라이 |

**스킬 사용 흐름:**
```
use_skill(char, skill_id, target, send_to_char)
  ├─ SKILLS dict에서 skill 조회
  ├─ SP 소모 (char.move -= sp_cost)
  ├─ 카테고리별 효과 적용
  │   ├─ attack: calc_attack_skill_damage → target.hp 감소
  │   ├─ recovery: calc_heal_amount → target.hp 회복
  │   ├─ magic: calc_magic_damage → target.hp 감소
  │   └─ stealth/utility: 카테고리별 특수 효과
  └─ 결과 메시지 전송
```

---

## 6. 데이터 규모 (마이그레이션 출력)

| 데이터 | 수량 |
|--------|------|
| 방 (rooms) | 17,590 |
| 아이템 (items) | 969 |
| 몬스터 (monsters) | 947 |
| 존 (zones) | 122 |
| 상점 (shops) | 0 (LPC 내장) |
| 도움말 (help) | 72 |
| 직업 (classes) | 14 |
| 스킬 (skills) | 51 |
| 명령어 (commands) | 51 |
| 트리거 (triggers) | 0 (LPC 내장) |
| 게임 설정 (configs) | 98 |

### tbaMUD vs 10woongi 데이터 비교

| 항목 | tbaMUD | 10woongi | 비고 |
|------|--------|----------|------|
| 방 | 12,700 | **17,590** | 10woongi 38% 더 큼 |
| 아이템 | 4,765 | 969 | tbaMUD 5배 |
| 몬스터 | 3,705 | 947 | tbaMUD 4배 |
| 존 | 189 | 122 | |
| 상점 | 334 | 0 | LP-MUD는 코드 내장 |
| 트리거 | 1,461 | 0 | LP-MUD는 코드 내장 |
| 직업 | 4 | **14** | 10woongi 3.5배 |
| 스킬 | 54 | 51 | 비슷 |
| 설정 | 54 | **98** | 10woongi 전투/스탯 설정 다수 |

---

## 7. 핵심 VNUM 체계

10woongi는 LPC 파일 경로의 SHA-256 해시를 31-bit 정수로 변환하여 VNUM으로 사용한다.
일반적인 순차 정수(1~12700)와 달리, **10억 단위의 큰 정수**가 VNUM이 된다.

| 용도 | VNUM | 방 이름 |
|------|------|---------|
| 시작방 (START_ROOM) | 1,392,841,419 | 장백성 마을 광장 |
| 대기실 (VOID_ROOM) | 1,854,941,986 | 대기실 |
| 냉동실 (FREEZER_ROOM) | 1,958,428,208 | 접속 끊긴 사람이 오는 냉동실 |

**VNUM 호환 보장**: Python `dict`는 큰 정수 키도 O(1) 접근을 보장하므로,
기존 tbaMUD의 작은 VNUM과 10woongi의 SHA-256 VNUM이 동일한 World 코드로 동작한다.

---

## 8. 무협 6스탯 시스템

### 스탯 정의

| 키 | 한국어 | 영향 범위 |
|----|--------|----------|
| stamina | 체력 | HP 데미지 보너스 |
| agility | 민첩 | MP 계산, 회피 패널티 |
| wisdom | 지혜 | SP 계산 (보조) |
| bone | 기골 | HP 계산 (주) |
| inner | 내공 | SP 계산 (주), SP 데미지 보너스 |
| spirit | 투지 | 명중률 보너스 |

### 시그마 공식 상세

```python
def sigma(n):
    """1~n-1 합. n>150이면 선형 전환."""
    if n <= 1: return 0
    if n <= 150: return n * (n - 1) // 2
    return sigma(150) + (n - 150) * 150  # 11175 + (n-150)*150

# HP = 80 + 6 * sigma(기골) / 30
# SP = 80 + (sigma(내공) * 2 + sigma(지혜)) / 30
# MP = 50 + sigma(민첩) / 15
```

**계산 예시 (기본 스탯 13):**
- sigma(13) = 78
- HP = 80 + 6 * 78 / 30 = 80 + 15 = **95**
- SP = 80 + (78*2 + 78) / 30 = 80 + 7 = **87**
- MP = 50 + 78 / 15 = 50 + 5 = **55**

---

## 9. core/ 수정 내역 (호환성 유지)

모든 core 변경은 **optional protocol 패턴**으로 구현되어, tbaMUD 373 테스트가 완전히 통과한다.

### core/world.py — Exit 키 호환 (~4줄)

```python
# 10woongi의 dir/dest 키를 tbaMUD의 direction/to_room과 통합
exits.append(Exit(
    direction=e.get("direction", e.get("dir", 0)),
    to_room=e.get("to_room", e.get("dest", -1)),
    keywords=e.get("keywords", e.get("keyword", "")),
    description=e.get("description", e.get("desc", "")),
    ...
))
# + MobInstance에 extensions 필드 추가
extensions: dict[str, Any] = field(default_factory=dict)
```

### core/engine.py — 플러그인 전투/어펙트 훅 (~15줄)

```python
# combat_round 간격 설정화 (tbaMUD=20, 10woongi=10)
combat_interval = self.config.get("engine", {}).get("combat_round", 20)

# 플러그인 우선 → 없으면 기존 tbaMUD 로직
plugin = getattr(self, "_plugin", None)
if plugin and hasattr(plugin, "combat_round"):
    await plugin.combat_round(self)
    return
```

### core/session.py — 플러그인 로그인 훅 (~10줄)

```python
# 플러그인 초기 상태
plugin = getattr(self.engine, "_plugin", None)
if plugin and hasattr(plugin, "get_initial_state"):
    self.state = plugin.get_initial_state()

# 플러그인 환영 배너
if plugin and hasattr(plugin, "welcome_banner"):
    return plugin.welcome_banner()
```

### core/db.py — players 확장 (~6줄)

```sql
extensions JSONB NOT NULL DEFAULT '{}'
```

---

## 10. 배포

### Docker Compose (멀티게임)

```yaml
services:
  postgres:    # PostgreSQL 16-alpine, 멀티 DB (init-db.sh)
  tbamud:      # GAME=tbamud, 포트 4000/8080
  10woongi:    # GAME=10woongi, 포트 4001/8081
```

| 서비스 | Telnet | API/WS | DB |
|--------|--------|--------|-----|
| tbamud | 4000 | 8080 | genos_tbamud |
| 10woongi | 4001 | 8081 | genos_10woongi |
| postgres | — | — | 5432 |

### DB 자동 초기화

```bash
# scripts/init-db.sh — PostgreSQL 초기화 시 실행
CREATE DATABASE genos_10woongi OWNER genos;
```

서버 최초 부팅 시:
1. `rooms` 테이블 존재 확인
2. 없으면 `schema.sql` → `seed_data.sql` 자동 실행
3. `players` 테이블 별도 보장 (extensions JSONB 포함)

---

## 11. 테스트 요약

### 10woongi 테스트: 196개 (10 파일)

| 파일 | 테스트 수 | 대상 |
|------|----------|------|
| test_10w_foundation.py | 34 | 설정 로드, 플러그인, 상수, 데이터 파일 |
| test_10w_world.py | 12 | Exit 키 호환, SHA-256 VNUM, dir36 |
| test_10w_stats.py | 24 | sigma 엣지 케이스, HP/SP/MP 공식 |
| test_10w_login.py | 22 | 7단계 로그인, "새로" 분기, 플러그인 훅 |
| test_10w_combat.py | 14 | 시그마 명중/데미지, 이중 데미지, 사망/부활 |
| test_10w_skills.py | 20 | 51 스킬, 카테고리, SP 소모, 클래스 제한 |
| test_10w_equip.py | 9 | 22슬롯 착용/해제, 반지 10개 순차, get/drop |
| test_10w_level.py | 14 | 경험치 공식, 레벨업, 승급 4종 |
| test_10w_commands.py | 13 | 이동/정보/통신/관리자 명령어 |
| test_10w_integration.py | 34 | E2E 전체 시나리오 (전투/아이템/레벨/Docker/호환) |

### 전체 테스트: 569개

| 게임 | 테스트 수 | 상태 |
|------|----------|------|
| tbaMUD (Phase A-1) | 373 | 전체 통과 |
| 10woongi (Phase A-2) | 196 | 전체 통과 |
| **합계** | **569** | **전체 통과** |

---

## 12. 주요 기술 이슈 및 해결

### 숫자 시작 패키지명 (`games.10woongi`)

**문제**: `from games.10woongi.login import ...` → `SyntaxError: invalid decimal literal`

**해결**: 모든 10woongi 모듈에서 `importlib.import_module()` 사용.
```python
_PKG = "games.10woongi"
def _import(submodule): return importlib.import_module(f"{_PKG}.{submodule}")
```

### MobInstance.extensions 접근 불가

**문제**: `MobInstance(slots=True)` → 임의 속성 할당 불가 (`_extensions` 등)

**해결**: MobInstance dataclass에 `extensions: dict[str, Any] = field(default_factory=dict)` 필드 명시 추가.

### 기존 tbaMUD 테스트의 _plugin AttributeError

**문제**: tbaMUD 테스트가 Engine 전체 부팅 없이 부분 생성 → `self._plugin` 미설정

**해결**: `getattr(self, "_plugin", None)` 안전 접근 패턴. plugin 없으면 기존 로직 폴백.

### MobInstance.gold/experience 기본값 0

**문제**: `MobProto.gold=50`이지만 `MobInstance.gold`는 별도 필드(기본값 0). 자동 전파 안 됨.

**해결**: 테스트/게임 로직에서 인스턴스 필드를 명시적으로 설정. 향후 Phase B에서 `create_mob()` 시 proto 값 자동 복사 검토.

### World.zones가 list (dict 아님)

**문제**: `w.zones[1] = Zone(...)` → `IndexError` (zones는 list)

**해결**: `w.zones.append(Zone(...))` 사용. MEMORY.md에 기록.

### send_to_char 2인자 시그니처

**문제**: `send_to_char(msg)` 1인자로 호출 → `perform_attack`에서는 `send_to_char(char, msg)` 2인자

**해결**: engine._send_to_char를 2인자로 통일. `char.session` 체크 후 호출하여 session 없는 NPC에는 미전송.

---

## 13. 향후 계획

| Phase | 내용 | 상태 |
|-------|------|------|
| A-1 | tbaMUD-KR | **완료** (373 테스트) |
| A-2 | 10woongi (십웅기) | **완료** (196 테스트) |
| A-3 | Simoon-KR | 미착수 |
| A-4 | 3eyes-KR | 미착수 |
| B | 프레임워크 추출 | 미착수 |
| C | 게임 생성 마법사 | 미착수 |

Phase A-3 (Simoon-KR)에서는 `games/simoon/` 디렉토리를 추가하여 동일한 `core/` 위에 게임별 플러그인을 구현한다.
Phase A-2에서 확립된 플러그인 훅 패턴(`combat_round`, `tick_affects`, `get_initial_state`)을 재사용하며,
Simoon 고유의 CircleMUD 3.0 한국어 커스텀 + EUC-KR 인코딩을 처리한다.

Phase B에서 4개 게임의 공통 패턴을 Protocol 기반 플러그형 시스템(CombatSystem, SpawnSystem, StatCalculator)으로 추출한다.
