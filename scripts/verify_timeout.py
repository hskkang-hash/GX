#!/usr/bin/env python
"""타임아웃 없는 외부 호출 게이트 (규약 §2 · C-3.3).

★ **이 파일에는 판정 로직이 없다.** `scan_request_timeouts.py` 의 AST 엔진을 그대로 부른다.

왜 로직을 옮기지 않았나 — 원칙 1: 중복 0
-----------------------------------------
규약 §2 는 `verify_timeout.py` 를 "신설"로 적었다. 그런데 이미
`scan_request_timeouts.py`(W0-17)가 **AST 실측**으로 같은 일을 하고 있었고,
그 파일에는 실측 이력(면제 3건의 사유·"49건은 grep 추정치였다"는 정정)이 붙어 있다.

여기에 판정 로직을 새로 쓰면 **같은 것을 세는 스크립트가 둘**이 된다.
둘은 언젠가 다른 수를 말하고, 그때 어느 쪽이 진실인지 알 수 없게 된다 —
D-227(manifest 유실)이 만든 상태이고, 백필 적용본이 dry-run 을 `import` 한 이유이기도 하다.

그래서 **엔진은 하나로 두고 넓혔다**(`requests` → 외부 의존 전 계열),
이 파일은 규약이 이름 붙인 게이트 진입점으로만 둔다.

    python scripts/verify_timeout.py           # 판정 (미조치 있으면 exit 1)
    python scripts/verify_timeout.py --report  # 표만 (게이트로 쓰지 않을 때)
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ENGINE = HERE / "scan_request_timeouts.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def main() -> int:
    if not ENGINE.is_file():
        # 엔진이 사라졌는데 게이트가 통과하면, 그때부터 아무것도 안 보면서 초록이다.
        print(f"[TIMEOUT] 엔진이 없다: {ENGINE} — 판정할 수 없으므로 멈춘다")
        return 1

    report_only = "--report" in sys.argv[1:]
    argv = [str(ENGINE), str(ROOT / "backend")]
    if not report_only:
        argv.append("--check")

    saved = sys.argv
    sys.argv = argv
    try:
        runpy.run_path(str(ENGINE), run_name="__main__")
    except SystemExit as exc:
        return int(exc.code or 0)
    finally:
        sys.argv = saved
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
