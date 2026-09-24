#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-96 — 8영역 · FC · PR · CR 네 수를 **한 번에** 내는 산출기.

왜 이 도구가 생겼나
-------------------
    8영역만 `verify_ga_readiness.py` 가 냈다. **FC(기능 완결성) · PR(상용 준비) ·
    CR(상용 준비도)** 은 산출기가 없어 **사람이 눈대중으로 추정**했고, 그래서
    보고마다 값이 흔들렸다 — 턴 H 84·85 → 턴 I 82·83 → 세종 지시서 CR 38%.

★ 출생 표본 (D-310) — BIRTH_SAMPLE
----------------------------------
이 도구를 만들게 한 문장 둘이다. 자기시험이 이 둘을 **직접** 시험한다:

  ① `GX-CR_상용준비도_셈법_v0.1.md` §5-3:
     「**38 은 이 셈법이 낼 수 있는 수가 아니다**」 —
     ①이 0.6이고 나머지 여덟이 {0,0.5,1} 이면 가능한 합은 `0.6 + 0.5k` 뿐이다.
     격자 밖의 수는 **눈대중이 한 번 더 나온 것**이다.
  ② `RESUME_NEXT.md` P-96:
     「FC 82 · PR 83 은 **[추정]**. 스크립트가 잴 때까지 척도로 쓰지 않는다」 —
     셈법이 없는 수를 실측처럼 내는 것이 이 도구가 막아야 할 바로 그 일이다.

  → 그래서 이 도구는 턴 K 까지 **FC·PR 에 수를 내지 않았다** — 「셈법 미정 · 세종 판정
    필요」로 **회색(exit 2)**. **회색으로 내는 것이 추정치를 실측처럼 내는 것보다 낫다**
    (D-301 · 규칙 ①). 그 회색이 셈법을 불러왔다.

★ 턴 L (2026-09-07 · P-103) — **셈법이 왔다. 그래서 이제는 센다**
------------------------------------------------------------------
    `docs/design/GX-FCPR_기능완결성_상용준비_셈법_v0.1.md` (세종 · 턴 L)
      · **FC = PRD v2.6 §3 페인포인트 18 × {0, 0.5, 1} ÷ 18** — 하한·상한 · 손 밖은 0/1
      · **PR = 관문 G1~G5 × 3항목 = 15칸 × {0, 0.5, 1} ÷ 15**

    이 도구는 CR 과 **똑같은 방식으로** 그 문서를 읽는다 — 값을 코드에 베끼지 않는다:
      · 행 수가 18·15 가 아니면 빨강        · 값이 격자 밖이면 빨강
      · 근거 경로 없는 행에 1이면 빨강(규칙 ③)  · 문서가 적은 수 ≠ 다시 센 수면 빨강
      · **표기가 「판정」인 행**(= 세종 값이 남은 행)은 **회색** — 하한 0 · 상한 1 (§4)
      · PRD §3 의 **표와 요약이 갈리면 빨강** — 세종 합 9.5 가 어느 쪽으로 센 수인지
        모른 채 낸 수는 실측이 아니다

    ★ 출생 표본 ② 는 죽지 않았다. 뜻이 좁아졌다: **셈법 문서가 사라지면 이 도구는 다시
      회색을 낸다.** 자기시험 첫 갈래가 지금도 그것을 시험한다.
    ⚠ **FC 82 · PR 83 은 폐기**다(셈법 §0 약속하지 않는 것 1). 이 셈법으로 낸 첫 수가
      그보다 낮아도 후퇴가 아니라 **반납**이다.

셈법의 자리 — 코드가 아니라 문서다
----------------------------------
CR 의 셈법은 `docs/design/GX-CR_상용준비도_셈법_v0.1.md` §2~3 에 **이미 있다.**
이 스크립트는 그 문서를 **읽어서** 계산한다 — 값을 코드에 베끼지 않는다.
베끼는 순간 문서와 코드가 갈리고, 갈린 것을 아무도 모른다(P-93 의 그 병).

    **문서와 코드가 갈리면 exit 1.** 갈리는 자리는 셋이다:
      · 문서 ① 항목값 ≠ `verify_ga_readiness` 영역 ⑧ 비율   (셈법 규칙 2)
      · 문서가 적어 둔 하한·상한 ≠ 이 도구가 표에서 다시 센 하한·상한
      · 항목이 아홉이 아니다 / 값이 {0, 0.5, 1} 밖이다        (셈법 §2)

    python scripts/verify_readiness_scores.py             # 넷을 한 번에
    python scripts/verify_readiness_scores.py --table     # 대표 보고용 표
    python scripts/verify_readiness_scores.py --self-test

    exit 0 초록 · exit 1 빨강(문서와 코드가 갈렸다) · exit 2 **회색**(못 쟀다)

호스트에서 돈다 — Django 가 필요 없다. `verify_ga_readiness.py` 를 **부른다**(읽어서
답하지 않는다 · D-210).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CR_DOC = ROOT / "docs" / "design" / "GX-CR_상용준비도_셈법_v0.1.md"
FCPR_DOC = ROOT / "docs" / "design" / "GX-FCPR_기능완결성_상용준비_셈법_v0.1.md"
PRD_DOC = (ROOT / "docs" / "design"
           / "PRD_v2.6_사용자여정_화면실사_제품언어_20260925.md")
GA_SCRIPT = ROOT / "scripts" / "verify_ga_readiness.py"

#: FC·PR 의 분모. **셈법 문서가 못박은 수다** — 여기가 흔들리면 아래 수는 전부 무의미하다.
FC_ROWS, PR_ROWS = 18, 15

#: PRD v2.6 §3 판정 열 → 값. 세종 [판정] 쪽의 수이고, 실측이 덮는다.
VERDICT_VALUE = {"해결": 1.0, "반": 0.5, "못 함": 0.0}

#: 실측 표의 「표기」 칸. **판정** 이 남아 있으면 그 행은 회색이다(§4).
TAG_MEASURED, TAG_CPO, TAG_OUT_OF_HAND = "실측", "판정", "손 밖"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

TAG = "[SCORES]"

#: 셈법 §2 — 항목 아홉. 값은 {0, 0.5, 1}. ①만 예외다(영역 ⑧ 비율을 그대로 쓴다).
CIRCLED = "①②③④⑤⑥⑦⑧⑨"
ALLOWED = (0.0, 0.5, 1.0)
UNMEASURED = "못 쟀다"


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 순수 함수로 둔다
# ═══════════════════════════════════════════════════════════════════════════

def parse_cr_tables(text: str) -> list[list[tuple[str, str]]]:
    """마크다운에서 **①~⑨ 아홉 행을 가진 표**만 골라 [(기호, 값칸)] 로 돌려준다.

    같은 문서에 표가 여럿이다(§3 턴 G · §4 비교 · §5-1 턴 H). 아홉을 다 갖춘 표만
    센다 — §4 는 「⑤~⑦」을 한 행에 묶었으므로 아홉이 아니고, 그래서 걸러진다.
    **부르는 쪽이 마지막 표를 쓴다** — 가장 나중에 잰 절이 지금 값이다.
    """
    tables: list[list[tuple[str, str]]] = []
    cur: list[tuple[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if cur:
                tables.append(cur)
                cur = []
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        head = cells[0].replace("*", "").strip()
        if len(head) == 1 and head in CIRCLED:
            cur.append((head, _pick_value_cell(cells[1:])))
    if cur:
        tables.append(cur)

    good = []
    for t in tables:
        syms = [k for k, _ in t]
        if len(t) == 9 and syms == list(CIRCLED):
            good.append(t)
    return good


def _pick_value_cell(cells: list[str]) -> str:
    """오른쪽부터 훑어 **값처럼 생긴 칸**을 고른다.

    근거·비고 칸에는 「6/10」 같은 수가 섞여 있다. 그래서 **칸 전체**가 수(또는
    「못 쟀다」)일 때만 값으로 본다 — 문장 속의 수를 값으로 줍지 않는다.
    """
    for cell in reversed(cells):
        v = cell.replace("*", "").replace("`", "").strip()
        if v == UNMEASURED:
            return UNMEASURED
        if re.fullmatch(r"\d+(?:\.\d+)?", v):
            return v
    return ""


def judge_cr_table(rows: list[tuple[str, str]], *, area8_ratio: float | None) -> tuple[dict, list[str]]:
    """표 아홉 행을 셈법 §2 로 판정하고 하한·상한을 낸다. 어긋난 것들도 함께 돌려준다."""
    bad: list[str] = []
    values: dict[str, float | None] = {}

    if len(rows) != 9:
        bad.append("항목이 아홉이 아니다 (%d개) — 셈법 §2 의 분모가 흔들리면 아래 수는 무의미하다" % len(rows))

    for sym, raw in rows:
        if raw == UNMEASURED:
            values[sym] = None
            continue
        if raw == "":
            bad.append("%s: 값 칸을 못 읽었다 — 표의 모양이 바뀌었다면 이 도구도 함께 고쳐라" % sym)
            values[sym] = None
            continue
        v = float(raw)
        values[sym] = v
        if sym == "①":
            # 셈법 규칙 2 — ①은 영역 ⑧ 비율을 그대로 쓴다. {0,0.5,1} 격자 밖이어도 된다.
            if not (0.0 <= v <= 1.0):
                bad.append("①: 값 %s 가 0~1 밖이다" % raw)
        elif v not in ALLOWED:
            bad.append("%s: 값 %s 가 {0, 0.5, 1} 밖이다 — 셈법 §2 가 셋으로 못박았다" % (sym, raw))

    # ★ 셈법 규칙 2 — ①은 게이트가 낸 영역 ⑧ 비율이어야 한다.
    #   여기가 「문서와 코드가 갈리는」 첫 자리다.
    if area8_ratio is not None and values.get("①") is not None:
        if abs(values["①"] - area8_ratio) > 0.005:
            bad.append("①: 문서 %.2f ≠ `verify_ga_readiness` 영역 ⑧ 비율 %.2f — "
                       "**문서와 코드가 갈렸다.** 셈법 규칙 2 는 같은 사실을 두 곳에 "
                       "적지 말라고 했다 (D-227). 문서를 고쳐라" % (values["①"], area8_ratio))

    known = sum(v for v in values.values() if v is not None)
    unmeasured = sum(1 for v in values.values() if v is None)
    lo = known / 9.0 * 100.0
    hi = (known + unmeasured) / 9.0 * 100.0
    return {"values": values, "known": known, "unmeasured": unmeasured,
            "lower": lo, "upper": hi}, bad


def parse_doc_stated(text: str) -> tuple[float | None, float | None]:
    """문서가 **적어 둔** 하한·상한을 마지막 것으로 집는다 (다시 센 수와 대조하려고)."""
    lo = hi = None
    for m in re.finditer(r"CR\s*하한\s*=\s*[^=\n]*=\s*([\d.]+)\s*%", text):
        lo = float(m.group(1))
    for m in re.finditer(r"CR\s*상한\s*=\s*[^=\n]*=\s*([\d.]+)\s*%", text):
        hi = float(m.group(1))
    return lo, hi


def on_grid(total: float, area1: float) -> bool:
    """★ 출생 표본 ① — 합이 `area1 + 0.5k` 격자 위에 있는가.

    §5-3 이 38% 를 두고 한 산수다. 격자 밖의 수는 이 셈법의 산물이 아니다 —
    **눈대중**이다. 눈대중을 실측 칸에 적지 않기 위한 검사다.
    """
    k = (total - area1) / 0.5
    return abs(k - round(k)) < 1e-6


def parse_ga_areas(out: str) -> tuple[list[dict], float | None, float | None]:
    """`verify_ga_readiness.py` 의 표준출력에서 8영역·가중합계·손 안 도달율을 읽는다."""
    areas = []
    rx = re.compile(r"^\s*(\d)\s+(.+?)\s+가중\s*(\d+)%\s+절\s*(\d+)/(\d+)\s*=\s*(\d+)%")
    for line in out.splitlines():
        m = rx.match(line)
        if m:
            areas.append({"no": int(m.group(1)), "name": m.group(2).strip(),
                          "weight": int(m.group(3)), "done": int(m.group(4)),
                          "total": int(m.group(5)), "pct": int(m.group(6))})
    total = None
    m = re.search(r"상용 오픈 가중 합계 \*\*([\d.]+)%\*\*", out)
    if m:
        total = float(m.group(1))
    inhand = None
    m = re.search(r"손 안 도달율 ([\d.]+)%", out)
    if m:
        inhand = float(m.group(1))
    return areas, total, inhand


# ═══════════════════════════════════════════════════════════════════════════
# FC · PR — 셈법 문서(§1·§2·§3′)를 **읽어서** 센다. CR 과 같은 방식이다.
#   ★ 값을 코드에 베끼지 않는다. 베끼는 순간 문서와 코드가 갈리고,
#     갈린 것을 아무도 모른다(P-93 의 그 병).
# ═══════════════════════════════════════════════════════════════════════════

def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _plain(cell: str) -> str:
    return cell.replace("*", "").replace("`", "").strip()


def _int_or_none(cell: str):
    v = _plain(cell)
    return int(v) if re.fullmatch(r"\d+", v) else None


def parse_numbered_grid(text: str, n: int, col: int = 0) -> list[list[dict]]:
    """첫(또는 `col` 번째) 칸이 **정확히 1..n** 인 표만 골라 돌려준다.

    CR 파서가 ①~⑨ 아홉 기호로 표를 고른 것과 같은 방식이다 — **분모가 맞는 표만**
    센다. 18 이 아닌 표, 15 가 아닌 표는 이 셈법의 표가 아니다.
    """
    blocks: list[list[dict]] = []
    cur: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if cur:
                blocks.append(cur)
                cur = []
            continue
        cells = _cells(s)
        if len(cells) <= col:
            continue
        no = _int_or_none(cells[col])
        if no is None:
            continue
        cur.append({"no": no, "cells": cells})
    if cur:
        blocks.append(cur)
    want = list(range(1, n + 1))
    return [b for b in blocks if [r["no"] for r in b] == want]


def read_measured_grid(text: str, n: int) -> list[dict] | None:
    """§3′ 실측 표 한 벌 → [{no, value, evidence, tag, why}]. 없으면 `None`.

    칸 순서는 문서의 표 그대로다: `| # | · | · | 값 | 근거 경로 | 표기 | 사유 |`.
    표의 모양이 바뀌면 **이 함수도 함께 고쳐라** — 못 읽은 채 넘어가면 눈이 먼다.
    """
    blocks = parse_numbered_grid(text, n, col=0)
    blocks = [b for b in blocks if all(len(r["cells"]) >= 6 for r in b)]
    if not blocks:
        return None
    rows = []
    for r in blocks[-1]:                      # 가장 나중에 잰 표가 지금 값이다
        c = r["cells"]
        raw = _plain(c[3])
        rows.append({
            "no": r["no"],
            "raw": raw,
            "value": None if raw == UNMEASURED else (
                float(raw) if re.fullmatch(r"\d+(?:\.\d+)?", raw) else None),
            "unreadable": raw != UNMEASURED and not re.fullmatch(r"\d+(?:\.\d+)?", raw),
            "evidence": _plain(c[4]),
            "tag": _plain(c[5]),
            "why": _plain(c[6]) if len(c) > 6 else "",
            #: 판정에는 안 쓴다. **관문 이름(G1~G5)** 을 표에서 읽으려고 남긴다 —
            #: 「세 칸씩 끊으면 G1」 같은 가정을 코드에 넣지 않으려고(P-117).
            "cells": c,
        })
    return rows


def parse_prd_painpoints(text: str) -> tuple[list[dict], dict, dict]:
    """PRD v2.6 §3 — 페인포인트 표의 **판정 열**과 그 아래 **요약 문장**을 따로 읽는다.

    ★ 이 둘이 갈릴 수 있다. 갈리면 세종의 합(9.5)이 어느 쪽으로 센 수인지 모르게 된다.
      그래서 **둘 다** 읽고 대조한다.
    """
    rows: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        c = _cells(s)
        if len(c) < 4:
            continue
        user = _plain(c[0])
        if not re.fullmatch(r"U[1-6]|전원", user):
            continue
        m = re.match(r"(해결|반|못 함)", _plain(c[3]))
        if not m:
            continue
        rows.append({"no": len(rows) + 1, "user": user, "pain": _plain(c[1]),
                     "verdict": m.group(1), "value": VERDICT_VALUE[m.group(1)]})
    table = {k: sum(1 for r in rows if r["verdict"] == k) for k in VERDICT_VALUE}
    stated: dict = {}
    m = re.search(r"\*\*(\d+)\s*해결\s*·\s*(\d+)\s*반\s*·\s*(\d+)\s*못 함", text)
    if m:
        stated = {"해결": int(m.group(1)), "반": int(m.group(2)), "못 함": int(m.group(3))}
    return rows, table, stated


def slice_section(text: str, start: str, end: str) -> str:
    """`## 3.` 부터 `## 3′.` 앞까지처럼 **한 절만** 잘라 낸다.

    ★ 왜 자르는가: 자르지 않고 문서 전체에서 「수 옆의 수」를 주우면 **§2 셈법 표의
      머리줄**(`| 관문 | # | 항목 | 1 | 0.5 | 0 | 근거 출처 |`)이 「항목 1 의 값은 0.5」
      로 읽힌다 [실측 2026-09-07 · 이 파서가 실제로 그렇게 읽었다]. 격자의 눈금을
      값으로 줍는 것 — 그것이 눈먼 파서다(P-93).
    """
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return text[i:j if j > 0 else len(text)]


def parse_cpo_pr_values(text: str) -> dict[int, float]:
    """§3 세종 [판정] PR 표 — 한 줄에 두 항목씩 들어 있는 표에서 (번호, 값) 을 줍는다.

    부르는 쪽이 **§3 만** 넘긴다(`slice_section`). 문서 전체를 넘기면 위 함수의
    설명대로 머리줄을 값으로 줍는다.
    """
    out: dict[int, float] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        c = _cells(s)
        for i in range(len(c) - 1):
            no = _int_or_none(c[i])
            val = _plain(c[i + 1])
            if no is not None and 1 <= no <= PR_ROWS and re.fullmatch(r"\d+(?:\.\d+)?", val):
                out.setdefault(no, float(val))
    return out


def judge_measured_grid(rows: list[dict], n: int, label: str) -> tuple[dict, list[str], list[str]]:
    """실측 표를 §1·§2 의 규칙으로 판정한다 → (셈, 빨강, 회색).

    규칙 ② 값은 격자 밖으로 안 나간다 · 규칙 ③ **근거 경로 없는 행에 1을 주지 않는다** ·
    규칙 넷 손 밖은 하한 0 · 상한 1 · §4 세종 값이 남은 행은 **회색**(하한 0 · 상한 1).
    """
    red: list[str] = []
    gray: list[str] = []
    if len(rows) != n:
        red.append("%s: 행이 %d 이 아니다 (%d행) — 분모가 흔들리면 아래 수는 무의미하다"
                   % (label, n, len(rows)))

    lower = upper = 0.0
    unmeasured = 0
    out_of_hand = 0
    for r in rows:
        v, tag, ev = r["value"], r["tag"], r["evidence"]
        if r["unreadable"]:
            red.append("%s %d: 값 칸을 못 읽었다(%r) — 표의 모양이 바뀌었다면 "
                       "**이 도구도 함께 고쳐라**" % (label, r["no"], r["raw"]))
        elif v is not None and v not in ALLOWED:
            red.append("%s %d: 값 %g 가 {0, 0.5, 1} 밖이다 — 셈법이 셋으로 못박았다"
                       % (label, r["no"], v))
        if not ev:
            red.append("%s %d: **근거 경로가 없다** — 규칙 ③(근거 경로 없는 행에 1을 주지 "
                       "않는다)은 경로 칸이 비면 판정 자체를 못 한다" % (label, r["no"]))
        elif v is not None and v > 0:
            path = ROOT / ev.split("#", 1)[0].strip()
            if not path.exists():
                red.append("%s %d: 값 %g 인데 근거 경로 `%s` 가 저장소에 없다 — 규칙 ③"
                           % (label, r["no"], v, ev))

        if tag == TAG_CPO or v is None:
            #: §4 — 세종 값이 남은 행 · 못 잰 행은 **회색**. 0 으로도 1 로도 세지 않는다.
            unmeasured += 1
            upper += 1.0
            gray.append("%s %d: %s — 하한 0 · 상한 1"
                        % (label, r["no"],
                           "세종 판정 · 미실측" if tag == TAG_CPO else UNMEASURED))
        elif tag == TAG_OUT_OF_HAND:
            #: 규칙 넷 — 손 밖은 하한에서 그대로, 상한에서 1.
            out_of_hand += 1
            lower += v
            upper += 1.0
        else:
            lower += v
            upper += v

    return ({"lower_sum": lower, "upper_sum": upper, "n": n,
             "lower": lower / n * 100.0, "upper": upper / n * 100.0,
             "unmeasured": unmeasured, "out_of_hand": out_of_hand,
             "rows": rows}, red, gray)


def disagreeing_rows(measured: list[dict], cpo: dict[int, float]) -> list[str]:
    """실측 ≠ 세종 판정인 행. **매 턴 보고에 이 수가 들어간다**(§4)."""
    out = []
    for r in measured:
        want = cpo.get(r["no"])
        if want is None or r["value"] is None:
            continue
        if abs(r["value"] - want) > 1e-9:
            out.append("%d: 세종 %g → 실측 %g%s"
                       % (r["no"], want, r["value"],
                          " (%s)" % r["why"][:60] if r["why"] else ""))
    return out


def parse_fcpr_stated(text: str) -> dict:
    """문서가 **적어 둔** 수를 집는다 — 다시 센 수와 대조하려고(CR 과 같은 자리)."""
    out: dict = {}
    for key, pat in (("fc_lower", r"FC 하한 = [^=\n]*=\s*([\d.]+)\s*%"),
                     ("fc_upper", r"FC 상한 = [^=\n]*=\s*([\d.]+)\s*%"),
                     ("pr", r"\*\*PR = [^=\n]*=\s*([\d.]+)\s*%")):
        found = re.findall(pat, text)
        if found:
            out[key] = float(found[-1])
    return out


# ═══════════════════════════════════════════════════════════════════════════
# P-149 — **PR 15관문 · CR 8조건 산출기** (턴 R · 차선 Q)
#
# 왜 이 절이 생겼나
# -----------------
#   첫 표의 「PR · CR」 칸이 **회색 — 산출기 없음**으로 여러 턴 서 있었다. 그런데
#   정본은 이미 둘 다 있었다: PR 15관문은 `GX-FCPR §2`, CR 8조건은
#   `GX-REVIEW §1` 이다. 없던 것은 셈법이 아니라 **그 표를 읽는 코드**였고,
#   그래서 그 수는 매번 사람이 **인용**했다(09-08 손 점검 20.0 · 12.5).
#   인용한 수는 정본이 바뀌어도 안 바뀐다 — 그것이 이 도구가 막는 병이다(P-93).
#
# ★ 이 산출기가 **하지 않는** 것
#   · 값을 코드에 베끼지 않는다 — 표를 읽는다.
#   · 읽을 수 없는 칸을 0 으로도 1 로도 세지 않는다 — **회색**이고, 하한·상한이 갈린다.
#   · 「끝나는가」 술어의 PR 15칸을 **행별로** 내지 않는다. 그 술어의 per-row 정본이
#     저장소에 없기 때문이다(§12 는 합계 한 줄뿐). 없는 표를 지어내지 않는다.
# ═══════════════════════════════════════════════════════════════════════════

#: CR 8조건(§1)의 「지금 [실측]」 칸 → 값. 「반」만 0.5 이고 나머지는 끝났거나 아니다.
CR8_VALUE = {"없다": 0.0, "아니다": 0.0, "반": 0.5,
             "끝난다": 1.0, "그렇다": 1.0, "해결": 1.0}
CR8_ROWS = 8


def parse_pr_rubric(text: str) -> list[dict]:
    """`GX-FCPR §2` — PR **관문 15항목의 이름표**를 읽는다 (값이 아니라 눈금이다).

    표의 꼴: `| 관문 | # | 항목 | 1 | 0.5 | 0 | 근거 출처 |` — 번호가 **둘째 칸**이라
    `col=1` 로 고른다. 그래서 §3′-2(번호가 첫 칸)와 §3(세종 값 표)은 안 걸린다.
    관문 이름은 세 줄에 한 번만 적혀 있으므로 **이어받는다**.
    """
    blocks = parse_numbered_grid(text, PR_ROWS, col=1)
    if not blocks:
        return []
    out, gate = [], ""
    for r in blocks[-1]:
        c = r["cells"]
        g = _plain(c[0]) if c else ""
        m = re.match(r"(G[1-5])", g)
        if m:
            gate = m.group(1)
        out.append({"no": r["no"], "gate": gate,
                    "item": _plain(c[2]) if len(c) > 2 else "",
                    "source": _plain(c[6]) if len(c) > 6 else ""})
    return out


def parse_cr8(text: str) -> list[dict]:
    """`GX-REVIEW §1` — **돈을 내는 8조건**과 그 「지금 [실측]」 칸을 읽는다.

    표의 꼴: `| ① | 조건 | 술어 | **반** — … |`. 값 칸은 문장이라 **맨 앞 낱말**만
    본다 — 뒤의 사유는 사람이 읽을 것이고, 값은 그 첫 낱말이 정한다.
    아는 낱말이 아니면 `None`(**회색**)이다. 모르는 것을 0 으로 세지 않는다.
    """
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        c = _cells(s)
        if len(c) < 4:
            continue
        sym = _plain(c[0])
        if len(sym) != 1 or sym not in CIRCLED[:CR8_ROWS]:
            continue
        raw = _plain(c[3])
        m = re.match(r"(없다|아니다|반|끝난다|그렇다|해결)", raw)
        rows.append({"no": CIRCLED.index(sym) + 1, "cond": _plain(c[1]),
                     "raw": raw, "value": CR8_VALUE[m.group(1)] if m else None})
    return rows


def judge_cr8(rows: list[dict]) -> tuple[dict, list[str]]:
    """8조건 → 하한·상한. **회색은 0 으로도 1 로도 세지 않는다**(CR 9항목과 같은 규칙)."""
    bad = []
    if len(rows) != CR8_ROWS:
        bad.append("CR8: 조건이 여덟이 아니다 (%d개) — 분모가 흔들리면 아래 수는 무의미하다"
                   % len(rows))
    known = sum(r["value"] for r in rows if r["value"] is not None)
    unmeasured = sum(1 for r in rows if r["value"] is None)
    n = len(rows) or CR8_ROWS
    for r in rows:
        if r["value"] is None:
            bad.append("CR8 %d(%s): 「지금」 칸 %r 을 못 읽었다 — 표의 모양이 바뀌었다면 "
                       "**이 도구도 함께 고쳐라**" % (r["no"], r["cond"][:18], r["raw"][:24]))
    return {"known": known, "unmeasured": unmeasured, "n": n,
            "lower": known / n * 100.0, "upper": (known + unmeasured) / n * 100.0,
            "rows": rows}, bad


def cross_check_pr(rubric: list[dict], measured: list[dict]) -> list[str]:
    """§2 의 눈금(15항목)과 §3′-2 의 값(15행)이 **같은 표를 말하는가**.

    분모가 같아도 항목이 어긋나면 두 표는 다른 것을 재고 있는 것이다 —
    그때 낸 수는 둘 중 어느 쪽의 수도 아니다.
    """
    bad = []
    if not rubric:
        return ["PR: `GX-FCPR §2` 에서 **관문 15항목 표**를 못 찾았다 — 눈금 없이 낸 값은 "
                "무엇을 잰 수인지 말할 수 없다"]
    if len(rubric) != PR_ROWS:
        bad.append("PR: §2 의 항목이 %d개다 — 셈법이 못박은 분모는 %d다"
                   % (len(rubric), PR_ROWS))
    by_no = {r["no"]: r for r in measured}
    for item in rubric:
        m = by_no.get(item["no"])
        if not m:
            bad.append("PR %d: §2 에 있는 항목이 §3′-2 실측 표에 **없다**" % item["no"])
            continue
        cells = m.get("cells") or []
        got_gate = _plain(cells[1]) if len(cells) > 1 else ""
        if item["gate"] and got_gate and item["gate"] != got_gate:
            bad.append("PR %d: 관문이 갈린다 — §2 는 %s · §3′-2 는 %s"
                       % (item["no"], item["gate"], got_gate))
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 출생 표본을 첫 갈래로 둔다 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test(verbose: bool = True) -> int:
    cases: list[tuple[str, bool]] = []

    def ok(name, cond):
        cases.append((name, bool(cond)))

    # ── ★ 출생 표본 ① — 격자 밖의 수(38%)는 이 셈법의 산물이 아니다 (§5-3) ──
    #    합 3.1 → 34.4% 는 격자 위 · 합 3.42 → 38% 는 격자 밖.
    ok("★ 출생 표본 · 38% 는 격자 밖이다", not on_grid(3.42, 0.6))
    ok("★ 출생 표본 · 34.4%(합 3.1) 는 격자 위다", on_grid(3.1, 0.6))
    ok("★ 출생 표본 · 45.6%(합 4.1) 는 격자 위다", on_grid(4.1, 0.6))

    # ── ★ 출생 표본 ② — **셈법이 없으면 수를 내지 않는다** ────────────────────
    #    턴 L 에 셈법이 생겼다(GX-FCPR v0.1). 그래도 이 갈래는 그대로 남는다 —
    #    82·83 이 나쁜 수였던 이유는 「셈법 없이 나온 수」였기 때문이고, 문서가
    #    사라지면 이 도구는 **다시 회색**이어야 한다. 이것이 그 보증이다.
    fc0 = fc_pr_report("", "")
    ok("★ 출생 표본 · 셈법 문서가 없으면 FC·PR 은 회색이다",
       fc0["color"] == "회색" and fc0["fc"] is None and fc0["pr"] is None)
    ok("★ 출생 표본 · 회색에 사유 이름이 붙는다", "셈법 미정" in fc0["why"])
    ok("★ 출생 표본 · 셈법이 있어도 표가 없으면 빨강이다",
       fc_pr_report("셈법은 있는데 표가 없다", "")["red"])

    # ── 표 파싱 ─────────────────────────────────────────────────────────────
    sample = """
| # | 항목 | 턴 G | **턴 H** | 근거 |
|---|---|---|---|---|
| ① | 법·인증(영역 ⑧ 비율) | 0.6 | **0.6** | 영역 ⑧ **6/10** |
| ② | 가격표 | 0.5 | **0.5** | 숫자 4칸 [확인] |
| ③ | 계량 | 1 | **1** | test_be_metering.py |
| ④ | SLA | 0.5 | **0.5** | v0.2 |
| ⑤ | 청구 수단 | 0 | **0** | 서식 0건 |
| ⑥ | 파일럿 레퍼런스 | 0 | **0** | 0건 |
| ⑦ | 인증(GS·KISA) | 0 | **0** | 신청 0 |
| ⑧ | 채널 계약 | 못 쟀다 | **못 쟀다** | 계약서 없다 |
| ⑨ | 지원 체계 | 0.5 | **0.5** | 장애대응_1쪽.md |
"""
    tabs = parse_cr_tables(sample)
    ok("아홉 행 표를 집는다", len(tabs) == 1 and len(tabs[0]) == 9)
    res, bad = judge_cr_table(tabs[0], area8_ratio=0.6)
    ok("확인된 합 3.1", abs(res["known"] - 3.1) < 1e-9)
    ok("하한 34.4%", abs(res["lower"] - 34.444) < 0.01)
    ok("상한 45.6%", abs(res["upper"] - 45.555) < 0.01)
    ok("어긋남 0", not bad)

    # ── 「못 쟀다」는 0 으로도 1 로도 안 센다 → 하한 ≠ 상한 ────────────────────
    ok("못 쟀다 1건이면 하한과 상한이 갈린다", res["upper"] - res["lower"] > 1.0)

    # ── 음성 ① — 값이 격자 밖이면 잡는다 ────────────────────────────────────
    bad_tab = [(s, v) for s, v in tabs[0]]
    bad_tab[1] = ("②", "0.7")
    _, bad2 = judge_cr_table(bad_tab, area8_ratio=0.6)
    ok("음성 · 0.7 은 {0,0.5,1} 밖이라 잡힌다", any("밖이다" in b for b in bad2))

    # ── 음성 ② — 문서 ① 과 게이트 영역 ⑧ 이 갈리면 잡는다 (핵심 갈래) ────────
    _, bad3 = judge_cr_table(tabs[0], area8_ratio=0.8)
    ok("음성 · 문서 ①(0.6) ≠ 영역 ⑧(0.8) 을 잡는다", any("갈렸다" in b for b in bad3))

    # ── 음성 ③ — 아홉이 아니면 잡는다 (분모가 흔들리면 다 무의미) ─────────────
    _, bad4 = judge_cr_table(tabs[0][:8], area8_ratio=0.6)
    ok("음성 · 여덟 행이면 잡는다", any("아홉이 아니다" in b for b in bad4))

    # ── 음성 ④ — 근거 칸의 「6/10」 을 값으로 줍지 않는다 ─────────────────────
    ok("음성 · 문장 속 수를 값으로 안 줍는다", _pick_value_cell(["법·인증", "영역 ⑧ **6/10** — 이번 턴 그대로"]) == "")

    # ── 문서가 적어 둔 하한·상한을 집는다 ────────────────────────────────────
    lo, hi = parse_doc_stated("**CR 하한 = 3.1 ÷ 9 = 34.4%**\n**CR 상한 = 4.1 ÷ 9 = 45.6%**")
    ok("문서가 적어 둔 하한·상한을 집는다", lo == 34.4 and hi == 45.6)

    # ── ga_readiness 출력 파싱 ──────────────────────────────────────────────
    ga = ("  1  기능 완결성                 가중 20%  절 32/39 =  82%  →  16.41\n"
          "  8  법·인증 (개인정보·GS·SLA)     가중  5%  절  6/10 =  60%  →   3.00\n"
          "[GA] ★ 상용 오픈 가중 합계 **82.0%** [실측]\n"
          "[GA] ★ **손 안 도달율 92.7%** = 구현 114 / (140 − 설계 잠금 1 − 손 밖 16 = 123)\n")
    areas, tot, inh = parse_ga_areas(ga)
    ok("영역 표를 읽는다", len(areas) == 2 and areas[1]["done"] == 6 and areas[1]["total"] == 10)
    ok("가중 합계를 읽는다", tot == 82.0)
    ok("손 안 도달율을 읽는다", inh == 92.7)

    # ── FC·PR 격자 파서 · 판정 ──────────────────────────────────────────────
    def _grid(n, value="1", tag="실측", ev="scripts/verify_readiness_scores.py"):
        L = ["| # | 가 | 나 | 값 | 근거 경로 | 표기 | 사유 |", "|---|---|---|---|---|---|---|"]
        for i in range(1, n + 1):
            L.append("| %d | U1 | 페인 %d | %s | %s | %s | — |" % (i, i, value, ev, tag))
        return "\n".join(L)

    g18 = read_measured_grid(_grid(FC_ROWS, "0.5"), FC_ROWS)
    ok("18행 실측 표를 집는다", g18 is not None and len(g18) == FC_ROWS)
    res, red_, gray_ = judge_measured_grid(g18, FC_ROWS, "FC")
    ok("하한·상한이 9.0/18 = 50.0%", abs(res["lower"] - 50.0) < 0.01 and abs(res["upper"] - 50.0) < 0.01)
    ok("어긋남 0 · 회색 0", not red_ and not gray_)

    # 음성 ⑤ — 열여덟이 아니면 표로 안 집힌다 (분모가 흔들리면 다 무의미)
    ok("음성 · 17행 표는 FC 표로 안 집힌다", read_measured_grid(_grid(17, "0.5"), FC_ROWS) is None)

    # 음성 ⑥ — 격자 밖의 값을 잡는다
    bad_rows = read_measured_grid(_grid(PR_ROWS, "0.5"), PR_ROWS)
    bad_rows[2]["value"] = 0.7
    _, red6, _ = judge_measured_grid(bad_rows, PR_ROWS, "PR")
    ok("음성 · 0.7 은 {0,0.5,1} 밖이라 잡힌다", any("밖이다" in b for b in red6))

    # 음성 ⑦ — ★ **근거 경로 없는 1** 을 잡는다 (규칙 ③)
    noev = read_measured_grid(_grid(PR_ROWS, "1", ev="docs/없는파일.md"), PR_ROWS)
    _, red7, _ = judge_measured_grid(noev, PR_ROWS, "PR")
    ok("★ 음성 · 근거 경로가 저장소에 없는 1 을 잡는다 (규칙 ③)",
       any("저장소에 없다" in b for b in red7))

    # 음성 ⑧ — **세종 값이 남은 행은 회색**이고 하한 0 · 상한 1 로 샌다 (§4)
    cpo = read_measured_grid(_grid(PR_ROWS, "1", tag="판정"), PR_ROWS)
    res8, _, gray8 = judge_measured_grid(cpo, PR_ROWS, "PR")
    ok("★ 세종 값이 남은 행은 회색 · 하한 0 상한 1",
       len(gray8) == PR_ROWS and res8["lower"] == 0.0 and abs(res8["upper_sum"] - PR_ROWS) < 1e-9)

    # 음성 ⑨ — 손 밖은 하한에서 0 · 상한에서 1 (규칙 넷)
    outh = read_measured_grid(_grid(FC_ROWS, "0", tag="손 밖"), FC_ROWS)
    res9, _, _ = judge_measured_grid(outh, FC_ROWS, "FC")
    ok("손 밖은 하한 0% · 상한 100%", res9["lower"] == 0.0 and abs(res9["upper"] - 100.0) < 0.01)

    # PRD §3 — 표의 판정 열과 **그 아래 요약 문장**을 따로 읽고 대조한다
    prd = ("| 사용자 | 페인포인트 | 기능 | 판정 |\n|---|---|---|---|\n"
           "| U1 | 가 | — | **해결** |\n| U1 | 나 | — | **못 함** |\n"
           "| 전원 | 다 | — | 반 |\n\n**1 해결 · 2 반 · 0 못 함.**\n")
    prows, ptable, pstated = parse_prd_painpoints(prd)
    ok("PRD 판정 열을 읽는다 (해결=1 · 반=0.5 · 못 함=0)",
       [r["value"] for r in prows] == [1.0, 0.0, 0.5])
    ok("★ PRD 표(1/1/1) 와 요약(1/2/0) 이 갈린 것을 본다", ptable != pstated)

    # 세종 §3 PR 표 — 한 줄에 두 항목씩 든 표에서 값을 줍는다
    cpo_pr = parse_cpo_pr_values("| 1 | 0 | 공개 URL 0 | | 9 | 1 | 콘솔 0 |")
    ok("세종 PR 값 표를 읽는다(한 줄 두 항목)", cpo_pr == {1: 0.0, 9: 1.0})
    # ★ 음성 — §2 셈법 표의 **머리줄**을 값으로 줍지 않는다 (절을 잘라서 막는다)
    doc = "\n".join([
        "## 2. PR",
        "| 관문 | # | 항목 | 1 | 0.5 | 0 | 근거 |",
        "## 3. 세종 [판정]",
        "| 1 | 0 | 공개 URL 0 | | 9 | 1 | 콘솔 0 |",
        "## 3′. 실측",
    ])
    #: 앞줄은 **위험이 실재함**을 보이고(자르지 않으면 머리줄의 눈금 0.5 를 값으로 줍는다),
    #: 뒷줄은 **자르면 안 줍는다**를 보인다. 둘을 함께 두어야 이 방어가 왜 있는지 남는다.
    ok("★ 음성 · 절을 안 자르면 §2 머리줄(1 | 0.5 | 0)을 값으로 줍는다",
       parse_cpo_pr_values(doc) == {1: 0.5, 9: 1.0})
    ok("★ 절을 자르면 세종 값(1 → 0)만 읽는다",
       parse_cpo_pr_values(slice_section(doc, "## 3. 세종", "## 3′")) == {1: 0.0, 9: 1.0})
    ok("어긋난 행을 센다",
       disagreeing_rows([{"no": 1, "value": 0.5, "why": ""}], {1: 1.0}) != [])

    lo2 = parse_fcpr_stated("**FC 하한 = 7.0 ÷ 18 = 38.9%**  **FC 상한 = 8.0 ÷ 18 = 44.4%**\n"
                            "**PR = 7.0 ÷ 15 = 46.7%**")
    ok("문서가 적어 둔 FC·PR 수를 집는다",
       lo2 == {"fc_lower": 38.9, "fc_upper": 44.4, "pr": 46.7})

    # ── ★ P-149 — PR 15관문 눈금(§2) · CR 8조건(§1) 산출기 ────────────────────
    rub_src = "\n".join(
        ["| 관문 | # | 항목 | 1 | 0.5 | 0 | 근거 출처 |", "|---|---|---|---|---|---|---|"]
        + ["| %s | %d | 항목%d | 가 | 나 | 다 | `verify_x` |"
           % ("**G%d 이름**" % (i // 3 + 1) if i % 3 == 0 else "", i + 1, i + 1)
           for i in range(PR_ROWS)])
    rub = parse_pr_rubric(rub_src)
    ok("★ §2 의 관문 15항목을 읽는다 (번호가 **둘째 칸**인 표)", len(rub) == PR_ROWS)
    ok("★ 관문 이름은 세 줄에 한 번만 적혀도 **이어받는다**",
       [r["gate"] for r in rub][:4] == ["G1", "G1", "G1", "G2"])
    ok("★ 음성 · §3′-2(번호가 첫 칸)는 §2 눈금 표로 안 집힌다",
       parse_pr_rubric(_grid(PR_ROWS, "0.5")) == [])

    cr8_src = "\n".join([
        "| # | 조건 | 술어 | 지금 [실측] |", "|---|---|---|---|",
        "| ① | 바깥에서 URL | 술어 | **없다** — 공개 URL 0 |",
        "| ② | 계정이 안전하다 | 술어 | **반** — 74계정 공유 |",
        "| ③ | 첫 근무일 | 술어 | **아니다** — 확인창 사망 |",
        "| ④ | 보고서 | 술어 | **아니다** — 영문 CRUD |",
        "| ⑤ | 알림 | 술어 | **아니다** — channel=log |",
        "| ⑥ | SLA | 술어 | **아니다** — 운영 서버 0 |",
        "| ⑦ | 가격표 | 술어 | **아니다** — 빈칸 |",
        "| ⑧ | 감사 60초 | 술어 | **반** — 날짜로 찾는 길 없음 |"])
    c8 = parse_cr8(cr8_src)
    ok("★ 8조건의 「지금」 칸을 **맨 앞 낱말**로 읽는다 (뒤 사유는 사람 몫)",
       [r["value"] for r in c8] == [0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5])
    res8, bad8 = judge_cr8(c8)
    ok("★ CR8 = 1.0 ÷ 8 = 12.5% · 회색 0", abs(res8["lower"] - 12.5) < 0.01 and not bad8)
    unk = parse_cr8(cr8_src.replace("**없다** — 공개 URL 0", "**곧 된다** — 다음 턴"))
    res9, bad9 = judge_cr8(unk)
    ok("★ 음성 · 모르는 낱말은 **회색** — 0 으로도 1 로도 안 센다 (하한≠상한)",
       unk[0]["value"] is None and res9["upper"] - res9["lower"] > 1.0 and bad9)
    ok("★ 음성 · 여덟이 아니면 잡는다", any("여덟이 아니다" in b for b in judge_cr8(c8[:7])[1]))

    meas15 = read_measured_grid(_grid(PR_ROWS, "0.5"), PR_ROWS)
    for i, r in enumerate(meas15):
        r["cells"] = [str(r["no"]), "G%d" % (i // 3 + 1), "항목", "0.5", "e", "실측"]
    ok("★ §2 눈금과 §3′-2 값이 **같은 표를 말하면** 어긋남 0", not cross_check_pr(rub, meas15))
    meas15[4]["cells"][1] = "G5"
    ok("★ 음성 · 관문이 갈리면 잡는다 (분모가 같아도 다른 것을 잰 것이다)",
       any("관문이 갈린다" in b for b in cross_check_pr(rub, meas15)))
    ok("★ 음성 · §2 를 못 읽으면 **회색 사유**가 나온다", cross_check_pr([], meas15))

    # ── P-117 · 첫 표 — **두 술어를 섞지 않는다** ──────────────────────────
    #    ★ 출생 표본 ③: 09-08 손 점검이 낸 33.3/20.0/12.5 와 이 도구가 문서에서
    #      다시 센 41.7/50.0/34.4 는 **둘 다 참**이다. 이 갈래들이 지키는 것은
    #      「둘을 한 칸에 넣지 않는다」 하나다.
    ho = parse_handson(
        "| **FC** | 48흐름 ÷ 48 | **33.3%** (16.0/48) | ≥ 70 | … |\n"
        "| **PR** | 15관문 ÷ 15 | **20.0%** (3.0/15) | ≥ 80 | … |\n"
        "| **CR** | 8조건 ÷ 8 | **12.5%** (1.0/8) | ≥ 75 | … |\n")
    ok("★ 「끝나는가」 세 수를 분자·분모까지 읽는다",
       ho.get("FC") == {"pct": 33.3, "sum": 16.0, "n": 48, "rc1": 70.0}
       and ho["PR"]["n"] == 15 and ho["CR"]["n"] == 8)
    ok("★ 음성 · 손 점검 문서가 없으면 그 칸은 비어 있다 (0 으로도 안 센다)",
       parse_handson("") == {})
    ok("RC-1 문턱 줄을 읽는다",
       parse_rc1("**RC-1 문턱**: FC ≥ 70 · PR ≥ 80 · CR ≥ 75 · 상용 /100 ≥ 88.")
       == {"FC": 70.0, "PR": 80.0, "CR": 75.0, "상용 /100": 88.0})

    obt = parse_onboarding("옛 값 27.5 / 48 = 57%\n지금 **29.0 / 48 = 60%**\n")
    ok("온보딩은 **가장 나중에 적힌** N/48 을 쓴다", obt and obt["sum"] == 29.0)
    ok("온보딩 N÷48 을 다시 곱해 검산한다(60.4 → 60 은 어긋남이 아니다)", obt["consistent"])
    ok("★ 음성 · 분자와 백분율이 갈리면 잡는다",
       not parse_onboarding("**29.0 / 48 = 90%**")["consistent"])

    marks = gate_marks([
        {"value": 1.0, "cells": ["1", "G1", "가", "1", "e", "실측"]},
        {"value": 1.0, "cells": ["2", "G1", "나", "1", "e", "실측"]},
        {"value": 1.0, "cells": ["3", "G1", "다", "1", "e", "실측"]},
        {"value": 0.0, "cells": ["4", "G2", "라", "0", "e", "실측"]},
        {"value": 0.5, "cells": ["5", "G2", "마", "0.5", "e", "실측"]},
        {"value": 0.0, "cells": ["6", "G2", "바", "0", "e", "실측"]},
        {"value": 0.0, "cells": ["7", "G3", "사", "0", "e", "실측"]},
    ])
    ok("관문 표식 — 셋 다 1 이면 ●", marks[0][:2] == ("G1", "●"))
    ok("관문 표식 — 섞이면 ◐", marks[1][:2] == ("G2", "◐"))
    ok("★ 관문 표식 — 셋 다 0 이면 ○ (◐ 로 올려 주지 않는다)", marks[2][:2] == ("G3", "○"))
    ok("관문 이름은 **표에서 읽는다** — 3칸씩 끊는다고 가정하지 않는다",
       [m[0] for m in marks] == ["G1", "G2", "G3"] and marks[2][3] == 1)


    # ═══════════════════════════════════════════════════════════════════════
    # ★ P-220 · 턴 AA — 세 수 산출기의 자기시험. **양성과 음성 둘 다.**
    #   턴 Z 에 `verify_classification` 이 **자기시험이 아예 없어서** 칸 이름을
    #   동사로 읽는 오독이 오래 살았다. 새 술어에는 출생 표본을 반드시 붙인다.
    # ═══════════════════════════════════════════════════════════════════════

    # ── ★ P-216 출생 표본 — **각 kind 하나씩 표본 5** ──────────────────────
    #   다섯 부류가 각각 제 눈금을 받는가. 하나라도 어긋나면 그 대장의 수는
    #   「닫힌 절」과 「닫히지 않은 절」을 같은 칸에 세운 수다.
    _t = dict(KIND_SCORE)
    ok("★ P-216 표본 · closed 한 절 = 1.0", kind_points({"closed": 1}, _t)[0] == 1.0)
    ok("★ P-216 표본 · ratchet 한 절 = 1.0 (늘지 않음이 조건)",
       kind_points({"ratchet": 1}, _t)[0] == 1.0)
    ok("★ P-216 표본 · rule_only 한 절 = 0.5 (규칙은 섰으나 현장이 비었다)",
       kind_points({"rule_only": 1}, _t)[0] == 0.5)
    ok("★ P-216 표본 · gate_only 한 절 = 0.5 (제목이 게이트보다 넓다)",
       kind_points({"gate_only": 1}, _t)[0] == 0.5)
    ok("★ P-216 표본 · unmeasurable 한 절 = **0.0** (잠김도 여기 있고 분모에서 안 뺀다)",
       kind_points({"unmeasurable": 1}, _t)[0] == 0.0)

    #: ★★ **눈금은 N 쪽에서 가져온다 — 별명이어도 찾는다** [실측 2026-09-21 · 턴 AA].
    #:   첫 판은 소스를 정규식으로 읽었고 **못 찾았다**: N 이 세운 것은
    #:   `KIND_SCORE = {…}` 가 아니라 별명 `KIND_SCORE = KIND_POINTS` 였다.
    #:   판정문은 「N 쪽에 아직 없다」고 찍었고 **그것은 거짓이었다** — 눈금이 이미
    #:   서 있는데 「없다」고 말하는 게이트는 갈림을 못 본 게이트다.
    _tbl, _why = aa_kind_score_table()
    ok("★★ N 쪽 눈금을 **가져온다**(별명이어도) — 「아직 없다」가 아니다",
       len(_tbl) == 5 and "아직 없다" not in _why)
    ok("★ 가져온 눈금이 다섯 부류를 다 덮는다", set(_tbl) == set(KIND_ORDER))
    ok("★ 그리고 **어디서 가져왔는지 말한다**(조용히 고르지 않는다)",
       ("import" in _why or "소스" in _why or "갈렸다" in _why))

    #: ★ **음성 대조** — 다섯 밖의 부류는 0 으로도 1 로도 세지 않는다.
    _pts, _bad = kind_points({"closed": 1, "초록": 3}, _t)
    ok("★ 음성 · 다섯 밖의 부류가 오면 **잡는다**(조용히 0 으로 세지 않는다)",
       _pts == 1.0 and len(_bad) == 1)

    #: ★ **출생 표본 — 세 턴 동안 「67.x」라 부르던 수** (턴 Z 대장 실측치 그대로).
    #:   status 로 세면 66.5, kind 로 세면 63.3 이다. 이 표본이 그 차이를 잠근다.
    _roll = {"closed": 80, "ratchet": 3, "rule_only": 3,
             "gate_only": 4, "unmeasurable": 64}
    ok("★ 출생 표본 · 대장 154절의 kind 점수는 86.5 다",
       abs(kind_points(_roll, _t)[0] - 86.5) < 1e-9)
    ok("★ 출생 표본 · 닫힌 절은 **80/154** 이고 kind 평평 점수는 56.2% 다",
       sum(_roll.values()) == 154
       and abs(kind_points(_roll, _t)[0] / 154 * 100 - 56.17) < 0.02)
    ok("★ 음성 · 닫힌 절만 세면 51.9% 다 — **56 과 다른 수**이고, 어느 쪽을 "
       "뜻하는지 말하지 않는 「56」은 두 수 사이에 떠 있다",
       abs(_roll["closed"] / 154 * 100 - 51.95) < 0.02)

    # ── ★ 못 잰 칸은 **0 이 아니라 회색** — 이 도구의 한 줄 ────────────────
    _c_ok = [cell("잰 칸", 1.0, 1, 2)]
    _c_grey = [cell("잰 칸", 0.5, 1, 1), cell("못 잰 칸", 0.5)]
    _s = aa_score(_c_grey)
    ok("★ 회색을 0 으로 세면 하한 50 · 1 로 세면 상한 100 — 그 폭이 «모르는 만큼»이다",
       abs(_s["lower"] - 50.0) < 1e-9 and abs(_s["upper"] - 100.0) < 1e-9)
    ok("★ **측정치는 회색을 분모에서 뺀다** — 잰 칸만으로는 100 이다",
       abs(_s["measured_pct"] - 100.0) < 1e-9 and _s["w_measured"] == 0.5)
    ok("★ 음성 · 회색 칸이 **0 점으로 세어지지 않는다**(0 으로 세면 측정치가 50 이 된다)",
       _s["measured_pct"] != 50.0)
    ok("★ 음성 · 칸을 다 못 재면 **측정치가 없다**(0 이 아니다 · 분모 0인 초록은 초록이 아니다)",
       aa_score([cell("a", 1.0), cell("b", 1.0)])["measured_pct"] is None)
    ok("양성 · 잰 칸만 있으면 하한 = 상한 = 측정치",
       aa_score(_c_ok)["lower"] == aa_score(_c_ok)["upper"] == 50.0)
    ok("★ 회색 칸 수를 소리 내어 센다", _s["n_measured"] == 1 and _s["n_cells"] == 2)

    # ── ★ CR 격자 — 「8칸 중 2.2」는 이 셈법이 낼 수 있는 수가 아니다 ───────
    #    이 파일의 출생 표본 ①(38%)이 **그대로 한 번 더 나왔다.**
    ok("★ 출생 표본 ①의 재발 · 합 2.2 는 격자 밖이다", not aa_on_grid(2.2))
    ok("★ 양성 · 합 2.5 는 격자 위다", aa_on_grid(2.5))
    ok("★ 양성 · 합 2.0 · 0.0 · 8.0 도 격자 위다",
       aa_on_grid(2.0) and aa_on_grid(0.0) and aa_on_grid(8.0))
    ok("★ 음성 · 합 2.75 · 2.3 은 격자 밖이다",
       not aa_on_grid(2.75) and not aa_on_grid(2.3))

    # ── ★ CR 8칸 표를 **읽는다**. 없으면 회색이고, 그 회색이 표를 불러온다 ──
    _cr_doc = "\n".join([
        "| # | 칸 | 값 | 근거 |", "|---|---|---|---|",
        "| CR1 | 가격 숫자 4 | 0 | GX-PRICE v0.1 |",
        "| CR2 | 계량 씨앗 0 | 0 | 카메라 8/12 |",
        "| CR3 | 실카메라 ≥1 | 0 | 0/4 |",
        "| CR4 | 공개 주소 | 0 | 일곱 턴째 |",
        "| CR5 | 웹푸시 도달 | 0 | VAPID 소실 |",
        "| CR6 | SLA v1.0 | 0.5 | v0.3 |",
        "| CR7 | 채널 계약서 | 0 | 0건 |",
        "| CR8 | 계약 11조 | 0 | 잠김 |"])
    _rows, _why = parse_aa_cr8(_cr_doc)
    ok("★ 양성 · CR 8칸 표가 있으면 여덟 행을 읽는다", len(_rows) == 8 and not _why)
    ok("★ 양성 · 읽은 값의 합 0.5 는 격자 위다 (6.25%)",
       aa_on_grid(sum(r["value"] for r in _rows)))
    ok("★ 음성 · 표가 **없으면** 회색이고 사유에 「없다」가 있다",
       parse_aa_cr8("합만 적힌 문서 — 8칸 중 2.2")[0] == []
       and "없다" in parse_aa_cr8("8칸 중 2.2")[1])
    ok("★ 음성 · 격자 밖의 값 칸은 **회색**이다 (0 으로 눌러 적지 않는다)",
       parse_aa_cr8("| CR1 | 가격 | 0.3 | e |")[0][0]["value"] is None)
    ok("★ 음성 · 행이 여덟이 아니면 잡는다 — 분모가 흔들리면 아래 수는 무의미하다",
       "분모" in parse_aa_cr8("| CR1 | 가격 | 0 | e |")[1])

    # ── ★★ [턴 AB · P-232] CR 표가 **두 벌**이 된다 — 갈리면 빨강 ──────────
    #    세종 §4-1(정본)과 N 전사가 갈리면 그때 낸 수는 둘 중 어느 쪽의 수도 아니다.
    _cr_wo = _cr_doc.replace("| CR6 | SLA v1.0 | 0.5 |", "| CR6 | SLA v1.0 | 0.5 |")
    _cr_diff = _cr_doc.replace("| CR1 | 가격 숫자 4 | 0 |",
                               "| CR1 | 가격 숫자 4 | 1 |")
    _r, _w, _lab, _n, _rd = aa_cr8_chain([("정본", _cr_wo), ("전사", _cr_doc)])
    ok("★ 양성 · 두 벌이 **같으면** 초록이고 그 사실을 적는다",
       len(_r) == 8 and not _rd and any("대조했다" in x for x in _n))
    _r2, _w2, _lab2, _n2, _rd2 = aa_cr8_chain([("정본", _cr_wo), ("전사", _cr_diff)])
    ok("★★ 음성 · 두 벌이 **갈리면 빨강**이다 — 조용히 첫 것을 고르지 않는다",
       any("갈렸다" in x for x in _rd2))
    ok("★ 그때도 **정본(첫 출처)의 수**를 쓴다 — 전사가 원본을 못 이긴다",
       _r2[0]["value"] == 0.0 and _lab2 == "정본")
    _r3, _w3, _lab3, _n3, _rd3 = aa_cr8_chain([("옛 자리", "8칸 중 2.2")])
    ok("★ 출생 표본 · 표가 **어디에도 없으면** 회색이고 사유에 「어디에도 없다」가 있다",
       _r3 == [] and "어디에도 없다" in _w3)
    ok("★ 수를 **어디서 읽었는지** 말한다 (출처 없는 수는 인용이다)", _lab == "정본")
    ok("★ 음성 · 행이 여덟이 아닌 출처는 **빨강으로** 잡는다(조용히 건너뛰지 않는다)",
       any("행이" in x for x in
           aa_cr8_chain([("깨진 표", "| CR1 | 가격 | 0 | e |")])[4]))

    # ── ★★ [턴 AB · 실측] **표가 제 합을 적는다. 그 합이 행과 갈렸다** ────────
    #    WO-04 §4-1 은 여덟 행 아래 「합 **2.0/8 = 25 %**」를 적었는데 여덟 행을
    #    더하면 **1.5** 다. 읽는 사람은 굵게 적힌 합을 읽고, 그 합은 다시 셀 수
    #    없는 수다 — **행이 정본이다.** 이 갈래가 없으면 25 가 조용히 산다.
    ok("★ 양성 · 표가 적은 합을 **읽는다**",
       parse_aa_cr8_sum("| **합** | | **2.0/8 = 25 %** | 격자 안 |") == 2.0)
    ok("★ 음성 · 합 줄이 없으면 **None** 이다(0 으로 세지 않는다)",
       parse_aa_cr8_sum("| CR1 | 가격 | 0 | e |") is None)
    _cr_lie = _cr_doc + "\n| **합** | | **2.0/8 = 25 %** | 격자 안 |"
    ok("★★ 음성 · 합 2.0 인데 행의 합이 0.5 면 **빨강**이다 — 「행이 정본이다」",
       any("표의 합이 제 행과 갈렸다" in x
           for x in aa_cr8_chain([("정본", _cr_lie)])[4]))
    # ★★ [턴 AB] **같은 수를 다르게 적은 것은 갈림이 아니다** — 여덟 칸이 전부
    #    빨강으로 났던 자리다(WO 는 `0` · N 은 `**없다** — 값 0`).
    _cr_n = _cr_doc.replace("| 0 |", "| **없다** — 값 0 |").replace(
        "| 0.5 |", "| **반** — 값 0.5 |")
    _rn, _wn, _labn, _nn, _rdn = aa_cr8_chain([("정본", _cr_doc), ("전사", _cr_n)])
    ok("★★ 음성 · **같은 수를 다르게 적은 것**을 갈림으로 찍지 않는다 "
       "(글자가 아니라 값을 댄다)", not _rdn and len(_rn) == 8)
    ok("★ 그리고 말로 적은 칸(「없다」·「반」)에서도 **같은 값**을 읽는다",
       [r["value"] for r in _rn]
       == [r["value"] for r in aa_cr8_chain([("전사", _cr_n)])[0]])
    # ★★ [턴 AB] 한 문서에 표가 **둘** 있으면 여덟 행짜리 첫 표를 쓴다.
    _two = _cr_doc + "\n\n### 대조\n\n" + _cr_n
    ok("★★ 음성 · 한 문서에 CR 표가 **둘**이어도 16행으로 읽지 않는다 "
       "(N 전사본이 §4 에 대조표를 한 번 더 적는다)",
       len(parse_aa_cr8(_two)[0]) == 8 and not parse_aa_cr8(_two)[1])
    _cr_true = _cr_doc + "\n| **합** | | **0.5/8 = 6.25 %** | 격자 안 |"
    ok("★ 양성 · 합이 행과 **맞으면** 빨강이 아니다(없는 갈림을 만들지 않는다)",
       not aa_cr8_chain([("정본", _cr_true)])[4])

    # ── ★★★ P-253 · 턴 AD 파 2 — 대장 부류 줄을 **6키(여섯째 부류) 줄**에서
    #    읽는다(파일을 다시 읽지 않는다). 옛 5키 줄은 걷었다 ───────────────
    #: unmeasurable 60 + measured_red 4 = 64 — 옛 접힌 모양의 「못 잼 64」와
    #: 같은 총량이 되도록 골랐다(아래 `_roll` 표본과 나란히 대조되도록).
    _ga = ("[GA] [입력] ★ P-246 여섯째 부류 — closed 80 · ratchet 3 · rule_only 3 · "
           "unmeasurable 60 · measured_red 4 · gate_only 4  (점수는 안 움직인다 — "
           "measured_red 도 unmeasurable 도 0.0)")
    ok("★ 양성 · 6키 줄을 읽는다", (parse_ga_kinds(_ga) or {}).get("total") == 154)
    ok("★ 양성 · 부류 합이 절 수와 같다", (parse_ga_kinds(_ga) or {})["sum"] == 154)
    ok("★ 양성 · **여섯째 부류(measured_red)를 따로 읽는다**(더는 못 잼에 안 접힌다)",
       (parse_ga_kinds(_ga) or {})["counts"].get("measured_red") == 4)
    ok("★ 음성 · 부류 줄이 없으면 **None** 이다(0 이 아니다)",
       parse_ga_kinds("[GA] 아무 말 없음") is None)

    #: ★★★ 출생 표본(D-310) — 옛 5키 줄이 **다시 나타나면 빨강**이다(P-253).
    #:   09-22 저녁 실측이 이 표본을 낳았다: 이 산출기가 옛 정규식으로 옛
    #:   5키 줄만 읽어 「못 잼 71」 안에 「재서 빨강」 3 이 묻혔다(위 `_KIND_LINE`
    #:   주석의 재서 확인 그대로 — 합성이 아니다). 이제 그 줄은 **더는 부류로도
    #:   안 읽히고**, 더 나아가 **그 모양이 나타났다는 사실 자체가 빨강**이다 —
    #:   그래야 다음 사람이 「호환」이라는 이름으로 되살리지 못한다.
    _ga_old_5key = ("[GA] [입력] 「초록」 부류 154절 — closed 80 · ratchet 3 · "
                    "rule_only 3 · unmeasurable 64 · gate_only 4")
    ok("★ 음성 · 옛 5키 줄은 **더는 부류 줄로 안 읽힌다**(P-253 으로 걷었다)",
       parse_ga_kinds(_ga_old_5key) is None)
    ok("★★ 양성 · 옛 5키 줄이 나타나면 **잡는다**(재발 감지, D-310 출생 표본)",
       old_5key_line_present(_ga_old_5key))
    ok("★ 음성 · 6키 줄만 있으면 재발이 아니다(안전하다)",
       not old_5key_line_present(_ga))
    ok("★★ 양성 · `aa_report()`가 옛 5키 줄의 재발을 **빨강**으로 낸다(회색이 아니다)",
       any("P-253 재발" in r for r in
           aa_report(ga_out=_ga_old_5key, click=None, click_why="x",
                     onboard_text="", review_text="")["red"]))

    # ── ★ 영역 꼬리에서 closed 를 **뺄셈으로** 되찾는다 ────────────────────
    _area = ("  2  보안                     가중 20%  절 16/20 =  80%  →  16.00   "
             "(래칫 1 · 규칙만 1 · 못 잼 4 · 게이트만 0)")
    _ak = parse_ga_area_kinds(_area)
    ok("★ 양성 · 영역 꼬리에서 closed 14 를 되찾는다",
       _ak and _ak[0]["kinds"]["closed"] == 14)
    ok("★ 양성 · 그 영역의 kind 점수는 15.5/20 = 77.5% 다",
       abs(area_kind_total(_ak, _t)[0] - 15.5) < 1e-9)
    ok("★ 음성 · 꼬리가 없는 줄은 안 읽는다(0 으로 세지 않는다)",
       parse_ga_area_kinds("  2  보안  가중 20%  절 16/20 =  80%") == [])

    # ── ★ 세 수 전체 — 양성 한 벌과 음성 한 벌 ─────────────────────────────
    _ga_full = "\n".join([
        "  1  기능 완결성                 가중 20%  절 10/39 =  26%  →   5.13   "
        "(래칫 0 · 규칙만 0 · 못 잼 29 · 게이트만 0)",
        "[GA] ★ 상용 오픈 가중 합계 **66.5%** [실측]",
        _ga])
    _rep = aa_report(ga_out=_ga_full,
                     click={"green": 32, "red": 1, "grey": 15,
                            "n": 48, "when": "", "exit": 2},
                     onboard_text="합계 **24.5 / 48 = 51.0%**",
                     review_text=_cr_doc)
    ok("★ 양성 · FC 세 칸을 다 쟀다", _rep["fc"]["n_measured"] == 3)
    #: ★★ **음성 · 이 도구의 가장 미끄러운 자리** [실측 2026-09-21 · 턴 AA].
    #:   그 게이트가 「0/48 · 초록 0 · 빨강 0 · 회색 48」을 낸다. 그 0 을 칸에
    #:   그대로 적으면 FC 가 **0점 한 칸**을 받고 수가 내려간다 — 그런데 그것은
    #:   「못 한다」가 아니라 **「안 쟀다」**다. 이 갈래가 그 둘을 가른다.
    _rep_nil = aa_report(ga_out=_ga_full,
                         click={"green": 0, "red": 0, "grey": 48,
                                "n": 48, "when": "", "exit": 0},
                         onboard_text="합계 **24.5 / 48 = 51.0%**",
                         review_text=_cr_doc)
    ok("★★ 음성 · 게이트가 **한 행도 판정하지 않았으면** 그 칸은 **회색**이다 — 0점이 아니다",
       _rep_nil["fc"]["n_measured"] == 2
       and not _rep_nil["fc"]["cells"][0]["measured"])
    ok("★ 그때 FC 측정치는 **남은 두 칸**으로 난다 — 0 으로 눌러 적은 25.5 가 아니다",
       abs(_rep_nil["fc"]["measured_pct"] - 38.3) < 0.2)
    ok("★ 그리고 그 사실이 **사유로 적힌다**(조용히 회색이 되지 않는다)",
       any("한 행도 판정하지 않았다" in g for g in _rep_nil["grey"]))
    # ★★ [턴 AB] **`--static` 의 거짓 0** — 게이트를 안 부르면 영역 ① 도달이
    #    꼬리에 `0/39` 로 찍힌다. 그 0 을 칸에 적으면 FC 가 22 점 떨어진다.
    _ga_static = chr(10).join([
        "[GA] ★★ 이 실행은 **정적 갈래(--static)** 다 — 게이트를 **한 벌도 안 불렀다**",
        "  1  기능 완결성                 가중 20%  절 0/39 =   0%  →   0.00   "
        "(래칫 0 · 규칙만 0 · 못 잼 39 · 게이트만 0)",
        _ga])
    _rep_st = aa_report(ga_out=_ga_static, click=None, click_why="x",
                        onboard_text="합계 **24.5 / 48 = 51.0%**",
                        review_text=_cr_doc)
    ok("★★ 음성 · 정적 갈래의 `0/39` 를 **0 으로 적지 않는다** — 회색이다",
       not _rep_st["fc"]["cells"][2]["measured"])
    ok("★ 그리고 그 사실이 **사유로 적힌다**(조용히 회색이 되지 않는다)",
       any("정적 갈래" in g for g in _rep_st["grey"]))
    ok("★ 양성 · 게이트를 부른 실행에서는 그 칸이 **선다**(없는 회색을 만들지 않는다)",
       _rep["fc"]["cells"][2]["measured"])

    ok("★ 양성 · FC = (66.7 + 51.0 + 25.6) ÷ 3 = 47.8 — 세종의 수와 같다",
       abs(_rep["fc"]["measured_pct"] - 47.8) < 0.1)
    ok("★ 음성 · PR 은 **네 칸 중 하나만** 쟀다 — 뒤 세 칸은 증거가 0건이다",
       _rep["pr"]["n_measured"] == 1 and len(_rep["pr"]["grey"]) == 3)
    ok("★ 음성 · PR 하한(회색을 0으로) %.1f 과 측정치(회색을 분모에서) %.1f 는 **다른 수**다"
       % (_rep["pr"]["lower"], _rep["pr"]["measured_pct"]),
       abs(_rep["pr"]["lower"] - _rep["pr"]["measured_pct"]) > 10)
    ok("★ 양성 · PR 측정치는 kind 평평 점수 56.2 다 (분모가 0.7 뿐이므로)",
       abs(_rep["pr"]["measured_pct"] - 56.17) < 0.05)
    ok("★ 양성 · P-216 내려간 수 — 상용 66.5 → 63.3",
       _rep["drop"] and abs(_rep["drop"]["kind"] - 5.13) < 0.05)
    ok("★ 양성 · `MEASURED=` 줄이 **분모를 말한다**",
       "분모" in aa_measured_line(_rep) and "3" in aa_measured_line(_rep))
    ok("★ 음성 · CR 8칸 표가 없으면 CR 은 **회색 8칸**이다",
       aa_report(ga_out=_ga_full, click=None, click_why="게이트를 못 불렀다",
                 onboard_text="", review_text="8칸 중 2.2"
                 )["cr"]["measured_pct"] is None)
    _rep0 = aa_report(ga_out="", click=None, click_why="게이트를 못 불렀다",
                      onboard_text="", review_text="")
    ok("★ 출생 표본 · 아무것도 못 읽으면 **세 수 전부 회색**이다(0 이 아니다)",
       all(_rep0[k]["measured_pct"] is None for k in ("fc", "pr", "cr")))
    ok("★ 출생 표본 · 그때 `MEASURED=` 는 **잰 칸 0** 이라고 적는다(거짓 분모가 아니다)",
       "0/3" in aa_measured_line(_rep0))
    ok("★ 음성 · 문서가 적은 격자 밖의 수(2.2)를 **빨강으로** 잡는다",
       any("격자 밖" in r for r in aa_report(
           ga_out=_ga_full, click=None, click_why="x", onboard_text="",
           review_text="| Commercial Readiness | 27 | … 8칸 중 2.2 |")["red"]))

    fails = [n for n, g in cases if not g]
    if verbose or fails:
        for name, good in cases:
            if verbose or not good:
                print("  %-4s %s" % ("OK" if good else "FAIL", name))
    if fails:
        print("%s 자기시험 **실패** %d건 — 판정기를 먼저 의심한다 (D-350)" % (TAG, len(fails)))
        return 1
    print("%s 자기시험 %d건 통과 — ★ **출생 표본**(38%% 격자 · 셈법 없으면 회색) 포함 · "
          "음성 대조 9(격자 밖 · 행 수 · 근거 없는 1 · 세종 값 잔존 · 손 밖 · 머리줄 눈금 …)"
          % (TAG, len(cases)))
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# FC · PR — 수를 내지 않는다
# ═══════════════════════════════════════════════════════════════════════════

def fc_pr_report(fcpr_text: str = "", prd_text: str = "") -> dict:
    """FC·PR 을 **셈법 문서에서** 센다. 문서가 없으면 그때는 여전히 회색이다.

    ★ 출생 표본 ② 는 죽지 않았다 — 뜻이 좁아졌을 뿐이다. 「82·83」 이 나쁜 수였던 이유는
      **셈법 없이 나왔기 때문**이다. 그러므로 이 함수의 첫 갈래는 지금도 같다:
      **셈법이 없으면 수를 내지 않는다.** 셈법이 생겼으니 이제는 그 문서를 읽어서 낸다.
    """
    out: dict = {"color": "회색", "why": "셈법 미정 · 세종 판정 필요",
                 "fc": None, "pr": None, "red": [], "gray": [], "disagree": []}
    if not fcpr_text.strip():
        out["gray"] = ["FC·PR: 셈법 문서가 없다 — SOURCE_MISSING. "
                       "셈법 없는 수를 지어내지 않는다"]
        return out

    fc_rows = read_measured_grid(fcpr_text, FC_ROWS)
    pr_rows = read_measured_grid(fcpr_text, PR_ROWS)
    if fc_rows is None or pr_rows is None:
        out["why"] = "셈법 문서에서 실측 표(18행·15행)를 못 찾았다"
        out["red"] = ["FC·PR: 셈법 문서에 **행 %s·%s 짜리 실측 표**가 없다 — "
                      "문서의 모양이 바뀌었다면 **이 도구도 함께 고쳐라**. "
                      "못 읽은 채 넘어가면 이 도구가 눈이 먼다 (P-93)"
                      % (FC_ROWS, PR_ROWS)]
        return out

    fc, fc_red, fc_gray = judge_measured_grid(fc_rows, FC_ROWS, "FC")
    pr, pr_red, pr_gray = judge_measured_grid(pr_rows, PR_ROWS, "PR")

    #: ① 분모 확인 — PRD v2.6 §3 의 행이 정말 18 인가 (§1 이 못박은 분모)
    prd_rows, prd_table, prd_stated = parse_prd_painpoints(prd_text or "")
    if prd_text and len(prd_rows) != FC_ROWS:
        fc_red.append("FC: PRD v2.6 §3 페인포인트 표가 %d행이다 — 셈법 §1 의 분모는 %d다"
                      % (len(prd_rows), FC_ROWS))
    #: ② PRD 가 **자기 자신과** 갈리는가 — 표의 판정 열 대 그 아래 요약 문장
    if prd_stated and prd_table and prd_stated != prd_table:
        fc_red.append("FC: PRD v2.6 §3 이 **자기 자신과 갈렸다** — 표의 판정 열 %s ≠ "
                      "요약 문장 %s. 세종 합 9.5 가 어느 쪽으로 센 수인지 정하고 "
                      "**PRD 를 고쳐라**(산출기가 맞출 자리가 아니다)"
                      % (prd_table, prd_stated))

    #: ③ 세종 [판정] 과 어긋난 행 — 매 턴 보고에 들어가는 수
    fc_cpo = {r["no"]: r["value"] for r in prd_rows}
    pr_cpo = parse_cpo_pr_values(
        slice_section(fcpr_text, "## 3. 세종", "## 3′") or fcpr_text)
    if len(pr_cpo) != PR_ROWS:
        pr_gray.append("PR: 세종 §3 판정 표에서 %d칸만 읽혔다(15 이어야) — "
                       "어긋난 행 셈이 불완전하다" % len(pr_cpo))
    fc_dis = disagreeing_rows(fc_rows, fc_cpo)
    pr_dis = disagreeing_rows(pr_rows, pr_cpo)

    #: ④ 문서가 적어 둔 수와 다시 센 수 — 갈리면 빨강 (CR 과 같은 자리)
    stated = parse_fcpr_stated(fcpr_text)
    for key, got, name in (("fc_lower", fc["lower"], "FC 하한"),
                           ("fc_upper", fc["upper"], "FC 상한"),
                           ("pr", pr["lower"], "PR")):
        if key in stated and abs(stated[key] - got) > 0.15:
            fc_red.append("%s: 문서가 적은 %.1f%% ≠ 다시 센 %.1f%% — "
                          "**문서와 코드가 갈렸다**" % (name, stated[key], got))

    out.update({
        "color": "빨강" if (fc_red + pr_red) else ("회색" if (fc_gray + pr_gray) else "초록"),
        "why": "", "fc": fc, "pr": pr,
        "red": fc_red + pr_red, "gray": fc_gray + pr_gray,
        "disagree": {"FC": fc_dis, "PR": pr_dis},
        "prd": {"rows": len(prd_rows), "table": prd_table, "stated": prd_stated},
    })
    return out


# ═══════════════════════════════════════════════════════════════════════════
# P-117 — **보고 첫 표를 사람이 타자하지 않는다**
#
# 왜 이 절이 생겼나 (턴 O · 2026-09-10)
# --------------------------------------
#   보고의 첫 표는 여덟 줄인데 그 여덟이 **매 턴 사람 손으로 타자**됐다. 손으로 옮긴
#   수는 옮기는 동안 낡고, 낡은 줄과 갓 잰 줄이 한 표에서 같은 굵기로 보인다.
#
# ★★ 그리고 이 턴에 **술어가 둘이 됐다** — 이 절이 존재하는 진짜 이유다
# ---------------------------------------------------------------------
#   ⓐ 「있는가」(v0.1 · **산출물** 술어) — 화면·라우트·시험이 실재하는가.
#      이 도구가 셈법 문서(GX-FCPR §3′ · GX-CR §2~3)를 읽어 **다시 센다**.
#   ⓑ 「끝나는가」(v0.2 · **손** 술어 · PRD v2.7 §1) — 역할 계정으로 눌렀더니
#      호출이 나가고 서버 값이 바뀌고 화면 칸이 바뀌었는가.
#      09-08 사용자 점검이 그 술어로 재서 **FC 33.3 · PR 20.0 · CR 12.5** 를 냈다.
#
#   **둘 다 참이고, 섞으면 둘 다 거짓이 된다.** 평균을 내면 「그려진 것」이
#   「끝나는 것」의 점수를 빌려 가고, 대표는 그 차이를 못 본다 — 그 차이가 지금
#   이 제품의 **가장 큰 사실**이다. 그래서 이 표는 두 칸을 **나란히** 두고,
#   **분모가 같은 자리에서만** 차를 뺀다:
#
#       · PR      — 같은 15칸을 두 술어로 쟀다  → 차를 낸다
#       · 온보딩  — 같은 48행을 두 술어로 쟀다  → 차를 낸다
#       · FC · CR — 분모가 다르다(18 페인 ↔ 48 흐름 · 9 항목 ↔ 8 조건)
#                   → **차를 내지 않는다.** 「분모가 다르다」라고 적는다.
#
#   ⓑ 칸은 **이 도구가 잰 수가 아니다.** 그래서 언제나 출처와 잰 때를 달고 나가고,
#   `verify_click_completes`(Q 차선)가 서면 인용이 아니라 **게이트를 부른 수**로
#   저절로 바뀐다 — 값을 코드에 베끼지 않는 이 도구의 규칙 그대로다.
# ═══════════════════════════════════════════════════════════════════════════

REVIEW_DOC = (ROOT / "docs" / "design"
              / "GX-REVIEW_상용점검_사용자관점_v2_20260910.md")
PRD27_DOC = ROOT / "docs" / "design" / "PRD_v2.7_눌러서끝나는가_20260910.md"
ONBOARD_DOC = ROOT / "docs" / "agent" / "onboarding_48.md"
RESUME_DOC = ROOT / "docs" / "agent" / "RESUME_NEXT.md"
CLICK_SCRIPT = ROOT / "scripts" / "verify_click_completes.py"
#: 보험 패치는 **저장소 밖**에 뜬다 — 저장소가 통째로 날아가도 남아야 하므로.
PATCH_DIR = ROOT.parent / "_patches"

#: 온보딩 48행 · 손 술어의 FC 분모. 둘이 같은 48 이라는 것이 이 표의 요점이다.
ONBOARD_ROWS = 48


#: [P-332 · 차선 Q · WO-GX-20260924-13 §5 · WO-GX-20260926-12 §12] **참고 회차는
#: 정본이 아니다.** `onboarding_48.md` 절 머리에 이 표식이 있으면(3002 개발 서버
#: 회차 등) 그 절 안의 `N / 48 = P%` 는 **아무리 나중에 있어도** 정본으로 안 집는다
#: — S1 출처는 8500(고객 주소) 회차만이어야 한다(P-317). 표식이 없는 절(지금까지의
#: 관행 · 이 파일 자기시험의 텍스트)은 그대로 「가장 나중 것」을 쓴다 — 규칙이
#: 새로 생긴 것이지 옛 문서·옛 시험이 거짓말하게 된 것이 아니다.
ONBOARD_REF_MARK = "참고 · 개발 서버"
#: 표식은 **그 절 머리 가까이**에 있어야 그 절 전체를 가리킨 것으로 본다. 창을
#: 안 두고 「그 앞 어디에나」로 보면, 정본 절의 본문이 다른 절 이름을 그저
#: **언급만** 해도(예: 「위 §…절에 참고 표기를 더했다」) 정본 절 자신이 참고로
#: 오인될 수 있다 — 실제로 이 문서 2026-09-24 절 초안에서 그렇게 어긋날 뻔했다.
ONBOARD_REF_WINDOW = 400


def _last_non_reference_onboard_match(text: str, matches: list):
    """뒤에서부터 훑어 **참고로 표기되지 않은** 첫 매치를 고른다.

    절 경계는 `\\n## ` (그 문서의 절 머리 표식)로 잡는다. 표식이 그 절 머리
    `ONBOARD_REF_WINDOW`자 안에 있으면 그 절은 참고고, 그 절 안의 매치는 전부
    건너뛴다. 전부 참고면(오늘은 없는 일이다) 그래도 마지막 것을 낸다 — 회색보다
    「어긋날 수 있는 수」가 낫다(문서가 모순되면 `consistent` 검산이 잡는다).
    """
    for m in reversed(matches):
        start = text.rfind("\n## ", 0, m.start())
        start = 0 if start == -1 else start
        header_zone = text[start:start + ONBOARD_REF_WINDOW]
        if ONBOARD_REF_MARK in header_zone:
            continue                       # 이 절은 참고다 — 정본 후보에서 뺀다
        return m
    return matches[-1]


def parse_onboarding(text: str) -> dict | None:
    """`onboarding_48.md` 가 **마지막으로 적은, 참고 아닌** `N / 48 = P%` 를 집고 검산한다.

    이 문서에는 재측 절이 여럿이라 같은 꼴이 열 번 넘게 나온다. **가장 나중 것**이
    지금 값이다(CR 표에서 마지막 표를 쓰는 것과 같은 규칙) — 다만 [P-332] **「참고 ·
    개발 서버」로 적은 절은 아무리 나중이어도 건너뛴다**(`_last_non_reference_
    onboard_match` 참조). 그리고 집은 뒤 **N ÷ 48 이 정말 P 인지** 다시 곱해 본다 —
    문서 안에서 분자와 백분율이 갈리면 그것은 이 도구가 잡아야 할 어긋남이다.
    """
    matches = list(re.finditer(
        r"(\d+(?:\.\d+)?)\s*/\s*%d\s*=\s*\*{0,2}(\d+(?:\.\d+)?)\s*%%"
        % ONBOARD_ROWS, text))
    if not matches:
        return None
    chosen = _last_non_reference_onboard_match(text, matches)
    num, pct = float(chosen.group(1)), float(chosen.group(2))
    calc = num / ONBOARD_ROWS * 100.0
    return {"sum": num, "n": ONBOARD_ROWS, "pct": pct, "calc": calc,
            #: 문서는 60.4 를 60 으로 줄여 적는다 — 반올림 한 칸까지는 어긋남이 아니다.
            "consistent": abs(calc - pct) <= 0.6}


#: 「끝나는가」 세 수가 적힌 꼴 — `| **FC** | … | **33.3%** (16.0/48) | ≥ 70 | …`
_HANDSON_ROW = re.compile(
    r"^\|\s*\*{0,2}(FC|PR|CR)\*{0,2}\s*\|.*?"
    r"\*\*(\d+(?:\.\d+)?)\s*%\*\*\s*\(\s*(\d+(?:\.\d+)?)\s*/\s*(\d+)\s*\)"
    r"(?:.*?≥\s*(\d+(?:\.\d+)?))?")


def parse_handson(text: str) -> dict:
    """「끝나는가」 술어로 잰 FC·PR·CR **과 RC-1 문턱**을 집는다.

    ★ 이것은 **이 도구가 잰 수가 아니다.** 사람이 눌러 본 점검의 수이고, 그래서
      부르는 쪽이 언제나 출처와 잰 때를 함께 낸다. 여기서 하는 일은 「베끼지 않고
      읽는다」 하나뿐이다 — 코드에 33.3 을 적어 두면 다음 점검에서 그 줄이 거짓말한다.
    """
    out: dict = {}
    for line in text.splitlines():
        m = _HANDSON_ROW.match(line.strip())
        if not m:
            continue
        key, pct, num, den, rc = m.groups()
        out.setdefault(key, {"pct": float(pct), "sum": float(num),
                             "n": int(den), "rc1": float(rc) if rc else None})
    return out


def parse_rc1(text: str) -> dict:
    """PRD v2.7 §3 의 한 줄 — `**RC-1 문턱**: FC ≥ 70 · PR ≥ 80 · CR ≥ 75 · 상용 /100 ≥ 88`."""
    out: dict = {}
    m = re.search(r"RC-1 문턱\*{0,2}\s*[:：](.+)", text)
    if m:
        for name, val in re.findall(r"(FC|PR|CR|상용 /100)\s*≥\s*(\d+(?:\.\d+)?)", m.group(1)):
            out[name] = float(val)
    return out


def gate_marks(pr_rows: list[dict]) -> list[tuple[str, str, float, int]]:
    """PR 15칸 → 관문 다섯의 표식. **칸을 다시 세지 않는다** — §3′-2 의 그 값이다.

    ● 셋 다 1 · ○ 셋 다 0 · ◐ 그 사이. 관문 이름은 표의 「관문」 칸에서 읽는다
    (3개씩 끊는다고 가정하지 않는다 — 표가 바뀌면 이름이 먼저 움직인다).
    """
    order: list[str] = []
    bag: dict[str, list[float]] = {}
    for r in pr_rows:
        cells = r.get("cells") or []
        name = _plain(cells[1]) if len(cells) > 1 else ""
        if not re.fullmatch(r"G[1-5]", name):
            continue
        if name not in bag:
            order.append(name)
            bag[name] = []
        bag[name].append(0.0 if r["value"] is None else r["value"])
    out = []
    for name in order:
        vals = bag[name]
        s = sum(vals)
        mark = "●" if s == len(vals) else ("○" if s == 0 else "◐")
        out.append((name, mark, s, len(vals)))
    return out


def commit_state() -> dict:
    """커밋 해시 · 작업본 · **보험 패치**. 첫 표 여덟째 줄은 이 셋으로 쓴다.

    ★ 「보류한 사유」는 이 도구가 못 잰다 — 사람의 결정이다. 대신 **잴 수 있는 것**을
      잰다: 미커밋 파일 수와, 보험 패치가 **지금 작업본보다 낡았는지**. 낡은 보험은
      보험이 아니고, 그 사실은 사유보다 앞선다.
    """
    def git(*args) -> str:
        try:
            p = subprocess.run(["git", "-C", str(ROOT), *args],
                               capture_output=True, timeout=60)
            return (p.stdout or b"").decode("utf-8", "replace").strip()
        except Exception:                                     # noqa: BLE001
            return ""

    head = git("rev-parse", "--short=7", "HEAD")
    when = git("log", "-1", "--format=%cI")
    porcelain = git("status", "--porcelain")
    lines = [l for l in porcelain.splitlines() if l.strip()]
    kinds: dict[str, int] = {}
    for l in lines:
        kinds[l[:2].strip() or "?"] = kinds.get(l[:2].strip() or "?", 0) + 1

    #: 작업본에서 **가장 나중에 손댄 때** — 보험 패치와 견줄 상대다.
    newest = 0.0
    for l in lines:
        rel = l[3:].strip().strip('"')
        p = ROOT / rel.split(" -> ")[-1]
        try:
            newest = max(newest, p.stat().st_mtime)
        except OSError:
            continue

    patches = []
    if PATCH_DIR.is_dir():
        for p in sorted(PATCH_DIR.glob("*worktree*.patch")):
            patches.append((p.stat().st_mtime, p))
    patch = patches[-1][1] if patches else None
    patch_mtime = patches[-1][0] if patches else None

    return {"head": head, "committed_at": when, "dirty": len(lines), "kinds": kinds,
            "clean": not lines, "newest_worktree_mtime": newest,
            "patch": patch, "patch_mtime": patch_mtime,
            "patch_stale": bool(patch_mtime and newest and patch_mtime < newest)}


def run_click_completes() -> tuple[dict | None, str]:
    """`verify_click_completes` 를 **부른다**(읽어서 답하지 않는다 · D-210).

    `--measure` 없이 부른다 — 그 갈래는 브라우저를 띄우고 **역할 계정 넷의 자리를
    가져간다.** 이 도구는 그 자리를 뺏지 않는다. 증거가 없으면 그 게이트가 스스로
    「0/48 · 회색 48」이라 적고, 우리는 그것을 그대로 옮긴다.

    ★★ **눈금이 다르다.** 그 게이트는 행마다 {초록 · 빨강 · **회색**} 셋을 내고,
      회색은 「못 쟀다」다 — 0 이 아니다(D-301). 그러므로 이 도구는 그 게이트의 수를
      **한 수로 옮기지 않는다**: 하한 = 초록 ÷ 48 · 상한 = (초록 + 회색) ÷ 48.
      회색을 0 으로 눌러 적으면 못 잰 것을 「못 한다」로 바꿔 쓰는 것이고,
      1 로 올려 적으면 초록이 아닌 것에 초록을 주는 것이다.
    """
    if not CLICK_SCRIPT.is_file():
        return None, "게이트 «scripts/verify_click_completes.py» 가 아직 없다"
    try:
        p = subprocess.run([sys.executable, str(CLICK_SCRIPT)],
                           capture_output=True, timeout=1800)
    except Exception as exc:                                   # noqa: BLE001
        return None, "게이트를 못 불렀다: %s" % exc
    out = ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace")
    m = re.search(r"초록 (\d+) · 빨강 (\d+) · 회색 (\d+)", out)
    if not m:
        return None, "게이트가 «초록 N · 빨강 N · 회색 N» 을 내지 않았다 (exit %s)" % p.returncode
    g, r, y = (int(x) for x in m.groups())
    mw = re.search(r"\[실측\s+([^\s·\]]+)", out)
    return {"green": g, "red": r, "grey": y, "n": ONBOARD_ROWS,
            "when": mw.group(1) if mw else "", "exit": p.returncode}, ""


def _stamp(path) -> str:
    """파일이 **언제 적혔는지**. 수 옆에 날짜가 없으면 그 수는 나이를 숨긴다."""
    try:
        import datetime as _dt
        return _dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%m-%d %H:%M")
    except Exception:                                          # noqa: BLE001
        return "?"


# ═══════════════════════════════════════════════════════════════════════════
# 수집
# ═══════════════════════════════════════════════════════════════════════════

#: ★★ [턴 AB · 차선 N 실측 · 조율자 확정] **로그인 창이 없는 차선은 `--static`.**
#:   인자 없이 부르면 `verify_ga_readiness` 가 자식 게이트를 부르고, 그중
#:   `verify_contract_route_reach.py` 가 **로그인한다** — 남의 창을 가져간다(D-510).
#:   `--no-gates` 로는 **못 막는다**(절의 게이트만 끄고 영역 ①은 그대로 부른다).
#:   로그인을 0 으로 만드는 것은 **`--static` 뿐**이다.
#:   ⚠ 그 대가: `--static` 은 **게이트 색을 안 본다.** 이 산출기가 쓰는 것은
#:     **부류 셈·절 수·영역 꼬리**뿐이고 그 셋은 대장이 내는 수라 안 달라진다.
#:     달라지는 것은 「대장 상태 ↔ 게이트 색」 대조인데, 그 대조는 **조율자가
#:     병합 뒤 전량으로** 한다(창을 가진 사람의 자리다).
GA_STATIC_ARGS = ("--static",)


def run_ga(args: tuple = GA_STATIC_ARGS) -> tuple[str, int | None]:
    if not GA_SCRIPT.is_file():
        return "", None
    p = subprocess.run([sys.executable, str(GA_SCRIPT)] + list(args),
                       capture_output=True, timeout=900)
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    return out, p.returncode


# ═══════════════════════════════════════════════════════════════════════════
# 본문
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# P-220 · 턴 AA — 세종의 **세 수**를 산출기가 낸다 (2026-09-21 · 차선 Q)
#
# 왜 이 절이 생겼나
# -----------------
#   세종이 `GX-REVIEW v2.0 §0` 에 세 수를 **정의**했다 — FC 47.8 · PR 56 · CR 27.
#   그런데 그 세 수는 **손으로 적힌 수**다. 손으로 적은 수는 정본이 움직여도
#   안 움직인다(P-93 의 그 병). 그래서 산출기가 낸다.
#
# ★★ 이 절의 한 줄 — **못 재는 칸은 0 이 아니라 회색이다**
#   재부팅 아침 N/10 은 **증거가 0건**이고(다섯 턴째) 스테이징 걷기도 0이다.
#   그 칸을 **0 으로 세는 것**과 **「못 쟀다」로 세는 것**은 다른 일이다:
#
#       0 으로 세면   → 「우리는 그것을 못 한다」   (제품이 무너졌다는 말)
#       회색으로 세면 → 「우리는 그것을 모른다」   (우리가 안 쟀다는 말)
#
#   둘을 뭉치면 증거를 만들 이유가 사라진다 — 어차피 수는 그대로이므로.
#   그래서 이 산출기는 **세 수를 한 수로 내지 않는다**:
#
#       하한 = 회색을 0 으로 · 상한 = 회색을 1 로 · 측정치 = 회색을 분모에서 뺀다
#
#   그리고 `MEASURED=` 머리글에 **그 분모를 적는다.** 분모를 안 말하는 수는
#   「무엇을 보고 한 말인가」에 답하지 못한다(D-301 · P-204).
#
# ★ **분모가 늘어 수가 내려가면 절 수를 함께 적는다.** 「66.5 → 51.9」만 적으면
#   읽는 사람은 제품이 후퇴했다고 읽는다. 실제로 움직인 것은 **세는 눈**이다.
#   그래서 모든 줄이 `N/D` 를 값과 **같은 줄에** 싣는다.
# ═══════════════════════════════════════════════════════════════════════════

AA_REVIEW_DOC = (ROOT / "docs" / "design"
                 / "GX-REVIEW_실사용자_상용점검_v2.0_20260921.md")
AA_WO_DOC = (ROOT / "docs" / "workorders"
             / "WO-GX-20260921-03_상용전환_실사용자기준.md")

#: ★★ [턴 AB · P-232] **CR 8칸 표의 출처가 셋이 됐다.** 턴 AA 에는 표가 아예 없어서
#:   CR 이 회색 8칸이었다. 이제 세종이 WO-04 §4-1 에 여덟 줄을 적었고(합 2.0/8),
#:   차선 N 이 그것을 `docs/design/GX-CR_8칸_v1.0_20260921.md` 로 옮겨 적는다.
#:
#:   ⚠ **그래서 표가 두 벌이 될 수 있다.** 두 벌이 갈리면 그때 낸 수는 둘 중 어느
#:     쪽의 수도 아니다(D-369 · P-216 이 막으려던 그 모양). 이 산출기는 **셋을 다
#:     열고 대조한다** — 갈리면 **빨강**이고, 조용히 한쪽을 고르지 않는다.
#:
#:   ★ 순서는 「가까운 것이 먼저」가 아니라 **「정본이 먼저」**다. P-232 는 §4-1 을
#:     정본이라 못박았고, N 의 파일은 **그 정본의 전사**다. 전사가 원본과 갈리면
#:     원본이 이긴다 — 그러나 **갈렸다는 사실을 먼저 소리 내어 적는다.**
AA_CR8_DOC = ROOT / "docs" / "design" / "GX-CR_8칸_v1.0_20260921.md"
AA_WO04_GLOB = "WO-GX-20260921-04_*.md"

#: ★ P-216 — **점수를 `kind` 로 센다** (세종 · 턴 AA).
#:   세 턴 동안 「67.x」라 부르던 수는 `status: 구현` 을 센 수였다. 「구현」은
#:   **닫혔다는 뜻이 아니다** — 대장은 이미 다섯 부류로 갈라 적고 있었는데
#:   점수식만 그 갈래를 안 봤다. 실은 **닫힌 절 80/154** 였다.
#:
#:   ⚠ 이 표는 `verify_ga_readiness.py`(차선 N) 와 **같은 눈금이어야 한다.**
#:     갈리면 두 도구가 같은 대장에서 다른 수를 내고, 그때 낸 수는 둘 중
#:     어느 쪽의 수도 아니다. 그래서 N 쪽에 같은 이름이 서면 **거기서 가져온다** —
#:     두 벌을 두지 않는다(D-369). 아래 `aa_kind_score_table()` 이 그 일을 한다.
KIND_SCORE: dict[str, float] = {
    "closed": 1.0,        # 닫혔다 — 누른 뒤를 봤고 분모가 실재한다
    "ratchet": 1.0,       # 래칫 — **늘지 않음이 조건이다**(아래 주의)
    "rule_only": 0.5,     # 규칙만 — 규칙은 섰으나 현장이 비었다
    "gate_only": 0.5,     # 게이트만 — 제목이 게이트보다 넓다
    "unmeasurable": 0.0,  # 못 잼 — **0 이다. 회색이 아니다**(아래 주의)
}
KIND_ORDER = ("closed", "ratchet", "rule_only", "gate_only", "unmeasurable")

#: ★ **`unmeasurable` 은 왜 회색이 아니라 0 인가.** 회색은 「이 산출기가 못 쟀다」이고,
#:   `unmeasurable` 은 **대장이 재고 나서 「못 잰 절이다」라고 적은 판정**이다.
#:   잰 결과가 「못 잼」인 것과 재지 못한 것은 다르다. 세종이 못박았다 —
#:   **「잠김은 분모에서 빼지 않는다」.** 빼면 대장이 작아지고 수가 올라간다.
#: ★ **`ratchet` 1.0 은 조건부다.** 「늘지 않았다」는 대장이 스스로 적은 말이고
#:   이 산출기가 다시 잰 것이 아니다. 그래서 세는 자리마다 그 사실을 소리 내어 적는다.
KIND_CAVEAT = {
    "ratchet": "래칫 1.0 은 **늘지 않음이 조건**이다 — 그 「늘지 않음」은 대장이 "
               "스스로 적은 말이고 이 산출기가 다시 잰 것이 아니다",
    "unmeasurable": "못 잼 0.0 은 **재고 나서 내린 판정**이다 — 이 산출기의 회색과 "
                    "다르다. 잠김도 여기 있고, **분모에서 빼지 않는다**",
}


def aa_kind_score_table() -> tuple[dict, str]:
    """눈금 표를 **N 쪽에서 먼저 찾는다** — 없으면 내 표를 쓰되 그 사실을 적는다.

    두 벌을 두지 않는다(D-369). `verify_ga_readiness.py` 에 `KIND_SCORE` 라는
    이름이 서면 그 순간부터 그쪽이 정본이고, 내 표는 **대조용**으로만 남는다.
    갈리면 **빨강**이다 — 조용히 한쪽을 고르면 그 수가 어느 쪽의 수인지 모른다.
    """
    if not GA_SCRIPT.is_file():
        return dict(KIND_SCORE), "N 쪽 게이트가 없다 — 내 표로 센다"
    #: ★★ [실측 2026-09-21 · 턴 AA] 처음에는 **소스를 정규식으로 읽었다**. 그리고
    #:   못 찾았다 — N 이 세운 것은 `KIND_SCORE = {…}` 가 아니라 **별명**
    #:   `KIND_SCORE = KIND_POINTS` 였기 때문이다. 판정문은 「N 쪽에 아직 없다」고
    #:   찍었고, **그것은 거짓이었다.** 눈금이 이미 서 있는데 「없다」고 말하는 게이트는
    #:   갈림을 못 본 게이트다 — P-216 이 막으려던 바로 그 모양이다.
    #:   ★ 그래서 **부른다**: 모듈을 import 해 그 이름을 읽는다(읽어서 답하지 않는다 ·
    #:     D-210). N 이 쪽지에 「베끼지 말고 가져다 쓰라」고 적은 그 뜻이다.
    theirs: dict = {}
    how = "import"
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import verify_ga_readiness as _ga
        got = getattr(_ga, "KIND_SCORE", None)
        if isinstance(got, dict):
            theirs = {str(k): float(v) for k, v in got.items()}
    except Exception:                                           # noqa: BLE001
        theirs = {}
    if not theirs:
        #: import 가 막히면(의존성·설정) **소스로 물러선다** — 그러나 물러선 사실을 적는다.
        how = "소스 읽기(물러섬)"
        src = GA_SCRIPT.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^(?:KIND_SCORE|KIND_POINTS)[^=]*=\s*\{(.*?)\}", src, re.M | re.S)
        if m:
            for k, v in re.findall(r"['\"]([a-z_]+)['\"]\s*:\s*([\d.]+)", m.group(1)):
                theirs[k] = float(v)
    if not theirs:
        return (dict(KIND_SCORE),
                "N 쪽(`%s`)에 `KIND_SCORE` 가 **아직 없다** — 내 표로 센다. "
                "N 이 세우면 그쪽이 정본이다 (P-216 은 한 커밋이다)" % GA_SCRIPT.name)
    if theirs != KIND_SCORE:
        return theirs, ("★ **눈금이 갈렸다** — N 쪽(%s) %r 이 내 쪽 %r 과 다르다. "
                        "같은 대장에서 두 수가 난다" % (how, theirs, KIND_SCORE))
    return theirs, ("N 쪽 `%s::KIND_SCORE` 를 **%s 로 가져왔다** — 눈금이 같다. "
                    "두 벌을 두지 않는다 (D-369 · P-216 은 한 커밋이다)"
                    % (GA_SCRIPT.name, how))


#: ★★★ P-253 · 2026-09-23 · 턴 AD 파 2 · 차선 Q — **6키 줄을 읽는다(옛 5키 줄은 걷었다)**.
#:   `verify_ga_readiness` 가 찍던 두 줄 중 **먼저 나오는** 줄은
#:   `「초록」 부류 N절 — closed … unmeasurable … gate_only`(다섯 이름, `measured_red`
#:   없음)이었다 — `measured_red` 를 `unmeasurable` 속에 접어 옛 모양 그대로 낸
#:   **호환용 줄**이었다(N, Q.inbox/N.md). 이 정규식(`부류\s+(\d+)절`)은 그 줄만
#:   걸렸다 — **「★ P-246 여섯째 부류 — …」줄은 「부류 N절」 모양이 아니라서
#:   원래도 안 걸렸다**(N 의 예상이 맞았다). 그래서 이 산출기는 **먼저 나오는
#:   접힌 줄만 읽어 왔다** — 아래 「재서 확인」이 그 사실을 눌러 봤다.
#:
#:   ★★ 재서 확인 [실측 2026-09-22 저녁 · 차선 Q · `--static`]:
#:     `verify_ga_readiness.py --static` 을 실행하고 `parse_ga_kinds()` 에
#:     그 원문을 그대로 먹였더니 `{'total': 155, 'counts': {'closed': 73,
#:     'ratchet': 3, 'rule_only': 3, 'unmeasurable': 71, 'gate_only': 5},
#:     'sum': 155}` 이 났다 — **`measured_red` 가 없다.** 「못 잼 71」 안에
#:     그 순간의 「재서 빨강」 3 이 묻혀 있었다(같은 실행의 6키 줄:
#:     unmeasurable 68 · measured_red 3). 조율자가 게이트를 부르는 갈래로
#:     잰 다른 시각(WO-GX-20260923-07 §1)에는 같은 은닉이 「못 잼 72」 안에
#:     「재서 빨강」 4 로 나타났다 — **합성이 아니라 실측 둘이 같은 병을 보였다.**
#:
#:   P-253(세종)이 「오늘 걷는다」고 판정했다 — `verify_ga_readiness.py`(N 소유,
#:   같은 커밋으로 Q 가 고쳤다) 쪽에서 옛 줄의 print 문을 지웠으므로, 이 정규식도
#:   **유일하게 남은 6키 줄**을 읽도록 바꾼다. **부류 셈·점수 식(`KIND_SCORE`·
#:   `KIND_ORDER`·`kind_points()`)은 이 커밋에서 손대지 않는다** — `measured_red`
#:   는 `unmeasurable` 과 점수가 같으므로(둘 다 0.0), 점수 계산 직전에만 접어
#:   `kind_points()` 에 먹인다(아래 `aa_report()`). 눈금표 자체는 그대로 다섯이다.
_KIND_LINE = re.compile(r"P-246\s*여섯째\s*부류\s*[—-]\s*(.+)")

#: ★ P-253 — **걷어낸 옛 5키 줄이 「호환」이라는 이름으로 되살아나면 잡는다.**
#:   `_KIND_LINE` 을 6키 줄로 바꾸기만 하면, 누군가 다음 턴에 「예전 도구가
#:   이 모양을 읽었으니 호환용으로 남겨 둔다」며 옛 줄을 되살려도 이 산출기는
#:   **조용히 무시**한다(부류 줄을 못 읽었다 · 회색) — 그러나 그 줄이 **다시
#:   나타났다는 사실 자체**는 회색이 아니라 빨강이어야 한다. 되살아난 옛 줄은
#:   `measured_red` 라는 낱말이 그 줄에 없다는 것으로 가른다(6키 줄은 반드시
#:   그 낱말을 담는다).
_OLD_5KEY_LINE = re.compile(r"부류\s+\d+절\s*[—-]")


def old_5key_line_present(out: str) -> bool:
    """★★ 자기시험 표본(D-310 · **출생 표본**) — 이 술어는 실측에서 태어났다.

    2026-09-22 저녁 `--static` 실행에서 이 산출기(옛 정규식)가 옛 5키 줄
    (`「초록」 부류 155절 — … unmeasurable 71 … gate_only 5`, `measured_red` 없음)
    을 읽어 **「못 잼 71」 안에 「재서 빨강」 3 이 묻힌 채로** 점수를 냈다(합성이
    아니다 — 위 `_KIND_LINE` 주석의 재서 확인 그대로). 조율자가 게이트-부르는
    갈래로 잰 다른 시각(WO-GX-20260923-07 §1)의 대장에서는 같은 은닉이 **「못 잼
    72」 안에 「재서 빨강」 4** 로 나타났다. P-253 으로 그 줄을 걷었지만, 코드
    모양만 남으면 「호환」이라는 이름으로 다음 사람이 되살릴 수 있다 — 그래서
    그 모양 자체를 시험한다: 빨강이면 재발, 아니면 안전하다.
    """
    for line in out.splitlines():
        if _OLD_5KEY_LINE.search(line) and "measured_red" not in line:
            return True
    return False


def parse_ga_kinds(out: str):
    """대장의 **부류 셈**을 게이트 출력에서 읽는다 — 파일을 다시 읽지 않는다(D-210).

    P-253 이후 **6키 줄**(`★ P-246 여섯째 부류 — …`)만 읽는다 — 옛 5키 줄은
    걷었고, 이 정규식은 그 줄에도 원래 안 걸렸다(「부류 N절」 모양이 아니라서).
    그 줄은 스스로 총합을 안 적으므로(옛 줄과 달리) **총합은 여섯 칸의 합으로
    센다** — 파일을 다시 읽지 않고(D-210), 이 줄 하나만으로 총합·부류 합이
    항상 같다(구성상 자명하다 — 정규식이 토큰을 빠뜨리면 `got` 자체가 준다).
    """
    for line in out.splitlines():
        m = _KIND_LINE.search(line)
        if not m:
            continue
        got = {k: int(v) for k, v in re.findall(r"([a-z_]+)\s+(\d+)", m.group(1))}
        if not got:
            continue
        total = sum(got.values())
        return {"total": total, "counts": got, "sum": total}
    return None


def kind_points(counts: dict, table: dict):
    """부류 셈 → 점수 합. **모르는 부류가 있으면 그 칸의 점수를 내지 않는다.**"""
    bad, pts = [], 0.0
    for k, n in counts.items():
        if k not in table:
            bad.append("부류 «%s» 가 눈금 표에 없다 — 모르는 부류를 0 으로도 1 로도 "
                       "세지 않는다 (다섯 밖의 이름은 대장이 먼저 고칠 자리다)" % k)
            continue
        pts += table[k] * n
    return pts, bad


# ── 칸 — 세 수는 전부 「칸의 합」이다. 칸 하나를 못 재면 **그 칸만** 회색이다 ──

def cell(name: str, weight: float, num=None, den=None, why: str = "",
         source: str = "") -> dict:
    """한 칸. `num` 이 `None` 이면 **회색**이다 — 0 이 아니다.

    `den` 은 **그 칸의 분모**이고 언제나 값과 같은 줄에 실린다. 분모를 숨기면
    「수가 내려갔다」와 「분모가 늘었다」가 구별되지 않는다.
    """
    val = None if (num is None or not den) else num / den
    return {"name": name, "weight": weight, "num": num, "den": den,
            "value": val, "why": why, "source": source,
            "measured": val is not None}


def aa_score(cells: list) -> dict:
    """칸 목록 → 하한 · 상한 · **측정치**(회색을 분모에서 뺀 수).

    ★ 세 수를 한 수로 내지 않는 이유가 여기 있다. 하한과 상한이 벌어진 폭이
      **우리가 모르는 만큼**이고, 그 폭은 증거 한 건으로만 좁혀진다.
    """
    w_all = sum(c["weight"] for c in cells)
    w_meas = sum(c["weight"] for c in cells if c["measured"])
    got = sum(c["weight"] * c["value"] for c in cells if c["measured"])
    grey = [c for c in cells if not c["measured"]]
    return {
        "cells": cells, "w_all": w_all, "w_measured": w_meas, "got": got,
        "lower": got / w_all * 100.0 if w_all else None,
        "upper": (got + (w_all - w_meas)) / w_all * 100.0 if w_all else None,
        #: **측정치** — 잰 칸만으로 낸 수. 「지금 아는 것 안에서는 이렇다」이고,
        #: 분모가 `w_measured` 라는 것을 머리글이 반드시 함께 말해야 한다.
        "measured_pct": got / w_meas * 100.0 if w_meas else None,
        "grey": grey,
        "n_measured": len(cells) - len(grey), "n_cells": len(cells),
    }


def aa_fmt(sc: dict) -> str:
    """한 수 · 잰 칸 · 분모 · 하한 · 상한을 **한 줄로**."""
    if sc["measured_pct"] is None:
        return "**회색 — 잰 칸 0/%d.** 분모가 0인 초록은 초록이 아니다" % sc["n_cells"]
    return ("**%.1f** [잰 칸 %d/%d · 분모 %.2f/%.2f] · 하한 %.1f(회색을 0으로) · "
            "상한 %.1f(회색을 1로)"
            % (sc["measured_pct"], sc["n_measured"], sc["n_cells"],
               sc["w_measured"], sc["w_all"], sc["lower"], sc["upper"]))


#: CR 8칸의 격자 — 값은 {0, 0.5, 1} 뿐이다. 그래서 **합은 0.5의 배수**이고
#: 백분율은 `k/16` 위에만 선다(6.25% 눈금). ★ 세종 §0 이 적은 「8칸 중 2.2」는
#: 그 격자 **밖**이다 — 이 파일의 출생 표본 ①(「38 은 이 셈법이 낼 수 있는 수가
#: 아니다」)이 **그대로 한 번 더 나온 것**이고, 그래서 그 표본이 아직 도구다.
AA_GRID = (0.0, 0.5, 1.0)


def aa_on_grid(total: float) -> bool:
    """합이 0.5 의 배수인가. 아니면 그 수는 **눈대중이 한 번 더 나온 것**이다."""
    return abs(total * 2 - round(total * 2)) < 1e-9


#: CR 8칸의 **이름**. 세종 지시서(WO §2)가 못박은 여덟이다.
#: ⚠ 값은 여기 없다 — 값을 코드에 적는 순간 정본이 움직여도 이 줄이 거짓말한다.
#:   값은 `AA_REVIEW_DOC` 의 **CR 8칸 표**에서 읽는다. 그 표가 없으면 **회색**이다.
AA_CR8_NAMES = ("가격 숫자 4", "계량 씨앗 0", "실카메라 ≥1", "공개 주소",
                "웹푸시 도달", "SLA v1.0", "채널 계약서", "계약 11조")


#: CR8 한 칸의 값을 **말로** 적은 모양. 「반」만 0.5 이고 나머지는 끝났거나 아니다.
#: ⚠ `CR8_VALUE`(이 파일 위쪽 · §1 파서의 것)와 **같은 눈금**이다 — 두 벌을 두지
#:   않으려고 그 표를 그대로 가져다 쓴다(D-369).
_CR8_WORD = re.compile(r"\*{0,2}(없다|아니다|반|있다|끝났다|됐다)\*{0,2}")
#: `… — 값 0` 처럼 **수를 따로 적은** 칸. 말보다 이 수가 먼저다(더 좁다).
_CR8_NUM_IN_CELL = re.compile(r"값\s*(0\.5|0|1(?:\.0)?)\b")
#: 칸 하나가 통째로 수인 모양 — WO §4-1 의 `| CR1 | 가격 숫자 4 | 0 | 근거 |`.
_CR8_BARE_NUM = re.compile(r"^(0|0\.5|1|1\.0)$")


def _cr8_cell_value(cells: list) -> tuple:
    """행의 칸들에서 **값 하나**를 뽑는다 → `(값 또는 None, 읽은 글자)`.

    ★ 순서가 곧 규칙이다. 넓은 그물을 먼저 던지면 이름 칸의 「1」을 값으로 읽는다:
      ① `값 N` 이라고 **수를 따로 적은** 칸      (가장 좁다)
      ② 칸이 **통째로** 0 · 0.5 · 1 인 것
      ③ 「없다 · 반 · 있다」처럼 **말로** 적은 칸
    못 읽으면 `None` — **0 이 아니다.** 격자 밖의 값은 회색이고, 회색은 0 이 아니다.
    """
    for c in cells:
        m = _CR8_NUM_IN_CELL.search(c)
        if m:
            return float(m.group(1)), c
    for c in cells:
        if _CR8_BARE_NUM.match(c):
            return float(c), c
    for c in cells:
        m = _CR8_WORD.fullmatch(c.strip())
        if m:
            return CR8_VALUE.get(m.group(1)), c
    return None, (cells[0] if cells else "")


def parse_aa_cr8(text: str):
    """CR 8칸 표를 읽는다 — **두 가지 모양을 다 읽는다.**

    ① WO-04 §4-1 (세종 정본)   `| CR1 | 가격 숫자 4 | 0 | 근거 |`
    ② N 전사 `GX-CR_8칸_v1.0`  `| ① | CR1 가격 숫자 4 | 술어 | **없다** — 값 0 | 근거 |`

    ★★ [실측 2026-09-21 · 턴 AB] 처음에는 ①만 읽었다. 그런데 N 이 옮겨 적은 표는
      **CR 표식이 첫 칸이 아니라 둘째 칸**에 있고 값은 「**없다** — 값 0」처럼 말과
      수가 같이 적혀 있다. ①만 읽는 그물로는 N 의 파일에서 **0행**이 나오고,
      그 0 은 「표가 없다」로 읽힌다 — **「없다」가 아니라 「못 찾았다」**다.
      이 파일이 오늘 두 번째로 밟은 자리다(`verify_spec_coverage` 의 `DSM-01`).
    ★ 그래서 **표식을 앞 두 칸에서 찾고**, 값은 `_cr8_cell_value` 가 좁은 그물부터
      던져 뽑는다. 둘 다 읽히면 **두 벌을 대조**할 수 있다(`aa_cr8_chain`).

    ⚠ 표가 없으면 회색이 나오는 것이 **옳다** — 그 회색이 표를 불러온다
      (턴 AA 에 그랬고, 그래서 세종이 §4-1 에 여덟 줄을 적었다).
    """
    #: ★★ [실측 2026-09-21 · 턴 AB] **한 문서에 CR 표가 둘 있을 수 있다.**
    #:   N 의 전사본은 §1 에 여덟 줄을 적고 §4 에 **대조표**로 여덟 줄을 한 번 더
    #:   적는다. 문서 전체를 한 줄기로 훑으면 **16행**이 나오고, 이 도구는 그것을
    #:   「행이 여덟이 아니다」라는 **거짓 빨강**으로 냈다 — 표는 멀쩡한데.
    #:   ⇒ **표 단위로 끊어서** 모으고, **여덟 행짜리 첫 표**를 쓴다.
    #:     (표가 아닌 줄이 하나라도 끼면 다른 표다 — 마크다운의 성질 그대로다.)
    tables: list[list] = [[]]
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if tables[-1]:
                tables.append([])
            continue
        tables[-1].append(s)
    blocks = [r for r in (_parse_aa_cr8_rows(tbl) for tbl in tables) if r]
    if not blocks:
        return [], ("CR 8칸 표가 이 본문에 **없다** — 합만 있는 수는 다시 셀 수 없다. "
                    "`| CR1 | 가격 숫자 4 | 0 | 근거 |` 여덟 줄을 적으면 "
                    "이 산출기가 센다")
    for rows in blocks:
        if len(rows) == 8:
            return rows, ""
    rows = max(blocks, key=len)
    return rows, ("CR 8칸 표의 행이 %d 이다 — 분모가 흔들리면 아래 수는 무의미하다"
                  % len(rows))


def _parse_aa_cr8_rows(lines: list) -> list:
    """표 한 덩이에서 `CR1`~`CR8` 행만 뽑는다 (두 모양 다)."""
    rows = []
    for s in lines:
        c = _cells(s)
        if len(c) < 3:
            continue
        no = None
        idx = 0
        for k in (0, 1):
            if k < len(c):
                m = re.match(r"^CR\s*([1-8])\b", _plain(c[k]))
                if m:
                    no, idx = int(m.group(1)), k
                    break
        if no is None:
            continue
        #: 이름 — 표식 칸에 이름이 붙어 있으면(`CR1 가격 숫자 4`) 그것을 떼어 쓰고,
        #: 아니면 다음 칸이 이름이다(`| CR1 | 가격 숫자 4 | …`).
        head = _plain(c[idx])
        tail = re.sub(r"^CR\s*[1-8]\s*", "", head).strip()
        name = tail or (_plain(c[idx + 1]) if idx + 1 < len(c) else "")
        #: 값은 **표식 칸과 이름 칸을 뺀 나머지**에서 찾는다 — 이름 안의 숫자를
        #: 값으로 읽지 않게(「CR1 가격 숫자 **4**」의 4 가 그 자리다).
        rest = [_plain(x) for j, x in enumerate(c)
                if j > idx and not (tail == "" and j == idx + 1)]
        val, raw = _cr8_cell_value(rest)
        if val is not None and val not in AA_GRID:
            val = None
        rows.append({"no": no, "name": name, "raw": raw, "value": val})
    return rows


#: ★★ [턴 AB · 실측] CR 8칸 표는 여덟 행 아래에 **제 합을 스스로 적는다**:
#:     `| **합** | | **2.0/8 = 25 %** | 0.5 배수 격자 안 |`
#:   그 합이 **여덟 행을 더한 수와 갈릴 수 있다.** 갈리면 읽는 사람은 **합을 읽는다**
#:   (표 아래 굵은 글씨가 더 눈에 띈다) — 그리고 그 수는 다시 셀 수 없는 수다.
#:   행이 정본이다. 합은 **행에서 나와야** 하고, 안 나오면 빨강이다.
_CR8_SUM = re.compile(r"\|\s*\*{0,2}합\*{0,2}\s*\|[^|]*\|\s*\*{0,2}"
                      r"([\d.]+)\s*/\s*8")


def parse_aa_cr8_sum(text: str) -> float | None:
    """표가 **스스로 적은 합**을 집는다 — 행을 더한 수와 대조하려고."""
    m = _CR8_SUM.search(text or "")
    return float(m.group(1)) if m else None


def aa_cr8_sources() -> list[tuple[str, str]]:
    """CR 8칸 표를 **가진 파일들**을 연다 — 정본(WO §4-1) → 전사(N) → 옛 자리 순.

    ★ 손으로 2.0 을 적지 않는다. 이 함수가 하는 일은 **파일을 여는 것**뿐이고,
      값은 `parse_aa_cr8` 이 그 본문에서 읽는다. 파일이 하나도 없으면 빈 목록이고,
      그때 CR 은 **회색 8칸**이다 — 그 회색이 표를 불러온다(턴 AA 가 그랬다).
    """
    out: list[tuple[str, str]] = []
    wo_dir = ROOT / "docs" / "workorders"
    for p in sorted(wo_dir.glob(AA_WO04_GLOB)) if wo_dir.is_dir() else []:
        out.append(("WO-04 §4-1(세종 정본 · P-232) `%s`" % p.name,
                    p.read_text(encoding="utf-8", errors="replace")))
    if AA_CR8_DOC.is_file():
        out.append(("N 전사 `%s`" % AA_CR8_DOC.name,
                    AA_CR8_DOC.read_text(encoding="utf-8", errors="replace")))
    if AA_REVIEW_DOC.is_file():
        out.append(("옛 자리 `%s`" % AA_REVIEW_DOC.name,
                    AA_REVIEW_DOC.read_text(encoding="utf-8", errors="replace")))
    return out


def aa_cr8_chain(sources: list[tuple[str, str]]):
    """여러 출처의 CR 8칸 표를 **다 읽고 대조한다.**

    돌려주는 것: `(rows, why, label, notes, reds)`
      · `rows`  — 정본(첫 출처 중 표를 가진 것)의 여덟 행. 없으면 `[]`
      · `why`   — 회색/빨강 사유 한 줄 (없으면 "")
      · `label` — 그 수를 **어디서 읽었는지**. 판정문이 이 이름을 그대로 낸다
      · `notes` — 소리 내어 적을 것(전사가 아직 없다 등). 회색이 아니다
      · `reds`  — 표가 둘 이상인데 **값이 갈렸다**. 빨강이다

    ★ 「N 의 파일이 없으면 회색」이 아니라 **「표가 어디에도 없으면 회색」**이다.
      기계가 저장소의 파일에서 읽은 수는 손으로 적은 수가 아니다 — P-234 가 막는
      것은 「손으로 적기」이지 「가까운 파일에서 읽기」가 아니다. 다만 전사가 아직
      없다는 **사실은 적는다**(안 적으면 다음 사람이 「N 이 옮겼다」로 읽는다).
    """
    notes: list[str] = []
    reds: list[str] = []
    found: list[tuple[str, list, str]] = []
    for label, text in sources:
        rows, why = parse_aa_cr8(text)
        if rows and len(rows) == 8:
            found.append((label, rows, text))
        elif rows:
            #: ★ 행이 여덟이 아닌 표는 **쓰지 않는다.** 분모가 흔들리는 표에서 낸 수는
            #:   수가 아니다 — 그러나 **조용히 건너뛰지도 않는다**(빨강으로 말한다).
            reds.append("CR: %s (%s)" % (why, label))
    if not AA_CR8_DOC.is_file():
        notes.append("CR: N 전사 `%s` 가 **아직 없다** — 지금 수는 WO-04 §4-1 "
                     "(세종 정본 · P-232)에서 **기계가 읽은** 것이다. N 이 옮겨 "
                     "적으면 두 벌이 되고, 그때부터 이 산출기가 **둘을 대조**한다"
                     % AA_CR8_DOC.name)
    if not found:
        return [], ("CR 8칸 표가 **어디에도 없다** — 연 파일 %d개(%s). 합만 있는 수는 "
                    "다시 셀 수 없다. `| CR1 | 가격 숫자 4 | 0 | 근거 |` 여덟 줄을 "
                    "적으면 이 산출기가 센다"
                    % (len(sources), " · ".join(l for l, _ in sources) or "없음")
                    ), "", notes, reds
    label, rows, src_text = found[0]
    #: ★★ **표가 제 합을 적었으면 행과 대 본다.** 갈리면 빨강 — 읽는 사람은 굵게
    #:   적힌 합을 읽고, 그 합은 다시 셀 수 없는 수다. **행이 정본이다.**
    said = parse_aa_cr8_sum(src_text)
    if said is not None:
        got = sum(r["value"] for r in rows if r["value"] is not None)
        n_ok = sum(1 for r in rows if r["value"] is not None)
        if n_ok == 8 and abs(said - got) > 1e-9:
            reds.append("★★ **표의 합이 제 행과 갈렸다** — %s 가 적은 합 **%.1f/8**, "
                        "여덟 행을 더하면 **%.1f/8**(%+.1f). **행이 정본이다** — "
                        "합은 행에서 나와야 하고, 안 나오는 합은 다시 셀 수 없는 "
                        "수다(P-93). CR 은 %.1f%% 가 아니라 **%.1f%%** 다"
                        % (label, said, got, got - said,
                           said / 8 * 100.0, got / 8 * 100.0))
    #: ★ 둘 이상이면 **대조한다.** 갈리면 빨강 — 조용히 첫 것을 고르지 않는다.
    for other_label, other, _ in found[1:]:
        #: ⚠⚠ [실측 2026-09-21 · 턴 AB] 처음에는 **글자(`raw`)를 댔다.** 그랬더니
        #:   여덟 칸이 **전부 빨강**으로 났다 — WO 는 `0` 이라 적고 N 은
        #:   `**없다** — 값 0` 이라 적었을 뿐 **두 수는 같았다.**
        #:   ★ **갈렸다는 것은 값이 다르다는 뜻이지 글자가 다르다는 뜻이 아니다.**
        #:     같은 수를 다르게 적은 것을 빨강으로 내면, 그 빨강은 사람이 끄게 된다
        #:     (꺼진 게이트는 없는 게이트보다 나쁘다 · D-311).
        for a, b in zip(rows, other):
            if a["value"] != b["value"]:
                reds.append("★ **CR 표가 갈렸다** — CR%d(%s): 정본 %s=%s · %s=%s "
                            "(글자로는 %r ↔ %r). 같은 칸에서 두 수가 난다 (D-369)"
                            % (a["no"], a["name"], label, _num(a["value"]),
                               other_label, _num(b["value"]),
                               a["raw"][:24], b["raw"][:24]))
        if len(rows) != len(other):
            reds.append("★ **CR 표의 행 수가 갈렸다** — %s %d행 ↔ %s %d행"
                        % (label, len(rows), other_label, len(other)))
    #: ★ 「합이 갈렸다」는 표 **안**의 일이고 「두 벌이 갈렸다」는 표 **사이**의 일이다.
    #:   둘을 한 깃발로 세면, 합이 어긋난 날 「두 벌은 같다」는 초록이 조용히 사라진다.
    if len(found) > 1 and not any("두 수가 난다" in r for r in reds):
        notes.append("CR: 표 %d벌(%s)을 **다 읽고 대조했다 — 같다**. 두 벌을 두지 "
                     "않는다(D-369)" % (len(found), " · ".join(l for l, _, _t in found)))
    return rows, "", label, notes, reds


def parse_aa_stated(text: str) -> dict:
    """세종이 **적어 둔** 세 수를 집는다 — 다시 센 수와 대조하려고(CR 과 같은 자리)."""
    out = {}
    for key, pat in (("fc", r"Feature Completion\*{0,2}\s*\|\s*\*{0,2}(\d+(?:\.\d+)?)"),
                     ("pr", r"Production Readiness\*{0,2}\s*\|\s*\*{0,2}(\d+(?:\.\d+)?)"),
                     ("cr", r"Commercial Readiness\*{0,2}\s*\|\s*\*{0,2}(\d+(?:\.\d+)?)")):
        m = re.search(pat, text)
        if m:
            out[key] = float(m.group(1))
    m = re.search(r"8칸 중\s*(\d+(?:\.\d+)?)", text)
    if m:
        out["cr_sum"] = float(m.group(1))
    m = re.search(r"세 수 평균\s*\*{0,2}(\d+(?:\.\d+)?)", text)
    if m:
        out["fc_avg"] = float(m.group(1))
    return out


#: PR 의 뒤 세 칸이 **증거로 서는 자리**. 없으면 회색이다 — 0 이 아니다.
#: ⚠ 이름을 여기 적는 것은 「손 목록」이 아니다. 값을 적는 것이 손 목록이고,
#:   여기 있는 것은 **어디를 보면 되는지**다. 그 자리가 비었다는 사실이 곧 측정이다.
AA_PR_EVIDENCE = (
    ("재부팅 아침 N/10", 0.10, "docs/agent/evidence/OPS-20",
     "재부팅 뒤 열 가지가 스스로 섰는가 — **증거 0건 · 다섯 턴째**"),
    ("스테이징 걷기 6/6", 0.10, "docs/agent/evidence/OPS-21",
     "스테이징에서 여섯 역할이 걸었는가 — 스테이징 자체가 **0**(파 4 전제 · 10-05)"),
    ("창 2a·2b 집행", 0.10, "docs/agent/evidence/P-220/window_2ab.md",
     "창 2a(09-23 12:00 · C0 질문) · 창 2b(VAPID·SMTP·시험 DB) — **미집행**"),
)


def aa_evidence(rel: str):
    """증거 자리가 **실재하는가**. 없으면 그 칸은 회색이다 — 0 이 아니다."""
    p = ROOT / rel
    if p.exists():
        try:
            n = len([x for x in p.iterdir()]) if p.is_dir() else 1
        except OSError:
            n = 0
        if n == 0:
            return False, "증거 자리 `%s` 는 있으나 **비어 있다**" % rel
        return True, _stamp(p)
    return False, "증거 자리 `%s` 가 **없다**" % rel


#: 영역 줄의 꼬리 — `… 절 16/20 =  80%  → 16.00   (래칫 1 · 규칙만 1 · 못 잼 4 · 게이트만 0)`
#: ★ 이 꼬리가 있어서 **영역별 kind 점수**를 다시 셀 수 있다.
#:   `closed = 절 수 − (래칫 + 규칙만 + 못 잼 + 게이트만)` — 대장이 P-211 로
#:   「부류 합 = 절 수」를 이미 보증했으므로 이 뺄셈은 안전하다.
_AREA_TAIL = re.compile(
    r"^\s*(\d)\s+.+?가중\s*(\d+)%\s+절\s*(\d+)/(\d+)\s*=.*?"
    r"\(래칫\s*(\d+)\s*·\s*규칙만\s*(\d+)\s*·\s*못 잼\s*(\d+)\s*·\s*게이트만\s*(\d+)\)")


def parse_ga_area_kinds(out: str) -> list:
    """영역마다 `{closed, ratchet, rule_only, gate_only, unmeasurable}` 을 되돌린다."""
    rows = []
    for line in out.splitlines():
        m = _AREA_TAIL.match(line)
        if not m:
            continue
        no, w, done, total, rat, rule, unm, gate = (int(x) for x in m.groups())
        closed = total - (rat + rule + unm + gate)
        rows.append({"no": no, "weight": w, "done": done, "total": total,
                     "kinds": {"closed": closed, "ratchet": rat,
                               "rule_only": rule, "unmeasurable": unm,
                               "gate_only": gate}})
    return rows


def area_kind_total(rows: list, table: dict):
    """영역 가중 합계를 **kind 로** 다시 센다 — P-216 의 「내려간 수」가 여기서 난다."""
    if not rows:
        return None, []
    bad, total = [], 0.0
    for a in rows:
        if any(v < 0 for v in a["kinds"].values()):
            bad.append("영역 %d: 부류 합이 절 수를 넘는다 — 대장이 먼저 고칠 자리다"
                       % a["no"])
            continue
        pts, b = kind_points(a["kinds"], table)
        bad += b
        total += a["weight"] * (pts / a["total"] if a["total"] else 0.0)
    return total, bad


def aa_report(ga_out: str = None, click=None, click_why: str = "",
              onboard_text: str = None, review_text: str = None) -> dict:
    """세종의 **세 수**를 낸다. 못 잰 칸은 **회색**이고, 회색은 분모에서 빠진다.

    인자를 주면 그것으로 센다(**자기시험이 이 문을 쓴다**) — 안 주면 실제로
    게이트를 부르고 문서를 읽는다. 시험용 갈래와 실제 갈래가 **같은 코드**를
    지나야 한다. 갈리면 시험은 시험이 아닌 것을 시험한다.
    """
    red: list = []
    grey: list = []
    note: list = []

    live = ga_out is None
    #: ★ 「인자로 받았는가」를 **덮기 전에** 기억한다 — 아래 CR 출처 사슬이 이것으로
    #:   갈린다(시험 본문이면 그것만 · 아니면 저장소의 파일 셋을 연다).
    cr_source_text_given = review_text is not None
    if live:
        ga_out, _rc = run_ga()
    if onboard_text is None:
        onboard_text = (ONBOARD_DOC.read_text(encoding="utf-8", errors="replace")
                        if ONBOARD_DOC.is_file() else "")
    if review_text is None:
        review_text = (AA_REVIEW_DOC.read_text(encoding="utf-8", errors="replace")
                       if AA_REVIEW_DOC.is_file() else "")

    table, table_why = aa_kind_score_table()
    if table_why.startswith("★"):
        red.append(table_why)
    elif table_why:
        note.append(table_why)

    areas, ga_total, _inhand = parse_ga_areas(ga_out or "")
    kind_rows = parse_ga_area_kinds(ga_out or "")
    roll = parse_ga_kinds(ga_out or "")
    #: ★ P-253 — 걷어낸 옛 5키 줄이 되살아났는지는 **회색이 아니라 빨강**이다.
    #:   `roll` 이 서든 안 서든(6키 줄이 있든 없든) 이 검사는 독립으로 돈다 —
    #:   옛 줄이 6키 줄과 **나란히** 되살아나도 잡아야 하기 때문이다.
    if old_5key_line_present(ga_out or ""):
        red.append("★ P-253 재발 — 걷어낸 옛 5키 줄(「초록」 부류 N절 — … "
                   "unmeasurable … gate_only, measured_red 없음)이 다시 나타났다. "
                   "「호환」이라는 이름으로 되살리지 않는다 — 6키 줄만 정본이다")

    # ── FC — 세 칸의 **단순 평균**이다. 세종이 셋에 같은 무게를 줬다 ────────
    fc_cells = []

    #: ① 48행 「누른 뒤」 — 그 게이트의 눈금은 {초록·빨강·**회색**} 셋이다.
    #:   회색을 0 으로 눌러 적으면 「못 잰 것」이 「못 한다」가 된다(D-301).
    #:   그래서 값은 초록/48 로 두되, **그 칸 자신의 상한**을 사유에 싣는다.
    if click and (click["green"] + click["red"]) == 0:
        #: ★★ **여기가 이 도구의 가장 미끄러운 자리다** [실측 2026-09-21 · 턴 AA].
        #:   그 게이트가 「**0/48** — 초록 0 · 빨강 0 · **회색 48**」을 낸다. 그 0 을
        #:   그대로 칸에 적으면 FC 가 0점 한 칸을 받고 **수가 내려간다** — 그런데
        #:   그것은 「우리가 못 한다」가 아니라 **「우리가 안 쟀다」**다.
        #:   게이트가 **한 행도 판정하지 않았으면 그 칸은 회색이다.** 0 이 아니다.
        #:   (`--measure` 없이 부르므로 증거가 낡으면 언제나 이 갈래다. 이 도구는
        #:    역할 계정 넷의 자리를 뺏지 않는다 — 그 대가가 이 회색이다.)
        grey.append("FC①: 48행 「누른 뒤」 — 그 게이트가 **한 행도 판정하지 않았다** "
                    "(초록 0 · 빨강 0 · 회색 48). **0 이 아니라 못 쟀다.** "
                    "증거 `docs/agent/evidence/P-118/click_completes.json` 이 "
                    "없거나 낡았다 — `--measure` 로 한 번 누르면 이 칸이 선다")
        fc_cells.append(cell("48행 「누른 뒤」 초록", 1 / 3,
                             why="게이트가 한 행도 판정하지 않았다 (회색 %d/%d)"
                                 % (click["grey"], ONBOARD_ROWS)))
    elif click:
        up = (click["green"] + click["grey"]) / ONBOARD_ROWS * 100.0
        fc_cells.append(cell(
            "48행 「누른 뒤」 초록", 1 / 3, click["green"], ONBOARD_ROWS,
            why=("게이트 자신의 회색 %d행 — 이 칸의 상한은 %.1f 이다 "
                 "(회색을 초록으로 보면)" % (click["grey"], up)),
            source="scripts/verify_click_completes.py 를 **불렀다**"))
    else:
        grey.append("FC①: 48행 「누른 뒤」를 못 쟀다 — %s" % (click_why or "사유 없음"))
        fc_cells.append(cell("48행 「누른 뒤」 초록", 1 / 3,
                             why=click_why or "게이트를 못 불렀다"))

    #: ② 온보딩 48행
    ob = parse_onboarding(onboard_text) if onboard_text else None
    if ob and ob["consistent"]:
        fc_cells.append(cell("온보딩 48행 점수", 1 / 3, ob["sum"], ob["n"],
                             source="docs/agent/onboarding_48.md 의 **마지막** 재측"))
    elif ob:
        red.append("FC②: 온보딩 문서 안에서 분자와 백분율이 갈린다 "
                   "(%.1f/%d = %.1f%% 인데 %.1f%% 라 적혀 있다)"
                   % (ob["sum"], ob["n"], ob["calc"], ob["pct"]))
        fc_cells.append(cell("온보딩 48행 점수", 1 / 3,
                             why="문서 안에서 분자와 백분율이 갈렸다"))
    else:
        grey.append("FC②: `onboarding_48.md` 에서 `N / 48 = P%` 를 못 읽었다")
        fc_cells.append(cell("온보딩 48행 점수", 1 / 3, why="문서를 못 읽었다"))

    #: ③ 계약 39절 도달 — 대장 영역 ①이 그대로 인용하는 그 수다(D-345).
    #: ★★ [실측 2026-09-21 · 턴 AB] **`--static` 이 이 칸에 거짓 0 을 만든다.**
    #:   로그인 창이 없는 차선은 `verify_ga_readiness` 를 `--static` 으로 부른다
    #:   (그래야 로그인이 0 이다 · D-510). 그런데 `--static` 은 **게이트를 한 벌도
    #:   안 부르고**, 영역 ①의 도달 수는 **게이트가 세는 수**다. 그래서 꼬리에
    #:   `절 0/39` 가 찍히고, 이 도구가 첫 판에서 그 **0 을 그대로 칸에 적었다** —
    #:   FC 가 52.0 → 30.2 로 떨어졌다. 그것은 「우리가 못 한다」가 아니라
    #:   **「우리가 안 쟀다」**다(이 파일 FC① 의 그 자리가 한 번 더 나왔다).
    #:   ⇒ 정적 갈래에서는 이 칸을 **회색**으로 둔다. 0 이 아니다.
    static_run = "정적 갈래" in (ga_out or "") or "--static" in (ga_out or "")
    a1 = [a for a in areas if a["no"] == 1]
    if a1 and static_run and not a1[0]["done"]:
        grey.append("FC③: 계약 39절 도달 — **정적 갈래(`--static`)라 게이트를 한 벌도 "
                    "안 불렀다.** 영역 ①의 도달 수는 **게이트가 세는 수**이므로 "
                    "꼬리의 `0/39` 는 **0 이 아니라 못 잰 것**이다 (D-301). "
                    "창을 가진 사람이 게이트를 부르면 이 칸이 선다")
        fc_cells.append(cell("계약 39절 도달", 1 / 3,
                             why="정적 갈래 — 영역 ① 게이트를 안 불렀다"))
    elif a1:
        fc_cells.append(cell("계약 39절 도달", 1 / 3, a1[0]["done"], a1[0]["total"],
                             source="verify_ga_readiness 영역 ①(게이트가 센 도달 수)"))
    else:
        grey.append("FC③: 대장 영역 ①을 못 읽었다 — `verify_ga_readiness` 를 못 불렀다")
        fc_cells.append(cell("계약 39절 도달", 1 / 3, why="영역 ①을 못 읽었다"))

    fc = aa_score(fc_cells)

    # ── PR — 앞 칸 0.7 은 **대장의 kind 점수**, 뒤 세 칸 0.3 은 **증거 자리** ──
    pr_cells = []
    pr_closed_line = ""
    if roll:
        #: ★ P-253 — **눈금표(`table`)는 아직 다섯 칸이다** — 손대지 않는다
        #:   (부류 셈·점수 식은 이 커밋에서 안 건드린다). 6키 줄은 `measured_red`
        #:   를 따로 실어 오므로, 점수 계산 **직전에만** `unmeasurable` 에 접는다 —
        #:   둘의 점수가 이미 같기 때문에(0.0 · KIND_POINTS) 접어도 총점은 그대로다.
        #:   `roll["counts"]` 자신은 접지 않는다 — 아래 `pr_closed_line` 이
        #:   「재서 빨강」을 **따로** 보이는 것이 이번에 걷은 은닉을 되풀이하지
        #:   않는 자리다.
        score_counts = dict(roll["counts"])
        score_counts["unmeasurable"] = (score_counts.get("unmeasurable", 0)
                                        + score_counts.pop("measured_red", 0))
        pts, bad = kind_points(score_counts, table)
        red += bad
        if roll["sum"] != roll["total"]:
            red.append("PR①: 부류 합 %d 이 절 수 %d 과 다르다 — 안 세어진 절은 "
                       "「닫혔다」로 읽힌다 (P-211)" % (roll["sum"], roll["total"]))
        pr_cells.append(cell("대장 kind 점수", 0.70, pts, roll["total"],
                             why=" · ".join(KIND_CAVEAT[k] for k in ("ratchet",
                                                                     "unmeasurable")),
                             source="verify_ga_readiness 의 부류 줄(P-211 검산을 통과한 셈)"))
        closed = roll["counts"].get("closed", 0)
        pr_closed_line = ("닫힌 절 **%d/%d** = %.1f · kind 점수 **%.1f/%d** = %.1f "
                          "(래칫 %d · 규칙만 %d · 게이트만 %d · 못 잼 %d · 재서 빨강 %d)"
                          % (closed, roll["total"], closed / roll["total"] * 100.0,
                             pts, roll["total"], pts / roll["total"] * 100.0,
                             roll["counts"].get("ratchet", 0),
                             roll["counts"].get("rule_only", 0),
                             roll["counts"].get("gate_only", 0),
                             roll["counts"].get("unmeasurable", 0),
                             roll["counts"].get("measured_red", 0)))
    else:
        grey.append("PR①: 대장의 부류 줄을 못 읽었다 — `verify_ga_readiness` 를 못 불렀다")
        pr_cells.append(cell("대장 kind 점수", 0.70, why="부류 줄을 못 읽었다"))

    for name, w, rel, what in AA_PR_EVIDENCE:
        ok, why = aa_evidence(rel)
        if ok:
            #: 증거 자리가 섰다 — 그러나 **몇 건인지는 그 증거가 스스로 말해야 한다.**
            #: 자리만 보고 1.0 을 주면 빈 폴더가 만점이 된다. 그래서 여전히 회색이다.
            grey.append("PR: 「%s」 증거 자리는 섰다(%s) — 그러나 **그 안의 수를 읽는 "
                        "술어가 아직 없다.** 자리만 보고 점수를 주지 않는다" % (name, why))
            pr_cells.append(cell(name, w, why="자리는 있으나 수를 읽는 술어가 없다"))
        else:
            grey.append("PR: 「%s」 — %s · %s" % (name, why, what))
            pr_cells.append(cell(name, w, why=why + " · " + what))

    pr = aa_score(pr_cells)

    # ── CR — 8칸. 표가 없으면 **회색 8칸**이다 (그 회색이 표를 불러온다) ────
    #: ★ 인자로 본문을 받았으면(자기시험) **그것만** 본다 — 시험이 저장소의 실물을
    #:   읽어 버리면 「표가 없으면 회색」 갈래를 영영 못 시험한다.
    cr_sources = ([(AA_REVIEW_DOC.name, review_text)] if cr_source_text_given
                  else aa_cr8_sources())
    cr8, cr_why, cr_label, cr_notes, cr_reds = aa_cr8_chain(cr_sources)
    note += cr_notes
    red += cr_reds
    cr_cells = []
    if not cr8:
        grey.append("CR: %s" % cr_why)
        for nm in AA_CR8_NAMES:
            cr_cells.append(cell(nm, 1 / 8, why="CR 8칸 표가 없다"))
    else:
        for r in cr8:
            if r["value"] is None:
                grey.append("CR%d(%s): 값 칸 %r 이 격자 {0, 0.5, 1} 밖이다"
                            % (r["no"], r["name"], r["raw"]))
                cr_cells.append(cell(r["name"], 1 / 8, why="격자 밖의 값"))
            else:
                cr_cells.append(cell(r["name"], 1 / 8, r["value"], 1.0,
                                     source=cr_label))
    cr = aa_score(cr_cells)
    #: ★ 읽은 여덟의 **합도 격자 위에 있어야 한다.** 「27」·「2.2」가 폐기된 이유가
    #:   그것이고(P-232), 폐기된 수가 다시 표로 들어오면 여기서 빨강이 난다.
    if cr8 and all(r["value"] is not None for r in cr8):
        _sum = sum(r["value"] for r in cr8)
        if not aa_on_grid(_sum):
            red.append("★ **격자 밖** — 표에서 읽은 여덟의 합 %.2f 가 0.5의 배수가 "
                       "아니다 (%s)" % (_sum, cr_label))
        else:
            note.append("CR: 표에서 읽은 여덟의 합 **%.1f/8 = %.1f%%** — 격자 안이다 "
                        "(%s). 「27」·「2.2」는 폐기된 수다 (P-232)"
                        % (_sum, _sum / 8 * 100.0, cr_label))

    # ── 적어 둔 수와 다시 센 수를 **대조한다** (인용은 실측이 아니다 · P-93) ──
    stated = parse_aa_stated(review_text or "")
    if "cr_sum" in stated and not aa_on_grid(stated["cr_sum"]):
        red.append("★ **격자 밖** — 문서가 적은 CR 합 %.2f 는 이 셈법이 낼 수 있는 "
                   "수가 아니다. 8칸이 {0, 0.5, 1} 이면 합은 **0.5의 배수**뿐이다. "
                   "격자 밖의 수는 **눈대중이 한 번 더 나온 것**이다 "
                   "(이 파일 출생 표본 ①이 그대로 한 번 더 나왔다)"
                   % stated["cr_sum"])

    # ── ★ 셈법 ① — 영역 ⑧ 비율을 **상태로 볼 것인가 부류로 볼 것인가** ─────
    #   [N → Q 쪽지 · 턴 AA ⑤] P-215 로 `LAW-04` 가 내려가며 둘이 **갈렸다**:
    #     상태(구현 5/10) 0.500 · 부류(kind 4.00/10) 0.400
    #   ★★ **Q 의 판단: 이번 턴에는 옮기지 않는다. 그러나 갈렸다고 소리 내어 적는다.**
    #     사유 둘 —
    #       ① CR 셈법 규칙 2 는 **문서**(`GX-CR …_v0.1.md`)가 정한다. 문서를 안 고치고
    #          코드만 0.400 으로 옮기면 **문서와 코드가 갈리고**, 갈린 것을 아무도
    #          모른다 — 이 파일이 막으려고 있는 바로 그 병이다(P-93 · D-227).
    #          문서를 고치는 것은 세종·조율자의 자리다(P-203).
    #       ② 그렇다고 조용히 0.500 을 쓰면 **P-216 의 한 줄과 어긋난 채로** 산다.
    #     그래서 **옮기지 않고 판정문에 두 수를 나란히 낸다.** 회색이다 — 빨강이 아니다
    #     («제품이 무너졌다»가 아니라 «정할 사람이 아직 안 정했다»이므로).
    #: ⚠ [실측 2026-09-21] 첫 그물은 `상태[^\d]*([\d.]+)` 였고 **「구현 5/10」의 5 를
    #:   집었다** — N 이 낸 줄은 `상태(구현 5/10) **0.500** · 부류(kind 4.00/10) **0.400**`
    #:   이라 괄호 안의 수가 먼저 온다. 집을 것은 **굵게 적힌 비율**이다.
    m8 = re.search(r"영역 ⑧ 비율[^\n]*?상태[^·\n]*?\*\*([\d.]+)\*\*"
                   r"[^\n]*?부류[^·\n]*?\*\*([\d.]+)\*\*", ga_out or "")
    if m8 and abs(float(m8.group(1)) - float(m8.group(2))) > 1e-9:
        grey.append("셈법 ①: 영역 ⑧ 비율이 **갈렸다** — 상태 %s · 부류(kind) %s. "
                    "이 산출기는 **상태 %s 를 쓴다**(CR 셈법 문서 규칙 2 가 그 자리다). "
                    "부류로 옮기려면 **문서를 먼저 고친다** — 코드만 옮기면 문서와 "
                    "갈리고, 갈린 것을 아무도 모른다 (세종·조율자의 자리 · P-203)"
                    % (m8.group(1), m8.group(2), m8.group(1)))

    # ── P-216 — **내려간 수**. 영역 가중 합계를 kind 로 다시 센다 ───────────
    kind_total, bad = area_kind_total(kind_rows, table)
    red += bad
    drop = None
    if kind_total is not None and ga_total is not None:
        drop = {"status": ga_total, "kind": kind_total,
                "delta": kind_total - ga_total}

    return {"fc": fc, "pr": pr, "cr": cr, "stated": stated, "drop": drop,
            "roll": roll, "table": table, "red": red, "grey": grey,
            "note": note, "pr_closed_line": pr_closed_line,
            "click": click, "onboard": ob, "areas": areas}


def aa_measured_line(rep: dict) -> str:
    """`MEASURED=` 한 줄 — **분모는 머리글 시점에 지금 센 것**이다.

    ★ 거짓 분모를 적지 않는다. 「8칸」이라 적고 8칸을 안 봤으면 그 줄이 거짓말이다.
      그래서 이 줄은 `aa_report()` 가 **실제로 돌고 난 뒤** 그 결과에서 만들어진다.
    """
    #: ⚠⚠ [실측 2026-09-21 · 턴 AA] 처음에는 칸마다 「분모 0.67/1.00」처럼 **소수**를
    #:   적었다. 그랬더니 `_gate_header.judge_measured` 의 `분모\s*([0-9][0-9,]*)` 가
    #:   「분모 **0**.67」의 **`0` 만 집어** 「분모가 0이다 — 0건 검사는 통과가 아니다」
    #:   라는 **빨강**을 냈다. 내 게이트가 내 머리글에 걸린 것이다.
    #:   ★ 고침: **맨 앞의 `분모` 는 언제나 「칸 수」(정수)** 다. 몫(가중)은 `몫` 이라
    #:     부른다 — 같은 낱말을 두 뜻으로 쓰면 읽는 쪽이 둘 중 하나를 고르게 된다.
    def one(key, label):
        sc = rep[key]
        return "%s 잰 칸 **%d/%d**(몫 %.2f/%.2f)" % (
            label, sc["n_measured"], sc["n_cells"], sc["w_measured"], sc["w_all"])
    n_cells = sum(rep[k]["n_cells"] for k in ("fc", "pr", "cr"))
    n_meas = sum(rep[k]["n_measured"] for k in ("fc", "pr", "cr"))
    return ("세종 세 수(FC·PR·CR)를 **칸마다** 잰다 — **분모 %d칸**(FC 3 · PR 4 · CR 8) "
            "중 **잰 칸 %d**: %s · %s · %s. "
            "**못 잰 칸은 0 이 아니라 회색**이고 회색은 위 몫에서 빠진다 — 그래서 "
            "하한(회색을 0으로)과 상한(회색을 1로)을 함께 낸다 (D-301 · P-204)"
            % (n_cells, n_meas,
               one("fc", "FC"), one("pr", "PR"), one("cr", "CR")))


def aa_print(rep: dict) -> int:
    """세 수를 찍는다. ★ **내려간 수를 첫 줄에 적고 사유를 붙인다.**"""
    d = rep["drop"]
    if d and abs(d["delta"]) < 0.05:
        #: ★★ [실측 2026-09-21 18:2x] **N 쪽이 이미 kind 로 센다.** 그러면 이 줄의
        #:   「전」과 「후」가 같은 수가 되고 `-0.0` 이 찍힌다 — 그것을 「안 내려갔다」로
        #:   읽으면 정반대다. **내려간 수는 이미 N 의 합계 안에 들어 있다.**
        #:   그래서 이 갈래는 **대조**라고 말한다. 수가 같다는 것이 여기서는 초록이다.
        print("%s ★★ **상용 %.1f** — P-216 이 **이미 반영된 수**다(N 쪽 합계). "
              "이 산출기가 대장을 kind 로 다시 세어 **%.1f** 를 얻었다 — **같다.**"
              % (TAG, d["status"], d["kind"]))
        print("%s    ★ 이 `%+.1f` 를 「안 내려갔다」로 읽지 마라. 내려간 수는 N 의 "
              "보고에 있다: **66.5 → 53.8**(P-216 −3.2 · P-215 −9.5). "
              "여기 `0` 은 **두 도구가 같은 수를 낸다**는 뜻이다 (D-369)"
              % (TAG, d["delta"]))
        if rep["pr_closed_line"]:
            print("%s    실은: %s" % (TAG, rep["pr_closed_line"]))
        print("%s    ★ **내려간 수가 정본이다.** 후퇴가 아니라 **반납**이다 — "
              "절 수는 154 그대로다(분모는 안 움직였다)." % TAG)
    elif d:
        print("%s ★★ **상용 %.1f → %.1f** (%+.1f) — P-216 「점수를 `kind` 로 센다」."
              % (TAG, d["status"], d["kind"], d["delta"]))
        print("%s    사유: 세 턴 동안 「67.x」라 부르던 수는 `status: 구현` 을 센 "
              "수였다. **「구현」은 닫혔다는 뜻이 아니다** — 대장은 이미 다섯 부류로 "
              "갈라 적고 있었는데 점수식만 그 갈래를 안 봤다." % TAG)
        if rep["pr_closed_line"]:
            print("%s    실은: %s" % (TAG, rep["pr_closed_line"]))
        print("%s    ★ **내려간 수가 정본이다.** 후퇴가 아니라 **반납**이다 — "
              "절 수는 154 그대로다(분모는 안 움직였다)." % TAG)
    else:
        print("%s ? 상용 수를 kind 로 다시 못 셌다 — 영역 꼬리를 못 읽었다" % TAG)

    print("")
    for key, label, defn in (
            ("fc", "FC", "(48행 「누른 뒤」 초록/48 + 온보딩 48행/48 + 계약 39절 도달/39) ÷ 3"),
            ("pr", "PR", "대장 kind 점수 ×0.7 + 재부팅 아침 ×0.1 + 스테이징 ×0.1 + 창 2a·2b ×0.1"),
            ("cr", "CR", "8칸 각 {0, 0.5, 1} ÷ 8")):
        sc = rep[key]
        print("%s %-3s %s" % (TAG, label, aa_fmt(sc)))
        print("%s     셈법: %s" % (TAG, defn))
        for c in sc["cells"]:
            if c["measured"]:
                print("%s       O %-22s %s/%s = %5.1f%%   %s"
                      % (TAG, c["name"], _num(c["num"]), _num(c["den"]),
                         c["value"] * 100.0, c["source"] or c["why"]))
            else:
                print("%s       ? %-22s **회색 — 못 쟀다.** %s"
                      % (TAG, c["name"], c["why"]))
        st = rep["stated"].get(key)
        if st is not None and sc["measured_pct"] is not None:
            print("%s     문서가 적은 수 %.1f ↔ 다시 센 수 %.1f (%+.1f)"
                  % (TAG, st, sc["measured_pct"], sc["measured_pct"] - st))
        elif st is not None:
            print("%s     문서가 적은 수 %.1f ↔ **다시 셀 수 없다(회색)** — "
                  "그 수는 인용이지 실측이 아니다" % (TAG, st))
        print("")

    for line in rep["note"]:
        print("%s   · %s" % (TAG, line))
    for line in rep["grey"]:
        print("%s   ? %s" % (TAG, line))
    for line in rep["red"]:
        print("%s   X %s" % (TAG, line))

    n_grey = len(rep["grey"])
    print("%s [입력] 칸 %d개(FC 3 · PR 4 · CR 8) · 잰 칸 %d · **회색 %d**"
          % (TAG, 15,
             rep["fc"]["n_measured"] + rep["pr"]["n_measured"] + rep["cr"]["n_measured"],
             rep["fc"]["n_cells"] - rep["fc"]["n_measured"]
             + rep["pr"]["n_cells"] - rep["pr"]["n_measured"]
             + rep["cr"]["n_cells"] - rep["cr"]["n_measured"]))
    if rep["red"]:
        print("%s X **빨강** — 위 %d건. 문서와 코드가 갈렸거나 격자 밖이다" % (TAG, len(rep["red"])))
        return 1
    if n_grey:
        print("%s ? **회색(exit 2)** — 못 잰 칸이 있다. 회색은 초록이 아니다 (D-301). "
              "★ 그 칸들은 **0 이 아니다** — 증거 한 건이 하한과 상한을 좁힌다" % TAG)
        return 2
    return 0


def _num(v) -> str:
    """정수는 정수로 · 소수는 한 자리로. `24.5/48` 과 `10/39` 가 같은 표에 선다."""
    if v is None:
        return "?"
    return "%d" % v if abs(v - round(v)) < 1e-9 else "%.1f" % v


def main() -> int:
    ap = argparse.ArgumentParser(description="8영역 · FC · PR · CR 을 한 번에 낸다")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--table", action="store_true", help="대표 보고용 마크다운 표")
    ap.add_argument("--report", action="store_true",
                    help="**턴 보고 첫 표 여덟 줄** — 그대로 붙여 넣는다 (P-117)")
    ap.add_argument("--aa", action="store_true",
                    help="★ **세종의 세 수**(FC·PR·CR) — 못 잰 칸은 회색이다 (P-220)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if self_test(verbose=False):
        return 1

    # ── ★ P-220 · 세종의 세 수 ────────────────────────────────────────────
    #    `MEASURED=` 는 **이 보고가 돌고 난 뒤** 만든다 — 분모를 미리 적으면
    #    그 분모는 「지금 센 것」이 아니라 「적어 둔 것」이고, 그것이 거짓 분모다.
    if args.aa:
        click, click_why = run_click_completes()
        rep = aa_report(click=click, click_why=click_why)
        from _gate_header import gate_header as _gh, file_stamp
        _gh(__file__, measured=aa_measured_line(rep),
            target="세종 세 수 — 대장(kind) · 온보딩 48행 · 48행 「누른 뒤」 · CR 8칸",
            as_="(자격증명 없음 — 게이트를 부르고 문서를 읽는다)",
            source="verify_ga_readiness.py + verify_click_completes.py 를 **부른다** · "
                   + file_stamp(AA_REVIEW_DOC) + " + " + file_stamp(ONBOARD_DOC))
        return aa_print(rep)

    gray: list[str] = []
    red: list[str] = []

    # ── ① 8영역 — `verify_ga_readiness` 를 **부른다** (읽어서 답하지 않는다) ──
    ga_out, ga_rc = run_ga()
    areas, ga_total, inhand = parse_ga_areas(ga_out)
    area8 = None
    if not areas:
        gray.append("8영역: `verify_ga_readiness.py` 를 못 불렀다 — SOURCE_MISSING")
    else:
        for a in areas:
            print("%s   영역 %d %-24s 가중 %2d%%  %2d/%-3d = %3d%%"
                  % (TAG, a["no"], a["name"][:24], a["weight"], a["done"], a["total"], a["pct"]))
        a8 = [a for a in areas if a["no"] == 8]
        if a8:
            area8 = round(a8[0]["done"] / a8[0]["total"], 4)
        print("%s ★ 8영역 가중 합계 **%s%%** · 손 안 도달율 **%s%%** [실측] (게이트 exit %s)"
              % (TAG, ga_total, inhand, ga_rc))
        #: ★ 색은 `verify_ga_readiness` 가 낸다 — 같은 사실을 두 곳에 적지 않는다 (D-227).
        #:   그러나 **어떤 색 위에서 나온 수인지**는 여기서 말해야 한다. 빨강인 대장에서
        #:   뽑은 수를 아무 말 없이 내면 읽는 사람은 그것을 초록 위의 수로 읽는다.
        if ga_rc == 1:
            print("%s ⚠ 위 수는 `verify_ga_readiness` 가 **빨강(exit 1)** 인 상태에서 "
                  "나온 수다 — 그 빨강의 색은 그 판정기가 낸다(D-227). 여기서는 "
                  "**어떤 색 위의 수인지**만 적는다" % TAG)
            gray.append("8영역: 대장 게이트가 **빨강**이다 — 그 절들이 고쳐지면 이 수는 움직인다")
        elif ga_rc == 2:
            print("%s ⚠ 위 수는 `verify_ga_readiness` 가 **회색(exit 2)** 인 상태에서 "
                  "나온 수다 — 못 부른 게이트가 있다" % TAG)
            gray.append("8영역: `verify_ga_readiness` 가 회색이다(못 부른 게이트가 있다) — "
                        "영역 수는 실재하나 그 안에 못 잰 절이 있다")

    # ── ② CR — 문서를 **읽어서** 계산한다 ──────────────────────────────────
    print("")
    if not CR_DOC.is_file():
        gray.append("CR: 셈법 문서가 없다 (%s) — SOURCE_MISSING. "
                    "셈법 없는 수를 지어내지 않는다" % CR_DOC.name)
        cr = None
    else:
        text = CR_DOC.read_text(encoding="utf-8", errors="replace")
        tables = parse_cr_tables(text)
        if not tables:
            red.append("CR: 셈법 문서에서 ①~⑨ 아홉 행 표를 못 찾았다 — "
                       "문서의 모양이 바뀌었다면 **이 도구도 함께 고쳐라**. "
                       "못 읽은 채 넘어가면 이 도구가 눈이 먼다 (P-93)")
            cr = None
        else:
            rows = tables[-1]  # 가장 나중에 잰 절이 지금 값이다
            cr, bad = judge_cr_table(rows, area8_ratio=area8)
            red.extend("CR: " + b for b in bad)

            print("%s [CR] 셈법 %s §2~3 — 항목 9 · 값 {0, 0.5, 1} (①만 영역 ⑧ 비율)"
                  % (TAG, CR_DOC.name))
            print("%s [CR] 항목값: %s" % (TAG, " · ".join(
                "%s=%s" % (k, UNMEASURED if v is None else ("%g" % v))
                for k, v in cr["values"].items())))
            print("%s [CR] 확인된 합 **%.1f** · 못 쟀다 **%d**건 "
                  "(0 으로도 1 로도 세지 않는다 — 셈법 §0)"
                  % (TAG, cr["known"], cr["unmeasured"]))
            print("%s ★ **CR 하한 %.1f%% · 상한 %.1f%%** [실측 · 문서 셈법으로 다시 셈]"
                  % (TAG, cr["lower"], cr["upper"]))

            # 문서가 적어 둔 수와 다시 센 수를 대조한다 — 갈리면 빨강
            d_lo, d_hi = parse_doc_stated(text)
            if d_lo is not None and abs(d_lo - cr["lower"]) > 0.15:
                red.append("CR: 문서가 적은 하한 %.1f%% ≠ 다시 센 하한 %.1f%% — "
                           "**문서와 코드가 갈렸다**" % (d_lo, cr["lower"]))
            if d_hi is not None and abs(d_hi - cr["upper"]) > 0.15:
                red.append("CR: 문서가 적은 상한 %.1f%% ≠ 다시 센 상한 %.1f%% — "
                           "**문서와 코드가 갈렸다**" % (d_hi, cr["upper"]))
            if d_lo is not None and d_hi is not None and not red:
                print("%s [CR] 문서가 적어 둔 %.1f%% / %.1f%% 와 같다 — 문서와 코드가 안 갈렸다"
                      % (TAG, d_lo, d_hi))

            # ★ 출생 표본 ① — 격자 검사. 격자 밖의 수는 눈대중이다(§5-3)
            a1 = cr["values"].get("①")
            if a1 is not None:
                print("%s [CR] 격자: 가능한 합은 `%.1f + 0.5k` 뿐이다 — "
                      "이 격자 밖의 수(예: 38%%)는 이 셈법의 산물이 아니라 **눈대중**이다 (§5-3)"
                      % (TAG, a1))

    # ── ③ FC · PR — 셈법 문서(§1·§2·§3′)를 **읽어서** 센다 (P-103) ──────────
    print("")
    fcpr_text = FCPR_DOC.read_text(encoding="utf-8", errors="replace") if FCPR_DOC.is_file() else ""
    prd_text = PRD_DOC.read_text(encoding="utf-8", errors="replace") if PRD_DOC.is_file() else ""
    fp = fc_pr_report(fcpr_text, prd_text)
    if fp["fc"] is None:
        print("%s [FC·PR] **회색 — %s**" % (TAG, fp["why"] or "표를 못 읽었다"))
    else:
        print("%s [FC] 셈법 %s §1·§3′ — 페인포인트 **%d**(PRD v2.6 §3) · 값 {0, 0.5, 1}"
              % (TAG, FCPR_DOC.name, FC_ROWS))
        print("%s [FC] 확인된 합 **%.1f** · 손 밖 **%d**행 · 회색(세종 값·못 잼) **%d**행"
              % (TAG, fp["fc"]["lower_sum"], fp["fc"]["out_of_hand"], fp["fc"]["unmeasured"]))
        print("%s ★ **FC 하한 %.1f%% · 상한 %.1f%%** [실측 · 문서 셈법으로 다시 셈]"
              % (TAG, fp["fc"]["lower"], fp["fc"]["upper"]))
        print("%s [PR] 관문 G1~G5 × 3 = **%d**칸 · 확인된 합 **%.1f** · 회색 **%d**행"
              % (TAG, PR_ROWS, fp["pr"]["lower_sum"], fp["pr"]["unmeasured"]))
        if fp["pr"]["unmeasured"] or fp["pr"]["out_of_hand"]:
            print("%s ★ **PR 하한 %.1f%% · 상한 %.1f%%** [실측]"
                  % (TAG, fp["pr"]["lower"], fp["pr"]["upper"]))
        else:
            print("%s ★ **PR %.1f%%** [실측 · 회색 0행이므로 한 수다]" % (TAG, fp["pr"]["lower"]))
        for label in ("FC", "PR"):
            dis = fp["disagree"][label]
            print("%s [%s] **세종 판정과 어긋난 행 %d**%s"
                  % (TAG, label, len(dis), (" — " + " · ".join(dis[:6])) if dis else ""))
            if len(dis) > 6:
                print("%s        … 그리고 %d행 더" % (TAG, len(dis) - 6))
        print("%s   ⚠ **FC 82 · PR 83 은 이 셈법의 산물이 아니다 — 폐기**(셈법 §0). "
              "위 수가 그보다 낮은 것은 후퇴가 아니라 반납이다" % TAG)
    red.extend(fp["red"])
    gray.extend(fp["gray"])

    # ── ④ P-149 — PR 15관문(§2 눈금) · CR 8조건(§1) **첫 판** ─────────────────
    #    ★ 이 두 수는 여태 사람이 **인용**하던 자리다(09-08 손 점검 20.0 · 12.5).
    #      인용한 수는 정본이 바뀌어도 안 바뀐다 — 그래서 여기서 **읽어서 다시 센다**.
    print("")
    review_text = REVIEW_DOC.read_text(encoding="utf-8", errors="replace") \
        if REVIEW_DOC.is_file() else ""

    if not fcpr_text:
        gray.append("PR15: 셈법 문서가 없다 — 관문 눈금을 못 읽는다")
    else:
        rubric = parse_pr_rubric(
            slice_section(fcpr_text, "## 2. PR", "## 3. 세종") or fcpr_text)
        print("%s [PR15] 눈금 `%s` §2 — 관문 %s · 항목 **%d**"
              % (TAG, FCPR_DOC.name,
                 " ".join(sorted({r["gate"] for r in rubric if r["gate"]})) or "?",
                 len(rubric)))
        if fp.get("pr"):
            bad_pr = cross_check_pr(rubric, fp["pr"]["rows"])
            red.extend("PR15: " + b for b in bad_pr)
            if not bad_pr:
                print("%s ★ **PR(15관문) %.1f%%** (%.1f/%d) [실측 · 「있는가」 술어 · "
                      "§2 눈금 ↔ §3′-2 값 어긋남 **0**]"
                      % (TAG, fp["pr"]["lower"], fp["pr"]["lower_sum"], PR_ROWS))
        else:
            gray.append("PR15: §3′-2 실측 표를 못 읽었다 — 눈금은 있고 값이 없다")
        #: ★ 「끝나는가」 술어의 PR 은 **행별 정본이 없다.** §12 는 합계 한 줄뿐이다.
        #:   없는 표를 지어내지 않는다 — 그 칸은 회색이고, 인용으로만 나간다.
        gray.append("PR15(「끝나는가」 술어): 15칸을 **행별로** 적은 정본이 저장소에 없다 "
                    "(`%s` §12 는 합계 한 줄뿐) — 없는 표를 지어내지 않는다. "
                    "그 술어의 PR 은 **인용**이지 이 산출기의 수가 아니다" % REVIEW_DOC.name)

    if not review_text:
        gray.append("CR8: `%s` 가 없다 — 8조건의 정본이 없다. 셈법 없는 수를 지어내지 않는다"
                    % REVIEW_DOC.name)
    else:
        cr8_rows = parse_cr8(
            slice_section(review_text, "## 1. 상용서비스", "## 2.") or review_text)
        cr8, bad8 = judge_cr8(cr8_rows)
        red.extend("CR8: " + b for b in bad8)
        print("%s [CR8] 셈법 `%s` §1 — **돈을 내는 8조건** · 값 {0, 0.5, 1}"
              % (TAG, REVIEW_DOC.name))
        print("%s [CR8] 조건값: %s" % (TAG, " · ".join(
            "%s=%s" % (CIRCLED[r["no"] - 1],
                       UNMEASURED if r["value"] is None else ("%g" % r["value"]))
            for r in cr8_rows)))
        if cr8["unmeasured"]:
            print("%s ★ **CR(8조건) 하한 %.1f%% · 상한 %.1f%%** [실측 · 회색 %d조건]"
                  % (TAG, cr8["lower"], cr8["upper"], cr8["unmeasured"]))
        else:
            print("%s ★ **CR(8조건) %.1f%%** (%.1f/%d) [실측 · 문서 표를 다시 셈 · 회색 0]"
                  % (TAG, cr8["lower"], cr8["known"], cr8["n"]))
        #: 문서가 §12 에 적어 둔 수와 대조한다 — CR 9항목·FC 와 **같은 자리**의 검사다.
        h = parse_handson(review_text).get("CR")
        if h and abs(h["pct"] - cr8["lower"]) > 0.15:
            red.append("CR8: 문서 §12 가 적은 %.1f%% ≠ §1 표를 다시 센 %.1f%% — "
                       "**문서와 코드가 갈렸다.** 수를 맞추지 말고 어느 쪽이 틀렸는지 "
                       "정하고 그쪽을 고쳐라" % (h["pct"], cr8["lower"]))
        elif h:
            print("%s [CR8] §12 가 적어 둔 %.1f%% 와 같다 — 문서와 코드가 안 갈렸다"
                  % (TAG, h["pct"]))

    # ── 판정 ────────────────────────────────────────────────────────────────
    print("")
    if args.table:
        print(md_table(areas, ga_total, inhand, cr, fp))
        print("")

    if args.report:
        #: ★ 첫 표는 **도구가 찍는다.** 사람이 옮겨 적는 순간 그 표는 낡기 시작한다.
        block, rgray = report_block(areas, ga_total, inhand, cr, fp)
        print("─" * 78)
        print("[보고 첫 표 · 여기부터 그대로 붙여 넣는다 — P-117]")
        print("─" * 78)
        print(block)
        print("─" * 78)
        print("")
        gray.extend(rgray)

    if red:
        for r in red:
            print("%s X %s" % (TAG, r))
        print("%s **실패(exit 1)** — 문서와 코드가 갈렸다. 수를 맞추지 말고 "
              "**어느 쪽이 틀렸는지** 정하고 그쪽을 고쳐라" % TAG)
        return 1
    for g in gray:
        print("%s ? %s" % (TAG, g))
    print("%s **회색(exit 2)** — CR 은 쟀고(하한/상한), **FC·PR 은 못 쟀다.** "
          "회색은 초록이 아니다 (D-301). 회색으로 내는 것이 추정치를 실측처럼 내는 것보다 낫다" % TAG)
    return 2


def md_table(areas, ga_total, inhand, cr, fp) -> str:
    L = ["| 척도 | 값 | 색 | 출처 |", "|---|---|---|---|"]
    if areas:
        L.append("| 8영역 가중 합계 | **%s%%** | 실측 | `verify_ga_readiness.py` |" % ga_total)
        L.append("| 손 안 도달율 | **%s%%** | 실측 | `verify_ga_readiness.py` |" % inhand)
        for a in areas:
            L.append("| 　영역 %d %s | %d/%d = %d%% | 실측 | 같음 |"
                     % (a["no"], a["name"], a["done"], a["total"], a["pct"]))
    if cr:
        L.append("| **CR** 하한/상한 | **%.1f%% / %.1f%%** | 실측 | `%s` §2~3 |"
                 % (cr["lower"], cr["upper"], CR_DOC.name))
    if fp.get("fc"):
        L.append("| **FC** 기능 완결성 하한/상한 | **%.1f%% / %.1f%%** | 실측 | `%s` §1·§3′ (18행) |"
                 % (fp["fc"]["lower"], fp["fc"]["upper"], FCPR_DOC.name))
        L.append("| **PR** 상용 준비 | **%.1f%%** | 실측 | `%s` §2·§3′ (15칸) |"
                 % (fp["pr"]["lower"], FCPR_DOC.name))
        L.append("| 　세종 판정과 어긋난 행 | FC **%d** · PR **%d** | 실측 | 같음 |"
                 % (len(fp["disagree"]["FC"]), len(fp["disagree"]["PR"])))
    else:
        L.append("| **FC** 기능 완결성 | — | **회색** | %s |" % fp["why"])
        L.append("| **PR** 상용 준비 | — | **회색** | %s |" % fp["why"])
    return "\n".join(L)


# ═══════════════════════════════════════════════════════════════════════════
# P-117 — 보고 첫 표 여덟 줄. **붙여 넣을 수 있는 꼴로** 낸다
# ═══════════════════════════════════════════════════════════════════════════

GREY_CELL = "**회색**"


def _band(lo: float, hi: float) -> str:
    """하한과 상한이 같으면 한 수로, 벌어지면 띠로 적는다."""
    return "%.1f" % lo if abs(hi - lo) < 0.05 else "%.1f~%.1f" % (lo, hi)


def report_block(areas, ga_total, inhand, cr, fp) -> tuple[str, list[str]]:
    """턴 보고의 **첫 표 여덟 줄** + G1~G5 + 남은 턴 + RC-1 을 그대로 낸다.

    ★ 두 술어를 **나란히** 둔다. 섞지 않는다 — 섞은 수는 두 사실을 다 지운다.
    """
    gray: list[str] = []
    review = REVIEW_DOC.read_text(encoding="utf-8", errors="replace") \
        if REVIEW_DOC.is_file() else ""
    prd27 = PRD27_DOC.read_text(encoding="utf-8", errors="replace") \
        if PRD27_DOC.is_file() else ""
    onboard = ONBOARD_DOC.read_text(encoding="utf-8", errors="replace") \
        if ONBOARD_DOC.is_file() else ""

    hands = parse_handson(review)
    if not hands:
        gray.append("「끝나는가」 칸: 손 점검 문서를 못 읽었다 (%s) — 그 칸은 전부 회색이다"
                    % REVIEW_DOC.name)
    hand_src = "`%s` §9 · **09-08 손 점검**" % REVIEW_DOC.name

    ob = parse_onboarding(onboard)
    if ob is None:
        gray.append("온보딩: `%s` 에서 «N / 48 = P%%» 를 못 읽었다" % ONBOARD_DOC.name)
    elif not ob["consistent"]:
        gray.append("온보딩: 문서가 적은 %.1f%% 와 %.1f/%d 을 다시 곱한 %.1f%% 가 갈린다"
                    % (ob["pct"], ob["sum"], ob["n"], ob["calc"]))

    #: FC 의 「끝나는가」 칸은 **게이트를 부른다.** 없으면 손 점검을 인용한다.
    click, click_note = run_click_completes()
    if click is None:
        gray.append("`verify_click_completes` — %s. 「끝나는가」 칸은 **09-08 손 점검 인용**이다"
                    % click_note)
        fc2 = hands.get("FC")
        fc2_cell = ("**%.1f** (%.1f/%d 흐름)" % (fc2["pct"], fc2["sum"], fc2["n"])) \
            if fc2 else GREY_CELL
        fc2_lo = fc2_hi = (fc2["pct"] if fc2 else None)
        fc2_sum_lo = fc2["sum"] if fc2 else None
        fc2_src = hand_src
    else:
        n = click["n"]
        fc2_lo = click["green"] / n * 100.0
        fc2_hi = (click["green"] + click["grey"]) / n * 100.0
        fc2_sum_lo = float(click["green"])
        fc2_cell = ("**%s** (초록 %d · 빨강 %d · **회색 %d**/%d)"
                    % (_band(fc2_lo, fc2_hi), click["green"], click["red"], click["grey"], n))
        fc2_src = "`verify_click_completes` 를 **불렀다** · %s" % (
            click["when"] or _stamp(CLICK_SCRIPT))
        if click["grey"]:
            gray.append("「끝나는가」 FC: 게이트가 **회색 %d행**을 냈다 — 그래서 한 수가 "
                        "아니라 띠(%s)다. 회색을 0 으로도 1 로도 세지 않는다"
                        % (click["grey"], _band(fc2_lo, fc2_hi)))

    L = ["| # | 척도 | **「있는가」** v0.1 · 산출물 술어 | **「끝나는가」** v0.2 · 손 술어 "
         "| 차 | 출처 · 잰 때 |",
         "|---|---|---|---|---|---|"]
    NO_SAME = "— (같은 술어의 수가 없다)"
    DIFF_DEN = "**분모가 다르다** — 빼지 않는다"

    # ── 1·2 상용 /100 · 손 안 도달율 ────────────────────────────────────────
    import datetime as _dt
    ga_src = "`verify_ga_readiness.py` 를 **지금 불렀다** · %s" % _dt.datetime.now().strftime(
        "%m-%d %H:%M")
    L.append("| 1 | 상용 /100 | **%s** | %s | — | %s |"
             % (("%s" % ga_total) if ga_total is not None else GREY_CELL, NO_SAME, ga_src))
    L.append("| 2 | 손 안 도달율 | **%s** | %s | — | %s |"
             % (("%s" % inhand) if inhand is not None else GREY_CELL, NO_SAME, ga_src))

    # ── 3 온보딩 48행 — **두 술어가 같은 48행을 쟀다. 여기서 차가 뜻을 가진다** ──
    #    ★ 이 줄이 이 표의 심장이다: `onboarding_48.md` 의 48행과 「끝나는가」의 48흐름은
    #      **같은 48행**이다. 그러므로 여기의 차는 눈금 차가 아니라 **「그려졌지만 안
    #      끝나는 행」의 수**다 — 대표가 보아야 할 바로 그 수.
    if ob and fc2_lo is not None:
        p1 = ob["pct"]
        #: ★ 차는 **하한**에서만 낸다. 상한은 「못 잰 것이 다 끝난다면」의 수이고,
        #:   그것으로 차를 내면 「끝나는가」가 「있는가」를 넘는 음수 아닌 수가 나온다 —
        #:   못 잰 것을 **좋은 쪽으로** 세어 만든 수다. 차는 잰 것으로만 낸다.
        L.append("| 3 | 온보딩 48행 | **%.0f%%** (%.1f/%d) | **%s%%** | "
                 "**%+.1f%%p** · **%.1f행** — 같은 48행인데 %s | `%s` %s ↔ %s |"
                 % (p1, ob["sum"], ob["n"], _band(fc2_lo, fc2_hi),
                    fc2_lo - p1, (p1 - fc2_lo) / 100.0 * ob["n"],
                    ("그려졌는데 안 끝난다 (하한 기준 · 나머지 %.0f행은 **못 쟀다**)"
                     % ((fc2_hi - fc2_lo) / 100.0 * ob["n"]))
                    if fc2_hi > fc2_lo else "그려졌는데 안 끝난다",
                    ONBOARD_DOC.name, _stamp(ONBOARD_DOC), fc2_src))
    else:
        L.append("| 3 | 온보딩 48행 | %s | %s | — | `%s` |"
                 % (("**%.0f%%** (%.1f/%d)" % (ob["pct"], ob["sum"], ob["n"])) if ob else GREY_CELL,
                    GREY_CELL, ONBOARD_DOC.name))

    # ── 4 FC ────────────────────────────────────────────────────────────────
    if fp.get("fc"):
        v1 = "**%s** (%.1f~%.1f/18 페인)" % (_band(fp["fc"]["lower"], fp["fc"]["upper"]),
                                            fp["fc"]["lower_sum"], fp["fc"]["upper_sum"])
        s1 = "`%s` §3′-1 · %s" % (FCPR_DOC.name, _stamp(FCPR_DOC))
    else:
        v1, s1 = GREY_CELL, fp.get("why", "")
    L.append("| 4 | **FC** 기능 완결 | %s | %s | %s | %s ↔ %s |"
             % (v1, fc2_cell, DIFF_DEN + " (18 페인 ↔ 48 흐름)", s1, fc2_src))

    # ── 5 PR — **분모가 같은 15칸이다. 차가 곧 「그려짐」의 값이다** ──────────
    pr2 = hands.get("PR")
    if fp.get("pr") and pr2 and pr2["n"] == PR_ROWS:
        d = pr2["pct"] - fp["pr"]["lower"]
        L.append("| 5 | **PR** 상용 준비 | **%.1f** (%.1f/%d 관문) | **%.1f** (%.1f/%d 관문) "
                 "| **%+.1f%%p** · %.1f칸 | `%s` §3′-2 · %s ↔ %s |"
                 % (fp["pr"]["lower"], fp["pr"]["lower_sum"], PR_ROWS,
                    pr2["pct"], pr2["sum"], pr2["n"], d,
                    fp["pr"]["lower_sum"] - pr2["sum"], FCPR_DOC.name,
                    _stamp(FCPR_DOC), hand_src))
    else:
        L.append("| 5 | **PR** 상용 준비 | %s | %s | — | — |"
                 % (("**%.1f**" % fp["pr"]["lower"]) if fp.get("pr") else GREY_CELL,
                    ("**%.1f**" % pr2["pct"]) if pr2 else GREY_CELL))

    # ── 6 CR ────────────────────────────────────────────────────────────────
    cr2 = hands.get("CR")
    v1 = ("**%s** (%.1f~%.1f/9 항목)" % (_band(cr["lower"], cr["upper"]),
                                        cr["known"], cr["known"] + cr["unmeasured"])) \
        if cr else GREY_CELL
    v2 = ("**%.1f** (%.1f/%d 조건)" % (cr2["pct"], cr2["sum"], cr2["n"])) if cr2 else GREY_CELL
    L.append("| 6 | **CR** 상용 준비도 | %s | %s | %s | `%s` §2~3 · %s ↔ %s |"
             % (v1, v2, DIFF_DEN + " (9 항목 ↔ 8 조건)", CR_DOC.name,
                _stamp(CR_DOC), hand_src))

    # ── 7 8영역 한 줄 ───────────────────────────────────────────────────────
    if areas:
        one = " ".join("%s%d" % (CIRCLED[a["no"] - 1], a["pct"]) for a in areas)
        L.append("| 7 | 8영역 | %s → 가중 **%s** | %s | — | %s |" % (one, ga_total, NO_SAME, ga_src))
    else:
        L.append("| 7 | 8영역 | %s | %s | — | %s |" % (GREY_CELL, NO_SAME, ga_src))

    # ── 8 커밋 해시 · 또는 「보류 · 막는 게이트 · 사유 · 보험 패치」 ──────────
    cs = commit_state()
    if cs["clean"]:
        cell = "**커밋 `%s`** · %s" % (cs["head"], cs["committed_at"][:16])
        src = "`git rev-parse HEAD`"
    else:
        kinds = " · ".join("%s %d" % (k, v) for k, v in sorted(cs["kinds"].items()))
        patch = ("`%s` %s%s" % (cs["patch"].name, _stamp(cs["patch"]),
                                " · ⚠ **작업본보다 낡았다**" if cs["patch_stale"] else "")) \
            if cs["patch"] else "**없다**"
        cell = ("**보류** · HEAD `%s`(%s) · 미커밋 **%d**파일(%s) · 보험 패치 %s"
                % (cs["head"], cs["committed_at"][:10], cs["dirty"], kinds, patch))
        src = "`git status --porcelain` · `%s/`" % PATCH_DIR.name
        gray.append("커밋: **보류의 사유는 이 도구가 못 잰다** — 사람의 결정이다. "
                    "조율자가 「막는 게이트 이름 · 사유」를 이 칸에 손으로 덧붙인다")
        if cs["patch_stale"]:
            gray.append("보험 패치가 **작업본보다 낡았다** — 지금 뜨지 않으면 이 턴의 "
                        "일은 보험 밖에 있다")
    L.append("| 8 | 커밋 | %s | — | — | %s |" % (cell, src))

    out = ["\n".join(L), ""]

    # ── 각주 — **09-08 손 점검을 표 안에 녹이지 않는다** ────────────────────
    #    게이트가 서기 전의 수이고 눈금이 다르다({1, 0.5, 0} ↔ {초록, 회색, 빨강}).
    #    그래서 표의 칸이 아니라 **각주**로 둔다 — 지우지도, 섞지도 않는다.
    if hands:
        out.append("※ 「끝나는가」 **첫 실측**(2026-09-08 · 사람이 역할 계정으로 직접 누름 · "
                   + "%s): " % hand_src
                   + " · ".join("%s **%.1f** (%.1f/%d)"
                                % (k, hands[k]["pct"], hands[k]["sum"], hands[k]["n"])
                                for k in ("FC", "PR", "CR") if k in hands)
                   + ". 게이트가 서기 전의 수이고 **눈금이 다르다**"
                     "({1 · 0.5 · 0} ↔ {초록 · 회색 · 빨강}) — 위 칸과 빼지 않는다.")
        out.append("")

    # ── G1~G5 ───────────────────────────────────────────────────────────────
    if fp.get("pr"):
        marks = gate_marks(fp["pr"]["rows"])
        if marks:
            out.append("**G1~G5** " + "  ".join("%s %s(%.1f/%d)" % (n, m, s, k)
                                                for n, m, s, k in marks)
                       + "   ← 「있는가」 15칸 · `%s` §3′-2" % FCPR_DOC.name)
        else:
            gray.append("G1~G5: §3′-2 의 「관문」 칸에서 G1~G5 를 못 읽었다")
            out.append("**G1~G5** " + GREY_CELL)
    else:
        out.append("**G1~G5** " + GREY_CELL)

    # ── 남은 턴 ─────────────────────────────────────────────────────────────
    #: ★ **어떤 문서도 남은 턴 수를 적지 않았다.** 지어내지 않는다(D-301). 대신
    #:   잴 수 있는 것을 잰다 — RC-1 문턱까지 **몇 칸이 움직여야 하는가**.
    turns = re.findall(r"남은 턴\s*[:：]?\s*\*{0,2}(\d+)", RESUME_DOC.read_text(
        encoding="utf-8", errors="replace") if RESUME_DOC.is_file() else "")
    if turns:
        out.append("**남은 턴** %s [문서 인용 · `%s`]" % (turns[-1], RESUME_DOC.name))
    else:
        gray.append("남은 턴: **어느 문서도 적지 않았다** — 지어내지 않는다. "
                    "아래 「RC-1 까지 남은 칸」이 그 자리에 서는 실측이다")
        out.append("**남은 턴** %s — 지시서·셈법 어디에도 턴 수가 없다. "
                   "RC-1 은 턴이 아니라 **대표 결정(공개 URL·스테이징)** 에 걸려 있다"
                   % GREY_CELL)

    # ── RC-1 ────────────────────────────────────────────────────────────────
    rc = parse_rc1(prd27)
    for key, r in (("FC", hands.get("FC")), ("PR", hands.get("PR")), ("CR", hands.get("CR"))):
        if r and r.get("rc1") is not None and key in rc and abs(r["rc1"] - rc[key]) > 1e-9:
            gray.append("RC-1 문턱 %s: `%s` 는 ≥%g · `%s` 는 ≥%g — **두 문서가 갈렸다**"
                        % (key, REVIEW_DOC.name, r["rc1"], PRD27_DOC.name, rc[key]))
    if rc:
        #: ★ 거리는 **위 표가 쓴 그 수**에서 잰다. 표와 다른 출처로 거리를 재면
        #:   두 줄이 같은 이름으로 다른 말을 한다 — 이 도구가 막으려는 바로 그 병.
        need = []
        srcs: list[tuple[str, float | None, float | None, int, str]] = [
            ("FC", fc2_sum_lo, fc2_lo, ONBOARD_ROWS,
             "게이트 하한" if click is not None else "09-08 손 점검"),
        ]
        for key, den in (("PR", PR_ROWS), ("CR", 8)):
            h = hands.get(key)
            srcs.append((key, h["sum"] if h else None, h["pct"] if h else None,
                         h["n"] if h else den, "09-08 손 점검"))
        for key, s, pct, den, note in srcs:
            if key not in rc or s is None:
                continue
            need.append("%s ≥%g (지금 %.1f · **%+.1f칸** · %s)"
                        % (key, rc[key], pct, rc[key] / 100.0 * den - s, note))
        if "상용 /100" in rc and ga_total is not None:
            need.append("상용 ≥%g (지금 %s · **%+.1f점** · 「있는가」)"
                        % (rc["상용 /100"], ga_total, rc["상용 /100"] - float(ga_total)))
        out.append("**RC-1** " + " · ".join(need)
                   + "   ← 문턱 `%s` §3 · **「끝나는가」 술어로 잰 거리**" % PRD27_DOC.name)
    else:
        gray.append("RC-1: `%s` 에서 「RC-1 문턱」 줄을 못 읽었다" % PRD27_DOC.name)
        out.append("**RC-1** " + GREY_CELL)

    return "\n".join(out), gray


if __name__ == "__main__":
    from _gate_header import gate_header, file_stamp  # P-107 — TARGET/AS/SOURCE
    #: ★ `--aa` 갈래는 **제 머리글을 스스로 낸다** — 그 갈래의 `MEASURED=` 분모는
    #:   보고가 돌고 난 뒤에야 알 수 있기 때문이다(잰 칸 몇 개인지는 재 봐야 안다).
    #:   여기서 한 번 더 찍으면 머리글이 둘이 되고, 읽는 사람은 **앞엣것을 읽는다.**
    if "--aa" not in sys.argv:
        gate_header(
            __file__,
            #: ⚠ 여기 적은 분모는 **셈법 문서가 못박은 수**다(코드가 고른 수가 아니다).
            #:   문서의 행 수가 이와 다르면 이 도구는 수를 내지 않고 **빨강**이다 —
            #:   그러므로 이 줄은 「지금 센 것」과 갈릴 수 없다.
            measured=("셈법 문서를 **읽어서** 네 수를 낸다 — CR **분모 9항목**(§2) · "
                      "FC **분모 %d행**(PRD v2.6 §3) · PR **분모 %d칸**(GX-FCPR §2) · "
                      "CR8 **분모 %d칸**(GX-REVIEW §1) · 8영역은 "
                      "`verify_ga_readiness.py` 를 **불러서** 받는다. "
                      "문서의 행 수가 이 분모와 다르면 수를 내지 않고 빨강이다"
                      % (FC_ROWS, PR_ROWS, CR8_ROWS)),
            target="셈법 문서 셋 + verify_ga_readiness.py 를 **부른다**(읽어서 답하지 않는다)",
            as_="(자격증명 없음 — 문서를 읽고 게이트를 부른다)",
            source=file_stamp(CR_DOC) + " + " + file_stamp(FCPR_DOC) + " + "
                   + file_stamp(PRD_DOC),
        )
    sys.exit(main())
