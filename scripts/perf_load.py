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

    print("[PERF-LOAD] [입력] 시나리오 %d종 · 동시 %d · %d라운드 (워밍업 %d라운드 버림)"
          % (len(keys), args.concurrency, args.rounds, WARMUP_ROUNDS))
    results = []
    rc = 0
    for key in keys:
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
        rc = rc or (0 if ok else 1)

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

    if rc == 0:
        print("[PERF-LOAD] 통과 — 오류 0건" +
              ("" if args.budget_ms is None else " · p95 전부 예산 안"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
