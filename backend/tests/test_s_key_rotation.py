# -*- coding: utf-8 -*-
"""SEC-07 — 들어오는 키의 **발급 · 폐기 · 회전**이 실제로 서는가 (차선 S · 2026-09-26).

무엇을 재는가 — 다섯
--------------------
  ① 발급    만료 없는 키가 기본값으로 나오지 않는다
  ② 폐기    끊은 키는 **그 자리에서** 인증을 통과하지 못한다
  ③ 회전    새 키가 서고, **옛 키가 겹치는 창 동안 살아 있다** — 그리고 그 뒤에 죽는다
  ④ 격리    남의 테넌트 키는 만지지 못한다 (선등록 `common.key_rotation.rotate_key`)
  ⑤ 주기    「돌려야 할 때」를 도구가 말한다 — 그리고 **아무도 안 부르면 소용없다**는
            사실을 beat 가 갚는다

★ 왜 `verify_key()` 로 재는가
------------------------------
「끊었다」의 증거는 행의 `is_active=False` 가 아니라 **그 키로 더는 들어오지 못한다**이다.
행만 보면 dj-core 의 인증이 그 열을 안 볼 수도 있고, 그러면 우리는 끊었다고 믿고
상대는 계속 들어온다. 그래서 이 시험은 **제품이 인증에 쓰는 그 함수**를 부른다.
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone


class KeyFixture(TestCase):
    """테넌트 A/B · 각 테넌트의 관리자와 키 주인."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="key-tenant-A")
        cls.group_b = UserGroup.objects.create(name="key-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(
            created_by=None)

        cls.admin_a = cls._user("key_admin_a", cls.group_a, admin=True)
        cls.admin_b = cls._user("key_admin_b", cls.group_b, admin=True)
        cls.owner_a = cls._user("key_owner_a", cls.group_a)
        cls.owner_b = cls._user("key_owner_b", cls.group_b)

    @classmethod
    def _user(cls, username, group, *, admin=False):
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        if admin:
            from common.tenant_roles import tenant_admin_role_code

            #: 테넌트 관리자 역할 코드는 **group 마다 다르다** — 코드 문자열만 맞추면
            #: 남의 테넌트 admin 역할을 얻어 붙이는 경로가 열린다(tenant_roles 의 그 주석).
            code = tenant_admin_role_code(group.id)
            role = Role.objects.create(role_name=code, code=code)
            from kernels.k1_event.services import _owner_field

            if _owner_field(type(role)) == "groups":
                role.groups.set([group])
            else:
                role.group = group
                role.save(update_fields=["group"])
            user.roles.add(role)
        return user


class IssueTest(KeyFixture):
    """① 발급 — **만료 없는 키가 기본값으로 나오지 않는다.**"""

    def test_a_key_gets_an_expiry_even_when_nobody_asks(self) -> None:
        from common import key_rotation

        issued = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                        name="에스비 App")
        self.assertIsNotNone(
            issued.expires_at,
            "만료 없는 키가 기본값이면 회전 정책은 문서로만 존재합니다.")
        self.assertTrue(issued.plaintext, "원문이 없으면 상대에게 줄 것이 없습니다.")

    def test_a_nameless_key_is_refused(self) -> None:
        """이름 없는 키는 나중에 **어느 것을 끊을지** 못 고른다."""
        from common import key_rotation

        with self.assertRaises(ValueError):
            key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a, name="  ")

    def test_an_endless_key_is_refused_even_if_asked(self) -> None:
        from common import key_rotation

        with self.assertRaises(ValueError):
            key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                   name="영원한 키", expires_days=0)


class RevokeTest(KeyFixture):
    """② 폐기 — 끊은 키로는 **더는 들어오지 못한다.**"""

    def test_a_revoked_key_no_longer_authenticates(self) -> None:
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        issued = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                        name="끊을 키")
        row = InboundKey.objects.get(pk=issued.key_id)
        # ★ 양성 대조 — 끊기 **전에는** 통과해야 한다. 아니면 이 시험은 아무것도 안 잰다.
        self.assertTrue(row.verify_key(issued.plaintext))

        key_rotation.revoke_key(actor=self.admin_a, key_id=issued.key_id,
                                reason="유출 의심")
        row.refresh_from_db()
        self.assertFalse(
            row.verify_key(issued.plaintext),
            "끊었다고 적어 두고 그 키로 계속 들어올 수 있으면 끊은 것이 아닙니다.")

    def test_revoking_without_a_reason_is_refused(self) -> None:
        from common import key_rotation

        issued = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                        name="사유 없는 폐기")
        with self.assertRaises(ValueError):
            key_rotation.revoke_key(actor=self.admin_a, key_id=issued.key_id, reason="")

    def test_the_row_is_kept_not_deleted(self) -> None:
        """지우면 **그 키가 무엇을 했는지**가 함께 사라진다."""
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        issued = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                        name="남는 행")
        key_rotation.revoke_key(actor=self.admin_a, key_id=issued.key_id, reason="정리")
        self.assertTrue(InboundKey.objects.filter(pk=issued.key_id).exists())


class RotateTest(KeyFixture):
    """③ 회전 — **끊는 것이 아니라 겹치는 것**이다."""

    def test_the_old_key_survives_the_overlap_window(self) -> None:
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        old = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                     name="회전 대상")
        new = key_rotation.rotate_key(actor=self.admin_a, key_id=old.key_id,
                                      overlap_days=7)
        old_row = InboundKey.objects.get(pk=old.key_id)

        self.assertNotEqual(old.key_id, new.key_id)
        self.assertTrue(
            old_row.verify_key(old.plaintext),
            "회전하자마자 옛 키가 죽으면 그 순간 상대 연동이 끊깁니다 — "
            "그리고 끊긴 쪽에서는 우리 잘못으로 보이지 않습니다.")

    def test_the_old_key_dies_after_the_window(self) -> None:
        """겹치는 창은 **끝이 있어야** 창이다."""
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        old = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                     name="창이 닫힌다")
        key_rotation.rotate_key(actor=self.admin_a, key_id=old.key_id, overlap_days=7)
        old_row = InboundKey.objects.get(pk=old.key_id)
        old_row.expires_at = timezone.now() - timedelta(seconds=1)
        old_row.save(update_fields=["expires_at"])
        self.assertFalse(old_row.verify_key(old.plaintext))

    def test_rotation_never_extends_a_shorter_life(self) -> None:
        """회전이 **수명을 늘리는 일**이 되면 안 된다."""
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        old = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                     name="곧 죽을 키")
        row = InboundKey.objects.get(pk=old.key_id)
        soon = timezone.now() + timedelta(days=1)
        row.expires_at = soon
        row.save(update_fields=["expires_at"])

        key_rotation.rotate_key(actor=self.admin_a, key_id=old.key_id, overlap_days=30)
        row.refresh_from_db()
        self.assertLessEqual(row.expires_at, soon,
                             "겹치는 창이 옛 키의 수명을 늘렸습니다.")

    def test_a_dead_key_is_not_rotated(self) -> None:
        from common import key_rotation

        old = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                     name="이미 끊긴 키")
        key_rotation.revoke_key(actor=self.admin_a, key_id=old.key_id, reason="정리")
        with self.assertRaises(ValueError):
            key_rotation.rotate_key(actor=self.admin_a, key_id=old.key_id)


class TenantGuardTest(KeyFixture):
    """④ 격리 — **남의 테넌트 키는 만지지 못한다** (선등록이 경고한 자리).

    돌리면 그쪽 연동이 끊기고, **끊긴 쪽에서는 우리 잘못으로 보이지 않는다.**
    회전은 지우기보다 조용한 파괴다.
    """

    def _victim_key(self):
        from common import key_rotation

        return key_rotation.issue_key(actor=self.admin_b, owner=self.owner_b,
                                      name="B 테넌트 키")

    def test_another_tenants_key_cannot_be_rotated(self) -> None:
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        victim = self._victim_key()
        before = InboundKey.objects.count()
        with self.assertRaises(PermissionDenied):
            key_rotation.rotate_key(actor=self.admin_a, key_id=victim.key_id)
        # ★ 거절만으로는 모자라다 — **행이 안 늘었는가**까지 본다(D-290).
        self.assertEqual(before, InboundKey.objects.count(),
                         "거절했다면서 새 키가 만들어졌습니다.")
        row = InboundKey.objects.get(pk=victim.key_id)
        self.assertTrue(row.verify_key(victim.plaintext),
                        "거절했다면서 남의 키의 수명이 바뀌었습니다.")

    def test_another_tenants_key_cannot_be_revoked(self) -> None:
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        victim = self._victim_key()
        with self.assertRaises(PermissionDenied):
            key_rotation.revoke_key(actor=self.admin_a, key_id=victim.key_id,
                                    reason="남의 것")
        self.assertTrue(InboundKey.objects.get(pk=victim.key_id).is_active)

    def test_a_non_admin_cannot_issue(self) -> None:
        from common import key_rotation

        with self.assertRaises(PermissionDenied):
            key_rotation.issue_key(actor=self.owner_a, owner=self.owner_a,
                                   name="권한 없는 발급")

    def test_the_positive_control_still_passes(self) -> None:
        """★ 양성 대조 (D-277) — 전부 거절이면 그것은 「막았다」가 아니라
        「이 함수가 아무것도 못 한다」일 수 있다."""
        from common import key_rotation

        issued = key_rotation.issue_key(actor=self.admin_b, owner=self.owner_b,
                                        name="제 테넌트 발급")
        self.assertTrue(issued.plaintext)
        rotated = key_rotation.rotate_key(actor=self.admin_b, key_id=issued.key_id)
        self.assertNotEqual(issued.key_id, rotated.key_id)


class DuePolicyTest(KeyFixture):
    """⑤ 주기 — 「때가 됐다」를 도구가 말하는가. **그리고 그 말을 누가 듣는가.**"""

    def test_an_old_key_is_reported(self) -> None:
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        issued = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                        name="늙은 키")
        row = InboundKey.objects.get(pk=issued.key_id)
        InboundKey.objects.filter(pk=row.pk).update(
            created_at=timezone.now() - timedelta(days=key_rotation.KEY_MAX_AGE_DAYS + 1),
            expires_at=timezone.now() + timedelta(days=365))
        due = key_rotation.keys_due_for_rotation()
        self.assertIn(issued.key_id, [d.key_id for d in due])

    def test_a_fresh_key_is_not_reported(self) -> None:
        """★ 음성 대조 — 전부 「돌려야 한다」고 말하는 도구는 아무것도 안 재는 것이다."""
        from common import key_rotation

        issued = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                        name="갓 만든 키")
        due = key_rotation.keys_due_for_rotation()
        self.assertNotIn(issued.key_id, [d.key_id for d in due])

    def test_a_revoked_key_is_not_nagged_about(self) -> None:
        from common import key_rotation

        InboundKey = apps.get_model("apikey_account", "APIKey")
        issued = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                        name="끊긴 늙은 키")
        InboundKey.objects.filter(pk=issued.key_id).update(
            created_at=timezone.now() - timedelta(days=999))
        key_rotation.revoke_key(actor=self.admin_a, key_id=issued.key_id, reason="정리")
        self.assertNotIn(issued.key_id,
                         [d.key_id for d in key_rotation.keys_due_for_rotation()])

    def test_the_watch_beat_actually_calls_the_policy(self) -> None:
        """★ **잇는 것은 제품이 한다** (D-421 원칙).

        이 시험이 없으면 `keys_due_for_rotation` 은 「시험만 부르는 함수」가 되고,
        운영에서는 죽은 채로 초록이 난다. beat 를 직접 불러 **그 수가 나오는지** 본다.
        """
        from common.ops_tasks import key_rotation_watch_beat

        InboundKey = apps.get_model("apikey_account", "APIKey")
        from common import key_rotation

        issued = key_rotation.issue_key(actor=self.admin_a, owner=self.owner_a,
                                        name="beat 가 볼 키")
        InboundKey.objects.filter(pk=issued.key_id).update(
            created_at=timezone.now() - timedelta(days=key_rotation.KEY_MAX_AGE_DAYS + 5),
            expires_at=timezone.now() + timedelta(days=365))

        report = key_rotation_watch_beat()
        self.assertGreaterEqual(report["due"], 1)
        self.assertIn(issued.key_id, [k["key_id"] for k in report["keys"]])
        self.assertEqual(report["policy_days"], key_rotation.KEY_MAX_AGE_DAYS)
