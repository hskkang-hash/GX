# Q 보고 — 턴 AD (차선 Q · 회색 게이트 → 0)

이것 하나만 끝까지 했다: `verify_gate_header.py` 의 MEASURED_LINE 회색을 줄이는 일.
429 없음 — 도중에 한도에 안 걸렸다. 제품 코드는 안 건드렸다(모두 `scripts/` 판정기 +
`docs/agent/verify_gates.sh` 1줄). 커밋은 안 함(조율자만).

## ① 실측 — 명령 + 결과 (전/후)

```
PYTHONIOENCODING=utf-8 python scripts/verify_gate_header.py
```

**전** (턴 시작 시 재측정):
```
MEASURED_LINE  게이트 81개 중 70개가 「무엇을 · 분모 N」을 말한다 · 회색 11
  ['verify_alarm_budget.py', 'verify_bundle_api_base.py', 'verify_bundle_hash.py',
   'verify_camera_address.py', 'verify_camera_pulse.py', 'verify_event_drop.py',
   'verify_minio.py', 'verify_perf_budget.py', 'verify_purge.py',
   'verify_release_candidate.py', 'verify_seed_p20.py']
[기한] D-511 기한 2026-09-23 — 그날부터 red. 오늘은 아직 회색
```

**후**:
```
MEASURED_LINE  게이트 81개 중 79개가 「무엇을 · 분모 N」을 말한다 · 회색 2
  ['verify_perf_budget.py', 'verify_release_candidate.py']
[기한] D-511 기한 2026-09-23 — 그날부터 red. 오늘은 아직 회색
```

**회색 11 → 2.** 남은 2건은 **의도한 `deferred:RC-1 2026-09-25`**다(면제 아님 —
`judge_measured()` 가 여전히 문제 목록에 넣는다. §3 지시대로 그대로 둠).

`verify_backup_recovery.py` 는 이번 재측정에서 이미 HEADER_LIVE 도 MEASURED_LINE 도
정상이었다(E 가 턴 AC 이후 고쳐 둔 상태) — 손 안 댐, `verify_gates.sh` 의
`ALL_GATES` 등재만 함(④ 참고).

## ② 고친 파일:줄 (전부 `scripts/` 판정기 + `verify_gates.sh` 1줄 · 제품 코드 0)

- `scripts/verify_alarm_budget.py:54-59,417-423` — `JUDGED_ASPECTS`(5) 신설 · `measured=`
- `scripts/verify_camera_pulse.py:463-476` — `len(FALLBACK)`(5) 로 `measured=`
- `scripts/verify_camera_address.py:38-43,155-163` — `CLASSIFY_BUCKETS`(3) 신설 · `measured=`
- `scripts/verify_minio.py:68-73,289-299` — `MEASURED_STAGES`(4) 신설 · `measured=`
- `scripts/verify_bundle_api_base.py:339-352` — `len(_NOT_API)`(10) 로 `measured=`
- `scripts/verify_bundle_hash.py:93-100,715-724` — `SCAN_PATTERNS`(3) 신설 · `measured=`
- `scripts/verify_release_candidate.py:285-299` — `deferred:RC-1 2026-09-25`
- `scripts/verify_perf_budget.py:1503-1518` — `deferred:RC-1 2026-09-25`
- `scripts/verify_event_drop.py:57-71,423-437` — `SURGE_INPUT`(300) 로 `measured=`
  (미배선으로 재분류 — ④ 참고)
- `scripts/verify_purge.py:88-95,683-694` — `JUDGED_ASPECTS`(7) 신설 · `measured=`
  (미배선으로 재분류 — ④ 참고)
- `scripts/verify_seed_p20.py:102-135(judge)·171-217(collect)·127-166(self_test)·
  269-283(header)` — **P-251 다섯째 수 신설**(§③ 참고) · `measured=`
- `docs/agent/verify_gates.sh:1497` — `ALL_GATES` 에 `backup-recovery` 등재

## ③ `verify_seed_p20.py` — P-251 술어 구현 (㉯)

게이트 술어를 그대로 코드로 옮겼다: 「`data_source=seed` 사건이 청구·월간 KPI 에
0건」. 다섯째 `judge()` 행 `"P-251 씨앗은 청구·KPI 0건"` 신설.

- **분모**: 씨앗 사건 수(런타임 · 기존 4수와 같은 `seed_events` 칸을 재사용 — D-212,
  새 분모를 따로 안 만듦).
- **잰 것**: 씨앗 사건 pk 집합을 `common.billing_marks.exclude_unbillable()` +
  `exclude_soft_deleted()`(B 소유 · **읽기·호출만**, `kernels.k1_event.count_events`
  가 쓰는 것과 같은 두 겹)에 걸어 **남는 것**(=청구에 새는 것)을 센다. 0이면 통과.
- **범위 결정(솔직히 적는다)**: "청구"는 K1 `count_events`(=`exclude_unbillable`)로
  직접 확인. "월간 KPI"는 K6 `kpi_series`가 아직 미구현(`NotImplementedYet`)이라
  이벤트 단위 월간 KPI 경로가 따로 없음 — 지금 코드에서 이벤트가 거치는 청구 경로는
  이 함수 하나뿐이다. K6 `usage_snapshot`(카메라·계정 수)은 **다른 분모**(카메라 대수)
  라 이 다섯째 행에 안 섞었다 — 섞으면 "사건" 분모와 "카메라" 분모가 한 칸에서
  갈린다. **이 gap 은 남는다**(⑦ 참고).
- **분모 0 처리**: `seed_events == 0` 이면 `False` + "분모 0, 잴 표본이 없다"로
  명시(그 문구 없이 True 로 적지 않음) — 이 파일 기존 4수도 population 0 을 이미
  `False`+설명으로 다루고 있어 그 관례를 그대로 따름(rc 는 어차피 다른 4수가 이미
  결정).
- **출생 표본**(D-310): `leaking = dict(green, seed_billable_leak=20)` — 씨앗
  전부가 청구 셈에 새는 상태를 빨강으로 잡아야 한다. `self_test()` 에 4갈래
  추가(전부 유출 · 일부 유출 1건 · 분모 0 · 판정 불가) — 전부 통과.
- **현재 실측 안 함**: gx-shell 안에서 라이브로 돌리지는 않았다(호스트에서
  `--self-test` 만 확인) — 오늘 창 안에서 gx-shell 실측까지는 시간이 부족했다.
  **미리 예측**: `seed.py` 자체 문서(§ 앞부분)가 "씨앗 카메라의 `StreamMonitor.
  data_source` 는 기본값 `live` 그대로다(D-514)"라고 이미 적어 뒀고, 씨앗 사건은
  `track_id` 표식도 없다 — `exclude_unbillable` 의 세 갈래(㉠㉡㉢) 중 어느 것도
  지금은 안 걸릴 가능성이 높다. 즉 **오늘 gx-shell 에서 돌리면 빨강이 나올 것으로
  예상**하지만, 이것은 예측이지 실측이 아니다 — 실측은 다음 사람(또는 다음 창)이
  gx-shell 안에서 해야 한다. B 의 이번 턴 배선("발급 순간 배선 5")이 "씨앗 계정"을
  겨눈다고 적혀 있고 "씨앗 사건"(이벤트 행) 자체는 그 5개 목록에 없어 보인다 —
  겹치는지 B 쪽에 확인이 필요하다.

## ④ ㉱ `verify_event_drop.py` · `verify_purge.py` — 오늘 갈랐다

턴 AC 는 둘 다 "불확실(라이브 트래픽/스케줄 의존일 수 있다)"로 남겨 뒀다. 오늘
코드를 다시 읽어 **가른 결과 — 둘 다 미배선(㉮)이지 시간 의존(㉰)이 아니다**:

- `verify_event_drop.py`: `surge_case()` 가 **합성 300건**(`SURGE_INPUT`)을 직접
  만들어 가드 모듈을 돌린다. 트래픽도 큐도 기다리지 않는다(파일 머리말: "호스트에서
  돈다 — Django 설정이 필요 없다"). → `SURGE_INPUT` 을 분모로 배선.
- `verify_purge.py`: `collect()` 가 시드를 **직접 심고** `retention.purge()` 를
  **동기로** 부른다(한 트랜잭션 안에서 재고 되돌린다). cron/주기 작업을 기다리지
  않는다. → `judge()` 의 일곱 수 이름을 `JUDGED_ASPECTS` 로 뽑아 분모로 배선.

## ⑤ 음성 대조

- 6개 미배선 게이트: 각 파일 자체의 `--self-test` 가 기존 양성/음성/출생 표본을
  그대로 유지한 채 전부 통과(내가 추가한 것은 헤더 텍스트뿐, 판정 로직은 안 건드림).
- `verify_seed_p20.py`: 새 4갈래(전부 유출 20/20 · 일부 유출 1/20 · 분모 0 ·
  판정 불가 `None`)를 self_test() 에 심어 **전부 빨강/비초록으로 잡히는지** 확인 —
  통과.
- `deferred:` 2건: `_gate_header.py --self-test` 의 기존 4갈래(양성 1·무when 거절
  1·음성 1·회귀 없음 1)가 그대로 통과 — 내가 새로 쓴 `deferred:RC-1 2026-09-25`
  문자열이 `_DENOM` 정규식(「분모」 낱말)에 우연히 안 걸리는지 실측으로 확인함
  (`judge_measured()` 출력에 "정직한 지연 신고" 문구가 그대로 찍혔다 — 분모 갈래로
  안 새는 것 확인).
- `verify_gate_header.py --self-test`, `_gate_header.py --self-test`,
  `verify_tool_selftest.py` 전부 회귀 없이 통과(아래 자기시험 로그).

## ⑥ 출생 표본(D-310)

새 판정 갈래는 `verify_seed_p20.py` 의 P-251 행 하나뿐이다 — 그 갈래의 출생 표본은
③에 적은 `leaking`(씨앗 전부가 청구로 새는 상태) 이다. 나머지 8개 파일은 **기존
judge()/self_test() 을 안 건드리고 헤더 텍스트만** 달아서, 새 판정 갈래가 아니라
기존 갈래의 분모 배선이다 — `verify_tool_selftest.py` 기준선도 그대로 통과(새로
표본 없이 태어난 도구 0종).

## ⑦ 못 한 것과 왜

- P-251 을 **gx-shell 안에서 라이브로 실측**하지 못했다 — 시간 부족(오늘 저녁
  재부팅 전 끝내야 해서 gx-shell 왕복·로그인 자격 확인까지 벌이지 않음). 코드는
  다 짜 놨고 자기시험은 통과했으나, **실제 씨앗 데이터 위에서 이 다섯째 수가 초록인지
  빨강인지는 아직 안 쟀다.**
- P-251 의 "월간 KPI" 절반(카메라·계정 단위 `usage_snapshot`)은 이 게이트에 안
  넣었다 — "사건" 분모와 "카메라" 분모가 다른 population 이라 한 칸에 섞으면
  분모가 흐려진다고 판단(③에 적음). 카메라 쪽(D-514, `StreamMonitor.data_source`
  기본값 문제)은 **여전히 미해결·미배선**으로 남아 있다 — 다음 창에서 별도 행으로
  다뤄야 한다.
- `verify_perf_budget.py`·`verify_release_candidate.py` 의 진짜 "합격선" 배선은
  RC-1(09-25) 전까지 손 안 댐 — §3 지시 그대로.
- `PIPE_EXIT` 회색 3건(`verify_feature_reach.py:56` 등)은 손 안 댐 — 내 소관 밖의
  기존 발견(턴 AC 부터 있었다), 이번 창 범위 밖.

## ⑧ 지시서/이전 판단 중 틀린 것

- 턴 AC 는 `verify_event_drop.py`·`verify_purge.py` 를 "불확실(트래픽/스케줄
  의존)"로 남겼는데, 오늘 코드를 다시 읽으니 **둘 다 라이브 환경을 안 기다리는
  합성·동기 판정기였다** — ④에 실측 근거 적음. 지시서 §3 Q 행의 "가르시오" 요청대로
  가른 결과가 턴 AC 판단과 다르다.
- 지시서 §3 Q 행의 "미배선 6" 목록(§0 상단)에는 `verify_event_drop`·`verify_purge`
  가 없었다(㉱ 로 별도 취급하라고 돼 있었다) — 결과적으로 이번 창에서는 8개
  (6+2)를 전부 미배선 취급으로 배선했다. 이건 지시서 위반이 아니라 지시서가
  요청한 "가름" 작업 자체의 결과다.

## ⑨ 모르는 것

- `verify_seed_p20.py` P-251 행이 gx-shell 라이브에서 초록인지 빨강인지 — 예측만
  했고 실측 안 함(⑦).
- B 의 "씨앗 계정" 발급 순간 배선이 "씨앗 사건"(이벤트 행)의 청구 유출까지
  같이 막는지 — 모른다. B 쪽 산출물을 봐야 안다.
- `verify_release_candidate.py`/`verify_perf_budget.py` 의 실제 RC-1 합격선
  숫자(무엇을 몇으로 삼을지) — 세종 RC-1 선언문 초안(09-25)이 나와야 안다.

## 자기시험/회귀 로그

```
PYTHONIOENCODING=utf-8 python scripts/verify_alarm_budget.py --self-test      → 통과
PYTHONIOENCODING=utf-8 python scripts/verify_camera_pulse.py --self-test      → 통과
PYTHONIOENCODING=utf-8 python scripts/verify_camera_address.py --self-test    → 통과(5건)
PYTHONIOENCODING=utf-8 python scripts/verify_minio.py --self-test             → 통과
PYTHONIOENCODING=utf-8 python scripts/verify_bundle_api_base.py --self-test   → 전부 통과
PYTHONIOENCODING=utf-8 python scripts/verify_bundle_hash.py --self-test       → 통과
PYTHONIOENCODING=utf-8 python scripts/verify_release_candidate.py --self-test → 통과(4건)
PYTHONIOENCODING=utf-8 python scripts/verify_perf_budget.py --self-test       → 통과
PYTHONIOENCODING=utf-8 python scripts/verify_event_drop.py --self-test        → 통과(9건)
PYTHONIOENCODING=utf-8 python scripts/verify_purge.py --self-test             → 통과
PYTHONIOENCODING=utf-8 python scripts/verify_seed_p20.py --self-test          → 통과(P-251 포함)
PYTHONIOENCODING=utf-8 python scripts/_gate_header.py --self-test             → 통과(회귀 없음)
PYTHONIOENCODING=utf-8 python scripts/verify_gate_header.py --self-test       → 통과
PYTHONIOENCODING=utf-8 python scripts/verify_tool_selftest.py                 → 통과(새로 표본 없이 태어난 도구 0종)
PYTHONIOENCODING=utf-8 python -m py_compile <11개 파일>                        → OK
bash -n docs/agent/verify_gates.sh                                            → SYNTAX_OK
```

삭제 0 · `--no-verify` 안 씀 · 커밋 안 함(작업 트리에만) · 금지구역 안 건드림
(`backend/delivery`·`orders`·`terminals` 등 읽기도 안 함, 이번 일과 무관) ·
`verify_ga_readiness.py`·`ga_readiness.yaml` 안 건드림(N 소유 · diff 에 있는 그
파일들은 N 의 병행 작업) · `verify_backup_recovery.py` 안 건드림(E 가 이미
고쳐 둠, `ALL_GATES` 등재만 함) · 비밀 안 적음.
