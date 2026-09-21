# -*- coding: utf-8 -*-
"""P-206 — **청구서에서 빼는 표식**. 세는 자리가 묻는 한 질문의 정본 한 곳.

한 문장
-------
    `probe`(게이트 탐침)와 `drill`(훈련)은 **행으로 남고 제품이 보지만, 돈으로는 안 간다.**

왜 이 파일이 따로 있나 — **두 표식의 뜻이 다르기 때문**이다 (P-201)
--------------------------------------------------------------------
`common/probe_marker.py`(차선 U1 소유)가 **표식 문자열의 정본**이다. 이 파일은 거기서
낱말을 빌려다가 **청구의 셈**이 묻는 질문 하나에만 답한다. P-201 표를 그대로 옮기면:

    probe  : 제품이 **안 센다**(P-193) · 청구도 **안 한다**
    drill  : 제품이 **센다**(훈련 배지 · K4 「훈련 N건 별도」) · 청구는 **안 한다**
    실사건  : 제품도 세고 · 청구도 한다

★ **가운데 줄이 이 파일의 존재 이유 전부다.** `drill` 은 `exclude_probe` 로는 안 빠진다
  (`startswith("data_source=probe")` 가 `data_source=drill;…` 을 안 거른다 — P-201 이
  그렇게 되도록 일부러 둔 것이다). 그래서 제품은 아무것도 안 고치고 훈련을 세고,
  **청구만** 여기를 지나 한 줄 더 뺀다.

★ **매개변수를 만들지 않는다** (P-201 · 세종이 이름으로 금지). `include_drill` 같은
  칸을 부르는 자리마다 달면 세는 법이 자리마다 갈라지고 갈라진 쪽이 조용히 이긴다.
  그래서 이 파일의 문은 **인자 없는 한 줄**이다 — 청구의 셈은 **언제나** 둘 다 뺀다.
  제품의 셈이 필요하면 그 자리는 이 파일을 **부르지 않는다**(`query_events` ·
  `list_deliveries` 는 지금도 이 파일을 모른다).

⚠ **남은 구멍은 이름을 적어 둔다** [실측 2026-09-20 · 차선 U56]
----------------------------------------------------------------
표식이 **없는** 옛 훈련 사건 — 훈련 창(`stream_monitors/services/drill.py` 의 감사
한 줄) 안에서 났지만 `track_id` 가 빈 행 — 은 이 갈래로 **못 뺀다.** 그 행들은 지금도
청구에 든다. 창 판정은 행마다 감사를 물어야 해서 **월 단위 셈 한 번에 쓸 수 없다**
(한 달 셈이 감사 전수 조회가 된다). 이것은 **모르는 것이 아니라 아는 빚**이고,
`tests/test_u56_metering_seeds.py` 가 그 사실을 시험으로 적어 두었다 — 0으로 덮지 않는다.

★ **거르는 곳은 측정이지 제품이 아니다** (D-497). 이 파일을 부르는 자리는
  `kernels/k1_event.count_events` · `kernels/k2_notify.count_deliveries` ·
  `kernels/k6_feedback.usage_snapshot` **셋뿐**이고, 셋 다 **세기만** 한다.
  목록·화면은 이 파일을 모른다.

★ **표식을 실을 자리가 없던 표 셋 — 이제 있다** (P-224 · 2026-09-21 · 턴 AB · 차선 B)
--------------------------------------------------------------------------------
턴 Z 에 계량의 마지막 직접 셈 셋(카메라·계정·미디어 장부)이 커널로 들어왔는데 그 세
표에는 `track_id` 칸이 **없었다.** 걸 자리가 없으니 `exclude_unbillable` 은 안 걸렸고,
**씨앗이 청구에 들고 있었다** [실측 2026-09-21 11:37 · 이 턴의 「전」 · 아래 수].

칸을 세 표에 똑같이 더하는 길은 **집행 불가**였다. 셋 중 둘이 남의 것이기 때문이다:

    stream_monitors.StreamMonitor   ← **우리 앱**.  칸을 더할 수 있다
    user.CoreUser                   ← **dj-core**.  §0.4 — 못 더한다
    file_management.UserMediaFile   ← **dj-core**.  §0.4 — 못 더한다
    core.apikey_account.APIKey      ← **dj-core**.  §0.4 — 못 더한다

세종 P-224 가 그래서 길을 **둘로 갈랐다**:

    ① **카메라 표는 칸으로** — `data_source`, 기본값 `live`.
       기본값이 `live` 인 것이 규약이다: **표식 없음 = 고객의 것**이다. 반대로 두면
       표식을 안 단 고객 행이 조용히 공짜가 되고, **공짜가 된 것은 안 보인다.**
    ② **dj-core 셋은 곁표로** — `common.BillingMark` 한 표(`common/models.py`).
       남의 표에 칸을 더하지 않고, 남의 행을 고치지도 않는다. **우리 표에 우리가
       심었다는 사실을 적어 둘 뿐**이고, 그 사실을 읽는 자리는 이 파일 하나다.

  ★ **읽는 자리는 늘어나지 않았다.** 부르는 쪽(`k1_event` · `k2_notify` ·
    `k6_feedback`)은 한 글자도 안 고쳤다 — 세 갈래(칸 · 곁표 · `track_id`)를 고르는
    일은 전부 `exclude_unbillable` 안에서 끝난다. 부르는 자리마다 `if` 를 쓰면 그
    판단이 자리마다 갈리고, **갈라진 쪽이 조용히 이긴다.**
  ★ 0으로 덮지 않는다. 이름으로 씨앗을 거르는 길(`username__startswith="gxseed"`)은
    **지금도 없다** — 그것은 표식이 아니라 추측이고, 추측이 청구 근거가 되는 순간
    고객 이름 하나가 우리 접두와 겹치면 그 계정이 조용히 공짜가 된다 (D-280).
    이름은 **소급 한 번**에 근거로 쓰였고(그 목록은 마이그레이션 안에 pk 로 얼어
    있다), **세는 코드는 이름을 모른다.** 그 둘은 다른 일이다.

⚠ **저장 장부(미디어)의 씨앗 몫은 여전히 「못 쟀다」다.** 곁표는 섰지만 *무엇을
  표시할지*의 근거가 없다 — 미디어 행에는 표식도 없고 이름·만든이로도 안 갈린다
  [실측: 씨앗 이름 0건 · 만든이가 씨앗 계정인 것 0건]. 그것은 **정황이지 표식이
  아니다.** 0으로 덮지 않는다 (D-301).

⚠ **표식은 「발급 순간」에 달려야 한다.** 소급은 한 번이고, 그 뒤로 새로 나는 씨앗은
  만드는 경로가 제 손으로 `mark_unbillable` 을 불러야 한다. 그 배선이 안 된 경로는
  다시 새 구멍이다 — 어느 경로가 남았는지는 차선 B 보고의 「넘김」에 적혀 있다.
"""
from __future__ import annotations

import logging

from common.probe_marker import (DRILL_MARKER, PROBE_FIELD, PROBE_MARKER,
                                 exclude_probe)

log = logging.getLogger("guardianx.billing.marks")

#: 청구에서 빼는 표식들. **여기서 문자열을 새로 적지 않는다** — `probe_marker` 가
#: 정본이고 이 파일은 그 값을 **묶기만** 한다. 새 표식이 생기면 이 튜플에 든다.
UNBILLABLE_MARKERS = (PROBE_MARKER, DRILL_MARKER)

#: 출처 칸의 **이름**. 새로 짓지 않았다 — 표식 문자열의 왼쪽이 그대로 칸 이름이다
#: (`data_source=probe` 의 왼쪽). 그래서 칸과 표식은 **같은 낱말을 쓴다**: 한쪽을
#: 고치면 다른 쪽이 따라 바뀌고, 두 벌이 갈릴 자리가 애초에 없다.
DATA_SOURCE_FIELD = PROBE_MARKER.split("=", 1)[0]

#: **기본값 — 고객의 것.** 마이그레이션이 모든 옛 행에 이 값을 넣는다. 반대로
#: (기본값을 씨앗 쪽으로) 두면 표식을 안 단 고객 행이 조용히 공짜가 된다.
BILLABLE_SOURCE = "live"

#: 검수·시연용으로 **우리가 심은** 행. `probe`·`drill` 과 달리 이 낱말은 여기 산다 —
#: 제품은 이 행을 실사건과 **똑같이** 센다(화면에도 뜨고 큐에도 선다). 가르는 것은
#: **청구뿐**이고, 그래서 청구가 묻는 자리가 이 낱말의 유일한 소비자다.
#: (`probe`·`drill` 은 제품이 갈라야 하므로 `probe_marker` 가 정본이다.)
SEED_SOURCE = "seed"

#: 출처 칸이 가질 수 있는 값 중 **청구에 못 올리는 것들.** 위 표식들에서 낱말만
#: 떼어 온다 — 여기서 `probe`·`drill` 을 다시 타자하지 않는다.
NONBILLABLE_SOURCES = tuple(
    marker.split("=", 1)[1] for marker in UNBILLABLE_MARKERS) + (SEED_SOURCE,)


#: ⚠ **행 하나를 두고 묻는 함수(`is_unbillable_track`)는 만들지 않았다.** 쓸 자리가
#:   없기 때문이다 — 청구의 셈은 **queryset 에서** 빼고(`exclude_unbillable`),
#:   받아서 파이썬에서 거르지 않는다(`exclude_probe` 머리말의 그 이유: 상한이 걸린
#:   목록을 뒤에서 거르면 상한 밖의 행이 없는 것이 된다). 부르는 사람 없는 함수를
#:   미리 세우면 그것은 잠든 코드이고, 잠든 코드는 **틀려도 아무도 모른다**(D-377).
#:   한 행을 묻는 자리가 생기는 날 `probe_marker.is_probe_track` ·
#:   `probe_marker.is_drill_track` 을 **그대로** 부르면 된다.


def _field_names(model) -> set:
    return {f.name for f in model._meta.get_fields()}


def _mark_model():
    """곁표 모델(`common.BillingMark`). 없으면 `None`.

    왜 늦게 찾나 — 이 파일은 커널이 **import 하는** 파일이고, import 시점에 앱
    등록이 끝났다는 보장이 없다. `apps.get_model` 을 부르는 시점을 **묻는 순간**으로
    미루면 그 순서를 신경 쓸 일이 없다(`k6_feedback` 이 미디어 장부를 찾는 방식과
    같다). 없으면 `None` — 마이그레이션 전 DB 에서도 셈이 죽지는 않는다.
    """
    from django.apps import apps as django_apps

    try:
        return django_apps.get_model("common", "BillingMark")
    except LookupError:
        return None


def marked_unbillable_ids(model) -> list:
    """곁표에 **우리가 심었다고 적혀 있는** 행들의 pk.

    ★ **이름을 묻지 않는다.** 이 함수가 아는 것은 표 이름(`model_label`)과 출처 낱말
      뿐이다. 어느 행이 씨앗인지는 **만든 쪽이 적어 둔 것**이고, 여기서 다시 추측하지
      않는다 (D-280).

    ★ 값을 파이썬으로 끌어올린다. 곁표의 `object_id` 는 문자열이고 세는 표의 pk 는
      정수일 수 있어서 **DB 가 두 칸을 직접 견줄 수 없다.** 끌어올리는 양은 「우리가
      심은 행」의 수라 작고(수십), 이것은 **결과를 뒤에서 거르는 것이 아니다** —
      거르기는 그대로 ORM 이 한다(`exclude(pk__in=…)`).
    """
    Mark = _mark_model()
    if Mark is None:
        return []
    to_python = model._meta.pk.to_python
    out = []
    for raw in (Mark._base_manager
                .filter(model_label=model._meta.label_lower,
                        data_source__in=NONBILLABLE_SOURCES)
                .values_list("object_id", flat=True)):
        try:
            out.append(to_python(raw))
        except (ValueError, TypeError):
            #: ★ **조용히 버리지 않는다.** 못 읽은 표식은 그 행이 청구로 돌아간다는
            #:   뜻이고, 그것은 고객에게 우리 씨앗을 청구하는 일이다. 큰 소리로 남긴다.
            log.warning(
                "청구 표식의 object_id 를 %s 의 pk 로 읽지 못했다: %r — 그 행은 이번 "
                "셈에서 청구에 든다", model._meta.label_lower, raw)
    return out


def exclude_unbillable(qs, *, via: str = ""):
    """queryset 에서 **청구에 못 올리는 행을 뺀다.** ORM 이 있는 자리(커널)에서만 쓴다.

    Args:
        via: 표식이 이 표에 없고 관계 너머에 있을 때 그 관계 이름
            (`DeliveryRecord` → `via="event"`). `exclude_probe` 와 같은 뜻이다.

    ★ 인자가 `via` 하나뿐인 것이 규약이다(P-201). 「이번만 훈련을 세 달라」는 칸을
      만들지 않는다 — 그 칸이 생기는 순간 청구의 셈이 부르는 자리마다 갈라진다.

    ★ **갈래가 셋으로 늘었다 — 부르는 쪽은 그대로다** (P-224 · 턴 AB).
      ㉠ `track_id` 에 얹힌 표식 (사건·발송)  ㉡ `data_source` 칸 (카메라)
      ㉢ 곁표 `common.BillingMark` (dj-core 셋 — 칸을 못 더하는 표)
      셋 중 **이 표에 걸 수 있는 것만** 건다. 이 판단이 여기 있는 이유는 부르는
      자리마다 `if` 를 쓰면 그 판단이 갈리기 때문이다 — 이 파일이 존재하는 이유.

    ⚠ **관계 너머(`via`)는 ㉠ 만 본다.** ㉡·㉢ 은 「이 행이 무엇인가」를 묻는데,
      관계 너머의 행은 **다른 표의 행**이라 그 표의 pk 로 물어야 한다. 지금 `via` 를
      쓰는 자리는 발송 하나(`event` 너머)이고 사건은 ㉠ 로 이미 갈린다 — **쓰는 데가
      없는 갈래를 미리 세우면 그것은 잠든 코드이고, 잠든 코드는 틀려도 아무도 모른다**
      (D-377). 사건 표에 칸이나 곁표 표식이 생기는 날 여기를 넓힌다.

    ★ **`track_id` 가 사라진 날 조용히 통과되지 않는가** — 그 질문은 이제 시험이
      든다(`test_b_billing_marks.py::TheEventMarkerStillHasItsField`). 예전에는 이
      함수가 FieldError 로 큰 소리를 내는 것이 그 역할이었는데, 칸이 없는 표
      (`CoreUser`)에도 이 함수가 걸리게 된 뒤로는 그 소리를 낼 수 없다.
    """
    names = _field_names(qs.model)
    if via:
        qs = exclude_probe(qs, via=via)
        return qs.exclude(**{f"{via}__{PROBE_FIELD}__startswith": DRILL_MARKER})

    if PROBE_FIELD in names:
        qs = exclude_probe(qs)
        qs = qs.exclude(**{f"{PROBE_FIELD}__startswith": DRILL_MARKER})
    if DATA_SOURCE_FIELD in names:
        qs = qs.exclude(**{f"{DATA_SOURCE_FIELD}__in": NONBILLABLE_SOURCES})
    marked = marked_unbillable_ids(qs.model)
    if marked:
        qs = qs.exclude(pk__in=marked)
    return qs


def mark_unbillable(obj, source: str, *, reason: str = ""):
    """**발급 순간에** 이 행이 우리 것임을 적는다 — 곁표 한 줄 (P-224 ②).

    Args:
        obj: 방금 만든 행(계정·미디어·API 키 …). 남의 표여도 된다 — **그 행을 고치지
            않는다.** 우리 표에 「저 행은 우리가 만든 것」이라고 적을 뿐이다.
        source: `NONBILLABLE_SOURCES` 중 하나, 또는 `BILLABLE_SOURCE`.
        reason: 다음 사람이 **코드를 안 읽고** 「왜 이 행이 청구에서 빠졌나」에 답할
            수 있는 한 줄. 빈 사유는 면제와 구별되지 않는다.

    ★ **만드는 경로에서 부른다.** 뒤에서 이름으로 훑어 다는 길을 만들지 않는다 —
      그 길이 곧 D-280 이 금지한 추측이다.
    ★ **덮어쓴다(update_or_create).** 같은 행에 두 표식이 남으면 어느 쪽이 정본인지
      아무도 못 답한다. 두 번 불러도 결과가 같아야 씨앗 명령을 다시 돌릴 수 있다.
    """
    if source not in NONBILLABLE_SOURCES and source != BILLABLE_SOURCE:
        raise ValueError(
            f"모르는 출처입니다: {source!r}. 아는 낱말은 "
            f"{(BILLABLE_SOURCE,) + NONBILLABLE_SOURCES} 뿐입니다 — 새 낱말이 "
            f"필요하면 이 파일에 뜻과 함께 세우십시오(새 낱말이 부르는 자리에서 "
            f"태어나면 청구가 그 뜻을 모릅니다).")
    Mark = _mark_model()
    if Mark is None:
        raise LookupError(
            "청구 표식 곁표(common.BillingMark)가 없습니다 — 마이그레이션이 아직 "
            "안 내렸습니다. 표식을 못 남긴 채 씨앗을 만들면 그 씨앗은 청구에 듭니다.")
    mark, _ = Mark._base_manager.update_or_create(
        model_label=obj._meta.label_lower, object_id=str(obj.pk),
        defaults={"data_source": source, "reason": reason[:500]})
    return mark


def has_marker_field(model) -> bool:
    """이 표에 **표식을 걸 수 있는가.**

    왜 필요한가: 청구의 셈이 표 셋(카메라·계정·미디어 장부)으로 넓어졌는데 그 셋에는
    `track_id` 가 없었다. 없는 칸에 거름을 걸면 FieldError 로 죽고, 죽지 않으려고
    부르는 자리마다 `if` 를 쓰면 **그 판단이 자리마다 갈린다.**

    ★ **뜻이 넓어졌다** (P-224 · 턴 AB). 예전에는 「`track_id` 칸이 있는가」였다.
      이제는 **「어떤 갈래로든 걸 수 있는가」**다 — 칸(`track_id`·`data_source`)이
      있거나, 곁표(`common.BillingMark`)가 서 있으면 참이다. 이름을 안 바꾼 이유는
      부르는 쪽(`k6_feedback._billable_count`)이 묻는 질문이 **한 글자도 안 바뀌었기**
      때문이다: 「이 표에 청구 거름을 걸어도 되나」.

    ★ **매개변수가 아니라 사실이다.** 이것은 「이번만 포함」 칸이 아니다 — 부르는 쪽이
      고를 수 있는 것이 없고, 답은 **모델과 스키마가** 준다. `exclude_soft_deleted` 가
      `deleted` 칸의 유무를 모델에 묻는 것과 같은 규약이다(표 이름을 여기 적지 않는
      것도 같은 이유 — 적어 두면 새 표가 생길 때 아무도 이 목록을 안 고친다).
    """
    names = _field_names(model)
    if PROBE_FIELD in names or DATA_SOURCE_FIELD in names:
        return True
    return _mark_model() is not None


def exclude_soft_deleted(qs, model):
    """**지운 행은 청구하지 않는다** — 청구의 셈이 지키는 둘째 규칙.

    [실측 2026-09-05 · `apps/dsm/metering.py` 머리말] dj-core 는 `objects` 를
    `CustomManagerGroup(models.Manager)` 로 덮었다 — safedelete 의 매니저가 **아니다.**
    그래서 소프트 삭제된 행이 평범한 조회에 **그대로 보인다.** 아무 생각 없이 세면
    **고객이 지운 카메라·사건에 돈을 받는다.**

    ★ 이 세 줄이 `metering.py::_alive` 였다. 셈이 커널로 옮겨 가면서 규칙도 같이
      왔다 — 규칙을 앱에 두고 셈만 옮기면 **규칙이 부르는 사람 없이 남는다.**

    `deleted` 칸이 없는 표는 그냥 센다. 칸의 유무를 **모델에 물어서** 정한다 —
    표 이름을 여기 적어 두면 새 표가 생길 때 아무도 이 목록을 안 고친다.
    """
    names = {f.name for f in model._meta.get_fields()}
    if "deleted" in names:
        qs = qs.filter(deleted__isnull=True)
    return qs
