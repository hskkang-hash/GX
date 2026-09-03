# P-3 봉투 — promoted 11 을 세었다 (A2 선행 · 조율자)

- 잰 날: 2026-09-20 · 잰 사람: Code · 도구: `scripts/verify_envelope.py --list` + 실제 HTTP 왕복
- 지시: 「먼저 promoted 11 을 세어 이름·화면 붙인다(지금, 조율자)」 (세종 09-20 §3 A2)

## ① 이름 11 · 화면

`[ENVELOPE] 봉투: clean 356 · authz_envelope 296 · promoted 11` — promoted 는 **전부 `/api/dsm/`** 이다.

| # | method · 경로 | 화면 | 화면이 HTTP 상태를 읽는가 |
|---|---|---|---|
| 1 | GET `/api/dsm/dashboard/frame` | 관제 대시보드 | ✔ `features/dsm/api.ts::unwrap` |
| 2 | GET `/api/dsm/dashboard/link-state` | 관제 대시보드 | ✔ 같은 함수 |
| 3 | GET `/api/dsm/events` | 이벤트 목록 · 관제 대시보드 | ✔ |
| 4 | GET `/api/dsm/deliveries` | 관제 대시보드 | ✔ |
| 5 | POST `/api/dsm/events/{id}/notify` | 이벤트 상세 | ✔ |
| 6 | GET `/api/dsm/events/{id}/clip` | **없음** — C 차선(W2 상세)에서 붙는다 | — |
| 7 | GET `/api/dsm/events/{id}/clip/stream` | **없음** (11조 잠김) | — |
| 8 | GET `/api/dsm/reports/templates` | **없음** — 검수 콘솔 자리 | — |
| 9 | GET `/api/dsm/reports/{id}.pdf` | **없음** | — |
| 10 | POST `/api/dsm/settings/thresholds` | **없음** — F-12 관리자 화면 미착수 | — |
| 11 | GET `/api/dsm/settings/{domain}` | **없음** | — |

**화면이 부르는 5 · 아직 화면 없는 6.** 부르는 5는 전부 `unwrap()` 하나를 지나고,
그 함수는 **HTTP 상태와 본문 `status_code` 를 둘 다** 읽는다(D-358). 즉 이 5자리는
승격이 켜져도 깨지지 않는다 — 아니, **이미 켜져 있다.** ②를 보라.

## ② ★ 정정 — promoted 11 은 **이미 승격 중**이다. 스위치가 바꾸는 것은 그 11이 아니다

세종 판정문은 「켜면 promoted 11 이 실제 4xx/5xx 가 되어 HTTP 상태 안 보던 화면이 깨진다」였다.
실측은 다르다.

    backend/config/settings.py:173
    API_CONTRACT_PROMOTE_PATHS = ("/api/dsm/", ...)   ← 기본값. 전역 플래그와 **무관**하게 승격
    API_CONTRACT_PROMOTE_ERROR_STATUS = false          ← 꺼져 있는 것은 **전역** 플래그

`promotion_enabled_for(path)` 는 둘 중 하나만 참이면 승격한다(D-349 ③ — 계약 면은 래칫에 두지 않는다).

**실측 [2026-09-20 · 제품 토큰]:**

    GET  /api/dsm/events/999999        HTTP **404**   (본문 봉투 없음)
    GET  /api/dsm/settings/nope        HTTP **501**
    GET  /api/config-management/list   HTTP **200** · success=false · status_code=**403**
    GET  /api/dashboard/dashboard      HTTP **200** · success=false · status_code=**403**

DSM 면은 이미 진짜 상태를 낸다. **200 봉투에 4xx 를 담아 내보내는 것은 나머지 652자리**다
(clean 356 + authz_envelope 296).

## ③ 그래서 전역 스위치의 폭발 반경은 11이 아니라 **652** — 그리고 그중 상당수가 §0.4 다

전역 플래그를 켜면 `/api/config-management/*` · `/api/dashboard/*` · `/api/delivery/*` ·
`/api/orders/*` · `/api/terminals/*` 가 일제히 진짜 4xx 를 내기 시작한다. 그 화면들은
`frontend/src/features/{Delivery,Orders,Terminal}` — **우리가 고칠 수 없는 자리다**(§0.4 · D-207).

지시서는 「깨진 화면은 HTTP 상태를 읽게 고친다 — 미들웨어를 끄지 않는다」고 했다.
그 지시와 §0.4 가 여기서 **정면으로 부딪친다.** 고칠 수 없는 화면을 깨는 스위치는
「고쳐야 할 빚」이 아니라 「남의 집 문을 여는 일」이다.

**Code 권고 — 전역 플래그 대신 `API_CONTRACT_PROMOTE_PATHS` 를 한 접두씩 넓힌다.**
한 접두를 넣을 때마다 (ⓐ) 그 경로를 부르는 화면을 세고 (ⓑ) 그 화면이 상태를 읽는지 보고
(ⓒ) 화면 재촬영으로 확인한다. 우리 화면이 다 옮겨진 뒤에야 전역 플래그가 **아무것도 바꾸지
않는 상태**가 되고, 그때 켜는 것이 옳다. 켜서 깨뜨리고 고치는 순서가 아니라,
고치고 나서 켜는 순서다.

판정은 세종의 자리다 — 이 문서는 수와 실측만 낸다.
