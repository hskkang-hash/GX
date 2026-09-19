# -*- coding: utf-8 -*-
"""P-185 ㉣ — **0건을 실제로 만들어 놓고 잰다** (턴 W · 차선 U24).

세종: 「0건일 때 화면이 무엇을 말하는가. … **0건일 때를 실제로 만들어서 눌러 봐라** —
**분모 0 을 안 보고 쓴 문구는 안 본 것이다.**」

이 파일이 하는 일은 **분모를 0 으로 만드는 것**이다
----------------------------------------------------
화면 문구를 고치는 것은 `.tsx` 의 일이고, 여기서는 그 문구가 걸리는 **조건이 실제로
나는지**를 서버 쪽에서 재 둔다. 0건 화면을 고쳐 놓고 0건을 한 번도 못 만들어 봤다면
그 문구는 **아무도 안 본 문장**이고, 그런 문장은 대개 틀려 있다.

잰 자리 둘 — 둘 다 **카메라 0대 · 보고서 0건인 새 테넌트**를 만들어서 두드린다.
  ① `GET /api/dsm/cameras/address-gap`  — `measurable` 이 **거짓**으로 온다
     (`total=0` 일 때 「0%」가 아니라 「잴 수 없다」. 화면은 이때 비율 카드를 안 그린다)
  ② `GET /api/dsm/reports/runs`         — `runs` 가 **빈 배열**로 온다
     (요청은 200 이다. 「못 가져온 것」과 「0건」이 여기서 갈린다)

★ 「관리·설정」(`/dsm/system` · `SystemSettings.tsx`)은 **이번 턴 차선 U56 이 쓰고 있다.**
  한 파일은 한 차선이므로 U24 는 그 화면을 고치지 않았다 — 문구는 재서 넘겼다.

캐시 처리: 우회 — `Client(**NO_CACHE)` (`X-No-Cache` · D-341 착시 ⑦).
이 시험이 재는 것은 **분모가 0 인 순간의 응답**이다. 적중한 본문이 돌아오면
0 건이 아니던 옛 화면을 0 건으로 읽게 되고, 그것이 바로 이 시험이 막으려는
「분모 0 을 안 보고 쓴 문구」다 — 캐시를 타면 시험이 제 목적을 배반한다.
"""
from __future__ import annotations

import contextlib
import json

from django.apps import apps
from django.test import Client, TestCase

from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PASSWORD = "u24-empty-test-only-not-a-secret"


def _forget_leftover_request() -> None:
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class ZeroDenominatorTest(TestCase):
    """**분모 0 인 테넌트 하나.** 카메라도 보고서도 한 건 없이 태어난 곳이다."""

    @classmethod
    def setUpClass(cls):
        _forget_leftover_request()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        _forget_leftover_request()

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        UserGroup = apps.get_model("user", "UserGroup")
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")

        cls.group = UserGroup.objects.create(name="empty-state-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)
        role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
        cls.user = CoreUser.objects.create_user(
            username="u24_empty_admin", password=PASSWORD, is_active=True,
            email="u24_empty_admin@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: cls.user, "group": cls.group})
        cls.user.roles.add(role)

    def setUp(self):
        _forget_leftover_request()
        super().setUp()
        self.client = Client(**NO_CACHE)

    def tearDown(self):
        super().tearDown()
        _forget_leftover_request()

    # ── ① 카메라 일괄 등록의 분모 ────────────────────────────────────────
    def test_address_gap_says_it_cannot_be_measured_at_zero(self):
        """★ 카메라 0대에서 비율은 **0% 가 아니라 「잴 수 없다」**다 (D-301).

        화면이 이 값을 보고 갈린다: 참이면 비율 카드, 거짓이면 빈 상태 한 장.
        종전에는 이 갈림이 없어서 **「0 / 0대」가 초록**으로 떴고, 초록 0 은 이 제품에서
        「다 채웠다」로 읽힌다 — 실제는 「아직 아무것도 없다」였다.
        """
        resp = self.client.get("/api/dsm/cameras/address-gap",
                               **_bearer(self.user))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        body = json.loads(resp.content)
        self.assertEqual(body["total"], 0, "이 테넌트에는 카메라가 없어야 한다")
        self.assertIs(body["measurable"], False)
        self.assertIsNone(body["coverage"],
                          "분모가 0 이면 비율은 **없다** — 0.0 으로 적지 않는다")

    # ── ② 보고서 0건 ────────────────────────────────────────────────────
    def test_report_runs_is_two_hundred_and_empty(self):
        """★ 0건은 **성공한 응답**이다. 오류와 같은 그림으로 그리면 안 되는 이유가 이것이다."""
        resp = self.client.get("/api/dsm/reports/runs", **_bearer(self.user))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        body = json.loads(resp.content)
        self.assertEqual(body.get("runs"), [],
                         "새 테넌트에는 실행 기록이 한 줄도 없어야 한다")

    # ── ③ 열람 청구 0건 (같은 화면의 표) ─────────────────────────────────
    def test_privacy_requests_is_two_hundred_and_empty(self):
        """청구 0건도 **200 + 빈 목록**이다. `unanswered` 가 0 으로 함께 온다."""
        resp = self.client.get("/api/dsm/law/privacy-requests?limit=10",
                               **_bearer(self.user))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        body = json.loads(resp.content)
        self.assertEqual(body.get("items"), [])
        self.assertEqual(body.get("total"), 0)
        self.assertEqual(body.get("unanswered"), 0,
                         "0건과 「안 셌다」를 가른다 — 화면이 이 수를 쓴다")
