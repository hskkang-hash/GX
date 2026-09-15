#!/usr/bin/env python
"""데이터를 쓰는 스크립트가 **분류 등록부를 참조하는지** 판정한다 (D-270 ③).

왜 이 게이트가 있나
-------------------
2026-08-27, 백필 적용본이 `advanced_table.GridSetting`(479행) · `menu.Tab` 을 채우려 했다.
D-261 (c) 는 그것을 **금지**하고 있었다. 판정문은 있었다 — 없었던 것은 **게이트**다.
막은 것은 규칙이 아니라 시뮬레이션이었고, 시뮬레이션을 안 돌렸으면 그대로 나갔다.

  **문서에 적힌 판정은 지켜지지 않는다. 깨지면 실행이 멈추는 검사가 딸려야 한다.**

그래서 이 스크립트는 `scripts/` 와 관리 명령을 훑어 **데이터를 쓰는 것**을 찾아내고,
그것이 분류 등록부(`backend/tests/tenant_classification.py`)를 참조하지 않으면 **실패**한다.

작성 원칙 — D-264 계열
----------------------
"아는 것만 통과"가 아니라 **"모르는 것을 만나면 멈춘다"** 로 쓴다.

  · 파싱이 안 되는 파일 → **실패** (건너뛰지 않는다)
  · 쓰기인지 읽기인지 **판정할 수 없는 호출** → **쓰기로 센다.** 모호할 때 안전한 쪽은
    "아마 읽기겠지"가 아니라 "쓰기일 수 있다"다. 읽기임을 아는 사람은 `WRITE_AUDIT` 에
    사유와 함께 등재한다 — 면제가 아니라 **"사람이 봤고 이 근거로 읽기다"의 기록**이다
  · 새 쓰기 패턴이 등장하면 이 목록에 없으므로 **판정 불가 = 쓰기로 떨어져** 참조를 요구받는다

이미 있는 빚 — 래칫으로 잠근다 (2026-08-27 실측)
--------------------------------------------------
처음 돌렸더니 **쓰기 31개 중 등록부를 참조하는 것은 1개**(백필 적용본)뿐이었다.
그중에는 공용 마스터를 **통째로 지우는** 것도 있다 —
`init_days_of_week.py` 의 `DayOfWeek.objects.all().delete()`,
`init_anyang_data.py` 의 `OrderItemType.objects.all().delete()`(OrderItemType 은 SHARED_MASTERS 다).

여기서 두 갈래가 있었다:

  (가) 전부 실패시킨다 → 오늘부터 모든 커밋이 막힌다 → 게이트가 꺼진다 → **장식이 된다**
  (나) 조용히 통과시킨다 → 빚이 안 보인다 → **"봐서 괜찮았다"와 "안 봤다"가 구별되지 않는다**

둘 다 틀렸다. 그래서 `KNOWN_DEBT` **증가금지 래칫**을 쓴다 —
`tenant_classification.UNASSIGNED_BASELINE` 과 같은 장치다.

  · 래칫에 없는 파일이 참조 없이 쓰면 → **실패** (새 빚은 못 진다)
  · 래칫에 있는 파일이 **빚을 늘리면** → 실패
  · 빚이 줄면 통과하되 "래칫을 낮춰라"를 출력한다 (줄어드는 것은 환영이다)

**래칫은 갚을 빚의 목록이지 면제 목록이 아니다.** 전부 0 이 되는 것이 목표고,
그 사이에도 **새로 새는 것은 오늘부터 막힌다.**

이름 매칭 금지 (D-263)
----------------------
`.update(` 라는 **이름**으로 세지 않는다 — `dict.update()` 가 그 이름을 쓴다.
**수신자 사슬을 AST 로 따라가** 매니저·쿼리셋·커서에 닿는지 본다.
이름으로 세면 사전 갱신이 DB 쓰기로 잡히고, 그러면 게이트가 시끄러워지고,
시끄러운 게이트는 결국 꺼진다 — 꺼진 게이트는 장식이다.

    python scripts/verify_classification.py           # 판정 (위반 시 exit 1)
    python scripts/verify_classification.py --list    # 파일별 분류 출력
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "backend" / "tests" / "tenant_classification.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 훑는 곳. 앱 코드(views/models)는 대상이 아니다 — 그쪽은 테넌트 스코프 게이트(C-3.1)가 본다.
#: 여기서 보는 것은 **사람이 손으로 돌리는 일회성 쓰기**다. 그것이 오늘 사고를 냈다.
SCOPES = ["scripts/*.py", "backend/*/management/commands/*.py"]

#: 등록부를 참조한다고 인정하는 흔적. 어느 방식이든 **파일에 실제로 닿아야** 한다.
REGISTRY_MARKS = ("tenant_classification", "SHARED_MASTERS", "TENANT_UNASSIGNED")

#: ORM 쓰기 메서드.
ORM_WRITE = {
    "update", "bulk_update", "bulk_create", "create", "get_or_create",
    "update_or_create", "delete", "save",
}

#: 수신자 사슬에 이것이 있으면 매니저·쿼리셋이다 (= DB 를 만진다).
QUERYSET_MARKS = {
    "objects", "_base_manager", "_default_manager",
    "filter", "exclude", "all", "using", "select_for_update", "get_queryset",
}

#: 커서 실행. 인자의 SQL 을 봐야 읽기인지 쓰기인지 갈린다.
CURSOR_EXEC = {"execute", "executemany"}

#: SQL 쓰기 동사. 하나라도 있으면 쓰기다.
SQL_WRITE = ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "DROP", "ALTER",
             "CREATE", "GRANT", "REVOKE")

#: ★ "이건 DB 쓰기가 아니다"를 **사람이 보고** 기록한 곳. 사유 없는 등재는 거부한다.
#:   키는 `경로:줄번호`. 줄이 밀리면 등재가 풀려 다시 쓰기로 잡힌다 — 그래야 낡은 면제가 안 남는다.
WRITE_AUDIT: dict[str, str] = {
    "backend/common/management/commands/clear_cache.py:101":
        "redis_client.delete() — Redis 키 삭제다. DB 행이 아니라 캐시이고 분류 등록부의 대상이 아니다",
    "backend/common/management/commands/clear_cache.py:147":
        "redis_client.delete() — 같은 이유. 캐시 비우기이지 테넌트 데이터 쓰기가 아니다",

}

#: ★ 증가금지 래칫 — 2026-08-27 실측으로 잠근 **기존 빚**. 파일별 '등록부 미참조 쓰기' 건수다.
#:
#: ⚠ **면제 목록이 아니라 갚을 목록이다.** 여기 있는 파일은 공용 마스터를 구별하지 못한 채
#:   데이터를 쓴다. 새 빚은 오늘부터 막히고, 이 목록은 0 을 향해 줄여 간다.
#:   숫자를 **올리는 방향으로 고치는 것은 게이트를 끄는 것과 같다** — 고칠 것은 코드다.
#:
#: 처분은 P-W0-13-5 로 적재했다 (관리 명령 30개의 등록부 참조 배선 · 우선순위 판정 요청).
KNOWN_DEBT: dict[str, int] = {
    # scripts/ — 백필 계열. dry-run·rollback 은 적용본과 같은 판정을 딛고 서야 한다
    "scripts/backfill_owner_dryrun.py": 1,
    "scripts/backfill_owner_rollback.py": 1,
    "scripts/probe_tenant_isolation.py": 3,
    "scripts/role_split_local.py": 6,
    # ★ 공용 마스터를 통째로 지우는 것들 — 가장 먼저 갚아야 할 빚
    "backend/orders/management/commands/init_anyang_data.py": 6,
    "backend/terminals/management/commands/init_days_of_week.py": 3,
    "backend/orders/management/commands/init_status_mapping_data.py": 6,
    "backend/orders/management/commands/init_status_mapping_data_anyang.py": 6,
    "backend/operation_settings/management/commands/init_operation_settings.py": 2,
    "backend/operation_settings/management/commands/load_operation_settings_sample.py": 3,
    "backend/handover/management/commands/init_shifts.py": 1,
    # AdminConfig(SHARED_MASTERS) 를 만드는 것들
    "backend/dashboard/management/commands/create_dashboard_config.py": 1,
    "backend/delivery/management/commands/create_operation_config.py": 1,
    "backend/devices/management/commands/generate_unit_config.py": 2,
    "backend/devices/management/commands/migrate_unit_preferences.py": 1,
    "backend/orders/management/commands/create_delivery_inquiry_refresh_config.py": 2,
    "backend/surveillance/management/commands/init_surveillance_data.py": 2,
    "backend/terminals/management/commands/init_default_speed_wp.py": 2,
    # 나머지 테넌트 데이터 쓰기
    "backend/dashboard/management/commands/generate_delivery_dashboard.py": 10,
    "backend/delivery/management/commands/create_status_mappings.py": 2,
    "backend/delivery/management/commands/generate_delivery_operation_items.py": 1,
    "backend/delivery/management/commands/remove_status_mappings.py": 1,
    "backend/devices/management/commands/create_default_drone_status.py": 1,
    "backend/flight_log/management/commands/update_total_distance_old_records.py": 2,
    "backend/orders/management/commands/backfill_order_status_mapping_names.py": 1,
    "backend/orders/management/commands/create_default_delivery_options.py": 1,
    "backend/orders/management/commands/create_default_order_status.py": 1,
    "backend/orders/management/commands/create_order_history.py": 22,
    "backend/orders/management/commands/generate_delivery_process.py": 9,
    "backend/orders/management/commands/update_external_status_codes.py": 2,
    "backend/report_template/management/commands/create_default_template.py": 1,
    "backend/report_template/management/commands/manage_templates.py": 5,
    "backend/stream_monitors/management/commands/create_stream_monitors.py": 1,
    "backend/stream_monitors/management/commands/create_test_session.py": 2,
    "backend/terminals/management/commands/create_sample_terminals.py": 2,
}


class Scan(ast.NodeVisitor):
    """한 파일의 쓰기·판정불가를 모은다. 문자열 변수는 값을 따라가 SQL 을 읽는다."""

    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.writes: list[tuple[int, str]] = []
        self.unknown: list[tuple[int, str]] = []

    # 문자열 상수 대입을 기억한다 — `sql = f"...."; c.execute(sql)` 를 읽기 위해서다.
    def visit_Assign(self, node: ast.Assign) -> None:
        val = self._const_str(node.value)
        if val is not None:
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.strings[t.id] = val
        self.generic_visit(node)

    def _const_str(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):      # f-string — 상수 조각만 모아도 동사는 보인다
            return "".join(v.value for v in node.values
                           if isinstance(v, ast.Constant) and isinstance(v.value, str))
        if isinstance(node, ast.Name):
            return self.strings.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = self._const_str(node.left), self._const_str(node.right)
            if a is not None and b is not None:
                return a + b
        return None

    @staticmethod
    def _chain(node: ast.AST) -> list[str]:
        """수신자 사슬을 뿌리까지 따라간다 — 이름이 아니라 **닿는 곳**으로 판정하기 위해."""
        out: list[str] = []
        cur = node
        while True:
            if isinstance(cur, ast.Attribute):
                out.append(cur.attr)
                cur = cur.value
            elif isinstance(cur, ast.Call):
                cur = cur.func
            elif isinstance(cur, ast.Name):
                out.append(cur.id)
                break
            elif isinstance(cur, ast.Subscript):
                cur = cur.value
            else:
                break
        return list(reversed(out))

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            chain = self._chain(node.func.value)
            where = ".".join(chain + [attr])

            if attr in CURSOR_EXEC:
                sql = self._const_str(node.args[0]) if node.args else None
                if sql is None:
                    self.unknown.append((node.lineno, f"{where}() — SQL 을 상수로 못 읽었다"))
                elif any(v in sql.upper() for v in SQL_WRITE):
                    verb = next(v for v in SQL_WRITE if v in sql.upper())
                    self.writes.append((node.lineno, f"{where}() · SQL {verb}"))

            elif attr in ORM_WRITE:
                if set(chain) & QUERYSET_MARKS:
                    self.writes.append((node.lineno, f"{where}()"))
                elif attr in {"save", "delete"} and chain:
                    # 모델 인스턴스일 수도, 남의 객체(redis 등)일 수도 있다 — 우리가 정할 수 없다.
                    # ★ 모호하면 **쓰기로 센다.** 읽기임을 아는 사람이 WRITE_AUDIT 에 적는다.
                    self.unknown.append((node.lineno, f"{where}() — 수신자가 모델인지 확정 불가"))
                # dict.update() 등 매니저에 닿지 않는 것은 DB 쓰기가 아니다 (이름 매칭 금지)

        self.generic_visit(node)


def registry_self_check() -> list[str]:
    """등록부 자체가 성립하는지 — 참조를 강제해도 등록부가 엉망이면 소용없다."""
    problems: list[str] = []
    if not REGISTRY.is_file():
        return [f"분류 등록부가 없다: {REGISTRY} — 참조를 강제할 대상이 없다"]

    spec = importlib.util.spec_from_file_location("tenant_classification", REGISTRY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for name in ("SHARED_MASTERS", "TENANT_UNASSIGNED", "DEFERRED"):
        table = getattr(mod, name, None)
        if not isinstance(table, dict):
            problems.append(f"{name} 이 없거나 dict 가 아니다")
            continue
        for label, why in table.items():
            if not isinstance(why, str) or len(why.strip()) < 10:
                problems.append(f"{name}['{label}'] 에 근거가 없다 — 근거 없는 등재는 면제다")
            if "." not in label:
                problems.append(f"{name} 의 '{label}' 은 app.Model 꼴이 아니다")

    for label in sorted(mod.conflicts() if hasattr(mod, "conflicts") else set()):
        problems.append(f"'{label}' 이 두 곳 이상에 선언됐다 — 공용이면서 주인 없음일 수는 없다")

    base = getattr(mod, "UNASSIGNED_BASELINE", {})
    for label in getattr(mod, "TENANT_UNASSIGNED", {}):
        if label not in base:
            problems.append(
                f"TENANT_UNASSIGNED['{label}'] 에 증가금지 래칫(UNASSIGNED_BASELINE)이 없다")
    return problems


def targets() -> list[Path]:
    out: list[Path] = []
    for pat in SCOPES:
        out += sorted(ROOT.glob(pat))
    return [p for p in out if p.name != Path(__file__).name]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="파일별 분류를 전부 출력한다")
    args = ap.parse_args()

    print("[CLASSIFICATION] 데이터 쓰기 ↔ 분류 등록부 참조 대조 (D-270 ③)")
    problems = registry_self_check()
    for p in problems:
        print(f"  ✗ 등록부: {p}")

    files = targets()
    n_write = n_clean = 0
    debt_now: dict[str, int] = {}
    audited_seen: set[str] = set()

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        src = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            # 건너뛰지 않는다. 못 읽는 파일은 **판정하지 않은 파일**이고, 그것이 사각지대다.
            problems.append(f"{rel}: 파싱 실패 ({exc.msg} @{exc.lineno}) — 판정할 수 없다")
            print(f"  !! {rel}: 파싱 실패 — 판정 불가")
            continue

        scan = Scan()
        scan.visit(tree)

        # 판정 불가는 **쓰기로 센다.** WRITE_AUDIT 에 사유가 있는 줄만 뺀다.
        writes = list(scan.writes)
        for ln, what in scan.unknown:
            key = f"{rel}:{ln}"
            if key in WRITE_AUDIT:
                audited_seen.add(key)
            else:
                writes.append((ln, what + " → 모호하므로 쓰기로 센다"))
        writes.sort()

        if not writes:
            if args.list:
                print(f"    ·  {rel}: 쓰기 없음")
            continue

        n_write += 1
        refs = any(m in src for m in REGISTRY_MARKS)
        if refs:
            n_clean += 1
            if args.list:
                print(f"  OK {rel}: 쓰기 {len(writes)}건 · 등록부 참조 있음")
            continue

        debt_now[rel] = len(writes)
        allowed = KNOWN_DEBT.get(rel)
        if allowed is None:
            problems.append(
                f"{rel}: 데이터를 쓰는데 분류 등록부를 참조하지 않는다 (D-270 ③) — "
                f"쓰기 {len(writes)}건. 공용 마스터·미배정을 구별하지 못하는 쓰기다")
            print(f"  !! {rel}: 쓰기 {len(writes)}건 · 등록부 참조 **없음** — 래칫에 없는 새 빚")
            for ln, what in writes[:4]:
                print(f"      {ln:>4}: {what}")
        elif len(writes) > allowed:
            problems.append(
                f"{rel}: 등록부 미참조 쓰기가 {allowed} → {len(writes)} 로 **늘었다**. "
                f"래칫은 갚을 목록이지 늘릴 목록이 아니다 (D-270 ③)")
            print(f"  !! {rel}: 빚 {allowed} → {len(writes)} 증가")
        elif len(writes) < allowed:
            print(f"  ↓  {rel}: 빚 {allowed} → {len(writes)} 로 줄었다 — "
                  f"KNOWN_DEBT 를 {len(writes)} 로 낮춰라")
        elif args.list:
            print(f"  =  {rel}: 빚 {len(writes)}건 (래칫 유지)")

    # 낡은 등재는 지운다 — 남아 있으면 다음 사람이 그것을 근거로 읽는다
    for key, why in WRITE_AUDIT.items():
        rel = key.rsplit(":", 1)[0]
        if not (ROOT / rel).is_file():
            problems.append(f"WRITE_AUDIT 의 '{key}' 파일이 실재하지 않는다 — 낡은 면제는 지운다")
        elif key not in audited_seen:
            problems.append(
                f"WRITE_AUDIT 의 '{key}' 가 더는 그 줄에 없다 (줄이 밀렸거나 고쳐졌다) — "
                f"확인하고 지우거나 줄번호를 고쳐라")
        if len(why.strip()) < 10:
            problems.append(f"WRITE_AUDIT['{key}'] 에 사유가 없다")

    for rel in KNOWN_DEBT:
        if not (ROOT / rel).is_file():
            problems.append(f"KNOWN_DEBT 의 '{rel}' 이 실재하지 않는다 — 지운 파일의 빚은 지운다")
        elif rel not in debt_now:
            print(f"  ✓  {rel}: 빚을 갚았다 — KNOWN_DEBT 에서 지워라")

    total_debt = sum(debt_now.values())
    print()
    print(f"[CLASSIFICATION] 대상 {len(files)}개 · 쓰기 {n_write}개 "
          f"(등록부 참조 {n_clean}개) · WRITE_AUDIT {len(audited_seen)}줄")
    print(f"[CLASSIFICATION] 남은 빚 {len(debt_now)}개 파일 {total_debt}건 "
          f"— 래칫 상한 {sum(KNOWN_DEBT.values())}건 (P-W0-13-5)")
    if problems:
        print(f"[CLASSIFICATION] 위반 {len(problems)}건 — 멈춘다")
        for p in problems:
            print("  · " + p)
        return 1
    print("[CLASSIFICATION] 통과 — 새 빚 없음. 쓰는 것은 등록부를 참조하거나 래칫 안에 있다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(__file__)
    raise SystemExit(main())
