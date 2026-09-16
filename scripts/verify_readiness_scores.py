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


def parse_onboarding(text: str) -> dict | None:
    """`onboarding_48.md` 가 **마지막으로 적은** `N / 48 = P%` 를 집고 검산한다.

    이 문서에는 재측 절이 여럿이라 같은 꼴이 열 번 넘게 나온다. **가장 나중 것**이
    지금 값이다(CR 표에서 마지막 표를 쓰는 것과 같은 규칙). 그리고 집은 뒤
    **N ÷ 48 이 정말 P 인지** 다시 곱해 본다 — 문서 안에서 분자와 백분율이
    갈리면 그것은 이 도구가 잡아야 할 어긋남이다.
    """
    found = re.findall(r"(\d+(?:\.\d+)?)\s*/\s*%d\s*=\s*\*{0,2}(\d+(?:\.\d+)?)\s*%%"
                       % ONBOARD_ROWS, text)
    if not found:
        return None
    num, pct = float(found[-1][0]), float(found[-1][1])
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

def run_ga() -> tuple[str, int | None]:
    if not GA_SCRIPT.is_file():
        return "", None
    p = subprocess.run([sys.executable, str(GA_SCRIPT)], capture_output=True, timeout=900)
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    return out, p.returncode


# ═══════════════════════════════════════════════════════════════════════════
# 본문
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description="8영역 · FC · PR · CR 을 한 번에 낸다")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--table", action="store_true", help="대표 보고용 마크다운 표")
    ap.add_argument("--report", action="store_true",
                    help="**턴 보고 첫 표 여덟 줄** — 그대로 붙여 넣는다 (P-117)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if self_test(verbose=False):
        return 1

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
    gate_header(
        __file__,
        target="셈법 문서 셋 + verify_ga_readiness.py 를 **부른다**(읽어서 답하지 않는다)",
        as_="(자격증명 없음 — 문서를 읽고 게이트를 부른다)",
        source=file_stamp(CR_DOC) + " + " + file_stamp(FCPR_DOC) + " + " + file_stamp(PRD_DOC),
    )
    sys.exit(main())
