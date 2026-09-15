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

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from apps.dsm import field


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
