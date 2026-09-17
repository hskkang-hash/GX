#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""온보딩 48행 **첫 수** — 두 칸(정본 경로 · 누를 문구) 채워진 22행을 셋째 술어로 잰다 (2026-09-17 · 턴 T · V 단독 · P-165 ④).

무엇을 재나
-----------
`docs/agent/onboarding_48.md` 「턴 T · P-159 ①」 절의 표에서 정본 경로와 누를 문구가 **둘 다** 있는 22행.
행마다 셋을 본다 — ① 그 역할 계정으로 로그인해 정본 경로에 닿는가 ② 누를 문구가 **실제로 화면에 보이는가**
③ 셋째 술어([서버 기록]/[화면 상태]/[API 호출])가 서는가. 셋이 다 서면 초록(1) · 정본이 「◐ 상한」이라 적은 행은
서도 반(0.5) · 술어가 안 서면 빨강(0) · **재지 못한 행은 회색**이다(초록이 아니다).

⚠ 재지 못한 것과 안 선 것을 가른다 — 로그인 실패·화면 미도달·예외는 회색(`measured=False`), 술어가 거짓이면 빨강.
⚠ 「정본 없음」 26행은 여기 없다 — 회색 그대로다. 분모 48 은 파일(`onboarding_48.md`)의 행 수다.
⚠ 계정당 세션 1개 · IP 당 로그인 5회/분 — 계정을 바꿀 때마다 **61초** 기다린다(P-157).
⚠ 재조회는 **서버 기록**으로 한다(같은 컨테이너의 Django ORM · HTTP 로그인을 더 쓰지 않는다) — 화면이 그린 값이 아니다.

    docker exec -e GX_SEED_ROLE_PASSWORD -e PYTHONIOENCODING=utf-8 gx-shell \
        python /repo/scripts/measure_onboarding_t.py --snap-event 4798 --seed-a 231073 --seed-b 231074

종료 코드: 0 잰 행이 있다(수는 JSON 에) · 2 못 쟀다(환경 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

TAG = "[ONB-T]"
DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}
GAP_SECONDS = 61            # 계정 바꿀 때 기다리는 시간 (율제한 5/분 · 세션 1개)

# 정본에서 옮긴 문구 — docs/agent/onboarding_48.md 「턴 T」 절 · 글자 그대로
PRODUCT_LINE = "GuardianX는 대응 시간을 잽니다."
FIRST_TIME = "처음이세요?"
LINK_BADGES = ["연계 정상", "연계 대기", "연계 끊김"]
ADMIN_HEADER = "관리자 전용 화면입니다. 아래 표기는 아직 영문입니다."
STATE_WORDS = ["미처리", "접수", "조치 중", "종결"]
ADVANCE_LABELS = ["접수하기", "조치 시작", "종결하기"]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# 서버 기록 — 같은 컨테이너의 ORM (HTTP 로그인을 더 쓰지 않는다)
# ---------------------------------------------------------------------------
_django_ready = False


def orm():
    global _django_ready
    if not _django_ready:
        sys.path.insert(0, "/app")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        # playwright 동기 API 가 이벤트 루프를 스레드에 두므로 Django 가 ORM 을 막는다(SynchronousOnlyOperation · 1차 실행에서 3사람 회색) — 측정 도구라 푼다
        os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
        import django
        django.setup()
        _django_ready = True
    from django.apps import apps
    return apps


def event_row(event_id: int) -> dict:
    DE = orm().get_model("stream_monitors", "DetectionEvent")
    r = DE._base_manager.filter(pk=event_id).values(
        "pk", "verdict", "response_state", "severity", "snapshot_path",
        "stream_monitor__install_address", "stream_monitor__name").first()
    return dict(r or {})


def delivery_count(event_id: int) -> int:
    DR = orm().get_model("stream_monitors", "DeliveryRecord")
    return DR._base_manager.filter(event_id=event_id).count()


def camera_counts(group_id: int = 4) -> dict:
    SM = orm().get_model("stream_monitors", "StreamMonitor")
    qs = SM._base_manager.filter(group_id=group_id)
    blank = qs.filter(install_address__isnull=True).count() + qs.filter(install_address="").count()
    return {"total": qs.count(), "without_address": blank}


def audit_count_for(event_id: int) -> int:
    """감사 행 — 상태 전이가 남긴 행 수. 표에 이벤트 칸이 없으면 -1 (못 셈)."""
    try:
        AL = orm().get_model("logger", "AuditLogs")
        names = {f.name for f in AL._meta.get_fields()}
        for cand in ("event_id", "object_id", "target_id"):
            if cand in names:
                return AL._base_manager.filter(**{cand: event_id}).count()
        return -1
    except Exception:                                   # noqa: BLE001
        return -1


# ---------------------------------------------------------------------------
# 브라우저 — 로그인 · 응답 기록
# ---------------------------------------------------------------------------
class Net:
    """브라우저가 실제로 부른 응답. `/api/` 만 본문을 조금 적는다."""

    def __init__(self):
        self.rows: list = []

    def attach(self, page):
        def on_response(resp):
            try:
                url = resp.url
                row = {"method": resp.request.method, "url": url, "status": resp.status,
                       "ctype": (resp.headers or {}).get("content-type", "")}
                if "/api/" in url and "application/json" in row["ctype"]:
                    try:
                        row["json"] = resp.json()
                    except Exception:                   # noqa: BLE001
                        row["json"] = None
                self.rows.append(row)
            except Exception:                           # noqa: BLE001
                pass
        page.on("response", on_response)

    def mark(self) -> int:
        return len(self.rows)

    def find(self, method: str, needle: str, since: int = 0) -> list:
        return [r for r in self.rows[since:] if r["method"] == method and needle in r["url"]]

    def ok(self, method: str, needle: str, since: int = 0, status=(200,)) -> dict | None:
        hits = [r for r in self.find(method, needle, since) if r["status"] in status]
        return hits[-1] if hits else None


def login(page, net: Net, web: str, user: str, password: str) -> dict:
    """사람이 하는 그대로 — /login 화면 · 두 칸 · Log In · 「다른 기기」 창이 뜨면 Confirm."""
    since = net.mark()
    page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
    try:
        page.wait_for_selector("input", state="visible", timeout=30_000)
    except Exception:                                   # noqa: BLE001
        pass
    page.wait_for_timeout(1_500)
    body_before = page.inner_text("body")
    fields = page.locator("input")
    if fields.count() < 2:
        return {"ok": False, "why": "로그인 칸이 둘 미만", "login_body": body_before[:200]}
    fields.nth(0).fill(user)
    fields.nth(1).fill(password)
    # dj-core 의 단추 글자는 브라우저 locale 을 따른다 — 「Log In」/「로그인」 둘 다 받는다 [실측 2026-09-17]
    submit = page.get_by_role("button", name="Log In")
    if not submit.count():
        submit = page.get_by_role("button", name="로그인")
    submit.first.click()
    page.wait_for_timeout(9_000)
    confirmed = False
    try:
        btn = page.get_by_role("button", name="Confirm")
        if btn.count() and btn.first.is_visible():
            btn.first.click()
            page.wait_for_timeout(9_000)
            confirmed = True
    except Exception:                                   # noqa: BLE001
        pass
    posts = net.find("POST", "/api/v1/auth/login", since)
    # ★ [실측 2026-09-17 · 턴 T · V] 정본 표는 `GET /api/v1/auth/profile` 이라 적었으나 SPA 가 로그인 직후 부르는
    #   것은 `getProfileAPI` = `GET /api/v1/user/get-user-detail/{id}` 다(`frontend/src/features/nav/roleHome.ts:22` ·
    #   runserver 로그에 auth/profile 0건 · get-user-detail 17건). 기대식 오류 — 둘 다 받고 어느 쪽이 섰는지 적는다.
    profile_dj = net.ok("GET", "/api/v1/auth/profile", since)
    profile_spa = net.ok("GET", "/api/v1/user/get-user-detail", since)
    profile = profile_dj or profile_spa
    still_login = page.url.rstrip("/").endswith("/login")
    return {"ok": not still_login, "url": page.url, "end_previous_session": confirmed,
            "login_posts": [p["status"] for p in posts], "profile_200": bool(profile),
            "profile_endpoint": ("/api/v1/auth/profile" if profile_dj else ("/api/v1/user/get-user-detail" if profile_spa else "")),
            "login_body_has_product_line": PRODUCT_LINE in body_before,
            "login_body_has_first_time": FIRST_TIME in body_before,
            "why": ("로그인 뒤에도 /login" if still_login else "")}


def goto(page, web: str, route: str, settle_ms: int = 6_000) -> str:
    page.goto(f"{web}{route}", wait_until="networkidle", timeout=60_000)
    page.wait_for_timeout(settle_ms)
    return page.url


def body(page) -> str:
    try:
        return page.inner_text("body")
    except Exception:                                   # noqa: BLE001
        return ""


def visible_text(page, text: str) -> bool:
    try:
        loc = page.get_by_text(text, exact=False)
        n = loc.count()
        for i in range(min(n, 5)):
            if loc.nth(i).is_visible():
                return True
        return False
    except Exception:                                   # noqa: BLE001
        return False


def click_button(page, name: str, exact: bool = False) -> bool:
    try:
        btn = page.get_by_role("button", name=name, exact=exact)
        if btn.count() and btn.first.is_visible():
            btn.first.click()
            return True
        loc = page.get_by_text(name, exact=exact)
        if loc.count() and loc.first.is_visible():
            loc.first.click()
            return True
    except Exception:                                   # noqa: BLE001
        pass
    return False


def table_cells(page) -> list:
    try:
        return page.evaluate("() => Array.from(document.querySelectorAll('table td')).map(e => e.innerText.trim())")
    except Exception:                                   # noqa: BLE001
        return []


def table_rows(page) -> int:
    try:
        return page.evaluate("() => document.querySelectorAll('table tbody tr').length")
    except Exception:                                   # noqa: BLE001
        return 0


# ---------------------------------------------------------------------------
# 행 — 하나씩. 돌려주는 것: measured · phrase_seen · predicate · verdict · evidence
# ---------------------------------------------------------------------------
def result(row, route, phrase_seen, predicate, evidence, cap_half=False, measured=True, url=""):
    if not measured:
        verdict, score = "gray", None
    elif phrase_seen and predicate:
        verdict, score = ("half", 0.5) if cap_half else ("green", 1.0)
    else:
        verdict, score = "red", 0.0
    return {"row": row, "route": route, "url": url, "phrase_seen": phrase_seen,
            "predicate": predicate, "verdict": verdict, "score": score,
            "cap_half": cap_half, "measured": measured, "evidence": evidence,
            "measured_at": now_iso()}


def measure(web: str, snap_event: int, seed_a: int, seed_b: int, role_pw: str, out_path: str, only=()) -> int:
    from playwright.sync_api import sync_playwright

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    results: list = []
    logins: list = []
    probe_cam = f"GX-ONB-V-{stamp}"

    personas = [
        ("U1", "gxseed_u1_operator", DESKTOP),
        ("U2", "gxseed_u2_manager", DESKTOP),
        ("U3", "gxseed_u1_operator", MOBILE),
        ("U4", "gxseed_u4_official", DESKTOP),
        ("U5", "gxseed_u5_sysop", DESKTOP),
    ]
    if only:
        personas = [p for p in personas if p[0] in only]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        for idx, (pn, user, vp) in enumerate(personas):
            if idx:
                print(f"{TAG} 계정을 바꾼다 — {GAP_SECONDS}초 기다림 (율제한 · 세션 1개)")
                time.sleep(GAP_SECONDS)
            ctx = browser.new_context(viewport=vp)
            page = ctx.new_page()
            net = Net()
            net.attach(page)
            print(f"{TAG} ═══ {pn} · {user} · {vp['width']}px ═══")
            lg = login(page, net, web, user, role_pw)
            logins.append({"persona": pn, "user": user, **lg})
            print(f"{TAG} 로그인 {pn}: ok={lg['ok']} posts={lg.get('login_posts')} profile={lg.get('profile_200')} end_prev={lg.get('end_previous_session')}")
            if not lg["ok"]:
                # 못 잰 행은 회색 — 이 사람의 행 전부
                for row in {"U1": ["U1#1", "U1#2", "U1#3", "U1#8", "U1#9", "U1#11", "U1#19"],
                            "U2": ["U2#1", "U2#2", "U2#4", "U2#6", "U2#19"],
                            "U3": ["U3#1", "U3#2", "U3#7", "U3#9"],
                            "U4": ["U4#8", "U4#11"],
                            "U5": ["U5#2", "U5#4", "U5#5", "U5#15"]}[pn]:
                    results.append(result(row, "", False, False, "로그인 실패 — 못 쟀다: " + lg.get("why", ""), measured=False))
                ctx.close()
                continue
            try:
                fn = {"U1": rows_u1, "U2": rows_u2, "U3": rows_u3, "U4": rows_u4, "U5": rows_u5}[pn]
                fn(page, net, web, results, lg, snap_event=snap_event, seed_a=seed_a, seed_b=seed_b, probe_cam=probe_cam)
            except Exception as exc:                    # noqa: BLE001
                print(f"{TAG} ⚠ {pn} 예외: {type(exc).__name__}: {exc}")
                traceback.print_exc()
            finally:
                try:
                    # 세션을 닫는다 — 다음 사람이 튕기지 않게 (동시 접속 1개)
                    page.evaluate("() => fetch('/api/v1/auth/logout', {method: 'POST'}).catch(() => null)")
                except Exception:                       # noqa: BLE001
                    pass
                ctx.close()
        browser.close()

    measured_rows = [r for r in results if r["measured"]]
    green = sum(1 for r in results if r["verdict"] == "green")
    half = sum(1 for r in results if r["verdict"] == "half")
    red = sum(1 for r in results if r["verdict"] == "red")
    gray = sum(1 for r in results if r["verdict"] == "gray")
    score = sum(r["score"] or 0 for r in results)
    summary = {
        "measured_at": now_iso(), "stamp": stamp, "web": web,
        "denominator": 48, "two_column_rows": 22, "no_canonical_rows_gray": 26,
        "rows_attempted": len(results), "rows_measured": len(measured_rows),
        "green": green, "half": half, "red": red, "gray_measured_fail": gray,
        "score_sum": score, "score_over_48": f"{score}/48",
        "sample": {"snap_event": snap_event, "seed_a": seed_a, "seed_b": seed_b, "probe_camera": probe_cam},
        "logins": logins, "rows": results,
        "rule": "초록 = 문구 보임 + 셋째 술어 섬 · 정본이 ◐ 상한이라 적은 행은 반 · 술어 거짓 = 빨강 · 못 잰 행 = 회색(초록이 아니다) · 정본 없음 26행은 회색 그대로",
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"{TAG} 두 칸 행 22 중 시도 {len(results)} · 초록 {green} · 반 {half} · 빨강 {red} · 회색(못 잼) {gray} · 정본 없음 회색 26")
    print(f"{TAG} **{score}/48** (분모 48 = onboarding_48.md 의 행 수 · 손으로 적지 않았다)")
    for r in results:
        print(f"{TAG}   {r['verdict']:5s} {r['row']:6s} {r['route']:32s} 문구={r['phrase_seen']} 술어={r['predicate']} — {r['evidence'][:150]}")
    print(f"{TAG} [증거] {out_path}")
    return 0


# ---------------------------------------------------------------------------
# U1 · 관제요원 (1440)
# ---------------------------------------------------------------------------
def rows_u1(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam):
    # #1 교대 시작 — 로그인: 로그인 화면 문장 + POST login 200 + GET profile 200
    phrase = lg["login_body_has_product_line"] and lg["login_body_has_first_time"]
    pred = (200 in lg.get("login_posts", [])) and lg.get("profile_200", False)
    out.append(result("U1#1", "/login", phrase, pred,
                      f"login POST {lg.get('login_posts')} · 프로필 200={lg.get('profile_200')} ({lg.get('profile_endpoint') or '둘 다 없음'} — 정본은 auth/profile 이라 적었고 SPA 는 get-user-detail 을 부른다 · 기대식 오류) · 문장={lg['login_body_has_product_line']} · 처음이세요?={lg['login_body_has_first_time']}",
                      url=lg.get("url", "")))

    # #2 전체 상황판: 배지 셋 중 하나 + frame 200 + link-state 200 — 정본이 ◐ 유지 근거를 적었다(카메라 정상/이상 칸 없음)
    m = net.mark()
    url = goto(page, web, "/dsm/dashboard", settle_ms=10_000)
    b = body(page)
    badge = [x for x in LINK_BADGES if x in b]
    frame = net.ok("GET", "/api/dsm/dashboard/frame", m, status=(200, 304))
    link_all = [r["status"] for r in net.find("GET", "/api/dsm/dashboard/link-state", m)]
    # ★ [실측 2026-09-17 · 턴 T · V · 2차 실행] 대시보드는 `link-state` 를 따로 부르지 않는다 — 배지는 `frame.data.link`
    #   (`ControlDashboard.tsx:95` · `services.py:171 dashboard_frame(... link=link_state())`) 에서 온다. 정본 표의
    #   「`GET /api/dsm/dashboard/link-state` 200」은 기대식 오류(호출 0건인데 배지는 떴다). frame 200 + 배지가 술어다.
    fjson = (frame or {}).get("json") or {}
    frame_link = (fjson.get("link") or {}) if isinstance(fjson, dict) else {}
    out.append(result("U1#2", "/dsm/dashboard", bool(badge), bool(frame) and bool(frame_link),
                      f"배지={badge} · frame 200={bool(frame)} · frame.link={frame_link.get('status') if isinstance(frame_link, dict) else frame_link} · link-state 따로 호출 {link_all} (기대식 오류 — 화면은 frame 의 link 를 그린다) · ◐ 상한(카메라 정상/이상 칸 없음 — 정본 표기)",
                      cap_half=True, url=url))

    # #3 죽은 카메라: 카메라 격자 + 자동 순회/순회 멈춤 + 응답 없음 · pulse 200 · 타일 응답 없음/마지막 응답 ≥1
    m = net.mark()
    url = goto(page, web, "/dsm/cameras/grid")
    b = body(page)
    phrase = ("카메라 격자" in b) and (("자동 순회" in b) or ("순회 멈춤" in b)) and ("응답 없음" in b)
    pulse = net.ok("GET", "/api/dsm/cameras/pulse", m)
    tiles = b.count("응답 없음") + b.count("마지막 응답")
    out.append(result("U1#3", "/dsm/cameras/grid", phrase, bool(pulse) and tiles >= 1,
                      f"pulse 200={bool(pulse)} · 「응답 없음」/「마지막 응답」 {tiles}회 · 격자={('카메라 격자' in b)} 순회={('자동 순회' in b) or ('순회 멈춤' in b)}", url=url))

    # #8 이벤트 목록: 단추 넷 + GET /api/dsm/events 200 + 처리 단계 값
    m = net.mark()
    url = goto(page, web, "/dsm/events")
    b = body(page)
    btns = [x for x in ["미처리 보기", "지난 12시간 보기", "내 담당 보기", "시스템 보기"] if x in b]
    ev = net.ok("GET", "/api/dsm/events", m)
    cells = table_cells(page)
    states = [c for c in cells if c in STATE_WORDS]
    out.append(result("U1#8", "/dsm/events", len(btns) == 4, bool(ev) and len(states) >= 1,
                      f"단추={btns} · GET events 200={bool(ev)} · 처리 단계 값 {len(states)}칸 {sorted(set(states))}", url=url))

    # #9 이벤트 상세: 등급 배지 + GET /api/dsm/events/{id} 200 (서버 재조회)
    m = net.mark()
    url = goto(page, web, f"/dsm/events/{snap_event}")
    b = body(page)
    badge = [x for x in ["심각", "경계", "주의"] if x in b]
    det = net.ok("GET", f"/api/dsm/events/{snap_event}", m)
    out.append(result("U1#9", "/dsm/events/:id", bool(badge), bool(det),
                      f"배지={badge} · GET events/{snap_event} 200={bool(det)}", url=url))

    # #11 진위 판단: /dsm/queue 「실제로 확인 · 접수」 → POST review-and-acknowledge 200 → 서버 재조회 verdict
    m = net.mark()
    url = goto(page, web, "/dsm/queue")
    b = body(page)
    label = "실제로 확인 · 접수"
    seen = visible_text(page, label)
    evidence = ""
    pred = False
    if seen:
        clicked = click_button(page, label)
        page.wait_for_timeout(6_000)
        post = net.find("POST", "/review-and-acknowledge", m) or net.find("POST", "/review", m)
        eid = None
        if post:
            u = post[-1]["url"].split("/api/dsm/events/")[-1]
            try:
                eid = int(u.split("/")[0])
            except ValueError:
                eid = None
        after = event_row(eid) if eid else {}
        pred = bool(post and post[-1]["status"] == 200 and after.get("verdict"))
        evidence = (f"눌렀다={clicked} · POST {[p['status'] for p in post]} {post[-1]['url'].split('/api')[-1][:60] if post else ''} · "
                    f"서버 재조회 event {eid} verdict={after.get('verdict')} state={after.get('response_state')} · 배지 실제={('실제' in body(page))}")
    else:
        others = [x for x in (ADVANCE_LABELS + ["오탐으로 판정"]) if visible_text(page, x)]
        evidence = f"큐 화면에 「{label}」 이 보이지 않는다 — 보이는 단추 {others} · 초점 사건이 미처리가 아니면 이 단추는 없다(데이터 상태) · 본문 {b[:100]!r}"
    out.append(result("U1#11", "/dsm/queue", seen, pred, evidence, url=url))

    # #19 교대 인계 메모: 홈 카드 「인계 메모」 → 「인계 읽기」 → /handover 도달 + 본문 (68자 그대로면 빨강 · P-98)
    m = net.mark()
    url = goto(page, web, "/dsm/home")
    b = body(page)
    seen = ("인계 메모" in b) and (("인계 읽기" in b) or ("인계 메모 쓰기" in b))
    pred = False
    evidence = ""
    if seen:
        clicked = click_button(page, "인계 읽기") or click_button(page, "인계 메모 쓰기")
        page.wait_for_timeout(8_000)
        reached = "/handover" in page.url
        hb = body(page)
        pred = reached and len(hb) > 68
        evidence = f"눌렀다={clicked} · 도달={reached} ({page.url}) · 본문 {len(hb)}자 (P-98 68자 그대로면 빨강) · 앞부분 {hb[:80]!r}"
        url = page.url
    else:
        evidence = f"홈에 「인계 메모」/「인계 읽기」 카드가 안 보인다 — 본문 앞부분 {b[:120]!r}"
    out.append(result("U1#19", "/dsm/home → /handover", seen, pred, evidence, url=url))


# ---------------------------------------------------------------------------
# U2 · 관제팀장 (1440)
# ---------------------------------------------------------------------------
def rows_u2(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam):
    # #1 밤사이 요약: 「지난 12시간 보기」 → GET summary?hours=12 200 + 수치 또는 「아직 판정한 이벤트가 없습니다」 · 0% 면 빨강
    m = net.mark()
    url = goto(page, web, "/dsm/events")
    seen = visible_text(page, "지난 12시간 보기")
    pred, evidence = False, ""
    if seen:
        click_button(page, "지난 12시간 보기")
        page.wait_for_timeout(6_000)
        s = net.ok("GET", "/api/dsm/events/summary?hours=12", m)
        b = body(page)
        zero_pct = "0%" in b
        none_msg = "아직 판정한 이벤트가 없습니다" in b
        js = (s or {}).get("json") or {}
        measurable = js.get("measurable") if isinstance(js, dict) else None
        # ★ 정본의 「0% 가 뜨면 빨강」은 분모 0 을 0% 로 그리는 착시를 막는 규칙이다 — 서버가 measurable=True 로 낸 0% 는 수다.
        bad_zero = zero_pct and not measurable
        pred = bool(s) and (not bad_zero) and (none_msg or isinstance(js, dict))
        evidence = (f"summary?hours=12 200={bool(s)} · reviewed={js.get('reviewed') if isinstance(js, dict) else '?'} false_positive={js.get('false_positive') if isinstance(js, dict) else '?'} "
                    f"measurable={measurable} unhandled={js.get('unhandled') if isinstance(js, dict) else '?'} · 화면 0%={zero_pct} (분모 0 인 0% 만 빨강) · 없음문장={none_msg}")
        url = page.url
    else:
        evidence = "「지난 12시간 보기」 단추가 안 보인다"
    out.append(result("U2#1", "/dsm/events", seen, pred, evidence, url=url))

    # #2 미처리: ?preset=unhandled · 「미처리 보기」 · GET events?limit=50&response_state=occurred · 처리 단계 열 전부 미처리
    m = net.mark()
    url = goto(page, web, "/dsm/events?preset=unhandled")
    seen = visible_text(page, "미처리 보기")
    g = net.find("GET", "response_state=occurred", m)
    g200 = [r for r in g if r["status"] == 200]
    cells = table_cells(page)
    states = [c for c in cells if c in STATE_WORDS]
    all_unhandled = len(states) >= 1 and all(c == "미처리" for c in states)
    js = (g200[-1].get("json") if g200 else None) or {}
    n_srv = len(js.get("events", [])) if isinstance(js, dict) else -1
    out.append(result("U2#2", "/dsm/events?preset=unhandled", seen, bool(g200) and all_unhandled,
                      f"GET …response_state=occurred 200={bool(g200)} (서버 {n_srv}건) · 처리 단계 칸 {len(states)} 전부 미처리={all_unhandled} {sorted(set(states))}", url=url))

    # #4 심각 이벤트: 배지 심각 · GET snapshot 200 image/jpeg · <img> ≥1 · 주소 칸 비어 있지 않음 — 하나라도 빠지면 ◐
    m = net.mark()
    url = goto(page, web, f"/dsm/events/{snap_event}")
    b = body(page)
    seen = "심각" in b
    snap = [r for r in net.find("GET", f"/api/dsm/events/{snap_event}/snapshot", m)]
    snap_ok = any(r["status"] == 200 and "image/jpeg" in r["ctype"] for r in snap)
    try:
        imgs = page.evaluate("() => Array.from(document.querySelectorAll('img')).filter(i => i.naturalWidth > 0 && (i.src||'').includes('snapshot')).length")
    except Exception:                                   # noqa: BLE001
        imgs = 0
    addr = (event_row(snap_event).get("stream_monitor__install_address") or "").strip()
    addr_on = bool(addr) and addr.split(" (")[0] in b
    full = snap_ok and imgs >= 1 and addr_on
    partial = (snap_ok or imgs >= 1) and not full
    out.append(result("U2#4", "/dsm/events/:id", seen, full or partial,
                      f"snapshot {[r['status'] for r in snap]} jpeg={snap_ok} · img(snapshot, naturalWidth>0)={imgs} · 주소 화면={addr_on} · 셋 다={full}",
                      cap_half=partial, url=url))

    # #6 상황보고서: /report-template · 「보고서 서식」 + 머리줄 · GET reports/templates 200 · 표 행 ≥1 (0 이면 ◐)
    m = net.mark()
    url = goto(page, web, "/report-template", settle_ms=12_000)
    b = body(page)
    seen = ("보고서 서식" in b) and (ADMIN_HEADER in b)
    t = net.ok("GET", "/api/dsm/reports/templates", m)
    rows = table_rows(page)
    out.append(result("U2#6", "/report-template", seen, bool(t),
                      f"templates 200={bool(t)} · 표 행 {rows} (0 이면 ◐) · 보고서 서식={('보고서 서식' in b)} 머리줄={(ADMIN_HEADER in b)} · url={page.url}",
                      cap_half=(rows < 1), url=url))

    # #19 장애 판단: ?preset=system · 「시스템 보기」 · GET events?event_type=camera_down,storage_high 200 · 유형 열이 그 둘뿐
    m = net.mark()
    url = goto(page, web, "/dsm/events?preset=system")
    seen = visible_text(page, "시스템 보기")
    g = [r for r in net.find("GET", "event_type=", m) if r["status"] == 200]
    js = (g[-1].get("json") if g else None) or {}
    evs = js.get("events", []) if isinstance(js, dict) else []
    types = sorted({str(e.get("event_type")) for e in evs})
    only_two = all(t in ("camera_down", "storage_high") for t in types)
    out.append(result("U2#19", "/dsm/events?preset=system", seen, bool(g) and only_two,
                      f"GET event_type=… 200={bool(g)} · 서버 {len(evs)}건 유형={types} · 둘뿐={only_two} (0건이면 빈 상태가 그려져야 한다)", url=url))


# ---------------------------------------------------------------------------
# U3 · 이동 중 (390 · 같은 계정)
# ---------------------------------------------------------------------------
def rows_u3(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam):
    # #1 알림 수신: /dsm/events/:id 「알림 보내기」 → POST notify 200 → deliveries +N (서버 기록) → /m/inbox 에 그 사건 카드
    m = net.mark()
    before = delivery_count(seed_a)
    url = goto(page, web, f"/dsm/events/{seed_a}")
    seen = visible_text(page, "알림 보내기")
    pred, evidence = False, ""
    if seen:
        click_button(page, "알림 보내기")
        page.wait_for_timeout(8_000)
        post = net.find("POST", f"/api/dsm/events/{seed_a}/notify", m)
        after = delivery_count(seed_a)
        b = body(page)
        msg = "발송을 요청했습니다" in b
        url2 = goto(page, web, "/m/inbox")
        ib = body(page)
        card = (f"#{seed_a}" in ib) or (str(seed_a) in ib)
        pred = bool(post and post[-1]["status"] == 200 and after > before and card)
        evidence = f"POST notify {[p['status'] for p in post]} · deliveries {before} → {after} · 결과 문장={msg} · /m/inbox 카드={card}"
        url = url2
    else:
        evidence = "「알림 보내기」 단추가 안 보인다"
    out.append(result("U3#1", "/dsm/events/:id → /m/inbox", seen, pred, evidence, url=url))

    # #2 위치 확인: /m/events/:id 「어디로 가나」 카드 + 주소 문자열 + 「지도에서 보기」
    url = goto(page, web, f"/m/events/{snap_event}")
    b = body(page)
    addr = (event_row(snap_event).get("stream_monitor__install_address") or "").strip()
    seen = visible_text(page, "지도에서 보기")
    pred = ("어디로 가나" in b) and bool(addr) and (addr.split(" (")[0] in b)
    out.append(result("U3#2", "/m/events/:id", seen, pred,
                      f"어디로 가나={('어디로 가나' in b)} · 주소 화면={(addr.split(' (')[0] in b) if addr else False} · 지도에서 보기={seen}", url=url))

    # #7 현장 도착 보고: /m/events/:id 「현장 조치」 → 전이 단추 → POST response 200 → 서버 재조회 전이 + 감사 행
    m = net.mark()
    url = goto(page, web, f"/m/events/{seed_b}")
    b = body(page)
    before = event_row(seed_b)
    labels = [x for x in ADVANCE_LABELS if visible_text(page, x)]
    seen = ("현장 조치" in b) and bool(labels)
    pred, evidence = False, ""
    if seen:
        click_button(page, labels[0])
        page.wait_for_timeout(7_000)
        # 확인 창이 있으면 누른다 (제품 갈래 그대로)
        for name in ("확인", "OK"):
            try:
                c = page.get_by_role("button", name=name, exact=True)
                if c.count() and c.first.is_visible():
                    c.first.click()
                    page.wait_for_timeout(6_000)
                    break
            except Exception:                           # noqa: BLE001
                pass
        post = net.find("POST", f"/api/dsm/events/{seed_b}/response", m)
        after = event_row(seed_b)
        changed = after.get("response_state") != before.get("response_state")
        pred = bool(post and post[-1]["status"] == 200 and changed)
        evidence = (f"단추 {labels[0]} · POST response {[p['status'] for p in post]} · 서버 재조회 {before.get('response_state')} → {after.get('response_state')} · 감사 행={audit_count_for(seed_b)}")
    else:
        evidence = f"현장 조치={('현장 조치' in b)} · 전이 단추={labels}"
    out.append(result("U3#7", "/m/events/:id", seen, pred, evidence, url=url))

    # #9 현장 상황 한 줄: 「현장 회신 — 본 것을 한 줄로」 · 「회신 보내기」 → POST field-reply 200 → field-replies total +1 (재읽기)
    m = net.mark()
    url = goto(page, web, f"/m/events/{seed_b}")
    b = body(page)
    fr = [r for r in net.find("GET", f"/api/dsm/events/{seed_b}/field-replies", m) if r["status"] == 200]
    js0 = (fr[-1].get("json") if fr else None) or {}
    n0 = js0.get("total", len(js0.get("replies", []))) if isinstance(js0, dict) else -1
    seen = ("현장 회신 — 본 것을 한 줄로" in b) and visible_text(page, "회신 보내기")
    pred, evidence = False, ""
    if seen:
        try:
            ta = page.locator("textarea")
            ta.last.fill(f"V 단독 셋째 술어 실측 {datetime.now().strftime('%H:%M:%S')} — 현장 이상 없음")
        except Exception as exc:                        # noqa: BLE001
            evidence = f"글칸 채우기 실패 {type(exc).__name__}"
        click_button(page, "회신 보내기")
        page.wait_for_timeout(7_000)
        post = net.find("POST", f"/api/dsm/events/{seed_b}/field-reply", m)
        m2 = net.mark()
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(6_000)
        fr2 = [r for r in net.find("GET", f"/api/dsm/events/{seed_b}/field-replies", m2) if r["status"] == 200]
        js1 = (fr2[-1].get("json") if fr2 else None) or {}
        n1 = js1.get("total", len(js1.get("replies", []))) if isinstance(js1, dict) else -1
        pred = bool(post and post[-1]["status"] == 200 and n1 == n0 + 1)
        evidence = f"POST field-reply {[p['status'] for p in post]} · field-replies total {n0} → {n1} (다시 읽음)"
    else:
        evidence = f"머리글={('현장 회신 — 본 것을 한 줄로' in b)} · 회신 보내기 보임={visible_text(page, '회신 보내기')}"
    out.append(result("U3#9", "/m/events/:id", seen, pred, evidence, url=url))


# ---------------------------------------------------------------------------
# U4 · 재난안전과 (1440)
# ---------------------------------------------------------------------------
def rows_u4(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam):
    # #8 특정 사건 이력: 「지난 12시간 보기」 → GET events?since=… 200 — 조합 검색 없음 · ◐ 상한
    m = net.mark()
    url = goto(page, web, "/dsm/events")
    seen = visible_text(page, "지난 12시간 보기")
    pred, evidence = False, ""
    if seen:
        click_button(page, "지난 12시간 보기")
        page.wait_for_timeout(6_000)
        g = [r for r in net.find("GET", "/api/dsm/events?", m) if "since=" in r["url"] and r["status"] == 200]
        pred = bool(g)
        evidence = f"GET events?since= 200={bool(g)} · 조합 검색(사건번호·주소·유형) 없음 → ◐ 상한(정본 표기)"
        url = page.url
    else:
        evidence = "「지난 12시간 보기」 단추가 안 보인다"
    out.append(result("U4#8", "/dsm/events", seen, pred, evidence, cap_half=True, url=url))

    # #11 카메라 설치 현황: /device · 「드론·로봇 장비 등록」 + 머리줄 · 표 행 ≥1 (view_only 로 0행이면 빨강)
    url = goto(page, web, "/device", settle_ms=12_000)
    b = body(page)
    seen = ("드론·로봇 장비 등록" in b) and (ADMIN_HEADER in b)
    rows = table_rows(page)
    out.append(result("U4#11", "/device", seen, rows >= 1,
                      f"url={page.url} · 「드론·로봇 장비 등록」={('드론·로봇 장비 등록' in b)} · 머리줄={(ADMIN_HEADER in b)} · 표 행 {rows} · 본문 앞 {b[:80]!r}", url=url))


# ---------------------------------------------------------------------------
# U5 · 시스템 관리자 (1440)
# ---------------------------------------------------------------------------
def rows_u5(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam):
    # #2 역할: /roles · 「역할 관리」 + 머리줄 · 표 행 ≥1 + 「Add New Role」
    url = goto(page, web, "/roles", settle_ms=12_000)
    b = body(page)
    seen = ("역할 관리" in b) and (ADMIN_HEADER in b)
    rows = table_rows(page)
    add = "Add New Role" in b
    out.append(result("U5#2", "/roles", seen, rows >= 1 and add,
                      f"url={page.url} · 역할 관리={('역할 관리' in b)} · 머리줄={(ADMIN_HEADER in b)} · 표 행 {rows} · Add New Role={add} · 본문 앞 {b[:80]!r}", url=url))

    # #4 카메라 등록: /dsm/cameras/import · 「카메라 일괄 등록」 · 「표 먼저 보기」 → dry-run → 적용 → POST import 200 → 카메라 수 +1
    m = net.mark()
    c0 = camera_counts()
    url = goto(page, web, "/dsm/cameras/import")
    b = body(page)
    seen = ("카메라 일괄 등록" in b) and ("표 먼저 보기" in b)
    pred, evidence = False, ""
    if seen:
        csv = "name,code,ip_source,address,detail" + chr(10) + f"{probe_cam},{probe_cam},rtsp://10.0.0.250/probe,,V 단독 실측 씨앗"
        try:
            page.locator("textarea").first.fill(csv)
        except Exception as exc:                        # noqa: BLE001
            evidence = f"글칸 채우기 실패 {type(exc).__name__} · "
        clicked1 = click_button(page, "표 먼저 보기")
        page.wait_for_timeout(7_000)
        clicked2 = click_button(page, "이 표대로 적용")
        page.wait_for_timeout(8_000)
        posts = net.find("POST", "/api/dsm/cameras/import", m)
        c1 = camera_counts()
        pred = bool(posts) and any(p["status"] == 200 for p in posts) and c1["total"] == c0["total"] + 1
        evidence += f"표 먼저 보기={clicked1} · 적용={clicked2} · POST import {[p['status'] for p in posts]} · 카메라 수 {c0['total']} → {c1['total']} (서버 기록)"
    else:
        evidence = f"카메라 일괄 등록={('카메라 일괄 등록' in b)} · 표 먼저 보기={('표 먼저 보기' in b)}"
    out.append(result("U5#4", "/dsm/cameras/import", seen, pred, evidence, url=url))

    # #5 주소 채우기: /dsm/cameras/address · 문구 셋 · 이름+주소 → 표 먼저 보기 → 채우기 → 미입력 수 -1 (서버 기록)
    m = net.mark()
    g0 = camera_counts()
    url = goto(page, web, "/dsm/cameras/address")
    b = body(page)
    seen = ("카메라 주소 채우기" in b) and ("표 먼저 보기" in b) and ("채우기" in b)
    pred, evidence = False, ""
    if seen:
        try:
            inputs = page.locator("input[type=text], input:not([type])")
            inputs.nth(0).fill(probe_cam)
            inputs.nth(1).fill("경기도 안양시 만안구 안양로 123")
            inputs.nth(2).fill("V 단독 실측")
        except Exception as exc:                        # noqa: BLE001
            evidence = f"칸 채우기 실패 {type(exc).__name__} · "
        clicked1 = click_button(page, "표 먼저 보기")
        page.wait_for_timeout(7_000)
        clicked2 = click_button(page, "채우기", exact=True)
        page.wait_for_timeout(8_000)
        posts = net.find("POST", "/api/dsm/cameras/import", m)
        g1 = camera_counts()
        gap_calls = [r["status"] for r in net.find("GET", "/api/dsm/cameras/address-gap", m)]
        pred = bool(posts) and any(p["status"] == 200 for p in posts) and g1["without_address"] == g0["without_address"] - 1
        evidence += f"표 먼저 보기={clicked1} · 채우기={clicked2} · POST import {[p['status'] for p in posts]} · address-gap GET {gap_calls} · 미입력 {g0['without_address']} → {g1['without_address']} (서버 기록)"
    else:
        evidence = f"주소 채우기={('카메라 주소 채우기' in b)} · 표 먼저 보기={('표 먼저 보기' in b)} · 채우기={('채우기' in b)}"
    out.append(result("U5#5", "/dsm/cameras/address", seen, pred, evidence, url=url))

    # #15 저장 용량: /dsm/metering · 「이번 달 사용량」 + 「저장 용량」 · GET metering 200 · % 없으면 ◐
    m = net.mark()
    url = goto(page, web, "/dsm/metering")
    b = body(page)
    seen = ("이번 달 사용량" in b) and ("저장 용량" in b)
    g = net.ok("GET", "/api/dsm/metering", m)
    pct = "%" in b
    out.append(result("U5#15", "/dsm/metering", seen, bool(g),
                      f"metering 200={bool(g)} · 화면에 %={pct} (없으면 ◐ — 상한 미선언) · 이번 달 사용량={('이번 달 사용량' in b)} 저장 용량={('저장 용량' in b)}",
                      cap_half=(not pct), url=url))


def main() -> int:
    ap = argparse.ArgumentParser(description="온보딩 48행 첫 수 — 두 칸 채운 22행 셋째 술어 실측 (V 단독)")
    ap.add_argument("--web", default=os.environ.get("GX_WEB", "http://localhost:3002"))
    ap.add_argument("--snap-event", type=int, required=True, help="snapshot_path·주소가 있는 사건 id")
    ap.add_argument("--seed-a", type=int, required=True, help="알림 보내기 표본 (심각 씨앗)")
    ap.add_argument("--seed-b", type=int, required=True, help="전이·회신 표본 (미처리 씨앗)")
    ap.add_argument("--out", default="")
    ap.add_argument("--only", default="", help="쉼표로 나눈 페르소나만 (예: U1,U3) — 재측용")
    args = ap.parse_args()
    pw = os.environ.get("GX_SEED_ROLE_PASSWORD") or ""
    if not pw:
        print(f"{TAG} 자격이 없다 — GX_SEED_ROLE_PASSWORD 를 환경으로 준다 (값은 적지 않는다)")
        return 2
    try:
        import playwright  # noqa: F401
    except ImportError:
        print(f"{TAG} playwright 없음 — 판정 불가")
        return 2
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    # gx-shell 은 docs 를 /docs 에 마운트한다(/repo/docs 는 컨테이너 안 빈 자리 — 1차 실행이 거기 썼다)
    out = args.out or f"/docs/agent/evidence/P-159/onboarding_measure_{stamp}.json"
    only = [x.strip() for x in args.only.split(",") if x.strip()]
    return measure(args.web, args.snap_event, args.seed_a, args.seed_b, pw, out, only=only)


if __name__ == "__main__":
    sys.exit(main())
