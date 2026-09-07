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

  → 그래서 이 도구는 **FC·PR 에 수를 내지 않는다.** 근거가 될 수 있는 것만 나열하고
    「셈법 미정 · 세종 판정 필요」로 **회색(exit 2)** 을 낸다.
    **회색으로 내는 것이 추정치를 실측처럼 내는 것보다 낫다** (D-301 · 규칙 ①).

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
GA_SCRIPT = ROOT / "scripts" / "verify_ga_readiness.py"

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

    # ── ★ 출생 표본 ② — FC·PR 은 수를 내지 않는다 ────────────────────────────
    fc = fc_pr_report()
    ok("★ 출생 표본 · FC 는 수가 아니라 회색이다", fc["color"] == "회색" and fc["value"] is None)
    ok("★ 출생 표본 · PR 도 회색이다", fc["color"] == "회색")
    ok("★ 출생 표본 · 회색에 사유 이름이 붙는다", "셈법 미정" in fc["why"])

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

    fails = [n for n, g in cases if not g]
    if verbose or fails:
        for name, good in cases:
            if verbose or not good:
                print("  %-4s %s" % ("OK" if good else "FAIL", name))
    if fails:
        print("%s 자기시험 **실패** %d건 — 판정기를 먼저 의심한다 (D-350)" % (TAG, len(fails)))
        return 1
    print("%s 자기시험 %d건 통과 — ★ **출생 표본** 6(38%% 격자 · FC·PR 회색) 포함 · "
          "음성 대조 4" % (TAG, len(cases)))
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# FC · PR — 수를 내지 않는다
# ═══════════════════════════════════════════════════════════════════════════

def fc_pr_report() -> dict:
    """FC·PR 은 **셈법이 없다.** 근거 후보만 나열하고 회색을 낸다.

    ⚠ 여기서 수를 지어내지 않는다. 「82 · 83」 은 사람의 추정이었고, 추정을 실측 칸에
      옮기는 순간 다음 사람은 그것을 잰 수로 읽는다 — 이 저장소가 CR 35% 로 이미 한 번
      겪은 일이다(셈법 문서 §1: 「35% 는 세종의 눈대중이다」).
    """
    return {
        "value": None,
        "color": "회색",
        "why": "셈법 미정 · 세종 판정 필요",
        "candidates": [
            ("FC 기능 완결성", [
                "`verify_ga_readiness` 영역 ① 비율 (지금 32/39 = 82%) — 계약 절 대장에서 파생",
                "손 안 도달율 (구현 / (전체 − 설계잠금 − 손 밖))",
                "`verify_contract_ac` 의 AC 대장 — 절마다 수용 기준이 있는가",
                "`verify_route_alive` · `verify_envelope` — 라우트가 실제로 닿는가",
            ]),
            ("PR 상용 준비", [
                "관문 G1~G5 (RESUME_NEXT §0 — 지금 ◐ 4 · ● 1)",
                "`verify_prod_settings` (지금 5/5)",
                "`verify_live_freshness` (지금 초록)",
                "공개 URL 유무 (지금 **0**) — G1 의 유일한 열쇠",
                "`verify_front_line_502` 의 5xx 정본 · `ops_*` 의 운영 지속 표본",
            ]),
        ],
        "note": ("이 넷 중 무엇을 어떤 가중으로 세는지는 **판정이 있어야 정해진다.** "
                 "가중을 이 도구가 정하면 그것은 산출기가 아니라 또 하나의 눈대중이다."),
    }


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

    # ── ③ FC · PR — 수를 내지 않는다 ────────────────────────────────────────
    print("")
    fp = fc_pr_report()
    print("%s [FC·PR] **회색 — %s**" % (TAG, fp["why"]))
    for name, cands in fp["candidates"]:
        print("%s   %s — 근거가 될 수 있는 것:" % (TAG, name))
        for c in cands:
            print("%s     · %s" % (TAG, c))
    print("%s   %s" % (TAG, fp["note"]))
    print("%s   ⚠ 직전 보고의 **FC 82 · PR 83 은 [추정]** 이다. 이 도구는 그 두 수를 "
          "**덮어쓰지 않는다** — 셈법이 없으므로 잰 것이 없다 (P-96)" % TAG)
    gray.append("FC: %s" % fp["why"])
    gray.append("PR: %s" % fp["why"])

    # ── 판정 ────────────────────────────────────────────────────────────────
    print("")
    if args.table:
        print(md_table(areas, ga_total, inhand, cr, fp))
        print("")

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
    L.append("| **FC** 기능 완결성 | — | **회색** | %s |" % fp["why"])
    L.append("| **PR** 상용 준비 | — | **회색** | %s |" % fp["why"])
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
