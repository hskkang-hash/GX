#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""화면 캡처 **실행체** — 브라우저가 실제로 지나간 화면만 남긴다 (D-347 · D-384 ②).

두 턴 동안 스크린샷이 **0장**이었고, 0장인 것이 정직한 상태였다. 사유는 둘이었다:

    ① 브라우저를 여는 구동체가 없다 (playwright·selenium 어느 것도 requirements 에 없음)
    ② 프런트 의존 설치본이 저장소와 어긋나 빌드가 서지 않는다 (FRONTEND_DEPS_DRIFT · D-376)

[실측 2026-09-12] ②가 풀렸다 — **빌드가 1회 성공했다**(`vite build` 66초 · exit 0).
D-381 이 문턱을 낮춘 그대로다: **타입오류 3229건이 있어도 번들은 만들어진다.**
타입검사와 번들링은 다른 일이고, 스크린샷에 필요한 것은 후자다.

이 실행체가 하는 일 — 그리고 하지 않는 일
------------------------------------------
    한다   : 로그인 화면부터 **사람이 하는 그대로** 지나가며, 각 화면이 **떴는지 단언**하고
             그 순간에 찍는다. 단언이 깨지면 **찍지 않고 실패한다.**
    안 한다: 화면을 따로 띄워 예쁘게 만들어 찍는 일. 그것이 D-347 ①이 금지한 것이고,
             고객이 보는 자리에서는 착시가 아니라 **거짓말**이다 (D-284).

    ★ 단언이 캡처보다 먼저다. 「파일이 생겼다」는 성공이 아니다 — 로그인 화면으로
      튕긴 뒤 찍은 PNG 도 파일은 생긴다. 그래서 **화면마다 그 화면에만 있는 글자**를
      찾고, 못 찾으면 그 자리에서 멈춘다.

    ★ 씨앗은 **시험 데이터뿐**이다 (D-347 ④). 실제 영상 프레임·개인정보는 넣지 않는다.
      만든 것에는 전부 `PROBE_TAG` 가 붙고, 끝나면 지운다.

무엇이 필요한가 (없으면 **판정 불가로 멈춘다** · exit 2)
--------------------------------------------------------
    · API      기본 http://localhost:8000   (`--api`)
    · 화면     기본 http://localhost:3002   (`--web`) — `vite build` 산출물을 SPA 로 서빙
    · 계정     `--user` / `--password`

    python scripts/capture_screens.py --user gxprobe_e2e --password ****
    python scripts/capture_screens.py --dry-run     # 씨앗·정리 없이 도달만 본다

⚠ 계정은 **이 실행체가 만들지 않는다.** 사람이 만든 계정을 받아 쓴다 — 스크립트가
  계정을 만들면 그 계정의 존재를 아무도 대장에서 못 찾고, 비밀번호가 소스에 박힌다.
  이 저장소의 개발 환경에는 `gxprobe_e2e` 를 손으로 만들어 두었고, 그 계정은
  **개발 DB 에만** 있다. 운영에 같은 계정을 만들지 말 것.

산출: `docs/agent/evidence/D-347/screens/SCREENS-1/<ROLE>/<route>.png`
      + `run_log.json` (단계 시각). `scripts/verify_screens.py` 가 이 둘을 ±5분으로 대조한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 이 실행체가 만든 씨앗에만 붙는 표. **지울 때의 유일한 근거**다.
PROBE_TAG = "gxprobe-D384-screen"

#: 시나리오 코드. E2E-1·2·3 은 업무 시나리오 등재부(`e2e_contract.py`)의 것이므로
#: 쓰지 않는다 — 이것은 **화면 캡처 실행**이고, 이름이 그 사실을 말해야 한다.
SCENARIO = "SCREENS-1"

ROOT = Path(__file__).resolve().parent.parent

#: 증거를 어디에 남기나. 컨테이너에서는 저장소가 `/repo` 로, 문서 트리가 `/docs` 로
#: **따로** 마운트된다 — `/repo/docs` 는 없다. 그래서 자리를 하나로 못 박지 않는다.
#: ★ 1차판은 `ROOT/docs` 로 못 박았고, 컨테이너에서 **PNG 는 남는데 인덱스는 못 고치는**
#:   반쪽 상태가 났다. 그 상태가 가장 나쁘다 — 파일과 인덱스가 갈라지고,
#:   갈라진 인덱스는 `verify_screens.py` 가 「어디서 온 화면인지 말하지 않는다」로 잡는다.
def _screens_dir() -> Path:
    for base in (ROOT / "docs", Path("/docs")):
        if (base / "agent" / "evidence" / "D-347" / "screens" / "INDEX.yaml").is_file():
            return base / "agent" / "evidence" / "D-347" / "screens"
    return ROOT / "docs" / "agent" / "evidence" / "D-347" / "screens"


SCREENS = _screens_dir()

#: 무엇을 찍나. `must_see` 는 **그 화면에만 있는 글자**다 — 로그인으로 튕겼는지
#: 빈 껍데기가 떴는지를 이것 하나로 가른다.
TARGETS = [
    {"step": 1, "route": "/dsm/dashboard", "must_see": "관제 대시보드"},
    {"step": 2, "route": "/dsm/events", "must_see": "이벤트 목록"},
    {"step": 3, "route": "/dsm/events/{event_id}", "must_see": "이벤트 상세"},
    # ── D-386 [실측 2026-09-13] 다섯 장을 더한다. 셋은 우리가 만든 화면이고
    #    이 다섯은 **인수받은 화면**이다 — 남의 화면을 여는 것이 값이 큰 이유는
    #    우리가 한 번도 열어 본 적 없는 배선이 거기 있기 때문이다.
    #    `must_see` 는 **실제로 띄워 보고** 그 화면에만 있는 글자로 골랐다(추측 아님).
    {"step": 4, "route": "/device", "must_see": "Add New Device"},
    {"step": 5, "route": "/roles", "must_see": "Add New Role"},
    {"step": 6, "route": "/menu", "must_see": "Menu Management"},
    {"step": 7, "route": "/configuration-management", "must_see": "Is Active?"},
    {"step": 8, "route": "/profile", "must_see": "Personal Information"},
]

#: ★ [실측 2026-09-13 · D-386] 열어 보고 **찍지 못한 화면**. 목록에 남긴다 —
#:   못 찍은 것을 목록에서 지우면 「안 해 본 것」과 「해 봤더니 안 되는 것」이 같아진다.
#:   `/users` 는 API 6건이 전부 200 인 채로 **본문 글자 수가 0** 이었다(빈 화면).
#:   결함으로 등재했다: DA-05/blockers.yaml :: RJCORE_BLANK_ON_NO_PERMISSION
KNOWN_BLANK = [
    {"route": "/users", "why": "본문 0자 · API 6건 200 · JS 오류 0건 — 권한 없는 화면이 "
                               "안내 대신 빈 화면을 낸다 (DA-03 §3-4 위반 · rj-core §0.4)"},
]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def _django():
    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.apps import apps
    return apps


# ---------------------------------------------------------------------------
# 씨앗 — **시험 데이터만.** 빈 화면도 화면이지만, 빈 화면만 찍으면
#        「목록이 그린다」와 「목록이 비어 있다」가 구별되지 않는다 (D-301 의 화면 판).
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 분류 등록부 참조 (D-270 ③) — **주인 없는 행을 만들지 않는다**
# ---------------------------------------------------------------------------
def _assert_owned(label: str, group_id) -> None:
    """이 스크립트가 쓰는 모델이 **소유가 필요한 모델인가**를 등록부에 묻는다.

    ★ 형식적으로 등록부를 import 하는 것이 아니다. 이 스크립트는 시험 데이터를
      심었다가 지우는데, **심는 순간 주인이 없으면** 그 행은 어느 테넌트에도 안 보이거나
      (읽기 격리) 모두에게 보인다(공용 마스터로 오인). 둘 다 나쁘고, 둘의 차이가
      바로 `SHARED_MASTERS` 와 `TENANT_UNASSIGNED` 다.

    등록부가 「공용도 아니고 주인 없음도 아니다」라고 말하면 **group 이 반드시 있어야 한다.**
    """
    sys.path.insert(0, "/app")
    try:
        from tests.tenant_classification import SHARED_MASTERS, TENANT_UNASSIGNED
    except ImportError:                       # 등록부를 못 읽으면 **판정 불가**다
        raise RuntimeError(
            "분류 등록부(tests/tenant_classification.py)를 못 읽었다 — "
            "소유가 필요한지 모르는 채로 쓰지 않는다 (D-270 ③)")
    if label in SHARED_MASTERS or label in TENANT_UNASSIGNED:
        return                                 # 등록부가 「주인 없어도 된다」고 말한다
    if not group_id:
        raise RuntimeError(
            f"{label} 은 등록부에서 공용 마스터도 미배정 선언도 아니다 — "
            f"**소유(group)가 있어야 한다.** 주인 없이 심으면 그 행은 격리 판정에서 "
            f"「공용」과 구별되지 않는다 (D-270 ③)")


def seed_events(username: str, n: int = 2) -> int:
    """★ 씨앗은 **그 계정이 실제로 볼 수 있는 자리**에 심는다.

    1차판은 `group` 없이 심었고, 그래서 세 화면이 전부 「0건」·「404」로 찍혔다 —
    테넌트 좁히기가 **제대로 걸린 결과**다(F-09). 격리를 끄고 찍으면 그것은 고객이 볼
    화면이 아니므로, 끄는 대신 **계정에 소속을 주고 그 소속으로 심는다.**
    격리는 그대로 두고, 보이는 것만 진짜로 만든다.
    """
    apps = _django()
    from django.contrib.auth import get_user_model

    from common.tenant_filters import get_user_group

    U = get_user_model()
    user = U._base_manager.get(username=username)
    # ★ 소속은 `CoreUser` 가 아니라 **프로필 연결**이 들고 있다. 제품이 그렇게 읽으므로
    #   (`common.tenant_filters.get_user_group`) 여기서도 그대로 읽는다 — 두 벌로 읽으면
    #   화면이 보는 소속과 씨앗이 심긴 소속이 갈라진다(D-369).
    group = get_user_group(user)
    if group is None:
        Link = apps.get_model("user", "UserProfileLink")
        Group = apps.get_model("user", "UserGroup")
        group = Group._base_manager.order_by("pk").first()
        if group is None:
            raise RuntimeError("UserGroup 이 한 건도 없다 — 씨앗을 심을 소속이 없다")
        link = getattr(user, "userprofilelink", None)
        if link is None:
            Link._base_manager.create(user=user, group=group)
        else:
            link.group = group
            link.save(update_fields=["group"])
        user.refresh_from_db()
        group = get_user_group(user)
        if group is None:
            raise RuntimeError("소속을 붙였는데도 제품이 읽지 못한다 — 두 경로가 갈라졌다")
    gid = group.pk
    _assert_owned("stream_monitors.StreamMonitor", gid)
    _assert_owned("stream_monitors.DetectionEvent", gid)
    SM = apps.get_model("stream_monitors", "StreamMonitor")
    DE = apps.get_model("stream_monitors", "DetectionEvent")
    monitor, _ = SM._base_manager.get_or_create(
        code=f"{PROBE_TAG}-CAM",
        defaults=dict(name=f"{PROBE_TAG} 캡처용 카메라", ip_source="127.0.0.1",
                      is_active=False, is_visualize=False, order=9998,
                      is_external=False, address_source="",
                      group_id=gid),
    )
    if monitor.group_id != gid:
        monitor.group_id = gid
        monitor.save(update_fields=["group"])
    now = datetime.now(timezone.utc)
    first = None
    for i in range(n):
        e = DE._base_manager.create(
            stream_monitor=monitor, event_type=PROBE_TAG,
            severity=("warning" if i else "critical"),
            occurred_at=now, snapshot_path="", status="new", address_status="pending",
            group_id=gid,
        )
        first = first or e.id
    return first


def clean_events() -> dict:
    apps = _django()
    SM = apps.get_model("stream_monitors", "StreamMonitor")
    DE = apps.get_model("stream_monitors", "DetectionEvent")
    ev = DE._base_manager.filter(event_type=PROBE_TAG)
    n_ev = ev.count()
    ev.delete()
    mon = SM._base_manager.filter(code__startswith=PROBE_TAG)
    n_mon = mon.count()
    mon.delete()
    return {"events": n_ev, "monitors": n_mon}


# ---------------------------------------------------------------------------
# 로그인 — **동시 접속 잠금을 정직하게 푼다**
# ---------------------------------------------------------------------------
def _release_session(username: str) -> None:
    """dj-core 는 `user.token`/`refresh_token`/미소멸 토큰으로 「다른 기기 접속」을 판정한다.

    ★ 그 판정을 **끄지 않는다.** 끄면 제품의 성질이 바뀌고, 그러면 우리가 찍는 화면이
      고객이 볼 화면이 아니게 된다. 여기서는 **이 시험 계정의 흔적만** 지운다.
    """
    apps = _django()
    from django.contrib.auth import get_user_model
    U = get_user_model()
    u = U._base_manager.filter(username=username).first()
    if u is None:
        return
    try:
        from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken
        BlacklistedToken.objects.filter(token__user_id=u.id).delete()
        OutstandingToken.objects.filter(user_id=u.id).delete()
    except Exception as exc:                            # noqa: BLE001
        print(f"[SHOT] 토큰 정리 건너뜀: {type(exc).__name__} {exc}", file=sys.stderr)
    u.token = None
    u.refresh_token = None
    u.save(update_fields=["token", "refresh_token"])
    _ = apps  # django.setup() 만 필요했다


def read_role(username: str) -> str:
    """찍은 사람의 역할을 **제품이 들고 있는 값**에서 읽는다 (D-323).

    ★ 1차판은 `role = "OPERATOR"` 로 박혀 있었다. 바로 위 주석이 「우리가 정해서 적지
      않는다」라고 말하면서 정해서 적고 있었다 — 그리고 그 진술은 **틀렸다**:
      이 계정의 `role` 은 [실측] **None** 이다. 그래서 `/users` 가 빈 화면으로 떴다.
      인덱스에 OPERATOR 라 적혔으면 그 사실이 통째로 가려졌을 것이다.
    """
    apps = _django()
    from django.contrib.auth import get_user_model
    u = get_user_model()._base_manager.filter(username=username).first()
    role = getattr(getattr(u, "role", None), "code", None) or getattr(u, "role", None)
    _ = apps
    return str(role) if role else "NO_ROLE"


def capture(*, web: str, user: str, password: str, event_id: int, role: str,
            api: str) -> dict:
    from playwright.sync_api import sync_playwright

    # ★ 이번 실행이 남길 자리를 **먼저 비운다.** 이벤트 상세의 경로에는 그때그때의
    #   id 가 들어가므로, 비우지 않으면 지난 실행의 PNG 가 남아 인덱스와 어긋난다 —
    #   `verify_screens.py` 는 인덱스에 없는 PNG 를 「어디서 온 화면인지 말하지
    #   않는다」로 실패시킨다. 그 실패는 옳고, **비우는 것이 이쪽의 몫**이다.
    import shutil
    shutil.rmtree(SCREENS / SCENARIO, ignore_errors=True)
    SCREENS.mkdir(parents=True, exist_ok=True)
    entries, steps, page_errors = [], {}, []
    #: 화면이 **실제로 부른** API. 우리가 「이 화면은 이걸 부를 것이다」라고 적지 않는다 —
    #: 브라우저가 부른 것을 그대로 적고, `verify_route_alive.py` 가 그 목록을 때린다(D-386).
    api_calls: dict[str, list] = {}
    seen_calls: list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: page_errors.append(str(e)[:200]))
        page.on("response", lambda r: seen_calls.append(
            (r.request.method, r.url, r.status)))
        try:
            page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(1_500)
            fields = page.locator("input")
            if fields.count() < 2:
                raise RuntimeError("로그인 화면에 입력칸이 둘 미만이다 — 화면이 안 떴다")
            fields.nth(0).fill(user)
            fields.nth(1).fill(password)
            page.get_by_role("button", name="Log In").click()
            page.wait_for_timeout(9_000)
            if page.url.rstrip("/").endswith("/login"):
                raise RuntimeError(
                    f"로그인 뒤에도 로그인 화면이다 ({page.url}) — "
                    f"본문: {page.inner_text('body')[:160]!r}")


            for t in TARGETS:
                route = t["route"].replace("{event_id}", str(event_id))
                seen_calls.clear()
                page.goto(f"{web}{route}", wait_until="networkidle", timeout=60_000)
                page.wait_for_timeout(6_000)
                body = page.inner_text("body")
                if t["must_see"] not in body:
                    raise RuntimeError(
                        f"{route}: 「{t['must_see']}」 가 화면에 없다 — "
                        f"찍지 않는다. 본문: {body[:200]!r}")

                #: ★ [실측 2026-09-13] 1차판은 URL 을 `/api/` 로 잘랐고, 그래서
                #:   **구글 지도**(`maps.googleapis.com/maps/api/js`)가 우리 라우트
                #:   `/api/js` 로 둔갑했다. `verify_route_alive` 가 그 404 를
                #:   「죽은 라우트」로 보고했다 — 죽은 것은 라우트가 아니라 측정이었다(D-350).
                #: ★ 그리고 **질의문자열을 지우지 않는다.** 지우면 필수 인자가 사라져
                #:   살아 있는 라우트가 422 로 나온다 — 같은 종류의 두 번째 오답이었다.
                api_calls[route] = sorted({
                    (m, u[len(api):], st)
                    for m, u, st in seen_calls
                    if u.startswith(api + "/api/")})
                step = f"{SCENARIO}/{t['step']}"
                when = datetime.now().replace(microsecond=0)
                rel = "%s/%s/%s.png" % (SCENARIO, role,
                                        route.strip("/").replace("/", "_") or "root")
                out = SCREENS / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(out))
                steps[step] = when.isoformat()
                entries.append({
                    "route": route, "user_role": role, "scenario": step,
                    "captured_at": when.isoformat(), "file": rel,
                })
                print(f"[SHOT] {rel} — 「{t['must_see']}」 확인 후 캡처")
        finally:
            browser.close()

    return {"entries": entries, "steps": steps, "page_errors": page_errors,
            "api_calls": api_calls}


#: 인덱스의 `screens:` 아래를 **이 실행체가 직접 쓴다.**
#: 사람이 손으로 옮겨 적게 두면 id 하나가 어긋나는 날 인덱스가 거짓말을 한다 —
#: 그리고 그 거짓말은 **고객이 보는 자리**에 실린다 (D-284).
_INDEX_HEAD = """screens:
  # ★ 아래는 `scripts/capture_screens.py` 가 **실행하면서 직접 쓴다.** 손으로 고치지 말 것 —
  #   손으로 옮겨 적으면 이벤트 id 하나가 어긋나는 날 인덱스가 거짓말을 하고,
  #   그 거짓말은 고객이 보는 자리에 실린다 (D-284).
  #
  #   전부 **브라우저가 실제로 지나간 화면**이다. 이 실행체는 화면마다
  #   「그 화면에만 있는 글자」를 먼저 찾고, 못 찾으면 **찍지 않고 실패한다** —
  #   로그인으로 튕긴 뒤 찍은 PNG 도 파일은 생기므로, 「파일이 생겼다」를 성공으로
  #   두면 이 인덱스가 거짓말을 싣게 된다.
  #
  #   ⚠ [실측 2026-09-13 · D-386] 역할은 **`NO_ROLE`** 이다. 이 계정은 제품의 `role` 이
  #     **비어 있다** — 1차판이 `OPERATOR` 라 적어 두었던 자리이고, 그것은 진술이지
  #     실측이 아니었다(D-323). 지금은 제품이 들고 있는 값을 읽어 적는다.
  #     그리고 그 사실이 화면 하나를 설명한다: `/users` 는 **본문 0자**로 떴다.
  #     빈 화면은 찍지 않았고 결함으로 등재했다(RJCORE_BLANK_ON_NO_PERMISSION).
"""


def _rewrite_index(entries: list) -> None:
    index = SCREENS / "INDEX.yaml"
    if not index.is_file():
        print(f"[SHOT] 인덱스가 없다: {index} — 항목을 적지 못했다", file=sys.stderr)
        return
    text = index.read_text(encoding="utf-8")
    head, sep, _ = text.partition("screens:")
    if not sep:
        print("[SHOT] 인덱스에 `screens:` 자리가 없다 — 항목을 적지 못했다", file=sys.stderr)
        return
    row = "\n".join((
        "  - route: {route}",
        "    user_role: {user_role}",
        "    scenario: {scenario}",
        '    captured_at: "{captured_at}"',
        "    file: {file}",
        "",
    ))
    body = "".join(row.format(**e) for e in entries)
    index.write_text(head + _INDEX_HEAD + body, encoding="utf-8")
    print(f"[SHOT] 인덱스 갱신 — {index.name} 에 {len(entries)}장")


def main() -> int:
    ap = argparse.ArgumentParser(description="화면 캡처 실행체 (D-347 · D-384 ②)")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--web", default="http://localhost:3002")
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="씨앗·캡처 없이 두 자리에 닿는지만 본다")
    args = ap.parse_args()

    import urllib.error
    import urllib.request
    for name, url in (("API", args.api + "/api/docs"), ("화면", args.web + "/")):
        try:
            urllib.request.urlopen(url, timeout=15)
        except urllib.error.HTTPError:
            pass                                  # 4xx 도 「서 있다」는 뜻이다
        except Exception as exc:                  # noqa: BLE001
            # ★ 닿지 못한 것은 **닿지 못했다**고 끝낸다. 0장을 통과로 만들지 않는다.
            print(f"[SHOT] {name} 에 닿지 못했다 ({url}): {type(exc).__name__} {exc}")
            print("[SHOT] 판정 불가 — 실행되지 않은 캡처를 성공으로 적지 않는다 (D-301)")
            return EXIT_UNDECIDABLE
    print(f"[SHOT] [입력] API {args.api} · 화면 {args.web} · 대상 {len(TARGETS)}장")
    if args.dry_run:
        print("[SHOT] --dry-run — 두 자리 다 서 있다")
        return EXIT_OK

    _release_session(args.user)
    role = read_role(args.user)
    print(f"[SHOT] 찍는 사람의 역할 = {role} (제품이 들고 있는 값 · D-323)")
    event_id = seed_events(args.user)
    try:
        got = capture(web=args.web, user=args.user, password=args.password,
                      event_id=event_id, role=role, api=args.api)
    finally:
        print(f"[SHOT] 씨앗 정리: {clean_events()}")

    (SCREENS / "run_log.json").write_text(json.dumps({
        "harness": "scripts/capture_screens.py",
        "scenario": SCENARIO,
        "ran_at": datetime.now().replace(microsecond=0).isoformat(),
        "steps": got["steps"],
        #: 브라우저가 뱉은 오류를 **숨기지 않는다.** 0건이면 0건이라고 적힌다.
        "page_errors": got["page_errors"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    routes_out = ROOT / "docs" / "agent" / "evidence" / "D-386" / "screen_routes.json"
    if not routes_out.parent.parent.is_dir():          # 컨테이너에서는 /docs 가 따로다
        routes_out = Path("/docs") / "agent" / "evidence" / "D-386" / "screen_routes.json"
    routes_out.parent.mkdir(parents=True, exist_ok=True)
    routes_out.write_text(json.dumps({
        "source": "scripts/capture_screens.py — 브라우저가 실제로 부른 것",
        "captured_at": datetime.now().replace(microsecond=0).isoformat(),
        "screens": {k: [{"method": m, "path": p, "status": st}
                        for m, p, st in v] for k, v in got["api_calls"].items()},
        "blank_screens": KNOWN_BLANK,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SHOT] 화면이 부른 API 기록: {routes_out}")

    _rewrite_index(got["entries"])
    print(f"[SHOT] {len(got['entries'])}장 · 브라우저 오류 {len(got['page_errors'])}건")
    print(json.dumps(got["entries"], ensure_ascii=False, indent=2))
    return EXIT_OK if len(got["entries"]) == len(TARGETS) else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
