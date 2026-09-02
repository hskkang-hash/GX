#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-347 — 피드백 콘솔의 화면은 **실제 실행 캡처만**. 진술을 증거로 바꾼다.

왜 게이트가 필요한가
--------------------
D-347 은 「E2E 실행 중에 찍는다」고 정했다. 그런데 **그 문장은 진술이다.**

    ★ 이게 없으면 「E2E 중에 찍었다」가 진술로만 남는다 (D-323 — 확인 행위가 잠금을 내린다).

그래서 이 게이트가 **시각으로** 대조한다. 캡처 시각이 그 시나리오·단계의 E2E 실행 시각과
±5분 안에 있지 않으면, 그것은 시험이 지나간 화면이 아니다.

이 페이지는 **고객이 본다.** 실제가 아닌 화면이 한 장이라도 들어가면
**착시가 아니라 거짓말**이다 — D-284(거짓 성공 금지)의 대외 판이다.

보는 것 — 다섯
--------------
  ① 항목마다 메타 5칸이 **찼는가** (route · user_role · scenario · captured_at ·
     **data_source** — 시드인가 현장인가 · P-9)
  ② `file` 이 가리킨 PNG 가 **실재하는가** (없는 파일을 적으면 그것도 문서다)
  ③ 파일 자리가 규약대로인가 — `<scenario>/<role>/<route>.png`
  ④ `captured_at` 이 E2E 실행 로그의 그 단계 시각과 **±5분** 안인가
  ⑤ 0장일 때 **사유가 있는가** — 「0장」과 「못 찍었다」는 다르다 (D-301)

★ 0장은 실패가 아니다. **사유 없는 0장이 실패다.**
  지금은 브라우저를 여는 E2E 가 없어 0장이고, 그 사유가 `empty_reason` 과
  잠금 대장(BROWSER_E2E_HARNESS)에 적혀 있다. 사유를 지우면 이 게이트가 빨개진다.

    python scripts/verify_screens.py             # 판정
    python scripts/verify_screens.py --list      # 화면 목록
    python scripts/verify_screens.py --self-test

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "docs" / "agent" / "evidence" / "D-347" / "screens"
INDEX = SCREENS / "INDEX.yaml"
BLOCKERS = ROOT / "docs" / "agent" / "evidence" / "DA-05" / "blockers.yaml"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: ★ [P-9 · 2026-09-16] **다섯째 칸을 더했다 — `data_source`.**
#:   시드로 찍은 화면은 실제 화면이지만 **실제 사고는 아니다.** 그 둘이 구분되지
#:   않으면 검수 자리에서 시드 화면이 현장 화면으로 읽힌다 — 착시가 아니라 거짓말이다
#:   (D-284). 비어 있으면 이 게이트가 멈춘다: 출처 없는 화면은 싣지 않는다.
META_FIELDS = ("route", "user_role", "scenario", "captured_at", "data_source")


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 순수 함수로
# ═══════════════════════════════════════════════════════════════════════════

def expected_path(entry: dict) -> str:
    """규약 ⑤ — `<scenario>/<role>/<route>.png`.

    시나리오의 단계(`E2E-1/8`)에서 앞부분만 쓴다. 경로의 `/` 는 `_` 로 눕힌다 —
    경로를 그대로 디렉터리로 만들면 한 화면이 트리 깊숙이 숨는다.
    """
    scenario = str(entry.get("scenario", "")).split("/")[0]
    role = str(entry.get("user_role", ""))
    route = str(entry.get("route", "")).strip("/").replace("/", "_") or "root"
    return "%s/%s/%s.png" % (scenario, role, route)


def parse_when(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def judge_entry(entry: dict, *, exists, run_log: dict, tolerance_min: int) -> list[str]:
    """화면 한 장을 판정한다."""
    label = entry.get("file") or entry.get("route") or "(이름 없음)"
    out: list[str] = []

    missing = [f for f in META_FIELDS if not str(entry.get(f) or "").strip()]
    if missing:
        out.append("%s: 메타가 비었다 — %s" % (label, ", ".join(missing)))

    rel = str(entry.get("file") or "").strip()
    if not rel:
        out.append("%s: file 이 없다" % label)
        return out
    if not exists(rel):
        out.append("%s: 파일이 없다 — 없는 캡처를 적으면 그것도 문서다" % rel)
    want = expected_path(entry)
    if rel != want:
        out.append("%s: 자리가 규약과 다르다 — «%s» 여야 한다 (<scenario>/<role>/<route>.png)"
                   % (rel, want))

    when = parse_when(entry.get("captured_at"))
    if entry.get("captured_at") and when is None:
        out.append("%s: captured_at 이 날짜·시각이 아니다: %r" % (rel, entry.get("captured_at")))
    elif when is not None:
        step = str(entry.get("scenario") or "")
        ran = parse_when((run_log.get("steps") or {}).get(step))
        if ran is None:
            # ★ 「E2E 중에 찍었다」가 진술로만 남는 자리다.
            out.append("%s: E2E 로그에 «%s» 단계의 시각이 없다 — "
                       "「시험 중에 찍었다」를 확인할 수 없다 (D-323)" % (rel, step))
        elif abs(when - ran) > timedelta(minutes=tolerance_min):
            out.append("%s: 캡처 %s 와 E2E 단계 %s 가 %d분 넘게 벌어졌다 — "
                       "시험이 지나간 화면이 아니다"
                       % (rel, when.isoformat(), ran.isoformat(), tolerance_min))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    """★ 출생 표본: **「E2E 중에 찍었다」가 진술로만 남은 상태**.

    로그와 대조되지 않는 캡처, 시각이 벌어진 캡처, 없는 파일 — 셋 다 잡혀야 한다.
    거기서 초록이 나오면 이 게이트는 합성 화면을 고객 앞에 통과시킨다.
    """
    log = {"steps": {"E2E-1/8": "2026-09-08T11:20:00"}}
    good = {"route": "/dashboard", "user_role": "OPERATOR", "scenario": "E2E-1/8",
            "data_source": "시드",
            "captured_at": "2026-09-08T11:22:00", "file": "E2E-1/OPERATOR/dashboard.png"}
    have = {"E2E-1/OPERATOR/dashboard.png"}.__contains__

    def p(entry, *, exists=have, run=log):
        return judge_entry(entry, exists=exists, run_log=run, tolerance_min=5)

    checks = [
        ("음성 대조 — 규약대로 찍힌 한 장은 통과한다", not p(good)),
        ("★ 출생표본 — E2E 로그에 그 단계가 없으면 잡는다 (진술만 남는다)",
         any("확인할 수 없다" in x for x in p(good, run={"steps": {}}))),
        ("★ 출생표본 — 시각이 5분 넘게 벌어지면 잡는다",
         any("벌어졌다" in x for x in p(dict(good, captured_at="2026-09-08T11:40:00")))),
        ("★ 없는 파일을 적으면 잡는다",
         any("파일이 없다" in x for x in p(dict(good, file="E2E-1/OPERATOR/없다.png")))),
        ("메타 한 칸이 비면 잡는다",
         any("메타가 비었다" in x for x in p(dict(good, user_role="")))),
        ("자리가 규약과 다르면 잡는다",
         any("자리가 규약과 다르다" in x for x in p(dict(good, file="아무데나.png"),
                                                exists=lambda r: True))),
        ("captured_at 이 시각이 아니면 잡는다",
         any("날짜·시각이 아니다" in x for x in p(dict(good, captured_at="어제")))),
        ("경로의 / 는 _ 로 눕힌다",
         expected_path({"scenario": "E2E-2/3", "user_role": "ADMIN",
                        "route": "/events/1/clip"}) == "E2E-2/ADMIN/events_1_clip.png"),
    ]
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[SCREENS] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not INDEX.exists():
        print("[SCREENS] 인덱스가 없다: %s — 판정이 아니라 틀이 없는 것이다" % INDEX)
        return 1

    data = yaml.safe_load(INDEX.read_text(encoding="utf-8")) or {}
    meta = data.get("meta") or {}
    entries = data.get("screens") or []
    tolerance = int(meta.get("tolerance_minutes", 5))

    run_log: dict = {}
    log_path = ROOT / str(meta.get("run_log", ""))
    if log_path.is_file():
        try:
            run_log = json.loads(log_path.read_text(encoding="utf-8"))
        except ValueError:
            run_log = {}

    print("[SCREENS] [입력] 인덱스 항목 %d장 · E2E 로그 %s · 허용 오차 ±%d분"
          % (len(entries), "있음" if run_log else "없음", tolerance))

    problems: list[str] = []
    for entry in entries:
        problems += judge_entry(entry, exists=lambda rel: (SCREENS / rel).is_file(),
                                run_log=run_log, tolerance_min=tolerance)

    # ★ 인덱스에 없는 파일 — 어디서 왔는지 모르는 화면이 콘솔에 실리지 않게 한다.
    listed = {str(e.get("file") or "") for e in entries}
    stray = sorted(p.relative_to(SCREENS).as_posix()
                   for p in SCREENS.rglob("*.png") if p.relative_to(SCREENS).as_posix() not in listed)
    for s in stray:
        problems.append("%s: 인덱스에 없는 캡처다 — 어디서 온 화면인지 말하지 않는다" % s)

    if not entries:
        # ⑤ 0장은 실패가 아니다. **사유 없는 0장이 실패다** (D-301).
        reason = str(meta.get("empty_reason") or "").strip()
        if not reason:
            print("[SCREENS] FAIL 0장인데 사유가 없다 — 「아직 안 찍었다」와 "
                  "「찍을 수 없다」가 구별되지 않는다")
            return 1
        print("[SCREENS] 0장 · 사유: %s" % reason.splitlines()[0])
        blocked = "BROWSER_E2E_HARNESS" in (
            BLOCKERS.read_text(encoding="utf-8") if BLOCKERS.exists() else "")
        print("[SCREENS] 잠금 대장 등재: %s" % ("BROWSER_E2E_HARNESS" if blocked else "★ 없음"))
        if not blocked:
            print("[SCREENS] FAIL 0장의 사유가 잠금 대장에 없다 — 사유가 문서에만 있으면 늙는다")
            return 1

    if args.list:
        for entry in entries:
            print("  %-28s %-10s %-10s %s" % (entry.get("route"), entry.get("user_role"),
                                              entry.get("scenario"), entry.get("file")))

    if problems:
        for p in problems:
            print("[SCREENS] FAIL %s" % p)
        return 1
    print("[SCREENS] 통과 — 실린 화면은 전부 실제 실행 캡처다 (지금 %d장)" % len(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
