"""테넌트 스코프 강제 — **주 통제 지점** (W0-14).

배경 (D-207)
    격리를 ORM 매니저 한 지점에 의존하지 않는다. `CustomManagerGroup` 은 dj-core
    안에 있어 이 저장소가 고칠 수 없고(§0.4), 게다가 `performance_bypass_models`
    로 뚫려 있다. **이 저장소가 통제할 수 있는 지점은 뷰다.**

실측 (2026-08-15)
    이 저장소의 HTTP 표면은 django-ninja-extra 다.
      · `NinjaExtraAPI` 인스턴스      18
      · `@api_controller`             78  (46 파일)
      · `@route.*` 데코레이터        466  (get 204 / post 156 / put 62 / delete 43 / patch 1)
      · 그중 `auth=` 미선언          102
      · `common/tenant_filters` 호출처  **0**   ← 만들어 두고 연결하지 않았다
    DRF ViewSet·APIView 는 **0개**다. 티켓 spec 의 `TenantScopedViewSetMixin`
    (DRF 갈래)은 이 저장소에 적용 대상이 없다 — WP-1 ENTRY §3 참조.

이 모듈이 하는 일 — 세 가지뿐이다
    1. `@tenant_scoped(...)` — 라우트 하나에 group 스코프를 건다.
    2. `PUBLIC_ROUTES` / 미분류(UNREVIEWED) — **두 층으로 나뉜 면제 대장.**
    3. `enumerate_operations()` — 등록된 전 라우트를 런타임에 열거한다.
       `tests/test_route_tenant_scope.py` 의 누락 탐지가 이것을 쓴다.

★ 경고 모드가 기본값이다
    `settings.TENANT_SCOPE_ENFORCE` 가 참이 아니면 **아무것도 차단하지 않는다.**
    차단됐을 요청을 `logger.warning` 으로만 남긴다. 466개 라우트 중 어느 것이
    group 경로를 못 찾는지 아직 아무도 모르기 때문이다. 목록이 0 에 수렴한 뒤
    설정 한 줄로 차단으로 넘어간다 (WP-1 ENTRY §6-2).

    되돌리기: `TENANT_SCOPE_ENFORCE=False`. 코드 되돌림 불필요.
"""
from __future__ import annotations

import functools
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from django.conf import settings

from common.tenant_filters import NoTenantGroupError, get_user_group
from common.tenant_roles import global_admin_reason, is_global_admin

log = logging.getLogger(__name__)

#: 라우트 함수에 붙는 표식. 열거기가 이것으로 스코프 적용 여부를 판정한다.
SCOPE_ATTR = "_gx_tenant_scope"


def enforcing() -> bool:
    """차단 모드인가. 기본값은 **거짓**(경고 모드)."""
    return bool(getattr(settings, "TENANT_SCOPE_ENFORCE", False))


# ─────────────────────────────────────────────────────────────────────────────
# 1. 면제 대장 — **두 층이다**
# ─────────────────────────────────────────────────────────────────────────────
#
# 한 층으로 두면 미분류가 면제로 위장한다. 그러면 테스트는 초록이 되고 노출은
# 그대로 남는다 — 게이트가 있다는 착시가 게이트가 없는 것보다 나쁘다
# (WP-0 EXIT §6-1 `tickets.sha256` 이 같은 실패 모양이었다).
#
#   PUBLIC      인증이 필요 없다고 **판정이 끝난** 것. 사유 필수. 티켓 spec ③ 한정
#               (health / login / 공개 문서).
#   UNREVIEWED  아직 아무도 보지 않은 것. **목록이 아니라 잔여값**이다 —
#               전체에서 스코프 적용분과 PUBLIC 을 뺀 나머지가 자동으로 여기 온다.
#               목표는 0 이고, 테스트가 그 수를 매번 출력한다.

#: 인증 불요로 **판정이 끝난** 라우트. `(HTTP메서드, 경로패턴)` → 사유.
#: 여기에 넣는 것은 "인증 없이 열려 있어야 한다"는 선언이다. 추측으로 넣지 않는다.
PUBLIC_ROUTES: dict[tuple[str, str], str] = {
    # 토큰 발급 자체는 인증 전이어야 성립한다.
    ("POST", "/api/token/pair"): "JWT 발급 — 인증 전 경로",
    ("POST", "/api/token/refresh"): "JWT 갱신 — 인증 전 경로",
    ("POST", "/api/token/verify"): "JWT 검증 — 인증 전 경로",
    # 브라우저가 폼 전송 전에 가져가야 하는 값.
    ("GET", "/api/stream-monitors/auth/csrf-token/"): "CSRF 토큰 — 로그인 폼 선행 요청",
}

#: 테넌트 개념이 성립하지 않는 접두어. 스키마 문서·관리자 화면.
#: **업무 데이터 경로를 여기 추가하지 말 것.** 추가하려면 사유와 함께 위 dict 로 간다.
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/admin/",
    "/api/docs",
)


def is_public(method: str, path: str) -> str | None:
    """PUBLIC 이면 사유를, 아니면 None."""
    reason = PUBLIC_ROUTES.get((method.upper(), path))
    if reason:
        return reason
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return f"공개 접두어 {prefix}"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. 스코프 주입
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ScopeSpec:
    """이 라우트가 어떻게 테넌트에 묶이는가."""

    #: group 을 요구하는가. False 면 "스코프를 검토했고 불필요하다"는 뜻이며
    #: 반드시 `reason` 이 있어야 한다 (검토했다는 것과 안 봤다는 것을 가른다).
    required: bool = True
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.required and not self.reason:
            raise ValueError(
                "required=False 인 스코프는 사유가 필요합니다. "
                "사유 없는 면제는 UNREVIEWED 와 구별되지 않습니다."
            )


def tenant_scoped(
    *, required: bool = True, reason: str = ""
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """라우트 핸들러에 group 스코프를 건다.

    경고 모드(기본)에서는 **차단하지 않고 기록만 한다.** 차단 모드에서는
    group 이 없는 요청을 `NoTenantGroupError` 로 끊는다.

    사용::

        @route.get("", auth=CustomJWTAuth())
        @tenant_scoped()
        def list_items(self, request):
            return filter_by_group_field(Item.objects.all(), request.user)

    ⚠ 이 데코레이터는 **표식과 경고**다. 실제 좁히기는 핸들러 안에서
      `common.tenant_filters` 로 한다. 데코레이터가 queryset 을 대신 좁혀 주는
      것처럼 보이면 안 된다 — 그렇게 믿는 순간 필터 없는 핸들러가 통과한다.
    """
    spec = ScopeSpec(required=required, reason=reason)

    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs)
            if spec.required and request is not None:
                _check(request, func)
            return func(*args, **kwargs)

        setattr(wrapper, SCOPE_ATTR, spec)
        return wrapper

    return decorate


def _find_request(args: tuple, kwargs: dict) -> Any:
    """ninja-extra 핸들러는 `(self, request, ...)` 또는 `(request, ...)` 다."""
    candidate = kwargs.get("request")
    if candidate is not None:
        return candidate
    for value in args[:2]:
        if hasattr(value, "META") and hasattr(value, "path"):
            return value
    return None


def _check(request: Any, func: Callable[..., Any]) -> None:
    user = getattr(request, "user", None)
    if is_global_admin(user):
        # 전역만 경계를 넘는다 (W0-16 정의 · D-247). 레거시 `superuser` 역할로
        # 통과한 건은 회수 진척을 세야 하므로 사유와 함께 남긴다 — 이 줄이
        # `TENANT_TRUST_LEGACY_SUPERUSER` 를 내려도 되는 시점의 근거가 된다.
        if global_admin_reason(user) == "legacy-superuser":
            log.warning(
                "[TENANT_SCOPE][LEGACY_GLOBAL] path=%s user=%s handler=%s",
                getattr(request, "path", "?"),
                getattr(user, "id", None),
                f"{getattr(func, '__module__', '?')}.{getattr(func, '__qualname__', '?')}",
            )
        return
    if get_user_group(user) is not None:
        return

    where = f"{getattr(func, '__module__', '?')}.{getattr(func, '__qualname__', '?')}"
    detail = (
        f"tenant-scope: group 없는 요청 — path={getattr(request, 'path', '?')} "
        f"user={getattr(user, 'id', None)} handler={where}"
    )
    if enforcing():
        raise NoTenantGroupError(detail)
    # 경고 모드 — 차단됐을 것을 남기기만 한다.
    log.warning("[TENANT_SCOPE][WOULD_BLOCK] %s", detail)


# ─────────────────────────────────────────────────────────────────────────────
# 2-B. 커널 계층(L3)의 스코프 — **데코레이터가 아니라 시그니처다** (D-281)
# ─────────────────────────────────────────────────────────────────────────────
#
# 왜 위의 `tenant_scoped` 를 커널에 쓰지 않나
# -------------------------------------------
# `tenant_scoped` 는 `_find_request` 로 `request` 를 찾고, **못 찾으면 그냥 통과시킨다**
# (`wrapper` 의 `request is not None` 조건). HTTP 라우트에는 `request` 가 실제로 있으니
# 유효하지만, **커널 서비스 함수에는 `request` 가 없다.** 붙이면 표식만 남고 아무것도
# 안 막는다 — 데코레이터 466/466 부착을 완결로 착각했던 착시 ①(D-249)의 재현이다.
#
# D-281 이 정한 방식:
#
#     def query_events(*, scope: TenantScope, ...)      # scope 없으면 **호출 자체가 불가**
#
# 데코레이터는 "붙였는가"만 본다. 필수 인자는 **부르는 쪽이 테넌트를 알아야만** 호출된다.
# 표식이 아니라 **구조**다 — 우회할 자리가 없다. 빠뜨리면 `TypeError` 가 즉시 난다.
#
# 사람 없는 호출은 어떻게 하나 — 없애지 않고 **이름을 붙여 센다**
# ---------------------------------------------------------------
# 검출 파이프라인(gRPC 콜백)에는 요청자가 없다. 그렇다고 스코프 인자를 빼면
# "테넌트를 생각하지 않은 호출"과 구별이 사라진다. 그래서 `TenantScope.system(reason=...)`
# 을 두고 **사유를 필수**로 받는다. 이것은 면제가 아니라 **등재**다:
#   · 사유 없는 시스템 스코프는 만들 수 없다 (`__post_init__` 이 던진다).
#   · 시스템 스코프로는 **읽지 못한다** (`require_actor()`). 읽기가 전역이 되는 길을 막는다.
#   · `grep "TenantScope.system"` 한 줄로 전수가 세어진다 — 수가 아니라 **이름으로**
#     잠그는 D-285 (2) 와 같은 계열이다.


class SystemScopeCannotRead(Exception):
    """시스템 스코프로 테넌트 데이터를 읽으려 했다 (D-281).

    쓰기 파이프라인에 요청자가 없다는 것은 **읽어도 된다는 뜻이 아니다.**
    이 예외가 나오면 부르는 쪽이 요청자를 갖고 있는지 다시 볼 것 —
    "일단 system 으로 읽자"가 한 번 통과하면 그 경로는 영구히 전역 읽기가 된다.
    """


@dataclass(frozen=True)
class TenantScope:
    """커널 호출 하나가 **누구로서** 일어나는가 (D-281).

    두 가지 뿐이다. 세 번째를 만들지 말 것 — 늘어나는 순간 이 타입이 답하는 질문이 흐려진다.

        TenantScope.of(request.user)         # 사람이 부른다 (HTTP 라우트 → 커널)
        TenantScope.system(reason="…")       # 사람이 없다 (파이프라인). **사유 필수**

    ⚠ 이 객체는 **권한을 주지 않는다.** 좁히기는 여전히 `common.tenant_filters` 의
      문지기가 한다 (시그니처가 1차, 문지기가 2차 — D-281). 여기서 하는 일은
      "부르는 쪽이 테넌트를 명시하게 강제하는 것" 하나다.
    """

    #: 요청자. 시스템 스코프면 `None`.
    actor: Any = None
    #: 사람이 없는 호출의 사유. 시스템 스코프에서만 채워진다.
    system_reason: str = ""

    def __post_init__(self) -> None:
        if self.actor is None and not self.system_reason:
            raise ValueError(
                "TenantScope 는 요청자(actor) 또는 시스템 사유(system_reason) 중 하나가 "
                "반드시 있어야 합니다. 둘 다 비면 '테넌트를 생각하지 않은 호출'과 "
                "구별되지 않습니다 (D-281). "
                "TenantScope.of(user) 또는 TenantScope.system(reason='…') 를 쓰십시오."
            )
        if self.actor is not None and self.system_reason:
            raise ValueError(
                "요청자와 시스템 사유를 함께 둘 수 없습니다 — 그 호출은 사람의 것입니까, "
                "파이프라인의 것입니까. 하나로 답하십시오 (D-281)."
            )

    # ── 만드는 법 두 가지 ────────────────────────────────────────────────
    @classmethod
    def of(cls, actor: Any) -> "TenantScope":
        """사람이 부르는 호출. `actor` 가 없으면 만들지 않는다."""
        if actor is None:
            raise ValueError(
                "TenantScope.of(None) — 요청자가 없습니다. 인증이 필요한 경로라면 "
                "여기까지 오기 전에 401 로 끊어야 하고, 파이프라인이라면 "
                "TenantScope.system(reason='…') 를 쓰십시오 (D-281)."
            )
        return cls(actor=actor)

    @classmethod
    def system(cls, *, reason: str) -> "TenantScope":
        """사람이 없는 호출. **사유가 필수다** — 등재이지 면제가 아니다.

        여기 적는 사유는 다음 사람이 "이 호출에 왜 요청자가 없나"를 코드에서 바로
        읽을 수 있어야 한다. `reason="pipeline"` 같은 건 사유가 아니다.
        """
        if not (reason or "").strip():
            raise ValueError(
                "TenantScope.system(reason=...) 에 사유가 없습니다. "
                "사유 없는 시스템 스코프는 면제와 구별되지 않습니다 (D-281 · D-261 c)."
            )
        return cls(actor=None, system_reason=reason.strip())

    # ── 묻는 법 ──────────────────────────────────────────────────────────
    @property
    def is_system(self) -> bool:
        return self.actor is None

    def require_actor(self) -> Any:
        """읽기 경로의 문턱. 시스템 스코프면 **던진다.**

        쓰기 파이프라인에 요청자가 없다는 사실이 읽기까지 열어 주지 않게 한다.
        시스템 스코프로 `query_events` 가 돌면 그것은 곧 **전역 조회**이고,
        전역 조회는 격리가 아니라 격리의 부재다.
        """
        if self.actor is None:
            raise SystemScopeCannotRead(
                f"시스템 스코프(사유={self.system_reason!r})로 테넌트 데이터를 읽을 수 "
                f"없습니다. 읽기에는 요청자가 필요합니다 — TenantScope.of(user) (D-281)."
            )
        return self.actor


# ─────────────────────────────────────────────────────────────────────────────
# 3. 라우트 열거 — 누락 탐지 테스트의 입력
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RouteInfo:
    method: str
    path: str
    handler: str
    module: str
    has_auth: bool
    scope: ScopeSpec | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    #: `@path_permission(..., path_override=…)` 이 핸들러에 남긴 권한 경로.
    #: 격리 시험 픽스처가 "이 라우트에 닿으려면 어떤 권한이 필요한가"를 여기서 읽는다.
    path_override: Any = None

    @property
    def state(self) -> str:
        """`scoped` / `public` / `unreviewed` 셋 중 하나."""
        if self.scope is not None:
            return "scoped"
        if is_public(self.method, self.path):
            return "public"
        return "unreviewed"


def _iter_ninja_apis() -> Iterable[tuple[str, Any]]:
    """등록된 `NinjaAPI`/`NinjaExtraAPI` 인스턴스를 `(마운트경로, api)` 로 낸다.

    `config/urls.py` 는 `include("<app>.urls")` 23개뿐이고 라우트가 없다.
    실제 오퍼레이션은 각 앱 모듈의 API 인스턴스 안에 있으므로, URL 리졸버를
    타고 내려가 **모듈 수준의 API 객체**를 찾는다.
    """
    try:
        from django.urls import get_resolver
        from django.urls.resolvers import URLResolver
        from ninja import NinjaAPI
    except Exception as exc:  # pragma: no cover - import 환경 문제
        log.warning("tenant_scope: 라우트 열거 불가 — %s", exc)
        return

    seen: set[int] = set()

    def walk(patterns: Iterable[Any], prefix: str) -> Iterable[tuple[str, Any]]:
        for entry in patterns:
            if not isinstance(entry, URLResolver):
                continue
            here = prefix + str(getattr(entry.pattern, "_route", "") or "")
            module = getattr(entry, "urlconf_module", None)
            # include("app.urls") → 모듈. 그 모듈 안의 API 인스턴스를 줍는다.
            for value in _module_values(module):
                if isinstance(value, NinjaAPI) and id(value) not in seen:
                    seen.add(id(value))
                    yield here, value
            try:
                yield from walk(entry.url_patterns, here)
            except Exception:  # pragma: no cover - 잘못된 include 방어
                continue

    yield from walk(get_resolver().url_patterns, "/")


def _module_values(module: Any) -> Iterable[Any]:
    if module is None:
        return ()
    if isinstance(module, (list, tuple)):
        return ()
    return list(vars(module).values()) if hasattr(module, "__dict__") else ()


def enumerate_operations() -> list[RouteInfo]:
    """등록된 전 라우트를 연다. **정적 grep 이 아니라 런타임 레지스트리를 읽는다.**

    grep 은 주석·문자열도 세고 동적 등록을 놓친다. 이 함수가 세는 수가 정본이다.
    """
    routes: list[RouteInfo] = []
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    view = getattr(op, "view_func", None)
                    full = _join(mount, prefix, op_path)
                    for method in getattr(op, "methods", []) or []:
                        routes.append(
                            RouteInfo(
                                method=str(method).upper(),
                                path=full,
                                handler=getattr(view, "__qualname__", "?"),
                                module=getattr(view, "__module__", "?"),
                                has_auth=bool(getattr(op, "auth_callbacks", None)),
                                scope=getattr(view, SCOPE_ATTR, None),
                                tags=tuple(getattr(op, "tags", ()) or ()),
                                path_override=getattr(view, "_path_override", None),
                            )
                        )
    routes.sort(key=lambda r: (r.path, r.method))
    return routes


def _join(*parts: str) -> str:
    out = "/" + "/".join(p.strip("/") for p in parts if p and p.strip("/"))
    return out or "/"


def summarize(routes: list[RouteInfo] | None = None) -> dict[str, Any]:
    """현황 요약. 테스트와 `evidence/W0-14/coverage.md` 가 같은 값을 쓴다."""
    routes = enumerate_operations() if routes is None else routes
    buckets: dict[str, list[RouteInfo]] = {"scoped": [], "public": [], "unreviewed": []}
    for r in routes:
        buckets[r.state].append(r)
    total = len(routes)
    return {
        "total": total,
        "scoped": len(buckets["scoped"]),
        "public": len(buckets["public"]),
        "unreviewed": len(buckets["unreviewed"]),
        "no_auth": sum(1 for r in routes if not r.has_auth),
        "coverage_pct": round(100.0 * len(buckets["scoped"]) / total, 1) if total else 0.0,
        "enforcing": enforcing(),
        "buckets": buckets,
    }
