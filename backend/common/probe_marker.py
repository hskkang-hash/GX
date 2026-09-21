# -*- coding: utf-8 -*-
"""P-193 — **게이트는 제 씨앗을 세지 않는다.** probe 표식의 **백엔드 정본 한 곳**.

세종 P-193:
    `/api/dsm/events/summary` 의 `unhandled` 칸을 비롯해 **모든 집계·큐·온보딩 술어가
    `data_source=probe`(track_id 표식)를 뺀다. 삭제가 아니라 셈이다.**

왜 이 파일이 필요한가 — 턴 W 실측
---------------------------------
FC 가 29 → 32 로 올랐는데 **오른 세 행이 전부 게이트가 심은 probe 사건 위**에 서 있었다.
「24시간 안 미처리 사건」이 `총 3 · probe 3 · probe 아님 0` 이었다. 집계가 표식을 안 봤기
때문이다 — **게이트가 심은 사건을 게이트가 일감으로 읽고 초록을 냈다.**

★ **여기는 한 곳이다.** 세는 법을 부르는 자리마다 따로 쓰면 어긋나고, 어긋난 쪽이 조용히
  이긴다. probe 를 거르는 백엔드의 모든 자리는 이 파일의 `is_probe_track` /
  `exclude_probe` 만 부른다.

★ **축이 둘이다** (2026-09-20 · 차선 U3 가 화면을 누르다 찾았다). 사건만 막으면 절반이다:
  `DetectionEvent` 를 지나는 축(K1 `query_events` · K6 오탐)과 **발송을 지나는 축**
  (K2 `list_deliveries` — M1 「나에게 온 것」)은 **다른 커널**이고, 사건 축을 닫은 뒤에도
  관제요원의 「나에게 온 것」 맨 위에 게이트가 심은 알림이 서 있었다.
  표식은 발송 행에 없다 — `event` FK 너머에 있다. 그래서 `exclude_probe(qs, via="event")`.

왜 `common/`(L1)인가 — 두 사실이 자리를 정했다
----------------------------------------------
    ① **App 층은 ORM 을 만질 수 없다.** `tests/test_dsm_app.py::AppStaysThinTest` 가
       `apps/dsm/{services,api}.py` 본문에서 모델 접근을 잡는다. 그러니 **거르는 실행**은
       커널에 있어야 한다.
    ② **커널이 둘이다.** 미처리는 K1(`query_events`)이, 오탐 분모는 K6
       (`false_positive_rate`)가 각자 질의한다. 어느 한 커널 안에 두면 다른 커널이 제
       벌을 갖게 된다 — 그것이 위에서 말한 「두 벌」이다.
    `verify_layers` 허용표: `backend/kernels/** → common.**` (공용 유틸은 L1).

표식이 `track_id` 에 얹혀 있는 것은 **고른 것이 아니라 발견한 것**이다
--------------------------------------------------------------------
`DetectionEvent` 에 `data_source` 칸은 **없다.** 그것은 의도다 — `apps/dsm/services.py`
`event_data_source` 가 적어 두었다: *「칸이 아니라 창 판정이다 … 새 칸이 태어나는 순간
과거가 비고, 빈 과거는 「훈련이 아니었다」로 읽힌다」*. probe 는 훈련(drill)과 달리 **창이
없어서** 창 판정으로 답할 수 없고, 그래서 만든 쪽(`scripts/probe_marks.py`)이 화면이 그리지
않는 자유 칸(`track_id`, 64자)에 규약 문자열을 적어 두었다.

    data_source=probe;run=<RUN>            심을 때
    data_source=probe;run=<RUN>;judged=1   판정 뒤

이 얹힘은 **빚**이다. 씨앗을 지우는 날(대표 승인) 같이 갚는다. 그때까지는 여기가 정본이다.

★ **제품을 감추는 파일이 아니다** (D-497 「거르는 곳은 측정이지 제품이 아니다」).
  운영자의 사건 목록은 probe 를 **계속 본다** — 바뀌는 것은 **셈**뿐이다. 감추면 그것은
  「세지 않기」가 아니라 **사건을 숨긴 것**이고, 숨긴 사건은 아무도 못 고친다.

★ **새 문을 만들지 않는다.** probe 를 표기·제외하는 새 라우트가 나면 그것은 새 쓰기 면이고
  빨강이다(조율자 선등록 ㉠). 표식은 이미 행 안에 있다.

짝 맞추기
---------
`scripts/probe_events.py`(조율자 소유)가 게이트 쪽 정본이고 이 파일이 백엔드 쪽 정본이다.
둘은 **같은 뜻이어야 한다** — 갈리는 순간 게이트가 「probe 0건」이라고 하는데 집계는 세고
있는(또는 그 반대) 상태가 된다. `tests/test_u1_probe_not_counted.py` 가 게이트 파일을
**실물로 읽어** 출생 표본 전수로 두 판정기를 맞대 본다. 그 시험이 이 짝을 지킨다.
"""
from __future__ import annotations

#: 행 안에 박힌 표식. 만든 쪽(`scripts/probe_marks.py::MARK` ·
#: `scripts/probe_events.py::PROBE_MARKER`)이 적는다. **여기서 새로 정하는 값이 아니라
#: 그 값을 백엔드가 아는 자리**이고, 짝은 시험이 지킨다.
PROBE_MARKER = "data_source=probe"

#: 표식이 얹혀 있는 칸. 바뀔 일이 없지만 두 부르는 자리(K1·K6)가 문자열을 각자 적지
#: 않게 한 곳에 둔다.
PROBE_FIELD = "track_id"


def is_probe_track(track_id) -> bool:
    """이 행이 **게이트가 만든 것인가** — 한 줄짜리 정본.

    `None`·빈 문자열은 **사람이 만든 것으로 본다.** 모르면 세는 쪽에 둔다 — 빠뜨리는
    쪽보다 낫다: 우리 수가 실제보다 낮게 나오는 것은 보이지만(일감이 안 보인다),
    높게 나오는 것은 **초록으로 보여서 안 보인다.**

    앞에서만 센다. 가운데 낀 것(`xdata_source=probe`)·대문자는 우리 표식이 아니다 —
    남이 적은 값과 우연히 같아 보이는 것을 probe 로 읽으면 **진짜 일감이 사라진다.**
    """
    return bool(track_id) and str(track_id).startswith(PROBE_MARKER)


def exclude_probe(qs, *, via: str = ""):
    """queryset 에서 probe 를 뺀다 — **ORM 이 있는 자리(커널)에서만 쓴다.**

    Args:
        via: 표식이 **이 표에 없고 따라가야 할 때** 그 관계 이름. 예: 발송 이력
            (`DeliveryRecord`)은 제 칸에 표식이 없고 `event` FK 너머에 있다 →
            `via="event"`. 비우면 이 표의 `track_id` 를 본다.

    ★ **따라가는 한 줄을 부르는 쪽에 적지 않는다.** `qs.exclude(event__track_id…)` 를
      커널마다 손으로 쓰면 그 순간 표식 문자열이 두 벌이 되고, 한쪽을 고칠 때 다른
      쪽은 안 고쳐진다 — 이 파일이 존재하는 이유가 그것이다(P-193 「한 곳」).
      ⚠ **따라가는 관계는 null 이 아니어야 한다.** `DeliveryRecord.event` 는 null 이
        아니다[실측 models.py `event = ForeignKey(DetectionEvent, CASCADE)`] — null 을
        허용하는 관계에 쓰면 「표식이 없는 것」과 「이을 것이 없는 것」이 한 답이 된다.

    ★ 받아서 파이썬에서 거르지 않는다. 상한(`limit`)이 걸린 목록을 받아 뒤에서 거르면
      **상한 밖의 사건이 없는 것이 되고**, 「미처리 3건」이 「상한 안의 3건」이 된다
      (DA-04 「필터는 전부 서버에서」와 같은 자리).
    """
    field = f"{via}__{PROBE_FIELD}" if via else PROBE_FIELD
    return qs.exclude(**{f"{field}__startswith": PROBE_MARKER})


# ═══════════════════════════════════════════════════════════════════════════
# P-201 — 표식을 **둘로 가른다** (2026-09-20 · 턴 Y · 세종)
# ═══════════════════════════════════════════════════════════════════════════
#
# P-193 이 서고 **비용이 따라왔다.** 씨앗을 안 세게 하니 **그 씨앗으로 잴 수도 없게**
# 됐다 — 온보딩 `U1#11`(「미처리 사건이 화면에 뜬다」)이 그래서 내려갔다. 잴 것을 심으면
# 그 순간 안 세어지고, 안 세어지는 것으로는 「센다」를 증명할 수 없다.
#
# 세종 판정 — **두 표식은 다른 질문에 답한다:**
#
#     data_source=probe   **게이트 생존 탐침.** 제품이 **안 센다**(P-193 그대로 —
#                         화면·큐·발송·청구 전부). 「게이트가 돌긴 하는가」만 묻는다.
#     data_source=drill   **훈련.** 제품이 **센다.** 사람 화면에 「훈련」 배지가 뜨고,
#                         청구에서는 빠지고, 보고서 K4 는 「훈련 N건 별도」 한 줄.
#
# ★ **새 문 0 · 새 매개변수 0.** 바뀌는 것은 **심는 쪽이 적는 표식 값 하나**뿐이다.
#   제품의 거르는 자리는 `exclude_probe` **정의 하나 그대로**이고, 그 정의는
#   `startswith("data_source=probe")` 라 `data_source=drill;…` 을 **안 거른다** —
#   그래서 drill 은 **아무 코드도 안 고치고** 세어진다. 세종이 이름으로 금지한 것이
#   그 반대다: `include_drill` 같은 매개변수를 새로 만들면, 세는 법이 **부르는 자리마다**
#   갈라지고 갈라진 쪽이 조용히 이긴다(이 파일이 존재하는 이유).
#
# ⚠ 그래서 `exclude_probe` 는 **위에서 한 글자도 바뀌지 않았다.** 이 절이 더하는 것은
#   「이 행이 훈련인가」를 **읽는 쪽**이 물을 수 있는 한 줄뿐이다.

#: 훈련 표식의 머리. 값은 `stream_monitors.services.drill.DATA_SOURCE`(="drill")와
#: **같은 낱말**이다 — 창 판정(UX-17)과 행 표식(P-201)은 **같은 것을 가리킨다**:
#: 「이것은 훈련이다」. 두 축이 한 낱말로 모여야 화면이 한 배지를 그린다.
DRILL_MARKER = "data_source=drill"

#: `DetectionEvent.track_id` 상한 [실측 models.py `max_length=64`]. 넘기면 DB 가 자르고,
#: **자른 표식은 표식이 아니다** — `scripts/probe_marks.py::TRACK_ID_MAX` 와 같은 수다.
TRACK_ID_MAX = 64


def is_drill_track(track_id) -> bool:
    """이 행이 **훈련으로 심긴 것인가** — 한 줄짜리 정본.

    `is_probe_track` 과 **같은 규약**이다: 앞에서만 센다 · `None`·빈 문자열은 훈련이
    아니다. 다만 기울기가 반대다 — probe 는 「모르면 세는 쪽」(빠뜨리면 일감이 사라진다)
    이고, drill 은 **「모르면 실운영 쪽」**이다: 실운영 사건을 훈련으로 잘못 읽으면
    **진짜 경보에 「훈련」 배지가 붙고**, 그 배지를 본 관제요원은 손을 늦춘다.
    """
    return bool(track_id) and str(track_id).startswith(DRILL_MARKER)


def drill_mark(run_id: str = "") -> str:
    """심는 쪽이 `track_id` 에 적을 규약 문자열.

    **길이를 여기서 검사한다** — 넣는 쪽마다 검사하면 한 곳이 빠지고, 빠진 곳에서
    64자가 잘려 나간다(`probe_marks.mark_string` 과 같은 판단).
    """
    s = f"{DRILL_MARKER};run={run_id}" if run_id else DRILL_MARKER
    if len(s) > TRACK_ID_MAX:
        raise ValueError(
            f"훈련 표식이 {len(s)}자 — track_id 상한 {TRACK_ID_MAX}자를 넘는다: {s!r}")
    return s
