# -*- coding: utf-8 -*-
"""턴 AR · 차선 Q — 판정기 넷 + 두 열(P-458) + 훈련 표식 미처리 씨앗(P-456) 자기시험 짝.

라이브 서버·8500 은 건드리지 않는다. 씨앗 통합 시험은 Django 시험 DB 에서만 심는다.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from tests.test_dsm_app import DsmFixture


def _path(name: str) -> Path:
    for base in (Path("/repo/scripts"), Path(__file__).resolve().parents[2] / "scripts"):
        if (base / name).is_file():
            return base / name
    raise AssertionError("scripts/%s 없음" % name)


def _load(mod: str, filename: str):
    sys.path.insert(0, str(_path(filename).parent))
    spec = importlib.util.spec_from_file_location(mod, str(_path(filename)))
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod] = m
    spec.loader.exec_module(m)
    return m


class TitlePartsArrowTest(unittest.TestCase):
    def test_arrow_name_is_cited(self) -> None:
        m = _load("ar_tp", "verify_spec_title_parts.py")
        got = m.extract_gx_tokens("X.tsx::data-gx=a-b-1 → c-d-2 · 재조회 → GET /api/x-y/z → f.py::rec_drop")
        self.assertEqual(got, ["a-b-1", "c-d-2"])
        self.assertEqual(m.extract_gx_tokens("data-gx=a-b-1(버튼) → Off.tsx::fws-f3-16-heli-pct"),
                         ["a-b-1", "fws-f3-16-heli-pct"])
        self.assertEqual(m.extract_gx_tokens("→ c-d-2 (data-gx 없음)"), [])


class ClickCompletesRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.m = _load("ar_cc", "verify_click_completes.py")

    def test_next_clock_plus_one_minute(self) -> None:
        n = self.m.next_clock
        self.assertEqual(n("21:47", "21:47"), "21:48")
        self.assertEqual(n("23:59", "23:59"), "00:00")
        self.assertEqual(n("21:47", "20:00"), "21:47")
        self.assertEqual(n("06:13", ""), "06:13")

    def test_csv_round_suffix_only_on_code_column(self) -> None:
        f = self.m.suffix_csv_codes
        src = "name,code,ip\na,GATE-01,rtsp://x"
        self.assertEqual(f(src, "r1"), "name,code,ip\na,GATE-01-r1,rtsp://x")
        self.assertEqual(f("a,b\n1,2", "r1"), "a,b\n1,2")

    def test_flows_use_new_rules_and_probe_mark_path(self) -> None:
        by = {f["key"]: f for f in self.m.FLOWS}
        self.assertTrue(any(s.get("kind") == "csv_suffix" for s in by["U5#4"]["prepare"]))
        self.assertTrue(all(s["text"].startswith("{clock:") for s in by["U3#16"]["prepare"]))
        snip = self.m.probe_mark_snippet("r0930")
        compile(snip, "<snip>", "exec")
        self.assertIn("mark_unbillable(o, 'probe'", snip)
        self.assertIn("-r0930", snip)

    def test_two_columns_do_not_mix(self) -> None:
        m = self.m
        rows = [("U1#1", m.GREEN, "", {}, {}), ("U1#2", m.RED, "", {}, {})]
        out = m.two_columns(rows, None)
        self.assertEqual([c["browser_clicked"] for c in out], [m.GREY, m.GREY])
        self.assertEqual([c["client_measured"] for c in out], [m.GREEN, m.RED])
        out2 = m.two_columns(rows, {"observations": {"U1#2": {"verdict": m.GREEN}}})
        self.assertEqual(out2[1]["browser_clicked"], m.GREEN)
        self.assertEqual(out2[1]["client_measured"], m.RED)
        self.assertTrue(all(x["browser_clicked"] == m.GREY for x in m.browser_targets_column(None)))


class SecretScanFingerprintTest(unittest.TestCase):
    def test_relative_and_absolute_fingerprints_meet(self) -> None:
        m = _load("ar_ss", "verify_secret_scan.py")
        bs = chr(92)
        root = "C:" + bs + "GuardianX" + bs + "guardianx-source"
        ab = root + bs + "docs" + bs + "a" + bs + "X.json:slack-webhook-url:17"
        rl = "docs/a/X.json:slack-webhook-url:17"
        self.assertEqual(m.norm_fingerprint(ab, root), rl)
        self.assertEqual(m.norm_fingerprint(rl, root), rl)
        self.assertNotEqual(m.norm_fingerprint("docs/a/X.json:slack-webhook-url:18", root), rl)
        keep, n = m.drop_ignored([{"Fingerprint": rl}], {rl})
        self.assertEqual((len(keep), n), (0, 1))
        self.assertEqual(m._fingerprint_self_test(), [])


class U48CapTest(unittest.TestCase):
    def test_cap_lifted_with_canon_row(self) -> None:
        m = _load("ar_mo", "measure_onboarding_t.py")
        self.assertIs(m.U4_8_CAP_HALF, False)
        doc = None
        for base in (Path("/docs"), Path(__file__).resolve().parents[2] / "docs"):
            if (base / "agent" / "onboarding_48.md").is_file():
                doc = (base / "agent" / "onboarding_48.md").read_text(encoding="utf-8")
        self.assertIsNotNone(doc)
        row = [ln for ln in doc.splitlines() if ln.startswith("| 8 | 특정 사건 이력 조회 | `/dsm/events`")]
        self.assertEqual(len(row), 1)
        self.assertNotIn("초록이 되지 않는다(◐ 상한)", row[0])


class DrillSeedPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cs = _load("ar_cs", "capture_screens.py")

    def test_plan_is_drill_marked_with_run_mark_and_not_probe(self) -> None:
        from common.probe_marker import is_drill_track, is_probe_track

        plan = self.cs.drill_seed_plan(3, "20261001T120000")
        self.assertEqual(len(plan), 3)
        for it in plan:
            self.assertTrue(is_drill_track(it["track_id"]))
            self.assertFalse(is_probe_track(it["track_id"]))
            self.assertIn("run=20261001T120000", it["track_id"])
        self.assertEqual(len({it["minutes_ago"] for it in plan}), 3)   # 시각을 벌린다(F-04)
        with self.assertRaises(ValueError):
            self.cs.drill_seed_plan(0, "x")

    def test_drill_camera_is_not_swallowed_by_probe_rules(self) -> None:
        self.assertFalse(self.cs.DRILL_SEED_CODE.startswith(self.cs.PROBE_TAG))


class DrillSeedIntegrationTest(DsmFixture):
    """시험 DB 에만 심는다 — 라이브 DB 를 쓰지 않는다."""

    def test_seed_drill_events_plants_unjudged_drill_rows_with_zero_billing(self) -> None:
        cs = _load("ar_cs2", "capture_screens.py")
        from django.apps import apps
        from common.billing_marks import BILLABLE_SOURCE, _mark_model

        ids = cs.seed_drill_events("dsm_user_a", n=2, run_stamp="20261001T120000")
        self.assertEqual(len(ids), 2)
        DE = apps.get_model("stream_monitors", "DetectionEvent")
        rows = list(DE._base_manager.filter(pk__in=ids))
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertTrue(str(r.track_id).startswith("data_source=drill;run=20261001T120000"))
            self.assertFalse(r.verdict)                                 # 미처리
        self.assertEqual({cs._event_data_source_of(i) for i in ids}, {"drill"})
        SM = apps.get_model("stream_monitors", "StreamMonitor")
        mon = SM._base_manager.get(code=cs.DRILL_SEED_CODE)
        self.assertEqual(mon.group_id, self.group_a.pk)
        mark = _mark_model()._base_manager.get(model_label=mon._meta.label_lower, object_id=str(mon.pk))
        self.assertEqual(mark.data_source, "drill")
        self.assertNotEqual(mark.data_source, BILLABLE_SOURCE)
