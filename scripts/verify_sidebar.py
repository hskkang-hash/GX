#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UX-25 — **관제요원이 사이드바에서 우리 제품에 닿는가.** 네 수를 잰다 (세종 P-61).

    메뉴 정본은 dj-core DB 다 — 코드가 아니라 시드(데이터)로 넣는다(§0.4 무수정).
    이름은 한국어. 순서는 하루에 누르는 횟수 순.
    역할에 없는 메뉴는 **렌더하지 않는다**(비활성 아님) · 관제 역할(U1) 메뉴 **9장 상한**.
        — 세종 P-61 (2026-09-05)

왜 판정기가 따로 있는가 — **심었다와 보인다는 다른 사실이다**
--------------------------------------------------------------
`seed_product_menus` 가 끝에 찍는 수는 **자기가 방금 한 일**(넣은 행 수)이다. 이 판정기는
시드를 부르지 않고 **지금 보이는 것**만 센다. 갈리는 자리가 실제로 셋이나 있다:

  · `RoleMenu` 는 `unique_together=(menu, role)` 이고 이 DB 의 `role_role` 은 **소속을
    갖는다.** 같은 코드의 역할이 소속마다 따로 있으면 연결이 한쪽에만 생긴다 —
    「심었다」는 참인데 그 사람의 사이드바는 비어 있다
  · dj-core `list_menus` 는 **보이는 것에 부모를 얹는다**(`permitted ∪ 부모들`).
    자식만 켜면 **눌러도 아무 데도 안 가는 묶음 마디**가 함께 뜬다
  · 응답 캐시가 낡은 목록을 200 으로 돌려줄 수 있다 — 그러면 DB 는 맞고 화면은 틀리다

재는 것 넷
----------
  ① **역할별 제품 메뉴 행 수**가 표(`common/product_menus.py`)의 기대와 같은가
  ② 사이드바의 줄이 **실재하는 라우트**에 닿는가 (앞판 소스에서 경로를 뽑아 맞댄다)
  ③ **「드론」 같은 낱말과 영문 메뉴명 0건** — 우리가 심은 줄 + U1 사이드바 전체
  ④ **U1 9장 상한** — 관제요원의 사이드바 전체가 아홉 줄을 넘지 않는가

★ 두 눈으로 잰다 — 그리고 **두 눈이 어긋나면 그것이 결함이다**
--------------------------------------------------------------
  ㉠ **링크 표(ORM)**: 역할 코드로 `RoleMenu.permit_read` 를 훑고 부모를 얹는다.
     계정이 없어도 잴 수 있다 — U5(관리자)는 이 저장소에 시드 계정이 없다.
  ㉡ **실제 로그인(HTTP)**: `POST /api/v1/auth/login` → `GET /api/menu/menus`.
     사람이 실제로 보는 것이다. 캐시도 지나고 부모 얹기도 지난다.

  ㉠은 ㉡의 **재현**이다. 재현은 틀릴 수 있으므로 계정이 있는 역할에서는 **둘을 맞댄다.**
  어긋나면 ㉠의 셈이 틀린 것이고, 그 틀림은 U5 의 수를 조용히 거짓말로 만든다(D-369).

    docker exec -w /app -e PYTHONPATH=/app gx-shell python /repo/scripts/verify_sidebar.py
    python scripts/verify_sidebar.py               # 호스트에서 — 컨테이너로 위임한다
    python scripts/verify_sidebar.py --self-test   # 판정 규칙만 (Django 없이)

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(환경 없음). 회색은 초록이 아니다.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 표는 **여기 없다** — `backend/common/product_menus.py` 한 곳이다 (D-369)
#   그 모듈은 Django 없이도 읽히도록 지어져 있다(역할 코드는 함수 안에서 늦게 읽는다).
#   못 읽었을 때만 아래 그물을 쓴다 — 그물로 잰 것은 **그렇게 말한다.**
# ═══════════════════════════════════════════════════════════════════════════
FALLBACK_EXPECT = {"U1": 5, "U2": 7, "U4": 2, "U5": 3}
FALLBACK_CAP = 9

#: U1 상한. P-61 이 정한 수다.
U1_MENU_CAP = 9

#: 사이드바 이름에 **없어야 하는 낱말**. 관제 제품의 말이 아니다.
#: ★ 「드론 같은 낱말」이 무엇인지 판정기가 정하지 않는다 — 이 표가 곧 그 정의다.
#:   늘 때마다 사람이 여기를 고친다. 정규식으로 뭉뚱그리면 「무엇이 걸렸나」를 못 읽는다.
FORBIDDEN_WORDS = (
    "드론", "무인기", "기체", "항공", "비행", "관제국",
    "배송", "적재함", "물류", "택배", "배달",
)

#: 한글이 한 자라도 있는가. 없으면 **영문 메뉴명**이다.
HANGUL = re.compile(r"[가-힣]")


def load_table():
    """표를 읽는다. 돌려주는 것은 (기대수, 줄들, 사유). 사유가 있으면 **그물로 쟀다**."""
    for candidate in ("/app", str(ROOT / "backend")):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
    try:
        from common.product_menus import PRODUCT_MENUS, expected_counts
        return dict(expected_counts()), tuple(PRODUCT_MENUS), None
    except Exception as exc:                                  # noqa: BLE001
        return dict(FALLBACK_EXPECT), (), "표를 못 읽었다(%s) — 그물값으로 잰다" % type(exc).__name__


# ═══════════════════════════════════════════════════════════════════════════
# 앞판 라우트 — **경로가 실재하는가**는 앞판 소스가 정본이다
# ═══════════════════════════════════════════════════════════════════════════
#: 라우트 문자열이 사는 파일들. 여기 밖에서 라우트를 정하지 않는 것이 이 저장소의 규약이다
#: (`features/dsm/routes.ts` 머리말 · `features/mobile/routes.ts` 도 같은 판단).
ROUTE_SOURCES = (
    "frontend/src/App.tsx",
    "frontend/src/services/API.ts",
    "frontend/src/features/dsm/routes.ts",
    "frontend/src/features/mobile/routes.ts",
)

#: `path: '/dsm/queue'` 꼴. 변수 조각(`:id`)이 든 것은 그대로 둔다 — 맞댈 때 접두로 본다.
_PATH_LITERAL = re.compile(r"path:\s*'([^']+)'")


def known_routes(root: Path = ROOT) -> set[str]:
    """앞판이 실제로 등록하는 경로들. **못 읽으면 빈 집합**이고, 빈 집합은 판정 불가다."""
    found: set[str] = set()
    for rel in ROUTE_SOURCES:
        f = root / rel
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in _PATH_LITERAL.finditer(text):
            p = m.group(1).strip()
            if p.startswith("/"):
                found.add(p)
    return found


def route_exists(path: str, routes: set[str]) -> bool:
    """이 경로에 갈 데가 있는가.

    ★ 변수 조각을 **접두로 흡수하지 않는다.** `/dsm/events/:id` 가 있다고 해서
      `/dsm/events/queue` 가 사는 것은 아니다 — 라우트 삼킴은 이 저장소가 이미
      한 번 만난 함정이다(`features/dsm/routes.ts` 의 ⚠).
    """
    return path in routes


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 함수로 떼어 둔 이유는 **시험하기 위해서다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(found: dict, expect: dict) -> list[tuple[str, bool, str]]:
    """`found` 는 「지금 보이는 것」. `None` 은 **못 쟀다**이지 0 이 아니다 (D-301)."""
    out: list[tuple[str, bool, str]] = []

    by_role = found.get("by_role")
    if by_role is None:
        return [("제품 메뉴 행", False, "**못 쟀다** — DB 에 닿지 못했다"),
                ("라우트 실재", False, "못 쟀다"),
                ("우리 대장의 말", False, "못 쟀다"),
                ("U1 상한", False, "못 쟀다"),
                ("두 눈 대조", False, "못 쟀다")]

    # ── ① 역할별 제품 메뉴 행 수 ────────────────────────────────────────
    bad = []
    for key in sorted(expect):
        got = by_role.get(key, {}).get("product")
        if got is None:
            bad.append("%s 못 쟀다" % key)
        elif got != expect[key]:
            bad.append("%s %d줄 (기대 %d)" % (key, got, expect[key]))
    out.append(("제품 메뉴 행", not bad,
                "; ".join(bad) or " · ".join("%s %d줄" % (k, by_role[k]["product"])
                                             for k in sorted(expect))))

    # ── ② 라우트 실재 ───────────────────────────────────────────────────
    dead = found.get("dead_links")
    if dead is None:
        out.append(("라우트 실재", False, "못 쟀다 — 앞판 소스를 못 읽었다"))
    else:
        out.append(("라우트 실재", not dead,
                    "닿지 않는 줄: %s" % "; ".join(dead) if dead
                    else "우리가 심은 줄 전부가 실재 라우트에 닿는다"))

    # ── ③ 우리 대장의 말 — 금지 낱말 · 영문 메뉴명 ──────────────────────
    words = found.get("forbidden")
    english = found.get("english")
    if words is None or english is None:
        out.append(("우리 대장의 말", False, "못 쟀다"))
    else:
        why = []
        if words:
            why.append("금지 낱말 %d건: %s" % (len(words), "; ".join(words)))
        if english:
            why.append("영문 메뉴명 %d건: %s" % (len(english), "; ".join(english)))
        out.append(("우리 대장의 말", not why, " / ".join(why) or "금지 낱말 0건 · 영문 메뉴명 0건"))

    # ── ④ U1 상한 ───────────────────────────────────────────────────────
    total = by_role.get("U1", {}).get("total")
    if total is None:
        out.append(("U1 상한", False, "못 쟀다"))
    else:
        out.append(("U1 상한", total <= U1_MENU_CAP,
                    "관제요원 사이드바 %d줄 (상한 %d)" % (total, U1_MENU_CAP)))

    # ── ⑤ 두 눈 대조 — 링크 표(ORM)와 실제 로그인(HTTP)이 같은 말을 하는가 ──
    #    ★ 이것이 없으면 U5 의 수는 **아무도 확인하지 않은 재현**이다.
    mismatch = found.get("eye_mismatch")
    checked = found.get("eyes_checked")
    if mismatch is None:
        out.append(("두 눈 대조", False, "못 쟀다 — 로그인으로 재지 못했다"))
    elif not checked:
        out.append(("두 눈 대조", False,
                    "**한 눈으로만 쟀다** — 로그인한 역할이 0개다. 링크 표의 재현이 "
                    "맞는지 아무도 확인하지 않았다"))
    else:
        out.append(("두 눈 대조", not mismatch,
                    "어긋난 역할: %s" % "; ".join(mismatch) if mismatch
                    else "역할 %d개에서 링크 표와 실제 로그인이 같다" % len(checked)))

    return out


# ═══════════════════════════════════════════════════════════════════════════
# 수집 — Django 와 (있으면) 로그인
# ═══════════════════════════════════════════════════════════════════════════
#: 로그인해서 잴 수 있는 사람. `seed_role_users` 가 심은 넷이다.
#:
#: ★ [2026-09-06 · 턴 G] **U5 가 여기 들어왔다.** 그전까지 U5(관리자)만 시드 계정이
#:   없어서 링크 표(ORM 재현)로만 쟀고, 판정 ⑤(두 눈 대조)는 셋에서만 돌았다 —
#:   즉 **U5 의 70줄은 아무도 눈으로 본 적 없는 수**였다. 재현은 틀릴 수 있고,
#:   틀린 재현은 조용히 거짓말을 한다(이 파일 머리말의 그 이유 그대로).
HTTP_ACCOUNTS = {
    "U1": "gxseed_u1_operator",
    "U2": "gxseed_u2_manager",
    "U4": "gxseed_u4_official",
    "U5": "gxseed_u5_sysop",
}


def _visible_menu_ids(role_codes) -> tuple[set, dict]:
    """링크 표로 재는 눈 ㉠ — `permitted ∪ 부모들`.

    ★ dj-core `list_menus` 의 셈을 **재현한다.** 재현이라는 것을 숨기지 않는다:
      맞는지는 눈 ㉡(실제 로그인)이 확인하고, 어긋나면 판정 ⑤가 빨강이다.
    """
    from core.menu.models import Menu, RoleMenu

    permitted = set(
        RoleMenu._base_manager.filter(
            role__code__in=list(role_codes), permit_read=True, deleted__isnull=True
        ).values_list("menu_id", flat=True)
    )
    rows = {m.pk: m for m in Menu._base_manager.filter(deleted__isnull=True)}
    permitted = {i for i in permitted if i in rows}
    visible = set(permitted)
    for i in list(permitted):
        seen, cur = set(), rows[i].parent_id
        while cur and cur not in seen and cur in rows:
            seen.add(cur)
            visible.add(cur)
            cur = rows[cur].parent_id
    return visible, rows


def _http_paths(api: str, username: str, password: str):
    """눈 ㉡ — 실제로 로그인해서 사이드바를 받는다. 돌려주는 것은 (경로,이름) 목록."""
    import json
    import urllib.request

    from verify_route_alive import login  # 로그인 문을 두 벌 두지 않는다 (D-369)

    token = login(api, username, password)
    if not token:
        return None
    req = urllib.request.Request(
        api + "/api/menu/menus?page_size=500",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:                                         # noqa: BLE001
        return None
    out: list[tuple[str, str]] = []

    def walk(items):
        for it in items or []:
            out.append((it.get("path") or "", it.get("menu_name") or ""))
            walk(it.get("children"))

    walk(body.get("menus"))
    return out


def collect(api: str | None, password: str | None) -> tuple[dict, dict, str | None]:
    expect, table, table_why = load_table()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    #: 컨테이너는 `/repo` 와 `/app`(=backend) 을 **따로** 마운트한다 —
    #: `/repo` 에서 부르면 `config` 가 이름 공간에 없다(`verify_seed_roles` 와 같은 줄).
    for candidate in ("/app", str(ROOT / "backend")):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
    try:
        import django
        django.setup()
    except Exception as exc:                                  # noqa: BLE001
        return {}, expect, "Django 를 못 세웠다: %s: %s" % (type(exc).__name__, exc)

    if not table:
        return {}, expect, "제품 메뉴 표를 못 읽었다 — 무엇을 기대할지 모른다"

    found: dict = {"table_why": table_why}
    try:
        from common.product_menus import role_codes_for
        from core.menu.models import Menu

        # 우리가 심은 줄의 행 id — 열쇠는 (경로, 이름) 쌍이다(시드와 같은 눈)
        ours: dict = {}
        for row in table:
            m = Menu._base_manager.filter(
                path=row["path"], menu_name=row["name"], deleted__isnull=True
            ).order_by("id").first()
            if m is not None:
                ours[m.pk] = row

        # ★ **역할 코드마다 따로 잰다.** 묶음(U1)의 합집합으로 재면 안 된다 —
        #   사람은 묶음이 아니라 **역할 하나**로 로그인하고, 상한은 그 사람의 화면에
        #   걸린다. [실측 2026-09-05] U1 안에서도 `fire_user` 5줄 · `operator` 19줄로
        #   갈렸다. 합집합으로 쟀으면 두 수가 하나로 뭉개져 아무것도 안 보였을 것이다.
        by_role: dict = {}
        for key in sorted(expect):
            per_code = {}
            all_names: set = set()
            for code in role_codes_for(key):
                visible, rows = _visible_menu_ids([code])
                per_code[code] = {
                    "total": len(visible),
                    "product": len(visible & set(ours)),
                }
                all_names |= {(rows[i].menu_name or "") for i in visible}
            by_role[key] = {
                "per_code": per_code,
                #: 상한은 **가장 넓은 역할**에 걸린다 — 최댓값으로 잰다.
                "total": max((v["total"] for v in per_code.values()), default=0),
                #: 제품 행은 **가장 좁은 역할**로 잰다 — 한 역할에만 안 붙어도 결함이다.
                "product": min((v["product"] for v in per_code.values()), default=0),
                "names": sorted(all_names),
            }
        found["by_role"] = by_role
        found["seeded"] = len(ours)
        found["missing_rows"] = [r["name"] for r in table
                                 if r["path"] not in {v["path"] for v in ours.values()}]

        # ── ② 라우트 실재 — 우리가 심은 줄만 판정한다 ────────────────────
        routes = known_routes()
        if not routes:
            found["dead_links"] = None
        else:
            found["dead_links"] = [
                "%s → %s" % (r["name"], r["path"])
                for r in table if not route_exists(r["path"], routes)]
        found["route_count"] = len(routes)

        # ── ③ 말 — 우리가 심은 줄 전부 + U1 사이드바 전체 ────────────────
        checked_names = [(r["name"], "표") for r in table]
        checked_names += [(n, "U1 사이드바") for n in by_role.get("U1", {}).get("names", [])]
        found["forbidden"] = sorted({
            "%s(%s)" % (n, where) for n, where in checked_names
            for w in FORBIDDEN_WORDS if w in n})
        found["english"] = sorted({
            "%s(%s)" % (n, where) for n, where in checked_names if not HANGUL.search(n)})

        # ── ⑤ 두 눈 대조 ────────────────────────────────────────────────
        mismatch, checked = [], []
        if api and password:
            for key, username in HTTP_ACCOUNTS.items():
                if key not in expect:
                    continue
                seen = _http_paths(api, username, password)
                if seen is None:
                    continue
                checked.append(key)
                http_total = len(seen)
                http_product = sum(1 for p, n in seen
                                   if any(p == r["path"] and n == r["name"] for r in table))
                # ★ 이 사람이 **실제로 가진 역할**로 재현한다. 묶음 전체로 맞대면
                #   「계정이 한 역할만 가졌다」는 사실이 어긋남으로 잡혀서, 진짜 어긋남을
                #   덮는다 — 판정기가 늑대를 외치면 다음 늑대는 아무도 안 본다.
                from django.contrib.auth import get_user_model
                user = get_user_model()._base_manager.filter(username=username).first()
                his_codes = sorted(r.code for r in user.roles.all()) if user else []
                mine, _rows = _visible_menu_ids(his_codes) if his_codes else (set(), {})
                orm_total, orm_product = len(mine), len(mine & set(ours))
                if http_total != orm_total or http_product != orm_product:
                    mismatch.append(
                        "%s(%s) 링크표 %d줄(제품 %d) ≠ 로그인 %d줄(제품 %d)"
                        % (key, "·".join(his_codes) or "역할 0개",
                           orm_total, orm_product, http_total, http_product))
                by_role[key]["http_total"] = http_total
                by_role[key]["http_product"] = http_product
                by_role[key]["http_codes"] = his_codes
            found["eye_mismatch"] = mismatch
            found["eyes_checked"] = checked
        else:
            found["eye_mismatch"] = None
            found["eyes_checked"] = None
    except Exception as exc:                                  # noqa: BLE001
        return found, expect, "DB 를 읽다 죽었다: %s: %s" % (type(exc).__name__, exc)
    return found, expect, None


# ═══════════════════════════════════════════════════════════════════════════
# 자기 시험 — **판정기도 시험받는다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    """양성·음성 표본으로 판정 규칙만 시험한다. Django 도 DB 도 없이 돈다.

    ★ **출생 표본** (D-310) — 이 판정기를 만들게 한 사례는 합성이 아니다.
      [실측 2026-09-05 · 턴 F 착수 전 · 실제 로그인] `gxseed_u1_operator` 의 사이드바
      **12줄 · 제품 화면 0장**. 12줄은 정찰 임무 · GaionGCS · 정찰거점 · 적재함 ·
      장치 구성 템플릿 · 항로 및 경로 · 체크리스트 설정 · 관리자 설정과 묶음 마디 넷이다.
      ★ 그 상태가 **아무 시험도 안 보고 있던 것**이 이 도구를 만든 이유다:
        화면은 있었고 라우트도 살아 있었다. 없는 것은 **거기로 가는 줄**이었다.
    """
    ok = True
    expect = {"U1": 5, "U2": 7, "U4": 2, "U5": 3}

    # ── 출생 표본 — 제품 0장 · 인수 자산 12줄. **초록이면 안 된다** ────────
    birth = {
        "by_role": {"U1": {"total": 12, "product": 0, "names": ["Mission", "GaionGCS"]},
                    "U2": {"total": 14, "product": 0, "names": []},
                    "U4": {"total": 24, "product": 0, "names": []},
                    "U5": {"total": 10, "product": 0, "names": []}},
        "dead_links": [], "forbidden": [], "english": ["Mission(U1 사이드바)"],
        "eye_mismatch": [], "eyes_checked": ["U1"],
    }
    r = judge(birth, expect)
    #: 그날 갈린 것은 **제품 행 수**와 **영문 이름**과 **상한**이다. 「전부 빨강」으로 재면
    #: 이 표본은 「아무것도 못 쟀다」와 같은 것을 재게 되고, 그러면 출생 표본이 아니다.
    ok &= [p for _, p, _ in r] == [False, True, False, False, True]

    # 아무것도 못 쟀다 → 다섯 다 실패이고, 「0건」이 아니라 「못 쟀다」로 말해야 한다
    r = judge({}, expect)
    ok &= all(not p for _, p, _ in r) and "못 쟀다" in r[0][2]

    # ── 온전 표본 — 지금 닫힌 모양 ────────────────────────────────────────
    good = {
        "by_role": {"U1": {"total": 5, "product": 5,
                           "names": ["지금 처리할 것", "무슨 일 있었나", "카메라 격자",
                                     "인계 메모", "처음이세요"]},
                    "U2": {"total": 21, "product": 7, "names": []},
                    "U4": {"total": 26, "product": 2, "names": []},
                    "U5": {"total": 12, "product": 3, "names": []}},
        "dead_links": [], "forbidden": [], "english": [],
        "eye_mismatch": [], "eyes_checked": ["U1", "U2", "U4"],
    }
    r = judge(good, expect)
    ok &= all(p for _, p, _ in r)

    # ── 음성 표본 ①: 심었는데 **한 역할에만 안 붙었다** ───────────────────
    #   역할이 소속을 갖는 이 DB 에서 가장 그럴듯한 고장이다.
    half = {**good, "by_role": {**good["by_role"],
                                "U5": {"total": 12, "product": 0, "names": []}}}
    r = judge(half, expect)
    ok &= [p for _, p, _ in r] == [False, True, True, True, True]

    # ── 음성 표본 ②: **눌러도 아무 데도 안 가는 줄** ─────────────────────
    #   「Media Viewer」에서 실제로 만난 고장. 행은 있고 라우트가 없다.
    dead = {**good, "dead_links": ["감사 기록 → /dsm/audit"]}
    r = judge(dead, expect)
    ok &= [p for _, p, _ in r] == [True, False, True, True, True]

    # ── 음성 표본 ③: 드론 낱말이 되돌아왔다 ──────────────────────────────
    drone = {**good, "forbidden": ["드론 및 로봇(U1 사이드바)"]}
    r = judge(drone, expect)
    ok &= [p for _, p, _ in r] == [True, True, False, True, True]

    # ── 음성 표본 ④: 영문 메뉴명 ─────────────────────────────────────────
    eng = {**good, "english": ["Delivery Settings(U1 사이드바)"]}
    r = judge(eng, expect)
    ok &= [p for _, p, _ in r] == [True, True, False, True, True]

    # ── 음성 표본 ⑤: 상한을 넘었다 (시드는 됐는데 인수 자산이 안 끊겼다) ──
    over = {**good, "by_role": {**good["by_role"],
                                "U1": {**good["by_role"]["U1"], "total": 17}}}
    r = judge(over, expect)
    ok &= [p for _, p, _ in r] == [True, True, True, False, True]

    # ── 음성 표본 ⑥: **두 눈이 어긋났다** — 링크 표의 재현이 틀린 날 ──────
    #   이것이 빨강이 아니면 U5 의 수는 아무도 확인하지 않은 추측이 된다.
    squint = {**good, "eye_mismatch": ["U1 링크표 5줄(제품 5) ≠ 로그인 12줄(제품 0)"]}
    r = judge(squint, expect)
    ok &= [p for _, p, _ in r] == [True, True, True, True, False]

    # ── 음성 표본 ⑦: **한 눈으로만 쟀다** — 회색은 초록이 아니다 ──────────
    one_eye = {**good, "eye_mismatch": [], "eyes_checked": []}
    r = judge(one_eye, expect)
    ok &= [p for _, p, _ in r] == [True, True, True, True, False]

    # ── 라우트 판정 자체 — 변수 조각이 리터럴을 **삼키지 않는가** ─────────
    routes = {"/dsm/events", "/dsm/events/:id", "/dsm/queue"}
    ok &= route_exists("/dsm/queue", routes)
    ok &= route_exists("/dsm/events", routes)
    ok &= not route_exists("/dsm/events/queue", routes)   # 삼킴 금지
    ok &= not route_exists("/dsm/audit", routes)

    # ── 말 판정 자체 ─────────────────────────────────────────────────────
    ok &= bool(HANGUL.search("카메라 격자")) and not HANGUL.search("Delivery Settings")
    ok &= any(w in "드론 및 로봇" for w in FORBIDDEN_WORDS)
    ok &= not any(w in "지금 처리할 것" for w in FORBIDDEN_WORDS)

    print("self-test: %s" % ("통과" if ok else "실패"))
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    from verify_route_alive import delegate_to_container, load_local_env  # 두 벌을 안 둔다

    env_files = load_local_env()
    ap = argparse.ArgumentParser(description="사이드바에 제품이 있나 (UX-25 · P-61)")
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--password", default=os.environ.get("GX_SEED_ROLE_PASSWORD"),
                    help="시드 역할 계정 공용 비밀번호(저장소 밖 .env.gates)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        print("판정 불가(exit 2): **판정기 자신이 자기 시험에 떨어졌다.**")
        return EXIT_UNDECIDABLE

    #: 서버도 DB 도 컨테이너 안에 있다 — 호스트에서 부르면 스스로를 안으로 보낸다.
    container = os.environ.get("GX_ROUTE_CONTAINER", "").strip()
    if container and not os.environ.get("GX_ROUTE_IN_CONTAINER"):
        os.environ.setdefault("GX_API", "http://localhost:8000")
        if args.password:
            os.environ["GX_SEED_ROLE_PASSWORD"] = args.password
        return delegate_to_container(container, None, script="verify_sidebar.py")

    found, expect, why = collect(args.api, args.password)
    if why:
        print("판정 불가(exit 2): %s" % why)
        print("  회색은 초록이 아니다 — 못 잰 것을 통과로 적지 않는다.")
        return EXIT_UNDECIDABLE

    if env_files:
        print("[verify_sidebar] 자격증명: %s (저장소 밖)" % ", ".join(env_files))
    if found.get("table_why"):
        print("[verify_sidebar] ⚠ %s" % found["table_why"])
    print("[verify_sidebar] 심긴 제품 메뉴 행 %d개 · 앞판 라우트 %d개를 읽었다"
          % (found.get("seeded", 0), found.get("route_count", 0)))

    rows = judge(found, expect)
    for name, passed, why2 in rows:
        print("  %s %-12s %s" % ("OK  " if passed else "FAIL", name, why2))

    # ── 판정하지 않고 **세는** 줄들 ──────────────────────────────────────
    by_role = found.get("by_role") or {}
    for key in sorted(by_role):
        r = by_role[key]
        extra = ""
        if "http_total" in r:
            extra = " · %s 로 로그인하면 %d줄(제품 %d)" % (
                "·".join(r.get("http_codes") or []) or "?", r["http_total"], r["http_product"])
        print("  [실측] %s 사이드바 최대 %d줄 (제품 최소 %d줄)%s"
              % (key, r["total"], r["product"], extra))
        for code, v in sorted((r.get("per_code") or {}).items()):
            print("         · %-24s %2d줄 (제품 %d)" % (code, v["total"], v["product"]))
    missing = found.get("missing_rows")
    if missing:
        print("  [실측] 표에는 있는데 **DB 에 아직 없는** 줄: %s" % ", ".join(missing))
        print("         — `python manage.py seed_product_menus` 를 돌리지 않았다.")
    if found.get("eyes_checked") is not None and len(found["eyes_checked"]) < len(HTTP_ACCOUNTS):
        print("  [실측] 로그인으로 재지 못한 역할이 있다 — U5(관리자)는 이 저장소에 "
              "시드 계정이 없다. 그 수는 **링크 표의 재현**이다.")

    #: ★ [차선 S 실측 2026-09-06 · 턴 I] **「못 쟀다」를 빨강으로 내고 있었다.**
    #:   로그인이 안 되면 다섯 칸이 전부 실패로 채워지고 그대로 exit 1 이 됐다 —
    #:   같은 시각대에 색이 흔들렸고, 그 빨강은 제품이 아니라 환경의 사실이었다(P-70).
    #:   순서는 **빨강이 회색을 이긴다**: 진짜 실패가 하나라도 있으면 빨강이고,
    #:   실패가 전부 「못 쟀다」일 때만 회색이다. 회색은 초록이 아니다(D-301).
    failed = [(k, why) for k, ok, why in rows if not ok]
    if not failed:
        return EXIT_OK
    unmeasured = [k for k, why in failed if "못 쟀다" in (why or "")]
    if len(unmeasured) == len(failed):
        print("  **판정 불가(회색)** — 실패한 %d칸이 전부 「못 쟀다」다 (%s). "
              "환경의 사실이지 제품의 빨강이 아니다 (P-70)"
              % (len(failed), ", ".join(unmeasured)))
        return EXIT_UNDECIDABLE
    return EXIT_FAIL


if __name__ == "__main__":
    from _gate_header import gate_header, roles_of  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target=os.environ.get("GX_API", "http://localhost:8000") + " (gx-shell 안 · 호스트에 포트가 없다)",
        as_="시드 역할 계정 " + "/".join(sorted(HTTP_ACCOUNTS.values())) + " · " + " · ".join(roles_of(u) for u in sorted(HTTP_ACCOUNTS.values())) + " · 자격 이름 GX_SEED_ROLE_PASSWORD (값 아님)",
        source="살아 있는 서버 응답 (HTTP) + gx-shell ORM 대조",
        reason="메뉴는 역할마다 다르다 — 한 계정으로 재면 다른 역할의 메뉴는 안 재진다",
    )
    raise SystemExit(main())
