# N4 승격 제안 — DSM-U3-01·U3-02·U6-01·U6-03
(턴 AO · WO-GX-20260930-18 §N4 · P-356·358·392 · 차선 N4)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다(§0.4 하드룰).

## 0. 배정과 실측이 갈린 자리 — 먼저 적는다

지시서는 "DSM-U4 잔여 중 S 크기(DSM-U4-02·05·08·09 중 S 인 것)"도 이 넷과 함께
닫으라고 했다. **미포함표(`기능명세_미포함표_20260925.md` 98·103·106·107행)를
실측하니 넷 다 "M" 이고 "S" 는 0건이었다.** 그래서 이 문서가 P-356 넷으로 닫는
절은 아래 **넷뿐**이다 — 목표(닫은 절 ≥ 5)에 하나 못 미친다. 지어내지 않고 그대로
적는다(배정 문장의 조건절 "중 S 인 것"이 빈 집합이었다는 사실 자체가 이 차선의
실측 결과다).

## 1. 승격 규칙(P-356) 적용 요약

**닫은 넷**이 넷(구현·증거·게이트 행·승격 제안)을 다 갖췄다고 이 차선이 주장한다:
DSM-U3-01(역할별 M2 문안) · DSM-U3-02(통제 실행 회신) · DSM-U6-01(스마트시티
통합플랫폼 이벤트 연계 — 112·119·재난상황 긴급대응·CAP 1.2) · DSM-U6-03(사회적약자
실종 요청 수신 → 객체 검색 사건 생성).

1. **실제 구현**
   - `backend/apps/dsm/api_u36_an.py`(조율자가 세운 빈 컨트롤러 `DsmU36AnAPI` 에
     라우트 넷 추가 — `GET /events/{id}/m2-brief` · `POST /controls/{id}/executed` ·
     `POST /external-events` · `POST /search-requests`. 넷 다 기존 12개 컨트롤러
     파일의 리터럴·변수 조각 전수와 안 겹친다[실측 grep — 최종 보고 §라우트 참고]).
   - `backend/apps/dsm/u36_an_service.py`(신규) — 넷의 업무 함수 전부. 새 DB 표
     **0개**(마이그레이션 파일도 0개).
     - U3-01: `M2_PHRASE_TABLE`(역할×유형 문안, 파이썬 상수 dict — 명세 원문
       "역할 × 유형 문안 표"를 그대로 짓는다. 명세 예시 "시설 담당 「도로 통제
       후 회신」"이 시험의 문자열 대조 그 자체다).
     - U3-02: **로직 0줄** — `apps/dsm/control_board_service.py`(턴 AM·N4 가
       지었고 턴 AN·N1 이 이어받은 파일)의 `advance(stage="실행")` 를 새 리터럴
       `/controls/{id}/executed` 로 여는 것뿐이다. U4-04(통제·대피 현황판, 턴
       AN 에 닫힘)가 이미 「도달→결정→실행→해제」 4단계 순서를 판정하고 있어
       완결조건("도달→결정→실행 3시각")이 **U4-04 의 기존 상태 기계를 그대로
       탄다**(두 번째 판정식을 짓지 않았다).
     - U6-01: 서명(`common/webhook_contract.verify` — SEC-16 규약을 그대로
       재사용, 새 판정식 0개) + `settings.EXTERNAL_EVENT_SIGNING_KEYS`(신규,
       `WEBHOOK_SIGNING_KEYS` 와 **같은 파서**(`_parse_webhook_signing_keys`)
       재사용 · 방향은 반대 — 상대가 우리에게 보내는 값이라 우리가 만들지
       않는다) + `data_source=external` 표식(`track_id` 위, `common/
       probe_marker.py` 의 probe·drill 과 **같은 자리 다른 낱말** — 그 공용
       파일은 고치지 않았다).
     - U6-03: **재식별(용모 기반 객체 검색) AI 는 짓지 않는다** — 이 저장소
       어디에도 그 능력이 없다(턴 AN `N1_promotions.md` §DSM-U6-03 실측:
       "「객체 검색」 능력이 제품 어디에도 없다"). 완결조건이 글자 그대로
       요구하는 "요청 → 사건 1"만 닫는다: 요청을 받아 K1 경로로 사건 하나를
       남기고(제품은 CCTV 통합관제이지 재식별 엔진이 아니다 — 사람이 카메라로
       찾는다), 감사 한 줄(`apps.dsm.audit.record_event_action`)을 더해
       "재식별 검색"이라는 이름이 약속하지 않는 능력을 감추지 않는다.
   - `backend/apps/dsm/services.py`(+34줄, 함수 하나 `record_external_event`
     추가) — **F-05 잠금을 지키기 위해 불가피했다.** `kernels.k1_event` 를
     App 에서 직접 부를 수 있는 곳은 이 파일 하나뿐이고(`test_f05_event_api.py::
     EntrySurfaceIsOneTest`), 사건 생성 래퍼가 그 파일에 없었다. 기존 함수들과
     같은 모양(얇은 래퍼, 규칙 없음)으로 하나만 더했다 — **공용 파일이지만
     조율자 소유 넷(§규약 목록)에는 없다.** 다른 차선이 같은 파일을 건드리면
     병합 때 조율자가 봐야 한다(최종 보고 §4).
   - `backend/config/settings.py`(+16줄) — `EXTERNAL_EVENT_SIGNING_KEYS` 추가
     (`WEBHOOK_SIGNING_KEYS` 바로 아래, 같은 파서 재사용). 이것도 공용 파일이라
     병합 시 확인이 필요하다(최종 보고 §4).
2. **실측 증거** — `docs/agent/evidence/SPEC/DSM-U3-01.json` · `DSM-U3-02.json` ·
   `DSM-U6-01.json` · `DSM-U6-03.json` 넷, 전부 `backend/tests/test_dsm_u36_an.py`
   의 pytest 실행이 **기계로** 찍었다(`measured_by: "django_test_client"`).
   공용 `tests/test_fws_app.py::_write_evidence` 를 그대로 재사용하고(고치지
   않는다), `title_parts`는 시험 파일 안의 `_add_title_parts` 헬퍼(증거 파일을
   다시 열어 그 칸만 얹는다)로 채웠다 — 넷 **전부** 빈 칸 0.
3. **게이트** — 새 게이트 `scripts/verify_spec_dsm_u36.py`(`verify_spec_u5_an.py`
   의 판정식을 그대로 베꼈다 · `--self-test` 있음 · 자기시험 0건 실패 ·
   `--no-run` 실측 결과 **닫은 열 4/4 · 최종 PASS**). 짝 `backend/tests/
   test_dsm_u36_gate_can_fail.py`(`TheSelfTestCanFail` 셋 — 자기시험을 몸소
   망가뜨려 1을 본다).
4. **대장 이동** — 아래 §2 의 표를 `ga_readiness.yaml` 의 `kind_derived.
   annex_promoted.closed` 에 넷 이어 붙이는 것을 제안한다.

## 2. 절 표

| id | 제목(명세 원문) | 증거 | 게이트 |
|---|---|---|---|
| DSM-U3-01 | 역할별 M2 문안 | `evidence/SPEC/DSM-U3-01.json` | `verify_spec_dsm_u36.py` |
| DSM-U3-02 | 통제 실행 회신 | `evidence/SPEC/DSM-U3-02.json` | `verify_spec_dsm_u36.py` |
| DSM-U6-01 | 스마트시티 통합플랫폼 이벤트 연계(112·119·재난상황 긴급대응·CAP 1.2) | `evidence/SPEC/DSM-U6-01.json` | `verify_spec_dsm_u36.py` |
| DSM-U6-03 | 사회적약자(실종) 요청 수신 → 객체 검색 사건 생성 | `evidence/SPEC/DSM-U6-03.json` | `verify_spec_dsm_u36.py` |

## 3. 못 닫은 것 — 무엇이 없는가

- **DSM-U4-02·05·08·09** — 배정 조건("S 크기") 자체가 이 넷 중 0건이었다(전부
  미포함표에서 "M"). §0 참고. 지어내지 않는다.
- **DSM-U6-02**(NDMS 내보내기, L) — 이 차선의 배정 밖(WO-18 이 이 차선에 맡긴
  것은 U3-01·U3-02·U6-01·U6-03 넷뿐이다).

## 4. 조율자에게 넘기는 것 (최종 보고 §4 와 중복 — 여기 다시 적는다)

1. `backend/tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE` 에 아래 넷을 추가:
   - `("GET", "/api/dsm/events/{int:event_id}/m2-brief")`
   - `("POST", "/api/dsm/controls/{int:point_id}/executed")`
   - `("POST", "/api/dsm/external-events")`
   - `("POST", "/api/dsm/search-requests")`
   실측[턴 AO 끝 시점]: `test_the_entry_surface_is_pinned_by_name` 를 돌리면 이
   넷 **말고도** 다른 차선(N1·N3 로 보이는 `/ops/*`·`/video-access-requests/
   annual-stats`)이 늘려 둔 줄이 함께 잡힌다 — 이 차선이 만든 것은 이 넷뿐이다.
2. `backend/apps/dsm/services.py`·`backend/config/settings.py` — 공용 파일에
   각각 함수 하나·설정 하나를 더했다(§1 참고). 다른 차선이 같은 파일을 같은
   턴에 고쳤으면 병합 시 확인이 필요하다.
3. `scripts/_gate_header.py::SELF_TEST_LINKS` 에 `verify_spec_dsm_u36.py` →
   `tests/test_dsm_u36_gate_can_fail.py` 등록 줄.
