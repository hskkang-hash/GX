#!/usr/bin/env python
"""FlightLog 상세 조회가 테넌트를 보는가 — **읽기 전용** 실측 (W0-14c · D-266).

왜 이 프로브가 필요한가
-----------------------
격리 시험에서 `GET /api/flight-log/flight-log/detail/{id}` 가 **500** 을 냈다.
500 은 `(403, 404)` 가 아니므로 시험은 실패로 기록한다 — 그것은 맞다.
그러나 500 에는 성격이 다른 두 가지가 섞인다:

  (가) **막혔다** — 소유자가 아니라 조회가 안 됐고, 그 뒤 처리가 죽었다
  (나) **찾았다** — 남의 레코드를 정상적으로 꺼낸 뒤, 다른 데이터가 없어서 죽었다

(가)면 격리는 서 있고 응답 계약만 나쁜 것이다. (나)면 **격리가 없다.**
둘을 구별하지 않고 "500 이니 안전하다"고 읽는 것이 이 저장소가 반복해 만난 실패 모양이다.

무엇을 하나
-----------
`FlightLogService.get_flight_log_detail` 이 딛고 선 **조회 한 줄**을 그대로 재현해,
서로 다른 테넌트의 레코드가 나오는지 본다. 쓰기는 하지 않는다.

    python scripts/probe_flightlog_lookup.py
"""
from __future__ import annotations

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
    FlightLog = apps.get_model("flight_log", "FlightLog")

    total = FlightLog._base_manager.count()
    by_group: dict = {}
    for gid, pk in FlightLog._base_manager.values_list("group_id", "pk"):
        by_group.setdefault(gid, []).append(pk)

    print(f"[PROBE] flight_log.FlightLog 전체 {total:,}행 · 소속 group {len(by_group)}종")
    for gid, pks in sorted(by_group.items(), key=lambda kv: -len(kv[1]))[:6]:
        print(f"        group_id={gid!s:6} {len(pks):>5}행  (예: pk {pks[:3]})")

    print()
    print("[PROBE] 핸들러가 쓰는 조회 = FlightLog._base_manager.get(id=id)")
    print("        (flight_log/services/flight_log_service.py:get_flight_log_detail)")
    print()

    # `objects` 와 `_base_manager` 가 같은 답을 주는지 — 다르면 매니저가 무언가를 거른다는 뜻.
    n_default = FlightLog.objects.count()
    print(f"[PROBE] FlightLog.objects.count()      = {n_default:,}")
    print(f"[PROBE] FlightLog._base_manager.count() = {total:,}")
    if n_default == total:
        print("        → 두 수가 같다. 이 문맥에서는 기본 매니저도 아무것도 거르지 않는다.")

    # 핵심: 서로 다른 group 의 레코드를 **같은 조회 한 줄**로 전부 꺼낼 수 있는가
    groups = [g for g in by_group if g is not None]
    print()
    if len(groups) < 2:
        print(f"[PROBE] ⚠ 소속 group 이 {len(groups)}종뿐이라 교차 조회를 재지 못한다.")
        print("        판정 불가 — '안전하다'가 아니다.")
        return 0

    picked = [(g, by_group[g][0]) for g in groups[:3]]
    ok = 0
    for gid, pk in picked:
        obj = FlightLog._base_manager.get(id=pk)
        print(f"[PROBE] _base_manager.get(id={pk}) → group_id={obj.group_id} · 조회 성공")
        ok += 1
    print()
    print(f"[PROBE] 서로 다른 테넌트 {ok}건을 **같은 조회 한 줄로 전부** 꺼냈다.")
    print("        이 조회에는 요청자·테넌트가 인자로 들어오지 않는다 —")
    print("        즉 상세 응답의 500 은 '막혔다'가 아니라 '찾은 뒤 다른 데서 죽었다'이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
