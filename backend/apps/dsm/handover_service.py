# -*- coding: utf-8 -*-
"""UX-34 — **교대 인계 자동 초안** (`POST|GET /api/dsm/handover/draft`) · 차선 U1 · 턴 R.

무엇을 짓는가 — **서버가 쓰고 사람이 고친다**
------------------------------------------------
그전(턴 O·차선 C2 `ShiftHandoverPanel.tsx`)까지는 화면이 `events/summary` 두 수를
빌려 그 자리에서 문장을 지었다. 이번 턴은 그 자동 초안을 **서버 쪽에 표(`DsmHandover`
· 턴 Q 가 세운 표)로 옮긴다** — 사람이 손으로 세지 않고, 다음 근무자 홈이 읽을
자리가 화면 렌더가 아니라 **저장된 행**이 되게 한다(UX-32-U2 「최신 1」).

★ **셈은 여기서 하지 않는다.** 미처리·시스템 사건·내가 처리한 건수는 전부
  `apps.dsm.services.recent_events`(K1 을 그대로 부르는 얇은 층)가 센 것을 옮길
  뿐이다. App 이 다시 세면 두 집계가 생기고, 두 집계는 반드시 어긋난다
  (`events_summary`·W1 요약이 이미 지킨 규약과 같다).

★ 2026-09-20 (턴 X · P-193) — 그래서 본문의 **「미처리 N」은 게이트가 심은 probe 사건을
  세지 않는다.** 여기에 줄 하나 더하지 않아서 그렇게 된다: `recent_events` 의 기본값이
  「안 센다」이기 때문이다(`common/probe_marker.py` 가 뜻을 정하고 커널이 거른다).
  다음 근무자가 읽는 첫 줄이 **게이트가 몇 번 돌았는지**를 말하면 안 된다 —
  인계는 사람이 이어받을 일감의 목록이고, 씨앗은 일감이 아니다.

★ **사건 id 를 본문에 적는다.** 닫는 조건(RESUME_NEXT 턴 R · U1)이 요구하는 것이
  「수가 실제 그 시간대 사건에서 나왔다」는 증거다. 수만 적으면 「지어낸 수」와
  구별이 안 된다 — id 가 그 증거다(D-301 「수를 지어내지 않는다」의 같은 계열).

★ **표 저장은 `stream_monitors.models.DsmHandover`** — 턴 Q 가 이미 세웠다. 새로
  만들지 않는다. 테넌트 칸은 `group`(FK) — `apps/dsm/field.py::save_field_photo`
  가 같은 표 계열(`TenantModel`)에서 확인한 것과 같은 이름이다(F-DB 차선의 선언이
  정본이다 — 새로 판정하지 않는다).

★ [턴 AO · P-407 · 차선 N1] **DSM-U5-05 「인계 메모 근무자 자동」 연결** —
  `shift_roster_service.current_workers()`(턴 AN 이 세운 함수)가 편성표에서
  그 날짜의 조별 근무자를 이미 구조화해 낸다. 이 함수는 그것을 인계 초안의
  **본문 한 줄**로 옮긴다(`draft.on_duty` 로도 구조째 낸다) — **새 표는 0**이다
  (`DsmHandover` 에 칸을 더하지 않는다 · 위 「표 저장」 머리말과 같은 판단).
  근무표가 그 날짜에 없으면(팀이 0) 「근무 편성 없음」을 그대로 적는다 —
  지어내지 않는다(D-280).
  ★ **여전히 닫지 않는 것**을 정직하게 남긴다 — 관제일지(DSM-U1-04) 자체가
  이 저장소 어디에도 없다. 이 함수가 잇는 것은 「인계 메모가 근무자를 자동으로
  담는다」는 사실 하나이지, 명세의 완결조건 「일지 근무자 = 편성표」 그 자체가
  아니다(일지가 없으므로).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.dsm import services, shift_roster_service
from common.tenant_scope import TenantScope

#: W1 「시스템」 프리셋(`api.py` events 목록 · U2#19)과 같은 목록이다. 여기서
#: 새로 정하지 않는다 — 두 곳에 있으면 언젠가 갈린다.
_SYSTEM_EVENT_TYPES = ["camera_down", "storage_high"]

#: 본문에 사건 번호를 **이름으로** 적는 상한. 40건을 다 적으면 인계 메모가 아니라
#: 목록이 된다 — 3분에 읽을 수 있는 수만 적는다(PRD v1.1 「인계는 3분」).
_NAMED_UNRESOLVED_CAP = 5

#: 한 번에 세는 상한 — `events_summary` 의 `_UNHANDLED_CAP` 과 같은 자리 다른 값.
#: 인계 초안은 카드 한 장이라 200 이면 넉넉하고, 넘으면 "이상"으로 적는다.
_COUNT_CAP = 200


class HandoverRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없거나 그 밖의 저장 불가 사유. 사람의 말로 담는다."""


#: DSM-U2-05 「교대 인수인계 합동 확인」 — 확인 여부는 **표를 늘리지 않고** 감사에 남긴다
#: (이 파일 머리말 「셈은 여기서 하지 않는다」와 같은 결의 판단 — 확인도 새 칸이 아니라
#: 새 감사 줄이다). `DsmHandover` 에 칸을 더하면 이관(migration)이 필요하고, 확인은
#: 「그 인계를 팀장이 봤다」는 사실 하나이지 상태가 아니다 — 감사 표가 정확히 그 모양이다.
_ACK_LOGGER_NAME = "guardianx.u2.handover_ack"
_ACK_TAG = "[U2-HANDOVER-ACK]"


def _ack_action(handover_id: int) -> str:
    return f"handover_ack:{handover_id}"


def _is_acknowledged(handover_id: int) -> bool:
    from common import audit_writer

    action = _ack_action(handover_id)
    return bool(audit_writer.read(
        logger_name=_ACK_LOGGER_NAME, action=action, limit=1))


@dataclass(frozen=True)
class HandoverDraft:
    body: str
    summary_line: str
    unresolved_count: int
    unresolved_capped: bool
    system_event_count: int
    handled_count: int
    unresolved_event_ids: list[int]
    since: Any
    until: Any
    hours: int
    #: [턴 AO · P-407] DSM-U5-05 「인계 메모 근무자 자동」 — 그 날짜의 조별
    #: 근무자(`shift_roster_service.current_workers()` 그대로). 근무표가 없으면
    #: `{"date": ..., "teams": [], "team_count": 0}`.
    on_duty: dict


def _actor_id(scope: TenantScope) -> int | None:
    try:
        return getattr(scope.require_actor(), "pk", None)
    except Exception:  # noqa: BLE001 — 시스템 스코프 등 「나」가 없는 요청
        return None


def build_draft(*, scope: TenantScope, hours: int = 24) -> HandoverDraft:
    """근무 시간대(`hours`) 기록에서 본문을 짓는다. **셈은 K1 이 한다** — 여기선 옮길 뿐.

    Raises:
        ValueError: `hours` 가 계약 밖(0 이하 또는 31일 초과) — `events_summary` 와
            같은 창.
    """
    if hours <= 0 or hours > 24 * 31:
        raise ValueError("hours 는 1 이상 744(31일) 이하여야 합니다.")

    until = timezone.now()
    since = until - timedelta(hours=hours)

    unresolved = services.recent_events(
        scope=scope, since=since, until=until,
        response_state="occurred", limit=_COUNT_CAP + 1)
    unresolved_capped = len(unresolved) > _COUNT_CAP
    unresolved = unresolved[:_COUNT_CAP]

    system_events = services.recent_events(
        scope=scope, since=since, until=until,
        event_type=_SYSTEM_EVENT_TYPES, limit=_COUNT_CAP)

    actor_id = _actor_id(scope)
    handled = (services.recent_events(
        scope=scope, since=since, until=until,
        reviewed_by_id=actor_id, limit=_COUNT_CAP)
        if actor_id is not None else [])

    unresolved_ids = [e.event_id for e in unresolved]
    named_ids = unresolved_ids[:_NAMED_UNRESOLVED_CAP]
    if named_ids:
        names = ", ".join(f"#{i}" for i in named_ids)
        more = " 외" if len(unresolved_ids) > len(named_ids) else ""
        id_note = f" ({names}{more})"
    else:
        id_note = ""

    stamp = timezone.localtime(until).strftime("%Y-%m-%d %H:%M")
    unresolved_label = (f"{len(unresolved_ids)}건 이상" if unresolved_capped
                        else f"{len(unresolved_ids)}건")

    #: [턴 AO · P-407] DSM-U5-05 — 이 인계가 다루는 날짜(`until` 의 현지 날짜)의
    #: 조별 근무자를 편성표에서 그대로 가져온다. 근무표가 없어도(팀 0) 예외를
    #: 올리지 않는다 — 인계는 근무표가 없어도 성립한다(머리말 「셈은 여기서 하지
    #: 않는다」와 같은 결의 판단 — 근무표가 비면 「없다」고 정직하게 적는다).
    on_duty_date = timezone.localtime(until).date().isoformat()
    try:
        on_duty = shift_roster_service.current_workers(scope=scope, date=on_duty_date)
    except ValueError:
        on_duty = {"date": on_duty_date, "teams": [], "team_count": 0}

    if on_duty["teams"]:
        team_bits = [
            f"{t['team']}({t['shift'] or '?'}) "
            + (",".join(t["members"]) if t["members"] else "(명단 없음)")
            for t in on_duty["teams"]
        ]
        roster_line = (f"근무 편성 {on_duty['team_count']}개 조 — "
                       + " · ".join(team_bits))
    else:
        roster_line = "근무 편성 없음(등록된 근무표 없음)"

    #: ★ 본문 **5줄** — 근무자 자동 줄(DSM-U5-05)을 더해 넷에서 다섯이 됐다.
    #: 여섯째 줄(넘기는 말)은 여전히 사람의 자리다.
    body_lines = [
        f"[교대 인계 자동 초안] {stamp} (최근 {hours}시간)",
        f"미처리 {unresolved_label}{id_note}",
        f"시스템 사건 {len(system_events)}건",
        f"내가 처리한 사건 {len(handled)}건"
        + ("" if actor_id is not None else " (요청자를 특정할 수 없어 못 셌습니다)"),
        roster_line,
    ]
    summary_line = (
        f"미처리 {unresolved_label} · 시스템 {len(system_events)} · "
        f"처리 {len(handled)} ({stamp})")

    return HandoverDraft(
        body="\n".join(body_lines),
        summary_line=summary_line,
        unresolved_count=len(unresolved_ids),
        unresolved_capped=unresolved_capped,
        system_event_count=len(system_events),
        handled_count=len(handled),
        unresolved_event_ids=unresolved_ids,
        since=since, until=until, hours=hours,
        on_duty=on_duty,
    )


def _as_dict(draft: HandoverDraft) -> dict:
    return {
        "body": draft.body,
        "summary_line": draft.summary_line,
        "unresolved_count": draft.unresolved_count,
        "unresolved_capped": draft.unresolved_capped,
        "system_event_count": draft.system_event_count,
        "handled_count": draft.handled_count,
        "unresolved_event_ids": draft.unresolved_event_ids,
        "since": draft.since,
        "until": draft.until,
        "hours": draft.hours,
        #: [턴 AO · P-407] DSM-U5-05 — 근무자 자동(구조째). 저장된 것은 본문
        #: 텍스트뿐(위 「새 표 0」) — 이 칸은 `preview`·`save` 응답에서 그 순간의
        #: 계산값을 그대로 낸다.
        "on_duty": draft.on_duty,
    }


def preview(*, scope: TenantScope, hours: int = 24) -> dict:
    """GET — **저장하지 않는다.** 사람이 고치기 전에 서버가 쓴 글을 미리 본다."""
    return _as_dict(build_draft(scope=scope, hours=hours))


def save(*, scope: TenantScope, hours: int = 24, note: str = "") -> dict:
    """POST — 초안을 `DsmHandover` 한 행으로 적는다.

    `note` 는 사람이 그 자리에서 더하는 특이사항 한 줄(비어도 인계는 성립한다 —
    `ShiftHandoverPanel.tsx` 머리말과 같은 판단). 본문(`body`)은 **여기서 짓는다** —
    사람은 그것을 고쳐 다시 보낼 수 있지만(재저장은 새 행), 빈 칸을 채우는 것이
    아니다.

    Raises:
        ValueError: `hours` 계약 밖.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
        HandoverRejected: 소속 조직이 없어 저장할 수 없다.
    """
    from django.apps import apps

    from common.tenant_filters import get_user_group

    draft = build_draft(scope=scope, hours=hours)
    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead 를 올린다

    group = get_user_group(actor)
    if group is None:
        raise HandoverRejected("소속 조직이 없어 인계 메모를 저장할 수 없습니다.")

    DsmHandover = apps.get_model("stream_monitors", "DsmHandover")
    row = DsmHandover.objects.create(
        body=draft.body,
        note=(note or "").strip(),
        unresolved_count=draft.unresolved_count,
        system_event_count=draft.system_event_count,
        handled_count=draft.handled_count,
        unresolved_event_ids=draft.unresolved_event_ids,
        group=group,
        #: ISO-03 목적 선언 — `dsm.handover_draft` 는 이 파일에서만 쓴다.
        purpose_code="dsm.handover_draft",
    )

    out = _as_dict(draft)
    out.update({
        "id": row.pk,
        "note": row.note,
        "created_at": row.created_on,
    })
    return out


def latest(*, scope: TenantScope) -> dict:
    """GET — **다음 근무자 홈 카드**가 읽을 자리(UX-32-U2 「최신 1」).

    ★ 화면에 그리는 것은 F 차선의 몫이다 — 여기서는 라우트와 응답만 연다.
    ★ 테넌트로 다시 좁힌다(`group=group`) — 기본 매니저가 스레드 값으로 이미
      좁혀도(D-... 스레드에 남은 요청 함정), 명시로 다시 좁히면 그 함정이 조용히
      섞여도 여기서는 새지 않는다.
    """
    from django.apps import apps

    from common.tenant_filters import get_user_group

    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return {"exists": False}

    DsmHandover = apps.get_model("stream_monitors", "DsmHandover")
    row = DsmHandover.objects.filter(group=group).order_by("-id").first()
    if row is None:
        return {"exists": False}

    return {
        "exists": True,
        "id": row.pk,
        "body": row.body,
        "note": row.note,
        "unresolved_count": row.unresolved_count,
        "system_event_count": row.system_event_count,
        "handled_count": row.handled_count,
        "unresolved_event_ids": row.unresolved_event_ids,
        "created_at": row.created_on,
        #: DSM-U2-05 — 홈 카드 「인계 확인 ✓」가 읽는 칸.
        "acknowledged": _is_acknowledged(row.pk),
    }


def acknowledge(*, scope: TenantScope, handover_id: int) -> dict:
    """DSM-U2-05 — **교대 인수인계 합동 확인**(`POST /api/dsm/handover/{id}/ack`).

    08~09시 인계 메모를 팀장이 「확인」 버튼으로 체크하는 자리. 같은 표
    (`DsmHandover`)를 다시 읽어 **그 인계가 내 테넌트 것인지 먼저 확인**한다
    (`event_note_service` 의 「먼저 확인」과 같은 순서 — 문지기를 두 번 세우지 않되,
    남의 인계 id 를 넣으면 이 함수 앞에서 막힌다).

    Raises:
        django.http.Http404: 그런 인계 메모가 없다 · 남의 테넌트 것이다 ·
            요청자에게 소속 조직이 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.apps import apps
    from django.http import Http404

    from common import audit_writer
    from common.tenant_filters import get_user_group

    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise Http404("소속 조직이 없어 이 인계 메모를 확인할 수 없습니다.")

    DsmHandover = apps.get_model("stream_monitors", "DsmHandover")
    row = DsmHandover.objects.filter(pk=handover_id, group=group).first()
    if row is None:
        raise Http404("그런 인계 메모가 없습니다.")

    entry = audit_writer.write(
        logger_name=_ACK_LOGGER_NAME, tag=_ACK_TAG, actor=actor,
        action=_ack_action(handover_id), outcome=audit_writer.ALLOWED,
        reason="교대 인수인계 합동 확인", api_method="POST",
    )
    return {"id": handover_id, "ack_id": entry.audit_id, "acknowledged": True}
