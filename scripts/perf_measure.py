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
    print("[PERF] → %s" % args.out)
    print("[PERF] ★ 이 수는 **목표가 아니라 출발점**이다 (D-280).")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
