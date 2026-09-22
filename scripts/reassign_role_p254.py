# -*- coding: utf-8 -*-
"""P-254 — `order_geumsan`(id 102 · GeumSan-ETRI)를 **GX 계열로 판정**하고
역할 `order` → `fire_user` 로 옮긴다.

    세종 판정(WO-GX-20260923-07 §4 P-254):
      「ETRI 계열 테넌트는 우리 파일럿 축이고, 재배정은 M2M 한 줄이라
       되돌릴 수 있다 → `fire_user` 재배정(전/후 표 · 삭제 0).
       인수 판정으로 바뀌면 되돌린다(되돌리기는 대표 → 그때 한 줄).」

★ **이 스크립트는 아무것도 지우지 않는다.** M2M 한 줄을 옮길 뿐이다.
  계정·프로필·테넌트·비밀번호는 건드리지 않는다.
★ **되돌리는 길이 같은 파일에 있다** — `--revert`. 되돌릴 것이 남아야
  「되돌릴 수 있는 변경」이라 부를 수 있다(창 2a 의 불변).
  다만 **되돌리기는 대표 결정**이므로 이 파일은 길만 두고, 부르는 것은 그때다.
★ 기본은 **재 보기만 한다**(`--dry-run` 이 기본). 옮기려면 `--apply`.

부르는 자리: **gx-shell 안**(DB 를 직접 본다 · HTTP 0).
    MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
      -e PYTHONIOENCODING=utf-8 -w /app gx-shell \
      python /repo/scripts/reassign_role_p254.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys

import django

django.setup()

from django.apps import apps                      # noqa: E402
from django.contrib.auth import get_user_model    # noqa: E402
from django.db import transaction                 # noqa: E402

#: 세종이 이름으로 적은 한 사람. 수를 지시서가 줬고, **길은 여기서 잰다**(P-258).
TARGET_ID = 102
TARGET_USERNAME = "order_geumsan"
FROM_CODE = "order"
TO_CODE = "fire_user"


def _roles(u) -> list:
    return sorted(r.code for r in u.roles.all())


def _tenant(u) -> str:
    """사람의 테넌트는 `UserProfileLink.group` 이 정본이다.

    ⚠ `Role.group` 이 아니다 — 그것은 **역할이 정의된 스코프**이지
      사람이 속한 테넌트가 아니다(U56 이 턴 AD 에 이 자리에서 헷갈릴 뻔했다).
    """
    #: ⚠ 역참조 이름을 **추측하지 않는다.** `profile_link` 는 U56 이 쪽지에 적은
    #:   이름이지만 그것은 모델 이름이지 이 방향의 접근자가 아닐 수 있다.
    #:   그래서 **모델을 이름으로 찾아** 이 사람의 행을 직접 읽는다.
    for model in apps.get_models():
        if model.__name__ != "UserProfileLink":
            continue
        row = model.objects.filter(user_id=u.id).first()
        if row is None:
            return "(%s 에 이 사람의 행이 없다)" % model.__name__
        grp = getattr(row, "group", None)
        return getattr(grp, "name", None) or str(grp)
    return "(UserProfileLink 모델을 못 찾았다)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="실제로 옮긴다 (없으면 재 보기만)")
    ap.add_argument("--revert", action="store_true",
                    help="되돌린다 — fire_user → order. **대표 결정이다**")
    args = ap.parse_args()

    User = get_user_model()
    u = User.objects.filter(id=TARGET_ID).first()
    if u is None:
        print("[P-254] id=%d 가 없다 — 옮길 것이 없다" % TARGET_ID)
        return 1
    if u.username != TARGET_USERNAME:
        #: ★ 이름과 id 가 둘 다 맞아야 한다. 하나만 맞으면 **다른 사람**일 수 있고,
        #:   남의 역할을 옮기는 것은 되돌려도 흔적이 남는 일이다.
        print("[P-254] ★ id=%d 의 이름이 %r 이다 — 기대한 %r 이 아니다. 멈춘다"
              % (TARGET_ID, u.username, TARGET_USERNAME))
        return 2

    RoleModel = u.roles.model
    Role = apps.get_model(RoleModel._meta.app_label, RoleModel._meta.model_name)
    src = Role.objects.filter(code=FROM_CODE).first()
    dst = Role.objects.filter(code=TO_CODE).first()
    if src is None or dst is None:
        print("[P-254] 역할 코드를 못 찾았다 — %s=%s · %s=%s"
              % (FROM_CODE, src, TO_CODE, dst))
        return 3

    a_code, b_code = (TO_CODE, FROM_CODE) if args.revert else (FROM_CODE, TO_CODE)
    a_role, b_role = (dst, src) if args.revert else (src, dst)

    before = {
        "user": {"id": u.id, "username": u.username, "roles": _roles(u),
                 "is_active": u.is_active,
                 "deleted": str(getattr(u, "deleted", None)),
                 "tenant": _tenant(u)},
        "role_counts": {FROM_CODE: src.users.count(), TO_CODE: dst.users.count()},
    }
    print("[P-254] 전 · " + json.dumps(before, ensure_ascii=False))

    if not args.apply:
        print("[P-254] 재 보기만 했다 — 옮기려면 --apply (삭제 0 · M2M 한 줄)")
        return 0

    #: ★ 살아 있는 계정만 옮긴다(P-258 · `is_active AND deleted IS NULL`).
    #:   소프트삭제된 계정을 되살리는 모양이 되면 그것은 재배정이 아니다.
    if not u.is_active or getattr(u, "deleted", None) is not None:
        print("[P-254] ★ 살아 있는 계정이 아니다(is_active=%s · deleted=%s) — 멈춘다"
              % (u.is_active, getattr(u, "deleted", None)))
        return 4

    with transaction.atomic():
        u.roles.remove(a_role)
        u.roles.add(b_role)

    #: ★★ **같은 객체로 확인하지 않는다.** 방금 쓴 그 인스턴스는 제가 쓴 것을
    #:   기억하고 있어서 초록을 낸다. DB 에서 다시 읽는다.
    fresh = get_user_model().objects.get(id=TARGET_ID)
    after = {
        "user": {"id": fresh.id, "username": fresh.username,
                 "roles": _roles(fresh), "is_active": fresh.is_active,
                 "deleted": str(getattr(fresh, "deleted", None))},
        "role_counts": {FROM_CODE: Role.objects.get(code=FROM_CODE).users.count(),
                        TO_CODE: Role.objects.get(code=TO_CODE).users.count()},
        "order_보유자_남은_이름": sorted(
            x.username for x in Role.objects.get(code=FROM_CODE).users.all()),
    }
    print("[P-254] 후 · " + json.dumps(after, ensure_ascii=False))

    ok = b_code in after["user"]["roles"] and a_code not in after["user"]["roles"]
    print("[P-254] %s · 계정 살아 있음=%s · 삭제 0"
          % ("옮겼다" if ok else "★ 안 옮겨졌다",
             get_user_model().objects.filter(id=TARGET_ID).exists()))
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main())
