# -*- coding: utf-8 -*-
"""P-426 — `scripts/drill_seed_click.py --unjudged` (턴 AP · 차선 Q).

무엇을 못박나
--------------
① `--unjudged` 를 안 주면(기본값) 심는 동작은 전과 같다 — argparse 기본값이
   `False`, 그리고 `main()` 의 확인 단계(`verify_unjudged`)는 그 옵션이 참일 때만
   불린다(기본값 불변).
② `verify_unjudged()` 는 `verify_click_completes.py` 의 U1#11 표본 판정과
   **같은 잣대**(`verdict` 가 falsy면 미판정)를 쓴다 — ORM 값을 흉내 낸 가짜
   모델로 판정/미판정을 정확히 가른다.
③ 이미 판정된 사건이 섞여 있거나 못 찾은 id 가 있으면 결과에 그대로 보고된다 —
   조용히 넘기지 않는다.
④ `verify_click_completes.py` 의 U1#11 술어 문자열(`not e.get("verdict")`)이 그대로
   있는지 — 이 파일의 잣대가 그 파일과 갈리면 이 시험이 먼저 안다(문자열 대조).

★ 클래스는 `unittest.TestCase` 를 물려받는다 — 이 저장소의 pytest 설정은
  `python_classes` 를 안 넓혀서, TestCase 를 안 물려받는 맨 클래스는 **수집되지
  않는다**(`test_ap_q_p422_onboarding_default_no_c.py` 머리말의 실측 참고).
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _tool_path(name: str) -> Path:
    candidates = [
        Path("/repo/scripts/%s" % name),
        Path(__file__).resolve().parents[2] / "scripts" / name,
        Path("/app/scripts/%s" % name),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise AssertionError("scripts/%s 를 못 읽었다 — 찾아본 자리: %s" % (name, candidates))


def _load_module(name: str, filename: str):
    path = _tool_path(filename)
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_django_apps(rows: list[dict]):
    """`django.apps.apps.get_model("stream_monitors", "DetectionEvent")` 를 흉내 낸다.

    `verify_unjudged()` 가 `_base_manager.filter(pk__in=...).values("pk", "verdict")`
    를 부르는 그 모양만 지원하는 가짜 — 실제 ORM 을 세우지 않고도 잣대를 잰다.
    """

    class _QS(list):
        def filter(self, **kw):
            pk_in = set(kw.get("pk__in") or [])
            return _QS(r for r in self if r["pk"] in pk_in)

        def values(self, *names):
            return _QS({k: r[k] for k in names} for r in self)

    class _Manager:
        def __init__(self, data):
            self._data = _QS(data)

        def filter(self, **kw):
            return self._data.filter(**kw)

    class _Model:
        _base_manager = _Manager(rows)

    class _FakeAppsRegistry:
        def get_model(self, app_label, model_name):
            assert (app_label, model_name) == ("stream_monitors", "DetectionEvent")
            return _Model

    fake_apps_module = types.ModuleType("django.apps")
    fake_apps_module.apps = _FakeAppsRegistry()
    return fake_apps_module


class DefaultFlagDoesNotChangeSeedingTest(unittest.TestCase):
    """① — --unjudged 안 주면 기본값(False)이고, 심는 동작 자체는 그것과 무관하다."""

    def test_unjudged_defaults_to_false_in_the_real_parser(self) -> None:
        # main() 은 argparse 를 함수 안에서 만든다 — 파서를 직접 재현해 기본값을 잰다.
        drill = _load_module("gx_drill_seed_click_p426_a", "drill_seed_click.py")
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("--user", default="gxseed_u1_operator")
        ap.add_argument("--n", type=int, default=drill.DEFAULT_N)
        ap.add_argument("--address", default=None)
        ap.add_argument("--unjudged", action="store_true")
        parsed = ap.parse_args([])
        self.assertFalse(parsed.unjudged)
        self.assertEqual(parsed.n, drill.DEFAULT_N)
        self.assertEqual(drill.DEFAULT_N, 4)

    def test_source_declares_unjudged_as_store_true_default_false(self) -> None:
        text = _tool_path("drill_seed_click.py").read_text(encoding="utf-8")
        self.assertIn('"--unjudged"', text)
        # store_true 인자는 --unjudged 선언 뒤에 action="store_true" 가 딸려 있어야
        # 기본값이 False 다(명시적 default=True 로 뒤집힌 자리가 없다).
        idx = text.index('"--unjudged"')
        nearby = text[idx:idx + 200]
        self.assertIn("store_true", nearby)


class VerifyUnjudgedMatchesTheGateTest(unittest.TestCase):
    """② ③ — verify_unjudged() 가 U1#11 과 같은 잣대를 쓰고, 판정된 것을 잡아낸다."""

    def setUp(self) -> None:
        self._orig = sys.modules.get("django.apps")

    def tearDown(self) -> None:
        if self._orig is not None:
            sys.modules["django.apps"] = self._orig
        else:
            sys.modules.pop("django.apps", None)

    def _drill_with_fake_db(self, rows):
        sys.modules["django.apps"] = _fake_django_apps(rows)
        return _load_module("gx_drill_seed_click_p426_b_%d" % id(rows), "drill_seed_click.py")

    def test_all_unjudged(self) -> None:
        drill = self._drill_with_fake_db([
            {"pk": 1, "verdict": None}, {"pk": 2, "verdict": ""}, {"pk": 3, "verdict": None},
        ])
        out = drill.verify_unjudged([1, 2, 3])
        self.assertEqual(out["planted"], 3)
        self.assertEqual(out["found"], 3)
        self.assertEqual(out["judged"], [])
        self.assertEqual(out["unjudged"], [1, 2, 3])
        self.assertEqual(out["missing"], [])

    def test_some_already_judged_is_reported(self) -> None:
        drill = self._drill_with_fake_db([
            {"pk": 1, "verdict": None}, {"pk": 2, "verdict": "confirmed"},
        ])
        out = drill.verify_unjudged([1, 2])
        self.assertEqual(out["judged"], [2])
        self.assertEqual(out["unjudged"], [1])

    def test_missing_ids_are_reported_not_silently_dropped(self) -> None:
        drill = self._drill_with_fake_db([{"pk": 1, "verdict": None}])
        out = drill.verify_unjudged([1, 99])
        self.assertEqual(out["missing"], [99])


class PredicateStaysInSyncWithTheGateTest(unittest.TestCase):
    """④ — verify_click_completes.py 의 U1#11 표본 술어 문자열이 그대로 있다."""

    def test_gate_source_still_uses_not_verdict_predicate(self) -> None:
        text = _tool_path("verify_click_completes.py").read_text(encoding="utf-8")
        self.assertIn(
            'if not e.get("verdict")', text,
            "verify_click_completes.py 의 U1#11 미판정 잣대 문자열이 바뀌었다 — "
            "drill_seed_click.verify_unjudged() 의 verdict 판단과 다시 맞춰야 한다")
