# -*- coding: utf-8 -*-
"""K6 피드백·계측 커널 — 공개 면 (DA-04 §2 K6).

오탐을 모으고, 사용량을 세는 한 벌.

이중 AC (DA-04 §1-2) — 충돌 시 **계약 AC 우선**
------------------------------------------------
    [F-14 계약] 월간 오탐률 리포트 생성
    [U1 상품]  오탐률 추이 **월 하락**
    [U4 상품]  요금 = 시스템 집계

★ DA-04 가 이미 해법을 적었다:

    같은 `status` 필드가 월간 리포트(F-14)와 추이 지표(U1)와 과금 근거(U4)를 동시에
    먹인다. **집계 경로를 하나로 유지하는 것 자체가 요구사항이다.**

그래서 이 커널은 **집계 표를 만들지 않는다.** `false_positive_rate` 하나가 전체 창과
월별 칸을 같은 질의에서 낸다 — 두 벌로 세면 숫자가 갈리고, 갈린 숫자는 고객 앞에서 못 쓴다.

왜 K6 은 모델이 없나
--------------------
DA-04 K6: *"오탐률의 분모·분자는 `DetectionEvent.status` 하나에서 나온다.
**별도 집계 테이블을 만들지 않는다.**"* 그 말을 그대로 따른다 — 이 패키지에
`models.py` 가 없는 것이 설계이고, 있으면 그것이 결함이다.

★ 한 칸만 옮겼다 — `status` → `verdict` (D-293)
-----------------------------------------------
DA-04 가 지목한 칸은 `status` 였는데, 그 칸은 **수명주기**라서 종료(`closed`)가
판정(`confirmed`/`rejected`)을 덮는다. 덮이면 그 이벤트가 분모에서 빠지고,
**종료가 쌓일수록 오탐률이 저절로 좋아진다.** 개선이 아니라 나쁜 데이터가
사라지는 것이고, U1 의 "오탐률 월 하락"이 그 축소만으로 달성돼 버린다.

그래서 같은 행에 덮이지 않는 칸 `verdict` 를 하나 두고 **거기서만 센다.**
DA-04 의 요구는 지켜진다 — 여전히 표 하나, 집계 경로 하나다. 바뀐 것은
어느 칸에서 세는가뿐이고, 그 한 칸이 지표의 자가개선을 막는다.

  강제: `tests/test_d293_cohort_regression.py` — 같은 코호트를 두 시점에 계산해
  **값이 동일한지** 본다. 값이 변하면 exit 1.

`record_feedback` 은 왜 K1 을 부르나 — **쓰기 경로는 하나여야 한다**
-------------------------------------------------------------------
DA-04 K6 표는 `record_feedback` 옆에 *"K1 `review_event` 가 호출"* 이라 적었다.
그런데 판정을 **저장하는 자리**는 `DetectionEvent.status` 하나뿐이고, K6 이 그것을
직접 쓰면 같은 필드에 **쓰는 곳이 둘**이 된다. 그 순간 "집계 경로를 하나로" 라는
요구가 쓰기 단계에서 이미 깨진다.

그래서 방향을 뒤집지 않고 **얇게 위임한다**: `K6.record_feedback` → `K1.review_event`.
K6 은 K1 을 **소비**하고, 쓰기는 여전히 K1 한 곳에서 일어난다.
이것이 D-287 이 말한 재사용의 증거이기도 하다 —
*"진짜 재사용은 K2·K3·K4 가 K1 을 소비하는 것으로 증명된다."*

  ※ 실측이 문서와 다른 지점이라 **P-K6-2 로 적재**했다 (D-210 실측 우선 · D-213 적재 후 전진).

테넌트 스코프 — D-281
---------------------
공개 함수는 전부 `*, scope: TenantScope` 를 **키워드 전용 필수 인자**로 받는다.
계측은 전부 읽기이므로 `scope.require_actor()` 를 통과해야 한다 — 시스템 스코프로
오탐률을 물으면 그것은 **전 테넌트 집계**이고, 전 테넌트 집계는 격리의 부재다.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any, Iterable

from django.apps import apps
from django.db.models import Count, Q
from django.utils import timezone

from common.tenant_filters import filter_by_group_field
from common.tenant_scope import TenantScope
from kernels.k6_feedback.exceptions import InvalidMetricInput, NotImplementedYet
from kernels.k6_feedback.schemas import FalsePositiveRate, RateWindow

#: 분모에 드는 판정 — **사람이 판정한 것만**. 미판정(null)은 분모가 아니다.
#: 미판정을 분모에 넣으면 판정을 미루기만 해도 오탐률이 떨어진다.
#:
#: ★ 이름이 `..._STATUSES` 가 아니라 `..._VERDICTS` 인 것이 D-293 의 요점이다:
#:   세는 칸이 `status`(수명주기 — 종료가 덮는다)에서 `verdict`(판정 — 덮이지 않는다)로
#:   옮겨졌다. 값 자체는 같은 두 글자이고, **어느 칸에서 세는가**만 달라졌다.
REVIEWED_VERDICTS = ("confirmed", "rejected")

#: 지원하는 묶음 단위. `kpi_series` 와 공유한다 — 두 함수가 다른 달력을 쓰면
#: 같은 기간의 두 보고가 다른 칸으로 나온다.
BUCKETS = ("month",)


def _model(name: str):
    return apps.get_model("stream_monitors", name)


def _owner_field(model) -> str:
    """K1 과 **같은 판단**을 쓴다 — 판단은 한 곳에서만 한다 (D-212).

    저장소 소스의 `BaseModelWithGroup` 은 `groups` M2M 을 선언하지만 실행 중인
    dj-core 는 `group` FK 를 준다(P-LOCAL-4 미결). 한쪽을 박으면 다른 환경에서 조용히 깨진다.
    """
    from kernels.k1_event.services import _owner_field as k1_owner_field

    return k1_owner_field(model)


def _month_starts(since: datetime, until: datetime) -> list[datetime]:
    """`since` 부터 `until` 까지의 **달 시작점**들. 달력은 여기 한 곳에서만 센다."""
    cursor = since.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    out: list[datetime] = []
    while cursor <= until:
        out.append(cursor)
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 1. record_feedback — 판정을 적재한다 (쓰기는 K1 한 곳에서)
# ═══════════════════════════════════════════════════════════════════════════
def record_feedback(event_id: int, *, verdict: str, reason: str = "",
                    scope: TenantScope):
    """오탐 판정을 남긴다. **저장은 K1 이 한다** — 여기서 직접 쓰지 않는다.

    같은 `status` 필드에 쓰는 곳이 둘이 되면 "집계 경로를 하나로" 라는 DA-04 의 요구가
    쓰기 단계에서 이미 깨진다. 그래서 이 함수는 K1 의 문지기·감사 경로를 그대로 탄다:
    남의 테넌트 이벤트면 K1 이 404 를 던지고, 판정자·판정시각도 K1 이 찍는다.

    돌려주는 것은 K1 의 `EventView` 다. K6 이 같은 값을 자기 모양으로 다시 싸지 않는다 —
    싸는 순간 두 스키마가 갈리고, 갈린 스키마는 App 이 어느 쪽을 믿을지 모르게 만든다.
    """
    from kernels.k1_event import review_event  # 순환 import 를 만들지 않는다 (함수 안에서)

    return review_event(event_id, verdict=verdict, reason=reason, scope=scope)


# ═══════════════════════════════════════════════════════════════════════════
# 2. false_positive_rate — 비율 + **분모·분자** (F-14 ↔ U1 이 같은 것을 본다)
# ═══════════════════════════════════════════════════════════════════════════
def false_positive_rate(
    *,
    scope: TenantScope,
    since: datetime | None = None,
    until: datetime | None = None,
    bucket: str | None = None,
    event_type: str | Iterable[str] | None = None,
    severity: str | Iterable[str] | None = None,
    stream_monitor_id: int | None = None,
    ai_model_id: int | None = None,
) -> FalsePositiveRate:
    """기간의 오탐률. **비율만 내지 않는다 — 분모·분자를 함께 낸다** (DA-04 K6 표).

    `bucket="month"` 면 월별 칸을 함께 낸다. **같은 질의에서 낸다** — F-14 의 월간
    리포트와 U1 의 추이가 서로 다른 집계 경로를 타면 두 숫자가 갈린다.

    ★ 분모가 0 이면 `rate` 는 `None` 이다. **0.0 이 아니다.**
      0.0 으로 내면 "판정을 안 하기만 해도 오탐률이 좋아지는" 지표가 된다.

    ★ 미판정 수(`unreviewed`)를 함께 낸다 — 모수를 숨기지 않는다 (D-271 ③).
    """
    if bucket is not None and bucket not in BUCKETS:
        raise InvalidMetricInput(
            f"bucket={bucket!r} 은 지원하지 않는다. 허용: {', '.join(BUCKETS)}. "
            f"달력을 두 벌로 만들지 않는다 — 같은 기간이 두 보고에서 다른 칸으로 나온다")

    Event = _model("DetectionEvent")
    # 계측은 읽기다. 시스템 스코프로는 물을 수 없다 — 그것은 전 테넌트 집계이고,
    # 전 테넌트 집계는 격리가 아니라 격리의 부재다 (D-281).
    actor = scope.require_actor()

    until = until or timezone.now()
    since = since or (until - timedelta(days=30))
    if since > until:
        raise InvalidMetricInput(f"기간이 뒤집혔다 — since={since} > until={until}")

    qs = Event._base_manager.filter(occurred_at__gte=since, occurred_at__lte=until)
    qs = filter_by_group_field(qs, actor, field=_owner_field(Event))

    def _in(field: str, value):
        nonlocal qs
        if value is None:
            return
        if isinstance(value, str):
            qs = qs.filter(**{field: value})
        else:
            qs = qs.filter(**{f"{field}__in": list(value)})

    _in("event_type", event_type)
    _in("severity", severity)
    if stream_monitor_id is not None:
        qs = qs.filter(stream_monitor_id=stream_monitor_id)
    if ai_model_id is not None:
        qs = qs.filter(ai_model_id=ai_model_id)
    # 소유가 M2M 일 때 조인이 같은 행을 여러 번 낸다. 세는 자리에서 그것은
    # **분모가 부풀어 오르는 것**이고, 부푼 분모는 오탐률을 실제보다 낮게 보고한다.
    qs = qs.distinct()

    filters = {
        "since": since, "until": until, "event_type": event_type,
        "severity": severity, "stream_monitor_id": stream_monitor_id,
        "ai_model_id": ai_model_id,
    }
    total = _window(qs, since, until)
    buckets: tuple[RateWindow, ...] = ()
    if bucket == "month":
        buckets = tuple(
            _window(qs, start, _next_month(start) - timedelta(microseconds=1))
            for start in _month_starts(since, until)
        )
    return FalsePositiveRate(total=total, buckets=buckets, filters=filters)


def _next_month(start: datetime) -> datetime:
    return (start.replace(day=28) + timedelta(days=4)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)


def _window(qs, since: datetime, until: datetime) -> RateWindow:
    """창 하나를 **한 번의 질의**로 센다.

    상태별로 따로 물으면 질의가 창 수만큼 늘고(F-05 의 p95 를 먹는다), 무엇보다
    **각 질의 사이에 판정이 바뀔 수 있다** — 그러면 분자와 분모가 다른 시점의 사실이 된다.
    """
    row = qs.filter(occurred_at__gte=since, occurred_at__lte=until).aggregate(
        # ★ 세는 칸은 `verdict` 다 — `status` 가 아니다 (D-293).
        #   status 로 세면 종료된 판정이 분모에서 빠지고, 그러면 같은 코호트의
        #   오탐률이 **시간이 갈수록 달라진다.** 코호트 회귀 시험이 그것을 막는다.
        rejected=Count("pk", filter=Q(verdict="rejected"), distinct=True),
        reviewed=Count("pk", filter=Q(verdict__in=REVIEWED_VERDICTS), distinct=True),
        # 미판정 — 수명주기와 무관하게 **판정이 없는 것 전부**다. `status="new"` 로
        # 세면 판정 없이 종료된 이벤트가 어느 칸에도 안 잡혀 모수가 조용히 준다.
        unreviewed=Count("pk", filter=Q(verdict__isnull=True), distinct=True),
        # 판정 없이 닫힌 것 — 미판정의 부분집합이다. 이 수가 크면 판정 절차가
        # 종료에 밀리고 있다는 뜻이고, 그것은 지표가 아니라 운영의 신호다.
        closed_unjudged=Count(
            "pk", filter=Q(status="closed", verdict__isnull=True), distinct=True),
    )
    return RateWindow(
        since=since, until=until,
        rejected=row["rejected"], reviewed=row["reviewed"],
        unreviewed=row["unreviewed"],
        closed_without_verdict=row["closed_unjudged"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3. usage_snapshot — **아직 없다** (W4-1 계측 모델이 선행)
# ═══════════════════════════════════════════════════════════════════════════
def usage_snapshot(*, scope: TenantScope, since: datetime | None = None,
                   until: datetime | None = None):
    """채널수·이벤트수·저장량 등의 사용량 스냅샷 (U4 과금 근거).

    ★ **구현하지 않았다.** DA-04 K6 표가 이 출력을 `W4-1 UsageSnapshot` 으로 지목하는데
      그 모델이 저장소에 **없다**(실측: `grep -rn UsageSnapshot backend/` → 0건).
      저장량·채널수를 지금 세면 **어디서 세는지를 추측**하게 되고, 그 추측이 곧 과금 근거가
      된다 — D-280 이 금지한 자리다. 요금이 걸린 숫자는 특히 그렇다.

    조용히 0 이나 빈 dict 를 돌려주지 않는다. 계측에서 그것은 가장 나쁜 모양이다:
    **아무도 재지 않은 지표가 좋은 지표로 보고된다.**

    선행: W4-1(계측 모델) — 무엇을 세는가(채널·이벤트·저장량)의 정의가 먼저다.
    """
    scope.require_actor()  # 스코프를 받는 자리는 지금 세운다 — 나중에 붙이면 잊는다
    raise NotImplementedYet(
        "K6.usage_snapshot(U4 과금 근거)은 아직 구현되지 않았다. "
        "W4-1 `UsageSnapshot` 모델이 저장소에 없고(실측 0건), 무엇을 세는지의 정의가 "
        "선행이다. 요금 근거를 추측으로 채우지 않는다 (D-280). "
        "지금은 이름만 서 있다 — DA-04 §2 K6 표가 정한 공개 면 4개 중 하나다")


# ═══════════════════════════════════════════════════════════════════════════
# 4. kpi_series — **아직 없다** (t0/t1 계측 적재가 선행)
# ═══════════════════════════════════════════════════════════════════════════
def kpi_series(metric: str, *, scope: TenantScope,
               since: datetime | None = None, until: datetime | None = None):
    """3초·30초 실측 분포를 포함한 KPI 시계열 (p50/p95).

    ★ **구현하지 않았다.** DA-04 K6: *"DA-03 §2-4 의 `t0/t1` 계측을 여기 적재한다.
      검수는 '재봤더니 빨랐다'가 아니라 **p50/p95** 로 한다."* — 그 `t0/t1` 을 적재하는
      자리가 아직 코드에 없다. 없는 표본으로 p95 를 내면 그 수는 **만들어진 수**다.

    선행 2건:
      · 계측 지점 — 어느 두 점 사이를 재는가 (DA-03 §2-4 가 지정한 t0/t1).
      · 적재처 — 이벤트 행에 붙일 것인가 별 표인가. 별 표를 만들면 DA-04 의
        "집계 경로를 하나로" 와 충돌하므로 **판단이 필요하다** (P-K6-3 적재).
    """
    scope.require_actor()
    if not (metric or "").strip():
        raise InvalidMetricInput("metric 이름이 비었다 — 무엇을 재는지 말하지 않았다")
    raise NotImplementedYet(
        f"K6.kpi_series(metric={metric!r})는 아직 구현되지 않았다. "
        "DA-03 §2-4 의 t0/t1 계측 적재가 선행이다 — 표본이 없는 p95 는 만들어진 수다. "
        "적재처 판단은 P-K6-3 으로 적재했다")
