# -*- coding: utf-8 -*-
"""P-274 — **틀린 자격은 거절한다.** 못 푸는 `Bearer` 가 500 이 아니라 401 인가 (턴 AG).

캐시 처리: 우회 — `tests/no_cache.NO_CACHE`(`X-No-Cache`)를 실은 `Client` 로 때린다.
**우회여야 하는 까닭**: 이 시험이 묻는 것은 「이 요청이 **지금** 무슨 상태를 내는가」인데,
응답 캐시가 적중하면 지난 본문이 그대로 돌아온다 — 겹을 끄고 켠 A/B 가 **같은 수**를
내면 그 A/B 는 아무것도 안 잰 것이다 (D-341 착시 ⑦).

무엇을 잠그는가
----------------
[실측 2026-09-23 · 턴 AF] 아무 글자나 실은 `Authorization: Bearer` 하나로 읽기 면
**364자리 전부가 HTTP 500** 이었다. 자료는 안 샜지만 그 0 은 「거절해서」가 아니라
**「죽어서」**였고, 지켜보는 사람이 「막혔다」와 「죽었다」를 구별할 수 없었다.

뿌리는 dj-core(`site-packages/core/middleware/refresh_token.py`)의 `except` 갈래가
`jwt.decode` 를 **try 없이** 다시 부르는 것이다 — §0.4 라 한 줄도 못 고친다.
그래서 `common/jwt_guard.py` 를 **그보다 바깥**에 세웠다.

★ 이 파일이 지키는 것은 「401 이 난다」가 아니라 **「바뀐 것이 그것 하나뿐이다」**이다.
  겹을 켜고 끈 A/B 로 잰다 — 진짜 토큰의 답이 켬·끔에서 **같아야** 한다.
  같지 않으면 이 겹은 고치는 게 아니라 **새 문을 잠근 것**이다.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from ninja_jwt.tokens import AccessToken

from common import jwt_guard
from tests.no_cache import NO_CACHE

#: 아무 데도 없는 글자 — 실토큰을 안 쓴다(로그인 0회 · 잠금 계수기 0).
GARBAGE = "gx.nonexistent.probe.token.do-not-issue-this"

#: 모양은 JWT 인데 **서명이 틀린** 글자. 턴 AG 의 첫 판이 이것을 **놓쳤다** —
#: 「구조적으로 못 푸는가」만 물었더니 이 표본이 그대로 500 이었다.
SHAPED_BAD_SIG = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzAwMDAwMDAwLCJqdGkiOiJhIiwidXNlcl9pZCI6MX0."
    "this_signature_is_not_valid"
)

PROBE_PATH = "/api/dsm/events"


def _client():
    return Client(raise_request_exception=False, **NO_CACHE)


def _fake_request(meta):
    """`META` 만 가진 최소 요청. 겹의 헤더 읽기를 HTTP 없이 가른다."""
    return type("R", (), {"META": dict(meta)})()


class TheGuardAnswersInsteadOfDying(TestCase):
    """★ 출생 표본 — 이 파일을 만들게 한 바로 그 사례 (D-310).

    [실측 2026-09-23 · 턴 AF] `Bearer gx.nonexistent...` 한 줄에 364/364 가 500.
    아래 두 시험이 그 자리다 — **쓰레기 하나로는 부족하다.** 서명만 틀린 표본을
    같이 두지 않으면 「절반만 고친 겹」이 초록으로 지나간다(조율자가 실제로 그랬다).
    """

    def test_garbage_bearer_is_401_not_500(self):
        r = _client().get(PROBE_PATH, HTTP_AUTHORIZATION="Bearer " + GARBAGE)
        self.assertEqual(
            401, r.status_code,
            "쓰레기 `Bearer` 가 401 이 아닙니다(%s). 500 이면 거절이 아니라 고장이고, "
            "고객은 「막혔다」와 「죽었다」를 구별할 수 없습니다." % r.status_code)

    def test_shaped_but_badly_signed_bearer_is_401_not_500(self):
        """★★ 턴 AG 조율자 오판 ① 이 여기서 잡힌다.

        첫 판은 「구조적으로 못 푸는가」만 물었고, 이 표본은 **구조가 멀쩡해서**
        그대로 dj-core 로 갔다가 500 이 났다. 술어를 「dj-core 가 터지는가」로
        바꾼 뒤에야 401 이 된다.
        """
        r = _client().get(PROBE_PATH, HTTP_AUTHORIZATION="Bearer " + SHAPED_BAD_SIG)
        self.assertEqual(
            401, r.status_code,
            "서명만 틀린 `Bearer` 가 401 이 아닙니다(%s). dj-core 의 `except` 갈래는 "
            "**서명을 검사하며** 다시 읽으므로, 「구조 해독」만 보는 술어로는 이 표본이 "
            "빠져나갑니다 — 절반만 고친 겹입니다." % r.status_code)

    def test_no_read_route_answers_500_to_a_wrong_token(self):
        """분모를 손으로 안 적는다 — 살아 있는 라우터에서 읽기 면을 **지금 센다**.

        ★ 이 시험이 「364」라는 수를 박지 않는 까닭: 라우트가 늘면 분모도 늘어야 한다.
          수를 박으면 새로 난 라우트는 **세지지 않고도 초록**이 된다.
        """
        from common.tenant_scope import _iter_ninja_apis, _join

        read_methods = {"GET", "HEAD", "OPTIONS"}
        client, paths = _client(), []
        for mount, api in _iter_ninja_apis():
            for prefix, router in getattr(api, "_routers", []) or []:
                for op_path, pv in (getattr(router, "path_operations", {}) or {}).items():
                    for op in getattr(pv, "operations", []) or []:
                        methods = {str(m).upper() for m in (getattr(op, "methods", []) or [])}
                        if methods & read_methods:
                            paths.append(_join(mount, prefix, op_path))
        self.assertTrue(paths, "읽기 면을 한 자리도 못 셌습니다 — 열거기 고장입니다.")

        five_hundreds = []
        for path in paths:
            url = path.replace("{int:", "{").replace("{str:", "{")
            while "{" in url and "}" in url:
                head, _, rest = url.partition("{")
                _, _, tail = rest.partition("}")
                url = head + "1" + tail
            r = client.get(url, HTTP_AUTHORIZATION="Bearer " + GARBAGE)
            if r.status_code == 500:
                five_hundreds.append(url)
        self.assertEqual(
            [], five_hundreds,
            "틀린 토큰에 **500** 을 내는 읽기 자리가 %d/%d 입니다: %s. "
            "유출 0 과 거절 0 은 다른 수입니다 — 게이트가 세상을 다 말하게 두십시오."
            % (len(five_hundreds), len(paths), five_hundreds[:5]))


class TheGuardChangesNothingElse(TestCase):
    """★★ 음성 대조 — **바뀐 것이 그것 하나뿐인가.**

    401 만 세면 「전부 막아 버린 겹」도 초록이다. 그래서 같은 토큰을 겹 켬·끔으로
    두 번 때려 **진짜 토큰의 답이 같은지**를 본다.
    """

    @classmethod
    def setUpTestData(cls):
        #: ★ `email` 은 **고유 칸**이고 빈 값이 이미 있다 [실측: 빈 이메일로 만들면
        #:   `duplicate key ... user_coreuser_email_key`]. 시험이 남의 행과 부딪히지
        #:   않도록 이 시험만의 주소를 준다 — `.invalid` 는 어디로도 안 가는 도메인이다.
        cls.user = get_user_model()._base_manager.create(
            username="gxtest_p274_subject", email="gxtest_p274_subject@example.invalid")
        cls.real = str(AccessToken.for_user(cls.user))

    def _status(self, token):
        return _client().get(PROBE_PATH, HTTP_AUTHORIZATION="Bearer " + token).status_code

    def test_a_real_token_is_answered_the_same_with_the_guard_on_and_off(self):
        with override_settings(JWT_GUARD_ENABLED=False):
            off = self._status(self.real)
        with override_settings(JWT_GUARD_ENABLED=True):
            on = self._status(self.real)
        self.assertEqual(
            off, on,
            "진짜 토큰의 답이 겹 끔(%s)과 켬(%s)에서 갈립니다. 이 겹은 **거절만** 해야 "
            "하고 받아들이는 자리가 없어야 합니다 — 갈리면 두 번째 인증기가 된 것입니다."
            % (off, on))

    def test_the_guard_predicate_lets_a_real_token_through(self):
        self.assertFalse(
            jwt_guard.would_djcore_raise(self.real),
            "진짜 토큰을 「dj-core 가 터진다」로 읽었습니다 — 이 겹이 정상 요청을 막습니다.")
        self.assertTrue(
            jwt_guard.would_djcore_raise(GARBAGE),
            "쓰레기 토큰을 「안 터진다」로 읽었습니다 — 그러면 dj-core 가 500 을 냅니다.")

    def test_the_rollback_switch_really_rolls_back(self):
        """되돌리기 한 줄이 **진짜로 되돌리는가.** 안 그러면 그것은 되돌리기가 아니다.

        ★ 이 시험이 **500 을 기대한다**는 것이 이상해 보이면 맞다 — 그것이 요점이다.
          겹을 끄면 병이 돌아와야 하고, 안 돌아오면 둘 중 하나다: 병이 이미 사라졌거나
          스위치가 겹을 안 끄거나. **둘은 다른 사실이고 여기서 갈라야 한다.**
        """
        with override_settings(JWT_GUARD_ENABLED=False):
            self.assertEqual(
                500, self._status(GARBAGE),
                "겹을 껐는데도 500 이 아닙니다 — 이 시험이 재는 병이 이미 사라졌거나, "
                "`JWT_GUARD_ENABLED` 가 실제로는 겹을 안 끕니다.")


class TheGuardIgnoresWhatIsNotItsBusiness(TestCase):
    """★ 이 겹이 **안 건드려야** 하는 것들. 여기가 비면 겹은 조용히 넓어진다."""

    def test_a_request_with_no_authorization_header_is_untouched(self):
        r = _client().get(PROBE_PATH)
        self.assertNotEqual(
            500, r.status_code,
            "헤더가 없는 요청이 500 입니다 — 이 겹이 건드릴 자리가 아닙니다.")
        self.assertIsNone(
            jwt_guard.bearer_token(_fake_request({})),
            "헤더가 없는데 토큰을 읽었다고 합니다.")

    def test_an_empty_bearer_is_left_to_the_access_gate(self):
        """빈 `Bearer ` 는 이미 관문이 401 로 답한다 — 같은 사실을 두 겹이 말하지 않는다."""
        self.assertIsNone(
            jwt_guard.bearer_token(_fake_request({"HTTP_AUTHORIZATION": "Bearer "})),
            "빈 `Bearer ` 를 이 겹이 집었습니다. 그 자리는 `access_gate` 의 것이고, "
            "두 겹이 같은 사실을 말하면 한쪽을 고칠 때 다른 쪽이 그 변화를 덮습니다.")

    def test_a_non_bearer_scheme_is_untouched(self):
        self.assertIsNone(
            jwt_guard.bearer_token(_fake_request({"HTTP_AUTHORIZATION": "Basic YWJjOmRlZg=="})),
            "`Basic` 을 이 겹이 집었습니다 — 이 겹은 `Bearer` 만 봅니다.")

    def test_both_header_spellings_are_read(self):
        """dj-core 가 **둘 다** 읽는다 — 한 자리만 보면 다른 자리로 온 글자가 500 이 된다."""
        for key in ("HTTP_AUTHORIZATION", "Authorization"):
            self.assertEqual(
                GARBAGE,
                jwt_guard.bearer_token(_fake_request({key: "Bearer " + GARBAGE})),
                "`%s` 자리로 온 `Bearer` 를 못 읽었습니다 — dj-core 는 이 자리도 읽습니다."
                % key)


class TheAnswerSpeaksTheCustomersLanguage(TestCase):
    """거절은 **고객의 말**로 한다. 기계 낱말만 남기면 화면이 그것을 그대로 그린다."""

    def test_the_401_body_carries_four_languages_and_a_code(self):
        body = _client().get(PROBE_PATH, HTTP_AUTHORIZATION="Bearer " + GARBAGE).json()
        self.assertEqual(401, body.get("status"))
        self.assertEqual(jwt_guard.UNDECODABLE_CODE, body.get("code"))
        for lang in ("ko", "en", "vi", "th"):
            self.assertTrue(
                (body.get("message") or {}).get(lang),
                "답 본문에 `%s` 말이 없습니다 — dj-core 의 답 모양과 같아야 앞단이 읽습니다."
                % lang)

    def test_the_401_is_not_cached_and_says_what_to_come_back_with(self):
        r = _client().get(PROBE_PATH, HTTP_AUTHORIZATION="Bearer " + GARBAGE)
        self.assertEqual("no-store", r.headers.get("Cache-Control"),
                         "401 이 캐시되면 자격을 고쳐 와도 같은 거절이 돌아옵니다.")
        self.assertIn("Bearer", r.headers.get("WWW-Authenticate", ""),
                      "401 인데 무엇으로 다시 오라는 말이 없습니다.")

    def test_the_setting_name_is_the_one_the_comment_promises(self):
        """되돌리기 한 줄의 이름이 **settings 주석과 같은가.** 다르면 그 주석이 거짓이다."""
        self.assertEqual("JWT_GUARD_ENABLED", jwt_guard.SETTING_NAME)
        self.assertTrue(
            jwt_guard.enabled() or hasattr(settings, "JWT_GUARD_ENABLED"),
            "기본값이 꺼짐입니다 — 새 겹은 켜져야 일을 합니다.")
