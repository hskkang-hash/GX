#!/usr/bin/env python
"""소유자 백필 **되돌리기** — `backfill_owner_apply.py` 의 짝 (W0-13 · D-261).

D-261 은 롤백 스크립트 **없이 적용을 금지**했다. 23,616행은 되돌릴 수 없으면 사고다.
이 스크립트가 그 짝이고, 적용본이 쓴 저널(JSONL)만을 근거로 옛 값을 복원한다.

무엇을 근거로 되돌리나
----------------------
저널의 한 줄 = `{"model": "app.Model", "pk": 12, "field": "group_id", "old": null, "new": 5}`
적용본은 **쓰기 전에** 이 줄을 남기고 fsync 한다. 그러므로 저널에 있는 것은 전부 실제로
바뀌었거나(적용 성공) 바뀌지 않았거나(중간에 죽음) 둘 중 하나다 — 어느 쪽이든 복원은 안전하다.

★ **남이 그 뒤에 바꾼 값은 되돌리지 않는다.**
  복원 전에 현재 값이 저널의 `new` 와 같은지 확인하고, 다르면 **건너뛰고 보고**한다.
  이것을 안 하면 롤백이 제3자의 정당한 변경을 조용히 덮는다 —
  백필이 만들 수 있는 두 번째 사고다.

사용
----
    python scripts/backfill_owner_rollback.py --journal <경로>           # 계획만 (쓰지 않음)
    python scripts/backfill_owner_rollback.py --journal <경로> --apply   # 실제 복원

⚠ 운영 DB 금지. 복제본에서 먼저 (D-245).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.apps import apps  # noqa: E402
from django.db import transaction  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def read_journal(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"[ROLLBACK] 저널이 없다: {path}")
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            # 마지막 줄이 잘렸을 수 있다(적용 중 중단). 조용히 넘기지 않는다.
            print(f"[ROLLBACK] ⚠ {i}행을 읽을 수 없다 — 잘린 저널일 수 있다. 건너뛴다")
            continue
        if "_meta" in rec:
            continue
        rows.append(rec)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", required=True)
    ap.add_argument("--apply", action="store_true", help="실제로 복원한다 (기본은 계획만)")
    args = ap.parse_args()

    rows = read_journal(Path(args.journal))
    print(f"[ROLLBACK] 저널 {len(rows):,}행 · 모드: {'복원' if args.apply else '계획(쓰지 않음)'}")

    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)

    restored = skipped_changed = missing = 0
    for label, recs in sorted(by_model.items()):
        try:
            model = apps.get_model(label)
        except LookupError:
            print(f"  ⚠ {label:44} 그런 모델이 없다 — 건너뜀 ({len(recs)}행)")
            continue

        field = recs[0]["field"]
        pks = [r["pk"] for r in recs]
        current: dict = {}
        for i in range(0, len(pks), 1000):
            current.update(
                dict(model._base_manager.filter(pk__in=pks[i:i + 1000]).values_list("pk", field))
            )

        # old 값별로 묶어 update() 한다 — save() 는 auto_now 를 건드린다
        groups: dict = defaultdict(list)
        for r in recs:
            if r["pk"] not in current:
                missing += 1
                continue
            if current[r["pk"]] != r["new"]:
                # 우리가 쓴 값이 아니다 — 남이 바꿨거나 애초에 안 써졌다. 덮지 않는다.
                skipped_changed += 1
                continue
            groups[r["old"]].append(r["pk"])

        n = sum(len(v) for v in groups.values())
        restored += n
        print(f"  {label:44} 복원 대상 {n:>6} / 저널 {len(recs):>6}")
        if args.apply and n:
            with transaction.atomic():
                for old, pk_list in groups.items():
                    for i in range(0, len(pk_list), 1000):
                        model._base_manager.filter(pk__in=pk_list[i:i + 1000]).update(**{field: old})

    print()
    print(f"[ROLLBACK] 복원 {restored:,} · 값이 달라 건너뜀 {skipped_changed:,} · 행 없음 {missing:,}")
    if skipped_changed:
        print("[ROLLBACK] ⚠ 건너뛴 행은 **우리가 쓴 값이 아니다.** 그 뒤에 누가 바꿨거나 "
              "적용이 중간에 죽은 것이다. 덮지 않는 것이 옳다 — 필요하면 사람이 개별 확인하라.")
    if not args.apply:
        print("[ROLLBACK] ※ 한 행도 쓰지 않았다. 실제 복원은 --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
