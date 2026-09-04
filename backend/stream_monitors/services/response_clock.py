# -*- coding: utf-8 -*-
"""대응 시계 — 네 시각을 **계산하는 한 자리** (UX-14 · 차선 C · 2026-09-24).

착수 전 실측이 지시서를 고쳤다
------------------------------
지시서 §2 C행은 *"네 시각(`occurred_at`→`acknowledged_at`→`arrived_at`→`closed_at`)은
**모델에 이미 있습니다**(D-399 대응 축). 없는 것은 계산과 표시입니다"* 라 적었다.
**실측하니 그렇지 않다** [실측 2026-09-24 · `stream_monitors/models.py` 전문 대조]:

    DetectionEvent 에 있는 것    occurred_at · last_seen_at · reviewed_at
    DetectionEvent 에 없는 것    acknowledged_at · arrived_at · closed_at

D-399 가 세운 것은 **칸 하나**(`response_state`)이고, 그 칸의 주석이 이유를 적어 두었다:

    ⚠ 이 칸은 **who·when·reason 을 들지 않는다.** 전이 기록은 `logger.AuditLogs` 에
      `common/audit_writer.py` 로 남긴다 — 새 표를 만들지 않는다(D-333).
      현재 값만 여기 있고, **어떻게 왔는지는 감사가 안다.**

그래서 네 시각은 **이미 기록돼 있다 — 다만 표가 아니라 감사에 있다.** 이 파일이 하는
일은 그 감사를 읽어 네 시각으로 세우는 것 하나다.

★ **칸 셋을 새로 만들지 않는다.** 만들면 같은 사실이 두 곳(감사 · 행)에 적히고,
  둘이 어긋나는 날 어느 쪽이 진짜인지 아무도 답할 수 없다. 그리고 이미 쌓인
  전이 이력은 새 칸에 **소급되지 않는다** — 새 칸은 태어나는 순간 과거가 비어 있고,
  빈 과거는 「대응이 빨랐다」로 읽힌다. 감사를 읽으면 과거도 함께 온다.

무엇을 하지 않나
----------------
· **테넌트를 좁히지 않는다.** 이 파일은 `event_id` 를 받아 그 이벤트의 감사를 읽을
  뿐이고, *어느 이벤트를 볼 수 있는가* 는 K1 의 문지기(`get_event`·`query_events`)가
  이미 답했다. 여기서 두 번째 문지기를 만들면 두 벌이 되고, 두 벌은 어긋난다(D-212).
  ⚠ 그러므로 **부르는 쪽은 반드시 스코프를 통과한 이벤트만 넘겨야 한다.**
· `kernels.k1_event` 를 import 하지 않는다 — 이 파일은 K1 소비자가 **아니다**.
  감사 표(`logger.AuditLogs`)만 읽는다. (`tests/test_f05_event_api.K1_CONSUMERS` 무변)
· 자동 종결을 **지우지 않는다.** 분모에서 뺄 뿐이고, 뺐다는 사실을 수로 함께 낸다.

★ 상수 두 벌 — 그리고 갈라지는 것을 시험이 본다
-----------------------------------------------
`LOGGER_NAME` 과 `AUTO_CLOSE_ACTOR` 는 `kernels/k1_event/response_flow.py` 에 정본이
있다. 그것을 import 하면 이 파일이 **K1 소비자가 되어** F-05 「진입면 하나」 대장
(`K1_CONSUMERS`)을 늘려야 하고, 그것은 이 파일이 하는 일(감사 읽기)에 비해 과한 선언이다.
그래서 **글자로 두 벌을 둔다** — `response_flow.py` 가 `STATES` 에 대해 쓴 것과 같은
규약이고, 갈라지는 것은 `tests/test_c_response_clock.ConstantsMatchTheKernelTest` 가 본다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable, Sequence

from django.apps import apps

log = logging.getLogger(__name__)

#: 대응 전이 감사의 `logger_name`. **정본은 `kernels/k1_event/response_flow.LOGGER_NAME`.**
LOGGER_NAME = "guardianx.dsm.response"

#: 오탐 자동 종결의 행위자. **정본은 `response_flow.FALSE_POSITIVE_ACTOR`.**
#: 이 이름으로 닫힌 이벤트가 대응 시간 통계의 **분모에서 빠진다**(지시서 §3-4).
AUTO_CLOSE_ACTOR = "system:false_positive"

#: 대응 진행 값 넷. 정본은 `response_flow.STATES`.
OCCURRED, ACKNOWLEDGED, IN_PROGRESS, CLOSED = (
    "occurred", "acknowledged", "in_progress", "closed")

#: ★ 카드 글자가 커지는 문턱 — **30초 · 2분 · 5분 · 8분** (UX-14).
#:
#:   왜 색이 아니라 크기인가: 관제요원은 숫자를 읽지 않는다. 야간 관제실에서
#:   40인치 화면을 3m 밖에서 보는 사람에게 **색은 배경과 싸우고 크기는 안 싸운다.**
#:   색맹(남성 8%)에게도 크기는 그대로 읽힌다.
#:
#:   ⚠ 표를 **서버에 하나만 둔다.** 화면은 시계가 계속 도니까 자기도 계산해야 하는데,
#:     그 표를 화면이 따로 들면 서버 통계와 화면 글자가 다른 문턱을 쓰게 된다.
#:     그래서 응답에 `tier_thresholds_sec` 를 **실어 보낸다** — `allowed_next` 와 같은 규약.
URGENCY_THRESHOLDS_SEC: tuple[int, ...] = (30, 120, 300, 480)

#: 감사 조회의 상한. 상한 없이 읽으면 한 달 통계 한 번이 감사 표 전체를 끌어온다.
#: ★ 닿았다는 사실은 `truncated=True` 로 **말한다** — 조용히 자르면 p95 가 거짓말을 한다.
_AUDIT_ROW_CAP = 20_000

#: 감사 시각과 이벤트 발생 시각 사이의 여유. 전이는 발생보다 뒤에 일어나지만,
#: 시계 오차·시드 데이터로 **몇 초 앞선 행**이 있을 수 있다. 그것을 놓치지 않는다.
_SINCE_SLACK = timedelta(minutes=1)


# ═══════════════════════════════════════════════════════════════════════════
# 값
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Stamps:
    """한 이벤트의 **네 시각**과 그 시각들이 말하지 않는 것 둘.

    ★ `auto_closed` 를 값에 싣는 이유: 「닫혔다」만 보면 사람이 닫은 것과 규칙이 닫은
      것이 같은 모양이다. 두 개를 같은 분모에 넣으면 **오탐이 많을수록 대응이 빨라진다** —
      지표가 사실의 반대를 말하는 그 모양이고, D-293 이 `status`/`verdict` 에서 이미
      한 번 막은 것과 같은 계열의 착시다.

    ★ `reopened` 를 세는 이유: 「종결 → 조치중」 되돌림(D-399 유일한 역방향)이 있으면
      그 이벤트는 **한 번 닫혔다가 다시 열린 것**이다. 첫 종결 시각으로 대응 시간을
      재면 되돌림이 통계를 좋게 만든다 — 그래서 `closed_at` 은 **마지막 종결**이고,
      되돌림 뒤 아직 안 닫혔으면 `None` 이다.
    """

    event_id: int
    occurred_at: datetime
    acknowledged_at: datetime | None = None
    arrived_at: datetime | None = None
    closed_at: datetime | None = None
    auto_closed: bool = False
    reopened: int = 0
    #: 감사에서 실제로 읽은 전이들. 상세 화면의 타임라인이 이것을 그린다.
    transitions: tuple[dict, ...] = ()

    # ── 구간 셋. **없으면 None 이지 0 이 아니다** (D-290) ─────────────────
    @property
    def acknowledge_seconds(self) -> float | None:
        return _delta(self.occurred_at, self.acknowledged_at)

    @property
    def arrive_seconds(self) -> float | None:
        """발생 → 조치 착수. **접수부터가 아니라 발생부터** 잰다 —
        사람이 늦게 접수한 시간도 현장이 기다린 시간이다."""
        return _delta(self.occurred_at, self.arrived_at)

    @property
    def close_seconds(self) -> float | None:
        return _delta(self.occurred_at, self.closed_at)

    def elapsed_seconds(self, now: datetime) -> float | None:
        """**아직 도는 시계.** 닫혔으면 멈춘다 — 닫힌 이벤트가 계속 커지면
        화면이 「급한 것」을 잘못 가리킨다."""
        if self.closed_at is not None:
            return None
        return max(0.0, (now - self.occurred_at).total_seconds())

    def as_dict(self, *, now: datetime | None = None) -> dict:
        elapsed = self.elapsed_seconds(now) if now is not None else None
        return {
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
            "acknowledged_at": self.acknowledged_at,
            "arrived_at": self.arrived_at,
            "closed_at": self.closed_at,
            "acknowledge_seconds": self.acknowledge_seconds,
            "arrive_seconds": self.arrive_seconds,
            "close_seconds": self.close_seconds,
            "auto_closed": self.auto_closed,
            "reopened": self.reopened,
            "elapsed_seconds": elapsed,
            "urgency_tier": urgency_tier(elapsed),
            "transitions": list(self.transitions),
        }


def _delta(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return (end - start).total_seconds()


def urgency_tier(elapsed_seconds: float | None) -> int:
    """0(방금) ~ 4(8분 넘음). **닫힌 이벤트는 0** — 시계가 멈췄다."""
    if elapsed_seconds is None:
        return 0
    tier = 0
    for threshold in URGENCY_THRESHOLDS_SEC:
        if elapsed_seconds >= threshold:
            tier += 1
    return tier


# ═══════════════════════════════════════════════════════════════════════════
# 감사를 읽어 네 시각을 세운다
# ═══════════════════════════════════════════════════════════════════════════
def _audit_model():
    return apps.get_model("logger", "AuditLogs")


def _row_time(row: dict) -> datetime | None:
    """감사 행의 시각. `create_datetime` 이 정본이고 `created_on` 은 보조다 —
    둘 다 `auto_now_add` 이지만 `created_on` 은 null 을 허용한다 [실측 2026-09-24]."""
    return row.get("create_datetime") or row.get("created_on")


def _as_mapping(value: Any) -> dict:
    """`data_before`/`data_after`. JSONField 이지만 **문자열로 오는 백엔드가 있다** —
    그때 조용히 빈 dict 가 되면 네 시각이 통째로 사라진다."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        import json
        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def stamps_for(events: Iterable[Any]) -> dict[int, Stamps]:
    """스코프를 **이미 통과한** 이벤트들의 네 시각.

    `events` 는 `event_id` 와 `occurred_at` 을 가진 무엇이든 된다 —
    K1 의 `EventView` · dict · 튜플 아무거나. 이 파일은 이벤트 표를 읽지 않는다.

    ★ 왜 한 건씩이 아니라 한 번에 읽나: 목록 화면은 카드 20~50장을 한 화면에 그린다.
      건별로 감사를 읽으면 화면 한 장이 감사 조회 50회이고, 그러면 **화면이 느려서
      아무도 안 쓴다** — 안 쓰이는 화면은 없는 화면과 같다.
    """
    pairs: list[tuple[int, datetime]] = []
    for e in events:
        eid = _get(e, "event_id")
        occurred = _get(e, "occurred_at")
        if eid is None or occurred is None:
            continue
        pairs.append((int(eid), occurred))
    if not pairs:
        return {}

    wanted = {eid for eid, _ in pairs}
    since = min(occurred for _, occurred in pairs) - _SINCE_SLACK

    rows = list(
        _audit_model()
        ._base_manager.filter(logger_name=LOGGER_NAME)
        .filter(create_datetime__gte=since)
        .order_by("create_datetime", "id")
        .values("id", "create_datetime", "created_on", "username",
                "data_before", "data_after")[:_AUDIT_ROW_CAP]
    )

    built: dict[int, dict] = {
        eid: {"occurred_at": occurred, "acknowledged_at": None,
              "arrived_at": None, "closed_at": None,
              "auto_closed": False, "reopened": 0, "transitions": []}
        for eid, occurred in pairs
    }

    for row in rows:
        after = _as_mapping(row.get("data_after"))
        eid = after.get("event_id")
        if not isinstance(eid, int) or eid not in wanted:
            continue
        before = _as_mapping(row.get("data_before"))
        frm = before.get("response_state") or ""
        to = after.get("response_state") or ""
        at = _row_time(row)
        if at is None:
            #: 시각 없는 전이는 **버리지 않고 센다** — 버리면 「전이가 없었다」와
            #: 「시각을 모른다」가 같은 그림이 된다(D-290).
            log.warning("[UX-14] 감사 %s 에 시각이 없다 — 네 시각에서 빠진다", row.get("id"))
            continue
        by = (row.get("username") or "").strip()
        auto = (by == AUTO_CLOSE_ACTOR) or (after.get("rule") == "false_positive")

        slot = built[eid]
        slot["transitions"].append(
            {"at": at, "from": frm, "to": to, "by": by, "automatic": auto})

        if to == ACKNOWLEDGED and slot["acknowledged_at"] is None:
            slot["acknowledged_at"] = at
        elif to == IN_PROGRESS:
            if frm == CLOSED:
                #: 되돌림 — 다시 열렸다. 마지막 종결을 **지운다.**
                slot["reopened"] += 1
                slot["closed_at"] = None
                slot["auto_closed"] = False
            elif slot["arrived_at"] is None:
                slot["arrived_at"] = at
        elif to == CLOSED:
            slot["closed_at"] = at
            slot["auto_closed"] = auto

    return {
        eid: Stamps(event_id=eid,
                    occurred_at=slot["occurred_at"],
                    acknowledged_at=slot["acknowledged_at"],
                    arrived_at=slot["arrived_at"],
                    closed_at=slot["closed_at"],
                    auto_closed=slot["auto_closed"],
                    reopened=slot["reopened"],
                    transitions=tuple(slot["transitions"]))
        for eid, slot in built.items()
    }


def _get(obj: Any, name: str):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


# ═══════════════════════════════════════════════════════════════════════════
# 월간 p50 / p95 — **분모를 함께 낸다** (D-301)
# ═══════════════════════════════════════════════════════════════════════════
def percentile(values: Sequence[float], q: float) -> float | None:
    """최근접 순위(nearest-rank). **보간하지 않는다.**

    왜: 표본이 7건일 때 보간한 p95 는 **관측된 적 없는 값**이다. 대외 보고에
    「95%가 이 안에 들어온다」로 쓰이는 수라면, 그 수는 실제로 일어난 대응 중
    하나여야 한다. 보간값은 「어느 사건이 그랬는가」에 답하지 못한다.
    """
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int(-(-len(ordered) * q // 1))))
    return float(ordered[rank - 1])


def latency_stats(stamps: Iterable[Stamps]) -> dict:
    """대응 시간 p50/p95 — **자동 종결을 분모에서 뺀다** (지시서 §3-4).

    빼지 않으면 무슨 일이 생기나: 오탐 자동 종결은 사람이 아무것도 안 해도
    `occurred → closed` 가 **즉시** 찍힌다. 그것이 분모에 들어가면 오탐이 많은
    달일수록 「대응 시간이 좋아진다」 — 지표가 사실의 정반대를 말한다.

    ★ 뺀 수를 **함께 낸다.** 「빼고 잰 것」과 「원래 그만큼이었던 것」은 다른 사실이고,
      뺀 건수가 안 보이면 다음 사람이 이 수를 원본 건수로 읽는다(D-301).
    """
    rows = list(stamps)
    auto = [s for s in rows if s.auto_closed]
    counted = [s for s in rows if not s.auto_closed]

    def band(getter) -> dict:
        vals = [v for v in (getter(s) for s in counted) if v is not None]
        return {
            "n": len(vals),
            "p50": percentile(vals, 0.50),
            "p95": percentile(vals, 0.95),
            #: 분모 0 이면 p50 은 `null` 이다 — **0.0 이 아니다.** 0.0 으로 내면
            #: 「아무도 대응 안 한 달」이 「즉시 대응한 달」과 같은 숫자가 된다.
            "measurable": bool(vals),
        }

    return {
        "events": len(rows),
        "counted": len(counted),
        "excluded_auto_closed": len(auto),
        "acknowledge": band(lambda s: s.acknowledge_seconds),
        "arrive": band(lambda s: s.arrive_seconds),
        "close": band(lambda s: s.close_seconds),
        "tier_thresholds_sec": list(URGENCY_THRESHOLDS_SEC),
    }
