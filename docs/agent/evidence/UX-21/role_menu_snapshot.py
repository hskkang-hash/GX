# -*- coding: utf-8 -*-
"""역할별로 **지금 보이는 메뉴**를 그대로 찍는다 — P-50 전후 대조용.

★ 이 스냅샷은 dj-core `list_menus` 와 **같은 눈**으로 본다:
  보이는 것 = `permit_read=True` 인 메뉴 ∪ 그 조상들.
  묶음 마디(경로가 `/` 로 시작하지 않는 것)는 화면이 아니므로 따로 센다 —
  「화면 N장」을 셀 때 마디를 화면으로 세면 수가 거짓이 된다.

  python manage.py shell < role_menu_snapshot.py
"""
from core.menu.models import Menu, RoleMenu
from config.k3_roles import (
    K3_ROLE_OPERATORS, K3_ROLE_MANAGERS, K3_ROLE_EXECUTIVES, K3_ROLE_SYSOPS,
)

ROLES = (
    [("U1", c) for c in K3_ROLE_OPERATORS]
    + [("U2", c) for c in K3_ROLE_MANAGERS]
    + [("U4", c) for c in K3_ROLE_EXECUTIVES]
    + [("U5", c) for c in K3_ROLE_SYSOPS]
)

print("### 역할별 보이는 메뉴 (permit_read=True ∪ 조상)")
for tag, code in ROLES:
    ids = set(RoleMenu.objects.filter(role__code=code, permit_read=True)
              .values_list("menu_id", flat=True))
    # 조상을 올린다 — dj-core list_menus 가 그렇게 한다
    anc, seen = set(), set()
    for m in Menu.objects.filter(id__in=ids):
        pid = m.parent_id
        while pid and pid not in seen:
            seen.add(pid); anc.add(pid)
            par = Menu.objects.filter(id=pid).first()
            pid = par.parent_id if par else None
    vis = ids | anc
    rows = sorted(Menu.objects.filter(id__in=vis).values_list("path", "menu_name"))
    screens = [r for r in rows if (r[0] or "").startswith("/")]
    nodes = [r for r in rows if not (r[0] or "").startswith("/")]
    print("== %s %s — 화면 %d · 묶음마디 %d (합 %d)"
          % (tag, code, len(screens), len(nodes), len(rows)))
    for pth, nm in screens:
        print("   화면 %-28s %s" % (pth, nm))
    for pth, nm in nodes:
        print("   마디 %-28s %s" % (pth, nm))
