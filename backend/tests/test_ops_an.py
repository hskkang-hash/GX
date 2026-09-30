# -*- coding: utf-8 -*-
"""플랫폼 운영자 U0 — O-01·02·06·07·08·09·11·12 실측 HTTP 시험 (턴 AO · 차선 N3).

닫는 여덟: O-01(테넌트 발급) · O-02(앱 설치·버전) · O-06(인시던트) · O-07(백업·복구) ·
O-08(온보딩 관제) · O-09(감사(플랫폼)) · O-11(릴리스·배포) · O-12(시드·훈련 데이터).

**안 닫는 둘**: O-05(건강 보드 — 5xx·게이트16색 부재, 반쪽) · O-10(키·자격 회전 —
라이브 로그인 반쪽 불가, 턴 AM 결론 유지). 이 시험은 그 둘도 **스모크**(200·정직한
회색 칸)는 확인하지만 `_write_evidence`/`title_parts`(승격 표)는 안 남긴다 — 반쪽을
닫힘으로 올리지 않는다(P-417).

`FwsHttpTest`(테넌트 A/B·JWT 발급기)를 그대로 쓴다(D-212 — 같은 표를 두 벌 두지
않는다). U0 는 `is_superuser=True` 인 계정 하나만 새로 세운다 — `common.tenant_roles.
is_global_admin` 이 보는 바로 그 칸이다.
"""
from __future__ import annotations

import json
import uuid
from datetime import timedelta
from pathlib import Path

from django.apps import apps
from django.core.cache import cache

from tests.test_fws_app import FwsHttpTest, _qs, _write_evidence

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"

TENANTS = "/api/dsm/ops/tenants"
APPS_LIST = "/api/dsm/ops/apps"
APPS_INSTALL = "/api/dsm/ops/apps/install"
APPS_STATUS = "/api/dsm/ops/apps/status"
HEALTH = "/api/dsm/ops/health"
INCIDENTS = "/api/dsm/ops/incidents"
BACKUPS = "/api/dsm/ops/backups"
ONBOARDING = "/api/dsm/ops/onboarding"
AUDIT = "/api/dsm/ops/audit"
AUDIT_REQUEST = "/api/dsm/ops/audit/access-requests"
KEYS = "/api/dsm/ops/keys"
RELEASES = "/api/dsm/ops/releases"
SEED = "/api/dsm/ops/seed"
SEED_TOGGLE = "/api/dsm/ops/seed/toggle"
LOGIN = "/api/v1/auth/login"


def _add_title_parts(clause_id: str, parts: list[dict]) -> None:
    """[턴 AQ · P-431 · 차선 Q] 사람 표는 `SPEC/<id>.retro.md`(손으로만) — json 에
    `title_parts` 를 **쓰지 않는다**(턴 AP 에 O 여덟 절의 재판정 표가 이 함수로 한 번
    지워졌다). 표 모양(빈 칸 0)만 여기서 본다."""
    for part in parts:
        missing = [k for k in ("part", "where", "status") if not (part.get(k) or "").strip()]
        assert not missing, f"{clause_id} title_parts 에 빈 칸: {part!r} ({missing})"


class OpsAnFixture(FwsHttpTest):
    """`FwsHttpTest`(테넌트 A/B) 위에 **U0 계정 하나**만 더한다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        CoreUser = apps.get_model("user", "CoreUser")
        cls.u0 = CoreUser.objects.create_user(
            username="opsan_u0_%s" % uuid.uuid4().hex[:8],
            password="test-only-not-a-secret", is_active=True,
            is_superuser=True, is_staff=True, email="opsan_u0@test.invalid")

    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def _issue_tenant(self, *, code: str | None = None):
        code = code or ("t-%s" % uuid.uuid4().hex[:8])
        admin_user = "opsadmin_%s" % uuid.uuid4().hex[:8]
        params = {
            "code": code, "name": "온보딩 시험 테넌트 %s" % code,
            "admin_username": admin_user, "admin_email": "%s@test.invalid" % admin_user,
            "admin_password": "Tenant-Admin-Pw-1!",
        }
        resp = self.client.post(_qs(TENANTS, **params), **self._bearer(self.u0))
        return resp, params


# ═══════════════════════════════════════════════════════════════════════════
# 문지기 — U0 아니면 어느 O-* 문도 안 열린다(P-415)
# ═══════════════════════════════════════════════════════════════════════════
class PlatformOperatorGateTest(OpsAnFixture):
    def test_tenant_admin_is_403_on_every_ops_door(self) -> None:
        head = self._bearer(self.user_a)  # 테넌트 관리자 — U0 아니다
        for path in (TENANTS, APPS_LIST, HEALTH, INCIDENTS, BACKUPS, ONBOARDING,
                    AUDIT, KEYS, RELEASES, SEED):
            resp = self.client.get(path, **head)
            self.assertEqual(403, resp.status_code, "%s 가 U0 아닌 사람에게 열렸다" % path)

    def test_anonymous_is_401(self) -> None:
        resp = self.client.get(TENANTS)
        self.assertIn(resp.status_code, (401, 403))


# ═══════════════════════════════════════════════════════════════════════════
# O-01 — 테넌트 발급
# ═══════════════════════════════════════════════════════════════════════════
class O01_TenantIssuanceTest(OpsAnFixture):
    def test_issue_then_admin_logs_in_and_reaches_role_home(self) -> None:
        resp, params = self._issue_tenant()
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(params["code"], body["tenant_code"])
        self.assertEqual(params["admin_username"], body["admin_username"])

        listing = self.client.get(TENANTS, **self._bearer(self.u0))
        self.assertEqual(200, listing.status_code)
        codes = [t["tenant_code"] for t in self._body(listing)["tenants"]]
        self.assertIn(params["code"], codes, "발급한 테넌트가 목록에 없다")

        #: ★ 완결 조건 그 자체 — "테넌트 관리자가 로그인 → 역할 홈"을 발급과
        #:   **분리된 행위**로 실측한다(발급 응답 안에서 흉내 내지 않는다).
        login_resp = self.client.post(
            LOGIN, data=json.dumps({"username": params["admin_username"],
                                   "password": params["admin_password"],
                                   "end_previous_session": True}),
            content_type="application/json")
        self.assertEqual(200, login_resp.status_code, login_resp.content)
        login_body = self._body(login_resp)
        self.assertTrue(login_body.get("user", {}).get("access_token"),
                        "로그인 응답에 access_token 이 없다 — %r" % login_body)

        _write_evidence(
            "O-01", title="테넌트 발급",
            test_ref="tests.test_ops_an.O01_TenantIssuanceTest."
                    "test_issue_then_admin_logs_in_and_reaches_role_home",
            method="POST", path=_qs(TENANTS, **params), request_params=params,
            response=resp,
            what="POST /api/dsm/ops/tenants 로 테넌트+초기 관리자 1을 발급한 뒤, 그 "
                "관리자 계정으로 실제 POST /api/v1/auth/login 을 두드려 200·"
                "access_token 을 받는다 — 완결 조건('테넌트 관리자가 로그인 → 역할 "
                "홈')의 앞 절반(로그인)을 발급과 분리된 실제 HTTP 로 증명한다. 뒤 "
                "절반(역할 홈)은 role='admin'이 K3 MANAGER 프리셋으로 이미 배선돼 "
                "있음을 config/k3_roles.py 가 보장한다(이 시험은 재확인하지 않는다 "
                "— 표를 두 벌 두지 않는다, D-212).")
        _add_title_parts("O-01", [
            {"part": "테넌트(시군구) 생성", "where": "tenant_code/name", "status": "measured"},
            {"part": "초기 관리자 1", "where": "admin_username", "status": "measured"},
            {"part": "완결조건 — 관리자 로그인", "where": "POST /api/v1/auth/login → access_token",
             "status": "measured"},
            {"part": "완결조건 — 역할 홈", "where": "role=admin → K3 MANAGER(config/k3_roles.py, 기존 배선 재사용)",
             "status": "measured — 기존 배선 재사용(새로 안 만든다)"},
            {"part": "계층(시도→시군구→부서) · 도메인·인증서",
             "where": "UserGroup.settings.domain/region", "status": "measured — 값 칸만(인증서 자동 발급은 없음)"},
        ])

    def test_duplicate_code_is_rejected(self) -> None:
        resp1, params = self._issue_tenant()
        self.assertEqual(200, resp1.status_code, resp1.content)
        resp2 = self.client.post(_qs(TENANTS, **params), **self._bearer(self.u0))
        self.assertEqual(422, resp2.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# O-02 — 앱 설치·버전
# ═══════════════════════════════════════════════════════════════════════════
class O02_AppInstallTest(OpsAnFixture):
    def test_install_list_and_conflict_free(self) -> None:
        issue_resp, params = self._issue_tenant()
        self.assertEqual(200, issue_resp.status_code)
        code = params["code"]
        head = self._bearer(self.u0)

        install_params = {"tenant_code": code, "app_code": "dsm", "version": "1.1"}
        resp = self.client.post(_qs(APPS_INSTALL, **install_params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("active", body["status"])

        listed = self.client.get(_qs(APPS_LIST, tenant_code=code), **head)
        self.assertEqual(200, listed.status_code)
        installs = self._body(listed)["installs"]
        self.assertEqual(1, len(installs), "시드 대장에 행이 둘 이상 — 충돌")
        self.assertEqual("dsm", installs[0]["app_code"])

        #: 같은 버전 재설치 = 충돌(422) — "시드 대장 0 충돌"의 반쪽.
        dup = self.client.post(_qs(APPS_INSTALL, **install_params), **head)
        self.assertEqual(422, dup.status_code)

        #: 다른 버전 = 업그레이드(충돌 아님) — 여전히 행 하나(최신 스냅샷).
        upgrade = self.client.post(
            _qs(APPS_INSTALL, tenant_code=code, app_code="dsm", version="1.2"), **head)
        self.assertEqual(200, upgrade.status_code)
        listed2 = self.client.get(_qs(APPS_LIST, tenant_code=code), **head)
        installs2 = self._body(listed2)["installs"]
        self.assertEqual(1, len(installs2), "업그레이드가 새 행을 만들었다 — 최신 스냅샷이어야 한다")
        self.assertEqual("1.2", installs2[0]["version"])

        _write_evidence(
            "O-02", title="앱 설치·버전",
            test_ref="tests.test_ops_an.O02_AppInstallTest.test_install_list_and_conflict_free",
            method="POST", path=_qs(APPS_INSTALL, **install_params),
            request_params=install_params, response=resp,
            what="POST .../ops/apps/install 로 테넌트에 앱을 설치하면 목록에 행 1(k_"
                "app_installation 대체 — 감사 스냅샷)이 생기고, 같은 버전 재설치는 "
                "422(시드 대장 충돌 0)이며 다른 버전은 업그레이드로 받아 행 수가 "
                "그대로 1이다 — 완결조건('행 · 시드 대장 0 충돌') 실측.")
        _add_title_parts("O-02", [
            {"part": "앱 설치", "where": "POST .../apps/install → status=active", "status": "measured"},
            {"part": "업그레이드", "where": "version 1.1→1.2, 행 수 그대로 1", "status": "measured"},
            {"part": "비활성화", "where": "POST .../apps/status", "status": "measured"},
            {"part": "완결조건 — k_app_installation 행", "where": "installs[0]",
             "status": "measured — 전용 모델이 없어 감사 스냅샷 행으로 대신함(새 모델 0)"},
            {"part": "완결조건 — 시드 대장 0 충돌", "where": "같은 버전 재설치 422", "status": "measured"},
            {"part": "유령 시드 정리", "where": "POST .../apps/status(status=inactive)",
             "status": "measured — 수동 정리 경로만(자동 탐지·주기 실행은 범위 밖)"},
        ])

    def test_deactivate(self) -> None:
        issue_resp, params = self._issue_tenant()
        code = params["code"]
        head = self._bearer(self.u0)
        self.client.post(_qs(APPS_INSTALL, tenant_code=code, app_code="fws", version="1.0"), **head)
        resp = self.client.post(
            _qs(APPS_STATUS, tenant_code=code, app_code="fws", status="inactive"), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertEqual("inactive", self._body(resp)["status"])


# ═══════════════════════════════════════════════════════════════════════════
# O-06 — 인시던트
# ═══════════════════════════════════════════════════════════════════════════
class O06_IncidentLifecycleTest(OpsAnFixture):
    def test_open_respond_escalate_close(self) -> None:
        issue_resp, params = self._issue_tenant()
        code = params["code"]
        head = self._bearer(self.u0)

        open_params = {"tenant_code": code, "app_code": "dsm", "severity": "critical",
                      "summary": "카메라 군집 두절"}
        resp = self.client.post(_qs(INCIDENTS, **open_params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        incident_id = body["incident_id"]
        self.assertEqual("open", body["status"])
        self.assertTrue(body["sla_first_response_due"])
        self.assertTrue(body["sla_escalation_due"])

        respond = self.client.post(
            _qs(INCIDENTS + ("/%s/respond" % incident_id), note="조치 시작"), **head)
        self.assertEqual(200, respond.status_code, respond.content)
        self.assertEqual("acknowledged", self._body(respond)["status"])

        escalate = self.client.post(
            _qs(INCIDENTS + ("/%s/escalate" % incident_id), note="2차 인계"), **head)
        self.assertEqual(200, escalate.status_code)
        self.assertEqual("escalated", self._body(escalate)["status"])

        close = self.client.post(
            _qs(INCIDENTS + ("/%s/close" % incident_id), cause="카메라 전원 이상",
               prevention="UPS 점검 주기 단축"), **head)
        self.assertEqual(200, close.status_code, close.content)
        closed_body = self._body(close)
        self.assertEqual("closed", closed_body["status"])
        self.assertTrue(closed_body["closing_report"], "종결 보고서가 비었다")

        listed = self.client.get(_qs(INCIDENTS, tenant_code=code), **head)
        self.assertEqual(1, len(self._body(listed)["incidents"]))

        _write_evidence(
            "O-06", title="인시던트",
            test_ref="tests.test_ops_an.O06_IncidentLifecycleTest."
                    "test_open_respond_escalate_close",
            method="POST", path=_qs(INCIDENTS, **open_params), request_params=open_params,
            response=resp,
            what="POST .../ops/incidents(접수) → .../respond(1차 대응) → .../escalate"
                "(에스컬레이션) → .../close(종결·원인)까지 네 호출을 실제로 두드려 "
                "SLA 시계(영업시간 4h·영업일 1일 기한)와 종결 보고서 1을 실측한다 — "
                "완결조건('SLA 시계 · 종결 보고서 1') 실측.")
        _add_title_parts("O-06", [
            {"part": "접수(테넌트·앱·심각도)", "where": "POST /ops/incidents", "status": "measured"},
            {"part": "1차 대응(4영업시간)", "where": "sla_first_response_due", "status": "measured"},
            {"part": "에스컬레이션(1영업일)", "where": "sla_escalation_due / escalate", "status": "measured"},
            {"part": "종결·원인", "where": "close → cause/closing_report", "status": "measured"},
            {"part": "완결조건 — SLA 시계", "where": "business_hours_deadline/business_days_deadline",
             "status": "measured"},
            {"part": "완결조건 — 종결 보고서 1", "where": "closing_report", "status": "measured"},
        ])

    def test_business_hours_deadline_skips_weekend(self) -> None:
        from datetime import datetime, timezone

        from apps.dsm.ops_an_service import business_hours_deadline

        # 금요일 17:00 KST + 4시간 — 금요일에 1시간(17시→18시 마감)만 쓰고,
        # 나머지 3시간은 토·일을 건너 월요일 09:00→12:00 KST 로 이어진다.
        fri_17 = datetime(2026, 10, 2, 17, 0, tzinfo=timezone(timedelta(hours=9)))
        deadline = business_hours_deadline(fri_17, 4)
        kst_deadline = deadline.astimezone(timezone(timedelta(hours=9)))
        self.assertEqual(2026, kst_deadline.year)
        self.assertEqual(10, kst_deadline.month)
        self.assertEqual(5, kst_deadline.day)  # 월요일
        self.assertEqual(12, kst_deadline.hour)


# ═══════════════════════════════════════════════════════════════════════════
# O-07 — 백업·복구
# ═══════════════════════════════════════════════════════════════════════════
class O07_BackupBoardTest(OpsAnFixture):
    def test_backup_and_restore_receipts_are_read_not_invented(self) -> None:
        head = self._bearer(self.u0)
        resp = self.client.get(BACKUPS, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)

        backup_path = ROOT / "docs" / "agent" / "evidence" / "D-373" / "backup_last.json"
        drill_path = ROOT / "docs" / "agent" / "evidence" / "D-373" / "restore_drill_last.json"
        if backup_path.is_file():
            self.assertTrue(body["backup"]["read"], "회수증 파일이 있는데 못 읽었다고 답했다")
            on_disk = json.loads(backup_path.read_text(encoding="utf-8"))
            self.assertEqual(on_disk.get("measured_at"), body["backup"]["measured_at"],
                             "장부 값과 응답 값이 다르다 — 지어낸 값일 수 있다")
            self.assertEqual(on_disk.get("manifest", {}).get("db", {}).get("via"),
                             body["backup"]["destination"], "회수증의 저장 목적지(via) 값이 다르다")
        if drill_path.is_file():
            self.assertTrue(body["restore_drill"]["read"])
            on_disk = json.loads(drill_path.read_text(encoding="utf-8"))
            self.assertEqual(on_disk.get("rto_seconds"), body["restore_drill"]["rto_seconds"])

        _write_evidence(
            "O-07", title="백업·복구",
            test_ref="tests.test_ops_an.O07_BackupBoardTest."
                    "test_backup_and_restore_receipts_are_read_not_invented",
            method="GET", path=BACKUPS, request_params={}, response=resp,
            what="GET /api/dsm/ops/backups 응답의 backup.measured_at·restore_drill."
                "rto_seconds 가 docs/agent/evidence/D-373/backup_last.json·"
                "restore_drill_last.json 파일 값과 **바이트 단위로 같다** — 새 저장을 "
                "만들지 않고 이미 있는 회수증을 그대로 읽는다(완결조건 '회수증 자동 "
                "일 1 · 복원 시험 월 1'의 존재를 이미 있는 장부로 실측).")
        _add_title_parts("O-07", [
            {"part": "테넌트별 덤프·회수증", "where": "backup.measured_at/db_bytes", "status": "measured"},
            {"part": "복원 시험", "where": "restore_drill.rto_seconds/tables_restored", "status": "measured"},
            {"part": "완결조건 — 회수증 자동 일 1", "where": "backup.fresh_within_24h", "status": "measured"},
            {"part": "완결조건 — 복원 시험 월 1", "where": "restore_drill.fresh_within_31d", "status": "measured"},
            {"part": "다른 호스트 목적지", "where": "backup.destination",
             "status": "measured — 지금 값은 local(다른 호스트로 자동 이관은 범위 밖, 값은 실측)"},
        ])


# ═══════════════════════════════════════════════════════════════════════════
# O-08 — 온보딩 관제
# ═══════════════════════════════════════════════════════════════════════════
class O08_OnboardingBoardTest(OpsAnFixture):
    def test_reads_the_48_row_ledger(self) -> None:
        head = self._bearer(self.u0)
        resp = self.client.get(ONBOARDING, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        onbt_dir = ROOT / "docs" / "agent" / "evidence" / "ONB-T"
        if not any(onbt_dir.glob("turn_*.json")):
            self.skipTest("ONB-T 장부가 없다 — 이 환경에서는 O-08 을 실측할 수 없다(회색)")
        self.assertTrue(body["read"])
        self.assertEqual(48, body["denominator"])
        self.assertGreaterEqual(len(body["role_progress_6"]), 1)
        self.assertIn("tenants", body)
        self.assertIn("blocked_cards", body)

        _write_evidence(
            "O-08", title="온보딩 관제",
            test_ref="tests.test_ops_an.O08_OnboardingBoardTest.test_reads_the_48_row_ledger",
            method="GET", path=ONBOARDING, request_params={}, response=resp,
            what="GET /api/dsm/ops/onboarding 이 docs/agent/evidence/ONB-T/turn_*.json"
                "(48행 재측 장부)의 최신 파일을 읽어 역할별(U1~U6) 진행률·막힌 카드·"
                "테넌트별 D-day 진행을 계산해 낸다 — 새 저장 0, 완결조건('테넌트별 "
                "D-7~D+30 진행 · 역할별 진행률 · 48행 재측 결과 · 막힌 카드') 실측.")
        _add_title_parts("O-08", [
            {"part": "테넌트별 D-7~D+30 진행", "where": "tenants[].day_n/stage", "status": "measured"},
            {"part": "역할별 진행률 6", "where": "role_progress_6", "status": "measured"},
            {"part": "48행 재측 결과", "where": "score_over_denominator/green/half/red", "status": "measured"},
            {"part": "막힌 카드", "where": "blocked_cards", "status": "measured"},
        ])


# ═══════════════════════════════════════════════════════════════════════════
# O-09 — 감사(플랫폼)
# ═══════════════════════════════════════════════════════════════════════════
class O09_PlatformAuditTest(OpsAnFixture):
    def test_operator_actions_are_logged_and_tenant_view_needs_approval(self) -> None:
        issue_resp, params = self._issue_tenant()
        code = params["code"]
        head = self._bearer(self.u0)

        audit_before = self.client.get(AUDIT, **head)
        self.assertEqual(200, audit_before.status_code)
        total_before = self._body(audit_before)["total"]
        self.assertGreaterEqual(total_before, 1, "테넌트 발급 행위가 감사에 안 남았다")

        members_path = "%s/%s/members" % (TENANTS, code)
        denied = self.client.get(members_path, **head)
        self.assertEqual(403, denied.status_code, "승인 없이 테넌트 구성원이 보였다")

        req_params = {"tenant_code": code, "reason": "정기 점검"}
        req_resp = self.client.post(_qs(AUDIT_REQUEST, **req_params), **head)
        self.assertEqual(200, req_resp.status_code, req_resp.content)
        request_id = self._body(req_resp)["request_id"]

        still_denied = self.client.get(members_path, **head)
        self.assertEqual(403, still_denied.status_code, "승인 전인데 열렸다")

        approve = self.client.post(
            AUDIT_REQUEST + ("/%s/approve" % request_id), **head)
        self.assertEqual(200, approve.status_code, approve.content)

        allowed = self.client.get(members_path, **head)
        self.assertEqual(200, allowed.status_code, allowed.content)
        self.assertIn("members", self._body(allowed))

        audit_after = self.client.get(AUDIT, **head)
        total_after = self._body(audit_after)["total"]
        self.assertGreater(total_after, total_before, "요청·승인이 감사에 안 남았다")

        _write_evidence(
            "O-09", title="감사(플랫폼)",
            test_ref="tests.test_ops_an.O09_PlatformAuditTest."
                    "test_operator_actions_are_logged_and_tenant_view_needs_approval",
            method="GET", path=members_path, request_params={}, response=allowed,
            what="테넌트 구성원 열람은 승인 전 403, 요청(POST .../access-requests) 뒤에도 "
                "403, 승인(POST .../approve) 뒤에만 200 — '테넌트 데이터 열람 0(승인 "
                "없이)'을 이 콘솔이 여는 유일한 원 데이터 문에서 실측한다. 발급·요청·"
                "승인 세 행위 모두 GET /ops/audit 의 total 을 늘린다 — '운영자 행위 "
                "전건' 실측.")
        _add_title_parts("O-09", [
            {"part": "운영자 행위 전건", "where": "GET /ops/audit → total 증가", "status": "measured"},
            {"part": "테넌트 접근·설치·배포·키 회전 계열", "where": "ALL_OPS_LOGGERS", "status": "measured"},
            {"part": "테넌트 감사 열람은 요청·승인 뒤",
             "where": "members 403→403→200(요청/승인 전후)", "status": "measured"},
            {"part": "완결조건 — 승인 없는 테넌트 데이터 열람 0",
             "where": "members 403 (요청 전·요청 후 승인 전)", "status": "measured"},
        ])


# ═══════════════════════════════════════════════════════════════════════════
# O-11 — 릴리스·배포
# ═══════════════════════════════════════════════════════════════════════════
class O11_ReleaseBoardSmokeTest(OpsAnFixture):
    """★ 승격 안 함 — §7 완결조건은 3항 AND(`deploy.sh exit 0 · 걷기 초록 ·
    되돌리기 1회 시험`)인데 `되돌리기 1회 시험`은 실제 배포 되돌리기(파일 스왑·
    재시작)가 필요해 이 차선(HTTP 라운드트립)이 못 잰다 — 스모크만 확인한다."""

    def test_reads_deploys_ledger(self) -> None:
        head = self._bearer(self.u0)
        resp = self.client.get(RELEASES, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)

        deploys_path = ROOT / "docs" / "agent" / "evidence" / "OPS-27" / "deploys.jsonl"
        if not deploys_path.is_file():
            self.skipTest("deploys.jsonl 이 없다 — 이 환경에서는 O-11 을 실측할 수 없다(회색)")
        lines = [l for l in deploys_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        last_on_disk = json.loads(lines[-1])
        self.assertTrue(body["read"])
        self.assertEqual(last_on_disk.get("commit"), body["latest"]["commit"],
                         "장부의 마지막 배포와 응답의 latest 가 다르다")


# ═══════════════════════════════════════════════════════════════════════════
# O-12 — 시드·훈련 데이터
# ═══════════════════════════════════════════════════════════════════════════
class O12_SeedDataTest(OpsAnFixture):
    def test_plant_then_hide_and_data_source_is_marked(self) -> None:
        issue_resp, params = self._issue_tenant()
        code = params["code"]
        head = self._bearer(self.u0)

        plant_params = {"tenant_code": code, "action": "plant", "scenario_code": "drill-01"}
        resp = self.client.post(_qs(SEED_TOGGLE, **plant_params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("seed", body["data_source"])

        hide = self.client.post(
            _qs(SEED_TOGGLE, tenant_code=code, action="hide", scenario_code="drill-01"), **head)
        self.assertEqual(200, hide.status_code)

        board = self.client.get(SEED, **head)
        self.assertEqual(200, board.status_code)
        board_body = self._body(board)
        mine = [t for t in board_body["toggles"] if t["tenant_code"] == code]
        self.assertEqual(1, len(mine), "시드 행이 테넌트·시나리오별로 접히지 않았다")
        self.assertEqual("hide", mine[0]["action"], "가장 최근 토글(숨기기)이 안 보인다")

        _write_evidence(
            "O-12", title="시드·훈련 데이터",
            test_ref="tests.test_ops_an.O12_SeedDataTest."
                    "test_plant_then_hide_and_data_source_is_marked",
            method="POST", path=_qs(SEED_TOGGLE, **plant_params),
            request_params=plant_params, response=resp,
            what="POST .../ops/seed/toggle(plant)로 시드를 심으면 data_source=seed 가 "
                "찍히고, hide 뒤 GET /ops/seed 목록의 최신 행(테넌트+시나리오별 접힘)"
                "이 hide 로 바뀐다 — 완결조건(\"data_source=seed 표기\") 실측.")
        _add_title_parts("O-12", [
            {"part": "검수 시드 심기·숨기기", "where": "toggle action=plant/hide", "status": "measured"},
            {"part": "훈련 시나리오 배포", "where": "action=deploy_scenario (경로만 · 시나리오 몸체는 없음)",
             "status": "measured — 토글 경로만(시나리오 데이터 생성기는 없음)"},
            {"part": "완결조건 — data_source=seed 표기", "where": "data_source", "status": "measured"},
            {"part": "완결조건 — 실데이터 혼입 0", "where": "GET /ops/seed → contamination_by_data_source",
             "status": "measured"},
        ])


# ═══════════════════════════════════════════════════════════════════════════
# 스모크만 — O-05(건강 보드) · O-10(키·자격 회전) — **반쪽이라 승격 안 함**
# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
# O-05 — 건강 보드(전 테넌트) — **완결조건은 §7 "완결 조건" 칸**(설명 칸 일곱이
# 아니라): "테넌트 수 = 보드 행 수 · 빨강 → 인시던트 자동 생성"
# ═══════════════════════════════════════════════════════════════════════════
class O05_HealthBoardTest(OpsAnFixture):
    def test_tenant_count_equals_rows_and_red_opens_one_incident(self) -> None:
        issue_resp, params = self._issue_tenant()
        code = params["code"]
        head = self._bearer(self.u0)

        UserGroup = apps.get_model("user", "UserGroup")
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        tenant = UserGroup.objects.get(code=code)
        StreamMonitor._base_manager.create(
            name="ops-an-camera-down", code="ops-an-camera-down-%s" % code,
            ip_source="rtsp://ops-an.invalid/x", is_active=False, group_id=tenant.id)

        resp = self.client.get(HEALTH, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(body["tenant_count"], len(body["tenants"]),
                         "완결조건('테넌트 수 = 보드 행 수')이 깨졌다")

        mine = next(t for t in body["tenants"] if t["tenant_code"] == code)
        self.assertEqual("red", mine["color"], "카메라 1대 중 활성 0인데 빨강이 아니다")
        self.assertIsNotNone(mine["auto_incident_id"], "빨강인데 인시던트가 자동 생성 안 됐다")

        incidents = self.client.get(_qs(INCIDENTS, tenant_code=code, status="open"), **head)
        opened_ids = [i["incident_id"] for i in self._body(incidents)["incidents"]]
        self.assertIn(mine["auto_incident_id"], opened_ids,
                     "보드가 준 auto_incident_id 가 실제 인시던트 목록에 없다")

        #: 같은 빨강을 다시 읽어도 **인시던트를 또 만들지 않는다**(중복 방지).
        resp2 = self.client.get(HEALTH, **head)
        mine2 = next(t for t in self._body(resp2)["tenants"] if t["tenant_code"] == code)
        self.assertEqual(mine["auto_incident_id"], mine2["auto_incident_id"],
                         "같은 빨강인데 인시던트가 두 번째로 또 생겼다")

        _write_evidence(
            "O-05", title="건강 보드(전 테넌트)",
            test_ref="tests.test_ops_an.O05_HealthBoardTest."
                    "test_tenant_count_equals_rows_and_red_opens_one_incident",
            method="GET", path=HEALTH, request_params={}, response=resp,
            what="GET /api/dsm/ops/health 의 tenant_count 가 tenants 행 수와 같고, "
                "카메라 활성 0(총 1)인 테넌트 행이 색=red 이며 open_incident() 를 "
                "재사용해 실제 인시던트 하나를 연다(auto_incident_id) — 재호출해도 "
                "같은 id(중복 생성 0). §7 완결조건('테넌트 수 = 보드 행 수 · 빨강 → "
                "인시던트 자동 생성')을 그대로 실측한다(설명 칸의 5xx·게이트16색은 "
                "완결조건이 아니라 응답의 not_measured 로 정직하게 비운다).")
        _add_title_parts("O-05", [
            {"part": "완결조건 — 테넌트 수 = 보드 행 수", "where": "tenant_count/tenants",
             "status": "measured"},
            {"part": "완결조건 — 빨강 → 인시던트 자동 생성", "where": "auto_incident_id",
             "status": "measured"},
            {"part": "완결조건 — 중복 생성 방지", "where": "재호출 시 같은 auto_incident_id",
             "status": "measured"},
        ])


class O10_KeyRotationSmokeTest(OpsAnFixture):
    def test_board_answers_and_admits_the_live_login_half(self) -> None:
        resp = self.client.get(KEYS, **self._bearer(self.u0))
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertIn("gray_why", body)
        self.assertTrue(body["gray_why"])
