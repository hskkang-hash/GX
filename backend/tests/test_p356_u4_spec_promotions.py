# -*- coding: utf-8 -*-
"""P-356/P-358 · WO-GX-20260925-15 §5 — **DSM-U4-06·U5-02 승격 시험** · 차선 N1 · 턴 AL.

캐시 처리: 우회/비움/해당 없음 — Django 테스트 클라이언트가 매 시험 새 프로세스로
`cache.clear()` 를 부른다(`test_p356_u2_spec_promotions.py` 와 같은 이유 —
`common/idempotency.py` 가 Redis 캐시에 성공 응답을 잠깐 기억하는데, 창을 안 비우면
같은 시험 파일 안에서 두 번째 요청이 **새 자원 대신 옛 응답**을 받는다).

이 파일이 잰다
--------------
  DSM-U4-06 `POST|GET /api/dsm/alert-level` — 4단계(관심·주의·경계·심각) 밖 값은
    400 · 접수마다 감사 한 줄 · 가장 최근 접수가 목록 첫 행(지금 단계) · 남의
    테넌트 접수는 안 보인다.
  DSM-U5-02 `GET /api/dsm/access-log[/export.csv]` — 시스템관리자·테넌트관리자만
    200(팀장은 403) · 접속 로그 다섯 채널(`db`·`jwt`·`application`·`security`·
    `user_update`)이 **실제로 보인다**(일반 감사 화면(`/audit`)에는 여전히 안 보인다
    — 대표 결정 ⑤는 안 바뀐다) · 남의 테넌트 접속 기록은 안 보인다 · **조회 자체가
    감사 한 줄**을 남긴다(GX-LAW-09 §5-2).

무엇을 다시 묻지 않나
---------------------
일반 감사 화면의 울타리(`READABLE_LOGGER_NAMES` 가 접속 로그를 빼는가)는
`test_u56_audit_channels.py` 가 이미 잰다 — 여기서는 **좁힌 새 문이 그 채널을
여는가**만 묻는다. 두 시험이 같은 사실을 다시 재면 한쪽이 바뀔 때 다른 쪽이
못 따라간다(D-212).
"""
from __future__ import annotations

import json
from pathlib import Path

from django.apps import apps
from django.core.cache import cache
from django.utils import timezone

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

ALERT = "/api/dsm/alert-level"
ACCESS_LOG = "/api/dsm/access-log"
ACCESS_LOG_CSV = "/api/dsm/access-log/export.csv"
AUDIT = "/api/dsm/audit"


def _repo_root() -> Path:
    """`parents[2]` 로 기어오른다 — `test_p356_u2_spec_promotions.py::_repo_root` 와
    같은 계산이다(같은 디렉터리에 쓰는 두 시험 파일이 다른 길을 걷지 않는다 —
    그 파일 머리말의 실측 경고 그대로 옮긴다)."""
    return Path(__file__).resolve().parents[2]


#: P-356 ② — 증거 파일이 사는 자리. **손으로 만들지 않는다** — 아래
#: `EvidenceExportTest` 가 실제로 때린 응답으로 채운다.
EVIDENCE_DIR = _repo_root() / "docs" / "agent" / "evidence" / "SPEC"


class U4Fixture(DsmFixture):
    """역할 — 팀장(A·B) · 시스템관리자(A·B, `code="admin"` 한 역할을 공유 — 역할
    코드는 unique 라 그 역할을 두 계정에 붙인다. 어느 테넌트인지는 계정의
    `UserGroup` 링크가 가른다 — `is_tenant_admin` 은 역할의 소유 group 이 아니라
    **요청자 자신의 소속**을 본다, `common/tenant_roles.py::is_tenant_admin` 그대로)."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        Role = apps.get_model("role", "Role")

        cls.manager_a = cls._user(
            "u4al_manager_a", cls.group_a,
            cls._own(cls._role("dsm_u4al_mgr_a"), cls.group_a))
        cls.manager_b = cls._user(
            "u4al_manager_b", cls.group_b,
            cls._own(cls._role("dsm_u4al_mgr_b"), cls.group_b))

        admin_role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
        cls.sysop_a = cls._user("u4al_sysop_a", cls.group_a, admin_role)
        cls.sysop_b = cls._user("u4al_sysop_b", cls.group_b, admin_role)

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self._clear_thread_request()

    def tearDown(self) -> None:
        #: HTTP 를 때린 시험 뒤 스레드에 요청이 남으면 다음 시험의 `objects` 가 빈다
        #: (메모리 「스레드에 남은 요청이 거짓 초록을 만든다」).
        self._clear_thread_request()
        super().tearDown()

    @staticmethod
    def _clear_thread_request() -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

    @staticmethod
    def _seed_access_log_row(*, channel: str, user_id: int, note: str, ip="10.0.0.9"):
        """접속 로그처럼 생긴 행 하나 — `test_u56_audit_channels.py::_row` 와 같은
        이유로 `audit_writer.write` 를 안 쓴다: 심고 싶은 것은 *dj-core 가 쌓은 것처럼
        생긴 행*이다. `AccessLogTest`·`EvidenceExportTest` 둘 다 쓰므로 기지에 둔다."""
        AuditLogs = apps.get_model("logger", "AuditLogs")
        return AuditLogs.objects.create(
            logger_name=channel, level_name="INFO", api_name="/probe",
            api_method="GET", note=note, msg=note, user_id=user_id,
            client_ip=ip)


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U4-06 위기경보·비상 단계 접수 입력
# ═══════════════════════════════════════════════════════════════════════════
class AlertLevelTest(U4Fixture):
    def test_out_of_range_level_is_400(self) -> None:
        resp = self.client.post(
            ALERT, {"level": "존재하지않는단계"},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_record_then_list_round_trips_latest_first(self) -> None:
        first = self.client.post(
            ALERT, {"level": "관심", "doc_no": "제1호"},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(200, first.status_code, first.content[:300])

        cache.clear()
        second = self.client.post(
            ALERT, {"level": "경계", "doc_no": "제2호", "staffing": 12},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(200, second.status_code, second.content[:300])
        self.assertIn("alert_id", second.json())

        cache.clear()
        listing = self.client.get(ALERT, **_bearer(self.manager_a))
        self.assertEqual(200, listing.status_code, listing.content[:300])
        rows = listing.json()
        self.assertEqual(2, len(rows))
        #: ★ 가장 최근 접수가 첫 행이다 — 「지금 단계」는 그 행이 말한다.
        self.assertIn("경계", rows[0]["text"])
        self.assertIn("제2호", rows[0]["text"])
        self.assertIn("12명", rows[0]["text"])
        self.assertIn("관심", rows[1]["text"])

    def test_other_tenant_alert_is_not_visible(self) -> None:
        self.client.post(
            ALERT, {"level": "심각"}, content_type="application/json",
            **_bearer(self.manager_b))

        cache.clear()
        mine = self.client.get(ALERT, **_bearer(self.manager_a))
        self.assertEqual(200, mine.status_code)
        self.assertEqual([], mine.json())


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U5-02 접속기록 전용 조회·CSV
# ═══════════════════════════════════════════════════════════════════════════
class AccessLogTest(U4Fixture):
    def test_manager_cannot_see_the_access_log(self) -> None:
        resp = self.client.get(ACCESS_LOG, **_bearer(self.manager_a))
        self.assertEqual(403, resp.status_code, resp.content[:300])

    def test_manager_cannot_export_csv(self) -> None:
        resp = self.client.get(ACCESS_LOG_CSV, **_bearer(self.manager_a))
        self.assertEqual(403, resp.status_code, resp.content[:300])

    def test_sysop_sees_access_log_channels_general_audit_still_hides_them(self) -> None:
        from apps.dsm import audit

        rows = [
            self._seed_access_log_row(
                channel=ch, user_id=self.manager_a.pk, note=f"u4al-probe {ch}")
            for ch in audit.ACCESS_LOG_LOGGER_NAMES
        ]

        cache.clear()
        opened = self.client.get(ACCESS_LOG, **_bearer(self.sysop_a))
        self.assertEqual(200, opened.status_code, opened.content[:300])
        got_ids = {item["log_id"] for item in opened.json()["items"]}
        self.assertTrue(
            {r.pk for r in rows} <= got_ids,
            f"심은 접속 로그 행이 전용 화면에 안 보입니다 — 심은 {[r.pk for r in rows]} "
            f"· 화면 {sorted(got_ids)}")
        self.assertEqual(list(audit.ACCESS_LOG_LOGGER_NAMES),
                         opened.json()["channels"])

        #: ★ 대표 결정 ⑤는 안 바뀐다 — 같은 행이 **일반 감사 화면**에는 여전히 안 뜬다.
        cache.clear()
        general = self.client.get(AUDIT, **_bearer(self.sysop_a))
        self.assertEqual(200, general.status_code, general.content[:300])
        general_ids = {item["audit_id"] for item in general.json()["items"]}
        leaked = {r.pk for r in rows} & general_ids
        self.assertEqual(
            set(), leaked,
            "접속 로그 행이 일반 감사 화면에도 떴습니다 — 대표 결정 ⑤가 깨졌습니다.")

    def test_other_tenant_access_log_is_not_visible(self) -> None:
        row = self._seed_access_log_row(
            channel="security", user_id=self.manager_a.pk, note="u4al-tenant-a-only")

        cache.clear()
        theirs = self.client.get(ACCESS_LOG, **_bearer(self.sysop_b))
        self.assertEqual(200, theirs.status_code, theirs.content[:300])
        self.assertNotIn(
            row.pk, {item["log_id"] for item in theirs.json()["items"]},
            "B 테넌트 시스템관리자에게 A 테넌트 접속 기록이 보입니다.")

    def test_reading_the_access_log_is_itself_audited(self) -> None:
        from apps.dsm import access_log_service

        cache.clear()
        before = len(access_log_service.audit_writer.read(
            logger_name=access_log_service.LOGGER_NAME, limit=200))

        resp = self.client.get(ACCESS_LOG, **_bearer(self.sysop_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])

        after = access_log_service.audit_writer.read(
            logger_name=access_log_service.LOGGER_NAME, limit=200)
        self.assertEqual(before + 1, len(after))
        self.assertTrue(any(e.action == "access_log:read" for e in after))

    def test_csv_export_is_a_real_csv_with_bom(self) -> None:
        self._seed_access_log_row(
            channel="db", user_id=self.manager_a.pk, note="u4al-csv-probe")

        cache.clear()
        resp = self.client.get(ACCESS_LOG_CSV, **_bearer(self.sysop_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertEqual("text/csv; charset=utf-8", resp["Content-Type"])
        self.assertEqual("no-store", resp["Cache-Control"])
        self.assertTrue(resp.content.startswith("﻿".encode("utf-8")))
        text = resp.content.decode("utf-8-sig")
        self.assertIn("log_id", text.splitlines()[0])


# ═══════════════════════════════════════════════════════════════════════════
# P-356 ② 증거 — `docs/agent/evidence/SPEC/<id>.json` 둘. **손으로 안 적는다** —
# 이 시험이 실제로 때린 응답을 그대로 담는다(Django TestCase · test client · test DB).
# `scripts/verify_spec_dsm.py` 가 이 파일들의 실재·모양을 잰다.
# ═══════════════════════════════════════════════════════════════════════════
class EvidenceExportTest(U4Fixture):
    def _dump(self, spec_id: str, *, test: str, method: str, path: str,
             req_body, status: int, resp_body, what: str) -> None:
        payload = {
            "id": spec_id,
            "measured_at": timezone.now().isoformat(),
            "measured_by": "django_test_client",
            "test": test,
            "request": {"method": method, "path": path, "body": req_body},
            "response": {"status": status, "body": resp_body},
            "what": what,
        }
        #: ★ `docs/agent/evidence/**` 쓰기는 시험 중 기본으로 막혀 있다
        #:   (`common.evidence_guard`). 이 자리는 **일부러 쓰는 자리**다.
        with allow_evidence_writes(
                "P-356 ② DSM 별표 절 실측 증거 — pytest 가 방금 두드린 HTTP "
                "왕복을 그대로 적는다(손으로 옮기지 않는다)"):
            EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            (EVIDENCE_DIR / f"{spec_id}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8")

    def test_dump_dsm_u4_06_evidence(self) -> None:
        body = {"level": "경계", "doc_no": "제3호", "staffing": 24}
        resp = self.client.post(ALERT, body, content_type="application/json",
                                **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self._dump(
            "DSM-U4-06",
            test="tests.test_p356_u4_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u4_06_evidence",
            method="POST", path=ALERT, req_body=body,
            status=resp.status_code, resp_body=resp.json(),
            what="위기경보 접수 1건을 실제로 남기고 응답을 그대로 옮겼다 — "
                "완결 조건(변경 감사)은 이 감사 줄 자체다. 손으로 지어낸 값 0.")

    def test_dump_dsm_u5_02_evidence(self) -> None:
        from apps.dsm import audit

        row = self._seed_access_log_row(
            channel="security", user_id=self.manager_a.pk, note="u4al-evidence-probe")

        cache.clear()
        resp = self.client.get(ACCESS_LOG, **_bearer(self.sysop_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertIn(row.pk, {item["log_id"] for item in body["items"]})
        self.assertEqual(list(audit.ACCESS_LOG_LOGGER_NAMES), body["channels"])

        self._dump(
            "DSM-U5-02",
            test="tests.test_p356_u4_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u5_02_evidence",
            method="GET", path=ACCESS_LOG, req_body={},
            status=resp.status_code, resp_body=body,
            what="시스템관리자로 접속기록 전용 문을 실제로 두드려 심어 둔 접속 로그 행"
                "(security 채널)이 실제로 보이는 것을 확인했다 — 일반 감사 화면에는 "
                "안 뜨는 채널이 이 좁은 문에서만 열린다(GX-LAW-09 §5-2).")
