#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-368 강제 도구 — **쓰기 메서드에 인증 관문이 없으면 exit 1.**

    읽기 유출 — 나간 것은 되돌릴 수 없다. 그러나 **무엇이 나갔는지는 안다**
    쓰기 오염 — 들어온 것도 되돌릴 수 없고, **게다가 조용하다**

D-358 은 「한꺼번에 막으면 제품이 깨진다」였고 그 신중함은 옳았다. D-368 이 그
문장의 **범위를 좁혔다**: 그것은 읽기 면의 규칙이다. 쓰기는 다르다.

보는 것 — 다섯
--------------
  ① ★ **`writes` 0건**   익명이 도달하고 그 핸들러가 쓰는 자리. **래칫이 없다.**
                          기존분 면제도 없다 — 여기만은 소급해서 갚는다
  ② **새 면 100%**       우리가 만드는 면(`NEW_SURFACE_PREFIXES`)은 관문 의무.
                          한 자리라도 관문 없이 태어나면 exit 1
  ③ **래칫** (D-311)     나머지 갈래의 건수가 기준선을 넘으면 exit 1.
                          기존 43자리에 소급 사유를 요구하지 않는다
  ④ **선언 대조**        `public_by_design` 은 면제가 아니라 **선언**이다.
                          프로브의 선언 목록과 증거의 갈래가 어긋나면 잡는다
  ⑤ **증거 신선도**      낡은 증거로 내는 초록은 아무것도 재지 않은 것이다 (D-301)

★ 왜 게이트가 컨테이너를 부르지 않나 (verify_route_inventory.py 와 같은 이유)
------------------------------------------------------------------------------
분류는 **런타임 레지스트리를 때려야** 나온다. 게이트가 매번 컨테이너를 띄우면 게이트가
환경에 매이고, 환경이 죽으면 게이트가 **초록으로** 죽는다. 그래서 게이트는 커밋된
증거를 본다. 증거를 다시 뜨는 것은 사람의 일이고, 낡은 증거는 ⑤가 잡는다.

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

VERDICTS = ("writes", "read_only_in_practice", "rejected_elsewhere", "public_by_design")


def judge(payload: dict, baseline: dict, today: datetime) -> list[str]:
    """판정식은 **여기 한 곳에만** 둔다 (D-212). 파일 없이 시험할 수 있게 순수 함수로."""
    problems: list[str] = []
    rows = payload.get("routes") or []
    counts = {v: sum(1 for r in rows if r.get("verdict") == v) for v in VERDICTS}

    # ① writes 0건 — 래칫 없음
    writing = [r for r in rows if r.get("verdict") == "writes"]
    for r in writing:
        problems.append(
            f"★ 관문 없는 쓰기: {r['method']} {r['path']} ({r.get('view', '?')}) — "
            f"익명이 핸들러에 도달하고 그 핸들러가 쓴다. {r.get('writes_by', '')} "
            f"쓰기 오염은 조용하고, 심어진 행은 진짜와 섞여 나중에 못 골라낸다 (D-368)")

    # ② 새 면 100%
    for r in rows:
        if any(str(r.get("path", "")).startswith(p) for p in NEW_SURFACE_PREFIXES):
            problems.append(
                f"★ 새 면인데 관문이 없다: {r['method']} {r['path']} — "
                f"새 면은 100% 의무다. 기존분 래칫은 여기 닿지 않는다 (D-358 · D-368)")

    # ③ 래칫
    for v in ("read_only_in_practice", "rejected_elsewhere", "public_by_design"):
        base = baseline.get(v)
        if base is None:
            problems.append(f"기준선에 {v!r} 갈래가 없다 — `--freeze` 로 먼저 잠근다")
        elif counts[v] > base:
            problems.append(
                f"★ 래칫: {v} 가 {base}자리 → {counts[v]}자리로 **늘었다.** "
                f"관문 없는 쓰기 면은 줄기만 한다 (D-311)")

    # ④ 선언 대조 — 증거의 public_by_design 이 프로브의 선언 목록과 같은가
    declared = set(baseline.get("public_by_design_paths") or [])
    seen = {r["path"] for r in rows if r.get("verdict") == "public_by_design"}
    for extra in sorted(seen - declared):
        problems.append(
            f"★ 선언되지 않은 공개 쓰기 면: {extra} — `public_by_design` 은 면제가 "
            f"아니라 **선언**이다. 사람이 목록에 이름을 적어야 한다")

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
                    f"증거가 {age}일 됐다(상한 {MAX_AGE_DAYS}일) — 낡은 증거로 내는 "
                    f"초록은 아무것도 재지 않은 것이다 (D-301)")
        except ValueError:
            problems.append(f"측정 시각을 읽지 못했다: {stamp!r}")

    return problems


def _fake(verdicts, *, measured_at=None, paths=None):
    now = measured_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for i, v in enumerate(verdicts):
        rows.append({"method": "POST", "path": (paths or {}).get(i, f"/api/x/{i}"),
                     "verdict": v, "view": "m.f", "writes_by": ""})
    return {"measured_at": now, "routes": rows}


def self_test() -> int:
    now = datetime.now(timezone.utc)
    base = {"read_only_in_practice": 4, "rejected_elsewhere": 28,
            "public_by_design": 11, "public_by_design_paths": ["/api/x/0"]}

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

    checks = [
        ("★ 출생 표본 — 관문 없이 쓰던 네 자리를 **넷 다** 잡는다",
         len([p for p in judge(BIRTH_SAMPLE, base, now)
              if "관문 없는 쓰기" in p]) == 4),
        ("★ writes 가 한 자리라도 있으면 잡는다",
         any("관문 없는 쓰기" in p
             for p in judge(_fake(["writes"]), base, now))),
        ("writes 가 0건이면 그 갈래로는 안 잡는다",
         not any("관문 없는 쓰기" in p
                 for p in judge(_fake(["rejected_elsewhere"]), base, now))),
        ("★ 새 면(/api/dsm/)에 관문이 없으면 잡는다",
         any("새 면" in p for p in judge(
             _fake(["rejected_elsewhere"], paths={0: "/api/dsm/things"}), base, now))),
        ("★ 래칫 — 갈래가 늘면 잡는다",
         any("래칫" in p for p in judge(
             _fake(["read_only_in_practice"] * 5), base, now))),
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
             _fake(["rejected_elsewhere"], measured_at="2020-01-01T00:00:00+00:00"),
             base, now))),
        ("★ 기준선이 없으면 초록을 내지 않는다",
         bool(judge(_fake(["rejected_elsewhere"]), {}, now))),
    ]
    for name, ok in checks:
        print(f"  {'OK  ' if ok else 'FAIL'}  {name}")
    bad = [n for n, ok in checks if not ok]
    pos = sum(1 for n, _ in checks if n.startswith("★"))
    print(f"[WRITEAUTH] 자기시험 {len(checks)}건 {'통과' if not bad else '실패'} "
          f"(양성 {pos} · 음성 {len(checks) - pos})")
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
        print(f"[WRITEAUTH] 증거가 없다: {SURFACE.relative_to(ROOT)} — "
              f"`probe_write_surface.py` 를 컨테이너에서 먼저 돌린다. **판정 불가**다")
        return EXIT_UNDECIDABLE
    payload = json.loads(SURFACE.read_text(encoding="utf-8"))
    rows = payload.get("routes") or []
    counts = {v: sum(1 for r in rows if r.get("verdict") == v) for v in VERDICTS}

    print(f"[WRITEAUTH] 관문 없는 쓰기 라우트 **{len(rows)}자리** "
          f"(잰 때 {payload.get('measured_at', '?')})")
    for v in VERDICTS:
        star = " ★" if v == "writes" and counts[v] else ""
        print(f"    {v:24} {counts[v]:3}자리{star}")

    if args.list:
        for v in VERDICTS:
            names = [f"{r['method']} {r['path']}" for r in rows if r["verdict"] == v]
            if names:
                print(f"  [{v}]")
                for n in sorted(names):
                    print(f"    {n}")

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps({
            "note": ("D-368 래칫 기준선. **`writes` 는 여기 없다** — 그 갈래에는 "
                     "래칫이 없고 0건이 절대선이다."),
            "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "read_only_in_practice": counts["read_only_in_practice"],
            "rejected_elsewhere": counts["rejected_elsewhere"],
            "public_by_design": counts["public_by_design"],
            "public_by_design_paths": sorted(
                r["path"] for r in rows if r["verdict"] == "public_by_design"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[WRITEAUTH] 기준선 기록 → {BASELINE.relative_to(ROOT)}")
        return EXIT_OK

    if not BASELINE.exists():
        print(f"[WRITEAUTH] 기준선이 없다 — `--freeze` 로 오늘 현황을 먼저 잠근다. "
              f"기준선 없이 내는 초록은 아무것도 재지 않은 것이다 (D-301)")
        return EXIT_FAIL
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems = judge(payload, baseline, datetime.now(timezone.utc))

    if problems:
        print("[WRITEAUTH] 위반")
        for p in problems:
            print(f"  · {p}")
        return EXIT_FAIL
    print("[WRITEAUTH] 통과 — **익명이 도달해서 쓰는 자리 0건.** 새 면은 100% (D-368)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
