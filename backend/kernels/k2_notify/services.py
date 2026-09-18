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

import logging
from datetime import datetime
from typing import Iterable

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common import audit_writer
from common.tenant_filters import assert_scoped, filter_by_group_field, get_user_group
from common.ai_act_notice import notice_line
from common.tenant_scope import TenantScope
from kernels.k2_notify import channels as channel_registry
from kernels.k2_notify import webpush as webpush_gate
from kernels.k2_notify.exceptions import (
    EventNotFound,
    InvalidNotifyInput,
    NoRecipients,
    NotifyPermissionDenied,
    NotImplementedYet,
)
from kernels.k2_notify.schemas import (
    F10_MAX_LATENCY,
    SUPPRESS_WINDOW,
    DeliveryView,
    Recipient,
    RuleView,
)


logger = logging.getLogger(__name__)


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
        f"관제 화면에서 확인하십시오.\n"
        # ★ LAW-06 — 자동 분석 고지. **꼬리에 붙는다** (2026-09-05 · 차선 L).
        #   고지는 「어딘가에 적혀 있다」가 아니라 **읽는 자리에 있다**여야 뜻이 있다.
        #   화면 밖에서 판정을 처음 보는 사람은 이 본문으로 본다 — 그래서 여기다.
        #   문장은 common/ai_act_notice.py 한 곳에서만 정한다: 커널은 App 을
        #   import 할 수 없으므로(계층 역전 금지), 문장을 App 에 두면 두 벌이 되고
        #   두 벌이 된 고지는 한쪽만 고쳐진다.
        f"{notice_line()}"
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
                # ★ [턴 T · U3 · P-160] `webpush` 의 주소는 메일이 아니라 **구독 한 벌**이다.
                #   기기마다 한 통 — 구독 0인 사람은 **빠진다**(주소 없는 편지는 「보냈다」로
                #   적히지 않는다 · `webpush.py` 머리말 ①).
                if str(channel) == webpush_gate.WEBPUSH:
                    addresses = webpush_gate._subscription_addresses(user.pk)
                else:
                    addresses = (getattr(user, "email", "") or "",)
                for address in addresses:
                    out.append(Recipient(
                        user_id=user.pk,
                        display_name=getattr(user, "username", "") or str(user.pk),
                        address=address,
                        channel=str(channel),
                        rule_id=rule.pk,
                        role_code=getattr(rule.role, "code", "") or "",
                    ))
    return tuple(out)


def _owner_for(scope: TenantScope, group):
    """`group=` 을 받되 **사람이 남의 테넌트를 가리키지 못하게** 한다 (D-281 · D-290).

    ★ 2026-09-04 (차선 Q) — 이 함수가 없던 동안 `group=` 은 **무조건 믿는 인자**였다.
      파이프라인(시스템 스코프)에는 요청자가 없으니 그 인자가 꼭 필요하다. 그런데
      같은 인자를 사람이 넘길 수도 있었고, 그러면 A 테넌트 사용자가 `group=B` 로
      **B 의 이벤트 수와 카메라 맥박을 뽑아** 자기 수신자에게 메일로 보낼 수 있었다.
      읽기 격리를 온전히 지키고도 새는 자리이고, `WRITE_NO_PROBE` 의
      `send_heartbeat_digest` 항목이 정확히 그것을 경고하고 있었다.

    규칙 셋:
      · 시스템 스코프(요청자 없음)  → 준 `group` 을 그대로 쓴다. 사유는 스코프가 든다
      · 사람인데 `group` 이 없다     → 자기 소속
      · 사람인데 `group` 을 줬다     → **자기 것이거나 전역 관리자일 때만** 받는다

    ⚠ 거절은 값이 아니라 예외다. `None` 을 돌려주면 부르는 쪽이 「소속 없음」과
      「남의 것을 가리켰다」를 같은 모양으로 보고, 그 둘은 다른 사실이다.
    """
    from common.tenant_roles import is_global_admin

    actor = scope.actor
    if scope.is_system or actor is None:
        return group
    own = get_user_group(actor)
    if group is None:
        return own
    if is_global_admin(actor):
        return group
    if own is not None and getattr(group, "pk", None) == own.pk:
        return group
    # ★ 좁은 갈래다(2026-09-24 병합) — 격리 러너가 **권한 거절로만** 세게 한다.
    #   넓은 `InvalidNotifyInput` 으로 던지면 「모르는 채널」로 죽은 호출까지 「막혔다」가 된다.
    raise NotifyPermissionDenied(
        "남의 테넌트를 `group=` 으로 가리켰다. 이 인자는 요청자가 없는 호출"
        "(파이프라인·크론)을 위한 자리이지 **테넌트를 고르는 손잡이가 아니다** — "
        "사람이 고를 수 있으면 남의 관제 현황이 내 수신자에게 간다 (D-281)")


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
# 1-b. save_notification_rule — **규칙을 만드는 자리** (P-20 ① · 2026-09-22)
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 이 면이 열렸나 — **개발 DB 의 알림 규칙이 0건이었다** [실측 2026-09-21].
# 규칙이 0건이면 `resolve_recipients` 는 언제나 빈 목록을 내고, `send` 는 언제나
# `NoRecipients` 를 던진다. 즉 **알림 체계 전체가 꺼진 상태**이고, 그 상태에서
# 모바일 M1(내게 온 이벤트)은 빈 화면이다. 화면이 비어 있는 이유가 「사건이 없어서」인지
# 「규칙이 없어서」인지 화면만 봐서는 갈리지 않는다 — 그것이 이 면을 여는 이유다.
#
# ★ **시드가 행을 직접 만들지 않게 하려고 여기에 둔다** (P-9 · D-401).
#   `NotificationRule.objects.create(...)` 를 시드가 부르면 등급 열거·역할 실재·채널
#   이름·소속 판정이 **한 번도 안 돈다.** 그 네 검사가 안 돈 규칙은 화면에는 규칙으로
#   보이면서 발송에서는 아무도 못 고른다. D-401 이 이벤트에서 잡은 것과 같은 병이다.
def save_notification_rule(
    *,
    scope: TenantScope,
    severity: str,
    role_code: str,
    channels: Iterable[str],
    zone: str | None = None,
    is_active: bool = True,
    rule_id: int | None = None,
    group=None,
) -> RuleView:
    """알림 규칙 하나를 만들거나 고친다. **「누구에게 무엇이 가는가」가 정해지는 자리.**

    ★ 역할 **코드**로 받는다. 번호로 받으면 부르는 쪽이 `role.Role` 을 먼저 조회해야 하고,
      그러면 역할 모델이 K2 의 공개 계약이 된다(`Recipient.role_code` 와 같은 이유).
      그리고 번호는 환경마다 다르다 — 시드가 번호를 박으면 다른 DB 에서 **엉뚱한 역할**에
      재난 알림이 간다.

    ★ **채널 이름을 검사한다.** 등록된 어댑터가 없어도 좋다(업체 미정 · D4-1) —
      그러나 **아무 문자열이나 받지는 않는다.** 오타로 만든 채널은 발송 때마다 실패 행만
      남기고, 그 행을 보는 사람은 「업체가 죽었다」로 읽는다. 모르는 이름은 지금 막는다.

    ★ **남의 규칙은 없는 것으로 답한다** (`get_scoped_or_404` · D-269). 403 은 "그 번호는
      있지만 네 것이 아니다"를 알려 주고, 규칙의 존재 자체가 「저 테넌트가 무엇을 어떻게
      받는가」의 일부다.

    ⚠ 되돌려 주는 것은 모델이 아니라 `RuleView` 다 — 모델을 내보내면 App 이 그 위에서
      `.save()` 를 부르고, 그 순간 이 함수의 네 검사가 우회된다.
    """
    Rule = _model("NotificationRule")
    Event = _model("DetectionEvent")

    # ── ① 등급 ────────────────────────────────────────────────────────────
    if severity not in Event.Severity.values:
        raise InvalidNotifyInput(
            f"severity={severity!r} 은 계약에 없다. 허용: {', '.join(Event.Severity.values)}")

    # ── ② 채널 ────────────────────────────────────────────────────────────
    names = tuple(dict.fromkeys(str(c).strip() for c in channels if str(c).strip()))
    if not names:
        raise InvalidNotifyInput(
            "채널이 비었다 — 채널 없는 규칙은 **아무에게도 안 가는 규칙**이고, 화면에는 "
            "규칙으로 보인다. 그것이 D-284 가 이름 붙인 조용한 무력화다")
    unknown = [c for c in names
               if channel_registry.get(c) is None and c not in channel_registry.UNAVAILABLE]
    if unknown:
        raise InvalidNotifyInput(
            f"모르는 채널이다: {unknown}. 등록된 채널: "
            f"{', '.join(sorted(channel_registry.REGISTRY))} / 미구현(자리 있음): "
            f"{', '.join(sorted(channel_registry.UNAVAILABLE))}. "
            f"오타로 만든 채널은 발송마다 실패 행만 남기고, 그 행은 「업체가 죽었다」로 읽힌다")

    # ── ③ 역할 ────────────────────────────────────────────────────────────
    Role = apps.get_model("role", "Role")
    role = Role._base_manager.filter(code=role_code).first()
    if role is None:
        have = ", ".join(sorted(Role._base_manager.values_list("code", flat=True))[:20])
        raise InvalidNotifyInput(
            f"role_code={role_code!r} 인 역할이 없다. 있는 것(일부): {have}. "
            f"없는 역할을 가리키는 규칙은 **영원히 0명**을 고른다")

    # ── ④ 테넌트 ──────────────────────────────────────────────────────────
    actor = scope.actor
    group = group or (get_user_group(actor) if actor is not None else None)
    if group is None:
        raise InvalidNotifyInput(
            "규칙을 담을 테넌트가 없다. 파이프라인·시드 호출이면 `group=` 을 넘겨라 — "
            "그것 없이 만들면 **소유 없는 규칙**이 되고, 소유 없는 행은 §0.4 의 "
            "`created_by__isnull` OR 절을 타고 **모든 테넌트에 보인다** (D-281)")

    zone = (zone or "").strip() or None
    return _write_rule(Rule, scope, actor, group, role, severity, names, zone,
                       is_active, rule_id)


@transaction.atomic
def _write_rule(Rule, scope, actor, group, role, severity, names, zone,
                is_active, rule_id) -> RuleView:
    """검사를 다 지난 값을 **행으로 만든다.** 검사와 쓰기를 나눈 이유는 하나다 —
    `@transaction.atomic` 안에서 입력 검증까지 하면 거절도 트랜잭션을 열고 닫는다."""
    created = rule_id is None
    if created:
        row = Rule._base_manager.create(
            severity=severity, role=role, zone=zone,
            channels=list(names), is_active=is_active)
        _set_owner(row, group)
    else:
        # ★ 문지기가 **먼저다** (W0-14c). 안에 두면 "막힌 것"과 "찾고 나서 죽은 것"이
        #   구별되지 않는다. 시스템 스코프에는 요청자가 없으므로 소유를 직접 견준다.
        if actor is not None:
            from common.tenant_filters import get_scoped_or_404

            row = get_scoped_or_404(Rule, rule_id, actor)
        else:
            row = Rule._base_manager.filter(pk=rule_id).first()
            if row is None or not _owns(row, group):
                raise InvalidNotifyInput(
                    f"rule_id={rule_id} 는 이 테넌트의 규칙이 아니다 — 시스템 스코프라도 "
                    f"남의 규칙은 고치지 않는다 (D-281)")
        row.severity = severity
        row.role = role
        row.zone = zone
        row.channels = list(names)
        row.is_active = is_active
        row.save(update_fields=["severity", "role", "zone", "channels", "is_active"])

    view = RuleView(rule_id=row.pk, severity=row.severity, role_id=row.role_id,
                    role_code=getattr(role, "code", "") or "", zone=row.zone,
                    channels=tuple(row.channels or []), is_active=row.is_active)
    audit_writer.write(
        logger_name="guardianx.dsm.notify", tag="[RULE]", actor=actor,
        action="notify.save_rule", api_name=f"dsm.notify.save_rule:{row.pk}",
        api_method="POST" if created else "PUT",
        outcome=audit_writer.ALLOWED,
        reason=(f"알림 규칙 {'생성' if created else '수정'} — "
                f"{view.severity}/{view.role_code}/{view.zone or '*'} "
                f"채널 {', '.join(view.channels)}"),
        before=None if created else {"rule_id": row.pk},
        after={"rule_id": row.pk, "severity": view.severity,
               "role_code": view.role_code, "zone": view.zone,
               "channels": list(view.channels), "is_active": view.is_active},
        status_http=200,
    )
    return view


def _set_owner(row, group) -> None:
    """소유를 박는다. 필드 이름을 하드코딩하지 않는다 — `_inherit_owner` 와 같은 판단을
    쓰되, 물려받을 원본이 없는 자리(신규 규칙)라 group 을 직접 받는다."""
    field = _owner_field(type(row))
    if field == "groups":
        row.groups.set([group])
    else:
        setattr(row, "group", group)
        row.save(update_fields=["group"])


def _owns(row, group) -> bool:
    field = _owner_field(type(row))
    if field == "groups":
        return row.groups.filter(pk=group.pk).exists()
    return getattr(row, "group_id", None) == group.pk


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
    ).exclude(
        # ★ [턴 T · U3] 훈련(시험) 발송은 억제 근거가 아니다 — 시험 한 통이 다음 진짜
        #   경보를 삼키면 안 된다(`webpush.py` 머리말 ②).
        recipient_address__startswith=webpush_gate.DRILL_ADDRESS_PREFIX,
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
        # ★ [턴 U · P-173 §2 ④ 실측 · 턴 T 넘김] `resolve_recipients` 는 `zone=` 을
        #   받아 구역 규칙을 고를 수 있는데, 이 발송 경로는 그 값을 **한 번도
        #   넘기지 않고 있었다** — 카메라를 구역에 묶고 그 구역 전용 알림 규칙을
        #   만들어도, 실제 발송은 언제나 전역 규칙(`zone` 빈 규칙)만 썼다. 그
        #   차이는 지금 눈에 안 띈다 — [실측 2026-09-18 · 개발 DB] `Zone` 행 0건 ·
        #   구역 있는 `NotificationRule` 0/9 건 · 카메라 119 도 구역 0개라, 지금은
        #   `zone=None` 과 결과가 같다. 그래도 **와이어가 빠진 것은 사실**이고,
        #   `Zone` 이 채워지는 날 조용히 전역 규칙으로 새는 상태였다.
        #
        #   카메라 하나가 구역 여럿에 걸칠 수 있다(`Zone.cameras` M2M · 모델 머리말
        #   「하천 합류부·교차로」) — 그래서 구역마다 한 번씩 묻고 **사람·채널 단위로
        #   합쳐 중복 제거**한다(같은 사람이 두 구역 규칙에 걸려도 두 통 가지 않는다).
        #   구역이 없으면(지금의 모든 실측 데이터) **종전과 완전히 같다** — 뒤로
        #   호환된다.
        zone_names = tuple(
            event.stream_monitor.zones.values_list("name", flat=True))
        if zone_names:
            seen_recipient: set[tuple[int, str]] = set()
            merged: list[Recipient] = []
            for zone_name in zone_names:
                for r in resolve_recipients(
                        scope=scope, severity=event.severity, group=group,
                        zone=zone_name):
                    key = (r.user_id, r.channel)
                    if key in seen_recipient:
                        continue
                    seen_recipient.add(key)
                    merged.append(r)
            recipients = tuple(merged)
        else:
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

    # ★ 훈련 모드 (UX-17 · 2026-09-24 · 조율자가 잇는다 — 차선은 이 파일을 안 만진다)
    #
    #   테넌트가 훈련 중이면 **채널을 로그 어댑터로 바꾼다.** 지자체는 연 2회 이상
    #   재난 대응 훈련을 하고, 그날 실제 문자가 소방·팀장에게 나가면 **그날로 알림을 끈다.**
    #
    #   ★ 이름을 **가장하지 않고 그대로 남긴다**: 행의 `channel` 에 `log` 가 적히므로
    #     종료 보고서가 「사람이 아니라 로그로 갔다」를 말할 수 있다. 원래 채널로 적어 두고
    #     몰래 로그로 보내면, 그 행은 **보냈다는 거짓말**이 된다(D-284).
    #   ⚠ 안전한 기본값은 **실발송**이다 — `group_id` 가 없으면 `is_drill_mode` 는 거짓이다.
    #     스위치를 못 읽는 상태에서 조용해지는 것이 이 절이 막으려는 사고 그 자체다.
    from stream_monitors.services.drill import DRILL_CHANNEL, is_drill_mode

    group = _group_of(event)
    channel = (DRILL_CHANNEL
               if is_drill_mode(group_id=getattr(group, "pk", None))
               else recipient.channel)

    row = Delivery._base_manager.create(
        event=event,
        recipient_id=recipient.user_id,
        # ⚠ 구독 JSON 은 행에 적지 않는다 — 지문 12자로 접는다(`webpush.py` 머리말 ⚠).
        recipient_address=webpush_gate._address_label(recipient.address),
        channel=channel,
        occurred_at=event.occurred_at,
        succeeded=False,
        failure_reason=None,
        retry_count=0,
    )
    _inherit_owner(row, event)

    # ★ [턴 T · U3 · M4] 사람의 설정이 **지금 이 채널**을 막으면 보내지 않는다 — 그리고
    #   그 사실을 행에 **사유 이름**으로 남긴다(`quiet_hours` · `channel_not_chosen`).
    #   행이 없으면 「보낸 적 없음」과 「막혀서 안 보냄」이 같아진다(D-290).
    #   ⚠ 훈련 모드(`log`)는 막지 않는다 — 훈련은 사람의 채널이 아니라 로그로 가고,
    #     막으면 「훈련에서 몇 통이 갔을 것인가」를 세지 못한다.
    blocked = (None if channel == DRILL_CHANNEL
               else webpush_gate._blocked_reason(recipient.user_id, recipient.channel))
    if blocked:
        row.succeeded, row.sent_at, row.failure_reason = False, None, blocked
        row.save(update_fields=["succeeded", "sent_at", "failure_reason"])
        return _to_view(row)

    adapter = channel_registry.get(channel)
    if adapter is None:
        row.failure_reason = channel_registry.why_unavailable(channel)[:250]
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
# 3-b. notice_false_positive — 오탐으로 종결됐다고 **원 수신자에게 한 번** (P-16 · 오탐 ③)
# ═══════════════════════════════════════════════════════════════════════════
#: 이 통지의 감사 `logger_name`. 발송 이력(`DeliveryRecord`)과 **다른 자리**에 남긴다 —
#: 이유는 아래 함수 머리말 ★★ 를 보라.
FP_NOTICE_LOGGER = "guardianx.dsm.notify"
FP_NOTICE_ACTION = "notify.false_positive"


def _fp_notice_key(event_id: int) -> str:
    """이 이벤트의 통지 한 줄을 **정확히** 집는 이름. 「1회」는 이 이름으로 지켜진다."""
    return f"dsm.{FP_NOTICE_ACTION}:{event_id}"


def notice_false_positive(*, scope: TenantScope, event_id: int) -> tuple[str, ...]:
    """알림이 나갔던 이벤트가 오탐이 되면 **원 수신자에게 1회** 알린다.

    돌려주는 것: 알린 주소들. 알릴 사람이 없으면 빈 튜플이다 —
    **「보낸 적 없음」과 「받을 사람이 없음」은 다른 사실이다**(D-290).

    ★★ **왜 `DeliveryRecord` 행을 만들지 않는가.** 그 표는 F-10 의 30초 AC 를 재는
      두 점(`occurred_at → sent_at`)이고, 동시에 K2 의 5분 억제(`suppress`)가 세는
      표다. 여기에 통지 행을 끼우면 두 가지가 한꺼번에 망가진다:
        · F-10 지연 통계가 **경보가 아닌 것**을 경보로 세고
        · 5분 억제가 이 통지를 최근 발송으로 읽어 **그 다음 진짜 경보를 삼킨다**
      통지는 발송이 아니라 **뒷정리**다. 그래서 감사 한 줄로만 남긴다 — 세종이 지시한
      「로그 어댑터」가 이것이다.

    ★ **1회**는 감사 행의 존재로 지킨다. 같은 이벤트를 두 번 오탐이라 해도 통지는 하나다.
      두 번 알리면 「오탐이 두 번 일어났다」로 읽히고, 그 수를 누군가는 센다.
    """
    Delivery = _model("DeliveryRecord")
    Event = _model("DetectionEvent")

    event = Event._base_manager.filter(pk=event_id).first()
    if event is None:
        raise EventNotFound(f"event_id={event_id} 가 없다")
    if not scope.is_system:
        assert_scoped(Event, event_id, scope.actor)

    key = _fp_notice_key(event_id)
    if audit_writer.read(logger_name=FP_NOTICE_LOGGER, action=key, limit=1):
        return ()                     # 이미 알렸다 — 두 번째는 일어나지 않는다

    #: 원 수신자 = **실제로 받은 사람**이다. 실패한 발송은 받은 적이 없으므로 알릴
    #: 것도 없다 — 「보내려 했다」에 정정을 보내면 없던 경보를 만들어 낸다.
    addresses = tuple(dict.fromkeys(
        row.recipient_address
        for row in Delivery._base_manager.filter(event_id=event_id, succeeded=True)
        if row.recipient_address
    ))
    if not addresses:
        return ()

    audit_writer.write(
        logger_name=FP_NOTICE_LOGGER, tag="[FP]", actor=scope.actor,
        action=FP_NOTICE_ACTION, api_name=key, api_method="POST",
        outcome=audit_writer.ALLOWED,
        reason=(f"오탐으로 종결됨을 원 수신자 {len(addresses)}명에게 통지 "
                f"(event_id={event_id})"),
        before={"event_id": event_id, "verdict": "rejected"},
        after={"event_id": event_id, "notified": list(addresses)},
        status_http=200,
    )
    logger.info("[FP] event_id=%s 오탐 종결 통지 %d명: %s",
                event_id, len(addresses), ", ".join(addresses))
    return addresses


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
