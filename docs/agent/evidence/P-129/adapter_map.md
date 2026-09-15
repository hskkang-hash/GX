# P-129 — 「서버는 주는데 화면이 안 그린다」 여섯(+발송 수)의 뿌리 대조표

- 적은 사람: 차선 F(기반) · 턴 Q · 2026-09-15
- **SOURCE** = 저장소 원문(경로:줄) · 정적 대조. **AS** = 로그인 안 함(HTTP 도구 금지 차선).
- 가설 [추정 · 세종 · `archive/RESUME_NEXT_턴P_20260911.md:58`]: 봉투 승격(D-349)이 응답 모양을
  바꿨고 프런트가 승격 전 모양을 읽는다 → 고침은 어댑터 한 곳.

## 0. 먼저 잰 두 사실 — 가설이 서는 바닥

| # | 사실 | 근거 |
|---|---|---|
| A | 승격은 **상태줄만** 바꾼다. 본문은 그대로다 | `backend/common/api_contract.py:260-263` 「본문·헤더는 그대로 두고 상태줄만 고친다」 |
| B | 승격 조건은 `success is False` **이고** `status_code` 400~599 정수 | `api_contract.py:108-124` |
| C | `/api/dsm/**` 라우트는 **맨몸 dict** 를 내고 거절은 ninja `HttpError`(진짜 4xx)다 — `200 + success:false` 를 안 만든다 | `backend/apps/dsm/api.py:12` · `exceptions.py:4` · `law_api.py:17` · [grep] `apps/dsm/*.py` 에 응답 `"success"`/`"data":` 칸 0 |
| D | 이 앱의 axios 는 **본문**을 돌려준다(rj-core 인터셉터 `return i.data`). 4xx·5xx 는 거절 갈래 | `frontend/src/features/dsm/api.ts` P-121 머리말(종전 237-257) |
| E | DSM 화면은 거의 전부 `dsmGet`/`dsmPost*` 를 거친다. 종전 `unwrap()` 은 `res?.data ?? res` 로 **두 모양을 다 받았다** | `features/dsm/api.ts` 종전 123-152 |

→ A·B·C 때문에 **승격은 `/api/dsm/**` 응답의 모양을 한 번도 바꾸지 않았다.** 가설의 전제(승격이 모양을 바꿨다)가 이 여섯 자리에서는 성립하지 않는다.

## 1. 대조표

| # | 자리 | 서버 경로 | 승격 접두 | 서버 응답 모양 (파일:줄) | 화면이 읽는 자리 (파일:줄) | 화면이 기대하는 모양 | 어긋남 |
|---|---|---|---|---|---|---|---|
| 1 | 사진 | `GET /api/dsm/events/{id}/snapshot` | 안 (`/api/dsm/`) — 단 JSON 아님 | 바이트 `image/jpeg` · 오류 404/503/500 (`apps/dsm/api.py:723-747`) | `features/dsm/api.ts` `fetchSnapshotUrl` → `pickBlob(res)` · 부품 `dsm/components/EventSnapshot.tsx:64` · 쓰는 곳 `EventDetail.tsx:378` · `mobile/pages/MobileEventDetail.tsx:358` · `FocusQueue.tsx:360` | Blob 또는 `{data: Blob}` | **있었다 → 이미 닫힘(P-121)** — `res.data` 를 Blob 에 읽어 `createObjectURL(undefined)`. 지금은 두 모양 다 받는다 |
| 2 | 판정 | `POST /api/dsm/events/{id}/review?verdict=&reason=` | 안 | 맨몸 `{event_id, status, verdict, reviewed_by_id, reviewed_at, reject_reason, …}` · 거절 404/403/422 (`api.py:524-563`) | `EventDetail.tsx:190-196` `dsmPostQueryOnce` → 응답 버림 → `event.reload()` → `VerdictBadge verdict={e.verdict}` (`:320` · `:488`) | 상세의 `verdict` | **없음** — 상세 라우트가 `verdict` 를 낸다(`api.py:403`) |
| 3 | 상황판 `preset` | `GET /api/dsm/dashboard/frame` | 안 | 맨몸 `{preset, preset_matched, five_states, state_counts, panel_total, panels, link}` (`api.py:151-170`) | `ControlDashboard.tsx:69-73` `dsmGet` · `frame.data.preset` (`:158-159`) · `frame.data?.preset_matched` (`:142` · `:164-165`) | 같은 이름 | **없음** |
| 4 | 실시간 `counts` | `GET /api/dsm/cameras/pulse` | 안 | 맨몸 `{now, rules, counts:{alive,total,never_seen}, cameras, cluster}` (`api.py:1254-1274` → `services.py:1176-1209`) | `hooks/useCameraGrid.ts:90-91` `dsmGet` · `pulse.data?.counts` (`:128`) · `CameraGrid.tsx:87,124-136` · 월 `Wall.tsx:219-227` → `useCameraPulse.ts:44,105-128`(`cameras` 행 수로 셈) | 같은 이름 | **없음** |
| 5 | 역할 부여 `preset` | **못 찾음** | — | `preset` 을 내는 라우트는 #3 하나(`kernels/k3_dashboard/services.py:109-123` · 매핑 `config/k3_roles.py`) | 역할·사람·그룹 화면에서 `preset` 을 읽는 자리 **0** (`frontend/src` grep). 역할 관리 화면은 rj-core(저장소 밖 · `settings.py:375-378`) | — | **판정 불가** — 읽는 화면이 없다. [추정] 「역할을 줬는데 상황판이 `preset_matched=false`」라면 K3 매핑·시드의 문제이지 모양이 아니다 |
| 6 | 웹훅 `total` | `GET /api/dsm/webhook-subscriptions` | 안 | 맨몸 `{total, subscriptions}` (`api.py:648-659`) | **없음** — `frontend/` 에서 `webhook` 은 `package-lock.json` 뿐 | — | **판정 불가** — 그리는 화면이 없다(없는 화면은 「안 그린다」가 아니라 「없다」) |
| 7 | 발송 수 | `POST /api/dsm/events/{id}/notify` → `GET /api/dsm/deliveries?event_id=` | 안 | notify 맨몸 `{total, deliveries:[…]}` · 404/409(`NoRecipients`)/400 (`api.py:566-603`) · deliveries 맨몸 `{total, deliveries}` (`api.py:685-705`) | `EventDetail.tsx:122` `dsmPostOnce` → **응답 버림** → `:125` 「발송을 요청했습니다」 고정 → `:126` `deliveries.reload()` → 표 `deliveries.data?.deliveries ?? []` (`:546`) · 모바일 `MobileInbox.tsx:119` `deliveries.data?.total` | 같은 이름 | **모양 어긋남 없음** — 아래 §2 |

## 2. 턴 Q 판정 P-141 — 셋 중 몇이 같은 뿌리였나

| P-141 빨강 | 이 뿌리(P-129 응답 모양)인가 | 근거 · 남는 원인 |
|---|---|---|
| 로그인 뒤 첫 화면 `Personal Information` | **아니다** | 규칙 결함(역할 홈 부재) — `LoginDesktop.tsx` 종전 124-130 · `App.tsx` 종전 465-481. P-141 역할 홈으로 닫는다(`evidence/P-141/role_home.md`) |
| 모바일 사건 사진 안 보임 | **아니다(지금은)** | 모양 결함은 P-121 에서 닫혔다(#1). 남는 길: `MobileEventDetail.tsx:355` 가 `e.snapshot_path` 가 **있을 때만** 부품을 그린다 — 경로 없는 사건은 그림이 없다(자료). 경로가 있는데 안 보이면 404/503(저장소)이다. [미측정 — 390px 캡처는 조율자 한 줄] |
| 알림을 보내도 발송 수 그대로 | **아니다** | 화면이 notify 응답의 `total` 을 **버린다**(`EventDetail.tsx:122`). 서버가 억제로 `{total:0}` 을 200 으로 내도(`kernels/k2_notify/services.py:531-534` 억제 시 `()` 반환) 화면은 「발송을 요청했습니다」만 말한다 — **조용한 0** 이다. 수신자 0 은 409 로 따로 뜬다(`api.py:594-595`). 멱등 창(화면 2초 · 서버 10분)의 재답도 수가 안 는 길이다 |

**셋 중 같은 뿌리 = 0.** 가설(승격이 모양을 바꿨다)은 `/api/dsm/**` 에서 기각 — 근거 §0 A·B·C.
여섯 중 모양 결함이 실제로 있었던 곳은 **#1 하나**이고 이미 닫혔다. #5·#6 은 **화면이 없다**.

## 3. 그래도 어댑터를 한 곳에 세운 이유와 고친 것

`features/dsm/adapter.ts::unwrap(body, httpStatus?)` — WO-01 §5 「어댑터」. 모양 셋(`envelope`·`bare`·`error`)을 한 곳에서 가른다.
`features/dsm/api.ts` 의 내부 `unwrap` 과 거절 갈래가 이제 이것만 부른다(공통 호출부 한 곳 → DSM 화면 전부).
그 과정에서 종전 해석의 **잠복 결함 셋**을 닫았다(모두 지금 증상은 없음 · 다음 라우트에서 터질 자리):

1. `res?.status` 를 HTTP 상태로 읽었다 — 인터셉터가 본문을 주므로 그것은 **본문의 `status` 칸**이다. 숫자 `status` 를 싣는 본문(dj-core 로그인 면 `{"status": 400}` 모양)이 오면 거짓 실패.
2. `body?.data ?? body` — 맨몸 본문의 도메인 `data` 칸을 봉투로 오인해 안쪽만 돌려줬다.
3. 거절 갈래가 `.message` 만 읽어 ninja `HttpError` 의 `{detail}` 사유가 화면에 안 닿았다(axios 영문 문장이 대신 떴다).

그리고 봉투 `success:false` 는 200 이어도 실패로 판정한다(DA-03 §0-1 — 상태와 `success` 둘 다).

## 4. 다른 차선 파일 — 고치지 않았다, 요청으로 올린다

- `features/dsm/pages/EventDetail.tsx:122-126` → notify 응답을 `unwrap()` 결과로 받아 `total === 0` 이면 「보낼 사람이 없거나 억제되어 발송되지 않았습니다」류 문장을 말할 것(조용한 0 제거) — U24/U56 소유. 문구는 GX-COPY 에 먼저.
- `features/dsm/wallToken.ts:255` `wallGet` 이 종전 `unwrap` 과 같은 `?.data ?? ` 관용을 따로 들고 있다 → `adapter.unwrap()` 적용 요청(소유 차선 확인 필요).
