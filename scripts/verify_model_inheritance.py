#!/usr/bin/env python
"""D-295 강제 도구 — **신규 코드에서 `BaseModelWithGroup` 을 상속하지 않는다.**

    python scripts/verify_model_inheritance.py             # 판정 (허용목록 밖 상속이면 exit 1)
    python scripts/verify_model_inheritance.py --list      # 현재 상속 전수를 이름으로 출력
    python scripts/verify_model_inheritance.py --self-test # ★ 탐지기가 실제로 탐지하는가 (D-277)

무엇을 지키나 — **제거하지 않기로 한 결정을 제거 없이 지킨다**
--------------------------------------------------------------
D-295 의 상황은 이렇다:

  · `BaseModelWithGroup` 은 실행 중인 dj-core 에서 **DEPRECATED** 다. 필드를 하나도 더
    정의하지 않고, `BaseModel` 이 이미 `group` FK 와 `CustomManagerGroup` 을 갖는다.
  · 그런데 이 저장소의 **8개 앱**이 그것을 상속 중이고, dj-core 는 §0.4 금지구역(D-207)이다.
  · 8개 앱 동시 수정은 **이득 대비 위험이 크다.**

그래서 판정은 "제거 시도 금지 · 별칭 상태로 그대로 둔다" 였다. 문제는 그 다음이다 —
**아무것도 하지 않으면 새 코드가 계속 그것을 상속한다.** 오래된 것을 못 고치기로 했으면
적어도 **새 것이 늘지 않게** 해야 하고, 그것이 이 게이트다.

수가 아니라 **이름**으로 잠근다 (D-285 (2))
-------------------------------------------
D-295 가 못박았다: *"기존 8개는 허용 목록에 이름으로 등재 — 개수가 아니라 이름으로."*

개수로 잠그면 낡은 상속 하나가 지워질 때마다 **새 상속 하나가 들어올 자리**가 생긴다.
수는 그대로인데 빚은 바뀐다. `PUBLIC_BASELINE` 이 그렇게 무력해졌고(D-249),
`common/tenant_tripwire.py` 가 같은 이유로 이름 집합을 쓴다.

허용목록이 **줄어드는 것은 환영**이다 — 줄어도 실패하지 않는다.
없던 이름이 나타나는 것만 실패다.

무엇을 못 잡나 — 경계를 적는다 (D-277)
--------------------------------------
· AST 로 **선언된 기저 클래스 이름**만 본다. 중간 클래스를 하나 끼워 우회하면
  (`class Mine(SomethingThatInheritsIt)`) 이 판정기는 못 본다. 그 경우도 잡으려면
  Django 를 띄워 MRO 를 봐야 하고, 이 게이트는 pre-commit 에서 **Django 없이** 돈다.
  → 중간 클래스 자체가 허용목록에 등재되므로, 그 클래스가 새로 생기는 순간은 잡힌다.
· `import` 만 하고 상속하지 않는 파일은 대상이 아니다. 상속이 없으면 문제도 없다.
"""
from __future__ import annotations

import argparse
import ast
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 금지되는 기저 클래스. 이름 하나뿐이지만 목록으로 두는 이유는, 다음에 또
#: DEPRECATED 가 생기면 **여기 이름을 더하는 것으로 끝나게** 하기 위해서다.
DEPRECATED_BASES: frozenset[str] = frozenset({"BaseModelWithGroup"})

#: ★ 허용목록 — **2026-08-31 실측 전수 16건 / 8개 앱** (D-295 · D-285 ②).
#:
#: 형식은 `파일경로::클래스이름` 이다. 파일만 적으면 그 파일 안에서 새 상속이
#: 얼마든지 늘 수 있고, 클래스 이름만 적으면 다른 앱에서 같은 이름이 통과한다.
#:
#: ⚠ **여기에 이름을 더하는 것은 빚을 하나 더 지는 일이다.** 더하기 전에 물어라:
#:   `BaseModel` 로 충분하지 않은가. 실행 중인 dj-core 에서 그 둘의 격리 수준은
#:   **같다**(D-292 실측: BaseModel 이 이미 group FK + CustomManagerGroup 을 갖는다).
#:   그러므로 신규 모델의 정답은 언제나 `BaseModel` 이다.
ALLOWLIST: frozenset[str] = frozenset({
    "backend/checklist_setting/models.py::ChecklistSetting",
    "backend/common/measurable_model.py::MeasurableModelWithGroup",
    "backend/dashboard/models.py::Dashboard",
    "backend/dashboard/models.py::DashboardPanel",
    "backend/orders/models.py::ExternalOrderStatus",
    "backend/orders/models.py::OrderStatusMapping",
    "backend/partner/models.py::Partner",
    "backend/stream_monitors/models.py::StreamMonitor",
    "backend/stream_monitors/models.py::DetectionEvent",
    "backend/stream_monitors/models.py::NotificationRule",
    "backend/stream_monitors/models.py::DeliveryRecord",
    "backend/surveillance/models.py::SurveillanceProfileChecklist",
    "backend/surveillance/models.py::VideoAnalysis",
    "backend/terminals/models.py::TerminalType",
    "backend/terminals/models.py::Function",
    "backend/terminals/models.py::TerminalPurpose",
})

#: 훑지 않는 곳. 상속을 **선언하는** 자리가 아니다.
SKIP_PARTS: frozenset[str] = frozenset({
    "venv", ".venv", "migrations", "node_modules", "__pycache__",
})


def _base_names(node: ast.ClassDef) -> list[str]:
    """기저 클래스의 **마지막 이름 조각**들. `core.base.BaseModelWithGroup` → `BaseModelWithGroup`."""
    out: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            out.append(base.id)
        elif isinstance(base, ast.Attribute):
            out.append(base.attr)
    return out


def scan(root: Path = BACKEND) -> list[str]:
    """`파일경로::클래스이름` 전수. 정렬해 돌려준다 — diff 가 읽히게."""
    found: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if SKIP_PARTS & set(path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and (
                    DEPRECATED_BASES & set(_base_names(node))):
                found.append(f"{rel}::{node.name}")
    return sorted(found)


def judge(found: list[str]) -> tuple[list[str], list[str]]:
    """(허용목록 밖 신규, 사라진 기존). 사라진 것은 **실패가 아니다** — 환영이다."""
    current = set(found)
    return sorted(current - ALLOWLIST), sorted(ALLOWLIST - current)


# ---------------------------------------------------------------------------
# 양성 대조 — 탐지기가 실제로 탐지하는가 (D-277 · D-289)
# ---------------------------------------------------------------------------
_PLANT_CAUGHT = '''
from core.base import BaseModelWithGroup


class PlantedShouldBeCaught(BaseModelWithGroup):
    """허용목록에 없는 새 상속 — **잡혀야 한다.**"""
'''

_PLANT_CLEAN = '''
from core.base import BaseModel


class PlantedShouldPass(BaseModel):
    """신규 모델의 정답 — **안 잡혀야 한다.**"""


class AlsoFine:
    """상속과 무관한 평범한 클래스."""
'''


def self_test() -> int:
    """가짜 파일을 심어 판정기에 먹인다.

    양성만 보면 **늘 빨간불인 탐지기**도 통과한다. 그래서 음성도 함께 본다 —
    잡아야 할 것을 잡고, **잡지 말아야 할 것을 안 잡는가.**
    """
    rc = 0
    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp)
        (sandbox / "caught.py").write_text(_PLANT_CAUGHT, encoding="utf-8")
        (sandbox / "clean.py").write_text(_PLANT_CLEAN, encoding="utf-8")

        # scan() 은 ROOT 기준 상대경로를 만든다. 샌드박스는 ROOT 밖이므로 직접 판정한다.
        hits = []
        for path in sorted(sandbox.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and (
                        DEPRECATED_BASES & set(_base_names(node))):
                    hits.append(f"{path.name}::{node.name}")

        if "caught.py::PlantedShouldBeCaught" in hits:
            print("  [INH] 양성 대조 — 심은 신규 상속 1건을 잡았다. 판정기는 작동한다")
        else:
            print("  [INH] ✗ 양성 대조 실패 — 심은 위반을 못 잡았다. 이 게이트는 눈이 멀었다")
            rc = 1

        noise = [h for h in hits if h.startswith("clean.py")]
        if noise:
            print(f"  [INH] ✗ 음성 대조 실패 — BaseModel 상속을 위반으로 잡았다: {noise}")
            rc = 1
        else:
            print("  [INH] 음성 대조 — BaseModel 상속은 잡지 않는다. 늘 빨간불이 아니다")
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true",
                        help="현재 상속 전수를 이름으로 출력")
    parser.add_argument("--self-test", action="store_true",
                        help="탐지기 자체를 시험한다 (D-277)")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    found = scan()
    if args.list:
        print(f"[INH] BaseModelWithGroup 상속 전수 {len(found)}건 "
              f"(허용목록 {len(ALLOWLIST)}건)")
        for name in found:
            mark = "  " if name in ALLOWLIST else "★ "
            print(f"  {mark}{name}")
        return 0

    # ★ 모수가 0 이면 그것은 통과가 아니라 **열거기 고장**이다 (D-271 ②).
    #   허용목록에 16건이 등재돼 있는데 0건이 세어졌다면 훑는 경로가 틀린 것이다.
    if not found and ALLOWLIST:
        print("[INH] ✗ 전수 0건 — 허용목록에는 "
              f"{len(ALLOWLIST)}건이 있다. 훑는 경로가 틀렸다. "
              "못 센 것을 통과로 세지 않는다")
        return 1

    new, gone = judge(found)
    print(f"[INH] 상속 {len(found)}건 (술어=AST 기저클래스 이름, "
          f"모수=backend/**/*.py 전수, 허용목록={len(ALLOWLIST)})")
    if gone:
        print(f"[INH] 허용목록에서 사라진 것 {len(gone)}건 — **환영이다.** "
              "빚이 줄었다. 목록에서 지워도 좋다:")
        for name in gone:
            print(f"    - {name}")
    if new:
        print(f"[INH] ✗ 허용목록 밖 신규 상속 {len(new)}건")
        for name in new:
            print(f"    ★ {name}")
        print("\n  `BaseModelWithGroup` 은 DEPRECATED 다. 실행 중인 dj-core 에서 "
              "`BaseModel` 이 이미 group FK 와 CustomManagerGroup 을 갖고 있으므로 "
              "**격리 수준이 같다**(D-292 실측). 신규 모델은 `BaseModel` 을 상속하라.\n"
              "  그래도 상속해야 하는 이유가 있다면 이 스크립트의 ALLOWLIST 에 "
              "**이름으로** 등재하고, 그 커밋 메시지에 이유를 적어라 (D-295 · D-285 ②).")
        return 1

    print("[INH] 신규 위반 0건 — 기존 빚은 그대로 두고, 새 빚만 막는다 (D-295)")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    _n_py = sum(1 for _p in (ROOT / "backend").rglob("*.py"))
    gate_header(__file__, measured=("dj-core 를 **새로 상속하는 자리**가 늘었는가 — **분모 %s개**"
              "(`backend/` 파이썬 전수 · AST 로 기저클래스를 읽는다 · 지금 "
              "셌다). 래칫이다 — 초록은 「**새** 상속 0건」이지 "
              "「상속 0건」이 아니다 (D-295)" % (_n_py or "못 셌다")))
    raise SystemExit(main())
