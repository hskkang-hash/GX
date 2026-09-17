# -*- coding: utf-8 -*-
"""U24 · 턴 T (P-164) — 통계 축 5 · CSV · 상급 보고 체크 · 감사 읽기.

이 파일이 잰다
--------------
  ① `/stats/axes` — **합계 = 목록 수**(같은 창의 `GET /events` `total`) · 다섯 축 각각의
    건수 합 = `total`(어느 행도 두 번 세어지거나 빠지지 않는다) · 축 이름 다섯이 응답에 있다
  ② `/stats/export.csv` — UTF-8 BOM · 머리 1행 · 행 수 = 축 행 합 + 머리 + 합계 ·
    마지막 합계 행의 수 = `total` · `Cache-Control: no-store`
  ③ 상급 보고 — 체크 → `flags` 에 보임 → 해제 → 안 보임 · 감사에 **성공 2 + 실패 1** ·
    남의 사건은 404(존재 여부가 새지 않는다) · 남의 테넌트 체크는 `flags` 에 안 보인다
  ④ `/audit` — 익명 401 · 관제요원(fire_user) 403 · 팀장(fire_admin) 200 ·
    읽기 전용(view_only) 200 · 운영자(admin) 200 · **격리**(B 의 행위가 A 에게 안 보인다) ·
    필터 3(기간 · 행위자 · 행위 종류) · 쪽

무엇을 다시 묻지 않나
---------------------
사건 목록 자체(K1) · 감사 체인(LAW-08) · 역할 판정식(`tenant_roles` · `role_gate`)은
각자의 시험이 잰다. 여기서는 **라우트가 그것을 잃지 않고 옮기는가**만 묻는다.

캐시: 시험마다 `cache.clear()` — `test_u24_stats.py` 와 같은 이유.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

STATS_AXES = "/api/dsm/stats/axes"
STATS_CSV = "/api/dsm/stats/export.csv"
AUDIT = "/api/dsm/audit"
FLAGS = "/api/dsm/events/upper-report/flags"

REAL_SAMPLE = (
    "apps.dsm.api_u24.DsmU24API / apps.dsm.stats.stats_axes · apps.dsm.audit.read_page · "
    "stream_monitors.DsmUpperReportFlag — 저장소의 실제 라우트·모델. 합성 더미가 아니다"
)

AXES_EXPECTED = ("camera", "event_type", "severity", "verdict", "hour")


def _upper(event_id: int) -> str:
    return f"/api/dsm/events/{event_id}/upper-report"


class TurnTFixture(DsmFixture):
    """`DsmFixture` 에 역할 넷(팀장 · 요원 · 읽기 전용 · 운영자)을 더한다 — 전부 테넌트 A."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        cls.manager_a = cls._user(
            "u24t_manager_a", cls.group_a, cls._own(cls._role("fire_admin"), cls.group_a))
        cls.operator_a = cls._user(
            "u24t_operator_a", cls.group_a, cls._own(cls._role("fire_user"), cls.group_a))
        cls.viewer_a = cls._user(
            "u24t_viewer_a", cls.group_a,
            cls._own(cls._role("view_only_-_u24t"), cls.group_a))
        cls.sysop_a = cls._user(
            "u24t_sysop_a", cls.group_a, cls._own(cls._role("admin"), cls.group_a))
        cls.manager_b = cls._user(
            "u24t_manager_b", cls.group_b, cls._own(cls._role("fire_admin_b"), cls.group_b))
        # fire_admin_b 는 K3 표에 없는 코드다 — B 의 팀장은 표에 있는 코드로 하나 더 둔다.
        cls.manager_b.roles.add(cls._own(cls._role("surveillance_order"), cls.group_b))

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self._clear_thread_request()

    def tearDown(self) -> None:
        #: HTTP 를 때린 시험이 스레드에 요청을 남기면 뒤 시험의 `objects` 가 빈다
        #: (메모리 「스레드에 남은 요청이 거짓 초록을 만든다」) — 시험 **사이**마다 비운다.
        self._clear_thread_request()
        super().tearDown()

    @staticmethod
    def _clear_thread_request() -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None


# ═══════════════════════════════════════════════════════════════════════════
# ① 축 5 — 합계 = 목록 수 · 축마다 합 = total
# ═══════════════════════════════════════════════════════════════════════════
class StatsAxesTest(TurnTFixture):
    def test_total_equals_events_list_and_every_axis_sums_to_total(self) -> None:
        from kernels.k6_feedback import record_feedback

        since = timezone.now() - timedelta(days=1)
        ids = [self._event(self.stream_a, severity=s, event_type=t)
               for s, t in (("critical", "fire"), ("critical", "fire"),
                            ("warning", "smoke"), ("info", "smoke"))]
        record_feedback(ids[0], verdict="confirmed", reason="t", scope=self.scope_a)
        record_feedback(ids[1], verdict="rejected", reason="t", scope=self.scope_a)
        # 테넌트 B 의 사건은 섞이면 안 된다.
        self._event(self.stream_b)

        params = {"since": since.isoformat()}
        events = self.client.get("/api/dsm/events", {**params, "limit": 2000},
                                 **_bearer(self.user_a))
        self.assertEqual(200, events.status_code, events.content)
        axes = self.client.get(STATS_AXES, params, **_bearer(self.user_a))
        self.assertEqual(200, axes.status_code, axes.content)
        body = axes.json()

        self.assertEqual(4, body["total"], "테넌트 B 의 사건이 섞였거나 행이 빠졌다")
        self.assertEqual(events.json()["total"], body["total"],
                         "합계 = 목록 수(AC-5) 위반")
        self.assertEqual(list(AXES_EXPECTED), body["axis_order"])
        for axis in AXES_EXPECTED:
            with self.subTest(axis=axis):
                self.assertIn(axis, body["axis_titles"])
                rows = body["axes"][axis]
                self.assertEqual(
                    body["total"], sum(r["count"] for r in rows),
                    f"축 {axis} 의 합이 total 과 다르다 — 어느 행이 두 번 세어졌거나 빠졌다")
        by_key = {r["key"]: r["count"] for r in body["axes"]["verdict"]}
        self.assertEqual({"confirmed": 1, "rejected": 1, "unreviewed": 2}, by_key,
                         "미판정이 판정값으로 뭉개졌다")
        self.assertEqual({"critical": 2, "warning": 1, "info": 1},
                         {r["key"]: r["count"] for r in body["axes"]["severity"]})

    def test_anonymous_gets_401(self) -> None:
        for path in (STATS_AXES, STATS_CSV):
            with self.subTest(path=path):
                self.assertEqual(401, self.client.get(path).status_code)


# ═══════════════════════════════════════════════════════════════════════════
# ② CSV — BOM · 머리 · 행 수 · 합계 행
# ═══════════════════════════════════════════════════════════════════════════
class StatsCsvTest(TurnTFixture):
    def test_csv_header_rows_and_total_row(self) -> None:
        import csv
        import io

        since = timezone.now() - timedelta(days=1)
        for _ in range(3):
            self._event(self.stream_a)
        params = {"since": since.isoformat()}

        axes = self.client.get(STATS_AXES, params, **_bearer(self.user_a)).json()
        resp = self.client.get(STATS_CSV, params, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertTrue(resp["Content-Type"].startswith("text/csv"))
        self.assertEqual("no-store", resp["Cache-Control"])
        self.assertIn("attachment", resp["Content-Disposition"])

        raw = resp.content
        import codecs

        self.assertTrue(raw.startswith(codecs.BOM_UTF8), "UTF-8 BOM 이 없다")
        text = raw.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(["axis", "axis_title", "key", "label", "count"], rows[0])
        axis_rows = sum(len(axes["axes"][a]) for a in axes["axis_order"])
        self.assertEqual(axis_rows + 2, len(rows),
                         "행 수 = 축 행 합 + 머리 1 + 합계 1 이어야 한다")
        self.assertEqual("total", rows[-1][0])
        self.assertEqual(str(axes["total"]), rows[-1][-1], "합계 행의 수가 total 과 다르다")
        self.assertEqual(3, axes["total"])
        self.assertIn("카메라", text, "한글 축 제목이 파일에 없다")


# ═══════════════════════════════════════════════════════════════════════════
# ③ 상급 보고 체크 — 토글 · 감사 · 격리
# ═══════════════════════════════════════════════════════════════════════════
class UpperReportTest(TurnTFixture):
    def test_set_then_clear_leaves_audit_and_is_tenant_isolated(self) -> None:
        from apps.dsm import audit

        eid = self._event(self.stream_a)
        eid_b = self._event(self.stream_b)

        before = len(audit_rows(audit.EVENT_LOGGER_NAME))

        r = self.client.post(_upper(eid), **_bearer(self.manager_a))
        self.assertEqual(200, r.status_code, r.content)
        self.assertTrue(r.json()["flagged"])
        self.assertTrue(r.json()["created"])
        self.assertIsNotNone(r.json()["audit_id"])

        flags = self.client.get(FLAGS, {"event_ids": f"{eid},{eid_b}"},
                                **_bearer(self.manager_a)).json()
        self.assertIn(str(eid), flags["flags"])
        self.assertNotIn(str(eid_b), flags["flags"])

        # 남의 사건 — 404 · 존재 여부가 새지 않는다 · 실패도 감사에 남는다
        r_b = self.client.post(_upper(eid_b), **_bearer(self.manager_a))
        self.assertEqual(404, r_b.status_code, r_b.content)

        # B 가 자기 사건에 체크해도 A 의 flags 엔 안 보인다
        self.assertEqual(200, self.client.post(_upper(eid_b), **_bearer(self.manager_b)).status_code)
        flags_a = self.client.get(FLAGS, **_bearer(self.manager_a)).json()
        self.assertNotIn(str(eid_b), flags_a["flags"], "테넌트 B 의 체크가 A 에 보인다")

        r2 = self.client.delete(_upper(eid), **_bearer(self.manager_a))
        self.assertEqual(200, r2.status_code, r2.content)
        self.assertFalse(r2.json()["flagged"])
        flags2 = self.client.get(FLAGS, {"event_ids": str(eid)}, **_bearer(self.manager_a)).json()
        self.assertEqual({}, flags2["flags"])

        # 풀 것이 없으면 404
        self.assertEqual(404, self.client.delete(_upper(eid), **_bearer(self.manager_a)).status_code)

        rows = audit_rows(audit.EVENT_LOGGER_NAME)[before:]
        mine = [r for r in rows if r.user_id == self.manager_a.pk]
        outcomes = sorted(r.level_name for r in mine)
        # set(성공) · set 남의 것(실패) · clear(성공) · clear 없는 것(실패)
        self.assertEqual(["INFO", "INFO", "WARNING", "WARNING"], outcomes,
                         "성공 2 · 실패 2 가 감사에 남아야 한다")
        self.assertTrue(all(r.logger_name == audit.EVENT_LOGGER_NAME for r in mine))
        self.assertFalse(any(r.logger_name == audit.LOGGER_NAME for r in mine),
                         "사건 행위가 F-12 설정 감사 전건에 섞였다")

    def test_read_only_role_cannot_check(self) -> None:
        eid = self._event(self.stream_a)
        r = self.client.post(_upper(eid), **_bearer(self.viewer_a))
        self.assertEqual(403, r.status_code, r.content)


def audit_rows(logger_name: str):
    from django.apps import apps

    Model = apps.get_model("logger", "AuditLogs")
    return list(Model._base_manager.filter(logger_name=logger_name).order_by("id"))


# ═══════════════════════════════════════════════════════════════════════════
# ④ 감사 읽기 — 권한 · 격리 · 필터 3 · 쪽
# ═══════════════════════════════════════════════════════════════════════════
class AuditReadTest(TurnTFixture):
    def _seed_actions(self):
        """A 팀장이 2건 · A 요원 0건(403 이라 감사 없음) · B 팀장이 1건을 남긴다."""
        e1 = self._event(self.stream_a)
        e2 = self._event(self.stream_a)
        eb = self._event(self.stream_b)
        self.assertEqual(200, self.client.post(_upper(e1), **_bearer(self.manager_a)).status_code)
        self.assertEqual(200, self.client.post(_upper(e2), **_bearer(self.manager_a)).status_code)
        self.assertEqual(200, self.client.delete(_upper(e2), **_bearer(self.manager_a)).status_code)
        self.assertEqual(200, self.client.post(_upper(eb), **_bearer(self.manager_b)).status_code)
        return e1, e2, eb

    def test_anonymous_401_and_role_gate(self) -> None:
        self.assertEqual(401, self.client.get(AUDIT).status_code)
        cases = (
            (self.operator_a, 403, "관제요원(fire_user)"),
            (self.manager_a, 200, "팀장(fire_admin)"),
            (self.viewer_a, 200, "읽기 전용(view_only)"),
            (self.sysop_a, 200, "운영자(admin)"),
        )
        for user, expected, label in cases:
            with self.subTest(role=label):
                r = self.client.get(AUDIT, **_bearer(user))
                self.assertEqual(expected, r.status_code, r.content)

    def test_tenant_isolation_and_three_filters_and_paging(self) -> None:
        e1, e2, eb = self._seed_actions()

        body = self.client.get(AUDIT, **_bearer(self.manager_a)).json()
        actors = {i["actor_id"] for i in body["items"]}
        self.assertIn(self.manager_a.pk, actors)
        self.assertNotIn(self.manager_b.pk, actors, "테넌트 B 의 감사 행이 A 에게 보인다")
        self.assertEqual(3, body["total"], body)
        self.assertFalse(any(f":{eb}" in i["action"] for i in body["items"]))

        # 행위자 필터 — 남의 사번을 넣어도 격리가 먼저다
        r = self.client.get(AUDIT, {"actor_id": self.manager_b.pk}, **_bearer(self.manager_a)).json()
        self.assertEqual(0, r["total"])
        r = self.client.get(AUDIT, {"actor_id": self.manager_a.pk}, **_bearer(self.manager_a)).json()
        self.assertEqual(3, r["total"])

        # 행위 종류 필터 — 앞머리 일치
        r = self.client.get(AUDIT, {"action": "upper_report:clear"}, **_bearer(self.manager_a)).json()
        self.assertEqual(1, r["total"])
        self.assertEqual(f"upper_report:clear:{e2}", r["items"][0]["action"])
        r = self.client.get(AUDIT, {"action": "upper_report:set"}, **_bearer(self.manager_a)).json()
        self.assertEqual(2, r["total"])

        # 기간 필터 — 미래부터는 0 · 어제부터는 전부
        future = (timezone.now() + timedelta(hours=1)).isoformat()
        past = (timezone.now() - timedelta(days=1)).isoformat()
        self.assertEqual(0, self.client.get(AUDIT, {"since": future},
                                            **_bearer(self.manager_a)).json()["total"])
        self.assertEqual(3, self.client.get(AUDIT, {"since": past},
                                            **_bearer(self.manager_a)).json()["total"])

        # 쪽 — page_size=2 면 2쪽 · 둘째 쪽에 1건
        p1 = self.client.get(AUDIT, {"page_size": 2, "page": 1}, **_bearer(self.manager_a)).json()
        p2 = self.client.get(AUDIT, {"page_size": 2, "page": 2}, **_bearer(self.manager_a)).json()
        self.assertEqual(2, p1["pages"])
        self.assertEqual(2, len(p1["items"]))
        self.assertEqual(1, len(p2["items"]))
        self.assertEqual(400, self.client.get(AUDIT, {"page_size": 999},
                                              **_bearer(self.manager_a)).status_code)
        del e1
