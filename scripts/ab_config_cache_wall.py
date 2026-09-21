#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""설정 캐시 **벽시계** A/B — **짝을 맞춰** 번갈아 잰다 (PERF-04).

재는 자리가 **둘**이다 — `--concurrency` 가 가른다
----------------------------------------------------
    `--concurrency 1`  (기본)  자리 여섯 · **요청 하나씩** 번갈아 — 쌍이 같은 순간
                               ⇒ **한 벌 값**(p50)을 잰다
    `--concurrency N>1`        자리 여섯 · **창(window) 하나씩** 번갈아 — 창마다 N 갈래가
                               한 팔을 때린다 ⇒ **포화한 서버의 p95** 를 잰다

둘은 **다른 것**을 잰다. 동시 1 은 요청 한 벌의 질의 수가 줄어드는 것을 보고,
동시 10 은 그 줄어든 질의가 **줄 서 있는 서버**에서 무엇을 하는지 본다.
★ **한쪽 수를 다른 쪽에 옮겨 적지 않는다.** 턴 Z 는 동시 1 만 쟀고, 그 수(7~11 ms)는
  동시 10 의 수가 **아니다**. 판에 `concurrency` 를 박는 이유가 이것이다.

★★ 동시 N 에서도 **짝 맞춤·순서 뒤집기는 그대로다.** 바뀌는 것은 짝의 단위뿐이다:
    동시 1  — 짝 = 요청 하나       · a_ms = 그 요청의 벽시계
    동시 N  — 짝 = 창 하나(N갈래) · a_ms = 그 창의 **p95**(`--metric p50` 이면 p50)
  창 하나에 200 아닌 응답이 **하나라도** 있으면 그 짝은 **버린다** — 실패는 빠르고,
  빠른 것을 효과로 읽는 것이 이 저장소가 이미 속은 자리다(턴 Y 자진 ⓑ).

★ 왜 **요청 단위**로 짝을 맞추나
--------------------------------
이 기계는 조용하지 않다. 차선 여덟이 같이 두드린다. 한 팔을 다 재고 다른 팔을 재면
그 사이의 표류가 **스위치의 차인 척한다.** 요청 하나씩 붙여 재면 표류가 두 팔에 거의
똑같이 실리고, **쌍 안에서 먼저 빼면** 그 표류가 상쇄된다.
그리고 쌍마다 **순서를 뒤집는다** — 늘 한 팔을 먼저 재면 「먼저 재는 벌」의 이득이
그 팔에만 실린다.

★★ **오류가 난 쌍은 먼저 버린다** (턴 Y 자진 ⓑ · 이 저장소가 이미 속은 자리)
------------------------------------------------------------------------------
실패 응답(401·5xx)은 **짧은 길로 빨리** 돌아온다. 그래서 오류 난 쌍을 그대로 두면
**「빨라졌다」를 실패에서 읽게 된다.** 이 저장소는 동시 접속 1개라, 재는 동안 누가 같은
계정으로 로그인하면 내 토큰이 죽고 그 뒤가 전부 401 이 된다 — **흔한 일이다.**
그래서 오류 난 쌍은 세지 않고 **버린 수를 말한다**(조용히 안 버린다).

★ **못 증명하면 못 증명했다고 적는다.**
---------------------------------------
판정은 둘을 **모두** 요구한다: ① 쌍의 방향이 한결같은가(부호 비율) ② 쌍차의 가운데가
눈금을 넘는가. 그리고 성한 쌍이 `MIN_PAIRS` 미만이면 **판정하지 않는다** —
쌍 하나는 언제나 한 방향이고, 그것은 판정이 아니라 동어반복이다.

쓰는 법 (두 팔은 **미리** 띄워 둔다 — 한 칸만 다르게)
-----------------------------------------------------
    # 팔 둘: 같은 명령줄 · `CONFIG_READ_CACHE_ENABLED` 만 다르다
    docker exec -d -e CONFIG_READ_CACHE_ENABLED=false gx-shell sh -c \\
        'cd /app && exec python -m gunicorn config.wsgi:application --bind 127.0.0.1:8601 \\
             --workers 4 --threads 4 --worker-class gthread --timeout 120'
    docker exec -d -e CONFIG_READ_CACHE_ENABLED=true  gx-shell sh -c '… --bind 127.0.0.1:8602 …'

    # 토큰 한 번 (재는 동안 아무도 로그인하지 않는다)
    docker exec -e GX_API -e GX_ROUTE_USER -e GX_ROUTE_PASSWORD gx-shell \\
        python /repo/scripts/ab_config_cache_wall.py --login --token-file /tmp/token

    docker exec gx-shell python /repo/scripts/ab_config_cache_wall.py \\
        --a 8601 --b 8602 --pairs 40 --token-file /tmp/token \\
        --out /docs/agent/evidence/PERF-04/<이 벌의 이름>.json

★ `--out` 은 **벌마다 다른 이름**으로 준다. 같은 이름에 덮으면 **앞 벌의 판이 사라진다** —
  턴 Z 에 그 일이 났고, 세 벌 중 둘의 원판이 남지 않았다.

    python scripts/ab_config_cache_wall.py --self-test    # 판정 규칙만 (서버 없이)
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

TAG = "[AB-CFG]"

#: 재는 자리 여섯. 이름은 턴 X `perf_breakdown.py` 의 것과 **같게** 둔다 —
#: 같은 자리를 다른 이름으로 부르면 턴을 넘어 대조할 수 없다.
PATHS: tuple[tuple[str, str], ...] = (
    ("STATUS", "/api/dsm/dashboard/link-state"),
    ("SCREEN", "/api/dsm/events/queue"),
    ("F05", "/api/dsm/events?limit=50"),
    ("FRAME", "/api/dsm/dashboard/frame"),
    ("RESPT", "/api/dsm/events/response-times"),
    ("SUMM", "/api/dsm/events/summary"),
)

#: 성한 쌍이 이 수보다 적으면 **판정하지 않는다** (턴 Y 자진 ⓐ).
MIN_PAIRS = 5

#: 이 기계의 눈금. 쌍차의 가운데가 이 아래면 「구별 못 했다」다
#: (턴 X 에 차선 F 가 잰 잡음 상한 5%).
FLOOR_PCT = 5.0

#: 쌍의 방향이 「한결같다」고 부를 비율. 40쌍에서 30쌍이면 동전으로는 만분의 몇이다.
SIGN_RATIO = 0.70

#: 세션이 끊긴 모양. **느린 것이 아니라 틀린 것**이다.
SESSION_LOST = (401, 403)


# ══════════════════════════════════════════════════════════════════════════
# 1. 판정 — 서버 없이 돈다. 자기시험이 겨누는 과녁이 여기가 전부다.
# ══════════════════════════════════════════════════════════════════════════

def drop_bad_pairs(pairs: list[dict]) -> tuple[list[dict], int]:
    """**오류가 난 쌍을 먼저 버린다.** 버린 수를 함께 돌려준다 (머리말 ★★)."""
    good = [p for p in pairs
            if p["a_code"] == 200 and p["b_code"] == 200]
    return good, len(pairs) - len(good)


def paired_verdict(pairs: list[dict]) -> dict:
    """쌍들에서 판정 하나. **「증명」·「못 증명」·「판정 불가」 셋뿐이다.**

    `b` 가 캐시를 **켠** 팔이라고 본다 — 즉 음수가 「캐시가 빠르다」다.
    """
    good, dropped = drop_bad_pairs(pairs)
    out = {"pairs_seen": len(pairs), "pairs_used": len(good),
           "pairs_dropped": dropped}
    if len(good) < MIN_PAIRS:
        out.update(verdict="판정 불가", reason=(
            "성한 쌍이 %d개 — 눈금(%d) 아래다. 쌍 하나는 언제나 한 방향이고 "
            "그것은 판정이 아니다" % (len(good), MIN_PAIRS)))
        return out

    diffs = [p["b_ms"] - p["a_ms"] for p in good]
    pcts = [100.0 * (p["b_ms"] - p["a_ms"]) / p["a_ms"] for p in good if p["a_ms"]]
    b_faster = sum(1 for d in diffs if d < 0)
    ratio = b_faster / float(len(diffs))
    med_pct = statistics.median(pcts) if pcts else 0.0
    out.update(
        a_p50_ms=round(statistics.median([p["a_ms"] for p in good]), 2),
        b_p50_ms=round(statistics.median([p["b_ms"] for p in good]), 2),
        diff_median_ms=round(statistics.median(diffs), 2),
        diff_median_pct=round(med_pct, 2),
        b_faster_pairs=b_faster,
        sign_ratio=round(ratio, 3),
    )
    consistent = ratio >= SIGN_RATIO or (1.0 - ratio) >= SIGN_RATIO
    if not consistent:
        out.update(verdict="못 증명", reason=(
            "방향이 갈린다 — 켬이 빠른 쌍 %d/%d (%.0f%%). 0 을 가운데 두고 흩어지는 것은 "
            "「효과 있다」가 아니다" % (b_faster, len(diffs), ratio * 100)))
    elif abs(med_pct) < FLOOR_PCT:
        out.update(verdict="못 증명", reason=(
            "가운데 %.1f%% 는 이 기계의 눈금(%.1f%%) 아래다 — 구별 못 했다"
            % (med_pct, FLOOR_PCT)))
    else:
        out.update(verdict="증명", reason=(
            "쌍 %d 중 %d 이 한 방향(%.0f%%)이고 가운데 %.1f%% 가 눈금(%.1f%%)을 넘는다"
            % (len(diffs), max(b_faster, len(diffs) - b_faster),
               max(ratio, 1 - ratio) * 100, med_pct, FLOOR_PCT)))
    return out


# ══════════════════════════════════════════════════════════════════════════
# 2. 두드리기
# ══════════════════════════════════════════════════════════════════════════

def _one(port: int, path: str, token: str, nonce: int) -> tuple[float, int]:
    import urllib.request                                  # noqa: PLC0415

    sep = "&" if "?" in path else "?"
    url = "http://127.0.0.1:%d%s%s_b=%d" % (port, path, sep, nonce)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
            code = resp.status
    except Exception as exc:                               # noqa: BLE001
        code = int(getattr(exc, "code", -1) or -1)
    return (time.perf_counter() - started) * 1000.0, code


def run_path(*, a_port: int, b_port: int, path: str, token: str,
             pairs: int, warmup: int) -> list[dict]:
    for i in range(warmup):
        _one(a_port, path, token, -i - 1)
        _one(b_port, path, token, -i - 1)
    rows = []
    for i in range(pairs):
        # 쌍마다 순서를 뒤집는다 (머리말 ★).
        if i % 2 == 0:
            a_ms, a_code = _one(a_port, path, token, i)
            b_ms, b_code = _one(b_port, path, token, i)
        else:
            b_ms, b_code = _one(b_port, path, token, i)
            a_ms, a_code = _one(a_port, path, token, i)
        rows.append({"pair": i + 1, "a_ms": a_ms, "a_code": a_code,
                     "b_ms": b_ms, "b_code": b_code})
    return rows


def window_stats(lat: list[float], codes: list[int]) -> dict:
    """창 하나의 셈. **서버 없이 도는 순수 함수** — 자기시험이 겨눌 수 있게 떼어 놨다.

    ★ `code` 는 창의 **합격 여부**다. 200 아닌 것이 **하나라도** 있으면 200 이 아니고,
      그러면 `drop_bad_pairs` 가 그 짝을 통째로 버린다. 실패는 빠른 길로 돌아오므로
      섞어 두면 **실패를 효과로** 읽게 된다.
    """
    ordered = sorted(lat)
    bad = sum(1 for c in codes if c != 200)

    def pct(q: float) -> float:
        if not ordered:
            return 0.0
        return ordered[min(len(ordered) - 1, int(len(ordered) * q))]

    return {"n": len(lat), "bad": bad,
            "p50": round(pct(0.50), 2), "p95": round(pct(0.95), 2),
            "p99": round(pct(0.99), 2),
            "mean": round(sum(lat) / len(lat), 2) if lat else 0.0,
            #: ★ **빈 창은 성한 창이 아니다.** `bad == 0` 만 보면 아무것도 못 보낸 창이
            #:   합격으로 들어와 「0 ms」가 효과인 척한다.
            "code": (200 if (bad == 0 and codes)
                     else next((c for c in codes if c != 200), -1))}


def _window(port: int, path: str, token: str, *, concurrency: int,
            reqs: int, tag: int) -> dict:
    """한 창 — **N 갈래가 같은 팔을 동시에** 때린다. 창 하나가 짝의 한 쪽이 된다."""
    import threading                                       # noqa: PLC0415

    lat: list[float] = []
    codes: list[int] = []
    lock = threading.Lock()

    def worker(wid: int) -> None:
        mine_l: list[float] = []
        mine_c: list[int] = []
        for j in range(reqs):
            ms, code = _one(port, path, token, tag * 100000 + wid * 1000 + j)
            mine_l.append(ms)
            mine_c.append(code)
        with lock:
            lat.extend(mine_l)
            codes.extend(mine_c)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(concurrency)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = (time.perf_counter() - t0) * 1000.0

    out = window_stats(lat, codes)
    out["wall_ms"] = round(wall, 1)
    return out


def run_path_concurrent(*, a_port: int, b_port: int, path: str, token: str,
                        windows: int, concurrency: int, reqs: int,
                        warmup: int, metric: str) -> tuple[list[dict], list[dict]]:
    """창 단위 짝 맞춤. **창마다 순서를 뒤집는다** — 먼저 재는 벌의 이득을 한 팔에 싣지 않는다."""
    for i in range(max(1, warmup // 4)):
        _window(a_port, path, token, concurrency=concurrency, reqs=2, tag=-i - 1)
        _window(b_port, path, token, concurrency=concurrency, reqs=2, tag=-i - 1)

    pairs: list[dict] = []
    detail: list[dict] = []
    for i in range(windows):
        if i % 2 == 0:
            wa = _window(a_port, path, token, concurrency=concurrency, reqs=reqs, tag=i * 2)
            wb = _window(b_port, path, token, concurrency=concurrency, reqs=reqs, tag=i * 2 + 1)
        else:
            wb = _window(b_port, path, token, concurrency=concurrency, reqs=reqs, tag=i * 2 + 1)
            wa = _window(a_port, path, token, concurrency=concurrency, reqs=reqs, tag=i * 2)
        pairs.append({"pair": i + 1,
                      "a_ms": wa[metric], "a_code": wa["code"],
                      "b_ms": wb[metric], "b_code": wb["code"]})
        detail.append({"pair": i + 1, "a": wa, "b": wb})
    return pairs, detail


def cred_fingerprint(user: str) -> str:
    """**어느 자격으로 쟀는지**를 판에 남기는 자국 — 값이 아니라 sha256 앞 12자다.

    이 저장소는 **한 계정 한 세션**이다. 그래서 재는 사람은 종종 「비어 있는 계정」으로
    옮겨 타야 하고, 그러면 **판에 적힌 수가 어느 자격의 수인지**가 흐려진다.
    자국을 박아 두면 두 벌이 같은 자격이었는지 **대조할 수 있다** — 값은 안 남는다.
    """
    import hashlib                                         # noqa: PLC0415

    return hashlib.sha256(user.encode("utf-8")).hexdigest()[:12]


def do_login(token_file: str, user_env: str = "GX_ROUTE_USER",
             password_env: str = "GX_ROUTE_PASSWORD") -> int:
    """토큰 **한 번**. 재는 동안 다시 부르지 않는다 — 부르면 제 세션을 제가 끊는다.

    ★ 자격은 **환경 이름으로** 고른다(`--user-env`). 값은 argv 에 0 이다.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django                                          # noqa: PLC0415

    django.setup()
    from verify_route_alive import login                   # noqa: PLC0415

    api = os.environ.get("GX_API", "").rstrip("/")
    user = os.environ.get(user_env, "")
    password = os.environ.get(password_env, "")
    if not (api and user and password):
        print("%s 자격이 없다 — GX_API · %s · %s (이름만)" % (TAG, user_env, password_env))
        return 2
    token = login(api, user, password)
    if not token:
        print("%s 토큰을 못 받았다 — 회색" % TAG)
        return 2
    with open(token_file, "w", encoding="utf-8") as fh:
        fh.write(token)
    with open(token_file + ".who", "w", encoding="utf-8") as fh:
        fh.write("%s %s" % (user_env, cred_fingerprint(user)))
    print("%s 로그인 1회 — %s UTC · 자격 %s(sha256 %s) · 토큰 -> %s"
          % (TAG, time.strftime("%H:%M:%S", time.gmtime()),
             user_env, cred_fingerprint(user), token_file))
    return 0


# ══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    bad = 0

    def check(name, got, want):
        nonlocal bad
        if got != want:
            bad += 1
            print("  FAIL %s: %r != %r" % (name, got, want))
        else:
            print("  ok   %s" % name)

    print("%s 자기시험 — 판정 규칙만 (서버 없이)" % TAG)

    def mk(n, a, b, a_code=200, b_code=200):
        return [{"pair": i + 1, "a_ms": a, "a_code": a_code,
                 "b_ms": b, "b_code": b_code} for i in range(n)]

    check("쌍 1은 판정 불가 (동어반복)",
          paired_verdict(mk(1, 100.0, 80.0))["verdict"], "판정 불가")
    check("쌍 4는 판정 불가", paired_verdict(mk(4, 100.0, 80.0))["verdict"], "판정 불가")
    check("쌍 5 · 한 방향 · 20%p 는 증명",
          paired_verdict(mk(5, 100.0, 80.0))["verdict"], "증명")
    check("한 방향이어도 1% 면 못 증명",
          paired_verdict(mk(10, 100.0, 99.0))["verdict"], "못 증명")

    #: 오류 난 쌍이 **버려지는가** — 이것이 턴 Y 가 속은 자리다.
    poisoned = mk(5, 100.0, 80.0) + mk(20, 100.0, 5.0, a_code=401, b_code=401)
    got = paired_verdict(poisoned)
    check("오류 쌍은 버린다", (got["pairs_used"], got["pairs_dropped"]), (5, 20))
    check("버린 뒤에도 성한 쌍으로 판정", got["verdict"], "증명")

    only_bad = mk(20, 100.0, 5.0, a_code=401, b_code=401)
    check("전부 오류면 판정 불가", paired_verdict(only_bad)["verdict"], "판정 불가")
    check("전부 오류인데 「증명」이 아니다",
          paired_verdict(only_bad).get("diff_median_pct"), None)

    #: 방향이 갈리면 — 0 을 가운데 두고 흩어지는 것은 효과가 아니다.
    mixed = (mk(5, 100.0, 80.0) + mk(5, 100.0, 120.0))
    check("방향이 갈리면 못 증명", paired_verdict(mixed)["verdict"], "못 증명")

    #: 반대 방향(캐시가 **느린** 쪽)도 한결같으면 「증명」이다 — 부호를 가리지 않는다.
    check("반대 방향도 한결같으면 증명",
          paired_verdict(mk(10, 80.0, 100.0))["verdict"], "증명")

    # ── 동시 N(창 단위 짝)의 셈 — 서버 없이 겨눌 수 있는 자리 전부 ──────────────
    lat100 = [float(i) for i in range(1, 101)]             # 1..100 ms
    ok = window_stats(lat100, [200] * 100)
    check("창 p50", ok["p50"], 51.0)
    check("창 p95", ok["p95"], 96.0)
    check("창이 성하면 code=200", ok["code"], 200)
    check("창 p95 는 p50 보다 크다", ok["p95"] > ok["p50"], True)

    #: **하나라도** 200 이 아니면 창 전체가 불합격이다 — 이것이 없으면 401 이 섞인
    #: 창의 낮은 p95 를 「캐시가 빠르다」로 읽는다.
    one_bad = window_stats(lat100, [200] * 99 + [401])
    check("창에 401 이 하나면 창이 불합격", one_bad["code"], 401)
    check("창의 불합격 수를 센다", one_bad["bad"], 1)
    check("불합격 창이 낀 짝은 버려진다",
          paired_verdict([{"pair": 1, "a_ms": 50.0, "a_code": 200,
                           "b_ms": 5.0, "b_code": one_bad["code"]}])["pairs_dropped"], 1)
    check("빈 창은 셈이 0 이고 code 가 -1",
          (window_stats([], [])["p95"], window_stats([], [])["code"]), (0.0, -1))

    print("  => %s" % ("통과" if not bad else "실패 %d건" % bad))
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="설정 캐시 벽시계 A/B (동시 1 · 짝 맞춤)")
    ap.add_argument("--a", type=int, default=8601, help="팔 A 의 포트")
    ap.add_argument("--b", type=int, default=8602,
                    help="팔 B 의 포트 — **여기가 캐시를 켠 팔**이라고 적는다")
    ap.add_argument("--pairs", type=int, default=40)
    ap.add_argument("--warmup", type=int, default=8)
    ap.add_argument("--concurrency", type=int, default=1,
                    help="1 이면 요청 단위 짝 · 2 이상이면 **창 단위 짝**(포화)")
    ap.add_argument("--windows", type=int, default=8,
                    help="동시 N 일 때 창 짝의 수 — MIN_PAIRS 아래면 판정하지 않는다")
    ap.add_argument("--reqs", type=int, default=15,
                    help="동시 N 일 때 창 하나에서 **갈래마다** 보내는 요청 수")
    ap.add_argument("--metric", default="p95", choices=("p95", "p50"),
                    help="동시 N 일 때 짝을 무엇으로 비교하나 — 포화의 질문은 p95 다")
    ap.add_argument("--token-file", default="/tmp/gx_ab_token")
    ap.add_argument("--login", action="store_true", help="토큰만 받고 끝낸다")
    ap.add_argument("--user-env", default="GX_ROUTE_USER",
                    help="자격의 **환경 이름**(값이 아니다) — 한 계정 한 세션이라 옮겨 탈 일이 있다")
    ap.add_argument("--password-env", default="GX_ROUTE_PASSWORD",
                    help="암호의 **환경 이름**(값이 아니다)")
    ap.add_argument("--arm-note", default="A=CONFIG_READ_CACHE_ENABLED=false · B=true",
                    help="두 팔이 무엇이 다른가 — 판에 박힌다")
    ap.add_argument("--out", default="", help="JSON — **벌마다 다른 이름**")
    ap.add_argument("--only", default="",
                    help="★ 재는 자리를 즐인다(쉼표로). 동시 N 에서는 짝의 **수**가 힘이라, "
                         "같은 요청 예산이라면 자리를 즐이고 짝을 늘리는 편이 낫다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.login:
        return do_login(args.token_file, args.user_env, args.password_env)

    if not os.path.exists(args.token_file):
        print("%s 토큰이 없다 — 먼저 `--login`. 익명으로 재면 401 의 왕복을 재게 된다" % TAG)
        return 2
    with open(args.token_file, encoding="utf-8") as fh:
        token = fh.read().strip()
    #: 재는 자격의 **자국**을 판에 옮긴다 — `--login` 이 옆에 써 둔 것을 읽을 뿐이다.
    who = ""
    if os.path.exists(args.token_file + ".who"):
        with open(args.token_file + ".who", encoding="utf-8") as fh:
            who = fh.read().strip()

    started = time.strftime("%H:%M:%S", time.gmtime())
    conc = max(1, args.concurrency)
    metric = args.metric if conc > 1 else "req"
    if conc > 1:
        print("%s **동시 %d(포화)** · 창 짝 %d · 창마다 %d갈래×%d요청 · 짝은 창의 %s"
              " · A=%d B=%d · %s"
              % (TAG, conc, args.windows, conc, args.reqs, args.metric,
                 args.a, args.b, args.arm_note))
        head = ("A " + args.metric, "B " + args.metric, "짝차 가운데", "부호 B<A", "버린 창")
    else:
        print("%s 동시 1 · 쌍 %d · 워밍업 %d(버림) · A=%d B=%d · %s"
              % (TAG, args.pairs, args.warmup, args.a, args.b, args.arm_note))
        head = ("A p50", "B p50", "쌍차 가운데", "부호 B<A", "버린 쌍")
    print("  %-7s %9s %9s %11s %10s %8s  %s"
          % ("자리", head[0], head[1], head[2], head[3], head[4], "판정"))

    payload = {"started_utc": started, "a_port": args.a, "b_port": args.b,
               "arm_note": args.arm_note, "pairs": args.pairs,
               "warmup": args.warmup, "paths": {},
               #: ★ 이 셋이 판에 박혀야 **동시 1 의 수를 동시 10 인 척** 읽지 못한다.
               "concurrency": conc, "pair_unit": "window" if conc > 1 else "request",
               "pair_metric": metric, "windows": args.windows if conc > 1 else None,
               "reqs_per_worker": args.reqs if conc > 1 else None,
               #: ★ 자격은 **`--login` 이 남긴 자국**에서만 읽는다. 재는 벌의
               #:   `--user-env` 기본값을 적으면 **판이 거짓말한다** — 로그인은 다른
               #:   이름으로 했는데 판에는 기본값이 박힌다(턴 AA 에 한 번 났다).
               "cred_fingerprint": who or "(자국 없음 — 어느 자격인지 모른다)"}
    want = {x.strip().upper() for x in args.only.split(",") if x.strip()}
    todo = [(n, p) for n, p in PATHS if not want or n in want]
    if not todo:
        print("%s --only 가 아무 자리도 고르지 못했다 — 회색" % TAG)
        return 2
    payload["paths_measured"] = [n for n, _ in todo]
    proven = unproven = ungraded = 0
    for name, path in todo:
        detail = None
        if conc > 1:
            rows, detail = run_path_concurrent(
                a_port=args.a, b_port=args.b, path=path, token=token,
                windows=args.windows, concurrency=conc, reqs=args.reqs,
                warmup=args.warmup, metric=args.metric)
        else:
            rows = run_path(a_port=args.a, b_port=args.b, path=path, token=token,
                            pairs=args.pairs, warmup=args.warmup)
        v = paired_verdict(rows)
        v["path"] = path
        payload["paths"][name] = {"verdict": v, "rows": rows}
        if detail is not None:
            payload["paths"][name]["windows"] = detail
        if v["verdict"] == "증명":
            proven += 1
        elif v["verdict"] == "못 증명":
            unproven += 1
        else:
            ungraded += 1
        print("  %-7s %9s %9s %11s %6s/%-4s %8d  %s"
              % (name,
                 v.get("a_p50_ms", "-"), v.get("b_p50_ms", "-"),
                 v.get("diff_median_ms", "-"),
                 v.get("b_faster_pairs", "-"), v.get("pairs_used", "-"),
                 v["pairs_dropped"], v["verdict"]))
        if v["verdict"] != "증명":
            print("         · %s" % v["reason"])

    payload["ended_utc"] = time.strftime("%H:%M:%S", time.gmtime())
    payload["tally"] = {"증명": proven, "못 증명": unproven, "판정 불가": ungraded}
    print("\n%s 증명 %d · 못 증명 %d · 판정 불가 %d (자리 %d)"
          % (TAG, proven, unproven, ungraded, len(todo)))

    if args.out:
        # ★ **판정 불가가 전부면 파일을 안 쓴다** — 옛 파일이 방금 잰 것처럼 보이면 안 된다.
        if ungraded == len(todo):
            print("%s 전부 판정 불가 — **파일을 안 썼다.** 없는 것이 맞다" % TAG)
        else:
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            print("%s JSON -> %s" % (TAG, args.out))
    return 0 if proven or unproven else 2


if __name__ == "__main__":
    raise SystemExit(main())
