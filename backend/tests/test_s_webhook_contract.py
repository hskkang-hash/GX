# -*- coding: utf-8 -*-
"""SEC-16 — 웹훅 서명·재시도 규약 회귀 시험 (차선 S · 2026-09-05).

이 파일이 왜 생겼나
    나가는 웹훅은 아직 **0개**다(문은 UX-19 가 낸다). 문이 먼저 서면 규약은 문에 맞춰
    지어지고, 그때 규약은 규약이 아니라 「지금 보내는 모양의 기록」이 된다.
    그래서 **규약을 먼저 짓고 시험으로 못박는다.**

무엇을 재는가 — 정본 `docs/agent/evidence/D-346/ga_readiness.yaml` SEC-16 의 닫는 조건 셋
    ① 서명 불일치 **거절**
    ② **5회 뒤 포기 기록**
    ③ 스키마 버전 헤더 **부재 거절**

무엇을 못 재는가 (D-301 — 못 재는 것을 적는다)
    · **실제 발송을 재지 않는다.** 나가는 웹훅이 0개라 때릴 문이 없다. 이 파일은
      규약 함수를 직접 부른다 — 문이 서면(UX-19) 그 문이 이 함수를 부르는지는
      `scripts/verify_webhook_contract.py` 가 소스에서 잰다.
    · **네트워크를 재지 않는다.** 재시도는 `RetryPolicy` 의 셈으로 잰다(sleep 없음).
      실제 타임아웃은 `common/external_http.py` 가 `settings.EXTERNAL_HTTP_TIMEOUT`
      으로 답한다 — 여기서 숫자를 다시 적지 않는다(D-212).
    · **키 보관처를 재지 않는다.** 서명키가 어디 사는지는 F-05 구독 등록(UX-19)의 몫이다.
      이 파일은 「키가 없으면 통과시키지 않는다」만 못박는다.

캐시 처리: **해당 없음** — HTTP 를 때리지 않는다. 순수 함수만 부른다 (D-341 규약).

절대 금지 (AGENT_LOOP 절대금지 #4 · D-105)
    이 파일의 시험을 skip·xfail·비활성화하지 말 것.

실행
    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \\
      python -m pytest tests/test_s_webhook_contract.py -q --nomigrations -p no:randomly
"""

from __future__ import annotations

import json

from django.test import SimpleTestCase

from common.webhook_contract import (
    EVENT_ID_HEADER,
    GIVEUP_EXHAUSTED,
    GIVEUP_REJECTED,
    MAX_ATTEMPTS,
    REJECT_BAD_SCHEMA,
    REJECT_BAD_SIGNATURE_FORM,
    REJECT_BAD_TIMESTAMP,
    REJECT_NO_SCHEMA,
    REJECT_NO_SECRET,
    REJECT_NO_SIGNATURE,
    REJECT_NO_TIMESTAMP,
    REJECT_SIGNATURE_MISMATCH,
    REJECT_STALE_TIMESTAMP,
    RetryPolicy,
    RETRYABLE_STATUS,
    SCHEMA_HEADER,
    SCHEMA_VERSION,
    SIGNATURE_HEADER,
    SIGNATURE_PREFIX,
    SUPPORTED_SCHEMA_VERSIONS,
    TIMESTAMP_HEADER,
    TIMESTAMP_TOLERANCE_SECONDS,
    attempts_from,
    giveup_record,
    outbound_headers,
    sign,
    verify,
)


class WebhookFixture(SimpleTestCase):
    """규약 시험의 공통 자리. DB 를 쓰지 않는다 — 규약은 순수 함수다."""

    SECRET = "s_구독별_서명키_이것은_시험값이다"
    NOW = 1_800_000_000.0

    def body(self, **extra) -> bytes:
        """CAP 1.2 를 흉내 낸 최소 본문. 규약은 본문 내용을 안 본다 —
        내용은 UX-19(CAP 1.2)의 몫이고 여기는 **바이트만** 본다."""
        payload = {"identifier": "s_evt_1", "msgType": "Alert", "status": "Actual"}
        payload.update(extra)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")

    def good_headers(self, body: bytes | None = None, **over) -> dict[str, str]:
        body = self.body() if body is None else body
        headers = outbound_headers(self.SECRET, body, event_id="s_evt_1",
                                   timestamp=str(int(self.NOW)))
        headers.update(over)
        return headers


# ═══════════════════════════════════════════════════════════════════════════
# 0) 양성 대조 — **먼저 통과하는 것을 보인다**
#    이것이 없으면 「전부 거절」이 규약처럼 보인다. 전부 거절하는 검증기는
#    규약이 아니라 고장이다 (D-301 의 짝).
# ═══════════════════════════════════════════════════════════════════════════

class ValidWebhookPassesTest(WebhookFixture):

    def test_a_correctly_signed_webhook_passes(self) -> None:
        body = self.body()
        ok, why = verify(self.SECRET, body, self.good_headers(body), now=self.NOW)
        self.assertTrue(ok, "바르게 서명한 웹훅이 거절됐다 — 사유 %r. "
                            "전부 거절하는 검증기는 규약이 아니라 고장이다" % why)
        self.assertEqual(why, "", "통과인데 사유가 붙었다")

    def test_outbound_headers_carry_the_whole_contract(self) -> None:
        """보낼 때 붙는 헤더가 규약 전부를 나른다. **여기 없는 헤더는 규약이 아니다.**"""
        headers = self.good_headers()
        self.assertEqual(headers[SCHEMA_HEADER], SCHEMA_VERSION)
        self.assertTrue(headers[SIGNATURE_HEADER].startswith(SIGNATURE_PREFIX),
                        "서명 값에 알고리즘 표식이 없다 — 받는 쪽이 무엇으로 검증할지 모른다")
        self.assertIn(TIMESTAMP_HEADER, headers, "타임스탬프가 없으면 재생을 못 막는다")
        self.assertEqual(headers[EVENT_ID_HEADER], "s_evt_1",
                         "이벤트 식별자가 없으면 상대가 중복 도착을 가릴 수 없다 — "
                         "재시도가 있는 규약에서 중복 도착은 결함이 아니라 정상이다")

    def test_the_schema_header_name_is_the_one_the_prd_named(self) -> None:
        """PRD v2.5 §6 이 이름을 정했다: `X-GX-Schema: 1`. 이름이 갈리면 계약이 갈린다."""
        self.assertEqual(SCHEMA_HEADER, "X-GX-Schema")
        self.assertEqual(SCHEMA_VERSION, "1")
        self.assertIn(SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS)


# ═══════════════════════════════════════════════════════════════════════════
# ① 서명 불일치 거절
# ═══════════════════════════════════════════════════════════════════════════

class SignatureMismatchIsRejectedTest(WebhookFixture):
    """★ 출생 표본 — **서명 없는 웹훅은 누구나 보낼 수 있는 경보다.**

    우리 이름으로 가짜 경보를 낼 수 있다는 뜻이고, 경보 제품에서 그것은 최악이다.
    """

    def test_a_wrong_secret_is_rejected(self) -> None:
        body = self.body()
        headers = self.good_headers(body)
        ok, why = verify("다른_키", body, headers, now=self.NOW)
        self.assertFalse(ok, "★ 다른 키로 서명한 웹훅이 통과했다 — 서명이 서명이 아니다")
        self.assertEqual(why, REJECT_SIGNATURE_MISMATCH)

    def test_a_tampered_body_is_rejected(self) -> None:
        """본문을 한 글자 바꾸면 거절된다 — 서명이 본문을 **덮고 있다**는 증명."""
        headers = self.good_headers(self.body())
        ok, why = verify(self.SECRET, self.body(status="Test"), headers, now=self.NOW)
        self.assertFalse(ok, "본문이 바뀌었는데 통과했다 — 서명이 본문을 덮지 않는다")
        self.assertEqual(why, REJECT_SIGNATURE_MISMATCH)

    def test_a_missing_signature_is_rejected(self) -> None:
        headers = self.good_headers()
        headers.pop(SIGNATURE_HEADER)
        ok, why = verify(self.SECRET, self.body(), headers, now=self.NOW)
        self.assertFalse(ok, "서명이 아예 없는데 통과했다")
        self.assertEqual(why, REJECT_NO_SIGNATURE)

    def test_a_signature_without_the_algorithm_marker_is_rejected(self) -> None:
        headers = self.good_headers()
        headers[SIGNATURE_HEADER] = headers[SIGNATURE_HEADER][len(SIGNATURE_PREFIX):]
        ok, why = verify(self.SECRET, self.body(), headers, now=self.NOW)
        self.assertFalse(ok, "알고리즘 표식 없는 서명이 통과했다")
        self.assertEqual(why, REJECT_BAD_SIGNATURE_FORM)

    def test_no_secret_on_our_side_is_a_rejection_not_a_pass(self) -> None:
        """★ 「키가 아직 없어서 통과시켰다」가 정확히 사고가 나는 자리다."""
        ok, why = verify("", self.body(), self.good_headers(), now=self.NOW)
        self.assertFalse(ok, "★ 우리 쪽에 키가 없는데 통과했다 — 없으면 닫는다")
        self.assertEqual(why, REJECT_NO_SECRET)

    def test_signing_without_a_key_raises_rather_than_producing_a_signature(self) -> None:
        with self.assertRaises(ValueError):
            sign("", self.body(), str(int(self.NOW)))


class ReplayIsRejectedTest(WebhookFixture):
    """서명이 **본문만** 덮으면 같은 요청을 다시 보내는 것을 못 막는다 (함정 둘)."""

    def test_a_recorded_request_replayed_later_is_rejected(self) -> None:
        body = self.body()
        headers = self.good_headers(body)
        later = self.NOW + TIMESTAMP_TOLERANCE_SECONDS + 1
        ok, why = verify(self.SECRET, body, headers, now=later)
        self.assertFalse(ok, "★ 창 밖에서 되보낸 요청이 통과했다 — 서명이 맞아도 재생은 재생이다")
        self.assertEqual(why, REJECT_STALE_TIMESTAMP)

    def test_inside_the_window_it_still_passes(self) -> None:
        """음성 대조 — 시계가 조금 어긋난 정상 요청까지 막으면 규약이 아니라 장애다."""
        body = self.body()
        headers = self.good_headers(body)
        ok, why = verify(self.SECRET, body, headers,
                         now=self.NOW + TIMESTAMP_TOLERANCE_SECONDS - 1)
        self.assertTrue(ok, "창 안인데 거절됐다 — 사유 %r" % why)

    def test_a_missing_or_malformed_timestamp_is_rejected(self) -> None:
        headers = self.good_headers()
        headers.pop(TIMESTAMP_HEADER)
        ok, why = verify(self.SECRET, self.body(), headers, now=self.NOW)
        self.assertEqual((ok, why), (False, REJECT_NO_TIMESTAMP))

        headers = self.good_headers(**{TIMESTAMP_HEADER: "어제"})
        ok, why = verify(self.SECRET, self.body(), headers, now=self.NOW)
        self.assertEqual((ok, why), (False, REJECT_BAD_TIMESTAMP))

    def test_moving_the_timestamp_alone_breaks_the_signature(self) -> None:
        """타임스탬프를 고쳐 창 안으로 끌어오면 **서명이 깨진다** — 서명이 그것도 덮는다."""
        body = self.body()
        headers = self.good_headers(body)
        headers[TIMESTAMP_HEADER] = str(int(self.NOW) + 10_000)
        ok, why = verify(self.SECRET, body, headers, now=self.NOW + 10_000)
        self.assertFalse(ok, "타임스탬프만 갈아끼웠는데 통과했다 — 서명이 그것을 안 덮는다")
        self.assertEqual(why, REJECT_SIGNATURE_MISMATCH)


# ═══════════════════════════════════════════════════════════════════════════
# ③ 스키마 버전 헤더 부재 거절
# ═══════════════════════════════════════════════════════════════════════════

class SchemaVersionHeaderIsRequiredTest(WebhookFixture):

    def test_a_missing_schema_header_is_rejected(self) -> None:
        headers = self.good_headers()
        headers.pop(SCHEMA_HEADER)
        ok, why = verify(self.SECRET, self.body(), headers, now=self.NOW)
        self.assertFalse(ok, "★ 스키마 버전 없는 웹훅이 통과했다 — "
                             "우리가 바뀌면 상대는 언제 깨졌는지 모른 채 깨진다")
        self.assertEqual(why, REJECT_NO_SCHEMA)

    def test_an_unknown_schema_version_is_rejected(self) -> None:
        headers = self.good_headers(**{SCHEMA_HEADER: "99"})
        ok, why = verify(self.SECRET, self.body(), headers, now=self.NOW)
        self.assertFalse(ok, "모르는 판을 통과시켰다 — 조용히 추측하지 않는다")
        self.assertEqual(why, REJECT_BAD_SCHEMA)

    def test_the_schema_is_judged_before_the_signature(self) -> None:
        """★ 순서가 규약이다. 모르는 판인데 서명은 맞는 요청 —
        서명부터 보면 「통과 아닌 통과」가 생긴다."""
        body = self.body()
        headers = outbound_headers(self.SECRET, body, timestamp=str(int(self.NOW)),
                                   schema="99")       # 판 99 로 **제대로** 서명했다
        ok, why = verify(self.SECRET, body, headers, now=self.NOW)
        self.assertFalse(ok)
        self.assertEqual(why, REJECT_BAD_SCHEMA,
                         "서명은 맞았지만 판을 모른다 — 사유는 서명이 아니라 판이어야 한다")

    def test_headers_are_read_case_insensitively(self) -> None:
        """HTTP 헤더 이름은 대소문자를 안 가린다. 가리는 것으로 읽으면
        **상대의 라이브러리에 따라 우리 규약이 갈린다.**"""
        body = self.body()
        headers = {k.lower(): v for k, v in self.good_headers(body).items()}
        ok, why = verify(self.SECRET, body, headers, now=self.NOW)
        self.assertTrue(ok, "소문자 헤더를 못 읽었다 — 사유 %r" % why)

    def test_django_meta_style_headers_are_read_too(self) -> None:
        """Django `request.META` 모양(`HTTP_X_GX_SCHEMA`)도 같은 규약으로 읽힌다."""
        body = self.body()
        headers = {"HTTP_" + k.upper().replace("-", "_"): v
                   for k, v in self.good_headers(body).items()}
        ok, why = verify(self.SECRET, body, headers, now=self.NOW)
        self.assertTrue(ok, "META 모양 헤더를 못 읽었다 — 사유 %r" % why)


# ═══════════════════════════════════════════════════════════════════════════
# ② 5회 뒤 포기 기록
# ═══════════════════════════════════════════════════════════════════════════

class RetryStopsAtFiveAndLeavesARowTest(WebhookFixture):
    """★ 재시도 규약이 없으면 상대가 한 번 죽었을 때 그 경보는 **조용히 사라진다.**

    조용히 사라지는 것이 이 제품에서 가장 나쁜 실패다 — 아무도 모르기 때문이다.
    """

    def test_the_policy_is_five_attempts(self) -> None:
        self.assertEqual(MAX_ATTEMPTS, 5, "정본이 정한 수는 5다 — 여기서 조용히 늘리지 않는다")
        self.assertEqual(len(RetryPolicy().schedule()), 5)

    def test_the_backoff_is_exponential(self) -> None:
        policy = RetryPolicy()
        delays = [policy.delay_for(n) for n in range(1, MAX_ATTEMPTS + 1)]
        self.assertEqual(delays, [1.0, 2.0, 4.0, 8.0, 16.0],
                         "지수 백오프가 아니다 — 죽은 상대를 같은 간격으로 때리면 폭주다")
        for earlier, later in zip(delays, delays[1:]):
            self.assertGreater(later, earlier)

    def test_the_last_attempt_has_no_wait_after_it(self) -> None:
        """마지막 시도 뒤에는 기다릴 다음 시도가 없다. 거기서 포기 기록이 나간다."""
        schedule = RetryPolicy().schedule()
        self.assertEqual(schedule[-1][0], MAX_ATTEMPTS)
        self.assertEqual(schedule[-1][1], 0.0)

    def test_a_dead_receiver_is_hit_exactly_five_times(self) -> None:
        """★ 출생 표본 — 상대가 계속 503 이면 **정확히 5번**이고 6번은 없다."""
        policy = RetryPolicy()
        attempts = attempts_from(policy, [503] * 20)
        self.assertEqual(attempts, MAX_ATTEMPTS,
                         "죽은 상대를 %d번 때렸다 — 5회에서 멈춰야 한다" % attempts)

    def test_a_client_error_is_not_retried(self) -> None:
        """4xx 는 다시 보내도 같은 답이 온다. 재시도는 「상대가 잠깐 죽었다」를 위한 것이지
        「우리가 틀렸다」를 위한 것이 아니다."""
        policy = RetryPolicy()
        self.assertEqual(attempts_from(policy, [400, 400, 400]), 1,
                         "400 을 다시 보냈다 — 상대를 때리는 재시도다")
        self.assertFalse(policy.should_retry(1, 403))

    def test_overload_and_timeout_are_retried_even_though_they_are_4xx(self) -> None:
        """음성 대조 — 429(과부하)·408(시간 초과)은 4xx 지만 다시 보낼 자리다."""
        for status in (408, 429):
            self.assertIn(status, RETRYABLE_STATUS)
            self.assertTrue(RetryPolicy().should_retry(1, status),
                            "%d 를 재시도하지 않는다 — 상대가 잠깐 바쁜 것을 영구 실패로 읽는다"
                            % status)

    def test_no_response_at_all_is_retried(self) -> None:
        """응답을 못 받은 것(연결 실패·타임아웃)과 거절당한 것은 다르다."""
        self.assertTrue(RetryPolicy().should_retry(1, None))

    def test_a_success_stops_immediately(self) -> None:
        self.assertEqual(attempts_from(RetryPolicy(), [503, 503, 200, 503]), 3)

    def test_giving_up_leaves_a_row(self) -> None:
        """★ **포기했다는 사실이 행으로 남는다.** 남기지 않으면 상대는 못 받았고
        우리는 보냈다고 믿는다 — 둘 다 모르는 채로."""
        row = giveup_record(subscription_id=7, event_id="s_evt_1",
                            attempts=MAX_ATTEMPTS, last_status=503,
                            last_error="Service Unavailable")
        self.assertEqual(row["attempts"], MAX_ATTEMPTS)
        self.assertEqual(row["max_attempts"], MAX_ATTEMPTS)
        self.assertEqual(row["reason"], GIVEUP_EXHAUSTED)
        self.assertEqual(row["subscription_id"], 7)
        self.assertEqual(row["event_id"], "s_evt_1")
        self.assertEqual(row["schema_version"], SCHEMA_VERSION)
        self.assertEqual(row["waited_seconds"], RetryPolicy().total_wait())
        self.assertIsNotNone(row["gave_up_at"], "언제 포기했는지 없으면 조사할 수 없다")

    def test_the_two_kinds_of_giving_up_are_not_the_same_word(self) -> None:
        """「실패」 한 낱말로 뭉치지 않는다 — 고치는 사람이 달라진다.
        상대가 죽어 있는 것과 우리 규약이 안 맞는 것은 다른 일이다."""
        self.assertNotEqual(GIVEUP_EXHAUSTED, GIVEUP_REJECTED)
        row = giveup_record(subscription_id=7, event_id="s_evt_2", attempts=1,
                            last_status=401, reason=GIVEUP_REJECTED)
        self.assertEqual(row["reason"], GIVEUP_REJECTED)
        self.assertEqual(row["attempts"], 1, "거절은 1회로 끝난다 — 5회를 쓰지 않는다")

    def test_a_giveup_row_with_zero_attempts_is_refused(self) -> None:
        """보내지 않은 것과 못 보낸 것은 다르다."""
        with self.assertRaises(ValueError):
            giveup_record(subscription_id=7, event_id="s_evt_3", attempts=0,
                          last_status=None)

    def test_total_wait_is_bounded(self) -> None:
        """5회를 다 써도 사람의 인내 안에서 끝난다 — 이 수를 보고서가 인용한다."""
        total = RetryPolicy().total_wait()
        self.assertEqual(total, 15.0)
        self.assertLess(total, 60.0)


# ═══════════════════════════════════════════════════════════════════════════
# 함정 — 새 인증 경로를 만들지 않았는가 (세종 §4-4 · P-37)
# ═══════════════════════════════════════════════════════════════════════════

class TheContractOpensNoNewDoorTest(SimpleTestCase):
    """★ 규약 모듈이 **문을 내면 안 된다.** 문은 UX-19 가 F-05 구독 등록 위에 낸다.

    여기서 라우트를 하나 열면 그것이 곧 새 인증 경로이고, 무계정 링크로 가는 첫 걸음이다
    (「이 URL 을 아는 사람은 누구나」 — 그 순간 URL 하나가 계정이 된다).
    """

    def test_the_module_declares_no_routes(self) -> None:
        import inspect

        from common import webhook_contract

        source = inspect.getsource(webhook_contract)
        for forbidden in ("@route.", "@api_controller", "@router.", "urlpatterns"):
            self.assertNotIn(
                forbidden, source,
                "규약 모듈이 라우트를 열었다(%r) — 새 인증 경로 금지(세종 §4-4 · P-37). "
                "문은 UX-19 가 F-05 구독 등록 위에 낸다" % forbidden)

    def test_the_module_needs_no_django_settings(self) -> None:
        """규약은 순수하다 — 설정에 매이면 시험이 환경에 매이고, 환경이 죽으면
        규약 시험이 **초록으로** 죽는다 (D-301)."""
        import inspect

        from common import webhook_contract

        source = inspect.getsource(webhook_contract)
        self.assertNotIn("from django", source,
                         "규약 모듈이 Django 에 매였다 — 순수 함수로 둔다")
