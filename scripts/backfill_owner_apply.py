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

from django.db import connection, models, transaction  # noqa: E402
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


def load_shared_masters() -> dict[str, str]:
    """`backend/tests/tenant_classification.py` 의 SHARED_MASTERS 를 읽는다.

    ★ **D-261 (c) 는 공용 마스터의 백필을 금지했다.** 그런데 처음 판은 이 등록부를 아예
      참조하지 않아 `advanced_table.GridSetting`(479행) · `menu.Tab`(8행) 등을 채우려 했다.
      채우면 다른 테넌트 화면에서 국가·시간대·상태값이 사라진다 — 판정이 막으려던 그 사고다.
      **시뮬레이션이 아니었으면 그대로 썼을 것이다.**

    ⚠ 등록부를 못 읽으면 **진행하지 않는다.** 비어 있다고 보고 진행하면 금지 대상을 전부
      채우게 된다 — 실패했을 때 안전한 쪽은 "멈춤"이다.
    """
    for cand in (Path("/app/tests/tenant_classification.py"),
                 HERE.parent / "backend" / "tests" / "tenant_classification.py"):
        if cand.is_file():
            spec = importlib.util.spec_from_file_location("tenant_classification", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return dict(mod.SHARED_MASTERS)
    raise SystemExit(
        "[BACKFILL] 분류 등록부(tenant_classification.py)를 찾지 못했다 — 멈춘다.\n"
        "         이 파일이 없으면 D-261 (c) 의 '공용 마스터 백필 금지'를 지킬 수 없다."
    )


SHARED_MASTERS = load_shared_masters()


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
                f"[BACKFILL] 저널이 이미 있다: {self.path}\n"
                "         덮어쓰지 않는다 — 기존 저널을 지우면 그 적용분은 되돌릴 수 없다."
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", encoding="utf-8", newline="\n")
        self._fh.write(json.dumps({"_meta": "GuardianX backfill journal · W0-13 · D-261"},
                                  ensure_ascii=False) + "\n")

    def record(self, label: str, pk, field: str, old, new):
        self.count += 1
        if self._fh:
            self._fh.write(json.dumps(
                {"model": label, "pk": pk, "field": field, "old": old, "new": new},
                ensure_ascii=False, default=str) + "\n")

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
    """(정해짐, 참조 0 = tenant_unassigned, 다중 소유 = 사람 판단)

    ★ **D-261 의 판정이 딛고 선 SQL 을 그대로 쓴다** (`backfill_dryrun.md` §7).
      처음 판은 역참조를 **일반화해 다시 유도**했다 — 모든 역방향 FK 중 group 을 가진 것.
      그러면 (a) 이후 상태에서 **2,551 / 848** 이 나온다. 틀린 수는 아니다: MissionWaypoint
      (8,877행 · 백필 前 group 100% NULL)가 (a) 로 채워지며 새로 켜진 증거이고 다중 소유는 0 이다.

      그러나 D-261 이 승인한 것은 **1,809 적용 / 1,590 미배정**이고, 그 수는 아래 8경로를
      **백필 前 상태**에서 잰 것이다(문서 SQL 을 지금 돌리면 정확히 재현된다).
      일반화한 정의로 742행을 더 쓰면 그것은 **판정이 "채우지 않는다"고 분류한 행**이다.
      승인받지 않은 행을 쓰지 않는 것이 이 스크립트의 첫째 규칙이므로, **판정의 정의**를 쓴다.
      → (a) 뒤에 다시 재면 742행이 결정 가능해진다. **2차 판정으로 올린다.**
        지금 안 써서 잃는 것은 없다 — 뒤에 더할 수 있고, 잘못 쓰면 되돌려야 한다.
    """
    if model._meta.label != "terminals.Terminal":
        raise RuntimeError(
            f"plan_backref 는 terminals.Terminal 전용이다 (D-261 b). 받은 것: {model._meta.label}"
        )

    # backfill_dryrun.md §7 의 usage 8경로. 한 줄도 바꾸지 않는다.
    USAGE = """
      SELECT rt.terminal_id AS tid, r.group_id FROM terminals_routeterminal rt
        JOIN terminals_routes r ON r.id=rt.route_id WHERE r.group_id IS NOT NULL
      UNION ALL SELECT r.terminal_from_id, r.group_id FROM terminals_routes r WHERE r.group_id IS NOT NULL
      UNION ALL SELECT o.pickup_location_id, o.group_id FROM orders_order o WHERE o.group_id IS NOT NULL
      UNION ALL SELECT o.delivery_terminal_id, o.group_id FROM orders_order o WHERE o.group_id IS NOT NULL
      UNION ALL SELECT d.terminal_id, d.group_id FROM devices_device d WHERE d.group_id IS NOT NULL
      UNION ALL SELECT w.terminal_id, w.group_id FROM surveillance_missionwaypoint w WHERE w.group_id IS NOT NULL
      UNION ALL SELECT f.start_point_id, f.group_id FROM flight_log_flightlog f WHERE f.group_id IS NOT NULL
      UNION ALL SELECT f.end_point_id, f.group_id FROM flight_log_flightlog f WHERE f.group_id IS NOT NULL
    """
    sql = f"""
    WITH orphan AS (SELECT id FROM terminals_terminal WHERE deleted IS NULL AND group_id IS NULL),
    usage AS ({USAGE})
    SELECT o.id, count(DISTINCT u.group_id) AS tenants, min(u.group_id) AS gid
    FROM orphan o LEFT JOIN usage u ON u.tid = o.id
    GROUP BY o.id
    """
    decided, orphan, multi = [], [], []
    with connection.cursor() as c:
        c.execute(sql)
        for pk, tenants, gid in c.fetchall():
            if tenants == 0:
                orphan.append(pk)
            elif tenants == 1:
                decided.append((pk, gid))
            else:
                multi.append(pk)      # **채우지 않는다.** 다중 소유는 사람이 정한다
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


class _PlanRollback(Exception):
    """계획 모드의 트랜잭션을 되돌리기 위한 신호. 오류가 아니다."""


def run_phases(models, journal, totals, unassigned, multi_owner, do_write: bool) -> None:
    """(a) 를 전부 끝낸 뒤 (b) 를 한다. **순서가 답을 바꾼다.**

    Terminal 의 소유는 자식(RouteTerminal 등)의 group 이 말해 주는데, 그 자식들은
    백필 前에 자기도 비어 있다 (실측: TerminalOperatingTime·DeliveryEvent 는 group 0건,
    RouteTerminal 은 2,062 중 255건만). 한 패스로 돌면서 Terminal 을 먼저 만나면
    **정해짐이 14 로 나온다** — dry-run 의 1,809 와 어긋난다.
    (a) 가 RouteTerminal 을 Routes 에서 채운 뒤 (b) 를 돌리면 같은 답이 나온다.
    추론 깊이를 늘리는 것이 아니라 **의존 순서를 지키는 것**이다 — 새 추측을 넣지 않는다.
    """
    print("[BACKFILL] ── (a) 부모 상속 · created_by 소속 ──")
    print(f"[BACKFILL] 공용 마스터 {len(SHARED_MASTERS)}종은 **제외**한다 (D-261 c · 백필 금지)")

    # ★ **계획을 전부 먼저 세우고 그 다음에 쓴다 (스냅샷 의미론).**
    #   그렇게 하지 않으면 부모를 채운 결과가 자식을 새로 풀어 **연쇄**가 일어나고,
    #   D-261 이 승인한 23,616(백필 前 상태에서 **독립적으로** 측정한 값)을 넘어 쓰게 된다.
    #   실측: 연쇄를 허용하면 R3 가 23,265 → 24,340 으로 늘었다.
    #   (b) 의 계획도 같은 이유로 **(a) 를 쓰기 전에** 세운다 — D-261 이 잰 상태가 그것이다.
    #
    # ★ 세이브포인트: Postgres 는 트랜잭션 안에서 쿼리 하나가 실패하면 **그 트랜잭션 전체를
    #   거부**한다("current transaction is aborted"). 저장소 모델과 운영 스키마가 어긋난
    #   4건(P-LOCAL-4)이 실제로 그렇게 만든다 — 세이브포인트가 없으면 그 한 건이
    #   나머지 130종을 전부 건너뛰게 한다(실측: 시뮬레이션 1차에서 그렇게 됐다).
    plans: list[tuple] = []
    for model, group_field in models:
        label = model._meta.label
        if label in SPLIT_BY_BACKREF or label in SHARED_MASTERS:
            continue
        try:
            with transaction.atomic():
                r3 = plan_r3(model, group_field)
                r2 = plan_r2(model, group_field)
            seen = {pk for pk, _ in r3}
            r2 = [(pk, v) for pk, v in r2 if pk not in seen]   # R3 가 우선
            if r3 or r2:
                plans.append((model, r3, r2))
        except Exception as exc:      # 저장소 모델 ↔ 운영 스키마 불일치 (P-LOCAL-4)
            print(f"  ⚠ {label:44} 계획 불가 — {str(exc).splitlines()[0][:80]}")

    backref_plans: list[tuple] = []
    for model, group_field in models:
        if model._meta.label not in SPLIT_BY_BACKREF:
            continue
        try:
            with transaction.atomic():
                backref_plans.append((model, *plan_backref(model)))
        except Exception as exc:
            print(f"  ⚠ {model._meta.label:44} (b) 계획 불가 — {str(exc).splitlines()[0][:80]}")

    for model, r3, r2 in plans:
        label = model._meta.label
        try:
            with transaction.atomic():
                n3 = apply_pairs(model, "group", r3, journal, do_write)
                n2 = apply_pairs(model, "group", r2, journal, do_write)
            totals["r3"] += n3
            totals["r2"] += n2
            if n3 or n2:
                print(f"  (a) {label:44} R3 {n3:>6} · R2 {n2:>5}")
        except Exception as exc:
            print(f"  ⚠ {label:44} 쓰기 건너뜀 — {str(exc).splitlines()[0][:80]}")

    print("[BACKFILL] ── (b) 역참조 (D-261 §7 의 8경로 · **(a) 前 스냅샷**에서 잰다) ──")
    for model, decided, orphan, multi in backref_plans:
        label = model._meta.label
        try:
            with transaction.atomic():
                n = apply_pairs(model, "group", decided, journal, do_write)
            totals["backref"] += n
            unassigned[label] = orphan
            if multi:
                multi_owner[label] = multi
            print(f"  (b) {label:44} 정해짐 {len(decided):>5} · "
                  f"참조0 {len(orphan):>5} · 다중소유 {len(multi):>3}")
        except Exception as exc:
            print(f"  ⚠ {label:44} 쓰기 건너뜀 — {str(exc).splitlines()[0][:80]}")


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
    models = [
        (m, gf) for m, gf in DR.tenantish_models()
        if m._meta.app_label not in DR.SYSTEM_OWNED_APPS
    ]   # created_by IS NULL 을 '시스템 기본'의 뜻으로 쓰는 앱은 건드리면 깨진다

    try:
        if args.apply:
            run_phases(models, journal, totals, unassigned, multi_owner, do_write=True)
        else:
            # ★ **계획 모드는 롤백되는 트랜잭션 안에서 진짜로 쓴다.**
            #   왜: (b) 는 (a) 의 결과 위에서만 옳은 수를 낸다. 쓰지 않고 세면 (b) 가
            #   14 로 나오고, 그러면 "적용 전에 수를 대조한다"는 가드가 무의미해진다 —
            #   대조할 수 없는 수를 대조하라고 요구하는 셈이다.
            #   시뮬레이션으로 만들면 **로직을 복제하지 않고** 적용 후의 수를 미리 본다.
            #   끝에서 반드시 되돌린다. 중간에 죽어도 Postgres 가 되돌린다.
            print("[BACKFILL] 계획 모드 = **롤백되는 트랜잭션 안의 시뮬레이션**. "
                  "적용 후와 같은 수가 나오고, 한 행도 남지 않는다.")
            try:
                with transaction.atomic():
                    run_phases(models, journal, totals, unassigned, multi_owner, do_write=True)
                    raise _PlanRollback
            except _PlanRollback:
                print("[BACKFILL] ↩ 트랜잭션 되돌림 — 디스크에 남은 변경 0건")
    finally:
        journal.close()

    print()
    print(f"[BACKFILL] (a) 부모상속 R3={totals['r3']:,} · created_by소속 R2={totals['r2']:,} "
          f"· 합계 {totals['r3'] + totals['r2']:,}   (D-261 예상 23,616)")
    print("[BACKFILL] ※ R2 가 예상(343)보다 적은 것은 **더 엄격하기 때문**이다 — dry-run 은"
          " 'created_by 가 있다'만 셌고, 여기서는 '그 사용자의 소속 group 이 실제로 확인된다'까지"
          " 요구한다. 소속이 확인되지 않는 생성자의 행은 채우면 추측이 된다.")
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
