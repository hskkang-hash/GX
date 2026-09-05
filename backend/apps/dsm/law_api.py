# -*- coding: utf-8 -*-
"""법·인증(영역 ⑧)의 HTTP 면 — LAW-02a · LAW-06 · LAW-07 (차선 L · 2026-09-05).

왜 `api.py` 옆에 **다른 파일**인가
----------------------------------
`apps/dsm/api.py` 는 이번 턴에 다른 차선이 쓰고 있다. 같은 파일에 두 차선이 들어가면
충돌하고, 충돌한 라우트 파일은 **라우팅 침묵**으로 나타난다 — 경로가 사라졌는데
오류도 안 난다. 그래서 컨트롤러를 하나 더 세우고 `urls.py` 에 한 줄로 등록한다.
`NinjaExtraAPI.register_controllers` 는 컨트롤러를 여럿 받는다.

    ⚠ **등록하지 않으면 라우트 열거기가 못 본다.** 못 보는 라우트는 트립와이어의
      눈 밖이고, 눈 밖의 라우트가 정확히 「문지기 없는 새 경로」가 된다(urls.py 머리말).

이 파일이 지키는 규약 — `api.py` 머리말과 **같다**
--------------------------------------------------
    ① 모든 라우트에 `auth=JwtOrInboundKey()` + `@tenant_scoped()`.
    ② 오류는 **HTTP 상태로.** `200 + {"success": false}` 를 만들지 않는다.
    ③ `response=<단일 스키마>` 를 선언하지 않는다 — 거부가 스키마를 통과해 사라진다.
    ④ 원시 타입 인자는 **질의(query)** 다. 화면은 `dsmPostQuery()` 로 부른다.

★ `from __future__ import annotations` 를 **쓰지 않는다** (D-378)
-----------------------------------------------------------------
미래 임포트가 켜지면 타입 주석이 문자열이 되고, `@tenant_scoped` 로 감싸인 핸들러의
`__globals__` 에서 그 문자열이 풀리지 않아 **라우트가 500 으로 죽는다.** 단위 시험은
그것을 못 잡는다 — 화면을 처음 띄운 순간에 나온다.

★ 지우는 라우트는 **전역 관리자만** 부른다
------------------------------------------
보존기간 집행은 지금 테넌트별이 아니다(`retention.py` 실측 ②). 테넌트 관리자가
누르면 남의 테넌트 영상까지 지워진다 — 그래서 실행은 전역 관리자만이고,
미리보기는 관리자면 볼 수 있다. **보는 것과 지우는 것을 다른 문으로 둔다.**
"""
from django.core.exceptions import PermissionDenied
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_roles import is_global_admin, is_tenant_admin
from common.tenant_scope import TenantScope, tenant_scoped


def _scope(request):
    """요청자에서 스코프를 만든다. 없으면 **401** — `api.py._scope` 와 같은 판단이다."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


def _admin(request):
    """관리자인가. 아니면 **403** — 청구인의 이름과 연락처가 실린 면이다."""
    scope = _scope(request)
    user = scope.require_actor()
    if not (is_global_admin(user) or is_tenant_admin(user)):
        raise HttpError(403, "이 화면은 관리자만 볼 수 있습니다.")
    return scope


@api_controller("", tags=["DSM 법·인증 (LAW-02a · LAW-06 · LAW-07)"])
class DsmLawAPI:
    """법·인증 면. **읽기가 기본이고, 지우는 문은 하나뿐이다.**"""

    # ═══════════════════════════════════════════════════════════════════
    # LAW-06 — 다섯 의무 자리표
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/law/ai-act/duties", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-06 자리표 — 테넌트 자료를 읽지 않지만 문지기는 단다")
    def ai_act_duties(self, request):
        """다섯 의무가 **제품의 어디에 사는가.** 없는 칸은 없다고 적혀 나온다."""
        from apps.dsm.ai_act import duty_table

        _scope(request)
        return duty_table()

    # ═══════════════════════════════════════════════════════════════════
    # LAW-02a — 보존 일수 선언 · 집행
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/law/retention", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-02a 보존 정책 — 설정 면과 같은 문지기를 쓴다")
    def retention_policy(self, request):
        """제품이 선언한 **영상 보관 기간**과 그 수의 출처, 그리고 「도는가」."""
        from apps.dsm.retention import policy

        _scope(request)
        return policy()

    @route.post("/law/retention/sweep", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-02a 보존기간 집행 — 되돌릴 수 없는 쓰기다")
    def retention_sweep(self, request, dry_run: bool = True, reason: str = ""):
        """보존기간을 집행한다. **`dry_run` 기본값이 참이다.**

        참이면 세기만 하고 아무것도 지우지 않는다. 거짓으로 부르는 것은
        **전역 관리자**만 할 수 있다 — 지금 이 집행은 테넌트별이 아니다.
        """
        from apps.dsm.retention import sweep

        scope = _admin(request)
        actor = scope.require_actor()
        if not dry_run and not is_global_admin(actor):
            raise HttpError(
                403, "영상 삭제 집행은 전역 관리자만 할 수 있습니다. "
                     "이 집행은 테넌트별로 나뉘지 않습니다.")
        if not dry_run and not (reason or "").strip():
            raise HttpError(
                422, "왜 지금 지우는지 사유가 필요합니다. "
                     "되돌릴 수 없는 일에는 사유가 남아야 합니다.")
        return sweep(dry_run=bool(dry_run), actor=actor, reason=reason)

    # ═══════════════════════════════════════════════════════════════════
    # LAW-07 — 열람·삭제 청구 (리터럴이 변수보다 **위에** 선다 · D-410)
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/law/privacy-requests", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-07 청구 목록 — 남의 테넌트 청구가 보이면 안 된다")
    def privacy_requests(self, request, limit: int = 100):
        """내 테넌트의 청구 목록."""
        from apps.dsm.privacy_request import list_requests

        return list_requests(scope=_admin(request), limit=int(limit))

    @route.post("/law/privacy-requests", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-07 청구 접수 — 접수는 테넌트 안에서만 생긴다")
    def privacy_request_accept(self, request, subject_name: str, contact: str,
                               kind: str = "열람", camera_id: int = 0,
                               note: str = ""):
        """청구를 접수한다. **접수 번호가 그 자리에서 나온다.**"""
        from apps.dsm.privacy_request import accept

        try:
            return accept(scope=_admin(request), subject_name=subject_name,
                          contact=contact, kind=kind,
                          camera_id=camera_id or None, note=note)
        except ValueError as exc:
            raise HttpError(422, str(exc)) from exc
        except PermissionDenied as exc:
            raise HttpError(403, str(exc)) from exc

    @route.get("/law/privacy-requests/{receipt_no}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-07 청구 상세 — 남의 테넌트 청구는 없는 것으로 답한다")
    def privacy_request_detail(self, request, receipt_no: str):
        """청구 한 건 + **회신 기록.**"""
        from apps.dsm.privacy_request import detail

        try:
            return detail(scope=_admin(request), receipt_no=receipt_no)
        except LookupError as exc:
            raise HttpError(404, str(exc)) from exc

    @route.get("/law/privacy-requests/{receipt_no}/masked", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-07 마스킹본 — 원본은 이 문으로도 나가지 않는다")
    def privacy_request_masked(self, request, receipt_no: str):
        """**마스킹본**만 낸다. 원본 객체 경로는 이 응답의 어느 칸에도 없다."""
        from apps.dsm.privacy_request import masked_view

        try:
            return masked_view(scope=_admin(request), receipt_no=receipt_no)
        except LookupError as exc:
            raise HttpError(404, str(exc)) from exc

    @route.post("/law/privacy-requests/{receipt_no}/reply", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-07 회신 기록 — 남의 테넌트 청구에 답할 수 없다")
    def privacy_request_reply(self, request, receipt_no: str, text: str,
                              outcome: str = ""):
        """회신을 **기록한다.** 보내지는 않는다 — 보내는 자리는 제품 밖이다."""
        from apps.dsm.privacy_request import reply

        try:
            return reply(scope=_admin(request), receipt_no=receipt_no,
                         text=text, outcome=outcome)
        except LookupError as exc:
            raise HttpError(404, str(exc)) from exc
        except ValueError as exc:
            raise HttpError(422, str(exc)) from exc
