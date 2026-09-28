# N2 승격 제안 — FWS-F1-01~15 · FWS-F2-01~15 · FWS-F5-01~10 (턴 AK·AL·AM · P-356·357·358·387 · 차선 N2)

**턴 AL 추가분은 §5~§9, 턴 AM(F5 드론 운용자) 추가분은 §10 이하** — §0~§4(F1 10건 ·
분모 293 확인)는 턴 AK 그대로 남긴다(이미 조율자가 검토했을 수 있는 문서를 손대지
않는다). F2·F5 는 각각 별도 절로 붙인다.

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

---

## 5. F2 산림재난대응단·진화대 — 승격 규칙(P-356) 적용 요약 (턴 AL)

「임무」는 새 표가 아니다 — F1 의 「확인 요청」과 같은 판단으로 K1 이벤트를
진화대 쪽에서 본 것이다(`backend/apps/fws/missions.py` 머리말 · P-357). 대응
진행(출동·도착·철수)은 K1 이 이미 가진 4값 표(`occurred → acknowledged →
in_progress → closed`, `kernels/k1_event/response_flow.py`)를 **그대로** 빌린다
— 3번째 상태기계를 세우지 않았다(D-212).

10건이 넷을 다 갖췄다고 이 차선이 주장한다:

1. **실제 구현** — `backend/apps/fws/{missions,standby,equipment,training}.py`
   (신규 4파일, 여전히 Django 앱 아님) · `backend/apps/fws/api.py` 에 라우트
   추가 · `backend/config/urls.py` 는 이미 턴 AK 가 물렸다(고치지 않음).
2. **실측 증거** — `docs/agent/evidence/SPEC/<id>.json` 10건, 전부
   `backend/tests/test_fws_f2.py` 의 pytest 실행이 **기계로** 찍었다
   (`measured_by: "django_test_client"`, `test_fws_app._write_evidence` 재사용 —
   두 벌을 만들지 않는다).
3. **게이트** — `scripts/verify_spec_fws.py` 를 F2 열 10건으로 확장했다(길목
   시험이 이제 `test_fws_app.py` + `test_fws_f2.py` 둘을 같이 돈다). 재실행 →
   **닫은 열 20/20 · PASS**(길목 시험 90 passed 포함 — F1 14 + F2 14 + 그 밖의
   락 시험은 별도로 `tests/test_f05_event_api.py`·`tests/test_dsm_app.py` 를
   함께 돌려 76 passed 로 확인).
4. **대장 이동** — 아래 §6 의 YAML 을 `ga_readiness.yaml` 의 `kind_derived.
   annex_promoted.closed`(턴 AK 가 이미 연 그 자리)에 F2 10건을 이어 붙이는
   것을 제안한다. §0 의 (a) 판단(별표 승격은 새 키 하나로 모은다)을 그대로
   따른다 — 이번에도 D-309 원장은 건드리지 않는다.

## 6. 표 — 닫은 F2 10건

| id | 제목 | 엔드포인트 | 증거 | 게이트 행 |
|---|---|---|---|---|
| FWS-F2-01 | 대기 상태 등록(주간·야간 5분대기조·위치) | `POST/GET /api/fws/resources/me/status` | `evidence/SPEC/FWS-F2-01.json` | OK |
| FWS-F2-02 | 임무 수신(출동 지시) | `GET /api/fws/missions/{id}` · `POST …/response`(action=dispatch) | `evidence/SPEC/FWS-F2-02.json` | OK |
| FWS-F2-03 | 이동·도착 회신(GPS) | `POST /api/fws/missions/{id}/response`(action=arrived) | `evidence/SPEC/FWS-F2-03.json` | OK |
| FWS-F2-05 | 지원 요청(인력·물·헬기·중장비) | `POST /api/fws/missions/{id}/field-reply` | `evidence/SPEC/FWS-F2-05.json` | OK |
| FWS-F2-07 | 안전 경보 수신(풍향 급변·헬기 투하 구역 이탈) | `GET /api/fws/alerts` · `POST /api/fws/alerts/{id}/ack`(F1-10 문 재사용) | `evidence/SPEC/FWS-F2-07.json` | OK |
| FWS-F2-11 | 철수·복귀 회신 | `POST /api/fws/missions/{id}/response`(action=released) | `evidence/SPEC/FWS-F2-11.json` | OK |
| FWS-F2-12 | 내 임무 이력·투입 시간(수당 근거) | `GET /api/fws/missions/mine` | `evidence/SPEC/FWS-F2-12.json` | OK |
| FWS-F2-13 | 훈련 임무 수신(훈련 배지) | `GET /api/fws/training/mission` | `evidence/SPEC/FWS-F2-13.json` | OK |
| FWS-F2-14 | 장비 점검 체크(등짐펌프·진화차) | `POST /api/fws/equipment/checks` · `GET …/mine` | `evidence/SPEC/FWS-F2-14.json` | OK |
| FWS-F2-15 | 근무 외 차단·담당 구역 | `GET/POST /api/fws/notify-prefs`(F1-12 문 재사용) | `evidence/SPEC/FWS-F2-15.json` | OK |

프런트: 위 열 개 문을 여는 새 화면 — `frontend/src/features/fws/pages/
FieldHome.tsx`(`/fws/field`, FM3) — F1 의 `/fws/home` 과 형제 가지(둘 다 최상위
리터럴이라 서로 안 삼킨다). F2-07·F2-15 는 **이 화면에서도 새 위젯을 만들지
않았다** — 문이 F1 것 그대로이므로, 그 값을 읽는 화면도 이미 `PatrolHome.tsx`
(F1-10)·기존 `/notify-prefs` 소비처가 있다. `FieldHome.tsx` 는 F2 고유 절(01·
02·03·05·11·12·13·14)의 진입면만 새로 연다.

⚠ **정직하게 남기는 한계 둘**(missions.py 머리말에 상술):
- `mission_detail`(F2-02)이 내는 것은 K1 `EventView` 가 가진 칸뿐이다 — 명세서
  원문의 접근로·풍향·집결지·지휘자는 K1 스키마에 없어 `null` 로 낸다(지어내지
  않는다, D-284). 그 넷을 채우려면 커널 변경이 필요하고 이 차선(App 층) 권한
  밖이다.
- 대응 진행(`response_state`)은 **사건 전체의 칸**이다 — 한 진화대의 「철수」가
  사건을 `closed` 로 옮기면, 아직 현장에 남은 다른 진화대의 진행도 함께 닫힌
  것처럼 보인다. 이번 턴 범위(첫 고객 1곳 규모)에서는 사건당 진화대가 사실상
  하나로 취급되고, 다중 대응팀 분리 배정(새 축)이 생기기 전까지 이 한계가
  남는다.

## 7. 제안 YAML — `kind_derived.annex_promoted.closed` 에 F2 10건 이어 붙이기

```yaml
# docs/agent/evidence/D-346/ga_readiness.yaml :: areas[id=="1"].kind_derived.annex_promoted 안에 추가 제안
kind_derived:
  annex_promoted:
    closed:
      # (턴 AK 가 이미 넣은 F1 10건은 그대로 두고, 아래 F2 10건을 이어 붙인다)
      - FWS-F2-01
      - FWS-F2-02
      - FWS-F2-03
      - FWS-F2-05
      - FWS-F2-07
      - FWS-F2-11
      - FWS-F2-12
      - FWS-F2-13
      - FWS-F2-14
      - FWS-F2-15

kind_evidence:
  FWS-F2-01:
    title: 대기 상태 등록(주간·야간 5분대기조·위치)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-01.json
    rows: [tests.test_fws_f2.F2_01_StandbyStatusTest.test_set_then_read_back_standby_status]
    strength: change
    measured_at: "2026-09-28T00:00:00Z"
    what: |
      POST /api/fws/resources/me/status(야간 5분대기조·위치) 뒤 GET 재조회에
      상태·좌표가 그대로 보인다(자원 배치판 표시는 F3 화면 소유라 범위 밖 —
      standby.py 머리말에 정직하게 남김).

  FWS-F2-02:
    title: 임무 수신(출동 지시)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-02.json
    rows: [tests.test_fws_f2.F2_02_03_11_MissionResponseTest.test_mission_detail_dispatch_arrive_release_chain]
    strength: reflect
    measured_at: "2026-09-28T00:00:00Z"
    capture_none_why: |
      접근로·풍향·집결지·지휘자는 K1 EventView 스키마에 없다 — null 로 낸다
      (missions.py 머리말). 채우려면 커널 변경이 필요해 이 차선 권한 밖이다.
    what: |
      K1 이벤트를 '임무'로 GET — 발화점 좌표·화세·시각·대응 진행이 응답에
      실린다. 「출동」1탭(action=dispatch)이 대응 진행을 acknowledged 로 옮긴다.

  FWS-F2-03:
    title: 이동·도착 회신(GPS)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-03.json
    rows: [tests.test_fws_f2.F2_02_03_11_MissionResponseTest.test_mission_detail_dispatch_arrive_release_chain]
    strength: change
    measured_at: "2026-09-28T00:00:00Z"
    what: |
      출동 탭 뒤 action=arrived 회신이 대응 진행을 in_progress 로 옮기고
      elapsed_minutes(30분 시계)를 함께 낸다 — K1 현장 회신에도 GPS 가 남는다.

  FWS-F2-05:
    title: 지원 요청(인력·물·헬기·중장비)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-05.json
    rows: [tests.test_fws_f2.F2_05_SupportRequestTest.test_support_request_reaches_field_reply]
    strength: reflect
    measured_at: "2026-09-28T00:00:00Z"
    capture_none_why: |
      지휘 화면의 새 배지 위젯은 DSM 화면(lane L) 소유라 만들지 않았다 — 값이
      도달하는 자리(K1 field_replies)까지만 이 차선의 범위다.
    what: |
      kind=helicopter 지원 요청이 K1 현장 회신으로 남고 field_replies 목록에
      그대로 도달한다(지휘 화면이 읽는 자리).

  FWS-F2-07:
    title: 안전 경보 수신(풍향 급변·헬기 투하 구역 이탈)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-07.json
    rows: [tests.test_fws_f2.F2_07_SafetyAlertTest.test_wind_shift_alert_arrives_and_acks_via_shared_alerts_endpoint]
    strength: reflect
    measured_at: "2026-09-28T00:00:00Z"
    what: |
      새 엔드포인트 없음 — F1-10 이 연 GET /alerts · POST /alerts/{id}/ack 를
      F2 안전 경보(풍향 급변 등)도 그대로 쓴다(K2 발송은 채널·내용을 안 가린다).

  FWS-F2-11:
    title: 철수·복귀 회신
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-11.json
    rows: [tests.test_fws_f2.F2_02_03_11_MissionResponseTest.test_mission_detail_dispatch_arrive_release_chain]
    strength: change
    measured_at: "2026-09-28T00:00:00Z"
    what: |
      action=released 회신이 대응 진행을 closed 로 옮기고(자원 배치판 해제와
      같은 뜻), 도착~철수 duration_minutes 를 함께 낸다.

  FWS-F2-12:
    title: 내 임무 이력·투입 시간(수당 근거)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-12.json
    rows: [tests.test_fws_f2.F2_12_MissionsMineTest.test_dispatch_arrive_release_are_counted_in_mine]
    strength: reflect
    measured_at: "2026-09-28T00:00:00Z"
    capture_none_why: |
      K1·K2 감사에는 테넌트 칸이 없어 사람별 전건 문지기가 없다 — missions.py
      가 자기 감사(guardianx.fws.mission)를 따로 쓴다(patrol.py 와 같은 관례).
    what: |
      출동→도착→철수 한 임무 뒤 GET /missions/mine 에 그 임무가 1건,
      duration_minutes 와 함께 잡힌다.

  FWS-F2-13:
    title: 훈련 임무 수신(훈련 배지)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-13.json
    rows: [tests.test_fws_f2.F2_13_TrainingBadgeTest.test_badge_and_zero_real_channel_when_drill_mode_is_on]
    strength: reflect
    measured_at: "2026-09-28T00:00:00Z"
    what: |
      훈련 모드가 켜진 테넌트에서 GET /training/mission 이 badge='훈련' ·
      real_channel_sends=0 을 낸다(DSM drill_state·drill_report 재사용 — 새
      스위치를 만들지 않았다).

  FWS-F2-14:
    title: 장비 점검 체크(등짐펌프·진화차)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-14.json
    rows: [tests.test_fws_f2.F2_14_EquipmentCheckTest.test_check_is_recorded_and_read_back]
    strength: change
    measured_at: "2026-09-28T00:00:00Z"
    what: |
      POST /equipment/checks(등짐펌프 BP-7 · pass) 뒤 GET /equipment/checks/mine
      의 count 가 1, 방금 남긴 장비 코드가 그대로 보인다 — 점검 1 실측.

  FWS-F2-15:
    title: 근무 외 차단·담당 구역
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F2-15.json
    rows: [tests.test_fws_f2.F2_15_OffDutyBlockTest.test_off_duty_block_and_assigned_zone_save_then_read_back]
    strength: reflect
    measured_at: "2026-09-28T00:00:00Z"
    what: |
      새 엔드포인트 없음 — F1-12 가 연 GET/POST /notify-prefs 를 F2 진화대도
      그대로 써서 근무 외 차단 시간대·담당 구역이 저장 → 재조회에 남는다.
```

## 8. 못 닫은 F2 다섯 — 「무엇이 없는가」

- **FWS-F2-04** 현장 상황 보고(화선 길이·방향·진화 가능 여부·사진) — 사진 업로드
  저장 경로가 없다(F1-07 과 같은 한계). M 규모라 범위 밖.
- **FWS-F2-06** 진화선 구축·구간 완료 보고 — 「구간」은 K1 에 없는 축(진화선을
  여러 구간으로 나눠 각각의 진행을 추적)이라 새 표가 필요하다. M 규모라
  범위 밖.
- **FWS-F2-08** 주불 진화 보고 — 완결조건이 'F4 승인'(다른 역할의 승인 절차)이고,
  그 승인 축은 K1 4값 대응 진행표에 없다. M 규모라 범위 밖.
- **FWS-F2-09** 잔불 정리 구역 배정·완료 — 「구역」별 배정·완료(N/N)를 담을 표가
  없다(F2-06 과 같은 한계 — 구간·구역 축). M 규모라 범위 밖.
- **FWS-F2-10** 뒷불 감시 교대·발견 보고(열점 위치) — 발견 보고가 「재발화 사건
  연결」을 요구해 새 이벤트 생성 경로가 필요하고, 위치·지도 인접 주의(F1-04와
  같은 한계)도 겹친다. M 규모라 범위 밖.

## 9. 분모 293 재확인 요청 (P-356 ③)

§4 와 같은 이유로 이 문서는 `verify_spec_coverage.py` 를 재실행하지 않았다. F2
10건이 별표 목록에서 **빠지고** area 1 로 **옮겨지므로**, 조율자가 §7 을 적용한
뒤 `python scripts/verify_spec_coverage.py --no-emit` 를 다시 돌려 분모가 293
그대로인지(F1·F2 승격 20건을 함께 옮긴 뒤 기준) 반드시 확인할 것.

---

## 10. F5 드론 운용자 — 세종 판정 P-387(요청·상태·결과 세 축뿐, 드론 0대) (턴 AM)

작업지시가 준 판정(P-387) 그대로다: 이 저장소에는 실제 드론이 **0대** 있다. 그래서
F5 열 다섯을 닫을 때 만든 것은 드론이 하는 일의 흉내가 아니라 **사람이 드론을
부리는 서류** 셋뿐이다 — 요청(F5-01) · 상태 전이(F5-01) · 결과 첨부(F5-03). 나머지
둘(F5-02 열점·화선 · F5-08 비행 기록·F5-10 계량)은 전부 **값**이고 지도·폴리라인·
실제 센서 데이터는 만들지 않았다(`backend/apps/fws/drone.py` 머리말 전문 참조).

★ **다중 행위자 규칙**(작업지시 「per-drone actions must not close the shared
incident」) — `recon()`·`confirm_result()` 는 `apps.dsm.services.advance_response`
를 **한 번도 부르지 않는다.** 이 규칙이 실제로 지켜지는지는
`test_recon_state_never_advances_shared_response_state` 가 사건의
`response_state` 가 정찰 상태 전이 뒤에도 `occurred` 그대로인지 재서 잡는다.

10건이 넷을 다 갖췄다고 이 차선이 주장하는 것은 **다섯 건뿐이다**(S 규모 셋
F5-02·03·08 우선 + 그 위에 자연히 붙는 F5-01·F5-10). 나머지 다섯(F5-04·05·06·
07·09)은 §13 에 「무엇이 없는가」로 남긴다.

1. **실제 구현** — `backend/apps/fws/drone.py`(신규) · `backend/apps/fws/api.py`
   에 `/api/fws/drone/*` 라우트 8개 추가(`missions/mine`·`missions/{id}/recon`·
   `missions/{id}/hotspots`·`missions/{id}/hotspots/mine`·
   `verifications/{id}/reply`·`flights`·`flights/mine`·`flights/minutes`).
2. **실측 증거** — `docs/agent/evidence/SPEC/<id>.json` 5건, 전부
   `backend/tests/test_fws_f5.py` 의 pytest 실행이 **기계로** 찍었다
   (`measured_by: "django_test_client"`, `test_fws_app._write_evidence` 재사용).
3. **게이트** — `scripts/verify_spec_fws.py` 를 F5 열 다섯 건으로 확장했다(길목
   시험이 이제 `test_fws_app.py` + `test_fws_f2.py` + `test_fws_f5.py` 셋을 같이
   돈다). `test_fws_f5.py` 단독 재실행 → **13 passed**(길목 확인). 전체 재실행은
   §12 참조.
4. **대장 이동** — 아래 §11 의 YAML 을 `ga_readiness.yaml` 의 `kind_derived.
   annex_promoted.closed`(턴 AK 가 이미 연 그 자리)에 F5 5건을 이어 붙이는 것을
   제안한다. §0 의 (a) 판단을 그대로 따른다 — D-309 원장은 건드리지 않는다.

## 11. 표 — 닫은 F5 다섯 건 + 「제목이 부르는 것 ↔ 있는 것」 (P-376)

| id | 제목 | 엔드포인트 | 증거 |
|---|---|---|---|
| FWS-F5-01 | 정찰 임무 수신(발화 추정 좌표·반경) → 열화상 정찰 | `POST /api/fws/drone/missions/{id}/recon`(action) · `GET .../drone/missions/mine` | `evidence/SPEC/FWS-F5-01.json` |
| FWS-F5-02 | 열점·화선 표시(열화상 프레임 → 지도 폴리라인) | `POST /api/fws/drone/missions/{id}/hotspots` · `GET …/hotspots/mine` | `evidence/SPEC/FWS-F5-02.json` |
| FWS-F5-03 | 확인 회신(산불 맞음/오인 · 사진·열화상) | `POST /api/fws/drone/verifications/{id}/reply` | `evidence/SPEC/FWS-F5-03.json` |
| FWS-F5-08 | 비행 기록·배터리·기체 상태 | `POST /api/fws/drone/flights` · `GET …/flights/mine` | `evidence/SPEC/FWS-F5-08.json` |
| FWS-F5-10 | 계량(비행 분) | `GET /api/fws/drone/flights/minutes` | `evidence/SPEC/FWS-F5-10.json` |

P-376 「반쪽은 닫힌 것이 아니다」 — 절마다 제목이 부르는 낱말과 실제로 있는 것을
가른다. 있는 열은 이 차선이 실측했고, 없는 열은 세종 판정 P-387 이 애초에 범위
밖으로 그은 것이지 빠뜨린 것이 아니다(드론 0대 — 실기체·실센서는 이 시스템의
소관이 아니다).

**FWS-F5-01** 정찰 임무 수신(발화 추정 좌표·반경) → 열화상 정찰

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 발화 추정 좌표 | 있음 — K1 이벤트 `lat`·`lng`(F1/F2 가 이미 쓰던 값, 새로 만들지 않음) |
| 반경 | 있음 — `radius_m` 값(요청 감사 한 줄에 저장 · K1 이벤트 스키마엔 없는 칸이라 이 파일에만 남음) |
| 수신(요청) | 있음 — `action=request` |
| 상태(수락→이륙→귀환) | 있음 — `action=accept/airborne/return`, 이 조종사 자신의 기록으로 순서 검사(앞 단계 없으면 409) |
| 열화상 정찰(실비행·센서 데이터) | **없음** — P-387: 드론 0대. 이 시스템이 내는 것은 「정찰 임무를 받았다·상태가 어디까지 갔다」는 서류뿐이고, 실제 비행·촬영(열화상 프레임 자체)은 시스템 밖(기체·사람)의 일이다 |

**FWS-F5-02** 열점·화선 표시(열화상 프레임 → 지도 폴리라인)

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 열점 위치(들) | 있음 — `points`(좌표 목록 값, JSON) |
| 화선(들) | 있음 — `fireline`(좌표 목록 값, 최소 2점) |
| 지휘 화면 도달 | 있음 — K1 `field_reply` 로 남아 사건 상세의 현장 회신 목록에 도달(지휘 화면은 DSM lane N1 소유라 새 위젯은 안 만듦) |
| 열화상 "프레임"(원본 이미지·센서 데이터) | **없음** — 좌표 값만 받는다. 프레임 자체(이미지 바이너리)는 저장하지 않는다(드론 0대, P-387) |
| 지도 폴리라인(렌더) | **없음(의도)** — §0.4 인접 금지구역(`MapForRoute*`) 밖. 좌표 목록 값만 값으로 내고, 그리는 것은 화면(다른 컴포넌트)의 몫으로 남긴다 |

**FWS-F5-03** 확인 회신(산불 맞음/오인 · 사진·열화상)

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 산불 맞음/오인(결과 판정) | 있음 — F1-06 `verification.reply_verification` 문을 그대로 재사용(RESULT 3택) |
| 사진·열화상(첨부) | 있음(값으로) — `attachment_ref`(경로/URL 문자열). 「산불 맞음」인데 첨부가 없으면 422(명세 원문 강제) |
| 사건 판정(verdict) 반영 | 있음 — K1 `review_event` 가 `confirmed`/`rejected` 로 바꾼다(F1-06 과 같은 문 · 대응 진행 `response_state` 는 안 건드림, 다중 행위자 규칙) |
| 실제 사진·열화상 파일(바이너리 업로드·저장) | **없음** — `attachment_ref` 는 **값**(문자열)만 받는다. 실제 업로드 저장 경로는 이번 차선 범위 밖(F1-07·F2-04 와 같은 한계) |

**FWS-F5-08** 비행 기록·배터리·기체 상태

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 비행 기록 | 있음 — `flight_minutes`·`source`·`note`, 저장 → 재조회(`flights/mine`) |
| 배터리 상태 | 있음 — `battery_pct`(0~100 범위 검증) |
| 기체 상태 | 있음 — `airframe_code`(값), `source`(DJI 등 연동 어댑터의 **이름 값 자리**뿐 — 실제 DJI API 호출 0건, P-387) |
| (없는 것) | 없음 — 제목이 부르는 세 값(기록·배터리·기체) 전부 값으로 있다. 제목이 실연동을 요구하지 않으므로 `source` 가 어댑터 자리인 것은 갭이 아니라 판정이 그은 선이다 |

**FWS-F5-10** 계량(비행 분)

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 비행 분 계량 | 있음 — `flight_minutes_total`(F5-08 값을 세기만 한다, 새 표 없음), 월 필터 가능 |
| (없는 것) | 없음 |

## 12. 게이트·전체 시험 재실행 결과

`python scripts/verify_spec_fws.py --run`(F5 5건 추가 · `--self-test` 그대로
통과 · `test_verify_spec_fws_gate_can_fail.py` 짝은 손대지 않음) 재실행 결과
[실측 2026-09-28T09:14 · gx-shell]:

    길목 시험 = test_fws_app.py · test_fws_f2.py · test_fws_f5.py
    pytest 요약 — 통과 43 · 실패 0 · 에러 0
    ── 요약 — 닫은 열 25/25 · 최종 PASS ──

이 차선이 개별로 확인한 pytest 실측(gx-shell, `--create-db`):

    tests/test_fws_f5.py                                                13 passed (단독)
    tests/test_fws_app.py + test_fws_f2.py + test_fws_f5.py
      + test_f05_event_api.py + test_dsm_app.py (합본)     2 failed, 89 passed
      ↳ 실패 2건은 **F5 밖** — `EntrySurfaceIsLockedTest::test_the_count_is_not_zero`·
        `test_the_entry_surface_is_pinned_by_name`, 전부 `/api/dsm/cbs-drafts`·
        `/api/dsm/control-points`·`/api/dsm/video-access-requests`·
        `/api/dsm/shifts`·`/api/dsm/situation-reports` 새 라우트가
        `EVENT_ENTRY_SURFACE`/`K1_CONSUMERS`(같은 시험 파일 · 다른 lane 소유)에
        등재되지 않아 생긴 실패다. `apps/fws/drone.py`·`/api/fws/drone/*` 는 이
        실패 목록에 **없다** — 이 차선이 만들지 않았고 고치지도 않았다(공유
        파일 · 다른 lane 담당).

정적 게이트(호스트에서 docker 없이 돈다):

    scripts/verify_ui_copy.py            → 통과 — 새로 생긴 대장 언어 0건
    scripts/verify_route_scope_declared.py → 통과 — 선언 없이 태어난 새 라우트 0건
    scripts/verify_layers.py             → 위반 1건, **`backend/apps/fws/
                                            integration.py:416`**(lane N3 · F6
                                            소유 파일) — `apps/fws/drone.py` 는
                                            위반 0건(grep 로 확인). 이 차선의
                                            책임 밖이라 고치지 않았다.

## 13. 못 닫은 F5 다섯 — 「무엇이 없는가」

- **FWS-F5-04** 잔불 순회 예약(구역·간격·야간) — '구역'·'간격'(반복 일정)은 K1 에
  없는 축이다(F2-09 와 같은 한계). 예약 자체도 미래 반복 일정을 담을 표가 새로
  필요하다. M 규모라 범위 밖.
- **FWS-F5-05** 대피 안내 방송(스피커) 임무 — 방송 대상 '구역' 축이 F5-04 와 같은
  이유로 없고, 방송 음성·문구 콘텐츠를 담을 저장 경로도 없다(F1-07 과 같은 한계).
  M 규모라 범위 밖.
- **FWS-F5-06** 비행 제한(헬기 투입 중 드론 금지 구역 · 고도) 표시·차단 — '헬기
  투입 중' 상태를 아는 축이 없다(F2-05 지원 요청은 텍스트 로그일 뿐 실제 배치
  플래그가 아니다). 고도·금지구역 판정도 새 축이 필요하다. L 규모라 범위 밖.
- **FWS-F5-07** 피해면적 산출(정사영상 → 폴리곤 ha) — F-03 폴리곤 문
  (`stream_monitors.services.zones.save_zone`)은 F-12 관리자 위험구역 지정
  전용이고 면적 계산이 없다. 정찰용 피해면적 폴리곤을 받는 새 입력 문이 없다 —
  F-03 폴리곤 잠금이 이 용도를 허락하지 않는다(D-299·D-365, 작업지시가 미리 건
  조건 그대로). M 규모라 범위 밖.
- **FWS-F5-09** 영상 스트림 관제 화면 공유 — 실시간 스트림 공유 인프라가 이 App
  층에 없다. DSM 의 클립 스트림은 다른 App(lane N1) 소유라 재사용하지 않았다.
  M 규모라 범위 밖.

## 14. 제안 YAML — `kind_derived.annex_promoted.closed` 에 F5 5건 이어 붙이기

```yaml
# docs/agent/evidence/D-346/ga_readiness.yaml :: areas[id=="1"].kind_derived.annex_promoted 안에 추가 제안
kind_derived:
  annex_promoted:
    closed:
      # (턴 AK 의 F1 10건 · 턴 AL 의 F2 10건은 그대로 두고, 아래 F5 5건을 이어 붙인다)
      - FWS-F5-01
      - FWS-F5-02
      - FWS-F5-03
      - FWS-F5-08
      - FWS-F5-10

kind_evidence:
  FWS-F5-01:
    title: 정찰 임무 수신(발화 추정 좌표·반경) → 열화상 정찰
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F5-01.json
    rows: [tests.test_fws_f5.F5_01_ReconTest.test_request_accept_airborne_return_and_mine_reflects_state]
    strength: change
    measured_at: "2026-09-28T09:13:55Z"
    capture_none_why: |
      실제 열화상 정찰(비행·센서 데이터)은 없다 — 세종 판정 P-387(드론 0대,
      요청·상태 두 축만). radius_m 은 K1 이벤트 스키마에 없어 이 파일의 감사
      한 줄에만 남는다.
    what: |
      정찰 요청(반경 값)→수락→이륙→귀환 상태 전이가 내 대기열(mine)에 그대로
      남는다 — 요청·상태 두 축 실측. 다중 행위자 규칙(상태 전이가 사건의
      response_state 를 안 옮김)도 별도 시험으로 확인.

  FWS-F5-02:
    title: 열점·화선 표시(열화상 프레임 → 지도 폴리라인)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F5-02.json
    rows: [tests.test_fws_f5.F5_02_HotspotsTest.test_submit_points_and_fireline_then_read_back]
    strength: change
    measured_at: "2026-09-28T09:13:57Z"
    capture_none_why: |
      열화상 "프레임"(이미지 바이너리)은 저장하지 않는다 — 좌표 값만. 지도
      렌더는 §0.4 인접 금지구역 밖이라 만들지 않았다(값만 낸다).
    what: |
      열점 2점·화선 2점(좌표 목록 값)을 제출한 뒤 재조회에 그대로 보인다 —
      K1 field_reply 로 지휘 화면이 읽는 자리에도 도달.

  FWS-F5-03:
    title: 확인 회신(산불 맞음/오인 · 사진·열화상)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F5-03.json
    rows: [tests.test_fws_f5.F5_03_ConfirmResultTest.test_fire_confirmed_requires_attachment_ref]
    strength: change
    measured_at: "2026-09-28T09:13:58Z"
    capture_none_why: |
      사진·열화상 실제 파일(바이너리) 업로드 저장소는 없다 — attachment_ref 는
      경로/URL 값만 받는다(F1-07·F2-04 와 같은 한계).
    what: |
      드론 확인 회신(산불 맞음 + 참조)이 K1 사건의 verdict 를 confirmed 로
      바꾼다 — F1-06 문 재사용(P-357) + 참조 값 필수화(참조 없이 fire_confirmed
      는 422).

  FWS-F5-08:
    title: 비행 기록·배터리·기체 상태
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F5-08.json
    rows: [tests.test_fws_f5.F5_08_FlightLogTest.test_log_is_recorded_and_read_back]
    strength: change
    measured_at: "2026-09-28T09:14:00Z"
    what: |
      POST /drone/flights(dji · M30T-7 · 배터리 68.5 · 22분) 뒤 GET
      /drone/flights/mine 에 그 값이 그대로 보인다. source 는 DJI 등 연동
      어댑터의 값 자리뿐(실제 API 호출 0건, P-387).

  FWS-F5-10:
    title: 계량(비행 분)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws.py
    proof: docs/agent/evidence/SPEC/FWS-F5-10.json
    rows: [tests.test_fws_f5.F5_10_FlightMinutesTest.test_flight_minutes_are_summed]
    strength: reflect
    measured_at: "2026-09-28T09:14:02Z"
    what: |
      비행 기록 두 건(15분·27.5분) 뒤 GET /drone/flights/minutes 의
      flight_minutes_total 이 42.5 — F5-08 값을 세기만 한다(새 표 없음).
```

## 15. 분모 재확인 요청 (P-356 ③, F5 몫)

§9 와 같은 이유로 F5 몫도 `verify_spec_coverage.py` 를 재실행하지 않았다. F5 5건이
별표 목록에서 **빠지고** area 1 로 **옮겨지므로**, 조율자가 §14 를 적용한 뒤
`python scripts/verify_spec_coverage.py --no-emit` 를 다시 돌려 분모가 293
그대로인지(F1·F2·F5 승격 25건을 함께 옮긴 뒤 기준) 반드시 확인할 것.
