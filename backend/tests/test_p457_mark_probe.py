# -*- coding: utf-8 -*-
"""P-457 — `mark_probe` 관리 명령: 곁표만 쓰고 · 격자에서 빠지고 · 되돌리면 돌아온다.

① 표식하면 제품 격자(`_product_cameras`)에서 빠진다 — 그런데 **행은 한 글자도 안 바뀐다.**
② `--undo` 하면 격자로 돌아온다 — 곁표 줄 0.
③ 다른 낱말(`seed`) 곁표는 덮어쓰지도 지우지도 않는다 · 공용 마스터 표는 거절(D-270 ③).
④ 사유가 비면 거절 · 없는 행이면 거절(반쪽 집행 0).
⑤ `--dry-run` 은 쓰지 않는다.
"""
import io

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError

from common.billing_marks import mark_unbillable
from tests.test_dsm_app import DsmFixture

LABEL = "stream_monitors.streammonitor"


class MarkProbeCommand(DsmFixture):
    def _grid(self):
        from stream_monitors.services.camera_pulse import _product_cameras

        return set(_product_cameras().values_list("pk", flat=True))

    def _marks(self, pk):
        Mark = apps.get_model("common", "BillingMark")
        return list(Mark._base_manager.filter(model_label=LABEL, object_id=str(pk))
                    .values_list("data_source", flat=True))

    def _run(self, *args):
        out = io.StringIO()
        call_command("mark_probe", *args, stdout=out)
        return out.getvalue()

    def test_mark_then_undo_round_trip(self):
        pk = self.stream_a.pk
        before = self.stream_a.__class__._base_manager.filter(pk=pk).values().first()
        self.assertIn(pk, self._grid())

        self._run("--id", str(pk), "--reason", "시험 잔여")
        self.assertNotIn(pk, self._grid())
        self.assertEqual(self._marks(pk), ["probe"])
        after = self.stream_a.__class__._base_manager.filter(pk=pk).values().first()
        self.assertEqual(before, after, "행을 고치면 안 된다 — 곁표만")
        self.assertIn(self.stream_b.pk, self._grid(), "다른 행은 그대로")

        # 두 번 불러도 같다
        self._run("--id", str(pk), "--reason", "시험 잔여")
        self.assertEqual(self._marks(pk), ["probe"])

        self._run("--id", str(pk), "--undo")
        self.assertIn(pk, self._grid())
        self.assertEqual(self._marks(pk), [])

    def test_refuses_to_overwrite_or_undo_other_marks(self):
        mark_unbillable(self.stream_a, "seed", reason="검수 씨앗")
        with self.assertRaises(CommandError):
            self._run("--id", str(self.stream_a.pk), "--reason", "x")
        with self.assertRaises(CommandError):
            self._run("--id", str(self.stream_a.pk), "--undo")
        self.assertEqual(self._marks(self.stream_a.pk), ["seed"])

    def test_empty_reason_and_missing_row_refused_without_partial_write(self):
        with self.assertRaises(CommandError):
            self._run("--id", str(self.stream_a.pk))
        with self.assertRaises(CommandError):
            self._run("--id", str(self.stream_a.pk), "999999999", "--reason", "x")
        self.assertEqual(self._marks(self.stream_a.pk), [], "하나가 거절이면 아무것도 안 쓴다")

    def test_refuses_shared_master_table(self):
        with self.assertRaises(CommandError) as cm:
            self._run("--model", "user.timezone", "--id", "1", "--reason", "x")
        self.assertIn("공용 마스터", str(cm.exception))

    def test_dry_run_writes_nothing(self):
        out = self._run("--id", str(self.stream_a.pk), "--reason", "x", "--dry-run")
        self.assertIn("[미리]", out)
        self.assertEqual(self._marks(self.stream_a.pk), [])
