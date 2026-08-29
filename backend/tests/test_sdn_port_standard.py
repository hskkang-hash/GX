# -*- coding: utf-8 -*-
"""SDN 연결 **표준**이 서 있는가 — 그리고 **그 이상을 만들지 않았는가**.

대표 지시 (2026-08-31)
----------------------
    SDN API 는 다음 지시가 있을 때까지 제외하고, **연결할 수 있는 표준만 사전 작성**.

그 지시는 두 가지를 동시에 요구한다. 이 파일은 **둘 다** 잰다:

    ① 표준이 서 있는가   — 포트 5종·수령 요건·오류 계약·설정 갈아끼우기 자리
    ② 그 이상을 안 만들었는가 — 엔드포인트·필드 이름·타입·오류 코드·Mock **없음**

②가 없으면 이 파일은 절반이다. 표준이 서 있다는 것만 재면, 어느 날 누가
"어차피 이 정도는 뻔하다" 며 필드 이름을 채워 넣어도 초록이 유지된다 —
그리고 명세가 도착하는 날 그 전부가 재작업이 된다 (D-280 · DA-02 §0).

왜 시험으로 잠그나
------------------
"만들지 않았다" 는 **오늘의 사실**이고, 사실은 내일 바뀐다. D-286 이 이름 붙인
실패 모양이 그것이다 — 문서에 적힌 금지는 지켜진 적이 없다.
"""
from __future__ import annotations

import ast
import inspect
from datetime import datetime, timedelta
from pathlib import Path

from django.test import SimpleTestCase

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "adapters.sdn (포트·수령요건·오류계약) · docs/design/DA-02_SDN_API_매핑서_v0.1_수령요건.md — "
    "저장소의 실제 패키지와 실제 계약 문서. 합성 더미를 부르지 않는다"
)

SDN_DIR = Path(__file__).resolve().parents[1] / "adapters" / "sdn"


# ═══════════════════════════════════════════════════════════════════════════
# ① 표준이 서 있는가
# ═══════════════════════════════════════════════════════════════════════════
class PortStandardExistsTest(SimpleTestCase):
    """연결할 자리가 **실제로** 있는가 — 문서가 아니라 코드에."""

    def test_five_contract_interfaces_have_a_port_method(self) -> None:
        """계약 [별첨1] §4 의 인터페이스 5종이 전부 포트에 자리를 갖는가.

        수가 아니라 **이름**으로 잠근다 (D-285 ②). 개수로 잠그면 하나가 지워질 때
        다른 하나가 들어올 자리가 생긴다.
        """
        from adapters.sdn import INTERFACES, PORT_METHODS, SdnPort

        self.assertEqual(
            {"I-1", "I-2", "I-3", "I-4", "I-5"}, set(INTERFACES),
            "계약이 정한 인터페이스 5종이 갈렸습니다 — 계약 본문입니다.")
        for code, methods in PORT_METHODS.items():
            for name in methods:
                self.assertTrue(
                    hasattr(SdnPort, name),
                    f"{code} 의 포트 메서드 {name} 이 없습니다.")
                self.assertIn(
                    name, SdnPort.__abstractmethods__,
                    f"{name} 이 추상 메서드가 아닙니다 — 구현하지 않아도 통과하면 "
                    f"그 포트는 계약이 아닙니다.")

    def test_calling_it_now_stops_and_says_why(self) -> None:
        """★ **조용한 성공을 만들지 않는다** (D-284 · D-290).

        구현이 없는 함수는 성공을 반환하지 않는다. None 도 빈 튜플도 아니고,
        **왜 못 하는지를 말하며 멈춘다.**
        """
        from adapters.sdn import QosIntent, SpecNotReceived, current

        with self.assertRaises(SpecNotReceived) as caught:
            current().request_qos(QosIntent(
                stream_monitor_id=1, reason="시험", hold_for=timedelta(minutes=5)))

        message = str(caught.exception)
        for token in ("3조2항", "2026-08-25", "DA-02", "D-280"):
            self.assertIn(token, message,
                          f"예외 메시지에 {token} 이 없습니다 — 로그 한 줄이 곧 "
                          f"독촉 근거가 되어야 합니다.")
        self.assertTrue(
            caught.exception.missing,
            "미수령 차단 항목이 비어 있습니다 — 무엇이 없어서 못 하는지 말하지 "
            "않는 예외는 '안 됨' 과 같습니다.")

    def test_every_interface_is_blocked_and_says_by_what(self) -> None:
        """다섯 인터페이스 **전부** 착수 불가이고, 그 사유가 항목으로 세어지는가."""
        from adapters.sdn import INTERFACES, can_start, missing_blocking

        for code in INTERFACES:
            self.assertFalse(
                can_start(code),
                f"{code} 가 착수 가능으로 나옵니다 — 명세를 받았다면 requirements.py 의 "
                f"received 와 이 시험을 같은 커밋에서 고치십시오.")
            self.assertTrue(missing_blocking(code),
                            f"{code} 의 미수령 A 등급 목록이 비었습니다.")

    def test_the_port_can_be_swapped_by_configuration(self) -> None:
        """DA-02 §3-5 — **Mock 도 실기도 같은 인터페이스.** 설정 한 줄로 갈아끼운다 (D-212).

        지금 Mock 을 만들 수는 없지만, **갈아끼우는 자리**는 지금 시험할 수 있다.
        시험이 꽂은 것은 시험이 뽑는다 — 전역 상태를 남기면 시험 순서가 결과를 바꾼다.
        """
        from adapters.sdn import (ControlReceipt, LinkStateNotice, SdnPort,
                                  UnavailableSdnPort, current, register)

        class _Stub(SdnPort):
            name = "stub"

            def request_qos(self, intent):
                return ControlReceipt(request_id="x", interface="I-1",
                                      requested_at=datetime.now(), dispatched=True)

            def request_reroute(self, intent):
                return ControlReceipt(request_id="x", interface="I-2",
                                      requested_at=datetime.now(), dispatched=True)

            def poll_link_states(self):
                return ()

            def on_link_state(self, notice: LinkStateNotice) -> None:
                return None

            def fetch_results(self, *, since):
                return ()

            def check_auth(self) -> bool:
                return True

        undo = register(_Stub())
        self.addCleanup(undo)
        self.assertEqual("stub", current().name)
        undo()
        self.assertIsInstance(current(), UnavailableSdnPort,
                              "되돌리기가 전역 상태를 남겼습니다.")

    def test_register_refuses_something_that_is_not_the_port(self) -> None:
        """양성 대조 — 아무거나 꽂히면 '같은 인터페이스' 라는 말이 빈말이 된다."""
        from adapters.sdn import register

        with self.assertRaises(TypeError):
            register(object())


# ═══════════════════════════════════════════════════════════════════════════
# ② 그 이상을 만들지 않았는가 — **여기가 이 파일의 요점이다**
# ═══════════════════════════════════════════════════════════════════════════
class NothingWasGuessedTest(SimpleTestCase):
    """★ 추측 금지의 시험판 (D-280 · DA-02 §0).

    "만들지 않았다" 는 오늘의 사실이고, 사실은 내일 바뀐다. 그래서 잠근다.
    """

    def _sources(self) -> dict[str, str]:
        return {p.name: p.read_text(encoding="utf-8")
                for p in sorted(SDN_DIR.glob("*.py"))}

    def test_no_mock_adapter_exists(self) -> None:
        """DA-02 §0 — **Mock 조차 못 만든다.** 없는 것이 옳다.

        Mock 이 생겼다는 것은 누군가 필드 이름을 정했다는 뜻이고, 정할 근거는
        명세뿐이다. 명세가 왔다면 이 시험과 `KERNEL_READY` 를 같은 커밋에서 고친다.
        """
        names = sorted(p.name for p in SDN_DIR.glob("*.py"))
        self.assertNotIn("mock.py", names,
                         "Mock 어댑터가 생겼습니다 — I-1~I-5 의 필드 이름과 타입 없이는 "
                         "Mock 도 추측입니다 (DA-02 §0).")
        for name, src in self._sources().items():
            self.assertNotIn(
                "class MockSdn", src,
                f"{name} 안에 Mock 어댑터가 있습니다 — 파일 이름만 피한 형태입니다.")

    def test_no_endpoint_urls_are_written_down(self) -> None:
        """엔드포인트는 저쪽이 정한다(1-1·2-1, A 등급). 한 줄도 적지 않았는가.

        문서 인용은 허용된다 — 계약·판정 문서의 이름이지 호출 대상이 아니다.
        """
        for name, src in self._sources().items():
            for line_no, line in enumerate(src.splitlines(), 1):
                if "http://" in line or "https://" in line:
                    self.fail(
                        f"{name}:{line_no} 에 URL 이 있습니다 — SDN 엔드포인트는 "
                        f"명세가 정합니다. 추측한 주소 위의 어댑터는 재작업 확정입니다.\n"
                        f"    {line.strip()}")

    def test_no_result_code_table_is_invented(self) -> None:
        """결과 코드표는 미수령이다(1-6, A 등급). 코드 열거를 만들지 않았는가."""
        for name, src in self._sources().items():
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                bases = {b.attr if isinstance(b, ast.Attribute) else
                         getattr(b, "id", "") for b in node.bases}
                self.assertFalse(
                    bases & {"Enum", "IntEnum", "StrEnum", "TextChoices"},
                    f"{name} 의 {node.name} 이 열거를 만듭니다 — SDN 의 결과 코드·"
                    f"상태값 열거는 명세가 정합니다 (1-6 · 3-5, 둘 다 A 등급).")

    def test_the_link_notice_stays_opaque(self) -> None:
        """I-3 통보는 **해석하지 않고 나른다** — 위치 매핑·상태값이 미수령이기 때문이다.

        `raw` 에서 필드를 꺼내 쓰는 코드가 생기면 그 이름이 우리 계약이 되고,
        명세가 오는 날 전부 고쳐야 한다 (DA-02 §3-2 · 3-4 · 3-5).
        """
        from adapters.sdn import LinkStateNotice

        fields = set(LinkStateNotice.__dataclass_fields__)
        self.assertEqual(
            {"link_ref", "received_at", "raw"}, fields,
            f"I-3 통보에 필드가 늘었습니다: {sorted(fields)}. 링크 상태값과 위치 매핑의 "
            f"형식은 미수령입니다 — 늘리려면 명세를 먼저 받으십시오.")

    def test_the_port_has_no_flight_command(self) -> None:
        """★ F-13 의 AC 는 **부정 조건**이다 — 승인 없이 비행 명령이 전송되지 않는다.

        포트에 비행 관련 메서드가 **없는 것**이 그 불변식의 구조적 표현이다.
        시험도 부정으로 쓴다 (DA-01 AC-13).
        """
        from adapters.sdn import SdnPort

        names = [n for n in dir(SdnPort) if not n.startswith("_")]
        for forbidden in ("fly", "takeoff", "dispatch_drone", "send_waypoint",
                          "arm", "mission"):
            self.assertFalse(
                [n for n in names if forbidden in n.lower()],
                f"SDN 포트에 비행 관련 메서드({forbidden})가 생겼습니다. F-13 은 "
                f"제안까지이고 비행 명령은 사람 승인 후에만 나갑니다 (AC-13).")


# ═══════════════════════════════════════════════════════════════════════════
# ③ 잠금이 실제로 잠겨 있는가 — E2E-3 은 아직 의무가 아니다
# ═══════════════════════════════════════════════════════════════════════════
class StillLockedTest(SimpleTestCase):
    """포트가 생겼다고 **시나리오가 열리면 안 된다** — 잴 수 없는 것을 재라고 요구하게 된다."""

    def test_sdn_is_not_present_for_e2e_yet(self) -> None:
        from tests.e2e.e2e_contract import SCENARIOS, kernel_present

        self.assertFalse(
            kernel_present("SDN"),
            "SDN 이 해금됐습니다 — 어댑터 구현과 E2E-3 시험 파일이 함께 있어야 합니다.")
        self.assertFalse(SCENARIOS["E2E-3"].unlocked)
        self.assertNotIn(7, {s.no for s in SCENARIOS["E2E-1"].active_steps},
                         "E2E-1 의 SDN 단계가 열렸습니다 — Mock 조차 없는데 잴 수 없습니다.")

    def test_not_ready_carries_a_reason(self) -> None:
        """★ **"안 됐다" 는 말은 사유를 요구한다** (D-264).

        사유 없는 False 는 "아직" 인지 "영영" 인지 구별되지 않고, 구별되지 않는 것은
        잊힌다. `scripts/verify_e2e_contract.py` 가 같은 것을 저장소 밖에서 본다.
        """
        from tests.e2e.e2e_contract import not_ready_reason

        reason = not_ready_reason("SDN")
        self.assertTrue(reason.strip(), "SDN 미준비 사유가 비었습니다.")
        self.assertIn("명세", reason)
        self.assertIn("6조3항", reason,
                      "사유에 계약 조항이 없습니다 — 이것은 기술 항목이 아니라 "
                      "계약 항목이고, 그 사실이 사유에 남아야 합니다 (D-297).")

    def test_positive_control_flipping_the_flag_would_unlock(self) -> None:
        """★ 양성 대조 (D-277) — **이 잠금은 잠글 수도 열 수도 있는가.**

        위 시험들은 전부 "잠겨 있다" 를 단언한다. 무슨 짓을 해도 잠겨 있는 술어라면
        그 초록은 아무것도 재지 않은 것이다. 그래서 여기서는 실제로 열어 본다 —
        그리고 되돌린다.
        """
        import adapters.sdn as sdn
        from tests.e2e.e2e_contract import kernel_present

        original = sdn.KERNEL_READY
        try:
            sdn.KERNEL_READY = True
            self.assertTrue(
                kernel_present("SDN"),
                "KERNEL_READY 를 올렸는데도 잠겨 있습니다 — 해금 술어가 이 값을 "
                "보고 있지 않습니다. 그렇다면 위의 '잠겨 있다' 도 뜻이 없습니다.")
        finally:
            sdn.KERNEL_READY = original
        self.assertFalse(kernel_present("SDN"), "되돌리기가 실패했습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ④ 명세와 코드가 갈리지 않는가
# ═══════════════════════════════════════════════════════════════════════════
class RequirementsMatchTheDocumentTest(SimpleTestCase):
    """수령 요건서(DA-02)와 `requirements.py` 는 **같은 것을 말해야 한다**.

    두 곳이 갈리면 어느 쪽이 계약인지 아무도 모른다 — D-227 이 만든 상황이 그것이었다.
    """

    DOC = (Path(__file__).resolve().parents[2] / "docs" / "design"
           / "DA-02_SDN_API_매핑서_v0.1_수령요건.md")

    def test_every_requirement_key_appears_in_the_document(self) -> None:
        self.assertTrue(self.DOC.is_file(), f"수령 요건서를 찾지 못했습니다: {self.DOC}")
        text = self.DOC.read_text(encoding="utf-8")

        from adapters.sdn import REQUIREMENTS

        missing = [r.key for r in REQUIREMENTS if f"| {r.key} " not in text]
        self.assertEqual(
            [], missing,
            f"코드에는 있고 문서에는 없는 수령 항목: {missing}. 문서가 정본이므로 "
            f"둘을 같은 커밋에서 고치십시오.")

    def test_nothing_is_marked_received_yet(self) -> None:
        """★ 하나라도 받았다면 **근거를 함께 적어야 한다** (D-289 실물 표본).

        `received=True` 만 적고 출처가 비면 그것은 문서가 아니라 기억이다.
        """
        from adapters.sdn import REQUIREMENTS

        for r in REQUIREMENTS:
            if r.received:
                self.assertTrue(
                    r.source.strip(),
                    f"{r.key} 를 받았다고 적었는데 근거(문서명·날짜)가 없습니다.")
        received = [r.key for r in REQUIREMENTS if r.received]
        self.assertEqual(
            [], received,
            f"수령 항목이 생겼습니다: {received}. 사실이라면 DA-02 를 v1.0 으로 승격하고 "
            f"이 시험을 같은 커밋에서 고치십시오 — 반가운 실패입니다.")
