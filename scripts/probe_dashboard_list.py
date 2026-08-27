#!/usr/bin/env python
"""Dashboard 목록 응답에 **남의 것이 들어 있는가** — 본문을 직접 본다 (W0-14c).

왜 이 프로브인가
----------------
`via_parent` 자식 필터가 `"id":5` 하나를 잡았는데, 같은 응답에 그 대시보드의
**이름**(`iso-dash-N`)은 없었다. 두 가지 중 하나다:

  (가) 진짜 누출인데 응답 스키마가 이름을 안 싣는다
  (나) `"id":5` 가 **중첩된 다른 객체**(패널·위젯 등)의 id 라서 걸린 오탐

둘을 가르지 않고 "잡혔으니 누출"이라 적으면 그것은 측정이 아니라 추측이다 —
이번 턴에 FlightLog 의 500 을 가른 것과 같은 이유로, 본문을 직접 본다.

읽기 전용이다. 데이터를 만들지도 고치지도 않는다.

    python scripts/probe_dashboard_list.py
"""
from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def main() -> int:
    Dashboard = apps.get_model("dashboard", "Dashboard")
    Panel = apps.get_model("dashboard", "DashboardPanel")

    rows = list(Dashboard._base_manager.values("id", "name", "code", "group_id")[:20])
    print(f"[PROBE] dashboard.Dashboard {Dashboard._base_manager.count()}행")
    for r in rows[:10]:
        print(f"        id={r['id']:<5} group={str(r['group_id']):<6} {r['name']}")

    print()
    print(f"[PROBE] dashboard.DashboardPanel {Panel._base_manager.count()}행 — "
          f"목록 응답에 **중첩**되어 나갈 수 있는 객체다")
    for r in list(Panel._base_manager.values("id", "dashboard_id", "group_id")[:10]):
        print(f"        id={r['id']:<5} dashboard={r['dashboard_id']} group={r['group_id']}")

    print()
    print("[PROBE] 판단 기준")
    print("        · 목록 응답의 최상위 항목 id 에 남의 대시보드 id 가 있으면 → 누출")
    print("        · 중첩된 패널·위젯의 id 가 우연히 같은 수면 → 자식 필터의 오탐")
    print("        두 경우가 같은 문자열(\"id\":N)로 보이므로, 시험은 **이름 같은 고유값**을")
    print("        함께 봐야 한다. 이름이 없는 스키마라면 그 사실 자체가 조사 대상이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
