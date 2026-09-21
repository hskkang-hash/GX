#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-79 — **V 의 첫 판정기.** 직전 커밋과 견줘 시험 수·오류 수·소요의 변화를 낸다.

무엇이 이 도구를 만들었나 — **빨강이 8배 빨랐고, 아무도 그 수를 안 봤다**
--------------------------------------------------------------------------
[실측 2026-09-06 · 턴 G · `docs/agent/evidence/P-71/판별자가_한_번_틀렸다.md`]

    [앞] 21 errors in 3.66s
    [뒤] 21 passed, 34 warnings in 31.04s

차선 셋(E·C·V)이 같은 빨강을 따로 가져왔고 **셋 다 「환경」이라고 불렀고 셋 다 틀렸다.**
그것은 우리가 만든 회귀였다 — `--nomigrations` 판별자 한 줄. 그 사실은 **수 하나에**
적혀 있었다: 시험이 8배 빨리 끝났다. **아무것도 안 했으니까.**

  ★ 자기 차선 밖에서 온 빨강은 환경처럼 보인다. 옆 차선이 만든 회귀도 그렇게 보인다.
    그 둘을 가르는 것은 차선 하나가 아니라 **전체를 보는 자리**의 일이다 (세종).
    이 파일이 그 자리의 도구다.

무엇을 보는가 — 셋
------------------
  ``시험 수``   걷힌 시험이 몇 개인가. **줄어든 것을 아무도 안 본다** — 0건 수집은
                초록처럼 보인다 (P-71 의 `TheDisabledRun…` 함정이 그 자리였다).
  ``오류 수``   실패 + 오류. 늘면 빨강이다.
  ``소요``      **이 수가 P-71 을 잡을 수 있었다.** 아무것도 안 하면 빨리 끝난다.

판정 — **±20% 를 넘으면 회색이 아니라 빨강**
--------------------------------------------
회색은 「환경이라 못 쟀다」는 뜻이고, 그 낱말은 P-71 에서 **회귀를 덮는 데 쓰였다.**
그래서 이 도구에서 20% 밖의 변화는 회색이 될 수 없다. 사람이 봐야 한다.

  ★ **사유란에 「환경」이라고 적으려면 `env` 블록에 실패 항목의 이름이 있어야 한다**
    (`scripts/gate_env.py --json` 이 낸 것). 이름 없는 「환경」은 받지 않는다 —
    셋이 그날 적은 것이 정확히 그 이름 없는 「환경」이었다.

기준선은 어디에 두나
--------------------
    docs/agent/evidence/P-79/delta_baseline.json

한 벌의 실행을 한 줄로 적는다(`runs` 배열, 시간 순). 판정은 **한 갈래(suite) 안에서
가장 최근 두 점**을 견준다. 점이 하나뿐이면 판정이 아니라 **회색**이다 — 견줄 것이
없는데 초록을 내면 그것이 D-301 이다.

쓰는 법
-------
    python scripts/verify_delta.py --self-test
    python scripts/verify_delta.py --record --suite backend-unit --from-file out.txt \\
        --command "docker exec … pytest tests -q --nomigrations" [--env-json env.json] \\
        [--reason "환경 — minio 가 없다"]
    python scripts/verify_delta.py                      # 갈래마다 최근 두 점을 견준다
    python scripts/verify_delta.py --suite backend-unit
    python scripts/verify_delta.py --list
    python scripts/verify_delta.py --baseline-note "이번 벌은 오염돼 안 적는다 — …"

★ [P-93 · 턴 J] `--baseline-note` — **기준선을 안 옮기기로 한 것도 판단이다.**
  점은 안 적고 사유만 적는다. 턴 I 는 오염된 마감 벌을 적지 않기로 옳게 정했지만,
  그 사유를 남길 길이 「적으면서 사유를 다는 것」뿐이었다 — 판단과 사유가 다른 자리에
  있었다. 이제 같은 자리에 있다.

빨강에는 **사유 이름**이 붙는다 (P-87 · 턴 I) — `BASELINE_STALE` · `DIRTY_RUN` ·
`SUITE_SHRANK` · `GATE_SCOPE_WIDENED` · `REAL_REGRESSION` · `SPEEDUP_SUSPECT` ·
`SLOWDOWN_UNEXPLAINED` · `ENV_UNNAMED`. 「무엇이 줄었다」만 말하는 빨강은 읽은 사람의
할 일을 정해 주지 않는다. **이름은 종료 코드를 바꾸지 않는다.**

종료 코드: **0 초록 · 1 빨강 · 2 회색**.
회색은 둘이다 — ① 견줄 점이 없다 ② **가장 최근 점이 HEAD 가 아니다**(P-93 · 턴 J).
②를 초록으로 내던 자리가 있었다: 낡은 두 점이 서로 조용하면 이 도구가 「초록」을 냈고,
그 초록은 **지금 코드를 한 줄도 안 본 초록**이었다. 못 잰 것을 초록으로 적지 않는다.
호스트에서 돈다 — Django 가 필요 없다. 읽는 것은 pytest 가 마지막에 적은 한 줄이다.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "docs" / "agent" / "evidence" / "P-79" / "delta_baseline.json"
TAG = "[DELTA]"

EXIT_OK, EXIT_FAIL, EXIT_GRAY = 0, 1, 2

#: 문턱. 세종 판정 — 「±20% 를 넘으면 회색이 아니라 빨강」.
THRESHOLD = 0.20

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# pytest 가 마지막에 적는 한 줄을 읽는다
# ═══════════════════════════════════════════════════════════════════════════
#: `21 errors in 3.66s` · `21 passed, 34 warnings in 31.04s` ·
#: `===== 3 failed, 1141 passed, 12 skipped in 250.01s (0:04:10) =====`
_SUMMARY = re.compile(
    r"^=*\s*(?P<body>\d+\s+[a-z]+(?:\s*,\s*\d+\s+[a-z]+)*)"
    r"\s+in\s+(?P<secs>\d+(?:\.\d+)?)s\b[^\n]*$",
    re.M,
)
#: 결과로 세는 낱말. `warnings`·`deselected` 는 시험이 아니다 — 세면 분모가 흔들린다.
_OUTCOMES = {"passed", "failed", "error", "errors", "skipped",
             "xfailed", "xpassed"}
_ERRORLIKE = {"failed", "error", "errors"}


def parse_pytest(text: str) -> dict | None:
    """pytest 출력에서 `(시험 수 · 오류 수 · 소요)` 를 뽑는다. 못 읽으면 `None`.

    ★ **마지막 요약 줄을 쓴다.** 앞쪽 줄에도 비슷한 모양이 나올 수 있고(재실행 요약 등),
      판정에 쓰는 것은 그 실행이 끝나며 적은 마지막 수다.
    """
    last = None
    for m in _SUMMARY.finditer(text):
        last = m
    if last is None:
        return None
    counts: dict[str, int] = {}
    for chunk in last.group("body").split(","):
        parts = chunk.split()
        if len(parts) == 2 and parts[0].isdigit():
            counts[parts[1]] = counts.get(parts[1], 0) + int(parts[0])
    tests = sum(v for k, v in counts.items() if k in _OUTCOMES)
    errors = sum(v for k, v in counts.items() if k in _ERRORLIKE)
    if tests == 0 and errors == 0:
        return None
    return {"tests": tests, "errors": errors,
            "duration_s": float(last.group("secs")),
            "counts": counts, "summary_line": last.group(0).strip()}


# ═══════════════════════════════════════════════════════════════════════════
# 기준선
# ═══════════════════════════════════════════════════════════════════════════
def load() -> dict:
    if not BASELINE.is_file():
        return {"schema": 1, "threshold": THRESHOLD, "runs": []}
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")


def append_note(data: dict, why: str, *, commit: str, at: str) -> dict:
    """`baseline_notes` 에 한 줄 더한다 — **`runs` 는 건드리지 않는다.**

    ★ [P-93 · 턴 J] 왜 이 함수가 따로 있나:

        턴 I 는 마감 벌을 **적지 않기로** 정했다(옆 차선의 파일 수정과 겹친 오염된 벌).
        그 판단은 옳았는데, 그것을 파일에 적을 길이 `--record --baseline-why` 뿐이었다 —
        **적지 않기로 한 벌을 적어야만 사유를 남길 수 있었다.** 그래서 그 사유는
        다음 점의 꼬리에 붙어서야 겨우 남았다.

        기준선을 **안 옮기기로 한 것도 판단이다.** 판단에는 사유가 있어야 하고,
        사유는 판단과 같은 자리에 있어야 한다. 그래서 `--baseline-note` 를 둔다.
    """
    notes = list(data.get("baseline_notes") or [])
    notes.append({"at": at, "commit": commit, "why": why})
    data["baseline_notes"] = notes
    return data


def dirty_files() -> int:
    """잰 순간 **작업본이 몇 파일 더러웠는가**. 못 물으면 `-1`(모른다 ≠ 0).

    ★ 0 과 「모른다」를 가른다. 0 으로 적으면 「깨끗한 창에서 쟀다」가 되고,
      그것이 이 저장소가 계속 만나는 거짓말(D-301)이다.
    """
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            return -1
        return len([ln for ln in out.stdout.splitlines() if ln.strip()])
    except Exception:                                   # noqa: BLE001
        return -1


def head_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or "알 수 없음"
    except Exception:                                   # noqa: BLE001
        return "알 수 없음"


# ═══════════════════════════════════════════════════════════════════════════
# 판정
# ═══════════════════════════════════════════════════════════════════════════
def _ratio(old: float, new: float) -> float | None:
    """`(new-old)/old`. 앞이 0 이면 비율이 없다 — `None` 이고, 그것은 초록이 아니다."""
    if old == 0:
        return None
    return (new - old) / old


# ═══════════════════════════════════════════════════════════════════════════
# 사유 이름 — **「무엇이 줄었다」는 판정이 아니다** (P-87 · 2026-09-06 · 턴 I)
# ═══════════════════════════════════════════════════════════════════════════
#: ★ 무엇이 이 표를 만들었나 [실측 2026-09-06 · 턴 I]
#:
#:   이 판정기가 처음 낸 exit 1 은 이렇게 말했다:
#:
#:       **빨강** 오류가 0 → 4 로 4건 늘었다
#:       **빨강** 소요가 +29.9% 움직였다
#:
#:   틀린 말은 하나도 없는데 **읽은 사람이 할 일이 정해지지 않는다.** 오류 4건이
#:   코드가 만든 것인지 · 기준선이 낡아 엉뚱한 두 점을 견준 것인지 · 시험이 도는
#:   동안 옆 차선이 같은 파일을 고치고 있었던 것인지가 갈리지 않기 때문이다.
#:   그 셋은 **할 일이 완전히 다르다**(고친다 / 다시 잰다 / 다시 돌린다).
#:
#:   P-71 이 정확히 이 자리였다. 차선 셋이 같은 빨강을 「환경」이라고 불렀고 셋 다
#:   틀렸다. 이름 없는 사유는 그때도 아무 일도 하지 않았다. 그래서 **모든 빨강은
#:   이름을 가진다** — 이름이 없는 빨강이 하나라도 나오면 그것은 이 판정기의 결함이고,
#:   자기시험이 그것을 잡는다(`UNNAMED_RED`).
#:
#:   ⚠ 이름은 **종료 코드를 바꾸지 않는다.** 사유가 「기준선이 낡았다」여도 빨강은
#:     빨강이다 — 사유를 붙여 초록으로 내리는 순간 이 표가 거짓 초록의 도구가 된다.
CAUSE_TEXT: dict[str, str] = {
    "ENV_UNNAMED":
        "사유란에 「환경」이라 적었는데 `env` 블록에 이름이 없다 — "
        "할 일: `gate_env.py --json` 이 낸 이름을 붙이고 다시 적는다",
    "BASELINE_STALE":
        "뒤 점의 커밋이 저장소 HEAD 가 아니다 — 이 판정은 **지금 코드를 안 본다**. "
        "할 일: HEAD 에서 한 벌 돌려 `--record` 로 적고 다시 판정한다",
    "DIRTY_RUN":
        "**오염된 창에서 난 수다** — 두 점의 커밋이 같은데 수가 달라졌거나(같은 코드에서 "
        "다른 수), 잰 순간 **작업본이 더러웠다**(미커밋 파일이 있었다 · 동시 차선·"
        "오염된 시험 DB·경주). 원인은 이 커밋의 코드가 아니다. "
        "할 일: 조용한 창에서 다시 돌린다",
    "SUITE_SHRANK":
        "걷힌 시험이 문턱 밖으로 **줄었다** — 0건 수집은 초록처럼 보인다(P-71). "
        "할 일: 무엇이 안 걷혔는지 이름을 댄다",
    "GATE_SCOPE_WIDENED":
        "걷힌 시험이 문턱 밖으로 **늘었다** — 판정 범위가 넓어졌다. "
        "할 일: 늘어난 시험 이름을 대고, 늘어난 것이 맞으면 기준선을 갱신한다",
    "REAL_REGRESSION":
        "커밋이 움직였고 오류가 늘었다 — **코드가 원인일 자리다**. "
        "할 일: 늘어난 실패의 이름을 대고 고친다",
    "SPEEDUP_SUSPECT":
        "소요가 문턱 밖으로 **줄었다** — 아무것도 안 하면 빨리 끝난다(P-71). "
        "할 일: 시험 수가 그대로인지 먼저 본다",
    "SLOWDOWN_UNEXPLAINED":
        "소요가 문턱 밖으로 **늘었다** — 느려진 만큼 무엇이 늘었는지 이름이 필요하다",
    "UNNAMED_RED":
        "빨강인데 이름이 붙지 않았다 — **이 판정기의 결함이다**(사유 표에 빠진 갈래). "
        "할 일: `CAUSE_TEXT` 에 갈래를 추가한다",
}

#: 우선순위. **위에 있는 것이 아래를 설명한다** — 같은 커밋에서 수가 달라졌으면
#: 그 뒤의 「오류가 늘었다」는 코드 이야기가 아니다.
CAUSE_ORDER = ("ENV_UNNAMED", "BASELINE_STALE", "DIRTY_RUN", "SUITE_SHRANK",
               "GATE_SCOPE_WIDENED", "REAL_REGRESSION", "SPEEDUP_SUSPECT",
               "SLOWDOWN_UNEXPLAINED", "UNNAMED_RED")


def classify(old: dict, new: dict, threshold: float = THRESHOLD,
             head: str = "") -> list[str]:
    """빨강의 **사유 이름들** — 우선순위 순. 빨강이 아니면 빈 목록.

    `head` 를 주면 `BASELINE_STALE` 을 함께 본다(비우면 그 갈래는 판정하지 않는다 —
    git 이 없는 자리에서 「낡았다」를 지어내지 않기 위해서다).
    """
    found: set[str] = set()

    reason = (new.get("reason") or "").strip()
    named = [str(x) for x in (new.get("env") or {}).get("missing", [])]
    if "환경" in reason and not named:
        found.add("ENV_UNNAMED")

    rt = _ratio(old["tests"], new["tests"])
    rd = _ratio(old["duration_s"], new["duration_s"])
    errors_up = new["errors"] > old["errors"]
    moved = (errors_up
             or (rt is not None and abs(rt) > threshold)
             or (rd is not None and abs(rd) > threshold))

    old_c, new_c = str(old.get("commit", "")), str(new.get("commit", ""))
    if moved and old_c and new_c and old_c == new_c:
        found.add("DIRTY_RUN")
    #: ★ [P-93 · 턴 J] **커밋이 움직여도 오염은 오염이다.**
    #:
    #:   종전 판은 DIRTY_RUN 을 「두 점의 커밋이 같은데 수가 달라졌다」로만 잡았다.
    #:   그러면 **커밋이 움직인 위에 미커밋 작업본이 얹힌 벌**은 잡히지 않고
    #:   `REAL_REGRESSION`(= 코드가 원인일 자리)으로 이름 붙는다. 할 일이 갈린다:
    #:   하나는 「고친다」이고 하나는 「조용한 창에서 다시 돌린다」다.
    #:
    #:   [실측 2026-09-07 · 턴 J] 이 벌이 정확히 그랬다 — HEAD 778dad3 위에 작업본
    #:   60파일이 얹혀 있었고(차선 C 가 화면을 다시 찍는 중 · 조율자가 settings.py 를
    #:   고치는 중), 실패 9건은 전부 그 차선들의 자리였다. 커밋이 움직였다는 이유로
    #:   그것을 REAL_REGRESSION 이라 부르면 **엉뚱한 사람이 엉뚱한 것을 고치러 간다.**
    if moved and int(new.get("dirty_files") or 0) > 0:
        found.add("DIRTY_RUN")
    if moved and head and new_c and new_c != head:
        found.add("BASELINE_STALE")

    if rt is not None and rt < -threshold:
        found.add("SUITE_SHRANK")
    if rt is not None and rt > threshold:
        found.add("GATE_SCOPE_WIDENED")
    if errors_up and old_c and new_c and old_c != new_c:
        found.add("REAL_REGRESSION")
    if rd is not None and rd < -threshold:
        found.add("SPEEDUP_SUSPECT")
    if rd is not None and rd > threshold:
        found.add("SLOWDOWN_UNEXPLAINED")

    #: 빨강인데 이름이 하나도 없으면 **그 사실 자체를 이름으로 낸다.**
    if moved and not found:
        found.add("UNNAMED_RED")
    return [c for c in CAUSE_ORDER if c in found]


def judge(old: dict, new: dict, threshold: float = THRESHOLD,
          head: str = "") -> tuple[int, list[str]]:
    """`(종료코드, 말할 줄들)` — 두 점을 견준다.

    ★ **여기가 이 도구의 심장이다.** 20% 밖의 변화는 회색이 될 수 없다.
    """
    lines: list[str] = []
    red: list[str] = []

    rows = (
        ("시험 수", old["tests"], new["tests"], _ratio(old["tests"], new["tests"])),
        ("오류 수", old["errors"], new["errors"], _ratio(old["errors"], new["errors"])),
        ("소요(초)", old["duration_s"], new["duration_s"],
         _ratio(old["duration_s"], new["duration_s"])),
    )
    for name, a, b, r in rows:
        shown = "—" if r is None else f"{r:+.1%}"
        lines.append(f"{TAG}   {name:9} {a:>10,.2f} → {b:>10,.2f}   {shown:>9}")

    # ① 시험 수 — 줄어든 것을 아무도 안 본다
    r = _ratio(old["tests"], new["tests"])
    if r is not None and abs(r) > threshold:
        red.append(f"시험 수가 {r:+.1%} 움직였다 ({old['tests']:,} → {new['tests']:,}) — "
                   f"문턱 ±{threshold:.0%}. **걷힌 시험이 달라진 것은 코드가 달라진 "
                   f"것보다 먼저 봐야 한다** (0건 수집은 초록처럼 보인다)")

    # ② 오류 수 — 늘면 빨강. 앞이 0 이면 비율이 없으므로 **건수로** 본다
    if new["errors"] > old["errors"]:
        red.append(f"오류가 {old['errors']} → {new['errors']} 로 "
                   f"{new['errors'] - old['errors']}건 늘었다")

    # ③ 소요 — **이 수가 P-71 을 잡을 수 있었다**
    r = _ratio(old["duration_s"], new["duration_s"])
    if r is not None and abs(r) > threshold:
        faster = new["duration_s"] < old["duration_s"]
        why = ("**아무것도 안 하면 빨리 끝난다.** 「시험이 왜 이렇게 빨리 끝나지」는 "
               "그 자체로 신호다 (P-71)" if faster else
               "느려진 만큼 무엇이 늘었는지 이름이 필요하다")
        red.append(f"소요가 {r:+.1%} 움직였다 "
                   f"({old['duration_s']:.2f}s → {new['duration_s']:.2f}s) — {why}")

    # ④ **이름 없는 「환경」은 받지 않는다**
    reason = (new.get("reason") or "").strip()
    named = [str(x) for x in (new.get("env") or {}).get("missing", [])]
    if "환경" in reason and not named:
        red.append("사유란에 「환경」이라고 적었는데 `env` 블록에 **실패 항목의 이름이 "
                   "없다.** 이름 없는 「환경」은 받지 않는다 — 차선 셋이 그날 적은 것이 "
                   "정확히 이것이었고, 그 빨강은 우리가 만든 회귀였다 (P-71). "
                   "`python scripts/gate_env.py --require … --json env.json` 이 낸 "
                   "이름을 `--env-json` 으로 붙인다")
    elif "환경" in reason and named:
        lines.append(f"{TAG}   사유 「환경」 — 이름 있음: {', '.join(named)}")
    elif reason:
        lines.append(f"{TAG}   사유: {reason}")

    if red:
        #: ★ **사유 이름이 먼저 온다** (P-87). 「무엇이 줄었다」만 말하는 빨강은
        #:   읽은 사람의 할 일을 정해 주지 않는다.
        names = classify(old, new, threshold, head)
        lines.append(f"{TAG} **빨강 사유** {' · '.join(names)} "
                     f"(첫 사유 `{names[0]}`)")
        for nm in names:
            lines.append(f"{TAG}   `{nm}` — {CAUSE_TEXT[nm]}")
        for r_ in red:
            lines.append(f"{TAG} **빨강** {r_}")
        lines.append(f"{TAG} ±{threshold:.0%} 밖의 변화는 **회색이 될 수 없다** — "
                     "회색은 「못 쟀다」이지 「봐도 되는 변화」가 아니다")
        return EXIT_FAIL, lines

    #: ★ [P-93 · 턴 J] **HEAD 에서 잰 점이 없으면 초록이 아니라 회색이다.**
    #:
    #:   종전 판은 `BASELINE_STALE` 을 **빨강일 때만** 붙였다(`if moved and …`).
    #:   그래서 낡은 두 점이 서로 조용하면 이 도구는 **「초록」**을 냈다 —
    #:   지금 코드를 한 줄도 안 보고서. 그것이 이 저장소가 P-93 에서 96종을 훑으며
    #:   찾던 바로 그 모양이다: **판정기가 읽는 자리가 지금이 아닌데 색은 초록.**
    #:
    #:   [실측 2026-09-07 · 턴 J] HEAD 가 `778dad3` 인데 가장 최근 점은 `abbdf36`
    #:   이었고, 이 도구는 `초록` 을 냈다. 「못 쟀다」와 「봐도 된다」는 다른 말이다.
    if head and str(new.get("commit", "")) != head:
        lines.append(f"{TAG} **회색(exit 2)** — 가장 최근 점의 커밋 "
                     f"`{new.get('commit', '?')}` 이 HEAD `{head}` 가 아니다. "
                     f"셋 다 문턱 안이지만 **이 판정은 지금 코드를 안 봤다** — "
                     f"못 잰 것을 초록으로 적지 않는다 (D-301 · `BASELINE_STALE`)")
        lines.append(f"{TAG}   할 일: HEAD 에서 한 벌 돌려 `--record` 로 적고 다시 판정한다")
        return EXIT_GRAY, lines
    lines.append(f"{TAG} 초록 — 셋 다 ±{threshold:.0%} 안이고 오류가 늘지 않았다")
    return EXIT_OK, lines


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — ★ 출생 표본을 fixture 로 박는다 (D-310)
# ═══════════════════════════════════════════════════════════════════════════
#: ★ **출생 표본** — P-71 그 실행 그대로다. `docs/agent/evidence/P-71/…` 의 두 줄이고,
#:   이 도구가 있어야 했던 이유다. 여기서 초록이 나오면 이 도구는 도구가 아니다.
BIRTH_SAMPLE_BEFORE = "21 errors in 3.66s"
BIRTH_SAMPLE_AFTER = "21 passed, 34 warnings in 31.04s"


def self_test() -> int:
    bad: list[str] = []

    # ── ① 파싱 — 출생 표본의 두 줄을 글자 그대로 읽는가
    a = parse_pytest(BIRTH_SAMPLE_BEFORE)
    b = parse_pytest(BIRTH_SAMPLE_AFTER)
    if not a or (a["tests"], a["errors"], a["duration_s"]) != (21, 21, 3.66):
        bad.append(f"출생 표본 [앞] 을 못 읽었다: {a}")
    if not b or (b["tests"], b["errors"], b["duration_s"]) != (21, 0, 31.04):
        bad.append(f"출생 표본 [뒤] 를 못 읽었다: {b}")

    # ── ② ★ 출생 표본 판정 — **건강하던 그 갈래가 21 errors in 3.66s 로 바뀐 순간.**
    #        오류가 21건 늘었고 소요가 88% 줄었다. 둘 다 빨강이어야 한다.
    healthy = {"tests": 21, "errors": 0, "duration_s": 31.04}
    broken = {"tests": 21, "errors": 21, "duration_s": 3.66}
    rc, lines = judge(healthy, broken)
    text = "\n".join(lines)
    if rc != EXIT_FAIL:
        bad.append("★ **출생 표본** — 21 errors in 3.66s 가 빨강이 아니다. "
                   "이 도구는 자기가 태어난 이유를 못 본다")
    if "오류가 0 → 21" not in text:
        bad.append("출생 표본에서 오류가 21건 는 것을 말하지 않는다")
    if "소요가 -88" not in text.replace("−", "-"):
        bad.append(f"출생 표본에서 소요 -88% 를 말하지 않는다:\n{text}")

    # ── ③ 음성 — 문턱 안의 흔들림은 초록이다. 다 빨갛게 하는 도구는 꺼진다
    rc, _ = judge({"tests": 1144, "errors": 0, "duration_s": 233.5},
                  {"tests": 1150, "errors": 0, "duration_s": 245.0})
    if rc != EXIT_OK:
        bad.append("시험 +0.5% · 소요 +4.9% 는 문턱 안인데 빨강이다 — "
                   "다 빨갛게 하는 게이트는 사람이 끈다 (D-353)")

    # ── ④ **이름 없는 「환경」은 받지 않는다** — 차선 셋이 그날 적은 그것
    rc, lines = judge({"tests": 21, "errors": 0, "duration_s": 31.0},
                      {"tests": 21, "errors": 0, "duration_s": 31.2,
                       "reason": "환경 결함이지 코드 결함이 아니다", "env": {"missing": []}})
    if rc != EXIT_FAIL:
        bad.append("이름 없는 「환경」을 받아 줬다 — P-71 이 그 자리다")

    # ── ⑤ 이름 있는 「환경」은 받는다 (그리고 이름을 적는다)
    rc, lines = judge({"tests": 21, "errors": 0, "duration_s": 31.0},
                      {"tests": 21, "errors": 0, "duration_s": 31.2,
                       "reason": "환경 — MinIO 가 없다", "env": {"missing": ["minio"]}})
    if rc != EXIT_OK or "이름 있음: minio" not in "\n".join(lines):
        bad.append("이름 있는 「환경」을 거절했거나 이름을 적지 않았다")

    # ── ⑥ 견줄 점이 하나뿐이면 **회색**이지 초록이 아니다 (D-301)
    rc, _ = compare([{"suite": "x", "tests": 1, "errors": 0, "duration_s": 1.0}], "x")
    if rc != EXIT_GRAY:
        bad.append("점이 하나뿐인데 회색이 아니다 — 견줄 것이 없는데 낸 초록은 "
                   "아무것도 재지 않은 것이다 (D-301)")

    # ── ⑦ 앞이 0 인 자리에서 비율을 만들지 않는다 (0 나눗셈으로 죽지 않는다)
    rc, lines = judge({"tests": 0, "errors": 0, "duration_s": 0.0},
                      {"tests": 5, "errors": 0, "duration_s": 2.0})
    if rc != EXIT_OK:
        bad.append("앞이 0 인 자리에서 비율을 만들어 빨강을 냈다")

    # ── ⑧ ★ **모든 빨강은 이름을 가진다** (P-87 · 턴 I)
    #        이름 없는 빨강이 나오면 그것은 판정기의 결함이다. 여기가 그 자리를 지킨다.
    reds = (
        ({"tests": 21, "errors": 0, "duration_s": 31.04, "commit": "aaa"},
         {"tests": 21, "errors": 21, "duration_s": 3.66, "commit": "bbb"}),
        ({"tests": 1147, "errors": 0, "duration_s": 487.4, "commit": "e96ab7d"},
         {"tests": 1152, "errors": 4, "duration_s": 633.16, "commit": "e96ab7d"}),
        ({"tests": 1000, "errors": 0, "duration_s": 100.0, "commit": "aaa"},
         {"tests": 100, "errors": 0, "duration_s": 90.0, "commit": "bbb"}),
    )
    for a_, b2 in reds:
        rc, lines = judge(a_, b2)
        text = chr(10).join(lines)
        if rc != EXIT_FAIL:
            bad.append(f"빨강이어야 할 표본이 빨강이 아니다: {b2}")
            continue
        if "**빨강 사유**" not in text:
            bad.append(f"빨강인데 **사유 이름**이 없다: {b2}")
        if "UNNAMED_RED" in text:
            bad.append(f"사유 표에 갈래가 빠졌다(UNNAMED_RED): {b2}")

    # ── ⑨ REAL_REGRESSION 과 DIRTY_RUN 은 **같은 자리가 아니다**
    #        커밋이 움직였고 오류가 늘었다 → 코드가 원인일 자리 (고친다)
    got = classify({"tests": 21, "errors": 0, "duration_s": 31.0, "commit": "aaa"},
                   {"tests": 21, "errors": 3, "duration_s": 31.2, "commit": "bbb"})
    if got != ["REAL_REGRESSION"]:
        bad.append(f"커밋이 다른데 오류가 는 자리를 REAL_REGRESSION 이라 안 했다: {got}")
    #        커밋이 같은데 수가 달라졌다 → 코드가 원인일 수 없다 (다시 돌린다)
    got = classify({"tests": 21, "errors": 0, "duration_s": 31.0, "commit": "aaa"},
                   {"tests": 21, "errors": 3, "duration_s": 31.2, "commit": "aaa"})
    if got != ["DIRTY_RUN"]:
        bad.append(f"같은 커밋에서 수가 달라진 자리를 DIRTY_RUN 이라 안 했다: {got}")

    # ── ⑩ BASELINE_STALE 은 **HEAD 를 줬을 때만** 판정한다 (없는 사실을 짓지 않는다)
    pair = ({"tests": 21, "errors": 0, "duration_s": 31.0, "commit": "aaa"},
            {"tests": 21, "errors": 3, "duration_s": 31.2, "commit": "bbb"})
    if "BASELINE_STALE" in classify(*pair):
        bad.append("HEAD 를 주지 않았는데 BASELINE_STALE 을 지어냈다")
    if "BASELINE_STALE" not in classify(*pair, head="zzz"):
        bad.append("뒤 점이 HEAD 가 아닌데 BASELINE_STALE 을 안 냈다")
    if "BASELINE_STALE" in classify(*pair, head="bbb"):
        bad.append("뒤 점이 HEAD 인데 BASELINE_STALE 을 냈다")

    # ── ⑪ 시험 수가 준 자리와 넌 자리는 이름이 다르다
    got = classify({"tests": 1000, "errors": 0, "duration_s": 100.0, "commit": "aaa"},
                   {"tests": 100, "errors": 0, "duration_s": 95.0, "commit": "bbb"})
    if "SUITE_SHRANK" not in got or "GATE_SCOPE_WIDENED" in got:
        bad.append(f"시험 수가 준 자리를 SUITE_SHRANK 라 안 했다: {got}")
    got = classify({"tests": 100, "errors": 0, "duration_s": 100.0, "commit": "aaa"},
                   {"tests": 1000, "errors": 0, "duration_s": 105.0, "commit": "bbb"})
    if "GATE_SCOPE_WIDENED" not in got or "SUITE_SHRANK" in got:
        bad.append(f"시험 수가 는 자리를 GATE_SCOPE_WIDENED 라 안 했다: {got}")

    # ── ⑫ 초록에는 사유가 붙지 않는다 (이름이 빨강을 만들어 내면 안 된다)
    if classify({"tests": 1144, "errors": 0, "duration_s": 233.5, "commit": "aaa"},
                {"tests": 1150, "errors": 0, "duration_s": 245.0, "commit": "bbb"}):
        bad.append("문턱 안의 초록에 사유 이름이 붙었다")

    # ── ⑬ 사유 표에 구멍이 없다 — 우선순위 목록과 설명이 같은 집합인가
    if set(CAUSE_ORDER) != set(CAUSE_TEXT):
        bad.append("CAUSE_ORDER 와 CAUSE_TEXT 가 어긋난다 — "
                   "이름은 있는데 설명이 없거나 그 반대다")

    # ── ⑯ [P-93 · 턴 J] **HEAD 가 아닌 점 위의 「조용함」은 초록이 아니다** ────
    quiet_old = {"tests": 1152, "errors": 0, "duration_s": 600.0, "commit": "aaa"}
    quiet_new = {"tests": 1169, "errors": 0, "duration_s": 610.0, "commit": "bbb"}
    rc_q, _ = judge(quiet_old, quiet_new, THRESHOLD, head="zzz")
    if rc_q != EXIT_GRAY:
        bad.append(f"HEAD 가 아닌 점 위의 조용함을 초록으로 냈다 (exit {rc_q}) — "
                   "지금 코드를 안 보고 낸 초록이다")
    rc_q2, _ = judge(quiet_old, quiet_new, THRESHOLD, head="bbb")
    if rc_q2 != EXIT_OK:
        bad.append(f"HEAD 인 점 위의 조용함을 초록으로 안 냈다 (exit {rc_q2})")
    rc_q3, _ = judge(quiet_old, quiet_new, THRESHOLD, head="")
    if rc_q3 != EXIT_OK:
        bad.append("HEAD 를 모르는데 회색을 지어냈다 — 없는 사실을 짓지 않는다")

    # ── ⑮ [P-93 · 턴 J] **더러운 작업본에서 난 빨강은 DIRTY_RUN 이다** ────────
    #    커밋이 움직였어도 그렇다. 「고친다」와 「다시 돌린다」를 가르는 이름이다.
    dirty = classify({"tests": 1169, "errors": 0, "duration_s": 541.5, "commit": "aaa"},
                     {"tests": 1182, "errors": 9, "duration_s": 667.2, "commit": "bbb",
                      "dirty_files": 60})
    if "DIRTY_RUN" not in dirty:
        bad.append(f"더러운 작업본에서 난 빨강을 DIRTY_RUN 이라 안 했다: {dirty}")
    if dirty and dirty[0] != "DIRTY_RUN":
        bad.append(f"DIRTY_RUN 이 첫 사유가 아니다 — 할 일이 뒤바뀐다: {dirty}")
    clean = classify({"tests": 1169, "errors": 0, "duration_s": 541.5, "commit": "aaa"},
                     {"tests": 1182, "errors": 9, "duration_s": 667.2, "commit": "bbb",
                      "dirty_files": 0})
    if "DIRTY_RUN" in clean:
        bad.append(f"깨끗한 창인데 DIRTY_RUN 을 지어냈다: {clean}")
    if "REAL_REGRESSION" not in clean:
        bad.append(f"깨끗한 창의 오류 증가를 REAL_REGRESSION 이라 안 했다: {clean}")
    #    「모른다(-1)」를 「더럽다」로도 「깨끗하다」로도 세지 않는다
    unknown = classify({"tests": 1169, "errors": 0, "duration_s": 541.5, "commit": "aaa"},
                       {"tests": 1182, "errors": 9, "duration_s": 667.2, "commit": "bbb",
                        "dirty_files": -1})
    if "DIRTY_RUN" in unknown:
        bad.append(f"작업본 상태를 모르는데 DIRTY_RUN 을 지어냈다: {unknown}")
    #    초록에는 더러워도 이름이 안 붙는다 (이름이 빨강을 만들어 내면 안 된다)
    if classify({"tests": 1169, "errors": 0, "duration_s": 541.5, "commit": "aaa"},
                {"tests": 1170, "errors": 0, "duration_s": 545.0, "commit": "bbb",
                 "dirty_files": 60}):
        bad.append("문턱 안의 초록에 DIRTY_RUN 이 붙었다")

    # ── ⑭ [P-93 · 턴 J] **안 옮기기로 한 것도 사유가 남는다** ─────────────────
    #    `append_note` 는 사유만 적고 `runs` 를 늘리지 않는다. 늘리면 그것이 곧
    #    「적지 않기로 한 벌을 적은 것」이고, 다음 턴이 그 점과 견주게 된다.
    d0 = {"schema": 1, "runs": [{"suite": "s", "tests": 1}], "baseline_notes": []}
    d1 = append_note(dict(d0), "오염된 벌이라 안 적는다", commit="abc", at="2026-09-07T00:00:00+00:00")
    if len(d1["runs"]) != 1:
        bad.append("append_note 가 runs 를 건드렸다 — 사유만 적어야 한다")
    if len(d1["baseline_notes"]) != 1 or "안 적는다" not in d1["baseline_notes"][0]["why"]:
        bad.append("append_note 가 사유를 안 적었다")
    d2 = append_note(d1, "두 번째 사유", commit="abc", at="2026-09-07T00:01:00+00:00")
    if len(d2["baseline_notes"]) != 2:
        bad.append("사유가 덮어써졌다 — 사유는 쌓이는 것이지 갈리는 것이 아니다")

    for b_ in bad:
        print(f"{TAG} 자기시험 FAIL {b_}")
    if bad:
        print(f"{TAG} 자기시험 {len(bad)}건 실패 — 판정기를 먼저 의심한다 (D-350)")
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — ★ **출생 표본**(21 errors in 3.66s → 빨강) 포함 "
          f"갈래 16 · 사유 이름 {len(CAUSE_ORDER)}종 "
          f"({' · '.join(CAUSE_ORDER)})")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def runs_of(runs: list[dict], suite: str) -> list[dict]:
    return [r for r in runs if r.get("suite") == suite]


def compare(runs: list[dict], suite: str, head: str = "") -> tuple[int, list[str]]:
    """한 갈래의 **가장 최근 두 점**을 견준다."""
    mine = runs_of(runs, suite)
    if len(mine) < 2:
        return EXIT_GRAY, [
            f"{TAG} **못 쟀다** — 갈래 `{suite}` 의 점이 {len(mine)}개다. "
            "견줄 것이 없다. 다음 실행을 `--record` 로 적으면 그때 판정한다 "
            "(견줄 것 없이 내는 초록은 아무것도 재지 않은 것이다 · D-301)"]
    old, new = mine[-2], mine[-1]
    head_lines = [f"{TAG} 갈래 `{suite}` — "
            f"{old.get('commit', '?')}({old.get('recorded_at', '?')[:16]}) → "
            f"{new.get('commit', '?')}({new.get('recorded_at', '?')[:16]})"]
    rc, lines = judge(old, new, THRESHOLD, head)
    return rc, head_lines + lines


def main() -> int:
    ap = argparse.ArgumentParser(description="P-79 — 직전 커밋 대비 시험 델타 판정기")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--record", action="store_true", help="실행 한 벌을 기준선에 적는다")
    ap.add_argument("--suite", default="", help="갈래 이름 (예: backend-unit)")
    ap.add_argument("--from-file", default="", help="pytest 출력이 담긴 파일")
    ap.add_argument("--command", default="", help="그 실행을 만든 명령 (그대로 적는다)")
    ap.add_argument("--commit", default="", help="비우면 현재 HEAD")
    ap.add_argument("--reason", default="", help="사유. 「환경」이면 --env-json 이 필요하다")
    ap.add_argument("--env-json", default="", help="gate_env.py --json 이 낸 파일")
    ap.add_argument("--note", default="")
    ap.add_argument("--baseline-why", default="",
                    help="기준선을 이 실행으로 갱신하는 **사유**. 파일에 남고 판정 때 읽힌다")
    ap.add_argument("--baseline-note", default="",
                    help="**점을 안 적고 사유만** 적는다 — 기준선을 옮기지 않기로 한 판단의 사유")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    data = load()
    runs: list[dict] = data.get("runs", [])

    #: ★ 안 옮기기로 한 것도 판단이고, 판단에는 사유가 있어야 한다 (P-93 · 턴 J).
    if args.baseline_note:
        if args.record:
            print(f"{TAG} --baseline-note 와 --record 를 같이 쓰지 않는다 — "
                  "적을 거면 `--baseline-why` 가 그 자리다")
            return EXIT_GRAY
        at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        save(append_note(data, args.baseline_note, commit=args.commit or head_commit(), at=at))
        print(f"{TAG} [사유] 기준선을 **옮기지 않았고** 사유를 적었다 — "
              f"{BASELINE.relative_to(ROOT).as_posix()}")
        print(f"{TAG}   {args.baseline_note}")
        return EXIT_OK

    if args.record:
        if not args.suite or not args.from_file:
            print(f"{TAG} --record 에는 --suite 와 --from-file 이 필요하다")
            return EXIT_GRAY
        text = Path(args.from_file).read_text(encoding="utf-8", errors="replace")
        got = parse_pytest(text)
        if got is None:
            print(f"{TAG} **못 읽었다** — {args.from_file} 에서 pytest 요약 줄을 "
                  "못 찾았다. 실행이 요약을 적기 전에 끊겼을 수 있다 "
                  "(끊긴 실행을 0건으로 적으면 그것이 다음 판정의 근거가 된다)")
            return EXIT_GRAY
        env: dict = {"missing": [], "checked": []}
        if args.env_json:
            raw = json.loads(Path(args.env_json).read_text(encoding="utf-8"))
            env = {"missing": raw.get("missing", []),
                   "checked": [r.get("name") for r in raw.get("rows", [])]}
        row = {
            "suite": args.suite,
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "commit": args.commit or head_commit(),
            "command": args.command,
            "tests": got["tests"],
            "errors": got["errors"],
            "duration_s": got["duration_s"],
            "counts": got["counts"],
            "summary_line": got["summary_line"],
            "source": "기계",
            "reason": args.reason,
            "env": env,
            "note": args.note,
            #: ★ 잰 순간의 작업본 상태를 **점과 함께** 적는다 (P-93 · 턴 J).
            #:   나중에 기억으로 복원할 수 없는 사실이고, 이것이 없으면 오염된 벌이
            #:   `REAL_REGRESSION` 으로 이름 붙는다.
            "dirty_files": dirty_files(),
        }
        runs.append(row)
        if args.baseline_why:
            notes = list(data.get("baseline_notes") or [])
            notes.append({"at": row["recorded_at"], "commit": row["commit"],
                          "why": args.baseline_why})
            data["baseline_notes"] = notes
        data["runs"] = runs
        data["threshold"] = THRESHOLD
        data["schema"] = 1
        save(data)
        print(f"{TAG} [입력] 1건 적었다 — `{args.suite}` {row['commit']} · "
              f"시험 {row['tests']:,} · 오류 {row['errors']} · "
              f"소요 {row['duration_s']:.2f}s")
        print(f"{TAG} 기준선 → {BASELINE.relative_to(ROOT).as_posix()} "
              f"(총 {len(runs)}점)")
        return EXIT_OK

    suites = sorted({r.get("suite", "?") for r in runs})
    print(f"{TAG} [입력] {len(runs)}점 · 갈래 {len(suites)}종 "
          f"({', '.join(suites) or '없음'}) · 문턱 ±{THRESHOLD:.0%}")
    #: ★ [P-87 · 턴 I] **기준선을 갱신한 사유는 파일 안에 있고, 여기서 읽어 말한다.**
    #:   갱신 사유가 파일에만 있고 아무도 안 읽으면 그것은 없는 것과 같다 —
    #:   다음 사람은 「왜 이 두 점을 견주고 있는가」를 모른 채 색만 본다.
    for note in (data.get("baseline_notes") or [])[-2:]:
        print(f"{TAG} [기준선 갱신] {note.get('at', '?')[:19]} · "
              f"{note.get('why', '(사유 없음)')}")
    if not runs:
        print(f"{TAG} **못 쟀다** — 기준선이 비어 있다. `--record` 로 첫 점을 적는다 "
              "(0점 판정과 판정 못 함은 다르다 · D-301)")
        return EXIT_GRAY

    if args.list:
        for r in runs:
            print(f"{TAG}   {r.get('suite'):14} {r.get('commit', '?'):9} "
                  f"{r.get('recorded_at', '')[:19]}  시험 {r.get('tests', 0):>6,} · "
                  f"오류 {r.get('errors', 0):>3} · {r.get('duration_s', 0):>8.2f}s")

    worst = EXIT_OK
    head = head_commit()
    if head == "알 수 없음":
        head = ""
    for suite in ([args.suite] if args.suite else suites):
        rc, lines = compare(runs, suite, head)
        for ln in lines:
            print(ln)
        if rc == EXIT_FAIL:
            worst = EXIT_FAIL
        elif rc == EXIT_GRAY and worst == EXIT_OK:
            worst = EXIT_GRAY
    return worst


if __name__ == "__main__":
    from _gate_header import gate_header, file_stamp  # P-107 — TARGET/AS/SOURCE
    from _gate_header import count_json as _cj
    _n_runs = _cj(BASELINE, "runs")
    gate_header(
        __file__,
        measured=("이번 시험 출력의 **네 수**(passed·failed·error·skipped)를 "
                  "기준선의 마지막 실행과 댄다 — **분모 %s번**(`delta_baseline.json"
                  "::runs` 에 쌓인 실행 · 지금 셌다) · 문턱 %.0f%%. 기준선을 못 "
                  "읽으면 **댈 것이 없고**, 댈 것 없는 초록은 초록이 아니다"
                  % (_n_runs if _n_runs else "못 셌다", THRESHOLD * 100)),
        target="--command 로 준 시험 명령의 출력 (기본은 gx-shell 안 pytest)",
        as_="(계정 없음) — 시험 러너가 낸 요약 줄을 읽는다",
        source="이번에 돌린 시험 출력 + " + file_stamp(BASELINE),
    )
    raise SystemExit(main())
