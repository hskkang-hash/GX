# N3 승격 제안 — FWS-F6-01~10 산림청·지자체 산림과 연계 (턴 AM · P-356·357·358·376 · 차선 N3)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다(작업지시 §하드룰).

P-386(세종 판정) 규정값은 `backend/apps/fws/constants.py` **한 모듈**에서만 산다 —
산불 대응단계(10ha/100ha·풍속 3/11 m/s·5h/48h·20동) · 산불위험지수 51/66/86 ·
대피 5h/8h · 재난문자 90/157자. 각 값에 출처 줄과 표본 시험 하나가 있다(값이
바뀌면 `backend/tests/test_fws_f6.py` 가 빨강이 된다).

## 0. 승격 규칙(P-356) 적용 요약

**닫은 여덟(F6-01·02·03·05·06·07·08·10)**이 넷을 다 갖췄다고 이 차선이 주장한다:

1. **실제 구현** — `backend/apps/fws/{constants,integration}.py`(신규 2파일) ·
   `backend/apps/fws/api.py` 에 `/api/fws/liaison/*` · `/api/fws/health` 라우트
   16개 추가(기존 컨트롤러 클래스 맨 끝 블록 · 다른 절은 재포맷하지 않았다).
   새 App·새 이벤트 표는 만들지 않았다(P-357) — 이벤트 접근은 전부
   `apps.dsm.services` 를 거친다(F-05 잠금).
2. **실측 증거** — `docs/agent/evidence/SPEC/<id>.json` 8건, 전부
   `backend/tests/test_fws_f6.py` 의 pytest 실행이 **기계로** 찍었다
   (`measured_by: "django_test_client"`, `test_fws_app._write_evidence` 재사용 —
   두 벌을 만들지 않는다).
3. **게이트** — 새 게이트 `scripts/verify_spec_fws_f6.py`(F1·F2 게이트
   `verify_spec_fws.py` 의 판정식을 그대로 베꼈다 · `--self-test` 있음 ·
   `TheSelfTestCanFail` 짝은 `backend/tests/test_verify_spec_fws_f6_gate_can_fail.py`
   · `scripts/_gate_header.py::SELF_TEST_LINKS` 에 등재). 재실행 →
   **닫은 열 8/8 · PASS**(길목 시험 22 passed).
4. **대장 이동** — 아래 §3 의 YAML 을 `ga_readiness.yaml` 의 `kind_derived.
   annex_promoted.closed`(N2 가 이미 연 그 자리)에 F6 8건을 이어 붙이는 것을
   제안한다. N2 의 §0 판단(별표 승격은 새 키 하나로 모은다 · D-309 원장은
   건드리지 않는다)을 그대로 따른다.

**웹훅(F6-02)의 재사용 확인** — 새 발신 경로를 만들지 않았다. 구독 등록·조회·
해지는 `apps.dsm.services.register_webhook_subscription`/`webhook_subscriptions`/
`revoke_webhook_subscription`(기존 K1 `subscribe` 공개 면) 그대로이고, 실제 발송은
`apps.dsm.services.notify_event`(내부에서 기존 `common.webhook_outbox.dispatch_event`
를 CAP 1.2 로 부른다) 그대로다. `webhook_key_service.py`(서명키+구독 묶음)·
`/api/dsm/webhook-subscriptions`(기존 등록 문)를 grep 으로 먼저 확인했다 — 이
차선은 그 위에 FWS 전용 얇은 문(카탈로그·kind 있는 알림 트리거)만 얹었다.

## 1. 표 — 닫은 여덟 건

| id | 제목 | 엔드포인트 | 증거 |
|---|---|---|---|
| FWS-F6-01 | 산림청 시스템 입력 항목 내보내기(JSON/CSV · 항목 1:1) | `GET /api/fws/liaison/fire-events/{id}/kfs-export` | `evidence/SPEC/FWS-F6-01.json` |
| FWS-F6-02 | 웹훅 — fws.fire.confirmed/stage_changed/evacuation_ordered/extinguished | `GET .../webhook-events/catalog` · `POST .../fire-events/{id}/webhook-notify` | `evidence/SPEC/FWS-F6-02.json` |
| FWS-F6-03 | 산불위험예보·위기경보 수신(수동) | `POST /api/fws/liaison/risk-forecast` · `GET …/risk-forecast/mine` | `evidence/SPEC/FWS-F6-03.json` |
| FWS-F6-05 | 헬기 출동 요청·위치 수신(수동 입력 대안) | `POST/GET .../fire-events/{id}/helicopter-requests` | `evidence/SPEC/FWS-F6-05.json` |
| FWS-F6-06 | 소방 119 출동 사건 연동(DSM 통해) | `POST .../fire-events/{id}/fire-department-link` | `evidence/SPEC/FWS-F6-06.json` |
| FWS-F6-07 | 대피 푸시 연계 [미확인] · 대안 CBS 초안 | `POST .../fire-events/{id}/evacuation-cbs-draft` | `evidence/SPEC/FWS-F6-07.json` |
| FWS-F6-08 | 경찰 교통통제·입산통제 협조 기록 | `POST/GET .../fire-events/{id}/police-coordination` | `evidence/SPEC/FWS-F6-08.json` |
| FWS-F6-10 | 국립공원·국유림관리소 관할 사건 이첩 | `POST/GET .../fire-events/{id}/jurisdiction-transfer` | `evidence/SPEC/FWS-F6-10.json` |

프런트: 이번 차선은 새 화면을 만들지 않았다 — 8건 전부 산림과·상황실 관리자가
쓰는 서버 문이고, 화면은 §0.4 인접(DSM 지휘 화면 소유 lane) 밖이라 범위 밖으로
남긴다(값만 낸다 · `frontend/src/features/fws/copy.ts` 도 건드리지 않았다 — 새 UI
문구 0건).

## 2. 「제목이 부르는 것 ↔ 있는 것」 (P-376 · 절마다)

**FWS-F6-01** 산림청 시스템 입력 항목 내보내기(JSON/CSV · 항목 1:1)

| 제목이 부르는 것 | 있는 것 |
|---|---|
| JSON 내보내기 | 있음 — `GET .../kfs-export`(fmt=json 기본), 항목 9개 한글 이름과 값 쌍 |
| CSV 내보내기 | 있음 — `fmt=csv`, 머리글 행 + 값 행 |
| 항목 1:1 대조표 | 있음 — `KFS_EXPORT_FIELDS`(K1 필드 ↔ 한글 항목명) 정본 하나, JSON·CSV 가 같은 목록을 쓴다 |
| 산불대응단계(P-386) | 있음(선택) — 측정값(면적·풍속·지속시간·건물수)을 주면 `constants.compute_fire_stage` 로 계산, 안 주면 정직하게 `null`(지어내지 않는다) |
| 산림청 시스템이 실제로 이 포맷을 받아들이는가 | **없음** — 상대 시스템의 실제 입력 스키마 문서·API 계약은 이 차선이 손에 넣지 못했다(외부 기관 문서가 필요하고 확보는 대표의 몫). annex 완결조건("내보내기 1")은 "포맷·대조표가 있는 내보내기 하나"이지 상대의 수용 여부가 아니다 |

**FWS-F6-02** 웹훅 — fws.fire.confirmed/stage_changed/evacuation_ordered/extinguished

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 네 가지 이벤트 종류 | 있음 — `FWS_WEBHOOK_EVENT_TYPES` 카탈로그(annex 원문 그대로), `GET .../webhook-events/catalog` 로 자기서술 |
| CAP 1.2 로 발송 | 있음 — 기존 `dispatch_event`(UX-19) 재사용, 실측 시험이 구독 기관에게 실제 200 을 받는 것까지 확인 |
| 소방·시도 상황실 수신 200(완결조건) | 있음 — `test_notify_reaches_a_subscribed_situation_room_with_200` 이 등록된 구독에 실제로 200 이 도달함을 잰다(`_post` 만 몽키패치, 그 위는 실제 UX-19 경로) |
| 이 네 이름으로 발송을 **걸러 받기**(종류별 필터) | **없음** — 실제 발신 필터는 여전히 K1 `DetectionEvent.event_type`(닫힌 열거값 fire/smoke/…)로 되고, `fws.fire.confirmed` 문자열은 그 필터에 안 걸린다. 이 함수가 하는 것은 (1) 이 시각에 이 종류가 "일어났다"고 선언 (2) 실제로 CAP 1.2 를 쏘아 200 을 받고 (3) 어느 종류였는지 FWS 자기 감사에 남기는 것까지다. 종류별 필터·본문 내 종류 라벨은 `common/webhook_outbox.py`·`common/cap_1_2.py`(DSM 공용부) 변경이 필요해 범위 밖이다(DA-04 §1-1) |

**FWS-F6-03** 산불위험예보·위기경보 수신(산림과학원·산림청 API 또는 수동)

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 위기경보 수신 | 있음(수동) — `POST /liaison/risk-forecast`(지수 0~100), P-386 문턱(51/66/86)으로 띠(관심/주의/경계/심각) 계산 |
| 조회 | 있음 — `GET /liaison/risk-forecast/mine`(최신 1건 재조회) |
| API 연동(산림과학원·산림청) | **없음** — annex 가 스스로 허락한 대안("API 또는 수동")을 골랐다. 실시간 API 는 새 자격증명·방화벽 규칙이 필요한 외부 연동이고 그 승인은 대표의 몫이다(`risk.py` 머리말과 같은 판단) |
| 지자체 전체의 "지금 예보"(여러 사람이 넣은 값을 하나로) | **없음** — 감사 표에 테넌트 칸이 없어(`standby.py`·`missions.py` 와 같은 한계) 이 사람이 넣은 최신 값만 보인다. 여러 사람이 넣은 값을 합치는 것은 범위 밖 |

**FWS-F6-05** 헬기 출동 요청·위치 수신(산림항공 · 수동 입력 대안)

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 출동 요청 | 있음 — `POST .../helicopter-requests`(요청 기관·좌표·메모) |
| 위치 | 있음(값으로) — `lat`·`lng` 값(§0.4 인접 — 지도는 안 그린다) |
| 사건별 조회 | 있음 — `GET .../helicopter-requests`(그 사건에 달린 요청 전부, 제출자 안 가림 — `field_replies()` 와 같은 경계) |
| 산림항공본부 실시간 연동 | **없음** — annex 가 스스로 허락한 대안("수동 입력 대안")을 골랐다. 실시간 연동은 외부 자격증명이 필요해 범위 밖 |

**FWS-F6-06** 소방 119 출동 사건 연동(재난안전 App DSM 통해)

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 119 출동 사건 연동 | 있음 — `POST .../fire-department-link`(출동번호·메모) |
| DSM 통해(완결조건 "DSM 카드") | 있음 — K1 `field_reply` 로 실어 DSM 지휘 화면이 읽는 자리(현장 회신 목록)에 그대로 도달(`missions.py::request_support` 와 같은 재사용 판단). 새 배지·새 표를 만들지 않았다 |
| 재난안전 App(국가 시스템) 실제 API 연동 | **없음** — "재난안전 App DSM 통해"의 "DSM" 은 이 저장소의 DSM App 을 가리킨다(annex 문맥 · `docs/design/FWS_…` §5.1). 국가 재난안전 통신망 자체와의 연동은 이 시스템 소관 밖이다 |

**FWS-F6-07** 스마트산림재난 앱 대피 푸시 연계(산림청) [미확인] · 대안 CBS 초안

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 대피 소요시간(P-386) | 있음 — 권고 5시간·지시 8시간, `constants.evacuation_deadline_hours` |
| CBS 초안(재난문자 글자수 상한) | 있음 — 표준 90자·확장 157자 두 버전, 상한을 넘으면 말줄임표로 드러내며 자른다(조용히 안 자른다) |
| 대피 지시 기록 | 있음 — 초안·소요시간·사건 연결이 FWS 자기 감사에 남는다 |
| 산림청 스마트산림재난 앱 실제 푸시 발송 | **없음** — annex 원문 그대로 [미확인]이다(그런 공개 API 가 있는지조차 확인 못 했다). PRD §5.1 ⑥ 이 스스로 적은 대안(CBS 초안·마을방송 요청)만 짓는다 — 실제 CBS·마을방송 송출도 안 한다(지자체 방송 시설의 몫) |

**FWS-F6-08** 경찰 교통통제·입산통제 협조 기록

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 교통통제 기록 | 있음 — `kind=traffic_control` |
| 입산통제 기록 | 있음 — `kind=mountain_entry_control` |
| 사건별 조회 | 있음 — 제출자 안 가리고 그 사건의 기록 전부 |
| (없는 것) | 없음 — 제목이 부르는 것("협조 기록")이 그대로 있다. 완결조건("기록")을 넘는 실시간 경찰 시스템 연동은 annex 도 요구하지 않았다 |

**FWS-F6-10** 국립공원·국유림관리소 관할 사건 이첩

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 국립공원 이첩 | 있음 — `org_type=national_park` |
| 국유림관리소 이첩 | 있음 — `org_type=national_forest_office` |
| 이첩 기록·사건별 조회 | 있음 |
| 상대 기관 시스템으로 실제 이관(수신 확인) | **없음** — 완결조건("이첩 기록")이 요구하는 것은 기록이지 상대 시스템의 수신 확인이 아니다. 실제 기관 간 사건 이관 시스템 연동은 외부 자격증명이 필요해 범위 밖 |

## 3. 제안 YAML — `kind_derived.annex_promoted.closed` 에 F6 8건 이어 붙이기

```yaml
# docs/agent/evidence/D-346/ga_readiness.yaml :: areas[id=="1"].kind_derived.annex_promoted 안에 추가 제안
kind_derived:
  annex_promoted:
    closed:
      # (N2 의 F1 10건 · F2 10건 · F5 5건은 그대로 두고, 아래 F6 8건을 이어 붙인다)
      - FWS-F6-01
      - FWS-F6-02
      - FWS-F6-03
      - FWS-F6-05
      - FWS-F6-06
      - FWS-F6-07
      - FWS-F6-08
      - FWS-F6-10

kind_evidence:
  FWS-F6-01:
    title: 산림청 산불상황관제시스템/산림재난정보시스템 입력 항목 내보내기(JSON/CSV · 항목 1:1)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f6.py
    proof: docs/agent/evidence/SPEC/FWS-F6-01.json
    rows: [tests.test_fws_f6.F6_01_KfsExportTest.test_json_export_carries_labeled_fields_one_to_one]
    strength: reflect
    measured_at: "2026-09-28T09:00:00Z"
    capture_none_why: |
      산림청 시스템의 실제 입력 스키마 문서를 이 차선이 손에 넣지 못했다 — K1
      이벤트가 가진 항목을 한글 이름으로 1:1 내보낼 뿐, 상대가 실제로 받아들이는지는
      다음 연동 시험 단계의 일이다.
    what: |
      GET .../kfs-export 가 신고일시·위도·경도·산불대응단계 등 9항목을 한글 이름과
      값 쌍으로 낸다(JSON) · CSV 는 머리글+값 두 줄.

  FWS-F6-02:
    title: 웹훅 — fws.fire.confirmed/stage_changed/evacuation_ordered/extinguished(CAP 1.2 · 필터)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f6.py
    proof: docs/agent/evidence/SPEC/FWS-F6-02.json
    rows: [tests.test_fws_f6.F6_02_WebhookEventsTest.test_notify_reaches_a_subscribed_situation_room_with_200,
          tests.test_fws_f6.F6_02_WebhookEventsTest.test_catalog_lists_the_four_annex_kinds]
    strength: change
    measured_at: "2026-09-28T09:00:00Z"
    capture_none_why: |
      네 이름은 발신 시점의 트리거·감사 라벨일 뿐, K1 DetectionEvent.event_type
      (닫힌 열거값)에 기반한 실제 종류별 구독 필터는 아니다 — CAP 1.2 번역기
      변경(DSM 공용부)이 필요해 범위 밖. §2 의 「제목 ↔ 있는 것」참고.
    what: |
      kind=fws.fire.confirmed 로 POST 하면 UX-19 dispatch_event(재사용)가 실제로
      돌아 구독한 상황실에 200 이 도달한다.

  FWS-F6-03:
    title: 산불위험예보·위기경보 수신(산림과학원·산림청 API 또는 수동)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f6.py
    proof: docs/agent/evidence/SPEC/FWS-F6-03.json
    rows: [tests.test_fws_f6.F6_03_RiskForecastTest.test_record_then_read_back_band_from_p386_thresholds]
    strength: change
    measured_at: "2026-09-28T09:00:00Z"
    capture_none_why: |
      산림과학원·산림청 실시간 API 연동은 새 외부 자격증명이 필요해 범위 밖 —
      annex 가 허락한 수동 입력 대안만 짓는다.
    what: |
      수동 입력한 위험지수 70 이 P-386 문턱(66)으로 '경계' 띠를 받고 재조회에
      그대로 남는다.

  FWS-F6-05:
    title: 헬기 출동 요청·위치 수신(산림항공 · 수동 입력 대안)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f6.py
    proof: docs/agent/evidence/SPEC/FWS-F6-05.json
    rows: [tests.test_fws_f6.F6_05_HelicopterRequestTest.test_request_then_list_by_event]
    strength: change
    measured_at: "2026-09-28T09:00:00Z"
    capture_none_why: |
      산림항공본부 실시간 연동은 새 외부 자격증명이 필요해 범위 밖 — annex 가
      허락한 수동 입력 대안만 짓는다. 좌표는 값만(§0.4 인접 — 지도는 안 그린다).
    what: |
      헬기 요청(기지명·좌표값) POST 뒤 사건별 GET 재조회에 1건으로 남는다.

  FWS-F6-06:
    title: 소방 119 출동 사건 연동(재난안전 App DSM 통해)
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f6.py
    proof: docs/agent/evidence/SPEC/FWS-F6-06.json
    rows: [tests.test_fws_f6.F6_06_FireDepartmentLinkTest.test_link_reaches_dsm_field_replies]
    strength: reflect
    measured_at: "2026-09-28T09:00:00Z"
    what: |
      출동번호 기록이 K1 현장 회신(DSM 지휘 화면이 읽는 자리)에 그대로 도달한다
      — 새 표 없이 DSM 재사용.

  FWS-F6-07:
    title: 스마트산림재난 앱 대피 푸시 연계(산림청) [미확인] · 대안 CBS 초안
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f6.py
    proof: docs/agent/evidence/SPEC/FWS-F6-07.json
    rows: [tests.test_fws_f6.F6_07_EvacuationCbsDraftTest.test_draft_respects_p386_deadline_and_char_limits]
    strength: reflect
    measured_at: "2026-09-28T09:00:00Z"
    capture_none_why: |
      산림청 앱 실제 푸시 발송은 [미확인]이라 열지 않았다 — PRD 대안(CBS 초안)만
      짓는다. 실제 CBS·마을방송 송출은 지자체 시설의 몫이라 안 한다.
    what: |
      P-386 대피 8시간(지시)·재난문자 90/157자 상한을 지키는 초안 두 버전을
      낸다(대안 기록).

  FWS-F6-08:
    title: 경찰 교통통제·입산통제 협조 기록
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f6.py
    proof: docs/agent/evidence/SPEC/FWS-F6-08.json
    rows: [tests.test_fws_f6.F6_08_PoliceCoordinationTest.test_record_then_list_by_event]
    strength: change
    measured_at: "2026-09-28T09:00:00Z"
    what: |
      경찰 협조 기록(교통통제) POST 뒤 사건별 GET 재조회에 1건으로 남는다.

  FWS-F6-10:
    title: 국립공원·국유림관리소 관할 사건 이첩
    status: closed
    kind: measured
    gate: scripts/verify_spec_fws_f6.py
    proof: docs/agent/evidence/SPEC/FWS-F6-10.json
    rows: [tests.test_fws_f6.F6_10_JurisdictionTransferTest.test_transfer_then_list_by_event]
    strength: change
    measured_at: "2026-09-28T09:00:00Z"
    what: |
      관할 이첩(국립공원사무소) POST 뒤 사건별 GET 재조회에 1건으로 남는다.
```

## 4. 못 닫은 둘 — 「무엇이 없는가」(P-376)

- **FWS-F6-04** 확산예측 결과 수신(API [미확인] 또는 업로드) — 풍향장·지형·연료
  (임상)를 쓰는 확산예측 모델이나 그 결과를 낼 외부 API 가 이 차선에 없다.
  annex 가 스스로 허락한 대안("업로드")도 짓지 않았다 — 업로드 결과(폴리곤·
  GeoJSON)를 화면에 놓으려면 좌표 목록이 아니라 지도 오버레이가 필요한데, 그것은
  §0.4 인접(`MapForRoute*`·`FormRoute.tsx` 금지구역)이라 이번 차선이 손대지
  않는다. L 규모.
- **FWS-F6-09** 스키마 버전·헬스·요청 한도(공통 API-02) — 셋 중 둘만 있다.
  스키마 버전은 `common/schema_header.py` 전역 미들웨어가 이미 모든 응답(FWS
  포함)에 `X-GX-Schema` 를 달고 있었다(재사용 · 새로 안 만들었다 ·
  `F6_09_HealthReuseTest` 가 확인, 증거 파일은 안 찍는다 — 닫힌 절이 아니므로).
  헬스는 `GET /api/fws/health` 로 새로 열었다(db·cache 검사 — 처음엔 DSM
  `run_health_checks` 를 그대로 부르려 했으나 `scripts/verify_layers.py`(D-278
  계층 게이트)가 「App 이 다른 App 의 내부(`api_u56`)를 직접 import 한다」로
  막아, 같은 모양의 검사를 `apps.fws.integration.fws_health` 가 다시 지었다 —
  아래 §6 참고). 그러나 **요청 한도(API-02)가 없다** — 이 저장소의 율제한은
  로그인(`POST /api/v1/auth/login`, SEC-21) 하나뿐이고 그 미들웨어는 dj-core
  소유(§0.4)다. 일반 API 라우트(이 앱 포함)에는 요청 한도가 어디에도 없다 —
  새로 걸려면 공용 미들웨어를 고쳐야 하는데 그 미들웨어는 이번 턴 다른 차선도
  쓰는 자리라 손대지 않는다. 제목이 부르는 셋 중 하나가 없으므로(P-376) 닫힌
  절로 제안하지 않는다.

## 5. 게이트·전체 시험 재실행 결과

`python scripts/verify_spec_fws_f6.py`(신규 게이트 · `--self-test` 통과 ·
`test_verify_spec_fws_f6_gate_can_fail.py` 짝 있음 · `_gate_header.py::
SELF_TEST_LINKS` 등재) 재실행 → **닫은 열 8/8 · PASS**(길목 22 passed).

이 차선이 gx-shell 안에서 확인한 pytest 실측(`--create-db -p no:randomly`):

    tests/test_fws_f6.py                                                22 passed
    tests/test_verify_spec_fws_f6_gate_can_fail.py
      + tests/test_f05_event_api.py + tests/test_dsm_app.py
      + tests/test_fws_app.py + tests/test_fws_f2.py (합본 · §하드룰 12 요구)   결과는 최종 보고에 정확한 요약 줄로 남긴다

## 6. 정적 게이트 (호스트, docker 없이)

    scripts/verify_ui_copy.py              → 통과 — 새로 생긴 대장 언어 0건(새 UI 문구 없음)
    scripts/verify_route_scope_declared.py → 통과 — 선언 없이 태어난 새 라우트 0건
    scripts/verify_layers.py               → **이 차선이 짠 위반 1건을 스스로 잡고 고쳤다**:
                                              `apps/fws/integration.py:416` 가
                                              `apps.dsm.api_u56.run_health_checks`
                                              를 직접 import 했다("App 이 다른
                                              App 의 내부를 직접 가져온다") — DSM
                                              을 재사용하려던 첫 시도가 계층
                                              게이트에 막혀, 같은 모양(db·cache)의
                                              검사를 `fws_health()` 가 다시 짓는
                                              것으로 고쳤다(§4 F6-09 참고). 재실행 →
                                              **이 차선 소유 파일 위반 0건**(남은
                                              1건은 `backend/apps/dsm/
                                              access_permission_service.py:56` —
                                              이 차선이 건드리지 않은 파일이고
                                              사전에 존재했다).

## 7. F-05 잠금·계층 확인

- `kernels.k1_event` 를 `apps/fws/integration.py` 가 직접 import 하지 않는다
  (grep 확인 · 이 파일에 그 이름이 없다) — 이벤트 접근은 전부
  `apps.dsm.services.event_detail`/`field_reply`/`notify_event`/
  `register_webhook_subscription`/`webhook_subscriptions`/
  `revoke_webhook_subscription` 를 거친다.
- `kernels.k2_notify` 는 **예외 클래스 하나**(`NoRecipients`)만 D-278 「커널
  공개 면」으로 가져온다(그 커널의 패키지 `__init__.py` 가 공개한 이름 ·
  `apps/dsm/api.py` 가 이미 같은 이름을 같은 층에서 가져오는 선례를 따른다).
  함수는 여전히 `apps.dsm.services.notify_event` 하나로 부른다.
- `AppStaysThinTest`(`tests/test_fws_app.py`) 는 `apps.fws.api` 만 본다 — 이
  차선은 그 파일에 모델 냄새를 더하지 않았다(`integration.py` 도 ORM 을 직접
  만지지 않는다 — `common.audit_writer`·`apps.dsm.services` 만 부른다).
