# -*- coding: utf-8 -*-
"""P-469 — 백업 따라잡기: 꺼졌던 기계가 켜져 beat 가 뜨면 스스로 한 번 뜬다.

① 마지막 beat 계열 덤프가 24h 이내면 안 보낸다 · 넘으면 보낸다.
② 손 덤프(manual)가 마지막이면 따라잡는다 — 손 덤프는 정시를 대신하지 못한다.
③ 백업 주기가 꺼져 있으면 안 보낸다.
④ 잠금 — 두 번 떠도 한 번만 보낸다.
⑤ beat_init 신호에 붙어 있다.
"""
import json
from datetime import datetime, timedelta, timezone
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase

from common import ops_tasks

NOW = datetime(2026, 10, 1, 0, 9, tzinfo=timezone.utc)   # 10-01 09:09 KST — PC 가 켜진 실례


def _last(invoked_by="beat", verdict="OK", hours=1.0):
    return {"invoked_by": invoked_by, "verdict": verdict,
            "measured_at": (NOW - timedelta(hours=hours)).isoformat()}


class CatchupReasonTest(SimpleTestCase):
    def test_fresh_beat_or_catchup_needs_nothing(self):
        self.assertIsNone(ops_tasks.backup_catchup_reason(_last("beat", hours=3), NOW))
        self.assertIsNone(ops_tasks.backup_catchup_reason(_last("beat_catchup", hours=23), NOW))

    def test_birth_sample_20261001(self):
        """출생 표본 — 마지막 beat 덤프가 28.3h 전(09-30 05:00 KST)이었다."""
        why = ops_tasks.backup_catchup_reason(_last("beat", hours=28.3), NOW)
        self.assertIn("28.3", why)

    def test_manual_last_or_missing_or_failed_catches_up(self):
        self.assertIsNotNone(ops_tasks.backup_catchup_reason(_last("manual", hours=1), NOW))
        self.assertIsNotNone(ops_tasks.backup_catchup_reason(None, NOW))
        self.assertIsNotNone(ops_tasks.backup_catchup_reason(_last("beat", "ALARM", 1), NOW))


class CatchupOnBeatStartTest(SimpleTestCase):
    def setUp(self):
        cache.delete("gx:ops:backup_catchup_lock")

    def tearDown(self):
        cache.delete("gx:ops:backup_catchup_lock")

    def _run(self, last, enabled=True):
        sent = []
        body = json.dumps(last) if last is not None else "{broken"
        with mock.patch.object(ops_tasks, "backup_schedule_enabled", return_value=enabled), \
                mock.patch.object(ops_tasks.Path, "read_text", return_value=body):
            ops_tasks.backup_catchup_on_beat_start(lambda: sent.append(1))
        return len(sent)

    def test_sends_once_when_stale_then_lock_holds(self):
        stale = {"invoked_by": "beat", "verdict": "OK",
                 "measured_at": (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()}
        self.assertEqual(1, self._run(stale))
        self.assertEqual(0, self._run(stale), "잠금이 있으면 두 번째는 안 보낸다")

    def test_fresh_sends_nothing(self):
        fresh = {"invoked_by": "beat", "verdict": "OK",
                 "measured_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()}
        self.assertEqual(0, self._run(fresh))

    def test_disabled_sends_nothing(self):
        self.assertEqual(0, self._run(None, enabled=False))

    def test_hooked_to_beat_init(self):
        from celery.signals import beat_init

        import config.celery as cc
        receivers = [r[1]() for r in beat_init.receivers]
        self.assertIn(cc.backup_catchup_on_beat_init, receivers)

    def test_beat_only_sends_the_check_task(self):
        """beat 컨테이너에는 증거 폴더가 없다(10-01 실측) — beat 는 판단 태스크만 보낸다."""
        import config.celery as cc
        with mock.patch.object(cc.app, "send_task") as send:
            cc.backup_catchup_on_beat_init()
        send.assert_called_once_with("common.ops_backup_catchup_check")

    def test_check_task_runs_backup_inline_when_stale(self):
        stale = {"invoked_by": "beat", "verdict": "OK",
                 "measured_at": (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()}
        with (mock.patch.object(ops_tasks, "backup_schedule_enabled", return_value=True),
              mock.patch.object(ops_tasks.Path, "read_text", return_value=json.dumps(stale)),
              mock.patch.object(ops_tasks, "ops_backup_beat") as run):
            ops_tasks.ops_backup_catchup_check()
        run.assert_called_once_with(invoked_by="beat_catchup")
