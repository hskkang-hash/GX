# -*- coding: utf-8 -*-
"""대응 진행 축의 **전이 규칙과 감사를 쥔 한 자리** (D-399).

왜 이 파일이 생겼나
-------------------
지시서(세종 2026-09-14)가 「이벤트 상태를 4값으로」 를 냈고, 착수 전 실측에서
**이미 4값**이 나왔다 [실측 2026-09-14]. 다만 두 4값이 **다른 것을 묻는다**:

    DetectionEvent.status          「이 탐지가 진짜인가」   신규 → 확인/기각 → 종료
    DetectionEvent.response_state  「사람이 어디까지 했나」 발생 → 확인 → 조치중 → 종결

지시서의 값을 `status` 에 밀어 넣으면 판정과 대응이 한 칸에 섞인다. 그것이
D-293 이 `status` 와 `verdict` 를 가른 이유이고, 섞여 있던 동안 종료가 쌓일수록
오탐률이 **저절로 좋아졌다.** 그래서 축을 하나 더 세웠다 (D-399 ⓐ).

어디에 사는가 — **커널(K1)이다**
--------------------------------
1차판은 이 파일을 `apps/dsm/` 에 두었고 `tests/test_dsm_app.AppStaysThinTest` 가
**즉시 빨개졌다** — App 이 `_base_manager` 를 만지고 있었기 때문이다. 그 지적이 옳다:
`DetectionEvent` 의 수명주기는 K1 의 것이고, `review_event`·`close_event` 가 이미
여기 산다. 대응 진행만 App 에 두면 **같은 표의 규칙이 두 층에 흩어진다.**
App 은 이제 이것을 부르고 **예외를 HTTP 로 번역할 뿐**이다.

무엇을 하지 않나
----------------
· **새 감사 표를 만들지 않는다** (D-333). `logger.AuditLogs` 가 이미 있고,
  쓰는 손은 `common/audit_writer.py` 하나다 (D-325 표 ②).
· `response_state` 를 직접 대입하는 두 번째 자리를 만들지 않는다. 규칙이 두 벌이
  되면 반드시 어긋나고, 판정식 복사본 하나가 격리 사고의 원인이었다 (D-212).
· **거절을 200 으로 내지 않는다.** 여기서 던지는 예외를 `api.py` 가 4xx 로 번역한다.
  `200 + {"success": false}` 는 착시 ⑧이고 이 App 이 처음부터 금지한 것이다.

되돌림을 하나만 두는 이유
-------------------------
「종결 → 조치중」 하나뿐이다. 되돌림을 넓게 열면 **감사 이력이 이야기를 잃는다** —
앞뒤로 오간 흔적만 남고 "지금 어디까지 왔나" 를 아무도 말할 수 없게 된다.
그 하나에도 **사유가 필수**다: 무엇에서 무엇으로는 표가 알고 **왜** 는 여기서만 들어온다.
"""
from __future__ import annotations

from typing import Any

from django.db import transaction

from common import audit_writer
from common.audit_writer import AuditEntry
from common.tenant_scope import TenantScope
from kernels.k1_event.exceptions import (
    ResponseTransitionForbidden,
    ResponseTransitionNeedsManager,
    ResponseTransitionNeedsReason,
)
from kernels.k1_event.services import _model

#: ⚠ 값을 **글자로** 적는다. `_model(...)` 은 `apps.get_model` 이라 모듈 import 시각에는
#:   아직 앱이 안 서 있다 — 여기서 부르면 기동 순서에 따라 죽는다.
#:   그러면 **정본과 두 벌이 되는데**, 그 두 벌이 어긋나는 것을 시험이 막는다:
#:   `tests/test_response_flow.StatesMatchTheModelTest` 가 모델의 값과 글자로 대조한다.
#:   「두 벌을 두되 갈라지는 것을 시험이 본다」 — 이 저장소가 쓰는 방식이다(D-337 계열).
OCCURRED = "occurred"
ACKNOWLEDGED = "acknowledged"
IN_PROGRESS = "in_progress"
CLOSED = "closed"
STATES = (OCCURRED, ACKNOWLEDGED, IN_PROGRESS, CLOSED)

#: 감사 행의 `logger_name`. **이 문자열로 대응 전이 전건을 뽑는다** —
#: 이름이 하나여야 「전건」이라는 말이 성립한다 (D-285 ②).
LOGGER_NAME = "guardianx.dsm.response"
TAG = "[RESP]"

#: ★ 오탐 자동 종결의 **행위자** (P-16). 감사에 사람 이름이 아니라 이 이름이 남는다 —
#:   U1 이 누른 것은 「오탐」이고 「종결」은 **규칙이 한 일**이다. 둘을 같은 행위자로
#:   적으면 감사가 「그 사람이 닫았다」고 말하게 되고, 그것은 일어난 일이 아니다.
#:   ⚠ 행위자가 시스템이라고 해서 **테넌트가 없어지는 것이 아니다** — 문지기는
#:     판정자의 스코프로 지난다(아래 `close_as_false_positive` 첫 줄).
FALSE_POSITIVE_ACTOR = "system:false_positive"


class _SystemActor:
    """감사 한 줄에 쓸 **이름뿐인 행위자.** `audit_writer` 는 `pk` 와 `username` 만 본다.

    가짜 사용자 행을 만들지 않는 이유: DB 에 사람이 아닌 사람이 생기면 권한·통계·
    로그인이 전부 그 행을 사람으로 세게 된다. 이름만 남기는 것으로 충분하다.
    """

    pk = None
    username = FALSE_POSITIVE_ACTOR


#: 허용 전이. **앞으로만 간다** — 건너뛰기 없음.
#: `occurred → closed` 직행을 넣지 않은 이유: 접수한 사람이 없는 종결이 생기고,
#: 그러면 「아무도 안 봤는데 닫힌 이벤트」와 「보고 닫은 이벤트」가 같아진다 (D-290).
FORWARD: dict[str, str] = {
    OCCURRED: ACKNOWLEDGED,
    ACKNOWLEDGED: IN_PROGRESS,
    IN_PROGRESS: CLOSED,
}

#: 유일한 되돌림. 관제팀장(U2)만, 사유 필수.
BACKWARD: dict[str, str] = {CLOSED: IN_PROGRESS}

#: 되돌림을 할 수 있는 프리셋. K3 가 이미 역할→프리셋을 판정하므로 **여기서 역할을
#: 다시 해석하지 않는다** — 해석이 두 벌이 되면 어긋난다 (D-212).
MANAGER_PRESETS = ("MANAGER", "EXECUTIVE")


def _allowed_next(current: str) -> tuple[str, ...]:
    """지금 상태에서 갈 수 있는 곳.

    ★ 이름 앞에 `_` 가 붙은 이유 [실측 2026-09-14]: 게이트 `gx-tenant-scope` 가
      1차판을 **반려했다** — 「커널 공개 함수인데 `*, scope` 가 없다」. 옳은 지적이다.
      이건 **표 조회일 뿐 데이터를 내지 않지만**, 게이트는 그것을 구별할 수 없고
      구별하려 드는 순간 예외 목록이 생긴다. 예외 목록은 자란다.
      밖에서 부를 일이 없으므로 **공개 면이 아니라고 말하는 쪽**이 옳다 —
      값은 `advance_response`·`response_state` 가 스코프를 받고 실어 낸다.
    """
    out = []
    if current in FORWARD:
        out.append(FORWARD[current])
    if current in BACKWARD:
        out.append(BACKWARD[current])
    return tuple(out)


def _is_manager(scope: TenantScope) -> bool:
    from kernels.k3_dashboard.services import get_preset
    return get_preset(scope=scope).preset in MANAGER_PRESETS


def advance_response(event_id: int, *, to_state: str, reason: str = "",
                     scope: TenantScope) -> dict:
    """대응 진행을 한 칸 옮긴다. **거절은 예외로 나간다** (App 이 4xx 로 번역).

    ★ **문지기를 새로 만들지 않는다.** 남의 테넌트 이벤트를 거르는 판정은 이미
      `get_event` 에 있다(404 · IDOR). 쓰기 전에 **읽기 문지기를 그대로 통과시키는 것**
      이 첫 줄이 하는 일이다 — 두 벌이 어긋난 자리가 D-212 의 격리 사고였다.

    ★ 감사가 먼저다. 감사에 남길 수 없으면 그 전이는 **일어나지 않는 것이 옳다** —
      `apps/dsm/audit.py` 가 설정 변경에 대해 정한 것과 같은 성질의 행위다.
      (화재 판정은 메일이 죽어도 살아야 하지만, 사람의 조치 기록은 그렇지 않다)
    """
    from kernels.k1_event.services import get_event

    get_event(event_id, scope=scope)          # 남의 것이면 여기서 404 가 난다
    Event = _model("DetectionEvent")
    event = Event._base_manager.get(pk=event_id)

    frm = event.response_state
    if to_state not in STATES:
        raise ResponseTransitionForbidden(
            frm=frm, to=to_state,
            why=f"{to_state!r} 은 대응 진행 값이 아니다. 허용: {list(STATES)}")

    backward = BACKWARD.get(frm) == to_state
    if FORWARD.get(frm) != to_state and not backward:
        raise ResponseTransitionForbidden(
            frm=frm, to=to_state,
            why=("앞으로만 간다. 건너뛰기와 되감기는 없다 — 되돌림은 "
                 "「종결 → 조치중」 하나뿐이다. "
                 f"지금 갈 수 있는 곳: {list(_allowed_next(frm)) or '없음(끝)'}"))

    if backward:
        if not reason.strip():
            raise ResponseTransitionNeedsReason(frm=frm, to=to_state)
        if not _is_manager(scope):
            raise ResponseTransitionNeedsManager(frm=frm, to=to_state)

    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=scope.actor,
        action=f"response.{frm}->{to_state}",
        outcome=audit_writer.ALLOWED,
        reason=reason.strip() or f"대응 진행 {frm} → {to_state}",
        before={"event_id": event.id, "response_state": frm},
        after={"event_id": event.id, "response_state": to_state},
        api_name="dsm.events.response", api_method="POST", status_http=200,
    )
    #: ★ 한 칸만 쓴다. `save()` 전체를 부르면 이 요청과 무관한 칸들이 함께 나가고,
    #:   동시에 들어온 다른 쓰기를 덮는다.
    event.response_state = to_state
    event.save(update_fields=["response_state"])
    return {
        "event_id": event_id, "from": frm, "to": to_state,
        "allowed_next": list(_allowed_next(to_state)),
        "audit_id": entry.audit_id,
    }


@transaction.atomic
def close_as_false_positive(event_id: int, *, reason: str = "",
                            scope: TenantScope) -> dict:
    """오탐 판정에 따라 대응 축을 **끝까지 닫는다** (P-16 · 소비자만 부른다).

    ★ 왜 `advance_response` 로 못 하나 — 전이표는 **앞으로 한 칸씩**만 허용한다
      (`occurred → acknowledged → in_progress → closed`). 오탐은 그 계단을 오르는 일이
      아니라 **계단 자체가 없어지는 일**이다: 아무도 접수하지 않았고 아무도 조치하지
      않았는데 이 이벤트는 끝났다. 그것을 세 번의 가짜 전이로 흉내 내면 감사가
      「누가 접수했다」고 거짓말을 한다.

    ★ 그래도 **이 파일 안**이다. `response_state` 를 대입하는 자리는 여전히 둘뿐이고
      둘 다 여기 있다 — 규칙이 두 층에 흩어지지 않는다(D-212 · D-399).

    ★ 문지기는 **판정자의 스코프**로 지난다. 행위자만 시스템이다. 이 둘을 섞어
      시스템 스코프로 열면 「시스템이 하는 일에는 테넌트가 없다」가 되고, 그것이
      격리의 부재다 (D-281).

    ★ **두 번 불러도 한 번만 일어난다.** 이미 `closed` 면 감사도 쓰지 않고 돌아간다 —
      같은 사실을 두 줄로 적으면 「몇 번 닫혔나」가 세어지지 않는다.
    """
    from kernels.k1_event.services import get_event

    get_event(event_id, scope=scope)          # 남의 것이면 여기서 404 가 난다
    Event = _model("DetectionEvent")
    event = Event._base_manager.get(pk=event_id)

    frm = event.response_state
    if frm == CLOSED:
        return {"event_id": event_id, "from": frm, "to": CLOSED,
                "changed": False, "audit_id": None}

    #: 누가 눌렀는지는 **본문에** 남긴다. 행위자 칸은 규칙의 것이고, 그 규칙을 켠 사람은
    #: 본문에서 읽힌다 — 둘을 한 칸에 넣으면 하나가 지워진다.
    by = getattr(scope.actor, "username", "") or ""
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=_SystemActor(),
        action=f"response.{frm}->{CLOSED}",
        outcome=audit_writer.ALLOWED,
        reason=(reason.strip()
                or f"오탐 판정에 따른 자동 종결 (판정자 {by or '알 수 없음'} · P-16)"),
        before={"event_id": event.id, "response_state": frm},
        after={"event_id": event.id, "response_state": CLOSED,
               "rule": "false_positive", "reviewed_by": by},
        api_name="dsm.events.review", api_method="POST", status_http=200,
    )
    event.response_state = CLOSED
    event.save(update_fields=["response_state"])
    return {"event_id": event_id, "from": frm, "to": CLOSED,
            "changed": True, "audit_id": entry.audit_id,
            "allowed_next": list(_allowed_next(CLOSED))}


def response_state(event_id: int, *, scope: TenantScope) -> dict:
    """지금 어디까지 왔나 + 갈 수 있는 곳.

    ★ `allowed_next` 를 함께 내는 이유: 화면이 자기 전이표를 따로 들면 **서버가
      거절하는 버튼을 그리게 된다.** 표는 여기 하나만 둔다.
    """
    from kernels.k1_event.services import get_event

    get_event(event_id, scope=scope)
    current = _model("DetectionEvent")._base_manager.values_list(
        "response_state", flat=True).get(pk=event_id)
    return {"response_state": current, "allowed_next": list(_allowed_next(current))}
