# -*- coding: utf-8 -*-
"""LAW-06 — **다섯 의무 자리표와 고지가 닿는 자리** (차선 L · 2026-09-05).

이 파일이 묻는 것 넷
--------------------
① **칸이 다섯인가.** 넷이나 여섯인 자리표는 자리표가 아니다.
② **각 칸이 「어디에 사는가」를 가리키는가, 그리고 그 자리가 실재하는가.**
   이름만 적힌 표는 리팩터링 한 번에 낡고, 낡은 표는 아무것도 안 가리키면서
   「있다」고 말한다.
③ ★ **빈칸과 「없음」이 다른가.** 아직 없는 자리는 지워지는 것이 아니라
   `present=False` + 사유로 남아야 한다. 지우면 「그 의무가 없다」와
   「그 의무를 아직 안 했다」가 같은 그림이 된다.
④ **고지가 두 자리에 닿는가** — 로그인 뒤 첫 화면과 **알림 본문** 둘 다.
   그리고 그 문장이 **한 곳에서만** 정해지는가. 두 벌이 된 고지는 한쪽만 고쳐진다.

★ 이 파일이 묻지 **않는** 것 — 그 문장이 법이 요구하는 고지로 충분한가.
  조문 대조는 법률대리인의 판정이다. 재는 것은 **닿는가**이지 적법성이 아니다.
"""
from __future__ import annotations

from pathlib import Path

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.ai_act · common.ai_act_notice · kernels.k2_notify.services · "
    "frontend/src/features/dsm/components/AutoAnalysisNotice.tsx — 저장소의 실물"
)

#: 화면 쪽 파일. 컨테이너는 `/repo/frontend`, 호스트는 `<저장소>/frontend` 다 —
#: 한 자리로 못 박으면 한쪽에서 「파일이 없다」로 죽는다.
FRONT_TAIL = Path("src") / "features" / "dsm"


def _frontend(*parts) -> str | None:
    """화면 파일 원문. 못 읽으면 `None` — **회색은 초록이 아니다**(D-301)."""
    here = Path(__file__).resolve()
    bases = [Path("/repo/frontend"), Path("/frontend")]
    bases += [p / "frontend" for p in here.parents if (p / "frontend").is_dir()]
    for base in bases:
        candidate = base.joinpath(FRONT_TAIL, *parts)
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return None


class TheTableHasFiveCellsTest(DsmFixture):
    """① · ② 다섯 칸이 있고, 각 칸이 **실재하는 자리**를 가리킨다."""

    def test_there_are_exactly_five_duties(self):
        from apps.dsm.ai_act import DUTY_NAMES, duty_table

        table = duty_table()
        self.assertEqual(table["duty_count"], 5)
        self.assertEqual([d["duty"] for d in table["duties"]], list(DUTY_NAMES))

    def test_the_five_names_are_the_ones_the_ledger_wrote(self):
        """대장이 적은 이름 그대로다 — 우리가 다시 짓지 않는다."""
        from apps.dsm.ai_act import DUTY_NAMES

        for name in ("위험관리", "설명가능성", "이용자보호", "사람감독", "문서화"):
            self.assertIn(name, DUTY_NAMES)

    def test_every_duty_points_somewhere(self):
        from apps.dsm.ai_act import duty_table

        for duty in duty_table()["duties"]:
            self.assertGreater(duty["anchor_count"], 0,
                               f"{duty['duty']} 가 아무 자리도 안 가리킨다")
            for anchor in duty["anchors"]:
                self.assertTrue(anchor["what"], "무엇을 하는 자리인지가 없다")
                self.assertTrue(anchor["target"], "어디에 사는지가 없다")

    def test_no_duty_is_entirely_unanchored(self):
        from apps.dsm.ai_act import duty_table

        table = duty_table()
        self.assertEqual(
            table["duties_without_any_anchor"], [],
            "자리가 하나도 없는 의무가 있다 — 그 의무는 「닿는다」고 말할 수 없다: %s"
            % table["duties_without_any_anchor"])

    def test_the_anchors_are_resolved_not_just_written(self):
        """★ 적힌 이름이 **실제로 import 되는가.** 이름만 있는 표는 착시다."""
        from apps.dsm.ai_act import duty_table

        for duty in duty_table()["duties"]:
            for anchor in duty["anchors"]:
                self.assertIn("present", anchor)
                if not anchor["present"]:
                    self.assertTrue(anchor["why_not"],
                                    "없다고만 하고 왜 없는지가 없다")


class MissingIsWrittenNotErasedTest(DsmFixture):
    """③ ★ **빈칸과 「없음」은 다르다.**"""

    def test_the_missing_model_card_is_reported_as_missing(self):
        """[실측 2026-09-05] AI 모델 기술문서가 이 저장소에 없다.

        그 부재를 표에서 지우면 문서화 의무가 **다 된 것처럼** 보인다.
        이 시험이 빨개지는 날은 그 문서가 생긴 날이다 — 그때 이 시험을 고친다.
        """
        from apps.dsm.ai_act import duty_table

        docs = next(d for d in duty_table()["duties"] if d["duty"] == "문서화")
        missing = [a for a in docs["anchors"] if not a["present"]]
        self.assertTrue(
            missing,
            "★ 문서화의 빈칸이 사라졌다 — 모델 기술문서가 생겼다면 좋은 일이다. "
            "그때는 이 시험과 자리표를 함께 고쳐라")
        self.assertTrue(docs["gap"], "일부만 있는 의무의 사유가 비어 있다")
        self.assertIn("문서화", duty_table()["duties_with_gaps"])

    def test_the_table_says_legal_review_is_pending(self):
        """★ 「배선했다」와 「법을 지킨다」는 다른 사실이다."""
        from apps.dsm.ai_act import duty_table

        table = duty_table()
        self.assertTrue(table["legal_review_pending"])
        self.assertTrue(table["legal_review_note"])


class TheNoticeReachesBothPlacesTest(DsmFixture):
    """④ ★ 고지가 **알림 본문**과 **로그인 뒤 첫 화면** 둘 다에 닿는다."""

    def test_the_notice_is_in_the_alert_body(self):
        from common.ai_act_notice import NOTICE_BODY
        from kernels.k2_notify.services import _subject_and_body

        Event = self._event  # 픽스처의 이벤트 생성기
        event_id = Event(self.stream_a)

        from django.apps import apps as django_apps

        row = django_apps.get_model("stream_monitors", "DetectionEvent") \
            ._base_manager.get(pk=event_id)
        _subject, body = _subject_and_body(row)
        self.assertIn(NOTICE_BODY, body,
                      "알림 본문에 자동 분석 고지가 없다 — 화면 밖에서 판정을 처음 "
                      "보는 사람에게는 이 본문이 유일한 고지 자리다")

    def test_the_notice_is_on_the_first_screen_after_login(self):
        component = _frontend("components", "AutoAnalysisNotice.tsx")
        if component is None:
            #: ★ **회색은 초록이 아니다** — 통과시키지 않고 「못 쟀다」로 남긴다.
            #:   [실측 2026-09-05] 이 컨테이너에는 backend · docs · scripts 만
            #:   마운트돼 있고 frontend 가 없다. 호스트에서는 같은 대조가 초록이며
            #:   그 명령과 출력은 증거에 적혀 있다. 마운트가 생기면 이 자리는
            #:   저절로 재기 시작한다 — 시험을 고칠 필요가 없다.
            self.skipTest("frontend 가 이 컨테이너에 마운트되지 않았다 — "
                          "gx-shell 에 읽기전용 마운트가 필요하다(조율자 배선)")

        from common.ai_act_notice import NOTICE_BODY, NOTICE_TITLE

        self.assertIn(NOTICE_TITLE, component)
        self.assertIn(NOTICE_BODY, component,
                      "화면의 문장과 서버의 문장이 다르다 — 두 벌이 된 고지다")

        dashboard = _frontend("pages", "ControlDashboard.tsx")
        self.assertIsNotNone(dashboard, "관제 화면 원문을 못 읽었다")
        self.assertIn("AutoAnalysisNotice", dashboard,
                      "조각은 있는데 첫 화면이 그것을 안 그린다 — 「닿는다」가 아니다")

    def test_the_sentence_is_declared_in_exactly_one_backend_place(self):
        """★ **두 벌 금지.** 커널이 문장을 손으로 적으면 한쪽만 고쳐진다."""
        from common.ai_act_notice import NOTICE_BODY

        here = Path(__file__).resolve()
        backend = next(p for p in here.parents if (p / "kernels").is_dir())
        holders = []
        for path in backend.rglob("*.py"):
            if "__pycache__" in path.parts or path.name.startswith("test_"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if NOTICE_BODY in text:
                holders.append(path.name)
        self.assertEqual(holders, ["ai_act_notice.py"],
                         "고지 문장이 여러 곳에 적혀 있다: %s" % holders)

    def test_the_notice_surfaces_are_named(self):
        """닿아야 하는 자리를 **이름으로** 적어 둔다 — 안 적으면 셀 수 없다."""
        from apps.dsm.ai_act import duty_table

        surfaces = duty_table()["notice"]["surfaces"]
        self.assertIn("로그인 뒤 첫 화면", surfaces)
        self.assertIn("알림 본문", surfaces)
