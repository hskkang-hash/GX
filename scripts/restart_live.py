#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-321 — **재적재는 HUP 이 아니라 restart 다.** 사람이 기억하지 않게 한 줄로 (턴 AI 전).

한 문장
-------
    `backend/` 를 고쳐 커밋했으면 이것 한 줄:
        python scripts/restart_live.py --reason "P-289 camera_pulse"
    → `docker restart` 둘 → 건강·celery 준비 대기 → `verify_live_code` → 스모크(P-315)
    → `evidence/OPS-26/restarts.jsonl` 에 「시각 · 사유 · 커밋 · 결과」 한 줄.

왜 HUP 이 아닌가 [실측 2026-09-24 · 턴 AH · OPS-26]
--------------------------------------------------
`/app/gunicorn.conf.py:101` 이 `preload_app = True` 다. 앱은 **마스터**에 올라가고 워커는
그 복제다. `kill -HUP 1` 은 워커만 새로 띄우고 **코드는 다시 안 읽는다.** 대표 결정
「HUP 는 restart」(09-24) · 세종 P-321. `preload_app` 은 운영 모양이라 그대로 둔다.

지키는 선
---------
- 재시작하는 통은 **둘뿐이고 이름이 박혀 있다** — `gx-gunicorn-e` · `gx-celery-e`.
  헤드리스 허용 목록(`scripts/loop/headless.settings.json`)의 두 줄과 같다. 인자로 다른
  이름을 받지 않는다(재생성도 아니고 다른 통도 아니다 · 자료 0 · 되돌릴 것 없음).
- 순서는 P-321 그대로: **커밋 → restart → live_code 초록 → 스모크.** 커밋 안 된
  `backend/` 변경이 있으면 멈추지는 않되 줄에 `dirty_backend` 로 **센다**(한 작업 트리를
  여러 차선이 나눠 쓴다 — 남의 미커밋이 내 재시작을 막으면 안 된다).
- 계획 재시작은 SLA 밖이되 **수는 적는다**(P-171 결). 줄은 지우지 않는다(덧붙이기만).

    python scripts/restart_live.py --reason "…"       # 호스트에서 (docker 를 부른다)
    python scripts/restart_live.py --self-test        # 판정 규칙만

종료 코드: 0 초록 · 1 **빨강**(서버가 안 섰다 · 옛 코드 · 스모크 빨강) · 2 못 쟀다
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TAG = "[RESTART]"
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 헤드리스 허용 목록의 두 줄과 **글자 그대로** 같아야 한다(시험이 대조한다).
CONTAINERS = ("gx-gunicorn-e", "gx-celery-e")
HEALTH_URL = "http://localhost:8500/api/dsm/health"
WAIT_S = 90
LOG = ROOT / "docs" / "agent" / "evidence" / "OPS-26" / "restarts.jsonl"
KST = dt.timezone(dt.timedelta(hours=9))


def judge(*, restarted: dict, health_ok: bool, celery_ready: bool,
          live_code: int, smoke: int) -> tuple[int, str]:
    """재시작 한 번의 결과 → (종료 코드, 한 줄). 순수 함수다.

    ★ 건강 200 · 스모크 초록이어도 `live_code == 1` 이면 **빨강**이다. 그날의 반쪽
      서버는 건강도 events 도 200 이었다 — 옛 코드를 잡는 것은 live_code 하나뿐이다.
    """
    failed = [c for c, ok in restarted.items() if not ok]
    if failed:
        return EXIT_FAIL, f"빨강 — 재시작 실패: {' · '.join(failed)}"
    if not health_ok:
        return EXIT_FAIL, f"빨강 — {WAIT_S}초 안에 건강 200 이 안 왔다"
    if not celery_ready:
        return EXIT_FAIL, f"빨강 — {WAIT_S}초 안에 celery 「ready.」가 안 찍혔다"
    if live_code == EXIT_FAIL:
        return EXIT_FAIL, "빨강 — 재시작했는데도 옛 코드가 돌고 있다(verify_live_code)"
    if smoke == EXIT_FAIL:
        return EXIT_FAIL, "빨강 — 스모크(건강 · 로그인 · 읽기) 빨강"
    if EXIT_UNDECIDABLE in (live_code, smoke):
        return EXIT_UNDECIDABLE, (f"회색 — 섰지만 다 못 쟀다(live_code {live_code} · "
                                  f"smoke {smoke}) · 회색은 초록이 아니다")
    return EXIT_OK, "초록 — 둘 다 새로 섰고 새 코드이고 스모크 셋 200"


def make_line(*, at: str, reason: str, commit: str, dirty_backend: int,
              restarted: dict, health_ok: bool, celery_ready: bool,
              live_code: int, smoke: int, code: int, verdict: str) -> dict:
    """`restarts.jsonl` 한 줄. **값(비밀)은 담지 않는다** — 이름·수·색만."""
    return {"at": at, "reason": reason, "commit": commit, "dirty_backend": dirty_backend,
            "containers": list(restarted), "restarted": restarted,
            "health_ok": health_ok, "celery_ready": celery_ready,
            "live_code_exit": live_code, "smoke_exit": smoke,
            "exit": code, "verdict": verdict, "planned": True}


def _run(argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def _git(*args: str) -> str:
    try:
        return _run(["git", "-C", str(ROOT), *args]).stdout.strip()
    except Exception:                                   # noqa: BLE001
        return ""


def _health_ok(deadline: float) -> bool:
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=5) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    return False


def _celery_ready(since: str, deadline: float) -> bool:
    while time.monotonic() < deadline:
        out = _run(["docker", "logs", "--since", since, "gx-celery-e"])
        if " ready." in (out.stdout + out.stderr):
            return True
        time.sleep(3)
    return False


def self_test() -> int:
    """그날 실제로 일어난 모양으로 먼저 실패해 본다(P-323)."""
    ok = {c: True for c in CONTAINERS}
    base = dict(restarted=ok, health_ok=True, celery_ready=True)
    bad: list[str] = []
    if judge(**base, live_code=0, smoke=0)[0] != EXIT_OK:
        bad.append("다 선 재시작이 초록이 아니다")
    #: 출생 표본 [실측 2026-09-24] HUP 뒤의 모양 — 워커는 새것 · 건강 200 · events 200 ·
    #:   그러나 마스터는 옛 코드. 이것이 초록이면 이 도구는 그날의 사고를 절차로 굳힌다.
    if judge(**base, live_code=1, smoke=0)[0] != EXIT_FAIL:
        bad.append("옛 코드(live_code 1)를 건강·스모크 초록이 덮는다")
    if judge(restarted={**ok, "gx-celery-e": False}, health_ok=True, celery_ready=False,
             live_code=0, smoke=0)[0] != EXIT_FAIL:
        bad.append("celery 재시작 실패를 빨강으로 안 잡는다")
    if judge(**{**base, "health_ok": False}, live_code=0, smoke=0)[0] != EXIT_FAIL:
        bad.append("건강 200 이 안 와도 빨강이 아니다")
    if judge(**base, live_code=0, smoke=2)[0] != EXIT_UNDECIDABLE:
        bad.append("스모크 회색(V 단독 중)이 초록으로 접힌다")
    line = make_line(at="t", reason="r", commit="c", dirty_backend=0, restarted=ok,
                     health_ok=True, celery_ready=True, live_code=0, smoke=0, code=0, verdict="v")
    if set(line) & {"password", "token", "env"}:
        bad.append("줄에 비밀 칸이 있다")
    for b in bad:
        print(f"{TAG} 자기시험 실패: {b}")
    print(f"{TAG} 자기시험 {'통과' if not bad else '실패'} ({6 - len(bad)}/6)")
    return EXIT_OK if not bad else EXIT_FAIL


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P-321 계획 재시작 한 줄")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--reason", help="왜 다시 세우는가(커밋 제목 · P-번호) — 줄에 남는다")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.reason or not args.reason.strip():
        print(f"{TAG} --reason 이 없다 — 사유 없는 재시작은 수로 못 센다(P-321)")
        return EXIT_UNDECIDABLE

    commit = _git("rev-parse", "--short", "HEAD") or "?"
    dirty = [ln for ln in _git("status", "--porcelain", "--", "backend").splitlines() if ln.strip()]
    if dirty:
        print(f"{TAG} ⚠ 커밋 안 된 backend 변경 {len(dirty)}건 — P-321 순서는 커밋 먼저. "
              "멈추지 않고 줄에 센다")

    now = dt.datetime.now(KST)
    since = now.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    restarted: dict[str, bool] = {}
    for c in CONTAINERS:
        try:
            r = _run(["docker", "restart", c])
            restarted[c] = r.returncode == 0
        except Exception:                               # noqa: BLE001
            restarted[c] = False
        print(f"{TAG} docker restart {c} → {'OK' if restarted[c] else '실패'}")

    deadline = time.monotonic() + WAIT_S
    health = _health_ok(deadline) if restarted.get("gx-gunicorn-e") else False
    celery = _celery_ready(since, deadline) if restarted.get("gx-celery-e") else False
    print(f"{TAG} 건강 200 {'OK' if health else '✗'} · celery ready {'OK' if celery else '✗'}")

    live = _run([sys.executable, str(HERE / "verify_live_code.py")], timeout=180)
    print(live.stdout.rstrip())
    smoke = _run([sys.executable, str(HERE / "smoke_live.py")], timeout=120)
    print(smoke.stdout.rstrip())

    code, verdict = judge(restarted=restarted, health_ok=health, celery_ready=celery,
                          live_code=live.returncode, smoke=smoke.returncode)
    line = make_line(at=now.isoformat(timespec="seconds"), reason=args.reason.strip(),
                     commit=commit, dirty_backend=len(dirty), restarted=restarted,
                     health_ok=health, celery_ready=celery, live_code=live.returncode,
                     smoke=smoke.returncode, code=code, verdict=verdict)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(f"{TAG} [입력] 커밋 {commit} · 사유 「{args.reason.strip()}」 · 줄 → "
          f"{LOG.relative_to(ROOT).as_posix()}")
    print(f"{TAG} {verdict}")
    return code


if __name__ == "__main__":
    sys.exit(main())
