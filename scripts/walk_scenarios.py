#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""S1·S2·S3 **시나리오 걷기** — 390px 에서 사람처럼 지나간다 (2026-09-05 · 턴 C · 차선 Q).

무엇이 다른가 — **부하기와 촬영기 사이의 빈자리**
------------------------------------------------
    `perf_load.py`      문을 **두드린다**. API 가 몇 ms 인가. 화면은 안 연다.
    `capture_screens.py` 화면을 **찍는다**. 한 장 한 장이 떴는지 단언한다. 걷지는 않는다.
    이 도구            화면을 **걷는다**. 목록에서 필터를 누르고, 한 건을 열고,
                       그 사이에 **몇 번 눌렀고 몇 초 걸렸고 콘솔이 몇 번 울었는지** 센다.

★ **시나리오 이름을 새로 짓지 않는다** — `perf_load.SCENARIOS` 의 S1·S2·S3 을 그대로
  쓴다. 두 표를 만들면 다음 사람이 「S2」를 물었을 때 어느 표를 봐야 하는지 모른다(D-212).
  여기서 하는 일은 그 이름에 **화면 경로를 붙이는 것**뿐이다. 이름이 어긋나면 멈춘다.

★ **390px 는 모바일 폭이다.** 관제요원이 자리에서 보는 화면과 현장에서 보는 화면은
  같은 화면이 아니다. 데스크톱 1440px 에서만 걸으면 모바일에서 **누를 수 없는 자리**를
  영영 못 본다 — 그리고 현장은 늘 모바일이다.

⚠ **클릭 수를 줄이는 것이 목적이 아니다.** 지금 몇 번인지 **재는 것**이 목적이다.
  첫 수는 기준선이지 합격선이 아니다 — PERF-04 에서 배운 그대로다(세종 P-34).
  그래서 클릭 수와 경과 시간은 **표에 적고 판정하지 않는다.** 판정하는 것은 셋뿐이다:
  ① 걸어지는가(각 걸음의 단언) ② 콘솔이 우는가 ③ 세션을 닫았는가.

⚠ **로그인 세션을 물고 있지 마라.** 이 환경은 **동시 접속 1개**다 — 다른 차선이
  화면을 만지는 중에 이 도구가 세션을 쥐고 있으면 그쪽이 튕긴다. 끝나면
  `POST /api/v1/auth/logout` 으로 닫는다. 닫지 못하면 그 사실을 **빨강으로** 적는다.

    docker exec -i gx-shell python /repo/scripts/walk_scenarios.py \
        --user gxprobe_e2e --password ****
    python scripts/walk_scenarios.py --self-test     # 판정 규칙만 (브라우저 없이)

종료 코드: 0 걸었고 통과 · 1 걸었고 실패 · 2 **못 걸었다**(환경 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

TAG = "[WALK]"
ROOT = Path(__file__).resolve().parent.parent

#: **모바일 폭.** iPhone 12 급의 논리 해상도다. 이 수를 키우면 이 도구가 재는 것이
#: 달라진다 — 데스크톱에서 누를 수 있는 자리는 모바일의 증거가 아니다.
VIEWPORT = {"width": 390, "height": 844}


def _scenario_names() -> dict:
    """S1·S2·S3 의 이름을 **`perf_load` 에서 가져온다.** 여기서 다시 짓지 않는다.

    ★ 못 가져오면 **판정 불가**다. 이름을 이 파일에 베껴 두면 그날부터 두 표가 되고,
      두 표는 반드시 어긋난다 (D-212 · D-369).
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from perf_load import SCENARIOS

    return {k: SCENARIOS[k]["name"] for k in ("S1", "S2", "S3")}


# ═══════════════════════════════════════════════════════════════════════════
# 걸음 — **화면 경로만 여기 있다.** 이름은 perf_load 가 답한다
# ═══════════════════════════════════════════════════════════════════════════
#
# 걸음 하나는 셋 중 하나다:
#   {"go": 경로}              그 주소로 간다 (클릭이 아니다 — 주소창은 사람의 손이 아니다)
#   {"click": (역할, 이름)}    그 버튼·링크를 **누른다** (클릭 1회로 센다)
#   {"click_row": n}          표의 n번째 줄을 누른다 — 목록에서 한 건을 여는 손짓
# 그리고 걸음마다 `see` 가 있다: **그 걸음이 끝난 화면에만 있는 글자**.
# 공통 글자로 단언하면 안 움직여도 초록이 된다 — `capture_screens` 가 프리셋 넷에서
# 배운 함정이 그대로 여기에도 있다.
#
# ★ `see` 는 전부 **실제로 390px 에서 열어 본문을 읽고** 골랐다 [실측 2026-09-05 TC].
WALKS: dict[str, list] = {
    "S1": [
        {"go": "/dsm/events", "see": "이벤트 목록"},
        # 관제요원이 목록에서 가장 먼저 하는 일: **아직 아무도 안 본 것**만 남긴다.
        {"click": ("button", "미처리"),
         "see": "미처리 — 대응 축이 아직 「발생」인 것"},
        # 그리고 한 건을 연다. 여기까지가 「목록」 시나리오의 끝이다.
        {"click_row": 1, "see": "이벤트 상세"},
    ],
    "S2": [
        {"go": "/dsm/dashboard", "see": "관제 대시보드"},
        # 대시보드의 최근 이벤트에서 **전체 목록으로 건너가는 자리**. 이 한 번이
        # 안 되면 대시보드는 막다른 화면이 된다.
        #
        # ⚠ [실측 2026-09-05 TC] 이 자리는 **`href` 없는 `<a>`** 다. 그래서 접근성
        #   나무에서 `link` 가 아니고(이 화면의 link 는 **0개**다), 키보드 초점도
        #   새 탭 열기도 안 된다. 손가락으로는 눌리므로 **글자로** 누른다 —
        #   `get_by_role("link")` 로 걸으면 「없다」가 나오는데, 그 「없다」는
        #   자리가 없다는 뜻이 아니라 **역할이 없다**는 뜻이다. 둘을 섞지 않는다.
        {"click_text": "전체 목록", "see": "이벤트 목록"},
    ],
    "S3": [
        {"go": "/dsm/queue", "see": "지금 가장 급한 하나"},
        # 단일 초점에서 **가장 급한 하나를 여는** 단추. 이것이 이 화면의 존재 이유다.
        {"click": ("button", "상세 열기"), "see": "이벤트 상세"},
    ],
}

#: **알려진 잡음.** 목록으로 두는 이유는 `capture_screens.KNOWN_BLANK` 와 같다 —
#: 못 고치는 것을 목록에서 지우면 「없다」와 「알고 있으나 남의 자리다」가 같아진다(D-264).
#:
#: ⚠ 이 목록은 **면제가 아니라 분류**다. 여기 걸리는 줄은 「알려진 잡음」으로 세고,
#:   **여기 안 걸리는 줄은 한 건이라도 빨강**이다. 반대로 만들면(=아는 것만 빨강)
#:   내일 새로 나는 오류가 조용히 통과한다.
#: ⚠ [실측 2026-09-05 TC] 넷 다 §0.4 금지구역(orders·partner)의 웹소켓이고, 이 환경에
#:   그 서버가 없어 404 로 떨어진 뒤 **재접속을 반복한다** — 그래서 건수가 걸은 시간에
#:   비례한다. 화면의 결함이 아니라 환경의 사실이다. 고치는 것은 이 차선의 몫이 아니다.
KNOWN_CONSOLE_NOISE = (
    ("/ws/partner-callbacks/", "§0.4 partner 웹소켓 — 이 환경에 서버가 없다(404) · 재접속 루프"),
    ("Partner callback WebSocket error", "위 404 가 남기는 두 번째 줄"),
    ("/ws/orders/notifications/", "§0.4 orders 웹소켓 — 같음"),
    ("New order notification WebSocket error", "위 404 가 남기는 두 번째 줄"),
)


def classify_console(errors: dict) -> tuple:
    """콘솔 줄을 **알려진 잡음**과 **분류되지 않은 것**으로 가른다."""
    known, unknown = {}, {}
    for key, lines in (errors or {}).items():
        for line in lines:
            hit = next((why for tok, why in KNOWN_CONSOLE_NOISE if tok in line), None)
            bucket = known if hit else unknown
            bucket.setdefault(key, []).append(line)
    return known, unknown


#: S4(섞기)는 걷지 않는다 — **여러 자리를 동시에 두드리는 부하 시나리오**이고,
#: 사람의 손 하나로는 동시에 못 누른다. 이름을 빌린 표에 없는 것을 지어내지 않는다.
NOT_WALKED = {"S4": "부하용 혼합 시나리오 — 동시 호출이라 사람의 걸음으로 환산되지 않는다"}


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **함수로 떼어 둔다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(result: dict) -> list:
    """`(이름, 통과, 사유)`. **클릭 수와 시간은 판정하지 않는다** — 기준선이다.

    ★ `None` 은 **못 쟀다**이지 거짓이 아니다 (D-301).
    """
    out: list = []
    walks = result.get("walks")

    if not walks:
        out.append(("세 시나리오를 걸었다", False, "**못 걸었다** — 결과가 없다"))
    else:
        done = [k for k, w in walks.items() if w.get("completed")]
        ok = sorted(done) == sorted(WALKS)
        broke = {k: w.get("failed_at") for k, w in walks.items()
                 if not w.get("completed")}
        out.append(("세 시나리오를 걸었다", ok,
                    f"완주 {len(done)}/{len(WALKS)}"
                    + ("" if ok else f" — 멈춘 자리: {broke}. **모바일 폭에서 누를 수 "
                                     f"없는 자리**이거나 화면이 안 뜬 것이다")))

    errs = result.get("console_errors")
    if errs is None:
        out.append(("분류되지 않은 콘솔 오류 0건", False, "**못 쟀다**"))
    else:
        known, unknown = classify_console(errs)
        n_known = sum(len(v) for v in known.values())
        n_unknown = sum(len(v) for v in unknown.values())
        out.append(("분류되지 않은 콘솔 오류 0건", n_unknown == 0,
                    f"0건 (알려진 잡음 {n_known}건은 따로 센다)" if n_unknown == 0 else
                    f"{n_unknown}건 — {json.dumps(unknown, ensure_ascii=False)[:420]}"))

    closed = result.get("session_closed")
    if closed is None:
        out.append(("세션을 닫았다", False, "**못 쟀다** — 로그아웃을 부르지 못했다"))
    else:
        out.append(("세션을 닫았다", bool(closed),
                    "POST /api/v1/auth/logout 200" if closed else
                    "**세션이 열린 채다.** 이 환경은 동시 접속 1개다 — 물고 있으면 "
                    "다른 차선이 화면에서 튕긴다"))

    names = result.get("names_from_perf_load")
    out.append(("시나리오 이름을 빌려 왔다", bool(names),
                f"perf_load.SCENARIOS ← {names}" if names else
                "**이름을 못 가져왔다** — 여기서 새로 지으면 표가 둘이 된다 (D-212)"))
    return out


def self_test() -> int:
    """판정 규칙을 **브라우저 없이** 시험한다 (D-277 · D-350)."""
    bad: list = []

    def names(rows):
        return {n: ok for (n, ok, _why) in rows}

    green = {
        "walks": {k: {"completed": True, "clicks": 1, "ms": 1000} for k in WALKS},
        "console_errors": {k: [] for k in WALKS},
        "session_closed": True,
        "names_from_perf_load": {"S1": "목록", "S2": "대시보드", "S3": "단일 초점"},
    }
    got = names(judge(green))
    if not all(got.values()):
        bad.append(f"다 선 표본을 통과로 읽지 못한다: {got}")

    # ── **출생 표본** (D-310) — 이 도구가 없던 상태. 아무도 안 걸어 봤으므로
    #    걸음도 없고 수도 없다. 「0건 걸었다」가 초록이면 이 도구는 아무 일도 안 한다.
    if names(judge({"walks": {}, "console_errors": {}, "session_closed": True,
                    "names_from_perf_load": {}})).get("세 시나리오를 걸었다"):
        bad.append("**아무것도 안 걸었는데** 통과로 읽는다 — 0건은 통과가 아니다 (D-301)")

    # ── 음성 갈래 ──────────────────────────────────────────────────────────
    for key, value, expect_red in (
        ("walks", {**green["walks"], "S3": {"completed": False, "failed_at": 2}},
         "세 시나리오를 걸었다"),
        ("console_errors", {"S1": ["TypeError: x is not a function"]},
         "분류되지 않은 콘솔 오류 0건"),
        ("session_closed", False, "세션을 닫았다"),
        ("names_from_perf_load", {}, "시나리오 이름을 빌려 왔다"),
    ):
        if names(judge(dict(green, **{key: value}))).get(expect_red):
            bad.append(f"{key}={str(value)[:40]!r} 인데 「{expect_red}」를 통과로 읽는다")

    # ── **못 쟀다 ≠ 거짓** ─────────────────────────────────────────────────
    # ★ **알려진 잡음만 있는 표본은 초록**이어야 한다 — 아니면 목록이 목록이 아니다.
    noise = dict(green, console_errors={"S1": [
        "console.error: WebSocket connection to 'ws://x/ws/partner-callbacks/' failed"]})
    if not names(judge(noise)).get("분류되지 않은 콘솔 오류 0건"):
        bad.append("알려진 잡음만 있는 표본을 빨강으로 읽는다 — 분류가 분류가 아니다")
    # ★ 그리고 **잡음에 섞인 새 오류는 빨강**이어야 한다. 이것이 뒤집히면 목록이 면제가 된다.
    mixed = dict(green, console_errors={"S1": [
        "console.error: WebSocket connection to 'ws://x/ws/orders/notifications/' failed",
        "console.error: 새로 난 오류"]})
    if names(judge(mixed)).get("분류되지 않은 콘솔 오류 0건"):
        bad.append("**잡음에 섞인 새 오류**를 통과로 읽는다 — 목록이 면제가 됐다")

    for key, label in (("console_errors", "분류되지 않은 콘솔 오류 0건"),
                       ("session_closed", "세션을 닫았다")):
        hit = [r for r in judge(dict(green, **{key: None})) if r[0] == label][0]
        if hit[1] or "못 쟀다" not in hit[2]:
            bad.append(f"{key} 를 **못 쟀는데** 통과로 읽거나 사유에 그 사실이 없다")

    # ── 걸음표 자체를 시험한다 — 각 걸음에 **단언이 있는가** ───────────────
    for key, steps in WALKS.items():
        for i, step in enumerate(steps):
            if not step.get("see"):
                bad.append(f"{key} 의 {i+1}번째 걸음에 `see` 가 없다 — 단언 없는 걸음은 "
                           f"「눌렀다」만 남기고 「그래서 무엇이 떴는가」를 안 남긴다")

    if bad:
        print(f"{TAG} 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 초록 1 · 출생 표본 1 · 음성 4 · 판정 불가 2 · 걸음표 검사")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — 브라우저를 열고 **사람처럼** 지나간다
# ═══════════════════════════════════════════════════════════════════════════
def _login(page, web: str, user: str, password: str) -> None:
    """로그인. **「다른 기기 접속」 확인 창을 사람처럼 처리한다.**

    ⚠ 이 환경은 동시 접속 1개다. 확인을 누르면 **앞의 세션이 끊긴다** — 그래서 이
      도구는 끝나면 반드시 로그아웃한다. 물고 있는 것이 남에게 주는 피해다.
    """
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
        # 「이 계정이 다른 기기에서 접속 중입니다」 — end_previous_session 과 같은 뜻이다.
        confirm.first.click()
        page.wait_for_timeout(9_000)
    else:
        page.wait_for_timeout(6_000)
    if page.url.rstrip("/").endswith("/login"):
        raise RuntimeError(
            f"로그인 뒤에도 로그인 화면이다 ({page.url}) — "
            f"본문: {page.inner_text('body')[:200]!r}")


def _one_walk(page, web: str, key: str, steps: list) -> dict:
    """한 시나리오를 걷는다. **각 걸음의 시간과 클릭 수를 따로 센다.**"""
    out = {"clicks": 0, "ms": 0, "steps": [], "completed": False, "failed_at": None}
    started_all = time.perf_counter()
    for i, step in enumerate(steps, start=1):
        started = time.perf_counter()
        what = ""
        #: **일부러 기다린 시간.** 이것을 빼지 않으면 「경과 18초」가 화면이 느린
        #: 것처럼 읽힌다 — 사실은 17초가 이 도구가 심은 대기다. 재는 사람이 심은
        #: 시간을 재는 대상의 시간으로 적는 것이 착시 ⑤다.
        settle = 0
        try:
            if "go" in step:
                what = f"주소 {step['go']}"
                page.goto(f"{web}{step['go']}", wait_until="networkidle", timeout=60_000)
                settle = 5_000
                page.wait_for_timeout(settle)
            elif "click" in step:
                role, name = step["click"]
                what = f"{role} 「{name}」 누름"
                target = page.get_by_role(role, name=name)
                if not target.count():
                    raise RuntimeError(
                        f"390px 화면에 {role} 「{name}」 가 없다 — **모바일에서 누를 수 "
                        f"없는 자리**이거나 이름이 바뀌었다")
                target.first.click()
                out["clicks"] += 1
                settle = 5_000
                page.wait_for_timeout(settle)
            elif "click_text" in step:
                what = f"글자 「{step['click_text']}」 누름"
                target = page.get_by_text(step["click_text"], exact=False)
                if not target.count():
                    raise RuntimeError(
                        f"390px 화면에 「{step['click_text']}」 가 없다")
                target.first.click()
                out["clicks"] += 1
                settle = 5_000
                page.wait_for_timeout(settle)
            elif "click_row" in step:
                n = step["click_row"]
                what = f"표 {n}번째 줄 누름"
                rows = page.get_by_role("row")
                # 0번째는 머리글이다. 사람이 누르는 것은 그 아래 첫 줄이다.
                if rows.count() <= n:
                    raise RuntimeError(f"표에 누를 줄이 없다 (줄 {rows.count()}개)")
                rows.nth(n).click()
                out["clicks"] += 1
                settle = 6_000
                page.wait_for_timeout(settle)
            body = page.inner_text("body")
            if step["see"] not in body:
                raise RuntimeError(
                    f"「{step['see']}」 가 화면에 없다 — 본문: {body[:200]!r}")
        except Exception as exc:                                # noqa: BLE001
            # ★ [실측 2026-09-05 TC] **로그인 화면으로 튕긴 것은 화면의 결함이 아니다.**
            #   이 환경은 동시 접속 1개다 — 걷는 도중 다른 차선이 로그인하면 이쪽 세션이
            #   그 자리에서 끝나고, 다음 걸음은 전부 로그인 화면을 본다.
            #   그것을 「이 자리를 못 누른다」로 적으면 **환경의 사실을 화면의 결함으로**
            #   기록하는 것이고, 그 기록은 다음 사람을 없는 버그로 하루 보내게 한다(D-322).
            if page.url.rstrip("/").endswith("/login"):
                out["session_lost"] = True
            out["failed_at"] = i
            ms = round((time.perf_counter() - started) * 1000)
            out["steps"].append({"n": i, "what": what, "ok": False, "ms": ms,
                                 "settle_ms": settle, "net_ms": max(ms - settle, 0),
                                 "why": f"{type(exc).__name__}: {exc}"[:300]})
            break
        ms = round((time.perf_counter() - started) * 1000)
        out["steps"].append({"n": i, "what": what, "ok": True, "ms": ms,
                             "settle_ms": settle, "net_ms": max(ms - settle, 0)})
    else:
        out["completed"] = True
    out["ms"] = round((time.perf_counter() - started_all) * 1000)
    #: **심은 대기를 뺀** 시간. 표에 적는 수는 이쪽이다.
    out["net_ms"] = sum(s.get("net_ms", 0) for s in out["steps"])
    return out


def _logout(page, api: str) -> bool:
    """**세션을 닫는다.** 브라우저가 가진 토큰으로 그대로 부른다 — 다시 로그인해서
    닫으면 그 사이에 세션이 하나 더 생기고, 그것이 정확히 이 절이 막으려는 일이다."""
    try:
        token = page.evaluate(
            "() => { try { const u = JSON.parse(localStorage.getItem('userInfo')"
            " || '{}'); return u.access_token || u.token || ''; } catch (e)"
            " { return ''; } }")
        if not token:
            return False
        got = page.evaluate(
            """async ([api, token]) => {
                const r = await fetch(api + '/api/v1/auth/logout', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json',
                              'Authorization': 'Bearer ' + token},
                    body: '{}'});
                return r.status;
            }""", [api, token])
        return int(got) in (200, 201, 204)
    except Exception:                                           # noqa: BLE001
        return False


def walk(*, web: str, api: str, user: str, password: str) -> dict:
    from playwright.sync_api import sync_playwright

    result = {"viewport": VIEWPORT, "web": web, "api": api,
              "when": datetime.now().replace(microsecond=0).isoformat(),
              "names_from_perf_load": _scenario_names(),
              "walks": {}, "console_errors": {}, "session_closed": None,
              "not_walked": NOT_WALKED}

    current = {"key": "login"}
    errors: dict = {"login": []}
    #: 화면이 부른 **우리 API 중 실패한 것**. 콘솔 줄만 보면 「Network Error」까지만
    #: 보이고 **무엇이 왜 실패했는지**가 안 남는다 — 그 한 줄이 다음 사람의 하루다.
    api_failures: dict = {}

    def note(kind: str, text: str) -> None:
        errors.setdefault(current["key"], []).append(f"{kind}: {text}"[:200])

    def note_response(r) -> None:
        try:
            if r.status >= 400 and "/api/" in r.url:
                api_failures.setdefault(current["key"], []).append(
                    f"{r.status} {r.request.method} {r.url}"[:200])
        except Exception:                                       # noqa: BLE001
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()
        # ★ **두 가지를 다 듣는다**: 잡히지 않은 예외(pageerror)와 `console.error`.
        #   전자만 들으면 화면이 스스로 삼킨 오류가 안 보인다.
        page.on("pageerror", lambda e: note("pageerror", str(e)))
        page.on("console",
                lambda m: note("console.error", m.text) if m.type == "error" else None)
        page.on("response", note_response)
        try:
            _login(page, web, user, password)
            for key, steps in WALKS.items():
                current["key"] = key
                errors.setdefault(key, [])
                result["walks"][key] = _one_walk(page, web, key, steps)
        finally:
            result["session_closed"] = _logout(page, api)
            browser.close()
    result["console_errors"] = errors
    result["api_failures"] = api_failures
    result["session_lost"] = any(w.get("session_lost")
                                 for w in result["walks"].values())
    return result


def _evidence_dir() -> Path:
    """증거 자리. 컨테이너는 저장소를 `/repo`, 문서를 `/docs` 로 **따로** 붙인다 —
    `capture_screens` 가 같은 함정을 이미 밟았다. 자리를 하나로 못 박지 않는다."""
    #: ★ [실측 2026-09-05 TC] `agent/evidence` 가 **있는지**만 보면 틀린다 —
    #:   컨테이너의 `/repo/docs` 는 마운트가 아니라 **빈 껍데기**이고, 거기에 쓰면
    #:   증거가 컨테이너 안에서 사라진다(호스트에서 안 보인다). 그래서 **정본 파일**이
    #:   있는 자리를 고른다: 「폴더가 있다」와 「그 폴더가 그 폴더다」는 다른 사실이다.
    marker = Path("agent") / "evidence" / "D-346" / "ga_readiness.yaml"
    for base in (Path("/docs"), ROOT / "docs"):
        if (base / marker).is_file():
            return base / "agent" / "evidence" / "UX-WALK"
    return ROOT / "docs" / "agent" / "evidence" / "UX-WALK"


def main() -> int:
    ap = argparse.ArgumentParser(description="S1·S2·S3 시나리오 걷기 (390px)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--web", default=os.environ.get("GX_WEB", "http://localhost:3002"))
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--user", default=os.environ.get("GX_ROUTE_USER", ""))
    ap.add_argument("--password", default=os.environ.get("GX_ROUTE_PASSWORD", ""))
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL
    if not args.user or not args.password:
        print(f"{TAG} **판정 불가** — 계정이 없다. 이 도구는 계정을 만들지 않는다 "
              f"(만들면 대장에 없는 계정이 생기고 비밀번호가 소스에 박힌다)")
        return EXIT_UNDECIDABLE

    try:
        result = walk(web=args.web, api=args.api, user=args.user,
                      password=args.password)
    except Exception as exc:                                    # noqa: BLE001
        print(f"{TAG} **판정 불가** — 걷지 못했다: {type(exc).__name__}: {exc}")
        print(f"{TAG} 화면(3002)·API(8000)·playwright 셋이 다 있어야 걷는다")
        return EXIT_UNDECIDABLE

    if result.get("session_lost"):
        print(f"{TAG} **판정 불가** — 걷는 도중 **세션을 빼앗겼다**(로그인 화면으로 튕겼다). "
              f"이 환경은 동시 접속 1개다: 다른 차선이 로그인하면 이쪽이 끝난다. "
              f"화면의 결함이 아니므로 빨강으로 적지 않는다 — **다시 걷는다.**")

    names = result["names_from_perf_load"]
    print(f"{TAG} [환경] {VIEWPORT['width']}×{VIEWPORT['height']}px · {args.web} · "
          f"{result['when']}")
    for key in WALKS:
        w = result["walks"].get(key, {})
        print(f"{TAG} {key} {names.get(key, '?')}")
        print(f"{TAG}    클릭 {w.get('clicks', '?')}회 · "
              f"실걸음 {w.get('net_ms', '?')}ms (심은 대기 뺀 수) · "
              f"총 {w.get('ms', '?')}ms · "
              f"콘솔 오류 {len(result['console_errors'].get(key, []))}건 · "
              f"{'완주' if w.get('completed') else '멈춤(걸음 %s)' % w.get('failed_at')}")
        for s in w.get("steps", ()):
            print(f"{TAG}      {'  ' if s['ok'] else 'X '}{s['n']}. {s['what']} "
                  f"({s.get('net_ms', s['ms'])}ms + 대기 {s.get('settle_ms', 0)}ms)" + ("" if s["ok"] else f" — {s['why']}"))

    known, unknown = classify_console(result.get("console_errors") or {})
    n_known = sum(len(v) for v in known.values())
    if n_known:
        seen = {}
        for lines in known.values():
            for line in lines:
                why = next((w for tok, w in KNOWN_CONSOLE_NOISE if tok in line), "?")
                seen[why] = seen.get(why, 0) + 1
        print(f"{TAG} [알려진 잡음 {n_known}건] — 판정하지 않는다. 목록에 있으니 "
              f"「없다」와 「남의 자리다」가 섞이지 않는다:")
        for why, n in sorted(seen.items(), key=lambda kv: -kv[1]):
            print(f"{TAG}      {n:3}건 · {why}")
    fails = result.get("api_failures") or {}
    if fails:
        print(f"{TAG} [화면이 부른 API 중 실패] — 판정하지 않는다. **다음 사람이 볼 "
              f"자리**로 적어 둔다:")
        for key, lines in fails.items():
            for line in sorted(set(lines))[:6]:
                print(f"{TAG}      {key} · {line}")

    rc = EXIT_UNDECIDABLE if result.get("session_lost") else EXIT_OK
    for (name, ok, why) in judge(result):
        print(f"{TAG} {'  ' if ok else 'X '}{name:22} {why}")
        if not ok and rc != EXIT_UNDECIDABLE:
            rc = EXIT_FAIL

    out = Path(args.json_out) if args.json_out else _evidence_dir() / "walk.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"{TAG} [증거] {out}")
    except OSError as exc:
        print(f"{TAG} ⚠ 증거를 못 남겼다: {exc}")

    print(f"{TAG} " + {
        EXIT_OK: "통과 — 세 시나리오를 걸었고 콘솔은 조용했다. "
                 "★ 클릭 수는 **기준선이지 합격선이 아니다**",
        EXIT_FAIL: "실패 — 위의 X 가 모바일 폭에서 막힌 자리다",
        EXIT_UNDECIDABLE: "**회색** — 세션을 빼앗겨 끝까지 못 걸었다. "
                          "회색은 초록도 빨강도 아니다 (D-301)",
    }[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main())
