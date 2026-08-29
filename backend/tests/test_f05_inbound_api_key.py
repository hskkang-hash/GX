# -*- coding: utf-8 -*-
"""F-05 진입면의 **들어오는 API Key** — 규약 다섯을 시험으로 건다 (D-335).

★ 이 절은 「만들기」가 아니라 「좁히기」였다 — 착수하며 알게 된 것
----------------------------------------------------------------
dj-core 의 `CustomJWTAuth` 는 **이미** inbound 키 헤더와 `Authorization` 의 inbound 스킴을
받는다(core/api/v1/auth.py:136·168). 즉 들어오는 키는 만들 것이 아니라 **이미 살아 있었고,
아무도 그 범위를 정하지 않았다.**

착수 전 호출로 잰 것 [실측 2026-09-07] — 키 하나로 F-05 진입면 **7자리에 전부** 닿았다:

    /api/dsm/events · /deliveries · /dashboard/frame(200) · /events/{id}/clip ·
    **/events/{id}/clip/stream** · /reports/templates(200) · /settings/{domain}

`clip/stream` 이 계약 11조(영상 반출 · D-306)의 자리다. **발급된 아무 키나 거기 닿고 있었다.**
인증 자체는 성했다 — 만료·비활성·가짜 키는 전부 401 이었다. 성하지 않은 것은 **범위**다.

「같은 이름, 다른 것」 (D-337)
    outbound(나가는) 키 = 우리가 남을 부를 때 · 표 ②가 관리한다
    inbound (들어오는) 키 = 남이 우리를 부를 때 · **이 파일이 그것이다**

규약 다섯 (D-335) — 아래 클래스가 하나씩 맡는다
    ① 키는 테넌트에 묶인다      TenantBindingTest
    ② HTTPS 강제                HttpsRequiredTest
    ③ 읽기 전용부터            ReadOnlyTest
    ④ 키 값을 저장하지 않는다   KeyIsNeverStoredInPlaintextTest
    ⑤ 부작위                    NoReachToVideoOrOtherTenantsTest   ← ★ 이것이 본체다

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105) — skip·xfail 하지 말 것.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from common.inbound_api_key import JwtOrInboundKey, carries_inbound_key

#: ★ **들어오는 키가 닿아도 되는 자리 — 전부.** 이 집합이 곧 개방 선언이다.
#: 늘리는 일은 손으로 이 줄을 더하는 일이고, 그 손이 「진입면을 넓힌다」는 선언이다
#: (`test_f05_event_api.py::EVENT_ENTRY_SURFACE` 와 같은 방식).
INBOUND_KEY_ALLOWED = frozenset({
    ("GET", "/api/dsm/events"),
})

#: 닿으면 **안 되는** 자리 중 무게가 다른 둘. 나머지는 아래 부작위 시험이 전수로 본다.
#: ★ 이 설정 도메인은 **나가는(outbound) 키**의 표다(표 ② · D-337). 들어오는 키가 닿으면
#: 「남을 부르는 우리 자격증명」이 「남이 우리를 부르는 키」에게 보이는 꼴이다.
OUTBOUND_KEY_SETTINGS_PATH = "/api/dsm/settings/api_keys"

#: 들어오는 키를 우리 층이 붙들고 있는 모양. 이 글자가 문지기 소스에 있으면 안 된다(규약 ④).
INBOUND_KEY_MISHANDLING = ("logger.info(api_key", "print(api_key", "= api_key", "save(", "objects.create(")

VIDEO_ROUTE = "/api/dsm/events/1/clip/stream"
CLIP_ROUTE = "/api/dsm/events/1/clip"


def _dsm_operations():
    """DSM 진입면을 런타임 레지스트리에서 읽는다 — 정적 grep 이 아니다."""
    from common.tenant_scope import _iter_ninja_apis, _join

    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    path = _join(mount, prefix, op_path)
                    if not path.startswith("/api/dsm/"):
                        continue
                    for method in (getattr(op, "methods", []) or []):
                        yield str(method).upper(), path, (getattr(op, "auth_callbacks", None) or [])


class _KeyFixture(TestCase):
    """실제 키를 발급한다 — 합성 더미가 아니라 dj-core 의 발급 면을 쓴다 (D-289)."""

    def setUp(self):
        from core.apikey_account.models import APIKey as InboundKeyRecord

        User = get_user_model()
        self.user = User.objects.create(username="f05-partner",
                                        email="f05@test.invalid", is_active=True)
        self.raw_key, prefix, key_hash = InboundKeyRecord.generate_key()
        self.inbound_key_row = InboundKeyRecord.objects.create(
            user=self.user, name="f05-inbound", key_hash=key_hash,
            prefix=prefix, is_active=True)
        # 캐시를 우회한다 — 관문을 재는 시험이 캐시를 재면 안 된다 (D-334 에서 배운 것).
        self.client = Client(raise_request_exception=False, HTTP_X_NO_CACHE="true")

    def get(self, path, secure=False):
        return self.client.get(path, HTTP_X_API_KEY=self.raw_key, secure=secure)


@override_settings(INBOUND_API_KEY_REQUIRE_HTTPS=False)
class NoReachToVideoOrOtherTenantsTest(_KeyFixture):
    """⑤ 부작위 — **키가 닿는 자리가 선언된 것뿐인가** (D-300).

    ★ 이것이 이 파일의 본체다. 「이벤트 조회를 열었다」가 아니라
      **「그 밖 어디에도 안 열렸다」**를 재야 D-335 규약 ③⑤ 가 지켜진다.
    """

    def test_the_key_reaches_only_the_declared_routes(self):
        declared = {
            (m, p) for m, p, cbs in _dsm_operations()
            if any(isinstance(cb, JwtOrInboundKey) and cb.inbound_key for cb in cbs)
        }
        self.assertEqual(
            INBOUND_KEY_ALLOWED, declared,
            "들어오는 키를 받는 라우트 집합이 바뀌었다. 늘렸다면 절과 사유를 함께 적고 "
            "이 목록을 손으로 고쳐라 — 그 손이 곧 진입면을 넓힌다는 선언이다:\n"
            f"  선언됨 {sorted(declared)}\n  기대   {sorted(INBOUND_KEY_ALLOWED)}",
        )

    def test_every_dsm_route_uses_the_inbound_gate(self):
        """게이트를 안 거치는 라우트가 하나라도 있으면 그리로 키가 샌다."""
        ungated = [f"{m} {p}" for m, p, cbs in _dsm_operations()
                   if not any(isinstance(cb, JwtOrInboundKey) for cb in cbs)]
        self.assertEqual(
            ungated, [],
            "문지기 없는 진입면이 있다 — 키가 그리로 들어온다:\n  " + "\n  ".join(ungated))

    def test_the_key_cannot_reach_the_original_video(self):
        """★ 계약 11조 (D-306). 발급된 키가 원본 영상에 닿으면 안 된다."""
        for path in (VIDEO_ROUTE, CLIP_ROUTE):
            resp = self.get(path)
            self.assertEqual(
                resp.status_code, 401,
                f"{path} 에 들어오는 키가 닿았다 (status={resp.status_code}) — "
                f"계약 11조 영상 반출 규약을 키 하나가 넘는다")

    def test_the_key_cannot_reach_settings_or_reports(self):
        for path in (OUTBOUND_KEY_SETTINGS_PATH, "/api/dsm/reports/templates",
                     "/api/dsm/deliveries", "/api/dsm/dashboard/frame"):
            resp = self.get(path)
            self.assertEqual(resp.status_code, 401,
                             f"{path} 에 들어오는 키가 닿았다 (status={resp.status_code})")

    def test_the_declared_route_does_let_the_key_in(self):
        """음성 대조 — 전부 401 이면 「막았다」가 아니라 「아무것도 안 열렸다」이다.

        이 단언이 없으면 위 시험들은 라우트가 통째로 죽어도 초록이다.
        """
        resp = self.get("/api/dsm/events")
        self.assertNotEqual(
            resp.status_code, 401,
            "이벤트 조회에조차 키가 못 들어간다 — 열어 준 것이 없으면 위 시험은 "
            "아무것도 재지 않은 것이다")


@override_settings(INBOUND_API_KEY_REQUIRE_HTTPS=True)
class HttpsRequiredTest(_KeyFixture):
    """② 키가 평문으로 흐르면 키가 아니다."""

    def test_plaintext_request_with_a_key_is_refused(self):
        resp = self.get("/api/dsm/events", secure=False)
        self.assertEqual(resp.status_code, 401,
                         "평문 요청에 실린 키가 통과했다 — 그 키는 이미 새어 있다")

    def test_https_request_with_a_key_passes(self):
        resp = self.get("/api/dsm/events", secure=True)
        self.assertNotEqual(resp.status_code, 401)

    def test_jwt_path_is_not_affected_by_the_https_rule(self):
        """좁히는 것은 **키 갈래뿐**이다. 사람 로그인 경로를 건드리지 않는다."""
        resp = self.client.get("/api/dsm/events")          # 아무 자격도 없음
        self.assertEqual(resp.status_code, 401)


@override_settings(INBOUND_API_KEY_REQUIRE_HTTPS=False)
class ReadOnlyTest(_KeyFixture):
    """③ 읽기 전용부터 — 쓰기 면은 절을 따로 세운다."""

    def test_no_write_route_accepts_an_inbound_key(self):
        from common.inbound_api_key import WRITE_METHODS

        opened_writes = [
            f"{m} {p}" for m, p, cbs in _dsm_operations()
            if m in WRITE_METHODS
            and any(isinstance(cb, JwtOrInboundKey) and cb.inbound_key for cb in cbs)
        ]
        self.assertEqual(
            opened_writes, [],
            "쓰기 라우트에 들어오는 키를 열었다 — 계약 AC 절에 쓰기가 있는지 먼저 "
            "확인하고, 없으면 만들지 않는다 (D-335 ③):\n  " + "\n  ".join(opened_writes))

    def test_the_notify_write_route_refuses_the_key(self):
        resp = self.client.post("/api/dsm/events/1/notify", HTTP_X_API_KEY=self.raw_key)
        self.assertEqual(resp.status_code, 401,
                         "키로 발송을 일으킬 수 있다 — 쓰기 IDOR 이다")


@override_settings(INBOUND_API_KEY_REQUIRE_HTTPS=False)
class TenantBindingTest(_KeyFixture):
    """① 키는 테넌트에 묶인다 — 키의 소유자가 곧 스코프다."""

    def test_the_route_that_accepts_the_key_is_tenant_scoped(self):
        """키를 받는 라우트에 문지기가 없으면 ①은 성립할 수 없다."""
        from common.tenant_scope import SCOPE_ATTR

        unscoped = []
        for method, path, cbs in _dsm_operations():
            if not any(isinstance(cb, JwtOrInboundKey) and cb.inbound_key for cb in cbs):
                continue
            view = _view_for(method, path)
            if getattr(view, SCOPE_ATTR, None) is None:
                unscoped.append(f"{method} {path}")
        self.assertEqual(
            unscoped, [],
            "들어오는 키를 받으면서 테넌트 문지기가 없는 라우트다 — 키 하나로 "
            "남의 테넌트가 보인다:\n  " + "\n  ".join(unscoped))

    def test_an_inactive_key_is_refused(self):
        self.inbound_key_row.is_active = False
        self.inbound_key_row.save(update_fields=["is_active"])
        self.assertEqual(401, self.get("/api/dsm/events").status_code)

    def test_an_expired_key_is_refused(self):
        self.inbound_key_row.expires_at = timezone.now() - timezone.timedelta(days=1)
        self.inbound_key_row.save(update_fields=["expires_at"])
        self.assertEqual(401, self.get("/api/dsm/events").status_code)

    def test_a_forged_key_is_refused(self):
        resp = self.client.get("/api/dsm/events", HTTP_X_API_KEY="not-a-real-key-000000")
        self.assertEqual(401, resp.status_code)


class KeyIsNeverStoredInPlaintextTest(TestCase):
    """④ 키 값을 저장하지 않는다 — 우리 층이 원문을 들고 있지 않은가."""

    def test_the_gate_never_returns_the_key_value(self):
        """`carries_inbound_key` 는 **유무만** 답한다.

        값을 반환하면 부르는 쪽이 그것을 로그에 넣게 되고, 그 순간 키가 평문으로 남는다.
        """
        from django.test import RequestFactory

        req = RequestFactory().get("/", HTTP_X_API_KEY="super-secret-value")
        got = carries_inbound_key(req)
        self.assertIs(got, True)
        self.assertNotIsInstance(got, str, "유무가 아니라 값을 돌려주고 있다")

    def test_our_layer_stores_no_raw_key(self):
        """우리 모듈 소스에 키를 담아 두는 자리가 없는가 — 눈으로가 아니라 글자로 본다."""
        from pathlib import Path

        src = (Path(__file__).resolve().parents[1] / "common" / "inbound_api_key.py").read_text(
            encoding="utf-8")
        for bad in INBOUND_KEY_MISHANDLING:
            self.assertNotIn(
                bad, src,
                f"들어오는 키 문지기가 키 값을 다루는 모양이 있다: {bad!r} (D-335 ④)")

    def test_djcore_stores_only_a_hash(self):
        """발급 면이 해시만 갖는가 — **읽고 확인만 한다**(§0.4, 고치지 않는다)."""
        from core.apikey_account.models import APIKey as InboundKeyRecord

        fields = {f.name for f in InboundKeyRecord._meta.get_fields()}
        self.assertIn("key_hash", fields)
        self.assertNotIn("key", fields, "발급 면이 키 원문 칸을 갖고 있다")

        raw, prefix, key_hash = InboundKeyRecord.generate_key()
        self.assertNotEqual(raw, key_hash)
        self.assertEqual(64, len(key_hash), "sha256 16진수 64자가 아니다")


# ── 작은 도우미 ─────────────────────────────────────────────────────────────
def _view_for(method: str, path: str):
    from common.tenant_scope import _iter_ninja_apis, _join

    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    if _join(mount, prefix, op_path) != path:
                        continue
                    if method not in [str(m).upper() for m in (getattr(op, "methods", []) or [])]:
                        continue
                    return getattr(op, "view_func", None)
    return None
