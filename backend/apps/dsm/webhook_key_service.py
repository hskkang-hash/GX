# -*- coding: utf-8 -*-
"""U56 차선 전용 — P-145 웹훅 서명키 발급을 구독 등록과 묶는다.

왜 `apps/dsm/services.py` 가 아니라 여기인가
---------------------------------------------
그 파일은 F-09~F-12 전체가 쓰는 공용부이고 같은 턴에 다른 차선도 고친다. U1 이
`event_note_service.py` · `handover_service.py` 를 따로 둔 것과 같은 이유로(그
파일들의 머리말 참고), 이 차선의 새 조립도 **차선 전용 파일**에 둔다 — 공용 파일에
줄을 끼우면 같은 턴의 다른 차선과 충돌하고, 충돌한 서비스 파일은 조용히 한쪽
로직을 지운다.

이 파일이 하는 일 — **구독 등록과 서명키 발급을 한 동작으로 묶는다**
--------------------------------------------------------------------
호출자(U6 연계 담당)는 서명키 **이름**조차 몰라도 된다 — 이 함수가 이름을 만들고
(`kernels.k5_trust.signing_key_name_for`), 값을 만들고(`generate_signing_key`),
그 값을 `common.webhook_outbox.register()`(기존 F-05 등록 문)에 물린 뒤 **응답에
한 번만** 싣는다. 그 뒤로는 회전(`/rotate`)만 값을 새로 낸다.

문지기 — **설정 문(F-12)과 같은 무게**
----------------------------------------
서명키를 만드는 것은 "상대에게 우리 이름으로 경보를 낼 자격"을 여는 일이다 —
임계값·인바운드 API 키 발급과 같은 급이다. 그래서 판정을 새로 짓지 않고
`apps.dsm.services.guard_setting`(F-12 의 유일한 판정식, D-212)을 그대로 부른다.

★ 실패 순서 — **키를 만들기 전에 먼저 걸러낸다**
--------------------------------------------------
`common.webhook_outbox.validate_endpoint()` 를 키 생성 **앞에** 부른다. 순서를
바꾸면(등록 실패 뒤에 발견) 아무 구독에도 안 물린 값이 이번 프로세스의 표에
남는다 — 새지는 않지만(반환도 저장도 안 한다) 깨끗하지 않다. 구독 상한
(`MAX_SUBSCRIPTIONS_PER_TENANT`)까지는 여기서 미리 재지 않는다 — 그 수를 여기서
다시 세면 두 벌이 되고(D-212), 상한을 넘긴 드문 경우에 쓰이지 않는 값 하나가
프로세스 메모리에 남는 것은 감수한다(재시작하면 사라진다 · 저장되지 않는다).
"""
from __future__ import annotations

from typing import Any

from apps.dsm import audit
from apps.dsm.exceptions import PermissionDeniedForSetting
from common.tenant_scope import TenantScope


def issue_webhook_subscription(*, scope: TenantScope, endpoint_url: str,
                               event_types=None, min_severity: str = "",
                               payload_format: str = "json",
                               filters=None) -> dict[str, Any]:
    """P-145 — 서명키를 **우리가 만들어** 구독에 물린다. 값은 반환값에 한 번만 있다.

    ★ [턴 T · WS-17] `filters` 를 함께 받는다 — 계약 모양이 아니면 **키를 만들기 전에**
      거절한다(`InvalidWebhookFilters` · 위 「실패 순서」와 같은 이유).
    """
    from apps.dsm.services import guard_setting, register_webhook_subscription
    from common.webhook_outbox import validate_endpoint
    from kernels.k5_trust import generate_signing_key, signing_key_name_for

    spec = normalize_filters(filters)

    access = guard_setting(
        scope=scope, action="write:webhook_signing_key:issue:%s" % endpoint_url,
        api_method="POST")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)

    # ★ 걸러낼 것부터 건다 — 키를 만들기 전에 주소부터 본다(위 머리말 「실패 순서」).
    validate_endpoint(endpoint_url)

    # ★ 소속을 여기서 묻지 않는다 — **커널이 `scope` 에서 직접 묻는다**(D-281 · 턴 R).
    #   1차판은 여기서 `require_user_group(actor)` 로 숫자를 뽑아 커널에 건넸다.
    #   숫자를 건네면 「어느 테넌트의 이름인가」를 커널이 아니라 호출자가 정하게 되고,
    #   그러면 다음 호출자가 다른 숫자를 넣는 날 아무도 막지 못한다.
    name = signing_key_name_for(scope=scope)
    issued = generate_signing_key(scope=scope, name=name)

    sub = register_webhook_subscription(
        scope=scope, endpoint_url=endpoint_url, signing_key_ref=issued.name,
        event_types=event_types, min_severity=min_severity,
        payload_format=payload_format)

    # ★ [WS-17] filters 는 등록 문(`register`)에 칸이 없다 — 등록 뒤 같은 행에 쓴다.
    #   `register` 는 F-05 공용 문이라 이 차선이 시그니처를 넓히지 않는다.
    if spec:
        from common.webhook_outbox import _model
        Subscription = _model("WebhookSubscription")
        Subscription._base_manager.filter(pk=sub.subscription_id).update(filters=spec)

    # ★ 감사에는 **지문(sha256 앞 12자)만** — 값은 여기에도, 그 어디에도 두 번 적지 않는다.
    audit.record(
        scope=scope, action="write:webhook_signing_key:issued:%s" % issued.name,
        outcome=audit.ALLOWED,
        reason="구독 등록과 함께 서명키 생성 (P-145 · SEC-16)",
        after={"signing_key_name": issued.name, "sha256_12": issued.sha256_12},
        api_name="issue_webhook_subscription", api_method="POST", status_http=200)

    return {
        "subscription_id": sub.subscription_id,
        "endpoint_url": sub.endpoint_url,
        "event_types": list(sub.event_types),
        "min_severity": sub.min_severity,
        "payload_format": sub.payload_format,
        "is_active": sub.is_active,
        "signing_key_name": issued.name,
        # ★ 값은 여기 **한 번만** 실린다 — 조회(`GET /webhook-subscriptions`)는
        #   이 칸을 만들지 않는다(그 라우트는 `signing_key_ref` 이름만 낸다).
        "signing_key_secret": issued.secret,
        "filters": spec,
        "audit_id": access.audit_id,
    }


# ═══════════════════════════════════════════════════════════════════════════
# WS-17 「webhook filters」 — 사건 종류 · 심각도 · 카메라 (턴 T · 차선 U56)
# ═══════════════════════════════════════════════════════════════════════════
#
# 표는 이미 있다 — `WebhookSubscription.filters`(JSONField · F 가 턴 Q 에 팠다). 없던 것은
# **그 칸을 채우는 문**과 **그 칸을 읽고 거르는 판정**이다. 이 파일이 둘을 다 가진다:
#   · `normalize_filters()`   호출자가 준 JSON 을 계약 모양으로 좁힌다(모르는 키는 거절)
#   · `set_subscription_filters()`  내 테넌트의 구독 한 줄에 filters 를 쓴다(쓰기 면 WS-17)
#   · `subscription_accepts()`  이 구독이 이 사건을 받는가 — **빈 dict 는 「거르지 않는다」**
#
# ⚠ 발송기(`common/webhook_outbox.py::_passes_filter`)는 이 차선 소유가 아니다. 그 함수가
#   `subscription_accepts(row.filters, event)` 를 한 줄 부르기 전까지 filters 는 **저장은
#   되지만 발송을 거르지 않는다** — 등록 요청으로 조율자에게 넘긴다(보고 ③).

#: 계약 키 셋. 값은 전부 **문자열 목록**이다(카메라는 stream_monitor id 를 문자열로).
FILTER_KEYS = ("type", "severity", "camera")
_MAX_ITEMS_PER_KEY = 200


class InvalidWebhookFilters(ValueError):
    """filters 가 계약 모양이 아니다 — 400 감이다(요청이 틀렸다)."""


def normalize_filters(raw) -> dict[str, list[str]]:
    """`{"type": [...], "severity": [...], "camera": [...]}` 로 좁힌다.

    ★ 모르는 키는 **거절**한다(조용히 버리면 「zone 으로 걸었다」고 믿는 상대가 생긴다).
    ★ 빈 목록 키는 지운다 — 저장된 모양에서 「빈 목록」과 「없음」이 같은 뜻이기 때문이다.
    """
    if raw is None or raw == "":
        return {}
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except ValueError as exc:
            raise InvalidWebhookFilters("filters 는 JSON 객체여야 합니다: %s" % exc)
    if not isinstance(raw, dict):
        raise InvalidWebhookFilters("filters 는 JSON 객체여야 합니다.")
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        if key not in FILTER_KEYS:
            raise InvalidWebhookFilters(
                "모르는 필터 키 %r — 허용: %s" % (key, ", ".join(FILTER_KEYS)))
        if value is None:
            continue
        if isinstance(value, (str, int)):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise InvalidWebhookFilters("필터 %r 의 값은 목록이어야 합니다." % key)
        items = sorted({str(v).strip() for v in value if str(v).strip()})
        if len(items) > _MAX_ITEMS_PER_KEY:
            raise InvalidWebhookFilters(
                "필터 %r 의 항목이 상한(%d)을 넘습니다." % (key, _MAX_ITEMS_PER_KEY))
        if items:
            out[key] = items
    return out


def subscription_accepts(filters, event) -> bool:
    """이 filters 아래에서 이 사건이 나가는가. **빈 dict 는 전부 통과**다.

    `event` 는 `event_type` · `severity` · `stream_monitor_id` 를 가진 무엇이든 된다
    (모델도, 시험의 가짜도). 키가 있는데 사건이 그 목록 밖이면 거른다.
    """
    spec = filters or {}
    if not isinstance(spec, dict):
        return True
    types = spec.get("type") or []
    if types and str(getattr(event, "event_type", "")) not in set(map(str, types)):
        return False
    sevs = spec.get("severity") or []
    if sevs and str(getattr(event, "severity", "")) not in set(map(str, sevs)):
        return False
    cams = spec.get("camera") or []
    if cams:
        cam_id = getattr(event, "stream_monitor_id", None)
        if cam_id is None or str(cam_id) not in set(map(str, cams)):
            return False
    return True


def get_subscription_filters(*, scope: TenantScope, subscription_id: int) -> dict[str, Any]:
    """내 테넌트의 구독 한 줄의 filters 를 읽는다. 남의 것은 404(존재 여부도 새지 않는다)."""
    from common.tenant_filters import assert_scoped
    from common.webhook_outbox import _model

    actor = scope.require_actor()
    Subscription = _model("WebhookSubscription")
    assert_scoped(Subscription, subscription_id, actor)
    row = Subscription._base_manager.filter(pk=subscription_id).first()
    if row is None:  # pragma: no cover - assert_scoped 가 먼저 404 를 낸다
        from django.http import Http404
        raise Http404("그런 구독이 없습니다.")
    return {"subscription_id": row.pk, "filters": dict(row.filters or {}),
            "is_active": row.is_active}


def set_subscription_filters(*, scope: TenantScope, subscription_id: int,
                             filters) -> dict[str, Any]:
    """WS-17 — 구독 한 줄에 filters 를 쓴다. **문지기는 `guard_setting`**(F-12 와 같은 무게).

    ★ 남의 구독은 404 다(`assert_scoped` 규약 · D-269). 403 은 존재를 새게 한다.
    ★ 되돌리기는 빈 객체 `{}` 를 저장하는 것이다 — 「거르지 않는다」로 돌아간다.
    """
    from apps.dsm.services import guard_setting
    from common.tenant_filters import assert_scoped
    from common.webhook_outbox import _model

    spec = normalize_filters(filters)
    access = guard_setting(
        scope=scope, action="write:webhook_filters:%s" % subscription_id,
        api_method="POST")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)

    actor = scope.require_actor()
    Subscription = _model("WebhookSubscription")
    assert_scoped(Subscription, subscription_id, actor)
    row = Subscription._base_manager.filter(pk=subscription_id).first()
    if row is None:  # pragma: no cover - assert_scoped 가 먼저 404 를 낸다
        from django.http import Http404
        raise Http404("그런 구독이 없습니다.")
    before = dict(row.filters or {})
    row.filters = spec
    row.save(update_fields=["filters"])
    audit.record(
        scope=scope, action="write:webhook_filters:%s" % subscription_id,
        outcome=audit.ALLOWED, reason="구독 필터 저장 (WS-17)",
        before={"filters": before}, after={"filters": spec},
        api_name="set_subscription_filters", api_method="POST", status_http=200)
    return {"subscription_id": row.pk, "filters": spec, "is_active": row.is_active,
            "audit_id": access.audit_id}


__all__ = ["issue_webhook_subscription", "normalize_filters", "subscription_accepts",
           "get_subscription_filters", "set_subscription_filters",
           "InvalidWebhookFilters", "FILTER_KEYS"]
