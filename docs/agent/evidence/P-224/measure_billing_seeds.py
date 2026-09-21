# -*- coding: utf-8 -*-
"""턴 AB 차선 B — 청구 전/후 표의 「전」. 읽기만 한다."""
import json
from django.apps import apps
from django.db.models import Count, Sum
from django.utils import timezone

from common.billing_marks import exclude_soft_deleted

Stream = apps.get_model("stream_monitors", "StreamMonitor")
CoreUser = apps.get_model("user", "CoreUser")
Media = apps.get_model("file_management", "UserMediaFile")
Link = apps.get_model("user", "UserProfileLink")
Group = Link._meta.get_field("group").related_model

now = timezone.now()
out = {"measured_at": now.isoformat(timespec="seconds"),
       "group_model": Group._meta.label_lower,
       "tenants": []}

for g in Group._base_manager.all().order_by("pk"):
    cam_qs = exclude_soft_deleted(
        Stream._base_manager.filter(group=g, created_on__lt=now), Stream)
    usr_qs = exclude_soft_deleted(
        CoreUser._base_manager.filter(userprofilelink__group=g, is_active=True,
                                      date_joined__lt=now).distinct(), CoreUser)
    med_qs = exclude_soft_deleted(
        Media._base_manager.filter(group=g, created_on__lt=now), Media)
    agg = med_qs.aggregate(total=Sum("file_size"), files=Count("id"))
    row = {
        "pk": g.pk,
        "name": getattr(g, "name", "") or getattr(g, "code", ""),
        "cameras_billed": cam_qs.distinct().count(),
        "users_billed": usr_qs.distinct().count(),
        "media_files": int(agg["files"] or 0),
        "media_bytes": int(agg["total"] or 0),
    }
    out["tenants"].append(row)

# ── 정황 분류 (청구 규칙이 아니라 **진단**이다 · D-280) ────────────────────
etri = [t for t in out["tenants"] if t["users_billed"] and t["cameras_billed"]]
detail = {}
for g in Group._base_manager.all().order_by("pk"):
    cam_qs = exclude_soft_deleted(
        Stream._base_manager.filter(group=g, created_on__lt=now), Stream)
    cams = [{"pk": c.pk, "code": c.code, "name": c.name} for c in cam_qs.distinct()]
    usr_qs = exclude_soft_deleted(
        CoreUser._base_manager.filter(userprofilelink__group=g, is_active=True,
                                      date_joined__lt=now).distinct(), CoreUser)
    users = []
    for u in usr_qs:
        link = Link._base_manager.filter(user=u, group=g).first()
        users.append({"pk": u.pk, "username": u.username,
                      "employee_id": getattr(link, "employee_id", None)})
    if cams or users:
        detail[str(g.pk)] = {"name": getattr(g, "name", ""),
                             "cameras": cams, "users": users}
out["detail"] = detail
out["has_data_source_field"] = {
    "stream_monitors.streammonitor":
        "data_source" in {f.name for f in Stream._meta.get_fields()},
    "user.coreuser":
        "data_source" in {f.name for f in CoreUser._meta.get_fields()},
    "file_management.usermediafile":
        "data_source" in {f.name for f in Media._meta.get_fields()},
}
print("GXJSON_START")
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
print("GXJSON_END")
