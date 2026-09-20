# -*- coding: utf-8 -*-
"""P-198 / PERF-04 — **설정 읽기 기억이 답을 바꾸지 않는다** (턴 X · 차선 F).

무엇을 재는가
-------------
`common.config_read_cache` 가 dj-core `core.configuration.utils._get_config_sync` 를
감싼다. 감싼 것의 유일한 계약은 **「같은 요청 안에서 같은 물음은 한 번만 묻는다」**이고,
이 시험은 그 계약의 **경계**를 잰다 — 빠르다는 것은 여기서 안 잰다(그건 `perf_load` 의 몫).

    ① 켜면 같은 물음을 두 번 물어도 **원 함수는 한 번만** 불린다
    ② 그래도 **돌려주는 값은 같다** — 빨라지려고 답을 바꾸면 그건 고친 것이 아니다
    ③ 기본값(`default`)이 다르면 **다른 물음**이다 — 다시 묻는다
    ④ 요청이 끝나면 **버린다** — 다음 요청은 새 값을 본다 (운영자가 설정을 바꾼 그 순간)
    ⑤ **쓰기 요청은 한 자도 안 기억한다** — 같은 요청에서 쓰고 다시 읽는 자리가 산다
    ⑥ 요청 **밖**에서는 원래대로 매번 묻는다 (셀러리·관리 명령이 헌 값을 안 본다)
    ⑦ `None` 을 기억한 것과 기억이 없는 것을 가른다 — 섞이면 캐시가 아무 일도 안 한다
    ⑧ 끄면(`CONFIG_READ_CACHE_ENABLED=False`) 겹이 **경로에서 빠진다**

★ dj-core 를 한 자도 안 고쳤다는 것도 여기서 잰다 — 벗긴 뒤에 원 함수가
  제자리에 돌아오는지(⑨). 벗겨지지 않는 감싸개는 시험 사이를 넘어 남는다.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import MiddlewareNotUsed
from django.test import RequestFactory, override_settings

from common import config_read_cache as crc


# ── 시험이 쓰는 도우미 — **제품에 두지 않는다** (D-377) ────────────────────
#
# 처음엔 이 둘을 `common/config_read_cache.py` 에 뒀다. 부르는 곳이 **시험뿐**이었고
# `dormant` 게이트가 「켜진 상태로 태어나야 한다」로 빨개졌다 — 옳은 빨강이다.
# 운영이 안 부르는 함수를 제품에 두면 다음 사람이 **있는 줄 알고 안 만든다.**
# 답은 등재가 아니라 **이사**다(턴 V `docx_export.text_of` 와 같은 처방).


def _memo_size() -> int:
    """지금 이 스레드가 기억하고 있는 항목 수. 「정말 기억했나」를 묻는 자리."""
    memo = getattr(crc._state, "memo", None)
    return 0 if memo is None else len(memo)


def _uninstall() -> bool:
    """감싸개를 벗긴다. **시험 뒷정리 전용** — 제품 경로에는 이 필요가 없다.

    제품의 되돌리기는 `CONFIG_READ_CACHE_ENABLED = False` 하나로 온전하다:
    겹이 `MiddlewareNotUsed` 로 경로에서 빠지고, 이미 감싼 뒤에 꺼도 감싸개가
    매번 `enabled()` 를 보고 원 함수로 그냥 지나간다. 벗길 일이 없다.
    벗겨야 하는 것은 **시험뿐**이다 — 안 벗기면 감싸개가 시험 사이를 넘어 남는다.
    """
    from core.configuration import utils as cfg_utils

    current = getattr(cfg_utils, "_get_config_sync", None)
    original = getattr(current, "_gx_original", None)
    if original is not None:
        cfg_utils._get_config_sync = original
    crc._installed = False
    crc.end()
    return original is not None


class _Spy:
    """원 함수 자리에 서서 **몇 번 불렸는지** 센다. 답은 물음에서 그대로 만든다."""

    #: 「답을 안 정했다」와 「답이 `None` 이다」를 가른다 — 그 둘을 섞으면 ⑦번 시험이
    #: 제 손을 잰다(감시자가 None 을 못 돌려주니 캐시가 잘했는지 알 수 없다).
    NOT_SET = object()

    def __init__(self, answer=NOT_SET):
        self.calls: list[tuple] = []
        self.answer = answer

    def __call__(self, name, fieldpath=None, default=None):
        self.calls.append((name, fieldpath, repr(default)))
        if self.answer is self.NOT_SET:
            return "%s::%s" % (name, fieldpath)
        return self.answer


@pytest.fixture
def spy(monkeypatch):
    """dj-core 자리에 감시자를 세우고, 그 위에 우리 감싸개를 올린다. 끝나면 벗긴다."""
    from core.configuration import utils as cfg_utils

    probe = _Spy()
    monkeypatch.setattr(cfg_utils, "_get_config_sync", probe, raising=True)
    crc._installed = False
    assert crc.install() is True
    yield probe
    _uninstall()
    crc._installed = False


def _call(name="System", fieldpath="security.encryption", default=None):
    from core.configuration import utils as cfg_utils

    return cfg_utils._get_config_sync(name, fieldpath, default)


# ── ① · ② 같은 물음은 한 번 · 답은 그대로 ──────────────────────────────────
def test_같은_물음은_요청_안에서_한_번만_묻는다(spy):
    crc.begin()
    try:
        first = _call()
        second = _call()
        third = _call()
    finally:
        crc.end()
    assert len(spy.calls) == 1, "세 번 물었는데 원 함수가 %d번 불렸다" % len(spy.calls)
    assert first == second == third, "기억이 답을 바꿨다 — 빨라지려고 답을 바꾸면 고친 것이 아니다"


# ── ③ 기본값이 다르면 다른 물음이다 ────────────────────────────────────────
def test_기본값이_다르면_다시_묻는다(spy):
    crc.begin()
    try:
        _call(default=None)
        _call(default={})
        _call(default=0)
        _call(default=None)          # 처음 것과 같은 물음 — 여기서는 안 묻는다
    finally:
        crc.end()
    assert len(spy.calls) == 3, "기본값이 다른 물음을 한 물음으로 셌다: %r" % (spy.calls,)


# ── ④ 요청이 끝나면 버린다 ────────────────────────────────────────────────
def test_요청이_끝나면_버린다(spy):
    crc.begin()
    _call()
    crc.end()
    assert _memo_size() == 0, "요청이 끝났는데 기억이 남아 있다"
    crc.begin()
    _call()
    crc.end()
    assert len(spy.calls) == 2, "앞 요청의 답을 다음 요청이 읽었다"


# ── ⑥ 요청 밖에서는 원래대로 ──────────────────────────────────────────────
def test_요청_밖에서는_매번_묻는다(spy):
    _call()
    _call()
    assert len(spy.calls) == 2, "요청 밖(셀러리·관리 명령)인데 기억이 살아 있다"


# ── ⑦ None 을 기억한 것과 기억이 없는 것 ──────────────────────────────────
def test_None_도_기억한다(spy):
    spy.answer = None
    crc.begin()
    try:
        assert _call() is None
        assert _call() is None
    finally:
        crc.end()
    assert len(spy.calls) == 1, "None 을 「기억 없음」으로 읽어 매번 다시 물었다"


# ── ⑤ 쓰기 요청은 한 자도 안 기억한다 ─────────────────────────────────────
@pytest.mark.parametrize("method,기억하는가", [
    ("get", True), ("head", True), ("options", True),
    ("post", False), ("put", False), ("patch", False), ("delete", False),
])
def test_쓰기_요청은_기억하지_않는다(spy, method, 기억하는가):
    seen = {}

    def inner(request):
        _call()
        _call()
        seen["원함수_호출수"] = len(spy.calls)
        seen["기억항목"] = _memo_size()
        return "ok"

    mw = crc.ConfigReadCacheMiddleware(inner)
    request = getattr(RequestFactory(), method)("/api/dsm/dashboard/link-state")
    assert mw(request) == "ok"
    if 기억하는가:
        assert seen["원함수_호출수"] == 1
        assert seen["기억항목"] == 1
    else:
        assert seen["원함수_호출수"] == 2, "쓰기 요청인데 기억했다 — 쓰고 다시 읽는 자리가 죽는다"
        assert seen["기억항목"] == 0
    assert _memo_size() == 0, "겹을 빠져나왔는데 기억이 남아 있다"


def test_뷰가_터져도_기억을_버린다(spy):
    def boom(request):
        _call()
        raise RuntimeError("뷰가 터졌다")

    mw = crc.ConfigReadCacheMiddleware(boom)
    with pytest.raises(RuntimeError):
        mw(RequestFactory().get("/api/dsm/dashboard/link-state"))
    assert _memo_size() == 0, "예외가 났을 때 기억이 스레드에 남았다 — 다음 요청이 그것을 읽는다"


# ── ⑧ 끄면 경로에서 빠진다 ────────────────────────────────────────────────
@override_settings(CONFIG_READ_CACHE_ENABLED=False)
def test_끄면_겹이_경로에서_빠진다():
    with pytest.raises(MiddlewareNotUsed):
        crc.ConfigReadCacheMiddleware(lambda request: "ok")


@override_settings(CONFIG_READ_CACHE_ENABLED=False)
def test_꺼져_있으면_기억이_열려_있어도_안_쓴다(spy):
    crc.begin()
    try:
        _call()
        _call()
    finally:
        crc.end()
    assert len(spy.calls) == 2, "되돌리기 한 줄이 안 듣는다"


# ── ⑨ 벗기면 dj-core 가 제자리로 돌아온다 ─────────────────────────────────
def test_벗기면_원_함수가_제자리로_돌아온다():
    from core.configuration import utils as cfg_utils

    #: ★ [실측 2026-09-20 · 전량 pytest] **먼저 벗기고 시작한다.** 이 시험만 돌리면
    #:   감싸개가 없지만, 전량으로 돌리면 앞선 시험들이 `Client` 로 겹을 태워서
    #:   **이미 감싸인 채** 들어온다. 그때 `original` 은 원 함수가 아니라 감싸개이고,
    #:   `install()` 은 「이미 감쌌다」로 그냥 참을 돌려준다 — 그러면 이 시험은
    #:   **제 손을 잰다.** 파일 하나로는 초록이고 전량으로는 빨강이던 자리가 여기다.
    _uninstall()
    original = cfg_utils._get_config_sync
    assert not getattr(original, "_gx_config_cache", False), "벗겼는데 아직 감싸개다"
    crc._installed = False
    assert crc.install() is True
    assert cfg_utils._get_config_sync is not original, "감싸지 않았다"
    assert _uninstall() is True
    assert cfg_utils._get_config_sync is original, "감싸개가 벗겨지지 않았다 — 시험 사이를 넘어 남는다"
    crc._installed = False


def test_두_번_감싸지_않는다():
    from core.configuration import utils as cfg_utils

    _uninstall()                      # 위와 같은 이유 — 깨끗한 자리에서 시작한다
    original = cfg_utils._get_config_sync
    assert not getattr(original, "_gx_config_cache", False), "벗겼는데 아직 감싸개다"
    crc._installed = False
    crc.install()
    once = cfg_utils._get_config_sync
    crc._installed = False          # 「이미 깔았다」 표시를 지우고 다시 시켜 본다
    crc.install()
    assert cfg_utils._get_config_sync is once, "감싸개 위에 감싸개가 또 얹혔다"
    _uninstall()
    assert cfg_utils._get_config_sync is original
    crc._installed = False


# ── 배선 — 설정에 줄이 실제로 들어 있는가 ─────────────────────────────────
def test_미들웨어가_설정에_있고_설정_읽는_겹보다_바깥이다():
    from django.conf import settings

    mw = list(settings.MIDDLEWARE)
    me = "common.config_read_cache.ConfigReadCacheMiddleware"
    assert me in mw, "겹이 설정에 없다 — 파일만 있고 배선이 없으면 아무 일도 안 한다"
    #: 설정을 읽는 것으로 실측된 겹들보다 **전부 바깥**이어야 한다 (PERF-04 추적).
    for inner in ("core.middleware.jwt_user_restore.JWTUserRestoreMiddleware",
                  "common.access_gate.AccessGateMiddleware",
                  "common.role_gate.RoleGateMiddleware",
                  "partner.middleware.PartnerAuthMiddleware",
                  "core.logger.middleware.CoreLoggingMiddleware"):
        assert mw.index(me) < mw.index(inner), (
            "%s 가 %s 보다 안쪽이다 — 그 겹의 설정 읽기가 기억 밖에 남는다" % (me, inner))
