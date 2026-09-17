# -*- coding: utf-8 -*-
"""WO-GX-20260915-01 §4.2 — 차선 **U3(현장 · 휴대전화)** 라우터 모듈. 이 파일은 U3 차선만 고친다.

규약은 `api_u1.py` 머리말과 같다: 기존 라우트는 옮기지 않는다 · `DsmAPI`·`DsmLawAPI` 뒤에
붙으므로 기존 경로에 다른 메서드를 더하지 않는다(405 삼킴) · 새 경로는 ISO-03·SEC-04·계약
도달을 태어날 때 통과한다.
"""
from django.http import Http404
from ninja import File
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from apps.dsm import field, notify_prefs as prefs


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401.** `api.py::_scope` 와 같은 규약 —

    파일마다 새 인증 경로를 만들지 않는다(`api_u1.py` 가 이미 같은 세 줄을 둔 이유와
    같다 — 공용부 `api.py` 는 조율자 소유라 이번 턴에 그 파일을 손대지 않는다).
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("", tags=["DSM — U3 현장 (WO-01 차선 U3)"])
class DsmU3API:
    """U3 차선의 새 라우트가 태어나는 자리(턴 Q 조율자 분할)."""

    # ── UX-45 M3 — 현장 사진 한 장 (P-141 · 턴 Q) ───────────────────────
    #
    # ★ 착수 시점에는 `dsm_field_photo` 모델이 없어 이 문을 걸지 않았다. 작업
    #   후반에 F-DB 차선이 모델을 세웠다(`stream_monitors/models.py::DsmFieldPhoto`
    #   · `stream_monitors/migrations/0029_v11_tables.py`) — 그래서 문을 연다.
    #   검증·저장은 `apps/dsm/field.py::save_field_photo` 가 한다(이 파일은 예외를
    #   상태 코드로 번역만 한다 — `field-reply` 라우트와 같은 얇은 자리).
    @route.post("/events/{int:event_id}/field-photo", auth=JwtOrInboundKey())
    @tenant_scoped(reason="현장 사진 쓰기 — 남의 이벤트에 사진을 붙일 수 없다 (쓰기 IDOR)")
    def upload_field_photo(
        self, request, event_id: int, photo: UploadedFile = File(...),
    ):
        """사진 1장을 올린다. **바이트 자체는 안 돌려준다** — 확인용 값만 낸다.

        상태 넷을 다르게 낸다 — 뭉치면 운영자가 어디를 고칠지 모른다:
            401 인증 없음 · 404 없는/남의 이벤트 · 403 요청자 없음(시스템 스코프) ·
            422 크기·형식 위반 · 503 저장소 연결 안 됨
        """
        try:
            result = field.save_field_photo(
                scope=_scope(request), event_id=event_id,
                content_type=photo.content_type or "", data=photo.read())
        except Http404:
            raise HttpError(404, "그런 이벤트가 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except field.FieldPhotoRejected as exc:
            raise HttpError(422, str(exc))
        except field.FieldPhotoStorageDown as exc:
            raise HttpError(503, str(exc))
        return result

    # ── CH-03 웹푸시 구독 (WS-08 · 턴 S) ─────────────────────────────────
    #
    # ⚠ **경로 순서** — 리터럴 둘(`vapid-key` · `test-send`)을 `{int:subscription_id}`
    #   **위**에 세운다. 지금은 `int` 변환기라 `vapid-key` 를 삼키지 않지만, 변환기가
    #   `{str:…}` 로 바뀌는 날 조용히 404 가 된다 — 조용한 404 는 「기능이 없다」와
    #   구별되지 않는다(D-410 이 남긴 자리 · 메모리 「라우트 삼킴 함정」).
    # ⚠ 구독은 **한 사람의 한 기기**의 것이다. 그래서 문지기가 둘이다:
    #   `@tenant_scoped`(기관) + `notify_prefs._rows_of`(요청자 자신) — 같은 기관
    #   동료의 휴대전화 구독이 내 목록에 보이면 그것도 누출이다.
    @route.get("/push-subscriptions/vapid-key", auth=JwtOrInboundKey())
    @tenant_scoped(reason="웹푸시 공개키 — 요청자 확인 뒤에 낸다. 값 자체는 공개지만 "
                          "「이 제품이 웹푸시를 쓴다」는 사실까지 익명에 열지 않는다")
    def push_vapid_key(self, request):
        """브라우저가 `pushManager.subscribe` 에 넣을 **공개키**.

        ★ **200 + `configured:false`** 로 낸다(501 이 아니다). 화면은 이 응답을 보고
          「알림 받기」 단추를 그릴지 말지를 정해야 하는데, 501 은 오류 상자로 그려지고
          그러면 「없는 것에 손잡이를 그리지 않는다」를 화면이 집행할 수 없다.
          **없음을 사유와 함께 말하는 200** 이 이 자리의 정직한 모양이다(D-284).
        ★ 비밀키는 이 경로가 **읽지도 않는다** — 읽는 곳은 발송 어댑터 한 곳이다.

        ★★ **값이 나가는 칸은 `public_key` 하나뿐이고, 그것은 의도된 것이다.**
          VAPID 공개키는 정의상 공개다 — 구독하는 모든 브라우저에
          `applicationServerKey` 로 들어가고, 그 값 하나로는 아무것도 보낼 수 없다
          (보내려면 **비밀키 서명**이 필요하다). 상태 쪽(`vapid_status`)은 값을
          한 글자도 들지 않으며 지문 12자로만 대조한다 — 그래서 로그·증거·캡처에
          값이 따라 나가는 자리가 없다(조율자 지시 · `verify_no_secret_echo`).
        """
        _scope(request)
        status = prefs.vapid_status()
        return {**status, "public_key": prefs.vapid_public_key()}

    @route.post("/push-subscriptions/test-send", auth=JwtOrInboundKey())
    @tenant_scoped(reason="시험 발송 — 남의 기기를 울릴 수 없다. 받는 사람은 "
                          "요청자 자신뿐이고 고를 인자가 없다")
    @idempotent("dsm.push-subscriptions.test-send")
    def push_test_send(self, request, title: str = "", body: str = ""):
        """내 기기로 **훈련 알림**을 한 번 보낸다 — 잠금화면 도달을 사람이 눈으로 본다.

        ⚠ **표 밖에서 태어난 면이다.** 선등록표(`docs/agent/write_surfaces_v11.yaml`)의
          WS-08 은 「구독」이고 발송은 그 표에 없다 — 조율자가 턴 S 선등록에서 바로 이
          자리를 「예상하지 못할 자리」로 지목했다. 지우지 않고 보고에 적는다.
        ⚠ `DeliveryRecord` 행을 만들지 않는다 — 이것은 경보가 아니다. 그 표에 끼우면
          F-10 지연 통계가 경보 아닌 것을 세고, 5분 억제가 **다음 진짜 경보를 삼킨다.**
        """
        try:
            return prefs.send_test_push(
                scope=_scope(request), title=title, body=body)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except prefs.PushSubscriptionRejected as exc:
            raise HttpError(422, str(exc))

    @route.post("/push-subscriptions", auth=JwtOrInboundKey())
    @tenant_scoped(reason="웹푸시 구독 등록 — 남의 계정에 내 기기를 물릴 수 없다 "
                          "(쓰기 IDOR). 구독은 한 번 걸면 계속 울린다")
    @idempotent("dsm.push-subscriptions")
    def create_push_subscription(self, request, endpoint: str, p256dh: str,
                                 auth_secret: str, label: str = ""):
        """이 기기를 등록한다.

        ★ 인자 이름이 `auth_secret` 인 것은 브라우저 쪽 이름(`keys.auth`)과 **일부러
          다르다**: `auth` 는 이 라우트의 문지기 인자(`@route.post(auth=…)`)와 같은
          낱말이라, 같은 이름을 쓰면 읽는 사람이 둘을 헷갈린다.
        ★ 응답에 **엔드포인트도 키도 실리지 않는다** — 지문 12자와 기기 이름뿐이다.
          푸시 엔드포인트는 그 기기로 알림을 밀어 넣는 주소이고, 한 번 새면 회수할 수
          없다(서명키를 한 번만 내보내는 D-335 ④ 와 같은 결).

        거절을 4xx 로 나눈다: 403 요청자 없음 · 422 값이 계약 밖(평문 http · 키 누락 ·
        기기 수 상한).
        """
        try:
            return prefs.subscribe(
                scope=_scope(request), endpoint=endpoint, p256dh=p256dh,
                auth_secret=auth_secret, label=label)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except prefs.PushSubscriptionRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/push-subscriptions", auth=JwtOrInboundKey())
    @tenant_scoped(reason="구독 목록 — 남의 기기가 보이면 안 된다")
    def list_push_subscriptions(self, request):
        """내 기기들. **내 것만** 나온다 — 기관 전체가 아니다(위 ⚠)."""
        try:
            rows = prefs.list_subscriptions(scope=_scope(request))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        #: 0 을 「없음」으로 적지 않는다 — 모수와 함께 낸다(D-301).
        return {"total": len(rows), "subscriptions": list(rows)}

    @route.delete("/push-subscriptions/{int:subscription_id}",
                  auth=JwtOrInboundKey())
    @tenant_scoped(reason="구독 해지 — 남의 기기를 끌 수 없다 (쓰기 IDOR). "
                          "끄면 그 사람의 경보가 조용히 멈춘다")
    def delete_push_subscription(self, request, subscription_id: int):
        """이 기기를 끈다. **행을 지우지 않는다** — 언제 무엇을 받았는지가 함께 사라진다.

        404 는 **남의 구독**일 때도 난다 — 존재 여부가 새는 것도 누출이다.
        """
        try:
            return prefs.unsubscribe(
                scope=_scope(request), subscription_id=subscription_id)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except prefs.PushSubscriptionNotFound as exc:
            raise HttpError(404, str(exc))

    # ── M4 「내 알림 설정」 (WS-02 · UX-43-M4 · 턴 S 골격) ────────────────
    #
    # ⚠ `/me/…` 는 새 접두다. `/settings/{domain}`(`api.py:1143`)에 안 걸린다 —
    #   그 와일드카드는 `/settings/` 아래 한 조각만 삼킨다(U56 이 `/settings/people`
    #   에서 실측으로 만난 그 함정).
    @route.get("/me/notify-prefs", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 알림 설정 읽기 — 남의 근무 시간·담당 구역은 내 것이 아니다")
    def get_notify_prefs(self, request):
        """내 설정. **없어도 모양은 같다** — 「아직 안 정했다」는 `saved:false` 다."""
        try:
            return prefs.notify_prefs(scope=_scope(request))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.put("/me/notify-prefs", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 알림 설정 쓰기 — 남의 설정을 바꾸면 그 사람이 "
                          "받아야 할 경보가 조용히 멈춘다 (쓰기 IDOR)")
    def put_notify_prefs(self, request, quiet_start: str = "", quiet_end: str = "",
                         zone_ids: str = "", channels: str = ""):
        """설정을 저장한다. 살아 있는 행은 **계정당 하나**다 (DB UNIQUE 가 함께 지킨다).

        ★ 이 설정은 규칙이 고른 수신을 **좁히기만** 한다 — 넓히지 못한다. 그래서 빈
          칸은 「아무것도 안 받는다」가 아니라 **「규칙 그대로 받는다」**이고, 응답의
          `note` 가 그 사실을 화면의 말로 들고 있다.
        ★ 차단 시간대를 한쪽만 채우면 **422 다.** DB CHECK 가 막는 자리를 사람의
          말로 먼저 막는다 — DB 오류로 떨어지면 화면이 무엇을 고칠지 모른다.
        """
        try:
            return prefs.save_notify_prefs(
                scope=_scope(request), quiet_start=quiet_start, quiet_end=quiet_end,
                zone_ids=zone_ids, channels=channels)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except prefs.NotifyPrefsRejected as exc:
            raise HttpError(422, str(exc))
