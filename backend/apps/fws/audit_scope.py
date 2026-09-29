# -*- coding: utf-8 -*-
"""FWS 감사 곁표(`common.models.AuditScope`) 쓰기·읽기 자리 하나
(턴 AO 차선 O · P-411 · `docs/agent/checkpoints/turn-ao/O.md`).

무엇 때문에 이 파일이 생겼나
-----------------------------
`office2.py`(F3-18 계도·단속 통계·입산통제구역)·`admin_settings.py`(U5-02
초소 등록·U5-03 대피 대상 등록)는 새 표 없이 dj-core 감사 로그
(`logger.AuditLogs`)에 기록한다(턴 AN 의 판단 — 위 두 파일 머리말). 그런데
그 표에는 **테넌트(group) 칸이 없어**(§0.4 dj-core 소유 — 고칠 수 없다)
통계·등록 목록을 테넌트 전체로 묻지 못하고 "이 행을 쓴 사람 자신의 것만"으로
좁혀 왔다 — 반쪽(두 지자체의 운영 담당이 같은 절을 쓰면 서로의 것을 못 본다).

세종 P-411: 감사표는 안 만진다 — 우리 곁표 하나(`common.models.AuditScope`)로
「그 감사 행이 어느 테넌트(group) 것인가」만 따로 적는다(BillingMark 와 같은
판단 · `common/models.py::AuditScope` 머리말 참고). **이 파일은 그 곁표에
쓰고 읽는 자리를 하나로 묶는다.**

왜 네 절만인가 — 범위를 넓히지 않는다
--------------------------------------
이 도우미를 부르는 것은 F3-18(계도·단속 기록·입산통제구역 설정)·U5-02(초소
등록)·U5-03(대피 대상 등록)의 쓰기 자리 **뿐**이다. 같은 두 파일의 다른 쓰기
(F3-11~14·F3-17·F3-19 등)는 이미 사건 id(F-05 K1 문)로 테넌트가 좁혀 있거나
이번 반쪽에 걸리지 않으므로 손대지 않는다(파일 소유·범위 최소 — 남의 절까지
곁표로 옮기면 이 차선의 책임 밖 코드를 건드리는 것이다).

왜 미들웨어로 전역을 가로채지 않는가
--------------------------------------
이 감사표(`logger.AuditLogs`)에는 **다른 앱(DSM 의 F-12 설정 감사 등)의 행도
같이 쌓인다**(`common/audit_writer.py` 머리말 — "감사 한 줄을 쓰는 자리
하나"). 미들웨어나 `audit_writer.write` 자체를 가로채면 이 차선이 손대면 안
되는 다른 App 의 감사 행까지 곁표를 얻게 되고, 그 반경은 차선 O 의 파일 소유
밖이다(§0.4 인접 원칙과 같은 결 — 닫아야 할 문은 넓히지 않고 좁힌다). 그래서
**호출자가 명시적으로 부르는 좁은 도우미**로 남긴다 — 이 차선이 손대는 정확히
그 자리만 영향받는다.
"""
from __future__ import annotations

from django.apps import apps as django_apps

from common import audit_writer
from common.tenant_filters import get_user_group


def record(*, scope, logger_name: str, tag: str, action: str, payload: dict,
          reason: str, kind: str = "", api_method: str = "POST"):
    """감사 행 하나를 쓰고, **곧바로** 곁표(`AuditScope`) 행을 잇는다.

    `audit_writer.write` 가 이미 감사 쓰기 실패를 삼키지 않는다(그 파일 머리말)
    — 이 함수는 그 계약을 그대로 물려받는다: 감사 행이 먼저 성립해야 곁표를
    붙일 `audit_id` 가 생긴다.

    ★ 소속 group 이 없는 행위자(전역 관리자 등)는 곁표를 **안 남긴다**(아래
      `_save_scope` — 좁힐 테넌트가 없다). 그래도 감사 행 자체는 그대로
      남는다 — 이전(곁표가 없던 시절)과 같은 모양일 뿐, 새로운 손실이 아니다.
    """
    actor = scope.require_actor()
    entry = audit_writer.write(
        logger_name=logger_name, tag=tag, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason, after=payload,
        api_name=action, api_method=api_method)
    _save_scope(audit_id=entry.audit_id, actor=actor, kind=kind or logger_name)
    return entry


def _model():
    return django_apps.get_model("common", "AuditScope")


def _save_scope(*, audit_id: int, actor, kind: str) -> None:
    group = get_user_group(actor)
    group_id = getattr(group, "pk", None)
    if group_id is None:
        return  # 소속 group 없음 — 좁힐 테넌트가 없다(위 머리말).
    _model()._base_manager.update_or_create(
        audit_id=audit_id, defaults={"tenant_group_id": group_id, "kind": kind})


def tenant_audit_ids(*, scope, kind: str = "") -> set:
    """요청자의 group(테넌트)에 표식된 감사 행 id 전부.

    `scope.require_actor()` 로 인증을 다시 확인한다 — 이 함수를 부르는 쪽은
    이미 라우트 문턱(`require_admin`·`@tenant_scoped`)을 지났지만, 읽기 문턱을
    한 번 더 세우는 편이 **닫는 쪽을 기본값으로** 둔다(`tenant_filters.py`
    머리말과 같은 결).

    group 이 없으면(전역 관리자 등) **빈 집합**을 돌려준다 — 격리 시험(다른
    테넌트는 0건)과 같은 방향의 판단이다: "전역이니 전부 본다"가 아니라
    "좁힐 테넌트가 없으니 0건"으로 닫는다. 전역 관리자에게 전체를 보여주는
    것은 이 차선의 범위 밖 — 필요해지면 `is_global_admin()` 분기를 이 자리에
    더한다(지금은 짓지 않는다 · 지어내지 않는다).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    group_id = getattr(group, "pk", None)
    if group_id is None:
        return set()
    qs = _model()._base_manager.filter(tenant_group_id=group_id)
    if kind:
        qs = qs.filter(kind=kind)
    return set(qs.values_list("audit_id", flat=True))


__all__ = ["record", "tenant_audit_ids"]
