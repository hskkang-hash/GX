# -*- coding: utf-8 -*-
"""P-192 — `capture_service` ffmpeg 타임아웃 (2026-09-19 · 턴 W · 차선 U3).

닫는 문장 하나: **닿지 않는 카메라에 붙어 안 끝나는 프로세스 0.**

종전에는 `subprocess.run(cmd, capture_output=True, text=True)` 였다 — 타임아웃 인자가
없고 ffmpeg 쪽 소켓 타임아웃도 없었다. 그래서 닿지 않는 주소를 물면 ffmpeg 가 붙어
있었고, 부른 gunicorn·celery 일꾼도 함께 묶였다.

⚠⚠ **이 시험이 지키는 가장 중요한 한 줄은 `-stimeout` 이 아니라는 것이다.**

    판정문은 `-stimeout` 을 적었지만 컨테이너의 ffmpeg 는 **7.1.3** 이고 거기서
    `-stimeout` 은 삭제됐다 [실측 2026-09-19 · `gx-shell`]:

        Unrecognized option 'stimeout'.
        Error splitting the argument list: Option not found

    그대로 적었으면 **닿는 카메라까지 전부 즉시 실패**한다 — 타임아웃을 넣은 것이
    아니라 촬영을 끈 것이 된다. `test_stimeout_is_not_used` 가 그날을 막는다.

⚠ 단위 — `-timeout` 은 **마이크로초**다. 초로 적으면 15초가 15마이크로초가 되고,
  그러면 모든 촬영이 즉시 시간 초과다. `test_read_timeout_is_microseconds` 가 센다.

[실측 2026-09-19 · `gx-shell` · 닿지 않는 주소 넷]

    주소                                        종전        지금     ffmpeg 최대
    192.0.2.1:554 (RFC5737 TEST-NET)           21.25s      5.01s        0
    10.0.0.21:554 (턴 V 실측)                   21.12s      5.02s        0
    112.170.174.81:38554 (턴 V 실측)            21.15s      5.01s        0
    no-such-host.invalid:554 (이름 못 풂)         —         0.03s        0

이 시험들은 **망을 타지 않는다** — 망을 타면 망이 흔들리는 날 빨개지고, 빨간 시험은
곧 꺼진다. 대신 ① 명령의 모양 ② 못 닿을 때 ffmpeg 를 안 띄우는가 ③ 무시해도 죽이는가
를 본다. 망을 실제로 탄 수는 위 표(그리고 보고서)에 있다.
"""
from __future__ import annotations

import subprocess
import time
import unittest
from unittest import mock

from stream_monitors.services import capture_service as cs


class _FakeMonitor:
    """`StreamMonitor` 대역. 외부 카메라라 `ip_source` 가 그대로 주소가 된다."""

    def __init__(self, ip_source: str):
        self.is_external = True
        self.ip_source = ip_source


def _patch_monitor(url: str):
    patcher = mock.patch.object(cs, "StreamMonitor")
    SM = patcher.start()
    SM.objects.filter.return_value.first.return_value = _FakeMonitor(url)
    return patcher


class FfmpegCommandShapeTest(unittest.TestCase):
    """① 명령의 모양 — 실제로 부르지 않고 `cmd` 만 붙잡는다."""

    def _captured_cmd(self, url="rtsp://camera.example:554/live"):
        """`_capture_frame` 을 한 번 굴리고 ffmpeg 에 넘어간 `cmd` 를 돌려준다.

        접속 시험(`_probe_tcp`)은 **열린 것으로** 두고(그래야 ② 단계까지 간다),
        ffmpeg 는 실패로 둔다(그래야 MinIO 까지 안 간다).
        """
        patcher = _patch_monitor(url)
        self.addCleanup(patcher.stop)
        seen = {}

        def fake_run(cmd, timeout_sec):
            seen["cmd"] = cmd
            seen["timeout_sec"] = timeout_sec
            return 1, "stub failure"

        with mock.patch.object(cs, "_probe_tcp", return_value=""), \
                mock.patch.object(cs, "_run_ffmpeg", side_effect=fake_run):
            self.assertIsNone(cs.CaptureService()._capture_frame("gx-cam", ""))
        return seen

    def test_stimeout_is_not_used(self):
        """⚠ `-stimeout` 이 명령에 있으면 **이 판의 ffmpeg 는 즉시 죽는다.**

        7.1.3 에서 삭제된 이름이다. 누가 판정문 글자대로 되돌려 놓는 날 여기서 빨개진다.
        """
        cmd = self._captured_cmd()["cmd"]
        self.assertNotIn("-stimeout", cmd)

    def test_read_timeout_is_microseconds(self):
        """⚠ 단위 — 초가 아니라 **마이크로초**. 15 초 → `"15000000"`."""
        cmd = self._captured_cmd()["cmd"]
        self.assertIn("-timeout", cmd)
        value = cmd[cmd.index("-timeout") + 1]
        self.assertEqual(value, str(cs.CAPTURE_READ_TIMEOUT_SEC * 1_000_000))
        #: 여섯 자리 이상이어야 마이크로초다 — 초로 적으면 두 자리다.
        self.assertGreaterEqual(len(value), 7)

    def test_timeout_comes_before_input(self):
        """⚠ 입력 옵션이므로 `-i` **앞**이다. 뒤에 두면 조용히 아무 효과가 없다."""
        cmd = self._captured_cmd()["cmd"]
        self.assertLess(cmd.index("-timeout"), cmd.index("-i"))

    def test_process_wall_is_longer_than_connect_plus_read(self):
        """벽(③)이 ①+②보다 짧으면 ffmpeg 가 제 사유를 적기 전에 죽어 로그가 빈다."""
        self.assertGreater(
            cs.CAPTURE_PROCESS_TIMEOUT_SEC,
            cs.CAPTURE_CONNECT_TIMEOUT_SEC + cs.CAPTURE_READ_TIMEOUT_SEC)
        seen = self._captured_cmd()
        self.assertEqual(seen["timeout_sec"], cs.CAPTURE_PROCESS_TIMEOUT_SEC)


class UnreachableCameraTest(unittest.TestCase):
    """② 못 닿으면 **ffmpeg 를 아예 안 띄운다** — P-192 가 세라고 한 그 수가 0 이다."""

    def test_no_ffmpeg_process_when_unreachable(self):
        patcher = _patch_monitor("rtsp://192.0.2.1:554/cam")
        self.addCleanup(patcher.stop)
        with mock.patch.object(cs, "_probe_tcp",
                               return_value="카메라에 5초 안에 접속하지 못했습니다."), \
                mock.patch.object(cs, "_run_ffmpeg") as run, \
                mock.patch.object(subprocess, "Popen") as popen:
            self.assertIsNone(cs.CaptureService()._capture_frame("gx-cam", ""))
        run.assert_not_called()
        popen.assert_not_called()

    def test_probe_has_a_deadline_and_says_why(self):
        """접속 시험은 **문턱 안에** 끝나고 사유를 한 줄로 낸다 (망을 안 탄다)."""
        with mock.patch.object(cs.socket, "create_connection",
                               side_effect=cs.socket.timeout()):
            started = time.monotonic()
            reason = cs._probe_tcp("rtsp://192.0.2.1:554/cam", 5)
            self.assertLess(time.monotonic() - started, 2)
        self.assertIn("5초", reason)
        self.assertTrue(reason)

    def test_probe_names_the_dns_failure_separately(self):
        """이름을 못 푼 것과 못 닿은 것은 **다른 사실**이다 — 뭉치면 어디를 고칠지 모른다."""
        with mock.patch.object(cs.socket, "create_connection",
                               side_effect=cs.socket.gaierror()):
            reason = cs._probe_tcp("rtsp://no-such-host.invalid:554/cam", 5)
        self.assertIn("이름", reason)

    def test_probe_uses_default_rtsp_port_when_absent(self):
        with mock.patch.object(cs.socket, "create_connection") as conn:
            cs._probe_tcp("rtsp://camera.example/live", 5)
        self.assertEqual(conn.call_args.args[0], ("camera.example", 554))


class HardWallTest(unittest.TestCase):
    """③ ffmpeg 가 ①②를 **무시해도** 우리가 끝낸다."""

    def test_kills_a_process_that_ignores_the_deadline(self):
        started = time.monotonic()
        returncode, stderr = cs._run_ffmpeg(["sleep", "120"], 2)
        elapsed = time.monotonic() - started
        #: 벽 2초 + SIGTERM 유예. 120초를 다 기다리지 않는다.
        self.assertLess(elapsed, 2 + cs._KILL_GRACE_SEC + 3)
        #: 신호로 죽었으므로 음수다 (0 이면 곱게 끝난 것이라 벽이 안 선 것이다).
        self.assertLess(returncode, 0)
        #: 로그만 보고 「왜 이 줄이 실패했나」를 알 수 있어야 한다.
        self.assertIn("강제 종료", stderr)

    def test_normal_exit_is_untouched(self):
        returncode, _ = cs._run_ffmpeg(["true"], 10)
        self.assertEqual(returncode, 0)


class RedactTest(unittest.TestCase):
    """로그에 **자격이 안 적힌다** — 외부 카메라 주소는 `id:pw@host` 꼴이 흔하다."""

    def test_credentials_never_reach_the_log(self):
        redacted = cs._redact("rtsp://gxoperator:hunter2@cam.example:554/live")
        self.assertNotIn("hunter2", redacted)
        self.assertNotIn("gxoperator", redacted)
        #: 그래도 **어느 카메라인지**는 남아야 한다 — 안 남으면 고칠 데를 못 찾는다.
        self.assertIn("cam.example:554", redacted)

    def test_plain_url_is_readable(self):
        self.assertEqual(cs._redact("rtsp://192.0.2.1:554/live"),
                         "rtsp://192.0.2.1:554/live")
