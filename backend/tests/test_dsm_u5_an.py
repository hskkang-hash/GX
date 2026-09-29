# -*- coding: utf-8 -*-
"""DSM App(L4) — U5(시스템 관리자) 별표 절 둘의 **HTTP 실측**과
`docs/agent/evidence/SPEC/*.json` 생성 (WO-GX-20260929-17 §5 P-356 · 턴 AN 차선 N4).

닫는 절: DSM-U5-01(운영·관리 방침 항목 관리) · DSM-U5-03(연계 설정 — 스마트시티
통합플랫폼·112·119·NDMS). DSM-U5-04(임계값 소스)는 이 파일이 닫지 않는다(차선
범위 밖) — `docs/agent/evidence/SPEC/N4_promotions_an.md` 의 「무엇이 없는가」를
본다.

★ 새 `/api/dsm/` 라우트 넷(`GET/POST /u5an/privacy-policy` ·
  `GET/POST /u5an/integrations` · `POST /u5an/integrations/test`)은
  `tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE` 에 아직 없다 — 그 파일은
  조율자 몫이라 이 파일이 고치지 않는다(최종 보고에 정확한 (METHOD, path) 를
  옮겨 적는다).

`tests.test_fws_app.FwsHttpTest` 를 그대로 쓴다 — 이름은 FWS 이지만 실제로는
`DsmFixture` + 일반 HTTP 클라이언트/베어러 도우미일 뿐이라 DSM 라우트에도 똑같이
쓴다(같은 표를 두 벌로 만들지 않는다, D-212). 증거 쓰기(`_write_evidence`)도 그
파일의 것을 재사용한다 — FWS 전용이 아니라 "요청·응답을 그대로 적는" 일반 함수다.
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

PRIVACY_POLICY = "/api/dsm/u5an/privacy-policy"
INTEGRATIONS = "/api/dsm/u5an/integrations"
INTEGRATIONS_TEST = "/api/dsm/u5an/integrations/test"


def _add_title_parts(clause_id: str, parts: list[dict]) -> None:
    with allow_evidence_writes(
            "P-356 ② title_parts — 제목이 부르는 부분과 실측 상태를 표로 남긴다"):
        path = EVIDENCE_DIR / f"{clause_id}.json"
        body = json.loads(path.read_text(encoding="utf-8"))
        body["title_parts"] = parts
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")


class U5AnFixture(FwsHttpTest):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        Role = apps.get_model("role", "Role")
        admin_role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
        cls.user_a.roles.add(admin_role)
        cls.user_b.roles.add(admin_role)

    def setUp(self) -> None:
        super().setUp()
        cache.clear()


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U5-01 — 운영·관리 방침 항목 관리
# ═══════════════════════════════════════════════════════════════════════════
class U5_01_PrivacyPolicyTest(U5AnFixture):
    def test_save_reread_and_retention_matches_destruction_policy(self) -> None:
        from django.test import override_settings

        head = self._bearer(self.user_a)
        params = {
            "purpose": "산불 감시 및 방범", "install_locations": "정문·주차장",
            "filming_scope": "출입로 전방 30m", "responsible_person": "정보통신과장",
            "access_grantees": "정보통신과 담당자 2명", "filming_hours": "24시간",
            "viewing_procedure": "열람청구서 접수 후 3일 이내 처리",
        }
        with override_settings(VIDEO_RETENTION_DAYS=30):
            resp = self.client.post(_qs(PRIVACY_POLICY, **params), **head)
            self.assertEqual(200, resp.status_code, resp.content)
            body = self._body(resp)
            self.assertEqual("정보통신과장", body["responsible_person"])
            self.assertEqual(1, body["installed_camera_count"],
                             "실측 카메라 대수(테넌트 A 는 1대)와 다르다")
            self.assertEqual(30, body["retention_days"],
                             "완결조건(보관 기간 = 파기 정책 값)이 깨졌다 — "
                             "apps.dsm.retention.retention_days() 와 달라졌다")
            self.assertIn("정보통신과장", body["document_text"])

            reread = self.client.get(PRIVACY_POLICY, **head)
        self.assertEqual(200, reread.status_code, reread.content)
        self.assertEqual(body, self._body(reread))

        _write_evidence(
            "DSM-U5-01", title="운영·관리 방침 항목 관리",
            test_ref="tests.test_dsm_u5_an.U5_01_PrivacyPolicyTest."
                    "test_save_reread_and_retention_matches_destruction_policy",
            method="POST", path=_qs(PRIVACY_POLICY, **params), request_params=params,
            response=resp,
            what="POST .../u5an/privacy-policy 로 저장한 항목이 재조회에 그대로 "
                "보이고, retention_days 는 손으로 적는 칸이 아니라 apps.dsm.retention."
                "retention_days()(파기가 실제로 보는 값)를 그대로 읽는다 — 완결조건 "
                "실측(VIDEO_RETENTION_DAYS=30 선언 시 방침의 보관 기간도 30)")
        _add_title_parts("DSM-U5-01", [
            {"part": "설치 목적", "where": "purpose", "status": "measured"},
            {"part": "대수", "where": "installed_camera_count", "status": "measured"},
            {"part": "위치", "where": "install_locations", "status": "measured"},
            {"part": "촬영 범위", "where": "filming_scope", "status": "measured"},
            {"part": "관리책임자", "where": "responsible_person", "status": "measured"},
            {"part": "접근권한자", "where": "access_grantees", "status": "measured"},
            {"part": "촬영 시간", "where": "filming_hours", "status": "measured"},
            {"part": "보관 기간", "where": "retention_days", "status": "measured"},
            {"part": "열람 절차", "where": "viewing_procedure", "status": "measured"},
            {"part": "방침 문서 자동 생성", "where": "document_text", "status": "measured"},
        ])

    def test_undeclared_retention_is_honestly_none(self) -> None:
        from django.test import override_settings

        head = self._bearer(self.user_a)
        with override_settings(VIDEO_RETENTION_DAYS=None):
            resp = self.client.get(PRIVACY_POLICY, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIsNone(self._body(resp)["retention_days"],
                         "미선언인데 수를 지어냈다(D-284 위반)")

    def test_non_admin_is_403(self) -> None:
        CoreUser = apps.get_model("user", "CoreUser")
        plain = CoreUser.objects.create_user(
            username="u5an_plain", password="test-only-not-a-secret", is_active=True,
            email="u5an_plain@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: plain, "group": self.group_a})
        head_plain = self._bearer(plain)
        resp = self.client.get(PRIVACY_POLICY, **head_plain)
        self.assertEqual(403, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U5-03 — 연계 설정(스마트시티 통합플랫폼·112·119·NDMS)
# ═══════════════════════════════════════════════════════════════════════════
class U5_03_IntegrationsTest(U5AnFixture):
    def test_save_test_and_status_word_progression(self) -> None:
        head = self._bearer(self.user_a)

        empty = self.client.get(INTEGRATIONS, **head)
        self.assertEqual(200, empty.status_code, empty.content)
        rows = {r["service"]: r for r in self._body(empty)["integrations"]}
        self.assertEqual({"smart_city", "police_112", "fire_119", "ndms"}, set(rows))
        self.assertEqual("끊김", rows["ndms"]["status"], "미설정 상태가 '끊김'이 아니다")

        params = {"service": "ndms", "endpoint_name": "ndms-prod-gateway",
                 "outbound_api_key_ref": "NDMS_OUTBOUND_KEY_REF"}
        saved = self.client.post(_qs(INTEGRATIONS, **params), **head)
        self.assertEqual(200, saved.status_code, saved.content)
        saved_body = self._body(saved)
        self.assertEqual("ndms-prod-gateway", saved_body["endpoint_name"])
        self.assertEqual("NDMS_OUTBOUND_KEY_REF", saved_body["outbound_api_key_ref"],
                         "저장한 것은 참조 이름이지 값이 아니다 — 응답도 이름만 낸다")
        self.assertEqual("대기", saved_body["status"], "시험 전인데 '정상'을 냈다")

        tested = self.client.post(_qs(INTEGRATIONS_TEST, service="ndms"), **head)
        self.assertEqual(200, tested.status_code, tested.content)
        tested_body = self._body(tested)
        self.assertEqual("정상", tested_body["status"])
        self.assertIsNotNone(tested_body["tested_at"])

        _write_evidence(
            "DSM-U5-03",
            title="연계 설정 — 스마트시티 통합플랫폼·112·119·NDMS",
            test_ref="tests.test_dsm_u5_an.U5_03_IntegrationsTest."
                    "test_save_test_and_status_word_progression",
            method="POST", path=_qs(INTEGRATIONS_TEST, service="ndms"),
            request_params={"service": "ndms"}, response=tested,
            what="네 연계서비스(스마트시티 통합플랫폼·112·119·NDMS)가 목록에 있고, "
                "끝점 이름·자격 참조명(값 아님)을 저장하면 상태가 '대기'였다가 "
                "연결 시험 뒤 '정상'이 된다 — 시험은 설정 완결성만 보고 실제로는 "
                "밖으로 나가지 않는다(WO-17 경계)")
        _add_title_parts("DSM-U5-03", [
            {"part": "스마트시티 통합플랫폼", "where": "service=smart_city",
             "status": "measured"},
            {"part": "112", "where": "service=police_112", "status": "measured"},
            {"part": "119", "where": "service=fire_119", "status": "measured"},
            {"part": "NDMS", "where": "service=ndms", "status": "measured"},
            {"part": "엔드포인트", "where": "endpoint_name", "status": "measured"},
            {"part": "자격 참조명", "where": "outbound_api_key_ref", "status": "measured"},
            {"part": "연결 시험", "where": "POST /u5an/integrations/test",
             "status": "measured"},
            {"part": "상태 한 단어", "where": "status", "status": "measured"},
        ])

    def test_unknown_service_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(INTEGRATIONS, service="made_up"), **head)
        self.assertEqual(422, resp.status_code)

    def test_other_tenant_does_not_see_my_config(self) -> None:
        head_a = self._bearer(self.user_a)
        self.client.post(
            _qs(INTEGRATIONS, service="ndms", endpoint_name="a-only",
               outbound_api_key_ref="A_ONLY_REF"),
            **head_a)
        head_b = self._bearer(self.user_b)
        resp = self.client.get(INTEGRATIONS, **head_b)
        rows = {r["service"]: r for r in self._body(resp)["integrations"]}
        self.assertEqual("", rows["ndms"]["endpoint_name"],
                         "테넌트 B 가 테넌트 A 의 연계 설정을 봤다")
