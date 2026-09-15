# -*- coding: utf-8 -*-
"""P-100 — **권한 거절이 500 이 아니고, 5xx 본문에 내부가 없다** (2026-09-07 · 차선 B).

이 파일이 못박는 것은 둘이다.

  (a) **그 라우트**  `GET /api/report-template/` 는 권한 없는 계정에게 **403** 이다.
      500 이 아니다. 401·403 은 5xx 가 아니고, 인가 판정의 답이 서버 결함일 수 없다.

  (b) **전역 규칙**  어떤 5xx 본문에도 `Traceback` · `pydantic` · `File "` ·
      내부 파일경로가 **한 자도 없다.** 이것이 (a)보다 중요한 절반이다 —
      (a)는 라우트 하나고 (b)는 모든 라우트다.

출생 표본 — **고치기 전에 실제로 잰 것** [2026-09-07 · gxseed_u4_official(view_only)]
--------------------------------------------------------------------------------
    GET http://localhost:8000/api/report-template/  ->  HTTP 500 · text/plain · 951바이트
        Traceback (most recent call last):
          File "/usr/local/lib/python3.11/site-packages/ninja_extra/operation.py", line 216, in run
          File "/usr/local/lib/python3.11/site-packages/ninja/operation.py", line 280, in _result_to_response
        ...
    표지 넷 중 넷이 다 있었다.  원문: `docs/agent/evidence/P-100/before.json`

아래 `BIRTH_SAMPLE` 이 그 본문의 앞머리다. **판정기가 이것을 못 잡으면 도구가 아니다**
(D-310 의 방식 그대로 — 양성 대조를 시험 안에 둔다).

절대 금지 (AGENT_LOOP 절대금지 #4)
    이 파일의 시험을 skip·xfail 하지 말 것.

실행
    python manage.py test tests.test_p100_error_body -v 2
"""

from __future__ import annotations

import json

from django.http import HttpResponse, JsonResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings

from common.error_body import (
    LEAK_MARKERS,
    SafeErrorBodyMiddleware,
    leak_markers,
    safe_payload,
    scrub_applies,
)
from tests.no_cache import NO_CACHE
from tests.test_api_contract import _DeniedUserMixin, _bearer

#: 고치기 전 그 본문의 앞머리 [실측 2026-09-07]. 한 글자도 지어내지 않았다.
BIRTH_SAMPLE = (
    'Traceback (most recent call last):\n'
    '  File "/usr/local/lib/python3.11/site-packages/ninja_extra/operation.py", line 216, in run\n'
    '    _processed_results = self._result_to_response(\n'
    '  File "/usr/local/lib/python3.11/site-packages/ninja/operation.py", line 280, '
    'in _result_to_response\n'
    '    validated_object = response_model.model_validate(\n'
    'pydantic_core._pydantic_core.ValidationError: 1 validation error for NinjaResponseSchema\n'
)

#: 지시가 이름으로 못박은 네 표지. 이 시험이 세는 것은 정확히 이 넷이다.
FOUR_MARKERS = ("Traceback", "pydantic", 'File "', "internal_path")

#: P-100 (a) 의 그 라우트. 화면과 게이트가 부르는 그 경로 그대로.
ROUTE_REPORT_TEMPLATE = "/api/report-template/"


# =============================================================================
# 1) 판정 함수 — **순수 함수만 본다** (D-277). 양성 대조 · 음성 대조 둘 다
# =============================================================================
class LeakMarkerTest(SimpleTestCase):
    """`leak_markers()` 가 출생 표본을 잡는가, 그리고 멀쩡한 본문을 안 잡는가."""

    def test_birth_sample_trips_all_four_markers(self):
        """**양성 대조** — 2026-09-07 의 그 본문에서 넷이 다 나와야 한다."""
        found = leak_markers(BIRTH_SAMPLE)
        for marker in FOUR_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, found, "출생 표본에서 %r 를 못 잡는다" % marker)

    def test_clean_denial_body_has_no_markers(self):
        """**음성 대조** — 거절 봉투에는 표지가 하나도 없다. 여기서 뭔가 나오면 판정이 넓다."""
        body = json.dumps({"success": False, "status_code": 403,
                           "message": {"ko": "권한이 거부되었습니다."}}, ensure_ascii=False)
        self.assertEqual(leak_markers(body), [])

    def test_safe_payload_itself_is_clean(self):
        """우리가 내보내는 본문이 표지를 갖고 있으면 이 도구는 자기 꼬리를 문다."""
        self.assertEqual(leak_markers(json.dumps(safe_payload(500), ensure_ascii=False)), [])

    def test_internal_paths_are_markers(self):
        for text in ("at /app/backend/config/settings.py line 3",
                     "/usr/local/lib/python3.11/site-packages/ninja/operation.py",
                     r"C:\GuardianX\guardianx-source\backend\common\error_body.py"):
            with self.subTest(text=text):
                self.assertIn("internal_path", leak_markers(text))

    def test_bytes_and_nonsense_do_not_crash(self):
        self.assertEqual(leak_markers(b"{}"), [])
        self.assertEqual(leak_markers(None), [])
        self.assertEqual(leak_markers(17), [])

    def test_marker_names_are_the_four_the_order_asked_for(self):
        """표지 이름을 조용히 바꾸지 않는다 — 게이트가 이 이름으로 센다."""
        self.assertEqual(tuple(LEAK_MARKERS), ("Traceback", "pydantic", 'File "'))


class ScrubScopeTest(SimpleTestCase):
    """**어디까지 갈아 끼우나** — 규칙을 한 곳에서만 정했다는 것을 못박는다."""

    def test_production_scrubs_everywhere(self):
        for path in ("/api/report-template/", "/admin/", "/", "/static/x.js"):
            with self.subTest(path=path):
                self.assertTrue(scrub_applies(path, debug=False))

    def test_development_scrubs_api_only(self):
        self.assertTrue(scrub_applies("/api/report-template/", debug=True))
        self.assertFalse(scrub_applies("/admin/", debug=True))

    @override_settings(SAFE_ERROR_BODY=False)
    def test_revert_lever_turns_everything_off(self):
        """되돌리기 한 줄 (D-212). 꺼지면 어떤 경로에서도 안 만진다."""
        for debug in (True, False):
            for path in ("/api/report-template/", "/admin/"):
                with self.subTest(debug=debug, path=path):
                    self.assertFalse(scrub_applies(path, debug=debug))


# =============================================================================
# 2) 응답 단계 그물 — ninja 를 안 타는 5xx 까지 덮는가
# =============================================================================
class SafeErrorBodyMiddlewareTest(SimpleTestCase):
    """미들웨어 한 겹만 놓고 잰다. 라우팅도 DB 도 안 쓴다."""

    def setUp(self):
        self.rf = RequestFactory()

    def _run(self, response, path="/api/anything"):
        mw = SafeErrorBodyMiddleware(lambda request: response)
        return mw(self.rf.get(path))

    @override_settings(DEBUG=True)
    def test_leaky_500_body_is_replaced(self):
        out = self._run(HttpResponse(BIRTH_SAMPLE, status=500, content_type="text/plain"))
        self.assertEqual(leak_markers(out.content), [], "본문에 내부가 남았다")

    @override_settings(DEBUG=True)
    def test_status_line_is_not_touched(self):
        """**500 을 200 으로 만들지 않는다.** 이 겹이 하는 것은 본문뿐이다."""
        out = self._run(HttpResponse(BIRTH_SAMPLE, status=500, content_type="text/plain"))
        self.assertEqual(out.status_code, 500)
        self.assertIs(json.loads(out.content).get("success"), False)

    @override_settings(DEBUG=True)
    def test_clean_5xx_body_is_left_alone(self):
        """표지가 없으면 한 자도 안 만진다 — 서비스가 쓴 503 사유가 지워지면 안 된다."""
        body = json.dumps({"success": False, "status_code": 503, "message": "저장소 연결 없음"},
                          ensure_ascii=False)
        out = self._run(HttpResponse(body, status=503, content_type="application/json"))
        self.assertEqual(json.loads(out.content).get("message"), "저장소 연결 없음")

    @override_settings(DEBUG=True)
    def test_2xx_and_4xx_are_left_alone(self):
        for status in (200, 403, 404, 422):
            with self.subTest(status=status):
                out = self._run(JsonResponse({"ok": status}, status=status))
                self.assertEqual(json.loads(out.content), {"ok": status})

    @override_settings(DEBUG=True, SAFE_ERROR_BODY=False)
    def test_revert_lever_leaves_the_leak_alone(self):
        """되돌리면 앞판 그대로다 — 되돌림이 실제로 되는지를 시험이 증명한다(D-212)."""
        out = self._run(HttpResponse(BIRTH_SAMPLE, status=500, content_type="text/plain"))
        self.assertIn("Traceback", out.content.decode())

    @override_settings(DEBUG=True)
    def test_streaming_response_is_not_consumed(self):
        """스트리밍 본문은 만지면 소비된다. 손대지 않는 것이 옳다."""
        from django.http import StreamingHttpResponse

        resp = StreamingHttpResponse(iter([b"x", b"y"]), status=500)
        out = self._run(resp)
        self.assertEqual(b"".join(out.streaming_content), b"xy")


# =============================================================================
# 3) 살아 있는 라우트 — **HTTP 를 실제로 때린다** (착시 (9) 방지)
# =============================================================================
class ReportTemplateDenialTest(_DeniedUserMixin, TestCase):
    """P-100 (a) — 권한 없는 계정에게 `GET /api/report-template/` 가 무엇을 내는가.

    ★ 단위 시험으로는 못 잡는 자리다. 이 결함은 **라우트가 응답 스키마로 검증하는
      순간**에 났고, 서비스 함수를 직접 부르는 시험은 그 자리를 지나지 않는다
      (착시 (9)). 그래서 여기서는 HTTP 를 때린다.

    캐시 처리: 우회 — X-No-Cache (D-341 착시 (7)). 캐시 적중 본문은 언제나 200 이라
    이 시험이 캐시를 재면 조용히 초록이 된다.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = cls._make_denied_user("p100_denied")

    def setUp(self):
        self.client = Client(**NO_CACHE)
        self.headers = _bearer(self.user)

    def test_denial_is_403_not_500(self):
        """**401·403 != 5xx.** 인가 판정의 답이 서버 결함일 수 없다."""
        resp = self.client.get(ROUTE_REPORT_TEMPLATE, **self.headers)
        self.assertEqual(resp.status_code, 403,
                         "권한 거절이 %s 다 — 500 이면 P-100 이 되살아났다" % resp.status_code)

    def test_denial_body_has_zero_traceback_markers(self):
        """P-100 (b) — 넷 중 **하나도** 없어야 한다."""
        resp = self.client.get(ROUTE_REPORT_TEMPLATE, **self.headers)
        found = leak_markers(resp.content)
        self.assertEqual(found, [], "거절 본문에 내부가 실렸다: %s" % found)

    def test_denial_body_still_says_it_was_denied(self):
        """상태만 고치고 **거부 사실을 지우지 않는다** (W0-18 · 200+{} 로 되돌아가지 않는다)."""
        resp = self.client.get(ROUTE_REPORT_TEMPLATE, **self.headers)
        body = json.loads(resp.content)
        self.assertIs(body.get("success"), False)
        self.assertEqual(body.get("status_code"), 403)

    def test_unauthenticated_is_401_not_500(self):
        """인증이 없으면 401 이다. 이것도 5xx 가 아니다."""
        resp = Client(**NO_CACHE).get(ROUTE_REPORT_TEMPLATE)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(leak_markers(resp.content), [])
