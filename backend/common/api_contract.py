# -*- coding: utf-8 -*-
"""응답 후처리 계층 — 권한거부를 실제 HTTP 상태로 승격한다 (W0-18 · D-248).

왜 필요한가
    `core/role/permission.py` 의 `@path_permission` 은 권한거부를 **평범한 dict**
    `{"success": False, "message": …, "status_code": 403}` 으로 돌려준다.
    그 파일은 §0.4 금지구역이라 고칠 수 없다(D-207 · D-248). 그래서 저장소 쪽
    **응답 후처리**로 실제 상태를 되찾는다.

거부 dict 가 밖으로 나가는 길은 **셋**이고 셋 다 모양이 다르다
(실측: `docs/agent/evidence/W0-18/backward_compat_impact.md` §1)

    A  `response=` 선언이 없는 라우트  281건 → **289건** (P-W0-18-1 로 C 8건이 넘어왔다)
       → 200 + 거부 본문 그대로.  __call__ 응답단계에서 상태만 승격한다.

    B  `response=List[…]` 라우트        7건
       → pydantic 이 dict 를 거절 → 예외 → `ninja/errors.py:_default_exception` 이
         `if not settings.DEBUG: raise exc` 로 Django 에 도로 넘긴다
         → **`process_exception` 이 호출된다.** 그 예외의 `input` 에 거부 dict 가
         그대로 들어 있어서 복원할 수 있다. delivery 5건이 §0.4 안이라 이 길이 유일하다.

    C  `response=<단일 스키마>` 라우트   8건 → **0건** (2026-08-25 · P-W0-18-1 A 안)
       → 거부 dict 가 그 스키마로 검증되면서 **빈 객체 `{}` 로 소멸했다.**
         응답이 만들어지기 전에 정보가 사라지므로 **이 계층에서는 복원할 수 없다.**
         그래서 계층이 아니라 **선언 쪽**을 고쳤다 — 8건 전부 §0.4 밖
         (report_template 4 · checklist_setting 4)이라 `response=` 를 뗄 수 있었고,
         떼고 나니 A 부류가 되어 이 미들웨어의 사정권에 들어왔다.
         이 부류가 다시 0 보다 커지면 `tests/test_api_contract.py` 가 잡는다.

되돌리기 (D-212)
    `settings.API_CONTRACT_PROMOTE_ERROR_STATUS` **기본 False**.
    False 이면 이 미들웨어는 경로에 있어도 **아무것도 바꾸지 않는다.**
    되돌림은 설정 한 줄이고 배포 재빌드가 필요 없다.

승격하지 않는 것 — 판정을 좁게 잡는다
    `success is False` **이고** `status_code` 가 400~599 **정수**일 때만 승격한다.
    저장소가 본문에 `status_code` 를 넣는 곳 23군데를 전수 확인했고, 그중
    이 조합에 걸리는 것은 없다(배송 진행단계 0~5 · 도메인 상태문자열 · 200).
    넓히면 배송·주문 경로까지 흔들린다. R1 동안은 좁게 둔다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

FLAG = "API_CONTRACT_PROMOTE_ERROR_STATUS"

#: 승격 대상으로 인정하는 상태 범위
_MIN_STATUS = 400
_MAX_STATUS = 599


#: 전역 플래그가 꺼져 있어도 **여기 경로는 승격한다** (D-349 ③).
#: 계약 상대가 읽는 면(F-05)은 래칫에 두지 않는다 — 거기서 200 봉투에 담긴 실패는
#: 에스비 App 이 성공으로 읽고, 그것은 계약 사고다.
SCOPE = "API_CONTRACT_PROMOTE_PATHS"


def promotion_enabled() -> bool:
    """플래그 한 곳. 시험도 운영도 이 함수만 본다 (D-212)."""
    return bool(getattr(settings, FLAG, False))


def promotion_scope() -> tuple[str, ...]:
    """전역 플래그와 **무관하게** 승격하는 경로 앞머리들."""
    return tuple(getattr(settings, SCOPE, ()) or ())


def promotion_enabled_for(path: str) -> bool:
    """이 경로에서 승격하는가.

    ★ 두 갈래를 **하나의 함수로** 답한다. 두 곳에서 물으면 언젠가 갈리고,
      갈리면 어느 쪽이 진짜 규칙인지 아무도 모른다(D-337 계열).
    """
    if promotion_enabled():
        return True
    return any(path.startswith(prefix) for prefix in promotion_scope())


def denial_status(payload: Any) -> int | None:
    """이 본문이 `@path_permission` 의 거부인가. 맞으면 승격할 상태, 아니면 None.

    `success is False` 를 쓴다 (`not payload.get("success")` 가 아니다) —
    키가 없거나 빈 문자열인 경우까지 거부로 읽으면 판정이 넓어진다.
    """
    if not isinstance(payload, dict):
        return None
    if payload.get("success") is not False:
        return None
    code = payload.get("status_code")
    # bool 은 int 의 서브클래스다. True 가 1 로 통과하는 것을 막는다.
    if isinstance(code, bool) or not isinstance(code, int):
        return None
    if not (_MIN_STATUS <= code <= _MAX_STATUS):
        return None
    return code


def _json_body(response: HttpResponse) -> Any | None:
    """응답 본문을 JSON 으로 읽는다. 읽을 수 없으면 None.

    스트리밍·파일 응답은 `.content` 를 만지면 안 된다(소비된다).
    Content-Encoding 이 붙었으면 이미 압축된 뒤라 파싱할 수 없다 — 그래서
    이 미들웨어는 `GZipMiddleware` 보다 **안쪽**에 둔다(§ 배치 주석 참조).
    """
    if getattr(response, "streaming", False):
        return None
    if response.has_header("Content-Encoding"):
        return None
    ctype = response.headers.get("Content-Type", "")
    if "json" not in ctype.lower():
        return None
    try:
        return json.loads(response.content.decode(response.charset or "utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _denial_from_exception(exception: BaseException) -> dict | None:
    """pydantic 이 거부 dict 를 거절해 터진 예외에서 원래 dict 를 되찾는다 (B 부류).

    pydantic v2 의 `ValidationError.errors()` 는 각 오류에 `input` 을 담는다.
    응답 검증에서 터진 것이면 그 `input` 이 핸들러가 돌려준 값 그 자체다.
    타입으로 좁히지 않고 **모양으로** 판정한다 — pydantic 을 직접 import 하면
    버전 교체 때 조용히 무력화된다.
    """
    errors = getattr(exception, "errors", None)
    if not callable(errors):
        return None
    try:
        items = errors()
    except Exception:  # pragma: no cover - 예외 안에서 또 터지면 원본을 살린다
        return None
    if not isinstance(items, (list, tuple)):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        payload = item.get("input")
        if denial_status(payload) is not None:
            return payload
    return None


#: 거부 dict 가 밖으로 나가는 세 가지 길. 시험과 증거가 같은 이름을 쓴다.
KIND_PROMOTABLE = "A_no_schema"      # 200 + 거부본문 → 미들웨어가 승격
KIND_RAISES = "B_list_schema"        # pydantic 거절 → 예외 → process_exception 이 복원
KIND_SWALLOWED = "C_single_schema"   # {} 로 소멸 → 이 계층에서 복원 불가


def classify_permission_routes() -> dict[str, list[str]]:
    """`@path_permission` 이 붙은 라우트를 거부 응답의 모양으로 분류한다.

    **정적 grep 이 아니라 런타임 레지스트리를 읽는다** — `common.tenant_scope` 와 같은
    이유다(주석·문자열을 세지 않고 동적 등록을 놓치지 않는다).
    `evidence/W0-18/backward_compat_impact.md` §1-1 의 수와 이 함수의 수는 같아야 한다.
    """
    from common.tenant_scope import _iter_ninja_apis, _join

    out: dict[str, list[str]] = {
        KIND_PROMOTABLE: [],
        KIND_RAISES: [],
        KIND_SWALLOWED: [],
    }
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    view = getattr(op, "view_func", None)
                    if not getattr(view, "_path_override", None):
                        continue
                    label = "{} {}".format(
                        ",".join(str(m).upper() for m in (getattr(op, "methods", []) or [])),
                        _join(mount, prefix, op_path),
                    )
                    out[_route_kind(op)].append(label)
    for bucket in out.values():
        bucket.sort()
    return out


def _route_kind(op) -> str:
    """ninja Operation 하나의 응답 스키마 성격."""
    models = getattr(op, "response_models", None) or {}
    model = models.get(200) or (next(iter(models.values())) if models else None)
    if model is None:
        return KIND_PROMOTABLE
    field = getattr(model, "model_fields", {}).get("response")
    if field is None:
        return KIND_PROMOTABLE
    annotation = str(getattr(field, "annotation", ""))
    if annotation.startswith("typing.List") or annotation.startswith("list["):
        return KIND_RAISES
    return KIND_SWALLOWED


class ApiContractStatusMiddleware:
    """200-body-4xx 를 실제 HTTP 4xx 로 승격한다.

    ★ 배치 — `UniversalCacheMiddleware` **바로 위**. 두 조건을 동시에 만족해야 한다.

      ① **캐시보다 바깥**.  `UniversalCacheMiddleware` 는 캐시 적중 시 저장해 둔
         본문으로 `JsonResponse(...)` 를 새로 만든다 — 즉 **상태코드를 버리고 늘 200**
         으로 돌려준다(`universal_optimization.py:872`). 이 미들웨어를 캐시 안쪽에 두면
         적중한 요청에서는 아예 호출되지 않아 **승격이 통째로 사라진다.**
         바깥에 두면 캐시가 만든 200 도 다시 승격된다.
      ② **GZipMiddleware 보다 안쪽**.  압축된 본문은 JSON 으로 읽을 수 없다.

    Django 의 응답단계는 MIDDLEWARE 목록을 거꾸로 돈다 — 목록에서 아래에 있을수록
    응답을 먼저 본다. 두 조건은 "GZip 아래, UniversalCache 위"로 만난다.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not promotion_enabled_for(request.path):
            return response
        # 승격은 200 에서만 한다. 이미 4xx 로 나가는 응답은 건드릴 이유가 없다.
        if response.status_code != 200:
            return response
        code = denial_status(_json_body(response))
        if code is None:
            return response
        logger.info(
            "[API_CONTRACT] 승격 %s %s: 200 -> %s",
            request.method,
            request.path,
            code,
        )
        # 본문·헤더는 그대로 두고 상태줄만 고친다. 다시 렌더하지 않는다 —
        # 기존 클라이언트가 읽던 `success`/`message` 가 사라지면 안 된다.
        response.status_code = code
        return response

    def process_exception(self, request, exception):
        """B 부류 — 응답 스키마 검증에서 터진 거부를 4xx 로 되살린다.

        되살리지 못하면 None 을 돌려 **원래 예외를 그대로 흐르게 둔다.**
        진짜 직렬화 결함을 이 미들웨어가 삼키면 안 된다.
        """
        if not promotion_enabled_for(request.path):
            return None
        payload = _denial_from_exception(exception)
        if payload is None:
            return None
        code = denial_status(payload)
        logger.info(
            "[API_CONTRACT] 승격(예외) %s %s: 500 -> %s",
            request.method,
            request.path,
            code,
        )
        return JsonResponse(payload, status=code)
