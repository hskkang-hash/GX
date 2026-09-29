# N4 승격 제안 — FWS-U5-01~04 · DSM-U5-01·03 기관/시스템 관리자(산불 설정)
(턴 AN · WO-GX-20260929-17 §5 P-356·358·392 · 차선 N4)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다(작업지시 §하드룰).

세종 판정 P-397·P-398(기존 문을 재사용한다)을 그대로 따랐다 — 새 표 **0**
(`logger.AuditLogs` 감사 한 줄로 전부 처리 · `patrol.py`·`standby.py`·
`integration.py`·`apps/dsm/notify_prefs.py` 와 같은 관례), 새 App 없음, F-05
잠금(`apps.dsm.services` 만 거친다), FWS-U5-04 는 `kernels.k2_notify.rule_admin`
(실재 `NotificationRule` 표)을 새 저장처 없이 그대로 재사용했다.

## 0. 승격 규칙(P-356) 적용 요약

**닫은 여섯**이 넷(구현·증거·게이트 행·승격 제안)을 다 갖췄다고 이 차선이 주장한다:
FWS-U5-01(카메라 산불 표식) · FWS-U5-02(초소·순찰함·순찰 구역) · FWS-U5-03
(마을·대피소·요양시설 — 대피 대상 자동 산출) · FWS-U5-04(알림 규칙 · 야간
5분대기조 채널) · DSM-U5-01(운영·관리 방침 항목 관리) · DSM-U5-03(연계 설정).

1. **실제 구현**
   - `backend/apps/fws/api_admin.py`(조율자가 세운 빈 컨트롤러 `FwsAdminAPI` 에
     라우트 9개 추가, 전부 `/api/fws/admin/...` 접두어 — 이 App 의 다른 라우트
     전수에 첫 조각이 변수인 라우트가 0개라 삼킴이 없다).
   - `backend/apps/fws/admin_settings.py`(신규) — U5-01~04 의 업무 함수 전부.
     새 DB 표 0개(마이그레이션 파일도 0개) — 감사 로그(`logger.AuditLogs`)
     정본 판단을 그대로 따랐다(`patrol.py` 머리말과 같은 이유). 카메라
     산불 표식은 `stream_monitors.StreamMonitor`(기존 DSM 카메라 모델)를
     재사용하고 표식(고지대·PTZ 프리셋·열화상 채널·감시 반경 폴리곤)만
     감사 로그에 얹었다. U5-04 는 `kernels.k2_notify`(`notify_rule_overview`·
     `save_rule`·`send_test_notification`)를 그대로 위임 호출한다 — 새 저장을
     짓지 않았다.
   - `backend/apps/dsm/api_u5_an.py`(조율자가 세운 빈 컨트롤러 `DsmU5AnAPI` 에
     라우트 5개 추가, 전부 `/u5an/...` 접두어 — `api.py` 의 유일한 변수 조각
     `/settings/{domain}` 을 피하려고 처음부터 다른 리터럴을 골랐다).
   - `backend/apps/dsm/u5_an_service.py`(신규) — U5-01·03 의 업무 함수. 새 DB
     표 0개. 방침의 "보관 기간" 칸은 손으로 적지 않고 `apps.dsm.retention.
     retention_days()`(파기가 **실제로 보는** 값)를 그대로 읽어 완결조건
     ("보관 기간 = 파기 정책 값")을 어긋날 수 없게 만들었다. 연계 설정은
     끝점 이름·자격 **참조명**(`outbound_api_key_ref`)만 저장하고 값은 어디에도
     싣지 않으며, "연결 시험"은 설정 완결성만 보고 실제로 밖에 나가지 않는다
     (WO-17 지시서 §5 경계).
   - `frontend/src/features/fws/pages/AdminHome.tsx`(조율자가 세운 빈 화면을
     채움 · `DroneHome.tsx` 모양) · `frontend/src/features/fws/copy_admin.ts`
     (신규 사전, 공용 `copy.ts` 는 고치지 않았다). DSM 쪽 화면은 이 차선이
     만들지 않았다(§4 참고 — HTTP 실측만으로 P-356 ①을 만족한다고 판단).
2. **실측 증거** — `docs/agent/evidence/SPEC/FWS-U5-0{1,2,3,4}.json` ·
   `DSM-U5-0{1,3}.json` 6건, 전부 `backend/tests/test_fws_u5.py`·
   `test_dsm_u5_an.py` 의 pytest 실행이 **기계로** 찍었다(`measured_by:
   "django_test_client"`). 공용 `tests/test_fws_app.py::_write_evidence` 를
   그대로 재사용하고(고치지 않는다), 그 위에 이 턴의 새 요구(`title_parts`)를
   시험 파일 안의 `_add_title_parts` 헬퍼(증거 파일을 다시 열어 그 칸만 얹는다)
   로 채웠다 — 여섯 건 **전부** 빈 칸 0.
3. **게이트** — 새 게이트 `scripts/verify_spec_u5_an.py`(`verify_spec_fws_f6.py`
   의 판정식을 그대로 베꼈다 · `--self-test` 있음 · 경로 접두어를 `/api/fws/`·
   `/api/dsm/` 둘 다 허용하도록 넓혔다 · 이 여섯은 전부 이 턴의 것이므로
   `title_parts` 없음을 봐주지 않는다 — F6 게이트와 다른 처지).
4. **대장 이동** — 아래 §2 의 표를 `ga_readiness.yaml` 의 `kind_derived.
   annex_promoted.closed` 에 여섯 건 이어 붙이는 것을 제안한다.

## 1. 새로 연 라우트 아홉 + 다섯

### FWS `/api/fws/admin/...` (`FwsAdminAPI`, 이미 등록됨 — 새 등록 요청 없음)

| 메서드 | 경로 | 절 |
|---|---|---|
| GET | `/api/fws/admin/cameras` | FWS-U5-01 |
| GET | `/api/fws/admin/cameras/{int:camera_id}/fire-marker` | FWS-U5-01 |
| POST | `/api/fws/admin/cameras/{int:camera_id}/fire-marker` | FWS-U5-01 |
| POST | `/api/fws/admin/posts` | FWS-U5-02 |
| GET | `/api/fws/admin/posts` | FWS-U5-02 |
| POST | `/api/fws/admin/evac-targets` | FWS-U5-03 |
| GET | `/api/fws/admin/evac-targets` | FWS-U5-03 |
| GET | `/api/fws/admin/notify-rules` | FWS-U5-04 |
| POST | `/api/fws/admin/notify-rules` | FWS-U5-04 |
| POST | `/api/fws/admin/notify-rules/test` | FWS-U5-04 |

(표는 10행 — 위 §0 "라우트 9개"는 서로 다른 **경로**(path) 기준, 이 표는
메서드까지 가른 행 수다.)

### DSM `/api/dsm/u5an/...` (`DsmU5AnAPI`, 이미 등록됨 — 새 등록 요청 없음)

| 메서드 | 경로 | 절 |
|---|---|---|
| GET | `/api/dsm/u5an/privacy-policy` | DSM-U5-01 |
| POST | `/api/dsm/u5an/privacy-policy` | DSM-U5-01 |
| GET | `/api/dsm/u5an/integrations` | DSM-U5-03 |
| POST | `/api/dsm/u5an/integrations` | DSM-U5-03 |
| POST | `/api/dsm/u5an/integrations/test` | DSM-U5-03 |

## 2. 표 — 닫은 여섯 건

| id | 제목 | 엔드포인트 | 증거 |
|---|---|---|---|
| FWS-U5-01 | 산불 감시 카메라 등록(고지대·PTZ 프리셋·열화상 채널·감시 반경 폴리곤) | `GET/POST /api/fws/admin/cameras[/{id}/fire-marker]` | `evidence/SPEC/FWS-U5-01.json` |
| FWS-U5-02 | 초소·순찰함(NFC)·순찰 구역 | `POST/GET /api/fws/admin/posts` | `evidence/SPEC/FWS-U5-02.json` |
| FWS-U5-03 | 마을·대피소·요양시설 등록(대피 대상 자동 산출) | `POST/GET /api/fws/admin/evac-targets` | `evidence/SPEC/FWS-U5-03.json` |
| FWS-U5-04 | 산불 알림 규칙(등급별 수신: 진화대·산림과·지휘·산림청) · 야간 5분대기조 채널 | `GET/POST /api/fws/admin/notify-rules[/test]` | `evidence/SPEC/FWS-U5-04.json` |
| DSM-U5-01 | 운영·관리 방침 항목 관리 | `GET/POST /api/dsm/u5an/privacy-policy` | `evidence/SPEC/DSM-U5-01.json` |
| DSM-U5-03 | 연계 설정 — 스마트시티 통합플랫폼·112·119·NDMS | `GET/POST /api/dsm/u5an/integrations[/test]` | `evidence/SPEC/DSM-U5-03.json` |

프런트: `frontend/src/features/fws/pages/AdminHome.tsx`(`/fws/admin` · 조율자가
세운 빈 화면에 이 차선이 채움) · `frontend/src/features/fws/copy_admin.ts`(이
차선 소유 신규 사전 · 공용 `copy.ts` 는 고치지 않았다). 서버 호출은 기존
`features/fws/api.ts` 의 `fwsGet`/`fwsPostQuery` 함수만 썼다(그 파일은 고치지
않았다) — 경로 문자열은 화면이 직접 든다.

## 3. 「제목이 부르는 것 ↔ 있는 것」 (절마다 요약 — 전체 표는 각 evidence json 의 `title_parts`)

**FWS-U5-01** 산불 감시 카메라 등록

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 고지대 | 있음 — `is_highland` |
| PTZ 프리셋 | 있음 — `ptz_presets`(쉼표 문자열 → 목록) |
| 열화상 채널 | 있음 — `thermal_channel` |
| 감시 반경 폴리곤 | 있음(값만) — `radius_polygon`(좌표 배열 JSON). 폴리곤 **판정**(안/밖)은 짓지 않았다 — `drone.py::submit_hotspots` 와 같은 한계(값만 오간다) |
| 카메라 등록 자체 | **기존 문 재사용** — `stream_monitors.StreamMonitor`(DSM `/cameras/import`) 그대로, 새 표를 만들지 않았다 |

**FWS-U5-02** 초소·순찰함(NFC)·순찰 구역

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 초소 | 있음 — `post_code`/`name` |
| 순찰함(NFC) | 있음 — `nfc_boxes`(코드 목록) |
| 순찰 구역 | 있음 — `patrol_zone` |
| 조직 전체 공유 | **본인 등록만**(감사 표에 테넌트 칼럼이 없다 · `patrol.py`·`standby.py` 와 같은 한계 — annex U5 는 "정보통신과 담당" 한 자리를 전제하므로 실사용 영향은 제한적이라고 판단, 정직하게 명시) |

**FWS-U5-03** 마을·대피소·요양시설

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 마을 | 있음 — `kind=village` |
| 대피소 | 있음 — `kind=shelter` |
| 요양시설 | 있음 — `kind=care_facility` |
| 대피 대상 자동 산출 | 있음 — `evacuee_target_total`(합계 칸을 손으로 두지 않고 등록값을 더해서 낸다) |

**FWS-U5-04** 산불 알림 규칙 · 야간 5분대기조 채널

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 등급별 수신 | 있음 — K2 `NotificationRule`(등급×역할×채널) 그대로 재사용 |
| 진화대·산림과·지휘·산림청 | 있음(제안) — `role_suggestions`(role_code 4개). 자유 문자열이라 그 이름의 역할이 실재해야 저장이 통과한다(강제 아님 · 제안) |
| 야간 5분대기조 채널 | 있음 — `zone=fws_night_standby` 로 같은 역할의 주간/야간 규칙을 가른다 |

**DSM-U5-01** 운영·관리 방침 항목 관리

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 설치 목적·위치·촬영 범위·관리책임자·접근권한자·촬영 시간·열람 절차 | 있음 — 관리자가 적는 7칸 |
| 대수 | 있음(실측) — `installed_camera_count`(손으로 안 적는다, `StreamMonitor` 실count) |
| 보관 기간 | 있음(실측) — `retention_days`(`apps.dsm.retention.retention_days()` 그대로, 완결조건 "= 파기 정책 값"을 어긋날 수 없게 함) |
| 방침 문서 자동 생성 | **부분** — 텍스트 한 장(`document_text`)은 자동 생성한다. **PDF 조판은 없다**(annex 출력란의 "방침 PDF"는 K4 서식·페이지 나누기가 필요해 범위 밖) — §4 「무엇이 없는가」에 남긴다. 완결조건 자체("보관 기간 = 파기 정책 값")는 PDF 를 요구하지 않으므로 절은 닫힌 것으로 판단했다 |

**DSM-U5-03** 연계 설정

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 스마트시티 통합플랫폼·112·119·NDMS | 있음 — 네 서비스 전부 목록에 있다 |
| 엔드포인트 | 있음 — `endpoint_name` |
| 자격 참조명 | 있음 — `outbound_api_key_ref`(이름만, 값은 어디에도 없다) |
| 연결 시험 | 있음(범위를 좁혀) — 설정 완결성만 본다. **실제 핸드셰이크는 하지 않는다**(WO-17 §5 경계 — 외부 호출 금지) |
| 상태 한 단어 | 있음 — `status` ∈ {정상, 대기, 끊김} |

## 4. 「무엇이 없는가」— 반쪽으로 올리지 않은 것

- **DSM-U5-01 의 "방침 PDF"** — 텍스트 문서 자동 생성까지만 있고 PDF 조판은
  없다(K4 서식·글꼴·페이지 나누기가 필요한 별도 작업). 완결조건이 PDF 를
  요구하지 않으므로 절 자체는 닫힌 것으로 남기되, 이 한 조각만 비어 있음을
  숨기지 않는다(`title_parts` 에 `status: "partial"` 로 명시).
- **FWS-U5-02 의 "조직 전체 공유"** — 감사 로그를 정본으로 쓰는 한 등록한
  사람 자신의 값만 보인다. annex 가 U5 를 "정보통신과 담당 또는 관제센터
  운영 담당" 한 자리로 그리므로 실사용 영향은 제한적이라 판단해 절은 닫았다.

## 5. 하지 않음(P-358) — annex 원문 대조

- **FWS-U5-05 오탐 필터 모델 활성(안개·소각 시간대·계절)** — AI 판별 모델이
  이 저장소 어디에도 없다(모델 학습·추론 파이프라인은 L 규모 · 대표 승인이
  필요한 별도 사업). "저장은 되는데 아무 일도 안 하는 스위치"를 짓지 않는다
  (지어내지 않는다).
- **DSM-U5-04 임계값 소스 등록(하천 수위계·강우량계)** — 차선 배정표 밖(WO-17
  지시서가 이 차선에 맡긴 것은 U5-01·U5-03 둘뿐이다). `kernels.k5_trust` 의
  기존 임계값 표와 맞물린 별도 차선 몫.
- **O-03 라이선스·계량·청구** — 사업 결정(가격 정책)이 먼저 서야 하는 L 규모
  절이고 이 차선의 앱 범위와 무관하다.

## 6. 제안 YAML — `kind_derived.annex_promoted.closed` 에 여섯 건 이어 붙이기

```yaml
# docs/agent/evidence/D-346/ga_readiness.yaml :: areas[id=="1"].kind_derived.annex_promoted 안에 추가 제안
kind_derived:
  annex_promoted:
    closed:
      - FWS-U5-01
      - FWS-U5-02
      - FWS-U5-03
      - FWS-U5-04
      - DSM-U5-01
      - DSM-U5-03

kind_evidence:
  FWS-U5-01:
    title: 산불 감시 카메라 등록(고지대·PTZ 프리셋·열화상 채널·감시 반경 폴리곤)
    status: closed
    kind: measured
    gate: scripts/verify_spec_u5_an.py
    proof: docs/agent/evidence/SPEC/FWS-U5-01.json
    rows: [tests.test_fws_u5.U5_01_CameraFireMarkerTest.test_save_and_reread_carries_every_named_part]
    strength: change
    measured_at: "2026-09-29T00:00:00Z"
    what: |
      기존 DSM 카메라 모델(StreamMonitor)을 재사용하고 산불 표식(고지대·PTZ
      프리셋·열화상 채널·감시 반경 폴리곤)을 저장·재조회·목록 세 곳에서 실측했다.

  FWS-U5-02:
    title: 초소·순찰함(NFC)·순찰 구역
    status: closed
    kind: measured
    gate: scripts/verify_spec_u5_an.py
    proof: docs/agent/evidence/SPEC/FWS-U5-02.json
    rows: [tests.test_fws_u5.U5_02_PostRegistryTest.test_register_then_list_shows_the_same_post]
    strength: change
    measured_at: "2026-09-29T00:00:00Z"
    capture_none_why: |
      감사 표에 테넌트 칼럼이 없어 등록한 사람 자신의 값만 낸다(patrol.py·
      standby.py 와 같은 한계).
    what: |
      초소 이름·순찰 구역·순찰함(NFC) 코드를 등록한 뒤 목록에 그대로 보인다.

  FWS-U5-03:
    title: 마을·대피소·요양시설 등록(대피 대상 자동 산출)
    status: closed
    kind: measured
    gate: scripts/verify_spec_u5_an.py
    proof: docs/agent/evidence/SPEC/FWS-U5-03.json
    rows: [tests.test_fws_u5.U5_03_EvacTargetsTest.test_registering_villages_and_shelters_auto_computes_targets]
    strength: change
    measured_at: "2026-09-29T00:00:00Z"
    what: |
      마을·요양시설·대피소 셋을 등록하면 합계 칸 없이 headcount 를 더해 대피
      대상 총원을 자동 산출한다(312+41=353).

  FWS-U5-04:
    title: 산불 알림 규칙(등급별 수신: 진화대·산림과·지휘·산림청) · 야간 5분대기조 채널
    status: closed
    kind: measured
    gate: scripts/verify_spec_u5_an.py
    proof: docs/agent/evidence/SPEC/FWS-U5-04.json
    rows: [tests.test_fws_u5.U5_04_NotifyRulesTest.test_overview_lists_role_suggestions_and_night_standby_zone,
           tests.test_fws_u5.U5_04_NotifyRulesTest.test_save_a_night_standby_rule_then_it_appears_in_overview]
    strength: reflect
    measured_at: "2026-09-29T00:00:00Z"
    what: |
      K2 rule_admin(notify_rule_overview/save_rule/send_test_notification)을
      그대로 재사용하며 진화대·산림과·지휘·산림청 역할 제안과 야간 5분대기조
      구역(zone=fws_night_standby) 분리를 실측했다.

  DSM-U5-01:
    title: 운영·관리 방침 항목 관리
    status: closed
    kind: measured
    gate: scripts/verify_spec_u5_an.py
    proof: docs/agent/evidence/SPEC/DSM-U5-01.json
    rows: [tests.test_dsm_u5_an.U5_01_PrivacyPolicyTest.test_save_reread_and_retention_matches_destruction_policy]
    strength: change
    measured_at: "2026-09-29T00:00:00Z"
    capture_none_why: |
      방침 문서는 텍스트로만 자동 생성한다 — PDF 조판(K4 서식)은 범위 밖.
    what: |
      항목 7칸 저장·재조회 + 카메라 대수 실측 + 보관 기간이 apps.dsm.retention.
      retention_days() 와 정확히 같음을 실측(완결조건).

  DSM-U5-03:
    title: 연계 설정 — 스마트시티 통합플랫폼·112·119·NDMS
    status: closed
    kind: measured
    gate: scripts/verify_spec_u5_an.py
    proof: docs/agent/evidence/SPEC/DSM-U5-03.json
    rows: [tests.test_dsm_u5_an.U5_03_IntegrationsTest.test_save_test_and_status_word_progression]
    strength: change
    measured_at: "2026-09-29T00:00:00Z"
    capture_none_why: |
      연결 시험은 설정 완결성만 본다 — 실제 핸드셰이크는 WO-17 §5 경계 밖.
    what: |
      네 서비스 목록 · 끝점 이름·자격 참조명 저장(값 아님) · 상태 단어가
      끊김→대기→정상으로 실제로 바뀌는 것을 실측.
```

## 7. 게이트·시험 재실행 결과

`python scripts/verify_spec_u5_an.py --self-test` → **19/19 통과 · 자기시험 0건
실패**(빈 title_parts·빈 칸 셀·5xx 응답·다른 App 경로·id 불일치·title_parts
자체 없음 표본을 스스로 망가뜨려 빨강을 확인 — 이 게이트는 F6 게이트와 달리
title_parts 없음도 빨강으로 잡는다).

gx-shell 안에서 확인한 pytest 실측(DB `test_gx_lane_n4`, `-p no:randomly`):

    tests/test_fws_u5.py       10 passed, 35 warnings in 185.33s (0:03:05)
    tests/test_dsm_u5_an.py     6 passed, 35 warnings in 183.87s (0:03:03)

(경고는 pydantic/ninja 전역 deprecation + teardown 시 DB 동시 접속 경고뿐 —
이 차선 코드가 새로 낸 오류가 아니다.)

`python scripts/verify_spec_u5_an.py --no-run` → **닫은 열 6/6 · PASS**.

## 8. F-05 잠금·계층 확인

- `kernels.k1_event` 를 `apps/fws/admin_settings.py`·`apps/dsm/u5_an_service.py`
  어느 쪽도 직접 import 하지 않는다(grep 확인 — 이 두 파일에 그 이름이 없다).
  이 여섯 절은 애초에 이벤트를 만지지 않는다(설정 값만 다룬다).
- `apps/fws/admin_settings.py` 는 `stream_monitors.models.StreamMonitor` 를
  직접 import 한다 — `apps/dsm/api_u56.py::_one_camera`/`set_camera_address` 가
  이미 같은 자리를 같은 방식으로 만지는 전례를 그대로 따랐다(`stream_monitors`
  는 `backend/apps/` 밖이라 D-278 계층 게이트(`scripts/verify_layers.py`)가
  막지 않는다).
- 새 DB 표 0개 — 마이그레이션 파일도 0개.
