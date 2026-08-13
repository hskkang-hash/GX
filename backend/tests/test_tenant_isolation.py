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
class Target:
    """격리 검증 대상 1건."""

    label: str
    app_label: str
    model_name: str
    #: 목록/상세 API 접두사. None 이면 API 시나리오는 건너뛰고 ORM 만 본다.
    api_base: str | None = None
    #: 레코드 1건을 만드는 데 필요한 최소 필드
    factory_kwargs: dict[str, Any] = field(default_factory=dict)
    #: 내보내기 엔드포인트 (있으면 test_export 대상)
    export_path: str | None = None


#: W0-3 지시서가 지정한 9종.
#: `Handover` 라는 이름의 모델은 존재하지 않는다 — handover 앱의 실제 최상위 모델은
#: HandoverDocument 다. 지시서의 이름이 아니라 실재하는 모델로 등록한다.
MODELS: tuple[Target, ...] = (
    Target("Order",               "orders",            "Order",               "/api/orders/"),
    Target("Terminal",            "terminals",         "Terminal",            "/api/terminals/"),
    Target("StreamMonitor",       "stream_monitors",   "StreamMonitor",       "/api/stream-monitors/"),
    Target("Dashboard",           "dashboard",         "Dashboard",           "/api/dashboard/"),
    Target("Device",              "devices",           "Device",              "/api/devices/"),
    Target("ChecklistSetting",    "checklist_setting", "ChecklistSetting",    "/api/checklist-setting/"),
    Target("SurveillanceProfile", "surveillance",      "SurveillanceProfile", "/api/surveillance/"),
    Target("HandoverDocument",    "handover",          "HandoverDocument",    "/api/handover/"),
    Target("ReportTemplate",      "report_template",   "ReportTemplate",      "/api/report-template/"),

    # W2-1 에서 신설. BaseModelWithGroup 상속 — group 격리 대상이다.
    Target("DetectionEvent",      "stream_monitors",   "DetectionEvent",      "/api/stream-monitors/"),
)

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


@contextlib.contextmanager
def acting_as(user):
    """매니저가 보는 '현재 요청'을 주어진 사용자로 바꾼다.

    CustomManagerGroup 은 thread-local 요청에서 user 를 읽는다.
    common.base_model 은 `from ... import get_current_request` 로 함수를 직접
    바인딩하므로 원본 모듈만 패치하면 반영되지 않는다. 둘 다 패치한다.
    """
    request = mock.Mock()
    request.user = user
    targets = [
        "common.base_model.get_current_request",
        "core.middleware.refresh_token.get_current_request",
    ]
    with contextlib.ExitStack() as stack:
        for dotted in targets:
            with contextlib.suppress(ModuleNotFoundError, AttributeError):
                stack.enter_context(mock.patch(dotted, return_value=request))
        yield request


class TenantFixtureMixin:
    """group A/B 사용자와 각 group 소유 레코드를 만든다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        CoreUser = apps.get_model("user", "CoreUser")
        UserGroup = apps.get_model("user", "UserGroup")

        cls.group_a = UserGroup.objects.create(name="tenant-A")
        cls.group_b = UserGroup.objects.create(name="tenant-B")
        cls.user_a = cls._make_user("user_a", cls.group_a)
        cls.user_b = cls._make_user("user_b", cls.group_b)

    @classmethod
    def _make_user(cls, username: str, group):
        """CoreUser 를 만들고 group 에 소속시킨다.

        UserProfileLink 의 정확한 모듈 경로·필드명은 dj-core 안에 있어
        저장소에서 읽을 수 없다. 관계 이름(`userprofilelink`)으로 역참조해
        런타임에 모델을 찾는다 — 사내 패키지 버전이 바뀌어도 깨지지 않는다.
        """
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True
        )
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_model = link_field.related_model
        link_model.objects.create(**{link_field.remote_field.name: user, "group": group})
        return user

    @classmethod
    def _create_for(cls, model: type[models.Model], group, owner, target: Target):
        """`group` 소유 레코드 1건. 필수 필드는 target.factory_kwargs 로 채운다."""
        with acting_as(owner):
            obj = model(**target.factory_kwargs)
            obj.created_by = owner
            obj.save()
            if is_group_isolatable(model):
                obj.groups.set([group])
        return obj


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
        with acting_as(self.user_b):
            orphan = model(**target.factory_kwargs)
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
    """list / detail / update / delete / export 를 userA 로 호출해 B 를 못 보게 한다."""

    FORBIDDEN = (403, 404)

    def setUp(self) -> None:
        self.client_a = Client()
        self.client_a.force_login(self.user_a)

    def _targets(self):
        return [t for t in MODELS if t.api_base]

    def test_list_api(self) -> None:
        for target in self._targets():
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self.client_a.get(target.api_base)
                if res.status_code == 404:
                    self.fail(
                        f"[{target.label}] 목록 경로 {target.api_base} 가 404 입니다. "
                        "Target.api_base 를 실제 라우트로 고치십시오."
                    )
                self.assertNotContains(res, f'"id":{obj_b.pk}', msg_prefix=target.label)

    def test_detail_api(self) -> None:
        for target in self._targets():
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self.client_a.get(f"{target.api_base}{obj_b.pk}/")
                self.assertIn(res.status_code, self.FORBIDDEN, msg=target.label)

    def test_update_api(self) -> None:
        for target in self._targets():
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                before = model.objects.db_manager().filter(pk=obj_b.pk).values().first()
                res = self.client_a.patch(
                    f"{target.api_base}{obj_b.pk}/",
                    data="{}", content_type="application/json",
                )
                self.assertIn(res.status_code, self.FORBIDDEN, msg=target.label)
                after = model.objects.db_manager().filter(pk=obj_b.pk).values().first()
                self.assertEqual(before, after, f"[{target.label}] DB 가 변경되었습니다.")

    def test_delete_api(self) -> None:
        for target in self._targets():
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self.client_a.delete(f"{target.api_base}{obj_b.pk}/")
                self.assertIn(res.status_code, self.FORBIDDEN, msg=target.label)
                self.assertTrue(
                    model.objects.db_manager().filter(pk=obj_b.pk).exists(),
                    f"[{target.label}] 레코드가 삭제되었습니다.",
                )

    def test_export(self) -> None:
        for target in self._targets():
            if not target.export_path:
                continue
            model = get_model(target)
            with self.subTest(model=target.label):
                obj_b = self._create_for(model, self.group_b, self.user_b, target)
                res = self.client_a.get(target.export_path)
                body = res.content.decode("utf-8", "replace")
                self.assertNotIn(
                    str(obj_b.pk), body,
                    f"[{target.label}] 내보내기 결과에 tenant-B 데이터가 포함됩니다.",
                )
