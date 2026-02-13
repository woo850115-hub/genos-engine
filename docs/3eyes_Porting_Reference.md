# 3eyes MUD 완전 이식 참조 문서

**Phase A-3 | 2026-02-13**

---

## 1. 개요

제3의 눈(3eyes)은 Mordor 2.0 기반 한국어 MUD로, 93개 C 소스 파일,
356개 명령어, 62개 주문으로 구성된 대규모 시스템이다.
GenOS 엔진에 원본 충실도 100%로 이식한다.

### 원본 규모

| 항목 | 수치 |
|------|------|
| C 소스 파일 | 93개 |
| 명령어 (cmdlist[]) | 356개 |
| 주문 (spllist[]/ospell[]) | 62개 |
| 방 | 7,439 |
| 아이템 | 1,362 |
| 몬스터 | 1,394 |
| 존 | 103 |
| 직업 | 8 기본 + 9 고급 = 17 |
| 종족 | 8 |
| 무기숙련 | 5종 |
| 마법영역 | 4종 |
| 게시판 | 18개 |
| 가족(길드) | 16개 |

### 현재 구현 상태 (이식 전)

| 항목 | 구현 | 미구현 |
|------|------|--------|
| 명령어 | ~40 | ~316 |
| 주문 | 62 (정의만) | 62 (효과 미구현) |
| 전투 공식 | 간소화 | 원본 충실 복원 필요 |
| NPC AI | 없음 | MAGGRE/MFLEER/MMAGIC |
| 은행 | 없음 | bank.c 전체 |
| 게시판 | 없음 | board.c 전체 (18개) |
| 제련 | 없음 | command7.c forge |
| 가족(길드) | 없음 | command4.c/kyk6.c |
| 결혼 | 없음 | comm11.c/kyk3.c |
| 경매 | 없음 | kyk1.c |
| 포커 | 없음 | poker.c/poker2.c |
| 전직 | 없음 | command7.c train |
| DM 명령어 | ~10 | ~50 |

---

## 2. 원본 소스 파일 맵

```
/home/genos/workspace/3eyes/src/
├── mstruct.h          — 핵심 구조체 (creature, object, room, exit_)
├── mtype.h            — 플래그/상수 정의 (모든 #define)
├── mextern.h          — 외부 변수/함수 선언
├── global.c           — cmdlist[356], spllist[62], ospell[26], thaco_list, class_stats, level_exp, bonus
├── player.c           — compute_thaco(), mod_profic(), profic(), mprofic(), up_level(), weight_ply()
├── creature.c         — check_for_flee(), die(), add_enm_crt(), lowest_piety()
├── command1.c         — look, inventory, equipment, score, health
├── command2.c         — backstab, search, steal, hide, sneak, peek
├── command3.c         — 방향이동, open, close, lock, unlock, flee
├── command4.c         — go, follow, group, say, tell, yell, 가족 명령어
├── command5.c         — attack(), attack_crt(), who, title, description
├── command6.c         — get, drop, put, give, wear, wield, hold, remove
├── command7.c         — train(), forge(), buy, sell, list, value, repair, shop, trade
├── command8.c         — ready, compare, time, weather, exits, brief, toggle
├── command9.c         — sit, stand, rest, sleep, wake, quit, save
├── comm10.c           — gsay, gtalk, broadcast, dm commands (일부)
├── comm11.c           — family talk, marriage, divorce, online deposit
├── comm12.c           — 소식, 투표, 버전, 경험치이전
├── magic1.c           — cast(), teach(), offensive_spell(), spllist lookup
├── magic2.c           — vigor, light, bless, protection, teleport, recall
├── magic3.c           — summon, fly, levitate, heal, cure poison
├── magic4.c           — enchant, detect_invis, detect_magic, blindness cure
├── magic5.c           — resist fire/cold/magic, water breathing, earth shield
├── magic6.c           — fear, silence, charm, room_vigor, transport
├── magic7.c           — track, locate, blind, know_alignment, remove_curse
├── magic8.c           — spell_fail(), drain_exp, disease cure, advanced spells
├── kyk1.c             — 경매(auction), 킬러(killer) 시스템
├── kyk2.c             — 게시판, 별명
├── kyk3.c             — comp_chance(), aim_exp(), marriage helper, 전직 helper
├── kyk4.c             — 포커(poker) 시스템
├── kyk5.c             — 킬러 감옥, PK 시스템
├── kyk6.c             — 가족(family/guild) 시스템
├── kyk7.c             — 순위(rank), 무술순위
├── kyk8.c             — 타자이벤트, 이름변경, 그림자공격
├── bank.c             — 은행 (입금/출금/보관/온라인송금)
├── board.c            — 게시판 18개 (글쓰기/보기/삭제/목록)
├── poker.c/poker2.c   — 포커 게임
├── map.c              — ASCII 지도 표시
├── alias.c            — 별명(alias) 시스템
├── rank.c             — 순위 시스템
├── dm1-6.c            — DM(관리자) 명령어 (~60개)
└── io.c/combat.c/...  — 네트워크, 전투 루프 등
```

---

## 3. 핵심 공식 — 원본 C 소스 기준

### 3-1. compute_thaco() — THAC0 계산 (player.c:1131-1162)

```c
void compute_thaco(ply_ptr) {
    n = (level/10) >= 20 ? 19 : (level/10);
    thaco = thaco_list[class][n];

    // 무기 adjustment (마법 무기 보너스)
    if(ready[WIELD-1])
        thaco -= ready[WIELD-1]->adjustment;

    // 무기숙련 보너스
    thaco -= mod_profic(ply_ptr);

    // STR 보너스 (-4 ~ +7 범위 제한)
    t = MIN(7, MAX(-4, bonus[strength]));
    thaco -= t;

    // 클래스별 최종 범위 제한
    if(class < INVINCIBLE):     thaco ∈ [0, 20]
    else if(class < CARETAKER): thaco ∈ [-5, 10]
    else:                       thaco ∈ [-10, 0]

    // PBLESS 보너스
    if(PBLESS): thaco -= 3;
}
```

### 3-2. attack_crt() — 공격 처리 (command5.c:132-438)

```
1. 쿨다운 검사 (LT_ATTCK)
2. PHIDDN/PINVIS 해제
3. 다중 공격 횟수 결정:
   - 기본 1회
   - PUPDMG + Invincible lv100+: (level-97)/10 + mrand(0,3) > 2 → +1
   - PUPDMG + Caretaker+: mrand(1,4) == 1 → +1
   - mrand(0,3) > 2 → +1 (backswing)
   - backswing 시 mrand(1,4) == 1 → +1

4. 각 공격마다:
   a. 무기 파손 검사 (shotscur < 1)
   b. 히트 판정: mrand(1,30) >= thaco - armor/10
      - PFEARS: +2, PBLIND: +5
   c. 데미지 계산:
      - 무기 있음: mdice(weapon) + bonus[STR] + profic(weapon_type)/10
      - 야만인/무적자+ 맨손: mdice(char) + bonus[STR] + comp_chance()
      - 일반 맨손: mdice(char) + bonus[STR]
      - Mage/Cleric: 무기 숙련도 보너스 없음
   d. 크리티컬: mrand(1,100) <= mod_profic() → +n*mrand(3,6)-n
      - OALCRT 무기: 항상 크리티컬
   e. 무기 떨어뜨림: mrand(1,300) <= (5-mod_profic()) && !OCURSE
   f. 그림자 공격 (SHADOW_ATTACK): 별도 데미지 인스턴스
   g. 결혼 파워: 배우자 같은 방 → 데미지 2배
   h. 무기숙련 증가: addprof = (damage * monster_exp) / monster_max_hp
```

### 3-3. mod_profic() — 무기숙련 보너스 (player.c:1170-1203)

```
클래스별 나눗수(amt):
  Fighter/Barbarian/Invincible/Caretaker+: 20
  Ranger/Paladin: 25
  Thief/Assassin/Cleric: 30
  Mage (default): 40

리턴값 = profic(ply_ptr, weapon_type) / amt
  → 무기 장착 시: weapon.type 사용
  → 맨손: BLUNT(2) 사용
```

### 3-4. profic() — 숙련도 백분율 (player.c:1261-1345)

```
12단계 경험치→백분율 변환 테이블 (클래스별):

Fighter/Invincible/Caretaker+/DM:
  0, 768, 1024, 1440, 1910, 16000, 31214, 167000, 268488, 695000, 934808, 500M

Barbarian:
  0, 1536, 2048, 2880, 3820, 32000, 62428, 334000, 536976, 1390000, 1869616, 500M

Thief/Ranger:
  0, 2304, 3072, 4320, 5730, 48000, 93642, 501000, 805464, 2085000, 2804424, 500M

Cleric/Paladin/Assassin:
  0, 3072, 4096, 5076, 7640, 64000, 124856, 668000, 1073952, 2780000, 3939232, 500M

Mage:
  0, 5376, 7168, 10080, 13370, 112000, 218498, 1169000, 1879416, 4865000, 6543656, 500M

알고리즘:
  for i=0..10: if raw < table[i+1]: prof = 10*i; break
  prof += (raw - table[i]) * 10 / (table[i+1] - table[i])
  return MIN(100, prof)
```

### 3-5. mprofic() — 마법영역 숙련도 (player.c:1353-1419)

```
Mage/Invincible/Caretaker+/DM:
  0, 1024, 2048, 4096, 8192, 16384, 35768, 85536, 140000, 459410, 2073306, 500M

Cleric:
  0, 1024, 4092, 8192, 16384, 32768, 70536, 119000, 226410, 709410, 2973307, 500M

Paladin/Ranger:
  0, 1024, 8192, 16384, 32768, 65536, 105000, 165410, 287306, 809410, 3538232, 500M

Default (Fighter/Barbarian/Thief/Assassin):
  0, 1024, 40000, 80000, 120000, 160000, 205000, 222000, 380000, 965410, 5495000, 500M

동일 알고리즘 (realm[index-1] 사용, 1-indexed)
```

### 3-6. comp_chance() — 종합 레벨 보정치 (kyk3.c:757-769)

```c
int comp_chance(creature *ply_ptr) {
    lev = level;
    if(class >= INVINCIBLE) lev += 150;
    if(class >= CARETAKER)  lev += 150;
    return MIN(80, lev / 6);
}
```

사용처: spell_fail, 도둑술 확률, 무게 계산, 추적, 쿨다운 지속시간 등

### 3-7. spell_fail() — 주문 실패 확률 (magic8.c:837-943)

```
공식: chance = (comp_chance + bonus[INT]) * mult + base
     → mrand(1,100) > chance이면 실패

클래스별 (mult, base):
  Assassin:  (5, 30)
  Barbarian: (5, 0)
  Cleric:    (5, 65)
  Fighter:   (5, 10)
  Mage:      (5, 75)
  Paladin:   (5, 50)
  Ranger:    (4, 56)
  Thief:     (6, 22)
  Invincible+: 항상 성공 (default case)
```

### 3-8. offensive_spell() — 공격 주문 (magic1.c:819-1050)

```
1. 마나 검사 (osp->mp)
2. S_ISSET 검사 (주문 학습 여부)
3. PINVIS 해제
4. 보너스 계산 (how == CAST일 때):
   bonus_type 1: INT_bonus + mprofic(realm)/10
   bonus_type 2: INT_bonus + mprofic(realm)/6
   bonus_type 3: INT_bonus + mprofic(realm)/4

5. 영역 보너스 (방 플래그):
   같은 영역: bns *= 2
   반대 영역: bns = MIN(-bns, -5)
   대립쌍: WATER↔FIRE, WIND↔EARTH

6. 데미지: dice(ndice, sdice, pdice + bns)
7. 마나 차감 + spell_fail 검사
8. 영역 숙련도 증가: addrealm = (dmg * mob_exp) / mob_max_hp
```

### 3-9. cast() — 주문 시전 흐름 (magic1.c:24-129)

```
1. 주문 이름 파싱 (spllist[] 부분일치)
2. PBLIND 검사
3. RNOMAG 방 검사
4. LT_SPELL 쿨다운 검사
5. PHIDDN 해제
6. 주문 함수 호출 (offensive_spell 또는 개별 함수)
7. 쿨다운 설정:
   Cleric/Mage/Caretaker+: 3초
   DM+: 1초
   기타: 5초
   특수: 드래곤슬레이브 +3초, 기가슬레이브 +25초, 고급주문 +1초
```

---

## 4. 플래그 시스템 (mtype.h)

### 4-1. 플레이어 플래그 (64-bit, flags[8])

```
비트  이름       설명
0     PBLESS    축복 (THAC0 -3)
1     PHIDDN    은신
2     PINVIS    투명
4     PNOSUM    소환 불가
5     PBLIND    실명 (공격 +5, 주문 불가)
6     PCHARM    매혹
7     PFEARS    공포 (공격 +2)
9     PHASTE    가속 (공격 간격 1초)
10    PCHAOS    카오스 (PK 가능)
12    PPOISN    중독
13    PDISEA    질병
14    PANSIC    ANSI 색상 사용
15    PBRIGH    밝은 색상
18    PDINVI    투명 감지
19    PDMAGC    마법 감지
20    PKNOWA    성향 감지
22    PFLY      비행
23    PLEVIT    공중부양
24    PWATER    수중호흡
25    PSHIEL    돌방패
26    PRFIRE    화염저항
27    PRCOLD    냉기저항
28    PRMAGI    마법저항
29    PMARRI    결혼
30    PFAMIL    가족(길드) 소속
33    PNOHPGRAPH HP 그래프 비표시
34    PDMINV    DM 투명
35    PDIRTY    접속자 목록 비표시
36    PUPDMG    파워업그레이드 (추가 공격)
37    PSILNC    침묵 (말하기 불가)
42    PLIGHT    빛 주문
43    PTRACK    추적 중
```

### 4-2. 몬스터 플래그

```
0     MAGGRE    공격적 (자동 공격)
1     MFLEER    도주 (HP < 20%)
2     MUNKIL    불사 (공격 불가)
3     MMGONL    마법만 통함
4     MENONL    마법무기만 통함
7     MMALES    남성
15    MMAGIC    전투중 마법 시전
```

### 4-3. 방 플래그

```
0     RDARKR    항상 어두움
1     RDARKN    밤에만 어두움
2     RNOKIL    PK 금지
3     RNOMAG    마법 금지
4     RNOTEL    텔레포트 금지
5     RHEALR    치유 방 (자동 HP 회복)
6     RBANK     은행
7     RSHOP     상점
8     RTRAIN    전직 방
9     RREPAI    수리점
10    RFORGE    제련소
11    RPOKER    포커룸
12    REARTH    대지 영역 보너스
13    RWINDR    바람 영역 보너스
14    RFIRER    화염 영역 보너스
15    RWATER    물 영역 보너스
17    RSUVIV    서바이벌 (PK 구역)
19    RPHARM    유해 방 (HP 감소)
20    RPPOIS    독 방
21    RPMPDR    MP 감소 방
22    RNOMAP    지도 불가
23    REVENT    이벤트 방
24    RFAMIL    가족 전용 방
27    RMARRI    결혼식 방
28    RKILLR    킬러 감옥
```

### 4-4. 오브젝트 플래그

```
0     OINVIS    투명
1     ONODRP    버리기 불가
2     OCURSE    저주 (벗기/떨어뜨리기 불가)
3     OWTLES    무게 없음
5     OCLIMB    등반 장비
6     OLIGHT    광원
10    OPOISN    독 바른 무기
41    ONSHAT    파손 불가
42    OALCRT    항상 크리티컬
50    OSHADO    그림자 공격 부여
```

---

## 5. 쿨다운 시스템 (lasttime[45])

```
슬롯  이름          기본 간격
0     LT_ATTCK     1~6초 (클래스/상태별)
1     LT_SPELL     1~30초 (클래스/주문별)
2     LT_HEALS     3초
3     LT_STEAL     5초
4     LT_PICKL     3초
5     LT_SEARC     3초
6     LT_TRACK     10초
7     LT_PLYER     3초
8     LT_HIDE      5초
9     LT_TURNS     3초
10    LT_RENEW     3초
11    LT_LIGHT     300+(comp_chance*300)초
12    LT_INVIS     300+(comp_chance*300)초
13    LT_VIGOR     3초
14    LT_DETCT     300초
15    LT_BLESS     300초
16    LT_PROTE     300초
17    LT_MEDITATE  60초
18    LT_POWER     60초
19    LT_ACCUR     60초
20    LT_SNEAK     5초
30    LT_TRAIN     60초
31    LT_FORGE     60초
32    LT_POKER     3초
```

---

## 6. 주문 목록 (62개)

### 6-1. 공격 주문 (ospell[] — 26개)

| ID | 한글 | 영역 | MP | 주사위 | 보너스타입 |
|----|------|------|-----|--------|-----------|
| 1  | 상처 | WIND | 3 | 1d8+0 | 1 |
| 6  | 화염구 | FIRE | 8 | 2d8+2 | 1 |
| 13 | 번개 | WIND | 12 | 3d6+3 | 1 |
| 14 | 얼음폭발 | WATER | 15 | 3d8+5 | 1 |
| 25 | 충격 | WIND | 5 | 1d12+1 | 1 |
| 26 | 지진파 | EARTH | 7 | 2d6+2 | 1 |
| 27 | 화상 | FIRE | 6 | 1d10+2 | 1 |
| 28 | 수포 | FIRE | 10 | 2d8+3 | 2 |
| 29 | 먼지돌풍 | WIND | 8 | 2d6+2 | 2 |
| 30 | 물화살 | WATER | 6 | 1d10+1 | 1 |
| 31 | 분쇄 | EARTH | 12 | 3d6+4 | 2 |
| 32 | 삼킴 | WATER | 15 | 3d8+5 | 2 |
| 33 | 폭발 | FIRE | 18 | 4d6+5 | 2 |
| 34 | 증기 | WATER | 16 | 3d10+4 | 2 |
| 35 | 파쇄 | EARTH | 20 | 4d8+6 | 3 |
| 36 | 소각 | FIRE | 25 | 5d8+8 | 3 |
| 37 | 혈액비등 | FIRE | 30 | 6d8+10 | 3 |
| 38 | 천둥 | WIND | 28 | 5d10+8 | 3 |
| 39 | 지진 | EARTH | 35 | 6d10+10 | 3 |
| 40 | 대홍수 | WATER | 35 | 6d10+10 | 3 |
| 47 | 경험흡수 | — | 20 | 3d8+5 | 1 |
| 56 | 드래곤슬레이브 | FIRE | 60 | 10d12+20 | 3 |
| 57 | 기가슬레이브 | — | 100 | 15d12+30 | 3 |
| 58 | 플라즈마 | FIRE | 50 | 8d10+15 | 3 |
| 59 | 메기도 | EARTH | 55 | 8d12+15 | 3 |
| 60 | 지옥불 | FIRE | 45 | 7d10+12 | 3 |
| 61 | 아쿠아레이 | WATER | 45 | 7d10+12 | 3 |

### 6-2. 유틸리티 주문 (36개)

| ID | 한글 | MP | 효과 |
|----|------|-----|------|
| 0 | 활력 | 3 | HP+15 |
| 2 | 빛 | 2 | PLIGHT |
| 3 | 해독 | 5 | PPOISN 해제 |
| 4 | 축복 | 5 | PBLESS (THAC0-3) |
| 5 | 보호 | 5 | AC 강화 |
| 7 | 투명 | 8 | PINVIS |
| 8 | 회복 | 15 | HP+50 |
| 9 | 투명감지 | 5 | PDINVI |
| 10 | 마법감지 | 3 | PDMAGC |
| 11 | 텔레포트 | 10 | 랜덤방 이동 |
| 15 | 마법부여 | 20 | 무기 adjustment+1 |
| 16 | 귀환 | 5 | 시작방 이동 |
| 17 | 소환 | 15 | 대상 소환 |
| 18 | 치료 | 10 | HP+30 |
| 19 | 대치료 | 30 | HP+100 |
| 20 | 추적 | 8 | 대상 방향 표시 |
| 21 | 공중부양 | 8 | PLEVIT |
| 22 | 화염저항 | 10 | PRFIRE |
| 23 | 비행 | 12 | PFLY |
| 24 | 마법저항 | 15 | PRMAGI |
| 41 | 성향감지 | 3 | PKNOWA |
| 42 | 저주해제 | 10 | OCURSE 해제 |
| 43 | 냉기저항 | 10 | PRCOLD |
| 44 | 수중호흡 | 8 | PWATER |
| 45 | 돌방패 | 12 | PSHIEL |
| 46 | 위치감지 | 5 | 대상 위치 표시 |
| 48 | 질병치료 | 8 | PDISEA 해제 |
| 49 | 실명치료 | 8 | PBLIND 해제 |
| 50 | 공포 | 12 | PFEARS 부여 |
| 51 | 방활력 | 15 | 방 전체 HP+20 |
| 52 | 전송 | 20 | 대상방 이동 |
| 53 | 실명 | 10 | PBLIND 부여 |
| 54 | 침묵 | 12 | PSILNC 부여 |
| 55 | 매혹 | 15 | PCHARM 부여 |
| 62 | 강화 | 25 | 장비 업그레이드 |

---

## 7. 전직 시스템 (command7.c train)

```
전직 경로:
  일반(1-8) lv200 → Invincible(9) lv1 리셋
    → Invincible lv200 → Caretaker(10) lv1 리셋
      → Caretaker lv200 → Care_II(11)
        → Care_II → Care_III(12)

전직 조건:
  - RTRAIN 방에서만
  - 60초 쿨다운 (LT_TRAIN)
  - 경험치: aim_exp(ply_ptr)
  - 골드: aim_exp(ply_ptr)/123 + level*23

Invincible 특성:
  - HP dice 3배, MP dice 3배
  - THAC0 범위: [-5, 10]
  - 레벨 경험치 5배

Caretaker 특성:
  - HP +2000, MP +900
  - THAC0 범위: [-10, 0]
  - 레벨 경험치 25배

Care_II/III:
  - 레벨 리셋 없음
  - 필요경험치 = hpmax*1500 + mpmax*1000
```

---

## 8. 이식 Phase 계획

```
Phase 0 (인프라) ──┬── Phase 1 (전투) ──── Phase 5 (성장)
                   ├── Phase 2 (마법) ──┤
                   ├── Phase 3 (경제)   ├── Phase 6 (기타)
                   ├── Phase 4 (커뮤니티)│
                   └── Phase 7 (DM)     └── Phase 8 (방/NPC)
```

### Phase 0: 핵심 인프라 (선행 필수)
- S_ISSET 스펠 비트필드 → player_data `"spells_known"` set
- Proficiency/Realm → player_data 저장 + 원본 테이블 구현
- Lasttime 쿨다운 → player_data `"cooldowns"` dict
- Creature Flags → player_data `"flags"` set
- Position → player_data `"position"` int

### Phase 1: 전투 시스템
- compute_thaco() 완전 구현
- attack_crt() 원본 공식 (다중공격, 크리티컬, 무기파손, backswing)
- NPC AI (MAGGRE, MFLEER, MMAGIC)
- Flee 원본 공식

### Phase 2: 마법 시스템
- cast() 원본 흐름
- offensive_spell() 원본 공식 (영역 보너스)
- 유틸리티 주문 37개 효과
- spell_fail() 클래스별
- teach/study 시스템

### Phase 3: 경제 시스템
- 은행 (bank.c)
- 상점 정비
- 경매 (kyk1.c)

### Phase 4: 커뮤니티
- 게시판 18개 (board.c)
- 가족/길드 (command4.c, kyk6.c)
- 결혼 (comm11.c, kyk3.c)

### Phase 5: 성장 시스템
- train() 전직
- 숙련도 자동 성장
- power/meditate/accurate

### Phase 6: 기타 시스템
- 제련, 포커, 킬러, 순위, 지도, 별명

### Phase 7: DM 명령어 (~60개)

### Phase 8: 방 특수효과 + NPC 특수행동

---

## 9. 파일 구조 (목표)

```
games/3eyes/
├── __init__.py
├── constants.py          ← 대폭 확장 (플래그, 스펠, 쿨다운, 테이블)
├── game.py               ← regen, update tick 확장
├── level.py              ← Invincible/Caretaker 전직 추가
├── login.py              (변경 없음)
├── combat/
│   ├── __init__.py
│   └── death.py          (변경 없음)
└── lua/
    ├── lib.lua           ← profic/mprofic/S_ISSET/comp_chance/flags 구현
    ├── combat/
    │   ├── thac0.lua     ← 재작성 (원본 공식)
    │   └── spells.lua    ← 재작성 (62개 완전 구현)
    └── commands/
        ├── admin.lua     ← 대폭 확장 (~60개 DM 명령어)
        ├── board.lua     ← 신규 (게시판 18개)
        ├── combat.lua    ← 수정 (flee, NPC AI)
        ├── comm.lua      (유지)
        ├── economy.lua   ← 신규 (은행, 경매)
        ├── family.lua    ← 신규 (가족/길드)
        ├── forge.lua     ← 신규 (제련)
        ├── info.lua      ← 수정 (score 확장)
        ├── items.lua     (유지)
        ├── magic.lua     ← 신규 (cast/study/teach)
        ├── map.lua       (유지)
        ├── misc.lua      ← 신규 (순위, 별명, 이벤트)
        ├── movement.lua  (유지)
        ├── poker.lua     ← 신규 (포커 게임)
        ├── ranking.lua   ← 신규 (순위 시스템)
        ├── shops.lua     ← 재작성 (원본 충실)
        ├── skills.lua    ← 전제조건 추가
        ├── stealth.lua   (유지)
        ├── social.lua    ← 신규 (결혼, 소셜)
        └── training.lua  ← 신규 (전직, 훈련)

core/
└── lua_commands.py       ← ctx 메서드 추가 (cooldown, flags, spells_known)
```
