# -*- coding: utf-8 -*-
"""D-334 — 주석 처리된 권한 데코레이터가 남긴 **열린 문 15자리**를 못박는다.

2026-09-07 실측. 권한 계열 데코레이터 사용 **320자리**(활성 281 · 주석 39) 중,
주석 처리된 39자리를 인증 관문 유무로 갈랐다:

    · authn_only        24자리 — `auth=` 는 살아 있다. 익명 요청은 401 이었다
    · no_authn_no_authz 15자리 — `auth=` 도 없다. **익명 요청이 핸들러에 닿았다**

15자리 전부를 **호출로** 확인했다(코드를 읽어서 답하지 않았다 — D-210):
GET 8자리는 그냥 때렸고(200×3 · 422 · 400×2 · 404×2 · 500), POST 7자리는 등록된
핸들러를 도달 표시만 남기는 대체물로 잠시 바꿔 때렸다 — 본체는 한 줄도 돌지 않았다.
**전부 401 이 아니었다.** 그중 셋은 익명에게 200 과 데이터를 돌려주고 있었다.

이 파일이 못박는 것은 셋이다.

  1) 그 15자리에 **인증 관문이 붙어 있다.** 레지스트리에서 확인한다
  2) 익명 요청이 그 자리에서 **401** 을 받는다. 호출로 확인한다
  3) **주석 처리된 권한 + `auth=` 없음** 의 조합이 저장소에 0건이다 (게이트와 같은 술어)

★ 왜 권한을 되살리지 않고 인증만 붙였나
    `@path_permission` 은 **권한**이고 `auth=` 는 **인증**이다 — 같은 이름이 아니다(D-337).
    열려 있던 것은 인증이고, 그것이 사고다. 권한 복구는 역할·경로 대장이 필요한 별개의 일이라
    나머지 24자리와 함께 래칫(D-311)에 둔다. **열린 문에는 유예가 없고, 느슨한 권한에는 있다.**

★ 캐시가 코드 수정보다 오래 산다 — 이번에 실측한 것
    `UniversalCacheMiddleware` 는 캐시 적중 시 뷰를 부르지 않고 `JsonResponse(200)` 을
    돌려준다. 키에 사용자 권한 서명이 들어가고 익명은 `"anon"` 이라, **열려 있던 동안
    익명으로 채워진 항목이 코드를 고친 뒤에도 익명에게 그대로 나갔다.**
    (2026-09-07 실측: 수정 후에도 2자리가 200 이었고, `cache.clear()` 뒤 0 이 됐다.)
    → 그래서 이 시험은 캐시를 우회해서 때린다. **관문을 재는 시험이 캐시를 재면 안 된다.**

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""

from __future__ import annotations

from django.test import Client, TestCase

#: ★ **출생 표본** — 2026-09-07 익명 호출이 인증 관문을 지난 15자리. 실측 목록 그대로다.
#: `(메서드, 경로, 그때 익명이 받은 것)`. 경로 파라미터는 호출 때 1 로 채운다.
FORMERLY_OPEN = [
    ("POST", "/api/delivery/processing/update-delivery-event", "422"),
    ("GET", "/api/dronehw/drone-communication-management/online-drones", "200"),
    ("GET", "/api/operational-data/operational-data/download-operational-data", "422"),
    ("POST", "/api/operational-data/operational-data/{id}/upload-operational-log-drone", "도달"),
    ("POST", "/api/operational-data/operational-data/{id}/upload-operational-log-robot", "도달"),
    ("POST", "/api/operational-data/operational-data/{id}/upload-operational-video-drone", "도달"),
    ("POST", "/api/operational-data/operational-data/{id}/upload-operational-video-robot", "도달"),
    ("GET", "/api/operational-data/operational-data/{id}/download-operational-log-drone", "400"),
    ("GET", "/api/operational-data/operational-data/{id}/download-operational-log-robot", "400"),
    ("POST", "/api/surveillance/surveillance-profiles/{id}/completed-profile", "도달"),
    ("GET", "/api/terminals/days-of-week", "200"),
    ("GET", "/api/terminals/days-of-week/{id}", "404"),
    ("GET", "/api/terminals/terminal-types", "200"),
    ("GET", "/api/terminals/terminal-types/{id}", "404"),
    ("GET", "/api/terminals/functions/function-types", "500"),
]

#: 그중 익명에게 **데이터를 돌려주고 있던** 자리. 사고의 본체다.
LEAKED_200 = [p for m, p, got in FORMERLY_OPEN if got == "200"]


def _concrete(path: str) -> str:
    return path.replace("{id}", "1")


def _registry_rows():
    """ninja 레지스트리를 읽는다 — 정적 grep 이 아니다(동적 등록을 놓치지 않기 위해)."""
    from common.tenant_scope import _iter_ninja_apis, _join

    rows = {}
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    path = _join(mount, prefix, op_path)
                    for method in (getattr(op, "methods", []) or []):
                        rows[(str(method).upper(), path)] = op
    return rows


def _normalize(path: str) -> str:
    """레지스트리의 `{order_item_id}` 와 이 파일의 `{id}` 를 같은 것으로 본다."""
    import re
    return re.sub(r"\{[^}]+\}", "{}", path)


class FormerlyOpenRoutesHaveAuthTest(TestCase):
    """① 15자리에 인증 관문이 붙어 있는가 — 레지스트리에서 확인한다."""

    def test_every_formerly_open_route_has_auth_callback(self):
        rows = {(m, _normalize(p)): op for (m, p), op in _registry_rows().items()}
        missing, unfound = [], []
        for method, path, _got in FORMERLY_OPEN:
            op = rows.get((method, _normalize(path)))
            if op is None:
                unfound.append("%s %s" % (method, path))
                continue
            if not (getattr(op, "auth_callbacks", None) or []):
                missing.append("%s %s" % (method, path))

        self.assertEqual(
            unfound, [],
            "라우트가 사라졌거나 경로가 바뀌었다 — 목록을 실측으로 갱신하라:\n  "
            + "\n  ".join(unfound),
        )
        self.assertEqual(
            missing, [],
            "★ 인증 관문이 다시 없어졌다. 익명이 핸들러에 닿는다:\n  " + "\n  ".join(missing),
        )


class FormerlyOpenRoutesRejectAnonymousTest(TestCase):
    """② 익명 요청이 401 을 받는가 — **호출로** 확인한다 (D-210).

    GET 만 때린다. 쓰기 메서드는 부작용이 있어 이 시험에서 부르지 않고, ①의
    레지스트리 단언이 그 자리를 지킨다 — 두 시험이 갈라 맡는다.
    """

    def setUp(self):
        # 캐시를 우회한다. 관문을 재는 시험이 캐시를 재면 안 된다 (파일 머리말 참조).
        self.client = Client(raise_request_exception=False, HTTP_X_NO_CACHE="true")

    def test_anonymous_get_is_rejected(self):
        wrong = []
        for method, path, _got in FORMERLY_OPEN:
            if method != "GET":
                continue
            resp = self.client.get(_concrete(path))
            if resp.status_code != 401:
                wrong.append("%s -> %s (401 이어야 한다)" % (path, resp.status_code))
        self.assertEqual(
            wrong, [],
            "★ 익명 요청이 인증 관문을 지났다:\n  " + "\n  ".join(wrong),
        )

    def test_leaked_routes_no_longer_return_data(self):
        """익명에게 200 과 데이터를 돌려주던 셋 — 본문이 나가지 않는다."""
        self.assertEqual(len(LEAKED_200), 3, "사고 규모를 바꾸려면 사유와 함께 바꿔라")
        for path in LEAKED_200:
            resp = self.client.get(_concrete(path))
            self.assertEqual(
                resp.status_code, 401,
                "%s 가 익명에게 다시 열렸다 (status=%s)" % (path, resp.status_code),
            )


class NoCommentedGuardWithoutAuthTest(TestCase):
    """③ 「주석 처리된 권한 + `auth=` 없음」이 저장소에 0건인가.

    게이트(`scripts/verify_commented_guards.py`)와 **같은 술어**를 시험에서도 본다.
    게이트는 커밋을 막고 이 시험은 회귀를 막는다 — 둘 다 필요하다(D-286).
    """

    def test_zero_open_doors(self):
        import sys
        from pathlib import Path

        scripts = Path(__file__).resolve().parents[2] / "scripts"
        if not scripts.is_dir():                       # 컨테이너에서는 /repo/scripts
            scripts = Path("/repo/scripts")
        self.assertTrue(scripts.is_dir(), "scripts/ 를 찾지 못했다: %s" % scripts)
        sys.path.insert(0, str(scripts))

        from probe_commented_guards import static_census

        backend = Path(__file__).resolve().parents[1]
        rows = static_census(str(backend))["commented_rows"]
        open_doors = [
            "%s:%s %s" % (r["file"], r["line"], r.get("handler"))
            for r in rows if not r["auth_kwarg_in_source"]
        ]
        self.assertEqual(
            open_doors, [],
            "★ 주석 처리된 권한이 `auth=` 없는 라우트에 있다 — 열린 문이다:\n  "
            + "\n  ".join(open_doors),
        )
