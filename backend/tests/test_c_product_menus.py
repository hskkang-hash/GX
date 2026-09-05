# -*- coding: utf-8 -*-
"""제품 화면이 **사이드바에 서는가** — UX-25 시드 (세종 P-61 · 차선 C).

이 파일이 묻는 것
-----------------
① **행이 실제로 생기는가.** 표(`common/product_menus.py`)의 열 줄이 dj-core `Menu` 표에
   들어가고, 역할 넷에 `permit_read` 가 켜지는가.
② **두 번 돌려도 안 겹치는가.** 시드의 규약이다. 겹치면 사이드바에 같은 줄이 두 번 뜨고,
   그것은 「메뉴가 늘었다」와 구별되지 않는다.
③ ★★ **테넌트가 생기면 함께 서는가.** 지시서 §4 가 적은 함정이 이것이다 —
   개발 테넌트에만 한 번 넣고 끝내면 새 테넌트에서 다시 0 이 된다. 이 시험은
   `UserGroup` 을 **실제로 만들고** 그 순간 메뉴가 서는지 묻는다.
   ★ 「신호를 걸었다」와 「신호가 돌았다」는 다른 사실이다(D-301). 코드에 데코레이터가
     있는 것은 증거가 아니다 — 테넌트를 만들어 보는 것이 증거다.
④ **역할이 새로 생겨도 함께 서는가.** 이 DB 의 `role_role` 은 **소속을 갖는다**
   [실측 2026-09-05 — `fire_user` 는 소속 6]. 새 테넌트가 같은 코드의 역할을 따로
   만들면 그 역할에는 연결이 하나도 없다. 사람은 역할이 있는데 사이드바가 빈다.
⑤ **소속이 안 붙는가.** 붙는 순간 그 행은 「어느 테넌트의 메뉴」가 되고,
   `RoleMenu` 가 (메뉴,역할) 유일이라 다른 테넌트는 연결을 못 만든다.
⑥ **남의 행을 안 고치는가.** `/handover` 에는 이미 인수 행(『Handover』)이 있다.
   경로만 보고 찾으면 그 행을 우리 것으로 착각하고 이름을 덮어쓴다.

★ D-289 — 표본은 저장소 실물이다. dj-core 의 실제 표(`Menu`·`RoleMenu`·`Role`)를 만진다.
"""
from __future__ import annotations

from io import StringIO

from django.apps import apps
from django.core.management import call_command
from django.test import TestCase

from common.product_menus import (
    PRODUCT_MENUS,
    ensure_product_menus,
    expected_counts,
    ordering_of,
    role_codes_for,
)


def _menu_model():
    return apps.get_model("menu", "Menu")


def _rolemenu_model():
    return apps.get_model("menu", "RoleMenu")


def _role_model():
    return apps.get_model("role", "Role")


def _usergroup_model():
    return apps.get_model("user", "UserGroup")


class SeedFixture(TestCase):
    """역할 코드를 먼저 세운다 — 시드는 **없는 역할을 만들지 않는다**(그것은 시드의 일이 아니다)."""

    def setUp(self) -> None:
        Role = _role_model()
        self.roles = {}
        for bucket in ("U1", "U2", "U4", "U5"):
            for code in role_codes_for(bucket):
                self.roles[code], _ = Role.objects.get_or_create(code=code)

    def _seed(self, **kw):
        out = StringIO()
        call_command("seed_product_menus", stdout=out, **kw)
        return out.getvalue()


class RowsAppearTest(SeedFixture):
    """① 행이 생기고 역할에 붙는다."""

    def test_every_row_in_the_table_lands_in_the_menu_table(self) -> None:
        ensure_product_menus()
        Menu = _menu_model()
        for row in PRODUCT_MENUS:
            m = Menu._base_manager.filter(
                path=row["path"], menu_name=row["name"], deleted__isnull=True).first()
            self.assertIsNotNone(m, "%s 가 안 생겼다" % row["name"])
            self.assertEqual(m.ordering, ordering_of(row),
                             "%s 의 자리가 표와 다르다" % row["name"])
            self.assertIsNone(m.parent_id, "%s 는 뿌리여야 한다" % row["name"])

    def test_each_bucket_sees_exactly_what_the_table_says(self) -> None:
        """★ 「심었다」가 아니라 **「그 역할이 본다」**를 센다."""
        ensure_product_menus()
        Menu, RoleMenu = _menu_model(), _rolemenu_model()
        ours = {
            Menu._base_manager.filter(
                path=r["path"], menu_name=r["name"], deleted__isnull=True).first().pk
            for r in PRODUCT_MENUS
        }
        for bucket, want in expected_counts().items():
            for code in role_codes_for(bucket):
                seen = set(RoleMenu._base_manager.filter(
                    role__code=code, permit_read=True, deleted__isnull=True,
                    menu_id__in=ours).values_list("menu_id", flat=True))
                self.assertEqual(len(seen), want,
                                 "%s(%s) 가 보는 제품 줄이 %d (기대 %d)"
                                 % (bucket, code, len(seen), want))

    def test_only_read_is_granted(self) -> None:
        """관제요원에게 필요한 것은 **보는 것**이지 만드는 것이 아니다."""
        ensure_product_menus()
        RoleMenu = _rolemenu_model()
        Menu = _menu_model()
        m = Menu._base_manager.filter(path="/dsm/queue", deleted__isnull=True).first()
        for link in RoleMenu._base_manager.filter(menu=m, deleted__isnull=True):
            self.assertTrue(link.permit_read)
            self.assertFalse(link.permit_create or link.permit_update or link.permit_delete)


class IdempotentTest(SeedFixture):
    """② 두 번 돌려도 행이 안 겹친다."""

    def test_running_twice_creates_nothing_new(self) -> None:
        """★ 이 시험의 첫 줄이 이미 **신호가 돌았다는 증거**다.

        `setUp` 은 역할만 만들었는데 그 순간 `Role` 신호가 표를 세웠다 — 그래서
        여기서 부르는 `ensure_product_menus()` 는 **새로 만들 것이 없다.**
        [실측 2026-09-05 — 처음에 이 시험은 `10 개가 생긴다`를 기대했고 `0 != 10` 으로
        떨어졌다. 떨어진 이유가 **결함이 아니라 신호였다.**]
        """
        first = ensure_product_menus()
        second = ensure_product_menus()
        self.assertEqual(first["menu_created"], 0,
                         "역할을 만든 시점에 이미 서 있어야 한다(신호)")
        self.assertEqual(first["menu_unchanged"], len(PRODUCT_MENUS))
        self.assertEqual(second["menu_created"], 0)
        self.assertEqual(second["link_created"], 0)
        self.assertEqual(second["menu_unchanged"], len(PRODUCT_MENUS))

    def test_the_row_count_does_not_grow(self) -> None:
        Menu = _menu_model()
        ensure_product_menus()
        before = Menu._base_manager.filter(deleted__isnull=True).count()
        ensure_product_menus()
        ensure_product_menus()
        self.assertEqual(Menu._base_manager.filter(deleted__isnull=True).count(), before,
                         "같은 줄이 두 번 뜬다 — 시드가 멱등이 아니다")


class TenantCreationTest(SeedFixture):
    """③★★ **테넌트가 생기면 함께 선다.** 지시서 §4 의 함정이 이것이다."""

    def test_a_brand_new_tenant_does_not_start_at_zero(self) -> None:
        """★ **0 에서 시작시킨다.** 그러지 않으면 아무것도 안 재는 시험이 된다.

        `setUp` 이 역할을 만들면 신호가 이미 표를 세운다. 그 상태에서 테넌트를 만들고
        「있다」를 세면, 테넌트 신호가 죽어 있어도 초록이다 — 판정기가 자기가 심은 것을
        세는 그 모양이다(D-301). 그래서 **먼저 지운다.**
        """
        Menu = _menu_model()
        Menu._base_manager.filter(
            path__in=[r["path"] for r in PRODUCT_MENUS]).delete()
        self.assertEqual(
            Menu._base_manager.filter(path="/dsm/queue").count(), 0,
            "출발선이 0 이 아니면 이 시험은 아무것도 안 잰다")

        _usergroup_model().objects.create(name="ux25-new-tenant")

        got = Menu._base_manager.filter(
            path="/dsm/queue", menu_name="지금 처리할 것", deleted__isnull=True).count()
        self.assertEqual(got, 1,
                         "테넌트를 만들었는데 제품 메뉴가 안 섰다 — "
                         "새 테넌트의 사이드바가 다시 0 이다")

    def test_two_tenants_do_not_duplicate_the_rows(self) -> None:
        """★ 테넌트마다 한 벌씩 심으면 사이드바에 같은 줄이 여러 번 뜬다.

        `list_menus` 는 메뉴를 소속으로 가리지 않는다 [실측 2026-09-05] — 그래서
        정본은 **소속 없는 한 벌**이어야 한다.
        """
        Menu = _menu_model()
        UserGroup = _usergroup_model()
        Menu._base_manager.filter(
            path__in=[r["path"] for r in PRODUCT_MENUS]).delete()
        UserGroup.objects.create(name="ux25-tenant-A")
        UserGroup.objects.create(name="ux25-tenant-B")
        self.assertEqual(
            Menu._base_manager.filter(path="/dsm/queue", deleted__isnull=True).count(), 1)


class NewRoleTest(SeedFixture):
    """④ 역할이 새로 생겨도 그 역할의 연결이 함께 선다."""

    def test_a_role_created_later_gets_the_links(self) -> None:
        Role, RoleMenu, Menu = _role_model(), _rolemenu_model(), _menu_model()
        ensure_product_menus()
        # 이 코드는 우리 표에 있다. 같은 코드의 **다른 행**을 새로 만든다
        # (이 DB 의 역할은 소속을 가지므로 실제로 일어나는 일이다).
        Role._base_manager.filter(code="fire_user").delete()
        new_role = Role.objects.create(code="fire_user")
        m = Menu._base_manager.filter(path="/dsm/queue", deleted__isnull=True).first()
        self.assertTrue(
            RoleMenu._base_manager.filter(
                menu=m, role=new_role, permit_read=True, deleted__isnull=True).exists(),
            "나중에 생긴 역할에는 연결이 없다 — 그 사람의 사이드바는 빈다")


class NoTenantStampTest(SeedFixture):
    """⑤ 행에 소속이 안 붙는다."""

    def test_rows_and_links_have_no_group(self) -> None:
        ensure_product_menus()
        Menu, RoleMenu = _menu_model(), _rolemenu_model()
        for row in PRODUCT_MENUS:
            m = Menu._base_manager.filter(
                path=row["path"], menu_name=row["name"], deleted__isnull=True).first()
            self.assertIsNone(m.group_id, "%s 에 소속이 붙었다" % row["name"])
            for link in RoleMenu._base_manager.filter(menu=m, deleted__isnull=True):
                self.assertIsNone(link.group_id, "%s 의 연결에 소속이 붙었다" % row["name"])


class OtherRowsAreLeftAloneTest(SeedFixture):
    """⑥ 남의 행을 안 고친다 — `/handover` 에는 이미 인수 행이 있다."""

    def test_the_acquired_handover_row_is_untouched(self) -> None:
        Menu = _menu_model()
        legacy = Menu.objects.create(menu_name="Handover", path="/handover", ordering=0)
        ensure_product_menus()
        legacy.refresh_from_db()
        self.assertEqual(legacy.menu_name, "Handover")
        self.assertEqual(legacy.ordering, 0, "남의 행의 자리를 옮겼다")
        # 우리 줄은 **따로** 생긴다
        mine = Menu._base_manager.filter(
            path="/handover", menu_name="인계 메모", deleted__isnull=True).first()
        self.assertIsNotNone(mine)
        self.assertNotEqual(mine.pk, legacy.pk)

    def test_a_menu_outside_the_table_is_not_created(self) -> None:
        """표에 없는 것은 안 만든다 — 월 모드는 **일부러** 사이드바 밖이다."""
        ensure_product_menus()
        Menu = _menu_model()
        self.assertEqual(
            Menu._base_manager.filter(path="/wall", deleted__isnull=True).count(), 0)


class CommandTest(SeedFixture):
    """명령이 실제로 돈다 — 그리고 `--dry-run` 은 **아무것도 안 쓴다**."""

    def test_dry_run_writes_nothing(self) -> None:
        Menu = _menu_model()
        before = Menu._base_manager.filter(deleted__isnull=True).count()
        self._seed(dry_run=True)
        self.assertEqual(Menu._base_manager.filter(deleted__isnull=True).count(), before)

    def test_the_command_seeds(self) -> None:
        self._seed()
        Menu = _menu_model()
        self.assertEqual(
            Menu._base_manager.filter(path="/dsm/queue", deleted__isnull=True).count(), 1)

    def test_unlink_turns_off_without_deleting(self) -> None:
        """★ 되끄기는 **지우기가 아니다.** 행은 그대로 있고 칸만 꺼진다."""
        self._seed()
        Menu, RoleMenu = _menu_model(), _rolemenu_model()
        m = Menu._base_manager.filter(path="/dsm/queue", deleted__isnull=True).first()
        n_links = RoleMenu._base_manager.filter(menu=m, deleted__isnull=True).count()
        self._seed(unlink=True)
        self.assertEqual(
            Menu._base_manager.filter(path="/dsm/queue", deleted__isnull=True).count(), 1,
            "행이 지워졌다")
        self.assertEqual(
            RoleMenu._base_manager.filter(menu=m, deleted__isnull=True).count(), n_links,
            "연결 행이 지워졌다")
        self.assertEqual(
            RoleMenu._base_manager.filter(
                menu=m, permit_read=True, deleted__isnull=True).count(), 0)
        # 다시 세우면 켜진다
        self._seed()
        self.assertEqual(
            RoleMenu._base_manager.filter(
                menu=m, permit_read=True, deleted__isnull=True).count(), n_links)
