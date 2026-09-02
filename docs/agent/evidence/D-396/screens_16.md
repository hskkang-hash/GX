# 화면 **16/16** — 그리고 열었더니 결함 넷이 나왔다 (D-396 · D-397)

**실행 2026-09-14** · 구동체 `scripts/capture_screens.py` (playwright chromium 1440×900) ·
판정 `scripts/verify_screens.py` · `scripts/verify_route_alive.py`

---

## 1. 몇 장인가 [실측]

**8장 → 16장** (0/16 → 3/16 → 8/16 → **16/16**). 인덱스는 실행체가 직접 쓴다.

고르기 전에 **후보 16개를 실제로 열어 본문을 읽었다** — `must_see` 를 추측으로 적지
않는다(D-386). 정찰 결과: **찍을 수 있는 것 13 · 찍을 수 없는 것 3.**

| # | 경로 | 그 화면에만 있는 글자 |
|---|---|---|
| 9 | `/surveillance-dashboard` | Last Updated |
| 10 | `/survey-profile` | Add New Profile |
| 11 | `/media-data` | No preview available. |
| 12 | `/flight-log-analysis` | Drone State Prediction |
| 13 | `/multi-stream-monitor` | Participants |
| 14 | `/operation-settings` | API URL |
| 15 | `/report-template` | Usage Count |
| 16 | `/notam` | SNOWTAM |

브라우저 오류 **0건** · `verify_screens.py` 통과(16장 · run_log ±5분 대조).
§0.4(배송·주문·터미널) 화면은 고르지 않았다.

---

## 2. ★ D-386 이 옳았다 — **「16장이면 더 나온다」에 넷이 나왔다**

### ① `/api/media-data/` 가 **500** 이다 — 그리고 화면은 「자료 없음」으로 보인다

```
GET /api/media-data/?page_size=25&current_page=1  ->  500
화면: 「0 of 0」 · 오류 문구 0자
```

**단위 시험 542건이 전부 초록인 채로** 그 자리가 죽어 있었다. `/api/dsm/events` 때와
같은 갈래다(D-386) — 그때는 3장에서 하나, 이번에는 16장에서 하나.

★ 응답을 그대로 받아 보니 **세 가지가 동시에 잘못돼 있었다** [실측]:

```json
{"success": true, "status": 500, "message": "Failed to retrieve operational notice list", "data": []}
   └ ①봉투가 성공이라 말한다      └ ②남의 앱 이름을 말한다
```

  ① `BaseResponse(success=True, …)` 가 dj-core 의 **기본값**이다. 우리 뷰가
     `success=False` 를 안 넘겨 **조용히 참**이 됐다
  ② `MESSAGE_ENUM.GET_LIST_FAILED` 하나를 여러 앱이 나눠 쓰는데 그 영문이 **한 앱의
     것**이었다. 틀린 문구는 고치는 사람을 **엉뚱한 앱으로 보낸다**
  ③ 그리고 화면은 그 500 을 받고도 목록을 비워 그렸다 — **당직자에게는
     「영상 자료가 없다」로 보인다**(D-378)

**고친 것 [실측]:** ①②를 고쳤다. 응답은 이제 이렇게 말한다:

```json
{"success": false, "status": 500, "message": "Failed to retrieve media list", "data": []}
```

**고치지 않은 것과 그 사유:**
  · 500 자체는 이 환경에 MinIO 가 없어서다(`minio.invalid`) — **환경이다**
  · ③은 화면 쪽이고 그 화면은 **인수 자산**이다. 즉 **서버는 이제 진실을 말하는데
    화면이 안 듣는다.** 잠금에 올렸다: `MEDIA_LIST_SHOWS_EMPTY_WHEN_STORAGE_DOWN`
  · 게이트 `route-alive` 는 이 자리에서 **빨간 채로 둔다**(D-327). 초록으로 만드는
    예외를 넣지 않는다 — 넣는 순간 그 게이트가 하는 일이 없어진다

### ② **두 번째 빈 화면** — `/handover`

```
본문 0자 · API 실패 0건 · JS 오류 0건
```

`/users` 와 **같은 모양**이다. 한 건이면 그 화면의 사정이지만 **둘이면 성질**이다 —
`RJCORE_BLANK_ON_NO_PERMISSION` 에 표본을 더했다.

### ③ **도달 불가 2건** — `/monitoring-dashboard` · `/intergrated-dashboard`

요청한 경로가 아니라 이 계정의 홈(`/profile`)이 떴다. **빈 화면과 다른 결함이다:**
빈 화면은 「왔는데 아무것도 없다」이고, 이것은 **「거기 갈 수 없다」**이다.
둘을 한 칸에 두면 고치는 사람이 어디를 볼지 모른다 — ㉠㉡㉢ 을 가른 것과 같은 이유다(D-377).

⚠ 이 계정의 `role` 은 `NO_ROLE` 이다. 역할이 있는 계정에서는 다를 수 있고 **아직 재 보지
않았다.** 「권한 때문」이라고 적지 않는다 (D-322 — 근거 없는 주장은 부재 주장도 주장이다).

---

## 3. ★★ 그리고 **판정기가 눈 감김을 스스로 잡았다** (D-397)

첫 캡처는 16장 전부 성공했고 `verify_screens` 도 통과했다. **그런데
`screen_routes.json` 은 16화면 전부 「API 호출 0건」이었다.**

```
[ALIVE] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):
    자기표본 /api/dsm/events 이 목록에 없다 — 500 을 내던 그 자리다 (D-310)
```

원인 [실측]: `--api http://127.0.0.1:8000` 을 줬는데 **번들은 `http://localhost:8000`
을 부른다.** 접두 대조가 한 건도 안 맞았다.

★ 이 조합이 가장 나쁘다: **화면은 다 떴고 데이터도 다 그려졌는데 기록만 비었다.**
  그 빈 기록은 `verify_route_alive` 를 **「때릴 것이 없어 통과」**로 만든다 —
  **0건은 통과가 아니다**(D-301). 죽은 라우트가 있어도 초록이 났을 것이다.

★ 잡은 것은 **D-310 이 박아 둔 출생 표본**이다. `verify_route_alive` 는 자기를 만들게 한
  그 500 라우트가 목록에 없으면 **판정을 시작하지 않는다.** 그 규약이 두 턴 만에 값을 했다.

**고침:** `capture_screens.py` 가 이제 **어느 화면에서든 우리 API 기록이 0건이면 실패**
하고, `/api/` 를 실제로 부른 주소를 **그대로 보여 준다** — 무엇과 안 맞았는지가 화면에
있어야 다음 사람이 5분 만에 고친다.

바로잡은 뒤 [실측]: **16화면 · API 호출 109건** 기록. 그중 실패 1건이 위 §2 ①이다.

---

## 4. 라우트를 실제로 때렸다 [실측]

```
[ALIVE] 자기시험 통과 — 판정 규칙 8종 + 출생 표본 /api/dsm/events 500 + 자기표본
[ALIVE] [입력] 26건 — 화면이 실제로 부른 GET 라우트
[ALIVE] 24건 산다 · **죽은 라우트 2건** (같은 자리의 두 형태 — 경로 끝 빗금 있고 없고)
[ALIVE] exit 1
```

직전 턴 13건 → 이번 **26건**. 화면이 8장 늘자 때릴 자리가 두 배가 됐다.

---

## 5. 검증 [실측 2026-09-14]

```
화면            16/16 · 브라우저 오류 0건 · verify_screens exit 0
route-alive     **exit 1** — 죽은 라우트 2건. 빨간 채로 보고한다 (D-327)
발견            결함 4건 (500 라우트 1 · 빈 화면 1 · 도달 불가 2)
고친 것         2자리 (오류 봉투의 success · 오류 문구) — 화면 쪽은 안 고쳤다
§0.4 수정       0줄
```
