#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""역할 x 전 라우트 판정 — **메뉴 밖 화면이 열리는가, 그 화면의 API 가 자료를 내는가** (P-471 · P-293).

출생 표본 [실측 2026-09-30 · 턴 AR · V · 관제요원 U1 · 8500]
-------------------------------------------------------------
    메뉴(사이드바)는 5줄인데 주소를 치면 10 라우트가 열렸다:
      `/dsm/reports` `/dsm/system` `/dsm/notify` `/roles`            -> 반쪽(셸 + 「권한이 없」)
      `/dsm/people` `/users` `/device` `/report-template`
      `/dsm/cameras/import` `/dsm/team-status`                      -> 거절 없이 열림
    그리고 [실측 2026-10-01 · 같은 계정 · GET] 그 화면들이 부르는 API 중
      `GET /api/v1/user/list` 가 **200 · 사용자 54명 전문**을 냈다(`/users` 의 문).
      `get-user-detail/115` · `stats/by-reviewer` · `webhook-subscriptions` · `metering`
      · `cameras/address-gap` 도 200. 화면이 반쪽인 것이 아니라 **자료가 나갔다.**
    메뉴와 가드가 **두 벌**이었던 것이 뿌리다 — 이제 `roleScreens.json` 한 벌이다.

이 판정기가 보는 것 (모두 같은 출처 `frontend/src/features/nav/roleScreens.json`)
  ① 자기시험      출생 표본 열 라우트가 U1 에게 **안내(닫힘)** 로 판정되고, U1 메뉴 다섯은 열린다
  ② 같은 출처     메뉴 줄은 모두 owners 에 든다 · roleNav.ts 에 손으로 적은 메뉴 줄이 없다
  ③ 가드 배선     App.tsx 가 withRoleGuard 로 사이드바 밑 라우트 전부를 감싼다
  ④ 라우트 전수   App.tsx 의 사이드바 밑 라우트마다 표의 줄을 찾는다(없으면 「플랫폼 운영자」로 센다)
  ⑤ 온보딩 카드   역할 카드가 가리키는 화면은 그 역할이 연다(잠긴 카드 링크 0)
  ⑥ --api         역할 계정 토큰으로 화면의 API 를 **GET 으로만** 불러 본다. 주인이 아닌데(그리고
                   `api_open_to` 로 읽기를 선언하지 않았는데) 2xx 이고 `sensitive` 면 빨강(= 자료 누수). 주인인데 403 이면 「반쪽」 빨강.
  ⑦ --matrix      6 역할 x 전 라우트 표(`docs/agent/evidence/P-293/role_route_matrix.md`)를 쓴다

    python scripts/verify_role_routes.py                 # ①~⑤ (서버 없이)
    python scripts/verify_role_routes.py --self-test     # ①만
    python scripts/verify_role_routes.py --api           # ⑥ (gx-shell 안에서 · 아래 자격은 이름만)
    python scripts/verify_role_routes.py --matrix        # ⑦

⑥ 의 자격: 환경 변수 `GX_SEED_ROLE_PASSWORD`(값은 어디에도 안 적는다) · `GX_API`
(컨테이너 안 기준, 기본 http://gx-nginx-e:8500). 로그인은 `/api/v1/auth/login` +
`end_previous_session: true`, 끝나면 logout(동시 접속 1개). **GET 만 부른다 — 쓰기 0.**

종료 코드: 0 통과 · 1 실패 · 2 못 쟀다(서버·자격 없음)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / "frontend" / "src"
TABLE = FRONT / "features" / "nav" / "roleScreens.json"
MATRIX = ROOT / "docs" / "agent" / "evidence" / "P-293" / "role_route_matrix.md"
MEASURED = ROOT / "docs" / "agent" / "evidence" / "P-293" / "role_route_api_measured.json"

EXIT_OK, EXIT_FAIL, EXIT_GRAY = 0, 1, 2
BS = chr(92)

ROLES = ["U1", "U2", "U3", "U4", "U5", "U6"]
#: 사람 버킷 — 가드가 걸리는 역할. U6 은 U5 계정으로, U3 은 뷰어 계정으로 열린다(계정 겹침).
BUCKETS = ["U1", "U2", "U4", "U5"]
ACCOUNTS = {
    "U1": "gxseed_u1_operator",
    "U2": "gxseed_u2_manager",
    "U4": "gxseed_u4_official",
    "U5": "gxseed_u5_sysop",
}
KIND_OF = {"U1": "operator", "U2": "manager", "U4": "executive", "U5": "admin"}

#: ★ 출생 표본 — P-293 이 적은 관제요원의 메뉴 밖 열 라우트와, 메뉴 안 다섯.
BIRTH_SAMPLE_U1_OUTSIDE = (
    "/dsm/reports", "/dsm/system", "/dsm/notify", "/roles",
    "/dsm/people", "/users", "/device", "/report-template",
    "/dsm/cameras/import", "/dsm/team-status",
)
BIRTH_SAMPLE_U1_MENU = (
    "/dsm/queue", "/dsm/events", "/dsm/cameras/grid", "/handover", "/start",
)

# ══════════════════════════════════════════════════════════════════════════
# 표 읽기 · 판정 (roleNav.ts::routeVerdict 와 **같은 알고리즘** — 같은 JSON 을 읽는다)
# ══════════════════════════════════════════════════════════════════════════


def load_table(path: Path = TABLE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pattern(entry: dict) -> "re.Pattern[str]":
    esc = re.escape(entry["path"])
    esc = re.sub(re.escape(":") + r"[A-Za-z_]+", "[^/]+", esc)
    tail = "(/.*)?" if entry.get("prefix") else ""
    return re.compile("^" + esc + tail + "/?$")


def entry_of(table: dict, pathname: str):
    p = (pathname or "/").split("?")[0].split("#")[0] or "/"
    best, score = None, -1
    for e in table["screens"]:
        if not _pattern(e).match(p):
            continue
        s = (0 if e.get("prefix") else 10000) + len(e["path"])
        if s > score:
            best, score = e, s
    return best


def verdict(table: dict, bucket, pathname: str) -> dict:
    """{allowed, owner_text}. 버킷을 모르면 열린다(모르는 것을 막지 않는다)."""
    if not bucket:
        return {"allowed": True, "owner_text": ""}
    e = entry_of(table, pathname)
    if e and e.get("exempt"):
        return {"allowed": True, "owner_text": ""}
    owners = e["owners"] if e else []
    mine = ["U5", "U6"] if bucket == "U5" else [bucket]
    if any(o in mine for o in owners):
        return {"allowed": True, "owner_text": ""}
    names = table["owner_names"]
    text = " · ".join(names.get(o, o) for o in owners if o not in ("U3", "U6"))
    return {"allowed": False,
            "owner_text": text or (e or {}).get("ownerLabel") or table["default_owner_label"]}


def role_opens(table: dict, role: str, pathname: str) -> bool:
    """표 기준으로 이 역할(U1~U6)이 그 화면의 주인인가 — 매트릭스용(U3·U6 도 센다)."""
    e = entry_of(table, pathname)
    return bool(e) and role in e["owners"]


# ══════════════════════════════════════════════════════════════════════════
# 라우트 전수 — App.tsx 의 사이드바 밑 (소스를 읽는다 · 빌드 없이)
# ══════════════════════════════════════════════════════════════════════════


def strip_comments(src: str) -> str:
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == BS:
                    j += 1
                j += 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


_TOK = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\{|(\{)|(\})|\bpath\s*:\s*(?:'([^']*)'|\"([^\"]*)\"|`([^`]*)`)")


def parse_table(src: str, name: str) -> dict:
    m = re.search(r"(?:export\s+)?const\s+" + re.escape(name) + r"\b[^=]*=\s*\{", src)
    if not m:
        return {}
    stack, depth, res = [], 1, {}
    for t in _TOK.finditer(src, m.end()):
        key, opn, cls, p1, p2, p3 = t.groups()
        if key:
            stack.append(key)
            depth += 1
        elif opn:
            stack.append(None)
            depth += 1
        elif cls:
            depth -= 1
            if depth == 0:
                break
            stack.pop()
        else:
            p = p1 if p1 is not None else (p2 if p2 is not None else p3)
            res[".".join(k for k in stack if k)] = p
    return res


#: rj-core 가 들고 있는 `CustomRouters` — 저장소 밖 패키지라 읽을 수 없다. 실측
#: [2026-10-01 · gx-fe-build:/app/node_modules/rj-core/dist/rj-core.es.js:7185~7225].
RJ_CORE_ROUTERS = {
    "CustomRouters.home.path": "/",
    "CustomRouters.profile.path": "/profile",
    "CustomRouters.menu.path": "/menu",
    "CustomRouters.menu.subRoutes.addMenu.path": "/menu/add",
    "CustomRouters.role.path": "/roles",
    "CustomRouters.config.path": "/configuration-management",
    "CustomRouters.config.subRoutes.editConfig.path": "/configuration-management/edit/:configId",
    "CustomRouters.user.path": "/users",
    "CustomRouters.user.subRoutes.addUser.path": "/users/add",
}


def _tables(front: Path = FRONT) -> dict:
    t = dict(RJ_CORE_ROUTERS)
    t["CustomRoutes.qrCode"] = "/qr-code"
    for prefix, f, name in (
        ("CustomRoutes", "services/API.ts", "CustomRoutes"),
        ("dsm2Routes", "features/dsm/routes.ts", "dsm2Routes"),
        ("dsmU24Routes", "features/dsm/routes.u24.ts", "dsmU24Routes"),
        ("fwsRoutes", "features/fws/routes.ts", "fwsRoutes"),
        ("opsRoutes", "features/ops/routes.ts", "opsRoutes"),
        ("mobileRoutes", "features/mobile/routes.ts", "mobileRoutes"),
    ):
        p = front / f
        if not p.is_file():
            continue
        s = strip_comments(p.read_text(encoding="utf-8"))
        for k, v in parse_table(s, name).items():
            t[prefix + "." + k] = v
    return t


def sidebar_routes(front: Path = FRONT) -> tuple[list[str], int]:
    """(해석된 주소들, 해석 못 한 식 수). 사이드바 element 의 children 배열 안만 본다."""
    app = front / "App.tsx"
    s = strip_comments(app.read_text(encoding="utf-8"))
    i = s.find("<Sidebar />")
    # 라우터 안의 것(함수 안 `<CustomSidebar` 정의가 아니라 `element: <Sidebar />`)
    i = s.find("element: <Sidebar />")
    if i < 0:
        return [], 0
    j = s.index("children:", i)
    k = s.index("[", j)
    d = 0
    e = k
    for e in range(k, len(s)):
        if s[e] == "[":
            d += 1
        elif s[e] == "]":
            d -= 1
            if d == 0:
                break
    body = s[k:e]
    tabs = _tables(front)
    out, bad = [], 0
    for ex in re.findall(r"path:\s*([^,}\n]+?)\s*[,}\n]", body):
        ex = ex.strip()
        if re.match(r"^['\"].*['\"]$", ex):
            out.append(ex.strip("'\""))
            continue
        if ex in tabs:
            out.append(tabs[ex])
        elif ex + ".path" in tabs:
            out.append(tabs[ex + ".path"])
        elif ex.endswith(".path") and ex[:-5] in tabs:
            out.append(tabs[ex[:-5]])
        else:
            bad += 1
    # 중복 제거(순서 유지) · 와일드카드는 라우트가 아니라 「없는 주소」다
    seen, uniq = set(), []
    for p in out:
        if p in seen or p == "*":
            continue
        seen.add(p)
        uniq.append(p)
    return uniq, bad


# ══════════════════════════════════════════════════════════════════════════
# ①~⑤ 정적 판정
# ══════════════════════════════════════════════════════════════════════════


def self_test(table: dict) -> list[str]:
    bad = []
    # 양성: 출생 표본 열 라우트는 U1 에게 닫힌다
    for p in BIRTH_SAMPLE_U1_OUTSIDE:
        v = verdict(table, "U1", p)
        if v["allowed"]:
            bad.append(f"U1 에게 {p} 가 열린다 — 출생 표본이 다시 열렸다(P-293)")
        elif not v["owner_text"]:
            bad.append(f"U1 에게 {p} 가 닫히는데 안내문 주인 이름이 비었다")
    # 음성 대조: 메뉴 안 다섯은 열린다
    for p in BIRTH_SAMPLE_U1_MENU:
        if not verdict(table, "U1", p)["allowed"]:
            bad.append(f"U1 메뉴 {p} 가 닫힌다 — 늘 막는 가드는 가드가 아니라 고장이다")
    # 버킷을 모르면 열린다
    if not verdict(table, None, "/roles")["allowed"]:
        bad.append("버킷을 모르는데 막는다 — 모르는 것을 막으면 빈 화면이 사고가 된다")
    # 표에 없는 주소는 플랫폼 운영자 화면
    v = verdict(table, "U5", "/some-new-inherited-screen")
    if v["allowed"] or v["owner_text"] != table["default_owner_label"]:
        bad.append("표에 없는 주소가 조용히 열린다")
    # 가짜 표본: 메뉴에만 넣고 owners 에 안 넣으면 menu-in-owners 검사가 잡는다
    fake = {"owner_names": table["owner_names"], "default_owner_label": "x",
            "screens": [{"path": "/x", "owners": ["U2"], "menu": {"U1": 0}, "label": "x"}]}
    if not menu_owner_violations(fake):
        bad.append("menu 에만 있고 owners 에 없는 줄을 못 잡는다(자기시험)")
    return bad


def menu_owner_violations(table: dict) -> list[str]:
    out = []
    for e in table["screens"]:
        for b in (e.get("menu") or {}):
            if b not in e["owners"]:
                out.append(f"{e['path']}: 메뉴에 {b} 줄이 있는데 owners 에 {b} 가 없다")
    return out


def static_checks(table: dict, front: Path = FRONT) -> tuple[list[str], list[str]]:
    """(실패 목록, 정보 줄)."""
    bad, info = [], []
    # ② 같은 출처
    bad += menu_owner_violations(table)
    nav = (front / "features" / "nav" / "roleNav.ts")
    if nav.is_file():
        code = strip_comments(nav.read_text(encoding="utf-8"))
        if re.search(r"menuId:\s*\d+", code):
            bad.append("roleNav.ts 에 손으로 적은 메뉴 줄(menuId: 숫자)이 있다 — 메뉴와 가드가 다시 두 벌이다")
        if "roleScreens.json" not in code or "routeVerdict" not in code:
            bad.append("roleNav.ts 가 roleScreens.json 에서 메뉴·가드를 만들지 않는다")
    else:
        bad.append("roleNav.ts 가 없다")
    # ③ 가드 배선
    app = (front / "App.tsx")
    if app.is_file():
        atxt = strip_comments(app.read_text(encoding="utf-8"))
        if "withRoleGuard(<Sidebar />" not in atxt:
            bad.append("App.tsx 가 사이드바 밑 라우트를 withRoleGuard 로 감싸지 않는다")
    wg = front / "features" / "nav" / "withRoleGuard.tsx"
    rg = front / "features" / "nav" / "RoleRouteGuard.tsx"
    if not wg.is_file() or not rg.is_file():
        bad.append("withRoleGuard.tsx / RoleRouteGuard.tsx 가 없다")
    elif "routeVerdict" not in rg.read_text(encoding="utf-8"):
        bad.append("RoleRouteGuard.tsx 가 routeVerdict(표 판정)를 부르지 않는다")
    # ④ 라우트 전수
    routes, unresolved = sidebar_routes(front)
    if not routes:
        bad.append("App.tsx 의 사이드바 밑 라우트를 못 읽었다")
    explicit = [r for r in routes if entry_of(table, r)]
    defaulted = [r for r in routes if not entry_of(table, r)]
    info.append(f"사이드바 밑 라우트 {len(routes)}자리 (해석 못 한 식 {unresolved}) · "
                f"표에 줄 있음 {len(explicit)} · 표에 없어 「플랫폼 운영자」로 셈 {len(defaulted)}")
    # 표의 줄이 App.tsx 에 실제로 서 있는가(유령 줄 금지) — 사이드바 밖 한 줄(/start)은 선언
    outside_ok = {"/start"}
    for e in table["screens"]:
        p = e["path"]
        if p in outside_ok:
            continue
        hit = any(_pattern(e).match(r) for r in routes)
        if not hit and not e.get("note", "").startswith("루트"):
            bad.append(f"표의 {p} 가 App.tsx 사이드바 밑에 없다 — 없는 화면을 가리키는 줄")
    # ⑤ 온보딩 카드 링크
    cards = card_links()
    for role, links in cards.items():
        for link in sorted(links):
            if not role_opens(table, role, link):
                bad.append(f"{role} 온보딩 카드가 가리키는 {link} 를 {role} 이 못 연다 — 잠긴 카드 링크")
    # ⑤b 클릭 걷기 48행(verify_click_completes.py)이 역할마다 여는 화면도 그 역할이 연다
    walk = card_routes_from_click_rows()
    n_walk = 0
    for role, route in walk:
        if route == "/login":      # 로그인 화면은 관문 밖(사이드바 밑이 아니다)
            continue
        n_walk += 1
        probe = route.replace("{event}", "1")
        if role in ("U1", "U2", "U3", "U4", "U5") and not role_opens(table, role, probe):
            bad.append(f"클릭 걷기 {role} 행이 여는 {route} 를 {role} 이 못 연다 — 걷던 화면이 안내로 막힌다")
    info.append(f"클릭 걷기 행 대조: {n_walk}행의 (역할, 화면)")
    info.append("온보딩 카드 링크 대조: " + " · ".join(
        f"{r} {len(v)}" for r, v in sorted(cards.items())))
    return bad, info


def card_routes_from_click_rows() -> list[tuple[str, str]]:
    src = ROOT / "scripts" / "verify_click_completes.py"
    if not src.is_file():
        return []
    txt = src.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r'F\("(U[1-6])#[0-9]+",\s*"[^"]*",\s*"u[1-6]",\s*"(/[^"?]*)', txt):
        out.append((m.group(1), m.group(2)))
    return out


def card_links() -> dict:
    src = ROOT / "backend" / "apps" / "dsm" / "onboarding.py"
    if not src.is_file():
        return {}
    txt = src.read_text(encoding="utf-8")
    m = re.search(r"^CARDS\s*=\s*\{", txt, re.M)
    if not m:
        return {}
    body = txt[m.end():]
    out: dict[str, set] = {}
    cur = None
    for line in body.splitlines():
        h = re.match(r"^    \"(U[1-6])\": \(", line)
        if h:
            cur = h.group(1)
            out[cur] = set()
            continue
        if line.startswith("}"):
            break
        c = re.search(r"Card\(\"[a-z0-9_.]+\",\s*\"[^\"]*\",\s*\"(/[^\"?]*)", line)
        if c and cur:
            out[cur].add(c.group(1))
    return out


# ══════════════════════════════════════════════════════════════════════════
# ⑥ API 실측 (GET 만)
# ══════════════════════════════════════════════════════════════════════════


def _call(base, method, path, body=None, tok=None):
    h = {"Content-Type": "application/json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as f:
            return f.status, f.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode()


def measure(table: dict, base: str, password: str, roles=BUCKETS) -> dict:
    """역할마다 로그인 -> 화면 API GET -> 로그아웃. 값(본문)은 저장하지 않는다 — 상태와 바이트 수만."""
    apis = sorted({e["api"] for e in table["screens"] if e.get("api")})
    res: dict = {"base": base, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "roles": {}}
    for role in roles:
        st, b = _call(base, "POST", "/api/v1/auth/login",
                      {"username": ACCOUNTS[role], "password": password,
                       "end_previous_session": True})
        try:
            user = json.loads(b or b"{}").get("user") or {}
        except ValueError:
            user = {}
        tok = user.get("access_token")
        if not tok:
            res["roles"][role] = {"login": st, "error": "토큰 없음"}
            continue
        rows = {}
        try:
            for api in apis:
                s, body = _call(base, "GET", api, tok=tok)
                inner = None
                try:
                    j = json.loads(body)
                    if isinstance(j, dict) and j.get("status_code") in (401, 403):
                        inner = j["status_code"]
                except ValueError:
                    pass
                rows[api] = {"status": inner or s, "bytes": len(body)}
        finally:
            lo, _ = _call(base, "POST", "/api/v1/auth/logout", {}, tok)
            res["roles"][role] = {"login": st, "logout": lo, "apis": rows}
        time.sleep(2)
    return res


def judge_measured(table: dict, measured: dict) -> tuple[list[str], list[str], list[str]]:
    """(빨강, 노랑, 수정됨-미배포). 빨강: 주인 아닌데 2xx + sensitive · 주인인데 403(반쪽).

    「수정됨-미배포」: 실측은 200 이지만 이번 턴 서버 규칙(`role_gate.judge_surface`)이 그 역할에게
    그 문을 닫는다 — 코드로는 닫혔고(시험 18건) 살아 있는 서버에는 아직 안 올라간 것. 배포 뒤
    `--api` 를 다시 돌려 이 목록이 **0** 이 돼야 닫힌 것이다(그 전에는 닫혔다고 적지 않는다).
    """
    red, yellow, pending = [], [], []
    for role, r in measured.get("roles", {}).items():
        for e in table["screens"]:
            api = e.get("api")
            if not api or api not in r.get("apis", {}):
                continue
            st = r["apis"][api]["status"]
            owner = role_opens(table, role, e["path"]) or (role == "U5" and role_opens(table, "U6", e["path"]))
            declared_read = role in (e.get("api_open_to") or [])
            if owner and st in (401, 403):
                red.append(f"{role} {e['path']}: 주인인데 API {api} 가 {st} — 반쪽 화면")
            if not owner and not declared_read and 200 <= st < 300:
                msg = f"{role} {e['path']}: 주인이 아닌데 API {api} 가 {st}({r['apis'][api]['bytes']}B)"
                if e.get("sensitive") and _predict_closed(api, role):
                    pending.append(msg)
                else:
                    (red if e.get("sensitive") else yellow).append(msg)
    return red, yellow, pending


# ══════════════════════════════════════════════════════════════════════════
# ⑦ 매트릭스
# ══════════════════════════════════════════════════════════════════════════


def _predict_closed(api: str, role: str) -> bool:
    """서버 쪽 P-471 규칙(role_gate.judge_surface)이 이 역할에게 이 API 를 닫는가 — 배포 후 예상."""
    try:
        sys.path.insert(0, str(ROOT / "backend"))
        from django.conf import settings  # noqa: PLC0415
        if not settings.configured:
            settings.configure()
        from common import role_gate  # noqa: PLC0415
        return role_gate.judge_surface(method="GET", path=api.split("?")[0],
                                       kinds={KIND_OF[role]}, user_id=-1) is not None
    except Exception:  # noqa: BLE001
        return False


def build_matrix(table: dict, measured: dict | None, front: Path = FRONT) -> str:
    routes, unresolved = sidebar_routes(front)
    # 사이드바 밖이지만 표에 있는 줄(/start)도 한 줄로 낸다
    for e in table["screens"]:
        if e["path"] == "/start" and "/start" not in routes:
            routes.append("/start")
    names = table["owner_names"]
    L = []
    L.append("# 6 역할 x 전 라우트 — 화면 · API 두 칸 (P-293 · P-471)")
    L.append("")
    L.append("생성: `python scripts/verify_role_routes.py --matrix` · 표 출처 "
             "`frontend/src/features/nav/roleScreens.json` (메뉴와 가드가 같은 출처) · "
             f"라우트 {len(routes)}자리(App.tsx 사이드바 밑 + /start).")
    L.append("")
    L.append("읽는 법")
    L.append("- 화면 칸: `열림` = 그 역할이 표의 주인(가드 통과) · `안내` = 「이 화면은 ○○ 역할 화면입니다」로 통째 막힘.")
    L.append("- API 칸: 8500 에서 그 역할 계정 토큰으로 GET 한 실측 상태. `200→403` = 실측은 200 이었고 "
             "이번 턴 서버 규칙(`role_gate.py` 규칙 ③)이 배포되면 403 이 된다(**미배포 · 시험으로만 확인**). "
             "`-` = 이 화면은 읽는 API 가 없다 · `미측` = 이번에 못 쟀다.")
    L.append("- U3(현장 대원)·U6(외부 연계)는 사람 메뉴 버킷이 없다: U6 은 U5 계정으로, U3 은 뷰어 계정으로 열려서 "
             "가드는 U1·U2·U4·U5 에만 걸린다. 두 열의 화면 칸은 표의 선언이고 **API 는 계정이 없어 못 쟀다**(미측).")
    if measured:
        L.append(f"- 측정 시각 {measured.get('at')} · 대상 {measured.get('base')} · 서버는 **옛 코드**(이번 턴 수정 미배포).")
    L.append("")
    head = "| 화면 주소 | 표 줄 | " + " | ".join(f"{r} {names[r]} 화면 | {r} API" for r in ROLES) + " |"
    L.append(head)
    L.append("|" + "---|" * (2 + 2 * len(ROLES)))
    for rt in routes:
        e = entry_of(table, rt)
        row = [f"`{rt}`", e["path"] if e else "(없음 -> 플랫폼 운영자)"]
        for role in ROLES:
            if e and role in e["owners"]:
                scr = "열림"
            else:
                scr = "안내"
            api = (e or {}).get("api")
            if not api:
                cell = "-"
            elif role in ("U3", "U6") or not measured or role not in measured.get("roles", {}):
                cell = "미측"
            else:
                m = measured["roles"][role].get("apis", {}).get(api)
                if not m:
                    cell = "미측"
                else:
                    cell = str(m["status"])
                    if 200 <= m["status"] < 300 and _predict_closed(api, role):
                        cell += "→403"
            row.append(scr)
            row.append(cell)
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    # 출생 표본 열 라우트 요약
    L.append("## 출생 표본 — 관제요원(U1) 메뉴 밖 열 라우트")
    L.append("")
    L.append("| 화면 | U1 화면 | U1 API (실측) | 서버 규칙 후 |")
    L.append("|---|---|---|---|")
    for p in BIRTH_SAMPLE_U1_OUTSIDE:
        e = entry_of(table, p)
        api = (e or {}).get("api")
        v = verdict(table, "U1", p)
        m = (measured or {}).get("roles", {}).get("U1", {}).get("apis", {}).get(api) if api else None
        meas = str(m["status"]) if m else ("-" if not api else "미측")
        after = "-" if not api else ("403" if (m and (m["status"] in (401, 403) or _predict_closed(api, "U1"))) else meas)
        L.append(f"| `{p}` | {'열림' if v['allowed'] else '안내(' + v['owner_text'] + ')'} | {meas} | {after} |")
    L.append("")
    return "\n".join(L) + "\n"


# ══════════════════════════════════════════════════════════════════════════


def main() -> int:
    ap = argparse.ArgumentParser(description="역할 x 라우트 판정 (P-471 · P-293)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--base", default=os.environ.get("GX_API", "http://gx-nginx-e:8500"))
    ap.add_argument("--table", default=str(TABLE))
    args = ap.parse_args()

    table = load_table(Path(args.table))
    st_bad = self_test(table)
    n_screens = len(table["screens"])
    print(f"[ROLE-ROUTES] [입력] 표 {n_screens}줄 · {args.table} · 출생 표본 {len(BIRTH_SAMPLE_U1_OUTSIDE)}+"
          f"{len(BIRTH_SAMPLE_U1_MENU)}자리")
    if st_bad:
        for b in st_bad:
            print(f"[ROLE-ROUTES] ✗ 자기시험: {b}")
        return EXIT_FAIL
    print("[ROLE-ROUTES] 자기시험 통과 — 열 라우트 닫힘 · 메뉴 다섯 열림 · 모르는 버킷 열림 · 표 밖 닫힘")
    # 음성 시험(판정기가 눈이 있는가): 표를 일부러 망가뜨리면 자기시험이 **빨개져야** 한다.
    broken = json.loads(json.dumps(table))
    for e in broken["screens"]:
        if e["path"] in ("/users", "/roles"):
            e["owners"] = list(e["owners"]) + ["U1"]
    if not self_test(broken):
        print("[ROLE-ROUTES] ✗ 자기시험의 눈이 멀었다 — U1 에게 /users·/roles 를 연 표를 못 잡는다")
        return EXIT_FAIL
    print("[ROLE-ROUTES] 음성 시험 통과 — U1 에게 /users·/roles 를 연 표는 자기시험이 잡는다")
    if args.self_test:
        return EXIT_OK

    bad, info = static_checks(table)
    for line in info:
        print(f"[ROLE-ROUTES]   {line}")

    measured = None
    if MEASURED.is_file():
        try:
            measured = json.loads(MEASURED.read_text(encoding="utf-8"))
        except ValueError:
            measured = None

    rc = EXIT_FAIL if bad else EXIT_OK
    for b in bad:
        print(f"[ROLE-ROUTES] ✗ {b}")

    if args.api:
        pw = os.environ.get("GX_SEED_ROLE_PASSWORD", "")
        if not pw:
            print("[ROLE-ROUTES] GRAY GX_SEED_ROLE_PASSWORD 없음 — 못 쟀다(판정 불가)")
            return EXIT_GRAY
        print(f"[ROLE-ROUTES] [입력] 대상 {args.base} · 역할 {len(BUCKETS)} · 자격 길이 {len(pw)} (값은 안 적는다)")
        measured = measure(table, args.base, pw)
        bad_login = [r for r, v in measured["roles"].items() if "error" in v]
        if bad_login:
            print(f"[ROLE-ROUTES] GRAY 로그인 못 한 역할: {bad_login}")
            return EXIT_GRAY
        MEASURED.parent.mkdir(parents=True, exist_ok=True)
        MEASURED.write_text(json.dumps(measured, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        red, yellow, pending = judge_measured(table, measured)
        for p_ in pending:
            print(f"[ROLE-ROUTES] ! 수정됨-미배포(살아 있는 서버는 아직 200): {p_}")
        for y in yellow:
            print(f"[ROLE-ROUTES] · 노랑(선언된 집계/읽기): {y}")
        for r in red:
            print(f"[ROLE-ROUTES] ✗ 빨강: {r}")
        rc = EXIT_FAIL if (red or bad) else EXIT_OK
    elif measured:
        red, yellow, pending = judge_measured(table, measured)
        print(f"[ROLE-ROUTES] [입력] 저장된 실측 {measured.get('at')} — 빨강 {len(red)} · 노랑 {len(yellow)}"
              f" · 수정됨-미배포 {len(pending)} (재측은 --api; 이 줄은 저장본을 다시 읽은 것)")
        if pending:
            print("[ROLE-ROUTES]   ! 수정됨-미배포는 배포 뒤 --api 재측으로 0 이 돼야 한다")
        if red:
            rc = EXIT_FAIL
        for r in red:
            print(f"[ROLE-ROUTES]   저장본 빨강: {r}")

    if args.matrix:
        MATRIX.parent.mkdir(parents=True, exist_ok=True)
        MATRIX.write_text(build_matrix(table, measured), encoding="utf-8")
        print(f"[ROLE-ROUTES] 매트릭스 -> {MATRIX.relative_to(ROOT)}")

    print("[ROLE-ROUTES] " + ("통과" if rc == EXIT_OK else "실패"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
