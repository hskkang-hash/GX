"""테넌트(group) 격리 회귀 테스트 — W0-3.

이 파일은 **머지 게이트**다. 새 모델을 추가하면 MODELS 레지스트리에 등록해야 하고,
등록하지 않으면 `test_registry_covers_all_isolatable_models` 가 실패한다.

절대 금지 (AGENT_LOOP 절대금지 #4 / D-105):
    이 파일의 테스트를 skip·xfail·비활성화하지 말 것.
    테스트가 틀린 것 같으면 고치지 말고 멈추고 보고한다.

────────────────────────────────────────────────────────────────────────────
구조

  1) TenantIsolationRegistryTest   — 레지스트리가 실제 코드베이스를 덮는가
  2) TenantIsolationORMTest        — 매니저 수준 격리 (5시나리오 중 list/detail)
  3) TenantIsolationAPITest        — HTTP 수준 격리 (list/detail/update/delete/export)

────────────────────────────────────────────────────────────────────────────
⚠️ 이 코드베이스에는 BaseModelWithGroup 이 **두 개** 있다 (W0-3 실측)

  A. core.base.BaseModelWithGroup        ← dj-core 사내 패키지 (§0.4 금지구역)
       사용: orders, terminals, stream_monitors, surveillance, checklist_setting,
             delivery, partner, drone_communication  (8개 앱)
  B. common.base_model.BaseModelWithGroup ← 이 저장소
       사용: dashboard.Dashboard, dashboard.DashboardPanel  (2개 모델뿐)

  W0-2 가 지목한 performance_bypass_models 목록은 B 안에 있다.
  그런데 그 목록이 나열한 order/terminal/coreuser 등은 전부 A 를 쓴다.
  → B 의 목록을 고쳐도 그 모델들의 필터링은 바뀌지 않는다.
  이 테스트가 그 사실을 실증한다. 자세한 내용은 tickets.yaml W0-2 blocker 참조.
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable
from unittest import mock

from django.apps import apps
from django.db import models
from django.test import Client, TestCase

from tests.tenant_census import CENSUS


# ═══════════════════════════════════════════════════════════════════════════
# 레지스트리 — 새 모델을 추가하면 여기에 등록한다
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Route:
    """시나리오 하나가 부를 실제 라우트. `{pk}` 는 대상 레코드의 pk 로 치환된다.

    `body` 가 필요한 이유 (D-253 배선)
        수정 시나리오에 빈 본문(`{}`)을 보내면 **검증에서 422 로 튕겨** 소유권 판정에
        도달하지 못한다. 실제 공격자는 자기 테넌트의 유효한 데이터를 남의 레코드에
        보낸다 — 그래서 본문은 **tenant-A 가 만들 수 있는 유효한 값**으로 채운다.
        `form=True` 는 이 저장소의 몇몇 라우트가 `data: str = Form(...)` 를 받기 때문이다.
    """

    method: str
    path: str
    #: dict 또는 `Deps` 를 받아 dict 를 만드는 콜러블. None 이면 빈 본문.
    body: Any = None
    #: 참이면 multipart/form-data 로 보낸다 (`Form(...)` 라우트용).
    form: bool = False

    def for_pk(self, pk: Any) -> str:
        return self.path.replace("{pk}", str(pk))


@dataclass(frozen=True)
class Target:
    """격리 검증 대상 1건.

    ★ 2026-08-22 배선 정정 (D-253) — 단언은 무변경, **부르는 곳만** 고쳤다.
      이전 판은 `api_base` 하나로 다섯 시나리오의 경로를 조립했다
      (`f"{api_base}{pk}/"` + PATCH). 그 가정이 실측과 전부 달랐다:
        · 목록 경로 4개가 404 (`/api/terminals/` 는 라우트가 아니라 마운트 지점이다)
        · 상세 경로에는 **끝 슬래시가 없다** (`/api/terminals/terminals/{id}`)
        · **PATCH 는 이 저장소 전체에 1건뿐**이다. 수정은 PUT(또는 devices 는 POST),
          삭제는 대개 대량 경로(`delete/{ids}`)다 → 405 를 받고 있었다
      근거: `docs/agent/evidence/W0-14/openapi_routes.json` (21개 ninja API · 531 오퍼레이션)
    """

    label: str
    app_label: str
    model_name: str
    #: 목록 라우트. None 이면 목록 시나리오는 NO_ROUTE 로 명시 등록돼야 한다.
    list_path: str | None = None
    detail: Route | None = None
    update: Route | None = None
    delete: Route | None = None
    #: 내보내기 엔드포인트 (있으면 test_export 대상)
    export_path: str | None = None
    #: 레코드 1건을 만드는 팩토리. `Deps` 로 필수 FK 를 만들어 쓴다.
    factory: Callable[["Deps", int], dict[str, Any]] | None = None

    # ── D-272: 도달 가능성 3값 ──────────────────────────────────────────
    #: `direct_pk` · `via_parent` · `no_route`. **인구조사(tenant_census)와 같아야 한다** —
    #: 다르면 `test_reach_matches_census` 가 실패한다. 두 곳이 다른 말을 하면 어느 쪽도 못 믿는다.
    reach: str = "direct_pk"
    #: `via_parent` 일 때 부모 경로. `{pk}` 는 **부모의 pk** 로 치환된다.
    #: 자기 pk 경로가 없다고 안전한 것이 아니다 — 부모를 부르면 자식이 딸려 나온다.
    via_parent: Route | None = None
    #: 만들어진 자식에서 **부모의 pk** 를 꺼낸다. 없으면 `via_parent` 경로에 `{pk}` 가 없어야 한다.
    parent_pk: Callable[[Any], Any] | None = None
    #: URL 의 `{pk}` 자리에 넣을 **속성 이름**. 기본은 `pk` 다.
    #:
    #: ★ 모든 단건 경로가 pk 를 받는 것은 아니다 — `task_status` 는 업무 키(`task_id`)를 받는다.
    #:   pk 를 넣으면 없는 레코드를 조회하게 되고, 그때 나오는 200/404 는
    #:   **격리의 답이 아니라 배선의 답**이다. 첫 판이 그 200 을 누출로 보고했다.
    pk_attr: str = "pk"


#: W0-3 지시서가 지정한 9종 + W2-1 신설 1종.
#: `Handover` 라는 이름의 모델은 존재하지 않는다 — handover 앱의 실제 최상위 모델은
#: HandoverDocument 다. 지시서의 이름이 아니라 실재하는 모델로 등록한다.
MODELS: tuple[Target, ...] = (
    Target(
        "Order", "orders", "Order",
        list_path="/api/orders/order/",
        detail=Route("GET", "/api/orders/order/{pk}"),
        factory=lambda d, n: {
            "order_code": f"ISO-{n}", "recipient_name": f"iso{n}",
            "recipient_phone": "01000000000", "recipient_address": d.address(),
            # 상세 핸들러가 `order.status.code` 를 무조건 읽는다 (order_views.py:1291).
            # status 가 비면 판정 전에 500 이 된다 — 그것은 별 결함이고 여기서 다루지 않는다.
            "status": d.order_status(),
        },
    ),
    Target(
        "Terminal", "terminals", "Terminal",
        list_path="/api/terminals/terminals",
        detail=Route("GET", "/api/terminals/terminals/{pk}"),
        update=Route("PUT", "/api/terminals/terminals/{pk}", form=True,
                     body=lambda d: {"data": json.dumps({"name": "iso-updated"})}),
        delete=Route("DELETE", "/api/terminals/terminals/delete/{pk}"),
        factory=lambda d, n: {"name": f"iso-terminal-{n}"},
    ),
    Target(
        "StreamMonitor", "stream_monitors", "StreamMonitor", reach="direct_pk",
        list_path="/api/stream-monitors/stream-monitors",
        factory=lambda d, n: {
            "name": f"iso-monitor-{n}", "code": f"ISO-MON-{n}",
            "ip_source": "rtsp://iso.invalid/stream",
        },
    ),
    Target(
        "Dashboard", "dashboard", "Dashboard", reach="via_parent",
        list_path="/api/dashboard/dashboard/",
        factory=lambda d, n: {"name": f"iso-dash-{n}", "code": f"ISO-DASH-{n}"},
    ),
    Target(
        "Device", "devices", "Device",
        list_path="/api/devices/devices-management",
        detail=Route("GET", "/api/devices/devices-management/{pk}"),
        update=Route("POST", "/api/devices/devices-management/{pk}", form=True,
                     body=lambda d: {"data": json.dumps({"name": "iso-updated"})}),
        delete=Route("DELETE", "/api/devices/devices-management/delete/{pk}"),
        factory=lambda d, n: {"name": f"iso-device-{n}", "serial_number": f"ISO-SN-{n}"},
    ),
    Target(
        "ChecklistSetting", "checklist_setting", "ChecklistSetting",
        list_path="/api/checklist-setting/",
        update=Route("PUT", "/api/checklist-setting/{pk}",
                     body=lambda d: {"item_name": {"en": "iso-updated"},
                                     "category": d.checklist_category().pk}),
        delete=Route("DELETE", "/api/checklist-setting/delete/{pk}"),
        factory=lambda d, n: {"item_name": f"iso-item-{n}", "category": d.checklist_category()},
    ),
    Target(
        "SurveillanceProfile", "surveillance", "SurveillanceProfile",
        list_path="/api/surveillance/surveillance-profiles",
        detail=Route("GET", "/api/surveillance/surveillance-profiles/{pk}"),
        update=Route("PUT", "/api/surveillance/surveillance-profiles/{pk}"),
        delete=Route("DELETE", "/api/surveillance/surveillance-profiles/{pk}"),
        factory=lambda d, n: {
            "name": f"iso-profile-{n}", "mission": d.survey_mission(),
            "start_time": d.now(),
        },
    ),
    Target(
        "HandoverDocument", "handover", "HandoverDocument", reach="via_parent",
        list_path="/api/handover/handover/management",
        factory=lambda d, n: {
            "start_date": d.now(), "end_date": d.now(), "handover": d.owner,
            "shift": d.handover_shift(), "date_create_shift": d.today(),
        },
    ),
    Target(
        "ReportTemplate", "report_template", "ReportTemplate",
        list_path="/api/report-template/",
        detail=Route("GET", "/api/report-template/{pk}"),
        update=Route("PUT", "/api/report-template/{pk}",
                     body={"name": "iso-updated", "template": "iso"}),
        delete=Route("DELETE", "/api/report-template/delete/{pk}"),
        factory=lambda d, n: {"name": f"iso-template-{n}"},
    ),

    # ─────────────────────────────────────────────────────────────────────
    # W0-14c · P0 등재 (D-262 ② EXIT 필수 · 착수 순서 D-266 선결 2종 먼저)
    #
    # ★ 경로는 **초안이 아니라 실측**이다. `p0_target_draft.md` 는 정적 초안이었고
    #   실제로 둘 중 하나가 틀렸다 — VideoAnalysis 의 상세 경로로
    #   `/api/surveillance/surveillance-profiles/{profile_id}` 를 적었는데 그것은
    #   **다른 모델(SurveillanceProfile)의 라우트**다. 실경로는 `/video-analysis/{id}` 다.
    #   근거: evidence/W0-14/openapi_routes.json (531 경로 · 652 오퍼레이션)
    #   필수 필드도 기동본에서 실측했다 (scripts/probe_p0_targets.py) — 둘 다 0개.
    # ─────────────────────────────────────────────────────────────────────

    # flight_log.FlightLog — 308행 · F-13 정찰. ★ D-266: WP-DA2 착수를 막는 2종 중 하나
    Target(
        "FlightLog", "flight_log", "FlightLog",
        list_path="/api/flight-log/flight-log/",
        detail=Route("GET", "/api/flight-log/flight-log/detail/{pk}"),
        delete=Route("DELETE", "/api/flight-log/flight-log/delete/{pk}"),
        factory=lambda d, n: {},          # 필수 필드 0개 (실측)
    ),

    # surveillance.VideoAnalysis — 117행 · F-01~03 탐지. ★ D-266 선결 2종 중 하나
    Target(
        "VideoAnalysis", "surveillance", "VideoAnalysis",
        list_path="/api/surveillance/video-analysis",
        detail=Route("GET", "/api/surveillance/video-analysis/{pk}"),
        factory=lambda d, n: {},          # 필수 필드 0개 (실측)
    ),

    # ─────────────────────────────────────────────────────────────────────
    # W0-14c · P0 나머지 13종 (D-262 ② EXIT 전수 · D-272 도달 가능성 3값)
    #
    # ★ `reach` 는 인구조사(tenant_census)와 **같아야 한다** — 다르면 시험이 실패한다.
    #   direct_pk  = 자기 pk 로 지목하는 경로가 있다 → 그 경로를 친다
    #   via_parent = 자기 pk 경로는 없고 **부모를 통해 노출된다** →
    #                부모 경로 스코프 + 자식 필터를 **둘 다** 친다.
    #                "직접 경로 없음"은 안전이 아니다 (D-272).
    # ─────────────────────────────────────────────────────────────────────

    # --- direct_pk 3종 (FlightLog·VideoAnalysis 는 위에 이미 있다) --------
    Target(
        "OrderItem", "orders", "OrderItem", reach="direct_pk",
        list_path="/api/operational-data/operational-data",
        detail=Route("GET", "/api/operational-data/operational-data/{pk}"),
        factory=lambda d, n: {"order": d.order(), "name": f"iso-item-{n}"},
    ),
    Target(
        "OrderStatusMapping", "orders", "OrderStatusMapping", reach="direct_pk",
        list_path="/api/orders/order-status-mappings",
        detail=Route("GET", "/api/orders/order-status-mappings/{pk}"),
        factory=lambda d, n: {"delivery_status": d.delivery_status()},
    ),
    Target(
        # ★ 초안·추적본이 지목한 `/api/optimization/optimization/task-status/{task_id}` 는
        #   **이 모델의 라우트가 아니다** — 그 핸들러는 Celery `AsyncResult(task_id)` 를 볼 뿐
        #   TaskStatus 를 만지지 않는다. 이름이 같아서 매핑됐다.
        #   실제 라우트는 `/api/task-status/task-status/{task_id}` 이고,
        #   자리표시자는 pk 가 아니라 **업무 키 `task_id`** 다 (D-273 초안 검증 원칙).
        "TaskStatus", "task_status", "TaskStatus", reach="direct_pk",
        pk_attr="task_id",
        detail=Route("GET", "/api/task-status/task-status/{pk}"),
        factory=lambda d, n: {"task_id": f"iso-task-{d.tag}-{n}", "task_type": "iso"},
    ),

    # --- via_parent 10종 --------------------------------------------------
    Target(
        "MissionWaypoint", "surveillance", "MissionWaypoint", reach="via_parent",
        via_parent=Route("GET", "/api/surveillance/survey-missions/{pk}"),
        parent_pk=lambda o: o.mission_id,
        factory=lambda d, n: {"mission": d.survey_mission(), "order": n,
                              "latitude": "37.0", "longitude": "127.0"},
    ),
    Target(
        "SurveillanceProfileDrone", "surveillance", "SurveillanceProfileDrone",
        reach="via_parent",
        via_parent=Route("GET", "/api/surveillance/surveillance-profiles/{pk}"),
        parent_pk=lambda o: o.profile_id,
        # unique(profile, order) 제약이 있고 order 에 기본값이 있어, 두 테넌트가
        # 같은 값으로 충돌한다 — 실측에서 IntegrityError 로 드러났다. 순번을 준다.
        factory=lambda d, n: {"profile": d.surveillance_profile(), "order": n},
    ),
    Target(
        "SurveillanceProfileChecklist", "surveillance", "SurveillanceProfileChecklist",
        reach="via_parent",
        via_parent=Route("GET", "/api/surveillance/surveillance-profiles/{pk}"),
        parent_pk=lambda o: o.profile_id,
        # unique(profile, profile_drone) — 캐시된 드론을 다시 쓰면 다른 시나리오가 만든
        # 체크리스트와 충돌한다. 순번을 준 새 드론으로 만든다 (실측에서 드러났다).
        factory=lambda d, n: {"profile": d.surveillance_profile(),
                              "profile_drone": d.profile_drone_n(n)},
    ),
    Target(
        "SurveillanceProfileChecklistItem", "surveillance",
        "SurveillanceProfileChecklistItem", reach="via_parent",
        # 유일한 도달 경로가 `write` 버킷에 있다 — 부모 프로필의 pk 를 받는다.
        via_parent=Route("GET", "/api/surveillance/surveillance-profiles/{pk}"),
        parent_pk=lambda o: o.checklist.profile_id,
        factory=lambda d, n: {"checklist": d.profile_checklist()},
    ),
    Target(
        "OrderHistory", "orders", "OrderHistory", reach="via_parent",
        via_parent=Route("GET", "/api/orders/order/{pk}"),
        parent_pk=lambda o: o.order_id,
        factory=lambda d, n: {"order": d.order(), "action": "iso",
                              "description": f"iso-history-{n}"},
    ),
    Target(
        "Payment", "orders", "Payment", reach="via_parent",
        via_parent=Route("GET", "/api/orders/order/{pk}"),
        parent_pk=lambda o: o.order_id,
        factory=lambda d, n: {"order": d.order(), "amount": 1000,
                              "payment_type": d.payment_type()},
    ),
    Target(
        "DeliveryOperation", "delivery", "DeliveryOperation", reach="via_parent",
        via_parent=Route("GET", "/api/orders/order/{pk}"),
        parent_pk=lambda o: o.order_id,
        # order 가 OneToOne 이라 캐시된 주문을 재사용하면 unique 위반이다.
        factory=lambda d, n: {"order": d.order_n(n), "current_status": d.delivery_status()},
    ),
    Target(
        "DeliveryOperationItem", "delivery", "DeliveryOperationItem", reach="via_parent",
        # 부모(DeliveryOperation)를 지목하는 라우트가 없다 — 목록 경로로 자식 필터를 본다.
        via_parent=Route("GET", "/api/operational-data/operational-data"),
        factory=lambda d, n: {"delivery_operation": d.delivery_operation()},
    ),
    Target(
        "RouteTerminal", "terminals", "RouteTerminal", reach="via_parent",
        via_parent=Route("GET", "/api/terminals/routes/{pk}"),
        parent_pk=lambda o: o.route_id,
        factory=lambda d, n: {"route": d.routes(), "terminal": d.terminal()},
    ),
    Target(
        "TerminalOperatingTime", "terminals", "TerminalOperatingTime", reach="via_parent",
        via_parent=Route("GET", "/api/terminals/terminals/{pk}/operating-times"),
        parent_pk=lambda o: o.terminal_id,
        factory=lambda d, n: {"terminal": d.terminal(), "day_of_week": d.day_of_week()},
    ),

    # W2-1 에서 신설. BaseModelWithGroup 상속 — group 격리 대상이다.
    # HTTP 표면은 아직 없다 (W2-2 가 만든다) — 그래서 전 시나리오가 NO_ROUTE 다.
    Target(
        "DetectionEvent", "stream_monitors", "DetectionEvent", reach="no_route",
        factory=lambda d, n: {
            "stream_monitor": d.stream_monitor(), "event_type": "iso-test",
            "occurred_at": d.now(), "snapshot_path": f"iso/{n}.jpg",
        },
    ),
)

#: 라우트가 **실재하지 않는** 시나리오. `"<label>:<시나리오>"` → 사유.
#:
#: 왜 목록으로 두는가
#:     경로가 없는 칸을 조용히 건너뛰면 "5/5 초록"이 실제 커버리지보다 커 보인다.
#:     그 착시는 게이트가 없는 것보다 나쁘다 (WP-0 EXIT §6-1 `tickets.sha256` 과 같은 실패 모양).
#:     그래서 **사유와 함께 명시 등록**하고, 이 집합이 늘면 아래 증가금지 시험이 실패한다.
#: 줄어드는 것은 환영이다 — 라우트가 생기면 여기서 지우고 Target 에 적는다.
NO_ROUTE: dict[str, str] = {
    "Order:update": "id 로 수정하는 라우트가 없다. 수정은 POST /{id}/change-status 등 동사별 경로다",
    "Order:delete": "삭제 라우트가 없다 (주문은 취소로 처리한다 — POST /{id}/cancel-order)",
    "StreamMonitor:detail": "단건 조회 라우트가 없다. 목록만 있다",
    "StreamMonitor:update": "수정은 POST '' 에 본문 배열로 하는 대량 갱신이다 — pk 로 지목할 수 없다",
    "StreamMonitor:delete": "id 로 삭제하는 라우트가 없다 (external-stream-monitors 만 있다)",
    "Dashboard:detail": "단건 조회 라우트가 없다",
    "Dashboard:update": "id 로 수정하는 라우트가 없다 (refresh·weather-setting 등 동사 경로만)",
    "Dashboard:delete": "삭제 라우트가 없다",
    "ChecklistSetting:detail": "PUT /{id} 는 있으나 GET /{id} 가 없다 — 상세 조회 라우트 없음",
    "HandoverDocument:detail": "단건 조회는 GET /content/by-id-management (질의문자열) — pk 경로가 아니다",
    "HandoverDocument:update": "수정은 POST /management 본문 — pk 로 지목할 수 없다",
    "HandoverDocument:delete": "삭제는 DELETE /management 본문 — pk 로 지목할 수 없다",
    "DetectionEvent:list": "HTTP 표면 미구현 (W2-2 가 만든다)",
    "DetectionEvent:detail": "HTTP 표면 미구현 (W2-2)",
    "DetectionEvent:update": "HTTP 표면 미구현 (W2-2)",
    "DetectionEvent:delete": "HTTP 표면 미구현 (W2-2)",

    # ── W0-14c · P0 등재분 (2026-08-27 실측) ─────────────────────────────
    "FlightLog:update": "수정 라우트가 없다. 비행 로그는 기기가 쓰고 사람은 읽기만 한다 "
                        "(flight_log/views.py 의 라우트 4개는 목록·상세·다운로드·삭제뿐)",
    "VideoAnalysis:update": "수정 라우트가 없다 — /video-analysis 컨트롤러는 GET 3개뿐이다",
    "VideoAnalysis:delete": "삭제 라우트가 없다 — 같은 이유",

    # ── W0-14c · P0 나머지 등재분 (2026-08-28 · openapi_routes.json 전수 대조) ──
    "OrderItem:update": "수정 라우트가 없다. /operational-data/{order_item_id} 아래는 "
                        "업로드 POST 4건뿐이고 품목 자체를 고치는 경로가 아니다",
    "OrderItem:delete": "삭제 라우트가 없다 — 품목은 주문 취소로 처리된다",
    "OrderStatusMapping:update": "PUT 은 /update/{group_id} 로 **그룹 단위**다 — "
                                 "매핑 pk 를 지목하지 않는다",
    "OrderStatusMapping:delete": "DELETE 는 /delete/{group_ids} 로 **그룹 단위**다 — "
                                 "매핑 pk 를 지목하지 않는다",
    "TaskStatus:list": "목록 라우트가 없다. task-status 는 {task_id} 단건 조회 2건뿐이다",
    "TaskStatus:update": "수정 라우트가 없다 — 상태는 작업이 쓰고 사람은 읽기만 한다",
    "TaskStatus:delete": "삭제 라우트가 없다 — 같은 이유",
}

#: ★ **FK 격리가 실증된 모델** — D-271 ① 의 증명 게이트.
#:
#: 값은 **무엇으로 증명했는가**다. "FK 를 가졌다"는 증명이 아니다 —
#: 비소유 테넌트로 HTTP 를 쳐서 누출 0 을 본 것이 증명이다.
#: 여기 없는 FK 모델은 `unproven` 이고, **unproven 은 안전이 아니라 "아직 모른다"**이다.
#:
#: ⚠ 이 표에 이름을 올리는 것은 **초록 하나를 늘리는 일**이다. 근거 없이 올리지 않는다.
#:   근거는 이 파일의 시나리오 시험이 그 모델을 실제로 쳤다는 사실이어야 하고,
#:   아래 `test_proven_models_are_actually_probed` 가 그것을 대조한다.
FK_PROVEN: dict[str, str] = {
    "orders.Order":
        "detail 시나리오 실측 — 남의 pk 로 GET /api/orders/order/{id} (2026-08-27 · §0.4 계약 결함 별건)",
    "terminals.Terminal":
        "detail 404 실측 — GET /api/terminals/terminals/{id} (2026-08-27)",
    "devices.Device":
        "detail·update·delete 전건 404 실측 (2026-08-27)",
    "checklist_setting.ChecklistSetting":
        "update·delete 404 실측 (2026-08-27)",
    "surveillance.SurveillanceProfile":
        "detail·update·delete 전건 404 실측 (2026-08-27)",
    "report_template.ReportTemplate":
        "detail·update·delete 전건 404 실측 (2026-08-27)",
    "flight_log.FlightLog":
        "detail·delete 404 실측 — assert_scoped 부착 후 (2026-08-27 · D-274)",
    "surveillance.VideoAnalysis":
        "detail 404 실측 — assert_scoped 부착 후 (2026-08-27 · D-274)",
}

#: 격리 메커니즘이 **아예 없는** 모델 — 소유 필드(`groups` M2M · `group` FK) 둘 다 없다.
#:
#: ★ 2026-08-28: **비었다.** 옛 술어가 `groups` M2M 만 봐서 여기 4종이 들어 있었으나
#:   (`orders.Order` · `devices.Device` · `report_template.ReportTemplate` ·
#:   `handover.HandoverDocument`), 넷 다 **`group` FK 를 가지고 있다.**
#:   즉 이 집합은 **틀린 사실을 정본에 기록하고 있었다** — D-271 이 고친 것이 이것이다.
#:   비운 것은 요구를 낮춘 것이 아니다: 그 넷은 이제 `FK_PROVEN` 의 **실증 대상**이 된다.
KNOWN_UNISOLATED: frozenset[str] = frozenset()


# ═══════════════════════════════════════════════════════════════════════════
# 헬퍼
# ═══════════════════════════════════════════════════════════════════════════

def get_model(target: Target) -> type[models.Model]:
    return apps.get_model(target.app_label, target.model_name)


def _concrete(model: type[models.Model]):
    """실제 필드만. **역방향 접근자를 세지 않는다** (D-263).

    `auth.Permission` 에는 `auth.Group.permissions` 의 역방향 접근자가 `group` 이라는
    이름으로 잡힌다 — 인구조사 첫 판이 그것을 800행짜리 격리 대상으로 보고했다.
    """
    return [f for f in model._meta.get_fields() if isinstance(f, models.Field)]


def has_group_m2m(model: type[models.Model]) -> bool:
    return any(f.name == "groups" and getattr(f, "many_to_many", False)
               for f in _concrete(model))


def has_group_fk(model: type[models.Model]) -> bool:
    """dj-core `BaseModelWithGroup` 계열 — `group` FK 로 테넌트를 가린다."""
    return any(f.name == "group" and getattr(f, "many_to_one", False)
               for f in _concrete(model))


def is_group_isolatable(model: type[models.Model]) -> bool:
    """group 격리를 **받을 수 있는가** — `groups` M2M ∪ `group` FK (D-271).

    ★ 2026-08-28 술어 교정 (D-271 · P-LOCAL-3 A안 승인).
      옛 정의는 `groups` M2M 만 봤다. 그 술어로 센 모수는 **2종**이다
      (`dashboard.Dashboard` · `dashboard.DashboardPanel`) — 실측 모수는 **142종**이고,
      나머지 140종은 dj-core `BaseModelWithGroup` 의 **`group` FK(단수)** 를 쓴다.
      W0-13 백필이 채운 25,296행이 바로 그 `group_id` 다. **기전은 있고 모양이 달랐다.**

      즉 옛 정의는 "격리 메커니즘이 없다"는 **틀린 사실**을 4개 모델에 새기고 있었고
      (`KNOWN_UNISOLATED`), 모수 2 위의 초록으로 D-260 이 지적한 착시를 만들고 있었다.

      **D-105(격리 시험 약화 금지) 저촉이 아니다** — 시험을 무르게 하는 변경이 아니라
      술어의 사실오류 교정이고, 아래 `is_isolation_proven` 이 요구 수준을 **높인다.**
    """
    return has_group_m2m(model) or has_group_fk(model)


def is_isolation_proven(model: type[models.Model]) -> bool:
    """격리가 **증명됐는가** — D-271 ① 의 증명 게이트.

    "FK 를 가졌다"와 "그 필터가 실제로 걸린다"는 다른 문장이다.
    W0-11 §5-2 가 `created_by__isnull` OR 3곳으로 후자가 거짓일 수 있음을 이미 보였고,
    이번 턴에 `FlightLog` 가 `_base_manager` 로 통째로 열려 있던 것이 그 실례다.

    그래서 **FK 는 실증된 것만 초록으로 센다.** 미실증은 `unproven` 이고,
    unproven 은 "안전"이 아니라 **"아직 모른다"**이다.
    """
    if has_group_m2m(model):
        return True
    return f"{model._meta.app_label}.{model.__name__}" in FK_PROVEN


class _FakeRequest:
    """매니저가 보는 '현재 요청' 대역 (D-253 배선).

    `mock.Mock()` 을 쓰면 `common/base_model.py` 의 `user_id not in request._user_group_cache`
    에서 **TypeError: argument of type 'Mock' is not iterable** 이 난다 — Mock 이 캐시
    속성을 Mock 으로 자동 생성하기 때문이다. 실제 요청이 갖는 최소한만 가진 스텁을 쓴다.
    """

    def __init__(self, user):
        self.user = user
        self.META: dict[str, Any] = {}
        self.path = "/tenant-isolation-test"
        self._user_group_cache: dict[Any, Any] = {}


@contextlib.contextmanager
def acting_as(user):
    """매니저가 보는 '현재 요청'을 주어진 사용자로 바꾼다.

    CustomManagerGroup 은 thread-local 요청에서 user 를 읽는다.
    common.base_model 은 `from ... import get_current_request` 로 함수를 직접
    바인딩하므로 원본 모듈만 패치하면 반영되지 않는다. 둘 다 패치한다.
    """
    request = _FakeRequest(user)
    targets = [
        "common.base_model.get_current_request",
        "core.middleware.refresh_token.get_current_request",
    ]
    with contextlib.ExitStack() as stack:
        for dotted in targets:
            with contextlib.suppress(ModuleNotFoundError, AttributeError):
                stack.enter_context(mock.patch(dotted, return_value=request))
        # ★ 스레드 로컬 자체도 바꾼다 (D-253 배선).
        #   dj-core 는 `get_current_request` 를 **자기 모듈에서** import 해 쓰므로 위의
        #   patch 두 개로는 저장 시 `created_by` 자동 채움 경로를 덮지 못한다. 그러면
        #   **직전 HTTP 요청의 사용자**가 소유자로 찍히고, tenant-B 소유로 만들려던 레코드가
        #   실제로는 tenant-A 것이 된다 — 픽스처가 시험을 스스로 통과시켜 버린다.
        previous = None
        thread_local = None
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            previous = getattr(thread_local, "request", None)
            thread_local.request = request
        try:
            yield request
        finally:
            if thread_local is not None:
                with contextlib.suppress(Exception):
                    thread_local.request = previous


class Deps:
    """필수 FK 를 만드는 도우미 (D-253 배선 승인분).

    이전 판의 `factory_kwargs` 는 정적 dict 여서 필수 FK 를 채울 수 없었다 —
    errors 24건이 전부 그것이었다 (Order.recipient_address · ChecklistSetting.category ·
    SurveillanceProfile.mission · HandoverDocument.shift · DetectionEvent.stream_monitor).
    의존은 한 번만 만들어 재사용한다 (같은 테넌트 소유로 둔다 — 검증 대상이 아니다).
    """

    def __init__(self, owner, group):
        self.owner = owner
        self.group = group
        self._cache: dict[str, Any] = {}
        # 의존의 code 는 **전역 UNIQUE** 다. 테넌트마다 다른 접미사를 붙여야
        # A 쪽과 B 쪽 의존이 충돌하지 않는다 (실측: ISO-CAT 중복으로 픽스처가 죽었다).
        self.tag = f"{getattr(group, 'pk', 'x')}"


    # --- 값 -----------------------------------------------------------------
    @staticmethod
    def now():
        from django.utils import timezone

        return timezone.now()

    @classmethod
    def today(cls):
        return cls.now().date()

    # --- 의존 레코드 ---------------------------------------------------------
    def _once(self, key: str, build: Callable[[], Any]):
        if key not in self._cache:
            self._cache[key] = build()
        return self._cache[key]

    def _create(self, app_label: str, model_name: str, **kwargs):
        model = apps.get_model(app_label, model_name)
        obj = model(**kwargs)
        obj.created_by = self.owner
        obj.save()
        if has_group_m2m(model):
            obj.groups.set([self.group])
        elif has_group_fk(model) and getattr(obj, "group_id", None) != self.group.pk:
            obj.group = self.group
            obj.save(update_fields=["group"])
        return obj

    def address(self):
        return self._once("address", lambda: self._create("delivery", "Address"))

    def checklist_category(self):
        return self._once("checklist_category", lambda: self._create(
            "checklist_setting", "ChecklistSettingCategory",
            name=f"iso-category-{self.tag}", code=f"ISO-CAT-{self.tag}",
        ))

    def survey_mission(self):
        def build():
            purpose = self._create("surveillance", "MissionPurpose",
                                   name=f"iso-purpose-{self.tag}",
                                   code=f"ISO-PURPOSE-{self.tag}")
            status = self._create("surveillance", "SurveyMissionStatus",
                                  name=f"iso-status-{self.tag}",
                                  code=f"ISO-STATUS-{self.tag}")
            return self._create("surveillance", "SurveyMission",
                                name=f"iso-mission-{self.tag}", maximum_drones=1,
                                purpose=purpose, status=status)
        return self._once("survey_mission", build)

    def handover_shift(self):
        return self._once("handover_shift", lambda: self._create(
            "handover", "HandoverShift", name=f"iso-shift-{self.tag}",
            start_time="09:00", end_time="18:00",
        ))

    def order_status(self):
        return self._once("order_status", lambda: self._create(
            "orders", "OrderStatus", name=f"iso-ostatus-{self.tag}",
            code=f"iso_ostatus_{self.tag}",
        ))

    def stream_monitor(self):
        return self._once("stream_monitor", lambda: self._create(
            "stream_monitors", "StreamMonitor", name=f"iso-dep-monitor-{self.tag}",
            code=f"ISO-DEP-MON-{self.tag}", ip_source="rtsp://iso.invalid/dep",
        ))

    # ── W0-14c · P0 등재분의 의존 (2026-08-28) ───────────────────────────
    # 필수 필드는 전부 기동본에서 실측했다 (scripts/probe_p0_targets.py).
    # 추정으로 채우지 않는다 — W0-14b 를 죽인 것이 못 본 필수 FK 24건이었다.
    def terminal(self):
        return self._once("terminal", lambda: self._create(
            "terminals", "Terminal", name=f"iso-dep-terminal-{self.tag}"))

    def day_of_week(self):
        return self._once("day_of_week", lambda: self._create(
            "terminals", "DayOfWeek", name=f"iso-dow-{self.tag}", code=f"ISO-DOW-{self.tag}"))

    def routes(self):
        return self._once("routes", lambda: self._create(
            "terminals", "Routes", name=f"iso-route-{self.tag}"))

    def order(self):
        return self._once("order", lambda: self._create(
            "orders", "Order", order_code=f"ISO-DEP-{self.tag}",
            recipient_name=f"iso-dep-{self.tag}", recipient_phone="01000000000",
            recipient_address=self.address(), status=self.order_status()))

    def order_n(self, n: int):
        """순번을 준 **새** 주문. `DeliveryOperation.order` 가 OneToOne 이라
        캐시된 주문을 다시 쓰면 unique 위반이다 (실측에서 드러났다)."""
        return self._once(f"order_{n}", lambda: self._create(
            "orders", "Order", order_code=f"ISO-DEP-{self.tag}-{n}",
            recipient_name=f"iso-dep-{self.tag}-{n}", recipient_phone="01000000000",
            recipient_address=self.address(), status=self.order_status()))

    def delivery_status(self):
        return self._once("delivery_status", lambda: self._create(
            "delivery", "DeliveryStatus", name=f"iso-dstatus-{self.tag}",
            code=f"ISO-DSTATUS-{self.tag}"))

    def delivery_operation(self):
        return self._once("delivery_operation", lambda: self._create(
            "delivery", "DeliveryOperation", order=self.order_n(900),
            current_status=self.delivery_status()))

    def payment_type(self):
        return self._once("payment_type", lambda: self._create(
            "orders", "PaymentType", name=f"iso-ptype-{self.tag}",
            code=f"ISO-PTYPE-{self.tag}"))

    def external_order_status(self):
        return self._once("external_order_status", lambda: self._create(
            "orders", "ExternalOrderStatus", name=f"iso-ext-{self.tag}",
            value=f"ISO-EXT-{self.tag}"))

    def surveillance_profile(self):
        return self._once("surveillance_profile", lambda: self._create(
            "surveillance", "SurveillanceProfile", name=f"iso-dep-profile-{self.tag}",
            mission=self.survey_mission(), start_time=self.now()))

    def profile_drone(self):
        return self._once("profile_drone", lambda: self._create(
            "surveillance", "SurveillanceProfileDrone",
            profile=self.surveillance_profile(), order=900 + int(self.tag or 0)))

    def profile_drone_n(self, n: int):
        """순번을 준 **새** 드론. `unique(profile, order)` 때문에 재사용하면 충돌한다."""
        return self._once(f"profile_drone_{n}", lambda: self._create(
            "surveillance", "SurveillanceProfileDrone",
            profile=self.surveillance_profile(), order=1000 + n))

    def profile_checklist(self):
        return self._once("profile_checklist", lambda: self._create(
            "surveillance", "SurveillanceProfileChecklist",
            profile=self.surveillance_profile(), profile_drone=self.profile_drone()))


class TenantFixtureMixin:
    """group A/B 사용자와 각 group 소유 레코드를 만든다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        CoreUser = apps.get_model("user", "CoreUser")
        UserGroup = apps.get_model("user", "UserGroup")

        # 스레드 로컬에 남은 이전 시험의 요청을 먼저 지운다 (D-253 배선).
        # 남겨 두면 dj-core 가 `created_by` 를 **롤백된 사용자 id** 로 자동 채우고,
        # 그 매달린 FK 가 teardown 의 제약 검사에서 터진다 (user_usergroup_created_by_id_fk).
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="tenant-A")
        cls.group_b = UserGroup.objects.create(name="tenant-B")
        # 자동 채워진 소유자 흔적을 지운다 — 이 시험의 관심사가 아니고, 매달린 FK 만 남긴다.
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)
        cls.user_a = cls._make_user("user_a", cls.group_a)
        cls.user_b = cls._make_user("user_b", cls.group_b)
        cls._grant_path_permissions([cls.user_a, cls.user_b])

    # ------------------------------------------------------------------ 권한
    @classmethod
    def _grant_path_permissions(cls, users) -> None:
        """두 사용자에게 **같은** 경로 권한을 준다 (D-253 배선 승인분).

        왜 필요한가
            보호된 라우트는 `@path_permission(...)` 을 통과해야 핸들러에 닿는다.
            역할이 없는 픽스처 사용자는 그 앞에서 막혔고(401/거부), 그래서 이 시험은
            **격리가 아니라 권한 부재**를 재고 있었다. 두 사용자에게 동일한 권한을 주면
            남는 차이는 **소속 테넌트 하나**뿐 — 그것이 이 시험이 묻는 것이다.

        ⚠ 역할 코드를 `superuser` 로 두지 않는다. 그 코드는 dj-core 의 ORM 필터와
          권한 검사를 통째로 통과시킨다(`core/base.py:308` · `permission.py:475`) —
          그 역할을 주면 격리 시험이 스스로 우회를 만든다.
        """
        Role = apps.get_model("role", "Role")
        Menu = apps.get_model("menu", "Menu")
        RoleMenu = apps.get_model("menu", "RoleMenu")

        role = Role.objects.create(role_name="tenant-isolation-test", code="tenant_iso_test")
        for path in sorted(cls._protected_paths()):
            menu = Menu.objects.create(menu_name=f"iso {path}", path=path)
            RoleMenu.objects.create(
                menu=menu, role=role,
                permit_read=True, permit_create=True,
                permit_update=True, permit_delete=True,
            )
        for user in users:
            user.roles.add(role)

    @classmethod
    def _protected_paths(cls) -> set[str]:
        """등록된 라우트가 요구하는 권한 경로를 **런타임에서** 수집한다.

        `path_permission` 이 핸들러에 `_path_override` 를 남긴다. 손으로 적으면
        라우트가 늘 때마다 어긋나므로 열거기(W0-14)가 찾은 핸들러에서 읽는다.
        """
        paths: set[str] = set()
        try:
            from common.tenant_scope import enumerate_operations
        except Exception:  # pragma: no cover - 열거 불가 환경
            return paths
        for route in enumerate_operations():
            override = getattr(route, "path_override", None)
            if override is None:
                continue
            if isinstance(override, (list, tuple, set)):
                paths.update(str(p) for p in override)
            else:
                paths.add(str(override))
        return paths

    @classmethod
    def _make_user(cls, username: str, group):
        """CoreUser 를 만들고 group 에 소속시킨다.

        UserProfileLink 의 정확한 모듈 경로·필드명은 dj-core 안에 있어
        저장소에서 읽을 수 없다. 관계 이름(`userprofilelink`)으로 역참조해
        런타임에 모델을 찾는다 — 사내 패키지 버전이 바뀌어도 깨지지 않는다.
        """
        CoreUser = apps.get_model("user", "CoreUser")
        # email 을 명시한다 — dj-core CoreUser.email 은 UNIQUE 라서 두 사용자가 모두
        # 빈 문자열로 들어가면 setUpTestData 가 픽스처 단계에서 죽는다 (P-LOCAL-2).
        # **판정 로직은 한 글자도 바꾸지 않는다.** 픽스처만 유효해진다 (D-250 · 옵션 A).
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid",
        )
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_model = link_field.related_model
        link_model.objects.create(**{link_field.remote_field.name: user, "group": group})
        return user

    def _deps_for(self, owner, group) -> "Deps":
        """시험 하나 안에서 (소유자, group) 당 `Deps` 하나. 의존의 UNIQUE 충돌을 막는다."""
        cache = getattr(self, "_deps_cache", None)
        if cache is None:
            cache = self._deps_cache = {}
        key = (getattr(owner, "pk", None), getattr(group, "pk", None))
        deps = cache.get(key)
        if deps is None:
            deps = cache[key] = Deps(owner, group)
        return deps

    def _create_for(self, model: type[models.Model], group, owner, target: Target):
        """`group` 소유 레코드 1건. 필수 필드는 target.factory 가 채운다 (D-253).

        ★ 인스턴스 메서드다(클래스 메서드가 아니다). 의존 레코드 캐시를 **시험 하나의
          수명**으로 묶기 위해서다. 클래스에 캐시를 두면 앞 시험에서 만든 pk 가 롤백된 뒤에도
          남아, 다음 시험이 없는 행을 참조하고 teardown 의 FK 검사에서 터진다.
        """
        self._seq = getattr(self, "_seq", 0) + 1
        seq = self._seq
        with acting_as(owner):
            deps = self._deps_for(owner, group)
            kwargs = target.factory(deps, seq) if target.factory else {}
            obj = model(**kwargs)
            obj.created_by = owner
            obj.save()
            if has_group_m2m(model):
                obj.groups.set([group])
            elif has_group_fk(model):
                # ★ dj-core 의 BaseModelWithGroup 은 `group` FK(단수)를 쓴다.
                #   여기서 명시하지 않고 자동 채움에 기대면, 픽스처가 **남의 것을 만들지
                #   못했는데도 시험은 통과**할 수 있다 — D-253 2차 정정이 잡은 오염이
                #   정확히 그 모양이었다(직전 요청의 사용자로 저장돼 A 가 읽는 게 정상이었다).
                if getattr(obj, "group_id", None) != getattr(group, "pk", None):
                    obj.group = group
                    obj.save(update_fields=["group"])
        # 만든 것이 정말 그 테넌트 소유인가 — 픽스처가 스스로 증명한다.
        # 이것이 아니면 이 시험은 격리가 아니라 자기 자신을 시험하게 된다.
        self._assert_owned_by(obj, group, target)
        return obj

    @staticmethod
    def _m2m_owner_pks(obj) -> set:
        """`groups` M2M 의 실제 소유자 pk. **연결 테이블을 `_base_manager` 로 직접 읽는다.**

        ★ `obj.groups.values_list("pk")` 로 물으면 안 된다 — 그 관리자는 `UserGroup` 의
          테넌트 필터를 타므로, 현재 사용자 문맥이 없는 자리에서는 **붙어 있는데도 빈 집합**을
          돌려준다. 실측에서 Dashboard 가 정확히 그렇게 나왔다.
          '없다'와 '내게 안 보인다'를 구별하려면 연결 테이블 자체를 봐야 한다
          (D-253 이 삭제 판정을 `_base_manager` 로 옮긴 것과 같은 이유다).
        """
        through = type(obj)._meta.get_field("groups").remote_field.through
        to_obj = next(f.name for f in through._meta.fields
                      if f.related_model is type(obj))
        to_grp = next(f for f in through._meta.fields
                      if f.related_model is not None and f.name != to_obj
                      and f.related_model is not type(obj))
        rows = through._base_manager.filter(**{to_obj: obj})
        return set(rows.values_list(f"{to_grp.name}_id", flat=True))

    def _assert_owned_by(self, obj, group, target: Target) -> None:
        model = type(obj)
        if has_group_m2m(model):
            owners = self._m2m_owner_pks(obj)
            self.assertEqual(
                {group.pk}, owners,
                f"[{target.label}] 픽스처가 만든 레코드의 groups 가 {owners} 입니다 — "
                f"의도한 소유는 {group.pk} 입니다. 소유가 틀리면 이 시험은 격리를 재지 않습니다.")
        elif has_group_fk(model):
            self.assertEqual(
                getattr(group, "pk", None), getattr(obj, "group_id", None),
                f"[{target.label}] 픽스처가 만든 레코드의 group_id 가 "
                f"{getattr(obj, 'group_id', None)} 입니다 — 의도한 소유는 {group.pk} 입니다.")

    @classmethod
    def _bearer(cls, user) -> dict[str, str]:
        """이 사용자로 인증된 요청 헤더.

        `force_login`(세션)만으로는 ninja JWT 라우터가 통과하지 않는다 — 실측 401.
        그리고 `RefreshToken.for_user()` 로 만든 **맨 토큰도 통과하지 않는다** — dj-core 는
        토큰의 `jti` 를 사용자에 저장된 세션 토큰과 대조한다. 그래서 로그인 경로가 하는
        것과 **같은 세 단계**를 그대로 한다: session_id 부여 → access 발급 → jti 저장.

        로그인 엔드포인트를 부르지 않는 이유: 그 경로에는 속도 제한이 있고, 초과 시
        429 가 아니라 **HTTP 500** 으로 나간다 (W0-18 의 대상). 이 시험의 주제가 아니다.
        """
        import uuid

        import jwt
        from django.conf import settings
        from ninja_jwt.tokens import RefreshToken

        session_id = str(uuid.uuid4())
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = jwt.decode(
            access,
            settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")],
        )
        setter = getattr(user, "set_encrypted_session_token", None)
        if setter is not None:
            setter(session_id, decoded.get("jti"))
            user.save()
        return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


# ═══════════════════════════════════════════════════════════════════════════
# 1) 레지스트리 검사 — 머지 게이트
# ═══════════════════════════════════════════════════════════════════════════

class TenantIsolationRegistryTest(TestCase):
    """새 모델을 만들고 여기 등록하지 않으면 실패한다."""

    #: dj-core 프레임워크 앱 — §0.4 라 이 저장소가 고칠 수 없다.
    #: **면제가 아니라 관할 밖**이다. 수는 따로 세어 보고한다.
    FRAMEWORK_APPS = {"user", "core"}

    @classmethod
    def _live_isolatable(cls) -> set[str]:
        """지금 코드에서 격리 대상인 모델 전부 (D-271 술어 · 저장소 관할)."""
        return {
            f"{m._meta.app_label}.{m.__name__}"
            for m in apps.get_models()
            if is_group_isolatable(m) and m._meta.app_label not in cls.FRAMEWORK_APPS
        }

    def test_census_matches_code(self) -> None:
        """인구조사 표가 **지금 코드**와 일치하는가 — 모르는 모델을 만나면 멈춘다 (D-264).

        표에 없는 모델이 코드에 생기면 아무도 그것을 보지 않는다.
        `leak_targets.json`(131종)이 덤프 집계라 **행 0인 모델 25종을 못 봤던 것**이
        정확히 그 상태였다 — 행이 0인 것은 "안전"이 아니라 "아직 안 썼다"이다.
        """
        live = self._live_isolatable()
        table = set(CENSUS)
        only_code = sorted(live - table)
        only_table = sorted(table - live)
        self.assertEqual(
            [], only_code,
            f"인구조사에 없는 격리 대상이 코드에 있습니다: {only_code}\n"
            "scripts/gen_tenant_census.py 를 다시 돌리고, **왜 늘었는지**를 함께 적으십시오.")
        self.assertEqual(
            [], only_table,
            f"인구조사에는 있는데 코드에 없는 모델입니다: {only_table}\n"
            "모델이 지워졌다면 표도 다시 만드십시오 — 낡은 표는 초록을 만듭니다.")

    def test_registry_covers_all_isolatable_models(self) -> None:
        """**모수는 142종이다** (D-271 ②).

        옛 정의는 `groups` M2M 만 세어 모수가 **2종**이었고, 그 위의 "누락 1건"은
        아무것도 말하지 않았다 — D-260 이 지적하고 D-271 이 인정한 작은 모수의 착시다.

        지금 요구하는 것: **P0 는 전수 등재**(D-262 ② EXIT 조건),
        나머지는 인구조사에 **사유와 함께** 분류되어 있을 것.
        """
        registered = {f"{t.app_label}.{t.model_name}" for t in MODELS}
        live = self._live_isolatable()

        p0 = sorted(k for k, v in CENSUS.items() if v[0] == "P0")
        missing_p0 = sorted(set(p0) - registered)
        self.assertEqual(
            [], missing_p0,
            f"P0 {len(p0)}종 중 {len(missing_p0)}종이 레지스트리에 없습니다 "
            f"(D-262 ② EXIT 조건):\n{missing_p0}\nMODELS 에 Target(...) 을 추가하십시오.")

        nofix = []
        for label in sorted(live - registered):
            entry = CENSUS.get(label)
            if entry is None or not (entry[4] or "").strip():
                nofix.append(label)
        self.assertEqual(
            [], nofix,
            f"분류 사유가 없는 격리 대상입니다: {nofix}\n"
            "사유 없는 분류는 '안 봤다'와 구별되지 않습니다 (D-262 ④).")

        print(f"\n[ISO] 모수 {len(live)}종 — 등재 {len(registered & live)} · "
              f"P0 {len(p0)}(전수 등재) · 표 밖 0")

    def test_unproven_fk_is_not_counted_green(self) -> None:
        """D-271 ① — FK 는 **실증된 것만** 초록으로 센다.

        "FK 를 가졌다"와 "그 필터가 실제로 걸린다"는 다른 문장이다.
        이번 턴의 `FlightLog` 가 그 실례다 — FK 를 가졌는데 `_base_manager` 로 통째로 열려 있었다.
        그러므로 미실증(`unproven`)은 **안전이 아니라 "아직 모른다"**이고, 초록에서 뺀다.
        """
        live = self._live_isolatable()
        proven, unproven = [], []
        for label in sorted(live):
            model = apps.get_model(label)
            (proven if is_isolation_proven(model) else unproven).append(label)

        registered = {f"{t.app_label}.{t.model_name}" for t in MODELS}
        self.assertTrue(
            set(proven) & registered,
            "실증된 모델이 하나도 없습니다 — FK_PROVEN 이 비었거나 술어가 깨졌습니다.")

        print(f"[ISO] 실증 {len(proven)}/{len(live)} · unproven {len(unproven)} "
              f"(unproven 은 안전이 아니라 '아직 모른다')")

        not_registered = sorted(set(FK_PROVEN) - registered)
        self.assertEqual(
            [], not_registered,
            f"FK_PROVEN 에 있는데 레지스트리에 없는 모델입니다: {not_registered}\n"
            "시험이 치지 않는 모델을 '실증됐다'고 적을 수 없습니다.")

    def test_proven_models_are_actually_probed(self) -> None:
        """실증 목록의 모델은 **HTTP 시나리오가 실재**해야 한다 (D-271 ①).

        시나리오가 하나도 없는데 이름만 올라와 있으면, 그 초록은 아무도 치지 않은 초록이다.
        """
        by_label = {f"{t.app_label}.{t.model_name}": t for t in MODELS}
        naked = []
        for label, why in FK_PROVEN.items():
            t = by_label.get(label)
            if t is None:
                continue
            if not (t.list_path or t.detail or t.update or t.delete or t.export_path):
                naked.append(label)
            self.assertGreaterEqual(
                len((why or "").strip()), 10,
                f"FK_PROVEN['{label}'] 에 근거가 없습니다 — 무엇으로 증명했는지 적으십시오.")
        self.assertEqual(
            [], naked,
            f"HTTP 시나리오가 하나도 없는데 실증됐다고 적힌 모델입니다: {naked}")

    def test_unisolated_set_has_not_grown(self) -> None:
        """격리 메커니즘이 **아예 없는** 모델이 새로 늘지 않았는지 확인한다.

        ★ 2026-08-28: 술어 교정(D-271)으로 이 집합은 **비었다.**
          옛 정의가 `groups` M2M 만 봐서 FK 를 가진 4종을 "메커니즘 없음"으로 적고 있었다.
          비운 것은 요구를 낮춘 것이 아니다 — 그 넷은 이제 `FK_PROVEN` 의 실증 대상이다.
        """
        actual_unisolated = {
            f"{t.app_label}.{t.model_name}" for t in MODELS
            if not is_group_isolatable(get_model(t))
        }
        new = actual_unisolated - KNOWN_UNISOLATED
        self.assertEqual(
            set(), new,
            f"소유 필드(groups M2M · group FK)가 **아예 없는** 모델이 추가되었습니다: "
            f"{sorted(new)}\nBaseModelWithGroup 을 상속시키십시오. (부록 A / D-108)")
        stale = KNOWN_UNISOLATED - actual_unisolated
        self.assertEqual(
            set(), stale,
            f"KNOWN_UNISOLATED 에 남아 있으나 실제로는 소유 필드가 있는 모델입니다: "
            f"{sorted(stale)}\n틀린 사실을 정본에 두지 마십시오 — 지우십시오.")

    def test_bypass_list_does_not_grow(self) -> None:
        """권한 우회 목록에 항목을 추가하는 것을 막는다 (절대금지 #6 / D-103)."""
        import re
        from pathlib import Path

        src = Path(__file__).resolve().parent.parent / "common" / "base_model.py"
        text = src.read_text(encoding="utf-8")
        match = re.search(r"performance_bypass_models\s*=\s*\[(.*?)\]", text, re.S)
        current = set(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))) if match else set()

        business = {"order", "orderitem", "orderhistory", "payment",
                    "ordercomment", "orderassignment", "terminal"}
        leftover = current & business
        self.assertEqual(
            set(), leftover,
            f"업무 데이터 모델이 아직 우회 목록에 있습니다: {sorted(leftover)}\n"
            "W0-2 미완. 성능 문제는 인덱스→prefetch→분할→캐시 로 푼다. 우회는 금지다.",
        )


# ═══════════════════════════════════════════════════════════════════════════
# 2) ORM 수준 격리
# ═══════════════════════════════════════════════════════════════════════════

class TenantIsolationORMTest(TenantFixtureMixin, TestCase):
    """매니저가 다른 테넌트의 레코드를 돌려주지 않는지 본다."""

    def test_list_excludes_other_tenant(self) -> None:
        failures = []
        for target in MODELS:
            model = get_model(target)
            if not is_group_isolatable(model):
                continue  # 2) 는 격리 가능한 모델만. 나머지는 1) 이 잡는다.
            with self.subTest(model=target.label):
                self._create_for(model, self.group_a, self.user_a, target)
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                with acting_as(self.user_a):
                    visible = set(model.objects.values_list("pk", flat=True))
                if obj_b.pk in visible:
                    failures.append(target.label)
                self.assertNotIn(
                    obj_b.pk, visible,
                    f"[{target.label}] userA 의 목록에 tenant-B 레코드가 보입니다.",
                )
        self.assertEqual([], failures)

    def test_null_created_by_is_not_globally_visible(self) -> None:
        """created_by 가 비어 있는 레코드가 전 테넌트에 노출되는지 확인한다.

        CustomManagerGroup 의 필터는 `Q(created_by__isnull=True)` 를 OR 로 포함한다.
        즉 생성자 없는 레코드는 **모든 테넌트에 보인다.** 데이터 마이그레이션이나
        관리 커맨드로 만든 레코드가 여기 해당한다 — 실제 유출 경로다.
        """
        target = next(t for t in MODELS if is_group_isolatable(get_model(t)))
        model = get_model(target)
        self._seq = getattr(self, "_seq", 0) + 1
        with acting_as(self.user_b):
            deps = Deps(self.user_b, self.group_b)
            kwargs = target.factory(deps, self._seq) if target.factory else {}
            orphan = model(**kwargs)
            orphan.created_by = None
            orphan.save()
            # 소유를 붙이는 모양이 둘이다 (D-271 술어 확장). M2M 만 가정하면
            # FK 모델에서 AttributeError 로 죽는다 — 술어를 넓힌 뒤 실측으로 드러났다.
            if has_group_m2m(model):
                orphan.groups.set([self.group_b])
            else:
                orphan.group = self.group_b
                orphan.save(update_fields=["group"])
        with acting_as(self.user_a):
            visible = set(model.objects.values_list("pk", flat=True))
        self.assertNotIn(
            orphan.pk, visible,
            f"[{target.label}] created_by 가 NULL 인 tenant-B 레코드가 userA 에게 보입니다. "
            "CustomManagerGroup 의 Q(created_by__isnull=True) 가 원인입니다.",
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3) HTTP 수준 격리 — 5시나리오
# ═══════════════════════════════════════════════════════════════════════════

class TenantIsolationAPITest(TenantFixtureMixin, TestCase):
    """list / detail / update / delete / export 를 userA 로 호출해 B 를 못 보게 한다.

    ★ 2026-08-22 (D-253): **단언은 무변경.** 부르는 경로·메서드·인증만 실측대로 고쳤다.
      라우트가 실재하지 않는 칸은 `NO_ROUTE` 에 사유와 함께 등재되고, 그 집합이 늘면
      `NoRouteRegistryTest` 가 실패한다 — "없어서 건너뜀"이 조용히 늘어나는 것을 막는다.
    """

    FORBIDDEN = (403, 404)

    def setUp(self) -> None:
        self.client_a = Client()
        self.auth_a = self._bearer(self.user_a)

    def _payload(self, route: Route):
        """요청 본문과 content-type. 본문 값은 **tenant-A 가 만든 유효한 값**이다."""
        from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

        body = route.body
        if callable(body):
            # 공격자(tenant-A)가 **자기 것**으로 만든 유효한 값을 보낸다.
            # 같은 시험 안에서는 같은 Deps 를 쓴다 — 새로 만들면 code UNIQUE 에 걸린다.
            with acting_as(self.user_a):
                body = body(self._deps_for(self.user_a, self.group_a))
        if route.form:
            return encode_multipart(BOUNDARY, body or {}), MULTIPART_CONTENT
        return json.dumps(body or {}), "application/json"

    class _Crashed:
        """핸들러가 예외로 죽었을 때의 응답 대역. 상태코드는 500 으로 본다.

        왜 예외를 삼키지 않고 **판정으로 바꾸나**
            Django 테스트 클라이언트는 뷰의 미포착 예외를 그대로 다시 던진다.
            그러면 `subTest` 루프가 **그 자리에서 끝나고 뒤의 모델은 아예 호출되지 않는다** —
            실측: `orders.Order` 상세가 `DoesNotExist` 로 죽어 그 뒤 FlightLog·VideoAnalysis 가
            판정에 도달하지 못했다. 앞의 한 건이 뒤의 전부를 가린 것이다.
            그 상태에서 "실패 1건"이라는 보고는 **커버리지 착시**다.

            그래서 예외를 500 응답으로 바꿔 기록한다. 500 은 (403, 404) 가 아니므로
            **단언은 그대로 실패한다** — 판정이 느슨해지지 않는다. 달라지는 것은
            "뒤의 모델도 판정된다"는 것뿐이다.
        """

        def __init__(self, exc: BaseException):
            self.status_code = 500
            self.exc = exc
            self.content = f"{type(exc).__name__}: {exc}".encode("utf-8", "replace")

    @staticmethod
    def _leak_markers(obj) -> tuple[list[str], bool]:
        """응답 본문에서 **이 레코드**를 찾아낼 문자열들과, 그것이 확정적인지.

        ★ `"id":N` 하나만 보면 안 된다 — 두 방향으로 틀린다:
          · **오탐**: 실측에서 `"id":1` 이 최상위 대시보드가 아니라 중첩된
            `"panels":[{"id":1,…}]` 에 맞았다. 그걸 누출이라 적으면 사람은 곧
            이 시험을 안 믿게 된다.
          · **누락**: 응답에 공백이 있으면(`"id": 1`) 부분 문자열 검사가 놓친다.
            기존 `test_list_api` 의 `assertNotContains` 가 그 모양이었다.

        그래서 **픽스처가 심어 둔 고유값**(iso- 로 시작하는 이름·코드)을 우선한다.
        그런 값이 없는 모델에서만 `"id":N` 으로 떨어지고, 그때는 확정적이지 않음을
        함께 돌려준다 — 판정이 그 사실을 알고 쓰게 하려는 것이다.
        """
        distinctive = []
        for attr in ("code", "name", "order_code", "task_id", "item_name",
                     "description", "serial_number"):
            val = getattr(obj, attr, None)
            if isinstance(val, str) and val.lower().startswith("iso"):
                distinctive.append(val)
        if distinctive:
            return distinctive, True
        return [f'"id":{obj.pk}'], False

    @staticmethod
    def _structural_hit(obj, body: str):
        """본문을 **파싱해서** 이 레코드로 보이는 객체를 찾는다.

        ★ 왜 문자열 검색으로는 안 되나 — 실측이 두 번 가르쳐 줬다:
          · `"id":1` 이 최상위 항목이 아니라 중첩된 `"panels":[{"id":1,…}]` 에 맞았다
          · `"id":3` 이 handover **문서**가 아니라 그 안의 **교대(shift)** 에 맞았다
          둘 다 "누출"로 보고됐고 둘 다 아니었다. 추측으로 빨간불을 켜면
          사람은 곧 이 시험을 안 믿게 되고, 안 믿는 시험은 꺼진 시험과 같다.

        그래서 **id 가 같은 것만으로는 세지 않는다.** 같은 dict 안에 그 모델의
        필드 이름이 둘 이상 함께 있어야 그 모델의 직렬화로 본다.
        """
        try:
            doc = json.loads(body)
        except Exception:                       # noqa: BLE001 — JSON 이 아니면 구조로 못 본다
            return None
        field_names = {f.name for f in type(obj)._meta.get_fields()} - {"id", "pk"}
        found = []

        def walk(node, path="$"):
            if isinstance(node, dict):
                if node.get("id") == obj.pk:
                    shared = (set(node) & field_names) | {
                        k[:-3] for k in node if k.endswith("_id") and k[:-3] in field_names}
                    if len(shared) >= 2:
                        found.append((path, sorted(shared)[:6]))
                for k, v in node.items():
                    walk(v, f"{path}.{k}")
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, f"{path}[{i}]")

        walk(doc)
        return found[0] if found else None

    @classmethod
    def _find_leak(cls, obj, body: str):
        """본문에서 이 레코드를 찾으면 `(맞은 근거, 문맥)`, 없으면 None."""
        marks, decisive = cls._leak_markers(obj)
        flat = body.replace(" ", "")
        if decisive:
            # 픽스처가 심은 고유값 — 이것이 맞으면 다툴 여지가 없다
            for m in marks:
                if m and m in flat:
                    at = flat.index(m)
                    return m, flat[max(0, at - 80):at + 80]
            return None
        # 고유값이 없는 모델 — **구조로** 확인한다 (id 일치만으로는 세지 않는다)
        hit = cls._structural_hit(obj, body)
        if hit:
            path, shared = hit
            return f"id={obj.pk} @ {path} (필드 {shared})", flat[:160]
        return None

    @staticmethod
    def _url_key(obj, target: Target):
        """URL 에 넣을 식별자. 대개 pk 이지만 업무 키인 경우가 있다 (`pk_attr`)."""
        return getattr(obj, target.pk_attr)

    def _call(self, method: str, path: str, **kwargs):
        try:
            return self.client_a.generic(method, path, **kwargs, **self.auth_a)
        except Exception as exc:               # noqa: BLE001 — 판정으로 바꾼다
            return self._Crashed(exc)

    # ------------------------------------------------------------------ 대상
    def _scenario_targets(self, attr: str):
        """그 시나리오의 라우트가 실재하는 대상만 준다.

        경로가 없으면 `NO_ROUTE` 에 등재돼 있어야 한다. 등재 없이 비어 있으면
        아래 `_assert_declared` 가 실패한다 — 조용한 누락을 막는 장치다.
        """
        out = []
        for target in MODELS:
            route = target.list_path if attr == "list" else getattr(target, attr)
            if route:
                out.append((target, route))
            else:
                self._assert_declared(target, attr)
        return out

    def _assert_declared(self, target: Target, attr: str) -> None:
        """칸이 비었으면 **왜 비었는지**가 어딘가에 적혀 있어야 한다.

        ★ D-272 이후 사유는 두 곳에서 온다:
          · `reach != "direct_pk"` — 자기 pk 경로가 애초에 없다는 **분류**가 사유다.
            그 대신 `via_parent` 시나리오가 친다. 이쪽을 NO_ROUTE 에 또 적으면
            면제 대장이 분류를 베껴 쓰는 꼴이 되고, 그러면 대장의 수가 뜻을 잃는다.
          · `reach == "direct_pk"` — 자기 pk 경로가 **있는데** 이 칸만 없는 경우다.
            그건 진짜 누락이므로 NO_ROUTE 에 사유와 함께 등재해야 한다.
        """
        if target.reach != "direct_pk":
            self.assertIsNotNone(
                CENSUS.get(f"{target.app_label}.{target.model_name}"),
                f"[{target.label}] reach={target.reach} 인데 인구조사에 없습니다.")
            return
        key = f"{target.label}:{attr}"
        self.assertIn(
            key, NO_ROUTE,
            f"[{key}] 라우트가 없는데 사유가 등재되지 않았습니다. "
            "Target 에 실제 라우트를 적거나, NO_ROUTE 에 **사유와 함께** 등재하십시오.")

    def test_list_api(self) -> None:
        for target, path in self._scenario_targets("list"):
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self.client_a.get(path, **self.auth_a)
                if res.status_code == 404:
                    self.fail(
                        f"[{target.label}] 목록 경로 {path} 가 404 입니다. "
                        "Target.list_path 를 실제 라우트로 고치십시오."
                    )
                # 옛 판은 `assertNotContains(res, '"id":N')` 이었다. 그 검사는
                # 공백 있는 응답(`"id": N`)을 **놓치고**, 중첩 객체의 id 에 **잘못 맞는다.**
                # 픽스처가 심은 고유값을 우선해 둘 다 없앤다.
                found = self._find_leak(obj_b, res.content.decode("utf-8", "replace"))
                self.assertIsNone(
                    found,
                    f"[{target.label}] 목록에 tenant-B 레코드가 보입니다: {found}")

    def _report(self, name: str, rows: list[tuple[str, int, str]]) -> None:
        """대상별 판정을 **표로** 남기고, 새는 것 전부를 한 번에 단언한다.

        ★ 왜 표인가 — subTest 만으로는 앞의 실패가 뒤를 가린다. 실측: `orders.Order` 상세가
          죽으면서 그 뒤 FlightLog·VideoAnalysis 가 판정에 도달했는지조차 알 수 없었다.
          "실패 1건"이라는 보고가 실제로는 "1건 실패 + N건 미측정"이었던 것이다.
          **미측정을 통과로 읽는 것이 이 저장소가 반복해서 만난 실패 모양이다.**
        """
        print(f"\n[ISO] {name} — 대상 {len(rows)}건")
        for label, status, note in rows:
            mark = "OK  " if status in self.FORBIDDEN else "LEAK"
            print(f"  {mark} {label:26} {status}  {note}")
        leaks = [f"{label}({status})" for label, status, _ in rows
                 if status not in self.FORBIDDEN]
        self.assertEqual(
            [], leaks,
            f"{name}: 남의 테넌트 레코드에 {self.FORBIDDEN} 가 아닌 응답을 준 대상 — {leaks}")

    def test_detail_api(self) -> None:
        rows: list[tuple[str, int, str]] = []
        for target, route in self._scenario_targets("detail"):
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self._call(route.method, route.for_pk(self._url_key(obj_b, target)))
                rows.append((target.label, res.status_code, str(getattr(res, "exc", ""))[:60]))
        self._report("detail", rows)

    def test_update_api(self) -> None:
        rows: list[tuple[str, int, str]] = []
        for target, route in self._scenario_targets("update"):
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                before = model._base_manager.filter(pk=obj_b.pk).values().first()
                data, content_type = self._payload(route)
                res = self._call(route.method, route.for_pk(self._url_key(obj_b, target)),
                                 data=data, content_type=content_type)
                rows.append((target.label, res.status_code, str(getattr(res, "exc", ""))[:60]))
                after = model._base_manager.filter(pk=obj_b.pk).values().first()
                self.assertEqual(before, after, f"[{target.label}] DB 가 변경되었습니다.")
        self._report("update", rows)

    def test_delete_api(self) -> None:
        rows: list[tuple[str, int, str]] = []
        for target, route in self._scenario_targets("delete"):
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self._call(route.method, route.for_pk(self._url_key(obj_b, target)))
                rows.append((target.label, res.status_code, str(getattr(res, "exc", ""))[:60]))
                # ★ `objects` 가 아니라 `_base_manager` 로 묻는다 (D-253 배선).
                #   `objects` 는 테넌트 필터를 타므로 "삭제됐다"와 "내게 안 보인다"를
                #   구별하지 못한다 — 남의 레코드는 항상 안 보이므로 **삭제되지 않았는데도**
                #   삭제된 것으로 판정됐다. 판정을 사실에 맞춘다(더 엄격해진다).
                self.assertTrue(
                    model._base_manager.filter(pk=obj_b.pk).exists(),
                    f"[{target.label}] 레코드가 삭제되었습니다.",
                )
        self._report("delete", rows)

    def test_detector_can_see_own_records(self) -> None:
        """★ **양성 대조** — 탐지기가 *있는 것*을 찾을 수 있는가.

        누출 0건이라는 보고는 두 가지를 뜻할 수 있다:
          (가) 정말 안 샌다
          (나) **탐지기가 눈이 멀었다**

        둘을 가르지 않으면 초록은 아무것도 증명하지 않는다 — 이번 턴에만
        문자열 검사가 두 번 오탐하고(중첩 panels·shift), 한 번 누락했다(공백 `"id": 3`).
        그래서 **자기 테넌트의 레코드는 반드시 찾아내야 한다**고 못 박는다.
        여기가 빨개지면 같은 시나리오의 "누출 0" 은 **판정 불가**로 읽어야 한다.
        """
        blind: list[str] = []
        seen: list[str] = []
        for target in MODELS:
            if not target.list_path:
                continue
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_a = self._create_for(model, self.group_a, self.user_a, target)
                res = self.client_a.get(target.list_path, **self.auth_a)
                if res.status_code != 200:
                    blind.append(f"{target.label}(목록 {res.status_code})")
                    continue
                found = self._find_leak(
                    obj_a, res.content.decode("utf-8", "replace"))
                (seen if found else blind).append(target.label)
        print(f"\n[ISO] 탐지기 양성 대조 — 자기 레코드를 찾음 {len(seen)} · "
              f"못 찾음 {len(blind)}")
        if blind:
            print("      못 찾은 대상(그 시나리오의 '누출 0' 은 판정 불가다): "
                  + ", ".join(blind))
        self.assertTrue(
            seen,
            "탐지기가 자기 테넌트 레코드조차 하나도 못 찾았습니다 — "
            "이 시험의 '누출 0' 은 아무것도 증명하지 않습니다.")

    def test_via_parent_api(self) -> None:
        """D-272 — 부모를 통해 노출되는 모델은 **둘 다** 친다.

        ① **부모 경로 스코프** — 남의 부모를 지목하면 막혀야 한다
        ② **자식 필터** — 설령 부모 경로가 열려 있어도, 응답 본문에 **남의 자식이
           들어 있으면 안 된다**

        왜 둘인가: 부모만 막으면 목록형 경로가 남고, 자식만 보면 부모의 pk 로 들어오는
        길이 남는다. "직접 경로가 없다"는 안전이 아니다 — 그것이 D-272 의 문장이다.
        """
        rows: list[tuple[str, int, str]] = []
        child_leaks: list[str] = []
        for target in MODELS:
            if target.reach != "via_parent":
                continue
            # 부모 pk 경로가 없으면 **목록 경로**로 자식 필터를 본다.
            # via_parent 인데 아무 데도 안 치면 그 분류는 "안 봤다"와 같아진다.
            route = target.via_parent or (
                Route("GET", target.list_path) if target.list_path else None)
            self.assertIsNotNone(
                route,
                f"[{target.label}] reach=via_parent 인데 칠 경로가 없습니다 — "
                "부모 경로나 목록 경로 중 하나는 있어야 분류가 뜻을 갖습니다.")
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                if target.parent_pk is not None:
                    ppk = target.parent_pk(obj_b)
                    self.assertIsNotNone(
                        ppk, f"[{target.label}] 부모 pk 를 꺼내지 못했습니다.")
                    path = route.for_pk(ppk)
                else:
                    path = route.path                    # 목록형 — {pk} 가 없다
                res = self._call(route.method, path)
                body = getattr(res, "content", b"").decode("utf-8", "replace")

                # ① 부모 pk 를 지목한 경우에만 **막혀야 한다.**
                #   목록형 경로에 200 은 정상이다 — 거기서 묻는 것은 상태가 아니라 **본문**이다.
                #   둘을 같은 칸에서 세면 목록의 정상 200 이 누출로 보고된다(첫 판이 그랬다).
                if target.parent_pk is not None:
                    rows.append((target.label, res.status_code,
                                 str(getattr(res, "exc", ""))[:50]))
                else:
                    note = "목록형 — 상태는 200 이 정상. 본문만 본다"
                    rows.append((target.label + "(목록)", 404, note))

                # ② 자식 필터 — 본문에 남의 자식이 들어 있으면 그 자체가 누출이다.
                found = self._find_leak(obj_b, body)
                if found:
                    hit, ctx = found
                    child_leaks.append(f"{target.label}(자식 {hit} @ {path})  …{ctx}…")
        self._report("via_parent(부모 경로 스코프)", rows)
        self.assertEqual(
            [], child_leaks,
            f"부모 경로 응답에 **남의 자식 레코드**가 들어 있습니다: {child_leaks}\n"
            "부모를 막지 못했거나 자식 필터가 없습니다 (D-272).")

    def test_reach_matches_census(self) -> None:
        """레지스트리의 `reach` 와 인구조사가 **같은 말을 하는가**.

        두 곳이 다른 말을 하면 어느 쪽도 못 믿는다 — D-227(manifest 유실)이 만든 상태다.
        """
        bad = []
        for target in MODELS:
            label = f"{target.app_label}.{target.model_name}"
            entry = CENSUS.get(label)
            if entry is None:
                continue
            if entry[1] != target.reach:
                bad.append(f"{label}: 레지스트리={target.reach} 인구조사={entry[1]}")
        self.assertEqual(
            [], bad,
            f"도달 가능성이 두 곳에서 다릅니다:\n" + f"\n".join(bad))

    def test_export(self) -> None:
        for target in MODELS:
            if not target.export_path:
                continue
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self.client_a.get(target.export_path, **self.auth_a)
                body = res.content.decode("utf-8", "replace")
                self.assertNotIn(
                    str(obj_b.pk), body,
                    f"[{target.label}] 내보내기 결과에 tenant-B 데이터가 포함됩니다.",
                )


# ═══════════════════════════════════════════════════════════════════════════
# 4) 면제 대장 증가 금지 — "없어서 건너뜀"이 늘어나는 것을 막는다
# ═══════════════════════════════════════════════════════════════════════════

class NoRouteRegistryTest(TestCase):
    """`NO_ROUTE` 는 **줄어들기만** 해야 한다 (D-253 A안의 조건).

    경로가 없는 칸을 조용히 건너뛰면 "5/5 초록"이 실제 커버리지보다 커 보인다.
    그래서 사유를 요구하고, 개수의 상한을 못 박는다.
    """

    #: 2026-08-22 배선 정정 시점의 실측값 — **레지스트리 10종일 때의 총합**이다.
    #: 아래 `PER_LABEL` 로 대체됐으나 그 시점의 수를 지우지 않는다 (무엇이 바뀌었는지 남긴다).
    BASELINE = 16

    #: ★ **레이블별 증가금지 래칫** (2026-08-27 · W0-14c).
    #:
    #: 왜 전역 총합을 버렸나 — D-262 ② 가 P0 전수 등재를 EXIT 조건으로 걸었다.
    #: 레지스트리가 10종에서 늘면 "라우트 없는 칸"도 함께 는다. 그것은 **새로 생긴 누락이
    #: 아니라 새로 보이게 된 누락**이다. 그런데 전역 상한 16 은 그 등재 자체를 막는다 —
    #: 즉 **EXIT 조건을 지키려면 게이트를 꺼야 하는** 구조였다.
    #:
    #: 그렇다고 상한만 올리면 그것이야말로 게이트를 끄는 일이다. 그래서 레이블별로 못 박는다.
    #: 이쪽이 **전역 총합보다 엄격하다** — 총합만 보면 한 모델의 증가가 다른 모델의
    #: 감소 뒤에 숨을 수 있고, 그때 "줄었다"는 보고가 나온다.
    #:
    #: 늘리려면 이 표를 고쳐야 하고, 그 diff 가 곧 "왜 늘렸는가"를 묻는 자리가 된다.
    PER_LABEL: dict[str, int] = {
        # ── 2026-08-22 실측 10종분 (합 16 — 위 BASELINE 과 같다) ──────────
        "Order": 2, "StreamMonitor": 3, "Dashboard": 3, "ChecklistSetting": 1,
        "HandoverDocument": 3, "DetectionEvent": 4,
        # ── 2026-08-27 W0-14c P0 등재분 ────────────────────────────────
        "FlightLog": 1,        # update 없음
        "VideoAnalysis": 2,    # update·delete 없음
        # ── 2026-08-28 W0-14c P0 전수 등재분 (direct_pk 만 여기 온다) ──
        # via_parent·no_route 대상은 **분류가 사유**이므로 이 대장에 오지 않는다 (D-272).
        "OrderItem": 2,            # update·delete 없음
        "OrderStatusMapping": 2,   # 수정·삭제가 그룹 단위라 pk 를 못 지목한다
        "TaskStatus": 3,           # list·update·delete 없음
    }

    def test_every_entry_has_a_reason(self) -> None:
        for key, reason in NO_ROUTE.items():
            self.assertTrue(
                reason and reason.strip(),
                f"NO_ROUTE[{key}] 에 사유가 없습니다. 사유 없는 면제는 누락과 구별되지 않습니다.",
            )

    def test_no_route_set_does_not_grow(self) -> None:
        """레이블별로 늘지 않았는가. 총합만 보면 한쪽 증가가 다른 쪽 감소 뒤에 숨는다."""
        from collections import Counter

        actual = Counter(key.partition(":")[0] for key in NO_ROUTE)
        for label, count in sorted(actual.items()):
            allowed = self.PER_LABEL.get(label)
            self.assertIsNotNone(
                allowed,
                f"[{label}] 라우트 없는 시나리오 {count}건이 래칫에 없습니다. "
                "새 대상을 등재했다면 PER_LABEL 에 그 수를 적으십시오 — "
                "적는 행위가 '왜 없어도 되는가'를 묻는 자리입니다.",
            )
            self.assertLessEqual(
                count, allowed,
                f"[{label}] 라우트 없는 시나리오가 늘었습니다 ({allowed} → {count}). "
                "새 모델에 HTTP 표면을 만들거나, 왜 없어도 되는지 사유를 함께 적으십시오.",
            )
        for label, allowed in sorted(self.PER_LABEL.items()):
            if actual.get(label, 0) < allowed:
                print(f"[NO_ROUTE] {label}: {allowed} → {actual.get(label, 0)} 로 줄었다 "
                      f"— PER_LABEL 을 낮춰라")

    def test_legacy_baseline_still_holds(self) -> None:
        """2026-08-22 의 10종분 총합 16 은 그대로여야 한다.

        레이블별 래칫으로 바꾸면서 **옛 수가 조용히 늘어나지 않았음**을 따로 증명한다.
        표의 형태를 바꾼 커밋이 동시에 수를 늘리는 것이 가장 알아채기 어려운 후퇴다.
        """
        legacy = {"Order", "StreamMonitor", "Dashboard", "ChecklistSetting",
                  "HandoverDocument", "DetectionEvent"}
        total = sum(1 for key in NO_ROUTE if key.partition(":")[0] in legacy)
        self.assertLessEqual(
            total, self.BASELINE,
            f"2026-08-22 10종분의 라우트 없음이 {self.BASELINE} → {total} 로 늘었습니다.",
        )

    def test_keys_refer_to_registered_targets(self) -> None:
        labels = {t.label for t in MODELS}
        scenarios = {"list", "detail", "update", "delete"}
        for key in NO_ROUTE:
            label, _, scenario = key.partition(":")
            self.assertIn(label, labels, f"NO_ROUTE[{key}] 의 대상이 레지스트리에 없습니다.")
            self.assertIn(scenario, scenarios, f"NO_ROUTE[{key}] 의 시나리오 이름이 틀렸습니다.")
