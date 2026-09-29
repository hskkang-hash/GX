# N2 승격 제안 — FWS-F3-01~09 산림과 담당 앞 절 아홉(턴 AN · P-356·357·358·376·397 · 차선 N2)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다(작업지시 §하드룰).

세종 판정 P-397(F1·F2·F5·F6 이 이미 만든 문을 재사용한다)을 그대로 따랐다 — 새
표 **0**(`logger.AuditLogs` 감사 한 줄로 전부 처리 · `patrol.py`·`standby.py`·
`integration.py` 와 같은 관례), 새 App 없음, F-05 잠금(`apps.dsm.services` 만
거친다) 그대로.

## 0. 승격 규칙(P-356) 적용 요약

**닫은 아홉(FWS-F3-01~09)**이 넷을 다 갖췄다고 이 차선이 주장한다:

1. **실제 구현** — `backend/apps/fws/office.py`(신규) · `backend/apps/fws/
   api_office.py`(조율자가 세운 빈 컨트롤러에 라우트 17개 추가) ·
   `frontend/src/features/fws/pages/OfficeHome.tsx`(조율자가 세운 빈 화면을
   채움) · `frontend/src/features/fws/copy_office.ts`(신규). 새 표 0(요구
   「≤1」보다 더 좁혔다) · 새 App 0(P-357) · 이벤트 접근은 전부
   `apps.dsm.services` 를 거친다(F-05 잠금). **F3-05(오인 종결·산불 확정)는
   새 라우트가 0줄이다** — 기존 F1-06 문(`/api/fws/verifications/{id}/reply`)을
   산림과 담당 역할로 그대로 두드려 실측했을 뿐이다(P-397 이 요구하는 재사용의
   가장 좁은 예).
2. **실측 증거** — `docs/agent/evidence/SPEC/FWS-F3-0{1..9}.json` 9건, 전부
   `backend/tests/test_fws_f3a.py` 의 pytest 실행이 **기계로** 찍었다
   (`measured_by: "django_test_client"`). 공용 `tests/test_fws_app.py::
   _write_evidence` 를 고치지 않고, 이 차선의 시험 파일 안에 **같은 봉투 +
   `title_parts`**(제목이 부르는 것 ↔ 있는 것, 빈 칸 0)를 더한 자기 버전을
   썼다(`_규약.md` 요구 · O 게이트가 이 칸을 다시 셀 것이다).
3. **게이트** — 새 게이트 `scripts/verify_spec_fws_f3.py`(F6 게이트
   `verify_spec_fws_f6.py` 의 판정식을 그대로 베꼈다 · `--self-test` 있음 ·
   `title_parts` 빈 칸도 이 게이트가 추가로 잰다). 재실행 →
   **닫은 아홉 9/9 · PASS**(길목 시험 21 passed · 0 failed).
   `TheSelfTestCanFail` 짝은 `backend/tests/test_fws_f3a.py::
   FwsF3GateSelfTestCanFail`(같은 파일 안 — 새 파일을 늘리지 않았다) —
   **조율자에게: `scripts/_gate_header.py::SELF_TEST_LINKS` 에
   `"verify_spec_fws_f3.py": "backend/tests/test_fws_f3a.py"` 한 줄 등재
   요망**(공용 파일이라 이 차선이 스스로 고치지 않았다).
4. **대장 이동** — 아래 §2 의 표를 `ga_readiness.yaml` 의 `kind_derived.
   annex_promoted.closed` 에 F3-01~09 9건을 이어 붙이는 것을 제안한다(N2·N3
   가 이미 쓰는 그 자리 — D-309 원장은 건드리지 않는다).

## 1. 재사용 확인 — 무엇을 다시 안 지었나

| 절 | 재사용한 기존 문 |
|---|---|
| F3-01 위험지수·위기경보 | `apps.fws.risk.risk_today()`(F1-03) |
| F3-01 카메라 정상 | `apps.dsm.services.camera_pulse()`(UX-23) |
| F3-01 진행 사건 | `apps.dsm.services.recent_events()`(F-09) |
| F3-04 확인요청 발송 | `apps.dsm.services.notify_event()`(F1/F6 재사용) |
| F3-05 전체 | `apps.fws.verification.reply_verification()`(F1-06) — **새 라우트 0** |
| F3-07 산림청 번호 | `apps.fws.contacts.FOREST_REPORT_NUMBER`(F1-08) |
| F3-08 자원배정 발송 | `apps.dsm.services.field_reply()` · `notify_event()`(F2 임무·F6 통보 재사용) |
| F3-09 단계 계산 | `apps.fws.constants.compute_fire_stage()`(P-386 · F6-01 재사용) |

**새로 지은 것은 딱 셋**: (1) 그룹 전체를 안전하게 좁혀 보는 자리
(`office._group_user_ids` — `common.tenant_filters.filter_users_by_group` 재사용,
`apps/dsm/access_permission_service.py::person_permissions` 와 같은 문), (2) 「가장
가까운 감시원」 하버사인 거리 계산, (3) 헬기 요청의 **기지·도착예정** 구조화
기록(F6-05 `request_helicopter` 는 그 두 칸이 없어 옆에 둔다 — 그 함수는 고치지
않았다, D-212).

## 2. 표 — 닫은 아홉 건

| id | 제목 | 엔드포인트 | 증거 |
|---|---|---|---|
| FWS-F3-01 | 산불 상황판(띠 6수) | `GET /api/fws/office/dashboard` | `evidence/SPEC/FWS-F3-01.json` |
| FWS-F3-02 | 조심기간·특별대책기간 설정 · 초소·순찰 구역 등록 | `POST/GET .../office/season` · `.../office/posts` | `evidence/SPEC/FWS-F3-02.json` |
| FWS-F3-03 | 인력 배치(근무표 CSV · 야간 5분대기조) | `POST/GET /api/fws/office/roster` | `evidence/SPEC/FWS-F3-03.json` |
| FWS-F3-04 | 탐지 확인 요청 1클릭 · 10분 시계 | `POST/GET .../fire-events/{id}/verification-request` | `evidence/SPEC/FWS-F3-04.json` |
| FWS-F3-05 | 오인 종결(사유) · 산불 확정 | `POST /api/fws/verifications/{id}/reply`(F1-06 재사용 · 새 라우트 0) | `evidence/SPEC/FWS-F3-05.json` |
| FWS-F3-06 | 신고 접수 기록(30분 시계 시작) | `POST/GET .../fire-events/{id}/intake` | `evidence/SPEC/FWS-F3-06.json` |
| FWS-F3-07 | 산림청 상황실 통보(042-481-4119) · 헬기 요청 기록 | `POST/GET .../fire-events/{id}/agency-notify` | `evidence/SPEC/FWS-F3-07.json` |
| FWS-F3-08 | 자원 배정(진화대·차량·드론 · 임무 문안 자동) | `POST/GET .../fire-events/{id}/resource-assignment` | `evidence/SPEC/FWS-F3-08.json` |
| FWS-F3-09 | 대응단계 입력 3칸 → 단계 제안 → F4 확정 요청 | `POST/GET .../fire-events/{id}/stage-proposal` | `evidence/SPEC/FWS-F3-09.json` |

프런트: `frontend/src/features/fws/pages/OfficeHome.tsx`(`/fws/office` — 이미
등록됨) 가 아홉 절 전부를 화면 문(대시보드 조회 · 기간·초소·근무표 저장 폼 ·
사건 번호 하나로 묶은 확인요청·확정/오인·접수·통보·배정·단계 제안 카드 6종)으로
잇는다. 지도·위치 렌더는 없다(좌표는 값으로만 — 헬기 도착예정·초소 위치도
문자열/숫자 그대로).

## 3. 「제목이 부르는 것 ↔ 있는 것」(P-376 · 절마다) — 요약

전체 표는 각 `docs/agent/evidence/SPEC/FWS-F3-0{1..9}.json` 의 `title_parts`
배열이 정본이다(빈 칸 0 · O 게이트가 다시 센다). 여기는 그중 **없는 것이 있는
한 줄**만 요약한다:

**FWS-F3-04** 탐지 확인 요청 1클릭 — 「가장 가까운 드론」 제안

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 1클릭 확인요청 발송 | 있음 — `notify_event` 재사용 |
| 10분 시계 | 있음 — `deadline_at`·`timeout_minutes=10` |
| 가장 가까운 감시원 제안 | 있음 — 오늘 체크인 위치와 사건 좌표의 하버사인 거리순 |
| 가장 가까운 드론 제안 | **없음** — 이 저장소에 드론이 0대다(P-387, 턴 AM 차선 N2 머리말). 위치 텔레메트리가 아예 없어 지어낼 수 없다(D-284). §5.3 표의 **완결조건은 "요청 발송 · 10분 시계"**이고(제목 괄호의 "가장 가까운"은 §6 FF-2 프로세스 표의 UX 힌트), FW-03 화면의 수용기준도 "1클릭 요청 · 회신 → 카드 상태"다 — 완결조건 기준으로 닫힌 절로 제안한다(F6-07 이 "실제 앱 푸시" 없이 PRD 대안으로 닫힌 것과 같은 판단). 드론 위치가 생기는 날(하드웨어 연동) 이 함수의 몸통만 넓히면 된다(계약은 그대로).

## 4. 시험 재실행 (조율자 창 ① 재확인용)

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n2 -w /app gx-shell \
  python -m pytest tests/test_fws_f3a.py -q -p no:randomly
# 21 passed
python scripts/verify_spec_fws_f3.py --no-run
# 닫은 열 9/9 · PASS
```
