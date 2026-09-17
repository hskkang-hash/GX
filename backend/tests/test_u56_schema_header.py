# -*- coding: utf-8 -*-
"""`X-GX-Schema: 1.1` — **전 응답** 헤더 · 분모는 라우트 대장에서 뽑는다 (턴 T · 차선 U56).

캐시 처리: 우회 — 헤더는 미들웨어가 매 응답에 붙이는 것이라 `tests.no_cache.NO_CACHE` 로
응답 캐시를 우회해 잰다(D-341). 적중 본문에 헤더가 붙는지는 이 시험의 술어가 아니다.

분모 규약 — 「분모 0 인 초록은 초록이 아니다」
----------------------------------------------
표본은 `docs/agent/evidence/D-343/route_inventory.json`(738) 에서 **기계가** 뽑는다:
  · 대장의 `view` 에서 **api 모듈**(클래스 앞까지)을 갈라 모듈마다 1 라우트(GET 우선) —
    「각 api 파일 1 이상」
  · GET 이 20 미만이면 GET 을 더 뽑아 **최소 20**
  · 경로 변수 `{…}` 는 `1` 로 채운다 — 무엇이 답하든(200·401·404·405·422·500) 헤더가 붙는가만 본다.
결과는 `[SCHEMA-HDR] 헤더 N/N (GET g · 모듈 m)` 한 줄로 찍힌다 — 보고에 그 분모를 그대로 옮긴다.

★ 실패 응답에도 붙어야 한다 — 익명 401 · 404 · 5xx 표지가 이 표본의 대다수다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from django.test import Client, TestCase

from tests.no_cache import NO_CACHE

INVENTORY = Path(__file__).resolve().parents[2] / "docs" / "agent" / "evidence" / "D-343" / "route_inventory.json"
MIN_GET = 20
HEADER = "X-GX-Schema"


def _module_of(view: str) -> str:
    # "pkg.mod.Class.method" → "pkg.mod" (마지막 두 조각이 클래스·메서드)
    parts = (view or "").split(".")
    return ".".join(parts[:-2]) if len(parts) >= 3 else view


def _fill(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "1", path)


def sample_routes(rows: list[dict]) -> list[dict]:
    by_module: dict[str, list[dict]] = {}
    for r in rows:
        by_module.setdefault(_module_of(r.get("view", "")), []).append(r)
    picked: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for mod in sorted(by_module):
        cands = by_module[mod]
        cands = sorted(cands, key=lambda r: (r["method"] != "GET", "{" in r["path"], r["path"]))
        r = cands[0]
        key = (r["method"], r["path"])
        if key not in seen:
            seen.add(key)
            picked.append(r)
    gets = [r for r in picked if r["method"] == "GET"]
    if len(gets) < MIN_GET:
        for r in sorted(rows, key=lambda r: ("{" in r["path"], r["path"])):
            if r["method"] != "GET":
                continue
            key = (r["method"], r["path"])
            if key in seen:
                continue
            seen.add(key)
            picked.append(r)
            if sum(1 for p in picked if p["method"] == "GET") >= MIN_GET:
                break
    return picked


class SchemaHeaderOnEveryResponseTest(TestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_header_on_sampled_routes_from_inventory(self):
        rows = json.loads(INVENTORY.read_text(encoding="utf-8"))["routes"]
        self.assertGreater(len(rows), 0, "대장이 비었다 — 분모 0")
        sample = sample_routes(rows)
        gets = sum(1 for r in sample if r["method"] == "GET")
        modules = len({_module_of(r["view"]) for r in sample})
        self.assertGreaterEqual(gets, MIN_GET)

        missing = []
        statuses: dict[int, int] = {}
        for r in sample:
            url = _fill(r["path"])
            call = getattr(self.client, r["method"].lower())
            try:
                resp = call(url)
            except Exception as exc:  # noqa: BLE001 — 뷰가 죽어도 헤더는 미들웨어 몫
                missing.append("%s %s (예외 %s)" % (r["method"], url, type(exc).__name__))
                continue
            statuses[resp.status_code] = statuses.get(resp.status_code, 0) + 1
            if resp.get(HEADER) != "1.1":
                missing.append("%s %s → %s" % (r["method"], url, resp.status_code))
        print("\n[SCHEMA-HDR] 헤더 %d/%d (GET %d · 모듈 %d) · 상태 %s"
              % (len(sample) - len(missing), len(sample), gets, modules,
                 dict(sorted(statuses.items()))))
        self.assertEqual([], missing, "X-GX-Schema 가 빠진 응답: %s" % missing)

    def test_header_on_error_and_success_paths(self):
        for url, want in (("/api/dsm/health", 200), ("/api/dsm/no-such-route-xyz", 404)):
            resp = self.client.get(url)
            self.assertEqual(want, resp.status_code, url)
            self.assertEqual("1.1", resp.get(HEADER), url)
