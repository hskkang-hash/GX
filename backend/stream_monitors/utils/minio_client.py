import time
from core.file_management.models import UserMediaFile
from minio import Minio
from minio.error import S3Error
from datetime import datetime
import os
import io
from django.conf import settings
from core.middleware.refresh_token import get_current_request
import logging

logger = logging.getLogger(__name__)


class MinioClient:
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket_name = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
        self.available = False
        self.client = None

        try:
            # C-3.3 — 저장소도 외부 의존이다. 타임아웃 없이 부르지 않는다.
            #
            # 실측(2026-08-27): endpoint 가 닿지 않을 때 이 클라이언트가
            # **매 호출마다 5회 재시도**를 돌았다(백필 실행 로그). 타임아웃도 재시도 상한도
            # 없어서, 저장소 하나가 안 뜨면 그 뒤의 모든 작업이 그만큼 매달린다 —
            # "부분 실패가 전면 정지가 되는" 바로 그 경로다.
            #
            # MinIO SDK 는 호출마다 timeout= 을 받지 않는다. **여기서 한 번** 정한다.
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=False,  # Set to True for HTTPS
                http_client=self._http_client(),
            )
            self._ensure_bucket_exists()
            self.available = True
        except Exception as e:
            logger.error(f"Failed to initialize Minio client: {e}")
            logger.warning("Storage functionality will be disabled. Images and videos will not be saved.")

    @staticmethod
    def _http_client():
        """타임아웃·재시도 상한이 걸린 연결 풀. **값은 설정에서 온다** (C-3.4 · C-3.5).

        기본값은 보수적으로 잡았다 — 저장소가 죽었을 때 **빨리 실패하고 나머지를 서빙**하는
        것이 목적이지, 요청을 끝까지 성공시키는 것이 목적이 아니다.
        """
        import urllib3

        connect = getattr(settings, "MINIO_CONNECT_TIMEOUT", 3.0)
        read = getattr(settings, "MINIO_READ_TIMEOUT", 10.0)
        retries = getattr(settings, "MINIO_MAX_RETRIES", 1)
        return urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=connect, read=read),
            retries=urllib3.Retry(total=retries, backoff_factor=0.2,
                                  status_forcelist=[500, 502, 503, 504]),
        )

    def _ensure_bucket_exists(self):
        """Create the bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created successfully")
            else:
                logger.info(f"Bucket '{self.bucket_name}' already exists")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise

    def save_image(self, image_data, stream_id, group_code=None):
        """
        Save an image to Minio storage.

        Args:
            image_data: Image data as bytes or BytesIO
            stream_id: ID of the stream the image was captured from
            group_code: Code of the group to save the image to
        Returns:
            str: Object name (path) of the saved image or None if storage is unavailable
        """
        if not self.available or not self.client:
            logger.warning("Storage is unavailable. Image will not be saved.")
            return None

        try:
            # Safely get group from request context
            request = get_current_request()
            group = None
            if request and hasattr(request, 'user') and request.user:
                if hasattr(request.user, 'userprofilelink') and request.user.userprofilelink:
                    group = request.user.userprofilelink.group

            if group_code:
                group_code = group_code
            else:
                if group:
                    group_code = group.code
                else:
                    group_code = "default"

            username = request.user.username if request and hasattr(request, 'user') and request.user else "public"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            object_name = f"{group_code}/{username}/images/{stream_id}/{timestamp}.jpg"

            # Convert to BytesIO if it's bytes
            if isinstance(image_data, bytes):
                image_data = io.BytesIO(image_data)
                image_data.seek(0)

            # Get the size of the data
            image_data.seek(0, os.SEEK_END)
            size = image_data.tell()
            image_data.seek(0)

            # Upload the image
            self.client.put_object(
                self.bucket_name,
                object_name,
                image_data,
                size,
                content_type="image/jpeg"
            )

            # create user media file
            user_media_file = UserMediaFile()
            user_media_file.file_url = f"/{self.bucket_name}/{object_name}"
            user_media_file.file_size = size
            user_media_file.is_minio = False
            user_media_file.created_by = request.user
            user_media_file.group = request.user.userprofilelink.group
            user_media_file.save()

            logger.info(f"Image saved to {self.bucket_name}/{object_name}")
            return object_name
        except Exception as e:
            logger.error(f"Error saving image to Minio: {e}")
            return None

    def save_video(self, video_data, stream_id, filename=None):
        """Save a video to MinIO with retry and timeout handling."""
        if not self.available or not self.client:
            logger.warning("Storage is unavailable. Video will not be saved.")
            return None

        try:
            if filename:
                object_name = f"videos/{stream_id}/{filename}.mp4"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                object_name = f"videos/{stream_id}/{timestamp}.mp4"

            if isinstance(video_data, bytes):
                video_data = io.BytesIO(video_data)

            # Get the actual size of the stream
            video_data.seek(0, os.SEEK_END)
            size = video_data.tell()
            video_data.seek(0)

            # Validate that the stream has data
            if size == 0:
                logger.warning(f"Video stream is empty. Skipping upload for {object_name}")
                return None

            # Check if stream is readable and has enough data
            # Read a small chunk to verify the stream is accessible
            try:
                current_pos = video_data.tell()
                test_read = video_data.read(1)
                video_data.seek(current_pos)
                if not test_read:
                    logger.warning(f"Video stream is not readable. Skipping upload for {object_name}")
                    return None
            except Exception as e:
                logger.warning(f"Error reading video stream: {e}. Skipping upload for {object_name}")
                return None

            for attempt in range(3):
                try:
                    # Reset stream position before each attempt
                    video_data.seek(0)

                    self.client.put_object(
                        self.bucket_name,
                        object_name,
                        video_data,
                        size,
                        content_type="video/mp4"
                    )
                    logger.info(f"Video saved to {self.bucket_name}/{object_name}")
                    return object_name
                except Exception as e:
                    error_str = str(e).lower()
                    # Check if error is about insufficient data - don't retry in this case
                    if "not enough data" in error_str or "stream having not enough data" in error_str:
                        logger.error(f"Video stream has insufficient data: {e}. Skipping upload for {object_name}")
                        return None

                    # For other errors, retry
                    if attempt < 2:  # Don't log warning on last attempt
                        logger.warning(f"Upload attempt {attempt+1} failed: {e}")
                        time.sleep(2)
                    else:
                        logger.error(f"Upload attempt {attempt+1} failed: {e}")

            logger.error("All upload attempts failed.")
            return None

        except Exception as e:
            logger.error(f"Error saving video to Minio: {e}")
            return None


    def save_json(self, json_data, stream_id, filename=None):
        """
        Save JSON data to Minio storage.

        Args:
            json_data: JSON data as dict, list, or JSON string
            stream_id: ID of the stream
            filename: Optional custom filename to use (without extension). If not provided, uses timestamp.

        Returns:
            str: Object name (path) of the saved JSON file or None if storage is unavailable
        """
        if not self.available or not self.client:
            logger.warning("Storage is unavailable. JSON will not be saved.")
            return None

        try:
            import json as json_lib
            # Convert dict/list to JSON string if needed
            if isinstance(json_data, (dict, list)):
                json_string = json_lib.dumps(json_data, indent=2, ensure_ascii=False)
            else:
                json_string = str(json_data)

            # Convert to BytesIO
            json_bytes = json_string.encode('utf-8')
            json_data_io = io.BytesIO(json_bytes)

            if filename:
                object_name = f"analysis/{stream_id}/{filename}.json"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                object_name = f"analysis/{stream_id}/{timestamp}.json"

            # Get the size of the data
            json_data_io.seek(0, os.SEEK_END)
            size = json_data_io.tell()
            json_data_io.seek(0)

            # Upload the JSON
            self.client.put_object(
                self.bucket_name,
                object_name,
                json_data_io,
                size,
                content_type="application/json"
            )

            logger.info(f"JSON saved to {self.bucket_name}/{object_name}")
            return object_name
        except Exception as e:
            logger.error(f"Error saving JSON to Minio: {e}")
            return None

    def get_json(self, object_path_or_url: str):
        """
        Download and parse JSON file from MinIO storage.

        Args:
            object_path_or_url: Either a full URL (http://endpoint/bucket/path),
                              URL without protocol (endpoint/bucket/path), or object path (path/to/file.json)

        Returns:
            dict or list: Parsed JSON data, or None if error or storage unavailable
        """
        if not self.available or not self.client:
            logger.warning("Storage is unavailable. Cannot retrieve JSON.")
            return None

        try:
            import json as json_lib
            import requests

            # Check if it's a full URL with protocol
            if object_path_or_url.startswith('http://') or object_path_or_url.startswith('https://'):
                # It's a full URL - download directly
                response = requests.get(object_path_or_url, timeout=30)
                if response.status_code != 200:
                    logger.error(f"Failed to download JSON from {object_path_or_url}, status: {response.status_code}")
                    return None
                json_data = json_lib.loads(response.content.decode('utf-8'))
                return json_data
            elif '/' in object_path_or_url and not object_path_or_url.startswith('/'):
                # It might be a URL without protocol (e.g., "endpoint/bucket/path")
                # Try to construct a URL and download
                try:
                    # Remove leading slash if present
                    path_clean = object_path_or_url.lstrip('/')
                    # Construct URL (assuming HTTP, can be made configurable)
                    download_url = f'http://{path_clean}'
                    response = requests.get(download_url, timeout=30)
                    if response.status_code == 200:
                        json_data = json_lib.loads(response.content.decode('utf-8'))
                        return json_data
                except Exception:
                    # If URL download fails, fall through to MinIO client method
                    pass

            # It's just a path - use MinIO client
            # Remove leading slash if present
            object_path = object_path_or_url.lstrip('/')

            # If the path contains bucket name, extract just the object path
            if '/' in object_path:
                parts = object_path.split('/', 1)
                if len(parts) == 2 and parts[0] == self.bucket_name:
                    object_path = parts[1]

            # Get object from MinIO
            response = self.client.get_object(self.bucket_name, object_path)

            # Read and parse JSON
            json_bytes = response.read()
            json_data = json_lib.loads(json_bytes.decode('utf-8'))
            response.close()
            response.release_conn()

            return json_data

        except json_lib.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {object_path_or_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving JSON from Minio: {e}")
            return None

    def get_file_size(self, object_path_or_url: str):
        """
        Get file size from MinIO storage.

        Args:
            object_path_or_url: Either a full URL (http://endpoint/bucket/path),
                              URL without protocol (endpoint/bucket/path), or object path (path/to/file)

        Returns:
            int: File size in bytes, or None if error or storage unavailable
        """
        if not self.available or not self.client:
            logger.warning("Storage is unavailable. Cannot retrieve file size.")
            return None

        try:
            import requests

            # Check if it's a full URL with protocol
            if object_path_or_url.startswith('http://') or object_path_or_url.startswith('https://'):
                # Try to get file size via HEAD request
                try:
                    response = requests.head(object_path_or_url, timeout=10)
                    if response.status_code == 200 and 'Content-Length' in response.headers:
                        return int(response.headers['Content-Length'])
                except Exception:
                    pass
            elif '/' in object_path_or_url and not object_path_or_url.startswith('/'):
                # It might be a URL without protocol (e.g., "endpoint/bucket/path")
                try:
                    path_clean = object_path_or_url.lstrip('/')
                    download_url = f'http://{path_clean}'
                    response = requests.head(download_url, timeout=10)
                    if response.status_code == 200 and 'Content-Length' in response.headers:
                        return int(response.headers['Content-Length'])
                except Exception:
                    pass

            # Extract object path from URL or use as-is
            object_path = object_path_or_url.lstrip('/')

            # If it's a URL, extract the object path part
            if object_path_or_url.startswith('http://') or object_path_or_url.startswith('https://'):
                # URL format: http://endpoint/bucket/path/to/file
                # Remove protocol
                path_without_protocol = object_path_or_url.split('://', 1)[1] if '://' in object_path_or_url else object_path_or_url
                # Split by '/' and skip endpoint, get bucket and path
                parts = path_without_protocol.split('/')
                if len(parts) >= 3:
                    # parts[0] = endpoint, parts[1] = bucket, parts[2:] = object path
                    if parts[1] == self.bucket_name:
                        object_path = '/'.join(parts[2:])
                    else:
                        # Bucket name doesn't match, try to use everything after bucket
                        object_path = '/'.join(parts[2:]) if len(parts) > 2 else '/'.join(parts[1:])
            elif '/' in object_path:
                # Check if it starts with bucket name
                parts = object_path.split('/', 1)
                if len(parts) == 2 and parts[0] == self.bucket_name:
                    object_path = parts[1]

            # Get object stats from MinIO
            stat = self.client.stat_object(self.bucket_name, object_path)
            return stat.size

        except Exception as e:
            logger.error(f"Error retrieving file size from Minio: {e}")
            return None

    def get_metadata(self, object_path_or_url: str) -> dict:
        """
        Get custom metadata of an object in MinIO WITHOUT downloading the file.
        """
        if not self.available or not self.client:
            logger.warning("Storage is unavailable. Cannot retrieve metadata.")
            return {}

        try:
            object_path = object_path_or_url.lstrip('/')

            # Nếu là full URL: https://endpoint/bucket/path
            if object_path_or_url.startswith('http://') or object_path_or_url.startswith('https://'):
                path_without_protocol = object_path_or_url.split('://', 1)[1]
                parts = path_without_protocol.split('/', 2)
                if len(parts) >= 3 and parts[1] == self.bucket_name:
                    object_path = parts[2]

            # Nếu path có bucket ở đầu
            if object_path.startswith(self.bucket_name + '/'):
                object_path = object_path[len(self.bucket_name) + 1:]

            stat = self.client.stat_object(self.bucket_name, object_path)
            return stat.metadata or {}

        except S3Error as e:
            logger.error(f"MinIO error getting metadata: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return {}

# Singleton instance to be used throughout the application
minio_client = MinioClient()
