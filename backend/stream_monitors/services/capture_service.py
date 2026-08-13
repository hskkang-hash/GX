import os
import time
import datetime
import uuid
import subprocess

from stream_monitors.models import StreamMonitor, StreamMonitorAIModel
from stream_monitors.schemas.schemas_djantic_out import CaptureResponse
from django.conf import settings
from stream_monitors.utils.minio_client import minio_client
import logging


logger = logging.getLogger(__name__)


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
        print("rtsp_url: ", rtsp_url)
        logger.info(f"[capture_frame] Starting capture for {stream_id} from RTSP: {rtsp_url}")

        # check if folder ettings.IMG_DIR not exist, create it
        if not os.path.exists(settings.IMG_DIR):
            os.makedirs(settings.IMG_DIR)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        local_filename = f"{stream_id}_{timestamp}_{unique_id}.jpg"
        if ai_model_code and ai_model_code != "":
            local_filename = f"{stream_id}_{timestamp}_{unique_id}_{ai_model_code}.jpg"
        local_path = os.path.join(settings.IMG_DIR, local_filename)

        logger.info(f"[capture_frame] Running FFmpeg capture for {stream_id}")
        
        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
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
        print("cmd: ", cmd)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[capture_frame] FFmpeg failed for {stream_id}:\n{result.stderr}")
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
