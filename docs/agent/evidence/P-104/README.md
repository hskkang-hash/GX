# P-104 · P-93 — 「8영역 ③ = 100」은 다시 잰 수인가, 남은 수인가

**잰 때** 2026-09-07 18:4x (KST) · **차선 P** · HEAD `6cf2c19`

## 물음

지난 턴에 판정기 셋이 **눈이 멀어 있었다**는 것이 드러났고, 그중 하나가 영역 ③의
출처였다: `scripts/verify_tenant_scope.py` 가 **2026-08-22 · 531경로짜리 사진**
(`W0-14/openapi_routes.json`)을 읽고 「라우트가 안 생겼다」를 냈다.
그렇다면 **③ = 100 은 그 눈이 다시 뜨기 전의 수인가, 뒤의 수인가.**

## 답 — ③ = 100 [실측 · 2026-09-07 18:4x 에 다시 쟀다]

옛 수가 남아 있던 것이 아니라, **다시 재도 100 이었다.** 다만 「다시 쟀다」는
말이 성립하려면 네 절을 전부 오늘 실제로 돌렸어야 한다. 돌렸다:

| 절 | 판정기 | 오늘 결과 |
|---|---|---|
| ISO-01 | `backend/tests/test_tenant_isolation.py` | **28 passed** (컨테이너 · 47s) |
| ISO-02 | `scripts/verify_tenant_scope.py` (이 턴에 고침) | **exit 0** · 라우트 705건 |
| ISO-03 | `scripts/verify_route_scope_declared.py` | **exit 0** (정적 눈 518건) |
| ISO-04 | `scripts/check_demo_isolation.py` | **PASS** |
| (보강) | `tests/test_route_tripwire.py` + `test_route_tenant_scope.py` | **16 passed** — 런타임 **전수** 열거 |

### 라우트 수 531 → 705

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell python -c \
      "import django; django.setup(); from common.tenant_scope import _iter_ninja_apis, _join; ..."
    → live route ops: 705   distinct paths: 578

| 출처 | 잰 때 | 라우트 |
|---|---|---|
| `W0-14/openapi_routes.json` (**폐기**) | 2026-08-22 | 531 경로 |
| `D-343/route_inventory.json` (살아 있는 실측본) | 2026-09-07T14:42:43 | 705 오퍼레이션 · 578 경로 |
| 살아 있는 라우터 직접 열거 | 지금 | **705 오퍼레이션 · 578 경로** |

## 무엇을 고쳤나 (P-93)

**판정기가 읽는 자리는 앱이 쓰는 자리여야 한다.**

`verify_tenant_scope.py::_route_paths()` 의 순서를 셋으로 못박았다.

1. **살아 있는 라우터** — `DJANGO_SETTINGS_MODULE` 이 서 있으면 `_iter_ninja_apis()` 로 직접 센다.
   실측본이 라우터보다 적으면 **「실측본이 낡았다」로 멈춘다.**
2. **라우터가 쓴 실측본** — `D-343/route_inventory.json`. 실측 하한
   `ROUTE_OPS_FLOOR = 705` 를 밑돌면 「라우트가 줄었다」가 아니라 **사진이 낡았다**로 멈춘다.
3. **옛 사진으로는 떨어지지 않는다.** 실측본이 없으면 통과가 아니라 **위반**이다 (D-301).

옛 사진은 지우지 않고 **파일 안에 「폐기 · 사유」를 적었다** —
`tenant_census.py` 의 사유문과 W0-14 산출물 여럿이 그 사진을 인용하고 있어서,
지우면 그 인용이 「무엇을 보고 한 말인지」를 잃는다.

## 8영역 출처 대조 (P-93)

이번 실행(18:4x)은 **모든 판정기의 마지막 손질 시각보다 뒤**다 — 가장 늦은 것이
`verify_tenant_scope.py` 09-07 18:43(이 턴의 수정)이다. 그래서 여덟 수는 전부
「고치기 전에 낸 수」가 아니다. 갈리는 것은 **판정기가 읽는 산출물의 나이**다.

| 영역 | 판정기 | 읽는 산출물 | 산출물 쓴 때 | 판정 |
|---|---|---|---|---|
| ① 82% | `verify_ga_readiness` 자체 정규식 (**`gate:` 0개**) · `verify_contract_ac.py`(오늘 exit 0) | `D-309/contract_ac_ledger.yaml` | 09-03 10:51 | **회색** — 대장에 `gate:` 가 한 칸도 없어 ⑧ 대조가 이 영역을 통째로 건너뛴다 |
| ② 80% | `verify_route_inventory` 외 9벌 (전부 오늘 초록) | `D-343/route_inventory.json` (24h 신선도 규칙 있음) | **09-07 16:42** | 실측 |
| ③ 100% | `verify_tenant_scope` · `verify_route_scope_declared` + 시험 3벌 | 살아 있는 라우터 / `D-343` | **지금 / 09-07 16:42** | **실측** |
| ④ 77% | `verify_purge` · `verify_camera_pulse` · `ops_alert_routing` · `verify_front_line_502` (오늘 초록) | 단, OPS-05·OPS-09 증명은 1회성 실행기록 | 08-29 22:46 · 08-30 01:07 | 실측(게이트) + **회색(증명 2건이 8월 실행기록)** |
| ⑤ 71% | `verify_perf_budget` | `PERF-01/load.json` · `PERF-04/budget.json` | 09-05 10:38 · 09-05 20:29 | **회색** — 게이트가 스스로 exit 2 를 냈다 |
| ⑥ 92% | `verify_decision_tools` · `verify_alarm_budget` (오늘 초록) | 코드·대장 직접 | 09-07 09:23 | 실측 |
| ⑦ 89% | `verify_sidebar` · `verify_ui_copy` · `verify_wall_keys` (오늘 초록) | `UX-20/copy_baseline.txt` | 09-07 09:23 | 실측 |
| ⑧ 60% | `verify_clip_extraction` · `verify_retention_declared` · `verify_evidence_chain` (오늘 초록) | `D-373/backup_last.json` | 09-07 09:23 | 실측 |

## 회색 판정기가 머리 수를 먹인다 — 「못 부른 게이트」는 실측이 아니었다

`scripts/verify_readiness_scores.py:388` 이 내는 문장

    ⚠ 위 수는 `verify_ga_readiness` 가 **회색(exit 2)** 인 상태에서 나온 수다
      — 못 부른 게이트가 있다

은 **exit 2 를 만나면 언제나 찍히는 고정 문구**다. 오늘 실측은 다르다:

    [GA] 대장↔게이트 26절 · 게이트 25벌 — 색이 같다 25 · **못 쟀다 1**
    [GA]   ? 못 쟀다: PERF-04 ← scripts/verify_perf_budget.py

**못 부른 게이트는 0벌이다.** 25벌 전부 불렸고, 그중 하나(`verify_perf_budget`)가
**스스로 회색을 냈다** — 회귀 문턱 20% 보다 측정 잡음이 27~80% 로 크고, STATUS 예산
300ms 를 3벌의 p95 가 196–338ms 로 걸친다. 제품의 회색이 아니라 **runserver 라는
측정대의 회색**이고, 게이트가 그렇게 적고 있다(OPS-13 뒤 gunicorn+nginx 에서 다시 잰다).

즉 「못 불렀다」와 「불렀는데 회색을 냈다」가 한 문장에 뭉쳐 있다. 그 둘은 다른 사실이다.

### 정말로 못 부를 수 있는 자리 (구조)

`run_gate()` 가 `None`(못 불렀다)을 내는 길은 셋뿐이다 — 파일 없음 · 120초 초과 · OSError.
그리고 `NEEDS_DJANGO` 6벌은 `GX_ROUTE_CONTAINER`(저장소 밖 `.env.gates`)가 있어야만
컨테이너로 위임된다. 없으면 호스트에서 돌고 **전부 회색**이다 — 실측:

    python scripts/verify_purge.py         → rc=2  「컨테이너 안에서 … 돌린다」
    python scripts/verify_alarm_budget.py  → rc=2
    python scripts/verify_camera_pulse.py  → rc=2
    python scripts/ops_alert_routing.py    → rc=2

대장에서 그 넷을 가리키는 절은 OPS-07b · QA-12 · OPS-15 · OPS-10 이다.
**`.env.gates` 가 없는 사람이 부르면 ④와 ⑥의 게이트 대조가 네 절에서 사라진다.**

## 남은 눈의 한계 — 정적 눈은 살아 있는 표면의 73% 만 본다

    [TRIPWIRE:static] 라우트 518건   ↔   살아 있는 라우터 705 오퍼레이션

`verify_route_scope_declared`(ISO-03)와 트립와이어의 **정적 눈**은 AST 로 518건을 센다.
빠진 187건을 보는 것은 **런타임 눈**(`tests/test_route_tripwire.py`)이고, 오늘 그것도
돌렸다(16 passed). 그러나 그 런타임 눈은 pre-commit 에 없다 — 커밋 시점에는 여전히
518건만 본다. ③이 100 인 것은 **런타임 눈을 오늘 사람이 손으로 돌렸기 때문**이지,
게이트가 매번 그것을 도는 것은 아니다.
