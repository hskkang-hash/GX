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

import codecs
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


# ═══════════════════════════════════════════════════════════════════════════
# 4. false_positive_by_camera — UX-36 「어느 카메라가 시끄러운가」
#    (부속서A 업무플로우 U2 #10 · BF-3 3단계)
# ═══════════════════════════════════════════════════════════════════════════
#: 한 번에 훑는 카메라 수 상한. `_ROW_CAP` 과 같은 발상 — 카메라가 많은 테넌트에서
#: 이 집계가 카메라마다 K6 을 한 번씩 부르므로, 상한이 없으면 목록보다 무거워진다.
#: 닿았다는 사실은 응답이 말한다(`camera_capped`) — 조용히 자르지 않는다.
_CAMERA_CAP = 50


def _window_from_days(days: int | None, since: datetime | None,
                      until: datetime | None) -> tuple[datetime, datetime]:
    """`days=7`(정본이 부르는 모양)을 두 끝으로 편다.

    ★ 두 끝을 **둘 다** 정해서 내려보낸다. 여는 쪽만 정하면 창이 아니라 반직선이
      되고, 그러면 「지난 7일」이 「7일 전부터 미래까지」가 된다(`EventList.tsx::windowOf`
      머리말과 같은 규약).
    """
    if days is not None:
        if days <= 0:
            raise StatsInputError(f"days 는 1 이상이다 — days={days}")
        until = _floor_to_ttl(until or timezone.now()) if until is None else until
        since = until - timedelta(days=days)
    return _resolve_window(since, until)


def false_positive_by_camera(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
    days: int | None = None,
    top_n: int = 3,
) -> dict:
    """카메라별 오탐률 — **내림차순 · 상위 N 강조** (부속서A U2 #10 완결 조건).

    ★ **나눗셈을 여기서 하지 않는다.** 카메라마다
      `kernels.k6_feedback.false_positive_rate(stream_monitor_id=...)` 를 부르고
      그 결과를 그대로 옮긴다 — K6 이 이미 `stream_monitor_id` 를 받는다(실측).
      여기서 다시 세면 같은 수를 내는 집계 경로가 둘이 되고, 갈린 수는 고객
      앞에서 못 쓴다(DA-04 K6 표 · `stats_false_positive` 와 같은 사유).

    ★ 분모 0(판정 0건)인 카메라는 `false_positive_rate: null` 이고 **0.0 이 아니다.**
      그런 카메라는 정렬에서 **맨 뒤**로 간다 — 「한 번도 판정 안 한 카메라」가
      「오탐이 0인 카메라」보다 조용해 보이면 안 된다(D-290).

    ★ 상위 N 은 **잴 수 있는 행에만** 매긴다. 못 재는 행에 순위를 주면 그 순위는
      판정을 안 했다는 사실을 상으로 바꾼다.
    """
    actor = scope.require_actor()
    since, until = _window_from_days(days, since, until)
    if top_n < 0:
        raise StatsInputError(f"top_n 은 0 이상이다 — top_n={top_n}")

    key = _cache_key("fp_by_camera", actor, since=since, until=until, top_n=top_n)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    rows = services.recent_events(scope=scope, since=since, until=until,
                                  limit=_ROW_CAP + 1)
    capped = len(rows) > _ROW_CAP
    rows = rows[:_ROW_CAP]

    #: 이 창에 **실제로 사건을 낸** 카메라만 센다. 카메라 표를 따로 훑지 않는 이유:
    #: 사건이 한 건도 없는 카메라는 「조용한가」를 물을 표본이 없다 — 그 카메라를
    #: 오탐률 0% 로 적으면 꺼져 있는 카메라가 가장 좋은 카메라가 된다.
    names: dict[int, str] = {}
    order: list[int] = []
    for e in rows:
        cid = e.stream_monitor_id
        if cid is None:
            continue
        if cid not in names:
            names[cid] = e.stream_monitor_name or ""
            order.append(cid)
    camera_total = len(order)
    camera_capped = camera_total > _CAMERA_CAP
    order = order[:_CAMERA_CAP]

    from kernels.k6_feedback import false_positive_rate

    cameras = []
    for cid in order:
        rate = false_positive_rate(scope=scope, since=since, until=until,
                                   stream_monitor_id=cid)
        w = rate.total
        cameras.append({
            "stream_monitor_id": cid,
            "stream_monitor_name": names[cid],
            #: 비율만 내지 않는다 — 분자·분모를 함께 낸다(D-271 ③ · D-301).
            "false_positive": w.rejected,
            "reviewed": w.reviewed,
            "unreviewed": w.unreviewed,
            "false_positive_rate": w.rate,        # 분모 0 이면 **null**
            "measurable": rate.is_measurable,
        })

    #: 못 재는 행은 맨 뒤 · 같은 비율이면 **분모가 큰 쪽**이 위다(판정 3건 중 2건보다
    #: 판정 100건 중 66건이 더 단단한 수다).
    cameras.sort(key=lambda r: (
        r["false_positive_rate"] is None,
        -(r["false_positive_rate"] or 0.0),
        -r["reviewed"],
        r["stream_monitor_id"],
    ))

    ranked = 0
    for r in cameras:
        r["top"] = bool(r["measurable"] and ranked < top_n)
        if r["top"]:
            ranked += 1

    payload = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "cameras": cameras,
        "camera_total": camera_total,
        "top_n": top_n,
        "capped": capped,
        "row_cap": _ROW_CAP,
        "camera_capped": camera_capped,
        "camera_cap": _CAMERA_CAP,
    }
    _cache_set(key, payload)
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# 5. simulate_threshold — UX-36 「슬라이더 → 시간당 N건」 (부속서A U2 #11 · BF-3 4단계)
# ═══════════════════════════════════════════════════════════════════════════
#: 정본 BF-3 4단계가 이름으로 적은 문턱 — 「6건 초과 주황」. 화면이 자기 문턱을
#: 들지 않도록 **서버가 낸다**(`FocusQueue` 의 `tier_thresholds_sec` 와 같은 규약).
_NOISY_PER_HOUR = 6.0


def simulate_threshold(
    *,
    scope: TenantScope,
    camera_id: int,
    confidence_min: float,
    days: int = 7,
) -> dict:
    """「이 문턱이면 최근 N일 기준 **시간당 몇 건**이 남나」 — 아무것도 바꾸지 않는다.

    ★ **쓰지 않는다.** 이 함수는 저장도 판정도 하지 않고 셈만 한다 — 누르는 것과
      바뀌는 것을 가른다. 실제 변경은 `POST /api/dsm/settings/thresholds`(F-12 의
      유일한 임계값 문)가 하고, 그 문은 **사유가 비면 400** 이다.

    ★ 확신도가 **비어 있는 사건은 「남는다」고 세지 않는다.** `confidence` 가 `null`
      인 행은 어떤 문턱으로도 가를 수 없다 — 그 수를 `unknown_confidence` 로 따로
      내고, 가를 수 있는 행이 하나도 없으면 `measurable: false` 다. 0 건으로 내면
      「문턱을 올렸더니 알림이 사라졌다」는 거짓 안심이 된다(D-290).

    ★ 남의 카메라 id 를 넣어도 새는 것이 없다: 세는 표본은 `recent_events` 가 이미
      요청자의 테넌트로 좁힌 사건뿐이다. 남의 카메라 id 는 **0 건**으로 떨어지고,
      이 응답에는 카메라 이름이 없다(존재 여부가 새지 않는다 · D-269).
    """
    scope.require_actor()
    if not isinstance(confidence_min, (int, float)):
        raise StatsInputError("확신도 문턱이 숫자가 아니다")
    if not (0.0 <= float(confidence_min) <= 1.0):
        raise StatsInputError(
            f"확신도 문턱은 0.0 과 1.0 사이다 — confidence_min={confidence_min}. "
            f"모델이 내는 확신도가 그 범위이기 때문이다")
    if days <= 0 or days > _MAX_WINDOW.days:
        raise StatsInputError(
            f"days 는 1 과 {_MAX_WINDOW.days} 사이다 — days={days}")

    confidence_min = float(confidence_min)
    until = _floor_to_ttl(timezone.now())
    since = until - timedelta(days=days)

    #: ⚠ **캐시를 타지 않는다.** 슬라이더를 움직인 결과가 60초 전 값이면 사람은
    #:   자기가 방금 고른 문턱의 수를 보고 있다고 믿으면서 다른 수를 본다
    #:   (P-19 「응답 캐시가 장애를 덮는다」의 같은 결).
    rows = services.recent_events(scope=scope, since=since, until=until,
                                  limit=_ROW_CAP + 1)
    sample_capped = len(rows) > _ROW_CAP
    rows = rows[:_ROW_CAP]

    #: 카메라로 좁히는 일을 **커널이 못 해 준다** — `query_events` 에 카메라 인자가
    #: 없다(실측). 그래서 여기서 접는다(`stats_by_reviewer` 가 요원으로 접는 것과
    #: 같은 자리). ⚠ 표본 상한에 닿으면 그 카메라의 옛 사건이 이 셈 밖으로 나가므로
    #: `sample_capped` 를 응답에 싣는다 — 화면이 그 사실을 적는다.
    mine = [e for e in rows if e.stream_monitor_id == camera_id]
    graded = [e for e in mine if e.confidence is not None]
    kept = [e for e in graded if float(e.confidence) >= confidence_min]

    hours = (until - since).total_seconds() / 3600.0
    measurable = bool(graded) and hours > 0
    return {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "days": days,
        "camera_id": camera_id,
        "confidence_min": confidence_min,
        #: 분모들. 「시간당 N건」만 내면 그것이 몇 건 중 몇인지 아무도 모른다.
        "events_total": len(mine),
        "graded_total": len(graded),
        "unknown_confidence": len(mine) - len(graded),
        "kept": len(kept),
        "dropped": len(graded) - len(kept),
        "window_hours": hours,
        #: 이 문턱이면 시간당 몇 건 — 가를 수 있는 행이 0 이면 **null**(0.0 이 아니다).
        "events_per_hour": (len(kept) / hours) if measurable else None,
        #: 지금은 시간당 몇 건. 「바꾸면 얼마나 줄어드나」는 두 수가 함께 있어야 뜻이 있다.
        "current_per_hour": (len(mine) / hours) if hours > 0 else None,
        "measurable": measurable,
        #: 문턱은 서버가 낸다 — 화면이 6 을 들고 있으면 두 곳이 갈린다.
        "noisy_per_hour": _NOISY_PER_HOUR,
        "noisy": bool(measurable and (len(kept) / hours) > _NOISY_PER_HOUR),
        "sample_capped": sample_capped,
        "row_cap": _ROW_CAP,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 6. 임계값 — **되돌려 읽는 자리** (부속서A U2 #11 「저장(사유) → 재조회」)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ **쓰는 문을 새로 만들지 않는다.** F-12 의 임계값 쓰기는
#   `POST /api/dsm/settings/thresholds` 하나이고(사유 필수 · 계약 고정값은 409 ·
#   무권한 403 + 감사 번호), 그 문은 이미 서 있다. 같은 일을 하는 문을 하나 더 열면
#   문지기가 두 벌이 되고 두 벌은 반드시 어긋난다(D-212).
#   여기 있는 것은 **읽는 쪽**뿐이다 — 저장한 값이 정말 그 카메라에 붙었는지를
#   사람이 화면에서 확인하는 자리.


def camera_threshold_keys(*, scope: TenantScope) -> dict:
    """이 화면이 **카메라별로 고칠 수 있는 임계값**의 목록. 값은 내지 않는다.

    ★ 화면이 키를 손으로 들지 않게 하는 것이 이 함수의 전부다. 키 이름을 화면에
      박아 두면 표 ①(`kernels/k5_trust/thresholds.py`)이 늘거나 줄 때 화면만
      옛말이 되고, 옛말이 된 것은 안 보인다(D-286).

    ★ 계약이 못박은 값(`contract_fixed`)은 **목록에서 뺀다** — 슬라이더로 옮길 수
      있는 것처럼 그려 놓고 저장에서 409 를 내면 그 화면이 거짓말을 한 것이다.
    """
    from kernels.k5_trust import list_thresholds

    keys = [
        {
            "key": r["key"],
            "title": r["title"],
            "unit": r["unit"],
            "default": r["default"],
            "applies_to": r["applies_to"],
        }
        for r in list_thresholds(scope=scope)
        if r["applies_to"] == "camera" and not r["contract_fixed"]
    ]
    return {"keys": keys, "total": len(keys)}


def camera_threshold(*, scope: TenantScope, camera_id: int, key: str) -> dict:
    """그 카메라에 **지금 유효한** 임계값. 「저장 → 재조회」의 재조회가 이것이다.

    ★ 좁은 것이 이긴다(camera → tenant → global → 정의) — 그 판정은 커널
      (`resolve_threshold`)이 한다. 여기서 다시 하지 않는다.

    ★ 값이 없으면 **`null` 이고 0 이 아니다.** 0 으로 내면 「기준선이 0」으로 읽히고,
      그러면 모든 신호가 초과가 된다(표 ① 머리말이 이름으로 막은 자리).

    ★ 문지기는 커널 안에 있다 — `resolve_threshold` 가 남의 카메라 pk 에
      `assert_scoped` 를 건다(W0-14c). 여기서 다시 세우지 않는다.
    """
    from kernels.k5_trust import ThresholdNotSet, resolve_threshold

    try:
        value = resolve_threshold(key, scope=scope, camera_id=camera_id)
    except ThresholdNotSet:
        return {"key": key, "camera_id": camera_id, "value": None, "set": False}
    return {"key": key, "camera_id": camera_id, "value": value, "set": True}


# ═══════════════════════════════════════════════════════════════════════════
# 7. stats_axes — UX-39 통계 화면의 **축 5** + CSV (턴 T · P-164 U24 ①)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 축 이름은 **실측**이다 — `EventView`(kernels/k1_event/schemas.py) 에 있는 칸만 축이
#   된다: 카메라(`stream_monitor_id/name`) · 유형(`event_type`) · 심각도(`severity`) ·
#   판정(`verdict` — 미판정은 `unreviewed` 로 따로 센다) · 시간대(`occurred_at` 의 시).
#   「구역」은 행에 없다(Zone 은 카메라 묶음이지 사건 칸이 아니다 — 실측) — 지어내지 않고
#   가정 목록에 남긴다. 축이 다섯인 것은 정본이 다섯을 불러서가 아니라 **행이 다섯을
#   들고 있어서**다.
#
# ★ 「합계 = 목록 수」(AC-5) — 이 함수도 `services.recent_events` 를 **같은 인자로**
#   부른다. 화면은 이 `total` 을 같은 창의 `GET /events?limit=<row_cap>` 의 `total`
#   과 대조해 다르면 빨강으로 적는다(`TeamStatus` 의 「합계 = 행 합」 규약).
#   그리고 **각 축의 건수 합은 `total` 과 같다** — 어느 행도 어느 칸에 두 번 세어지지
#   않고, 어느 행도 빠지지 않는다(시험이 다섯 축 전부를 대조한다).

#: 축의 이름과 사람이 읽는 제목. **화면이 이 이름을 손으로 들지 않는다** — 응답에 실린다.
AXES = (
    ("camera", "카메라"),
    ("event_type", "유형"),
    ("severity", "심각도"),
    ("verdict", "판정"),
    ("hour", "시간대"),
)

#: 미판정 행의 판정 축 키. `verdict` 가 `None` 인 것을 빈 문자열로 뭉개지 않는다 —
#: 「아직 아무도 판정하지 않았다」는 판정값이 아니라 **판정의 부재**다(D-290).
UNREVIEWED_KEY = "unreviewed"


def _axis_rows(counter: Counter, labels: dict | None = None) -> list[dict]:
    """Counter → 화면 행. 건수 내림차순 · 같은 건수면 키 오름차순(결과가 흔들리지 않게)."""
    labels = labels or {}
    rows = [{"key": str(k), "label": labels.get(k, str(k)), "count": int(n)}
            for k, n in counter.items()]
    rows.sort(key=lambda r: (-r["count"], r["key"]))
    return rows


def stats_axes(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
    event_type: str | list[str] | None = None,
    severity: str | list[str] | None = None,
) -> dict:
    """UX-39 통계 화면 — 기간 내 사건을 **축 다섯**으로 접는다. 나눗셈이 없다(건수뿐).

    ★ 시간대는 **서버 시간대**(`settings.TIME_ZONE`)의 시(0~23)다 — 어느 시간대인지를
      `hour_tz` 로 함께 낸다. 화면이 브라우저 시간대로 다시 접으면 두 곳이 갈린다.
    """
    actor = scope.require_actor()
    since, until = _resolve_window(since, until)

    key = _cache_key("axes", actor, since=since, until=until,
                     event_type=event_type, severity=severity)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    rows = services.recent_events(scope=scope, since=since, until=until,
                                  event_type=event_type, severity=severity,
                                  limit=_ROW_CAP + 1)
    capped = len(rows) > _ROW_CAP
    rows = rows[:_ROW_CAP]

    camera_names = {e.stream_monitor_id: (e.stream_monitor_name or f"카메라 {e.stream_monitor_id}")
                    for e in rows}
    hour_labels = {h: f"{h:02d}시" for h in range(24)}
    verdict_labels = {UNREVIEWED_KEY: "미판정"}

    axes = {
        "camera": _axis_rows(Counter(e.stream_monitor_id for e in rows), camera_names),
        "event_type": _axis_rows(Counter(e.event_type for e in rows)),
        "severity": _axis_rows(Counter(e.severity for e in rows)),
        "verdict": _axis_rows(
            Counter((e.verdict if e.verdict is not None else UNREVIEWED_KEY) for e in rows),
            verdict_labels),
        "hour": _axis_rows(
            Counter(timezone.localtime(e.occurred_at).hour for e in rows), hour_labels),
    }

    payload = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "total": len(rows),
        "axes": axes,
        "axis_titles": {k: t for k, t in AXES},
        "axis_order": [k for k, _ in AXES],
        "hour_tz": str(timezone.get_current_timezone()),
        "capped": capped,
        "row_cap": _ROW_CAP,
    }
    _cache_set(key, payload)
    return payload


#: CSV 의 첫 글자 — 한글이 엑셀에서 깨지지 않게 UTF-8 BOM 을 앞에 둔다.
#: (`codecs.BOM_UTF8` 을 푼 것 — 보이지 않는 글자를 소스에 직접 두면 편집기가 조용히 지운다.)
CSV_BOM = codecs.BOM_UTF8.decode("utf-8")
CSV_HEADER = ("axis", "axis_title", "key", "label", "count")


def stats_axes_csv(**kwargs) -> str:
    """`stats_axes` 를 **그대로** CSV 로 편다 — 여기서 다시 세지 않는다.

    행 수 = 다섯 축의 행 수 합 + 머리 1 + 합계 1. 마지막 「합계」 행은 `total` 이라
    화면의 수와 파일의 수를 사람이 대조할 수 있다. 값은 `csv` 모듈이 인용한다 —
    카메라 이름에 쉼표가 있어도 칸이 밀리지 않는다.
    """
    import csv
    import io

    payload = stats_axes(**kwargs)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for axis in payload["axis_order"]:
        title = payload["axis_titles"][axis]
        for r in payload["axes"][axis]:
            writer.writerow((axis, title, r["key"], r["label"], r["count"]))
    writer.writerow(("total", "합계", "", f"{payload['since']} ~ {payload['until']}",
                     payload["total"]))
    return CSV_BOM + buf.getvalue()
