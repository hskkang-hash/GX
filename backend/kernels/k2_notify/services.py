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
from common.billing_marks import exclude_soft_deleted, exclude_unbillable
from common.probe_marker import exclude_probe
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
#
# ★★ [턴 Z · F-04 · 2026-09-21 · **세종이 계약을 정했다**]
#
#     억제 키는 `event_id` 가 **아니라**
#     **「같은 스트림 + 같은 유형 + 직전 발송 시각」**이다.
#
#   이유: **억제는 사람에게 「같은 일이 또 왔다」를 막는 것이지 사건 번호를 막는 것이
#   아니다.** 사건 번호로 억제하면 같은 카메라에서 같은 일이 10번 나도 10번 다 울린다 —
#   번호가 매번 다르기 때문이다. 받는 사람에게 그것은 **한 가지 일**인데 열 번 울린 것이다.
#
#   ★ 턴 Y 는 이 키를 이미 들고 있었지만 **계약이라고 적지 못했다** — 「세종 문안은
#     『같은 사건』만 말한다 · 지금 구현은 그 상위집합이다 · 좁히는 판단은 네 시험의
#     주인들과 함께」라고 적어 두었다. 그 한 줄 때문에 이 저장소의 시험 **넷**이 서로
#     다른 키를 붙들고 있었다(하나는 「같은 사건을 두 번 눌러도 접힌다」 · 하나는 「옆
#     사건도 접힌다」 · 하나는 「다른 종류는 안 접힌다」 · 하나는 「재알림은 이 판정을
#     안 본다」). **같은 것을 재는 네 시험이 계약을 셋으로 나눠 들고 있으면, 키를 고치는
#     날 어느 것이 계약이었는지 아무도 못 말한다.**
#
#   그래서 오늘 둘을 한다:
#     ① 키를 **한 곳**으로 — 아래 `_suppression_key()`. 질의에 손으로 쓰지 않는다.
#     ② 시험 넷을 **한 계약**으로 — `backend/tests/test_f04_suppression_key.py`
#        (네 시험은 남는다 · 각자 제 갈래를 계속 재고, **키의 정본은 그 파일 하나**다).
#
#   ⚠ **문안은 GX-COPY 사전 그대로다** — 낱말을 새로 짓지 않는다:
#        짧은 말  「5분 안에 같은 사건 재발송 억제」
#        화면의 말 「새로 보낸 알림이 없습니다. 같은 사건의 알림은 5분 안에 다시 보내지
#                   않습니다. 아래 발송 이력을 확인하십시오.」(GX-COPY §2026-09-15 턴 Q)
#     사전의 **「같은 사건」은 「같은 사건 번호」가 아니라 「같은 카메라에서 같은 종류의
#     일」**이다 — 그것이 오늘 세종이 정한 뜻이고, 아래 키가 그 뜻이다.
def _suppression_key(event) -> dict:
    """F-04 억제 키 — **이 세 줄이 계약이다** (2026-09-21 · 세종).

        같은 스트림  `event__stream_monitor_id`
        같은 유형    `event__event_type`
        직전 발송    `sent_at` (창은 부르는 쪽이 건다 — 키는 「어느 행들인가」만 답한다)

    ★ **키를 질의에 손으로 쓰지 않는다.** 손으로 쓰면 부르는 자리마다 키가 한 벌씩
      생기고, 갈라진 쪽이 조용히 이긴다(`common/probe_marker.py` 가 있는 이유와 같다).
    ★ `event_id` 는 **키가 아니다.** 여기 없다는 것이 계약의 절반이다 — 있으면
      같은 카메라의 같은 일이 매번 새 번호로 와서 매번 울린다.
    """
    return {
        "event__stream_monitor_id": event.stream_monitor_id,
        "event__event_type": event.event_type,
    }


def suppress(*, scope: TenantScope, event_id: int, channel: str | None = None,
             now: datetime | None = None) -> bool:
    """이 이벤트에 대한 알림을 접어야 하는가 (F-04).

    문안 — GX-COPY: **「5분 안에 같은 사건 재발송 억제」**

    ★ 보는 것은 **발송 이력**이다. 이벤트 행이 아니다.
      메일 서버가 죽어 못 보낸 알림은 "이미 알렸다"가 아니다 — 그것을 억제로 세면
      장애 5분 동안의 재난 알림이 통째로 사라진다. 억제는 **성공한 발송** 위에서만 한다.

    ★★ [턴 Y · F-04 · 2026-09-20] **제품 결함을 고쳤다 — 기준이 움직이지 않았다.**

    종전의 질의는 이랬다 [실측 전 본문]::

        occurred_at__lt  = event.occurred_at
        occurred_at__gte = event.occurred_at - SUPPRESS_WINDOW

    세 글자가 틀렸다. `DeliveryRecord.occurred_at` 은 **발송 시각이 아니라 그 발송이
    붙은 사건의 발생 시각**이고(`_send_one` 이 `occurred_at=event.occurred_at` 으로
    복사한다), 창의 양 끝도 **지나간 한 순간**에 못박혀 있다. 그래서 이 함수는
    **시간이 흘러도 답이 안 바뀐다** — 억제는 원래 「지금은 안 된다」인데
    그것이 **「영원히 안 된다」**가 됐다.

    [실측 2026-09-20 · 조율자] `POST /api/dsm/events/4798/notify` →
    **200 `{"total":0,"deliveries":[]}`**. 16일 지난 사건에 관제요원이 「알림 보내기」를
    눌렀는데 아무 일도 안 일어난다. 누른 사람은 그것을 알 길이 없다 — 200 이니까.

    **새 기준: 「같은 사건 · 같은 채널의 직전 발송 시각」이 지금으로부터 5분 안인가.**

        · **발송 시각**은 `sent_at` 이다. `occurred_at` 이 아니다 — `sent_at` 은
          **성공했을 때만** 찍히므로(`_send_one`) 실패한 발송이 억제로 세어지지 않는다는
          위의 성질이 **같은 칸 하나로** 지켜진다.
        · **「같은 사건」이 이제 정말로 들어온다.** 종전 질의는 `stream+type` 으로 묶으면서
          `occurred_at__lt = event.occurred_at` 으로 **자기 발송만 잘라 냈다** — 그래서
          옆 사건은 접는데 자기 자신은 못 접는, 문안과 정반대인 상태였다. 그 한 줄을
          걷어 냈다. 묶는 키(`stream+type`)는 **좁히지 않았다**: 좁히면 옆 사건을 안 접게
          되고, 그 계약은 이 저장소의 시험 **넷**이 들고 있다.
          ★ [턴 Z · 2026-09-21] 턴 Y 가 여기 적었던 「상위집합이다 · 좁히는 판단은
            나중에」가 **계약으로 확정됐다**(이 절 머리 ★★ · 세종): 키는 `event_id` 가
            아니라 **스트림 + 유형 + 직전 발송 시각**이고, **좁히지 않는 것이 옳다** —
            억제는 사람에게 「같은 일이 또 왔다」를 막는 일이기 때문이다.
        · **같은 채널**이다. 3분 전에 `log` 로 갔다고 문자를 접으면, 문자만 보는
          사람은 **알림을 받은 적이 없다.** `channel=None` 은 「아무 채널이나」이다.

    ⚠ **`renotify` 는 이 문턱을 안 본다** — `send(respect_suppression=False)` 로 부른다
      (`renotify.py:209`). 재알림은 **무응답을 깨우는** 일이고 그 문턱은 더 길다
      (`after_minutes` · 기본 10분 이상). 그래서 이 변경은 재알림을 건드리지 않는다.

    Args:
        channel: 같은 채널만 볼 때 그 이름. `None` 이면 채널을 가리지 않는다.
        now: 재는 순간. 시험이 시계를 직접 움직이기 위해 받는다 — `renotify(now=)` 와
            **같은 규약**이다. 비우면 지금이다.
    """
    Event = _model("DetectionEvent")
    Delivery = _model("DeliveryRecord")

    event = Event._base_manager.select_related("stream_monitor").filter(pk=event_id).first()
    if event is None:
        raise EventNotFound(f"event_id={event_id} 가 없다")
    if not scope.is_system:
        assert_scoped(Event, event_id, scope.actor)

    at = now or timezone.now()
    qs = Delivery._base_manager.filter(
        succeeded=True,
        #: ★★ 묶는 키는 **`_suppression_key` 한 곳**에서 온다 (턴 Z · F-04 계약).
        #:   여기에 `event__…` 를 손으로 다시 적지 않는다 — 적는 순간 키가 두 벌이 되고,
        #:   두 벌이 된 키는 한쪽만 고쳐진 채로 조용히 산다.
        #:   ⚠ 이 집합은 **이 사건 자신의 발송을 포함한다.** 종전에는
        #:     `occurred_at__lt = event.occurred_at` 이 자기 발송을 잘라 냈고(발송 행의
        #:     `occurred_at` 은 제 사건의 발생 시각 복사본이라 `<` 가 아니다), 그래서
        #:     **같은 사건을 몇 번 눌러도 한 번도 안 접혔다** — `#295402` 가 무리 셋
        #:     (4+4+4)으로 쌓인 자리다.
        #:   계약을 든 시험: `backend/tests/test_f04_suppression_key.py`(정본) ·
        #:   갈래를 재는 넷: `test_k2_notify_kernel` · `test_s_webhook_outbox` ·
        #:   `test_u56_notify_repeat_count` · `test_d_mobile_field`.
        **_suppression_key(event),
        #: ★ `sent_at` 은 **성공한 발송에만** 있다. `isnull=False` 를 함께 거는 이유:
        #:   `succeeded=True` 인데 `sent_at` 이 빈 행이 과거에 쌓였다면(날짜 없는
        #:   성공) 그 행은 **언제인지를 모른다** — 모르는 것을 「방금」으로 읽으면
        #:   그 사건은 다시 영원히 접힌다. 모르면 **안 접는 쪽**에 둔다.
        sent_at__isnull=False,
        sent_at__gte=at - SUPPRESS_WINDOW,
        sent_at__lte=at,
    ).exclude(
        # ★ [턴 T · U3] 훈련(시험) 발송은 억제 근거가 아니다 — 시험 한 통이 다음 진짜
        #   경보를 삼키면 안 된다(`webpush.py` 머리말 ②).
        recipient_address__startswith=webpush_gate.DRILL_ADDRESS_PREFIX,
    )
    if channel:
        qs = qs.filter(channel=channel)
    return qs.exists()


# ════════════════════════════════════════════════════════════════════════════
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

    #: ★★ [턴 Y · F-04] 억제를 **채널마다** 묻는다 — 그리고 **보내기 전에 한 번에** 묻는다.
    #:
    #:   ① 채널마다인 이유: 3분 전에 `log` 로 나갔다고 문자를 접으면, 문자만 보는
    #:      사람은 **알림을 받은 적이 없는데** 받은 것으로 세어진다.
    #:   ② **미리** 묻는 이유 [실측 · 이 변경을 쓰다 내가 만든 빨강]: 루프 안에서 줄마다
    #:      물었더니 **첫 수신자에게 방금 보낸 행**이 둘째 수신자의 억제 근거가 됐다 —
    #:      같은 발송 한 번 안에서 둘째 사람부터 전부 접혔다
    #:      (`test_a_camera_in_two_zones_merges_recipients_without_duplicates` 가 잡았다).
    #:      억제는 **이 발송 직전의 사실** 위에서 하는 판정이지, 이 발송이 만들고
    #:      있는 사실 위에서 하는 판정이 아니다.
    #:
    #:   ⚠ 훈련 모드에서는 `_send_one` 이 채널을 `log` 로 바꿔 적는다 — 그때 묻는
    #:     이름(`recipient.channel`)과 쌓인 이름(`log`)이 갈린다. 훈련 중에는 **덜 접는**
    #:     쪽으로 기울고, 훈련은 발송 수를 세는 것이 목적이므로 그 기울기가 옳다.
    folded: set[str] = set()
    if respect_suppression:
        folded = {ch for ch in {r.channel for r in recipients}
                  if suppress(scope=scope, event_id=event_id, channel=ch)}

    views: list[DeliveryView] = []
    for recipient in recipients:
        if recipient.channel in folded:
            # 접는 것도 사실이다. 다만 **행을 만들지 않는다** — 발송 이력은 발송의
            # 이력이지 판정의 이력이 아니다. 판정 이력이 필요하면 K6 이 이벤트에서 센다.
            continue
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
    #: ★ **게이트가 심은 사건 때문에 나간 알림을 셀 것인가** (P-193 · 2026-09-20 · 차선 U1).
    #:   기본값이 `False` 인 것이 이 인자의 전부다 — 사건 축(`k1_event.query_events`)과
    #:   **같은 기본값**이라야 한 판정이 두 축에서 같은 뜻이 된다.
    #:   여는 쪽은 **발송 대장**(`GET /api/dsm/deliveries`, 「무엇이 언제 누구에게 갔나」)
    #:   하나뿐이다 — 거기서까지 빼면 그것은 세지 않기가 아니라 **보낸 적 없음**이 되고,
    #:   이 표의 머리말이 금지한 바로 그 모양이다(「실패도 행으로 남는다」).
    include_probe: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> tuple[DeliveryView, ...]:
    """발송 이력 조회. **테넌트 스코프 강제** · 필터는 전부 서버에서.

    K4 보고서의 "조치 이력" 행이 이 함수의 결과다 — 보고서용 목록을 따로 만들지 않는다
    (DA-04 K2 이중 AC: 두 벌로 적재하지 않는다).

    ★ P-193 (2026-09-20) — **발송 축에도 게이트 씨앗이 선다.** 사건 축만 막았더니
      관제요원의 M1 「나에게 온 것」 첫 카드가 게이트가 심은 알림이었다[실측 · 차선 U3].
      표식은 이 표에 없고 `event` 너머에 있다 — 따라가는 한 줄은 `common.probe_marker`
      한 곳이 안다(여기서 `event__track_id` 를 손으로 쓰면 표식이 두 벌이 된다).
    """
    qs = _deliveries_queryset(
        scope=scope, since=since, until=until, until_inclusive=True,
        event_id=event_id, recipient_id=recipient_id, succeeded=succeeded)
    #: ⚠ 훈련(`drill`)은 **여기서 안 뺀다** (P-201). 제품은 훈련 발송을 센다 —
    #:   빼는 것은 청구뿐이고, 그 자리는 아래 `count_deliveries` 다.
    if not include_probe:
        qs = exclude_probe(qs, via="event")
    qs = qs.distinct().order_by("-occurred_at", "-id")
    return tuple(_to_view(row) for row in qs[offset:offset + limit])


#: 발송을 **시간으로 가를 때 쓸 수 있는 칸**. 문자열을 그대로 받지 않는다 —
#: 부르는 쪽이 아무 칸 이름이나 넣으면 그것이 곧 질의 조립이고, 오타 한 번이
#: `FieldError` 가 아니라 **다른 수**로 나올 수 있다.
#:   occurred_at  사건이 난 시각. 실패 행도 갖고 있다.
#:   sent_at      **실제로 보낸** 시각. 실패 행은 `None` 이다(models.py 주석:
#:                "실패에 시각을 넣으면 30초 AC 가 실패한 발송으로도 달성된다").
COUNTABLE_TIME_FIELDS = ("occurred_at", "sent_at")


def _deliveries_queryset(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
    until_inclusive: bool = True,
    time_field: str = "occurred_at",
    event_id: int | None = None,
    recipient_id: int | None = None,
    succeeded: bool | None = None,
    own_tenant_only: bool = False,
):
    """`list_deliveries` 와 `count_deliveries` 가 **같은 한 벌의 필터**를 쓰게 하는 자리.

    ★ **표식(probe·drill)은 여기서 안 거른다** — 두 갈래가 갈리는 지점이 그 한 줄이다
      (K1 `_events_queryset` 과 같은 판단 · P-201).
    """
    if time_field not in COUNTABLE_TIME_FIELDS:
        raise InvalidNotifyInput(
            f"시간 칸은 {COUNTABLE_TIME_FIELDS} 중 하나다 (받은 값: {time_field!r})")
    Delivery = _model("DeliveryRecord")
    actor = scope.require_actor()

    qs = Delivery._base_manager.select_related("event")
    if own_tenant_only:
        #: ★ 전역 관리자여도 **제 테넌트만**. 이유는 `count_deliveries` 독스트링.
        group = get_user_group(actor)
        if group is None:
            raise InvalidNotifyInput(
                "요청자에게 소속이 없어 테넌트 단위로 셀 수 없다. 소속 없이 센 수는 "
                "누구의 것인지 답할 수 없고, 청구서에 적을 수 없다")
        qs = qs.filter(**{_owner_field(Delivery): group})
    else:
        qs = filter_by_group_field(qs, actor, field=_owner_field(Delivery))
    if since is not None:
        qs = qs.filter(**{f"{time_field}__gte": since})
    if until is not None:
        qs = qs.filter(
            **{f"{time_field}__{'lte' if until_inclusive else 'lt'}": until})
    if event_id is not None:
        qs = qs.filter(event_id=event_id)
    if recipient_id is not None:
        qs = qs.filter(recipient_id=recipient_id)
    if succeeded is not None:
        qs = qs.filter(succeeded=succeeded)
    return qs


def count_deliveries(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
    time_field: str = "occurred_at",
    event_id: int | None = None,
    recipient_id: int | None = None,
    succeeded: bool | None = None,
) -> int:
    """**청구서에 적을 발송 수** — `list_deliveries` 의 **셈 갈래** (P-206 · D-508).

    왜 이 함수가 생겼나 — 실측 2026-09-20 (차선 U1 이 찾아 넘겼다)
    --------------------------------------------------------------
    `apps/dsm/metering.py` 의 `_notifications` · `_notifications_failed` 가
    `apps.get_model("stream_monitors", "DeliveryRecord")` 로 표를 **직접** 셌다.
    커널을 안 지나니 P-193 의 표식도 P-201 의 훈련 구별도 그 셈에 없었다 —
    **게이트가 심은 씨앗 때문에 나간 알림에 돈이 청구되고 있었다.**

    ★ **표식 매개변수가 없다.** 청구의 셈은 **언제나** probe·drill 을 뺀다
      (P-201 이 `include_drill` 같은 칸을 이름으로 금지했다). 제품의 셈이 필요하면
      `list_deliveries` 를 부른다 — 그쪽은 훈련을 **센다.**

    ★ `time_field` — **실패는 `sent_at` 으로 못 센다.** 실패 행의 `sent_at` 은
      `None` 이고(models.py), 그 칸으로 거르면 실패 건수가 **언제나 0**이 된다.
      그래서 「보낸 알림」은 `sent_at`, 「실패한 발송」은 `occurred_at` 으로 센다 —
      두 수가 다른 칸을 보는 것은 실수가 아니라 **표의 사실**이다.

    ★ 반열린 구간 · 소프트 삭제 제외 · 전역 관리자도 제 테넌트만 —
      셋 다 `k1_event.count_events` 와 **같은 이유**다(그 독스트링).
    """
    Delivery = _model("DeliveryRecord")
    qs = _deliveries_queryset(
        scope=scope, since=since, until=until, until_inclusive=False,
        time_field=time_field, event_id=event_id, recipient_id=recipient_id,
        succeeded=succeeded, own_tenant_only=True)
    qs = exclude_unbillable(qs, via="event")
    qs = exclude_soft_deleted(qs, Delivery)
    return qs.distinct().count()
