#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-69 — **오류·빈·폼 세 상태를 누른다** (2026-09-06 · 턴 G · 차선 Q).

무엇이 이 도구를 만들었나 — **33칸이 빈 이유는 화면이 아니라 도구였다**
--------------------------------------------------------------------
    `perf_load.py`       문을 두드린다. API 가 몇 ms 인가. 화면은 안 연다.
    `capture_screens.py` 화면을 **찍는다**. 한 장이 떴는지 단언한다.
    `walk_scenarios.py`  화면을 **걷는다**. 길이 이어지는가를 잰다.
    이 도구             화면을 **부순다**. 500·503·403·타임아웃을 주입하고,
                        빈 응답을 주입하고, 폼에 틀린 값을 넣는다 —
                        그리고 **화면이 그것을 사람의 말로 그리는가**를 잰다.

상용점검 §4 의 56칸 중 「오류 흐름」·「빈 상태」·「폼」 세 열은 위 셋 중 어느 것도
누르지 않는다. 없는 도구의 결과를 표에 적을 수 없어서 그 칸들이 비어 있었다.

★ **주입은 브라우저 안에서 끝난다.** Playwright 의 요청 가로채기는 요청이 네트워크로
  나가기 **전에** 가짜 응답을 돌려준다 — 서버는 그 요청을 본 적이 없다. 그래서 이
  도구는 8000 번 게이트 서버를 **오염시키지 않는다.** 그 사실을 우연에 맡기지 않고
  `_install_write_guard()` 로 **구조적으로** 못 박는다: 로그인·로그아웃을 뺀 모든
  비-GET `/api/` 요청은 네트워크에 닿기 전에 막힌다. 포트를 옮기는 것보다 이쪽이 세다 —
  포트는 사람이 틀릴 수 있지만 이 가드는 코드가 지킨다.

★ **시나리오 이름을 새로 짓지 않는다** — `perf_load.SCENARIOS` 에서 빌린다 (D-212).
★ **표를 새로 짓지 않는다** — 정본은 `docs/design/REVIEW_상용점검_사용자관점_20260905_TC.md`
  §4 이고, 행 8 · 열 7 · 이름을 그대로 쓴다.

⚠ **빈칸을 채우려고 초록을 만들지 않는다** (D-327). 못 쟀으면 `null` 로 내고,
  판정기는 `null` 을 **통과로 세지 않는다**. 회색은 초록이 아니다 (D-301).

    docker exec gx-shell python /repo/scripts/walk_states.py \
        --user gxprobe_q --password **** --json-out /docs/agent/evidence/P-69/states.json
    python scripts/walk_states.py --self-test        # 판정 규칙만 (브라우저 없이)

종료 코드: 0 눌렀고 통과 · 1 눌렀고 실패 · 2 **못 눌렀다**(환경 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

TAG = "[STATES]"
ROOT = Path(__file__).resolve().parent.parent

#: 데스크톱 · 모바일 두 폭. 「모바일 390」 열은 **390 에서 실제로 눌렀을 때만** 찬다.
DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}

#: DA-03 §4-3 — 화면이 스스로 정한 로딩 상한. 타임아웃 주입은 이보다 **길게** 끈다.
LOAD_TIMEOUT_MS = 10_000
TIMEOUT_INJECT_MS = 13_000


def _scenario_names() -> dict:
    """S1·S2·S3 의 이름을 **`perf_load` 에서 가져온다.** 여기서 다시 짓지 않는다 (D-212)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from perf_load import SCENARIOS

    return {k: SCENARIOS[k]["name"] for k in ("S1", "S2", "S3")}


# ═══════════════════════════════════════════════════════════════════════════
# 정본 표 — **행 이름을 그대로 쓴다.** 여기서 이름을 지으면 표가 둘이 된다 (D-212)
# ═══════════════════════════════════════════════════════════════════════════
#: `docs/design/REVIEW_상용점검_사용자관점_20260905_TC.md` §4 의 행 8 · 열 7.
CANON_ROWS = ("로그인", "지금 처리할 것", "이벤트 목록", "이벤트 상세",
              "관리·설정", "카메라 일괄 등록", "모바일 M1~M3", "보고서")
CANON_COLS = ("화면", "주요 버튼", "메뉴·링크", "폼(검증·오류)",
              "오류 흐름(500·503·403·타임아웃)", "빈 상태", "모바일 390")
#: 원표가 「—」로 둔 자리. **내가 정한 것이 아니다** — 원표를 읽어서 옮긴다.
CANON_NA = {
    ("로그인", "메뉴·링크"), ("로그인", "빈 상태"), ("로그인", "모바일 390"),
    ("이벤트 상세", "폼(검증·오류)"), ("이벤트 상세", "모바일 390"),
    ("카메라 일괄 등록", "메뉴·링크"), ("보고서", "폼(검증·오류)"),
}

#: 화면 한 장이 무엇으로 이루어지나. `see` 는 **그 화면에만 있는 글자**다 —
#: 공통 글자로 단언하면 안 움직여도 초록이 된다 (`capture_screens` 가 배운 함정).
#: ★ `api` 는 **정찰로 확인한다.** 여기 적은 것은 씨앗이고, 화면이 실제로 부른
#:   것과 다르면 정찰이 그 사실을 적는다 — 하드코딩한 경로가 낡는 자리다.
SCREENS: dict[str, dict] = {
    "로그인": {
        "route": "/login", "see": None, "needs_login": False,
        "api": "/api/v1/auth/login",
        # 로그인은 폼이 본체다. 빈 값·틀린 값을 넣는다.
        "form": {"kind": "login"},
    },
    "지금 처리할 것": {
        "route": "/dsm/queue", "see": "지금 처리할 것 — 가장 급한 하나",
        "api": "/api/dsm/events/queue",
        "empty_body": {"items": [], "top": None, "total": 0},
    },
    "이벤트 목록": {
        "route": "/dsm/events", "see": "이벤트 목록",
        "api": "/api/dsm/events",
        "empty_body": {"items": [], "total": 0},
    },
    "이벤트 상세": {
        "route": None, "see": "이벤트 상세",      # 목록에서 한 건을 열어 도달한다
        "api": "/api/dsm/events/",
        "reach": "from_list",
    },
    "관리·설정": {
        "route": "/dsm/drill", "see": "훈련 모드",
        "api": "/api/dsm/drill",
        "empty_body": {"enabled": False, "sessions": []},
    },
    "카메라 일괄 등록": {
        "route": "/dsm/cameras/import", "see": "카메라 일괄 등록 — 표를 먼저 봅니다",
        "api": "/api/dsm/cameras/address-gap",
        "form": {"kind": "csv"},
    },
    "모바일 M1~M3": {
        "route": "/m/inbox", "see": "내게 온 이벤트",
        "api": "/api/dsm/events",
        "empty_body": {"items": [], "total": 0},
        "mobile_only": True,
    },
    "보고서": {
        "route": "/report-template", "see": None,
        "api": None,                               # **정찰이 찾는다** — 인수 화면이다
        "recon_api": True,
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# GX-COPY — **오류 원문이 화면에 뜨면 빨강이다**
# ═══════════════════════════════════════════════════════════════════════════
#: 사전(`docs/design/GX-COPY_v1.md` §4 · `scripts/verify_ui_copy.PATTERNS`)이 이름으로
#: 금지한 것들. 저기는 **소스**를 보고 여기는 **화면에 실제로 뜬 글자**를 본다 —
#: 같은 사전의 다른 쪽 끝이다. 소스에 없어도 **서버가 준 문장이 그대로 그려지면**
#: 여기서만 걸린다. 그 자리가 정확히 `StateBoundary` 의 `description={reason}` 이다.
RAW_ERROR_MARKERS: tuple[tuple[str, str], ...] = (
    ("Network Error", "axios 원문 — GX-COPY 출생 표본 그 자체다"),
    ("Request failed with status code", "axios 원문"),
    ("AxiosError", "예외 클래스 이름"),
    ("Internal Server Error", "서버 원문(영문)"),
    ("Traceback (most recent call last)", "파이썬 역추적이 화면에 떴다"),
    ("<!DOCTYPE", "HTML 오류 페이지가 본문으로 그려졌다"),
    ("[object Object]", "객체를 문자열로 그렸다 — 사유가 통째로 사라진 자리"),
    ("ECONNREFUSED", "OS 오류 코드"),
    ("status_code", "봉투 내부 필드 이름"),
    ("xhr poll error", "전송 계층 원문"),
    ("is not a function", "자바스크립트 예외가 본문에 그려졌다"),
    ("undefined", "정의되지 않은 값이 사람의 자리에 그려졌다"),
)
#: 대장 언어(절 ID · 결정 번호 · 백틱 · 내부 경로)가 **화면 본문**에 있는가.
#: `verify_ui_copy.PATTERNS` 와 같은 뜻이고, 여기서는 렌더된 글자에 건다.
LEDGER_PATTERNS: tuple[tuple[str, str], ...] = (
    ("결정 번호", r"D-\d{3}(?!\d)"),
    ("절 ID", r"\b(?:UX|SEC|OPS|QA|LAW|PERF|ISO|AC|FR|NFR|DA)-\d{1,2}\b"),
    ("백틱", r"`"),
    ("마크다운 강조", r"\*\*"),
    ("출처 칩", r"data_source\s*="),
    ("내부 경로", r"(?:scripts/|backend/|frontend/src)"),
)
LEDGER_COMPILED = tuple((n, re.compile(rx)) for n, rx in LEDGER_PATTERNS)

#: 「오류 + 다시 시도」를 그렸다고 말할 수 있는 글자. `StateBoundary` 가 그리는 말이다.
ERROR_AFFORDANCE = ("불러오지 못했습니다", "다시 시도")
FORBIDDEN_AFFORDANCE = ("권한이 없습니다",)
#: 로딩이 고착됐는가 — antd `Skeleton` 이 남아 있으면 스피너 고착이다.
SPINNER_SELECTOR = ".ant-skeleton-active, .ant-spin-spinning"


def scan_raw_error(text: str) -> list:
    """화면에 뜬 글자에서 **오류 원문**과 **대장 언어**를 찾는다."""
    hits = []
    for token, why in RAW_ERROR_MARKERS:
        if token in text:
            hits.append(f"「{token}」 — {why}")
    for name, rx in LEDGER_COMPILED:
        m = rx.search(text)
        if m:
            hits.append(f"{name} 「{m.group(0)}」 — 사용자 본문에 대장 언어")
    return hits


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **순수 함수다** (D-277). 자기시험이 합성 입력을 먹인다
# ═══════════════════════════════════════════════════════════════════════════
def judge_error_probe(probe: dict | None) -> tuple:
    """오류 주입 한 건의 판정 → `(통과?, 사유)`. `None` 은 **못 쟀다**(통과 아님)."""
    if probe is None:
        return None, "**못 쟀다**"
    if probe.get("undecidable"):
        return None, f"**못 쟀다** — {probe.get('why', '')}"
    mode = probe.get("mode", "?")
    body = probe.get("body_text") or ""
    bad = []
    # ① 빈 화면이 아니어야 한다. **아무것도 안 그린 화면이 가장 나쁜 오류 화면이다.**
    if len(body.strip()) < 20:
        bad.append(f"**빈 화면이다**(본문 {len(body.strip())}자) — 사용자는 무엇이 "
                   f"일어났는지 알 수 없다")
    # ② 오류(또는 권한없음)를 말해야 한다.
    want = FORBIDDEN_AFFORDANCE if mode == "403" else ERROR_AFFORDANCE
    if not any(w in body for w in want):
        bad.append(f"「{' · '.join(want)}」 중 어느 것도 화면에 없다 — "
                   f"화면이 실패를 **말하지 않았다**")
    # ③ 스피너 고착 0.
    if probe.get("spinner_stuck"):
        bad.append("**스피너가 고착됐다** — 영원한 로딩은 「기다리는 중」으로 보이지만 "
                   "사용자는 아무것도 모른다 (DA-03 §4-3)")
    # ④ 오류 원문 노출 0 (GX-COPY).
    raw = probe.get("raw_hits") or []
    if raw:
        bad.append("**오류 원문이 화면에 떴다** (GX-COPY): " + " · ".join(raw[:3]))
    return (not bad), ("; ".join(bad) if bad else
                       f"{mode} 주입 → 오류 문구 + 다시 시도 · 원문 노출 0 · 스피너 0")


def judge_empty_probe(probe: dict | None) -> tuple:
    """빈 상태 한 건. **「빈」과 「오류」가 다른 문구여야 한다.**"""
    if probe is None:
        return None, "**못 쟀다**"
    if probe.get("undecidable"):
        return None, f"**못 쟀다** — {probe.get('why', '')}"
    body = probe.get("body_text") or ""
    bad = []
    if len(body.strip()) < 20:
        bad.append(f"**빈 화면이다**(본문 {len(body.strip())}자)")
    # ★ 빈 상태에 **오류 문구가 뜨면 빨강**이다 — 성공한 0건을 고장으로 그린 것이다.
    if any(w in body for w in ERROR_AFFORDANCE):
        bad.append("빈 상태인데 **오류 문구**를 그린다 — 요청은 성공했고 0건이다. "
                   "「없다」와 「못 가져왔다」가 같아 보이면 사용자가 잘못 읽는다 "
                   "(DA-03 §2-5)")
    if not (probe.get("empty_text") or "").strip():
        bad.append("빈 상태를 말하는 문구가 **없다** — 화면이 0건을 침묵으로 그렸다")
    if probe.get("raw_hits"):
        bad.append("빈 상태에 원문 노출: " + " · ".join(probe["raw_hits"][:3]))
    # ★ 「빈」과 「오류」의 문구가 **같으면** 빨강. 이것이 이 절의 핵심 단언이다.
    same = probe.get("same_as_error")
    if same is True:
        bad.append("**빈 문구와 오류 문구가 같다** — 둘을 같은 그림으로 그리면 "
                   "사용자가 「없구나」로 읽고, 실제로는 못 가져온 것이다")
    return (not bad), ("; ".join(bad) if bad else
                       f"빈 문구 「{(probe.get('empty_text') or '')[:40]}」 · "
                       f"오류와 다른 문구 · 원문 0")


def judge_form_probe(probe: dict | None) -> tuple:
    """폼 한 건 — 필수 빈값 · 형식 오류 · 서버 거절(422) · **이중 제출 0**."""
    if probe is None:
        return None, "**못 쟀다**"
    if probe.get("undecidable"):
        return None, f"**못 쟀다** — {probe.get('why', '')}"
    bad = []
    for key, label in (("required", "필수 빈값"), ("format", "형식 오류"),
                       ("reject422", "서버 거절(422)")):
        case = probe.get(key)
        if case is None:
            continue                       # 이 폼에 없는 갈래 — 없는 것을 빨강으로 세지 않는다
        if not case.get("message_shown"):
            bad.append(f"**{label}**: 칸 옆에 문구가 뜨지 않았다")
        if case.get("raw_hits"):
            bad.append(f"{label}: 원문 노출 " + " · ".join(case["raw_hits"][:2]))
    # ★ **이중 제출 0** — 저장을 두 번 눌렀을 때 요청이 두 번 나가면 빨강이다.
    dbl = probe.get("double_submit")
    if dbl is not None and dbl.get("requests", 0) > 1:
        bad.append(f"**이중 제출**: 빠르게 두 번 눌렀더니 요청이 "
                   f"{dbl['requests']}번 나갔다 — 저장 버튼이 잠기지 않는다")
    return (not bad), ("; ".join(bad) if bad else "필수·형식·거절 문구 표시 · 이중 제출 0")


def judge(result: dict) -> list:
    """표 전체의 판정 `(이름, 통과, 사유)`. **`None` 은 못 쟀다이지 통과가 아니다.**"""
    out: list = []
    screens = result.get("screens") or {}

    if not screens:
        out.append(("화면을 눌렀다", False, "**못 눌렀다** — 결과가 없다"))
        return out

    # ── 오류 흐름 ─────────────────────────────────────────────────────────
    err_rows = [(name, mode, judge_error_probe(p))
                for name, s in screens.items()
                for mode, p in (s.get("errors") or {}).items()]
    red = [(n, m, w) for (n, m, (ok, w)) in err_rows if ok is False]
    gray = [(n, m) for (n, m, (ok, _)) in err_rows if ok is None]
    green = [1 for (_n, _m, (ok, _)) in err_rows if ok is True]
    out.append(("오류 흐름 — 빈 화면이 아니라 「오류 + 다시 시도」", not red,
                f"주입 {len(err_rows)}건 · 통과 {len(green)} · 못 쟀다 {len(gray)}"
                + ("" if not red else " — 빨강 " + json.dumps(
                    [f"{n}/{m}: {w}" for n, m, w in red],
                    ensure_ascii=False)[:600])))

    # ── 빈 상태 ───────────────────────────────────────────────────────────
    emp_rows = [(name, judge_empty_probe(s.get("empty")))
                for name, s in screens.items() if s.get("empty") is not None]
    ered = [(n, w) for (n, (ok, w)) in emp_rows if ok is False]
    out.append(("빈 상태 — 「빈」과 「오류」가 다른 문구", not ered,
                f"{len(emp_rows)}화면"
                + ("" if not ered else " — 빨강 " + json.dumps(
                    [f"{n}: {w}" for n, w in ered], ensure_ascii=False)[:500])))

    # ── 폼 ────────────────────────────────────────────────────────────────
    frm_rows = [(name, judge_form_probe(s.get("form")))
                for name, s in screens.items() if s.get("form") is not None]
    fred = [(n, w) for (n, (ok, w)) in frm_rows if ok is False]
    out.append(("폼 — 문구 표시 · 이중 제출 0", not fred,
                f"{len(frm_rows)}폼"
                + ("" if not fred else " — 빨강 " + json.dumps(
                    [f"{n}: {w}" for n, w in fred], ensure_ascii=False)[:500])))

    # ── 서버를 오염시키지 않았다 ──────────────────────────────────────────
    blocked = result.get("blocked_writes")
    if blocked is None:
        out.append(("서버에 쓰지 않았다", False, "**못 쟀다** — 쓰기 가드가 안 걸렸다"))
    else:
        out.append(("서버에 쓰지 않았다", True,
                    f"비-GET /api/ 요청 {len(blocked)}건을 네트워크 앞에서 막았다 "
                    f"(로그인·로그아웃만 통과)"))

    closed = result.get("session_closed")
    out.append(("세션을 닫았다", bool(closed),
                "세션 자물쇠를 풀었다 (capture_screens._release_session)" if closed
                else "**세션이 열린 채다.** 이 환경은 동시 접속 1개다 — "
                     "물고 있으면 다음 차선이 로그인 창에서 막힌다"))

    names = result.get("names_from_perf_load")
    out.append(("시나리오 이름을 빌려 왔다", bool(names),
                f"perf_load.SCENARIOS ← {names}" if names else
                "**이름을 못 가져왔다** — 새로 지으면 표가 둘이 된다 (D-212)"))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 56칸 — **정본 표의 칸에 자동 기입한다.** 새 표를 짓지 않는다
# ═══════════════════════════════════════════════════════════════════════════
def to_cells(result: dict) -> dict:
    """`{행: {열: {"mark": ●|◐|""|—, "note": 사유}}}`.

    ★ 세는 규칙: `●` 전부 눌렀다 · `◐` 일부 · 빈칸 안 눌렀다 · `—` 해당 없음.
      **N/56 은 ●+◐ 만 센다.** 「—」를 채움으로 세면 표가 저절로 차오른다.
    ★ **못 쟀으면 빈칸이다.** 판정이 `None` 인 것을 `◐` 로 올리지 않는다 (D-327).
    """
    cells: dict = {r: {c: {"mark": "", "note": ""} for c in CANON_COLS}
                   for r in CANON_ROWS}
    for (r, c) in CANON_NA:
        cells[r][c] = {"mark": "—", "note": "원표가 「—」로 둔 자리"}

    screens = result.get("screens") or {}
    for row in CANON_ROWS:
        s = screens.get(row)
        if not s:
            continue

        # ── 화면 ──────────────────────────────────────────────────────────
        if s.get("reached"):
            widths = s.get("widths") or []
            mark = "●" if len(widths) >= 2 or s.get("mobile_only") else "◐"
            cells[row]["화면"] = {
                "mark": mark,
                "note": f"{s.get('route') or '(목록에서 열었다)'} 를 "
                        f"{'·'.join(str(w) for w in widths)}px 에서 열었다"
                        + ("" if mark == "●" else " — 한 폭만 열었다")}
        elif s.get("reach_error"):
            cells[row]["화면"] = {"mark": "", "note": f"못 열었다 — {s['reach_error']}"}

        # ── 오류 흐름 ─────────────────────────────────────────────────────
        errs = s.get("errors") or {}
        if errs and cells[row]["오류 흐름(500·503·403·타임아웃)"]["mark"] != "—":
            judged = {m: judge_error_probe(p) for m, p in errs.items()}
            pressed = [m for m, (ok, _) in judged.items() if ok is not None]
            missed = [m for m, (ok, _) in judged.items() if ok is None]
            reds = [f"{m}({w})" for m, (ok, w) in judged.items() if ok is False]
            if pressed:
                # 원표가 이름으로 요구한 넷을 다 눌렀는가.
                mark = ("●" if set(pressed) >= {"500", "503", "403", "timeout"}
                        else "◐")
                note = f"눌렀다 {'·'.join(pressed)}"
                if missed:
                    note += f" / 못 눌렀다 {'·'.join(missed)}"
                if reds:
                    note += " — **빨강** " + "; ".join(reds)[:300]
                else:
                    note += " — 전부 「오류 + 다시 시도」 · 원문 0 · 스피너 0"
                cells[row]["오류 흐름(500·503·403·타임아웃)"] = {"mark": mark,
                                                                 "note": note}

        # ── 빈 상태 ───────────────────────────────────────────────────────
        emp = s.get("empty")
        if emp is not None and cells[row]["빈 상태"]["mark"] != "—":
            ok, why = judge_empty_probe(emp)
            if ok is not None:
                cells[row]["빈 상태"] = {
                    "mark": "◐",       # ★ **빈 테넌트가 아니라 빈 응답 주입이다** — 일부다
                    "note": f"빈 200 응답을 주입해 쟀다(빈 테넌트로 잰 것이 아니다) — "
                            f"{'통과' if ok else '**빨강** ' + why}"}

        # ── 폼 ────────────────────────────────────────────────────────────
        frm = s.get("form")
        if frm is not None and cells[row]["폼(검증·오류)"]["mark"] != "—":
            ok, why = judge_form_probe(frm)
            if ok is not None:
                pressed = [k for k in ("required", "format", "reject422")
                           if frm.get(k) is not None]
                label = {"required": "필수 빈값", "format": "형식 오류",
                         "reject422": "서버 거절(422)"}
                mark = "●" if len(pressed) >= 3 else "◐"
                cells[row]["폼(검증·오류)"] = {
                    "mark": mark,
                    "note": f"눌렀다 {'·'.join(label[k] for k in pressed)}"
                            + (f" · 이중 제출 {frm['double_submit']['requests']}회"
                               if frm.get("double_submit") else "")
                            + (" — 통과" if ok else " — **빨강** " + why)}

        # ── 모바일 390 ────────────────────────────────────────────────────
        if 390 in (s.get("widths") or []) and cells[row]["모바일 390"]["mark"] != "—":
            cells[row]["모바일 390"] = {
                "mark": "●", "note": "390×844 에서 열고 위 갈래를 눌렀다"}

        # ── 주요 버튼 — ★ **세는 것은 누르는 것이 아니다.** 빈칸으로 둔다 ──────
        #   [스스로 잡은 부풀리기 · 2026-09-06] 처음에는 「보이는 단추 N개」를 셌다고
        #   `◐` 를 줬다. 세는 규칙은 `◐` 를 **「일부만 눌렀다」**로 정의한다 — 한 번도
        #   안 누른 칸에 `◐` 를 주면 **표가 저절로 차오르고**(D-327) 그 수는 「눌러
        #   봤다」로 읽힌다. 목록은 다음 사람에게 쓸모가 있으므로 **사유로만** 남기고,
        #   칸은 **빈칸**이다. 이 도구는 쓰기 가드 때문에 쓰기 단추를 누르지 않는다.
        inv = s.get("buttons")
        if inv and cells[row]["주요 버튼"]["mark"] == "":
            names = [b for b in inv if b]
            if names:
                cells[row]["주요 버튼"] = {
                    "mark": "",
                    "note": f"**안 눌렀다** — 이 도구는 세기만 한다(쓰기 가드). "
                            f"보이는 단추 {len(names)}개: "
                            + ", ".join(f"「{n}」" for n in names[:8])}
    return cells


def count_cells(cells: dict) -> dict:
    full = sum(1 for r in cells for c in cells[r] if cells[r][c]["mark"] == "●")
    part = sum(1 for r in cells for c in cells[r] if cells[r][c]["mark"] == "◐")
    na = sum(1 for r in cells for c in cells[r] if cells[r][c]["mark"] == "—")
    blank = sum(1 for r in cells for c in cells[r] if cells[r][c]["mark"] == "")
    return {"full": full, "partial": part, "na": na, "blank": blank,
            "counted": full + part, "total": len(CANON_ROWS) * len(CANON_COLS)}


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **양성과 음성을 함께** (D-277 · D-350)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    bad: list = []

    good_err = {"mode": "500", "body_text": "불러오지 못했습니다. 다시 시도" + "x" * 30,
                "spinner_stuck": False, "raw_hits": []}
    ok, _ = judge_error_probe(good_err)
    if not ok:
        bad.append("「오류 + 다시 시도」를 그린 화면을 통과로 못 읽는다")

    # ── ★★ **출생 표본** (D-310) — 이 도구를 만들게 한 바로 그 모양들 ────────
    #   ㉠ 500 을 맞고 **빈 화면**이 된다  ㉡ 스피너가 영원히 돈다
    #   ㉢ `Network Error` 가 사용자 자리에 뜬다 (GX-COPY 출생 표본 그 자체)
    if judge_error_probe({"mode": "500", "body_text": "", "spinner_stuck": False,
                          "raw_hits": []})[0]:
        bad.append("**출생 표본 ㉠** — 500 에 **빈 화면**인데 통과로 읽는다. "
                   "아무것도 안 그린 화면이 가장 나쁜 오류 화면이다")
    if judge_error_probe({"mode": "500", "body_text": "불러오지 못했습니다 다시 시도" * 3,
                          "spinner_stuck": True, "raw_hits": []})[0]:
        bad.append("**출생 표본 ㉡** — 스피너가 고착됐는데 통과로 읽는다")
    # ★ ㉠ 을 **혼자 세우는** 표본. 위의 빈 본문은 「오류 문구도 없다」로도 걸리므로
    #   빈 화면 검사가 지워져도 빨강이 유지된다 — 그러면 그 검사는 시험되지 않은
    #   채로 남는다(변이 시험에서 실제로 살아남았다 [실측 2026-09-06]). 오류 문구
    #   **만** 있고 그 밖에 아무것도 없는 화면은 ① 로만 걸려야 한다.
    if judge_error_probe({"mode": "500", "body_text": "다시 시도",
                          "spinner_stuck": False, "raw_hits": []})[0]:
        bad.append("**출생 표본 ㉠-단독** — 「다시 시도」 넉 자만 있고 그 밖에 아무것도 "
                   "없는 화면을 통과로 읽는다. 사용자는 무엇이 일어났는지 모른다")
    leak = judge_error_probe(
        {"mode": "500", "body_text": "불러오지 못했습니다 다시 시도 Network Error" * 2,
         "spinner_stuck": False,
         "raw_hits": scan_raw_error("Network Error")})
    if leak[0]:
        bad.append("**출생 표본 ㉢** — `Network Error` 가 화면에 떴는데 통과로 읽는다 "
                   "(GX-COPY 출생 표본)")

    # ── 403 은 「권한없음」으로 그려야 한다 — 오류와 한 칸에 두지 않는다 ────
    if judge_error_probe({"mode": "403", "body_text": "불러오지 못했습니다" * 5,
                          "spinner_stuck": False, "raw_hits": []})[0]:
        bad.append("403 인데 「권한이 없습니다」가 아니라 「불러오지 못했습니다」를 "
                   "통과로 읽는다 — 「고장」과 「내 권한이 아님」은 다른 칸이다")
    if not judge_error_probe({"mode": "403", "body_text": "이 항목에 대한 권한이 없습니다" * 2,
                              "spinner_stuck": False, "raw_hits": []})[0]:
        bad.append("403 에 「권한이 없습니다」를 그렸는데 빨강이다")

    # ── 빈 상태 ───────────────────────────────────────────────────────────
    if not judge_empty_probe({"body_text": "조건에 맞는 이벤트가 없습니다" * 2,
                              "empty_text": "조건에 맞는 이벤트가 없습니다",
                              "same_as_error": False, "raw_hits": []})[0]:
        bad.append("빈 문구를 제대로 그린 화면을 빨강으로 읽는다")
    if judge_empty_probe({"body_text": "불러오지 못했습니다 다시 시도" * 3,
                          "empty_text": "불러오지 못했습니다",
                          "same_as_error": True, "raw_hits": []})[0]:
        bad.append("**빈 상태에 오류 문구**를 그렸는데 통과로 읽는다 — "
                   "「없다」와 「못 가져왔다」가 같아진다 (DA-03 §2-5)")
    if judge_empty_probe({"body_text": "x" * 50, "empty_text": "",
                          "same_as_error": False, "raw_hits": []})[0]:
        bad.append("빈 상태를 **침묵**으로 그렸는데 통과로 읽는다")

    # ── 폼 · **이중 제출** ────────────────────────────────────────────────
    if not judge_form_probe({"required": {"message_shown": True},
                             "double_submit": {"requests": 1}})[0]:
        bad.append("필수 문구가 떴고 제출이 1회인데 빨강이다")
    if judge_form_probe({"required": {"message_shown": False}})[0]:
        bad.append("필수 빈값에 **문구가 안 떴는데** 통과로 읽는다")
    if judge_form_probe({"required": {"message_shown": True},
                         "double_submit": {"requests": 2}})[0]:
        bad.append("**이중 제출**(요청 2회)인데 통과로 읽는다 — 저장이 두 번 나간다")

    # ── **못 쟀다 ≠ 통과** (D-301) ────────────────────────────────────────
    for fn, label in ((judge_error_probe, "오류"), (judge_empty_probe, "빈"),
                      (judge_form_probe, "폼")):
        if fn(None)[0] is not None:
            bad.append(f"{label} 갈래에서 **못 쟀다**(None)를 참·거짓으로 읽는다")
        if fn({"undecidable": True, "why": "x"})[0] is not None:
            bad.append(f"{label} 갈래에서 판정불가를 참·거짓으로 읽는다")

    # ── 표 채우기 — **못 쟀으면 빈칸이다** ────────────────────────────────
    empty_cells = to_cells({"screens": {}})
    cnt = count_cells(empty_cells)
    if cnt["counted"] != 0:
        bad.append(f"아무것도 안 눌렀는데 {cnt['counted']}칸이 찼다 — "
                   f"**표가 저절로 차오른다** (D-327)")
    if cnt["total"] != 56:
        bad.append(f"정본 표가 56칸이 아니다({cnt['total']}) — 행 8 × 열 7 이어야 한다")
    if cnt["na"] != len(CANON_NA):
        bad.append(f"「—」 수가 원표와 다르다: {cnt['na']} ≠ {len(CANON_NA)}")

    # ★ **못 쟀다는 칸을 채우지 않는다** — 판정이 None 인 표본을 넣어 확인한다.
    undec = to_cells({"screens": {"이벤트 목록": {
        "reached": False, "reach_error": "화면이 안 떴다",
        "errors": {"500": {"undecidable": True, "why": "주입 못 했다"}},
        "empty": {"undecidable": True, "why": "x"}}}})
    if undec["이벤트 목록"]["오류 흐름(500·503·403·타임아웃)"]["mark"] != "":
        bad.append("**못 쟀다는 주입**으로 「오류 흐름」 칸을 채운다 (D-327)")
    if undec["이벤트 목록"]["빈 상태"]["mark"] != "":
        bad.append("**못 쟀다는 빈 상태**로 칸을 채운다")
    if undec["이벤트 목록"]["화면"]["mark"] != "":
        bad.append("화면을 **못 열었는데** 「화면」 칸을 채운다")

    # ★ 넷을 다 눌러야 `●` 다 — 셋만 누르면 `◐`.
    three = to_cells({"screens": {"이벤트 목록": {
        "reached": True, "route": "/dsm/events", "widths": [1440, 390],
        "errors": {m: {"mode": m, "body_text": "불러오지 못했습니다 다시 시도" * 3,
                       "spinner_stuck": False, "raw_hits": []}
                   for m in ("500", "503", "403")}}}})
    if three["이벤트 목록"]["오류 흐름(500·503·403·타임아웃)"]["mark"] != "◐":
        bad.append("500·503·403 **셋만** 눌렀는데 ● 로 센다 — 원표는 타임아웃까지 넷이다")
    four = to_cells({"screens": {"이벤트 목록": {
        "reached": True, "route": "/dsm/events", "widths": [1440, 390],
        "errors": {m: {"mode": m,
                       "body_text": ("이 항목에 대한 권한이 없습니다" if m == "403"
                                     else "불러오지 못했습니다 다시 시도") * 3,
                       "spinner_stuck": False, "raw_hits": []}
                   for m in ("500", "503", "403", "timeout")}}}})
    if four["이벤트 목록"]["오류 흐름(500·503·403·타임아웃)"]["mark"] != "●":
        bad.append("넷을 다 눌렀는데 ● 가 아니다")

    # ── ★ **세는 것은 누르는 것이 아니다** (스스로 잡은 부풀리기) ──────────
    counted_only = to_cells({"screens": {"보고서": {
        "reached": True, "route": "/report-template", "widths": [1440],
        "buttons": ["생성", "HWPX", "PDF"]}}})
    if counted_only["보고서"]["주요 버튼"]["mark"] != "":
        bad.append("단추를 **세기만 했는데** 「주요 버튼」 칸에 표를 준다 — "
                   "◐ 는 「일부만 **눌렀다**」이지 「보인다」가 아니다 (D-327)")
    if "안 눌렀다" not in counted_only["보고서"]["주요 버튼"]["note"]:
        bad.append("안 누른 칸의 사유에 **안 눌렀다**는 말이 없다")

    # ── 「—」를 덮어쓰지 않는다 ────────────────────────────────────────────
    na = to_cells({"screens": {"이벤트 상세": {
        "reached": True, "route": None, "widths": [1440],
        "form": {"required": {"message_shown": True}}}}})
    if na["이벤트 상세"]["폼(검증·오류)"]["mark"] != "—":
        bad.append("원표가 「—」로 둔 칸을 측정으로 **덮어썼다** — 해당 없음을 "
                   "채움으로 바꾸면 표가 저절로 차오른다")

    # ── 원문 탐지기 자체 ──────────────────────────────────────────────────
    if not scan_raw_error("어쩌구 Network Error 저쩌구"):
        bad.append("`Network Error` 를 못 찾는다 — GX-COPY 출생 표본이다")
    if not scan_raw_error("이것은 D-327 입니다"):
        bad.append("결정 번호를 화면 본문에서 못 찾는다")
    if scan_raw_error("조건에 맞는 이벤트가 없습니다. (요청은 성공했고 0건입니다)"):
        bad.append("**정상 한국어 문구를 원문 노출로 읽는다** — 태어나면서부터 "
                   "빨간 게이트는 다음 사람이 우회한다")

    # ── 행·열 이름이 정본과 같은가 ────────────────────────────────────────
    if len(CANON_ROWS) != 8 or len(CANON_COLS) != 7:
        bad.append("행 8 · 열 7 이 아니다 (D-212)")
    for row in SCREENS:
        if row not in CANON_ROWS:
            bad.append(f"「{row}」 는 정본 표에 없는 행 이름이다 — 표를 새로 지었다")

    if bad:
        print(f"{TAG} 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — **출생 표본 3**(빈 화면 · 스피너 고착 · Network Error) "
          f"· 403 갈래 2 · 빈 상태 3 · 폼 3 · 못 쟀다 6 · 표 채우기 7 · 원문 3 · 이름 2")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — 브라우저를 열고 **부순다**
# ═══════════════════════════════════════════════════════════════════════════
def _install_write_guard(context, api: str, blocked: list) -> None:
    """★ **서버를 오염시키지 않는다 — 구조로 못 박는다.**

    로그인·로그아웃을 뺀 모든 비-GET `/api/` 요청을 **네트워크에 닿기 전에** 막는다.
    이 도구는 단추를 누르고 폼을 제출하므로, 가드가 없으면 게이트 서버(8000)에
    실제 쓰기가 나간다 — 그러면 다른 차선의 게이트가 빨개진다.

    ⚠ 막은 요청에는 **가짜 409** 를 돌려준다. `abort` 로 끊으면 화면이 그것을
      「네트워크 오류」로 그리고, 그 빨강은 **내가 만든 것**이지 화면의 결함이 아니다 —
      그 둘을 섞으면 없는 버그로 다음 사람이 하루를 쓴다 (D-322).
    """
    allow = ("/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/auth/refresh")

    def handler(route):
        req = route.request
        if req.method == "GET" or any(a in req.url for a in allow):
            return route.continue_()
        blocked.append(f"{req.method} {req.url}"[:200])
        route.fulfill(status=409, content_type="application/json",
                      body=json.dumps({"message": "시험 도구가 막았습니다.",
                                       "status_code": 409}))

    context.route(f"{api}/api/**", handler)


def _login(page, web: str, user: str, password: str) -> None:
    """`walk_scenarios._login` 과 **같은 절차다.** 여기서 다시 짓지 않는다."""
    page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
    page.wait_for_timeout(2_000)
    fields = page.locator("input")
    if fields.count() < 2:
        raise RuntimeError("로그인 화면에 입력칸이 둘 미만이다 — 화면이 안 떴다")
    fields.nth(0).fill(user)
    fields.nth(1).fill(password)
    page.get_by_role("button", name="Log In").click()
    page.wait_for_timeout(3_000)
    confirm = page.get_by_role("button", name="Confirm")
    if confirm.count():
        confirm.first.click()
        page.wait_for_timeout(9_000)
    else:
        page.wait_for_timeout(6_000)
    if page.url.rstrip("/").endswith("/login"):
        raise RuntimeError(
            f"로그인 뒤에도 로그인 화면이다 ({page.url}) — "
            f"본문: {page.inner_text('body')[:200]!r}")


def _release_session(username: str) -> bool:
    """**세션 자물쇠를 푼다** — `capture_screens._release_session` 을 그대로 빌린다.

    ★ 여기서 다시 짓지 않는다 (D-369). 두 벌로 닫으면 한쪽이 조용히 아무것도 안 닫고,
      이 환경은 **동시 접속 1개**라 안 닫힌 세션 하나가 다음 차선을 통째로 막는다.

    ⚠ [실측 2026-09-06 · 턴 G] 처음에는 `walk_scenarios._logout` 처럼 브라우저의
      `localStorage.userInfo` 에서 토큰을 꺼내 `POST /auth/logout` 을 불렀다. **그
      자리에 토큰이 없다** — 이 앱은 토큰을 쿠키(`token`)로 들고 있고 `userInfo` 에는
      access_token 이 없다. 그래서 로그아웃이 **조용히 401 로 실패했고**, 세션이 물린
      채로 남아 다음 로그인이 「다른 기기 접속」 확인 창을 만났다. 그 창을 눌러도
      로그인이 완성되지 않아 **뒤따르는 측정이 전부 로그인 화면을 봤다.**
      → 「닫았다고 적혔는데 안 닫힌 것」이 가장 비싼 거짓 초록이다.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from capture_screens import _release_session as release

        release(username)
        return True
    except Exception as exc:                                    # noqa: BLE001
        print(f"{TAG} ⚠ 세션을 못 풀었다: {type(exc).__name__}: {exc}", flush=True)
        return False


def _visible_text(page) -> str:
    try:
        return page.inner_text("body")
    except Exception:                                           # noqa: BLE001
        return ""


def _spinner_stuck(page) -> bool:
    try:
        return page.locator(SPINNER_SELECTOR).count() > 0
    except Exception:                                           # noqa: BLE001
        return False


def _button_names(page) -> list:
    """화면에 **보이는** 단추의 이름. 세기만 하고 누르지 않는다."""
    out: list = []
    try:
        loc = page.get_by_role("button")
        for i in range(min(loc.count(), 30)):
            try:
                b = loc.nth(i)
                if b.is_visible():
                    name = (b.inner_text() or "").strip().replace("\n", " ")
                    if name and name not in out:
                        out.append(name[:30])
            except Exception:                                   # noqa: BLE001
                continue
    except Exception:                                           # noqa: BLE001
        return out
    return out


def _goto(page, web: str, route: str, see: str | None) -> tuple:
    """그 주소로 간다 → `(도달?, 사유)`."""
    try:
        page.goto(f"{web}{route}", wait_until="networkidle", timeout=45_000)
        page.wait_for_timeout(3_000)
        body = _visible_text(page)
        if page.url.rstrip("/").endswith("/login") and not route.endswith("/login"):
            return False, "로그인 화면으로 튕겼다 — 세션을 빼앗겼을 수 있다"
        if see and see not in body:
            return False, f"「{see}」 가 화면에 없다 — 본문: {body[:160]!r}"
        return True, ""
    except Exception as exc:                                    # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"[:200]


#: 주입 네 갈래. **원표가 이름으로 요구한 것 그대로다** — 500·503·403·타임아웃.
#: ★ `netfail` 은 **연결 자체가 안 되는 경우**다 — 원표가 로그인 행에 「서버 다운」으로
#:   적어 둔 자리이고, `500` 처럼 본문이 있는 오류와 **다른 코드 길**을 지난다:
#:   응답 본문이 없으므로 화면은 axios 의 원문(`Network Error`)까지 밀려난다.
#:   그 자리가 GX-COPY 출생 표본이 태어난 곳이므로 반드시 따로 누른다.
INJECT_MODES = ("500", "503", "403", "timeout", "netfail")


def _inject(context, api: str, api_path: str, mode: str) -> None:
    """`api_path` 를 부르는 요청에 **가짜 응답**을 돌려준다.

    ★ 요청은 네트워크로 **나가지 않는다** — 서버는 이 요청을 본 적이 없다.
      그래서 이 시험은 8000 을 오염시키지 않는다.

    ⚠⚠ **타임아웃 주입은 첫 요청 하나만 끈다** [실측 2026-09-06 · 턴 G].
      처음에는 걸리는 요청마다 13초를 잤다. 그런데 ㉠ 동기 API 의 라우트 처리기는
      **파이썬 쪽 디스패처를 막고**, ㉡ 화면은 `useDsmResource(refreshMs)` 로 스스로
      다시 부른다. 둘이 겹치면 잠자는 요청이 **끝없이 쌓여** 도구가 영영 안 끝난다 —
      한 화면에서 10분을 태우고 아무것도 못 쟀다. 그래서 **첫 요청만 실제로 끌고**,
      뒤따르는 것들은 곧바로 504 로 끊는다. 재려는 것은 「화면이 자기 상한(10초)을
      넘겼을 때 오류로 전이하는가」이고, 그 물음에는 **한 번 끄는 것으로 충분하다.**
    """
    state = {"stalled": False}

    def handler(route):
        if mode == "netfail":
            # 서버가 아예 없는 경우. **가짜 응답조차 주지 않는다.**
            route.abort("connectionrefused")
            return
        if mode == "timeout":
            if not state["stalled"]:
                state["stalled"] = True
                # 화면이 정한 상한(10초)보다 **길게** 끈다 → 스스로 오류로 전이해야 한다.
                time.sleep(TIMEOUT_INJECT_MS / 1000.0)
                route.fulfill(status=200, content_type="application/json", body="{}")
                return
            # 뒤따르는 재요청은 **즉시** 끊는다 — 여기서 또 자면 도구가 안 끝난다.
            route.fulfill(status=504, content_type="application/json",
                          body=json.dumps({"status_code": 504}))
            return
        status = int(mode)
        route.fulfill(status=status, content_type="application/json",
                      body=json.dumps({"status_code": status}))

    context.route(f"**{api_path}**", handler)


def _read_twice(page, late_ms: int) -> tuple:
    """**이르게 한 번, 늦게 한 번** 읽는다 → `(판정에 쓸 본문, 이른 본문, 늦은 본문)`.

    ⚠ [실측 2026-09-06 · 턴 G] 오류를 **토스트**로 띄우는 화면은 몇 초 뒤 그 줄이
      사라진다. 늦게 한 번만 읽으면 도구는 「화면이 실패를 말하지 않았다」고 적는데,
      사실은 **말했다가 지웠다.** 둘은 다른 결함이고 다르게 고친다 — 그래서 둘 다 읽고
      **말한 적이 있으면 그 본문으로 판정**하되, 사라졌다는 사실은 따로 적는다.
    """
    page.wait_for_timeout(1_500)
    early = _visible_text(page)
    page.wait_for_timeout(max(late_ms - 1_500, 500))
    late = _visible_text(page)
    said_early = any(w in early for w in ERROR_AFFORDANCE + FORBIDDEN_AFFORDANCE)
    said_late = any(w in late for w in ERROR_AFFORDANCE + FORBIDDEN_AFFORDANCE)
    return (early if (said_early and not said_late) else late), early, late


def _probe_errors(context, page, web: str, api: str, name: str, spec: dict) -> dict:
    """한 화면에 네 갈래를 차례로 주입한다."""
    out: dict = {}
    api_path = spec.get("api")
    if not api_path:
        return {m: {"undecidable": True, "why": "이 화면이 부르는 API 를 못 찾았다"}
                for m in INJECT_MODES}
    for mode in INJECT_MODES:
        started = time.perf_counter()
        try:
            _inject(context, api, api_path, mode)
            ok, why = _goto(page, web, spec["route"], None)
            # 타임아웃 갈래는 화면이 상한을 넘긴 뒤 오류로 바뀔 때까지 더 기다린다.
            # (첫 요청이 13초를 끌므로 `goto` 자체가 이미 그만큼 기다린 뒤다.)
            body, early, late = _read_twice(page, 4_000 if mode != "timeout"
                                            else 6_000)
            base = spec.get("baseline_body") or ""
            if base and body.strip() == base.strip():
                # ★ **주입이 화면에 닿지 않았다.** 같은 본문을 「잘 그렸다」로 세면
                #   아무것도 안 눌러 놓고 초록을 얻는다 (D-327).
                out[mode] = {
                    "undecidable": True,
                    "why": f"주입해도 본문이 기준선과 **한 글자도 다르지 않다** — "
                           f"이 화면은 `{api_path}` 의 실패에 반응하지 않는다(또는 "
                           f"그 자리를 안 부른다). 「오류를 잘 그렸다」로 셀 수 없다"}
            else:
                out[mode] = {
                    "mode": mode, "body_text": body[:4000],
                    "spinner_stuck": _spinner_stuck(page),
                    "raw_hits": scan_raw_error(body),
                    "vanished": bool(
                        any(w in early for w in ERROR_AFFORDANCE + FORBIDDEN_AFFORDANCE)
                        and not any(w in late for w in
                                    ERROR_AFFORDANCE + FORBIDDEN_AFFORDANCE)),
                    "url": page.url,
                }
            if not ok and "튕겼다" in why:
                out[mode] = {"undecidable": True, "why": why}
        except Exception as exc:                                # noqa: BLE001
            out[mode] = {"undecidable": True,
                         "why": f"{type(exc).__name__}: {exc}"[:200]}
        finally:
            try:
                context.unroute(f"**{api_path}**")
            except Exception:                                   # noqa: BLE001
                pass
            print(f"{TAG}   · {name} / {mode} 주입 "
                  f"{time.perf_counter() - started:.0f}s", flush=True)
    return out


def empty_like(real):
    """**실제 응답에서 「0건」을 만든다** — 모양을 지어내지 않는다.

    ⚠⚠ [실측 2026-09-06 · 턴 G] 처음에는 빈 응답의 모양을 **손으로 적었다**
      (`{"items": [], "top": null, "total": 0}`). 그런데 `/api/dsm/events/queue` 의
      실제 계약은 `{now, total_events, card_total, sample_capped, window_seconds,
      tier_thresholds_sec, focus, queue}` 였다. 없는 칸을 읽은 화면이 그 자리에서
      **터졌고**(`Cannot read properties of undefined (reading 'length')`), 도구는
      그것을 「빈 상태가 빨강」으로 적었다. **그 빨강은 화면의 결함이 아니라 내가
      먹인 거짓 모양이었다** — 지어낸 입력은 지어낸 결함을 만든다(D-322).

    그래서 모양을 **화면이 방금 받은 진짜 응답에서** 가져온다: 배열은 비우고,
    개수를 뜻하는 수는 0으로 내리고, **그 밖의 칸은 건드리지 않는다.**
    """
    if isinstance(real, list):
        return []
    if not isinstance(real, dict):
        return real
    out = {}
    for k, v in real.items():
        low = k.lower()
        if isinstance(v, list):
            #: 배열이라고 다 목록은 아니다 — 임계값 같은 **설정 배열**은 비우면
            #: 화면이 또 터진다. 이름으로 가른다.
            out[k] = v if ("threshold" in low or "tier" in low) else []
        elif isinstance(v, bool):
            out[k] = v
        elif isinstance(v, (int, float)) and any(
                t in low for t in ("total", "count", "_n", "num")):
            out[k] = 0
        elif isinstance(v, dict):
            out[k] = empty_like(v)
        else:
            out[k] = v
    #: 「가장 급한 하나」처럼 **최상위 한 건**을 담는 칸은 0건이면 없는 것이 맞다.
    for k in ("focus", "top", "highlight"):
        if k in out:
            out[k] = None
    return out


def _probe_empty(context, page, web: str, api: str, name: str, spec: dict,
                 error_body: str) -> dict | None:
    """**성공한 0건**을 주입한다 — 200 에 빈 목록.

    ⚠ 이것은 **빈 테넌트가 아니다.** 빈 테넌트로 재려면 카메라 0·이벤트 0·규칙 0 인
      테넌트가 있어야 하는데, 이 저장소의 대장에 그런 테넌트가 없고 **만들면 대장에
      없는 테넌트가 생긴다.** 그래서 화면의 빈 갈래를 **응답으로** 연다. 재는 것은
      「화면이 0건을 사람의 말로 그리는가」이고, 그 물음에는 이 방법이 답한다.
      다만 표에는 **그렇게 쟀다고 적는다** — 방법을 숨기면 다음 사람이 오독한다.
    """
    api_path = spec.get("api")
    base = spec.get("baseline_body") or ""
    real = (spec.get("real_bodies") or {})
    if not api_path:
        return None
    #: 이 화면이 **방금 받은 진짜 응답들** 중 목록을 담은 것들을 전부 비운다.
    #: 하나만 비우면 다른 목록이 남아 화면이 안 비고, 그 「안 빔」을 빈 상태로 적게 된다.
    targets = {p: empty_like(b) for p, b in real.items()}
    if not targets:
        return {"undecidable": True,
                "why": "이 화면이 받은 진짜 응답을 못 잡았다 — 빈 모양을 지어내지 않는다"}

    def make(payload):
        def handler(route):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(payload))
        return handler

    try:
        for path, payload in targets.items():
            #: ★★ 꼬리 `**` 가 **반드시** 있어야 한다 [실측 2026-09-06 · 턴 G].
            #:   `**/api/dsm/events` 는 `/api/dsm/events?limit=50` 을 **안 잡는다.**
            #:   그래서 빈 응답이 목록에 안 먹었고, 화면은 22건을 그대로 그렸다 —
            #:   그런데 도구는 그 화면을 보고 「빈 문구가 없다」고 **빨강**을 적었다.
            #:   주입이 안 먹은 것을 화면의 결함으로 적는 것이 D-322 그 자체다.
            context.route(f"**{path}**", make(payload))
        _goto(page, web, spec["route"], None)
        page.wait_for_timeout(5_000)
        body = _visible_text(page)
        # antd `Empty` 가 그리는 자리에서 문구를 집는다. 없으면 본문에서 「없습니다」 줄.
        empty_text = ""
        try:
            emp = page.locator(".ant-empty-description")
            if emp.count():
                empty_text = (emp.first.inner_text() or "").strip()
        except Exception:                                       # noqa: BLE001
            pass
        if not empty_text:
            #: ★ 「빈 상태가 **더한** 말」만 빈 문구다. 그냥 「없습니다」가 든 줄을
            #:   집으면 화면에 늘 있던 설명 문단이 잡히고, 그것을 오류 문구와 견주어
            #:   「빈과 오류가 같다」는 없는 결함이 태어난다 [실측 2026-09-06].
            base_lines = {ln.strip() for ln in (base or "").splitlines()}
            for line in body.splitlines():
                t = line.strip()
                if t and t not in base_lines and ("없습니다" in t or "없음" in t
                                                  or "0건" in t):
                    empty_text = t
                    break
        if base and body.strip() == base.strip():
            return {"undecidable": True,
                    "why": "빈 응답을 주입했는데 본문이 기준선과 **한 글자도 다르지 "
                           "않다** — 주입이 이 화면에 닿지 않았다. 「빈 문구가 없다」로 "
                           "셀 수 없다"}
        return {"body_text": body[:4000], "empty_text": empty_text,
                "raw_hits": scan_raw_error(body),
                # ★ 「빈」과 「오류」가 **같은 문구인가.** 오류 주입 때의 본문과 견준다.
                "same_as_error": bool(empty_text) and empty_text in (error_body or ""),
                "targets": sorted(targets),
                "method": "화면이 받은 **진짜 응답의 목록을 비워** 되돌려 주었다 "
                          "(빈 테넌트가 아니다 · 모양은 계약 그대로)"}
    except Exception as exc:                                    # noqa: BLE001
        return {"undecidable": True, "why": f"{type(exc).__name__}: {exc}"[:200]}
    finally:
        for path in targets:
            try:
                context.unroute(f"**{path}**")
            except Exception:                                   # noqa: BLE001
                pass


def _probe_form_login(page, web: str, api: str) -> dict:
    """로그인 폼 — 필수 빈값 · 틀린 값. **이중 제출**도 여기서 센다."""
    out: dict = {}
    sent: list = []

    def count_login(req):
        if "/api/v1/auth/login" in req.url and req.method == "POST":
            sent.append(req.url)

    try:
        page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2_500)

        # ① 필수 빈값 — 아무것도 안 넣고 누른다.
        before = _visible_text(page)
        page.get_by_role("button", name="Log In").click()
        page.wait_for_timeout(2_500)
        after = _visible_text(page)
        added = after.replace(before, "")
        out["required"] = {
            "message_shown": len(added.strip()) > 0 or "required" in after.lower()
            or "입력" in added or "필수" in added,
            "added_text": added[:300], "raw_hits": scan_raw_error(after)}

        # ② 틀린 값 — 서버가 거절하는 자리. **주입으로 401 을 만든다**(실계정 잠금 방지).
        page.on("request", count_login)
        fields = page.locator("input")
        fields.nth(0).fill("gxprobe_q")
        fields.nth(1).fill("wrong-password-not-real")
        page.route("**/api/v1/auth/login", lambda r: r.fulfill(
            status=401, content_type="application/json",
            body=json.dumps({"message": "아이디 또는 비밀번호가 올바르지 않습니다.",
                             "status_code": 401})))
        btn = page.get_by_role("button", name="Log In")
        # ★ **이중 제출** — 빠르게 두 번 누른다. 요청이 두 번 나가면 빨강이다.
        sent.clear()
        btn.click()
        btn.click(delay=0)
        page.wait_for_timeout(3_500)
        body = _visible_text(page)
        out["format"] = {"message_shown": "않습니다" in body or "올바르지" in body
                         or "실패" in body,
                         "raw_hits": scan_raw_error(body)}
        out["double_submit"] = {"requests": len(sent), "where": "로그인"}
    except Exception as exc:                                    # noqa: BLE001
        return {"undecidable": True, "why": f"{type(exc).__name__}: {exc}"[:200]}
    finally:
        try:
            page.remove_listener("request", count_login)
            page.unroute("**/api/v1/auth/login")
        except Exception:                                       # noqa: BLE001
            pass
    return out


def _probe_form_csv(context, page, web: str, spec: dict) -> dict:
    """카메라 일괄 등록 — 빈 CSV · 잘못된 행 · **서버 거절(422) 주입**."""
    out: dict = {}
    sent: list = []

    def count_import(req):
        if "/api/dsm/cameras/import" in req.url and req.method != "GET":
            sent.append(req.url)

    try:
        ok, why = _goto(page, web, spec["route"], spec.get("see"))
        if not ok:
            return {"undecidable": True, "why": f"화면에 못 갔다 — {why}"}
        area = page.locator("textarea")
        if not area.count():
            return {"undecidable": True, "why": "이 화면에 입력칸(textarea)이 없다"}
        buttons = page.get_by_role("button")

        def press_first(names):
            for i in range(buttons.count()):
                try:
                    t = (buttons.nth(i).inner_text() or "")
                    if any(n in t for n in names) and buttons.nth(i).is_visible():
                        buttons.nth(i).click()
                        return True
                except Exception:                               # noqa: BLE001
                    continue
            return False

        # ① 필수 빈값 — 빈 채로 「표 먼저 보기」.
        area.first.fill("")
        before = _visible_text(page)
        pressed = press_first(("표 먼저", "미리", "확인", "적용"))
        page.wait_for_timeout(3_000)
        after = _visible_text(page)
        if pressed:
            out["required"] = {
                "message_shown": len(after.replace(before, "").strip()) > 0,
                "added_text": after.replace(before, "")[:300],
                "raw_hits": scan_raw_error(after)}

        # ② 형식 오류 — 열이 안 맞는 줄을 넣는다.
        area.first.fill("이건,csv가,아니다\n@@@,,,")
        before = _visible_text(page)
        page.on("request", count_import)
        sent.clear()
        pressed = press_first(("표 먼저", "미리", "확인", "적용"))
        page.wait_for_timeout(3_500)
        after = _visible_text(page)
        if pressed:
            out["format"] = {
                "message_shown": len(after.replace(before, "").strip()) > 0,
                "added_text": after.replace(before, "")[:300],
                "raw_hits": scan_raw_error(after)}
            out["double_submit"] = {"requests": len(sent), "where": "표 먼저 보기"}

        # ③ 서버 거절 — **422 를 주입한다.** 서버에는 안 간다.
        context.route("**/api/dsm/cameras/import**", lambda r: r.fulfill(
            status=422, content_type="application/json",
            body=json.dumps({"message": "표의 3행에 필요한 값이 없습니다.",
                             "status_code": 422})))
        area.first.fill("name,rtsp\n카메라1,rtsp://x")
        before = _visible_text(page)
        pressed = press_first(("표 먼저", "미리", "확인", "적용"))
        page.wait_for_timeout(3_500)
        after = _visible_text(page)
        if pressed:
            out["reject422"] = {
                "message_shown": "없습니다" in after.replace(before, "")
                or len(after.replace(before, "").strip()) > 0,
                "added_text": after.replace(before, "")[:300],
                "raw_hits": scan_raw_error(after)}
    except Exception as exc:                                    # noqa: BLE001
        return {"undecidable": True, "why": f"{type(exc).__name__}: {exc}"[:200]}
    finally:
        try:
            page.remove_listener("request", count_import)
            context.unroute("**/api/dsm/cameras/import**")
        except Exception:                                       # noqa: BLE001
            pass
    return out


def _baseline(page, web: str, spec: dict) -> tuple:
    """**주입하지 않은 채** 한 번 연다 → `(본문, {경로: 진짜 응답})`.

    ★ 두 가지를 여기서 얻는다:
      ㉠ **기준선 본문** — 주입한 화면이 이것과 **한 글자도 안 다르면** 주입이 화면에
        닿지 않은 것이다. 그때 「오류를 잘 그렸다」고 적으면 **거짓 초록**이다
        [실측 2026-09-06: 보고서 화면이 다섯 갈래 전부 같은 본문을 냈다].
      ㉡ **진짜 응답** — 빈 상태를 만들 때 모양을 지어내지 않기 위한 원본이다.
    """
    bodies: dict = {}

    def note(resp):
        try:
            if resp.request.method != "GET" or "/api/" not in resp.url:
                return
            if resp.status != 200:
                return
            path = "/api/" + resp.url.split("/api/", 1)[1].split("?")[0]
            if path in bodies:
                return
            ct = (resp.header_value("content-type") or "")
            if "json" not in ct:
                return
            bodies[path] = resp.json()
        except Exception:                                       # noqa: BLE001
            pass

    page.on("response", note)
    try:
        _goto(page, web, spec["route"], None)
        page.wait_for_timeout(3_000)
        body = _visible_text(page)
    finally:
        try:
            page.remove_listener("response", note)
        except Exception:                                       # noqa: BLE001
            pass
    return body, bodies


def _recon(page, web: str, spec: dict) -> list:
    """이 화면이 **실제로 부르는** API 를 적는다. 하드코딩한 경로는 낡는다."""
    seen: list = []

    def note(req):
        if "/api/" in req.url and req.method == "GET":
            path = "/api/" + req.url.split("/api/", 1)[1].split("?")[0]
            if path not in seen:
                seen.append(path)

    page.on("request", note)
    try:
        _goto(page, web, spec["route"], None)
        page.wait_for_timeout(4_000)
    finally:
        try:
            page.remove_listener("request", note)
        except Exception:                                       # noqa: BLE001
            pass
    return seen


def run(*, web: str, api: str, user: str, password: str,
        only: list | None = None) -> dict:
    from playwright.sync_api import sync_playwright

    blocked: list = []
    result = {
        "when": datetime.now().replace(microsecond=0).isoformat(),
        "web": web, "api": api,
        "names_from_perf_load": _scenario_names(),
        "screens": {}, "blocked_writes": blocked, "session_closed": None,
        "how": "Playwright 요청 가로채기 — 주입한 요청은 네트워크로 나가지 않는다",
    }
    todo = [k for k in SCREENS if not only or k in only]

    # ★ **먼저 자물쇠를 푼다.** 앞 실행이 물고 있으면 이번 로그인이 「다른 기기 접속」
    #   창을 만나고, 그 창 뒤의 측정은 전부 로그인 화면을 본다 [실측 2026-09-06].
    result["session_released_before"] = _release_session(user)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(viewport=DESKTOP)
        _install_write_guard(context, api, blocked)
        page = context.new_page()
        try:
            # ── 로그인 폼은 **로그인 전에** 눌러야 한다 ────────────────────
            if "로그인" in todo:
                s = result["screens"].setdefault("로그인", {})
                s["route"] = "/login"
                s["reached"] = True
                s["widths"] = [1440]
                s["form"] = _probe_form_login(page, web, api)
                s["buttons"] = _button_names(page)
                # 오류 흐름 — 로그인 API 에 500·503·403·타임아웃.
                errs = {}
                for mode in INJECT_MODES:
                    try:
                        _inject(context, api, "/api/v1/auth/login", mode)
                        page.goto(f"{web}/login", wait_until="networkidle",
                                  timeout=60_000)
                        page.wait_for_timeout(2_000)
                        f = page.locator("input")
                        f.nth(0).fill("gxprobe_q")
                        f.nth(1).fill("x")
                        page.get_by_role("button", name="Log In").click()
                        body, early, late = _read_twice(
                            page, 6_000 if mode != "timeout" else 16_000)
                        errs[mode] = {"mode": mode, "body_text": body[:4000],
                                      "spinner_stuck": _spinner_stuck(page),
                                      "raw_hits": scan_raw_error(body),
                                      "vanished": bool(
                                          any(w in early for w in ERROR_AFFORDANCE
                                              + FORBIDDEN_AFFORDANCE)
                                          and not any(w in late for w in
                                                      ERROR_AFFORDANCE
                                                      + FORBIDDEN_AFFORDANCE)),
                                      "url": page.url}
                    except Exception as exc:                    # noqa: BLE001
                        errs[mode] = {"undecidable": True,
                                      "why": f"{type(exc).__name__}: {exc}"[:200]}
                    finally:
                        try:
                            context.unroute(f"**/api/v1/auth/login**")
                        except Exception:                       # noqa: BLE001
                            pass
                s["errors"] = errs

            _login(page, web, user, password)

            for name in todo:
                if name == "로그인":
                    continue
                spec = SCREENS[name]
                print(f"{TAG} [{name}] 시작", flush=True)
                s = result["screens"].setdefault(name, {})
                s["route"] = spec.get("route")
                s["widths"] = []
                s["mobile_only"] = bool(spec.get("mobile_only"))

                # ── 이벤트 상세는 **목록에서 연다** ────────────────────────
                if spec.get("reach") == "from_list":
                    ok, why = _goto(page, web, "/dsm/events", "이벤트 목록")
                    if ok:
                        try:
                            rows = page.get_by_role("row")
                            if rows.count() > 1:
                                rows.nth(1).click()
                                page.wait_for_timeout(5_000)
                                s["route"] = page.url.split(web, 1)[-1]
                                ok = spec["see"] in _visible_text(page)
                                why = "" if ok else "상세로 갔는데 머리글이 없다"
                            else:
                                ok, why = False, "목록에 누를 줄이 없다"
                        except Exception as exc:                # noqa: BLE001
                            ok, why = False, f"{type(exc).__name__}: {exc}"[:160]
                    s["reached"], s["reach_error"] = ok, why
                    if ok:
                        s["widths"] = [1440]
                        s["buttons"] = _button_names(page)
                        if s["route"]:
                            spec = dict(spec, route=s["route"])
                            s["errors"] = _probe_errors(context, page, web, api,
                                                        name, spec)
                    continue

                if spec.get("recon_api"):
                    found = _recon(page, web, spec)
                    s["recon"] = found
                    # 이 화면이 부른 것 중 **자기 화면의 것**을 고른다.
                    pick = next((f for f in found if "auth" not in f), None)
                    spec = dict(spec, api=pick)
                    s["api_used"] = pick

                ok, why = _goto(page, web, spec["route"], spec.get("see"))
                s["reached"], s["reach_error"] = ok, why
                if not ok:
                    continue
                s["widths"].append(1440)
                s["buttons"] = _button_names(page)

                # ★ **주입 전에** 기준선과 진짜 응답을 잡는다.
                base_body, real_bodies = _baseline(page, web, spec)
                s["baseline_len"] = len(base_body)
                s["real_api_seen"] = sorted(real_bodies)
                spec = dict(spec, baseline_body=base_body, real_bodies=real_bodies)

                s["errors"] = _probe_errors(context, page, web, api, name, spec)
                err_body = ""
                for m in ("500", "503"):
                    pr = (s["errors"] or {}).get(m) or {}
                    err_body += pr.get("body_text") or ""
                s["empty"] = _probe_empty(context, page, web, api, name, spec,
                                          err_body)
                if spec.get("form", {}).get("kind") == "csv":
                    s["form"] = _probe_form_csv(context, page, web, spec)

                # ── 390px 에서 한 번 더 연다 ──────────────────────────────
                try:
                    page.set_viewport_size(MOBILE)
                    page.wait_for_timeout(1_000)
                    ok2, _ = _goto(page, web, spec["route"], spec.get("see"))
                    if ok2:
                        s["widths"].append(390)
                finally:
                    page.set_viewport_size(DESKTOP)
                    page.wait_for_timeout(500)
        finally:
            browser.close()
    # ★★ 자물쇠 풀기는 **`sync_playwright` 블록 밖**이어야 한다 [실측 2026-09-06 · 턴 G].
    #   안에서 부르면 Django ORM 이 `SynchronousOnlyOperation: You cannot call this
    #   from an async context` 로 죽는다 — playwright 의 동기 API 는 그 안쪽이
    #   **async 문맥**이기 때문이다. 그리고 그 죽음은 조용하다: 도구는 「세션이 열린
    #   채다」라고 빨강 한 줄만 적고 끝나며, **세션은 진짜로 물린 채 남는다.**
    #   이 환경은 동시 접속 1개라 그 한 줄이 다음 차선을 통째로 막는다.
    result["session_closed"] = _release_session(user)
    return result


def render_md(result: dict) -> str:
    """측정 결과를 **정본 표 그대로의 마크다운**으로 낸다.

    ★ 손으로 표를 옮겨 적지 않는다. 옮겨 적는 순간 JSON 과 문서가 갈라지고,
      갈라진 둘 중 어느 쪽이 실측인지 다음 사람이 알 수 없다 (D-369).
    """
    #: ★ 저장된 `cells` 를 쓰지 않고 **늘 다시 센다** — 세는 규칙이 바뀌면 낡은 칸이
    #:   남고, 낡은 칸과 새 규칙이 섞인 표는 어느 쪽으로도 읽을 수 없다.
    cells = to_cells(result)
    counts = count_cells(cells)
    out: list = []
    out.append("| " + " | ".join(("화면",) + CANON_COLS[1:]) + " |")
    out.append("|" + "---|" * len(CANON_COLS))
    for row in CANON_ROWS:
        line = []
        for col in CANON_COLS:
            c = cells[row][col]
            mark, note = c["mark"], (c["note"] or "").replace("|", "·")
            if col == "화면":
                line.append(f"**{row}** {mark} {note}".strip())
            else:
                line.append(f"{mark} {note}".strip() if mark else note)
        out.append("| " + " | ".join(line) + " |")
    out.append("")
    out.append("| | 수 |")
    out.append("|---|---|")
    out.append(f"| ● 전부 눌렀다 | **{counts['full']}** |")
    out.append(f"| ◐ 일부 눌렀다 | **{counts['partial']}** |")
    out.append(f"| **N/56 (● + ◐)** | **{counts['counted']} / 56 = "
               f"{round(counts['counted'] / 56 * 100)}%** |")
    out.append(f"| — 해당 없음(원표) | {counts['na']} |")
    out.append(f"| (빈칸) **안 눌렀다** | {counts['blank']} |")
    return "\n".join(out)


def _evidence_dir() -> Path:
    """`walk_scenarios._evidence_dir` 와 **같은 판단**이다 — 「폴더가 있다」와
    「그 폴더가 그 폴더다」는 다른 사실이다."""
    marker = Path("agent") / "evidence" / "D-346" / "ga_readiness.yaml"
    for base in (Path("/docs"), ROOT / "docs"):
        if (base / marker).is_file():
            return base / "agent" / "evidence" / "P-69"
    return ROOT / "docs" / "agent" / "evidence" / "P-69"


def main() -> int:
    ap = argparse.ArgumentParser(description="P-69 오류·빈·폼 세 상태를 누른다")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--web", default=os.environ.get("GX_WEB", "http://localhost:3002"))
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--user", default=os.environ.get("GX_ROUTE_USER", ""))
    ap.add_argument("--password", default=os.environ.get("GX_ROUTE_PASSWORD", ""),
                    help="⚠ argv 는 `ps` 에 그대로 보인다 — 되도록 --password-env 를 쓴다")
    ap.add_argument("--password-env", default="",
                    help="비밀번호가 든 **환경변수 이름**. 이쪽이 본줄기다 — "
                         "argv 로 넘기면 같은 호스트의 누구나 `ps` 로 읽는다 (D-204)")
    ap.add_argument("--only", default="", help="쉼표로 나눈 행 이름(정본 표의 이름)")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--render-md", default="",
                    help="이미 잰 states.json 을 표 마크다운으로만 낸다(브라우저 없이)")
    args = ap.parse_args()

    if args.render_md:
        data = json.loads(Path(args.render_md).read_text(encoding="utf-8"))
        print(render_md(data))
        return EXIT_OK
    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL
    #: ★ 환경변수 풀이는 **계정 검사보다 먼저**다. 뒤에 두었더니 「계정이 없다」로
    #:   판정 불가를 냈다 [실측 2026-09-06] — 순서 하나가 도구를 통째로 재우는 자리다.
    if args.password_env:
        args.password = os.environ.get(args.password_env, "")
    if not args.user or not args.password:
        print(f"{TAG} **판정 불가** — 계정이 없다. 이 도구는 계정을 만들지 않는다")
        return EXIT_UNDECIDABLE

    only = [s.strip() for s in args.only.split(",") if s.strip()] or None
    try:
        result = run(web=args.web, api=args.api, user=args.user,
                     password=args.password, only=only)
    except Exception as exc:                                    # noqa: BLE001
        print(f"{TAG} **판정 불가** — 못 눌렀다: {type(exc).__name__}: {exc}")
        return EXIT_UNDECIDABLE

    cells = to_cells(result)
    counts = count_cells(cells)
    result["cells"] = cells
    result["counts"] = counts

    print(f"{TAG} [환경] {args.web} · {result['when']} · "
          f"주입은 브라우저 안에서 끝난다(서버 무접촉)")
    for row in CANON_ROWS:
        marks = " ".join(f"{cells[row][c]['mark'] or '·'}" for c in CANON_COLS)
        print(f"{TAG}   {marks}  {row}")
    print(f"{TAG} [셈] ● {counts['full']} · ◐ {counts['partial']} · "
          f"빈칸 {counts['blank']} · — {counts['na']} · "
          f"**N/56 = {counts['counted']}/56**")

    rc = EXIT_OK
    for (name, ok, why) in judge(result):
        print(f"{TAG} {'  ' if ok else 'X '}{name:42} {why}")
        if not ok:
            rc = EXIT_FAIL

    out = Path(args.json_out) if args.json_out else _evidence_dir() / "states.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"{TAG} [증거] {out}")
    except OSError as exc:
        print(f"{TAG} ⚠ 증거를 못 남겼다: {exc}")

    print(f"{TAG} " + {
        EXIT_OK: "통과 — 눌렀고 화면이 사람의 말로 답했다",
        EXIT_FAIL: "실패 — 위의 X 가 화면이 실패를 삼킨 자리다",
        EXIT_UNDECIDABLE: "**회색** — 못 눌렀다 (D-301)",
    }[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main())
