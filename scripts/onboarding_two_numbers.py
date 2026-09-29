#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-408 — 온보딩 완료율 **두 수**를 함께 찍는다 (턴 AO · 차선 Q).

왜 둘인가
---------
`docs/agent/onboarding_48.md` 는 「48 기준」한 수만 정본으로 적어 왔다
(`30.0 / 48 = 62.5%`). 그런데 턴 AN 의 갈래표(P-396)가 48행 중 16행을
**(c) dj-core/§0.4 밖**(금지구역·인수 자산·계약 11조 설계 잠금·표본/데이터
상태·환경변수 배선 — 이 저장소의 어느 차선도 코드로 못 올리는 행)으로 갈랐다.
48 을 분모로 두면 **애초에 못 오르는 16행**이 매 회차 상한을 깎아먹는 채로
「완료율」이 읽히고, 그러면 코드가 실제로 닿을 수 있는 상한(48−c)에 얼마나
가까운지가 안 보인다. 그래서 **둘 다** 찍는다 — 한쪽만 찍는 경로는 없다:

    ① 48 기준        N / 48
    ② 상한 기준      N / (48 − c)

**N 은 둘이 같다.** 갈라지는 것은 분모뿐이다 — (c) 행이 오르지 않았다고 해서
그 행의 점수를 N 에서 빼지 않는다(둘 다 「지금 딴 점수」를 그대로 쓴다). c 를
바꿔 N 을 다시 계산하면 「상한을 낮췄더니 점수도 오른」 것처럼 보이는 착시가
생긴다 — 이 도구는 그 착시를 만들지 않는다.

N 의 출처 — **회차 JSON, 손으로 안 더한다**
--------------------------------------------
`docs/agent/evidence/ONB-T/turn_*.json` (예: `turn_an_7.json`)의 `score_sum` ·
`denominator` 를 그대로 읽는다(`measure_onboarding_t.py` 가 이미 세어 둔 값 —
두 벌로 세면 어긋난다 · D-212). 여러 파일이 있으면 **가장 최근 `measured_at`**
을 고른다(`--turn-file` 로 못박을 수 있다).

c 의 출처 — **onboarding_48.md 의 `**(c)**` 표, 손으로 안 센다**
-------------------------------------------------------------------
L 차선이 이 턴에 표에 붙이는 `| 행 | ... | **(c)** | ... |` 행을 정규식으로
센다(행 id 로 중복 제거 — 같은 행이 여러 재측 절에 반복돼도 한 번만 센다).
L 이 아직 표를 못 붙였으면(또는 다른 셈을 쓰고 싶으면) `--c-rows U1#2,U2#3,...`
로 **직접 준다** — 주면 표를 안 읽고 그 목록만 쓴다. 파일도 없고 `--c-rows`
도 없으면 c=0 으로 찍되, **c=0 이 「상한 없음」이 아니라 「못 찾았다」임을
문장에 적는다**(빈 것을 0 으로 지어내지 않는다 · D-301).

쓰는 법
-------
    python scripts/onboarding_two_numbers.py --self-test          # 순수 함수 (파일 없이)
    docker exec gx-shell python /repo/scripts/onboarding_two_numbers.py
    docker exec gx-shell python /repo/scripts/onboarding_two_numbers.py \\
        --turn-file docs/agent/evidence/ONB-T/turn_an_7.json \\
        --c-rows U1#4,U1#8,U1#11,U2#2,U2#6,U2#16,U3#7,U3#14,U4#11,U4#15,U4#9,U6#4,U1#2,U2#4,U4#8,U5#2

종료 코드: 0 두 수를 다 찍었다 · 1 회차 JSON 을 못 읽었다(찍을 것이 없다) · 2 `--self-test` 실패.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_SELFTEST_FAIL = 0, 1, 2

TAG = "[ONB-2N]"

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TURN_GLOB = str(ROOT / "docs" / "agent" / "evidence" / "ONB-T" / "turn_*.json")
DEFAULT_ONBOARDING_MD = ROOT / "docs" / "agent" / "onboarding_48.md"

#: 표의 행 id 칸 — `| U1#4 \`/multi-stream-monitor\` | ... |` 의 맨 앞 칸.
_ROW_ID_RE = re.compile(r"^\|\s*(U\d#\d+)\b")


# ═══════════════════════════════════════════════════════════════════════════
# 순수 함수 — 파일 I/O 없이 문자열·dict 만 받는다(`--self-test` 가 이것만 잰다)
# ═══════════════════════════════════════════════════════════════════════════

def c_rows_from_markdown(text: str) -> set[str]:
    """`onboarding_48.md` 본문에서 `**(c)**` 로 갈린 행 id 를 모은다.

    같은 행이 여러 재측 절(턴마다 표가 또 있다)에 반복돼도 **id 로만** 모으므로
    한 번만 센다 — 어느 절의 것이든 (c) 로 적힌 적이 있으면 상한 표에 든다.
    """
    ids: set[str] = set()
    for line in text.splitlines():
        if "**(c)**" not in line:
            continue
        m = _ROW_ID_RE.match(line)
        if m:
            ids.add(m.group(1))
    return ids


def parse_c_rows_arg(raw: str) -> set[str]:
    """`--c-rows U1#2,U2#3` → `{"U1#2", "U2#3"}`. 빈 조각은 버린다."""
    return {p.strip() for p in (raw or "").split(",") if p.strip()}


def two_numbers(*, score_sum: float, denominator: int, c_rows: set[str],
                canon_rows: set[str] | None = None) -> dict:
    """N·48·c 로 두 수를 만든다. **분자는 하나뿐이다** — 위 머리말 참고.

    `canon_rows` 를 주면 `c_rows` 를 그 집합과 **교집합**으로 좁힌다 — 오타·
    지난 회차 행 이름이 섞여 상한을 잘못 깎는 것을 막는다(모르는 행은 안 뺀다).
    """
    if canon_rows:
        known = c_rows & canon_rows
        unknown = c_rows - canon_rows
    else:
        known, unknown = set(c_rows), set()
    c = len(known)
    cap_denominator = denominator - c
    out = {
        "n": score_sum,
        "denominator_48": denominator,
        "by_48": "%s/%d" % (_fmt(score_sum), denominator),
        "by_48_pct": _pct(score_sum, denominator),
        "c": c,
        "c_rows": sorted(known),
        "c_rows_unknown": sorted(unknown),
        "cap_denominator": cap_denominator,
        "by_cap": None,
        "by_cap_pct": None,
        "cap_undefined_why": "",
    }
    if c == 0:
        out["cap_undefined_why"] = (
            "c=0 — 상한 표를 못 찾았다(onboarding_48.md 에 **(c)** 행이 없거나 "
            "--c-rows 를 안 줬다). 「상한이 없다」는 별개의 주장이니 지어내지 않는다")
        return out
    if cap_denominator <= 0:
        out["cap_undefined_why"] = (
            "48 - c(%d) = %d — 분모가 0 이하다. c 목록을 다시 본다"
            % (c, cap_denominator))
        return out
    out["by_cap"] = "%s/%d" % (_fmt(score_sum), cap_denominator)
    out["by_cap_pct"] = _pct(score_sum, cap_denominator)
    return out


def _fmt(n: float) -> str:
    return ("%g" % n) if n == int(n) else ("%.1f" % n)


def _pct(numerator: float, denominator: int) -> str:
    if not denominator:
        return "?"
    return "%.1f%%" % (100.0 * numerator / denominator)


def render(out: dict, *, turn_source: str, c_source: str) -> str:
    lines = [
        "%s N=%s(출처: %s)" % (TAG, _fmt(out["n"]), turn_source),
        "%s ① 48 기준   %s = %s" % (TAG, out["by_48"], out["by_48_pct"]),
    ]
    if out["by_cap"] is None:
        lines.append("%s ② 상한 기준  (못 찍음) — %s" % (TAG, out["cap_undefined_why"]))
    else:
        lines.append(
            "%s ② 상한 기준  %s = %s  (48 - c=%d · 출처: %s)"
            % (TAG, out["by_cap"], out["by_cap_pct"], out["c"], c_source))
    if out["c_rows"]:
        lines.append("%s   c 행(%d) %s" % (TAG, out["c"], ", ".join(out["c_rows"])))
    if out["c_rows_unknown"]:
        lines.append(
            "%s   ⚠ 회차 JSON 의 48행에 없는 c 이름 — 상한 계산에서 뺐다: %s"
            % (TAG, ", ".join(out["c_rows_unknown"])))
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# 파일 I/O — 위 순수 함수에 무엇을 먹일지만 정한다
# ═══════════════════════════════════════════════════════════════════════════

def _latest_turn_file(pattern: str) -> Path | None:
    candidates = [Path(p) for p in glob.glob(pattern)]
    if not candidates:
        return None

    def _key(p: Path):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            return (doc.get("measured_at") or "", p.name)
        except Exception:                               # noqa: BLE001
            return ("", p.name)

    return max(candidates, key=_key)


def load_turn(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    score_sum = doc.get("score_sum")
    denominator = doc.get("denominator")
    if score_sum is None or denominator is None:
        raise ValueError(
            "%s 에 score_sum/denominator 가 없다 — measure_onboarding_t.py 산출물이 맞는가"
            % path)
    canon = set(doc.get("canon_two_column") or [r["row"] for r in doc.get("rows", [])])
    return {"score_sum": float(score_sum), "denominator": int(denominator),
           "canon_rows": canon, "source": str(path)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--turn-file", default=None,
                    help="회차 JSON 경로. 안 주면 %s 중 가장 최근 measured_at" % DEFAULT_TURN_GLOB)
    ap.add_argument("--turn-glob", default=DEFAULT_TURN_GLOB)
    ap.add_argument("--onboarding-md", default=str(DEFAULT_ONBOARDING_MD))
    ap.add_argument("--c-rows", default=None,
                    help="쉼표로 구분한 (c) 행 id — 주면 onboarding_48.md 를 안 읽는다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    turn_path = Path(args.turn_file) if args.turn_file else _latest_turn_file(args.turn_glob)
    if turn_path is None or not turn_path.is_file():
        print("%s 회차 JSON 을 못 찾았다 — %s (또는 --turn-file)"
              % (TAG, args.turn_glob))
        return EXIT_FAIL
    try:
        turn = load_turn(turn_path)
    except Exception as exc:                            # noqa: BLE001
        print("%s 회차 JSON을 못 읽었다 — %s: %s" % (TAG, type(exc).__name__, exc))
        return EXIT_FAIL

    if args.c_rows is not None:
        c_rows = parse_c_rows_arg(args.c_rows)
        c_source = "--c-rows(손으로 줌)"
    else:
        md_path = Path(args.onboarding_md)
        if md_path.is_file():
            c_rows = c_rows_from_markdown(md_path.read_text(encoding="utf-8"))
            c_source = str(md_path)
        else:
            c_rows = set()
            c_source = "%s 없음 — --c-rows 도 안 줬다" % md_path

    out = two_numbers(score_sum=turn["score_sum"], denominator=turn["denominator"],
                      c_rows=c_rows, canon_rows=turn["canon_rows"])
    print(render(out, turn_source=turn["source"], c_source=c_source))
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# --self-test — Django 도 저장소 파일도 없이 순수 함수만 잰다
# ═══════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    # ① 표에서 (c) 행을 뽑는다 — 중복 id 는 한 번만
    md = (
        "| U1#4 `/x` | 증거 | **(c)** | 비고 |\n"
        "| U1#9 `/y` | 증거 | **(a)** | 비고 — (c) 라는 낱말이 비고에 있어도 갈래 칸이 아니면 안 센다 |\n"
        "| U1#4 `/x` | 다른 절의 같은 행 | **(c)** | 재측에도 또 (c) |\n"
        "| U2#3 `/z` | 증거 | **(c)** | 비고 |\n"
    )
    rows = c_rows_from_markdown(md)
    check("표에서 (c) 행 셋을 뽑는다(중복 제거)", rows == {"U1#4", "U2#3"})

    # ② --c-rows 파싱
    check("--c-rows 콤마 목록을 자른다",
         parse_c_rows_arg(" U1#2, U2#3 ,, U3#9") == {"U1#2", "U2#3", "U3#9"})
    check("빈 문자열은 빈 집합", parse_c_rows_arg("") == set())

    # ③ 두 수 — 분자는 하나, 분모만 갈린다
    out = two_numbers(score_sum=30.0, denominator=48,
                      c_rows={"U1#4", "U1#8", "U1#11"},
                      canon_rows={"U1#4", "U1#8", "U1#11", "U1#2"})
    check("① 48 기준 문자열", out["by_48"] == "30/48")
    check("② 상한 기준 분모 = 48-3", out["cap_denominator"] == 45)
    check("② 상한 기준 문자열", out["by_cap"] == "30/45")
    check("분자가 갈리지 않는다(N 은 하나)", out["n"] == 30.0)
    check("퍼센트 계산", out["by_48_pct"] == "62.5%")

    # ④ c=0(상한 표를 못 찾음)이면 ②를 지어내지 않는다
    zero = two_numbers(score_sum=10.0, denominator=48, c_rows=set())
    check("c=0 이면 by_cap 이 None", zero["by_cap"] is None)
    check("c=0 사유 문장이 있다", "못 찾았다" in zero["cap_undefined_why"])

    # ⑤ 회차 JSON 에 없는 c 행 이름은 상한 계산에서 빠지고 따로 보고된다
    mixed = two_numbers(score_sum=30.0, denominator=48,
                        c_rows={"U1#4", "U9#99"}, canon_rows={"U1#4", "U1#8"})
    check("모르는 c 행은 뺀다", mixed["c"] == 1)
    check("모르는 c 행은 따로 보고된다", mixed["c_rows_unknown"] == ["U9#99"])

    # ⑥ 분모가 0 이하로 떨어지면 ②를 지어내지 않는다(경계)
    over = two_numbers(score_sum=5.0, denominator=6, c_rows={"A#1", "A#2", "A#3",
                                                            "A#4", "A#5", "A#6"},
                       canon_rows={"A#1", "A#2", "A#3", "A#4", "A#5", "A#6"})
    check("48-c<=0 이면 by_cap 이 None", over["by_cap"] is None)

    # ⑦ 소수 없는 N 은 정수로, 소수 있는 N 은 .1f 로 찍는다
    check("정수 N 서식", _fmt(30.0) == "30")
    check("소수 N 서식", _fmt(29.5) == "29.5")

    if failures:
        print("%s --self-test 실패 %d건: %s" % (TAG, len(failures), failures))
        return EXIT_SELFTEST_FAIL
    print("%s --self-test 통과 %d건" % (TAG, 7))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
