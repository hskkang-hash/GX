# N2 승격 제안 — FWS-F1-01~15 (턴 AK · P-356·357·358 · 차선 N2)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다(작업지시 §하드룰).

## 0. 승격 규칙(P-356) 적용 요약

10건이 넷을 다 갖췄다고 이 차선이 주장한다:

1. **실제 구현** — `backend/apps/fws/*`(신규, Django 앱 아님 — DSM 과 같은 이유로
   `INSTALLED_APPS` 안 건드림) · 엔드포인트가 실제로 `backend/config/urls.py` 에
   `path("api/fws/", include("apps.fws.urls"))` 로 물려 있다.
2. **실측 증거** — `docs/agent/evidence/SPEC/<id>.json` 10건, 전부
   `backend/tests/test_fws_app.py` 의 pytest 실행이 **기계로** 찍었다
   (`measured_by: "django_test_client"`). 아래 표의 `measured_at` 은 이 보고를 쓰기
   직전 재실행한 시각이다(재실행하면 갱신된다 — 손으로 옮기지 않는다).
3. **게이트** — `scripts/verify_spec_fws.py`(`--self-test` 있음 · `TheSelfTestCanFail`
   짝은 `backend/tests/test_verify_spec_fws_gate_can_fail.py` · `scripts/_gate_header.py`
   의 `SELF_TEST_LINKS` 에 등재). `python scripts/verify_spec_fws.py` 전체 재실행 →
   **닫은 열 10/10 · PASS**(길목 시험 14 passed 포함 — `AppStaysThinTest` 1 +
   절별 시험 13).
4. **대장 이동** — 아래 §2 의 YAML 을 `ga_readiness.yaml` 의 `annex_2_spec.clauses`
   에서 area **"1" 기능 완결성**으로 옮기는 것을 제안한다.

⚠ **스키마 불확실 지점 하나 — 조율자 판단 필요.** area "1" 의 `kind_derived.closed`
리스트는 지금 전부 `docs/agent/evidence/D-309/contract_ac_ledger.yaml` 의 계약 절
id(`F-01-c2` 꼴)만 담고 있고, 그 파일 머리말은 "절을 여기 옮겨 적지 않는다 — 계약
절 대장이 원본"이라고 못박는다. `FWS-F1-01` 같은 별표 id 는 D-309 원장에 없는
id다. 두 갈래 중 하나를 조율자가 고르면 된다:

    (a) area "1" 에 **새 키**(예: `kind_derived.annex_promoted`)를 두어 별표 승격
        id 를 D-309 계약 절과 섞지 않는다 — 원장 정의(§머리말)를 그대로 지킨다.
    (b) `kind_derived.closed` 에 그대로 추가하고, D-309 원장에도 같은 id 로 대응
        행을 하나씩 더한다(원장이 원본이라는 규칙을 지키려면 원장도 같이 늘어야
        한다).

이 차선은 (a) 를 권한다 — 원장을 안 건드리고, 「별표 승격」이라는 사실 자체가
칸 이름에 남는다. 아래 YAML 은 (a) 모양으로 썼다. 조율자가 (b) 를 고르면
`kind_derived.closed` 로 옮기고 D-309 에도 행을 추가해야 한다.

## 1. 표 — 닫은 10건

| id | 제목 | 엔드포인트 | 증거 | 게이트 행 |
|---|---|---|---|---|
| FWS-F1-01 | 근무 시작·초소 체크인(NFC/GPS) | `POST /api/fws/patrol/checkin` | `evidence/SPEC/FWS-F1-01.json` | OK |
| FWS-F1-02 | 순찰 경로 기록(GPS 트랙·전자순찰함 NFC) | `POST /api/fws/patrol/track` | `evidence/SPEC/FWS-F1-02.json` | OK |
| FWS-F1-03 | 오늘 위험지수·위기경보·입산통제 확인 | `GET /api/fws/risk/today` | `evidence/SPEC/FWS-F1-03.json` | OK |
| FWS-F1-05 | 확인 요청 수신 | `GET /api/fws/verifications/{id}` | `evidence/SPEC/FWS-F1-05.json` | OK |
| FWS-F1-06 | 현장 확인 회신 | `POST /api/fws/verifications/{id}/reply` | `evidence/SPEC/FWS-F1-06.json` | OK |
| FWS-F1-08 | 119·산림청 신고 번호 버튼 | `GET /api/fws/emergency-contacts` | `evidence/SPEC/FWS-F1-08.json` | OK |
| FWS-F1-10 | 안전 알림 수신(도달·확인) | `GET /api/fws/alerts` · `POST /api/fws/alerts/{id}/ack` | `evidence/SPEC/FWS-F1-10.json` | OK |
| FWS-F1-11 | 내 근무 기록·순찰 실적(일·주) | `GET /api/fws/patrol/mine` | `evidence/SPEC/FWS-F1-11.json` | OK |
| FWS-F1-12 | 근무 외 알림 차단·담당 초소 설정 | `GET/POST /api/fws/notify-prefs` | `evidence/SPEC/FWS-F1-12.json` | OK |
| FWS-F1-13 | 오프라인 큐(복귀 시 전송 N) | `POST /api/fws/patrol/checkin`(Idempotency-Key 재전송) | `evidence/SPEC/FWS-F1-13.json` | OK |

프런트: 위 열 개 문 전부를 여는 화면 하나 — `frontend/src/features/fws/pages/
PatrolHome.tsx`(`/fws/home`). 카메라 사각·초동진화 등 나머지 화면은 아직 없다
(§3 참조).

## 2. 제안 YAML — area "1" 기능 완결성에 추가할 블록

```yaml
# docs/agent/evidence/D-346/ga_readiness.yaml :: areas[id=="1"] 안에 추가 제안
kind_derived:
  annex_promoted:
    # ★ P-356 로 승격된 별표 절. D-309 계약 절과 다른 칸에 둔다(머리말 참조).
    closed:
      - FWS-F1-01
      - FWS-F1-02
      - FWS-F1-03
      - FWS-F1-05
      - FWS-F1-06
      - FWS-F1-08
      - FWS-F1-10
      - FWS-F1-11
      - FWS-F1-12
      - FWS-F1-13

kind_evidence:
  FWS-F1-01:
    title: 근무 시작·초소 체크인(NFC/GPS)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-01.json
    rows: [tests.test_fws_app.F1_01_CheckinTest.test_checkin_sets_on_duty_status_with_location]
    strength: change
    measured_at: "2026-09-27T00:48:36Z"
    what: |
      POST /api/fws/patrol/checkin 뒤 응답 status=on_duty · location 이 요청 좌표
      그대로 실린다(django 테스트 클라이언트 실측).

  FWS-F1-02:
    title: 순찰 경로 기록(GPS 트랙 · 전자순찰함 NFC)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-02.json
    rows: [tests.test_fws_app.F1_02_TrackTest.test_gps_point_and_checkpoint_pass_are_counted_separately]
    strength: change
    measured_at: "2026-09-27T00:48:37Z"
    what: |
      GPS 점 1건과 순찰함 통과 1건이 track_count·checkpoint_count 로 갈려 나온다.

  FWS-F1-03:
    title: 오늘 위험지수·위기경보·입산통제 확인
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-03.json
    rows: [tests.test_fws_app.F1_03_RiskTodayTest.test_risk_band_has_the_contract_shape]
    strength: reflect
    measured_at: "2026-09-27T00:48:39Z"
    capture_none_why: |
      외부 산림청 위험예보 연동은 이번 턴 범위 밖(backend/apps/fws/risk.py 머리말에
      정직하게 남김) — 건기 달력 규칙으로 오늘의 띠를 계산한다. 계약(응답 모양)은
      연동이 들어와도 안 바뀐다.
    what: |
      GET /api/fws/risk/today 가 오늘 날짜 기준 level·fire_alert·mountain_entry_banned
      를 낸다.

  FWS-F1-05:
    title: 확인 요청 수신
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-05.json
    rows: [tests.test_fws_app.F1_05_06_VerificationTest.test_verification_detail_and_fire_confirmed_reply]
    strength: reflect
    measured_at: "2026-09-27T00:48:40Z"
    what: |
      K1 이벤트를 확인 요청으로 GET — 좌표·스냅샷 경로가 응답에 실린다(지도 렌더는
      금지구역 밖).

  FWS-F1-06:
    title: 현장 확인 회신
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-06.json
    rows: [tests.test_fws_app.F1_05_06_VerificationTest.test_verification_detail_and_fire_confirmed_reply,
          tests.test_fws_app.F1_05_06_VerificationTest.test_false_alarm_requires_one_of_five_reasons]
    strength: change
    measured_at: "2026-09-27T00:48:40Z"
    what: |
      현장 회신(산불 맞음/소각·오인 5택/접근 불가)이 K1 사건의 verdict 를 confirmed·
      rejected 로 바꾼다 — DSM K1 커널 공유(P-357).

  FWS-F1-08:
    title: 119·산림청 신고 번호 버튼
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-08.json
    rows: [tests.test_fws_app.F1_08_EmergencyContactsTest.test_numbers_come_from_the_server_not_the_screen]
    strength: reflect
    measured_at: "2026-09-27T00:48:41Z"
    what: |
      GET /api/fws/emergency-contacts(익명 허용)가 119·042-481-4119 를 낸다.

  FWS-F1-10:
    title: 안전 알림 수신(풍향 급변·대피 지시·철수)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-10.json
    rows: [tests.test_fws_app.F1_10_AlertsTest.test_alert_arrives_and_can_be_acknowledged]
    strength: change
    measured_at: "2026-09-27T00:48:42Z"
    what: |
      K2 send() 발송이 GET /api/fws/alerts(내 목록)에 도달로 나타나고, POST ack 로
      확인된다 — DSM K2 커널 공유(P-357).

  FWS-F1-11:
    title: 내 근무 기록·순찰 실적(일·주)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-11.json
    rows: [tests.test_fws_app.F1_11_PatrolMineTest.test_todays_checkin_and_track_are_counted]
    strength: reflect
    measured_at: "2026-09-27T00:48:44Z"
    what: |
      체크인 1·트랙 1 뒤 GET /api/fws/patrol/mine 의 today 칸이 1·1.

  FWS-F1-12:
    title: 근무 외 알림 차단·담당 초소 설정
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-12.json
    rows: [tests.test_fws_app.F1_12_NotifyPrefsTest.test_save_then_read_back]
    strength: change
    measured_at: "2026-09-27T00:48:45Z"
    what: |
      POST 로 저장한 방해 금지 시간대·담당 초소가 이후 GET 재조회에 그대로 보인다.

  FWS-F1-13:
    title: 오프라인 큐(산지 통신 불가 시 기록 저장 후 전송)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F1-13.json
    rows: [tests.test_fws_app.F1_13_OfflineReplayTest.test_replayed_checkin_with_same_key_is_not_double_counted]
    strength: change
    measured_at: "2026-09-27T00:48:46Z"
    capture_none_why: |
      프런트 오프라인 큐(frontend/src/features/fws/offlineQueue.ts)는 브라우저
      localStorage 를 쓴다 — Django 테스트 클라이언트로는 그 경로를 못 잰다. 이
      절이 실제로 재는 것은 **서버가 재전송 중복을 막는가**다(같은 Idempotency-Key
      로 두 번 보내도 patrol/mine.today.checkins 가 1 그대로).
    what: |
      같은 Idempotency-Key 로 체크인을 두 번 보내도(오프라인 큐 재전송을 흉내)
      근무 기록이 중복되지 않는다(common/idempotency.py 재사용 — 새 중복 제거
      기구를 만들지 않았다).
```

## 3. 못 닫은 다섯 — 「무엇이 없는가」

- **FWS-F1-04** 계도·단속 기록 — 위치·지도 화면이 필요하다. §0.4 인접 금지구역
  (`MapForRoute*`·`FormRoute.tsx`) 밖에서 좌표만 다루는 이번 차선 범위 밖으로
  작업지시가 명시적으로 넘겼다(04는 위치 · M 규모).
- **FWS-F1-07** 직접 신고(사진·GPS·화세·차량 진입 가능) — 사진 업로드 저장 경로가
  없다. M 규모라 이번 차선(S 10건 우선)의 시간 안에 못 붙였다.
- **FWS-F1-09** 초동진화 참여 회신(도착/진화 중/철수 3시각) — F1-06 과 다른
  상태기계가 필요한데 아직 없다. M 규모라 범위 밖.
- **FWS-F1-14** 카메라 사각 신고 — 신고를 받는 관리자 카드 소비 화면이 없다.
  M 규모라 범위 밖.
- **FWS-F1-15** 근무 종료·인계(특이사항 한 줄) — DSM `handover_service` 재사용
  여지는 확인했으나(코드 읽기만 했다 — 호출은 안 했다) 실제 엔드포인트를 아직
  안 열었다. M 규모라 범위 밖.

## 4. 분모 293 불변 확인 (P-356 ③)

이 문서는 `verify_spec_coverage.py` 를 재실행하지 않았다(annex_2_spec 은 이 차선이
못 건드리는 대장 파일 — 조율자가 §2 를 적용한 뒤 재실행해야 분모 293 이 그대로인지
확인된다). 승격 10건은 별표 목록(annex_2_spec.clauses)에서 **빠지고** area 1 로
**옮겨지므로**, 조율자가 옮긴 뒤 `python scripts/verify_spec_coverage.py --no-emit`
를 돌려 분모가 293 그대로인지 반드시 확인할 것 — 294 가 나오면 어딘가 중복 등재다
(P-356 ③ 규칙 그대로).
