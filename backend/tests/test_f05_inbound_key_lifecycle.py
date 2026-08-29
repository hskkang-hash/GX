# -*- coding: utf-8 -*-
"""계약 F-05 「API Key **발급·폐기** 포함」 · F-12 「API키」 — 세 번 미뤄진 절 (D-367).

이 파일이 재는 것과 안 재는 것
------------------------------
    잰다   발급 · 폐기 · 회전 · 목록 — **네 동작이 실제로 도는가**
           전부 **테넌트 귀속**인가 · 값이 **한 번만** 나가는가 · 무권한이 막히는가
    안 잰다 인증 자체 — `test_f05_inbound_api_key.py` 가 잰다. 그 파일은 **소비 면**
           (키를 들고 오면 어디에 닿는가)이고 이 파일은 **발급 면**이다.
           둘을 한 파일에 두면 "키가 통한다" 와 "키를 만들 수 있다" 가 섞인다 —
           그 섞임이 이 절을 두 번 잘못 판정하게 한 원인이었다(D-335 · D-337).

★ 왜 이 절이 세 번 미뤄졌나 — 그 내력이 이 시험의 설계다
--------------------------------------------------------
    2026-09-06  표 ②(나가는 키)가 갚을 줄 알았다 → **방향이 반대**였다 (D-337)
    2026-09-07  인증은 이미 성했고 **범위**가 문제였다 → 좁혔으나 그건 소비 면 (D-335)
    2026-09-10  남은 하나 — **발급·폐기의 면.** 이 파일

그래서 첫 갈래가 `test_the_two_directions_are_not_the_same_thing` 이다.
그 혼동이 이 절을 두 번 잘못 판정하게 했으므로, 시험이 그 구별을 기억한다 (D-310).

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from common.tenant_scope import TenantScope


class InboundKeyFixture(TestCase):
    """테넌트 A/B · 각각 관리자 하나. `DsmFixture` 규약을 따른다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="key-tenant-A")
        cls.group_b = UserGroup.objects.create(name="key-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("key_user_a", cls.group_a, admin=True)
        cls.user_b = cls._user("key_user_b", cls.group_b, admin=True)
        #: 관리자가 **아닌** 사람 — 무권한 갈래의 표본
        cls.plain_a = cls._user("key_plain_a", cls.group_a, admin=False)

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.plain_scope = TenantScope.of(cls.plain_a)

    @staticmethod
    def _own(obj, group):
        from kernels.k1_event.services import _owner_field

        if _owner_field(type(obj)) == "groups":
            obj.groups.set([group])
        else:
            obj.group = group
            obj.save(update_fields=["group"])
        return obj

    @classmethod
    def _user(cls, username, group, *, admin: bool):
        from common.tenant_roles import tenant_admin_role_code

        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        code = tenant_admin_role_code(group.pk) if admin else f"watch_{username}"
        user.roles.add(cls._own(Role.objects.create(role_name=code, code=code), group))
        user.refresh_from_db()
        return user


class TwoDirectionsTest(TestCase):
    """★ **출생 표본** (D-310) — 이 절을 두 번 잘못 판정하게 한 그 혼동."""

    def test_the_two_directions_are_not_the_same_thing(self) -> None:
        """나가는 키(표 ②)와 들어오는 키는 **다른 것**이다.

        둘 다 "API Key" 라 불려서 2026-09-06 에 한 번 같은 것으로 읽혔다(D-337).
        표 ②가 섰을 때 이 절을 올렸다면 그 순간 대장이 거짓말을 시작했을 것이다.
        """
        from kernels.k5_trust import credentials, inbound_keys

        #: 표 ②는 **환경변수**의 표다 — 테넌트별 행이 아니다
        self.assertTrue(credentials.CREDENTIALS,
                        "표 ②가 비었습니다 — 대조가 성립하지 않습니다.")
        for name, definition in credentials.CREDENTIALS.items():
            self.assertTrue(
                definition.env_var,
                f"표 ②의 '{name}' 에 env_var 가 없습니다 — 표 ②는 환경변수의 표이고, "
                f"그 성질이 들어오는 키와 갈리는 자리입니다.")

        #: 들어오는 키에는 env_var 가 **없다.** DB 행이고 테넌트에 묶인다
        self.assertNotIn(
            "env_var", {f for f in inbound_keys.InboundKeyView.__dataclass_fields__},
            "들어오는 키에 env_var 칸이 생겼습니다 — 표 ②와 섞이고 있습니다(D-337).")
        self.assertIn(
            "group_id", inbound_keys.InboundKeyView.__dataclass_fields__,
            "들어오는 키에 테넌트 칸이 없습니다 — dj-core 가 모르는 그 칸이 "
            "우리가 더하는 것의 전부입니다.")

    def test_neither_direction_carries_a_value_field(self) -> None:
        """★ 어느 방향도 **값 칸을 갖지 않는다** (D-204 · D-319).

        "마스킹해서 저장" 은 저장이다. 칸이 있으면 언젠가 채워지고, 채워진 값은
        덤프·백업·화면·로그로 흘러나간다.
        """
        from kernels.k5_trust import inbound_keys

        for field in inbound_keys.InboundKeyView.__dataclass_fields__:
            self.assertNotIn(
                field, ("secret", "key", "value", "key_hash", "token"),
                f"조회 값에 '{field}' 칸이 있습니다 — 값이 나가는 자리가 생겼습니다.")


class IssueAndRevokeTest(InboundKeyFixture):
    """★ **계약 절 본체** — 발급·폐기가 실제로 돈다."""

    def test_f05_issue_and_revoke_contract_ac(self) -> None:
        """★ 계약 AC — 「API Key **발급·폐기**」. 두 동작을 한 시험에서 잇는다.

        발급만 재고 폐기를 안 재면 "발급은 되는데 못 끄는 키" 가 초록으로 들어온다 —
        끌 수 없는 키는 **영원한 키**이고, 그것이 이 절이 계약에 들어간 이유다.
        """
        from kernels.k5_trust import issue_key, revoke_key

        issued = issue_key(scope=self.scope_a, name="에스비 연계 App")
        self.assertTrue(issued.secret, "발급됐는데 값이 안 나왔습니다.")
        self.assertTrue(issued.view.is_active)
        self.assertEqual(issued.view.group_id, self.group_a.pk,
                         "발급된 키가 테넌트에 안 묶였습니다 — dj-core 는 이 칸을 "
                         "모르므로 우리가 안 묶으면 아무도 안 묶습니다.")

        revoked = revoke_key(scope=self.scope_a, key_id=issued.view.key_id)
        self.assertFalse(revoked.is_active, "폐기했는데 살아 있습니다.")

        APIKey = apps.get_model("apikey_account", "APIKey")
        self.assertTrue(
            APIKey.objects.filter(pk=issued.view.key_id).exists(),
            "폐기가 행을 지웠습니다 — '언제부터 없었나' 가 사라집니다. "
            "사고 조사에 필요한 것은 '지금 없다' 가 아닙니다.")

    def test_the_secret_is_shown_exactly_once(self) -> None:
        """★ 값은 **발급 순간 한 번만.** 조회에는 두 번 다시 안 나온다.

        저장소가 원문을 갖지 않으므로(sha256 해시만) 이것은 정책이 아니라 **성질**이다.
        조회에 값이 실리는 순간 그 성질이 깨졌다는 뜻이다.
        """
        from kernels.k5_trust import issue_key, list_keys

        issued = issue_key(scope=self.scope_a, name="한 번만")
        rows = list_keys(scope=self.scope_a)
        found = [r for r in rows if r.key_id == issued.view.key_id]
        self.assertEqual(len(found), 1)

        serialized = repr(found[0])
        self.assertNotIn(issued.secret, serialized,
                         "조회 결과에 키 값이 실려 있습니다.")
        self.assertIn(found[0].prefix, issued.secret,
                      "prefix 가 그 키의 것이 아닙니다 — 사람이 '그 키' 를 못 지목합니다.")

    def test_an_unnamed_key_is_refused(self) -> None:
        """이름 없는 키는 발급하지 않는다 — 폐기할 때 어느 키인지 못 고른다."""
        from kernels.k5_trust import issue_key

        with self.assertRaises(ValueError):
            issue_key(scope=self.scope_a, name="   ")

    def test_a_zero_expiry_is_refused_not_read_as_forever(self) -> None:
        """★ `expires_days=0` 은 「무기한」이 아니라 **「이미 만료」**다.

        조용히 무기한으로 읽으면 끄려던 키가 영원한 키가 된다 — 뜻이 정반대인
        두 값을 한 입력에 두지 않는다(D-290).
        """
        from kernels.k5_trust import issue_key

        with self.assertRaises(ValueError):
            issue_key(scope=self.scope_a, name="영일짜리", expires_days=0)

    def test_rotation_replaces_and_marks_the_old_one(self) -> None:
        """회전 — 새 키가 나오고 **옛 키는 `rotated` 로 남는다.**

        `absent`(폐기됨)와 다른 값인 이유: 뒤엣것은 **후속 키가 있다**는 뜻이고,
        앞엣것은 그냥 없어진 것이다. 두 사실을 한 값에 두면 "왜 껐나" 를 못 읽는다.
        """
        from kernels.k5_trust import list_keys, rotate_key
        from kernels.k5_trust.credentials import ROTATED

        from kernels.k5_trust import issue_key

        first = issue_key(scope=self.scope_a, name="회전 대상")
        second = rotate_key(scope=self.scope_a, key_id=first.view.key_id)

        self.assertNotEqual(first.view.key_id, second.view.key_id)
        self.assertNotEqual(first.secret, second.secret)
        self.assertEqual(second.view.name, "회전 대상",
                         "회전 뒤 이름이 바뀌었습니다 — 같은 용도의 키인데 화면에서 "
                         "다른 키로 보입니다.")

        by_id = {k.key_id: k for k in list_keys(scope=self.scope_a)}
        self.assertEqual(by_id[first.view.key_id].status, ROTATED)
        self.assertTrue(by_id[second.view.key_id].is_active)

    def test_revoked_keys_stay_in_the_list(self) -> None:
        """폐기된 키가 목록에서 **사라지지 않는다.**

        빼면 "폐기했다" 가 화면에서 "없었다" 와 같은 그림이 되고, 폐기 이력을
        아무도 못 읽는다 (D-290).
        """
        from kernels.k5_trust import issue_key, list_keys, revoke_key

        issued = issue_key(scope=self.scope_a, name="꺼진 키")
        revoke_key(scope=self.scope_a, key_id=issued.view.key_id)

        ids = [k.key_id for k in list_keys(scope=self.scope_a)]
        self.assertIn(issued.view.key_id, ids)
        self.assertNotIn(
            issued.view.key_id,
            [k.key_id for k in list_keys(scope=self.scope_a, include_inactive=False)],
            "include_inactive=False 인데도 꺼진 키가 나옵니다 — 그 인자가 무의미합니다.")


class KeysAreBoundToTheTenantTest(InboundKeyFixture):
    """★ **전부 테넌트 귀속** (지시 D-360 ③). dj-core 가 모르는 그 칸이 여기서 선다."""

    def test_another_tenants_key_is_invisible(self) -> None:
        from kernels.k5_trust import issue_key, list_keys

        mine = issue_key(scope=self.scope_a, name="내 키")
        theirs = issue_key(scope=self.scope_b, name="남의 키")

        mine_ids = [k.key_id for k in list_keys(scope=self.scope_a)]
        self.assertIn(mine.view.key_id, mine_ids)
        self.assertNotIn(theirs.view.key_id, mine_ids,
                         "남의 테넌트 키가 내 목록에 보입니다.")

    def test_another_tenants_key_cannot_be_revoked(self) -> None:
        """★ 남의 키는 **없는 것으로** 답한다 — 403 이 아니다 (D-269).

        403 은 "있는데 못 만진다" 를 알려 주고, 그것만으로 남의 테넌트에 그 id 가
        있다는 사실이 샌다.
        """
        from kernels.k5_trust import InboundKeyNotFound, issue_key, revoke_key

        theirs = issue_key(scope=self.scope_b, name="남의 키")
        with self.assertRaises(InboundKeyNotFound):
            revoke_key(scope=self.scope_a, key_id=theirs.view.key_id)

        APIKey = apps.get_model("apikey_account", "APIKey")
        self.assertTrue(APIKey.objects.get(pk=theirs.view.key_id).is_active,
                        "남의 키가 실제로 꺼졌습니다 — 거부 응답과 DB 가 갈렸습니다.")

    def test_another_tenants_key_cannot_be_rotated(self) -> None:
        """회전은 **폐기 + 발급**이므로 폐기 쪽만 막으면 안 된다 — 여기도 막힌다."""
        from kernels.k5_trust import InboundKeyNotFound, issue_key, rotate_key

        theirs = issue_key(scope=self.scope_b, name="남의 회전 대상")
        with self.assertRaises(InboundKeyNotFound):
            rotate_key(scope=self.scope_a, key_id=theirs.view.key_id)

    def test_the_pipeline_cannot_issue_keys(self) -> None:
        """★ 시스템 스코프로는 발급하지 않는다 (D-281).

        파이프라인에는 요청자가 없고, 주인 없는 키는 **어느 테넌트의 것인지 아무도
        모른다.** 모르는 키는 폐기할 사람도 없다.
        """
        from kernels.k5_trust import issue_key

        pipe = TenantScope.system(reason="키 시험 — 파이프라인에는 요청자가 없다")
        with self.assertRaises(PermissionDenied):
            issue_key(scope=pipe, name="주인 없는 키")


class SettingSurfaceTest(InboundKeyFixture):
    """★ F-12 「API키」 — **관리자 설정 한 곳에서** 다뤄지는가."""

    def test_a_non_admin_cannot_issue_a_key(self) -> None:
        """★ AC-12 「무권한은 차단하며」 — 발급도 그 차단 안이다.

        키 하나가 곧 진입면 하나다. 아무나 발급할 수 있으면 F-05 의 「하나로만
        들어온다」가 **아무 의미도 없어진다.**
        """
        from apps.dsm import services
        from apps.dsm.exceptions import PermissionDeniedForSetting

        APIKey = apps.get_model("apikey_account", "APIKey")
        before = APIKey.objects.count()

        with self.assertRaises(PermissionDeniedForSetting) as caught:
            services.issue_inbound_key(scope=self.plain_scope, name="몰래 발급")
        self.assertTrue(caught.exception.audit_id,
                        "차단이 감사에 안 남았습니다 (AC-12).")
        self.assertEqual(before, APIKey.objects.count(),
                         "차단했는데 키가 만들어졌습니다.")

    def test_the_setting_page_shows_both_directions_separately(self) -> None:
        """★ 설정 화면이 **두 방향을 나란히, 그러나 따로** 낸다 (D-337).

        한 칸에 뭉치면 그 혼동이 화면 안으로 들어온다 — 관리 주체도 폐기 절차도
        다른 둘을 같은 목록에서 보면 운영자가 남의 키를 우리 키로 읽는다.
        """
        from apps.dsm import services
        from kernels.k5_trust import issue_key

        issued = issue_key(scope=self.scope_a, name="화면 표본")
        out = services.setting_overview(scope=self.scope_a, domain="api_keys")

        self.assertIn("inbound", out)
        self.assertIn("outbound", out)
        self.assertIn(issued.view.key_id, [k["key_id"] for k in out["inbound"]])
        self.assertTrue(out["inbound_capability"],
                        "이 키로 무엇을 할 수 있는지가 비었습니다 — 표 ②가 "
                        "capability 를 비울 수 없게 한 것과 같은 이유입니다(D-328).")

    def test_no_key_value_reaches_the_setting_page(self) -> None:
        """★ 설정 화면 응답 **전체**에 키 값이 없다. 한 칸씩 보지 않고 통째로 본다."""
        from apps.dsm import services
        from kernels.k5_trust import issue_key

        issued = issue_key(scope=self.scope_a, name="값 누출 대조")
        out = services.setting_overview(scope=self.scope_a, domain="api_keys")
        self.assertNotIn(issued.secret, repr(out),
                         "설정 화면 응답에 키 값이 실려 있습니다.")

    def test_the_capability_is_read_from_the_gate_not_retyped(self) -> None:
        """★ 「이 키로 할 수 있는 일」이 **미들웨어의 허용 집합에서** 나온다 (D-286).

        문장으로 따로 적으면 허용 집합이 바뀌는 날 그 문장만 옛말이 되고,
        **옛말이 된 문장은 옛말인 것이 안 보인다.**
        """
        from common.access_gate import INBOUND_KEY_ALLOWED
        from kernels.k5_trust import inbound_key_facts

        # ★ **공개 면으로** 읽는다. `_capability_now` 는 비공개다 — 설비의 사실이라
        #   scope 를 받을 이유가 없는데 커널 공개 면은 D-281 로 scope 를 반드시 받아야
        #   하고, 쓰지도 않을 scope 를 다는 것은 「테넌트마다 다른 답이 있다」는
        #   거짓 신호이기 때문이다(verify_tenant_scope 가 그것을 잡았다).
        said = inbound_key_facts(scope=self.scope_a)["capability"]
        for method, path in INBOUND_KEY_ALLOWED:
            self.assertIn(path, said,
                          f"허용된 {method} {path} 가 capability 문장에 없습니다.")
        self.assertIn(str(len(INBOUND_KEY_ALLOWED)), said,
                      "닿는 자리의 **수**가 문장에 없습니다 — 건수를 냅니다(D-301).")
