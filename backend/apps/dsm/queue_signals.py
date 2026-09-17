# -*- coding: utf-8 -*-
"""큐 카드의 **현장 신호** — 「지원 요청」과 「조치 완료」 (차선 U1 · 턴 S).

무엇을 답하는가
---------------
관제요원의 큐 카드는 지금 **탐지의 사실**만 말한다(등급·유형·경과·처리 단계).
현장에서 돌아온 말은 그 화면에 한 자도 없다. 그래서 두 가지가 안 보인다:

    ① **지원 요청** — 현장이 「혼자 못 한다」고 했다. 큐에서 가장 먼저 눈에 띄어야 한다.
    ② **조치 완료** — 현장이 끝났다고 했다. 관제는 그것을 보고 **종결**을 누른다.

둘 다 이미 있는 문(`POST …/field-reply`)으로 들어오는 **한 줄**이고, 이 모듈은 그
한 줄들을 카드별로 **분류해 줄 뿐**이다. 새 표도 새 상태 축도 만들지 않는다.

★ **커널을 직접 부르지 않는다.** 회신 읽기는 `apps.dsm.services.field_replies`
  하나로만 간다 — F-05 의 「App 소비자는 `apps/dsm/services.py` 하나」 규약
  (`tests/test_f05_event_api.py::K1_CONSUMERS`)이 그것이다. 그래서 이 파일에는
  `kernels` 라는 낱말이 없다.

★ **문지기는 그 함수가 이미 든다.** `field_replies` 는 이벤트 문지기(`get_event`)를
  먼저 지나므로 남의 테넌트 사건 번호를 물으면 `Http404` 가 난다 — 이 모듈은 그
  404 를 **조용히 건너뛴다**. 「없다」와 「남의 것이다」를 응답에서 가르지 않는 것이
  곧 격리다(존재 여부도 누출이다 — `field.py` 머리말과 같은 판정).

★ **묶어 읽지 않는다 — 사건 번호를 받아 그만큼만 읽는다.** 감사 표 전체를 한 번에
  훑으면 훨씬 싸지만, 그러려면 회신의 `logger_name` 상수를 이 파일이 알아야 하고
  그 상수는 커널의 것이다(위 규약). 그래서 **화면이 지금 그린 카드의 id 만** 받아
  그 수만큼 읽는다 — 상한(`MAX_EVENT_IDS`)이 그 비용의 천장이다.

분류를 무엇으로 하는가 — **두 후보를 다 받는다** [턴 S · 배선 대기]
-------------------------------------------------------------------
U3 차선의 M3 설계(`docs/workorders/WO-GX-20260915-01/U3_M3_시트_설계.md` §1)는
「지원 요청」을 담는 방법을 **둘 중 하나로 다음 파에 고른다**고 적고 이름만 올렸다:

    (가) 회신 본문에 **정형 접두** — `[지원요청] 사다리차 필요`
    (나) 회신 행에 **종류 칸**(`kind`) — `{"kind": "support_request", …}`

이 모듈은 **둘 다 읽는다.** 하나를 고르는 것은 스키마 판단이고 U3·조율자의 자리다 —
고르기 전에 화면이 서야 하므로, 읽는 쪽이 둘을 다 받아 두면 **어느 쪽으로 정해져도
화면은 이미 그것을 그린다.** 그리고 응답은 **무엇으로 읽혔는지**(`wired`)를 함께
낸다: 아직 아무 회신도 종류를 달고 오지 않았다면 그 사실이 「데이터 없음」이 아니라
**「배선 대기」**라는 것을 화면이 말할 수 있어야 한다. 둘은 다른 사실이다 —
앞은 「현장이 아무 말도 안 했다」이고 뒤는 「말은 왔는데 우리가 종류를 못 읽는다」다.

⚠ `kind` 는 `field_replies` 의 값(`FieldReply`)에 **아직 없는 칸**이다(턴 S 실측).
  그래서 (나)는 값에 그 이름이 생기는 날 저절로 살아난다 — `getattr` 로 묻고,
  없으면 없는 대로 (가)만으로 판정한다. 없는 칸을 있는 척하지 않는다.

배선됨 — U3 가 고른 길은 (다) **저장 문자열의 정형 접두** [턴 T · 실측]
-----------------------------------------------------------------------
U3 는 둘 중 어느 쪽도 아닌 셋째 길로 갔다: `POST …/field-reply?kind=done` 이
저장 문자열 머리에 `[FIELD:done] ` 를 붙이고(`apps/dsm/field.py::compose_reply`),
읽는 쪽은 `field.split_reply()` 로 종류와 깨끗한 본문을 되찾는다. 이 모듈은 그
**같은 함수**로 읽는다 — 접두 문법을 여기서 다시 적지 않는다(두 벌은 갈린다).
(가)·(나)는 그대로 둔다: 되읽기는 좁히지 않는다.

★ 사람의 자리에 접두가 보이면 그 판정의 실패다(`field.py` 머리말) — 그래서 이
  모듈이 내는 본문(`support_text`·`action_done_text`·`last_text`)은 **깨끗한
  본문**이다.

★ **닫힌 사건은 종결 확인 카드에서 빠진다.** 종결은 서버 기록(`response_state`)이
  닫는 것이고(불변 「온보딩 카드의 완료는 서버 기록이 닫는다」), 카드는 그 기록을
  되읽어 그린다 — 회신이 남아 있어도 기록이 `closed` 면 `action_done` 은 거짓이다.
  그래서 「확인 → 기록 닫힘 → 재조회 0」이 서버에서 선다.
"""
from __future__ import annotations

from typing import Any

from django.http import Http404

from apps.dsm import field, services

#: 종결된 기록의 상태 이름. 커널 상수(`kernels.k1_event.response_flow.CLOSED`)와 같은
#: 값이지만 커널을 import 하지 않는다(F-05 — App 소비자는 `services` 하나).
#: 갈리는지는 시험이 본다(`test_u1_queue_field_signals::ConfirmDoneTest`).
CLOSED_STATE = "closed"
OCCURRED_STATE = "occurred"

#: 한 번에 물을 수 있는 사건 수의 천장. 화면이 그리는 카드 수(초점 1 + 대기 몇 장)를
#: 넘길 이유가 없다 — 큐 전체(200)를 물으면 그만큼 읽기가 나간다.
MAX_EVENT_IDS = 30

#: 한 사건에서 볼 회신 수. 「마지막에 뭐라고 했나」가 이 화면의 물음이라 깊게 안 판다.
REPLY_LOOKBACK = 20

#: (가) 정형 접두 — U3 설계가 예로 든 그 모양. **화면에 보이는 글자 그대로**다.
SUPPORT_MARKERS = ("[지원요청]", "[지원 요청]")
DONE_MARKERS = ("[조치완료]", "[조치 완료]")

#: (나) 종류 칸의 값. 이름은 U3 가 정할 자리이고, 여기 적은 둘은 **받을 준비**다.
SUPPORT_KINDS = ("support_request", "support")
DONE_KINDS = ("action_done", "done", "completed")


def _kind_of(reply: Any) -> str:
    """회신 한 줄의 **종류 칸**. 아직 없는 칸이면 빈 글자다 — 지어내지 않는다."""
    value = getattr(reply, "kind", None)
    return str(value).strip().lower() if value else ""


def _split(reply: Any) -> tuple[str, str]:
    """저장 문자열 → (U3 접두의 종류, 깨끗한 본문). 접두가 없으면 종류는 `note` 다."""
    stored = (getattr(reply, "text", "") or "")
    name, body = field.split_reply(stored)
    return name, body.strip()


def _text_of(reply: Any) -> str:
    """사람의 자리에 놓을 본문 — **접두를 뗀** 것."""
    return _split(reply)[1]


def _starts_with_marker(text: str, markers: tuple[str, ...]) -> bool:
    head = text.lstrip()
    return any(head.startswith(m) for m in markers)


def classify(reply: Any) -> str:
    """회신 한 줄 → `"support"` · `"done"` · `""`(그냥 한 줄).

    ★ **순수 함수다** — 시험이 DB 없이 이 갈래 전부를 잰다. 세 후보(칸 · U3 저장
      접두 · 화면 접두)를 한 자리에서 읽으므로, 어느 쪽으로 정해지든 고칠 자리가 하나다.
    """
    kind = _kind_of(reply)
    if kind in SUPPORT_KINDS:
        return "support"
    if kind in DONE_KINDS:
        return "done"

    #: (다) U3 가 실제로 쓰는 길 — `[FIELD:done] …`. `note` 는 「그냥 한 줄」이다.
    stored_kind, text = _split(reply)
    if stored_kind in SUPPORT_KINDS:
        return "support"
    if stored_kind in DONE_KINDS:
        return "done"

    if _starts_with_marker(text, SUPPORT_MARKERS):
        return "support"
    if _starts_with_marker(text, DONE_MARKERS):
        return "done"
    return ""


def _signal_for(*, scope, event_id: int) -> dict | None:
    """한 사건의 신호 한 줄. 남의/없는 사건이면 `None` — 그 둘을 가르지 않는다."""
    try:
        replies = services.field_replies(
            scope=scope, event_id=event_id, limit=REPLY_LOOKBACK)
    except Http404:
        # ★ 남의 테넌트 사건도 없는 사건도 여기로 온다. **같은 답을 준다.**
        return None

    #: 서버 기록 — 종결 확인 카드가 되읽는 값. 문지기는 위에서 이미 지났다.
    state = services.response_state(scope=scope, event_id=event_id)
    response_state = str(state.get("response_state") or "")
    allowed_next = list(state.get("allowed_next") or [])
    is_closed = response_state == CLOSED_STATE

    support_text = ""
    done_text = ""
    last_text = ""
    last_author = ""
    typed = 0

    #: `field_replies` 는 최신이 앞이다(`order_by("-id")`). 마지막 말이 첫 줄이다.
    for index, reply in enumerate(replies):
        if index == 0:
            last_text = _text_of(reply)
            last_author = (getattr(reply, "author_name", "") or "").strip()
        mark = classify(reply)
        if mark:
            typed += 1
        if mark == "support" and not support_text:
            support_text = _text_of(reply)
        elif mark == "done" and not done_text:
            done_text = _text_of(reply)

    return {
        "event_id": event_id,
        "reply_total": len(replies),
        #: 종류를 달고 온 회신 수. 0이면 이 사건에 대해서는 **분류를 못 한 것**이지
        #: 「현장이 지원을 안 청한 것」이 아니다 — 화면이 그 둘을 다르게 적는다.
        "typed_total": typed,
        "support_requested": bool(support_text),
        "support_text": support_text,
        #: ★ 「조치 완료」는 **기록이 아직 열려 있을 때만** 카드가 된다. 닫힌 기록의
        #: 회신은 남아 있어도 확인할 것이 없다 — 그래서 확인 → 닫힘 → 재조회 0 이다.
        "action_done": bool(done_text) and not is_closed,
        "action_done_text": done_text,
        "response_state": response_state,
        "allowed_next": allowed_next,
        "closed": is_closed,
        "last_text": last_text,
        "last_author": last_author,
    }


class ConfirmDoneRejected(Exception):
    """확인할 「조치 완료」가 없다(409) — 회신이 없거나 기록이 이미 닫혀 있다."""


def confirm_done(*, scope, event_id: int) -> dict:
    """종결 확인 카드의 「확인」 — **서버 기록을 닫는다.**

    ★ 규칙은 K1 이 든다. 전이표(`occurred → acknowledged → in_progress → closed` ·
      건너뛰기 없음)·감사·문지기는 전부 `services.advance_response`(그 뒤 K1)에 있고,
      여기서는 그 문을 **갈 수 있는 만큼 앞으로** 부를 뿐이다. `acknowledged` 에서
      누르면 두 칸(조치 착수 → 종결)이 각각 감사에 남는다 — 한 칸으로 접지 않는다.
    ★ `occurred`(아무도 접수 안 함)에서는 닫히지 않는다 — 접수한 사람이 없는 종결은
      K1 이 거절하고(D-290), 이 함수는 그 거절을 좁히지 않는다(409 로 나간다).
    ★ 확인할 것이 없으면(조치 완료 회신 0 · 이미 닫힘) 아무것도 옮기지 않는다 —
      「확인」이 회신 없는 사건을 닫는 단추가 되면 그것은 거짓말이다.

    Returns:
        닫힌 뒤의 신호 한 줄(`_signal_for` 와 같은 모양) + `steps`(옮긴 칸들).
    Raises:
        Http404: 남의/없는 사건(문지기 그대로).
        ConfirmDoneRejected: 확인할 조치 완료가 없다.
        services.ResponseTransitionForbidden 등: K1 의 거절 그대로.
    """
    before = _signal_for(scope=scope, event_id=event_id)
    if before is None:
        raise Http404("그런 이벤트가 없습니다.")
    if not before["action_done"]:
        raise ConfirmDoneRejected(
            "확인할 조치 완료 회신이 없거나 기록이 이미 닫혀 있습니다 — "
            "확인은 현장이 「조치 완료」를 보낸 열린 사건에서만 기록을 닫습니다.")

    if before["response_state"] == OCCURRED_STATE:
        raise ConfirmDoneRejected(
            "아직 아무도 접수하지 않은 사건입니다 — 접수(키 1)가 먼저입니다. "
            "접수한 사람이 없는 종결은 만들지 않습니다.")

    steps: list[str] = []
    allowed = list(before["allowed_next"])
    #: 앞으로만, 한 칸씩. 전이표의 길이가 상한이라 무한히 돌 수 없다(4칸).
    for _ in range(4):
        if CLOSED_STATE in allowed:
            moved = services.advance_response(
                scope=scope, event_id=event_id, to_state=CLOSED_STATE)
            steps.append(CLOSED_STATE)
            break
        forward = [s for s in allowed if s != CLOSED_STATE]
        if not forward:
            break
        moved = services.advance_response(
            scope=scope, event_id=event_id, to_state=forward[0])
        steps.append(forward[0])
        allowed = list(moved.get("allowed_next") or [])

    after = _signal_for(scope=scope, event_id=event_id) or before
    return {"steps": steps, "signal": after}


def queue_field_signals(*, scope, event_ids: list[int]) -> dict:
    """카드 몇 장의 현장 신호를 한 번에 — **화면이 물은 id 만.**

    Args:
        scope: 요청자의 테넌트 스코프.
        event_ids: 화면이 지금 그린 카드의 사건 번호들(상한 `MAX_EVENT_IDS`).

    Returns:
        `signals` 는 **읽힌 것만** 담는다 — 남의/없는 사건은 목록에 아예 없다.
        `asked` 와 `read` 를 함께 내므로 「물었는데 못 읽은 수」가 드러난다(분모 없는
        수는 수가 아니다).

        `wired` 는 **배선 상태**다: 종류를 달고 온 회신이 하나라도 있었는가.
        거짓이면 화면은 「데이터 없음」이 아니라 **「배선 대기」**라고 적는다.
    """
    seen: set[int] = set()
    asked: list[int] = []
    for raw in event_ids:
        try:
            eid = int(raw)
        except (TypeError, ValueError):
            continue
        if eid in seen:
            continue
        seen.add(eid)
        asked.append(eid)
        if len(asked) >= MAX_EVENT_IDS:
            break

    signals = []
    for eid in asked:
        row = _signal_for(scope=scope, event_id=eid)
        if row is not None:
            signals.append(row)

    typed_total = sum(s["typed_total"] for s in signals)
    return {
        "asked": len(asked),
        "read": len(signals),
        "reply_total": sum(s["reply_total"] for s in signals),
        #: ★ 배선 대기 여부. 회신은 오는데 종류가 하나도 안 달려 있으면 거짓이다.
        "wired": typed_total > 0,
        "typed_total": typed_total,
        "support_count": sum(1 for s in signals if s["support_requested"]),
        "action_done_count": sum(1 for s in signals if s["action_done"]),
        "signals": signals,
        "max_event_ids": MAX_EVENT_IDS,
    }
