# O 승격 제안 — 감사 테넌트 곁표(P-411) · FWS-F3-18 승격 · FWS-F3-16 열림 유지
(턴 AO · WO-GX-20260930-18 · 차선 O)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이 문서는
제안만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다(§0.4 금지구역 인접·
공통 규약).

## 0. 이 차선이 한 일 — 한 줄

턴 AN(N3·N4)이 `logger.AuditLogs`(dj-core 소유 · §0.4 금지구역)에 테넌트(group)
칸이 없어 F3-18(계도·단속 통계·입산통제구역)·U5-02(초소 등록)·U5-03(대피 대상
등록)을 "이 감사 행을 쓴 **사람 자신**의 것만" 으로 좁혀 놓았던 반쪽을, 새 곁표
**`common.models.AuditScope`**(마이그레이션 `common/0005_p411_audit_scope.py` ·
새 표 1개 — 이 턴의 「새 표 ≤ 1」이 이것)로 넘어섰다. 쓰는 자리는
`backend/apps/fws/audit_scope.py::record`(F3-18·U5-02·U5-03 의 쓰기 네 자리만
거친다 — 미들웨어로 전역을 가로채지 않았다) 하나로 묶었다.

F3-16(통계)은 **같이 검토했으나 코드를 바꾸지 않았다** — 아래 §3.

## 1. 실제 구현

- **새 표 1개** — `backend/common/models.py::AuditScope`(app_label=`common` ·
  `apps/fws` 는 Django 앱으로 등록돼 있지 않아 마이그레이션을 가질 수 없다 ·
  `common.models.BillingMark`(P-224)와 같은 판단 — dj-core 표를 향한 FK 를 걸지
  않는다). 마이그레이션 `backend/common/migrations/0005_p411_audit_scope.py`
  (`common` 의 최신 다음 번호 · 아무 행도 안 건드린다).
- **쓰기 도우미** — `backend/apps/fws/audit_scope.py`(신규) · `record(...)` 가
  `common.audit_writer.write`(기존 정본)로 감사 행을 쓴 **직후** 그 `audit_id` 를
  요청자의 group(`common.tenant_filters.get_user_group`)에 잇는다. `tenant_
  audit_ids(...)` 가 그 테넌트의 감사 행 id 집합을 돌려준다(group 없으면 빈
  집합 — 닫는 쪽이 기본값).
- **office2.py**(F3-18) — `record_patrol_enforcement`·`set_entry_control_zone`
  의 쓰기 자리 둘을 `audit_scope.record` 로 바꾸고, `patrol_enforcement_stats`·
  `entry_control_zones` 의 읽기를 `_rows_for_tenant`(곁표로 좁힌 전건)로 바꿨다.
  응답의 `scope` 값이 `"mine"` → `"tenant"` 로 바뀐다(정직하게 알린다).
- **admin_settings.py**(U5-02·U5-03) — `save_post`·`save_evac_entity` 의 쓰기
  자리 둘을 `audit_scope.record` 로, `my_posts`·`evac_targets` 의 읽기를
  `_tenant_rows`(곁표로 좁힌 전건)로 바꿨다. 함수 이름(`my_posts`)은 API 레이어
  (`api_admin.py`, 이 차선 소유 아님)가 부르므로 그대로 뒀다 — 내용만 바뀌었다.
- **다른 테넌트는 0건** — 네 함수 전부 새 시험으로 확인(§4).

## 2. 실측 증거

- `docs/agent/evidence/SPEC/FWS-F3-18.json` — 같은 테넌트 두 사람이 나눠 남긴
  계도 1건·단속 1건 · 입산통제구역 2곳이 GET 에서 **합쳐** 나온다(`total=2` ·
  `zones` 2건 · `scope="tenant"`). `title_parts` 의 "계도·단속 통계" 행에서
  "본인 실적" 문구를 뺐다 — 이제 조직 전체를 센다(반쪽이 아니다).
- `docs/agent/evidence/SPEC/FWS-U5-02.json` — 같은 테넌트 두 관리자가 나눠
  등록한 초소(P-77·P-78) 둘 다 목록에 보인다. `title_parts` 에 「테넌트 전체」
  행을 새로 더했다.
- `docs/agent/evidence/SPEC/FWS-U5-03.json` — 같은 테넌트 두 관리자가 나눠
  등록한 마을·요양시설·대피소 셋(`count=3`)이 합쳐져 대피 대상 총원이 자동
  산출된다(312+41=353). `title_parts` 에 「테넌트 전체」 행을 새로 더했다.
- `docs/agent/evidence/SPEC/FWS-F3-16.json` — **바꾸지 않았다**(코드를 안
  건드렸다 · §3). `test_fws_f3b.py` 전체를 다시 돌리며 기계로 재측만 됐다
  (시각·사건 id 만 다르고 내용은 동일 — `git diff` 로 확인).

## 3. FWS-F3-16 — **왜 이번에도 닫지 않는가** (P-406 결정 번호 없음 · 열린 행)

지시서가 「F3-16 의 골든타임 준수율이 확인 회신 30분 비율의 **대리**라면 그 행은
여전히 열린 행」이라 명시했다. 확인했다:

- `title_parts` 의 "골든타임 준수율" 행은 이미(N3 시절부터) `"근사 실측 — …"`
  으로 시작한다 — 턴 AO 규약(`_규약.md` "턴 AO 에 더한 것")의 열린 행 접두어
  목록(`없음`·`부분`·`근사`·`대리`·`대안`·`[미확인]`)에 그대로 걸린다.
- 실제 헬기 투하·지상 도달 시각을 저장소에서 다시 찾았다 — **`stream_monitors/
  services/response_clock.py::stamps_for`가 사건별 `arrived_at`(현장 도착/조치
  착수 전이 시각 — 감사를 읽어 세운 **원값**, p50/p95 분포가 아니다)을 낸다.**
  office2.py 머리말이 "이 앱이 갖고 있지 않다"고 적은 것보다는 사실 더 가깝다
  — 그러나 그것도 annex 가 부르는 "헬기 투하" 시각은 **아니다**(대응 상태 넷
  `occurred`/`acknowledged`/`in_progress`/`closed` 안에 헬기 투하를 가리키는
  상태·칸이 없다 — 그 사건이 산불이든 아니든 K1 은 헬기 투하를 모른다).
  `arrived_at` 을 골든타임 계산에 넣더라도 annex 제목의 절반("헬기 투하")은
  여전히 못 채운다 — **부분 개선이 반쪽을 반쪽인 채로 둔다.**
- 위 계산 자체를 바꾸는 일(`office2.fire_stats` 알고리즘 교체)은 이 차선의
  일감이 아니다 — 이번 일감은 「곁표로 테넌트 범위를 넘는다」이지 「골든타임
  지표를 다시 짓는다」가 아니다(지시서 §1·§2 의 파일 소유는 office2.py 지만,
  일감은 명시적으로 곁표·테넌트 범위 조회다). 지어내지 않고 **열린 채로 둔다.**

**결론 — FWS-F3-16 은 이번에도 승격 제안에서 뺀다.** `scripts/verify_spec_fws_
f3b.py` 의 `CLOSED_CLAUSES` 에서 빼고 `NOT_STARTED` 로 옮겼다(아래 §5).
`ga_readiness.yaml` 에는 원래도 "closed" 로 들어간 적이 없다(§5 확인) — 그러니
**대장은 바뀔 것이 없다.** 다음 사람에게: 골든타임을 정말 닫으려면 annex 의
"헬기 투하" 시각을 낼 수 있는 원 데이터(살수 지시·헬기 배치 기록)가 이 저장소
밖에서 먼저 들어와야 한다.

## 4. 격리 시험 — 새 파일 `backend/tests/test_ao_o_audit_scope.py`

`apps/fws/audit_scope.py` 자체의 계약 셋을 직접 잰다(HTTP 없이) + HTTP 로 F3-18
경로가 실제로 그 도우미를 쓰는지 한 번 더:

```
tests/test_ao_o_audit_scope.py::AuditScopeUnitTest
  test_record_writes_a_sidecar_row_with_the_actors_tenant        곁표 쓰기
  test_tenant_audit_ids_covers_every_person_in_the_tenant         같은 테넌트 읽기(두 사람)
  test_other_tenant_sees_zero                                     다른 테넌트는 0
  test_actor_without_group_skips_the_sidecar_without_raising      group 없는 행위자 — 예외 없이 곁표만 생략
tests/test_ao_o_audit_scope.py::AuditScopeHttpTest
  test_two_people_same_tenant_see_each_others_patrol_records      HTTP 로 재확인(같은 테넌트 합산)
  test_other_tenant_gets_zero_patrol_stats                        HTTP 로 재확인(다른 테넌트 0)
```

## 5. 게이트 행

- `scripts/verify_spec_fws_f3b.py` — `CLOSED_CLAUSES` 에서 `FWS-F3-16` 을 빼고
  `NOT_STARTED` 로 옮겼다(§3 사유 그대로 적었다). `FWS-F3-18` 은 그대로 닫힌
  열에 남았다(내용만 반쪽에서 온전으로 바뀌었다). `gate_header(measured=...)`
  갱신 — 닫은 열 9 → **8**, 못 닫은 열 2 → **3**.
  `python scripts/verify_spec_fws_f3b.py --no-run` → **닫은 열 8/8 · PASS**.
- `scripts/verify_spec_u5_an.py` — **고치지 않았다.** U5-02·U5-03 은 이미
  닫힌 열이었고(내용만 반쪽에서 온전으로 바뀌었다) `CLOSED_CLAUSES`·
  `NOT_STARTED` 는 그대로 맞다.
  `python scripts/verify_spec_u5_an.py --no-run` → **닫은 열 6/6 · PASS**.

## 6. `ga_readiness.yaml` 확인 — 바뀔 것이 무엇인가 (조율자용 체크리스트)

```
$ grep -n "FWS-F3-16\|FWS-F3-18" docs/agent/evidence/D-346/ga_readiness.yaml
  354:    - id: FWS-F3-16   status: 미착수  kind: unmeasurable  hand: in  src: FWS
  359:    - id: FWS-F3-18   status: 미착수  kind: unmeasurable  hand: in  src: FWS
```

**둘 다 원래도 "closed" 로 승격된 적이 없다**(N3 가 P-356 넷 중 ①②③만 갖추고
④ 제안(`N3_promotions_an.md`)을 냈으나 조율자가 아직 대장에 적용하지 않은
상태로 보인다 — U5 시리즈는 N4 의 제안이 이미 적용돼 있는 것과 대조된다). 이
문서가 제안하는 것은:

- **FWS-F3-18** — 위 354/359 행 근방의 `미착수` 항목을, U5-02/U5-03 이 쓰는
  것과 같은 `closed` 모양으로 바꾸는 것을 제안한다(아래 YAML). `FWS-F3-11~14·
  17·19·20` 은 이 차선의 일감이 아니라 손대지 않았다 — N3 의 제안(`N3_
  promotions_an.md`)이 여전히 유효하면 그것도 함께 적용을 검토해 주시기 바란다.
- **FWS-F3-16** — **바꾸지 않는다.** 지금 그대로(`미착수`)가 맞다 — 이 문서가
  하는 일은 "여전히 승격하면 안 된다"를 다시 확인하는 것뿐이다.
- **FWS-U5-02·U5-03** — 이미 `closed`. `kind_why` 문구를 갱신하고 싶다면(옛
  "본인 등록만" 한계가 이제 사실이 아니다) 아래 참고용 문장을 제안하되, 상태
  값 자체는 바꿀 것이 없다.

```yaml
# docs/agent/evidence/D-346/ga_readiness.yaml :: FWS-F3-18 의 status/kind 를
# (예시) 아래처럼 바꾸는 것을 제안 — 정확한 위치·들여쓰기는 조율자가 그 파일의
# annex_promoted.closed 배열 모양(예: U5-02 근방)에 맞춰 옮겨 주시기 바란다.
- id: FWS-F3-18
  title: 계도·단속 통계 · 입산통제구역 관리
  status: 구현
  kind: closed
  kind_why: |
    [P-356·411 · 턴 AN(N3)+AO(O) · 차선 N3→O] 별표 승격 — 구현 · 증거
    `docs/agent/evidence/SPEC/FWS-F3-18.json`(시험 클라이언트 실측 · title_parts
    빈 칸 0) · 게이트 `scripts/verify_spec_fws_f3b.py` 행 PASS(닫은 열 8/8) ·
    턴 AO 가 곁표(`common.models.AuditScope`)로 "본인만" 한계를 넘어 같은
    테넌트 전체 집계로 고쳤다(이전 N3 증거는 "본인 실적" 이라 반쪽이었다).
  gate: scripts/verify_spec_fws_f3b.py
  gate_args: --no-run
  proof: backend/tests/test_fws_f3b.py
  evidence: docs/agent/evidence/SPEC/FWS-F3-18.json
  origin: 기능명세 별표(annex_2_spec) → 승격 2026-09-29(턴 AO 갱신)

# FWS-F3-16 은 위 배열에 넣지 않는다 — 골든타임 준수율 행이 열려 있다(§3).
```

## 7. 시험 재실행 결과 [실측 2026-09-29 · gx-shell(`test_gx_lane_o`)]

```
tests/test_ao_o_audit_scope.py   6 passed in 445.23s (0:07:25)
tests/test_fws_f3b.py           10 passed in 449.43s (0:07:29)
tests/test_fws_u5.py            10 passed in 67.62s (0:01:07)

python scripts/verify_spec_fws_f3b.py --no-run   → 닫은 열 8/8 · PASS
python scripts/verify_spec_u5_an.py --no-run     → 닫은 열 6/6 · PASS
```

## 8. F-05 잠금·계층·§0.4 확인

- `kernels.k1_event` 를 `apps/fws/audit_scope.py` 가 import 하지 않는다(grep
  0건) — 이 곁표는 사건을 만지지 않는다(누가 감사 행을 썼는지만 본다).
- `apps/fws/audit_scope.py` 는 `common.audit_writer`·`common.tenant_filters`
  만 import 한다(둘 다 L1 · 기존 `office2.py`·`admin_settings.py` 가 이미
  쓰던 것과 같은 계층).
- `logger.AuditLogs`(dj-core · §0.4)는 **한 자도 안 고쳤다** — 새 표
  (`common.models.AuditScope`)만 그 옆에 세웠다. `backend/delivery`·`orders`·
  `terminals` 는 건드리지 않았다.
- 새 모델 **1개**(이 턴 「새 표 ≤ 1」의 그 하나) · 마이그레이션 **1개**
  (`common/0005_p411_audit_scope.py`, `common` 앱의 최신 다음 번호).
