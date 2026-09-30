# -*- coding: utf-8 -*-
"""DSM-U4-06 — **위기경보·비상 단계 접수 입력** (`POST|GET /api/dsm/alert-level`) ·
차선 N1 · 턴 AL (P-356 ⑤).

annex(§4.2) 완결 조건은 「변경 감사」 하나다 — 상급(중대본·지대본)이 위기경보 단계를
올리거나 내리면 **그 접수 사실이 감사에 남는가**만 묻는다. 「상단바 띠·홈 카드」
화면은 턴 AL 에선 범위 밖이었고(P-356), 턴 AQ 차선 W2B 가 `features/dsm/components/
AlertLevelBand.tsx`(띠) · `AlertLevelCard.tsx`(홈 카드)로 그린다 — 둘 다 `GET /alert-level`
의 첫 행(`level` 칸)을 읽는다.

★ **새 표를 만들지 않는다** — `apps/dsm/situation_meeting_service.py` 머리말과
  같은 판단이다. 「테넌트 상태 축」이라는 별도 칸을 두면 그 칸과 감사 이력이 둘로
  쌓이고, 어느 쪽이 「지금 단계」의 정본인지 갈린다. 한 접수 = 감사 한 줄, **가장
  최근 줄이 곧 지금 단계**다(`latest()` 가 그 줄 하나를 읽는다).

★ **단계 넷은 이 파일의 것이다 — `apps/fws/risk.py::LEVELS` 를 빌리지 않는다.**
  두 파일이 같은 문자열 `("관심","주의","경계","심각")` 을 쓰는 것은 우연이 아니라
  **둘 다 같은 국가 위기경보 4단계**(재난 및 안전관리 기본법 제38조)를 가리키기
  때문이다. 그렇다고 하나를 import 하지 않는다 — FWS(`backend/apps/fws/**`)는
  이번 턴 다른 차선(N2) 소유표이고(§0.4 옆 규약), 산불 위기경보(FWS)와 재난안전과
  일반 위기경보(DSM)는 **다른 발령 주체·다른 접수 절차**를 가진 별개의 절이다.
  이름이 같은 상수를 두 곳에 두는 것과, 소유 경계를 넘어 import 하는 것 중
  이번 턴은 전자를 택한다(D-212 는 "같은 판정을 두 벌로 재는 것"을 금하지, "같은
  이름의 열거값을 두 App 이 각자 선언하는 것"을 금하지 않는다).
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

#: 국가 위기경보 4단계(법 제38조) — 낮은 것에서 높은 것 순.
LEVELS = ("관심", "주의", "경계", "심각")

LOGGER_NAME = "guardianx.u4.alert_level"
TAG = "[U4-ALERT]"


class AlertLevelRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없다. `situation_meeting_service.SituationMeetingRejected`
    와 같은 모양."""


def _action(group_id: int) -> str:
    return f"alert_level:{group_id}"


def _fmt(*, level: str, occurred_at, doc_no: str, staffing: int | None) -> str:
    stamp = timezone.localtime(occurred_at).strftime("%Y-%m-%d %H:%M")
    staffing_text = f"{staffing}명" if staffing is not None else "(미기재)"
    return (f"단계={level} · 접수 시각={stamp} · 문서번호={doc_no or '(미기재)'} · "
            f"비상 근무 편성={staffing_text}")


def _parse(text: str) -> dict[str, Any]:
    """[턴 AQ · 차선 W2B] 감사 줄 한 문장(`_fmt`)을 칸으로 되읽는다 — 상단바 띠·홈 카드가
    「단계」 글자를 문장에서 다시 자르지 않게(화면이 문장을 자르면 두 벌이 된다).
    이 파일이 쓴 모양만 읽는다 — 못 읽는 칸은 빈 값이다(지어내지 않는다)."""
    out: dict[str, Any] = {"level": "", "received_at": "", "doc_no": "", "staffing": None}
    for part in (text or "").split(" · "):
        key, _, value = part.partition("=")
        if key == "단계" and value in LEVELS:
            out["level"] = value
        elif key == "접수 시각":
            out["received_at"] = value
        elif key == "문서번호" and value != "(미기재)":
            out["doc_no"] = value
        elif key == "비상 근무 편성" and value.endswith("명"):
            try:
                out["staffing"] = int(value[:-1])
            except ValueError:
                pass
    return out


def record_alert(*, scope: TenantScope, level: str, occurred_at: str | None = None,
                 doc_no: str = "", staffing: int | None = None) -> dict[str, Any]:
    """상급 발령 접수 한 건을 감사 줄로 남긴다 — **가장 최근 줄이 지금 단계**다.

    Raises:
        ValueError: `level` 이 4단계 밖이거나, `occurred_at` 이 있는데 ISO 로 못 읽는다,
            `staffing` 이 음수다.
        AlertLevelRejected: 소속 조직이 없어 저장할 수 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    level = (level or "").strip()
    if level not in LEVELS:
        raise ValueError(f"단계는 {LEVELS} 중 하나다 — level={level!r}")
    if staffing is not None and staffing < 0:
        raise ValueError(f"비상 근무 편성 인원 수는 0 이상이다 — staffing={staffing!r}")

    when = timezone.now()
    if occurred_at:
        parsed = parse_datetime(occurred_at)
        if parsed is None:
            raise ValueError(f"접수 시각을 읽을 수 없습니다: {occurred_at!r}")
        when = timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed

    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise AlertLevelRejected(
            "소속 조직이 없어 위기경보 접수를 저장할 수 없습니다.")

    text = _fmt(level=level, occurred_at=when, doc_no=(doc_no or "").strip(),
               staffing=staffing)
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_action(group.pk), outcome=audit_writer.ALLOWED,
        reason=text, api_method="POST",
    )
    return {
        "alert_id": entry.audit_id,
        "level": level,
        "occurred_at": when,
        "doc_no": (doc_no or "").strip(),
        "staffing": staffing,
        "actor_id": entry.actor_id,
    }


def list_alerts(*, scope: TenantScope, limit: int = 100) -> list[dict[str, Any]]:
    """접수 이력 — 최신이 먼저 · **내 테넌트 것만**(`_action` 이 좁힌다).

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return []
    entries = audit_writer.read(
        logger_name=LOGGER_NAME, action=_action(group.pk), limit=limit)
    return [
        {"alert_id": e.audit_id, "text": e.reason, "actor_id": e.actor_id,
         **_parse(e.reason)}
        for e in entries
    ]


def latest_alert(*, scope: TenantScope) -> dict[str, Any]:
    """**지금 단계** — 상단바 띠·홈 카드가 읽을 자리(화면은 이번 범위 밖).

    이력이 없으면 `exists: False` 다 — 0 은 「접수 없음」이지 「모른다」가 아니다.

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return {"exists": False}
    entries = audit_writer.read(
        logger_name=LOGGER_NAME, action=_action(group.pk), limit=1)
    if not entries:
        return {"exists": False}
    e = entries[0]
    return {"exists": True, "alert_id": e.audit_id, "text": e.reason,
            "actor_id": e.actor_id, **_parse(e.reason)}
