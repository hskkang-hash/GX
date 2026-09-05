"""
Django signals for surveillance app.
Handles VideoAnalysis post_save to broadcast detection messages via WebSocket.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from core.common.constant import Language

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
