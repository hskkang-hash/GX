# -*- coding: utf-8 -*-
"""FWS-F2-14 — 장비 점검 체크(등짐펌프·진화차) (턴 AL 차선 N2).

`apps/fws/standby.py`·`patrol.py` 와 같은 판단 — 점검은 **일어난 일 한 줄**이고
새 표를 세우지 않는다. 완결조건(명세서 §5.2)은 「점검 1」 — 한 건이 남고 다시
읽힌다(저장 → 재조회 실측, `notify_prefs.py` 의 「저장→읽기」와 같은 형).
"""
from __future__ import annotations

from django.apps import apps
from django.utils import timezone

from common import audit_writer

LOGGER_NAME = "guardianx.fws.equipment"
TAG = "[FWS-EQUIP]"
ACTION_CHECK = "equipment.check"

#: 결과 2택 — 점검은 「이상 없음/이상 있음」 둘 중 하나를 반드시 남긴다.
RESULT_PASS = "pass"
RESULT_FAIL = "fail"
RESULTS = (RESULT_PASS, RESULT_FAIL)

MAX_EQUIPMENT_CODE_CHARS = 40
MAX_NOTE_CHARS = 300


class EquipmentCheckRejected(Exception):
    """값이 계약 밖이다 — 422."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def check(*, scope, equipment_type: str, equipment_code: str = "",
         result: str = "", note: str = "") -> dict:
    """FWS-F2-14 — 장비 점검 체크 한 건. `equipment_type` 은 자유 문자열이다(등짐펌프·
    진화차는 명세서의 **예시**이지 전체 목록이 아니다 — 임의로 닫힌 목록을 만들면
    다음 장비 종류가 생길 때마다 배포가 필요해진다)."""
    equipment_type = (equipment_type or "").strip()
    if not equipment_type:
        raise EquipmentCheckRejected(
            "장비 종류가 비었다 — 무엇을 점검했는지 없이는 「점검 1」이 뜻을 갖지 못한다")
    equipment_code = (equipment_code or "").strip()
    if len(equipment_code) > MAX_EQUIPMENT_CODE_CHARS:
        raise EquipmentCheckRejected(
            f"장비 코드가 {len(equipment_code)}자다. 상한은 {MAX_EQUIPMENT_CODE_CHARS}자")
    if result not in RESULTS:
        raise EquipmentCheckRejected(
            f"result={result!r} 는 점검 결과가 아니다. 허용: {RESULTS}")
    note = (note or "").strip()
    if len(note) > MAX_NOTE_CHARS:
        raise EquipmentCheckRejected(f"note 가 {len(note)}자다. 상한은 {MAX_NOTE_CHARS}자")

    actor = scope.require_actor()
    now = timezone.now()
    payload = {"equipment_type": equipment_type, "equipment_code": equipment_code,
              "result": result, "note": note, "checked_at": now.isoformat()}
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=ACTION_CHECK,
        outcome=audit_writer.ALLOWED,
        reason=f"{equipment_type} {equipment_code or ''} 점검 {result}".strip(),
        after=payload, api_name=ACTION_CHECK, api_method="POST")
    return {"check_id": entry.audit_id, **payload}


def mine(*, scope, limit: int = 50) -> dict:
    """내가 남긴 점검 전건, 최신순 — 「점검 1」이 실제로 남았는지 재조회로 확인한다."""
    actor = scope.require_actor()
    rows = (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=actor.pk, api_name=ACTION_CHECK)
        .order_by("-id")[: max(1, min(limit, 500))]
    )
    checks = []
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        checks.append({"check_id": row.pk, **payload})
    return {"checks": checks, "count": len(checks)}
