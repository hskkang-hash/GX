import asyncio
import time
import os
import io
import shutil

from stream_monitors.models import StreamMonitorAIModel
from stream_monitors.utils.minio_client import minio_client
from stream_monitors.utils.redis_client import redis_client
from django.conf import settings
from asgiref.sync import sync_to_async
import logging


logger = logging.getLogger(__name__)


class RecordingTask:
    def __init__(self, stream_id: str, record_id: str, record_code: str = None, rtsp_url: str = None, use_ai_model: bool = False):
        self.stream_id = stream_id
        self.record_id = record_id
        self.record_code = record_code or record_id  # Use record_code if provided, otherwise fallback to record_id
        self.use_ai_model = use_ai_model
        self.rtsp_url = rtsp_url
        self.record_dir = os.path.join(settings.RECORD_DIR, self.record_code)
        self.segment_list_path = os.path.join(self.record_dir, f"{self.stream_id}_segments.txt")
        self.is_recording = False
        self.local_path = None
        self.ffmpeg_process = None
        self.recording_task = None
        
        # Initialize status in Redis
        self._update_status({
            'stream_id': stream_id,
            'record_id': record_id,
            'record_code': self.record_code,
            'status': 'initialized',
            'created_at': time.time(),
            'is_recording': False,
            'object_path': None,
            'error': None
        })
    
    @classmethod
    async def create(cls, stream_id: str, record_id: str, record_code: str = None, ai_model_name: str = None, record_url: str = None):
        """
        Async factory method to create a RecordingTask instance.
        
        Args:
            stream_id: ID of the stream
            record_id: ID of the record
            record_code: Code for the record (optional, defaults to record_id)
            ai_model_name: AI model code to use (optional)
            
        Returns:
            RecordingTask: Initialized recording task instance
        """
        if record_url:
            use_ai_model = "ai_" in record_url
            rtsp_url = record_url
        else:
            use_ai_model = False
            rtsp_url = f"{settings.RTSP_URL}/stream/{stream_id}"
            
            # Change from HLS URL to RTSP URL
            if ai_model_name and ai_model_name != "":
                use_ai_model = True
                try:
                    # Use sync_to_async for database query
                    # stream_monitor_ai = await sync_to_async(
                    #     lambda: StreamMonitorAIModel.objects.filter(
                    #         stream_monitor__code=stream_id, 
                    #         ai_model__code=ai_model_name
                    #     ).first()
                    # )()
                    
                    if ai_model_name:
                        rtsp_url = f"{settings.RTSP_URL}/stream/ai_{stream_id}"
                    else:
                        rtsp_url = f"{settings.RTSP_URL}/stream/{stream_id}"
                except Exception as e:
                    logger.warning(f"Error fetching AI stream URL: {e}. Using default RTSP URL.")
                    rtsp_url = f"{settings.RTSP_URL}/stream/{stream_id}"
        
        return cls(stream_id, record_id, record_code, rtsp_url, use_ai_model)
        
    def _update_status(self, updates: dict):
        """Update recording status in Redis."""
        redis_client.update_recording_status(self.record_code, updates)
        
    def start_recording(self, is_new_record: bool = True):
        """Start recording video from the stream."""
        if self.is_recording:
            logger.warning(f"Recording already active for stream {self.stream_id}")
            self._update_status({
                'status': 'already_recording',
                'error': 'Recording already active'
            })
            return False
        
        try:
            if is_new_record:
                logger.info(f"Starting recording from stream {self.stream_id}")
                os.makedirs(self.record_dir, exist_ok=True)
                self._update_status({
                    'status': 'starting',
                    'is_recording': True,
                    'started_at': time.time(),
                    'error': None
                })
            else:
                logger.info(f"Resuming recording from stream {self.stream_id}")
                self._update_status({
                    'status': 'resuming',
                    'is_recording': True,
                    'resumed_at': time.time(),
                    'error': None
                })
                
            self.is_recording = True
            self.local_path = os.path.join(self.record_dir, f"{self.stream_id}_{int(time.time())}.mp4")
            with open(self.segment_list_path, 'a') as f:
                abs_path = os.path.abspath(self.local_path)
                f.write(f"file '{abs_path}'\n")
            self.recording_task = asyncio.create_task(self._recording_loop())
            self._update_status({
                'status': 'recording',
                'is_recording': True,
                'local_path': self.local_path
            })
            
            return True
        except Exception as e:
            logger.error(f"Error starting recording for stream {self.stream_id}: {e}")
            self._update_status({
                'status': 'error',
                'is_recording': False,
                'error': str(e)
            })
            return False
        
    async def stop_recording(self, is_pause: bool = False):
        """Stop recording and save the video."""
        if not self.is_recording:
            logger.warning(f"No active recording for stream {self.stream_id}")
            self._update_status({
                'status': 'not_recording',
                'error': 'No active recording'
            })
            return None
            
        logger.info(f"Stopping recording for stream {self.stream_id}")
        self.is_recording = False
        
        self._update_status({
            'status': 'stopping',
            'is_recording': False,
            'stopped_at': time.time()
        })
        
        if self.ffmpeg_process:
            try:
                # Check if process is still running before trying to terminate
                if self.ffmpeg_process.returncode is None:
                    self.ffmpeg_process.terminate()
                    await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                # If terminate doesn't work, try to kill the process
                try:
                    if self.ffmpeg_process.returncode is None:
                        self.ffmpeg_process.kill()
                        await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=2.0)
                except Exception as e:
                    logger.warning(f"Failed to kill ffmpeg process: {e}")
            except Exception as e:
                logger.warning(f"Failed to terminate ffmpeg process: {e}")
        
        try:
            await asyncio.wait_for(self.recording_task, timeout=5.0)
        except asyncio.TimeoutError:
            self.recording_task.cancel()
        
        if not is_pause:
            # Start background task for saving video to MinIO
            asyncio.create_task(self._save_video_async())
            expected_path = f"videos/{self.stream_id}/{self.record_code}.mp4"
            
            self._update_status({
                'status': 'processing',
                'object_path': expected_path,
                'message': 'Video is being processed and saved in the background'
            })
            
            return expected_path  # Return expected path immediately
        
        self._update_status({
            'status': 'paused',
            'is_recording': False
        })
        
        return None
        
    async def _recording_loop(self):
        """
        Main recording loop that writes MP4 directly from RTSP stream.
        """
        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",  # Use TCP for stable connection
            "-i", self.rtsp_url,
            "-c:v", "copy",  # Copy video stream without re-encoding
            "-an",  # No audio
            "-f", "mp4",  # Output as MP4 directly
            "-movflags", "+faststart+frag_keyframe+empty_moov",  # Optimize for streaming
            "-frag_duration", "1000000",  # 1 second fragments
            "-reset_timestamps", "1",  # Reset timestamps for clean output
            str(self.local_path)
        ]
        # if self.use_ai_model:
        #     cmd = [
        #         "ffmpeg",
        #         "-i", self.rtsp_url,
        #         "-c:v", "copy",  # Copy video stream without re-encoding
        #         "-an",  # No audio
        #         "-f", "mp4",  # Output as MP4 directly
        #         "-movflags", "+faststart+frag_keyframe+empty_moov",  # Optimize for streaming
        #         "-frag_duration", "1000000",  # 1 second fragments
        #         "-reset_timestamps", "1",  # Reset timestamps for clean output
        #         str(self.local_path)
        #     ]
        logger.debug(f"Running FFmpeg: {' '.join(cmd)}")

        self.ffmpeg_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
            
    async def _save_video_async(self):
        """Save the recorded video to storage asynchronously."""
        try:
            self._update_status({
                'status': 'merging',
                'message': 'Merging video segments'
            })
            
            merged_path = os.path.join(self.record_dir, f"{self.stream_id}_{int(time.time())}_final.mp4")
            print("merged_path: ", merged_path)
            cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(self.segment_list_path),
                    "-c", "copy",
                    str(merged_path)
                ]
            logger.info(f"Running FFmpeg to merge videos: {' '.join(cmd)}")
            merge_proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await merge_proc.wait()
            if merge_proc.returncode != 0:
                error_msg = await merge_proc.stderr.read()
                logger.error(f"Failed to merge video: {error_msg}")
                self._update_status({
                    'status': 'error',
                    'error': f'Failed to merge video: {error_msg}'
                })
                return
            
            self._update_status({
                'status': 'uploading',
                'message': 'Uploading video to storage'
            })
            
            await self._save_video_with_custom_name(merged_path)
        except Exception as e:
            logger.error(f"Error in async video saving for stream {self.stream_id}: {e}")
            self._update_status({
                'status': 'error',
                'error': str(e)
            })
        finally:
            # Clean up temporary file
            if self.record_dir is not None and os.path.exists(self.record_dir):
                try:
                    shutil.rmtree(self.record_dir)
                    logger.info(f"Removed temporary file {self.record_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {self.local_path}: {e}")
    
    async def _save_video_with_custom_name(self, merged_path: str):
        """Save the recorded video to storage with custom filename."""
        try:
            # Read the video file and save to Minio
            with open(merged_path, 'rb') as f:
                video_data = io.BytesIO(f.read())
                
            # Save to Minio if storage is available with custom filename
            # Note: In async context, we can't reliably get the request, so we'll use default path
            object_path = minio_client.save_video(video_data, self.stream_id, self.record_code)
            
            if object_path is None:
                logger.warning("Video recorded but not saved to storage (storage unavailable)")
                self._update_status({
                    'status': 'error',
                    'error': 'Storage unavailable',
                    'message': 'Video recorded but not saved to storage'
                })
            else:
                logger.info(f"Recording completed for stream {self.stream_id}, saved to {object_path}")
                self._update_status({
                    'status': 'completed',
                    'object_path': object_path,
                    'completed_at': time.time(),
                    'message': 'Recording completed successfully'
                })
            
            return object_path
        except Exception as e:
            logger.error(f"Failed to save video to storage: {e}")
            self._update_status({
                'status': 'error',
                'error': str(e)
            })
            return None
