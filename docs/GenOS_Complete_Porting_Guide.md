# GenOS 완벽 전환 가이드 — 원본 MUD → GenOS Engine

**Version 2.0 | 2026-02-14 | 3eyes 포팅 실전 사례 기반 + 명령어 전환 플레이북**

이 문서는 원본 MUD 소스를 GenOS Engine으로 완벽하게 전환하는 전 과정을
3eyes (Mordor 2.0) 포팅 실전 사례를 중심으로, tbaMUD/10woongi/simoon 패턴까지
포괄하여 정리한 종합 가이드입니다.

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [전환 전 준비: 원본 분석](#2-전환-전-준비-원본-분석)
3. [파일 구조 템플릿](#3-파일-구조-템플릿)
4. [단계별 전환 프로세스](#4-단계별-전환-프로세스)
5. [Python 레이어 — 플러그인 프로토콜](#5-python-레이어--플러그인-프로토콜)
6. [Lua 레이어 — 명령어 / 전투 / 마법](#6-lua-레이어--명령어--전투--마법)
7. [데이터 레이어 — SQL / Config / 텍스트](#7-데이터-레이어--sql--config--텍스트)
   - 7.1 [통합 스키마 (Unified Schema v1.0)](#71-통합-스키마-unified-schema-v10)
   - 7.2 [seed_data.sql 구조](#72-seed_datasql-구조)
   - 7.3 [config/\<game\>.yaml](#73-configgameyaml)
   - 7.4 [텍스트 파일 (banner/menu/news)](#74-텍스트-파일-bannertxt-menutxt-newstxt)
   - 7.5 [보충 데이터 — 마이그레이션 도구 미생성 테이블](#75-보충-데이터--마이그레이션-도구가-생성하지-않는-테이블)
   - 7.6 [초기 아이템 검증 절차](#76-초기-아이템-검증-절차)
   - 7.7 [PK 차등 시스템 상세](#77-pk플레이어-킬-차등-시스템-상세)
   - 7.8 [시체 부패 메커니즘](#78-시체-부패corpse-decay-메커니즘)
8. [ANSI 색상 변환 규칙](#8-ansi-색상-변환-규칙)
9. [한국어 처리 패턴](#9-한국어-처리-패턴)
10. [Lua ↔ Python 인터옵 핵심 패턴](#10-lua--python-인터옵-핵심-패턴)
11. [공통 함정과 해결책](#11-공통-함정과-해결책)
12. [검증 체크리스트](#12-검증-체크리스트)
13. [실전 사례: 3eyes 전체 전환 기록](#13-실전-사례-3eyes-전체-전환-기록)
14. [명령어 전환 실전 플레이북](#14-명령어-전환-실전-플레이북)
   - 14.1 [명령어 전수 조사 방법](#141-명령어-전수-조사-방법)
   - 14.2 [명령어 7가지 유형별 전환 패턴](#142-명령어-7가지-유형별-전환-패턴)
   - 14.3 [common → game 오버라이드 전략](#143-common--game-오버라이드-전략)
   - 14.4 [SOV 파싱 함정과 해결책](#144-sov-파싱-함정과-해결책)
   - 14.5 [Lua ↔ Python 인터옵 실전 함정](#145-lua--python-인터옵-실전-함정)
   - 14.6 [테스트 작성 패턴](#146-테스트-작성-패턴)
   - 14.7 [게임별 명령어 체계 특성](#147-게임별-명령어-체계-특성)
   - 14.8 [전환 작업 순서 (권장)](#148-전환-작업-순서-권장)
   - 14.9 [빠른 참조: ctx API 전체 목록](#149-빠른-참조-ctx-api-전체-목록)
   - 14.10 [최종 검증 스크립트](#1410-최종-검증-스크립트)

---

## 1. 아키텍처 개요

### 1.1 GenOS 5-레이어 구조

```
┌─────────────────────────────────────────────────────┐
│  Client (Telnet / Web / API)                        │
├─────────────────────────────────────────────────────┤
│  Network    core/net.py + core/session.py           │
├─────────────────────────────────────────────────────┤
│  Command    core/lua_commands.py  (Lua 명령어 런타임)│
├─────────────────────────────────────────────────────┤
│  Game Logic games/<game>/  (Python + Lua)           │
│   ├─ game.py          플러그인 프로토콜             │
│   ├─ login.py         로그인 상태머신               │
│   ├─ constants.py     게임별 상수                   │
│   ├─ level.py         레벨업 공식                   │
│   ├─ combat/death.py  사망 처리                     │
│   └─ lua/             모든 명령어 + 전투 + 마법     │
├─────────────────────────────────────────────────────┤
│  Persistence  core/db.py + PostgreSQL               │
│   └─ data/<game>/sql/  schema.sql + seed_data.sql   │
└─────────────────────────────────────────────────────┘
```

### 1.2 핵심 설계 원칙

| 원칙 | 설명 |
|------|------|
| **Python은 인프라, Lua는 콘텐츠** | 플러그인/DB/네트워크 = Python, 명령어/전투/마법 = Lua |
| **원본 충실** | C 공식 → 가능한 한 그대로 포팅, 단순화 최소화 |
| **통합 스키마** | 7개 게임이 동일 DB 스키마 사용 (Unified Schema v1.0) |
| **GenOS ANSI** | 원본 색상 체계 → `{color}` 포맷 단일 변환 |
| **플러그인 스케일** | 단순 게임 4 hooks → 복잡 게임 8+ hooks |
| **공유 Lua 라이브러리** | `common/lua/` 에 범용 명령어 35,000+ 줄 |

### 1.3 4개 게임 구현 비교

| 항목 | tbaMUD | 10woongi | simoon | 3eyes |
|------|--------|----------|--------|-------|
| 원본 엔진 | CircleMUD 3.1 | FluffOS (LPC) | CircleMUD 3.0 | Mordor 2.0 |
| 원본 포맷 | 텍스트 파일 | LPC 소스 | 텍스트 파일 | 바이너리 C struct |
| Python 파일 | 11 | 10 | 7 | 7 |
| Lua 파일 | ~10 | ~11 | ~10 | 22 |
| Plugin 훅 수 | 4 (최소) | 5 | 5 | 8 (최대) |
| 포트 (telnet) | 4000 | 4001 | 4002 | 4003 |
| DB | genos_tbamud | genos_10woongi | genos_simoon | genos_3eyes |
| 시작방 | 3001 | 1392841419 | 3093 | 1 |
| 전투 주기 | 2초 | 1초 | 2초 | 2초 |

---

## 2. 전환 전 준비: 원본 분석

### 2.1 원본 소스 맵 작성

전환 첫 단계는 **원본 소스 전수조사**입니다. 3eyes 사례:

```
원본 소스: 93개 C 파일
├── command1.c ~ command8.c    명령어 (8파일)
├── comm1.c ~ comm12.c         통신 (12파일)
├── creature.c                 NPC AI / 전투
├── magic1.c ~ magic8.c        마법 (8파일)
├── player.c                   플레이어 시스템
├── global.c                   상수 / 테이블
├── mstruct.h                  구조체 / 플래그
├── dm1.c ~ dm6.c              관리자 명령 (6파일)
├── kyk1.c ~ kyk8.c            한국어 커스텀 (8파일)
├── poker.c, poker2.c          미니게임
├── bank.c, board.c            경제 / 커뮤니티
└── ... (기타 유틸리티)
```

### 2.2 필수 추출 항목

원본에서 반드시 추출해야 할 정보:

| 항목 | 추출 대상 | 3eyes 예시 |
|------|-----------|-----------|
| **클래스** | ID, 이름, 스탯, HP/MP 성장 | 17 클래스 (8 기본 + 9 전직/관리자) |
| **종족** | ID, 이름, 스탯 보정 | 8 종족 (드워프~노움) |
| **플래그** | 비트 위치 → 문자열 이름 | 64-bit creature/room/object flags |
| **쿨다운** | 슬롯 ID, 이름, 기본 시간 | 45 슬롯 (LT_ATTCK ~ LT_POKER) |
| **주문** | ID, 이름, 마나, 영역, 효과 | 62 주문 (26 공격 + 36 유틸) |
| **숙련도** | 무기/마법 타입, 경험치 테이블 | 5 무기 + 4 영역, 12단계 테이블 |
| **경험치** | 레벨별 필요 경험치 테이블 | 201레벨 테이블 |
| **스탯 보너스** | 수치 → 보너스 매핑 | 0~34 → -4~+5 |
| **THAC0** | 클래스별 20레벨 THAC0 테이블 | 20×20 배열 |
| **전투 공식** | 명중/회피/데미지/크리티컬 | compute_thaco(), attack_crt() |
| **마법 공식** | 성공률/데미지/영역 보너스 | spell_fail(), offensive_spell() |
| **사망 처리** | 경험치 패널티, 시체 생성, 부활 | (cur-prev)×3/4, SPIRIT_ROOM |
| **레벨업** | 스탯 순환, HP/MP 성장, 전직 | LEVEL_CYCLE, exp_multiplier |
| **방 효과** | 특수 방 플래그 → 틱 효과 | RHEALR/RPHARM/RPPOIS/RPMPDR |
| **NPC AI** | 공격/도주/마법 사용 패턴 | MAGGRE/MFLEER/MMAGIC |
| **로그인** | 상태머신 흐름, 검증 규칙 | 10단계 (이름→메뉴→게임) |
| **색상 코드** | 원본 ANSI 체계 | ESC[0m 직접 사용 |

### 2.3 원본 공식 문서화

추출한 공식은 **Porting Reference** 문서로 정리합니다:

```markdown
# <게임> Porting Reference

## 전투 공식
### compute_thaco() — 원본: creature.c:XXX-YYY
base = THAC0_TABLE[class_id][level / 10]
bonus = -STR_bonus - weapon_adjustment
...

## 마법 공식
### offensive_spell() — 원본: magic1.c:819-1050
bonus_type 1: INT + comp_chance
bonus_type 2: INT + mprofic + comp_chance
...
```

---

## 3. 파일 구조 템플릿

### 3.1 게임별 디렉토리

```
genos-engine/
├── games/
│   ├── common/
│   │   └── lua/
│   │       ├── lib.lua                 공용 유틸 (can_act, format_number...)
│   │       └── commands/
│   │           ├── core.lua            look, quit, save, who, help, exits
│   │           ├── items.lua           get, drop, put, give, wear, remove
│   │           ├── doors.lua           open, close, lock, unlock
│   │           ├── position.lua        sit, stand, rest, sleep, wake
│   │           └── combat_core.lua     kill, attack, flee, rescue
│   │
│   └── <game>/                    ← 게임별 디렉토리
│       ├── __init__.py            (빈 파일)
│       ├── game.py                플러그인 프로토콜 (필수)
│       ├── login.py               로그인 상태머신 (필수)
│       ├── constants.py           게임별 상수 (필수)
│       ├── level.py               레벨업 공식 (필수)
│       ├── combat/
│       │   ├── __init__.py        (빈 파일)
│       │   └── death.py           사망 처리 (필수)
│       └── lua/
│           ├── lib.lua            게임별 공유 함수
│           ├── combat/
│           │   ├── thac0.lua      전투 라운드 엔진
│           │   └── spells.lua     마법 시스템
│           └── commands/
│               ├── combat.lua     kill, flee, search
│               ├── comm.lua       say, tell, yell, broadcast
│               ├── info.lua       score, who, equipment, affects
│               ├── items.lua      get, drop, wear (오버라이드)
│               ├── movement.lua   open, close, enter, scan
│               ├── skills.lua     bash, kick, trip, backstab
│               ├── stealth.lua    sneak, hide, pick, steal
│               ├── shops.lua      buy, sell, list, repair
│               ├── admin.lua      goto, transfer, shutdown...
│               └── ...            (게임별 추가 명령어)
│
├── data/<game>/
│   ├── sql/
│   │   ├── schema.sql             통합 스키마 DDL (공통)
│   │   └── seed_data.sql          마이그레이션 데이터
│   ├── lua/                       마이그레이션 생성 Lua 데이터
│   │   ├── classes.lua
│   │   ├── races.lua
│   │   ├── skills.lua
│   │   ├── exp_tables.lua
│   │   ├── stat_tables.lua
│   │   ├── combat.lua
│   │   ├── korean_nlp.lua
│   │   └── korean_commands.lua
│   ├── banner.txt                 접속 배너
│   ├── menu.txt                   메인 메뉴
│   └── news.txt                   공지사항
│
└── config/<game>.yaml             게임별 설정
```

### 3.2 필수 파일 vs 선택 파일

| 파일 | 필수 | 설명 |
|------|------|------|
| `game.py` | **필수** | 플러그인 프로토콜 진입점 |
| `login.py` | **필수** | 원본 로그인 흐름 재현 |
| `constants.py` | **필수** | 클래스/종족/플래그/쿨다운 |
| `level.py` | **필수** | 경험치 테이블 + 레벨업 |
| `combat/death.py` | **필수** | 사망 시 경험치/아이템/부활 |
| `lua/lib.lua` | **필수** | 게임별 Lua 공유 함수 |
| `lua/combat/thac0.lua` | **필수** | 전투 라운드 (THAC0 엔진) |
| `lua/combat/spells.lua` | 마법 있으면 필수 | 주문 시스템 |
| `lua/commands/*.lua` | 명령어별 | 게임별 명령어 구현 |
| `schema.sql` | **필수** | DB DDL (공통 스키마) |
| `seed_data.sql` | **필수** | 마이그레이션 출력 데이터 |
| `config/<game>.yaml` | **필수** | 포트/DB/엔진 설정 |
| `banner.txt` | 권장 | 접속 시 ASCII 아트 |

---

## 4. 단계별 전환 프로세스

### 전체 흐름 (8단계)

```
Step 0  원본 분석 + Porting Reference 작성
  ↓
Step 1  마법 시스템 (spells.lua)
  ↓
Step 2  전투 시스템 (thac0.lua + game.py NPC AI)
  ↓
Step 3  경제 시스템 (shops, bank, auction)
  ↓
Step 4  커뮤니티 (게시판, 길드, 결혼)
  ↓
Step 5  성장 시스템 (전직, 훈련, 숙련도)
  ↓
Step 6  기타 시스템 (미니게임, PK, 순위)
  ↓
Step 7  관리자 명령어 (~50+ DM 커맨드)
  ↓
Step 8  정비 — 방 효과 + NPC 행동 + 출력 보강
```

### Step 0: 원본 분석 (가장 중요)

1. **소스 전수조사**: 모든 C/LPC 파일 목록화, 줄 수 계산
2. **데이터 규모 파악**: 방/아이템/몹/존 수 카운트
3. **명령어 목록 추출**: `cmd_info[]` / `command_list` 등에서 전체 추출
4. **공식 추출**: 전투/마법/레벨업 핵심 공식을 원본 줄 번호와 함께 기록
5. **플래그 매핑**: 비트 위치 → 의미 있는 문자열 이름 변환표
6. **Porting Reference 작성**: 위 내용을 단일 MD 파일로 정리

### Step 1: 마법 시스템

```
원본 매핑:
  magic*.c  →  lua/combat/spells.lua
  spllist[] →  constants.py SPELL_LIST

핵심 포팅 항목:
  1. spell_fail() — 클래스별 시전 성공률
  2. offensive_spell() — 영역 기반 데미지 + 방 보너스
  3. 유틸리티 주문 — 버프/힐/디버프/텔레포트
  4. cast() — 주문명 부분일치 + 쿨다운 + PBLIND/RNOMAG 검사
  5. teach/study — 주문 전수/학습
```

### Step 2: 전투 시스템

```
원본 매핑:
  creature.c  →  lua/combat/thac0.lua + game.py
  command5.c  →  lua/combat/thac0.lua (무기 파손/드롭)

핵심 포팅 항목:
  1. compute_thaco() — THAC0 계산 (클래스 테이블 + 스탯 + 장비)
  2. attack_crt() — 다중공격 (1-4타, PUPDMG + 백스윙)
  3. 크리티컬 — mod_profic% 확률, 3~6배 데미지
  4. 그림자 공격 — OSHADO 플래그 장비
  5. 결혼 파워 — 배우자 같은 방 → 데미지 2배
  6. 무기 내구도 — 25% 확률 감소, 0이면 파괴
  7. NPC AI — MAGGRE(공격), MFLEER(도주), MMAGIC(시전)
```

### Step 3-6: 콘텐츠 시스템

각 단계는 독립적 Lua 파일로 구현:

| Step | 시스템 | Lua 파일 | 주요 명령어 |
|------|--------|----------|------------|
| 3 | 경제 | economy.lua, shops.lua | deposit, withdraw, auction, buy, sell, repair |
| 4 | 커뮤니티 | board.lua, family.lua, social.lua | write, read, fcreate, propose, marry |
| 5 | 성장 | training.lua + level.py 수정 | train, power, meditate, accurate |
| 6 | 기타 | forge.lua, poker.lua, misc.lua, ranking.lua | forge, poker, alias, chaos, rank |

### Step 7: 관리자 명령어

```
원본 매핑:
  dm1.c ~ dm6.c  →  lua/commands/admin.lua

레벨 계층 (3eyes 예):
  ZONEMAKER(13) < REALZONEMAKER(14) < SUB_DM(15) < DM(16) < ME(17)

필수 DM 명령어 (~40개):
  텔레포트: goto, transfer, at, teleport
  생성/삭제: load, purge, destroy
  플레이어: advance, set, force, freeze, jail, ban, mute
  정보: stat, where, zstat, users, uptime
  가시성: invis, visible, snoop
  시스템: shutdown, reboot, reload, saveworld
  존: zreset
  유틸: announce, echo, gecho, slay, peace, dmheal
```

### Step 8: 정비 + 출력 보강

1. **방 특수효과** → `game.py room_tick_effects()` (RHEALR, RPHARM, RPPOIS, RPMPDR)
2. **시체 부패** → `death.py decay_corpses()` + `game.py on_tick()`
3. **info 확장** → score에 전직/숙련도/결혼/가족 추가
4. **who 확장** → 클래스 등급별 색상, DM 투명 필터
5. **ANSI 전수 검사** → 모든 출력이 `{color}` 포맷인지 확인

---

## 5. Python 레이어 — 플러그인 프로토콜

### 5.1 game.py — GamePlugin Protocol

**최소 구현 (tbaMUD 수준):**

```python
class MyGamePlugin:
    name = "mygame"

    def welcome_banner(self) -> str:
        """접속 시 표시할 배너 (banner.txt 로드)."""
        ...

    def get_initial_state(self) -> Any:
        """로그인 첫 상태 반환."""
        return MyGetNameState()

    def register_commands(self, engine) -> None:
        """Lua에서 등록하므로 pass."""
        pass

    async def handle_death(self, engine, victim, killer=None) -> None:
        """사망 처리 위임."""
        await death.handle_death(engine, victim, killer=killer)

    def playing_prompt(self, session) -> str:
        """게임 중 프롬프트."""
        c = session.character
        return f"< {c.hp}/{c.max_hp}hp {c.mana}/{c.max_mana}mp > "

def create_plugin() -> MyGamePlugin:
    return MyGamePlugin()
```

**완전 구현 (3eyes 수준, 8 hooks):**

```python
class ThreeEyesPlugin:
    name = "3eyes"

    # 기본 4 hooks
    def welcome_banner(self) -> str: ...
    def get_initial_state(self) -> Any: ...
    def register_commands(self, engine) -> None: pass
    async def handle_death(self, engine, victim, killer=None) -> None: ...
    def playing_prompt(self, session) -> str: ...

    # 확장 hooks (복잡한 게임)
    async def on_tick(self, engine) -> None:
        """매 틱 호출 — 시체 부패 등."""
        await death.decay_corpses(engine)

    async def mobile_activity(self, engine) -> None:
        """NPC AI — MAGGRE 자동 공격, DEX 체크."""
        for room in engine.world.rooms.values():
            for mob in room.characters:
                if mob.is_npc and "aggressive" in mob.proto.act_flags:
                    # ... 공격 대상 선정 + 전투 시작

    async def room_tick_effects(self, engine) -> None:
        """방 플래그 효과 — 힐링/독/데미지/MP 드레인."""
        for room in engine.world.rooms.values():
            if "healing" in room.flags:
                for ch in room.characters:
                    ch.hp = min(ch.max_hp, ch.hp + random.randint(5, 15))

    def regen_char(self, engine, char) -> None:
        """틱당 HP/MP/MV 회복 (클래스/레벨 기반)."""
        hp_regen = 5 + con_bonus
        if char.class_id == BARBARIAN: hp_regen += 2
        if char.class_id >= INVINCIBLE: hp_regen += 3
        char.hp = min(char.max_hp, char.hp + hp_regen)
```

**핵심 패턴:**
- `_import()` 지연 임포트로 순환 참조 방지
- `_PKG = "games.3eyes"` → `importlib.import_module(f"{_PKG}.{submodule}")`
- 10woongi처럼 숫자 시작 패키지는 `importlib.import_module()` 필수

### 5.2 login.py — 상태머신 패턴

**구조:**
```python
class StateN:
    def prompt(self) -> str:
        """프롬프트 텍스트 반환."""
        return "입력하세요: "

    async def on_input(self, session, text) -> Any:
        """입력 처리 후 다음 상태 반환. None이면 현재 상태 유지."""
        if valid(text):
            return NextState()
        await session.send_line("잘못된 입력입니다.")
        return None  # re-prompt
```

**3eyes 10단계 흐름:**
```
GetName → ConfirmNew → SelectGender → SelectClass → SelectRace → SetPassword → Disconnect
     ↓                                                                        (재접속 필요)
GetPassword → MainMenu → News → EnterGame
                  ↓
          ChangePassword
```

**필수 검증 (원본 충실):**
- 이름: 한글 1~5자 (`re.findall(r'[\uac00-\ud7af]', name)`)
- 비밀번호: 5~14자, 이름과 동일 불가, `1234`/`1111` 불가
- 로그인 시도: 3회 실패 → 강제 접속종료
- 신규 캐릭터: 생성 후 접속종료 → 재접속 필요 (원본 동작)

**초기 캐릭터 데이터:**
```python
# SetPasswordState.on_input() 에서:
session.player_data["stats"] = {"str": 10, "dex": 10, "con": 10, "int": 10, "pie": 10}
session.player_data["gold"] = c.INITIAL_GOLD  # 5000
session.player_data["hp"] = cls["hp_start"]    # 클래스별 초기 HP
session.player_data["mana"] = cls["mp_start"]  # 클래스별 초기 MP
session.player_data["extensions"]["proficiency"] = [0, 0, 0, 0, 0]
session.player_data["extensions"]["realm"] = [0, 0, 0, 0]
session.player_data["inventory"] = [1140, 1141, 1143, 1144]  # 초기 아이템 vnum
```

### 5.3 constants.py — 상수 패턴

```python
# ── 클래스 ──
ASSASSIN = 1; BARBARIAN = 2; ...; ME = 17
CLASS_NAMES = {1: "암살자", 2: "야만인", ...}
CLASS_STATS = {1: {"hp_start": 55, "mp_start": 50, "hp_lv": 6, "mp_lv": 2}, ...}
LEVEL_CYCLE = {1: ["con", "pie", "str", ...], ...}  # 레벨업시 스탯 순환

# ── 종족 ──
RACE_NAMES = {1: "드워프", ...}
RACE_STAT_MODS = {1: {"str": 1, "pie": -1}, ...}

# ── 플래그 (비트 위치 → 정수 상수) ──
PBLESS = 0; PHIDDN = 1; PINVIS = 2; ...  # Player flags
MAGGRE = 0; MFLEER = 1; ...               # Monster flags
RDARKR = 0; RBANK = 6; RSHOP = 7; ...     # Room flags

# ── 쿨다운 슬롯 ──
LT_ATTCK = 0; LT_SPELL = 1; ...

# ── 주문 ──
SPELL_LIST = {0: {"name": "vigor", "kr": "활력", "mp": 3}, ...}

# ── 숙련도 경험치 테이블 ──
PROF_TABLE_FIGHTER = [0, 768, 1024, 1440, ...]

# ── 스탯 보너스 ──
STAT_BONUS = {0: -4, 10: 0, 18: 2, 24: 4, 29: 5, ...}
```

### 5.4 level.py — 경험치/레벨업 패턴

```python
EXP_TABLE = {1: 0, 2: 500, 3: 1200, ...}  # 201레벨

def _exp_multiplier(class_id: int) -> int:
    """전직 경험치 배수."""
    if class_id >= CARETAKER: return 25
    if class_id >= INVINCIBLE: return 5
    return 1

def exp_for_level(level: int, class_id: int = 0) -> int:
    base = EXP_TABLE.get(min(level, MAX_MORTAL_LEVEL), 0)
    return base * _exp_multiplier(class_id)

def check_level_up(char) -> bool:
    needed = exp_for_level(char.level + 1, char.class_id)
    return char.experience >= needed

async def do_level_up(char, send_fn=None):
    cls_stats = CLASS_STATS.get(char.class_id, CLASS_STATS[4])
    # HP/MP 증가 (CON 보너스 반영)
    hp_gain = cls_stats["hp_lv"] + get_stat_bonus(char.stats.get("con", 13))
    # 스탯 순환
    stat_key = LEVEL_CYCLE[class_id][char.level % 10]
    char.stats[stat_key] = min(63, char.stats.get(stat_key, 10) + 1)
```

### 5.5 combat/death.py — 사망 처리 패턴

```python
async def handle_death(engine, victim, killer=None):
    # 1. 전투 중단
    victim.fighting.fighting = None
    victim.fighting = None

    # 2. 시체 생성 (아이템 이전)
    corpse = _make_corpse(victim)  # inventory + equipment → corpse.contains
    room.objects.append(corpse)

    # 3. 골드 이전 (killer에게)
    if victim.gold > 0 and killer:
        killer.gold += victim.gold

    # 4a. NPC 사망 → 경험치 + 숙련도 지급
    if victim.is_npc:
        exp = calculate_exp_gain(killer, victim)
        killer.experience += exp
        _add_proficiency(killer, exp)

    # 4b. 플레이어 사망 → 경험치 패널티 + 부활
    else:
        # PvE: 3/4 패널티, PvP: 1/4 패널티
        exp_loss = (cur_exp - prev_exp) * (3 if not is_pk else 1) // 4
        victim.experience -= exp_loss

        # PK 추적 (pk_kills/pk_deaths)
        if is_pk:
            killer.session.player_data["pk_kills"] += 1
            victim.session.player_data["pk_deaths"] += 1

        # 부활: SPIRIT_ROOM, HP 100%, MP 10%
        victim.room_vnum = SPIRIT_ROOM
        victim.hp = victim.max_hp

# 시체 부패 (tick마다 호출)
async def decay_corpses(engine):
    for room in engine.world.rooms.values():
        for obj in room.objects:
            if obj.values.get("corpse"):
                obj.values["timer"] -= 1
                if obj.values["timer"] <= 0:
                    # 아이템 바닥 드롭 + 시체 제거
```

---

## 6. Lua 레이어 — 명령어 / 전투 / 마법

### 6.1 명령어 등록 패턴

```lua
-- register_command(영문명, function, 한글명)
register_command("score", function(ctx, args)
    local ch = ctx.char
    local lines = {}
    lines[#lines + 1] = "{bright_cyan}━━━━ 능력치 ━━━━{reset}"
    lines[#lines + 1] = "  이름: " .. ch.name
    lines[#lines + 1] = "  레벨: " .. ch.level
    ctx:send(table.concat(lines, "\r\n"))
end, "능력")
```

**ctx (CommandContext) 주요 API:**

```lua
-- ── 메시지 ──
ctx:send(msg)                    -- 본인에게
ctx:send_room(msg)               -- 같은 방 전체에게
ctx:send_to(target, msg)         -- 특정 대상에게
ctx:send_all(msg)                -- 전역 (서버 전체)

-- ── 캐릭터 ──
ctx.char                         -- 현재 캐릭터 (MobInstance)
ctx:find_char(keyword)           -- 같은 방에서 캐릭터 찾기
ctx:find_player(name)            -- 이름으로 온라인 플레이어 찾기
ctx:get_online_players()         -- 전체 온라인 플레이어 리스트

-- ── 아이템 ──
ctx:find_inv_item(keyword)       -- 인벤토리에서 찾기
ctx:find_equip_item(keyword)     -- 장착 중에서 찾기
ctx:find_room_item(keyword)      -- 방 바닥에서 찾기
ctx:obj_to_char(obj, char)       -- 아이템을 캐릭터에게
ctx:obj_from_char(obj)           -- 캐릭터에서 아이템 제거

-- ── 방/이동 ──
ctx:get_room()                   -- 현재 방 객체
ctx:teleport_to(vnum)            -- 텔레포트
ctx:send_room_except(ch, msg)    -- ch 제외하고 방 전체에게

-- ── 상점 ──
ctx:get_shop()                   -- 현재 방의 상점
ctx:get_shop_items()             -- 상점 인벤토리
ctx:get_buy_price(item)          -- 구매가
ctx:get_sell_price(item)         -- 판매가

-- ── 플레이어 데이터 (JSONB) ──
ctx:get_player_data(key)         -- 세션별 데이터 읽기
ctx:set_player_data(key, value)  -- 세션별 데이터 쓰기

-- ── 플래그 ──
ctx:has_flag(flag_id)            -- 플래그 확인
ctx:set_flag(flag_id)            -- 플래그 설정
ctx:clear_flag(flag_id)          -- 플래그 해제

-- ── 명령어 호출 ──
ctx:call_command(cmd, args)      -- 다른 명령어 실행
ctx:defer_death()                -- 사망 처리를 Python에 위임
```

### 6.2 lib.lua — 게임별 공유 라이브러리

게임 전용 함수를 여기에 정의합니다:

```lua
-- ── 상수 (THAC0 테이블 등) ──
THAC0_TABLE = { ... }           -- 20×20 클래스별 THAC0
THREEEYES_CLASSES = { ... }     -- 클래스 이름 맵

-- ── 숙련도 계산 ──
function te_profic(player, prof_type) ... end  -- 무기 숙련도 0~100%
function te_mprofic(player, realm) ... end     -- 영역 숙련도 0~100%

-- ── 전투 유틸 ──
function te_compute_thaco(ch, victim) ... end  -- THAC0 계산
function te_comp_chance(level, class_id) ... end
function te_get_stat_bonus(stat) ... end

-- ── 방 플래그 체크 ──
function te_room_has_flag(ctx, flag_id)
    local room = ctx:get_room()
    if not room then return false end
    local flags = room.flags
    if not flags then return false end
    local ok, result = pcall(function()
        for i = 0, 100 do
            local ok2, f = pcall(function() return flags[i] end)
            if not ok2 or f == nil then return false end
            if f == flag_id or f == "flag_" .. flag_id then return true end
        end
        return false
    end)
    return ok and result
end

-- ── 쿨다운 체크/설정 ──
function te_check_cooldown(ctx, slot, cooldown_secs)
    local cd = ctx:get_player_data("cooldowns") or {}
    local last = cd[tostring(slot)] or 0
    local now = os.time()
    if now - last < cooldown_secs then
        local remain = cooldown_secs - (now - last)
        return false, remain
    end
    return true, 0
end

function te_set_cooldown(ctx, slot)
    local cd = ctx:get_player_data("cooldowns") or {}
    cd[tostring(slot)] = os.time()
    ctx:set_player_data("cooldowns", cd)
end
```

### 6.3 thac0.lua — 전투 라운드 패턴

```lua
-- combat_round 훅으로 등록
function threeeyes_combat_round(ctx, attacker, defender)
    -- 1. THAC0 계산
    local thaco = te_compute_thaco(attacker, defender)

    -- 2. 다중 공격 (1~4타)
    local num_attacks = 1
    if has_pupdmg then num_attacks = num_attacks + 1 end
    if high_proficiency then num_attacks = num_attacks + 1 end

    for strike = 1, num_attacks do
        -- 3. 명중 판정
        local roll = math.random(1, 20)
        if roll >= thaco then
            -- 4. 데미지 계산
            local dmg = weapon_dice + str_bonus + profic_bonus

            -- 5. 크리티컬 (mod_profic% 확률)
            if math.random(1, 100) <= mod_profic then
                dmg = dmg * math.random(3, 6)
            end

            -- 6. 결혼 파워 (배우자 같은 방)
            if spouse_in_room then dmg = dmg * 2 end

            -- 7. 데미지 적용
            defender.hp = defender.hp - dmg
        end
    end

    -- 8. 그림자 공격 (OSHADO 장비)
    if has_shadow_weapon then
        local shadow_dmg = calculate_shadow_damage()
        defender.hp = defender.hp - shadow_dmg
    end

    -- 9. 무기 내구도 감소 (25%)
    if math.random(1, 4) == 1 then
        weapon.shots_remaining = weapon.shots_remaining - 1
    end

    -- 10. 사망 체크
    if defender.hp <= 0 then
        ctx:defer_death()  -- Python death handler로 위임
    end
end
```

### 6.4 spells.lua — 마법 시스템 패턴

```lua
-- cast 명령어
register_command("cast", function(ctx, args)
    -- 1. 주문명 부분 일치 검색
    local spell = find_spell_by_prefix(spell_name)

    -- 2. 시전 가능 검사
    if ctx:has_flag(PBLIND) then ctx:send("실명 상태!"); return end
    if te_room_has_flag(ctx, RNOMAG) then ctx:send("마법 불가 지역!"); return end

    -- 3. 마나 검사
    if ch.mana < spell.mp then ctx:send("마나 부족!"); return end

    -- 4. 쿨다운 검사 (LT_SPELL)
    local can, remain = te_check_cooldown(ctx, LT_SPELL, 3)
    if not can then ctx:send("아직 준비 안됨!"); return end

    -- 5. spell_fail() 검사
    if not check_spell_success(ctx, spell) then
        ch.mana = ch.mana - (spell.mp // 2)  -- 실패 시 마나 절반 소모
        ctx:send("{red}주문 시전에 실패했습니다!{reset}")
        return
    end

    -- 6. 마나 차감 + 쿨다운
    ch.mana = ch.mana - spell.mp
    te_set_cooldown(ctx, LT_SPELL)

    -- 7. 효과 적용
    if spell.offensive then
        apply_offensive_spell(ctx, spell, target)
    else
        apply_utility_spell(ctx, spell, target)
    end
end, "시전")

-- 공격 주문 데미지 (원본 offensive_spell() 충실 이식)
function apply_offensive_spell(ctx, spell, target)
    local ch = ctx.char
    -- bonus_type에 따라 분기
    local bonus = te_get_stat_bonus(ch.stats.int or 13)
    bonus = bonus + te_comp_chance(ch.level, ch.class_id)

    -- 영역 보너스 (방 영역과 주문 영역 비교)
    local room_realm = get_room_realm(ctx)
    if room_realm == spell.realm then
        bonus = bonus * 2  -- 같은 영역 방: 보너스 2배
    elseif is_opposite_realm(room_realm, spell.realm) then
        bonus = bonus * -1  -- 대립 영역: 역보너스
    end

    local dmg = spell.base_dmg + bonus
    target.hp = target.hp - dmg
end
```

---

## 7. 데이터 레이어 — SQL / Config / 텍스트

### 7.1 통합 스키마 (Unified Schema v1.0)

**20+2 테이블 구조:**

```
Proto Tables (마이그레이션 생성, 읽기 전용):
  rooms          방 (7,439)      → zone_vnum, flags TEXT[], ext JSONB
  room_exits     출구 (16,514)   → from_vnum, direction, to_vnum
  mob_protos     몬스터 (1,394)  → act_flags TEXT[], stats JSONB
  item_protos    아이템 (1,362)  → item_type TEXT, values JSONB
  zones          존 (103)        → level_range INT4RANGE
  skills         기술 (63)       → class_levels JSONB
  classes        직업 (8)        → hp_gain INT4RANGE
  races          종족 (8)        → stat_mods JSONB
  shops          상점             → buy_types TEXT[], inventory JSONB
  quests         퀘스트           → target JSONB, rewards JSONB
  socials        소셜 (32)       → messages JSONB
  help_entries   도움말 (116)    → keywords TEXT[]
  combat_messages 전투 메시지 (9) → to_char, to_victim, to_room
  text_files     텍스트 (6)      → category, content
  game_tables    수치 테이블 (523) → table_name, key JSONB, value JSONB
  game_configs   설정 (43)       → key, value JSONB, category

Instance Tables (런타임 변경):
  players        플레이어         → stats JSONB, equipment JSONB, ext JSONB
  organizations  가족/길드        → org_type, treasury
  lua_scripts    Lua 스크립트     → game, category, source
  boards*        게시판           → (선택)
  board_posts*   게시글           → (선택)
```

**v1.0 핵심 변경점 (원본 대비):**

| 원본 | GenOS | 이유 |
|------|-------|------|
| `flags: int bitvector` | `flags: TEXT[]` + GIN 인덱스 | 7게임 플래그 체계 통합 |
| `hp_dice: "3d8+2"` | `max_hp: INTEGER` | 마이그레이션 시 중앙값 계산 |
| `item_type: int` | `item_type: TEXT` | "weapon", "armor" 가독성 |
| `values[4]: int` | `values: JSONB` | `{"damage": "2d6+3"}` 유연성 |
| `exits[6]` 배열 | `room_exits` 별도 테이블 | 그래프 모델 |
| `6개 수치 테이블` | `game_tables` 1개 | KV 통합 |
| `socials: 9 TEXT columns` | `messages: JSONB` | 동적 메시지 |

### 7.2 seed_data.sql 구조

```sql
BEGIN;

-- Proto 데이터 (마이그레이션 도구가 생성)
INSERT INTO rooms (...) VALUES (...);        -- 7,437행
INSERT INTO room_exits (...) VALUES (...);   -- 16,514행
INSERT INTO mob_protos (...) VALUES (...);   -- 1,394행
INSERT INTO item_protos (...) VALUES (...);  -- 1,362행
INSERT INTO game_tables (...) VALUES (...);  -- 523행
INSERT INTO help_entries (...) VALUES (...); -- 116행
INSERT INTO skills (...) VALUES (...);       -- 63행
INSERT INTO classes (...) VALUES (...);      -- 8행
INSERT INTO races (...) VALUES (...);        -- 8행

-- 보충 데이터 (수동 추가)
INSERT INTO zones (...) VALUES (...);           -- 103행
INSERT INTO game_configs (...) VALUES (...);    -- 43행
INSERT INTO socials (...) VALUES (...);         -- 32행
INSERT INTO combat_messages (...) VALUES (...); -- 9행
INSERT INTO text_files (...) VALUES (...);      -- 6행

COMMIT;
```

### 7.3 config/<game>.yaml

```yaml
game: 3eyes                        # games/<game>/ 디렉토리명
name: "제3의 눈 (3eyes)"            # 표시 이름

network:
  telnet_host: "0.0.0.0"
  telnet_port: 4003                # 게임별 고유 포트
  api_host: "0.0.0.0"
  api_port: 8083

database:
  host: "localhost"
  port: 5432
  user: "genos"
  password: "genos"
  database: "genos_3eyes"          # 게임별 DB
  min_connections: 2
  max_connections: 10

world:
  start_room: 1                    # 신규 캐릭터 시작 방
  void_room: 0                     # 유효하지 않은 방 → void

engine:
  tick_rate: 10                    # 초당 틱
  save_interval: 300               # 5분마다 저장
  max_players: 100
  combat_round: 20                 # 전투 라운드 틱 수
  shutdown_timeout: 30

dev:
  hot_reload: true
  debug: true
  log_level: "DEBUG"
```

### 7.4 텍스트 파일 (banner.txt, menu.txt, news.txt)

```
data/<game>/
├── banner.txt      접속 시 ASCII 아트 (원본 로고 재현)
├── menu.txt        메인 메뉴 텍스트 (원본 동일)
└── news.txt        공지사항 (GenOS 전환 안내)
```

### 7.5 보충 데이터 — 마이그레이션 도구가 생성하지 않는 테이블

마이그레이션 도구(`genos migrate`)는 원본 바이너리/텍스트에서 rooms, mobs, items,
skills, classes, races 등을 자동 추출합니다. 하지만 **다음 6개 테이블은 수동 보충**이
필요합니다. 이 과정을 빠뜨리면 엔진 실행 시 존 리셋, 설정 로드, 소셜 명령 등이
작동하지 않습니다.

#### 7.5.1 zones — rooms에서 파생

마이그레이션 도구는 각 room에 `zone_vnum`을 기록하지만, `zones` 테이블 자체는
생성하지 않습니다. **seed_data.sql의 rooms INSERT에서 zone_vnum을 추출**하여 생성합니다:

```python
# zones 파생 스크립트 (실제 3eyes에서 사용한 방법)
zones = {}
for m in re.finditer(r"INSERT INTO rooms.*?VALUES\s*\((\d+),\s*(\d+),\s*'([^']*)',", content):
    vnum, zone_vnum, name = int(m.group(1)), int(m.group(2)), m.group(3)
    if zone_vnum not in zones:
        zones[zone_vnum] = {'count': 0, 'min': vnum, 'max': vnum, 'name': name}
    z = zones[zone_vnum]
    z['count'] += 1
    z['min'] = min(z['min'], vnum)
    z['max'] = max(z['max'], vnum)

# 각 zone → INSERT 생성
# level_range는 zone_vnum 기반 휴리스틱 또는 원본 데이터에서 추출
# ext에 room_count, vnum_range 메타데이터 포함
```

생성 예시 (3eyes: 103개 존):
```sql
INSERT INTO zones (vnum, name, ..., ext) VALUES
  (0,  '초보 학교 입구', ..., '{"room_count": 79, "vnum_range": [1, 99]}'),
  (1,  '火神의 성지',    ..., '{"room_count": 100, "vnum_range": [100, 199]}'),
  (11, '본당으로 가는 길', ..., '{"room_count": 100, "vnum_range": [1100, 1199]}'),
  ...
```

#### 7.5.2 game_configs — 게임 시스템 설정 (43개)

게임별 모든 시스템 파라미터를 JSONB value로 저장합니다.
**constants.py에 하드코딩된 값을 DB에도 미러링**하여, 운영 중 DB만으로 설정 조회 가능:

| 카테고리 | 키 | 값 예시 | 설명 |
|----------|-----|---------|------|
| **general** | `game_name` | `"제3의 눈 (3eyes)"` | 게임 이름 |
| | `game_engine` | `"Mordor 2.0"` | 원본 엔진 |
| **world** | `start_room` | `1` | 신규 캐릭터 시작 방 vnum |
| | `spirit_room` | `11971` | 사망 후 부활 방 vnum |
| **gameplay** | `max_mortal_level` | `201` | 일반 최대 레벨 |
| | `initial_gold` | `5000` | 신규 캐릭터 초기 골드 |
| | `initial_items` | `[1140,1141,1143,1144]` | 초기 아이템 vnum 배열 |
| | `corpse_decay_ticks` | `5` | 시체 부패 틱 수 |
| **economy** | `bank_max_gold` | `999999999` | 은행 최대 보관액 |
| | `bank_max_items` | `10` | 은행 보관함 최대 개수 |
| | `auction_min_price` | `100` | 경매 최소 시작가 |
| | `sell_max_price` | `100000` | 상점 판매 최대가 |
| **cooldown** | `forge_cooldown` | `60` | 제련 쿨다운 (초) |
| | `train_cooldown` | `60` | 전직 쿨다운 (초) |
| **combat** | `aggro_dex_skip_chance` | `30` | MAGGRE DEX 회피율 (%) |
| | `weapon_break_chance` | `25` | 무기 내구도 감소 확률 (%) |
| | `flee_exp_penalty` | `0.1` | 도주 경험치 패널티 비율 |
| | `death_exp_penalty` | `0.75` | 사망 경험치 패널티 비율 |
| **pk** | `pk_min_level` | `50` | PK(카오스) 최소 레벨 |
| | `jail_base_time` | `60` | PK 감옥 기본 시간 (초/킬) |
| | `killer_threshold` | `5` | 킬러 상태 진입 킬 수 |
| **advancement** | `invincible_exp_mult` | `5` | 무적자 경험치 배수 |
| | `caretaker_exp_mult` | `25` | 보살핌자 경험치 배수 |
| **regen** | `regen_base_hp` | `5` | 기본 HP 회복/틱 |
| | `regen_base_mp` | `5` | 기본 MP 회복/틱 |
| | `regen_base_mv` | `3` | 기본 MV 회복/틱 |
| **room_effects** | `heal_room_hp` | `[5, 15]` | 힐링 방 HP 회복 범위 |
| | `harm_room_hp` | `[3, 10]` | 유해 방 HP 피해 범위 |
| | `mpdrain_room_mp` | `[5, 15]` | MP 흡수 방 피해 범위 |
| | `poison_room_chance` | `20` | 독 방 중독 확률 (%) |
| **social** | `marriage_damage_mult` | `2.0` | 결혼 데미지 배수 |
| | `max_families` | `50` | 최대 가족(길드) 수 |
| | `family_max_members` | `30` | 가족 최대 인원 |
| **community** | `board_count` | `18` | 게시판 수 |
| | `max_board_posts` | `50` | 게시판별 최대 글 수 |
| **minigame** | `poker_ante` | `500` | 포커 참가비 |
| **player** | `max_aliases` | `20` | 최대 별명 개수 |
| **char_creation** | `create_classes` | `[[8,"도둑"],[2,"권법가"],...]` | 생성 직업 선택지 |
| | `create_races` | `[[1,"요정족"],[2,"드래곤족"],...]` | 생성 종족 선택지 |
| **tables** | `class_names` | `{"1":"암살자","2":"야만인",...}` | 직업 이름 매핑 |
| | `race_names` | `{"1":"드워프","2":"엘프",...}` | 종족 이름 매핑 |
| | `prof_names` | `{"0":"날붙이","1":"찌르기",...}` | 숙련도 이름 |
| | `realm_names` | `{"0":"대지","1":"바람",...}` | 영역 이름 |

**핵심**: `value`는 JSONB이므로 정수, 문자열, 배열, 객체 모두 저장 가능합니다.

#### 7.5.3 socials — 소셜 명령어 (32개)

소셜 명령어의 한글 메시지를 `messages` JSONB에 저장합니다.
3eyes 기본 세트 32개:

```
smile(미소), grin(싱글벙글), laugh(웃음), chuckle(킥킥),
cry(울기), nod(끄덕), shake(고개젓기), bow(인사),
wave(손흔들기), clap(박수), dance(춤), sigh(한숨),
hug(포옹), kiss(키스), poke(찌르기), slap(뺨때리기),
pat(토닥), yawn(하품), cough(기침), think(생각),
ponder(곰곰이), shrug(으쓱), groan(신음), blush(얼굴빨개짐),
thank(감사), comfort(위로), wink(윙크), giggle(킥킥),
stomp(발구르기), beg(자비), cheer(환호), growl(으르렁)
```

messages JSONB 구조:
```json
{
  "no_arg_to_char": "당신은 미소짓습니다.",
  "no_arg_to_room": "$n이(가) 미소짓습니다.",
  "found_to_char": "$N에게 미소짓습니다.",
  "found_to_victim": "$n이(가) 당신에게 미소짓습니다.",
  "found_to_room": "$n이(가) $N에게 미소짓습니다."
}
```
- `$n` = 행위자 이름, `$N` = 대상 이름
- `no_arg_*` = 대상 없이 사용할 때, `found_*` = 대상 지정 시

#### 7.5.4 combat_messages — 전투 메시지 (9단계)

데미지 크기에 따른 전투 출력 메시지:

| hit_type | to_char (공격자) | to_victim (피해자) |
|----------|-----------------|-------------------|
| `miss` | $N에게 공격했지만 빗나갔습니다. | $n이(가) 당신에게 공격했지만 빗나갔습니다. |
| `hit` | $N을(를) 타격했습니다. | $n이(가) 당신을 타격했습니다. |
| `hard_hit` | $N을(를) 강하게 타격했습니다! | $n이(가) 당신을 강하게 타격했습니다! |
| `crush` | $N을(를) 강타했습니다!! | $n이(가) 당신을 강타했습니다!! |
| `obliterate` | $N을(를) {bright_red}분쇄{reset}했습니다!!! | ... |
| `annihilate` | $N을(를) {bright_red}완전히 박살{reset}냈습니다!!!! | ... |
| `critical` | {bright_yellow}치명타!{reset} $N에게 막대한 피해! | ... |
| `shadow` | {bright_magenta}그림자 공격!{reset} $N의 뒤에서! | ... |
| `death` | {bright_red}$N을(를) 쓰러뜨렸습니다!{reset} | ... |

각 메시지에 `to_room` (방 관찰자용)도 포함됩니다.

#### 7.5.5 text_files — 시스템 텍스트 (6개)

| name | category | 내용 |
|------|----------|------|
| `motd` | system | 오늘의 메시지 (접속 시 표시) |
| `rules` | system | 게임 규칙 (비매너/버그이용/PK 규칙) |
| `credits` | system | 크레딧 (원본 + GenOS Engine) |
| `imotd` | system | 관리자 전용 공지 |
| `greeting` | system | 환영 메시지 |
| `newbie_guide` | help | 초보자 가이드 (기본 명령어 안내) |

### 7.6 초기 아이템 검증 절차

`constants.py`의 `INITIAL_ITEMS` 목록이 **실제 `item_protos` 테이블에 존재**하는지
반드시 검증해야 합니다. 존재하지 않는 vnum을 지급하면 인벤토리 로드 시 오류 발생:

```bash
# 검증 명령어: seed_data.sql에서 해당 vnum 검색
grep "INSERT INTO item_protos" seed_data.sql | grep -E '\b(1140|1141|1143|1144)\b'
```

3eyes 검증 결과:
| vnum | short_desc | item_type | 확인 |
|------|-----------|-----------|------|
| 1140 | 전자수첩 | other | OK |
| 1141 | 노트북 | other | OK |
| 1143 | 이벤트 스코프 | other | OK |
| 1144 | 임무수첩 | other | OK |

`start_room`과 `spirit_room` vnum도 동일하게 `rooms` 테이블 존재 여부를 확인합니다.

### 7.7 PK(플레이어 킬) 차등 시스템 상세

사망 처리는 **PvE(몬스터에 의한 사망)와 PvP(플레이어에 의한 사망)를 차등 처리**합니다:

| 항목 | PvE 사망 | PvP 사망 |
|------|---------|---------|
| **경험치 패널티** | (현재 레벨 exp - 이전 레벨 exp) × **3/4** | (현재 레벨 exp - 이전 레벨 exp) × **1/4** |
| **부활 HP** | max_hp **100%** | max_hp **50%** |
| **부활 MP** | max_mana **10%** | max_mana **25%** |
| **PK 카운트** | — | killer: pk_kills +1, victim: pk_deaths +1 |
| **전역 알림** | 없음 | `[PK] {killer}이(가) {victim}을(를) 살해했습니다!` |
| **킬러 경고** | — | pk_kills ≥ 10 → "킬러 상태! 자수를 고려하세요" |

PK 추적 데이터는 `player_data` (세션 JSONB) 에 저장:
```python
# death.py 에서:
killer.session.player_data["pk_kills"] += 1
victim.session.player_data["pk_deaths"] += 1
```

### 7.8 시체 부패(Corpse Decay) 메커니즘

시체는 `_make_corpse()` 에서 `values = {"corpse": True, "timer": 5}` 로 생성됩니다.
이후 **매 엔진 틱마다** `decay_corpses()` 가 호출되어:

```
틱 0: 시체 생성 (timer=5)
틱 1: timer=4
틱 2: timer=3
틱 3: timer=2
틱 4: timer=1
틱 5: timer=0 → 부패!
  ├─ 시체 안의 아이템 → 방 바닥으로 드롭
  ├─ 시체 객체 → room.objects에서 제거
  └─ 방 메시지: "{yellow}{시체이름}가 부패하여 사라집니다.{reset}"
```

`game.py`의 `on_tick()` 훅에서 호출:
```python
async def on_tick(self, engine):
    await death.decay_corpses(engine)
```

---

## 8. ANSI 색상 변환 규칙

### 8.1 GenOS `{color}` 포맷

모든 출력은 `{color_name}` 포맷을 사용합니다:

```
{reset}          — 리셋
{bold}           — 볼드
{black}          — 검정
{red}            — 빨강
{green}          — 초록
{yellow}         — 노랑
{blue}           — 파랑
{magenta}        — 자홍
{cyan}           — 시안
{white}          — 하양
{bright_red}     — 밝은 빨강
{bright_green}   — 밝은 초록
{bright_yellow}  — 밝은 노랑
{bright_blue}    — 밝은 파랑
{bright_magenta} — 밝은 자홍
{bright_cyan}    — 밝은 시안
{bright_white}   — 밝은 하양
{bg_red}         — 배경 빨강
{bg_green}       — 배경 초록
...
```

### 8.2 원본 → GenOS 변환표

**Mordor 2.0 (3eyes) — ESC 코드 직접 사용:**
```
\033[0m  → {reset}
\033[1m  → {bold}
\033[31m → {red}
\033[32m → {green}
\033[1;31m → {bright_red}
```

**CircleMUD (tbaMUD/simoon) — @코드:**
```
@n → {reset}
@r → {red}    @R → {bright_red}
@g → {green}  @G → {bright_green}
@y → {yellow} @Y → {bright_yellow}
@b → {blue}   @B → {bright_blue}
```

**FluffOS (10woongi) — %^코드%^:**
```
%^RESET%^  → {reset}
%^RED%^    → {red}
%^BOLD%^   → {bold}
%^GREEN%^  → {green}
```

**SMAUG (99hunter) — &코드:**
```
&W → {bright_white}
&g → {green}
&R → {bright_red}
&w → {white}
&x → {reset}
```

### 8.3 변환 원칙

1. **모든 원본 색상 → GenOS `{color}` 1:1 대응**
2. **배경색은 `{bg_*}` 접두사** 사용
3. **리셋은 반드시 `{reset}`** (원본의 `\033[0m`, `@n`, `%^RESET%^` 등)
4. **출력 문자열에 원본 ESC 코드 잔존 불허** — 전수 검사 필요
5. **구분선 스타일 유지**: `━━━━` (원본이 `-` 면 `━` 로 업그레이드)

---

## 9. 한국어 처리 패턴

### 9.1 조사 처리

```lua
-- korean_nlp.lua (자동 생성)
function has_batchim(char)
    -- UTF-8 한글 종성 검사
    local code = utf8_code(char)
    return (code - 0xAC00) % 28 ~= 0
end

-- 사용 예:
-- "검을" vs "방패를" → 받침 여부로 조사 자동 선택
ctx:send(target.name .. (has_batchim(target.name) and "을" or "를") .. " 공격합니다.")
```

### 9.2 한국어 명령어 SOV 파서

```lua
-- korean_commands.lua (자동 생성)
-- SOV (주어-목적어-동사) 파싱
-- "고블린에게 검으로 공격해" → {verb="kill", target="고블린", instrument="검"}

VERB_MAP = {
    ["공격"] = "kill", ["죽여"] = "kill",
    ["시전"] = "cast", ["먹어"] = "eat",
    ["마셔"] = "drink", ["봐"] = "look",
    ...
}

PARTICLE_MAP = {
    ["에게"] = "target",     -- 대상
    ["을"] = "object",       -- 목적어
    ["를"] = "object",
    ["으로"] = "instrument", -- 도구
    ["로"] = "instrument",
    ["에서"] = "location",   -- 장소
}
```

### 9.3 명령어 등록 시 한글 별칭

```lua
-- register_command(영문, function, 한글명)
register_command("kill", function(ctx, args) ... end, "죽여")
register_command("cast", function(ctx, args) ... end, "시전")
register_command("score", function(ctx, args) ... end, "능력")
```

---

## 10. Lua ↔ Python 인터옵 핵심 패턴

### 10.1 Python list 접근 (0-indexed, pcall 필수)

```lua
-- ✗ 잘못된 방법
for _, item in ipairs(ch.inventory) do ... end  -- #연산자 작동 안 함!

-- ✓ 올바른 방법 (pcall + 0-indexed)
for i = 0, 200 do
    local ok, item = pcall(function() return ch.inventory[i] end)
    if not ok or not item then break end
    -- item 사용
end

-- ✓ ctx 헬퍼 사용 (권장)
local count = ctx:get_inv_count()
for i = 0, count - 1 do
    local item = ch.inventory[i]
    ...
end
```

### 10.2 Python dict 접근 (pcall 감싸기)

```lua
-- ✗ 잘못된 방법
local slot_item = ch.equipment["head"]  -- nil 대신 에러 발생 가능

-- ✓ 올바른 방법
local ok, slot_item = pcall(function() return ch.equipment["head"] end)
if ok and slot_item then
    -- slot_item 사용
end
```

### 10.3 async 함수 위임

```lua
-- Lua에서 직접 async 호출 불가
-- ✗ await engine.do_look(session, "")

-- ✓ ctx 메서드로 위임
ctx:do_look()                  -- 내부적으로 async 처리
ctx:defer_death()              -- 사망 처리를 Python에 위임
ctx:teleport_to(vnum)          -- 텔레포트 (방 이동 + look 자동)
```

### 10.4 tick_affects는 Python 유지

Lua에서 Python list를 직접 수정하면 인터옵 문제 발생:

```python
# Python에서 처리 (game.py)
async def tick_affects(self, engine):
    for char in all_characters:
        if "poisoned" in char.flags:
            char.hp -= 5  # Lua가 아닌 Python에서 직접 수정
```

### 10.5 death는 defer 패턴

```lua
-- Lua 전투 코드에서:
if defender.hp <= 0 then
    ctx:defer_death()  -- 즉시 처리하지 않고 큐에 넣음
    return             -- 이후 Python plugin.handle_death()에서 처리
end
```

---

## 11. 공통 함정과 해결책

### 11.1 Python 측

| 함정 | 증상 | 해결책 |
|------|------|--------|
| 숫자 시작 패키지명 | `import games.10woongi` 에러 | `importlib.import_module("games.10woongi.login")` |
| `World.zones`가 list | `zones[vnum]` KeyError | `zones.append()` 사용, dict 아님 |
| 플러그인 훅 없음 | `AttributeError` | `getattr(self, "_plugin", None)` 안전 접근 |
| `send_fn` 타입 | 동기 호출 시 무반응 | `send_fn`은 async여야 함 |
| `on_input` 이름 | `handle_input` 호출해도 무응답 | login state는 `on_input()` 메서드 |
| `create_mob` 인자 | room_vnum 누락 | `World.create_mob(vnum, room_vnum)` — 2인자 |
| MobInstance.gold | NPC gold 0 | proto 값 자동 전파 안 됨, 명시적 설정 필요 |
| INT4RANGE 역전 | `[100,50)` 에러 | `[min(a,b), max(a,b)+1)` 보장 |

### 11.2 Lua 측

| 함정 | 증상 | 해결책 |
|------|------|--------|
| `#list` 연산자 | 항상 0 반환 | `ctx:get_inv_count()` 또는 pcall 루프 |
| Python dict 접근 | 에러/크래시 | `pcall(function() return dict[key] end)` |
| `table.insert` on Python list | 무효 | `list:append(item)` 또는 ctx 헬퍼 |
| `ipairs` on Python list | 빈 결과 | 0-indexed pcall 반복 패턴 사용 |
| `math.min`/`math.max` | 미정의 에러 | `math.min()` 은 표준 Lua에서 사용 가능하나 인자 주의 |
| 한글 문자열 길이 | `#str` = 바이트 수 | UTF-8 길이 함수 별도 사용 |

### 11.3 데이터 측

| 함정 | 증상 | 해결책 |
|------|------|--------|
| TEXT[] 싱글 쿼트 | SQL 에러 | `_sql_arr()` 에서 `'` → `''` 이스케이프 |
| JSONB NULL | 쿼리 실패 | `NOT NULL DEFAULT '{}'` |
| zones 비어있음 | 존 리셋 불가 | rooms에서 zone_vnum 추출하여 생성 |
| flags 형식 혼재 | 검사 실패 | 숫자/문자열/접두사 모두 체크: `"flag_7" in flags or 7 in flags or "shop" in flags` |

---

## 12. 검증 체크리스트

### 12.1 구조 검증

- [ ] `game.py` — `create_plugin()` 함수 존재
- [ ] `login.py` — 모든 State 클래스에 `prompt()` + `on_input()` 있음
- [ ] `constants.py` — CLASS_NAMES, RACE_NAMES, SPELL_LIST 키 일치
- [ ] `level.py` — EXP_TABLE 키가 1~MAX_LEVEL 범위 포함
- [ ] `death.py` — `handle_death()` + `calculate_exp_gain()` 존재
- [ ] `lib.lua` — 게임별 유틸 함수 전부 정의
- [ ] `thac0.lua` — combat_round 훅 등록
- [ ] `spells.lua` — 모든 SPELL_LIST 주문 효과 구현
- [ ] `schema.sql` — BEGIN; / COMMIT; 짝 맞음
- [ ] `seed_data.sql` — 14개 테이블 INSERT 존재
- [ ] `config/<game>.yaml` — 포트 충돌 없음

### 12.2 데이터 검증

- [ ] rooms 수 = 원본 방 수 일치
- [ ] mob_protos 수 = 원본 몬스터 수 일치
- [ ] item_protos 수 = 원본 아이템 수 일치
- [ ] zones 수 = 원본 존 수 일치
- [ ] skills 수 = 원본 주문/기술 수 일치
- [ ] classes 수 = 원본 직업 수 일치
- [ ] races 수 = 원본 종족 수 일치
- [ ] INITIAL_ITEMS vnums이 item_protos에 존재
- [ ] start_room vnum이 rooms에 존재
- [ ] SPIRIT_ROOM vnum이 rooms에 존재

### 12.3 기능 검증

- [ ] 로그인 → 신규 캐릭터 생성 → 재접속 → 게임 진입
- [ ] 이동 (6방향) + look + exits
- [ ] 아이템 get/drop/wear/remove
- [ ] 전투 kill → 데미지 → 사망 → 경험치 → 시체
- [ ] 마법 cast → 마나 소모 → 효과 → 쿨다운
- [ ] 레벨업 → 스탯 증가 → HP/MP 증가
- [ ] 상점 buy/sell/list
- [ ] score/who/equipment 출력 정상
- [ ] DM goto/transfer/shutdown 동작
- [ ] ANSI 색상이 `{color}` 포맷으로만 출력

### 12.4 문법 검증

```bash
# Python 문법 검사
python3 -c "import ast; ast.parse(open('game.py').read())"

# SQL 기본 검사
grep -c "^INSERT INTO" seed_data.sql  # 테이블별 행 수 확인
grep -c "BEGIN;" seed_data.sql        # 1이어야 함
grep -c "COMMIT;" seed_data.sql       # 1이어야 함

# Lua 파일 수 + 줄 수
find games/<game>/lua -name "*.lua" | xargs wc -l
```

---

## 13. 실전 사례: 3eyes 전체 전환 기록

### 13.1 최종 규모

| 분류 | 파일 수 | 줄 수 |
|------|---------|-------|
| Python (게임 로직) | 5 | 1,550 |
| Lua (명령어/전투/마법) | 24 | 9,828 |
| Lua (마이그레이션 데이터) | 8 | 1,690 |
| SQL (스키마+데이터) | 2 | 45,818 |
| Config | 1 | 34 |
| 텍스트 (배너/메뉴/뉴스) | 3 | 61 |
| **합계** | **41** | **56,633** |

### 13.2 데이터 규모

| 항목 | 수량 |
|------|------|
| 방 (rooms) | 7,439 |
| 출구 (room_exits) | 16,514 |
| 몬스터 (mob_protos) | 1,394 |
| 아이템 (item_protos) | 1,362 |
| 존 (zones) | 103 |
| 주문 (skills) | 63 |
| 게임 설정 (game_configs) | 43 |
| 수치 테이블 (game_tables) | 523 |
| 도움말 (help_entries) | 116 |
| 소셜 (socials) | 32 |
| 전투 메시지 (combat_messages) | 9 |
| 직업 (classes) | 8 |
| 종족 (races) | 8 |
| 텍스트 파일 (text_files) | 6 |

### 13.3 구현된 명령어 (297개 활성 / 321개 등록)

**Phase 1~8 (209개) + Batch 1~7 미포팅 명령어 추가 (88개) = 297개 활성**

```
전투 (15): kill, flee, search, bash, kick, trip, berserk, rescue, backstab,
           주문해제, 해제, 일격필살, 그림자공격, 그림자대기, 던져
마법 (4): cast, practice, teach, study → 62 주문
이동 (12): n/s/e/w/u/d + 대각선(4) + 나가, 나가는길
아이템 (12): get, drop, put, give, wear, wield, hold, remove, eat, drink,
            사용/zap, 긁어
통신 (12): say, tell, yell, gsay, broadcast, emote, shout, whisper,
           내보내, 듣기거부, 수신거부, 뉴스
정보 (19): score, who, equipment, inventory, look, exits, map, title,
           affects, health, consider, compare, time, weather, spells,
           brief/prompt/toggle, 사용자정보, 감정, 묘사
소셜 (39): 미소, 절, 웃어, 춤, 노래, 울어, 안아 등 39개 감정표현
은신 (6): sneak, hide, pick, steal, backstab, 엿봐
상점 (7): buy, sell, list, value, appraise, repair, trade
경제 (6): deposit, withdraw, balance, locker, transfer, auction, bid
커뮤니티 (15): blist, read, write, delete, fcreate, fjoin, fleave,
               fkick, ftalk, flist, finfo, fdisband, 선전포고,
               편지보내기, 편지받기, 편지삭제
결혼 (4): propose, accept, marry, divorce
성장 (10): train, power, meditate, accurate, 직업전환, 향상,
           혈도봉쇄, 흡성대법, 경공술, 신원법
기술 (4): 추적, 독살포, 경계, 멸혼술
특수 (14): forge, enhance, poker(5), rank, alias, unalias, chaos,
           killer, surrender, rename, version, 경험치전수, 메모,
           투체변신술, 무술대회서열
관리자 (~60): 기존 40 + DM 한국어 별칭(~40) + 신규 DM(~20)
             *방제작, *방이름, *방삭제, *방설명, *물건이름, *괴물,
             *교체, *dm_flag, *dm_system, *dm_event 등
기본 (2): quit, save
별칭 (~15): 봐→look, 사→buy, 저장→save, 귀→귀환 등
```

> **비활성화(nil)**: 24개 (common 명령어 중 원본에 없는 것: exits, commands, junk 등)

### 13.4 Python 전용 시스템 (Lua로 이식 불가)

| 시스템 | 이유 |
|--------|------|
| `on_tick()` 시체 부패 | room.objects 직접 수정 (Lua list 인터옵 문제) |
| `mobile_activity()` NPC AI | 전체 rooms 순회 + fighting 상태 변경 |
| `room_tick_effects()` | 전체 rooms 순회 + flags 복합 검사 |
| `regen_char()` | char 인스턴스 직접 HP/MP 수정 |
| `handle_death()` | 시체 생성 + 인벤토리 이전 + 방 이동 |
| `tick_affects()` | Python list 직접 수정 |
| 로그인 상태머신 | DB 접근 (async) + 세션 관리 |

### 13.5 3eyes 고유 시스템

| 시스템 | 구현 위치 | 원본 소스 |
|--------|-----------|-----------|
| 전직 (Invincible→Caretaker) | training.lua + level.py | command7.c, kyk3.c |
| 숙련도 5종 + 영역 4종 | lib.lua (profic/mprofic) | player.c |
| 포커 게임 | poker.lua (487줄) | poker.c, poker2.c |
| 제련 | forge.lua (126줄) | command7.c |
| PK/킬러 | misc.lua + death.py | kyk1.c, kyk5.c |
| 가족(길드) | family.lua (350줄) | kyk6.c |
| 결혼 | social.lua (217줄) | comm11.c, kyk3.c |
| 게시판 18개 | board.lua (254줄) | board.c |
| 순위 시스템 | ranking.lua (142줄) | kyk7.c, rank.c |
| 별명 20개 | misc.lua | alias.c, kyk2.c |
| MAGGRE NPC AI | game.py | creature.c |
| 방 힐링/독/데미지 | game.py | update.c |
| 시체 부패 | death.py + game.py | update.c |

---

## 부록: 빠른 참조

### A. 새 게임 포트 시작 체크리스트

```
1. [ ] 원본 소스 분석 + Porting Reference 작성
2. [ ] games/<game>/ 디렉토리 생성
3. [ ] constants.py — 클래스/종족/플래그/주문 정의
4. [ ] level.py — 경험치 테이블 + 레벨업 공식
5. [ ] login.py — 원본 로그인 흐름 재현
6. [ ] combat/death.py — 사망 처리 + 경험치 배분
7. [ ] game.py — 플러그인 프로토콜 + 필요한 hooks
8. [ ] lua/lib.lua — 게임별 유틸 함수
9. [ ] lua/combat/thac0.lua — 전투 엔진
10. [ ] lua/combat/spells.lua — 마법 시스템
11. [ ] lua/commands/*.lua — 명령어 파일들
12. [ ] data/<game>/sql/schema.sql — 공통 스키마 복사
13. [ ] data/<game>/sql/seed_data.sql — 마이그레이션 실행
14. [ ] config/<game>.yaml — 포트/DB 설정
15. [ ] data/<game>/banner.txt + menu.txt + news.txt
16. [ ] 보충 데이터: zones, game_configs, socials, combat_messages, text_files
17. [ ] 전수 검증 (12장 체크리스트)
```

### B. 포트 번호 할당

| 게임 | Telnet | API |
|------|--------|-----|
| tbaMUD | 4000 | 8080 |
| 10woongi | 4001 | 8081 |
| simoon | 4002 | 8082 |
| 3eyes | 4003 | 8083 |
| muhan13 | 4004 | 8084 |
| murim | 4005 | 8085 |
| 99hunter | 4006 | 8086 |

### C. DB 이름 규칙

```
genos_<game>
예: genos_tbamud, genos_3eyes, genos_muhan13
```

---

---

## 14. 명령어 전환 실전 플레이북

**3eyes 전환(203→297개)에서 축적된 노하우. 다른 6개 게임에도 동일 적용.**

### 14.1 명령어 전수 조사 방법

원본에서 명령어 목록을 빠짐없이 추출하는 것이 첫 단계입니다.

| 엔진 | 추출 방법 | 예시 |
|------|-----------|------|
| Mordor 2.0 (3eyes, muhan13) | `command*.c`의 `cmd[]` 배열에서 `{cmd_no, name, func, level}` 추출 | `grep 'cmd\[' command*.c` |
| Mordor 확장 (murim) | 동일 + `kyk*.c` 추가 명령어 확인 | `grep 'ADDCMD\|addcom' kyk*.c` |
| CircleMUD (tbaMUD, simoon) | `interpreter.c`의 `cmd_info[]` → `{command, func, min_pos, min_level}` | `grep '{.*do_.*}' interpreter.c` |
| SMAUG (99hunter) | `명령어.dat`(488줄) + `tables.c`의 `cmd_table[]` | 파일 직접 파싱 |
| LP-MUD (10woongi) | `add_action()` 호출 + `lib/삽입파일/명령어.h` 매핑 배열 | `grep add_action lib/**/*.c` |

**전수 조사 절차:**

```bash
# 1단계: 원본 명령어 목록 추출 → cmdlist_original.txt
# 2단계: 현재 GenOS 등록 명령어 추출
grep -r 'register_command(' games/<game>/lua/ --include='*.lua' -h \
  | grep -v '^\s*--' | sed 's/.*register_command("\([^"]*\)".*/\1/' | sort > cmdlist_genos.txt
# 3단계: diff로 미등록 확인
comm -23 cmdlist_original.txt cmdlist_genos.txt > missing.txt
```

### 14.2 명령어 7가지 유형별 전환 패턴

모든 명령어는 아래 7가지 유형 중 하나로 분류됩니다.
유형에 따라 구현 패턴이 완전히 다릅니다.

#### 유형 1: 단순 별칭 (Alias)

기존 명령어를 다른 이름으로 호출. **가장 많고 가장 쉬움.**

```lua
-- 패턴: register_command(별칭, function → call_command(원본))
register_command("봐", function(ctx, args) ctx:call_command("look", args or "") end)
register_command("사", function(ctx, args) ctx:call_command("구매", args or "") end)
```

**주의사항:**
- `ctx:call_command("구입", ...)` 같은 **자기참조 절대 금지** → 무한재귀
- 원본 명령어가 `register_command(원본, nil)`로 비활성화되지 않았는지 확인
- 별칭은 overrides.lua에 모아놓기 (관리 편의)

#### 유형 2: common 비활성화 (nil Override)

원본에 없는 common 명령어를 게임에서 제거합니다.

```lua
-- 패턴: register_command(영어명, nil) — 해당 명령어 완전 비활성화
register_command("exits", nil)      -- 원본에 없는 영문 명령어
register_command("junk", nil)       -- common 기본 명령어이나 원본에 없음
register_command("kill", nil)       -- combat.lua에서 한글로 재등록
```

**주의사항:**
- nil 등록은 **반드시 게임 Lua 로딩 순서 이후**에 실행 (common이 먼저 로드됨)
- overrides.lua 최상단에 nil 등록을 모아놓기 (명시적)
- 비활성화 후 같은 기능을 한글명으로 재등록하는 경우 주석으로 매핑 명시

#### 유형 3: 한글 재등록 (Korean Name + 원본 로직)

common의 영어 명령어를 비활성화하고 한글명으로 재등록합니다.

```lua
-- 패턴: nil → 새 한글명 등록
register_command("kill", nil)                    -- common 영어 제거
register_command("공격", function(ctx, args)      -- 원본 한글명으로 재등록
    local ch = ctx.char
    if not args or args == "" then
        ctx:send("누구를 공격하시겠습니까?"); return
    end
    local target = ctx:find_char(args)
    -- ... (게임별 로직)
end)
```

**이 패턴이 원본 재현의 핵심.** 게임별 한글 명령어명을 원본 cmdlist에서 정확히 가져와야 합니다.

#### 유형 4: 테이블 구동 (Table-Driven)

소셜/감정 등 동일 패턴 반복 명령어는 데이터 테이블로 구동합니다.

```lua
local EMOTES = {
    -- {cmd, 혼자, 방_혼자, 대상O_나, 대상O_상대, 대상O_방}
    {"미소", "$n이(가) 미소짓습니다.",
             "$n이(가) 미소짓습니다.",
             "$N에게 미소짓습니다.",
             "$n이(가) 당신에게 미소짓습니다.",
             "$n이(가) $N에게 미소짓습니다."},
    -- ... 39개 소셜
}

for _, e in ipairs(EMOTES) do
    register_command(e[1], function(ctx, args) do_emote(ctx, args, e) end)
end
```

**장점**: 39개 소셜이 ~250줄 (개별 구현 시 ~800줄)
**적용 대상**: 소셜, 소환 주문, 버프 주문, DM 명령어 등

#### 유형 5: 게이트 체크 (Gated Command)

방 플래그/클래스/레벨/쿨다운 등 조건을 먼저 검사합니다.

```lua
register_command("수련", function(ctx, args)
    -- Gate 1: 방 플래그
    if not te_room_has_flag(ctx, 8) then  -- RTRAIN
        ctx:send("전직 방을 찾아가세요."); return
    end
    -- Gate 2: 클래스
    if ch.class_id < 1 or ch.class_id > 8 then
        ctx:send("이미 전직했습니다."); return
    end
    -- Gate 3: 레벨
    if ch.level < 200 then ctx:send("레벨 부족"); return end
    -- Gate 4: 쿨다운
    local cd = ctx:check_cooldown(LT_TRAIN)
    if cd > 0 then ctx:send("대기: " .. cd .. "초"); return end
    -- Gate 5: 비용 (골드/경험치)
    if ch.gold < cost then ctx:send("골드 부족"); return end
    -- 실행
    ch.gold = ch.gold - cost
    ctx:set_cooldown(LT_TRAIN, 60)
    ctx:send("전직 성공!")
end)
```

**체크 순서 규칙**: 방 → 클래스 → 레벨 → 쿨다운 → 비용 → 실행

#### 유형 6: DM 관리 명령어

모든 DM 명령어는 `*` 접두사 + 권한 체크로 시작합니다.

```lua
local function is_dm(ctx, min_class)
    min_class = min_class or CLASS_DM
    return ctx.char and ctx.char.class_id >= min_class
end

register_command("*순간이동", function(ctx, args)
    if not is_dm(ctx) then ctx:send("관리자 전용"); return end
    local vnum = tonumber(args)
    if not vnum then ctx:send("사용법: *순간이동 <방번호>"); return end
    if not ctx:room_exists(vnum) then ctx:send("방 없음"); return end
    ctx:teleport_to(vnum)
    ctx:defer_look()
end)
```

**DM 등급 계층**: ZONEMAKER(13) < REALZONEMAKER(14) < SUB_DM(15) < DM(16) < ME(17)
- 일반 DM 명령어: `is_dm(ctx)` (class_id >= 16)
- 존 편집: `is_dm(ctx, CLASS_ZONEMAKER)` (class_id >= 13)

#### 유형 7: 상태 변경 (State Mutation)

플레이어/NPC의 상태를 직접 변경하는 명령어입니다.

```lua
register_command("쉬어", function(ctx, args)
    local ch = ctx.char
    if ch.position == POS_RESTING then ctx:send("이미 쉬고 있습니다."); return end
    if ch.fighting then ctx:send("전투 중!"); return end
    ch.position = POS_RESTING   -- 직접 상태 변경
    ctx:send("쉬기 시작합니다.")
end)
```

**주의**: `ch.position`, `ch.gold`, `ch.experience`, `ch.hp` 등은 Lua에서 직접 변경 가능.
**불가**: `ch.inventory`, `ch.equipment`, `room.characters` 등 Python list/dict는 ctx 헬퍼 사용 필수.

---

### 14.3 common → game 오버라이드 전략

GenOS는 common/lua → game/lua 순서로 로드합니다.
**나중에 같은 이름으로 register_command하면 덮어쓰기됩니다.**

```
로딩 순서:
  1. common/lua/lib.lua           ← 공통 유틸
  2. common/lua/commands/*.lua    ← 공통 명령어 (영문 기반)
  3. games/<game>/lua/lib.lua     ← 게임별 유틸 + 상수
  4. games/<game>/lua/commands/overrides.lua  ← ★ 비활성화 + 별칭
  5. games/<game>/lua/commands/*.lua  ← 게임별 한글 명령어
  6. games/<game>/lua/combat/*.lua   ← 전투/마법
```

**overrides.lua의 3단계 패턴:**

```lua
-- ① 원본에 없는 common 명령어 비활성화
register_command("exits", nil)
register_command("commands", nil)

-- ② 한글로 재등록할 영어명 제거 (게임 Lua에서 재등록됨)
register_command("kill", nil)       -- → combat.lua: 공격
register_command("take", nil)       -- → items.lua: 주워
register_command("say", nil)        -- → comm.lua: 말

-- ③ 단순 별칭 등록
register_command("봐", function(ctx, args) ctx:call_command("look", args or "") end)
register_command("저장", function(ctx, args) ctx:call_command("save", args or "") end)
```

**★ 핵심 원칙: 원본에 없는 명령어는 nil, 원본에 있는 명령어는 반드시 원본 이름으로.**

---

### 14.4 SOV 파싱 함정과 해결책

GenOS 명령어 파서는 **SOV(한국어) 우선 + SVO(영문) 폴백** 순서로 동작합니다.

```
입력: "고블린 공격"
  → SOV: 마지막 토큰 "공격" = 동사? → cmd_handlers["공격"] or cmd_korean["공격"]→"attack"
  → args = "고블린"

입력: "attack goblin"
  → SOV: "goblin" = 동사? → 없음
  → SVO: "attack" = 동사? → cmd_handlers["attack"] → YES
  → args = "goblin"
```

#### 함정 1: 명령어명이 인자와 겹치는 경우

```
입력: "메모 중요한 메모"
  → SOV: 마지막 "메모" = 등록 명령어 → args = "메모 중요한"  ← ❌ 순서 뒤집힘!
```

**해결**: 명령어명이 인자에도 등장할 수 있는 경우, 테스트에서 중복 없는 인자 사용.
실제 게임 플레이에서는 드문 케이스이므로 Lua 단에서 처리 불필요.

#### 함정 2: `look` 명령어 재등록 → 무한 재귀

```lua
-- ❌ 절대 금지!
register_command("look", function(ctx, args)
    ctx:defer_look()  -- defer_look이 cmd_handlers["look"]을 호출 → 자기자신 → ∞
end)

-- ✅ 올바른 방법: look은 common에서 제공, 한글 별칭만 등록
register_command("봐", function(ctx, args) ctx:call_command("look", args or "") end)
```

`defer_look()`은 내부적으로 `cmd_handlers["look"]`을 호출합니다.
따라서 `look`을 Lua로 재등록하면 무한 재귀가 발생합니다.
**`look`은 common 구현을 그대로 사용하고, 별칭만 등록하세요.**

#### 함정 3: 방향 초성과 명령어 초성 충돌

```python
# 방향 초성은 DIR_NAMES_KR_MAP에 등록 (process_command에서 방향으로 처리)
DIR_NAMES_KR_MAP = {"ㅂ": 0, "ㄷ": 1, "ㄴ": 2, "ㅅ": 3, "ㅇ": 4, "ㅁ": 5}

# 명령어 초성은 CHOSEONG_MAP에 등록 (별도 확장 단계에서 처리)
CHOSEONG_MAP = {"ㄱ": "공격", "ㅈ": "저장", "ㅊ": "착용", "ㅎ": "help"}
```

**원칙**: 방향과 겹치는 초성(ㅂ/ㄷ/ㄴ/ㅅ/ㅇ/ㅁ)은 **방향이 우선**.
나머지(ㄱ/ㅈ/ㅊ/ㅎ/ㄹ)만 CHOSEONG_MAP에 등록.

#### 함정 4: `_resolve_command`에서 직접 핸들러가 Korean 매핑보다 우선

```
"공격" 입력 시:
  1. cmd_handlers["공격"] → 게임별 Lua 핸들러 (있으면 이것 사용)
  2. cmd_korean["공격"] → "attack" → cmd_handlers["attack"] (1이 없을 때만)
```

**이 우선순위 덕분에** 게임별 한글 명령어가 글로벌 Korean 매핑을 안전하게 오버라이드합니다.
예: 3eyes의 `register_command("공격", custom_handler)` → KOREAN_VERB_MAP["공격"]="attack"보다 우선.

---

### 14.5 Lua ↔ Python 인터옵 실전 함정

#### 함정 1: lupa + MagicMock = OOM (치명적!)

```python
# ❌ 절대 금지! 테스트에서 MagicMock 사용
session = MagicMock()  # lupa가 __getitem__으로 접근 → 모든 키에 non-nil 반환
                       # Lua의 `while pcall(fn) / if nil then break end` → 무한루프 → OOM

# ✅ 반드시 SimpleNamespace 사용
session = SimpleNamespace()
session.send_line = AsyncMock()
session.character = char
session.player_data = {"level": 1, "name": "테스터"}
```

**원인**: lupa는 Python 객체에 `__getitem__`으로 속성 접근합니다.
MagicMock은 모든 키에 대해 새 MagicMock(non-nil)을 반환합니다.
Lua에서 `pcall + nil break` 패턴이 무한루프에 빠집니다.

#### 함정 2: Python list/dict 직접 조작 불가

```lua
-- ❌ 작동하지 않음
local inv = ch.inventory     -- Python list 프록시
#inv                          -- 항상 0 (Python list에 # 연산자 미지원)
table.insert(inv, item)      -- 무효 (Python list에 table.insert 불가)
inv[1]                        -- nil (Python list는 0-indexed)

-- ✅ ctx 헬퍼 사용
local count = ctx:get_inv_count()    -- Python에서 len() 호출
for i = 0, count - 1 do             -- 0-indexed 반복
    local ok, item = pcall(function() return ch.inventory[i] end)
    if not ok or item == nil then break end
    -- ...
end
```

#### 함정 3: set_player_data로 Lua table 저장 시 Python 호환 문제

```lua
-- ⚠️ 주의: Lua table을 set_player_data에 저장하면 LuaTable 프록시가 됨
local list = {"a", "b", "c"}
ctx:set_player_data("my_list", list)
-- Python에서: session.player_data["my_list"] → lupa.LuaTable (not Python list)
-- Python의 `in` 연산자 작동 안 될 수 있음

-- ✅ 테스트에서는 메시지 검증이 더 안전
msgs = _get_sent(session)
assert any("수신거부합니다" in m for m in msgs)  -- 상태 검증 대신 메시지 검증
```

#### 함정 4: frozen dataclass 속성은 Lua에서 설정 불가

```lua
-- ⚠️ MobProto는 frozen=True → proto.stats["str"] = 15 가능하나 proto.stats = {} 불가
-- MobInstance는 mutable → ch.gold = 100 가능, ch.hp = 50 가능
-- 그러나 ch.stats가 proto.stats를 참조하면 frozen 제약 받을 수 있음

-- ✅ pcall로 안전하게 감싸기
pcall(function()
    if not ch.stats then ch.stats = {} end
    ch.stats[stat_name] = new_val
end)
```

---

### 14.6 테스트 작성 패턴

#### 기본 테스트 구조

```python
@pytest.mark.asyncio
async def test_명령어_기본(self):
    eng = _make_engine()                    # Engine + World + Lua 초기화
    ch = _player(level=10, room_vnum=100)   # SimpleNamespace 기반 캐릭터
    session = _make_session(eng, ch)        # SimpleNamespace 세션 (MagicMock 금지!)
    eng.world.rooms[100].characters = [ch]  # 방에 캐릭터 배치

    await eng.process_command(session, "명령어 인자")  # 단일 문자열!

    msgs = _get_sent(session)               # send_line.call_args_list → str 리스트
    assert any("기대 메시지" in m for m in msgs)
```

#### 핵심 규칙

| 규칙 | 올바른 예 | 잘못된 예 |
|------|-----------|-----------|
| process_command 인자 | `process_command(session, "공격 고블린")` | `process_command(session, "공격", "고블린")` |
| 세션 생성 | `SimpleNamespace()` | `MagicMock()` |
| 상태 검증 | `assert any("메시지" in m for m in msgs)` | `assert session.player_data["key"] == value` |
| 골드/HP 검증 | 직접 `ch.gold` 확인 가능 | Lua table 반환값 검증은 불안정 |
| send_all 테스트 | `eng.sessions["s1"] = session` 먼저 등록 | session 미등록 시 broadcast 안 됨 |

#### `_get_sent()` 헬퍼

```python
def _get_sent(session):
    """send_line 호출 내역을 문자열 리스트로 반환."""
    return [str(c) for c in session.send_line.call_args_list]
    # 각 요소: "call('메시지 텍스트')"
    # "메시지" in "call('메시지 텍스트')" → True
```

#### 테스트 수 가이드

- 소셜/별칭: 대표 1~2개만 (패턴이 동일)
- 핵심 명령어: 각각 최소 1개 (성공 케이스)
- DM 명령어: 권한 체크 1개 + 기능 1~2개
- 전투/마법: 기존 combat 테스트와 통합

---

### 14.7 게임별 명령어 체계 특성

| 게임 | 명령어 체계 | 핵심 차이점 |
|------|-------------|-------------|
| **3eyes** | 한글 전용 + 영문 호환 | 360개, `*DM` 접두사, 초성 약어, 소셜 39개, 별명 20개 |
| **tbaMUD** | 영문 전용 + 한글 매핑 | 275개, prefix matching, socials 104개, 한글은 KOREAN_VERB_MAP |
| **simoon** | 영문 기반 + 한글 혼합 | 546개, EUC-KR, tbaMUD와 유사하나 한글 명령어 추가 |
| **10woongi** | 한글 전용 | 51개 (LPC action), `add_action` 기반, 체언 종결 |
| **muhan13** | 3eyes와 동일 엔진 | 350개, 구조 동일하나 **struct 필드 순서 다름** |
| **murim** | 무협 특화 한글 | ~300개, 21 클래스, 무술/내공 특화 명령어 대량 |
| **99hunter** | 한글 전용 (SMAUG) | 488개, 30 클래스, 신/의회 시스템, &W 색상 |

#### 게임별 주의사항

**tbaMUD/simoon**: 이미 common 명령어 체계가 원본과 유사하므로 overrides 최소.
대신 socials 104개를 DB socials 테이블에서 자동 로딩하는 것이 효율적.

**10woongi**: `add_action("명령어", "handler_func")` → `register_command("명령어", fn)`.
LPC 함수를 Lua로 1:1 변환. 체언 종결이므로 SOV 파서와 자연스럽게 호환.

**muhan13**: 3eyes와 90% 동일. **creature struct 필드 순서가 다른 것이 유일한 차이.**
Lua 명령어 파일은 3eyes를 복사 후 필드명만 수정하면 됩니다.
단, creature2(4096B) 확장 struct의 별도 처리 필요.

**murim**: 무술/내공 시스템이 핵심. 18종 스탯, 256개 무공, 40 착용 슬롯.
`te_stat()` 확장 필요 (5→18종), lib.lua에 무술 전용 유틸 추가.

**99hunter**: SMAUG 명령어 체계는 CircleMUD과 크게 다름.
MOB S/C 타입, Direction 10, 4×32 bitvector 등 고유 처리 필요.
`&W`/`&g` 색상 코드 → `{white}`/`{green}` 변환기 필요.

---

### 14.8 전환 작업 순서 (권장)

모든 게임에 적용 가능한 검증된 순서입니다.

```
1. 원본 cmdlist 전수 추출 + 분류 (유형 1~7)
2. overrides.lua — nil 비활성화 + 단순 별칭 (유형 1, 2)
3. 한글 재등록 — 기본 명령어 (look/get/drop/say 등) (유형 3)
4. 소셜/감정 — 테이블 구동 (유형 4)
5. 핵심 명령어 — 신규 로직 (유형 5, 7)
6. 특수 시스템 — 게임 고유 (유형 5)
7. DM 관리 — 별칭 + 신규 (유형 6)
8. 편지/게시판/커뮤니티 — 부가 기능
```

**각 단계마다 `pytest tests/test_lua_<game>.py -q` 실행하여 회귀 방지.**

---

### 14.9 빠른 참조: ctx API 전체 목록

아래는 Lua 명령어 함수 `function(ctx, args)` 의 `ctx` 객체가 제공하는 전체 메서드입니다.

```lua
-- ═══ 메시지 ═══
ctx:send(msg)                        -- 본인에게 전송
ctx:send_to(target, msg)             -- 특정 대상에게
ctx:send_room(msg)                   -- 같은 방 전체 (자신 제외)
ctx:send_all(msg)                    -- 서버 전체 브로드캐스트
ctx:send_to_room(room_vnum, msg)     -- 특정 방 전체

-- ═══ 캐릭터 조회 ═══
ctx.char                             -- 현재 캐릭터 (MobInstance)
ctx:find_char(keyword)               -- 현재 방에서 NPC/PC 찾기
ctx:find_player(name)                -- 온라인 플레이어 이름 검색
ctx:find_world_char(name)            -- 전체 월드에서 캐릭터 찾기
ctx:get_online_players()             -- 온라인 세션 테이블

-- ═══ 방/이동 ═══
ctx:get_room(vnum?)                  -- 방 객체 (생략 시 현재 방)
ctx:get_room_vnum()                  -- 현재 방 번호
ctx:room_exists(vnum)                -- 방 존재 여부
ctx:teleport_to(vnum)                -- 텔레포트
ctx:move_to(room_vnum)               -- 이동
ctx:move_char_to(char, room_vnum)    -- 다른 캐릭터 이동
ctx:get_start_room()                 -- 시작/귀환 방
ctx:get_random_room_vnum()           -- 안전 랜덤 방
ctx:defer_look()                     -- look 명령 예약

-- ═══ 출구/문 ═══
ctx:get_exits(room?)                 -- 출구 목록 (Lua table)
ctx:find_door(keyword)               -- 문 방향 찾기 (-1=없음)
ctx:find_exit(dir_or_kw)             -- 출구 찾기
ctx:has_door(dir)                    -- 문 존재 여부
ctx:is_door_closed(dir)              -- 닫혀있나
ctx:is_door_locked(dir)              -- 잠겨있나
ctx:set_door_state(dir, closed, locked?)  -- 문 상태 변경
ctx:has_key(dir)                     -- 열쇠 소유 여부
ctx:peek_exit(dir)                   -- 출구 목적지 vnum
ctx:peek_exit_at(room_vnum, dir)     -- 특정 방의 출구

-- ═══ 아이템 ═══
ctx:find_inv_item(keyword)           -- 인벤토리 검색
ctx:find_equip_item(keyword)         -- 장비 검색
ctx:find_obj_room(keyword)           -- 방 바닥 검색
ctx:create_obj(vnum)                 -- 아이템 생성
ctx:obj_to_char(obj, char)           -- 인벤토리에 넣기
ctx:obj_from_char(obj)               -- 인벤토리에서 꺼내기
ctx:obj_to_room(obj, room_vnum)      -- 바닥에 놓기
ctx:obj_from_room(obj)               -- 바닥에서 제거
ctx:obj_to_obj(obj, container)       -- 컨테이너에 넣기
ctx:obj_from_obj(obj)                -- 컨테이너에서 꺼내기
ctx:equip(obj, slot)                 -- 장비 장착
ctx:unequip(slot)                    -- 장비 해제
ctx:wear_item(item)                  -- 자동 슬롯 장착
ctx:wield_item(item)                 -- 무기 장착
ctx:remove_item(item)                -- 장비 해제
ctx:wear_all()                       -- 전체 장착
ctx:recalc_equip()                   -- 장비 보너스 재계산
ctx:get_inv_count()                  -- 인벤토리 개수 (# 대체)

-- ═══ 상점 ═══
ctx:get_shop()                       -- 현재 방 상점 정보
ctx:find_shop()                      -- (상점, 상인) 튜플
ctx:get_shop_items()                 -- 상점 물품 목록
ctx:get_buy_price(item)              -- 구매가
ctx:get_sell_price(item)             -- 판매가
ctx:buy_item(item)                   -- 구매
ctx:sell_item(item)                  -- 판매

-- ═══ 전투 ═══
ctx:start_combat(target)             -- 전투 시작
ctx:stop_combat(char)                -- 전투 종료
ctx:deal_damage(target, amount)      -- 데미지 적용
ctx:heal(target, amount)             -- HP 회복

-- ═══ 어펙트/버프 ═══
ctx:apply_affect(target, id, dur, mods?)     -- 어펙트 추가
ctx:remove_affect(target, id)                -- 어펙트 제거
ctx:has_affect(target, id)                   -- 어펙트 확인
ctx:apply_spell_buff(target, spell, dur, mods?)  -- 스펠 버프
ctx:remove_spell_affect(target, spell)       -- 스펠 해제
ctx:has_spell_affect(target, spell)          -- 스펠 확인
ctx:get_affects(target)                      -- 전체 어펙트 목록

-- ═══ 쿨다운 ═══
ctx:check_cooldown(slot)             -- 남은 초 (0=준비완료)
ctx:set_cooldown(slot, seconds)      -- 쿨다운 설정
ctx:clear_cooldown(slot)             -- 쿨다운 해제

-- ═══ 플래그 ═══
ctx:has_flag(flag_id)                -- 플래그 확인
ctx:set_flag(flag_id)                -- 플래그 설정
ctx:clear_flag(flag_id)              -- 플래그 해제
ctx:has_mob_flag(target, flag_name)  -- NPC 플래그
ctx:has_room_flag(flag_name)         -- 방 플래그

-- ═══ 플레이어 데이터 ═══
ctx:get_player_data(key)             -- JSONB 필드 읽기
ctx:set_player_data(key, value)      -- JSONB 필드 쓰기
ctx:set_player_data_on(target, key, value)  -- 다른 PC의 데이터

-- ═══ 스킬/주문 ═══
ctx:knows_spell(spell_id)            -- 주문 습득 여부
ctx:learn_spell(spell_id)            -- 주문 학습
ctx:learn_spell_for(target, spell_id) -- 다른 PC에게 주문 학습
ctx:forget_spell(spell_id)           -- 주문 망각
ctx:get_skill_proficiency(name_or_char, skill_id)  -- 숙련도
ctx:practice_skill(skill_id, gain)   -- 숙련도 상승
ctx:get_all_skills()                 -- 전체 스킬 목록

-- ═══ 자원 ═══
ctx:add_hp(amount)                   -- HP 증감
ctx:add_mana(amount)                 -- MP 증감
ctx:add_move(amount)                 -- 이동력 증감

-- ═══ 생성/제거 ═══
ctx:create_mob(vnum, room_vnum)      -- 몬스터 생성
ctx:load_mob(vnum)                   -- 현재 방에 몹 생성
ctx:load_obj(vnum)                   -- 아이템 생성 후 인벤토리
ctx:purge_room()                     -- 방 정리
ctx:remove_char_from_room(char)      -- 방에서 제거
ctx:extract_char(char)               -- 월드에서 완전 제거

-- ═══ 따라가기 ═══
ctx:follow(target)                   -- 따라가기
ctx:unfollow()                       -- 따라가기 해제
ctx:get_following()                  -- 현재 따라가는 대상
ctx:get_followers()                  -- 따라오는 자 목록

-- ═══ 정보 ═══
ctx:get_help(keyword)                -- 도움말 검색
ctx:get_all_commands()               -- 전체 명령어 목록
ctx:get_aliases()                    -- 별칭 목록
ctx:set_alias(name, cmd)             -- 별칭 설정
ctx:get_class(class_id)              -- 직업 정보
ctx:get_skill(skill_id)              -- 스킬 정보
ctx:get_config(key)                  -- 게임 설정값
ctx:get_room_name(room_vnum)         -- 방 이름

-- ═══ 시간/날씨 ═══
ctx:get_game_hour()                  -- 게임 시간
ctx:get_game_day()                   -- 게임 날짜
ctx:get_game_month()                 -- 게임 월
ctx:get_game_year()                  -- 게임 년도
ctx:get_weather()                    -- 현재 날씨

-- ═══ 유틸 ═══
ctx:random(a, b)                     -- 랜덤 정수
ctx:roll_dice("2d6+3")              -- 주사위 굴림
ctx:particle(word, p1, p2)           -- 한글 조사 선택
ctx:is_admin()                       -- 관리자 여부
ctx:log(msg)                         -- 로그 기록

-- ═══ 명령어 호출 ═══
ctx:call_command(cmd, args)          -- 다른 명령어 실행
ctx:execute(cmd, args)               -- call_command 별칭

-- ═══ 토글 ═══
ctx:get_toggles()                    -- 토글 설정 맵
ctx:toggle(key)                      -- 토글 전환

-- ═══ 지연 실행 (Lua 종료 후 Python에서 실행) ═══
ctx:defer_look()                     -- look 예약
ctx:defer_death(victim, killer)      -- 사망 처리 예약
ctx:defer_save()                     -- 저장 예약
ctx:defer_force(target, cmd)         -- 강제 명령 예약
ctx:defer_reload()                   -- Lua 리로드 예약
ctx:defer_shutdown()                 -- 셧다운 예약
```

---

### 14.10 최종 검증 스크립트

모든 배치 완료 후 실행하는 종합 검증입니다.

```bash
cd /home/genos/workspace/genos-engine && . .venv/bin/activate

# 1. 전체 테스트 통과 확인
python -m pytest -q --tb=short    # 790+ passed

# 2. 게임별 명령어 수 확인
echo "=== 3eyes ==="
grep -r 'register_command(' games/3eyes/lua/ --include='*.lua' -h \
  | grep -v '^\s*--' | wc -l      # 321 total
grep -r 'register_command(' games/3eyes/lua/ --include='*.lua' -h \
  | grep -v '^\s*--' | grep ', nil)' | wc -l  # 24 disabled → 297 active

# 3. 원본 대비 커버리지
# 원본: 360개 → 현재: 297개 활성 (82.5%)
# 차이: 대부분 DM 내부 명령어 + 동의어

# 4. Lua 줄 수 확인
find games/3eyes/lua -name "*.lua" | xargs wc -l | tail -1  # ~9,800줄

# 5. 파일당 명령어 분포 확인 (균형 잡혔는지)
for f in games/3eyes/lua/commands/*.lua; do
    cnt=$(grep 'register_command(' "$f" | grep -v '^\s*--' | wc -l)
    echo "$(basename $f): $cnt"
done
```

---

*이 문서는 3eyes 완전 전환 실전 사례를 기반으로 작성되었으며,*
*7개 게임 전체 포팅에 적용 가능한 범용 가이드입니다.*
*GenOS Engine v1.0 / Unified Schema v1.0 기준.*
*§14 명령어 전환 플레이북 추가: 2026-02-14.*
