#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[턴 AS · P-470] 옛 이름 — 본체는 `scripts/browser_click.py` 다(한 벌만 남긴다). 이 파일은 그것을 부를 뿐이다."""
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.argv[0] = str(Path(__file__).resolve().parent / "browser_click.py")
    runpy.run_path(sys.argv[0], run_name="__main__")
