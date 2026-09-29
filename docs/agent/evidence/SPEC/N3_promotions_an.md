# N3 승격 제안 — FWS-F3-10~20 산림과 담당 잔여(대피·상황보고·통계·오탐률·단속·훈련·온보딩)
(턴 AN · WO-GX-20260929-17 §5 P-356·392·397 · 차선 N3)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다.

P-397(세종 판정) — F1·F2·F5·F6 이 이미 연 문을 다시 열지 않는다. 이 차선이 새로
지은 것은 `backend/apps/fws/office2.py`·`api_office2.py`(신규 2파일)뿐이고, 사건에
관한 것은 전부 `apps.dsm.services`(F-05) 를 거친다. 새 DB 표는 **0개**다 —
`patrol.py`·`standby.py`·`equipment.py` 와 같은 감사 로그 한 줄 정본 판단을 그대로
따랐다.

## 0. 승격 규칙(P-356) 적용 요약

**닫은 아홉(F3-11·12·13·14·16·17·18·19·20)**이 넷을 다 갖췄다고 이 차선이 주장한다:

1. **실제 구현** — `backend/apps/fws/office2.py`(신규) · `backend/apps/fws/
   api_office2.py`(조율자가 세운 빈 컨트롤러에 이 차선이 라우트 18개를 더함,
   전부 `/api/fws/office2/...` 접두어 — 같은 턴 차선 N2 의 `api_office.py`
   (`/fws/...` 최상위 가지)와 겹치지 않게 애초에 다른 접두어를 골랐다). 새 App·
   새 이벤트 표는 만들지 않았다(P-357) — 이벤트 접근은 전부 `apps.dsm.services`
   를 거친다(F-05 잠금). 대피 문안은 F6-07(`integration.draft_evacuation_notice`)을
   그대로 부르고, 훈련은 F2-13(`training.py`)과 같은 판단으로 DSM 훈련 스위치
   (`set_drill_mode`/`drill_state`/`drill_report`)를 그대로 쓴다. 오탐 사유는
   F1-06(`verification.FALSE_ALARM_REASONS`)를 그대로 되짚는다.
2. **실측 증거** — `docs/agent/evidence/SPEC/FWS-F3-{11,12,13,14,16,17,18,19,20}.json`
   9건, 전부 `backend/tests/test_fws_f3b.py` 의 pytest 실행이 **기계로** 찍었다
   (`measured_by: "django_test_client"`). 이 턴(P-392)의 새 요구 — 증거마다
   `title_parts`(「제목이 부르는 것 ↔ 있는 것」 표 · 빈 칸 0)를 더 실었다. 공용
   `tests/test_fws_app.py::_write_evidence` 는 그 칸을 모르므로, 같은 모양 +
   `title_parts` 를 내는 `_write_evidence2` 를 `test_fws_f3b.py` 안에 두었다(공용
   파일을 고치지 않는다 · D-212 를 어기지 않는다 — 그 함수는 F6 게이트를 다시
   부르지 않는 새 파일이다).
3. **게이트** — 새 게이트 `scripts/verify_spec_fws_f3b.py`(`verify_spec_fws_f6.py`
   의 판정식을 그대로 베꼈다 · `--self-test` 있음 · title_parts 빈 칸 검사
   1행 추가). 재실행 → **닫은 열 9/9 · PASS**(길목 시험 10 passed).
4. **대장 이동** — 아래 §3 의 YAML 을 `ga_readiness.yaml` 의 `kind_derived.
   annex_promoted.closed`(N2 가 이미 연 그 자리)에 F3 9건을 이어 붙이는 것을
   제안한다.

## 1. 표 — 닫은 아홉 건

| id | 제목 | 엔드포인트 | 증거 |
|---|---|---|---|
| FWS-F3-11 | 대피 초안 — 대상 마을·대피소·문안(CBS 90/157자·마을방송문·앱 푸시) 자동 → F4 승인 요청 | `POST /api/fws/office2/evacuations/{id}/plan` | `evidence/SPEC/FWS-F3-11.json` |
| FWS-F3-12 | 대피 이행 확인(마을별 완료·잔류자·요양시설) | `POST .../evacuations/{id}/progress` · `GET .../evacuations/{id}/status` | `evidence/SPEC/FWS-F3-12.json` |
| FWS-F3-13 | 매시간 상황보고 초안 → 산림청 입력 항목 내보내기 | `POST/GET .../reports/{id}/hourly` | `evidence/SPEC/FWS-F3-13.json` |
| FWS-F3-14 | 진화완료 보고·산불 통계 항목(항목 1:1) | `POST/GET .../reports/{id}/final` | `evidence/SPEC/FWS-F3-14.json` |
| FWS-F3-16 | 통계 — 발생·면적·원인·시간대·구역·오인율·확인 시간·골든타임 준수율 | `GET .../stats/fires` | `evidence/SPEC/FWS-F3-16.json` |
| FWS-F3-17 | 카메라별 오탐률·임계값 시험(K6·QA-12) | `GET .../stats/camera-false-alarms` · `POST .../threshold-test` | `evidence/SPEC/FWS-F3-17.json` |
| FWS-F3-18 | 계도·단속 통계 · 입산통제구역 관리 | `POST .../patrol/enforcement` · `GET .../mine` · `POST/GET .../entry-control-zones` | `evidence/SPEC/FWS-F3-18.json` |
| FWS-F3-19 | 훈련 시나리오 실행(가상 사건 · 실채널 0) | `POST .../drill/start` · `GET .../drill/status` · `POST .../drill/end` | `evidence/SPEC/FWS-F3-19.json` |
| FWS-F3-20 | 온보딩 카드 7(조심기간 전) | `GET .../onboarding/progress` | `evidence/SPEC/FWS-F3-20.json` |

프런트: `frontend/src/features/fws/pages/OfficeReport.tsx`(`/fws/office/report` ·
조율자가 세운 빈 화면에 이 차선이 채움) · `frontend/src/features/fws/copy_office2.ts`
(이 차선 소유 신규 사전 · 공용 `copy.ts` 는 고치지 않았다). 서버 호출은 기존
`features/fws/api.ts` 의 `fwsGet`/`fwsPostQuery` 함수만 썼다(그 파일은 고치지
않았다) — 경로 문자열은 화면이 직접 든다.

## 2. 「제목이 부르는 것 ↔ 있는 것」 (절마다 요약 — 전체 표는 각 evidence json 의 `title_parts`)

**FWS-F3-11** 대피 초안

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 대상 마을·대피소 | 있음 — `villages_json` 목록(마을 최대 20곳), 응답 `drafts[].village/shelter` |
| 문안(CBS 90/157자) | 있음 — F6-07(`integration.draft_evacuation_notice`) 재사용, 상한 실측 |
| 마을방송문 | F6-07 대안 그대로(annex 가 CBS 문안과 마을방송문을 같은 문안으로 대안 처리) — 별도 필드 없음 |
| 앱 푸시 | **없음** — F6-07 이 이미 [미확인]으로 남긴 것을 그대로 물려받는다(외부 자격증명 필요) |
| F4 승인 요청 | 있음 — 응답 `status=pending_f4_approval` |

**FWS-F3-13** 매시간 상황보고 초안

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 발생·위치·진화 현황·인력/장비·인명·시설·기상 | 있음 — K1 이벤트 + 요청값 그대로 |
| 면적 | **없음(진행 중 사건)** — 진행 중 사건의 면적은 F3-14 최종 실측 전까지 측정값이 없다(D-284, 지어내지 않는다) |
| 산림청 입력 항목 내보내기 | 있음 — F6-01(`integration.export_kfs_feed`) 재사용 |

**FWS-F3-16** 통계

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 발생·면적·원인·시간대·구역·오인율·확인 시간 | 있음 — K1 이벤트 집계 + F3-14 최종보고 되짚기 |
| 골든타임 준수율 | **근사** — 실제 헬기 투하·지상 도달(30분) 시각을 이 앱이 갖고 있지 않다(그 시각을 쥔 커널의 공개 문 `apps.dsm.services.response_latency` 는 분포(p50/p95)만 내고 사건별 원값을 안 낸다). 확인 회신(occurred_at→reviewed_at) 30분 이내 비율로 근사하고, 응답 `golden_time_note` 에 그 사실을 그대로 적는다 |

**FWS-F3-18** 계도·단속 통계 · 입산통제구역 관리

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 계도·단속 통계 | 있음(본인 기록만) — 감사 표에 테넌트 칸이 없어(`patrol.py`·`equipment.py` 와 같은 한계) 조직 전체 집계는 범위 밖 |
| 입산통제구역 관리 | 있음(본인이 설정한 구역만) — 설정→조회 실측 |

나머지 다섯 절(F3-12·14·17·19·20)은 제목이 부르는 것이 그대로 있다 — 완결조건을
넘는 항목은 없다.

## 3. 제안 YAML — `kind_derived.annex_promoted.closed` 에 F3 9건 이어 붙이기

```yaml
# docs/agent/evidence/D-346/ga_readiness.yaml :: areas[id=="1"].kind_derived.annex_promoted 안에 추가 제안
kind_derived:
  annex_promoted:
    closed:
      # (N2 의 F3-01~09 · 다른 차선 몫은 그대로 두고, 아래 F3 9건을 이어 붙인다)
      - FWS-F3-11
      - FWS-F3-12
      - FWS-F3-13
      - FWS-F3-14
      - FWS-F3-16
      - FWS-F3-17
      - FWS-F3-18
      - FWS-F3-19
      - FWS-F3-20

kind_evidence:
  FWS-F3-11:
    title: 대피 초안 — 대상 마을·대피소·문안(CBS 90/157자·마을방송문·앱 푸시) 자동 → F4 승인 요청
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-11.json
    rows: [tests.test_fws_f3b.F3_11_EvacuationPlanTest.test_plan_drafts_cbs_text_per_village_and_waits_for_f4_approval]
    strength: reflect
    measured_at: "2026-09-29T03:10:00Z"
    capture_none_why: |
      앱 푸시(산림청 스마트산림재난 앱)는 F6-07 이 이미 [미확인]으로 남긴 것을
      그대로 물려받는다 — 외부 자격증명이 필요해 범위 밖.
    what: |
      마을 2곳 각각의 CBS 문안(90/157자 상한 · 8시간 지시 대피)이 생기고
      status=pending_f4_approval 로 F4 승인을 기다린다.

  FWS-F3-12:
    title: 대피 이행 확인(마을별 완료·잔류자·요양시설)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-12.json
    rows: [tests.test_fws_f3b.F3_12_EvacuationProgressTest.test_progress_then_status_shows_percent_and_remaining]
    strength: change
    measured_at: "2026-09-29T03:10:00Z"
    what: |
      대피 이행 기록 2건(완료 1 · 미완료 1) 뒤 이행 50.0% · 잔류자 3 · 요양시설
      미해제 1건이 그대로 남는다.

  FWS-F3-13:
    title: 매시간 상황보고 초안 → 산림청 입력 항목 내보내기
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-13.json
    rows: [tests.test_fws_f3b.F3_13_HourlyReportTest.test_draft_then_export_and_list]
    strength: change
    measured_at: "2026-09-29T03:10:00Z"
    capture_none_why: |
      진행 중 사건의 면적은 F3-14 최종 실측 전까지 측정값이 없다 — 정직하게
      비운다(D-284).
    what: |
      초안 항목(인력·장비·인명·시설·기상)과 F6-01 내보내기(kfs_export.fields)가
      한 응답에 실린다.

  FWS-F3-14:
    title: 진화완료 보고·산불 통계 항목(산불정보ID·원인·면적·문자전송 여부·일출몰)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-14.json
    rows: [tests.test_fws_f3b.F3_14_FinalReportTest.test_record_final_report_maps_items_one_to_one]
    strength: change
    measured_at: "2026-09-29T03:10:00Z"
    what: |
      6항목(산불정보ID·원인·면적·문자전송 여부·일출·일몰)이 1:1로 실리고, 재조회에도
      그대로 남는다.

  FWS-F3-16:
    title: 통계 — 발생·면적·원인·시간대·구역·오인율·확인 시간·골든타임 준수율
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-16.json
    rows: [tests.test_fws_f3b.F3_16_FireStatsTest.test_stats_covers_all_eight_parts]
    strength: reflect
    measured_at: "2026-09-29T03:10:00Z"
    capture_none_why: |
      골든타임 준수율은 근사치다 — 실제 헬기 투하·지상 도달 시각을 이 앱이 갖고
      있지 않아 확인 회신 시각(30분)으로 근사하고, 응답에 그 사실을 명시한다.
    what: |
      사건 2건(확정 1 · 오인 1) 뒤 여덟 칸(발생·면적·원인·시간대·구역·오인율·확인
      시간·골든타임 근사)이 전부 나온다.

  FWS-F3-17:
    title: 카메라별 오탐률(안개·소각 …)·임계값 시험(K6·QA-12)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-17.json
    rows: [tests.test_fws_f3b.F3_17_CameraFalseAlarmTest.test_rate_and_threshold_test]
    strength: change
    measured_at: "2026-09-29T03:10:00Z"
    what: |
      오인 판정 1건 뒤 카메라별 오탐률 100%·사유(안개) 집계, 임계값 50% 시험이
      fail 로 저장된다.

  FWS-F3-18:
    title: 계도·단속 통계 · 입산통제구역 관리
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-18.json
    rows: [tests.test_fws_f3b.F3_18_PatrolEnforcementTest.test_record_stats_and_zone_management]
    strength: change
    measured_at: "2026-09-29T03:10:00Z"
    capture_none_why: |
      감사 표에 테넌트 칸이 없어(§0.4 dj-core 소유) 본인이 남긴 기록만 센다 —
      조직 전체 집계는 범위 밖(patrol.py·equipment.py 와 같은 한계).
    what: |
      계도 기록 1건 → 통계 집계, 입산통제구역 설정 1건 → 재조회.

  FWS-F3-19:
    title: 훈련 시나리오 실행(가상 사건 · 실채널 0)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-19.json
    rows: [tests.test_fws_f3b.F3_19_DrillScenarioTest.test_start_status_end_real_channel_zero]
    strength: reflect
    measured_at: "2026-09-29T03:10:00Z"
    what: |
      훈련 시작→상태 확인→종료 보고서에서 real_channel_sends=0 이 실측된다(DSM
      훈련 스위치 재사용).

  FWS-F3-20:
    title: 온보딩 카드 7(조심기간 전)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f3b.py
    proof: docs/agent/evidence/SPEC/FWS-F3-20.json
    rows: [tests.test_fws_f3b.F3_20_OnboardingCardsTest.test_seven_cards_close_to_100_percent]
    strength: change
    measured_at: "2026-09-29T03:10:00Z"
    what: |
      F3 카드 7개에 해당하는 문을 전부 두드린 뒤 done=7·percent=100.0.
```

## 4. 못 닫은 둘 — 「무엇이 없는가」(P-358)

- **FWS-F3-10** 확산예측 결과 등록 · 화선 도달 예상 시각 마을별 — 풍향장·지형·
  연료(임상)를 쓰는 확산예측 모델이나 그 결과를 낼 산림과학원 외부 API 가 이
  차선에 없다. annex 가 스스로 허락한 대안(「업로드」)도 짓지 않았다 — 업로드
  결과(폴리곤·좌표)를 화면에 놓으려면 좌표 목록이 아니라 지도 오버레이·마을별
  화선 도달 예상 시각 계산이 필요한데, 지도 렌더는 §0.4 인접(`MapForRoute*`·
  `FormRoute.tsx` 금지구역)이라 이번 차선이 손대지 않는다. L 규모.
- **FWS-F3-15** 조사반 배정·조사 대장(원인·감식·경찰 합동·피해면적 드론 산출) —
  조사반 배정 기록 자체는 지을 수 있었으나, 완결조건이 요구하는 「대장 1」의
  핵심인 **드론 정사영상 폴리곤 피해면적 산출**은 F5 의 열점·화선 좌표 기록
  (`drone.py::submit_hotspots`)과는 다른 일이다 — 좌표 목록을 받는 것이 아니라
  그것으로부터 넓이를 셈하는 새 계산이고, 이 차선이 손에 넣은 산식·검증 표본이
  없다(지어내면 D-284 위반). L 규모 · 조율자 지시대로 「하지 않음」 후보로 남긴다.

## 5. 게이트·시험 재실행 결과

`python scripts/verify_spec_fws_f3b.py --no-run`(신규 게이트 · `--self-test` 통과
17/17) → **닫은 열 9/9 · PASS**.

gx-shell 안에서 확인한 pytest 실측(DB `test_gx_lane_n3`, `--create-db -p no:randomly`):

    tests/test_fws_f3b.py    10 passed in 247.81s (0:04:07)

## 6. F-05 잠금·계층 확인

- `kernels.k1_event` 를 `apps/fws/office2.py` 가 직접 import 하지 않는다(grep
  확인 · 이 파일에 그 이름이 없다) — 이벤트 접근은 전부 `apps.dsm.services.
  event_detail`/`recent_events`/`review_event`(시험 픽스처 안에서만 · 직접
  판정은 F1 문)/`drill_state`/`set_drill_mode`/`drill_report` 를 거친다.
- `AppStaysThinTest`(`tests/test_fws_app.py`) 는 `apps.fws.api` 만 본다 — 이
  차선은 그 파일을 건드리지 않았다. `api_office2.py` 는 조율자가 세운 컨트롤러
  껍데기에 라우트만 더했고, 저장·집계는 전부 `office2.py`(감사 로그·
  `apps.dsm.services` 재사용)에 있다.
- 새 DB 표 0개 — 마이그레이션 파일도 0개.
