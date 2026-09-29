# 턴 AN · 차선 L(화면 말 · 술어) — P-396 온보딩 갈래 표 · 화면 문구 · 「누른 뒤」 술어

## ① 바꾼/만든 파일
- `docs/agent/onboarding_48.md` — 끝에 **「★ 턴 AN 갈래 표(P-396)」** 절을 붙였다(기존 내용은
  줄이지 않았다). 여섯째 회차(`turn_am_6.json`) 빨강 13·반 12 = 25행 전부에 행 번호·색·
  증거 한 줄·갈래(a/b/c)·비고(고칠 파일 또는 절 번호 또는 사유)를 적었다. 합계
  **(a) 8 · (b) 1 · (c) 16**.
- `frontend/src/features/mobile/pages/MobileSettings.tsx` — 온보딩 U3#16. 새로고침 뒤에도
  남는 "저장 여부" 줄이 「저장된 설정이 있습니다.」였다 — 저장 **직후**에만 뜨는 상태 칸의
  낱말("저장됨")과 달라 셋째 조건 계측(문자열 대조)이 "화면 「저장됨」=False"로 읽었다.
  「저장됨 — 이미 정한 값이 있습니다.」로 두 낱말을 하나로 모았다.
- `frontend/src/features/dsm/pages/EventDetail.tsx` — 온보딩 U3#1. "알림 보내기"의 결과가
  `message.*` 토스트뿐이었다(이 화면의 다른 쓰기 — 진위 판정·등급 재판정·상급기관 제출 —
  는 전부 이미 상태 칸을 쓰고 있는데 발송만 그 규약을 안 따랐다). `notifyOutcome` 상태와
  `data-gx="notify-outcome"` Alert 를 더해 토스트가 사라진 뒤에도 결과 문장이 남게 했다.
- `backend/tests/test_an_l_screen_language.py` — 새 파일. 위 두 파일이 다시 새지 않는가를
  소스 문자열로 좁혀 잰다(P-371 자매 파일과 같은 성질 — HTTP 를 안 때린다).
- `scripts/verify_click_completes.py` — **술어 추가만**(P-118 회색 중 「누를 자리를
  선언하지 않은」 6행을 채웠다 — 자세한 근거는 각 F() 앞 주석 참조):
  - **U2#9** 「요원별 처리 현황」 — `goto("/dsm/team-status")` + `GET /api/dsm/stats/by-reviewer`
    + `srv_reflect(..., "total_reviewed")`. U1#2·U1#3 과 같은 모양(화면 자체가 부른다).
  - **U2#16** 「알림 규칙 확인」 — `goto("/dsm/notify")` + 같은 GET(U5#9 와 같은 `rules` 필드,
    다만 **다른 페르소나(U2)의 읽기**라 U5#9 의 쓰기와 상태를 안 겹친다).
  - **U4#1** 「주간 상황 요약」 — `btn("7일")` + `GET /api/dsm/events` + `srv_reflect`.
    온보딩 실측(`turn_am_6.json`) 이 U4 계정으로 이미 초록을 낸 사실을 그대로 옮겼다.
  - **U4#5** 「월간 보고서 자동 생성」· **U4#15** 「상급기관 제출 자료」 — 둘 다
    `status_is(403)`. **처음엔 U4(읽기 전용)가 정말 403 을 받는지 스스로 의심했다** —
    `api_u24.py` 의 `_report_reader_denial`/`_upper_report_set` 코드만 보면 `is_read_only`
    가 오히려 **허용**하는 것처럼 읽혀서 한 번 후보에서 뺐다. 그런데 `Reports.tsx:24` 의
    주석과 **기존 백엔드 시험 두 개**(`test_u24_reports.py::
    test_read_only_official_downloads_but_cannot_create` ·
    `test_u24_turn_t.py::test_read_only_role_cannot_check`)가 **플랫폼 문지기**
    (`common/role_gate.py::READONLY_DENIAL_CODE` — 앱 라우트보다 앞에 서는 미들웨어)가
    이미 403 을 잠가 둔 사실을 증명하고 있어 되살렸다. U4#S5 가 쓰는 것과 같은
    `status_is` 모양이고, 서버 문장("읽기 전용 계정입니다…")이 그대로 화면에 뜬다
    (`userFacingError` 의 `fromServer` 갈래).
  - **U6#14** 「스키마 버전 확인」 — `api()` + `GET /api/dsm/health` + `srv_reflect(...,
    "schema")`. 종전 주석은 "술어가 헤더라 잴 자리가 없다"였는데, `Integrations.tsx:367`
    가 **같은 값을 몸통에도** `스키마 {healthData.schema}` 로 그리고 있어 U6#2·U6#3·U6#15
    와 같은 몸통-반영 모양으로 좁혀 잴 수 있었다(헤더 자체는 여전히 못 잰다 — 지어내지
    않는다).
  - `--self-test` 로만 확인했다(`--measure` 는 안 돌렸다 — V 의 몫). 40/40 양성 대조 통과.

## ② 시험 이름과 결과
- `MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings
  -e DB_TEST_NAME=test_gx_lane_l -w /app gx-shell python -m pytest
  tests/test_an_l_screen_language.py -q -p no:randomly --create-db`
  → **5 passed**, 5 warnings(Pydantic 지원종료·naive datetime 경고뿐 — 실패 아님).
- 호스트 `python scripts/verify_ui_copy.py` → **잔여 0건**(기준선 84건 · 갚은 것 84건) ·
  본 비율 100% — dsm/mobile/login 스코프 안 셋째 조건 위반이 이미 전부 갚혀 있음을
  오늘 재확인(내가 새로 갚은 것은 아니다 — 턴 AM 차선 L 의 몫. 표에 그대로 적었다).
- 호스트 `python scripts/verify_click_completes.py --self-test` → **자기시험 통과**
  (양성 대조 40/40 초록 · 기대 호출 식 40개 자기 URL 통과 · 상태를 바꾸는 클릭 10자리
  전부 되돌림 선언 · 분모 48 그대로). `--measure` 는 **돌리지 않았다**(라이브 서버 — 세종
  규약 P-399 · 회차 사이엔 고칠 수 있으나 재는 것은 V 의 몫).

## ③ 닫은 절 · 못 닫은 절
- 별표 절(P-356) 승격 대상 없음 — 이번 일은 온보딩 갈래 정리·화면 문구·측정 도구
  술어 채우기(P-396·P-118)라 「명세 절 닫기」범주 밖. `docs/agent/roadmap/
  기능명세_미포함표_20260925.md` 의 O-03(라이선스·계량·청구)을 U5#15 의 갈래(b)로
  지목했지만, 그 절 자체를 닫지는 않았다(그 결정은 이 차선 소유 밖 — §3 참고).

## ④ 조율자에게 넘길 줄
- 없음 — 공용 파일(`backend/apps/fws/api.py`·`urls.py`·`frontend/src/App.tsx`·
  `features/fws/routes.ts`·`features/fws/copy.ts`·`backend/apps/fws/constants.py`)을
  건드리지 않았다. `EVENT_ENTRY_SURFACE`·라우트 대장에 넣을 새 `/api/dsm/` 라우트도 없다
  (새 라우트를 안 열었다 — 기존 문만 새로 잰다).
- **세종/조율자 확인 요청**: U6#4(웹훅) 은 이 문서 위 절이 이미 "웹훅 서명키
  (`WEBHOOK_SIGNING_KEYS`)가 컨테이너 환경에 없다 — 창 2b 항목"이라고 적어 두었다 —
  이 차선은 그 환경변수 배선을 건드리지 않았으니 창 2b 담당이 그대로 가져가면 된다.
- **표본/데이터 상태 다섯 행**(U1#8·U1#11·U2#2·U3#7·U4#15) — 코드를 읽어 결함을 못
  찾았지만 확정도 못 했다. 다음 회차(일곱째)에서 같은 행이 또 빨갛다면 표본 가설을
  버리고 다시 봐야 한다는 뜻이다 — V/세종에게 이 표를 참고자료로 남긴다.

## ⑤ 스스로 의심하는 점
- **U4#5·U4#15 의 403 술어**: 처음엔 앱 코드(`_report_reader_denial`)만 보고 "이 코드는
  읽기 전용도 허용한다"고 잘못 판단해 후보에서 뺐었다. 기존 Django 시험 두 개를 찾아
  플랫폼 미들웨어가 앱 코드보다 먼저 막는다는 것을 확인하고 되살렸다 — 하지만 이
  미들웨어 배선 자체를 **내가 직접 실행해 재현**한 것은 아니고, 기존 시험 파일의 코드를
  읽고 판단했다. `--measure` 로 실제로 눌러 보기 전까지는 100% 확신이 아니다.
- **U2#4(스냅샷 이미지 미표시)**: `EventSnapshot.tsx` 를 정독했지만 뚜렷한 결함을 못
  찾았다 — (c)로 적었으나 사실은 「원인 불명」에 가깝다. 같은 부품을 쓰는 모바일판
  (U3#3)은 그 회차에 초록이었다는 점이 유일한 단서다.
- **U6#14 의 `srv_reflect`가 실제로 몸통 `schema` 칸을 제대로 문자열 비교하는가**는
  `--self-test`(합성 표본)로만 확인했다 — 실제 JSON 값 `"1.1"` 같은 짧은 문자열이
  `on_screen`/텍스트 비교 로직에서 숫자 필드(예: 카메라 대수)와 우연히 겹쳐 오탐을
  내지 않는지는 실측(`--measure`)이 나와야 완전히 안다.
- **U4#1 의 `srv_reflect("/api/dsm/events?limit=20", "events")`**: U1#8 의 것을 그대로
  빌렸다 — "7일" 필터가 실제로 걸렸는지까지는 안 재고 "이벤트 목록에 무언가 반영됐다"만
  잰다(그 대신 ④ 문구에 "보고 있는 기간"을 넣어 그 화면에 있다는 것 정도는 확인한다).
  더 정밀한 술어(정확히 7일 창의 `since`/`until`) 는 다음에 누가 다시 좁힐 수 있다.
- 갈래 표의 (c) 16건 중 「인수 자산」 5건(U1#4·U2#6·U4#11·U5#2 + 기존 U3#14/U4#9 계약
  잠금과는 별개)은 전부 **정적 코드 확인**(import 문·SCOPE 상수)으로 판단했다 — 화면을
  직접 열어 눈으로 본 것은 아니다.
