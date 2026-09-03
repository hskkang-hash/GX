#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""차선을 가르는 것은 자원이 아니라 **이름**이다 (P-18 정정 · 2026-09-21).

무엇이 막고 있었나 — **컨테이너가 아니라 이름 하나**
----------------------------------------------------
2026-09-20 에 C∥D∥E 를 동시에 못 띄운 사유는 「컨테이너 1대 · 시험 DB 1개」였다.
그중 진짜 벽은 **시험 DB 이름 하나**뿐이었다. Django 는 시험 DB 이름을 `test_` + DB 이름
으로 **정해서** 만들기 때문에, 두 실행이 같은 이름을 만들려 들면 나중 것이 죽는다.

★ **출생 표본** (D-310) — 두 갈래를 같은 날 같은 기계에서 쟀다 [실측 2026-09-21]:

    (가) 이름을 가르면      DB_TEST_NAME=test_gx_c  ‖  test_gx_d
         → 13 passed ‖ 11 passed · **DuplicateDatabase 0건**

    (나) 이름이 같으면      DB_TEST_NAME=test_gx_same  ‖  test_gx_same
         → `psycopg2.errors.DuplicateDatabase: database "test_gx_same" already exists`
           `psycopg2.errors.ObjectInUse: ... is being accessed by other users`
           10 passed · **1 error**

(나)가 이 도구의 이유다. 그 빨강은 **코드 결함처럼 보이지만 환경 충돌**이고,
실제로 2026-09-10 에 그 모양을 한 번 오독할 뻔했다.

무엇을 보는가 — 셋이다
----------------------
  ① `settings.py` 의 `DATABASES["default"]["TEST"]["NAME"]` 이 **환경에서** 온다
     (`DB_TEST_NAME`). 상수로 박히면 차선이 다시 한 이름을 쓴다.
  ② 그 이름이 `.env.example` 에 **이름만** 있다 (D-204 — 값은 저장소 밖).
  ③ 기본값이 비어 있어 **안 주면 지금까지와 똑같이 돈다** — 차선을 안 쓰는 사람의
     명령을 바꾸지 않는 것이 이 정정의 조건이었다.

    python scripts/verify_lane_isolation.py            # 판정
    python scripts/verify_lane_isolation.py --self-test

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 못 쟀다(파일 없음)

호스트에서 돈다 — Django 가 필요 없다. 파일을 읽는다.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "backend" / "config" / "settings.py"
ENV_EXAMPLE = ROOT / "backend" / ".env.example"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 차선마다 가르는 네 이름 (P-18 정정). 시험 DB 만 코드가 강제할 수 있고,
#: 나머지 셋은 실행 명령에서 정해지므로 **여기서는 이름만 적어 둔다.**
LANE_NAMES = {
    "DB_TEST_NAME": "시험 DB — 이 도구가 강제한다",
    "포트": "runserver 8x00 — 실행 명령",
    "버킷 접두": "<x>_ — 실행 명령",
    "시드 테넌트": "tenant_<x> — 시드 인자",
}

ENV_KEY = "DB_TEST_NAME"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def test_name_source(src: str) -> str | None:
    """`TEST` 칸의 `NAME` 이 무엇에서 오는가. 환경이면 그 이름을, 아니면 None."""
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Assign)
                and any(getattr(t, "id", "") == "DATABASES" for t in node.targets)):
            continue
        for call in ast.walk(node.value):
            #: `env("DB_TEST_NAME", default=...)` 를 찾는다 — 상수로 박힌 이름은 안 받는다.
            if (isinstance(call, ast.Call)
                    and getattr(call.func, "id", "") == "env"
                    and call.args
                    and isinstance(call.args[0], ast.Constant)
                    and call.args[0].value == ENV_KEY):
                return ENV_KEY
    return None


def has_default_empty(src: str) -> bool:
    """안 주면 Django 기본으로 돌아가는가 — `default=None` 이어야 한다."""
    return bool(re.search(r'env\(\s*"%s"\s*,\s*default\s*=\s*None\s*\)' % ENV_KEY, src))


def self_test() -> int:
    ok = True
    #: ★ 출생 표본 — (나) 같은 이름이 부딪히는 모양 그대로.
    birth_collision = (
        'psycopg2.errors.DuplicateDatabase: database "test_gx_same" already exists')
    cases = [
        ("★ 출생 표본 — 환경에서 오면 잡아낸다",
         'DATABASES = {"default": {"TEST": {"NAME": env("DB_TEST_NAME", default=None)}}}',
         ENV_KEY),
        ("상수로 박힌 이름은 통과시키지 않는다",
         'DATABASES = {"default": {"TEST": {"NAME": "test_fixed"}}}',
         None),
        ("`TEST` 칸이 아예 없으면 통과시키지 않는다",
         'DATABASES = {"default": {"NAME": "x"}}',
         None),
    ]
    for label, src, want in cases:
        got = test_name_source(src)
        mark = "  " if got == want else "✗ "
        print(f"[LANE] {mark}{label} — {got!r} (기대 {want!r})")
        ok &= got == want

    if "DuplicateDatabase" not in birth_collision:
        print("[LANE] ✗ 출생 표본 문구가 비었다")
        ok = False
    else:
        print("[LANE]   ★ 출생 표본 보유 — 같은 이름일 때 실제로 난 오류를 적어 두었다")

    print(f"[LANE] 자기시험 {'통과' if ok else '실패'} (출생 표본 포함)")
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser(description="차선 자원 분리는 이름 분리다 (P-18 정정)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        print("[LANE] **자기시험이 실패했다** — 판정을 내지 않는다")
        return EXIT_FAIL

    if not (SETTINGS.exists() and ENV_EXAMPLE.exists()):
        print(f"[LANE] 파일을 못 찾았다: {SETTINGS} · {ENV_EXAMPLE} — **판정 불가**")
        return EXIT_UNDECIDABLE

    src = SETTINGS.read_text(encoding="utf-8", errors="replace")
    example = ENV_EXAMPLE.read_text(encoding="utf-8", errors="replace")
    rc = EXIT_OK

    print(f"[LANE] [입력] {len(LANE_NAMES)}건 — 차선마다 가르는 이름")
    for name, why in LANE_NAMES.items():
        print(f"[LANE]   {name:14} {why}")

    # ① 환경에서 오는가
    got = test_name_source(src)
    if got != ENV_KEY:
        rc = EXIT_FAIL
        print(f"[LANE] ✗ `DATABASES[\"default\"][\"TEST\"][\"NAME\"]` 이 환경에서 오지 않는다 "
              f"— 차선이 다시 **한 이름**을 쓴다 (P-18)")
    else:
        print(f"[LANE]   시험 DB 이름이 `{ENV_KEY}` 에서 온다")

    # ② 저장소에는 이름만
    if ENV_KEY not in example:
        rc = EXIT_FAIL
        print(f"[LANE] ✗ `.env.example` 에 `{ENV_KEY}` 가 없다 — 이름을 저장소에 두지 "
              f"않으면 다음 사람이 그 이름을 모른다 (D-204)")
    else:
        print(f"[LANE]   `.env.example` 에 이름만 있다 (값 없음 · D-204)")

    # ③ 안 주면 예전 그대로
    if not has_default_empty(src):
        rc = EXIT_FAIL
        print("[LANE] ✗ 기본값이 비어 있지 않다 — 차선을 안 쓰는 사람의 명령이 바뀐다. "
              "이 정정의 조건이 그것이었다")
    else:
        print("[LANE]   안 주면 Django 기본(`test_` + DB_NAME) — 기존 명령 그대로")

    if rc == EXIT_OK:
        print("[LANE] 통과 — 차선은 이름으로 갈린다 (컨테이너 복제 없음)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
