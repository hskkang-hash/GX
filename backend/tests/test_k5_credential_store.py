# -*- coding: utf-8 -*-
"""K5 표 ② 자격증명 저장처 — **F-05 「API Key 발급·폐기」 · F-12 「API키」** (D-325 · D-328).

이 시험이 묻는 것 넷
--------------------
    ① **값이 어디에도 없는가**            모델에 값 칸이 없다. 조회는 언제나 마스킹
    ② **「있다」와 「무엇인지 안다」가 갈리는가**  상태 5값. `present` 와 `typed` 사이가 juso 사건
    ③ **모르는 키를 기능 코드가 못 쓰는가**  `secret_for` 가 두 조건에서 멈춘다
    ④ **조회가 감사에 남는가**            누가 무엇을 물어봤는지가 남는다

★ 출생 사건 (2026-09-05~06)
---------------------------
대표께서 승인키 2건을 발급하셨다. 우리는 **「키가 있는가」만 물었고 「어떤 키인가」는
묻지 않았다.** 받은 것은 도로명주소 **팝업 API** 키 — 브라우저 UI 위젯이지 서버 조회
API 조차 아니었다. 그 하루가 `present` 와 `typed` 사이다.
"""
from __future__ import annotations

from unittest import mock

from django.test import TestCase

from tests.test_dsm_app import DsmFixture


def _sys():
    """조회 갈래만 보는 시험용 스코프. **값을 내주는 갈래는 실제 사용자 스코프로 잰다.**"""
    from common.tenant_scope import TenantScope

    return TenantScope.system(reason="표 ② 사실 조회 시험 — 값이 아니라 상태를 본다")


class CredentialStoreShapeTest(TestCase):
    """표의 모양 — **값을 담을 칸이 없다.**"""

    def test_the_model_has_no_place_to_put_a_value(self) -> None:
        """★ D-204 · D-319 — "마스킹해서 저장" 은 저장이다. **칸 자체를 만들지 않는다.**

        칸이 있으면 언젠가 채워지고, 채워진 값은 덤프·백업·화면·로그로 흘러나간다.
        """
        from django.apps import apps

        Model = apps.get_model("stream_monitors", "CredentialRecord")
        names = {f.name for f in Model._meta.get_fields()}
        for forbidden in ("value", "secret", "key_value", "token", "password"):
            self.assertNotIn(forbidden, names,
                             f"표 ②에 {forbidden} 칸이 생겼습니다 — 값은 담지 않습니다.")

    def test_the_status_enum_has_the_typed_step(self) -> None:
        """★ D-328 — 4값이 아니라 **5값**이다. 빠진 한 칸이 juso 사건이었다."""
        from django.apps import apps

        Model = apps.get_model("stream_monitors", "CredentialRecord")
        values = {c[0] for c in Model._meta.get_field("status").choices}
        self.assertEqual({"absent", "present", "typed", "verified", "rotated"}, values)

    def test_every_declared_credential_says_what_it_can_do(self) -> None:
        """`api_type` 과 `capability` — 이 두 칸이 없어서 하루를 잃었다."""
        from kernels.k5_trust.credentials import CREDENTIALS

        self.assertTrue(CREDENTIALS)
        for name, spec in CREDENTIALS.items():
            with self.subTest(name=name):
                self.assertTrue(spec.api_type.strip(),
                                "발급처가 부르는 이름 그대로 적습니다.")
                self.assertTrue(spec.capability.strip(),
                                "이 키로 무엇을 할 수 있는지가 없으면 또 같은 일이 납니다.")

    def test_the_popup_key_records_that_it_cannot_do_server_lookup(self) -> None:
        """★ 출생 표본 — 그 하루의 사실이 표에 문자열로 박혀 있다."""
        from kernels.k5_trust.credentials import CREDENTIALS

        spec = CREDENTIALS["JUSO_POPUP_KEY_1"]
        self.assertIn("팝업", spec.api_type)
        self.assertIn("서버 조회 불가", spec.capability)
        self.assertFalse(spec.is_secret,
                         "팝업 키는 브라우저에 노출되는 공개 클라이언트 키입니다 (D-331).")


class CredentialObservationTest(TestCase):
    """② 「있다」와 「무엇인지 안다」는 다른 사실이다 (D-323 · D-328)."""

    def test_absent_when_this_environment_does_not_have_it(self) -> None:
        """**발급 완료 ≠ 전달 완료 ≠ 환경 존재** — 이 환경을 본다 (D-316)."""
        from kernels.k5_trust import credential_fact

        with mock.patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("JUSO_POPUP_KEY_1", None)
            fact = credential_fact(scope=_sys(), name="JUSO_POPUP_KEY_1")
        self.assertEqual("absent", fact["observed_status"])
        self.assertEqual("", fact["masked"], "없는 키에서 마스킹 흔적이 나오면 안 됩니다.")

    def test_declared_and_observed_are_two_columns(self) -> None:
        """선언(우리가 안다고 적은 것)과 관찰(이 환경이 말하는 것)을 한 칸에 두지 않는다."""
        from kernels.k5_trust import credential_fact

        import os

        os.environ.pop("JUSO_POPUP_KEY_1", None)
        fact = credential_fact(scope=_sys(), name="JUSO_POPUP_KEY_1")
        self.assertEqual("typed", fact["declared_status"])
        self.assertEqual("absent", fact["observed_status"])

    def test_the_lookup_is_always_masked(self) -> None:
        from kernels.k5_trust import credential_fact

        with mock.patch.dict("os.environ",
                             {"JUSO_POPUP_KEY_1": "ABCDEFGHIJKLMNOP"}):
            fact = credential_fact(scope=_sys(), name="JUSO_POPUP_KEY_1")
        self.assertNotIn("CDEFGHIJKLMN", fact["masked"])
        self.assertTrue(fact["masked"].startswith("AB"))
        self.assertTrue(fact["masked"].endswith("OP"))

    def test_an_undeclared_name_is_refused(self) -> None:
        from kernels.k5_trust import CredentialNotDeclared, credential_fact

        with self.assertRaises(CredentialNotDeclared):
            credential_fact(scope=_sys(), name="SOME_KEY_NOBODY_DECLARED")


class CredentialUsageGateTest(DsmFixture):
    """③④ 모르는 키는 못 쓰고, 물어본 사실은 남는다."""

    def test_a_key_below_typed_is_refused_to_feature_code(self) -> None:
        """★ 출생 표본 — 이 갈래가 있었다면 juso 하루를 잃지 않았다 (D-328)."""
        from kernels.k5_trust import CredentialNotUsable, secret_for

        with mock.patch.dict("os.environ", {"DATA_GO_KR_KEY_DECODED": "abcdefghijkl"}):
            with self.assertRaises(CredentialNotUsable):
                secret_for("DATA_GO_KR_KEY_DECODED", scope=self.scope_a)

    def test_a_typed_key_with_capability_is_handed_over(self) -> None:
        from kernels.k5_trust import secret_for

        with mock.patch.dict("os.environ", {"JUSO_POPUP_KEY_1": "abcdefghijkl"}):
            self.assertEqual("abcdefghijkl",
                             secret_for("JUSO_POPUP_KEY_1", scope=self.scope_a))

    def test_an_absent_key_is_refused_even_if_typed(self) -> None:
        """선언이 typed 여도 **이 환경에 없으면** 못 쓴다 (D-316)."""
        from kernels.k5_trust import CredentialNotUsable, secret_for

        import os

        os.environ.pop("JUSO_POPUP_KEY_1", None)
        with self.assertRaises(CredentialNotUsable):
            secret_for("JUSO_POPUP_KEY_1", scope=self.scope_a)

    def test_both_the_grant_and_the_refusal_are_audited(self) -> None:
        """차단만 남기면 「시도가 없었다」와 「시도가 막혔다」가 같아진다 (AC-12 계열)."""
        from kernels.k5_trust import CredentialNotUsable, audit, secret_for

        with mock.patch.dict("os.environ", {"JUSO_POPUP_KEY_1": "abcdefghijkl",
                                            "DATA_GO_KR_KEY_DECODED": "abcdefghijkl"}):
            secret_for("JUSO_POPUP_KEY_1", scope=self.scope_a)
            with self.assertRaises(CredentialNotUsable):
                secret_for("DATA_GO_KR_KEY_DECODED", scope=self.scope_a)
        rows = audit._entries()
        outcomes = {r.action: r.outcome for r in rows}
        self.assertEqual(audit.ALLOWED, outcomes["read:JUSO_POPUP_KEY_1"])
        self.assertEqual(audit.DENIED, outcomes["read:DATA_GO_KR_KEY_DECODED"])

    def test_no_audit_row_carries_the_value(self) -> None:
        """감사에 값이 실리면 감사가 곧 유출 경로가 된다."""
        from kernels.k5_trust import audit, secret_for

        with mock.patch.dict("os.environ", {"JUSO_POPUP_KEY_1": "SUPERSECRETVALUE"}):
            secret_for("JUSO_POPUP_KEY_1", scope=self.scope_a)
        for row in audit._entries():
            self.assertNotIn("SUPERSECRETVALUE", row.reason)
            self.assertNotIn("SUPERSECRETVALUE", row.action)

    def test_refresh_writes_the_verification_columns(self) -> None:
        """★ D-323 · D-325 — `verified_at`/`verified_by` 는 이제 **조회 결과**다.

        손으로 적는 칸이면 그것은 진술이고, 진술은 잠금을 내리지 못한다.
        """
        from django.apps import apps

        from kernels.k5_trust import refresh_credential

        with mock.patch.dict("os.environ", {"JUSO_POPUP_KEY_1": "abcdefghijkl"}):
            out = refresh_credential(scope=self.scope_a, name="JUSO_POPUP_KEY_1",
                                     verified_by="환경변수 존재 확인")
        self.assertEqual("typed", out["status"])
        row = apps.get_model("stream_monitors", "CredentialRecord").objects.get(
            name="JUSO_POPUP_KEY_1")
        self.assertIsNotNone(row.verified_at)
        self.assertEqual("환경변수 존재 확인", row.verified_by)


class CredentialSettingSurfaceTest(DsmFixture):
    """F-12 「API키」·「임계값」 — 설정 면에서 **사유 있는 501 이 아니라 표가 나온다.**"""

    def setUp(self) -> None:
        super().setUp()
        from common.tenant_roles import tenant_admin_role_code

        self.user_a.roles.add(self._own(
            self._role(tenant_admin_role_code(self.group_a.pk)), self.group_a))
        self.user_a.refresh_from_db()

    def test_the_api_keys_domain_returns_the_table_not_a_501(self) -> None:
        from apps.dsm import services

        out = services.setting_overview(scope=self.scope_a, domain="api_keys")
        self.assertIn("api_keys", out)
        self.assertTrue(out["api_keys"])
        for row in out["api_keys"]:
            self.assertNotIn("value", row, "설정 면에 값이 나오면 안 됩니다.")

    def test_the_thresholds_domain_returns_the_table_too(self) -> None:
        from apps.dsm import services

        out = services.setting_overview(scope=self.scope_a, domain="thresholds")
        self.assertTrue(out["thresholds"])
        self.assertIn("history", out)
