# -*- coding: utf-8 -*-
"""DSM-U3-04 — **PS-LTE 그룹통화 번호 · 상황실 번호 버튼** (`POST|GET /api/dsm/hotline`)
· 차선 N1 · 턴 AM (P-356 §AM).

annex(§4.2) 완결 조건은 「1탭」이다 — 이동 중인 현장 대응자가 M2 화면에서 한 번 눌러
상황실이나 PS-LTE 그룹통화에 건다. `구현` 칸은 `tel:` 하나뿐이고, 재난안전통신망
자체와 연동하지 않는다 — 그 연동은 이 저장소가 잴 수 없는 외부 통신망 영역이다
(`docs/agent/roadmap/기능명세_미포함표_20260925.md` §3 이 이미 그렇게 적어 뒀다).

★ **왜 이제야 서는가.** `frontend/src/features/mobile/pages/MobileEventDetail.tsx`
  머리말 "★★ 전화 버튼을 그리지 않았다"(2026-09-05 · 차선 C)가 이미 답을 냈다 —
  걸 번호가 제품 어디에도 없었다. 그 글이 후보 둘을 남겨 뒀다:
      ⓐ 카메라마다 하나 — 그 자리를 지키는 사람(「현장에 건다」)
      ⓑ 테넌트마다 하나 — 관제 대표번호(「관제에 건다」)
  DSM-U3-04 의 두 번호(PS-LTE 그룹통화 · 상황실)는 **둘 다 조직이 쥔 번호**다 —
  카메라가 아니라 상황실이 쥔 번호이므로 ⓑ 로 선다. ⓐ(카메라별 담당자 번호)는
  여전히 없다 — 이 절이 요구하지 않는다.

★ **새 표를 만들지 않는다** — `alert_level_service.py` 머리말과 같은 판단이다.
  번호가 바뀌는 일은 드물지만, 바뀌면 **누가 언제 바꿨는지**가 감사여야 한다 —
  그래서 한 접수 = 감사 한 줄, 가장 최근 줄이 지금 번호다.

★ 번호의 **값**은 이 파일이 정하지 않는다 — 법정 고시 값이 아니라 조직마다 다른
  값이라(시군구 상황실마다 회선이 다르다) 규제 상수 모듈에 두지 않는다
  (`common/log_retention_policy.py` 류와는 다른 성격 — 그쪽은 법이 값을 못박고,
  이쪽은 조직이 입력한다). 형식은 전화·PS-LTE 다이얼에 쓰는 문자만 받는다
  (숫자·`+`·`*`·`#`·`-`·공백) — 이름이나 메모가 섞이면 `tel:` 링크가 깨진다.
"""
from __future__ import annotations

import re
from typing import Any

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

LOGGER_NAME = "guardianx.u3.hotline"
TAG = "[U3-HOTLINE]"

#: 다이얼 문자만 받는다. 상한 32자 — PS-LTE 그룹 ID·국제 표기(+82…)를 넉넉히 담는다.
_DIAL_RE = re.compile(r"^[0-9+*#\- ]{2,32}$")

#: `_fmt`/`_parse` 짝이 쓰는 「값 없음」 표식. 사람이 실제로 이 문자열을 번호로
#: 입력할 수 없다(다이얼 문자만 받으므로) — 그래서 안전하게 구분자로 쓴다.
_BLANK = "(미기재)"


class HotlineRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없다. `alert_level_service.AlertLevelRejected`
    와 같은 모양."""


def _action(group_id: int) -> str:
    return f"hotline:{group_id}"


def to_tel(number: str) -> str:
    """`tel:` URI 에 넣을 값 — 공백·하이픈(사람이 읽기 좋으라고 넣은 구분자)을 뗀다.
    PS-LTE 단축 다이얼(`*`·`#`)과 국제 표기(`+`)는 그대로 둔다."""
    return re.sub(r"[\s\-]+", "", number or "")


def _validate(label: str, number: str) -> str:
    number = (number or "").strip()
    if number and not _DIAL_RE.match(number):
        raise ValueError(
            f"{label} 은(는) 숫자·+·*·#·-·공백만 받습니다 — {label}={number!r}")
    return number


def _fmt(*, room: str, pslte: str) -> str:
    return f"상황실={room or _BLANK} · PS-LTE={pslte or _BLANK}"


_PARSE_RE = re.compile(r"^상황실=(?P<room>.*?) · PS-LTE=(?P<pslte>.*)$")


def _parse(text: str) -> tuple[str, str]:
    """`_fmt` 의 역함수. 못 읽으면 둘 다 빈 문자열이다 — 모르는 옛 줄을 지어내지 않는다."""
    m = _PARSE_RE.match(text or "")
    if not m:
        return "", ""
    room, pslte = m.group("room"), m.group("pslte")
    return ("" if room == _BLANK else room, "" if pslte == _BLANK else pslte)


def set_hotline(*, scope: TenantScope, situation_room_phone: str = "",
                pslte_group_call: str = "") -> dict[str, Any]:
    """상황실 번호·PS-LTE 그룹통화 번호를 감사 줄로 남긴다 — **가장 최근 줄이 지금 번호**다.

    Raises:
        ValueError: 두 칸이 다 비었다 · 다이얼 문자 밖의 글자가 섞였다.
        HotlineRejected: 소속 조직이 없어 저장할 수 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    room = _validate("상황실 번호", situation_room_phone)
    pslte = _validate("PS-LTE 그룹통화 번호", pslte_group_call)
    if not room and not pslte:
        raise ValueError("상황실 번호·PS-LTE 그룹통화 번호 중 하나는 있어야 합니다.")

    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise HotlineRejected("소속 조직이 없어 연락 번호를 저장할 수 없습니다.")

    text = _fmt(room=room, pslte=pslte)
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_action(group.pk), outcome=audit_writer.ALLOWED,
        reason=text, api_method="POST",
    )
    return {
        "hotline_id": entry.audit_id,
        "situation_room_phone": room,
        "pslte_group_call": pslte,
        "actor_id": entry.actor_id,
    }


def latest_hotline(*, scope: TenantScope) -> dict[str, Any]:
    """**지금 번호** — M2 버튼이 읽을 자리.

    설정이 없으면 `configured: False` 다 — 없는 것에 손잡이를 그리지 않는다
    (`MobileEventDetail.tsx` 머리말 "전화 버튼을 그리지 않았다"와 같은 규율 —
    번호가 없는 테넌트에는 죽은 버튼을 보여 주지 않는다).

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return {"configured": False}
    entries = audit_writer.read(
        logger_name=LOGGER_NAME, action=_action(group.pk), limit=1)
    if not entries:
        return {"configured": False}
    e = entries[0]
    room, pslte = _parse(e.reason)
    return {
        "configured": bool(room or pslte),
        "hotline_id": e.audit_id,
        "situation_room_phone": room,
        "situation_room_tel": to_tel(room) if room else "",
        "pslte_group_call": pslte,
        "pslte_group_call_tel": to_tel(pslte) if pslte else "",
        "actor_id": e.actor_id,
    }
