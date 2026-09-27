# -*- coding: utf-8 -*-
"""FWS-F1-10 — 안전 알림 수신(풍향 급변·대피 지시·철수) — 도달·확인 (턴 AK 차선 N2).

K2 를 그대로 쓴다
------------------
「나에게 무엇이 왔는가」는 이미 K2 의 발송 대장(`list_deliveries`)이 갖고 있는 사실이다
— 채널·수신자·성공 여부·시각까지. 이 파일이 새로 하는 일은 **「내 것만」**으로
좁히는 것과, **확인(ack)** 이라는 사람의 행위를 감사 한 줄로 남기는 것 둘뿐이다.
발송(K2 send)은 관제 쪽 화면의 일이라 이 절의 범위가 아니다 — 여기서 만드는 것은
「받는 사람이 받았다고 누르는 것」이다.
"""
from __future__ import annotations

from django.apps import apps

from common import audit_writer
from kernels.k2_notify.services import list_deliveries

LOGGER_NAME = "guardianx.fws.alert_ack"
TAG = "[FWS-ALERT]"
ACTION_ACK = "alert.ack"


class AlertNotFound(Exception):
    """그런 알림이 없다 — 404. 남의 알림일 때도 이것이다(존재 여부도 새면 누출)."""


def my_alerts(*, scope, limit: int = 50) -> list[dict]:
    """FWS-F1-10 「도달」 — 나에게 실제로 간(성공한) 발송만."""
    actor = scope.require_actor()
    deliveries = list_deliveries(
        scope=scope, recipient_id=actor.pk, succeeded=True, limit=limit)
    acked = _acked_ids(actor.pk)
    return [
        {
            "delivery_id": d.delivery_id,
            "event_id": d.event_id,
            "channel": d.channel,
            "occurred_at": d.occurred_at.isoformat() if d.occurred_at else None,
            "sent_at": d.sent_at.isoformat() if d.sent_at else None,
            "acknowledged": d.delivery_id in acked,
        }
        for d in deliveries
    ]


def _model():
    return apps.get_model("logger", "AuditLogs")


def _acked_ids(user_id: int) -> set[int]:
    rows = (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=user_id, api_name=ACTION_ACK)
        .order_by("-id")[:2000]
    )
    out: set[int] = set()
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        delivery_id = payload.get("delivery_id")
        if isinstance(delivery_id, int):
            out.add(delivery_id)
    return out


def ack_alert(*, scope, delivery_id: int) -> dict:
    """FWS-F1-10 「확인」 — 이 사람이 이 알림을 봤다고 남긴다.

    ★ 남의 배달 번호로 확인을 남길 수 없다 — `my_alerts` 로 자기 목록에 있는 것만
      먼저 확인하고 그 번호로 부른다(문지기는 부르는 쪽이 목록을 좁혀 준 것에 기댄다
      — `field_reply.list_field_replies` 와 같은 얕은 좁히기이지만, 발송 이력은
      이미 `list_deliveries` 가 테넌트로 좁혀 두어서 남의 테넌트 배달 번호는애초에
      이 사람 목록에 없다).
    """
    actor = scope.require_actor()
    own = {d["delivery_id"] for d in my_alerts(scope=scope, limit=2000)}
    if delivery_id not in own:
        raise AlertNotFound(f"delivery_id={delivery_id} 가 없다")
    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=ACTION_ACK,
        outcome=audit_writer.ALLOWED, reason=f"알림 {delivery_id} 확인",
        after={"delivery_id": delivery_id}, api_name=ACTION_ACK, api_method="POST")
    return {"delivery_id": delivery_id, "acknowledged": True}
