#!/usr/bin/env python
"""격리 대상 모수를 **코드베이스에서 직접** 센다 (D-271 ②).

왜 필요한가
-----------
`test_registry_covers_all_isolatable_models` 는 `groups` M2M 을 가진 모델만 셌다.
그 모수로 나온 "누락 1건"이 **작은 모수의 착시**였다 (D-260 지적 · D-271 인정).

실제 테넌시 기전은 dj-core `BaseModelWithGroup` 의 **`group` FK** 이고,
W0-13 백필이 채운 25,296행이 바로 그 열이다. 그래서 모수는 **M2M ∪ FK** 다.

이 스크립트는 그 모수를 **지금 코드에서** 세어, 커밋된 인구조사
(`leak_targets.json` · 131종)와 **대조**한다. 두 수가 갈리면 그 차이가 조사 대상이다 —
조용히 맞추지 않는다.

    python scripts/probe_isolatable_census.py            # 대조
    python scripts/probe_isolatable_census.py --emit     # tenant_census.py 생성용 데이터
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import models  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: dj-core 프레임워크 앱 — §0.4 금지구역이라 이 저장소가 고칠 수 없다.
#: **면제가 아니라 관할 밖**이다. 수는 따로 세어 보고한다.
FRAMEWORK_APPS = {"user", "core"}

CENSUS = Path("/docs/agent/evidence/W0-14/leak_targets.json")
if not CENSUS.is_file():
    CENSUS = Path(__file__).resolve().parent.parent / "docs" / "agent" / "evidence" / "W0-14" / "leak_targets.json"


def has_m2m(model) -> bool:
    return any(f.name == "groups" for f in model._meta.get_fields())


def has_fk(model) -> bool:
    return any(f.name == "group" and getattr(f, "many_to_one", False)
               for f in model._meta.get_fields())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="분류 표를 JSON 으로 낸다")
    args = ap.parse_args()

    m2m, fk, both, framework = [], [], [], []
    for model in apps.get_models():
        label = f"{model._meta.app_label}.{model.__name__}"
        a, b = has_m2m(model), has_fk(model)
        if not (a or b):
            continue
        if model._meta.app_label in FRAMEWORK_APPS:
            framework.append(label)
            continue
        if a and b:
            both.append(label)
        elif a:
            m2m.append(label)
        else:
            fk.append(label)

    live = sorted(set(m2m) | set(fk) | set(both))
    print(f"[CENSUS] 실측 모수 — 총 {len(live)}종")
    print(f"         groups M2M 만    {len(m2m):>4}")
    print(f"         group FK 만      {len(fk):>4}")
    print(f"         둘 다            {len(both):>4}   {both}")
    print(f"         dj-core 관할 밖  {len(framework):>4}  (§0.4 — 면제가 아니라 관할 밖)")
    print()
    print("[CENSUS] 옛 술어(groups M2M 만)로 세면 "
          f"{len(m2m) + len(both)}종 — 그것이 D-260 이 지적한 작은 모수다")

    if not CENSUS.is_file():
        print(f"[CENSUS] ⚠ 커밋된 인구조사를 못 찾았다: {CENSUS} — 대조하지 못한다")
        return 1

    doc = json.loads(CENSUS.read_text(encoding="utf-8"))
    committed = {t["label"] for t in doc["targets"]}
    print()
    print(f"[CENSUS] 커밋된 인구조사(leak_targets.json) {len(committed)}종 과 대조")
    only_live = sorted(set(live) - committed)
    only_doc = sorted(committed - set(live))
    print(f"         코드에만 있는 것 {len(only_live)}종: {only_live[:12]}")
    print(f"         문서에만 있는 것 {len(only_doc)}종: {only_doc[:12]}")

    if args.emit:
        Path("census_live.json").write_text(
            json.dumps({"live": live, "m2m_only": sorted(m2m), "fk_only": sorted(fk),
                        "both": sorted(both), "framework": sorted(framework)},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print("[CENSUS] census_live.json 생성")

    # 차이가 있으면 **그 차이가 조사 대상**이다. 맞을 때까지 인자를 고치지 않는다.
    return 0 if not (only_live or only_doc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
