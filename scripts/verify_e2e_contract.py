#!/usr/bin/env python
"""E2E 등재부를 **저장소 밖에서** 한 번 더 잠근다 (D-291 · D-285 ②).

`backend/tests/e2e/test_e2e_contract.py` 가 이미 규약을 판정한다. 그런데 그 판정기는
**시험 안에 있다.** 시험 파일이 통째로 지워지면 판정기도 함께 사라지고, 남는 것은
"전건 통과" 뿐이다 — 게이트가 있다는 착시가 게이트가 없는 것보다 나쁘다
(WP-0 EXIT §6-1 `tickets.sha256` 이 같은 실패 모양이었다).

그래서 CI 게이트가 부를 수 있는 **저장소 수준 검사**를 따로 둔다:

    python scripts/verify_e2e_contract.py          # 판정 (어긋나면 exit 1)
    python scripts/verify_e2e_contract.py --list   # 시나리오·단계·해금 상태

Django 를 띄우지 않는다 — 파일이 있는가, 이름이 맞는가만 본다.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E2E_DIR = ROOT / "backend" / "tests" / "e2e"
CONTRACT = E2E_DIR / "e2e_contract.py"
CHECKER = E2E_DIR / "test_e2e_contract.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: D-291 이 이름 붙인 시나리오 3종. **여기가 저장소 밖의 정본이다.**
#: 늘리려면 이 집합과 `e2e_contract.SCENARIOS` 와 `test_e2e_contract.EXPECTED_CODES`
#: 셋을 같은 커밋에서 함께 고친다 — 세 곳이 갈리면 이 스크립트가 멈춘다.
EXPECTED_CODES = {"E2E-1", "E2E-2", "E2E-3"}

#: 규약 ①~④ 가 요구하는 시험 메서드 이름. `e2e_contract.REQUIRED_METHODS` 의 사본이며,
#: **사본인 것이 요점이다** — 한쪽만 고치면 아래 §대조에서 갈린다.
REQUIRED_METHODS = {
    "test_runs_on_migrated_database",
    "test_isolation_read_and_write_are_blocked",
    "test_positive_control_without_the_event",
    "test_degraded_variant_keeps_core_path",
}


def literal_from(path: Path, name: str):
    """모듈을 import 하지 않고 최상위 할당의 리터럴을 읽는다.

    import 하면 Django 설정이 필요하고, 그러면 이 스크립트는 컨테이너 밖에서
    못 돈다 — CI 게이트는 어디서든 돌아야 한다.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        targets = getattr(node, "targets", []) or ([node.target] if hasattr(node, "target") else [])
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name:
                try:
                    return ast.literal_eval(node.value)
                except ValueError:
                    return None
    return None


def scenario_codes() -> set[str]:
    """`SCENARIOS` 의 키. dict 리터럴이라 literal_eval 이 안 되므로 키만 훑는다."""
    tree = ast.parse(CONTRACT.read_text(encoding="utf-8"), filename=str(CONTRACT))
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign | ast.Assign):
            continue
        targets = getattr(node, "targets", []) or [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "SCENARIOS" for t in targets):
            continue
        if isinstance(node.value, ast.Dict):
            return {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    return set()


def scenario_modules() -> dict[str, str]:
    """시나리오 코드 → 모듈 경로. `module="tests.e2e.x"` 를 코드 순서대로 짝짓는다."""
    src = CONTRACT.read_text(encoding="utf-8")
    codes = re.findall(r'code="(E2E-\d+)"', src)
    modules = re.findall(r'module="([\w.]+)"', src)
    return dict(zip(codes, modules))


def required_methods_in_contract() -> set[str]:
    src = CONTRACT.read_text(encoding="utf-8")
    block = re.search(r"REQUIRED_METHODS[^=]*=\s*\{(.*?)\n\}", src, re.S)
    if not block:
        return set()
    return set(re.findall(r'"(test_[a-z0-9_]+)"', block.group(1)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    problems: list[str] = []

    # ── 판정기 자신이 살아 있는가 ────────────────────────────────────────
    for path, why in ((CONTRACT, "E2E 등재부"), (CHECKER, "규약 판정 시험")):
        if not path.exists():
            problems.append(f"{why} {path.relative_to(ROOT)} 가 없다 — 게이트가 사라졌다")
    if problems:
        for p in problems:
            print(f"  · {p}")
        print("[E2E] 실패")
        return 1

    # ── 이름 집합 (D-285 ②) ─────────────────────────────────────────────
    codes = scenario_codes()
    if codes != EXPECTED_CODES:
        problems.append(
            f"시나리오 이름 집합이 갈렸다 — 등재부={sorted(codes)} / "
            f"이 스크립트={sorted(EXPECTED_CODES)}")

    checker_codes = literal_from(CHECKER, "EXPECTED_CODES")
    if checker_codes is not None and set(checker_codes) != EXPECTED_CODES:
        problems.append(
            f"시험 쪽 EXPECTED_CODES 가 갈렸다 — {sorted(checker_codes)}")

    # ── 규약 메서드 이름의 사본 대조 ────────────────────────────────────
    in_contract = required_methods_in_contract()
    if in_contract and in_contract != REQUIRED_METHODS:
        problems.append(
            f"규약 메서드 이름이 갈렸다 — 등재부={sorted(in_contract)} / "
            f"이 스크립트={sorted(REQUIRED_METHODS)}")

    # ── 해금된 시나리오에 파일이 있는가 (파일 수준 판정) ────────────────
    #    해금 여부는 커널 패키지의 실재로 본다 — 등재부와 같은 기준이다.
    modules = scenario_modules()
    rows = []
    for code in sorted(codes):
        module = modules.get(code, "?")
        path = ROOT / "backend" / (module.replace(".", "/") + ".py")
        exists = path.exists()
        rows.append((code, module, exists))
        if exists:
            src = path.read_text(encoding="utf-8")
            missing = sorted(m for m in REQUIRED_METHODS if f"def {m}(" not in src)
            if missing:
                problems.append(f"{code}: 규약 메서드 누락 {missing}")
            for token in ("time.sleep(", "asyncio.sleep("):
                if token in src:
                    problems.append(f"{code}: 실시간 대기 {token} — 규약 ⑤ 위반")

    if args.list:
        for code, module, exists in rows:
            print(f"  {code}  {module:34} {'있음' if exists else '아직 없음'}")

    print(f"[E2E] 시나리오 {len(codes)}건 등재 · 시험 모듈 "
          f"{sum(1 for _, _, e in rows if e)}건 실재 · 규약 메서드 {len(REQUIRED_METHODS)}종")

    if problems:
        print("[E2E] 불일치 — 등재부와 시험이 갈렸다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[E2E] 대조 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
