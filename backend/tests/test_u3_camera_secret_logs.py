# -*- coding: utf-8 -*-
"""P-200 — **카메라 자격이 로그에 적히지 않는다** (2026-09-20 · 턴 X · 차선 U3).

닫는 문장 하나: **`StreamMonitor.ip_source` 의 비밀번호가 로그 줄에 0번 나온다.**

왜 이 시험이 있나 — 턴 W 에 막았고, 턴 X 에 **그대로 살아 있었다**
-----------------------------------------------------------------
턴 W(P-192)에 `capture_service.py` 의 두 줄을 `_redact` 로 막았다. 그런데 **지키는
판정기를 안 세웠다.** 그래서 옆 파일에서 같은 줄 **일곱 개**가 멀쩡히 살아 있었다
[실측 2026-09-20 · `stream_monitor_services.py` `:651 :688 :744 :1247 :1254 :1275 :1286`].
한 파일 안에 숨은 방어는 옆 파일을 못 지킨다.

★ 이 시험은 **씻개가 옳게 씻는가**와 **저장소에 새는 줄이 있는가**를 함께 본다.
  앞엣것만 있으면 「씻개는 멀쩡한데 아무도 안 부른다」가 초록으로 지나간다.

★ 살아 있는 로그(`docker logs`)를 실제로 훑는 쪽은 게이트다 —
  `docs/agent/verify_gates.sh --gate camera-secret-logs` (`scripts/verify_camera_secret_logs.py`).
  시험은 컨테이너에 못 닿으므로 **코드 면**을 맡고, 게이트가 **로그 면**을 맡는다.

⚠ 이 파일에 적힌 자격은 전부 **가짜**다(`gxfakecam` / `NOT_A_REAL_PW`). 진짜 카메라
  자격은 시험에도 안 적는다 — 저장소에 적히는 순간 그것은 더 이상 비밀이 아니다.

캐시 처리: 해당 없음 — HTTP 를 한 번도 안 때린다. 순수 함수와 **파일 바이트**만 본다
(응답 캐시도 스레드로컬 요청도 이 시험에 닿지 않는다 · D-341 · P-181).
"""
import importlib.util
import unittest
from pathlib import Path

from stream_monitors.services import capture_service
from stream_monitors.services.url_redaction import redact_payload, redact_url

#: 컨테이너 안에서 저장소 뿌리는 `/repo` 다(`./:/repo:ro` 마운트 · D-285 (4)).
#: 호스트에서 돌리면 `backend/tests/..` 위로 올라가 찾는다.
REPO_ROOT_CANDIDATES = ("/repo",)
JUDGE_NAME = "verify_camera_secret_logs.py"


def _find_judge():
    here = Path(__file__).resolve()
    for root in [*(Path(c) for c in REPO_ROOT_CANDIDATES), *here.parents[1:4]]:
        candidate = root / "scripts" / JUDGE_NAME
        if candidate.is_file():
            return candidate
    return None

#: 가짜 자격. 모양만 진짜와 같다.
FAKE = "rtsp://gxfakecam:NOT_A_REAL_PW@cam.invalid:554/live"
FAKE_USER = "gxfakecam"
FAKE_PW = "NOT_A_REAL_PW"


def _load_judge():
    path = _find_judge()
    assert path is not None, (
        "게이트 정본 `scripts/%s` 를 찾지 못했습니다. 컨테이너라면 `/repo` 마운트가 "
        "빠진 것입니다 (D-285 (4)). ★ 이 시험은 skip 하지 않습니다 — 못 찾으면 "
        "짝을 **확인하지 못한 것**이고, 확인 못 한 것은 초록이 아닙니다." % JUDGE_NAME)
    spec = importlib.util.spec_from_file_location("gx_judge_p200", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RedactUrlTest(unittest.TestCase):
    """씻개 — **자격은 지우고, 사람이 쓸 것은 남긴다.**"""

    def test_credentials_are_gone(self):
        out = redact_url(FAKE)
        self.assertNotIn(FAKE_PW, out)
        self.assertNotIn(FAKE_USER, out)
        self.assertIn("***@", out)

    def test_host_and_path_survive(self):
        # 다 지우면 로그가 쓸모없어진다 — **어느 카메라였나**는 남아야 한다.
        out = redact_url(FAKE)
        self.assertIn("cam.invalid:554", out)
        self.assertIn("/live", out)

    def test_internal_url_is_untouched(self):
        # 내부 미디어 서버 주소에는 자격이 없다. 건드리면 사람이 읽을 것을 뺏는다.
        inner = "rtsp://mediamtx:8554/stream/abc123"
        self.assertEqual(redact_url(inner), inner)

    def test_query_string_is_dropped(self):
        # 자격이 `?user=…&pass=…` 로 오는 카메라가 있다. 통째로 버린다.
        out = redact_url("rtsp://cam.invalid:554/live?user=%s&pass=%s" % (FAKE_USER, FAKE_PW))
        self.assertNotIn(FAKE_PW, out)
        self.assertNotIn(FAKE_USER, out)

    def test_non_url_is_returned_as_is(self):
        for value in ("", "abc", None, 7):
            self.assertEqual(redact_url(value), value)

    def test_a_response_body_that_merely_mentions_a_url_is_untouched(self):
        # ⚠ 「`://` 가 들어 있으면 주소」로 보면 **본문 전체가 주소로 바뀐다** —
        #   그러면 로그에서 고장 원인이 사라진다. 막는 것과 눈을 가리는 것은 다르다.
        body = "<html><body>502 from http://ai-grpc:9000/start_record</body></html>"
        self.assertEqual(redact_url(body), body)
        self.assertEqual(redact_payload({"api_response": body})["api_response"], body)

    def test_capture_service_uses_the_shared_one(self):
        # ★ `capture_service._redact` 가 **딴 살림**을 차리면 두 파일이 다른 규칙으로
        #   씻는다. 턴 W 의 결함이 정확히 그 모양이었다.
        self.assertIs(capture_service._redact, redact_url)


class RedactPayloadTest(unittest.TestCase):
    """**한 겹 건너 새던 자리** — dict 를 통째로 찍으면 자격이 그대로 나간다."""

    def test_nested_values_are_redacted(self):
        body = {"rtsp_url": FAKE, "stream_id": "cam-1",
                "extra": [{"input_rtsp": FAKE}]}
        out = redact_payload(body)
        text = repr(out)
        self.assertNotIn(FAKE_PW, text)
        self.assertNotIn(FAKE_USER, text)
        self.assertEqual(out["stream_id"], "cam-1")

    def test_original_is_not_touched(self):
        # ⚠ 원본을 씻으면 **카메라에 못 붙는다** — 나가는 요청은 진짜 주소라야 한다.
        body = {"rtsp_url": FAKE}
        redact_payload(body)
        self.assertEqual(body["rtsp_url"], FAKE)

    def test_non_string_values_survive(self):
        body = {"n": 3, "flag": True, "none": None}
        self.assertEqual(redact_payload(body), body)


class NoLeakingLogLineInRepoTest(unittest.TestCase):
    """저장소에 **씻기지 않고 로그로 가는 줄이 0개**인가 — 판정기를 그대로 부른다.

    ★ 기대값을 손으로 안 적는다. 게이트가 쓰는 **그 판정기**를 부른다 — 두 벌로 두면
      시험만 통과하고 게이트는 다른 규칙으로 도는 상태가 만들어진다.
    """

    def setUp(self):
        self.judge = _load_judge()

    def test_judge_self_test_passes(self):
        # 판정기가 눈이 멀었으면 「0건」은 아무 뜻이 없다 (D-350).
        self.assertEqual(self.judge.self_test(), self.judge.EXIT_OK)

    def test_repo_has_no_unredacted_log_line(self):
        findings, nfiles, broken = self.judge.scan_static()
        self.assertGreater(nfiles, 0, "훑은 파이썬 파일이 0개 — 검사 못 한 것이지 0건이 아니다")
        self.assertEqual(broken, [], "못 읽은 파일이 있다 — 회색은 초록이 아니다")
        self.assertEqual(
            findings, [],
            "카메라 자격이 씻기지 않고 로그로 간다:\n  " +
            "\n  ".join("%s:%d %s" % f for f in findings))

    def test_planting_the_turn_w_line_turns_it_red(self):
        # ★ **음성 대조** — 막은 줄을 한 번 벗겨 심으면 판정기가 잡아야 한다.
        #   안 잡히면 위의 「0건」은 판정이 아니라 침묵이다.
        planted = (
            "def capture(stream_id):\n"
            "    rtsp_url = stream_monitor.ip_source\n"
            "    logger.info(f'RTSP: {rtsp_url}')\n"
        )
        findings, why = self.judge.analyze_source(planted, "<심은 것>")
        self.assertEqual(why, "")
        self.assertEqual(len(findings), 1)

    def test_live_log_pattern_catches_a_planted_line(self):
        # ★ 로그 면의 음성 대조. 게이트는 이 정규식으로 `docker logs` 를 훑는다.
        self.assertTrue(self.judge.CRED_RE.search("INFO RTSP URL: " + FAKE))
        self.assertFalse(self.judge.CRED_RE.search(
            "INFO RTSP URL: rtsp://***@cam.invalid:554/live"))
        self.assertFalse(self.judge.CRED_RE.search(
            "INFO RTSP URL: rtsp://cam.invalid:554/live"))

    def test_report_masks_what_it_found(self):
        # 판정기가 걸린 줄을 **그대로 옮기면** 판정기가 유출기가 된다.
        masked = self.judge.mask_hit("INFO RTSP URL: " + FAKE)
        self.assertNotIn(FAKE_PW, masked)
        self.assertNotIn(FAKE_USER, masked)

    def test_sanitizer_names_match_the_product(self):
        # 씻개 이름을 바꾸면서 판정기를 안 고치면 **씻고 있는데도 빨강**이 난다.
        # 조용히 갈리지 않게 여기서 맞댄다.
        self.assertIn("redact_url", self.judge.SANITIZERS)
        self.assertIn("redact_payload", self.judge.SANITIZERS)
        self.assertIn("_redact", self.judge.SANITIZERS)

    def test_taint_source_is_the_real_model_field(self):
        # 샘이 실재하지 않는 칸 이름이면 ②는 **언제나 초록**이다.
        from stream_monitors.models import StreamMonitor
        names = {f.name for f in StreamMonitor._meta.get_fields()}
        for attr in self.judge.TAINT_SOURCE_ATTRS:
            self.assertIn(attr, names,
                          "판정기가 좇는 칸 '%s' 가 모델에 없다" % attr)
