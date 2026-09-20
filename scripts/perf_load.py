#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PERF-01 — **부하 시험 도구와 시나리오.** 함수가 아니라 문을 두드린다 (차선 Q).

왜 이 도구가 따로 있나 (`perf_measure.py` 가 이미 있는데)
--------------------------------------------------------
    `scripts/perf_measure.py`  **커널 함수**를 부른다. 한 번에 하나씩. p50/p95 를 낸다
    이 파일                    **HTTP 문**을 두드린다. **여럿이 동시에.**

둘은 다른 것을 잰다. 함수는 12ms 인데 그 함수를 부르는 문이 동시 20에서 2초가 되는 일은
흔하다 — 미들웨어 · 직렬화 · 인증 · 커넥션 풀은 함수 안에 없다. PERF-03 이 낸 수
(K1 p50 12.28ms)를 「응답이 12ms」로 읽으면 그것이 착시 ①(부분을 전체로)이다.

무엇을 재나 — 시나리오 넷
-------------------------
    S1 목록      관제요원이 가장 자주 여는 자리 (이벤트 목록 + 요약 한 줄)
    S2 대시보드  첫 화면 한 벌 (프레임 · 연계 상태)
    S3 단일초점  가장 급한 하나 (큐 · 응답시간)
    S4 섞기      위 셋을 돌아가며 — **실제 관제실은 한 자리만 두드리지 않는다**

★ 이 도구는 **읽기만** 한다. 쓰기 면을 부하로 때리면 그 데이터가 진짜와 섞이고,
  섞이면 나중에 골라낼 수 없다(D-368 이 쓰기 면을 따로 센 그 이유).

★ **재지 못하면 재지 못했다고 말한다** (D-301 · D-400). 서버가 없거나 로그인이 안 되면
  exit 2 다 — 0건을 「부하가 없다」로 읽지 않는다.

★★ **동시 N 은 시나리오의 자리 수 이상이어야 한다** (2026-09-20 · 턴 X · 차선 F).
  한 라운드의 배치는 `calls[i % len(calls)] for i in range(concurrency)` 라서, 동시 N 이
  자리 수보다 작으면 **앞의 N 개만** 눌린다. 그런데도 시나리오 줄은 「S2 대시보드 —
  첫 화면 **한 벌**」이라는 이름으로 p50/p95 를 냈다. **한 번도 안 누른 자리에 수가
  적히는 것**이고, 그것은 이 저장소가 내내 걷어낸 병(제 씨앗을 세는 게이트 · 언제나
  회색인 검사)과 같은 종류다.
  [실측] `--concurrency 1` 로 돌린 `PERF-04/turnx_c1_before.json` 은 **선언된 자리 10 중
  4 개만** 눌렀는데 네 시나리오 전부 수가 적혔다. 이제 그 설정은 **재기 전에 멈추고
  회색(exit 2)** 을 낸다 (`coverage_gap`).
  ⚠ **기준선은 영향이 없다** — 가장 넓은 S4 가 자리 4개이고 기준선은 동시 10 이다.
    `load.json`·`turnx_after_r5.json` 을 열어 세 보면 **빠짐 0**이다. 자기시험이
    그 사실을 매번 다시 센다(「기준선 설정(동시 10)은 전 시나리오를 다 누른다」).
    **과거 수는 한 자도 안 바뀐다.**

    python scripts/perf_load.py --self-test         # 판정 규칙만 (서버 없이)
    python scripts/perf_load.py --list              # 시나리오 표
    python scripts/perf_load.py --scenario S1 --concurrency 10 --rounds 5
    python scripts/perf_load.py --all --out docs/agent/evidence/PERF-01/load.json

컨테이너에서 돈다(서버가 거기 있다):
    docker exec -e GX_API=… -e GX_ROUTE_USER=… -e GX_ROUTE_PASSWORD=… \\
        gx-shell python /repo/scripts/perf_load.py --all --out /docs/agent/evidence/PERF-01/load.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 시나리오 — **화면이 실제로 부르는 자리**만 넣는다
# ═══════════════════════════════════════════════════════════════════════════
#: 값이 든 경로(`/events/4674`)는 넣지 않는다 — 그 순간의 씨앗을 가리키고,
#: 씨앗은 캡처가 끝나며 지워진다(D-347 ④). 없는 id 를 때리면 404 를 재게 된다.
SCENARIOS: dict[str, dict] = {
    "S1": {
        "name": "목록 — 관제요원이 가장 자주 여는 자리",
        "calls": [
            ("GET", "/api/dsm/events?limit=50"),
            ("GET", "/api/dsm/events/summary"),
        ],
    },
    "S2": {
        "name": "대시보드 — 첫 화면 한 벌",
        "calls": [
            ("GET", "/api/dsm/dashboard/frame"),
            ("GET", "/api/dsm/dashboard/link-state"),
        ],
    },
    "S3": {
        "name": "단일 초점 — 가장 급한 하나",
        "calls": [
            ("GET", "/api/dsm/events/queue"),
            ("GET", "/api/dsm/events/response-times"),
        ],
    },
    "S4": {
        "name": "섞기 — 실제 관제실은 한 자리만 두드리지 않는다",
        "calls": [
            ("GET", "/api/dsm/events?limit=50"),
            ("GET", "/api/dsm/dashboard/frame"),
            ("GET", "/api/dsm/events/queue"),
            ("GET", "/api/dsm/events/summary"),
        ],
    },
}

#: ★ **출생 표본** (D-310) — 이 도구를 만들게 한 수. PERF-03 은 커널 함수로
#:   K1 p50 **12.28ms** 를 냈다(2026-09-09). 그 수를 「응답이 12ms」로 읽으면
#:   미들웨어·직렬화·인증·풀이 전부 0ms 라고 말하는 것이다. 문을 두드려야 그 차이가 나온다.
BIRTH_SAMPLE = {"kernel_p50_ms": 12.28, "measured": "2026-09-09 · PERF-03"}

#: 워밍업으로 버릴 라운드. 첫 호출은 커넥션·캐시·임포트를 함께 재므로 **다른 것**이다.
WARMUP_ROUNDS = 1

#: 종료 코드. **0 통과 · 1 빨강(오류·예산 초과) · 2 회색(못 쟀다).**
#: 빨강이 회색을 이긴다 — 잰 실패는 **사실**이고 못 잰 것은 **모름**이다. 사실이 먼저 선다.
#: 그래도 회색은 **언제나 이름으로 적는다**: 회색은 초록이 아니다 (D-301).
EXIT_OK, EXIT_ALARM, EXIT_GRAY = 0, 1, 2


class CoverageGap(RuntimeError):
    """**선언한 자리를 다 누르지 못하는 설정**으로 재려 했다. 수를 내지 않고 멈춘다."""


def coverage_gap(calls: "list | tuple", concurrency: int) -> str | None:
    """이 설정이 시나리오의 **모든 자리를 누르는가.** 못 누르면 사유, 누르면 `None`.

    ★ 순수 함수다 — 자기시험이 서버 없이 먹인다.

    무엇을 막는가 — **한 번도 안 누른 자리에 수가 적히는 것**
    ------------------------------------------------------
    한 라운드의 배치는 `calls[i % len(calls)] for i in range(concurrency)` 다.
    그래서 **동시 N 이 호출 수보다 작으면 앞의 N 개만** 눌리는데, 시나리오 줄은
    여전히 「S2 대시보드 — 첫 화면 **한 벌**」이라는 이름으로 p50/p95 를 낸다.
    그 수는 한 벌의 수가 아니라 **그 한 벌 중 첫 자리의 수**다.

    [실측 2026-09-20 · 턴 X] `--concurrency 1` 로 돌린 `turnx_c1_before.json` 에서
    **선언된 자리 10개 중 4개만** 눌렸다(안 눌린 7자리: `events/summary` ·
    `dashboard/link-state` · `events/response-times` · `dashboard/frame` ·
    `events/queue` · `events/summary`). 그런데 네 시나리오 전부 수가 적혔다.
    **안 눌린 자리에 적힌 수는 수가 아니다** — 이제 그 자리에는 **회색**이 선다.

    ★ 기준선(동시 10)은 **영향을 받지 않는다** [실측 2026-09-20 · 아래 두 파일을
      코드가 아니라 **파일을 열어** 셌다]:

          docs/agent/evidence/PERF-01/load.json      동시 10 → S1 2/2 · S2 2/2 · S3 2/2 · S4 4/4
          docs/agent/evidence/PERF-04/turnx_after_r5.json  동시 10 → 같다 (빠짐 없음)

      가장 넓은 시나리오가 S4(자리 4개)이므로 **동시 10 이면 언제나 전부 눌린다.**
      그래서 이 규칙은 **과거 수를 한 자도 바꾸지 않는다** — 옛 수는 그대로 서고,
      앞으로 안 눌리는 자리만 수 대신 회색을 받는다.

    ⚠ **고르게 눌리는 것까지는 요구하지 않는다.** 동시 10 · 자리 4개면 앞 두 자리가
      라운드마다 한 번 더 눌린다(기준선 S4 가 실제로 `n=15/10/10/15` 다). 그것은
      기준선이 **이미 그렇게 잰 사실**이고, 여기서 고르게 만들면 옛 수와 못 댄다.
      이 함수가 막는 것은 **0회**이지 불균등이 아니다.
    """
    if concurrency >= len(calls):
        return None
    missed = [p for _m, p in list(calls)[concurrency:]]
    return ("동시 %d 로는 이 시나리오의 자리 %d 개를 다 못 누른다 — "
            "**%d 자리가 0회**다 (%s). 안 누른 자리의 수는 수가 아니므로 재지 않는다. "
            "동시 %d 이상으로 돌려라 (기준선은 동시 10)."
            % (concurrency, len(calls), len(missed), ", ".join(missed), len(calls)))


def percentile(values: list[float], pct: float) -> float:
    """p50 · p95. **정렬 뒤 위치**로 낸다 — 표본이 적을 때 보간은 없는 수를 만든다."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(pct / 100.0 * len(ordered) + 0.5)) - 1))
    return ordered[idx]


def judge(summary: dict, *, budget_ms: float | None) -> tuple[bool, str]:
    """한 시나리오의 판정. **순수 함수다** — 자기시험이 합성 수치를 먹인다.

    · 오류가 하나라도 있으면 빨강. 느린 것보다 **틀린 것**이 먼저다
    · 예산을 줬는데 p95 가 넘으면 빨강
    · 예산이 없으면 **판정하지 않는다** — 첫 수는 기준선이지 합격선이 아니다
    """
    if summary.get("errors", 0) > 0:
        return False, "오류 %d건 — 느린 것보다 틀린 것이 먼저다" % summary["errors"]
    if budget_ms is None:
        return True, "첫 수(기준선) — 예산이 없으므로 합격·불합격을 말하지 않는다"
    if summary.get("p95_ms", 0) > budget_ms:
        return False, "p95 %.0fms > 예산 %.0fms" % (summary["p95_ms"], budget_ms)
    return True, "p95 %.0fms ≤ 예산 %.0fms" % (summary["p95_ms"], budget_ms)


def run_scenario(api: str, token: str, key: str, *, concurrency: int,
                 rounds: int) -> dict:
    """시나리오 하나를 **동시 N** 으로 `rounds` 번 돈다."""
    from verify_route_alive import hit                    # noqa: PLC0415

    calls = SCENARIOS[key]["calls"]
    #: ★ **재기 전에 멈춘다.** 잰 뒤에 「덜 눌렸다」를 덧붙이면 그 수가 먼저 읽히고,
    #:   먼저 읽힌 수는 옮겨 적힌다. 수를 아예 만들지 않는 것이 유일하게 듣는 방법이다.
    gap = coverage_gap(calls, concurrency)
    if gap:
        raise CoverageGap("%s: %s" % (key, gap))
    samples: list[float] = []
    per_call: dict[str, list[float]] = {}
    errors: list[str] = []

    def one(call):
        method, path = call
        started = time.perf_counter()
        status = hit(api, method, path, token)
        elapsed = (time.perf_counter() - started) * 1000.0
        return path, status, elapsed

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for round_no in range(rounds + WARMUP_ROUNDS):
            batch = [calls[i % len(calls)] for i in range(concurrency)]
            for path, status, elapsed in pool.map(one, batch):
                if round_no < WARMUP_ROUNDS:
                    continue                 # 워밍업은 버린다 — 다른 것을 재고 있다
                if not (200 <= status < 300):
                    errors.append("%s -> %s" % (path, status))
                samples.append(elapsed)
                per_call.setdefault(path, []).append(elapsed)

    return {
        "scenario": key,
        "name": SCENARIOS[key]["name"],
        "concurrency": concurrency,
        "rounds": rounds,
        "requests": len(samples),
        #: ★ **눌린 자리를 수와 같은 칸에 적는다** (턴 X · ③). 읽는 사람이 `per_call`
        #:   의 열쇠를 세어 보지 않아도 「선언 4 · 눌린 4」가 수 옆에 서 있게 한다.
        #:   `coverage_gap` 이 0회를 막으므로 이 둘은 늘 같아야 한다 — 다르면 버그다.
        "coverage": {"declared": len(calls),
                     "pressed": len(per_call),
                     "declared_calls": [p for _m, p in calls]},
        "errors": len(errors),
        "error_detail": sorted(set(errors))[:10],
        "p50_ms": round(percentile(samples, 50), 1),
        "p95_ms": round(percentile(samples, 95), 1),
        "max_ms": round(max(samples), 1) if samples else 0.0,
        "mean_ms": round(statistics.fmean(samples), 1) if samples else 0.0,
        "per_call": {p: {"n": len(v), "p50_ms": round(percentile(v, 50), 1),
                         "p95_ms": round(percentile(v, 95), 1)}
                     for p, v in sorted(per_call.items())},
    }


def self_test() -> int:
    fails = 0
    cases = [
        ("오류가 있으면 예산과 무관하게 빨강",
         judge({"errors": 1, "p95_ms": 1.0}, budget_ms=10_000)[0] is False),
        ("예산이 없으면 판정하지 않는다(초록)",
         judge({"errors": 0, "p95_ms": 99_999}, budget_ms=None)[0] is True),
        ("예산을 넘으면 빨강",
         judge({"errors": 0, "p95_ms": 501}, budget_ms=500)[0] is False),
        ("예산 안이면 초록",
         judge({"errors": 0, "p95_ms": 499}, budget_ms=500)[0] is True),
        ("p50 은 가운데다", percentile([1, 2, 3, 4, 5], 50) == 3),
        ("p95 는 꼬리다", percentile([1, 2, 3, 4, 100], 95) == 100),
        ("빈 표본에서 0 을 0 이라 말한다", percentile([], 95) == 0.0),
        ("시나리오에 값이 든 경로가 없다",
         all("{" not in p and not any(seg.isdigit() for seg in p.split("/"))
             for s in SCENARIOS.values() for _m, p in s["calls"])),
        ("시나리오는 읽기뿐이다",
         all(m == "GET" for s in SCENARIOS.values() for m, _p in s["calls"])),

        # ── [턴 X · ③] 안 눌린 자리에 수가 적히지 않는다 ──────────────────────
        ("동시 N 이 호출 수보다 작으면 회색 사유를 낸다",
         coverage_gap([("GET", "/a"), ("GET", "/b")], 1) is not None),
        ("그 사유가 **안 눌리는 자리의 이름**을 댄다",
         "/b" in (coverage_gap([("GET", "/a"), ("GET", "/b")], 1) or "")),
        ("동시 N 이 호출 수와 같으면 통과다",
         coverage_gap([("GET", "/a"), ("GET", "/b")], 2) is None),
        ("동시 N 이 더 크면 통과다 (불균등은 막지 않는다)",
         coverage_gap([("GET", "/a"), ("GET", "/b"), ("GET", "/c"), ("GET", "/d")], 10) is None),
        #: ★ 기준선이 쓴 그 설정이 **지금도 통과하는지**를 코드가 직접 센다.
        #:   주석에 적어 둔 「동시 10 은 영향 없다」가 다음 사람의 믿음이 아니라
        #:   **돌아가는 검사**가 되는 자리다. 시나리오가 늘어 자리가 11개가 되는 날
        #:   이 줄이 먼저 빨개진다.
        ("기준선 설정(동시 10)은 **전 시나리오**를 다 누른다",
         all(coverage_gap(s["calls"], 10) is None for s in SCENARIOS.values())),
        ("가장 넓은 시나리오의 자리 수가 10 을 넘지 않는다",
         max(len(s["calls"]) for s in SCENARIOS.values()) <= 10),
        ("회색과 빨강은 다른 종료 코드다",
         EXIT_OK == 0 and EXIT_ALARM == 1 and EXIT_GRAY == 2),
    ]
    for label, ok in cases:
        print("  %-4s %s" % ("OK" if ok else "FAIL", label))
        fails += 0 if ok else 1
    if fails:
        print("[PERF-LOAD] 자기시험 %d건 실패" % fails)
        return 1
    print("[PERF-LOAD] 자기시험 %d건 통과 (출생 표본: 커널 p50 %.2fms — 문이 아니라 함수의 수)"
          % (len(cases), BIRTH_SAMPLE["kernel_p50_ms"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="PERF-01 부하 시험 도구")
    ap.add_argument("--scenario", choices=sorted(SCENARIOS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--budget-ms", type=float, default=None,
                    help="p95 예산. 안 주면 첫 수(기준선)로만 적는다")
    ap.add_argument("--out", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.list:
        for key, spec in sorted(SCENARIOS.items()):
            print("  %-3s %-45s %d호출" % (key, spec["name"], len(spec["calls"])))
        return 0

    keys = sorted(SCENARIOS) if args.all else ([args.scenario] if args.scenario else ["S4"])

    #: ★ [턴 X · ③] **자리를 다 못 누르는 설정이면 로그인하기 전에 멈춘다.**
    #:   로그인은 IP 기준 분당 5회다(D-460) — 어차피 못 잴 벌에 그 몫을 쓰지 않는다.
    #:   그리고 「재고 나서 회색」보다 「재기 전에 회색」이 낫다: 수가 만들어지지 않으면
    #:   옮겨 적힐 수도 없다.
    gaps = {k: coverage_gap(SCENARIOS[k]["calls"], args.concurrency) for k in keys}
    gaps = {k: why for k, why in gaps.items() if why}
    for key, why in sorted(gaps.items()):
        print("[PERF-LOAD] ? %-3s **판정 불가(회색)** — %s" % (key, why))
    measurable = [k for k in keys if k not in gaps]
    if not measurable:
        print("[PERF-LOAD] **아무것도 안 쟀다** — 고른 시나리오 %d종이 전부 위 사유다. "
              "회색은 초록이 아니다 (D-301)." % len(keys))
        #: ⚠ 안 썼다는 것을 **말한다.** 안 쓰면 그 경로의 **옛 파일이 그대로 남고**,
        #:   남은 파일은 방금 잰 것처럼 보인다 — 「재지 못했다」가 조용해지는 자리가 거기다.
        if args.out:
            print("[PERF-LOAD] ⚠ `%s` 에 **아무것도 안 썼다.** 그 경로에 옛 파일이 있으면 "
                  "그것은 **이번 수가 아니다** — 날짜(`measured_at`)를 보고 쓰라." % args.out)
        return EXIT_GRAY

    from verify_route_alive import login                  # noqa: PLC0415

    api = os.environ.get("GX_API", "").rstrip("/")
    user = os.environ.get("GX_ROUTE_USER", "")
    password = os.environ.get("GX_ROUTE_PASSWORD", "")
    if not (api and user and password):
        print("[PERF-LOAD] **판정 불가** — 자격증명이 없다 "
              "(GX_API · GX_ROUTE_USER · GX_ROUTE_PASSWORD)")
        return 2
    token = login(api, user, password)
    if not token:
        print("[PERF-LOAD] **판정 불가** — 로그인 실패. %s 가 서 있는가 (동시 접속 1개다)" % api)
        return 2

    print("[PERF-LOAD] [입력] 시나리오 %d종%s · 동시 %d · %d라운드 (워밍업 %d라운드 버림)"
          % (len(measurable),
             "" if not gaps else " (회색 %d종 제외 · 위 사유)" % len(gaps),
             args.concurrency, args.rounds, WARMUP_ROUNDS))
    results = []
    #: 회색이 하나라도 있으면 통과로 끝나지 않는다. 빨강이 나면 빨강이 이긴다.
    rc = EXIT_GRAY if gaps else EXIT_OK
    for key, why in sorted(gaps.items()):
        results.append({"scenario": key, "name": SCENARIOS[key]["name"],
                        "concurrency": args.concurrency, "rounds": args.rounds,
                        "measured": False, "verdict": "GRAY", "why": why})
    for key in measurable:
        summary = run_scenario(api, token, key, concurrency=args.concurrency,
                               rounds=args.rounds)
        ok, why = judge(summary, budget_ms=args.budget_ms)
        summary["verdict"] = "OK" if ok else "ALARM"
        summary["why"] = why
        results.append(summary)
        print("  %-3s %-42s n=%-4d p50 %6.1fms · p95 %6.1fms · 최대 %6.1fms · 오류 %d  [%s]"
              % (key, summary["name"][:42], summary["requests"], summary["p50_ms"],
                 summary["p95_ms"], summary["max_ms"], summary["errors"],
                 summary["verdict"]))
        for path, stat in summary["per_call"].items():
            print("        %-46s n=%-4d p50 %6.1fms · p95 %6.1fms"
                  % (path, stat["n"], stat["p50_ms"], stat["p95_ms"]))
        if summary["error_detail"]:
            for line in summary["error_detail"]:
                print("        ✗ %s" % line)
        #: 빨강은 회색을 **덮는다** — 잰 실패는 사실이고 못 잰 것은 모름이다.
        #: 그래도 회색 줄은 위에 이미 이름으로 찍혔다(색을 지우는 것이 아니다).
        if not ok:
            rc = EXIT_ALARM

    if args.out:
        payload = {
            "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "api": api,
            "concurrency": args.concurrency,
            "rounds": args.rounds,
            "warmup_rounds": WARMUP_ROUNDS,
            "budget_ms": args.budget_ms,
            "birth_sample": BIRTH_SAMPLE,
            "note": ("문을 두드린 수다. 커널 함수의 수(PERF-03)와 **같은 것이 아니다** — "
                     "미들웨어·직렬화·인증·커넥션 풀은 함수 안에 없다."),
            "scenarios": results,
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[PERF-LOAD] 기록 → %s" % out)

    if rc == EXIT_OK:
        print("[PERF-LOAD] 통과 — 오류 0건 · 선언한 자리 전부 눌렀다" +
              ("" if args.budget_ms is None else " · p95 전부 예산 안"))
    elif rc == EXIT_GRAY:
        print("[PERF-LOAD] **회색(exit 2)** — 시나리오 %d종을 못 쟀다(위 ? 줄). "
              "회색은 초록이 아니다 (D-301)." % len(gaps))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
