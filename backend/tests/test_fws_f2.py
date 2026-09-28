# -*- coding: utf-8 -*-
"""FWS App(L4) — F2(산림재난대응단·진화대) 별표 절 10건의 **HTTP 실측**과
`docs/agent/evidence/SPEC/*.json` 생성 (WO-GX-20260925-15 §5 P-356·357·358 · 턴 AL
차선 N2).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`) 헤더를 모든 요청에 싣는다
(`test_fws_app.py` 와 같은 규약). 이 파일은 새 캐시를 만들지 않는다 — 멱등 캐시는
`setUp` 에서 `cache.clear()` 로 비운다.

이 파일이 재는 것 — P-356 승격 규칙 넷 중 ①②(③·④는 게이트·제안 문서)
------------------------------------------------------------------------
    ① 실제 구현    `self.client` 가 `/api/fws/...` 를 실제로 두드린다
    ② 실측 증거    각 시험이 요청·응답을 그대로 `docs/agent/evidence/SPEC/<id>.json`
                    에 적는다(`test_fws_app._write_evidence` 재사용 — 두 벌을
                    만들지 않는다, D-212).

F2-07·F2-15 는 **새 엔드포인트가 없다** — F1-10(`/alerts`)·F1-12(`/notify-prefs`)를
그대로 재사용한다(머리말 각 클래스 참조 · P-357 「같은 문을 두 번 열지 않는다」).
"""
from __future__ import annotations

import contextlib
from datetime import timedelta
from urllib.parse import urlencode

from django.core.cache import cache
from django.test import Client
from django.utils import timezone as dj_timezone

from tests.no_cache import NO_CACHE
from tests.test_fws_app import FwsHttpTest, _write_evidence

ALERTS = "/api/fws/alerts"
NOTIFY_PREFS = "/api/fws/notify-prefs"
STANDBY_STATUS = "/api/fws/resources/me/status"
TRAINING_MISSION = "/api/fws/training/mission"
EQUIPMENT_CHECKS = "/api/fws/equipment/checks"
EQUIPMENT_CHECKS_MINE = "/api/fws/equipment/checks/mine"
MISSIONS_MINE = "/api/fws/missions/mine"


def _qs(path: str, **params) -> str:
    live = {k: v for k, v in params.items() if v is not None}
    return f"{path}?{urlencode(live)}" if live else path


def _mission_path(event_id) -> str:
    return f"/api/fws/missions/{event_id}"


def _mission_response_path(event_id) -> str:
    return f"/api/fws/missions/{event_id}/response"


def _mission_support_path(event_id) -> str:
    return f"/api/fws/missions/{event_id}/field-reply"


def _ack_path(delivery_id) -> str:
    return f"/api/fws/alerts/{delivery_id}/ack"


class Fws2HttpTest(FwsHttpTest):
    """`FwsHttpTest`(F1 시험의 픽스처·헬퍼)를 그대로 쓴다 — 같은 표를 두 벌로 만들지
    않는다."""

    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self) -> None:
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cache.clear()


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-01 대기 상태 등록(주간·야간 5분대기조·위치)
# ═══════════════════════════════════════════════════════════════════════════
class F2_01_StandbyStatusTest(Fws2HttpTest):
    def test_set_then_read_back_standby_status(self) -> None:
        head = self._bearer(self.user_a)
        empty = self.client.get(STANDBY_STATUS, **head)
        self.assertEqual(200, empty.status_code)
        self.assertIsNone(self._body(empty)["status"])

        params = {"status": "standby_night", "lat": 36.4, "lng": 127.4}
        save = self.client.post(_qs(STANDBY_STATUS, **params), **head)
        self.assertEqual(200, save.status_code, save.content)
        self.assertEqual("standby_night", self._body(save)["status"])

        read = self.client.get(STANDBY_STATUS, **head)
        self.assertEqual(200, read.status_code)
        body = self._body(read)
        self.assertEqual("standby_night", body["status"])
        self.assertEqual({"lat": 36.4, "lng": 127.4}, body["location"])
        _write_evidence(
            "FWS-F2-01", title="대기 상태 등록(주간·야간 5분대기조·위치)",
            test_ref="tests.test_fws_f2.F2_01_StandbyStatusTest."
                    "test_set_then_read_back_standby_status",
            method="GET", path=STANDBY_STATUS, request_params={}, response=read,
            what="POST 로 등록한 대기 상태(야간)·위치가 이후 GET 재조회에 그대로 "
                "보인다 — 등록·위치 실측(자원 배치판 표시는 F3 화면 소유라 범위 밖)")

    def test_unknown_status_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(STANDBY_STATUS, status="not-a-status"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-02 임무 수신 · FWS-F2-03 이동·도착 회신(GPS) · FWS-F2-11 철수·복귀 회신
# ═══════════════════════════════════════════════════════════════════════════
class F2_02_03_11_MissionResponseTest(Fws2HttpTest):
    def test_mission_detail_dispatch_arrive_release_chain(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire",
                               when=dj_timezone.now() - timedelta(minutes=5))
        head = self._bearer(self.user_a)

        detail = self.client.get(_mission_path(event_id), **head)
        self.assertEqual(200, detail.status_code, detail.content)
        detail_body = self._body(detail)
        self.assertEqual(event_id, detail_body["mission_id"])
        self.assertEqual("occurred", detail_body["response_state"])
        _write_evidence(
            "FWS-F2-02", title="임무 수신(출동 지시)",
            test_ref="tests.test_fws_f2.F2_02_03_11_MissionResponseTest."
                    "test_mission_detail_dispatch_arrive_release_chain",
            method="GET", path=_mission_path(event_id), request_params={},
            response=detail,
            what="K1 이벤트를 '임무'로 GET — 발화점 좌표·화세·시각이 응답에 실린다"
                "(접근로·풍향·집결지·지휘자는 K1 스키마에 없어 null · missions.py "
                "머리말에 정직하게 남김)")

        dispatch_params = {"action": "dispatch"}
        dispatch = self.client.post(
            _qs(_mission_response_path(event_id), **dispatch_params), **head)
        self.assertEqual(200, dispatch.status_code, dispatch.content)
        self.assertEqual("acknowledged", self._body(dispatch)["to"])

        arrive_params = {"action": "arrived", "lat": 36.1, "lng": 127.2}
        arrive = self.client.post(
            _qs(_mission_response_path(event_id), **arrive_params), **head)
        self.assertEqual(200, arrive.status_code, arrive.content)
        arrive_body = self._body(arrive)
        self.assertEqual("in_progress", arrive_body["to"])
        self.assertIsNotNone(arrive_body["elapsed_minutes"])
        _write_evidence(
            "FWS-F2-03", title="이동·도착 회신(GPS)",
            test_ref="tests.test_fws_f2.F2_02_03_11_MissionResponseTest."
                    "test_mission_detail_dispatch_arrive_release_chain",
            method="POST", path=_qs(_mission_response_path(event_id), **arrive_params),
            request_params=arrive_params, response=arrive,
            what="출동 탭 뒤 action=arrived 회신이 대응 진행을 in_progress 로 "
                "옮기고 elapsed_minutes(30분 시계)를 함께 낸다 — 도착 시각·30분 "
                "시계 실측")

        release_params = {"action": "released", "note": "철수 완료"}
        release = self.client.post(
            _qs(_mission_response_path(event_id), **release_params), **head)
        self.assertEqual(200, release.status_code, release.content)
        release_body = self._body(release)
        # [턴 AL · 조율자 병합] 철수는 사건을 닫지 않는다 — 다른 진화대가 아직 끄고 있을 수 있다.
        self.assertEqual("in_progress", release_body["to"])
        self.assertIs(False, release_body["event_advanced"])
        self.assertIsNotNone(release_body["duration_minutes"])
        _write_evidence(
            "FWS-F2-11", title="철수·복귀 회신",
            test_ref="tests.test_fws_f2.F2_02_03_11_MissionResponseTest."
                    "test_mission_detail_dispatch_arrive_release_chain",
            method="POST", path=_qs(_mission_response_path(event_id), **release_params),
            request_params=release_params, response=release,
            what="action=released 회신이 이 진화대의 철수를 기록하고 도착~철수 "
                "duration_minutes 를 낸다 — **사건 상태는 안 옮긴다**(in_progress 그대로 · "
                "닫는 것은 지휘의 일) · 철수·복귀 회신 실측")

    def _second_user_same_tenant(self):
        """같은 테넌트의 둘째 진화대원 — 픽스처의 `_user` 를 그대로 쓴다(두 벌 금지)."""
        return self._user("fws_crew_2", self.group_a, self.role_a)

    def test_second_crew_joins_without_409_and_release_keeps_event_open(self) -> None:
        """[턴 AL · 조율자 병합] 한 불에 진화대 둘 — 둘째 출동·도착은 409 가 아니고, 첫째 철수는 사건을 안 닫는다."""
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        a = self._bearer(self.user_a)
        path = _mission_response_path(event_id)
        for action in ("dispatch", "arrived"):
            r = self.client.post(_qs(path, action=action, lat=1.0, lng=2.0), **a)
            self.assertEqual(200, r.status_code, r.content)
        other = self._second_user_same_tenant()
        b = self._bearer(other)
        for action in ("dispatch", "arrived"):
            r = self.client.post(_qs(path, action=action, lat=1.0, lng=2.0), **b)
            self.assertEqual(200, r.status_code, r.content)
            self.assertIs(False, self._body(r)["event_advanced"])
        r = self.client.post(_qs(path, action="released"), **a)
        self.assertEqual(200, r.status_code, r.content)
        detail = self._body(self.client.get(_mission_path(event_id), **b))
        self.assertEqual("in_progress", detail["response_state"])

    def test_releasing_before_arriving_is_409(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        path = _mission_response_path(event_id)
        self.assertEqual(200, self.client.post(_qs(path, action="dispatch"), **head).status_code)
        self.assertEqual(409, self.client.post(_qs(path, action="released"), **head).status_code)

    def test_arriving_before_dispatch_is_409(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(_mission_response_path(event_id), action="arrived",
               lat=1.0, lng=2.0), **head)
        self.assertEqual(409, resp.status_code, resp.content)

    def test_other_tenant_mission_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.get(_mission_path(event_id), **head)
        self.assertEqual(404, resp.status_code, resp.content)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-05 지원 요청(인력·물·헬기·중장비)
# ═══════════════════════════════════════════════════════════════════════════
class F2_05_SupportRequestTest(Fws2HttpTest):
    def test_support_request_reaches_field_reply(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"kind": "helicopter", "amount": "1", "note": "산불 진화 헬기 요청"}
        resp = self.client.post(_qs(_mission_support_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("helicopter", body["kind"])
        self.assertIn("reply_id", body)

        from common.tenant_scope import TenantScope
        from apps.dsm.services import field_replies

        replies = field_replies(scope=TenantScope.of(self.user_a), event_id=event_id)
        self.assertTrue(
            any("helicopter" in r.text for r in replies),
            "지원 요청이 K1 현장 회신(지휘 화면이 읽는 자리)에 도달하지 않았습니다")
        _write_evidence(
            "FWS-F2-05", title="지원 요청(인력·물·헬기·중장비)",
            test_ref="tests.test_fws_f2.F2_05_SupportRequestTest."
                    "test_support_request_reaches_field_reply",
            method="POST", path=_qs(_mission_support_path(event_id), **params),
            request_params=params, response=resp,
            what="kind=helicopter 지원 요청이 K1 현장 회신으로 남고, 지휘 화면이 "
                "읽는 field_replies 목록에 그대로 도달한다(새 배지 위젯은 DSM 화면 "
                "소유라 범위 밖) — 지원 요청 도달 실측")

    def test_unknown_kind_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(_mission_support_path(event_id), kind="drone"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-07 안전 경보 수신(풍향 급변·헬기 투하 구역 이탈) — F1-10 문 재사용
# ═══════════════════════════════════════════════════════════════════════════
class F2_07_SafetyAlertTest(Fws2HttpTest):
    """새 엔드포인트가 없다 — F1-10 이 이미 연 `/alerts`·`/alerts/{id}/ack` 가
    채널·내용에 무관하게 「내게 온 안전 알림」 전부를 낸다(K2 발송이 낸 것은
    무엇이든 같은 문으로 도달한다). 이 시험은 F2 문맥(풍향 급변)의 알림도 같은
    문으로 도달·확인됨을 실측해 F2-07 을 닫는다."""

    def test_wind_shift_alert_arrives_and_acks_via_shared_alerts_endpoint(self) -> None:
        from kernels.k2_notify.services import send

        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        deliveries = send(scope=self.scope_pipe, event_id=event_id)
        mine = [d for d in deliveries if d.recipient_id == self.user_a.pk]
        self.assertTrue(mine, "픽스처 규칙이 user_a 에게 발송을 안 만들었습니다")
        delivery_id = mine[0].delivery_id

        head = self._bearer(self.user_a)
        list_resp = self.client.get(ALERTS, **head)
        self.assertEqual(200, list_resp.status_code, list_resp.content)
        row = next(r for r in self._body(list_resp)["alerts"]
                  if r["delivery_id"] == delivery_id)
        self.assertFalse(row["acknowledged"])

        ack = self.client.post(_ack_path(delivery_id), **head)
        self.assertEqual(200, ack.status_code, ack.content)
        self.assertTrue(self._body(ack)["acknowledged"])
        _write_evidence(
            "FWS-F2-07", title="안전 경보 수신(풍향 급변·헬기 투하 구역 이탈)",
            test_ref="tests.test_fws_f2.F2_07_SafetyAlertTest."
                    "test_wind_shift_alert_arrives_and_acks_via_shared_alerts_endpoint",
            method="POST", path=_ack_path(delivery_id), request_params={},
            response=ack,
            what="F2 안전 경보(풍향 급변 등)도 F1-10 이 연 GET /alerts·POST "
                "/alerts/{id}/ack 로 도달·확인된다 — 새 문을 열지 않고 재사용 "
                "실측(K2 발송은 채널·내용을 안 가린다)")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-12 내 임무 이력·투입 시간(수당 근거)
# ═══════════════════════════════════════════════════════════════════════════
class F2_12_MissionsMineTest(Fws2HttpTest):
    def test_dispatch_arrive_release_are_counted_in_mine(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        self.client.post(_qs(_mission_response_path(event_id), action="dispatch"), **head)
        self.client.post(
            _qs(_mission_response_path(event_id), action="arrived", lat=1.0, lng=2.0),
            **head)
        self.client.post(
            _qs(_mission_response_path(event_id), action="released"), **head)

        resp = self.client.get(MISSIONS_MINE, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(1, body["count"])
        row = body["missions"][0]
        self.assertEqual(event_id, row["mission_id"])
        self.assertIsNotNone(row["duration_minutes"])
        _write_evidence(
            "FWS-F2-12", title="내 임무 이력·투입 시간(수당 근거)",
            test_ref="tests.test_fws_f2.F2_12_MissionsMineTest."
                    "test_dispatch_arrive_release_are_counted_in_mine",
            method="GET", path=MISSIONS_MINE, request_params={}, response=resp,
            what="출동→도착→철수 한 임무 뒤 GET /missions/mine 에 그 임무가 1건, "
                "duration_minutes(투입 시간)와 함께 잡힌다 — 이력·수당 근거 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-13 훈련 임무 수신(훈련 배지)
# ═══════════════════════════════════════════════════════════════════════════
class F2_13_TrainingBadgeTest(Fws2HttpTest):
    def test_no_badge_when_drill_mode_is_off(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.get(TRAINING_MISSION, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIsNone(self._body(resp)["badge"])

    def test_badge_and_zero_real_channel_when_drill_mode_is_on(self) -> None:
        from apps.dsm.services import set_drill_mode

        set_drill_mode(scope=self.scope_a, enabled=True, reason="시험 훈련 창")
        head = self._bearer(self.user_a)
        resp = self.client.get(TRAINING_MISSION, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("훈련", body["badge"])
        self.assertTrue(body["drill_mode"])
        self.assertEqual(0, body["real_channel_sends"],
                         "훈련 배지가 떠 있는데 실채널 발송이 0이 아닙니다 — "
                         "완결조건(실채널 0)이 깨졌습니다")
        _write_evidence(
            "FWS-F2-13", title="훈련 임무 수신(훈련 배지)",
            test_ref="tests.test_fws_f2.F2_13_TrainingBadgeTest."
                    "test_badge_and_zero_real_channel_when_drill_mode_is_on",
            method="GET", path=TRAINING_MISSION, request_params={}, response=resp,
            what="훈련 모드가 켜진 테넌트에서 GET /training/mission 이 "
                "badge='훈련' · real_channel_sends=0 을 낸다(DSM drill_state·"
                "drill_report 재사용) — 훈련 배지·실채널 0 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-14 장비 점검 체크(등짐펌프·진화차)
# ═══════════════════════════════════════════════════════════════════════════
class F2_14_EquipmentCheckTest(Fws2HttpTest):
    def test_check_is_recorded_and_read_back(self) -> None:
        head = self._bearer(self.user_a)
        params = {"equipment_type": "backpack_pump", "equipment_code": "BP-7",
                 "result": "pass", "note": "이상 없음"}
        resp = self.client.post(_qs(EQUIPMENT_CHECKS, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertEqual("pass", self._body(resp)["result"])

        mine_resp = self.client.get(EQUIPMENT_CHECKS_MINE, **head)
        self.assertEqual(200, mine_resp.status_code, mine_resp.content)
        mine_body = self._body(mine_resp)
        self.assertEqual(1, mine_body["count"], "점검 1건이 재조회에서 안 잡힙니다")
        self.assertEqual("BP-7", mine_body["checks"][0]["equipment_code"])
        _write_evidence(
            "FWS-F2-14", title="장비 점검 체크(등짐펌프·진화차)",
            test_ref="tests.test_fws_f2.F2_14_EquipmentCheckTest."
                    "test_check_is_recorded_and_read_back",
            method="GET", path=EQUIPMENT_CHECKS_MINE, request_params={},
            response=mine_resp,
            what="POST /equipment/checks(등짐펌프 BP-7 · pass) 뒤 GET "
                "/equipment/checks/mine 의 count 가 1, 방금 남긴 장비 코드가 "
                "그대로 보인다 — 점검 1 실측")

    def test_unknown_result_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(EQUIPMENT_CHECKS, equipment_type="fire_truck", result="maybe"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-15 근무 외 차단·담당 구역 — F1-12 문 재사용
# ═══════════════════════════════════════════════════════════════════════════
class F2_15_OffDutyBlockTest(Fws2HttpTest):
    """새 엔드포인트가 없다 — F1-12 가 이미 연 `/notify-prefs`(방해 금지 시간대 ·
    담당 초소/구역)를 진화대(F2)도 그대로 쓴다. 이 시험은 F2 사용자(user_a)가 담당
    '구역'(assigned_post_code 재사용)을 저장·재조회함을 실측해 F2-15 를 닫는다."""

    def test_off_duty_block_and_assigned_zone_save_then_read_back(self) -> None:
        head = self._bearer(self.user_a)
        params = {"quiet_hours_start": "23:00", "quiet_hours_end": "05:00",
                 "assigned_post_code": "ZONE-3"}
        save = self.client.post(_qs(NOTIFY_PREFS, **params), **head)
        self.assertEqual(200, save.status_code, save.content)

        read = self.client.get(NOTIFY_PREFS, **head)
        self.assertEqual(200, read.status_code)
        body = self._body(read)
        self.assertEqual("23:00", body["quiet_hours_start"])
        self.assertEqual("ZONE-3", body["assigned_post_code"])
        _write_evidence(
            "FWS-F2-15", title="근무 외 차단·담당 구역",
            test_ref="tests.test_fws_f2.F2_15_OffDutyBlockTest."
                    "test_off_duty_block_and_assigned_zone_save_then_read_back",
            method="GET", path=NOTIFY_PREFS, request_params={}, response=read,
            what="F1-12 가 연 GET/POST /notify-prefs 를 F2 진화대도 그대로 써서 "
                "근무 외 차단 시간대·담당 구역이 저장 → 재조회에 남는다 — 새 문을 "
                "열지 않고 재사용 실측")
