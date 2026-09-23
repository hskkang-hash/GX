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

★ 「혼자 재면 통과」함정 (턴 AE · 차선 S · 실측 2026-09-23)
------------------------------------------------------------
`LocMemCache` 는 `LOCATION` 문자열을 키로 한 **프로세스 전역** 딕셔너리를 쓴다
(`django.core.cache.backends.locmem._caches`). `override_settings(CACHES=LOCMEM)` 이
클래스마다 새 백엔드 객체를 만들어도 `LOCATION="sec21-lane-f"` 가 같으면 **같은
전역 딕셔너리**를 돌려받는다 — 그래서 이 시험을 어제 전량 안에서 돌리면(다른 시험이
같은 창 안에서 방금 로그인을 몇 번 했으면) 계수가 이미 차 있어 **여섯 번째보다
먼저** 429 가 나거나, 반대로 여섯 번째에도 아직 안 차 있어 400 이 나올 수 있다 —
**벽시계 위 어디에 서느냐로 색이 바뀐다.** `django_ratelimit.core.get_usage` 는
`caches[getattr(settings, "RATELIMIT_USE_CACHE", "default")]` 를 읽는다(실측:
`RATELIMIT_USE_CACHE` 는 이 저장소 어디에도 없다 → 별칭은 `"default"`) — 이 클래스가
덮은 `CACHES["default"]` 와 **같은 별칭**이다. 그래서 `setUp` 은 정확히
`caches["default"].clear()` 를 부른다(전역 `django.core.cache.cache` 가 아니라 —
그건 이 클래스 밖에서 import 되면 override 이전 별칭을 붙들 수 있다).

음성 대조(이 파일의 진짜 닫는 조건)는 `test_prefilled_counter_makes_first_call_429`
다: 계수를 일부러 채운 뒤 **다른 클라이언트**(같은 IP)로 「첫」 부름을 해도 429 가
와야 한다 — 그래야 이 시험이 실제로 그 캐시를 재고 있다는 뜻이다. 이 시험이
빨강이면(즉 채워도 400) 위 여섯째-시험은 통과해도 아무것도 안 잰 것이다.

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
    def setUp(self):
        # ★ 시험 사이에 계수를 비운다 — `LOCATION="sec21-lane-f"` 는 프로세스 전역
        # 딕셔너리를 가리키므로, 안 비우면 「벽시계 위 어디에 서느냐」로 색이 바뀐다
        # (턴 AE 실측: 어제 전량 실패 · 오늘 전량 통과 · 코드는 그대로였다).
        # `django_ratelimit` 이 읽는 별칭과 **같은 별칭**("default")을 비운다 — 실측:
        # `RATELIMIT_USE_CACHE` 설정이 이 저장소 어디에도 없어 기본값 "default" 다.
        from django.core.cache import caches

        caches["default"].clear()

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

    # ── 음성 대조 표본 1 (턴 AE · P-255) ─────────────────────────────────────
    #
    # 아래 두 시험은 **함께** 서야 「고쳤다」다. 하나만 서면 이 파일은 여전히
    # 「혼자 재면 통과」다.

    def test_cleared_counter_needs_five_before_sixth_is_429(self):
        """양성 대조 — `setUp` 이 비운 직후에는 다섯째까지 400 이고 여섯째만 429 다.

        (위 `test_sixth_login_is_429_...` 와 같은 방향이지만, 그 시험의 온갖 부가
        단언과 분리해 이 방향 하나만 짧게 못박아 둔다 — 아래 음성 대조와 나란히
        읽히도록.)
        """
        client = Client(**NO_CACHE, REMOTE_ADDR=ADDR)
        for i in range(LIMIT_PER_MINUTE):
            r = self._post(client)
            self.assertEqual(r.status_code, 400, f"{i+1}번째: {r.content[:200]!r}")
        r = self._post(client)
        self.assertEqual(r.status_code, 429, r.content[:200])

    def test_prefilled_counter_makes_first_call_429(self):
        """음성 대조 — 계수를 일부러 채운 뒤에는 **새 클라이언트의 첫 부름**도 429 다.

        `setUp` 이 막 비웠어도, 이 시험 안에서 다시 `LIMIT_PER_MINUTE` 번을 태워
        채우면(= 「앞 시험이 방금 로그인을 몇 번 했다」를 흉내) 그 다음은 같은 IP
        위에서는 클라이언트 객체가 달라져도(= 다른 시험이라고 흉내) 429 다 — 율제한은
        세션이 아니라 **IP·창**으로 센다. 이 시험이 초록이어야 이 파일이 실제로
        `caches["default"]`(`LOCATION="sec21-lane-f"`)를 재고 있다는 뜻이다. 이 시험이
        빨강이면(즉 채워도 여전히 400 이 나오면) 위 시험들은 캐시를 안 재는 —
        아무것도 검증 못 하는 — 시험이다.
        """
        priming_client = Client(**NO_CACHE, REMOTE_ADDR=ADDR)
        for i in range(LIMIT_PER_MINUTE):
            r = self._post(priming_client)
            self.assertEqual(r.status_code, 400, f"채우는 중 {i+1}번째: {r.content[:200]!r}")

        # 새 클라이언트(같은 IP) — 이 클라이언트 기준으로는 "첫" 부름이다.
        fresh_client = Client(**NO_CACHE, REMOTE_ADDR=ADDR)
        r = self._post(fresh_client)
        self.assertEqual(r.status_code, 429, r.content[:200])
        body = json.loads(r.content.decode("utf-8"))
        self.assertEqual(body["code"], RATE_LIMITED_CODE)
