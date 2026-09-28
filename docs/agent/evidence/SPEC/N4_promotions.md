# N4 승격 제안 — DSM-U4-01(부분)·U4-03(부분)·U4-04(부분)·U4-07(부분)·U5-05(부분)
(P-356/P-358/P-376 · WO-GX-20260925-15 §5 · 턴 AM · 차선 N4)

**대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)은 손대지 않았다** — 이 파일은
조율자가 그대로 옮겨 붙일 수 있는 YAML 조각을 제안만 한다(P-356 ④).

## 배정과 결과

이 차선(N4)에 이번 턴 배정된 것은 아홉 — DSM-U4-01·02·03·04·05·07·08·09 ·
DSM-U5-05. 그중 **다섯을 닫는다 — 전부 부분 승격이다.** P-376(「절반은 닫힘이
아니다」)에 따라 제목이 부르는 항목 중 하나라도 없으면 그 항목을 「없다」고
적는다 — 다섯 다 어느 갈래가 빠졌는지 아래 표에 그대로 남긴다. 나머지 넷
(U4-02·05·08·09)은 이번 차선 시간 안에 정직하게 못 붙였다(§ 아래 표).

## 무엇을 닫았나 (5/9 · 전부 부분 승격)

| id | 제목 | 엔드포인트 | 증거 | 게이트 |
|---|---|---|---|---|
| DSM-U4-01 | 재난상황보고서 제N보 채번 대장 | `POST/GET /api/dsm/situation-reports` · `.../sent` | `docs/agent/evidence/SPEC/DSM-U4-01.json` | `scripts/verify_spec_dsm_u4.py` |
| DSM-U4-03 | 재난문자(CBS) 초안 | `POST/GET /api/dsm/cbs-drafts` · `.../approve` · `.../sent` | `docs/agent/evidence/SPEC/DSM-U4-03.json` | `scripts/verify_spec_dsm_u4.py` |
| DSM-U4-04 | 통제·대피 현황판 | `POST/GET /api/dsm/control-points` · `.../advance` | `docs/agent/evidence/SPEC/DSM-U4-04.json` | `scripts/verify_spec_dsm_u4.py` |
| DSM-U4-07 | 영상 열람·제공(반출) 대장 | `POST/GET /api/dsm/video-access-requests` · `.../approve` · `.../provide` | `docs/agent/evidence/SPEC/DSM-U4-07.json` | `scripts/verify_spec_dsm_u4.py` |
| DSM-U5-05 | 교대 편성(4조 3교대) CSV | `POST /api/dsm/shifts/import` · `GET /api/dsm/shifts` | `docs/agent/evidence/SPEC/DSM-U5-05.json` | `scripts/verify_spec_dsm_u4.py` |

다섯 다 실제 구현(`backend/apps/dsm/situation_report_ledger_service.py` ·
`cbs_draft_service.py` · `control_board_service.py` · `video_access_ledger_service.py` ·
`shift_roster_service.py` — 전부 **새 표 0개 · 새 마이그레이션 0개**, `common/audit_writer.py`
감사 이력으로 대장을 쌓는다, `alert_level_service.py`·`threshold_alert_service.py`
와 같은 판단) · 증거(`docs/agent/evidence/SPEC/<id>.json`,
`backend/tests/test_p356_u4_rest_spec_promotions.py::EvidenceExportTest` 가 Django
TestCase + test client(test DB)로 실제로 때려서 냄) · 게이트
(`scripts/verify_spec_dsm_u4.py --self-test` 통과 · 짝
`backend/tests/test_verify_spec_dsm_u4_gate_can_fail.py::TheSelfTestCanFail` 이
응답 500·증거 없음을 각각 빨강으로 잡는 것을 확인) · 아래 이동 제안.

★ **왜 다섯 다 부분인가** — 이 절들의 명세 제목은 여러 갈래를 한 줄에 묶는다
(예: U5-05 는 「CSV 업로드」 + 「인계 메모·일지 근무자 자동」 둘). 이번 차선이
실제로 손댈 수 있었던 것은 **감사 이력 기반 대장**(등록→승인→기록의 다단계
전이) 쪽이고, **다른 파일·다른 절(관제일지 DSM-U1-04, 일일상황보고 DSM-U4-05,
`handover_service.py`)에 걸린 자동 반영**은 이번 배정에도, 이번 차선에도 서지
않았다. P-356 「부분 승격」 선례(턴 AL · DSM-U5-02)와 같은 판단 — **실제로
갖춘 부분만** 승격하고 나머지는 이름으로 남긴다(D-274).

### DSM-U4-01 — 제목이 부르는 것 ↔ 있는 것

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 13항목 자동 채움 | **기존 자산**(`apps/dsm/incident_report.py::build_situation_report`, 턴 AB) — 세종 §4-3 필수 10칸으로 이미 채운다. 이번 턴이 새로 만든 것이 아니다 — 13 vs 10 차이는 `docs/design/GX-FORM_별지1호_v1.0.md` 가 이미 범위로 못박아 둔 것이고, 이번 턴은 그 서식을 안 건드렸다 |
| 제N보 채번 | ✅ 신규 — `situation_report_ledger_service.issue_report`(감사 대장, 사건당 1부터 순서 채번) |
| 최초/중간/최종 구분 | ✅ 신규 — `kind` 파라미터, `REPORT_KINDS` 검증(400) |
| HWPX/PDF | ❌ **없음** — 기존 서식은 DOCX 만 낸다(`docx_export`). HWPX 렌더러 자체가 이 저장소 어디에도 없다(전체 DSM 서식군의 기존 한계이지 이 절만의 결함이 아니다) |
| 발송 기록 | ✅ 신규 — `POST .../situation-reports/{id}/sent`(수신처·시각) |
| 완결조건 「지체 없이 타이머」 | **부분** — 경과분(`elapsed_minutes`, 사건 발생시각 대비 발행시각)은 계산해 응답에 낸다. 법정 분 단위 기준을 명세서·조사 메모 어디서도 못 찾아(D-280, 지어내지 않는다) 빨강/초록 판정은 하지 않는다 — 화면이 이 값으로 문턱을 그릴 수 있지만 그 문턱을 이 절이 대신 정하지 않는다 |

**판정: 부분 승격.** HWPX 없음(기존 한계 상속) · 「지체 없이」 빨강/초록 판정 없음(값은 있음)이 빠졌다.

### DSM-U4-03 — 제목이 부르는 것 ↔ 있는 것

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 유형·구역 선택 | ✅ `kind`(위급/긴급/안전안내) · `region` |
| 표준 문안(자동 생성) | **부분** — 정형 템플릿 라이브러리는 없다. 사람이 `message` 를 직접 쓰고, 이 절은 그 문안의 **글자수만** 검사한다(유형별 표준 문구 사전은 이번 턴 범위 밖) |
| 글자수 검사(90/157) | ✅ `apps/dsm/u4_regulations.py::CBS_LEN_LIMIT` — 안전안내 90 · 긴급·위급 157(명세서 §4.4 실측) |
| 승인권자 결재 요청 | ✅ `POST .../cbs-drafts/{id}/approve` |
| 발송은 행안부 시스템(이 제품은 안 함) | ✅ 명세 그대로 — 발송 버튼이 없다 |
| 발송 기록 | ✅ `POST .../cbs-drafts/{id}/sent`(승인 전이면 409) |
| 야간(21~06시) 안전안내 경고 | ✅ `night_warning` 플래그(저장은 막지 않는다 — 「자제」이지 「금지」가 아니다) |

**판정: 부분 승격.** 「표준 문안 자동 생성」(사전 템플릿)이 빠졌다 — 완결조건(승인·발송 감사, 야간 경고)은 갖췄다.

### DSM-U4-04 — 제목이 부르는 것 ↔ 있는 것

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 통제 개소 등록 | ✅ `POST /control-points` |
| 도달·결정·실행·해제 4시각 | ✅ 순서 강제(`CONTROL_STAGE_ORDER`) — 건너뛰면 409, 넷 다 감사에 남는다 |
| 대피 인원·장소 | ✅ `evacuee_count` · `evacuation_site`(등록 시 같은 줄에 기록) |
| 현황판(출력) | ✅ `GET /control-points` — 지점마다 지금 단계(JSON 표. 화면은 P-356 이 명시한 대로 선택이라 안 만들었다) |
| 일일보고 자동 반영(출력) | ❌ **없음** — DSM-U4-05(일일상황보고 자동)가 이번 배정에도 미착수라 반영할 문서 자체가 없다 |
| `controls` 모델(처리) | **다른 모양으로 있음** — 새 ORM 표 대신 감사 이력 대장(`AppStaysThinTest` 가 apps/dsm 의 ORM 을 막는다 · 새 표 0 원칙). 완결조건(4시각 전부 기록)은 모델 종류와 무관하게 충족한다 |

**판정: 부분 승격.** 「일일보고 자동 반영」이 빠졌다(선행 절 DSM-U4-05 미착수) — 4시각·현황판 자체는 갖췄다.

### DSM-U4-07 — 제목이 부르는 것 ↔ 있는 것

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 수사기관 요청 접수(공문번호·목적·범위) | ✅ `POST /video-access-requests`(셋 다 필수, 빈 값 400) |
| 승인 | ✅ `POST .../approve` |
| 마스킹본 제공 | **부분** — 「제공했다」는 사실·시각·경로 기록은 있다. **실제 영상 픽셀 마스킹 파이프라인 실행은 없다** — `privacy_request.py`(LAW-07, 정보주체 본인 청구)의 이미지 마스킹과는 다른 대상(수사기관 등 제3자 제공)이고, 그 파이프라인을 이 절이 재사용하거나 새로 만들지 않았다 |
| 개인영상정보 관리대장 자동 기재 | ✅ 요청→승인→제공 세 단계가 감사 대장에 자동으로 쌓인다(`GET /video-access-requests`) |
| 원본 반출 0 | ✅ **구조로 보장** — 이 절의 어느 함수도 영상 파일 경로·바이트를 받는 매개변수가 없다 |
| 연간 통계(출력) | ❌ **없음** — 목록 조회만 있고 연간 집계는 만들지 않았다 |

**판정: 부분 승격.** 「실제 마스킹 파이프라인」과 「연간 통계」가 빠졌다 — 대장 자체(접수→승인→제공)와 원본 반출 0 은 갖췄다.

### DSM-U5-05 — 제목이 부르는 것 ↔ 있는 것

| 제목이 부르는 것 | 있는 것 |
|---|---|
| CSV 업로드 | ✅ `POST /shifts/import`(머리글 고정 `date,team,shift,members`) |
| `shifts` 저장 | ✅(감사 이력 대장 — 재업로드는 최근 줄이 이긴다) |
| 표(출력) | ✅ `GET /shifts`(날짜로 좁힐 수 있다) |
| 인계 메모 근무자 자동 | ❌ **없음** — `handover_service.py`(다른 턴 소유, 이번 턴이 고치지 않기로 함)를 안 건드렸다 |
| 일지 근무자 자동 | ❌ **없음** — 관제일지(DSM-U1-04) 자체가 이 제품에 없다(여전히 미착수) |
| 완결조건 「일지 근무자 = 편성표」 | ❌ **미달성** — 위 두 이유로 이 완결조건 자체를 채우지 못했다 |

**판정: 부분 승격 — 가장 좁은 부분.** CSV 업로드·저장·조회 표까지만 닫았다.
명세의 **완결조건 자체(일지 근무자=편성표)는 이번 턴에 못 채웠다** — 그래도
승격 제안에 넣는 이유는, 이 절의 제목이 부르는 「CSV → `shifts`」 저장처 자체가
이 저장소에 전혀 없던 것(N1 의 턴 AL 「무엇이 없는가」 그대로)에서 실제 저장처가
선 것은 별개의 실측 가능한 진전이기 때문이다. ⚠ **조율자 확인 요청** — 완결조건
자체가 없는 이 절을 「부분 승격」으로 인정할지, 인정 안 되면 이동하지 않고
`annex_2_spec.clauses` 에 그대로 두어야 하는지(P-356 「셋 중 하나라도 없으면
승격하지 않는다」) 판단해 달라.

## 이동 제안 — `annex_2_spec.clauses` → 8영역 「7 사용성(관리 UI·온보딩)」

★ 영역 선택 사유는 턴 AK·AL 과 같다 — F 의 Table A 재실행을 이번 턴도 못 받았고,
이미 관리자용 신규 엔드포인트를 담아 온 영역 `"7"` 에 잠정 배치한다(조율자·F 가
다른 영역이 맞다고 판단하면 `area id` 한 줄만 바꾸면 된다).

### ① `annex_2_spec.clauses` 에서 지운다

```yaml
    # 지운다 — DSM-U4-01·U4-03·U4-04·U4-07·U5-05 는 아래 area "7" 로 이동했다
    # (부분 승격 — kind: closed_partial, 각 kind_why 의 범위 참조)
    # - id: DSM-U4-01
    #   status: 미착수
    #   kind: unmeasurable
    #   hand: in
    #   src: DSM
    # - id: DSM-U4-03 ... (동일하게 지운다)
    # - id: DSM-U4-04 ... (동일하게 지운다)
    # - id: DSM-U4-07 ... (동일하게 지운다)
    # - id: DSM-U5-05 ... (동일하게 지운다)
```

### ② `areas:` → `id: "7"` (사용성) `.clauses` 끝에 더한다

```yaml
      - id: DSM-U4-01
        title: 재난상황보고서(별지 제1호서식) 제N보 채번 대장(부분 — 기존 10칸 서식
          + 신규 제N보 채번·최초/중간/최종 구분·발송기록. HWPX 없음·「지체없이」
          빨강판정 없음은 미착수)
        status: 부분구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/situation_report_ledger_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U4-01.json

      - id: DSM-U4-03
        title: 재난문자(CBS) 초안(부분 — 유형·구역·글자수·승인·발송기록·야간경고
          있음. 유형별 표준 문안 템플릿 자동 생성은 미착수)
        status: 부분구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/cbs_draft_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U4-03.json

      - id: DSM-U4-04
        title: 통제·대피 현황판(부분 — 통제개소·4시각·대피인원장소·현황판 있음.
          일일보고 자동 반영은 DSM-U4-05 미착수로 미착수)
        status: 부분구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/control_board_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U4-04.json

      - id: DSM-U4-07
        title: 영상 열람·제공(반출) 대장(부분 — 요청·승인·제공기록·원본반출0 있음.
          실제 마스킹 파이프라인 실행·연간 통계는 미착수)
        status: 부분구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/video_access_ledger_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U4-07.json

      - id: DSM-U5-05
        title: 교대 편성 CSV(부분 — CSV 업로드·저장·조회 표 있음. 인계메모·일지
          근무자 자동은 미착수 — 완결조건 자체 미달성. 조율자 인정 여부 확인 요)
        status: 부분구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/shift_roster_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U5-05.json
```

## 무엇이 없는가 — 못 닫은 넷(이번 배정 9 중)

| id | 제목 | 무엇이 없는가 |
|---|---|---|
| DSM-U4-02 | 중간 보고 사이클 | 08·17시 기준 자동 초안 배치·NDMS 표 내보내기가 없다. M 규모(배치 스케줄 + 표 1:1 매핑)라 이번 차선(가장 싼 것 우선)의 시간 안에 못 붙였다 |
| DSM-U4-05 | 일일상황보고 자동 | 06:00 자동 배치가 없다. `monthly_report.py::KINDS` 는 세 종류로 잠겨 있고(N1 소유, 안 건드림) 별도 경로를 새로 파는 것도 M 규모다 — celery beat 등재(`config/**`, 조율자 소유) 없이 「자동」을 주장하면 거짓이다 |
| DSM-U4-08 | 재난관리평가·감사 자료 묶음 | 기간별 ZIP(PDF+CSV) 조립 배치가 없다. 이번 턴 U4-01·03·04·07 이 새로 섰지만 **HWPX/PDF 로 찍어 내는 서식이 아니라 JSON 감사 이력**이라 ZIP 에 넣을 PDF/CSV 산출물 자체가 없다 |
| DSM-U4-09 | 통계 축 추가(지역안전지수) | `stats?by=safety_index` 매핑축이 없다. 기존 `stats_axes`(턴 T 소유)는 5축뿐이고, 공유 파일(`apps/dsm/stats.py`)을 고치는 일이라 이번 차선의 새 파일 전용 범위 밖이다 |

이 넷은 `annex_2_spec.clauses` 에 **그대로 둔다**(status: 미착수 · kind: unmeasurable · 변경 없음).

## N1 게이트와의 관계 — 조율자 확인 요청

`scripts/verify_spec_dsm.py`(N1 소유, 이 턴이 고치지 않음)의 `NOT_STARTED_AL` 표는
DSM-U4-01·02·03·04·05·07·08·09 · DSM-U5-05 전부를 「못 닫음」으로 적어 둔다(턴 AL
시점 실측). 이 차선(N4)이 그중 다섯을 부분 승격으로 닫으면서 그 표가 **낡았다**
— N1 의 파일을 이 턴이 고치지 않기로 했으므로, 두 게이트(`verify_spec_dsm.py` ·
`verify_spec_dsm_u4.py`)를 **합쳐서** 읽어야 「닫은 열」의 전체 그림이 맞다.
조율자가 대장에 옮길 때 이 점을 참고해 주시길 요청한다 — N1 의 `NOT_STARTED_AL`
문구 자체를 고치는 것은 이 차선의 권한 밖이다(파일 소유 규약).

## 시험 · 게이트 재현 (턴 AM · 차선 N4)

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n4 -w /app gx-shell \
  python -m pytest tests/test_p356_u4_rest_spec_promotions.py -q --create-db -p no:randomly

python scripts/verify_spec_dsm_u4.py --self-test     # 판정 규칙만(호스트 · docker 없음)
python scripts/verify_spec_dsm_u4.py                  # 전체(호스트 — 안에서 docker exec 로 위임)
```

**실제 재현(턴 AM · 2026-09-28)**:
`tests/test_p356_u4_rest_spec_promotions.py` — `26 passed in 216.78s`(1건 실패를
잡아 고쳤다 — `cbs_draft_service._find` 가 승인/발송 감사 줄을 **원래 초안의
`audit_id`** 로 다시 좁히려 했는데, 승인·발송은 매번 새 감사 행이라 그 값이 절대
같을 수 없어 항상 「승인 안 됨」으로 잘못 읽었다. `action` 문자열 자체가 이미
group·draft_id 를 품고 있으므로 그것만으로 찾도록 고쳤다). 함께 돌린 길목
전체(`test_p356_u4_rest_spec_promotions.py` ·
`test_verify_spec_dsm_u4_gate_can_fail.py` · `test_f05_event_api.py` ·
`test_dsm_app.py`) — `77 passed in 52.17s`.
`python scripts/verify_spec_dsm_u4.py --no-run` — 닫은 열 5/5 · 최종 PASS.
