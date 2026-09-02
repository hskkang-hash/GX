# -*- coding: utf-8 -*-
"""**켠 것이 실제로 도는지** 시험이 본다 (D-377 착시 ⑨).

D-377 이 이름 붙인 착시는 「코드가 있으면 동작한다」고 읽는 것이다. 그 착시의 재발이
바로 **「켜기만 하고 안 도는 것」**이다 — beat 표에 한 줄 넣어 놓고 그 줄이 가리키는
태스크가 없어도, 표는 초록으로 보인다.

이 파일이 그 자리를 막는다. 셋을 본다:

    ① beat 표의 **모든 항목**이 실제로 등록된 태스크를 가리키는가
       ★ 이 시험은 실측이 만들었다. `config/celery.py` 에 **주석으로 꺼진 채 오타가 난**
         항목이 있었다 — `flight_log.task.…`(실제 모듈은 `flight_log.tasks`).
         꺼져 있어 아무도 몰랐고, 켜는 날 15분마다 `NotRegistered` 를 낼 참이었다.
         **꺼진 것이 틀린 것을 숨긴다.** 그래서 표 전체를 이름으로 대조한다.

    ② 이번 턴에 **켠 것**(감사 로그 보존기간 집행)이 실제로 돌고, 무엇을 했는지 말하는가

    ③ 지난 턴에 켠 것(감시·백업)도 실제로 도는가 — 켤 때 시험을 안 붙였으므로 여기서 갚는다

⚠ 여기서 「돈다」는 **태스크 함수가 끝까지 실행되고 판정을 돌려준다**는 뜻이다.
  판정이 `OK` 여야 한다는 뜻이 아니다 — 이 환경에는 MinIO 도 감사 로그도 없을 수 있고,
  그때 `UNKNOWN`/`SKIPPED` 를 **돌려주는 것**이 옳은 동작이다 (D-301).
"""
from __future__ import annotations

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone


class BeatScheduleWiringTest(TestCase):
    """① beat 표의 모든 줄이 **실재하는 태스크**를 가리킨다."""

    def test_every_beat_entry_points_at_a_registered_task(self):
        from config.celery import app

        schedule = app.conf.beat_schedule
        self.assertTrue(schedule, "beat 표가 비었다 — 열거기가 눈이 멀었다 (D-301)")

        # autodiscover 는 워커가 뜰 때 돈다. 시험 프로세스에서도 같은 이름 공간을
        # 갖도록 강제한다 — 안 하면 「등록 안 됨」이 **시험 환경의 사실**이 되어 버린다.
        app.loader.import_default_modules()

        missing = []
        for name, entry in schedule.items():
            task_name = entry.get("task", "")
            if task_name not in app.tasks:
                missing.append(f"{name}: «{task_name}» 이 등록된 태스크가 아니다")

        self.assertEqual(
            missing, [],
            "beat 표가 없는 태스크를 가리킨다 — 켜는 날 주기마다 NotRegistered 가 난다:\n"
            + "\n".join(missing))

    def test_commented_out_beat_lines_still_name_a_real_module(self):
        """★ **꺼진 줄도 이름은 맞아야 한다.**

        꺼진 항목은 언젠가 켜진다. 켜는 사람은 그 줄이 옳다고 믿고 켜고, 틀렸으면
        그때 처음 안다 — 운영에서. 그래서 주석 안의 태스크 경로도 모듈까지는 본다.
        """
        import importlib
        import re
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / "config" / "celery.py").read_text(
            encoding="utf-8")
        commented = re.findall(r'^\s*#.*["\']task["\']\s*:\s*["\']([\w\.]+)["\']',
                               source, re.M)
        self.assertTrue(commented,
                        "주석으로 꺼진 beat 항목을 한 줄도 못 찾았다 — "
                        "이 시험이 아무것도 보지 않고 있다 (D-301)")
        broken = []
        for dotted in commented:
            module = dotted.rsplit(".", 1)[0]
            try:
                importlib.import_module(module)
            except ImportError as exc:
                broken.append(f"«{dotted}» — 모듈 {module} 을 못 읽는다: {exc}")
        self.assertEqual(broken, [],
                         "꺼진 beat 항목의 태스크 경로가 틀렸다:\n" + "\n".join(broken))


class TurnedOnTasksActuallyRunTest(TestCase):
    """②③ 켠 것이 **실행되고 판정을 돌려준다.**"""

    def test_audit_purge_beat_runs_and_reports_what_it_did(self):
        from common.ops_tasks import ops_audit_purge_beat

        payload = ops_audit_purge_beat()
        self.assertIn("verdict", payload)
        self.assertIn(payload["verdict"], {"OK", "UNKNOWN", "ALARM", "SKIPPED"})
        if payload["verdict"] == "OK":
            # 「돌았다」가 아니라 **「무엇을 했다」**를 말해야 한다 (D-290).
            for key in ("rows_before", "rows_after", "purged"):
                self.assertIn(key, payload, f"{key} 가 없다 — 무엇을 지웠는지 말하지 않는다")
            self.assertGreaterEqual(payload["rows_before"], payload["rows_after"])

    @override_settings(OPS_AUDIT_PURGE_ENABLED=False)
    def test_audit_purge_says_it_skipped_instead_of_going_quiet(self):
        """끈 것은 **끈 채로 말한다.** 조용히 아무것도 안 하면 「돌았는데 아무 일 없었다」와
        구별되지 않는다 (D-290)."""
        from common.ops_tasks import ops_audit_purge_beat

        payload = ops_audit_purge_beat()
        self.assertEqual(payload["verdict"], "SKIPPED")
        self.assertIn("OPS_AUDIT_PURGE_ENABLED", payload["reason"])

    def test_audit_purge_keeps_rows_inside_the_retention_window(self):
        """★ **보존기간 안의 것은 남는다.** 「지웠다」만 보면 전부 지워도 초록이다."""
        try:
            from core.logger.models import AuditLogs
        except ImportError:
            self.skipTest("dj-core 감사 로그 모델이 없다 — 판정 불가지 통과가 아니다")

        from common.ops_tasks import ops_audit_purge_beat

        fresh = AuditLogs._base_manager.create()
        AuditLogs._base_manager.filter(pk=fresh.pk).update(
            create_datetime=timezone.now() - timedelta(days=1))
        stale = AuditLogs._base_manager.create()
        AuditLogs._base_manager.filter(pk=stale.pk).update(
            create_datetime=timezone.now() - timedelta(days=4000))

        payload = ops_audit_purge_beat()
        if payload["verdict"] != "OK":
            self.skipTest(f"정리가 돌지 않았다({payload['verdict']}) — 판정 불가")

        self.assertTrue(AuditLogs._base_manager.filter(pk=fresh.pk).exists(),
                        "보존기간 **안**의 감사 로그가 지워졌다 — 지우기가 너무 넓다")
        self.assertFalse(AuditLogs._base_manager.filter(pk=stale.pk).exists(),
                         "보존기간 **밖**의 감사 로그가 남았다 — 보존기간이 도는 자리가 없다")

    def test_monitor_beat_runs(self):
        """D-373 이 켠 것. 켤 때 시험을 안 붙였으므로 여기서 갚는다."""
        from common.ops_tasks import ops_monitor_beat

        payload = ops_monitor_beat()
        self.assertIn(payload.get("verdict"), {"OK", "UNKNOWN", "ALARM"})

    def test_backup_beat_runs_and_says_it_is_off(self):
        from common.ops_tasks import ops_backup_beat, ops_status

        payload = ops_backup_beat()
        self.assertIn(payload.get("verdict"), {"OK", "UNKNOWN", "ALARM", "SKIPPED"})
        # 상태를 묻는 자리가 **끈 것을 켠 것처럼 말하지 않는다** (D-375).
        self.assertIn("백업_주기", ops_status())


class DormantAuditorSelfTest(TestCase):
    """판정 전에 **판정기부터** (D-277 · D-350)."""

    def test_verify_dormant_self_test_passes(self):
        import subprocess
        import sys
        from pathlib import Path

        # 컨테이너에서는 저장소가 `/repo` 로 마운트되고 앱은 `/app` 에 복사된다 —
        # 그래서 자리를 하나로 못 박지 않는다. 어느 쪽에도 없으면 **건너뛰되
        # 그 사실을 말한다**(D-301) — 「없어서 통과」로 두지 않는다.
        candidates = [
            Path(__file__).resolve().parents[2] / "scripts" / "verify_dormant.py",
            Path("/repo/scripts/verify_dormant.py"),
        ]
        script = next((c for c in candidates if c.is_file()), None)
        if script is None:
            self.skipTest("verify_dormant.py 를 %s 어디에서도 못 찾았다 — 판정 불가"
                          % ", ".join(str(c) for c in candidates))
        out = subprocess.run([sys.executable, str(script), "--self-test"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0,
                         f"잠자는 기능 판정기의 자기시험이 깨졌다:\n{out.stdout}\n{out.stderr}")

    def test_celery_signal_hooks_are_not_reported_dormant(self):
        """★ 출생 표본을 **저장소 실물로** 박는다 (D-310 · D-393).

        합성 fixture 는 규칙이 있는지를 본다. 이 시험은 **그 규칙이 오늘 이 저장소의
        그 세 함수에 실제로 걸리는지**를 본다 — D-388 이 ㉮「켜야 할 것」으로 냈던
        `config/celery.py` 의 시그널 훅 셋이다. 셋은 `@worker_process_init.connect`
        등으로 **처음부터 배선돼 있었다.** 켜라고 낸 것이 이미 켜져 있었다.

        ⚠ 이 시험이 빨개지는 길은 둘이다. 둘 다 알아야 할 일이다:
          ① 판정기가 시그널 배선을 다시 못 보게 됐다 (규칙이 사라졌다)
          ② 누가 `celery.py` 에서 `.connect` 배선을 떼어 냈다 — **그때는 진짜 잠든다**
        """
        import ast
        import importlib.util
        from pathlib import Path

        candidates = [
            Path(__file__).resolve().parents[2] / "scripts" / "verify_dormant.py",
            Path("/repo/scripts/verify_dormant.py"),
        ]
        script = next((c for c in candidates if c.is_file()), None)
        if script is None:
            self.skipTest("verify_dormant.py 를 못 찾았다 — 판정 불가 (D-301)")

        spec = importlib.util.spec_from_file_location("_vd_for_test", script)
        vd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vd)

        celery_py = script.parent.parent / "backend" / "config" / "celery.py"
        if not celery_py.is_file():
            celery_py = Path("/repo/backend/config/celery.py")
        if not celery_py.is_file():
            self.skipTest("backend/config/celery.py 를 못 찾았다 — 판정 불가 (D-301)")

        tree = ast.parse(celery_py.read_text(encoding="utf-8", errors="replace"))
        hooks = {
            node.name: vd._wired_by_signal(node)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        expected = ["init_worker_process",
                    "close_db_connections_before_task",
                    "close_db_connections_after_task"]
        missing = [n for n in expected if n not in hooks]
        self.assertEqual(missing, [],
                         "config/celery.py 에서 시그널 훅이 사라졌다: %s" % missing)
        unwired = [n for n in expected if not hooks[n]]
        self.assertEqual(unwired, [],
                         "`@<시그널>.connect` 배선을 판정기가 못 봤다 — D-388 이 이 셋을 "
                         "㉮「켜야 할 것」으로 냈던 그 자리다: %s" % unwired)

        # 음성 — **파일째 면제가 아니다.** 배선 없는 함수는 여전히 배선 없음으로 나와야 한다
        plain = [n for n, w in hooks.items() if not w]
        self.assertTrue(plain,
                        "celery.py 의 함수 전부가 「배선됨」으로 나왔다 — 파일째 면제된 것이다")
