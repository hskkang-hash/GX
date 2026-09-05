"""WebSocket consumers for surveillance profile notifications."""

from __future__ import annotations

import json
import logging
from typing import List

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone


logger = logging.getLogger(__name__)


class SurveillanceProfileNotificationConsumer(AsyncWebsocketConsumer):
    """Broadcast surveillance profile auto-launch events to clients."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rooms: List[str] = []

    async def connect(self):
        from django.contrib.auth.models import AnonymousUser

        user = self.scope.get("user", AnonymousUser())
        if not user or user.is_anonymous:
            logger.warning("[SURVEILLANCE][WS] Anonymous connection rejected")
            await self.close()
            return

        self.rooms = []

        await self.channel_layer.group_add("surveillance_profiles_global", self.channel_name)
        self.rooms.append("surveillance_profiles_global")

        try:
            group_codes = await self._get_user_group_codes()
        except Exception as exc:
            logger.exception("[SURVEILLANCE][WS] Failed to resolve user groups: %s", exc)
            group_codes = []

        for code in group_codes:
            room = f"surveillance_profiles_{code}"
            await self.channel_layer.group_add(room, self.channel_name)
            self.rooms.append(room)

        await self.accept()

        await self.send(
            json.dumps(
                {
                    "type": "connected",
                    "message": "Connected to surveillance profile notifications",
                    "timestamp": timezone.now().isoformat(),
                    "rooms": self.rooms,
                }
            )
        )

        logger.info(
            "[SURVEILLANCE][WS] User %s subscribed to rooms: %s",
            getattr(user, "username", "unknown"),
            ", ".join(self.rooms),
        )

    async def disconnect(self, close_code):
        for room in self.rooms:
            try:
                await self.channel_layer.group_discard(room, self.channel_name)
            except Exception:
                logger.debug("[SURVEILLANCE][WS] Room cleanup failed for %s", room, exc_info=True)

        logger.info("[SURVEILLANCE][WS] Disconnected channel=%s", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Surveillance notifications are server-push only. Echo minimal ack for debugging if clients send ping.
        if text_data:
            try:
                payload = json.loads(text_data)
            except json.JSONDecodeError:
                payload = {"type": "unknown"}

            if payload.get("type") == "ping":
                await self.send(
                    json.dumps(
                        {
                            "type": "pong",
                            "timestamp": timezone.now().isoformat(),
                        }
                    )
                )

    async def surveillance_preflight(self, event):
        await self.send(
            json.dumps(
                {
                    "type": "surveillance_preflight",
                    "timestamp": event.get("timestamp"),
                    "profiles": event.get("profiles", []),
                }
            )
        )

    async def detection_message(self, event):
        """새 탐지가 났다는 **신호 하나**를 내보낸다 (UX-08).

        ★ 이 핸들러가 없는 채로 `broadcast_detection_message` 를 부르면 Channels 가
          `No handler for message type detection_message` 로 죽고, **그 그룹에 붙은
          모든 관제 세션이 끊긴다.** 「켜기」는 시그널 주석을 지우는 일이 아니라
          받는 쪽을 먼저 세우는 일이다 — 받는 쪽 없이 켜면 켜는 순간이 사고다.

        ★ 여기로 나가는 것은 **카드가 아니라 신호**다. 화면은 이것을 받고 자기
          목록 문을 다시 부른다. 카드를 여기서 만들면 화면이 그리는 목록과
          서버가 정하는 목록(5분 창 묶음 · 알림 억제)이 **두 벌**이 되고,
          두 벌은 반드시 어긋난다. 무엇이 한 장인지는 목록 문 한 곳이 정한다.
        """
        await self.send(
            json.dumps(
                {
                    "type": "detection_message",
                    "timestamp": event.get("timestamp"),
                    "message": event.get("message", {}),
                }
            )
        )

    async def surveillance_activation(self, event):
        await self.send(
            json.dumps(
                {
                    "type": "surveillance_activation",
                    "timestamp": event.get("timestamp"),
                    "profiles": event.get("profiles", []),
                }
            )
        )

    @database_sync_to_async
    def _get_user_group_codes(self) -> List[str]:
        try:
            user = self.scope.get("user")
            if not user or not user.is_authenticated:
                return []

            profile_link = getattr(user, "userprofilelink", None)
            if not profile_link or not getattr(profile_link, "group", None):
                return []

            group = profile_link.group
            codes: List[str] = []
            group_code = getattr(group, "code", None)
            if group_code:
                codes.append(str(group_code))
            else:
                codes.append(str(group.id))

            return codes
        except Exception as exc:
            logger.exception("[SURVEILLANCE][WS] Error resolving user groups: %s", exc)
            return []
