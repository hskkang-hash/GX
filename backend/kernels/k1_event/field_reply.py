# -*- coding: utf-8 -*-
"""K1 **현장 회신** — 이동 중인 사람이 한 줄을 남긴다 (차선 D · U3 #9 · M3).

무엇인가
--------
관제가 「가 보라」고 보낸 사건에 대해, **현장에 있는 사람이 돌려주는 한 줄**이다.
「불이 났다」/「오작동이다」/「도착했다, 소방 대기」 같은 문장이고, 이것이 없으면
관제는 사람이 갔는지조차 대응 상태 칸으로만 짐작한다.

왜 새 표를 만들지 않았나 [판정 2026-09-04 · 차선 D]
--------------------------------------------------
회신을 담을 후보가 셋이었다.

    ① 새 모델 + 마이그레이션 0027      가장 곧은 길. 그러나 `stream_monitors/models.py`
                                       는 이번 턴 여러 차선이 같이 쓰는 파일이고,
                                       모델·마이그레이션 충돌은 병합에서 가장 비싸다.
    ② `DeliveryRecord` 에 얹기          **금지다.** 그 표는 F-10 의 30초와 5분 억제를
                                       재는 자리다(`notice_false_positive` 가 행을
                                       안 만드는 것과 같은 이유). 회신 행이 섞이면
                                       발송 통계가 조용히 오염된다.
    ③ 감사 표에 전용 `logger_name`      **이것으로 갔다.**

③을 고른 이유는 이 저장소가 **대응 진행 이력을 이미 그렇게 남기고 있어서**다:
`response_flow.LOGGER_NAME = "guardianx.dsm.response"` 가 전이 전건을 담고, D-399 는
「대응 전이의 행위자는 행이 아니라 감사에 있다」고 못박았다. 현장 회신은 그 축의
**같은 계열**이다 — 사람이 한 일의 기록이지 탐지의 사실이 아니다.

한계를 적어 둔다 [실측]
-----------------------
· 감사 표(`logger.AuditLogs`)는 dj-core 소유이고 §0.4 금지구역이라 **테넌트 소유 칼럼이
  없다.** 그래서 읽기 쪽 좁히기를 표가 해 주지 못하고, `list_field_replies` 가
  **이벤트 문지기를 먼저 지난 뒤** 그 이벤트 번호로만 뽑는다. 이벤트가 이미 걸러졌으므로
  결과도 걸러진 것이지만, 그 성질은 **표가 아니라 이 함수가** 지킨다.
· 사진 1장은 **없다.** 파일을 받으려면 업로드 면과 저장소 규약이 필요하고, 그것은
  이 턴의 범위 밖이다. 「사진 없이 한 줄」이 아무것도 없는 것보다 낫다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from common import audit_writer
from common.tenant_scope import TenantScope
from kernels.k1_event.exceptions import InvalidEventInput

#: 감사 행의 `logger_name`. **이 문자열 하나로 현장 회신 전건을 뽑는다** —
#: 이름이 하나여야 「전건」이 성립한다 (D-285 ②). 대응 전이(`…dsm.response`)와
#: **다른 이름**이다: 섞으면 「전이 전건」 집계가 회신 수만큼 부풀어 오른다.
LOGGER_NAME = "guardianx.dsm.field_reply"
TAG = "[FIELD]"
ACTION = "field_reply"

#: 한 줄의 상한. 「한 줄 보고」라는 말이 뜻을 가지려면 상한이 있어야 한다.
#: 감사 표의 `note` 칼럼이 받는 길이보다 넉넉히 짧게 잡는다.
MAX_REPLY_CHARS = 500


@dataclass(frozen=True)
class FieldReply:
    """남긴 회신 한 줄. **모델이 아니라 값이다** (K2 `Recipient` 와 같은 이유)."""

    reply_id: int
    event_id: int
    author_id: int | None
    author_name: str
    text: str


def reply_from_field(
    *,
    scope: TenantScope,
    event_id: int,
    text: str,
) -> FieldReply:
    """현장에서 한 줄을 남긴다.

    문턱 셋:

        ① **내 테넌트의 이벤트인가** — `get_event` 를 그대로 지난다. 남의 것이면 404 다.
          문지기를 새로 만들지 않는다: 읽기 문지기를 쓰기 앞에 그대로 세우는 것이
          `advance_response` 가 한 일이고, 두 벌은 갈린다 (D-212).
        ② **사람인가** — 시스템 스코프는 회신을 남길 수 없다. 「현장 회신」은 정의상
          사람이 하는 일이고, 행위자 없는 회신은 감사에서 「누가 갔나」에 답하지 못한다.
        ③ **한 줄인가** — 비었거나 상한을 넘으면 거절이다. 잘라 저장하지 않는다:
          잘린 회신은 「연기 없음」이 「연기 있음…」의 앞부분일 수 있다.

    ★ **무계정 링크 금지**(불변 제약)의 실제 집행이 ②다. 모바일은 링크로 들어오지만
      회신을 남기는 것은 **계정**이다. 토큰 없는 요청은 여기까지 오지 못하고,
      혹시 시스템 스코프로 들어와도 여기서 멈춘다.
    """
    from kernels.k1_event.services import get_event

    # ① 남의 것이면 여기서 404 가 난다
    event = get_event(event_id, scope=scope)

    # ② 행위자 없는 회신은 회신이 아니다
    actor = None if scope.is_system else scope.require_actor()
    if actor is None:
        raise InvalidEventInput(
            "현장 회신은 사람이 남긴다 — 시스템 스코프로는 남길 수 없다. "
            "행위자 없는 회신은 감사에서 「누가 갔나」에 답하지 못한다")

    # ③ 한 줄인가. **잘라 저장하지 않는다**
    body = (text or "").strip()
    if not body:
        raise InvalidEventInput(
            "현장 회신이 비었다. 빈 회신을 저장하면 「회신 1건」이라는 수가 "
            "「사람이 갔다」를 뜻하지 않게 된다")
    if len(body) > MAX_REPLY_CHARS:
        raise InvalidEventInput(
            f"현장 회신이 {len(body)}자다. 상한은 {MAX_REPLY_CHARS}자 — "
            "잘라 저장하지 않는다: 잘린 회신은 뜻이 뒤집힐 수 있다")

    # ★ 감사가 곧 저장이다. 실패하면 예외가 올라간다 — 남길 수 없으면 그 회신은
    #   일어나지 않는 것이 옳다 (`audit_writer` 머리말 · `advance_response` 와 같은 규약).
    entry = audit_writer.write(
        logger_name=LOGGER_NAME,
        tag=TAG,
        actor=actor,
        action=ACTION,
        outcome=audit_writer.ALLOWED,
        reason=body,
        #: ★ 사건 번호를 **구조로도** 남긴다. `note` 만 있으면 회신을 이벤트별로
        #:   뽑을 때 문자열을 뒤져야 하고, 문자열 뒤지기는 곧 갈린다.
        after={"event_id": event.event_id, "text": body},
        api_name=ACTION,
        api_method="POST",
    )
    return FieldReply(
        reply_id=entry.audit_id,
        event_id=event.event_id,
        author_id=getattr(actor, "pk", None),
        author_name=getattr(actor, "username", "") or "",
        text=body,
    )


def list_field_replies(
    *,
    scope: TenantScope,
    event_id: int,
    limit: int = 50,
) -> tuple[FieldReply, ...]:
    """한 이벤트의 현장 회신들. **이벤트 문지기를 먼저 지난다.**

    ⚠ 좁히기를 표가 해 주지 못한다(머리말 [실측]). 그래서 순서가 뜻이다:
      `get_event` 가 먼저 404 를 내고, 그 뒤에야 번호로 뽑는다. 순서를 바꾸면
      **남의 이벤트 번호로 남의 현장 회신을 읽을 수 있다.**
    """
    from django.apps import apps

    from kernels.k1_event.services import get_event

    get_event(event_id, scope=scope)      # 남의 것이면 여기서 404

    AuditLogs = apps.get_model("logger", "AuditLogs")
    rows = (
        AuditLogs._base_manager
        .filter(logger_name=LOGGER_NAME, api_name=ACTION)
        .order_by("-id")[: max(1, min(limit, 500))]
    )

    out: list[FieldReply] = []
    for row in rows:
        payload = _payload_of(row)
        if payload.get("event_id") != event_id:
            continue
        out.append(FieldReply(
            reply_id=row.pk,
            event_id=event_id,
            author_id=row.user_id,
            author_name=row.username or "",
            text=payload.get("text") or (row.note or ""),
        ))
    return tuple(out)


def _payload_of(row) -> dict:
    """`data_after` 를 딕셔너리로 읽는다. **못 읽으면 빈 것으로 본다** — 던지지 않는다.

    감사 한 줄이 깨졌다고 나머지 회신을 못 읽게 되면, 고장 하나가 화면 전체를 비운다.
    """
    raw = getattr(row, "data_after", None)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (str, bytes)):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}
