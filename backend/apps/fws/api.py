# -*- coding: utf-8 -*-
"""FWS App(L4)의 유일한 문 — **얇다**: 여기서 하는 일은 스코프를 만들고, 아래
기능 모듈(`patrol` · `risk` · `verification` · `alerts` · `notify_prefs` · `contacts`)을
부르고, 그 예외를 HTTP 상태로 옮기는 것뿐이다. 판정·저장은 전부 그 모듈들과
그 모듈들이 부르는 커널(K1·K2)에 있다 — `tests/test_fws_app.py::AppStaysThinTest`
가 이 파일이 모델을 직접 만지지 않는지를 잰다.

P-357 — FWS 는 새 앱이 아니다
------------------------------
프런트는 같은 SPA 의 `/fws/*` 라우트를 쓰고, 이 App 은 그 화면들의 서버 쪽 짝이다.
DSM 커널(K1 이벤트·K2 알림)을 공유한다 — 새 이벤트·발송 표를 만들지 않는다.


★ `from __future__ import annotations` 를 **쓰지 않는다** (D-378 · `apps/dsm/
law_api.py` 머리말과 같은 이유) — 미래 임포트가 켜지면 타입 주석이 문자열이
되고, `@tenant_scoped` 로 감싸인 핸들러의 `__globals__` 에서 그 문자열이 안
풀려 라우트가 500 으로 죽는다. 단위 시험은 그것을 못 잡는다.
"""

from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from apps.fws import alerts, contacts, notify_prefs, patrol, risk, verification


def _scope(request) -> TenantScope:
    """`apps/dsm/api_u1.py::_scope` 와 같은 세 줄 — 공용부(조율자 소유)를 이 턴에
    건드리지 않기 위해 그대로 옮겨 둔다."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("", tags=["FWS — 산불감시 (WO-15 §5 P-357 · 차선 N2)"])
class FwsAPI:
    # ── FWS-F1-01 근무 시작·초소 체크인 ─────────────────────────────────
    @route.post("/patrol/checkin", auth=JwtOrInboundKey())
    @tenant_scoped(reason="체크인은 이 사람의 근무 기록이다 — 남의 초소 상태를 "
                         "대신 켤 수 없다")
    @idempotent("fws.patrol.checkin")
    def patrol_checkin(self, request, post_code: str, method: str = "gps",
                      lat: float | None = None, lng: float | None = None):
        try:
            return patrol.checkin(scope=_scope(request), post_code=post_code,
                                  method=method, lat=lat, lng=lng)
        except patrol.PatrolInputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F1-02 순찰 경로 기록 ─────────────────────────────────────────
    @route.post("/patrol/track", auth=JwtOrInboundKey())
    @tenant_scoped(reason="트랙은 이 사람의 순찰 기록이다")
    @idempotent("fws.patrol.track")
    def patrol_track(self, request, post_code: str, lat: float | None = None,
                     lng: float | None = None, checkpoint_code: str = ""):
        try:
            return patrol.track(scope=_scope(request), post_code=post_code,
                                lat=lat, lng=lng, checkpoint_code=checkpoint_code)
        except patrol.PatrolInputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F1-11 내 근무 기록·순찰 실적 ─────────────────────────────────
    @route.get("/patrol/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 실적 — 본인 것만")
    def patrol_mine(self, request):
        return patrol.mine(scope=_scope(request))

    # ── FWS-F1-03 오늘 위험지수·위기경보·입산통제 ────────────────────────
    @route.get("/risk/today", auth=JwtOrInboundKey())
    @tenant_scoped(reason="오늘 위험지수는 테넌트 자료가 아니다(전국 공개 지수) — 만지는 테넌트 모델 0 · 선언만(ISO-03)")
    def risk(self, request):
        _scope(request)  # 인증만 확인 — 값은 테넌트 무관 공용 정보다
        return risk.risk_today()

    # ── FWS-F1-08 119·산림청 신고 번호 ──────────────────────────────────
    @route.get("/emergency-contacts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="신고 번호는 테넌트 자료가 아니다(119 · 산림청) — 만지는 테넌트 모델 0 · 선언만(ISO-03)")
    def emergency_contacts(self, request):
        # ★ [턴 AK · 조율자 병합] 차선은 익명으로 열었다(번호는 비밀이 아니다). 그러나 익명 표면은
        #   래칫(open_anonymous 73)이 지키는 자리이고 넓히는 것은 판정이 필요한 일이다 — 기본값은
        #   닫힌 쪽. 이 번호를 쓰는 화면(`/fws/home`)은 로그인 뒤에만 열리므로 닫아도 1탭은 그대로다.
        #   익명 공개가 필요하면(예: 로그인 전 화면) 세종 판정 뒤 `auth=None` 한 줄 + 래칫 기준선 +1.
        return contacts.emergency_contacts()

    # ── FWS-F1-05 확인 요청 수신 ─────────────────────────────────────────
    @route.get("/verifications/{int:verification_id}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 이벤트를 확인 요청으로 읽을 수 없다")
    def get_verification(self, request, verification_id: int):
        from django.http import Http404
        try:
            return verification.get_verification(
                scope=_scope(request), verification_id=verification_id)
        except Http404:
            raise HttpError(404, "그런 확인 요청이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F1-06 현장 확인 회신 ─────────────────────────────────────────
    @route.post("/verifications/{int:verification_id}/reply", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 이벤트에 회신·판정을 쓸 수 없다")
    @idempotent("fws.verifications.reply")
    def reply_verification(self, request, verification_id: int, result: str,
                           reason_code: str = "", note: str = ""):
        from django.http import Http404
        try:
            return verification.reply_verification(
                scope=_scope(request), verification_id=verification_id,
                result=result, reason_code=reason_code, note=note)
        except Http404:
            raise HttpError(404, "그런 확인 요청이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except verification.VerificationReplyRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F1-10 안전 알림 수신(도달·확인) ──────────────────────────────
    @route.get("/alerts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 앞으로 온 발송만")
    def my_alerts(self, request):
        return {"alerts": alerts.my_alerts(scope=_scope(request))}

    @route.post("/alerts/{int:delivery_id}/ack", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 목록에 있는 알림만 확인할 수 있다")
    @idempotent("fws.alerts.ack")
    def ack_alert(self, request, delivery_id: int):
        try:
            return alerts.ack_alert(scope=_scope(request), delivery_id=delivery_id)
        except alerts.AlertNotFound as exc:
            raise HttpError(404, str(exc))

    # ── FWS-F1-12 근무 외 알림 차단·담당 초소 설정 ───────────────────────
    @route.get("/notify-prefs", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인 설정만 읽는다")
    def get_notify_prefs(self, request):
        return notify_prefs.get_prefs(scope=_scope(request))

    @route.post("/notify-prefs", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인 설정만 쓴다")
    def save_notify_prefs(self, request, quiet_hours_start: str = "",
                          quiet_hours_end: str = "", assigned_post_code: str = ""):
        try:
            return notify_prefs.save_prefs(
                scope=_scope(request), quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end,
                assigned_post_code=assigned_post_code)
        except notify_prefs.NotifyPrefsRejected as exc:
            raise HttpError(422, str(exc))
