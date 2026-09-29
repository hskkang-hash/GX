#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-392 · WO-17 §4 O — 「제목이 부르는 것 ↔ 있는 것」 표 빈 칸 게이트.
차선 O · 턴 AN. 시험 DB `test_gx_lane_o`(참고용 — 이 게이트 자체는 gx-shell 도
DB 도 안 쓴다. 대장 YAML 과 `docs/agent/evidence/SPEC/*.json` 만 읽는다).

무엇을 재는가
-------------
`_규약.md`(별표 절 승격 P-356 넷)의 둘째 조건은 증거 안에 **「제목이 부르는 것
↔ 있는 것」 표**(`title_parts: [{part, where, status}]` · 빈 칸 0)를 두는 것이다.
이 게이트가 그 표의 **빈 칸**을 센다 — 아무도 안 세면 반쪽 승격이 초록으로 읽힌다.

입력 — **읽는 규칙은 베낀 것이지 다시 정한 것이 아니다**
---------------------------------------------------------
대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에서 **annex 에서 옮겨 온
DSM-/FWS-/O- 절**을 뽑는다. 그 규칙은 `scripts/verify_spec_coverage.py::
promoted_ids()` 가 이미 쓰는 규칙이다 — `areas[].clauses[].id` 를 정본으로
삼는다(그 함수 주석, 2026-09-29 확인: `area_ids = {(c.get("id") or "").strip()
for a in (data.get("areas") or []) for c in (a.get("clauses") or [])}`).
판정기끼리 import 는 금지(D-212 · 서로 다른 차선 소유)라 **읽는 방식만 베끼고
출처를 여기 적는다** — `promoted_area7_ids()` 가 그 자리다.

★ 그런데 이 게이트는 「전체 등재」가 아니라 **영역 "7"** 로 좁힌다(WO-17 지시).
  2026-09-29 실측: DSM-/FWS-/O- 접두 id 는 대장의 **영역 7("가용성")에만** 39건
  나타나고, 다른 일곱 영역에는 **0건**이다(`promoted_area7_ids()` 가 그 사실도
  방어적으로 잰다 — 접두 id 가 영역 7 밖에서 보이면 이상행으로 따로 낸다).

닫힘 상태 값 — **실측이 0건이라 관례로 잡는다**
------------------------------------------------
`title_parts[].status` 가 「닫혔다」로 읽히는 값의 목록이 필요하다. 2026-09-29
`docs/agent/evidence/SPEC/*.json` 전수(42건)를 실측했다 — **`title_parts` 키를
쓰는 파일이 0건**이다(이 표가 이번 턴에 처음 요구되기 때문). 그래서 이 목록은
「SPEC 폴더에서 실측한 값」이 아니라 **이 저장소가 이미 쓰는 관례어**를 기본값
으로 잡은 것이다 — 이 파일들이 근거다:
    · `docs/agent/evidence/SPEC/O_promotions.md`·`N1_promotions.md` 의 승격 표
      머리글이 「있는 것」이라는 낱말을 쓴다 → 한국어 닫힘 값은 **"있음"**.
    · `scripts/verify_spec_fws_f6.py` 류의 판정 산문이 "완료"·"닫힘" 을 섞어 쓴다.
    · 다른 차선이 영어로 적을 가능성을 막지 않으려고 "ok"/"present"/"done" 도 둔다.
CLOSED_STATUS 가 그 목록이다. **다음 판이 실제 값을 SPEC 폴더에 남기면 이 목록에
보태고 이 주석을 「실측」으로 고친다** — 지금은 정직하게 「관례 추정」이라 적는다.

판정 — 셋으로 가른다(옛 승격을 빨강으로 만들지 않는다)
--------------------------------------------------------
    ① **표 있고 빈 칸/열린 행 ≥ 1**            → **RED**(반쪽 승격)
    ② **표 자체가 없다**(`title_parts` 키 없음) → **GREY** 「옛 승격 · 표 없음」
       — 대장은 안 줄인다. 소급 빨강은 세종 판정 몫(이 게이트의 결론은 보고의
       「청구」줄에 남긴다). ⚠ **이 턴(AN)부터 새로 올리는 증거는 표가 필수** —
       이 물러섬은 턴 AK~AM 유산에만 적용된다는 뜻이지, 앞으로도 봐준다는 뜻이
       아니다(그래서 최종 exit 은 옛 승격이 몇 건이든 이 사실만으로는 안 내려간다
       — `verify_spec_fws_f6.py::NOT_STARTED` 가 이미 세운 그 전례: 「주장하지
       않은 것」은 실패로 세지 않는다).
    ③ **증거 파일 자체가 없다** / **JSON 이 표(object) 가 아니다** → **GREY**
       (못 쟀다 — `verify_spec_fws_f6.py::judge_evidence` 의 `payload is None →
       EXIT_UNDECIDABLE` 과 같은 전례. 이미 대장에 승격돼 있는 절이라도 증거가
       비면 「빨강」이 아니라 「못 쟀다」로 낸다 — 그 전례를 이 게이트도 따른다).

종료 코드(저장소 규약 D-400)
    0 = 쟀고 통과(①이 0건)   1 = 쟀고 실패(①이 1건 이상)   2 = 못 쟀다(대장/영역 7 을 못 읽었다)

    python scripts/verify_spec_title_parts.py             # 판정(호스트 — 파일만 읽는다)
    python scripts/verify_spec_title_parts.py --self-test   # 판정 규칙만
    python scripts/verify_spec_title_parts.py --list        # 절별 한 줄씩 다 보인다

무엇을 하지 않는가
------------------
대장 이동 · 게이트 행 추가는 이 게이트의 일이 아니다 — 조율자가 한다(넣을 조각은
`docs/agent/checkpoints/turn-an/O.md` 에 있다).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "agent" / "evidence" / "D-346" / "ga_readiness.yaml"
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
TAG = "[SPEC-TITLE]"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

EXIT_OK, EXIT_RED, EXIT_GREY = 0, 1, 2

#: annex 에서 옮겨 온 절의 접두 — 대장 원문 모양 그대로(DSM-U*-*· FWS-[FU]*-* · O-**).
PROMOTED_PREFIX = re.compile(r"^(?:DSM|FWS|O)-")

#: 이 게이트가 좁히는 영역. WO-17 §4 O 지시 · 2026-09-29 실측(접두 id 39건이
#: 전부 이 영역에만 있다).
AREA7_ID = "7"

#: 닫힘으로 읽는 status 값 — 위 머리글 "닫힘 상태 값" 참조(실측 0건 · 관례 추정).
#: 대소문자 무시(영문만) · 앞뒤 공백 제거 뒤 비교.
CLOSED_STATUS = frozenset({"있음", "완료", "닫힘", "ok", "present", "done", "closed"})
#: [턴 AN 창 ② · 조율자 · 첫 판정 전] SPEC 폴더 **실측** 낱말(차선 N1~N4 가 쓴 것) — 표 칸이
#: 닫힘을 이 **앞머리**로 적는다: `measured`(35) · `present`(32) · `있음…`(22) · `구현 — …`(7).
#: 열린 쪽 실측: `없음(…)` · `부분(…)` · `missing …` · `[미확인]` · `… 대안 그대로` · `근사 실측` ·
#: `정직하게 비움` — 이것들은 앞머리가 위와 안 겹친다(그래서 열린 행으로 남는다).
CLOSED_PREFIXES = ("measured", "present", "있음", "구현")

#: [턴 AO · P-406 · 차선 N1] **결정으로 뺀 행** — `title_parts[].excluded_by` 가
#: 결정 번호 모양(`P-###` 또는 `D-###`)이고 `excluded_why`(사유 1줄)가 있으면
#: 그 행은 status 앞머리와 무관하게 닫힘이다(§5 P-406). **번호 없는 「없음」은
#: 여전히 빈 칸/열린 행이다** — `excluded_by` 가 없거나 이 모양이 아니면 이 규칙은
#: 적용되지 않는다(예: `excluded_by: "없음"` · `excluded_by` 키 자체가 없음).
EXCLUDED_BY_RE = re.compile(r"^(?:P|D)-\d{3}$")

#: [턴 AO · P-406 · 차선 N1] **대리 지표는 반쪽이다** — 제목이 부르는 수를 다른
#: 수로 근사했으면(status 가 이 앞머리로 시작) 열린 행이다. `CLOSED_PREFIXES`
#: 와 겹치지 않는지 `self_test` 가 확인한다(아래 「겹침 없음」 표본).
PROXY_PREFIXES = ("근사", "대리", "proxy")


def _is_excluded_closed(row: dict) -> bool:
    """P-406 — 결정으로 뺀 행인가(번호 + 사유 둘 다 있어야 닫힘)."""
    by = row.get("excluded_by")
    why = row.get("excluded_why")
    if not isinstance(by, str) or not EXCLUDED_BY_RE.match(by.strip()):
        return False
    return isinstance(why, str) and bool(why.strip())


def _is_proxy(status) -> bool:
    """대리 지표 — status 앞머리가 근사/대리/proxy 면 반쪽(열린 행)이다."""
    if not isinstance(status, str):
        return False
    st = status.strip().lower()
    return st.startswith(tuple(p.lower() for p in PROXY_PREFIXES))


# ═══════════════════════════════════════════════════════════════════════════
# ① 대장을 읽는다 — promoted_ids() 의 읽는 방식을 베낀다(출처는 머리글)
# ═══════════════════════════════════════════════════════════════════════════
def load_ledger() -> tuple[dict | None, str]:
    if not LEDGER.is_file():
        return None, "대장 파일이 없다: %s" % LEDGER
    try:
        import yaml  # noqa: PLC0415
        data = yaml.safe_load(LEDGER.read_text(encoding="utf-8", errors="replace")) or {}
    except Exception as exc:                                     # noqa: BLE001
        return None, "대장을 못 읽었다: %s" % exc
    if not isinstance(data, dict):
        return None, "대장의 최상위가 표(object) 가 아니다"
    return data, ""


def promoted_area7_ids(data: dict) -> tuple[list[str], list[str], bool]:
    """`(영역7 안의 접두 id · 영역7 밖에서 보인 같은 접두 id · 영역7 이 있었나)`.

    ★ 읽는 자리는 `scripts/verify_spec_coverage.py::promoted_ids()` 와 같다
      (`areas[].clauses[].id`). 다만 그 함수는 **입력 id 목록과 교집합**을 내고,
      이 함수는 **영역 7 로 좁혀 접두로** 뽑는다 — WO-17 §4 O 가 요구하는 자리가
      다르기 때문이다(주석 참조). 같은 대장 구조를 두 번 다른 목적으로 읽는 것이지
      두 벌의 「승격이란 무엇인가」 규칙을 두는 것이 아니다.
    """
    areas = data.get("areas") or []
    area7_found = False
    seen: set[str] = set()
    in7: list[str] = []
    outside7: list[str] = []
    for a in areas:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") if a.get("id") is not None else "").strip()
        if aid == AREA7_ID:
            area7_found = True
        for c in (a.get("clauses") or []):
            if not isinstance(c, dict):
                continue
            cid = (c.get("id") or "").strip()
            if not cid or not PROMOTED_PREFIX.match(cid):
                continue
            if aid == AREA7_ID:
                if cid not in seen:
                    seen.add(cid)
                    in7.append(cid)
            else:
                outside7.append(cid)
    return in7, outside7, area7_found


# ═══════════════════════════════════════════════════════════════════════════
# ② 증거 — title_parts 표를 읽는다
# ═══════════════════════════════════════════════════════════════════════════
def _load_evidence(clause_id: str) -> tuple[dict | None, str]:
    path = EVIDENCE_DIR / ("%s.json" % clause_id)
    if not path.is_file():
        return None, "증거 파일이 없다: %s" % path.name
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace")), ""
    except (ValueError, OSError) as exc:                          # noqa: BLE001
        return None, "증거 파일을 못 읽었다(%s): %s" % (path.name, exc)


def _is_closed(status) -> bool:
    if not isinstance(status, str):
        return False
    st = status.strip().lower()
    return st in CLOSED_STATUS or st.startswith(CLOSED_PREFIXES)


def judge_title_parts(title_parts) -> dict:
    """표 한 장을 순수하게 판정한다(D-277 — 파일 없이 시험한다).

    돌려주는 것 `{"kind": ...}`:
      "missing"   — 표 자체가 없다(`None`)
      "malformed" — 표는 있는데 모양이 아니다(목록이 아니다 · 행이 0 · 행이 표가 아니다)
      "measured"  — `n_rows · n_blank_cells · n_open_rows · detail` 을 낸다
    """
    if title_parts is None:
        return {"kind": "missing"}
    if not isinstance(title_parts, list):
        return {"kind": "malformed",
                "why": "title_parts 가 목록이 아니다(%s)" % type(title_parts).__name__}
    if not title_parts:
        return {"kind": "malformed",
                "why": "title_parts 키는 있으나 행이 0 — 표가 있다고 말하며 빈 목록이다"}
    n_blank, n_open = 0, 0
    detail = []
    for i, row in enumerate(title_parts):
        if not isinstance(row, dict):
            return {"kind": "malformed",
                    "why": "title_parts[%d] 이 표(dict) 가 아니다" % i}
        blanks_here = [f for f in ("part", "where", "status")
                       if not isinstance(row.get(f), str) or not row.get(f).strip()]
        n_blank += len(blanks_here)
        status = row.get("status")
        #: P-406 결정 제외가 최우선(번호+사유가 있으면 status 앞머리와 무관하게
        #: 닫힘) — 그다음 실측 닫힘 앞머리, 단 대리 지표(근사/대리/proxy)는
        #: 결정 제외가 아닌 한 언제나 열린 행이다(「대리 지표는 반쪽」).
        excluded = _is_excluded_closed(row)
        closed = excluded or (_is_closed(status) and not _is_proxy(status))
        if not closed:
            n_open += 1
        detail.append({"row": i, "blanks": blanks_here, "closed": closed,
                       "status": row.get("status")})
    return {"kind": "measured", "n_rows": len(title_parts),
            "n_blank_cells": n_blank, "n_open_rows": n_open, "detail": detail}


def classify_payload(clause_id: str, payload) -> dict:
    """증거 페이로드 하나 → 판정 한 줄. **순수 함수**(자기시험이 파일 없이 돌린다)."""
    if payload is None:
        return {"id": clause_id, "verdict": "grey", "bucket": "no_evidence",
                "detail": "증거 파일이 없다(못 쟀다)"}
    if not isinstance(payload, dict):
        return {"id": clause_id, "verdict": "grey", "bucket": "malformed",
                "detail": "증거 JSON 이 표(object) 가 아니다"}
    j = judge_title_parts(payload.get("title_parts"))
    if j["kind"] == "missing":
        return {"id": clause_id, "verdict": "grey", "bucket": "legacy_no_table",
                "detail": "title_parts 표가 없다 — 옛 승격(턴 AN 이전)으로 본다. "
                         "빨강으로 만들지 않는다(대장은 안 줄인다 · 소급 빨강은 세종 몫)"}
    if j["kind"] == "malformed":
        return {"id": clause_id, "verdict": "grey", "bucket": "malformed", "detail": j["why"]}
    if j["n_blank_cells"] or j["n_open_rows"]:
        return {"id": clause_id, "verdict": "red", "bucket": "half",
                "detail": "표 %d행 · 빈 칸 %d · 열린 행 %d — 반쪽 승격"
                         % (j["n_rows"], j["n_blank_cells"], j["n_open_rows"]),
                "rows": j["n_rows"], "blank": j["n_blank_cells"], "open": j["n_open_rows"]}
    return {"id": clause_id, "verdict": "ok", "bucket": "clean",
            "detail": "표 %d행 · 빈 칸 0 · 열린 행 0" % j["n_rows"]}


def classify_clause(clause_id: str) -> dict:
    payload, why = _load_evidence(clause_id)
    rep = classify_payload(clause_id, payload)
    if payload is None and why:
        rep["detail"] = why
    return rep


# ═══════════════════════════════════════════════════════════════════════════
# ③ 모은다
# ═══════════════════════════════════════════════════════════════════════════
def measure() -> dict:
    data, why = load_ledger()
    if data is None:
        return {"ok": False, "why": why}
    in7, outside7, area7_found = promoted_area7_ids(data)
    if not area7_found:
        return {"ok": False,
                "why": "대장에서 영역 id==\"7\" 을 못 찾았다 — 대장 구조가 바뀌었을 수 있다"}
    results = [classify_clause(cid) for cid in in7]
    buckets: dict[str, list] = {"ok": [], "half": [], "legacy_no_table": [],
                                "no_evidence": [], "malformed": []}
    for r in results:
        buckets.setdefault(r["bucket"], []).append(r)
    return {"ok": True, "promoted_n": len(in7), "ids": in7, "outside7": outside7,
            "results": results, "buckets": buckets}


# ═══════════════════════════════════════════════════════════════════════════
# 출력
# ═══════════════════════════════════════════════════════════════════════════
def report(rep: dict, *, list_all: bool = False) -> int:
    if not rep.get("ok"):
        print("%s [입력] 승격 절 0건(못 읽었다)" % TAG)
        print("%s ? **회색(exit 2)** — %s" % (TAG, rep.get("why", "?")))
        return EXIT_GREY

    n = rep["promoted_n"]
    b = rep["buckets"]
    print("%s [입력] 승격(영역 7 · DSM-/FWS-/O- 접두) **%d건** · 표 있고 빈칸/열린 행 "
         "1+(반쪽) **%d** · 표 있고 깨끗함 %d · 옛 승격·표 없음(그레이) %d · "
         "증거 없음(그레이) %d · 표 모양 이상(그레이) %d"
         % (TAG, n, len(b["half"]), len(b["ok"]), len(b["legacy_no_table"]),
            len(b["no_evidence"]), len(b["malformed"])))

    if rep["outside7"]:
        uniq_outside = sorted(set(rep["outside7"]))
        print("%s   ? 이상행 — 영역 7 밖에서도 DSM-/FWS-/O- 접두 id 가 보인다(%d건): %s "
             "— 판정에는 안 넣는다(이 게이트는 영역 7 만 본다는 WO 지시), 대장 구조 점검용 관측"
             % (TAG, len(uniq_outside), ", ".join(uniq_outside[:10])
                + (" …" if len(uniq_outside) > 10 else "")))

    for r in rep["results"]:
        if r["verdict"] == "red" or list_all:
            mark = {"red": "X   ", "grey": "?   ", "ok": "OK  "}[r["verdict"]]
            print("%s %s [%s] %s" % (TAG, mark, r["id"], r["detail"]))

    if b["legacy_no_table"]:
        print("%s   ? 옛 승격 · 표 없음 **%d건**: %s"
             % (TAG, len(b["legacy_no_table"]),
                ", ".join(r["id"] for r in b["legacy_no_table"])))
    if b["no_evidence"]:
        print("%s   ? 증거 없음 **%d건**: %s"
             % (TAG, len(b["no_evidence"]), ", ".join(r["id"] for r in b["no_evidence"])))
    if b["malformed"]:
        print("%s   ? 표 모양 이상 **%d건**: %s"
             % (TAG, len(b["malformed"]), ", ".join(r["id"] for r in b["malformed"])))

    if b["half"]:
        print("%s X **빨강** %d건 — 표가 있는데 빈 칸/열린 부분이 남았다(반쪽 승격은 닫힘이 아니다)"
             % (TAG, len(b["half"])))
        return EXIT_RED

    print("%s O **초록의 뜻**: 영역 7 의 승격 절 %d건 중 표를 가진 것은 전부 빈 칸 0 · "
         "열린 행 0 이다. 표가 아직 없는 %d건(옛 승격)은 실패로 세지 않았다 — "
         "그 사실이 이 초록의 한계다(청구는 보고 문서에 남긴다)"
         % (TAG, n, len(b["legacy_no_table"])))
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310·D-277) — 순수 함수만 두드린다, 파일을 안 만든다
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def ok(name, good):
        cases.append((name, bool(good)))

    # ── judge_title_parts ────────────────────────────────────────────────
    ok("표 없음(None) → missing",
       judge_title_parts(None)["kind"] == "missing")
    ok("표는 있으나 목록이 아니다 → malformed",
       judge_title_parts({"part": "x"})["kind"] == "malformed")
    ok("표는 있으나 행이 0 → malformed(빈 목록은 표가 아니다)",
       judge_title_parts([])["kind"] == "malformed")
    ok("행이 dict 가 아니다 → malformed",
       judge_title_parts(["안행"])["kind"] == "malformed")

    _clean = [{"part": "수위", "where": "GET /a", "status": "있음"},
             {"part": "강우량", "where": "GET /b", "status": "ok"}]
    j = judge_title_parts(_clean)
    ok("★ 깨끗한 표본 — 빈 칸 0 · 열린 행 0",
       j["kind"] == "measured" and j["n_blank_cells"] == 0 and j["n_open_rows"] == 0
       and j["n_rows"] == 2)

    _blank = [{"part": "수위", "where": "", "status": "있음"},
             {"part": "", "where": "GET /b", "status": ""}]
    j = judge_title_parts(_blank)
    ok("★★ 빈 칸 표본 — where 하나 + part·status 둘 = 빈 칸 3, 마지막 행은 status 도 "
       "비어 열린 행이기도 하다(열린 행 1)",
       j["n_blank_cells"] == 3 and j["n_open_rows"] == 1)

    _open = [{"part": "수위", "where": "GET /a", "status": "있음"},
            {"part": "강우량", "where": "GET /b", "status": "미확인"}]
    j = judge_title_parts(_open)
    ok("★ 열린 부분 표본 — 칸은 다 찼지만 status 가 닫힘이 아니다 → 빈 칸 0 · 열린 행 1",
       j["n_blank_cells"] == 0 and j["n_open_rows"] == 1)

    # ★ 출생 표본(턴 AN 창 ② 실측 · 2026-09-29) — 이 게이트가 처음 막은 반쪽 승격.
    #   FWS-F3-11(대피 초안)은 차선 보고가 「닫음」이었고 게이트 행도 PASS 였다. 표의
    #   두 행이 닫힘이 아니었다(아래는 그 증거 파일의 status 앞머리 그대로). 조율자는
    #   이것을 보고 승격을 되돌렸다 — 이 표가 초록이면 이 도구는 태어난 까닭을 잊은 것이다.
    _birth = [{"part": "대피 대상 마을", "where": "POST …/evacuations/{id}/plan", "status": "measured"},
              {"part": "마을방송문", "where": "integration.draft_evacuation_notice",
               "status": "F6-07 대안 그대로 — 별도 필드 없음(문안 공용)"},
              {"part": "앱 푸시", "where": "(없음)",
               "status": "[미확인] — 산림청 스마트산림재난 앱 연동은 F6-07 이 이미 범위 밖으로 남겼다"}]
    j = judge_title_parts(_birth)
    ok("★ 출생 표본 — FWS-F3-11: 「대안 그대로」·「[미확인]」 두 행은 열린 행이다 → 반쪽",
       j["n_blank_cells"] == 0 and j["n_open_rows"] == 2)
    ok("★ 실측 닫힘 앞머리(measured · present · 있음… · 구현 — …)는 닫힘이다",
       _is_closed("measured") and _is_closed("있음(신규)") and _is_closed("구현 — 3명 실측")
       and not _is_closed("없음(범위 밖 — 별도 절)") and not _is_closed("근사 실측 — x")
       and not _is_closed("정직하게 비움[None]"))

    ok("닫힘 값은 대소문자 무시(영문) · 앞뒤 공백 무시",
       _is_closed("  OK  ") and _is_closed("Present") and _is_closed("있음"))
    ok("닫힘 값이 아닌 것은 안 닫힘",
       not _is_closed("검토중") and not _is_closed("") and not _is_closed(None))

    # ── P-406 결정 제외 · 대리 지표(턴 AO · 차선 N1) ────────────────────────
    ok("CLOSED_PREFIXES 와 PROXY_PREFIXES 는 앞머리가 안 겹친다(자기시험이 확인)",
       not any(c.lower().startswith(p.lower()) or p.lower().startswith(c.lower())
              for c in CLOSED_PREFIXES for p in PROXY_PREFIXES))

    _row_excluded_numbered = {"part": "산림청 앱 실제 푸시", "where": "(없음)",
                              "status": "없음(세종 판정)",
                              "excluded_by": "P-392", "excluded_why": "산림청 "
                              "스마트산림재난 앱 연동은 F6-07 이 범위 밖으로 "
                              "남겼다"}
    ok("★ P-406 짝 ① — excluded_by 번호(P-###) + excluded_why 있음 → 닫힘",
       _is_excluded_closed(_row_excluded_numbered))
    j = judge_title_parts([_row_excluded_numbered])
    ok("★ 표 안에서도 닫힘으로 잡힌다(열린 행 0)", j["n_open_rows"] == 0)

    _row_excluded_no_number = {"part": "산림청 앱 실제 푸시", "where": "(없음)",
                               "status": "없음(세종 판정)"}
    ok("★ P-406 짝 ② — excluded_by 번호 없음(키 자체가 없음) → 여전히 열린 행",
       not _is_excluded_closed(_row_excluded_no_number))
    j = judge_title_parts([_row_excluded_no_number])
    ok("★ 표에서도 열린 행 1(번호 없는 「없음」은 빈 칸과 같은 대접)",
       j["n_open_rows"] == 1)

    _row_excluded_bad_number = {"part": "x", "where": "y", "status": "없음",
                                "excluded_by": "없음", "excluded_why": "사유"}
    ok("★ excluded_by 값 자체가 결정 번호 모양이 아니면(예: '없음') → 안 닫힘",
       not _is_excluded_closed(_row_excluded_bad_number))

    _row_excluded_no_why = {"part": "x", "where": "y", "status": "없음",
                            "excluded_by": "P-392", "excluded_why": ""}
    ok("★ excluded_why 가 비면(사유 없음) → 번호가 있어도 안 닫힘",
       not _is_excluded_closed(_row_excluded_no_why))

    _row_proxy = {"part": "골든타임 준수율", "where": "확인 회신 30분 비율",
                 "status": "대리 지표 — 확인 회신 30분 비율로 근사"}
    ok("★ P-406 짝 ③ — 대리(대리/근사/proxy 앞머리) → 열린 행",
       _is_proxy(_row_proxy["status"]) and not _is_closed(_row_proxy["status"]))
    j = judge_title_parts([_row_proxy])
    ok("★ 표에서도 열린 행 1(대리 지표는 반쪽)", j["n_open_rows"] == 1)

    _row_proxy_approx = {"part": "x", "where": "y", "status": "근사 실측 — x"}
    ok("★ '근사' 앞머리도 대리와 같이 열린 행", _is_proxy(_row_proxy_approx["status"]))

    _row_proxy_en = {"part": "x", "where": "y", "status": "Proxy metric for X"}
    ok("★ 영문 'proxy' 앞머리도 대소문자 무시하고 열린 행",
       _is_proxy(_row_proxy_en["status"]))

    # ── classify_payload ─────────────────────────────────────────────────
    ok("증거 없음(None) → grey · no_evidence",
       classify_payload("X-01", None) == {"id": "X-01", "verdict": "grey",
                                           "bucket": "no_evidence",
                                           "detail": "증거 파일이 없다(못 쟀다)"})
    ok("증거가 표(object) 가 아니다 → grey · malformed",
       classify_payload("X-01", ["아님"])["bucket"] == "malformed")
    ok("★★ 표 없음(title_parts 키 없음) → **grey(옛 승격)**, red 가 아니다",
       classify_payload("X-01", {"id": "X-01", "what": "실측"})["verdict"] == "grey")
    r = classify_payload("X-01", {"title_parts": _blank})
    ok("★★★ 표 있고 빈 칸 있음 → **red · half**(반쪽 승격이 이 게이트의 핵심 표적이다)",
       r["verdict"] == "red" and r["bucket"] == "half")
    r = classify_payload("X-01", {"title_parts": _clean})
    ok("표 있고 깨끗함 → ok · clean",
       r["verdict"] == "ok" and r["bucket"] == "clean")

    # ── promoted_area7_ids — 대장 구조를 흉내 낸 표본(파일 안 만든다) ──────
    _ledger = {"areas": [
        {"id": "2", "clauses": [{"id": "SEC-01"}, {"id": "DSM-U9-99"}]},
        {"id": "7", "clauses": [{"id": "DSM-U3-03"}, {"id": "FWS-F1-01"},
                                {"id": "DSM-U3-03"},   # 중복 — 한 번만 센다
                                {"id": "SEC-02"},      # 접두 밖 — 안 센다
                                {"id": "O-05"}]},
    ]}
    in7, outside7, found = promoted_area7_ids(_ledger)
    ok("★ 영역 7 접두 id 를 뽑는다(순서 유지 · 중복 제거) — DSM-U3-03·FWS-F1-01·O-05",
       in7 == ["DSM-U3-03", "FWS-F1-01", "O-05"])
    ok("★★ 영역 7 **밖**에서 보인 같은 접두 id 도 따로 잡는다(이번 표본은 DSM-U9-99)",
       outside7 == ["DSM-U9-99"])
    ok("영역 7 을 찾았다는 사실도 낸다", found is True)

    _no7 = {"areas": [{"id": "2", "clauses": [{"id": "DSM-U1-01"}]}]}
    _in7, _out7, _found = promoted_area7_ids(_no7)
    ok("★ 영역 7 이 대장에 아예 없으면 found=False(0건과 다르다 — D-301)",
       _found is False and _in7 == [])

    fails = [n for n, g in cases if not g]
    for name, good in cases:
        print("  %-4s %s" % ("OK" if good else "FAIL", name))
    if fails:
        print("%s 자기시험 **실패** %d건 — 판정기를 먼저 의심한다 (D-350)" % (TAG, len(fails)))
        return EXIT_RED
    print("%s 자기시험 %d건 통과 — 빈 칸 표본 1 · 표 없음(옛 승격) 표본 1 · 깨끗한 표본 1 · "
         "열린 부분 표본 1 · 대장 구조(중복 제거·영역 밖 접두·영역 7 없음) 표본 3"
         % (TAG, len(cases)))
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="영역 7 승격 절의 「제목 ↔ 있는 것」 표 빈 칸 게이트")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true", help="절마다 한 줄씩 다 보인다(기본은 빨강만)")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    rep = measure()
    return report(rep, list_all=args.list)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107

    _rep = None
    _n = "?"
    try:
        _rep = measure()
        _n = str(_rep.get("promoted_n", "?")) if _rep.get("ok") else "?"
    except Exception:                                              # noqa: BLE001
        pass

    gate_header(
        __file__,
        target="`%s` + `%s/*.json`" % (
            str(LEDGER.relative_to(ROOT)).replace("\\", "/"),
            str(EVIDENCE_DIR.relative_to(ROOT)).replace("\\", "/")),
        as_="(자격증명 없음 — 대장 YAML 과 증거 JSON 파일만 읽는다)",
        source="저장소 작업본의 대장 · SPEC 증거 디렉터리(지금 읽는다 · docker·HTTP 없음)",
        measured=("영역 7(annex 승격) 의 DSM-/FWS-/O- 접두 절마다 증거의 "
                  "`title_parts` 표를 재어 빈 칸·열린 행을 센다 — **분모 %s건**" % _n),
    )
    sys.exit(main())
