#!/usr/bin/env python
"""P-202 — **시험은 운영 감사표에 한 행도 안 쓴다.** 단위 전량 전/후로 센다.

★ 출생 표본 (D-310) — 이 게이트를 태어나게 한 사건은 **차선 S 의 사고다**
-------------------------------------------------------------------------
[실측 2026-09-20 · 턴 X · 차선 S] 시험 DB 다툼 가드의 첫 판이 「이 DB 에 누가 붙어
있나」를 **장고 연결로 물었다.** 묻는 행위 자체가 그 뒤의 `create_test_db` 를 바꿨고,
시험 셋이 운영 DB 에 붙어 운영 감사표에 `guardianx.test.law08_race` **219행**을 남겼다
(03:53~03:55). 그 무리 안에서 증거 체인이 갈려 끊김 **#276795** 가 났다.

    · 그 219행은 **지울 수 없다** — 감사표에서 행을 지우는 것은 「안 고쳐졌다」의 증명
      자체를 약하게 한다(대표 결정 2026-09-20 · 「끊김만 등재하고 행은 둔다」).
    · 즉 이 사고의 비용은 **영구적**이다. 그래서 「안 나게 하는 것」말고는 갚을 길이 없고,
      가드만 달고 지키는 판정기를 안 세우면 그 가드는 한 턴 만에 돌아온다
      (턴 W→X 에 `camera-secret-logs` 가 그대로 보여 준 얼굴이다).

그래서 이 게이트가 재는 것 — **수 하나**
-----------------------------------------
    단위 시험 전량을 돌리기 **전과 후**에, **운영** 감사표에서
    `logger_name LIKE 'guardianx.test.%'` 인 행을 센다. 차이가 0 이어야 한다.

  · **분모는 전량 시험 수**다. 시험 셋만 돌리고 낸 「새 행 0」은 0 이 아니다 —
    그 0 은 「안 샜다」가 아니라 **「샐 자리를 안 지나갔다」**이다 (D-301).
  · **수를 낸다. 값은 안 낸다.** 빨강일 때도 인쇄하는 것은 `id` 와 `logger_name` 까지다 —
    그 둘이 있어야 다음 사람이 어느 시험이 샜는지 찾아갈 수 있고, 그 이상은 감사 내용이다.
  · **이 게이트는 「0 이 늘 0」임을 증명하지 않는다.** 기준선 219 는 그대로 있고 세지 않는다 —
    세면 그 수가 「고쳐야 할 빚」처럼 읽히고, 그 빚을 갚는 유일한 길이 **삭제**가 된다.

두 개의 눈
----------
  ① **정적**(언제나) — *가드가 배선돼 있는가.* 가드가 빠진 저장소에서 「새 행 0」이 나오면
     그것은 이번 실행이 운이 좋았다는 뜻이다. 그 초록은 다음 실행을 못 지킨다.
  ② **표**(`--db`) — 실제로 전량을 돌리고 운영 표를 전/후로 센다.

    python scripts/verify_test_writes_prod_zero.py            # ① 만 → **exit 2** (안 쟀다)
    python scripts/verify_test_writes_prod_zero.py --db       # ① + ② (약 5분)
    python scripts/verify_test_writes_prod_zero.py --self-test

★ **`--db` 없는 호출은 exit 2 다** (P-204 · 이 턴의 규약)
---------------------------------------------------------
`exit 0` 은 「제품이 성립한다」가 아니라 **「이 호출이 통과」**다. 형제 게이트
`verify_evidence_chain.py` 는 `--db` 없이 부르면 정적만 하고 **exit 0** 을 낸다 —
차선 V 가 턴 X 에 그 자리를 자진 신고했다. 같은 얼굴을 여기서 되풀이하지 않는다:
운영 표를 한 번도 안 본 호출은 **회색**이고, 회색은 초록이 아니다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

CONTAINER = os.environ.get("GX_SHELL", "gx-shell")

#: 시험이 남기는 감사 행의 이름표. `audit_writer` 를 지나는 모든 행은 `logger_name` 을
#: 들고, 시험이 쓴 것은 이 접두를 쓴다. **운영 행과 섞이지 않는 유일한 표시**다.
TEST_LOGGER_PREFIX = "guardianx.test."

#: 게이트가 제 시험 DB 를 든다 — 남의 차선 이름을 빌리면 그 차선의 실행과 다툰다(QA-11).
GATE_DB_NAME = os.environ.get("GX_P202_DB", "test_gx_p202")

#: ① 정적 눈이 확인하는 배선. **셋이 다 있어야** 가드가 실제로 돈다.
#:   하나라도 빠지면 가드는 서 있는데 안 도는 물건이 된다.
WIRING = (
    ("backend/common/evidence_chain.py", "def guard_audit_db",
     "가드 자체가 없다"),
    ("backend/common/evidence_chain.py", "def audit_db_isolated",
     "이름을 보는 순수 술어가 없다 — 가드를 DB 없이 시험할 수 없다"),
    ("backend/common/audit_writer.py", "guard_audit_db(doing=",
     "감사 쓰는 문이 가드를 안 부른다"),
    ("backend/conftest.py", "arm_audit_db_guard",
     "conftest 가 가드를 안 켠다 — 서 있어도 안 돈다"),
)


# ══════════════════════════════════════════════════════════════════════════
# 순수 판정 — DB 도 도커도 없이 시험한다 (D-277). 자기시험이 겨누는 과녁이 여기다.
# ══════════════════════════════════════════════════════════════════════════

#: `1823 tests collected` · `786 passed, 3 skipped` 를 읽는다.
_COLLECTED = re.compile(r"(\d+)\s+tests?\s+collected")
_OUTCOME = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped|xfailed|xpassed)")


def parse_collected(text: str) -> int | None:
    """`--collect-only` 가 센 **전량 시험 수**. 못 읽으면 `None` — 0 이 아니다.

    ★ 0 과 `None` 을 가르는 것이 요점이다. 「못 읽었다」를 0 으로 접으면
      분모가 0 인 채로 「새 행 0」이 나오고, **분모 0 인 초록은 초록이 아니다**(D-301).
    """
    found = _COLLECTED.findall(text or "")
    return int(found[-1]) if found else None


def parse_ran(text: str) -> int | None:
    """실행 요약에서 **실제로 돈 시험 수**. `passed+failed+error+skipped+x…` 를 더한다.

    ⚠ 수집 수와 다를 수 있다(중간에 죽은 실행 · `-x`). 그때 분모로 쓰는 것은
      **실제로 돈 수**다 — 돌지 않은 시험은 샐 자리를 안 지나갔다.
    """
    found = _OUTCOME.findall(text or "")
    if not found:
        return None
    return sum(int(n) for n, _ in found)


def judge(*, before: int | None, after: int | None,
          tests: int | None) -> tuple[int, str]:
    """전/후 두 수와 분모로 색을 낸다. **순수 함수다.**

    셋이 아니라 넷이다 — 초록 · 빨강 · **회색** · 그리고 **줄어든 자리**.

      · 분모가 없거나 0      → **2**(회색). 안 잰 것이지 통과가 아니다.
      · 전·후를 못 셌다      → **2**(회색). 0 으로 안 읽는다.
      · 새 행이 늘었다       → **1**. 시험이 운영 표에 썼다.
      · 행이 **줄었다**      → **1**. 감사표에서 행이 사라지는 것은 이 게이트가 재는
                               사고보다 무겁다. 「0 이 아니다」로 뭉뚱그리지 않는다.
      · 차이 0               → **0**.
    """
    if tests is None or tests <= 0:
        return 2, ("분모가 없다 — 시험을 **한 건도 안 돌린 채** 낸 「새 행 0」은 "
                   "「안 샜다」가 아니라 「샐 자리를 안 지나갔다」이다 (D-301)")
    if before is None or after is None:
        return 2, "운영 감사표를 전/후로 못 셌다 — 회색은 초록이 아니다 (D-301)"
    delta = after - before
    if delta > 0:
        return 1, (f"시험이 **운영 감사표에 {delta}행** 을 썼다 (전 {before} → 후 {after} · "
                   f"분모 {tests}). 그 행은 지울 수도 고칠 수도 없다 — 턴 X 의 219행이 "
                   f"그대로 남아 있는 이유다 (P-191 · 대표 결정)")
    if delta < 0:
        return 1, (f"운영 감사표에서 행이 **{-delta}행 사라졌다** (전 {before} → 후 {after}). "
                   f"이것은 새 행보다 무겁다 — 감사 행의 삭제는 체인이 잡으려는 사건 그 자체다")
    return 0, (f"새 행 **0** (전 {before} → 후 {after} · 분모 {tests}). "
               f"기준선 {before}행은 그대로 둔다 — 지우지 않는 것이 규약이다")


def judge_wiring(files: dict) -> list[str]:
    """① 정적 — 가드 배선이 **셋 다** 있는가. `files` 는 {경로: 본문}."""
    out: list[str] = []
    for rel, needle, why in WIRING:
        src = files.get(rel)
        if src is None:
            out.append(f"{rel} 를 못 읽었다 — 배선을 확인할 수 없다")
        elif needle not in src:
            out.append(f"{rel} 에 «{needle}» 가 없다 — {why}")
    return out


# ══════════════════════════════════════════════════════════════════════════
# 표를 보는 눈 — gx-shell 에 위임한다. 호스트에는 dj-core 가 없다.
# ══════════════════════════════════════════════════════════════════════════

_COUNT_SNIPPET = r"""
import os, django, json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.apps import apps
from django.db import connection
M = apps.get_model("logger", "AuditLogs")
qs = M._base_manager.filter(logger_name__startswith=%(prefix)r)
# ★ 값은 안 싣는다 — id 와 logger_name 까지다(머리말). msg·note·data 는 감사 내용이다.
print("GX_P202_JSON " + json.dumps({
    "db": connection.settings_dict.get("NAME") or "",
    "count": qs.count(),
    "max_id": qs.order_by("-id").values_list("id", flat=True).first(),
}, ensure_ascii=False))
"""

_NEW_ROWS_SNIPPET = r"""
import os, django, json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.apps import apps
M = apps.get_model("logger", "AuditLogs")
qs = (M._base_manager.filter(logger_name__startswith=%(prefix)r, id__gt=%(since)d)
      .order_by("id").values("id", "logger_name")[:40])
print("GX_P202_JSON " + json.dumps({"rows": list(qs)}, ensure_ascii=False))
"""


def _docker(args: list[str], *, timeout: int = 1800) -> tuple[int, str]:
    """gx-shell 안에서 돌린다. **도커가 없으면 회색(2)이지 초록이 아니다.**"""
    if shutil.which("docker") is None:
        return 2, "docker 를 못 찾았다"
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    try:
        proc = subprocess.run(
            ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings", *args],
            capture_output=True, text=True, env=env,
            encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return 2, f"시간 초과 ({timeout}s)"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _payload(out: str) -> dict | None:
    for line in out.splitlines():
        if line.startswith("GX_P202_JSON "):
            try:
                return json.loads(line[len("GX_P202_JSON "):].strip())
            except ValueError:
                return None
    return None


def count_prod_rows() -> dict | None:
    """**운영** 감사표의 시험 접두 행 수. 시험 DB 가 아니라 앱이 쓰는 그 표다."""
    _, out = _docker([CONTAINER, "python", "-c",
                      _COUNT_SNIPPET % {"prefix": TEST_LOGGER_PREFIX}], timeout=180)
    return _payload(out)


def collect_tests() -> tuple[int | None, str]:
    """전량 단위 시험을 **세기만** 한다 (분모). 돌리지 않는다."""
    _, out = _docker([
        "-e", f"DB_TEST_NAME={GATE_DB_NAME}", CONTAINER,
        "python", "-m", "pytest", "tests", "--ignore=tests/e2e",
        "-q", "--nomigrations", "-p", "no:randomly", "--collect-only"], timeout=600)
    return parse_collected(out), out


def run_suite() -> tuple[int | None, str]:
    """전량 단위 시험을 **실제로 돌린다.** 돌린 수를 돌려준다.

    ⚠ 시험의 **빨강은 이 게이트의 색이 아니다.** 여기서 재는 것은 「운영 표에 행이
      늘었나」 하나다. 시험이 깨진 실행에서도 그 수는 잴 수 있고, 오히려 그런 실행이
      더 잘 샌다 — 그래서 실패를 이유로 멈추지 않고 **돈 수를 분모로** 삼는다.
    """
    _, out = _docker([
        "-e", f"DB_TEST_NAME={GATE_DB_NAME}", CONTAINER,
        "python", "-m", "pytest", "tests", "--ignore=tests/e2e",
        "-q", "--nomigrations", "-p", "no:randomly",
        # ★ `--tb=no -rf` — 역추적은 안 받고 **이름만** 받는다. 이 게이트는
        #   시험의 빨강을 판정하지 않지만, 「그떄 빨강이 몇이었는지」를 못 적으면
        #   다음 사람이 이 초록을 「전량 초록」으로 읽는다.
        "--tb=no", "-rf"], timeout=2400)
    return parse_ran(out), out


# ══════════════════════════════════════════════════════════════════════════
# 자기시험 — **이 게이트가 빨개지는 것을 본다** (D-277 · D-350)
# ══════════════════════════════════════════════════════════════════════════

def _fake_tree(*, drop: str = "") -> dict:
    """자기시험용 합성 나무. **한 파일에 볼 줄이 둘인 자리가 있다** —
    `{경로: 조각}` 으로 한 번에 만들면 뒤의 조각이 앞의 것을 덮어서 자기시험이
    **거짓 빨강**을 낸다. 이 자리에서 실제로 한 번 빨개졌다 [실측 2026-09-20]:
    `배선이 다 있으면 어긋남 0` 이 X 였고, 어긋난 것은 제품이 아니라 표본이었다.
    """
    tree: dict = {}
    for rel, needle, _ in WIRING:
        tree[rel] = tree.get(rel, "") + needle + " | "
    if drop:
        tree.pop(drop, None)
    return tree


SELF_TESTS = (
    ("★ 출생 표본 — 턴 X 의 219행 유출이면 **빨강(1)**",
     lambda: judge(before=2429, after=2648, tests=1823)[0] == 1),
    ("차이 0 이면 초록(0)",
     lambda: judge(before=219, after=219, tests=1823)[0] == 0),
    ("★ **분모 0 이면 회색(2)** — 「샐 자리를 안 지나갔다」",
     lambda: judge(before=219, after=219, tests=0)[0] == 2),
    ("분모를 못 읽었으면 회색(2) — None 을 0 으로 안 읽는다",
     lambda: judge(before=219, after=219, tests=None)[0] == 2),
    ("전/후를 못 셌으면 회색(2)",
     lambda: judge(before=None, after=219, tests=1823)[0] == 2),
    ("행이 **줄었으면** 빨강(1) — 삭제는 새 행보다 무겁다",
     lambda: judge(before=219, after=218, tests=1823)[0] == 1),
    ("수집 수를 읽는다",
     lambda: parse_collected("1823 tests collected in 4.71s") == 1823),
    ("수집 수를 못 읽으면 None",
     lambda: parse_collected("no tests ran") is None),
    ("돈 수를 더해서 읽는다 (passed + skipped)",
     lambda: parse_ran("1820 passed, 3 skipped, 4 warnings in 250.1s") == 1823),
    ("빨강이 섞인 실행도 분모가 선다",
     lambda: parse_ran("1800 passed, 20 failed, 3 skipped in 260s") == 1823),
    ("요약이 없으면 None — 0 이 아니다",
     lambda: parse_ran("INTERNALERROR") is None),
    ("★ 배선이 다 있으면 어긋남 0",
     lambda: judge_wiring(_fake_tree()) == []),
    ("★ 가드를 켜는 줄이 빠지면 잡는다 — 서 있어도 안 도는 가드",
     lambda: len(judge_wiring(_fake_tree(drop="backend/conftest.py"))) == 1),
    ("★ 한 파일에 줄이 둘인 자리도 **따로** 센다",
     lambda: len(judge_wiring(_fake_tree(
         drop="backend/common/evidence_chain.py"))) == 2),
    ("파일을 못 읽으면 어긋남으로 센다 — 못 본 것은 통과가 아니다",
     lambda: len(judge_wiring({})) == len(WIRING)),
)


def self_test() -> int:
    bad = 0
    for label, fn in SELF_TESTS:
        try:
            ok = bool(fn())
        except Exception as exc:                          # noqa: BLE001
            ok, label = False, f"{label}  ← {type(exc).__name__}: {exc}"
        print(("  O " if ok else "  X ") + label)
        bad += 0 if ok else 1
    print(f"[P-202] 자기시험 {len(SELF_TESTS) - bad}/{len(SELF_TESTS)} 통과")
    return 0 if bad == 0 else 1


# ══════════════════════════════════════════════════════════════════════════

def read_wiring_files() -> dict:
    out = {}
    for rel, _, _ in WIRING:
        path = ROOT / rel
        if path.is_file():
            out[rel] = path.read_text(encoding="utf-8", errors="replace")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--db", action="store_true",
                    help="전량 시험을 돌리고 운영 감사표를 전/후로 센다 (약 5분)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        _header(measured=f"자기시험 표본 · 분모 {len(SELF_TESTS)}")
        print("[P-202] 자기시험 — 이 게이트가 빨개지는 것을 본다")
        return self_test()

    # ── ① 정적 — 가드가 배선돼 있는가 ───────────────────────────────────────
    files = read_wiring_files()
    problems = judge_wiring(files)

    if not args.db:
        # ★ P-204 — 운영 표를 한 번도 안 본 호출은 **회색**이다. 여기서 0 을 내면
        #   「전량 시험이 운영 표에 안 썼다」로 읽히고, 그 문장은 재지 않은 문장이다.
        _header(measured=("(선언 없음 — `--db` 없이 부른 호출이라 운영 감사표를 "
                          "한 번도 안 봤다 · 분모 0)"))
        print(f"[입력] 가드 배선 자리 {len(WIRING)}곳 (정적만 봤다)")
        for p in problems:
            print(f"  · {p}")
        print("[P-202] ① 정적 — " + (f"배선 어긋남 {len(problems)}건"
                                   if problems else "가드 배선 4자리 모두 성립"))
        print("[P-202] ② 표 — **안 쟀다(회색).** `--db` 를 줘야 운영 감사표를 전/후로 센다. "
              "이 호출의 종료 코드는 **2** 다 — `exit 0` 은 「이 호출이 통과」이지 "
              "「제품이 성립한다」가 아니다 (P-204)")
        return 2

    # ── ② 표 — 분모를 먼저 센다(머리글의 마지막 줄이 그 수를 든다) ──────────
    tests, collect_out = collect_tests()
    _header(measured=(f"단위 전량 시험 전/후 운영 감사표의 "
                      f"`logger_name LIKE '{TEST_LOGGER_PREFIX}%'` 새 행 · "
                      f"분모 {tests if tests else 0} (전량 단위 시험 수 · 수집으로 셌다)"))
    print(f"[입력] 가드 배선 자리 {len(WIRING)}곳 · 전량 단위 시험 {tests if tests else 0}건")
    for p in problems:
        print(f"  · {p}")
    print("[P-202] ① 정적 — " + (f"배선 어긋남 {len(problems)}건"
                               if problems else "가드 배선 4자리 모두 성립"))
    if tests is None:
        print("[P-202] ② 표 — **판정 불가**(회색). 전량 시험을 세지 못했다:")
        print(collect_out[-1200:])
        return 2

    pre = count_prod_rows()
    if pre is None:
        print(f"[P-202] ② 표 — **판정 불가**(회색). 컨테이너 «{CONTAINER}» 에서 "
              f"운영 감사표를 못 셌다. 회색은 초록이 아니다 (D-301)")
        return 2
    print(f"[P-202] ② 표 — 운영 DB «{pre['db']}» · 전(前) {pre['count']}행 "
          f"(기준선이다 — 세기만 하고 안 지운다)")

    ran, run_out = run_suite()
    tail = [l for l in run_out.splitlines() if l.strip()][-1:] if run_out else []
    print(f"[P-202] ② 표 — 전량 실행 끝: {tail[0][:160] if tail else '(요약 없음)'}")
    # ★ 시험의 빨강은 **이 게이트의 색이 아니다** — 그러나 수를 적지 않으면
    #   다음 사람이 이 초록을 「전량 초록」으로 읽는다. 이름까지 낸다.
    reds = [l.strip() for l in run_out.splitlines() if l.startswith("FAILED ")]
    print(f"[P-202] ② 표 — 그 실행의 시험 빨강 {len(reds)}건 "
          f"(**이 게이트의 색이 아니다** · 다른 차선의 색이다)")
    for red in reds[:20]:
        print(f"    · {red[:150]}")

    post = count_prod_rows()
    if post is None:
        print("[P-202] ② 표 — **판정 불가**(회색). 실행 뒤 운영 감사표를 못 셌다")
        return 2

    # ★ **돈 수를 못 읽었으면 수집 수로 메우지 않는다.** 실행이 중간에 죽으면 수집 수는
    #   「돌 뻔한 수」이고, 그것을 분모로 쓰면 지나가지도 않은 자리를 지나간 것으로 센다.
    #   다만 **늘어난 행은 분모와 무관하게 늘어난 것**이다 — 그 빨강은 회색 뒤에 안 숨긴다.
    if ran is None:
        print("[P-202] ② 표 — 실행 요약을 못 읽었다(돈 시험 수 불명). "
              f"수집 수 {tests} 로 **메우지 않는다** — 분모는 없는 것으로 센다")
    rc, line = judge(before=pre["count"], after=post["count"], tests=ran)
    if post["count"] > pre["count"]:
        # ★ 분모를 모르는 실행이어도 **늘어난 행은 늘어난 것**이다. 회색 뒤에 안 숨긴다.
        rc = 1
        line = (f"시험이 **운영 감사표에 {post['count'] - pre['count']}행** 을 썼다 "
                f"(전 {pre['count']} → 후 {post['count']}). 그 행은 지울 수도 고칠 수도 없다 (P-191)")
        # ★ 빨강일 때만 **어느 시험이 샜는지**를 id·logger_name 까지 인쇄한다.
        #   그 이상(msg·note·data)은 감사 내용이라 안 낸다 — 게이트는 수를 내지 값을 안 낸다.
        _, out = _docker([CONTAINER, "python", "-c",
                          _NEW_ROWS_SNIPPET % {"prefix": TEST_LOGGER_PREFIX,
                                               "since": int(pre.get("max_id") or 0)}],
                         timeout=180)
        rows = (_payload(out) or {}).get("rows") or []
        for r in rows:
            print(f"    · #{r['id']} {r['logger_name']}")
    print(f"[P-202] ② 표 — {line}")
    if problems and rc == 0:
        # 가드가 없는데 이번 실행만 안 샌 것은 **초록이 아니다**.
        print("[P-202] 이번 실행은 안 샜지만 **가드 배선이 빠져 있다** — "
              "다음 실행을 지키지 못하는 초록이다")
        return 1
    return rc


def _header(*, measured: str) -> None:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _gate_header import gate_header
    except Exception:                                     # noqa: BLE001
        return
    gate_header(__file__,
                target=f"운영 DB (컨테이너 «{CONTAINER}» 의 DJANGO_SETTINGS_MODULE"
                       f"=config.settings · 앱이 쓰는 그 표)",
                as_="(HTTP 계정 없음) — gx-shell 안 Django ORM · DB 자격은 앱이 들고 "
                    "있는 것 그대로(이름: DATABASE_URL / POSTGRES_*)",
                source="살아 있는 DB (django.setup 뒤 ORM) — 파일 사진이 아니다",
                measured=measured)


if __name__ == "__main__":
    raise SystemExit(main())
