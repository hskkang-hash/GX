# -*- coding: utf-8 -*-
"""K5 신뢰 커널 공개 면 — 표 ① 임계값 · 표 ② 자격증명 (D-325 · D-328).

계층 (DA-04 §1)
---------------
**L3 Platform.** App(L4)·어댑터(L2)는 여기 서비스 함수만 부른다 — 모델을 직접 만지지 않는다.
그래서 이 파일이 모델을 `apps.get_model` 로 늦게 찾는다: 커널이 특정 앱의 모듈을
import 하면 그 순간 커널이 그 앱에 묶이고, "한 번 개발해서 두 번 판다" 가 거짓이 된다.

이중 AC (D-325 초효율)
----------------------
    계약 (F)  F-02 「지점별 기준선 설정」 · F-05 「API Key 발급·폐기」 ·
              F-12 「임계값」 「API키」
    상품 (U)  U1~U4 상용판이 **같은 표를 쓴다.** 임계값과 자격증명은 재난안전 전용 개념이
              아니다 — 산업안전·시설물 App 도 같은 두 표를 그대로 소비한다.
"""
from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common.tenant_filters import assert_scoped, filter_by_group_field, get_user_group
from common.tenant_roles import is_global_admin
from common.tenant_scope import TenantScope
from kernels.k5_trust import audit, credentials as cred, thresholds as th
from kernels.k5_trust.exceptions import (
    CredentialNotUsable,
    ScopeNotAvailable,
    ThresholdIsContractFixed,
    ThresholdNotSet,
)


def _model(name: str):
    return apps.get_model("stream_monitors", name)


# ═══════════════════════════════════════════════════════════════════════════
# 표 ① 임계값
# ═══════════════════════════════════════════════════════════════════════════

def _lookup_chain(spec, *, tenant_id: int | None,
                  camera_id: int | None = None) -> list[dict]:
    """**좁은 것이 이긴다** — camera → tenant → global. 그 순서를 적은 곳은 여기뿐이다.

    표를 그리는 `list_thresholds` 와 값을 푸는 `resolve_threshold` 가 **같은 한 벌**을
    쓴다(D-212). 두 벌이던 동안 표는 전역만 읽고 실행은 기관을 읽어서,
    **저장은 됐는데 표가 안 바뀌는** 자리가 났다(턴 AA · U5#S3).

    `applies_to` 보다 좁은 층은 **아예 후보에 없다** — 있지도 못할 행을 묻지 않는다.
    """
    lookups: list[dict] = []
    if camera_id is not None and spec.applies_to == th.SCOPE_CAMERA:
        lookups.append({"scope_level": th.SCOPE_CAMERA, "camera_id": camera_id})
    if tenant_id is not None and spec.applies_to in (th.SCOPE_TENANT, th.SCOPE_CAMERA):
        lookups.append({"scope_level": th.SCOPE_TENANT, "group_id": tenant_id})
    lookups.append({"scope_level": th.SCOPE_GLOBAL})
    return lookups


def list_thresholds(*, scope: TenantScope) -> tuple[dict[str, Any], ...]:
    """표 ① 전체 — **정의 + 지금 유효한 값 + 그 값이 어디서 왔는가.**

    F-12 관리자 설정이 그리는 표가 이것이다. `source` 를 함께 내는 이유:
    같은 숫자라도 "정의 기본값" 인지 "누가 덮어쓴 값" 인지가 다르고,
    그 구별이 없으면 운영자가 자기가 바꾼 값을 다시 못 찾는다.
    """
    actor = scope.require_actor()
    Setting = _model("ThresholdSetting")
    # ★★ **기관 층이 전역 층을 이긴다** — 「지금 유효한 값」은 `resolve_threshold` 가
    #   답하는 값과 **같아야** 한다. 여기가 전역 층만 읽던 동안, 제 기관 값을 바꾼
    #   기관 관리자는 저장이 성공했는데도 표에서 **정의 기본값**을 봤다
    #   (턴 AA 차선 A 실측 · U5#S3). 화면이 제 사용자에게 유효하지 않은 값을 그렸다.
    #   ⚠ 카메라 층은 여기서 안 읽는다 — 이 표에는 카메라가 없다. 카메라 한 대의
    #     값은 `resolve_threshold(camera_id=…)` 가 답하는 자리다(D-290).
    my_group_id = getattr(get_user_group(actor), "pk", None)
    overrides = {
        (r.key, r.scope_level): r.value
        for r in Setting._base_manager.filter(scope_level=th.SCOPE_GLOBAL)
    }
    if my_group_id is not None:
        overrides.update({
            (r.key, r.scope_level): r.value
            for r in Setting._base_manager.filter(
                scope_level=th.SCOPE_TENANT, group_id=my_group_id)
        })
    # ★ 좁은 층의 건수는 **내 테넌트 것만** 센다 — 남의 테넌트가 몇 개를 덮었는지는
    #   숫자만으로도 알려 줄 이유가 없다. 전역 행은 group 이 없으므로 위에서 따로 읽는다.
    counts: dict[tuple[str, str], int] = {}
    scoped = filter_by_group_field(
        Setting._base_manager.exclude(scope_level=th.SCOPE_GLOBAL), actor)
    for key, level in scoped.values_list("key", "scope_level"):
        counts[(key, level)] = counts.get((key, level), 0) + 1
    for key, level in Setting._base_manager.filter(
            scope_level=th.SCOPE_GLOBAL).values_list("key", "scope_level"):
        counts[(key, level)] = counts.get((key, level), 0) + 1
    rows = []
    for key, spec in th.THRESHOLDS.items():
        # ★ 순서를 여기서 새로 짜지 않는다 — `resolve_threshold` 와 **같은 한 벌**을
        #   부른다(D-212). 판정식이 두 벌이면 표와 실행이 갈리고, 갈린 것은 안 보인다.
        override, source_level = None, None
        for where in _lookup_chain(spec, tenant_id=my_group_id):
            found = overrides.get((key, where["scope_level"]))
            if found is not None:
                override, source_level = found, where["scope_level"]
                break
        rows.append({
            "key": key,
            "title": spec.title,
            "unit": spec.unit,
            "default": spec.default,
            "value": float(override) if override is not None else spec.default,
            "source": "override" if override is not None else (
                "default" if spec.default is not None else "unset"),
            # ★ **어느 층이 이겼는가.** `source` 만으로는 「전역이 바뀐 것」과
            #   「내 기관이 바뀐 것」이 한 칸에 뭉친다 — 그 둘은 고치는 사람이 다르다.
            "source_level": source_level,
            "applies_to": spec.applies_to,
            "contract_fixed": spec.contract_fixed,
            "clause": spec.clause,
            "why": spec.why,
            "used_by": list(spec.used_by),
            # ★ 좁은 층에 값이 몇 개 있는가. 「전역 기본만 채운다」가 지켜지는지 보인다.
            "override_counts": {
                level: counts.get((key, level), 0) for level in th.SCOPE_LEVELS
            },
        })
    return tuple(rows)


def resolve_threshold(key: str, *, scope: TenantScope,
                      camera_id: int | None = None) -> float:
    """지금 이 자리에서 유효한 값. **좁은 것이 이긴다** — camera → tenant → global → 정의.

    값이 없으면 `ThresholdNotSet` 으로 멈춘다. **0 을 돌려주지 않는다** —
    「기준선이 0cm」로 읽히면 모든 신호가 초과가 된다 (D-284 · D-290).
    """
    spec = th._definition(key)
    Setting = _model("ThresholdSetting")

    # ★ 문지기가 먼저다 (W0-14c). 남의 카메라 pk 를 넘겨 그 지점의 기준선을 읽어 가는
    #   경로를 여기서 끊는다. 파이프라인(system scope)에는 요청자가 없으므로 건너뛴다 —
    #   그때 테넌트는 **카메라 자신의 group** 이 정한다 (record_detection 과 같은 규약).
    camera = None
    if camera_id is not None:
        if not scope.is_system:
            assert_scoped(_model("StreamMonitor"), camera_id, scope.actor)
        camera = _model("StreamMonitor")._base_manager.filter(pk=camera_id).first()
    tenant_id = (getattr(camera, "group_id", None)
                 or getattr(get_user_group(scope.actor), "pk", None))

    for where in _lookup_chain(spec, tenant_id=tenant_id, camera_id=camera_id):
        row = Setting._base_manager.filter(key=key, **where).first()
        if row is not None:
            return float(row.value)

    if spec.default is None:
        raise ThresholdNotSet(
            f"임계값 {key!r}({spec.title}) 에 값이 없다. 기본값을 지어내지 않는다 — "
            f"그 숫자가 곧 계약 AC 의 판정 근거가 되기 때문이다(D-280). "
            f"적용 범위는 '{spec.applies_to}' 이므로 그 층에 값을 넣어야 한다. "
            f"근거 절: {spec.clause or '(없음)'}")
    return float(spec.default)


@transaction.atomic
def set_threshold(*, scope: TenantScope, key: str, value: float, reason: str,
                  scope_level: str = th.SCOPE_GLOBAL,
                  scope_ref: int | None = None) -> dict[str, Any]:
    """임계값 하나를 덮어쓴다. **사유 없이는 못 바꾼다.**

    권한 판정은 여기서 하지 않는다 — F-12 문지기(`apps.dsm.services.guard_setting`)가
    한다. **판정식을 두 벌 두지 않는다**(D-212). 이 함수가 하는 일은 셋이다:
    계약 고정 여부 확인 · 값 기록 · **내력과 감사 남기기.**
    """
    spec = th._definition(key)
    actor = scope.require_actor()

    if spec.contract_fixed:
        audit._threshold_change(actor=actor, key=key, outcome=audit.DENIED,
                               reason="계약 고정 임계값")
        raise ThresholdIsContractFixed(
            f"{key!r} 는 계약이 못박은 값이다 — {spec.clause}. "
            f"설정 한 줄로 계약을 어길 수 있으면 그 계약은 코드에서 사라진 것이다. "
            f"바꾸려면 계약을 바꾼다")
    if scope_level not in th.SCOPE_LEVELS:
        raise ScopeNotAvailable(
            f"scope_level={scope_level!r} 은 열거 밖이다 {th.SCOPE_LEVELS} — "
            f"오타는 새 범위가 아니다")
    if scope_level == th.SCOPE_CAMERA and spec.applies_to != th.SCOPE_CAMERA:
        raise ScopeNotAvailable(
            f"{key!r} 는 카메라별로 두는 값이 아니다 (applies_to={spec.applies_to})")
    if scope_level == th.SCOPE_TENANT and spec.applies_to == th.SCOPE_GLOBAL:
        raise ScopeNotAvailable(
            f"{key!r} 는 전역 하나뿐인 값이다 (applies_to=global)")
    if not (reason or "").strip():
        raise ValueError(
            "사유가 없다. 사유 없는 임계값 변경은 다음 사람에게 사고로만 보인다 — "
            "무엇에서 무엇으로 바꿨는지는 표가 알지만 **왜** 는 여기밖에 남지 않는다")

    # ★ 문지기가 먼저다 — 남의 지점 기준선을 바꾸는 경로를 여기서 끊는다 (W0-14c).
    if scope_level == th.SCOPE_CAMERA:
        assert_scoped(_model("StreamMonitor"), scope_ref, actor)
    if scope_level == th.SCOPE_TENANT:
        mine = getattr(get_user_group(actor), "pk", None)
        if not is_global_admin(actor) and scope_ref != mine:
            raise ScopeNotAvailable(
                "남의 테넌트 임계값은 바꿀 수 없다 — 전역 관리 역할만 다른 테넌트를 만진다")

    Setting, Change = _model("ThresholdSetting"), _model("ThresholdChange")
    where, camera = _where(scope_level, scope_ref)

    row = Setting._base_manager.filter(key=key, **where).first()
    previous = row.value if row is not None else None

    if row is None:
        Setting._base_manager.create(
            key=key, value=str(value), updated_by=actor, **where)
    else:
        row.value = str(value)
        row.updated_by = actor
        row.save(update_fields=["value", "updated_by", "updated_at"])

    Change._base_manager.create(
        key=key, scope_level=scope_level,
        camera_id=where.get("camera_id"),
        camera_label=getattr(camera, "name", "") or "",
        group_id=where.get("group_id"),
        old_value=previous, new_value=str(value), reason=reason, changed_by=actor)
    audit._threshold_change(actor=actor, key=key, outcome=audit.ALLOWED,
                           reason=reason, before=previous, after=str(value))
    return {"key": key, "scope_level": scope_level, "scope_ref": scope_ref,
            "old": previous, "new": str(value)}


def _where(scope_level: str, scope_ref: int | None) -> tuple[dict, Any]:
    """층 하나를 **행의 자리**로 옮긴다. `scope_ref` 의 뜻이 층마다 다르므로 여기서 가른다.

    tenant → `group_id` · camera → `camera_id` · global → 둘 다 null.
    한 칸에 두 뜻을 담지 않으려고 모델을 나눴으므로(D-290), 번역도 한 곳에서만 한다.
    """
    if scope_level == th.SCOPE_CAMERA:
        camera = _model("StreamMonitor")._base_manager.filter(pk=scope_ref).first()
        if camera is None:
            raise ScopeNotAvailable(
                f"카메라 {scope_ref} 가 없다 — 없는 지점의 기준선은 다음 사고의 근거가 된다")
        return ({"scope_level": scope_level, "camera_id": camera.pk,
                 "group_id": getattr(camera, "group_id", None)}, camera)
    if scope_level == th.SCOPE_TENANT:
        if scope_ref is None:
            raise ScopeNotAvailable("테넌트 층인데 어느 테넌트인지가 없다")
        return ({"scope_level": scope_level, "group_id": scope_ref}, None)
    return ({"scope_level": scope_level}, None)


def threshold_history(*, scope: TenantScope, key: str | None = None,
                      limit: int = 50) -> tuple[dict, ...]:
    """변경 이력. **무엇에서 무엇으로, 누가, 왜** — 넷이 함께 나온다."""
    actor = scope.require_actor()
    Change = _model("ThresholdChange")
    # 전역 변경(group=null)은 모두가 본다. 좁은 층의 변경은 **자기 테넌트 것만** 본다.
    qs = (filter_by_group_field(Change._base_manager.exclude(group__isnull=True), actor)
          | Change._base_manager.filter(group__isnull=True))
    if key:
        qs = qs.filter(key=key)
    return tuple({
        "key": r.key, "scope_level": r.scope_level,
        "camera": r.camera_id, "camera_label": r.camera_label, "tenant": r.group_id,
        "old": r.old_value, "new": r.new_value, "reason": r.reason,
        "changed_at": r.changed_at, "changed_by": r.changed_by_id,
    } for r in qs[:limit])


# ═══════════════════════════════════════════════════════════════════════════
# 표 ② 자격증명 저장처
# ═══════════════════════════════════════════════════════════════════════════

def list_credentials(*, scope: TenantScope) -> tuple[dict[str, Any], ...]:
    """표 ② 전체. **값은 없다 — 사실만 있다.**

    `declared_status`(우리가 안다고 적어 둔 것)와 `observed_status`(이 환경이 지금
    말하는 것)를 **따로** 낸다. 둘을 한 칸에 두면 D-323 이 무의미해진다:
    **발급 완료 ≠ 전달 완료 ≠ 환경 존재.**
    """
    scope.require_actor()
    Record = _model("CredentialRecord")
    rows_by_name = {r.name: r for r in Record._base_manager.all()}
    out = []
    for name, spec in cred.CREDENTIALS.items():
        row = rows_by_name.get(name)
        observed = cred._observe(name)
        out.append({
            "name": name,
            "api_type": spec.api_type,
            "capability": spec.capability,
            "intended_use": spec.intended_use,
            "is_secret": spec.is_secret,
            "declared_status": spec.declared_status,
            "observed_status": observed,
            "usable_by_feature_code": (
                cred._at_least(observed, cred.MIN_USABLE) and bool(spec.capability.strip())),
            "owner_tenant": getattr(row, "group_id", None),
            "verified_at": getattr(row, "verified_at", None),
            "verified_by": getattr(row, "verified_by", "") if row else "",
            # ★ 값이 아니라 마스킹된 흔적. 없으면 빈 문자열이다.
            "masked": cred._mask(_raw(name)) if observed != cred.ABSENT else "",
        })
    return tuple(out)


def _raw(name: str) -> str:
    """환경변수 원값. **이 모듈 밖으로 나가는 유일한 통로는 `secret_for` 하나다.**"""
    import os

    return os.environ.get(cred._definition(name).env_var, "")


def credential_fact(*, scope: TenantScope, name: str) -> dict[str, Any]:
    """자격증명 하나에 대해 우리가 아는 사실. **조회는 감사에 남는다** (D-325 표 ②)."""
    spec = cred._definition(name)
    observed = cred._observe(name)
    if scope is not None and scope.actor is not None:
        audit._credential_access(actor=scope.actor, name=name,
                                outcome=audit.ALLOWED,
                                reason=f"조회 — 상태 {observed}")
    return {
        "name": name, "api_type": spec.api_type, "capability": spec.capability,
        "declared_status": spec.declared_status, "observed_status": observed,
        "is_secret": spec.is_secret,
        "masked": cred._mask(_raw(name)) if observed != cred.ABSENT else "",
    }


def secret_for(name: str, *, scope: TenantScope) -> str:
    """기능 코드가 **실제로 호출할 때** 쓰는 값. 여기가 유일한 출구다.

    ★ 두 조건을 넘지 못하면 값을 내주지 않는다 (D-328):
        ① 이 환경에서 관찰된 상태가 `typed` 이상 — **무엇인지 아는 키인가**
        ② `capability` 가 비어 있지 않다 — **무엇을 할 수 있는지 적혀 있는가**
    juso 사건이 정확히 ①에서 걸렸어야 했다. 걸릴 자리가 없어서 하루를 잃었다.
    """
    spec = cred._definition(name)
    observed = cred._observe(name)
    if not cred._at_least(observed, cred.MIN_USABLE) or not spec.capability.strip():
        if scope is not None and scope.actor is not None:
            audit._credential_access(actor=scope.actor, name=name,
                                    outcome=audit.DENIED,
                                    reason=f"상태 {observed} · capability "
                                           f"{'있음' if spec.capability.strip() else '없음'}")
        raise CredentialNotUsable(
            f"{name!r} 는 아직 기능 코드가 쓸 수 없다 — 이 환경 상태 '{observed}', "
            f"capability {'기재됨' if spec.capability.strip() else '**비어 있음**'}. "
            f"「있다」와 「무엇인지 안다」는 다른 사실이다(D-328). "
            f"쓰려면 표 ②의 상태를 typed 이상으로 올리고 capability 를 적어라")
    if scope is not None and scope.actor is not None:
        audit._credential_access(actor=scope.actor, name=name, outcome=audit.ALLOWED,
                                reason="기능 사용")
    return _raw(name)


def refresh_credential(*, scope: TenantScope, name: str, verified_by: str,
                       owner_tenant: int | None = None) -> dict[str, Any]:
    """이 환경을 다시 보고 표를 갱신한다. **진술이 아니라 확인 행위가 남긴다** (D-323).

    `verified_at`/`verified_by` 를 손으로 적지 않게 하는 것이 이 함수의 존재 이유다 —
    이것이 있어야 `blockers.yaml` 의 두 칸이 조회 결과가 된다(D-325).
    """
    scope.require_actor()
    cred._definition(name)
    observed = cred._observe(name)
    Record = _model("CredentialRecord")
    row, _ = Record._base_manager.get_or_create(name=name)
    row.status = observed
    row.api_type = cred.CREDENTIALS[name].api_type
    row.capability = cred.CREDENTIALS[name].capability
    if owner_tenant is not None:
        row.group_id = owner_tenant
    row.verified_at = timezone.now()
    row.verified_by = verified_by
    row.save()
    return {"name": name, "status": observed,
            "verified_at": row.verified_at, "verified_by": verified_by}
