#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PERF-04 — **회귀의 원인을 이름으로 가른다** (P-198 · 차선 F).

`perf_load.py` 는 **얼마나 느린가**를 잰다. 이 파일은 **어디가 느린가**를 잰다.
둘은 다른 질문이고, 앞의 수만으로는 고칠 자리를 못 찾는다.

한 요청을 **네 조각**으로 가른다 — 추측하지 않고 조각마다 잰다:

    ① 질의 수(N+1)     `CaptureQueriesContext` — 같은 SQL 이 몇 번 도는가
    ② 질의 시간        위 문맥이 주는 `time` 의 합
    ③ 서비스/커널 시간 ①②를 뺀 파이썬 시간 (직렬화 포함)
    ④ 미들웨어 시간    **요청 전체 − 뷰 안에서 잰 시간**
                       겹마다 가르려면 `--ablate` (한 겹씩 빼고 다시 잰다)

★ **프로세스 안에서 잰다** (`django.test.Client`). HTTP 왕복·WSGI·동시성은 여기 없다 —
  `perf_load.py` 의 수와 **같은 수가 아니다.** 이 도구의 쓸모는 절대값이 아니라
  **조각 사이의 비율**이고, 고친 뒤 그 비율이 어떻게 바뀌었는지다.
  (착시 ①「부분을 전체로」를 피하려면 고침의 증거는 언제나 `perf_load` 로 낸다.)

★ 캐시를 비낀다 — 호출마다 `?_b=<난수>`. 질의문자열이 캐시 열쇠에 들어가므로
  그 한 칸이면 `UniversalCacheMiddleware` 적중을 피한다. 캐시 **적중 여부 자체**를
  재려면 `--cache-probe` 를 쓴다(같은 URL 을 두 번 두드려 둘째가 빨라지는가).

컨테이너에서 돈다 (Django 가 거기 있다):

    MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \\
      -e GX_API -e GX_ROUTE_USER -e GX_ROUTE_PASSWORD \\
      gx-shell python /repo/scripts/perf_breakdown.py --out /docs/agent/evidence/PERF-04/breakdown.json

    python /repo/scripts/perf_breakdown.py --self-test     # 판정 규칙만 (Django 없이)

갈래 다섯 — **물음이 다르면 도구도 다르다**

    --trace       질의를 모양별로 세고 **부른 자리**를 적는다 (N+1 의 이름)
    --profile     파이썬 시간을 **함수 이름**으로 가른다 (질의가 적은데 느릴 때)
    --sweep       동시 수를 올려 가며 잰다 — **한 벌이 비싼가 · 서로 막는가**
    --ablate      겹을 하나씩 빼고 잰다 (한 겹이 지배할 때만 쓸모 있다)
    --ab-inproc   **한 프로세스 안에서 스위치 한 칸만** 켰다 껐다 하며 번갈아 잰다
                  ← 이 기계처럼 시끄러운 곳에서 **고침의 몫을 가르는 유일한 방법**이다.
                    질의 수는 정수라 잡음이 없다; 벽시계는 잡음이 효과보다 클 수 있다
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 컨테이너의 마운트는 셋이 따로다 — `/app` 이 backend 다. 이름으로 찾게 해 둔다.
for _cand in ("/app", str(Path(__file__).resolve().parent.parent / "backend")):
    if _cand not in sys.path and Path(_cand).is_dir():
        sys.path.insert(0, _cand)
sys.path.insert(0, str(Path(__file__).resolve().parent))

TAG = "[BREAKDOWN]"
EXIT_OK, EXIT_RED, EXIT_GRAY = 0, 1, 2

#: 회귀가 난 **그 세 자리** (턴 W 실측 · P-198). 기준선과 같은 경로여야 댈 수 있다.
TARGETS: list[tuple[str, str]] = [
    ("STATUS", "/api/dsm/dashboard/link-state"),
    ("SCREEN", "/api/dsm/events/queue"),
    ("F05", "/api/dsm/events?limit=50"),
    # 대조군 — 회귀 표에 없는 자리. 「전부 느린가」와 「이 자리가 느린가」를 가른다.
    ("FRAME", "/api/dsm/dashboard/frame"),
    ("RESPT", "/api/dsm/events/response-times"),
    ("SUMM", "/api/dsm/events/summary"),
]

#: N+1 이라고 부를 문턱. 같은 SQL 모양이 이만큼 반복되면 이름을 붙인다.
NPLUS1_REPEAT = 5


def sql_shape(sql: str) -> str:
    """SQL 한 줄을 **모양**으로 줄인다 — 값이 다른 같은 질의를 한 무리로 센다."""
    out, in_str = [], False
    for ch in sql:
        if ch == "'":
            in_str = not in_str
            if in_str:
                out.append("'?")
            continue
        if in_str:
            continue
        out.append("?" if ch.isdigit() else ch)
    shaped = "".join(out)
    while "?" * 2 in shaped:
        shaped = shaped.replace("??", "?")
    return shaped[:220]


def judge(slice_ms: dict[str, float], *, nplus1: int) -> tuple[str, str]:
    """조각 표 하나에 **이름**을 붙인다. 순수 함수다 — 자기시험이 합성 수치를 먹인다.

    고칠 자리를 하나만 말한다. 「전부 조금씩」은 고칠 자리가 아니다.
    """
    if nplus1 >= NPLUS1_REPEAT:
        return "N+1", "같은 SQL 모양이 %d회 반복된다" % nplus1
    if not slice_ms:
        return "분산", "잰 조각이 없다 — 0 으로 나누지 않는다"
    total = sum(max(0.0, v) for v in slice_ms.values()) or 1.0
    name, worst = max(slice_ms.items(), key=lambda kv: kv[1])
    share = 100.0 * max(0.0, worst) / total
    if share < 40.0:
        return "분산", "한 조각이 40%% 를 못 넘는다 (최대 %s %.0f%%)" % (name, share)
    return name, "%s 가 %.0f%% 를 쓴다 (%.1fms / %.1fms)" % (name, share, worst, total)


# ═══════════════════════════════════════════════════════════════════════════
# 재기 — Django 가 있어야 한다
# ═══════════════════════════════════════════════════════════════════════════
def _boot_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django                                          # noqa: PLC0415

    django.setup()


def _token() -> str | None:
    """제품의 로그인으로 토큰을 받는다. 못 받으면 **못 받았다고 말한다**(회색)."""
    api = os.environ.get("GX_API", "").rstrip("/")
    user = os.environ.get("GX_ROUTE_USER", "")
    password = os.environ.get("GX_ROUTE_PASSWORD", "")
    if not (api and user and password):
        return None
    try:
        from verify_route_alive import login               # noqa: PLC0415
    except ImportError:
        return None
    return login(api, user, password)


def measure_path(client, path: str, token: str, *, reps: int) -> dict:
    """한 자리를 `reps` 번 두드리고 조각으로 가른다."""
    from django.db import connection, reset_queries        # noqa: PLC0415
    from django.test.utils import CaptureQueriesContext    # noqa: PLC0415

    sep = "&" if "?" in path else "?"
    headers = {"HTTP_AUTHORIZATION": "Bearer %s" % token}
    walls: list[float] = []
    q_counts: list[int] = []
    q_ms: list[float] = []
    statuses: Counter = Counter()
    shapes: Counter = Counter()

    for i in range(reps + 2):                   # 앞 둘은 워밍업 — 다른 것을 잰다
        url = "%s%s_b=%d" % (path, sep, random.randrange(10**9))
        reset_queries()
        with CaptureQueriesContext(connection) as ctx:
            started = time.perf_counter()
            resp = client.get(url, **headers)
            elapsed = (time.perf_counter() - started) * 1000.0
        if i < 2:
            continue
        statuses[resp.status_code] += 1
        walls.append(elapsed)
        q_counts.append(len(ctx.captured_queries))
        q_ms.append(sum(float(q.get("time") or 0.0) for q in ctx.captured_queries) * 1000.0)
        for q in ctx.captured_queries:
            shapes[sql_shape(q["sql"])] += 1

    worst_shape, worst_n = ("", 0)
    if shapes:
        worst_shape, worst_n = shapes.most_common(1)[0]
        worst_n = int(round(worst_n / max(1, len(walls))))       # 요청 한 벌당

    return {
        "path": path,
        "reps": len(walls),
        "status": {str(k): v for k, v in statuses.items()},
        "wall_p50_ms": round(statistics.median(walls), 2) if walls else 0.0,
        "wall_mean_ms": round(statistics.fmean(walls), 2) if walls else 0.0,
        "wall_min_ms": round(min(walls), 2) if walls else 0.0,
        "queries": int(round(statistics.fmean(q_counts))) if q_counts else 0,
        "query_ms": round(statistics.fmean(q_ms), 2) if q_ms else 0.0,
        "distinct_shapes": len(shapes),
        "top_shape_per_request": worst_n,
        "top_shape": worst_shape,
    }


def ablate(client_factory, path: str, token: str, *, reps: int,
           middleware: list[str]) -> list[dict]:
    """겹을 **하나씩 빼고** 다시 잰다 — 남는 차가 그 겹의 값이다.

    ★ 앞에서부터 누적으로 빼지 않는다(그러면 앞 겹의 값이 뒤에 묻는다). 한 번에 하나다.
    ★ 빼면 200 이 아니게 되는 겹이 있다 — 그 줄은 **수를 적지 않고 사유를 적는다.**
    """
    from django.test import override_settings              # noqa: PLC0415

    rows: list[dict] = []
    base = measure_path(client_factory(), path, token, reps=reps)
    rows.append({"removed": "(없음 · 전부)", **base})
    for name in middleware:
        rest = [m for m in middleware if m != name]
        with override_settings(MIDDLEWARE=rest):
            try:
                got = measure_path(client_factory(), path, token, reps=reps)
            except Exception as exc:                        # noqa: BLE001
                rows.append({"removed": name, "note": "뺐더니 죽는다: %s" % type(exc).__name__})
                continue
        if list(got["status"]) != list(base["status"]):
            got["note"] = "빼면 상태가 달라진다(%s) — 시간은 대지 않는다" % got["status"]
        got["delta_ms"] = round(base["wall_p50_ms"] - got["wall_p50_ms"], 2)
        rows.append({"removed": name, **got})
    return rows


def trace_queries(client, path: str, token: str) -> list[dict]:
    """한 요청의 **모든 질의**를 모양별로 세고, **누가 불렀는지**를 함께 적는다.

    `connection.execute_wrapper` 를 쓴다 — 질의를 실제로 내보내는 자리라서
    미들웨어·인증·뷰 어디서 났든 전부 지난다. 「몇 개다」는 고칠 자리를 안 알려 준다.
    **누가** 불렀는지가 고칠 자리다.
    """
    import traceback                                       # noqa: PLC0415

    from django.db import connection                       # noqa: PLC0415

    seen: dict[str, dict] = {}

    def wrapper(execute, sql, params, many, context):
        shape = sql_shape(sql)
        row = seen.setdefault(shape, {"shape": shape, "n": 0, "ms": 0.0, "callers": Counter()})
        row["n"] += 1
        #: 우리 코드의 프레임만 남긴다 — django/psycopg 안쪽은 어디서나 같다
        frames = [f for f in traceback.extract_stack()[:-1]
                  if "/site-packages/" not in f.filename and "perf_breakdown" not in f.filename]
        if frames:
            f = frames[-1]
            row["callers"]["%s:%d %s" % (f.filename.split("/")[-1], f.lineno, f.name)] += 1
        t0 = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            row["ms"] += (time.perf_counter() - t0) * 1000.0

    sep = "&" if "?" in path else "?"
    hdr = {"HTTP_AUTHORIZATION": "Bearer %s" % token}
    client.get("%s%s_b=%d" % (path, sep, random.randrange(10**9)), **hdr)   # 워밍업
    with connection.execute_wrapper(wrapper):
        client.get("%s%s_b=%d" % (path, sep, random.randrange(10**9)), **hdr)
    out = []
    for row in sorted(seen.values(), key=lambda r: -r["n"]):
        out.append({"n": row["n"], "ms": round(row["ms"], 2), "shape": row["shape"][:160],
                    "callers": [f"{k} ×{v}" for k, v in row["callers"].most_common(3)]})
    return out


def sweep_http(api: str, token: str, path: str, *, concs: list[int], rounds: int) -> list[dict]:
    """**같은 자리**를 동시 N 으로 올려 가며 HTTP 로 두드린다.

    왜 이것이 필요한가 — `perf_load` 의 수는 동시 10 한 점이다. 한 점으로는
    **요청 한 벌이 비싼 것**과 **여럿이 서로를 막는 것**이 구별되지 않는다.
    둘은 고칠 자리가 다르다:

        p95 ≈ 동시 × (한 벌 값)      → 한 벌이 비싸다. 코드를 줄인다
        p95 ≫ 동시 × (한 벌 값)      → 서로 막는다. 잠금·연결·직렬화를 본다

    ⚠ `perf_load` 는 **동시 N 이 시나리오의 자리 수보다 작으면 이제 멈춘다**
      (`coverage_gap` · 2026-09-20 턴 X). 그전에는 앞의 N 개만 누르고도 시나리오
      이름으로 수를 냈다 — **안 누른 자리에 수가 적혔다.** 그래서 「동시 1」 같은 낮은
      점은 거기서 못 재고, 이 함수가 시나리오가 아니라 **경로 하나**를 받는다.
    """
    from concurrent.futures import ThreadPoolExecutor      # noqa: PLC0415
    from verify_route_alive import hit                     # noqa: PLC0415

    rows = []
    for conc in concs:
        samples: list[float] = []
        bad = 0

        def one(_i):
            sep = "&" if "?" in path else "?"
            url = "%s%s_b=%d" % (path, sep, random.randrange(10**9))
            t0 = time.perf_counter()
            status = hit(api, "GET", url, token)
            return status, (time.perf_counter() - t0) * 1000.0

        with ThreadPoolExecutor(max_workers=conc) as pool:
            for rnd in range(rounds + 1):                  # 첫 라운드는 워밍업
                for status, ms in pool.map(one, range(conc)):
                    if rnd == 0:
                        continue
                    if not (200 <= status < 300):
                        bad += 1
                    samples.append(ms)
        p50 = statistics.median(samples) if samples else 0.0
        p95 = sorted(samples)[min(len(samples) - 1, int(0.95 * len(samples)))] if samples else 0.0
        rows.append({"concurrency": conc, "n": len(samples), "errors": bad,
                     "p50_ms": round(p50, 1), "p95_ms": round(p95, 1),
                     "min_ms": round(min(samples), 1) if samples else 0.0,
                     "throughput_rps": round(1000.0 * conc / p50, 1) if p50 else 0.0})
    return rows


def profile_path(client, path: str, token: str, *, reps: int, top: int) -> list[str]:
    """한 자리를 `reps` 번 두드리며 **파이썬 시간**을 함수 이름으로 가른다.

    질의 수가 작은데도 느리면 남는 것은 파이썬이다. 「미들웨어가 느리다」는
    고칠 자리가 아니다 — **함수 이름**이 고칠 자리다.
    """
    import cProfile                                        # noqa: PLC0415
    import io as _io                                       # noqa: PLC0415
    import pstats                                          # noqa: PLC0415

    sep = "&" if "?" in path else "?"
    hdr = {"HTTP_AUTHORIZATION": "Bearer %s" % token}
    client.get("%s%s_b=%d" % (path, sep, random.randrange(10**9)), **hdr)   # 워밍업

    prof = cProfile.Profile()
    prof.enable()
    for _ in range(reps):
        client.get("%s%s_b=%d" % (path, sep, random.randrange(10**9)), **hdr)
    prof.disable()
    buf = _io.StringIO()
    pstats.Stats(prof, stream=buf).sort_stats("cumulative").print_stats(top)
    return [ln for ln in buf.getvalue().splitlines() if ln.strip()]


def ab_alternate(api_a: str, api_b: str, token: str, *, pairs: int,
                 concurrency: int, rounds: int) -> dict:
    """**같은 코드·같은 데이터·같은 창**에서 스위치 한 칸만 다른 두 서버를 **번갈아** 잰다.

    왜 번갈아 재나 — 이 기계는 조용하지 않다. 한 벌을 다 재고 다른 벌을 재면
    그 사이에 남의 부하가 바뀌고, 그러면 잰 차가 **스위치의 차인지 시각의 차인지**
    구별되지 않는다. A·B·A·B 로 붙여 재면 그 표류가 **두 팔에 똑같이** 실린다.

    ★ 로그인은 **한 번만** 한다 — 제품의 로그인은 IP 기준 분당 5회다(D-460).
      두 서버는 같은 DB 를 보므로 토큰 하나가 둘 다 연다.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import perf_load                                       # noqa: PLC0415

    got: dict[str, list[dict]] = {"A": [], "B": []}
    for i in range(pairs):
        for arm, api in (("A", api_a), ("B", api_b)):
            row = {"pair": i + 1, "api": api}
            for key in sorted(perf_load.SCENARIOS):
                s = perf_load.run_scenario(api, token, key,
                                           concurrency=concurrency, rounds=rounds)
                row[key] = {"p50_ms": s["p50_ms"], "p95_ms": s["p95_ms"],
                            "errors": s["errors"]}
            got[arm].append(row)
            print("    %s 벌%d %-28s %s" % (arm, i + 1, api,
                  " · ".join("%s p50 %6.1f" % (k, row[k]["p50_ms"])
                             for k in sorted(perf_load.SCENARIOS))))
    return got


def ab_inproc(client_factory, path: str, token: str, *, reps: int, pairs: int) -> dict:
    """**한 프로세스 안에서** 스위치를 켰다 껐다 하며 번갈아 잰다.

    왜 이것이 가장 셀 수 있는 수인가 — HTTP 도, WSGI 도, 동시성도, 남의 부하도
    **두 팔에 똑같이** 실린다. 다른 것은 `enabled()` 가 보는 한 칸뿐이다.
    질의 수는 잡음이 없다(정수다) — 그래서 **질의 수의 차가 곧 증거**이고,
    벽시계는 이 기계에서 잡음이 크므로 **참고로만** 적는다.

    ★ 겹은 이미 깔려 있다. 스위치를 끄면 감싸개가 `enabled()` 를 보고 원 함수로
      그냥 지나간다 — 겹을 빼는 것이 아니라 **기억만 끄는 것**이라 나머지는 그대로다.
    """
    from django.test import override_settings              # noqa: PLC0415

    arms: dict[str, list[dict]] = {"켬": [], "끔": []}
    for _ in range(pairs):
        for name, flag in (("켬", True), ("끔", False)):
            with override_settings(CONFIG_READ_CACHE_ENABLED=flag):
                arms[name].append(measure_path(client_factory(), path, token, reps=reps))
    out = {}
    for name, rows in arms.items():
        out[name] = {
            "queries": statistics.median([r["queries"] for r in rows]),
            "query_ms": round(statistics.median([r["query_ms"] for r in rows]), 2),
            "wall_p50_ms": round(statistics.median([r["wall_p50_ms"] for r in rows]), 2),
            "wall_min_ms": round(min(r["wall_min_ms"] for r in rows), 2),
            "runs": rows,
        }
    return out


def self_test() -> int:
    fails = 0
    cases = [
        ("반복이 문턱을 넘으면 N+1 이라 부른다",
         judge({"query_ms": 1.0, "python_ms": 1.0}, nplus1=NPLUS1_REPEAT)[0] == "N+1"),
        ("반복이 없으면 가장 큰 조각을 부른다",
         judge({"query_ms": 90.0, "python_ms": 10.0}, nplus1=1)[0] == "query_ms"),
        ("한 조각이 40%를 못 넘으면 '분산' 이다",
         judge({"a": 30.0, "b": 35.0, "c": 35.0}, nplus1=1)[0] == "분산"),
        ("미들웨어가 압도하면 미들웨어를 부른다",
         judge({"query_ms": 5.0, "python_ms": 5.0, "middleware_ms": 400.0},
               nplus1=1)[0] == "middleware_ms"),
        ("SQL 모양은 값이 달라도 한 무리다",
         sql_shape("SELECT * FROM t WHERE id = 12") == sql_shape("SELECT * FROM t WHERE id = 7")),
        ("SQL 모양은 문자열 값도 지운다",
         sql_shape("SELECT * FROM t WHERE n = 'a'") == sql_shape("SELECT * FROM t WHERE n = 'bb'")),
        ("다른 표는 다른 모양이다",
         sql_shape("SELECT * FROM a") != sql_shape("SELECT * FROM b")),
        ("대상은 기준선과 같은 경로다",
         {"/api/dsm/dashboard/link-state", "/api/dsm/events/queue",
          "/api/dsm/events?limit=50"} <= {p for _n, p in TARGETS}),
        ("빈 조각표에서 0 으로 안 나눈다", judge({}, nplus1=0)[0] == "분산"),
    ]
    for label, ok in cases:
        print("  %-4s %s" % ("OK" if ok else "FAIL", label))
        fails += 0 if ok else 1
    print("%s 자기시험 %d/%d" % (TAG, len(cases) - fails, len(cases)))
    return EXIT_RED if fails else EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="PERF-04 회귀 원인 가르기")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--reps", type=int, default=12)
    ap.add_argument("--only", default="", help="이 문자열이 든 경로만")
    ap.add_argument("--ablate", default="", help="이 경로 하나에 대해 겹을 하나씩 빼고 잰다")
    ap.add_argument("--ab-inproc", action="store_true",
                    help="한 프로세스 안에서 스위치만 켰다 껐다 하며 번갈아 잰다")
    ap.add_argument("--ab", default="",
                    help="'A주소,B주소' — 스위치만 다른 두 서버를 번갈아 잰다")
    ap.add_argument("--ab-pairs", type=int, default=3)
    ap.add_argument("--ab-concurrency", type=int, default=10)
    ap.add_argument("--ab-rounds", type=int, default=5)
    ap.add_argument("--sweep", default="", help="이 자리를 동시 N 을 올려 가며 HTTP 로 잰다")
    ap.add_argument("--concs", default="1,2,5,10", help="--sweep 의 동시 수들")
    ap.add_argument("--rounds", type=int, default=10, help="--sweep 의 라운드")
    ap.add_argument("--profile", default="", help="이 자리의 파이썬 시간을 함수 이름으로 가른다")
    ap.add_argument("--profile-top", type=int, default=45)
    ap.add_argument("--trace", action="store_true",
                    help="질의를 모양별로 세고 **부른 자리**를 적는다")
    ap.add_argument("--cache-probe", action="store_true",
                    help="같은 URL 을 두 번 — 둘째가 빨라지면 캐시가 적중한 것이다")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        _boot_django()
    except Exception as exc:                                # noqa: BLE001
        print("%s **판정 불가** — Django 를 못 세웠다: %s %s" % (TAG, type(exc).__name__, exc))
        return EXIT_GRAY

    token = _token()
    if not token:
        print("%s **판정 불가** — 토큰을 못 받았다 (GX_API · GX_ROUTE_USER · GX_ROUTE_PASSWORD)" % TAG)
        return EXIT_GRAY

    if args.ab:
        api_a, _, api_b = args.ab.partition(",")
        api_a, api_b = api_a.strip().rstrip("/"), api_b.strip().rstrip("/")
        #: ★ `perf_load` 가 어차피 멈추지만(`CoverageGap`), 여기서 먼저 **사유로** 막는다 —
        #:   역추적으로 멈추면 「도구가 깨졌다」로 읽히고, 사유로 멈추면 고칠 것이 보인다.
        import perf_load as _plc                            # noqa: PLC0415

        _short = {k: _plc.coverage_gap(v["calls"], args.ab_concurrency)
                  for k, v in _plc.SCENARIOS.items()}
        _short = {k: w for k, w in _short.items() if w}
        if _short:
            for k, w in sorted(_short.items()):
                print("%s ? %-3s **판정 불가(회색)** — %s" % (TAG, k, w))
            print("%s A/B 는 시나리오 넷을 다 재야 뜻이 선다 — `--ab-concurrency` 를 올려라" % TAG)
            return EXIT_GRAY
        print("%s A/B 번갈아 — A=%s · B=%s · %d쌍 · 동시 %d · %d라운드"
              % (TAG, api_a, api_b, args.ab_pairs, args.ab_concurrency, args.ab_rounds))
        got = ab_alternate(api_a, api_b, token, pairs=args.ab_pairs,
                           concurrency=args.ab_concurrency, rounds=args.ab_rounds)
        import perf_load as _pl                             # noqa: PLC0415

        print("%s 시나리오별 가운데값 (쌍 %d)" % (TAG, args.ab_pairs))
        summary = {}
        for key in sorted(_pl.SCENARIOS):
            a = statistics.median([r[key]["p50_ms"] for r in got["A"]])
            b = statistics.median([r[key]["p50_ms"] for r in got["B"]])
            a95 = statistics.median([r[key]["p95_ms"] for r in got["A"]])
            b95 = statistics.median([r[key]["p95_ms"] for r in got["B"]])
            delta = 100.0 * (a - b) / b if b else 0.0
            summary[key] = {"A_p50": a, "B_p50": b, "A_p95": a95, "B_p95": b95,
                            "delta_pct_vs_B": round(delta, 1)}
            print("    %-3s  A p50 %7.1f (p95 %7.1f) · B p50 %7.1f (p95 %7.1f) · A는 B의 %+.1f%%"
                  % (key, a, a95, b, b95, delta))
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(
                {"measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "how": "스위치 한 칸만 다른 두 서버를 A·B·A·B 로 붙여 쟀다 (표류가 두 팔에 같이 실린다)",
                 "api_a": api_a, "api_b": api_b, "pairs": args.ab_pairs,
                 "concurrency": args.ab_concurrency, "rounds": args.ab_rounds,
                 "summary": summary, "runs": got}, ensure_ascii=False, indent=2),
                encoding="utf-8")
            print("%s 기록 → %s" % (TAG, out))
        return EXIT_OK

    if args.sweep:
        api = os.environ.get("GX_API", "").rstrip("/")
        concs = [int(c) for c in args.concs.split(",") if c.strip()]
        print("%s 동시 곡선 — %s · 동시 %s · %d라운드 (워밍업 1라운드 버림)"
              % (TAG, args.sweep, concs, args.rounds))
        rows = sweep_http(api, token, args.sweep, concs=concs, rounds=args.rounds)
        one = rows[0]["p50_ms"] if rows else 0.0
        for r in rows:
            ideal = one * r["concurrency"]
            print("    동시 %-3d n=%-4d p50 %7.1fms · p95 %7.1fms · 최저 %6.1f · 오류 %d · "
                  "처리량 %6.1f건/초 | 동시×한벌 = %7.1fms → %s"
                  % (r["concurrency"], r["n"], r["p50_ms"], r["p95_ms"], r["min_ms"],
                     r["errors"], r["throughput_rps"], ideal,
                     "선형(한 벌이 비싸다)" if r["p50_ms"] <= ideal * 1.3
                     else "선형 초과(서로 막는다 %.1f배)" % (r["p50_ms"] / max(ideal, 1e-9))))
        payload_sweep = {"path": args.sweep, "rows": rows}
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(
                {"measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "sweep": payload_sweep}, ensure_ascii=False, indent=2), encoding="utf-8")
            print("%s 기록 → %s" % (TAG, out))
        return EXIT_OK

    from django.conf import settings                        # noqa: PLC0415
    from django.test import Client                          # noqa: PLC0415

    def client_factory():
        return Client()

    targets = [(n, p) for n, p in TARGETS if args.only in p]
    print("%s [입력] 자리 %d · 반복 %d (워밍업 2회 버림) · 프로세스 안 측정"
          % (TAG, len(targets), args.reps))

    rows = []
    for name, path in targets:
        got = measure_path(client_factory(), path, token, reps=args.reps)
        got["name"] = name
        verdict, why = judge({"query_ms": got["query_ms"],
                              "not_query_ms": got["wall_p50_ms"] - got["query_ms"]},
                             nplus1=got["top_shape_per_request"])
        got["verdict"], got["why"] = verdict, why
        rows.append(got)
        print("  %-7s %-34s 벽 p50 %7.1fms (최저 %7.1f) · 질의 %3d개 %6.1fms · "
              "모양 %2d종 · 최다모양 %d회/요청  → %s"
              % (name, path[:34], got["wall_p50_ms"], got["wall_min_ms"],
                 got["queries"], got["query_ms"], got["distinct_shapes"],
                 got["top_shape_per_request"], verdict))
        print("          사유: %s" % why)

    payload = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "how": "django.test.Client — 프로세스 안. HTTP 왕복·동시성 없음. perf_load 의 수와 다른 수다",
        "reps": args.reps,
        "middleware_count": len(settings.MIDDLEWARE),
        "rows": rows,
    }

    if args.ab_inproc:
        print("%s 프로세스 안 A/B — 스위치 한 칸만 번갈아 (%d쌍 × %d회)"
              % (TAG, args.ab_pairs, args.reps))
        inproc = {}
        for name, path in targets:
            got = ab_inproc(client_factory, path, token, reps=args.reps, pairs=args.ab_pairs)
            inproc[name] = {"path": path, **{k: {kk: vv for kk, vv in v.items() if kk != "runs"}
                                             for k, v in got.items()}}
            on, off = got["켬"], got["끔"]
            dq = off["queries"] - on["queries"]
            dw = 100.0 * (on["wall_p50_ms"] - off["wall_p50_ms"]) / (off["wall_p50_ms"] or 1)
            print("    %-7s 질의 끔 %3d → 켬 %3d (**%+d개**) · 질의시간 %6.2f → %6.2fms · "
                  "벽 p50 %6.2f → %6.2fms (%+.1f%% · 잡음 큼)"
                  % (name, off["queries"], on["queries"], -dq,
                     off["query_ms"], on["query_ms"],
                     off["wall_p50_ms"], on["wall_p50_ms"], dw))
        payload["ab_inproc"] = inproc

    if args.profile:
        lines = profile_path(client_factory(), args.profile, token,
                             reps=max(5, args.reps // 2), top=args.profile_top)
        print("%s 파이썬 프로파일 — %s" % (TAG, args.profile))
        for ln in lines:
            print("   ", ln)
        payload["profile"] = {"path": args.profile, "lines": lines}

    if args.trace:
        traced = {}
        for name, path in targets:
            rowsq = trace_queries(client_factory(), path, token)
            traced[name] = {"path": path, "queries": sum(r["n"] for r in rowsq), "shapes": rowsq}
            print("%s 질의 추적 — %s (%s · 모두 %d개)"
                  % (TAG, name, path, traced[name]["queries"]))
            for r in rowsq:
                print("    ×%-3d %6.2fms  %s" % (r["n"], r["ms"], r["shape"][:110]))
                print("              ← %s" % " · ".join(r["callers"]))
        payload["trace"] = traced

    if args.cache_probe:
        probe = []
        for name, path in targets:
            c = client_factory()
            url = "%s%s_b=%d" % (path, "&" if "?" in path else "?", random.randrange(10**9))
            hdr = {"HTTP_AUTHORIZATION": "Bearer %s" % token}
            c.get(url, **hdr)                              # 담는다
            t0 = time.perf_counter(); c.get(url, **hdr); first = (time.perf_counter() - t0) * 1000
            t0 = time.perf_counter(); c.get(url, **hdr); second = (time.perf_counter() - t0) * 1000
            hit = second < first * 0.4
            probe.append({"name": name, "path": path, "again_ms": round(first, 1),
                          "again2_ms": round(second, 1), "looks_cached": hit})
            print("  캐시 %-7s 같은 URL 재호출 %.1fms → %.1fms  %s"
                  % (name, first, second, "적중으로 보인다" if hit else "적중 아님"))
        payload["cache_probe"] = probe

    if args.ablate:
        print("%s 겹 하나씩 빼기 — %s" % (TAG, args.ablate))
        abl = ablate(client_factory, args.ablate, token, reps=max(6, args.reps // 2),
                     middleware=list(settings.MIDDLEWARE))
        base = abl[0]["wall_p50_ms"]
        for row in abl[1:]:
            if "note" in row and "wall_p50_ms" not in row:
                print("    %-62s %s" % (row["removed"][-62:], row["note"]))
                continue
            print("    %-62s p50 %7.1fms · 뺀 값 %+7.1fms %s"
                  % (row["removed"][-62:], row["wall_p50_ms"], row.get("delta_ms", 0.0),
                     row.get("note", "")))
        payload["ablation"] = {"path": args.ablate, "base_p50_ms": base, "rows": abl}

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("%s 기록 → %s" % (TAG, out))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
