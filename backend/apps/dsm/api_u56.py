# -*- coding: utf-8 -*-
"""WO-GX-20260915-01 §4.2 — 차선 **U56(관리자 · 연계)** 라우터 모듈. 이 파일은 U56 차선만 고친다.

규약은 `api_u1.py` 머리말과 같다: 기존 라우트는 옮기지 않는다 · `DsmAPI`·`DsmLawAPI` 뒤에
붙으므로 기존 경로에 다른 메서드를 더하지 않는다(405 삼킴) · 새 경로는 ISO-03·SEC-04·계약
도달을 태어날 때 통과한다.

턴 R 에 여기서 태어나는 것 셋
------------------------------
    ① S-14 「사람·역할」— `apps/dsm/people.py`(턴 Q 골격)를 **처음으로 부르는 자리**
       (P-141 잠든 코드 게이트 — 시험만 부르는 것은 운영에서는 죽은 것이다).
    ② P-145 웹훅 서명키 — 구독 등록과 서명키 발급을 한 번에(`webhook_key_service.py`).
    ③ 문지기는 전부 `guard_setting`(F-12 의 유일한 판정식, D-212) — 여기서 새
       판정을 짓지 않는다.
"""
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import TenantScope, tenant_scoped


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401.** `api.py::_scope` 와 같은 규약 —

    파일마다 새 인증 경로를 만들지 않는다. 이 한 줄은 `TenantScope.of` 를 감쌀
    뿐이고, 두 파일이 갈릴 자리가 아니다(공용부 `api.py` 는 조율자 소유라 이번
    턴에 그 파일을 손대지 않는다 — 대신 같은 세 줄을 여기 그대로 둔다, `api_u1.py`
    와 동일 규약).
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


def _bearer_header(request) -> dict:
    """이 요청이 들고 온 `Authorization` 을 **그대로** 다음 문에 옮긴다.

    ★ 새 인증 경로를 만들지 않는다 — `people.create_person`/`deactivate_person`
      이 요구하는 `actor_bearer_header` 는 dj-core 의 실제 생성·비활성화 경로를
      두드릴 때 쓸 자격이고, 그 자격은 **지금 이 요청을 인증한 바로 그 토큰**이어야
      한다(둘이 다르면 "누가 만들었나"와 "누가 인증했나"가 갈린다).
    """
    header = request.META.get("HTTP_AUTHORIZATION")
    if not header:
        raise HttpError(401, "인증이 필요합니다.")
    return {"HTTP_AUTHORIZATION": header}


@api_controller("", tags=["DSM — U5·U6 관리자·연계 (WO-01 차선 U56)"])
class DsmU56API:
    """U56 차선의 새 라우트가 태어나는 자리(턴 Q 조율자 분할 · 처음엔 비어 있다)."""

    # ── S-14 「사람·역할」— people.py 를 처음 부르는 자리 (UX-42 #1·#2·#3) ──
    #
    # ⚠ **경로 함정** [실측 · 턴 R] `/settings/people`(한 조각)은 `api.py:1143`
    #   `GET /settings/{domain}` 에 **삼켜진다** — Django 는 메서드보다 경로를
    #   먼저 맞춰 보고, 그 와일드카드가 `DsmAPI`(먼저 등록)에 있어 한 조각짜리
    #   `/settings/<무엇>` 은 전부 그 GET 문 앞에서 잡혀 POST 가 405 로 죽는다
    #   (라우트 삼킴 · 메모리 「라우트 삼킴 함정」과 같은 모양 — [실측 2026-09-16]).
    #   그래서 두 조각으로 연다: `/settings/people/create`.
    @route.post("/settings/people/create", auth=JwtOrInboundKey())
    @tenant_scoped(reason="S-14 사람 만들기 — 설정 문(F-12)과 같은 문지기를 쓴다. "
                         "계정 생성은 테넌트 하나를 늘리는 쓰기라 무권한이면 "
                         "쓰기 IDOR 만큼 위험하다")
    def create_person(self, request, username: str, email: str, password: str,
                      group_id: int, role_ids: str = "", display_name: str = "",
                      employee_id: str = ""):
        """UX-42 #1·#2 — 계정을 만들고 역할을 붙인다. **관리자만** 지난다.

        ★ 판정은 여기서 한다 — dj-core 의 `create-user` 뷰 자체엔 권한 검사가
          없다(`people.py::create_person` 머리말의 실측). 그 문 앞에 `guard_setting`
          을 세우지 않으면 **로그인한 아무나** 계정을 만들 수 있다 — 이 라우트가
          바로 그 앞자리다.
        ★ `role_ids` 는 쉼표로 구분한 정수 문자열이다(`event_types` 와 같은 관용 —
          `api.py::create_webhook_subscription` 머리말 참고). 비우면 dj-core 가
          기본 역할을 스스로 채운다(`people.py` 주석).
        """
        from apps.dsm import people
        from apps.dsm.services import guard_setting

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="write:people:create:%s" % username,
            api_method="POST")
        if not access.allowed:
            raise HttpError(403, access.reason)

        bearer = _bearer_header(request)
        ids = [int(x) for x in role_ids.split(",") if x.strip()]
        try:
            created = people.create_person(
                actor_bearer_header=bearer, username=username, email=email,
                password=password, group_id=group_id, role_ids=ids,
                display_name=display_name, employee_id=employee_id or None)
        except people.PersonOpError as exc:
            code = exc.status_code if exc.status_code in (400, 401, 403, 409) else 422
            raise HttpError(code, exc.body[:400])

        return {"user_id": created.user_id, "username": created.username,
                "audit_id": access.audit_id}

    @route.post("/settings/people/{int:user_id}/deactivate", auth=JwtOrInboundKey())
    @tenant_scoped(reason="S-14 사람 비활성화 — 관리자만. 남의 계정을 끌 수 없다")
    def deactivate_person(self, request, user_id: int):
        """UX-42 #3 — 계정을 끈다(`is_active=False`). **행을 지우지 않는다.**

        ★ 누가 끌 수 있는지는 여기(`guard_setting`)가 정한다 — `people.deactivate_person`
          은 그 판정을 하지 않는다(그 파일 머리말, D-212 — 판정을 두 벌 두지 않는다).
          비활성화 뒤 **이미 발급된 토큰**이 막히는 것은 dj-core `CustomJWTAuth` 의
          기존 경로다(새 인증 경로를 만들지 않는다).
        """
        from apps.dsm import people
        from apps.dsm.services import guard_setting

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="write:people:deactivate:%s" % user_id,
            api_method="POST")
        if not access.allowed:
            raise HttpError(403, access.reason)

        bearer = _bearer_header(request)
        try:
            people.deactivate_person(actor_bearer_header=bearer, user_id=user_id)
        except people.PersonOpError as exc:
            code = exc.status_code if exc.status_code in (400, 401, 403, 404, 409) else 422
            raise HttpError(code, exc.body[:400])

        return {"user_id": user_id, "deactivated": True, "audit_id": access.audit_id}

    # ── P-145 웹훅 서명키 — 구독 등록 + 발급을 한 번에 ─────────────────────
    #   ⚠ 같은 함정 — 한 조각 `/settings/webhook-subscriptions` 도 `/settings/{domain}`
    #     에 삼켜진다. 두 조각(`/issue`)으로 연다(위 people 과 같은 실측).
    @route.post("/settings/webhook-subscriptions/issue", auth=JwtOrInboundKey())
    @tenant_scoped(reason="P-145 서명키 발급 — 상대에게 우리 이름으로 경보를 낼 "
                         "자격을 여는 쓰기다. 설정 문(F-12)과 같은 무게로 지킨다")
    def issue_webhook_subscription(self, request, endpoint_url: str,
                                   event_types: str = "", min_severity: str = "",
                                   payload_format: str = "json"):
        """P-145 — **서명키를 우리가 만들어** 구독에 물린다. 값은 응답에 **한 번만**.

        ★ 기존 `POST /webhook-subscriptions`(`api.py`)를 대신하지 않는다 — 그 문은
          "이름을 이미 아는 상대"(운영자가 미리 값을 나눈 자리)를 위해 그대로 남는다.
          이 문은 **이름조차 몰라도** 되는 새 경로다(라우트 삼킴 없음 — 경로가
          `/settings/` 로 다르다).
        ★ 값은 여기서만 나온다. 그 뒤 `GET /webhook-subscriptions` 목록에는
          `signing_key_ref`(이름)만 있고 값은 없다(`api.py::_subscription_payload`).
        """
        from apps.dsm.exceptions import PermissionDeniedForSetting
        from apps.dsm.webhook_key_service import issue_webhook_subscription as _issue
        from common.tenant_scope import SystemScopeCannotRead
        from common.webhook_outbox import WebhookSubscriptionError

        types = tuple(t.strip() for t in (event_types or "").split(",") if t.strip())
        try:
            result = _issue(
                scope=_scope(request), endpoint_url=endpoint_url,
                event_types=types, min_severity=min_severity,
                payload_format=payload_format)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, exc.reason)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except WebhookSubscriptionError as exc:
            raise HttpError(422, str(exc))
        return result
