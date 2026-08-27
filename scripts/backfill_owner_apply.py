#!/usr/bin/env python
"""소유자 백필 **적용본** — created_by / group (W0-13 · D-261).

⚠ 이 스크립트는 **행을 쓴다.** dry-run(`backfill_owner_dryrun.py`)의 짝이다.

D-261 이 건 조건 3건 — 하나라도 빠지면 적용을 거부한다
--------------------------------------------------------
  (1) **dry-run 리포트 첨부** (D-209)  → `--dryrun-report <경로>` 로 실재를 확인한다
  (2) **역방향 롤백 스크립트**          → `scripts/backfill_owner_rollback.py` 가 짝이고,
                                          이 스크립트가 그 입력인 **저널을 먼저 쓴다**
  (3) **사전 백업** (D-002)             → `--backup <덤프파일>` 의 실재·크기를 확인한다

  세 조건을 인자로 받는 이유: 체크박스가 아니라 **파일의 실재**로 확인하기 위해서다.
  "백업했다"는 말은 검증할 수 없지만 덤프 파일의 크기와 시각은 검증할 수 있다.

무엇을 적용하나 — D-261 의 세 갈래 중 (a)(b)만이다
---------------------------------------------------
  **(a) 부모 상속 가능 23,616행 → 적용.** 내역은 R2 + R3 다:
       · R3 (부모 레코드의 group 을 물려받음) 23,273
       · R2 (created_by 의 소속 group)          343
       소유가 **결정론적으로 도출**되므로 추측이 아니다.

  **(b) terminals.Terminal 3,399행 → 분할.**
       역참조 전수 실측으로 소유가 **하나로 정해지는 1,809행만** 적용한다.
       참조가 0인 1,590행은 **채우지 않는다** — 채우면 소유자를 추측하게 된다.
       그 1,590 은 `tenant_unassigned` 로 **선언**되고(백엔드 registry),
       격리 시험이 "전역 관리자 외 비노출"을 단언으로 지킨다.

  **(c) 공용 마스터 약 2,000행 → 이 스크립트의 범위가 아니다.**
       백필하지 않는다(D-261 c). `shared: true` 등록은 registry 의 일이다.

★ **R1 45행은 이 판정의 범위 밖이다.** D-261 (a) 의 23,616 은 R2+R3 의 합이고,
  R1(group 은 있는데 created_by 가 없는 45행)은 RESUME_NEXT 가 언급하지 않았다.
  임의로 끼워 넣지 않는다 — 승인받지 않은 행을 쓰는 것이 이 스크립트가 가장 하면 안 되는 일이다.
  `--include-r1` 을 주면 적용하되, **별도 판정이 있을 때만 쓰라.**

사용
----
    # 0) 계획만 본다 (쓰지 않는다). dry-run 과 같은 수가 나와야 한다.
    python scripts/backfill_owner_apply.py

    # 1) 실제 적용 — 세 조건을 전부 파일로 준다
    python scripts/backfill_owner_apply.py --apply \\
        --dryrun-report docs/agent/evidence/W0-13/backfill_dryrun.md \\
        --backup /backup/gx_before_backfill.dump \\
        --journal docs/agent/evidence/W0-13/backfill_journal.jsonl

    # 2) 되돌리기
    python scripts/backfill_owner_rollback.py --journal <같은 경로> --apply

⚠ **운영 DB 금지.** 복제본에서 먼저 돌린다 (D-245 · 불변 제약).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import models, transaction  # noqa: E402
from django.db.models import Q  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).resolve().parent

#: (b) 역추론 대상. 참조가 **정확히 한 테넌트**를 가리킬 때만 그 테넌트로 정한다.
SPLIT_BY_BACKREF = {"terminals.Terminal"}

#: 백업 파일이 이보다 작으면 백업이 아니라고 본다 (빈 파일·실패한 덤프 방지).
MIN_BACKUP_BYTES = 1024 * 1024  # 1MB


# ---------------------------------------------------------------------------
# dry-run 의 분류 로직을 **그대로 재사용한다** — 다시 쓰면 두 수가 갈린다
# ---------------------------------------------------------------------------
def load_dryrun_module():
    """`backfill_owner_dryrun.py` 를 모듈로 읽는다.

    왜 import 하나: 귀속 규칙(R1/R2/R3)·제외 앱·소프트삭제 판정을 **복제하지 않기 위해서**다.
    복제하면 언젠가 dry-run 과 적용본이 다른 수를 말하고, 그때 어느 쪽이 진실인지 알 수 없다
    (D-227 manifest 유실과 같은 실패 모양).
    """
    path = HERE / "backfill_owner_dryrun.py"
    spec = importlib.util.spec_from_file_location("backfill_owner_dryrun", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DR = load_dryrun_module()


def soft_filter(model) -> Q:
    if any(f.name == "deleted" for f in model._meta.get_fields()):
        return Q(deleted__isnull=True)
    return Q()


# ---------------------------------------------------------------------------
# 저널 — 쓰기 **전에** 옛 값을 남긴다. 이것이 롤백의 유일한 근거다.
# ---------------------------------------------------------------------------
class Journal:
    def __init__(self, path: Path | None):
        self.path = path
        self._fh = None
        self.count = 0

    def open(self):
        if self.path is None:
            return
        if self.path.exists():
            raise SystemExit(
                f"[BACKFILL] 저널이 이미 있다: {self.path}\\n"
                "         덮어쓰지 않는다 — 기존 저널을 지우면 그 적용분은 되돌릴 수 없다."
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", encoding="utf-8", newline="\\n")
        self._fh.write(json.dumps({"_meta": "GuardianX backfill journal · W0-13 · D-261"},
                                  ensure_ascii=False) + "\\n")

    def record(self, label: str, pk, field: str, old, new):
        self.count += 1
        if self._fh:
            self._fh.write(json.dumps(
                {"model": label, "pk": pk, "field": field, "old": old, "new": new},
                ensure_ascii=False, default=str) + "\\n")

    def close(self):
        if self._fh:
            self._fh.flush()
            os.fsync(self._fh.fileno())   # 저널이 디스크에 닿기 전에 죽으면 롤백 불가다
            self._fh.close()


# ---------------------------------------------------------------------------
# (a) R3 — 부모의 group 을 물려받는다
# ---------------------------------------------------------------------------
def plan_r3(model, group_field: str) -> list[tuple]:
    """(pk, 새 group_id) 목록. **가장 많이 덮는 부모 하나**를 dry-run 과 같은 방식으로 고른다."""
    if group_field != "group":
        return []          # M2M(groups)은 단일 값 대입이 아니므로 이 갈래에서 다루지 않는다
    soft = soft_filter(model)
    best_field, best_cover = None, 0
    for f in model._meta.get_fields():
        if not isinstance(f, models.ForeignKey):
            continue
        pnames = {pf.name for pf in f.related_model._meta.get_fields()}
        if "group" not in pnames:
            continue
        try:
            cover = model._base_manager.filter(
                soft & Q(group__isnull=True) & Q(**{f"{f.name}__group__isnull": False})
            ).count()
        except Exception:
            continue
        if cover > best_cover:
            best_field, best_cover = f.name, cover
    if not best_field:
        return []
    qs = model._base_manager.filter(
        soft & Q(group__isnull=True) & Q(**{f"{best_field}__group__isnull": False})
    ).values_list("pk", f"{best_field}__group_id")
    return list(qs)


# ---------------------------------------------------------------------------
# (a) R2 — created_by 의 소속 group
# ---------------------------------------------------------------------------
def plan_r2(model, group_field: str) -> list[tuple]:
    if group_field != "group":
        return []
    soft = soft_filter(model)
    qs = model._base_manager.filter(
        soft & Q(group__isnull=True) & Q(created_by__isnull=False)
        & Q(created_by__userprofilelink__group__isnull=False)
    ).values_list("pk", "created_by__userprofilelink__group_id")
    # 한 사용자가 여러 group 에 걸린 경우가 있으면 **정하지 않는다** — 중복 pk 를 걸러 낸다.
    by_pk: dict = {}
    ambiguous: set = set()
    for pk, gid in qs:
        if pk in by_pk and by_pk[pk] != gid:
            ambiguous.add(pk)
        by_pk[pk] = gid
    for pk in ambiguous:
        by_pk.pop(pk, None)
    if ambiguous:
        print(f"[BACKFILL] ⚠ {model._meta.label}: created_by 가 여러 group 에 걸린 {len(ambiguous)}행 "
              "— 소유를 정하지 않고 건너뛴다 (추측 금지)")
    return list(by_pk.items())


# ---------------------------------------------------------------------------
# (b) 역참조 전수 — 소유가 **하나로 정해질 때만** 정한다
# ---------------------------------------------------------------------------
def plan_backref(model) -> tuple[list[tuple], list, list]:
    """(정해짐, 참조 0 = tenant_unassigned, 다중 소유 = 사람 판단)"""
    soft = soft_filter(model)
    targets = list(model._base_manager.filter(soft & Q(group__isnull=True)).values_list("pk", flat=True))
    rels = [
        f for f in model._meta.get_fields()
        if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
        and "group" in {pf.name for pf in f.related_model._meta.get_fields()}
    ]
    decided, orphan, multi = [], [], []
    for pk in targets:
        groups: set = set()
        for rel in rels:
            try:
                groups |= set(
                    rel.related_model._base_manager.filter(**{f"{rel.field.name}_id": pk})
                    .exclude(group__isnull=True)
                    .values_list("group_id", flat=True)
                )
            except Exception:
                continue
            if len(groups) > 1:
                break
        if not groups:
            orphan.append(pk)
        elif len(groups) == 1:
            decided.append((pk, next(iter(groups))))
        else:
            multi.append(pk)          # **채우지 않는다.** 다중 소유는 사람이 정한다
    return decided, orphan, multi


# ---------------------------------------------------------------------------
def apply_pairs(model, field: str, pairs: list[tuple], journal: Journal, do_write: bool) -> int:
    """(pk, 값) 목록을 적용하고 **옛 값을 먼저 저널에 남긴다**."""
    if not pairs:
        return 0
    label = model._meta.label
    col = f"{field}_id"
    olds = dict(model._base_manager.filter(pk__in=[p for p, _ in pairs]).values_list("pk", col))
    written = 0
    by_value: dict = {}
    for pk, val in pairs:
        if olds.get(pk) == val:
            continue                     # 이미 그 값이면 건드리지 않는다
        journal.record(label, pk, col, olds.get(pk), val)
        by_value.setdefault(val, []).append(pk)
        written += 1
    if do_write:
        with transaction.atomic():
            for val, pks in by_value.items():
                # .update() 를 쓴다 — save() 는 auto_now·시그널을 건드려 백필이 다른 열까지 바꾼다
                for i in range(0, len(pks), 1000):
                    model._base_manager.filter(pk__in=pks[i:i + 1000]).update(**{col: val})
    return written


# ---------------------------------------------------------------------------
def guard(args) -> None:
    """D-261 의 조건 3건을 **파일의 실재**로 확인한다."""
    problems = []
    if not args.dryrun_report or not Path(args.dryrun_report).is_file():
        problems.append("(1) dry-run 리포트가 없다 — --dryrun-report <경로> (D-209)")
    if not args.backup:
        problems.append("(2) 백업 파일이 지정되지 않았다 — --backup <덤프> (D-002)")
    else:
        b = Path(args.backup)
        if not b.is_file():
            problems.append(f"(2) 백업 파일이 없다: {b} (D-002)")
        elif b.stat().st_size < MIN_BACKUP_BYTES:
            problems.append(
                f"(2) 백업이 너무 작다 ({b.stat().st_size:,}B < {MIN_BACKUP_BYTES:,}B) — "
                "실패한 덤프일 수 있다 (D-002)")
    if not args.journal:
        problems.append("(3) 저널 경로가 없다 — --journal <경로>. 저널 없이는 되돌릴 수 없다 (D-261)")
    if problems:
        print("[BACKFILL] 적용을 **거부**한다 — D-261 조건 미충족:")
        for p in problems:
            print("  · " + p)
        raise SystemExit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다 (기본은 계획만)")
    ap.add_argument("--dryrun-report", help="D-209 — dry-run 리포트 경로")
    ap.add_argument("--backup", help="D-002 — 적용 전 덤프 파일 경로")
    ap.add_argument("--journal", help="D-261 — 롤백 저널을 쓸 경로")
    ap.add_argument("--include-r1", action="store_true",
                    help="R1(45행)도 적용. ★ D-261 범위 밖 — 별도 판정이 있을 때만")
    args = ap.parse_args()

    if args.apply:
        guard(args)
    journal = Journal(Path(args.journal) if (args.journal and args.apply) else None)
    journal.open()

    mode = "적용" if args.apply else "계획(쓰지 않음)"
    print(f"[BACKFILL] 모드: {mode}")
    if not args.apply:
        print("[BACKFILL] ※ 이 실행은 한 행도 쓰지 않는다. --apply 와 조건 3건이 있어야 쓴다.")

    totals = {"r3": 0, "r2": 0, "backref": 0}
    unassigned: dict[str, list] = {}
    multi_owner: dict[str, list] = {}

    try:
        for model, group_field in DR.tenantish_models():
            label = model._meta.label
            if model._meta.app_label in DR.SYSTEM_OWNED_APPS:
                continue          # created_by IS NULL 을 '시스템 기본'의 뜻으로 쓴다 — 건드리면 깨진다
            try:
                if label in SPLIT_BY_BACKREF:
                    decided, orphan, multi = plan_backref(model)
                    n = apply_pairs(model, "group", decided, journal, args.apply)
                    totals["backref"] += n
                    unassigned[label] = orphan
                    if multi:
                        multi_owner[label] = multi
                    print(f"  (b) {label:44} 정해짐 {len(decided):>5} · "
                          f"참조0 {len(orphan):>5} · 다중소유 {len(multi):>3}")
                    continue
                r3 = plan_r3(model, group_field)
                r2 = plan_r2(model, group_field)
                seen = {pk for pk, _ in r3}
                r2 = [(pk, v) for pk, v in r2 if pk not in seen]   # R3 가 우선
                n3 = apply_pairs(model, "group", r3, journal, args.apply)
                n2 = apply_pairs(model, "group", r2, journal, args.apply)
                totals["r3"] += n3
                totals["r2"] += n2
                if n3 or n2:
                    print(f"  (a) {label:44} R3 {n3:>6} · R2 {n2:>5}")
            except Exception as exc:      # 저장소 모델 ↔ 운영 스키마 불일치 (P-LOCAL-4)
                print(f"  ⚠ {label:44} 건너뜀 — {str(exc).splitlines()[0][:90]}")
    finally:
        journal.close()

    print()
    print(f"[BACKFILL] (a) 부모상속 R3={totals['r3']:,} · created_by소속 R2={totals['r2']:,} "
          f"· 합계 {totals['r3'] + totals['r2']:,}   (D-261 예상 23,616)")
    print(f"[BACKFILL] (b) 역참조 단일소유 {totals['backref']:,}   (D-261 예상 1,809)")
    for label, pks in unassigned.items():
        print(f"[BACKFILL] (b) {label} tenant_unassigned {len(pks):,}행 — **채우지 않았다** "
              "(D-261 예상 1,590). registry 에 선언하고 시험이 비노출을 지킨다")
    for label, pks in multi_owner.items():
        print(f"[BACKFILL] ⚠ {label} **다중 소유 {len(pks):,}행** — 채우지 않았다. 사람이 정해야 한다 "
              "(dry-run 실측은 0건이었다 — 0 이 아니면 전제가 달라진 것이다)")
    if not args.include_r1:
        print("[BACKFILL] ※ R1(group 있고 created_by 없음)은 **적용하지 않았다** — "
              "D-261 (a) 의 23,616 은 R2+R3 이고 R1 은 판정 범위 밖이다.")
    if args.apply:
        print(f"[BACKFILL] 저널 {journal.count:,}행 → {args.journal}")
        print("[BACKFILL] 되돌리기: python scripts/backfill_owner_rollback.py "
              f"--journal {args.journal} --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
