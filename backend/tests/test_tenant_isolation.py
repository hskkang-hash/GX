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
        "StreamMonitor", "stream_monitors", "StreamMonitor",
        list_path="/api/stream-monitors/stream-monitors",
        factory=lambda d, n: {
            "name": f"iso-monitor-{n}", "code": f"ISO-MON-{n}",
            "ip_source": "rtsp://iso.invalid/stream",
        },
    ),
    Target(
        "Dashboard", "dashboard", "Dashboard",
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
        "HandoverDocument", "handover", "HandoverDocument",
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

    # W2-1 에서 신설. BaseModelWithGroup 상속 — group 격리 대상이다.
    # HTTP 표면은 아직 없다 (W2-2 가 만든다) — 그래서 전 시나리오가 NO_ROUTE 다.
    Target(
        "DetectionEvent", "stream_monitors", "DetectionEvent",
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
}

#: 격리 메커니즘이 **아직 없는** 모델 (2026-08-13 실측).
#: 이 집합이 늘어나면 test_unisolated_set_has_not_grown 이 실패한다 —
#: 격리 없는 모델을 새로 들이는 것을 막는 장치다. 줄어드는 것은 환영이다.
KNOWN_UNISOLATED: frozenset[str] = frozenset({
    "orders.Order",              # core.base.BaseModel — groups 필드 없음
    "devices.Device",            # core.base.BaseModel — groups 필드 없음
    "report_template.ReportTemplate",  # core.base.BaseModel — groups 필드 없음
    "handover.HandoverDocument",       # core.base.BaseModel — groups 필드 없음
})


# ═══════════════════════════════════════════════════════════════════════════
# 헬퍼
# ═══════════════════════════════════════════════════════════════════════════

def get_model(target: Target) -> type[models.Model]:
    return apps.get_model(target.app_label, target.model_name)


def is_group_isolatable(model: type[models.Model]) -> bool:
    """`groups` M2M 을 가진 모델만 group 격리를 받을 수 있다."""
    return any(f.name == "groups" for f in model._meta.get_fields())


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
        if is_group_isolatable(model):
            obj.groups.set([self.group])
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
            if is_group_isolatable(model):
                obj.groups.set([group])
        return obj

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

    def test_registry_covers_all_isolatable_models(self) -> None:
        registered = {f"{t.app_label}.{t.model_name}" for t in MODELS}
        missing = []
        for model in apps.get_models():
            if not is_group_isolatable(model):
                continue
            label = f"{model._meta.app_label}.{model.__name__}"
            if model._meta.app_label in {"user", "core"}:
                continue  # dj-core 프레임워크 모델은 §0.4 금지구역
            if label not in registered:
                missing.append(label)
        self.assertEqual(
            [], sorted(missing),
            "group 격리 대상 모델이 이 테스트에 등록되지 않았습니다.\n"
            "MODELS 레지스트리에 Target(...) 을 추가하십시오. (W0-3 머지 규칙)",
        )

    def test_unisolated_set_has_not_grown(self) -> None:
        """격리 메커니즘 없는 모델이 새로 늘지 않았는지 확인한다."""
        actual_unisolated = set()
        for target in MODELS:
            model = get_model(target)
            if not is_group_isolatable(model):
                actual_unisolated.add(f"{target.app_label}.{target.model_name}")
        new = actual_unisolated - KNOWN_UNISOLATED
        self.assertEqual(
            set(), new,
            f"격리 메커니즘(groups M2M) 없는 모델이 새로 추가되었습니다: {sorted(new)}\n"
            "BaseModelWithGroup 을 상속시키십시오. (부록 A / D-108)",
        )

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
            orphan.groups.set([self.group_b])
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
        key = f"{target.label}:{attr}"
        self.assertIn(
            key, NO_ROUTE,
            f"[{key}] 라우트가 없는데 사유가 등재되지 않았습니다. "
            "Target 에 실제 라우트를 적거나, NO_ROUTE 에 **사유와 함께** 등재하십시오.",
        )

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
                self.assertNotContains(res, f'"id":{obj_b.pk}', msg_prefix=target.label)

    def test_detail_api(self) -> None:
        for target, route in self._scenario_targets("detail"):
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self.client_a.generic(
                    route.method, route.for_pk(obj_b.pk), **self.auth_a
                )
                self.assertIn(res.status_code, self.FORBIDDEN, msg=target.label)

    def test_update_api(self) -> None:
        for target, route in self._scenario_targets("update"):
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                before = model._base_manager.filter(pk=obj_b.pk).values().first()
                data, content_type = self._payload(route)
                res = self.client_a.generic(
                    route.method, route.for_pk(obj_b.pk),
                    data=data, content_type=content_type, **self.auth_a
                )
                self.assertIn(res.status_code, self.FORBIDDEN, msg=target.label)
                after = model._base_manager.filter(pk=obj_b.pk).values().first()
                self.assertEqual(before, after, f"[{target.label}] DB 가 변경되었습니다.")

    def test_delete_api(self) -> None:
        for target, route in self._scenario_targets("delete"):
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self.client_a.generic(
                    route.method, route.for_pk(obj_b.pk), **self.auth_a
                )
                self.assertIn(res.status_code, self.FORBIDDEN, msg=target.label)
                # ★ `objects` 가 아니라 `_base_manager` 로 묻는다 (D-253 배선).
                #   `objects` 는 테넌트 필터를 타므로 "삭제됐다"와 "내게 안 보인다"를
                #   구별하지 못한다 — 남의 레코드는 항상 안 보이므로 **삭제되지 않았는데도**
                #   삭제된 것으로 판정됐다. 판정을 사실에 맞춘다(더 엄격해진다).
                self.assertTrue(
                    model._base_manager.filter(pk=obj_b.pk).exists(),
                    f"[{target.label}] 레코드가 삭제되었습니다.",
                )

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

    #: 2026-08-22 배선 정정 시점의 실측값. **늘리지 말 것.** 라우트가 생기면 줄인다.
    BASELINE = 16

    def test_every_entry_has_a_reason(self) -> None:
        for key, reason in NO_ROUTE.items():
            self.assertTrue(
                reason and reason.strip(),
                f"NO_ROUTE[{key}] 에 사유가 없습니다. 사유 없는 면제는 누락과 구별되지 않습니다.",
            )

    def test_no_route_set_does_not_grow(self) -> None:
        self.assertLessEqual(
            len(NO_ROUTE), self.BASELINE,
            f"라우트 없는 시나리오가 늘었습니다 ({self.BASELINE} → {len(NO_ROUTE)}). "
            "새 모델에 HTTP 표면을 만들거나, 왜 없어도 되는지 사유를 함께 적으십시오.",
        )

    def test_keys_refer_to_registered_targets(self) -> None:
        labels = {t.label for t in MODELS}
        scenarios = {"list", "detail", "update", "delete"}
        for key in NO_ROUTE:
            label, _, scenario = key.partition(":")
            self.assertIn(label, labels, f"NO_ROUTE[{key}] 의 대상이 레지스트리에 없습니다.")
            self.assertIn(scenario, scenarios, f"NO_ROUTE[{key}] 의 시나리오 이름이 틀렸습니다.")
