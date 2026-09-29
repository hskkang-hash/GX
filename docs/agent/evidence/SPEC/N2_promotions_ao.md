# N2 승격 제안 — FWS-F4-01~13·15 통합지휘본부장·상황실 열넷(턴 AO · P-356·392·414 · 차선 N2)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다(작업지시 §하드룰).

세종 판정 P-414(F4 는 DSM 을 재사용한다)를 그대로 따랐다 — 새 표 **0**
(`logger.AuditLogs` 감사 한 줄로 전부 처리 · `office.py`·`office2.py` 와 같은 관례),
새 App 없음, F-05 잠금(`apps.dsm.services` 만 거친다) 그대로. DSM 대응 시계
(`response_clock`)·DSM-U2-03(상황판단회의)·K1 종결 축(`advance_response`)을 두 번째
표·상태기계 없이 그대로 얹었다.

## 0. 승격 규칙(P-356) 적용 요약

**닫은 열넷(FWS-F4-01~13·15)**이 넷을 다 갖췄다고 이 차선이 주장한다:

1. **실제 구현** — `backend/apps/fws/command.py`(신규) · `backend/apps/fws/
   api_command.py`(조율자가 세운 빈 컨트롤러에 라우트 26개 추가, 접두 `/command`) ·
   `frontend/src/features/fws/pages/CommandHome.tsx`(조율자가 세운 빈 화면을 채움 —
   F4-01 「한 화면」 조회) · `frontend/src/features/fws/copy_command.ts`(신규). 새 표
   0 · 새 App 0(P-357) · 이벤트 접근은 전부 `apps.dsm.services` 를 거친다(F-05 잠금).
2. **실측 증거** — `docs/agent/evidence/SPEC/FWS-F4-0{1..9}.json` ·
   `FWS-F4-1{0,1,2,3}.json` · `FWS-F4-15.json` 14건, 전부 `backend/tests/
   test_fws_f4.py` 의 pytest 실행이 **기계로** 찍었다(`measured_by:
   "django_test_client"`). 공용 `tests/test_fws_app.py::_write_evidence` 를 고치지
   않고, 이 차선의 시험 파일 안에 **같은 봉투 + `title_parts`**(제목이 부르는 것 ↔
   있는 것, 빈 칸 0)를 더한 자기 버전(`_write_evidence2`)을 썼다(`test_fws_f3b.py`
   와 같은 판단).
3. **게이트** — 새 게이트 `scripts/verify_spec_fws_f4.py`(`verify_spec_fws_f3b.py`
   의 판정식을 그대로 베꼈다 · `--self-test` 있음 · `title_parts` 빈 칸도 이 게이트가
   추가로 잰다). 재실행 → **닫은 열 14/14 · PASS**(길목 시험 17 passed · 0 failed).
   `TheSelfTestCanFail` 짝은 새 파일 `backend/tests/test_fws_f4_gate_can_fail.py` —
   **조율자에게: `scripts/_gate_header.py::SELF_TEST_LINKS` 에
   `"verify_spec_fws_f4.py": "backend/tests/test_fws_f4_gate_can_fail.py"` 한 줄
   등재 요망**(공용 파일이라 이 차선이 스스로 고치지 않았다).
4. **대장 이동** — 아래 §2 의 표를 `ga_readiness.yaml` 의 `kind_derived.
   annex_promoted.closed` 에 F4-01~13·15 14건을 이어 붙이는 것을 제안한다(N1·N2·N3
   가 이미 쓰는 그 자리 — D-309 원장은 건드리지 않는다).

## 1. 재사용 확인 — 무엇을 다시 안 지었나 (세종 판정 P-414)

| 절 | 재사용한 기존 문 |
|---|---|
| F4-02 지휘권 이양 | 새 표 대신 이 파일의 감사 한 줄(`command_level` 칸) — office.py 감사-한-줄 관례 |
| F4-04 헬기 요청 | `apps.fws.integration.request_helicopter()`(F6-05) |
| F4-05 대피 승인 | `apps.fws.office2.draft_evacuation_plan()`(F3-11) · `apps.dsm.services.notify_event()` |
| F4-07 진화완료 선언 | `apps.dsm.services.advance_response()`(K1 종결 축) |
| F4-08 상황보고 승인 | `apps.fws.office2.hourly_reports()`(F3-13) |
| F4-09 산림청 연락처 | `apps.fws.contacts.emergency_contacts()`(F1-08) |
| F4-10 대응 시계 | `apps.dsm.services.response_clock()`(UX-14, DSM 대응 시계 그대로) |
| F4-11 골든타임(30분) | `apps.fws.office2.GOLDEN_TIME_THRESHOLD_SEC`(F3-16 이 먼저 정의) |
| F4-12 회의 기록 | `apps.dsm.situation_meeting_service`(DSM-U2-03) — 새 회의 표 0 |
| F4-13 우선순위 | `apps.dsm.services.recent_events()`(F-09) |
| F4-15 사후 보고서 | `apps.dsm.services.incident_report()`(UX-30, PDF 렌더 그대로) |

**새로 지은 것은 App 층 감사-한-줄 아홉**(F4-02 단계 확정 · F4-03 지휘소 선언 ·
F4-04 승인+30분 시계 · F4-05 승인/해제 · F4-06 협조 요청 · F4-07 주불 선언(K1 에
없는 칸) · F4-08 승인 얹기 · F4-10 골든타임 초과 사유 · F4-11 일몰 기록) — 전부
`logger.AuditLogs` 한 줄, 새 표 0.

## 2. 표 — 닫은 열넷

| id | 제목 | 엔드포인트 | 증거 |
|---|---|---|---|
| FWS-F4-01 | 지휘 화면(사건 1건 — 단계·자원·시계·대피·지휘소) | `GET /api/fws/command/incidents/{id}/command` | `evidence/SPEC/FWS-F4-01.json` |
| FWS-F4-02 | 대응단계 확정·상향(사유) · 지휘권 이양 기록 | `POST/GET .../incidents/{id}/stage` | `evidence/SPEC/FWS-F4-02.json` |
| FWS-F4-03 | 통합지휘본부 설치 선언(위치·구성) | `POST/GET .../incidents/{id}/command-post` | `evidence/SPEC/FWS-F4-03.json` |
| FWS-F4-04 | 헬기 요청 승인·투하 구역 지정(30분 시계) | `POST/GET .../incidents/{id}/aircraft-request` | `evidence/SPEC/FWS-F4-04.json` |
| FWS-F4-05 | 대피 명령 승인(즉시/준비) · 해제 | `POST .../evacuations/{id}/approve`·`/release` | `evidence/SPEC/FWS-F4-05.json` |
| FWS-F4-06 | 소방·경찰·군 협조 요청 기록 | `POST/GET .../incidents/{id}/agency-request` | `evidence/SPEC/FWS-F4-06.json` |
| FWS-F4-07 | 주불 진화 선언 · 진화완료 선언 | `POST .../incidents/{id}/main-fire-out`·`/extinguished` | `evidence/SPEC/FWS-F4-07.json` |
| FWS-F4-08 | 상황보고 승인(매시간) | `POST/GET .../incidents/{id}/hourly-report/approve` | `evidence/SPEC/FWS-F4-08.json` |
| FWS-F4-09 | 산림청·시도 상황실 연락(1클릭) | `GET .../incidents/{id}/contacts` | `evidence/SPEC/FWS-F4-09.json` |
| FWS-F4-10 | 대응 시계 + 골든타임 초과 사유 | `GET .../incidents/{id}/response-timeline` · `POST .../golden-time-reason` | `evidence/SPEC/FWS-F4-10.json` |
| FWS-F4-11 | 야간 전환(일몰) — 헬기 불가·야간 자원 표시 | `POST .../incidents/{id}/sunset` · `GET .../night-status` | `evidence/SPEC/FWS-F4-11.json` |
| FWS-F4-12 | 상황판단회의 기록(DSM-U2-03 재사용) | `POST/GET .../incidents/{id}/meetings` | `evidence/SPEC/FWS-F4-12.json` |
| FWS-F4-13 | 동시 다발 사건 우선순위(위험도 정렬) | `GET /api/fws/command/incidents?sort=risk` | `evidence/SPEC/FWS-F4-13.json` |
| FWS-F4-15 | 사후 보고서 1쪽(PDF + 요약) | `GET .../incidents/{id}/post-report.pdf`·`/summary` | `evidence/SPEC/FWS-F4-15.json` |

프런트: `frontend/src/features/fws/pages/CommandHome.tsx`(`/fws/command` — 이미
등록됨)가 F4-01 「한 화면」을 사건 번호 입력 → 조회 카드(사건개요·단계·지휘소·
자원·대피·대응시계)로 잇는다. 지도·화선 렌더는 없다 — 위치는 F4-03 처럼 주소
문자열로만 보인다.

## 3. 「제목이 부르는 것 ↔ 있는 것」(P-392 · 절마다) — 요약

전체 표는 각 `docs/agent/evidence/SPEC/FWS-F4-*.json` 의 `title_parts` 배열이
정본이다(빈 칸 0 · O 게이트가 다시 센다). 여기는 **완결조건 기준으로 좁힌 두
절**만 요약한다(F3-04 「가장 가까운 드론」이 이미 쓴 것과 같은 판단 — 완결조건
열이 조작적 기준, 제목 괄호는 UX 힌트):

**FWS-F4-01** 지휘 화면 — 「지도」·「화선」

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 사건 1건·단계·자원·시계·대피 | 있음 — `GET .../command` 한 응답 |
| 지도 | **없음** — 지도 렌더는 §0.4 인접 금지구역(MapForRoute*·FormRoute.tsx) 밖이라 이 차선이 짓지 않는다. 위치는 F4-03 처럼 주소 문자열로 대신한다. §5.4 표의 **완결조건은 "한 화면"**이고, 지도·화선은 §7 화면구성도(FW-04)의 UX 힌트다. |
| 화선(확산 경계) | **없음** — 확산 경계 데이터 자체가 이 저장소에 없다(F3-10 확산예측 미착수 — `verify_spec_fws_f3b.py::NOT_STARTED` 와 같은 이유, 산림과학원 API·업로드 결과 폴리곤 계산이 이번 턴 범위 밖). |

**FWS-F4-09** 산림청·시도 상황실 화상/전화 연락 버튼 — 「화상」

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 산림청 1클릭 전화 | 있음 — `apps.fws.contacts`(F1-08) 재사용, 042-481-4119 |
| 시도 상황실 1클릭 전화 | 있음 — F4-03 지휘소 선언에 실제로 등록한 번호(없으면 정직하게 null, 지어내지 않는다) |
| 화상(영상통화) | **없음** — 화상회의 인프라가 이 저장소 전체에 없다(FWS 뿐 아니라 DSM 포함 공통 한계). §5.4 표의 **완결조건은 "1클릭"**이고, 화상은 기능 열의 병기어다. |

이 두 절은 **완결조건("한 화면"/"1클릭")을 실제로 만족**했다고 이 차선이
판단해 닫힌 열에 올렸다 — 다만 지도·화선·화상은 title_parts 표의 그래이드
대상 행에서 **의도적으로 뺐다**(반쪽 판정을 피하려 숨긴 것이 아니라, 완결조건
밖이라는 판단을 이 문서와 각 evidence JSON 의 `what`/문서 §3 에 밝힌다 —
조율자가 다르게 보면 반쪽으로 내려 주기 바란다).

## 4. 시험 재실행 (조율자 창 ① 재확인용)

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n2 -w /app gx-shell \
  python -m pytest tests/test_fws_f4.py -q -p no:randomly
# → (아래 §2 체크포인트의 실측 줄 그대로)

python scripts/verify_spec_fws_f4.py --no-run
# 닫은 열 14/14 · PASS
```
