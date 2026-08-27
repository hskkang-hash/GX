#!/usr/bin/env python
"""커밋된 인구조사가 **못 본 격리 대상**을 센다 (D-271 ② 부수 발견).

무엇을 묻나
-----------
`leak_targets.json`(131종)은 W0-13 백필 dry-run 의 **덤프 집계**에서 나왔다.
덤프 집계는 **행이 있는 표**만 센다. 그러면 행이 0인 모델은 인구조사에 없고,
없으면 아무도 보지 않는다 — **행이 0이라는 이유의 자동 면제**다 (D-263 이 금지한 것).

행이 0인 것은 "격리가 필요 없다"가 아니라 **"아직 안 썼다"**이다.
내일 첫 행이 들어오는 순간 그 모델은 무방비로 시작한다.

    python scripts/probe_census_gap.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

FRAMEWORK_APPS = {"user", "core"}

CENSUS = Path("/docs/agent/evidence/W0-14/leak_targets.json")
if not CENSUS.is_file():
    CENSUS = (Path(__file__).resolve().parent.parent / "docs" / "agent"
              / "evidence" / "W0-14" / "leak_targets.json")


def main() -> int:
    doc = json.loads(CENSUS.read_text(encoding="utf-8"))
    committed = {t["label"] for t in doc["targets"]}

    missing = []
    for model in apps.get_models():
        label = f"{model._meta.app_label}.{model.__name__}"
        if model._meta.app_label in FRAMEWORK_APPS or label in committed:
            continue
        # ★ 이름으로 세지 않는다 (D-263). `auth.Permission` 에는 `auth.Group.permissions` 의
        #   **역방향** 접근자가 `group` 이라는 이름으로 잡힌다 — 그것은 소유 필드가 아니다.
        #   첫 판이 그것을 800행짜리 격리 대상으로 보고했다. 실제 필드만 본다.
        from django.db import models as dj
        concrete = [f for f in model._meta.get_fields() if isinstance(f, dj.Field)]
        owns = any(
            (f.name == "group" and getattr(f, "many_to_one", False))
            or (f.name == "groups" and getattr(f, "many_to_many", False))
            for f in concrete
        )
        if not owns:
            continue
        try:
            n = model._base_manager.count()
            err = ""
        except Exception as exc:                      # 스키마 불일치 (P-LOCAL-4)
            n, err = None, str(exc).splitlines()[0][:60]
        missing.append((label, n, err))

    zero = [m for m in missing if m[1] == 0]
    nonzero = [m for m in missing if m[1] not in (0, None)]
    broken = [m for m in missing if m[1] is None]

    print(f"[GAP] 인구조사에 없는 격리 대상 {len(missing)}종")
    print(f"      · 행 0        {len(zero):>3}종 — 덤프 집계라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다**")
    print(f"      · 행 있음     {len(nonzero):>3}종 — **집계 누락이다. 0행 아티팩트가 아니다**")
    print(f"      · 셀 수 없음  {len(broken):>3}종 — 저장소 모델 ↔ 운영 스키마 불일치 (P-LOCAL-4)")
    print()
    if nonzero:
        print("[GAP] ★ 행이 있는데 인구조사에 없던 것 — 이쪽이 문제다")
        for label, n, _ in sorted(nonzero, key=lambda x: -x[1]):
            print(f"        {label:44} {n:>6}행")
        print()
    if broken:
        print("[GAP] 셀 수 없음 (P-LOCAL-4)")
        for label, _, err in broken:
            print(f"        {label:44} {err}")
        print()
    print("[GAP] 행 0 (아직 안 쓴 것)")
    print("        " + " · ".join(label for label, _, _ in sorted(zero)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
