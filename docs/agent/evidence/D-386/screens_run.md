# 화면 여덟 장 — 그리고 화면이 잡은 결함 (D-386)

**실행 2026-09-13** · 구동체 `scripts/capture_screens.py` (playwright chromium 1440×900) ·
판정 `scripts/verify_screens.py` · `scripts/verify_route_alive.py`

## 1. 몇 장인가 [실측]

**3장 → 8장** (0/16 → 3/16 → **8/16**). 인덱스는 실행체가 직접 쓴다 —
`docs/agent/evidence/D-347/screens/INDEX.yaml`.

| # | 경로 | 그 화면에만 있는 글자로 단언 |
|---|---|---|
| 1 | `/dsm/dashboard` | 관제 대시보드 |
| 2 | `/dsm/events` | 이벤트 목록 |
| 3 | `/dsm/events/{id}` | 이벤트 상세 |
| 4 | `/device` | Add New Device |
| 5 | `/roles` | Add New Role |
| 6 | `/menu` | Menu Management |
| 7 | `/configuration-management` | Is Active? |
| 8 | `/profile` | Personal Information |

브라우저 오류 **0건** · `verify_screens.py` 통과(run_log 와 ±5분 대조).

## 2. ★ 이번 턴의 수확 — 열어 봤더니 **빈 화면 1건**

`/users` (사용자 관리):

```
본문 글자 수      0        ← 아무것도 그리지 않았다
JS 오류           0건      ← 스크립트가 죽은 것이 아니다
그 화면의 API     6건 전부 200   ← 서버도 살아 있다
```

원인 [실측]: 이 계정의 `role` 이 **None** 이다. 읽기 권한 판정이 거짓이 되고
`rj-core` 의 `UserManagement` 가 **아무것도 그리지 않는다.**

DA-03 §3-4 는 「화면 전체가 권한없음이면 **빈 화면 대신 안내 한 장**을 낸다」로 정해 두었다.
지금 동작은 그 규약 위반이고, **당직자에게는 「화면이 고장 났다」로 보인다**(D-378).
`rj-core` 는 §0.4 이관 자산이라 우리가 고치지 않는다 — 대장에 올렸다:
`DA-05/blockers.yaml :: RJCORE_BLANK_ON_NO_PERMISSION`.

★ 찍지 않았다. 빈 화면은 단언이 서지 않으므로 **캡처하지 않고 결함으로 낸다** —
  그러나 목록에서 지우지도 않는다(`capture_screens.KNOWN_BLANK`).
  지우면 「안 해 본 것」과 「해 봤더니 안 되는 것」이 같아진다.

## 3. ★ 두 번째 수확 — **찍는 사람의 역할이 진술이었다**

1차판 `capture_screens.py` 에는 `role = "OPERATOR"` 가 박혀 있었고, 바로 위 주석은
「우리가 정해서 적지 않는다」고 말하고 있었다. **그 진술은 틀렸다** — 실측하니 `NO_ROLE` 이다.
이제 제품이 들고 있는 값을 읽어 적는다(`read_role`). 그리고 그 사실이 §2 를 설명한다.
인덱스가 `OPERATOR` 라 적고 있었으면 **빈 화면의 원인이 통째로 가려졌을 것이다** (D-323).

## 4. 라우트를 실제로 때렸다 — `verify_route_alive.py`

화면이 **브라우저에서 실제로 부른** API 를 그대로 적어 두고(`screen_routes.json` ·
8화면 51건), 그중 GET 을 **다시 HTTP 로 때린다.**

```
[ALIVE] [입력] 13건 — 화면이 실제로 부른 GET 라우트 (값이 든 경로 2건은 씨앗이 지워져 때리지 않는다)
[ALIVE] 통과 — 13건 전부 살아 있다 (실제 HTTP 로 때렸다)          [실측 2026-09-13]
```

★ 자기표본(D-310): **500 을 내던 그 라우트**(`/api/dsm/events`)가 목록에 없으면
  자기시험이 먼저 실패한다 — 눈이 감기는 것을 눈이 본다.

★ 판정기를 **두 번 고쳤고 두 번 다 판정기가 틀렸다** (D-350):
  ① 기록기가 URL 을 `/api/` 로 잘라 **구글 지도**(`maps.googleapis.com/maps/api/js`)를
     우리 라우트 `/api/js` 로 둔갑시켰다 → 「죽은 라우트 404」 2건이 전부 가짜였다
  ② 질의문자열을 지우고 때려 **살아 있는 라우트가 422** 로 나왔다(필수 인자가 사라졌다)
  둘 다 「죽은 라우트 4건」이라는 **틀린 보고**를 낼 뻔했다. 죽은 것은 측정이었다.

## 5. 서버가 없으면 — **통과가 아니라 판정 불가**

게이트 `route-alive` 는 서버 미기동·자격증명 부재에서 **SKIP(판정 불가)** 을 낸다.
때려 보지 못한 것을 초록으로 적지 않는다 (D-301).
