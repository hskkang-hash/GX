# N3 승격 제안 — 턴 AP (DSM-U5-02 · U5-05 · O-10 · O-11 · O-01 대행 강화)
(턴 AP · WO-GX-20261001-19 · 차선 N3)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이
문서는 제안·보고만 한다.** 이 차선은 `ga_readiness.yaml`을 손대지 않았다.

## 0. 일 요약

지시 순서(WO-19 §4 N3 · §5 P-421 ⑤) 그대로 다섯 절을 다뤘다:

| 절 | 결과 | 무엇이 갈랐나 |
|---|---|---|
| DSM-U5-02 | **완전히 닫힘**(5/5 title_parts measured) | 「선언 == 설정」을 코드 항등으로 만들고 성능 조건을 실측 |
| DSM-U5-05 | **완전히 닫힘**(7/7 title_parts measured/있음) | 관제일지 = 인계 메모 + 사건 타임라인 합본(새 표 0) — 완결조건 항등 실측 |
| O-10 | **절차·기록은 닫혔다 · 절 전체는 여전히 반쪽** | 콘솔 문·감사 줄·다음 회전일은 실측 · 「화면」 행이 새로 열렸다(§3) |
| O-11 | **절차·기록은 닫혔다 · 절 전체는 여전히 반쪽** | 되돌리기 1회 시험을 기록 읽기로 닫았다 · 「화면」 행이 새로 열렸다(§3) |
| O-01 대행 재확인 | 강화 완료(승격 대상 아님 — 기존 절 보강) | 시간 제한(15분) 신설 · 재확인 표 `O-01_proxy_review.md` |

**⚠ 절 중간에 발견한 것 — 눈금은 하나다(P-419).** N1 이 같은 턴 안에서
「같은 눈금」재판정을 O-01·02·05·06·07·08·09·12 여덟에 적용해 전부에
「화면(콘솔 보드)」 열린 행을 새로 찾았다(`TITLE_PARTS_RULE.md` §1-3). 이
차선이 O-10·O-11 을 위 표처럼 「절차·기록」으로 닫으려던 참이었는데, 같은
잣대를 O-10·O-11 에도 대야 정직하다 — 대 보니 **같은 결손**이었다
(`frontend/src/features/ops/api.ts` 에 `keys` 엔드포인트 자체가 없고,
`fetchReleaseBoard()` 는 있어도 `OpsHome.tsx` 가 안 부른다). 그래서 §3 처럼
그 사실을 title_parts 에 정직하게 더했다 — **P-428 은 화면 미배선을 빼는
사유로 못 쓴다**(TITLE_PARTS_RULE.md §3, 이 턴 규약 그대로) — O-10·O-11 을
"닫은 절"로 세지 않는다.

## 1. DSM-U5-02 — 접근권한·접속기록 (완전히 닫힘)

닫혀 있던 넷(권한 매트릭스·조회·CSV) 위에 남은 둘을 닫았다:

- **「접속기록 1년 이상 보관」**: `common/log_retention_policy.py` 에
  `enforced_declared_days('audit')` 를 새로 더했다 — **기존 `POLICY['audit']
  .days`(730 · P-230 목표 선언)·`aligned()`·`divergence()` 는 한 글자도 안
  건드렸다**(그 셋을 고치면 `scripts/ops_retention_policy.py` 의 자기시험
  — "선언 730·집행 365 면 반드시 빨강" 표본 — 이 깨진다, 그 게이트는 이
  차선 소유가 아니다). 새 함수는 `common.ops_tasks.audit_retention_declared_
  days()`(dj-core 가 실제로 읽는 `AdminConfig::System > security.
  audit_log_retention_days` 자리)를 **그대로 되읽고**, 미선언이면 730(법정
  목표)으로 안전하게 대체한다. 「선언 == 설정」이 이제 대조가 아니라
  **항등**이다 — 같은 함수가 같은 자리를 읽는다.
- **「완결 조건 조회 ≤ 60초」**: 새 시험이 `GET /api/dsm/access-log`
  왕복시간을 `time.perf_counter()` 로 직접 재 60초 미만을 확인한다(대리
  지표 0).

게이트: `scripts/verify_spec_dsm.py` 에 **④ 행**(`judge_retention_alignment`)
을 더했다 — gx-shell 안에서 `enforced_declared_days('audit')` 과
`audit_retention_declared_days()` 를 직접 불러 대조한다(pytest 를 또 안
돌린다 — 가벼운 `docker exec python -c` 하나).

증거: `docs/agent/evidence/SPEC/DSM-U5-02.json`(title_parts 5/5 measured).
시험: `backend/tests/test_ap_n3_u5_02_retention.py`(6건 통과).

## 2. DSM-U5-05 — 교대 편성 근무자 자동 (완전히 닫힘)

턴 AO 가 닫은 다섯(CSV 업로드·shifts 저장·표·근무자 자동 조회·인계 메모
근무자 자동) 위에 남은 둘 — 「일지 근무자 자동」·「완결조건 일지 근무자 =
편성표」 — 을 닫았다.

**새 표 0.** `handover_service.control_log()` 신설 — 관제일지(DSM-U1-04)라는
새 저장처를 만드는 대신, 이미 있는 두 공개 면을 한 응답으로 묶었다:
`build_draft()`(인계 메모)와 `apps.dsm.services.recent_events`/
`response_clock`(사건 타임라인, UX-14 가 이미 연 면). 새 문은
`GET /api/dsm/u5an/control-log`(`api_u5_an.py`) 하나뿐.

완결조건 「일지 근무자 = 편성표」는 **항등**이다: `control_log()['on_duty']`
는 `build_draft().on_duty` 를 그대로 옮긴 것이고, 그것은
`shift_roster_service.current_workers()` 를 그대로 옮긴 것이다 — 세 자리가
같은 호출 하나의 결과라 다른 값을 낼 길이 없다. 시험이 세 자리를 HTTP
응답에서 나란히 대조했다(`ControlLogTest`).

★ **정직하게 남기는 것**: 이번에 닫은 것은 U5-05 절의 그 두 행이지, DSM-U1-04
(「관제일지 자동」) 자체를 별도 절로 승격한 것이 아니다 — U1-04 는 여전히
미착수 절로 남아 있다(`scripts/verify_spec_dsm.py::NOT_STARTED`). 또한 이
관제일지 API 를 읽는 **전용 화면**은 만들지 않았다(frontend 는 이 차선
소유 밖) — U5-05 의 title_parts 일곱 항목 중 「화면」을 명시적으로 요구하는
행은 없어서(기존 다섯 행이 그 기준으로 이미 닫혀 있었다) 절 자체는 닫힘으로
센다. U1-04 를 별도 절로 승격할 때는 그 화면 요구를 먼저 확인해야 한다.

게이트: `scripts/verify_spec_dsm.py` `TESTS_RELS` 에 새 길목
(`tests/test_ap_n3_u5_05_control_log.py`)을 더했다 — 기존 ①②③ 판정식은
그대로(D-212).

증거: `docs/agent/evidence/SPEC/DSM-U5-05.json`(title_parts 7/7). 시험:
`backend/tests/test_ap_n3_u5_05_control_log.py`(2건 — 합본 실측 + 테넌트
격리).

## 3. O-10 · O-11 — 절차·기록은 닫혔다 · 「화면」이 새로 열려 절은 반쪽

### 3-1. O-10 키·자격 회전

지시(P-421 ⑤)대로 **절차·기록** 셋을 실측으로 채웠다:

- **콘솔 문** — 기존 `GET /api/dsm/ops/keys`(보드) · `POST /api/dsm/ops/
  keys/rotate`(회전, `kernels.k5_trust.rotate_key` 그대로 재사용)를 실제
  HTTP 로 두드려 확인.
- **감사 줄** — `key_rotation_board()` 가 이제 `rotation_audit_count` ·
  `last_rotation_audit`(가장 최근 회전 감사 스냅샷)를 낸다. 회전 뒤 실측
  ≥ 1.
- **다음 회전일** — `key_rotation_board()['keys'][*]['next_rotation_due_at']`
  신설 — 정책 주기(`policy_days`)에서 지난 나이(`age_days`)를 뺀 날짜를
  **지금(now) 기준**으로 다시 센다.
- **부수 실측 버그 수정**: `rotate_api_key()` 의 `new_key_id` 가
  `getattr(issued, "id", None)`(항상 `None` — `IssuedKey` 에 `.id` 칸이
  없다, `.view.key_id` 다)였다 — 시험이 응답 값을 실제로 대조하니 걸렸다.
  `issued.view.key_id` 로 고쳤다.

완결 조건 AND 의 라이브 절반(「회전 뒤 게이트 계정 로그인 4/4」)은 여전히
이 저장소 차선 공통 규칙이 라이브 로그인을 금지해 못 잰다 —
`excluded_by: "P-428"` + 사유.

**그러나** title_parts 에 「화면(회전 보드)」 행을 더했고, 그 행은
**열려 있다** — `frontend/src/features/ops/api.ts` 의 `opsEndpoint` 에
`keys`/`keys/rotate` 자체가 없다(grep 0). P-428 은 화면 미배선을 빼는
사유가 아니므로(TITLE_PARTS_RULE.md §3) 이 행은 정직하게 열어 뒀다 —
**O-10 절 전체는 아직 반쪽이다.**

### 3-2. O-11 릴리스·배포

완결 조건 3항 AND 중 마지막(「되돌리기 1회 시험」)을 닫았다:
`scripts/deploy_spa_8500.py::drill()` 이 **배포 때마다 이미** 되돌리기
연습을 실행해 `deploys.jsonl` 의 `drill_ok` 칸에 남긴다(그 파일 106~135행)
— 이 턴은 그 기록을 `release_board()` 가 명시적으로 낸다: `latest_deploy_
exit_ok` · `latest_smoke_ok` · `latest_rollback_drill_ok` · 3항 AND
(`deploy_gate_passed`) · 전체 이력(`rollback_drill_history`). 새 저장 0 —
이미 있는 장부를 읽을 뿐이다.

운영 서버에 실제로 되돌리는 **집행**(파일 스왑·컨테이너 재시작)은 여전히
`excluded_by: "P-428"`.

**그러나** O-10 과 같은 이유로 「화면(릴리스 보드)」 행을 열어 뒀다 —
`fetchReleaseBoard()` 함수는 `frontend/src/features/ops/api.ts` 에 있지만
`OpsHome.tsx` 가 부르지 않는다(grep 0, 데이터는 서지만 화면엔 안 뜬다).
**O-11 절 전체는 아직 반쪽이다.**

게이트: `scripts/verify_spec_ops.py` — `TESTS_REL_N3B`(길목) 더함 ·
`CLOSED_CLAUSES` 에 O-10·O-11 **남겨 뒀다**(id 를 판정 밖으로 빼지 않기
위해서 — `judge_title_parts` 가 화면 행을 실측할 때마다 정직하게 FAIL을
낸다. 「닫혔다」는 주장이 아니라 「계속 대조한다」는 뜻이다). gate_header
`measured=` 를 「닫힌 열 0/11 이 정직한 결론」으로 고쳤다 — 실행 출력이
정본이다.

증거: `docs/agent/evidence/SPEC/O-10.json`(신규) ·
`docs/agent/evidence/SPEC/O-11.json`(기존 파일의 「되돌리기 1회 시험」 행만
갱신 + 「화면」 행 추가). 시험: `backend/tests/test_ap_n3_o10_o11_ops.py`
(2건).

## 4. O-01 — 대행 호출 시간 제한(15분) (P-427 ⑤ · 승격 대상 아님, 보강)

턴 AO 청구 ⑤ 재확인. `ops_an_service.issue_tenant()` 가 U0 의
`Authorization` 헤더를 안쪽 `POST /api/v1/user/create-user` 호출에 물려
주는 대행 패턴은 유지하되, **자격의 나이**를 처음으로 확인한다:
`PROXY_FRESHNESS_LIMIT_SECONDS = 900`(15분) · `_forwarded_auth_age_seconds()`
가 JWT `iat` 를 읽어 나이를 재고, 초과하면 `OpsAnPermissionDenied`(403,
테넌트 미생성)로 거절 + 감사 줄(`issue_denied_stale_proxy`)을 남긴다.

재확인 표: `docs/agent/evidence/SPEC/O-01_proxy_review.md`(셋 — U0 만 ·
감사 줄 · 시간 제한). 시험: `backend/tests/test_ap_n3_o01_proxy.py`(4건 —
신선한 자격 회귀 · 낡은 자격 403+감사+테넌트 미생성 · 도우미 함수 자체
둘).

## 5. 게이트 재현

```
python scripts/verify_spec_dsm.py --self-test    # 20건 통과
python scripts/verify_spec_dsm.py --no-run        # 기존 CLOSED_CLAUSES(DSM-U5-02·U5-05 포함) 재확인

python scripts/verify_spec_ops.py --self-test     # 자기시험 전부 통과
python scripts/verify_spec_ops.py --no-run        # 실제 실행 — O-10·O-11 을 포함한 annex 전부
                                                    # 「화면」 열린 행으로 FAIL(정직한 결론)

MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n3 -w /app gx-shell \
  python -m pytest tests/test_ap_n3_u5_02_retention.py \
    tests/test_ap_n3_u5_05_control_log.py \
    tests/test_ap_n3_o10_o11_ops.py \
    tests/test_ap_n3_o01_proxy.py \
    -q --create-db -p no:randomly
```

## 6. 조율자에게 넘길 줄

1. 새 `/api/dsm/` 라우트 1개(`GET /api/dsm/u5an/control-log`)를
   `backend/tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE`(조율자 소유)
   에 올려 주십시오.
2. **O-10·O-11 「화면」 결손** — `frontend/src/features/ops/api.ts` 에
   `keys`/`keys/rotate` 엔드포인트를 더하고, `OpsHome.tsx` 에 회전 보드·
   릴리스 보드(이미 있는 `fetchReleaseBoard()`)를 렌더하면 두 절이 완전히
   닫힙니다. 서버 쪽은 전부 실측·안정입니다 — 남은 것은 프런트엔드
   컴포넌트뿐입니다. 이 차선(N3, backend/apps/dsm 소유)은 frontend 파일을
   고칠 권한이 없어 손대지 않았습니다.
3. **O-01·02·05·06·07·08·09·12 도 같은 「화면」 결손**(N1 이 같은 턴에
   먼저 발견) — 이 여덟은 N3 소유이지만 이번 배정(WO-19 §4)이 U5-02 ·
   U5-05 · O-10 · O-11 · O-01 보강까지였고, 여덟의 화면 배선은 시간상 이
   턴에 못 붙였습니다. 다음 배정 후보로 올립니다 — 실은 O-10·O-11 과
   **한 번에 같이 배선하는 것이 효율적**입니다(같은 `OpsHome.tsx` 파일).
   ⚠ 이 여덟의 title_parts 는 이 차선이 실수로 한 번 지웠다가 대화 기록
   에서 재구성해 복원했습니다(§7 사고 기록) — **N1 이 원본과 대조해
   주시길 부탁드립니다.** 특히 `where` 칸(새로 생긴 「화면」·재분류 행)은
   재구성이라 원문과 토씨가 다를 수 있습니다.
4. `docs/agent/evidence/D-346/ga_readiness.yaml` — DSM-U5-02 · DSM-U5-05
   두 절 승격(완전히 닫힘)을 대장에 반영해 주십시오. O-10 · O-11 은
   **내리지 마십시오**(원래 AO 턴부터 대장에 없었습니다 — 여전히 반쪽·
   미승격 상태 그대로입니다). 이 차선은 대장을 고치지 않았습니다.
5. `backend/apps/dsm/ops_an_service.py::rotate_api_key` 의 실측 버그 둘
   (§3-1) — ① `new_key_id` 가 `getattr(issued,"id",None)`(항상 `None`,
   `IssuedKey` 엔 `.id` 칸이 없다) ② **더 중요한 것**: `scope =
   TenantScope.of(actor)`(U0 자신)로 `k5_trust.rotate_key` 를 불러
   `NoTenantGroupError` 로 **항상 500** 이었습니다(U0 은 어느 그룹에도
   안 속한다 — `k5_trust._group_of` 가 시스템 스코프도 거절하도록
   설계돼 있습니다, 의도된 설계라 이 차선이 그 문은 못 바꿉니다). 즉
   **이 턴 전에는 실제 회전 호출이 한 번도 성공한 적이 없었을 가능성이
   높습니다**(스모크 시험이 GET 보드만 쟀지 POST 회전을 실측한 적이
   없었습니다). `_tenant_member_for_proxy()` 신설로 그 테넌트의 실제
   구성원 스코프를 대신 빌리게 고쳤습니다 — 재확인 부탁드립니다.
6. **재실행 경고** — `tests/test_ops_an.py::_add_title_parts()`(줄 49)와
   `tests/test_ap_n3_o10_o11_ops.py`의 `_write_evidence()`(O-10 전용, 새
   파일 쓰개) 둘 다 title_parts 를 **통째로 덮어씁니다**(기존 표를 안
   읽고 보존 안 함). `test_fws_f4.py::_write_evidence2` 류와 같은 함정
   입니다(N1 체크포인트가 이미 경고한 패턴) — 이 두 파일을 다시 돌리면
   O-01·02·05·06·07·08·09·10·12 의 title_parts 가 옛 버전으로 되돌아
   갑니다. 병합 전 전량 시험에 이 파일들이 걸리면 **같은 사고가 재현될
   수 있습니다** — 전량 시험 뒤 이 id 들의 title_parts 를 다시 한 번
   대조해 주시길 요청합니다.

## 7. 스스로 의심하는 점

- **DSM-U5-05 의 "완전히 닫힘" 판정**은 U5-05 절의 title_parts 일곱 항목
  기준으로는 정확하지만, 「관제일지」라는 낱말이 부르는 제품 전체
  기대(전용 화면·PDF 출력 등, DSM-U1-04 의 영역)까지 만족시킨 것은
  아니다 — U1-04 를 별도 절로 볼지 여부의 판단은 여전히 조율자 몫이고,
  이 판단이 세 번째 턴째 반복되고 있다(N4 턴 AM → N1 턴 AN·AO → 이 턴).
- O-10 `next_rotation_due_at` 계산은 **스냅샷 시각이 아니라 지금(now)
  기준**으로 다시 센다 — `key_rotation_last.json` 의 `age_days` 가 스냅샷
  당시 값이라, 스냅샷이 오래될수록(며칠~몇 주) 이 계산의 오차가 커진다.
  정확하려면 `age_days` 를 다시 재는 새 탐침이 필요한데, 이번 턴은 기존
  파일을 읽기만 했다(새 저장 0 지시 준수) — 오차 방향과 크기를 이 문서에
  적어 둔다.
- O-01 시간 제한(15분)은 **U0 자신의 세션은 안 건드린다** — 대행에만
  적용된다. 그래서 U0 이 15분 넘게 로그인해 있다가 아무 문제 없이 다른
  일(예: `GET /ops/tenants`)을 계속할 수 있고, 그러다 `issue_tenant` 만
  거절당한다 — 사용자 경험상 「왜 이것만 안 되지」로 보일 수 있다(화면
  쪽 에러 메시지 설계는 이 차선 밖).
- **⚠⚠⚠ 사고 — 이 차선이 N1 의 재판정을 실제로 한 번 지웠다가 되살렸다.**
  O-10·O-11 시험을 만들며 `tests/test_ops_an.py` 를 함께 돌렸는데(길목
  공유), 그 파일의 `_add_title_parts()`(줄 49)가 **파일 안 리터럴로
  title_parts 를 통째로 덮어쓴다**(기존 표를 안 읽는다 — `test_fws_f4.py::
  _write_evidence2` 류와 같은 함정, N1 이 자기 체크포인트에 이미 경고해
  둔 그 패턴). 그 결과 N1 이 같은 턴에 O-01·02·05·06·07·08·09·12 여덟에
  새로 찾아 적어 둔 「화면」 열린 행·재분류(부분/측정) 행이 **전부
  사라지고 옛(턴 AO) 「전부 measured」 버전으로 되돌아갔다** — O-05 는
  9행에서 3행으로 줄었다(6행 증발). 이 차선은 `python scripts/
  verify_spec_ops.py --no-run` 을 돌리다 여덟 절이 전부 "title_parts N행
  전부 닫힘"으로 나오는 것을 보고 **이상함을 느껴** 재대조했고, 이 대화
  기록에 남아 있던 N1 의 판정 결과(먼저 한 번 읽어 뒀던 것)를 그대로
  복원했다(§4 아래 스크립트). **원문이 아니라 재구성이다** — `where` 칸
  중 새로 생긴 행은 `N1_rejudge_ap.md` §2 요약을 참고해 다시 지어 썼다.
  복원 뒤 O-10.json 도 **같은 사고를 두 번째로** 겪었다: 내가 손으로
  더한 「화면(회전 보드)」 행을, 그 뒤에 다시 돌린 `test_ap_n3_o10_o11_ops
  .py` 재실행이 자기 시험의 `_write_evidence()`(새 파일 전용 쓰개 — 이것도
  기존 표를 안 읽고 통째로 쓴다)로 지웠다 — 두 번째로 알아채고 다시 붙였다.
  **원인**: 손으로 JSON 을 patch 한 뒤 같은 파일을 쓰는 시험을 다시 돌리면
  patch 가 사라진다 — 이 턴 규약이 여러 곳에서 경고한 "재실행이 재판정을
  지운다" 함정에 이 차선도 두 번 걸렸다. 지금 이 문서의 §3·§5 결과는
  **마지막에 다시 읽어 확인한 값**이다. 조율자 창에서 병합 직전 한 번 더
  `--no-run` 으로 재확인해 주시길 강하게 요청한다 — 이후 다른 차선의
  test 재실행이 또 이 파일들을 건드릴 수 있다.
