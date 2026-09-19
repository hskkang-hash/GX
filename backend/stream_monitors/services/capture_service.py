import os
import time
import datetime
import socket
import uuid
import subprocess
import urllib.parse

from stream_monitors.models import StreamMonitor, StreamMonitorAIModel
from stream_monitors.schemas.schemas_djantic_out import CaptureResponse
from django.conf import settings
from stream_monitors.utils.minio_client import minio_client
import logging


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# P-192 - ffmpeg 타임아웃 (턴 W · 차선 U3)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★★ 고친 것 한 줄: **닿지 않는 카메라에 붙어 안 끝나는 프로세스 0.**
#
#   종전에는 `subprocess.run(cmd, capture_output=True, text=True)` 였다 — 타임아웃
#   인자가 없고, ffmpeg 쪽에도 소켓 타임아웃 옵션이 없었다. 닿지 않는 주소를 물면
#   그 프로세스는 **운영체제의 TCP 재시도가 끝날 때까지** 붙어 있고, 그동안 부른
#   쪽(gunicorn 일꾼 · celery 일꾼)도 함께 묶인다.
#
# ⚠⚠ **`-stimeout` 은 이 ffmpeg 판에 없다** [실측 2026-09-19 · `gx-shell`]
#
#   판정문은 `-stimeout` 을 적었지만, 컨테이너의 ffmpeg 는 **7.1.3** 이고 거기서
#   `-stimeout` 은 삭제됐다. 그대로 적었으면 이렇게 됐다:
#
#       $ ffmpeg -rtsp_transport tcp -stimeout 5000000 -i rtsp://...
#       Unrecognized option 'stimeout'.
#       Error splitting the argument list: Option not found
#
#   즉 **닿는 카메라까지 전부 즉시 실패**한다 — 타임아웃을 넣은 것이 아니라 촬영을
#   끈 것이 된다. 이 판의 이름은 `-timeout` 이고 단위는 **마이크로초**다:
#
#       -timeout <int64>  set timeout (in microseconds) of socket I/O operations
#
# ★ **실측** [2026-09-19 · `gx-shell` · 닿지 않는 주소 셋(192.0.2.1 · 10.0.0.21 ·
#   112.170.174.81)에 각각]. 세 주소 모두 같은 수가 나왔다:
#
#       옵션 없음(종전)        21.1 ~ 21.3 초   rc=145  "Connection refused"
#       -timeout  5000000       5.10 ~  5.14 초  rc=146  "Connection timed out"
#       -timeout 15000000      15.11 ~ 15.17 초  rc=146  "Connection timed out"
#
#   5,000,000 이 5초로 나왔으므로 **단위가 마이크로초임이 실물로 확인됐다**(초로
#   읽혔다면 5,000,000초 = 58일이라 200초 벽에 걸렸을 것이다).
#
# ★ 문턱이 **셋**인 이유 — 하나로는 판정문의 「connect 5 · read 15」를 못 적는다.
#   ffmpeg 의 `-timeout` 은 소켓 I/O 하나를 재므로, 그 값을 5로 두면 읽기까지 5초가
#   되고 15로 두면 닿지 않는 주소에 15초를 붙어 있는다. 그래서 잇는다:
#
#     ① 접속(5초)  — 파이썬이 **먼저** TCP 를 두드린다. 안 열리면 ffmpeg 를
#                    **아예 띄우지 않는다**. 닿지 않는 카메라에서 ffmpeg 프로세스
#                    수가 0 이 되는 자리가 여기다.
#     ② 읽기(15초) — ffmpeg `-timeout 15000000`. 붙긴 붙었는데 프레임이 안 오는
#                    카메라를 끊는다.
#     ③ 벽(25초)  — `Popen` + `communicate(timeout=…)`. **ffmpeg 가 ①②를 무시해도
#                    우리가 끝낸다.** 넘기면 SIGTERM → 3초 뒤 SIGKILL 이다.
#
#   셋 다 `settings` 로 덮을 수 있다 — 현장 카메라가 느리다고 코드를 고치지 않는다.

def _sec(name: str, default: int) -> int:
    """`settings` 에 있으면 그 값, 없으면 기본값. **초 단위**로만 다룬다.

    마이크로초 환산은 명령을 짤 때 **한 곳에서만** 한다(`* 1_000_000`) — 단위를
    두 곳에서 곱하면 그중 한 곳이 반드시 틀리고, 틀린 쪽은 5초가 5마이크로초가 된다.
    """
    value = getattr(settings, name, default)
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


#: ① 접속 — 파이썬이 TCP 를 두드려 보는 시간(초).
CAPTURE_CONNECT_TIMEOUT_SEC = _sec("CAPTURE_CONNECT_TIMEOUT_SEC", 5)
#: ② 읽기 — ffmpeg 소켓 I/O 타임아웃(초). 명령에는 **마이크로초**로 들어간다.
CAPTURE_READ_TIMEOUT_SEC = _sec("CAPTURE_READ_TIMEOUT_SEC", 15)
#: ③ 벽 — 파이썬이 ffmpeg 를 죽이는 시간(초). ①+②보다 길어야 한다 — 짧으면
#:   ffmpeg 가 제 사유(「연결 시간 초과」)를 적기 전에 죽어서 로그가 빈다.
CAPTURE_PROCESS_TIMEOUT_SEC = _sec(
    "CAPTURE_PROCESS_TIMEOUT_SEC",
    CAPTURE_CONNECT_TIMEOUT_SEC + CAPTURE_READ_TIMEOUT_SEC + 5)
#: SIGTERM 뒤 SIGKILL 까지 기다리는 시간(초).
_KILL_GRACE_SEC = 3

#: RTSP 기본 포트. 주소에 포트가 없으면 이것으로 두드린다.
_DEFAULT_RTSP_PORT = 554


def _redact(url: str) -> str:
    """로그에 적기 전에 **자격을 지운다**.

    ⚠ 종전 코드는 `print("rtsp_url: ", rtsp_url)` 과 `logger.info(f"… RTSP: {rtsp_url}")`
      로 주소를 **그대로** 적었다. 외부 카메라 주소는 `rtsp://아이디:비밀번호@호스트/…`
      꼴이 흔하고(`StreamMonitor.ip_source`), 그러면 카메라 비밀번호가 접근 로그에
      남는다. 로그 줄은 지우지 않는 것이 규약이라(D-004 회전) 애초에 안 적는다.
    """
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "(주소 해석 실패)"
    if not parts.hostname:
        return url
    host = parts.hostname
    if parts.port:
        host = f"{host}:{parts.port}"
    if parts.username or parts.password:
        host = f"***@{host}"
    return urllib.parse.urlunsplit((parts.scheme, host, parts.path, "", ""))


def _probe_tcp(url: str, timeout_sec: int) -> str:
    """① 접속 — 주소의 TCP 문을 두드린다. 열리면 `""`, 안 열리면 **사유 한 줄**.

    ★ 왜 ffmpeg 에 맡기지 않나: ffmpeg 에게 「접속 5초 · 읽기 15초」를 따로 줄 수단이
      이 판에 없다(`-timeout` 하나가 소켓 I/O 전부를 잰다). 그리고 여기서 걸러 내면
      닿지 않는 카메라에 대해 **ffmpeg 프로세스가 하나도 안 뜬다** — P-192 가 세라고
      한 그 수가 0 이 되는 자리다.
    ★ 값은 한 글자도 안 적는다 — 사유에도 `_redact` 한 주소만 들어간다.
    """
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname
        port = parts.port or _DEFAULT_RTSP_PORT
    except ValueError:
        return "주소를 해석할 수 없습니다."
    if not host:
        return "주소에 호스트가 없습니다."
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return ""
    except socket.timeout:
        return (f"카메라에 {timeout_sec}초 안에 접속하지 못했습니다 "
                f"({_redact(url)} · 접속 시간 초과).")
    except socket.gaierror:
        return f"카메라 주소의 이름을 풀지 못했습니다 ({_redact(url)})."
    except OSError as exc:
        waited = time.monotonic() - started
        return (f"카메라에 접속하지 못했습니다 ({_redact(url)} · "
                f"{exc.__class__.__name__} · {waited:.1f}초).")


def _run_ffmpeg(cmd: list, timeout_sec: int):
    """③ 벽 — ffmpeg 를 띄우고 **반드시 끝낸다**. `(returncode, stderr)` 를 낸다.

    ★ `subprocess.run(..., timeout=…)` 도 죽이기는 하지만, 여기서는 **끊는 순서를
      눈에 보이게** 쓴다: SIGTERM 으로 한 번 부탁하고(그래야 ffmpeg 가 파일을 닫는다)
      3초 안에 안 죽으면 SIGKILL 이다. ffmpeg 가 ①②를 무시해도 여기서 끝난다.
    ★ 넘겨서 죽인 경우 `returncode` 는 음수(신호)이고, `stderr` 에는 **우리가 적은
      한 줄**이 붙는다 — 로그만 보고 「왜 이 줄이 실패했나」를 알 수 있어야 한다.
    """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    try:
        _, stderr = proc.communicate(timeout=timeout_sec)
        return proc.returncode, stderr
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=_KILL_GRACE_SEC)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate()
        note = (f"[capture_frame] ffmpeg 가 {timeout_sec}초를 넘겨 강제 종료했습니다 "
                f"(SIGTERM -> {_KILL_GRACE_SEC}초 -> SIGKILL).")
        return proc.returncode, (stderr or "") + "\n" + note


class CaptureService:
    """Service class for handling image capture operations."""

    def capture_image(self, stream_id: str, ai_model_code: str, group_code: str = None) -> CaptureResponse:
        """
        Capture an image from a stream and save it to storage.

        Args:
            stream_id: ID of the stream to capture from
            ai_model_code: Code of the AI model to capture from
            group_code: Code of the group to capture from
        Returns:
            CaptureResponse: Information about the captured image

        Raises:
            ValueError: If stream not found or no frame available
            Exception: For other capture-related errors
        """
        try:
            capture_result = self._capture_frame(stream_id, ai_model_code, group_code)

            return CaptureResponse(
                stream_id=stream_id,
                object_path=capture_result,
                message='',
                success=capture_result is not None
            )

        except ValueError as e:
            logger.warning(f"Capture validation error for stream {stream_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error capturing image from stream {stream_id}: {e}")
            raise Exception(f"Failed to capture image: {str(e)}")

    def _capture_frame(self, stream_id: str, ai_model_code: str, group_code: str = None) -> str | None:
        """
        Capture a frame from an RTSP stream and upload it to MinIO using the shared MinioClient.

        Args:
            stream_id (str): ID of the stream
            ai_model_code (str): Code of the AI model to capture from
            group_code (str): Code of the group to capture from
        Returns:
            str | None: MinIO object path (e.g. "images/stream_id/....jpg") or None if failed
        """
        rtsp_url = f"{settings.RTSP_URL}/stream/{stream_id}"
        stream_monitor = StreamMonitor.objects.filter(code=stream_id).first()
        if stream_monitor.is_external:
            rtsp_url = stream_monitor.ip_source
        if ai_model_code and ai_model_code != "":
            try:
                rtsp_url = f"{settings.RTSP_URL}/stream/ai_{stream_id}"
                # if stream_monitor.is_external:
                #     rtsp_url = stream_monitor.ip_source
            except StreamMonitorAIModel.DoesNotExist:
                rtsp_url = f"{settings.RTSP_URL}/stream/{stream_id}"
        #: ⚠ 주소를 **그대로 적지 않는다** — 외부 카메라 주소에는 자격이 섞여 있다(`_redact`).
        logger.info(
            f"[capture_frame] Starting capture for {stream_id} from RTSP: {_redact(rtsp_url)}")

        # check if folder ettings.IMG_DIR not exist, create it
        if not os.path.exists(settings.IMG_DIR):
            os.makedirs(settings.IMG_DIR)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        local_filename = f"{stream_id}_{timestamp}_{unique_id}.jpg"
        if ai_model_code and ai_model_code != "":
            local_filename = f"{stream_id}_{timestamp}_{unique_id}_{ai_model_code}.jpg"
        local_path = os.path.join(settings.IMG_DIR, local_filename)

        # ── ① 접속 (P-192) — 안 열리면 ffmpeg 를 **띄우지 않는다** ──────────
        #
        # ★ 여기서 끝나는 줄에는 ffmpeg 프로세스가 **하나도 없다.** 종전에는 닿지
        #   않는 주소마다 ffmpeg 하나가 21초씩 붙어 있었다 [실측 2026-09-19].
        unreachable = _probe_tcp(rtsp_url, CAPTURE_CONNECT_TIMEOUT_SEC)
        if unreachable:
            logger.error(f"[capture_frame] 카메라에 닿지 않습니다 ({stream_id}): {unreachable}")
            return None

        logger.info(f"[capture_frame] Running FFmpeg capture for {stream_id}")

        # ── ② 읽기 (P-192) — `-timeout` 은 **마이크로초**다 ─────────────────
        #
        # ⚠ 이 판(ffmpeg 7.1.3)에 `-stimeout` 은 **없다**. 위 머리말의 실측 참조.
        # ⚠ 입력 옵션이므로 반드시 `-i` **앞**에 온다 — 뒤에 두면 출력 옵션으로
        #   읽혀 조용히 아무 효과가 없다(그러면 「넣었다」고 적고 안 넣은 것이 된다).
        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-timeout", str(CAPTURE_READ_TIMEOUT_SEC * 1_000_000),
            "-i", rtsp_url,
            "-vframes", "1",
            "-q:v", "2",
            local_path
        ]
        # if ai_model_code and ai_model_code != "":
        #    cmd = [
        #     "ffmpeg", "-y",
        #     "-i", rtsp_url,
        #     "-vframes", "1",
        #     "-q:v", "2",
        #     local_path
        # ]
        # ── ③ 벽 (P-192) — ffmpeg 가 ①②를 무시해도 **우리가 끝낸다** ───────
        returncode, stderr = _run_ffmpeg(cmd, CAPTURE_PROCESS_TIMEOUT_SEC)
        if returncode != 0:
            logger.error(f"[capture_frame] FFmpeg failed for {stream_id}:\n{stderr}")
            try:
                os.remove(local_path)
            except FileNotFoundError:
                pass
            return None

        logger.info(f"[capture_frame] FFmpeg capture successful for {stream_id}, saving to MinIO")

        try:
            with open(local_path, "rb") as f:
                image_bytes = f.read()
            os.remove(local_path)
            object_path = minio_client.save_image(image_bytes, stream_id, group_code)
            logger.info(f"[capture_frame] Image saved successfully for {stream_id}: {object_path}")
            return object_path
        except Exception as e:
            logger.error(f"[capture_frame] Failed to save image to MinIO for {stream_id}: {e}")
            return None
