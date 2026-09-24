# -*- coding: utf-8 -*-
"""P-325 — 「보냈습니다」 길목 시험 (턴 S · 2026-09-24).

재는 것 셋
----------
    ① 있는 주소 · SMTP 죽음  → 실패 안내(「보냈습니다」가 아니다) · 메일 0통
    ② 없는 주소 · SMTP 죽음  → ①과 **바이트까지 같은 본문**(계정 존재가 안 샌다)
    ③ SMTP 살아 있음         → dj-core 로 그대로 넘어간다(메일은 우리 겹이 아니라
                                dj-core 의 `try/except` 안에서 만들어진다 — 그래서
                                실제 발송은 `RecordingBackend` 로 잡아 0통을 유지한다)

이 파일이 SMTP 를 **진짜로** 열지 않는 이유
--------------------------------------------
`common.reset_mail_gate.smtp_reachable` 을 직접 patch 한다 — 소켓을 실제로 열면
이 컨테이너의 `SMTP_SERVER=smtp.invalid`(더미 값)에 매번 좌우되고, 「SMTP 가 살아
있을 때」를 이 시험 환경에서는 아예 만들 수 없다. `_tcp_probe`/캐시는 이 파일이
아니라 실물 환경에서만 확인한다(게이트 `scripts/verify_password_reset.py` 가
`--self-test` 로 판정 규칙만 다시 잰다).

★ 이 시험이 잡는 함정 — **순서를 뒤집으면 계정 존재가 샌다**
--------------------------------------------------------------
길목이 "주소를 먼저 보고 SMTP 를 나중에 보는" 모양이면, 있는 주소만 SMTP 검사를
타는 경로가 생겨 그 차이(지연·로그·응답)로 회원 명단을 셀 수 있다. `test_a_*` 와
`test_an_*` 가 **바이트까지 같은 본문**을 요구하는 것이 그 함정을 잡는 자리다 —
순서를 뒤집어 심어 보면(주소 조회 후 SMTP 판정) 있는 주소 쪽만 다른 코드 경로를
타게 만들 수 있어 이 단언이 갈라진다(자기시험 결과는 이 파일이 아니라 작업 보고에
적는다 — D-310 은 판정기의 자기시험을 요구하지, 응용 시험 파일 자체에 이형 코드를
심어 두라는 규칙은 아니다).

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib
from unittest import mock

from django.apps import apps
from django.test import Client, TestCase, override_settings

from common import reset_mail_gate
from tests.no_cache import NO_CACHE


class RecordingBackend:
    """dj-core 가 세우는 `SMTPEmailBackend` 자리에 대신 선다 — 실 SMTP 는 절대 안 연다.

    `test_s_password_reset_walk.py::RecordingBackend` 와 같은 자리 — 두 파일이 서로
    다른 시각에 이 클래스를 모듈 전역 상태(`sent`)로 갱신하므로, 여기서도 매 `setUp`
    에서 비운다(테스트 순서 간 오염 방지).
    """

    sent: list = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    def send_notification(self, email_data):
        RecordingBackend.sent.append(email_data)
        return True


LOCMEM = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "p325-reset-mail-gate",
    }
}

FORGOT = "/api/v1/auth/forgot-password"

#: 시험 계정의 비밀번호. dj-core 의 is_strong_password 를 통과해야 해서 길다.
PW = "GxP325-Reset-2026!aa"


@override_settings(CACHES=LOCMEM)
class ResetMailGateTest(TestCase):
    """비밀번호 찾기 길목 — SMTP 도달성이 먼저, 주소는 그다음."""

    def setUp(self) -> None:
        from django.core.cache import caches

        caches["default"].clear()
        RecordingBackend.sent = []
        #: 부르는 자리의 이름을 가로챈다(정의된 자리를 갈아 끼우면 import 시점에
        #: dj-core `auth.py` 가 붙들어 둔 옛 이름이 살아 아무것도 안 잡힌다).
        patcher = mock.patch("core.api.v1.auth.SMTPEmailBackend", RecordingBackend)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        """HTTP 를 때린 시험은 스레드에 요청을 남긴다 — 치우고 나간다.

        `test_s_password_reset_walk.py` 가 이미 실측한 관용구다: 치우지 않으면
        `thread_local.request.user` 가 되돌려진 사용자 행을 가리킨 채 남아, 뒤따르는
        시험(`UserGroup` 저장 훅 등)이 죽은 `created_by` 로 FK 위반을 낸다.
        """
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    # ── 도우미 ───────────────────────────────────────────────────────────
    def _user(self, name: str, email: str):
        CoreUser = apps.get_model("user", "CoreUser")
        return CoreUser.objects.create_user(
            username=name, password=PW, is_active=True, email=email)

    def _post(self, path: str, body: dict, addr: str = "10.255.255.91"):
        client = Client(REMOTE_ADDR=addr, **NO_CACHE)
        return client.post(path, data=body, content_type="application/json")

    # ── ① 있는 주소 · SMTP 죽음 — 「보냈습니다」가 아니다 · 메일 0통 ───────
    def test_a_known_address_gets_the_honest_failure_when_smtp_is_dead(self) -> None:
        user = self._user("gxtest_p325_known", "gxtest_p325_known@test.invalid")
        with mock.patch.object(reset_mail_gate, "smtp_reachable", return_value=False):
            r = self._post(FORGOT, {"email": user.email})

        self.assertNotEqual(
            200, r.status_code,
            "SMTP 가 죽었는데 200(「보냈습니다」류)을 냈다 — 거짓말을 그대로 통과시켰다")
        self.assertEqual(0, len(RecordingBackend.sent),
                         "SMTP 가 죽었는데 dj-core 까지 넘어가 메일을 만들었다")
        body = r.content.decode("utf-8")
        self.assertNotIn("token=", body, "실패 응답에 재설정 토큰이 실렸다")

    # ── ② 없는 주소 · SMTP 죽음 — ①과 바이트까지 같은 본문 ─────────────────
    def test_an_unknown_address_answers_byte_identical_when_smtp_is_dead(self) -> None:
        user = self._user("gxtest_p325_enum", "gxtest_p325_enum@test.invalid")

        with mock.patch.object(reset_mail_gate, "smtp_reachable", return_value=False):
            known = self._post(FORGOT, {"email": user.email})
            unknown = self._post(FORGOT, {"email": "gxtest_p325_nobody@test.invalid"})

        self.assertEqual(known.status_code, unknown.status_code,
                         "있는 주소와 없는 주소의 상태 코드가 다르다 — 그 차이로 "
                         "회원 명단을 셀 수 있다")
        self.assertEqual(known.content, unknown.content,
                         "있는 주소와 없는 주소의 본문이 바이트까지 같지 않다")
        self.assertEqual(0, len(RecordingBackend.sent),
                         "SMTP 가 죽었는데 어느 쪽이든 메일을 만들었다")

    # ── ③ SMTP 살아 있음 — dj-core 로 그대로 넘어간다 ───────────────────────
    def test_smtp_alive_falls_through_to_djcore(self) -> None:
        user = self._user("gxtest_p325_alive", "gxtest_p325_alive@test.invalid")
        with mock.patch.object(reset_mail_gate, "smtp_reachable", return_value=True):
            r = self._post(FORGOT, {"email": user.email})

        self.assertEqual(200, r.status_code, r.content[:300])
        self.assertEqual(
            1, len(RecordingBackend.sent),
            "SMTP 가 살아 있는데 dj-core 까지 안 넘어갔다 — 길목이 정상 경로를 막았다")
        #: 실 발송 0 — `RecordingBackend` 가 SMTPEmailBackend 자리를 대신 선다.
        #: (여기서 `RecordingBackend.sent` 에 쌓이는 것 자체가 "실물 SMTP 를 안
        #: 열었다"는 증거다 — 진짜로 열었다면 이 mock 은 아예 안 불렸을 것이다.)
