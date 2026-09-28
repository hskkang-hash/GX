# -*- coding: utf-8 -*-
"""P-376 「반쪽은 닫힘이 아니다」 — DSM-U2-04·DSM-U5-02 반쪽 메움 시험. 차선 O · 턴 AM.

캐시 처리: 우회/비움/해당 없음 — `test_p356_u2_spec_promotions.py` 와 같은 이유로
매 요청 전 `cache.clear()` 를 부른다(`common/idempotency.py` 가 Redis 에 성공 응답을
잠깐 기억하는데, 창을 안 비우면 같은 시험 파일 안 두 번째 요청이 새 자원 대신
옛 응답을 받는다).

이 파일이 잰다 — 둘
--------------------
  (a) DSM-U2-04 「강우량」 반쪽 — `kernels.k5_trust.thresholds.THRESHOLDS` 에
      `rainfall.baseline` 키를 등록한 것이 **기존 엔드포인트를 코드 변경 0으로**
      그대로 받는가(`waterlevel.baseline` 과 정확히 같은 모양) · 값을 아직 안
      심은 지점은 여전히 `ThresholdNotSet`(D-280 — 지어낸 기본값이 없다).
  (b) DSM-U5-02 앞 갈래 「사람별 카메라·기능 권한」 — 새 문
      `GET /api/dsm/access-log/permissions`(`api_u5_perm.py`) 이 실제로 사람별
      카메라 목록·기능(위젯) 권한을 내는가 · 문지기가 접속기록과 같은가(시스템
      관리자만 200, 팀장은 403) · 남의 테넌트 사람·카메라가 안 섞이는가.

무엇을 다시 묻지 않나
---------------------
`waterlevel.baseline` 자체의 판정(좁은 것이 이기는가 · 계약 고정)은
`test_k5_threshold_table.py` 가 이미 잰다 — 여기서는 **새 키 하나가 같은 판정
경로를 코드 수정 없이 타는가**만 묻는다. `access-log`(뒤 갈래)의 채널·CSV 는
`test_p356_u4_spec_promotions.py` 가 이미 잰다 — 여기서는 **앞 갈래(권한 매트릭스)
가 실제로 서는가**만 묻는다.
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

OBSERVE = "/api/dsm/thresholds/observe"
PERMISSIONS = "/api/dsm/access-log/permissions"


def _decide_url(observation_id: int) -> str:
    return f"/api/dsm/thresholds/observe/{observation_id}/decide"


def _repo_root() -> Path:
    """`test_p356_u2_spec_promotions.py::_repo_root` 와 같은 계산 — 같은 디렉터리에
    쓰는 시험 파일들이 다른 길을 걷지 않는다(그 파일 머리말의 실측 경고 그대로)."""
    return Path(__file__).resolve().parents[2]


#: P-376 — 증거 파일이 사는 자리. **손으로 만들지 않는다** — 아래 시험이 실제로
#: 때린 응답으로 채운다. `DSM-U2-04.json`·`DSM-U5-02.json`(N1 소유, P-356 증거)와
#: 겹치지 않게 `P376_` 접두어를 쓴다.
EVIDENCE_DIR = _repo_root() / "docs" / "agent" / "evidence" / "SPEC"


def _dump(spec_id: str, *, test: str, method: str, path: str,
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
    #: `docs/agent/evidence/**` 쓰기는 시험 중 기본 차단(P-87 ④) — 여기는 일부러
    #: 쓰는 자리이므로 이름을 대고 연다(`test_p356_u2_spec_promotions.py` 와 같은 판단).
    with allow_evidence_writes(
            "P-376 반쪽 메움 실측 증거 — pytest 가 방금 두드린 HTTP 왕복을 그대로 "
            "적는다(손으로 옮기지 않는다)"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / f"{spec_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8")


class P376Fixture(DsmFixture):
    """역할 셋 — 팀장(A), 시스템관리자(A·B, 역할 코드 공유 · `is_tenant_admin`
    이 요청자 자신의 소속으로 가른다, `test_p356_u4_spec_promotions.py::U4Fixture`
    와 같은 판단)."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        Role = apps.get_model("role", "Role")

        cls.manager_a = cls._user(
            "p376_manager_a", cls.group_a, cls._own(cls._role("dsm_p376_mgr_a"), cls.group_a))

        admin_role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
        cls.sysop_a = cls._user("p376_sysop_a", cls.group_a, admin_role)
        cls.sysop_b = cls._user("p376_sysop_b", cls.group_b, admin_role)

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


# ═══════════════════════════════════════════════════════════════════════════
# (a) DSM-U2-04 「강우량」 반쪽
# ═══════════════════════════════════════════════════════════════════════════
class RainfallThresholdKeyTest(P376Fixture):
    def test_rainfall_key_is_defined_with_no_invented_default(self) -> None:
        """★ D-280 — `rainfall.baseline` 도 `waterlevel.baseline` 과 같은 모양이다:
        정의는 있고 기본값은 없다. 지어낸 숫자가 없다는 것이 이 표의 요점이다."""
        from kernels.k5_trust.thresholds import THRESHOLDS

        self.assertIn("rainfall.baseline", THRESHOLDS,
                      "annex 원문이 함께 부르는 「강우량」 키가 표 ①에 없습니다.")
        spec = THRESHOLDS["rainfall.baseline"]
        self.assertIsNone(spec.default, "지어낸 기본값이 있습니다 — D-280 위반.")
        self.assertTrue(spec.clause.strip(), "출처 절이 비어 있습니다.")
        self.assertTrue(spec.why.strip())

    def test_unset_rainfall_point_still_stops_not_defaults(self) -> None:
        """기준선을 아직 안 심은 지점은 **여전히 멈춘다** — 0 으로 새지 않는다."""
        from kernels.k5_trust import ThresholdNotSet, resolve_threshold

        with self.assertRaises(ThresholdNotSet):
            resolve_threshold("rainfall.baseline", scope=self.scope_a,
                              camera_id=self.stream_a.pk)

    def test_observe_decide_takes_rainfall_key_with_zero_code_changes(self) -> None:
        """★ 요점 — `ThresholdObserveIn.key` 는 문자열을 그대로 받는다. 값 판정은
        `resolve_threshold` 하나이므로 **새 키를 표에 올리는 것만으로** 이 문이
        같은 도달·결정 감사 모양을 낸다(`api_u24.py`·`threshold_alert_service.py`
        둘 다 이 시험이 코드를 고치지 않았다)."""
        from kernels.k5_trust import set_threshold

        set_threshold(scope=self.scope_a, key="rainfall.baseline", value=50,
                     reason="P-376 반쪽 메움 시험 — 지점 강우량 통제 기준",
                     scope_level="camera", scope_ref=self.stream_a.pk)

        cache.clear()
        obs_req = {"camera_id": self.stream_a.pk, "key": "rainfall.baseline",
                  "value": 62}
        observed = self.client.post(OBSERVE, obs_req, content_type="application/json",
                                    **_bearer(self.manager_a))
        self.assertEqual(200, observed.status_code, observed.content[:300])
        obs_body = observed.json()
        self.assertTrue(obs_body["reached"])
        self.assertEqual("rainfall.baseline", obs_body["key"])
        observation_id = obs_body["observation_id"]

        cache.clear()
        dec_req = {"decision": "통제 실시"}
        decided = self.client.post(_decide_url(observation_id), dec_req,
                                   content_type="application/json",
                                   **_bearer(self.manager_a))
        self.assertEqual(200, decided.status_code, decided.content[:300])
        dec_body = decided.json()
        self.assertEqual("rainfall.baseline", dec_body["key"])

        _dump(
            "P376_DSM-U2-04-rainfall",
            test="tests.test_p376_half_clauses.RainfallThresholdKeyTest"
                ".test_observe_decide_takes_rainfall_key_with_zero_code_changes",
            method="POST", path=_decide_url(observation_id),
            req_body={"observe": obs_req, "decide": dec_req},
            status=decided.status_code,
            resp_body={"observe": obs_body, "decide": dec_body},
            what="강우량 관측값(62mm)이 기준(50mm)에 닿아 도달 카드가 섰고(observe), "
                "그 뒤 결정을 남겨(decide) 도달 시각·결정 시각 둘 다 감사에 남았다 — "
                "`waterlevel.baseline` 때와 똑같은 엔드포인트·똑같은 코드, 표에 키 "
                "하나만 늘었다.")

    def test_a_point_with_no_rainfall_baseline_still_400s(self) -> None:
        """기준선 미설정 지점을 관측하면 **400**(카드가 안 선다) — 0을 기준으로
        삼지 않는다는 것이 HTTP 층에서도 지켜진다."""
        cache.clear()
        resp = self.client.post(
            OBSERVE, {"camera_id": self.stream_b.pk, "key": "rainfall.baseline",
                     "value": 5},
            content_type="application/json", **_bearer(self.sysop_b))
        self.assertEqual(400, resp.status_code, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# (b) DSM-U5-02 앞 갈래 — 사람별 카메라·기능 권한
# ═══════════════════════════════════════════════════════════════════════════
class AccessPermissionMatrixTest(P376Fixture):
    def test_manager_is_denied_same_as_access_log(self) -> None:
        """★ 문지기가 접속기록과 같다 — 팀장은 403(시스템관리자만 통과)."""
        cache.clear()
        resp = self.client.get(PERMISSIONS, **_bearer(self.manager_a))
        self.assertEqual(403, resp.status_code, resp.content[:300])

    def test_sysop_sees_person_camera_and_feature_permissions(self) -> None:
        """시스템관리자는 자기 테넌트의 사람마다 카메라 목록 + 기능(위젯) 권한을
        본다 — **둘 다 실측**(카메라 이름·기능 키 이름까지)."""
        cache.clear()
        resp = self.client.get(PERMISSIONS, **_bearer(self.sysop_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()

        by_id = {row["person_id"]: row for row in body["items"]}
        self.assertIn(self.manager_a.pk, by_id, "팀장 A 가 매트릭스에 없습니다.")
        self.assertIn(self.sysop_a.pk, by_id, "시스템관리자 자신도 매트릭스에 있어야 합니다.")

        manager_row = by_id[self.manager_a.pk]
        self.assertEqual([{"camera_id": self.stream_a.pk, "name": self.stream_a.name}],
                         manager_row["cameras"],
                         "팀장 A 의 카메라 칸이 A 그룹 카메라(stream_a)가 아닙니다.")
        self.assertIn("threshold", manager_row["features"],
                      "기능 권한 칸에 위젯 이름(threshold 등)이 없습니다.")
        self.assertEqual(8, len(manager_row["features"]),
                         "DA-03 §3-4 의 설정 위젯 8종이 다 안 나왔습니다.")

        # 같은 그룹의 두 사람은 카메라 칸이 같다 — 이 제품의 카메라 접근은
        # 사람별이 아니라 그룹(테넌트) 단위라는 사실을 표가 숨기지 않는다.
        sysop_row = by_id[self.sysop_a.pk]
        self.assertEqual(manager_row["cameras"], sysop_row["cameras"])

        _dump(
            "P376_DSM-U5-02-permissions",
            test="tests.test_p376_half_clauses.AccessPermissionMatrixTest"
                ".test_sysop_sees_person_camera_and_feature_permissions",
            method="GET", path=PERMISSIONS, req_body={},
            status=resp.status_code, resp_body=body,
            what="시스템관리자로 사람별 권한 매트릭스 문을 실제로 두드려, 팀장 A 의 "
                "행에 A 그룹 카메라 목록과 8개 기능 위젯의 권한 값이 실려 나오는 것을 "
                "확인했다 — annex 「사람별 카메라·기능 권한」의 앞 갈래가 실제로 선다.")

    def test_other_tenants_people_and_cameras_do_not_leak(self) -> None:
        """★ 격리 — B 테넌트 시스템관리자가 A 테넌트 사람·카메라를 볼 수 없다."""
        cache.clear()
        resp = self.client.get(PERMISSIONS, **_bearer(self.sysop_b))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()

        ids = {row["person_id"] for row in body["items"]}
        self.assertNotIn(self.manager_a.pk, ids,
                         "B 테넌트 관리자가 A 테넌트 팀장을 봅니다 — 격리 실패.")
        self.assertNotIn(self.sysop_a.pk, ids)
        for row in body["items"]:
            camera_ids = {c["camera_id"] for c in row["cameras"]}
            self.assertNotIn(self.stream_a.pk, camera_ids,
                             "B 테넌트 사람의 카메라 칸에 A 그룹 카메라가 섞였습니다.")

    def test_access_permission_read_is_itself_audited(self) -> None:
        """조회 자체가 감사에 남는다 — 접속기록 전용 문과 같은 규약(GX-LAW-09 §5-2).

        ★ `common.audit_writer.read` 를 쓴다(`threshold_alert_service.py::decide`
        와 같은 조회 면) — `apps.dsm.audit` 가 아니다: 이 채널은 접속기록과 같은
        이유로 **일반 감사 화면에 일부러 안 뜬다**(`access_permission_service.py`
        의 `LOGGER_NAME`), 그 화면의 질의 함수(`apps.dsm.audit.read_page`)를
        부르면 애초에 안 보이는 채널을 보는 셈이라 다른 것을 재게 된다."""
        from common import audit_writer

        cache.clear()
        resp = self.client.get(PERMISSIONS, **_bearer(self.sysop_a))
        self.assertEqual(200, resp.status_code)

        rows = audit_writer.read(logger_name="guardianx.u5.access_permission_read")
        self.assertTrue(rows, "권한 매트릭스 조회 자체가 감사에 안 남았습니다.")
        self.assertEqual("access_permission:read", rows[0].action)
