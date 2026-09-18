# -*- coding: utf-8 -*-
"""U24 · 턴 U (P-173) — 보고서 서식 3 · 실행 기록 · 파일 2(DOCX 정본 · PDF 병행) · 감사 체인/CSV.

이 파일이 잰다
--------------
  ① 서식 3 — 사건 1쪽(`incident`) · 「이번 달 우리 센터」 자동본(`monthly`) ·
    상급 제출용(`upper`). 셋 다 `DsmReportRun` 한 행을 남긴다(무엇을 · 자동인가 · 끝났나).
  ② **택배 필드 0** — 완성된 **DOCX 의 글자**를 다시 센다. 「같은 HTML 에서 나왔으니
    같을 것이다」는 검사가 아니다(D-284 계열). 배송·주문·단말·delivery·order·terminal 0회.
  ③ 파일 2 — `.docx` 는 `PK` 로 시작(zip) · `.pdf` 는 `%PDF` 로 시작 · 둘 다 > 1KB ·
    `Cache-Control: no-store` · 원본 스냅샷 경로 무반출.
  ④ 격리 — 남의 테넌트 실행 기록은 **404**(403 이 아니다 · 존재를 알리지 않는다) ·
    남의 사건으로 만들기 404 · 그때 실행 기록 행이 **생기지 않는다**.
  ⑤ 자격 — 익명 401 · 관제요원(fire_user) 403 · 팀장(fire_admin) 200 · 읽기 전용(U4) 200.
  ⑥ 집계 재사용 — 월간본의 「전체 사건 수」는 `stats.stats_summary` 의 `total` 과 같다
    (손 SQL 0 · 두 번 세지 않는다).
  ⑦ 감사 — `/audit` 항목에 `prev_hash`·`hash`·`chain` 세 칸 · 이어진 행은 `linked` ·
    `/audit/export.csv` 는 BOM + 머리 1행 + `no-store`.
  ⑧ 배치 — `monthly_report.run_monthly(group=…)` 가 **자동본**(`trigger=auto`) 한 행을 낸다.

무엇을 다시 묻지 않나
---------------------
집계 자체(`test_u24_stats.py`) · 감사 체인의 위조 검증(`evidence_chain` 시험) ·
K1 문지기(`test_tenant_isolation.py`)는 각자의 시험이 잰다. 여기서는 **보고서 면이
그것을 잃지 않고 쓰는가**만 묻는다.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

RUNS = "/api/dsm/reports/runs"
AUDIT = "/api/dsm/audit"
AUDIT_CSV = "/api/dsm/audit/export.csv"

REAL_SAMPLE = (
    "apps.dsm.api_u24.DsmU24API · apps.dsm.monthly_report · apps.dsm.docx_export · "
    "apps.dsm.incident_report · stream_monitors.DsmReportRun — 저장소의 실제 라우트·모델"
)

#: 「택배 필드 0」 — 이 낱말이 종이에 한 칸이라도 있으면 빨강이다. 지시서가 센다.
FORBIDDEN_WORDS = ("배송", "주문", "단말", "운송장", "택배", "delivery", "order", "terminal")


def _visible_text(html: str) -> str:
    """HTML 에서 **종이에 인쇄되는 글자**만. 스타일·표시는 종이가 아니다."""
    import re

    from apps.dsm import docx_export

    return re.sub(r"<[^>]+>", " ", docx_export.body_of(html))


def _docx(run_id: int) -> str:
    return f"{RUNS}/{run_id}.docx"


def _pdf(run_id: int) -> str:
    return f"{RUNS}/{run_id}.pdf"


class ReportFixture(DsmFixture):
    """역할 넷 — 팀장(U2) · 읽기 전용(U4) · 관제요원(U1) · B 테넌트 팀장."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        cls.manager_a = cls._user(
            "u24u_manager_a", cls.group_a, cls._own(cls._role("fire_admin"), cls.group_a))
        cls.viewer_a = cls._user(
            "u24u_viewer_a", cls.group_a,
            cls._own(cls._role("view_only_-_u24u"), cls.group_a))
        cls.operator_a = cls._user(
            "u24u_operator_a", cls.group_a, cls._own(cls._role("fire_user"), cls.group_a))
        cls.manager_b = cls._user(
            "u24u_manager_b", cls.group_b, cls._own(cls._role("fire_admin_b"), cls.group_b))
        cls.manager_b.roles.add(cls._own(cls._role("surveillance_order"), cls.group_b))

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self._clear_thread_request()

    def tearDown(self) -> None:
        #: HTTP 를 때린 시험이 스레드에 요청을 남기면 뒤 시험의 `objects` 가 빈다
        #: (메모리 「스레드에 남은 요청이 거짓 초록을 만든다」).
        self._clear_thread_request()
        super().tearDown()

    @staticmethod
    def _clear_thread_request() -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

    # ── 도우미 ───────────────────────────────────────────────────────────
    def _make(self, user, **payload):
        return self.client.post(RUNS, payload, content_type="application/json",
                                **_bearer(user))

    def _run_id(self, user, **payload) -> int:
        resp = self._make(user, **payload)
        self.assertEqual(resp.status_code, 200, resp.content[:400])
        body = resp.json()
        self.assertEqual(body["status"], "succeeded", body)
        return body["run_id"]


# ═══════════════════════════════════════════════════════════════════════════
# ① 서식 3 — 실행 기록 한 행씩
# ═══════════════════════════════════════════════════════════════════════════
class ReportRunCreateTest(ReportFixture):
    def test_three_kinds_each_leave_one_run_row(self) -> None:
        event_id = self._event(self.stream_a)
        ids = [
            self._run_id(self.manager_a, kind="incident", event_id=event_id),
            self._run_id(self.manager_a, kind="monthly"),
            self._run_id(self.manager_a, kind="upper"),
        ]
        self.assertEqual(len(set(ids)), 3)

        listing = self.client.get(RUNS, **_bearer(self.manager_a))
        self.assertEqual(listing.status_code, 200, listing.content[:300])
        body = listing.json()
        kinds = {r["kind"] for r in body["runs"]}
        self.assertEqual(kinds, {"incident", "monthly", "upper"})
        #: 사람이 눌렀다 — 자동이라고 적으면 PRD §7.4 의 수가 거짓이 된다.
        self.assertEqual({r["trigger"] for r in body["runs"]}, {"manual"})
        self.assertEqual({r["trigger_label"] for r in body["runs"]}, {"사람"})

    def test_monthly_total_equals_stats_summary_total(self) -> None:
        """집계는 `stats.py` 공개 함수 그대로 — 종이가 다시 세지 않는다."""
        from apps.dsm import monthly_report, stats

        for _ in range(3):
            self._event(self.stream_a)
        self._event(self.stream_b)          # 남의 테넌트 — 섞이면 격리 실패다

        since, until = monthly_report.monthly_window()
        expected = stats.stats_summary(scope=self.scope_a, since=since, until=until)
        cache.clear()
        run_id = self._run_id(self.manager_a, kind="monthly")
        from apps.dsm import docx_export

        run = monthly_report.run_model()._base_manager.get(pk=run_id)
        text = docx_export.text_of(
            monthly_report.render_run(scope=self.scope_a, run=run, fmt="docx"))
        self.assertIn(f"{expected['total']}건", text)
        self.assertGreaterEqual(expected["total"], 3)

    def test_other_tenant_event_is_404_and_leaves_no_row(self) -> None:
        from apps.dsm import monthly_report

        foreign = self._event(self.stream_b)
        before = monthly_report.live_runs(group=self.group_a).count()
        resp = self._make(self.manager_a, kind="incident", event_id=foreign)
        self.assertEqual(resp.status_code, 404, resp.content[:300])
        self.assertEqual(monthly_report.live_runs(group=self.group_a).count(), before)

    def test_unknown_kind_is_400(self) -> None:
        resp = self._make(self.manager_a, kind="invoice")
        self.assertEqual(resp.status_code, 400, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# ② · ③ 파일 2 — DOCX 정본 · PDF 병행 · 택배 필드 0
# ═══════════════════════════════════════════════════════════════════════════
class ReportFileTest(ReportFixture):
    def test_docx_is_zip_over_1kb_and_has_zero_delivery_fields(self) -> None:
        from apps.dsm import docx_export

        event_id = self._event(self.stream_a)
        cases = {
            "incident": self._run_id(self.manager_a, kind="incident", event_id=event_id),
            "monthly": self._run_id(self.manager_a, kind="monthly"),
            "upper": self._run_id(self.manager_a, kind="upper"),
        }
        for kind, run_id in cases.items():
            with self.subTest(kind=kind):
                resp = self.client.get(_docx(run_id), **_bearer(self.manager_a))
                self.assertEqual(resp.status_code, 200, resp.content[:300])
                data = resp.getvalue()
                self.assertTrue(data.startswith(b"PK"), f"{kind}: DOCX(zip) 가 아니다")
                self.assertGreater(len(data), 1024, f"{kind}: 1KB 이하 — 빈 문서다")
                self.assertIn("no-store", resp["Cache-Control"])
                self.assertIn("wordprocessingml", resp["Content-Type"])

                text = docx_export.text_of(data)
                low = text.lower()
                for word in FORBIDDEN_WORDS:
                    self.assertNotIn(word.lower(), low,
                                     f"{kind}: 종이에 「{word}」 가 들어갔다 — 택배 필드 0")
                #: 원본은 나가지 않는다(계약 11조) — 스냅샷 경로가 종이에 찍히면 반출이다.
                self.assertNotIn("minio://", low)

    def test_pdf_is_pdf_over_1kb(self) -> None:
        run_id = self._run_id(self.manager_a, kind="monthly")
        resp = self.client.get(_pdf(run_id), **_bearer(self.manager_a))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        data = resp.getvalue()
        self.assertTrue(data.startswith(b"%PDF"), "PDF 가 아니다")
        self.assertGreater(len(data), 1024)
        self.assertEqual(resp["Content-Type"], "application/pdf")

    def test_form_titles_are_the_words_the_screen_presses(self) -> None:
        """서식 제목 = 화면 카드의 글자. 갈리면 사람이 「그 보고서」라고 부를 수 없다."""
        from apps.dsm import incident_report as form
        from apps.dsm import monthly_report

        self.assertEqual(form.MONTHLY_TITLE, monthly_report.KIND_LABEL["monthly"])
        self.assertEqual(form.DOCUMENT_TITLE, monthly_report.KIND_LABEL["incident"])


# ═══════════════════════════════════════════════════════════════════════════
# ④ · ⑤ 격리 · 자격
# ═══════════════════════════════════════════════════════════════════════════
class ReportAccessTest(ReportFixture):
    def test_anonymous_is_401(self) -> None:
        self.assertEqual(self.client.get(RUNS).status_code, 401)

    def test_operator_is_403(self) -> None:
        resp = self.client.get(RUNS, **_bearer(self.operator_a))
        self.assertEqual(resp.status_code, 403, resp.content[:300])

    def test_read_only_official_downloads_but_cannot_create(self) -> None:
        """U4(읽기 전용 담당관)은 **내려받는다**. 만들기는 못 한다 — 그것이 그 계정의 뜻이다.

        ★ [실측 2026-09-18] 읽기 전용 계정의 POST 는 플랫폼 문지기(`role_gate` ·
          `read_only_role`)가 403 으로 끊는다. 우리 라우트의 판정보다 **앞에 선 문**이고,
          그것이 옳다: 「읽기 전용」이 쓰기를 하면 그 낱말이 거짓이 된다.
          그래서 U4 의 자동본은 **배치가 만든다**(`trigger=auto`) — 화면의 「만들기」는
          팀장(U2)·운영자의 자리이고, U4 에게는 그 실패가 상태 칸에 그대로 적힌다.
        """
        denied = self._make(self.viewer_a, kind="monthly")
        self.assertEqual(denied.status_code, 403, denied.content[:300])

        run_id = self._run_id(self.manager_a, kind="monthly")
        resp = self.client.get(_docx(run_id), **_bearer(self.viewer_a))
        self.assertEqual(resp.status_code, 200, resp.content[:300])

    def test_other_tenant_run_is_404(self) -> None:
        run_id = self._run_id(self.manager_a, kind="monthly")
        for url in (_docx(run_id), _pdf(run_id)):
            with self.subTest(url=url):
                resp = self.client.get(url, **_bearer(self.manager_b))
                self.assertEqual(resp.status_code, 404, resp.content[:300])
        listing = self.client.get(RUNS, **_bearer(self.manager_b)).json()
        self.assertEqual(listing["runs"], [])


# ═══════════════════════════════════════════════════════════════════════════
# ⑦ 감사 — 해시 체인 두 칸 · CSV
# ═══════════════════════════════════════════════════════════════════════════
class AuditChainTest(ReportFixture):
    def _make_audit_rows(self) -> int:
        event_id = self._event(self.stream_a)
        resp = self.client.post(f"/api/dsm/events/{event_id}/upper-report", {},
                                content_type="application/json",
                                **_bearer(self.manager_a))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        return event_id

    def test_audit_items_carry_chain_columns_and_are_linked(self) -> None:
        self._make_audit_rows()
        body = self.client.get(AUDIT, **_bearer(self.manager_a)).json()
        self.assertGreaterEqual(len(body["items"]), 1)
        first = body["items"][0]
        for key in ("prev_hash", "hash", "chain"):
            self.assertIn(key, first)
        self.assertEqual(len(first["hash"]), 64, "저장된 해시가 sha256 이 아니다")
        self.assertEqual(first["chain"], "linked", first)
        self.assertIn("chain_states", body)
        self.assertEqual(body["chain_states"]["broken"], 0)

    def test_audit_csv_has_bom_header_and_no_store(self) -> None:
        self._make_audit_rows()
        resp = self.client.get(AUDIT_CSV, **_bearer(self.manager_a))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        text = resp.getvalue().decode("utf-8")
        self.assertTrue(text.startswith("﻿"), "엑셀이 한글을 깨뜨린다 — BOM 이 없다")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        self.assertTrue(lines[0].endswith("chain"), lines[0])
        self.assertIn("prev_hash", lines[0])
        self.assertGreaterEqual(len(lines), 3)      # 머리 + 행 ≥ 1 + 합계
        self.assertIn("no-store", resp["Cache-Control"])

    def test_operator_cannot_export_audit(self) -> None:
        resp = self.client.get(AUDIT_CSV, **_bearer(self.operator_a))
        self.assertEqual(resp.status_code, 403, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# ⑧ 배치 — 자동본 한 행
# ═══════════════════════════════════════════════════════════════════════════
class MonthlyBatchTest(ReportFixture):
    def test_run_monthly_makes_one_auto_row_for_the_group(self) -> None:
        from apps.dsm import monthly_report

        self._event(self.stream_a)
        run = monthly_report.run_monthly(group=self.group_a)
        self.assertEqual(run.kind, "monthly")
        self.assertEqual(run.trigger, "auto", "배치가 낸 행은 자동이다")
        self.assertEqual(run.status, "succeeded", run.failure_reason)
        self.assertEqual(run.group_id, self.group_a.pk)
        self.assertIsNotNone(run.period_start)
        self.assertIsNotNone(run.period_end)
        self.assertLessEqual(run.period_start, run.period_end)

    def test_window_is_this_month_and_does_not_reach_into_the_future(self) -> None:
        from apps.dsm import monthly_report

        since, until = monthly_report.monthly_window()
        now = timezone.localtime()
        self.assertEqual((since.day, since.hour, since.minute), (1, 0, 0))
        self.assertLessEqual(until, now + timedelta(seconds=5))

    def test_group_without_any_account_gets_a_failed_row_with_a_reason(self) -> None:
        """조용히 건너뛰지 않는다 — 건너뛴 조직은 다음 달에도 조용하다."""
        from django.apps import apps

        from apps.dsm import monthly_report

        UserGroup = apps.get_model("user", "UserGroup")
        empty = UserGroup.objects.create(name="dsm-tenant-empty")
        run = monthly_report.run_monthly(group=empty)
        self.assertEqual(run.status, "failed")
        self.assertTrue(run.failure_reason, "사유 없는 실패는 「없다」와 「못 했다」를 못 가른다")


class FormPurityTest(TestCase):
    """서식 함수는 **DB 를 만지지 않는다** — 그래서 이 시험은 픽스처 없이 글자만 센다."""

    def test_monthly_and_upper_forms_have_zero_delivery_words(self) -> None:
        from apps.dsm import incident_report as form

        now = timezone.now()
        html = form.build_monthly_html(
            tenant="안양시 재난안전과", issued_by="담당자", since=now, until=now,
            summary={"total": 0, "by_severity": {}, "by_response_state": {}},
            axes={"axes": {}}, note="", trigger="auto")
        html += form.build_upper_html(
            tenant="안양시 재난안전과", issued_by="담당자", since=now, until=now, rows=[])
        #: **사람이 보는 글자**만 센다. 서식의 CSS 에는 `border` 가 있고 그 안에 `order`
        #: 가 들어 있다 — 스타일 글자를 세면 이 시험은 영원히 빨강이고, 상시 빨강은
        #: 아무도 안 본다(D-301 의 형제). 종이에 실제로 인쇄되는 글자는 본문뿐이다.
        low = _visible_text(html).lower()
        for word in FORBIDDEN_WORDS:
            self.assertNotIn(word.lower(), low, f"서식에 「{word}」 가 있다")
        #: 「특이사항」 칸은 비어도 남는다 — 사라지면 「없었다」와 「안 적었다」가 섞인다.
        self.assertIn("특이사항", html)
        self.assertIn("기재된 특이사항이 없습니다.", html)
