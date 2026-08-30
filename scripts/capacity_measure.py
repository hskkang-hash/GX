#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""용량 측정 ①② — **저장 대당 MB/s** 와 **추론 제외 상한** (D-372 · D-354 ②).

왜 계약이 아니라 영업 때문에 급한가
-----------------------------------
계약 검수에는 한 절도 안 걸린다. 그러나 **「몇 대까지 됩니까 · 디스크가 얼마나
필요합니까」에 답하지 못하면 지자체 제안서를 쓸 수 없다.** 다음 계약의 첫 질문이다.

★ 이 도구가 가장 조심하는 것 — **가정을 실측인 척하지 않는다** (D-322 · D-280)
------------------------------------------------------------------------------
견적은 언제나 이렇게 생겼다:

        [실측] 이벤트 한 건이 차지하는 바이트
      × [입력] 대당 이벤트율 (건/시간)          ← **우리가 정하는 수가 아니다**
      × [실측] 카메라 대수
      = [산출] 대당 MB/s

가운데 줄이 가정이다. 그것을 상수로 코드에 박으면 **산출값이 실측처럼 보인다** —
그리고 그 수가 제안서에 들어간다. 그래서 이 도구는 이벤트율을 **인자로만** 받고,
안 주면 값을 내지 않는다. 대신 **시나리오 표**를 낸다: 「분당 1건이면 이만큼,
10건이면 이만큼」. 고객이 자기 현장의 수를 고르는 것이 옳다.

★ 이 환경에서 잴 수 없는 것을 **적는다** (D-301)
------------------------------------------------
[실측 2026-09-11] 이 DB 의 `DetectionEvent` 는 **0건**이고 `EventClip` 도 **0건**이다.
`StreamMonitor` 는 **39대**(안양 규모와 같다). 즉 **「39대 실제 쓰기량」이 없다.**
그래서 지시 D-372 ①의 「실제 쓰기량에서」를 그대로는 못 한다. 대신 그 자리를 둘로 나눈다:

    [실측]  행 하나의 바이트 — **직접 써 보고 표 크기 변화를 잰다.** 그리고 되돌린다
    [미측정] 객체저장(영상) — `minio.invalid` 로 닿지 못한다. 필요한 것을 함께 적는다

  ★ 「0건」을 「쓰기량 0」으로 적지 않는다. 그것은 **아직 안 재진 것**이다.

② 추론 제외 상한 (D-372 ②)
---------------------------
디코딩·네트워크 계단을 끝까지 재려면 RTSP 원본 N개와 AI 서버가 필요하고 이 환경에는
둘 다 없다. 그래서 **추론 자리를 고정 지연 스텁으로 두고** 우리 소프트웨어가 견디는
쪽만 잰다 — 그 이름이 「추론 제외 상한」이다.

    잰다   : 검출 한 건이 이벤트 행이 되기까지 (K1 `record_detection`) · 초당 처리 건수
    스텁   : 추론 지연 `--inference-ms` (기본 0 — **0 은 「추론이 공짜」가 아니라
             「이 수에 추론이 안 들어 있다」는 뜻이다.** 이름이 그것을 말한다)
    미측정 : ffmpeg 디코딩 · RTSP 수신 — 원본이 있어야 잰다

★ 종료 조건 셋 (D-372 · D-365)
------------------------------
    ① 드롭 1% 초과      ② 이벤트 p95 1초 초과      ③ 계약 AC 위반
셋 중 하나라도 걸리면 그 지점이 상한이고, **환경·커밋 해시와 함께** 기록한다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \\
        python /repo/scripts/capacity_measure.py --out /docs/agent/evidence/D-372/capacity.json
    python scripts/capacity_measure.py --self-test        # 호스트에서도 돈다
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 몇 건을 써 보고 재는가. 적으면 표 크기 변화가 페이지 단위에 묻히고,
#: 많으면 되돌리는 데 오래 걸린다.
SIZE_SAMPLE_ROWS = 500

#: 지연을 몇 번 재는가 / 앞의 몇 번을 버리는가 (`perf_measure.py` 와 같은 규약).
LATENCY_SAMPLES = 60
LATENCY_WARMUP = 10

#: 종료 조건 (D-372). **목표가 아니라 멈추는 선**이다.
STOP_DROP_RATE = 0.01          # 드롭 1%
STOP_EVENT_P95_SEC = 1.0       # 이벤트 p95 1초

#: 시나리오 표의 이벤트율(대당 건/시간). **가정이지 실측이 아니다** —
#: 그래서 값 하나가 아니라 **여러 개**를 낸다. 하나만 내면 그것이 답으로 읽힌다.
EVENT_RATE_SCENARIOS = (1, 6, 60, 600)


# ═══════════════════════════════════════════════════════════════════════════
# 환경 — **환경 없는 성능 수치는 착시 ⑤다** (D-365)
# ═══════════════════════════════════════════════════════════════════════════

def commit_hash() -> str:
    """어느 코드에서 잰 수인가. 없으면 「없음」이라고 적는다 — 지어내지 않는다.

    ★ 컨테이너 안에는 `.git` 도 git 도 없다(마운트된 것은 코드뿐이다). 그래서
      호스트가 `GX_COMMIT` 으로 넘긴다 — **넘어오지 않으면 비운다.** 비운 자리는
      「못 적었다」이고, 지어낸 해시보다 낫다 (D-365 · D-284).
    """
    given = os.environ.get("GX_COMMIT", "").strip()
    if given:
        return given
    for args in (["git", "rev-parse", "HEAD"],):
        try:
            out = subprocess.run(args, capture_output=True, text=True, timeout=5,
                                 cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return "없음 (이 자리에서 git 을 읽지 못했다 — 저장소 밖이거나 git 이 없다)"


def environment() -> dict:
    env: dict = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": commit_hash(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "gpu": "없음 — AI 추론은 외부 서버가 한다. 그래서 이 수는 「추론 제외」다",
    }
    for path, key in (("/sys/fs/cgroup/memory.max", "cgroup_memory_max"),
                      ("/sys/fs/cgroup/cpu.max", "cgroup_cpu_max")):
        try:
            with open(path, encoding="utf-8") as fh:
                env[key] = fh.read().strip()
        except OSError:
            env[key] = "읽지 못함"
    return env


# ═══════════════════════════════════════════════════════════════════════════
# 순수 계산 — 파일·DB 없이 시험할 수 있게 (D-277)
# ═══════════════════════════════════════════════════════════════════════════

def bytes_per_camera_per_second(row_bytes: float, events_per_hour: float) -> float:
    """대당 초당 바이트. **곱셈 하나이고, 그 하나가 견적의 전부다.**"""
    return row_bytes * events_per_hour / 3600.0


def scenario_table(row_bytes: float, cameras: int,
                   rates=EVENT_RATE_SCENARIOS) -> list[dict]:
    """이벤트율을 **고르게** 만든다 — 하나만 내면 그것이 답으로 읽힌다."""
    out = []
    for rate in rates:
        per_cam = bytes_per_camera_per_second(row_bytes, rate)
        out.append({
            "가정_대당_이벤트율_시간당": rate,
            "대당_MB_per_s": round(per_cam / 1_048_576, 9),
            "대당_MB_per_day": round(per_cam * 86400 / 1_048_576, 4),
            f"{cameras}대_MB_per_day": round(per_cam * 86400 * cameras / 1_048_576, 3),
            f"{cameras}대_GB_per_year": round(
                per_cam * 86400 * 365 * cameras / 1_073_741_824, 3),
        })
    return out


def stop_conditions(drop_rate: float | None, p95_sec: float | None,
                    contract_violations: list[str]) -> list[str]:
    """종료 조건 셋 (D-372). **못 잰 것은 「통과」가 아니다** (D-301)."""
    hits: list[str] = []
    if drop_rate is None:
        hits.append("[판정 불가] 드롭률을 재지 못했다 — 「0%」가 아니다")
    elif drop_rate > STOP_DROP_RATE:
        hits.append(f"★ 드롭 {drop_rate * 100:.2f}% > {STOP_DROP_RATE * 100:.0f}% — 여기가 상한이다")
    if p95_sec is None:
        hits.append("[판정 불가] 이벤트 p95 를 재지 못했다")
    elif p95_sec > STOP_EVENT_P95_SEC:
        hits.append(f"★ 이벤트 p95 {p95_sec:.3f}초 > {STOP_EVENT_P95_SEC}초 — 여기가 상한이다")
    hits.extend(f"★ 계약 AC 위반: {v}" for v in contract_violations)
    return hits


# ═══════════════════════════════════════════════════════════════════════════
# ① 저장 — **직접 써 보고 표 크기 변화를 잰다. 그리고 되돌린다**
# ═══════════════════════════════════════════════════════════════════════════

def _measure_storage_once() -> dict:
    """이벤트 한 건이 차지하는 바이트 (인덱스 포함).

    ★ 측정 때문에 생긴 행이 남으면 다음 측정의 분모가 달라진다 —
      **측정기가 자기가 재는 세상을 바꾸면 안 된다**(`perf_measure.py` 와 같은 규약).
      그래서 트랜잭션 안에서 하고 `set_rollback(True)` 로 되돌린다.

    ★ `pg_total_relation_size` 는 인덱스와 TOAST 를 포함한다. 데이터만 세면
      **실제 디스크보다 작게** 나오고, 작게 나온 견적은 현장에서 디스크가 찬다.
    """
    from django.apps import apps
    from django.db import connection, transaction
    from django.utils import timezone as djtz

    from common.tenant_scope import TenantScope
    from kernels.k1_event.services import record_detection

    Event = apps.get_model("stream_monitors", "DetectionEvent")
    Stream = apps.get_model("stream_monitors", "StreamMonitor")

    cameras = Stream._base_manager.count()
    existing_events = Event._base_manager.count()
    table = Event._meta.db_table

    def total_size() -> int:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_total_relation_size(%s)", [table])
            return int(cur.fetchone()[0])

    result: dict = {
        "카메라_대수_실측": cameras,
        "기존_이벤트_행수_실측": existing_events,
        "표": table,
    }

    # ★ 카메라를 **새로 만들지 않고 있는 것을 쓴다.**
    #   ① 39대가 이미 있는데 40번째를 만들면 그 행이 측정의 일부가 된다
    #   ② 만들면 이 스크립트가 「테넌트 데이터를 쓰는 도구」가 되고,
    #      분류 등록부(D-270 ③)를 참조해야 하는 자리가 된다 —
    #      **측정기는 재는 세상에 들어가지 않는 것이 옳다**
    stream = Stream._base_manager.order_by("pk").first()
    if stream is None:
        result["상태"] = "판정 불가"
        result["이유"] = ("카메라가 0대다 — 이벤트를 쓸 스트림이 없다. "
                          "「행당 0바이트」가 아니라 **못 잰 것**이다 (D-301)")
        return result

    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute(f'ANALYZE "{table}"')
        before = total_size()

        scope = TenantScope.system(reason="용량 측정 — 파이프라인에는 요청자가 없다")
        types = list(Event.EventType.values)
        base = djtz.now()
        from datetime import timedelta

        for i in range(SIZE_SAMPLE_ROWS):
            record_detection(
                scope=scope, stream_monitor_id=stream.pk,
                event_type=types[i % len(types)], severity="critical",
                occurred_at=base + timedelta(seconds=i * 60),
                snapshot_path=f"snapshots/measure/{i}.jpg",
                confidence=0.87, lat=37.4, lng=126.9,
            )
        with connection.cursor() as cur:
            cur.execute(f'ANALYZE "{table}"')
        after = total_size()
        transaction.set_rollback(True)

    delta = after - before
    row_bytes = delta / SIZE_SAMPLE_ROWS if SIZE_SAMPLE_ROWS else 0
    result.update({
        "쓴_행수": SIZE_SAMPLE_ROWS,
        "표_증가_바이트_실측": delta,
        "행당_바이트_실측": round(row_bytes, 1),
        "주": ("`pg_total_relation_size` — 인덱스·TOAST 포함. 트랜잭션 안에서 재고 "
               "되돌렸다(원본 DB 를 더럽히지 않는다). ★ 표는 페이지(8KB) 단위로 자라므로 "
               "행당 바이트는 표본 수가 적을수록 거칠다 — 그래서 500행을 쓴다"),
    })
    if delta <= 0:
        result["경고"] = ("표 크기가 늘지 않았다 — 페이지 여유에 묻혔거나 ANALYZE 가 "
                          "반영되지 않았다. **이 수를 견적에 쓰지 마라** (D-301)")
    return result


def measure_storage(repeat: int = 3) -> dict:
    """같은 측정을 **여러 번** 하고 흩어진 폭을 함께 낸다 (D-350).

    ★ 왜 한 번으로 안 되나 [실측 2026-09-11]: 두 번 재니 **1081 · 1344 바이트/건**이
      나왔다. 표는 8KB 페이지 단위로 자라고 인덱스도 덩어리로 자라므로, 한 번 잰
      수는 그 덩어리가 어디서 끊겼는지에 흔들린다.
      **한 번 재고 그 수를 견적에 넣으면 25% 를 그냥 틀린다.**
      그래서 폭을 감추지 않고 `최소·중앙·최대`를 다 낸다 — 제안서에는 최대를 쓴다
      (작게 잡은 견적은 현장에서 디스크가 찬다).
    """
    runs = [_measure_storage_once() for _ in range(max(1, repeat))]
    values = sorted(r["행당_바이트_실측"] for r in runs)
    out = dict(runs[-1])
    out.update({
        "반복": len(runs),
        "행당_바이트_최소": values[0],
        "행당_바이트_중앙": values[len(values) // 2],
        "행당_바이트_최대": values[-1],
        "행당_바이트_실측": values[-1],      # 견적에는 **최대**를 쓴다
        "반복_전체": values,
        "흩어짐_주": ("표는 8KB 페이지 · 인덱스는 덩어리로 자란다. 한 번 잰 수는 그 "
                      "덩어리가 어디서 끊겼는지에 흔들리므로 **폭을 함께 적는다**. "
                      "견적에는 최대값을 쓴다 — 작게 잡은 견적은 현장에서 디스크가 찬다"),
    })
    return out


def measure_object_store() -> dict:
    """영상·캡처가 사는 곳. **닿지 못하면 닿지 못했다고 적는다** (D-301)."""
    from django.apps import apps

    out: dict = {
        "상태": "미측정",
        "이유": "",
        "무엇이_있어야_재나": (
            "① 객체저장(MinIO)에 닿는 자격증명과 주소 — 지금은 `minio.invalid` 다 "
            "② 이벤트에 묶인 클립이 실제로 쌓인 기간. `EventClip` 이 0건이면 "
            "「대당 영상 MB/s」의 분자가 없다"),
    }
    try:
        Clip = apps.get_model("stream_monitors", "EventClip")
        out["EventClip_행수_실측"] = Clip._base_manager.count()
    except Exception as exc:                       # noqa: BLE001
        out["EventClip_행수_실측"] = None
        out["이유"] = f"{type(exc).__name__}: {exc}"[:160]
    if out.get("EventClip_행수_실측") == 0:
        out["이유"] = ("클립 행이 0건이다 — **「영상 쓰기량 0」이 아니라 「아직 안 재진 것」**이다. "
                       "0 을 견적에 넣으면 디스크 견적이 통째로 빠진다")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# ② 추론 제외 상한 — 소프트웨어가 견디는 쪽만 잰다
# ═══════════════════════════════════════════════════════════════════════════

def measure_throughput_excluding_inference(inference_ms: float) -> dict:
    """검출 한 건이 이벤트 행이 되기까지. **추론은 스텁이다.**

    ★ 이름이 「추론 제외 상한」인 이유: 이 수에 GPU 추론이 **안 들어 있다.**
      들어 있는 척하면 그것이 착시 ⑤(환경 없는 성능 수치)의 다른 얼굴이다.
    """
    from datetime import timedelta

    from django.apps import apps
    from django.db import transaction
    from django.utils import timezone as djtz

    from common.tenant_scope import TenantScope
    from kernels.k1_event.services import record_detection

    Event = apps.get_model("stream_monitors", "DetectionEvent")
    Stream = apps.get_model("stream_monitors", "StreamMonitor")

    samples: list[float] = []
    attempted = 0
    stored_before = stored_after = 0

    stream = Stream._base_manager.order_by("pk").first()
    if stream is None:
        return {"상태": "판정 불가",
                "이유": "카메라가 0대다 — 잴 대상이 없다. 「0건/초」가 아니다 (D-301)"}

    with transaction.atomic():
        scope = TenantScope.system(reason="용량 측정 — 추론 제외 상한")
        types = list(Event.EventType.values)
        base = djtz.now()
        stored_before = Event._base_manager.count()

        for i in range(LATENCY_SAMPLES):
            if inference_ms:
                time.sleep(inference_ms / 1000.0)   # 추론 자리 — **고정 지연 스텁**
            t0 = time.perf_counter()
            record_detection(
                scope=scope, stream_monitor_id=stream.pk,
                event_type=types[i % len(types)], severity="critical",
                occurred_at=base + timedelta(seconds=i * 60),
                confidence=0.9,
            )
            samples.append(time.perf_counter() - t0)
            attempted += 1
        stored_after = Event._base_manager.count()
        transaction.set_rollback(True)

    warm = samples[LATENCY_WARMUP:] or samples
    warm_sorted = sorted(warm)
    p95 = warm_sorted[max(0, int(len(warm_sorted) * 0.95) - 1)]
    stored = stored_after - stored_before
    # ★ 「투입 n = 저장 n」 — D-367 이 잠근 성질을 여기서도 값으로 낸다.
    drop_rate = 0.0 if attempted == 0 else max(0.0, (attempted - stored) / attempted)

    return {
        "표본": len(warm),
        "warmup_버림": LATENCY_WARMUP,
        "추론_스텁_ms": inference_ms,
        "이벤트_기록_평균_초": round(statistics.fmean(warm), 6),
        "이벤트_기록_p95_초": round(p95, 6),
        "이벤트_기록_최대_초": round(max(warm), 6),
        "추론_제외_상한_건_per_s": round(1.0 / statistics.fmean(warm), 1) if warm else None,
        "투입": attempted,
        "저장": stored,
        "드롭률": drop_rate,
        "주": ("★ **추론 제외**다. GPU 추론·ffmpeg 디코딩·RTSP 수신이 이 수에 없다. "
               "한 프로세스·직렬 기준이고, 워커를 늘리면 늘어난다 — 그 곱은 여기서 하지 않는다"),
        "미측정": ("디코딩 계단(ffmpeg) · 네트워크 수신(RTSP) — 원본 스트림 N개가 있어야 "
                   "잰다. 없이 낸 수를 계단이라고 부르면 그것이 지어낸 수다 (D-280)"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    checks = [
        ("행 500바이트 · 시간당 6건 → 대당 초당 바이트가 맞는가",
         abs(bytes_per_camera_per_second(500, 6) - (500 * 6 / 3600)) < 1e-9),
        ("이벤트율 0 이면 저장량 0",
         bytes_per_camera_per_second(500, 0) == 0),
        ("시나리오 표는 **하나가 아니라 여럿**을 낸다 (하나면 답으로 읽힌다)",
         len(scenario_table(500, 39)) == len(EVENT_RATE_SCENARIOS)),
        ("★ 드롭 2% 면 종료 조건에 걸린다",
         any("드롭" in h and h.startswith("★") for h in stop_conditions(0.02, 0.1, []))),
        ("드롭 0.5% 면 안 걸린다",
         not any(h.startswith("★") and "드롭" in h
                 for h in stop_conditions(0.005, 0.1, []))),
        ("★ p95 1.2초면 걸린다",
         any("p95" in h and h.startswith("★") for h in stop_conditions(0.0, 1.2, []))),
        ("★ 계약 AC 위반은 그대로 종료 조건이다",
         any("계약 AC" in h for h in stop_conditions(0.0, 0.1, ["F-10 30초 초과"]))),
        ("★ 못 잰 것은 통과가 아니다 — 판정 불가로 나온다",
         any("판정 불가" in h for h in stop_conditions(None, None, []))),
        ("커밋 해시 자리는 비어도 **지어내지 않는다**",
         isinstance(commit_hash(), str) and commit_hash() != ""),
    ]
    for name, ok in checks:
        print(f"  {'OK  ' if ok else 'FAIL'}  {name}")
    bad = [n for n, ok in checks if not ok]
    pos = sum(1 for n, _ in checks if n.startswith("★"))
    print(f"[CAPACITY] 자기시험 {len(checks)}건 {'통과' if not bad else '실패'} "
          f"(양성 {pos} · 음성 {len(checks) - pos})")
    return EXIT_OK if not bad else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", metavar="PATH", help="결과 JSON 경로")
    ap.add_argument("--repeat", type=int, default=3,
                    help="저장 측정을 몇 번 반복할 것인가. 한 번 잰 수는 페이지 경계에 "
                         "흔들린다 — 폭을 보려고 여러 번 잰다 (D-350)")
    ap.add_argument("--inference-ms", type=float, default=0.0,
                    help="추론 자리의 고정 지연 스텁(ms). 기본 0 — 0 은 「추론이 공짜」가 "
                         "아니라 「이 수에 추론이 안 들어 있다」는 뜻이다")
    args = ap.parse_args()

    rc = self_test()
    if args.self_test:
        return rc
    if rc != EXIT_OK:
        print("[CAPACITY] 자기시험이 실패했다 — 판정기를 먼저 고친다 (D-350)")
        return rc

    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        import django

        django.setup()
    except Exception as exc:                       # noqa: BLE001
        print(f"[CAPACITY] Django 를 세우지 못했다: {type(exc).__name__}: {exc}")
        print("[CAPACITY] **판정 불가**다. 컨테이너에서 돌린다")
        return EXIT_UNDECIDABLE

    env = environment()
    storage = measure_storage(args.repeat)
    objects = measure_object_store()
    throughput = measure_throughput_excluding_inference(args.inference_ms)

    cameras = storage.get("카메라_대수_실측") or 0
    row_bytes = storage.get("행당_바이트_실측") or 0
    table = scenario_table(row_bytes, cameras) if row_bytes > 0 else []
    stops = stop_conditions(throughput.get("드롭률"),
                            throughput.get("이벤트_기록_p95_초"), [])

    payload = {
        "decision": "D-372",
        "환경": env,
        "①_저장": {
            "DB": storage,
            "객체저장": objects,
            "시나리오": table,
            "읽는_법": ("행당 바이트는 [실측]이고 이벤트율은 [입력·가정]이다. "
                        "곱한 값은 [산출]이지 실측이 아니다 — 제안서에 옮길 때 "
                        "그 태그를 지우지 마라 (D-322)"),
        },
        "②_추론_제외_상한": throughput,
        "종료_조건": {
            "정의": {"드롭": f">{STOP_DROP_RATE * 100:.0f}%",
                     "이벤트_p95": f">{STOP_EVENT_P95_SEC}초",
                     "계약_AC": "위반 시 즉시"},
            "걸린_것": stops,
        },
    }

    print(f"[CAPACITY] 환경 — cpu {env['cpu_count']} · commit {env['commit'][:12]} · GPU {env['gpu'][:2]}")
    print(f"[CAPACITY] ① 저장 — 카메라 **{cameras}대**[실측] · "
          f"이벤트 행 **{row_bytes:.0f}바이트/건**[실측·최대] "
          f"(반복 {storage.get('반복')}회 · 폭 {storage.get('반복_전체')} · "
          f"기존 이벤트 행 {storage['기존_이벤트_행수_실측']}건)")
    for row in table:
        rate = row["가정_대당_이벤트율_시간당"]
        print(f"           [가정] 대당 시간당 {rate:>4}건 → "
              f"대당 {row['대당_MB_per_day']:>8.3f} MB/일 · "
              f"{cameras}대 {row[f'{cameras}대_GB_per_year']:>9.2f} GB/년")
    print(f"[CAPACITY] ① 영상 — **{objects['상태']}**: {objects['이유']}")
    print(f"[CAPACITY] ② 추론 제외 상한 — 평균 {throughput['이벤트_기록_평균_초'] * 1000:.1f}ms · "
          f"p95 {throughput['이벤트_기록_p95_초'] * 1000:.1f}ms · "
          f"**{throughput['추론_제외_상한_건_per_s']}건/초** (1 프로세스 · 추론 제외)")
    print(f"[CAPACITY] ② 투입 {throughput['투입']}건 = 저장 {throughput['저장']}건 · "
          f"드롭 {throughput['드롭률'] * 100:.2f}%")
    if stops:
        print("[CAPACITY] 종료 조건에 걸린 것:")
        for h in stops:
            print(f"    {h}")
    else:
        print("[CAPACITY] 종료 조건 — 걸린 것 없음 (이 표본 크기에서)")

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"[CAPACITY] 증거 → {args.out}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
