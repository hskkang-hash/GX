#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""성능 1차 측정 — **먼저 재고, 나온 수를 목표의 출발점으로** (D-354 ② · D-280).

    목표를 먼저 정하지 마십시오 — 먼저 재고, 나온 수를 목표의 출발점으로.
    환경을 반드시 적으십시오(CPU·GPU·메모리·네트워크) — **환경 없는 성능 수치는 착시 ⑤**입니다.

왜 계약이 아니라 영업 때문에 급한가
-----------------------------------
계약 검수에는 한 절도 안 걸린다. 그러나 **「몇 대까지 됩니까」에 답하지 못하면 지자체
제안서를 쓸 수 없다.** 다음 계약을 따는 데는 이것이 첫 질문이다.

재는 것 셋 (D-354 ②)
--------------------
  ① **이벤트 처리 지연** — 검출 하나가 이벤트 행이 되기까지 (K1 `record_detection`)
  ② **알림 발송 지연** — 이벤트 하나가 수신자에게 나가기까지 (K2 `send`)
  ③ **동시 스트림 상한** — 몇 대까지 동시에 도는가

★ ③은 이 환경에서 **끝까지 잴 수 없다** — 그리고 그렇게 적는다 (D-301)
------------------------------------------------------------------------
동시 스트림 상한을 실측하려면 RTSP 원본 N개와 AI 서버가 필요하다. 이 환경에는 둘 다 없다
(`AI_RTSP_PATH=http://ai.invalid/...`). 그래서 이 스크립트는 ③에 대해 **두 가지를 나눠** 적는다:

    · [실측] **선언된 상한** — 설정·코드가 정한 값 (있으면 그 값, 없으면 「선언 없음」)
    · [미측정] **실제 상한** — 무엇이 있어야 잴 수 있는지와 함께

  「선언된 상한」을 「실제 상한」으로 적는 순간 그것이 착시 ①(부착률을 완성으로)이다.

★ 원본 DB 를 더럽히지 않는다
----------------------------
측정은 트랜잭션 안에서 하고 **되돌린다**(`set_rollback(True)`). 측정 때문에 생긴 행이
남으면 다음 측정의 분모가 달라진다 — 측정기가 자기가 재는 세상을 바꾸면 안 된다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/perf_measure.py --out /docs/agent/evidence/D-354/perf.json
    python scripts/perf_measure.py --self-test        # 호스트에서도 돈다

★ **5xx 는 여기서 세지 않는다** (P-84 · 2026-09-06 · 턴 I)
------------------------------------------------------
가용성(5xx) 판정은 **두 줄**이고 그 두 줄은 한 자리에서만 난다:

    ① 개발 기계 수      참고 · runserver N대 · loadavg 를 같은 줄에 적는다
    ② 운영형 인스턴스    `gx-gunicorn-e` / `gx-nginx-e`(8500) — **SLA 정본은 이것뿐**

    python scripts/verify_front_line_502.py --sla-5xx

②를 못 재면 「SLA 미측정 · 사유: 운영형 인스턴스 없음」(회색)이다 — ①의 수를 SLA
칸에 옮겨 적는 길은 없다. 여기(이 파일)에 5xx 수를 따로 적으면 **표가 둘이 되고**,
표가 둘이면 다음 사람이 어느 표를 봐야 하는지 모른다 (D-212).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 몇 번 재는가. 적으면 꼬리가 안 보이고, 많으면 안 돌게 된다.
SAMPLES = 30
#: 앞의 몇 번은 버린다 — 첫 호출은 임포트·연결·캐시 채우기가 섞인다(그건 지연이 아니다).
WARMUP = 5


def percentiles(values: list[float]) -> dict[str, float]:
    """p50·p95·최대. **평균을 쓰지 않는다** — 평균은 꼬리를 숨긴다."""
    if not values:
        return {}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "p50_ms": round(statistics.median(ordered) * 1000, 2),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] * 1000, 2),
        "max_ms": round(ordered[-1] * 1000, 2),
        "min_ms": round(ordered[0] * 1000, 2),
    }


def environment() -> dict:
    """**환경 없는 성능 수치는 착시 ⑤다.** 그래서 수보다 이걸 먼저 적는다."""
    env: dict = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "gpu": "없음 (이 환경에 GPU 가 붙어 있지 않다 — AI 추론은 외부 서버가 한다)",
    }
    # 컨테이너 상한 — 호스트의 코어 수가 아니라 **이 컨테이너에 허락된 몫**이 진짜 분모다.
    for path, key in (("/sys/fs/cgroup/memory.max", "cgroup_memory_max"),
                      ("/sys/fs/cgroup/cpu.max", "cgroup_cpu_max")):
        try:
            with open(path, encoding="utf-8") as fh:
                env[key] = fh.read().strip()
        except OSError:
            env[key] = "읽지 못함"
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal"):
                    env["mem_total"] = line.split(":", 1)[1].strip()
                    break
    except OSError:
        env["mem_total"] = "읽지 못함"
    return env


def declared_stream_ceiling() -> dict:
    """③ **선언된** 동시 스트림 상한. 실측이 아니다 — 설정이 말하는 값이다."""
    from django.conf import settings

    found = {}
    for name in dir(settings):
        if not name.isupper():
            continue
        if any(word in name for word in ("STREAM", "WORKER", "CONCURR", "MAX_")):
            value = getattr(settings, name, None)
            if isinstance(value, (int, str, bool)):
                found[name] = value
    return found


def measure(samples: int = SAMPLES, warmup: int = WARMUP) -> dict:
    """K1·K2 를 실제로 불러 지연을 잰다. **트랜잭션 안에서 하고 되돌린다.**"""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.db import transaction
    from django.utils import timezone as djtz

    from common.tenant_scope import TenantScope
    from kernels.k1_event import services as k1
    from kernels.k2_notify import services as k2

    from django.apps import apps

    StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
    monitor = StreamMonitor._base_manager.order_by("id").first()
    if monitor is None:
        raise RuntimeError("카메라가 한 대도 없다 — 잴 대상이 없다 (D-301)")

    scope = TenantScope.system(reason="성능 1차 측정 (D-354 ②)")
    k1_times: list[float] = []
    k2_times: list[float] = []
    notes: list[str] = []

    with transaction.atomic():
        for i in range(samples + warmup):
            # ★ 논리 시계 — 중복 억제(F-04 5분)가 측정을 삼키지 않게 시각을 벌린다.
            occurred = djtz.now() - djtz.timedelta(minutes=10 * (i + 1))
            start = time.perf_counter()
            result = k1.record_detection(
                scope=scope, stream_monitor_id=monitor.id, event_type="fire",
                severity="critical", occurred_at=occurred, confidence=0.91,
            )
            k1_times.append(time.perf_counter() - start)

            event_id = getattr(getattr(result, "event", None), "id", None) or \
                getattr(result, "event_id", None)
            if event_id:
                start = time.perf_counter()
                try:
                    k2.send(scope=scope, event_id=event_id, respect_suppression=False)
                except Exception as exc:                     # 저하 운전 — 실패도 시간이다
                    notes.append("K2 예외: %s" % type(exc).__name__)
                k2_times.append(time.perf_counter() - start)
        transaction.set_rollback(True)      # ★ 측정기가 자기가 재는 세상을 바꾸지 않는다

    return {
        "event_pipeline": percentiles(k1_times[warmup:]),
        "notify_pipeline": percentiles(k2_times[warmup:]),
        "notes": notes,
        "witness_camera_id": monitor.id,
    }


#: 부하 계단. **1 부터 시작한다** — 1 이 없으면 「부하 없을 때」와 비교할 기준이 없고,
#: 기준이 없으면 "느려졌다" 를 말할 수 없다.
LOAD_STEPS: tuple[int, ...] = (1, 2, 4, 8, 16)

#: 「무너졌다」의 술어. p95 가 **1단계(부하 없음) 대비 몇 배**가 되면 무너진 것으로 보는가.
#: 값의 근거: 계약 AC 가 정한 수가 **아니다**(D-280). 배수로 두는 이유는 절대값이
#: 환경마다 다르기 때문이고, 3배는 「같은 일이 눈에 띄게 느려졌다」의 통상 기준이다.
DEGRADATION_FACTOR: float = 3.0


def measure_under_load(steps=LOAD_STEPS, per_worker: int = 10) -> dict:
    """★ **부하 하 재측정** (D-359) — 동시에 몇이 들어오면 어디서 먼저 무너지는가.

    D-359 가 정한 목적을 그대로 옮긴다:

        **어디서 먼저 무너지는가**를 찾는 것이 목적이다. 절대값은 그 다음이다.

    ★ 이 측정이 **재는 것과 못 재는 것**을 먼저 적는다 (D-301 · 착시 ⑤)
      재는 것    이벤트 쓰기·알림 발송의 **동시성 상한** — DB 연결·락·인덱스가 걸리는 구간
      못 재는 것 **동시 스트림 상한** — RTSP 원본 N개와 AI 추론 서버(GPU)가 없다.
                 그 수를 이 결과에서 유추하면 안 된다. 여기 없는 것은 여기 없다.

      즉 이것은 「카메라 몇 대」의 답이 **아니다.** AI·GPU 없이도 상한이 걸리는 구간이
      있고, 그 구간을 재는 것이다 — 그 둘을 한 수로 적으면 제안서에 잘못된 수가 간다.

    ★ 되돌린다 — 스레드마다 트랜잭션이 따로라 `set_rollback` 을 못 쓴다.
      그래서 만든 행의 id 를 모아 **끝나고 지운다.** 측정기가 자기가 재는 세상을
      바꾸면 다음 측정의 분모가 달라진다.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.apps import apps
    from django.db import connections
    from django.utils import timezone as djtz

    from common.tenant_scope import TenantScope
    from kernels.k1_event import services as k1

    StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
    Event = apps.get_model("stream_monitors", "DetectionEvent")
    monitor = StreamMonitor._base_manager.order_by("id").first()
    if monitor is None:
        raise RuntimeError("카메라가 한 대도 없다 — 잴 대상이 없다 (D-301)")

    scope = TenantScope.system(reason="부하 하 재측정 (D-359)")
    created: list[int] = []
    lock = threading.Lock()
    counter = {"n": 0}
    rows = []

    def one_call() -> float:
        with lock:
            counter["n"] += 1
            nth = counter["n"]
        # ★ 논리 시계 — 중복 억제(F-04 5분)가 측정을 삼키면 **빠른 것이 아니라
        #   안 한 것**이고, 그 둘은 같은 수로 보인다.
        occurred = djtz.now() - djtz.timedelta(minutes=10 * nth)
        start = time.perf_counter()
        result = k1.record_detection(
            scope=scope, stream_monitor_id=monitor.id, event_type="fire",
            severity="critical", occurred_at=occurred, confidence=0.91)
        elapsed = time.perf_counter() - start
        event_id = getattr(result, "event_id", None)
        if event_id:
            with lock:
                created.append(event_id)
        return elapsed

    def worker(n: int) -> list[float]:
        try:
            return [one_call() for _ in range(n)]
        finally:
            connections.close_all()      # 스레드마다 연결이 따로다 — 두면 샌다

    try:
        for workers in steps:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                started = time.perf_counter()
                results = list(pool.map(worker, [per_worker] * workers))
                wall = time.perf_counter() - started
            times = [t for chunk in results for t in chunk]
            stat = percentiles(times)
            stat["workers"] = workers
            stat["calls"] = len(times)
            #: 초당 처리량. **지연만 보면 「느려졌지만 더 많이 처리했다」가 안 보인다.**
            stat["throughput_per_sec"] = round(len(times) / wall, 2) if wall else None
            rows.append(stat)
    finally:
        if created:
            # ★ **분류 등록부를 보고 지운다** (D-270 ③).
            #
            #   왜 면제로 처리하지 않았나: 이것은 모호한 호출이 아니라 **진짜 ORM
            #   삭제**다. 그런 자리에 「이건 괜찮다」를 적어 두면, 다음에 정말 위험한
            #   삭제가 같은 모양으로 들어와도 아무도 안 본다.
            #
            #   그래서 검사한다 — **공용 마스터는 어떤 경우에도 지우지 않는다.**
            #   측정이 자기가 만든 행만 지운다는 것은 지금 이 코드를 읽으면 알지만,
            #   다음 사람이 이 되돌림을 다른 모델에 복사할 때 그 사실이 따라가지 않는다.
            #   등록부 대조는 그때 멈춘다.
            from tests.tenant_classification import SHARED_MASTERS

            label = f"{Event._meta.app_label}.{Event.__name__}"
            if label in SHARED_MASTERS:
                raise RuntimeError(
                    f"{label} 은 공용 마스터다 — 측정 되돌림이 공용 데이터를 "
                    f"지우려 한다. 멈춘다 (D-270 ③)")
            Event._base_manager.filter(pk__in=created).delete()

    baseline = rows[0]["p95_ms"] if rows and rows[0].get("p95_ms") else None
    knee = None
    for row in rows:
        if baseline and row.get("p95_ms") and row["p95_ms"] > baseline * DEGRADATION_FACTOR:
            knee = row["workers"]
            break

    return {
        "steps": rows,
        "baseline_p95_ms": baseline,
        "degradation_factor": DEGRADATION_FACTOR,
        #: ★ **어디서 먼저 무너지는가.** `None` 이면 이 계단 안에서는 안 무너졌다는
        #:   뜻이고, 그것은 「상한이 없다」가 **아니다** — 계단이 짧았을 뿐이다.
        "knee_workers": knee,
        "knee_note": (
            f"동시 {knee} 에서 p95 가 부하 없을 때의 {DEGRADATION_FACTOR}배를 넘었다"
            if knee else
            f"계단 {steps} 안에서는 {DEGRADATION_FACTOR}배를 넘지 않았다 — "
            f"**상한이 없다는 뜻이 아니라 이 계단이 짧다는 뜻이다.** 더 올려 봐야 안다"),
        "not_measured": {
            "concurrent_streams": (
                "RTSP 원본 N개와 AI 추론 서버(GPU)가 없다. 이 결과에서 「카메라 몇 대」를 "
                "유추하면 안 된다 — 여기서 잰 것은 이벤트 쓰기·알림의 동시성이고, "
                "스트림 수집·디코딩·추론은 이 측정에 들어 있지 않다"),
        },
        "cleaned_up_events": len(created),
    }


def self_test() -> int:
    """★ 출생 표본 — **환경 없는 수치**와 **평균으로 꼬리를 숨기는 것**을 막는가."""
    checks = [
        ("★ 출생표본 — 평균이 아니라 p95 를 낸다 (평균은 꼬리를 숨긴다)",
         "p95_ms" in percentiles([0.001] * 19 + [1.0])),
        ("★ 꼬리가 실제로 보인다 (p95 가 p50 보다 크다)",
         percentiles([0.001] * 19 + [1.0])["p95_ms"] >
         percentiles([0.001] * 19 + [1.0])["p50_ms"]),
        ("빈 표본은 빈 결과다 — 0 으로 적지 않는다", percentiles([]) == {}),
        ("표본 수를 함께 낸다 (모수 없는 수는 수가 아니다 · D-301)",
         percentiles([0.01, 0.02])["n"] == 2),
        ("환경에 CPU 수가 들어간다", "cpu_count" in environment()),
        ("환경에 GPU 칸이 **명시적으로** 있다 (없으면 없다고 적는다)",
         "gpu" in environment()),
        ("워밍업을 버린다 — 첫 호출은 지연이 아니다", WARMUP > 0),
    ]
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[PERF] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return EXIT_FAIL if bad else EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/docs/agent/evidence/D-354/perf.json")
    ap.add_argument("--samples", type=int, default=SAMPLES)
    ap.add_argument("--load", action="store_true",
                    help="부하 하 재측정 (D-359) — 계단식으로 올리며 무너지는 자리를 찾는다")
    ap.add_argument("--per-worker", type=int, default=10)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    payload: dict = {"environment": environment(), "samples_requested": args.samples}
    measured = measure(samples=args.samples)
    payload.update(measured)
    payload["stream_ceiling"] = {
        "declared": declared_stream_ceiling(),
        "measured": None,
        "why_unmeasured": (
            "동시 스트림 상한을 실측하려면 RTSP 원본 N개와 AI 서버가 필요하다. "
            "이 환경에는 둘 다 없다(AI_RTSP_PATH=%s). "
            "「선언된 상한」을 「실제 상한」으로 적으면 그것이 착시 ①이다."
            % os.environ.get("AI_RTSP_PATH", "(미설정)")),
        "what_it_takes": [
            "RTSP 원본 N개 (모의 송출기라도 실제 프레임이 흘러야 한다)",
            "AI 추론 서버 1대 (지금은 ai.invalid)",
            "측정 대상 지표: 프레임 드롭률 · CPU/메모리 · 이벤트 지연의 열화 지점",
        ],
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    env = payload["environment"]
    print("[PERF] [입력] 표본 %d회 (워밍업 %d회 버림) · 카메라 id=%s"
          % (args.samples, WARMUP, payload.get("witness_camera_id")))
    print("[PERF] 환경: CPU %s · mem %s · cgroup cpu %s · GPU %s"
          % (env.get("cpu_count"), env.get("mem_total"),
             env.get("cgroup_cpu_max"), env.get("gpu")))
    for key, label in (("event_pipeline", "이벤트 처리"), ("notify_pipeline", "알림 발송")):
        row = payload.get(key) or {}
        if row:
            print("[PERF] %s 지연: p50 %sms · p95 %sms · 최대 %sms (n=%s)"
                  % (label, row["p50_ms"], row["p95_ms"], row["max_ms"], row["n"]))
        else:
            print("[PERF] %s 지연: 표본 없음 — 재지 못했다" % label)
    print("[PERF] 동시 스트림 상한: **미측정** — %s"
          % payload["stream_ceiling"]["why_unmeasured"].split(".")[0])

    if args.load:
        # ★ 부하 하 재측정 (D-359). **부하 없는 수와 나란히 적는다** —
        #   위의 p95 는 「부하 없는 상태의 수」이고, 그 사실이 표에 함께 있어야 한다.
        load = measure_under_load(per_worker=args.per_worker)
        payload["under_load"] = load
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("[PERF] ── 부하 하 재측정 (D-359) ──")
        for row in load["steps"]:
            print("[PERF]   동시 %2d · 호출 %3d · p50 %7.2fms · p95 %7.2fms · "
                  "처리량 %s/s"
                  % (row["workers"], row["calls"], row["p50_ms"], row["p95_ms"],
                     row["throughput_per_sec"]))
        print("[PERF] ★ 어디서 먼저 무너지는가: %s" % load["knee_note"])
        print("[PERF] ★ 여기 없는 것: %s"
              % load["not_measured"]["concurrent_streams"].split(".")[0])
        print("[PERF] 측정으로 생긴 이벤트 %d건을 지웠다" % load["cleaned_up_events"])
    print("[PERF] → %s" % args.out)
    print("[PERF] ★ 이 수는 **목표가 아니라 출발점**이다 (D-280).")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
