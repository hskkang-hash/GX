# -*- coding: utf-8 -*-
"""FWS App(L4) — S 등급 별표 절 10건의 **HTTP 실측**과 `docs/agent/evidence/SPEC/*.json`
생성 (WO-GX-20260925-15 §5 P-356·357·358 · 턴 AK 차선 N2).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`) 헤더를 모든 요청에 싣는다.
멱등(`Idempotency-Key`) 캐시는 Django 캐시를 따로 쓰므로, 그 캐시를 재는 시험은
`setUp` 에서 `django.core.cache.cache.clear()` 로 비운 뒤 시작한다(P-19 계열 — 적중
본문이 다음 시험의 상태를 가리면 안 된다).

이 파일이 재는 것 — **P-356 승격 규칙 넷 중 ①②**
---------------------------------------------------
    ① 실제 구현        `self.client` 가 `/api/fws/...` 를 **실제로 두드린다**
                        (핸들러가 손으로 부른 함수가 아니라, urls.py 가 실제로
                        문 연 라우트)
    ② 실측 증거        각 시험이 요청·응답을 **그대로** `docs/agent/evidence/SPEC/
                        <id>.json` 에 적는다 — 손으로 쓴 값 0개, 이 시험이 만든 값뿐.
③(게이트)·④(대장 이동)은 `scripts/verify_spec_fws.py` 와
`docs/agent/evidence/SPEC/N2_promotions.md` 가 가진다.

Django 모델을 직접 만지는 것은 `apps.fws.patrol`·`notify_prefs`·`alerts`(감사 로그
전건 읽기) — DSM 의 `notify_prefs.py`·`audit.py` 와 같은 자리이고, 그 파일들은
`AppStaysThinTest` 가 보는 두 파일(`api`·`services`) 밖이다(아래 참조).
"""
from __future__ import annotations

import contextlib
import json
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase

from common.evidence_guard import allow_evidence_writes
from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"


def _qs(path: str, **params) -> str:
    """원시 인자는 **질의(query)**다(`apps/dsm/law_api.py` 머리말 ④와 같은 규약 —
    이 저장소의 Ninja 라우트는 primitive POST 인자를 query 로 받는다). `None` 은
    보내지 않는다 — 「안 보냄」과 「빈 문자열」은 다른 값이다."""
    live = {k: v for k, v in params.items() if v is not None}
    return f"{path}?{urlencode(live)}" if live else path

PATROL_CHECKIN = "/api/fws/patrol/checkin"
PATROL_TRACK = "/api/fws/patrol/track"
PATROL_MINE = "/api/fws/patrol/mine"
RISK_TODAY = "/api/fws/risk/today"
EMERGENCY_CONTACTS = "/api/fws/emergency-contacts"
ALERTS = "/api/fws/alerts"
NOTIFY_PREFS = "/api/fws/notify-prefs"


def _verification_path(vid) -> str:
    return f"/api/fws/verifications/{vid}"


def _reply_path(vid) -> str:
    return f"/api/fws/verifications/{vid}/reply"


def _ack_path(delivery_id) -> str:
    return f"/api/fws/alerts/{delivery_id}/ack"


def _write_evidence(clause_id: str, *, title: str, test_ref: str, method: str,
                    path: str, request_params: dict, response, what: str) -> None:
    """실측 증거 한 건을 **기계가** 적는다 — 손으로 옮겨 적지 않는다(P-356 ②).

    `response` 는 Django 테스트 클라이언트가 돌려준 실제 HttpResponse다. 이
    저장소의 Ninja 라우트는 원시 인자를 질의(query)로 받으므로(`law_api.py`
    머리말 ④) `path` 는 실제로 두드린 전체 경로(질의 포함)를 그대로 담는다.

    캐시 처리: 해당 없음 — 증거 파일 쓰기는 HTTP 응답 캐시와 무관하다.

    ★ `docs/agent/evidence/**` 쓰기는 시험 중 기본으로 막혀 있다(`common.
      evidence_guard` — 시험 DB 의 수가 운영 증거로 둔갑한 사고, P-87 ④). 이
      자리는 **일부러 쓰는 자리**이므로 이름을 대고 연다.
    """
    import datetime as _dt

    with allow_evidence_writes(
            "P-356 ② FWS 별표 절 실측 증거 — pytest 가 방금 두드린 HTTP 왕복을 "
            "그대로 적는다(손으로 옮기지 않는다)"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            body = json.loads((response.content or b"{}").decode("utf-8", "replace"))
        except (ValueError, TypeError):
            body = {"_raw": (response.content or b"").decode("utf-8", "replace")}
        payload = {
            "id": clause_id,
            "title": title,
            "measured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "measured_by": "django_test_client",
            "test": test_ref,
            "request": {"method": method, "path": path, "params": request_params},
            "response": {"status": response.status_code, "body": body},
            "what": what,
        }
        out = EVIDENCE_DIR / f"{clause_id}.json"
        #: [턴 AN · P-392] 다른 시험이 이 증거 위에 더한 「제목이 부르는 것 ↔ 있는 것」 표
        #:   (`title_parts`)는 **보존한다** — 이 시험은 HTTP 왕복만 다시 적는다. 안 그러면
        #:   전량 시험 순서에 따라 표가 지워져 O 게이트가 옛 승격으로 오판한다(FWS-F6-07).
        if out.is_file():
            try:
                prev = json.loads(out.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                prev = {}
            for keep in ():  #: [턴 AQ · P-431 · 차선 Q] 사람 표 키는 json 에 옮기지 않는다 — 정본은 <id>.retro.md
                if keep in prev:
                    payload[keep] = prev[keep]
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


class FwsHttpTest(DsmFixture):
    """`DsmFixture` 를 그대로 쓴다(테넌트 A/B·스트림·역할·규칙) — 같은 표를 두 벌로
    만들지 않는다(`test_f_system_request_handled.py` 와 같은 재사용)."""

    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self) -> None:
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cache.clear()

    def _bearer(self, user) -> dict:
        """`test_f_system_request_handled.py::_bearer` 와 같은 세 줄 — 실제 JWT."""
        import jwt as pyjwt
        from ninja_jwt.tokens import RefreshToken

        session_id = str(uuid.uuid4())
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        setter = getattr(user, "set_encrypted_session_token", None)
        if setter is not None:
            setter(session_id, decoded.get("jti"))
            user.save()
        return {"HTTP_AUTHORIZATION": "Bearer %s" % access}

    @staticmethod
    def _body(resp):
        return json.loads((resp.content or b"{}").decode("utf-8"))


# ═══════════════════════════════════════════════════════════════════════════
# ① 얇은가 — App 이 커널의 일을 다시 하고 있지 않은가 (DA-04 §1-1)
# ═══════════════════════════════════════════════════════════════════════════
class AppStaysThinTest(TestCase):
    """`tests/test_dsm_app.py::AppStaysThinTest` 와 같은 잣대, 이 App 의 유일한
    조립 파일(`api.py`)에 적용한다. FWS 는 `services.py` 를 두지 않는다 — 기능마다
    모듈이 갈려 있고(`patrol`·`risk`·`verification`·`alerts`·`notify_prefs`·
    `contacts`), 감사 로그를 직접 읽고 쓰는 자리(`patrol`·`alerts`·`notify_prefs`)는
    DSM 의 `notify_prefs.py`·`audit.py` 와 같은 자리라 이 시험이 보지 않는다
    (그 파일들의 표는 새 모델이 아니라 dj-core 감사 표 하나뿐이고, 그 표를 만지는
    합의는 이미 §0.4 밖에서 K1 field_reply.py 가 세워 두었다)."""

    MODEL_SMELLS = ("apps.get_model(", "_base_manager", ".objects.filter(",
                    "models.Model")

    def test_the_api_module_does_not_touch_django_models(self) -> None:
        import inspect

        from apps.fws import api

        src = inspect.getsource(api)
        for smell in self.MODEL_SMELLS:
            self.assertNotIn(
                smell, src,
                f"apps.fws.api 가 모델을 직접 만집니다({smell}). API 층이 만질 수 "
                f"있는 것은 기능 모듈·커널의 함수뿐입니다 (DA-04 §1-4).")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-01 근무 시작·초소 체크인
# ═══════════════════════════════════════════════════════════════════════════
class F1_01_CheckinTest(FwsHttpTest):
    def test_checkin_sets_on_duty_status_with_location(self) -> None:
        head = self._bearer(self.user_a)
        params = {"post_code": "P-12", "method": "gps", "lat": 36.35, "lng": 127.38}
        resp = self.client.post(_qs(PATROL_CHECKIN, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("on_duty", body["status"],
                         "체크인 뒤 초소 상태가 '근무 중'이 아닙니다")
        self.assertEqual({"lat": 36.35, "lng": 127.38}, body["location"])
        _write_evidence(
            "FWS-F1-01", title="근무 시작·초소 체크인(NFC/GPS)",
            test_ref="tests.test_fws_app.F1_01_CheckinTest."
                    "test_checkin_sets_on_duty_status_with_location",
            method="POST", path=_qs(PATROL_CHECKIN, **params), request_params=params,
            response=resp,
            what="POST /api/fws/patrol/checkin 뒤 응답의 status 가 on_duty, "
                "location 이 요청 좌표 그대로 실려 온다 — 초소 상태·위치 둘 다 실측")

    def test_missing_post_code_is_422_not_500(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(PATROL_CHECKIN, post_code="", method="gps"), **head)
        self.assertEqual(422, resp.status_code, resp.content)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-02 순찰 경로 기록(GPS 트랙 · 전자순찰함 NFC)
# ═══════════════════════════════════════════════════════════════════════════
class F1_02_TrackTest(FwsHttpTest):
    def test_gps_point_and_checkpoint_pass_are_counted_separately(self) -> None:
        head = self._bearer(self.user_a)
        r1 = self.client.post(
            _qs(PATROL_TRACK, post_code="P-12", lat=36.1, lng=127.1), **head)
        self.assertEqual(200, r1.status_code, r1.content)
        self.assertEqual(1, self._body(r1)["track_count"])
        self.assertEqual(0, self._body(r1)["checkpoint_count"])

        params = {"post_code": "P-12", "checkpoint_code": "CHK-3"}
        resp = self.client.post(_qs(PATROL_TRACK, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(1, body["track_count"])
        self.assertEqual(1, body["checkpoint_count"],
                         "순찰함 통과가 트랙과 같은 칸에 섞였거나 안 세어졌습니다")
        _write_evidence(
            "FWS-F1-02", title="순찰 경로 기록(GPS 트랙 · 전자순찰함 NFC)",
            test_ref="tests.test_fws_app.F1_02_TrackTest."
                    "test_gps_point_and_checkpoint_pass_are_counted_separately",
            method="POST", path=_qs(PATROL_TRACK, **params), request_params=params,
            response=resp,
            what="GPS 점 1건 뒤 순찰함 통과 1건을 보내면 track_count=1 · "
                "checkpoint_count=1 로 갈려 나온다 — 트랙 1 · 순찰함 통과 N 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-03 오늘 위험지수·위기경보·입산통제
# ═══════════════════════════════════════════════════════════════════════════
class F1_03_RiskTodayTest(FwsHttpTest):
    def test_risk_band_has_the_contract_shape(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.get(RISK_TODAY, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        for key in ("level", "fire_alert", "mountain_entry_banned", "season", "as_of"):
            self.assertIn(key, body, f"위험지수 응답에 {key} 칸이 없습니다")
        from apps.fws.risk import LEVELS
        self.assertIn(body["level"], LEVELS)
        self.assertEqual(date.today().isoformat(), body["as_of"])
        _write_evidence(
            "FWS-F1-03", title="오늘 위험지수·위기경보·입산통제 확인",
            test_ref="tests.test_fws_app.F1_03_RiskTodayTest."
                    "test_risk_band_has_the_contract_shape",
            method="GET", path=RISK_TODAY, request_params={},
            response=resp,
            what="GET /api/fws/risk/today 가 오늘 날짜 기준 띠(level)·위기경보·"
                "입산통제 값을 낸다 — 띠 표시 실측(외부 기상 연동은 범위 밖, "
                "risk.py 머리말에 정직하게 남김)")

    def test_anonymous_is_401(self) -> None:
        resp = self.client.get(RISK_TODAY)
        self.assertEqual(401, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-05 확인 요청 수신 · FWS-F1-06 현장 확인 회신
# ═══════════════════════════════════════════════════════════════════════════
class F1_05_06_VerificationTest(FwsHttpTest):
    def test_verification_detail_and_fire_confirmed_reply(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)

        detail_resp = self.client.get(_verification_path(event_id), **head)
        self.assertEqual(200, detail_resp.status_code, detail_resp.content)
        detail_body = self._body(detail_resp)
        self.assertEqual(event_id, detail_body["verification_id"])
        _write_evidence(
            "FWS-F1-05", title="확인 요청 수신(카메라 사진·위치·거리·지도)",
            test_ref="tests.test_fws_app.F1_05_06_VerificationTest."
                    "test_verification_detail_and_fire_confirmed_reply",
            method="GET", path=_verification_path(event_id), request_params={},
            response=detail_resp,
            what="K1 이벤트를 '확인 요청'으로 GET — 화면이 그릴 좌표·스냅샷 경로가 "
                "응답에 실린다(지도 렌더는 금지구역 밖이라 좌표 값만)")

        reply_params = {"result": "fire_confirmed", "note": "연기 확인, 화세 보통"}
        reply_resp = self.client.post(_qs(_reply_path(event_id), **reply_params), **head)
        self.assertEqual(200, reply_resp.status_code, reply_resp.content)
        reply_body = self._body(reply_resp)
        self.assertEqual("confirmed", reply_body["verdict"],
                         "현장 확인 회신(산불 맞음)이 사건 판정을 확정으로 안 바꿨습니다")
        _write_evidence(
            "FWS-F1-06", title="현장 확인 회신(산불 맞음/소각·오인/접근 불가)",
            test_ref="tests.test_fws_app.F1_05_06_VerificationTest."
                    "test_verification_detail_and_fire_confirmed_reply",
            method="POST", path=_qs(_reply_path(event_id), **reply_params),
            request_params=reply_params,
            response=reply_resp,
            what="현장 회신 result=fire_confirmed 뒤 K1 사건의 verdict 가 "
                "confirmed 로 바뀐다 — 회신 → 사건 확정 실측")

    def test_false_alarm_requires_one_of_five_reasons(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        bad = self.client.post(
            _qs(_reply_path(event_id), result="false_alarm",
               reason_code="not-a-real-reason"), **head)
        self.assertEqual(422, bad.status_code, bad.content)

        good = self.client.post(
            _qs(_reply_path(event_id), result="false_alarm",
               reason_code="agri_burning"), **head)
        self.assertEqual(200, good.status_code, good.content)
        self.assertEqual("rejected", self._body(good)["verdict"])

    def test_other_tenant_verification_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.get(_verification_path(event_id), **head)
        self.assertEqual(404, resp.status_code, resp.content)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-08 119·산림청 신고 번호
# ═══════════════════════════════════════════════════════════════════════════
class F1_08_EmergencyContactsTest(FwsHttpTest):
    def test_numbers_come_from_the_server_not_the_screen(self) -> None:
        # [턴 AK · 조율자 병합] 익명은 닫혔다(래칫 open_anonymous) — 로그인한 감시원만.
        self.assertIn(self.client.get(EMERGENCY_CONTACTS).status_code, (401, 403))
        resp = self.client.get(EMERGENCY_CONTACTS, **self._bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("119", body["fire_report"])
        self.assertEqual("042-481-4119", body["forest_report"])
        _write_evidence(
            "FWS-F1-08", title="119·산림청 신고 번호 버튼",
            test_ref="tests.test_fws_app.F1_08_EmergencyContactsTest."
                    "test_numbers_come_from_the_server_not_the_screen",
            method="GET", path=EMERGENCY_CONTACTS, request_params={},
            response=resp,
            what="GET /api/fws/emergency-contacts(로그인 뒤 · 익명은 닫힘)가 119·042-481-4119 를 "
                "낸다 — 화면은 이 값으로 tel: 링크를 만든다(1탭)")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-10 안전 알림 수신(도달·확인)
# ═══════════════════════════════════════════════════════════════════════════
class F1_10_AlertsTest(FwsHttpTest):
    def test_alert_arrives_and_can_be_acknowledged(self) -> None:
        from kernels.k2_notify.services import send

        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        deliveries = send(scope=self.scope_pipe, event_id=event_id)
        mine = [d for d in deliveries if d.recipient_id == self.user_a.pk]
        self.assertTrue(mine, "픽스처 규칙(critical→email)이 user_a 에게 발송을 "
                              "안 만들었습니다 — 시험 전제가 깨졌습니다")
        delivery_id = mine[0].delivery_id

        head = self._bearer(self.user_a)
        list_resp = self.client.get(ALERTS, **head)
        self.assertEqual(200, list_resp.status_code, list_resp.content)
        rows = self._body(list_resp)["alerts"]
        row = next((r for r in rows if r["delivery_id"] == delivery_id), None)
        self.assertIsNotNone(row, "방금 보낸 알림이 내 목록(도달)에 없습니다")
        self.assertFalse(row["acknowledged"])
        _write_evidence(
            "FWS-F1-10", title="안전 알림 수신(풍향 급변·대피 지시·철수)",
            test_ref="tests.test_fws_app.F1_10_AlertsTest."
                    "test_alert_arrives_and_can_be_acknowledged",
            method="GET", path=ALERTS, request_params={},
            response=list_resp,
            what="K2 send() 로 보낸 발송이 GET /api/fws/alerts(내 목록)에 도달로 "
                "나타난다 — 도달 실측(확인은 같은 시험의 ack 호출)")

        ack_resp = self.client.post(_ack_path(delivery_id), **head)
        self.assertEqual(200, ack_resp.status_code, ack_resp.content)
        self.assertTrue(self._body(ack_resp)["acknowledged"])
        again = self.client.get(ALERTS, **head)
        row2 = next(r for r in self._body(again)["alerts"]
                   if r["delivery_id"] == delivery_id)
        self.assertTrue(row2["acknowledged"], "확인 뒤 재조회에 acknowledged 가 "
                                              "안 실렸습니다")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-11 내 근무 기록·순찰 실적(일·주)
# ═══════════════════════════════════════════════════════════════════════════
class F1_11_PatrolMineTest(FwsHttpTest):
    def test_todays_checkin_and_track_are_counted(self) -> None:
        head = self._bearer(self.user_a)
        self.client.post(_qs(PATROL_CHECKIN, post_code="P-9", method="nfc"), **head)
        self.client.post(
            _qs(PATROL_TRACK, post_code="P-9", lat=36.2, lng=127.2), **head)

        resp = self.client.get(PATROL_MINE, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(1, body["today"]["checkins"])
        self.assertEqual(1, body["today"]["tracks"])
        self.assertGreaterEqual(body["week"]["checkins"], 1)
        _write_evidence(
            "FWS-F1-11", title="내 근무 기록·순찰 실적(일·주)",
            test_ref="tests.test_fws_app.F1_11_PatrolMineTest."
                    "test_todays_checkin_and_track_are_counted",
            method="GET", path=PATROL_MINE, request_params={},
            response=resp,
            what="체크인 1·트랙 1 뒤 GET /api/fws/patrol/mine 의 today 칸이 "
                "1·1 로 표에 실측된다(week 칸은 today 를 포함해 >=1)")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-12 근무 외 알림 차단·담당 초소 설정
# ═══════════════════════════════════════════════════════════════════════════
class F1_12_NotifyPrefsTest(FwsHttpTest):
    def test_save_then_read_back(self) -> None:
        head = self._bearer(self.user_a)
        empty = self.client.get(NOTIFY_PREFS, **head)
        self.assertEqual(200, empty.status_code)
        self.assertEqual("", self._body(empty)["assigned_post_code"])

        save_params = {"quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
                      "assigned_post_code": "P-12"}
        save_resp = self.client.post(_qs(NOTIFY_PREFS, **save_params), **head)
        self.assertEqual(200, save_resp.status_code, save_resp.content)

        read_resp = self.client.get(NOTIFY_PREFS, **head)
        self.assertEqual(200, read_resp.status_code)
        body = self._body(read_resp)
        self.assertEqual("22:00", body["quiet_hours_start"])
        self.assertEqual("P-12", body["assigned_post_code"])
        _write_evidence(
            "FWS-F1-12", title="근무 외 알림 차단·담당 초소 설정",
            test_ref="tests.test_fws_app.F1_12_NotifyPrefsTest.test_save_then_read_back",
            method="GET", path=NOTIFY_PREFS, request_params={},
            response=read_resp,
            what="POST 로 저장한 방해 금지 시간대·담당 초소가 이후 GET 재조회에 "
                "그대로 보인다 — 저장 실측(같은 시험 안 다른 요청으로 재조회)")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-13 오프라인 큐 — 복귀 시 전송 N (Idempotency-Key 로 재전송 중복 제거)
# ═══════════════════════════════════════════════════════════════════════════
class F1_13_OfflineReplayTest(FwsHttpTest):
    """산지에서 통신이 끊긴 동안 화면이 요청을 큐에 쌓고, 복귀 시 **같은 키로**
    다시 보낸다. 서버가 두 번째를 세지 않아야 「복귀 시 전송 N」의 N 이 참이다."""

    def test_replayed_checkin_with_same_key_is_not_double_counted(self) -> None:
        head = self._bearer(self.user_a)
        head_with_key = dict(head, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        params = {"post_code": "P-7", "method": "gps", "lat": 1.0, "lng": 2.0}
        replay_path = _qs(PATROL_CHECKIN, **params)

        first = self.client.post(replay_path, **head_with_key)
        self.assertEqual(200, first.status_code, first.content)

        # ★ 오프라인 큐가 복귀 시 **같은 요청을 다시** 보낸다 — 통신이 끊긴 줄
        #   모르고 화면이 한 번 더 쏘는 바로 그 모양.
        replay = self.client.post(replay_path, **head_with_key)
        self.assertEqual(200, replay.status_code, replay.content)

        mine_resp = self.client.get(PATROL_MINE, **head)
        checkins = self._body(mine_resp)["today"]["checkins"]
        self.assertEqual(
            1, checkins,
            f"같은 Idempotency-Key 로 두 번 보냈는데 근무 기록이 {checkins}건입니다 "
            f"— 복귀 시 재전송이 실제 근무 기록을 중복시킵니다")
        _write_evidence(
            "FWS-F1-13", title="오프라인 큐 — 산지 통신 불가 시 기록 저장 후 전송",
            test_ref="tests.test_fws_app.F1_13_OfflineReplayTest."
                    "test_replayed_checkin_with_same_key_is_not_double_counted",
            method="POST", path=replay_path, request_params=params,
            response=replay,
            what="같은 Idempotency-Key 로 체크인을 두 번 보내도(오프라인 큐의 "
                "재전송을 흉내) patrol/mine 의 checkins 는 1 그대로다 — "
                "복귀 시 전송 N 이 중복을 만들지 않음을 실측(프런트 큐는 "
                "frontend/src/features/fws/offlineQueue.ts, 서버 쪽 중복 제거는 "
                "common/idempotency.py 재사용)")
