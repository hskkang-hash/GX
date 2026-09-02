# -*- coding: utf-8 -*-
"""기존 이벤트의 대응 진행 값을 채운다 (D-399).

왜 기본값만으로 부족한가
------------------------
0024 는 새 칸을 `occurred` 로 채운다. 그러면 **이미 사람이 판정하고 종료한 이벤트도
「아무도 안 봤다」로 보인다.** 대응 이력이 통째로 「발생」으로 돌아가는 것이고,
그 상태에서 화면을 열면 당직자가 끝난 일을 다시 접수한다.

매핑 [판정] — 인용이 아니라 우리가 정했다 (D-322)
--------------------------------------------------
지시서는 「발생→occurred, 처리→closed」 라고 적었으나, 그것은 이 저장소의 상태가
**2값이라는 전제**에서 쓰인 것이다. 실측하면 `status` 는 4값이므로 매핑도 네 줄이다:

    status=new        → occurred       아직 아무도 안 봤다
    status=confirmed  → acknowledged   **사람이 「진짜다」라고 판정했다 = 접수한 것이다.**
                                       in_progress 로 올리지 않는 이유: 판정은 「봤다」이지
                                       「조치했다」가 아니다. 안 한 일을 했다고 적지 않는다
    status=rejected   → closed         오탐이므로 대응은 끝났다
    status=closed     → closed         이미 끝났다

★ `status` 는 **건드리지 않는다.** 이 마이그레이션은 새 칸만 채운다 —
  D-293 이 지킨 판정 칸을 여기서 덮으면 오탐률이 다시 갈린다.
★ 되돌리기(reverse)는 새 칸을 기본값으로 되돌릴 뿐이다. `status` 를 복원하려 하지
  않는다 — 애초에 건드리지 않았으므로 복원할 것이 없다.
"""
from __future__ import annotations

from django.db import migrations

#: [판정] 위 표 그대로. 코드와 주석이 갈리지 않도록 **여기 하나만** 둔다.
STATUS_TO_RESPONSE = {
    "new": "occurred",
    "confirmed": "acknowledged",
    "rejected": "closed",
    "closed": "closed",
}


def forwards(apps, schema_editor):
    Event = apps.get_model("stream_monitors", "DetectionEvent")
    moved = 0
    for status, response in STATUS_TO_RESPONSE.items():
        if response == "occurred":
            continue                      # 기본값과 같다 — 건드릴 필요가 없다
        moved += Event.objects.filter(status=status).update(response_state=response)
    print(f"[MIGRATE 0025] 대응 진행 backfill — {moved}행을 기본값에서 옮겼다 (D-399)")


def backwards(apps, schema_editor):
    Event = apps.get_model("stream_monitors", "DetectionEvent")
    n = Event.objects.exclude(response_state="occurred").update(response_state="occurred")
    print(f"[MIGRATE 0025] 되돌림 — {n}행을 occurred 로. status 는 건드리지 않았다")


class Migration(migrations.Migration):

    dependencies = [
        ("stream_monitors", "0024_detectionevent_response_state"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
