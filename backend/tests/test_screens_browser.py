# -*- coding: utf-8 -*-
"""**시험이 브라우저를 연다** — 단위가 못 보는 층을 시험 쪽에서도 본다 (D-386).

    "캡처 첫 시도에서 `/api/dsm/events` 가 **500** 이었다.
     **단위 시험 530건이 전부 초록인 채로** 그 라우트는 운영에서 죽어 있었다."

단위 시험은 함수를 부르고 브라우저는 **라우트를 때린다.** 그 사이(URL 배선·스키마
해석·직렬화·권한·미들웨어 순서·정적 자산)를 단위는 전부 건너뛴다. 그래서 이 파일이 있다.

두 갈래로 나뉜다 — **둘의 성질이 다르다**
------------------------------------------
    ① 언제나 도는 갈래  : 캡처가 남긴 **증거의 앞뒤가 맞는가.** 서버가 없어도 돈다.
                          구동체가 자기 눈을 감기면(자기표본을 목록에서 떨어뜨리면)
                          여기서 먼저 빨개진다
    ② 살아 있을 때 도는 갈래: 화면·API 가 실제로 서 있고 자격증명이 있으면
                          **브라우저를 열어** 화면이 뜨는지 본다

★ ②는 **환경이 없으면 건너뛴다.** 건너뛴 것을 통과로 적지 않는다 (D-301) —
  `pytest -rs` 가 사유를 그대로 말한다.

    GX_SCREENS_WEB=http://localhost:3002 GX_API=http://localhost:8000 \
    GX_ROUTE_USER=... GX_ROUTE_PASSWORD=... pytest backend/tests/test_screens_browser.py
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest

#: 증거 자리 — 컨테이너에서는 문서가 `/docs` 로 따로 붙는다(`/repo/docs` 는 없다).
_TAIL = Path("agent") / "evidence"


def _docs_root() -> Path | None:
    here = Path(__file__).resolve()
    for base in (here.parents[2] / "docs", Path("/docs")):
        if (base / _TAIL / "D-386" / "screen_routes.json").is_file():
            return base
    return None


DOCS = _docs_root()
WEB = os.environ.get("GX_SCREENS_WEB", "http://localhost:3002")
API = os.environ.get("GX_API", "http://localhost:8000")
USER = os.environ.get("GX_ROUTE_USER")
PASSWORD = os.environ.get("GX_ROUTE_PASSWORD")


def _release_session() -> str | None:
    """**동시 접속 잠금을 정직하게 푼다** — 끄지 않고, 이 시험 계정의 세션만 닫는다.

    dj-core 는 `user.token`/미소멸 토큰으로 「다른 기기 접속」을 판정한다. 그 판정을 끄면
    제품의 성질이 바뀌고, 그러면 이 시험이 보는 화면이 고객이 볼 화면이 아니게 된다.
    그래서 **제품의 로그아웃을 그대로 부른다**(`/api/v1/auth/logout`) — 사람이 하는 일과 같다.

    ★ 이 한 걸음이 없으면 이 시험은 「직전에 누가 로그인했나」에 따라 빨개진다.
      환경 때문에 흔들리는 빨강은 결함을 가린다 — 아무도 안 보게 되기 때문이다.
    """
    # ★ [D-411 · 2026-09-19] 앞판은 `/api/token/pair` 로 토큰을 받아 로그아웃했다.
    #   그 문은 제거됐다 — 그리고 **없어도 되는 문이었다**: `login` 자신이
    #   `end_previous_session` 으로 앞선 세션을 닫는다. 토큰을 받으러 다른 문에
    #   들르던 것은 처음부터 우회였고, 그 우회가 제거를 막고 있던 유일한 사용처였다.
    body = json.dumps({"username": USER, "password": PASSWORD,
                       "end_previous_session": True}).encode()
    req = urllib.request.Request(f"{API}/api/v1/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:                      # noqa: BLE001
        return f"토큰을 못 받았다: {type(exc).__name__} {exc}"
    #: 제품은 **200 + success:false** 로 「다른 곳에 활성 세션」을 낸다 — 토큰이 없다.
    #:   그 200 을 성공으로 읽으면 조용한 실패가 초록이 된다 [실측 · verify_route_alive].
    token = None
    for sc in (data, data.get("user") or {}, data.get("data") or {}):
        if isinstance(sc, dict) and data.get("success") is not False:
            for k in ("access_token", "access", "token"):
                v = sc.get(k)
                if isinstance(v, str) and len(v) > 40:
                    token = v
                    break
    if not token:
        return f"토큰이 응답에 없다 (success={data.get('success')!r})"
    out = urllib.request.Request(f"{API}/api/v1/auth/logout", data=b"{}",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {token}"})
    try:
        urllib.request.urlopen(out, timeout=20)
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            return f"로그아웃이 {e.code} 를 냈다"
    except Exception as exc:                      # noqa: BLE001
        return f"로그아웃을 못 불렀다: {type(exc).__name__} {exc}"
    return None


def _alive(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=5)
        return True
    except urllib.error.HTTPError:
        return True                     # 4xx 도 「서 있다」는 뜻이다
    except Exception:                   # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# ① 언제나 도는 갈래 — 구동체가 자기 눈을 감기지 않았나
# ---------------------------------------------------------------------------
@pytest.mark.skipif(DOCS is None, reason="캡처 증거를 못 찾았다 (아직 한 번도 안 찍었다)")
def test_captured_screens_and_recorded_routes_agree():
    """찍은 화면마다 **그 화면이 부른 API** 가 기록돼 있어야 한다.

    기록이 비면 `verify_route_alive.py` 가 때릴 것이 없어지고, **때릴 것이 없는 판정기는
    조용히 초록**이 된다 — 이 국면이 잡으려는 바로 그 모양이다(D-301).
    """
    routes = json.loads((DOCS / _TAIL / "D-386" / "screen_routes.json").read_text("utf-8"))
    index = (DOCS / _TAIL / "D-347" / "screens" / "INDEX.yaml").read_text("utf-8")
    shot_routes = [ln.split("route:", 1)[1].strip()
                   for ln in index.splitlines() if ln.strip().startswith("- route:")]
    assert shot_routes, "인덱스에 화면이 한 장도 없다 — 0장을 통과로 읽지 않는다"
    for route in shot_routes:
        assert route in routes["screens"], (
            f"{route} 를 찍었는데 그 화면이 부른 API 가 기록되지 않았다 — "
            f"때릴 것이 없는 판정기는 조용히 초록이 된다")
        assert routes["screens"][route], f"{route} 의 API 기록이 비었다"


@pytest.mark.skipif(DOCS is None, reason="캡처 증거를 못 찾았다")
def test_self_sample_route_is_still_watched():
    """★ D-310 자기표본 — **500 을 내던 그 라우트**가 감시 목록에서 빠지지 않았나."""
    routes = json.loads((DOCS / _TAIL / "D-386" / "screen_routes.json").read_text("utf-8"))
    paths = {c["path"].split("?", 1)[0]
             for calls in routes["screens"].values() for c in calls}
    assert "/api/dsm/events" in paths, (
        "자기표본 /api/dsm/events 가 기록에서 사라졌다 — 그 자리는 단위가 전부 초록인 채로 "
        "운영에서 500 을 내던 곳이다 (D-310)")


@pytest.mark.skipif(DOCS is None, reason="캡처 증거를 못 찾았다")
def test_blank_screens_are_named_not_dropped():
    """열어 봤더니 **빈 화면**이던 것은 목록에서 지우지 않는다.

    지우면 「안 해 본 것」과 「해 봤더니 안 되는 것」이 같아진다 — 그 둘이 같아지는 순간
    다음 사람이 같은 자리를 다시 판다 (D-300 부작위 시험의 화면 판).
    """
    routes = json.loads((DOCS / _TAIL / "D-386" / "screen_routes.json").read_text("utf-8"))
    blanks = routes.get("blank_screens", [])
    for b in blanks:
        assert b.get("why"), f"{b.get('route')} 를 빈 화면이라 적고 사유를 안 적었다"
        assert b["route"] not in routes["screens"], (
            f"{b['route']} 는 빈 화면인데 찍힌 화면 목록에도 있다 — 둘 중 하나가 거짓말이다")


# ---------------------------------------------------------------------------
# ② 살아 있을 때 도는 갈래 — **브라우저를 연다**
# ---------------------------------------------------------------------------
#: ★ [실측 2026-09-13] **수집 시각에 네트워크를 치지 않는다.**
#:   1차판은 이 자리에서 모듈 수준으로 `_alive()` 를 불렀다 — 즉 **pytest 수집 단계에서**
#:   개발 서버로 HTTP 두 번을 쳤다. 그러자 **전혀 다른 시험 하나가 빨개졌다**:
#:       tests/test_event_no_drop.py::test_full_queue_evicts_the_lowest_grade_not_the_oldest
#:       (dropped 0 != 1) — 이 파일을 빼면 538 전부 초록, 넣으면 그 하나가 실패 [실측 2회]
#:   원인이 무엇이든(공유 redis 를 통한 간섭이 가장 그럴듯하다), **시험 파일이 수집만으로
#:   바깥을 건드리면 다른 시험의 초록을 좀먹는다.** 그래서 판정을 시험 안으로 옮겼다.
def _live_reason() -> str | None:
    if DOCS is None:
        return "캡처 증거를 못 찾았다"
    if not (USER and PASSWORD):
        return "자격증명이 없다 (GX_ROUTE_USER/GX_ROUTE_PASSWORD)"
    if not _alive(f"{WEB}/"):
        return f"화면이 서 있지 않다 ({WEB})"
    if not _alive(f"{API}/api/docs"):
        return f"API 가 서 있지 않다 ({API})"
    return None


def test_browser_opens_dsm_screens():
    """로그인부터 사람이 하는 그대로 지나가며 **화면이 뜨는지** 본다.

    ★ 단언은 「그 화면에만 있는 글자」다. 로그인으로 튕긴 뒤에도 페이지는 뜨므로
      「200 이 왔다」를 통과로 두면 이 시험은 아무것도 보지 않는다.
    """
    why = _live_reason()
    if why is not None:
        pytest.skip(why)                  # 건너뛴 것을 통과로 적지 않는다 (D-301)
    playwright = pytest.importorskip("playwright.sync_api",
                                     reason="playwright 가 없다 — 브라우저를 열 수 없다")
    want = [("/dsm/dashboard", "관제 대시보드"), ("/dsm/events", "이벤트 목록")]
    with playwright.sync_playwright() as p:
        why = _release_session()
        assert why is None, f"앞선 세션을 닫지 못했다 — {why}"
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(f"{WEB}/login", wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(1_500)
            fields = page.locator("input")
            assert fields.count() >= 2, "로그인 화면에 입력칸이 둘 미만이다 — 화면이 안 떴다"
            fields.nth(0).fill(USER)
            fields.nth(1).fill(PASSWORD)
            page.get_by_role("button", name="Log In").click()
            page.wait_for_timeout(9_000)
            assert not page.url.rstrip("/").endswith("/login"), (
                f"로그인 뒤에도 로그인 화면이다 ({page.url})")
            for route, must_see in want:
                page.goto(f"{WEB}{route}", wait_until="networkidle", timeout=60_000)
                page.wait_for_timeout(6_000)
                body = page.inner_text("body")
                assert must_see in body, (
                    f"{route}: 「{must_see}」 가 화면에 없다 — 본문 {len(body)}자: "
                    f"{body[:160]!r}")
        finally:
            browser.close()
