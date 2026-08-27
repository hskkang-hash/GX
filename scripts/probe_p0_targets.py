#!/usr/bin/env python
"""P0 모델의 **실경로와 필수 필드를 기동본에서 실측한다** (W0-14c 준비).

왜 필요한가
-----------
`p0_target_draft.md` 는 **정적 초안**이다. 그 문서 스스로 §4 에서 세 가지를 기동본에서
확인하라고 적었다:

  1. 수정/삭제 경로의 실제 모양 — 이 저장소는 PATCH 가 전체에 1건이고, 수정은 PUT
     (devices 는 POST), 삭제는 대개 `delete/{ids}` 대량 경로다
  2. dj-core 부모(`BaseModel`·`BaseModelWithGroup`·`MeasurableModelWithGroup`)의 필수 필드 —
     **저장소 밖이라 정적으로는 보이지 않는다**
  3. 라우트가 없는 시나리오

W0-14b 를 죽인 것이 바로 이 둘이었다 — 추정한 경로와 못 본 필수 FK 24건.
**추정 위에 배선을 쌓으면 전부 다시 해야 한다.**

    python scripts/probe_p0_targets.py                 # 전체
    python scripts/probe_p0_targets.py flight_log.FlightLog surveillance.VideoAnalysis
"""
from __future__ import annotations

import os
import re
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import models  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: D-262 ② 가 EXIT 필수로 지정한 P0. 착수 순서대로 — D-266 선결 2종 먼저,
#: 그 다음 필수 FK 가 적은 순(배선이 싼 순).
#: 근거: evidence/W0-14/leak_targets_coverage.md §7-2 · p0_target_draft.md §2
P0 = [
    "flight_log.FlightLog",                              # ★ D-266
    "surveillance.VideoAnalysis",                        # ★ D-266
    "terminals.RouteTerminal",
    "task_status.TaskStatus",
    "surveillance.MissionWaypoint",
    "orders.OrderHistory",
    "orders.OrderItem",
    "delivery.DeliveryOperationItem",
    "surveillance.SurveillanceProfileChecklistItem",
    "surveillance.SurveillanceProfileDrone",
    "orders.OrderStatusMapping",
    "delivery.DeliveryOperation",
    "terminals.TerminalOperatingTime",
    "surveillance.SurveillanceProfileChecklist",
    "orders.Payment",
]

AUTO = ("AutoField", "BigAutoField")


def required_fields(model) -> list[str]:
    """저장에 **반드시** 값이 필요한 필드. dj-core 부모의 것까지 포함해 실측한다."""
    out = []
    for f in model._meta.get_fields():
        if not isinstance(f, models.Field) or f.auto_created:
            continue
        if f.get_internal_type() in AUTO:
            continue
        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
            continue
        if f.null or f.blank or f.has_default():
            continue
        rel = f.related_model._meta.label if f.related_model else ""
        out.append(f"{f.name}:{f.get_internal_type()}{'→' + rel if rel else ''}")
    return out


def group_field(model) -> str:
    names = {f.name for f in model._meta.get_fields()}
    if "group" in names:
        return "group (FK)"
    if "groups" in names:
        return "groups (M2M)"
    return "**없음**"


def routes_for(model) -> list[tuple[str, str]]:
    """django-ninja 라우트 중 이 모델의 앱을 지나는 것. 경로에 pk 자리가 있는지 표시한다."""
    found: list[tuple[str, str]] = []
    try:
        from config.urls import api  # 프로젝트마다 다르면 여기서 멈춘다 — 조용히 넘기지 않는다
    except Exception as exc:
        print(f"  ⚠ 라우트 열거 불가: {exc}")
        return found
    for prefix, router in getattr(api, "_routers", []):
        for path, path_view in getattr(router, "path_operations", {}).items():
            full = (prefix.rstrip("/") + "/" + path.lstrip("/")).replace("//", "/")
            for op in path_view.operations:
                for method in op.methods:
                    found.append((method, "/" + full.lstrip("/")))
    return found


PK_TOKEN = re.compile(r"\{[^}]*\}")


def main() -> int:
    wanted = sys.argv[1:] or P0
    all_routes = None
    for label in wanted:
        try:
            model = apps.get_model(label)
        except LookupError:
            print(f"=== {label}: **모델이 없다** — 이름이 바뀌었거나 앱이 빠졌다")
            continue
        if all_routes is None:
            all_routes = routes_for(model)
        app = label.split(".")[0]
        req = required_fields(model)
        print(f"\n=== {label}  (테이블 {model._meta.db_table})")
        print(f"    부모: {' → '.join(b.__name__ for b in type(model).__mro__[0:1])}"
              f"{', '.join(b.__name__ for b in model.__mro__[1:3])}")
        print(f"    그룹 필드: {group_field(model)}")
        print(f"    필수 필드 {len(req)}개: {req if req else '없음'}")
        hits = [(m, p) for m, p in (all_routes or []) if f"/{app.replace('_', '-')}/" in p
                or f"/{app}/" in p]
        pk_hits = [(m, p) for m, p in hits if PK_TOKEN.search(p)]
        print(f"    앱 라우트 {len(hits)}개 · 그중 pk 를 지목하는 것 {len(pk_hits)}개")
        for m, p in sorted(pk_hits)[:14]:
            print(f"      {m:7} {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
