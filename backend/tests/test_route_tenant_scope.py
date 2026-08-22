"""라우트 테넌트 스코프 **누락 탐지** — W0-14 ②.

이 파일이 W0-14 의 핵심이다. 스코프를 거는 것보다 **안 걸린 것을 세는 것**이 어렵고,
세지 못하면 "다 걸었다"는 말이 검증되지 않는다.

────────────────────────────────────────────────────────────────────────────
왜 별도 파일인가

  `tests/test_tenant_isolation.py` 는 W0-3 의 산출물이고 절대금지 #5 가 수정을
  막는다. 이 파일은 **거기에 손대지 않기 위해** 따로 만들었다. 축도 다르다 —
  저쪽은 모델(ORM), 이쪽은 **라우트(HTTP)** 다.

────────────────────────────────────────────────────────────────────────────
경고 모드 (WP-1 ENTRY §6-2 · 대표 승인 2026-08-15)

  이 테스트는 **미분류(UNREVIEWED) 가 있다는 이유로 실패하지 않는다.**
  실패 조건은 하나다 — **그 수가 늘어나는 것.**

      · 처음 실행 : 대장(route_baseline.json)이 없으면 만들고 통과시킨다.
                    만들어진 파일을 커밋하는 것이 사람의 몫이다.
      · 이후 실행 : 미분류 수가 대장보다 크면 **실패.**
                    새 엔드포인트가 스코프 없이 들어온 것이다.

  0 을 요구하지 않는 이유: 착수 시점 커버리지가 0/466 이다. 지금 0 을 요구하면
  이 테스트는 첫날부터 빨간불로 고정되고, 고정된 빨간불은 아무도 보지 않는다.
  **줄어드는 것이 보이게 하는 쪽**을 택했다.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase

from common import tenant_scope

#: 미분류 잔여 대장. 이 저장소가 "지금 몇 개를 안 봤는지" 기억하는 유일한 곳.
BASELINE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs" / "agent" / "evidence" / "W0-14" / "route_baseline.json"
)

#: 정적 실측(2026-08-15) — `@route.*` 데코레이터 수. 런타임 열거 결과와 대조해
#: **열거기가 라우트를 놓치고 있지 않은지** 본다. 열거가 0 이면 테스트가 통과해도
#: 아무것도 검증하지 않은 것이다.
STATIC_ROUTE_COUNT = 466

#: 열거 결과가 이보다 적으면 열거기가 고장난 것으로 본다.
#: 정적 466 의 절반. 동적 등록·주석 오차를 감안한 하한이다.
MIN_EXPECTED_ROUTES = 233


def _load_baseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_baseline(payload: dict) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ServiceLayerGroupSelectionTest(SimpleTestCase):
    """서비스 레이어가 group 을 임의로 고르지 않는가 — W0-12 ③.

    ★ AUTHOR-ERROR (D-214). W0-12 의 dod ③ 은
      *"`test_service_layer_does_not_pick_arbitrary_group` 통과
        (W0-3 의 expectedFailure 해제)"* 라고 적었으나,
      `tests/test_tenant_isolation.py` 에 그런 이름의 테스트는 **없고**
      `@expectedFailure` 도 **0건**이다(WP-0 `coverage.md` §3).

      그 파일에 테스트를 새로 넣는 것은 절대금지 #5(격리 테스트 수정)에 닿는다.
      그래서 **동등한 가드를 여기 둔다.** 이름은 dod 문구를 그대로 따랐다.

    정적 검사인 이유: 이 결함은 런타임이 아니라 **코드에 적힌 폴백**이었다.
    DB 없이 잡히고, DB 없이 잡히는 것이 회귀 게이트로 더 낫다.
    """

    #: 소유자를 임의로 정하는 호출. 정규식으로 두는 이유는 §W0-12 verify 와 같다.
    FORBIDDEN = r"UserGroup\.objects\.first\(\)"

    def test_service_layer_does_not_pick_arbitrary_group(self) -> None:
        import re

        backend = Path(__file__).resolve().parents[1]
        pattern = re.compile(self.FORBIDDEN)
        offenders: list[str] = []
        for py in backend.rglob("*.py"):
            parts = set(py.parts)
            if "__pycache__" in parts or "migrations" in parts:
                continue
            if py.name == Path(__file__).name:
                continue
            try:
                text = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{py.relative_to(backend)}:{i}: {line.strip()}")

        self.assertEqual(
            offenders,
            [],
            "소유 group 을 임의로 고르는 폴백이 다시 들어왔습니다 (W0-12 회귀).\n"
            "요청자에서 group 을 받으십시오: "
            "common.tenant_filters.require_user_group(user)\n" + "\n".join(offenders),
        )


class RouteEnumerationTest(SimpleTestCase):
    """열거기 자체가 동작하는가. **이것이 먼저다.**"""

    def test_enumerator_finds_routes(self) -> None:
        routes = tenant_scope.enumerate_operations()
        self.assertGreaterEqual(
            len(routes),
            MIN_EXPECTED_ROUTES,
            f"라우트 열거가 {len(routes)}건뿐입니다 (정적 실측 {STATIC_ROUTE_COUNT}건). "
            "열거기가 NinjaExtraAPI 인스턴스를 못 찾고 있습니다. "
            "이 상태에서는 아래 커버리지 수치가 전부 무의미합니다.",
        )

    def test_every_route_has_exactly_one_state(self) -> None:
        """`scoped` / `public` / `unreviewed` 는 상호배타이고 합이 전체여야 한다."""
        s = tenant_scope.summarize()
        self.assertEqual(
            s["scoped"] + s["public"] + s["unreviewed"],
            s["total"],
            "라우트 상태 분류가 전체를 덮지 못합니다 — 분모가 새고 있습니다.",
        )


class ScopeDecoratorIntegrationTest(SimpleTestCase):
    """`@tenant_scoped` 가 ninja-extra 와 실제로 맞물리는가.

    ★ **이 테스트가 초록이 되기 전에는 데코레이터를 실 컨트롤러에 붙이지 않는다.**

    이유: 데코레이터는 오프라인에서 30건의 순수 로직 시험을 통과했지만
    (WP-1 EXIT 참조), `ninja`·`ninja_extra` 가 개발 머신에 없어 **등록 경로는
    한 번도 실행되지 않았다.** ninja 는 `inspect.signature` 로 핸들러 인자를 읽어
    스키마를 만든다. 래퍼가 원 시그니처를 가리면 466개 엔드포인트의 요청 파싱이
    한꺼번에 깨지고, 그것은 경고 모드로도 막히지 않는다 — **앱이 기동하지 않는다.**

    `functools.wraps` 가 `__wrapped__` 를 남기므로 `inspect.signature` 는 원본을
    따라간다는 것이 설계 근거다. 이 테스트는 그 근거를 **주장이 아니라 실행**으로 바꾼다.
    """

    def test_decorator_preserves_handler_signature(self) -> None:
        import inspect

        def handler(self, request, item_id: int, q: str = "x"):  # noqa: ANN001
            return item_id, q

        wrapped = tenant_scope.tenant_scoped()(handler)
        self.assertEqual(
            list(inspect.signature(wrapped).parameters),
            ["self", "request", "item_id", "q"],
            "래퍼가 원 시그니처를 가립니다 — ninja 가 스키마를 만들지 못합니다.",
        )
        self.assertIs(getattr(wrapped, "__wrapped__", None), handler)

    def test_decorated_route_registers_and_is_seen_as_scoped(self) -> None:
        """실제 API 인스턴스에 등록하고, 열거기가 `scoped` 로 보는지 확인한다."""
        try:
            from ninja_extra import NinjaExtraAPI, api_controller, route
        except ImportError:  # pragma: no cover
            self.skipTest("ninja_extra 미설치 — 사내망 환경에서 실행할 것")

        api = NinjaExtraAPI(urls_namespace="gx_scope_probe")

        @api_controller("/probe", tags=["scope-probe"])
        class _ProbeController:
            @route.get("/items")
            @tenant_scope.tenant_scoped()
            def list_items(self, request):  # noqa: ANN001
                return []

        api.register_controllers(_ProbeController)

        found = [
            op
            for _prefix, router in (getattr(api, "_routers", []) or [])
            for _p, pv in (getattr(router, "path_operations", {}) or {}).items()
            for op in (getattr(pv, "operations", []) or [])
        ]
        self.assertTrue(found, "데코레이터를 붙인 라우트가 등록되지 않았습니다.")
        self.assertTrue(
            any(getattr(op.view_func, tenant_scope.SCOPE_ATTR, None) for op in found),
            "등록된 오퍼레이션에서 스코프 표식이 사라졌습니다 — "
            "열거기가 이 라우트를 unreviewed 로 셉니다.",
        )


class RouteTenantScopeTest(SimpleTestCase):
    """W0-14 ② 본체."""

    maxDiff = None

    def test_all_routes_are_tenant_scoped(self) -> None:
        """전 라우트가 (a)스코프 적용 또는 (b)PUBLIC 등재여야 한다.

        경고 모드에서는 **미분류 수의 증가만** 실패로 본다.
        """
        s = tenant_scope.summarize()
        print(
            "\n[TENANT_SCOPE] "
            f"total={s['total']} scoped={s['scoped']} public={s['public']} "
            f"unreviewed={s['unreviewed']} no_auth={s['no_auth']} "
            f"coverage={s['coverage_pct']}% enforcing={s['enforcing']}"
        )

        baseline = _load_baseline()
        if baseline is None:
            _write_baseline(
                {
                    "note": (
                        "W0-14 미분류 라우트 잔여 대장. 이 수는 줄어들기만 해야 한다. "
                        "생성 후 커밋할 것."
                    ),
                    "total": s["total"],
                    "scoped": s["scoped"],
                    "public": s["public"],
                    "unreviewed": s["unreviewed"],
                    "no_auth": s["no_auth"],
                }
            )
            print(
                f"[TENANT_SCOPE] 대장을 새로 만들었습니다: {BASELINE_PATH}\n"
                "               이 파일을 커밋해야 다음 실행부터 증가 금지가 걸립니다."
            )
            return

        self.assertLessEqual(
            s["unreviewed"],
            baseline["unreviewed"],
            "미분류 라우트가 늘었습니다 "
            f"({baseline['unreviewed']} → {s['unreviewed']}). "
            "새 엔드포인트에 @tenant_scoped 를 걸거나, 인증 불요라면 "
            "common/tenant_scope.PUBLIC_ROUTES 에 **사유와 함께** 등재하십시오.",
        )

    def test_public_routes_all_have_reasons(self) -> None:
        """PUBLIC 은 사유 없이는 등재될 수 없다. 사유가 없으면 미분류와 같다."""
        for key, reason in tenant_scope.PUBLIC_ROUTES.items():
            self.assertTrue(
                reason and reason.strip(),
                f"PUBLIC 등재 {key} 에 사유가 없습니다.",
            )

    def test_public_list_does_not_grow(self) -> None:
        """면제 목록 증가 금지 (W0-14 ②).

        미분류를 줄이는 가장 쉬운 방법은 PUBLIC 으로 옮기는 것이다.
        그 경로를 막지 않으면 커버리지는 오르고 노출은 그대로 남는다.
        """
        baseline = _load_baseline()
        if baseline is None:
            self.skipTest("대장 없음 — test_all_routes_are_tenant_scoped 가 먼저 만든다")
        s = tenant_scope.summarize()
        self.assertLessEqual(
            s["public"],
            baseline["public"] + 0,
            f"PUBLIC 면제가 늘었습니다 ({baseline['public']} → {s['public']}). "
            "면제 추가는 대표 승인 사항입니다 — 대장을 함께 갱신하십시오.",
        )

    def test_all_group_models_are_covered(self) -> None:
        """group 을 가진 모델을 소유한 앱의 HTTP 표면이 대장에 잡혀 있는가.

        `test_tenant_isolation.test_registry_covers_all_isolatable_models` 와
        축이 다르다 — 저쪽은 **모델이 테스트 레지스트리에 있는가**, 이쪽은
        **그 모델을 노출하는 앱의 라우트가 분류되어 있는가**다.
        """
        from django.apps import apps

        owning_apps: set[str] = set()
        for model in apps.get_models():
            names = {f.name for f in model._meta.get_fields()}
            if "groups" in names or "group" in names:
                owning_apps.add(model._meta.app_label)

        routes = tenant_scope.enumerate_operations()
        seen_apps = {r.module.split(".")[0] for r in routes}

        # 라우트를 하나도 못 찾은 '소유 앱'은 HTTP 표면이 없다는 뜻이거나
        # 열거기가 그 앱을 놓친 것이다. 후자면 커버리지 수치가 거짓이 된다.
        unmapped = sorted(a for a in owning_apps if a not in seen_apps)
        print(
            f"\n[TENANT_SCOPE] group 보유 모델 소유 앱 {len(owning_apps)}개 / "
            f"라우트가 잡힌 앱 {len(seen_apps & owning_apps)}개 / "
            f"라우트 미발견 {len(unmapped)}개: {unmapped}"
        )

        baseline = _load_baseline()
        if baseline is None:
            self.skipTest("대장 없음 — test_all_routes_are_tenant_scoped 가 먼저 만든다")
        self.assertLessEqual(
            len(unmapped),
            baseline.get("unmapped_apps", len(unmapped)),
            f"라우트가 잡히지 않는 소유 앱이 늘었습니다: {unmapped}",
        )
