#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PERF-06 — **200/분 속도제한이 이벤트를 버리는가 미루는가. 호출로 묻는다** (차선 Q).

정본이 못 박은 대로 **읽기로 판정하지 않는다** (`ga_readiness.yaml` PERF-06:
「그 제한의 출처를 코드에서 찾고, 버리는지 미루는지를 **호출로** 확인한다」).
코드는 이미 「미룬다」고 적혀 있다(D-367). 적혀 있는 것과 도는 것은 다른 사실이다 —
그래서 이 도구는 **상한을 넘기는 호출을 실제로 날리고 DB 행 수를 센다.**

무엇을 재는가 — 넷
------------------
  ① **투입 n = DB 행 n**            상한(200/분)의 **1.5배**를 1분 안에 넣고 행을 센다
  ② **dropped == 0**                `SignalProtection.defer_stats()` 의 소실 칸
  ③ **deferred > 0**                상한을 실제로 넘겼는가 (안 넘겼으면 아무것도 안 잰 것)
  ④ **되돌렸는가**                  잰 자리에 행을 남기지 않는다

⚠ **표본은 서로 다른 스트림으로 세운다** — 이 함정이 이 절의 핵심이다
---------------------------------------------------------------------
`record_detection` 을 **같은 스트림·같은 종류로** 연달아 부르면 K1 의 기록 창
(`DEDUP_WINDOW` 10초)이 두 표본을 **한 행으로 접는다**. 그 상태로 행을 세면
「투입 300 · 행 1」이 나오고, 그것을 「속도제한이 299건을 버렸다」로 읽게 된다.
**중복 억제를 재면서 속도제한을 쟀다고 적는 것** — 그것이 이 도구가 스트림을
n개 세우는 이유다. 접힘이 0건임을 함께 세어 그 사실을 증거에 박는다.

★ 쓰기 전에 **분류 등록부에 묻는다** (D-270 ③)
------------------------------------------------
이 도구는 재기 위해 **스트림 300대를 진짜로 심는다.** 그 표가 공용 마스터라면 그 행은
되돌리기 전까지 **전 테넌트 화면에 뜬다** — 측정이 남의 관제에 얼룩을 남긴다. 그래서
첫 `create()` 앞에서 `_registry_guard()` 를 부르고, 공용 마스터면 **심지 않고 멈춘다.**
판정식은 복사하지 않는다 — `verify_alarm_budget` 의 문지기를 그대로 빌려 온다(D-212).

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/probe_event_rate_limit.py --out /docs/agent/evidence/PERF-06/calls.json
    python scripts/probe_event_rate_limit.py --self-test     # 판정 규칙만 (Django 없이)

종료 코드: 0 쟀고 소실 0 · 1 쟀고 소실 있음 · 2 **못 쟀다**(환경 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: ★ **이 도구가 실제로 행을 심는 표.** 심기 전에 `_refuse_if_shared_master` 에 이대로
#:   넘긴다 (D-270 ③). 두 표를 고르는 데 추측이 없다 — 코드가 만드는 자리를 그대로 셌다:
#:
#:     stream_monitors.StreamMonitor   `collect()` 이 직접 만든다(`Stream._base_manager.create`)
#:                                     그리고 `_own()` 의 `row.save(update_fields=["group"])`
#:                                     가 저장하는 것도 **이 표다** — `_own` 은 `cam` 으로만
#:                                     불리고 `cam` 은 StreamMonitor 이기 때문이다
#:     stream_monitors.DetectionEvent  `record_detection` 이 만든다. **내 파일에 create 가
#:                                     안 보인다고 안 심는 것이 아니다** — 이 도구가 부른
#:                                     결과로 300행이 생긴다. 부작용까지 세지 않으면
#:                                     검사는 내 코드만 보고 세상을 못 본다
#:
#: ★ 왜 이것이 형식이 아닌가: 이 도구는 **스트림 300대를 진짜로 심는다.** 그 표가 공용
#:   마스터였다면 측정하는 5초 동안 **모든 테넌트의 관제 화면에 유령 카메라 300대**가
#:   떴을 것이다. 되돌리기 전까지는 남의 관제에 얼룩이 남는다.
PLANTED_TABLES = ("stream_monitors.StreamMonitor", "stream_monitors.DetectionEvent")

#: 분류의 **유일한 출처**. 판정식을 여기 복사하지 않는다 (D-212) — 아래
#: `_refuse_if_shared_master` 가 이 파일을 실제로 읽어 판정한다.
CLASSIFICATION_REGISTRY = "backend/tests/tenant_classification.py"

#: 상한의 몇 배를 넣는가. 1.0 이면 **넘지 않으므로 아무것도 안 잰다** — 1.5 는
#: 넘기되 한 번의 시험이 몇 분씩 걸리지 않는 자리다.
SURGE_FACTOR = 1.5


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수 (D-277). 자기시험이 합성 수치를 먹인다
# ═══════════════════════════════════════════════════════════════════════════
def judge(counts: dict) -> list:
    """`(이름, 통과, 사유)`. ★ `None` 은 **못 쟀다**이지 거짓이 아니다 (D-301)."""
    out: list = []

    sent, rows = counts.get("calls_sent"), counts.get("rows_created")
    if sent is None or rows is None:
        out.append(("투입 n = DB 행 n", False, "**못 쟀다** — 호출을 못 날렸다"))
    else:
        out.append(("투입 n = DB 행 n", sent == rows,
                    f"투입 {sent}건 · 행 {rows}건" + ("" if sent == rows else
                     f" — **{sent - rows}건이 DB 에 없다.** 재난이 몰릴 때 이벤트가 "
                     f"사라진다는 뜻이고, 그 순간이 정확히 시스템이 필요한 순간이다")))

    folded = counts.get("folded")
    if folded is None:
        out.append(("접힌 표본 0건 (중복 억제를 재고 있지 않다)", False, "**못 쟀다**"))
    else:
        out.append(("접힌 표본 0건 (중복 억제를 재고 있지 않다)", folded == 0,
                    "접힘 0건 — 서로 다른 스트림이다" if folded == 0 else
                    f"{folded}건이 접혔다 — 표본이 같은 스트림을 쓰고 있다. 이 수로 "
                    f"속도제한을 말하면 **중복 억제를 재고 속도제한이라 적는 것**이다"))

    dropped = counts.get("dropped")
    if dropped is None:
        out.append(("소실 0건 (dropped)", False, "**못 쟀다** — 통계를 못 읽었다"))
    else:
        detail = counts.get("drop_detail") or {}
        out.append(("소실 0건 (dropped)", dropped == 0,
                    "dropped 0" if dropped == 0 else
                    f"dropped {dropped} · {detail} — 미루는 갈래가 아니라 **버리는 갈래**다"))

    deferred = counts.get("deferred")
    inline = counts.get("ran_inline") or 0
    if deferred is None:
        out.append(("상한을 실제로 넘겼다", False, "**못 쟀다**"))
    else:
        crossed = (deferred + (counts.get("coalesced") or 0) + inline) > 0
        out.append(("상한을 실제로 넘겼다", crossed,
                    f"deferred {deferred} · coalesced {counts.get('coalesced')} · "
                    f"ran_inline {inline}" + ("" if crossed else
                     " — **상한을 안 넘겼다.** 넘지 않은 시험은 초록이 아니라 "
                     "아무것도 안 잰 것이다 (D-289)")))

    left = counts.get("leftover_rows")
    if left is None:
        out.append(("되돌렸다", False, "**못 쟀다**"))
    else:
        out.append(("되돌렸다", left == 0,
                    "남은 행 0건" if left == 0 else
                    f"{left}행이 남았다 — 재는 행위가 재는 대상을 바꾼다"))
    return out


def self_test() -> int:
    """판정 규칙을 스스로 시험한다. **Django 없이 돈다** (D-277 · D-350)."""
    bad: list = []

    def names(rows):
        return {n: ok for (n, ok, _why) in rows}

    green = dict(calls_sent=300, rows_created=300, folded=0, dropped=0,
                 drop_detail={}, deferred=100, coalesced=0, ran_inline=0,
                 leftover_rows=0)
    got = names(judge(green))
    if not all(got.values()):
        bad.append(f"다 선 표본을 통과로 읽지 못한다: {got}")

    # ── 출생 표본 (D-310) — 이 도구를 만들게 한 로그 한 줄 ────────────────
    #   "Rate limit exceeded for detectionevent (200/min) - skipping"
    #   그 `skipping` 이 **버리는 것**이었다면 아래가 그때의 수다.
    birth = dict(green, rows_created=200, dropped=100,
                 drop_detail={"detectionevent": 100})
    b = names(judge(birth))
    if b.get("투입 n = DB 행 n") or b.get("소실 0건 (dropped)"):
        bad.append("**출생 표본**(투입 300 · 행 200 · dropped 100)을 통과로 읽는다 — "
                   "버리는 갈래를 못 잡는 판정기는 초록을 내도 아무것도 재지 않은 것이다")

    # ── 함정 표본 — 같은 스트림으로 재서 중복 억제가 접은 수 ──────────────
    trap = dict(green, rows_created=1, folded=299)
    t = names(judge(trap))
    if t.get("접힌 표본 0건 (중복 억제를 재고 있지 않다)"):
        bad.append("같은 스트림으로 재 **299건이 접힌** 표본을 통과로 읽는다 — "
                   "그 수는 속도제한이 아니라 중복 억제의 수다")

    for key, value, expect in (
        ("dropped", 3, "소실 0건 (dropped)"),
        ("leftover_rows", 7, "되돌렸다"),
        ("deferred", 0, "상한을 실제로 넘겼다"),
    ):
        sample = dict(green, **{key: value})
        if key == "deferred":
            sample["coalesced"] = 0
            sample["ran_inline"] = 0
        if names(judge(sample)).get(expect):
            bad.append(f"{key}={value!r} 인데 「{expect}」를 통과로 읽는다")

    rows = judge(dict(green, rows_created=None))
    hit = [r for r in rows if r[0] == "투입 n = DB 행 n"][0]
    if hit[1] or "못 쟀다" not in hit[2]:
        bad.append("호출을 **못 날렸는데** 통과로 읽거나 사유에 그 사실이 없다 (D-301)")

    if bad:
        print("[PERF-06] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[PERF-06] 자기시험 통과 — 초록 1 · 출생 표본 1 · 함정 1 · 음성 3 · 판정 불가 1")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — **되돌리는 트랜잭션 안에서** 상한을 넘긴다
# ═══════════════════════════════════════════════════════════════════════════
class _Rollback(Exception):
    """되돌리기 위해 일부러 던지는 예외."""


def collect(surge_factor: float = SURGE_FACTOR) -> dict:
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.apps import apps
    from django.db import transaction
    from django.utils import timezone

    from common.cache_signal_protection import SignalProtection
    from common.tenant_scope import TenantScope
    from common.universal_optimization import CACHE_INVALIDATION_RATE_LIMIT
    from kernels.k1_event.services import DEDUP_WINDOW, record_detection

    Event = apps.get_model("stream_monitors", "DetectionEvent")
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    UserGroup = apps.get_model("user", "UserGroup")

    limit = int(CACHE_INVALIDATION_RATE_LIMIT)
    n = int(limit * surge_factor)
    out: dict = {
        "limit_per_minute": limit,
        "surge_factor": surge_factor,
        "calls_sent": None, "rows_created": None, "folded": None,
        "dropped": None, "deferred": None, "coalesced": None,
        "ran_inline": None, "drained": None, "failed": None,
        "drop_detail": None, "leftover_rows": None,
        "elapsed_s": None, "events_per_sec": None,
        "dedup_window_s": DEDUP_WINDOW.total_seconds(),
        "distinct_streams": n,
        "cameras_in_db": Stream._base_manager.count(),
    }

    group = UserGroup.objects.order_by("pk").first()
    if group is None:
        print("[PERF-06] 테넌트(UserGroup)가 하나도 없다 — **판정 불가** (D-301)")
        return out
    out["group_used"] = f"{group.pk}:{group.name}"

    scope = TenantScope.system(
        reason="PERF-06 — 속도제한이 버리는지 미루는지 호출로 확인한다. 되돌린다")
    marker = f"gx-perf06-{int(time.time())}"
    SignalProtection.reset_defer_state()

    # ★ **쓰기 전에 등록부에 묻는다** (D-270 ③). 판정기는 만들지 않고
    #   `verify_alarm_budget` 이 이미 지은 것을 그대로 쓴다 — 두 벌은 반드시
    #   어긋나고(D-369), 그 함수는 컨테이너의 `/repo`·`/app` 이중 마운트 함정과
    #   「못 읽으면 통과시키지 않는다」(D-301)까지 이미 담고 있다.
    #   ⚠ 이 줄은 `transaction.atomic()` **밖**이자 첫 `create()` **앞**이다 —
    #     심고 나서 묻는 것은 묻지 않은 것과 같다.
    _registry_guard()(PLANTED_TABLES)
    out["classification_registry"] = CLASSIFICATION_REGISTRY
    out["planted_tables"] = list(PLANTED_TABLES)

    now = timezone.now()
    folded = 0
    try:
        with transaction.atomic():
            streams = [
                Stream._base_manager.create(
                    name=f"{marker}-{i}", code=f"{marker}-{i}",
                    ip_source="rtsp://probe.invalid/x", is_active=True)
                for i in range(n)
            ]
            for cam in streams:
                _own(cam, group)

            before = Event._base_manager.count()
            started = time.perf_counter()
            for i, cam in enumerate(streams):
                # ★ 스트림이 **매번 다르다.** 같은 스트림이면 10초 창이 접는다.
                res = record_detection(
                    scope=scope, stream_monitor_id=cam.pk,
                    event_type="fire", severity="critical",
                    occurred_at=now + timedelta(milliseconds=i),
                    snapshot_path="")
                if res.folded_into_existing:
                    folded += 1
            elapsed = time.perf_counter() - started
            after = Event._base_manager.count()

            stats = SignalProtection.defer_stats()
            out.update({
                "calls_sent": n,
                "rows_created": after - before,
                "folded": folded,
                "elapsed_s": round(elapsed, 3),
                "events_per_sec": round(n / elapsed, 1) if elapsed else None,
                "dropped": stats["dropped"],
                "deferred": stats["deferred"],
                "coalesced": stats["coalesced"],
                "ran_inline": stats["ran_inline"],
                "drained": stats["drained"],
                "failed": stats["failed"],
                "drop_detail": stats["drop_detail"],
                "queue_len": stats["queue_len"],
            })
            print(f"[PERF-06]   투입 {n}건 · 행 {out['rows_created']}건 · 접힘 {folded}건 · "
                  f"{elapsed:.2f}초 ({out['events_per_sec']}건/초)")
            print(f"[PERF-06]   미룸 통계 {stats}")
            raise _Rollback
    except _Rollback:
        pass

    out["leftover_rows"] = Stream._base_manager.filter(code__startswith=marker).count()
    SignalProtection.reset_defer_state()
    return out


def _registry_guard():
    """공용 마스터 문지기를 **빌려 온다.** 짓지 않는다 (D-212 · D-369).

    `scripts/verify_alarm_budget.py::_refuse_if_shared_master` 가 이 저장소에서
    이미 옳게 지어진 그것이다. 그 함수가 `backend/tests/tenant_classification.py`
    (= `CLASSIFICATION_REGISTRY`)를 **실제로 읽어** `SHARED_MASTERS` 에 든 표인지
    판정하고, 못 읽으면 통과시키지 않는다 — 「검사 못함」과 「대상 아님」은 다른
    사실이기 때문이다(D-301).

    돌려주는 것: 표 이름들을 받아 **공용 마스터면 멈추는** 함수 하나.
    """
    from verify_alarm_budget import _refuse_if_shared_master   # noqa: PLC0415

    def refuse(labels) -> None:
        _refuse_if_shared_master(
            labels,
            lambda why: (_ for _ in ()).throw(SystemExit("[분류] " + why)))
        print(f"[PERF-06] [분류] 심는 표 {len(tuple(labels))}종이 공용 마스터가 "
              f"아님을 등록부에서 확인했다 — {CLASSIFICATION_REGISTRY}")

    return refuse


def _own(row, group):
    """소유를 붙인다. 커널의 판단기를 그대로 쓴다 (D-212)."""
    from kernels.k1_event.services import _owner_field

    if _owner_field(type(row)) == "groups":
        row.groups.set([group])
    else:
        row.group = group
        row.save(update_fields=["group"])


def main() -> int:
    ap = argparse.ArgumentParser(
        description="PERF-06 — 속도제한이 버리는가 미루는가. 호출로 확인한다")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--surge", type=float, default=SURGE_FACTOR)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    try:
        counts = collect(args.surge)
    except Exception as exc:                             # noqa: BLE001
        print(f"[PERF-06] **판정 불가** — 환경을 세우지 못했다: {type(exc).__name__}: {exc}")
        return EXIT_UNDECIDABLE

    if counts.get("calls_sent") is None:
        print("[PERF-06] **판정 불가** — 호출을 못 날렸다 (D-301)")
        return EXIT_UNDECIDABLE

    rc = EXIT_OK
    for (name, ok, why) in judge(counts):
        print(f"[PERF-06] {'  ' if ok else 'X '}{name:38} {why}")
        if not ok:
            rc = EXIT_FAIL

    if args.out:
        payload = dict(counts)
        payload["measured_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload["verdict"] = "미룬다 (소실 0)" if rc == EXIT_OK else "소실이 있다"
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[PERF-06] 기록 → {out}")

    print("[PERF-06] " + ("통과 — 상한을 넘겼고 **행이 하나도 안 사라졌다**. "
                          "`skipping` 은 버리는 것이 아니라 미루는 것이다"
                          if rc == EXIT_OK else
                          "실패 — 위의 X 가 소실이 일어난 자리다"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
