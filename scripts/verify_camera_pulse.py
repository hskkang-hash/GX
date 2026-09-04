#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-15 — **구역 3중 2는 1건, 1대는 0건** (2026-09-04 · 차선 Q).

    "강제 도구: `verify_camera_pulse.py` — 시드에서 구역 A 카메라 3대 중 2대의 프레임을
     멈추면 5분 안에 `camera_cluster_down` 1건 · **1대만 멈추면 0건**(부작위) ·
     캐시를 지나지 않음(P-19)."   — 지시서 §2 Q행 · PRD v2.5 E2

무엇을 재는가 — **네 수**
-------------------------
    ① 3대 중 **2대**를 5분 안에 함께 멈춘다 → `camera_cluster_down` **1건**
    ② 3대 중 **1대**만 멈춘다               → **0건**  ← 초록의 절반은 이쪽이다
    ③ 2대가 죽어 있지만 **함께 죽지 않았다** → 0건
    ④ 캐시를 지나지 않는가 (P-19)

★ 왜 ②가 초록의 절반인가 (지시서 §3-3 부작위)
---------------------------------------------
이 규칙의 값은 무엇을 만드는가가 아니라 **무엇을 안 만드는가**에 있다. 한 대가 끊길
때마다 재난 징후를 내면 관제 화면은 카메라 고장 목록이 되고, 진짜 군집 두절은 그
목록 속에 묻힌다. ①만 재는 판정기는 그 상태를 초록으로 통과시킨다.

★ **아무것도 남기지 않는다** — 트랜잭션을 열고 되돌린다
------------------------------------------------------
①을 진짜로 재려면 맥박을 멈추고 이벤트를 만들어 봐야 한다. 그런데 이 도구는 개발·검수
DB 에서 돌고, 남긴 이벤트는 다음 사람의 화면에 **진짜 군집 두절**로 보인다. 그래서
`transaction.atomic` 안에서 재고 **반드시 되돌린다**. 판정기가 자기가 만든 사실을
재는 것도 막는다 — 되돌리지 못하면 그 자리에서 **회색(exit 2)** 이지 초록이 아니다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/verify_camera_pulse.py
    python scripts/verify_camera_pulse.py --self-test    # 판정 규칙만 (Django 없이)

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(환경 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 규칙의 수. **읽어 온다** — 아래 `_rules()` 가 서비스 모듈에서 가져오고, 못 가져오면
#: 이 값을 마지막 그물로 쓴다. 여기서 복사한 것이 어긋나면 판정기는 아무것도 없는 곳을
#: 세고 「0건」이라 말한다 (verify_seed_p20 의 `FALLBACK_SEED_CODE` 와 같은 자리).
FALLBACK = {
    "min_cameras": 3,
    "min_down": 2,
    "timeout_minutes": 5,
    "window_minutes": 5,
    "event_type": "camera_cluster_down",
}

#: P-19 — 「상태·가용성을 말하는 응답은 캐시를 지나지 않는다」. 군집 두절은 이 화면에
#: 실리므로 이 접두가 우회 목록에 있어야 한다. `scripts/verify_cache_frame.py` 가
#: 같은 목록을 다른 각도에서 본다 — **판정의 중복이 아니라 두 각도**다.
CACHE_BYPASS_PREFIX = "dsm/"


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **함수로 떼어 둔 이유는 시험하기 위해서다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(counts: dict) -> list:
    """네 수를 판정한다. `(이름, 통과, 사유)` 넷.

    ★ `None` 은 **못 쟀다**이지 0 이 아니다 (D-301). 못 잰 칸은 통과가 아니고,
      그 사실이 사유에 남는다.
    """
    out: list = []

    n = counts.get("two_down_events")
    if n is None:
        out.append(("3중 2 두절 → 1건", False, "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("3중 2 두절 → 1건", n == 1,
                    f"{n}건" + ("" if n == 1 else
                                " — 구역이 통째로 끊겨도 관제 화면에 아무 줄도 안 뜬다"
                                if n == 0 else
                                " — 한 사건이 여러 줄이 됐다. 억제가 안 걸린다")))

    n = counts.get("one_down_events")
    if n is None:
        out.append(("1대 두절 → 0건 (부작위)", False, "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("1대 두절 → 0건 (부작위)", n == 0,
                    f"{n}건" + ("" if n == 0 else
                                " — **초록의 절반이 무너졌다.** 카메라 한 대 고장마다 "
                                "재난 징후가 나가면 관제 화면은 고장 목록이 되고, "
                                "진짜 군집 두절은 그 속에 묻힌다")))

    n = counts.get("scattered_down_events")
    if n is None:
        out.append(("따로 죽은 2대 → 0건", False, "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("따로 죽은 2대 → 0건", n == 0,
                    f"{n}건" + ("" if n == 0 else
                                " — 한 달 전에 죽은 카메라 옆에서 오늘 한 대가 끊긴 "
                                "것을 재난 징후라고 말한다")))

    bypass = counts.get("cache_bypass")
    if bypass is None:
        out.append(("캐시를 지나지 않는다 (P-19)", False,
                    "**못 쟀다** — 우회 목록을 못 읽었다 (0건과 구별한다 · D-301)"))
    else:
        out.append(("캐시를 지나지 않는다 (P-19)", bool(bypass),
                    (f"`{CACHE_BYPASS_PREFIX}` 가 BYPASS_PATTERNS 에 있고, 판정 경로는 "
                     f"ORM 직결이다" if bypass else
                     f"`{CACHE_BYPASS_PREFIX}` 가 우회 목록에 없다 — 적중한 본문은 "
                     f"언제나 200 이고, 두절이 그 200 뒤에 숨는다 (D-412)")))
    return out


def self_test() -> int:
    """판정 규칙을 스스로 시험한다. **Django 없이 돈다** (D-277 · D-350).

    ★ **출생 표본** (D-310) — 이 판정기를 만들게 한 사례는 합성이 아니다.
      [실측 등재 2026-09-24 · onboarding_48 U1#3] `cameras_silent_24h` 는 「조용함」과
      「죽음」을 못 가른다고 그 문서가 적었다. 그 상태의 수가 아래 `birth` 다:
      군집 규칙이 **없던 날**의 수 — 2대가 함께 끊겨도 0건이고, 1대만 끊겨도 0건이다.
      두 수가 **같다**는 것이 이 절이 존재하는 이유이고, 아래 첫 갈래가 그 표본이다.
    """
    bad: list = []

    def names(rows):
        return {n: ok for (n, ok, _why) in rows}

    # ── 출생 표본 — **규칙이 없던 날.** 두 수가 같아서 아무것도 안 보였다 ──
    birth = dict(two_down_events=0, one_down_events=0, scattered_down_events=0,
                 cache_bypass=True)
    got = names(judge(birth))
    if got.get("3중 2 두절 → 1건"):
        bad.append("**출생 표본**(군집 규칙이 없던 날: 2대가 함께 끊겨도 0건)을 "
                   "통과로 읽는다 — 이 판정기가 태어난 이유를 못 본다 (D-310)")
    if not got.get("1대 두절 → 0건 (부작위)"):
        bad.append("출생 표본에서 부작위 갈래까지 빨갛게 읽는다 — 그날 1대 0건은 "
                   "사실이었다. 판정기가 사실을 틀렸다고 말하면 안 된다")

    # ── 초록 표본 — 규칙이 선 뒤 ──────────────────────────────────────────
    green = dict(two_down_events=1, one_down_events=0, scattered_down_events=0,
                 cache_bypass=True)
    got = names(judge(green))
    if not all(got.values()):
        bad.append(f"다 선 표본을 통과로 읽지 못한다: {got}")

    # ── 음성 갈래 — 하나씩 무너뜨린다 ────────────────────────────────────
    for key, value, expect_red in (
        ("two_down_events", 0, "3중 2 두절 → 1건"),
        ("two_down_events", 3, "3중 2 두절 → 1건"),      # 많아도 틀린 수다
        ("one_down_events", 1, "1대 두절 → 0건 (부작위)"),
        ("scattered_down_events", 1, "따로 죽은 2대 → 0건"),
        ("cache_bypass", False, "캐시를 지나지 않는다 (P-19)"),
    ):
        sample = dict(green, **{key: value})
        if names(judge(sample)).get(expect_red):
            bad.append(f"{key}={value} 인데 「{expect_red}」를 통과로 읽는다")

    # ── 못 쟀다 ≠ 0 ─────────────────────────────────────────────────────
    rows = judge(dict(green, one_down_events=None))
    hit = [(n, ok, why) for (n, ok, why) in rows if n.startswith("1대")][0]
    if hit[1] or "못 쟀다" not in hit[2]:
        bad.append("부작위를 **못 쟀는데** 통과로 읽거나 사유에 그 사실이 없다 (D-301)")

    if bad:
        print("[OPS15] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[OPS15] 자기시험 통과 — 출생 표본 1 · 초록 표본 1 · 음성 5 · 판정 불가 1")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — **트랜잭션을 열고 되돌린다.** 아무것도 남기지 않는다
# ═══════════════════════════════════════════════════════════════════════════
def _rules() -> dict:
    """규칙의 수를 **서비스 모듈에서 읽어 온다.** 못 읽으면 마지막 그물."""
    try:
        from stream_monitors.services import camera_pulse as cp

        return {
            "min_cameras": cp.CLUSTER_MIN_CAMERAS,
            "min_down": cp.CLUSTER_MIN_DOWN,
            "timeout_minutes": cp.PULSE_TIMEOUT.total_seconds() / 60,
            "window_minutes": cp.CLUSTER_WINDOW.total_seconds() / 60,
            "event_type": cp.CLUSTER_EVENT_TYPE,
        }
    except Exception as exc:                             # noqa: BLE001
        print(f"[OPS15] ⚠ 서비스에서 규칙의 수를 못 읽었다: {type(exc).__name__}: {exc} — "
              f"마지막 그물로 상수를 쓴다(값이 갈리면 엉뚱한 것을 잰다)")
        return dict(FALLBACK)


def _cache_bypass_ok() -> bool | None:
    """P-19 — 「상태·가용성」 접두가 캐시 우회 목록에 있는가. 못 읽으면 `None`."""
    try:
        from common.universal_optimization import UniversalOptimizer

        patterns = list(getattr(UniversalOptimizer, "BYPASS_PATTERNS", []) or [])
    except Exception:                                    # noqa: BLE001
        return None
    if not patterns:
        return None
    return any(CACHE_BYPASS_PREFIX in str(p) for p in patterns)


class _Rollback(Exception):
    """되돌리기 위해 일부러 던지는 예외. **성공 경로에서 던진다** — 실패가 아니다."""


def collect(*, synthesize: bool = True) -> dict:
    """세 갈래를 **한 트랜잭션 안에서** 재고 통째로 되돌린다.

    ★ 시드에 3대짜리 구역이 있으면 **그것을 쓴다**(현장의 사실을 잰다).
      없으면 이 도구가 **합성 구역을 세워** 재고 같은 트랜잭션에서 지운다 —
      「잴 것이 없어서 회색」으로 끝나면 이 절의 부작위가 영원히 안 재진다.
      어느 쪽을 썼는지는 `[입력]` 줄에 그대로 적힌다: 합성으로 잰 초록을
      시드의 초록처럼 보고하지 않는다.
    """
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.apps import apps
    from django.core.cache import cache
    from django.db import transaction
    from django.utils import timezone

    from common.tenant_scope import TenantScope
    from stream_monitors.services.camera_pulse import scan_clusters

    # 캐시 처리: **비움** — 이 판정기는 HTTP 를 지나지 않지만, ORM 층에도 무효화
    # 신호가 없는 캐시가 있다. 비우고 시작해야 「지금」을 잰다 (P-19 · tests/no_cache.py).
    try:
        cache.clear()
        cache_note = "비움"
    except Exception as exc:                             # noqa: BLE001
        cache_note = f"못 비웠다({type(exc).__name__})"

    rules = _rules()
    out = {
        "rules": rules,
        "cache_note": cache_note,
        "cache_bypass": _cache_bypass_ok(),
        "zones_total": None, "zone_used": None, "zone_origin": None,
        "cameras_in_zone": None,
        "two_down_events": None, "one_down_events": None,
        "scattered_down_events": None,
        "rolled_back": False,
    }

    Zone = apps.get_model("stream_monitors", "Zone")
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    Event = apps.get_model("stream_monitors", "DetectionEvent")

    zones = Zone._base_manager.filter(kind="camera_group", is_active=True)
    out["zones_total"] = zones.count()

    scope = TenantScope.system(
        reason="OPS-15 판정기 — 맥박 검사에는 요청자가 없다. 되돌리는 트랜잭션이다")
    now = timezone.now()
    dead = now - timedelta(minutes=rules["timeout_minutes"] + 1)
    old = now - timedelta(days=30)
    marker = f"gx-ops15-probe-{int(now.timestamp())}"

    def _measure(pulses: dict, label: str) -> int:
        """맥박을 그렇게 두고 훑는다. **저장점까지 되돌린다.**"""
        made = {"n": 0}
        try:
            with transaction.atomic():
                for pk, when in pulses.items():
                    Stream._base_manager.filter(pk=pk).update(last_frame_at=when)
                before = Event._base_manager.filter(
                    event_type=rules["event_type"]).count()
                scan_clusters(scope=scope, now=now)
                made["n"] = Event._base_manager.filter(
                    event_type=rules["event_type"]).count() - before
                raise _Rollback
        except _Rollback:
            pass
        print(f"[OPS15]   {label}: 이벤트 {made['n']}건 (되돌렸다)")
        return made["n"]

    try:
        with transaction.atomic():
            pick, cam_ids = None, []
            for zone in zones:
                cams = list(Stream._base_manager.filter(zones=zone, is_active=True)
                            .values_list("pk", flat=True))
                if len(cams) >= rules["min_cameras"]:
                    pick, cam_ids = zone, cams
                    out["zone_origin"] = "시드/현장"
                    break

            if pick is None and synthesize:
                print(f"[OPS15] 카메라 {rules['min_cameras']}대 이상인 활성 구역이 "
                      f"현장에 없다 — **합성 구역을 세워** 잰다(같은 트랜잭션에서 지운다)")
                cams = [
                    Stream._base_manager.create(
                        name=f"{marker}-{i}", code=f"{marker}-{i}",
                        ip_source="rtsp://probe.invalid/x", is_active=True)
                    for i in range(rules["min_cameras"])
                ]
                pick = Zone._base_manager.create(
                    name=marker, kind="camera_group", is_active=True)
                pick.cameras.set(cams)
                cam_ids = [c.pk for c in cams]
                out["zone_origin"] = "합성(되돌림)"

            if pick is None:
                print(f"[OPS15] 카메라 {rules['min_cameras']}대 이상인 활성 구역이 "
                      f"**없다** — **판정 불가**이지 0건이 아니다 (D-301)")
                raise _Rollback

            out["zone_used"] = f"{pick.pk}:{pick.name}"
            out["cameras_in_zone"] = len(cam_ids)
            alive = {pk: now for pk in cam_ids}

            # ① 3중 2 — 함께 멈춘다
            two = dict(alive)
            two[cam_ids[0]] = dead
            two[cam_ids[1]] = dead - timedelta(minutes=1)
            out["two_down_events"] = _measure(two, f"{rules['min_down']}대 동시 두절")

            # ② 1대만 — **0건이어야 한다**
            one = dict(alive)
            one[cam_ids[0]] = dead
            out["one_down_events"] = _measure(one, "1대만 두절(부작위)")

            # ③ 2대가 죽어 있으나 **따로** 죽었다
            scattered = dict(alive)
            scattered[cam_ids[0]] = old
            scattered[cam_ids[1]] = dead
            out["scattered_down_events"] = _measure(scattered, "따로 죽은 2대")

            raise _Rollback
    except _Rollback:
        pass

    # 되돌아갔는지 **확인한다.** 되돌리지 못한 판정기는 회색이지 초록이 아니다.
    leftover = Event._base_manager.filter(
        event_type=rules["event_type"], occurred_at__gte=now - timedelta(minutes=1)
    ).count()
    ghosts = Stream._base_manager.filter(code__startswith=marker).count()
    out["rolled_back"] = (leftover == 0 and ghosts == 0)
    if not out["rolled_back"]:
        print(f"[OPS15] ⚠ 되돌리지 못했다 — 이벤트 {leftover}건 · 합성 카메라 {ghosts}대가 "
              f"남아 있다. 이 판정기가 만든 사실이 다음 사람의 화면에 뜬다")
    return out



def _refuse_if_shared_master(labels, fail):
    """★ 쓰기 전에 **공용 마스터인지 묻는다** (D-270 ③).

    이 도구는 재기 위해 행을 심고 되돌린다. 심는 표가 **공용 마스터**라면 그 행은
    되돌리기 전까지 **전 테넌트 화면에 뜬다** — 측정이 남의 관제에 얼룩을 남긴다.
    등록부(`tests/tenant_classification.py`)가 그 분류의 **유일한 출처**다 —
    판정식을 복사하지 않는다(D-212).

    ⚠ 못 읽으면 **통과시키지 않는다**: 「검사 못함」과 「대상 아님」은 다른 사실이다(D-301).
    """
    #: ★ 이름으로 못 찾으면 **파일로 찾는다.** 컨테이너는 `/repo` 와 `/app`(=backend)이
    #:   **따로** 마운트돼 `tests` 가 이름 공간에 없다 — 저장소가 이미 아는 함정이다
    #:   (`capture_screens._screens_dir` 이 같은 이유로 자리를 하나로 안 박는다).
    #:   그래도 **못 찾으면 통과시키지 않는다**: 「검사 못함」≠「대상 아님」(D-301).
    SHARED_MASTERS = None
    try:
        from tests.tenant_classification import SHARED_MASTERS
    except ImportError:
        import importlib.util

        here = Path(__file__).resolve().parent.parent
        for cand in (here / "backend" / "tests" / "tenant_classification.py",
                     Path("/app") / "tests" / "tenant_classification.py"):
            if not cand.is_file():
                continue
            spec = importlib.util.spec_from_file_location("_tenant_classification", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            SHARED_MASTERS = mod.SHARED_MASTERS
            break
    if SHARED_MASTERS is None:
        fail("분류 등록부(tests/tenant_classification.py)를 이름으로도 파일로도 읽지 "
             "못했다 — 공용 마스터인지 확인하지 못한 채로 쓰지 않는다 (D-270 ③ · D-301)")
        return
    for label in labels:
        if label in SHARED_MASTERS:
            fail(f"{label} 이 분류 등록부에서 **공용 마스터**다. 측정용 행을 공용 표에 "
                 f"심으면 되돌리기 전까지 전 테넌트가 그것을 본다")

def main() -> int:
    ap = argparse.ArgumentParser(
        description="OPS-15 카메라 맥박 군집 두절 — 3중 2는 1건, 1대는 0건")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="수를 JSON 으로도 낸다")
    ap.add_argument("--no-synthesize", action="store_true",
                    help="현장에 3대짜리 구역이 없으면 합성하지 않고 **회색**으로 끝낸다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    # ★ 여기서부터 **쓴다.** 쓰기 전에 분류 등록부에 묻는다 (D-270 ③) —
    #   못 읽으면 멈춘다. 자기시험은 아무것도 안 쓰므로 그 앞에 두지 않는다:
    #   등록부를 못 읽는 호스트에서도 판정 규칙 시험은 돌아야 한다.
    _refuse_if_shared_master(
        ("stream_monitors.StreamMonitor", "stream_monitors.Zone",
         "stream_monitors.DetectionEvent"),
        lambda why: (_ for _ in ()).throw(SystemExit("[분류] " + why)))


    try:
        counts = collect(synthesize=not args.no_synthesize)
    except Exception as exc:                             # noqa: BLE001
        print(f"[OPS15] **판정 불가** — 환경을 세우지 못했다: {type(exc).__name__}: {exc}")
        print("[OPS15] 컨테이너 안에서 DJANGO_SETTINGS_MODULE 를 주고 돌린다")
        return EXIT_UNDECIDABLE

    rules = counts["rules"]
    print(f"[OPS15] [입력] 활성 카메라묶음 구역 {counts['zones_total']}개 · "
          f"쓴 구역 {counts['zone_used']} · 그 구역 카메라 {counts['cameras_in_zone']}대 · "
          f"구역 출처 {counts['zone_origin']} · "
          f"규칙 {rules['min_cameras']}중 {rules['min_down']} · "
          f"두절 문턱 {rules['timeout_minutes']:g}분 · 동시 창 {rules['window_minutes']:g}분")
    print(f"[OPS15] 캐시 처리: {counts['cache_note']} — 판정은 HTTP 를 지나지 않고 "
          f"ORM 으로 직접 센다 (P-19)")
    if counts["zone_used"] is None:
        print("[OPS15] **판정 불가** — 잴 구역이 없다. 「검사 못함」은 「0건 검사」가 "
              "아니다 (D-301)")
        return EXIT_UNDECIDABLE
    if not counts["rolled_back"]:
        print("[OPS15] **회색(exit 2)** — 되돌리지 못했다. 판정기가 남긴 사실 위에서 "
              "낸 초록은 초록이 아니다")
        return EXIT_UNDECIDABLE

    rc = EXIT_OK
    for (name, ok, why) in judge(counts):
        print(f"[OPS15] {'  ' if ok else 'X '}{name:26} {why}")
        if not ok:
            rc = EXIT_FAIL
    if args.json:
        print("[OPS15] JSON " + json.dumps(counts, ensure_ascii=False, sort_keys=True,
                                           default=str))
    print("[OPS15] " + ("통과 — 3중 2는 1건이고 1대는 0건이다"
                        if rc == EXIT_OK else
                        "실패 — 위의 X 가 아직 비어 있는 자리다"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
