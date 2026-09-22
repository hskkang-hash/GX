# -*- coding: utf-8 -*-
"""`data_source` 낱말 밭의 **셋째 낱말** — 씨앗(seed) 카메라 식별의 정본 한 곳.

[턴 AC · 차선 U1 · 2026-09-22]

왜 이 파일이 필요한가 — **신호가 probe·drill 과 다르다**
--------------------------------------------------------------
`common/probe_marker.py`(probe·drill)는 **행 표식**(`track_id`)으로 가른다.
씨앗은 다르다 — `stream_monitors/management/commands/seed_dsm_events.py` 가 심는
사건은 K1 정식 경로(`record_detection`)를 그대로 지나서 나고, `track_id` 에 아무
표식도 얹지 않는다(그 커맨드의 머리말 — 「검수용 이벤트를 **실제 경로로** 심는다」의
요점이 바로 그것이다: 화면 코드에 고정값을 넣지 않는다). 그래서 표식은 **행이 아니라
카메라**에 있다 — 씨앗 카메라는 한 대(`code=GX-SEED-DSM`)이고, 그 카메라 위의 사건은
전부 씨앗이다.

★ [실측 2026-09-22] `stream_monitors.StreamMonitor.data_source`(P-224 청구 칸)는
  **이 낱말과 이름이 같지만 다른 신호다.** `scripts/verify_dead_fields.py` 의
  `DECLARED_UNWIRED` 가 그 칸을 D-514 로 「선언만 되고 새로 태어나는 카메라에 쓰는
  운영 자리가 아직 없다」로 등재해 두었다 — 지금도 `seed_dsm_events.py::_camera()`
  는 그 칸을 안 쓴다(`get_or_create` 의 `defaults` 에 없다 [실측]). 그 칸을 여기서
  같이 쓰면 **청구의 셈**(`common/billing_marks.py` · B 차선 소유)이 이 턴에 함께
  움직인다 — 그것은 이 낱말 밭이 답할 질문(「관제 화면이 씨앗이라고 말하는가」)과는
  다른 질문이고, 다른 차선의 수를 이 턴에 섞어 흔드는 일이다. 그래서 **이 파일은
  청구 칸을 건드리지 않는다** — 카메라 **코드**로만 가른다. 청구 칸 배선은 D-514
  등재문이 이름 붙인 자리(게이트 탐침·온보딩 계측기·훈련 창)와 함께 다음에 간다.

★ 코드 문자열의 정본은 **여기**다. `seed_dsm_events.py` 는 이 값을 가져다 쓴다 —
  심는 쪽이 식별자를 만들면 스크립트를 고치는 날 화면이 옛말이 된다(D-286 계열).

★ **행마다 묻지 않는다.** `apps/dsm/services.py::event_data_sources` 가 훈련 판정과
  같은 자리에서 이 파일의 `seed_stream_monitor_ids` 를 **후보 집합 하나로 한 번만**
  부른다 — `is_drill_event_for_stream` 의 N+1 교훈과 같다.

★ **App 층은 ORM 을 만지지 않는다** (DA-04 §1-1). `apps/dsm/services.py` 가 이
  파일을 통해서만 묻는다 — `tests/test_dsm_app.py::AppStaysThinTest` 가 그 경계를
  지킨다.
"""
from __future__ import annotations

#: 씨앗 카메라의 코드. `seed_dsm_events.py::_camera()` 가 심을 때 이 값을 쓴다.
SEED_CAMERA_CODE = "GX-SEED-DSM"

#: 화면·보고서가 적는 출처 이름 (GX-COPY §2 「시드(검수용)」·
#: `frontend/src/features/dsm/copy.ts::DATA_SOURCE_LABEL`).
DATA_SOURCE = "seed"


def seed_stream_monitor_ids(candidate_ids) -> set:
    """후보 중 **씨앗 카메라인 것의 pk 집합** — 한 번에 갈라 N+1 을 피한다.

    `None` 을 섞어 넘겨도 된다 — 여기서 거른다. 후보가 비면 쿼리를 아예 안 던진다.
    """
    ids = {i for i in candidate_ids if i is not None}
    if not ids:
        return set()
    from django.apps import apps

    StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
    return set(
        StreamMonitor._base_manager
        .filter(pk__in=ids, code=SEED_CAMERA_CODE)
        .values_list("pk", flat=True))


def is_seed_stream_monitor(stream_monitor_id) -> bool:
    """이벤트 하나로 묻는 갈래 — `event_data_source`(단건) 가 쓴다.

    ★ `None` 은 거짓이다 — 카메라를 모르면 씨앗이라고 우길 근거가 없다
      (`is_drill_track` 이 표식 없음을 「사람이 만든 것」으로 보는 것과 같은 기울기:
      모르면 실운영 쪽에 둔다).
    """
    if stream_monitor_id is None:
        return False
    return bool(seed_stream_monitor_ids({stream_monitor_id}))
