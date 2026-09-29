# 턴 AP · 차선 L — 온보딩(누를 자리 선언) · 2026-09-29

시험 DB: `test_gx_lane_l`. 라이브 측정 0(V 몫) — 아래 표는 전부 코드·문서 손이고,
색이 실제로 바뀌었다는 확인은 다음 V 회차가 한다.

---

## 1. P-423 「누를 자리」 선언 표 (Q 가 이 표를 보고 술어를 맞춘다)

대상 9행 — `docs/agent/evidence/P-118/click_completes.json` 의 `control.found=false`
행 중 지시받은 정확히 9행: U1#4 · U3#14 · U3#16 · U4#9 · U5#1 · U5#4 · U5#5 · U5#10 ·
U6#14. (U2#3 은 같은 색이지만 사유 문장이 다르고("「되돌리기(사유 필수)」를 화면에서
못 찾았다" — "이 도구가 누를 자리를 선언하지 않았다" 문장이 아니다) 지시서가 준
목록에 없어 이 차선은 손대지 않았다 — Q 가 다룰 몫으로 남긴다.)

### 1-A. 선언한 자리 — `data-gx` 새로 닮

| 행 | 화면(정본 경로) | 어느 단추 | 새 선언 | 파일·자리 |
|---|---|---|---|---|
| U5#1 | `/dsm/people` | 「계정 만들기」 제출(POST `/api/dsm/settings/people/create` 를 한 번에 끝내는 자리 — `/users` 의 「사용자 추가」 링크와 다르다, 그건 서식 화면으로 가는 링크일 뿐) | `data-gx="people-create-submit"`(단추) · `data-gx="people-create-outcome"`(성공 칸) | `frontend/src/features/dsm/pages/People.tsx` |
| U5#4 | `/dsm/cameras/import` | 「② 표 먼저 보기 (dry-run)」 · 「③ 이 표대로 적용」 | `data-gx="camera-import-dryrun"` / `data-gx="camera-import-apply"` | `frontend/src/features/dsm/pages/CameraImport.tsx` |
| U5#5 | `/dsm/cameras/address` | 행별 「이 한 대 채우기」(연다) → 「채우기」(POST `/api/dsm/cameras/{id}/address` 를 실제로 쏘는 자리, `api_u56.py:506`) | `data-gx="camera-address-row-start"` / `data-gx="camera-address-row-submit"` (아래 「아직 없는 카메라」 카드의 같은 글자 단추 둘도 `camera-address-new-dryrun` / `camera-address-new-apply` 로 갈라 text 대조 충돌을 없앴다) | `frontend/src/features/dsm/pages/CameraAddress.tsx` |
| U3#16 | `/m/settings` | 「설정 저장」(PUT `/api/dsm/me/notify-prefs` 를 부르고 곧장 재조회까지 하는 자리) | `data-gx="prefs-save-submit"` | `frontend/src/features/mobile/pages/MobileSettings.tsx` |
| U5#10 | `/dsm/notify` | 채널 칸 — **새 클릭 자리가 아니다**: U5#9 와 같은 단추(끄기/켜기)를 다시 안 누른다(같은 상태를 두 번 안 흔든다, 정본 문구). 필요했던 것은 저장 뒤 `…/list` 에 남는 channel 값을 안 눌러도 읽는 자리 | `data-gx="notify-rule-channel"` + `data-gx-channel={원래 채널 코드}`(표시명 아님 — `deliveryOutcome.tsx` 머리말과 같은 규약) | `frontend/src/features/dsm/pages/NotifySettings.tsx` |

### 1-B. 선언 없음 — 결정 번호로 c

| 행 | 화면 | 사유(증거 원문 요약) | 결정 번호 | 비고 |
|---|---|---|---|---|
| U1#4 | `/multi-stream-monitor`(인수 스트림) | 도달만 되고 스트림 자리(video/canvas) 0개 · 서버 값이 드러나는 칸이 애초에 없다 | **P-205**("정본 없음" 유지를 정본이 이미 확정) · §0.4 인접(`MultiStreamMonitor/index.tsx` 가 `rj-core` 임포트) | dsm/mobile/nav 밖 파일이라 이 차선이 못 고친다(금지구역 인접) |
| U3#14 | `/m/events/:id`(모바일 실시간) | 모바일 라우터엔 자리 셋뿐(inbox·eventDetail·settings) — 증거 자신이 "이 행은 ○ 다"라고 적음 | **D-306**(`decisions.yaml:2366` "「구간 참조」는 짓고 「구간 추출」은 계약 11조로 잠근다") | 영구 설계 잠금 — 자리가 생기면 잠금이 깨진 것 |
| U4#9 | `/dsm/events/:id`(증빙 영상) | 표 칸 「영상 구간」은 이름칸일 뿐 단추가 없다(`EventDetail.tsx` `CLIP_MISSING_REASON`) | **D-306**(위와 같음) | 영구 설계 잠금 |
| U6#14 | (화면 없음 — 기계 행) | "기계 흐름의 호출 경로가 선언되지 않았다" — U6 여덟 행은 애초에 화면이 없다(문구 칸 없음 규약, 턴 T 부터 유지) | **P-205**(기계 사용자에게 「누를 자리」는 문이라고 정본이 이미 확정 — `docs/agent/onboarding_48.md` "U6 · 외부 연계 시스템 — 기계 행 여덟" 절) | 이 행의 문(`GET /api/dsm/health` · 헤더 `X-GX-Schema`)은 이미 정본에 섰고 U56 이 짠 `test_u56_schema_header.py` 가 잠근다 — 화면 쪽 `data-gx` 선언 대상이 아니다. **화면이 없어 못 다는 것이지 안 만든 것이 아니다** |

**선언 표 요약**: 새로 단 `data-gx` 11개(6행 · 표 1-A) · 선언 없음 4행(표 1-B, 전부
결정 번호 있음). 9 + (U2#3 은 Q 몫으로 열어 둠) = 전 대상 완료.

---

## 2. 온보딩 +4 — 8회차(`turn_ao_8.json`, 34.5/48 · 반7 · 빨강10) 재조사

17행(반7+빨강10) 전부를 evidence 줄로 갈랐다. 우리 소유 파일(`features/dsm/**` 단
`EventList.tsx` 제외 · `features/mobile/**` · `features/nav/**`) 안에서, **화면
문구·상태 칸**이 원인인 것만 골라 고쳤다 — 데이터 상태·기능 결손·§0.4 밖·계약
잠금은 손대지 않았다(고쳐도 제품을 안 바꾸는 헛손이 된다).

### 2-A. 이번 턴 코드로 고친 것 — 2행

| 행 | 원인(evidence 줄) | 고침 |
|---|---|---|
| **U2#4** `/dsm/events/:id` | "snapshot [200] jpeg=True · img(snapshot, naturalWidth>0)=0" — `EventSnapshot` 의 `dataGx` prop 은 안 주면 `img` 에 `data-gx` 속성을 **안 단다**(컴포넌트 머리말, `EventSnapshot.tsx:39-44`). `MobileEventDetail.tsx:815` 는 이미 `dataGx="snapshot"` 을 주는데(U3#3 초록의 이유) 관제 쪽 `EventDetail.tsx` 만 그동안 안 줬다 — 사진이 안 그려진 게 아니라 **잴 셀렉터 자체가 없었다** | `EventDetail.tsx` 의 `<EventSnapshot .../>` 호출에 `dataGx="snapshot"` 추가 |
| **U5#14** `/dsm/system` | "◐ 상한(셋째 조건 — 절 ID)" — 턴 AO(P-408)가 이 화면의 재시작 **사유** 칸 하나만 `safeFreeText()` 로 감쌌다. 같은 화면에 자유 문장이 여섯 더 있었다: 백업 선언 실패 사유(`back.reason`) · 회수증 실패 사유(`receipts.data.reason`) · 저장 용량 사유(`storage.data?.reason`) · 저장 용량 각주(`capacity_note`) · 분모 출처(`capacity_source`) · 사용량 각주(`used_note`) — 전부 서버 자유 문장을 원문 그대로 찍고 있었다 | `SystemSettings.tsx` 의 위 여섯 자리 전부 `safeFreeText()` 로 감쌈(재시작 사유 칸은 이미 돼 있어 손 안 댐) |

두 고침 모두 **가설**이다 — 라이브 서버를 이 턴에 두드리지 않았으므로(V 몫) 다음
회차가 실제로 오르는지 가른다. `backend/tests/test_ap_l_click_declares.py` 가 소스
문자열로 회귀만 막는다(HTTP 없음).

### 2-B. 조사했으나 이 차선이 못 고치는 것 — 15행(evidence 줄 근거)

| 행 | 갈래 | 근거 |
|---|---|---|
| U1#2 | 정본이 이미 ◐ 확정(D-444) | "카메라 정상/이상 칸 없음 — 정본 표기" — 월 모드 자리 화면이 아니다, 다시 판단할 자리 아님 |
| U1#4 · U3#14 · U4#9 | 결정 잠금/§0.4 | 위 1-B 표와 동일(P-205·D-306) |
| U1#8 · U2#2 | 데이터 상태 | "처리 단계 값 0칸" — `EventList.tsx`(N4 소유·제외 파일) 코드는 정상, 그 회차 씨앗이 미처리 건을 안 남겼다. 결정 번호 없음 — 온보딩 문서에 "고칠 것"(드릴 씨앗 확장)으로 적어 둠(§3 참조) |
| U1#11 | 데이터 상태 | "「실제로 확인·접수」 안 보임" — `FocusQueue.tsx` 는 서버 `allowed_next` 만 그린다(D-399) · 초점 사건이 이미 미처리를 지난 표본 상태 |
| U2#6 | 인수 자산(메뉴에서 이미 뗌) | `/report-template` — SCOPE 밖 · 이번 턴 P-420 으로 c 편입(§3) |
| U3#1 | 판정기 타이밍(우리 코드 아님) | evidence 의 최종 url 이 이미 `/m/inbox`다 — "결과 문장" 은 EventDetail 쪽 상태 칸인데 페이지가 이미 다른 화면으로 넘어간 뒤 본문을 읽은 것으로 보인다. 코드(`EventDetail.tsx::notify()`)는 세 갈래 다 "발송을 요청했습니다"를 이미 담고 있다(턴 AN·AO 가 이미 고침) — 더 손댈 화면 쪽 자리가 없다. `/m/inbox` 카드 미반영은 `mine=true` 기본 설계(P-188)와 얽혀 있어 Q 의 P-425 몫 |
| U4#8 | 기능 결손 | "조합 검색 없음 → ◐ 상한" — `EventList.tsx`(N4 소유) · 이 턴 N4 가 P-424 로 구현 배정받음 |
| U4#11 · U5#2 | 인수 자산 | `/device`·`/roles` — dsm/mobile 밖 파일, SCOPE 밖. U5#2 는 이번 턴 P-420 으로 c 편입(§3), U4#11 은 FWS 실사용이라 메뉴에서 안 떼 c 밖 유지 |
| U4#15 | 데이터 상태(+ N4 파일) | "「보고 표시」·「보고함」 둘 다 없음" — `EventList.tsx`(제외 파일) · 그 프리셋에 렌더된 행이 0건일 가능성. 결정 번호 없음 |
| U6#3 | 설계 의도(D-371) | 키 401 · JWT 200 그대로면 ◐ 가 **맞는** 답(의도된 절반) — 고칠 결함이 아니다 |

---

## 3. P-420 — c2 → c 편입 · 재검토 7 확정

전문은 `docs/agent/onboarding_48.md` 끝의 **「★ 턴 AP c 확정 표(P-420)」** 절에 썼다
(요청대로 그 문서 끝에 붙이기만 했다 · 새 코드 변경 없음 — `roleNav.ts` 는 턴 AA 때부터
이미 옳았다). 요약:

- **U2#6**(`/report-template`) · **U5#2**(`/roles`) → `NAV_ACQUIRED_HIDDEN` 결정
  **P-420** 으로 c2 확정 → c 편입. 48 기준 분자·분모는 그대로, 상한 기준 분모만
  `48 − c` 로 움직인다(두 수 규약, P-408).
- **c_rows 갱신**: `U1#2, U1#4, U1#11, U2#6, U3#14, U4#9, U5#2` (5 → 7, `U3#7`
  은 8회차에 이미 초록이라 계속 제외).
- **재검토 7 확정**(U1#8·U2#2·U2#16·U4#15·U6#4·U2#4·U4#8): 닫힘 2(U2#16→P-410 ·
  U6#4→P-409, 이미 8회차 초록) · 이번 턴 코드로 고침 1(U2#4, 위 §2-A) · N4 이관
  1(U4#8→P-424) · 아직 열림·고칠 것 3(U1#8·U2#2·U4#15 — 결정 번호 대상이 아닌
  표본 결손, "고칠 것" 한 줄씩 적어 둠).

---

## 4. 새 시험

`backend/tests/test_ap_l_click_declares.py` — 소스 문자열 대조(HTTP 없음, 턴 AN·AO
자매 파일과 같은 성질):
① 1-A 표의 `data-gx` 6곳이 실제로 그 단추·칸에 붙어 있는가.
② `EventDetail.tsx` 가 `EventSnapshot` 에 `dataGx="snapshot"` 을 주는가(+ 모바일
쪽 회귀 방지).
③ `SystemSettings.tsx` 의 자유 문장 여섯 자리가 전부 `safeFreeText()` 를 거치는가
(+ 턴 AO 가 먼저 고친 재시작 사유 칸 회귀 방지).
`TheSelfTestCanFail` — 자기시험 둘(존재하지 않는 표식·호출을 찾게 해 진짜로
실패하는지 확인).

실행(처음 `--create-db`):
```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_l -w /app gx-shell \
  python -m pytest tests/test_ap_l_click_declares.py -q -p no:randomly --create-db
```
첫 실행에서 `CameraAddressDeclaresClickPlacesTests::test_row_start_button_has_data_gx`
가 **거짓 실패**했다 — 시험 자체의 버그였다("이 한 대 채우기" 문자열이 이 파일
머리말 주석(턴 U 표기)에 두 번 먼저 나와 `index()`가 **주석**을 button 으로
잡았다). 실제 소스(`CameraAddress.tsx:304` 부근)에는 `data-gx` 가 이미 옳게
붙어 있었다 — `index()` → `rindex()`(마지막 자리 = 실제 JSX 자식 글자)로 시험을
고쳤다(제품 코드는 안 고쳤다). 재실행(`--create-db` 없이):
```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_l -w /app gx-shell \
  python -m pytest tests/test_ap_l_click_declares.py -q -p no:randomly
```
**결과: 20 passed, 0 failed, 5 warnings in 400.51s (0:06:40).**

---

## 5. 끝낼 때 (규약 다섯 항목)

① **바꾼/만든 파일**
- `frontend/src/features/dsm/pages/People.tsx` (data-gx 2)
- `frontend/src/features/dsm/pages/CameraImport.tsx` (data-gx 2)
- `frontend/src/features/dsm/pages/CameraAddress.tsx` (data-gx 4)
- `frontend/src/features/mobile/pages/MobileSettings.tsx` (data-gx 1)
- `frontend/src/features/dsm/pages/NotifySettings.tsx` (data-gx + data-gx-channel 1)
- `frontend/src/features/dsm/pages/EventDetail.tsx` (`dataGx="snapshot"` 1 · U2#4)
- `frontend/src/features/dsm/pages/SystemSettings.tsx` (`safeFreeText` 확장 6곳 · U5#14)
- `docs/agent/onboarding_48.md` (끝에 「★ 턴 AP c 확정 표(P-420)」 절 추가만)
- `docs/agent/checkpoints/turn-ap/L.md` (이 파일)
- `backend/tests/test_ap_l_click_declares.py` (새 시험)

② **시험 이름 · 결과**
```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_l -w /app gx-shell \
  python -m pytest tests/test_ap_l_click_declares.py -q -p no:randomly
```
**20 passed, 0 failed, 5 warnings in 400.51s (0:06:40).** (첫 회는 `--create-db` +
시험 자체의 거짓 실패 1건을 고친 뒤 재실행 — §4 참조. 제품 코드는 그 재실행으로
안 바뀌었다, 시험의 `index()`→`rindex()` 만 고쳤다.)

③ **닫은 절 · 못 닫은 절** — 이 차선은 §0.10 기능명세 절을 새로 닫지 않았다(온보딩
표·선언 작업이라 별표 절 승격 대상이 아니다). P-423(선언 10 중 9 — 지시받은 정확한
목록)·P-420(c2 2행 편입)은 닫았다. U2#4·U5#14 온보딩 +2 는 **가설**로 남긴다(V
재측 전까지 "닫음"이라 적지 않는다).

④ **조율자에게 넘길 줄**
- `EVENT_ENTRY_SURFACE`: 이 턴 새 `/api/dsm/` 라우트를 안 열었다 — 넘길 줄 없음.
- 공용 파일: 손대지 않았다 — 넘길 줄 없음.
- Q 에게: U2#3(「되돌리기(사유 필수)」 못 찾음)은 이 차선의 P-423 목록(9행)에 없어
  손 안 댔다 — 필요하면 Q 가 판단.

⑤ **스스로 의심하는 점**
- U2#4·U5#14 고침은 **가설**이다 — 라이브 미측정이라 다음 회차가 실제로 올린다는
  보장이 없다(같은 자리에서 턴 AN 의 U3#1·U3#16 도 한 회차는 안 움직였다가 다음
  회차에 올랐다 — 지연이 있을 수 있다).
- U6#14 는 "화면이 없어 data-gx 를 못 단다"고 적었는데, 혹시 Q 쪽 harness 가 실은
  헤더 존재를 우리 screen 표식이 아니라 **다른 신호**로 찾고 있었다면(예: 응답
  헤더 자체를 셀렉터처럼 기대) 이 판단이 틀렸을 수 있다 — Q 확인 필요.
- U5#10 의 `data-gx-channel` 은 "원래 채널 코드"를 싣는데, `cs.join(',')` 가 배열이
  비었을 때(``) 빈 문자열을 싣는다 — Q 의 술어가 빈 문자열을 어떻게 읽는지 확인
  안 했다.
