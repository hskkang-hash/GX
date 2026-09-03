# -*- coding: utf-8 -*-
"""K2 알림 커널 — 공개 면 (DA-04 §2 K2).

등급별 수신자에게 보내고, **보낸 사실을 남기는** 한 벌.

이중 AC (DA-04 §1-2) — 충돌 시 **계약 AC 우선**
------------------------------------------------
    [F-10 계약] 심각 등급 발생 후 **30초 내 발송 기록**
    [U2 상품]  보고 자동화의 입력 · [U1] 오탐 흐름의 시작점

★ DA-04 가 해법을 이미 적었다:

    발송 기록이 곧 보고서의 "조치 이력" 행이다 — K4 가 이 레코드를 그대로 읽는다.
    **알림용·보고서용 두 벌로 적재하지 않는다.**

그래서 `DeliveryRecord` 하나가 알림 이력이자 조치 이력이다. 두 벌이면 알림과 보고서가
다른 말을 하고, 그 둘이 같은 회의에 올라가면 아무도 어느 쪽을 믿을지 모른다.

두 창은 여전히 다르다 — 그리고 **K2 는 K1 과 다른 것을 본다**
-------------------------------------------------------------
K1 의 `should_notify` 는 *이벤트 행*을 보고 "알릴 만한가"를 판정한다.
K2 의 `suppress` 는 *발송 이력*을 보고 "실제로 이미 보냈는가"를 판정한다.

  같은 5분이지만 답이 다를 수 있다. 메일 서버가 죽어 **보내지 못한 알림**은
  K1 기준으로는 "이미 알렸다"이고, K2 기준으로는 **아직 안 갔다**이다.
  후자가 사실이다. 억제는 사실 위에서 해야 한다 — 그러지 않으면 장애 5분 동안의
  재난 알림이 통째로 사라진다.

테넌트 스코프 — D-281
---------------------
공개 함수는 전부 `*, scope: TenantScope` 를 **키워드 전용 필수 인자**로 받는다.
발송은 파이프라인이 부를 수 있으므로 `TenantScope.system(reason=...)` 도 받되,
**조회는 요청자를 요구한다**(`require_actor`) — 시스템 스코프 조회는 전역 조회이고,
전역 조회는 격리가 아니라 격리의 부재다.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common.tenant_filters import assert_scoped, filter_by_group_field, get_user_group
from common.tenant_scope import TenantScope
from kernels.k2_notify import channels as channel_registry
from kernels.k2_notify.exceptions import (
    EventNotFound,
    InvalidNotifyInput,
    NoRecipients,
    NotImplementedYet,
)
from kernels.k2_notify.schemas import (
    F10_MAX_LATENCY,
    SUPPRESS_WINDOW,
    DeliveryView,
    Recipient,
)


def _model(name: str):
    return apps.get_model("stream_monitors", name)


def _owner_field(model) -> str:
    """K1 과 **같은 판단**을 쓴다 — 판단은 한 곳에서만 한다 (D-212)."""
    from kernels.k1_event.services import _owner_field as k1_owner_field

    return k1_owner_field(model)


def _inherit_owner(row, source) -> None:
    """이력의 소유를 **이벤트에서 물려받는다.**

    발송 이력이 주인 없는 행이 되면 §0.4 의 `created_by__isnull` OR 절을 타고
    모든 테넌트에게 보인다 — **남의 재난 알림 이력을 읽는 것**이 되고,
    그 이력에는 수신자 주소가 들어 있다. K1 `_inherit_owner` 와 같은 이유·같은 처리다.
    """
    field = _owner_field(type(row))
    if field == "groups":
        row.groups.set(source.groups.all())
    else:
        setattr(row, "group", getattr(source, "group", None))
        row.save(update_fields=["group"])


def _location_line(event) -> str:
    """FX-5 — 위치 한 줄. **상태에 따라 다른 문장이 나간다** (D-290 · D-298).

    ★ 이 함수는 이 파일의 원래 방침을 **한 겹 완화한다.** 아래 `_subject_and_body` 는
      "본문에 좌표 원문을 넣지 않는다" 였다 — 메일은 저장소 밖으로 나가는 유일한 경로이고
      본문에 실리는 것이 곧 유출 표면이기 때문이다. D-298 의 FX-5 지시가 그 방침을
      **명시적으로** 바꿨다: *"'failed' 면 알림에 '주소 확인 불가(좌표: …)'로 나가고"*.

      완화의 범위를 여기 한 줄로 좁혀 둔다: 조회에 **실패했을 때만** 좌표가 실린다.
      성공하면 도로명 주소만 나가고 좌표는 나가지 않는다 — 사람이 지도를 여는 데
      좌표가 필요한 경우는 주소를 못 얻은 경우뿐이기 때문이다.

    상태 넷이 각각 다른 문장을 낸다. 같은 문장으로 뭉치면 받는 사람은 "주소가 없는 사건"과
    "주소를 못 얻은 사건"을 구별할 수 없고, 새벽 당직자에게 그 차이가 곧 대응 속도다.

    ★ 2026-09-06 — **카메라 설치 주소가 먼저다** (D-330)
    ---------------------------------------------------
    좌표를 주소로 바꾸려고 외부 자원을 찾고 키를 신청하고 잠금을 세웠는데,
    답은 **카메라가 고정 설치물이라는 사실** 하나였다. 설치할 때 주소를 안다.

    그리고 결과가 더 좋다. 역지오코딩은 「서울시 …로 12」만 주지만
    우리는 **「정문 (서울시 …로 12)」**를 준다 — 새벽 당직자에게 이 차이가 결정적이다.

    ⚠ **발송을 지연시키지 않는다.** 주소는 보조 정보이지 발송 조건이 아니다.
      카메라 주소가 없으면(`address_source='unset'`) 아래 종전 갈래로 그대로 내려간다 —
      D-308 이 그은 경계를 넓히지 않는다.
    """
    camera = getattr(event, "stream_monitor", None)
    if camera is not None:
        installed = (getattr(camera, "install_address", "") or "").strip()
        source = getattr(camera, "address_source", "unset") or "unset"
        if installed and source != "unset":
            detail = (getattr(camera, "install_address_detail", "") or "").strip()
            return f"위치 {detail} ({installed})" if detail else f"위치 {installed}"

    status = getattr(event, "address_status", "") or ""
    if status == "resolved" and event.address:
        return f"위치 {event.address}"
    if status == "failed":
        # 좌표가 없는데 failed 인 상태는 만들어지지 않는다(k1_event._address_status 참조).
        # 그래도 방어적으로 적는다 — 없는 값을 'None' 이라고 인쇄하지 않기 위해서다.
        where = (f"좌표: {event.lat}, {event.lng}"
                 if event.lat is not None and event.lng is not None else "좌표 없음")
        return f"위치 주소 확인 불가({where})"
    if status == "pending":
        return "위치 주소 조회 중"
    return "위치 미상 — 좌표가 기록되지 않았습니다"


def _subject_and_body(event) -> tuple[str, str]:
    """알림 본문. **개인정보를 넣지 않는다.**

    메일은 저장소 밖으로 나가는 유일한 경로다. 여기서 무엇을 싣는가가 곧
    유출 표면이므로, 사람이 **화면으로 들어와 확인하게** 하는 최소 정보만 담는다.

    ⚠ 좌표는 예외 하나로 실린다 — FX-5 의 조회 실패 시뿐이다. `_location_line` 참조.
    """
    subject = f"[GuardianX] {event.get_severity_display()} — {event.get_event_type_display()}"
    body = (
        f"이벤트 #{event.pk}\n"
        f"발생 {timezone.localtime(event.occurred_at):%Y-%m-%d %H:%M:%S}\n"
        f"등급 {event.severity} · 종류 {event.event_type}\n"
        f"{_location_line(event)}\n"
        f"관제 화면에서 확인하십시오."
    )
    return subject, body


def _to_view(row) -> DeliveryView:
    return DeliveryView(
        delivery_id=row.pk,
        event_id=row.event_id,
        recipient_id=row.recipient_id,
        recipient_address=row.recipient_address,
        channel=row.channel,
        occurred_at=row.occurred_at,
        sent_at=row.sent_at,
        succeeded=row.succeeded,
        failure_reason=row.failure_reason,
        retry_count=row.retry_count,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. resolve_recipients — 누가 받는가
# ═══════════════════════════════════════════════════════════════════════════
def resolve_recipients(
    *,
    scope: TenantScope,
    severity: str,
    group=None,
    zone: str | None = None,
) -> tuple[Recipient, ...]:
    """등급 × 역할 × 구역 → 수신자 목록 (DA-04 §2 K2).

    ★ 규칙은 **역할**을 가리키고 사람을 가리키지 않는다. 사람을 직접 넣으면
      인사이동마다 규칙을 고쳐야 하고, 안 고친 규칙은 퇴사자에게 재난 알림을 보낸다.

    ★ 빈 목록을 **그냥 돌려준다** — 여기서는 그것이 정상 부재일 수 있다(그 등급에
      규칙이 없다). 실패로 바꾸는 자리는 `send` 다: 보낼 곳 없이 "보냈다"고 하는 것이
      조용한 무력화이기 때문이다 (D-290 — 부재와 실패를 가르되, 가르는 자리를 고른다).
    """
    Rule = _model("NotificationRule")
    Event = _model("DetectionEvent")
    if severity not in Event.Severity.values:
        raise InvalidNotifyInput(
            f"severity={severity!r} 은 계약에 없다. 허용: {', '.join(Event.Severity.values)}")

    actor = scope.actor
    group = group or (get_user_group(actor) if actor is not None else None)
    if group is None:
        raise InvalidNotifyInput(
            "수신자를 정할 테넌트가 없다. 파이프라인 호출이면 `group=` 을 넘겨라 — "
            "그것 없이 규칙을 고르면 **전 테넌트의 규칙**을 고르게 된다 (D-281)")

    qs = Rule._base_manager.filter(severity=severity, is_active=True)
    qs = _filter_rules_by_group(qs, group, actor=actor)
    # 구역 규칙이 있으면 그것을, 없으면 전역 규칙(zone 비어 있음)을 쓴다.
    # 둘 다 적용하면 같은 사람에게 두 번 간다.
    if zone:
        scoped = list(qs.filter(zone=zone))
        rules = scoped or list(qs.filter(zone__isnull=True))
    else:
        rules = list(qs.filter(zone__isnull=True))

    CoreUser = apps.get_model("user", "CoreUser")
    seen: set[tuple[int, str]] = set()
    out: list[Recipient] = []
    for rule in rules:
        members = CoreUser.objects.filter(
            roles=rule.role_id, userprofilelink__group=group, is_active=True
        ).distinct()
        for user in members:
            for channel in (rule.channels or []):
                key = (user.pk, channel)
                if key in seen:
                    continue  # 규칙 둘이 같은 역할을 가리켜도 두 번 보내지 않는다
                seen.add(key)
                out.append(Recipient(
                    user_id=user.pk,
                    display_name=getattr(user, "username", "") or str(user.pk),
                    address=getattr(user, "email", "") or "",
                    channel=str(channel),
                    rule_id=rule.pk,
                    role_code=getattr(rule.role, "code", "") or "",
                ))
    return tuple(out)


def _filter_rules_by_group(qs, group, actor=None):
    """규칙을 그 테넌트 것으로 좁힌다.

    ★ 요청자가 있으면 **문지기를 탄다** (`common.tenant_filters.filter_by_group_field`).
      직접 `filter(group=…)` 을 적으면 전역 관리자 판정·소유 필드 판정이 여기서 한 번 더
      복제되고, 복제된 판정은 곧 갈린다 (D-212 — 판단은 한 곳에서만).
    ★ 요청자가 없는 호출(발송 파이프라인)에서는 **이벤트가 정한 group** 으로 좁힌다.
      그 group 은 이미 이벤트의 소유이므로 추측이 아니다.
    """
    Rule = _model("NotificationRule")
    field = _owner_field(Rule)
    if actor is not None:
        return filter_by_group_field(qs, actor, field=field).distinct()
    if field == "groups":
        return qs.filter(groups=group).distinct()
    return qs.filter(group=group)


# ═══════════════════════════════════════════════════════════════════════════
# 2. suppress — **5분 중복 억제 판정은 여기다** (K1 이 아니다)
# ═══════════════════════════════════════════════════════════════════════════
def suppress(*, scope: TenantScope, event_id: int) -> bool:
    """이 이벤트에 대한 알림을 접어야 하는가 (F-04).

    ★ 보는 것은 **발송 이력**이다. 이벤트 행이 아니다.
      메일 서버가 죽어 못 보낸 알림은 "이미 알렸다"가 아니다 — 그것을 억제로 세면
      장애 5분 동안의 재난 알림이 통째로 사라진다. 억제는 **성공한 발송** 위에서만 한다.

    같은 스트림 · 같은 종류의 이벤트에 대해 `SUPPRESS_WINDOW` 안에 **성공한 발송**이
    있으면 참이다.
    """
    Event = _model("DetectionEvent")
    Delivery = _model("DeliveryRecord")

    event = Event._base_manager.select_related("stream_monitor").filter(pk=event_id).first()
    if event is None:
        raise EventNotFound(f"event_id={event_id} 가 없다")
    if not scope.is_system:
        assert_scoped(Event, event_id, scope.actor)

    return Delivery._base_manager.filter(
        succeeded=True,
        event__stream_monitor_id=event.stream_monitor_id,
        event__event_type=event.event_type,
        occurred_at__lt=event.occurred_at,
        occurred_at__gte=event.occurred_at - SUPPRESS_WINDOW,
    ).exists()


# ═══════════════════════════════════════════════════════════════════════════
# 3. send — 보내고, **보낸 사실을 남긴다**
# ═══════════════════════════════════════════════════════════════════════════
def send(
    *,
    scope: TenantScope,
    event_id: int,
    recipients: Iterable[Recipient] | None = None,
    channels: Iterable[str] | None = None,
    respect_suppression: bool = True,
) -> tuple[DeliveryView, ...]:
    """이벤트 하나를 수신자들에게 보낸다. **결과는 전부 행으로 남는다.**

    ★ 실패해도 예외를 올리지 않는다 — 저하 운전(DA2-21 (4)): *"발송 업체가 죽어도
      이벤트 처리·대시보드는 200 을 유지한다."* 대신 실패는 **행으로 보인다**:
      `succeeded=False` + `failure_reason`. "보낸 적 없음"(행 없음)과 구별된다 (D-290).

    ★ 수신자가 0명이면 `NoRecipients` 를 **던진다.** 여기서는 빈 목록이 정상 부재가
      아니라 **알림 체계가 꺼져 있는 상태**이기 때문이다 (DA-03 §3-2 조용한 무력화 금지).

    ★ `sent_at` 은 **성공했을 때만** 찍는다. 실패에 시각을 넣으면 F-10 의 30초가
      실패한 발송으로도 달성된다.
    """
    Event = _model("DetectionEvent")
    Delivery = _model("DeliveryRecord")

    event = Event._base_manager.select_related("stream_monitor").filter(pk=event_id).first()
    if event is None:
        raise EventNotFound(f"event_id={event_id} 가 없다")
    # 사람이 부른 발송은 **자기 테넌트 이벤트**에만 보낸다 — 쓰기 쪽 IDOR (D-290).
    # 파이프라인 스코프에는 이 문턱이 없고, 그래서 시스템 스코프는 사유를 요구한다.
    if not scope.is_system:
        assert_scoped(Event, event_id, scope.actor)

    if respect_suppression and suppress(scope=scope, event_id=event_id):
        # 접는 것도 사실이다. 다만 **행을 만들지 않는다** — 발송 이력은 발송의 이력이지
        # 판정의 이력이 아니다. 판정 이력이 필요하면 K6 이 이벤트에서 센다.
        return ()

    if recipients is None:
        group = _group_of(event)
        recipients = resolve_recipients(
            scope=scope, severity=event.severity, group=group)
    recipients = tuple(recipients)
    if channels is not None:
        allowed = set(channels)
        recipients = tuple(r for r in recipients if r.channel in allowed)

    if not recipients:
        raise NoRecipients(
            f"event_id={event_id}(severity={event.severity})에 대한 수신자가 0명이다. "
            "규칙이 없거나 그 역할에 사람이 없다 — **알림 체계가 꺼져 있는 상태**다. "
            "빈 성공으로 넘기지 않는다 (DA-03 §3-2 · D-290)")

    views: list[DeliveryView] = []
    for recipient in recipients:
        views.append(_send_one(event, recipient))
    return tuple(views)


def _group_of(event):
    field = _owner_field(type(event))
    if field == "groups":
        return event.groups.first()
    return getattr(event, "group", None)


@transaction.atomic
def _send_one(event, recipient: Recipient) -> DeliveryView:
    """한 사람·한 채널. **행을 먼저 만들고 결과를 채운다.**

    왜 먼저 만드나 — 어댑터가 프로세스를 죽여도(OOM·강제종료) "보내려 했다"는 사실은
    남아야 한다. 나중에 만들면 그 창에서 죽은 발송이 **없었던 일**이 된다.
    """
    Delivery = _model("DeliveryRecord")

    row = Delivery._base_manager.create(
        event=event,
        recipient_id=recipient.user_id,
        recipient_address=recipient.address,
        channel=recipient.channel,
        occurred_at=event.occurred_at,
        succeeded=False,
        failure_reason=None,
        retry_count=0,
    )
    _inherit_owner(row, event)

    adapter = channel_registry.get(recipient.channel)
    if adapter is None:
        row.failure_reason = channel_registry.why_unavailable(recipient.channel)[:250]
        row.save(update_fields=["failure_reason"])
        return _to_view(row)

    subject, body = _subject_and_body(event)
    # ★ 어댑터가 **예외로 죽는 경로**를 여기서 막는다 (저하 운전 · W0-17).
    #   `EmailChannel` 은 스스로 값으로 바꾸지만, 나중에 끼울 업체 SDK 는 그러지 않는다 —
    #   그리고 그것을 여기서 안 막으면 발송 하나가 **관제 전체를 세운다.**
    #   실측: `_ExplodingChannel` 시험이 이 줄이 없을 때 파이프라인을 세웠다.
    try:
        outcome = adapter.send(address=recipient.address, subject=subject, body=body)
    except Exception as exc:
        outcome = channel_registry.SendOutcome(
            False, f"어댑터 예외 {type(exc).__name__}: {exc}"[:240])
    if outcome.ok:
        row.succeeded = True
        row.sent_at = timezone.now()
        row.failure_reason = None
    else:
        row.succeeded = False
        row.sent_at = None          # 실패에 시각을 넣지 않는다 (F-10 이 거짓으로 달성된다)
        row.failure_reason = (outcome.reason or "사유 없음")[:250]
    row.save(update_fields=["succeeded", "sent_at", "failure_reason"])
    return _to_view(row)


# ═══════════════════════════════════════════════════════════════════════════
# 4. list_deliveries — K4 가 "조치 이력"으로 읽는 바로 그 목록
# ═══════════════════════════════════════════════════════════════════════════
def list_deliveries(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
    event_id: int | None = None,
    recipient_id: int | None = None,
    succeeded: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[DeliveryView, ...]:
    """발송 이력 조회. **테넌트 스코프 강제** · 필터는 전부 서버에서.

    K4 보고서의 "조치 이력" 행이 이 함수의 결과다 — 보고서용 목록을 따로 만들지 않는다
    (DA-04 K2 이중 AC: 두 벌로 적재하지 않는다).
    """
    Delivery = _model("DeliveryRecord")
    actor = scope.require_actor()

    qs = Delivery._base_manager.select_related("event")
    qs = filter_by_group_field(qs, actor, field=_owner_field(Delivery))
    if since is not None:
        qs = qs.filter(occurred_at__gte=since)
    if until is not None:
        qs = qs.filter(occurred_at__lte=until)
    if event_id is not None:
        qs = qs.filter(event_id=event_id)
    if recipient_id is not None:
        qs = qs.filter(recipient_id=recipient_id)
    if succeeded is not None:
        qs = qs.filter(succeeded=succeeded)
    qs = qs.distinct().order_by("-occurred_at", "-id")
    return tuple(_to_view(row) for row in qs[offset:offset + limit])
