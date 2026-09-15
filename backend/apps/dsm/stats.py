# -*- coding: utf-8 -*-
"""U24 통계 집계 — UX-39(통계 요약) · UX-35(요원별) · UX-36(오탐률).

이 파일이 하는 일과 안 하는 일 (`apps/dsm/services.py` 머리말과 같은 규약)
--------------------------------------------------------------------------
    한다   기존 공개 면(`services.recent_events` · `kernels.k6_feedback.false_positive_rate`)
           을 부른다 · 그 결과를 화면이 쓸 모양(집계 dict)으로 접는다 · 60초 캐시
    안 한다 ORM 을 직접 만지지 않는다 · 오탐률 나눗셈을 다시 하지 않는다(K6 이 한다) ·
           테넌트 좁히기를 다시 하지 않는다(`filter_by_group_field` 는 이미 K1·K6 안에 있다)

왜 배치 테이블이 없나 (WO-01 §5 성능 · 가정)
---------------------------------------------
지시서 §5: *"집계 `stats`·`by-reviewer`·`false-positive`는 야간 배치 테이블 + 캐시 60초."*
이번 턴 스키마 변경은 F-DB 의 신규 테이블 일곱(`dsm_handover` 등)뿐이고 이 셋은 그 안에
없다 — 그래서 **배치 테이블은 만들지 않는다.** 대신 요청 시 집계 + 캐시 60초로 좁힌다
(가정 · 조율자 검토 필요). p95 800ms 를 해치는 전 기간 무제한 스캔은 `_resolve_window`
가 기간 상한(366일)으로 막는다 — 배치 테이블이 없는 대신 **집계 자체를 좁힌다.**

집계는 왜 새 질의를 짜지 않고 `services.recent_events` 를 다시 부르나
-----------------------------------------------------------------------
AC-5(§3) *"합계 = 목록 수"* 는 `/api/dsm/events` 목록과 이 집계가 **같은 필터·같은
질의**를 타야 자동으로 성립한다. 집계용 질의를 따로 짜면 두 경로가 갈리고, 갈린 숫자는
감사 앞에서 못 쓴다(DA-04 K6 표와 같은 이유) — 그래서 이 파일은 새 질의를 만들지 않고
목록이 이미 쓰는 그 함수를 그대로 불러 Python 에서 접는다.

캐시 — 기존 사용 방식과 같은 모양 (`common/session_limit.py::SessionRegistry`)
--------------------------------------------------------------------------------
그 파일의 캐시 한 칸은 `"gx:ux24:sessions:%s" % user_id` 키에 JSON 문자열 하나였다.
여기도 같은 모양을 쓴다: 이름공간 있는 문자열 키 + `json.dumps`/`json.loads` + TTL 초.
**키에 테넌트를 반드시 넣는다** — 넣지 않으면 캐시 자체가 격리를 뚫는 자리가 된다.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone

from common.tenant_filters import get_user_group
from common.tenant_roles import is_global_admin
from common.tenant_scope import TenantScope

from apps.dsm import services
from apps.dsm.exceptions import DsmError


class StatsInputError(DsmError):
    """통계 질의의 기간이 계약을 벗어났다. `api_u24.py` 가 HTTP 400 으로 번역한다."""


# ═══════════════════════════════════════════════════════════════════════════
# 기간 — 세 라우트가 같은 말을 쓴다 (기존 `/events` since·until 재사용 · task 지시)
# ═══════════════════════════════════════════════════════════════════════════
#: 기간을 안 주면 이만큼 본다. `kernels.k6_feedback.false_positive_rate` 의 기본값(30일)과
#: 맞춘다 — 세 라우트가 다른 기본 창을 쓰면 같은 순간의 「기간」이 다른 뜻이 된다.
_DEFAULT_WINDOW = timedelta(days=30)

#: p95 800ms 상한을 지키는 자리. 배치 테이블이 없으므로 **여기서만** 막는다(위 머리말).
_MAX_WINDOW = timedelta(days=366)

#: 한 번의 집계가 훑는 행 상한. `apps/dsm/api.py::_UNHANDLED_CAP`(500)과 같은 발상 —
#: 상한 없이 세면 이벤트가 쌓인 테넌트에서 이 라우트가 목록보다 무거워진다.
_ROW_CAP = 2000


def _floor_to_ttl(when: datetime) -> datetime:
    """`when` 을 캐시 TTL(60초) 경계로 내림한다.

    ★ 왜 내림하나 — `until` 을 안 주는 호출(「지금까지」)마다 `timezone.now()` 를 그대로
      쓰면 **매 요청이 마이크로초 단위로 다른 값**을 갖고, 그러면 캐시 키(아래)가 매번
      달라져 60초 캐시가 사실상 죽는다(실측 — 첫 구현이 그렇게 죽었다). 60초 칸으로
      내림하면 같은 칸 안의 재호출이 같은 키를 타 실제로 캐시가 걸린다.
      **호출자가 `until` 을 명시하면 내림하지 않는다** — 명시한 값은 정확해야 한다
      (예: 보고서가 「그 시각까지」를 인용하는 자리).
    """
    epoch = int(when.timestamp())
    floored = epoch - (epoch % _CACHE_TTL_SECONDS)
    return datetime.fromtimestamp(floored, tz=when.tzinfo)


def _resolve_window(since: datetime | None, until: datetime | None) -> tuple[datetime, datetime]:
    until_given = until is not None
    until = until or timezone.now()
    if not until_given:
        until = _floor_to_ttl(until)
    since = since or (until - _DEFAULT_WINDOW)
    if since > until:
        raise StatsInputError(f"기간이 뒤집혔다 — since={since} > until={until}")
    if until - since > _MAX_WINDOW:
        raise StatsInputError(
            f"기간이 {_MAX_WINDOW.days}일을 넘습니다(since={since} · until={until}) — "
            f"배치 테이블 없이 이 기간을 통째로 훑으면 p95 800ms 를 해칩니다(WO-01 §5). "
            f"기간을 좁혀 주세요.")
    return since, until


# ═══════════════════════════════════════════════════════════════════════════
# 캐시 — 60초 · 키에 테넌트 + 파라미터 (WO-01 §5 · session_limit.py 와 같은 모양)
# ═══════════════════════════════════════════════════════════════════════════
_CACHE_PREFIX = "gx:dsm:u24:stats"
_CACHE_TTL_SECONDS = 60


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"직렬화할 수 없는 값: {value!r}")


def _tenant_cache_id(actor) -> str:
    """캐시 키의 테넌트 성분. **다른 테넌트가 같은 값을 내면 안 된다** — 틀리면 캐시가

    격리를 뚫는 자리가 된다. 전역 관리자는 필터를 안 타므로(`filter_by_group_field`)
    전역 집계를 공유해도 안전하다 — 그 자체가 이미 전 테넌트 집계이기 때문이다.
    """
    if is_global_admin(actor):
        return "admin"
    group = get_user_group(actor)
    if group is not None:
        return f"g{group.pk}"
    # group 없는 사용자 — 계정별로 가른다(공유하면 서로 다른 groupless 사용자가
    # 우연히 같은 키를 나눠 쓰게 된다. 실제로는 빈 결과만 나오지만 근거로 기대지 않는다).
    return f"u{getattr(actor, 'pk', 'anon')}"


def _cache_key(name: str, actor, **params) -> str:
    tenant = _tenant_cache_id(actor)
    raw = json.dumps(params, sort_keys=True, default=_json_default)
    #: sha256 앞 12자 — 이 저장소가 자격·핑거프린트를 대조할 때 쓰는 것과 같은 길이.
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{_CACHE_PREFIX}:{name}:{tenant}:{digest}"


def _cache_get(key: str) -> dict | None:
    raw = cache.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _cache_set(key: str, payload: dict) -> None:
    try:
        raw = json.dumps(payload, default=_json_default)
    except TypeError:
        return
    cache.set(key, raw, _CACHE_TTL_SECONDS)


# ═══════════════════════════════════════════════════════════════════════════
# 1. stats_summary — UX-39 통계 요약 (파 1 부분집합)
# ═══════════════════════════════════════════════════════════════════════════
def stats_summary(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
    event_type: str | list[str] | None = None,
    severity: str | list[str] | None = None,
) -> dict:
    """기간 내 건수 · 유형별 · 등급별 · 판정상태별 · 대응진행별 집계.

    ★ **부분집합이다.** 정본 UX-39 는 구역별·시간대별(24칸)·카메라 가동률·
      대응 p50/p95·CSV 까지 요구하지만, 이번 턴 소유 파일(`stats.py` 신설)만으로는
      구역(Zone)·카메라 가동률 커널이 없어 만들 수 없다 — 있는 커널(`recent_events`)
      로 낼 수 있는 축만 낸다. 나머지는 가정 목록·등록 요청에 남긴다.
    """
    actor = scope.require_actor()
    since, until = _resolve_window(since, until)

    key = _cache_key("summary", actor, since=since, until=until,
                     event_type=event_type, severity=severity)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    rows = services.recent_events(scope=scope, since=since, until=until,
                                  event_type=event_type, severity=severity,
                                  limit=_ROW_CAP + 1)
    capped = len(rows) > _ROW_CAP
    rows = rows[:_ROW_CAP]

    payload = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "total": len(rows),
        "by_event_type": dict(Counter(e.event_type for e in rows)),
        "by_severity": dict(Counter(e.severity for e in rows)),
        "by_status": dict(Counter(e.status for e in rows)),
        "by_response_state": dict(Counter(e.response_state for e in rows)),
        #: 상한에 닿았다는 사실은 응답이 말한다(`api.py::_UNHANDLED_CAP` 과 같은 계약).
        "capped": capped,
        "row_cap": _ROW_CAP,
    }
    _cache_set(key, payload)
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# 2. stats_by_reviewer — UX-35 요원별 처리 현황
# ═══════════════════════════════════════════════════════════════════════════
def stats_by_reviewer(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict:
    """요원(판정자)별 접수(판정 건수)·종결·평균 대응 시간·오탐 판정 수.

    ★ 모델 필드만 쓴다(task 지시) — `verdict`·`reviewed_by`·`reviewed_at`·`status`·
      `occurred_at`. 대응 진행(`response_state`)의 전이 행위자는 행이 아니라 감사
      (`logger.AuditLogs`)에만 있다(D-399 머리말) — 그래서 「접수」는 대응 진행의
      acknowledged 건수가 아니라 **이 요원이 판정한 건수**로 잡는다. 이 해석을
      가정 목록에 남긴다.

    ★ 「평균 대응 시간」은 `reviewed_at - occurred_at`(발생 → 판정)의 평균이다.
      대응 진행의 각 단계 시각이 행에 없으므로 이 두 점만으로 잰다 — 마찬가지로
      가정 목록에 남긴다.
    """
    actor = scope.require_actor()
    since, until = _resolve_window(since, until)

    key = _cache_key("by_reviewer", actor, since=since, until=until)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    rows = services.recent_events(scope=scope, since=since, until=until,
                                  limit=_ROW_CAP + 1)
    capped = len(rows) > _ROW_CAP
    rows = rows[:_ROW_CAP]

    buckets: dict[int, dict[str, float]] = {}
    for e in rows:
        if e.reviewed_by_id is None:
            continue  # 미판정은 「요원별」의 분모 밖이다 — K6 의 분모 규약과 같은 결이다.
        b = buckets.setdefault(e.reviewed_by_id, {
            "reviewed_total": 0, "closed_total": 0, "false_positive_total": 0,
            "_resp_sum": 0.0, "_resp_n": 0,
        })
        b["reviewed_total"] += 1
        if e.status == "closed":
            b["closed_total"] += 1
        if e.verdict == "rejected":
            b["false_positive_total"] += 1
        if e.reviewed_at is not None:
            b["_resp_sum"] += (e.reviewed_at - e.occurred_at).total_seconds()
            b["_resp_n"] += 1

    reviewers = []
    for reviewer_id in sorted(buckets):
        b = buckets[reviewer_id]
        avg = (b["_resp_sum"] / b["_resp_n"]) if b["_resp_n"] else None
        reviewers.append({
            "reviewer_id": reviewer_id,
            "reviewed_total": int(b["reviewed_total"]),
            "closed_total": int(b["closed_total"]),
            "false_positive_total": int(b["false_positive_total"]),
            #: 분모 0(판정은 있었지만 reviewed_at 이 비어 있던 옛 행)이면 **null** —
            #: 0.0 으로 내면 「잰 적 없다」와 「0초 만에 처리했다」가 같은 값이 된다(D-290).
            "avg_response_seconds": avg,
        })

    payload = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "reviewers": reviewers,
        "total_reviewed": sum(r["reviewed_total"] for r in reviewers),
        "capped": capped,
        "row_cap": _ROW_CAP,
    }
    _cache_set(key, payload)
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# 3. stats_false_positive — UX-36 오탐률 (K6 을 그대로 소비 · 다시 세지 않는다)
# ═══════════════════════════════════════════════════════════════════════════
def stats_false_positive(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
    event_type: str | list[str] | None = None,
    severity: str | list[str] | None = None,
) -> dict:
    """기간의 오탐률. 나눗셈은 여기서 하지 않는다 — `kernels.k6_feedback.false_positive_rate`
    가 이미 DA-04 K6 표가 정한 그 하나의 집계 경로다(F-14·U1·U4 가 같이 보는 수).
    """
    actor = scope.require_actor()
    since, until = _resolve_window(since, until)

    key = _cache_key("false_positive", actor, since=since, until=until,
                     event_type=event_type, severity=severity)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    from kernels.k6_feedback import false_positive_rate

    rate = false_positive_rate(scope=scope, since=since, until=until,
                               event_type=event_type, severity=severity)
    w = rate.total

    payload = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "false_positive": w.rejected,
        "reviewed": w.reviewed,
        "unreviewed": w.unreviewed,
        "closed_without_verdict": w.closed_without_verdict,
        #: 분모 0 이면 **null** — 0.0 이 아니다(RateWindow.rate 의 계약 그대로).
        "false_positive_rate": w.rate,
        "measurable": rate.is_measurable,
    }
    _cache_set(key, payload)
    return payload
