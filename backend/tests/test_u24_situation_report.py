# -*- coding: utf-8 -*-
"""별지 제1호 **재난 상황보고** — 10칸이 다 있는가, 그리고 **훈련이 실사건에 안 새는가**
(WO-GX-20260921-04 §4-3 · 턴 AB · 차선 U24 · 2026-09-21).

왜 이 파일이 생겼나 — **턴 AA 에 「없다」를 재서 적었다**
--------------------------------------------------------
    [실측 2026-09-21 · 턴 AA] grep 「별지」·「제N보」·「13항목」·form1·situation_report
      → backend 에 **0건**.  명세서(DSM v1.1 DSM-U4-01)가 적어 둔 `form1` 이 없었다.

턴 AA 는 **서식을 짓지 않았다** — 지어 놓고 아무도 안 부르면 잠든 코드가 된다(D-377).
세종이 턴 AB 에 §4-3 으로 **필수 10칸**을 적었고, 이 파일은 그 10칸이
**완성된 종이에 실제로 있는지**를 센다. 문서 정본은
`docs/design/GX-FORM_별지1호_v1.0.md` 이고, 시험은 그 문서가 아니라 **종이**를 읽는다.

이 파일이 묻는 것
-----------------
① **10칸이 전부 있는가.** 한 칸이라도 빠지면 그 종이는 별지 1호가 아니다.
② **훈련 음성.** 실사건 종이에 「훈련」이 **0건**인가 — 턴 AA 에 `_CSS` 에 규칙 한 줄을
   뒀다가 실사건 HTML 에 그 낱말이 샜다. 그 함정을 **이 서식에서도** 막는다.
③ **피해 현황을 0 으로 안 적는가.** 「피해 0명」과 「아직 안 세었다」는 다른 사실이다.
④ **보고 구분을 유도하고, 유도했다고 적는가.** 그리고 모르면 **이른 쪽**으로 떨어지는가.
⑤ **조치가 시각 순인가.** 상황보고는 시각 순을 요구한다(§4-3).
⑥ **가린 다섯이 안 새는가.** 종이 전체에 `gxseed_*` **0건**.

무엇을 다시 묻지 않나
---------------------
택배 칸 0(`FORBIDDEN_FIELD_TOKENS`)의 **뜻**은 `test_incident_report.py` 가 적었다.
여기서는 같은 목록을 **이 서식에 대해** 한 번 훑기만 한다 — 「같은 데서 나왔으니
같을 것이다」는 검사가 아니기 때문이다(`docx_export` 머리말과 같은 규율).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from apps.dsm import incident_report as form
from tests.test_dsm_app import DsmFixture
from tests.test_role_gate import _CleanThreadLocal

#: ★ D-289 — 표본은 저장소 실물이다. 합성 더미를 부르지 않는다.
REAL_SAMPLE = (
    "apps.dsm.incident_report.build_situation_html · build_situation_report · "
    "kernels.k4_report.build_context · apps.dsm.services.response_clock · "
    "실제 DetectionEvent 행"
)

#: 세종 §4-3 의 10칸 중 **종이에 글자로 찍히는 아홉**. ⑩(훈련 배너)은 칸이 아니라
#: 첫 줄이라 따로 잰다(`ThePaperSaysItIsADrillTest`).
TEN_BOXES = (
    "보고 구분", "보고 일시", "보고 기관", "보고자", "재난 종류",
    "발생 일시", "발생 장소", "피해 현황", "조치 사항", "향후 계획", "첨부",
)


class _Situation(_CleanThreadLocal, DsmFixture):
    """별지 1호 HTML 을 만드는 도우미. **DOCX 를 안 찍는다** — 여기서 재는 것은 글자다."""

    def _html(self, event_id: int, *, plan: str = "") -> str:
        return form.build_situation_report(
            scope=self.scope_a, event_id=event_id, plan=plan)

    def _drill_event(self) -> int:
        """훈련 표식을 **행에 얹어** 실제로 기록한다(`test_incident_report` 와 같은 길)."""
        from common.probe_marker import drill_mark
        from kernels.k1_event import record_detection

        return record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream_a.pk,
            event_type="fire", severity="critical",
            snapshot_path="minio://dsm/drill.jpg",
            track_id=drill_mark("20260921T000000")).event_id


class TheTenBoxesAreAllOnThePaperTest(_Situation):
    """① 10칸 — **한 칸이라도 빠지면 그 종이는 별지 1호가 아니다.**"""

    def test_every_required_box_is_printed(self) -> None:
        html = self._html(self._event(self.stream_a))
        missing = [box for box in TEN_BOXES if box not in html]
        self.assertEqual(
            [], missing,
            f"별지 1호에 필수 칸이 빠졌습니다: {missing}. "
            f"세종 WO-04 §4-3 이 적은 칸입니다 — 빠진 칸이 있으면 받는 기관은 "
            f"이 종이를 별지 1호로 접수하지 못합니다.")

    def test_the_boxes_carry_their_numbers(self) -> None:
        """받는 사람이 「⑥이 비었다」고 전화로 말할 수 있어야 한다 — 번호가 그 말이다."""
        html = self._html(self._event(self.stream_a))
        for mark in ("①", "④", "⑥", "⑦", "⑧", "⑨"):
            self.assertIn(mark, html, f"칸 번호 {mark} 가 종이에 없습니다.")

    def test_no_courier_field_on_this_paper_either(self) -> None:
        """택배 칸 0 — 앞 서식 셋과 **같은 목록**을 이 서식에도 훑는다."""
        html = self._html(self._event(self.stream_a))
        found = [t for t in form.FORBIDDEN_FIELD_TOKENS if t in html]
        self.assertEqual([], found, f"별지 1호에 택배 운송장 칸이 남아 있습니다: {found}")

    def test_no_placeholder_survives(self) -> None:
        self.assertNotIn("{{", self._html(self._event(self.stream_a)))


class TheDamageBoxIsNeverZeroTest(_Situation):
    """③ 피해 현황 — **「0」으로 적지 않는다.**

    「피해 0명」과 「아직 안 세었다」는 다른 사실이고, 결재는 전자로 읽는다(D-290).
    """

    def test_the_damage_box_says_it_is_being_counted(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertIn(form.DAMAGE_PENDING, html)
        self.assertIn("인명 피해", html)
        self.assertIn("재산 피해", html)

    def test_the_paper_says_why_there_is_no_number(self) -> None:
        """가린 것을 숨기면 거짓말이듯, **못 센 것을 숨겨도 거짓말이다.**"""
        html = self._html(self._event(self.stream_a))
        self.assertIn("보관하지 않습니다", html)

    def test_the_damage_box_never_prints_a_zero_count(self) -> None:
        html = self._html(self._event(self.stream_a))
        block = html.split("피해 현황", 1)[1].split("<h2>", 1)[0]
        for lie in ("0명", "0건", "없음</td>"):
            self.assertNotIn(
                lie, block,
                f"피해 현황 칸에 「{lie}」가 찍혔습니다 — 우리는 피해를 세지 않습니다. "
                f"그 글자는 「피해가 없었다」로 읽힙니다.")


class TheStageIsDerivedAndSaysSoTest(_Situation):
    """④ 보고 구분 — 유도하고, **유도했다고 적는다.** 모르면 **이른 쪽**이다."""

    def test_each_state_maps_to_its_stage(self) -> None:
        self.assertEqual(form.STAGE_FINAL, form.report_stage("closed")[0])
        self.assertEqual(form.STAGE_MIDDLE, form.report_stage("in_progress")[0])
        self.assertEqual(form.STAGE_MIDDLE, form.report_stage("acknowledged")[0])
        self.assertEqual(form.STAGE_FIRST, form.report_stage("occurred")[0])

    def test_an_unknown_state_falls_to_the_earliest_stage(self) -> None:
        """★ 「최종 보고」가 잘못 나가면 받는 쪽이 그 사건을 **닫는다.**"""
        stage, why = form.report_stage("")
        self.assertEqual(form.STAGE_FIRST, stage)
        self.assertIn("읽지 못했습니다", why)
        self.assertEqual(form.STAGE_FIRST, form.report_stage("낯선상태")[0])

    def test_the_paper_prints_the_reason_next_to_the_stage(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertIn("보고 구분", html)
        self.assertIn("사건입니다", html,
                      "보고 구분 옆에 「무엇을 보고 그렇게 적었는가」가 없습니다 — "
                      "사람이 고른 값이 아니므로 종이가 스스로 말해야 합니다.")

    def test_no_report_number_is_invented(self) -> None:
        """⚠ **제N보 채번을 하지 않는다** — 그 수를 담는 대장이 제품에 없다."""
        html = self._html(self._event(self.stream_a))
        for invented in ("제1보", "제 1 보", "1보"):
            self.assertNotIn(
                invented, html,
                f"종이에 「{invented}」가 찍혔습니다. 채번 대장이 없는데 수를 찍으면 "
                f"다음 보고가 그 수와 어긋납니다.")


class TheActionsAreInTimeOrderTest(_Situation):
    """⑤ 조치 사항 — **시각 순**(§4-3). 시각 없는 줄은 **뒤로** 민다."""

    class _Row:
        """K4 `ActionRow` 가 내는 칸만 가진 자리 — 정렬 규칙 하나를 잰다."""

        def __init__(self, sent_at, channel="log"):
            self.sent_at = sent_at
            self.channel = channel
            self.recipient_address = "a@org.kr"
            self.succeeded = True
            self.failure_reason = ""

    def _rendered(self, rows) -> str:
        return form.build_situation_html(
            event=_FakeEvent(), clock={"response_state": "occurred"},
            actions=rows, tenant="기관", issued_by="담당", data_source="live")

    def test_rows_are_sorted_by_sent_at(self) -> None:
        base = datetime(2026, 9, 21, 3, 0, 0)
        rows = [self._Row(base + timedelta(minutes=30), "webpush"),
                self._Row(base, "email")]
        html = self._rendered(rows)
        self.assertLess(
            html.index("email"), html.index("webpush"),
            "조치 사항이 시각 순이 아닙니다 — 상황보고를 읽는 사람은 위에서 아래로 "
            "시간이 흐른다고 읽습니다.")

    def test_rows_without_a_stamp_go_last(self) -> None:
        """시각 없는 줄이 앞에 오면 **「가장 먼저 한 조치」**로 읽힌다."""
        rows = [self._Row(None, "webpush"),
                self._Row(datetime(2026, 9, 21, 3, 0, 0), "email")]
        html = self._rendered(rows)
        self.assertLess(html.index("email"), html.index("webpush"))

    def test_the_given_list_is_not_mutated(self) -> None:
        """받은 배열을 **안 건드린다** — 부르는 쪽의 자료를 서식이 바꾸지 않는다."""
        a = self._Row(datetime(2026, 9, 21, 3, 30, 0))
        b = self._Row(datetime(2026, 9, 21, 3, 0, 0))
        rows = [a, b]
        self._rendered(rows)
        self.assertIs(a, rows[0])


class ThePlanBoxStaysEvenWhenEmptyTest(_Situation):
    """⑧ 향후 계획 — **비어도 칸은 남는다.**

    칸이 사라지면 「계획이 없었다」와 「아무도 안 적었다」를 가를 수 없다.
    """

    def test_the_box_is_there_when_nobody_wrote_anything(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertIn("향후 계획", html)
        self.assertIn("기재된 향후 계획이 없습니다", html)

    def test_what_a_person_wrote_lands_on_the_paper(self) -> None:
        html = self._html(self._event(self.stream_a), plan="야간 순찰 2회 추가")
        self.assertIn("야간 순찰 2회 추가", html)
        self.assertNotIn("기재된 향후 계획이 없습니다", html)


class TheAttachmentBoxNamesButDoesNotAttachTest(_Situation):
    """⑨ 첨부 — **이름만 적는다.** 원본 영상은 안 붙인다(계약 11조)."""

    def test_the_three_attachment_lines_are_named(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertIn("사건 1쪽 보고서", html)
        self.assertIn("해시 체인 증명", html)
        self.assertIn("영상 구간", html)

    def test_the_paper_says_the_clip_is_not_attached(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertIn("원본 영상은 이 종이에 붙이지 않습니다", html)

    def test_there_is_no_image_on_this_paper(self) -> None:
        """그림 0장 — `docx_export` 머리말의 약속이 이 서식에도 걸린다."""
        self.assertNotIn("<img", self._html(self._event(self.stream_a)))


class ThePaperSaysItIsADrillTest(_Situation):
    """② ★ **음성부터 잰다.** 실사건 종이에 「훈련」이 0건인가.

    턴 AA 에 `_CSS` 에 `.banner.drill` 규칙과 그 위 한글 주석을 뒀더니 **실사건 종이의
    HTML 에도** 「훈련」·`drill` 글자가 들어갔다 — 찍힌 종이에는 안 보이지만
    (DOCX 변환이 `<style>` 을 떼어낸다) HTML 을 훑어 재는 사람에게는 **실사건에 훈련
    표시가 있는 것으로 보인다.** 그 함정을 이 서식에서도 막는다.
    """

    def test_a_real_event_carries_no_drill_word(self) -> None:
        html = self._html(self._event(self.stream_a))
        self.assertNotIn(
            "훈련", html,
            "실사건의 별지 1호에 「훈련」이 들어갔습니다. 배너 조건이 너무 넓거나, "
            "서식(CSS·주석)에 그 낱말이 새고 있습니다.")

    def test_a_real_event_carries_no_drill_token(self) -> None:
        """글자 `drill` 도 0건이다 — 우리 표식이 고객 종이에 남지 않는다."""
        self.assertNotIn("drill", self._html(self._event(self.stream_a)))

    def test_a_drill_event_carries_the_banner(self) -> None:
        html = self._html(self._drill_event())
        self.assertIn("훈련", html)
        self.assertIn("실제 재난 상황이 아닙니다", html)

    def test_the_banner_is_the_first_thing_on_the_page(self) -> None:
        """표를 먼저 읽은 뒤에 「훈련이었다」를 알면 **이미 한 번 실제로 읽은 것**이다."""
        html = self._html(self._drill_event())
        body = html.split("<body>", 1)[1]
        self.assertLess(body.index("훈련"), body.index("보고 구분"))


class ThePaperHidesTheFiveTest(_Situation):
    """⑥ 가림 다섯이 **이 서식에서도** 선다 — 회귀 0."""

    def test_no_account_name_on_the_paper(self) -> None:
        """종이 전체에 `gxseed_` **0건.** 계정명은 로그인에 쓰는 내부 식별자다."""
        html = self._html(self._event(self.stream_a))
        self.assertNotIn(
            "gxseed_", html,
            "별지 1호에 계정명이 찍혔습니다 — 감사에게 나가는 종이에 로그인 이름이 "
            "박히면 받는 사람은 그것을 조직의 사람 목록으로 읽습니다.")

    def test_no_recipient_id_on_the_paper(self) -> None:
        """메일 아이디는 한 글자도 안 남는다. **도메인만** 남는다."""
        html = form.build_situation_html(
            event=_FakeEvent(), clock={"response_state": "occurred"},
            actions=[_Recipient("geumsan@org.kr", "log")],
            tenant="기관", issued_by="담당", data_source="live")
        self.assertNotIn("geumsan", html)
        self.assertIn("org.kr", html)

    def test_no_device_token_on_the_paper(self) -> None:
        html = form.build_situation_html(
            event=_FakeEvent(), clock={"response_state": "occurred"},
            actions=[_Recipient("drill:webpush:dc716379fa14", "webpush")],
            tenant="기관", issued_by="담당", data_source="live")
        self.assertNotIn("dc716379fa14", html)

    def test_the_paper_says_it_hid_things(self) -> None:
        """**가린 사실을 숨기면 그것도 거짓말이다.**"""
        self.assertIn(form.MASK_FOOTNOTE, self._html(self._event(self.stream_a)))

    def test_the_address_stops_at_the_administrative_unit(self) -> None:
        html = form.build_situation_html(
            event=_FakeEvent(address="경기도 안양시 만안구 안양천서로 100 (시드 카메라)"),
            clock={"response_state": "occurred"}, actions=[],
            tenant="기관", issued_by="담당", data_source="live")
        self.assertNotIn("안양천서로 100", html)
        self.assertIn("만안구", html)


class TheDocxIsARealDocxTest(_Situation):
    """정본은 DOCX 다 — **0바이트는 성공이 아니고**, 완성된 파일에도 계정명이 없다."""

    def test_the_bytes_are_a_zip_that_word_opens(self) -> None:
        from apps.dsm import docx_export

        data = docx_export.html_to_docx_bytes(
            self._html(self._event(self.stream_a)),
            title=form.SITUATION_TITLE, header=form.SITUATION_TITLE)
        self.assertTrue(data.startswith(b"PK"), "DOCX(zip) 모양이 아닙니다.")
        self.assertGreater(len(data), 1024)

    def test_the_finished_docx_carries_no_account_name(self) -> None:
        """HTML 에서 잰 것을 **완성된 파일에서 다시 잰다** — 「같은 데서 나왔으니
        같을 것이다」는 검사가 아니다."""
        import io
        import zipfile

        from apps.dsm import docx_export

        data = docx_export.html_to_docx_bytes(
            self._html(self._event(self.stream_a)),
            title=form.SITUATION_TITLE, header=form.SITUATION_TITLE)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            text = zf.read("word/document.xml").decode("utf-8", "replace")
        self.assertNotIn("gxseed_", text)
        self.assertNotIn("훈련", text,
                         "실사건 DOCX 에 「훈련」이 있습니다 — 배너가 새고 있습니다.")


class EveryTableHasItsWidestRowFirstTest(_Situation):
    """★★ **DOCX 변환이 첫 줄로 표의 칸 수를 정한다** — [실측 2026-09-21 · 턴 AB].

    이 시험은 **고장에서 나왔다.** 별지 1호의 ①②③ 표를 `_row`·`_row`·`_pair` 로
    썼더니 HTML 은 멀쩡한데 DOCX 가 **`IndexError: list index out of range`** 로
    죽었다 — 종이가 아예 안 나왔다.

        [실측 · 같은 변환기에 네 모양]
          _row · _row · _pair  → FAIL(IndexError)   ← 좁은 줄이 먼저
          _pair · _row · _row  → OK                 _row×3 → OK   _pair×2 → OK

    `_row` 는 `colspan="3"` 이라 **눈에는 네 칸이지만 셀은 둘**이다. 그 차이가 전부다.
    그래서 규칙을 **글자가 아니라 시험으로** 못 박는다 — 서식 넷 전부에 건다.
    ⚠ **HTML 만 보면 이 고장은 안 보인다.** 그래서 아래 `TheDocxIsARealDocxTest` 가
      완성된 바이트까지 간다. 이 시험은 그보다 **먼저 · 더 좁게** 사유를 말한다.
    """

    @staticmethod
    def _widest_row_is_first(html: str) -> list[str]:
        """첫 줄보다 넓은 줄을 가진 표를 찾아 돌려준다(빈 목록이면 안전)."""
        import re

        bad: list[str] = []
        for table in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S):
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
            widths = [len(re.findall(r"<t[hd][^>]*>", r)) for r in rows]
            if widths and max(widths) > widths[0]:
                bad.append(f"첫 줄 {widths[0]}칸 · 가장 넓은 줄 {max(widths)}칸")
        return bad

    def test_the_situation_form_keeps_the_rule(self) -> None:
        bad = self._widest_row_is_first(self._html(self._event(self.stream_a)))
        self.assertEqual(
            [], bad,
            f"별지 1호에 첫 줄보다 넓은 줄을 가진 표가 있습니다: {bad}. "
            f"DOCX 변환기가 첫 줄로 칸 수를 잡으므로 이 표는 **종이를 통째로 죽입니다** "
            f"(`docx_export` 머리말 「표의 첫 줄이 칸 수를 정한다」).")

    def test_the_one_page_incident_form_keeps_the_rule_too(self) -> None:
        """서식 넷이 **같은 규칙** 아래 있다 — 한 서식만 지키면 다음 서식이 밟는다."""
        from kernels.k4_report import build_context

        from apps.dsm import services

        eid = self._event(self.stream_a)
        context = build_context(scope=self.scope_a, event_id=eid)
        html = form.build_html(
            event=list(context.events)[0],
            clock=services.response_clock(scope=self.scope_a, event_id=eid),
            actions=context.actions, tenant="기관", issued_by="담당",
            data_source="live")
        self.assertEqual([], self._widest_row_is_first(html))


class _Recipient:
    """가림 시험이 쓰는 한 줄. K4 `ActionRow` 가 내는 칸 이름만 갖는다."""

    def __init__(self, address: str, channel: str):
        self.recipient_address = address
        self.channel = channel
        self.sent_at = datetime(2026, 9, 21, 3, 0, 0)
        self.succeeded = True
        self.failure_reason = ""


class _FakeEvent:
    """서식이 **DB 를 안 만진다**는 사실을 이 자리가 증명한다 — 인자로 받은 값만 그린다.

    ⚠ 이것은 **제품 경로의 대역이 아니다.** 제품 경로는 위 `_Situation._html` 이
      실제 사건으로 탄다. 이 자리는 「서식 함수 하나」를 DB 없이 재는 데만 쓴다.
    """

    def __init__(self, address: str = "경기도 안양시 만안구"):
        self.event_id = 1
        self.event_type = "fire"
        self.severity = "critical"
        self.occurred_at = datetime(2026, 9, 21, 3, 0, 0)
        self.stream_monitor_name = "카메라 1"
        self.address = address
        self.address_status = ""
