# -*- coding: utf-8 -*-
"""DSM-U4-09 — 통계 축 추가(지역안전지수 6분야) (턴 AP · WO-19 · 차선 N4).

명세 §4.4 DSM-U4-09: 「통계 축 추가 — 지역안전지수 6분야(화재·범죄·생활안전 …)에
맞춘 유형 분류 열」 · 서버 경로 `stats?by=safety_index` · 완결 조건 「분류 매핑 표」.

★ **새 질의를 짜지 않는다** — 이미 있는 `apps.dsm.stats.stats_axes()` 의
  `event_type` 축(그 자체가 `services.recent_events` → K1 커널을 그대로 부른
  결과)을 **다시 접을 뿐**이다(DA-04 「합계 = 목록 수」, `stats.py` 머리말과
  같은 판단). `stats.py`(공용 파일)는 고치지 않는다 — 이 파일이 그 결과를
  받아 재분류한다.
"""
from apps.dsm import stats as dsm_stats
from apps.dsm.u4_regulations import (EVENT_TYPE_SAFETY_INDEX, SAFETY_INDEX_FIELDS,
                                     SAFETY_INDEX_UNCLASSIFIED)


def safety_index_axis(*, scope, since=None, until=None, event_type=None,
                      severity=None) -> dict:
    """`stats_axes()` 의 `event_type` 축을 지역안전지수 6분야(+미분류)로 다시 접는다.

    Raises:
        apps.dsm.stats.StatsInputError: 기간이 계약(366일 상한 등)을 벗어났다
            (`stats_axes` 가 그대로 던진다 — 여기서 다시 검사하지 않는다).
    """
    base = dsm_stats.stats_axes(scope=scope, since=since, until=until,
                                event_type=event_type, severity=severity)
    counts: dict[str, int] = {f: 0 for f in SAFETY_INDEX_FIELDS}
    counts[SAFETY_INDEX_UNCLASSIFIED] = 0
    for row in base["axes"]["event_type"]:
        field = EVENT_TYPE_SAFETY_INDEX.get(row["key"], SAFETY_INDEX_UNCLASSIFIED)
        counts[field] += row["count"]
    order = (*SAFETY_INDEX_FIELDS, SAFETY_INDEX_UNCLASSIFIED)
    rows = [{"key": f, "label": f, "count": counts[f]} for f in order]
    return {
        "since": base["since"], "until": base["until"], "total": base["total"],
        "by": "safety_index",
        "safety_index": rows,
        #: 완결 조건이 부르는 「분류 매핑 표」 — event_type → 분야, 그대로 낸다
        #: (숨기지 않는다 · 화면이 이 표를 그대로 보여줄 수 있다).
        "mapping": dict(EVENT_TYPE_SAFETY_INDEX),
        "fields": list(SAFETY_INDEX_FIELDS),
        "capped": base["capped"],
    }
