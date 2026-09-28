# N1 승격 제안 — DSM-U2-03·U2-04·U2-05 (P-356/P-358 · WO-GX-20260925-15 §5 · 턴 AK)

**대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)은 손대지 않았다** — 이 파일은
조율자가 그대로 옮겨 붙일 수 있는 YAML 조각을 제안만 한다(P-356 ④). 분모 293 불변을
확인하려면 이동 뒤 `python scripts/verify_spec_coverage.py` 를 다시 돌려 「절 157 ·
별표 136」 줄이 그대로인지 본다(별표 쪽 3건이 빠지고 8영역 쪽에 3건이 늘어도, 별표는
분모에서 원래도 「등재」로만 세고 분자에 안 들어갔으므로 — **8영역 절 수가 3 늘어야
분자만 움직이고 분모 293은 그대로다**. 8영역 절 수 자체가 293의 구성 요소가 아니라
`대장 157절` 산식과 겹치지 않는지는 P-356 ⑤ 규칙대로 조율자가 재실행 출력으로
확인해 달라).

## 무엇을 닫았나 (3/11 · S 규모 먼저)

| id | 제목 | 엔드포인트 | 증거 | 게이트 |
|---|---|---|---|---|
| DSM-U2-03 | 상황판단회의 기록 | `POST/GET /api/dsm/situation-meetings` | `docs/agent/evidence/SPEC/DSM-U2-03.json` | `scripts/verify_spec_dsm.py` |
| DSM-U2-04 | 임계값 도달 알림 | `POST /api/dsm/thresholds/observe` · `.../observe/{id}/decide` | `docs/agent/evidence/SPEC/DSM-U2-04.json` | `scripts/verify_spec_dsm.py` |
| DSM-U2-05 | 교대 인수인계 합동 확인 | `POST /api/dsm/handover/{id}/ack` | `docs/agent/evidence/SPEC/DSM-U2-05.json` | `scripts/verify_spec_dsm.py` |

넷 다 갖췄다(P-356): ① 실제 구현(`backend/apps/dsm/situation_meeting_service.py` ·
`threshold_alert_service.py` · `handover_service.py::acknowledge` — 전부 기존 DSM
커널 재사용: `common/audit_writer.py` · `kernels/k5_trust` 임계값 판정 · `stream_monitors.DsmHandover`.
**새 표 0개 · 새 마이그레이션 0개**) ② 증거(`docs/agent/evidence/SPEC/<id>.json`,
`backend/tests/test_p356_u2_spec_promotions.py::EvidenceExportTest` 가 Django
TestCase + test client(test DB)로 실제로 때려서 냄) ③ 게이트(`scripts/verify_spec_dsm.py`,
`--self-test` 통과 · 짝 `backend/tests/test_verify_spec_dsm_gate_can_fail.py::TheSelfTestCanFail`
2건이 응답 500·증거 없음을 각각 빨강으로 잡는 것을 확인) ④ 아래 이동 제안.

## 이동 제안 — `annex_2_spec.clauses` → 8영역 「7 사용성(관리 UI·온보딩)」

★ **영역 선택 사유**: P-356 은 「영역은 F 의 Table A 「화면」 칸이 정한다」고 못박았다.
이 턴에 F 의 Table A 재실행을 따로 받지 못해(N1 은 그 표의 소유자가 아니다),
이 저장소에서 **이미 관리자용 신규 화면·엔드포인트를 담아 온 자리**(`UX-01`·`UX-02`·
`UX-25` 등, 전부 area `"7"`)와 같은 성격으로 잠정 배치했다 — **조율자·F 가 다른 영역이
맞다고 판단하면 이 제안의 `area id` 한 줄만 바꾸면 된다(클로즈 사실 자체는 안 바뀐다)**.

### ① `annex_2_spec.clauses` 에서 지운다 (현재 212~226행)

```yaml
    # 지운다 — DSM-U2-03·04·05 는 아래 area "7" 로 이동했다(P-356 ④)
    # - id: DSM-U2-03
    #   status: 미착수
    #   kind: unmeasurable
    #   hand: in
    #   src: DSM
    # - id: DSM-U2-04 ... (동일하게 지운다)
    # - id: DSM-U2-05 ... (동일하게 지운다)
```

### ② `areas:` → `id: "7"` (사용성) `.clauses` 끝에 더한다

```yaml
      - id: DSM-U2-03
        title: 상황판단회의 기록 — 회의 시각·참석·결정(통제·대피·비상 단계)·근거 값(수위·강우) 한 화면
        status: 구현
        kind: closed
        kind_why: |
          [실측 2026-09-27 · 턴 AK 차선 N1] `POST/GET /api/dsm/situation-meetings` 신설.
          `apps/dsm/situation_meeting_service.py` — 새 표 없이 `common/audit_writer.py`
          한 줄(action=situation_meeting:{group_id})로 테넌트별 회의 기록을 남긴다.
          Django TestCase + test client(test DB)로 결정 필수 400 · 감사 라운드트립 ·
          남의 테넌트 비가시성 셋 다 실측(`test_p356_u2_spec_promotions.py::SituationMeetingTest`).
        gate: scripts/verify_spec_dsm.py
        proof: backend/apps/dsm/situation_meeting_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U2-03.json
        note: |
          완결 조건 원문의 「결정 → 테넌트 상태 축 변경」은 이번 범위 밖이다 — 회의
          기록 자체(폼 → 감사 → 조회)만 닫았다. 상태 축 자동 전환은 별도 절로 갈리는
          것이 맞다고 보지만(다른 감사 이벤트 소비가 필요), 이 판단은 조율자 확인 요.

      - id: DSM-U2-04
        title: 임계값 도달 알림 — 하천 수위·강우량이 통제 기준에 닿으면 팀장·U4에게 도달 알림 · 결정 기록
        status: 구현
        kind: closed
        kind_why: |
          [실측 2026-09-27 · 턴 AK 차선 N1] `POST /api/dsm/thresholds/observe` ·
          `.../observe/{id}/decide` 신설. 값 판정은 **재사용**(`kernels.k5_trust.
          resolve_threshold` · 카메라 소유 확인도 그 커널의 `assert_scoped` 를 그대로
          씀 — 새 문지기 0). 기준 미만은 카드가 안 선다(reached=False) · 기준 이상은
          도달 감사 + 결정 감사 **둘 다** 남는다(완결 조건 「도달 시각·결정 시각 둘 다
          감사」 그대로) · 남의 테넌트 카메라 404 · 남의 도달 기록 결정 불가(404) 실측.
        gate: scripts/verify_spec_dsm.py
        proof: backend/apps/dsm/threshold_alert_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U2-04.json
        note: |
          `key` 는 지금 `waterlevel.baseline`(카메라별 지점 기준선, 기존 F-02 임계값
          커널) 하나로 실측했다 — 「강우량」 쪽 임계값 키(`rainfall.*`)는 k5_trust
          THRESHOLDS 표에 아직 없다(D-280 — 값을 지어내지 않는다). 키를 등록하면
          같은 엔드포인트가 그대로 받는다(코드 변경 0) — 그래서 닫힘으로 센다.

      - id: DSM-U2-05
        title: 교대 인수인계 합동 확인 — 08~09시 인계 메모를 팀장이 확인 체크
        status: 구현
        kind: closed
        kind_why: |
          [실측 2026-09-27 · 턴 AK 차선 N1] `POST /api/dsm/handover/{id}/ack` 신설.
          기존 UX-34 인계 표(`stream_monitors.DsmHandover`)에 칸을 더하지 않고
          감사 한 줄(`handover_ack:{id}`)로 확인을 남긴다 — 마이그레이션 0.
          `handover/latest` 의 `acknowledged` 칸이 확인 전후로 바뀌는 것과 남의
          테넌트 인계 메모는 404 인 것을 Django test client 로 실측
          (`test_p356_u2_spec_promotions.py::HandoverAckTest`).
        gate: scripts/verify_spec_dsm.py
        proof: backend/apps/dsm/handover_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U2-05.json
```

## 무엇이 없는가 — 못 닫은 여덟(M 규모, 이번 차선 시간 안에 못 붙였다)

| id | 제목 | 무엇이 없는가 |
|---|---|---|
| DSM-U1-01 | 유형별 행동 카드 | `playbooks.yaml` 유형별 「지금 할 일 3」 정의가 없다 · 체크 → 타임라인 배선 필요 |
| DSM-U1-02 | 112/119 통보 기록 | `POST /events/{id}/notify-agency`(통보 시각·통보자·전달 내용 3칸)가 없다 — 기존 `/notify` 는 F-10 발송이라 다른 절이다 |
| DSM-U1-03 | 인근 카메라 전환·추적 | `GET /cameras/nearby?event=`(반경 300m 자동 제안)가 없다 |
| DSM-U1-04 | 관제일지 자동 | 일지 표·PDF 출력이 없다(인계 확장 검토는 했으나 U2-05 와는 다른 절) |
| DSM-U1-05 | 비상벨·시민 신고 접수 카드 | `POST /events`(manual, source=manual) 사건 생성 진입점이 없다 |
| DSM-U1-06 | 선별관제 큐 정렬 | 심각+미처리 → 통보 미완 → 경과 순 정렬 규칙이 `events/queue` 에 없다 |
| DSM-U2-01 | 상황판단 카드 | 즉시 보고 대상 판정표(사망 3/화재 5·14종)와 확정 → U4 상황보고 초안 자동 생성 사슬이 없다 |
| DSM-U2-02 | 상황보고 초안 승인 | `POST /reports/{id}/approve`(승인/반려 상태 전이)가 없다 — 기존 `/reports/runs` 는 생성·다운로드뿐 |

이 여덟은 `annex_2_spec.clauses` 에 **그대로 둔다**(status: 미착수 · kind: unmeasurable ·
변경 없음) — 승격 넷 중 하나도 못 갖췄으므로 이동하지 않는다(P-356 「셋 중 하나라도
없으면 승격하지 않는다」).

## 시험 · 게이트 재현 (턴 AK)

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n1 -w /app gx-shell \
  python -m pytest tests/test_p356_u2_spec_promotions.py -q --create-db -p no:randomly

python scripts/verify_spec_dsm.py --self-test     # 판정 규칙만(호스트 · docker 없음)
python scripts/verify_spec_dsm.py                 # 전체(호스트 — 안에서 docker exec 로 위임)
```

---

# §AL 승격 제안 — DSM-U4-06 · DSM-U5-02(부분) (P-356/P-358 · WO-GX-20260925-15 §5 · 턴 AL)

**대장은 이번에도 손대지 않았다** — 아래는 조율자가 그대로 옮겨 붙일 수 있는 YAML
조각의 제안이다(P-356 ④). 이 턴 배정은 U4-01~09(9) + U5-02(1) + U5-05(1) = **11**
이고, 그중 **둘을 닫는다** — 지시(WO-15 §5)대로 S(U5-02)를 먼저, 그다음 M 중
「완결 조건이 가장 싼 것」(U4-06, 완결 조건이 「변경 감사」 한 줄뿐)을 골랐다. 나머지
아홉은 전부 다단계 워크플로우이거나 새 저장처·남의 파일 확장이 필요해 이번 차선
시간 안에 정직하게 못 붙였다(§ 아래 표).

## 무엇을 닫았나 (2/11)

| id | 제목 | 엔드포인트 | 증거 | 게이트 |
|---|---|---|---|---|
| DSM-U4-06 | 위기경보·비상 단계 접수 입력 | `POST/GET /api/dsm/alert-level` | `docs/agent/evidence/SPEC/DSM-U4-06.json` | `scripts/verify_spec_dsm.py` |
| DSM-U5-02 | 접근권한·접속기록(**부분** — 아래 범위 참조) | `GET /api/dsm/access-log[/export.csv]` | `docs/agent/evidence/SPEC/DSM-U5-02.json` | `scripts/verify_spec_dsm.py` |

넷 다 갖췄다(P-356): ① 실제 구현(`backend/apps/dsm/alert_level_service.py` ·
`backend/apps/dsm/access_log_service.py` + `apps/dsm/audit.py::access_log_denial`·
`read_access_log_page`·`access_log_csv` — 전부 기존 DSM 커널·표 재사용:
`common/audit_writer.py` 감사 한 줄(U4-06) · dj-core `logger.AuditLogs` 가 이미
쌓는 다섯 채널(U5-02, GX-LAW-09 §1 실측). **새 표 0개 · 새 마이그레이션 0개**)
② 증거(`docs/agent/evidence/SPEC/<id>.json`,
`backend/tests/test_p356_u4_spec_promotions.py::EvidenceExportTest` 가 Django
TestCase + test client(test DB)로 실제로 때려서 냄) ③ 게이트(`scripts/verify_spec_dsm.py`
가 이제 두 시험 파일을 함께 돌린다 — `--self-test` 통과) ④ 아래 이동 제안.

### DSM-U4-06 위기경보·비상 단계 접수 입력 — 완결 조건 그대로

annex(§4.2) 완결 조건은 「변경 감사」 하나다. 상급(중대본·지대본) 발령을
`POST /alert-level`(단계·시각·문서번호·비상 근무 편성)로 접수하면 감사 한 줄이
남고, 가장 최근 줄이 `GET /alert-level` 의 첫 행(지금 단계)이다. 4단계 밖 값은
400. 「상단바 띠·홈 카드」 화면은 P-356 이 명시한 대로 **선택**이라 만들지 않았다.

### DSM-U5-02 접근권한·접속기록 — **부분 승격**, 범위를 좁힌 이유

annex 제목은 「접근권한·접속기록」 두 갈래인데, 이번에 닫은 것은 **뒤 갈래
(접속기록 1년 이상 보관·조회·CSV)뿐**이다:

  · **닫힘**: 「접속기록 … 조회·CSV」— `GET /api/dsm/access-log`·`/export.csv`.
    설계는 이미 서 있었다(`docs/design/GX-LAW-09_접속기록_설계_v1.0.md` §5-2, 턴 AE
    차선 S) — 「권한을 좁힌 전용 화면(U5 시스템관리자만, 원문 노출, 그 접근 자체도
    감사)」을 그대로 코드로 옮겼을 뿐이다. 대표 결정 ⑤(접속 로그는 일반 감사 화면
    에서 뺀다)는 안 건드렸다 — `test_p356_u4_spec_promotions.py::
    test_sysop_sees_access_log_channels_general_audit_still_hides_them` 이 두 화면이
    갈리는 것을 같은 시험 안에서 확인한다. 「1년 이상 보관」은 이미 선언돼 있다
    (`common/log_retention_policy.py::POLICY["audit"].days == 730`, 원칙 365일보다
    김) — 이번 턴이 새로 만든 것이 아니라 **이미 있는 선언**이다.
  · **안 닫힘**: 「사람별 카메라·기능 권한」 — 사람마다 어느 카메라·어느 기능에
    접근 가능한지 보여주는 화면·엔드포인트는 **이번에도 안 만들었다.** 기존 역할
    (K3 표)이 기능 단위 권한은 이미 가르지만, **카메라별** 권한 매트릭스는
    저장처·화면 어느 쪽도 없다 — grep 로 재확인함(`권한관리`·`CameraPermission` 류
    이름 0건). 이것은 annex 제목의 **앞 갈래**이고, M 규모(카메라별 ACL 신설)라
    이번 차선(가장 싼 것 우선)의 시간 안에 못 붙였다.

★ P-356 판정 — 이 절을 **부분 승격**으로 다루는 근거: 지난 턴 U2-04 도 같은 모양의
선례(완결 조건 문구 중 「강우량」 임계값 키는 없이 「수위」만 실측)를 남겼다 —
annex 한 줄에 여러 사실이 묶여 있을 때, **실제로 갖춘 부분만** 승격하고 나머지는
이름으로 남긴다(D-274 — 빈 칸은 「모른다」와 「없다」를 안 가른다). 조율자가 이
판단(부분 승격 인정 여부)을 다시 봐 주시길 요청한다 — 인정되지 않으면 이 절은
이동하지 않고 `annex_2_spec.clauses` 에 그대로 남아야 한다(P-356 「넷 다 갖춰야
승격」 원칙 그대로).

## 이동 제안 — `annex_2_spec.clauses` → 8영역 「7 사용성(관리 UI·온보딩)」

★ 영역 선택 사유는 턴 AK 와 같다(§ 위 문단 — F 의 Table A 재실행을 이번 턴도 못
받았고, 이미 관리자용 신규 엔드포인트를 담아 온 영역 "7" 에 잠정 배치한다).

### ① `annex_2_spec.clauses` 에서 지운다

```yaml
    # 지운다 — DSM-U4-06 은 아래 area "7" 로 이동했다(P-356 ④)
    # - id: DSM-U4-06
    #   status: 미착수
    #   kind: unmeasurable
    #   hand: in
    #   src: DSM

    # 지운다 — DSM-U5-02 도 아래 area "7" 로 이동했다(부분 — kind_why 의 범위 참조)
    # - id: DSM-U5-02
    #   status: 미착수
    #   kind: unmeasurable
    #   hand: in
    #   src: DSM
```

### ② `areas:` → `id: "7"` (사용성) `.clauses` 끝에 더한다

```yaml
      - id: DSM-U4-06
        title: 위기경보·비상 단계 접수 입력 — 상급 발령 접수(단계·시각·문서번호) · 비상 근무 편성 인원 수 기록
        status: 구현
        kind: closed
        kind_why: |
          [실측 2026-09-28 · 턴 AL 차선 N1] `POST/GET /api/dsm/alert-level` 신설.
          `apps/dsm/alert_level_service.py` — 새 표 없이 `common/audit_writer.py`
          한 줄(action=alert_level:{group_id})로 테넌트별 접수 이력을 남긴다.
          완결 조건 원문(「변경 감사」)을 그대로 실측했다 — 4단계(관심·주의·경계·
          심각) 밖 값 400 · 접수마다 감사 한 줄 · 가장 최근 줄이 목록 첫 행(지금
          단계) · 남의 테넌트 접수 비가시성을 Django TestCase + test client 로
          실측(`test_p356_u4_spec_promotions.py::AlertLevelTest`).
        gate: scripts/verify_spec_dsm.py
        proof: backend/apps/dsm/alert_level_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U4-06.json
        note: |
          「상단바 띠·홈 카드」 화면은 만들지 않았다(P-356 — 화면은 선택). 값은
          이 API 로 이미 나가므로 화면은 그 값을 그리기만 하면 된다.

      - id: DSM-U5-02
        title: 접근권한·접속기록(부분 — 접속기록 1년 이상 보관·조회·CSV 만. 「사람별 카메라·기능 권한」 매트릭스는 미착수)
        status: 부분구현
        kind: closed_partial
        kind_why: |
          [실측 2026-09-28 · 턴 AL 차선 N1] `GET /api/dsm/access-log` ·
          `/api/dsm/access-log/export.csv` 신설 — GX-LAW-09 §5-2(턴 AE 차선 S)가
          이미 세운 설계(「좁힌 전용 화면 · U5 시스템관리자만 · 원문 노출 · 그
          접근 자체도 감사」)를 코드로 옮겼다. 새 표 0개 — dj-core 가 이미 쌓는
          `db`·`jwt`·`application`·`security`·`user_update` 다섯 채널을 읽는다.
          시스템관리자·테넌트관리자·전역관리자만 200(팀장 403) · 남의 테넌트
          접속 기록 비가시성 · 일반 감사 화면(`/audit`)에는 여전히 안 뜸(대표
          결정 ⑤ 유지) · 조회·CSV 마다 감사 한 줄(`guardianx.u5.access_log_read`)
          을 Django TestCase + test client 로 실측
          (`test_p356_u4_spec_promotions.py::AccessLogTest`). 「1년 이상 보관」은
          `common/log_retention_policy.py::POLICY["audit"].days=730` 로 이미 선언
          돼 있다(원칙 365일 이상 — 이번 턴 신설 아님, 기존 선언을 가리킨다).
        gate: scripts/verify_spec_dsm.py
        proof: backend/apps/dsm/access_log_service.py · backend/apps/dsm/audit.py
        evidence: docs/agent/evidence/SPEC/DSM-U5-02.json
        note: |
          **범위 밖(다음 사람 몫)**: 「사람별 카메라·기능 권한」 매트릭스 —
          사람마다 어느 카메라·어느 기능에 접근 가능한지 보여주는 화면·저장처가
          없다(grep 재확인 · 0건). M 규모(카메라별 ACL 신설)다.
          ⚠ **조율자 확인 요청**: 이 절을 annex 제목 전체(두 갈래)가 아니라
          **뒤 갈래만** 승격으로 인정할지 판단해 달라 — 인정 안 되면 이동하지
          않고 원래 자리(annex_2_spec.clauses · 미착수)에 그대로 둔다.
```

## 무엇이 없는가 — 못 닫은 아홉(이번 배정 11 중, M 규모 · 다음 턴 자리)

| id | 제목 | 무엇이 없는가 |
|---|---|---|
| DSM-U4-01 | 재난상황보고서(별지 1호) | 제N보 채번·최초/중간/최종 구분·「지체 없이」 타이머가 없다(기존 `situation_report_docx` 는 단건 스냅숏) |
| DSM-U4-02 | 중간 보고 사이클 | 08·17시 기준 자동 초안 배치·NDMS 표 내보내기가 없다 |
| DSM-U4-03 | 재난문자(CBS) 초안 | `POST /cbs-drafts` 자체가 없다(글자수 90/157·승인권자 결재요청·발송기록 3단계) |
| DSM-U4-04 | 통제·대피 현황판 | 통제 지점 4시각(도달·결정·실행·해제) 저장처가 없다 |
| DSM-U4-05 | 일일상황보고 자동 | 06:00 자동 배치가 없다 — 기존 `monthly_report.py::KINDS` 는 세 종류로 잠겨 있어(그 파일 소유는 다른 턴) 확장이 이번 차선 몫이 아니다 |
| DSM-U4-07 | 영상 열람·제공(반출) 대장 | `privacy_request.py` 에 「제공」·「반출」 관련 코드 0건(GX-LAW-09 §4 실측 그대로) |
| DSM-U4-08 | 재난관리평가·감사 자료 묶음 | 기간별 ZIP 조립 배치가 없다 — U4-01·02·03·04·07 선행 |
| DSM-U4-09 | 통계 축 추가(지역안전지수) | `stats?by=safety_index` 매핑축이 없다 — 기존 `stats_axes` 는 5축뿐 |
| DSM-U5-05 | 교대 편성 CSV | 근무표 업로드 파서·`shifts` 저장처가 없다 |

이 아홉은 `annex_2_spec.clauses` 에 **그대로 둔다**(status: 미착수 · kind: unmeasurable ·
변경 없음).

## 시험 · 게이트 재현 (턴 AL)

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n1 -w /app gx-shell \
  python -m pytest tests/test_p356_u2_spec_promotions.py tests/test_p356_u4_spec_promotions.py \
  -q --create-db -p no:randomly

python scripts/verify_spec_dsm.py --self-test     # 판정 규칙만(호스트 · docker 없음)
python scripts/verify_spec_dsm.py                 # 전체(호스트 — 두 시험 파일을 함께 돌린다)
```

---

# §AM 승격 제안 — DSM-U3-04 · DSM-U3-03 (P-356/P-358/P-376 · WO-GX-20260925-15 §5 · 턴 AM)

**대장은 이번에도 손대지 않았다** — 아래는 조율자가 그대로 옮겨 붙일 수 있는 YAML
조각의 제안이다(P-356 ④). 이 턴 배정은 DSM-U3-01~04(4) + DSM-U6-01~03(3) = **7**
이고, 그중 **둘을 닫는다** — 지시(WO-15 §5)대로 S(U3-04)를 먼저, 그다음 M 중
「가장 싼 것」(U3-03 — 사진 업로드도 상황보고 조립도 이미 서 있어 **잇기만** 했다)을
골랐다. 나머지 다섯(U3-01·U3-02·U6-01·U6-02·U6-03)은 이 저장소에 아직 없는
저장처·능력에 걸려 이번 차선 시간 안에 정직하게 못 붙였다(§ 아래 표).

★ **P-376 「반은 닫힌 것이 아니다」를 이 절에서 처음 적용한다.** 아래 두 절 각각에
「제목이 부르는 것 ↔ 있는 것」 표를 붙인다 — 제목이 부르는 낱말 중 하나라도 빈
줄이면 그 절은 승격 제안에서 뺀다(이번 둘은 뺄 것이 없었다 — 표가 그 증거다).

## 무엇을 닫았나 (2/7)

| id | 제목 | 엔드포인트·자리 | 증거 | 게이트 |
|---|---|---|---|---|
| DSM-U3-04 | PS-LTE 그룹통화 번호 · 상황실 번호 버튼 | `POST/GET /api/dsm/hotline` + `MobileEventDetail.tsx` M2 버튼 | `docs/agent/evidence/SPEC/DSM-U3-04.json` | `scripts/verify_spec_dsm.py` |
| DSM-U3-03 | 현장 사진 → 보고서 증빙 자동 첨부 | 기존 `POST /events/{id}/field-photo` + `GET /events/{id}/situation-report.docx` ⑨ 첨부 칸 | `docs/agent/evidence/SPEC/DSM-U3-03.json` | `scripts/verify_spec_dsm.py` |

넷 다 갖췄다(P-356): ① 실제 구현(`backend/apps/dsm/hotline_service.py`(신설) ·
`backend/apps/dsm/api_u3.py::set_hotline/get_hotline`(신설 라우트 둘) ·
`backend/apps/dsm/incident_report.py::_field_photo_count/build_situation_html/
build_situation_report`(기존 함수 확장) · `frontend/.../MobileEventDetail.tsx`
M2 전화 버튼(신설). **새 표 0개 · 새 마이그레이션 0개** — 번호는 감사 한 줄(U3-04),
사진 수는 이미 있는 `DsmFieldPhoto` 를 세기만 한다(U3-03)) ② 증거
(`docs/agent/evidence/SPEC/<id>.json`, `backend/tests/test_p356_u3u6_spec_promotions.py::
EvidenceExportTest` 가 Django TestCase + test client(test DB)로 실제로 때려서 냄)
③ 게이트(`scripts/verify_spec_dsm.py` 가 이제 세 시험 파일을 함께 돌린다 —
`--self-test` 통과, pytest 10건 전부 통과 — 아래 재현 참조) ④ 아래 이동 제안.

## 「제목이 부르는 것 ↔ 있는 것」(P-376)

### DSM-U3-04 「PS-LTE 그룹통화 번호 · 상황실 번호 버튼」

| 제목이 부르는 것 | 있는 것 |
|---|---|
| PS-LTE 그룹통화 번호 | `hotline_service.py` 의 `pslte_group_call`/`pslte_group_call_tel` 칸 — 테넌트당 하나, `POST /api/dsm/hotline` 로 접수, 감사 한 줄이 정본 |
| 상황실 번호 | 같은 문의 `situation_room_phone`/`situation_room_tel` 칸 — 같은 접수·같은 감사 |
| 버튼(M2) | `MobileEventDetail.tsx` M2 「② 어디로 가나」 카드에 `tel:` 링크 버튼 — **번호가 있는 칸만** 그린다(없으면 "아직 등록된 연락 번호가 없습니다"로 죽은 손잡이를 피한다, 이 파일 머리말의 기존 규율 그대로) |
| 완결 조건 「1탭」 | 버튼이 `<a href="tel:...">` 하나뿐이라 구조상 1탭이다. **실기기에서 다이얼러가 실제로 열리는지는 이 저장소가 못 잰다**(브라우저/OS 연동 · e2e 범위 밖) — 코드 모양(단일 `tel:` 링크)만 실측했다. |
| annex 「구현」 칸 `tel:` | 재난안전통신망 자체와는 연동하지 않는다 — annex 원문이 이미 그렇게 좁혀 뒀다(§ 위 로드맵 문서 §3 인용). |

빠진 낱말 없음 — 승격 제안.

### DSM-U3-03 「현장 사진 → 보고서 증빙 자동 첨부」

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 현장 사진 | 기존 `POST /events/{id}/field-photo`(턴 Q·R, 이번 턴 신설 아님) — `DsmFieldPhoto` 행 |
| 보고서 | 별지 1호 상황보고 `GET /events/{id}/situation-report.docx`(턴 AB 기존) |
| 증빙 | ⑨ 첨부 칸에 "N장이 이 사건에 자동 첨부되었습니다" 문장 — 원본 바이트는 계약 11조에 따라 안 붙인다(영상 구간과 같은 규약), 이름·수만 증빙으로 남는다 |
| 자동 | 사람이 첨부를 고르지 않는다 — `_field_photo_count` 가 `DsmFieldPhoto.objects.filter(event_id=…).count()` 로 스스로 세어 서식에 끼운다 |
| 첨부 | ⑨ 첨부 표에 실제 행 하나가 생긴다(0장이어도 칸은 남는다 — "없다"와 "집계 안 함"을 가른다) |
| 완결 조건 「첨부 1」 | 사진 1장 올린 뒤 리포트에 "1장이…" 문장이 **실측**됨(`FieldPhotoAttachmentTest::test_uploaded_photo_is_automatically_counted_on_the_report`) |

빠진 낱말 없음 — 승격 제안.

## 이동 제안 — `annex_2_spec.clauses` → 8영역 「7 사용성(관리 UI·온보딩)」

★ 영역 선택 사유는 턴 AK·AL 과 같다(§ 위 문단 — F 의 Table A 재실행을 이번 턴도 못
받았고, 이미 관리자·현장용 신규 엔드포인트를 담아 온 영역 "7" 에 잠정 배치한다.
조율자·F 가 다른 영역이 맞다고 판단하면 `area id` 한 줄만 바꾸면 된다).

### ① `annex_2_spec.clauses` 에서 지운다 (현재 227~231행)

```yaml
    # 지운다 — DSM-U3-04 는 아래 area "7" 로 이동했다(P-356 ④ · 턴 AM)
    # - id: DSM-U3-04
    #   status: 미착수
    #   kind: unmeasurable
    #   hand: in
    #   src: DSM

    # 지운다 — DSM-U3-03 도 아래 area "7" 로 이동했다(P-356 ④ · 턴 AM)
    # - id: DSM-U3-03
    #   status: 미착수
    #   kind: unmeasurable
    #   hand: in
    #   src: DSM
```

### ② `areas:` → `id: "7"` (사용성) `.clauses` 끝에 더한다

```yaml
      - id: DSM-U3-04
        title: PS-LTE 그룹통화 번호 · 상황실 번호 버튼 — M2 화면의 `tel:` 1탭 연락
        status: 구현
        kind: closed
        kind_why: |
          [실측 2026-09-28 · 턴 AM 차선 N1] `POST/GET /api/dsm/hotline` 신설.
          `apps/dsm/hotline_service.py` — 새 표 없이 `common/audit_writer.py`
          한 줄(action=hotline:{group_id})로 테넌트별 접수 이력을 남기고 가장
          최근 줄이 지금 번호다(`alert_level_service.py` 와 같은 판단). 두 칸
          다 비면 400 · 다이얼 문자(숫자·+·*·#·-·공백) 밖은 400 · 남의 테넌트
          번호 비가시성을 Django TestCase + test client 로 실측
          (`test_p356_u3u6_spec_promotions.py::HotlineTest`). `MobileEventDetail.tsx`
          M2 화면에 `tel:` 버튼 둘을 그렸다 — 번호가 있는 칸만(죽은 손잡이 0,
          이 화면 머리말이 2026-09-05 부터 지켜 온 규율 그대로).
        gate: scripts/verify_spec_dsm.py
        proof: backend/apps/dsm/hotline_service.py · backend/apps/dsm/api_u3.py · frontend/src/features/mobile/pages/MobileEventDetail.tsx
        evidence: docs/agent/evidence/SPEC/DSM-U3-04.json
        note: |
          재난안전통신망(PS-LTE) 자체와는 연동하지 않는다 — annex 「구현」 칸이
          `tel:` 하나뿐인 그대로다(이 저장소가 잴 수 없는 외부 통신망 영역,
          `기능명세_미포함표_20260925.md` §3 가 이미 그렇게 적어 뒀다). ⓐ(카메라
          별 담당자 번호)는 이 절이 요구하지 않으므로 안 만들었다 — `MobileEventDetail.tsx`
          머리말이 청했던 「⑤판단」이 ⓑ(테넌트당 하나)로 내려진 것이 이 닫음의
          전제다.

      - id: DSM-U3-03
        title: 현장 사진 → 보고서 증빙 자동 첨부 — 별지 1호 ⑨ 첨부 칸에 사진 수가 자동으로 찍힌다
        status: 구현
        kind: closed
        kind_why: |
          [실측 2026-09-28 · 턴 AM 차선 N1] 새 저장처·새 엔드포인트 0개 — 이미
          서 있던 둘을 이었다: 사진 업로드(`POST /events/{id}/field-photo`,
          턴 Q·R)와 별지 1호 상황보고 조립(`build_situation_report`, 턴 AB).
          `incident_report.py::_field_photo_count` 가 `DsmFieldPhoto` 를
          `event_id` 로 세어 ⑨ 첨부 칸에 "N장이 자동 첨부되었습니다"(0장이면
          "없습니다")를 적는다 — 원본 바이트는 안 싣는다(영상 구간과 같은 계약
          11조 규약, 그림 0장 `docx_export` 약속도 유지). 사진 업로드 → DOCX
          생성까지 실제 HTTP 왕복으로 실측(`test_p356_u3u6_spec_promotions.py::
          FieldPhotoAttachmentTest`) — 완성된 DOCX(zip) 의 `word/document.xml`
          을 직접 읽어 문장이 찍힌 것을 확인했다(HTML 만 보고 판단하지 않았다 —
          이 서식 파일의 기존 함정 「DOCX 변환이 첫 줄로 칸 수를 정한다」와 같은
          교훈으로, 완성 바이트까지 갔다).
        gate: scripts/verify_spec_dsm.py
        proof: backend/apps/dsm/incident_report.py
        evidence: docs/agent/evidence/SPEC/DSM-U3-03.json
        note: |
          격리도 실측했다 — 같은 테넌트 안에서도 **사건별로** 사진 수가 안 섞인다
          (`FieldPhotoAttachmentTest::test_someone_elses_photo_does_not_inflate_my_report`).
          테넌트 경계 자체는 K1 `get_event` 문지기가 이미 지킨다(재확인 아님).
```

## 무엇이 없는가 — 못 닫은 다섯(이번 배정 7 중, M·L 규모 · 다음 턴 자리)

| id | 제목 | 무엇이 없는가 |
|---|---|---|
| DSM-U3-01 | 역할별 M2 문안 | 「상주 경찰관·119·시설·당직」을 가르는 역할 분류가 제품에 없다 — `role.Role` 은 임의 코드일 뿐 이 네 갈래를 못박은 표가 아니다(grep 재확인 0건). 새 분류 칸이 필요해 U3-04(전화번호 둘)보다 비싸다. |
| DSM-U3-02 | 통제 실행 회신 | `POST /controls/{id}/executed` 가 받을 「통제 지점」 저장처가 없다. 완결 조건(「도달→결정→실행 3시각」)의 앞 두 시각을 쥔 DSM-U4-04(통제·대피 현황판, N4 소유)가 아직 미착수라 선행 절 의존. |
| DSM-U6-01 | 스마트시티 통합플랫폼 이벤트 연계 | 외부에서 사건을 **만드는** 문 자체가 없다(`POST /events` 수동 생성, DSM-U1-05 와 같은 벽 — 그 절도 턴 AK 부터 미착수). CAP 1.2 해석은 그 문이 선 다음의 일. |
| DSM-U6-02 | NDMS 입력용 내보내기 API | 별지 1호 13항목 1:1 매핑 JSON/CSV. **L 규모**(Table A 실측)로 이번 배정 중 가장 비싸다 — 지시(WO-15 §5) 「S 먼저, 그다음 가장 싼 M」이 이 절을 순서 맨 뒤로 둔다. |
| DSM-U6-03 | 사회적약자(실종) 요청 수신 → 객체 검색 사건 생성 | 「객체 검색」(용모 기반 재식별) 능력이 제품 어디에도 없다(grep 「객체 검색」·`object_search`·재식별 0건). AI 모델 연동이 먼저 서야 하는 M 규모 절. |

이 다섯은 `annex_2_spec.clauses` 에 **그대로 둔다**(status: 미착수 · kind: unmeasurable ·
변경 없음).

## 시험 · 게이트 재현 (턴 AM)

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n1 -w /app gx-shell \
  python -m pytest tests/test_p356_u2_spec_promotions.py tests/test_p356_u4_spec_promotions.py \
  tests/test_p356_u3u6_spec_promotions.py -q --create-db -p no:randomly

python scripts/verify_spec_dsm.py --self-test     # 판정 규칙만(호스트 · docker 없음)
python scripts/verify_spec_dsm.py                 # 전체(호스트 — 세 시험 파일을 함께 돌린다)
```
