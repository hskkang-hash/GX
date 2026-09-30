# -*- coding: utf-8 -*-
"""DSM-U2-04 — **임계값 도달 알림**
(`POST /api/dsm/thresholds/observe` · `POST /api/dsm/thresholds/observe/{id}/decide`)
차선 N1 · 턴 AK.

명세(§4.2)의 완결 조건은 **「도달 시각·결정 시각 둘 다 감사」** — 궁평2 감사 쟁점이
바로 이 둘의 구별(도달했다 vs 조치했다)이다. 그래서 이 파일은 두 걸음으로 가른다:
「도달」한 번 감사(`observe`) · 그 뒤 사람이 누른 「결정」을 별도 감사(`decide`)로
남긴다 — 한 행을 고쳐 쓰지 않는다(감사는 덮어쓰지 않는다, `event_note_service` 와
같은 판단).

**값 판정을 복사하지 않는다** — 임계값 정의·유효 범위·카메라별 지점 기준선은
전부 `kernels.k5_trust.services.resolve_threshold` 가 이미 갖고 있다(F-12 가 쓰는
그 커널). 여기서 다시 판정하면 두 벌이 되고, 두 벌은 반드시 어긋난다(D-212 계열).
카메라 소유 확인(IDOR 차단)도 그 커널이 이미 한다 — `decide()` 가 다시 확인할 때도
새 문지기를 만들지 않고 **같은 함수를 다시 부른다**(값은 버리고 문지기 효과만 쓴다).
"""
from __future__ import annotations

import re
from typing import Any

from common import audit_writer
from common.tenant_scope import TenantScope

LOGGER_NAME = "guardianx.u2.threshold_alert"
TAG = "[U2-THRESHOLD]"

#: 「도달」 행의 action 모양 — key 는 점을 포함할 수 있으므로(`waterlevel.baseline`)
#: camera_id 는 **끝의 숫자**로 가른다.
_REACHED_RE = re.compile(r"^threshold_reached:(?P<key>.+):(?P<camera_id>\d+)$")


def _reached_action(key: str, camera_id: int) -> str:
    return f"threshold_reached:{key}:{camera_id}"


def _decision_action(observation_id: int) -> str:
    return f"threshold_decision:{observation_id}"


def observe(*, scope: TenantScope, camera_id: int, key: str,
           value: float) -> dict[str, Any]:
    """외부 관측값(API·수동) 하나를 임계값과 견준다. **닿았을 때만 감사에 남긴다.**

    Raises:
        django.http.Http404: 카메라가 없다 · 남의 테넌트 카메라(커널 문지기).
        kernels.k5_trust.exceptions.ThresholdNotDefined: `key` 오타.
        kernels.k5_trust.exceptions.ThresholdNotSet: 이 카메라에 아직 기준선이
            없다(F-12 관리자가 먼저 정한다 — 여기서 지어내지 않는다, D-280).
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from kernels.k5_trust.services import resolve_threshold

    threshold = resolve_threshold(key, scope=scope, camera_id=camera_id)
    actor = scope.require_actor()

    reached = value >= threshold
    if not reached:
        return {"reached": False, "key": key, "camera_id": camera_id,
                "value": value, "threshold": threshold, "observation_id": None}

    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_reached_action(key, camera_id), outcome=audit_writer.ALLOWED,
        reason=(f"관측값 {value} ≥ 기준 {threshold} — 통제 여부 결정 필요 "
                f"(key={key} · camera={camera_id})"),
        api_method="POST",
    )
    return {"reached": True, "key": key, "camera_id": camera_id,
            "value": value, "threshold": threshold,
            "observation_id": entry.audit_id}


def decide(*, scope: TenantScope, observation_id: int,
          decision: str) -> dict[str, Any]:
    """도달 카드의 「결정」 버튼 — 결정 시각을 별도 감사 줄로 남긴다.

    Raises:
        ValueError: `decision` 이 비었다.
        django.http.Http404: 그런 도달 기록이 없다 · 남의 테넌트 카메라의 기록이다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.http import Http404

    from kernels.k5_trust.services import resolve_threshold

    decision = (decision or "").strip()
    if not decision:
        raise ValueError("통제 여부 결정이 비어 있습니다.")

    found = None
    for e in audit_writer.read(logger_name=LOGGER_NAME, limit=500):
        if e.audit_id == observation_id and e.action.startswith("threshold_reached:"):
            found = e
            break
    if found is None:
        raise Http404("그런 임계값 도달 기록이 없습니다.")

    match = _REACHED_RE.match(found.action)
    if not match:  # pragma: no cover - 이 파일이 쓴 모양이 아니면 여기 올 수 없다
        raise Http404("그런 임계값 도달 기록이 없습니다.")
    key, camera_id = match.group("key"), int(match.group("camera_id"))

    # ★ 카메라 소유 확인(IDOR 차단)을 다시 만들지 않는다 — `resolve_threshold` 안의
    #   `assert_scoped` 가 남의 테넌트 카메라면 여기서 Http404 를 던진다. 값은 버린다.
    resolve_threshold(key, scope=scope, camera_id=camera_id)

    actor = scope.require_actor()
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_decision_action(observation_id), outcome=audit_writer.ALLOWED,
        reason=f"관측#{observation_id} 결정: {decision}", api_method="POST",
    )
    return {"observation_id": observation_id, "decision_id": entry.audit_id,
            "decision": decision, "key": key, "camera_id": camera_id}


#: [턴 AQ · 차선 W2B] 도달 카드 문구 — 명세 §4.2 DSM-U2-04 원문
#: 「기준 도달 03:40 · 통제 여부 결정 필요」의 모양 그대로(시각만 실제 도달 시각).
NOTICE_FMT = "기준 도달 {hhmm} · 통제 여부 결정 필요"


def list_alerts(*, scope: TenantScope, limit: int = 50) -> list[dict[str, Any]]:
    """팀장·U4 홈의 **도달 카드** 목록 — 최신 먼저 · **내 테넌트 카메라 것만**.

    도달 줄(`threshold_reached:*`)마다 그 뒤 결정 줄(`threshold_decision:{id}`)이
    있으면 결정됨으로 읽는다. 새 표를 만들지 않는다 — `observe`/`decide` 가 남긴
    감사 두 줄이 곧 카드의 전부다.

    ★ 테넌트 문지기를 새로 세우지 않는다 — `decide()` 와 같은
      `common.tenant_filters.assert_scoped`(StreamMonitor) 가 남의 카메라면
      Http404 를 던지고, 그 줄은 목록에서 빠진다(존재를 안 알린다).

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.apps import apps
    from django.http import Http404
    from django.utils import timezone

    from common.tenant_filters import assert_scoped

    actor = scope.require_actor()
    rows = audit_writer.read(logger_name=LOGGER_NAME, limit=500)
    decisions = {}
    for e in rows:
        if e.action.startswith("threshold_decision:"):
            obs = int(e.action.rsplit(":", 1)[1])
            decisions.setdefault(obs, e)  # 최신이 먼저 — 첫 것이 마지막 결정

    stream_model = apps.get_model("stream_monitors", "StreamMonitor")
    allowed: dict[int, bool] = {}
    reached = []
    for e in rows:
        match = _REACHED_RE.match(e.action)
        if not match:
            continue
        camera_id = int(match.group("camera_id"))
        if camera_id not in allowed:
            try:
                assert_scoped(stream_model, camera_id, actor)
                allowed[camera_id] = True
            except Http404:
                allowed[camera_id] = False
        if allowed[camera_id]:
            reached.append((e, match.group("key"), camera_id))
        if len(reached) >= limit:
            break

    log_model = apps.get_model("logger", "AuditLogs")
    ids = [e.audit_id for e, _, _ in reached] + [
        d.audit_id for d in decisions.values()]
    stamps = dict(log_model._base_manager.filter(pk__in=ids)
                  .values_list("pk", "created_on"))

    def _hhmm(pk):
        at = stamps.get(pk)
        return timezone.localtime(at).strftime("%H:%M") if at else ""

    out = []
    for e, key, camera_id in reached:
        d = decisions.get(e.audit_id)
        reached_hhmm = _hhmm(e.audit_id)
        out.append({
            "observation_id": e.audit_id,
            "key": key,
            "camera_id": camera_id,
            "reached_at": stamps.get(e.audit_id),
            "notice": NOTICE_FMT.format(hhmm=reached_hhmm or "--:--"),
            "detail": e.reason,
            "decided": d is not None,
            "decision": (d.reason.split("결정: ", 1)[-1] if d else ""),
            "decided_at": stamps.get(d.audit_id) if d else None,
        })
    return out
