#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-07-a — 로그 **수집** 갈래만 센다 (①③⑤). 얇은 진입점 · 턴 AB · 차선 F.

왜 파일이 하나 더 있나 — **대장의 `gate:` 는 인자를 못 싣는다**
--------------------------------------------------------------
`ops_log_collectors.py` 는 이제 `--only 수집` 을 받는다. 그런데 대장
(`docs/agent/evidence/D-346/ga_readiness.yaml`)의 `gate:` 칸은 **인자 없는
명령 하나**만 싣는다 [N 실측 · 턴 AA ⑨ — `SEC-05`·`SEC-17`·`LAW-08` 넷이 같은
이유로 언제나 회색이다]. 그래서 **인자 없이 갈래가 갈리는 이름**이 필요하다.

    `OPS-07-a`(수집) → `scripts/ops_log_collectors_collect.py`     ← 이 파일
    `OPS-07`  (보존) → `scripts/ops_log_collectors_retention.py`

★ 이 파일은 **판정을 안 한다.** 판정식은 `ops_log_collectors.judge` 한 벌뿐이고,
  여기 있는 것은 「어느 판정을 종료코드에 세는가」뿐이다. 판정식을 두 벌 두면
  대장이 보는 색과 사람이 돌린 색이 갈린다(D-212).

★ 갈래 밖 판정(②④)도 **화면에는 찍힌다.** 종료코드에서만 뺀다 — 안 보이게
  하는 것과 안 세는 것은 다르고, 앞엣것은 숨기는 것이다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ops_log_collectors import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["--only", "수집"] + sys.argv[1:]))
