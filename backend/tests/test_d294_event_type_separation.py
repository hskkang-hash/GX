# -*- coding: utf-8 -*-
"""D-294 강제 도구 — **오탐률·통계가 타입별로 갈라지는가.** 섞이면 exit 1.

D-294 가 판정한 것
------------------
    F-02(침수·수위)는 계약 M 기능이므로 전용 이벤트 타입의 부재는
    **설계 선택이 아니라 누락**이다. 전용 타입을 신설하라.

왜 "실어 보내면 안 되는가" — 오염은 조용하다
--------------------------------------------
수위 초과를 `intrusion` 같은 기존 타입에 실어 보내면 화면은 돌아간다. 그러나
`intrusion` 의 오탐률 분모에 침수 이벤트가 섞이고, **아무도 그 사실을 모른다.**
침수 판정이 잘 되면 침입 오탐률이 좋아지고, 침수가 오탐이면 침입이 나빠 보인다.
지표가 가리키는 대상과 실제 대상이 갈리는 것이고, 그 갈림은 숫자에 드러나지 않는다.

이 파일이 잠그는 것 셋
----------------------
  ① `flood` 가 계약 열거에 **실재**하는가 (모델·마이그레이션·계약 문서)
  ② 집계가 타입별로 **갈라지는가** — 한 타입의 판정이 다른 타입의 분모에 안 든다
  ③ 타입 필터 없는 전체 집계가 **합과 같은가** — 갈라 세도 총합이 어긋나지 않는다
"""
from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from tests.test_k6_feedback_kernel import K6Fixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "stream_monitors.models.DetectionEvent.EventType · "
    "kernels.k6_feedback.false_positive_rate — 저장소의 실제 열거와 실제 집계 함수"
)

#: F-02 가 쓰는 타입. **이름을 여기 한 번 박는다** — 여러 곳에 흩어진 문자열은
#: 하나가 바뀔 때 나머지가 조용히 남는다 (D-285 ②: 수가 아니라 이름으로 잠근다).
FLOOD = "flood"


class FloodEventTypeExistsTest(K6Fixture):
    """① 열거에 실재하는가 — 문서·모델·DB 셋이 같은 말을 하는가."""

    def test_flood_is_in_the_contract_enum(self) -> None:
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertIn(
            FLOOD, Event.EventType.values,
            "F-02(침수·수위) 전용 타입이 없습니다 — 기존 타입에 실어 보내면 그 타입의 "
            "오탐률 분모가 오염되고 아무도 모릅니다 (D-294).")

    def test_the_kernel_accepts_it(self) -> None:
        """열거에 있는 것과 커널이 받는 것은 다른 사실이다."""
        event_id = self._event(self.stream_a, event_type=FLOOD, severity="critical")
        self.assertTrue(event_id)

    def test_the_contract_document_lists_it(self) -> None:
        """★ 문서와 코드가 갈리면 어느 쪽이 계약인지 아무도 모른다 (D-227 이 만든 상황).

        열거를 늘리는 것은 계약 문서를 고치는 일이라고 계약 문서 자신이 적어 두었다:
        *"추가 시 이 문서와 W2-3 색 규칙을 함께 갱신"*.
        """
        from pathlib import Path

        contract = (Path(__file__).resolve().parents[2]
                    / "docs" / "contracts" / "detection-event.md")
        self.assertTrue(contract.is_file(), f"계약 문서를 찾지 못했습니다: {contract}")
        text = contract.read_text(encoding="utf-8")
        self.assertIn(
            f"`{FLOOD}`", text,
            "모델에는 flood 가 있고 계약 문서에는 없습니다 — 같은 커밋에서 함께 "
            "고치라는 것이 그 문서가 스스로 정한 규칙입니다.")


class RateIsSeparatedByTypeTest(K6Fixture):
    """② 갈라지는가 — **한 타입의 판정이 다른 타입의 분모에 들지 않는가.**"""

    def setUp(self) -> None:
        super().setUp()
        self.since = timezone.now() - timedelta(days=2)
        self.until = timezone.now() + timedelta(seconds=1)

    def _rate(self, event_type=None):
        from kernels.k6_feedback import false_positive_rate

        return false_positive_rate(scope=self.scope_a, since=self.since,
                                   until=self.until, event_type=event_type).total

    def test_flood_verdicts_do_not_enter_the_fire_denominator(self) -> None:
        """화재는 전부 확인(오탐 0), 침수는 전부 기각(오탐 1.0) — 섞이면 둘 다 0.5 로 뭉갠다."""
        for _ in range(2):
            self._judge(self._event(self.stream_a, event_type="fire"), "confirmed")
        for _ in range(2):
            self._judge(self._event(self.stream_a, event_type=FLOOD,
                                    severity="critical"), "rejected")

        fire = self._rate("fire")
        flood = self._rate(FLOOD)

        self.assertEqual((2, 0), (fire.reviewed, fire.rejected),
                         "화재 분모에 침수가 섞였습니다 — 타입 분리가 깨졌습니다 (D-294).")
        self.assertEqual((2, 2), (flood.reviewed, flood.rejected),
                         "침수 분모에 화재가 섞였습니다 — 타입 분리가 깨졌습니다 (D-294).")
        self.assertEqual(0.0, fire.rate)
        self.assertEqual(1.0, flood.rate)
        self.assertNotEqual(
            fire.rate, flood.rate,
            "두 타입의 오탐률이 같습니다. 픽스처는 정반대로 만들었으므로, 같다면 "
            "타입 필터가 아무것도 하지 않고 있는 것입니다.")

    def test_the_whole_equals_the_sum_of_its_types(self) -> None:
        """③ 갈라 세도 총합이 어긋나지 않는가 — 두 벌로 세면 숫자가 갈린다 (DA-04 K6)."""
        self._judge(self._event(self.stream_a, event_type="fire"), "confirmed")
        self._judge(self._event(self.stream_a, event_type="smoke"), "rejected")
        self._judge(self._event(self.stream_a, event_type=FLOOD,
                                severity="critical"), "rejected")

        total = self._rate()
        parts = [self._rate(t) for t in ("fire", "smoke", FLOOD)]

        self.assertEqual(total.reviewed, sum(p.reviewed for p in parts),
                         "타입별 분모의 합이 전체 분모와 다릅니다 — 두 벌로 셌습니다.")
        self.assertEqual(total.rejected, sum(p.rejected for p in parts),
                         "타입별 분자의 합이 전체 분자와 다릅니다 — 두 벌로 셌습니다.")

    def test_positive_control_the_filter_can_actually_exclude(self) -> None:
        """★ 양성 대조 (D-277) — 필터가 **거르기는 하는가.**

        "섞이지 않았다"는 필터가 일했다는 뜻일 수도 있고, 애초에 표본이 하나뿐이라
        섞일 것이 없었다는 뜻일 수도 있다. 심어 놓고 걸러지는지 본다.
        """
        self._judge(self._event(self.stream_a, event_type=FLOOD,
                                severity="critical"), "rejected")

        self.assertEqual(1, self._rate(FLOOD).reviewed)
        self.assertEqual(
            0, self._rate("person").reviewed,
            "침수만 심었는데 사람 타입에서 분모가 나옵니다 — 필터가 무시되고 있습니다.")
