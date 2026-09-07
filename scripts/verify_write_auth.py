#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-368 / P-83 강제 도구 — **쓰기 메서드에 인증 관문이 없으면 exit 1.**

    읽기 유출 — 나간 것은 되돌릴 수 없다. 그러나 **무엇이 나갔는지는 안다**
    쓰기 오염 — 들어온 것도 되돌릴 수 없고, **게다가 조용하다**

D-358 은 「한꺼번에 막으면 제품이 깨진다」였고 그 신중함은 옳았다. D-368 이 그
문장의 **범위를 좁혔다**: 그것은 읽기 면의 규칙이다. 쓰기는 다르다.

★★ P-83 [세종 판정 2026-09-06 · 턴 I] — **401·403 과 422 는 다른 칸이다**
--------------------------------------------------------------------------
이 게이트는 턴 H 까지 **거짓 초록**이었다. 「관문 17」이라고 냈는데 그 17 중
**13이 실제로는 422**였다. 422 는 스키마 검증의 답이지 관문의 답이 아니다 —
「인증 없이도 여기까지 왔고 본문 형식에서 떨어졌다」는 뜻이고, 본문만 맞추면
그대로 들어간다. 그 셋을 한 칸에 넣었기 때문에 **열일곱 자리가 지켜지고 있다**고
읽혔다. 실제로 그랬던 것은 **둘**이었다.

    관문        = 401 · 403 **만**
    도달·검증   = 422 · 400   ← 관문이 아니다. 그리고 그 자리는
                                 **관문이 있는지 못 쟀다**로 센다(회색)
    도달 실패   = 404 · 405   ← 그 자리에 그 메서드가 없다

그래서 게이트의 **첫 줄**은 언제나 이 세 수로 시작한다. 총합만 적는 보고는 받지 않는다.

보는 것 — 일곱
--------------
  ① ★ **`writes` 0건**   익명이 도달하고 그 핸들러가 쓰는 자리. **래칫이 없다.**
                          기존분 면제도 없다 — 여기만은 소급해서 갚는다
  ② **새 면 100%**       우리가 만드는 면(`NEW_SURFACE_PREFIXES`)은 관문 의무.
                          한 자리라도 관문 없이 태어나면 exit 1
  ③ **래칫** (D-311)     **관문이 아닌** 갈래의 건수가 기준선을 넘으면 exit 1.
                          `gated` 에는 래칫이 없다 — 관문은 늘어도 좋다
  ④ **선언 대조**        `public_by_design` 은 면제가 아니라 **선언**이다.
                          프로브의 선언 목록과 증거의 갈래가 어긋나면 잡는다
  ⑤ **증거 신선도**      낡은 증거로 내는 초록은 아무것도 재지 않은 것이다 (D-301)
  ⑥ ★ **탐침 방식**      증거가 **스키마를 통과하는 본문**으로 잰 것인가.
                          빈 본문 하나로 잰 옛 증거(=422 를 관문으로 세던 증거)로는
                          초록을 못 낸다. 판정 규칙이 바뀌면 **증거도 다시 떠야** 한다
  ⑦ ★ **못 잰 자리**     `schema_rejected` 는 「막혔다」가 아니라 **「모른다」**다.
                          빨강이 없고 이것만 있으면 **회색(exit 2)** — 0 으로 내지 않는다

★ 왜 게이트가 컨테이너를 부르지 않나 (verify_route_inventory.py 와 같은 이유)
------------------------------------------------------------------------------
분류는 **런타임 레지스트리를 때려야** 나온다. 게이트가 매번 컨테이너를 띄우면 게이트가
환경에 매이고, 환경이 죽으면 게이트가 **초록으로** 죽는다. 그래서 게이트는 커밋된
증거를 본다. 증거를 다시 뜨는 것은 사람의 일이고, 낡은 증거는 ⑤가, 낡은 **방식**은
⑥이 잡는다.

    python scripts/verify_write_auth.py            # 판정
    python scripts/verify_write_auth.py --list     # 갈래별 목록
    python scripts/verify_write_auth.py --freeze   # 기준선 갱신
    python scripts/verify_write_auth.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "D-368"
SURFACE = EVIDENCE / "write_surface.json"
BASELINE = EVIDENCE / "write_auth_baseline.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: **우리가 만드는 면.** 여기서는 관문이 100% 다 — 기존분 래칫이 닿지 않는다 (D-358).
#: 새 커널 App 이 생기면 여기에 접두어를 더한다.
NEW_SURFACE_PREFIXES = ("/api/dsm/",)

#: 증거가 이보다 오래되면 판정을 못 한 것으로 본다.
MAX_AGE_DAYS = 30

#: ★ 탐침이 **스키마를 통과하는 본문**으로 쟀다는 표시. 이 표시가 없는 증거는
#:   빈 본문 하나로 잰 옛 증거이고, 그 증거의 「관문」 칸에는 422 가 섞여 있다.
REQUIRED_PROBE_MODE = "schema-passing-body"

#: 여섯 갈래 + 선언. 순서는 보고에 나오는 순서다.
VERDICTS = ("writes", "read_only_in_practice", "gated", "schema_rejected",
            "unreachable", "blocked_other", "public_by_design")

#: ★ **관문이 아닌 갈래.** 여기만 래칫이 걸린다 — 관문(`gated`)은 늘어도 좋다.
#:   `writes` 는 여기 없다: 그 갈래에는 래칫이 아니라 **0건 절대선**이 걸린다.
RATCHETED = ("read_only_in_practice", "schema_rejected", "unreachable",
             "blocked_other", "public_by_design")


def counts_of(rows: list[dict]) -> dict[str, int]:
    return {v: sum(1 for r in rows if r.get("verdict") == v) for v in VERDICTS}


def headline(counts: dict[str, int]) -> str:
    """★ **첫 줄은 언제나 세 수로 시작한다** (P-83). 총합만 적는 보고는 받지 않는다."""
    return ("관문 %d · 도달·검증 %d · 도달 실패 %d"
            % (counts.get("gated", 0),
               counts.get("schema_rejected", 0),
               counts.get("unreachable", 0) + counts.get("blocked_other", 0)))


def judge(payload: dict, baseline: dict, today: datetime) -> list[str]:
    """판정식은 **여기 한 곳에만** 둔다 (D-212). 파일 없이 시험할 수 있게 순수 함수로."""
    problems: list[str] = []
    rows = payload.get("routes") or []
    counts = counts_of(rows)

    # ⑥ 탐침 방식 — **판정 규칙이 바뀌면 증거도 다시 떠야 한다**
    mode = payload.get("probe_mode")
    if mode != REQUIRED_PROBE_MODE:
        problems.append(
            "★ 증거를 **옛 방식**으로 쟀다(probe_mode=%r · 필요한 값 %r) — 빈 본문 "
            "하나로 재면 422 가 나오고, 그 422 를 관문으로 세던 것이 턴 H 의 거짓 "
            "초록이었다. `probe_write_surface.py` 를 다시 돌려라 (P-83)"
            % (mode, REQUIRED_PROBE_MODE))

    # ① writes 0건 — 래칫 없음
    writing = [r for r in rows if r.get("verdict") == "writes"]
    for r in writing:
        problems.append(
            "★ 관문 없는 쓰기: %s %s (%s) — 익명이 핸들러에 도달하고 그 핸들러가 쓴다. %s "
            "쓰기 오염은 조용하고, 심어진 행은 진짜와 섞여 나중에 못 골라낸다 (D-368)"
            % (r.get("method"), r.get("path"), r.get("view", "?"), r.get("writes_by", "")))

    # ② 새 면 100%
    for r in rows:
        if any(str(r.get("path", "")).startswith(p) for p in NEW_SURFACE_PREFIXES):
            if r.get("verdict") not in ("gated", "public_by_design"):
                problems.append(
                    "★ 새 면인데 관문이 없다: %s %s (지금 %s) — 새 면은 100%% 의무다. "
                    "기존분 래칫은 여기 닿지 않는다 (D-358 · D-368)"
                    % (r.get("method"), r.get("path"), r.get("verdict")))

    # ③ 래칫 — **관문이 아닌 갈래만**
    for v in RATCHETED:
        base = baseline.get(v)
        if base is None:
            problems.append("기준선에 %r 갈래가 없다 — `--freeze` 로 먼저 잠근다" % v)
        elif counts[v] > base:
            problems.append(
                "★ 래칫: %s 가 %d자리 → %d자리로 **늘었다.** 관문이 아닌 갈래는 "
                "줄기만 한다 (D-311)" % (v, base, counts[v]))

    # ④ 선언 대조 — 증거의 public_by_design 이 프로브의 선언 목록과 같은가
    declared = set(baseline.get("public_by_design_paths") or [])
    seen = {r["path"] for r in rows if r.get("verdict") == "public_by_design"}
    for extra in sorted(seen - declared):
        problems.append(
            "★ 선언되지 않은 공개 쓰기 면: %s — `public_by_design` 은 면제가 아니라 "
            "**선언**이다. 사람이 목록에 이름을 적어야 한다" % extra)

    # ⑤ 신선도
    stamp = payload.get("measured_at")
    if not stamp:
        problems.append("증거에 측정 시각이 없다 — 언제 잰 것인지 모르는 수는 수가 아니다")
    else:
        try:
            when = datetime.fromisoformat(stamp)
            age = (today - when).days
            if age > MAX_AGE_DAYS:
                problems.append(
                    "증거가 %d일 됐다(상한 %d일) — 낡은 증거로 내는 초록은 아무것도 "
                    "재지 않은 것이다 (D-301)" % (age, MAX_AGE_DAYS))
        except ValueError:
            problems.append("측정 시각을 읽지 못했다: %r" % stamp)

    return problems


def undecided(payload: dict) -> list[str]:
    """⑦ **못 쟀다** — 빨강이 아니라 회색이다. 0 으로 내지 않는다 (규칙 ①).

    `schema_rejected` 는 「스키마를 맞춰 주고도 422 였다」는 뜻이다. 그 자리 뒤에
    관문이 있는지 **우리는 모른다** — 본문을 못 맞춰서 못 가 봤을 뿐이다.
    「막혔다」로 세면 그것이 곧 턴 H 의 거짓 초록이고, 「열렸다」로 세면 없는 빨강을
    만든다. 그래서 자기 칸에 두고 **판정 불가**로 낸다 (D-301 · P-12 ④).
    """
    out = []
    for r in payload.get("routes") or []:
        if r.get("verdict") == "schema_rejected":
            out.append("%s %s — 스키마를 %d바퀴 맞추고도 422. 못 채운 칸: %s"
                       % (r.get("method"), r.get("path"), r.get("rounds", 0),
                          ", ".join(r.get("unresolved") or []) or "(없음)"))
    return out


def _fake(verdicts, *, measured_at=None, paths=None, mode=REQUIRED_PROBE_MODE):
    now = measured_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for i, v in enumerate(verdicts):
        rows.append({"method": "POST", "path": (paths or {}).get(i, "/api/x/%d" % i),
                     "verdict": v, "view": "m.f", "writes_by": "", "rounds": 1,
                     "unresolved": []})
    return {"measured_at": now, "probe_mode": mode, "routes": rows}


def self_test() -> int:
    now = datetime.now(timezone.utc)
    base = {"read_only_in_practice": 4, "schema_rejected": 3, "unreachable": 3,
            "blocked_other": 2, "public_by_design": 11,
            "public_by_design_paths": ["/api/x/0"]}

    # ★ 출생 표본 (D-310) — **이 도구를 만들게 한 바로 그 네 자리.**
    #   [실측 2026-09-11 · probe_write_surface.py] 익명이 핸들러에 도달하고
    #   그 핸들러가 쓰던 자리들이다. 첫 갈래가 이것을 잡지 못하면 이 게이트는
    #   초록을 내도 아무것도 재지 않은 것이다.
    BIRTH_SAMPLE = _fake(
        ["writes", "writes", "writes", "writes"],
        paths={
            0: "/api/media-data/detect-callback",
            1: "/api/media-data/upload-detection",
            2: "/api/flight-log/flight-log/delete/{ids}",
            3: "/api/stream-monitors/stream-monitors/external-stream-monitors/{id}",
        })

    # ★★ **두 번째 출생 표본** (P-83) — 턴 H 의 거짓 초록 그 자체.
    #   그때 이 게이트가 본 것은 「관문 17」이었고, 그 17 중 13이 422 였다.
    #   같은 모양을 넣었을 때 첫 줄이 **관문 4 · 도달·검증 13** 으로 나와야 한다.
    FALSE_GREEN_SAMPLE = _fake(["gated"] * 4 + ["schema_rejected"] * 13)

    checks = [
        ("★★ 턴 H 의 그 모양에서 첫 줄이 **관문 4 · 도달·검증 13** 으로 갈린다",
         headline(counts_of(FALSE_GREEN_SAMPLE["routes"]))
         == "관문 4 · 도달·검증 13 · 도달 실패 0"),
        ("★★ 422 를 관문으로 세지 않는다 — 세 수가 한 칸으로 합쳐지지 않는다",
         counts_of(FALSE_GREEN_SAMPLE["routes"])["gated"] == 4),
        ("★ 첫 줄은 언제나 세 수로 시작한다",
         headline({}).startswith("관문 0 · 도달·검증 0 · 도달 실패 0")),
        ("★ 도달 실패 칸에 blocked_other 를 함께 센다(사라지지 않게)",
         headline(counts_of(_fake(["unreachable", "blocked_other"])["routes"]))
         == "관문 0 · 도달·검증 0 · 도달 실패 2"),

        ("★ 출생 표본 — 관문 없이 쓰던 네 자리를 **넷 다** 잡는다",
         len([p for p in judge(BIRTH_SAMPLE, base, now)
              if "관문 없는 쓰기" in p]) == 4),
        ("★ writes 가 한 자리라도 있으면 잡는다",
         any("관문 없는 쓰기" in p
             for p in judge(_fake(["writes"]), base, now))),
        ("writes 가 0건이면 그 갈래로는 안 잡는다",
         not any("관문 없는 쓰기" in p
                 for p in judge(_fake(["gated"]), base, now))),
        ("★ 새 면(/api/dsm/)에 관문이 없으면 잡는다",
         any("새 면" in p for p in judge(
             _fake(["schema_rejected"], paths={0: "/api/dsm/things"}), base, now))),
        ("★ 새 면이라도 **관문이 있으면** 안 잡는다 (음성 대조)",
         not any("새 면" in p for p in judge(
             _fake(["gated"], paths={0: "/api/dsm/things"}), base, now))),
        ("★ 래칫 — 관문 아닌 갈래가 늘면 잡는다",
         any("래칫" in p for p in judge(
             _fake(["read_only_in_practice"] * 5), base, now))),
        ("★★ 관문(gated)이 **늘어도** 래칫에 안 걸린다 — 관문은 늘어야 한다",
         not any("래칫" in p for p in judge(_fake(["gated"] * 99), base, now))),
        ("갈래가 줄면 안 잡는다",
         not any("래칫" in p for p in judge(
             _fake(["read_only_in_practice"]), base, now))),
        ("★ 선언되지 않은 공개 면은 잡는다",
         any("선언되지 않은" in p for p in judge(
             _fake(["public_by_design"], paths={0: "/api/surprise"}), base, now))),
        ("선언된 공개 면은 안 잡는다",
         not any("선언되지 않은" in p for p in judge(
             _fake(["public_by_design"], paths={0: "/api/x/0"}), base, now))),
        ("★ 증거가 낡으면 잡는다",
         any("낡은 증거" in p for p in judge(
             _fake(["gated"], measured_at="2020-01-01T00:00:00+00:00"), base, now))),
        ("★★ 옛 방식(빈 본문)으로 잰 증거로는 초록을 못 낸다",
         any("옛 방식" in p for p in judge(
             _fake(["gated"], mode=None), base, now))),
        ("★ 기준선이 없으면 초록을 내지 않는다",
         bool(judge(_fake(["gated"]), {}, now))),
        ("★ schema_rejected 는 **못 쟀다**로 샌다 (0 으로 내지 않는다)",
         len(undecided(_fake(["schema_rejected", "gated"]))) == 1),
        ("관문만 있으면 못 잰 것이 없다 (음성 대조)",
         undecided(_fake(["gated"])) == []),
    ]
    for name, ok in checks:
        print("  %s  %s" % ("OK  " if ok else "FAIL", name))
    bad = [n for n, ok in checks if not ok]
    pos = sum(1 for n, _ in checks if n.startswith("★"))
    print("[WRITEAUTH] 자기시험 %d건 %s (양성 %d · 음성 %d)"
          % (len(checks), "통과" if not bad else "실패", pos, len(checks) - pos))
    return EXIT_OK if not bad else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()

    rc = self_test()
    if args.self_test:
        return rc
    if rc != EXIT_OK:
        print("[WRITEAUTH] 자기시험이 실패했다 — 판정기를 먼저 고친다 (D-350)")
        return rc

    if not SURFACE.exists():
        print("[WRITEAUTH] 증거가 없다: %s — `probe_write_surface.py` 를 컨테이너에서 "
              "먼저 돌린다. **판정 불가**다" % SURFACE.relative_to(ROOT))
        return EXIT_UNDECIDABLE
    payload = json.loads(SURFACE.read_text(encoding="utf-8"))
    rows = payload.get("routes") or []
    counts = counts_of(rows)

    # ★★ 첫 줄 — 세 수로 시작한다 (P-83). 이 순서와 이 낱말을 바꾸지 마라.
    print("[WRITEAUTH] %s · ★관문없이 도달·쓰기 %d · 도달·안씀 %d · 선언 %d "
          "(관문 없는 쓰기 면 %d자리 · 잰 때 %s · 방식 %s)"
          % (headline(counts), counts["writes"], counts["read_only_in_practice"],
             counts["public_by_design"], len(rows),
             payload.get("measured_at", "?"), payload.get("probe_mode", "?")))
    for v in VERDICTS:
        star = " ★" if v == "writes" and counts[v] else ""
        print("    %-24s %3d자리%s" % (v, counts[v], star))

    if args.list:
        for v in VERDICTS:
            names = ["%s %s" % (r["method"], r["path"]) for r in rows if r["verdict"] == v]
            if names:
                print("  [%s]" % v)
                for n in sorted(names):
                    print("    %s" % n)

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        frozen = {
            "note": ("D-368 · P-83 래칫 기준선. **`writes` 도 `gated` 도 여기 없다** — "
                     "`writes` 에는 래칫이 아니라 0건 절대선이 걸리고, `gated`(관문)는 "
                     "늘어야 하는 갈래라 래칫을 걸지 않는다."),
            "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "public_by_design_paths": sorted(
                r["path"] for r in rows if r["verdict"] == "public_by_design"),
        }
        for v in RATCHETED:
            frozen[v] = counts[v]
        BASELINE.write_text(json.dumps(frozen, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print("[WRITEAUTH] 기준선 기록 → %s" % BASELINE.relative_to(ROOT))
        return EXIT_OK

    if not BASELINE.exists():
        print("[WRITEAUTH] 기준선이 없다 — `--freeze` 로 오늘 현황을 먼저 잠근다. "
              "기준선 없이 내는 초록은 아무것도 재지 않은 것이다 (D-301)")
        return EXIT_FAIL
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems = judge(payload, baseline, datetime.now(timezone.utc))
    grey = undecided(payload)

    if problems:
        print("[WRITEAUTH] 위반")
        for p in problems:
            print("  · %s" % p)
        if grey:
            print("  (그리고 **못 잰 자리** %d — 아래 회색 목록)" % len(grey))
            for g in grey:
                print("    ? %s" % g)
        return EXIT_FAIL

    if grey:
        # ★ 규칙 ① — 못 잰 것은 exit 2 로 낸다. 0 으로 내지 않는다.
        print("[WRITEAUTH] **못 쟀다** — 스키마를 맞춰 주고도 422 인 자리가 %d 있다. "
              "그 뒤에 관문이 있는지 없는지 이 증거로는 말할 수 없다 (D-301)" % len(grey))
        for g in grey:
            print("    ? %s" % g)
        return EXIT_UNDECIDABLE

    print("[WRITEAUTH] 통과 — **익명이 도달해서 쓰는 자리 0건.** 새 면은 100% (D-368 · P-83)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
