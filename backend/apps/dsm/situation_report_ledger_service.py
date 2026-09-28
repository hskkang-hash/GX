# -*- coding: utf-8 -*-
"""DSM-U4-01 — **재난상황보고서(별지 제1호서식) 제N보 채번 대장** (`POST
/api/dsm/situation-reports` · `.../situation-reports/{id}/sent` ·
`GET .../situation-reports`) · 차선 N4 · 턴 AM.

이 파일이 여는 것 — **채번 대장 하나**, 서식은 안 건드린다
------------------------------------------------------------
`docs/design/GX-FORM_별지1호_v1.0.md` §4 는 이렇게 적어 두었다: 「**제N보 채번을
하지 않는다** — 채번은 「이 사건에 대해 우리가 몇 번째로 보고했는가」인데, 그 수를
담는 대장이 제품에 없다 … 채번 대장이 서는 날 이 서식에 **한 줄**로 붙는다.」

이 파일이 그 대장이다. **`api_u24.py::situation_report_docx`(N1 소유·이 턴
손대지 않는다)는 안 건드린다** — 서식(10칸 HTML→DOCX)은 그대로 두고, 「이 사건에
대해 몇 번째 보고인가·최초/중간/최종 어느 것인가·언제 발행됐고 언제 발송됐는가」
를 **별도 대장**으로 남긴다. 서식이 채번을 읽고 싶어지는 날 이 대장의 `latest()`
한 줄을 부르면 된다(위 문서가 예고한 「한 줄」).

★ **새 표를 만들지 않는다** — `alert_level_service.py`와 같은 판단(감사 한 줄 =
채번 한 걸음). 발행(issue)과 발송 기록(sent)을 감사 두 종류로 가른다 —
`cbs_draft_service` 의 초안/발송과 같은 결이다.

★ 「지체 없이」 — **분 단위 법정 기준을 찾지 못했다**(D-280, 지어내지 않는다).
그래서 빨강/초록 판정은 하지 않고 **경과 분(`elapsed_minutes`)만 계산해 낸다**
— 화면이 그 값으로 문턱을 그릴 수 있지만 그 문턱을 이 파일이 정하지 않는다.
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

from apps.dsm.u4_regulations import REPORT_KINDS

LOGGER_NAME = "guardianx.u4.situation_report_ledger"
TAG = "[U4-REPORT-LEDGER]"
SCAN_CAP = 1000


class SituationReportRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없다."""


class SituationReportConflict(Exception):
    """이미 발송 기록이 있다 — 409 로 번역된다."""


def _issue_action(group_id: int, event_id: int) -> str:
    return f"situation_report_issue:{group_id}:{event_id}"


def _sent_action(group_id: int, report_id: int) -> str:
    return f"situation_report_sent:{group_id}:{report_id}"


def _require_group(scope: TenantScope):
    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise SituationReportRejected(
            "소속 조직이 없어 상황보고서 채번을 저장할 수 없습니다.")
    return actor, group


def issue_report(*, scope: TenantScope, event_id: int, kind: str) -> dict[str, Any]:
    """`POST /situation-reports` — 이 사건의 제N보를 하나 채번하고 감사 한 줄을 남긴다.

    ★ 사건의 존재·소유는 `services.event_detail` 의 문지기를 **그대로 빌린다** —
      여기서 새로 세우지 않는다(D-212. 남의 사건에 채번하면 존재 자체가 샌다).

    Raises:
        ValueError: `kind` 가 「최초/중간/최종」 밖이다.
        django.http.Http404: 그런 사건이 없다 · 남의 테넌트 사건이다.
        SituationReportRejected: 소속 조직이 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    kind = (kind or "").strip()
    if kind not in REPORT_KINDS:
        raise ValueError(f"보고 구분은 {REPORT_KINDS} 중 하나다 — kind={kind!r}")

    from apps.dsm import services

    view = services.event_detail(scope=scope, event_id=event_id)  # 404 는 그대로 위로
    actor, group = _require_group(scope)

    prior = [e for e in audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
            if e.action == _issue_action(group.pk, event_id)]
    report_no = len(prior) + 1

    now = timezone.now()
    occurred_at = getattr(view, "occurred_at", None)
    elapsed_minutes = None
    if occurred_at is not None:
        elapsed_minutes = round((now - occurred_at).total_seconds() / 60.0, 1)

    stamp = timezone.localtime(now).strftime("%Y-%m-%d %H:%M")
    reason = (f"사건#{event_id} 제{report_no}보 · 구분={kind} · 발행={stamp}" +
             (f" · 최초사건시각대비경과={elapsed_minutes}분"
              if elapsed_minutes is not None else " · 사건 발생 시각 미기재"))
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_issue_action(group.pk, event_id), outcome=audit_writer.ALLOWED,
        reason=reason, api_method="POST",
    )
    return {"report_id": entry.audit_id, "event_id": event_id, "report_no": report_no,
            "kind": kind, "issued_at": now, "elapsed_minutes": elapsed_minutes,
            "actor_id": entry.actor_id}


def mark_sent(*, scope: TenantScope, report_id: int, recipient: str = "",
             sent_at: str | None = None) -> dict[str, Any]:
    """`POST /situation-reports/{id}/sent` — 이 보(報)를 실제로 보낸 시각·수신처를 남긴다.

    Raises:
        django.http.Http404: 그런 발행 기록이 없다 · 남의 테넌트다.
        SituationReportConflict: 이미 발송 기록이 있다.
        ValueError: `sent_at` 을 못 읽는다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.http import Http404

    actor, group = _require_group(scope)
    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    issued = next((e for e in entries
                  if e.audit_id == report_id
                  and e.action.startswith(f"situation_report_issue:{group.pk}:")), None)
    if issued is None:
        raise Http404("그런 상황보고서 채번 기록이 없습니다.")
    if any(e.action == _sent_action(group.pk, report_id) for e in entries):
        raise SituationReportConflict(f"제N보#{report_id}는 이미 발송 기록이 있습니다.")

    when = timezone.now()
    if sent_at:
        parsed = parse_datetime(sent_at)
        if parsed is None:
            raise ValueError(f"발송 시각을 읽을 수 없습니다: {sent_at!r}")
        when = timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
    stamp = timezone.localtime(when).strftime("%Y-%m-%d %H:%M")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_sent_action(group.pk, report_id), outcome=audit_writer.ALLOWED,
        reason=f"제N보#{report_id} 발송 — 수신처={recipient or '(미기재)'} · 시각={stamp}",
        api_method="POST",
    )
    return {"report_id": report_id, "sent_id": entry.audit_id, "sent_at": when,
            "recipient": recipient}


def list_reports(*, scope: TenantScope, event_id: int | None = None,
                 limit: int = 100) -> list[dict[str, Any]]:
    """`GET /situation-reports` — 채번 이력(최신 먼저). `event_id` 로 좁힐 수 있다.

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return []
    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    prefix = (f"situation_report_issue:{group.pk}:{event_id}" if event_id is not None
             else f"situation_report_issue:{group.pk}:")
    rows = [{"report_id": e.audit_id, "text": e.reason}
           for e in entries if e.action.startswith(prefix)]
    return rows[:limit]
