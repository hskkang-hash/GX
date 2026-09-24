#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-315 — **살아 있는 서버의 스모크 1.** 시험은 코드를 재고 스모크는 서버를 잰다 (턴 AI 전).

한 문장
-------
    운영 모양 서버(8500)에서 세 문만 30초 안에 — 건강 200 · 로그인 200(토큰 있음) ·
    읽기 문 1 200. 하나라도 아니면 빨강.

왜 [실측 2026-09-24 · 턴 AH]
----------------------------
조율자가 `backend/` 를 고치고 gunicorn 을 안 세웠다. 전량 2,182건이 **전부 초록**인 채로
제품이 500 을 냈다. 시험은 매번 새로 import 하므로 그 고장을 구조적으로 못 잡는다.

이 스모크가 **잡는 것과 못 잡는 것**
------------------------------------
    잡는다:  서버가 죽었다 · 로그인이 깨졌다 · 토큰이 문을 못 연다 · 읽기 문이 500
    못 잡는다: 「반쪽 서버」(부팅 때 import 된 모듈은 옛것, 늦게 import 된 모듈만 새것).
               그날의 500 은 `/api/dsm/cameras/pulse` 한 자리였고 events 는 200 이었다.
               그 자리는 `verify_live_code`(OPS-26)가 잡는다 — 둘은 짝이다.
    그래서 `restart_live.py`(P-321)는 **둘 다** 부른다: 재시작 → live_code → 스모크.

★ 커밋 훅(pre-commit)에 붙이지 않았다 — 순서가 거꾸로다
------------------------------------------------------
P-315 는 「커밋 훅에 스모크 1」이었다. 그러나 P-321 이 순서를 정했다:
**커밋 → restart 둘 → verify_live_code 초록 → 스모크.** pre-commit 은 커밋 **전**에 돌고,
그때 서버는 **아직 옛 코드**다 — 고친 코드를 재지 못하고 옛 코드의 초록을 낸다.
그래서 이 스모크는 재시작 **뒤**에 `restart_live.py` 가 부른다. 손으로도 부를 수 있다.

★ 로그인 계정 — `GX_SMOKE_USER` 가 있으면 그것 · 없으면 `GX_ROUTE_USER`
----------------------------------------------------------------------
제품은 계정당 동시 접속이 1개다(`end_previous_session`). 역할 계정으로 로그인하면
**그 계정으로 재고 있는 사람의 세션을 끊는다.** [실측 2026-09-24] `.env.gates` 의
`GX_ROUTE_USER` 는 게이트 전용이 아니라 **역할 계정**(U4)이다 — 대장 게이트들이 이미 그 계정으로
로그인하므로 이 스모크가 새 종류의 해를 더하지는 않지만, 스모크 전용 계정이 옳다.
그 계정을 만들어 `.env.gates` 에 넣는 것은 `.env` 실제 값이라 **대표 결정**이다 — 그때까지 물러선다.
⚠ `GX_SMOKE_*` 는 지금 **환경에서만** 읽는다. `.env.gates` 로더(`verify_route_alive.LOCAL_ENV_KEYS`)는
  판정기라 조율자가 고치지 않았다(P-203) — 계정이 생기는 날 그 목록에 두 이름을 더한다.
`V_LOCK` 이 있으면 로그인하지 않고 **회색**(V 단독 중 · 재지 않음 · P-170 ①).

    python scripts/smoke_live.py               # 호스트에서 · 기본 http://localhost:8500
    python scripts/smoke_live.py --self-test   # 판정 규칙만

비밀: 비밀번호는 **본문**으로만 보낸다(쿼리 0 · argv 0). 토큰·비밀번호는 출력하지 않는다.
종료 코드: 0 초록 · 1 **빨강** · 2 못 쟀다(자격 없음 · V 단독 중)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TAG = "[SMOKE]"
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
DEFAULT_BASE = "http://localhost:8500"
DEADLINE_S = 30.0

HEALTH_PATH = "/api/dsm/health"
READ_PATH = "/api/dsm/events?limit=1"

#: 판정에 쓰는 한 걸음. `status` 는 HTTP 상태(0 = 응답 없음) · `None` = **안 쟀다**.
#: `ok_extra` 는 상태 밖의 조건 — 로그인은 200 이어도 **토큰이 있어야** 한다.


def step(name: str, status: int | None, ok_extra: bool = True, why: str = "") -> dict:
    return {"name": name, "status": status, "ok_extra": ok_extra, "why": why}


def judge(steps: list[dict], elapsed: float, deadline: float = DEADLINE_S) -> tuple[int, str]:
    """세 걸음과 걸린 시간 → (종료 코드, 한 줄). 순수 함수다.

    ① 안 잰 걸음(`status is None`)이 있으면 — 그 까닭이 자격 없음·V 단독이면 **회색**.
       안 잰 것을 초록으로 접지 않는다(「회색은 초록이 아니다」).
    ② 잰 걸음이 200 이 아니거나 덧조건이 거짓이면 **빨강**. 응답 없음(0)도 빨강이다 —
       「서버가 죽었다」가 이 스모크가 잡으려는 바로 그것이다.
    ③ 셋 다 섰어도 기한을 넘기면 **빨강**(P-315 「30초 안」).
    """
    for s in steps:
        if s["status"] is not None and (s["status"] != 200 or not s["ok_extra"]):
            got = "응답 없음" if s["status"] == 0 else f"HTTP {s['status']}"
            extra = "" if s["ok_extra"] else " · " + (s["why"] or "덧조건 거짓")
            return EXIT_FAIL, f"빨강 — {s['name']} {got}{extra}"
    skipped = [s for s in steps if s["status"] is None]
    if skipped:
        return EXIT_UNDECIDABLE, ("회색 — 안 잰 걸음: "
                                  + " · ".join(f"{s['name']}({s['why']})" for s in skipped))
    if len(steps) < 3:
        return EXIT_UNDECIDABLE, f"회색 — 걸음이 {len(steps)}개뿐이다(셋이어야 한다)"
    if elapsed > deadline:
        return EXIT_FAIL, f"빨강 — 셋 다 200 이지만 {elapsed:.1f}초(기한 {deadline:.0f}초)"
    return EXIT_OK, f"초록 — 건강 · 로그인 · 읽기 셋 다 200 · {elapsed:.1f}초"


def pick_account(env) -> tuple[str | None, str | None, str]:
    """스모크 전용 계정이 **짝으로** 있으면 그것 · 아니면 대장 게이트의 계정. 반쪽은 안 쓴다."""
    if env.get("GX_SMOKE_USER") and env.get("GX_SMOKE_PASSWORD"):
        return env["GX_SMOKE_USER"], env["GX_SMOKE_PASSWORD"], "GX_SMOKE_USER"
    return env.get("GX_ROUTE_USER"), env.get("GX_ROUTE_PASSWORD"), "GX_ROUTE_USER 로 물러섬"


def run(base: str) -> tuple[list[dict], float]:
    """세 걸음을 실제로 밟는다. 비밀은 환경 이름으로만 받고 본문으로만 보낸다."""
    import verify_route_alive as ra  # noqa: PLC0415 — 로더·로그인·hit 은 한 벌(D-369)
    try:
        from v_lock import is_locked, GRAY_NOTE  # noqa: PLC0415
    except ImportError:                                            # pragma: no cover
        is_locked, GRAY_NOTE = (lambda: False), ""

    t0 = time.monotonic()
    steps: list[dict] = []
    steps.append(step("건강 " + HEALTH_PATH, ra.hit(base, "GET", HEALTH_PATH, None)))

    ra.load_local_env()
    user, pw, who = pick_account(os.environ)
    if is_locked():
        steps.append(step("로그인", None, why=GRAY_NOTE or "V 단독 중"))
        steps.append(step("읽기 " + READ_PATH, None, why="로그인 안 함"))
    elif not user or not pw:
        steps.append(step("로그인", None, why="GX_SMOKE_USER·GX_ROUTE_USER 둘 다 없음(.env.gates)"))
        steps.append(step("읽기 " + READ_PATH, None, why="로그인 안 함"))
    else:
        tok = ra.login(base, user, pw)
        steps.append(step(f"로그인 {user} ({who})", 200 if tok else 401, ok_extra=bool(tok),
                          why="" if tok else "토큰을 못 받았다"))
        if tok:
            steps.append(step("읽기 " + READ_PATH, ra.hit(base, "GET", READ_PATH, tok)))
        else:
            steps.append(step("읽기 " + READ_PATH, None, why="토큰 없음"))
    return steps, time.monotonic() - t0


def self_test() -> int:
    """판정 규칙 — 그날 실제로 일어난 모양으로 먼저 실패해 본다(P-323)."""
    bad: list[str] = []
    ok3 = [step("건강", 200), step("로그인", 200), step("읽기", 200)]
    if judge(ok3, 2.0)[0] != EXIT_OK:
        bad.append("셋 다 200 · 2초가 초록이 아니다")
    #: 출생 표본 ① [실측 2026-09-17·18] 로그인 200 + success:false — 토큰이 없다.
    if judge([step("건강", 200), step("로그인", 200, False, "토큰 없음"), step("읽기", None, why="토큰 없음")],
             2.0)[0] != EXIT_FAIL:
        bad.append("200 인데 토큰 없는 로그인을 빨강으로 안 잡는다")
    #: 출생 표본 ② [실측 2026-09-24] 서버가 아예 안 받는다.
    if judge([step("건강", 0), step("로그인", None, why="x"), step("읽기", None, why="x")], 1.0)[0] != EXIT_FAIL:
        bad.append("응답 없음(0)을 빨강으로 안 잡는다 — 죽은 서버가 회색으로 숨는다")
    if judge([step("건강", 200), step("로그인", None, why="V"), step("읽기", None, why="V")], 1.0)[0] != EXIT_UNDECIDABLE:
        bad.append("V 단독 중(안 잰 걸음)이 회색이 아니다")
    if judge([step("건강", 200), step("로그인", 200), step("읽기", 500)], 1.0)[0] != EXIT_FAIL:
        bad.append("읽기 500 을 빨강으로 안 잡는다")
    if judge(ok3, DEADLINE_S + 1)[0] != EXIT_FAIL:
        bad.append("기한을 넘긴 셋 200 을 빨강으로 안 잡는다")
    if judge([step("건강", 200)], 1.0)[0] == EXIT_OK:
        bad.append("걸음 하나만으로 초록이 난다")
    for b in bad:
        print(f"{TAG} 자기시험 실패: {b}")
    print(f"{TAG} 자기시험 {'통과' if not bad else '실패'} ({7 - len(bad)}/7)")
    return EXIT_OK if not bad else EXIT_FAIL


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P-315 살아 있는 서버 스모크 1")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--base", default=os.environ.get("GX_SMOKE_BASE", DEFAULT_BASE))
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    steps, elapsed = run(args.base.rstrip("/"))
    for s in steps:
        mark = "·" if s["status"] is None else ("OK" if s["status"] == 200 and s["ok_extra"] else "✗")
        shown = "안 잼" if s["status"] is None else str(s["status"])
        print(f"{TAG} {mark} {s['name']} → {shown}{(' · ' + s['why']) if s['why'] else ''}")
    code, line = judge(steps, elapsed)
    print(f"{TAG} [입력] 대상 {args.base} · 기한 {DEADLINE_S:.0f}초 · 비밀번호는 본문으로만(값 출력 0)")
    print(f"{TAG} {line}")
    return code


if __name__ == "__main__":
    sys.exit(main())
