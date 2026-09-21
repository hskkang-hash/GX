#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-07 — 로그 **보존** 갈래만 센다 (②④). 얇은 진입점 · 턴 AB · 차선 F.

짝은 `scripts/ops_log_collectors_collect.py`(수집 갈래 ①③⑤ · `OPS-07-a`)다.
왜 두 파일인지는 그쪽 머리말에 적었다 — **대장의 `gate:` 가 인자를 못 싣기** 때문이다.

★ 이 갈래가 묻는 둘
    ② **지금 돌고 있는 수집기에 상한이 걸려 있는가** (적용)
    ④ **다음에 뜰 수집기에 상한이 걸리는가** (선언 · compose)

★ 이 갈래는 **감사 보존 일수의 선언**과 다른 질문이다. 선언한 수(P-230 · 감사 2년)가
  dj-core 가 읽는 자리에 실제로 있는지는 `scripts/ops_retention_policy.py` 가 잰다 —
  그쪽은 **한 행도 지우지 않고** 만료 건수만 센다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ops_log_collectors import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["--only", "보존"] + sys.argv[1:]))
