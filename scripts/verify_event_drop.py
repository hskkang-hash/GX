#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-367 — **이벤트는 버리지 않는다.** 소실되는 경로가 0건임을 부작위로 검사한다 (D-300).

왜 이 도구가 필요한가
---------------------
부하시험에서 먼저 무너진 것은 DB 도 CPU 도 아니라 **「이벤트 속도제한 200/분」**이었고,
그 자리의 로그는 `skipping` 한 단어였다. **`skipping` 이 drop 인지 queue 인지 코드가
말해 주지 않았다.** 말해 주지 않는 상태가 곧 결함이다 — 다음 사람도 같은 것을 다시 판다.

[실측 2026-09-11 · 코드] 그때의 `skipping` 은 **캐시 무효화**를 버리는 것이었다:

    common/cache_signal_protection.py::rate_limited   상한 초과 → `return`   ← **drop**
    유일한 사용처: common/universal_optimization.py::universal_cache_invalidation
                  (`post_save`·`post_delete` 전역 수신기 · 200/분)

    이벤트 행 자체는 kernels/k1_event/services.py::record_detection 이
    `@transaction.atomic` 안에서 저장한다 — **그 경로에는 상한도 큐도 없다.**

    ★ 즉 「재난 때 이벤트가 사라진다」는 **일어나지 않았다.** 그러나 결함은 있었다:
      무효화를 버리면 **낡은 화면이 남는다.** 폭주는 곧 재난이고, 그때 관제 대시보드가
      옛 데이터를 보여 준다 — 보는 사람에게는 이벤트가 사라진 것과 같은 일이다.

그래서 이 게이트가 잠그는 것은 **행동**이다: 상한을 넘었을 때 **미루는가, 버리는가.**

보는 것 — 넷
------------
  ① **모양**   상한 초과 갈래가 `SignalProtection.defer` 로 가는가.
               맨 `return` 으로 끝나면 그것이 drop 이고 exit 1
  ② **폭주**   출생 표본(D-310) — 200/분 상한에 **서로 다른 행 300건**을 1분 안에 넣는다.
               **투입 n = 실행 n · dropped 0.** 지연은 허용, 소실은 불허
  ③ **심각**   큐가 심각 등급으로 가득 찬 상태에서 심각 등급이 하나 더 온다.
               **버리지 않는다** — 그 자리에서 처리되어야 한다. 이건 상수다
  ④ **등급**   큐가 찼을 때 버리는 것은 **가장 낮은 등급**이지 가장 오래된 것이 아니다

★ 양성 대조 (D-277 · D-289)
---------------------------
`--self-test` 는 **옛 판(버리는 판)** 을 판정기에 먹여 **잡히는지** 본다.
잡지 못하는 게이트는 초록을 내도 아무것도 재지 않은 것이다.

    python scripts/verify_event_drop.py              # 판정
    python scripts/verify_event_drop.py --json OUT   # 증거 파일로
    python scripts/verify_event_drop.py --self-test

호스트에서 돈다 — Django 설정이 필요 없다(`SignalProtection` 은 설정을 읽지 않는다).
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
GUARD = BACKEND / "common" / "cache_signal_protection.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 출생 표본 (D-310) — 부하시험에서 처음 `skipping` 이 뜬 그 조건.
#: 「200/분 상한에 그보다 많은 저장이 1분 안에 들어왔다」가 전부다.
#: 300 은 200 을 **확실히** 넘으면서 자기시험이 몇 초 안에 끝나는 수다.
SURGE_LIMIT = 200
SURGE_INPUT = 300


# ═══════════════════════════════════════════════════════════════════════════
# ① 모양 — 상한 초과 갈래가 어디로 가는가
# ═══════════════════════════════════════════════════════════════════════════

def drop_shaped(source: str) -> list[str]:
    """`rate_limited` 안에서 **초과 갈래가 미루지 않고 끝나는** 모양을 찾는다.

    술어는 행위로 긋는다 (D-324): 「초과를 판정한 갈래(`check_rate_limit`) 안에
    `defer` 호출이 하나도 없으면 그것은 버리는 것이다.」

    ★ 이 판정기는 **`rate_limited` 라는 이름을 찾지 않는다.** 이름은 바뀐다.
      `check_rate_limit` 을 부르는 **모든** 함수를 보고, 그 함수가 초과를 알고도
      미루지 않으면 잡는다. 이름을 바꿔서 게이트를 피할 자리를 남기지 않는다.
    """
    problems: list[str] = []
    tree = ast.parse(source)

    def calls(node) -> set[str]:
        out = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                f = n.func
                name = getattr(f, "attr", None) or getattr(f, "id", None)
                if name:
                    out.add(name)
        return out

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        made = calls(node)
        if "check_rate_limit" not in made:
            continue
        if "defer" in made or "drain_deferred" in made:
            continue
        # 큐 자체를 만지는 함수는 대상이 아니다 — 초과를 보고 **일을 큐에 두고**
        # 물러나는 것은 버리는 것이 아니라 미루는 것이다(`drain_deferred` 가 그 모양).
        # 이 면제도 이름이 아니라 **행위**로 준다: 미루는 자리를 만지는가.
        if any(isinstance(n, ast.Attribute) and n.attr == "_defer_queue"
               for n in ast.walk(node)):
            continue
        problems.append(
            f"{node.name}(): 상한 초과를 판정하면서(`check_rate_limit`) "
            f"**미루지 않는다**(`defer` 없음) — 그 갈래는 버리는 갈래다. "
            f"지연은 허용, 소실은 불허 (D-367)")
    return problems


# ═══════════════════════════════════════════════════════════════════════════
# ②③④ 행동 — 실제 코드를 폭주시켜 본다
# ═══════════════════════════════════════════════════════════════════════════

def _load_guard():
    """실제 `common/cache_signal_protection.py` 를 불러온다.

    **다시 구현하지 않는다** — 두 벌은 반드시 어긋난다 (D-369). 재현이 아니라
    같은 코드를 돌린다. 못 불러오면 초록이 아니라 **판정 불가**다 (D-301).
    """
    sys.path.insert(0, str(BACKEND))
    import common.cache_signal_protection as guard  # noqa: PLC0415
    return guard


class _Sender:
    """`sender._meta.model_name` 만 보는 코드에 먹일 최소한의 대역."""

    def __init__(self, model_name: str):
        self._meta = type("M", (), {"model_name": model_name})()
        self.__name__ = model_name


class _Row:
    def __init__(self, pk: int):
        self.pk = pk


def _drain_all(guard, limit=None, rounds: int = 200) -> int:
    total = 0
    for _ in range(rounds):
        done = guard.SignalProtection.drain_deferred(limit)
        total += done
        if not done:
            break
    return total


def surge_case(guard) -> dict:
    """② 출생 표본 — 상한 200 에 **서로 다른 행 300건**. 투입 n = 실행 n."""
    guard.SignalProtection.reset_defer_state()
    ran: list[int] = []

    @guard.rate_limited(max_per_minute=SURGE_LIMIT)
    def handler(sender, instance, **kwargs):
        ran.append(instance.pk)

    sender = _Sender("detectionevent")
    for pk in range(SURGE_INPUT):
        handler(sender, _Row(pk))
    _drain_all(guard, None)

    stats = guard.SignalProtection.defer_stats()
    return {
        "투입": SURGE_INPUT,
        "실행": len(ran),
        "서로 다른 행": len(set(ran)),
        "dropped": stats["dropped"],
        "deferred": stats["deferred"],
        "drained": stats["drained"],
        "queue_len": stats["queue_len"],
    }


def critical_case(guard) -> dict:
    """③ 큐가 **심각 등급으로** 가득 찬 상태에서 심각 등급이 하나 더 온다."""
    guard.SignalProtection.reset_defer_state()
    ran: list[int] = []

    def handler(sender, instance, **kwargs):
        ran.append(instance.pk)

    sender = _Sender("detectionevent")          # CRITICAL_MODELS 안에 있다
    for pk in range(guard.DEFER_QUEUE_MAX):
        guard.SignalProtection.defer(
            handler, sender, _Row(pk), {},
            priority=guard.PRIORITY_CRITICAL, model_name="detectionevent")
    outcome = guard.SignalProtection.defer(
        handler, sender, _Row(10 ** 9), {},
        priority=guard.PRIORITY_CRITICAL, model_name="detectionevent")
    stats = guard.SignalProtection.defer_stats()
    return {
        "큐 상한": guard.DEFER_QUEUE_MAX,
        "넘친 심각 등급의 처분": outcome,       # "run_now" 여야 한다
        "dropped": stats["dropped"],
        "ran_inline": stats["ran_inline"],
    }


def priority_case(guard) -> dict:
    """④ 큐가 찼을 때 버리는 것은 **가장 낮은 등급**이지 가장 오래된 것이 아니다."""
    guard.SignalProtection.reset_defer_state()

    def handler(sender, instance, **kwargs):
        pass

    crit = _Sender("detectionevent")
    low = _Sender("sometable")

    # 가장 **오래된** 것을 심각 등급으로 둔다 — 나이로 버리면 이것이 먼저 나간다
    guard.SignalProtection.defer(handler, crit, _Row(1), {},
                                 priority=guard.PRIORITY_CRITICAL,
                                 model_name="detectionevent")
    for pk in range(2, guard.DEFER_QUEUE_MAX + 1):
        guard.SignalProtection.defer(handler, low, _Row(pk),
                                     {}, priority=guard.PRIORITY_LOW,
                                     model_name="sometable")
    # 큐가 찼다. 보통 등급 하나가 더 온다 → 가장 낮은 등급(LOW)이 나가야 한다
    guard.SignalProtection.defer(handler, low, _Row(10 ** 9), {},
                                 priority=guard.PRIORITY_NORMAL,
                                 model_name="sometable")
    stats = guard.SignalProtection.defer_stats()
    return {
        "버린 것": dict(stats["drop_detail"]),
        "심각 등급을 버렸는가": "detectionevent" in stats["drop_detail"],
        "dropped": stats["dropped"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# 판정
# ═══════════════════════════════════════════════════════════════════════════

def judge(shape: list[str], surge: dict, critical: dict, priority: dict) -> list[str]:
    """네 갈래의 결과를 문제 목록으로. **판정식을 한 곳에만 둔다** (D-212)."""
    problems = list(shape)

    if surge["실행"] != surge["투입"]:
        problems.append(
            f"★ 폭주 소실: 투입 {surge['투입']}건 · 실행 {surge['실행']}건 — "
            f"{surge['투입'] - surge['실행']}건이 사라졌다. "
            f"지연은 허용이고 소실은 불허다 (D-367)")
    if surge["dropped"]:
        problems.append(f"★ 폭주 중 버린 것 {surge['dropped']}건 — 0 이어야 한다")
    if surge["queue_len"]:
        problems.append(
            f"흘린 뒤에도 큐에 {surge['queue_len']}건이 남았다 — "
            f"미루기가 사실상 버리기가 된다")

    if critical["넘친 심각 등급의 처분"] != "run_now":
        problems.append(
            f"★ 큐가 심각 등급으로 찼는데 새 심각 등급의 처분이 "
            f"{critical['넘친 심각 등급의 처분']!r} 다 — **심각 등급은 어떤 경우에도 "
            f"버리지 않는다.** 버릴 수 없으면 그 자리에서 처리한다 (D-367 ③)")
    if critical["dropped"]:
        problems.append(f"★ 심각 등급을 {critical['dropped']}건 버렸다 — 이건 상수다")

    if priority["심각 등급을 버렸는가"]:
        problems.append(
            "★ 큐가 찼을 때 **심각 등급**을 버렸다 — 버릴 것은 가장 낮은 등급이다")
    if priority["dropped"] != 1:
        problems.append(
            f"큐가 찼는데 버린 것이 {priority['dropped']}건이다 — "
            f"자리를 하나 비웠어야 한다(1건). 판정기가 무엇을 재는지 다시 본다 (D-350)")

    return problems


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **옛 판을 먹여 잡히는지 본다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════

OLD_DROPPING_SOURCE = '''
class SignalProtection:
    @classmethod
    def check_rate_limit(cls, model_name, max_per_minute=100):
        return False

def rate_limited(max_per_minute=100):
    def decorator(func):
        def wrapper(sender, instance, **kwargs):
            if SignalProtection.check_rate_limit("x", max_per_minute):
                print("skipping")
                return
            return func(sender, instance, **kwargs)
        return wrapper
    return decorator
'''

NEW_DEFERRING_SOURCE = '''
def rate_limited(max_per_minute=100):
    def decorator(func):
        def wrapper(sender, instance, **kwargs):
            SignalProtection.drain_deferred(max_per_minute)
            if not SignalProtection.check_rate_limit("x", max_per_minute):
                return func(sender, instance, **kwargs)
            if SignalProtection.defer(func, sender, instance, kwargs,
                                      priority=0, model_name="x") == "run_now":
                return func(sender, instance, **kwargs)
        return wrapper
    return decorator
'''


def self_test() -> int:
    checks: list[tuple[str, bool]] = []

    hits = drop_shaped(OLD_DROPPING_SOURCE)
    checks.append(("★ 출생표본 옛 판(초과 시 `return`) — 잡는다", bool(hits)))
    checks.append(("새 판(미루는 판)은 안 잡는다", not drop_shaped(NEW_DEFERRING_SOURCE)))
    checks.append(("상한을 아예 안 보는 함수는 대상이 아니다",
                   not drop_shaped("def f():\n    return 1\n")))

    queue_holding = (
        "def drain(cls, limit):\n"
        "    if cls.check_rate_limit('x', limit):\n"
        "        return 0\n"
        "    cls._defer_queue.pop('k')\n")
    checks.append(("일을 큐에 둔 채 물러나는 것은 버리는 것이 아니다",
                   not drop_shaped(queue_holding)))

    ok_surge = {"투입": 300, "실행": 300, "서로 다른 행": 300, "dropped": 0,
                "deferred": 100, "drained": 100, "queue_len": 0}
    checks.append(("투입 = 실행 이면 통과", not judge([], ok_surge,
                                                  {"넘친 심각 등급의 처분": "run_now", "dropped": 0},
                                                  {"심각 등급을 버렸는가": False, "dropped": 1})))
    lost = dict(ok_surge, 실행=280)
    checks.append(("★ 20건이 사라지면 잡는다",
                   any("소실" in p for p in judge([], lost,
                       {"넘친 심각 등급의 처분": "run_now", "dropped": 0},
                       {"심각 등급을 버렸는가": False, "dropped": 1}))))
    checks.append(("★ 심각 등급을 버리면 잡는다",
                   any("심각 등급" in p for p in judge([], ok_surge,
                       {"넘친 심각 등급의 처분": "queued", "dropped": 1},
                       {"심각 등급을 버렸는가": False, "dropped": 1}))))
    checks.append(("★ 나이로 버려 심각 등급이 나가면 잡는다",
                   any("가장 낮은 등급" in p for p in judge([], ok_surge,
                       {"넘친 심각 등급의 처분": "run_now", "dropped": 0},
                       {"심각 등급을 버렸는가": True, "dropped": 1}))))
    checks.append(("★ 흘린 뒤 큐가 남으면 잡는다",
                   any("큐에" in p for p in judge([], dict(ok_surge, queue_len=7),
                       {"넘친 심각 등급의 처분": "run_now", "dropped": 0},
                       {"심각 등급을 버렸는가": False, "dropped": 1}))))

    bad = [n for n, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'OK  ' if ok else 'FAIL'}  {name}")
    pos = sum(1 for n, _ in checks if n.startswith("★"))
    print(f"[EVENTDROP] 자기시험 {len(checks)}건 "
          f"{'통과' if not bad else '실패'} (양성 {pos} · 음성 {len(checks) - pos})")
    return EXIT_OK if not bad else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", metavar="OUT", help="증거를 파일로 적는다")
    args = ap.parse_args()

    rc = self_test()
    if args.self_test:
        return rc
    if rc != EXIT_OK:
        print("[EVENTDROP] 자기시험이 실패했다 — 판정기를 먼저 고친다 (D-350)")
        return rc

    if not GUARD.exists():
        print(f"[EVENTDROP] {GUARD.relative_to(ROOT)} 가 없다 — 판정 불가 (D-301)")
        return EXIT_UNDECIDABLE
    try:
        guard = _load_guard()
    except Exception as exc:                     # noqa: BLE001
        print(f"[EVENTDROP] 실코드를 부르지 못했다: {type(exc).__name__}: {exc}")
        print("[EVENTDROP] **판정 불가**다. 「위반 0」이 아니다 (D-301)")
        return EXIT_UNDECIDABLE

    shape = drop_shaped(GUARD.read_text(encoding="utf-8"))
    surge = surge_case(guard)
    critical = critical_case(guard)
    priority = priority_case(guard)
    problems = judge(shape, surge, critical, priority)

    print(f"[EVENTDROP] ② 폭주 — 투입 {surge['투입']}건 · 실행 {surge['실행']}건 · "
          f"미룬 것 {surge['deferred']}건 · **버린 것 {surge['dropped']}건** "
          f"(상한 {SURGE_LIMIT}/분 · 출생 표본 D-310)")
    print(f"[EVENTDROP] ③ 심각 등급 — 큐 {critical['큐 상한']}칸이 전부 심각 등급일 때 "
          f"새 심각 등급의 처분: **{critical['넘친 심각 등급의 처분']}** "
          f"(버린 것 {critical['dropped']}건)")
    print(f"[EVENTDROP] ④ 등급 — 큐가 찼을 때 버린 것: {priority['버린 것'] or '없음'} "
          f"(심각 등급을 버렸는가: {'예' if priority['심각 등급을 버렸는가'] else '아니오'})")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "decision": "D-367",
            "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "surge": surge, "critical": critical, "priority": priority,
            "shape_problems": shape, "verdict": "PASS" if not problems else "FAIL",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[EVENTDROP] 증거 → {out}")

    if problems:
        print("[EVENTDROP] 위반")
        for p in problems:
            print(f"  · {p}")
        return EXIT_FAIL
    print("[EVENTDROP] 통과 — **소실 0건.** 지연은 허용, 소실은 불허 (D-367)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
