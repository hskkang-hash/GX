# -*- coding: utf-8 -*-
"""U56 ④ — `apps/dsm/people.py` 골격이 하는 두 가지를 잰다 (턴 Q P-141 · 시간이 남으면).

    ① `create_person` 이 dj-core 의 **실제 생성 경로**를 타는가 — 행이 실제로 생기고,
       비밀번호 값은 반환값에 없다.
    ② `deactivate_person` 뒤 **그 계정** 은 이미 들고 있던 유효한 토큰으로도 401 을
       받는가 — dj-core `CustomJWTAuth.authenticate()` 가 `user.is_active` 를 보고
       거절하는 **기존 경로**를 그대로 쓴다는 증거. 이 시험은 **새 인증 경로를 만들지
       않았다는 사실**을 재는 시험이다 — people.py 가 따로 401 을 판정하면 안 되고,
       dj-core 가 스스로 그것을 낸다.
"""
from __future__ import annotations

import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture


def _bearer(user) -> dict:
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


class PeopleSkeletonTest(DsmFixture):
    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)
        self.username = "u56_p141_person_%s" % uuid.uuid4().hex[:8]

    def test_create_person_goes_through_the_real_path_and_hides_the_password(self):
        from apps.dsm.people import create_person

        created = create_person(
            actor_bearer_header=_bearer(self.user_a),
            username=self.username, email="%s@test.invalid" % self.username,
            password="not-a-real-secret-1!", group_id=self.group_a.pk,
            role_ids=[self.role_a.pk], display_name="[시험] U56 P-141")

        self.assertTrue(created.user_id)
        self.assertEqual(self.username, created.username)
        self.assertNotIn("password", vars(created),
                         "반환값에 password 칸이 있습니다 — 값을 담지 않는다는 계약 위반.")

        CoreUser = apps.get_model("user", "CoreUser")
        row = CoreUser._base_manager.filter(pk=created.user_id).first()
        self.assertIsNotNone(row, "실제 생성 경로를 탔는데 행이 없습니다.")
        self.assertTrue(row.is_active)
        self.assertIn(self.role_a.pk, row.roles.values_list("pk", flat=True),
                     "지정한 역할이 안 붙었습니다.")

    def test_deactivation_makes_the_already_issued_token_401_via_the_existing_door(self):
        from apps.dsm.people import create_person, deactivate_person

        created = create_person(
            actor_bearer_header=_bearer(self.user_a),
            username=self.username, email="%s@test.invalid" % self.username,
            password="not-a-real-secret-1!", group_id=self.group_a.pk,
            role_ids=[self.role_a.pk], display_name="[시험] U56 P-141")

        CoreUser = apps.get_model("user", "CoreUser")
        person = CoreUser._base_manager.get(pk=created.user_id)

        #: **끄기 전에** 이미 유효한 토큰을 하나 발급해 둔다 — "발급 당시엔 살아
        #: 있었다"를 재현한다. 끈 뒤에 새로 발급한 토큰이 막히는 것은 당연하고,
        #: 이 시험이 재는 것은 **이미 들고 있던 토큰도** 막히는가다.
        person_bearer = _bearer(person)

        protected = self.client.get(
            "/api/dsm/events?limit=1", **person_bearer, **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, protected.status_code,
                         "끄기 전인데 이미 401 입니다 — 픽스처가 깨졌습니다: "
                         + (protected.content or b"")[:200].decode("utf-8", "replace"))

        #: 끄는 쪽은 **이 픽스처의 관리자**(user_a) 로 — deactivate_person 은 누가
        #: 끌 수 있는지 판정하지 않는다(그 판정은 dj-core 문의 것).
        deactivate_person(actor_bearer_header=_bearer(self.user_a),
                          user_id=created.user_id)

        person.refresh_from_db()
        self.assertFalse(person.is_active, "비활성화했는데 is_active 가 그대로입니다.")

        resp = self.client.get(
            "/api/dsm/events?limit=1", **person_bearer, **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(
            401, resp.status_code,
            "★ 이미 들고 있던 토큰이 비활성화 뒤에도 통과합니다 — "
            "dj-core CustomJWTAuth.authenticate() 의 is_active 검사가 이 자리에서 "
            "안 돌고 있을 수 있습니다: "
            + (resp.content or b"")[:200].decode("utf-8", "replace"))
