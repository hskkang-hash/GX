# -*- coding: utf-8 -*-
"""`GET /api/dsm/health` — 인증 없이 200 · 검사 하나 죽으면 503 과 그 이름 (턴 T · 차선 U56).

캐시 처리: 우회 — 생존 확인은 매 호출이 지금 상태여야 하므로 `tests.no_cache.NO_CACHE` 로
응답 캐시를 우회한다(D-341). 적중 본문은 언제나 200 이라 503 을 영원히 못 본다.

★ 본문에 비밀·호스트명이 없다는 것을 **글자로** 잰다 — 검사 이름과 상태 이름뿐이다.
"""
from __future__ import annotations

import json

from django.test import Client, TestCase

from tests.no_cache import NO_CACHE

HEALTH = "/api/dsm/health"


class DsmHealthTest(TestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_anonymous_gets_200_and_only_status_names(self):
        resp = self.client.get(HEALTH)
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = json.loads(resp.content.decode("utf-8"))
        self.assertEqual("ok", body["status"])
        self.assertEqual("1.1", body["schema"])
        self.assertEqual({"db", "cache", "queue"}, set(body["checks"]))
        self.assertTrue(all(v in ("ok", "fail") for v in body["checks"].values()))
        self.assertEqual([], body["failed"])
        self.assertEqual("no-store", resp["Cache-Control"])
        text = resp.content.decode("utf-8").lower()
        for forbidden in ("localhost", "redis://", "postgres", "password", "host"):
            self.assertNotIn(forbidden, text)
        self.assertEqual("1.1", resp["X-GX-Schema"])

    def test_a_dead_check_turns_503_and_names_itself(self):
        from apps.dsm import api_u56

        def boom():
            raise RuntimeError("secret-host-name-must-not-leak")

        original = api_u56.HEALTH_CHECKS["queue"]
        api_u56.HEALTH_CHECKS["queue"] = boom
        try:
            resp = self.client.get(HEALTH)
        finally:
            api_u56.HEALTH_CHECKS["queue"] = original
        self.assertEqual(503, resp.status_code, resp.content[:300])
        body = json.loads(resp.content.decode("utf-8"))
        self.assertEqual("fail", body["status"])
        self.assertEqual(["queue"], body["failed"])
        self.assertEqual("fail", body["checks"]["queue"])
        self.assertEqual("ok", body["checks"]["db"])
        self.assertNotIn("secret-host-name", resp.content.decode("utf-8"))
