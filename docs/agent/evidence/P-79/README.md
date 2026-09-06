# P-79 — **V 의 첫 판정기.** 직전 대비 시험 델타

[실측 2026-09-06 · 턴 H · 차선 Q] 도구: `scripts/verify_delta.py` · 기준선: 이 폴더의 `delta_baseline.json`

## 왜 만들었나 — ★ 출생 표본

턴 G 에서 차선 셋(E·C·V)이 같은 빨강을 따로 가져왔고 **셋 다 「환경」이라고 불렀고
셋 다 틀렸다.** 그것은 우리가 만든 회귀였다(`--nomigrations` 판별자 한 줄 · P-71).
그 사실은 **수 하나에** 적혀 있었다:

```
[앞] 21 errors in 3.66s
[뒤] 21 passed, 34 warnings in 31.04s
```

**빨강이 8배 빨랐다. 아무것도 안 했으니까.** 아무도 그 수를 안 봤다.

> 원칙(세종): **전체를 보는 자리는 차선이 아니라 V다.**
> 자기 차선 밖에서 온 빨강은 환경처럼 보인다. 옆 차선이 만든 회귀도 그렇게 보인다.

이 사례는 `verify_delta.py::self_test` 에 **fixture 로 박혀 있다**(D-310).
건강하던 갈래가 `21 errors in 3.66s` 로 바뀌면 이 도구는 반드시 빨강을 낸다 —
안 그러면 자기시험이 먼저 빨개진다.

## 기준선 — 어디에 · 어떤 형식으로

**파일**: `docs/agent/evidence/P-79/delta_baseline.json` (하나만 둔다 · D-212)

```jsonc
{
  "schema": 1,
  "threshold": 0.20,          // ±20% — 세종 판정
  "runs": [                   // ★ 시간 순. 판정은 한 갈래(suite)의 최근 두 점을 견준다
    {
      "suite": "backend-unit",       // 갈래 이름. 다른 명령은 다른 갈래다
      "recorded_at": "2026-09-06T…", // UTC
      "commit": "e96ab7d",           // 비우면 현재 HEAD
      "command": "docker exec … pytest tests -q --nomigrations …",
      "tests": 1147,                 // passed+failed+errors+skipped+xfailed+xpassed
      "errors": 0,                   // failed + errors
      "duration_s": 487.40,
      "counts": {"passed": 1144, "skipped": 3, "warnings": 34},
      "summary_line": "1144 passed, 3 skipped, 34 warnings in 487.40s (0:08:07)",
      "source": "기계",              // 문서에서 옮겨 적은 수와 섞지 않는다
      "reason": "",                  // 「환경」이라 적으려면 아래 env 에 이름이 있어야 한다
      "env": {"missing": [], "checked": ["minio","smtp","mount","session"]},
      "note": ""
    }
  ]
}
```

**갈래(suite)** 를 나누는 규칙: **명령이 다르면 다른 갈래다.** `--nomigrations` 있는
실행과 없는 실행은 같은 갈래가 아니다 — 섞으면 P-71 이 만든 격차가 「정상 변동」이 된다.

## 판정 — ±20% 를 넘으면 **회색이 아니라 빨강**

| 재는 것 | 빨강이 되는 조건 | 왜 |
|---|---|---|
| 시험 수 | \|Δ\| > 20% | 걷힌 시험이 달라진 것은 코드가 달라진 것보다 먼저 본다. **0건 수집은 초록처럼 보인다** |
| 오류 수 | 늘었다(건수) | 앞이 0 이면 비율이 없다 — 비율을 못 만드는 자리에서 초록을 내지 않는다 |
| 소요 | \|Δ\| > 20% | **이 수가 P-71 을 잡을 수 있었다.** 아무것도 안 하면 빨리 끝난다 |

**사유란에 「환경」이라고 적으려면 `env.missing` 에 실패 항목의 이름이 있어야 한다**
(`scripts/gate_env.py --require … --json env.json` 이 낸 것). 이름 없는 「환경」은
받지 않는다 — 차선 셋이 그날 적은 것이 정확히 그 이름 없는 「환경」이었다.

점이 하나뿐이면 판정이 아니라 **회색(exit 2)** 이다. 견줄 것이 없는데 내는 초록은
아무것도 재지 않은 것이다(D-301).

## 쓰는 법

```bash
python scripts/verify_delta.py --self-test          # 출생 표본 포함 갈래 7

# ① 실행 하나를 적는다 (출력 파일이 필요하다 — 끊긴 실행을 0건으로 적지 않기 위해)
python scripts/verify_delta.py --record --suite backend-unit \
    --from-file runs/unit_1.txt --env-json env.json \
    --command 'docker exec … pytest tests -q --nomigrations -p no:randomly --ignore=tests/e2e'

# ② 판정 — 갈래마다 최근 두 점
python scripts/verify_delta.py            # 0 초록 · 1 빨강 · 2 회색
python scripts/verify_delta.py --list
```

⚠ `python scripts/verify_delta.py | tail` 은 **앞 명령의 종료 코드를 덮는다.**
색을 보려면 파이프 없이 부르거나 `${PIPESTATUS[0]}` 를 본다.

## 게이트 목록에 넣지 않았다 — 왜

`verify_gates.sh::ALL_GATES` 는 **차선마다** 도는 목록이다. 이 도구는 차선이 아니라
**V(전체를 보는 자리)** 의 것이고, 차선 하나의 기준선에 다른 차선의 실행을 적으면
그 순간 이 도구가 재는 것은 전체가 아니라 그날의 순번이 된다.
V 가 턴마다 직접 부른다.


---

## 이번 턴의 실제 델타 — **첫 판정에서 빨강이 나왔고, 그 빨강은 참이다**

기준선을 이번 턴 수로 채웠다. 같은 HEAD(`e96ab7d`)에서 **같은 명령을 두 벌** 돌렸다 —
「직전 커밋과 대조」를 하려면 작업 중인 저장소를 되감아야 하는데, **다른 차선 다섯이
같은 작업 트리 위에서 일하는 중이라 되감을 수 없다.** 그래서 첫 두 점은 같은 커밋의
두 벌이고, 그것이 재는 것은 **이 도구의 잡음 바닥**이다 — ±20% 문턱이 쓸 만한지를
먼저 알아야 하기 때문이다.

```
$ python scripts/verify_delta.py
[DELTA] [입력] 2점 · 갈래 1종 (backend-unit) · 문턱 ±20%
[DELTA] 갈래 `backend-unit` — e96ab7d(2026-09-06T10:34) → e96ab7d(2026-09-06T10:45)
[DELTA]   시험 수        1,147.00 →   1,152.00       +0.4%
[DELTA]   오류 수            0.00 →       4.00           —
[DELTA]   소요(초)         487.40 →     633.16      +29.9%
[DELTA] **빨강** 오류가 0 → 4 로 4건 늘었다
[DELTA] **빨강** 소요가 +29.9% 움직였다 (487.40s → 633.16s)
exit 1
```

| 재는 것 | 1벌째 (10:34Z) | 2벌째 (10:45Z) | Δ | 색 |
|---|---:|---:|---:|:--|
| 시험 수 | 1,147 | 1,152 | **+0.4%** | 초록 |
| 오류 수 | 0 | **4** | +4건 | **빨강** |
| 소요 | 487.40s | 633.16s | **+29.9%** | **빨강** |

원 요약 줄:

```
[1벌] 1144 passed, 3 skipped, 34 warnings in 487.40s (0:08:07)
[2벌] 4 failed, 1145 passed, 3 skipped, 34 warnings in 633.16s (0:10:33)
```

### 사유 — **「환경」이 아니다. 이름이 있다**

빨강 넷은 전부 한 파일이다:

```
tests/test_be_purge.py::AuditPurgeIsReversibleTest::test_journal_round_trip_restores_the_same_rows
tests/test_be_purge.py::AuditPurgeIsReversibleTest::test_a_tampered_journal_is_not_restored
tests/test_be_purge.py::AuditPurgeIsReversibleTest::test_a_journal_place_that_is_not_a_volume_stops_the_purge
tests/test_be_purge.py::AuditPurgeIsReversibleTest::test_undeclared_journal_place_means_no_purge_at_all
```

**2벌째가 도는 동안 옆 차선이 바로 그 파일들을 고치고 있었다** — 컨테이너에서 본
프로세스 표가 그것을 이름으로 말한다 [실측 2026-09-06 · 기계]:

```
$ docker exec gx-shell ps -eo etime,args | grep pytest
 03:04  python -m pytest tests -q --nomigrations …            ← 이 실행(차선 Q)
 00:57  python -m pytest tests/test_l_retention.py tests/test_be_purge.py
        tests/test_dormant_wiring.py tests/test_be_metering.py -q --nomigrations
```

그리고 그 순간 `backend/common/audit_purge_journal.py` · `backend/common/ops_tasks.py` ·
`backend/config/retention_seed.py` · `backend/config/settings.py` · `backend/tests/test_be_purge.py`
가 **10분 안에 고쳐진 상태**였다.

소요 +29.9% 도 같은 뿌리다 — 8 코어를 두 벌의 pytest 가 나눠 썼다.

> ★ 이것이 P-71 이 다시 온 모양이다. 차선 하나가 보면 「환경 결함」처럼 보이고,
> **전체를 보면 옆 차선의 손이 보인다.** 이번에는 도구가 그것을 빨강으로 냈고,
> 사유란에 `env.missing` 은 비어 있다(환경은 다 있었다 — `gate_env --require mount` 초록).
> **이름 없는 「환경」이 들어설 자리가 없다.**

⚠ 이 4건을 「병합된 회귀」로 읽지 말 것. 옆 차선이 **고치는 도중의 상태**를 잰 것이고,
그 차선이 끝낸 뒤 다시 재야 참값이 나온다. 이 도구가 말한 것은 **「달라졌다, 보라」**이지
「누구의 결함이다」가 아니다.

### 문턱 ±20% 는 쓸 만한가 — **시험 수·오류 수는 그렇다. 소요는 이 환경에서 아니다**

같은 코드·같은 명령의 두 벌이 **소요에서 29.9% 벌어졌다.** 차선 여섯이 8 코어를
나눠 쓰는 이 환경에서 소요의 잡음은 문턱보다 크다 — `verify_perf_budget` 이 p95 에서
이미 배운 것과 같은 모양이다(잡음 20~23% > 문턱 20% → 회귀 판정 회색).

**그래도 소요를 빨강으로 둔다.** 근거: 이 도구가 잡아야 하는 것은 ±30% 의 흔들림이
아니라 **8배(−88%)** 다. 잡음이 문턱을 넘으면 사람이 이름을 대야 하고, 이번 턴에는
그 이름이 나왔다(옆 차선의 pytest). 이름을 못 대는 소요 변화가 쌓이면 그때 문턱을
다시 정한다 — 지금 미리 느슨하게 만들면 P-71 이 그 틈으로 다시 들어온다.
