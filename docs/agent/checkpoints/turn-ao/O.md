# 차선 O — 턴 AO 보고 (테넌트 곁표 · P-411 · WO-GX-20260930-18)

## ① 바꾼/만든 파일

**새로 만든 것**
- `backend/common/models.py` — `AuditScope` 모델 추가(app_label=`common`,
  `BillingMark`(P-224)와 같은 판단 — dj-core 표에 FK 를 걸지 않는다).
- `backend/common/migrations/0005_p411_audit_scope.py` — 새 마이그레이션 1개
  (이 턴 「새 표 ≤ 1」의 그 하나).
- `backend/apps/fws/audit_scope.py` — 곁표 쓰기(`record`)·읽기(`tenant_audit_ids`)
  도우미. F3-18·U5-02·U5-03 의 쓰기 네 자리만 이 도우미를 거친다(미들웨어로
  전역을 가로채지 않았다).
- `backend/tests/test_ao_o_audit_scope.py` — 곁표 쓰기·같은 테넌트 읽기·다른
  테넌트 0 을 직접(HTTP 없이) + HTTP 로 한 번 더 잰다.
- `docs/agent/evidence/SPEC/O_promotions_ao.md` — 승격 제안(FWS-F3-18) + F3-16
  이 왜 여전히 열려 있는지.
- `docs/agent/checkpoints/turn-ao/O.md` — 이 문서.

**고친 것**
- `backend/apps/fws/office2.py` — F3-18(`record_patrol_enforcement`·
  `set_entry_control_zone`·`patrol_enforcement_stats`·`entry_control_zones`)
  의 쓰기/읽기를 곁표 경유로. 응답 `scope` 값 `"mine"` → `"tenant"`. 머리말 갱신.
- `backend/apps/fws/admin_settings.py` — U5-02(`save_post`·`my_posts`)·U5-03
  (`save_evac_entity`·`evac_targets`)의 쓰기/읽기를 곁표 경유로. 머리말 갱신.
- `backend/tests/test_fws_f3b.py` — F3-18 시험에 "같은 테넌트 두 사람" +
  "다른 테넌트는 0" 을 더하고, evidence `title_parts` 에서 "본인 실적" 열린
  행을 닫힌 문구로 바꿨다. 모듈 머리말에 턴 AO 갱신 사실 적음.
- `backend/tests/test_fws_u5.py` — U5-02·U5-03 시험에 같은 방식으로 "같은
  테넌트 두 관리자" + "다른 테넌트는 0" 을 더하고 `title_parts` 에 "테넌트
  전체" 행을 새로 더했다.
- `scripts/verify_spec_fws_f3b.py` — `FWS-F3-16` 을 `CLOSED_CLAUSES` 에서 빼고
  `NOT_STARTED` 로 옮겼다(골든타임 준수율 행이 여전히 대리 지표 · 열린 행 ·
  WO-18 규약). `gate_header` 갱신(닫은 열 9→8 · 못 닫은 열 2→3).
- `scripts/verify_spec_u5_an.py` — **내용 변경 없음**(U5-02·U5-03 은 이미
  닫힌 열이었고 그대로 맞다 — 확인만 했다).

**곁다리로 갱신된 것(손으로 안 고침 — pytest 가 다시 쓴 것)**
- `docs/agent/evidence/SPEC/FWS-F3-16.json` — `test_fws_f3b.py` 전체 재실행
  때 같이 재측됨(시각·사건 id 만 다르다 — `title_parts` 내용은 그대로, `git
  diff` 로 확인).
- `docs/agent/evidence/SPEC/FWS-F3-18.json` · `FWS-U5-02.json` ·
  `FWS-U5-03.json` — 새 시험이 기계로 다시 찍었다(본인 실적 문구가 빠지고
  테넌트 전체 실측으로 바뀜).

## ② 시험 이름과 결과 [실측 2026-09-29 · gx-shell · `DB_TEST_NAME=test_gx_lane_o`]

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_o -w /app gx-shell \
  python -m pytest tests/test_ao_o_audit_scope.py -q --create-db -p no:randomly
  → 1 failed, 5 passed  (첫 회차 — role_gate 「역할 0」 403, 시험 픽스처 결함 · 아래 참고)

(고친 뒤 재실행, --create-db 없이)
python -m pytest tests/test_ao_o_audit_scope.py -q -p no:randomly
  → 6 passed in 445.23s

python -m pytest tests/test_fws_f3b.py -q -p no:randomly
  → 10 passed in 449.43s

python -m pytest tests/test_fws_u5.py -q -p no:randomly
  → 10 passed in 67.62s
```

게이트(호스트에서, `--no-run` — pytest 를 다시 안 돌리고 지금 evidence 만 본다):

```
python scripts/verify_spec_fws_f3b.py --no-run   → 닫은 열 8/8 · PASS
python scripts/verify_spec_u5_an.py --no-run     → 닫은 열 6/6 · PASS
python scripts/verify_spec_fws_f3b.py --self-test → 자기시험 0건 실패
```

## ③ 닫은 절 · 못 닫은 절

**닫음(이번 턴이 반쪽을 온전으로 고쳤다)**
- **FWS-F3-18** 계도·단속 통계 · 입산통제구역 관리 — 곁표로 같은 테넌트 전체를
  센다(이전: 본인 실적만). `title_parts` 의 열린 행을 닫았다.
- **FWS-U5-02** 초소·순찰함(NFC)·순찰 구역 — 곁표로 같은 테넌트 관리자 전원의
  등록을 본다(이전: 등록한 사람 자신만). 실질이 온전해졌다(대장 status 는
  이미 `closed` 였다 — §6 참고).
- **FWS-U5-03** 마을·대피소·요양시설 등록(대피 대상 자동 산출) — 같은 이유로
  온전해졌다.

**못 닫음 — 무엇이 없는가**
- **FWS-F3-16** 통계(…·골든타임 준수율) — 일곱 칸은 실측이지만 "골든타임
  준수율" 이 확인 회신 30분 비율의 **대리**다(`title_parts` status 가
  "근사 실측"으로 시작 — WO-18 규약상 열린 행). 실제 헬기 투하·지상 도달
  시각을 다시 찾아봤다 — `stream_monitors/services/response_clock.py` 가
  사건별 `arrived_at`(현장 도착/조치 착수 전이 시각)을 내는 것은 찾았지만,
  그것도 "헬기 투하" 시각은 아니다(대응 상태 넷에 그 상태가 없다). 지어내지
  않고 열어 둔다 — `scripts/verify_spec_fws_f3b.py` 의 `NOT_STARTED` 로 옮겼다.

## ④ 조율자에게 넘길 줄

- **공용 파일 — 제가 못 고친 것**: `backend/apps/fws/api_office2.py` 의
  `@tenant_scoped(reason=...)` 문구 넷이 이제 사실과 다릅니다 — "계도·단속
  기록은 이 사람이 남긴 것이다"(189행 근방) · "내 계도·단속 실적만 읽는다"
  (201행 근방) · "입산통제구역 설정은 이 사람이 남긴 것이다"(206행 근방) ·
  "내가 설정한 구역만 읽는다"(216행 근방) — 넷 다 이제 "같은 테넌트 전체"로
  바뀌어야 정확합니다. `api_office2.py` 는 차선 N3 소유라 저는 안 고쳤습니다.
- **`docs/agent/evidence/D-346/ga_readiness.yaml`**: `FWS-F3-18` 이 지금
  `status: 미착수 / kind: unmeasurable / hand: in`(354·359행 근방)으로
  남아 있습니다 — 이번 턴이 온전히 닫았으니 `closed` 로 올리는 것을 제안합니다
  (제안 YAML 은 `O_promotions_ao.md` §6). **`FWS-F3-16` 은 그대로 두어야
  합니다**(올리면 안 됩니다 — 골든타임 행이 열려 있습니다). `FWS-U5-02`·
  `U5-03` 은 이미 `closed` 라 손댈 것이 없습니다(원하시면 `kind_why` 문구만
  갱신 — 같은 문서 §6).
- **대장 이동은 제가 안 했습니다**(규약 — 조율자만 `ga_readiness.yaml` 을
  고칩니다).

## ⑤ 스스로 의심하는 점

- **곁표는 앞으로 쓰는 행부터만 채워집니다.** 과거(이 마이그레이션 이전)에
  이미 쌓인 F3-18·U5-02·U5-03 감사 행에는 곁표가 없어 `tenant_audit_ids`
  집합에 안 잡힙니다 — 운영에 이미 그런 데이터가 있었다면, 이번 배포 이후
  "테넌트 전체"가 실제로는 "배포 이후 쓴 것 전체"로 보일 수 있습니다(새로운
  손실은 아닙니다 — 소급 전에는 어차피 본인 것만 보였습니다). 소급 채움
  스크립트는 짓지 않았습니다(과거 행에서 「누가 썼는가」→group 은 되짚을 수
  있지만, 이 턴의 일감 밖이라 판단했습니다).
- **group 없는 행위자(전역 관리자 등)의 조회는 0건입니다.** `tenant_audit_ids`
  가 "닫는 쪽을 기본값"으로 판단해 그렇게 짰습니다(§`audit_scope.py` 머리말) —
  전역 관리자가 이 넷을 "전체 테넌트 합산"으로 봐야 한다면 그것은 이번 턴이
  안 지은 별도 분기입니다.
- **F3-16 의 "지상 도달"에 더 가까운 값**(`stream_monitors/services/
  response_clock.py::stamps_for` 의 `arrived_at`)을 찾았지만 쓰지 않았습니다
  — office2.py 의 알고리즘을 바꾸는 것이 제 일감인지 확신이 없어(파일
  소유는 있지만 일감 범위는 곁표·테넌트로 한정됨) 손대지 않았습니다. 다음
  차선이 판단할 여지를 남깁니다.
- **`api_office2.py` 의 stale 문구**(④ 참고)를 제가 못 고쳐서, 그 파일만 읽는
  사람은 아직 "본인만" 이라고 오해할 수 있습니다.
