# -*- coding: utf-8 -*-
"""P-409 — `scripts/measure_onboarding_t.py::_outbox_signed()` 가 실재하는 사실을
잰다 (턴 AO · 차선 Q). 순수 시험 — `test_p343_third_condition_wiring.py` 와 같은 모양
(계측기를 실제로 돌리지 않는다 · gx-shell/DB 가 필요 없다).

무엇이 문제였나
---------------
옛 버전은 이 저장소에 없는 모델(`stream_monitors.WebhookOutbox` 등)을 찾다가 늘
-1 이었다. 게다가 `get = orm()` 뒤 `get(label)` 로 부르는 것 자체가 이미 호출
불가능한 값이었다(`orm()` 은 django `apps` 레지스트리를 돌려준다 — 그 레지스트리는
`get_model(app_label, model_name)` 을 받지, `get(label)` 로 불리지 않는다).

실제 발송 행은 `stream_monitors.DeliveryRecord`(채널 이름은
`common/webhook_outbox.py::CHANNEL`)다. 서명 **값**은 행에 안 남지만, 서명이 안
붙는 경로는 정확히 하나(`deliver_one()` 이 `signing_secret()` 을 못 찾을 때 남기는
고정 `failure_reason` 문구)라서, 그 표식이 없는 행 수로 「서명 붙은 발송」을 잰다.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _measure_onboarding_t_path() -> Path:
    """같은 순서(`test_p343_third_condition_wiring.py`)로 찾는다."""
    candidates = [
        Path("/repo/scripts/measure_onboarding_t.py"),
        Path(__file__).resolve().parents[2] / "scripts" / "measure_onboarding_t.py",
        Path("/app/scripts/measure_onboarding_t.py"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise AssertionError(
        "scripts/measure_onboarding_t.py 를 못 읽었다 — 찾아본 자리: %s" % candidates)


def _load_module():
    path = _measure_onboarding_t_path()
    spec = importlib.util.spec_from_file_location(
        "gx_measure_onboarding_t_p409", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Row:
    def __init__(self, failure_reason: str = "") -> None:
        self.failure_reason = failure_reason


class _FakeQuerySet(list):
    """`_base_manager.filter(...).order_by(...)[:200]` 체인을 흉내낸다."""

    def __init__(self, rows, *, captured=None):
        super().__init__(rows)
        self._captured = captured

    def filter(self, **kw):
        if self._captured is not None:
            self._captured.update(kw)
        return self

    def order_by(self, *a, **kw):
        return self


class _FakeManager:
    def __init__(self, rows, *, captured=None):
        self._rows = rows
        self._captured = captured

    def filter(self, **kw):
        return _FakeQuerySet(self._rows, captured=self._captured).filter(**kw)


class _FakeDeliveryModel:
    def __init__(self, rows, *, captured=None):
        self._base_manager = _FakeManager(rows, captured=captured)


class _FakeApps:
    def __init__(self, model=None, *, raise_on_get_model: bool = False):
        self._model = model
        self._raise = raise_on_get_model

    def get_model(self, app_label, model_name):
        if self._raise:
            raise LookupError("no such model: %s.%s" % (app_label, model_name))
        assert app_label == "stream_monitors"
        assert model_name == "DeliveryRecord"
        return self._model


class OutboxSignedReadsRealTableTest(unittest.TestCase):
    """`_outbox_signed()` — 실재하는 표만 읽고, 실재하는 표식으로 가른다."""

    def setUp(self) -> None:
        self.onb = _load_module()

    def test_source_no_longer_names_nonexistent_models(self) -> None:
        """회귀 방지 — 저장소에 없는 옛 모델을 찾는 **그 반복문 코드**로 되돌아가지
        않았다. 문자열 자체(`gone`)는 이 파일(위 주석에서 「왜 옛 이름이 틀렸는지」를
        설명하며 인용한다)과 이 시험 실패 메시지에도 나오므로, 전체 파일에서
        문자열 부재를 재면 **자기 설명 주석까지 걸린다** — 그래서 옛 코드의 실제
        모양(`for label in (그 이름...`)만 정확히 겨눈다."""
        src = _measure_onboarding_t_path().read_text(encoding="utf-8")
        for gone in ("stream_monitors.WebhookOutbox", "stream_monitors.DsmWebhookOutbox",
                     "stream_monitors.WebhookDelivery"):
            needle = 'for label in ("%s"' % gone
            self.assertNotIn(needle, src, "%s 로 되돌아갔다 — P-409 이전 상태다" % needle)
        self.assertIn("DeliveryRecord", src)
        #: 옛 호출 불가능 패턴(`get = orm()` 뒤 `model = get(label)`)의 실제 코드 모양만
        #: 겨눈다 — 그 문구 역시 위 설명 주석이 인용하므로 블랭킷 매치는 안 쓴다.
        self.assertNotIn("model = get(label)", src)

    def test_u6_4_predicate_no_longer_demands_a_send_this_step_cannot_make(self) -> None:
        """회귀 방지 — U6#4 술어가 `signed >= 1` 을 다시 요구하지 않는다.

        이 걸음(구독 등록)은 새 사건을 만들지 않으므로 그 요구는 「하지 않는 일」을
        묻는 것이고, 항상 빨강이 될 운명이다. **옛 술어의 실제 코드 모양**만 겨눈다 —
        그 문구 자체는 이 파일의 설명 주석에도 인용되므로, 전체 파일에서 문자열
        부재를 재면 자기 설명까지 걸린다."""
        src = _measure_onboarding_t_path().read_text(encoding="utf-8")
        self.assertNotIn("(n1 > n0) and signed >= 1", src)
        self.assertIn("r.status in (200, 201), (n1 > n0),", src)

    def test_counts_rows_without_the_no_signing_key_marker(self) -> None:
        rows = [
            _Row(failure_reason=""),                                       # 성공 — 서명 붙음
            _Row(failure_reason="rejected_by_receiver · 5/5회 · 마지막 응답 400"),  # 서명 붙었으나 상대가 거절
            _Row(failure_reason="attempts_exhausted · 5/5회 · 마지막 응답 없음"),   # 서명 붙었으나 5회 소진
            _Row(failure_reason="서명키 'p118-gate' 의 값이 이 환경에 없습니다 — "
                                "서명 없이 내보내지 않습니다"),                     # 서명 자체가 안 붙음
        ]
        captured: dict = {}
        model = _FakeDeliveryModel(rows, captured=captured)
        self.onb.orm = lambda: _FakeApps(model)

        self.assertEqual(self.onb._outbox_signed(), 3)
        self.assertEqual(captured.get("channel"), "webhook",
                         "common/webhook_outbox.py::CHANNEL 로 좁히지 않았다")

    def test_all_signed_and_none_signed_edges(self) -> None:
        all_signed = [_Row(failure_reason=""), _Row(failure_reason="rejected_by_receiver")]
        self.onb.orm = lambda: _FakeApps(_FakeDeliveryModel(all_signed))
        self.assertEqual(self.onb._outbox_signed(), 2)

        none_signed = [_Row(failure_reason="서명키 'x' 의 값이 이 환경에 없습니다 — "
                                          "서명 없이 내보내지 않습니다")]
        self.onb.orm = lambda: _FakeApps(_FakeDeliveryModel(none_signed))
        self.assertEqual(self.onb._outbox_signed(), 0)

    def test_returns_minus_one_when_the_model_cannot_be_read(self) -> None:
        """**못 읽으면 -1** — 0 과 다르다(함수 자신의 계약)."""
        self.onb.orm = lambda: _FakeApps(raise_on_get_model=True)
        self.assertEqual(self.onb._outbox_signed(), -1)

    def test_returns_minus_one_when_orm_itself_fails(self) -> None:
        def _boom():
            raise RuntimeError("django not ready")

        self.onb.orm = _boom
        self.assertEqual(self.onb._outbox_signed(), -1)

    def test_empty_table_is_zero_not_minus_one(self) -> None:
        """읽긴 읽었는데 행이 없는 것과 못 읽은 것은 다른 값이다."""
        self.onb.orm = lambda: _FakeApps(_FakeDeliveryModel([]))
        self.assertEqual(self.onb._outbox_signed(), 0)
