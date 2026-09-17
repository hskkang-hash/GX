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
"""
from __future__ import annotations

from typing import Any

from django.http import Http404

from apps.dsm import services

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


def _text_of(reply: Any) -> str:
    return (getattr(reply, "text", "") or "").strip()


def _starts_with_marker(text: str, markers: tuple[str, ...]) -> bool:
    head = text.lstrip()
    return any(head.startswith(m) for m in markers)


def classify(reply: Any) -> str:
    """회신 한 줄 → `"support"` · `"done"` · `""`(그냥 한 줄).

    ★ **순수 함수다** — 시험이 DB 없이 이 갈래 전부를 잰다. 그리고 두 후보(접두·칸)를
      한 자리에서 읽으므로, 어느 쪽으로 정해지든 고칠 자리가 하나다.
    """
    kind = _kind_of(reply)
    if kind in SUPPORT_KINDS:
        return "support"
    if kind in DONE_KINDS:
        return "done"

    text = _text_of(reply)
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
        "action_done": bool(done_text),
        "action_done_text": done_text,
        "last_text": last_text,
        "last_author": last_author,
    }


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
