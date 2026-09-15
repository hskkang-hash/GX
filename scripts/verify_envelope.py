#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-349 착시 ⑧ — **봉투.** 겉의 200 이 안의 403 을 덮는다.

무슨 일이 있었나 (출생 표본 · D-310)
------------------------------------
    [실측 2026-09-08] 익명 호출 판정에서 **18건을 데이터 반출로 셌다.**
    그 18건은 HTTP **200** 이었고 본문은
        {"success": false, "message": {...}, "status_code": 403}
    였다 — **봉투는 200, 내용은 403.** 판정기가 봉투만 읽었다.
    내용을 읽게 고친 뒤 진짜 반출은 **11건**이었다.

★ 이건 판정기의 결함만이 아니라 **제품의 결함**이다
    오류를 HTTP 200 안에 담아 보내는 API 는 바깥의 모두를 속인다:
      · 게이트웨이·프록시가 실패를 성공으로 집계한다
      · 모니터링이 오류율 0% 를 보고한다
      · 클라이언트 라이브러리가 예외를 던지지 않고, 재시도 로직이 돌지 않는다
      · **그리고 우리 판정기도 속았다 — 우리가 첫 피해자였다**
    F-05 진입면이 이런 응답을 내면 **에스비 App 이 실패를 성공으로 읽는다. 계약 사고다.**

★ 술어를 한 번 좁혔다 (D-350 — 놀라운 수가 나오면 측정기를 먼저 의심한다)
--------------------------------------------------------------------------
처음에 `status_code=4xx` 를 grep 해 **564건**을 셌다. 놀라운 수였고, **틀렸다** —
그 대부분은 `BaseResponse(status_code=404)` 인데 그 클래스는 `JsonResponse` 를 상속하고
`super().__init__(..., status=status_code)` 를 부른다. **HTTP 상태가 따라간다.**
갈리는 것은 **Response 로 감싸지 않고 dict 를 그대로 돌려줄 때**뿐이다.
좁히고 나니 갈래는 둘이고, 이 저장소의 봉투 불일치는 사실상 **하나의 뿌리**에서 나온다:
dj-core `path_permission` 이 `{"success": False, "status_code": 403}` 을 그대로 돌려준다(§0.4).

무엇을 보는가 — 셋
------------------
  ① **승격 경로는 갈리지 않는다** — `API_CONTRACT_PROMOTE_PATHS`(기본 `/api/dsm/`) 아래
     라우트의 봉투 상태가 `promoted` 가 아니면 exit 1. **F-05 는 래칫에서 제외다**(D-349 ③)
  ② **나머지는 래칫**(D-311) — 오늘의 불일치 건수를 잠그고 **늘어나는 것만** 막는다.
     소급 수정 금지: dj-core 는 §0.4 라 우리가 고칠 수 없고, 전역 승격은 무증상 실패
     후보 21곳을 건드린다(W0-18 §2-2). 넓히는 일에는 판정이 필요하다
  ③ **우리 손으로 새 불일치를 만들지 않는다** — `body_status`(감싸지 않은 dict 반환)는
     0건이어야 한다. 이건 우리 코드고, 우리가 고칠 수 있다

    python scripts/verify_envelope.py            # 판정
    python scripts/verify_envelope.py --list     # 라우트별 봉투 상태
    python scripts/verify_envelope.py --freeze   # 기준선 갱신
    python scripts/verify_envelope.py --self-test

호스트에서 돈다 — 커밋된 인벤토리를 읽는다(게이트가 환경에 매이면 환경이 죽을 때
**초록으로** 죽는다 · D-301).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "D-349"
INVENTORY = ROOT / "docs" / "agent" / "evidence" / "D-343" / "route_inventory.json"
BASELINE = EVIDENCE / "envelope_baseline.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

PROMOTED = "promoted"
AUTHZ = "authz_envelope"
BODY_STATUS = "body_status"
CLEAN = "clean"

#: 계약 상대가 읽는 면. 여기는 **래칫이 없다.**
CONTRACT_SURFACE_PREFIXES = ("/api/dsm/",)

#: ★ [2026-09-05 턴 E · 차선 S · SEC-11a] **화면이 실제로 부른 호출**의 기록.
#:   캡처 24장이 브라우저에서 낸 호출 전수다 — 손으로 적은 목록이 아니다.
SCREEN_CALLS = ROOT / "docs" / "agent" / "evidence" / "D-386" / "screen_routes.json"

_HEADER = """\
# D-349 봉투 불일치 기준선 — **오늘의 건수** (2026-09-09 실측)
#
# ★ `python scripts/verify_envelope.py --freeze` 가 만든다. 손으로 고치지 말 것.
#
# 래칫이다(D-311). 늘면 exit 1. 줄어드는 것은 환영이고 --freeze 로 내린다.
# 소급 수정을 요구하지 않는 이유: 뿌리가 dj-core `path_permission` 이고 §0.4 라
# 우리가 못 고친다. 전역 승격은 무증상 실패 후보 21곳을 건드린다(W0-18 §2-2).
#
# 형식:  <상태> <탭> <건수>
"""


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 순수 함수로
# ═══════════════════════════════════════════════════════════════════════════

def judge(rows: list[dict], baseline: dict[str, int]) -> tuple[list[str], dict[str, int]]:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.get("envelope", "?")] = counts.get(r.get("envelope", "?"), 0) + 1

    problems: list[str] = []
    if not rows:
        problems.append("인벤토리가 비었다 — 판정이 아니라 열거기 고장이다 (D-301)")
        return problems, counts

    # ① 계약 면은 래칫에서 제외 — 즉시 0
    contract_bad = [
        "%s %s (%s)" % (r["method"], r["path"], r.get("envelope"))
        for r in rows
        if any(r["path"].startswith(p) for p in CONTRACT_SURFACE_PREFIXES)
        and r.get("envelope") != PROMOTED
    ]
    if contract_bad:
        problems.append(
            "★ 계약 상대가 읽는 면(F-05)에 봉투 불일치가 있다 — 여긴 래칫이 없다 (D-349 ③):\n    "
            + "\n    ".join(contract_bad[:10]))

    # ③ 우리 손으로 만든 불일치는 0건
    if counts.get(BODY_STATUS, 0) > 0:
        ours = [f"{r['method']} {r['path']}" for r in rows if r.get("envelope") == BODY_STATUS]
        problems.append(
            "우리 핸들러가 감싸지 않은 dict 로 상태를 돌려준다 %d건 — "
            "새 면은 HTTP 상태로 말한다 (D-349 ②):\n    " % len(ours) + "\n    ".join(ours[:10]))

    # ② 나머지는 래칫
    for name in (AUTHZ, BODY_STATUS):
        base = baseline.get(name)
        if base is None:
            problems.append("기준선에 %s 가 없다 — --freeze 로 잠가라" % name)
        elif counts.get(name, 0) > base:
            problems.append("%s 가 늘었다: 기준선 %d → 지금 %d. 봉투가 갈리는 면이 넓어졌다"
                            % (name, base, counts.get(name, 0)))
    return problems, counts


# ═══════════════════════════════════════════════════════════════════════════
# ④ **화면이 부르는 라우트의 봉투 잔여 = 0** — 이 수가 SEC-11a 의 심장이다
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 이 눈이 따로 서야 하는가 [실측 2026-09-05]
# ---------------------------------------------
# 이날 잔여는 205건이었다. 그런데 **화면이 부르는 라우트 중 봉투가 갈리는 것은 0건**이다:
#
#     캡처 24장의 고유 호출 33건 → promoted 27 · clean 5 · authz_envelope **0** · 미대조 1
#
# 즉 205 라는 수는 「화면이 205자리에서 거부를 삼킨다」가 아니다. **그 수를 그대로
# SEC-11a 의 빚으로 읽으면 틀린다** — P-35 가 이미 쪼개 두었다: 부르는 자리는 우리 몫,
# 안 부르는 인수 라우트는 주인이 따로 있다(SEC-11b).
#
# ★ 그래서 이 게이트가 지켜야 할 것은 **총량이 아니라 이 0** 이다. 접두를 넓히다가
#   화면이 부르는 자리를 되돌리거나, 새 화면이 봉투 갈리는 라우트를 부르기 시작하면
#   **그 순간** 빨개져야 한다. 총량 래칫(②)은 그것을 못 본다 — 총량은 그대로인 채
#   화면 쪽만 나빠질 수 있기 때문이다.


def _path_matcher(template: str) -> "re.Pattern[str]":
    """`/api/x/{id}` 같은 자리표를 한 단 매칭으로 바꾼다."""
    return re.compile("^" + re.sub(r"\{[^}]+\}", r"[^/]+", template).rstrip("/") + "/?$")


def screen_calls(doc: dict) -> list[tuple[str, str]]:
    """캡처 기록에서 **고유 호출**을 뽑는다 (질의문자열은 떼고, 중복은 접는다)."""
    out: set[tuple[str, str]] = set()
    for calls in (doc.get("screens") or {}).values():
        for call in calls or []:
            path = str(call.get("path", "")).split("?")[0]
            if path:
                out.add((str(call.get("method", "GET")).upper(), path))
    return sorted(out)


def judge_screen_surface(
    rows: list[dict], calls: list[tuple[str, str]]
) -> tuple[list[str], dict, list[str]]:
    """화면이 부른 호출마다 그 라우트의 봉투를 본다. **authz_envelope 는 0이어야 한다.**"""
    pats = [(_path_matcher(r["path"]), r) for r in rows]
    counts = {"matched": 0, "unmatched": 0, AUTHZ: 0}
    bad: list[str] = []
    unmatched: list[str] = []
    for method, path in calls:
        hit = next((r for pat, r in pats if r["method"] == method and pat.match(path)), None)
        if hit is None:
            counts["unmatched"] += 1
            unmatched.append("%s %s" % (method, path))
            continue
        counts["matched"] += 1
        if hit.get("envelope") == AUTHZ:
            counts[AUTHZ] += 1
            bad.append("%s %s  (라우트 %s)" % (method, path, hit["path"]))

    problems: list[str] = []
    if not calls:
        problems.append("화면 호출 기록이 비었다 — 판정이 아니라 열거기 고장이다 (D-301)")
    elif counts["matched"] == 0:
        problems.append("화면 호출 %d건 중 인벤토리와 대조된 것이 0건이다 — 못 잰 것이다"
                        % len(calls))
    if bad:
        problems.append(
            "★ **화면이 부르는 라우트에서 봉투가 갈린다** %d건 — 여기는 래칫이 아니라 0이다 "
            "(SEC-11a · P-35):\n    " % len(bad) + "\n    ".join(bad[:10]))
    return problems, counts, unmatched


def parse_baseline(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, _, value = line.partition("\t")
        try:
            out[name.strip()] = int(value.strip())
        except ValueError:
            continue
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    """★ 출생 표본: **18 을 11 로 만든 그 응답**이 이 게이트에 들어오면 잡히는가."""
    base = {AUTHZ: 296, BODY_STATUS: 0}

    def row(path, env, method="GET"):
        return {"method": method, "path": path, "envelope": env}

    checks = [
        ("★ 출생표본 — 계약 면(F-05)에 200/403 봉투가 남으면 잡는다",
         any("계약 상대가 읽는 면" in p
             for p in judge([row("/api/dsm/events", AUTHZ)], base)[0])),
        ("계약 면이 승격돼 있으면 통과한다",
         not judge([row("/api/dsm/events", PROMOTED)], base)[0]),
        ("★ 우리가 만든 불일치(body_status)는 0건이어야 한다",
         any("감싸지 않은 dict" in p
             for p in judge([row("/api/x", BODY_STATUS)], base)[0])),
        ("기존 authz 봉투는 래칫이다 — 기준선 안이면 통과",
         not judge([row("/api/x", AUTHZ)], base)[0]),
        ("래칫을 넘으면 잡는다",
         any("늘었다" in p for p in judge([row("/api/x", AUTHZ)], {AUTHZ: 0, BODY_STATUS: 0})[0])),
        ("빈 인벤토리는 초록이 아니다 (D-301)",
         any("열거기 고장" in p for p in judge([], base)[0])),
        ("기준선이 없으면 초록이 아니다",
         any("기준선에" in p for p in judge([row("/api/x", CLEAN)], {})[0])),
        # ── ④ 화면이 부르는 면 ────────────────────────────────────────
        ("★ 화면이 부르는 라우트에 봉투 갈림이 있으면 잡는다 (SEC-11a)",
         any("화면이 부르는 라우트" in p for p in judge_screen_surface(
             [row("/api/x/{id}", AUTHZ)], [("GET", "/api/x/7")])[0])),
        ("화면이 부르는 라우트가 승격돼 있으면 통과한다",
         not judge_screen_surface(
             [row("/api/x/{id}", PROMOTED)], [("GET", "/api/x/7")])[0]),
        ("자리표를 한 단으로만 편다 — 두 단을 삼키면 엉뚱한 라우트에 붙는다",
         not _path_matcher("/api/x/{id}").match("/api/x/7/deep")),
        ("화면 호출이 비면 초록이 아니다 (D-301)",
         any("열거기 고장" in p for p in judge_screen_surface([row("/api/x", CLEAN)], [])[0])),
        ("★ 대조가 0건이면 「잔여 0」이 아니라 **못 쟀다**",
         any("못 잰 것이다" in p for p in judge_screen_surface(
             [row("/api/x", CLEAN)], [("GET", "/api/other")])[0])),
        ("호출 뽑기가 질의문자열을 떼고 중복을 접는다",
         screen_calls({"screens": {"a": [{"method": "get", "path": "/api/x?q=1"},
                                          {"method": "GET", "path": "/api/x?q=2"}]}})
         == [("GET", "/api/x")]),
        ("기준선 파서가 두 줄을 읽는다",
         parse_baseline("# 주석\nauthz_envelope\t296\nbody_status\t0\n")
         == {AUTHZ: 296, BODY_STATUS: 0}),
    ]
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[ENVELOPE] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not INVENTORY.exists():
        print("[ENVELOPE] 인벤토리가 없다: %s" % INVENTORY)
        return 1

    rows = json.loads(INVENTORY.read_text(encoding="utf-8")).get("routes", [])
    if any("envelope" not in r for r in rows):
        print("[ENVELOPE] 인벤토리에 봉투 칸이 없다 — 인벤토리를 다시 떠라 (D-349 ①)")
        return 1

    if args.freeze:
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["envelope"]] = counts.get(r["envelope"], 0) + 1
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(
            _HEADER + "".join("%s\t%d\n" % (k, counts.get(k, 0)) for k in (AUTHZ, BODY_STATUS)),
            encoding="utf-8")
        print("[ENVELOPE] 기준선 authz_envelope=%d body_status=%d 로 잠갔다"
              % (counts.get(AUTHZ, 0), counts.get(BODY_STATUS, 0)))
        return 0

    baseline = parse_baseline(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    problems, counts = judge(rows, baseline)

    print("[ENVELOPE] [입력] 라우트 %d건 (모수=커밋된 인벤토리 전수 · "
          "술어=본문에 상태를 담으면서 HTTP 는 200 인 응답을 낼 수 있는가)" % len(rows))
    print("[ENVELOPE] 봉투: " + " · ".join(
        "%s %d" % (k, v) for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))))
    print("[ENVELOPE] 계약 면(F-05) %d건 — 래칫 없음 (D-349 ③)"
          % sum(1 for r in rows if any(r["path"].startswith(p)
                                       for p in CONTRACT_SURFACE_PREFIXES)))

    # ④ 화면이 부르는 면 — **여기는 래칫이 아니라 0이다** (SEC-11a · P-35)
    if not SCREEN_CALLS.exists():
        # 못 잰 것을 통과로 세지 않는다. 회색은 초록이 아니다 (exit 2).
        print("[ENVELOPE] **판정 불가** — 화면 호출 기록이 없다: %s" % SCREEN_CALLS)
        return 2
    calls = screen_calls(json.loads(SCREEN_CALLS.read_text(encoding="utf-8")))
    screen_problems, screen_counts, unmatched = judge_screen_surface(rows, calls)
    print("[ENVELOPE] 화면이 부르는 면: 고유 호출 %d건 → 대조 %d · 미대조 %d · "
          "봉투 갈림 **%d건** (여기는 0이어야 한다)"
          % (len(calls), screen_counts["matched"], screen_counts["unmatched"],
             screen_counts[AUTHZ]))
    for line in unmatched:
        # 미대조는 실패가 아니라 **못 잰 것**이다. 세어서 보이게만 둔다.
        print("          미대조(못 쟀다): %s" % line)
    problems.extend(screen_problems)

    if args.list:
        for r in rows:
            if r["envelope"] != CLEAN:
                print("  %-16s %-6s %s" % (r["envelope"], r["method"], r["path"]))

    if problems:
        for p in problems:
            print("[ENVELOPE] FAIL %s" % p)
        return 1
    print("[ENVELOPE] 통과 — 계약 면은 갈리지 않고, 나머지는 늘지 않았다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(__file__)
    raise SystemExit(main())
