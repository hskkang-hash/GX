#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""온보딩 48행 — 두 칸(정본 경로 · 누를 문구)이 **둘 다** 채워진 행을 셋째 술어로 잰다.

  턴 T · P-165 ④ (2026-09-17) 에 **22행**으로 섰고, 턴 V · P-180 (2026-09-18 · 차선 Q) 에
  정본 문서가 채운 **35행**으로 늘었다. **행 목록을 이 파일에 손으로 적지 않는다** — 아래 참조.

무엇을 재나
-----------
`docs/agent/onboarding_48.md` 「턴 T · P-159 ①」 절부터 끝까지의 표에서 정본 경로와 누를 문구가
**둘 다** 있는 행(같은 행이 두 번 나오면 아래 것이 이긴다 — 문서의 「세는 법」과 같은 규칙).
행마다 셋을 본다 — ① 그 역할 계정으로 로그인해 정본 경로에 닿는가 ② 누를 문구가 **실제로 화면에 보이는가**
③ 셋째 술어([서버 기록]/[화면 상태]/[API 호출])가 서는가. 셋이 다 서면 초록(1) · 정본이 「◐ 상한」이라 적은 행은
서도 반(0.5) · 술어가 안 서면 빨강(0) · **재지 못한 행은 회색**이다(초록이 아니다).

★★ [P-180 · 턴 V] **문서와 도구를 같은 변경에 둔다.** 턴 U 에 문서만 31 → 35행이 되고 이 도구는
   턴 T 의 22행 목록을 하드코딩한 채였다 — 그래서 「35행 재측」이 **물리적으로 불가능**했다(조율자 오판 2).
   이제 이 도구는 **정본 문서를 읽어** 행 목록과 분모를 만들고, 제 소스가 실제로 재는 행과 대 본다:

       python scripts/measure_onboarding_t.py --check     # 브라우저 없이 · 갈리면 종료코드 2

⚠ 재지 못한 것과 안 선 것을 가른다 — 로그인 실패·화면 미도달·예외는 회색(`measured=False`), 술어가 거짓이면 빨강.
⚠ 「정본 없음」 행은 여기 없다 — 회색 그대로다. 분모는 파일(`onboarding_48.md`)의 행 수다(손으로 적지 않는다).
⚠ 계정당 세션 1개 · IP 당 로그인 5회/분 — 계정을 바꿀 때마다 **61초** 기다린다(P-157).
⚠ 재조회는 **서버 기록**으로 한다(같은 컨테이너의 Django ORM · HTTP 로그인을 더 쓰지 않는다) — 화면이 그린 값이 아니다.
⚠ 상태를 바꾸는 행은 **되돌린다**(U3#16 차단 시간대 · U4#15 상급 보고 · U5#9 규칙 토글 · U5#1 비활성화).
   게이트가 제품의 상태를 남기면 다음 게이트가 제품 대신 우리를 잰다(턴 T U5#9 → `verify_seed_roles` 빨강).
   되돌리는 문이 **없는** 자리(U5#14 재시작 요청)는 사유를 적고 안 되돌린다 — 잊은 것과 구별되게.

    docker exec -e GX_SEED_ROLE_PASSWORD -e PYTHONIOENCODING=utf-8 gx-shell \
        python /repo/scripts/measure_onboarding_t.py --snap-event 4802 --seed-a 231073 --seed-b 231074

★ [U1 요청 ③ · 2026-09-18] `--snap-event` 를 안 주면 씨앗 명세에서 **`snapshot_path` 가 빈 문자열이
  아닌 첫 사건**을 고른다(U2#4 는 그림을 보는 행이다 — 그림 없는 씨앗으로 재면 제품이 아니라 씨앗을 잰다).
  명세에 그런 사건이 하나도 없으면 U2#4 는 ◐ 가 아니라 **회색**이다.
  ⚠ 지금 개발 DB 에서 그림이 있는 것이 확인된 사건은 **4802** 다(U1 실측 · 200 image/jpeg 37,594B).
    `capture_screens` 씨앗(`gxprobe-D384-screen-CAM`)은 `snapshot_path` 가 전부 비어 있었다 —
    그 자리는 이 턴에 `capture_screens.py` 가 **제품 경로(K1 `upload_snapshot`)를 타게** 고쳤다.

종료 코드: 0 잰 행이 있다(수는 JSON 에) · 2 못 쟀다(환경 없음) · `--check` 는 문서와 갈리면 2
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path
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

# [P-180 · 턴 V] 정본이 「표가 0행이면 「없다」가 떠야 한다 · 빈 표는 빨강」이라 적은 자리에서
# 「없다」를 읽는 말. 제품의 `StateBoundary` 가 쓰는 빈 상태 문장들이다 — 침묵은 빨강이다.
EMPTY_WORDS = ["없습니다", "0건입니다", "아직 없습니다", "해당 없음"]
NOTIFY_HEADLINE = "알림 받는 사람·채널"       # copy.ts::HEADLINE_COPY.notifySettings
PEOPLE_HEADLINE = "사람·역할 — 계정 만들기 · 비활성화"   # copy.ts::HEADLINE_COPY.people
MOBILE_SETTINGS_HEADLINE = "내 알림 설정"     # copy.ts::HEADLINE_COPY.mobileSettings
MOBILE_INBOX_HEADLINE = "내게 온 이벤트"      # copy.ts::HEADLINE_COPY.mobileInbox
# 씨앗 계정을 만들 때 쓰는 소속(테넌트). `camera_counts` 가 쓰는 그 번호와 같다.
SEED_GROUP_ID = 4


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# 정본 — **행 목록을 손으로 적지 않는다** [P-180 · 2026-09-18 턴 V · 차선 Q]
#
#   턴 U 에 조율자가 문서만 채우고 이 도구를 안 늘렸다(오판 2). 문서는 두 칸 35행인데
#   도구는 턴 T 의 22행을 들고 있어서 「35행 재측」이 **물리적으로 불가능**했다.
#   같은 일이 다시 나지 않게, 이 도구는 이제 **문서를 읽어 행 목록을 만든다** —
#   문서가 늘면 도구가 「내가 아직 안 재는 행」을 스스로 이름으로 말한다.
#
#   ⚠ 세는 법은 `onboarding_48.md` 「세는 법」 절의 것과 **같은 규칙**이다(두 벌을 두지 않는다):
#     턴 T · P-159 ① 절부터 끝까지의 표를 읽고, 같은 행이 두 번 나오면 **아래 것이 이긴다**.
# ---------------------------------------------------------------------------
import re                                               # noqa: E402

CANON_DOC_CANDIDATES = (
    "/docs/agent/onboarding_48.md",                     # gx-shell 은 docs 를 /docs 에 마운트한다
    str(Path(__file__).resolve().parent.parent / "docs" / "agent" / "onboarding_48.md"),
    "/repo/docs/agent/onboarding_48.md",
)
CANON_MARK = "## ★ 2026-09-17 턴 T · P-159 ①"
NO_CANON = "정본 없음"                  # 「정본 없음」


def implemented_rows() -> list:
    """이 도구가 **실제로 재는 행** — 제 소스에서 읽는다(목록을 두 벌로 두지 않는다).

    브라우저 없이 「문서 35 · 도구 N」을 대 볼 수 있어야 한다(`--check`). 손으로 적은
    목록과 실제 코드가 갈리면 그 목록은 다음 턴에 또 거짓말을 한다 — 턴 U 오판 2 의 모양이다.
    """
    src = open(__file__, encoding="utf-8").read()
    seen, out = set(), []
    for k in re.findall(r"""result\(\s*["'](U\d#\d+)["']""", src):
        if k not in seen:
            seen.add(k)
            out.append(k)
    return sorted(out, key=lambda k: (k.split("#")[0], int(k.split("#")[1])))


def check_tool_against_canon(path: str | None = None) -> int:
    """문서와 도구를 대 본다 — 브라우저 없이. 갈리면 **2**(회색)다."""
    canon = canon_rows(path)
    if not canon["ok"]:
        print(f"{TAG} X 정본을 못 읽었다 — 찾아본 자리 {canon.get('tried')}")
        return 2
    want, got = set(canon["two_column"]), set(implemented_rows())
    print(f"{TAG} [정본] {canon['source']}")
    print(f"{TAG} 행 {canon['denominator']} · 두 칸 {len(want)} · 정본 없음 {len(canon['no_canonical'])} "
          f"(손으로 세지 않았다 — 문서를 읽었다)")
    print(f"{TAG} 이 도구가 재는 행 {len(got)}")
    miss, extra = sorted(want - got), sorted(got - want)
    if miss:
        print(f"{TAG} X 정본에 있는데 도구가 안 재는 행 {len(miss)}: {miss}")
    if extra:
        print(f"{TAG} X 도구가 재는데 정본이 두 칸으로 안 적은 행 {len(extra)}: {extra}")
    if miss or extra:
        return 2
    print(f"{TAG} O 문서와 도구가 **같은 {len(want)}행**을 든다 (P-180 · P-171)")
    return 0


def canon_rows(path: str | None = None) -> dict:
    """정본 문서에서 **행 · 두 칸 · 정본 없음**을 읽는다. 못 읽으면 `ok=False` 다(지어내지 않는다)."""
    tried = []
    for cand in ([path] if path else []) + list(CANON_DOC_CANDIDATES):
        if not cand:
            continue
        tried.append(cand)
        try:
            doc = open(cand, encoding="utf-8").read()
        except OSError:
            continue
        if CANON_MARK not in doc:
            continue
        #: ★★ [P-205 · 2026-09-20 · 턴 Y · 차선 Q] **`maxsplit=1` 이 빠져 있었다.**
        #:   이 표식은 문서에 **두 번** 나온다 — 절 머리에 한 번, 아래 「세는 법」의
        #:   **명령문 안에** 한 번(그 명령이 제 표식을 글자로 품는다). `maxsplit` 없이
        #:   자르면 `[1]` 은 **첫 표식과 둘째 표식 사이**가 되고, 그래서
        #:   **둘째 표식 뒤에 붙인 표는 아무도 못 읽는다** — 오늘 여기에 13행을 적고
        #:   「행 48 · 두 칸 35」가 나왔다. 문서를 고쳤는데 수가 안 움직이는 그 모양이다.
        #:   ⚠ 얼린 바이트로 A/B 했다: **HEAD 의 정본에서는 두 규칙이 같은 수**(48·35·13 ·
        #:     갈린 행 0)를 낸다 — 이 고침은 **없던 행을 만들어 내지 않는다.** 오늘 바이트에서만
        #:     13행이 갈리고, 그 13행이 바로 오늘 적은 행이다.
        #:   정본의 말은 처음부터 「턴 T · P-159 ① 절**부터 끝까지**」였다 — 규칙이 아니라
        #:   구현이 그 말과 달랐다.
        seg = doc.split(CANON_MARK, 1)[1]
        state, who = {}, None
        for line in seg.splitlines():
            m = re.match(r"#{3,4} (U\d)", line)
            if m:
                who = m.group(1)
            if not line.startswith("|"):
                continue
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) >= 4 and re.fullmatch(r"(U\d )?\d+", c[0]):
                key = c[0] if " " in c[0] else "%s %s" % (who, c[0])
                state[key] = (NO_CANON not in c[2]) and (NO_CANON not in c[3])

        def order(k):
            a, b = k.split()
            return (a, int(b))

        two = [k.replace(" ", "#") for k in sorted([k for k, v in state.items() if v], key=order)]
        gray = [k.replace(" ", "#") for k in sorted([k for k, v in state.items() if not v], key=order)]
        return {"ok": True, "source": cand, "denominator": len(state),
                "two_column": two, "no_canonical": gray}
    return {"ok": False, "source": "", "denominator": 0,
            "two_column": [], "no_canonical": [], "tried": tried}


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


def auto_report_runs(kind: str = "monthly") -> int:
    """[P-180 · 턴 V] **자동본 행 수** — `trigger=auto` 인 실행 기록.

    U4 #5 의 술어가 「U4 가 누른다」가 아니라 **「자동 행 ≥ 1」** 인 이유: 읽기 전용 U4 의
    「만들기」는 403 이 옳고(플랫폼 문지기 `read_only_role`), 자동본은 매월 1일 배치
    `monthly_report.run_monthly_all` 이 만든다. 사람이 누른 것(`trigger=manual`)을 세면
    PRD §7.4 의 수가 거짓이 된다 — 그래서 **칸으로 가른다**.
    """
    try:
        RR = orm().get_model("stream_monitors", "DsmReportRun")
        return RR._base_manager.filter(trigger="auto", kind=kind).count()
    except Exception:                                   # noqa: BLE001
        return -1


def latest_succeeded_run(kind: str = "monthly") -> int:
    """내려받을 수 있는 가장 최근 실행 기록 id — 없으면 0 (U4 #7)."""
    try:
        RR = orm().get_model("stream_monitors", "DsmReportRun")
        r = RR._base_manager.filter(kind=kind, status="succeeded").order_by("-id").values("pk").first()
        return int(r["pk"]) if r else 0
    except Exception:                                   # noqa: BLE001
        return 0


def system_request_count() -> int:
    """운영계 「요청」 행 수 — U5 #14 의 재시작 요청이 남기는 그 표."""
    try:
        SR = orm().get_model("stream_monitors", "DsmSystemRequest")
        return SR._base_manager.count()
    except Exception:                                   # noqa: BLE001
        return -1


def user_count() -> int:
    """계정 수 — U5 #1 의 「사용자 수 +1」 (서버 기록 · 화면이 그린 수가 아니다)."""
    try:
        orm()
        from django.contrib.auth import get_user_model
        return get_user_model()._base_manager.count()
    except Exception:                                   # noqa: BLE001
        return -1


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
    #   runserver 로그에 auth/profile 0건 · get-user-detail 17건). 둘 다 받고 어느 쪽이 섰는지 적는다.
    #   ★ [P-190 · 턴 W · 차선 Q] **정본 쪽을 고쳤다** — `onboarding_48.md` U1 1 행의 기대식이 이제
    #     `get-user-detail` 이다. 둘 다 받는 것은 그대로 둔다(dj-core 가 언젠가 auth/profile 로 옮겨도 안 깨진다).
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
#: ★★ [P-212 · 턴 Z · 차선 Q] **회색 열다섯의 이름이 세 판을 가로질러 전부 같았다.**
#:   「못 쟀다」한 낱말이 서로 다른 세 가지를 삼키고 있었고, 이름이 같으니 누구도
#:   **어느 것을 고치면 수가 움직이는지** 몰랐다. 그래서 회색을 셋으로 가른다 —
#:   갈라 놓으면 각 부류의 **주인이 다르다**는 것이 드러난다:
#:
#:     env      「환경(로그인·세션)」    — 도구가 문 앞에서 막혔다. 제품을 **안 건드렸다.**
#:                                        고치는 자리: 자격·창·때린 주소. **우리 쪽이다.**
#:     nopred   「우리가 안 잰 것」      — 술어가 **없다.** 제품이 어떤지 모른다.
#:                                        고치는 자리: 판정기에 술어를 넣는 것. **우리 쪽이다.**
#:     nodata   「잴 것이 0」            — 문도 술어도 섰는데 **자료가 비었다.**
#:                                        고치는 자리: 씨앗·시드. 제품 버그가 **아니다.**
#:
#:   ⚠ 셋 다 **여전히 회색**이다. 가르는 것은 색을 올리는 일이 아니라 **주인을 적는 일**이다.
#:     사유를 안 적은 회색은 「잊은 것」과 구별되지 않는다 (D-301).
GRAY_KINDS = {
    "env": "환경(로그인·세션) — 도구가 문 앞에서 막혔다. 제품을 안 건드렸다",
    "nopred": "우리가 안 잰 것(술어 없음) — 제품이 어떤지 **모른다**",
    "nodata": "잴 것이 0(자료 상태) — 문도 술어도 섰는데 잴 자료가 비었다",
}


def result(row, route, phrase_seen, predicate, evidence, cap_half=False, measured=True,
           url="", gray_kind=""):
    if not measured:
        verdict, score = "gray", None
        #: 회색인데 부류를 안 준 자리는 **그 사실 자체를 적는다** — 조용히 빈 칸으로
        #: 두면 「가르지 않은 것」이 「가를 수 없는 것」처럼 보인다.
        gray_kind = gray_kind or "unsorted"
    else:
        verdict, score = (("half", 0.5) if cap_half else ("green", 1.0)) \
            if (phrase_seen and predicate) else ("red", 0.0)
        gray_kind = ""
    return {"row": row, "route": route, "url": url, "phrase_seen": phrase_seen,
            "predicate": predicate, "verdict": verdict, "score": score,
            "cap_half": cap_half, "measured": measured, "evidence": evidence,
            "gray_kind": gray_kind,
            "gray_why": GRAY_KINDS.get(gray_kind, "" if not gray_kind else
                                       "**부류를 안 적었다** — 이 회색은 주인이 없다"),
            "measured_at": now_iso()}


#: ★ [U3 쪽지 ③ · 턴 Z] **회색의 사유도 측정이다.** 로그인이 실제로 낸 상태·본문
#:   앞부분·때린 주소를 여기 담아 두고, 회색 줄이 **짐작 대신 그것**을 적는다.
#:   어제 「자격이 없다」라고 적힌 다섯 행은 자격이 **있었다** — 문이 틀렸을 뿐이다.
LOGIN_WHY: dict = {}


from urllib.parse import quote, urlencode      # noqa: E402  (U3 쪽지 ① — 질의로 싣는다)


def api_token(ctx, api_base: str, user: str, password: str) -> str | None:
    """기계의 로그인 — **문으로 들어온다**(사람은 화면으로 들어온다 · `login()`).

    토큰을 꺼내는 규칙은 두 벌로 두지 않는다 — `verify_route_alive._extract_token` 하나를
    쓴다(D-369). 그 함수에는 **「200 인데 success:false 는 토큰이 아니다」**가 박혀 있고,
    복사본은 그 교훈을 한쪽에만 남긴다.

    ★★ [실측 2026-09-21 · 턴 Z · Q] **`web` 이 아니라 `api_base` 다.** 여기에 `web`
      (= `--web`, 기본 `http://localhost:3002`)을 주고 있었다. 3002 은 API 가 아니라
      `SimpleHTTP/0.6 Python/3.11.14` **정적 SPA 서버**다 — POST 를 모르고
      **501 `Unsupported method ('POST')` 를 `text/html;charset=utf-8` 로** 낸다.
      그래서 `r.json()` 이 `JSONDecodeError` 로 터지고 이 함수가 `None` 을 돌려주어
      **U6 다섯 행(#1·#2·#3·#4·#9)이 「기계 자격이 없다」 회색**이 됐다.
      계정도 속도 제한도 세션 제한도 아니었다 — **때린 문이 API 가 아니었다.**
      (같은 자격으로 8000 에 때리면 200 · `application/json` · `access_token`.)
    """
    if not (user and password):
        LOGIN_WHY[user or "(이름 없음)"] = "자격 이름이 비었다 — 부르지도 않았다"
        return None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from verify_route_alive import _extract_token     # noqa: PLC0415
    except Exception:                                     # noqa: BLE001
        LOGIN_WHY[user] = "_extract_token 을 못 읽었다 — 부르지도 않았다"
        print(f"{TAG} ⚠ _extract_token 을 못 읽었다 — 기계 로그인을 건너뛴다(회색)")
        return None

    def once():
        r = ctx.request.post(
            api_base + "/api/v1/auth/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"username": user, "password": password,
                             "end_previous_session": True}),
            fail_on_status_code=False, timeout=30000)
        head = ""
        try:
            body = r.body()
            head = bytes(body)[:120].decode("utf-8", "replace")
        except Exception:                                 # noqa: BLE001
            pass
        try:
            return r.status, _extract_token(r.json()), head
        except Exception as exc:                          # noqa: BLE001
            #: ★ **JSON 이 아닌 답은 「자격이 없다」가 아니다.** 3002(정적 SPA 서버)에
            #:   POST 하면 501 `text/html` 이 오고, 그것을 자격 문제로 적으면 다음 사람이
            #:   엉뚱한 곳을 판다 — 턴 Y 가 그렇게 다섯 행을 잃었다 (턴 Z · Q 실측).
            return r.status, None, "%s: %s · 앞부분 %r" % (type(exc).__name__, exc, head)

    try:
        status, token, head = once()
        #: ★★ [U3 쪽지 ② · 턴 Z] **429 는 자격 문제가 아니다.** 로그인은 5/분/IP 다
        #:   (`NINJA_DEFAULT_THROTTLE_RATES` anon · 실측으로는 4번째부터 429 가 났다).
        #:   한 번만 기다렸다 다시 부른다 — 두 번째도 429 면 **포기하고 그 사실을 적는다.**
        #:   `verify_route_alive.login` 에는 이 길이 이미 있었고 여기만 없었다.
        if status == 429 and not token:
            print(f"{TAG} ⚠ 로그인 429 (율제한) — {GAP_SECONDS}초 기다렸다 한 번만 더 부른다")
            time.sleep(GAP_SECONDS)
            status, token, head = once()
        if not token:
            LOGIN_WHY[user] = ("POST %s/api/v1/auth/login -> %s · %s — **자격 문제라고 "
                               "단정하지 않는다**" % (api_base, status, head or "본문 없음"))
            print(f"{TAG} 기계 로그인 토큰 못 받음 {user}: {LOGIN_WHY[user]}")
        return token
    except Exception as exc:                              # noqa: BLE001
        LOGIN_WHY[user] = "%s: %s (때린 곳 %s)" % (type(exc).__name__, exc, api_base)
        print(f"{TAG} 기계 로그인 실패 {user}: {type(exc).__name__}: {exc}")
        return None


def guarded(out, key, route, fn):
    """한 행을 재다 터지면 **그 행만 회색**이다 (P-205 · 턴 Y).

    ★ 왜 필요해졌나 — 이 턴에 13행이 새로 들어왔고, 그 13행은 **아직 한 번도 안 돌았다.**
      한 행의 예외가 `rows_u3` 전체를 끊으면 **이미 서 있던 행까지 같이 회색**이 된다 —
      새 행을 더한 대가로 옛 행을 잃는 것이다. 울타리는 그 자리에 친다.
    ⚠ 울타리는 **회색을 만든다. 초록이 아니다.** 예외 글자를 그대로 증거에 적는다.
    """
    try:
        fn()
    except Exception as exc:                            # noqa: BLE001
        out.append(result(key, route, False, False,
                          "재다 터졌다 — %s: %s (못 쟀다 · 회색. 나머지 행은 그대로 잰다)"
                          % (type(exc).__name__, str(exc)[:200]),
                          measured=False, gray_kind="env"))


def measure(web: str, snap_event: int, seed_a: int, seed_b: int, role_pw: str, out_path: str,
            only=(), canon_path: str | None = None, api_base: str = "") -> int:
    #: `web` 은 **사람이 보는 화면**(SPA · 3002), `api_base` 는 **기계가 두드리는 문**(API · 8000).
    #: 한 글자로 둘을 가리키면 U6 처럼 정적 서버를 제품으로 착각한다 (턴 Z · Q 실측).
    api_base = api_base or os.environ.get("GX_API") or "http://localhost:8000"
    from playwright.sync_api import sync_playwright

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    results: list = []
    logins: list = []
    probe_cam = f"GX-ONB-V-{stamp}"
    probe_user = f"gxprobe_onb_{stamp}"

    # ── 정본에서 행 목록을 읽는다 — **분모도 행 이름도 손으로 적지 않는다** (P-180) ──
    canon = canon_rows(canon_path)
    if not canon["ok"]:
        print(f"{TAG} 정본을 못 읽었다 — 재지 않는다(지어낸 행 목록으로 재면 그 수는 아무 말도 안 한다). "
              f"찾아본 자리: {canon.get('tried')}")
        return 2
    print(f"{TAG} [정본] {canon['source']} — 행 {canon['denominator']} · "
          f"두 칸 {len(canon['two_column'])} · 정본 없음 {len(canon['no_canonical'])}")

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
                # 못 잰 행은 회색 — 이 사람의 행 전부. **목록은 정본에서 온다**(손으로 적지 않는다).
                for row in [k for k in canon["two_column"] if k.split("#")[0] == pn]:
                    results.append(result(row, "", False, False,
                                          "로그인 실패 — 못 쟀다: " + lg.get("why", ""),
                                          measured=False, gray_kind="env"))
                ctx.close()
                continue
            try:
                fn = {"U1": rows_u1, "U2": rows_u2, "U3": rows_u3, "U4": rows_u4, "U5": rows_u5}[pn]
                fn(page, net, web, results, lg, snap_event=snap_event, seed_a=seed_a, seed_b=seed_b,
                   probe_cam=probe_cam, probe_user=probe_user)
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

        # ── U6 · 기계 여덟 행 [P-205 · 턴 Y] — **브라우저 없이 문만 두드린다** ──
        #    ★ 안 이으면 「이 도구가 재는 행 48」이 거짓말이 된다: `implemented_rows()` 는
        #      소스의 `result("U6#…")` 를 세는데, 이 블록이 안 불리면 결과에는 한 행도 없다.
        #      「적어 둔 것」과 「부른 것」은 다른 사실이고, 이 저장소는 뒤엣것만 센다.
        if (not only) or ("U6" in only):
            want_u6 = [k for k in canon["two_column"] if k.startswith("U6#")]
            try:
                if personas:
                    print(f"{TAG} 계정을 바꾼다(U6 기계) — {GAP_SECONDS}초 기다림")
                    time.sleep(GAP_SECONDS)
                actx = browser.new_context()
                probe_pw = os.environ.get("GX_PROBE_PASSWORD") or ""
                #: ★ [U3 쪽지 ④ · 턴 Z] **계정 이름을 손으로 박지 않는다.** 다른 게이트는
                #:   전부 `GX_PROBE_USER` 를 읽는데 여기만 `"gxprobe_q"` 가 박혀 있었다.
                #:   오늘은 둘 다 살아 있고 같은 비밀로 열려서 아무 일도 안 났지만
                #:   (U3 실측: gxprobe_q id 112 · gxprobe_v id 116 · 둘 다 200),
                #:   자격이 한 번 돌면 **이 도구만 다른 계정을 재게 된다.**
                probe_user_name = os.environ.get("GX_PROBE_USER") or "gxprobe_q"
                u6_token = api_token(actx, api_base, probe_user_name, probe_pw)
                adm_token = api_token(actx, api_base, "gxseed_u5_sysop", role_pw)
                print(f"{TAG} ═══ U6 · 기계 · 계정={probe_user_name} · "
                      f"토큰={bool(u6_token)} · 관리자토큰={bool(adm_token)} ═══")
                logins.append({"persona": "U6", "user": probe_user_name,
                               "ok": bool(u6_token), "admin_ok": bool(adm_token),
                               "why": LOGIN_WHY.get(probe_user_name, ""),
                               "admin_why": LOGIN_WHY.get("gxseed_u5_sysop", "")})
                rows_u6(actx.request, api_base, results,
                        token=u6_token, admin_token=adm_token, seed_b=seed_b,
                        probe_user_name=probe_user_name)
                actx.close()
            except Exception as exc:                    # noqa: BLE001
                print(f"{TAG} ⚠ U6 예외: {type(exc).__name__}: {exc}")
                traceback.print_exc()
                got_u6 = {r["row"] for r in results}
                for k in want_u6:
                    if k not in got_u6:
                        results.append(result(k, "", False, False,
                                              "U6 걸음이 터졌다 — %s: %s (못 쟀다)"
                                              % (type(exc).__name__, str(exc)[:160]),
                                              measured=False, gray_kind="env"))
        browser.close()

    measured_rows = [r for r in results if r["measured"]]
    green = sum(1 for r in results if r["verdict"] == "green")
    half = sum(1 for r in results if r["verdict"] == "half")
    red = sum(1 for r in results if r["verdict"] == "red")
    gray = sum(1 for r in results if r["verdict"] == "gray")
    score = sum(r["score"] or 0 for r in results)
    denom = canon["denominator"]
    want = set(canon["two_column"])
    got = {r["row"] for r in results}
    # ★★ [P-180] **도구가 문서와 갈렸는지 스스로 말한다.** 턴 U 의 오판 2 가 다시 나면
    #    이 두 줄이 그것을 이름으로 적는다 — 「35행 재측」이 조용히 22행이 되지 않는다.
    not_measured = sorted(want - got)
    not_in_canon = sorted(got - want)
    summary = {
        "measured_at": now_iso(), "stamp": stamp, "web": web,
        "canon_source": canon["source"],
        "denominator": denom,
        "two_column_rows": len(canon["two_column"]),
        "no_canonical_rows_gray": len(canon["no_canonical"]),
        "canon_two_column": canon["two_column"],
        "canon_no_canonical": canon["no_canonical"],
        "rows_in_canon_not_measured": not_measured,
        "rows_measured_not_in_canon": not_in_canon,
        "rows_attempted": len(results), "rows_measured": len(measured_rows),
        "green": green, "half": half, "red": red, "gray_measured_fail": gray,
        "score_sum": score, "score_over_denominator": f"{score}/{denom}",
        "sample": {"snap_event": snap_event, "seed_a": seed_a, "seed_b": seed_b,
                   "probe_camera": probe_cam, "probe_user": probe_user},
        "logins": logins, "rows": results,
        "rule": ("초록 = 문구 보임 + 셋째 술어 섬 · 정본이 ◐ 상한이라 적은 행은 반 · 술어 거짓 = 빨강 · "
                 "못 잰 행 = 회색(초록이 아니다) · 「정본 없음」 행은 회색 그대로. "
                 "행 목록·분모는 onboarding_48.md 에서 읽는다 — 손으로 적지 않는다"),
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # ★★ [P-189 · 턴 W · 차선 Q] **utf-8 을 못 박고, 쓴 즉시 다시 읽어 같은 수가 나오는지 본다.**
    #   「썼다」는 초록이 아니다 — 「다시 읽으니 같더라」가 초록이다. 깨진 증거는 JSON 으로
    #   멀쩡히 파싱되고 **수만 틀린다**(실측 2026-09-19: FC 증거를 cp949 왕복시키면 29 → 8).
    #   newline 을 못 박는 이유: Windows 호스트의 기본 줄바꿈 변환이 끼면 같은 회차 증거가
    #   컨테이너판과 호스트판에서 **다른 바이트**가 되어, 해시로 대조하는 다음 사람이 헛짚는다.
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(out_path, encoding="utf-8") as f:          # errors 없음 — 무르게 읽지 않는다
        _back = json.load(f)
    if _back != summary:
        print(f"{TAG} ⚠ **쓰고 다시 읽었더니 다른 것이 나왔다** — 이 증거는 증거가 아니다 (P-189)")
        return 2
    if _back.get("score_over_denominator") != f"{score}/{denom}":
        print(f"{TAG} ⚠ **다시 읽은 수가 방금 잰 수와 다르다** "
              f"({_back.get('score_over_denominator')} ≠ {score}/{denom}) — P-189")
        return 2
    print(f"{TAG} 두 칸 행 {len(canon['two_column'])} 중 시도 {len(results)} · 초록 {green} · 반 {half} · "
          f"빨강 {red} · 회색(못 잼) {gray} · 정본 없음 회색 {len(canon['no_canonical'])}")
    #: ★ [P-212 · 턴 Z · Q] **회색을 셋으로 갈라 소리 내어 읽는다.** 한 낱말로 뭉친 회색은
    #:   세 턴째 같은 수에 머물렀고, 이름이 같으니 **어느 것을 고치면 수가 움직이는지**
    #:   아무도 몰랐다. 여기서 부류를 적으면 각 부류의 **주인**이 드러난다.
    #:   ⚠ 가른다고 색이 오르지 않는다 — 셋 다 여전히 회색이다.
    if gray:
        from collections import Counter as _C
        _kinds = _C(r.get("gray_kind") or "unsorted"
                    for r in results if r["verdict"] == "gray")
        print(f"{TAG} ── 회색 {gray}건의 사유 (P-212) ──")
        for _k, _n in sorted(_kinds.items(), key=lambda kv: -kv[1]):
            print(f"{TAG}   {_n:3d}건  {_k:8s} {GRAY_KINDS.get(_k, '**부류를 안 적었다**')}")
            for _r in results:
                if _r["verdict"] == "gray" and (_r.get("gray_kind") or "unsorted") == _k:
                    print(f"{TAG}          · {_r['row']:7s} {_r['evidence'][:96]}")
    if not_measured:
        print(f"{TAG} ⚠ **정본에 있는데 이 도구가 아직 안 재는 행 {len(not_measured)}**: {not_measured}")
    if not_in_canon:
        print(f"{TAG} ⚠ **이 도구가 재는데 정본에 두 칸이 아닌 행 {len(not_in_canon)}**: {not_in_canon}")
    if not not_measured and not not_in_canon and not only:
        print(f"{TAG} O 도구와 정본이 같은 {len(want)}행을 든다 (P-180 · P-171)")
    print(f"{TAG} **{score}/{denom}** (분모 {denom} = onboarding_48.md 의 행 수 · 손으로 적지 않았다)")
    for r in results:
        print(f"{TAG}   {r['verdict']:5s} {r['row']:6s} {r['route']:32s} 문구={r['phrase_seen']} 술어={r['predicate']} — {r['evidence'][:150]}")
    print(f"{TAG} [증거] {out_path}")
    return 0


# ---------------------------------------------------------------------------
# [P-184 · 턴 W · 차선 Q] **게이트가 만든 사건은 지우지 않고 세지 않는다.**
#
# 세는 법은 `scripts/probe_events.py` 한 곳이 정본이다 — 여기서 새로 쓰지 않는다.
# 두 벌을 두면 반드시 어긋나고, 어긋나면 **조용한 쪽이 이긴다**(D-212 · D-369).
#
# ★★ [2026-09-21 · 턴 Z · 차선 Q] **둘째 셈법(카메라 이름)을 같이 없앴다 — 되살리지 말 것.**
#
#   종전 이 자리는 정본에서 `PROBE_CAMERA_HINT`(게이트 전용 카메라 이름 `gxprobe`)를
#   **빌려다** 둘째 갈래로 걸렀다. 사유는 「응답 행에 `track_id` 가 없어서」였다.
#   그 갈래는 **틀렸다.** U1 이 P-201 마무리에서 이름으로 댔고, 제가 같은 것을 다시 쟀다:
#
#       [실측 2026-09-21 · 턴 Z · Q · gx-shell 안에서 GET /api/dsm/events?limit=5]
#         id=305027·305028·305029  cam='gxprobe-D384-screen 캡처용 카메라'
#                                  data_source='drill'   track_id=None
#
#   ⇒ 그 카메라에 매달린 것은 **탐침이 아니라 훈련(drill)** 이다. 이름으로 세면
#     **훈련 사건이 탐침으로 오인되어 분모에서 빠진다** — 우리 수가 **높게** 나오고,
#     높게 나오는 쪽은 아무도 못 본다. **이름은 표식이 아니다**(표식은 행 안에 있다).
#   ⇒ 그래서 세는 법은 **표식 하나**다: `is_probe_track(track_id)`.
#     `scripts/probe_events.py` 가 상수까지 지운 것도 같은 뜻이다 —
#     이름을 남겨 두면 다음 사람이 그것을 빌려다 또 이름으로 센다.
#
# ⚠ 그러면 **HTTP 자리에서는 아무것도 못 거른다**는 사실이 남는다. 그것을 숨기지 않는다:
#
#     [실측 2026-09-21 · 턴 Z · Q] `/api/dsm/events` 한 행의 칸은
#       data_source · event_id · event_type · last_seen_at · lat · lng · occurred_at ·
#       response_state · severity · snapshot_path · status · stream_monitor_id ·
#       stream_monitor_name · verdict          ← **`track_id` 가 없다**
#
#     그리고 `data_source` 로 갈음할 수도 **없다** — `apps/dsm/services.py:227
#     event_data_source` 는 `"drill"` 아니면 `"live"` **둘만** 낸다. `"probe"` 는
#     그 축에 **없다**(탐침은 훈련과 달리 창이 없어 창 판정으로 답할 수 없다).
#     그러므로 U1 이 쪽지에 준 두 길 중 **②(data_source 로 거르기)는 성립하지 않는다.**
#     남은 길은 ① — **안 거르되, 안 걸렀다고 말한다.**
#
# ⚠ **뺀 수를 적는다. 못 뺐으면 못 뺐다고 적는다.** 조용히 안 거르면 분모가 틀린 것을
#   아무도 못 본다 — 회색도 빨강도 안 나고 그냥 안 걸러지는 것이 가장 나쁜 모양이다.
#   「지우지 않고 세지 않기」의 요점은 제외가 아니라 **분모를 밝히는 것**이다(P-184).
#   그래서 이 함수는 못 거른 자리에서 `dropped=None` 을 돌려주고, 부르는 쪽이 그것을
#   증거줄에 **소리 내어** 적는다. [2026-09-19 조율자 실측: probe 사건 12건 ·
#   2026-09-21 U1 실측: 표식 `data_source=probe` **0건**(대표 결정으로 씨앗 4건 지움)]
# ---------------------------------------------------------------------------
def exclude_probe_rows(rows):
    """(사람 것만, 뺀 probe 사건 번호). 정본을 부른다 — 세는 법을 새로 쓰지 않는다.

    돌려주는 둘째 값의 뜻 **셋**을 가른다 — 「0건 뺐다」와 「못 뺐다」는 다른 사실이다:

        `[]`      잴 수 있었고 **뺄 것이 0건**이었다      (분모를 밝혔다)
        `[id…]`   잴 수 있었고 **이만큼 뺐다**            (분모를 밝혔다)
        `None`    **못 쟀다** — 거르지 못했다             (분모가 틀릴 수 있다 · D-301)

    `None` 을 조용한 성공으로 읽으면 안 된다. 부르는 쪽이 증거줄에 소리 내어 적는다.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from probe_events import is_probe_track          # noqa: E402
    except ImportError as exc:                           # noqa: BLE001
        #: 정본을 못 부르면 **거르지 않는다.** 여기서 급히 흉내 내면 그것이 두 번째 정본이 된다.
        #: ⚠ 다만 **조용히 지나가지 않는다** — 안 걸렀다는 사실을 돌려주고 찍는다.
        print(f"{TAG} ⚠ probe 정본(`probe_events.py`)을 못 불렀다 ({exc}) — **거르지 않았다**")
        return list(rows or []), None

    dicts = [r for r in (rows or []) if isinstance(r, dict)]
    #: ★ **표식 칸이 아예 없으면 「0건 뺐다」가 아니라 「못 뺐다」다.**
    #:   `/api/dsm/events` 응답에는 `track_id` 가 없다(머리말 ★★ 의 실측). 그 자리에서
    #:   `is_probe_track` 은 언제나 거짓이고, 그 거짓을 「탐침이 없다」로 읽으면
    #:   **분모 0인 초록**이 된다. 칸이 실리는 날 이 갈래는 저절로 살아난다.
    if dicts and not any("track_id" in r for r in dicts):
        return list(rows or []), None

    kept, dropped = [], []
    for r in rows or []:
        if not isinstance(r, dict):
            kept.append(r)
            continue
        #: 세는 법은 **표식 하나**다. 카메라 이름 갈래는 폐지됐다(머리말 ★★) —
        #: 그 갈래는 훈련(drill)을 탐침으로 읽었다. **되살리지 말 것.**
        if is_probe_track(r.get("track_id")):
            dropped.append(r.get("event_id"))
        else:
            kept.append(r)
    return kept, dropped


# ---------------------------------------------------------------------------
# U1 · 관제요원 (1440)
# ---------------------------------------------------------------------------
def rows_u1(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam, probe_user=""):
    # #1 교대 시작 — 로그인: 로그인 화면 문장 + POST login 200 + GET profile 200
    phrase = lg["login_body_has_product_line"] and lg["login_body_has_first_time"]
    pred = (200 in lg.get("login_posts", [])) and lg.get("profile_200", False)
    out.append(result("U1#1", "/login", phrase, pred,
                      f"login POST {lg.get('login_posts')} · 프로필 200={lg.get('profile_200')} ({lg.get('profile_endpoint') or '둘 다 없음'} — [P-190 · 턴 W] 정본을 화면이 부르는 것으로 맞췄다: get-user-detail 이 기대식이다) · 문장={lg['login_body_has_product_line']} · 처음이세요?={lg['login_body_has_first_time']}",
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
    #   「`GET /api/dsm/dashboard/link-state` 200」은 기대식 오류였다(호출 0건인데 배지는 떴다). frame 200 + 배지가 술어다.
    #   ★ [P-190 · 턴 W · 차선 Q] **정본 쪽을 고쳤다** — `onboarding_48.md` U1 2 행의 셋째 술어가 이제
    #     `frame` 하나만 요구한다. 세 턴 동안 이 주석만 「기대식 오류」라 적고 정본은 그대로였다.
    fjson = (frame or {}).get("json") or {}
    frame_link = (fjson.get("link") or {}) if isinstance(fjson, dict) else {}
    out.append(result("U1#2", "/dsm/dashboard", bool(badge), bool(frame) and bool(frame_link),
                      f"배지={badge} · frame 200={bool(frame)} · frame.link={frame_link.get('status') if isinstance(frame_link, dict) else frame_link} · link-state 따로 호출 {link_all} ([P-190 · 턴 W] 정본을 화면이 부르는 것으로 맞췄다: 배지는 frame.link 에서 온다 — 따로 호출 0건이 옳다) · ◐ 상한(카메라 정상/이상 칸 없음 — 정본 표기)",
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

    # #4 실시간 스트림 열기 [P-205 · 턴 Y] — **누를 자리 = /multi-stream-monitor · 기대 = 도달 + 스트림 자리 ≥1**
    #    문구 정본이 없어 세 턴 회색이던 행이다. 기계에게 필요한 것은 글자가 아니라 **자리**였다.
    def _u1_4():
        url = goto(page, web, "/multi-stream-monitor", settle_ms=10_000)
        b = body(page)
        reached = "/multi-stream-monitor" in (url or "")
        try:
            slots = page.evaluate(
                "() => document.querySelectorAll('video, canvas, [class*=stream i], [id*=stream i]').length")
        except Exception:                               # noqa: BLE001
            slots = 0
        # 인수 화면의 단언 글자(영문) — 사전 밖이라 문구 칸에는 못 적지만 **자리의 증거**는 된다
        says = ("Participants" in b) or ("Stream" in b) or ("스트림" in b)
        out.append(result("U1#4", "/multi-stream-monitor", reached,
                          (slots >= 1) or says,
                          f"도달={reached} (url={url}) · 스트림 자리(video/canvas/stream) {slots}개 · "
                          f"단언 글자={says} · 본문 {len(b)}자 "
                          f"— 도달만 하고 자리가 0이면 빨강(P-205)", url=url))
    guarded(out, "U1#4", "/multi-stream-monitor", _u1_4)

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
def rows_u2(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam, probe_user=""):
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
    #: [P-184] **게이트가 만든 사건은 세지 않는다** — 정본(`probe_events.py`)을 부른다.
    srv_rows = js.get("events", []) if isinstance(js, dict) else None
    human, probe_out = exclude_probe_rows(srv_rows)
    n_srv = len(human) if srv_rows is not None else -1
    probe_note = ("" if not probe_out else
                  f" · probe 제외 {len(probe_out)}건 {probe_out[:6]} (지우지 않고 세지 않는다 · P-184)")
    if probe_out is None:
        #: ★ [턴 Z · Q] 사유를 **이름으로** 적는다. 종전 문장은 원인을 하나(「정본을 못 불렀다」)로
        #:   단정했는데, 오늘 실제 사유는 **응답에 표식 칸이 없다**는 쪽이다.
        probe_note = (" · ⚠ **probe 를 못 걸렀다**(이 수에는 게이트 사건이 섞일 수 있다) — "
                      "응답 행에 `track_id` 가 없고(`data_source` 는 drill/live 둘만 낸다) "
                      "카메라 이름으로 거르는 갈래는 **훈련을 탐침으로 읽어서 폐지**했다 "
                      "(P-201 · P-184). 못 쟀다는 뜻이지 0건이라는 뜻이 아니다")
    out.append(result("U2#2", "/dsm/events?preset=unhandled", seen, bool(g200) and all_unhandled,
                      f"GET …response_state=occurred 200={bool(g200)} (서버 {n_srv}건{probe_note}) · 처리 단계 칸 {len(states)} 전부 미처리={all_unhandled} {sorted(set(states))}", url=url))

    # #3 이벤트 등급 재판정 [P-205 · 턴 Y] — **누를 자리를 찾는다 · 기대 = 0개(그래서 ○)**
    #    ★ 이 행은 채워도 ● 가 아니다. 「없는 것을 없다고 재는」 행이다 —
    #      회색(못 쟀다)과 빨강(재서 없다)은 다르고, 이 저장소는 그 둘을 가른다.
    def _u2_3():
        url = goto(page, web, f"/dsm/events/{snap_event or seed_a}")
        try:
            controls = page.evaluate(
                "() => {const w = ['심각','경계','주의','등급'];"
                " const el = Array.from(document.querySelectorAll("
                "   'select, [role=combobox], button, input'));"
                " return el.filter(e => {const t = ((e.innerText||'') + ' ' + (e.value||'') + ' '"
                "   + (e.getAttribute('aria-label')||'') + ' ' + (e.name||'')).trim();"
                "   return w.some(x => t.includes(x)) && /등급|severity/i.test("
                "     t + ' ' + (e.className||'') + ' ' + (e.id||''));}).length;}")
        except Exception:                               # noqa: BLE001
            controls = -1
        found = controls > 0
        out.append(result("U2#3", "/dsm/events/:id", True, found,
                          f"등급을 **다시 매기는** 자리 {controls}개 (0 이면 ○ — 재판정 칸이 없다는 "
                          f"것이 지금의 사실이다 · 1 이상이면 그것이 새 사실이고 그때 술어는 "
                          f"[서버 기록] severity 변경 + 감사 행 1 이 된다) · "
                          f"-1 은 화면을 못 물어본 것이다", url=url))
    guarded(out, "U2#3", "/dsm/events/:id", _u2_3)

    # #4 심각 이벤트: 배지 심각 · GET snapshot 200 image/jpeg · <img> ≥1 · 주소 칸 비어 있지 않음 — 하나라도 빠지면 ◐
    #    ★★ [U1 요청 ③ · 턴 V] **그림 실린 씨앗이 없으면 이 행은 회색이다** — ◐ 도 빨강도 아니다.
    #      그림 없는 사건으로 재면 snapshot 문이 404 이고, 그 404 는 제품의 결함이 아니라
    #      **씨앗의 빈 칸**이다(U1 실측 2026-09-18). 못 잰 것을 못 쟀다고 적는다(D-301).
    if not snap_event:
        out.append(result("U2#4", "/dsm/events/:id", False, False,
                          "그림 실린 씨앗이 없어 **못 쟀다** — 씨앗 명세의 snapshot_path 가 전부 비었다. "
                          "capture_screens 를 이 턴 판으로 다시 돌리거나 --snap-event 를 손으로 준다 "
                          "(개발 DB 에서 200 이 확인된 사건: 4802)",
                          measured=False, gray_kind="nodata"))
    else:
        m = net.mark()
        url = goto(page, web, f"/dsm/events/{snap_event}")
        b = body(page)
        seen = "심각" in b
        snap = [r for r in net.find("GET", f"/api/dsm/events/{snap_event}/snapshot", m)]
        snap_ok = any(r["status"] == 200 and "image/jpeg" in r["ctype"] for r in snap)
        try:
            imgs = page.evaluate("() => Array.from(document.querySelectorAll('img')).filter(i => i.naturalWidth > 0 && (i.src||'').includes('snapshot')).length")
        except Exception:                               # noqa: BLE001
            imgs = 0
        row = event_row(snap_event)
        addr = (row.get("stream_monitor__install_address") or "").strip()
        addr_on = bool(addr) and addr.split(" (")[0] in b
        full = snap_ok and imgs >= 1 and addr_on
        partial = (snap_ok or imgs >= 1) and not full
        out.append(result("U2#4", "/dsm/events/:id", seen, full or partial,
                          f"snapshot {[r['status'] for r in snap]} jpeg={snap_ok} · img(snapshot, naturalWidth>0)={imgs} · "
                          f"주소 화면={addr_on} · 셋 다={full} · "
                          f"[서버 기록] 이 사건의 snapshot_path={'있다' if (row.get('snapshot_path') or '').strip() else '**비었다**'}",
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

    # ══ [P-180 · 턴 V] 정본이 두 칸을 채운 뒤 늘어난 행 ═══════════════════════
    # #9 요원별 처리 현황: /dsm/team-status · 「요원별 현황」 · GET stats/by-reviewer 200 + 표 행 ≥1
    #    ★ 정본: 「표가 0행이면 「없다」가 떠야 하고 **빈 표는 빨강**」 — 0행을 침묵으로 그리면 빨강이다.
    m = net.mark()
    url = goto(page, web, "/dsm/team-status")
    b = body(page)
    seen = "요원별 현황" in b
    g = net.ok("GET", "/api/dsm/stats/by-reviewer", m)
    rows = table_rows(page)
    said_empty = any(w in b for w in EMPTY_WORDS)
    out.append(result("U2#9", "/dsm/team-status", seen, bool(g) and (rows >= 1 or said_empty),
                      f"by-reviewer 200={bool(g)} · 표 행 {rows} · 0행일 때 「없다」={said_empty} "
                      f"(빈 표를 침묵으로 그리면 빨강) · 「요원」 열={('요원' in b)}", url=url))

    # #16 알림 규칙 확인: /dsm/notify · 「알림 받는 사람·채널」 · GET notify-rules/list 200 + 규칙 표 행 ≥1
    m = net.mark()
    url = goto(page, web, "/dsm/notify")
    b = body(page)
    seen = NOTIFY_HEADLINE in b
    g = net.ok("GET", "/api/dsm/settings/notify-rules/list", m)
    rows = table_rows(page)
    said_empty = any(w in b for w in EMPTY_WORDS)
    js = (g or {}).get("json") or {}
    n_srv = len(js.get("rules", [])) if isinstance(js, dict) else -1
    out.append(result("U2#16", "/dsm/notify", seen, bool(g) and (rows >= 1 or said_empty),
                      f"notify-rules/list 200={bool(g)} (서버 규칙 {n_srv}건) · 표 행 {rows} · "
                      f"0건일 때 「없다」={said_empty} (빈 표는 빨강)", url=url))


# ---------------------------------------------------------------------------
# U3 · 이동 중 (390 · 같은 계정)
# ---------------------------------------------------------------------------
def rows_u3(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam, probe_user=""):
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

    # ══ [P-180 · 턴 V] 정본이 두 칸을 채운 뒤 늘어난 행 ═══════════════════════
    # #19 내가 처리한 이벤트 목록: /m/inbox · 「내게 온 이벤트」 ·
    #     정본: [API 호출] 브라우저가 `GET /api/dsm/deliveries?…&mine=true` 를 **실제로** 부름 + 제목 1.
    #     ★ 정본이 그대로 적어 둔 단서: 턴 I 실측은 화면이 `mine` 을 **안 불렀다** — 그대로면 ◐ 다
    #       (**제목만으로 초록이 되지 않는다**). 그래서 `mine` 이 없으면 반이 상한이다.
    #     ⚠ [실측 2026-09-18 · Q] `MobileInbox.tsx` 머리말이 그 인자가 아직 없다고 적고 있고,
    #       「내가 처리한 것」은 턴 T 에 선 다른 문(`GET /api/dsm/me/handled-events`)이 낸다.
    #       **정본을 여기서 고치지 않는다**(고치는 사람과 재는 사람이 달라야 한다) — 두 문을 다 적고
    #       판정은 정본대로 둔다. 정본을 옮길지는 V 의 실측 뒤 세종이 정한다.
    m = net.mark()
    url = goto(page, web, "/m/inbox")
    b = body(page)
    seen = MOBILE_INBOX_HEADLINE in b
    d200 = [r for r in net.find("GET", "/api/dsm/deliveries", m) if r["status"] == 200]
    mine = [r for r in net.find("GET", "/api/dsm/deliveries", m) if "mine=" in r["url"]]
    handled = net.ok("GET", "/api/dsm/me/handled-events", m)
    hjs = (handled or {}).get("json") or {}
    n_handled = hjs.get("total", -1) if isinstance(hjs, dict) else -1
    out.append(result("U3#19", "/m/inbox", seen, bool(d200),
                      f"deliveries 200={bool(d200)} · **mine 인자 호출 {len(mine)}건** "
                      f"(0 이면 ◐ 상한 — 제목만으로 초록이 되지 않는다) · "
                      f"[정본 밖 사실] me/handled-events 200={bool(handled)} 처리함 {n_handled}건 · 탭 「처리함」={('처리함' in b)}",
                      cap_half=(not mine), url=url))

    # #16 근무 외 알림 차단: /m/settings · 「내 알림 설정」 ·
    #     [서버 기록] PUT /api/dsm/me/notify-prefs 200 → **다시 읽은 값에 차단 시간대 반영**.
    #     ★★ 되돌린다 — 차단 시간대를 켠 채로 두면 **다음 회차의 알림이 막혀** 그 회차가 제품 대신
    #       우리를 잰다(턴 T U5#9 가 `verify_seed_roles` 를 빨갛게 만든 그 모양). 판정에 쓸 것을
    #       다 읽은 뒤 원래 값으로 되돌리고, 되돌린 사실을 증거에 적는다.
    m = net.mark()
    url = goto(page, web, "/m/settings", settle_ms=8_000)
    b = body(page)
    seen = MOBILE_SETTINGS_HEADLINE in b
    pred, evidence = False, ""
    before = net.ok("GET", "/api/dsm/me/notify-prefs", m)
    bjs = (before or {}).get("json") or {}
    was = {"quiet_start": (bjs.get("quiet_start") if isinstance(bjs, dict) else "") or "",
           "quiet_end": (bjs.get("quiet_end") if isinstance(bjs, dict) else "") or ""}
    if seen:
        want = {"quiet_start": "23:30", "quiet_end": "04:30"}

        def _save(qs: str, qe: str, mark: int) -> dict:
            """두 칸을 적고 「설정 저장」 — 돌려주는 것은 PUT 응답과 다시 읽은 값."""
            try:
                page.get_by_placeholder("22:00").first.fill(qs)
                page.get_by_placeholder("07:00").first.fill(qe)
            except Exception as exc:                    # noqa: BLE001
                return {"why": f"시간 칸 채우기 실패 {type(exc).__name__}"}
            click_button(page, "설정 저장")
            page.wait_for_timeout(7_000)
            put = [r for r in net.find("PUT", "/api/dsm/me/notify-prefs", mark)]
            m2 = net.mark()
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(6_000)
            again = net.ok("GET", "/api/dsm/me/notify-prefs", m2)
            ajs = (again or {}).get("json") or {}
            return {"put": [p["status"] for p in put],
                    "read_start": (ajs.get("quiet_start") if isinstance(ajs, dict) else None),
                    "read_end": (ajs.get("quiet_end") if isinstance(ajs, dict) else None)}

        r1 = _save(want["quiet_start"], want["quiet_end"], m)
        ok_put = 200 in (r1.get("put") or [])
        reflected = (r1.get("read_start") == want["quiet_start"]
                     and r1.get("read_end") == want["quiet_end"])
        saved_msg = "저장됨" in body(page)
        pred = bool(ok_put and reflected)
        # ── 되돌리기 — 판정에 쓸 것을 다 읽은 뒤에 (판정은 바뀌지 않는다) ──
        m3 = net.mark()
        r2 = _save(was["quiet_start"], was["quiet_end"], m3)
        restored = (r2.get("read_start") or "") == was["quiet_start"] and \
                   (r2.get("read_end") or "") == was["quiet_end"]
        evidence = (f"PUT notify-prefs {r1.get('put')} · 다시 읽음 {r1.get('read_start')}~{r1.get('read_end')} "
                    f"(기대 {want['quiet_start']}~{want['quiet_end']} · 반영={reflected}) · 화면 「저장됨」={saved_msg}"
                    f" · [되돌림] 원래 {was['quiet_start'] or '없음'}~{was['quiet_end'] or '없음'} 로 복구={restored}"
                    f" {r2.get('why', '')}{r1.get('why', '')}")
    else:
        evidence = f"「{MOBILE_SETTINGS_HEADLINE}」 이 화면에 없다 · url={page.url}"
    out.append(result("U3#16", "/m/settings", seen, pred, evidence, url=url))

    # #3 상황 사진 1장 보기 [P-205 · 턴 Y] — **모바일 상세의 사진 자리**
    #    ★ U2#4(데스크톱)와 **다른 화면**이다. 거기서는 `<img>` 가 0이었고(◐), 여기는 그린다고
    #      정본이 적었다 — 그 말이 맞는지는 이 행이 잰다. 문 200 인데 그림 0이면 **빨강**이다.
    def _u3_3():
        if not snap_event:
            out.append(result("U3#3", "/m/events/:id", False, False,
                              "그림 실린 씨앗이 없어 **못 쟀다**(U2#4 와 같은 사유 · --snap-event)",
                              measured=False, gray_kind="nodata"))
            return
        m = net.mark()
        url = goto(page, web, f"/m/events/{snap_event}")
        snap = net.find("GET", f"/api/dsm/events/{snap_event}/snapshot", m)
        snap_ok = any(r["status"] == 200 and "image/jpeg" in r["ctype"] for r in snap)
        try:
            imgs = page.evaluate(
                "() => Array.from(document.querySelectorAll('img'))"
                ".filter(i => i.naturalWidth > 0).length")
        except Exception:                               # noqa: BLE001
            imgs = 0
        out.append(result("U3#3", "/m/events/:id", snap_ok, snap_ok and imgs >= 1,
                          f"snapshot {[r['status'] for r in snap]} jpeg={snap_ok} · "
                          f"그려진 <img>(naturalWidth>0) {imgs}개 — 문이 200 인데 0이면 빨강 "
                          f"(U2#4 데스크톱이 정확히 그 모양이었다)", url=url))
    guarded(out, "U3#3", "/m/events/:id", _u3_3)

    # #14 해당 카메라 모바일 실시간 [P-205 · 턴 Y] — **계약 11조 설계 잠금이 지켜지는가**
    #    ★★ 이 행은 **●가 될 수 없다.** 잠금이 지켜지면 그것은 「제품이 옳다」이지
    #      「이 사람이 그 일을 끝낼 수 있다」가 아니다. 온보딩은 뒤엣것을 센다 → ○(0점).
    #      자리가 **생기면** 그때는 잠금이 깨진 것이고, 그건 온보딩이 아니라 계약이 볼 일이다.
    def _u3_14():
        url = goto(page, web, f"/m/events/{snap_event or seed_b}")
        b = body(page)
        try:
            live = page.evaluate(
                "() => document.querySelectorAll("
                "  'video, [class*=live i], [class*=stream i], [id*=stream i]').length")
        except Exception:                               # noqa: BLE001
            live = -1
        words = [w for w in ("실시간", "라이브", "스트림") if w in b]
        out.append(result("U3#14", "/m/events/:id", True, live > 0,
                          f"모바일 실시간 자리 {live}개 · 말 {words} — **0 이 지금의 사실이고 "
                          f"이 행은 ○ 다**(계약 11조 설계 잠금). 모바일 라우터에는 세 자리뿐이다 "
                          f"(inbox · eventDetail · settings). 자리가 생겼다면 잠금이 깨진 것이다",
                          url=url))
    guarded(out, "U3#14", "/m/events/:id", _u3_14)


# ---------------------------------------------------------------------------
# U6 · 외부 연계 시스템 — **기계다. 브라우저가 아니라 문을 두드린다** [P-205 · 턴 Y]
#
#   여덟 행이 세 턴째 회색이었던 이유는 문이 없어서가 아니라 **문구 칸이 비어서**였다.
#   기계는 글자를 읽지 않는다 — 기계에게 「누를 자리」는 **문**이고 「기대」는 **응답**이다.
#
# ⚠ 쓰기 갈래 셋의 규약
#   · `U6#1`(키 발급) · `U6#4`(웹훅 구독) 는 **되돌린다** — 지우는 문이 실재한다
#     (`api.py:1104` · `api.py:742`). 게이트가 남긴 자격·구독은 다음 게이트의 거짓 색이다
#     (턴 T 의 U5#9 가 그 모양이었다).
#   · `U6#9`(상태 갱신) 는 **없는 사건 id 로** 두드린다. 이 저장소가 쓰기 면을 재는 방식
#     그대로다(`verify_contract_route_reach`: 「쓰기 경로는 없는 id 로 두드린다」) —
#     **404 는 「관문을 지나 핸들러까지 갔고 상태는 안 건드렸다」**이고, 403 이면 관문에서
#     막힌 것이다(P-83 눈금). 전이 자체는 `U3#7` 이 사람 자격으로 이미 잰다.
# ---------------------------------------------------------------------------
U6_ANON_READS = ("/api/dsm/events", "/api/dsm/cameras/pulse", "/api/dsm/dashboard/frame",
                 "/api/dsm/deliveries", "/api/dsm/settings/notify-rules/list")
U6_ABSENT_EVENT = 987654321          # 없는 사건 — 쓰기 문을 상태 안 바꾸고 두드린다


def _json_of(resp):
    try:
        return resp.json()
    except Exception:                                   # noqa: BLE001
        return None


def _count_rows(js) -> int:
    """목록 응답의 행 수 — 봉투든 아니든 **배열을 찾아** 센다. 못 세면 -1 (0 이 아니다)."""
    if isinstance(js, list):
        return len(js)
    if not isinstance(js, dict):
        return -1
    scopes = [js]
    if isinstance(js.get("data"), dict):
        scopes.append(js["data"])
    for scope in scopes:
        if isinstance(scope.get("total"), int):
            return scope["total"]
        for v in scope.values():
            if isinstance(v, list):
                return len(v)
    return -1


def _outbox_signed() -> int:
    """[서버 기록] 서명이 붙은 웹훅 발송 행 수. **못 읽으면 -1** — 0 과 다르다."""
    try:
        get = orm()
    except Exception:                                   # noqa: BLE001
        return -1
    for label in ("stream_monitors.WebhookOutbox", "stream_monitors.DsmWebhookOutbox",
                  "stream_monitors.WebhookDelivery"):
        try:
            model = get(label)
        except Exception:                               # noqa: BLE001
            continue
        try:
            n = 0
            for r in model.objects.all().order_by("-id")[:200]:
                blob = (str(getattr(r, "headers", "") or "")
                        + str(getattr(r, "signature", "") or "")
                        + str(getattr(r, "signature_header", "") or ""))
                if blob.strip():
                    n += 1
            return n
        except Exception:                               # noqa: BLE001
            continue
    return -1


#: ★ [P-212 · 턴 Z] U6#4 가 오래 회색이던 까닭 하나는 **잴 것이 0**(`WEBHOOK_SIGNING_KEYS`
#:   빈 표)이었다. 시험 키의 **참조 이름**을 환경에서 받는다 — 값이 아니라 이름이고,
#:   쿼리·argv 에 실리는 것도 **이 참조 이름**뿐이다(키 자체는 시드가 들고 있다).
U6_SIGNING_KEY_REF = os.environ.get("GX_WEBHOOK_SIGNING_KEY_REF") or "p118-gate"


def rows_u6(api, api_base, out, *, token, admin_token, seed_b,
            probe_user_name="gxprobe_q"):
    """기계 행 여덟. `api` 는 playwright 의 `APIRequestContext` — 브라우저 없이 문만 부른다.

    ★★ [실측 2026-09-21 · 턴 Z · Q] 둘째 인자는 **`api_base`(8000)이지 `web`(3002)이 아니다.**
      `web` 을 주고 있던 동안 U6#12·#14·#15 는 **정적 SPA 서버의 404** 를 받아
      「익명 읽기 5건 전부 404」·「X-GX-Schema 없다」·「health 404」로 **빨강**이었다 —
      제품이 낸 빨강이 아니라 **문을 잘못 두드린 빨강**이다(거짓 빨강).
    """
    def call(method, path, *, headers=None, data=None):
        fn = getattr(api, method.lower())
        kw = {"headers": headers or {}, "fail_on_status_code": False, "timeout": 30000}
        if data is not None:
            kw["data"] = data
        r = fn(api_base + path, **kw)
        return r, _json_of(r)

    bearer = {"Authorization": "Bearer %s" % token} if token else {}
    admin = {"Authorization": "Bearer %s" % admin_token} if admin_token else {}
    JSON = {"Content-Type": "application/json"}

    def no_cred(row_key, route):
        """★ 자격 없이 두드려 401 을 받고 그것을 **빨강**으로 세면 제품이 아니라
        **우리의 빈 주머니**를 재는 것이다 — 회색이다 (D-301).

        ★★ [U3 쪽지 ③ · 턴 Z] **사유를 짐작하지 않는다.** 이 문장은 어제 거짓말을 했다 —
          「환경에 GX_PROBE_PASSWORD 를 주면 잰다」고 적었는데 그 값은 `.env.gates` 에
          **있었고**, 안 재진 까닭은 자격이 아니라 **때린 문이 API 가 아니었기 때문**이다.
          그래서 이제 **로그인이 실제로 낸 것**(상태 · 본문 앞부분 · 때린 주소)만 적는다.
          「무엇을 주면 잰다」는 그것을 **실제로 확인했을 때만** 쓴다.
        """
        why = LOGIN_WHY.get(probe_user_name) or LOGIN_WHY.get("gxprobe_q") or ""
        out.append(result(row_key, route, False, False,
                          "기계 토큰이 없어 **못 쟀다**(회색) — 로그인이 실제로 낸 것: %s"
                          % (why or "**기록이 없다** — 로그인을 부르지도 않았다"),
                          measured=False, gray_kind="env"))
        return True

    # #1 API 키로 인증 — 발급 → 키로 200 · 익명으로 401 → **되돌린다**
    def _u6_1():
        if not admin_token:
            out.append(result("U6#1", "POST /settings/api-keys", False, False,
                              "관리자 토큰이 없다 — 키를 발급할 수 없어 **못 쟀다**(회색). "
                              "로그인이 실제로 낸 것: %s"
                              % (LOGIN_WHY.get("gxseed_u5_sysop")
                                 or "**기록이 없다** — 부르지도 않았다"),
                              measured=False, gray_kind="env"))
            return
        name = "onb-U6-%s" % datetime.now().strftime("%H%M%S")
        #: ★★ [U3 쪽지 ① · 턴 Z · 격리 재현] **422 는 「본문 대신 쿼리」였다.**
        #:   `backend/apps/dsm/api.py:1060 issue_api_key(self, request, name: str, …)` —
        #:   django-ninja 는 **스키마가 아닌 맨 스칼라 인자를 `Query` 로 잡는다**(POST 라도).
        #:   그래서 JSON 본문에 실은 `name` 은 아무 데도 안 닿고
        #:   `422 {"loc": ["query","name"]}` 가 났다. 제품이 아니라 **우리가 틀린 문**이다.
        #:   ⚠ 「비밀은 쿼리에 0」과 안 부딪힌다 — 여기 실리는 것은 **키 이름**뿐이고
        #:     발급된 `secret` 은 **응답 본문**으로만 온다.
        r, js = call("post", "/api/dsm/settings/api-keys?name=%s" % quote(name),
                     headers=admin)
        #: ★ [턴 Z · Q] 이름에 **방향**을 준다. `inbound_` 는 「이 키를 들고 **밖에서 안으로**
        #:   들어오는 부름에 쓴다」는 뜻이다 — 맨 `key` 는 사전 열쇠인지 API 키인지, 우리가
        #:   보내는 것인지 받는 것인지 글자만 봐서는 갈리지 않는다.
        #:   ⚠ **우리 이름은 지역 변수뿐이다.** `sc.get("key")`·`sc.get("api_key")` 는
        #:     서버 응답의 칸 이름이고 `"X-API-Key"` 는 계약 헤더 이름,
        #:     `"/api/dsm/settings/api-keys"` 는 제품의 경로다 — 셋은 **우리 것이 아니라서
        #:     못 바꾼다**(바꾸면 측정이 깨진다 · `gx-homonyms` 를 이 사유로 얼렸다).
        inbound_key = inbound_key_id = None
        scopes = [js if isinstance(js, dict) else {}]
        if isinstance(scopes[0].get("data"), dict):
            scopes.append(scopes[0]["data"])
        for sc in scopes:
            inbound_key = inbound_key or sc.get("key") or sc.get("api_key") or sc.get("secret")
            inbound_key_id = (inbound_key_id if inbound_key_id is not None
                              else (sc.get("id") or sc.get("key_id")))
        with_inbound_key = None
        if inbound_key:
            rk, _ = call("get", "/api/dsm/events", headers={"X-API-Key": inbound_key})
            with_inbound_key = rk.status
        ra, _ = call("get", "/api/dsm/events")
        anon = ra.status
        if inbound_key_id is not None:
            rd, _ = call("delete", "/api/dsm/settings/api-keys/%s" % inbound_key_id,
                         headers=admin)
            reverted = " · [되돌림] DELETE api-keys/%s -> %s" % (inbound_key_id, rd.status)
        elif r.status == 422:
            #: ★ [U3 쪽지 ① · 턴 Z] **422 는 지울 것을 안 만든다.** 핸들러가 돌기 전에
            #:   떨어지므로 `transaction.atomic` 안으로도 안 들어간다 — U3 가 재현해
            #:   **키 0개**를 확인했다. 「손으로 지운다」는 다음 사람을 헛일 시킨다.
            reverted = " · [되돌릴 것 없음] 422 는 핸들러 앞에서 떨어졌다 — 키 0개 생성"
        else:
            reverted = " · **되돌리지 못했다** — 응답에서 키 id 를 못 찾았다(손으로 지운다)"
        out.append(result("U6#1", "POST /settings/api-keys", bool(inbound_key),
                          with_inbound_key == 200 and anon == 401,
                          "발급 %s · 키 받음=%s · 키로 GET events=%s(기대 200) · "
                          "익명 GET events=%s(기대 401)%s"
                          % (r.status, bool(inbound_key), with_inbound_key, anon, reverted)))
    guarded(out, "U6#1", "POST /settings/api-keys", _u6_1)

    # #2 이벤트 목록 — 200 + **봉투가 아닌 진짜 JSON**(total 과 events 가 둘 다)
    def _u6_2():
        if not token:
            no_cred("U6#2", "GET /api/dsm/events")
            return
        r, js = call("get", "/api/dsm/events", headers=bearer)
        d = js if isinstance(js, dict) else {}
        inner = d.get("data") if isinstance(d.get("data"), dict) else {}
        has_total = ("total" in d) or ("total" in inner)
        has_rows = isinstance(d.get("events"), list) or isinstance(inner.get("events"), list)
        out.append(result("U6#2", "GET /api/dsm/events", r.status == 200,
                          r.status == 200 and has_total and has_rows,
                          "status=%s · total 칸=%s · events 배열=%s · 최상위 칸 %s "
                          "— 봉투만 오면 빨강이다"
                          % (r.status, has_total, has_rows, sorted(d)[:8])))
    guarded(out, "U6#2", "GET /api/dsm/events", _u6_2)

    # #3 이벤트 상세 — JWT 200 · **키는 거절**(D-371 의 의도된 절반) → ◐ 상한
    def _u6_3():
        if not token:
            no_cred("U6#3", "GET /api/dsm/events/{id}")
            return
        ev = seed_b or U6_ABSENT_EVENT
        rj, _ = call("get", "/api/dsm/events/%s" % ev, headers=bearer)
        rk, _ = call("get", "/api/dsm/events/%s" % ev,
                     headers={"X-API-Key": "onb-not-a-real-key"})
        ok = (rj.status == 200) and (rk.status in (401, 403))
        out.append(result("U6#3", "GET /api/dsm/events/{id}", rj.status == 200, ok,
                          "JWT=%s(기대 200) · 키=%s(기대 401/403 — D-371 의 의도된 절반) "
                          "→ 둘 다 그대로면 **◐ 상한**. 키가 200 이면 D-371 이 깨진 것이다"
                          % (rj.status, rk.status), cap_half=ok))
    guarded(out, "U6#3", "GET /api/dsm/events/{id}", _u6_3)

    # #4 웹훅 수신 — 구독 200 → 목록 +1 → [서버 기록] 서명 붙은 발송 행 · **되돌린다**
    def _u6_4():
        if not token:
            no_cred("U6#4", "POST /webhook-subscriptions")
            return
        before, _ = call("get", "/api/dsm/webhook-subscriptions", headers=bearer)
        n0 = _count_rows(_json_of(before))
        #: ★★ [U3 쪽지 ① · 턴 Z] U6#1 과 **같은 뿌리**다 —
        #:   `api.py:698 create_webhook_subscription(self, request, endpoint_url: str,
        #:   signing_key_ref: str, event_types: str = "", …)` 도 전부 맨 스칼라라
        #:   django-ninja 가 **질의**로 잡는다. 본문으로 보내면 422 다.
        #:   `signing_key_ref` 는 **참조 이름**이지 키 자체가 아니다(값은 안 싣는다).
        r, js = call("post", "/api/dsm/webhook-subscriptions?"
                     + urlencode({"endpoint_url": "https://example.invalid/onb-u6",
                                  "signing_key_ref": U6_SIGNING_KEY_REF,
                                  "event_types": "event.created"}),
                     headers=bearer)
        sid = None
        scopes = [js if isinstance(js, dict) else {}]
        if isinstance(scopes[0].get("data"), dict):
            scopes.append(scopes[0]["data"])
        for sc in scopes:
            sid = sid if sid is not None else (sc.get("id") or sc.get("subscription_id"))
        after, _ = call("get", "/api/dsm/webhook-subscriptions", headers=bearer)
        n1 = _count_rows(_json_of(after))
        signed = _outbox_signed()
        if sid is not None:
            rd, _ = call("delete", "/api/dsm/webhook-subscriptions/%s" % sid, headers=bearer)
            reverted = " · [되돌림] DELETE %s -> %s" % (sid, rd.status)
        elif r.status == 422:
            reverted = " · [되돌릴 것 없음] 422 는 핸들러 앞에서 떨어졌다 — 구독 0개 생성"
        else:
            reverted = " · **되돌리지 못했다** — 구독 id 를 못 찾았다(손으로 지운다)"
        out.append(result("U6#4", "POST /webhook-subscriptions",
                          r.status in (200, 201), (n1 > n0) and signed >= 1,
                          "구독 %s · 목록 %d -> %d · [서버 기록] 서명이 붙은 발송 행 %d건"
                          "(-1 은 표를 못 읽은 것이다)%s — 이 걸음은 **새 사건을 만들지 않는다**"
                          "(제품에 그 문이 없다). 발송 갈래는 이미 남은 행으로 잰다"
                          % (r.status, n0, n1, signed, reverted)))
    guarded(out, "U6#4", "POST /webhook-subscriptions", _u6_4)

    # #9 상태 갱신 — **없는 id 로** 두드린다: 404 면 닿은 것 · 403 이면 못 닿은 것 (P-83)
    def _u6_9():
        if not token:
            no_cred("U6#9", "POST /events/{id}/response")
            return
        #: ★ [턴 Z · Q] `api.py:479 advance_response(self, request, event_id: int,
        #:   to_state: str, reason: str = "")` — 여기도 맨 스칼라라 **질의**다.
        #:   본문으로 보내면 핸들러에 닿기 전에 422 로 떨어져 **P-83 눈금이 안 선다**
        #:   (404 = 관문을 지났다 · 403 = 관문에서 막혔다 — 422 는 둘 다 아니다).
        r, _ = call("post", "/api/dsm/events/%d/response?%s"
                    % (U6_ABSENT_EVENT, urlencode({"to_state": "acknowledged"})),
                    headers=bearer)
        out.append(result("U6#9", "POST /events/{id}/response", True, r.status == 404,
                          "없는 사건(%d)으로 두드렸다 -> %s. **404 = 관문을 지나 핸들러까지 "
                          "갔다(상태는 안 건드렸다)** · 403 = 관문에서 막혔다(P-83 눈금). "
                          "전이 자체는 U3#7 이 사람 자격으로 잰다 — 같은 사실을 두 번 바꾸지 "
                          "않는다 · 외부 App 의 인증 경로가 authn_paths 대장에 아직 없다"
                          % (U6_ABSENT_EVENT, r.status)))
    guarded(out, "U6#9", "POST /events/{id}/response", _u6_9)

    # #12 인증 실패 — 익명 읽기 다섯이 **전부 401** (200 봉투 하나면 빨강 · P-133)
    def _u6_12():
        codes = {}
        for path in U6_ANON_READS:
            r, _ = call("get", path)
            codes[path] = r.status
        all401 = all(c == 401 for c in codes.values())
        two_hundreds = [p for p, c in codes.items() if c == 200]
        out.append(result("U6#12", "/api/dsm/** 익명", True, all401,
                          "익명 읽기 %d건 %s — 전부 401=%s%s"
                          % (len(codes), codes, all401,
                             "" if not two_hundreds else
                             " · **200 봉투 %d건: %s** (P-133 이 쫓던 자리)"
                             % (len(two_hundreds), two_hundreds))))
    guarded(out, "U6#12", "/api/dsm/** 익명", _u6_12)

    # #14 스키마 버전 — 응답 헤더 `X-GX-Schema` (backend/common/schema_header.py:19)
    def _u6_14():
        r, _ = call("get", "/api/dsm/health")
        h = dict((k.lower(), v) for k, v in (r.headers or {}).items())
        val = h.get("x-gx-schema")
        out.append(result("U6#14", "헤더 X-GX-Schema", True, bool(val),
                          "GET /api/dsm/health -> %s · X-GX-Schema=%s · 헤더 %d개"
                          % (r.status, val or "**없다**", len(h))))
    guarded(out, "U6#14", "헤더 X-GX-Schema", _u6_14)

    # #15 연계 헬스체크 — 200 또는 503(둘 다 답한 것) + 검사 셋의 이름
    def _u6_15():
        r, js = call("get", "/api/dsm/health")
        text = json.dumps(js, ensure_ascii=False) if js is not None else ""
        checks = [w for w in ("db", "cache", "queue") if w in text]
        out.append(result("U6#15", "GET /api/dsm/health", r.status in (200, 503),
                          r.status in (200, 503) and len(checks) >= 1,
                          "status=%s (200·503 둘 다 답한 것 — 503 은 「지금 아프다」이지 문 "
                          "없음이 아니다) · 검사 이름 %s · 익명 허용 목록의 문이다"
                          % (r.status, checks or "없음")))
    guarded(out, "U6#15", "GET /api/dsm/health", _u6_15)


# ---------------------------------------------------------------------------
# U4 · 재난안전과 (1440)
# ---------------------------------------------------------------------------
def rows_u4(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam, probe_user=""):
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
    # (U4#9 는 아래에 있다 — 표 순서가 아니라 화면 순서로 잰다)
    out.append(result("U4#11", "/device", seen, rows >= 1,
                      f"url={page.url} · 「드론·로봇 장비 등록」={('드론·로봇 장비 등록' in b)} · 머리줄={(ADMIN_HEADER in b)} · 표 행 {rows} · 본문 앞 {b[:80]!r}", url=url))

    # ══ [P-180 · 턴 V] 정본이 두 칸을 채운 뒤 늘어난 행 ═══════════════════════
    # #1 주간 상황 요약: /dsm/events · 단추 「7일」 · [API 호출] GET /api/dsm/events?since=… 200
    #    ★ 정본이 못박아 둔 것: 이 프리셋은 요약 문(`summary?hours=168`)을 **부르지 않는다** —
    #      부르는 것은 목록 문이다. 턴 T 착시 ⑨는 「누를 데가 없다」였을 뿐 그 호출을 약속한 적이 없다.
    m = net.mark()
    url = goto(page, web, "/dsm/events")
    seen = visible_text(page, "7일")
    pred, evidence = False, ""
    if seen:
        click_button(page, "7일", exact=True)
        page.wait_for_timeout(6_000)
        g = [r for r in net.find("GET", "/api/dsm/events?", m) if "since=" in r["url"] and r["status"] == 200]
        js = (g[-1].get("json") if g else None) or {}
        n_srv = len(js.get("events", [])) if isinstance(js, dict) else -1
        pred = bool(g)
        evidence = (f"「7일」 누른 뒤 GET events?since=… 200={bool(g)} (서버 {n_srv}건) · "
                    f"summary?hours=168 호출 {len(net.find('GET', 'hours=168', m))}건 — **정본은 이 문을 약속하지 않는다**")
        url = page.url
    else:
        evidence = "「7일」 칸이 안 보인다 (EventList.tsx PERIODS.d7)"
    out.append(result("U4#1", "/dsm/events", seen, pred, evidence, url=url))

    # #5 월간 보고서 자동 생성: /dsm/reports · 카드 「이번 달 우리 센터」 + 단추 「만들기」 ·
    #    ★★ 정본의 술어는 **「자동 행 ≥ 1」**이다 — U4 본인이 누르는 것이 아니다.
    #      읽기 전용 U4(`view_only_*`)의 「만들기」는 **403 이 옳고**(플랫폼 문지기 `read_only_role`),
    #      자동본은 매월 1일 배치 `monthly_report.run_monthly_all` 이 `trigger=auto` 로 만든다.
    #      사람이 누른 행(`trigger=manual`)을 세면 PRD §7.4 의 수가 거짓이 된다 — **칸으로 가른다.**
    #      ⚠ 그래서 이 행은 **누르지 않는다**(누르면 제품에 쓸모없는 403 을 하나 남길 뿐이다).
    m = net.mark()
    url = goto(page, web, "/dsm/reports", settle_ms=8_000)
    b = body(page)
    seen = ("이번 달 우리 센터" in b) and ("만들기" in b)
    n_auto = auto_report_runs("monthly")
    runs200 = net.ok("GET", "/api/dsm/reports/runs", m)
    out.append(result("U4#5", "/dsm/reports", seen, n_auto >= 1,
                      f"[서버 기록] trigger=auto · kind=monthly 실행 기록 {n_auto}행 (≥1 이어야 한다) · "
                      f"화면 GET reports/runs 200={bool(runs200)} · 「이번 달 우리 센터」={('이번 달 우리 센터' in b)} "
                      f"「만들기」={('만들기' in b)} · **누르지 않았다 — 읽기 전용 U4 의 만들기는 403 이 옳다**",
                      url=url))

    # #7 보고서 다운로드: 같은 화면 · 「DOCX 내려받기」(정본 · 결정 ⑤) ·
    #    [API 호출] GET /api/dsm/reports/runs/{id}.docx 200 · wordprocessingml
    #    + [화면 상태] 받은 바이트 > 1,024 (`Reports.tsx` 가 바이트 수를 **상태 칸**에 적는다 — 토스트가 아니다)
    #    ⚠ 누르는 자리가 둘이다: 만든 직후 카드의 「DOCX 내려받기」와 실행 목록 표 「파일」 열의 「DOCX」.
    #      읽기 전용 U4 는 만들 수 없으므로 그 사람에게 서는 자리는 **표의 것**이다.
    m = net.mark()
    b = body(page)
    phrase = ("DOCX 내려받기" in b) or ("DOCX" in b)
    pred, evidence = False, ""
    clicked = click_button(page, "DOCX", exact=True) or click_button(page, "DOCX 내려받기")
    page.wait_for_timeout(9_000)
    docx = [r for r in net.rows[m:] if ".docx" in r["url"] and "/reports/runs/" in r["url"]]
    ok200 = [r for r in docx if r["status"] == 200]
    wordml = any("wordprocessingml" in (r.get("ctype") or "") for r in ok200)
    b2 = body(page)
    got_bytes = 0
    mm = re.search(r"([\d,]+)\s*바이트", b2)
    if mm:
        try:
            got_bytes = int(mm.group(1).replace(",", ""))
        except ValueError:
            got_bytes = 0
    pred = bool(ok200) and wordml and got_bytes > 1024
    evidence = (f"단추 누름={clicked} (문구 「DOCX 내려받기」={('DOCX 내려받기' in b)} · 표의 「DOCX」={('DOCX' in b)}) · "
                f"GET reports/runs/{{id}}.docx {[r['status'] for r in docx]} · wordprocessingml={wordml} · "
                f"상태 칸 바이트 {got_bytes:,} (>1,024 이어야 한다) · 「내려받았습니다」={('내려받았습니다' in b2)} · "
                f"[서버 기록] 내려받을 수 있는 최신 monthly 실행 id={latest_succeeded_run('monthly')}")
    out.append(result("U4#7", "/dsm/reports", phrase, pred, evidence, url=page.url))

    # #15 상급기관 제출 자료: /dsm/events · 「보고 표시」/「보고함」 (누르기 전/후가 **다른 말**이다) ·
    #    [서버 기록] POST /api/dsm/events/{id}/upper-report 200 → 재조회에서 그 사건의 표시가 서버 값으로 「보고함」
    #    ★★ 되돌린다 — 같은 단추를 한 번 더 누르면 해제(DELETE)다. 체크를 남기면 다음 회차의
    #      「상급기관 제출용」 보고서가 우리가 만든 체크를 집계한다.
    #    ⚠ U4 는 읽기 전용이다 — 관문이 거절하면(403) 그것은 **제품이 옳게 막은 것**이고, 그 사실을
    #      증거에 그대로 적는다(빨강을 회색으로 바꾸지 않는다).
    m = net.mark()
    url = goto(page, web, "/dsm/events")
    b = body(page)
    seen = ("보고 표시" in b) or ("보고함" in b)
    pred, evidence = False, ""
    if seen:
        clicked = click_button(page, "보고 표시", exact=True)
        page.wait_for_timeout(7_000)
        posts = net.find("POST", "/upper-report", m)
        codes = [p["status"] for p in posts]
        m2 = net.mark()
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(6_000)
        flags = net.ok("GET", "/api/dsm/events/upper-report/flags", m2)
        fjs = (flags or {}).get("json") or {}
        # 응답은 {"flags": {"<event_id>": {...}}, "total": n} 이다 (`api_u24.py:528`)
        n_flag = fjs.get("total", len(fjs.get("flags", {}))) if isinstance(fjs, dict) else -1
        pred = bool(posts) and 200 in codes and n_flag >= 1
        # ── 되돌리기 — 판정 뒤에 (판정은 바뀌지 않는다) ──
        back = click_button(page, "보고함", exact=True)
        page.wait_for_timeout(6_000)
        dels = net.find("DELETE", "/upper-report", m2)
        evidence = (f"「보고 표시」 누름={clicked} · POST upper-report {codes} · "
                    f"재조회 flags 200={bool(flags)} 체크 {n_flag}건 · "
                    f"[되돌림] 「보고함」 다시 누름={back} DELETE {[d['status'] for d in dels]}"
                    + (" · ⚠ 관문이 거절했다(읽기 전용 U4) — 제품이 옳게 막은 자리다" if 403 in codes else ""))
    else:
        evidence = "「보고 표시」·「보고함」 둘 다 화면에 없다 (EventList.tsx 행마다 그리는 토글)"
    out.append(result("U4#15", "/dsm/events", seen, pred, evidence, url=url))

    # #16 감사 대응 이력: /dsm/audit · 「N.N초 · 60초 안」 (**틀 문장** — 수는 매회 다르다) ·
    #    [API 호출] GET /api/dsm/audit 200 + [화면 상태] 상태 칸의 계측 값 1 · 표 행 ≥ 1
    #    ⚠ 이 칸은 **계측이지 토스트가 아니다**(`AuditLog.tsx` 머리말).
    m = net.mark()
    url = goto(page, web, "/dsm/audit", settle_ms=8_000)
    b = body(page)
    seen = "초 · 60초 안" in b            # 틀 문장의 **고정 부분**만 본다 (수는 매회 다르다)
    g = net.ok("GET", "/api/dsm/audit", m)
    js = (g or {}).get("json") or {}
    n_srv = js.get("total", -1) if isinstance(js, dict) else -1
    rows = table_rows(page)
    # #9 증빙 영상 확인 [P-205 · 턴 Y] — **표 칸 「영상 구간」 · 문은 200 또는 404**
    #    ★ 404 는 **문 없음이 아니다** — 「이 사건에 영상이 없다」이다. 둘을 한 칸에 넣으면
    #      「없는 문」과 「빈 자료」가 같은 색이 된다. 누를 단추가 없으므로 **◐ 상한**이다
    #      (추출은 계약 11조 잠금 · `pages/EventDetail.tsx:457` 은 이름칸이다).
    def _u4_9():
        m = net.mark()
        ev = snap_event or seed_a
        url = goto(page, web, f"/dsm/events/{ev}")
        b = body(page)
        cell = "영상 구간" in b
        calls = net.find("GET", f"/api/dsm/events/{ev}/clip", m)
        codes = [r["status"] for r in calls]
        door = any(c in (200, 404) for c in codes)
        if not calls:
            # 화면이 그 문을 스스로 안 부르면 **우리가 부른다** — 문이 사는지가 이 행의 절반이다
            try:
                r = page.request.get(f"{web}/api/dsm/events/{ev}/clip")
                codes = [r.status]
                door = r.status in (200, 404)
            except Exception as exc:                    # noqa: BLE001
                codes = ["부르지 못함: %s" % type(exc).__name__]
        out.append(result("U4#9", "/dsm/events/:id", cell, door and cell,
                          f"표 칸 「영상 구간」={cell} · clip 문 {codes} "
                          f"(200·404 둘 다 문이 산 것 · 404 는 빈 자료다) · "
                          f"누를 단추 없음 → **◐ 상한**(추출은 계약 11조 잠금)",
                          cap_half=True, url=url))
    guarded(out, "U4#9", "/dsm/events/:id", _u4_9)

    out.append(result("U4#16", "/dsm/audit", seen, bool(g) and rows >= 1,
                      f"GET /api/dsm/audit 200={bool(g)} (서버 전체 {n_srv}건) · 표 행 {rows} · "
                      f"상태 칸 「초 · 60초 안」={seen} · 「첫 응답」 칸={('첫 응답' in b)} · 제목 「감사 기록」={('감사 기록' in b)}",
                      url=url))


# ---------------------------------------------------------------------------
# U5 · 시스템 관리자 (1440)
# ---------------------------------------------------------------------------
def rows_u5(page, net, web, out, lg, *, snap_event, seed_a, seed_b, probe_cam, probe_user=""):
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

    # ══ [P-180 · 턴 V] 정본이 두 칸을 채운 뒤 늘어난 행 ═══════════════════════
    # #1 사용자 계정 생성: /dsm/people · 「사람·역할 — 계정 만들기 · 비활성화」 ·
    #    [서버 기록] POST /api/dsm/settings/people/create 200 → **사용자 수 +1**
    #    ⚠ 문 경로는 `/settings/people` 이 아니라 `/settings/people/create` 다 —
    #      `/settings/{domain}` 이 삼켜 405 를 낸다 (`api.ts` `dsmU56Endpoint` 머리말 · 라우트 삼킴).
    #    ★★ 되돌린다 — 같은 화면의 「비활성화」로 끈다. 계정을 지우는 문은 제품에 없다(지우지 않는다).
    m = net.mark()
    u0 = user_count()
    url = goto(page, web, "/dsm/people", settle_ms=8_000)
    b = body(page)
    seen = PEOPLE_HEADLINE in b
    pred, evidence = False, ""
    if seen:
        try:
            page.get_by_label("아이디").first.fill(probe_user)
            page.get_by_label("이메일").first.fill(f"{probe_user}@example.invalid")
            # 씨앗 계정의 비밀번호는 **새로 짓는다** — 역할 계정의 비밀번호를 쓰지 않는다
            # (한 자리가 새면 여럿이 샌다). 값은 어디에도 적지 않는다.
            page.get_by_label("비밀번호").first.fill(secrets.token_urlsafe(18) + "Aa1!")
            page.get_by_label("소속(테넌트) ID").first.fill(str(SEED_GROUP_ID))
            page.get_by_label("표시 이름").first.fill("V 온보딩 실측 씨앗")
        except Exception as exc:                        # noqa: BLE001
            evidence = f"서식 채우기 실패 {type(exc).__name__} · "
        click_button(page, "계정 만들기", exact=True)
        page.wait_for_timeout(8_000)
        posts = net.find("POST", "/api/dsm/settings/people/create", m)
        codes = [p["status"] for p in posts]
        u1 = user_count()
        pred = bool(posts) and 200 in codes and u1 == u0 + 1
        # ── 되돌리기 — 판정 뒤에 (판정은 바뀌지 않는다) ──
        new_id = 0
        for p in posts:
            js = p.get("json") or {}
            if isinstance(js, dict):
                new_id = js.get("user_id") or js.get("id") or new_id
        off = []
        if new_id:
            # 「계정 비활성화」 카드의 칸 — `placeholder="user_id"` (`People.tsx`).
            # 행을 지우지 않는다(지우는 문은 제품에 없고, 삭제는 대표 결정이다).
            try:
                page.get_by_placeholder("user_id").first.fill(str(new_id))
            except Exception:                           # noqa: BLE001
                try:
                    page.locator("input[type=number]").last.fill(str(new_id))
                except Exception:                       # noqa: BLE001
                    pass
            click_button(page, "비활성화", exact=True)
            page.wait_for_timeout(7_000)
            off = net.find("POST", "/deactivate", m)
        evidence += (f"POST people/create {codes} · [서버 기록] 사용자 수 {u0} → {u1} · "
                     f"[되돌림] 만든 계정 id={new_id or '못 읽었다'} 비활성화 {[o['status'] for o in off] or '못 되돌림'} · "
                     f"씨앗 이름 {probe_user}")
    else:
        evidence = f"「{PEOPLE_HEADLINE}」 이 화면에 없다 · url={page.url}"
    out.append(result("U5#1", "/dsm/people", seen, pred, evidence, url=url))

    # #9 알림 규칙 설정: /dsm/notify · 「알림 받는 사람·채널」 ·
    #    [서버 기록] POST /api/dsm/settings/notify-rules/save 200 → `…/list` 반영
    #    ★★ 이 행의 클릭은 **되돌린다** (`verify_click_completes` U5#9 `revert_toggle` · 턴 U 절 4).
    #      턴 T 는 pk 9 를 **끈 채로** 남겼고 다음 게이트(`verify_seed_roles` K2 수신자)가 빨강이었다.
    #    ⚠ 심각 수신자를 0명으로 만드는 끄기는 서버가 **409** 로 거절한다 — 그것도 제품이 옳은 것이다.
    m = net.mark()
    url = goto(page, web, "/dsm/notify", settle_ms=8_000)
    b = body(page)
    seen = NOTIFY_HEADLINE in b
    pred, evidence = False, ""
    list0 = net.ok("GET", "/api/dsm/settings/notify-rules/list", m)
    js0 = (list0 or {}).get("json") or {}
    rules0 = js0.get("rules", []) if isinstance(js0, dict) else []
    on0 = sum(1 for r in rules0 if r.get("is_active"))
    if seen and rules0:
        label = "끄기" if visible_text(page, "끄기") else "켜기"
        clicked = click_button(page, label, exact=True)
        page.wait_for_timeout(7_000)
        saves = net.find("POST", "/api/dsm/settings/notify-rules/save", m)
        codes = [s["status"] for s in saves]
        m2 = net.mark()
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(6_000)
        list1 = net.ok("GET", "/api/dsm/settings/notify-rules/list", m2)
        js1 = (list1 or {}).get("json") or {}
        rules1 = js1.get("rules", []) if isinstance(js1, dict) else []
        on1 = sum(1 for r in rules1 if r.get("is_active"))
        pred = bool(saves) and 200 in codes and on1 != on0
        # ── 되돌리기 — 같은 문으로. 판정 뒤에 (판정은 바뀌지 않는다) ──
        back_label = "켜기" if label == "끄기" else "끄기"
        back = click_button(page, back_label, exact=True)
        page.wait_for_timeout(7_000)
        m3 = net.mark()
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(6_000)
        list2 = net.ok("GET", "/api/dsm/settings/notify-rules/list", m3)
        js2 = (list2 or {}).get("json") or {}
        rules2 = js2.get("rules", []) if isinstance(js2, dict) else []
        on2 = sum(1 for r in rules2 if r.get("is_active"))
        evidence = (f"「{label}」 누름={clicked} · POST notify-rules/save {codes} · "
                    f"켜진 규칙 {on0} → {on1} (바뀜={on1 != on0}) · "
                    f"[되돌림] 「{back_label}」 누름={back} → {on2} (복구={on2 == on0})"
                    + (" · ⚠ 409 — 심각 수신자 0명 저장을 서버가 거절했다(제품이 옳다)" if 409 in codes else ""))
        # #10 알림 채널 설정 — **같은 저장이 낸 값**을 본다 (정본: 채널 값이 `…/list` 에 남음)
        chans = sorted({c for r in (rules2 or rules1 or rules0) for c in (r.get("channels") or [])})
        known = [c for c in chans if c in ("email", "webpush")]
        out.append(result("U5#10", "/dsm/notify (채널 열)", seen, bool(saves) and 200 in codes and bool(known),
                          f"저장 200={bool(saves) and 200 in codes} · `…/list` 의 채널 값 {chans} · "
                          f"email/webpush 남음={known} · 제목 1={seen} "
                          f"(⚠ 채널 이름 자체는 아직 사전 밖이다 — 제목으로 자리를 단언하고 값은 서버 기록으로 잰다)",
                          url=url))
    else:
        evidence = f"제목={seen} · 서버 규칙 {len(rules0)}건 (0건이면 누를 토글이 없다)"
        out.append(result("U5#10", "/dsm/notify (채널 열)", seen, False,
                          f"규칙 저장을 못 했다 — 위 U5#9 참조 (서버 규칙 {len(rules0)}건)", url=url))
    out.append(result("U5#9", "/dsm/notify", seen, pred, evidence, url=url))

    # #14 시스템 상태 확인: /dsm/system · 「재시작을 요청합니다」 ·
    #    [서버 기록] POST /api/dsm/system/restart-request 200 → 응답 `executed: false`
    #    + GET /api/dsm/system/requests 200 **행 +1**
    #    ⚠ 목록 응답의 칸 이름은 `executed` 가 아니라 `status`(`"requested"`)다 — `executed` 는 POST 응답에만 있다.
    #    ⚠ 되돌림 **없음**: 이 문은 「기록만 남긴다」이고 기록을 지우는 문이 제품에 없다.
    #      그것이 옳다 — 「눌렀다」를 지울 수 있으면 그 표는 근거가 아니다. 사유를 적고 안 되돌린다.
    m = net.mark()
    s0 = system_request_count()
    url = goto(page, web, "/dsm/system", settle_ms=8_000)
    b = body(page)
    seen = "재시작을 요청합니다" in b
    pred, evidence = False, ""
    if seen:
        try:
            page.get_by_placeholder("왜 재시작이 필요한지 한 줄").first.fill(
                "V 온보딩 실측 (자동) — 실행하지 않는다. 기록만 남긴다")
        except Exception:                               # noqa: BLE001
            try:
                page.locator("input[type=text]").last.fill("V 온보딩 실측 (자동) — 기록만")
            except Exception:                           # noqa: BLE001
                pass
        click_button(page, "재시작을 요청합니다")
        page.wait_for_timeout(8_000)
        posts = net.find("POST", "/api/dsm/system/restart-request", m)
        codes = [p["status"] for p in posts]
        executed = None
        for p in posts:
            js = p.get("json") or {}
            if isinstance(js, dict) and "executed" in js:
                executed = js["executed"]
        m2 = net.mark()
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(6_000)
        reqs = net.ok("GET", "/api/dsm/system/requests", m2)
        rjs = (reqs or {}).get("json") or {}
        rrows = rjs.get("requests", rjs.get("rows", [])) if isinstance(rjs, dict) else []
        requested = any(str(r.get("status")) == "requested" for r in rrows)
        s1 = system_request_count()
        pred = bool(posts) and 200 in codes and executed is False and s1 == s0 + 1
        evidence = (f"POST restart-request {codes} · 응답 executed={executed} (False 여야 한다 — "
                    f"이 단추는 서버를 내리지 않는다) · GET system/requests 200={bool(reqs)} "
                    f"status=requested 있음={requested} · [서버 기록] 요청 행 {s0} → {s1} · "
                    f"[되돌림] **없다 — 기록을 지우는 문이 제품에 없고 그것이 옳다**")
    else:
        evidence = f"「재시작을 요청합니다」 단추가 안 보인다 · url={page.url}"
    out.append(result("U5#14", "/dsm/system", seen, pred, evidence, url=url))



# ═══════════════════════════════════════════════════════════════════════════
# [P-170 ① · 2026-09-18 턴 U · 차선 Q] **재는 동안 아무도 로그인하지 않는다**
#
#   턴 T 에 V 가 재는 동안 조율자의 게이트가 같은 역할 계정으로 로그인해 V 의 세션을
#   끊었다(계정당 세션 1개 → `end_previous_session` → 429 · D-487 ①). V 는 그 판을 버렸다.
#   이 도구는 **로그인을 한다** — 그러므로 LOCK 을 먼저 본다.
#
#   ★ **잠근 사람은 지나간다**: `GX_V_SESSION_ID` 가 LOCK 의 세션과 같으면 안 막는다.
#     그 밖의 사람에게는 **회색(exit 2)** 이다 — 회색은 초록이 아니다(D-301).
# ═══════════════════════════════════════════════════════════════════════════
def _v_lock_blocks(tag: str = TAG) -> bool:
    """V 단독 세션이 잠갔고 내가 그 사람이 아니면 True — 그때는 **재지 않는다**."""
    try:
        from v_lock import describe, is_locked
    except ImportError:                                   # 잠금 도구가 없으면 막지 않는다
        return False
    if not is_locked():
        return False
    print("%s ? **회색 — V 단독 중 · 재지 않음** (P-170 ① · docs/agent/evidence/V_LOCK)" % tag)
    print("%s   %s · 잠근 사람은 GX_V_SESSION_ID 를 주고 부른다" % (tag, describe()))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="온보딩 48행 첫 수 — 두 칸 채운 22행 셋째 술어 실측 (V 단독)")
    ap.add_argument("--web", default=os.environ.get("GX_WEB", "http://localhost:3002"),
                    help="사람이 보는 화면 — SPA 정적 서버")
    #: ★ [턴 Z · Q] **화면과 문은 다른 원점이다.** 3002 은 POST 를 501 text/html 로 낸다.
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"),
                    help="기계가 두드리는 문 — API 원점 (U6 여덟 행이 여기로 간다)")
    #: ★★ [P-170 ② · 턴 U] **씨앗 id 를 손으로 옮기지 않는다.** `capture_screens` 가 심고
    #:   `runs/<stamp>/seed.json` 에 적은 것을 읽는다 — 셋 다 `required` 를 뗀 이유가 그것이다.
    #:   손으로 준 값은 **언제나 이긴다**(특정 사건을 다시 재야 할 때가 있다).
    #:   씨앗 명세도 없고 손으로도 안 주면 **판정 불가(2)** 다 — 지어낸 번호로 재지 않는다.
    ap.add_argument("--snap-event", type=int, default=None, help="snapshot_path·주소가 있는 사건 id")
    ap.add_argument("--seed-a", type=int, default=None, help="알림 보내기 표본 (심각 씨앗)")
    ap.add_argument("--seed-b", type=int, default=None, help="전이·회신 표본 (미처리 씨앗)")
    ap.add_argument("--seed-file", default=None,
                    help="[P-170 ②] capture_screens 가 쓴 씨앗 명세 "
                         "(기본: docs/agent/evidence/P-157/runs/ 의 최신 seed.json)")
    ap.add_argument("--out", default="")
    ap.add_argument("--only", default="", help="쉼표로 나눈 페르소나만 (예: U1,U3) — 재측용")
    ap.add_argument("--canon", default=None,
                    help="[P-180] 정본 문서 자리 (기본: /docs/agent/onboarding_48.md → 저장소 docs/)")
    ap.add_argument("--check", action="store_true",
                    help="[P-180] 브라우저 없이 **문서와 도구를 대 본다** — 갈리면 2")
    args = ap.parse_args()

    if args.check:
        return check_tool_against_canon(args.canon)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if _v_lock_blocks():
        return 2
    from probe_marks import load_seed                       # noqa: E402
    seed = load_seed(args.seed_file)
    if seed["source"]:
        print(f"{TAG} [씨앗] {seed['source']} — 회차 {seed['run'] or '?'} · "
              f"사건 {seed['event_ids'] or '없음'}")
    #: 심각 씨앗 = `severity == critical` · 미처리 씨앗 = 그 밖의 첫 행. 등급은 명세가 나른다.
    sev = seed.get("severity_by_id") or {}
    crit = [i for i in seed["event_ids"] if sev.get(i) == "critical"]
    rest = [i for i in seed["event_ids"] if sev.get(i) != "critical"]
    #: ★★ [U1 요청 ③ · 2026-09-18 턴 V] **U2#4 는 그림을 보는 행이다.**
    #:   종전에는 `first_event_id` 를 그대로 썼는데, 그 씨앗의 `snapshot_path` 가 비어 있으면
    #:   `GET /api/dsm/events/{id}/snapshot` 이 404 이고 U2#4 가 내려간다 —
    #:   그때 내려간 것은 **제품이 아니라 씨앗**이다 [U1 실측 2026-09-18: 268496 → 404 ·
    #:   같은 순간 4802 → 200 image/jpeg 37,594B · `capture_screens` 씨앗 10건 전부 빈 문자열].
    #:   그래서 **그림이 실린 첫 씨앗**을 고른다. 하나도 없으면 고르지 않는다(회색으로 간다) —
    #:   지어낸 번호나 그림 없는 번호로 재지 않는다.
    snap_event = args.snap_event or seed.get("first_snapshot_event_id")
    snap_why = ""
    if not args.snap_event:
        if snap_event:
            snap_why = "씨앗 명세에서 snapshot_path 가 빈 문자열이 아닌 첫 사건"
        else:
            snap_why = ("씨앗 명세에 **그림 실린 사건이 하나도 없다** — U2#4 는 잴 수 없다(회색). "
                        "capture_screens 를 이 턴의 판으로 다시 돌리거나 --snap-event 를 손으로 준다 "
                        "(개발 DB 에서 200 이 확인된 사건: 4802)")
    seed_a = args.seed_a or (crit[0] if crit else seed["first_event_id"])
    seed_b = args.seed_b or (rest[0] if rest else None)
    print(f"{TAG} [씨앗·그림] snap_event={snap_event or '없음'} "
          f"({'손으로 준 값' if args.snap_event else snap_why})")
    if not (seed_a and seed_b):
        print(f"{TAG} 잴 사건이 없다 — {seed['why'] or '씨앗 명세에 등급이 갈리는 두 행이 없다'}. "
              f"`capture_screens.py` 를 --keep-seeds(기본)로 먼저 돌리거나 "
              f"--seed-a/--seed-b 를 손으로 준다. **판정 불가**")
        return 2
    #: ⚠ `snap_event` 가 없는 것은 **한 행(U2#4)만** 못 재는 것이다 — 나머지 34행은 잰다.
    #:   여기서 통째로 회색을 내면 씨앗 한 칸 때문에 그 회차 전부가 「못 잼」이 된다.
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
    return measure(args.web, snap_event, seed_a, seed_b, pw, out, only=only,
                   api_base=args.api)


if __name__ == "__main__":
    sys.exit(main())
