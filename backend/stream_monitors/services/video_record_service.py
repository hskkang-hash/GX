"""
Video Recording Service with segment-based recording.

Supports: start, stop, pause, resume operations.
- Each recording session has its own folder
- Pause stops current segment, resume creates new segment
- Stop merges all segments and uploads to MinIO
- Session data is persisted in Redis to survive restarts and share across workers
"""
import asyncio
import time
import os
import io
import json
import shutil
import requests
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from stream_monitors.utils.minio_client import minio_client
import logging

logger = logging.getLogger(__name__)

# Auto-stop timeout in seconds (10 minutes)
AUTO_STOP_TIMEOUT_SECONDS = 10 * 60

# Redis cache key prefix for recording sessions
RECORDING_SESSION_CACHE_PREFIX = "video_record_session:"
RECORDING_SESSION_CACHE_TIMEOUT = 60 * 60  # 1 hour


class RecordStatus(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPING = "stopping"
    MERGING = "merging"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class RecordingSession:
    """Represents an active recording session."""
    record_id: str  # Database record ID - used as unique identifier
    stream_id: str
    record_code: str
    rtsp_url: str
    record_dir: str
    segment_list_path: str
    status: RecordStatus = RecordStatus.IDLE
    current_segment_path: Optional[str] = None
    ffmpeg_process: Optional[asyncio.subprocess.Process] = None
    segment_count: int = 0
    started_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    auto_stop_enabled: bool = True  # Whether auto-stop is enabled
    auto_stop_task: Optional[asyncio.Task] = None  # Task for auto-stop after timeout
    
    def to_cache_dict(self) -> dict:
        """Convert session to a dict for caching (excludes non-serializable fields)."""
        return {
            "record_id": self.record_id,
            "stream_id": self.stream_id,
            "record_code": self.record_code,
            "rtsp_url": self.rtsp_url,
            "record_dir": self.record_dir,
            "segment_list_path": self.segment_list_path,
            "status": self.status.value,
            "current_segment_path": self.current_segment_path,
            "segment_count": self.segment_count,
            "started_at": self.started_at,
            "error": self.error,
            "auto_stop_enabled": self.auto_stop_enabled,
        }
    
    @classmethod
    def from_cache_dict(cls, data: dict) -> "RecordingSession":
        """Reconstruct session from cached dict."""
        return cls(
            record_id=data["record_id"],
            stream_id=data["stream_id"],
            record_code=data["record_code"],
            rtsp_url=data["rtsp_url"],
            record_dir=data["record_dir"],
            segment_list_path=data["segment_list_path"],
            status=RecordStatus(data["status"]),
            current_segment_path=data.get("current_segment_path"),
            segment_count=data.get("segment_count", 0),
            started_at=data.get("started_at", time.time()),
            error=data.get("error"),
            auto_stop_enabled=data.get("auto_stop_enabled", True),
            # ffmpeg_process and auto_stop_task are not cached
            ffmpeg_process=None,
            auto_stop_task=None,
        )


class VideoRecordService:
    """
    Service for video recording with segment support.
    
    Features:
    - Start: Begin recording to a new session folder
    - Pause: Stop current segment (ffmpeg process)
    - Resume: Start new segment in same folder
    - Stop: Merge all segments and upload to MinIO
    - Session data persisted in Redis for cross-worker/restart support
    """
    
    def __init__(self):
        self._sessions: Dict[str, RecordingSession] = {}  # In-memory cache, keyed by record_id
        self._background_tasks: set = set()  # Keep references to prevent garbage collection
    
    def _get_cache_key(self, record_id: str) -> str:
        """Get Redis cache key for a session."""
        return f"{RECORDING_SESSION_CACHE_PREFIX}{record_id}"
    
    def _save_session_to_cache(self, session: RecordingSession):
        """Save session to Redis cache."""
        try:
            cache_key = self._get_cache_key(session.record_id)
            cache.set(cache_key, json.dumps(session.to_cache_dict()), RECORDING_SESSION_CACHE_TIMEOUT)
            logger.debug(f"Session saved to cache: {session.record_id}")
        except Exception as e:
            logger.warning(f"Failed to save session to cache: {e}")
    
    def _get_session_from_cache(self, record_id: str) -> Optional[RecordingSession]:
        """Get session from Redis cache."""
        try:
            cache_key = self._get_cache_key(record_id)
            cached_data = cache.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                session = RecordingSession.from_cache_dict(data)
                logger.debug(f"Session restored from cache: {record_id}")
                return session
        except Exception as e:
            logger.warning(f"Failed to get session from cache: {e}")
        return None
    
    def _remove_session_from_cache(self, record_id: str):
        """Remove session from Redis cache."""
        try:
            cache_key = self._get_cache_key(record_id)
            cache.delete(cache_key)
            logger.debug(f"Session removed from cache: {record_id}")
        except Exception as e:
            logger.warning(f"Failed to remove session from cache: {e}")
    
    def _get_session(self, record_id: str) -> Optional[RecordingSession]:
        """Get recording session by record_id (from memory or cache)."""
        # First check in-memory sessions
        session = self._sessions.get(record_id)
        if session:
            return session
        
        # Try to restore from Redis cache
        session = self._get_session_from_cache(record_id)
        if session:
            # Re-add to in-memory sessions
            self._sessions[record_id] = session
            return session
        
        return None
    
    def _get_session_by_stream_id(self, stream_id: str) -> Optional[RecordingSession]:
        """Get recording session for a stream (finds first active session for the stream)."""
        for session in self._sessions.values():
            if session.stream_id == stream_id:
                return session
        return None
    
    def _create_session(self, record_id: str, stream_id: str, record_code: str, rtsp_url: str) -> RecordingSession:
        """Create a new recording session."""
        record_dir = os.path.join(settings.RECORD_DIR, record_code)
        os.makedirs(record_dir, exist_ok=True)
        
        session = RecordingSession(
            record_id=record_id,
            stream_id=stream_id,
            record_code=record_code,
            rtsp_url=rtsp_url,
            record_dir=record_dir,
            segment_list_path=os.path.join(record_dir, f"{record_id}_segments.txt"),
        )
        self._sessions[record_id] = session
        # Save to Redis cache for cross-worker/restart support
        self._save_session_to_cache(session)
        return session
    
    def _remove_session(self, record_id: str):
        """Remove recording session by record_id (from memory and cache)."""
        if record_id in self._sessions:
            del self._sessions[record_id]
        # Also remove from Redis cache
        self._remove_session_from_cache(record_id)
    
    async def _call_stop_detect_api(self, record_id: str):
        """Call the stop_detect API to stop AI detection."""
        try:
            detection_url = f"{settings.AI_GRPC_URL}/stop_detect"
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
            body_data = {
                'detection_id': str(record_id)
            }
            
            # Run blocking request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    detection_url,
                    json=body_data,
                    headers=headers,
                    timeout=120,
                    verify=False
                )
            )
            logger.info(f"✅ Stop detect API called successfully for record_id: {record_id}, status: {response.status_code}")
            return response
        except Exception as e:
            logger.warning(f"Stop detect API call failed for record_id {record_id}: {e}")
            return None
    
    def _schedule_auto_stop(self, session: RecordingSession):
        """Schedule auto-stop task for the session."""
        if not session.auto_stop_enabled:
            logger.debug(f"Auto-stop disabled for record_id {session.record_id}")
            return
        
        async def _auto_stop_after_timeout():
            try:
                logger.info(f"⏰ Auto-stop scheduled for record_id {session.record_id}, will stop in {AUTO_STOP_TIMEOUT_SECONDS}s")
                await asyncio.sleep(AUTO_STOP_TIMEOUT_SECONDS)
                # Check if session still exists and is still recording/paused
                existing_session = self._get_session(session.record_id)
                if existing_session and existing_session.status in (RecordStatus.RECORDING, RecordStatus.PAUSED):
                    logger.info(f"⏰ Auto-stopping recording for stream {session.stream_id}, record_id: {session.record_id} after {AUTO_STOP_TIMEOUT_SECONDS}s timeout")
                    
                    # Call stop_detect API
                    await self._call_stop_detect_api(session.record_id)
                    
                    # Stop the recording
                    await self.stop(session.record_id)
                else:
                    logger.debug(f"Auto-stop skipped for record_id {session.record_id}: session not found or already stopped")
            except asyncio.CancelledError:
                logger.debug(f"Auto-stop task cancelled for record_id {session.record_id}")
            except Exception as e:
                logger.error(f"Error in auto-stop task for record_id {session.record_id}: {e}")
            finally:
                # Remove task from background tasks set
                if session.auto_stop_task in self._background_tasks:
                    self._background_tasks.discard(session.auto_stop_task)
        
        task = asyncio.create_task(_auto_stop_after_timeout())
        session.auto_stop_task = task
        # Add to background tasks set to prevent garbage collection
        self._background_tasks.add(task)
    
    def _cancel_auto_stop(self, session: RecordingSession):
        """Cancel auto-stop task for the session."""
        if session.auto_stop_task:
            if not session.auto_stop_task.done():
                session.auto_stop_task.cancel()
            # Remove from background tasks set
            self._background_tasks.discard(session.auto_stop_task)
            session.auto_stop_task = None
    
    async def start(
        self, 
        record_id: str,
        stream_id: str, 
        rtsp_url: Optional[str] = None,
        ai_model_code: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Start a new recording session.
        
        Args:
            record_id: Database record ID (used as unique identifier)
            stream_id: Stream monitor ID/code
            rtsp_url: Optional custom RTSP URL (for external streams)
            ai_model_code: Optional AI model code (records from AI stream)
            
        Returns:
            Tuple[bool, str, Optional[str]]: (success, message, record_code)
        """
        try:
            # Check if already recording with this record_id
            existing_session = self._get_session(record_id)
            if existing_session:
                return False, f"Recording already exists for record_id {record_id}", existing_session.record_code
            
            # Generate record code
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            record_code = f"{timestamp}{stream_id}"
            if ai_model_code:
                record_code = f"{timestamp}{stream_id}_{ai_model_code}"
            
            # Determine RTSP URL
            if rtsp_url:
                final_rtsp_url = rtsp_url
            elif ai_model_code:
                final_rtsp_url = f"{settings.RTSP_URL}/stream/ai_{stream_id}"
            else:
                final_rtsp_url = f"{settings.RTSP_URL}/stream/{stream_id}"
            
            # Create session with record_id
            session = self._create_session(record_id, stream_id, record_code, final_rtsp_url)
            
            # Start first segment
            success = await self._start_segment(session)
            if not success:
                self._remove_session(record_id)
                return False, "Failed to start recording segment", None
            
            session.status = RecordStatus.RECORDING
            # Update cache with new status
            self._save_session_to_cache(session)
            
            # Schedule auto-stop after timeout
            self._schedule_auto_stop(session)
            
            logger.info(f"✅ Started recording for stream {stream_id}, record_id: {record_id}, record_code: {record_code} (auto-stop in {AUTO_STOP_TIMEOUT_SECONDS}s)")
            
            return True, "Recording started successfully", record_code
            
        except Exception as e:
            logger.error(f"❌ Error starting recording for stream {stream_id}: {e}")
            self._remove_session(record_id)
            return False, f"Error starting recording: {str(e)}", None
    
    async def pause(self, record_id: str) -> Tuple[bool, str]:
        """
        Pause recording (stop current segment).
        
        Args:
            record_id: Database record ID
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            session = self._get_session(record_id)
            
            if not session:
                return False, "No active recording session found"
            
            if session.status != RecordStatus.RECORDING:
                return False, f"Cannot pause: current status is {session.status.value}"
            
            # Stop current segment
            await self._stop_segment(session)
            session.status = RecordStatus.PAUSED
            # Update cache with new status
            self._save_session_to_cache(session)
            
            logger.info(f"⏸️ Paused recording for record_id: {record_id}")
            return True, "Recording paused successfully"
            
        except Exception as e:
            logger.error(f"❌ Error pausing recording for record_id {record_id}: {e}")
            return False, f"Error pausing recording: {str(e)}"
    
    async def resume(self, record_id: str) -> Tuple[bool, str]:
        """
        Resume recording (start new segment).
        
        Args:
            record_id: Database record ID
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            session = self._get_session(record_id)
            
            if not session:
                return False, "No active recording session found"
            
            if session.status != RecordStatus.PAUSED:
                return False, f"Cannot resume: current status is {session.status.value}"
            
            # Start new segment
            success = await self._start_segment(session)
            if not success:
                return False, "Failed to start new recording segment"
            
            session.status = RecordStatus.RECORDING
            # Update cache with new status
            self._save_session_to_cache(session)
            
            logger.info(f"▶️ Resumed recording for record_id: {record_id}")
            return True, "Recording resumed successfully"
            
        except Exception as e:
            logger.error(f"❌ Error resuming recording for record_id {record_id}: {e}")
            return False, f"Error resuming recording: {str(e)}"
    
    async def stop(self, record_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Stop recording, merge all segments and upload to MinIO.
        
        Args:
            record_id: Database record ID
            
        Returns:
            Tuple[bool, str, Optional[str]]: (success, message, minio_object_path)
        """
        try:
            session = self._get_session(record_id)
            
            if not session:
                logger.warning(f"No active recording session found for record_id: {record_id}")
                return False, "No active recording session found", None
            
            # Log if session was restored from cache (no ffmpeg_process)
            if session.ffmpeg_process is None and session.status == RecordStatus.RECORDING:
                logger.info(f"📦 Session {record_id} restored from cache (ffmpeg process not available)")
            
            # Cancel auto-stop task if exists
            self._cancel_auto_stop(session)
            
            # If recording and we have an ffmpeg process, stop it
            if session.status == RecordStatus.RECORDING and session.ffmpeg_process:
                await self._stop_segment(session)
            
            session.status = RecordStatus.STOPPING
            
            # Check if we have any segments
            if not os.path.exists(session.segment_list_path):
                logger.warning(f"No segments found for record_id: {record_id}")
                self._cleanup_session(session)
                return False, "No video segments recorded", None
            
            # Merge segments
            session.status = RecordStatus.MERGING
            merged_path = await self._merge_segments(session)
            
            if not merged_path:
                self._cleanup_session(session)
                return False, "Failed to merge video segments", None
            
            # Upload to MinIO
            session.status = RecordStatus.UPLOADING
            object_path = await self._upload_to_minio(session, merged_path)
            
            # Cleanup
            self._cleanup_session(session)
            
            if object_path:
                logger.info(f"✅ Recording completed for record_id: {record_id}, saved to {object_path}")
                return True, "Recording stopped and saved successfully", object_path
            else:
                return False, "Failed to upload video to storage", None
            
        except Exception as e:
            logger.error(f"❌ Error stopping recording for record_id {record_id}: {e}")
            session = self._get_session(record_id)
            if session:
                self._cleanup_session(session)
            return False, f"Error stopping recording: {str(e)}", None
    
    def get_status(self, record_id: str) -> Dict[str, Any]:
        """
        Get recording status.
        
        Args:
            record_id: Database record ID
            
        Returns:
            Dict with status information
        """
        session = self._get_session(record_id)
        
        if not session:
            return {
                "record_id": record_id,
                "is_recording": False,
                "status": "idle",
                "record_code": None
            }
        
        return {
            "record_id": record_id,
            "stream_id": session.stream_id,
            "is_recording": session.status == RecordStatus.RECORDING,
            "status": session.status.value,
            "record_code": session.record_code,
            "segment_count": session.segment_count,
            "started_at": session.started_at,
            "error": session.error
        }
    
    async def _start_segment(self, session: RecordingSession) -> bool:
        """Start a new video segment from RTSP."""
        try:
            session.segment_count += 1
            segment_path = os.path.join(
                session.record_dir,
                f"{session.record_id}_segment_{session.segment_count}_{int(time.time())}.mp4",
            )
            session.current_segment_path = segment_path

            # Register segment for concat
            with open(session.segment_list_path, "a") as f:
                f.write(f"file '{os.path.abspath(segment_path)}'\n")

            cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", session.rtsp_url,
                "-c:v", "copy",
                "-an",
                "-f", "mp4",
                "-movflags", "+faststart+frag_keyframe+empty_moov",
                "-frag_duration", "1000000",
                "-reset_timestamps", "1",
                "-y",
                str(segment_path),
            ]

            logger.debug("Starting FFmpeg segment: %s", " ".join(cmd))

            session.ffmpeg_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait briefly and validate process health
            try:
                await asyncio.wait_for(session.ffmpeg_process.wait(), timeout=1.0)
                stderr = await session.ffmpeg_process.stderr.read()
                logger.error(
                    "FFmpeg exited immediately (%s): %s",
                    session.ffmpeg_process.returncode,
                    stderr.decode(errors="ignore"),
                )
                return False
            except asyncio.TimeoutError:
                pass  # Process is running → good

            logger.info(
                "📹 Started segment %s for record_id %s",
                session.segment_count,
                session.record_id,
            )
            # Update cache with new segment info
            self._save_session_to_cache(session)
            return True

        except Exception as e:
            logger.error(
                "Error starting segment for record_id %s: %s",
                session.record_id,
                e,
            )
            session.error = str(e)
            self._save_session_to_cache(session)
            return False

    
    async def _stop_segment(self, session: RecordingSession):
        """Stop current video segment gracefully with signal escalation."""
        proc = session.ffmpeg_process
        if not proc:
            return

        try:
            if proc.returncode is None:
                # 1️⃣ Best-effort graceful quit via stdin
                if proc.stdin:
                    try:
                        proc.stdin.write(b"q\n")
                        await proc.stdin.drain()
                    except Exception as e:
                        logger.debug(f"Could not send 'q' to ffmpeg stdin: {e}")

                # 2️⃣ Short grace window
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("FFmpeg did not exit on 'q', sending SIGTERM")
                    proc.terminate()

                    # 3️⃣ Second grace window
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning("FFmpeg did not terminate, killing...")
                        proc.kill()
                        await proc.wait()

            logger.info(
                "📹 Stopped segment %s for record_id %s",
                session.segment_count,
                session.record_id,
            )

        except Exception as e:
            logger.warning(f"Error stopping segment: {e}")

        finally:
            session.ffmpeg_process = None

    
    async def _merge_segments(self, session: RecordingSession) -> Optional[str]:
        """Merge all video segments into one file."""
        try:
            merged_path = os.path.join(
                session.record_dir, 
                f"{session.record_id}_{int(time.time())}_final.mp4"
            )
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(session.segment_list_path),
                "-c", "copy",
                str(merged_path)
            ]
            
            logger.info(f"🔄 Merging {session.segment_count} segments for record_id {session.record_id}")
            logger.debug(f"Merge command: {' '.join(cmd)}")
            
            merge_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await merge_proc.communicate()
            
            if merge_proc.returncode != 0:
                logger.error(f"Failed to merge video: {stderr.decode()}")
                return None
            
            # Verify merged file exists and has content
            if not os.path.exists(merged_path) or os.path.getsize(merged_path) == 0:
                logger.error("Merged file is empty or doesn't exist")
                return None
            
            logger.info(f"✅ Merged video saved to {merged_path}")
            return merged_path
            
        except Exception as e:
            logger.error(f"Error merging segments: {e}")
            return None
    
    async def _upload_to_minio(self, session: RecordingSession, video_path: str) -> Optional[str]:
        """Upload merged video to MinIO."""
        try:
            logger.info(f"📤 Uploading video to MinIO for record_id {session.record_id}")
            
            loop = asyncio.get_event_loop()
            
            def read_and_upload():
                with open(video_path, 'rb') as f:
                    video_data = io.BytesIO(f.read())
                return minio_client.save_video(video_data, session.stream_id, session.record_code)
            
            # Retry upload up to 3 times
            object_path = None
            for attempt in range(1, 4):
                try:
                    object_path = await loop.run_in_executor(None, read_and_upload)
                    if object_path:
                        logger.info(f"✅ Upload successful on attempt {attempt}")
                        break
                except Exception as e:
                    logger.warning(f"Upload attempt {attempt} failed: {e}")
                
                if attempt < 3:
                    await asyncio.sleep(1.0)
            
            return object_path
            
        except Exception as e:
            logger.error(f"Error uploading to MinIO: {e}")
            return None
    
    def _cleanup_session(self, session: RecordingSession):
        """Clean up session resources."""
        try:
            # Cancel auto-stop task if still running
            self._cancel_auto_stop(session)
            
            # Remove from active sessions
            self._remove_session(session.record_id)
            
            # Remove temporary directory
            if os.path.exists(session.record_dir):
                try:
                    shutil.rmtree(session.record_dir)
                    logger.info(f"🧹 Cleaned up record directory {session.record_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove record directory: {e}")
                    
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


# Singleton instance
video_record_service = VideoRecordService()
