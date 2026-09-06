# -*- coding: utf-8 -*-
"""LAW-02a — **적었다가 아니라 그대로 지운다** (차선 L · 2026-09-05).

이 파일이 묻는 것 다섯
----------------------
① **수가 있는가, 그리고 그 수가 하나인가.** 안내판이 보는 수와 삭제가 보는 수가
   갈리면 그 종이는 게시되는 순간 거짓말이 된다.
② **지난 것은 지워지고 안 지난 것은 남는가** — 양성과 음성을 함께 본다.
   다 지우는 함수는 「기간을 지킨다」가 아니라 「다 버린다」이다.
③ **dry-run 이 기본값이고, dry-run 에서는 0건이 지워지는가.** 되돌릴 수 없는 일의
   기본값이 「한다」이면 그것은 기본값이 아니라 함정이다.
④ **지운 것이 감사에 남는가.** 안 남으면 「지웠다」와 「원래 없었다」가 같은 상태다.
⑤ **주기가 실제로 걸려 있는가.** 「보관 기간이 지난 영상은 자동으로 지워집니다」는
   주기가 없으면 거짓 문장이고, 그 문장은 화면과 안내판에 인쇄된다.

★ 이 파일이 묻지 **않는** 것 — 30일이 법적으로 맞는 수인가.
  그것은 법률대리인의 판정이다. 이 저장소는 LAW-02 를 「법률 대조 대기」로 미측정에
  두고 있고, 여기서도 같은 정직을 지킨다. 재는 것은 **집행**이지 적법성이 아니다.
"""
from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다. 합성 더미를 지우지 않는다.
REAL_SAMPLE = (
    "apps.dsm.retention · apps.dsm.legal_notice · common.ops_tasks · config.celery · "
    "stream_monitors.StreamMonitorRecord · stream_monitors.EventClip · "
    "stream_monitors.DetectionEvent · logger.AuditLogs — 저장소의 실제 모듈과 표"
)


def _model(name):
    return apps.get_model("stream_monitors", name)


def _age(model, pk, *, field, days):
    """행 하나를 **과거로 민다.** `auto_now_add` 칸은 create 로는 못 정한다."""
    model._base_manager.filter(pk=pk).update(
        **{field: timezone.now() - timedelta(days=days)})


class TheNumberIsDeclaredOnceTest(DsmFixture):
    """① 수가 있고, **그 수는 하나다.**"""

    def test_the_product_declares_a_retention_period(self):
        from apps.dsm.retention import retention_days, retention_source

        days = retention_days()
        self.assertIsInstance(days, int)
        self.assertGreater(days, 0, "0일 보존은 「즉시 삭제」다 — 그것은 선언이 아니다")
        self.assertTrue(retention_source(),
                        "수만 있고 출처가 없으면 다음 사람이 되짚지 못한다")

    def test_the_notice_board_reads_the_same_number(self):
        """★ 이 시험이 이 절의 요점 하나다.

        안내판(`legal_notice.retention_days`)과 삭제(`retention.retention_days`)가
        다른 수를 보면, 게시된 종이가 실제 삭제와 어긋난다. 그 어긋남은 **종이 쪽이
        법적 효력을 갖는다**는 점에서 보통의 불일치보다 나쁘다.
        """
        from apps.dsm import legal_notice, retention

        self.assertEqual(legal_notice.retention_days(), retention.retention_days())

    def test_the_notice_draft_no_longer_says_confirm_for_the_period(self):
        """보관 기간 칸이 **채워져 나온다.** 비어 있으면 「확인」으로 나갔다."""
        from apps.dsm.legal_notice import notice_draft

        draft = notice_draft(scope=self.scope_a)
        cell = next(c for c in draft["board"] if c["label"] == "보관 기간")
        self.assertIsNotNone(cell["value"], "보관 기간이 여전히 비어 있다")
        self.assertNotIn("보관 기간", draft["confirm_fields"])

    def test_a_broken_setting_does_not_become_zero_days(self):
        """★ 음성 대조 — 설정 오타가 **「0일 보존」이 되지 않는다.**

        0일 보존은 「즉시 삭제」라는 뜻이고, 오타 하나가 그 뜻을 갖게 두면
        되돌릴 수 없는 일이 조용히 일어난다.

        ★ 2026-09-06 · P-67 — **되돌아갈 곳이 바뀌었다.** 예전에는 오타가 제품
          기본값 30으로 되돌아갔다. 그 기본값이 사라졌으므로 지금은 **미선언**
          (`None`) 으로 간다. 목적은 그때나 지금이나 같다: 오타가 파기 명령이
          되지 않게 한다. 달라진 것은 「그래서 며칠 지우나」가 아니라
          **「그래서 안 지운다」**가 됐다는 것이고, 그쪽이 더 안전한 쪽이다.
        """
        from django.test import override_settings

        from apps.dsm.legal_notice import RETENTION_SETTING_NAMES
        from apps.dsm.retention import retention_days

        blank = {name: None for name in RETENTION_SETTING_NAMES}
        with override_settings(**dict(blank, VIDEO_RETENTION_DAYS=0)):
            self.assertIsNone(retention_days())
        with override_settings(**dict(blank, VIDEO_RETENTION_DAYS="이레")):
            self.assertIsNone(retention_days())
        with override_settings(**dict(blank, VIDEO_RETENTION_DAYS=7)):
            self.assertEqual(retention_days(), 7,
                             "운영자가 정한 값이 이겨야 한다")
        with override_settings(**blank):
            self.assertIsNone(retention_days(),
                              "코드 기본값이 되살아났다 — P-67 이 지운 자리다")


class DryRunIsTheDefaultTest(DsmFixture):
    """③ **기본값이 「안 지운다」이다.**"""

    def setUp(self):
        Record = _model("StreamMonitorRecord")
        self.old = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="old", object_path="")
        _age(Record, self.old.pk, field="created_at", days=999)

    def test_calling_sweep_without_arguments_deletes_nothing(self):
        from apps.dsm.retention import sweep

        Record = _model("StreamMonitorRecord")
        result = sweep()                       # ★ 인자 없이 — 이것이 규약이다
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["deleted_total"], 0,
                         "인자 없이 부른 집행이 무언가를 지웠다")
        self.assertGreater(result["expired_total"], 0,
                           "만료 건수를 세지도 못했다면 미리보기가 아니다")
        self.assertTrue(Record._base_manager.filter(pk=self.old.pk).exists(),
                        "미리보기가 행을 지웠다")

    def test_the_preview_is_also_audited(self):
        """미리보기도 남는다 — 「누가 무엇을 지우려고 들여다봤나」도 질문이다."""
        from apps.dsm.retention import LOGGER_NAME, sweep

        AuditLogs = apps.get_model("logger", "AuditLogs")
        before = AuditLogs._base_manager.filter(logger_name=LOGGER_NAME).count()
        sweep()
        after = AuditLogs._base_manager.filter(logger_name=LOGGER_NAME).count()
        self.assertEqual(after, before + 1)


class ExpiredGoesFreshStaysTest(DsmFixture):
    """② ★ **양성과 음성을 함께 본다.**"""

    def setUp(self):
        Record = _model("StreamMonitorRecord")
        Clip = _model("EventClip")

        #: 경로가 빈 녹화를 쓴다 — 객체저장소의 생사와 무관하게 **삭제 자체**를 잰다.
        #: (저장소가 죽었을 때의 거동은 아래 `ObjectFailureKeepsTheRowTest` 가 잰다)
        self.old_record = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="old", object_path="")
        self.new_record = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="new", object_path="")
        _age(Record, self.old_record.pk, field="created_at", days=999)

        event_id = self._event(self.stream_a)     # 이 픽스처는 **식별자**를 돌려준다
        self.old_clip = Clip._base_manager.create(
            event_id=event_id, object_key="", clip_status="referenced",
            start_offset=0.0, duration=30.0)
        self.new_clip = Clip._base_manager.create(
            event_id=event_id, object_key="", clip_status="referenced",
            start_offset=0.0, duration=30.0)
        _age(Clip, self.old_clip.pk, field="created_on", days=999)

    def test_expired_rows_are_actually_gone_and_fresh_rows_remain(self):
        from apps.dsm.retention import sweep

        Record = _model("StreamMonitorRecord")
        Clip = _model("EventClip")

        result = sweep(dry_run=False, actor=self.user_a, reason="시험 — 집행")

        self.assertFalse(Record._base_manager.filter(pk=self.old_record.pk).exists(),
                         "기간이 지난 녹화가 남았다")
        self.assertTrue(Record._base_manager.filter(pk=self.new_record.pk).exists(),
                        "★ 기간이 안 지난 녹화까지 지웠다 — 그것은 「지킨다」가 아니라 "
                        "「다 버린다」이다")
        self.assertFalse(Clip._base_manager.filter(pk=self.old_clip.pk).exists(),
                         "기간이 지난 구간 참조가 남았다")
        self.assertTrue(Clip._base_manager.filter(pk=self.new_clip.pk).exists(),
                        "★ 기간이 안 지난 구간 참조까지 지웠다")
        self.assertGreaterEqual(result["deleted_total"], 2)

    def test_the_delete_is_not_a_soft_delete(self):
        """★ **「지움」 표시가 아니라 행이 없어야 한다** [실측 · dj-core 는 소프트 삭제다].

        보존기간을 약속해 놓고 표시만 하면 그것은 지운 척이다. 그리고 그 척은
        평범한 조회에서 **똑같이 안 보이기 때문에** 아무도 모른다.
        """
        from apps.dsm.retention import sweep

        Clip = _model("EventClip")
        sweep(dry_run=False, actor=self.user_a, reason="시험 — 소프트 삭제 대조")

        for manager_name in ("all_objects", "deleted_objects"):
            manager = getattr(Clip, manager_name, None)
            if manager is None:
                continue
            self.assertFalse(
                manager.filter(pk=self.old_clip.pk).exists(),
                f"{manager_name} 에 아직 남아 있다 — 소프트 삭제로 지운 척했다")

    def test_what_was_deleted_is_written_to_the_audit_log(self):
        """④ 지운 것이 **감사에 남는다.**"""
        from apps.dsm.retention import LOGGER_NAME, sweep

        AuditLogs = apps.get_model("logger", "AuditLogs")
        result = sweep(dry_run=False, actor=self.user_a, reason="시험 — 감사 대조")

        row = AuditLogs._base_manager.get(pk=result["audit_id"])
        self.assertEqual(row.logger_name, LOGGER_NAME)
        self.assertEqual(row.api_name, "law02a:retention_sweep")
        after = row.data_after or {}
        self.assertFalse(after.get("dry_run"))
        self.assertGreaterEqual(after.get("deleted_total", 0), 2)
        #: 무엇을 지웠는지가 **식별자로** 남는다 — 수만 남으면 되짚을 수 없다.
        ids = [i for t in after.get("targets", []) for i in t.get("deleted_ids", [])]
        self.assertIn(self.old_record.pk, ids)
        #: ★ 체인 위에 얹혔는가 (LAW-08). 얹히지 않으면 뒤에서 조용히 고칠 수 있다.
        self.assertTrue(result["row_hash"])


class ObjectFailureKeepsTheRowTest(DsmFixture):
    """★ **바이트를 못 지웠으면 행을 남긴다.**

    행부터 지우면 그 바이트는 가리키는 것이 없는 채로 저장소에 영원히 남는다 —
    보존기간을 지킨다면서 정작 영상만 남기는 결과다.
    """

    def test_a_failed_object_delete_does_not_delete_the_row(self):
        from unittest.mock import patch

        from apps.dsm import retention

        Record = _model("StreamMonitorRecord")
        row = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="obj",
            object_path="gx-bucket/old/video.mp4")
        _age(Record, row.pk, field="created_at", days=999)

        with patch.object(retention, "_remove_object",
                          return_value="저장소가 죽었다"):
            result = retention.sweep(dry_run=False, actor=self.user_a,
                                     reason="시험 — 저장소가 죽었을 때")

        self.assertTrue(Record._base_manager.filter(pk=row.pk).exists(),
                        "바이트를 못 지웠는데 행을 지웠다 — 그 영상은 이제 고아다")
        self.assertGreaterEqual(result["object_failure_total"], 1,
                                "못 지운 사실이 응답에 안 남았다 — 조용한 실패다")


class TheSweepActuallyRunsTest(DsmFixture):
    """⑤ **주기가 걸려 있는가.** 「함수가 있다」와 「매일 돈다」는 다른 사실이다."""

    def test_the_beat_schedule_declares_the_sweep(self):
        from apps.dsm.retention import BEAT_TASK_NAME, sweep_is_scheduled

        self.assertTrue(
            sweep_is_scheduled(),
            f"beat 표에 {BEAT_TASK_NAME} 가 없다 — 그러면 「보관 기간이 지난 영상은 "
            f"자동으로 지워집니다」는 거짓 문장이고, 그 문장은 안내판에 인쇄된다")

    def test_the_policy_says_whether_it_is_enforced(self):
        from apps.dsm.retention import policy

        got = policy()
        self.assertIn("enforced", got)
        self.assertTrue(got["irreversible"],
                        "되돌릴 수 없다는 사실을 화면이 읽을 자리가 없다")
        self.assertTrue(got["legal_review"],
                        "법률 검토 대기라는 사실이 응답에서 사라졌다")

    def test_the_periodic_task_exists_and_is_not_a_preview(self):
        """★ 주기 실행은 **미리보기가 아니다.** 미리보기만 도는 주기는 「적었다」와 같다."""
        import inspect

        from common import ops_tasks

        self.assertTrue(hasattr(ops_tasks, "video_retention_sweep_beat"))
        source = inspect.getsource(ops_tasks.video_retention_sweep_beat)
        self.assertIn("dry_run=False", source)
