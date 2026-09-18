# -*- coding: utf-8 -*-
"""U5 #2 「역할 부여·변경」 — **`/roles` 표가 0행인 뿌리를 문으로 가른다** (턴 U · 차선 U56).

무엇이 있었나 [실측 · 턴 T · V 단독]
------------------------------------
    U5#2 | /roles | 문구 보임 | 술어 안 섬 | ○ (0.0)
    · 역할 관리=True · 머리줄=True · **표 행 0** · `Add New Role`=False
    · 같은 시각 runserver 는 `GET /api/roles/?page_size=1&current_page=1 200` 을 냈다

즉 **문은 200 을 냈는데 화면에 행이 0** 이었다. 두 가지가 가능하다:
    ㉠ 서버가 실제로 0행을 냈다 — 그러면 우리가 볼 것은 **왜 0인가**(소속·필터)
    ㉡ 서버는 행을 냈는데 화면이 못 그렸다 — 그러면 그것은 dj-core 화면의 일이다

이 시험이 가르는 것은 ㉠ 뿐이다(화면은 V 단독의 몫이고, 우리는 브라우저를 재지 않는다).
`/api/roles/` 는 **dj-core 라우트**다 — §0.4 라 고치지 않는다. 읽고 부르기만 한다.
"""
from __future__ import annotations

import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture


class RolesTableProbeTest(DsmFixture):
    """`admin` 자격으로 `/api/roles/` 를 두드려 **행 수와 모양**을 적는다."""

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self):
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    def _admin(self):
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(code="admin",
                                             defaults={"role_name": "admin"})
        role = self._own(role, self.group_a)
        self.user_a.roles.add(role)
        self.user_a.refresh_from_db()
        return self.user_a

    def _bearer(self, user) -> dict:
        import jwt as pyjwt
        from ninja_jwt.tokens import RefreshToken

        session_id = str(uuid.uuid4())
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        setter = getattr(user, "set_encrypted_session_token", None)
        if setter is not None:
            setter(session_id, decoded.get("jti"))
            user.save()
        return {"HTTP_AUTHORIZATION": "Bearer %s" % access}

    def test_roles_door_refuses_an_account_without_menu_permission(self):
        """★ 실측 ① — 문 앞에 **메뉴 권한 문지기**가 하나 더 있다.

        `admin` 역할만 가진 계정은 `/api/roles/` 에서 **403**(`Permission denied`)을
        받는다. dj-core `RoleController.list_roles` 의 데코레이터가
        `@path_permission("read", path_override="/roles")` 이기 때문이다 [실측].

        ⇒ 턴 T 가 본 「표 0행」의 앞에는 **「그 계정이 200 을 받았는가」**라는 질문이
          따로 있다. 둘을 뭉치면 「역할이 없다」와 「못 들어갔다」가 같은 그림이 된다.
        ★ 이 시험은 그 문지기를 **약하게 만들지 않는다** — 있는 그대로 적는다(§0.4).
        """
        admin = self._admin()
        resp = self.client.get("/api/roles/?page_size=50&current_page=1",
                               **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(
            403, resp.status_code,
            "문지기가 바뀌었습니다 — 이 시험이 적어 둔 실측이 낡았습니다: "
            + (resp.content or b"")[:300].decode("utf-8", "replace"))

    def test_roles_queryset_is_not_tenant_scoped(self):
        """★ 실측 ② — **0행의 뿌리는 격리가 아니다.**

        `list_roles` 의 질의는 `Role.objects.filter(deleted__isnull=True)` 이고,
        `Role.objects` 는 **평범한 `Manager`** 다(테넌트로 좁히는
        `CustomManagerGroup` 이 아니다) [실측 · 개발 DB 에서 비삭제 16행 ·
        group_id 분포 {None:6, 6:6, 5:3, 7:1}]. 따라서 「소속이 달라 안 보였다」는
        설명은 **이 라우트에는 서지 않는다.**

        ⇒ 남는 갈래는 화면 쪽이고, 그것은 §0.4(dj-core 인수 SPA)라 우리가 못 고친다.
          대장 등재 요청으로 넘긴다.
        """
        from django.db.models import Manager

        Role = apps.get_model("role", "Role")
        self.assertIs(
            type(Role.objects), Manager,
            "Role.objects 가 테넌트 매니저로 바뀌었습니다 — 이 절의 가름을 다시 하십시오.")
        self.assertGreaterEqual(
            Role.objects.filter(deleted__isnull=True).count(), 2,
            "질의 자체가 0행입니다 — 그러면 뿌리는 서버이고, 이 시험의 결론이 바뀝니다. "
            "(이 시험 DB 의 역할은 픽스처가 만든 둘뿐이다 — 개발 DB 의 16행과 다르다)")
