# -*- coding: utf-8 -*-
"""K2 — **웹푸시 발송 문** (P-160 ③ · 2026-09-17 · 턴 T · 차선 U3).

왜 이 모듈이 지금 태어나는가
----------------------------
턴 S 에 U3 가 `send_webpush` 공개 한 줄을 청했고 조율자가 **넣지 않았다** — 아무도
부르지 않는 공개 면은 잠든 코드다(D-377 · `write_surfaces_v11.yaml` 「턴 S 병합 결과」).
이 모듈은 **부르는 쪽과 같은 변경**에서 열린다: `apps/dsm/notify_prefs.send_test_push`
가 이 문을 타고, 결과는 `deliveries` 행(`channel=webpush`)으로 남는다.

두 갈래가 이 모듈을 쓴다
------------------------
    ① **규칙 경로** — 사건 → 규칙(채널 `webpush`) → 구독자 → `WebPushChannel.send`.
       `services.resolve_recipients` 가 `webpush` 채널의 수신자에게 **메일 주소 대신
       구독 한 벌**(JSON)을 `address` 로 준다 — 이 모듈의 `subscription_addresses` 가
       그 값을 만든다. 구독이 없는 사람은 수신자 목록에서 **빠진다**(주소 없는 편지는
       보낼 수 없고, 「보냈다」로 적히지도 않는다).
    ② **시험 경로** — `send_webpush(*, scope, subscription, title, body, event_id)`.
       App 의 「내 기기로 지금 한 통」이 부른다. 행은 **훈련 표식**(`recipient_address`
       가 `drill:` 로 시작)을 달고, `services.suppress` 는 그 행을 세지 않는다 —
       시험 한 통이 5분 억제로 **다음 진짜 경보를 삼키지 않게**(턴 S 시험이 지키던 그 사실).

⚠ 값을 남기지 않는다 — `recipient_address` 에는 엔드포인트가 아니라 **지문 12자**만
  적는다. 푸시 엔드포인트는 그 기기로 알림을 밀어 넣는 주소이고, 발송 이력은 화면·
  보고서·CSV 로 나가는 표다. VAPID 값은 어댑터가 환경변수에서 읽고 여기서는 **이름만**
  다룬다(D-204).

⚠ **구독 정본은 감사 한 줄이다**(`apps/dsm/notify_prefs.py` §2 머리말). 커널은 App 을
  import 할 수 없으므로(D-278) 같은 감사 행을 **같은 규칙**으로 읽는다 — 상수
  (`SUBSCRIPTION_LOGGER` · `ACTION_SUBSCRIBE` · `ACTION_TEST_SEND`)는 그쪽과 글자가
  같아야 한다. `tests/test_u3_webpush_send.py::ConstantsMatchTest` 가 두 벌이 갈리는
  것을 본다.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common.tenant_filters import assert_scoped, require_user_group
from common.tenant_scope import TenantScope
from kernels.k2_notify import channels as channel_registry
from kernels.k2_notify.exceptions import EventNotFound, InvalidNotifyInput, K2Error
from kernels.k2_notify.schemas import DeliveryView

log = logging.getLogger(__name__)

#: 구독 감사 행의 이름 — `apps/dsm/notify_prefs.py` 와 **글자가 같아야 한다**(머리말 ⚠).
SUBSCRIPTION_LOGGER = "guardianx.dsm.push_subscription"
ACTION_SUBSCRIBE = "push.subscribe"
ACTION_TEST_SEND = "push.test_send"

#: 발송 이력의 채널 이름. `channels.WebPushChannel.name` 과 같다.
WEBPUSH = channel_registry.WebPushChannel.name

#: 훈련(시험) 발송 행의 표식 — `recipient_address` 머리. `services.suppress` 가 이 머리를
#: 가진 행을 **억제 근거에서 뺀다.**
DRILL_ADDRESS_PREFIX = "drill:"

#: 차단 시간대 안이라 **보내지 않은** 행의 사유 이름. 화면·시험이 이 이름으로 묻는다(D-212).
QUIET_HOURS_REASON = "quiet_hours"
#: 사람이 M4 에서 채널을 골랐는데 그 채널이 아닐 때의 사유 이름.
CHANNEL_NOT_CHOSEN_REASON = "channel_not_chosen"


class WebPushNotConfigured(K2Error):
    """VAPID 자격·발송기가 이 환경에 없다. **이름만** 들고 있다 — 값은 없다."""

    def _init__(self, missing_env: list[str], reason: str = "") -> None:
        self.missing_env = list(missing_env)
        super().__init__(reason or (
            "웹푸시 자격이 이 환경에 없습니다 — 비어 있는 환경변수: "
            + ", ".join(self.missing_env)))


def webpush_missing_env(*, scope: TenantScope) -> list[str]:
    """비어 있는 VAPID 환경변수 **이름**. 값은 읽되 돌려주지 않는다.

    `scope` 는 D-281 의 규약이다 — 테넌트 데이터를 만지지 않지만 면제를 열지 않는다
    (면제 하나가 다음 함수의 문이 된다 · `channels.py` 머리말). 요청자 없는 호출은 거절한다.
    """
    require_user_group(scope.require_actor())      # 기관 없는 요청자는 이 이름도 못 묻는다
    return _missing_env()


def _missing_env() -> list[str]:
    return [name for name in (channel_registry.WebPushChannel.PUBLIC_ENV,
                              channel_registry.WebPushChannel.PRIVATE_ENV,
                              channel_registry.WebPushChannel.SUBJECT_ENV)
            if not (os.environ.get(name, "") or "").strip()]


def _fingerprint(endpoint: str) -> str:
    """엔드포인트의 지문 12자 — 밖으로 나가는 유일한 식별자(`notify_prefs.endpoint_fingerprint`)."""
    return hashlib.sha256((endpoint or "").encode("utf-8")).hexdigest()[:12]


def _payload_of(row) -> dict:
    raw = getattr(row, "data_after", None)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (str, bytes)):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _live_subscriptions(user_id: int) -> list[dict]:
    """이 사람의 살아 있는 구독들(기기마다 마지막 줄이 답한다). 값은 밖으로 안 나간다."""
    if not user_id:
        return []
    Audit = apps.get_model("logger", "AuditLogs")
    rows = (Audit._base_manager
            .filter(logger_name=SUBSCRIPTION_LOGGER, user_id=user_id)
            .exclude(api_name=ACTION_TEST_SEND)
            .order_by("-id")[:2000])
    seen: dict[str, dict] = {}
    for row in rows:
        payload = _payload_of(row)
        fp = str(payload.get("endpoint_sha12") or "")
        if not fp or fp in seen:
            continue
        seen[fp] = {
            "live": str(payload.get("action") or "") == ACTION_SUBSCRIBE,
            "subscription": {
                "endpoint": str(payload.get("endpoint") or ""),
                "keys": {"p256dh": str(payload.get("p256dh") or ""),
                         "auth": str(payload.get("auth") or "")},
            },
        }
    return [s["subscription"] for s in seen.values() if s["live"]]


def _subscription_addresses(user_id: int) -> tuple[str, ...]:
    """규칙 경로가 쓰는 **주소들** — 구독 한 벌을 JSON 문자열로. 구독 0이면 빈 튜플."""
    return tuple(json.dumps(sub, separators=(",", ":"))
                 for sub in _live_subscriptions(user_id))


def _address_label(address: str) -> str:
    """`deliveries.recipient_address` 에 적을 값 — **지문만**. 주소가 구독 JSON 이면 지문으로 접는다."""
    sub = channel_registry.WebPushChannel._subscription(address)
    if sub is None:
        return (address or "")[:255]
    return f"{WEBPUSH}:{_fingerprint(sub.get('endpoint', ''))}"


def _validated(subscription) -> dict:
    if not isinstance(subscription, dict):
        raise InvalidNotifyInput("subscription 은 {endpoint, keys{p256dh, auth}} 사전이어야 합니다.")
    parsed = channel_registry.WebPushChannel._subscription(json.dumps(subscription))
    if parsed is None:
        raise InvalidNotifyInput(
            "구독 한 벌을 읽지 못했습니다 — endpoint 와 keys(p256dh·auth)가 함께 있어야 합니다.")
    return parsed


@transaction.atomic
def send_webpush(*, scope: TenantScope, subscription: dict, title: str, body: str,
                 event_id: int) -> DeliveryView:
    """구독 한 벌로 **한 통** 보내고, 결과를 `deliveries` 행(`channel=webpush`)으로 남긴다.

    ★ 행은 **먼저** 만들고 결과를 채운다(`services._send_one` 과 같은 규약) — 발송기가
      프로세스를 죽여도 「보내려 했다」는 남는다.
    ★ 이 문으로 나간 행은 **훈련 표식**을 단다(`recipient_address` = `drill:webpush:<지문>`).
      `suppress` 가 세지 않으므로 시험 한 통이 다음 진짜 경보를 삼키지 않는다.
    ★ 자격이 없으면 행을 만들지 않고 **던진다**(`WebPushNotConfigured` · 이름 목록) —
      「보내려 했다」가 아니라 「보낼 수 없는 환경」이고, 그것은 발송 이력이 아니라
      설정의 사실이다. App 은 이것을 503 으로 옮긴다.
    ★ 값은 어디에도 남지 않는다 — 행에는 지문, 실패 사유에는 예외 **이름**만.
    """
    parsed = _validated(subscription)
    missing = _missing_env()
    if missing:
        raise WebPushNotConfigured(missing)

    Event = apps.get_model("stream_monitors", "DetectionEvent")
    Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
    event = Event._base_manager.filter(pk=event_id).first()
    if event is None:
        raise EventNotFound(f"event_id={event_id} 가 없다")
    if not scope.is_system:
        assert_scoped(Event, event_id, scope.actor)
    actor = scope.actor

    row = Delivery._base_manager.create(
        event=event,
        recipient_id=getattr(actor, "pk", None),
        recipient_address=f"{DRILL_ADDRESS_PREFIX}{WEBPUSH}:{_fingerprint(parsed['endpoint'])}",
        channel=WEBPUSH,
        occurred_at=event.occurred_at,
        succeeded=False,
        failure_reason=None,
        retry_count=0,
    )
    from kernels.k2_notify.services import _inherit_owner   # 늦은 import — 순환 방지

    _inherit_owner(row, event)

    adapter = channel_registry.get(WEBPUSH)
    try:
        outcome = adapter.send(address=json.dumps(parsed), subject=title, body=body)
    except Exception as exc:      # noqa: BLE001 — 발송 하나가 관제를 세우지 않는다(W0-17)
        outcome = channel_registry.SendOutcome(False, f"어댑터 예외 {type(exc).__name__}"[:240])
    if outcome.ok:
        row.succeeded, row.sent_at, row.failure_reason = True, timezone.now(), None
    else:
        row.succeeded, row.sent_at = False, None
        row.failure_reason = (outcome.reason or "사유 없음")[:250]
    row.save(update_fields=["succeeded", "sent_at", "failure_reason"])
    log.info("[K2][WEBPUSH] drill send delivery=%s ok=%s", row.pk, row.succeeded)
    return DeliveryView(
        delivery_id=row.pk, event_id=row.event_id, recipient_id=row.recipient_id,
        recipient_address=row.recipient_address, channel=row.channel,
        occurred_at=row.occurred_at, sent_at=row.sent_at, succeeded=row.succeeded,
        failure_reason=row.failure_reason, retry_count=row.retry_count)


# ═══════════════════════════════════════════════════════════════════════════
# M4 설정 — 규칙이 고른 수신을 **좁히기만** 한다 (`DsmNotifyPrefs` 머리말)
# ═══════════════════════════════════════════════════════════════════════════
def _prefs_of(user_id: int):
    Prefs = apps.get_model("stream_monitors", "DsmNotifyPrefs")
    return (Prefs._base_manager.filter(user_id=user_id, deleted__isnull=True)
            .order_by("-id").first())


def _in_window(now_t, start, end) -> bool:
    if start <= end:
        return start <= now_t < end
    return now_t >= start or now_t < end      # 자정을 넘는 구간(예 22:00 → 07:00)


def _blocked_reason(user_id: int, channel: str, *, now=None) -> str | None:
    """이 사람의 M4 설정이 **지금 이 채널**을 막는가. 막으면 사유 **이름**, 아니면 `None`.

    설정이 없으면 `None` — 빈 설정은 「규칙 그대로 받는다」다(넓히지도 좁히지도 않는다).
    """
    row = _prefs_of(user_id)
    if row is None:
        return None
    chosen = list(getattr(row, "channels", None) or [])
    if chosen and channel not in chosen:
        return CHANNEL_NOT_CHOSEN_REASON
    start, end = getattr(row, "quiet_start", None), getattr(row, "quiet_end", None)
    if start is not None and end is not None:
        now_t = timezone.localtime(now or timezone.now()).time()
        if _in_window(now_t, start, end):
            return QUIET_HOURS_REASON
    return None
