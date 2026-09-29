# -*- coding: utf-8 -*-
"""DSM-U4-02 — 중간 보고 사이클 (턴 AP · WO-19 · 차선 N4).

명세 §4.4 DSM-U4-02: 「중간 보고 사이클 — 08시·17시 기준 응급조치 보고 자동
초안(1일 2회) · NDMS 입력용 표 내보내기(항목 1:1)」 · 완결 조건 「1일 2회
초안 · 내보내기 1」.

★ **새 판정 문을 만들지 않는다**(P-357) — 「중간」 보(報) 채번 자체는 이미
  `situation_report_ledger_service.issue_report(kind="중간")`(턴 AM)이 한다.
  이 파일이 더하는 것은 둘뿐이다:

    1. **배치**(`issue_interim_batch`) — 08시/17시 두 기준 시각 중 어느 슬롯인지
       가려(`_slot_for`) 그 순간 「열려 있는」(미종결) 사건 전부에 중간 보고를
       한 번에 채번한다. 실제 cron 은 이 저장소에 없다 — `control_board_service
       .daily_reflection` 과 같은 판단(운영자가 그 시각에 이 문을 부르면 배치가
       선다). 같은 슬롯·같은 날 **중복 채번을 막는다**(자체 감사 마커).
    2. **NDMS CSV 내보내기**(`export_ndms_csv`) — 이미 채번된 상황보고를
       항목 1:1 로 편다. 새 질의를 짜지 않는다 — 발행 시 함께 남긴 구조화 칸
       (`issue_report` 의 `after=`)을 그대로 읽는다(값을 두 번 만들지 않는다).

★ 새 표를 만들지 않는다 — 배치 중복 방지 마커도 `audit_writer` 한 줄이다.
"""
import codecs
import csv
import io

from django.apps import apps as django_apps
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

from apps.dsm import situation_report_ledger_service as report_ledger
from apps.dsm.u4_regulations import REPORT_KIND_INTERIM

LOGGER_NAME = "guardianx.u4.interim_report_batch"
TAG = "[U4-INTERIM-BATCH]"
SCAN_CAP = 2000

#: 08시·17시 두 기준 — 명세서 §4.4 DSM-U4-02 「08시·17시 기준」 그대로(D-280).
SLOT_MORNING = "08:00"
SLOT_EVENING = "17:00"
#: 정오를 경계로 가른다 — 08시 슬롯은 자정~정오, 17시 슬롯은 정오~자정에 부른
#: 호출을 받는다(그 사이 아무 때나 불러도 「가장 가까운 지난 기준」으로 읽는다).
_SLOT_CUTOVER_HOUR = 12

#: 채번 대상 — 명세서가 「응급조치 보고」라 부르는 **아직 안 끝난** 사건.
#: 커널이 「미종결 아님」한 값을 바로 안 받으므로(D-399 대응 축은 상태 하나씩만
#: 받는다) 세 상태를 모두 물어 합친다 — `focus_queue` 가 여러 상태를 합치는
#: 것과 같은 판단.
_OPEN_STATES = ("occurred", "acknowledged", "in_progress")
_OPEN_STATE_SCAN_LIMIT = 200


def _model():
    return django_apps.get_model("logger", "AuditLogs")


def _slot_for(when) -> str:
    local = timezone.localtime(when)
    return SLOT_MORNING if local.hour < _SLOT_CUTOVER_HOUR else SLOT_EVENING


def _parse_when(as_of: str | None):
    if not as_of:
        return timezone.now()
    parsed = parse_datetime(as_of)
    if parsed is None:
        raise ValueError(f"시각을 읽을 수 없습니다: {as_of!r}")
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _batch_marker_action(group_id: int, event_id: int, slot: str, date_str: str) -> str:
    return f"interim_batch:{group_id}:{event_id}:{date_str}:{slot}"


def issue_interim_batch(*, scope: TenantScope, as_of: str | None = None) -> dict:
    """이 순간의 슬롯(08:00/17:00)에 맞춰 **아직 안 끝난 사건 전부**에 중간
    보고를 한 번에 채번한다. 같은 슬롯·같은 날 이미 채번된 사건은 건너뛴다
    (재호출해도 배치가 두 벌로 쌓이지 않는다).

    Raises:
        ValueError: `as_of` 를 못 읽는다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from apps.dsm import services

    actor = scope.require_actor()
    group = get_user_group(actor)
    when = _parse_when(as_of)
    slot = _slot_for(when)
    date_str = timezone.localtime(when).strftime("%Y-%m-%d")
    if group is None:
        return {"slot": slot, "date": date_str, "issued": [], "skipped": [],
               "issued_count": 0, "skipped_count": 0}

    markers = {e.action for e in audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)}

    seen_ids: set[int] = set()
    issued: list[dict] = []
    skipped: list[int] = []
    for state in _OPEN_STATES:
        for ev in services.recent_events(scope=scope, response_state=state,
                                         limit=_OPEN_STATE_SCAN_LIMIT):
            if ev.event_id in seen_ids:
                continue
            seen_ids.add(ev.event_id)
            marker = _batch_marker_action(group.pk, ev.event_id, slot, date_str)
            if marker in markers:
                skipped.append(ev.event_id)
                continue
            report = report_ledger.issue_report(
                scope=scope, event_id=ev.event_id, kind=REPORT_KIND_INTERIM)
            audit_writer.write(
                logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=marker,
                outcome=audit_writer.ALLOWED,
                reason=f"{slot} 중간 보고 배치 · 사건#{ev.event_id} · "
                      f"report_id={report['report_id']}",
                api_method="POST")
            issued.append({"event_id": ev.event_id, "report_id": report["report_id"]})

    return {"slot": slot, "date": date_str, "issued": issued, "skipped": skipped,
           "issued_count": len(issued), "skipped_count": len(skipped)}


#: NDMS 입력용 표 머리 — 「항목 1:1」(명세 완결 조건)이 부르는 칸. `event_type`·
#: `severity`·`address`·`occurred_at` 은 K1 이벤트가 이미 갖고 있는 값을
#: 그대로 옮긴다(지어내지 않는다 · D-280).
NDMS_HEADER = ("report_id", "event_id", "report_no", "kind", "issued_at",
              "elapsed_minutes", "event_type", "severity", "address", "occurred_at")
CSV_BOM = codecs.BOM_UTF8.decode("utf-8")


def export_ndms_csv(*, scope: TenantScope) -> str:
    """`GET /situation-reports/ndms-export.csv` — 이미 채번된 상황보고 전건을
    NDMS 입력용 표(항목 1:1)로 편다. 새 질의를 짜지 않는다 — 발행 때 함께
    남긴 구조화 칸(`issue_report` 의 `after=`)을 그대로 읽는다.

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.http import Http404

    from apps.dsm import services

    actor = scope.require_actor()
    group = get_user_group(actor)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(NDMS_HEADER)
    if group is not None:
        prefix = f"situation_report_issue:{group.pk}:"
        rows = (
            _model()._base_manager
            .filter(logger_name=report_ledger.LOGGER_NAME, api_name__startswith=prefix)
            .order_by("-id")[:report_ledger.SCAN_CAP]
        )
        for r in rows:
            payload = r.data_after if isinstance(r.data_after, dict) else {}
            event_id = payload.get("event_id")
            event_type = severity = address = occurred_at = ""
            if event_id is not None:
                try:
                    ev = services.event_detail(scope=scope, event_id=event_id)
                except Http404:
                    ev = None
                if ev is not None:
                    event_type = ev.event_type or ""
                    severity = ev.severity or ""
                    address = getattr(ev, "address", None) or ""
                    occurred_at = ev.occurred_at.isoformat() if ev.occurred_at else ""
            writer.writerow((
                r.pk, event_id, payload.get("report_no", ""), payload.get("kind", ""),
                payload.get("issued_at", ""), payload.get("elapsed_minutes", ""),
                event_type, severity, address, occurred_at))
    return CSV_BOM + buf.getvalue()
