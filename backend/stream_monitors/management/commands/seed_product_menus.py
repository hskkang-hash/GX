# -*- coding: utf-8 -*-
"""제품 화면을 **사이드바에 세운다** — UX-25 시드 한 자리 (세종 P-61).

    메뉴 정본은 dj-core DB 다 — **코드가 아니라 시드(데이터)로 넣는다**(§0.4 무수정).
    이름은 한국어. 순서는 하루에 누르는 횟수 순.
        — 세종 P-61

표는 여기 없다. 표는 `backend/common/product_menus.py` 한 곳이고, 이 명령은 그 표를
DB 로 옮기는 손이다. **두 벌을 두지 않는다**(D-369) — 판정기(`scripts/verify_sidebar.py`)도
같은 표를 읽는다. 표가 두 벌이면 「심은 것」과 「재는 것」이 어긋나고, 어긋나면
판정기는 자기가 심은 것을 세면서 초록을 낸다.

무엇을 하나
-----------
  · `Menu` 행 열 개를 **넣는다**(있으면 자리·아이콘만 맞춘다). 지우지 않는다.
  · 역할 묶음 넷(U1·U2·U4·U5)에 `RoleMenu.permit_read` 를 **켠다**. 네 칸 중
    읽기만 켠다 — 관제요원에게 필요한 것은 보는 것이지 만드는 것이 아니다.
  · **멱등이다.** 두 번 돌려도 행이 안 겹친다(열쇠는 경로+이름 쌍).

사용법
------
    docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
        python manage.py seed_product_menus --dry-run'
    docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
        python manage.py seed_product_menus'
    ... --show      # 지금 DB 에 무엇이 있나만 낸다(안 고친다)
    ... --unlink    # 이 시드가 켠 연결을 **되끈다**(행은 그대로 · 되돌릴 수 있다)

★ `--unlink` 는 지우기가 아니다
-------------------------------
UX-21 이 정한 규약을 그대로 따른다(`common/menu_exposure.py`): **행도 라우트도 한 줄
안 지운다.** 되끄는 것은 `permit_read` 칸뿐이고, 다시 이 명령을 돌리면 켜진다.
지우는 문을 두지 않는 이유는 하나다 — 지운 메뉴는 되돌릴 때 **id 가 바뀌고**,
누군가 그 id 를 적어 둔 자리(대시보드 링크·즐겨찾기)가 조용히 끊긴다.

★ 이 명령은 「보인다」를 말하지 않는다
-------------------------------------
끝에 찍는 수는 **자기가 방금 한 일**이다. 사이드바에 실제로 몇 줄이 뜨는지는
`scripts/verify_sidebar.py` 가 **로그인해서** 잰다. 심은 쪽이 자기 일을 세어 초록이라
말하는 것이 거짓 초록의 가장 흔한 모양이다(D-301 · `verify_seed_roles` 머리말과 같은 이유).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from common.product_menus import (
    ALREADY_IN_DB,
    BUCKET_LABEL,
    NOT_IN_SIDEBAR_BY_DECISION,
    P61_NO_SCREEN_YET,
    PRODUCT_MENUS,
    ensure_product_menus,
    expected_counts,
    ordering_of,
    role_codes_for,
    rows_for,
)


class Command(BaseCommand):
    help = "UX-25 — 제품 화면 메뉴 행을 dj-core `Menu` 표에 심는다(멱등 · 세종 P-61)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="바꾸지 않고 무엇을 할지만 낸다")
        parser.add_argument("--show", action="store_true",
                            help="지금 DB 에 무엇이 있나만 낸다 — 아무것도 안 고친다")
        parser.add_argument("--unlink", action="store_true",
                            help="이 시드가 켠 연결을 되끈다(행은 그대로 · 되돌릴 수 있다)")

    # ── 표를 사람이 읽는 모양으로 ────────────────────────────────────────
    def _print_table(self):
        self.stdout.write("[표] 제품 메뉴 %d줄 — 순서는 하루에 누르는 횟수 순"
                          % len(PRODUCT_MENUS))
        for row in PRODUCT_MENUS:
            self.stdout.write("  %5d  %-14s %-24s %s"
                              % (ordering_of(row), row["name"], row["path"],
                                 "·".join(row["buckets"])))
        for b, n in expected_counts().items():
            self.stdout.write("  기대 %s(%s) %d줄" % (b, BUCKET_LABEL[b], n))

    def _print_declarations(self):
        self.stdout.write("")
        self.stdout.write("[선언] P-61 이 적었으나 **화면이 없어서 안 건** 자리 %d개 —"
                          % len(P61_NO_SCREEN_YET))
        self.stdout.write("       없는 화면에 메뉴를 걸면 눌러도 아무 데도 안 가는 줄이 남는다.")
        for name, why in P61_NO_SCREEN_YET.items():
            self.stdout.write("       · %-24s %s" % (name, why))
        self.stdout.write("[선언] 화면은 있으나 **일부러 안 건** 자리:")
        for path, why in NOT_IN_SIDEBAR_BY_DECISION.items():
            self.stdout.write("       · %-24s %s" % (path, why))
        self.stdout.write("[선언] 이미 DB 에 있어 **새로 안 만드는** 자리:")
        for path, why in ALREADY_IN_DB.items():
            self.stdout.write("       · %-24s %s" % (path, why))

    def _show(self):
        from core.menu.models import Menu, RoleMenu

        self.stdout.write("[실측] 지금 DB — 이 명령이 심는 줄만 본다")
        for row in PRODUCT_MENUS:
            menu = Menu._base_manager.filter(
                path=row["path"], menu_name=row["name"], deleted__isnull=True).first()
            if menu is None:
                self.stdout.write("  없음   %-14s %s" % (row["name"], row["path"]))
                continue
            codes = sorted({c for b in row["buckets"] for c in role_codes_for(b)})
            live = RoleMenu._base_manager.filter(
                menu=menu, permit_read=True, deleted__isnull=True,
                role__code__in=codes).count()
            self.stdout.write("  #%-5s %-14s %-24s 자리 %s · 소속 %s · 켜진 연결 %d/%d"
                              % (menu.pk, row["name"], row["path"], menu.ordering,
                                 menu.group_id, live, len(codes)))

    def _unlink(self, dry_run: bool):
        from core.menu.models import Menu, RoleMenu

        turned_off = 0
        for row in PRODUCT_MENUS:
            menu = Menu._base_manager.filter(
                path=row["path"], menu_name=row["name"], deleted__isnull=True).first()
            if menu is None:
                continue
            qs = RoleMenu._base_manager.filter(
                menu=menu, permit_read=True, deleted__isnull=True)
            n = qs.count()
            if n and not dry_run:
                qs.update(permit_read=False)
            turned_off += n
        self.stdout.write(self.style.WARNING(
            "%s 연결 %d개를 되껐다 — **행은 그대로다.** 다시 세우려면 이 명령을 그냥 돌린다."
            % ("[dry-run] " if dry_run else "", turned_off)))

    def handle(self, *args, **opts):
        self._print_table()

        if opts["show"]:
            self.stdout.write("")
            self._show()
            self._print_declarations()
            return

        if opts["unlink"]:
            self._unlink(opts["dry_run"])
            return

        self.stdout.write("")
        result = ensure_product_menus(
            dry_run=opts["dry_run"], log=lambda m: self.stdout.write("  " + m))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            "%s행: 새로 %d · 고침 %d · 그대로 %d   연결: 새로 %d · 켬 %d · 그대로 %d"
            % ("[dry-run] " if opts["dry_run"] else "",
               result["menu_created"], result["menu_updated"], result["menu_unchanged"],
               result["link_created"], result["link_updated"], result["link_unchanged"])))
        if result["roles_missing"]:
            self.stdout.write(self.style.WARNING(
                "  ⚠ 이 DB 에 **없는 역할**: %s — 그 역할의 사람은 아무것도 못 본다"
                % ", ".join(sorted(result["roles_missing"]))))

        self._print_declarations()
        self.stdout.write("")
        self.stdout.write(
            "★ 이 수는 **심은 것**이지 **보이는 것**이 아니다. 보이는 줄은 로그인해서 잰다:")
        self.stdout.write("  python scripts/verify_sidebar.py")

        # 묶음별 기대 — 판정기가 이 수와 실측을 맞댄다
        for b, n in expected_counts().items():
            names = " · ".join(r["name"] for r in rows_for(b))
            self.stdout.write("  기대 %s(%s) %d줄: %s" % (b, BUCKET_LABEL[b], n, names))
