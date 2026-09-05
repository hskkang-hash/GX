# -*- coding: utf-8 -*-
"""UX-19 — **나가는 웹훅의 문.** 구독 → 발송 → 서명 → 재시도.

★ 이 파일이 SEC-16 의 「부르는 곳」이다 (P-42 · 2026-09-05)
-----------------------------------------------------------
`common/webhook_contract.py` 는 **문보다 먼저** 태어났고, 그 머리에
`intended_caller: UX-19 웹훅 CAP 1.2 · 턴 C` 라고 적혀 있다. 그 줄은 장식이 아니라
기한이었다 — 그 사이 `dormant` 게이트가 규약의 함수 셋(`attempts_from` ·
`giveup_record` · `outbound_headers`)을 **「아무도 안 부른다」**로 잡고 빨간 채였다.
**그 빨강이 옳았다**(D-377: 새로 만드는 것은 켜진 상태로 태어나야 한다).
이 파일이 그 셋을 부르면 빨강이 초록이 된다.

★ **규약을 고쳐서 맞추지 않았다 — 불러서 맞췄다.** 규약이 문에 맞춰 바뀌면
  그것은 규약이 아니라 「지금 보내는 모양」의 기록이 된다(규약 파일 독스트링).
  이 파일은 `webhook_contract` 의 값과 함수를 **읽기만** 한다.

무엇이 어디 있나 — 셋을 다른 파일에 둔다
----------------------------------------
    무엇을 보내나   `common/cap_1_2.py`        표준(OASIS CAP 1.2) 번역
    어떻게 보내나   `common/webhook_contract.py` 서명·재시도 규약 (SEC-16)
    누구에게       `WebhookSubscription` 표      구독 (F-05 등록 위)
    이 파일        그 셋을 잇는다. **그리고 잇기만 한다.**

★ 함정 (세종 §3 함정 ① · P-37) — **새 인증 경로를 만들지 않았다**
------------------------------------------------------------------
    · 구독은 **로그인한 계정**이 등록한다. `scope.require_actor()` 없이 태어나는
      구독 행이 없다 — 무계정 링크(「이 URL 을 아는 사람은 누구나」)가 없다.
    · `INBOUND_KEY_ALLOWED` 를 **한 줄도 넓히지 않았다.** 구독 등록·해지는 쓰기이고,
      `common/inbound_api_key.py` 의 규약 ③이 쓰기에 키를 열어 주는 것을 이미 막는다.
    · 이 파일에도 **라우트가 없다.** 문은 `apps/dsm/api.py` 가 낸다.

★ 서명키 값은 이 저장소에도 이 표에도 없다 (D-204)
--------------------------------------------------
`signing_key_ref` 는 **이름**이고, 값은 `settings.WEBHOOK_SIGNING_KEYS` 가 안다
(그 설정은 환경에서 온다). 이름을 못 풀면 **보내지 않는다** — 서명 없이 내보내는
것은 「우리 이름으로 누구나 낼 수 있는 경보」를 만드는 일이고, 규약의 `verify()` 가
키 없음을 통과가 아니라 거절로 못박은 것과 같은 판단이다.

★ 정직 고지 — **재시도는 이 요청 안에서 돈다** [실측·판정 2026-09-05]
---------------------------------------------------------------------
5회를 다 쓰면 `RetryPolicy().total_wait()` 초(오늘 값 15초)가 지나고, 그동안 발송
라우트가 그만큼 잡힌다. 그것을 감수하는 이유: **상대가 죽었을 때 경보가 조용히
사라지는 것이 더 나쁘다.** 워커로 옮기는 것은 다음 절이고, 그때도 `RetryPolicy`
는 그대로 쓴다 — 정책은 값이지 코드가 아니다.
그 사이의 안전장치는 둘이다: 구독마다 재시도가 아니라 **전체 예산**을 넘기면
남은 구독은 첫 시도만 하고(`DISPATCH_BUDGET_SECONDS`), 개별 호출 타임아웃은
`common/external_http.py` 가 `settings.EXTERNAL_HTTP_TIMEOUT` 로 건다(D-212).
"""
from __future__ import annotations

import ipaddress
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from common import cap_1_2, external_http
from common.tenant_filters import assert_scoped, filter_by_group_field, get_user_group
from common.tenant_scope import TenantScope
from common.webhook_contract import (
    MAX_ATTEMPTS,
    RetryPolicy,
    attempts_from,
    giveup_record,
    outbound_headers,
)

log = logging.getLogger(__name__)

#: 발송 이력의 채널 이름. `DeliveryRecord.Channel.WEBHOOK` 의 값과 **같아야 한다** —
#: 열거값을 여기 다시 적지 않고 모델에서 읽는 것이 옳으나, 이 모듈은 모델을 늦게
#: 찾으므로(계층) 이름 하나를 상수로 두고 시험이 둘이 같은지 잰다.
CHANNEL = "webhook"

#: 등록을 받아 주는 URL 의 스킴. **평문 http 를 기본으로 열지 않는다** —
#: 서명이 본문을 위조에서 지켜도, 평문은 본문을 **읽히는 것**에서 지키지 못한다.
#: 이벤트 본문에는 위치와 시각이 들어 있다.
DEFAULT_ALLOWED_SCHEMES = ("https",)

#: 상한. 한 테넌트가 구독을 무한히 만들면 이벤트 하나가 발송 폭풍이 된다.
MAX_SUBSCRIPTIONS_PER_TENANT = 20

#: 한 이벤트를 내보내는 데 쓸 수 있는 전체 시간(초). 이것을 넘기면 남은 구독은
#: **재시도 없이 한 번만** 시도한다. 넘겼다는 사실은 포기 행의 사유에 남는다.
DISPATCH_BUDGET_SECONDS = 45.0


class WebhookSubscriptionError(ValueError):
    """구독 등록·해지가 거절됐다. 라우트가 4xx 로 옮긴다."""


class UnknownSigningKey(WebhookSubscriptionError):
    """서명키 이름을 못 푼다. **등록 단계에서 막는다** — 등록은 됐는데 보낼 수 없는
    구독을 만들면, 그 구독은 「등록했으니 오겠지」라고 믿는 상대를 만든다."""


@dataclass(frozen=True)
class SubscriptionView:
    """구독 한 줄. **모델이 아니라 값이다** (K2 `Recipient` 와 같은 이유).

    ★ 서명키 **값**을 담는 칸이 없다. 이 값이 라우트 응답이 되므로, 칸이 있으면
      그 값이 화면과 로그로 나간다.
    """

    subscription_id: int
    endpoint_url: str
    signing_key_ref: str
    event_types: tuple[str, ...]
    min_severity: str
    payload_format: str
    is_active: bool
    last_delivered_at: datetime | None


def _model(name: str):
    """모델을 **늦게** 찾는다 — 이 모듈이 특정 앱에 import 로 묶이지 않게 (K5 와 같은 형)."""
    return apps.get_model("stream_monitors", name)


def mine(model, actor):
    """요청자의 테넌트로 좁힌 질의. **`objects` 로 묻지 않는다.**

    ★ [실측 · 저장소가 두 번 밟은 자리] dj-core 의 `CustomManagerGroup` 은
      **스레드에 남아 있는 요청**을 보고 자기 필터를 건다. HTTP 를 때린 시험 뒤에
      같은 스레드에서 `objects` 로 물으면 결과가 조용히 비고, 그러면 「없다」와
      「못 봤다」가 같은 모양이 된다. 그래서 사실은 `_base_manager` 로 묻고
      좁히기는 **우리 문지기**(`filter_by_group_field`)가 한다 —
      K1 이 소유 판정에 `_base_manager` 를 쓰는 것과 같은 이유다.
    """
    return filter_by_group_field(model._base_manager.all(), actor)


# ═══════════════════════════════════════════════════════════════════════════
# 등록 면 — **로그인한 계정만**. 무계정 구독이 없다 (P-37)
# ═══════════════════════════════════════════════════════════════════════════

def _allowed_schemes() -> tuple[str, ...]:
    return tuple(getattr(settings, "WEBHOOK_ALLOWED_SCHEMES", None)
                 or DEFAULT_ALLOWED_SCHEMES)


def validate_endpoint(url: str) -> str:
    """받아 줄 수 있는 수신 URL 인가. **거절 사유를 이름으로 낸다.**

    ★ 왜 안쪽 주소를 막는가 — **우리가 남의 대리인이 된다**
      등록만 하면 우리 서버가 그 주소로 POST 한다. 그 주소가 `127.0.0.1` 이나
      `169.254.169.254` 면, 밖에서 못 닿는 자리를 **우리 서버가 대신 두드리게** 된다.
      본문을 되돌려 주지 않으니 읽히지는 않지만, 두드리는 것 자체가 쓰기다.
      여기서 막는 것이 SEC-08 이 찾는 종류의 구멍을 미리 닫는 자리다.

    ⚠ 이 검사는 **이름을 본다.** 등록 뒤에 그 이름이 안쪽 주소로 다시 풀리는
      경우(DNS rebinding)까지는 막지 못한다 — 못 막는 것을 못 막는다고 적는다(D-301).
    """
    raw = (url or "").strip()
    if not raw:
        raise WebhookSubscriptionError("수신 URL 이 비었습니다.")
    parsed = urlparse(raw)
    schemes = _allowed_schemes()
    if parsed.scheme not in schemes:
        raise WebhookSubscriptionError(
            "수신 URL 의 방식이 %s 가 아닙니다(받은 것: %s). 평문으로 보내면 서명이 "
            "위조는 막아도 **내용을 읽히는 것**은 막지 못합니다."
            % (" / ".join(schemes), parsed.scheme or "없음"))
    host = (parsed.hostname or "").strip()
    if not host:
        raise WebhookSubscriptionError("수신 URL 에 호스트가 없습니다.")
    if host.lower() in ("localhost", "localhost.localdomain"):
        raise WebhookSubscriptionError(
            "우리 서버 자신을 가리키는 주소는 등록할 수 없습니다.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (address.is_private or address.is_loopback
                                or address.is_link_local or address.is_reserved
                                or address.is_multicast):
        raise WebhookSubscriptionError(
            "내부망·루프백 주소는 등록할 수 없습니다. 등록만으로 우리 서버가 그 주소를 "
            "대신 두드리게 됩니다.")
    return raw


def signing_secret(signing_key_ref: str) -> str:
    """이름 → 값. **값은 설정(환경)에만 있다** (D-204).

    못 풀면 빈 문자열이다. 부르는 쪽이 그것을 통과로 읽지 않게, 이 모듈의 두 자리가
    빈 문자열을 각각 **등록 거절**과 **발송 거절**로 옮긴다.
    """
    table = getattr(settings, "WEBHOOK_SIGNING_KEYS", None) or {}
    try:
        return str(table.get(signing_key_ref) or "")
    except AttributeError:
        return ""


def register(*, scope: TenantScope, endpoint_url: str, signing_key_ref: str,
             event_types: Iterable[str] | None = None, min_severity: str = "",
             payload_format: str = cap_1_2.FORMAT_JSON) -> SubscriptionView:
    """구독을 등록한다 (F-05). **계정이 등록한다** — 무계정 링크가 아니다.

    `scope.require_actor()` 를 먼저 부르는 이유: 시스템 스코프(사람 없는 호출)로는
    구독을 만들 수 없어야 한다. 만들 수 있으면 「누가 등록했는지 모르는 구독」이
    생기고, 그것은 우리가 관리하지 않는 계정과 같다.
    """
    actor = scope.require_actor()
    url = validate_endpoint(endpoint_url)
    ref = (signing_key_ref or "").strip()
    if not ref:
        raise WebhookSubscriptionError(
            "서명키 이름이 비었습니다. 서명 없는 웹훅은 **누구나 보낼 수 있는 경보**입니다.")
    if not signing_secret(ref):
        raise UnknownSigningKey(
            "서명키 %r 의 값을 이 환경에서 찾을 수 없습니다. 값은 저장소가 아니라 "
            "환경에 둡니다 — 값을 넣은 뒤 다시 등록해 주세요." % ref)
    if payload_format not in cap_1_2.SUPPORTED_FORMATS:
        raise WebhookSubscriptionError(
            "형식은 %s 중 하나입니다." % ", ".join(sorted(cap_1_2.SUPPORTED_FORMATS)))

    Subscription = _model("WebhookSubscription")
    if mine(Subscription, actor).filter(is_active=True).count() >= MAX_SUBSCRIPTIONS_PER_TENANT:
        raise WebhookSubscriptionError(
            "활성 구독이 상한(%d)에 닿았습니다. 쓰지 않는 구독을 먼저 해지해 주세요 — "
            "구독 하나가 늘 때마다 이벤트 하나가 나가는 횟수가 늡니다."
            % MAX_SUBSCRIPTIONS_PER_TENANT)

    row = Subscription.objects.create(
        endpoint_url=url,
        signing_key_ref=ref,
        event_types=sorted({str(t).strip() for t in (event_types or ()) if str(t).strip()}),
        min_severity=(min_severity or "").strip(),
        payload_format=payload_format,
        is_active=True,
        created_by=actor,
        #: **소유를 박는다.** 주인 없는 행은 §0.4 의 `created_by__isnull=True` OR 절을
        #: 타고 **모든 테넌트에게 보인다** — 남의 구독 URL 이 보이는 상태가 된다.
        group=get_user_group(actor),
    )
    return _view(row)


def list_subscriptions(*, scope: TenantScope) -> tuple[SubscriptionView, ...]:
    """내 테넌트의 구독 전부. **남의 것은 보이지 않는다.**"""
    actor = scope.require_actor()
    Subscription = _model("WebhookSubscription")
    return tuple(_view(row) for row in mine(Subscription, actor))


def revoke(*, scope: TenantScope, subscription_id: int) -> SubscriptionView:
    """구독을 끈다. **행을 지우지 않는다** — 지우면 그 구독이 무엇을 받았는지가
    함께 사라진다(SEC-05 폐기 규약과 같은 판단). 발송 이력은 이 행을 가리킨다."""
    actor = scope.require_actor()
    Subscription = _model("WebhookSubscription")
    assert_scoped(Subscription, subscription_id, actor)
    row = Subscription._base_manager.filter(pk=subscription_id).first()
    if row is None:  # pragma: no cover - assert_scoped 가 먼저 404 를 낸다
        raise WebhookSubscriptionError("그런 구독이 없습니다.")
    if row.is_active:
        row.is_active = False
        row.save(update_fields=["is_active"])
    return _view(row)


def _view(row) -> SubscriptionView:
    return SubscriptionView(
        subscription_id=row.pk,
        endpoint_url=row.endpoint_url,
        signing_key_ref=row.signing_key_ref,
        event_types=tuple(row.event_types or ()),
        min_severity=row.min_severity or "",
        payload_format=row.payload_format,
        is_active=row.is_active,
        last_delivered_at=row.last_delivered_at,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 발송 면 — CAP 1.2 로 만들고 · SEC-16 으로 서명하고 · SEC-16 으로 재시도한다
# ═══════════════════════════════════════════════════════════════════════════

#: 등급의 **순서**. 「이 등급 이상」을 판정하려면 순서가 필요하고, 그 순서는
#: `DetectionEvent.Severity` 의 선언 순서다. 여기 없는 값은 거르지 않는다 —
#: 모르는 등급을 조용히 버리면 새 등급이 생긴 날 경보가 사라진다.
_SEVERITY_ORDER = ("info", "warning", "critical")


def _passes_filter(row, event) -> bool:
    """이 구독이 이 이벤트를 받는가. **빈 목록은 「전부」다.**"""
    types = tuple(row.event_types or ())
    if types and event.event_type not in types:
        return False
    floor = (row.min_severity or "").strip()
    if floor and floor in _SEVERITY_ORDER and event.severity in _SEVERITY_ORDER:
        if _SEVERITY_ORDER.index(event.severity) < _SEVERITY_ORDER.index(floor):
            return False
    return True


def _event_payload(event) -> dict[str, Any]:
    """모델 → CAP 번역기가 받는 dict. **번역기가 모델을 모르게 한다.**"""
    monitor = getattr(event, "stream_monitor", None)
    return {
        "event_id": event.pk,
        "event_type": event.event_type,
        "severity": event.severity,
        "verdict": getattr(event, "verdict", None),
        "occurred_at": event.occurred_at,
        "lat": getattr(event, "lat", None),
        "lng": getattr(event, "lng", None),
        "address": getattr(event, "address", None),
        "confidence": getattr(event, "confidence", None),
        "response_state": getattr(event, "response_state", ""),
        "stream_monitor_name": getattr(monitor, "name", "") if monitor else "",
    }


def _sender() -> str:
    """CAP `sender`. 공백·쉼표가 없어야 한다 — 번역기가 그것을 거절한다."""
    return str(getattr(settings, "CAP_SENDER", "") or "guardianx.local")


def _post(url: str, body: bytes, headers: dict[str, str]) -> tuple[int | None, str]:
    """한 번 보낸다. **응답을 값으로 돌려준다** — `(상태코드, 오류문)`.

    상태코드 `None` 은 **응답을 못 받았다**(연결 실패·타임아웃)는 뜻이고, 규약의
    `should_retry` 가 그것을 「답을 거절한 것」과 다르게 다룬다.

    타임아웃 숫자를 여기 적지 않는다 — `external_http` 가 설정에서 읽는다(D-212).
    """
    try:
        response = external_http.request("POST", url, data=body, headers=headers)
    except Exception as exc:  # 저하 운전 — 관제를 멈추지 않는다 (W0-17)
        return None, ("%s: %s" % (type(exc).__name__, exc))[:200]
    return response.status_code, ""


def deliver_one(*, subscription, event, now: datetime | None = None,
                sender: Callable[[str, bytes, dict[str, str]], tuple[int | None, str]] | None = None,
                sleeper: Callable[[float], None] | None = None,
                allow_retry: bool = True) -> dict[str, Any]:
    """구독 하나에게 이벤트 하나를 보낸다. **결과를 값으로 돌려준다.**

    ★ 여기가 규약을 부르는 자리다:
        `outbound_headers()`  — 보낼 때 붙는 헤더 전부 (서명 포함)
        `RetryPolicy`         — 5회 지수 백오프
        `attempts_from()`     — **몇 번 보냈는가**를 세는 자리
        `giveup_record()`     — 5회 뒤 포기를 행으로

    ★ 시도 횟수를 **여기서 따로 세지 않는다**(D-212). 반복문이 자기 계수기를 들면
      규약이 세는 수와 행에 남는 수가 갈릴 수 있고, 갈려도 아무도 못 본다.
      관측한 상태 목록을 `attempts_from()` 에 넘겨 **규약이 세게** 한다 —
      시험이 「5회에서 멈춘다」를 재는 데 쓰는 바로 그 함수다.
    """
    post = sender if sender is not None else _post
    wait = sleeper if sleeper is not None else time.sleep
    policy = RetryPolicy()
    moment = now or timezone.now()

    secret = signing_secret(subscription.signing_key_ref)
    if not secret:
        # **키가 없으면 보내지 않는다.** 규약의 `verify()` 가 키 없음을 통과가 아니라
        # 거절로 못박은 것과 같은 판단이다 — 서명 없이 나간 경보는 회수할 수 없다.
        return {
            "succeeded": False, "attempts": 0, "last_status": None,
            "failure_reason": "서명키 %r 의 값이 이 환경에 없습니다 — 서명 없이 "
                              "내보내지 않습니다" % subscription.signing_key_ref,
            "giveup": None, "sent_at": None,
        }

    alert = cap_1_2.to_cap_alert(
        _event_payload(event),
        sender=_sender(),
        identifier="GX-EVT-%s" % event.pk,
        sent=moment if moment.tzinfo else timezone.make_aware(moment),
        sender_name=str(getattr(settings, "CAP_SENDER_NAME", "") or _sender()),
    )
    body, content_type = cap_1_2.render(alert, subscription.payload_format)

    statuses: list[int | None] = []
    last_error = ""
    schedule = policy.schedule() if allow_retry else policy.schedule()[:1]
    for attempt, delay in schedule:
        headers = dict(outbound_headers(secret, body, event_id=str(event.pk)))
        headers["Content-Type"] = content_type
        status, error = post(subscription.endpoint_url, body, headers)
        statuses.append(status)
        last_error = error
        if status is not None and 200 <= status < 300:
            return {
                "succeeded": True,
                "attempts": attempts_from(policy, statuses),
                "last_status": status, "failure_reason": "",
                "giveup": None, "sent_at": timezone.now(),
            }
        if not policy.should_retry(attempt, status):
            break
        if delay:
            wait(delay)

    attempts = attempts_from(policy, statuses)
    last_status = statuses[-1] if statuses else None
    reason = ("rejected_by_receiver"
              if (last_status is not None and 400 <= last_status < 500)
              else "attempts_exhausted")
    record = giveup_record(
        subscription_id=subscription.pk, event_id=str(event.pk), attempts=attempts,
        last_status=last_status, last_error=last_error, reason=reason)
    return {
        "succeeded": False, "attempts": attempts, "last_status": last_status,
        "failure_reason": _giveup_sentence(record), "giveup": record, "sent_at": None,
    }


def _giveup_sentence(record: dict) -> str:
    """포기 행 → 이력 칸 한 줄. **「실패」 한 낱말로 뭉치지 않는다** — 고치는 사람이 다르다.

    `attempts_exhausted` 는 상대가 죽어 있다(상대 담당자의 일)이고
    `rejected_by_receiver` 는 규약이 안 맞는다(우리와 상대가 함께 볼 일)다.
    """
    return ("%s · %d/%d회 · 마지막 응답 %s%s" % (
        record["reason"], record["attempts"], record["max_attempts"],
        record["last_status"] if record["last_status"] is not None else "없음",
        (" · %s" % record["last_error"]) if record["last_error"] else ""))[:255]


def dispatch_event(*, scope: TenantScope, event_id: int,
                   channels: Iterable[str] | None = None,
                   sender: Callable[..., tuple[int | None, str]] | None = None,
                   sleeper: Callable[[float], None] | None = None) -> tuple:
    """이벤트 하나를 **구독 전부**에게 CAP 1.2 로 내보낸다.

    `DeliveryView` 를 돌려준다 — 사람에게 간 발송과 **같은 모양**이다. 두 모양으로
    내면 화면과 보고서가 웹훅 발송을 따로 세게 되고, 따로 세는 순간 한쪽이 뒤처진다.

    ★ 구독이 0개면 **빈 값이다.** 그것이 이 기능을 켜기 전과 후를 같게 만든다 —
      아무도 구독하지 않은 테넌트에서는 이 코드가 지나가도 아무 일이 없다.
    """
    if channels is not None and CHANNEL not in set(channels):
        return ()

    Event = _model("DetectionEvent")
    Subscription = _model("WebhookSubscription")
    Delivery = _model("DeliveryRecord")

    event = Event._base_manager.select_related("stream_monitor").filter(
        pk=event_id).first()
    if event is None:
        return ()
    # ★ **구독은 이벤트의 테넌트에 속한다** — 요청자가 아니라.
    #   요청자로 좁히면 파이프라인(시스템 스코프) 발송에서 구독이 0건이 되고,
    #   요청자를 무시하면 남의 테넌트 구독에 우리 이벤트가 나간다. 이벤트의 주인이
    #   두 경우 모두에서 옳은 답이다. 요청자가 그 이벤트에 닿을 자격이 있는지는
    #   이 함수를 부르기 전에 이미 판정됐다(K2 `send` 의 `assert_scoped`).
    rows = Subscription._base_manager.filter(
        is_active=True, group_id=getattr(event, "group_id", None))
    targets = [row for row in rows if _passes_filter(row, event)]
    if not targets:
        return ()

    started = time.monotonic()
    views = []
    for row in targets:
        # 예산을 넘겼으면 남은 구독은 **한 번만** 시도한다. 그 사실은 포기 행에
        # `attempts=1` 로 남는다 — 「5회 다 썼다」와 구별된다(D-290).
        within_budget = (time.monotonic() - started) < DISPATCH_BUDGET_SECONDS
        result = deliver_one(subscription=row, event=event, sender=sender,
                             sleeper=sleeper, allow_retry=within_budget)
        record = Delivery.objects.create(
            event=event, recipient=None, recipient_address=row.endpoint_url,
            channel=CHANNEL, occurred_at=event.occurred_at,
            sent_at=result["sent_at"], succeeded=result["succeeded"],
            failure_reason=result["failure_reason"] or None,
            retry_count=max(result["attempts"] - 1, 0),
        )
        if result["succeeded"]:
            row.last_delivered_at = record.sent_at
            row.save(update_fields=["last_delivered_at"])
        else:
            log.warning("[UX-19][WEBHOOK] 발송 실패 sub=%s event=%s %s",
                        row.pk, event.pk, result["failure_reason"])
        views.append(_delivery_view(record))
    return tuple(views)


def _delivery_view(record):
    """K2 가 쓰는 값 모양 그대로. **두 벌로 만들지 않는다** (D-212)."""
    from kernels.k2_notify.schemas import DeliveryView

    return DeliveryView(
        delivery_id=record.pk, event_id=record.event_id,
        recipient_id=None, recipient_address=record.recipient_address,
        channel=record.channel, occurred_at=record.occurred_at,
        sent_at=record.sent_at, succeeded=record.succeeded,
        failure_reason=record.failure_reason, retry_count=record.retry_count,
    )


#: 규약이 정한 수를 이 모듈이 **다시 적지 않는다.** 보고서·화면이 「몇 번까지
#: 보내나」를 물으면 이 이름을 읽는다 (D-212).
ATTEMPT_CEILING = MAX_ATTEMPTS
