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
