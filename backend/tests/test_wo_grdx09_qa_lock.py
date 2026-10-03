# -*- coding: utf-8 -*-
"""WO-GRDX-20261002-09 AC-1 — 규격 09 M1 이중 잠금: `QA_BUILD` 가 없으면 `/qa/*` 는 없다.

출생 표본 [2026-10-03 11:3x · 영실 GRDX] `/qa/*` 는 아직 어디에도 없다 — 이 시험은 문을 만들기 **전에**
잠금을 먼저 세운다(03 「설계 단계부터 운영 배포에 포함될 수 없는 구조」). 문(M2)이 생기면 그 문이 이 잠금 안에 선다.
  · 운영 판(기본값): 루트 URL 에 `qa/` 조각이 없다 · `/qa/as/x` 404(CI 검사 — 규격 09 §3)
  · 잠금 ②: 조각이 등록돼 있어도 `QA_BUILD` 가 거짓이면 404
  · QA 판: 등록 + 참 → 아직 501(AC-2 전 · 인증을 건너뛰는 코드 0)

캐시 처리: 해당 없음 — 응답 캐시를 타지 않는 404·501 만 잰다.
"""
from django.test import Client, override_settings
from django.urls import get_resolver, include, path

urlpatterns = [path("qa/", include("apps.qa.urls"))]


def _patterns(resolver):
    return [str(p.pattern) for p in resolver.url_patterns]


def test_default_settings_do_not_register_qa_routes():
    from django.conf import settings
    assert settings.QA_BUILD is False
    assert not any(p.startswith("qa/") for p in _patterns(get_resolver("config.urls")))


@override_settings(DEBUG=False)
def test_qa_as_is_404_on_the_default_build():
    r = Client().get("/qa/as/customer_basic_01")
    assert r.status_code == 404


@override_settings(ROOT_URLCONF=__name__, QA_BUILD=False)
def test_runtime_lock_holds_even_if_routes_are_registered():
    r = Client().get("/qa/as/customer_basic_01")
    assert r.status_code == 404


@override_settings(ROOT_URLCONF=__name__, QA_BUILD=True)
def test_qa_build_answers_but_does_not_sign_in_yet():
    r = Client().get("/qa/as/customer_basic_01")
    assert r.status_code == 501
    assert "Set-Cookie" not in r.headers and "sessionid" not in r.cookies
