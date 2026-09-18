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
from ninja import Schema
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import TenantScope, tenant_scoped

#: 재시작 「요청」의 응답 문장. **한 곳에만 적는다** — 화면·시험·명세가 같은 글자를 읽는다.
#: 이 문장이 거짓이 되는 날(문이 실제로 서버를 내리는 날)은 시험이 먼저 빨개진다.
RESTART_ACK = ("요청이 기록됐습니다 — 실행은 점검 창에서 합니다. "
               "이 단추는 서버를 내리지 않습니다.")


class StorageOut(Schema):
    """U5 #15 저장 용량의 **응답 모양** — OpenAPI `components.schemas` 의 첫 줄.

    ★ 왜 하나라도 필요한가 (U6 #14 계열 · 턴 U): 이 저장소의 dsm 라우트는 인자를
      원시 타입으로 받고 응답을 `dict` 로 내므로 OpenAPI 문서에 **모양이 하나도
      없었다**. 모양이 없으면 외부 App 은 「200 이 온다」밖에 못 읽고, 그 상태의
      명세는 명세가 아니다. 이 한 장이 그 0 을 깬다.
    ★ `null` 이 값이다 — 상한 미선언은 `capacity_gb: null` 이고 `0` 이 아니다(D-301).
    """

    declared: bool
    capacity_gb: float | None = None
    used_gb: float | None = None
    used_pct: float | None = None
    verdict: str
    reason: str = ""
    used_note: str = ""
    env_name: str = ""


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


# ═══════════════════════════════════════════════════════════════════════════
# `GET /api/dsm/health` 의 검사 셋 — db · cache · queue (턴 T · 차선 U56)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 값은 **상태 이름**뿐이다. 예외의 문장·호스트명·포트·버전은 응답에 싣지 않는다 —
#   이 문은 자격증명 없이 열려 있고, 열린 문으로 나가는 글자는 전부 정찰 자료다.
# ★ 검사는 `HEALTH_CHECKS` 딕셔너리에 이름 → 호출로 둔다. 시험이 하나를 죽는 것으로
#   바꿔 503 을 잰다(monkeypatch) — 운영에서 바꾸는 자리가 아니다.
SCHEMA_VERSION = "1.1"


def _check_db() -> None:
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()


def _check_cache() -> None:
    from django.core.cache import cache

    key = "gx:health:ping"
    cache.set(key, "1", timeout=5)
    # 값이 안 돌아와도 죽은 것은 아니다(dummy 캐시) — 예외만 죽음으로 본다.
    cache.get(key)


def _check_queue() -> None:
    """발송 대기열의 중개자(Celery broker)에 닿는가. 설정이 없으면 「없음」이지 죽음이 아니다."""
    from django.conf import settings as dj_settings

    url = getattr(dj_settings, "CELERY_BROKER_URL", "") or ""
    if not url or getattr(dj_settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return
    try:
        from kombu import Connection
    except ImportError:  # pragma: no cover - kombu 없는 환경은 검사 자체가 없다
        return
    with Connection(url, connect_timeout=2) as conn:
        conn.ensure_connection(max_retries=1, interval_start=0, interval_step=0)


HEALTH_CHECKS = {"db": _check_db, "cache": _check_cache, "queue": _check_queue}


def run_health_checks() -> dict:
    """`{"status": "ok"|"fail", "schema": "1.1", "checks": {이름: "ok"|"fail"}, "failed": [...]}`."""
    checks: dict[str, str] = {}
    failed: list[str] = []
    for name, fn in HEALTH_CHECKS.items():
        try:
            fn()
            checks[name] = "ok"
        except Exception:  # noqa: BLE001 — 사유는 로그로만, 응답엔 이름만
            import logging
            logging.getLogger(__name__).warning("[HEALTH] 검사 실패: %s", name, exc_info=True)
            checks[name] = "fail"
            failed.append(name)
    return {"status": "ok" if not failed else "fail", "schema": SCHEMA_VERSION,
            "checks": checks, "failed": failed}


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
                                   payload_format: str = "json", filters: str = ""):
        """P-145 — **서명키를 우리가 만들어** 구독에 물린다. 값은 응답에 **한 번만**.

        ★ [턴 T · WS-17] `filters` 는 JSON 문자열 `{"type":[..],"severity":[..],"camera":[..]}` —
          질의 인자로 받는다(이 저장소의 dsm 라우트 관용 · `dsmPostQuery`). 모양이 틀리면 400.

        ★ 기존 `POST /webhook-subscriptions`(`api.py`)를 대신하지 않는다 — 그 문은
          "이름을 이미 아는 상대"(운영자가 미리 값을 나눈 자리)를 위해 그대로 남는다.
          이 문은 **이름조차 몰라도** 되는 새 경로다(라우트 삼킴 없음 — 경로가
          `/settings/` 로 다르다).
        ★ 값은 여기서만 나온다. 그 뒤 `GET /webhook-subscriptions` 목록에는
          `signing_key_ref`(이름)만 있고 값은 없다(`api.py::_subscription_payload`).
        """
        from apps.dsm.exceptions import PermissionDeniedForSetting
        from apps.dsm.webhook_key_service import InvalidWebhookFilters
        from apps.dsm.webhook_key_service import issue_webhook_subscription as _issue
        from common.tenant_scope import SystemScopeCannotRead
        from common.webhook_outbox import WebhookSubscriptionError

        types = tuple(t.strip() for t in (event_types or "").split(",") if t.strip())
        try:
            result = _issue(
                scope=_scope(request), endpoint_url=endpoint_url,
                event_types=types, min_severity=min_severity,
                payload_format=payload_format, filters=filters or None)
        except InvalidWebhookFilters as exc:
            raise HttpError(400, str(exc))
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, exc.reason)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except WebhookSubscriptionError as exc:
            raise HttpError(422, str(exc))
        return result

    # ── WS-17 「webhook filters」 — 사건 종류 · 심각도 · 카메라 (턴 T · 차선 U56) ──
    #
    # ⚠ 같은 함정 — 세 조각(`/settings/webhook-subscriptions/{id}/filters`)이라
    #   `/settings/{domain}`(한 조각)에 안 삼켜진다. GET·POST 를 **같은 경로 문자열**에
    #   붙여 한 PathView 에 세운다(D-410 · `api.py` 의 thresholds 와 같은 모양).
    # ★ 목록 문(`GET /webhook-subscriptions` · `api.py` U3 소유)의 응답에는 filters 칸이
    #   없다 — 그래서 읽기 문을 여기 따로 둔다. 왕복(저장 → 재조회)은 이 두 문으로 잰다.
    # ★ 발송기가 이 칸을 읽는 한 줄(`webhook_outbox._passes_filter`)은 이 차선 소유
    #   밖이다 — 등록 요청(보고 ③). 그 줄이 서기 전까지 filters 는 「저장되지만 거르지
    #   않는다」이고, 화면이 그 사실을 말로 적는다(`Integrations.tsx`).
    @route.get("/settings/webhook-subscriptions/{int:subscription_id}/filters",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="WS-17 구독 필터 조회 — 남의 구독은 404(존재도 새지 않는다)")
    def webhook_subscription_filters_get(self, request, subscription_id: int):
        """구독 한 줄의 filters. 빈 객체는 「거르지 않는다」다."""
        from django.http import Http404

        from apps.dsm.webhook_key_service import get_subscription_filters
        from common.tenant_scope import SystemScopeCannotRead

        try:
            return get_subscription_filters(
                scope=_scope(request), subscription_id=subscription_id)
        except Http404:
            raise HttpError(404, "그런 구독이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.post("/settings/webhook-subscriptions/{int:subscription_id}/filters",
                auth=JwtOrInboundKey())
    @tenant_scoped(reason="WS-17 구독 필터 저장 — 남의 구독의 수신 범위를 바꿀 수 없다 "
                          "(쓰기 IDOR). 문지기는 guard_setting(F-12 와 같은 무게)")
    def webhook_subscription_filters_set(self, request, subscription_id: int,
                                         filters: str = "{}"):
        """filters 를 저장한다. `filters` 는 JSON 문자열(질의 인자) — 틀리면 400.

        ★ 400 은 「요청이 틀렸다」(모르는 키 · JSON 아님) · 403 은 관리자가 아니다 ·
          404 는 남의 구독(존재도 새지 않는다).
        """
        from django.http import Http404

        from apps.dsm.exceptions import PermissionDeniedForSetting
        from apps.dsm.webhook_key_service import (InvalidWebhookFilters,
                                                  set_subscription_filters)
        from common.tenant_scope import SystemScopeCannotRead

        try:
            return set_subscription_filters(
                scope=_scope(request), subscription_id=subscription_id,
                filters=filters)
        except InvalidWebhookFilters as exc:
            raise HttpError(400, str(exc))
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, exc.reason)
        except Http404:
            raise HttpError(404, "그런 구독이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── `GET /api/dsm/health` — 인증 없이 · 상태 이름만 (턴 T · 차선 U56) ──
    #
    # ★ **자격증명이 없어도 200** 이다 — 로드밸런서·감시기가 부른다. 그래서 나가는 것은
    #   상태 **이름**뿐이다(`ok`/`fail`) · 비밀·호스트명·버전 문자열·오류 본문이 없다.
    #   본문에 자료가 없으므로 익명 401 게이트(P-133 · `probe_read_surface.PUBLIC_READ_BY_DESIGN`)
    #   에는 **이름으로 올린다**(등록 요청 · 그 파일은 이 차선 소유가 아니다).
    # ★ `auth=None` 이 명시다 — 컨트롤러 기본이 없어도 「안 적었다」와 「공개다」는 다르다.
    # ★ 검사 하나라도 죽으면 **503** 과 그 검사의 이름 — 200 으로 삼키면 감시기가 못 본다.
    # ⚠ 한 조각(`/health`)인데도 안전한 이유는 `/me` 와 같다 — `api.py` 의 변수 조각은
    #   `/settings/{domain}` 하나뿐이다.
    @route.get("/health", auth=None)
    @tenant_scoped(required=False,
                   reason="생존 확인 — 테넌트 자료가 아니다. 나가는 것은 검사 이름과 "
                          "상태 이름뿐(비밀·호스트명 없음)")
    def health(self, request):
        from django.http import JsonResponse

        body = run_health_checks()
        status = 200 if body["status"] == "ok" else 503
        resp = JsonResponse(body, status=status)
        resp["Cache-Control"] = "no-store"
        return resp

    # ═══════════════════════════════════════════════════════════════════════
    # S-16 「알림 받는 사람·채널」 — UX-43 · WS-14 (턴 S · 차선 U56)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # ⚠ **경로가 세 조각인 이유** — 위 people 과 **같은 함정**이다 [실측 · 턴 R·S].
    #   `/settings/notify-rules`(두 조각)는 `api.py` 의 `GET /settings/{domain}` 에
    #   `domain="notify-rules"` 로 **삼켜진다.** 삼켜지면 GET 은 501(「설정 영역이
    #   아니다」)을 내고 POST 는 405 다 — **있는데 없는 것처럼 보이는** 가장 나쁜 모양
    #   (D-410). 그래서 `/settings/notify-rules/{list,save,test}` 세 조각으로 연다.
    #   ⚠ 404 를 만나면 PROPFIND 로 한 번 더 두드려라 — 라우트가 있으면 405, 없으면 404 다.
    #
    # ★ 문지기는 `guard_setting` 하나다 (F-12 의 유일한 판정식 · D-212). 여기서 새
    #   판정을 짓지 않는다 — 알림 규칙은 「누가 재난을 아는가」를 정하는 설정이고,
    #   임계값·구역과 **같은 무게**로 지킨다.
    @route.get("/settings/notify-rules/list", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-43 알림 규칙 조회 — 남의 테넌트가 누구에게 재난을 "
                          "알리는지는 남의 정보다")
    def notify_rules_list(self, request):
        """S-16 화면이 읽는 한 묶음 — 등급별 도달 · 규칙 · 채널 · **심각이 막혔는가**.

        ★ `critical_blocked` 를 **같은 응답에** 실어 준다. 화면이 한 번 더 물어야 하면
          그 사이에 「규칙은 있는데 아무에게도 안 간다」가 안 보이고, 그것이 이 화면이
          막으려는 상태 그 자체다.
        """
        from apps.dsm.services import guard_setting
        from kernels.k2_notify import notify_rule_overview

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="read:notify-rules", api_method="GET")
        if not access.allowed:
            raise HttpError(403, access.reason)
        return notify_rule_overview(scope=scope)

    @route.post("/settings/notify-rules/save", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-43 알림 규칙 저장 — 남의 테넌트 규칙을 바꾸면 그쪽 "
                          "당직자가 재난을 못 듣는다 (쓰기 IDOR)")
    def notify_rules_save(self, request, severity: str, role_code: str,
                          channels: str, zone: str = "", is_active: bool = True,
                          rule_id: int = 0):
        """규칙 하나를 저장한다. **심각을 0명으로 만드는 저장은 409 다.**

        ★ 409 이지 400 이 아니다 — 요청이 틀린 게 아니라(400) **지금 상태에서 할 수
          없는 일**이다. `notify` 라우트가 `NoRecipients` 를 409 로 내는 것과 같은 자리·
          같은 뜻이다(알림 체계가 꺼지는 것을 200 으로 삼키지 않는다).
        ★ `channels` 는 쉼표로 구분한 문자열이다 — `event_types`·`role_ids` 와 같은 관용.
        ★ `rule_id=0` 이 「새로 만든다」다. ninja 질의 인자에 `None` 기본값을 두면
          「안 줬다」와 「0 을 줬다」가 같은 모양이 되므로 0 을 없음으로 읽는다.
        """
        from apps.dsm.services import guard_setting
        from kernels.k2_notify import (CriticalWithoutRecipients,
                                       InvalidNotifyInput,
                                       NotifyPermissionDenied, save_rule)

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="write:notify-rules:%s:%s" % (severity, role_code),
            api_method="POST")
        if not access.allowed:
            raise HttpError(403, access.reason)

        names = [c.strip() for c in (channels or "").split(",") if c.strip()]
        try:
            view = save_rule(
                scope=scope, severity=severity, role_code=role_code,
                channels=names, zone=(zone or "").strip() or None,
                is_active=is_active, rule_id=rule_id or None)
        except CriticalWithoutRecipients as exc:
            raise HttpError(409, str(exc))
        except NotifyPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except InvalidNotifyInput as exc:
            raise HttpError(400, str(exc))
        return {"rule_id": view.rule_id, "severity": view.severity,
                "role_code": view.role_code, "zone": view.zone,
                "channels": list(view.channels), "is_active": view.is_active,
                "audit_id": access.audit_id}

    @route.post("/settings/notify-rules/test", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-43 시험 발송 — 남의 테넌트 수신자에게 발송을 일으킬 "
                          "수 없다 (쓰기 IDOR)")
    def notify_rules_test(self, request, severity: str = "critical"):
        """시험 발송 — **훈련 채널로만 나간다.**

        ★ 채널을 인자로 받지 않는다. 고를 수 있으면 언젠가 실채널이 선택되고, 그날
          「시험」이라 부르며 당직자 휴대전화가 울린다 — 나간 메일은 취소되지 않는다.
        ★ 응답의 `reaches_people` 은 **언제나 거짓**이다. 화면이 「보냈습니다」만 그리면
          사람은 자기 수신함을 확인하러 간다.
        """
        from apps.dsm.services import guard_setting
        from kernels.k2_notify import (CriticalWithoutRecipients,
                                       InvalidNotifyInput, send_test_notification)

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="write:notify-rules:test:%s" % severity,
            api_method="POST")
        if not access.allowed:
            raise HttpError(403, access.reason)
        try:
            result = send_test_notification(scope=scope, severity=severity)
        except CriticalWithoutRecipients as exc:
            raise HttpError(409, str(exc))
        except InvalidNotifyInput as exc:
            raise HttpError(400, str(exc))
        return {**result, "audit_id": access.audit_id}

    # ═══════════════════════════════════════════════════════════════════════
    # S-15 「내 정보」 — UX-42-me (턴 S · 차선 U56)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # ★ **`guard_setting` 이 없다.** 이 문은 설정이 아니라 **자기 자신**이다 — 로그인한
    #   사람은 누구나 자기 정보를 본다. 관리자만 지나게 하면 관제요원이 「내가 무슨
    #   알림을 받는가」를 영영 못 본다(온보딩 U1 #7 「내 정보 확인」이 그 자리다).
    # ★ 남의 것을 가리킬 인자가 **없다.** 소속·계정은 `scope` 가 정하고, 커널의
    #   `my_notify_reach` 는 `scope.require_actor()` 로만 사람을 고른다(D-281 시그니처가 1차).
    # ⚠ 경로가 한 조각(`/me`)인데도 안전한 이유: `api.py` 의 와일드카드는
    #   `/settings/{domain}` **하나뿐**이고 그것은 `settings/` 로 시작하는 것만 삼킨다
    #   [실측 — `@route.*("/{` 전수 0건]. `/me` 를 가릴 변수 조각이 없다.
    @route.get("/me", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-42-me 내 정보 — 자기 계정의 수신 상태만. 남의 것을 "
                          "가리킬 인자가 시그니처에 없다")
    def me(self, request):
        """S-15 「내 정보」 — 나는 누구이고 **무엇을 받는가.**

        ★ 「내 알림 설정」의 **쓰기**(조용 시간·구역·채널 좁히기 · `DsmNotifyPrefs`)는
          여기 없다 — 그 면은 등록부의 **WS-02(lane U3)** 다. 한 표에 두 차선의 손이
          닿으면 그 표가 곧 당직자의 수신 여부다. 응답의 `prefs_surface_open: false` 가
          「설정이 없다」가 아니라 **「설정 화면이 아직 없다」**를 말해 준다.
        """
        from kernels.k2_notify import my_notify_reach

        return my_notify_reach(scope=_scope(request))

    # ═══════════════════════════════════════════════════════════════════════
    # 턴 U · 차선 U56 — 「끝내기」 다섯 (WS-22·WS-23 · API-03·04)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # ⚠ **경로 삼킴을 다시 세어 봤다** [실측 · 턴 U] `api.py`(먼저 등록)의 변수 조각은
    #   `/settings/{domain}` 하나뿐이다. 아래 다섯은 조각이 둘 이상이거나 `/settings/`
    #   로 시작하지 않으므로 삼키지 않는다:
    #       `/cameras/{int:camera_id}/address`      (3조각 · 앞의 `/cameras/*` 는 리터럴 둘뿐)
    #       `/system/restart-request` · `/system/requests` · `/system/backup-receipts`
    #       `/system/storage`
    #       `/settings/api-keys/{int:key_id}/scopes` (4조각 — `{domain}` 은 1조각만 먹는다)

    # ── WS-23 「한 대 고치기」 — 카메라 주소 전용 문 (U5 #5) ────────────────
    #
    # 왜 전용 문을 여는가 — **일괄 등록 문이 하던 일을 그만두게 하려는 것이 아니다**
    # -------------------------------------------------------------------------
    # 화면(`CameraAddress.tsx`)은 지금까지 한 대의 주소를 **한 줄짜리 CSV** 로 만들어
    # `POST /cameras/import` 에 보냈다. 그것이 옳은 임시방편이었다(같은 판정식을
    # 두 벌로 두지 않기 위해서다). 그러나 그 길에는 **한 대를 고칠 수 없는** 성질이
    # 둘 있다 [실측 · 턴 U]:
    #   ① 일괄 문은 **이름으로** 카메라를 찾는다 — 이름을 바꾼 카메라는 못 찾고
    #      **새로 만들어진다**(action=create). 「고치기」가 조용히 「만들기」가 된다.
    #   ② 대상이 id 가 아니므로 **남의 테넌트 404** 를 잴 자리가 없다 — 남의 이름은
    #      「없다」가 아니라 「만들겠다」가 된다.
    # 이 문은 **id 로** 한 대를 고친다. 만들지 않는다 — 없으면 404 다.
    @route.post("/cameras/{int:camera_id}/address", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5 #5 카메라 주소 한 대 — 남의 테넌트 카메라의 주소를 "
                          "바꾸면 그 주소가 남의 알림 본문으로 나간다 (쓰기 IDOR)")
    def set_camera_address(self, request, camera_id: int, address: str,
                           detail: str = ""):
        """UX-02 — **id 로 지목한 한 대**의 설치 주소를 채운다.

        · 관리자만 (`guard_setting` · F-12 와 같은 문지기 · 감사 1행)
        · 남의 테넌트 카메라는 **404** — 403 은 「있는데 못 만진다」를 알려 주고,
          그것만으로 남의 테넌트에 그 id 가 있다는 사실이 샌다 (D-269)
        · 빈 주소는 **422** — 「비운다」가 아니라 「값이 틀렸다」다. 지우는 문은
          따로 세운다(지우는 쪽으로 틀리지 않는다)
        · `address_source` 는 언제나 `manual` 이다 — 팝업으로 채워도 **출처는 사람**
          이다(D-331). 이 문에 출처 인자를 두지 않는 이유가 그것이다.
        """
        from apps.dsm.services import guard_setting
        from stream_monitors.models import StreamMonitor

        scope = _scope(request)
        value = (address or "").strip()
        if not value:
            # 422 — ninja 가 「인자가 없다」에 쓰는 코드와 같다. 빈 값은 값이 아니다.
            raise HttpError(422, "주소가 비었습니다 — 빈 주소는 없는 주소보다 나쁩니다.")
        if len(value) > 255:
            raise HttpError(422, "주소가 255자를 넘습니다.")

        access = guard_setting(
            scope=scope, action="write:camera:address:%s" % camera_id,
            api_method="POST")
        if not access.allowed:
            raise HttpError(403, access.reason)

        row = _one_camera(scope, camera_id, StreamMonitor)
        if row is None:
            raise HttpError(404, "그런 카메라가 없습니다.")

        before = row.install_address or ""
        row.install_address = value
        row.install_address_detail = (detail or "").strip() or None
        row.address_source = StreamMonitor.AddressSource.MANUAL
        row.save(update_fields=["install_address", "install_address_detail",
                                "address_source"])
        return {"camera_id": row.pk, "name": row.name,
                "install_address": row.install_address,
                "install_address_detail": row.install_address_detail or "",
                "address_source": row.address_source,
                #: ★ 「무엇에서 무엇으로」 — 화면이 「채웠다」와 「덮어썼다」를 가른다.
                "was_blank": not before, "previous_address": before,
                "audit_id": access.audit_id}

    # ── WS-22 「재시작 요청」 — **기록만.** 실행은 대표·점검 창 ──────────────
    #
    # ★★ 이 문은 컨테이너를 **건드리지 않는다.** 건드리면 그것이 「운영계 외부 행위」이고
    #    표의 줄이 아니라 결함이다(턴 U 선등록이 그렇게 적었다). 여기서 일어나는 일은
    #    행 하나와 감사 한 줄이 전부이고, 응답 문장이 그 사실을 말한다.
    @route.post("/system/restart-request", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5 #14 재시작 요청 — 남의 테넌트 이름으로 점검을 "
                          "요청할 수 없다. 기록만 남는다")
    def request_restart(self, request, reason: str):
        """재시작을 **요청**한다. 관리자만 · 사유 필수 · 감사 1행.

        ★ `status` 는 `requested` 로 태어난다. 「완료」는 실행한 사람이 적는다 —
          이 문이 `done` 을 적으면 아무도 안 한 일이 초록이 된다.
        """
        from apps.dsm.services import guard_setting
        from stream_monitors.models import DsmSystemRequest

        scope = _scope(request)
        text = (reason or "").strip()
        if not text:
            raise HttpError(422, "사유가 비었습니다 — 사유 없는 재시작 요청은 "
                                 "다음 사람에게 「왜 내렸는지 모르는 정지」입니다.")
        if len(text) > 255:
            raise HttpError(422, "사유가 255자를 넘습니다.")

        access = guard_setting(
            scope=scope, action="write:system:restart-request", api_method="POST")
        if not access.allowed:
            raise HttpError(403, access.reason)

        actor = scope.require_actor()
        row = DsmSystemRequest.objects.create(
            purpose_code="dsm.ops", kind=DsmSystemRequest.Kind.RESTART,
            reason=text, status=DsmSystemRequest.Status.REQUESTED,
            requested_by=actor)
        return {"request_id": row.pk, "kind": row.kind, "status": row.status,
                "reason": row.reason, "executed": False,
                "message": RESTART_ACK, "audit_id": access.audit_id}

    @route.get("/system/requests", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5 #14 요청 목록 — 남의 테넌트가 무엇을 요청했는지는 "
                          "남의 정보다")
    def system_requests(self, request, limit: int = 20):
        """요청 목록 — **최근 것부터.** 관리자만. 빈 목록은 「요청이 없다」다."""
        from apps.dsm.services import guard_setting
        from stream_monitors.models import DsmSystemRequest

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="read:system:requests", api_method="GET")
        if not access.allowed:
            raise HttpError(403, access.reason)

        rows = DsmSystemRequest.objects.all().order_by("-id")[:max(1, min(limit, 100))]
        return {
            "total": DsmSystemRequest.objects.count(),
            "requests": [
                {"request_id": r.pk, "kind": r.kind, "status": r.status,
                 "status_label": r.get_status_display(), "reason": r.reason,
                 "requested_by": getattr(r.requested_by, "username", "") or "",
                 "created_at": r.created_on.isoformat() if r.created_on else None,
                 "handled_note": r.handled_note}
                for r in rows],
            "note": RESTART_ACK,
        }

    # ── 백업 회수증 — **실물을 읽는다. 없으면 회색이다** ─────────────────────
    @route.get("/system/backup-receipts", auth=JwtOrInboundKey())
    @tenant_scoped(required=False,
                   reason="운영 기반의 사실(마지막 회수증 시각·파일 이름)이다. "
                          "테넌트 자료가 아니라 관리자에게만 연다 — guard_setting 이 문지기")
    def backup_receipts_view(self, request):
        """마지막 회수증 시각 · 파일 · **검증 가능 여부** · 다음 예정.

        ★ 회수증을 한 장도 못 찾으면 `verdict: "UNKNOWN"` 이다 — `0` 을 초록으로
          적지 않는다(D-301). 「백업이 0건이다」와 「여기서 안 읽힌다」는 다른 사실이다.
        ★ 주기가 꺼져 있으면 **「예정 없음 — 꺼짐」을 말로** 낸다. 빈 칸으로 두면
          「아직 안 정했다」와 「꺼 두기로 했다」가 같은 그림이 된다.
        ★ 나가지 않는 것: 회수증 안의 `db_settings`(호스트·계정) · 경로 전문 · 해시.
        """
        from apps.dsm.services import guard_setting
        from common.ops_tasks import backup_receipts

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="read:system:backup-receipts", api_method="GET")
        if not access.allowed:
            raise HttpError(403, access.reason)
        return backup_receipts()

    # ── 저장 상한 선언 → `storage_used_pct` (U5 #15) ────────────────────────
    @route.get("/system/storage", auth=JwtOrInboundKey(), response=StorageOut)
    @tenant_scoped(required=False,
                   reason="운영 기반의 사실(상한·사용량)이다. 관리자에게만 연다")
    def system_storage(self, request):
        """상한 N GB · 사용 N% — **선언이 없으면 그 말을 그대로 낸다.**

        ★ 판정은 `common.ops_tasks.storage_declaration()` **하나**다. 크론
          (`scripts/ops_monitor.py`)도 같은 함수를 읽는다 — 두 자리에서 따로 재면
          크론이 UNKNOWN 을 적는 날 이 화면이 초록을 그린다(D-212).
        ★ 이 문에만 ninja `Schema` 를 붙였다 — OpenAPI `components.schemas` 를
          0 에서 띄우는 자리다(U6 #14 계열 · 연계 명세가 그 스키마를 인용한다).
        """
        from apps.dsm.services import guard_setting
        from common.ops_tasks import storage_declaration

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="read:system:storage", api_method="GET")
        if not access.allowed:
            raise HttpError(403, access.reason)
        return storage_declaration()

    # ── API-03·04 「키 범위」 ────────────────────────────────────────────────
    #
    # ★ 범위의 정본은 `kernels/k5_trust/key_scopes.py` 하나다 — 이 라우트는 문지기와
    #   오류 코드만 정한다(D-212). 모르는 이름은 **422**(값이 틀렸다) · 남의 키는
    #   **404**(존재도 새지 않는다 · D-269) · 관리자가 아니면 **403** · 익명은 **401**.
    @route.get("/settings/api-keys/{int:key_id}/scopes", auth=JwtOrInboundKey())
    @tenant_scoped(reason="API-03 키 범위 조회 — 남의 테넌트 키의 범위는 남의 정보다")
    def api_key_scopes_get(self, request, key_id: int):
        """이 키가 어디까지 가는가. **정한 적 없으면 그렇게 말한다**(`state: "unset"`)."""
        from apps.dsm.services import guard_setting
        from kernels.k5_trust import (ALLOWED_SCOPES, InboundKeyNotFound,
                                      get_key_scopes)

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="read:inbound-api-key:scopes:%s" % key_id, api_method="GET")
        if not access.allowed:
            raise HttpError(403, access.reason)
        try:
            _assert_key_in_tenant(scope, key_id)
        except InboundKeyNotFound:
            raise HttpError(404, "그런 키가 없습니다.")
        view = get_key_scopes(scope=scope, key_id=key_id)
        return {"key_id": key_id, "state": view.state,
                "scopes": list(view.scopes or []),
                "allowed": sorted(ALLOWED_SCOPES)}

    @route.post("/settings/api-keys/{int:key_id}/scopes", auth=JwtOrInboundKey())
    @tenant_scoped(reason="API-03 키 범위 저장 — 남의 테넌트 키의 범위를 넓히면 "
                          "그 키가 우리 자료에 닿는다 (쓰기 IDOR)")
    def api_key_scopes_set(self, request, key_id: int, scopes: str = ""):
        """범위를 정한다(덮어쓴다). `scopes` 는 쉼표 문자열 또는 JSON 배열 문자열.

        ★ 빈 문자열은 **빈 목록**이다 — 「아무 데도 못 간다」. 기본값으로 메우지
          않는다(메우는 자리는 발급 문 하나다).
        """
        from apps.dsm.services import guard_setting
        from kernels.k5_trust import (InboundKeyNotFound, InvalidScopeName,
                                      set_key_scopes)

        scope = _scope(request)
        access = guard_setting(
            scope=scope, action="write:inbound-api-key:scopes:%s" % key_id, api_method="POST")
        if not access.allowed:
            raise HttpError(403, access.reason)
        try:
            _assert_key_in_tenant(scope, key_id)
        except InboundKeyNotFound:
            raise HttpError(404, "그런 키가 없습니다.")
        try:
            view = set_key_scopes(scope=scope, key_id=key_id, scopes=scopes)
        except InvalidScopeName as exc:
            raise HttpError(422, str(exc))
        except InboundKeyNotFound:
            # ★ 커널도 스스로 「내 키인가」를 본다(턴 U 병합). 위 `_assert_key_in_tenant`
            #   가 이미 걸렀으므로 여기까지 오면 그 사이에 폐기·이관된 것이다 —
            #   그때도 답은 **404** 다(존재도 새지 않는다 · D-269). 안 받으면 500 이 된다.
            raise HttpError(404, "그런 키가 없습니다.")
        return {"key_id": key_id, "state": view.state,
                "scopes": list(view.scopes or []), "audit_id": access.audit_id}


def _one_camera(scope, camera_id: int, model):
    """내 테넌트의 그 카메라. 남의 것이면 **`None`**(404 로 답한다 · D-269).

    ★ `objects` 의 스레드 맥락에 기대지 않는다 — 「스레드에 남은 요청」 함정.
      소속을 손으로 물어 `group_id` 로 좁힌다.
    """
    from common.tenant_filters import get_user_group
    from common.tenant_roles import is_global_admin

    actor = scope.require_actor()
    qs = model.objects.all()
    if not is_global_admin(actor):
        group = get_user_group(actor)
        group_id = getattr(group, "pk", None)
        if group_id is None:
            return None
        qs = qs.filter(group_id=group_id)
    return qs.filter(pk=camera_id).first()


def _assert_key_in_tenant(scope, key_id: int) -> None:
    """그 키가 **내 테넌트에** 있는가. 없으면 `InboundKeyNotFound`(→ 404).

    ★ 판정을 새로 짓지 않는다 — `k5_trust.list_keys` 가 이미 테넌트로 좁힌 목록을
      낸다. 여기서 dj-core 표를 직접 뒤지면 격리 판정이 두 벌이 된다(D-212 · §0.4).
    """
    from kernels.k5_trust import InboundKeyNotFound, list_keys

    for view in list_keys(scope=scope):
        if view.key_id == key_id:
            return
    raise InboundKeyNotFound(key_id)
