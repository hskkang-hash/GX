# P-141 · 여정 빨강 7 — 이름과 3종 분류 (턴 Q · 차선 Q · 2026-09-15)

**잰 것** `docs/agent/evidence/P-118/click_completes.json` (measured_at `2026-09-15T06:54:33Z` · 사건 4808) ·
판정문 `docs/agent/evidence/P-118/judgement_20260915_0654Z.txt:15-65` · 걷기 `docs/agent/evidence/P-64/walk_20260915_154917.json`
**분류 정본** P-132 3종 — 제품 결함 · 게이트 기대식 오류 · 정본 없음/데이터 없음 (`docs/agent/archive/RESUME_NEXT_턴P_20260911.md:68`) ·
제품 결함만 빨강 · 기대식 오류는 고쳐 재측 · 정본 없음은 회색 유지 (`작업지시서/…_20260915.md:179`)
**이 문서는 판정기를 돌리지 않았다** — 증거 파일과 코드를 읽어 대조했다(정적). 새 관측 0.

## 한 줄

    빨강 7 = 제품 결함 1 · 기대식 오류 3 · 데이터 없음 3
    이름 없던 2 = U1#19 교대 인계 메모 · U2#1 밤사이 요약 보기 (둘 다 데이터 없음)

**「셋은 뿌리 하나」(RESUME_NEXT P-141 표 — 첫 화면 · 사진 · 발송 수)는 이 증거로 서지 않는다.**
첫 화면은 제품 결함이고, 사진과 발송 수는 **서버도 화면도 움직였는데 판정기가 못 본** 자리다.
어댑터(P-129)를 고쳐도 이 둘은 빨강 그대로다 — 고칠 곳은 판정기의 재조회 식이다.

## 표

| 행 ID | 화면 | 관측 [실측] | 분류 | 근거 파일:줄 |
|---|---|---|---|---|
| **U1#1** 교대 시작 — 로그인 | `/login` → `/profile` | 로그인 요청은 나갔고 주소가 `/login` → `/profile` 로 바뀌었다. 화면 글은 「Personal Information · Add Profile Picture · Email * …」 — 기대 말(관제·대시보드·이벤트·GuardianX) 0 | **제품 결함** — 역할 홈(UX-32) 미구현. 첫인상이 인수 제품이다 | `click_completes.json:7`·`:131-134`(state)·`:135`(text) · `judgement_…0654Z.txt:18` · `verify_click_completes.py:140-142` · `PRD_v1.1_상용정본:179` |
| **U1#19** 교대 인계 메모 ★이름 없던 1 | `/handover` | `GET /api/handover/handover/notice` 나감. 재조회 `GET /api/dsm/events/summary?hours=24` 의 `unhandled` = **0 → 0**. 화면은 「[교대 인계 초안] … 미처리: 0건 · 오늘 판정: 0건」 — **서버의 0 을 화면이 그대로 적었다** | **데이터 없음** — 24시간 창 안에 사건이 0건이다. 미처리 둘은 11일 전 사건이다(같은 관측 U1#8 목록 「12:14 · 11일 전」). 판정기 술어가 `0` 을 「아무것도 안 냈다」로 읽는다 | `click_completes.json:819`·`:937-944`(state)·`:945`(text)·`:604`(11일 전) · `judgement_…0654Z.txt:25` · `verify_click_completes.py:183-186`(기대식)·`:449-450`(0 = 빈 값) |
| **U2#1** 밤사이 요약 보기 ★이름 없던 2 | `/dsm/events` (U2 · 관제 현황·훈련 모드 곁줄) | `GET /api/dsm/events/summary?hours=12` 나감. 재조회 `unhandled` = **0 → 0**. 화면 「요약 한 줄 · 지난 12시간 · 미처리 0건 · 오탐 0건 / 판정 0건 · 아직 판정한 이벤트가 없습니다」 | **데이터 없음** — 12시간 창 안에 사건 0건. 화면은 옳게 0 과 「아직 판정한 이벤트가 없습니다」를 적었다 | `click_completes.json:948`·`:1096-1103`(state)·`:1104`(text) · `judgement_…0654Z.txt:26` · `verify_click_completes.py:189-192`·`:449-450` |
| **U3#1** 알림 수신 (턴 P 「알림 발송 수 불변」) | `/dsm/events/4808` 「알림 보내기」 | `POST /api/dsm/events/4808/notify` 나감. 재조회 `GET /api/dsm/deliveries?limit=1` 의 `total` = **1 → 1**. 그런데 같은 화면의 발송 이력에 **06:53:16~17 새 행이 여럿** 떴다 — 「log · (수신자 없음) · 로그에 기록됨(사람에게 안 감)」 | **기대식 오류** — `deliveries` 의 `total` 은 **`len(rows)`** 이고 `limit=1` 이면 언제나 ≤ 1 이다. 행이 늘어도 이 칸은 못 늘어난다. 서버 상태는 바뀌었다 | `click_completes.json:1809`·`:1828`(state)·`:1834`(text) · `judgement_…0654Z.txt:34` · `backend/apps/dsm/api.py:687-690`(limit)·`:700`(`"total": len(rows)`) · `verify_click_completes.py:234-236` |
| **U3#3** 상황 사진 1장 보기 (턴 P 「모바일 사진」) | `/m/events/4808` · 390px | `GET /api/dsm/events/4808/snapshot` 나감. 재조회 `snapshot_path` 값 있음. 판정은 「화면에 없다」. 화면 글: 「스냅샷 · **이 사진에는 기관명과 열람 시각이 찍혀 있습니다.** · 참조 보기」 | **기대식 오류** — 그 캡션은 `EventSnapshot` 이 **사진을 받은 갈래에서만** 그린다(로딩은 Skeleton · 오류는 Alert 로 먼저 돌아간다). 곧 사진이 그려졌다. 판정기는 **객체 키 글자**를 화면에서 찾는데, 키는 설계대로 「참조 보기」 아래에 접혀 있다(P-121). 정본은 「390px에 img 1」이다 | `click_completes.json:1996`·`:2145`(state)·`:2152`(text) · `judgement_…0654Z.txt:36` · `frontend/src/features/dsm/components/EventSnapshot.tsx:101-103`·`:104-152`·`:153-174`(캡션 `:171`) · `frontend/src/features/mobile/pages/MobileEventDetail.tsx:404-406`·`:410-415`·`:417-432` · `verify_click_completes.py:240-242` · `PRD_v1.1_부속서A:80` · 대조 `evidence/P-121/shots/after_mobile_detail.png` |
| **U6#1** API 키로 인증 (턴 P 「U6 403」) | (화면 없음 · HTTP) | `POST /api/dsm/settings/api-keys?name=p118-gate` → **403** 「설정 변경 권한이 없는 계정 (감사 #211637)」. 행위자 `gxseed_u5_sysop`(admin) | **데이터 없음(역할 미부여)** — 제품은 옳게 거절했다. 발급은 전역 관리 역할 또는 `tenant_admin_<group_id>` 역할만 받는다. 그 역할을 든 시드 계정이 없다 — 부여는 데이터다(SEC-22 · U56). 곁 사실: 거절이 **감사 id 를 남겼다** | `click_completes.json:3016`·`:3030`(state)·`:3037`(text) · `judgement_…0654Z.txt:58` · `verify_click_completes.py:371-374`·`:1283`·`:1326` · `backend/apps/dsm/services.py:675-679`·`:763` · `backend/common/tenant_roles.py:98-111` · `backend/apps/dsm/api.py:988-989` |
| **U6#4** 이벤트 발생 웹훅 수신 (턴 P 「웹훅 서명키 비어 있음」) | (화면 없음 · HTTP) | `POST /api/dsm/webhook-subscriptions?endpoint_url=https://localhost:9/p118&signing_key_ref=p118-gate&event_types=fire` → **422** 「우리 서버 자신을 가리키는 주소는 등록할 수 없습니다.」. 재조회 `total` = 0 → 0 | **기대식 오류** — 판정기가 보낸 수신 주소가 `localhost` 라 제품의 문지기(SSRF)가 옳게 거절했다. **서명키 검사는 주소 검사 뒤라 이번 관측은 서명키에 닿지 못했다** — 「서명키 비어 있음」은 이 관측으로는 근거가 없다(못 잰 것) | `click_completes.json:3088`·`:3102`(state)·`:3109`(text) · `judgement_…0654Z.txt:61` · `verify_click_completes.py:381-383`·`:1292-1293` · `backend/common/webhook_outbox.py:173-175`(localhost 거절)·`:211-212`(주소 먼저)·`:217-220`(서명키 뒤) · `backend/apps/dsm/api.py:644-645`(422) |

## 셈

| 분류 | 수 | 행 |
|---|---|---|
| 제품 결함 | **1** | U1#1 |
| 기대식 오류 | **3** | U3#1 · U3#3 · U6#4 |
| 정본 없음/데이터 없음 | **3** | U1#19 · U2#1 · U6#1 |

## 턴 P 보고의 이름과 갈린 자리 셋

1. **「알림 발송 수 불변」(U3#1)** — 발송 수는 **변했다.** 화면에 새 행이 떴다. 안 변한 것은 `limit=1` 로 자른 목록의 길이다.
   RESUME_NEXT P-141 표의 가설 둘(P-129 어댑터 · K2 `NoRecipients`) 다 이 관측과 맞지 않는다:
   `NoRecipients` 였다면 라우트가 **409** 를 낸다(`api.py:594-595`). 실제는 행이 생겼고 채널이 `log` · 수신자 없음이다 —
   **「사람에게 가는 규칙이 없다」(규칙 0건 · `onboarding_48.md:147`)는 이 행의 곁 사실로 남는다**(UX-43).
2. **「모바일 사진 안 보임」(U3#3)** — 사진은 그려졌다(캡션이 성공 갈래에서만 뜬다). 이 관측은 글자뿐이고 픽셀 캡처가 없다 —
   390px 픽셀 한 장으로 확인하는 것이 남는다(아래 요청 ②).
3. **「웹훅 서명키 비어 있음」(U6#4)** — 관측된 거절은 **주소**다. 서명키 이름 `p118-gate` 가 이 환경의
   `WEBHOOK_SIGNING_KEYS` 에 있는지는 이번에 재지 않았다 — 주소를 고쳐 다시 재면 그것이 다음 벽일 수 있다
   (`UnknownSigningKey` 422 · `webhook_outbox.py:217-220`).

## 걷기 기록에서는

`walk_20260915_154917.json` 은 **빨강 0**이다 — S1·S2·S3 셋 다 `completed: true`(`:44`·`:69`·`:94`).
빨강 7 은 전부 `click_completes` 의 것이다. 걷기에 남은 실패는 `422 GET /api/user-groups/gen-schema?raw=false`
세 번(`:156-165`)뿐이고 그것은 인수 층 머리 요청이다 — 빨강 7 어느 행과도 뿌리가 겹치지 않는다.

## 조율자에게 (게이트를 돌려 확인할 것)

1. **기대식 오류 3 은 판정기를 고쳐 재측한다** — 게이트 소유 차선이 고친다(Q 는 scripts/ 를 안 만진다):
   U3#1 재조회를 `deliveries?event_id={event}` 의 `total` 로(`verify_click_completes.py:236`) ·
   U3#3 상태 칸을 「img 1 + 캡션」으로(`:240-242`) · U6#4 수신 주소를 사설·루프백이 아닌 주소로(`:1292`).
   **고친 뒤 빨강이면 그때 제품 결함이다.** 게이트를 느슨하게 해 초록을 만드는 것이 아니라, 재조회가 서버가 실제로 바꾼 칸을 읽게 하는 것이다.
2. U3#3 — 역할 계정 390px 로 `/m/events/{id}` 픽셀 1장(사진이 실제로 보이는가).
3. 데이터 없음 3 — U1#19·U2#1 은 **측정마다 창 안에 사건 1건을 실제 생성 경로로 만든 뒤** 재측(P-132 「게이트용 사건은 매 회 새로」).
   U6#1 은 U56 차선의 `tenant_admin_<gid>` 부여 뒤 재측 — 초록은 **부여 후 발급 200 + 재조회 +1** 이어야 한다.
