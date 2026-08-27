#!/usr/bin/env python
"""커널 공개 함수가 테넌트 스코프를 통과하는지 판정한다 (C-3.1 · D-105 · K5).

C-3.1 이 요구하는 것
--------------------
    "커널의 모든 공개 함수는 `@tenant_scoped()` 를 거치거나,
     거치지 않는 경우 PUBLIC 등록부에 **근거와 함께** 등재되어야 한다."

이 게이트는 오늘 **아무것도 막지 않는다.** `backend/kernels/` 가 아직 없기 때문이다
(커널은 WP-2 EXIT 후 K1 부터 선다). 그래도 지금 세우는 이유가 있다.

왜 커널이 서기 **전에** 세우나
------------------------------
오늘 두 번, 판정을 지킨 것은 게이트가 아니라 사람의 눈이었다.
그 둘의 공통점은 **판정이 먼저 있고 게이트가 나중에 왔다**는 것이다.
나중에 오는 게이트는 이미 쌓인 빚을 만나고, 그러면 래칫으로 잠그는 수밖에 없다 —
`verify_classification.py` 가 빚 113건을 안고 출발한 것이 바로 그 모양이다.

커널은 아직 한 줄도 없다. **여기서만은 빚 0 으로 시작할 수 있다.**
K1 의 첫 커밋부터 이 게이트가 서 있으면 래칫이 필요 없다.

    python scripts/verify_tenant_scope.py           # 판정 (위반 시 exit 1)
    python scripts/verify_tenant_scope.py --list    # 함수별 상태 출력

무엇을 보지 **않나** — 경계를 분명히 한다
------------------------------------------
라우트 단위의 스코프(현재 실재하는 것)는 이 게이트가 아니라
`backend/tests/test_route_tenant_scope.py` 가 본다. 그쪽은 Django 를 띄워
라우트를 열거해야 하므로 pre-commit 에서 돌릴 수 없다.

**같은 것을 두 곳에서 세지 않는다** (원칙 1: 중복 0). 여기서는
Django 없이 정적으로 판정할 수 있는 것만 본다:

  · 커널 공개 함수의 스코프 표식 (AST)
  · `PUBLIC_ROUTES` 전건에 사유가 있는가 (AST — 시험도 보지만 커밋 시점에 먼저 잡는다)
  · 면제 목록이 **늘지 않았는가** (PUBLIC_BASELINE 래칫)
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KERNEL_ROOT = ROOT / "backend" / "kernels"
APP_ROOT = ROOT / "backend" / "apps"
TENANT_SCOPE = ROOT / "backend" / "common" / "tenant_scope.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 스코프를 걸었다고 인정하는 데코레이터 이름.
SCOPE_DECORATORS = {"tenant_scoped"}

#: 커널 공개 함수의 면제 — `모듈:함수` → 사유. 사유 없는 등재는 거부한다.
#:
#: ⚠ **PUBLIC 은 검사 면제가 아니라 "공용임을 시험으로 증명한 것"이어야 한다** (D-261 c).
#:   여기 이름을 올리는 것은 "이 함수는 테넌트 데이터를 반환하지 않는다"는 **선언**이고,
#:   그 선언은 시험으로 뒷받침되어야 한다. 추측으로 올리지 않는다.
KERNEL_PUBLIC: dict[str, str] = {}

#: PUBLIC 라우트 면제의 증가금지 래칫. 오늘 실측 4건.
#:
#: 미분류(UNREVIEWED)를 줄이는 가장 쉬운 방법은 PUBLIC 으로 옮기는 것이다.
#: 그 길을 막지 않으면 **커버리지는 오르고 노출은 그대로 남는다.**
#: 늘리려면 대표 승인이 필요하다 — 이 수를 조용히 올리는 것이 그 승인을 건너뛰는 방법이다.
PUBLIC_BASELINE = 4

#: 커널이 아직 없어도 **이 게이트가 잠들지 않게** 한다.
#: 커널 디렉터리가 생기면 그때부터 판정 대상이 되고, 비어 있으면 그렇다고 말한다.
KERNEL_NAMES = ("k1_event", "k2_notify", "k3_dashboard", "k4_report",
                "k5_trust", "k6_feedback", "k7_context")


def _decorator_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    out: set[str] = set()
    for dec in fn.decorator_list:
        node = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
    return out


def scan_kernels(verbose: bool) -> list[str]:
    """커널 공개 함수를 훑는다. 커널이 없으면 그 사실을 말하고 통과한다."""
    problems: list[str] = []
    if not KERNEL_ROOT.is_dir():
        print(f"[SCOPE] 커널 디렉터리 없음 ({KERNEL_ROOT.relative_to(ROOT).as_posix()}) "
              "— 커널은 WP-2 EXIT 후 K1 부터 선다. 게이트는 그때 자동으로 물린다")
        return problems

    known = set(KERNEL_NAMES)
    seen_kernels = {d.name for d in KERNEL_ROOT.iterdir() if d.is_dir()
                    and not d.name.startswith("_")}
    # ★ 모르는 커널을 만나면 멈춘다 (D-264). 이름이 목록에 없으면 C-1 이 정한 커널이 아니다.
    for name in sorted(seen_kernels - known):
        problems.append(
            f"모르는 커널 디렉터리: backend/kernels/{name} — C-1 의 K1~K7 에 없다. "
            f"새 커널이면 KERNEL_NAMES 와 DA-04 §4 표를 **같은 커밋에서** 함께 고쳐라")

    n_scoped = n_public = 0
    for path in sorted(KERNEL_ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if "/tests/" in rel or path.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            problems.append(f"{rel}: 파싱 실패 ({exc.msg} @{exc.lineno}) — 판정할 수 없다")
            continue

        for node in tree.body:                       # 모듈 최상위 = 커널의 공개면
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue                             # 비공개는 커널 밖에서 못 부른다
            key = f"{rel}:{node.name}"
            if _decorator_names(node) & SCOPE_DECORATORS:
                n_scoped += 1
                if verbose:
                    print(f"  OK {key} — @tenant_scoped")
            elif key in KERNEL_PUBLIC:
                n_public += 1
                if verbose:
                    print(f"  P  {key} — PUBLIC: {KERNEL_PUBLIC[key]}")
            else:
                problems.append(
                    f"{key}: 커널 공개 함수인데 @tenant_scoped 도 없고 PUBLIC 등재도 없다 "
                    f"(C-3.1). 스코프 없이 데이터를 반환하는 커널 함수는 반려한다")

    print(f"[SCOPE] 커널 공개 함수 — 스코프 {n_scoped}개 · PUBLIC {n_public}개")
    return problems


def scan_public_registry() -> list[str]:
    """`PUBLIC_ROUTES` 를 **Django 없이** 정적으로 읽어 사유·증가를 본다."""
    problems: list[str] = []
    if not TENANT_SCOPE.is_file():
        return [f"면제 대장이 없다: {TENANT_SCOPE.relative_to(ROOT).as_posix()} — "
                f"없으면 무엇을 면제했는지 아무도 모른다"]

    tree = ast.parse(TENANT_SCOPE.read_text(encoding="utf-8"))
    routes: dict[str, str] | None = None
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target.id
        elif isinstance(node, ast.Assign) and node.targets and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
        if target != "PUBLIC_ROUTES" or not isinstance(node.value, ast.Dict):
            continue
        routes = {}
        for k, v in zip(node.value.keys, node.value.values):
            key = ast.unparse(k) if k is not None else "?"
            routes[key] = v.value if isinstance(v, ast.Constant) else ""

    if routes is None:
        # 이름이 바뀌었거나 형태가 달라졌다 — **못 찾았으면 통과가 아니라 실패**다.
        return ["PUBLIC_ROUTES 를 읽지 못했다 — 이름이나 형태가 바뀌었다면 "
                "이 게이트도 함께 고쳐야 한다. 못 읽은 채 통과시키지 않는다"]

    for key, reason in routes.items():
        if not isinstance(reason, str) or len(reason.strip()) < 5:
            problems.append(f"PUBLIC_ROUTES[{key}] 에 사유가 없다 — "
                            f"사유 없는 면제는 미분류와 구별되지 않는다")

    n = len(routes)
    print(f"[SCOPE] PUBLIC 라우트 면제 {n}건 (래칫 상한 {PUBLIC_BASELINE})")
    if n > PUBLIC_BASELINE:
        problems.append(
            f"PUBLIC 면제가 {PUBLIC_BASELINE} → {n} 로 **늘었다**. "
            f"면제 추가는 대표 승인 사항이다 — 미분류를 PUBLIC 으로 옮기면 "
            f"커버리지는 오르고 노출은 그대로 남는다")
    elif n < PUBLIC_BASELINE:
        print(f"[SCOPE] ↓ 면제가 {PUBLIC_BASELINE} → {n} 로 줄었다 — "
              f"PUBLIC_BASELINE 을 {n} 로 낮춰라")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="함수별 상태를 전부 출력한다")
    args = ap.parse_args()

    print("[SCOPE] 커널 테넌트 스코프 대조 (C-3.1 · D-105 · K5)")
    problems = scan_kernels(args.list) + scan_public_registry()

    for key, why in KERNEL_PUBLIC.items():
        if len(why.strip()) < 10:
            problems.append(f"KERNEL_PUBLIC['{key}'] 에 사유가 없다")

    print()
    if problems:
        print(f"[SCOPE] 위반 {len(problems)}건 — 멈춘다")
        for p in problems:
            print("  · " + p)
        return 1
    print("[SCOPE] 통과")
    print("[SCOPE] ※ 라우트 단위 스코프는 이 게이트가 아니라 "
          "backend/tests/test_route_tenant_scope.py 가 본다 (Django 필요). 중복해서 세지 않는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
