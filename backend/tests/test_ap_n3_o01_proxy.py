# -*- coding: utf-8 -*-
"""P-427 ⑤ · WO-GX-20261001-19 §5(P-427) — **O-01 대행 호출 강화**(턴 AP ·
차선 N3).

턴 AO 청구 ⑤(`docs/workorders/WO-GX-20260930-18_report.md` 끝 문단)가 남긴
질문: `ops_an_service.issue_tenant()` 가 U0 요청의 `Authorization` 헤더를
안쪽 `POST /api/v1/user/create-user` 호출에 그대로 물려준다 — "이미 인증된
U0 의 대행 · 새 구멍 아님"이라 판단했지만 **자격이 언제 발급됐는지는 묻지
않았다**. 이 파일이 재확인하고 더하는 것:

  ① **U0 만** — `_require_operator(actor)` 재확인(안 바뀌었다).
  ② **감사 줄 1** — 성공(`issue`)·거절(`issue_denied_stale_proxy`) 둘 다 감사에
     남는다는 것을 실측.
  ③ **시간 제한(15분)** — [이 턴이 더함] `PROXY_FRESHNESS_LIMIT_SECONDS`(900초)
     보다 오래된 `iat` 를 실은 자격으로는 대행이 **거절**된다(403)는 것을 실제
     JWT 를 만들어 실측한다.

재확인 표(사람이 읽는 요약)는 `docs/agent/evidence/SPEC/O-01_proxy_review.md`.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from apps.dsm import ops_an_service as svc
from tests.test_ops_an import TENANTS, OpsAnFixture


def _stale_bearer(user, *, minutes_old: int) -> dict:
    """`iat` 를 과거로 되돌린 실제 JWT — 서명은 그대로 유효하다(exp 는 안 건드려서
    아직 안 만료됐다). `FwsHttpTest._bearer`(=`OpsAnFixture._bearer`)와 **같은
    세션 등록**을 한다 — 안 하면 `core/auth.py` 가 `user.token`(세션 칸)과 이
    토큰의 `session_id`/`jti` 가 안 맞아 **다른 이유로** 401 을 낸다(세션 불일치)
    — 그러면 이 시험이 재려는 것(신선도 903초 초과 → 대행 거절 403)과 다른 것을
    잰 게 된다. 세션은 등록하고 **`iat` 만** 낡게 만든다."""
    import uuid

    import jwt as pyjwt
    from django.conf import settings
    from ninja_jwt.tokens import RefreshToken

    session_id = str(uuid.uuid4())
    refresh = RefreshToken.for_user(user)
    refresh["session_id"] = session_id
    access = refresh.access_token
    access.set_iat(at_time=timezone.now() - timedelta(minutes=minutes_old))
    access_str = str(access)
    decoded = pyjwt.decode(
        access_str, settings.NINJA_JWT["SIGNING_KEY"],
        algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
    setter = getattr(user, "set_encrypted_session_token", None)
    if setter is not None:
        setter(session_id, decoded.get("jti"))
        user.save()
    return {"HTTP_AUTHORIZATION": "Bearer %s" % access_str}


class O01ProxyFreshnessTest(OpsAnFixture):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def test_fresh_token_still_issues_tenant(self) -> None:
        """① 회귀 — 방금 로그인한(0분 된) U0 자격은 그대로 대행에 쓰인다."""
        resp, params = self._issue_tenant()
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = self._body(resp)
        self.assertEqual(params["code"], body["tenant_code"])

        rows = svc._audit_rows(svc.LOG_TENANTS, action_prefix="issue")
        mine = [r for r in rows if r.get("tenant_code") == params["code"]
               and r.get("_action") == "issue"]
        self.assertTrue(mine, "성공 발급인데 감사 줄(issue)이 안 남았다")

    def test_stale_token_is_rejected_with_403_and_audited(self) -> None:
        """③ 시간 제한 — 20분 된(제한 15분 초과) 자격은 대행을 거절당한다."""
        code = "t-stale-%s" % timezone.now().strftime("%H%M%S%f")
        params = {
            "code": code, "name": "낡은 자격 대행 시험 %s" % code,
            "admin_username": "opsadmin_stale_%s" % timezone.now().strftime("%H%M%S%f"),
            "admin_email": "opsadmin_stale@test.invalid",
            "admin_password": "Tenant-Admin-Pw-1!",
        }
        from tests.test_fws_app import _qs

        stale_head = _stale_bearer(self.u0, minutes_old=20)
        resp = self.client.post(_qs(TENANTS, **params), **stale_head)

        self.assertEqual(403, resp.status_code, resp.content[:300])

        from django.apps import apps

        UserGroup = apps.get_model("user", "UserGroup")
        self.assertFalse(UserGroup._base_manager.filter(code=code).exists(),
                         "거절된 대행 시도인데 테넌트가 만들어졌다")

        rows = svc._audit_rows(svc.LOG_TENANTS,
                               action_prefix=svc.LOG_TENANTS_PROXY_DENIED_ACTION)
        mine = [r for r in rows if r.get("tenant_code") == code]
        self.assertTrue(mine, "거절된 대행 시도인데 감사 줄이 안 남았다")
        self.assertGreater(mine[-1].get("auth_age_seconds") or 0, 900)

    def test_freshness_helper_rejects_unreadable_header(self) -> None:
        """도우미 함수 자체 — 못 읽는 헤더는 신선하지 않은 것으로 본다(모르면 통과
        안 시킨다)."""
        self.assertIsNone(svc._forwarded_auth_age_seconds(""))
        self.assertIsNone(svc._forwarded_auth_age_seconds("Bearer not-a-jwt"))

    def test_freshness_helper_reads_real_iat(self) -> None:
        head = _stale_bearer(self.u0, minutes_old=5)
        token = head["HTTP_AUTHORIZATION"]
        age = svc._forwarded_auth_age_seconds(token)
        self.assertIsNotNone(age)
        self.assertGreater(age, 4 * 60)
        self.assertLess(age, 6 * 60)
