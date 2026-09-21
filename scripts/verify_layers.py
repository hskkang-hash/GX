#!/usr/bin/env python
"""계층 위반 정적 검사 — **App(L4) 이 커널(L3) 내부를 직접 import 하면 멈춘다** (D-278).

무엇을 지키나 — 재사용 편의가 아니라 **IP 방어**다
---------------------------------------------------
DA-04 §1 이 못박은 커널 원칙 중 둘:

  1. 커널은 **L3 Platform 에만 산다.** App(L4)·어댑터(L2)는 커널 API 를 **소비만** 한다.
     → "본체=가이온 / 신규 연계=공동"(계약 8조3항)의 경계가 코드에 남아야 한다.
     커널 로직이 App 으로 새면 **그 경계가 코드에서 소멸한다.**
  4. 커널의 공개 면은 **서비스 함수**다. App 이 커널의 **모델을 직접 import 하지 않는다.**
     모델을 직접 만지면 커널을 바꿀 때 App 이 깨지고, 그러면 "한 번 개발"이 거짓이 된다.

이 두 문장은 지금까지 **문서에만** 있었다. 문서에만 있는 규칙은 지켜진 적이 없다 —
`verify_classification.py` 가 빚 113건을 안고 출발한 것이 그 증거다.

왜 K1 **전에** 세우나 (D-278)
-----------------------------
`backend/kernels/` 도 `backend/apps/` 도 **아직 한 줄도 없다.**
나중에 오는 게이트는 이미 쌓인 빚을 만나고, 그러면 래칫으로 잠그는 수밖에 없다.
**여기서만은 빚 0 으로 시작할 수 있다.** K1 의 첫 커밋부터 이 게이트가 서 있으면
래칫이 필요 없고, 위반은 **한 건도 태어나지 않는다.**

`verify_tenant_scope.py` 를 커널 0줄일 때 세운 것과 같은 계열이다.

판정 규칙
---------
    금지 ①  backend/apps/**      →  kernels.<k>.<내부모듈>     (모델·저장소 등 비공개면)
    금지 ②  backend/apps/**      →  kernels 를 통하지 않은 커널 내부 경로
    금지 ③  backend/kernels/**   →  apps.**                    (계층 역전)
    금지 ④  backend/apps/**      →  다른 App 의 내부            (App 간 결합)
    금지 ⑤  backend/kernels/**   →  adapters.**                (계층 역전 — 커널이 외부를 안다)
    금지 ⑥  backend/adapters/**  →  apps.**                    (계층 역전)

    허용    backend/apps/**      →  kernels.<k>                 (패키지 최상위 = 공개 면)
            backend/apps/**      →  kernels.<k>.{services,api,schemas,contracts}
            backend/kernels/**   →  common.**                   (공용 유틸은 L1)

사용법
------
    python scripts/verify_layers.py             # 판정 (위반 시 exit 1)
    python scripts/verify_layers.py --list      # 계층별 파일 수·import 를 전부 출력
    python scripts/verify_layers.py --self-test # ★ 탐지기가 실제로 탐지하는지 (D-277)

★ 양성 대조 의무 (D-277)
------------------------
이 게이트는 **오늘 아무 파일도 보지 않는다** (apps·kernels 가 없다). 그 상태에서 "위반 0"
을 출력하는 것은 초록이 아니라 **아무것도 재지 않은 것**이다. 그래서 `--self-test` 가
가짜 위반 파일을 만들어 판정기에 먹이고, **잡히는지·안 잡을 것은 안 잡는지**를 함께 본다.
`main()` 은 대상이 0건일 때 self-test 를 **자동으로** 돌린다 —
실패할 수 없는 시험은 시험이 아니다.
"""
from __future__ import annotations

import argparse
import ast
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 커널 패키지 이름 (C-1 · DA-04 §4). `verify_tenant_scope.KERNEL_NAMES` 와 같은 목록이다 —
#: 새 커널을 더할 때는 **두 곳과 DA-04 §4 표를 같은 커밋에서** 함께 고친다 (D-264).
KERNEL_NAMES = ("k1_event", "k2_notify", "k3_dashboard", "k4_report",
                "k5_trust", "k6_feedback", "k7_context")

#: 커널의 **공개 면**. 여기 있는 하위 모듈만 App 이 import 할 수 있다 (DA-04 §1-4).
#:
#: ⚠ 여기에 이름을 더하는 것은 "이 모듈은 커널의 계약이다"라는 **선언**이다.
#:   `models` 를 넣고 싶어지는 순간이 곧 커널이 새는 순간이므로, 넣지 않는다.
KERNEL_PUBLIC_MODULES = frozenset({"services", "api", "schemas", "contracts", "exceptions"})

APPS_ROOT = BACKEND / "apps"
KERNELS_ROOT = BACKEND / "kernels"
#: L2 어댑터. 2026-08-31 에 생겼다 — SDN 연결 표준(포트·수령 요건)이 첫 입주자다.
#: 어댑터가 늘어날 때 이 게이트가 함께 물리지 않으면, 커널이 어댑터를 부르는
#: 계층 역전이 조용히 들어온다 (계약 9조2항 '타 SDN 교체 가능' 이 그때 깨진다).
ADAPTERS_ROOT = BACKEND / "adapters"

_SKIP = {"__pycache__", "migrations", ".venv", "node_modules"}


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    imported: str
    rule: str
    why: str

    def render(self) -> str:
        return (f"{self.file}:{self.line}  import {self.imported}\n"
                f"      [{self.rule}] {self.why}")


def _imported_modules(tree: ast.Module) -> list[tuple[str, int]]:
    """`import a.b` · `from a.b import c` 를 `('a.b', lineno)` 로 낸다.

    `from a.b import c` 는 `a.b.c` 도 함께 낸다 — `from kernels.k1_event import models` 가
    `models` 를 이름으로 가져오는 형태이기 때문이다. 그것을 못 보면
    **가장 흔한 위반 형태를 놓친다.**
    """
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue                      # 상대 import 는 같은 패키지 안 — 계층을 넘지 않는다
            out.append((node.module, node.lineno))
            out += [(f"{node.module}.{a.name}", node.lineno) for a in node.names]
    return out


def _public_names(kernel: str) -> frozenset[str]:
    """커널의 **공개 면** — 그 패키지 `__init__.py` 의 `__all__` 을 AST 로 읽는다.

    import 하지 않는다: 이 게이트는 Django 없이 pre-commit 에서 돌아야 한다.
    읽지 못하면 **빈 집합**을 낸다 — 못 읽었는데 통과시키는 것이 D-271 이 경고한
    "모수 없는 초록" 이므로, 빈 집합은 곧 "전부 비공개면" 이라는 엄격한 판정이 된다.
    """
    init = KERNELS_ROOT / kernel / "__init__.py"
    if not init.is_file():
        return frozenset()
    try:
        tree = ast.parse(init.read_text(encoding="utf-8"))
    except SyntaxError:
        return frozenset()
    for node in tree.body:
        targets = getattr(node, "targets", []) or (
            [node.target] if hasattr(node, "target") else [])
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        if isinstance(node.value, ast.List | ast.Tuple):
            return frozenset(e.value for e in node.value.elts
                             if isinstance(e, ast.Constant) and isinstance(e.value, str))
    return frozenset()


def _is_private_kernel_path(kernel: str, name: str) -> bool:
    """`kernels.<kernel>.<name>` 이 **비공개면인가.**

    ★ 이 구별이 없으면 게이트가 정확히 반대로 판정한다 (2026-08-31 실측).

      `_imported_modules` 는 `from kernels.k1_event import record_detection` 을
      `kernels.k1_event.record_detection` 으로도 낸다 — `from kernels.k1_event import
      models` 를 잡기 위해서다. 그 확장은 옳다. 그런데 판정 쪽이 **이름과 모듈**을
      구별하지 못하면 DA-04 §1-4 가 권장한 바로 그 사용법이 금지①로 잡힌다.

      실제로 그랬다: `backend/apps/` 가 처음 생긴 날 `from kernels.k4_report import
      build_context, render` 가 위반 3건으로 잡혔다. 그전까지 드러나지 않은 것은
      대상 파일이 0건이었기 때문이다 — 재지 않는 게이트는 틀려도 초록이다.

    술어는 **커널이 스스로 선언한 공개 면**이다 — 그 패키지의 `__all__`.
    거기 있으면 공개 면에서 나온 이름이고, 없으면 비공개면이다.
    파일이 실재하는지로 묻지 않는 이유: `kernels.k1_event.models` 는 **파일이 없어도**
    막아야 한다. K1 이 모델을 갖지 않는 것은 설계이고, 그 이름을 가져오려는 시도
    자체가 계층을 넘으려는 시도이기 때문이다.
    """
    return name not in _public_names(kernel)


def judge_import(layer: str, owner: str, module: str) -> tuple[str, str] | None:
    """import 하나를 판정한다. 위반이면 `(규칙, 사유)`, 아니면 `None`.

    **순수 함수다** — `--self-test` 가 겨누는 과녁이 여기다 (D-277).
    `layer` 는 `"app"` / `"kernel"`, `owner` 는 그 파일이 속한 앱·커널 이름이다.
    """
    parts = module.split(".")
    head = parts[0]

    if layer == "app":
        if head == "kernels":
            if len(parts) < 2:
                return ("금지②", "커널 패키지를 통째로 가져온다 — 어느 커널의 무엇을 쓰는지가 "
                                 "코드에 안 남는다. `from kernels.k1_event import ...` 로 적어라")
            if len(parts) == 2:
                return None                   # kernels.k1_event — 공개 면 최상위. 허용
            sub = parts[2]
            if sub in KERNEL_PUBLIC_MODULES:
                return None
            if not _is_private_kernel_path(parts[1], sub):
                # 모듈이 아니라 **공개 면의 이름**이다 — `from kernels.k1_event import
                # record_detection`. 이것이 DA-04 §1-4 가 정한 올바른 사용법이다.
                return None
            return ("금지①", f"커널 비공개 모듈 `{parts[1]}.{sub}` 를 직접 가져온다. "
                              f"App 이 만질 수 있는 것은 서비스 함수뿐이다 (DA-04 §1-4) — "
                              f"공개 면: {', '.join(sorted(KERNEL_PUBLIC_MODULES))}. "
                              f"커널 로직이 App 으로 새면 계약 8조3항의 경계가 코드에서 사라진다")
        if head in KERNEL_NAMES:
            return ("금지②", f"커널 `{head}` 을 `kernels.` 를 거치지 않고 가져온다 — "
                              f"경로를 우회해도 계층은 그대로다")
        if head == "apps" and len(parts) >= 2 and parts[1] != owner:
            other = parts[1]
            if len(parts) > 2 and parts[2] not in KERNEL_PUBLIC_MODULES:
                return ("금지④", f"다른 App `{other}` 의 내부(`{parts[2]}`)를 직접 가져온다. "
                                  f"App 끼리는 커널을 통해 만난다 — 직접 결합하면 "
                                  f"App 하나를 떼어 팔 수 없다")
        return None

    if layer == "kernel":
        if head == "apps":
            return ("금지③", "커널(L3)이 App(L4)을 가져온다 — **계층 역전**이다. "
                             "커널은 App 을 몰라야 한다. 알면 그 커널은 그 App 전용이 되고, "
                             "재사용을 전제로 한 커널이라는 말이 거짓이 된다")
        if head == "adapters":
            return ("금지⑤", "커널(L3)이 어댑터(L2)를 가져온다 — **계층 역전**이다. "
                             "커널이 특정 외부 시스템을 알면 그 시스템을 갈아끼울 수 없고, "
                             "계약 9조2항의 '타 SDN 교체 가능' 이 코드에서 거짓이 된다. "
                             "어댑터를 부르는 것은 App(L4) 이다")
        return None

    if layer == "adapter":
        # 어댑터(L2)는 바깥 세계를 안다. 그것이 어댑터의 일이다.
        # 금지되는 것은 **안쪽으로 너무 깊이 들어가는 것**뿐이다.
        if head == "apps":
            return ("금지⑥", "어댑터(L2)가 App(L4)을 가져온다 — 계층 역전이다. "
                             "어댑터는 자기를 부르는 쪽을 몰라야 한다")
        if (head == "kernels" and len(parts) > 2
                and parts[2] not in KERNEL_PUBLIC_MODULES
                and _is_private_kernel_path(parts[1], parts[2])):
            return ("금지①", f"어댑터가 커널 비공개 모듈 `{parts[1]}.{parts[2]}` 를 직접 "
                              f"가져온다. 어댑터도 커널의 **공개 면만** 만진다 (DA-04 §1-1: "
                              f"'App(L4)·어댑터(L2)는 커널 API 를 소비만 한다')")
        return None

    return None


def iter_layer_files() -> list[tuple[str, str, Path]]:
    """`(layer, owner, path)` — 판정 대상 파일 전수."""
    out: list[tuple[str, str, Path]] = []
    for layer, root in (("app", APPS_ROOT), ("kernel", KERNELS_ROOT),
                        ("adapter", ADAPTERS_ROOT)):
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.py")):
            if set(p.parts) & _SKIP:
                continue
            rel = p.relative_to(root)
            owner = rel.parts[0] if len(rel.parts) > 1 else rel.stem
            out.append((layer, owner, p))
    return out


def scan(verbose: bool = False) -> tuple[list[Violation], int]:
    """전수 판정. `(위반, 본 파일 수)`."""
    violations: list[Violation] = []
    files = iter_layer_files()
    for layer, owner, path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            # 못 읽은 것을 통과로 세지 않는다.
            violations.append(Violation(rel, exc.lineno or 0, "?", "파싱실패",
                                        f"{exc.msg} — 판정할 수 없다"))
            continue
        # `from a.b import c` 는 `a.b` 와 `a.b.c` 를 함께 내므로 한 줄이 두 번 잡힌다.
        # 같은 (줄, 규칙)이면 **짧은 쪽만** 남긴다 — 같은 위반을 두 번 세면 수가 부풀고,
        # 부푼 수는 고쳐야 할 양을 잘못 알려 준다.
        seen: dict[tuple[int, str], Violation] = {}
        for module, lineno in _imported_modules(tree):
            hit = judge_import(layer, owner, module)
            if verbose:
                mark = "!!" if hit else "  "
                print(f"  {mark} [{layer}/{owner}] {rel}:{lineno} {module}")
            if not hit:
                continue
            k = (lineno, hit[0])
            if k not in seen or len(module) < len(seen[k].imported):
                seen[k] = Violation(rel, lineno, module, hit[0], hit[1])
        violations += [seen[k] for k in sorted(seen)]
    return violations, len(files)


# ---------------------------------------------------------------------------
# ★ 양성 대조 — 탐지기가 실제로 탐지하는가 (D-277)
# ---------------------------------------------------------------------------
#: `(layer, owner, import, 잡혀야 하는가, 설명)`
SELF_TEST_CASES = [
    ("app", "dsm", "kernels.k1_event.models", True,
     "App 이 커널 모델을 직접 가져온다 — 이 게이트가 세워진 이유 그 자체"),
    ("app", "dsm", "kernels.k1_event.repositories", True,
     "저장소 계층도 비공개면이다"),
    ("app", "dsm", "kernels", True,
     "커널 패키지 통째 — 무엇을 쓰는지 코드에 안 남는다"),
    ("app", "dsm", "k1_event.models", True,
     "`kernels.` 를 우회해도 계층은 그대로다"),
    ("app", "dsm", "apps.other_app.models", True,
     "App 끼리 내부로 직접 결합"),
    ("kernel", "k1_event", "apps.dsm.services", True,
     "커널이 App 을 가져온다 — 계층 역전"),
    # ↓ **안 잡혀야 하는 것들.** 늘 빨간불인 탐지기는 늘 초록인 탐지기와 똑같이 쓸모없다.
    ("app", "dsm", "kernels.k1_event", False, "커널 공개 면 최상위 — 허용"),
    # ★ 이름 vs 모듈 (2026-08-31). `from kernels.k1_event import record_detection` 은
    #   `_imported_modules` 가 `kernels.k1_event.record_detection` 으로도 낸다.
    #   그것을 모듈로 오인하면 **권장 사용법이 위반으로 잡힌다** — 실제로 그랬다.
    ("app", "dsm", "kernels.k1_event.record_detection", False,
     "모듈이 아니라 이름이다 — 공개 면에서 가져온 서비스 함수. DA-04 §1-4 의 권장 사용법"),
    ("app", "dsm", "kernels.k4_report.build_context", False,
     "같은 이유 — 이름이지 모듈이 아니다"),
    ("app", "dsm", "kernels.k3_dashboard.presets", True,
     "`__all__` 에 없는 이름 — 비공개 모듈이다(kernels/k3_dashboard/presets.py 실재)"),
    ("app", "dsm", "kernels.k3_dashboard.FIVE_STATES", False,
     "`__all__` 에 있는 상수 — 공개 면이다. 화면·시험·검수가 같은 값을 봐야 한다(D-212)"),
    ("app", "dsm", "kernels.k1_event.services", False, "서비스 함수 — 정확히 이것이 공개 면이다"),
    ("app", "dsm", "kernels.k2_notify.schemas", False, "스키마는 계약의 일부 — 허용"),
    ("app", "dsm", "apps.dsm.internal", False, "자기 App 내부 — 계층을 넘지 않는다"),
    ("app", "dsm", "common.tenant_filters", False, "공용 유틸(L1) — 허용"),
    ("kernel", "k1_event", "common.tenant_scope", False, "커널이 공용 유틸을 쓰는 것은 정상"),
    # L2 어댑터 (2026-08-31 신설)
    ("kernel", "k1_event", "adapters.sdn", True,
     "커널이 어댑터를 안다 — 계약 9조2항 '타 SDN 교체 가능' 이 코드에서 거짓이 된다"),
    ("adapter", "sdn", "apps.dsm.services", True,
     "어댑터가 자기를 부르는 쪽을 안다 — 계층 역전"),
    ("adapter", "sdn", "kernels.k1_event.models", True,
     "어댑터도 커널 공개 면만 만진다 (DA-04 §1-1)"),
    ("adapter", "sdn", "kernels.k1_event", False, "커널 공개 면 — 어댑터도 소비할 수 있다"),
    ("adapter", "sdn", "requests", False, "어댑터가 바깥 세계를 아는 것은 어댑터의 일이다"),
    ("app", "dsm", "adapters.sdn", False, "App 이 어댑터를 부른다 — 이것이 정상 방향이다"),
    ("kernel", "k1_event", "kernels.k2_notify.services", False,
     "커널끼리 공개 면으로 만나는 것은 막지 않는다 — 막을 근거가 DA-04 에 없다"),
]


def self_test(verbose: bool = True) -> list[str]:
    """가짜 위반을 심어 판정기가 **정말 잡는지** 본다. 실패하면 그 목록을 낸다.

    ★ 이 게이트는 오늘 대상 파일이 0건이다. 그 상태의 "위반 0" 은 초록이 아니라
      **아무것도 재지 않은 것**이다 — 착시 4형 ④(탐지기 자체 · D-277).
      그래서 판정기 자체를 시험한다.
    """
    fails: list[str] = []
    for layer, owner, module, should_catch, why in SELF_TEST_CASES:
        got = judge_import(layer, owner, module)
        caught = got is not None
        ok = caught == should_catch
        if verbose:
            mark = "OK  " if ok else "FAIL"
            verdict = got[0] if got else "허용"
            print(f"  {mark} [{layer}/{owner}] {module:38} → {verdict:8} ({why})")
        if not ok:
            fails.append(
                f"[{layer}/{owner}] {module} — "
                f"{'잡아야 하는데 통과시켰다' if should_catch else '잡으면 안 되는데 잡았다'} ({why})"
            )

    # 파일 단위 경로도 한 번 실제로 태운다 — `judge_import` 만 맞고 파서가 틀릴 수 있다.
    fails += _self_test_end_to_end(verbose)
    return fails


def _self_test_end_to_end(verbose: bool) -> list[str]:
    """진짜 파일을 만들어 `_imported_modules` → `judge_import` 전 경로를 태운다."""
    src = (
        "from kernels.k1_event import models          # 잡혀야 한다\n"
        "from kernels.k1_event import services        # 통과해야 한다\n"
        "import kernels.k3_dashboard.repositories     # 잡혀야 한다\n"
        "from common.tenant_filters import assert_scoped\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "probe.py"
        p.write_text(src, encoding="utf-8")
        hits = [m for m, _ in _imported_modules(ast.parse(p.read_text(encoding="utf-8")))
                if judge_import("app", "dsm", m)]
    want = {"kernels.k1_event.models", "kernels.k3_dashboard.repositories"}
    got = set(hits)
    if verbose:
        print(f"  {'OK  ' if got == want else 'FAIL'} 파일 경로 대조 — 잡은 것 {sorted(got)}")
    if got != want:
        return [f"파일 경로 대조 실패: 기대 {sorted(want)} · 실제 {sorted(got)}"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="파일별 import 를 전부 출력한다")
    ap.add_argument("--self-test", action="store_true",
                    help="판정기가 실제로 탐지하는지 본다 (D-277 양성 대조)")
    args = ap.parse_args()

    print("[LAYER] 계층 위반 정적 검사 (D-278 · DA-04 §1) — "
          "App(L4) 은 커널(L3) 의 공개 면만 쓴다")

    violations, n_files = scan(args.list)
    print(f"[LAYER] 대상 {n_files}개 파일 "
          f"(apps {'있음' if APPS_ROOT.is_dir() else '없음'} · "
          f"kernels {'있음' if KERNELS_ROOT.is_dir() else '없음'} · "
          f"adapters {'있음' if ADAPTERS_ROOT.is_dir() else '없음'})")

    # ★ 대상이 0건이면 "위반 0" 은 초록이 아니다. 그때는 **반드시** 판정기를 시험한다.
    run_self = args.self_test or n_files == 0
    self_fails: list[str] = []
    if run_self:
        if n_files == 0:
            print("[LAYER] 대상 0건 — 그 상태의 '위반 0' 은 재지 않은 것이다. "
                  "판정기 자체를 시험한다 (D-277)")
        print(f"[LAYER] 양성/음성 대조 {len(SELF_TEST_CASES)}건 + 파일 경로 1건")
        self_fails = self_test()

    print()
    if violations:
        print(f"[LAYER] 계층 위반 {len(violations)}건 — 멈춘다")
        for v in violations:
            print("  · " + v.render())
        print("\n  왜 막나: 커널 로직이 App 으로 새면 "
              "'본체=가이온 / 신규 연계=공동'(계약 8조3항)의 경계가 코드에서 소멸한다. "
              "재사용 편의가 아니라 IP 방어다 (DA-04 §1-1)")
        return 1
    if self_fails:
        print(f"[LAYER] ★ 판정기 자체가 고장났다 — 대조 {len(self_fails)}건 실패")
        for f in self_fails:
            print("  · " + f)
        print("\n  이 상태의 '위반 0' 은 초록이 아니라 눈이 감긴 것이다 (D-277 착시 ④)")
        return 1

    print("[LAYER] 통과 — 계층 위반 0건")
    if n_files == 0:
        print("[LAYER] ※ apps·kernels 가 아직 없다. K1 이 서는 순간부터 이 게이트가 물린다 — "
              "**빚 0 으로 시작한다** (D-278)")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    _n_layer = len(iter_layer_files())
    #: ★ [P-204 · 턴 Z · Q] **마지막 줄은 분모다.** 이 수는 **지금 센 것**이다 —
    #:   손으로 적은 수는 분모가 아니고, 분모를 안 말한 `exit 0` 은
    #:   「이 게이트가 통과」가 아니라 「이 호출이 끝났다」일 뿐이다.
    gate_header(__file__, measured=(
        "App(L4) 이 커널(L3) **내부**를 import 하는지 파일마다 본다 — "
        "**분모 %d**(apps·kernels·adapters 의 .py 전수 · 지금 셌다)" % _n_layer))
    raise SystemExit(main())
