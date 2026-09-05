"""
Django signals for surveillance app.
Handles VideoAnalysis post_save to broadcast detection messages via WebSocket.
"""

import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from core.common.constant import Language

# ★ [UX-08 · 2026-09-05] 관제 화면이 읽는 표는 **이것**이다. `VideoAnalysis` 가 아니다.
#   모델을 여기서 만지지 않는다 — sender 로만 쓴다(두드릴 자리를 고르는 데에만 필요하다).
from stream_monitors.models import DetectionEvent
from surveillance.models import VideoAnalysis
from surveillance.services.surveillance_dashboard_service import SurveillanceDashboardService
from common.constant import MESSAGE_ENUM

logger = logging.getLogger(__name__)


# ★ [UX-08 · 2026-09-05] **주석을 풀었다.** 두 겹으로 꺼져 있던 것 중 첫 겹이다.
#   두 번째 겹(`SurveillanceConfig.ready()` 가 이 모듈을 import 하는 것)은 apps.py 에 섰다.
#   ⚠ 풀기 전에 받는 쪽을 먼저 세웠다 — `consumers.py` 에 `detection_message` 핸들러가
#     없으면 이 한 줄이 그 그룹의 **모든 세션을 끊는다.** 켜기의 순서가 그것이다.
@receiver(post_save, sender=VideoAnalysis)
def video_analysis_post_save(sender, instance: VideoAnalysis, created: bool, **kwargs):
    """
    Signal handler for VideoAnalysis post_save.
    Broadcasts detection message via WebSocket when new VideoAnalysis with analysis_path is created/updated.

    Args:
        sender: VideoAnalysis model class
        instance: VideoAnalysis instance that was saved
        created: True if this is a new instance, False if update
        **kwargs: Additional signal arguments
    """
    # Only process if analysis_path exists and is not empty
    if not instance.analysis_path or instance.analysis_path.strip() == '':
        return

    # Only process if not deleted
    if instance.deleted:
        return

    try:
        # Generate ping message in English (default for socket, frontend will call API for user's language)
        drone_name = instance.drone_name or 'Unknown Drone'
        now = timezone.now()

        # Ping socket with simple notification that new detection is available
        # Frontend can then call API to get detailed messages in user's language
        ping_message = {
            "id": f"video_analysis_{instance.id}",
            "message": f"New detection data available from {drone_name}",  # English default for socket
            "category": "notification",
            "count": 1,
            "datetime": now.isoformat(),
            "date": now.date().isoformat(),
            "relative_time": "just now",
            "color": "#2196F3",
            "icon_type": "info",
            "video_analysis_id": instance.id,
            "drone_name": drone_name,
            "analysis_path": instance.analysis_path,
        }

        # ★ 폭주를 합친다 — 재난 때 저장마다 채널 레이어를 때리면 그 자체가 장애다.
        #   억제가 아니라 합치기다: 합쳐진 사이에 늘어난 것도 다음 두드림에 함께 온다.
        from common.live_ping import PING_COALESCE_SECONDS
        from django.core.cache import cache

        if not cache.add("gx:ux08:va-ping", 1, timeout=PING_COALESCE_SECONDS):
            return

        # Broadcast via WebSocket
        SurveillanceDashboardService.broadcast_detection_message(ping_message)
        logger.info(f"[SURVEILLANCE][SIGNAL] Broadcasted detection ping for VideoAnalysis #{instance.id}")

    except Exception as e:
        logger.exception(f"[SURVEILLANCE][SIGNAL] Error broadcasting detection ping for VideoAnalysis #{instance.id}: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# ★ [UX-08 · 2026-09-05 · 차선 C2] **그 전등의 스위치는 이것이었다.**
# ═══════════════════════════════════════════════════════════════════════════
#
# 무엇을 재고 무엇이 나왔나 [실측 2026-09-05]
# -------------------------------------------
# 위의 `VideoAnalysis` 시그널은 **드론 멀티스트림 화면**의 두드림이다. 관제 화면
# (대시보드 · 이벤트 목록 · 단일 초점 큐 · 카메라 격자)이 읽는 것은 `DetectionEvent`
# 이고, 그 행은 `VideoAnalysis` 를 한 번도 지나지 않는다. 즉 **위의 스위치를 켜도
# 관제 화면에는 한 장도 안 붙는다** — 켜 놓고 「안 뜬다」를 다시 찾게 되는 자리다.
#
#     grep -rn "ping_detection" backend/ →
#         common/live_ping.py:52                                  (정의)
#         stream_monitors/services/detection_event_bridge.py:329  (부르는 곳 · 단 하나)
#
# 두드림은 **AI gRPC 파이프라인 한 갈래에서만** 나가고 있었다. `record_detection` 을
# 부르는 다른 경로 — 맥박 군집 두절(`camera_pulse.scan_clusters`) · 검수 시드 —
# 로 태어난 이벤트는 화면을 **한 번도 두드리지 않았다.** 「코드는 있고 꺼져 있다」가
# 아니라 **「켜져 있는데 다른 전등이다」**였다.
#
# 왜 시그널인가 — 두드림을 **행이 태어나는 사실**에 매단다
# --------------------------------------------------------
# 갈래마다 손으로 `ping_detection` 을 부르면 갈래가 하나 늘 때마다 조용히 빠진다.
# 그것이 지금 상태다. `DetectionEvent` 의 post_save 에 매달면 **어느 경로로 나든**
# 두드림이 나간다 — 새 갈래를 만든 사람이 이 파일을 몰라도 된다.
#
# ⚠ 받는 쪽이 먼저다. `consumers.py::detection_message` 는 **이미 서 있다**
#   (턴 C). 핸들러 없이 그룹으로 쏘면 그 그룹의 모든 관제 세션이 끊긴다 —
#   켜기의 순서가 그것이다.
#
# ★ 여기서 **다시 하지 않는 것**: 훈련 모드 · 중복 억제(10초) · 알림 억제(5분) ·
#   소유 상속. 전부 커널(K1)이 이미 했다. 이 자리가 하는 일은 **문을 두드리는 것**
#   하나뿐이고, 두드림에는 자료가 실리지 않는다(카드가 아니라 신호 · live_ping 머리말).
@receiver(post_save, sender=DetectionEvent)
def detection_event_post_save(sender, instance, created: bool, **kwargs):
    """`DetectionEvent` 가 나거나 접히면 관제 화면을 한 번 두드린다 (UX-08).

    ★ **모든 저장에 두드리지 않는다.** 판정(오탐)·대응 진행·종결도 이 표를 저장하지만
      그것은 「새 탐지」가 아니다. 두 가지에만 두드린다:

        ① 새로 생긴 행                        `created=True`
        ② 접힌 관측 (`last_seen_at` 갱신)     카드의 「×N」이 올라가므로 화면이 바뀐다

      ②를 빼면 「7건이 났는데 화면은 그대로」가 된다(배지만 안 오른다). ①만도 ②만도
      아닌 저장을 두드리면 화면이 아무것도 안 바뀐 채 목록을 다시 읽는다 — 관제실
      화면 여럿이 밤새 그러면 그 자체가 부하다.

    ★ **커밋 뒤에** 두드린다. `record_detection` 은 `@transaction.atomic` 이므로
      이 시그널은 **아직 커밋되지 않은 트랜잭션 안**에서 온다. 그 자리에서 두드리면
      화면이 목록을 다시 읽는 순간 그 행이 **아직 없고**, 화면은 다음 주기 갱신까지
      아무것도 못 본다 — 두드림이 있으나 마나가 된다. 롤백된 이벤트로 두드리지
      않는 것도 같은 한 줄이 함께 지킨다.

    ★ 실패를 위로 던지지 않는다. 화면 갱신이 못 나갔다고 탐지 **기록**이 실패해서는
      안 된다 — 알림과 기록의 순서를 뒤집는 것이 된다. 다만 조용히 삼키지도 않는다:
      `ping_detection` 이 못 보낸 것을 경고로 남긴다.
    """
    if not created:
        fields = kwargs.get("update_fields") or ()
        if "last_seen_at" not in set(fields):
            return

    stream_monitor_id = instance.stream_monitor_id
    if stream_monitor_id is None:
        # 카메라 없는 이벤트는 방을 고를 수 없다. 전역으로 쏘지 않는다 —
        # 방을 잘못 고르면 남의 화면이 우리 때문에 다시 읽는다.
        return

    def _knock():
        try:
            from common.live_ping import ping_detection
            # ★ 방 고르기를 **다시 짜지 않는다** — 이미 한 곳에 있다(D-212).
            #   두 벌이면 갈리고, 갈린 쪽은 남의 방으로 쏜다.
            from stream_monitors.services.detection_event_bridge import _tenant_code_of

            ping_detection(tenant_code=_tenant_code_of(stream_monitor_id),
                           reason="detection")
        except Exception:  # noqa: BLE001 — 두드림 때문에 기록이 죽지 않는다
            logger.warning(
                "[UX-08][SIGNAL] DetectionEvent #%s 두드림 실패 — 목록은 주기 "
                "갱신으로 계속 산다", instance.pk, exc_info=True)

    transaction.on_commit(_knock)
