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

종료 코드: **0 초록 · 1 빨강 · 2 회색(견줄 점이 없다)**.
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


def judge(old: dict, new: dict, threshold: float = THRESHOLD) -> tuple[int, list[str]]:
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
        for r_ in red:
            lines.append(f"{TAG} **빨강** {r_}")
        lines.append(f"{TAG} ±{threshold:.0%} 밖의 변화는 **회색이 될 수 없다** — "
                     "회색은 「못 쟀다」이지 「봐도 되는 변화」가 아니다")
        return EXIT_FAIL, lines
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

    for b_ in bad:
        print(f"{TAG} 자기시험 FAIL {b_}")
    if bad:
        print(f"{TAG} 자기시험 {len(bad)}건 실패 — 판정기를 먼저 의심한다 (D-350)")
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — ★ **출생 표본**(21 errors in 3.66s → 빨강) 포함 "
          f"갈래 7")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def runs_of(runs: list[dict], suite: str) -> list[dict]:
    return [r for r in runs if r.get("suite") == suite]


def compare(runs: list[dict], suite: str) -> tuple[int, list[str]]:
    """한 갈래의 **가장 최근 두 점**을 견준다."""
    mine = runs_of(runs, suite)
    if len(mine) < 2:
        return EXIT_GRAY, [
            f"{TAG} **못 쟀다** — 갈래 `{suite}` 의 점이 {len(mine)}개다. "
            "견줄 것이 없다. 다음 실행을 `--record` 로 적으면 그때 판정한다 "
            "(견줄 것 없이 내는 초록은 아무것도 재지 않은 것이다 · D-301)"]
    old, new = mine[-2], mine[-1]
    head = [f"{TAG} 갈래 `{suite}` — "
            f"{old.get('commit', '?')}({old.get('recorded_at', '?')[:16]}) → "
            f"{new.get('commit', '?')}({new.get('recorded_at', '?')[:16]})"]
    rc, lines = judge(old, new)
    return rc, head + lines


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
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    data = load()
    runs: list[dict] = data.get("runs", [])

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
        }
        runs.append(row)
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
    for suite in ([args.suite] if args.suite else suites):
        rc, lines = compare(runs, suite)
        for ln in lines:
            print(ln)
        if rc == EXIT_FAIL:
            worst = EXIT_FAIL
        elif rc == EXIT_GRAY and worst == EXIT_OK:
            worst = EXIT_GRAY
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
