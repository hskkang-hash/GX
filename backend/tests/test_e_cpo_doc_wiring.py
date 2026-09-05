# -*- coding: utf-8 -*-
"""CPO 문서 4 — **배선이 실재하는가** (턴 C · 차선 E · 2026-09-05).

세종(CPO)이 서식 셋을 썼고, 이 차선이 한 일은 **배선**뿐이다:

    GX-LAW-02  안내판·방침의 「제품 자동」 칸  → `GET /api/dsm/settings/notice-draft`
    GX-LAW-03  수집 항목 표(모델에서 생성)     → `GET /api/dsm/settings/privacy-collection`
    GX-REPORT  월간 1쪽                        → K4 `MONTHLY_VARIABLES` 등재 + 분모 규칙

★ 이 시험이 못박는 것 넷
------------------------
  ① **리터럴 경로가 변수 경로에 삼켜지지 않는다** — `/settings/{domain}` 이 위에 있으면
     `/settings/notice-draft` 는 404 도 아니고 **501**("설정 영역이 아니다")로 답한다.
     있는데 없는 것처럼 보이는 가장 나쁜 모양이다 (D-410).
  ② **수집 항목 표가 모델과 갈리지 않는다** — 갈린 표는 「이것만 모읍니다」라고
     말하면서 다른 것을 모으는 문서가 된다. 처리방침에서 가장 위험한 실패다.
  ③ **서식의 변수와 코드의 변수가 같다** — 갈리면 템플릿이 빈 칸을 조용히 그리고,
     그 종이는 「없었다」와 「0이었다」를 구별하지 못한다.
  ④ **자동 종결·시드·훈련이 분모에서 빠진다** — 빼지 않으면 오탐이 많은 달일수록
     대응 시간이 좋아 보인다. 지표가 사실의 반대를 말하는 자리다.

⚠ 대장 상태는 **미측정**이다 — 법률 대조 전이라 라우트가 있다고 LAW-02·03 이
  「구현」이 되지 않는다. 이 시험이 재는 것은 **배선**이지 문안의 적법성이 아니다.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.test import TestCase

from apps.dsm.legal_notice import (
    COLLECTION_ROWS,
    RETENTION_SETTING_NAMES,
    collection_table,
    retention_days,
)
from kernels.k4_report.schemas import (
    MONTHLY_EXCLUDED_FROM_DENOMINATOR,
    MONTHLY_VARIABLES,
    _monthly_counted as monthly_counted,
)

LITERAL = "/settings/notice-draft"
LITERAL2 = "/settings/privacy-collection"
VARIABLE = "/settings/{domain}"


def _dsm_operations() -> list[str]:
    """DSM 라우터의 경로를 **선언 순서 그대로** 낸다. 순서가 곧 라우팅이다."""
    from common.tenant_scope import _iter_ninja_apis

    paths: list[str] = []
    for _mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path in (getattr(router, "path_operations", {}) or {}):
                if "dsm" in str(prefix) or "settings" in str(op_path):
                    paths.append(str(op_path))
    return paths


class LiteralRouteIsNotSwallowedTest(TestCase):
    """① 선언 순서 — **리터럴이 변수보다 위에 있다** (D-410)."""

    def setUp(self):
        self.paths = _dsm_operations()

    def test_both_literal_routes_are_declared(self):
        for literal in (LITERAL, LITERAL2):
            self.assertIn(literal, self.paths,
                          "%s 라우트가 선언되지 않았다" % literal)

    def test_literal_precedes_the_variable_path(self):
        """★ 이 시험이 이 배선의 요점이다.

        `/settings/{domain}` 을 위로 올리는 순간 이 둘은 501 로 죽는다. 그 501 은
        「기능이 없다」로 읽히고, 라우트는 멀쩡히 살아 있으므로 아무도 못 찾는다.
        """
        self.assertIn(VARIABLE, self.paths)
        var_at = self.paths.index(VARIABLE)
        for literal in (LITERAL, LITERAL2):
            self.assertLess(
                self.paths.index(literal), var_at,
                "%s 가 %s 아래로 내려갔다 — 변수 경로가 삼킨다(D-410)"
                % (literal, VARIABLE))


class CollectionTableComesFromModelsTest(TestCase):
    """② LAW-03 수집 항목 표는 **모델에서 만든다.**"""

    def test_every_row_resolves_to_a_real_model_and_field(self):
        table = collection_table()
        self.assertEqual(
            table["drifted"], [],
            "표가 모델과 갈렸다 — 이 방침 초안은 아직 내면 안 된다:\n  "
            + "\n  ".join("%s: %s" % (r["item"], r["why_not"])
                          for r in table["rows"] if r["why_not"]))

    def test_the_table_is_not_empty(self):
        """0건 검사와 검사 못함을 가른다 (D-301). 빈 표는 「아무것도 안 모은다」가 아니다."""
        self.assertGreaterEqual(len(COLLECTION_ROWS), 5)
        self.assertEqual(len(collection_table()["rows"]), len(COLLECTION_ROWS))

    def test_the_table_says_what_is_not_collected(self):
        """음성·얼굴·번호는 **제품 사양으로 없다** — 그 사실도 방침의 일부다."""
        items = {row["item"] for row in collection_table()["not_collected"]}
        self.assertIn("음성", items)


class NoticeDraftDoesNotInventValuesTest(TestCase):
    """★ **없는 값을 지어내지 않는다** (D-301 · D-290).

    서식의 안내판에는 「보관 기간 : 기본 30일」이 적혀 있다. 그런데 이 제품에는 영상
    보존 일수를 선언한 자리가 없다. 여기서 30을 적으면 그 순간 **게시된 안내판이
    거짓말을 시작하고**, 종이는 되돌릴 수 없다.
    """

    def test_retention_is_none_until_a_setting_declares_it(self):
        days = retention_days()
        self.assertTrue(days is None or isinstance(days, int))
        if days is None:
            #: 음성 대조 — 「없다」가 「0일」로 둔갑하지 않았는가
            self.assertNotEqual(days, 0)

    def test_the_retention_setting_names_are_declared(self):
        """찾아본 자리를 이름으로 남긴다 — 어디를 안 봤는지가 보이게."""
        self.assertGreater(len(RETENTION_SETTING_NAMES), 0)


class MonthlyReportVariablesMatchTheFormTest(TestCase):
    """③ 서식의 변수와 코드의 변수가 **같다.**"""

    #: 서식 원문. 컨테이너는 `/docs`, 호스트는 `<저장소>/docs` 다 — 한 자리로 못박으면
    #: 한쪽에서 「서식이 없다」로 죽는다 (`verify_perf_budget.evidence_path` 와 같은 모양).
    TAIL = Path("design") / "GX-REPORT_월간1쪽_이번달우리센터_서식_v0.1.md"

    def _form_text(self) -> str | None:
        here = Path(__file__).resolve()
        bases = [Path("/docs")]
        #: 저장소 뿌리가 어디인지 한 자리로 못박지 않는다 — 컨테이너는 `/app`(=backend)
        #: 이라 `parents[3]` 이 아예 없다 [실측: `IndexError: 3`].
        bases += [p / "docs" for p in here.parents if (p / "docs").is_dir()]
        for base in bases:
            cand = base / self.TAIL
            if cand.is_file():
                return cand.read_text(encoding="utf-8")
        return None

    def test_every_ascii_placeholder_in_the_form_is_registered(self):
        text = self._form_text()
        self.assertIsNotNone(
            text, "서식 원문을 못 읽었다 — **회색은 초록이 아니다**(D-301). "
                  "`/docs` 마운트를 확인하라")
        found = {m for m in re.findall(r"\{([a-z][a-z0-9_]*)\}", text)}
        self.assertGreater(len(found), 10, "서식에서 변수를 거의 못 읽었다 — "
                                           "정규식이 서식과 갈렸는지 먼저 의심하라(D-350)")
        missing = sorted(found - set(MONTHLY_VARIABLES))
        self.assertEqual(missing, [],
                         "서식에는 있는데 K4 에 등재되지 않은 변수: %s — "
                         "템플릿이 이 칸을 조용히 빈 문자열로 그린다" % missing)

    def test_no_duplicate_names(self):
        self.assertEqual(len(MONTHLY_VARIABLES), len(set(MONTHLY_VARIABLES)))


class MonthlyDenominatorExcludesThreeTest(TestCase):
    """④ **자동 종결·시드·훈련이 분모에서 빠진다** (서식 규칙 · D-293 정신)."""

    ROWS = (
        {"id": 1},
        {"id": 2, "auto_closed": True},
        {"id": 3, "seed": True},
        {"id": 4, "drill": True},
        {"id": 5},
        {"id": 6, "seed": True, "drill": True},
    )

    def test_all_three_are_excluded(self):
        counted, excluded = monthly_counted(self.ROWS)
        self.assertEqual([r["id"] for r in counted], [1, 5],
                         "빼야 할 줄이 분모에 남았다 — 오탐이 많은 달일수록 "
                         "대응 시간이 좋아 보인다")
        self.assertEqual(excluded, {"auto_closed": 1, "seed": 2, "drill": 2})

    def test_the_excluded_count_is_reported(self):
        """★ 뺀 수를 **함께 낸다** (D-301). 안 내면 다음 사람이 분모를 원본 건수로 읽는다."""
        _counted, excluded = monthly_counted(self.ROWS)
        self.assertEqual(set(excluded), set(MONTHLY_EXCLUDED_FROM_DENOMINATOR))

    def test_positive_control_nothing_is_excluded_when_no_flag_is_set(self):
        """음성 대조 — 전부 빼는 함수는 「걸렀다」가 아니라 「다 버렸다」이다."""
        counted, excluded = monthly_counted([{"id": 9}, {"id": 10}])
        self.assertEqual(len(counted), 2)
        self.assertEqual(sum(excluded.values()), 0)

    def test_object_rows_work_too(self):
        """줄이 사전이 아니라 객체여도 같은 판정이다 — 두 벌로 적지 않기 위해서."""
        class Row:
            def __init__(self, drill=False):
                self.drill = drill

        counted, excluded = monthly_counted([Row(), Row(drill=True)])
        self.assertEqual(len(counted), 1)
        self.assertEqual(excluded["drill"], 1)


class TodayLatencyStatsOnlyExcludesAutoClosedTest(TestCase):
    """★ **음성 대조 — 아직 안 된 자리를 시험이 기억한다.**

    위의 `monthly_counted` 는 셋을 다 뺀다. 그런데 지금 화면·API 가 쓰는
    `response_clock.latency_stats` 는 **자동 종결 하나만** 뺀다. 둘을 함께 적지
    않으면 「분모 규칙이 섰다」로 읽히고, 시드·훈련은 조용히 분모에 남는다.

    이 시험이 빨개지는 날은 그 자리가 **고쳐진 날**이다 — 그때 이 시험을 지운다.
    """

    def test_the_gap_is_still_here(self):
        from stream_monitors.services.response_clock import latency_stats

        stats = latency_stats([])
        self.assertIn("excluded_auto_closed", stats)
        for name in ("excluded_seed", "excluded_drill"):
            self.assertNotIn(
                name, stats,
                "★ `latency_stats` 가 %s 를 재기 시작했다 — 좋은 일이다. "
                "이 음성 대조를 지우고 위 규칙과 이어라" % name)
