#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""운영 기반 ③ — **감시 3종.** 죽었을 때 사람이 안다 (D-354 ①).

세 가지만 본다. 더 보면 아무도 안 본다.
--------------------------------------
  ① **살아 있는가** (liveness)  — DB · 캐시 · 객체저장에 닿는가
  ② **밀리는가** (lag)          — 최신 이벤트가 얼마나 오래됐나 · 못 보낸 알림이 쌓였나
  ③ **채워지는가** (fill)       — DB 가 얼마나 컸나 · 최근에 이벤트가 들어왔나

★ 임계값은 **목표가 아니라 출발점**이다 (D-280)
-----------------------------------------------
지금 이 값들은 2026-09-09 첫 측정에서 나온 수를 근거로 **넉넉하게** 잡았다.
운영 데이터가 쌓이면 조이는 것이 맞고, **재기 전에 정한 값이 아니다.**
값 하나하나에 「왜 이 수인가」를 적어 둔다 — 적을 수 없는 임계값은 임계값이 아니다.

★ 「닿지 못했다」와 「0이다」를 가른다 (D-301)
---------------------------------------------
객체저장이 죽어서 못 센 것과 객체가 0개인 것은 다른 사실이다.
못 잰 칸은 `null` 로 나가고 판정은 **UNKNOWN** 이다 — 초록이 아니다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/ops_monitor.py            # 사람이 읽는 표
    docker exec ... python /repo/scripts/ops_monitor.py --check   # 경보용: 0 정상 / 1 경보 / 2 판정 불가
    python scripts/ops_monitor.py --self-test

    ★ `--check` 를 크론에 걸고 exit 1 을 사람에게 보내면 그것이 경보다.
      **보내는 자리(메일·문자·챗)는 고객 환경마다 다르므로 여기서 정하지 않는다** —
      정하면 그 환경에서만 도는 감시가 된다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_ALARM, EXIT_UNKNOWN = 0, 1, 2

OK, ALARM, UNKNOWN = "OK", "ALARM", "UNKNOWN"

#: 임계값 — **왜 이 수인가**를 함께 적는다. 적을 수 없으면 임계값이 아니다.
THRESHOLDS = {
    # ① 살아 있는가
    "db_ping_ms": (500, "DB 왕복 500ms. 첫 측정에서 이벤트 처리 전체가 p95 13ms 였다 — "
                        "왕복 하나가 500ms 면 그건 지연이 아니라 고장이다"),
    # ② 밀리는가
    "latest_event_age_min": (60, "최신 이벤트가 60분보다 오래됐으면 파이프라인이 멈춘 것으로 본다. "
                                 "★ 카메라가 조용한 밤에도 울린다 — 그래서 이 값은 "
                                 "**운영 데이터를 보고 조여야 하는 첫 후보**다"),
    "unsent_deliveries": (10, "못 보낸 알림 10건. F-10 은 30초 내 발송이므로 10건이 쌓였다는 것은 "
                              "발송 경로가 막혔다는 뜻이다"),
    # ③ 채워지는가
    "db_size_gb": (50, "DB 50GB. 지금 4MB 다 — 이 값은 상한이 아니라 **증가를 눈치채는 자리**다"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def judge(signal: str, value, thresholds=THRESHOLDS) -> str:
    """한 신호의 판정. **못 잰 것은 초록이 아니다** (D-301)."""
    if value is None:
        return UNKNOWN
    limit = (thresholds.get(signal) or (None, ""))[0]
    if limit is None:
        return OK
    return ALARM if value > limit else OK


def collect() -> dict:
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.apps import apps
    from django.db import connection

    out: dict = {"measured_at": _now().isoformat(timespec="seconds"), "signals": {}}

    def put(name, value, note=""):
        out["signals"][name] = {"value": value, "verdict": judge(name, value), "note": note}

    # ① 살아 있는가 ────────────────────────────────────────────────────────
    try:
        start = time.perf_counter()
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        put("db_ping_ms", round((time.perf_counter() - start) * 1000, 2))
    except Exception as exc:
        put("db_ping_ms", None, "DB 에 닿지 못했다: %s" % type(exc).__name__)

    try:
        from django.core.cache import cache

        start = time.perf_counter()
        cache.set("ops_monitor_ping", "1", 10)
        alive = cache.get("ops_monitor_ping") == "1"
        out["signals"]["cache_alive"] = {
            "value": alive, "verdict": OK if alive else ALARM,
            "note": "왕복 %.1fms" % ((time.perf_counter() - start) * 1000)}
    except Exception as exc:
        out["signals"]["cache_alive"] = {"value": None, "verdict": UNKNOWN,
                                         "note": "캐시에 닿지 못했다: %s" % type(exc).__name__}

    # ★ [실측 2026-09-18] 앞판은 `default_storage.exists(...)` 를 불러 **예외가 안 나면
    #   닿은 것**으로 읽었다. MinIO 를 실제로 내리고 재어 보니 그 호출은 **예외 없이
    #   False** 를 돌려주었고, 이 신호는 저장소가 죽은 채로 **OK** 를 냈다.
    #
    #     저장소 살아 있을 때   object_store_alive  OK
    #     저장소 내렸을 때      object_store_alive  OK      ← 눈이 감겼다
    #
    #   「없다」와 「못 물어봤다」를 한 값으로 읽은 것이다 — D-301 이 이름 붙인 그 모양이고,
    #   하필 **「살아 있는가」를 보라고 세운 신호**에서 났다.
    #   그래서 저장소에게 **저장소만 답할 수 있는 것**을 묻는다: 버킷의 존재.
    #   닿지 못하면 그 호출은 **예외를 던진다** — 그것이 우리가 원하는 갈림이다.
    #   ⚠ 쓰지 않는다. 감시가 데이터를 만들면 그건 감시가 아니다.
    try:
        from django.conf import settings as _s
        from minio import Minio

        _ep = str(getattr(_s, "MINIO_ENDPOINT", "") or "")
        for _scheme in ("http://", "https://"):
            if _ep.startswith(_scheme):
                _ep = _ep[len(_scheme):]
        _bucket = getattr(_s, "MINIO_STORAGE_MEDIA_BUCKET_NAME", "")
        _c = Minio(_ep.rstrip("/"), access_key=_s.MINIO_ACCESS_KEY,
                   secret_key=_s.MINIO_SECRET_KEY,
                   secure=bool(getattr(_s, "MINIO_USE_HTTPS", False)))
        _found = _c.bucket_exists(_bucket)
        out["signals"]["object_store_alive"] = {
            "value": True, "verdict": OK if _found else ALARM,
            "note": ("저장소가 답했다 · 버킷 %s %s"
                     % (_bucket, "있음" if _found else "**없음** — 닿았지만 담을 곳이 없다"))}
    except Exception as exc:
        # 닿지 못한 것은 **모른다가 아니라 나쁨**이다. 「살아 있는가」의 답은 「아니오」다.
        out["signals"]["object_store_alive"] = {
            "value": False, "verdict": ALARM,
            "note": "저장소에 닿지 못했다: %s %s" % (type(exc).__name__, str(exc)[:80])}

    # ② 밀리는가 ──────────────────────────────────────────────────────────
    try:
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        latest = Event._base_manager.order_by("-occurred_at").values_list(
            "occurred_at", flat=True).first()
        if latest is None:
            put("latest_event_age_min", None, "이벤트가 한 건도 없다 — 「밀렸다」가 아니라 「비었다」")
        else:
            put("latest_event_age_min", round((_now() - latest).total_seconds() / 60, 1))
    except Exception as exc:
        put("latest_event_age_min", None, "재지 못했다: %s" % type(exc).__name__)

    try:
        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        put("unsent_deliveries", Delivery._base_manager.filter(succeeded=False).count())
    except Exception as exc:
        put("unsent_deliveries", None, "재지 못했다: %s" % type(exc).__name__)

    # ③ 채워지는가 ────────────────────────────────────────────────────────
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_database_size(current_database())")
            size = int(cur.fetchone()[0])
        put("db_size_gb", round(size / (1024 ** 3), 3))
    except Exception as exc:
        put("db_size_gb", None, "재지 못했다: %s" % type(exc).__name__)

    try:
        Monitor = apps.get_model("stream_monitors", "StreamMonitor")
        out["signals"]["cameras"] = {"value": Monitor._base_manager.count(), "verdict": OK,
                                     "note": "등록 카메라 수 — 늘고 줄어드는 것이 보인다"}
    except Exception as exc:
        out["signals"]["cameras"] = {"value": None, "verdict": UNKNOWN,
                                     "note": "재지 못했다: %s" % type(exc).__name__}
    return out


def self_test() -> int:
    """★ 출생 표본 — **못 잰 것을 초록으로 세지 않는가** (D-301)."""
    checks = [
        ("★ 출생표본 — 못 잰 값(None)은 UNKNOWN 이다. 초록이 아니다",
         judge("db_ping_ms", None) == UNKNOWN),
        ("임계값을 넘으면 ALARM", judge("db_ping_ms", 5000) == ALARM),
        ("임계값 안이면 OK", judge("db_ping_ms", 12) == OK),
        ("0 은 못 잰 것이 아니다 — 0 은 OK 다", judge("unsent_deliveries", 0) == OK),
        ("임계값이 없는 신호는 OK 로 둔다", judge("무명신호", 1) == OK),
        ("★ 임계값마다 사유가 있다 — 적을 수 없는 임계값은 임계값이 아니다",
         all(len(note) > 10 for _limit, note in THRESHOLDS.values())),
        ("신호가 셋 이상이다 (살아있나·밀리나·채워지나)", len(THRESHOLDS) >= 3),
    ]
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[OPS-MONITOR] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return EXIT_ALARM if bad else EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="경보용 — 0 정상 / 1 경보 / 2 판정 불가")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    report = collect()
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("[OPS-MONITOR] [입력] 신호 %d개 · %s"
              % (len(report["signals"]), report["measured_at"]))
        for name, row in report["signals"].items():
            limit = (THRESHOLDS.get(name) or (None, ""))[0]
            print("  %-7s %-22s %-10s %s"
                  % (row["verdict"], name, row["value"],
                     ("한계 %s · " % limit if limit is not None else "") + (row["note"] or "")))

    verdicts = [row["verdict"] for row in report["signals"].values()]
    if ALARM in verdicts:
        print("[OPS-MONITOR] ★ 경보 — %d개 신호가 한계를 넘었다"
              % sum(1 for v in verdicts if v == ALARM))
        return EXIT_ALARM if args.check else EXIT_OK
    if UNKNOWN in verdicts:
        print("[OPS-MONITOR] 판정 불가 %d개 — **못 잰 것은 초록이 아니다**(D-301)"
              % sum(1 for v in verdicts if v == UNKNOWN))
        return EXIT_UNKNOWN if args.check else EXIT_OK
    print("[OPS-MONITOR] 전 신호 정상")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
