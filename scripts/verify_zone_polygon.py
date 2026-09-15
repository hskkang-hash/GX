#!/usr/bin/env python
"""D-299 의 폴리곤 잠금을 **저장소 밖에서** 잠근다 — SDN 의 `KERNEL_READY` 패턴 재사용.

    ZONE_POLYGON_READY = False
      · 사유(`ZONE_POLYGON_NOT_READY_REASON`)가 비면            → exit 1
      · True 로 올리면 **F-03 폴리곤 계약 AC 시험이 의무**가 된다 → 없으면 exit 1
      · 폴리곤 판정 구현(point-in-polygon)이 없는데 올리면       → exit 1

왜 상수 하나에 이만큼을 붙이나
------------------------------
계약 F-03 의 AC 는 *"지정 위험구역(**폴리곤**) 내 사람·차량 진입"* 이다. 지금 도는 것은
카메라 묶음이고, 그것은 **계약보다 약하다.** 약한 것을 약하다고 말하지 않으면 그 약함이
조용히 계약의 자리를 차지한다 — "구역 판정 됩니다"가 초록으로 나가고, 폴리곤은 영영
아무도 안 만든다.

그래서 약함을 **상수로 선언**하고, 그 선언에 값을 붙였다. 내리면 사유를 요구하고,
올리면 시험을 부른다. 어느 방향으로도 조용할 수 없다 (D-286 · D-299).

    python scripts/verify_zone_polygon.py             # 판정
    python scripts/verify_zone_polygon.py --self-test # 양성·음성 대조 (D-277)

Django 를 띄우지 않는다 — AST 로 읽는다. CI 게이트는 어디서든 돌아야 한다.
DB 쪽 대조(`geometry_status='ready'` 인 행이 있는데 상수가 False)는 여기서 못 한다.
그것은 `backend/tests/test_zone_judgment.py::test_no_ready_polygon_zone_without_the_flag`
가 한다 — **두 눈이 같은 규칙을 다른 자리에서** 본다.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZONES = ROOT / "backend" / "stream_monitors" / "services" / "zones.py"
MODELS = ROOT / "backend" / "stream_monitors" / "models.py"
TESTS = ROOT / "backend" / "tests" / "test_zone_judgment.py"

#: 상수를 True 로 올리는 순간 **의무가 되는** 시험 이름. 계약 F-03 의 AC 를 재는 자리다.
POLYGON_AC_TEST = "test_f03_polygon_contract_ac"

#: 폴리곤 판정의 구현. 상수가 True 인데 이 이름이 없으면 "상수만 올린 것"이다.
POLYGON_IMPL = "_point_in_polygon"

#: 사유의 최소 길이. 한 줄 변명이 아니라 **무엇이 없어서 못 하는지**를 적게 한다.
MIN_REASON = 60

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def literal(src: str, name: str, filename: str = "<src>"):
    """최상위 할당의 리터럴. import 하지 않는다 — Django 없이 돌아야 한다."""
    tree = ast.parse(src, filename=filename)
    for node in tree.body:
        targets = getattr(node, "targets", []) or (
            [node.target] if hasattr(node, "target") else [])
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name:
                try:
                    return ast.literal_eval(node.value)
                except ValueError:
                    return None
    return None


def check(zones_src: str, models_src: str, tests_src: str) -> list[str]:
    """(문제 목록). 셋을 **함께** 본다 — 상수·모델 열거·시험이 갈리면 어느 쪽도 못 믿는다."""
    problems: list[str] = []

    ready = literal(zones_src, "ZONE_POLYGON_READY")
    if ready is None:
        return ["ZONE_POLYGON_READY 상수가 없다 — 폴리곤 잠금이 통째로 사라졌다. "
                "지워진 잠금은 지워진 것이 보이지 않는다 (D-299)"]

    reason = literal(zones_src, "ZONE_POLYGON_NOT_READY_REASON")

    if ready is False:
        # ── 내렸으면 사유를 요구한다 (D-264) ────────────────────────────
        if not (isinstance(reason, str) and reason.strip()):
            problems.append(
                "ZONE_POLYGON_READY=False 인데 ZONE_POLYGON_NOT_READY_REASON 이 비었다 — "
                "사유 없는 미완성은 '아직' 인지 '영영' 인지 구별되지 않는다 (D-264)")
        elif len(reason.strip()) < MIN_REASON:
            problems.append(
                f"ZONE_POLYGON_NOT_READY_REASON 이 {len(reason.strip())}자다 — "
                f"한 줄 변명이 아니라 **무엇이 없어서 못 하는지**를 적는다 (최소 {MIN_REASON}자)")
    else:
        # ── 올렸으면 시험과 구현을 요구한다 ─────────────────────────────
        if f"def {POLYGON_AC_TEST}" not in tests_src:
            problems.append(
                f"ZONE_POLYGON_READY=True 인데 {POLYGON_AC_TEST} 가 없다 — "
                f"'됐다'는 말은 시험을 부른다. 계약 F-03 의 폴리곤 AC 를 재는 시험 없이 "
                f"이 상수를 올릴 수 없다 (D-299)")
        if POLYGON_IMPL not in zones_src:
            problems.append(
                f"ZONE_POLYGON_READY=True 인데 {POLYGON_IMPL} 구현이 없다 — "
                f"상수만 올리고 구현을 안 올린 상태다")

    # ── 모델 열거와 서비스가 같은 말을 하는가 ──────────────────────────
    for token in ("not_implemented", "ready"):
        if f'"{token}"' not in models_src and f"'{token}'" not in models_src:
            problems.append(
                f"Zone.GeometryStatus 에 '{token}' 이 없다 — 서비스가 그 값으로 판정하는데 "
                f"모델이 그 값을 모르면 판정은 영원히 거짓이다")

    # ── 판정 함수가 미구현을 **던지는가** (조용한 False 금지 · D-284) ──
    if "NotImplementedError" not in zones_src:
        problems.append(
            "zones.py 에 NotImplementedError 가 없다 — 폴리곤 판정이 조용히 False 를 "
            "돌려주면 '구역 밖이다'와 '판정 못 한다'가 같은 값이 되고, 그 순간 "
            "미구현이 정상 판정으로 위장한다 (D-284 · D-290)")

    return problems


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277 · D-289) — 심은 위반을 잡는가, 멀쩡한 것은 안 잡는가
# ═══════════════════════════════════════════════════════════════════════════
_MODELS_OK = 'class GeometryStatus:\n    NOT_IMPLEMENTED = "not_implemented"\n    READY = "ready"\n'
_TESTS_OK = f"def {POLYGON_AC_TEST}(self):\n    pass\n"
_TESTS_NONE = "def test_something_else(self):\n    pass\n"
_ZONES_LOCKED = (
    "ZONE_POLYGON_READY = False\n"
    'ZONE_POLYGON_NOT_READY_REASON = "'
    + ("폴리곤 판정을 구현하지 않았다. 좌표 표현과 좌표계가 미확정이므로 "
       "지금 고르면 그 선택이 곧 계약이 된다(D-280).") + '"\n'
    "raise NotImplementedError('폴리곤 판정 미구현')\n"
)
_ZONES_NO_REASON = 'ZONE_POLYGON_READY = False\nraise NotImplementedError("x")\n'
_ZONES_OPENED = (
    "ZONE_POLYGON_READY = True\n"
    f"def {POLYGON_IMPL}(point, polygon): return True\n"
    "raise NotImplementedError('x')\n"
)
_ZONES_OPENED_BARE = "ZONE_POLYGON_READY = True\nraise NotImplementedError('x')\n"


def self_test() -> int:
    cases = (
        ("잠근 채 사유가 있으면 안 잡는다", _ZONES_LOCKED, _TESTS_OK, False),
        # ★ **출생 표본** (D-310) — 이 도구를 만들게 한 바로 그 사례.
        #   "추정으로 열면 그 추측이 F-03 의 계약이 된다." 사유 없이 잠그면 그 약함이
        #   조용히 계약의 자리를 차지한다 — 아래 갈래가 그것을 잡는다.
        ("사유 없이 잠근 것을 잡는다", _ZONES_NO_REASON, _TESTS_OK, True),
        ("구현·시험을 갖추고 올린 것은 안 잡는다", _ZONES_OPENED, _TESTS_OK, False),
        ("시험 없이 올린 것을 잡는다", _ZONES_OPENED, _TESTS_NONE, True),
        ("구현 없이 상수만 올린 것을 잡는다", _ZONES_OPENED_BARE, _TESTS_OK, True),
    )
    bad = 0
    for label, zsrc, tsrc, should_fail in cases:
        problems = check(zsrc, _MODELS_OK, tsrc)
        ok = bool(problems) == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
            print(f"        실제: {problems}")
    if bad:
        print(f"[ZONE] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[ZONE] 자기시험 {len(cases)}건 통과 (양성 3 · 음성 2)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    for path, why in ((ZONES, "구역 판정 서비스"), (MODELS, "Zone 모델"),
                      (TESTS, "구역 판정 시험")):
        if not path.is_file():
            print(f"[ZONE] {why} 가 없다: {path.relative_to(ROOT)} — "
                  f"판정할 수 없으므로 멈춘다")
            return 1

    if self_test() != 0:                 # 판정 전에 판정기부터 (D-277)
        return 1

    zones_src = ZONES.read_text(encoding="utf-8")
    problems = check(zones_src, MODELS.read_text(encoding="utf-8"),
                     TESTS.read_text(encoding="utf-8"))

    ready = literal(zones_src, "ZONE_POLYGON_READY")
    print(f"[ZONE] ZONE_POLYGON_READY={ready} · "
          f"F-03 폴리곤 AC 시험 {'있음' if f'def {POLYGON_AC_TEST}' in TESTS.read_text(encoding='utf-8') else '없음'} · "
          f"카메라 묶음 판정은 가동 중")

    if problems:
        print("[ZONE] D-299 위반")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[ZONE] 통과 — 잠긴 것은 사유가 있고, 열린 것은 시험이 있다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(__file__)
    sys.exit(main())
