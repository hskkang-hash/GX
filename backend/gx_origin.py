# ⚠ 일회용 진단 스크립트 · 제품 코드가 아니다 · 아무도 import 하지 않는다 (턴 O 확인)
# -*- coding: utf-8 -*-
"""P-112 origin classification of every CoreUser row. Read-only. No credential values printed."""
import os, django, json, hashlib, collections
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.apps import apps
U = apps.get_model("user", "CoreUser")
UPL = apps.get_model("user", "UserProfileLink")

# ★ [턴 O · 2026-09-10 · 영실] 자리표 상수를 환경에서 읽게 바꿨다.
#   이 파일은 턴 N 에서 차선이 끊기며 남은 **일회용 진단 스크립트**다(09-08 12:49 ·
#   추적 안 됨 · 부르는 곳 0). 그런데 자리가 `backend/`(앱 패키지) 안이고 비밀번호가
#   상수로 박혀 있었다. 값은 회전으로 무력화됐지만 **상수를 남기면 다음 사람이 복사한다**.
#   삭제는 대표 권한이라 하지 않았다 — 옮기거나 지우는 것은 판정으로.
SHARED = os.environ.get("GX_ORIGIN_SHARED_PW", "")

def email_class(e):
    e = (e or "").strip().lower()
    if not e or "@" not in e:
        return "none"
    d = e.rsplit("@", 1)[1]
    if d.endswith(".invalid"):
        return "reserved-invalid:" + d          # RFC2606 -- can never receive mail
    if d in ("yopmail.com", "mailinator.com", "10minutemail.com", "guerrillamail.com"):
        return "disposable-mail:" + d
    if d in ("example.com", "example.org", "example.net", "test.com", "localhost"):
        return "reserved-example:" + d
    return "real-routable:" + d                 # <-- the only class that can reach a human

rows = []
qs = U.all_objects.all() if hasattr(U, "all_objects") else U.objects.all()
for u in qs.order_by("id"):
    links = list(UPL.all_objects.filter(created_by=u)) if False else []
    upl = UPL.objects.filter(email=u.email).first()
    try:
        upl2 = u.userprofilelink.all()
        upl2 = list(upl2)
    except Exception:
        upl2 = []
    emp = ";".join(sorted({(l.employee_id or "") for l in upl2 if l.employee_id}))
    grp = ";".join(sorted({(l.group.name if l.group else "") for l in upl2 if l.group}))
    rows.append(dict(
        id=u.id, username=u.username,
        shared_pw=bool(u.check_password(SHARED)),
        su=bool(u.is_superuser), staff=bool(u.is_staff), active=bool(u.is_active),
        deleted=bool(getattr(u, "deleted", None)),
        joined=u.date_joined.isoformat() if u.date_joined else None,
        created_on=u.created_on.isoformat() if getattr(u, "created_on", None) else None,
        created_by=(u.created_by.username if getattr(u, "created_by", None) else None),
        last_login=u.last_login.isoformat() if u.last_login else None,
        email_class=email_class(u.email),
        emp_id=emp, group=grp,
        nroles=u.roles.count() if hasattr(u, "roles") else -1,
        pw_algo=(u.password or "").split("$")[0],
        last_change_password=u.last_change_password.isoformat() if u.last_change_password else None,
        password_expiry_date=u.password_expiry_date.isoformat() if u.password_expiry_date else None,
    ))
print(json.dumps(rows, ensure_ascii=False))
