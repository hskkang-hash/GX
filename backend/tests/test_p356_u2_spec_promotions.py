# -*- coding: utf-8 -*-
"""P-356/P-358 · WO-GX-20260925-15 §5 — **DSM-U2-03·U2-04·U2-05 승격 시험** · 차선 N1 · 턴 AK.

캐시 처리: 우회/비움/해당 없음 — Django 테스트 클라이언트가 매 시험 새 프로세스로
`cache.clear()` 를 부른다(`test_u24_reports.py::ReportFixture.setUp` 과 같은 이유 —
`common/idempotency.py` 가 Redis 캐시에 성공 응답을 잠깐 기억하는데, 창을 안 비우면
같은 시험 파일 안에서 두 번째 요청이 **새 자원 대신 옛 응답**을 받는다).

이 파일이 잰다
--------------
  DSM-U2-03 `POST|GET /api/dsm/situation-meetings` — 결정 필수 400 · 감사 한 줄 ·
    남의 테넌트 회의는 안 보인다.
  DSM-U2-04 `POST /api/dsm/thresholds/observe` · `.../decide` — 기준 미만은
    카드가 안 선다(`reached=False`) · 기준 이상이면 도달 감사 + 결정 감사 둘 다 ·
    남의 테넌트 카메라는 404(존재를 안 알린다) · 남의 도달 기록을 결정할 수 없다.
  DSM-U2-05 `POST /api/dsm/handover/{id}/ack` — 확인 감사 1 · `latest()` 의
    `acknowledged` 칸이 확인 전후로 바뀐다 · 남의 인계 메모는 404.

무엇을 다시 묻지 않나
---------------------
임계값 판정 자체(좁은 것이 이기는가 · 계약 고정)는 `test_k5_threshold_table.py` 가
잰다 — 여기서는 **App 면이 그 판정을 잃지 않고 감사로 옮기는가**만 묻는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.cache import cache
from django.utils import timezone

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

MEETINGS = "/api/dsm/situation-meetings"
OBSERVE = "/api/dsm/thresholds/observe"


def _repo_root() -> Path:
    """`parents[2]` 로 기어오른다 — 호스트에서 돌리면 저장소 뿌리, gx-shell 안에서는
    `/app`(backend)의 조부모인 컨테이너 루트("/")다. **컨테이너 루트가 맞는 이유**:
    거기 `docs/` 가 **`/docs` 로 바로 물려 있다**(`test_fws_app.py::EVIDENCE_DIR` 와
    같은 계산이고, 그 파일이 쓴 `FWS-F1-*.json` 이 실제로 호스트에 나타나는 것으로
    확인했다).

    ⚠ **첫 판은 `/repo` 를 먼저 확인해 썼다가 틀렸다** [실측 2026-09-27]:
      `/repo` 도 `is_dir()` 로는 있어 보였지만(별도 마운트), 거기에 쓴 증거 파일이
      **호스트에 나타나지 않았다** — 시험은 통과했는데 파일이 없는, 가장 나쁜
      종류의 초록이었다(D-301 계열). `test_fws_app.py` 가 이미 쓰고 있던 `parents[2]`
      계산으로 맞춰 그 함정을 없앤다 — **같은 디렉터리에 쓰는 두 시험 파일이 다른
      길을 걷지 않는다.**
    """
    return Path(__file__).resolve().parents[2]


#: P-356 ② — 증거 파일이 사는 자리. **손으로 만들지 않는다** — 아래
#: `EvidenceExportTest` 가 실제로 때린 응답으로 채운다.
EVIDENCE_DIR = _repo_root() / "docs" / "agent" / "evidence" / "SPEC"


def _decide_url(observation_id: int) -> str:
    return f"/api/dsm/thresholds/observe/{observation_id}/decide"


def _ack_url(handover_id: int) -> str:
    return f"/api/dsm/handover/{handover_id}/ack"


class U2Fixture(DsmFixture):
    """역할 둘 — 상황실장(팀장 A) · 다른 테넌트 팀장(B)."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        cls.manager_a = cls._user(
            "u2ak_manager_a", cls.group_a, cls._own(cls._role("dsm_u2_a"), cls.group_a))
        cls.manager_b = cls._user(
            "u2ak_manager_b", cls.group_b, cls._own(cls._role("dsm_u2_b"), cls.group_b))

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
# DSM-U2-03 상황판단회의 기록
# ═══════════════════════════════════════════════════════════════════════════
class SituationMeetingTest(U2Fixture):
    def test_decision_is_required(self) -> None:
        resp = self.client.post(
            MEETINGS, {"attendees": "팀장·U4", "basis": "수위 182cm"},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_record_then_list_round_trips(self) -> None:
        resp = self.client.post(
            MEETINGS,
            {"occurred_at": "2026-09-25T03:40:00+09:00",
             "attendees": "상황실장·팀장·U4",
             "decision": "통제 실시 · 비상 2단계 발령",
             "basis": "수위 182cm · 강우 41mm"},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertIn("meeting_id", body)

        listing = self.client.get(MEETINGS, **_bearer(self.manager_a))
        self.assertEqual(200, listing.status_code, listing.content[:300])
        rows = listing.json()
        self.assertEqual(1, len(rows))
        self.assertIn("통제 실시 · 비상 2단계 발령", rows[0]["text"])
        self.assertIn("182cm", rows[0]["text"])

    def test_other_tenant_meeting_is_not_visible(self) -> None:
        self.client.post(
            MEETINGS, {"decision": "B 테넌트만의 결정"},
            content_type="application/json", **_bearer(self.manager_b))

        cache.clear()
        mine = self.client.get(MEETINGS, **_bearer(self.manager_a))
        self.assertEqual(200, mine.status_code)
        self.assertEqual([], mine.json())


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U2-04 임계값 도달 알림
# ═══════════════════════════════════════════════════════════════════════════
class ThresholdAlertTest(U2Fixture):
    def _set_baseline(self, *, stream, value) -> None:
        from kernels.k5_trust import set_threshold

        set_threshold(scope=self.scope_a, key="waterlevel.baseline", value=value,
                     reason="시험 기준선", scope_level="camera", scope_ref=stream.pk)

    def test_below_threshold_does_not_raise_a_card(self) -> None:
        self._set_baseline(stream=self.stream_a, value=180)
        resp = self.client.post(
            OBSERVE, {"camera_id": self.stream_a.pk, "key": "waterlevel.baseline",
                     "value": 120},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertFalse(body["reached"])
        self.assertIsNone(body["observation_id"])

    def test_reach_then_decide_leaves_two_audit_rows(self) -> None:
        self._set_baseline(stream=self.stream_a, value=180)
        cache.clear()
        observed = self.client.post(
            OBSERVE, {"camera_id": self.stream_a.pk, "key": "waterlevel.baseline",
                     "value": 182},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(200, observed.status_code, observed.content[:300])
        obs_body = observed.json()
        self.assertTrue(obs_body["reached"])
        observation_id = obs_body["observation_id"]
        self.assertIsNotNone(observation_id)

        from apps.dsm import threshold_alert_service

        before = threshold_alert_service.audit_writer.read(
            logger_name=threshold_alert_service.LOGGER_NAME, limit=50)
        self.assertTrue(any(e.audit_id == observation_id for e in before))

        cache.clear()
        decided = self.client.post(
            _decide_url(observation_id), {"decision": "통제 실시"},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(200, decided.status_code, decided.content[:300])
        dec_body = decided.json()
        self.assertEqual(observation_id, dec_body["observation_id"])

        after = threshold_alert_service.audit_writer.read(
            logger_name=threshold_alert_service.LOGGER_NAME, limit=50)
        #: ★ 완결 조건 — 도달 시각·결정 시각 **둘 다** 감사에 남는다(한 행을 덮어쓰지 않는다).
        self.assertGreaterEqual(len(after), len(before) + 1)
        self.assertTrue(any(
            e.action == f"threshold_decision:{observation_id}" for e in after))

    def test_no_baseline_set_is_400_not_a_made_up_default(self) -> None:
        resp = self.client.post(
            OBSERVE, {"camera_id": self.stream_a.pk, "key": "waterlevel.baseline",
                     "value": 500},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_other_tenant_camera_is_404(self) -> None:
        self._set_baseline(stream=self.stream_a, value=180)
        resp = self.client.post(
            OBSERVE, {"camera_id": self.stream_b.pk, "key": "waterlevel.baseline",
                     "value": 999},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(404, resp.status_code, resp.content[:300])

    def test_cannot_decide_someone_elses_observation(self) -> None:
        from kernels.k5_trust import set_threshold

        set_threshold(scope=self.scope_b, key="waterlevel.baseline", value=180,
                     reason="B 시험 기준선", scope_level="camera",
                     scope_ref=self.stream_b.pk)
        cache.clear()
        observed = self.client.post(
            OBSERVE, {"camera_id": self.stream_b.pk, "key": "waterlevel.baseline",
                     "value": 200},
            content_type="application/json", **_bearer(self.manager_b))
        self.assertEqual(200, observed.status_code, observed.content[:300])
        observation_id = observed.json()["observation_id"]

        cache.clear()
        resp = self.client.post(
            _decide_url(observation_id), {"decision": "남의 사건을 가로챈다"},
            content_type="application/json", **_bearer(self.manager_a))
        self.assertEqual(404, resp.status_code, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U2-05 교대 인수인계 합동 확인
# ═══════════════════════════════════════════════════════════════════════════
class HandoverAckTest(U2Fixture):
    def _save_handover(self, *, user):
        resp = self.client.post(
            "/api/dsm/handover/draft", {"hours": 24, "note": "특이사항 없음"},
            content_type="application/json", **_bearer(user))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        return resp.json()["id"]

    def test_ack_flips_the_home_card_flag(self) -> None:
        handover_id = self._save_handover(user=self.manager_a)

        cache.clear()
        before = self.client.get(
            "/api/dsm/handover/latest", **_bearer(self.manager_a)).json()
        self.assertFalse(before["acknowledged"])

        cache.clear()
        ack = self.client.post(_ack_url(handover_id), **_bearer(self.manager_a))
        self.assertEqual(200, ack.status_code, ack.content[:300])
        self.assertTrue(ack.json()["acknowledged"])

        cache.clear()
        after = self.client.get(
            "/api/dsm/handover/latest", **_bearer(self.manager_a)).json()
        self.assertTrue(after["acknowledged"])

    def test_other_tenant_handover_is_404(self) -> None:
        handover_id = self._save_handover(user=self.manager_b)

        cache.clear()
        resp = self.client.post(_ack_url(handover_id), **_bearer(self.manager_a))
        self.assertEqual(404, resp.status_code, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# P-356 ② 증거 — `docs/agent/evidence/SPEC/<id>.json` 셋. **손으로 안 적는다** —
# 이 시험이 실제로 때린 응답을 그대로 담는다(Django TestCase · test client · test DB).
# `scripts/verify_spec_dsm.py` 가 이 파일들의 실재·모양을 잰다.
#
# ★ 스키마는 이 턴 차선 N2 의 `verify_spec_fws.py` 짝(`test_fws_app.py`)이 이미
#   세운 것과 **같다**(`id · measured_at · measured_by · test · request · response ·
#   what`, `measured_by="django_test_client"`) — 같은 디렉터리에 쌓이는 증거가
#   서로 다른 모양이면 다음 사람이 파일마다 다른 눈으로 읽어야 한다. 두 벌은
#   반드시 어긋난다(D-212 와 같은 결의 판단).
# ═══════════════════════════════════════════════════════════════════════════
class EvidenceExportTest(U2Fixture):
    """세 절을 한 번씩 더 때려 증거 파일로 남긴다 — 위 시험들과 같은 그림이다."""

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
        #:   (`common.evidence_guard` — 시험 DB 의 수가 운영 증거로 둔갑한 사고,
        #:   P-87 ④). 이 자리는 **일부러 쓰는 자리**이므로 이름을 대고 연다
        #:   (`test_fws_app.py::_write_evidence` 와 같은 판단).
        with allow_evidence_writes(
                "P-356 ② DSM 별표 절 실측 증거 — pytest 가 방금 두드린 HTTP "
                "왕복을 그대로 적는다(손으로 옮기지 않는다)"):
            EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            out_path = EVIDENCE_DIR / f"{spec_id}.json"
            #: [턴 AO · P-407] 다른 시험(소급 표 채움)이 이 증거 위에 더한
            #: 「제목이 부르는 것 ↔ 있는 것」 표(`title_parts`)는 **보존한다** —
            #: 이 시험은 HTTP 왕복만 다시 적는다. 안 그러면 전량 시험 순서에 따라
            #: 표가 지워져 O 게이트가 옛 승격으로 오판한다(`test_fws_app.py::
            #: _write_evidence` 와 같은 판단).
            if out_path.is_file():
                try:
                    prev = json.loads(out_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    prev = {}
                for keep in ("title_parts", "title_parts_note"):
                    if keep in prev:
                        payload[keep] = prev[keep]
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8")

    def test_dump_dsm_u2_03_evidence(self) -> None:
        body = {"occurred_at": "2026-09-27T03:40:00+09:00",
               "attendees": "상황실장·팀장·U4",
               "decision": "통제 실시 · 비상 2단계 발령",
               "basis": "수위 182cm · 강우 41mm"}
        resp = self.client.post(MEETINGS, body, content_type="application/json",
                                **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self._dump(
            "DSM-U2-03",
            test="tests.test_p356_u2_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u2_03_evidence",
            method="POST", path=MEETINGS, req_body=body,
            status=resp.status_code, resp_body=resp.json(),
            what="상황판단회의 기록 1건을 실제로 남기고 응답을 그대로 옮겼다 — "
                "손으로 지어낸 값 0.")

    def test_dump_dsm_u2_04_evidence(self) -> None:
        from kernels.k5_trust import set_threshold

        set_threshold(scope=self.scope_a, key="waterlevel.baseline", value=180,
                     reason="증거용 시험 기준선", scope_level="camera",
                     scope_ref=self.stream_a.pk)
        cache.clear()
        obs_req = {"camera_id": self.stream_a.pk, "key": "waterlevel.baseline",
                  "value": 182}
        observed = self.client.post(OBSERVE, obs_req, content_type="application/json",
                                    **_bearer(self.manager_a))
        self.assertEqual(200, observed.status_code, observed.content[:300])
        obs_body = observed.json()
        self.assertTrue(obs_body["reached"])
        observation_id = obs_body["observation_id"]

        cache.clear()
        dec_req = {"decision": "통제 실시"}
        decide_path = _decide_url(observation_id)
        decided = self.client.post(decide_path, dec_req, content_type="application/json",
                                   **_bearer(self.manager_a))
        self.assertEqual(200, decided.status_code, decided.content[:300])

        self._dump(
            "DSM-U2-04",
            test="tests.test_p356_u2_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u2_04_evidence",
            method="POST", path=decide_path,
            req_body={"observe": obs_req, "decide": dec_req},
            status=decided.status_code,
            resp_body={"observe": obs_body, "decide": decided.json()},
            what="관측값이 기준(180cm)에 닿아(182cm) 도달 카드가 섰고(observe), 그 뒤 "
                "결정을 남겨(decide) 도달 시각·결정 시각 둘 다 감사에 남았다.")

    def test_dump_dsm_u2_05_evidence(self) -> None:
        draft_req = {"hours": 24, "note": "증거용"}
        saved = self.client.post(
            "/api/dsm/handover/draft", draft_req, content_type="application/json",
            **_bearer(self.manager_a))
        self.assertEqual(200, saved.status_code, saved.content[:300])
        handover_id = saved.json()["id"]

        cache.clear()
        ack_path = _ack_url(handover_id)
        ack = self.client.post(ack_path, **_bearer(self.manager_a))
        self.assertEqual(200, ack.status_code, ack.content[:300])

        cache.clear()
        latest = self.client.get(
            "/api/dsm/handover/latest", **_bearer(self.manager_a))
        self.assertEqual(200, latest.status_code)
        self.assertTrue(latest.json()["acknowledged"])

        self._dump(
            "DSM-U2-05",
            test="tests.test_p356_u2_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u2_05_evidence",
            method="POST", path=ack_path, req_body={},
            status=ack.status_code,
            resp_body={"ack": ack.json(), "latest_after_ack": latest.json()},
            what="인계 메모를 저장하고 확인(ack)한 뒤 `latest()` 의 acknowledged 가 "
                "참으로 바뀐 것을 같은 시험 안에서 다시 읽어 확인했다.")
