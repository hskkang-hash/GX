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
                               payload_format: str = "json") -> dict[str, Any]:
    """P-145 — 서명키를 **우리가 만들어** 구독에 물린다. 값은 반환값에 한 번만 있다."""
    from apps.dsm.services import guard_setting, register_webhook_subscription
    from common.webhook_outbox import validate_endpoint
    from kernels.k5_trust import generate_signing_key, signing_key_name_for

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
        "audit_id": access.audit_id,
    }


__all__ = ["issue_webhook_subscription"]
