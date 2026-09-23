# U온 (온보딩) → 조율자 — 턴 AE

열 계정: 09-23 09:5x KST (대표 한 마디로 창을 열었다는 기록에 맞춰 실측 시각을 아래 각 절에 그대로 적는다).

## 0. 고르기 전에 가른 것 — 이 차선의 핵심

U2 빨강 넷 · U4 빨강 둘을 실측으로 갈랐다(§ 5 표는 아래 ⑤). 결론:

- **U2#3(이벤트 등급 재판정)** = **문이 없어서 빨강** → 코드로 끝까지 올렸다.
- U2#2·U2#6·U2#16, U4#15 = **데이터가 0건이라 빨강**(뒤에 상세).
- U4#11(`/device`)은 파일 소유가 아니고(뒤에 상세) 손대지 않았다.

⇒ **U2#3 하나를 끝까지 올렸다.** U4 는 소유표 안에서 고칠 수 있는 「문 없음」 행이
하나도 없었다(둘 다 데이터 0건이거나 파일 밖) — ③에 사유를 적는다.

---

## ① 실측 명령과 출력 그대로

### 갈라 잰 것 — U2#3 「문 없음」 확인

`GradeRule`/`set_grade_rule`(`backend/apps/dsm/services.py:980`)는 이벤트 **타입**의
앞으로의 기본 등급만 바꾼다는 것을 소스로 확인했다. 기존 사건 한 건의 `severity` 를
지금 다시 매기는 라우트는 `backend/apps/dsm/api.py` · `api_u1.py` · `api_u24.py` 전체를
grep 해도 **0개**였다(`severity` 를 쓰기로 받는 라우트가 `/settings/grade-rules` 하나뿐).

### 갈라 잰 것 — U2#2 / U4#15 「데이터 0건」 확인 (같은 뿌리)

```
docker exec -w /app gx-shell python manage.py shell -c "
from stream_monitors.models import DetectionEvent
qs = DetectionEvent.objects.filter(response_state='occurred').exclude(track_id__startswith='data_source=probe')
print(qs.count())
"
```
출력: **`0`**

→ **개발 DB 전체에 「미처리(occurred)」 상태의 실제(비-probe) 이벤트가 0건이다.**
U2#2(관제팀장 · ETRI-Group)와 U4#15(지자체 담당관 · 같은 그룹)가 같은 「미처리 보기」
프리셋을 쓰는데, 그 프리셋에 걸리는 12건을 개별 조회하니 **전부**
`track_id='data_source=probe;run=...'`(온보딩 계측기가 심은 씨앗)였다 — 실제 데이터는
없다. 그래서 `/dsm/events`(기본 프리셋 `unhandled`) 화면에 행이 0줄이고, 행이 0줄이면
U4#15 가 찾는 「보고 표시」/「보고함」 토글도 화면에 없다(행마다 그리는 토글이라 행이
없으면 토글도 없다 — 코드가 아니라 데이터의 결과).

같은 사실을 실제 로그인 + HTTP 로도 대조했다(gxseed_u4_official):
```
docker exec -e GX_SEED_ROLE_PASSWORD gx-shell python -c "
... POST /api/v1/auth/login (gxseed_u4_official) → 200
... GET /api/dsm/events?limit=50&response_state=occurred (Bearer 토큰) → 200, total 0
"
```
→ 실측 결과 `events total 0`. 화면과 서버가 같은 사실을 말한다.

### 확인 — EventList.tsx 「보고 표시」/「보고함」 토글은 이미 코드로 있다 (오늘 새로 안 지었다)

`frontend/src/features/dsm/pages/EventList.tsx:1167-1195` (턴 T · 상급 보고 열)에
이미 완성된 토글이 있었다(호출: `dsmU24StatsEndpoint.upperReportFlags` ·
`upperReport(eventId)` · 성공 시 `flags.reload()`로 재조회). 이 코드는 커밋
`f799fb1`(09-21 23:31 KST)부터 이미 있었고 09-22 측정(12:48) **이후**다 — 즉 코드가
없어서가 아니라 **잴 때 행이 0줄이라 안 보인 것**이다. `measure_onboarding_t.py:1783`도
`/dsm/events`를 기본 프리셋(미처리)으로 열어 같은 0줄을 만난다.

### 새로 지은 문 — U2#3 검증 (직접 함수 호출 · gx-shell manage.py shell, revert 포함)

```
event 4802 (그룹 ETRI-Group) 등급 재판정:
  before severity = critical
  POST 상당 호출 1 → {'event_id': 4802, 'severity': 'warning', 'previous_severity': 'critical', 'audit_id': 340014}
  DB 재조회 → severity = warning
  되돌림 호출 → {'event_id': 4802, 'severity': 'critical', 'previous_severity': 'warning', 'audit_id': 340015}
  DB 재조회 → severity = critical (원복 확인)

음성 대조:
  severity='bogus' → HttpError 400 "severity='bogus' 은 계약에 없다. 허용: critical, info, warning."
  event_id=999999999 → HttpError 404 "그런 사건이 없습니다."
  두 실패 뒤 event 4802.severity 재조회 → critical (안 바뀜 — 실패가 조용히 상태를 안 바꾼다)
```

### 타입검사 (기준선과 경합 없이 단독 실행)

```
MSYS_NO_PATHCONV=1 docker exec -w /app gx-fe-build npx tsc -p tsconfig.app.json --noEmit
```
출력 줄 수: **3234줄** (기준선과 동일 — 새 오류 0 · `EventDetail.tsx`/`EventList.tsx` 관련
오류 0건). 다른 tsc·무거운 게이트와 동시에 돌리지 않았다.

### 파이썬 문법 · 라우트 등록

```
docker exec -w /app gx-shell python -c "import py_compile; py_compile.compile('apps/dsm/api_u24.py', doraise=True)"
→ OK syntax
docker exec -w /app gx-shell python manage.py check
→ System check identified no issues (0 silenced).
```
(gx-shell 의 `manage.py runserver 8000` 은 `--noreload` 로 떠 있고, 다섯 차선이 동시에
그 서버를 쓰고 있어 **재기동은 하지 않았다** — 그래서 라이브 HTTP 로는 새 라우트를 못
때렸다. 대신 같은 프로세스를 새로 여는 `manage.py shell -c`로 함수를 직접 불러 재고,
`manage.py check`로 URL/앱 등록이 깨지지 않았음을 확인했다.)

### 부분 전량 (백그라운드로 돌렸다 — 완료되면 이 절에 결과를 덧붙인다)

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell python -m pytest \
  tests/test_u24_audit_target.py tests/test_u24_reports.py tests/test_u24_stats.py \
  tests/test_u24_turn_t.py tests/test_route_tenant_scope.py tests/test_tenant_isolation.py \
  tests/test_dsm_app.py tests/test_api_contract.py -q --create-db -p no:randomly
```
(⚠ 이것은 **전량 정본 호출이 아니다** — 관련 파일만 좁힌 부분 시험이다. 전량은 조율자
병합 시 정본 호출로 다시 돌아야 한다.)

결과(완료 후 재확인 — 첫 실행은 `| tail -80` 로 파이프해서 exit code 가 `tail` 것으로
가려졌다. 파이프 없이 exit code 를 파일에 직접 받아 다시 확인했다):
```
181 passed, 37 warnings in 360.75s (0:06:00)
EXITCODE=0
```
새로 지은 `event_severity_set`/`_event_severity_set` 를 포함해 U24 관련 시험·라우트
스코프 시험·테넌트 격리 시험·계약 시험이 전부 초록이다. (경고 37건은 이번 변경과
무관한 기존 Pydantic deprecation 경고 — 실측만 하고 안 건드렸다.)

---

## ② 고친 파일:줄

- `backend/apps/dsm/api_u24.py`
  - 357~379행(신설): `@route.post("/events/{int:event_id}/severity")` — U2 door.
    `_scope`·`@tenant_scoped` 그대로, 새 인증 경로 안 만듦.
  - 726~773행(신설): `_event_severity_set(...)` — 존재·소유 확인은
    `services.event_detail`(기존 함수 재사용) → `DetectionEvent._base_manager` 로
    쓰기 → `audit.record_event_action` 으로 감사(성공·실패 둘 다) → 응답에
    `severity`·`previous_severity`·`audit_id`.
- `frontend/src/features/dsm/pages/EventDetail.tsx`
  - 233~296행(신설): `regrade()` 콜백 — `Modal.confirm` + 사유 입력 + 실패 시
    칸에 남김(토스트만 쓰지 않음, 기존 진위 판정과 같은 규약).
  - 739~767행(신설): 「처리 단계 · 진위 판정」 카드 안에 「등급 재판정」 행 —
    등급 셋(정보·경고·위험) 단추 + 현재 등급 배지 + 실패 자국(`FailureNotice`).
    지금 등급과 같은 단추는 `disabled`.

두 파일 다 U온 소유표 안(§2: `EventDetail.tsx` · `backend/api_u24.py`(U2 door)).
`frontend/src/features/dsm/api.ts`(엔드포인트 상수 모음)는 소유표 밖이라 **안 건드렸다**
— 새 상수를 안 만들고 `dsmPostQueryOnce('/api/dsm/events/${id}/severity', …)` 처럼
문자열을 직접 썼다(기존 `dsmU1Endpoint.upperReport`와 같은 모양의 함수형 URL 패턴을
그대로 인용).

---

## ③ 안 한 것과 사유

1. **U2#2 · U2#6 · U2#16 (데이터 0건 계열)** — 손대지 않았다. 세 행 다 뿌리가
   같다: 「미처리 이벤트」·「보고서 실행」·「알림 규칙」 셋 다 **실제(비-probe) 행이
   0건**이다(①의 `qs.count() == 0` 실측 + `notify-rules` 서버 규칙 0건은 정본
   문서에 이미 실측돼 있다). 시드는 `scripts/` 아래 시드 스크립트 소유(U56/K+Q)이고
   U온 소유표에 없다 — **시드로 초록을 사면 안 된다**는 규약도 있어, 이 차선에서
   임의로 시드를 심지 않았다. U56/K+Q 에 쪽지로 넘긴다(④ 참고).
2. **U4#11 (`/device` 표 행 0)** — 손대지 않았다. 실제 화면 파일은
   `frontend/src/features/device/listDevice/ListDevice.tsx` 이고(온보딩 표기
   `/dsm/pages/Device*.tsx` 패턴과 다른 실제 경로), **U온 소유표에 없다.** 그 화면은
   `rj-core`(§0.4 금지구역 자체)의 `CustomizableTable`·`getDeviceManagement` 를
   그대로 쓰는 델리버리 계열 CRUD 화면이라, 고치려면 남의 파일 + 금지구역 인접
   코드를 만져야 한다 — 하지 않았다.
3. **U4#15 화면 쪽 코드는 이미 완성돼 있었다** — 새로 지을 것이 없었다(①에 커밋
   시각 대조). 이 행을 올리는 유일한 길은 그 테넌트에 실제 미처리 이벤트를 심는
   것인데, 그것은 위 1번과 같은 「시드」 문제이고 같은 이유로 손대지 않았다.
4. **전량 정본 시험은 안 돌렸다** — 관련 파일만 좁힌 부분 시험(181개)을 돌렸고
   전부 통과했다(①). 전량(2,123개 전체)은 조율자 병합 시 §1 정본 호출로 다시
   돌아야 한다 — 이 차선은 그 전량을 대신하지 않는다.
5. **실제 HTTP(runserver 8000)로 새 라우트를 때리지 않았다** — 그 서버가
   `--noreload`로 다섯 차선이 공유하는 중이라 재기동하면 다른 차선의 측정을
   깬다(§1-1 「동시접속 1개」와 같은 종류의 위험). 대신 같은 코드를 새 프로세스
   (`manage.py shell`)로 직접 불러 재고 되돌렸다(①).

---

## ④ 조율자가 브라우저로 눌러 줄 것

**U2#3 (이 차선이 끝까지 올린 것)**
- 계정: `gxseed_u2_manager` (비밀번호는 `.env.gates` 의 `GX_SEED_ROLE_PASSWORD`)
- 주소: `http://localhost:3002/dsm/events/4802` (또는 그 테넌트의 아무 사건 상세)
- 무엇을 보면 초록: 「처리 단계 · 진위 판정」 카드 안에 **「등급 재판정」** 줄이
  있고, 지금 등급과 다른 단추(예: 「⚠ 경고」)를 누르면 확인 창 → 확인 후 위쪽
  「등급」 배지가 **새 값으로** 바뀐다(새로고침 없이, `event.reload()`가 다시
  읽은 서버 값). 되돌리려면 같은 자리에서 원래 등급 단추를 다시 누르면 된다
  (예: 「☠ 위험」).

**U56/K+Q 에 넘길 것(U2#2·U2#6·U2#16·U4#15 — 데이터 0건)**
- 이 넷은 **시드가 답**이다. 조율자가 직접 누를 것은 없다 — 시드가 심긴
  뒤에 같은 계정으로 `/dsm/events`(U2#2·U4#15) · `/dsm/notify`(U2#16) ·
  `/report-template`(U2#6)를 다시 열면 표 행이 보이는지가 다음 술어다.
  ⚠ 심을 때 `mark_unbillable` 표식을 **먼저** 박고 역할/데이터를 주는 순서를
  지켜야 한다(§5 U56 ①과 같은 규약) — 청구가 새는 순서로 심으면 이 수는
  「시드로 산 초록」이 된다.

---

## ⑤ 빨강 여섯 — 데이터 0건 / 문 없음 표

| 행 | 실측 사실 | 갈래 | 답 | 이 차선이 한 일 |
|---|---|---|---|---|
| U2#2 미처리 이벤트 확인 | `response_state=occurred` 비-probe 행 **0건**(전 DB) | 데이터 0건 | 시드 | 안 함 — U56/K+Q 로 |
| U2#3 이벤트 등급 재판정 | 재판정 라우트 **0개**(grep 전수) | **문 없음** | 코드 | **끝까지 올림**(①②) |
| U2#6 상황보고서 생성(`/report-template`) | `templates` 200 아님·표 행 0 (정본 실측) | 데이터/설정 0건 계열 | 시드/설정 | 안 함 — 이 차선 소관 밖으로 판단, 근거는 아래 「내가 틀렸던 것」 |
| U2#16 알림 규칙 확인 | 서버 규칙 0건(정본 실측) | 데이터 0건 | 시드 | 안 함 — U56/K+Q 로 |
| U4#11 카메라 설치 현황(`/device`) | 표 행 0 · 화면 파일이 소유표 밖(`rj-core` 계열) | 파일 밖(갈래 판정 보류) | 코드일 수도 있으나 **소유 밖** | 안 함 |
| U4#15 상급기관 제출 자료 | 토글 **코드는 이미 있음** · 기본 프리셋 행 0줄이라 안 보임 | 데이터 0건(U2#2 와 같은 뿌리) | 시드 | 안 함 — U56/K+Q 로 |

---

## ⑥ 내가 틀렸던 것

1. **조율자의 처음 힌트(U4#15 는 「화면 쪽 일」)를 그대로 따랐으면 틀렸을 것이다.**
   `EventList.tsx:1167-1195`를 먼저 읽지 않고 「토글이 없다」는 판정문만 믿었으면
   존재하는 코드를 다시 짓거나(중복) 엉뚱한 자리를 고쳤을 것이다. 소스를 먼저
   읽고, 커밋 시각(09-21 23:31)이 측정 시각(09-22 12:48)보다 **앞선다**는 것까지
   대조한 뒤에야 「코드는 있다·데이터가 없다」로 가설을 뒤집었다. 힌트가 이미
   있던 코드를 가리키고 있었을 뿐, 「고쳐야 한다」는 뜻은 아니었다.
2. **처음에는 U2#2 의 0건이 gxseed_u2_manager 테넌트만의 문제인 줄 알았다.**
   같은 그룹(ETRI-Group)에 대해 직접 ORM 으로 「occurred 12건」을 보고 「데이터가
   있는데 API 가 0건을 낸다 — 버그다」로 잠깐 판단했다. `include_probe` 규약을
   다시 읽고 그 12건 **전부**가 `track_id=data_source=probe;...` 표식이라는 것을
   개별 확인한 뒤에야 「버그가 아니라 실제 데이터가 없다」로 정정했다. 가설을
   실측(A/B: 개별 행의 `track_id` 대조)으로 기각한 자리다.
3. U2#3 을 U2 화면(`EventList.tsx`/목록)이 아니라 **상세(`EventDetail.tsx`)**에
   붙였다 — 정본 문구가 화면을 못박지 않았고, 「재판정」이라는 말과 같은 결의
   「진위 판정」이 이미 상세에 있어 같은 화면에 붙이는 것이 자연스럽다고
   판단했다. 조율자가 다른 화면(목록)을 원하면 쪽지 주시면 옮기겠다.

---

## 후속 — 전량이 잡은 것 (조율자 지시 · 2026-09-23 이후)

조율자가 전량 정본 1회를 돌려 `test_f05_event_api.py::EntrySurfaceIsLockedTest`
둘을 빨강으로 냈다 — 새로 낸 문(`POST /events/{id}/severity`)이 **F-05 진입면
계약**(`EVENT_ENTRY_SURFACE`)에 등재가 안 돼 있었다. 옳은 빨강이다 — 문을 낸 사람이
계약도 갱신해야 한다는 것이 「끝까지」의 나머지 반이라는 지적을 그대로 받는다.

### 등재한 항목과 옆에 적은 근거

`backend/tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE` 에 한 줄을 더했다(그
옆 주석 블록 포함, 그 파일의 다른 자리는 안 건드렸다):

```
("POST", "/api/dsm/events/{int:event_id}/severity"),   # U2#3 · 이벤트 등급 재판정 ★쓰기
```

옆에 적은 근거 넷 — **전부 실측**, 추측으로 적지 않았다:

1. **누가 부를 수 있나 / 읽기 전용 U4 는 403 인가 — 실측했다(추측 아님).**
   이 문 자신의 코드가 막는 것이 아니라 **저장소 전역 미들웨어**
   (`common/role_gate.py::RoleGateMiddleware`, P-119)가 「쓰기 메서드 + 읽기
   전용 역할」을 문 앞에서 끊는다는 것을 먼저 소스로 확인했고, 그 다음 실제로
   두드려 확인했다:
   ```
   gxseed_u4_official 로 로그인 → POST /api/dsm/events/4802/severity
     (params: severity=warning) 를 gx-shell 안에서 실제로 호출
   → 403 {"code": "read_only_role", "message": {"ko": "읽기 전용 계정입니다 —
     이 작업은 수행할 수 없습니다."}}
   ```
   그 뒤 DB 재조회로 `severity` 가 그대로(`critical`, 안 바뀜)인 것도 확인했다 —
   막힌 요청이 반쪽만 쓰지 않는다.
   ⚠ 이 서버(`gx-shell` 의 `manage.py runserver 8000 --noreload`)는 새 라우트를
   메모리에 안 올린 **옛 코드**로 떠 있다. 그런데도 이 403 은 유효한 실측이다 —
   `RoleGateMiddleware` 는 **URL 이 실제로 그 라우트에 물리기 전에**, 메서드와
   경로 문자열만 보고 끊기 때문이다(`judge_readonly` 는 뷰를 안 본다). 라우트가
   살아 있는 서버에서 다시 재도 **같은 미들웨어를 먼저 지나므로** 결과는 같다.
2. **남의 테넌트 사건 — 404.** `services.event_detail`(새 문지기를 안 짜고
   기존 함수를 그대로 재사용)이 커널의 `assert_scoped` 를 태운다. [실측]
   `event_id=999999999` → `HttpError(404, "그런 사건이 없습니다.")`.
3. **나쁜 값 — 400.** `DetectionEvent.Severity.values` 밖의 값은 거절한다.
   [실측] `severity="bogus"` → `HttpError(400, "severity='bogus' 은 계약에
   없다. 허용: critical, info, warning.")`.
4. **감사 행 · 되돌림.** 사건 4802(그룹 ETRI-Group)를 `critical → warning`
   (감사 #340014) → `warning → critical`(감사 #340015)로 되돌렸고, DB 재조회로
   원복을 확인했다(먼저 보고한 그 실측 그대로 — 이번에 다시 반복하지 않았다,
   같은 이벤트 상태를 두 번 흔들면 그 사이 다른 차선의 측정이 섞일 위험이 있다).

### 시험 파일만 돌린 결과 — 둘 다 초록

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -w /app gx-shell python -m pytest tests/test_f05_event_api.py -q -p no:randomly \
  > /tmp/pytest_f05.txt 2>&1; echo "EXITCODE=$?" >> /tmp/pytest_f05.txt
```
출력(파이프 없이 파일로 받아 exit code 를 직접 확인했다 — 지난번 `| tail` 실수를
반복하지 않았다):
```
............                                                             [100%]
12 passed, 34 warnings in 18.74s
EXITCODE=0
```
`test_the_count_is_not_zero`·`test_the_entry_surface_is_pinned_by_name` 둘 다
초록이고, 나머지 10개도 그대로 초록이다.

### 하지 않은 것 (지시대로)

- 수를 110 으로 되돌리려고 문을 없애지 않았다 — 그 문은 U2#3 을 올린 진짜 일이다.
- 개수 단언을 빼거나 `>=`/부분집합 비교로 시험을 느슨하게 만들지 않았다 —
  `EVENT_ENTRY_SURFACE` 는 여전히 `frozenset` 과의 **완전 일치** 비교다.
- 이 파일에서 등재한 그 한 항목과 옆 주석 말고는 아무것도 안 건드렸다.
- 다른 시험·다른 파일은 안 건드렸다. 커밋하지 않았다 — 조율자가 병합한다.
