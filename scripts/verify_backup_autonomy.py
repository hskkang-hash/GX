#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-19 판정기 — 백업이 **저절로** 도는가(RPO). (턴 AE 차선 E · P-264 · 조율자 교정 2026-09-23)

왜 이 파일이 따로 있나 — **한 게이트에 물음을 둘 넣지 마라**
--------------------------------------------------------------
`OPS-04`(백업이 있고 **그것으로 살아나는가**)와 `OPS-19`(**저절로** 도는가 · RPO)는
다른 질문이다. 처음엔 `verify_backup_recovery.py` 의 ㉡ 을 「beat 가 부른 덤프인가」로
바꿔서 두 질문을 한 게이트에 합쳤다. 그 결과:

    [OPS-04] ㉡ beat 덤프 빨강 — 판정문의 호출자가 'beat' 가 아니다(None)
    [OPS-04] 빨강 — 복구할 것이 남아 있지 않다.

**마지막 줄이 거짓이었다.** 금고에 149,701,407 바이트 덤프가 있고, 그것으로 232표를
살려 냈다(RTO 13.7초) — 복구할 것은 **남아 있었다.** OPS-19 의 참인 「아직 자동은
증명 못했다」가 OPS-04 의 참인 「오늘은 복구된다」를 덮은 것이다(조율자 실측).

그래서 자를 쪼갠다:

    `verify_backup_recovery.py` → **OPS-04** (㉡ = 「바이트 있는 덤프 ≤ 48h」· 되돌림)
    `verify_backup_autonomy.py` → **OPS-19** (이 파일 · ㉤ = 「beat 가 부른 덤프 ≤ 26h」)

이 파일은 새 판정 로직을 **만들지 않는다.** `verify_backup_recovery.py` 의
`judge_beat_dump()`(호출자·파일 일치·나이를 함께 보는 술어, 음성 대조 완비)를
**그대로 가져다 쓴다** — 같은 물음의 두 벌은 반드시 어긋난다(D-369).

무엇을 재나 — 셋(OPS-04 와 ㉠·㉢ 은 같은 자리를 본다, ㉡ 대신 ㉤)
------------------------------------------------------------------
  ㉠ `backup_last.json` 의 판정 — ALARM 이면 빨강 (OPS-04 와 같다)
  ㉤ **마지막 beat 덤프의 나이 ≤ 26h** — `invoked_by=="beat"` 이고 그 판정문이 가리키는
     파일이 금고의 최신 덤프와 같아야 한다(판정문만 믿지 않는다). 손으로 뜬 덤프에는
     속지 않는다(음성 대조 — `self_test()` 참조).
  ㉢ 복구 회수증 — 최근 성공 회수증이 있는가 (OPS-04 와 같다)

부르는 방향 — **호스트에서 부른다** (이 파일 안에 `docker exec` 가 있다 — 정확히는
`verify_backup_recovery.list_vault()` 를 통해서다).

    python scripts/verify_backup_autonomy.py
    python scripts/verify_backup_autonomy.py --self-test

끝값: 0=초록(자동으로 돈 것을 이 판정문으로 말할 수 있다) · 1=빨강 · 2=회색(못 쟀다).

되돌림: 이 스크립트는 **읽기만** 한다. 뜨지도 지우지도 않는다.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_backup_recovery as _bak   # 판정 로직의 정본 — 베끼지 않는다 (D-369)

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2


def run(now=None, rows=...):
    now = now or _bak.utcnow()
    if rows is ...:
        rows = _bak.list_vault()
    #: ★ 금고는 **한 번만** 센다(OPS-04 판정기와 같은 원칙) — 머리글이 말한 분모와
    #:   판정이 본 분모가 같아야 한다.
    vault = _bak.judge_vault(rows, now=now)
    raw_verdict = _bak._read_verdict_raw()
    return {
        "verdict": _bak.judge_verdict(now=now),
        "beat_dump": _bak.judge_beat_dump(vault, raw_verdict, now=now),
        "receipt": _bak.latest_receipt(now=now),
        #: 참고용 — OPS-04 가 보는 금고 신선도. 이 게이트의 rc 에는 **안 들어간다**
        #: (그건 저 파일의 물음이다). 사람이 두 판정을 나란히 대조하기 쉽게만 남긴다.
        "vault_freshness_ops04_ref": vault,
    }


def report(result) -> int:
    parts = [("㉠ 판정문", result["verdict"]), ("㉤ beat 덤프", result["beat_dump"]),
             ("㉢ 회수증", result["receipt"])]
    mark = {"OK": "초록", "FAIL": "빨강", "UNDECIDABLE": "회색"}
    receipt_n = result["receipt"].get("scanned", 0)
    print("[OPS-19] [입력] 판정문 %d · 회수증 후보 %d"
          % (1 if _bak.VERDICT_FILE.is_file() else 0, receipt_n))
    for label, item in parts:
        print("[OPS-19] %s %s — %s" % (label, mark.get(item.get("state"), "?"),
                                       item.get("why", "")))
    ref = result.get("vault_freshness_ops04_ref") or {}
    print("[OPS-19] (참고 · 이 게이트의 rc 에는 안 들어간다) OPS-04 금고 신선도: %s — %s"
          % (mark.get(ref.get("state"), "?"), ref.get("why", "")))
    states = [item.get("state") for _, item in parts]
    if "FAIL" in states:
        print("[OPS-19] 빨강 — 백업이 **저절로** 돌았다는 것을 이 판정문으로는 아직 못 말한다.")
        return EXIT_FAIL
    if "UNDECIDABLE" in states:
        print("[OPS-19] 회색 — 못 쟀다. **회색은 초록이 아니다.**")
        return EXIT_UNDECIDABLE
    print("[OPS-19] 초록 — beat 가 부른 덤프가 최근에 있다.")
    return EXIT_OK


# ───────────────────────────────────────────────────────────────────────────
# 자기시험 — ★ 조율자 교정(2026-09-23)이 요구한 **네 표본** + `judge_beat_dump()` 의
#   단위 표본(음성 대조·출생 표본 포함, `verify_backup_recovery.py` 에서 옮겨 옴)
# ───────────────────────────────────────────────────────────────────────────
def self_test() -> int:
    now = datetime(2026, 9, 23, 0, 46, tzinfo=timezone.utc)   # 실측 09:46 KST
    fresh = "20260922T030000Z"
    old = "20260907T190000Z"
    cases = []

    # ═══ 조율자가 요구한 네 표본 — 오늘의 실물로 「두 물음이 다른 답을 낼 수 있다」를 보인다 ═══
    today_file = "db_database_guardianx_20260922T200000Z.dump"
    vault_today = _bak.judge_vault(
        [("/backup/20260922/" + today_file, 149_701_407)], now)
    raw_today_no_invoke = {"measured_at": "2026-09-22T20:00:00+00:00", "verdict": "OK",
                           "manifest": {"db": {"file": today_file, "bytes": 149_701_407}}}
    raw_today_beat = dict(raw_today_no_invoke, invoked_by="beat")

    # ① ㉡(OPS-04, 금고 신선도)은 초록인데 ㉤(OPS-19, beat 호출자)은 빨강 — **오늘의 실물.**
    #    한 사실에 두 다른 색이 나는 것이 옳다 — 그것이 이 교정 전체의 이유다.
    cases.append(("① 오늘의 실물: OPS-04(㉡ 금고 신선도)는 초록",
                  vault_today["state"] == "OK"))
    cases.append(("① 오늘의 실물: OPS-19(㉤ beat 덤프)는 빨강 — invoked_by 없음",
                  _bak.judge_beat_dump(vault_today, raw_today_no_invoke, now)["state"]
                  == "FAIL"))

    # ② 둘 다 초록 — invoked_by="beat" 가 실린 뒤(다음 beat 실행 이후)의 모습
    cases.append(("② 둘 다 초록: invoked_by=beat 가 실리면",
                  vault_today["state"] == "OK" and
                  _bak.judge_beat_dump(vault_today, raw_today_beat, now)["state"] == "OK"))

    # ③ 둘 다 빨강 — 금고 전체가 늙었을 때(정기 백업이 그냥 안 돈 상태)
    old_file = "db_x_%s.dump" % old
    vault_old = _bak.judge_vault([("/backup/" + old_file, 40_000_000)], now)
    raw_beat_old_file = {"invoked_by": "beat", "manifest": {"db": {"file": old_file}}}
    cases.append(("③ 둘 다 빨강: 금고 전체가 늙으면",
                  vault_old["state"] == "FAIL" and
                  _bak.judge_beat_dump(vault_old, raw_beat_old_file, now)["state"] == "FAIL"))

    # ④ ★★ ㉤ 음성 대조 — 손 덤프만 있는 금고에는 ㉤ 초록이 나면 안 된다(필수)
    raw_manual = dict(raw_today_no_invoke, invoked_by="manual")
    cases.append(("④ ★★ ㉤ 음성 대조: 금고에 바이트 있는 최신 덤프가 있어도 "
                  "판정문이 manual 이면 빨강 — 손으로 뜬 덤프만 있는 금고는 초록이 아니다",
                  _bak.judge_beat_dump(vault_today, raw_manual, now)["state"] == "FAIL"))

    # ═══ judge_beat_dump() 단위 표본 (verify_backup_recovery.py 에서 옮겨 옴) ═══
    fresh_name = "db_x_%s.dump" % fresh
    vault_fresh = _bak.judge_vault([("/backup/" + fresh_name, 5_000_000)], now)
    vault_unreachable = _bak.judge_vault(None, now)

    raw_beat_ok = {"invoked_by": "beat", "manifest": {"db": {"file": fresh_name}}}
    cases.append(("양성: invoked_by=beat 이고 파일이 금고 최신과 같으면 초록",
                  _bak.judge_beat_dump(vault_fresh, raw_beat_ok, now)["state"] == "OK"))

    cases.append(("음성: invoked_by 칸이 아예 없으면 빨강",
                  _bak.judge_beat_dump(vault_fresh, {}, now)["state"] == "FAIL"))

    raw_mismatch = {"invoked_by": "beat",
                    "manifest": {"db": {"file": "db_x_20260921T200000Z.dump"}}}
    cases.append(("음성: invoked_by=beat 이어도 판정문 파일과 금고 최신 파일이 다르면 빨강",
                  _bak.judge_beat_dump(vault_fresh, raw_mismatch, now)["state"] == "FAIL"))

    raw_beat_old = {"invoked_by": "beat", "manifest": {"db": {"file": old_file}}}
    cases.append(("음성: invoked_by=beat · 파일 일치 · 그러나 26h 를 넘으면 빨강",
                  _bak.judge_beat_dump(vault_old, raw_beat_old, now)["state"] == "FAIL"))

    cases.append(("음성: 금고에 바이트 있는 덤프가 없으면 beat 판정문이 있어도 빨강",
                  _bak.judge_beat_dump(vault_unreachable, raw_beat_ok, now)["state"]
                  == "FAIL"))

    # ★★ 출생 표본 — 이 개선을 낳은 바로 그 판정문 (배선 전/후 대조)
    cases.append(("★★ 출생 표본: 배선 전 실제 판정문(invoked_by 없음)은 "
                  "실제 자동 덤프가 있어도 ㉤ 을 못 채운다",
                  _bak.judge_beat_dump(vault_today, raw_today_no_invoke, now)["state"]
                  == "FAIL"))
    cases.append(("★★ 출생 표본: 같은 실물에 invoked_by=beat 만 더하면 초록",
                  _bak.judge_beat_dump(vault_today, raw_today_beat, now)["state"] == "OK"))

    bad = 0
    for label, ok in cases:
        print("  [%s] %s" % ("통과" if ok else "**실패**", label))
        bad += 0 if ok else 1
    print("[SELF-TEST] %d건 중 %d건 실패" % (len(cases), bad))
    return EXIT_OK if bad == 0 else EXIT_FAIL


def _header(rows) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header          # P-107 — TARGET/AS/SOURCE
    n_vault = 0 if rows is None else len(rows)
    receipts = (len(list(_bak.RECEIPT_DIR.glob("restore_run*.md")))
                if _bak.RECEIPT_DIR.is_dir() else 0)
    receipts += 1 if _bak.DRILL_FILE.is_file() else 0
    verdict_n = 1 if _bak.VERDICT_FILE.is_file() else 0
    total = (n_vault if rows is not None else 0) + receipts + verdict_n
    gate_header(
        __file__,
        target=("호스트 + 컨테이너 «%s» 의 금고 «%s» · 증거 파일 D-373/backup_last.json"
                % (_bak.VAULT_CONTAINER, _bak.VAULT_PATH)),
        as_=("(계정 없음) — `docker exec` 로 금고를 **읽기만** 한다(`verify_backup_recovery."
             "list_vault()` 를 통해서). 이 파일 안에 그 호출이 있으므로 **호스트에서** 부른다"),
        source=("기계가 쓴 판정문의 `invoked_by` 칸 + 그 판정문이 가리키는 파일명을 "
                "금고의 실제 최신 덤프와 대조 — 판정문만 믿지 않는다"),
        measured=("㉤ — 마지막 **beat** 가 부른 덤프의 나이 ≤ %dh — **분모 %d**"
                  "(금고 덤프 %s · 회수증 후보 %d · 판정문 %d). OPS-04"
                  "(`verify_backup_recovery.py`)의 ㉡(바이트 신선도, 48h)과는 "
                  "**다른 물음**이다 — 이 게이트는 그것을 rc 에 안 넣는다"
                  % (_bak.FRESH_BEAT_DUMP_HOURS, total,
                     "못 셈" if rows is None else n_vault, receipts, verdict_n)),
    )


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="OPS-19 — 백업이 저절로 도는가 (RPO)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="판정을 json 으로도 찍는다")
    args = ap.parse_args()

    #: ★ 자기시험 때도 머리글을 찍는다(`verify_gate_header.py` 가 `--self-test` 로 게이트를
    #:   연다) · 금고는 한 번만 센다(머리글이 말한 분모와 판정이 본 분모가 같아야 한다).
    rows = _bak.list_vault()
    _header(rows)
    if args.self_test:
        return self_test()

    result = run(rows=rows)
    rc = report(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return rc


if __name__ == "__main__":
    sys.exit(main())
