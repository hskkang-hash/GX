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
        response = requests.post(detect_urls, headers=headers, json=body_data, verify=False)
        response_data = response.json()
        print("response_data: ", response_data)
        results = response_data.get('results', [])
        return results

    @staticmethod
    @transaction.atomic
    def detect_and_save(data: MediaDetectInSchema):
        """
        Detect media files and save results to VideoAnalysis.
        For each result:
        - Save detections as JSON file to MinIO
        - Create VideoAnalysis record with video_path and analysis_path
        """
        # Call detect_media to get results
        results = MediaDataDetectService.detect_media(data)
        
        created_records = []
        
        return True, results