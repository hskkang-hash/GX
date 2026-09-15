# -*- coding: utf-8 -*-
"""사건 보고서 1쪽 — **택배 칸 0개인가, 그리고 사건 id 가 종이를 바꾸는가**
(UX-30 · P-125 · 차선 B · 2026-09-10).

이 파일이 묻는 것 넷
--------------------
① **택배 칸이 0인가.** 실측이 이 시험을 낳았다: 재난안전과 공무원이 손으로 부른
   `GET /api/dsm/reports/7.pdf` 가 **「배송 완료 보고서」**(Sender Name · Recipient Name ·
   Delivery Fee · Tax Amount · ETRI Receipt ID)를 냈고, `?event_id=4802` 를 붙여도
   **바이트가 한 글자도 안 바뀌었다**(md5 동일).

② **사건 id 가 종이를 바꾸는가.** ①의 뿌리는 「서식에 꽂을 자리가 없다」였다.
   그래서 이 시험은 두 사건의 종이가 **다른지**를 직접 본다 — 같으면 그때와 같은 상태다.

③ **판정자가 사람 이름인가.** `#105` 같은 내부 id 가 감사에게 나가는 종이에 찍히면
   받는 사람은 그것을 사람으로 읽는다. 이름이 없으면 **없다고 적는다**(D-290 계열).

④ **없는 시각을 0 으로 적지 않는가.** 「아무도 접수 안 함」이 「즉시 접수」로 보이는
   그 자리다 — `test_c_response_clock` 이 값에 대해 잰 것을 여기서는 **종이에 대해** 잰다.

무엇을 다시 묻지 않나
---------------------
네 시각을 세우는 계산은 `tests/test_c_response_clock.py` 가, 전이 규칙은
`tests/test_response_flow.py` 가 잰다. 여기서 다시 재면 두 벌이 된다.
"""
from __future__ import annotations

from django.http import Http404

from apps.dsm import incident_report as form
from tests.test_dsm_app import DsmFixture
from tests.test_role_gate import _CleanThreadLocal

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.incident_report(서식) · apps.dsm.services.incident_report · "
    "kernels.k4_report(build_context · render_html) · "
    "stream_monitors.services.response_clock · 실제 DetectionEvent 행 — "
    "합성 더미를 부르지 않는다"
)


class _Report(_CleanThreadLocal, DsmFixture):
    """서식 HTML 을 만드는 도우미. **PDF 를 찍지 않는다** — 여기서 재는 것은 내용이다."""

    def _html(self, event_id: int) -> str:
        from kernels.k4_report import build_context

        context = build_context(scope=self.scope_a, event_id=event_id)
        clock = self._services().response_clock(scope=self.scope_a, event_id=event_id)
        return form.build_html(
            event=list(context.events)[0], clock=clock, actions=context.actions,
            tenant=form.tenant_name(self.user_a),
            issued_by=form.person_label(self.user_a),
            sources_failed=tuple(context.sources_failed))

    @staticmethod
    def _services():
        from apps.dsm import services

        return services


class NoCourierFieldOnThePageTest(_Report):
    """① UX-30 검수 조건 그대로 — **택배 필드 0**."""

    def test_the_page_carries_none_of_the_waybill_fields(self) -> None:
        html = self._html(self._event(self.stream_a))
        found = [token for token in form.FORBIDDEN_FIELD_TOKENS if token in html]
        self.assertEqual(
            [], found,
            f"사건 보고서에 택배 운송장 칸이 남아 있습니다: {found}. "
            f"이 종이는 재난안전과에 나갑니다 — 배송 칸이 하나라도 있으면 "
            f"받는 사람은 이 제품이 무엇인지 다시 묻습니다.")

    def test_no_placeholder_survives_on_the_page(self) -> None:
        """`{{ … }}` 가 종이에 남으면 **치환이 안 된 것**이다 — 실측이 그 모양이었다."""
        html = self._html(self._event(self.stream_a))
        self.assertNotIn(
            "{{", html,
            "치환되지 않은 자리표시자가 종이에 남았습니다 — reports/7.pdf 가 "
            "`{{ order__sender_name }}` 를 그대로 인쇄한 그 상태입니다.")


class TheEventIdChangesThePaperTest(_Report):
    """② **사건 id 가 종이를 바꾸는가.** 안 바뀌면 P-125 그 상태다."""

    def test_two_events_do_not_produce_the_same_page(self) -> None:
        first = self._html(self._event(self.stream_a, event_type="fire"))
        second = self._html(self._event(self.stream_a, event_type="flood",
                                        severity="warning"))
        self.assertNotEqual(
            first, second,
            "서로 다른 두 사건이 **같은 종이**를 냈습니다 — `reports/7.pdf` 가 "
            "`?event_id=` 를 붙여도 md5 가 같았던 그 상태입니다.")

    def test_the_page_names_the_event_and_its_grade_in_korean(self) -> None:
        eid = self._event(self.stream_a, event_type="fire", severity="critical")
        html = self._html(eid)
        for expected in ("사건 보고서", "사건번호", str(eid), "심각", "화재",
                         self.stream_a.name):
            self.assertIn(expected, html, f"종이에 「{expected}」 가 없습니다.")
        for code in ("critical", "fire"):
            self.assertNotIn(
                f">{code}<", html,
                f"등급·유형이 코드값({code})으로 인쇄됐습니다 — 고객의 언어가 아닙니다.")


class TheFourStampsAreOnThePageTest(_Report):
    """④ 네 시각 — **없으면 「기록 없음」이고 0 이 아니다** (D-290)."""

    LABELS = ("발생", "접수", "조치 시작", "종결")

    def test_the_four_labels_are_always_printed(self) -> None:
        html = self._html(self._event(self.stream_a))
        for label in self.LABELS:
            self.assertIn(label, html, f"대응 시계의 「{label}」 칸이 없습니다.")

    def test_a_missing_stamp_is_not_printed_as_zero(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertIn(
            form.UNKNOWN, html,
            "아직 일어나지 않은 시각이 「기록 없음」으로 적히지 않았습니다.")
        self.assertNotIn(
            "0초", html,
            "일어나지 않은 구간이 「0초」로 인쇄됐습니다 — 그 종이는 「즉시 대응」으로 "
            "읽힙니다(D-290).")

    def test_the_stamps_appear_after_the_transitions(self) -> None:
        services = self._services()
        eid = self._event(self.stream_a)
        for state in ("acknowledged", "in_progress", "closed"):
            services.advance_response(scope=self.scope_a, event_id=eid,
                                      to_state=state)
        clock = services.response_clock(scope=self.scope_a, event_id=eid)
        html = self._html(eid)
        for name in ("acknowledged_at", "arrived_at", "closed_at"):
            self.assertIsNotNone(clock[name])
            self.assertIn(
                form._when(clock[name]), html,
                f"{name} 이 세워졌는데 종이에 안 실렸습니다.")


class TheReviewerIsAPersonNotAnIdTest(_Report):
    """③ **판정자 칸에 내부 id 를 찍지 않는다.**"""

    def test_a_named_reviewer_is_printed_by_name(self) -> None:
        from kernels.k1_event import review_event

        eid = self._event(self.stream_a)
        self.user_a.first_name = "홍길동"
        self.user_a.save(update_fields=["first_name"])
        review_event(eid, scope=self.scope_a, verdict="rejected",
                     reason="하천 둔치 소각 — 신고 확인됨")
        html = self._html(eid)

        self.assertIn("홍길동", html, "판정자의 이름이 종이에 없습니다.")
        self.assertIn("하천 둔치 소각 — 신고 확인됨", html,
                      "판정 사유가 종이에 없습니다.")
        self.assertNotIn(
            f"#{self.user_a.pk}", html,
            "판정자가 내부 id 로 인쇄됐습니다 — 감사는 그것을 사람 이름으로 읽습니다.")

    def test_an_account_without_a_real_name_says_so(self) -> None:
        """이름이 없으면 **없다고 적는다.** 조용히 id 로 떨어지지 않는다."""
        label = form.person_label(self.user_b)          # 실명이 없는 계정
        self.assertIn("실명 미등록", label)
        self.assertNotIn(str(self.user_b.pk), label)

    def test_a_vanished_account_is_named_as_unknown(self) -> None:
        self.assertIn("확인 불가", form.reviewer_label(9_999_999))
        self.assertNotIn("9999999", form.reviewer_label(9_999_999))

    def test_an_unjudged_event_says_unjudged(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertIn("미판정", html)


class ThePaperSaysWhichClockItUsedTest(_Report):
    """**두 시간 어긋난 종이를 조용히 내보내지 않는다** [실측 2026-09-10].

    이 서버의 `TIME_ZONE` 은 `Asia/Ho_Chi_Minh`(UTC+07:00)이고, 그래서 사건 시각이
    한국 시각보다 **두 시간 이르게** 찍힌다. 고칠 자리는 배포 설정이지만, 그 전까지
    종이는 **자기가 어느 시계로 적혔는지 말해야 한다** — 말하지 않으면 받는 사람은
    그것을 한국 시각으로 읽는다.
    """

    def test_the_footer_names_the_clock(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertIn("서버 표준시", html,
                      "종이가 어느 시계로 적혔는지 말하지 않습니다.")
        self.assertIn("UTC", html)

    def test_the_note_follows_the_setting_not_a_hardcoded_zone(self) -> None:
        """설정을 바꾸면 이 줄도 바뀐다 — **손으로 고칠 자리가 없다.**"""
        from django.test import override_settings

        with override_settings(TIME_ZONE="Asia/Seoul"):
            self.assertIn("+09:00", form.timezone_note())
        with override_settings(TIME_ZONE="UTC"):
            self.assertIn("+00:00", form.timezone_note())


class TheGateStandsOnThisRouteTest(_CleanThreadLocal, DsmFixture):
    """**남의 사건은 종이가 안 나온다.** 404 다 — 403 이 아니다 (D-269)."""

    def test_another_tenants_event_is_404(self) -> None:
        from apps.dsm import services

        eid = self._event(self.stream_b)                 # 테넌트 B 의 사건
        with self.assertRaises(Http404):
            services.incident_report(scope=self.scope_a, event_id=eid)

    def test_a_missing_event_is_404(self) -> None:
        from apps.dsm import services

        with self.assertRaises(Http404):
            services.incident_report(scope=self.scope_a, event_id=9_999_999)


class TheBytesAreAPdfTest(_CleanThreadLocal, DsmFixture):
    """**끝까지 간다** — 서식이 실제 엔진을 통과해 PDF 바이트가 되는가.

    ★ 이 시험이 없으면 「HTML 은 맞는데 종이는 안 나온다」가 초록으로 남는다 —
      착시 ⑨(함수는 초록이고 문은 죽어 있다)의 정확히 같은 모양이다.
    """

    def test_the_service_returns_real_pdf_bytes(self) -> None:
        from apps.dsm import services

        eid = self._event(self.stream_a)
        pdf = services.incident_report(scope=self.scope_a, event_id=eid)

        self.assertTrue(pdf.startswith(b"%PDF"),
                        "PDF 서명으로 시작하지 않습니다 — 이것은 PDF 가 아닙니다.")
        self.assertGreater(
            len(pdf), 1000,
            "1KB 도 안 되는 PDF 입니다 — 빈 PDF 는 열리기는 하고 내용이 없습니다(D-284).")

    def test_the_engine_refuses_empty_html(self) -> None:
        """K4 `render_html` 은 **빈 종이를 성공으로 내지 않는다** (D-284)."""
        from kernels.k4_report import InvalidReportInput, render_html

        with self.assertRaises(InvalidReportInput):
            render_html(scope=self.scope_a, html="   ")
