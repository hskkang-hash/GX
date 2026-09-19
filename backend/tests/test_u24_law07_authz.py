# -*- coding: utf-8 -*-
"""P-185 / LAW-07′ — **열람 청구 다섯 문에 누가 지나가는가** (턴 W · 차선 U24).

세종 판정문 그대로
------------------
    U4(재난안전과)가 **열람 청구의 주인**이다. `privacy-requests` **다섯 문**을
    `tenant_admin` 대신 **역할 U4·U5 허용**(U2 제외 · 읽기 전용 U4 는 **접수·회신까지**,
    마스킹본 조회는 **감사 1행**). 「눌러도 403 나는 줄」 0.
    **권한 확장은 새 인증 경로가 아니다 — authz 표만.**

★ 이 파일이 묻는 것은 **둘 다**이다
-----------------------------------
넓힌 쪽(U4 가 지나간다)만 재면 그것은 증거가 아니다. 넓히면서 U2 까지 들어갔는지를
**같은 다섯 문에서** 재야 「요청만큼만 넓혔다」가 성립한다. 그래서 이 파일의 표는
**5문 × 3역할 = 15칸**이고, 열다섯 칸 전부를 두드린다.

★ 함수가 아니라 **문을 두드린다** (D-210)
-----------------------------------------
`_privacy_officer()` 를 직접 불러서 재면 그 앞에 선 `RoleGateMiddleware` 를 못 본다.
그리고 U4 가 막히던 실제 자리는 **그 미들웨어**였다(읽기 전용 역할의 쓰기 금지).
겹을 건너뛰고 잰 초록은 화면에서 빨강으로 나타난다 — 그래서 HTTP 로 두드린다.

★ 스레드에 남은 요청을 지운다
-----------------------------
이 저장소에서 「HTTP 를 때린 시험 뒤 `objects` 가 빈다」가 실제로 있었다. 그 오염이
다음 시험을 **거짓 초록**으로 만든다. `_CleanThreadLocal` 을 그대로 쓴다.

캐시 처리: 우회 — `Client(**NO_CACHE)` (`X-No-Cache` · D-341 착시 ⑦).
**관문을 재는 시험이 캐시를 재면 안 된다.** 이 파일은 같은 다섯 문을 역할 셋
(U4 · U2 · U5)으로 **잇달아** 두드린다. 적중 본문이 돌아오면 **앞 사람의 200 이
뒷사람의 200 으로 보이고**, 권한 시험에서 그것은 곧 거짓 통과다 —
「U2 는 403 이어야 한다」를 재는 줄이 조용히 초록이 된다.
"""
from __future__ import annotations

import contextlib
import json

from django.apps import apps
from django.test import Client, TestCase

from common import role_gate
from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PASSWORD = "u24-law07-test-only-not-a-secret"

#: 역할 코드 — **여기서 새로 짓지 않는다.** 제품이 쓰는 그 표에서 읽는다(D-212).
#: 읽어 온 값이 곧 시험의 값이므로, 표가 바뀌면 이 시험도 같이 움직인다.
from config.k3_roles import (  # noqa: E402  (표를 읽는 임포트를 머리에서 설명한 뒤에 둔다)
    K3_ROLE_EXECUTIVES,
    K3_ROLE_MANAGERS,
    K3_ROLE_SYSOPS,
)

U4_ROLE = K3_ROLE_EXECUTIVES[0]        # "view_only_-_anyang"  — 지자체 담당관
U2_ROLE = K3_ROLE_MANAGERS[0]          # "fire_admin"          — 관제팀장
U5_ROLE = K3_ROLE_SYSOPS[0]            # "admin"               — 운영자

BASE = "/api/dsm/law/privacy-requests"


def _forget_leftover_request() -> None:
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class _CleanThreadLocal:
    @classmethod
    def setUpClass(cls):
        _forget_leftover_request()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        _forget_leftover_request()

    def setUp(self):
        _forget_leftover_request()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        _forget_leftover_request()


class _Persona(_CleanThreadLocal, TestCase):
    """U2 · U4 · U5 세 사람을 **한 테넌트 안에** 세운다.

    ★ 셋 다 같은 소속이다. 테넌트가 갈리면 403 이 「역할 때문」인지 「남의 테넌트라서」
      인지 못 가린다 — 재는 축을 하나로 둔다.
    """

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        UserGroup = apps.get_model("user", "UserGroup")
        cls.group = UserGroup.objects.create(name="law07-authz-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)

        cls.u2 = cls._person("law07_u2", U2_ROLE)
        cls.u4 = cls._person("law07_u4", U4_ROLE)
        cls.u5 = cls._person("law07_u5", U5_ROLE)

    @classmethod
    def _person(cls, username, role_code):
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(
            code=role_code, defaults={"role_name": role_code})
        user = CoreUser.objects.create_user(
            username=username, password=PASSWORD, is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": cls.group})
        user.roles.add(role)
        return user

    def setUp(self):
        super().setUp()
        self.client = Client(**NO_CACHE)

    # ── 다섯 문 ──────────────────────────────────────────────────────────
    def door_list(self, who):
        return self.client.get(f"{BASE}?limit=10", **_bearer(who))

    def door_accept(self, who, *, name="김민수"):
        return self.client.post(
            f"{BASE}?subject_name={name}&contact=010-1234-5678&kind=%EC%97%B4%EB%9E%8C",
            data=b"", content_type="application/json", **_bearer(who))

    def door_detail(self, who, receipt_no):
        return self.client.get(f"{BASE}/{receipt_no}", **_bearer(who))

    def door_masked(self, who, receipt_no):
        return self.client.get(f"{BASE}/{receipt_no}/masked", **_bearer(who))

    def door_reply(self, who, receipt_no, text="확인해 드렸습니다."):
        return self.client.post(
            f"{BASE}/{receipt_no}/reply?text={text}",
            data=b"", content_type="application/json", **_bearer(who))

    def a_receipt(self):
        """**U5 가** 하나 접수해 둔다 — 뒤 세 문이 두드릴 번호가 필요하다."""
        resp = self.door_accept(self.u5, name="사전접수")
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        return json.loads(resp.content)["receipt_no"]


class FiveDoorsByRoleTest(_Persona):
    """★★ **5문 × 3역할 표.** 이 파일의 무게중심이다."""

    def test_u4_passes_all_five_doors(self):
        """넓힌 쪽 — **「눌러도 403 나는 줄」이 0** 이어야 한다."""
        receipt = self.a_receipt()
        got = {
            "목록":     self.door_list(self.u4).status_code,
            "접수":     self.door_accept(self.u4).status_code,
            "상세":     self.door_detail(self.u4, receipt).status_code,
            "마스킹본": self.door_masked(self.u4, receipt).status_code,
            "회신":     self.door_reply(self.u4, receipt).status_code,
        }
        self.assertEqual(got, {k: 200 for k in got}, f"U4 다섯 문: {got}")

    def test_u5_passes_all_five_doors(self):
        receipt = self.a_receipt()
        got = {
            "목록":     self.door_list(self.u5).status_code,
            "접수":     self.door_accept(self.u5).status_code,
            "상세":     self.door_detail(self.u5, receipt).status_code,
            "마스킹본": self.door_masked(self.u5, receipt).status_code,
            "회신":     self.door_reply(self.u5, receipt).status_code,
        }
        self.assertEqual(got, {k: 200 for k in got}, f"U5 다섯 문: {got}")

    def test_u2_is_still_403_on_all_five_doors(self):
        """★ **안 넓힌 쪽.** 한쪽만 보면 증거가 아니다 — 세종은 「U2 제외」를 적었다."""
        receipt = self.a_receipt()
        got = {
            "목록":     self.door_list(self.u2).status_code,
            "접수":     self.door_accept(self.u2).status_code,
            "상세":     self.door_detail(self.u2, receipt).status_code,
            "마스킹본": self.door_masked(self.u2, receipt).status_code,
            "회신":     self.door_reply(self.u2, receipt).status_code,
        }
        self.assertEqual(got, {k: 403 for k in got}, f"U2 다섯 문: {got}")

    def test_the_u2_refusal_says_who_can(self):
        """거절이 **누가 할 수 있는지**를 말한다 — 막힌 사람이 다음 수를 안다."""
        body = json.loads(self.door_list(self.u2).content)
        said = json.dumps(body, ensure_ascii=False)
        self.assertIn("지자체 담당관", said)
        self.assertNotIn(role_gate.READONLY_DENIAL_CODE, said,
                         "U2 는 읽기 전용이 아니다 — 사유를 섞으면 고칠 곳이 덮인다")


class WhatExactlyChangedTest(_Persona):
    """★★ **넓히기 전의 403 을 지금도 볼 수 있다** — 같은 순간 · 같은 계정 · 같은 토큰.

    조율자 경고: 「넓히기 전 403 을 못 봤으면, 넓힌 뒤 200 은 **무엇이 바뀌어서
    200 인지 모르는 200**이다.」 옳다. 그런데 서버를 되돌려 다시 잴 필요는 없다 —
    **옛 문지기(`_admin`)가 이 파일에 그대로 살아 있고 이웃 문들이 그것을 쓴다.**

    그래서 A/B 를 **같은 요청 한 벌 안에서** 잰다:
        A  `GET /api/dsm/law/purge/tenants`      ← 옛 문지기 `_admin`      → U4 **403**
        B  `GET /api/dsm/law/privacy-requests`   ← 새 문지기 `_privacy_officer` → U4 **200**
    계정도 토큰도 서버도 같고 **다른 것은 문지기 하나뿐**이다. 그러므로 200 의 원인은
    문지기다 — 자격이 바뀐 것도, 낡은 프로세스를 두드린 것도 아니다.
    """

    def test_the_old_gatekeeper_still_refuses_u4_right_now(self):
        """A — 옛 규칙을 쓰는 이웃 문은 **지금도** U4 에게 403 이다."""
        resp = self.client.get("/api/dsm/law/purge/tenants", **_bearer(self.u4))
        self.assertEqual(resp.status_code, 403,
                         "옛 문지기가 U4 를 통과시키면 A/B 가 성립하지 않는다")

    def test_the_new_gatekeeper_lets_u4_in_at_the_same_moment(self):
        """B — 같은 계정·같은 토큰으로 새 규칙의 문은 200 이다."""
        self.assertEqual(self.door_list(self.u4).status_code, 200)

    def test_u4_still_fails_the_old_condition(self):
        """★ **옛 조건은 여전히 거짓이다.** 200 은 옛 조건이 참이 돼서가 아니다.

        옛 `_admin` 은 `is_global_admin or is_tenant_admin` 하나였다. 둘 다 U4 에게
        지금도 거짓이다 — 즉 **계정·역할·소속에 한 줄도 안 썼다**(자격을 고쳐서
        통과시킨 것이 아니라 표를 고쳐서 통과시켰다).
        """
        from common.tenant_roles import is_global_admin, is_tenant_admin

        self.assertIs(is_global_admin(self.u4), False)
        self.assertIs(is_tenant_admin(self.u4), False)
        # 대조: U5 는 종전에도 지나갔다 — 넓힌 것이 U5 를 새로 들인 것이 아니다.
        self.assertIs(is_tenant_admin(self.u5), True)
        # 대조: U2 도 옛 조건이 거짓이고, **지금도 못 들어간다.**
        self.assertIs(is_tenant_admin(self.u2), False)
        self.assertEqual(self.door_list(self.u2).status_code, 403)


class NewAuthPathWasNotBuiltTest(_Persona):
    """★★ 「권한 확장은 **새 인증 경로가 아니다**」 — 그것을 시험이 못박는다."""

    #: ★ **런타임 레지스트리**로 센다 — grep 은 주석·문자열도 세고 동적 등록을 놓친다
    #:   (`common/tenant_scope.enumerate_operations` 머리말).
    EXPECTED_DOORS = {
        ("GET", "/api/dsm/law/privacy-requests"),
        ("POST", "/api/dsm/law/privacy-requests"),
        ("GET", "/api/dsm/law/privacy-requests/{receipt_no}"),
        ("GET", "/api/dsm/law/privacy-requests/{receipt_no}/masked"),
        ("POST", "/api/dsm/law/privacy-requests/{receipt_no}/reply"),
    }

    def _doors(self):
        from common.tenant_scope import enumerate_operations

        return [r for r in enumerate_operations()
                if r.path.startswith("/api/dsm/law/privacy-requests")]

    def test_the_five_doors_are_still_exactly_five(self):
        """문이 **늘지 않았다.** 경로와 메서드가 종전 그대로 다섯이다."""
        got = {(r.method, r.path) for r in self._doors()}
        self.assertEqual(got, self.EXPECTED_DOORS,
                         "새 문이 났거나 문이 사라졌다 — 둘 다 빨강이다")

    def test_no_second_authenticator_was_added(self):
        """다섯 문이 전부 **종전의 그 인증기 하나**를 그대로 쓴다.

        `has_auth` 가 참이라는 것은 라우트에 인증 콜백이 걸려 있다는 뜻이다.
        권한을 넓히면서 인증을 벗긴 문이 하나라도 있으면 여기서 빨강이 난다.
        """
        for door in self._doors():
            with self.subTest(door=f"{door.method} {door.path}"):
                self.assertTrue(door.has_auth,
                                "인증 없는 문이 났다 — 그것이 「새 인증 경로」다")
                self.assertEqual(door.module, "apps.dsm.law_api",
                                 "다섯 문은 종전 그 파일에 그대로 있다")

    def test_an_anonymous_call_is_still_not_authenticated(self):
        """★ 넓힌 것은 **역할**이지 익명이 아니다."""
        self.assertIn(self.client.get(f"{BASE}?limit=10").status_code, (401, 403))

    def test_a_role_zero_account_still_sees_nothing(self):
        """역할 0 은 종전 그대로 `role_required` 다 — 이 확장이 그 관문을 안 건드렸다."""
        CoreUser = apps.get_model("user", "CoreUser")
        zero = CoreUser.objects.create_user(
            username="law07_zero", password=PASSWORD, is_active=True,
            email="law07_zero@test.invalid")
        resp = self.door_list(zero)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(json.loads(resp.content).get("code"),
                         role_gate.DENIAL_CODE)


class ReadOnlyGateWasNotOpenedWideTest(_Persona):
    """★★ 읽기 전용의 쓰기 금지는 **청구 면 둘**에서만 비켰다."""

    def test_u4_write_is_still_403_outside_the_two_doors(self):
        """U4#15 의 그 자리 — `upper-report` 는 **여전히 막힌다.**

        ★ 실재하지 않는 id 로 두드린다. 실재 사건 id 로 쓰기 면을 때리는 것이 곧
          두 번째 오염이다(`role_gate.py` P-119 주석의 그 규율).
        """
        resp = self.client.post("/api/dsm/events/999999999/upper-report",
                                data=b"{}", content_type="application/json",
                                **_bearer(self.u4))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(json.loads(resp.content).get("code"),
                         role_gate.READONLY_DENIAL_CODE)

    def test_retention_sweep_is_still_403_for_u4(self):
        """넓힌 것은 `_privacy_officer` 뿐 — `_admin` 은 손대지 않았다."""
        resp = self.client.post("/api/dsm/law/retention/sweep?dry_run=true",
                                data=b"{}", content_type="application/json",
                                **_bearer(self.u4))
        self.assertEqual(resp.status_code, 403)

    def test_the_pattern_list_is_exactly_two_shapes(self):
        """**순수 함수로** 재는 칸 — 요청 객체 없이 모양만 본다."""
        allow = role_gate.is_readonly_allowed_path
        self.assertTrue(allow("/api/dsm/law/privacy-requests"))
        self.assertTrue(allow("/api/dsm/law/privacy-requests/GX-PR-20260919-AB12CD/reply"))
        # 아래는 **비키지 않는다** — 넓은 규칙이었다면 여기가 전부 열린다.
        self.assertFalse(allow("/api/dsm/law/privacy-requests/GX-PR-1/masked"))
        self.assertFalse(allow("/api/dsm/law/privacy-requests/a/b/reply"))
        self.assertFalse(allow("/api/dsm/law/retention/sweep"))
        self.assertFalse(allow("/api/dsm/events/1/upper-report"))

    def test_role_zero_does_not_get_the_two_doors(self):
        """★ 두 목록은 **따로다.** 읽기 전용에 연 것이 역할 0 에 열리면 안 된다."""
        self.assertFalse(role_gate.is_allowed_path(
            "/api/dsm/law/privacy-requests"))
        self.assertFalse(role_gate.is_allowed_path(
            "/api/dsm/law/privacy-requests/GX-PR-1/reply"))


class U4CannotBeGreenOnUpperReportTest(_Persona):
    """★★ **U4#15 정본 정정의 증거** (세종 P-190 · 이 턴에 문서를 고치는 것은 Q 차선).

    U4#15 「상급기관 제출 자료」의 셋째 술어는
    `POST /api/dsm/events/{id}/upper-report` **200** 이다. 그런데 U4 의 역할 코드는
    `view_only_-_anyang` 이고 P-119 관문이 읽기 전용의 **쓰기 전부**를 막는다.
    즉 **U4 로는 이 행이 구조적으로 ● 가 될 수 없다** — 화면을 고쳐도, 문구를 고쳐도,
    다시 눌러도 안 된다. 그리고 그 403 은 **제품이 옳게 막은 자리**다(고칠 흠이 아니다).

    그래서 재는 축을 U2 로 옮긴다. 이 시험이 그 두 축을 **같은 순간 같은 문에서** 잰다.
    한 축만 재면 「U4 가 막힌다」까지만 알고 「그럼 어디서 재나」는 모른다.
    """

    UPPER = "/api/dsm/events/999999999/upper-report"
    #: ★ **실재하지 않는 id 로 두드린다.** 실재 사건 id 로 쓰기 면을 때리는 것이
    #:   곧 오염이다(role_gate P-119 주석이 적어 둔 그 사고).

    def _press(self, who):
        return self.client.post(self.UPPER, data=b"{}",
                                content_type="application/json", **_bearer(who))

    def test_u4_is_stopped_by_the_gate_not_by_the_handler(self):
        """U4 축 — **관문**이 403 을 낸다. 핸들러까지 가지도 못한다."""
        resp = self._press(self.u4)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(json.loads(resp.content).get("code"),
                         role_gate.READONLY_DENIAL_CODE,
                         "읽기 전용 관문이 낸 403 이어야 한다 — 권한 표가 아니다")

    def test_u2_gets_past_the_gate(self):
        """U2 축 — **관문을 지난다.** 지나서 404(없는 사건)를 받는다.

        ★ 404 가 곧 「핸들러가 돌았다」의 눈금이다(P-83 의 그 눈금). 403 이 아니라
          404 라는 것이 「이 사람은 이 문을 쓸 수 있고, 다만 그 사건이 없다」는 뜻이다.
          실재 사건으로 누르면 200 이 나올 자리이고, 그것이 U4#15 의 새 축이다.
        """
        resp = self._press(self.u2)
        self.assertNotEqual(resp.status_code, 403,
                            "U2 는 읽기 전용이 아니다 — 여기서 막히면 축을 옮길 수 없다")
        self.assertIn(resp.status_code, (404, 422),
                      f"관문을 지나 핸들러가 돌아야 한다 — 받은 것: {resp.status_code}")

    def test_read_only_accounts_are_exactly_the_u4_role(self):
        """왜 U4 만 막히나 — **역할 코드가 `view_only` 로 시작하기 때문**이다."""
        from common.role_gate import is_read_only

        self.assertIs(is_read_only(self.u4), True)
        self.assertIs(is_read_only(self.u2), False)
        self.assertIs(is_read_only(self.u5), False)


class MaskedViewLeavesOneAuditRowTest(_Persona):
    """★★ 「마스킹본 조회는 **감사 1행**」 — 남게 만든 것이 아니라 **남은 것을 본다.**"""

    def _rows(self):
        from apps.dsm.privacy_request import ACTION_VIEW, LOGGER_NAME

        return apps.get_model("logger", "AuditLogs")._base_manager.filter(
            logger_name=LOGGER_NAME, api_name=ACTION_VIEW)

    def test_one_masked_view_leaves_exactly_one_row(self):
        receipt = self.a_receipt()
        before = self._rows().count()
        resp = self.door_masked(self.u4, receipt)
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        after = self._rows().count()
        self.assertEqual(after - before, 1, "마스킹본 조회 1회 = 감사 1행")

    def test_the_row_names_the_receipt_and_the_viewer(self):
        """행이 **누가 · 어느 청구를** 보았는지 말한다. 말하지 않으면 감사가 아니다."""
        from apps.dsm.privacy_request import PAYLOAD_KEY

        receipt = self.a_receipt()
        self.assertEqual(self.door_masked(self.u4, receipt).status_code, 200)
        row = self._rows().order_by("-id").first()
        self.assertIsNotNone(row)
        payload = (row.data_after or {}).get(PAYLOAD_KEY) or {}
        self.assertEqual(payload.get("receipt_no"), receipt)
        self.assertIn("viewed_at", payload)
        self.assertEqual(str(row.username or ""), self.u4.username)

    def test_a_refused_view_leaves_no_row(self):
        """★ **음성 대조** — 403 은 조회가 아니다. 막힌 것이 대장에 남으면 수가 거짓이 된다."""
        receipt = self.a_receipt()
        before = self._rows().count()
        self.assertEqual(self.door_masked(self.u2, receipt).status_code, 403)
        self.assertEqual(self._rows().count(), before)
