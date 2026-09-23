# -*- coding: utf-8 -*-
"""P-266 — **열린 훈련 사건 하나** (차선 U온 · 턴 AF).

왜 이 명령이 생겼나 — 세종 판정 그대로
--------------------------------------------------------------------
온보딩 빨강 넷(U2#2 · U2#6 · U2#16 · U4#15)의 뿌리를 U온 이 지난 턴에 갈랐다:
개발 DB 전체에 「미처리(`response_state=occurred`)」 상태의 **실제(비-probe) 사건이
0건**이다 [실측 2026-09-23 · `DetectionEvent.objects.filter(response_state='occurred')
.exclude(track_id__startswith='data_source=probe').count() == 0`]. 시드 20건은 전부
`seed_dsm_events`(P-223 규약)가 **종결(closed)까지 걸어서** 심는다 — 첫날 큐가
「377시간 방치」로 읽히는 것을 막으려는 그 규약이, 동시에 「미처리 한 건」이 필요한
자리를 빈 채로 남긴다. `seed_dsm_events.py` 머리말이 이미 답을 적어 두었다:

    「미처리 한 건이 필요한 자리는 따로 심는다 … 그것은 **재는 순간에**
     `data_source=drill` 로 심고 재고 닫는 일이고, 검수용 시드가 늙어서
     대신할 일이 아니다. 잴 것을 미리 심어 두면 그 씨앗은 안 잴 때도
     화면에 서 있다.」

세종 판정(조율자 §3): **시드를 더 심지 않는다 — 열린 훈련 사건 하나로 잰다.**
이 명령이 심는 것은 정확히 그 한 건이다.

★★ 새 카메라를 만들지 않는다 — **청구 표면을 늘리지 않는다**
--------------------------------------------------------------------
새 `StreamMonitor` 행을 만들면 그 자체가 청구 표(P-224 ①)의 새 칸이고, 표식을 거는
일을 하나 더 늘린다. 이 명령은 `seed_dsm_events` 가 이미 심어 둔 씨앗 카메라
(`stream_monitors.services.seed.SEED_CAMERA_CODE` · `data_source=seed`)를 그대로
쓴다 — 그 카메라가 그 소속에 없으면 **멈춘다**(새로 만들지 않는다). 이 카메라는
이미 청구에서 빠져 있는 행이므로(카메라 관계 상속 ㉣ · `common/billing_marks.py`),
그 위에 사건을 하나 더 올려도 카메라 쪽 청구는 늘지 않는다 — 그리고 아래에서
**사건 자신에게도** 훈련 표식을 두 겹(㉠ 행 표식 + ㉢ 곁표)으로 건다.

★★ 순서가 이 일의 전부다 — `mark_unbillable` 을 만든 바로 다음 줄에서
--------------------------------------------------------------------
`record_detection`(K1 실제 경로)이 돌려주는 `event_id` 를 받는 **바로 다음 줄**에서
`common.billing_marks.mark_unbillable(obj, "drill", …)` 를 부른다. 그 사이에 청구를
읽는 코드를 두지 않는다 — 두면 그 창이 「표식 없이 존재한 순간」이고, 그 창에서
청구 셈이 지나가면 이 행은 고객 사건과 똑같이 청구에 든다(`seed_gxseed_role_order.py`
머리말과 같은 규율 — 거기는 역할을, 여기는 사건 자신을 표식보다 먼저 만든다는 점만
다르다).

★ `track_id` 표식(㉠)만으로도 이미 청구에서 빠진다 — `DetectionEvent` 는
  `track_id` 칸을 가지고 있어 `exclude_unbillable` 의 첫 갈래가 그대로 걸린다
  (`common/probe_marker.py::drill_mark`). `mark_unbillable` 곁표(㉢)는 **덧댄 증거**다
  — 두 축이 갈리는 날에도(예: 다음 사람이 `track_id` 정의를 좁히는 날) 이 행은
  여전히 청구 밖이어야 한다는 것을 곁표가 독립적으로 보증한다.

★ 「청구 0 증가」를 **전역 합계**가 아니라 **이 행 하나를 콕 집은 대조**로 증명한다
--------------------------------------------------------------------
이 저장소는 지금 차선 5개가 **같은 DB 를 동시에** 쓴다(턴 AF §1). 다른 차선이 그 사이
사건을 열고 닫으면 `count_events` 의 **전역 합계**는 내 행과 무관하게 흔들린다 —
그 흔들림을 「청구가 늘었다/안 늘었다」로 읽으면 거짓 판정이 된다. 그래서 이 스크립트는
전역 전/후 합계도 참고로 찍지만(⚠ 표시), **판정은 이 행 하나만 골라** 묻는다:

    exclude_unbillable(DetectionEvent.objects.filter(pk=event_id)).exists()

`False` 면 이 행은 청구 쿼리에서 빠진 것이고, 그것이 「훈련이라 청구되지 않는다」의
유일한 증거다. `True` 면 표식이 안 걸린 것이므로 스크립트는 **멈춘다**(청구가 새는
채로 넘기지 않는다).

★ 화면이 「훈련」이라고 말하는가 — **읽는 그 함수로** 잰다
--------------------------------------------------------------------
배지를 그리는 결정은 화면이 하지 않는다. `apps/dsm/services.py::event_data_source`
(상세)와 `event_data_sources`(목록·큐)가 정본이고, 상세 API(`GET /api/dsm/events/{id}`)
가 실제로 내보내는 것과 같은 호출을 그대로 부른다: `services.event_detail` →
`services.event_data_source`. 값이 `"drill"` 이면 `frontend/src/features/dsm/copy.ts`
의 `dataSourceBadge.drill = '훈련'` 이 화면에 그대로 그려진다 [실측 위치].

사용법
------
    docker exec -w /app gx-shell python manage.py seed_training_incident \\
        --user gxseed_u2_manager

    # 이미 있으면 다시 만들지 않는다(멱등 — 고정 run 표로 찾는다) · 세기만:
    docker exec -w /app gx-shell python manage.py seed_training_incident \\
        --user gxseed_u2_manager --report

⚠ **지우는 길을 두지 않는다.** 사건·카메라·계정을 지우는 것은 대표 결정이다
  (턴 AF 규약 「하지 마라」). 다시 잴 필요가 있으면 고정 run 표
  (`RUN_ID`)로 같은 행을 다시 찾아 재는 것으로 충분하다 — 새 행을 또 만들지 않는다.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

#: 고정 run 표. **바뀌지 않는다** — 재실행이 같은 행을 다시 찾아야 멱등이 선다.
RUN_ID = "p266open"
EVENT_TYPE = "fire"
SEVERITY = "critical"
REASON = ("P-266 온보딩 열린 훈련 사건 — U2#2·U4#15(그리고 같은 뿌리의 U2#6·U2#16) "
          "재측용. 청구 제외(순서: mark 가 record_detection 바로 다음)")


class Command(BaseCommand):
    help = "P-266 — 열린(미처리) 훈련 사건 하나를 K1 실제 경로로 심고 청구 0 증가를 실측한다"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", default="gxseed_u2_manager",
            help="이 계정의 소속(tenant)에 심는다. U2·U4 시드 계정은 같은 소속(ETRI-Group) "
                 "이므로 기본값 하나로 둘 다 잰다 (기본: gxseed_u2_manager)")
        parser.add_argument("--report", action="store_true",
                            help="세기만 한다 — 아직 없으면 아무것도 만들지 않는다")

    # ── 소속 ─────────────────────────────────────────────────────────────
    def _group_and_user(self, username):
        from django.contrib.auth import get_user_model

        from common.tenant_filters import get_user_group

        User = get_user_model()
        user = User._base_manager.filter(username=username).first()
        if user is None:
            raise CommandError(f"[TRAIN] 계정이 없다: {username}")
        group = get_user_group(user)
        if group is None:
            raise CommandError(f"[TRAIN] {username} 에 소속이 없다 — 심어도 안 보인다")
        return user, group

    def _camera(self, group):
        """씨앗 카메라를 **그대로 쓴다.** 없으면 멈춘다 — 새로 만들지 않는다."""
        from stream_monitors.models import StreamMonitor
        from stream_monitors.services.seed import SEED_CAMERA_CODE

        cam = StreamMonitor._base_manager.filter(
            code=SEED_CAMERA_CODE, group_id=group.pk).first()
        if cam is None:
            raise CommandError(
                f"[TRAIN] 씨앗 카메라({SEED_CAMERA_CODE})가 소속 {group.pk} 에 없다 — "
                "먼저 `seed_dsm_events --user <같은 소속 계정>` 을 돌려야 한다. "
                "이 스크립트는 새 카메라를 만들지 않는다(청구 표면을 늘리지 않는다).")
        return cam

    def _existing(self, cam_pk, track_id):
        from stream_monitors.models import DetectionEvent

        return (DetectionEvent._base_manager
                .filter(stream_monitor_id=cam_pk, track_id=track_id)
                .order_by("id").first())

    def handle(self, *args, **opts):
        from common.probe_marker import DRILL_MARKER, drill_mark
        from common.tenant_scope import TenantScope

        user, group = self._group_and_user(opts["user"])
        cam = self._camera(group)
        track_id = drill_mark(RUN_ID)

        existing = self._existing(cam.pk, track_id)
        if opts["report"]:
            if existing is None:
                self.stdout.write("[TRAIN] 아직 없다 — 만들려면 --report 없이 실행")
                return 0
            self._verify_and_report(existing.pk, user_group_scope=TenantScope.of(user))
            return 0

        if existing is not None:
            self.stdout.write(
                f"[TRAIN] 이미 있다(멱등) — 다시 만들지 않는다: event_id={existing.pk}")
            self._verify_and_report(existing.pk, user_group_scope=TenantScope.of(user))
            return 0

        from common.billing_marks import (exclude_unbillable, mark_unbillable,
                                          marked_unbillable_ids)
        from kernels.k1_event import count_events, record_detection
        from stream_monitors.models import DetectionEvent

        scope_user = TenantScope.of(user)
        scope_pipe = TenantScope.system(
            reason="P-266 훈련 사건 시드 — 탐지 파이프라인에는 요청자가 없다 (D-281)")

        # ── 청구(전) — 전역 참고값(⚠ 다른 차선과 공유하는 수) ─────────────
        before_total = count_events(scope=scope_user)
        self.stdout.write(
            f"[TRAIN] [실측] 청구 셈(전, count_events, 소속 {group.pk}) = {before_total} "
            "(⚠ 참고값 — 동시에 도는 다른 차선이 이 수를 함께 움직인다)")

        result = record_detection(
            scope=scope_pipe, stream_monitor_id=cam.pk,
            event_type=EVENT_TYPE, severity=SEVERITY,
            occurred_at=timezone.now(),
            track_id=track_id,
        )
        event_id = result.event_id
        self.stdout.write(
            f"[TRAIN] [실측] record_detection(K1) 호출 → event_id={event_id} · "
            f"track_id={track_id!r}")

        # ── ★★ 순서: mark_unbillable 을 만든 바로 다음 줄에서 ──────────────
        #   사이에 청구를 읽는 코드를 두지 않는다 — 두면 그 창이 「표식 없이
        #   존재한 순간」이고, 그 창에서 청구 셈이 지나가면 새는 것이 된다.
        obj = DetectionEvent._base_manager.get(pk=event_id)
        mark_unbillable(obj, "drill", reason=REASON)
        self.stdout.write(
            f"[TRAIN] [실측] mark_unbillable 완료 — record_detection 바로 다음 줄 "
            f"(event_id={event_id} · source=drill)")

        after_total = count_events(scope=scope_user)
        self.stdout.write(
            f"[TRAIN] [실측] 청구 셈(후, count_events, 소속 {group.pk}) = {after_total} "
            f"(전 {before_total} → 후 {after_total} · Δ={after_total - before_total} · "
            "⚠ 여전히 참고값이다 — 아래 「격리 대조」가 판정이다)")

        # ── 격리 대조 — 판정은 이 행 하나로만 한다 ─────────────────────────
        in_billing = exclude_unbillable(
            DetectionEvent._base_manager.filter(pk=event_id)).exists()
        marked_ids = marked_unbillable_ids(DetectionEvent)
        self.stdout.write(
            f"[TRAIN] [실측] [판정] 이 행이 청구 쿼리(exclude_unbillable)에 "
            f"남아있는가 = {in_billing} (False 여야 훈련이다) · "
            f"BillingMark 곁표에 있는가 = {event_id in marked_ids}")
        if in_billing:
            raise CommandError(
                f"[TRAIN] ★★ event_id={event_id} 가 청구 쿼리에서 안 빠졌다 — "
                "훈련 표식이 안 걸렸다. 청구가 새는 채로 두지 않는다 — 멈춘다.")

        self._verify_and_report(event_id, user_group_scope=scope_user)
        return 0

    # ── 독립 재조회 + 화면 판정 ─────────────────────────────────────────
    def _verify_and_report(self, event_id, *, user_group_scope):
        """같은 인스턴스로 확인하지 않는다 — 새로 읽는다."""
        from common.probe_marker import DRILL_MARKER
        from stream_monitors.models import DetectionEvent

        fresh = DetectionEvent._base_manager.get(pk=event_id)
        self.stdout.write(
            f"[TRAIN] [실측] 독립 재조회 · event_id={fresh.pk} · "
            f"response_state={fresh.response_state!r} (occurred 여야 '열린' 사건) · "
            f"severity={fresh.severity} · stream_monitor_id={fresh.stream_monitor_id} · "
            f"track_id={fresh.track_id!r} · "
            f"is_drill_track={fresh.track_id.startswith(DRILL_MARKER)}")

        # ── 화면이 실제로 부르는 그 함수로 배지를 잰다 (상세 API 와 같은 경로) ──
        from apps.dsm import services

        try:
            view = services.event_detail(scope=user_group_scope, event_id=event_id)
            badge = services.event_data_source(view=view)
        except Exception as exc:                          # noqa: BLE001
            badge = f"★ 못 잰다: {type(exc).__name__}: {exc}"
        self.stdout.write(
            f"[TRAIN] [실측] services.event_data_source(상세 API 와 같은 호출) = "
            f"{badge!r} — 'drill' 이면 copy.ts dataSourceBadge.drill='훈련' 이 "
            "화면에 그려진다")

        if fresh.response_state != "occurred":
            self.stdout.write(
                "[TRAIN] ⚠ response_state 가 occurred 가 아니다 — 이미 누가 접수했다. "
                "열린 사건이 필요하면 새 run 표로 다시 심어야 한다(이 스크립트는 "
                "이미 있는 행을 대신 되돌리지 않는다 — 대표 결정)")
