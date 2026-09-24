# -*- coding: utf-8 -*-
"""비밀번호 찾기 **한 바퀴** — 잊은 사람이 혼자 돌아온다 (턴 AH · P-290 · 차선 S).

무엇을 재는가
-------------
    ① 있는 주소로 부르면 **보낼 메일 1통**이 만들어지고 본문에 재설정 링크가 있다
    ② **없는 주소도 같은 답**이고 메일은 **0통** — 답으로 회원 명단을 캐낼 수 없다
    ③ 링크의 앞머리는 **설정한 주소**에서 온다(손으로 박은 값이 아니다)
    ④ 그 링크의 토큰으로 재설정하면 **새 비밀번호로 로그인이 된다** ← 한 바퀴
    ⑤ 같은 토큰은 **두 번 안 듣는다**
    ⑥ 지어낸 토큰은 거절된다

★ **이 시험은 「메일이 도착했다」를 재지 않는다 — 잴 수 없다.**
  여기서 붙잡는 것은 「보낼 물건이 이렇게 만들어졌다」이지 「수신함에 들어갔다」가
  아니다(test_e_ops10_alert_routing.py 가 같은 자리에서 먼저 적어 둔 구분).
  실제 도착은 **게이트가 Mailpit 수신함을 세서** 잰다. 두 수는 다른 수다:

      이 시험   「그렇게 되도록 배선돼 있다」   보내는 길이 막혀 있어도 초록
      게이트    「오늘 그랬다」                 SMTP 가 Mailpit 을 봐야 초록

  그래서 이 파일이 초록이어도 **대표 화면의 Mailpit 은 0통일 수 있다** — 지금이
  정확히 그 상태다(CEO_INBOX 열린 질문).

★★ **장고의 EMAIL_* 로는 이 문을 못 잡는다** [실측 2026-09-24].
  dj-core 는 `django.core.mail` 을 **안 쓴다.** `core/api/v1/auth.py` 가
  `SMTPEmailBackend()` 를 직접 세우고, 그 백엔드는 장고 설정이 아니라
  **`os.getenv` 로 다른 이름 여섯**을 읽는다 —
  SMTP_SERVER · SMTP_PORT · SENDER_EMAIL · SMTP_USERNAME · SMTP_PASSWORD · SMTP_TLS.
  그래서 `override_settings(EMAIL_BACKEND=locmem)` 은 **아무 일도 안 한다**
  (첫 판이 정확히 그래서 빨갰다: mail.outbox 가 0). 이 파일은 그 백엔드를
  **가로채서** 재고, 그것이 이 문을 재는 유일한 정직한 길이다.

⚠ **그리고 이 문은 실패를 삼킨다** [실측 · 고치지 않았다 · §0.4 안이라 여기선 못 고친다].
  `forgot_password` 의 `except Exception:` 이 발송 실패를 로그로만 남기고
  **성공 응답을 그대로 돌려준다.** 유출을 막으려던 설계가 **고장까지 같이 숨긴다** —
  지금 화면은 「메일 보냈습니다」라고 말하는데 한 통도 안 나간다.
  이 사실을 **단언으로 못박지 않는다**(고치는 날 시험이 빨개지면 안 된다).
  이것을 잡는 것은 시험이 아니라 **Mailpit 수신함을 세는 게이트**다.

★ §0.4 — 이 흐름은 **전부 dj-core 안**에 있다(core/api/v1/auth.py).
  이 파일은 그것을 **부르기만** 한다. 한 줄도 안 고친다.

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

from unittest import mock

from django.apps import apps
from django.test import Client, TestCase, override_settings

from tests.no_cache import NO_CACHE


class RecordingBackend:
    """dj-core 가 세우는 `SMTPEmailBackend` 자리에 **대신 선다.**

    실물은 redmail 로 SMTP 를 직접 연다 — 시험에서 그 문을 열 수는 없고, 열어서도
    안 된다. 여기서 붙잡는 것은 **그 문에 건네진 물건**이다: 받는 사람 · 제목 ·
    본문. 그 셋이 맞으면 「배선돼 있다」는 증명이고, 그 물건이 실제로 도착했는지는
    이 시험이 아니라 게이트가 잰다.
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
        "LOCATION": "s-password-reset-walk",
    }
}

FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"
LOGIN = "/api/v1/auth/login"

#: dj-core core/api/v1/auth.py — ratelimit(key=ip, rate=3/h, block=True).
#: 여기 적는 이유는 **시험이 그 수를 못박기 위해서**다(코드는 이 수를 안 안다).
#: 한 시험이 이 수보다 많이 부르면 색이 벽시계로 바뀐다 — 아래는 전부 2회 이하다.
FORGOT_LIMIT_PER_HOUR = 3

#: 시험 계정의 비밀번호. dj-core 의 is_strong_password 를 통과해야 해서 길다.
OLD_PW = "GxWalk-Old-2026!aa"
NEW_PW = "GxWalk-New-2026!bb"

#: 링크를 **정규식 없이** 찾는다 — 이 저장소의 도구가 heredoc 안의 백슬래시를
#: 벗겨서, 정규식을 쓰면 파일이 조용히 다른 뜻이 된다(기록된 함정).
MARK = "/reset-password?token="
#: 토큰이 끝나는 자리. 따옴표·꺾쇠·공백·앰퍼샌드에서 끊는다.
STOPS = " " + chr(34) + chr(39) + "<>&" + chr(10) + chr(13) + chr(9)


@override_settings(CACHES=LOCMEM)
class PasswordResetWalkTest(TestCase):
    """한 사람이 비밀번호를 잊고 **혼자** 돌아오기까지."""

    def setUp(self) -> None:
        from django.core.cache import caches

        #: django_ratelimit 이 읽는 별칭과 같은 별칭을 비운다 — 안 비우면
        #: 「벽시계 위 어디에 서느냐」로 색이 바뀐다(SEC-21 이 먼저 겪은 자리).
        caches["default"].clear()
        RecordingBackend.sent = []
        #: ★ **부르는 자리의 이름을 가로챈다.** 정의된 자리
        #:   (core.notifications.backends...)를 갈아 끼우면 auth.py 가 import 시점에
        #:   붙들어 둔 옛 이름이 그대로 살아 **아무것도 안 잡힌다.**
        patcher = mock.patch("core.api.v1.auth.SMTPEmailBackend", RecordingBackend)
        patcher.start()
        self.addCleanup(patcher.stop)

    # ── 도우미 ───────────────────────────────────────────────────────────
    def _user(self, name: str, email: str):
        CoreUser = apps.get_model("user", "CoreUser")
        return CoreUser.objects.create_user(
            username=name, password=OLD_PW, is_active=True, email=email)

    def _post(self, path: str, body: dict, addr: str = "10.255.255.90"):
        client = Client(REMOTE_ADDR=addr, **NO_CACHE)
        return client.post(path, data=body, content_type="application/json")

    def _mail_text(self) -> str:
        self.assertEqual(1, len(RecordingBackend.sent),
                         "보낼 메일이 만들어지지 않았다")
        return str(RecordingBackend.sent[0].get("body") or "")

    def _link_token(self) -> str:
        blob = self._mail_text()
        at = blob.find(MARK)
        self.assertNotEqual(
            -1, at,
            "메일 본문에 재설정 링크가 없다 — 받은 사람이 할 수 있는 일이 0이다")
        rest = blob[at + len(MARK):]
        cut = len(rest)
        for ch in STOPS:
            here = rest.find(ch)
            if here != -1:
                cut = min(cut, here)
        return rest[:cut]

    # ── ① 있는 주소 ──────────────────────────────────────────────────────
    def test_a_known_address_produces_one_mail_with_a_link(self) -> None:
        user = self._user("gxtest_p290_known", "gxtest_p290_known@test.invalid")
        r = self._post(FORGOT, {"email": user.email})
        self.assertEqual(200, r.status_code, r.content[:300])
        self.assertTrue(self._link_token(), "링크는 있는데 토큰이 비었다")

    # ── ② 없는 주소 — **답이 같아야 하고 메일은 0통** ────────────────────
    def test_an_unknown_address_answers_the_same_and_sends_nothing(self) -> None:
        user = self._user("gxtest_p290_enum", "gxtest_p290_enum@test.invalid")
        known = self._post(FORGOT, {"email": user.email})
        known_body = known.content
        RecordingBackend.sent = []

        unknown = self._post(FORGOT, {"email": "gxtest_p290_nobody@test.invalid"})

        self.assertEqual(known.status_code, unknown.status_code,
                         "있는 주소와 없는 주소의 상태 코드가 다르다 — 그 차이로 "
                         "회원 명단을 셀 수 있다")
        self.assertEqual(known_body, unknown.content,
                         "있는 주소와 없는 주소의 본문이 다르다 — 같은 화면이 아니다")
        self.assertEqual(0, len(RecordingBackend.sent),
                         "없는 주소에 메일을 만들었다")

    # ── ③ 링크 앞머리는 **설정한 주소**에서 온다 ─────────────────────────
    def test_the_link_prefix_comes_from_the_configured_address(self) -> None:
        """손으로 박은 주소가 아니라 AdminConfig System 의 frontendUrl 이 정한다.

        ⚠ 이 시험은 **지금의 값을 못박지 않는다.** 지금 그 칸은 **없어서** dj-core 의
          기본값 http://localhost:3001 (아무도 안 듣는 포트)이 나간다 — 그 상태를
          단언하면 고장이 시험으로 굳는다. 여기서 재는 것은 **칸이 링크를 정한다**는
          배선이고, 그래야 칸을 채우는 날 링크가 따라 움직인다.
        """
        AdminConfig = apps.get_model("configuration", "AdminConfig")
        row, _ = AdminConfig.objects.get_or_create(
            name="System", defaults={"settings": {}})
        conf = dict(row.settings or {})
        conf["frontendUrl"] = "http://gx-test-front.invalid:8500"
        row.settings = conf
        row.save(update_fields=["settings"])

        user = self._user("gxtest_p290_url", "gxtest_p290_url@test.invalid")
        self._post(FORGOT, {"email": user.email})

        self.assertIn(
            "http://gx-test-front.invalid:8500" + MARK, self._mail_text(),
            "설정한 주소가 링크에 안 실렸다 — 칸을 채워도 고객이 받는 링크는 "
            "안 바뀐다는 뜻이다")

    # ── ④ 한 바퀴 — **새 비밀번호로 로그인까지** ─────────────────────────
    def test_the_token_resets_and_the_new_password_logs_in(self) -> None:
        user = self._user("gxtest_p290_walk", "gxtest_p290_walk@test.invalid")
        self._post(FORGOT, {"email": user.email})
        token = self._link_token()

        done = self._post(RESET, {"token": token, "new_password": NEW_PW})
        self.assertEqual(200, done.status_code, done.content[:300])

        #: ★ 옛 비밀번호가 **안 듣는지**를 먼저 본다. 새 것만 재면 「둘 다 듣는」
        #:   상태가 초록으로 지나간다 — 그것은 재설정이 아니라 **추가**다.
        old = self._post(LOGIN, {"username": user.username, "password": OLD_PW})
        self.assertNotEqual(200, old.status_code,
                            "옛 비밀번호가 아직 듣는다 — 바꾼 것이 아니라 더한 것이다")

        new = self._post(LOGIN, {"username": user.username, "password": NEW_PW})
        self.assertEqual(200, new.status_code,
                         "새 비밀번호로 로그인이 안 된다 — 한 바퀴가 안 돈다: "
                         + repr(new.content[:300]))

    # ── ⑤ 음성 대조 — 같은 토큰은 두 번 안 듣는다 ───────────────────────
    def test_the_token_is_one_shot(self) -> None:
        user = self._user("gxtest_p290_once", "gxtest_p290_once@test.invalid")
        self._post(FORGOT, {"email": user.email})
        token = self._link_token()

        first = self._post(RESET, {"token": token, "new_password": NEW_PW})
        self.assertEqual(200, first.status_code, first.content[:300])

        again = self._post(RESET, {"token": token,
                                   "new_password": "GxWalk-Third-2026!cc"})
        self.assertNotEqual(
            200, again.status_code,
            "쓴 토큰이 또 듣는다 — 메일함을 한 번 본 사람이 언제든 다시 바꾼다")

    # ── ⑥ 음성 대조 — 지어낸 토큰 ────────────────────────────────────────
    def test_a_made_up_token_is_refused(self) -> None:
        r = self._post(RESET, {"token": "gx-not-a-real-token-0000",
                               "new_password": NEW_PW})
        self.assertNotEqual(200, r.status_code, "아무 토큰이나 받아 준다")
