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

#: ★ [실측 2026-09-20 · 턴 Y] **이 파일의 `--self-test` 는 윈도 콘솔에서 죽고 있었다** —
#:   cp949 가 `—` 를 못 찍어 `UnicodeEncodeError` 로 **rc=1**. 잠금을 시험하려고 부른
#:   자기시험이 제 출력에 걸려 죽으면, 그 도구는 「빨강」이 아니라 **없는 것**이다.
#:   (`_gate_header.py` 가 같은 이유로 둘 다 세운다.)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

ROOT = Path(__file__).resolve().parent.parent
ENV_SESSION = "GX_V_SESSION_ID"
GRAY_NOTE = "V 단독 중 · 재지 않음 (P-170 ① · evidence/V_LOCK)"

# ═══════════════════════════════════════════════════════════════════════════
# ★★ P-206 [실측 2026-09-20 · 턴 Y · 조율자가 갈라 보였다] **반쪽 잠금이었다.**
#
#   이 파일은 잠금을 **한 자리**에서만 봤다:
#       LOCK_PATH = ROOT/docs/agent/evidence/V_LOCK
#   호스트에서는 맞다. 그런데 **컨테이너 안에서 `ROOT` 는 `/repo`** 이고,
#   `/repo/docs` 에는 `agent` 만 있고 **`evidence` 가 없다.** 실물 잠금은
#   `/docs/agent/evidence/` 에 있다(그 자리는 존재한다). 그래서:
#
#       호스트에서 부른 판정기        → 잠금을 **본다**  (회색 · 옳다)
#       컨테이너로 **위임**한 판정기  → 잠금을 **못 본다**(로그인 성공 4회)
#
#   ★ 그리고 **로그인하는 판정기는 대개 컨테이너로 위임한다** — 호스트에 8000 포트가
#     없기 때문이다. 즉 **잠금이 가장 필요한 쪽에 가장 안 들었다.**
#   ★ 이미 값을 치렀다: 차선 F 의 성능 벌 셋 중 둘이 **401 로 먹혔다**(쌍 4~8 ·
#     1,750/2,400). 401 = 세션 끊김 = 같은 계정 로그인. 「잠갔으니 안전하다」가
#     그 순간 거짓이었다.
#   ★ 턴 W 에 `ISO-02` 를 회색으로 만든 **`/repo` 대 `/docs` 갈림과 같은 뿌리**다.
#
#   고치는 자리는 「컨테이너에서 경로를 바꿔 넘긴다」가 아니다 — 넘기는 자리가
#   하나라도 빠지면 그 자리만 조용히 안 잠긴다. **파일을 찾는 쪽이 두 자리를 다 본다**
#   (`verify_authn_paths._ledger()` 가 이미 쓰는 규약 · D-369: 두 벌을 두지 않는다).
# ═══════════════════════════════════════════════════════════════════════════
#: 잠금 파일의 꼬리. 앞의 뿌리만 자리마다 다르다.
LOCK_TAIL = Path("agent") / "evidence" / "V_LOCK"

#: 볼 자리 — **전부 본다.** 하나라도 있으면 잠긴 것이다.
#:   · `ROOT/docs`  호스트의 저장소 (컨테이너에서는 `/repo/docs` — 여기엔 evidence 가 없다)
#:   · `/docs`      gx-shell 이 문서를 붙이는 자리 (**실물 잠금은 여기 있다**)
#:   · `/repo/docs` 저장소를 통째로 붙인 자리 (있으면 본다)
LOCK_BASES = (ROOT / "docs", Path("/docs"), Path("/repo/docs"))


def lock_candidates(bases=None) -> list:
    """볼 자리 전부. **순서가 우선순위**이지 「여기만 본다」가 아니다."""
    return [Path(b) / LOCK_TAIL for b in (bases or LOCK_BASES)]


def find_lock(bases=None) -> "Path | None":
    """**두 자리를 다 보고** 먼저 실재하는 잠금을 돌려준다. 없으면 None."""
    for cand in lock_candidates(bases):
        try:
            if cand.is_file():
                return cand
        except OSError:                      # 권한·마운트 사고 — 그 자리는 모르는 자리다
            continue
    return None


def write_target(bases=None) -> Path:
    """**새로 잠글 자리** — `agent/evidence` 가 이미 있는 첫 자리(없으면 저장소 쪽)."""
    for cand in lock_candidates(bases):
        try:
            if cand.parent.is_dir():
                return cand
        except OSError:
            continue
    return Path((bases or LOCK_BASES)[0]) / LOCK_TAIL


#: 옛 이름 — 부르는 쪽이 아직 쓴다. **이제 「찾은 자리 또는 쓸 자리」**다.
LOCK_PATH = find_lock() or write_target()


def read_lock(path=None) -> dict | None:
    """LOCK 이 없으면 None. 있는데 못 읽으면 **잠긴 것으로 본다**(모르면 안 재는 쪽).

    ★ `path` 를 안 주면 **그때그때 두 자리를 다시 본다** — 모듈을 불러온 뒤에 잠기는
      일이 흔하고(러너가 먼저 뜨고 V 가 나중에 잠근다), 불러올 때 굳힌 자리는 그 뒤의
      잠금을 못 본다.
    """
    p = Path(path) if path is not None else find_lock()
    if p is None:
        return None
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return {"started_at": None, "session_id": None, "unreadable": True}
    try:
        data = json.loads(raw)
    except ValueError:
        return {"started_at": None, "session_id": None, "unreadable": True}
    return data if isinstance(data, dict) else {"session_id": None, "malformed": True}


def is_locked(path=None, env: dict | None = None) -> bool:
    """잠겨 있고 **내가 잠근 사람이 아니면** True."""
    env = os.environ if env is None else env
    lock = read_lock(path)
    if lock is None:
        return False
    mine = env.get(ENV_SESSION)
    if mine and lock.get("session_id") and mine == lock.get("session_id"):
        return False
    return True


def describe(path=None) -> str:
    lock = read_lock(path)
    if lock is None:
        return "안 잠김 (본 자리: %s)" % " · ".join(
            str(c).replace("\\", "/") for c in lock_candidates())
    where = Path(path) if path is not None else find_lock()
    return "잠김 — 시작 %s · 세션 %s · 자리 %s" % (
        lock.get("started_at") or "?", (lock.get("session_id") or "?")[:12],
        str(where).replace("\\", "/") if where else "?")


def acquire(session_id: str | None = None, path=None) -> dict:
    if read_lock(path) is not None:
        raise SystemExit("[V_LOCK] 이미 잠겨 있다 — %s. 끝난 V 가 안 풀었으면 조율자가 "
                         "`--unlock` 한다" % describe(path))
    target = Path(path) if path is not None else write_target()
    sid = session_id or uuid.uuid4().hex
    data = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "session_id": sid, "by": "V"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    data["path"] = str(target)
    return data


def release(path=None) -> bool:
    """**보이는 자리를 전부** 푼다 — 한 자리만 풀면 나머지가 남아 다음 판정기가 회색이 된다."""
    if path is not None:
        try:
            Path(path).unlink()
            return True
        except FileNotFoundError:
            return False
    freed = False
    for cand in lock_candidates():
        try:
            cand.unlink()
            freed = True
        except (FileNotFoundError, OSError):
            continue
    return freed


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

    # ── ★★ P-206 **출생 표본** — 「반쪽 잠금」 [실측 2026-09-20 · 턴 Y] ──────────
    #
    #   컨테이너의 모양을 그대로 세운다:
    #     · 뿌리 A(`/repo/docs` 꼴) — `agent` 는 있는데 **`evidence` 가 없다**
    #     · 뿌리 B(`/docs` 꼴)      — **실물 잠금이 여기 있다**
    #   종전 규칙은 **A 한 자리만** 봤다 → 「안 잠김」. 그 한 줄 때문에 컨테이너로
    #   위임한 판정기가 V 의 세션을 넷 끊었고, F 의 성능 벌 둘이 401 로 먹혔다.
    with tempfile.TemporaryDirectory() as d:
        base_a = Path(d) / "repo" / "docs"       # 컨테이너의 ROOT/docs — evidence 가 없다
        base_b = Path(d) / "docs"                # gx-shell 이 문서를 붙이는 자리
        (base_a / "agent").mkdir(parents=True)
        (base_b / "agent" / "evidence").mkdir(parents=True)
        (base_b / LOCK_TAIL).write_text(
            json.dumps({"started_at": "2026-09-20T15:00:00",
                        "session_id": "vsess", "by": "V"}) + "\n", encoding="utf-8")
        bases = (base_a, base_b)

        # 종전 규칙(**한 자리만**) — 이것이 그날의 사실이다
        if is_locked(base_a / LOCK_TAIL, env={}):
            bad.append("출생 표본이 안 선다 — 뿌리 A 에는 잠금이 없어야 한다")
        # 지금 규칙(**두 자리를 다 본다**) — 잠겨 있어야 한다
        if find_lock(bases) is None:
            bad.append("★ P-206: **두 자리를 다 보는데도** 잠금을 못 찾는다 — "
                       "컨테이너로 위임한 판정기가 다시 로그인한다")
        if not is_locked(find_lock(bases), env={}):
            bad.append("★ P-206: 찾은 잠금을 안 잠긴 것으로 읽는다")
        # 잠근 사람은 여전히 지나간다 (반쪽을 고치면서 이 문을 닫으면 V 가 못 잰다)
        if is_locked(find_lock(bases), env={ENV_SESSION: "vsess"}):
            bad.append("★ P-206: 잠근 V 자신이 막혔다 — 고침이 너무 넓다")
        # 새로 잠글 자리는 **evidence 가 있는 쪽**이어야 한다(없는 자리에 쓰면 아무도 못 본다)
        if write_target(bases) != base_b / LOCK_TAIL:
            bad.append("★ P-206: 새 잠금을 `evidence` 가 없는 자리에 쓰려 한다 — "
                       "쓴 잠금을 아무도 못 본다")
        # 풀면 **양쪽 다** 풀려야 한다
        release(base_b / LOCK_TAIL)
        if find_lock(bases) is not None:
            bad.append("★ P-206: 풀었는데 잠금이 남아 있다")
    if bad:
        print("[V_LOCK] 자기시험 **실패**:")
        for b in bad:
            print("    " + b)
        return 1
    print("[V_LOCK] 자기시험 통과 — 없음 1 · 잠김 2 · 잠근사람 1 · 중복 1 · 깨짐 1 · 풀기 2 "
          "· **P-206 출생 표본 6**(두 뿌리 · 반쪽 잠금을 잡는다)")
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
