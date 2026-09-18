"""V 단독 세션 잠금 — **재는 동안 아무도 로그인하지 않는다** (P-170 ① · 2026-09-18 턴 U).

★ 왜 이것이 필요한가 [실측 2026-09-17 · 턴 T · D-487]
  V 단독이 온보딩 48행을 재는 동안 조율자가 `verify_ga_readiness` 를 돌렸다. 그 안의 판정기
  (`verify_route_alive` 등)가 **같은 역할 계정으로 로그인**했고, 제품은 계정당 세션 1개라
  V 의 세션이 끊겼다(`end_previous_session`). 이어서 5회/분 율제한(SEC-21)이 429 를 냈다.
  V 는 그 판을 버리고 다시 쟀다 — 「경합 중에 잰 수는 수가 아니다」의 **반대편**이다:
  재는 쪽이 아니라 **재는 동안 끼어든 쪽**이 수를 망쳤다.

규약
  · V 단독이 시작할 때 `docs/agent/evidence/V_LOCK` 을 만든다 — JSON 한 줄
    `{"started_at": …, "session_id": …, "by": "V"}`.
  · 게이트 러너(`verify_ga_readiness` 의 직렬 묶음 · `verify_route_alive.login` · 탐침의 로그인)는
    LOCK 이 있으면 **로그인을 건너뛰고 회색**을 낸다 — 「V 단독 중 · 재지 않음」. 회색은 초록이
    아니다(D-301) — 잠긴 동안 그 게이트는 잰 것이 아니다.
  · V 자신의 도구(캡처 · 걷기 · click_completes · feature_reach · 온보딩 측정)는 막지 않는다:
    환경 변수 `GX_V_SESSION_ID` 가 LOCK 의 `session_id` 와 같으면 `is_locked()` 는 False 다.
    **잠근 사람만 지나간다.**
  · 끝나면 조율자가 지운다(`--unlock`). 지우지 않은 LOCK 은 다음 게이트가 회색으로 알린다 —
    조용히 초록이 되는 것보다 낫다.
  · LOCK 파일은 저장소에 커밋하지 않는다(`.gitignore`) — 있으면 「지금 재는 중」이란 뜻이다.

명령
  python scripts/v_lock.py --lock [--session-id ID]   # V 시작 (ID 를 안 주면 만들어 출력)
  python scripts/v_lock.py --status                    # 잠김/안 잠김
  python scripts/v_lock.py --unlock                    # 조율자가 끝에서
  python scripts/v_lock.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = ROOT / "docs" / "agent" / "evidence" / "V_LOCK"
ENV_SESSION = "GX_V_SESSION_ID"
GRAY_NOTE = "V 단독 중 · 재지 않음 (P-170 ① · evidence/V_LOCK)"


def read_lock(path: Path = LOCK_PATH) -> dict | None:
    """LOCK 이 없으면 None. 있는데 못 읽으면 **잠긴 것으로 본다**(모르면 안 재는 쪽)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return {"started_at": None, "session_id": None, "unreadable": True}
    try:
        data = json.loads(raw)
    except ValueError:
        return {"started_at": None, "session_id": None, "unreadable": True}
    return data if isinstance(data, dict) else {"session_id": None, "malformed": True}


def is_locked(path: Path = LOCK_PATH, env: dict | None = None) -> bool:
    """잠겨 있고 **내가 잠근 사람이 아니면** True."""
    env = os.environ if env is None else env
    lock = read_lock(path)
    if lock is None:
        return False
    mine = env.get(ENV_SESSION)
    if mine and lock.get("session_id") and mine == lock.get("session_id"):
        return False
    return True


def describe(path: Path = LOCK_PATH) -> str:
    lock = read_lock(path)
    if lock is None:
        return "안 잠김"
    return "잠김 — 시작 %s · 세션 %s" % (lock.get("started_at") or "?",
                                       (lock.get("session_id") or "?")[:12])


def acquire(session_id: str | None = None, path: Path = LOCK_PATH) -> dict:
    if read_lock(path) is not None:
        raise SystemExit("[V_LOCK] 이미 잠겨 있다 — %s. 끝난 V 가 안 풀었으면 조율자가 "
                         "`--unlock` 한다" % describe(path))
    sid = session_id or uuid.uuid4().hex
    data = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "session_id": sid, "by": "V"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def release(path: Path = LOCK_PATH) -> bool:
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def self_test() -> int:
    import tempfile

    bad: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "V_LOCK"
        # ① 없으면 안 잠김
        if is_locked(p, env={}):
            bad.append("LOCK 이 없는데 잠겼다고 한다")
        # ② 만들면 잠김 · 남은 다른 세션은 막힌다
        data = acquire("abc123", p)
        if not is_locked(p, env={}):
            bad.append("LOCK 을 만들었는데 안 잠겼다고 한다")
        if not is_locked(p, env={ENV_SESSION: "other"}):
            bad.append("다른 세션 id 인데 지나간다 — 잠근 사람만 지나가야 한다")
        # ③ 잠근 사람은 지나간다
        if is_locked(p, env={ENV_SESSION: "abc123"}):
            bad.append("잠근 세션이 막혔다 — V 자신의 도구가 돌 수 없다")
        if data.get("by") != "V":
            bad.append("잠근 주체를 안 적었다")
        # ④ 두 번 잠그면 거절
        try:
            acquire("dup", p)
            bad.append("이미 잠긴 것을 다시 잠갔다")
        except SystemExit:
            pass
        # ⑤ 깨진 LOCK 은 잠긴 것으로 본다 (모르면 안 재는 쪽)
        p.write_text("{not json", encoding="utf-8")
        if not is_locked(p, env={ENV_SESSION: "abc123"}):
            bad.append("깨진 LOCK 인데 지나간다 — 모르면 잠긴 쪽이어야 한다")
        # ⑥ 풀면 안 잠김 · 두 번 풀면 False
        if not release(p) or release(p):
            bad.append("풀기가 두 번째에 True 를 냈다")
        if is_locked(p, env={}):
            bad.append("풀었는데 잠겼다고 한다")
        if "안 잠김" not in describe(p):
            bad.append("describe 가 풀린 상태를 못 말한다")
    if bad:
        print("[V_LOCK] 자기시험 **실패**:")
        for b in bad:
            print("    " + b)
        return 1
    print("[V_LOCK] 자기시험 통과 — 없음 1 · 잠김 2 · 잠근사람 1 · 중복 1 · 깨짐 1 · 풀기 2")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lock", action="store_true")
    ap.add_argument("--unlock", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--session-id", default="")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.lock:
        data = acquire(a.session_id or None)
        print("[V_LOCK] 잠금 — 시작 %s · 세션 %s (V 도구는 %s=%s 로 돈다)"
              % (data["started_at"], data["session_id"], ENV_SESSION, data["session_id"]))
        return 0
    if a.unlock:
        print("[V_LOCK] %s" % ("풀었다" if release() else "잠겨 있지 않았다"))
        return 0
    print("[V_LOCK] " + describe())
    return 3 if is_locked() else 0


if __name__ == "__main__":
    sys.exit(main())
