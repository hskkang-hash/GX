# -*- coding: utf-8 -*-
"""celery 가 **찾는 이름**의 자리 (D-377 착시 ⑨ · 실측 2026-09-12).

★ 이 파일이 왜 생겼나 — 켠 줄 알았던 것이 안 돌고 있었다
--------------------------------------------------------
D-373 에서 감시(`ops_monitor_beat`)와 백업(`ops_backup_beat`)을 beat 표에 올렸고,
「주기를 등록했다」고 보고했다. **그런데 등록되지 않았다.**

    celery 의 `app.autodiscover_tasks()` 는 INSTALLED_APPS 의 각 앱에서
    **`tasks.py` 라는 이름만** 찾아 읽는다. 우리 태스크는 `common/ops_tasks.py` 에
    있었고 `common/tasks.py` 는 없었다 — 그래서 그 모듈은 워커에서 **한 번도
    import 되지 않았고**, `@shared_task` 는 실행되지 않았으며, beat 는 매일
    등록되지 않은 이름을 부를 참이었다 (`NotRegistered`).

    ▣ 그리고 그 사실은 **어디에서도 빨갛지 않았다.** beat 표에 줄이 있고, 태스크
      함수가 있고, 시험은 함수를 직접 불러 통과했다. 셋 다 초록이다.
      **이것이 착시 ⑨ 그 자체다** — 「켜기만 하고 안 도는 것」.

    ▣ 잡은 것은 사람이 아니라 시험이다:
      `backend/tests/test_dormant_wiring.py::test_every_beat_entry_points_at_a_registered_task`
      가 beat 표의 모든 줄을 등록부와 대조하면서 첫 실행에 세 줄을 뱉었다.

왜 `apps.py::ready()` 에서 import 하지 않고 이 파일을 두나
----------------------------------------------------------
`common/apps.py` 의 `ready()` 는 본문 전체가 `try/except Exception` 으로 감싸여 있다.
거기에 태스크 import 를 넣으면 **import 가 실패해도 조용히 지나간다** — 지금 고친
바로 그 실패의 다른 판이 된다. 그리고 celery 의 관례는 `tasks.py` 이므로, 다음 사람이
「이 앱의 태스크는 어디 있나」를 물을 때 **찾는 자리에 있는 것**이 낫다 (D-286).

여기서 다시 정의하지 않는다 — 본문은 `ops_tasks.py` 하나뿐이다. 두 벌은 어긋난다(D-369).
"""
from common.ops_tasks import (  # noqa: F401  — import 되는 것이 이 파일의 전부다
    camera_pulse_scan_beat,
    evidence_anchor_beat,
    heartbeat_digest_beat,
    ops_audit_purge_beat,
    ops_backup_beat,
    ops_monitor_beat,
)

__all__ = ["ops_monitor_beat", "ops_backup_beat", "ops_audit_purge_beat",
           # ★ 2026-09-24 (2파) — 이 줄에 이름이 없으면 `@shared_task` 는 **실행되지 않고**
           #   beat 는 매일 `NotRegistered` 를 낸다. 이 파일의 존재 이유가 그것이다.
           "heartbeat_digest_beat", "camera_pulse_scan_beat",
           "evidence_anchor_beat"]
