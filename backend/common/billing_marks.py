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
  `kernels/k1_event.count_events` · `kernels/k2_notify.count_deliveries` **둘뿐**이고,
  둘 다 **세기만** 한다. 목록·화면은 이 파일을 모른다.
"""
from __future__ import annotations

from common.probe_marker import (DRILL_MARKER, PROBE_FIELD, PROBE_MARKER,
                                 exclude_probe)

#: 청구에서 빼는 표식들. **여기서 문자열을 새로 적지 않는다** — `probe_marker` 가
#: 정본이고 이 파일은 그 값을 **묶기만** 한다. 새 표식이 생기면 이 튜플에 든다.
UNBILLABLE_MARKERS = (PROBE_MARKER, DRILL_MARKER)


#: ⚠ **행 하나를 두고 묻는 함수(`is_unbillable_track`)는 만들지 않았다.** 쓸 자리가
#:   없기 때문이다 — 청구의 셈은 **queryset 에서** 빼고(`exclude_unbillable`),
#:   받아서 파이썬에서 거르지 않는다(`exclude_probe` 머리말의 그 이유: 상한이 걸린
#:   목록을 뒤에서 거르면 상한 밖의 행이 없는 것이 된다). 부르는 사람 없는 함수를
#:   미리 세우면 그것은 잠든 코드이고, 잠든 코드는 **틀려도 아무도 모른다**(D-377).
#:   한 행을 묻는 자리가 생기는 날 `probe_marker.is_probe_track` ·
#:   `probe_marker.is_drill_track` 을 **그대로** 부르면 된다.


def exclude_unbillable(qs, *, via: str = ""):
    """queryset 에서 **청구에 못 올리는 행을 뺀다.** ORM 이 있는 자리(커널)에서만 쓴다.

    Args:
        via: 표식이 이 표에 없고 관계 너머에 있을 때 그 관계 이름
            (`DeliveryRecord` → `via="event"`). `exclude_probe` 와 같은 뜻이다.

    ★ 인자가 `via` 하나뿐인 것이 규약이다(P-201). 「이번만 훈련을 세 달라」는 칸을
      만들지 않는다 — 그 칸이 생기는 순간 청구의 셈이 부르는 자리마다 갈라진다.
    """
    qs = exclude_probe(qs, via=via)
    field = f"{via}__{PROBE_FIELD}" if via else PROBE_FIELD
    return qs.exclude(**{f"{field}__startswith": DRILL_MARKER})


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
