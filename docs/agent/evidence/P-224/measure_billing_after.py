# -*- coding: utf-8 -*-
"""턴 AB 차선 B — 청구 전/후 표의 「후」. **읽기만 한다.**

★ 「전」(`measure_billing_seeds.py`)과 **같은 표·같은 소프트 삭제 규칙**으로 세고,
  달라지는 것은 **청구 거름 한 줄**(`exclude_unbillable`)뿐이다. 두 수가 다른 셈으로
  나오면 그 차이는 표식의 효과가 아니라 셈의 차이다.

★ 운영 면(거름 없는 수)을 **같은 실행에서** 함께 낸다 — 「청구만 줄고 화면은 그대로」를
  한 표에서 볼 수 있어야 한다 (P-224 ③).

    MSYS_NO_PATHCONV=1 docker exec -i -e DJANGO_SETTINGS_MODULE=config.settings \
      gx-shell python manage.py shell < measure_billing_after.py
"""
import json

from django.apps import apps
from django.db.models import Count, Sum
from django.utils import timezone

from common.billing_marks import (exclude_soft_deleted, exclude_unbillable,
                                  has_marker_field)

Stream = apps.get_model("stream_monitors", "StreamMonitor")
CoreUser = apps.get_model("user", "CoreUser")
Media = apps.get_model("file_management", "UserMediaFile")
Link = apps.get_model("user", "UserProfileLink")
Group = Link._meta.get_field("group").related_model
Mark = apps.get_model("common", "BillingMark")


def billable(model, qs):
    """`kernels.k6_feedback._billable_count` 와 **같은 두 줄**이다."""
    qs = exclude_soft_deleted(qs, model)
    if has_marker_field(model):
        qs = exclude_unbillable(qs)
    return qs.distinct().count()


now = timezone.now()
out = {"measured_at": now.isoformat(timespec="seconds"),
       "marks_total": Mark._base_manager.count(),
       "marks_by_label": {},
       "tenants": []}
for row in (Mark._base_manager.values("model_label", "data_source")
            .annotate(n=Count("id")).order_by()):
    out["marks_by_label"][f"{row['model_label']}:{row['data_source']}"] = row["n"]

for g in Group._base_manager.all().order_by("pk"):
    cam_all = Stream._base_manager.filter(group=g, created_on__lt=now)
    usr_all = CoreUser._base_manager.filter(
        userprofilelink__group=g, is_active=True, date_joined__lt=now)
    med_all = Media._base_manager.filter(group=g, created_on__lt=now)
    agg = exclude_soft_deleted(med_all, Media).aggregate(
        total=Sum("file_size"), files=Count("id"))
    out["tenants"].append({
        "pk": g.pk,
        "name": getattr(g, "name", "") or getattr(g, "code", ""),
        # 운영 면 — 거름 없이. **이 수는 안 변해야 한다.**
        "cameras_screen": exclude_soft_deleted(cam_all, Stream).distinct().count(),
        "users_screen": exclude_soft_deleted(usr_all, CoreUser).distinct().count(),
        # 청구 면 — 거름 뒤.
        "cameras_billed": billable(Stream, cam_all),
        "users_billed": billable(CoreUser, usr_all),
        "media_files": int(agg["files"] or 0),
        "media_bytes": int(agg["total"] or 0),
    })

print("GXJSON_START")
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
print("GXJSON_END")
