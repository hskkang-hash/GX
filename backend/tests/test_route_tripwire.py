# -*- coding: utf-8 -*-
"""신규 경로 트립와이어 — **런타임 전수 열거** 판정 (D-275 §5-1).

WP-2 EXIT 승인의 **유일한 필수 부대조건**이 이것이다.

  §5-1 이 남긴 미지: 주인 없는 행은 매니저 수준에서 여전히 보이고, 근원은 저장소 밖이라
  못 고친다. 지금 닫혀 있는 이유는 라우트마다 문지기를 손으로 달았기 때문이고,
  **문지기 없는 새 경로가 하나 생기면 그 순간 다시 샌다.**

그 문장을 사람의 기억이 아니라 게이트가 지키게 한다. 판정기는
`common/tenant_tripwire.py` 에 있고, 이 파일은 그것을 **런타임 라우트 전수**에 물린다.

왜 여기(시험)인가 — `scripts/verify_tenant_scope.py` 와 무엇이 다른가
--------------------------------------------------------------------
지시가 요구한 것은 **런타임 열거**다. 런타임 열거는 Django 를 띄워야 하고,
pre-commit 은 Django 없이 돈다. 그래서 눈을 둘로 나눴다:

  · pre-commit  `verify_tenant_scope.py` — **정적** 눈. 소스의 `@route.*`. 커밋 시점에 먼저 건다.
  · 여기         **런타임** 눈. 등록된 오퍼레이션 전수. 동적 등록까지 본다.

**판정기는 하나다** (`tenant_tripwire.judge`). 눈만 둘이다 — 같은 것을 두 곳에서 세는 것이
아니라, 한 판정을 두 각도에서 먹인다.

★ 양성 대조 의무 (D-277)
------------------------
`assertNotContains('"id":N')` 이 응답의 `"id": N`(공백) 때문에 **구조적으로 실패할 수
없었던** 일이 있었다. "list 8/8 통과"는 그때부터 줄곧 거짓이었다 — 시험이 틀린 게 아니라
**탐지기가 눈이 멀어 있었다.**

그래서 이 파일은 "위반 0" 을 주장하기 전에 **탐지기가 실제로 탐지하는지 먼저 증명한다.**
  · 문지기 없는 라우트를 **심어 놓고** 잡히는지 (양성)
  · 문지기 있는 라우트를 심어 놓고 **안 잡히는지** (음성 — 늘 빨간불인 탐지기도 탐지기가 아니다)
둘 다 통과해야 아래 본 판정이 뜻을 가진다.
"""
from __future__ import annotations

from django.test import SimpleTestCase

from common import tenant_tripwire as tw
from common.tenant_scope import RouteInfo, ScopeSpec

#: 심는 라우트가 만질 테넌트 모델. 인구조사(정본 모수)에 실재하는 것으로 고른다 —
#: 없는 이름을 쓰면 "안 잡혔다"가 탐지기 탓인지 모델 탓인지 갈리지 않는다.
PLANTED_MODEL = "flight_log.FlightLog"


# ---------------------------------------------------------------------------
# 심는 핸들러 — **데코레이터를 붙이지 않는다**
# ---------------------------------------------------------------------------
# `@api_controller` / `@route.*` 를 붙이면 정적 눈이 이 시험 파일을 훑을 때 이 둘을
# **진짜 신규 위반으로** 집어낸다. 시험을 세우려다 게이트를 빨간불로 고정하는 셈이다.
# 판정기는 "모듈 + qualname → 소스 함수" 로 되짚으므로 데코레이터 없이도 그대로 판정된다.
class _PlantedController:
    """실패할 수 있는 시험인지 확인하기 위한 미끼. 어디에도 등록되지 않는다."""

    def leak_flight_logs(self, request, log_id: int):
        """문지기 없이 남의 테넌트 행에 닿는 핸들러 — **잡혀야 한다.**"""
        from flight_log.models import FlightLog

        return FlightLog._base_manager.get(id=log_id)

    def guarded_flight_logs(self, request, log_id: int):
        """같은 모델을 만지지만 문지기가 있다 — **안 잡혀야 한다.**"""
        from common.tenant_filters import assert_scoped
        from flight_log.models import FlightLog

        assert_scoped(FlightLog, log_id, request.user)
        return FlightLog._base_manager.get(id=log_id)


def _planted(handler: str, *, scoped: bool = False) -> RouteInfo:
    return RouteInfo(
        method="GET",
        path=f"/api/__tripwire_probe__/{handler}/{{log_id}}",
        handler=f"_PlantedController.{handler}",
        module="tests.test_route_tripwire",
        has_auth=True,
        scope=ScopeSpec() if scoped else None,
    )


class DetectorPositiveControlTest(SimpleTestCase):
    """★ 먼저 증명한다 — **재는 기계가 작동하는가** (착시 4형 ④ · D-277)."""

    def test_census_is_not_empty(self) -> None:
        """모수가 비면 그 위의 모든 초록은 뜻이 없다 (D-271 ②)."""
        census = tw.load_census_labels()
        self.assertGreaterEqual(
            len(census), 100,
            f"인구조사 모수가 {len(census)}종뿐입니다. 옛 술어의 모수는 2종이었고 "
            "그 위에서 '누락 1건'을 말하고 있었습니다 — 같은 착시로 돌아갔는지 확인하십시오.",
        )
        self.assertIn(
            PLANTED_MODEL, census,
            f"{PLANTED_MODEL} 이 인구조사에 없습니다 — 미끼가 미끼 구실을 못 합니다.",
        )

    def test_detector_catches_a_planted_unguarded_route(self) -> None:
        """**양성 대조** — 문지기 없는 라우트를 심으면 잡혀야 한다."""
        verdicts = {v.key: v for v in tw.scan_runtime([_planted("leak_flight_logs")])}
        (v,) = verdicts.values()
        self.assertEqual(
            v.verdict, "unguarded",
            f"심어 둔 무방비 라우트를 탐지기가 '{v.verdict}' 로 봤습니다 "
            f"(만진 모델={v.models}, 문지기={v.gatekeepers}).\n"
            "이 시험이 빨간불이면 아래 '신규 위반 0' 은 초록이 아니라 눈이 감긴 것입니다.",
        )
        self.assertIn(PLANTED_MODEL, v.models)

    def test_detector_clears_a_guarded_route(self) -> None:
        """**음성 대조** — 문지기가 있으면 잡히면 안 된다.

        늘 빨간불인 탐지기는 늘 초록인 탐지기와 똑같이 쓸모가 없다.
        """
        verdicts = {v.key: v for v in tw.scan_runtime([_planted("guarded_flight_logs")])}
        (v,) = verdicts.values()
        self.assertEqual(
            v.verdict, "guarded",
            f"문지기(assert_scoped)를 단 라우트를 '{v.verdict}' 로 봤습니다 — "
            "탐지기가 무엇이든 빨간불로 만들고 있습니다.",
        )
        self.assertIn("assert_scoped", v.gatekeepers)

    def test_decorator_alone_counts_as_a_gatekeeper(self) -> None:
        """`@tenant_scoped` 만 걸린 라우트도 guarded 여야 한다 (런타임 표식 경로)."""
        (v,) = tw.scan_runtime([_planted("leak_flight_logs", scoped=True)])
        self.assertEqual(v.verdict, "guarded")
        self.assertIn("tenant_scoped", v.gatekeepers)


class RuntimeTripwireTest(SimpleTestCase):
    """본 판정 — **런타임 라우트 전수**에 판정기를 물린다."""

    maxDiff = None

    def test_enumerator_is_not_blind(self) -> None:
        """열거가 0 이면 '위반 0' 은 통과가 아니다. **이것이 먼저다.**"""
        n = len(tw.scan_runtime())
        self.assertGreaterEqual(
            n, tw.MIN_EXPECTED_ROUTES,
            f"런타임 라우트를 {n}건밖에 못 셌습니다 (하한 {tw.MIN_EXPECTED_ROUTES}). "
            "열거기가 NinjaExtraAPI 인스턴스를 못 찾고 있습니다 — "
            "이 상태에서는 아래 수치가 전부 무의미합니다.",
        )

    def test_no_new_unguarded_route(self) -> None:
        """★ 트립와이어 본체 — 등재부에 **없던** 무방비 라우트가 나타나면 실패한다."""
        rep = tw.compare(tw.Report("runtime", tw.scan_runtime()))
        print("\n" + rep.summary)
        for note in rep.notes:
            print("  · " + note)
        self.assertEqual(
            rep.problems, [],
            "\n\n".join(
                ["문지기 없는 새 경로가 들어왔습니다 — EXIT 승인의 필수 부대조건(D-275 §5-1)입니다.", *rep.problems]
            ),
        )

    def test_baseline_is_present_and_names_not_counts(self) -> None:
        """등재부가 **이름**을 담고 있는가. 수만 담으면 자리 바꿔치기를 못 잡는다 (D-249)."""
        base = tw.load_baseline()
        self.assertIsNotNone(
            base, f"등재부가 없습니다: {tw.baseline_path()} — 없으면 무엇이 늘었는지 아무도 모릅니다."
        )
        eye = base.get("runtime") or {}
        self.assertIn("unguarded", eye, "등재부에 runtime 구획이 없습니다.")
        self.assertTrue(
            all(isinstance(k, str) and " " in k for k in eye["unguarded"]),
            "등재부 항목이 'METHOD module.qualname' 형태가 아닙니다 — 이름으로 잠그지 못합니다.",
        )
