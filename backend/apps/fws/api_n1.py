# -*- coding: utf-8 -*-
"""FWS-F6-07 반쪽 채움 — 웹푸시 **훈련** 채널 연계 (턴 AN · WO-GX-20260929-17 ·
차선 N1 · P-392 「반쪽 여섯 채우기」).

★ **이 파일은 아직 `apps/fws/urls.py` 에 등록되지 않았다** — 그 파일은 공용
  파일(§0.4 인접 규약)이라 이 차선이 고치지 않는다. 조율자에게 다음 두 줄을
  넘긴다(최종 보고 참고):
    ① `from apps.fws.api_n1 import FwsN1API`
    ② `fws_api.register_controllers(FwsOfficeAPI, FwsOffice2API, FwsAdminAPI,
       FwsN1API)` — 기존 등록 뒤에 이어 붙인다(N2·N3·N4 의 빈 컨트롤러 자리와
       같은 관례).
  등록 전까지 이 경로는 실제 서비스에서 열리지 않는다 — 시험은 이 파일의
  임시 URLconf(같은 컨트롤러를 이 파일이 스스로 마운트)로 재는다
  (`backend/tests/test_an_n1_f6_07_webpush.py` 참고 · `django.test.
  override_settings(ROOT_URLCONF=...)`).

이 파일은 **얇다** — 스코프를 만들고 `apps/fws/integration.py` 를 부르고, 그
예외를 HTTP 상태로 옮기는 것뿐이다(`apps/fws/api.py` 머리말과 같은 규율).
★ `from __future__ import annotations` 를 쓰지 않는다(D-378 · `api.py` 머리말과
  같은 까닭).
"""
from django.http import Http404
from ninja import Schema
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from kernels.k2_notify import InvalidNotifyInput, WebPushNotConfigured

from apps.fws import integration


def _scope(request) -> TenantScope:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


class EvacuationWebpushDrillIn(Schema):
    area_name: str
    kind: str = "order"
    #: `{endpoint, keys: {p256dh, auth}}` — `kernels.k2_notify.send_webpush` 가
    #: 받는 것과 같은 모양(`apps/dsm/api_u3.py::PushSubscriptionIn` 과 다른
    #: 스키마인 이유: 이 절은 기기를 저장하지 않고 **그 자리에서 한 통만**
    #: 보낸다 — 시험 경로와 같은 결이다).
    subscription: dict


@api_controller("", tags=["FWS — 차선 N1 반쪽 채우기 (턴 AN · P-392)"])
class FwsN1API:
    # ── FWS-F6-07 대피 웹푸시 훈련 채널 연계 ─────────────────────────────
    @route.post("/liaison/fire-events/{int:event_id}/evacuation-webpush-drill",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건으로 대피 웹푸시 훈련을 보낼 수 없다")
    @idempotent("fws.liaison.evacuation_webpush_drill")
    def liaison_evacuation_webpush_drill(self, request, event_id: int,
                                         payload: EvacuationWebpushDrillIn):
        """`POST .../evacuation-webpush-drill` — 산림청 앱 실제 푸시는 [미확인]이라
        열지 않는다(annex 그대로). 대신 **웹푸시 훈련 채널**(`kernels.k2_notify.
        send_webpush`)로 한 통을 보낸다 — 항상 훈련 표식, 제목은 `[훈련]`로
        시작한다. 문자 초안(`evacuation-cbs-draft`)은 그대로 둔다."""
        try:
            return integration.evacuation_webpush_drill(
                scope=_scope(request), event_id=event_id,
                area_name=payload.area_name, kind=payload.kind,
                subscription=payload.subscription)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))
        except WebPushNotConfigured as exc:
            #: `api_u3.py::push_test_send` 와 같은 규약 — 이름 목록을 문장 안에
            #: `missing_env=` 꼴로 싣는다(값은 없다). `getattr` 로 방어한다 —
            #: `kernels/k2_notify/webpush.py::WebPushNotConfigured.__init__` 의
            #: 이름 오탈자(`_init__`)로 `missing_env` 가 안 채워질 수 있다(그
            #: 파일은 이 차선 소유가 아니라 고치지 않는다 — 조율자에게 보고).
            raise HttpError(
                503, f"{exc} missing_env={','.join(getattr(exc, 'missing_env', []))}")
        except InvalidNotifyInput as exc:
            raise HttpError(400, str(exc))
