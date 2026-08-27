from core.base import get_current_request
from stream_monitors.models import StreamMonitor
from media_data.schemas.schemas_djantic_in import MediaDetectInSchema
from config import settings
from stream_monitors.utils.minio_client import minio_client
from surveillance.models import VideoAnalysis
from django.utils import timezone
from django.db import transaction, connection
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import requests
from common.external_http import default_timeout, long_timeout
import urllib3
import uuid
import logging
import socket
import cv2
import threading
import hashlib
from urllib.parse import urlparse

# Suppress InsecureRequestWarning for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


def send_media_detect_notification(group_code: str, msg: str, object_paths: list):
    """
    Send WebSocket notification after media detection completes.

    Args:
        group_code: Group code to notify (room: media_detect_{group_code})
        msg: Notification message
        object_paths: List of object paths that were processed
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("Channel layer not configured - notifications disabled")
            return

        if not group_code:
            logger.warning("Missing group_code - skipping media detect notification")
            return

        event = {
            'type': 'media_detect_notification',
            'msg': msg,
            'data': object_paths,
            'timestamp': timezone.now().isoformat(),
        }

        # Send to group room
        async_to_sync(channel_layer.group_send)(f'media_detect_{group_code}', event)
        logger.info(f"Sent media detect notification to group {group_code}")
        print(f"Sent media detect notification to group {group_code}: {msg}")

    except Exception as e:
        logger.error(f"Error sending media detect notification: {e}")
        print(f"Error sending media detect notification: {e}")


def get_server_ipv4_address():
    """
    Get the server's IPv4 address.
    Returns the IP address that can be used by external services to connect back.
    """
    try:
        # Create a socket to determine the outbound IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to an external address (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        logger.warning(f"Could not determine server IP address: {e}, falling back to localhost")
        return "127.0.0.1"


class _UpstreamShapeMismatch:
    """상류(AI 검출 서비스) 응답이 계약 모양이 아니었다 — **빈 목록과 다른 것** (D-284).

    `None` 이나 `[]` 를 쓰지 않는 이유: 그 둘은 "검출이 0건이었다"와 글자가 같다.
    같은 값으로 두 사실을 나르면 부르는 쪽이 구별할 수 없고, 구별하지 못하면
    상류 오류가 **200 성공**으로 나간다. 그것이 이 센티넬이 막는 것이다.
    """

    def __repr__(self) -> str:  # 로그에 이 이름이 그대로 보이게 한다
        return "<상류 응답 모양 불일치 — 검출 0건이 아니다>"


#: 단 하나의 인스턴스. `is` 로 비교한다 — 값이 아니라 **사실**을 나르는 표식이다.
_UPSTREAM_SHAPE_MISMATCH = _UpstreamShapeMismatch()


class MediaDataDetectService:
    """
    Service for detecting media files.
    """

    @staticmethod
    def detect_media(data: MediaDetectInSchema):
        """
        Detect media files.
        """
        detect_urls = f"{settings.AI_GRPC_URL}/detect_media"
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        # Convert schema objects to dicts for JSON serialization
        media_items_dict = [item.dict() for item in data.media_items] if data.media_items else []

        # calculator totals frames from media type 'video' in media_items_dict by cv2.VideoCapture
        total_frames = 0
        for item in media_items_dict:
            # Generate json_filename for each media item
            unique_id = str(uuid.uuid4())[:8]
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            item['json_filename'] = f"detection_{timestamp}_{unique_id}"

            if item['object_path'].startswith("/"):
                item['object_path'] = item['object_path'][1:]

            if item['media_type'] == 'video':
                video_path = f"https://{settings.MINIO_ENDPOINT}/{item['object_path']}"
                video_capture = cv2.VideoCapture(video_path)
                frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                total_frames += frames
                video_capture.release()
            item['object_path'] = f"https://{settings.MINIO_ENDPOINT}/{item['object_path']}"

        # Build callback URL - replace localhost with actual IPv4 for external service access
        # backend_url = settings.BACKEND_URL
        # if "localhost" in backend_url or "127.0.0.1" in backend_url:
        #     server_ip = get_server_ipv4_address()
        #     backend_url = backend_url.replace("localhost", server_ip).replace("127.0.0.1", server_ip)
        # backend_url = "http://192.168.0.31:8000"
        # callback_url = f"{backend_url}/api/media-data/detect-callback"

        # Provide callback_url so ai-streaming-service can notify completion (final analysis_path)
        callback_url = None
        try:
            backend_url = getattr(settings, "BACKEND_URL", None)
            if backend_url:
                callback_url = f"{backend_url.rstrip('/')}/api/media-data/detect-callback"
        except Exception:
            callback_url = None

        body_data = {
            'media_items': media_items_dict,
            'detection_type': data.detection_type,
            'bucket_name': settings.MINIO_STORAGE_MEDIA_BUCKET_NAME,
            'callback_url': f"{settings.BACKEND_URL}/api/media-data/upload-detection"
        }
        # Schedule a one-time notification after total_frames/20 seconds
        # Create VideoAnalysis records for each media item
        if total_frames < 100:
            total_frames = 100
        # if total_frames > 0:
        delay_seconds = total_frames / 20
        # Copy media_items_dict for use in closure
        items_for_record = list(media_items_dict)
        print(f"Analysis will be created in the next {delay_seconds} seconds")
        # Copy username + group_code for use in closure
        user = get_current_request().user
        username = user.username if user else None
        notify_group_code = None
        try:
            if user and hasattr(user, "userprofilelink") and user.userprofilelink and user.userprofilelink.group:
                notify_group_code = user.userprofilelink.group.code
        except Exception:
            notify_group_code = None

        def create_video_analysis_records():
            # Close any existing connection to get a fresh one for this thread
            connection.close()
            created_object_paths = []
            try:
                logger.info(f"Media detection notification: Processing completed for {len(items_for_record)} media items with {total_frames} total frames")
                print(f"Creating VideoAnalysis records for {len(items_for_record)} items...")
                for item in items_for_record:
                    try:
                        json_filename = item.get('json_filename')
                        object_path = item.get('object_path')
                        analysis_path = f"https://{settings.MINIO_ENDPOINT}/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/media_detections/{json_filename}.json"

                        # Build a stable source_key from the object path (strip domain/query, keep bucket/key)
                        raw = str(object_path or "")
                        try:
                            if raw.startswith("http://") or raw.startswith("https://"):
                                parsed = urlparse(raw)
                                raw = parsed.path.lstrip("/")
                        except Exception:
                            pass

                        stream_monitor = None
                        try:
                            stream_code = object_path.split('/')[-2]
                            stream_monitor = StreamMonitor.objects.get(code=stream_code)
                            print("stream_monitor",stream_monitor)
                        except Exception as e:
                            logger.error(f"Error getting stream monitor: {e}")
                            print(f"Error getting stream monitor: {e}")
                        VideoAnalysis.objects.create(
                            video_path=object_path,
                            analysis_path=analysis_path,
                            created_at=timezone.now(),
                            updated_at=timezone.now(),
                            stream_monitor=stream_monitor,
                            created_by=user if user else None,
                            modified_by=user if user else None,
                            group=user.userprofilelink.group if user and user.userprofilelink and user.userprofilelink.group else None,
                        )
                        created_object_paths.append(object_path)
                        logger.info(f"Created VideoAnalysis record for: {object_path}")
                        print(f"Created VideoAnalysis record for: {object_path}")
                    except Exception as e:
                        logger.error(f"Error creating VideoAnalysis record: {e}")
                        print(f"Error creating VideoAnalysis record: {e}")

                # Send WebSocket notification after creating all records
                if notify_group_code and created_object_paths:
                    send_media_detect_notification(
                        group_code=notify_group_code,
                        msg="Detect , you need to wait 2-3 munites to make sure detection is uploaded to storage",
                        object_paths=created_object_paths
                    )
            finally:
                # Close connection when done to clean up
                connection.close()

        timer = threading.Timer(delay_seconds, create_video_analysis_records)
        timer.start()

        # elif total_frames == 0, call detect_media_api directly
        response = requests.post(
            detect_urls, headers=headers, json=body_data, verify=False,
            timeout=long_timeout(),  # 프레임 검출은 본래 오래 걸린다. 그래도 무한은 아니다.
        )
        response_data = response.json()
        print("response_data: ", response_data)
        if not isinstance(response_data, dict) or 'results' not in response_data:
            # ★ "검출 0건"과 "응답 모양이 다르다"를 가른다 (D-284).
            #   전에는 `.get('results', [])` 가 둘을 같은 빈 목록으로 만들었고,
            #   그래서 상류가 오류를 돌려줘도 이 API 는 200 "성공"을 냈다.
            logger.error(
                "검출 상류 응답에 'results' 가 없습니다 — 키: %s. "
                "빈 목록으로 바꾸지 않고 모양 불일치로 올립니다 (D-284)",
                list(response_data)[:10] if isinstance(response_data, dict) else type(response_data).__name__,
            )
            return _UPSTREAM_SHAPE_MISMATCH
        return response_data['results']

    @staticmethod
    @transaction.atomic
    def detect_and_save(data: MediaDetectInSchema):
        """검출을 요청하고 그 결과를 돌려준다. **저장은 이 함수가 하지 않는다.**

        ★ 이 독스트링은 원래 거짓이었다 (D-284 (2))
        ------------------------------------------
        전에는 이렇게 적혀 있었다 — *"Detect media files and save results to
        VideoAnalysis. For each result: Save detections as JSON file to MinIO;
        Create VideoAnalysis record with video_path and analysis_path."*

        그런데 본문에는 `created_records = []` 한 줄뿐이었고 그 변수는 **쓰이지 않은 채**
        `return True, results` 로 끝났다. 부르는 쪽은 저장된 줄 알았다.

            D-284 원칙: **구현이 없는 함수는 성공을 반환하지 않는다.**
                        조용한 성공이 가장 나쁘다 — 부르는 쪽이 "저장됐다"고 믿고 다음을 쌓는다.

        ★ 다만 실측 결과, **저장은 실제로 일어난다 — 다른 곳에서**
        ---------------------------------------------------------
        `NotImplementedError` 를 던지지 않은 이유가 이것이다. 되짚어 보니:

          · `VideoAnalysis` 행은 `detect_media` 안의 `create_video_analysis_records()` 가
            만든다. `threading.Timer(total_frames / 20)` 로 **배경 스레드에서** 돈다.
          · MinIO 의 JSON 은 우리가 쓰지 않는다. AI 서비스가 쓰고
            `callback_url`(`/api/media-data/upload-detection`) 로 알려 준다.

        즉 "본문이 비어 있다"는 맞지만 "저장이 안 된다"는 **틀리다.** 없는 구현을 있다고
        적는 것만큼이나, 있는 구현을 없다고 적는 것도 다음 사람을 헤매게 한다.
        그래서 여기서는 **함수가 하는 일을 정확히 적는 쪽**을 골랐다.

        ★ 아직 정직하지 않은 것 — 남겨서 티켓으로 올린다
        ------------------------------------------------
        `create_video_analysis_records` 를 예약하는 `Timer.start()` 는 AI 서버로 보내는
        `requests.post` **보다 앞줄에 있다.** 그래서 **검출 요청이 실패해도 VideoAnalysis
        행은 만들어진다** — `analysis_path` 는 아직 있지도 않은 JSON 을 가리킨다.
        이것이야말로 D-284 가 이름 붙인 "조용한 성공"이다.

        고치지 않은 이유: 살아 있는 경로의 **동작 변경**이고 (배경 저장을 검출 성공에
        묶으면 지금 성공하던 요청이 실패로 바뀔 수 있다), 그 판단은 판정 사안이다.
        `decisions_pending` 의 **P-W2-2-2** 로 올렸다 (D-213 — STOP 대신 적재하고 전진).

        Returns:
            `(ok, results)` — `ok` 는 **상류 응답이 계약 모양이었는가**다.
            전에는 무조건 `True` 라 뷰의 400 갈래가 **닿을 수 없는 죽은 코드**였다.
        """
        # 상류가 `results` 키를 주지 않으면 그것은 "검출 0건"이 아니라 **모양이 다른 응답**이다.
        # 전에는 `.get('results', [])` 가 그 둘을 같은 빈 목록으로 만들어 200 을 냈다.
        results = MediaDataDetectService.detect_media(data)
        if results is _UPSTREAM_SHAPE_MISMATCH:
            return False, []
        return True, results
