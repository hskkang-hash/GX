# -*- coding: utf-8 -*-
"""턴 X · 차선 U56 — **API-03·04 잔여: 범위 이름은 넷인데 닿는 문은 둘이다.**

캐시 처리: 이 시험은 HTTP 를 타지 않는다 — 소스를 **AST 로 읽는 정적 검사**라
  응답 캐시가 낄 자리가 없다(D-341 의 `NO_CACHE` 가 필요 없는 갈래). 그 대신
  「읽은 파일 수」를 함께 세어 **못 읽어서 통과**하는 초록을 막는다.

무엇을 재는가 — **「발급된다」와 「어디론가 간다」는 다른 사실이다**
--------------------------------------------------------------------
`kernels/k5_trust/key_scopes.py` 는 범위 이름 **넷**을 정본으로 들고 있고
(`events:read` · `pulse:read` · `stats:read` · `webhooks:manage`),
`PATH_SCOPES` 는 그 이름을 경로 접두에 **다섯 줄**로 맺는다.

그런데 범위 판정(`assert_path_scope`)은 **키가 그 문을 통과한 뒤**에 돈다. 문이
`inbound_key=True` 를 선언하지 않으면 키는 범위를 따지기도 전에 **401** 로 끝난다.
⇒ 그 접두에 맺힌 범위 이름은 **발급은 되는데 갈 수 있는 문이 0개**다.
   발급자는 「줬다」고 믿고 상대는 못 쓴다 — 그것이 **조용히 갈리는 자리**다.

[실측 2026-09-20 · 턴 X] `inbound_key=True` 를 선언한 라우트는 저장소 전체에서 **둘**:

    apps/dsm/api.py:188   GET /api/dsm/events          → events:read
    apps/dsm/api.py:1388  GET /api/dsm/cameras/pulse   → pulse:read   ← **턴 X 에 U3 가 열었다**

남은 둘은 아직 닿지 않는다:

    stats:read       `/api/dsm/stats/*` **아홉** 문이 전부 `JwtOrInboundKey()` 기본값
                     (턴 W 엔 여덟이었다 — **한계가 줄지 않고 늘었다**). 소유: U24
    webhooks:manage  `/api/dsm/webhook-subscriptions`(api.py) ·
                     `/api/dsm/settings/webhook-subscriptions/*`(api_u56.py) 전부 기본값

★ **이 차선이 문을 열지 않았다.** `inbound_key=True` 는 「사유 한 줄」을 요구하는
  **개방 결정**이고, `stats/*` 는 U24 파일이다(한 파일은 한 차선). 쓰기 메서드에는
  줄 수조차 없다. 여는 것은 소유 차선의 판단이고 이 시험은 **그 수를 지킬 뿐**이다.

★ 이 시험이 빨개지면 — **좋은 일일 수도 있다.** 문이 늘었다면 명세
  `docs/design/GX-API_연계명세_v0.1.md` §3 을 **같은 변경에서** 갱신하고 아래
  `REACHABLE` 를 고쳐라. 고치지 않고 두면 명세가 조용히 거짓이 된다.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

#: 지금 **키에게 열려 있는** 문과 그 범위. 늘거나 줄면 이 시험이 먼저 말한다.
#: ⚠ 열쇠는 `@route.get("…")` 에 **적힌 그 글자**다 — 라우터가 앞에 `/api/dsm` 을
#:   붙이므로 `PATH_SCOPES`(`key_scopes.py`)의 전체 경로와 **모양이 다르다.**
#:   전체 경로로 적으면 이 시험은 언제나 빨갛고, 그 빨강은 제품이 아니라 이 파일의
#:   실수다. 그래서 둘을 한 칸에 두지 않고 **선언 글자 ↔ 전체 경로**를 같이 적는다.
ROUTER_PREFIX = "/api/dsm"
REACHABLE = {
    "/events": ("events:read", ROUTER_PREFIX + "/events"),
    "/cameras/pulse": ("pulse:read", ROUTER_PREFIX + "/cameras/pulse"),
}

#: 훑는 자리. 라우트 선언이 사는 파일 전부 — 하나라도 못 읽으면 회색이다.
ROUTE_FILES = (
    "apps/dsm/api.py",
    "apps/dsm/api_u1.py",
    "apps/dsm/api_u24.py",
    "apps/dsm/api_u56.py",
    "apps/dsm/law_api.py",
)


def _backend_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _routes_opened_to_keys() -> tuple[list[tuple[str, int]], int]:
    """`auth=...(inbound_key=True ...)` 를 **선언한** 라우트. `(자리 목록, 읽은 파일 수)`.

    ⚠ 문자열·주석의 `inbound_key=True` 는 안 잡는다 — AST 로 **키워드 인자**만 본다.
      그래서 「예전엔 True 였다」는 설명 주석이 이 시험을 빨갛게 만들지 않는다.
    """
    root = _backend_root()
    found: list[tuple[str, int]] = []
    read = 0
    for rel in ROUTE_FILES:
        path = root / rel
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        read += 1
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            opened = False
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                for kw in deco.keywords:
                    if kw.arg != "auth" or not isinstance(kw.value, ast.Call):
                        continue
                    for akw in kw.value.keywords:
                        if (akw.arg == "inbound_key"
                                and isinstance(akw.value, ast.Constant)
                                and akw.value.value is True):
                            opened = True
            if opened:
                #: 경로 글자는 데코레이터의 첫 위치 인자다.
                for deco in node.decorator_list:
                    if (isinstance(deco, ast.Call) and deco.args
                            and isinstance(deco.args[0], ast.Constant)
                            and isinstance(deco.args[0].value, str)):
                        found.append((deco.args[0].value, node.lineno))
                        break
    return found, read


class KeyScopeReachabilityTest(unittest.TestCase):
    """DB 를 안 쓴다 — 그래서 시험 DB 를 하나도 더 만들지 않는다(OPS-24 와 같은 결)."""

    def test_the_registry_still_declares_four_names(self):
        """① 정본이 넷을 들고 있다. 줄면 명세 §3 의 표가 거짓이 된다."""
        root = _backend_root() / "kernels" / "k5_trust" / "key_scopes.py"
        if not root.is_file():
            self.skipTest("key_scopes.py 를 못 찾았다 — **회색이지 통과가 아니다**")
        text = root.read_text(encoding="utf-8")
        for name in ("events:read", "pulse:read", "stats:read", "webhooks:manage"):
            self.assertIn(name, text, "범위 정본에서 «%s» 가 사라졌습니다." % name)

    def test_only_the_declared_doors_take_a_key(self):
        """② ★ **닿는 문의 수를 못 박는다.**

        늘면 「명세를 갱신하라」, 줄면 「문이 죽었다」 — 어느 쪽이든 사람이 봐야 한다.
        """
        found, read = _routes_opened_to_keys()
        self.assertEqual(
            len(ROUTE_FILES), read,
            "라우트 파일 %d 중 %d 개만 읽혔습니다 — 못 읽은 파일은 검사되지 "
            "않았고 그것을 초록으로 세면 안 됩니다." % (len(ROUTE_FILES), read))
        paths = sorted(p for p, _ in found)
        #: 선언 글자 ↔ 전체 경로가 갈리지 않았는지도 같은 판에서 본다 —
        #: `PATH_SCOPES` 가 전체 경로로 맺으므로 둘이 어긋나면 범위가 안 걸린다.
        reg = (_backend_root() / "kernels" / "k5_trust" / "key_scopes.py")
        if reg.is_file():
            text = reg.read_text(encoding="utf-8")
            for decl, (scope, full) in REACHABLE.items():
                self.assertIn(
                    '("%s", ' % full, text,
                    "`%s` 가 열려 있는데 `PATH_SCOPES` 에 «%s» 줄이 없습니다 — "
                    "범위 «%s» 가 그 문에서 **안 걸립니다**." % (decl, full, scope))
        self.assertEqual(
            sorted(REACHABLE), paths,
            "키에게 열린 문의 집합이 달라졌습니다 (지금: %s).\n"
            "· **늘었다면 좋은 일이다** — 다만 `docs/design/GX-API_연계명세_v0.1.md` "
            "§3 과 이 파일의 `REACHABLE` 을 **같은 변경에서** 고쳐라. 안 고치면 "
            "명세가 조용히 거짓이 된다.\n"
            "· **줄었다면 문이 죽은 것이다** — 범위 밖 403 을 잴 분모가 사라진다."
            % (found,))

    def test_stats_is_a_name_that_goes_nowhere_and_we_say_so(self):
        """③ ★★ **「발급된다」와 「어디론가 간다」를 갈라 적는다.**

        `stats:read` 는 발급되고 422 도 안 난다. 그런데 그 키가 갈 수 있는 문은
        **0개**다 — `/api/dsm/stats/*` 가 전부 `JwtOrInboundKey()` 기본값이라
        키는 범위를 따지기도 전에 **401** 로 끝난다.
        이 시험은 그 사실을 **수로** 고정한다. U24 가 문을 열면 여기가 빨개지고,
        그때 명세 §3 의 「남은 한계」 절을 지우면 된다.
        """
        root = _backend_root() / "apps" / "dsm" / "api_u24.py"
        if not root.is_file():
            self.skipTest("api_u24.py 를 못 찾았다 — **회색이지 통과가 아니다**")
        tree = ast.parse(root.read_text(encoding="utf-8"), filename=str(root))
        stats_routes, stats_open = 0, 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            first = node.args[0]
            if not (isinstance(first, ast.Constant)
                    and isinstance(first.value, str)
                    and first.value.startswith("/stats/")):
                continue
            stats_routes += 1
            for kw in node.keywords:
                if kw.arg == "auth" and isinstance(kw.value, ast.Call):
                    for akw in kw.value.keywords:
                        if (akw.arg == "inbound_key"
                                and isinstance(akw.value, ast.Constant)
                                and akw.value.value is True):
                            stats_open += 1
        self.assertGreater(stats_routes, 0, "`/stats/*` 를 한 문도 못 찾았습니다 — "
                                            "세는 법이 깨졌습니다.")
        self.assertEqual(
            0, stats_open,
            "`/stats/*` 가 키에게 열렸습니다 (%d/%d). **그 자체는 좋은 일입니다** — "
            "이제 `stats:read` 범위 밖 403 을 잴 수 있습니다. 명세 "
            "`GX-API_연계명세_v0.1.md` §3 의 「남은 한계」 절과 이 시험을 "
            "**같은 변경에서** 고쳐 주십시오." % (stats_open, stats_routes))
