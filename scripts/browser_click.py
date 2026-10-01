#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[턴 AS · P-470 · P-478 · 차선 B] **브라우저 측정기** — 사람이 쓰는 브라우저로 누르고,
**페이지를 새로고침한 뒤 화면 글자**에서 값이 바뀌었는지 본다.

옛 이름 `browser_click_22.py` 는 이 파일을 부르는 껍데기다(한 벌만 남는다).

두 갈래
  A) 23 행(F4 12 + O 11) — `click_one` 이 직접 누른다(`--run`).
  B) `click_completes` 48 행 — 누르는 것은 `verify_click_completes` 의 걷기(드라이버)가 이미 한다.
     드라이버가 누른 뒤 **새로고침한 본문**을 `reload` 로 남기고, 여기서 `verdict_48` 이 색을 낸다
     (`--rows48`). 네트워크 응답 재조회는 client 열의 일이고 **이 열에 넣지 않는다**.

판정 규칙(브라우저 없이 시험된다 — `--self-test`)
  * 그 `data-gx` 가 화면에 없다                → 회색 「자리 없음: …」
  * 있는데 잠겼다/눌리지 않는다/준비가 안 섰다 → 회색 「잠김: …」
  * 쓰는 자리(write): 새로고침한 화면 글자가 누르기 전과 같다 → 빨강 · 달라졌다 → 초록
  * 읽는 자리(read) : 새로고침 뒤 그 칸에 읽을 값이 서 있다 → 초록 · 비어 있다 → 빨강
  지어내지 않는다 — 못 쟀으면 회색이고 사유 한 줄이 붙는다.

증거: docs/agent/evidence/P-118/click_completes_browser.json (verify_click_completes 가 읽는다)
  {"measured_at", "spa", "observations": {"<data-gx>"|"<U1#1>": {"verdict": "green|red", "why": ...}}}
  회색은 verdict 를 주지 않고 `grey_why` 를 단다(판정기는 verdict 가 green/red 인 키만 센다).

실행(gx-shell 안 · 동시 접속 1 · 로그인은 /api/v1/auth/login + end_previous_session, 끝나면 logout)
  python scripts/browser_click.py --plan
  python scripts/browser_click.py --self-test
  GX_BROWSER_CLICK_OK=1 python scripts/browser_click.py --measure     # 호스트에서 gx-shell 로 위임
자격은 이 파일에 없다 — 저장소 밖 .env.gates / 환경 변수 이름만 쓴다(값은 출력하지 않는다).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

GREEN, RED, GREY = "green", "red", "grey"
BS = chr(92)                                    # 역슬래시를 코드에 쓰지 않는다
HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path(".")
ROOT = HERE.parent
EVID = ROOT / "docs" / "agent" / "evidence" / "P-118"
OUT = EVID / "click_completes_browser.json"
SHOTS = EVID / "browser_shots"
API_DEFAULT = "http://gx-nginx-e:8500"

#: 23 대상 — verify_click_completes.BROWSER_TARGETS 와 같은 순서(자기시험이 대조한다).
TARGETS = (
    ("FWS-F4-02", "fws-f4-02-confirm"), ("FWS-F4-03", "fws-f4-03-declare"),
    ("FWS-F4-04", "fws-f4-04-approve"), ("FWS-F4-05", "fws-f4-05-approve"),
    ("FWS-F4-05", "fws-f4-05-release"), ("FWS-F4-06", "fws-f4-06-record"),
    ("FWS-F4-07", "fws-f4-07-main-out"), ("FWS-F4-07", "fws-f4-07-extinguished"),
    ("FWS-F4-08", "fws-f4-08-approve"), ("FWS-F4-10", "fws-f4-10-golden-reason"),
    ("FWS-F4-11", "fws-f4-11-sunset"), ("FWS-F4-12", "fws-f4-12-record"),
    ("O-01", "o-01-issue"), ("O-06", "o-06-respond"), ("O-06", "o-06-escalate"),
    ("O-06", "o-06-close"), ("O-07", "o-07-receipt"), ("O-08", "o-08-tenants"),
    ("O-09", "o-09-approve"), ("O-10", "o-10-rotate"), ("O-11", "o-11-deploys"),
    ("O-12", "o-12-deploy-scenario"), ("O-12", "o-12-end-scenario"),
)

#: 계정 후보(이름은 저장소에 이미 있는 시드 역할 계정). 값은 환경 변수 GX_SEED_ROLE_PASSWORD.
F4_ACCOUNTS = ("gxseed_u2_manager", "gxseed_u5_sysop", "gxseed_u4_official")
O_ACCOUNTS = ("gxseed_u5_sysop", "gxseed_u2_manager")

# ──────────────────────────────────────────────────────────────────────────
# 대상 명세 — watch: 값이 바뀌어야 하는 칸(data-gx) · fills: 누르기 전에 채울 입력 칸
#   kind "write" = 눌러서 쓴다 · "read" = 보드를 열어 읽는다(누름 = 그 보드 열기)
#   {s} = 이번 회 표식(시각) — 같은 글자를 두 번 써서 「안 바뀐」 빨강이 나지 않게 한다
#   irreversible: 되돌림 문이 없는 쓰기 — 보고의 「되돌리지 못한 것」에 그대로 적힌다
# ──────────────────────────────────────────────────────────────────────────
F4 = {"group": "F4", "path": "/fws/command", "kind": "write"}
O = {"group": "O", "path": "/ops", "kind": "write"}
SPECS = {
    "fws-f4-02-confirm": dict(F4, watch="fws-f4-02-current",
                              fills=[("fws-f4-02-reason", "P-470 측정 {s}")],
                              irreversible="대응단계 이력 +1 (이력 삭제 문 없음)"),
    "fws-f4-03-declare": dict(F4, watch="fws-f4-03-current",
                              fills=[("fws-f4-03-address", "P-470 측정 {s}"),
                                     ("fws-f4-03-org", "측정반 {s}")],
                              irreversible="지휘본부 설치 선언 (덮어쓰기만 가능)"),
    "fws-f4-04-approve": dict(F4, watch="fws-f4-04-latest",
                              fills=[("fws-f4-04-org", "측정 {s}"), ("fws-f4-04-lat", "37.5"),
                                     ("fws-f4-04-lng", "127.0")],
                              irreversible="헬기 요청 승인 기록 (삭제 문 없음)"),
    "fws-f4-05-approve": dict(F4, watch="fws-f4-05-status",
                              irreversible="대피 명령 승인 기록 (해제 문으로 상태만 되돌림)"),
    "fws-f4-05-release": dict(F4, watch="fws-f4-05-status",
                              fills=[("fws-f4-05-release-reason", "P-470 측정 {s}")],
                              irreversible="해제 기록 (기록은 남는다)"),
    "fws-f4-06-record": dict(F4, watch="fws-f4-06-records",
                             fills=[("fws-f4-06-detail", "P-470 측정 {s}")],
                             irreversible="협조 요청 기록 (삭제 문 없음)"),
    "fws-f4-07-main-out": dict(F4, watch="fws-f4-07-declarations",
                               irreversible="주불 진화 선언 (취소 문 없음)"),
    "fws-f4-07-extinguished": dict(F4, watch="fws-f4-07-declarations",
                                   fills=[("fws-f4-07-reason", "P-470 측정 {s}")],
                                   irreversible="진화 완료 선언 — 사건 종결 축 (취소 문 없음)"),
    "fws-f4-08-approve": dict(F4, watch="fws-f4-08-approvals",
                              irreversible="상황보고 승인 기록 (취소 문 없음)"),
    "fws-f4-10-golden-reason": dict(F4, watch="fws-f4-10-golden",
                                    fills=[("fws-f4-10-reason", "P-470 측정 {s}")],
                                    irreversible="골든타임 초과 사유 기록 (덮어쓰기만 가능)"),
    "fws-f4-11-sunset": dict(F4, watch="fws-f4-11-badge",
                             fills=[("fws-f4-11-sunset-at", "{dt}")],
                             irreversible="일몰 시각 (덮어쓰기만 가능)"),
    "fws-f4-12-record": dict(F4, watch="fws-f4-12-meetings",
                             fills=[("fws-f4-12-decision", "P-470 측정 {s}")],
                             irreversible="상황판단회의 기록 (삭제 문 없음)"),
    "o-01-issue": dict(O, tab="o-01", watch="o-01-board",
                       fills=[("o-01-code", "gxprobe-b-{s}"), ("o-01-name", "측정 {s}"),
                              ("o-01-admin-username", "gxprobe_b_{s}"),
                              ("o-01-admin-email", "gxprobe_b_{s}@example.invalid"),
                              ("o-01-admin-password", "{pw}")],
                       irreversible="테넌트 1개 + 그 관리자 계정 발급 (삭제 문 없음)"),
    "o-06-respond": dict(O, tab="o-06", watch="o-06-board", row="P-470", ensure="incident"),
    "o-06-escalate": dict(O, tab="o-06", watch="o-06-board", row="P-470", ensure="incident"),
    "o-06-close": dict(O, tab="o-06", watch="o-06-board", row="P-470", ensure="incident",
                       fills=[("o-06-cause", "P-470 측정 원인")], show_all="o-06-show-all"),
    "o-07-receipt": dict(O, tab="o-07", watch="o-07-receipt", kind="read"),
    "o-08-tenants": dict(O, tab="o-08", watch="o-08-tenants", kind="read"),
    "o-09-approve": dict(O, tab="o-09", watch="o-09-board", row="P-470", ensure="access"),
    "o-10-rotate": dict(O, tab="o-10", watch="o-10-board", confirm="popconfirm",
                        row_pref=("gx", "probe", "seed", "drill", "훈련"),
                        irreversible="키 1개 회전 (옛 키는 쓸 수 없다 — 되돌림 문 없음)"),
    "o-11-deploys": dict(O, tab="o-11", watch="o-11-deploys", kind="read"),
    "o-12-deploy-scenario": dict(O, tab="o-12", watch="o-12-board",
                                 fills=[("o-12-scenario", "p470-{s}")], select="o-12-tenant",
                                 revert_by="o-12-end-scenario"),
    "o-12-end-scenario": dict(O, tab="o-12", watch="o-12-board",
                              fills=[("o-12-scenario", "p470-{s}")], select="o-12-tenant"),
}


# ══════════════════════════════════════════════════════════════════════════
# 순수 판정 — 브라우저 없이 시험된다
# ══════════════════════════════════════════════════════════════════════════
def meaningful(text) -> bool:
    """읽을 값이 서 있나 — 공백·줄표만 있으면 값이 아니다."""
    skip = "—–-·|:/"
    return any(not (ch.isspace() or ch in skip) for ch in str(text or ""))


def decide(kind, found, clicked, before, after, lock_why=""):
    """(verdict|None, 사유 한 줄). verdict None = 회색.

    found False → 자리 없음 · lock_why/clicked False → 잠김 · 그 밖에는 쓰기/읽기 규칙.
    """
    if not found:
        return None, "자리 없음: 그 data-gx 가 화면에 없다"
    if lock_why:
        return None, "잠김: " + lock_why
    if not clicked:
        return None, "잠김: 눌리지 않는다"
    if kind == "read":
        if meaningful(after):
            return GREEN, "새로고침 뒤에도 그 칸에 값이 서 있다"
        return RED, "새로고침 뒤 그 칸이 비어 있다"
    if (before or "") != (after or ""):
        return GREEN, "새로고침한 화면 글자가 누르기 전과 달라졌다"
    return RED, "눌렀는데 새로고침한 화면 글자가 그대로다 — 값이 안 바뀌었다"


def verdict_48(obs):
    """click_completes 한 행의 관측(드라이버 출력) → (verdict|None, 사유 한 줄).

    드라이버의 `reload` = {ok, before_text, after_text, url}. 네트워크 재조회 값(state.after)은
    **화면에서 확인하는 용도로만** 쓴다 — 서버가 낸 값이 새로고침한 화면에 글자로 있나.
    """
    ctl = (obs or {}).get("control") or {}
    calls_none = (obs or {}).get("reload") is None
    if not ctl.get("found"):
        why = str(ctl.get("why") or "")
        if "HTTP" in str(ctl.get("name") or ""):
            return None, "자리 없음: 기계 흐름 — 화면이 없다"
        low = ("튕겼" in why or "들어가지 못했" in why or "끊겼" in why
               or "준비가 안 섰" in why or "표본" in why or "미판정" in why)
        return None, ("잠김: " if low else "자리 없음: ") + (why[:80] or "누를 자리가 없다")
    if ctl.get("clicked") is False:
        return None, "잠김: " + str(ctl.get("why") or "눌리지 않는다")[:80]
    if (ctl.get("name") or "") == "HTTP" or calls_none:
        return None, "자리 없음: 새로고침 관측이 없다(기계 흐름이거나 드라이버가 못 남겼다)"
    rl = obs["reload"]
    if not rl.get("ok"):
        return None, "잠김: " + str(rl.get("why") or "새로고침을 못 했다")[:80]
    st = obs.get("state") or {}
    kind = st.get("kind")
    before, after = rl.get("before_text") or "", rl.get("after_text") or ""
    if kind == "route_change":
        if "/login" not in str(rl.get("url") or ""):
            return GREEN, "새로고침 뒤에도 로그인 화면이 아니다"
        return RED, "새로고침 뒤 로그인 화면으로 돌아갔다"
    if kind == "status_is":
        return None, "자리 없음: 상태코드를 재는 행 — 화면 글자가 값이 아니다"
    val = st.get("after")
    shown = str(val) in after if val not in (None, "") else False
    if kind == "server_change":
        if before != after and shown:
            return GREEN, "서버가 낸 새 값이 새로고침한 화면 글자에 있고 화면이 달라졌다"
        if not shown:
            return RED, "새로고침한 화면 글자에 서버가 낸 새 값이 없다"
        return RED, "새로고침한 화면 글자가 누르기 전과 같다"
    if kind == "server_reflect" or ctl.get("name") == "화면 열기":
        if meaningful(after) and (shown or val in (None, "")):
            return GREEN, "새로고침 뒤에도 서버 값이 화면 글자로 서 있다"
        return RED, "새로고침 뒤 화면 글자에 서버 값이 없다"
    return None, "자리 없음: 이 행의 술어 종류를 화면 글자로 못 푼다"


def merge_evidence(old, targets23, rows48, spa, now=None):
    """증거 json 한 벌 — 키 충돌 없이 23(data-gx) + 48(U#n)을 한 observations 에 담는다."""
    obs = dict(((old or {}).get("observations")) or {})
    for key, (v, why, extra) in dict(list(targets23.items()) + list(rows48.items())).items():
        rec = dict(extra or {})
        if v in (GREEN, RED):
            rec.update(verdict=v, why=why)
        else:
            rec.update(grey_why=why)
        obs[key] = rec
    return {"measured_at": now or datetime.now().isoformat(timespec="seconds"),
            "spa": spa, "observations": obs}


# ══════════════════════════════════════════════════════════════════════════
# 브라우저 쪽 — gx-shell 안에서만 돈다
# ══════════════════════════════════════════════════════════════════════════
def region_text(page, gx):
    try:
        loc = page.locator('[data-gx="%s"]' % gx)
        return loc.first.inner_text(timeout=4000) if loc.count() else ""
    except Exception:
        return ""


def ui_login(page, spa, user, pw):
    page.goto(spa + "/login", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2200)
    page.fill("input[name=username]", user)
    page.fill("input[name=password]", pw)
    page.click("button.login-button")
    end = time.time() + 25
    while time.time() < end:
        if "/login" not in page.url:
            page.wait_for_timeout(2500)
            return True
        try:
            b = page.get_by_role("button", name=re.compile("Confirm|확인"))
            if b.count() and b.first.is_visible():
                b.first.click()
        except Exception:
            pass
        page.wait_for_timeout(1000)
    return "/login" not in page.url


def antd_select_first(page, gx, prefer=()):
    """antd Select 를 열어 첫(선호) 옵션을 고른다. 못 고르면 False."""
    try:
        page.locator('[data-gx="%s"]' % gx).first.click(timeout=5000)
        page.wait_for_timeout(500)
        opts = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
        n = opts.count()
        if not n:
            return False
        pick = 0
        for i in range(n):
            t = (opts.nth(i).inner_text() or "").lower()
            if any(p in t for p in prefer):
                pick = i
                break
        opts.nth(pick).click(timeout=5000)
        page.wait_for_timeout(400)
        return True
    except Exception:
        return False


def enter_screen(page, spec, ctx):
    """화면에 들어간다(새로고침 뒤에도 같은 길로). F4 는 사건 번호를 넣고 불러온다 · O 는 탭을 연다."""
    page.goto(ctx["spa"] + spec["path"], wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2500)
    if "/login" in page.url:
        return False, "로그인 화면으로 튕겼다"
    if spec["group"] == "F4":
        box = page.locator('[data-gx="fws-f4-01-event-id"]')
        if not box.count():
            return False, "지휘 화면이 안 열렸다(이 계정은 /fws/command 가 없다)"
        box.first.fill(str(ctx["event"]))
        page.locator('[data-gx="fws-f4-01-load"]').first.click(timeout=5000)
        try:
            page.wait_for_selector('[data-gx="fws-f4-01-screen"]', timeout=12000)
        except Exception:
            return False, "사건 %s 의 지휘 화면이 안 떴다" % ctx["event"]
        return True, ""
    if not page.locator('[data-gx="ops-tabs"]').count():
        try:
            page.wait_for_selector('[data-gx="ops-tabs"]', timeout=8000)
        except Exception:
            return False, "플랫폼 운영 화면이 닫혀 있다(U0 아님)"
    tab = page.locator('[data-node-key="%s"]' % spec["tab"])
    if tab.count():
        tab.first.click(timeout=5000)
        page.wait_for_timeout(1500)
    return True, ""


def _fill(page, gx, text):
    el = page.locator('[data-gx="%s"]' % gx)
    if el.count():
        el.first.fill(text)
        return True
    return False


def _find(page, spec, gx):
    """누를 것을 찾는다. row 가 있으면 그 표식 행 안에서만(남의 행은 안 건드린다)."""
    sel = '[data-gx="%s"]' % gx
    if spec.get("row"):
        rows = page.locator("tr", has_text=spec["row"])
        if not rows.count():
            rows = page.locator(".ant-list-item", has_text=spec["row"])
        return rows.first.locator(sel) if rows.count() else page.locator("xpath=//nonexistent")
    if spec.get("row_pref"):
        allb = page.locator(sel)
        for i in range(allb.count()):
            row = allb.nth(i).locator("xpath=ancestor::tr[1]")
            t = (row.inner_text() or "").lower() if row.count() else ""
            if any(p in t for p in spec["row_pref"]):
                return allb.nth(i)
        return page.locator("xpath=//nonexistent")
    return page.locator(sel)


def ensure_precondition(page, spec, ctx):
    """표식 행이 없으면 만든다(남의 행 대신 우리 행을 누르려고). 만들었으면 사유를 돌려준다."""
    kind = spec.get("ensure")
    if kind == "incident" and not page.locator("tr", has_text="P-470").count():
        if antd_select_first(page, "o-06-tenant", prefer=("gx", "훈련")):
            _fill(page, "o-06-summary", "P-470 측정 인시던트 " + ctx["s"])
            page.locator('[data-gx="o-06-open"]').first.click(timeout=5000)
            page.wait_for_timeout(2500)
            ctx["created"].append("인시던트 1건 (P-470 표식 · 종결 문으로 닫는다)")
    if kind == "access" and not page.locator(".ant-list-item", has_text="P-470").count():
        if antd_select_first(page, "o-09-tenant", prefer=("gx", "훈련")):
            _fill(page, "o-09-reason", "P-470 측정 " + ctx["s"])
            page.locator('[data-gx="o-09-request-access"]').first.click(timeout=5000)
            page.wait_for_timeout(2500)
            ctx["created"].append("테넌트 접근 요청 1건 (P-470 표식 · 승인 기록이 감사에 남는다)")


def click_one(page, clause, gx, ctx):
    """한 대상을 누르고 관측 한 건을 돌려준다. 돌려주는 값: (verdict|None, 사유, 관측 사전)."""
    spec = SPECS[gx]
    ex = {"clause": clause, "kind": spec["kind"]}
    if spec.get("irreversible"):
        ex["irreversible"] = spec["irreversible"]
    if spec["group"] == "F4" and not ctx.get("event"):
        return None, "잠김: 훈련 사건이 없다 — 실사건에 선언을 쓰지 않는다", ex
    try:
        ok, why = enter_screen(page, spec, ctx)
        if not ok:
            return None, "잠김: " + why, ex
        ensure_precondition(page, spec, ctx)
        before = region_text(page, spec["watch"])
        ctl = _find(page, spec, gx)
        found = ctl.count() > 0
        lock = ""
        if found and spec["kind"] == "write":
            try:
                if ctl.first.is_disabled():
                    lock = "단추가 잠겨 있다(disabled)"
            except Exception:
                pass
        if not found:
            return decide(spec["kind"], False, False, "", "")[0], decide(spec["kind"], False, False, "", "")[1], ex
        if lock:
            v, w = decide(spec["kind"], True, False, "", "", lock)
            return v, w, ex
        clicked = spec["kind"] == "read"
        if spec["kind"] == "write":
            s = ctx["s"]
            for fgx, tpl in spec.get("fills") or []:
                _fill(page, fgx, tpl.format(s=s, pw=ctx["pw_new"], dt=ctx["dt"]))
            if spec.get("select"):
                antd_select_first(page, spec["select"], prefer=("gx", "probe", "seed", "drill", "훈련"))
            if gx == "fws-f4-05-approve":
                other = "prepare" if "즉시" in before else "immediate"
                r = page.locator('[data-gx="fws-f4-05-urgency"] input[value="%s"]' % other)
                if r.count():
                    r.first.check()
            try:
                ctl.first.click(timeout=8000)
                if spec.get("confirm") == "popconfirm":
                    page.wait_for_timeout(500)
                    page.locator(".ant-popover:not(.ant-popover-hidden) button.ant-btn-primary").first.click(timeout=5000)
                clicked = True
            except Exception as exc:                       # noqa: BLE001
                return None, "잠김: 눌리지 않는다 (%s)" % type(exc).__name__, ex
            page.wait_for_timeout(1800)
        # 새로고침 — 화면 글자만 본다(네트워크 재조회 아님)
        page.reload(wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)
        ok, why = enter_screen(page, spec, ctx)
        if not ok:
            return None, "잠김: 새로고침 뒤 " + why, ex
        if spec.get("show_all"):
            sa = page.locator('[data-gx="%s"]' % spec["show_all"])
            if sa.count():
                sa.first.click(timeout=3000)
                page.wait_for_timeout(800)
        after = region_text(page, spec["watch"])
        SHOTS_C = ctx["shots"]
        try:
            page.screenshot(path="%s/%s.png" % (SHOTS_C, gx), full_page=False)
        except Exception:
            pass
        ex["before_len"], ex["after_len"] = len(before), len(after)
        v, w = decide(spec["kind"], True, clicked, before, after)
        return v, w, ex
    except Exception as exc:                               # noqa: BLE001
        return None, "잠김: 걷다 끊겼다 (%s)" % type(exc).__name__, ex


def pick_event_from_env():
    raw = os.environ.get("GX_F4_EVENT") or ""
    return raw.split(",")[0].strip() or None


def run_in_shell(spa):
    """gx-shell 안에서 도는 본체 — 결과 json 을 stdout 마지막 줄 BROWSER_JSON: 로 낸다."""
    from playwright.sync_api import sync_playwright
    pw_role = os.environ.get("GX_SEED_ROLE_PASSWORD") or ""
    if not pw_role:
        print("자격 환경 변수가 없다 — 재지 않는다(값은 출력하지 않는다)")
        return 2
    shots = "/tmp/gxb_shots"
    os.makedirs(shots, exist_ok=True)
    stamp = datetime.now().strftime("%m%d%H%M%S")
    ctx = {"spa": spa, "event": pick_event_from_env(), "s": stamp, "created": [], "shots": shots,
           "pw_new": "Gx!" + stamp + "pB", "dt": datetime.now().strftime("%Y-%m-%dT18:%M")}
    results = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        for group, accounts in (("F4", F4_ACCOUNTS), ("O", O_ACCOUNTS)):
            mine = [(c, g) for c, g in TARGETS if SPECS[g]["group"] == group]
            done = False
            for user in accounts:
                bc = br.new_context(viewport={"width": 1440, "height": 900}, locale="ko-KR")
                page = bc.new_page()
                seen = [None]
                page.on("request", lambda r: seen.__setitem__(0, (r.headers.get("authorization") or "").split(" ", 1)[-1])
                        if (r.headers.get("authorization") or "").lower().startswith("bearer ") else None)
                try:
                    if not ui_login(page, spa, user, pw_role):
                        bc.close(); time.sleep(13); continue
                    spec0 = SPECS[mine[0][1]]
                    ok, why = enter_screen(page, spec0, ctx)
                    if not ok:
                        print("[BROWSER] %s 로는 %s 화면이 안 열린다: %s" % (user, group, why))
                        _logout(spa, seen[0]); bc.close(); time.sleep(13); continue
                    print("[BROWSER] %s 군은 %s 로 걷는다" % (group, user))
                    for clause, gx in mine:
                        results[gx] = click_one(page, clause, gx, ctx)
                        print("[BROWSER]   %-24s %s %s" % (gx, (results[gx][0] or "grey"), results[gx][1]))
                    done = True
                finally:
                    _logout(spa, seen[0])
                    bc.close()
                if done:
                    break
            if not done:
                for clause, gx in mine:
                    results[gx] = (None, "잠김: 이 군의 화면을 여는 계정이 없다(후보 %d 개 다 닫힘)" % len(accounts),
                                   {"clause": clause})
            time.sleep(13)
        br.close()
    print("BROWSER_JSON:" + json.dumps({"results": results, "created": ctx["created"]}, ensure_ascii=False))
    return 0


def _logout(spa, tok):
    if not tok:
        return
    import urllib.request as U
    try:
        U.urlopen(U.Request(spa + "/api/v1/auth/logout", data=b"{}", method="POST",
                            headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok}),
                  timeout=15)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════
# 호스트 쪽 — gx-shell 로 위임하고 증거를 쓴다
# ══════════════════════════════════════════════════════════════════════════
def _env_gates_names():
    """.env.gates 의 이름=값 중 GX_SEED_ROLE_PASSWORD 만 환경에 올린다(값은 출력하지 않는다)."""
    path = ROOT / ".env.gates"
    if os.environ.get("GX_SEED_ROLE_PASSWORD") or not path.exists():
        return
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^GX_SEED_ROLE_PASSWORD=(.*)$", ln.strip())
        if m:
            os.environ["GX_SEED_ROLE_PASSWORD"] = m.group(1).strip().strip("'" + chr(34))


def _newest_drill_event():
    best = None
    for f in sorted((ROOT / "docs/agent/evidence/P-157/runs").glob("*/drill_seed.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ev = [e for e in d.get("events", []) if e.get("event_type") == "fire"] or d.get("events", [])
        if ev:
            best = str(ev[0]["event_id"])
    return best


def measure(spa, container="gx-shell"):
    if os.environ.get("GX_BROWSER_CLICK_OK") != "1":
        print("[BROWSER] GX_BROWSER_CLICK_OK=1 이 없다 — 누르지 않는다(8500 보호)")
        return 2
    sys.path.insert(0, str(HERE))
    try:
        from v_lock import is_locked
        if is_locked():
            print("[BROWSER] V_LOCK 이 잠겨 있고 내 것이 아니다 — 재지 않는다")
            return 2
    except ImportError:
        pass
    _env_gates_names()
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    ev = os.environ.get("GX_F4_EVENT") or _newest_drill_event() or ""
    src = Path(__file__).read_text(encoding="utf-8")
    cmd = ["docker", "exec", "-i", "-e", "GX_SEED_ROLE_PASSWORD", "-e", "GX_F4_EVENT=" + ev, container,
           "python", "-", "--shell-run", "--spa", spa]
    p = subprocess.run(cmd, input=src.encode("utf-8"), capture_output=True, env=env)
    out = p.stdout.decode("utf-8", "replace")
    print(re.sub(r"BROWSER_JSON:.*", "", out))
    m = re.search(r"BROWSER_JSON:(.*)", out)
    if not m:
        print("[BROWSER] 결과를 못 받았다 rc=%d %s" % (p.returncode, p.stderr.decode("utf-8", "replace")[-600:]))
        return 2
    data = json.loads(m.group(1))
    t23 = {k: tuple(v) for k, v in data["results"].items()}
    rows48 = {}
    cc = EVID / "click_completes.json"
    if cc.exists():
        for key, obs in (json.loads(cc.read_text(encoding="utf-8")).get("observations") or {}).items():
            v, w = verdict_48(obs)
            rows48[key] = (v, w, {})
    old = None
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            old = None
    doc = merge_evidence(old, t23, rows48, spa)
    doc["created_by_measurer"] = data.get("created") or []
    EVID.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8", newline=chr(10))
    subprocess.run(["docker", "cp", container + ":/tmp/gxb_shots/.", str(SHOTS)], env=env, capture_output=True)
    print("[BROWSER] 증거를 썼다: %s" % OUT)
    return 0


def rows48_only():
    """드라이버가 남긴 click_completes.json 의 reload 로 48행 browser 열만 채운다(브라우저 안 켠다)."""
    cc = EVID / "click_completes.json"
    if not cc.exists():
        print("[BROWSER] click_completes.json 이 없다")
        return 2
    rows48 = {}
    for key, obs in (json.loads(cc.read_text(encoding="utf-8")).get("observations") or {}).items():
        v, w = verdict_48(obs)
        rows48[key] = (v, w, {})
    old = None
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    doc = merge_evidence(old, {}, rows48, API_DEFAULT)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8", newline=chr(10))
    n = lambda c: sum(1 for k in rows48 if (rows48[k][0] or GREY) == c)    # noqa: E731
    print("[BROWSER] 48행 browser 열: 초록 %d · 빨강 %d · 회색 %d / %d" % (n(GREEN), n(RED), n(GREY), len(rows48)))
    return 0


def plan() -> int:
    print("[BROWSER] 대상 %d행 (F4 12 + O 11) — 증거: %s" % (len(TARGETS), OUT))
    for clause, gx in TARGETS:
        sp = SPECS[gx]
        print("   %-10s [data-gx=%s] %s %s%s" % (clause, gx, sp["kind"], sp["path"],
                                                " · 되돌림 없음: " + sp["irreversible"] if sp.get("irreversible") else ""))
    return 0


# ══════════════════════════════════════════════════════════════════════════
# 자기시험 — 브라우저 없이 판정 규칙
# ══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    bad = []

    def say(ok, msg):
        print("[BROWSER-ST] %s %s" % ("O" if ok else "X", msg))
        if not ok:
            bad.append(msg)

    # 규칙 셋
    say(decide("write", False, False, "", "")[0] is None
        and decide("write", False, False, "", "")[1].startswith("자리 없음"), "없는 data-gx → 회색(자리 없음)")
    say(decide("write", True, False, "", "", "disabled")[0] is None
        and decide("write", True, False, "", "", "disabled")[1].startswith("잠김"), "잠긴 단추 → 회색(잠김)")
    say(decide("write", True, True, "건수 3", "건수 3")[0] == RED, "값 안 바뀜 → 빨강")
    say(decide("write", True, True, "건수 3", "건수 4")[0] == GREEN, "값 바뀜 → 초록")
    say(decide("read", True, True, "", "—")[0] == RED and decide("read", True, True, "", "2026-10-01")[0] == GREEN,
        "읽는 자리: 줄표뿐 → 빨강 · 값 있음 → 초록")
    # 출생 표본: AR 의 「뼈대라 23 행 회색」 사례 — 뼈대 증거(verdict 없음)는 23 행이 전부 회색이었다.
    skeleton = {"observations": {gx: {"clause": c, "control_found": False, "clicked": False,
                                      "why": "뼈대 — 누름 로직 미구현(V 몫)"} for c, gx in TARGETS}}
    sys.path.insert(0, str(HERE))
    try:
        import verify_click_completes as V
        col = V.browser_targets_column(skeleton)
        say(len(col) == 23 and all(x["browser_clicked"] == GREY for x in col),
            "출생 표본: 뼈대 증거는 23 행 전부 회색(AR 사례)")
        say(tuple(V.BROWSER_TARGETS) == TARGETS, "TARGETS 가 판정기의 BROWSER_TARGETS 와 같다")
        # 새 측정기가 낸 증거는 그 열을 채운다
        t23 = {gx: (GREEN if i % 2 else RED if i % 3 == 0 else None, "시험", {"clause": c})
               for i, (c, gx) in enumerate(TARGETS)}
        doc = merge_evidence(None, t23, {}, "x")
        col2 = V.browser_targets_column(doc)
        want = [x[0] if x[0] else GREY for x in (t23[g] for _, g in TARGETS)]
        say([x["browser_clicked"] for x in col2] == want, "판정기가 새 증거의 verdict 만 센다(회색은 grey_why)")
        say(all("grey_why" in doc["observations"][g] for _, g in TARGETS if t23[g][0] is None), "회색은 사유 한 줄이 붙는다")
    except ImportError as exc:
        say(False, "판정기를 못 불러왔다: %s" % exc)
    say(len(TARGETS) == 23 and set(g for _, g in TARGETS) == set(SPECS), "명세가 23 대상과 한 쌍씩")
    # 48행 규칙
    def obs(kind, after_val, before_t, after_t, ok=True, name="x", found=True, clicked=True):
        return {"control": {"found": found, "clicked": clicked, "name": name},
                "state": {"kind": kind, "after": after_val},
                "reload": {"ok": ok, "before_text": before_t, "after_text": after_t, "url": "/dsm/x"}}
    say(verdict_48(obs("server_change", 5, "발송 4건", "발송 5건"))[0] == GREEN, "48행: 바뀜 → 초록")
    say(verdict_48(obs("server_change", 5, "발송 4건", "발송 4건"))[0] == RED, "48행: 안 바뀜 → 빨강")
    say(verdict_48(obs("server_change", 5, "발송 4건", "발송 4건 다른"))[0] == RED, "48행: 새 값이 글자에 없음 → 빨강")
    say(verdict_48({"control": {"found": False, "why": "못 찾았다"}})[0] is None, "48행: 없는 자리 → 회색")
    say(verdict_48({"control": {"found": True, "clicked": True, "name": "HTTP GET"}})[0] is None, "48행: 기계 흐름 → 회색")
    say(verdict_48(obs("server_change", 5, "a", "b", ok=False))[0] is None, "48행: 새로고침 못 함 → 회색")
    say(verdict_48(obs("status_is", "403", "a", "b"))[0] is None, "48행: 상태코드 행 → 회색")
    say(verdict_48({"control": {"found": True, "clicked": True, "name": "x"}, "state": {"kind": "server_change"}})[0] is None,
        "48행: 새로고침 관측 없음(옛 증거) → 회색 — 지어내지 않는다")
    # 이 파일에 역슬래시 글자를 안 쓴다
    try:
        txt = Path(__file__).read_text(encoding="utf-8")
        say(BS not in txt.replace("chr(92)", ""), "코드에 역슬래시 0")
    except Exception:
        pass
    print("[BROWSER-ST] %s" % ("전부 통과" if not bad else "실패 %d" % len(bad)))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="브라우저 측정기 (P-470)")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--measure", action="store_true", help="호스트에서 gx-shell 로 위임해 23 + 48 을 잰다")
    ap.add_argument("--shell-run", action="store_true", help="(내부) gx-shell 안 본체")
    ap.add_argument("--rows48", action="store_true", help="click_completes.json 의 reload 로 48행 열만 채운다")
    ap.add_argument("--spa", default=API_DEFAULT)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.shell_run:
        return run_in_shell(a.spa)
    if a.measure:
        return measure(a.spa)
    if a.rows48:
        return rows48_only()
    return plan()


if __name__ == "__main__":
    sys.exit(main())
