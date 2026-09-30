# -*- coding: utf-8 -*-
"""턴 AQ · 차선 N2 — O 운영 콘솔 보드 배선(P-435 화면 축).

지난 턴 재판정(`docs/agent/evidence/SPEC/N1_rejudge_ap.md` §1)이 O 여덟을 「서버 문만
있고 운영 콘솔 보드가 없다」로 내렸다. 이 파일은 보드마다 두 가지를 잰다.

  ① **누름 → 재조회** — 화면의 누르는 자리가 부르는 바로 그 POST 를 U0 로 두드리고,
     그 보드가 그리는 GET 을 **다시 불러** 새 값이 보이는지 확인한다.
  ② **화면 소스 정적 대조** — 그 보드 컴포넌트(`frontend/src/features/ops/components/
     *Board.tsx`)에 `data-gx` 누르는 자리와 부르는 API 함수가 있고, 그 함수가
     `api.ts` 에서 같은 API 경로로 이어지며, `OpsHome.tsx` 가 그 보드를 그린다.

그리고 U0 아닌 역할은 쓰기 문에서 403 이다(문지기 시험 1).

이 파일은 증거 json(`<id>.json`)을 쓰지 않는다 — 사람 표(`<id>.retro.md`)는 손으로만
고친다(P-431). 새 시험은 `title_parts`·`retro` 키를 건드리지 않는다.

캐시 처리: 우회 — 기반 `OpsAnFixture`(=`FwsHttpTest`)가 `setUp` 에서 `cache.clear()` 뒤 `X-No-Cache` 클라이언트로 부르고, 이 파일의 `setUpTestData` 첫 줄이 스레드에 남은 요청을 비운다.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from django.apps import apps

from tests.test_fws_app import _qs
from tests.test_ops_an import (
    APPS_INSTALL,
    APPS_LIST,
    APPS_STATUS,
    AUDIT,
    AUDIT_REQUEST,
    BACKUPS,
    HEALTH,
    INCIDENTS,
    KEYS,
    ONBOARDING,
    RELEASES,
    SEED,
    SEED_TOGGLE,
    TENANTS,
    OpsAnFixture,
)

KEYS_ROTATE = "/api/dsm/ops/keys/rotate"


def _frontend_src() -> Path | None:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").is_file():
            return base
    return None


class _Fixture(OpsAnFixture):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        from core.middleware.refresh_token import thread_local

        thread_local.request = None
        super().setUpTestData()

    def _u0(self) -> dict:
        return self._bearer(self.u0)

    def _get(self, path: str) -> dict:
        resp = self.client.get(path, **self._u0())
        self.assertEqual(200, resp.status_code, resp.content[:300])
        return self._body(resp)

    def _post(self, path: str, **params) -> dict:
        resp = self.client.post(_qs(path, **params), **self._u0())
        self.assertEqual(200, resp.status_code, resp.content[:400])
        return self._body(resp)

    def _new_tenant(self) -> str:
        resp, params = self._issue_tenant()
        self.assertEqual(200, resp.status_code, resp.content[:300])
        return params["code"]

    # ── 정적 대조 ────────────────────────────────────────────────────────
    def _assert_screen(self, board_file: str, gx: list[str], api_fns: list[str],
                       paths: list[str]) -> None:
        src = _frontend_src()
        self.assertIsNotNone(src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        body = (src / "features/ops/components" / board_file).read_text(encoding="utf-8")
        api = (src / "features/ops/api.ts").read_text(encoding="utf-8")
        home = (src / "features/ops/pages/OpsHome.tsx").read_text(encoding="utf-8")
        frame = (src / "features/ops/components/BoardFrame.tsx").read_text(encoding="utf-8")
        for g in gx:
            if g.endswith("-refresh"):
                #: 다시 불러오기 단추는 겉틀(BoardFrame)이 `<gx>-refresh` 로 세운다 —
                #: 보드가 그 접두를 넘기고, 겉틀이 그 모양으로 다는지 둘 다 본다.
                prefix = g[: -len("-refresh")]
                self.assertTrue('gx="%s"' % prefix in body,
                                "%s 가 겉틀에 접두 %s 를 넘기지 않는다" % (board_file, prefix))
                self.assertTrue("data-gx={`${gx}-refresh`}" in frame,
                                "BoardFrame 에 다시 불러오기 단추가 없다")
                self.assertTrue("onClick={onReload}" in frame)
                continue
            self.assertTrue('data-gx="%s"' % g in body,
                            "%s 에 누르는 자리 %s 가 없다" % (board_file, g))
        for fn in api_fns:
            self.assertTrue(fn in body, "%s 가 %s 를 부르지 않는다" % (board_file, fn))
            self.assertTrue("export function %s" % fn in api, "api.ts 에 %s 가 없다" % fn)
        for p in paths:
            self.assertTrue("'%s'" % p in api, "api.ts 에 API 경로 %s 가 없다" % p)
        comp = board_file.rsplit(".", 1)[0]
        self.assertTrue("import %s from '../components/%s'" % (comp, comp) in home,
                      "OpsHome.tsx 가 %s 를 들이지 않는다" % comp)
        self.assertTrue("<%s />" % comp in home, "OpsHome.tsx 가 %s 를 그리지 않는다" % comp)
        #: 누른 뒤 재조회 — 보드의 누름은 `runOpsAction(…, board.reload)` 로 GET 을 다시 부른다.
        if any(not fn.startswith("fetch") for fn in api_fns):
            self.assertTrue("board.reload" in body, "%s 가 누른 뒤 보드를 다시 부르지 않는다" % board_file)


# ═══════════════════════════════════════════════════════════════════════════
# 문지기 — U0 아니면 쓰기 문도 403
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_NonOperatorIs403Test(_Fixture):
    def test_tenant_admin_is_403_on_board_write_doors(self) -> None:
        head = self._bearer(self.user_a)
        doors = [
            _qs(TENANTS, code="x-%s" % uuid.uuid4().hex[:6], name="x", admin_username="x",
                admin_email="x@test.invalid", admin_password="x"),
            _qs(APPS_INSTALL, tenant_code="x", app_code="dsm", version="1"),
            _qs(INCIDENTS, tenant_code="x", app_code="dsm", severity="minor"),
            _qs(AUDIT_REQUEST, tenant_code="x", reason="x"),
            _qs(KEYS_ROTATE, tenant_code="x", key_id=1),
            _qs(SEED_TOGGLE, tenant_code="x", action="deploy_scenario"),
        ]
        for door in doors:
            resp = self.client.post(door, **head)
            self.assertEqual(403, resp.status_code, "%s 가 U0 아닌 사람에게 열렸다" % door)
        self.assertEqual(403, self.client.get(SEED, **head).status_code)


# ═══════════════════════════════════════════════════════════════════════════
# O-01 테넌트 발급
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O01_TenantIssueBoardTest(_Fixture):
    def test_issue_then_board_reload_shows_row_with_hierarchy_and_domain(self) -> None:
        code = "t-%s" % uuid.uuid4().hex[:8]
        admin = "aqn2_%s" % uuid.uuid4().hex[:8]
        before = self._get(TENANTS)["count"]
        issued = self._post(TENANTS, code=code, name="보드 발급 시험 %s" % code,
                            admin_username=admin, admin_email="%s@test.invalid" % admin,
                            admin_password="Tenant-Admin-Pw-1!", region="시험도",
                            domain="%s.test.invalid" % code, departments="산림과, 안전총괄과")
        self.assertEqual(["산림과", "안전총괄과"], issued["departments"])

        after = self._get(TENANTS)
        self.assertEqual(before + 1, after["count"])
        row = next(t for t in after["tenants"] if t["tenant_code"] == code)
        self.assertEqual("시험도", row["region"])
        self.assertEqual(["산림과", "안전총괄과"], row["departments"])
        self.assertEqual("%s.test.invalid" % code, row["domain"])
        self.assertGreaterEqual(row["member_count"], 1, "초기 관리자 1 이 구성원으로 안 보인다")

        Department = apps.get_model("user", "Department")
        UserGroup = apps.get_model("user", "UserGroup")
        g = UserGroup._base_manager.get(code=code)
        self.assertEqual(2, Department._base_manager.filter(group_id=g.id).count())

    def test_screen_wires_issue_button(self) -> None:
        self._assert_screen(
            "TenantsBoard.tsx",
            gx=["o-01-issue", "o-01-refresh", "o-01-domain", "o-01-region", "o-01-departments"],
            api_fns=["issueTenant", "fetchTenants"], paths=[TENANTS])


# ═══════════════════════════════════════════════════════════════════════════
# O-02 앱 설치·버전
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O02_AppsBoardTest(_Fixture):
    def test_install_upgrade_deactivate_each_visible_on_reload(self) -> None:
        code = self._new_tenant()
        self._post(APPS_INSTALL, tenant_code=code, app_code="dsm", version="1.1")
        row = next(r for r in self._get(APPS_LIST)["installs"]
                   if r["tenant_code"] == code and r["app_code"] == "dsm")
        self.assertEqual(("1.1", "active"), (row["version"], row["status"]))

        self._post(APPS_INSTALL, tenant_code=code, app_code="dsm", version="1.2")
        row = next(r for r in self._get(APPS_LIST)["installs"]
                   if r["tenant_code"] == code and r["app_code"] == "dsm")
        self.assertEqual(("1.2", "1.1"), (row["version"], row["upgraded_from"]))

        self._post(APPS_STATUS, tenant_code=code, app_code="dsm", status="inactive")
        row = next(r for r in self._get(APPS_LIST)["installs"]
                   if r["tenant_code"] == code and r["app_code"] == "dsm")
        self.assertEqual("inactive", row["status"])

    def test_screen_wires_install_and_status(self) -> None:
        self._assert_screen(
            "AppsBoard.tsx",
            gx=["o-02-install", "o-02-refresh", "o-02-status"],
            api_fns=["installApp", "setAppStatus", "fetchAppInstalls"],
            paths=[APPS_LIST, APPS_INSTALL, APPS_STATUS])
        body = (_frontend_src() / "features/ops/components/AppsBoard.tsx").read_text(encoding="utf-8")
        self.assertIn("o-02-deactivate", body)
        self.assertIn("o-02-activate", body)


# ═══════════════════════════════════════════════════════════════════════════
# O-05 건강 보드
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O05_HealthBoardTest(_Fixture):
    def test_reload_turns_red_and_shows_auto_incident_and_all_noun_columns(self) -> None:
        code = self._new_tenant()
        first = next(t for t in self._get(HEALTH)["tenants"] if t["tenant_code"] == code)
        for key in ("cameras", "queue_lag_sec", "storage_used_pct", "backup_receipt_at",
                    "survival_alert_late", "color", "auto_incident_id"):
            self.assertIn(key, first, "건강 보드 행에 %s 칸이 없다" % key)

        UserGroup = apps.get_model("user", "UserGroup")
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        g = UserGroup.objects.get(code=code)
        StreamMonitor._base_manager.create(
            name="aq-n2-down", code="aq-n2-down-%s" % code,
            ip_source="rtsp://aq-n2.invalid/x", is_active=False, group_id=g.id)

        again = next(t for t in self._get(HEALTH)["tenants"] if t["tenant_code"] == code)
        self.assertEqual("red", again["color"])
        self.assertIsNotNone(again["auto_incident_id"])
        self.assertEqual({"active": 0, "total": 1}, again["cameras"])

    def test_screen_draws_every_noun_column(self) -> None:
        self._assert_screen(
            "HealthBoard.tsx",
            gx=["o-05-refresh", "o-05-cameras", "o-05-queue-lag", "o-05-storage",
                "o-05-backup-receipt", "o-05-survival", "o-05-color", "o-05-auto-incident"],
            api_fns=["fetchHealthBoard"], paths=[HEALTH])


# ═══════════════════════════════════════════════════════════════════════════
# O-06 인시던트
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O06_IncidentsBoardTest(_Fixture):
    def _row(self, incident_id: str) -> dict:
        return next(i for i in self._get(INCIDENTS)["incidents"] if i["incident_id"] == incident_id)

    def test_open_respond_escalate_close_each_visible_on_reload(self) -> None:
        code = self._new_tenant()
        opened = self._post(INCIDENTS, tenant_code=code, app_code="dsm", severity="major",
                            summary="보드 시험")
        iid = opened["incident_id"]
        row = self._row(iid)
        self.assertEqual("open", row["status"])
        self.assertTrue(row["sla_first_response_due"])

        self._post("%s/%s/respond" % (INCIDENTS, iid))
        self.assertEqual("acknowledged", self._row(iid)["status"])

        self._post("%s/%s/escalate" % (INCIDENTS, iid))
        self.assertEqual("escalated", self._row(iid)["status"])

        self._post("%s/%s/close" % (INCIDENTS, iid), cause="카메라 전원", prevention="전원 이중화")
        row = self._row(iid)
        self.assertEqual("closed", row["status"])
        self.assertIn("카메라 전원", row["closing_report"])

    def test_screen_wires_four_actions(self) -> None:
        self._assert_screen(
            "IncidentsBoard.tsx",
            gx=["o-06-open", "o-06-respond", "o-06-escalate", "o-06-close", "o-06-cause",
                "o-06-refresh", "o-06-closing-report"],
            api_fns=["openIncident", "respondIncident", "escalateIncident", "closeIncident",
                     "fetchIncidents"],
            paths=[INCIDENTS])


# ═══════════════════════════════════════════════════════════════════════════
# O-07 백업·복구
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O07_BackupBoardTest(_Fixture):
    def test_reload_reads_the_same_receipt(self) -> None:
        first = self._get(BACKUPS)
        again = self._get(BACKUPS)
        for part in ("backup", "restore_drill"):
            self.assertIn(part, first)
        self.assertEqual(first["backup"]["measured_at"], again["backup"]["measured_at"],
                         "새 저장 없이 같은 회수증을 읽어야 한다")
        for key in ("measured_at", "verdict", "db_bytes", "destination", "fresh_within_24h"):
            self.assertIn(key, first["backup"])
        for key in ("measured_at", "rto_seconds", "tables_restored", "fresh_within_31d"):
            self.assertIn(key, first["restore_drill"])

    def test_screen_draws_receipt_and_drill(self) -> None:
        self._assert_screen(
            "BackupBoard.tsx",
            gx=["o-07-refresh", "o-07-receipt", "o-07-receipt-at", "o-07-destination",
                "o-07-drill", "o-07-drill-at"],
            api_fns=["fetchBackupBoard"], paths=[BACKUPS])


# ═══════════════════════════════════════════════════════════════════════════
# O-08 온보딩 관제
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O08_OnboardingBoardTest(_Fixture):
    def test_new_tenant_appears_in_d_window_table_on_reload(self) -> None:
        code = self._new_tenant()
        body = self._get(ONBOARDING)
        self.assertTrue(body.get("read"), "48행 재측 장부를 못 읽었다 — 회색을 초록으로 두지 않는다")
        row = next(t for t in body["tenants"] if t["tenant_code"] == code)
        self.assertEqual(0, row["day_n"])
        self.assertTrue(row["stage"])
        self.assertIn("role_progress_6", body)
        self.assertIn("blocked_cards", body)

    def test_screen_draws_table_progress_blocked(self) -> None:
        self._assert_screen(
            "OnboardingBoard.tsx",
            gx=["o-08-refresh", "o-08-score", "o-08-role-progress", "o-08-tenants", "o-08-blocked"],
            api_fns=["fetchOnboardingBoard"], paths=[ONBOARDING])


# ═══════════════════════════════════════════════════════════════════════════
# O-09 감사(플랫폼)
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O09_AuditBoardTest(_Fixture):
    def test_request_then_approve_each_visible_on_reload_and_members_open_after(self) -> None:
        code = self._new_tenant()
        members = "%s/%s/members" % (TENANTS, code)
        self.assertEqual(403, self.client.get(members, **self._u0()).status_code)

        req = self._post(AUDIT_REQUEST, tenant_code=code, reason="장애 원인 확인")
        rid = req["request_id"]
        latest = next(e for e in self._get(AUDIT)["entries"] if e.get("request_id") == rid)
        self.assertEqual("requested", latest["status"])
        self.assertEqual(403, self.client.get(members, **self._u0()).status_code)

        self._post("%s/%s/approve" % (AUDIT_REQUEST, rid))
        latest = next(e for e in self._get(AUDIT)["entries"] if e.get("request_id") == rid)
        self.assertEqual("approved", latest["status"])
        self.assertEqual(200, self.client.get(members, **self._u0()).status_code)

    def test_screen_wires_request_approve_members(self) -> None:
        self._assert_screen(
            "AuditBoard.tsx",
            gx=["o-09-request-access", "o-09-approve", "o-09-view-members", "o-09-entries",
                "o-09-refresh"],
            api_fns=["requestTenantAccess", "approveTenantAccess", "fetchTenantMembers",
                     "fetchAuditLog"],
            paths=[AUDIT, AUDIT_REQUEST])


# ═══════════════════════════════════════════════════════════════════════════
# O-10 키·자격 회전 — 회전 절차 화면
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O10_KeysBoardTest(_Fixture):
    def test_rotate_then_board_reload_shows_new_audit_line(self) -> None:
        from common.tenant_scope import TenantScope
        from kernels.k5_trust import issue_key

        resp, params = self._issue_tenant()
        self.assertEqual(200, resp.status_code, resp.content[:300])
        code = params["code"]
        CoreUser = apps.get_model("user", "CoreUser")
        admin = CoreUser.objects.get(username=params["admin_username"])
        key_id = issue_key(scope=TenantScope.of(admin), name="aq-n2-o10-board").view.key_id

        before = self._get(KEYS)["rotation_audit_count"]
        self._post(KEYS_ROTATE, tenant_code=code, key_id=key_id)
        after = self._get(KEYS)
        self.assertEqual(before + 1, after["rotation_audit_count"])
        self.assertEqual(key_id, after["last_rotation_audit"]["key_id"])
        self.assertEqual(code, after["last_rotation_audit"]["tenant_code"])

    def test_screen_wires_rotate_and_runbook(self) -> None:
        self._assert_screen(
            "KeysBoard.tsx",
            gx=["o-10-rotate", "o-10-runbook", "o-10-next-due", "o-10-last-rotation",
                "o-10-rotation-count", "o-10-refresh"],
            api_fns=["rotateKey", "fetchKeyBoard"], paths=[KEYS, KEYS_ROTATE])


# ═══════════════════════════════════════════════════════════════════════════
# O-11 릴리스·배포 — 배포 기록 화면
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O11_ReleasesBoardTest(_Fixture):
    def test_reload_reads_deploy_record_with_three_checks(self) -> None:
        body = self._get(RELEASES)
        for key in ("deploys", "latest_deploy_exit_ok", "latest_smoke_ok",
                    "latest_rollback_drill_ok", "deploy_gate_passed"):
            self.assertIn(key, body)
        self.assertEqual(body["count"], self._get(RELEASES)["count"])

    def test_screen_draws_deploy_record(self) -> None:
        self._assert_screen(
            "ReleasesBoard.tsx",
            gx=["o-11-refresh", "o-11-deploys", "o-11-gate", "o-11-latest-drill"],
            api_fns=["fetchReleaseBoard"], paths=[RELEASES])


# ═══════════════════════════════════════════════════════════════════════════
# O-12 시드·훈련 데이터
# ═══════════════════════════════════════════════════════════════════════════
class AqN2_O12_SeedBoardTest(_Fixture):
    def _drill(self, code: str) -> dict:
        return next(t for t in self._get(SEED)["drill_by_tenant"] if t["tenant_code"] == code)

    def test_deploy_scenario_really_turns_drill_on_and_end_turns_it_off(self) -> None:
        code = self._new_tenant()
        self.assertFalse(self._drill(code)["drill_mode"])

        out = self._post(SEED_TOGGLE, tenant_code=code, action="deploy_scenario",
                         scenario_code="산불-초기대응", note="온보딩 훈련")
        self.assertTrue(out["drill_mode"])
        state = self._drill(code)
        self.assertTrue(state["drill_mode"], "배포 뒤 재조회에서 훈련 모드가 안 켜졌다")
        self.assertEqual("온보딩 훈련", state["reason"])

        #: 스위치 자신(K2 가 묻는 한 줄)도 켜졌다 — 기록만이 아니다.
        from stream_monitors.services import drill
        UserGroup = apps.get_model("user", "UserGroup")
        gid = UserGroup._base_manager.get(code=code).id
        self.assertTrue(drill.is_drill_mode(group_id=gid))

        self._post(SEED_TOGGLE, tenant_code=code, action="end_scenario", scenario_code="산불-초기대응")
        self.assertFalse(self._drill(code)["drill_mode"])
        self.assertFalse(drill.is_drill_mode(group_id=gid))

    def test_plant_and_hide_visible_on_reload(self) -> None:
        code = self._new_tenant()
        self._post(SEED_TOGGLE, tenant_code=code, action="plant", scenario_code="검수")
        row = next(t for t in self._get(SEED)["toggles"]
                   if t["tenant_code"] == code and t["scenario_code"] == "검수")
        self.assertEqual(("plant", "seed"), (row["action"], row["data_source"]))
        self._post(SEED_TOGGLE, tenant_code=code, action="hide", scenario_code="검수")
        row = next(t for t in self._get(SEED)["toggles"]
                   if t["tenant_code"] == code and t["scenario_code"] == "검수")
        self.assertEqual("hide", row["action"])

    def test_screen_wires_four_actions(self) -> None:
        self._assert_screen(
            "SeedBoard.tsx",
            gx=["o-12-refresh", "o-12-drill-state", "o-12-history", "o-12-tenant"],
            api_fns=["toggleSeed", "fetchSeedBoard"], paths=[SEED, SEED_TOGGLE])
        body = (_frontend_src() / "features/ops/components/SeedBoard.tsx").read_text(encoding="utf-8")
        for g in ("o-12-plant", "o-12-hide", "o-12-deploy-scenario", "o-12-end-scenario"):
            self.assertIn("'%s'" % g, body, "시드 보드에 %s 단추가 없다" % g)
