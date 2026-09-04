# -*- coding: utf-8 -*-
"""생존 알림 — **dead man's switch** · OPS-14 (2026-09-04 · 차선 Q).

★ 규약 — 매뉴얼 첫 쪽에 이 문장이 간다
--------------------------------------

    **매일 08:00 「GuardianX 정상」 1통이 온다. 안 오면 장애다.**

    이 메일은 좋은 소식을 전하려고 오는 것이 아니다. **안 오는 것으로 말하려고** 온다.
    받은 날 할 일은 없다. 안 온 날 할 일이 있다 — `docs/agent/runbook/장애대응_1쪽.md`.

왜 이것이 필요한가 — **침묵과 정상은 같은 모양이다**
----------------------------------------------------
[실측 등재 2026-09-24 · PRD v2.5 ②] 서버가 1대다. 죽으면 탐지도 알림도 함께 멈춘다.
그런데 「사건이 없어서 조용한 것」과 「죽어서 조용한 것」이 U5 의 받은편지함에서
**완전히 같은 모양**이다. 지금 그 둘을 가르는 발송이 **0건**이다.

감시 3종(`common/ops_tasks.ops_monitor_beat`)이 이미 돌지만 그것은 **로그와 증거
파일**에 남고(`ops_monitor.py` 가 「보내는 자리를 여기서 정하지 않는다」고 적었다),
로그는 사람이 보러 가야 보인다. 보러 가야 하는 신호는 바쁜 날 안 본다.
이 함수가 하는 일은 그 신호를 **사람 쪽으로 한 걸음** 옮기는 것뿐이다.

누구에게 가나 — **경보를 받는 사람들**
--------------------------------------
새 수신자 표를 만들지 않는다. 지금 이 테넌트의 알림 규칙이 고르는 사람들에게 간다 —
**경보를 받는 사람이 곧 침묵을 알아채야 하는 사람**이기 때문이다. 수신자가 0명이면
`NoRecipients` 로 멈춘다: 아무에게도 안 가는 생존 알림은 그 자체가 침묵이고,
그것을 조용히 성공으로 세는 것이 D-284 가 이름 붙인 조용한 무력화다.

무엇으로 남나 — **감사 한 줄. 새 표를 만들지 않는다** (D-333)
-------------------------------------------------------------
`DeliveryRecord` 는 이벤트에 매달린 표다(`event` FK 는 null 이 아니다). 생존 알림은
이벤트가 아니므로 그 표에 들어갈 수 없고, 들어가게 하려고 FK 를 null 로 여는 순간
**F-10 의 30초를 재는 두 점**이 흐려진다. 그래서 `logger.AuditLogs` 에 한 줄로 남긴다 —
`common/audit_writer.py` 한 자리를 쓰고, LAW-08 해시 체인이 그 줄에도 붙는다.

    발송 기록 조회:  audit_writer.read(logger_name=DIGEST_LOGGER, action=DIGEST_ACTION)

★ **한 번 보낼 때 한 줄**이다. 수신자마다 한 줄을 남기면 「오늘 보냈는가」가 사람 수에
  따라 다른 수가 되고, dead man's switch 는 **1인가 0인가**만 물어야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common import audit_writer
from common.tenant_scope import TenantScope
from kernels.k2_notify import channels as channel_registry
from kernels.k2_notify.exceptions import (
    InvalidNotifyInput,
    NoRecipients,
    NotifyPermissionDenied,
)
from kernels.k2_notify.services import _owner_for, resolve_recipients

# ═══════════════════════════════════════════════════════════════════════════
# 규약의 수 — **한 곳에만 둔다** (D-212). 매뉴얼·크론·판정기가 여기를 인용한다
# ═══════════════════════════════════════════════════════════════════════════

#: 보내는 시각(현지 시각 기준 시). 08:00 인 이유: 야간 당직 교대 뒤 첫 근무 시간이고,
#: 이 시각을 넘겨 안 오면 **하루가 시작되기 전에** 사람이 안다.
DIGEST_HOUR: int = 8

#: 이 시간 안에 오면 「왔다」로 본다. 크론 지연·재시도가 08:00 정각을 못 맞추는 것은
#: 장애가 아니다 — 그러나 폭을 안 정하면 「늦게 왔다」와 「안 왔다」가 갈리지 않는다.
DIGEST_GRACE: timedelta = timedelta(hours=2)

#: 감사에 남는 자리. 판정기(`--json`)와 매뉴얼이 이 두 이름을 인용한다.
DIGEST_LOGGER: str = "guardianx.k2.heartbeat"
DIGEST_ACTION: str = "heartbeat_digest"

#: 매뉴얼 첫 쪽에 그대로 들어가는 문장. **코드가 원본이다** — 문서에 따로 적으면
#: 규약이 바뀌는 날 문서만 옛말이 된다 (D-286).
DEAD_MAN_RULE: str = (
    "매일 08:00 「GuardianX 정상」 1통이 옵니다. **안 오면 장애입니다.** "
    "받은 날 할 일은 없고, 안 온 날 할 일이 있습니다 — 장애 대응 1쪽을 여십시오."
)


def _model(name: str):
    return apps.get_model("stream_monitors", name)


# ═══════════════════════════════════════════════════════════════════════════
# 나가는 값
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class HeartbeatDigestResult:
    """생존 알림 한 번의 결과. **보낸 수와 실패 수를 따로 든다.**

    한 사람에게 실패해도 나머지에게는 간다(저하 운전 · DA2-21 (4)). 그러나 실패를
    성공에 섞으면 「전부 갔다」가 되고, 그 다음 날 아무도 안 받았는데 기록은 초록이다.
    """

    #: 이 발송을 가리키는 감사 행 번호. **「08:00 발송 기록 1건」의 그 1건이다.**
    audit_id: int
    sent_at: datetime
    #: 요약이 말하는 날 (어제).
    covers: date
    events_yesterday: int
    cameras_alive: int
    cameras_total: int
    cameras_never_seen: int
    recipients: int
    delivered: int
    failed: int
    subject: str
    body: str
    failures: tuple = ()


# ═══════════════════════════════════════════════════════════════════════════
# 순수 — 본문과 「왔는가」 판정
# ═══════════════════════════════════════════════════════════════════════════
def _compose(covers: date, events: int, pulse_line: str, sent_at: datetime):
    """제목과 본문. **판정 문장을 본문에 넣는다** — 받는 사람이 규약을 매번 다시 읽는다."""
    subject = f"[GuardianX] 정상 — {covers.isoformat()} 요약"
    body = "\n".join([
        "GuardianX 정상",
        "",
        f"어제({covers.isoformat()}) 이벤트 {events}건",
        pulse_line,
        "",
        f"발송 {sent_at.isoformat(timespec='seconds')}",
        DEAD_MAN_RULE,
    ])
    return subject, body


class _DigestClock:
    """「오늘 것이 안 왔는가」를 재는 자리.

    ★ **모양이 클래스인 이유는 커널 규약이다** (`channels._ChannelRegistry` 와 같은 수).
      `kernels/` 안의 모듈 최상위 공개 함수는 `*, scope: TenantScope` 를 필수로
      요구받는다(D-281 · `scripts/verify_tenant_scope.py`). 그 규약에는 면제가 없고,
      있어서도 안 된다 — 면제를 하나 열면 다음 함수가 그 문으로 들어온다.

      그런데 이 판정은 **시각 둘을 견주는 산수**다. 테넌트를 만지지 않고 DB 도 안 본다.
      그러므로 규약을 무르게 하는 대신 **모양을 바꾼다**: 객체의 메서드로 둔다.
    """

    def is_late(self, last_sent: datetime | None, now: datetime,
                *, hour: int = DIGEST_HOUR,
                grace: timedelta = DIGEST_GRACE) -> tuple:
        """오늘 것이 **와야 할 시각을 넘겼는데 안 왔는가.** `(늦었다, 사유)`.

        ★ 이 판정이 없으면 이 절은 「보낸다」에서 끝난다. dead man's switch 의 값은
          **안 온 것을 누가 알아채는가**에 있고, 그 답이 사람의 기억이면 장치가 아니다.

        ★ 「아직 안 왔다」와 「늦었다」를 가른다 — 07:59 에 안 온 것은 정상이다.
          그 둘을 뭉치면 매일 아침 두 시간 동안 장애 경보가 뜨고, 그러면 이 신호가
          꺼진다(D-290).
        """
        due = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if now < due + grace:
            return (False, f"오늘 {hour:02d}:00 + 유예 {grace} 가 아직 안 지났다")
        if last_sent is None:
            return (True, f"발송 기록이 **한 건도 없다** — {hour:02d}:00 알림이 선 적이 없다")
        if last_sent < due:
            return (True, f"마지막 발송이 {last_sent.isoformat(timespec='seconds')} 다 — "
                          f"오늘 {hour:02d}:00 것이 안 왔다. **그것이 장애다**")
        return (False, f"오늘 것이 {last_sent.isoformat(timespec='seconds')} 에 왔다")


#: 부르는 쪽이 쓰는 이름.
digest_clock = _DigestClock()


# ═══════════════════════════════════════════════════════════════════════════
# 공개 면
# ═══════════════════════════════════════════════════════════════════════════
def send_heartbeat_digest(
    *,
    scope: TenantScope,
    group=None,
    now: datetime | None = None,
    channel: str = "email",
) -> HeartbeatDigestResult:
    """「GuardianX 정상 · 어제 이벤트 N · 카메라 맥박 N/N」 1통을 보낸다.

    ★ 남의 테넌트 요약을 내 수신자에게 보낼 수 없다. 본문에 실리는 것은 **그 테넌트의
      관제 현황**이고, 잘못 가면 그것은 안부 인사가 아니라 **반출**이다. 그래서 수와
      수신자를 **같은 group** 하나에서 뽑는다 — 둘을 따로 받으면 어긋날 자리가 생긴다.
    """
    adapter = channel_registry.get(channel)
    if adapter is None:
        raise InvalidNotifyInput(
            f"채널 {channel!r} 로는 못 보낸다 — {channel_registry.why_unavailable(channel)}")

    actor = scope.actor
    # ★ `group=` 을 그대로 믿지 않는다 — 사람이 남의 테넌트를 가리키면 거절한다.
    #   판단은 `services._owner_for` 한 곳이다 (D-212).
    owner = _owner_for(scope, group)
    if owner is None:
        raise InvalidNotifyInput(
            "요약을 낼 테넌트가 없다. 크론 호출이면 `group=` 을 넘겨라 — 그것 없이 세면 "
            "**전 테넌트의 수**가 한 통에 실리고, 그것은 남의 관제 현황 반출이다 (D-281)")

    now = now or timezone.now()
    covers = (now - timedelta(days=1)).date()
    events = _events_on(covers, owner, now)
    pulse = _pulse_line(scope, now, owner)

    people = _digest_recipients(scope, owner, channel)
    if not people:
        raise NoRecipients(
            "생존 알림을 받을 사람이 0명이다 — 이 테넌트의 알림 규칙이 아무도 고르지 "
            "않는다. 아무에게도 안 가는 dead man's switch 는 그 자체가 침묵이고, "
            "그것을 성공으로 세는 것이 조용한 무력화다 (D-284)")

    subject, body = _compose(covers, events, pulse[0], now)
    delivered, failures = 0, []
    for person in people:
        outcome = adapter.send(address=person.address, subject=subject, body=body)
        if outcome.ok:
            delivered += 1
        else:
            failures.append((person.address, outcome.reason))

    entry = _record(
        actor=actor, covers=covers, events=events, pulse=pulse, channel=channel,
        delivered=delivered, recipients=len(people), failures=failures, now=now,
        owner=owner)

    return HeartbeatDigestResult(
        audit_id=entry.audit_id, sent_at=now, covers=covers,
        events_yesterday=events,
        cameras_alive=pulse[1], cameras_total=pulse[2], cameras_never_seen=pulse[3],
        recipients=len(people), delivered=delivered, failed=len(failures),
        subject=subject, body=body, failures=tuple(failures),
    )


@transaction.atomic
def _record(*, actor, covers, events, pulse, channel, delivered, recipients,
            failures, now, owner=None):
    """감사 한 줄. **보냈든 못 보냈든 남는다** — 실패도 행이 된다 (D-290).

    `outcome` 이 `DENIED` 인 경우는 「한 명에게도 못 갔다」뿐이다. 일부 실패는
    `ALLOWED` 이고 그 사실이 `data_after` 에 수로 남는다 — 저하 운전은 실패가 아니다.
    """
    ok = delivered > 0
    reason = (f"어제({covers.isoformat()}) 이벤트 {events}건 · {pulse[0]} · "
              f"수신자 {recipients}명 중 {delivered}명 도달 · 채널 {channel}")
    if failures:
        reason += f" · 실패 {len(failures)}건"
    return audit_writer.write(
        logger_name=DIGEST_LOGGER,
        tag="[OPS-14]",
        actor=actor,
        action=DIGEST_ACTION,
        outcome=audit_writer.ALLOWED if ok else audit_writer.DENIED,
        reason=reason,
        after={
            #: ★ [2026-09-24 병합] **어느 테넌트의 안부인가.** 이 칸이 없던 동안 감사 행은
            #:   「누가 보냈나」는 말하고 「누구 것인가」는 말하지 않았다 — 크론은 요청자가
            #:   없으므로 `actor` 로도 못 되짚는다. 그러면 `heartbeat_watch` 가
            #:   「이 테넌트 것이 안 왔다」를 영원히 말할 수 없다.
            "group_id": getattr(owner, "pk", None),
            "covers": covers.isoformat(),
            "events_yesterday": events,
            "cameras_alive": pulse[1],
            "cameras_total": pulse[2],
            "cameras_never_seen": pulse[3],
            "recipients": recipients,
            "delivered": delivered,
            "failures": [f"{addr}: {why}" for (addr, why) in failures],
            "channel": channel,
            "sent_at": now.isoformat(timespec="seconds"),
        },
    )


def heartbeat_watch(*, scope: TenantScope, now: datetime | None = None) -> tuple:
    """**안 온 것을 알아채는 자리** — dead man's switch 의 나머지 절반.

    보내는 것만으로는 이 절이 서지 않는다. 「안 오면 장애다」의 값은 **안 온 것을 누가
    아는가**에 있고, 그 답이 사람의 기억이면 그것은 장치가 아니다(D-290).

    Returns:
        `((group_id, late, why), ...)` — 테넌트마다 한 줄. **늦지 않은 것도 돌려준다**:
        늦은 것만 돌려주면 「본 적이 없다」와 「봤는데 괜찮다」가 같은 빈 목록이 된다.

    ⚠ 읽기만 한다. 여기서 다시 보내지 않는다 — 감시가 발송을 겸하면 감시가 부하를 만들고,
      그 부하가 다시 감시 대상이 된다(D-412 ③ 과 같은 이유).
    """
    from django.apps import apps
    from django.utils import timezone

    from common import audit_writer

    #: ★ **사람은 부를 수 없다.** 이 함수는 전 테넌트의 「오늘 것이 왔는가」를 한 줄씩
    #:   돌려준다 — 그것은 한 테넌트의 사실이 아니라 **설비 전체의 사실**이고, 사람이
    #:   부를 수 있으면 「지금 알림이 안 나가는 테넌트」를 남이 알 수 있게 된다.
    #:   문지기로 좁히지 않고 **문 자체를 시스템에만 연다** — 좁힐 대상이 없기 때문이다.
    if not scope.is_system:
        raise NotifyPermissionDenied(
            "생존 알림 감시는 시스템 스코프 전용이다. 사람이 부르면 전 테넌트의 "
            "「알림이 안 나가는 상태」가 한 응답에 실린다 — 그것은 감시가 아니라 정찰이다")

    now = now or timezone.now()
    #: ★ 최근 것부터 한 번만 읽고 **파이썬에서 테넌트별 첫 줄**을 집는다.
    #:   테넌트마다 질의를 날리면 테넌트 수만큼 왕복하고, 그 비용이 5분마다 돈다.
    #:   `api_name` 이 action 이 저장되는 칸이다 — `audit_writer.write()` 가 그렇게 쓴다.
    rows = (audit_writer._model()._base_manager
            .filter(logger_name=DIGEST_LOGGER, api_name=DIGEST_ACTION)
            .order_by("-id")[:500])
    last_by_group: dict = {}
    for row in rows:
        after = row.data_after if isinstance(row.data_after, dict) else {}
        gid = after.get("group_id")
        if gid is None or gid in last_by_group:
            continue
        last_by_group[gid] = (getattr(row, "create_datetime", None)
                              or getattr(row, "created_on", None))

    out = []
    for group in apps.get_model("user", "UserGroup").objects.all():
        late, why = digest_clock.is_late(last_by_group.get(group.pk), now)
        out.append((group.pk, late, why))
    return tuple(out)


def _events_on(day: date, owner, now: datetime) -> int:
    """그 날 하루의 이벤트 수. **그 테넌트 것만** 센다."""
    Event = _model("DetectionEvent")
    # ★ 소유 필드 판단은 **K2 자신의 자리**를 통해 쓴다 (`services._owner_field`).
    #   그 함수가 K1 의 판단기를 그대로 부른다 — 판단은 한 곳에서만(D-212).
    #   여기서 K1 을 직접 import 하지 않는 이유: 이 모듈이 **K1 소비자로 등재**
    #   되어야 하고(F-05 진입면 대장), 등재는 「이벤트를 쓴다」는 선언이다.
    #   이 두 모듈은 이벤트를 **세거나 요약할 뿐** 만들지 않는다.
    from kernels.k2_notify.services import _owner_field

    start = timezone.make_aware(
        datetime.combine(day, datetime.min.time()), timezone.get_current_timezone()
    ) if timezone.is_aware(now) else datetime.combine(day, datetime.min.time())
    qs = Event._base_manager.filter(occurred_at__gte=start,
                                    occurred_at__lt=start + timedelta(days=1))
    if _owner_field(Event) == "groups":
        return qs.filter(groups=owner).distinct().count()
    return qs.filter(group=owner).count()


def _pulse_line(scope: TenantScope, now: datetime, owner):
    """「카메라 맥박 N/N」. 판정은 `camera_pulse` 한 곳이 한다 — 여기서 다시 세지 않는다."""
    from stream_monitors.services.camera_pulse import pulse_counts

    counts = pulse_counts(scope=scope, now=now, group=owner)
    return (counts.as_line(), counts.alive, counts.total, counts.never_seen)


def _digest_recipients(scope: TenantScope, owner, channel: str):
    """경보를 받는 사람들. **등급 전체를 훑어 한 사람은 한 번만** 담는다.

    새 수신자 표를 만들지 않는 이유는 하나다 — 표가 둘이면 인사이동 때 한쪽만 고쳐지고,
    안 고쳐진 쪽이 **퇴사자에게 매일 아침 관제 현황을 보내는 상태**로 남는다.
    """
    Event = _model("DetectionEvent")
    seen: set = set()
    out: list = []
    for severity in Event.Severity.values:
        for person in resolve_recipients(scope=scope, severity=severity, group=owner):
            if person.user_id in seen or not person.address:
                continue
            seen.add(person.user_id)
            out.append(person)
    return out


__all__ = [
    "DIGEST_HOUR",
    "DIGEST_GRACE",
    "DIGEST_LOGGER",
    "DIGEST_ACTION",
    "DEAD_MAN_RULE",
    "HeartbeatDigestResult",
    "digest_clock",
    "send_heartbeat_digest",
    "heartbeat_watch",
]
