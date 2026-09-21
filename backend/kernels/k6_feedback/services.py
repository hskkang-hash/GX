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

from common.billing_marks import (exclude_soft_deleted, exclude_unbillable,
                                  has_marker_field)
from common.probe_marker import exclude_probe
from common.tenant_filters import filter_by_group_field, get_user_group
from common.tenant_scope import TenantScope
from kernels.k6_feedback.exceptions import (InvalidMetricInput, K6Error,
                                            NotImplementedYet)
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

    # ★ P-193 — **게이트가 심은 사건은 분모에도 분자에도 안 든다** (2026-09-20 · 차선 U1).
    #   K6 에는 제품 면이 없다. 이 커널이 내는 수는 전부 **재는 수**이고(오탐률 ·
    #   판정 모수 · 미판정), 재는 수에 게이트의 씨앗이 들면 그 지표는 **게이트가 몇 번
    #   돌았는가**를 함께 재게 된다. 그래서 여기는 켜고 끌 인자가 없다 — 끌 자리가
    #   있으면 언젠가 꺼진 채로 대외 보고에 나간다.
    #   뜻은 `common.probe_marker` 한 곳이 정한다(K1 도 같은 곳을 부른다).
    qs = exclude_probe(qs)

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
# 3. usage_snapshot — **장부 셋을 센다** (P-178 U56 ② · 2026-09-21 · 턴 Z)
# ═══════════════════════════════════════════════════════════════════════════
#
# 무엇이 바뀌었나 — 이 자리는 턴 Y 까지 `NotImplementedYet` 이었다
# --------------------------------------------------------------
# 그때 적어 둔 선행 둘은 이랬다: ㉠ `W4-1 UsageSnapshot` 모델이 없다 ·
# ㉡ 「무엇을 세는가」의 정의가 없다. **㉡ 은 이제 있다** — `apps/dsm/metering.py`
# 가 2026-09-05 부터 그 정의를 응답의 `definitions` 로 싣고 화면·CSV 에 내보내고
# 있었다. 없던 것은 정의가 아니라 **정의가 사는 자리**였다.
#
# ㉠ 은 여전히 없고, 그래서 **여기서도 만들지 않는다.** `UsageSnapshot` 은 *적재*
# (스냅샷을 떠서 보관)의 표이고 이 함수는 *셈*이다. 셈을 하려고 표를 만들면 DA-04 K6
# 의 *"별도 집계 테이블을 만들지 않는다 — 두 벌로 세면 숫자가 갈린다"* 를 이 커널이
# 제 손으로 깬다. 적재가 필요해지는 날(청구서 확정·소급 불가 요건) 그 표가 선다.
#
# ★ **왜 K6 인가 — 엉뚱한 커널에 밀어 넣지 않았다**
# ------------------------------------------------
# DA-04 §2 K6 표가 이 출력을 **이름으로** 지목한다:
#     `usage_snapshot(group, period)` → 채널수·이벤트수·저장량 등 (W4-1 UsageSnapshot)
# 그리고 §4 티켓표의 `W4-1` 이 K6 줄에 있다. `metering.py` 가 적어 둔 빚
# (*"갚는 날: 계량 커널 면(W4-1)"*)이 가리키던 자리가 여기다. 새 커널을 세우지도,
# K1(이벤트)·K2(발송)에 장부 셈을 얹지도 않았다 — 둘 다 그 빚이 경고한 그 일이다.
#
# ★ **이벤트·발송은 여기서 안 센다.** 그 둘은 이미 K1·K2 가 센다(P-206). 같은 수를
#   두 커널이 내면 어느 쪽이 청구서인지 아무도 모른다. 이 함수는 **K1·K2 가 안 보는
#   장부 셋**만 답한다.
def usage_snapshot(*, scope: TenantScope, since: datetime | None = None,
                   until: datetime | None = None) -> dict[str, Any]:
    """**장부 셋** — 카메라 대수 · 쓰는 사람 수 · 저장 용량 (U4 과금 근거).

    Args:
        since: 받지만 **안 쓴다.** 이 셋은 「그 달에 새로 생긴 수」가 아니라
            **그 달 끝 시점의 잔량**이다. 카메라는 달마다 새로 사는 물건이 아니고,
            청구는 「그 달에 우리가 지켜 준 대수」에 붙는다. 시그니처에 남겨 두는
            이유는 `false_positive_rate`·`kpi_series` 와 **같은 모양**이어야 부르는
            쪽이 기간을 어느 함수에는 주고 어느 함수에는 안 주는 일이 없기 때문이다.
        until: 잔량을 세는 시점(반열린 — `created_on < until`). 비우면 지금.

    돌려주는 것::

        {"cameras": int, "users": int,
         "storage": {"bytes": int|None, "files": int|None,
                     "unsized": int|None, "why": str}}

    ★ **못 잰 칸은 `None` 이다 — 0이 아니다** (D-301). 미디어 장부를 못 찾으면
      「0바이트 썼다」가 아니라 **「못 쟀다」**다. 0으로 적으면 그 달 청구서의 저장
      용량 칸이 조용히 0원이 되고, 아무도 그것을 결함으로 못 읽는다.

    ★ **전역 관리자여도 제 테넌트만 센다.** `filter_by_group_field` 는 전역 관리자에게
      표 전체를 준다 — 읽기 화면에서는 옳고 **청구서에서는 재앙**이다(`count_events`
      머리말과 같은 자리). 그래서 여기서는 그 함수를 안 쓰고 소속을 직접 못박는다.
      남의 테넌트 카메라 대수가 내 청구서에 실리면 그것은 틀린 청구가 아니라
      **개인정보 유출**이다 — 남의 카메라 대수는 남의 사업 규모다.

    ★ **거르는 규칙은 `common/billing_marks` 한 곳에서 온다.** 소프트 삭제도
      표식(probe·drill)도 이 파일이 제 손으로 적지 않는다. 표식 칸이 없는 표에서는
      `has_marker_field` 가 거짓이라 표식 거름이 **안 걸린다** — 그 사실과 그 수는
      `billing_marks` 머리말 ⚠ 에 적혀 있다(0으로 덮지 않는다).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        raise K6Error(
            "요청자에게 소속이 없어 사용량을 셀 수 없다. 소속 없이 센 수는 "
            "누구의 사용량인지 답할 수 없고, 아무 테넌트나 고르면 남의 수가 "
            "청구서에 오른다 (W0-12)")
    if until is None:
        until = timezone.now()

    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    CoreUser = apps.get_model("user", "CoreUser")

    return {
        "cameras": _billable_count(
            Stream, Stream._base_manager.filter(group=group,
                                                created_on__lt=until)),
        #: `distinct()` — 소속은 **역참조를 타고** 붙는다. 한 사람에게 소속 행이 둘이면
        #: 조인이 그 사람을 두 번 낸다. 청구서에서 **한 사람을 두 번 세는 것**은 0을
        #: 1로 세는 것보다 발견이 늦다: 수가 그럴듯하기 때문이다.
        "users": _billable_count(
            CoreUser, CoreUser._base_manager.filter(
                userprofilelink__group=group, is_active=True,
                date_joined__lt=until).distinct()),
        "storage": _billable_storage(group, until),
    }


def _billable_count(model, qs) -> int:
    """청구에 올릴 수 있는 행만 센다 — **규칙은 `billing_marks` 가 안다.**

    이 두 줄이 이 커널 안에서 「청구의 셈」이라는 말의 전부다. 부르는 자리마다
    `filter(deleted__isnull=True)` 를 손으로 쓰면 그 순간 규칙이 두 벌이 되고,
    한쪽을 고칠 때 다른 쪽은 안 고쳐진다(그 두 벌이 `metering.py::_alive` 였다).
    """
    qs = exclude_soft_deleted(qs, model)
    if has_marker_field(model):
        qs = exclude_unbillable(qs)
    return qs.distinct().count()


def _billable_storage(group, until) -> dict[str, Any]:
    """**저장 용량** — 그 달 끝 시점에 이 테넌트가 저장소에 갖고 있던 바이트.

    ★ 어디서 세나 — **객체저장소를 훑지 않는다.** `core.file_management.UserMediaFile`
      에 `file_size` 와 `group` 이 있고, MinIO 에 올릴 때 그 행이 함께 쓰인다
      [실측 stream_monitors/utils/minio_client.py:253]. 그 장부를 센다.

      버킷을 직접 훑는 길도 있지만 두 가지가 막는다: ㉠ 객체 이름 앞머리는
      `group.code` 인데 **테넌트 몫만 재려면 전 객체를 나열**해야 하고, 화면 한 장이
      저장소 전체를 훑게 된다. ㉡ 이 환경의 저장소는 `minio.invalid` 라 아예 못 닿는다.
      청구서의 수가 저장소의 생사에 매달리면 **저장소가 죽은 달은 청구를 못 한다.**

    ★ **크기를 모르는 파일은 「0바이트」가 아니다.** `file_size` 가 비어 있는 행을
      `unsized` 로 따로 센다. 그 수가 0이 아니면 이 칸은 **하한**이고, 응답이 그렇게
      말한다 — 하한을 총량처럼 청구하면 그것은 우리에게 유리한 반올림이다.
    """
    try:
        Media = apps.get_model("file_management", "UserMediaFile")
    except LookupError as exc:                                  # noqa: BLE001
        #: 장부가 없으면 **못 쟀다**이지 0바이트가 아니다 (D-301).
        return {"bytes": None, "files": None, "unsized": None,
                "why": f"미디어 장부를 찾지 못했다: {exc}"[:200]}

    from django.db.models import Sum

    qs = Media._base_manager.filter(group=group, created_on__lt=until)
    qs = exclude_soft_deleted(qs, Media)
    if has_marker_field(Media):
        qs = exclude_unbillable(qs)
    agg = qs.aggregate(total=Sum("file_size"), files=Count("id"))
    unsized = qs.filter(file_size__isnull=True).count()
    return {
        "bytes": int(agg["total"] or 0),
        "files": int(agg["files"] or 0),
        "unsized": unsized,
        "why": ("크기가 안 적힌 파일이 %d개다 — 이 수는 **하한**이다" % unsized
                if unsized else ""),
    }


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
