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

c 의 출처 — **`--c-rows` 하나뿐이다 (P-422 → P-433)**
-------------------------------------------------------------------
★ [P-422 · 턴 AP] 옛 기본 동작은 `onboarding_48.md` 를 자동으로 훑어 문서 전체의
`**(c)**` 행을 모았다 — 30/48 을 30/32(93.8%)로 찍은 거짓 초록. 그래서 기본을 막고
명시 옵션 `--c-from-ledger` 만 남겼다.
★ [P-433 · 턴 AQ · 차선 Q] 그 명시 옵션이 **또** 거짓 초록(107.8)을 냈다 — 기본을
막으니 명시 옵션이 뚫렸다. **옵션 자체를 없앴다.** 이 도구는 장부를 읽지 않는다.
장부의 c 표는 「최신 회차 하나」이고, V 가 그 최신 c 를 `--c-rows` 로 옮겨 적는다
(손으로 늘리지 않는다 · 늘면 L 의 결정 번호가 있어야). `--c-from-ledger` 를 주면
argparse 가 오류(exit 2)를 낸다.

`--c-rows` 가 없으면 c=0 이 아니라 **「c 미명시」**(회색)다 — c=0(「표를 봤는데
없더라」)과는 다른 뜻이므로 문장을 갈랐다(빈 것을 0 으로 지어내지 않는다 · D-301).

쓰는 법
-------
    python scripts/onboarding_two_numbers.py --self-test          # 순수 함수 (파일 없이)
    docker exec gx-shell python /repo/scripts/onboarding_two_numbers.py
        # ↑ 기본 호출 — ①만 찍는다. ②는 「회색 · c 미명시」(숫자를 안 짓는다).
    docker exec gx-shell python /repo/scripts/onboarding_two_numbers.py \\
        --turn-file docs/agent/evidence/ONB-T/turn_an_7.json \\
        --c-rows U1#4,U1#8,U1#11,U2#2,U2#6,U2#16,U3#7,U3#14,U4#11,U4#15,U4#9,U6#4,U1#2,U2#4,U4#8,U5#2

종료 코드: 0 두 수를 다 찍었다 · 1 회차 JSON 을 못 읽었다(찍을 것이 없다) · 2 `--self-test` 실패.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_SELFTEST_FAIL = 0, 1, 2

TAG = "[ONB-2N]"

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TURN_GLOB = str(ROOT / "docs" / "agent" / "evidence" / "ONB-T" / "turn_*.json")


# ═══════════════════════════════════════════════════════════════════════════
# 순수 함수 — 파일 I/O 없이 문자열·dict 만 받는다(`--self-test` 가 이것만 잰다)
# ═══════════════════════════════════════════════════════════════════════════

def parse_c_rows_arg(raw: str) -> set[str]:
    """`--c-rows U1#2,U2#3` → `{"U1#2", "U2#3"}`. 빈 조각은 버린다."""
    return {p.strip() for p in (raw or "").split(",") if p.strip()}


#: [P-433 · 턴 AQ · 차선 Q] c 의 출처는 `--c-rows` 하나 — 장부를 읽는 갈래는 없다.
def resolve_c_rows(*, c_rows_arg: str | None) -> tuple[set[str], str]:
    """c 행 집합과 출처 문장. `--c-rows` 가 없으면 아무 행도 안 뺀다(「c 미명시」)."""
    if c_rows_arg is not None:
        return parse_c_rows_arg(c_rows_arg), "--c-rows(손으로 줌)"
    return set(), (
        "c 미명시 — 이 도구는 장부(onboarding_48.md)를 읽지 않는다(P-433). "
        "장부 최신 회차의 c 행을 --c-rows 로 옮겨 준다")



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
        #: [P-422] c 출처(c_source)를 여기서도 적는다 — 「c=0(표를 봤는데 없더라)」과
        #: 「c 미명시(기본 호출 · 아무 인자도 안 줌)」는 다른 뜻이라 섞으면 안 된다.
        lines.append(
            "%s ② 상한 기준  회색 · (못 찍음 · c 출처: %s) — %s"
            % (TAG, c_source, out["cap_undefined_why"]))
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
    ap.add_argument("--c-rows", default=None,
                    help="쉼표로 구분한 (c) 행 id — 장부 최신 회차의 c 를 옮겨 준다(P-433 · "
                        "장부를 읽는 옵션은 없다)")
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

    c_rows, c_source = resolve_c_rows(c_rows_arg=args.c_rows)

    out = two_numbers(score_sum=turn["score_sum"], denominator=turn["denominator"],
                      c_rows=c_rows, canon_rows=turn["canon_rows"])
    print(render(out, turn_source=turn["source"], c_source=c_source))
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# --self-test — Django 도 저장소 파일도 없이 순수 함수만 잰다
# ═══════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    failures: list[str] = []

    total = [0]

    def check(name: str, cond: bool) -> None:
        total[0] += 1
        if not cond:
            failures.append(name)

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

    # ⑧ [P-433] 기본(--c-rows 없음)은 아무 행도 안 뺀다 — 「c 미명시」
    default_rows, default_src = resolve_c_rows(c_rows_arg=None)
    check("기본 호출은 c 행을 하나도 안 뺀다", default_rows == set())
    check("기본 호출 출처 문장은 「c 미명시」", "미명시" in default_src)

    # ⑨ ⑧과 짝 — 기본 c_rows(빈 집합)를 먹이면 상한 줄이 회색(None)이어야 한다.
    default_out = two_numbers(score_sum=30.0, denominator=48, c_rows=default_rows)
    check("기본 호출은 상한 수를 안 낸다(by_cap=None)", default_out["by_cap"] is None)
    check("render() 가 기본 호출의 c 출처를 「c 미명시」로 찍는다",
         "미명시" in render(default_out, turn_source="t.json", c_source=default_src))

    # ⑩ --c-rows 만이 c 의 출처다
    manual_rows, manual_src = resolve_c_rows(c_rows_arg="U2#2,U2#3")
    check("--c-rows 가 c 행이다", manual_rows == {"U2#2", "U2#3"})
    check("--c-rows 출처 문장", manual_src == "--c-rows(손으로 줌)")

    # ⑪ ★ 출생 표본 [P-433 · 턴 AP V 실측] — `--c-from-ledger` 가 107.8 이라는 거짓 초록을
    #    냈다. 그 옵션은 **없어야** 한다: 주면 argparse 가 거절(SystemExit 2)해야 한다.
    import contextlib  # noqa: PLC0415
    import io as _io  # noqa: PLC0415
    code = None
    with contextlib.redirect_stderr(_io.StringIO()):
        try:
            main(["--c-from-ledger"])
        except SystemExit as exc:
            code = exc.code
    check("★ --c-from-ledger 를 주면 argparse 오류(exit 2)", code == 2)
    check("resolve_c_rows 에 장부 갈래 인자가 없다",
         "c_from_ledger" not in resolve_c_rows.__code__.co_varnames)


    if failures:
        print("%s --self-test 실패 %d건: %s" % (TAG, len(failures), failures))
        return EXIT_SELFTEST_FAIL
    print("%s --self-test 통과 %d건" % (TAG, total[0]))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
