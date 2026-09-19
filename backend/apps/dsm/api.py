# -*- coding: utf-8 -*-
"""DSM App 의 HTTP 면 — **신규 라우트는 트립와이어를 통과해야 한다** (D-275 §5-1).

이 파일이 지키는 셋
-------------------
① **문지기 없는 새 경로를 만들지 않는다.** WP-2 EXIT 가 남긴 미지는
   *"지금 닫혀 있는 이유는 라우트마다 문지기를 손으로 달았기 때문이고, 문지기 없는
   새 경로가 하나 생기면 그 순간 다시 샌다"* 였다. 그래서 모든 라우트가
   `@tenant_scoped()` 를 달고, **실제 좁히기는 커널이** `TenantScope` 로 한다
   (시그니처가 1차 · 문지기가 2차 — D-281).

② **오류는 HTTP 상태로 낸다.** `200 + {"success": false}` 를 만들지 않는다(W0-18).
   이 저장소는 권한 거부를 200 으로 내보내 **거부 사실이 소멸**한 라우트를 8건 갖고
   있었다. 신규 라우트는 그 전철을 밟지 않는다.

③ **`response=<단일 스키마>` 를 선언하지 않는다.** W0-18 실측: 그 선언이 붙은 8건에서
   거부 dict 가 스키마를 통과해 `200 + {}` 가 됐고, 거부 사실이 사라졌다.
   그 8건은 P-W0-18-1 A 안으로 전부 뗐다 — 새로 만들지 않는다.

왜 `BaseResponse` 를 쓰지 않나
------------------------------
기존 컨트롤러들은 `BaseResponse(status_code=..., ...)` 로 dict 를 돌려주고, 그 값은
**언제나 HTTP 200 으로 나간다.** 그것이 ②가 금지한 모양 그 자체다.
신규 App 은 성공이면 값을, 실패면 `HttpError` 를 던진다.
"""
# ★ `from __future__ import annotations` 를 **일부러 쓰지 않는다** (D-378 · 실측 2026-09-12).
#
#   브라우저를 처음 붙였더니 `/api/dsm/events` 가 **HTTP 500** 이었다:
#       pydantic.errors.PydanticUserError:
#           `QueryParams` is not fully defined; you should define `datetime`
#
#   미래 임포트가 켜지면 `since: datetime | None` 이 **문자열 주석**이 되고, ninja 는
#   그 문자열을 함수의 `__globals__` 에서 푼다. 그런데 이 핸들러는 `@tenant_scoped` 로
#   감싸여 있어 실제 함수 객체의 `__globals__` 는 `common/tenant_scope.py` 의 것이다 —
#   거기에 `datetime` 이 없다. 그래서 **주석이 영원히 풀리지 않는다.**
#
#   ★ 단위 시험은 이것을 못 잡았다. 시험은 `services.recent_events` 를 직접 부르고,
#     실패하는 자리는 **라우트가 질의 인자를 만드는 순간**이기 때문이다 — 착시 ⑨의
#     정확히 같은 모양이다(코드는 있고 시험은 초록인데 운영 경로가 죽는다).
#     화면을 처음 띄운 그 순간에 나왔다. **화면이 시험이었다.**
#
#   왜 여기서 미래 임포트를 빼는 것으로 고치나: 파이썬 3.11 에서 `X | None` 과
#   `dict[str, int]` 는 미래 임포트 없이도 동작한다. 데코레이터 쪽을 고치면
#   `common/tenant_scope.py` 가 자기와 무관한 타입을 임포트하게 되고, 그것은
#   **다음 사람이 이유를 못 읽는 코드**다.
from datetime import datetime, timedelta

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.wall_token import JwtOrWallToken
from common.tenant_roles import is_global_admin, is_tenant_admin
from common.tenant_scope import TenantScope, tenant_scoped
from core.api.v1.auth import CustomJWTAuth

from apps.dsm import services
from apps.dsm.exceptions import (
    IncidentReportUnavailable,
    PermissionDeniedForSetting,
    SettingNotAvailable,
)


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401** — 여기까지 오면 안 되는 상태다.

    `TenantScope.of(None)` 이 던지는 것을 그대로 500 으로 내보내지 않는다:
    인증이 없는 것은 서버 결함이 아니라 요청의 상태이고, 둘은 다른 상태 코드다.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


#: W1 요약 한 줄이 세는 「미처리」의 상한. **세는 데에도 상한이 있다** — 상한 없이
#: 세면 이벤트가 쌓인 테넌트에서 요약 한 줄이 목록보다 무거워지고, 그러면 가장 급한
#: 사람이 가장 오래 기다린다. 상한에 닿았다는 사실은 응답이 `unhandled_capped` 로 말한다.
_UNHANDLED_CAP = 500


def _panel_payload(panel) -> dict:
    """K3 `PanelView` → 화면이 읽는 dict. **상태를 반드시 싣는다.**

    상태를 빼면 화면이 "값이 없으니 빈 칸" 으로 그리고, 그 순간 오류와 빈 칸이
    같은 그림이 된다 — DA-03 §2-5 규칙 1이 금지한 자리다.
    """
    return {
        "panel_id": panel.panel_id,
        "dashboard_id": panel.dashboard_id,
        "title": panel.title,
        "panel_type": panel.panel_type,
        "state": panel.state.value,
        "reason": panel.reason,
        "config": panel.config,
    }


def _link_payload(link, request) -> dict:
    """연계 상태 → 화면이 읽는 dict. **사유는 싣지 않는다** (P-27 · 2026-09-26).

    ★ 여기가 사고가 났던 자리다. 앞판은 `reason` 을 그대로 실었고, 그 안에는
      상대사명 · 계약번호 · 조항 · 미이행 사실이 문단으로 들어 있었다. 관제요원 화면의
      「연계 상태」 상자가 그것을 그대로 그렸다 — 정직하려던 것이 누출이 됐다.

    ★ **막는 곳은 화면이 아니라 여기다.** 화면에서 안 그리게 하는 방식은 다음 화면이
      다시 그린다. 서버가 주지 않으면 어떤 화면도 그릴 수 없다.

    관리자에게만 `detail` 한 줄을 준다. 그 한 줄도 지어내지 않고 **사전에서** 가져온다
    (`services.LINK_DETAIL`) — 상대사명 · 계약번호 · 조항은 거기에도 없다.
    """
    user = getattr(request, "user", None)
    admin = is_global_admin(user) or is_tenant_admin(user)
    payload: dict = {"status": link.status.value}
    if admin:
        payload["detail"] = services.link_detail(link.status)
    return payload


def _subscription_payload(sub) -> dict:
    """구독 → 화면·연동 담당자가 읽는 dict.

    ★ **서명키 값을 담는 칸이 없다** (D-204). 여기 한 칸을 만들면 그 값이 화면과
      브라우저 개발자 도구와 로그에 남는다. 웹훅 서명키가 새면 **누구나 우리 이름으로
      경보를 낼 수 있다** — 그것이 SEC-16 이 존재하는 이유다. 나가는 것은 **이름**뿐이다.
    """
    return {
        "subscription_id": sub.subscription_id,
        "endpoint_url": sub.endpoint_url,
        "signing_key_ref": sub.signing_key_ref,
        "event_types": list(sub.event_types),
        "min_severity": sub.min_severity,
        "payload_format": sub.payload_format,
        "is_active": sub.is_active,
        "last_delivered_at": sub.last_delivered_at,
    }


# ★ 접두어를 비운다. `config/urls.py` 가 이미 `api/dsm/` 로 마운트하므로 여기서 다시
#   "/dsm" 을 붙이면 **`/api/dsm/dsm/...` 가 된다** — 기존 앱들이 실제로 그 모양이다
#   (`/api/stream-monitors/stream-monitors/...`). 새로 만드는 것까지 그럴 이유는 없다.
@api_controller("", tags=["DSM — 재난안전 모니터링 (F-09~F-12)"])
class DsmAPI:
    """F-09~F-12 의 라우트. **커널을 소비만 한다** (DA-04 §1-1)."""

    # ── F-09 재난 대시보드 ───────────────────────────────────────────────
    @route.get("/dashboard/frame", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-09 대시보드 프레임 — 남의 테넌트 패널이 섞이면 안 된다")
    def dashboard_frame(self, request, dashboard_code: str | None = None):
        """F-09 프레임. **AC-09 ①의 5상태를 값으로 낸다.**

        검수에서 "5상태 100%" 를 물으면 세지 않고 이 응답을 보여 준다:
        `five_states` 가 정의된 다섯이고 `state_counts` 가 각 상태의 칸 수다.
        **분모를 함께 낸다** — "정상 3칸" 만 보면 전체가 3인지 30인지 모른다.
        """
        frame = services.dashboard_frame(scope=_scope(request),
                                         dashboard_code=dashboard_code)
        return {
            "preset": frame.preset,
            "preset_matched": frame.preset_matched,
            "five_states": list(frame.five_states),
            "state_counts": frame.state_counts,
            "panel_total": len(frame.panels),
            "panels": [_panel_payload(p) for p in frame.panels],
            "link": _link_payload(frame.link, request),
        }

    @route.get("/dashboard/link-state", auth=JwtOrInboundKey())
    @tenant_scoped(required=False,
                   reason="연계 상태는 테넌트별 사실이 아니라 **설비의 사실**이다 — "
                          "테넌트 모델을 만지지 않으므로 group 을 요구하지 않는다. "
                          "그래도 표식은 단다: 표식이 없는 라우트는 '분류를 잊은 것' 과 "
                          "'분류가 필요 없는 것' 이 구별되지 않는다 (D-272)")
    def link_state(self, request):
        """FR-09-4 — 연계 정상 / 대기 / 끊김.

        ★ 인증은 필요하고 테넌트 좁히기는 필요 없다. 그 둘은 다른 질문이고,
          `required=False` 가 그 답을 코드에 남긴다. PUBLIC_ROUTES 에 넣지 않는 이유도
          같다 — 그 목록은 **인증 불요**를 뜻하고, 이 라우트는 인증이 필요하다.
        """
        state = services.link_state()
        return _link_payload(state, request)

    @route.get("/events", auth=JwtOrInboundKey(
        inbound_key=True,
        reason="F-05 「외부 App 이 이벤트 OpenAPI 하나로만 들어온다」 — 읽기 전용 조회"))
    @tenant_scoped(reason="F-09 이벤트 목록 — 남의 테넌트 이벤트가 보이면 격리 실패다")
    def events(self, request, since: datetime | None = None,
               until: datetime | None = None,
               event_type: str | None = None, severity: str | None = None,
               response_state: str | None = None, mine: bool = False,
               stream_monitor_id: int | None = None,
               limit: int = 50):
        """F-09 이벤트 목록.

        ★ 2026-09-17 (턴 T · 차선 U3) — `stream_monitor_id` 가 더해졌다. M2 「이 카메라
          7일」절이 `stream_monitor_id=<id>&since=<7일 전>` 으로 부른다 — 새 라우트가
          아니라 **있던 목록에 필터 하나**다. 커널 `query_events` 는 이 인자를 처음부터
          받았다(`k1_event/services.py:376`) — HTTP 로 여는 것뿐이다.
          (병합 · 조율자) 처음엔 `services.recent_events` 가 이 인자를 안 받아 여기서 커널을
            직접 불렀고, 진입면 시험이 「K1 소비 App 이 둘」로 막았다 — 인자를 services 로
            옮겨 App 은 하나다. 필터는 한 층(커널)에만 있다.

        ★ NFR-09-1 — 스트리밍 서버가 죽어도 이 목록은 200 이다.
          여기서 스트리밍을 부르지 않는 것이 그 성질의 전부다.

        ★ 2026-09-21 — `response_state` 가 **나가고 들어온다**(W1 「미처리」 프리셋).
          그전까지 대응 축은 상세에만 있었고, 그래서 관제팀장의 「미처리 이벤트 확인」을
          서버가 걸러 줄 수 없었다(온보딩 48행 U2 #2). 화면이 목록을 받아 자기가 거르면
          **페이지 밖 이벤트는 없는 것이 된다** — DA-04 「필터는 전부 서버에서」.

        ★ 2026-09-23 (차선 C · W1 프리셋 4종) — `until` 과 `mine` 이 더해졌다.

          · `until` 은 「지난 12시간」의 **닫는 쪽**이다. `since` 만 있으면 창이
            열려 있고, 열린 창은 「지난 12시간」이 아니라 「12시간 전부터 지금까지
            그리고 미래」다. 두 끝을 다 받는 것이 창이다.

          · `event_type` 은 **쉼표로 여럿**을 받는다(`camera_down,storage_high`).
            「시스템」 프리셋이 그것을 쓴다 — 시스템 신호는 한 유형이 아니다.

          · `mine=true` 는 **요청자 자신**으로 좁힌다. `reviewed_by_id=<숫자>` 를
            질의로 받지 않는 이유: 그러면 화면이 남의 사번을 넣어 「그 사람이 무엇을
            판정했나」를 물을 수 있고, 그것은 이 라우트가 계약한 것이 아니다.
            좁히는 값을 **서버가 정한다** — 요청은 「나」라고만 말한다.
            ⚠ 「내가 **판정**한 것」이다. 「내가 대응한 것」이 아니다 — 대응 전이의
              행위자는 행이 아니라 감사에 있다(D-399 가 두 축을 가른 그 이유).
        """
        scope = _scope(request)
        #: ★ 유형 **여럿**을 받는다 (2026-09-23 · W1 「시스템」 프리셋).
        #:   시스템 신호는 한 유형이 아니라 여럿이다(`camera_down` · `storage_high` ·
        #:   앞으로 늘어날 것들). 화면이 유형마다 한 번씩 부르면 두 응답을 화면이 합치게
        #:   되고, 합치는 순간 **각 응답의 상한이 따로 걸린다** — 「미처리 3건」이
        #:   실은 「첫 유형 상한 안의 3건」이 되는 그 모양이다.
        #:   커널 `query_events` 는 처음부터 `str | Iterable` 을 받는다 — 여기서 새로
        #:   만드는 것이 아니라 **이미 있는 것을 HTTP 로 여는 것**이다.
        types = ([t.strip() for t in event_type.split(",") if t.strip()]
                 if event_type and "," in event_type else event_type)
        reviewed_by_id = None
        if mine:
            #: `require_actor()` 는 시스템 스코프면 던진다 — 「나」가 없는 요청이
            #: 「나의 것」을 물으면 그것은 400 이 아니라 **일어날 수 없는 요청**이다.
            reviewed_by_id = getattr(scope.require_actor(), "pk", None)
            if reviewed_by_id is None:
                raise HttpError(403, "요청자를 특정할 수 없어 「내 담당」을 낼 수 없습니다.")
        rows = services.recent_events(scope=scope, since=since, until=until,
                                      event_type=types, severity=severity,
                                      response_state=response_state,
                                      reviewed_by_id=reviewed_by_id,
                                      stream_monitor_id=stream_monitor_id,
                                      limit=limit)
        return {"total": len(rows), "events": [
            {"event_id": e.event_id, "event_type": e.event_type,
             "severity": e.severity, "status": e.status, "verdict": e.verdict,
             "occurred_at": e.occurred_at, "last_seen_at": e.last_seen_at,
             "stream_monitor_id": e.stream_monitor_id,
             "stream_monitor_name": e.stream_monitor_name,
             "lat": e.lat, "lng": e.lng, "snapshot_path": e.snapshot_path,
             "response_state": e.response_state}
            for e in rows]}

    # ── W1 요약 한 줄 (차선 C · 2026-09-23) ─────────────────────────────
    #
    # ★ **라우트 삼킴을 먼저 본다** (D-410 이 남긴 자리). 바로 아래 `/events/{int:event_id}`
    #   는 `int` 변환기라 「summary」를 삼키지 않는다 — 그래도 **위에 둔다.** 변환기가
    #   언젠가 `{str:...}` 로 바뀌면 그 순간 이 라우트가 조용히 404 가 되고, 조용한
    #   404 는 「기능이 없다」와 구별되지 않는다.
    #
    # ★ 이 라우트가 여는 것은 **읽기뿐**이다 — 쓰기 면이 아니므로 WRITE_PROBES 대상이
    #   아니다(P-8 은 쓰기 면의 규약이다).
    @route.get("/events/summary", auth=JwtOrInboundKey())
    @tenant_scoped(reason="W1 요약 — 남의 테넌트 오탐률·미처리 수가 섞이면 격리 실패다")
    def events_summary(self, request, hours: int = 12):
        """U2 #1 「밤사이 요약 보기」 · W1 프리셋 「지난 12시간」의 **한 줄**.

        ★ 이 수를 App 이 세지 않는다. 오탐은 K6(`false_positive_rate`)가, 미처리는
          K1(`query_events`)이 센다 — App 은 **둘을 한 응답에 나란히 놓을 뿐**이다.
          여기서 나눗셈을 한 줄이라도 하면 집계 경로가 둘이 되고, 갈린 수는 고객
          앞에서 못 쓴다(DA-04 K6 「집계 경로를 하나로 유지하는 것 자체가 요구사항」).

        ★ **분모를 함께 낸다** (D-271 ③ · D-301). 「오탐 4건」만 보면 그것이 12건 중
          4인지 400건 중 4인지 모른다. `reviewed`(판정 모수) · `unreviewed`(미판정) 를
          같이 실어 보낸다.

        ★ 분모가 0이면 `rate` 는 **`null` 이다 — 0.0 이 아니다.** 0.0 으로 내면
          「판정을 안 하기만 해도 오탐률이 좋아지는」 지표가 된다. 그래서 화면이
          두 경우를 가를 수 있도록 `measurable` 을 함께 낸다.

        ★ 미처리 수에는 **상한이 있다.** 상한에 닿으면 `unhandled_capped=true` 로
          말한다 — 「215건」과 「최소 200건」을 같은 숫자로 내보내면 그 순간
          요약 한 줄이 거짓말을 한다(D-301 분모 규약의 같은 계열).
        """
        from django.utils import timezone

        from kernels.k6_feedback import false_positive_rate

        if hours <= 0 or hours > 24 * 31:
            # 400 — 요청이 틀렸다. 창을 임의로 잘라 「그럴듯한 수」를 내지 않는다.
            raise HttpError(400, "hours 는 1 이상 744(31일) 이하여야 합니다.")

        scope = _scope(request)
        until = timezone.now()
        since = until - timedelta(hours=hours)

        rate = false_positive_rate(scope=scope, since=since, until=until)
        w = rate.total

        #: 미처리 = 대응 축이 아직 「발생」인 것. `status`(탐지 판정)로 세지 않는다 —
        #: 두 축을 섞으면 U2 가 「봐야 할 것」과 「판정해야 할 것」을 구별하지 못한다.
        pending = services.recent_events(
            scope=scope, since=since, until=until,
            response_state="occurred", limit=_UNHANDLED_CAP + 1)
        capped = len(pending) > _UNHANDLED_CAP

        return {
            "hours": hours,
            "since": since,
            "until": until,
            #: 「지금 눈앞에 몇 건이 남아 있나」 — W1 「미처리」 프리셋이 여는 그 수.
            "unhandled": min(len(pending), _UNHANDLED_CAP),
            "unhandled_capped": capped,
            "unhandled_cap": _UNHANDLED_CAP,
            #: 오탐 축. **비율만 내지 않는다** — 분자·분모를 함께 낸다.
            "false_positive": w.rejected,
            "reviewed": w.reviewed,
            "unreviewed": w.unreviewed,
            "closed_without_verdict": w.closed_without_verdict,
            "false_positive_rate": w.rate,          # 분모 0 이면 **null**
            "measurable": rate.is_measurable,
        }

    # ── UX-13 단일 초점 큐 · UX-14 대응 시계 (차선 C · 2026-09-24) ────────
    #
    # ★ **라우트 삼킴을 먼저 본다** (D-410 이 남긴 자리). 이 둘은 아래
    #   `/events/{int:event_id}` **위**에 선다. 지금은 `int` 변환기라 「queue」·
    #   「response-times」를 삼키지 않지만, 변환기가 `{str:...}` 로 바뀌는 날
    #   조용히 404 가 되고 조용한 404 는 「기능이 없다」와 구별되지 않는다.
    #
    # ★ 둘 다 **읽기 전용**이다 — 쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다(P-8).
    # ★ [UX-24a · 턴 F · 차선 S] 월 표시 토큰이 닿는 **두 문 중 하나**.
    #   `/wall` 이 20초마다 부르는 자리다(Wall.tsx:177). 선언한 라우트만 그 토큰을
    #   받는다 — 선언 없는 라우트는 거절이 기본값이다(`common/wall_token.py`).
    #   ⚠ 읽기뿐이다. 같은 토큰으로 쓰기를 때리면 미들웨어가 먼저 403 을 낸다.
    @route.get("/events/queue", auth=JwtOrWallToken(
        wall_token=True,
        wall_reason="UX-24a 월 화면의 초점 큐 칸 — 세션 없이 읽는다 (P-62)",
    ))
    @tenant_scoped(reason="UX-13 초점 큐 — 남의 테넌트 이벤트가 최상단에 오면 격리 실패다")
    def events_queue(self, request, since: datetime | None = None,
                     until: datetime | None = None, limit: int = 200):
        """**W1 최상단은 목록이 아니라 가장 급한 하나다** (UX-13).

        왜 목록 라우트로 안 되나 — 「가장 급한 하나」와 「5분 창 묶음」은 **페이지
        밖까지 봐야** 정해진다. 화면이 `/events` 한 페이지를 받아 자기가 고르면
        상한 밖에 있는 더 급한 사건이 **없는 것이 된다**(DA-04 「필터는 전부 서버에서」).

        ★ **이벤트를 접는 것이 아니다.** 원본 건수는 `total_events` 로 그대로 나가고
          카드 수는 `card_total` 로 따로 나간다 — 둘이 다른 수인 것이 요점이다.
          F-14 통계는 원본을 세고, 접히는 것은 화면이지 기록이 아니다.

        ★ 문턱 표(`tier_thresholds_sec`)를 **함께 낸다.** 화면은 시계가 계속 도니까
          자기도 계산해야 하는데, 그 표를 화면이 따로 들면 서버 통계와 화면 글자가
          다른 문턱을 쓰게 된다 — `allowed_next` 와 같은 규약이다(D-399).
        """
        if limit <= 0 or limit > 1000:
            raise HttpError(400, "limit 은 1 이상 1000 이하여야 합니다.")
        return services.focus_queue(scope=_scope(request), since=since,
                                    until=until, limit=limit)

    @route.get("/events/response-times", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-14 대응 시간 — 남의 테넌트 p50/p95 가 섞이면 격리 실패다")
    def events_response_times(self, request, days: int = 30, limit: int = 2000):
        """월간 p50 / p95 — **자동 종결을 분모에서 뺀다** (지시서 §3-4).

        빼지 않으면 오탐 자동 종결이 대응 시간을 좋게 만든다: 규칙이 즉시 닫은
        이벤트는 `발생 → 종결` 이 0초에 가깝고, 그것이 분모에 들어가면 **오탐이 많은
        달일수록 대응이 빨라 보인다.** 지표가 사실의 정반대를 말하는 자리다.

        ★ 뺀 건수(`excluded_auto_closed`)를 **함께 낸다.** 분모 없는 백분위는
          「7건 중 p95」와 「700건 중 p95」를 같은 숫자로 내보낸다(D-301).
        ★ 분모 0 이면 p50·p95 는 **`null` 이다 — 0 이 아니다.** 대응한 적이 없는 달과
          즉시 대응한 달을 같은 숫자로 내면 그 표는 대외 보고에 못 쓴다.
        """
        from django.utils import timezone

        if days <= 0 or days > 366:
            raise HttpError(400, "days 는 1 이상 366 이하여야 합니다.")
        until = timezone.now()
        return services.response_latency(scope=_scope(request),
                                         since=until - timedelta(days=days),
                                         until=until, limit=limit)

    # ★ 들어오는 키를 **받지 않는다**(기본값 거절). 상세는 목록에 없는 것을 더 낸다 —
    #   `clip_path`(영상 구간) · `address` · `reviewed_by_id`. 계약이 F-05 로 연 것은
    #   **이벤트 조회**이지 이 셋이 아니고, 계약이 안 연 것을 우리가 열지 않는다(D-280).
    #   화면은 사람의 토큰으로 부르므로 이 선택이 화면을 막지 않는다.
    @route.get("/events/{int:event_id}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-09 이벤트 상세 — 남의 이벤트 id 로 펴 보면 IDOR 이다")
    def event_detail(self, request, event_id: int):
        """F-09 이벤트 상세 (D-371 ⑤ 화면 셋 중 셋째).

        ★ 남의 것이면 **404** 다 (403 이 아니다). 403 은 「그 id 는 있지만 네 것이
          아니다」를 알려 주고, **존재 여부가 새는 것도 누출**이다 — 판정은 K1 이 한다.

        ★ `verdict` 를 `status` 와 따로 낸다(D-293). 종료된 이벤트의 화면이
          「이것은 오탐이었다」를 계속 말할 수 있어야 한다.
        """
        e = services.event_detail(scope=_scope(request), event_id=event_id)
        return {
            "event_id": e.event_id, "event_type": e.event_type,
            "severity": e.severity, "status": e.status, "verdict": e.verdict,
            "occurred_at": e.occurred_at, "last_seen_at": e.last_seen_at,
            "stream_monitor_id": e.stream_monitor_id,
            "stream_monitor_name": e.stream_monitor_name,
            "confidence": e.confidence, "bbox": e.bbox,
            "snapshot_path": e.snapshot_path, "clip_path": e.clip_path,
            "address": e.address, "address_status": e.address_status,
            "lat": e.lat, "lng": e.lng,
            "reviewed_by_id": e.reviewed_by_id, "reviewed_at": e.reviewed_at,
            "reject_reason": e.reject_reason,
            #: ★ UX-17 — **이 이벤트가 훈련 중에 난 것인가** (`drill` / `live`).
            #:   화면·보고서가 이 값을 그대로 적는다(D-347 화면 메타 다섯째).
            #:   훈련 이벤트가 표식 없이 실제 이벤트와 섞이면, 나중에 그 달의 통계가
            #:   **훈련을 재난으로 센다.**
            "data_source": services.event_data_source(view=e),
            #: ★ D-399 — 대응 진행은 `status`(탐지 판정)와 **다른 축**이라 따로 낸다.
            #:   `allowed_next` 를 함께 내는 이유: 화면이 자기 전이표를 따로 들면
            #:   서버가 거절하는 버튼을 그리게 된다. 표는 서버에 하나만 둔다.
            **services.response_state(scope=_scope(request), event_id=e.event_id),
        }

    # ── UX-14 대응 시계 상세 (차선 C · 2026-09-24) ────────────────────────
    @route.get("/events/{int:event_id}/timeline", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-14 대응 시계 — 남의 이벤트 대응 이력을 펴 보면 IDOR 이다")
    def event_timeline(self, request, event_id: int):
        """네 시각 타임라인 — `occurred_at → acknowledged_at → arrived_at → closed_at`.

        ★ 착수 전 실측이 지시서를 고쳤다 [2026-09-24]: 이 넷 중 **모델에 있는 것은
          `occurred_at` 하나뿐**이다. 나머지 셋은 `logger.AuditLogs` 의 대응 전이
          기록에서 세운다 — D-399 가 그 칸의 주석에 *"현재 값만 여기 있고, 어떻게
          왔는지는 감사가 안다"* 라고 적어 둔 그대로다.
          칸 셋을 새로 만들지 않은 이유: 새 칸은 태어나는 순간 **과거가 비어 있고**,
          빈 과거는 「대응이 빨랐다」로 읽힌다.

        ★ 자동 종결이면 `auto_closed=true` 다. 「사람이 닫았다」와 같은 모양으로
          내보내면 대응 시간 통계가 오탐을 잘한 일로 센다.

        ★ **읽기 전용**이다 — 쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다(P-8).
        """
        return services.response_clock(scope=_scope(request), event_id=event_id)

    # ── 대응 진행 축 (D-399) ─────────────────────────────────────────────
    @route.post("/events/{int:event_id}/response", auth=JwtOrInboundKey())
    @tenant_scoped(reason="대응 진행 쓰기 — 남의 이벤트를 접수·종결할 수 없다 (쓰기 IDOR)")
    @idempotent("dsm.events.response")
    def advance_response(self, request, event_id: int, to_state: str,
                         reason: str = ""):
        """대응 진행을 한 칸 옮긴다 (D-399). 발생 → 접수 확인 → 조치중 → 종결.

        ★ **거절은 4xx 다.** `200 + {"success": false}` 를 만들지 않는다 —
          이 App 이 처음부터 금지한 모양이고(W0-18), 착시 ⑧의 자리다.

        셋을 **다른 상태 코드로** 가른다. 부르는 쪽이 할 일이 다르기 때문이다:
          409  그 전이 자체가 없다 — 다시 보내도 같다
          400  되돌림인데 사유가 비었다 — 채워 다시 보내면 된다
          403  되돌림인데 관제팀장이 아니다 — 이 사람은 못 한다
        하나로 묶어 400 만 내면 화면이 **무엇을 고쳐 다시 보낼지**를 모른다 (D-290).
        """
        #: ★ 커널 예외를 여기서 HTTP 로 번역한다. 커널은 HTTP 를 모른다 —
        #:   상태코드를 커널에 적으면 다음 소비자(배치·gRPC)가 그 값을 못 쓴다.
        #:   ⚠ 이름을 **`services` 를 거쳐** 받는다. 이 모듈이 K1 을 직접 부르면
        #:     `test_f05_event_api` 가 멈춘다 — 「K1 의 App 소비자는 하나뿐」이
        #:     F-05 「진입면 하나」의 실제 집행이고, 그 하나는 `services` 다.
        try:
            return services.advance_response(
                scope=_scope(request), event_id=event_id,
                to_state=to_state, reason=reason)
        except Http404:
            raise HttpError(404, "그런 이벤트가 없습니다.")
        except services.ResponseTransitionNeedsManager as exc:
            raise HttpError(403, str(exc))
        except services.ResponseTransitionNeedsReason as exc:
            raise HttpError(400, str(exc))
        except services.ResponseTransitionForbidden as exc:
            raise HttpError(409, str(exc))

    # ── 현장 회신 (U3 #9 · 차선 D 가 커널을, 조율자가 문을) ───────────────
    @route.post("/events/{int:event_id}/field-reply", auth=JwtOrInboundKey())
    @tenant_scoped(reason="현장 회신 쓰기 — 남의 이벤트에 회신을 남길 수 없다 (쓰기 IDOR)")
    @idempotent("dsm.events.field-reply")
    def field_reply(self, request, event_id: int, text: str = "",
                    kind: str = "note"):
        """이동 중인 사람이 한 줄을 돌려준다 (M3).

        ★ **문이 없으면 커널 면은 잠든 것이다.** 차선 D 가 커널과 시험을 세웠고
          `dormant` 게이트가 「켜진 상태로 태어나야 한다」로 이 자리를 잡았다 —
          그 빨강이 이 문을 만들게 했다(D-377).
        ★ 회신은 **계정이 남긴다.** 무계정 링크로 부를 수 있는 자리를 만들지 않는다.

        ★★ [턴 S · 차선 U3] **`kind` 가 붙었다 — 진입면은 넓어지지 않았다.**
          UX-45 M3 시트의 여섯 칸(도착 · 사진 · 한 줄 · 오탐 사유 · 지원 요청 ·
          조치 완료)을 **한 문**으로 받는다. 같은 문지기(`@tenant_scoped` +
          `JwtOrInboundKey`) · 같은 커널(`reply_from_field`) · 같은 감사 계열이고,
          바뀐 것은 **저장 문자열의 접두**뿐이다(`apps/dsm/field.py::compose_reply`).

          왜 커널에 칸을 더하지 않았나: 그 파일은 K1 이고 이번 턴 U3 의 소유가
          아니다 — 한 파일을 두 차선이 같은 턴에 고치면 충돌하고, 충돌한 라우트는
          **라우팅 침묵**이 된다. 판정과 사유는 `field.py` 의 kind 절에 적었다.

          ⚠ 접두는 **사람의 자리에 보이지 않는다.** 이 라우트가 `kind` 와 깨끗한
            `text` 로 갈라 내보낸다 — 화면이 접두를 보면 그것은 이 판정의 실패다.
          ⚠ `text` 의 기본값이 빈 문자열인 이유: 「도착」·「지원 요청」처럼 **누름
            자체가 사실**인 칸이 있다. 그 넷은 `field.py` 가 정한 문구로 채워지고,
            「한 줄」·「오탐 사유」 둘은 **여전히 본문이 필수**다(빈 회신을 기본
            문구로 메우면 아무도 안 적은 회신이 적은 것처럼 쌓인다).

        거절을 4xx 로 나눈다: 404 없는·남의 이벤트 · 422 빈 글·모르는 종류 ·
        403 요청자 없음(시스템 스코프).
        """
        from common.tenant_scope import SystemScopeCannotRead

        from apps.dsm import field

        #: ★ 커널에 닿기 **전에** 종류를 가른다. 모르는 종류를 `note` 로 접지 않는다 —
        #:   접으면 화면의 오타 하나가 「지원 요청」을 조용히 「한 줄」로 바꾼다.
        try:
            stored, _clean = field.compose_reply(kind=kind, text=text)
        except field.UnknownReplyKind as exc:
            raise HttpError(422, str(exc))

        try:
            reply = services.field_reply(
                scope=_scope(request), event_id=event_id, text=stored)
        except Http404:
            raise HttpError(404, "그런 이벤트가 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except services.InvalidEventInput as exc:
            raise HttpError(422, str(exc))
        # ★ 내는 칸은 `FieldReply` 가 **실제로 가진 것**뿐이다. 지어내지 않는다 —
        #   없는 칸을 읽어 라우트가 부르는 즉시 죽은 사례가 이 파일에 이미 있다(D-410).
        #   `kind` 는 지어낸 칸이 아니라 **저장된 문자열에서 되읽은 값**이다.
        name, body = field.split_reply(reply.text)
        return {"reply_id": reply.reply_id, "event_id": reply.event_id,
                "kind": name, "kind_label": field.kind_label(name),
                "text": body, "author_id": reply.author_id,
                "author_name": reply.author_name}

    @route.get("/events/{int:event_id}/field-replies", auth=JwtOrInboundKey())
    @tenant_scoped(reason="현장 회신 읽기 — 남의 이벤트 회신이 보이면 안 된다")
    def field_replies(self, request, event_id: int, limit: int = 50):
        """그 이벤트에 달린 현장 회신들. 이벤트 문지기를 먼저 지난다.

        ★★ [턴 S] **`by_kind` 를 함께 낸다** — M3 시트의 상태 칸이 읽는 값이다.
          화면이 목록을 받아 스스로 세지 않는 이유는 목록에 `limit` 이 있어서다:
          상한 밖의 회신이 안 세어지고, 그러면 「지원 요청 0건」이 실은
          「이 페이지에 없음」이 된다 — 그 사실이 화면에 안 나온다(D-301 · 모수).
          ⚠ 그래서 `by_kind` 도 **이 페이지의 수**다. 모수(`total`)를 함께 낸다.
        """
        from apps.dsm import field

        try:
            rows = services.field_replies(
                scope=_scope(request), event_id=event_id, limit=limit)
        except Http404:
            raise HttpError(404, "그런 이벤트가 없습니다.")

        replies = []
        by_kind: dict[str, int] = {}
        for r in rows:
            name, body = field.split_reply(r.text)
            by_kind[name] = by_kind.get(name, 0) + 1
            replies.append({
                "reply_id": r.reply_id, "event_id": r.event_id,
                "kind": name, "kind_label": field.kind_label(name),
                "text": body, "author_id": r.author_id,
                "author_name": r.author_name,
            })
        return {"total": len(rows), "by_kind": by_kind, "replies": replies}

    # ── 판정 축 (P-16 · 오탐 ②) ──────────────────────────────────────────
    @route.post("/events/{int:event_id}/review", auth=JwtOrInboundKey())
    @tenant_scoped(reason="판정 쓰기 — 남의 이벤트를 오탐이라 판정할 수 없다 (쓰기 IDOR)")
    @idempotent("dsm.events.review")
    def review_event(self, request, event_id: int, verdict: str, reason: str = ""):
        """이 탐지가 진짜인가를 판정한다 — `confirmed` / `rejected` (F-14 의 입력).

        ★ **이 문이 없어서 오탐률이 시드로만 채워지고 있었다.** 서비스는 2026-08 부터
          있었고 부를 주소가 없었다 — 착시 ⑨(함수는 문이 아니다)의 세 번째 실사례다.

        ★ `rejected` 면 **대응 축도 함께 닫힌다**(P-16). 다만 그 일은 이 라우트가
          하지 않는다 — 판정 신호를 받은 소비자 한 곳이 한다. 사용자에게 한 번의
          행동인 것과 코드에서 두 축이 맞물리는 것은 다른 일이다(D-399).

        **거절을 4xx 로 나눈다** (D-290). 부르는 쪽이 할 일이 다르기 때문이다:
          404  없는 이벤트 · **남의 테넌트 이벤트** (존재 여부도 새면 누출이다)
          422  판정값이 아니다 (`closed` 를 여기로 보내는 것 — 종료는 다른 문이다)
          403  요청자가 없다 (시스템 스코프) — **판정은 사람이 하는 일**이다(D-281)
        """
        from common.tenant_scope import SystemScopeCannotRead

        try:
            e = services.review_event(
                scope=_scope(request), event_id=event_id,
                verdict=verdict, reason=reason)
        except Http404:
            raise HttpError(404, "그런 이벤트가 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except services.InvalidEventInput as exc:
            #: 422 다 — 문법은 맞고 **값이 계약 밖**이다. 400 으로 묶으면 화면이
            #: 「보낸 모양이 틀렸나」와 「값이 틀렸나」를 구별하지 못한다.
            raise HttpError(422, str(exc))
        return {
            "event_id": e.event_id, "status": e.status, "verdict": e.verdict,
            "reviewed_by_id": e.reviewed_by_id, "reviewed_at": e.reviewed_at,
            "reject_reason": e.reject_reason,
            #: ★ 결합의 결과를 **같은 응답에** 실어 준다. 화면이 한 번 더 물어야 하면
            #:   그 사이에 두 종류의 종결이 보인다 — P-1 이 막으려던 그 모양이다.
            **services.response_state(scope=_scope(request), event_id=e.event_id),
        }

    # ── F-10 알림 발송 ───────────────────────────────────────────────────
    @route.post("/events/{int:event_id}/notify", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-10 발송 — 남의 이벤트로 발송을 일으킬 수 없다 (쓰기 IDOR)")
    @idempotent("dsm.events.notify")
    def notify(self, request, event_id: int):
        """F-10 발송. **실패도 200 이고, 실패는 행으로 보인다.**

        발송 실패는 이 라우트의 실패가 아니다 — 저하 운전(DA2-21 (4))이 요구하는 대로
        업체가 죽어도 이벤트 처리는 200 을 유지한다. 대신 각 행의 `succeeded` 가 갈린다.
        `404` 는 **남의 테넌트 이벤트**일 때만 난다.
        """
        from kernels.k2_notify import EventNotFound, InvalidNotifyInput, NoRecipients

        try:
            records = services.notify_event(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 이벤트가 없습니다.")
        # ★ [D-410 · 2026-09-19] **셋을 갈라 낸다** — 세 번째 눈이 잡은 자리다.
        #   계약 라우트 도달 판정기가 없는 id 로 두드렸더니 **500** 이었다:
        #   「그런 이벤트가 없다」를 **서버 결함**으로 내고 있었다. U6 은 자기 잘못인지
        #   우리 잘못인지 알 수 없고, 우리 감시는 남의 오타를 우리 장애로 센다.
        #
        #   404  없는 이벤트          — id 를 고쳐라 (남의 테넌트도 여기 · D-269)
        #   409  수신자 0명           — 요청이 틀린 게 아니라 **알림 체계가 꺼져 있다**.
        #                              200 으로 삼키면 그것이 조용한 무력화다(DA-03 §3-2)
        #   400  그 밖의 잘못된 입력  — 등급이 계약 밖 · 테넌트를 못 정함
        #   ⚠ 발송 **실패**는 여기 없다 — 그것은 200 이고 행의 `succeeded` 가 말한다.
        except EventNotFound:
            raise HttpError(404, "그런 이벤트가 없습니다.")
        except NoRecipients as exc:
            raise HttpError(409, str(exc))
        except InvalidNotifyInput as exc:
            raise HttpError(400, str(exc))
        return {"total": len(records), "deliveries": [
            {"delivery_id": r.delivery_id, "event_id": r.event_id,
             "recipient_id": r.recipient_id, "channel": r.channel,
             "succeeded": r.succeeded, "failure_reason": r.failure_reason,
             "sent_at": r.sent_at}
            for r in records]}

    # ── UX-19 외부 웹훅 구독 — **CAP 1.2 로 낸다** (2026-09-05 TC · 차선 S) ──
    #
    # ★ **새 인증 경로를 만들지 않았다** (세종 §4-4 · P-37).
    #   셋 다 `JwtOrInboundKey()` **기본값**이다 — 기본값은 「들어오는 키 거절」이고,
    #   `common/inbound_api_key.py` 의 규약 ③이 쓰기에 키를 열어 주는 것을 아예 막는다.
    #   `INBOUND_KEY_ALLOWED` 를 한 줄도 넓히지 않았다. 구독은 **계정이 등록한다.**
    # ★ 무계정 링크가 없다: 구독의 주인은 요청자의 테넌트이고 서버가 정한다.
    #   요청이 「누구 것으로 만들지」를 말할 수 있는 인자가 없다.
    @route.post("/webhook-subscriptions", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-19 구독 등록 — 남의 테넌트 이벤트를 내 주소로 받게 "
                          "만들 수 없다 (쓰기 IDOR). 구독은 한 번 걸면 그 뒤로는 "
                          "부르지 않아도 계속 나간다")
    def create_webhook_subscription(self, request, endpoint_url: str,
                                    signing_key_ref: str,
                                    event_types: str = "", min_severity: str = "",
                                    payload_format: str = "json"):
        """이벤트를 **표준(OASIS CAP 1.2)** 으로 받을 주소를 등록한다 (F-05 · UX-19).

        ★ 우리 스키마로 내보내지 않는다. 상급기관·SDN·에스비 App 이 각자 파싱하면
          **우리가 바뀔 때마다 셋이 깨진다.**

        `signing_key_ref` 는 서명키의 **이름**이다 — 값이 아니다. 값은 환경에만 있고
        (D-204), 이름을 못 풀면 **등록 단계에서 거절한다**: 등록은 됐는데 보낼 수 없는
        구독은 「등록했으니 오겠지」라고 믿는 상대를 만든다.

        거절을 4xx 로 나눈다: 403 요청자 없음(시스템 스코프) · 422 값이 계약 밖
        (평문 http · 내부망 주소 · 모르는 서명키 이름 · 구독 상한).
        """
        from common.tenant_scope import SystemScopeCannotRead
        from common.webhook_outbox import WebhookSubscriptionError

        types = tuple(t.strip() for t in (event_types or "").split(",") if t.strip())
        try:
            sub = services.register_webhook_subscription(
                scope=_scope(request), endpoint_url=endpoint_url,
                signing_key_ref=signing_key_ref, event_types=types,
                min_severity=min_severity, payload_format=payload_format)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except WebhookSubscriptionError as exc:
            raise HttpError(422, str(exc))
        return _subscription_payload(sub)

    @route.get("/webhook-subscriptions", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-19 구독 목록 — 남의 테넌트 수신 주소가 보이면 안 된다")
    def list_webhook_subscriptions(self, request):
        """내 테넌트의 구독 전부. **서명키 값은 나가지 않는다** — 이름만 나간다."""
        from common.tenant_scope import SystemScopeCannotRead

        try:
            rows = services.webhook_subscriptions(scope=_scope(request))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        return {"total": len(rows),
                "subscriptions": [_subscription_payload(r) for r in rows]}

    @route.delete("/webhook-subscriptions/{int:subscription_id}",
                  auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-19 구독 해지 — 남의 구독을 끌 수 없다 (쓰기 IDOR). "
                          "끄면 그 기관의 경보가 조용히 멈춘다")
    def delete_webhook_subscription(self, request, subscription_id: int):
        """구독을 끈다. **행을 지우지 않는다** — 무엇을 받았는지가 함께 사라진다.

        404 는 **남의 구독**일 때도 난다. 403 을 내면 「그 번호는 있는데 네 것이
        아니다」가 새고, 존재 여부가 새는 것도 누출이다(`assert_scoped` 규약).
        """
        from common.tenant_scope import SystemScopeCannotRead
        from common.webhook_outbox import WebhookSubscriptionError

        try:
            sub = services.revoke_webhook_subscription(
                scope=_scope(request), subscription_id=subscription_id)
        except Http404:
            raise HttpError(404, "그런 구독이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except WebhookSubscriptionError as exc:
            raise HttpError(422, str(exc))
        return _subscription_payload(sub)

    @route.get("/deliveries", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-10 발송 이력 — 수신자 주소가 새면 안 된다")
    def deliveries(self, request, event_id: int | None = None,
                   since: datetime | None = None, until: datetime | None = None,
                   succeeded: bool | None = None, mine: bool = False,
                   limit: int = 100, offset: int = 0):
        """FR-10-2 — 대상·시각·채널·성공여부가 남는가.

        ★ `mine=true` 는 **「내게 온 것」**이다 (차선 D · 2026-09-04). 사번을 받지 않는다 —
          받으면 남의 사번으로 남의 수신 이력을 물을 수 있고, 이 라우트가 막으려는 것이
          바로 그것이다. **진입면은 늘지 않는다**: method·path 가 그대로다.
        """
        rows = services.delivery_history(
            scope=_scope(request), event_id=event_id, since=since, until=until,
            succeeded=succeeded, mine=mine, limit=limit, offset=offset)
        return {"total": len(rows), "deliveries": [
            {"delivery_id": r.delivery_id, "event_id": r.event_id,
             "recipient_id": r.recipient_id, "channel": r.channel,
             "succeeded": r.succeeded, "failure_reason": r.failure_reason,
             "sent_at": r.sent_at}
            for r in rows]}

    # ── 스냅샷 바이트 (P-25 · 2026-09-24) ────────────────────────────────
    #
    # ★ 판정: **무계정 링크를 만들지 않는다.** 서명 URL 한 줄이면 이 라우트는 필요 없지만,
    #   그 링크는 계정 없이 열리고 한 번 새면 회수할 수 없다(불변 제약).
    #   그래서 바이트는 **우리 라우트로만** 나가고, 그 문은 인증과 테넌트를 본다.
    #
    # ★ 이것은 영상이 아니다. 정지 이미지 1장이고(DA-01 FR-01-3) 화면이 이미 그리고 있다.
    #   계약 11조가 막는 것은 원본 영상이며, 그 금지는 아래 구간 라우트가 그대로 진다.
    #
    # ★ 저장은 못 막는다 — 브라우저에 뜬 그림은 누구나 저장한다.
    #   **대신 출처를 남긴다**: 테넌트명과 열람 시각을 소인으로 찍는다.
    #   소인을 못 찍으면 **내보내지 않는다**(500) — 소인 없는 바이트가 나가면
    #   이 라우트가 준 것은 편의뿐이고 남긴 것은 없다.
    #
    # ★ 다운로드 헤더를 달지 않는다. `inline` 은 「화면에 그리라」이고
    #   `attachment` 는 「파일로 받으라」다 — 후자는 반출의 모양이다.
    @route.get("/events/{int:event_id}/snapshot", auth=JwtOrInboundKey())
    @tenant_scoped(reason="스냅샷 바이트 — 남의 이벤트 프레임이 나가면 격리 실패다")
    def event_snapshot(self, request, event_id: int):
        """이벤트 스냅샷 1장. **소인이 찍힌 JPEG.**

        상태 넷을 다르게 낸다 — 뭉치면 운영자가 어디를 고칠지 모른다:
            401 인증 없음 · 404 없는/남의 이벤트, 또는 프레임 없음 ·
            503 저장소 연결 안 됨 · 500 소인 실패(우리 결함)
        """
        try:
            jpeg = services.event_snapshot(scope=_scope(request), event_id=event_id)
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 이벤트가 없습니다.")
        except services.SnapshotUnavailable as exc:
            status = {"missing": 404, "storage": 503, "stamp": 500}.get(exc.kind, 500)
            raise HttpError(status, exc.reason)

        response = HttpResponse(jpeg, content_type="image/jpeg")
        # `inline` — 화면에 그리라는 뜻이다. 파일명을 주지 않는다(받아 두라는 신호다).
        response["Content-Disposition"] = "inline"
        # 캐시 금지 (P-19). 미들웨어의 `dsm/` 우회와 **두 겹**이다 — 한 겹이 지워져도
        # 다른 한 겹이 남는다. 남의 소인이 찍힌 그림이 중간 캐시에 남으면 안 된다.
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    # ── F-11 상황 보고서 ─────────────────────────────────────────────────
    @route.get("/reports/templates", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-11 템플릿 목록 — 남의 테넌트 템플릿이 보이면 안 된다")
    def report_templates(self, request):
        # ★ [D-410 · 2026-09-19] `renderer` 를 읽어 **AttributeError → 500** 이었다.
        #   `TemplateView`(K4 공개 면)에 그런 칸은 **한 번도 없었다** — App 이 없는
        #   칸을 지어내 읽고 있었고, 이 라우트는 부르는 즉시 죽었다.
        #   ★ 왜 여태 안 보였나: 단위 시험은 `services.report_templates` 를 부르고
        #     **그 반환값을 이 자리에서 다시 읽지 않는다.** 화면도 이 라우트를 안 부른다.
        #     함수는 초록이고 문은 죽어 있었다 — 착시 ⑨ 의 두 번째 실사례다.
        #   내는 칸은 `TemplateView` 가 **실제로 가진 것**뿐이다. 지어내지 않는다.
        rows = services.report_templates(scope=_scope(request))
        return {"total": len(rows), "templates": [
            {"template_id": t.template_id, "name": t.name,
             "is_default": t.is_default, "is_enabled": t.is_enabled,
             "usage_count": t.usage_count} for t in rows]}

    @route.get("/reports/{int:template_id}.pdf", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-11 보고서 — 남의 이벤트가 보고서에 실리면 안 된다")
    def report_pdf(self, request, template_id: int, event_id: int | None = None,
                   mission_id: int | None = None):
        """AC-11 — 템플릿 치환 PDF.

        ★ 불완전한 컨텍스트로 찍지 않는다. 출처가 실패했으면 K4 가 예외를 올리고,
          여기서는 **409** 로 번역한다 — 서버 결함(500)이 아니라 **지금 찍을 수 없는
          상태**이기 때문이다. 200 으로 빈 PDF 를 내보내지 않는다 (D-284).
        """
        from kernels.k4_report import InvalidReportInput, RenderFailed

        try:
            pdf = services.build_report(scope=_scope(request), template_id=template_id,
                                        event_id=event_id, mission_id=mission_id)
        except Http404:
            raise HttpError(404, "그런 템플릿이 없습니다.")
        except InvalidReportInput as exc:
            raise HttpError(400, str(exc))
        except RenderFailed as exc:
            raise HttpError(409, f"지금은 보고서를 찍을 수 없습니다 — {exc}")
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="guardianx-report-{template_id}.pdf"')
        return response

    # ── UX-30 사건 보고서 1쪽 (P-125 · 2026-09-10 · 차선 B) ────────────────
    #
    # ★ **경로의 숫자가 사건 id 다.** 위 `reports/{template_id}.pdf` 의 숫자는 저장소
    #   템플릿 표의 행 번호이고, 그 표의 19행은 전부 택배 운송장이다 — 그래서
    #   `reports/7.pdf` 는 「배송 완료 보고서」를 냈고 `?event_id=` 를 붙여도 바이트가
    #   **한 글자도 안 바뀌었다**(그 서식에 `{{ events }}` 가 없어 꽂을 자리가 없다).
    #   이 라우트는 서식을 요청이 못 고른다. 사건 하나 → 1쪽 서식 하나다.
    #
    # ★ 화면이 부를 주소는 **이것 하나**다:
    #       GET /api/dsm/events/{event_id}/report.pdf
    @route.get("/events/{int:event_id}/report.pdf", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-30 사건 보고서 — 남의 사건이 종이로 나가면 IDOR 이다")
    def event_report_pdf(self, request, event_id: int):
        """AC UX-30 — 사건 1건의 **1쪽 PDF**. 택배 칸 0개.

        상태를 뭉치지 않는다 — 뭉치면 운영자가 어디를 고칠지 모른다:
            401 인증 없음 · 404 없는/남의 사건 ·
            409 사건은 있는데 지금 찍을 수 없다(출처 실패·렌더 실패·발생 시각 없음)

        ★ `attachment` 다. 스냅샷(`inline`)과 반대인 이유: 이 문서는 **받아서 보관하고
          결재에 올리는 종이**다 — 화면에 띄우고 마는 그림이 아니다.
        """
        try:
            pdf = services.incident_report(scope=_scope(request), event_id=event_id)
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 사건이 없습니다.")
        except (IncidentReportUnavailable, SettingNotAvailable) as exc:
            raise HttpError(409, f"지금은 보고서를 만들 수 없습니다 — {exc}")

        response = HttpResponse(pdf, content_type="application/pdf")
        # ★ 파일 이름을 두 벌로 낸다. `filename*` 이 없으면 한글 이름이 깨지고,
        #   `filename` 만 없으면 옛 브라우저가 이름을 못 읽는다.
        response["Content-Disposition"] = (
            f'attachment; filename="guardianx-incident-{event_id}.pdf"; '
            f"filename*=UTF-8''guardianx-%EC%82%AC%EA%B1%B4%EB%B3%B4%EA%B3%A0%EC%84%9C"
            f"-{event_id}.pdf")
        # 보고서는 사람마다 다른 종이다 — 중간 캐시에 남기지 않는다 (P-19 스냅샷과 같은 규약).
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    # ── F-09 영상 재생 — 계약 11조(원본 영상 무반출)가 여기서 걸린다 (D-306) ──
    #
    # ★ 이 두 라우트가 이번 턴에서 가장 위험한 자리다. 영상은 우리 산출물 중 반출 위험이
    #   가장 크고, 계약 11조는 그것을 정면으로 금지한다. 규약 넷을 **시험으로** 걸었고
    #   (backend/tests/test_clip_playback.py), 넷 중 하나라도 없으면 라우트를 내지 않는다.
    #
    #     ① 테넌트 범위 — 남의 event_id 는 404. 403 이 아니다(존재도 알리지 않는다 · D-269)
    #     ② 만료 서명 URL — 무기한 링크 금지
    #     ③ 구간 한정 — 구간이 서명에 묶여 있어 **다른 구간을 요구할 수조차 없다**
    #     ④ 다운로드 아님 — 원본 전체를 주는 경로가 **없다**(부작위 시험이 잰다 · D-300)
    @route.get("/events/{int:event_id}/clip", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-09 영상 구간 참조 — 남의 이벤트 영상에 닿으면 계약 11조 위반이다")
    def event_clip(self, request, event_id: int):
        """AC-09 — 이벤트 클릭 → **어디를 보라**.

        돌려주는 것은 구간에 묶인 만료 티켓이고, **객체를 통째로 받을 수 있는 URL 이
        아니다.** 프리사인드 URL 을 내면 요청한 30초를 주려다 두 시간짜리 원본을 준다.
        """
        from stream_monitors.services import clips

        try:
            ticket = clips.issue_ticket(scope=_scope(request), event_id=event_id)
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 이벤트가 없습니다.")
        return {
            "event_id": ticket.event_id,
            "start_offset": ticket.start_offset,
            "duration": ticket.duration,
            "expires_at": ticket.expires_at.isoformat(),
            "token": ticket.token,
            # ★ 지금 바이트를 받을 수 있는가. 거짓이면 **사유가 함께 나간다** —
            #   조용히 빈 응답을 주면 화면은 "영상이 없다" 로 읽는다 (D-284 · D-290).
            "playable": ticket.playable,
            "reason": ticket.reason,
        }

    @route.get("/events/{int:event_id}/clip/stream", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-09 영상 구간 전송 — 구간 밖 바이트가 나가면 계약 11조 위반이다")
    def event_clip_stream(self, request, event_id: int, token: str,
                          start_offset: float, duration: float):
        """구간의 바이트. **지금은 아무 바이트도 나가지 않는다** (CLIP_EXTRACTION_READY=False).

        티켓을 **먼저** 검증하고 그다음 잠금에서 멈춘다. 순서가 반대면 "티켓이 틀렸다" 와
        "아직 못 준다" 가 같은 응답이 되고, 잠금이 풀린 날 검증이 도는지 아무도 모른다.
        """
        from stream_monitors.services import clips

        try:
            clip_ticket = clips.issue_ticket(scope=_scope(request), event_id=event_id)
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 이벤트가 없습니다.")
        try:
            clips.stream_window(
                token=token, event_id=event_id, object_key=clip_ticket.object_key,
                start_offset=start_offset, duration=duration)
        except Http404 as exc:
            raise HttpError(404, str(exc))
        except NotImplementedError as exc:
            # 501 — **아직 구현하지 않았다.** 404(없는 주소)도 500(결함)도 아니다.
            raise HttpError(501, str(exc))
        raise HttpError(500, "도달할 수 없는 자리")   # stream_window 는 언제나 멈춘다

    # ── F-12 관리자 설정 ─────────────────────────────────────────────────
    #
    # ⚠ **이 표지를 지우지 마라.** `test_clip_playback.test_rule4_no_full_download_...`
    #   이 `api.py` 원문을 「F-09 영상 재생」…「F-12 관리자 설정」 사이로 잘라 내
    #   계약 11조(원본 통째 다운로드 금지)를 검사한다. 표지가 없으면 그 시험이
    #   `ValueError: substring not found` 로 멈춘다 — 실제로 2026-09-19 에 그랬다.
    #   ★ 그때 고칠 것은 **시험이 아니라 표지**다(D-327). 표지는 영상 구간이
    #     끝나는 자리에 선다.
    @route.post("/settings/thresholds", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 임계값 쓰기 — 남의 테넌트 임계값을 못 바꾼다")
    def set_threshold(self, request, key: str, value: float, reason: str,
                      scope_level: str = "global", scope_ref: int | None = None):
        """F-12 「임계값」 · F-02 「**지점별** 기준선 설정」 — 값을 바꾸는 유일한 문.

        **사유 없이는 못 바꾼다.** 무엇에서 무엇으로는 표가 알지만 **왜** 는
        여기서만 들어온다 — 그 칸이 비면 400 이다.

        계약이 못박은 값(F-04 5분 · F-10 30초)은 **409** 다. 400(잘못된 요청)이 아니라
        409(상태 충돌)인 이유: 요청이 틀린 게 아니라 **그 값이 계약이라서** 안 되는 것이다.
        """
        from kernels.k5_trust import (
            ScopeNotAvailable,
            ThresholdIsContractFixed,
            ThresholdNotDefined,
        )

        try:
            return services.set_threshold_value(
                scope=_scope(request), key=key, value=value, reason=reason,
                scope_level=scope_level, scope_ref=scope_ref)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except ThresholdIsContractFixed as exc:
            raise HttpError(409, str(exc))
        except (ThresholdNotDefined, ScopeNotAvailable, ValueError) as exc:
            raise HttpError(400, str(exc))

    @route.post("/settings/zones", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 구역 쓰기 — 남의 테넌트 위험구역을 못 만든다")
    def save_zone(self, request, name: str, kind: str, zone_id: int | None = None,
                  geometry: dict | None = None, camera_ids: list[int] | None = None,
                  is_active: bool = True):
        """F-12 「구역」 · F-03 「지정 위험구역(폴리곤)」 — 구역을 **지정하는 유일한 문**.

        오류를 셋으로 가른다. 뭉치면 화면 앞의 사람이 무엇을 해야 할지 모른다:

            403  권한이 없다        — 감사 번호와 함께 나간다
            400  도형이 잘못됐다    — `InvalidPolygon`. **다시 그려야 한다**
            403  남의 카메라를 붙였다 — 조용히 빼지 않는다(D-284)

        ★ 남의 `zone_id` 는 **404** 다 — 403 은 그 구역이 있다는 사실을 알린다(D-269).
        """
        from stream_monitors.services.zones import InvalidPolygon

        try:
            return services.save_zone_setting(
                scope=_scope(request), zone_id=zone_id, name=name, kind=kind,
                geometry=geometry, camera_ids=camera_ids, is_active=is_active)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 구역이 없습니다.")
        except PermissionDenied as exc:
            # L3 이 낸 거부. **이 저장소가 쓰는 거부의 형태**이고,
            # `test_tenant_isolation._is_refusal` 이 아는 형태이기도 하다 —
            # 새 예외 형을 만들면 격리 시험이 그것을 「부서진 것」으로 읽는다.
            raise HttpError(403, str(exc))
        except InvalidPolygon as exc:
            # 400 — **요청이 틀렸다.** 구역을 다시 그려야 한다. 500(결함)이 아니다.
            raise HttpError(400, str(exc))
        except ValueError as exc:
            raise HttpError(400, str(exc))

    # ── F-05 「API Key 발급·폐기」 · F-12 「API키」 ─────────────────────────
    #
    # ★ 이 셋이 계약 F-05 의 마지막 절을 갚는 자리다 (D-367). 세 번 미뤄졌던 절이고,
    #   미룬 이유가 세 번 다 달랐다 — 방향 오판(D-337) · 범위 문제(D-335) · 그리고
    #   남은 하나가 이것, **발급·폐기의 면**이다.
    #
    # ★ `inbound_key=True` 를 여기에 **주지 않는다.** 들어오는 키로 들어오는 키를
    #   발급받을 수 있으면 키 하나가 영원히 자기를 갱신한다 — 폐기가 폐기가 아니게 된다.
    #   이 셋은 사람(JWT)만 부른다.
    @route.post("/settings/api-keys", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-05 키 발급 — 남의 테넌트 이름으로 키를 만들 수 없다")
    def issue_api_key(self, request, name: str, expires_days: int | None = None,
                      scopes: str = ""):
        """F-05 「API Key 발급」. **`secret` 이 사람에게 보이는 유일한 응답이다.**

        저장소는 원문을 갖지 않는다(sha256 해시만). 이 응답을 놓치면 되찾을 수 없고
        회전만 가능하다 — 되찾을 수 있다면 그것은 어딘가에 저장돼 있다는 뜻이다.

        ★ [턴 U · 차선 U56 · API-03] `scopes` — **이 키가 어디까지 가는가.**
          쉼표 문자열 또는 JSON 배열 문자열이고, 안 주면 기본은 `["events:read"]`
          **하나**다. 기본을 전부로 두면 D-335 가 잡은 「범위 없이 이미 열어 두었다」가
          그대로 돌아온다. 모르는 이름은 **422** 다 — 조용히 버리면 발급자는 준 줄
          알고 상대는 못 쓴다. 이름의 정본은 `kernels/k5_trust/key_scopes.py` 하나다.
        """
        from django.db import transaction

        from kernels.k5_trust import (DEFAULT_SCOPES, InvalidScopeName,
                                      set_key_scopes)

        scope = _scope(request)
        # ★ [턴 U 병합] 이름 검사를 **쓰는 자리 하나**로 모았다. 전에는 `normalize_scopes`
        #   를 발급 전에 따로 불렀는데, 그것은 순수 계산이라 커널 공개 면에 둘 수 없다
        #   (D-281 1차 — 공개 면은 `*, scope` 를 받아야 하고, 쓰지도 않을 scope 를 다는
        #   것은 거짓 신호다). 그래서 검사는 `set_key_scopes` 안에서만 일어난다.
        # ★ 그 대신 **발급과 범위를 한 트랜잭션으로 묶는다** — 422 가 나면 키도 함께
        #   사라진다. 묶지 않으면 「범위 없는 키」가 남고, 그 키는 아무도 모르는 채
        #   살아 있다(그 위험이 옛 순서가 막던 바로 그것이다). 되돌아가는 것에는
        #   허가 감사 한 줄도 포함된다 — 일어나지 않은 발급의 허가는 기록이 아니다.
        with transaction.atomic():
            try:
                issued = services.issue_inbound_key(
                    scope=scope, name=name, expires_days=expires_days)
            except PermissionDeniedForSetting as exc:
                raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
            except PermissionDenied as exc:
                raise HttpError(403, str(exc))
            except ValueError as exc:
                raise HttpError(400, str(exc))
            try:
                view = set_key_scopes(scope=scope, key_id=issued["key_id"],
                                      scopes=(scopes or "").strip() or DEFAULT_SCOPES)
            except InvalidScopeName as exc:
                raise HttpError(422, str(exc))
        return {**issued, "scopes": list(view.scopes or [])}

    @route.delete("/settings/api-keys/{int:key_id}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-05 키 폐기 — 남의 테넌트 키를 끌 수 없다")
    def revoke_api_key(self, request, key_id: int):
        """F-05 「API Key 폐기」. 행은 남고 **꺼진다.**

        남의 키는 **404** 다 — 403 은 "있는데 못 만진다" 를 알려 주고, 그것만으로
        남의 테넌트에 그 id 가 있다는 사실이 샌다 (D-269).
        """
        from kernels.k5_trust import InboundKeyNotFound

        try:
            return services.revoke_inbound_key(scope=_scope(request), key_id=key_id)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except InboundKeyNotFound:
            raise HttpError(404, "그런 키가 없습니다.")
        except PermissionDenied as exc:
            raise HttpError(403, str(exc))

    @route.post("/settings/api-keys/{int:key_id}/rotate", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-05 키 회전 — 남의 테넌트 키를 돌릴 수 없다")
    def rotate_api_key(self, request, key_id: int):
        """회전 — 폐기와 발급을 **한 번에.** 둘로 나누면 한쪽을 잊는다.

        옛 키는 지워지지 않고 `rotated` 로 남는다 — "폐기됐다" 와 "새것으로 바뀌었다"
        는 다른 사실이고, 뒤엣것은 **후속 키가 있다**는 뜻이다.
        """
        from kernels.k5_trust import InboundKeyNotFound

        try:
            return services.rotate_inbound_key(scope=_scope(request), key_id=key_id)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except InboundKeyNotFound:
            raise HttpError(404, "그런 키가 없습니다.")
        except PermissionDenied as exc:
            raise HttpError(403, str(exc))

    @route.post("/settings/grade-rules", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 등급규칙 쓰기 — 남의 테넌트 등급규칙을 못 바꾼다")
    def set_grade_rule(self, request, event_type: str, severity: str, reason: str):
        """F-12 「등급규칙」 · F-04 「JSON **무재기동** 반영」 — 규칙을 바꾸는 유일한 문.

        **사유 없이는 못 바꾼다.** 무엇에서 무엇으로는 표가 알지만 **왜** 는
        여기서만 들어온다 — 그 칸이 비면 400 이다.

        ★ 응답의 `lowered` 를 화면이 반드시 보여 줘야 한다. 참이면 그 이벤트는
          **조용해진 것**이고, 경보가 안 오는 것은 「아무 일도 없음」으로 보인다.
        """
        from kernels.k5_trust import GradeRuleNotDefined, SeverityNotInContract

        try:
            return services.set_grade_rule_value(
                scope=_scope(request), event_type=event_type,
                severity=severity, reason=reason)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except (GradeRuleNotDefined, SeverityNotInContract, ValueError) as exc:
            raise HttpError(400, str(exc))

    # ── F-12 설정 **조회** ────────────────────────────────────────────────
    #
    # ★ [D-410 · 2026-09-19] **이 자리는 맨 뒤여야 한다.** 위로 올리면 그 순간
    #   쓰기 라우트 넷이 다시 HTTP 로 도달 불가가 된다 — 그것이 며칠을 숨어 있었다.
    #
    #   django-ninja 는 경로 문자열마다 `PathView` 를 하나 두고, Django 는 **먼저
    #   등록된 패턴**에서 멈춘다. `settings/<str:domain>` 은 `settings/thresholds` ·
    #   `settings/zones` · `settings/api-keys` · `settings/grade-rules` 를 전부
    #   삼킨다. 삼킨 PathView 에는 GET 밖에 없으므로 POST 는 **405 (Allow: GET)** 였다.
    #
    #   ★★ 왜 여태 안 보였나 — **두 눈의 사각이 정확히 겹쳤다**(착시 ⑨ 배선형):
    #       · 단위 시험은 **서비스 함수**를 부른다 → 초록
    #       · route-alive 는 **화면이 부른 GET** 만 때린다 → 쓰기 면을 안 본다
    #     「구현되었다」는 참이었고 「외부 App 이 쓸 수 있다」가 거짓이었다. U6 은
    #     HTTP 로만 들어온다 — U6 에게 그 넷은 **없는 기능**이었다.
    #     세 번째 눈을 세웠다: `scripts/verify_contract_route_reach.py`.
    #
    #   ⚠ 순서만으로는 반이다. `thresholds` 와 `zones` 는 **설정 영역 이름이면서
    #     동시에 쓰기 경로**다 — 리터럴을 먼저 등록하면 이번엔 그 둘의 GET 이
    #     405 가 된다. 그래서 아래 둘을 **같은 리터럴 경로에** 붙였다: 한 경로 =
    #     한 PathView 이므로 GET·POST 가 한 문에 함께 선다.
    #     진입면이 넓어진 것이 아니다 — **같은 문이 제 이름으로 다시 걸린 것**이다
    #     (같은 핸들러 · 같은 문지기 · 같은 응답). `EVENT_ENTRY_SURFACE` 에
    #     그 사유와 함께 두 줄을 적었다.
    def _setting_overview(self, request, domain: str):
        """세 라우트가 **같은 몸**을 쓴다. 복사하면 한쪽만 고쳐지는 날이 온다."""
        try:
            return services.setting_overview(scope=_scope(request), domain=domain)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except SettingNotAvailable as exc:
            # 501 — 서버가 그 기능을 **아직 구현하지 않았다.** 404(없는 주소)도
            # 400(잘못된 요청)도 아니다. 셋을 뭉치면 "언젠가 생길 것" 과
            # "영영 없는 것" 이 클라이언트에서 구별되지 않는다.
            raise HttpError(501, str(exc))

    @route.get("/settings/thresholds", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 설정 — 남의 테넌트 설정이 보이면 안 된다")
    def settings_thresholds(self, request):
        """`GET /settings/{domain}` 의 `domain=thresholds` **바로 그것**이다.

        쓰기(POST)와 같은 경로 문자열이라 같은 `PathView` 에 실린다 — 그래야
        POST 가 산다. 응답도 문지기도 위 `{domain}` 과 글자까지 같다.
        """
        return self._setting_overview(request, "thresholds")

    @route.get("/settings/zones", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 설정 — 남의 테넌트 설정이 보이면 안 된다")
    def settings_zones(self, request):
        """`GET /settings/{domain}` 의 `domain=zones` **바로 그것**이다."""
        return self._setting_overview(request, "zones")

    # ═══════════════════════════════════════════════════════════════════════
    # LAW-02 · LAW-03 — 서식의 「제품 자동」 칸 (턴 C · 차선 E · CPO 문서 배선)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # ⚠ **선언 순서가 곧 라우팅이다** — 이 둘은 바로 아래 `/settings/{domain}` 보다
    #   **위**에 있어야 한다. 아래로 내리면 `domain="notice-draft"` 로 삼켜지고,
    #   그 순간 이 라우트는 404 도 아니고 501("설정 영역이 아니다")로 답한다 —
    #   **있는데 없는 것처럼 보이는** 가장 나쁜 모양이다 (D-410).
    # ⚠ 문안은 세종(CPO)의 것이고 법률대리인이 대조한다. 여기서 하는 일은 **배선**뿐이고,
    #   그래서 대장 상태는 「구현」이 아니라 **미측정**이다.

    @route.get("/settings/notice-draft", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-02 고지 초안 — 남의 테넌트 카메라 수가 보이면 안 된다")
    def law02_notice_draft(self, request):
        """LAW-02 안내판·운영방침의 **「제품 자동」 칸**을 설정값으로 채운다.

        못 채운 칸은 **비운 채로 `확인`** 이라고 적는다. 기본값(예: 「30일」)으로
        메우면 그 순간 안내판이 거짓말을 시작하고, 게시된 고지는 되돌릴 수 없다.
        """
        from apps.dsm.legal_notice import notice_draft

        return notice_draft(scope=_scope(request))

    @route.get("/settings/privacy-collection", auth=JwtOrInboundKey())
    @tenant_scoped(reason="LAW-03 수집 항목 표 — 설정 면과 같은 문지기를 쓴다")
    def law03_collection_table(self, request):
        """LAW-03 §1 수집 항목 표를 **모델에서 만든다.**

        손으로 적은 표는 모델이 바뀌어도 그대로 남는다 — 그 표는 「이것만 모읍니다」
        라고 말하면서 실제로는 다른 것을 모으는 문서가 된다. 그래서 항목마다 어느
        모델의 어느 칸인지를 못박고, 갈린 자리를 `drifted` 로 낸다.
        """
        from apps.dsm.legal_notice import collection_table

        return collection_table()

    @route.get("/settings/{domain}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 설정 — 남의 테넌트 설정이 보이면 안 된다")
    def settings_domain(self, request, domain: str):
        """AC-12 — 무권한 차단 + **성공·실패 모두 감사로그**.

        `403` 응답의 `audit_id` 는 **차단이 기록에 남았다는 증거**다.
        차단만 하고 안 남기면 "시도가 없었다" 와 "시도가 막혔다" 가 같은 상태가 된다.

        ⚠ **맨 마지막에 등록된다** — 위 D-410 주석을 읽어라. 이 자리를 올리면
          쓰기 라우트 넷이 조용히 405 로 되돌아간다.
        """
        return self._setting_overview(request, domain)

    # ═══════════════════════════════════════════════════════════════════════
    # UX-17 훈련 모드 · UX-18 벌크 등록 (차선 C · 2026-09-24)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # ★ **맨 뒤에 선다.** 바로 위 `/settings/{domain}` 은 `settings/` 로 시작하는
    #   것만 삼키므로 이 넷을 가리지 않는다. 그래도 뒤에 두는 이유는 D-410 이 남긴
    #   교훈이다 — 변수 경로 위로 리터럴을 옮기는 순간 다른 메서드가 405 로 죽는다.
    #   ⚠ 404 를 만나면 **PROPFIND 로 한 번 더 두드려라.** 라우트가 있으면 405 이고
    #     없으면 404 다 — 그 둘을 눈으로 못 가르면 「기능이 없다」와 「길이 다르다」가
    #     같은 그림이 된다.

    @route.get("/drill", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-17 훈련 상태 — 남의 테넌트가 훈련 중인지도 남의 정보다")
    def drill_state(self, request):
        """지금 훈련 모드인가 (UX-17). **읽기 전용.**

        `since`·`by`·`reason` 을 함께 낸다 — 「켜져 있다」만으로는 사후에
        「그 시각의 미발송이 훈련이었나 장애였나」를 가를 수 없다.
        """
        return services.drill_state(scope=_scope(request))

    @route.post("/drill", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-17 훈련 스위치 — 남의 테넌트 알림을 끌 수 있으면 격리 실패다")
    def set_drill_mode(self, request, enabled: bool, reason: str):
        """훈련 모드를 켜거나 끈다 (UX-17). **끄는 스위치다.**

        ★ 켜면 그 테넌트의 알림이 사람에게 가지 않는다. 그래서 이 면은 다른 어떤
          쓰기보다 조용하게 사고를 만든다 — 남이 켜면 남의 **진짜** 경보가 로그로 흘러
          아무에게도 안 간다. 문지기는 `stream_monitors/services/drill.py` 안에 하나
          있고, P-8 탐침(`drill.set_drill_mode`)이 그 자리를 잰다.

        ★ **사유 필수.** 사유 없는 미발송은 장애와 구별되지 않는다 → 400.

        ⚠ **아직 채널이 안 바뀐다.** 스위치와 상태 판정은 여기까지 서 있고,
          실제 채널 우회는 `kernels/k2_notify/` 안에서 일어나야 한다(발송 경로는
          하나다). 그 파일은 조율자의 것이고 이 차선은 만지지 않았다 —
          필요한 배선 한 자리를 보고서에 정확히 적었다.
        """
        try:
            return services.set_drill_mode(scope=_scope(request),
                                           enabled=bool(enabled), reason=reason)
        except ValueError as exc:
            # 400 — 요청이 틀렸다. 200 + {"success": false} 를 만들지 않는다(W0-18).
            raise HttpError(400, str(exc)) from exc
        except PermissionDenied as exc:
            raise HttpError(403, str(exc) or "훈련 모드를 바꿀 권한이 없습니다.") from exc

    @route.get("/drill/report", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-17 훈련 보고서 — 남의 테넌트 발송 현황이 나가면 격리 실패다")
    def drill_report(self, request):
        """훈련 종료 보고서 1장 (UX-17). **첫 줄이 「실채널 발송 N건」이다.**

        ★ 0 을 「없음」으로 적지 않는다 — **모수와 함께** 적는다(D-301). 창 안 발송
          전건이 몇이고 그중 실채널이 몇인지. 분모 없는 0 은 「발송 자체가 없었다」와
          구별되지 않고, 그러면 스위치가 안 걸린 채 아무 일도 없던 밤이 「훈련 성공」이 된다.
        """
        return services.drill_report(scope=_scope(request))

    @route.get("/cameras/address-gap", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-18 주소 배지 — 남의 테넌트 카메라 수가 섞이면 격리 실패다")
    def camera_address_gap(self, request):
        """「주소 없는 카메라 N대」 배지 (UX-18). **분모와 함께** 낸다.

        「39대」만 보면 그것이 40 중 39인지 400 중 39인지 모른다 — 앞은 거의 전부이고
        뒤는 10%다. 두 사실에 필요한 행동이 다르다.
        """
        return services.camera_address_gap(scope=_scope(request))

    @route.post("/cameras/import", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-18 벌크 등록 — 남의 테넌트에 카메라를 무더기로 심을 수 없다")
    def camera_import(self, request, csv_text: str, dry_run: bool = True):
        """CSV 일괄 등록 (UX-18). ★ **dry-run 이 기본값이다** (D-209).

        왜 기본이 dry-run 인가: 한 건짜리 등록은 잘못 눌러도 한 건이 틀린다.
        100행 일괄은 **한 번의 실수가 100대의 이름·주소를 덮어쓰고**, 덮어쓴 뒤에는
        원래 값이 어디에도 없다. 그래서 `dry_run=false` 를 **명시해야만** 쓴다 —
        기본값이 쓰기인 면은 언젠가 반드시 실수로 눌린다.

        ★ 표와 집행이 **같은 판정식**을 쓴다(`bulk_register._plan`). 두 벌이면 표에
          없던 일이 일어나고, 그러면 dry-run 은 보여 주기일 뿐 약속이 아니게 된다.

        ⚠ ONVIF 는 이 저장소에 **없다** [실측 2026-09-24 · `grep -ril onvif` 0건].
          없는 프로토콜 위에 화면을 얹지 않는다(P-15). CSV 한 갈래만 연다.
        """
        try:
            if dry_run:
                return services.plan_camera_import(scope=_scope(request),
                                                   csv_text=csv_text)
            return services.apply_camera_import(scope=_scope(request),
                                                csv_text=csv_text)
        except PermissionDenied as exc:
            raise HttpError(403, str(exc) or "카메라를 등록할 권한이 없습니다.") from exc

    # ═══════════════════════════════════════════════════════════════════════
    # UX-23 카메라 격자 (차선 C2 · 2026-09-05)
    # ═══════════════════════════════════════════════════════════════════════
    # ★ [UX-24a · 턴 F · 차선 S] 월 표시 토큰이 닿는 **두 문 중 둘째**.
    #   `useCameraPulse.ts` 가 부르는 자리다. 읽기뿐이고, 아무것도 만들지 않는다.
    # ── 들어오는 키 (턴 W · 차선 U3 · 조율자 요청 — 두 턴째 떠 있던 자리) ─────
    #
    # **연다.** 사유는 「상속했으니 열렸겠거니」가 아니라 **범위가 이미 이 경로를
    # 가리키고 있었다**는 것이다. `JwtOrWallToken` 이 `JwtOrInboundKey` 를 상속해도
    # `inbound_key` 는 기본 거짓이고(둘 다 **기본값이 거절**이다 · D-335 ③⑤ ·
    # D-300 부작위), 상속은 선언을 대신하지 않는다 — 그 규약은 옳으므로 안 바꾼다.
    # 바꾸는 것은 **이 한 라우트의 선언**뿐이다.
    #
    # ★★ 왜 여는가 — 안 열면 `pulse:read` 가 **거짓말이 된다** [실측 2026-09-19]:
    #       `kernels/k5_trust/key_scopes.py`
    #         · `SCOPE_PULSE_READ = "pulse:read"` 가 `ALLOWED_SCOPES` 에 있다 → 운영자가
    #           키에 **줄 수 있다**(발급 문이 422 를 안 낸다)
    #         · `PATH_SCOPES` 에 `("/api/dsm/cameras/pulse", SCOPE_PULSE_READ)` 가 있다
    #       그런데 이 라우트가 선언을 안 해 키는 **범위 판정에 닿기도 전에 401** 이었다.
    #       즉 「줄 수는 있는데 아무 데도 못 쓰는 범위」였다. 줄 수 있다고 적어 놓고
    #       쓰면 막는 것은, 없는 기능에 손잡이를 그린 것과 같다(D-284).
    #       ⇒ 여는 쪽이 **이미 내려진 판정을 집행하는 것**이고, 안 여는 쪽이 새 판정이다.
    #
    # ★ 여는 것이 **넓히는 것이 아니다** — 이것이 이 결정의 핵심이다:
    #     · 기본 범위는 `DEFAULT_SCOPES = ("events:read",)` 다. 이미 나간 키들은
    #       이 경로에서 그대로 **403** 이다(`_assert_request_key_scope`). 늘어나는 것은
    #       「운영자가 `pulse:read` 를 **일부러** 준 키」 하나뿐이다.
    #     · `@tenant_scoped` 는 그대로다 — 남의 테넌트 카메라는 여전히 안 보인다.
    #     · **읽기다.** 쓰기 메서드에는 `inbound_key=True` 를 줄 수조차 없다(생성 시 거부).
    #     · 평문이면 거절한다(`INBOUND_API_KEY_REQUIRE_HTTPS`) — 키가 평문으로 흐르면
    #       키가 아니다.
    # ★ 진입면은 **늘지 않는다**: method·path 가 그대로다. 늘어난 것은 **자격의 갈래**이고,
    #   그것을 보고에 크게 적는다.
    # ⚠ 이 문이 내는 것은 「어느 구역이 통째로 끊겼는가」다(아래 `tenant_scoped` 사유).
    #   그래서 `events:read` 와 **같은 범위로 뭉치지 않았다** — `pulse:read` 를 따로 둔
    #   그 판단이 옳고, 이 선언은 그 판단을 살릴 뿐이다.
    @route.get("/cameras/pulse", auth=JwtOrWallToken(
        wall_token=True,
        wall_reason="UX-24a 월 화면의 카메라 상태 칸 — 세션 없이 읽는다 (P-62)",
        inbound_key=True,
        reason="UX-23 카메라 맥박 읽기 — 범위 `pulse:read` 를 **일부러 받은** 키만. "
               "기본 범위(`events:read`)만 가진 키는 여기서 403 이다",
    ))
    @tenant_scoped(reason="UX-23 카메라 맥박 — 남의 테넌트 카메라의 생사가 나가면 "
                          "격리 실패다. 「어느 구역이 통째로 끊겼는가」는 재난 정보다")
    def camera_pulse(self, request):
        """카메라별 맥박 + 군집 두절 (UX-23 · OPS-15). **읽기 전용.**

        ★ 판정을 여기서 하지 않는다 — `stream_monitors/services/camera_pulse.py` 를
          부른다. 두 벌을 두면 화면의 「응답 없음」과 시스템 이벤트의 두절 판정이
          갈리고, 그 어긋남은 아무도 못 본다.

        ★ 아무것도 만들지 않는다(`create_events=False`). 화면을 열었다고 이벤트가
          생기면 **보는 행위가 보는 대상을 바꾼다.**

        ★ 세 값을 접지 않는다: 살아 있음 · 응답 없음 · 한 번도 안 옴.
          `alive` 와 `last_seen_at` 의 조합이 그 셋을 가른다(응답 모양은
          `docs/agent/evidence/UX-23/README.md` 에 적었다 — 다른 차선이 읽는다).
        """
        return services.camera_pulse(scope=_scope(request))
