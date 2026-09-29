# N1 승격 제안 — 반쪽 여섯 채우기(DSM-U4-03·04·07·U5-05 · FWS-F6-07)
(턴 AN · WO-GX-20260929-17 · P-392 「반쪽 여섯 채우기」 · 차선 N1)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다.

## 0. 배정과 결과 — 「반쪽 여섯」 중 다섯 닫음 · 하나는 결정으로 남김

턴 AM(WO-GX-20260928-16 보고 §2)이 코드는 커밋했지만 제목의 일부가 모자라
승격(대장 이동)을 하지 않았던 여섯: DSM-U4-01(HWPX) · U4-03(표준 문안) ·
U4-04(일일보고 반영) · U4-07(가림 처리) · U5-05(일지 근무자=편성표) ·
FWS-F6-07(앱 푸시 연계). 이 차선(N1)이 지시받은 순서대로:

1. **DSM-U4-04 일일보고 반영** → 채움(`control_board_service.daily_reflection`)
2. **DSM-U4-03 표준 문안** → 채움(`u4_regulations.CBS_STANDARD_TEMPLATE` · 자동 생성)
3. **DSM-U4-07 가림 처리** → 채움(`mask_jpeg` 실제 파이프라인 실행)
4. **DSM-U5-05 교대 편성** → **부분** 채움(근무자 자동 조회는 섰다 · 인계 메모·
   일지 반영은 여전히 못 닫음 — §2 참고)
5. **FWS-F6-07** → 채움(웹푸시 훈련 채널 · 세종 판정대로 실발송 없이)
6. **DSM-U4-01(HWPX)** → **채우지 않는다**(결정 ⑤ 「안 산다」) — §5 참고

**닫은 절 다섯**(P-356 넷을 모두 갖췄다고 이 차선이 주장하는 것):
DSM-U4-03·04·07·U5-05(전부 부분 승격 — 완결조건 일부는 여전히 없다, 아래 §2에
「무엇이 없는가」로 남긴다) · FWS-F6-07(대체 — 웹푸시 훈련 채널). 목표(5) 달성.

## 1. 표 — 닫은 다섯 건

| id | 제목 | 엔드포인트(신규) | 증거 | 게이트 |
|---|---|---|---|---|
| DSM-U4-03 | 재난문자(CBS) 초안 — 표준 문안 자동 생성 | `POST /api/dsm/cbs-drafts`(message 비우면 자동) | `evidence/SPEC/DSM-U4-03.json` | `scripts/verify_spec_dsm_u4.py` |
| DSM-U4-04 | 통제·대피 현황판 — 일일보고 자동 반영 | `GET /api/dsm/control-points/daily-report` | `evidence/SPEC/DSM-U4-04.json` | `scripts/verify_spec_dsm_u4.py` |
| DSM-U4-07 | 영상 열람·제공 대장 — 실제 마스킹 실행 | `POST /api/dsm/video-access-requests/{id}/provide`(image_b64) | `evidence/SPEC/DSM-U4-07.json` | `scripts/verify_spec_dsm_u4.py` |
| DSM-U5-05 | 교대 편성 — 근무자 자동 조회 | `GET /api/dsm/shifts/on-duty` | `evidence/SPEC/DSM-U5-05.json` | `scripts/verify_spec_dsm_u4.py` |
| FWS-F6-07 | 대피 앱 푸시 연계 — 웹푸시 훈련 채널 | `POST /api/fws/liaison/fire-events/{id}/evacuation-webpush-drill`(★ 미등록 — §4) | `evidence/SPEC/FWS-F6-07.json`(title_parts 보강) | `scripts/verify_spec_fws_f6.py` |

새 표 0개 · 새 마이그레이션 0개 — 전부 기존 감사 이력(`common.audit_writer`) 위에
서거나(DSM 넷), 기존 감사·커널 재사용(F6-07 — `kernels.k2_notify.send_webpush`)
위에 섰다.

## 2. 「제목이 부르는 것 ↔ 있는 것」(요약 — 전체 표는 각 evidence json 의 `title_parts`)

**DSM-U4-03** 재난문자(CBS) 초안 — 이번 턴에 **완전히** 닫혔다(빠졌던 부분만
있던 것 → title_parts 7행 전부 「있음」).

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 표준 문안(자동 생성) | [신규] `u4_regulations.CBS_STANDARD_TEMPLATE[kind]` 가 구역명 하나만 채워 자동 생성 — `message` 를 비워 보내면 켜진다. 사람 글이 있으면 그 글이 이긴다 |
| 나머지 여섯(유형·구역·글자수·승인·발송 배제·발송기록·야간경고) | 턴 AM 이 이미 닫았다(변경 없음) |

**DSM-U4-04** 통제·대피 현황판 — 완전히 닫혔다.

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 일일보고 자동 반영 | [신규] `GET /control-points/daily-report` — 통제 현황을 사람이 다시 안 세고 기준시각·단계별 집계·지점 목록으로 자동 접어 낸다. **U4-05(06:00 자동 배치·HWPX 출력) 자체는 여전히 범위 밖** — 이 함수는 그 배치가 삼킬 자료만 낸다 |
| 나머지 다섯 | 턴 AM 이 이미 닫았다 |

**DSM-U4-07** 영상 열람·제공(반출) 대장 — 「가림 처리」는 닫혔다, 「연간 통계」는
여전히 없다(이번 배정 밖).

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 마스킹본 제공(가림 처리) | [신규] `provide(image_b64=...)` 가 `apps.dsm.privacy_request.mask_jpeg`(LAW-07 의 순수 함수 재사용 — 그 파일은 고치지 않았다)를 실제로 돌린다. 결과·원본 바이트는 안 남기고 해시(앞 12자)·크기만 남는다 — 「가렸다」 주장이 아니라 「원본≠결과」 실측 |
| 연간 통계(출력) | **없음** — 목록 조회만 있고 연간 집계 배치는 없다(이번 배정 밖 · 별도 절 규모) |

**DSM-U5-05** 교대 편성 — **가장 좁은 부분 승격**(달라지지 않음, 안쪽 사실 하나만
새로 섰다).

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 근무자 자동 조회(핵심 사실) | [신규] `GET /shifts/on-duty` — 편성표에서 조별 근무자를 사람이 다시 안 옮기고 구조화해 낸다(주간/야간/비번의 시각 경계는 명세서에 없어 지어내지 않았다 — `date` 하루치를 그대로 낸다) |
| 인계 메모 근무자 자동 | **부분** — 자동 조회 함수는 섰으나 `handover_service.py`(다른 차선 소유 · 이 턴도 고치지 않는다)에 잇는 한 줄이 아직 없다 — §4 조율자 전달 |
| 일지 근무자 자동 | **없음** — 관제일지(DSM-U1-04) 자체가 이 저장소 어디에도 없다(훨씬 큰 별도 절 — 이 배정 밖) |
| 완결조건 「일지 근무자 = 편성표」 | **미달성** — 위 두 이유로 완결조건 자체를 못 채웠다. ⚠ 조율자 확인 요청(N4 가 턴 AM 에 이미 같은 질문을 남겼다): 완결조건이 없는 이 절을 「부분 승격」으로 계속 인정할지, 아니면 `annex_2_spec.clauses` 에 그대로 둘지 판단 부탁 |

**FWS-F6-07** 스마트산림재난 앱 대피 푸시 연계 — 세종 판정대로 대체 경로로 닫혔다.

| 제목이 부르는 것 | 있는 것 |
|---|---|
| 앱 푸시 연계 | [신규] 산림청 실제 앱 푸시는 여전히 [미확인]이라 안 연다 — **웹푸시 훈련 채널**(`kernels.k2_notify.send_webpush`)로 잇는다. 제목은 언제나 `[훈련]`로 시작 · `send_webpush` 자체 규약으로 발송 이력이 항상 `drill:` 표식(5분 억제·통계에 안 잡힘) — 실발송 아님 |
| 문자 초안(CBS) | 그대로 둔다(변경 없음) — 웹푸시는 그 옆에 새로 여는 자리다 |

## 3. 제안 YAML — DSM 넷은 이동, FWS 하나는 title_parts 보강

### ③-1 `annex_2_spec.clauses` → `areas[id=="7"].clauses` (N4_promotions.md 의 제안을 잇는다)

턴 AM(N4)이 이미 DSM-U4-01·03·04·07·U5-05 다섯을 area "7"로 옮기자고 제안했었다
(§`docs/agent/evidence/SPEC/N4_promotions.md`). 이 턴은 그중 **U4-01 을 뺀 넷**만
옮기자고 다시 제안한다 — U4-01 은 결정 ⑤(§5)로 이번에도 안 닫혔다.

```yaml
      - id: DSM-U4-03
        title: 재난문자(CBS) 초안(유형·구역·글자수·승인·발송기록·야간경고·
          표준 문안 자동 생성 — 전부 있음. [턴 AN] 표준 문안 자동 생성 채움)
        status: 구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/cbs_draft_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U4-03.json

      - id: DSM-U4-04
        title: 통제·대피 현황판(통제개소·4시각·대피인원장소·현황판·일일보고
          자동 반영 — 전부 있음. [턴 AN] 일일보고 자동 반영 채움. U4-05 의
          06:00 자동 배치·HWPX 출력 자체는 별도 절)
        status: 부분구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/control_board_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U4-04.json

      - id: DSM-U4-07
        title: 영상 열람·제공(반출) 대장(요청·승인·제공기록·원본반출0·실제
          마스킹 파이프라인 실행 있음. [턴 AN] 마스킹 실행 채움. 연간 통계는
          미착수)
        status: 부분구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/video_access_ledger_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U4-07.json

      - id: DSM-U5-05
        title: 교대 편성 CSV(부분 — CSV 업로드·저장·조회 표·근무자 자동 조회
          있음. [턴 AN] 근무자 자동 조회 채움. 인계메모 연결·일지 자체는 미착수
          — 완결조건 자체 미달성. 조율자 인정 여부 확인 요)
        status: 부분구현
        kind: closed_partial
        gate: scripts/verify_spec_dsm_u4.py
        proof: backend/apps/dsm/shift_roster_service.py
        evidence: docs/agent/evidence/SPEC/DSM-U5-05.json
```

`annex_2_spec.clauses` 에서 위 넷을 지운다(DSM-U4-01 은 그대로 둔다 — §5).

### ③-2 FWS-F6-07 — 이미 있는 자리(`kind_derived.annex_promoted.closed`)의 항목을 갱신

F6-07 은 턴 AM(N3)이 이미 `kind_derived.annex_promoted.closed` 로 이동을
제안했었다(§`N3_promotions.md`) — 다만 「앱 푸시 연계」가 없어 조율자가 대장에
아직 안 올린 것으로 보인다(WO-GX-20260928-16 보고 §2). 이 턴은 같은 자리에
**title_parts 만 보강**해 다시 올린다(그 항목이 `ga_readiness.yaml` 에 아직
없다면 §`N3_promotions.md` 의 YAML 그대로 올리고, `evidence` 파일은 그대로
`docs/agent/evidence/SPEC/FWS-F6-07.json`을 가리키면 title_parts 를 포함해 온다
— 파일 경로가 안 바뀌므로 별도 YAML 조각이 필요 없다).

## 4. 조율자에게 넘길 줄

- **`backend/apps/fws/urls.py`**(공용 파일 · 이 차선이 고치지 않음) — 새 컨트롤러
  `backend/apps/fws/api_n1.py::FwsN1API` 를 등록해 주십시오:
  ```python
  from apps.fws.api_n1 import FwsN1API
  # ...
  fws_api.register_controllers(FwsOfficeAPI, FwsOffice2API, FwsAdminAPI, FwsN1API)
  ```
  등록 전까지 `POST /api/fws/liaison/fire-events/{id}/evacuation-webpush-drill`
  은 실제 서비스에서 열리지 않는다 — 이 차선의 시험(`test_an_n1_f6_07_webpush.py`)
  은 이 파일 스스로가 마운트하는 임시 URLconf(`override_settings(ROOT_URLCONF=
  __name__)`)로 쟀다(가짜 Mock 요청이 아니라 진짜 Django `Client`·미들웨어·
  `@tenant_scoped`·`@idempotent` 전부가 돈다).
- **`backend/apps/dsm/handover_service.py`**(다른 차선 소유 · 이 턴이 고치지
  않음) — `shift_roster_service.current_workers(scope=..., date=...)` 를 인계
  메모 초안에 한 줄 이어 주시면 DSM-U5-05 의 「인계 메모 근무자 자동」이 닫힙니다.
- **`kernels/k2_notify/webpush.py`**(이 차선 소유 아님) — `WebPushNotConfigured.
  __init__` 가 `_init__`(밑줄 하나)로 오타나 있어 `missing_env` 가 실제로는 절대
  채워지지 않습니다(항상 부모 `Exception.__init__` 로 떨어짐). 이 차선은
  `api_n1.py` 에서 `getattr(exc, 'missing_env', [])` 로 방어했지만, 원래 의도
  (503 본문에 이름 목록)는 그 오타를 고쳐야 삽니다.
- **`ga_readiness.yaml` 대장 이동** — §3 참고.
- 새 `/api/dsm/` 라우트 셋(`control-points/daily-report` · `shifts/on-duty`) —
  `backend/tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE`(조율자 소유)에
  올려 주십시오. 새 `/api/fws/` 라우트(`evacuation-webpush-drill`)도 등록되면
  같은 표에 올라갈 필요가 있는지 확인 부탁드립니다(F6 문들이 이미 그 표에
  있는지 이 차선은 확인하지 못했다 — F-05 잠금은 지켰습니다: `apps.dsm.services`
  만 거칩니다).

## 5. DSM-U4-01(HWPX) — 채우지 않는다(결정 ⑤)

명세 제목이 부르는 「HWPX/PDF」 산출물은 이번 턴도 짓지 않는다. 사유 한 줄
(`docs/agent/evidence/SPEC/DSM-U4-01.json` 의 `decision_note`, `scripts/
verify_spec_dsm_u4.py::NOT_STARTED["DSM-U4-01"]` 에 같은 문구): **DOCX 가
정본**(`api_u24.py::situation_report_docx`)이고, HWPX(한글과컴퓨터 OWPML)는
새 의존성이라 **v1.2 옵션**으로 미룬다 — **출시 뒤** 수요가 있으면 그때 표
후보로 다시 올린다. 채번 대장 자체(제N보 채번·최초/중간/최종 구분·발송기록·
경과분 계산)는 여전히 서 있다 — 이 절이 안 닫힌 이유는 HWPX 하나뿐이다.
이 결정에 따라 `scripts/verify_spec_dsm_u4.py::CLOSED_CLAUSES` 에서
DSM-U4-01 을 빼고 `NOT_STARTED` 로 옮겼다(예전엔 title_parts 없이 「부분
승격」을 자칭했었다 — 이번 턴부터 title_parts 없는 절은 닫힌 열로 세지 않는다).

## 6. 게이트·시험 재현

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n1 -w /app gx-shell \
  python -m pytest tests/test_p356_u4_rest_spec_promotions.py -q --create-db -p no:randomly
# → 33 passed in 243.50s

MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n1 -w /app gx-shell \
  python -m pytest tests/test_an_n1_f6_07_webpush.py -q --create-db -p no:randomly
# → 3 passed in 196.88s

python scripts/verify_spec_dsm_u4.py --self-test   # 0건 실패
python scripts/verify_spec_dsm_u4.py --no-run       # 닫은 열 4/4 · PASS
python scripts/verify_spec_fws_f6.py --self-test    # 0건 실패
python scripts/verify_spec_fws_f6.py --no-run       # 닫은 열 8/8 · PASS(title_parts 는 F6-07 만 강제, 나머지 레거시는 완화)

# 인접 회귀(같은 gx-shell, 순차):
python -m pytest tests/test_p356_u4_rest_spec_promotions.py tests/test_an_n1_f6_07_webpush.py \
  tests/test_f05_event_api.py tests/test_dsm_app.py tests/test_fws_app.py tests/test_fws_f6.py \
  -q -p no:randomly
# → 2 failed, 118 passed in 307.77s — 실패 둘은 EVENT_ENTRY_SURFACE 가 낡아서다
#   (이 차선의 새 라우트 둘 + 다른 차선의 새 라우트 다섯이 아직 그 표에 없다 —
#   §4 조율자에게 넘길 줄 참고. 인증·테넌트 문지기 시험은 통과했다.)
```
