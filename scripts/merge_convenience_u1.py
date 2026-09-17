#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""편리성 계측을 대장에 **덧붙인다** — 줄면 멈춘다 (턴 S · 차선 U1).

무엇을 하는가
-------------
화면이 브라우저 안에서 잰 것(`window.__gxConvenience.export()` 의 JSON)을 받아
`docs/agent/evidence/U1-S/convenience_u1.json` 의 `runs` 에 **덧붙이고**, 지표별
가운뎃값을 `measured` 칸에 다시 적는다.

왜 덧붙이기만 하나 — **대장은 줄지 않는다**
--------------------------------------------
직전 턴에 캡처 도구가 대장 넷을 「이번 실행분」으로 덮어써서, 게이트가 그 상태를
읽고 수가 내려간 것을 「하락」으로 낼 뻔했다. 같은 함정이 여기에도 있다: 한 사람이
한 번 걸은 결과로 대장을 갈아 끼우면 **어제의 측정이 사라진다.** 그래서 이 도구는
① 덧붙이기만 하고 ② 덧붙인 뒤 수가 **줄었으면 쓰지 않고 멈춘다.**

무엇을 하지 않나
----------------
· **판정하지 않는다.** 목표를 넘겼는지 아닌지 이 도구는 말하지 않는다 — 첫 수는
  기준선이지 합격선이 아니다. 적는 것은 잰 수와 몇 번 쟀는가뿐이다.
· 값을 지어내지 않는다. 한 번도 안 잰 지표의 `measured` 는 `null` 로 **그대로 둔다** —
  0 은 「재 봤더니 0」이고 `null` 은 「못 쟀다」다.

    python scripts/merge_convenience_u1.py --dump <브라우저가 낸 JSON 경로>
    python scripts/merge_convenience_u1.py --self-test

V 단독 세션이 값을 내는 순서 [턴 T]
----------------------------------
  ① 브라우저(U1 계정 · SPA)에서 세 화면을 지나며 조작한다 — 어떤 조작 뒤 어떤 키에
     값이 생기는지는 `docs/agent/evidence/U1-S/convenience_u1.json` 의 `wired_at` 과
     아래 표가 말한다:
       u1_handle_event     /dsm/queue 초점 카드 뜸(시작) → 키 1(판정+접수) 성공 **또는**
                           종결 확인 「확인 — 종결」 성공(끝) → runs 에 1줄
       u1_handover_note    /handover 인계 자리 뜸(시작) → 「초안 가져오기」 또는
                           「인계 메모 쓰기」 누름(끝) → runs 에 1줄
       u1_dead_camera_check /dsm/cameras/grid 뜸(시작) → 무응답 수가 화면에 적힘(끝 ·
                           클릭 0 이 정상) → runs 에 1줄
  ② 같은 페이지에서 `JSON.stringify(window.__gxMetrics())` (또는
     `window.__gxConvenience.export()`) 를 evaluate 해 파일로 받는다 —
     `docs/agent/evidence/U1/convenience_dump_<UTC>.json`. `in_flight` 가 비어 있지
     않으면 그 지표는 **끝나지 않은 것**이다(수가 아니다) · `storage_ok=false` 면 그
     브라우저는 저장이 막힌 것이다.
  ③ `python scripts/merge_convenience_u1.py --dump <그 파일>` — 자기시험(실물 표본
     포함)을 지나 대장에 덧붙인다. 종료 0 · 「N줄 → N+k줄」 이 첫 값이다.

종료 코드: 0 붙였다 · 1 붙이다 멈췄다(줄었다·모양이 다르다) · 2 못 붙였다(파일 없음)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "agent" / "evidence" / "U1-S" / "convenience_u1.json"
SCHEMA = "gx.convenience.u1.v1"
TAG = "[CONV]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def _run_key(run: dict) -> tuple:
    """같은 측정인가. **시각 + 지표 + 대상**이 같으면 같은 줄로 본다 —
    걷기를 두 번 돌려 같은 덤프를 두 번 붙여도 수가 부풀지 않는다."""
    return (run.get("at"), run.get("metric"), run.get("subject"))


def merge(ledger: dict, dump: dict) -> tuple[dict, int]:
    """대장에 덤프를 붙인 **새 대장**과 늘어난 줄 수를 돌려준다. 순수 함수다."""
    if dump.get("schema") != SCHEMA:
        raise ValueError(
            f"덤프의 모양이 다르다: {dump.get('schema')!r} — 이 대장은 {SCHEMA!r} 만 받는다")

    old_runs = list(ledger.get("runs") or [])
    seen = {_run_key(r) for r in old_runs}

    added = []
    for run in dump.get("runs") or []:
        if not isinstance(run, dict):
            continue
        if _run_key(run) in seen:
            continue
        seen.add(_run_key(run))
        added.append(run)

    runs = old_runs + added

    #: ★ 여기가 래칫이다. 붙였는데 줄었으면 붙인 것이 아니다.
    if len(runs) < len(old_runs):
        raise ValueError("붙인 뒤 대장이 줄었다 — 멈춘다")

    out = dict(ledger)
    out["runs"] = runs
    out["metrics"] = [_remeasure(m, runs) for m in ledger.get("metrics") or []]
    return out, len(added)


def _remeasure(metric: dict, runs: list) -> dict:
    """한 지표의 `measured` 를 다시 적는다. **잰 것이 없으면 건드리지 않는다.**"""
    mine = [r for r in runs
            if r.get("metric") == metric.get("id") and r.get("completed") is not False]
    if not mine:
        return metric

    clicks = [int(r.get("clicks", 0)) for r in mine if r.get("clicks") is not None]
    elapsed = [int(r.get("elapsed_ms", 0)) for r in mine if r.get("elapsed_ms") is not None]

    out = dict(metric)
    out["measured"] = {
        "runs": len(mine),
        #: 가운뎃값이다 — 평균은 한 번의 긴 측정에 끌려간다.
        "clicks_median": statistics.median(clicks) if clicks else None,
        "elapsed_ms_median": statistics.median(elapsed) if elapsed else None,
    }
    out["measured_at"] = max((r.get("at") or "") for r in mine) or None
    out["why_null"] = None
    return out


def self_test() -> int:
    """양성·음성을 함께 잰다 — 한쪽만 재는 도구는 초록으로 죽는다."""
    fails = 0
    base = {
        "schema": SCHEMA,
        "metrics": [{"id": "u1_handle_event", "measured": None, "why_null": "아직"}],
        "runs": [],
    }
    dump = {
        "schema": SCHEMA,
        "runs": [
            {"metric": "u1_handle_event", "subject": "1", "clicks": 1,
             "elapsed_ms": 4000, "completed": True, "at": "2026-09-16T10:00:00Z"},
            {"metric": "u1_handle_event", "subject": "2", "clicks": 3,
             "elapsed_ms": 9000, "completed": True, "at": "2026-09-16T10:01:00Z"},
        ],
    }

    merged, added = merge(base, dump)
    if added != 2 or len(merged["runs"]) != 2:
        print(f"{TAG} 자기시험 FAIL 붙인 수가 다르다: {added}")
        fails += 1
    if merged["metrics"][0]["measured"]["clicks_median"] != 2:
        print(f"{TAG} 자기시험 FAIL 가운뎃값이 틀렸다")
        fails += 1

    # ① 같은 덤프를 다시 붙여도 **늘지 않는다**
    again, added2 = merge(merged, dump)
    if added2 != 0 or len(again["runs"]) != 2:
        print(f"{TAG} 자기시험 FAIL 같은 덤프가 두 번 세어졌다")
        fails += 1

    # ② 한 번도 안 잰 지표는 **null 로 남는다** (0 으로 채우지 않는다)
    untouched = merge(
        {"schema": SCHEMA, "metrics": [{"id": "u1_dead_camera_check", "measured": None}],
         "runs": []},
        {"schema": SCHEMA, "runs": []})[0]
    if untouched["metrics"][0]["measured"] is not None:
        print(f"{TAG} 자기시험 FAIL 안 잰 지표에 수가 생겼다")
        fails += 1

    # ③ 모양이 다른 덤프는 **거절한다**
    try:
        merge(base, {"schema": "something.else", "runs": []})
    except ValueError:
        pass
    else:
        print(f"{TAG} 자기시험 FAIL 남의 모양을 받았다")
        fails += 1

    # ④ [턴 T] **실물 표본** — 저장소의 실제 대장 + 가짜 값 1 → 줄지 않고 정확히 1 는다.
    #    합성 `base` 만 재면 실제 대장의 모양(metrics 넷 · runs 0)이 바뀌었을 때 못 본다.
    #    파일에는 쓰지 않는다 — 표본은 읽기다.
    if LEDGER.exists():
        try:
            real = json.loads(LEDGER.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{TAG} 자기시험 FAIL 실물 대장을 못 읽었다: {exc}")
            fails += 1
        else:
            before = len(real.get("runs") or [])
            fake = {"schema": SCHEMA, "runs": [
                {"metric": "u1_handle_event", "subject": "self-test",
                 "clicks": 1, "elapsed_ms": 1000, "completed": True,
                 "at": "1970-01-01T00:00:00Z"}]}
            grown, added_real = merge(real, fake)
            if added_real != 1 or len(grown["runs"]) != before + 1:
                print(f"{TAG} 자기시험 FAIL 실물 대장 {before}줄 + 1 이 "
                      f"{len(grown['runs'])}줄이 됐다")
                fails += 1
            if {m.get("id") for m in grown.get("metrics") or []} != {
                    "u1_handle_event", "u1_handover_note", "u1_dead_camera_check"}:
                print(f"{TAG} 자기시험 FAIL 실물 대장의 지표 셋이 아니다")
                fails += 1
            # 브라우저 덤프의 진단 칸(in_flight · storage_ok)은 **붙이지 않는다** —
            # 대장에는 끝난 측정만 든다.
            noisy = dict(fake, in_flight=[{"metric": "u1_handover_note"}], storage_ok=True)
            same, added_noisy = merge(real, noisy)
            if added_noisy != 1 or "in_flight" in same:
                print(f"{TAG} 자기시험 FAIL 진단 칸이 대장에 새었다")
                fails += 1
    else:
        print(f"{TAG} 자기시험 FAIL 실물 대장이 없다: {LEDGER}")
        fails += 1

    if fails:
        print(f"{TAG} 자기시험 {fails}건 실패")
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 양성 2 · 음성 3 · 실물 표본 1(대장 줄지 않음)")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="편리성 계측을 대장에 덧붙인다")
    ap.add_argument("--dump", default="", help="브라우저가 낸 JSON 경로")
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL
    if not args.dump:
        print(f"{TAG} **판정 불가** — 붙일 덤프가 없다. 브라우저에서 "
              f"window.__gxConvenience.export() 를 받아 파일로 주어라")
        return EXIT_UNDECIDABLE

    ledger_path = Path(args.ledger)
    dump_path = Path(args.dump)
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        dump = json.loads(dump_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"{TAG} **판정 불가** — 못 읽었다: {exc}")
        return EXIT_UNDECIDABLE

    before = len(ledger.get("runs") or [])
    try:
        merged, added = merge(ledger, dump)
    except ValueError as exc:
        print(f"{TAG} 멈춘다 — {exc}")
        return EXIT_FAIL

    ledger_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{TAG} 붙였다 — {before}줄 → {len(merged['runs'])}줄 (새로 {added}줄)")
    print(f"{TAG} ★ 이 수는 **기준선이지 합격선이 아니다** — 판정은 표와 사람이 한다")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
