# -*- coding: utf-8 -*-
"""SEC-21 — 로그인 율제한 초과 응답은 **429 · JSON · 한국어 · 남은 초**다 (턴 T · 차선 F).

착수 전 모양 [실측 2026-09-17 · 이 파일의 첫 판 · Django 테스트 클라이언트]
------------------------------------------------------------------------
    1~5회째  400 · application/json · {"success": false, "message": {...}}
    6회째    **403 · text/html · "<h1>403 Forbidden</h1>" · Retry-After 없음**
    7회째    〃

`django_ratelimit.exceptions.Ratelimited`(`PermissionDenied` 의 자식)를 Django 가
영문 HTML 403 으로 옮겼다. 화면은 403 을 「접근 권한 없음 · 관리자 문의」로 읽는다 —
사람이 할 일은 **기다림**인데 화면이 다른 일을 시켰다.

이 파일이 못박는 것 다섯
------------------------
  1) 여섯 번째 부름이 **429** 다 — 403 이 아니다 (권한이 아니라 빈도다)
  2) 본문이 **JSON** 이고 `message` 가 **한국어 한 문장**이다 — 영문 HTML 0
  3) `retry_after_seconds` 가 **양의 정수**이고 `Retry-After` 헤더와 같다 —
     그리고 문장 안의 수와 같다(화면이 읽는 수와 사람이 읽는 수가 하나다)
  4) 그 초는 **측정**이다(`retry_after_source == "measured"`) — 짐작(60)이 아니다.
     율제한 창(1분)보다 크지 않다
  5) 음성 대조 — 1~5회째는 이 겹이 **한 자도 안 만진다**(400 그대로)

캐시 처리: 우회 — 응답 캐시는 `tests.no_cache.NO_CACHE` 로 우회하고, 율제한 **계수**는
`override_settings(CACHES=locmem)` 에 산다(D-341). 운영 Redis 에
이 시험의 계수를 남기면 같은 주소의 실제 로그인이 1분 막힌다. 그래서 **시험 안의 캐시**로
가른다(주소도 `10.255.255.77` 로 따로 둔다). 로그인 계정은 **없는 이름**이다 — 실계정의
실패 횟수(5회 잠금)를 올리지 않는다.

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import json
import re

from django.test import Client, TestCase, override_settings

from common.rate_limit_body import (
    RATE_LIMITED_CODE,
    RateLimitBodyMiddleware,
    rate_limited_message,
)
from tests.no_cache import NO_CACHE

LOCMEM = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sec21-lane-f",
    }
}
ADDR = "10.255.255.77"
LOGIN = "/api/v1/auth/login"
NOBODY = {"username": "no_such_user_sec21", "password": "not-a-real-password"}

#: dj-core `core/api/v1/auth.py:348` — `@ratelimit(key='ip', rate='5/m', block=True)`.
#: 여기 다시 적는 이유는 **시험이 그 수를 못박기 위해서**다(코드는 이 수를 안 안다).
LIMIT_PER_MINUTE = 5


@override_settings(CACHES=LOCMEM)
class LoginRateLimitBodyTest(TestCase):
    def _post(self, client: Client):
        return client.post(LOGIN, data=NOBODY, content_type="application/json")

    def test_middleware_is_installed(self):
        from django.conf import settings

        self.assertIn("common.rate_limit_body.RateLimitBodyMiddleware", settings.MIDDLEWARE)

    def test_sixth_login_is_429_json_korean_with_seconds(self):
        client = Client(**NO_CACHE, REMOTE_ADDR=ADDR)

        # ⑤ 음성 대조 — 상한 안에서는 이 겹이 말하지 않는다.
        for _ in range(LIMIT_PER_MINUTE):
            r = self._post(client)
            self.assertEqual(r.status_code, 400, r.content[:200])
            self.assertIn("application/json", r["Content-Type"])

        # ①② 여섯 번째 — 429 · JSON.
        r = self._post(client)
        self.assertEqual(r.status_code, 429, r.content[:200])
        self.assertIn("application/json", r["Content-Type"])
        body = json.loads(r.content.decode("utf-8"))
        self.assertIs(body["success"], False)
        self.assertEqual(body["status"], 429)
        self.assertEqual(body["code"], RATE_LIMITED_CODE)
        self.assertNotIn(b"<html", r.content.lower())
        self.assertNotIn("Forbidden", body["message"])

        # ③ 남은 초 — 본문 · 헤더 · 문장이 **한 수**다.
        left = body["retry_after_seconds"]
        self.assertIsInstance(left, int)
        self.assertGreater(left, 0)
        self.assertEqual(r["Retry-After"], str(left))
        self.assertEqual(body["message"], rate_limited_message(left))
        m = re.search(r"(\d+)초 뒤", body["message"])
        self.assertIsNotNone(m, body["message"])
        self.assertEqual(int(m.group(1)), left)
        # 한국어 문장이다 — 한글이 들어 있고 영문 단어 문장이 아니다.
        self.assertRegex(body["message"], r"[가-힣]")

        # ④ 측정이다 — 짐작(60)이 아니고, 1분 창을 넘지 않는다.
        self.assertEqual(body["retry_after_source"], "measured")
        self.assertLessEqual(left, 60)

        # 일곱 번째도 같은 모양이고, 남은 초는 **늘지 않는다**(창은 하나다).
        r2 = self._post(client)
        self.assertEqual(r2.status_code, 429)
        body2 = json.loads(r2.content.decode("utf-8"))
        self.assertLessEqual(body2["retry_after_seconds"], left)

    def test_other_permission_denied_is_untouched(self):
        """`Ratelimited` 가 아닌 `PermissionDenied` 는 이 겹이 None 을 낸다 — 남의 흐름 제어다."""
        from django.core.exceptions import PermissionDenied
        from django.test import RequestFactory

        mw = RateLimitBodyMiddleware(lambda req: None)
        req = RequestFactory().post(LOGIN)
        self.assertIsNone(mw.process_exception(req, PermissionDenied()))
