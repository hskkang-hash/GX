# -*- coding: utf-8 -*-
"""FWS App(L4) — U5(기관 관리자·산불 설정) 별표 절 넷의 **HTTP 실측**과
`docs/agent/evidence/SPEC/*.json` 생성 (WO-GX-20260929-17 §5 P-356 · 턴 AN 차선 N4).

닫는 절: FWS-U5-01(카메라 산불 표식) · FWS-U5-02(초소·순찰함·순찰 구역) ·
FWS-U5-03(마을·대피소·요양시설 — 대피 대상 자동 산출) · FWS-U5-04(알림 규칙 ·
야간 5분대기조 채널). FWS-U5-05(오탐 필터 모델)는 이 파일이 닫지 않는다 —
`scripts/verify_spec_u5_an.py`·`docs/agent/evidence/SPEC/N4_promotions_an.md` 의
「무엇이 없는가」를 본다.

캐시 처리: 우회 — `tests.no_cache.NO_CACHE` 헤더(`test_fws_f6.py` 와 같은 규약).
`FwsHttpTest`(`test_fws_app.py`)를 그대로 쓴다 — 같은 표를 두 벌로 만들지 않는다.

★ 관리자 역할 — `test_p356_u4_spec_promotions.py::U4Fixture` 와 같은 판단(그 파일
  머리말): 역할 코드는 unique 라 `code="admin"` 한 역할을 `user_a`·`user_b` 양쪽에
  붙인다. 어느 테넌트인지는 계정의 `UserGroup` 링크가 가른다(`common/tenant_roles.
  py::is_tenant_admin` 은 요청자 자신의 소속만 본다).

★ 증거에 `title_parts`(WO-17 규약)를 더한다 — `_write_evidence`(공유 파일 소유,
  이 차선이 고치지 않는다)가 쓴 기본 증거를 **다시 열어** 그 필드만 얹는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.apps import apps
from django.core.cache import cache

from common.evidence_guard import allow_evidence_writes
from tests.test_fws_app import FwsHttpTest, _qs, _write_evidence

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"

CAMERAS = "/api/fws/admin/cameras"


def _marker_path(camera_id) -> str:
    return f"/api/fws/admin/cameras/{camera_id}/fire-marker"


POSTS = "/api/fws/admin/posts"
EVAC_TARGETS = "/api/fws/admin/evac-targets"
NOTIFY_RULES = "/api/fws/admin/notify-rules"
NOTIFY_RULES_TEST = "/api/fws/admin/notify-rules/test"


def _add_title_parts(clause_id: str, parts: list[dict]) -> None:
    """`_write_evidence` 가 쓴 파일을 다시 열어 `title_parts` 만 얹는다(머리말 참고)."""
    with allow_evidence_writes(
            "P-356 ② title_parts — 제목이 부르는 부분과 실측 상태를 표로 남긴다"):
        path = EVIDENCE_DIR / f"{clause_id}.json"
        body = json.loads(path.read_text(encoding="utf-8"))
        body["title_parts"] = parts
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")


class U5Fixture(FwsHttpTest):
    """`FwsHttpTest`(=`DsmFixture`)에 관리자 역할을 얹는다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        Role = apps.get_model("role", "Role")
        admin_role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
        cls.user_a.roles.add(admin_role)
        cls.user_b.roles.add(admin_role)
        # ★ `kernels.k2_notify.services.save_notification_rule` 는 `role_code` 가
        #   **실재하는 역할**이어야 지난다(제안 문자열만으로는 안 된다) — 그래서
        #   FWS 역할 제안(`admin_settings.FWS_NOTIFY_ROLE_SUGGESTIONS`)을 실제
        #   역할로 만들고, user_a 를 하나에 붙여 「받는 사람 0명」도 피한다.
        fws_role, _ = Role.objects.get_or_create(
            code="fws_response_team", defaults={"role_name": "fws_response_team"})
        cls.user_a.roles.add(fws_role)

    def setUp(self) -> None:
        super().setUp()
        cache.clear()


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-01 — 산불 감시 카메라 등록(고지대·PTZ 프리셋·열화상 채널·감시 반경 폴리곤)
# ═══════════════════════════════════════════════════════════════════════════
class U5_01_CameraFireMarkerTest(U5Fixture):
    def test_save_and_reread_carries_every_named_part(self) -> None:
        head = self._bearer(self.user_a)
        params = {
            "is_highland": True, "thermal_channel": "thermal-1",
            "ptz_presets": "north,south",
            "radius_polygon_json": '[{"lat":36.1,"lng":127.2},{"lat":36.2,"lng":127.3}]',
        }
        resp = self.client.post(_qs(_marker_path(self.stream_a.pk), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertTrue(body["is_highland"])
        self.assertEqual("thermal-1", body["thermal_channel"])
        self.assertEqual(["north", "south"], body["ptz_presets"])
        self.assertEqual(2, len(body["radius_polygon"]))

        reread = self.client.get(_marker_path(self.stream_a.pk), **head)
        self.assertEqual(200, reread.status_code, reread.content)
        self.assertEqual(body, self._body(reread))

        list_resp = self.client.get(CAMERAS, **head)
        self.assertEqual(200, list_resp.status_code, list_resp.content)
        rows = {c["camera_id"]: c for c in self._body(list_resp)["cameras"]}
        self.assertIn(self.stream_a.pk, rows)
        self.assertTrue(rows[self.stream_a.pk]["is_highland"])

        _write_evidence(
            "FWS-U5-01",
            title="산불 감시 카메라 등록(고지대·PTZ 프리셋·열화상 채널·감시 반경 폴리곤)",
            test_ref="tests.test_fws_u5.U5_01_CameraFireMarkerTest."
                    "test_save_and_reread_carries_every_named_part",
            method="POST", path=_qs(_marker_path(self.stream_a.pk), **params),
            request_params=params, response=resp,
            what="POST .../cameras/{id}/fire-marker 로 저장한 고지대·열화상 채널·PTZ "
                "프리셋·감시 반경 폴리곤이 재조회·목록 양쪽에 그대로 실려 온다 — 기존 "
                "DSM 카메라 모델(StreamMonitor)을 재사용하고 표식만 더했다")
        _add_title_parts("FWS-U5-01", [
            {"part": "고지대", "where": "is_highland", "status": "measured"},
            {"part": "PTZ 프리셋", "where": "ptz_presets", "status": "measured"},
            {"part": "열화상 채널", "where": "thermal_channel", "status": "measured"},
            {"part": "감시 반경 폴리곤", "where": "radius_polygon", "status": "measured"},
        ])

    def test_other_tenant_camera_is_404(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.get(_marker_path(self.stream_b.pk), **head)
        self.assertEqual(404, resp.status_code)

    def test_non_admin_is_403(self) -> None:
        # user_a·user_b 는 이 픽스처에서 이미 admin 역할을 갖고 있으므로(U5Fixture),
        # 권한 판정 자체를 재려면 admin 역할이 없는 계정을 따로 하나 만든다.
        CoreUser = apps.get_model("user", "CoreUser")
        plain = CoreUser.objects.create_user(
            username="u5_plain", password="test-only-not-a-secret", is_active=True,
            email="u5_plain@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: plain, "group": self.group_a})
        head_plain = self._bearer(plain)
        resp = self.client.get(_marker_path(self.stream_a.pk), **head_plain)
        self.assertEqual(403, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-02 — 초소·순찰함(NFC)·순찰 구역
# ═══════════════════════════════════════════════════════════════════════════
class U5_02_PostRegistryTest(U5Fixture):
    def _second_tenant_a_admin(self):
        """`self.group_a` 소속 두 번째 관리자 — 테넌트 전체 집계(곁표 · 턴 AO
        차선 O · P-411)를 재려면 "한 사람" 이 아니라 "같은 테넌트 두 사람"
        이어야 한다(U5 는 본래 관리자가 여럿일 수 있다 · `admin_settings.py`
        머리말)."""
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        admin_role = Role.objects.get(code="admin")
        user = CoreUser.objects.create_user(
            username="u5_02_second", password="test-only-not-a-secret",
            is_active=True, email="u5_02_second@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": self.group_a})
        user.roles.add(admin_role)
        return user

    def test_register_then_list_shows_the_same_post(self) -> None:
        head = self._bearer(self.user_a)
        params = {"post_code": "P-77", "name": "수리산 7번 초소",
                 "patrol_zone": "수리산 북측", "lat": 36.35, "lng": 127.38,
                 "nfc_boxes": "NFC-1,NFC-2"}
        resp = self.client.post(_qs(POSTS, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("수리산 7번 초소", body["name"])
        self.assertEqual(["NFC-1", "NFC-2"], body["nfc_boxes"])

        # ★ 턴 AO 차선 O · P-411 — 같은 테넌트의 **다른 관리자**가 등록한 초소도
        #   목록에 함께 보여야 한다(곁표가 넘어선 "등록한 사람 자신만" 한계).
        head2 = self._bearer(self._second_tenant_a_admin())
        params2 = {"post_code": "P-78", "name": "수리산 8번 초소",
                  "patrol_zone": "수리산 남측"}
        resp2 = self.client.post(_qs(POSTS, **params2), **head2)
        self.assertEqual(200, resp2.status_code, resp2.content)

        listed = self.client.get(POSTS, **head)
        self.assertEqual(200, listed.status_code, listed.content)
        codes = {p["post_code"]: p for p in self._body(listed)["posts"]}
        self.assertIn("P-77", codes)
        self.assertEqual("수리산 북측", codes["P-77"]["patrol_zone"])
        self.assertIn("P-78", codes,
                      "같은 테넌트 다른 관리자가 등록한 초소가 목록에 없다")
        self.assertEqual("수리산 남측", codes["P-78"]["patrol_zone"])

        # ★ 격리 — 다른 테넌트(user_b)는 이 테넌트의 초소를 하나도 못 본다.
        head_b = self._bearer(self.user_b)
        listed_b = self.client.get(POSTS, **head_b)
        self.assertEqual(200, listed_b.status_code, listed_b.content)
        self.assertEqual([], self._body(listed_b)["posts"])

        _write_evidence(
            "FWS-U5-02", title="초소·순찰함(NFC)·순찰 구역",
            test_ref="tests.test_fws_u5.U5_02_PostRegistryTest."
                    "test_register_then_list_shows_the_same_post",
            method="POST", path=_qs(POSTS, **params), request_params=params,
            response=resp,
            what="POST .../admin/posts 로 등록한 초소 이름·순찰 구역·순찰함(NFC) 코드가 "
                "GET .../admin/posts 목록에 그대로 보인다 — 같은 테넌트 다른 관리자가 "
                "등록한 초소(P-78)도 함께 보이고(곁표 common.models.AuditScope · 턴 "
                "AO 차선 O · P-411), 다른 테넌트는 같은 GET 에서 0건을 받는다(격리)")
        _add_title_parts("FWS-U5-02", [
            {"part": "초소", "where": "post_code/name", "status": "measured"},
            {"part": "순찰함(NFC)", "where": "nfc_boxes", "status": "measured"},
            {"part": "순찰 구역", "where": "patrol_zone", "status": "measured"},
            {"part": "테넌트 전체(같은 테넌트 여러 관리자)", "where": "GET .../admin/"
                                                          "posts — P-77·P-78 "
                                                          "둘 다",
            "status": "구현 — 곁표(AuditScope)로 실측(다른 테넌트는 0건)"},
        ])

    def test_blank_name_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(POSTS, post_code="P-1", name=""), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-03 — 마을·대피소·요양시설 등록(대피 대상 자동 산출)
# ═══════════════════════════════════════════════════════════════════════════
class U5_03_EvacTargetsTest(U5Fixture):
    def _second_tenant_a_admin(self):
        """`U5_02_PostRegistryTest._second_tenant_a_admin` 과 같은 판단 — 같은
        테넌트 두 관리자가 나눠 등록해도 대피 대상 총원이 합쳐지는지 잰다."""
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        admin_role = Role.objects.get(code="admin")
        user = CoreUser.objects.create_user(
            username="u5_03_second", password="test-only-not-a-secret",
            is_active=True, email="u5_03_second@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": self.group_a})
        user.roles.add(admin_role)
        return user

    def test_registering_villages_and_shelters_auto_computes_targets(self) -> None:
        head = self._bearer(self.user_a)
        village = {"kind": "village", "name": "안양천마을", "headcount": 312}
        care = {"kind": "care_facility", "name": "○○요양원", "headcount": 41}
        for params in (village, care):
            resp = self.client.post(_qs(EVAC_TARGETS, **params), **head)
            self.assertEqual(200, resp.status_code, resp.content)

        # ★ 턴 AO 차선 O · P-411 — 같은 테넌트의 **다른 관리자**가 등록한 대피소도
        #   자동 산출 합계에 함께 들어가야 한다(곁표가 넘어선 "등록한 사람 자신만"
        #   한계).
        head2 = self._bearer(self._second_tenant_a_admin())
        shelter = {"kind": "shelter", "name": "만안초 체육관", "headcount": 400}
        resp = self.client.post(_qs(EVAC_TARGETS, **shelter), **head2)
        self.assertEqual(200, resp.status_code, resp.content)

        listed = self.client.get(EVAC_TARGETS, **head)
        self.assertEqual(200, listed.status_code, listed.content)
        body = self._body(listed)
        self.assertEqual(3, body["count"],
                         "같은 테넌트 두 관리자가 나눠 등록한 3곳이 합쳐지지 않았다")
        self.assertEqual(312 + 41, body["evacuee_target_total"],
                         "대피 대상 자동 산출 — 마을+요양시설 headcount 합과 달라졌다")
        self.assertEqual(400, body["shelter_capacity_total"])
        self.assertTrue(body["shelter_covers_target"])

        # ★ 격리 — 다른 테넌트(user_b, 이 픽스처에서 admin 역할 보유)는 이
        #   테넌트의 등록을 하나도 못 본다.
        head_b = self._bearer(self.user_b)
        listed_b = self.client.get(EVAC_TARGETS, **head_b)
        self.assertEqual(200, listed_b.status_code, listed_b.content)
        body_b = self._body(listed_b)
        self.assertEqual(0, body_b["count"])
        self.assertEqual(0, body_b["evacuee_target_total"])

        _write_evidence(
            "FWS-U5-03", title="마을·대피소·요양시설 등록(대피 대상 자동 산출)",
            test_ref="tests.test_fws_u5.U5_03_EvacTargetsTest."
                    "test_registering_villages_and_shelters_auto_computes_targets",
            method="GET", path=EVAC_TARGETS, request_params={}, response=listed,
            what="같은 테넌트 두 관리자가 마을·요양시설·대피소를 나눠 등록한 뒤 "
                "GET .../admin/evac-targets 가 손으로 적는 합계 칸 없이 셋을 "
                "합쳐(count=3) headcount 를 더해 대피 대상 총원을 자동 산출한다"
                "(312+41=353, 곁표 common.models.AuditScope · 턴 AO 차선 O · "
                "P-411) — 완결조건(대피 대상 자동 산출) 실측, 다른 테넌트는 같은 "
                "GET 에서 0건을 받는다(격리)")
        _add_title_parts("FWS-U5-03", [
            {"part": "마을", "where": "kind=village", "status": "measured"},
            {"part": "대피소", "where": "kind=shelter", "status": "measured"},
            {"part": "요양시설", "where": "kind=care_facility", "status": "measured"},
            {"part": "대피 대상 자동 산출", "where": "evacuee_target_total",
             "status": "measured"},
            {"part": "테넌트 전체(같은 테넌트 여러 관리자)", "where": "GET .../admin/"
                                                          "evac-targets — count=3"
                                                          "(두 관리자가 나눠 등록)",
            "status": "구현 — 곁표(AuditScope)로 실측(다른 테넌트는 0건)"},
        ])

    def test_unknown_kind_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(EVAC_TARGETS, kind="made_up", name="x", headcount=1), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-04 — 산불 알림 규칙(등급별 수신: 진화대·산림과·지휘·산림청) · 야간
# 5분대기조 채널 — `kernels.k2_notify.rule_admin` 재사용 실측
# ═══════════════════════════════════════════════════════════════════════════
class U5_04_NotifyRulesTest(U5Fixture):
    def test_overview_lists_role_suggestions_and_night_standby_zone(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.get(NOTIFY_RULES, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertIn("severities", body)
        codes = {r["role_code"] for r in body["role_suggestions"]}
        self.assertEqual(
            {"fws_response_team", "fws_forestry_dept", "fws_command", "fws_kfs_liaison"},
            codes)
        self.assertEqual("fws_night_standby", body["night_standby_zone"])
        _write_evidence(
            "FWS-U5-04",
            title="산불 알림 규칙(등급별 수신: 진화대·산림과·지휘·산림청) · 야간 "
                 "5분대기조 채널",
            test_ref="tests.test_fws_u5.U5_04_NotifyRulesTest."
                    "test_overview_lists_role_suggestions_and_night_standby_zone",
            method="GET", path=NOTIFY_RULES, request_params={}, response=resp,
            what="GET .../admin/notify-rules 가 K2 rule_admin.notify_rule_overview 를 "
                "그대로 재사용하며 진화대·산림과·지휘·산림청 네 역할 제안과 야간 "
                "5분대기조 구역 이름을 함께 낸다")
        _add_title_parts("FWS-U5-04", [
            {"part": "등급별 수신", "where": "severities/rules", "status": "measured"},
            {"part": "진화대", "where": "role_suggestions[fws_response_team]",
             "status": "measured"},
            {"part": "산림과", "where": "role_suggestions[fws_forestry_dept]",
             "status": "measured"},
            {"part": "지휘", "where": "role_suggestions[fws_command]", "status": "measured"},
            {"part": "산림청", "where": "role_suggestions[fws_kfs_liaison]",
             "status": "measured"},
            {"part": "야간 5분대기조 채널", "where": "night_standby_zone",
             "status": "measured"},
        ])

    def test_save_a_night_standby_rule_then_it_appears_in_overview(self) -> None:
        head = self._bearer(self.user_a)
        params = {"severity": "warning", "role_code": "fws_response_team",
                 "channels": "email", "zone": "fws_night_standby"}
        resp = self.client.post(_qs(NOTIFY_RULES, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("fws_night_standby", body["zone"])

        overview = self.client.get(NOTIFY_RULES, **head)
        rule_zones = {r["role_code"]: r["zone"] for r in self._body(overview)["rules"]}
        self.assertEqual("fws_night_standby", rule_zones.get("fws_response_team"),
                         "저장한 zone=fws_night_standby 규칙이 재조회에서 사라졌다 "
                         "— 야간 5분대기조 채널 분리가 깨졌다")

    def test_test_send_never_reaches_a_real_channel(self) -> None:
        head = self._bearer(self.user_a)
        params = {"severity": "warning", "role_code": "fws_response_team",
                 "channels": "email"}
        self.client.post(_qs(NOTIFY_RULES, **params), **head)
        resp = self.client.post(_qs(NOTIFY_RULES_TEST, severity="warning"), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertFalse(body["reaches_people"])
