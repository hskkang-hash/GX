# -*- coding: utf-8 -*-
"""P-425 — `scripts/measure_onboarding_t.py` U3#1(알림 수신) 술어를 제품 기본
`/m/inbox` `mine=true` 에 맞춘다 (턴 AP · 차선 Q).

무엇이 거짓이었나
------------------
종전 술어는 `/m/inbox` **화면 본문에 이번 사건 번호가 보이는지**를 봤다
(`card = (f"#{seed_a}" in ib) or (str(seed_a) in ib)`). 이것은 **「보낸 사람이 곧
받는 사람」**이라는 가정이다 — u3 가 「알림 보내기」를 누른다고 u3 자신이 그 사건의
수신자로 등록돼 있다는 보장은 없다(수신자는 `NotificationRule` 이 따로 정한다).
U3#19 가 이미 실측해 적어 둔 이 화면의 정본은 `GET /api/dsm/deliveries?...&mine=true`
다 — 그래서 카드 문자열 대조를 걷어내고 **그 API 를 실제로 불렀는지**(`mine=true`)로
술어를 바꿨다(`scripts/measure_onboarding_t.py` 의 U3#1 블록 · P-425 주석).

이 시험이 못박는 것 (짝 시험)
------------------------------
① `mine=true` 호출이 있으면 **카드 문자열이 화면에 전혀 없어도** 초록이 된다
   (종전 가정을 실제로 걷어냈는지 — 이것이 핵심 회귀 방지).
② `mine=true` 호출이 없으면 카드 문자열이 있어도(옛 방식이면 초록이었을 상태)
   더 이상 초록이 되지 않는다 — 카드로 되돌아가지 않는다.
③ 서버 기록이 안 늘면(before==after) 여전히 빨강이다(P-425 이전과 같은 불변).
④ POST 가 200 이 아니면 여전히 빨강이다(P-425 이전과 같은 불변).
⑤ 소스에 옛 카드 대조(`f"#{seed_a}"` · `in ib`)가 U3#1 블록에 다시 없는지 문자열로도 대조한다.

`rows_u3()` 는 900행이 넘는 Playwright 드라이버라 전체를 세우지 않는다 — `out.append`
가 U3#1 결과를 받는 **첫 호출**이라는 사실을 이용해, 그 호출에서 멈추는 리스트를 준다
(뒤 900행은 실행되지 않는다). `goto`·`body`·`visible_text`·`click_button`·
`delivery_count`·`collect_screen_text`·`result` 는 모듈 전역이라 로드된 모듈 객체에
직접 갈아 끼운다.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _tool_path() -> Path:
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
    path = _tool_path()
    spec = importlib.util.spec_from_file_location("gx_measure_onboarding_t_p425", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Halt(Exception):
    def __init__(self, captured):
        super().__init__("U3#1 이후로 멈췄다(의도된 것)")
        self.captured = captured


class _HaltAfterFirstAppend(list):
    """`out.append(...)` 의 **첫 호출**(U3#1)에서 멈춘다 — 뒤 900행을 안 돈다."""

    def append(self, item):
        raise _Halt(item)


def _run_u3_1(mod, *, post_status=200, before=0, after=1, mine_present=True,
             card_text=""):
    """`rows_u3()` 를 U3#1 까지만 돌리고 그 결과(`result()` 로 넘어간 인자)를 돌려준다."""
    calls = {"goto": [], "find": []}
    counters = {"delivery_count": 0}

    def fake_goto(page, web, route, settle_ms=6_000):
        calls["goto"].append(route)
        return route

    def fake_body(page):
        # ① ② 의 핵심: 카드 문자열이 있든 없든(seed_a 가 본문에 있든) 결과가 안 갈려야 한다.
        return card_text

    def fake_visible_text(page, text):
        return text == "알림 보내기"

    def fake_click_button(page, name, exact=False):
        return True

    def fake_delivery_count(event_id):
        counters["delivery_count"] += 1
        return before if counters["delivery_count"] == 1 else after

    def fake_collect_screen_text(*, page=None):
        return "정상 문구 — 화면 언어 위반 없음"

    class FakeNet:
        def mark(self):
            return 0

        def find(self, method, needle, since=0):
            calls["find"].append((method, needle))
            if method == "POST" and needle.endswith("/notify"):
                return [{"status": post_status}]
            if method == "GET" and needle == "/api/dsm/deliveries":
                if mine_present:
                    return [{"status": 200, "url": "/api/dsm/deliveries?limit=20&mine=true"}]
                return [{"status": 200, "url": "/api/dsm/deliveries?limit=20"}]
            return []

    def fake_result(row, route, phrase_seen, predicate, evidence, **kw):
        return {"row": row, "route": route, "seen": phrase_seen, "pred": predicate,
                "evidence": evidence}

    class FakePage:
        def wait_for_timeout(self, ms):
            pass

    mod.goto = fake_goto
    mod.body = fake_body
    mod.visible_text = fake_visible_text
    mod.click_button = fake_click_button
    mod.delivery_count = fake_delivery_count
    mod.collect_screen_text = fake_collect_screen_text
    mod.result = fake_result

    out = _HaltAfterFirstAppend()
    try:
        mod.rows_u3(FakePage(), FakeNet(), "http://x", out, None,
                   snap_event=1, seed_a=42, seed_b=43, probe_cam="probe-cam")
    except _Halt as halted:
        return halted.captured, calls
    raise AssertionError("out.append(U3#1) 가 안 불렸다 — 「알림 보내기」 단추 감지 경로가 바뀌었나")


class U3Number1DoesNotAssumeSenderIsRecipientTest(unittest.TestCase):
    """① — mine=true 호출이 있으면 카드 문자열이 전혀 없어도 초록이다."""

    def test_green_without_any_card_text_when_mine_is_called(self) -> None:
        mod = _load_module()
        captured, _calls = _run_u3_1(
            mod, post_status=200, before=3, after=4, mine_present=True, card_text="")
        self.assertEqual(captured["row"], "U3#1")
        self.assertTrue(captured["pred"], captured["evidence"])
        self.assertNotIn("카드", captured["evidence"].split("(")[0])


class U3Number1DoesNotFallBackToCardTextTest(unittest.TestCase):
    """② — mine=true 호출이 없으면, 카드 문자열이 있어도 더 이상 초록이 아니다."""

    def test_red_when_mine_is_missing_even_with_card_text_present(self) -> None:
        mod = _load_module()
        captured, _calls = _run_u3_1(
            mod, post_status=200, before=3, after=4, mine_present=False,
            card_text="#42 사건 카드가 화면에 있다")
        self.assertFalse(captured["pred"], captured["evidence"])


class U3Number1StillRequiresARealServerChangeTest(unittest.TestCase):
    """③ ④ — 배달이 안 늘었거나 POST 가 200 이 아니면 여전히 빨강이다(불변)."""

    def test_red_when_delivery_count_does_not_increase(self) -> None:
        mod = _load_module()
        captured, _calls = _run_u3_1(
            mod, post_status=200, before=5, after=5, mine_present=True)
        self.assertFalse(captured["pred"], captured["evidence"])

    def test_red_when_post_is_not_200(self) -> None:
        mod = _load_module()
        captured, _calls = _run_u3_1(
            mod, post_status=404, before=3, after=4, mine_present=True)
        self.assertFalse(captured["pred"], captured["evidence"])


class OldCardComparisonIsGoneFromTheU3Number1BlockTest(unittest.TestCase):
    """⑤ — U3#1 블록 소스에 옛 카드 대조가 다시 들어오지 않았는지 문자열로 대조한다."""

    def test_u3_1_block_has_no_card_string_comparison(self) -> None:
        text = _tool_path().read_text(encoding="utf-8")
        start = text.index("# #1 알림 수신")
        end = text.index("# #2 위치 확인")
        block = text[start:end]
        self.assertNotIn('f"#{seed_a}"', block)
        self.assertNotIn("card = ", block)
        self.assertIn('"mine=" in r["url"]', block)
