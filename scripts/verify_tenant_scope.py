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
  · **신규 경로 트립와이어 — 정적 눈** (D-275 §5-1, 아래)

신규 경로 트립와이어 (D-275 §5-1) — **EXIT 승인의 유일한 필수 부대조건**
------------------------------------------------------------------------
WP-2 EXIT §5-1 의 미지는 이것이었다: 주인 없는 행은 매니저 수준에서 여전히 보이고,
근원은 저장소 밖이라 못 고친다. 지금 닫혀 있는 이유는 **라우트마다 문지기를 손으로 달았기
때문**이고, **문지기 없는 새 경로가 하나 생기면 그 순간 다시 샌다.**

그 문장을 사람의 기억이 아니라 게이트가 지키게 한다.

  판정기  `backend/common/tenant_tripwire.py` — **한 벌뿐이다**
  눈 둘   정적(여기, Django 불필요)  ·  런타임(`tests/test_route_tripwire.py`, 전수 열거)

여기가 정적 눈이다. 지시가 요구한 **런타임 전수 열거**는 시험 쪽이 한다 — pre-commit 은
Django 를 띄울 수 없기 때문이다. 정적 눈이 런타임 눈을 대신하는 것이 아니라,
**커밋 시점에 먼저 걸러 주는 앞눈**이다. 같은 것을 두 번 세는 것이 아니라 한 판정을
두 각도에서 먹인다 (원칙 1: 중복 0 은 **판정**의 중복을 금하는 것이다).

    python scripts/verify_tenant_scope.py --write-baseline   # 등재부 갱신(정적 구획만)
"""
from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
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
KERNEL_PUBLIC: dict[str, str] = {
    "backend/kernels/k1_event/services.py:record_detection":
        "테넌트 데이터를 **읽지 않는다.** 파이프라인이 부르는 쓰기 함수이고 호출자에 사람이 없다 "
        "— 요청자에게서 group 을 받을 수 없다. 대신 이벤트의 소유를 **스트림에서 물려받아 정한다** "
        "(_inherit_owner). 반환값은 id·bool 뿐이라 남의 테넌트 것이 실려 나갈 자리가 없다. "
        "시험 근거: tests/test_k1_event_kernel.py "
        "DedupSplitTest.test_a_different_stream_is_never_folded (다른 테넌트 스트림과 합쳐지지 않는다) · "
        "KernelTenantScopeTest.test_positive_control_own_event_is_found (소유가 실제로 붙는다)",
    "backend/kernels/k1_event/services.py:subscribe":
        "구현이 없다. 부르면 NotImplementedYet 을 던지고 **아무 데이터도 반환하지 않는다** "
        "(F-05 Webhook — W2-2 이후 별 티켓). 구현이 들어오는 커밋에서 이 등재를 지우고 "
        "문지기를 붙여야 한다 — 구독은 그 자체가 테넌트 자원이다. "
        "시험 근거: KernelPublicSurfaceTest.test_public_surface_matches_da04 (이름만 서 있음을 확인)",
}

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


# ---------------------------------------------------------------------------
# C-3.1 의 세 번째 통과 형태 — **문지기 호출** (P-K1-1 · 2026-08-28)
# ---------------------------------------------------------------------------
#: 판정기·문지기 목록을 여기서 다시 정의하지 않는다. 트립와이어가 라우트에 대해 쓰는
#: 것과 **같은 목록**을 쓴다 — 두 벌을 두면 "라우트에서는 문지기인데 커널에서는 아닌 것"이
#: 생기고, 그 어긋남은 아무도 못 본다.
_TRACE_CACHE: dict = {}


def _gatekeeper_names() -> set[str]:
    from common.tenant_tripwire import GATEKEEPER_CALLS
    return set(GATEKEEPER_CALLS)


def _gatekeepers_reached(path: Path, node: ast.AST) -> list[str]:
    """이 커널 함수의 호출 그래프가 **실제 문지기**에 닿는가.

    ★ 왜 `@tenant_scoped` 만으로 판정하지 않나 (P-K1-1)
      `tenant_scoped` 는 인자에서 `request` 를 찾고 못 찾으면 **그냥 통과시킨다**
      (`common/tenant_scope._find_request` → None → 검사 생략).
      커널 서비스 함수에는 `request` 가 없다. 붙이면 **표식만 남고 아무것도 안 막는다** —
      데코레이터 466/466 부착을 완결로 착각했던 착시 ①(D-249)과 똑같은 모양이다.

      그래서 통과 형태를 하나 **더한다.** 이것은 C-3.1 을 **무르게 하는 것이 아니라
      높이는 것**이다 (D-105 저촉 아님): 표식이 아니라 `common.tenant_filters` 의
      진짜 문지기가 호출 그래프에 있어야 인정한다.

      ⚠ C-3.1 문언과 다른 이행이므로 임의로 정하지 않고 `decisions_pending.yaml` 의
        **P-K1-1** 로 적재했다 (D-213). 판정이 나오면 이 함수와 그 항목을 함께 고친다.
    """
    from common import ast_call_trace as trace

    backend = BACKEND
    idx = _TRACE_CACHE.get("idx")
    if idx is None:
        idx = _TRACE_CACHE["idx"] = trace.Index(backend)
    t = idx.trace(node, path)
    return sorted(t.calls & _gatekeeper_names())


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

    n_scoped = n_public = n_guarded = 0
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
            guards = _gatekeepers_reached(path, node)
            if _decorator_names(node) & SCOPE_DECORATORS:
                n_scoped += 1
                if verbose:
                    print(f"  OK {key} — @tenant_scoped")
            elif guards:
                n_guarded += 1
                if verbose:
                    print(f"  G  {key} — 문지기: {', '.join(guards)}")
            elif key in KERNEL_PUBLIC:
                n_public += 1
                if verbose:
                    print(f"  P  {key} — PUBLIC: {KERNEL_PUBLIC[key]}")
            else:
                problems.append(
                    f"{key}: 커널 공개 함수인데 @tenant_scoped 도, 문지기 호출도, "
                    f"PUBLIC 등재도 없다 (C-3.1). "
                    f"인정하는 문지기: {', '.join(sorted(_gatekeeper_names()))}. "
                    f"스코프 없이 데이터를 반환하는 커널 함수는 반려한다")

    print(f"[SCOPE] 커널 공개 함수 — @tenant_scoped {n_scoped}개 · "
          f"문지기 호출 {n_guarded}개 · PUBLIC {n_public}개")
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


def _norm(s: str) -> str:
    s = s.strip("{}").lower().replace("_", "").replace("-", "")
    if s.endswith("id"):
        s = s[:-2]
    if s.endswith("s"):
        s = s[:-1]
    return s


def scan_no_route_models() -> list[str]:
    """`no_route` 로 등재된 모델에 **라우트가 생겼는지** 본다 (D-272).

    D-272 는 `no_route` 를 "면제가 아니라 등재"로 못 박고,
    **라우트가 추가되면 재검사되도록 게이트에 연결**하라고 했다. 여기가 그 연결이다.

    `no_route` 는 "닿을 수 없다"는 **그 시점의 사실**이다. 라우트 하나가 추가되면
    그 사실은 조용히 거짓이 되고, 아무도 그 모델을 다시 보지 않는다 —
    인구조사가 행 0 인 모델 25종을 못 보던 것과 같은 모양이다.

    Django 없이 판정한다: 커밋된 인구조사(`tenant_census.py`)와
    라우트 실측본(`openapi_routes.json`)만 읽는다. pre-commit 에서 돌아야 하기 때문이다.
    """
    import ast as _ast

    census = ROOT / "backend" / "tests" / "tenant_census.py"
    routes = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "openapi_routes.json"
    if not census.is_file() or not routes.is_file():
        return [f"인구조사·라우트 실측본을 못 찾았다 ({census.name} · {routes.name}) — "
                f"못 읽은 채 통과시키지 않는다"]

    tree = _ast.parse(census.read_text(encoding="utf-8"))
    table = None
    for node in _ast.walk(tree):
        tgt = None
        if isinstance(node, _ast.AnnAssign) and isinstance(node.target, _ast.Name):
            tgt = node.target.id
        elif isinstance(node, _ast.Assign) and isinstance(node.targets[0], _ast.Name):
            tgt = node.targets[0].id
        if tgt == "CENSUS" and isinstance(node.value, _ast.Dict):
            table = {k.value: _ast.literal_eval(v)
                     for k, v in zip(node.value.keys, node.value.values)}
    if table is None:
        return ["tenant_census.CENSUS 를 읽지 못했다 — 형태가 바뀌었다면 게이트도 함께 고쳐라"]

    import json as _json
    paths = list(_json.loads(routes.read_text(encoding="utf-8"))["routes"])
    problems = []
    n = 0
    for label, entry in table.items():
        if entry[1] != "no_route":
            continue
        n += 1
        model = label.split(".")[-1]
        for path in paths:
            parts = [s for s in path.split("/") if s]
            if any(_norm(s) == _norm(model) for s in parts):
                problems.append(
                    f"{label} 은 no_route 로 등재돼 있는데 라우트가 실재한다: {path} — "
                    f"인구조사를 다시 만들고 그 모델을 재검사하라 (D-272)")
                break
    print(f"[SCOPE] no_route 등재 {n}종 — 라우트 신설 여부 대조 (D-272)")
    return problems


def scan_route_tripwire(write_baseline: bool) -> list[str]:
    """★ 신규 경로 트립와이어 — **정적 눈** (D-275 §5-1).

    "라우트가 테넌트 모델을 만지는데 문지기가 하나도 없으면 unguarded" 를 판정하고,
    **등재부에 없던 unguarded 가 나타나면 실패**한다.

    판정기는 `backend/common/tenant_tripwire.py` 한 벌뿐이고, 여기는 그것에
    **정적 열거**를 먹인다. 런타임 전수 열거는 `tests/test_route_tripwire.py` 가 한다.

    ※ 왜 수가 아니라 이름인가: `PUBLIC_BASELINE` 처럼 수로 잠그면 낡은 라우트가 하나
      지워질 때마다 새 라우트 하나가 조용히 들어올 자리가 생긴다. 수는 그대로인데
      노출은 바뀐다. 그래서 이 게이트는 라우트 **하나하나의 이름**을 등재부에 적는다.
    """
    try:
        from common import tenant_tripwire as tw
    except Exception as exc:   # pragma: no cover - 판정기가 없으면 통과가 아니라 실패다
        return [f"트립와이어 판정기를 못 불렀다 ({exc}) — "
                f"backend/common/tenant_tripwire.py 가 있어야 한다. "
                f"판정기 없이 통과시키지 않는다"]

    rep = tw.compare(tw.Report("static", tw.scan_static()))
    print(rep.summary)
    for note in rep.notes:
        print("  · " + note)

    if write_baseline:
        import json
        path = tw.baseline_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = tw.build_baseline([rep], _today())
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + chr(10),
                       encoding="utf-8")
        os.replace(tmp, path)          # D-270 ① 원자 교체 — 원본을 truncate 하지 않는다
        print(f"[SCOPE] 등재부(정적 구획)를 다시 썼다: {path} — 커밋할 것. "
              f"런타임 구획은 건드리지 않았다")
        return []

    return rep.problems


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="함수별 상태를 전부 출력한다")
    ap.add_argument("--write-baseline", action="store_true",
                    help="트립와이어 등재부의 **정적 구획만** 다시 쓴다 (런타임 구획 보존)")
    args = ap.parse_args()

    print("[SCOPE] 커널 테넌트 스코프 대조 (C-3.1 · D-105 · K5)")
    problems = (scan_kernels(args.list) + scan_public_registry() + scan_no_route_models()
                + scan_route_tripwire(args.write_baseline))

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
    print("[SCOPE] ※ 트립와이어의 **런타임 전수 열거**는 backend/tests/test_route_tripwire.py 가 "
          "한다 (D-275 §5-1). 판정기는 한 벌이고 눈만 둘이다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
