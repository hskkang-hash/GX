# -*- coding: utf-8 -*-
"""F-05 — **외부 App 이 이벤트 OpenAPI 하나로만 들어오는가** (D-309 미측정 해소).

계약 AC 원문: *"외부 App 이 이벤트 OpenAPI **하나로만** 들어온다 (API Key 발급·폐기 포함)"*

이 파일이 왜 생겼나 — **D-309 대장의 유일한 '미측정' 이었다**
--------------------------------------------------------------
F-05 는 구현 여부와 무관하게 **재는 시험이 없었다.** 대장은 그것을 '부분' 이 아니라
'미측정' 으로 적게 했고(증명 없는 칸은 '구현' 으로 못 적는다), 그 한 칸이 이번 관문이 됐다.

무엇을 재는가 — 셋
------------------
  ① **진입면이 하나인가**   L4 App 중 K1 커널을 소비하는 것은 `apps.dsm` **하나뿐**이고,
                            그 App 의 HTTP 진입면은 등재된 10개뿐이다.
  ② **그 진입면이 잠겨 있는가**  전건 인증 + 테넌트 스코프.
  ③ **모양이 안정적인가**   응답 키 집합을 이름으로 고정한다(D-285 ②).

  ★ ①이 **부작위 시험**이다(D-300) — "만든 것" 이 아니라 **"다른 데로 못 들어옴"** 을 잰다.
    AC 의 핵심 단어가 "하나로만" 이므로, 이 AC 는 부작위로만 정확히 잴 수 있다.

무엇을 **못** 재는가 — 정직하게 남긴다
--------------------------------------
**API Key 발급·폐기(FR-05-3)는 저장처가 없다.** 그래서 못 잰다. 다만 그 부재는 조용하지
않다 — `apps.dsm.services.SETTING_DOMAINS['api_keys']` 가 사유와 함께 501 로 나가고,
`test_dsm_app.py::test_unavailable_domains_raise_instead_of_returning_empty` 가 그 갈래를
잰다. 아래 `test_api_key_issuance_is_declared_not_silently_missing` 가 그 선언이 살아
있는지 확인한다 — **없는 것을 없다고 말하는 상태**를 지키는 것이 지금 할 수 있는 전부다.

★ 술어를 먼저 밝힌다 (D-271 ③) — 그리고 **첫 술어는 틀렸다**
------------------------------------------------------------
"이벤트에 닿는 라우트" 를 처음에는 **핸들러 모듈의 소스 + 그 모듈이 끌어들인 우리 모듈**
(2단계 import 폐포)로 셌다. 결과는 662 중 **98건** — `delivery.views.api` 와
`stream_monitors.views.*` 가 전부 잡혔다. 그것들은 이벤트를 만지지 않고, 다만
`stream_monitors.models` 를 끌어들일 뿐이다. **전이 import 근접성은 도달이 아니다.**

빨간불의 뜻이 둘이 되면 그 게이트는 곧 꺼진다(D-295 가 게이트 둘을 나눈 이유).
그래서 술어를 **직접 import** 로 좁혔다: `kernels.k1_event` 를 import 하는 모듈.
실측 결과 라우트를 가진 51개 모듈 중 **0개**이고, K1 소비자는 8개뿐이다(아래 등재).
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from django.test import SimpleTestCase

BACKEND = Path(__file__).resolve().parents[1]
_SKIP_DIRS = {"__pycache__", "migrations", ".venv", "node_modules", "venv"}

# ═══════════════════════════════════════════════════════════════════════════
# 등재부 — **이름으로 잠근다** (D-285 ②). 수가 아니라 이름이다.
# ═══════════════════════════════════════════════════════════════════════════
#: F-05 가 말하는 **그 하나의 진입면.** 재난안전 App 의 HTTP 표면 전부다.
#: 여기 없는 라우트가 `/api/dsm/` 아래 생기면 이 시험이 멈춘다 — 진입면이 둘이 되는
#: 순간을 사람이 아니라 도구가 본다.
EVENT_ENTRY_SURFACE: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/api/dsm/dashboard/frame"),
    ("GET", "/api/dsm/dashboard/link-state"),
    ("GET", "/api/dsm/deliveries"),
    ("GET", "/api/dsm/events"),
    ("GET", "/api/dsm/events/{int:event_id}/clip"),
    ("GET", "/api/dsm/events/{int:event_id}/clip/stream"),
    ("POST", "/api/dsm/events/{int:event_id}/notify"),
    ("GET", "/api/dsm/reports/templates"),
    ("GET", "/api/dsm/reports/{int:template_id}.pdf"),
    ("GET", "/api/dsm/settings/{domain}"),
    # ★ 2026-09-19 **둘이 늘었다 — 그런데 진입면은 넓어지지 않았다** (D-410).
    #   `GET /settings/{domain}` 이 `domain=thresholds` · `domain=zones` 로 이미
    #   서 주던 **바로 그 문**이다: 같은 핸들러(`_setting_overview`) · 같은 문지기
    #   (@tenant_scoped + JwtOrInboundKey + guard_setting) · 같은 응답.
    #   바뀐 것은 **어느 URL 패턴이 그 문을 여는가** 뿐이다.
    #
    #   왜 다시 걸었나: 이 둘은 **설정 영역 이름이면서 동시에 쓰기 경로**다.
    #   `settings/<str:domain>` 이 먼저 등록돼 있는 한 `POST /settings/thresholds`
    #   는 405 였다(Allow: GET). 리터럴을 앞으로 옮기면 이번엔 GET 이 405 가 된다 —
    #   한 경로 = 한 PathView 이므로, **GET 과 POST 를 같은 문에 함께 세우는 것**이
    #   둘 다 사는 유일한 배선이다.
    #
    #   ⚠ 이 두 줄을 지우면 시험이 멈춘다. 멈추면 지우지 말고 **왜 문이 사라졌는지**
    #     를 보라 — 십중팔구 `{domain}` 이 다시 위로 올라간 것이다.
    ("GET", "/api/dsm/settings/thresholds"),
    ("GET", "/api/dsm/settings/zones"),
    # ★ 2026-09-06 추가 (D-325 표 ① · F-02 「지점별 기준선 설정」 · F-12 「임계값」).
    #   진입면이 **하나 늘었다** — 그리고 그것이 이 시험의 값이다: 사람이 아니라 도구가
    #   그 사실을 여기서 멈춰 세웠다. 늘리는 판단은 손으로 이 줄을 더하는 일이고,
    #   그 손이 곧 "진입면을 늘린다"는 선언이다.
    #   문지기: @tenant_scoped + CustomJWTAuth + guard_setting(F-12 감사 전건).
    ("POST", "/api/dsm/settings/thresholds"),
    # ★ 2026-09-10 **다섯이 늘었다** — 계약 절 셋을 갚으면서 (D-365~368).
    #   손으로 이 줄들을 더하는 일이 곧 "진입면을 넓힌다" 는 선언이다.
    #   이 시험이 아니었으면 다섯이 조용히 늘었을 것이고, F-05 의
    #   「이벤트 OpenAPI 하나로만 들어온다」가 소리 없이 약해졌을 것이다.
    #
    #   문지기: 전건 @tenant_scoped + JwtOrInboundKey(키 거절 · 기본값) +
    #           guard_setting(F-12 감사 — 성공·실패 모두)
    #   ★ 다섯 다 **들어오는 키를 받지 않는다.** 특히 api-keys 셋이 그렇다 —
    #     키로 키를 발급받을 수 있으면 키 하나가 영원히 자기를 갱신하고,
    #     그러면 폐기가 폐기가 아니게 된다.
    ("POST", "/api/dsm/settings/zones"),          # F-12 「구역」 (D-366)
    ("POST", "/api/dsm/settings/grade-rules"),    # F-12 「등급규칙」 (D-368)
    ("POST", "/api/dsm/settings/api-keys"),       # F-05 「발급」 (D-367)
    ("DELETE", "/api/dsm/settings/api-keys/{int:key_id}"),         # F-05 「폐기」
    ("POST", "/api/dsm/settings/api-keys/{int:key_id}/rotate"),    # F-05 「회전」
    # ★ 2026-09-14 **하나가 늘었다** — 대응 진행 축(D-399). 손으로 이 줄을 더하는 일이
    #   곧 「진입면을 넓힌다」는 선언이다. 이 시험이 그 선언을 강제했다.
    #   문지기: @tenant_scoped(쓰기 IDOR) + JwtOrInboundKey.
    #   ★ 이 라우트는 **거절을 4xx 로 낸다** — 409(그 전이는 없다) · 400(사유를 채워라) ·
    #     403(팀장이 해야 한다). 셋을 한 코드로 묶지 않는다(D-290).
    ("POST", "/api/dsm/events/{int:event_id}/response"),
    # ★ 2026-09-11 **하나가 늘었다** — 이벤트 상세 화면(D-371 ①)이 부를 자리.
    #   이 시험이 먼저 멈춰 세웠다. 게이트가 지시보다 위다(D-327) — 손으로 이 줄을
    #   더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #
    #   왜 목록에서 골라내지 않고 라우트를 늘렸나: 화면이 목록 응답에서 한 줄을
    #   골라 상세로 쓰면 **문지기가 목록에만 서고 상세에는 안 선다.** 그 자리가
    #   IDOR 이 태어나는 자리다. 상세는 서버에 다시 묻는다.
    #   문지기: @tenant_scoped + JwtOrInboundKey(**키 거절** — 상세는 목록에 없는
    #           clip_path·address·reviewed_by_id 를 더 낸다. 계약이 F-05 로 연 것은
    #           이벤트 조회이지 그 셋이 아니다)
    ("GET", "/api/dsm/events/{int:event_id}"),    # F-09 이벤트 상세 (D-371)
})

#: K1 커널을 소비하는 모듈 전수 → **왜 소비하는가.**
#:
#: 사유를 함께 두는 이유: 새 소비자가 생겼을 때 "늘었다" 만으로는 그것이 옳은지 모른다.
#: 커널끼리의 재사용(K2·K3·K4·K6)은 **진입면이 아니고**, 파이프라인(bridge)도 HTTP 가
#: 아니다. F-05 가 금지하는 것은 **App 이 여럿이 되는 것**이다.
K1_CONSUMERS: dict[str, str] = {
    "backend/kernels/k1_event/__init__.py":
        "커널 자신의 공개 면 — 소비자가 아니라 **소비되는 쪽**이다",
    "backend/kernels/k1_event/services.py":
        "커널 자신의 구현 — 공개 면이 여기를 다시 import 한다",
    "backend/kernels/k1_event/response_flow.py":
        "★ 커널 자신의 구현 — 대응 진행 축(D-399). 1차판은 이 파일이 `apps/dsm/` 에 "
        "있었고 `AppStaysThinTest` 가 즉시 빨개졌다. `DetectionEvent` 의 수명주기는 "
        "K1 의 것이고 review_event·close_event 가 이미 여기 산다 — 흩어 두면 같은 "
        "표의 규칙이 두 층에 나뉜다. 소비자가 아니라 **소비되는 쪽**이다",
    "backend/apps/dsm/services.py":
        "★ **유일한 App 소비자.** F-05 가 말하는 그 하나의 진입면이 여기서 시작한다",
    "backend/stream_monitors/management/commands/seed_dsm_events.py":
        "★ 검수용 시드 (P-9). **이 소비자가 K1 을 부르는 것이 요점이다** — 지시서가 정한 "
        "「실제 이벤트」는 K1 생성 경로를 통과한 행이고, DB 직접 INSERT 는 모형이다. "
        "HTTP 진입면이 아니라 운영자가 손으로 부르는 커맨드다",
    "backend/kernels/k2_notify/services.py":
        "커널 간 재사용 — 알림이 이벤트를 읽는다. HTTP 진입면이 아니다",
    "backend/kernels/k3_dashboard/services.py":
        "커널 간 재사용 — 대시보드가 이벤트를 읽는다",
    "backend/kernels/k4_report/services.py":
        "커널 간 재사용 — 보고서가 이벤트를 읽는다",
    "backend/kernels/k6_feedback/services.py":
        "커널 간 재사용 — 오탐률이 이벤트를 센다",
    "backend/stream_monitors/services/detection_event_bridge.py":
        "AI 검출 파이프라인 배선. gRPC 콜백이라 **요청자가 없고**(D-281 시스템 스코프) "
        "HTTP 진입면이 아니다 — 밖에서 부를 수 있는 주소가 없다",
}

#: `/api/dsm/events` 응답의 키 집합. **모양이 계약이다** — 조용히 늘거나 줄면 멈춘다.
EVENT_RESPONSE_KEYS: frozenset[str] = frozenset({
    "event_id", "event_type", "severity", "status", "verdict",
    "occurred_at", "last_seen_at", "stream_monitor_id", "stream_monitor_name",
    "lat", "lng", "snapshot_path",
})


def _py_files():
    for p in BACKEND.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if "/tests/" in str(p).replace("\\", "/"):
            continue                       # 시험은 진입면이 아니다
        yield p


def _rel(p: Path) -> str:
    return "backend/" + str(p.relative_to(BACKEND)).replace("\\", "/")


def _imports(tree: ast.Module) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            out.add(node.module)
            out |= {f"{node.module}.{a.name}" for a in node.names}
    return out


def _scan() -> tuple[list[str], list[str]]:
    """(K1 을 import 하는 모듈, 라우트를 가진 모듈) — **직접 import 로만** 센다."""
    consumers: list[str] = []
    route_modules: list[str] = []
    for path in _py_files():
        src = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        if any(i.startswith("kernels.k1_event") for i in _imports(tree)):
            consumers.append(_rel(path))
        if "@route." in src or "@api_controller" in src:
            route_modules.append(_rel(path))
    return sorted(consumers), sorted(route_modules)


class EntrySurfaceIsOneTest(SimpleTestCase):
    """★ ① **하나로만 들어오는가** — 부작위 시험 (D-300)."""

    def test_the_event_kernel_has_exactly_one_app_consumer(self) -> None:
        """★ AC 의 핵심 단어는 "하나로만" 이다. 그것은 **App 이 하나**라는 뜻이다."""
        consumers, _ = _scan()
        apps_consuming = [m for m in consumers if m.startswith("backend/apps/")]
        self.assertEqual(
            ["backend/apps/dsm/services.py"], apps_consuming,
            "K1 커널을 소비하는 App 이 하나가 아닙니다 — 진입면이 둘이 되면 "
            "F-05 의 '하나로만' 이 깨집니다. 새 App 이 이벤트를 쓰려면 "
            "그 판정을 먼저 받으십시오.")

    def test_no_route_module_imports_the_event_kernel_directly(self) -> None:
        """★ 라우트가 커널을 **직접** 부르면 App 계층이 비어 버린다 (DA-04 §1-1).

        실측: 라우트를 가진 모듈 51개 중 0개. 0 이 아니라 **51 을 함께 출력**하는 것이
        요점이다 — 모수 없는 초록은 보고가 아니다(D-271).
        """
        consumers, route_modules = _scan()
        self.assertGreater(len(route_modules), 30,
                           f"라우트를 가진 모듈을 {len(route_modules)}개밖에 못 셌습니다 — "
                           f"열거기가 눈이 멀었습니다 (D-301).")
        offenders = sorted(set(consumers) & set(route_modules))
        self.assertEqual(
            [], offenders,
            f"라우트를 가진 모듈이 K1 을 직접 import 합니다: {offenders}. "
            f"(모수: 라우트 모듈 {len(route_modules)} · K1 소비자 {len(consumers)})")

    def test_every_k1_consumer_is_registered_with_a_reason(self) -> None:
        """★ 소비자가 늘면 **사유와 함께** 늘어야 한다 — 이름으로 잠근다 (D-285 ②).

        개수로 잠그면 하나가 지워질 때 새 소비자가 들어올 자리가 생긴다.
        """
        consumers, _ = _scan()
        self.assertTrue(consumers, "K1 소비자를 한 건도 못 찾았습니다 — 열거기 고장입니다.")
        unlisted = [m for m in consumers if m not in K1_CONSUMERS]
        self.assertEqual(
            [], unlisted,
            f"등재되지 않은 K1 소비자: {unlisted}. 등재는 면제가 아니라 **선언**입니다 — "
            f"왜 이 모듈이 이벤트를 쓰는지 K1_CONSUMERS 에 적으십시오.")
        gone = [m for m in K1_CONSUMERS if m not in consumers]
        self.assertEqual(
            [], gone,
            f"등재돼 있는데 이제 K1 을 안 씁니다: {gone}. 낡은 등재가 남으면 "
            f"다음에 늘어나는 소비자를 그 이름이 가립니다.")
        for module, why in K1_CONSUMERS.items():
            self.assertGreater(len(why.strip()), 10, f"{module} 의 사유가 비었습니다.")


class EntrySurfaceIsLockedTest(SimpleTestCase):
    """★ ② 그 하나의 진입면이 **잠겨 있는가.**"""

    def _dsm_routes(self):
        from common.tenant_scope import enumerate_operations

        return [r for r in enumerate_operations() if r.path.startswith("/api/dsm/")]

    def test_the_entry_surface_is_pinned_by_name(self) -> None:
        """등재된 10개가 전부다. 늘거나 줄면 멈춘다 — 진입면은 계약이다."""
        rows = self._dsm_routes()
        actual = {(r.method, r.path) for r in rows}
        self.assertEqual(
            set(EVENT_ENTRY_SURFACE), actual,
            f"진입면이 달라졌습니다.\n"
            f"  새로 생긴 것: {sorted(actual - set(EVENT_ENTRY_SURFACE))}\n"
            f"  사라진 것:   {sorted(set(EVENT_ENTRY_SURFACE) - actual)}")

    def test_every_entry_route_is_authenticated(self) -> None:
        naked = [(r.method, r.path) for r in self._dsm_routes() if not r.has_auth]
        self.assertEqual([], naked, f"인증 없는 진입면: {naked}")

    def test_every_entry_route_is_tenant_scoped(self) -> None:
        """문지기 없는 경로가 하나 생기면 그 순간 다시 샌다 (D-275 §5-1)."""
        loose = [(r.method, r.path) for r in self._dsm_routes() if r.scope is None]
        self.assertEqual([], loose, f"테넌트 문지기가 없는 진입면: {loose}")

    def test_the_count_is_not_zero(self) -> None:
        """★ 0건은 통과가 아니라 **판정 불가**다 (D-301). 라우트를 못 세면 위 셋이 전부 초록이다."""
        self.assertEqual(
            len(EVENT_ENTRY_SURFACE), len(self._dsm_routes()),
            "런타임에서 진입면을 세지 못했습니다 — 등록이 바뀌었거나 열거기가 멀었습니다.")


class EntryShapeIsStableTest(SimpleTestCase):
    """★ ③ **모양이 계약이다** — 응답 키가 조용히 늘거나 줄면 외부 App 이 깨진다."""

    def test_the_event_response_keys_are_pinned(self) -> None:
        """라우트 소스에서 응답 딕셔너리의 키를 **읽어** 대조한다.

        HTTP 를 태우지 않는 이유: 이 시험이 재는 것은 값이 아니라 **모양**이고,
        모양은 소스에 있다. 값까지 재는 것은 E2E-1 의 일이다(두 벌로 재지 않는다).
        """
        from apps.dsm.api import DsmAPI

        src = inspect.getsource(DsmAPI.events)
        keys = set(re.findall(r'"(\w+)":\s*e\.', src))
        self.assertEqual(
            set(EVENT_RESPONSE_KEYS), keys,
            f"이벤트 응답의 모양이 달라졌습니다.\n"
            f"  새로 생긴 키: {sorted(keys - set(EVENT_RESPONSE_KEYS))}\n"
            f"  사라진 키:   {sorted(set(EVENT_RESPONSE_KEYS) - keys)}\n"
            f"외부 App 이 이 키를 읽습니다 — 바꾸려면 그 판정을 먼저 받으십시오.")

    def test_the_shape_comes_from_the_kernel_view_not_the_model(self) -> None:
        """★ 응답 키가 **커널 값(EventView)에 실재하는가.** 모델을 타고 들어가지 않는다.

        App 이 모델 속성을 직접 읽으면 커널을 바꿀 때 App 이 깨지고, "한 번 개발" 이
        거짓이 된다(DA-04 §1-4).
        """
        from dataclasses import fields

        from kernels.k1_event import EventView

        view_fields = {f.name for f in fields(EventView)}
        missing = sorted(EVENT_RESPONSE_KEYS - view_fields)
        self.assertEqual(
            [], missing,
            f"응답 키가 EventView 에 없습니다: {missing} — App 이 모델을 타고 "
            f"들어가고 있다는 뜻입니다.")


class ApiKeyStoreExistsTest(SimpleTestCase):
    """★ FR-05-3 — **저장처가 생겼다** (2026-09-06 · D-325 표 ② · D-328).

    이 시험의 앞선 판은 정반대를 쟀다: *"저장처가 없다는 사실이 사유와 함께 선언돼
    있어야 한다."* 그 시험은 이렇게 끝맺고 있었다 — **"저장처가 생겼다면 F-05 대장의
    not_measured 도 함께 고치십시오."** 그날이 왔으므로 함께 고친다.

    ★ 이름을 바꾸는 것이 요점이다. `...IsDeclaredMissing` 인 채로 내용만 뒤집으면
      다음 사람이 이름을 믿고 코드를 안 읽는다.
    """

    def test_the_api_key_domain_is_no_longer_blocked(self) -> None:
        from apps.dsm.services import SETTING_DOMAINS

        self.assertIn("api_keys", SETTING_DOMAINS,
                      "API Key 영역이 설정 대장에서 사라졌습니다 — 빠진 줄은 보이지 않습니다.")
        self.assertEqual("", (SETTING_DOMAINS["api_keys"] or "").strip(),
                         "표 ②가 섰는데 사유가 남아 있습니다 — 사유는 막힌 것의 표시입니다.")

    def test_the_store_holds_facts_not_values(self) -> None:
        """★ D-204 · D-319 — 저장처가 생겼다는 것이 **값을 담는다**는 뜻은 아니다."""
        from kernels.k5_trust.credentials import CredentialDef

        self.assertNotIn("value", CredentialDef.__dataclass_fields__,
                         "표 ②가 값을 담기 시작하면 그것은 저장처가 아니라 유출면입니다.")

    def test_every_key_says_what_kind_of_api_it_is(self) -> None:
        """★ D-328 — 「있는가」가 아니라 **「무엇인가」**. 그 칸이 없어서 하루를 잃었다."""
        from kernels.k5_trust.credentials import CREDENTIALS

        self.assertTrue(CREDENTIALS)
        self.assertTrue(all(s.api_type.strip() for s in CREDENTIALS.values()))
