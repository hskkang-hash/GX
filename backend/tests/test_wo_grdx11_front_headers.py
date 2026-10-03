# -*- coding: utf-8 -*-
"""WO-GRDX-20261002-11 AC-1 · AC-1b ② · AC-1c · AC-1d — 앞문 설정 **글자** 점검(서버를 띄우지 않는다).

화면 주소(HTML)는 no-cache · 해시 자산은 immutable · 보안 머리 셋이 모든 응답에 닿는다(상속이 끊기는 자리 포함)
· 압축이 켜져 있다 · index.html 에 안내 인라인 줄이 있다. 실제 응답 머리는 격리 컨테이너 curl 로 잰다(보고서).
설정 파일(`nginx/`)이 시험 환경에 안 보이면(gx-shell 은 backend 만 묶는다) 사유를 적고 건너뛴다.
"""
import re
from pathlib import Path

import pytest


def _find(rel: str):
    here = Path(__file__).resolve()
    for base in (*here.parents, Path("/repo")):
        p = base / rel
        if p.is_file():
            return p
    return None


CONF = _find("nginx/gx-front.conf")
HDR = _find("nginx/gx-headers.inc")
GATE = _find("nginx/generated/gx-gate.conf")
INDEX = _find("frontend/index.html")

need_nginx = pytest.mark.skipif(CONF is None or HDR is None,
                                reason="nginx/ 가 이 환경에 안 묶여 있다(gx-shell 은 backend 만) — 호스트에서 돌린다")


def _text(p):
    return p.read_text(encoding="utf-8")


def _block(conf: str, head: str) -> str:
    """`location ... {` 한 줄 머리에서 짝이 맞는 `}` 까지."""
    m = re.search(re.escape(head) + r"\s*\{", conf)  # `location = /` 가 `location = /_front/…` 에 걸리지 않게
    i = m.start()
    j = conf.index("{", i)
    depth, k = 0, j
    while True:
        depth += conf[k] == "{"
        depth -= conf[k] == "}"
        if depth == 0:
            return conf[i:k + 1]
        k += 1


@need_nginx
def test_html_locations_are_no_cache():
    c = _text(CONF)
    for head in ("location = /index.html", "location = /", "location ^~ /login", "location ^~ /dsm/",
                 "location = /start"):
        assert "expires epoch" in _block(c, head), head


@need_nginx
def test_assets_immutable_and_keep_security_headers():
    c = _text(CONF)
    b = _block(c, "location ^~ /assets/")
    assert "public, max-age=31536000, immutable" in b
    # add_header 를 두는 자리는 상속이 끊긴다 → 보안 머리 한 벌을 다시 include 해야 한다
    assert "gx-headers.inc" in b


@need_nginx
def test_security_headers_one_set_at_server_level():
    h = _text(HDR)
    for line in ('X-Frame-Options "SAMEORIGIN"', "X-Content-Type-Options \"nosniff\"",
                 'Referrer-Policy "strict-origin-when-cross-origin"'):
        assert line in h and "always" in h
    server = _block(_text(CONF), "server")
    assert "include /etc/nginx/gx/gx-headers.inc" in server


@need_nginx
def test_generated_gate_defines_no_headers_of_its_own():
    # 생성물에 add_header 가 있으면 server 수준 보안 머리가 그 자리에서 사라진다
    if GATE is None:
        pytest.skip("generated/gx-gate.conf 가 안 보인다")
    assert "add_header" not in _text(GATE)


@need_nginx
def test_upstream_duplicate_security_headers_are_hidden():
    p = CONF.parent / "gx-proxy.inc"
    t = _text(p)
    for name in ("X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy"):
        assert f"proxy_hide_header {name};" in t


@need_nginx
def test_gzip_on_for_text_not_images_or_woff2():
    c = _text(CONF)
    for d in ("gzip on;", "gzip_vary on;", "gzip_proxied any;"):
        assert d in c
    assert re.search(r"gzip_min_length\s+\d+;", c)
    types = re.search(r"^\s*gzip_types([^;]+);", c, re.M).group(1)
    for t in ("text/css", "application/json", "image/svg+xml", "javascript"):
        assert t in types
    for t in ("woff2", "png", "jpeg"):
        assert t not in types


@pytest.mark.skipif(INDEX is None, reason="frontend/index.html 이 이 환경에 안 보인다")
def test_index_has_stale_bundle_notice_inline_script():
    t = _text(INDEX)
    assert "새 판이 나왔습니다" in t and "sessionStorage" in t and "location.reload" in t
    assert "vite:preloadError" in t
    # 외부 자원 0 — 안내 줄은 인라인이다(카카오 SDK 는 기존 줄)
    inline = t[t.index("var KEY"):t.index("</script>", t.index("var KEY"))]
    assert "src=" not in inline and "http" not in inline
