#!/usr/bin/env python3
"""데모·목업 화면이 프로덕션 빌드로 새어나가지 않는지 정적으로 검사한다 (W0-4).

DoD 는 "프로덕션 빌드 산출물에 mockupDemoUi 청크가 없을 것"이다.
그 최종 판정은 `npm run build` 산출물 검사지만, 빌드는 사내 private 패키지
(rj-core / @gaion/gcs-fe, git+ssh://192.168.0.22)를 받을 수 있는 망에서만 돈다.

이 스크립트는 망과 무관하게 **번들에 남을 수밖에 없는 조건**을 잡는다.
정적 import 가 하나라도 남아 있으면 dead-code 제거가 불가능하므로,
빌드를 돌리지 않고도 DoD 위반을 확정할 수 있다.

검사 4종
  1. 데모 모듈을 정적 import 하는 소스가 있는가            → 있으면 청크 확정 잔존
  2. 데모 라우트가 __DEMO_ENABLED__ 분기 밖에서 등록되는가  → 있으면 프로덕션 노출
  3. vite.config.ts 에 __DEMO_ENABLED__ define 이 있는가    → 없으면 치환이 안 돼 제거 불가
  4. 데모 HTML 이 배포 경로(저장소 루트 / public)에 있는가  → 있으면 정적 서빙됨
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
SRC = FRONTEND / "src"

# 데모·목업 모듈 (경로 조각으로 판정)
DEMO_MODULES = (
    "features/mockupDemoUi",
    "features/setupData/DemoPage",
    "features/setupData/DemoUrlPage",
)

# 프로덕션에서 등록되면 안 되는 경로
DEMO_ROUTE_PATHS = (
    "/setup-demo-file",
    "/setup-demo-url",
    "/intergrated-dashboard",
    "/monitoring-dashboard",
    "/disabillity-dashboard",
)

# 라우트 경로를 '선언'만 하는 파일 (등록이 아니므로 검사 제외)
ROUTE_DECLARATION_FILES = ("src/services/API.ts",)

STATIC_IMPORT = re.compile(
    r"""^\s*import\s+(?!type\s)[^;]*?from\s*['"]([^'"]+)['"]""",
    re.M,
)
DYNAMIC_IMPORT = re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)""")

DEMO_HTML_LOCATIONS = (
    ROOT / "drone-monitoring.html",
    FRONTEND / "public" / "drone-monitoring.html",
    FRONTEND / "drone-monitoring.html",
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def is_demo_module(spec: str) -> bool:
    normalized = spec.replace("\\", "/").lstrip("./").replace("@/", "")
    return any(mod in normalized or mod.replace("features/", "") in normalized
               for mod in DEMO_MODULES if mod)


def iter_sources():
    if not SRC.is_dir():
        return
    for path in sorted(SRC.rglob("*")):
        if path.suffix in (".ts", ".tsx", ".js", ".jsx") and path.is_file():
            yield path


def check_static_imports(failures: list[str]) -> None:
    for path in iter_sources():
        if rel(path).startswith("frontend/src/features/mockupDemoUi"):
            continue  # 데모 모듈 내부끼리의 import 는 문제가 아니다
        if rel(path).startswith("frontend/src/features/setupData"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for spec in STATIC_IMPORT.findall(text):
            if is_demo_module(spec):
                failures.append(
                    f"{rel(path)} : 데모 모듈을 정적 import 한다 → '{spec}'\n"
                    f"      정적 import 는 dead-code 제거 대상이 아니다. "
                    f"__DEMO_ENABLED__ 분기 안의 dynamic import 로 바꿔야 한다."
                )


def check_route_registration(failures: list[str]) -> None:
    """데모 경로 문자열이 __DEMO_ENABLED__ 분기 밖에서 쓰이면 실패."""
    for path in iter_sources():
        relpath = rel(path)
        if any(relpath.endswith(decl) for decl in ROUTE_DECLARATION_FILES):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not any(p in text for p in DEMO_ROUTE_PATHS):
            continue
        if "__DEMO_ENABLED__" not in text:
            hits = [p for p in DEMO_ROUTE_PATHS if p in text]
            failures.append(
                f"{relpath} : 데모 경로가 플래그 분기 밖에서 참조된다 → {', '.join(hits)}"
            )


def check_vite_define(failures: list[str]) -> None:
    config = FRONTEND / "vite.config.ts"
    if not config.is_file():
        failures.append("frontend/vite.config.ts 가 없다")
        return
    text = config.read_text(encoding="utf-8", errors="replace")
    if "__DEMO_ENABLED__" not in text:
        failures.append(
            "frontend/vite.config.ts : __DEMO_ENABLED__ define 이 없다\n"
            "      define 이 없으면 빌드 시 리터럴 치환이 일어나지 않아 "
            "데모 분기가 번들에 그대로 남는다."
        )
        return
    if "VITE_ENABLE_DEMO" not in text:
        failures.append(
            "frontend/vite.config.ts : __DEMO_ENABLED__ 가 VITE_ENABLE_DEMO 와 "
            "연결되어 있지 않다"
        )


def check_demo_html(failures: list[str]) -> None:
    for path in DEMO_HTML_LOCATIONS:
        if path.is_file():
            failures.append(
                f"{rel(path)} : 데모 HTML 이 배포 경로에 있다 → docs/demo/ 로 옮긴다"
            )


def check_flag_branch_uses_dynamic_import(failures: list[str]) -> None:
    """플래그를 쓰는 파일에서 데모 모듈은 반드시 dynamic import 여야 한다."""
    found = False
    for path in iter_sources():
        if path.name.endswith(".d.ts"):
            continue  # 타입 선언 파일은 플래그를 '선언'만 한다
        text = path.read_text(encoding="utf-8", errors="replace")
        if "__DEMO_ENABLED__" not in text:
            continue
        found = True
        specs = [s for s in DYNAMIC_IMPORT.findall(text) if is_demo_module(s)]
        if not specs:
            failures.append(
                f"{rel(path)} : __DEMO_ENABLED__ 를 쓰지만 데모 모듈의 "
                f"dynamic import 가 없다"
            )
    if not found:
        failures.append(
            "__DEMO_ENABLED__ 를 사용하는 소스가 하나도 없다 — 게이트가 미적용 상태다"
        )


def main() -> int:
    failures: list[str] = []
    check_static_imports(failures)
    check_route_registration(failures)
    check_vite_define(failures)
    check_demo_html(failures)
    check_flag_branch_uses_dynamic_import(failures)

    if failures:
        print("FAIL: 데모·목업 격리 위반 (W0-4)", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        print(
            "\n  프로덕션 빌드에 미완성 데모 화면이 실리면 GS 인증에서 결함으로 처리된다.\n"
            "  데모는 VITE_ENABLE_DEMO=true 빌드에서만 살아 있어야 한다.",
            file=sys.stderr,
        )
        return 1

    print("PASS: 데모·목업 모듈이 프로덕션 빌드 경로에서 격리되어 있다 (W0-4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
