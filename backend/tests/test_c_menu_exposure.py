# -*- coding: utf-8 -*-
"""역할↔메뉴 **연결 끊기** — 지웠는가, 되돌릴 수 있는가 (UX-21 · P-40 · 차선 C).

이 파일이 묻는 것
-----------------
① **아무것도 지우지 않았는가.** 이 일의 승인 조건이 그것이다 — 메뉴 행도,
   라우트도, 연결 행 자체도 지우지 않는다. 지우면 되돌릴 것이 없어진다.
② **관제 역할에서 실제로 사라지는가.** 사이드바는 `permit_read` 로 그려지므로
   그 칸이 거짓이 되어야 사라진다. 「명령이 돌았다」와 「메뉴가 사라졌다」는
   다른 사실이다.
③ **되돌릴 수 있는가.** 되돌리기는 **장부대로**여야 한다 — 표만 보고 켜면
   끊기 전부터 꺼져 있던 연결까지 켜서 **없던 권한을 준다.** 그것은 되돌리기가
   아니라 새 부여다.
④ **U5 는 남는가.** 세종 P-40 이 남기라고 한 자리다. 관리자까지 끊으면
   장비를 등록할 자리가 없어진다.
⑤ **두 번 돌려도 같은가** (시드 규약). 두 번째 실행이 장부를 덮어쓰면
   되돌릴 진실이 사라진다.
"""
from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

#: ★ D-289 — 표본은 저장소 실물이다. dj-core 의 실제 표를 만진다(읽고 칸만 고친다).
REAL_SAMPLE = (
    "core.menu.models.Menu · core.menu.models.RoleMenu · core.role.models.Role — "
    "인수받은 실제 표. 합성 더미를 만들지 않는다"
)


class MenuUnlinkFixture(TestCase):
    """관제 역할 하나(U1)·관리자 하나(U5)·대상 메뉴 하나로 최소 표를 세운다."""

    def setUp(self) -> None:
        from core.menu.models import Menu, RoleMenu
        from core.role.models import Role
        from django.apps import apps

        # ★ 이름으로 import 하지 않는다 — dj-core 의 앱 라벨은 `user` 이고
        #   그 모듈은 이름 공간에 없다. 저장소의 다른 시험이 이미 이렇게 한다.
        UserGroup = apps.get_model("user", "UserGroup")

        self.ledger = Path(tempfile.mkdtemp()) / "ledger.json"

        # ★ **소속을 둘 만든다.** 이 표는 공용 마스터가 아니라 소속을 갖는다
        #   [실측 2026-09-05: 969행 중 926행이 소속을 가짐]. 소속이 하나뿐인
        #   픽스처로는 「남의 소속까지 끊었는가」를 물을 수 없다.
        self.group_a = UserGroup.objects.create(name="menu-tenant-A")
        self.group_b = UserGroup.objects.create(name="menu-tenant-B")

        self.menu = Menu.objects.create(menu_name="Drones and Robots", path="/device")
        # 대상이 아닌 메뉴 — 끊기가 **넘치지 않는지**를 재는 음성 대조다.
        self.other = Menu.objects.create(menu_name="관제 대시보드", path="/dsm/dashboard")

        self.u1, _ = Role.objects.get_or_create(code="fire_user")
        self.u2, _ = Role.objects.get_or_create(code="fire_admin")
        self.u5, _ = Role.objects.get_or_create(code="admin")

        self.link_u1 = RoleMenu.objects.create(
            menu=self.menu, role=self.u1, group=self.group_a,
            permit_read=True, permit_create=True, permit_update=False, permit_delete=False)
        #: **다른 소속**의 같은 메뉴. `--group A` 로 끊을 때 이것이 살아 있어야 한다.
        self.link_other_tenant = RoleMenu.objects.create(
            menu=self.menu, role=self.u2, group=self.group_b, permit_read=True)
        self.link_u5 = RoleMenu.objects.create(
            menu=self.menu, role=self.u5, group=self.group_a,
            permit_read=True, permit_create=True)
        self.link_other = RoleMenu.objects.create(
            menu=self.other, role=self.u1, group=self.group_a, permit_read=True)

    def _cut(self, **kw):
        out = StringIO()
        kw.setdefault("all_tenants", True)
        call_command("unlink_control_role_menus", ledger=str(self.ledger), stdout=out, **kw)
        return out.getvalue()

    def _restore(self, **kw):
        out = StringIO()
        call_command("relink_control_role_menus", ledger=str(self.ledger), stdout=out, **kw)
        return out.getvalue()


class NothingIsDeletedTest(MenuUnlinkFixture):
    """① ★ **한 줄도 안 지운다.** 지우면 되돌릴 것이 없어진다."""

    def test_menu_rows_and_link_rows_survive(self) -> None:
        from core.menu.models import Menu, RoleMenu

        before_menus = Menu.objects.count()
        before_links = RoleMenu.objects.count()

        self._cut()

        self.assertEqual(Menu.objects.count(), before_menus,
                         "메뉴 행이 줄었습니다 — 이 일은 삭제가 아닙니다.")
        self.assertEqual(RoleMenu.objects.count(), before_links,
                         "연결 행이 줄었습니다 — 끊는 것은 행이 아니라 칸입니다.")
        self.assertTrue(RoleMenu.objects.filter(pk=self.link_u1.pk).exists())


class ControlRoleLosesTheMenuTest(MenuUnlinkFixture):
    """② ★ 관제 역할에서 **실제로** 사라진다 — 사이드바가 보는 칸이 거짓이 된다."""

    def test_read_permission_is_false_after_cut(self) -> None:
        self._cut()
        self.link_u1.refresh_from_db()
        self.assertFalse(self.link_u1.permit_read, "관제 역할에 아직 보입니다.")
        self.assertFalse(self.link_u1.permit_create,
                         "읽기만 끊으면 **반만 끊긴 연결**이 남습니다.")

    def test_untargeted_menu_is_untouched(self) -> None:
        """넘치지 않는가 — 대상이 아닌 메뉴는 그대로다."""
        self._cut()
        self.link_other.refresh_from_db()
        self.assertTrue(self.link_other.permit_read,
                        "대상이 아닌 메뉴까지 끊었습니다 — 끊기가 넘쳤습니다.")

    def test_dry_run_writes_nothing(self) -> None:
        """표가 먼저다. 표를 그리는 실행은 **한 칸도 안 쓴다.**"""
        self._cut(dry_run=True)
        self.link_u1.refresh_from_db()
        self.assertTrue(self.link_u1.permit_read, "dry-run 이 실제로 썼습니다.")
        self.assertFalse(self.ledger.exists(), "dry-run 이 장부를 남겼습니다.")


class SysopKeepsTheMenuTest(MenuUnlinkFixture):
    """④ ★ U5 는 남는다 — 관리자까지 끊으면 장비를 등록할 자리가 없어진다."""

    def test_admin_link_is_untouched(self) -> None:
        self._cut()
        self.link_u5.refresh_from_db()
        self.assertTrue(self.link_u5.permit_read,
                        "시스템 관리자에게서도 끊었습니다 — P-40 은 U5 를 남기라고 했습니다.")


class ItCanBeUndoneTest(MenuUnlinkFixture):
    """③ ★ **장부대로** 되돌린다. 표대로 켜면 없던 권한을 주게 된다."""

    def test_restore_puts_back_exactly_what_was_there(self) -> None:
        self._cut()
        self._restore()
        self.link_u1.refresh_from_db()
        self.assertTrue(self.link_u1.permit_read)
        self.assertTrue(self.link_u1.permit_create)
        # 끊기 전에 **거짓이던 칸**은 거짓으로 돌아온다 — 되돌리기이지 새 부여가 아니다.
        self.assertFalse(self.link_u1.permit_update,
                         "끊기 전에 없던 권한이 되돌리기로 생겼습니다.")
        self.assertFalse(self.link_u1.permit_delete)

    def test_restore_without_a_ledger_refuses(self) -> None:
        """되돌릴 것이 없는 것과 **무엇을 되돌릴지 모르는 것**은 다르다."""
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self._restore()


class RunningTwiceIsSafeTest(MenuUnlinkFixture):
    """⑤ ★ 시드처럼 다시 돌 수 있다 — 두 번째 실행이 장부를 비우지 않는다."""

    def test_second_cut_keeps_the_ledger_truth(self) -> None:
        self._cut()
        first = json.loads(self.ledger.read_text(encoding="utf-8"))
        self._cut()
        again = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(len(again["entries"]), len(first["entries"]),
                         "두 번째 실행이 장부를 늘리거나 지웠습니다.")
        self._restore()
        self.link_u1.refresh_from_db()
        self.assertTrue(self.link_u1.permit_read,
                        "두 번 끊은 뒤에는 되돌릴 수 없게 됐습니다.")

    def test_cut_after_restore_can_be_undone_again(self) -> None:
        """되돌린 뒤 다시 끊어도 **또 되돌릴 수 있어야** 한다."""
        self._cut()
        self._restore()
        self._cut()
        self._restore()
        self.link_u1.refresh_from_db()
        self.assertTrue(self.link_u1.permit_read)


class ItSaysWhoseTableThisIsTest(MenuUnlinkFixture):
    """⑥ ★ **이 표가 누구 것인지 묻고 나서 쓴다** (D-270 ③).

    커밋 훅이 이 물음을 던졌고, 등록부의 답은 「아직 정해지지 않았다」(DEFERRED)였다 —
    「공용 마스터」도 「주인 없음」도 아니었다. 그래서 실물을 쟀고 **소속을 갖는 표**임을
    확인했다. 그 사실이 명령의 출력과 장부에 남아야, 다음 사람이 「왜 우리 메뉴가
    없나」에 답을 찾는다.
    """

    def test_the_registry_is_the_only_source_of_the_classification(self) -> None:
        """분류는 등록부에서 읽는다 — 판정식을 명령에 복사하지 않는다(D-212)."""
        from common.menu_exposure import EXPECTED_CLASSIFICATION, classification_of

        got, why = classification_of()
        self.assertEqual(got, EXPECTED_CLASSIFICATION,
                         "등록부의 분류가 바뀌었습니다 — 명령의 전제가 깨졌습니다.")
        self.assertTrue(why.strip(), "분류에 사유가 없습니다 — 근거 없는 등재입니다.")

    def test_it_prints_the_classification_before_writing(self) -> None:
        out = self._cut(dry_run=True)
        self.assertIn("menu.RoleMenu", out)
        self.assertIn("DEFERRED", out)

    def test_it_refuses_when_the_scope_is_not_declared(self) -> None:
        """★ **조용한 기본값을 두지 않는다.** 기본이 전역인 명령은 언젠가 모르고 눌린다."""
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            out = StringIO()
            call_command("unlink_control_role_menus",
                         ledger=str(self.ledger), stdout=out)

    def test_the_ledger_records_which_tenant(self) -> None:
        """소속을 안 적으면 되돌리기가 **어느 소속의 것인지** 말하지 못한다."""
        self._cut()
        led = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(led.get("write_target"), "menu.RoleMenu")
        self.assertEqual(led.get("scope"), "all-tenants")
        groups = {e["group_id"] for e in led["entries"]}
        self.assertIn(self.group_a.pk, groups)
        self.assertIn(self.group_b.pk, groups)


class ItDoesNotCutOtherTenantsUnlessToldTest(MenuUnlinkFixture):
    """⑦ ★ **남의 소속은 시키지 않으면 안 끊는다.**

    이것이 커밋 훅이 막아 준 진짜 사고다. 1차판은 소속을 안 가리고 끊었고, 그러면
    나중에 들어오는 다른 지자체가 자기 관제요원에게 드론 화면을 보여 주려 해도
    **이미 끊겨 있고 왜인지 모른다.**
    """

    def test_group_scope_leaves_the_other_tenant_alone(self) -> None:
        self._cut(all_tenants=False, group=[self.group_a.pk])
        self.link_u1.refresh_from_db()
        self.link_other_tenant.refresh_from_db()
        self.assertFalse(self.link_u1.permit_read, "지정한 소속이 안 끊겼습니다.")
        self.assertTrue(self.link_other_tenant.permit_read,
                        "**남의 소속까지 끊었습니다** — 시키지 않은 일을 했습니다.")

    def test_all_tenants_really_means_all(self) -> None:
        """전역으로 끊겠다고 **말했을 때만** 전역으로 끊는다."""
        self._cut()
        self.link_u1.refresh_from_db()
        self.link_other_tenant.refresh_from_db()
        self.assertFalse(self.link_u1.permit_read)
        self.assertFalse(self.link_other_tenant.permit_read)

    def test_restore_can_be_limited_to_one_tenant(self) -> None:
        """되돌리기도 소속별로 된다 — 한 소속만 되살려도 다른 소속은 그대로다."""
        self._cut()
        self._restore(group=[self.group_a.pk])
        self.link_u1.refresh_from_db()
        self.link_other_tenant.refresh_from_db()
        self.assertTrue(self.link_u1.permit_read, "지정한 소속이 안 되살아났습니다.")
        self.assertFalse(self.link_other_tenant.permit_read,
                         "시키지 않은 소속까지 되살렸습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# P-50 — 레거시 화면 셋을 **U5 에서도** 끊는다 (2026-09-05 턴 E · 상용 점검 §8)
#
#   턴 C 는 U5 를 남겼다. 상용 점검이 반박했다 — 「관제 제품인데 인수 자산 화면이
#   그대로 보인다」. 그래서 묶음이 둘이 됐고, 이 아래가 묻는 것은 **묶음이 서로를
#   삼키지 않는가**다. 합쳐 버리면 U5 가 `/device` 까지 잃고, 그것은 P-40 이
#   남기라 한 자리다.
# ═══════════════════════════════════════════════════════════════════════════


class LegacyThreeFixture(MenuUnlinkFixture):
    """P-50 세 화면 + **묶음 마디 하나**를 최소 표에 더한다.

    ★ 마디를 픽스처에 넣는 이유 — dj-core `list_menus` 는 묶음을 「자식이 남았으니
      보인다」가 아니라 **제 행의 `permit_read` 로도** 보인다. 자식만 끊으면
      사이드바에 **아무 데도 못 가는 한 줄**이 남는다. 그 한 줄을 재려면 표에
      있어야 한다.
    """

    def setUp(self) -> None:
        super().setUp()
        from core.menu.models import Menu, RoleMenu

        self.legacy_dash = Menu.objects.create(
            menu_name="Surveillance Dashboard", path="/surveillance-dashboard")
        self.media_bucket = Menu.objects.create(
            menu_name="Media Data", path="/media-data")
        #: 묶음 마디 — 경로가 라우트가 아니라 문자열이다(실물이 그렇다).
        self.media_viewer_node = Menu.objects.create(
            menu_name="Media Viewer", path="Media Viewer")
        self.multi_stream = Menu.objects.create(
            menu_name="Multi-Stream Monitor", path="/multi-stream-monitor",
            parent=self.media_viewer_node)

        def link(menu, role, **kw):
            kw.setdefault("permit_read", True)
            return RoleMenu.objects.create(
                menu=menu, role=role, group=self.group_a, **kw)

        self.u5_dash = link(self.legacy_dash, self.u5, permit_create=True)
        self.u5_bucket = link(self.media_bucket, self.u5, permit_create=True)
        self.u5_stream = link(self.multi_stream, self.u5)
        self.u5_node = link(self.media_viewer_node, self.u5)
        self.u1_stream = link(self.multi_stream, self.u1)
        self.u1_node = link(self.media_viewer_node, self.u1)


class SysopLosesTheLegacyThreeTest(LegacyThreeFixture):
    """★ U5 에서도 끊긴다 — P-50 의 본문."""

    def test_all_three_legacy_screens_go_dark_for_sysop(self) -> None:
        self._cut()
        for row, name in ((self.u5_dash, "레거시 감시 대시보드"),
                          (self.u5_bucket, "미디어 버킷"),
                          (self.u5_stream, "드론 다중 스트림")):
            row.refresh_from_db()
            self.assertFalse(row.permit_read,
                             "시스템 관리자에게 %s 가 아직 보입니다." % name)
            self.assertFalse(row.permit_create,
                             "%s 의 읽기만 끊겼습니다 — 반만 끊긴 연결입니다." % name)

    def test_the_empty_group_node_goes_too(self) -> None:
        """★ 자식만 끊으면 **아무 데도 못 가는 한 줄**이 사이드바에 남는다."""
        self._cut()
        self.u5_node.refresh_from_db()
        self.u1_node.refresh_from_db()
        self.assertFalse(self.u5_node.permit_read,
                         "자식 잃은 묶음 마디가 관리자 사이드바에 남았습니다.")
        self.assertFalse(self.u1_node.permit_read,
                         "자식 잃은 묶음 마디가 관제요원 사이드바에 남았습니다.")

    def test_sysop_still_keeps_the_ux21_eight(self) -> None:
        """★ 묶음이 서로를 삼키지 않는다 — U5 의 `/device` 는 P-40 이 남긴 자리다."""
        self._cut()
        self.link_u5.refresh_from_db()
        self.assertTrue(self.link_u5.permit_read,
                        "P-50 이 UX-21 묶음까지 끊었습니다 — U5 는 /device 를 "
                        "유지해야 합니다(P-40).")


class BundlesAreSeparableTest(LegacyThreeFixture):
    """★ 판정 하나만 돌리고, 판정 하나만 무를 수 있는가."""

    def test_ux21_bundle_alone_does_not_touch_the_legacy_three(self) -> None:
        self._cut(bundle=["UX-21"])
        self.u5_stream.refresh_from_db()
        self.link_u1.refresh_from_db()
        self.assertFalse(self.link_u1.permit_read, "UX-21 묶음이 안 끊겼습니다.")
        self.assertTrue(self.u5_stream.permit_read,
                        "UX-21 만 돌렸는데 P-50 대상까지 끊겼습니다.")

    def test_p50_bundle_alone_does_not_touch_the_acquired_eight(self) -> None:
        self._cut(bundle=["P-50"])
        self.u5_stream.refresh_from_db()
        self.link_u1.refresh_from_db()
        self.assertFalse(self.u5_stream.permit_read, "P-50 묶음이 안 끊겼습니다.")
        self.assertTrue(self.link_u1.permit_read,
                        "P-50 만 돌렸는데 UX-21 대상까지 끊겼습니다.")

    def test_the_ledger_says_which_decision_cut_each_row(self) -> None:
        """장부에 판정 이름이 없으면 **판정 하나만 무를 수 없다.**"""
        self._cut()
        led = json.loads(self.ledger.read_text(encoding="utf-8"))
        bundles = {e.get("bundle") for e in led["entries"]}
        self.assertEqual(bundles, {"UX-21", "P-50"},
                         "장부가 어느 판정으로 끊었는지 말하지 않습니다: %r" % bundles)
        # ★ 여기에 이름을 손으로 적지 않는다 (2026-09-05 · UX-25 가 `P-61-U1` 을 더했다).
        #   장부의 `bundles` 는 「이번에 **돌린** 판정」이고, 인자를 안 주면 표 전부다.
        #   손으로 적으면 판정이 하나 늘 때마다 이 줄이 빨강이 되고, 그 빨강은
        #   「장부가 고장났다」가 아니라 **「표가 늘었다」**다 — 둘을 구별 못 하는
        #   시험은 다음 사람에게 무시당한다.
        from common.menu_exposure import BUNDLE_IDS
        self.assertEqual(sorted(led.get("bundles", [])), sorted(BUNDLE_IDS))

    def test_one_decision_can_be_undone_alone(self) -> None:
        """P-50 만 되살리고 UX-21 은 끊긴 채로 둔다."""
        self._cut()
        self._restore(bundle=["P-50"])
        self.u5_stream.refresh_from_db()
        self.link_u1.refresh_from_db()
        self.assertTrue(self.u5_stream.permit_read, "P-50 이 안 되살아났습니다.")
        self.assertFalse(self.link_u1.permit_read,
                         "P-50 만 무르라 했는데 UX-21 까지 되살아났습니다.")


class LegacyThreeRoundTripTest(LegacyThreeFixture):
    """★ **왕복** — 끊었다 · 되붙였다 · 다시 끊는다. 세 번 다 같은 자리로 온다."""

    def test_cut_restore_cut_lands_in_the_same_place(self) -> None:
        self._cut()
        self.u5_dash.refresh_from_db()
        self.assertFalse(self.u5_dash.permit_read)

        self._restore()
        self.u5_dash.refresh_from_db()
        self.assertTrue(self.u5_dash.permit_read, "되붙지 않았습니다.")
        self.assertTrue(self.u5_dash.permit_create)
        # 끊기 전에 꺼져 있던 칸은 꺼진 채로 — 되돌리기이지 새 부여가 아니다.
        self.assertFalse(self.u5_dash.permit_update)

        self._cut()
        self.u5_dash.refresh_from_db()
        self.assertFalse(self.u5_dash.permit_read, "두 번째 끊기가 안 먹었습니다.")

    def test_nothing_is_deleted_across_the_round_trip(self) -> None:
        from core.menu.models import Menu, RoleMenu

        menus, links = Menu.objects.count(), RoleMenu.objects.count()
        self._cut()
        self._restore()
        self._cut()
        self.assertEqual(Menu.objects.count(), menus, "메뉴 행이 줄었습니다.")
        self.assertEqual(RoleMenu.objects.count(), links, "연결 행이 줄었습니다.")


class SuperuserIsNotInAnyBundleTest(LegacyThreeFixture):
    """★ `superuser` 에게는 셋이 **그대로 보인다** — 모르고 남긴 것이 아니다.

    전역 관리자 판정은 `common/tenant_roles.is_global_admin` 한 곳이 한다(D-212).
    여기에 적으면 판정식이 두 벌이 되고, 두 벌은 반드시 어긋난다. 그 사실을
    시험으로 **적어 둔다** — 다음 사람이 「빠뜨렸다」로 읽지 않게.
    """

    def test_superuser_is_absent_from_every_bundle(self) -> None:
        from common.menu_exposure import CUT_BUNDLES

        for b in CUT_BUNDLES:
            self.assertNotIn("superuser", b["roles"],
                             "%s 묶음이 superuser 를 넣었습니다 — 전역 관리자 판정은 "
                             "tenant_roles 한 곳이 합니다(D-212)." % b["id"])
