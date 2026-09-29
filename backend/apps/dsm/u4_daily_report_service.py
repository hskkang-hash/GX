# -*- coding: utf-8 -*-
"""DSM-U4-05 — 일일상황보고 자동 (턴 AP · WO-19 · 차선 N4).

명세 §4.4: 「일일상황보고 자동 — 기상특보·재난상황·통제 현황·피해 누계·대피·동원·
향후 계획 · 기준 시각 명기 · HWPX」 완결 조건 「매일 06:00 자동본」.

★ **새 질의를 짜지 않는다** — 이미 있는 공개 면을 그대로 합친다(DA-04):
    재난상황   `apps.dsm.services.recent_events`(오늘 발생분 · 등급별 집계 ·
               미종결 수)
    통제 현황  `apps.dsm.control_board_service.daily_reflection`(이미 「일일보고
               자동 반영」으로 지어졌다 — 턴 AN, DSM-U4-04 반쪽 채움)
    대피       위 통제 현황의 지점별 `evacuee_count`·`evacuation_site` 를 다시
               세지 않고 그대로 합산한다(같은 자료, 두 번째 집계를 안 만든다)

★ **기상특보는 짓지 않는다** — 기상청/산림청 특보 수신은 외부 기관 API 실연동
  이다(WO-19 「외부 실연동은 하지 않는다」→ evidence `excluded_by: P-428`).
★ **피해 누계·동원·향후 계획**은 이 저장소에 그 값을 쥔 구조화 표가 없다
  (별지 제1호서식은 사람이 그때그때 채우는 자유 입력칸이지 재조회 가능한 표가
  아니다 — `incident_report.py` 실측). 지어내지 않는다(D-280) — 열린 행으로
  정직하게 남긴다(P-419, 대리 지표를 만들지 않는다).
★ **HWPX 는 만들지 않는다** — 이미 있는 결정을 그대로 따른다
  (`situation_report_ledger_service.py` 머리말 「[턴 AN · P-392 · 결정 ⑤ 「안
  산다」] HWPX 는 채우지 않는다」와 같은 판단·같은 결정 번호). 이 함수의 JSON
  한 건이 「1쪽」의 구조화 표현이다 — 화면·프린트 서식은 이 JSON 을 그대로
  삼킬 수 있다.
"""
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.dsm import control_board_service


def _parse_when(as_of: str | None):
    if not as_of:
        return timezone.now()
    parsed = parse_datetime(as_of)
    if parsed is None:
        raise ValueError(f"시각을 읽을 수 없습니다: {as_of!r}")
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def daily_report(*, scope, as_of: str | None = None) -> dict:
    """`GET /daily-report` — 그 날(자정~`as_of`, 생략하면 지금)의 일일상황보고
    구조화본.

    Raises:
        ValueError: `as_of` 를 못 읽는다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from collections import Counter

    from apps.dsm import services

    when = _parse_when(as_of)
    local = timezone.localtime(when)
    day_start = local.replace(hour=0, minute=0, second=0, microsecond=0)

    today_events = services.recent_events(scope=scope, since=day_start, until=when,
                                          limit=500)
    by_severity = dict(Counter(e.severity for e in today_events))
    unresolved = [e.event_id for e in today_events if e.response_state != "closed"]

    control = control_board_service.daily_reflection(scope=scope, as_of=as_of)
    evacuee_total = 0
    evacuation_sites: list[str] = []
    for p in control.get("points", []):
        cnt = p.get("evacuee_count")
        if isinstance(cnt, (int, float)):
            evacuee_total += cnt
        site = p.get("evacuation_site")
        if site and site not in evacuation_sites:
            evacuation_sites.append(site)

    return {
        "as_of": when.isoformat(),
        "day": local.strftime("%Y-%m-%d"),
        "format": "json",  # HWPX 미채움 — P-392 결정 재사용
        "disaster_status": {
            "occurrence_count": len(today_events),
            "by_severity": by_severity,
            "unresolved_count": len(unresolved),
            "unresolved_event_ids": unresolved[:50],
        },
        "control_status": control,
        "evacuation": {
            "evacuee_count_total": evacuee_total,
            "evacuation_sites": evacuation_sites,
        },
        #: 아래 셋은 이 저장소에 구조화 원천이 없어 값을 지어내지 않는다(D-280).
        #: evidence title_parts 에 열린 행으로 정직하게 남긴다.
        "weather_advisory": None,
        "damage_cumulative": None,
        "mobilization": None,
        "future_plan": None,
    }
