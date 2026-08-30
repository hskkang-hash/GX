#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""**배포 전 점검** — 막은 것에는 여는 절차가 함께 있어야 한다 (D-382).

한 문장
-------
    **차단은 절반이다. 나머지 절반은 복구 경로다.**

D-370 에서 익명이 쓰던 네 자리를 막았고, 그중 둘은 **AI 분석 서버가 인증 없이 부르던
쓰기 콜백**이었다. 막은 것은 옳다 — 인증 없는 쓰기 콜백을 열어 두는 쪽이 더 나쁘다.

그런데 막기만 하면 이렇게 된다:

    배포한다 → AI 서버가 401 을 받는다 → 검출 결과가 안 들어온다
    → **아무도 안 죽었으므로 아무도 모른다** → 며칠 뒤 「검출이 왜 안 되지」

이 게이트가 그 자리를 막는다. **자격증명이 준비되지 않았으면 배포가 서지 않는다.**

무엇을 보나
-----------
표 ②(`kernels/k5_trust/credentials.py`)에서 `REQUIRED_BEFORE_DEPLOY` 에 오른 이름들이
이 환경에서 **`present` 이상**인가. 미만이면 exit 1 이다.

    ★ 왜 `typed` 가 아니라 `present` 인가 — 배포를 막는 질문과 코드가 읽어도 되는지의
      질문이 다르기 때문이다. 기능 코드는 `typed`(무슨 키인지 안다) 이상을 요구하고
      (`verify_credential_store.py`), 배포는 **값이 이 환경에 실려 있는가**만 묻는다.
      두 문턱을 하나로 합치면, 「무슨 키인지 아직 안 적었다」가 배포를 막게 된다 —
      그것은 서류 문제이지 운영 문제가 아니다.

    ★ 무엇을 세었는지 말한다 (D-301). 요구 목록이 비면 **통과가 아니라 실패**다 —
      아무것도 요구하지 않는 배포 점검은 점검이 없는 것보다 나쁘다(있다는 착시를 준다).

    python scripts/verify_deploy_ready.py            # 판정
    python scripts/verify_deploy_ready.py --list     # 요구 목록과 현재 상태
    python scripts/verify_deploy_ready.py --self-test

⚠ 이 게이트는 **환경을 본다.** 그래서 개발 기계에서는 빨간 것이 정상이다 —
  `--for-deploy` 없이 부르면 판정을 내되 종료 코드는 0 이고, 배포 파이프라인만
  `--for-deploy` 로 불러 실제로 멈춘다. 개발자의 초록을 위해 판정을 무르지 않는다:
  **판정은 언제나 같고, 그 판정에 무엇을 거는가만 다르다.**
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 상태 5값의 순서. 표 ②와 **같은 값**을 쓴다 — 여기서 다시 정의하면 어긋난다(D-369).
STATUS_ORDER = ("absent", "present", "typed", "verified", "rotated")

#: 배포 전에 이 환경에 **값이 있어야** 하는 이름과, 없으면 무엇이 깨지는가.
#: ★ 「무엇이 깨지나」를 함께 적는 이유: 배포를 막는 빨간불은 **막힌 사람이 스스로
#:   풀 수 있어야** 한다. 이름만 있으면 그 사람은 우리에게 물어야 한다.
REQUIRED_BEFORE_DEPLOY: dict[str, str] = {
    "INBOUND_AI_CALLBACK_KEY": (
        "AI 분석 서버가 `/api/media-data/detect-callback` · `/api/media-data/"
        "upload-detection` 을 부를 때 쓸 키다 (D-370 이 두 자리를 막았다). "
        "없으면 **검출 결과 콜백이 401 로 조용히 끊긴다** — 아무도 안 죽으므로 "
        "아무도 모른다. 재난 검출 본선(gRPC)은 살아 있지만 미디어 분석은 멈춘다."
    ),
}


def _load_table():
    """표 ②를 읽는다. Django 없이도 되게 **모듈만** 읽는다."""
    sys.path.insert(0, str(ROOT / "backend"))
    from kernels.k5_trust import credentials as cred
    return cred


def probe_status(env_var: str, declared: str) -> str:
    """이 환경의 상태. **값을 읽되 값을 내보내지 않는다** (D-204 · D-319).

    환경변수가 비어 있으면 선언이 무엇이든 `absent` 다 — 표에 적힌 상태는
    **우리가 아는 것**이고, 이 함수가 재는 것은 **여기 있는 것**이다. 둘이 다를 때
    이기는 쪽은 언제나 후자다(D-323 — 확인 행위가 잠금을 내린다).
    """
    if not (os.environ.get(env_var) or "").strip():
        return "absent"
    # 값이 있으면 최소 present. 선언이 그보다 높으면 선언을 존중한다.
    if STATUS_ORDER.index(declared) > STATUS_ORDER.index("present"):
        return declared
    return "present"


def audit() -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """(행, 문제). 행 = (이름, 환경변수, 상태, 없으면 무엇이 깨지나)."""
    cred = _load_table()
    rows, problems = [], []
    for name, breaks in REQUIRED_BEFORE_DEPLOY.items():
        spec = cred.CREDENTIALS.get(name)
        if spec is None:
            # 요구 목록에 있는데 표 ②에 없다 — **목록이 늙은 것**이다.
            problems.append(
                f"{name}: 배포 전 요구 목록에 있는데 표 ②에 선언이 없다. "
                f"목록과 표가 갈라졌다 — 둘 중 하나를 고쳐라 (D-369)")
            rows.append((name, "?", "미선언", breaks))
            continue
        status = probe_status(spec.env_var, spec.declared_status)
        rows.append((name, spec.env_var, status, breaks))
        if STATUS_ORDER.index(status) < STATUS_ORDER.index("present"):
            problems.append(
                f"{name}: 이 환경에 값이 없다 (`{spec.env_var}` 가 비었다 · {status}). "
                f"깨지는 것 — {breaks}")
    return rows, problems


def self_test() -> int:
    """심어 놓고 잡히는지 본다 (D-277 · D-310).

    ★ **출생 표본** — 이 도구를 만들게 한 바로 그 사례는 합성이 아니다:
      D-370 이 `/api/media-data/detect-callback` 과 `/api/media-data/upload-detection`
      두 자리에 인증을 붙였고, **AI 서버는 그 사실을 모른 채 배포될 참이었다.**
      키는 아직 받지 않았으므로 이 환경에서 그 이름은 `absent` 이고,
      **`absent` 인 채로 `--for-deploy` 가 통과하면 이 게이트는 존재 이유가 없다.**
      아래 마지막 갈래가 그 사례 그대로를 판정한다 — 합성 이름이 아니라
      `REQUIRED_BEFORE_DEPLOY` 의 실제 항목으로.
    """
    checks = []
    keep = dict(os.environ)
    try:
        os.environ.pop("GX_SELFTEST_KEY", None)
        checks.append(("빈 환경변수는 absent 다",
                       probe_status("GX_SELFTEST_KEY", "typed") == "absent"))
        os.environ["GX_SELFTEST_KEY"] = "   "
        checks.append(("공백만 있는 값도 absent 다 — 「있다」로 세면 그것이 착시다",
                       probe_status("GX_SELFTEST_KEY", "typed") == "absent"))
        os.environ["GX_SELFTEST_KEY"] = "x"
        checks.append(("값이 있고 선언이 present 면 present 다",
                       probe_status("GX_SELFTEST_KEY", "present") == "present"))
        checks.append(("값이 있고 선언이 verified 면 선언을 존중한다",
                       probe_status("GX_SELFTEST_KEY", "verified") == "verified"))
        checks.append(("★ 값이 있어도 선언이 absent 면 present 로 올린다 — "
                       "환경이 선언을 이긴다",
                       probe_status("GX_SELFTEST_KEY", "absent") == "present"))
    finally:
        os.environ.clear()
        os.environ.update(keep)

    checks.append(("요구 목록이 비어 있지 않다 — 빈 점검은 점검이 아니다",
                   bool(REQUIRED_BEFORE_DEPLOY)))
    # ★ 출생 표본 — D-370 이 막은 그 콜백의 키. 이름이 목록에 있고, 환경에 없을 때
    #   **실제로 문제로 잡히는가.** 여기서 초록이 나오면 배포가 그냥 지나간다.
    keep = dict(os.environ)
    try:
        os.environ.pop("INBOUND_AI_CALLBACK_KEY", None)
        _, problems = audit()
        checks.append(("★ 출생 표본 — AI 콜백 키가 없는 채로 배포하려 하면 잡는다",
                       any("INBOUND_AI_CALLBACK_KEY" in p for p in problems)))
        os.environ["INBOUND_AI_CALLBACK_KEY"] = "gxselftest-not-a-real-key"
        _, problems = audit()
        checks.append(("★ 출생 표본 음성 — 값이 실리면 더 막지 않는다",
                       not any("INBOUND_AI_CALLBACK_KEY" in p for p in problems)))
    finally:
        os.environ.clear()
        os.environ.update(keep)
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[DEPLOY] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="배포 전 자격증명 점검 (D-382)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--for-deploy", action="store_true",
                    help="배포 파이프라인용 — 준비되지 않았으면 **exit 1**")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:                       # 판정 전에 판정기부터 (D-277 · D-350)
        return 1

    rows, problems = audit()
    print(f"[DEPLOY] [입력] 배포 전 요구 자격증명 {len(rows)}건 "
          f"(모수=REQUIRED_BEFORE_DEPLOY · 술어=이 환경에서 present 이상인가)")
    if not rows:
        print("[DEPLOY] 요구 목록이 비었다 — **아무것도 요구하지 않는 점검은 "
              "점검이 없는 것보다 나쁘다** (있다는 착시를 준다 · D-301)")
        return 1

    for name, env_var, status, breaks in rows:
        mark = "READY" if STATUS_ORDER.index(status) >= 1 else "BLOCK" \
            if status != "미선언" else "BROKEN"
        print(f"  {mark}  {name:28} env={env_var:28} 상태={status}")
        if args.list:
            print(f"         없으면: {breaks}")

    if problems:
        for p in problems:
            print(f"[DEPLOY] 준비되지 않았다 — {p}")
        if args.for_deploy:
            print("[DEPLOY] ★ **배포하지 않는다.** 막은 것에는 여는 절차가 함께 "
                  "있어야 한다 (D-382)")
            return 1
        print("[DEPLOY] (개발 환경 판정 — 종료 코드는 0 이다. 배포 파이프라인은 "
              "`--for-deploy` 로 불러 실제로 멈춘다)")
        return 0
    print(f"[DEPLOY] 통과 — 요구 {len(rows)}건 전부 이 환경에 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
