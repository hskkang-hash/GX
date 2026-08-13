import asyncio
from typing import Dict, Callable

from stream_monitors.tasks.record_task import RecordingTask
from stream_monitors.schemas.recording_schemas import RecordingResponse, RecordingStatusResponse
from stream_monitors.utils.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)


class RecordService:
    """Service class for handling video recording operations."""
    
    def __init__(self):
        self.active_recordings: Dict[str, RecordingTask] = {}
        self.action_recordings: Dict[str, Callable] = {
            "START_RECORD": self._start_recording,
            "STOP_RECORD": self._stop_recording,
            "PAUSE_RECORD": self._pause_recording,
            "RESUME_RECORD": self._resume_recording,
        }
    
    async def control_record(self, stream_id: str, record_id: str, record_code: str, action: str, ai_model__code: str, record_url: str = None) -> RecordingResponse:
        """
        Toggle recording for a stream. If not recording, start recording. 
        If already recording, stop and save.
        
        Args:
            stream_id: ID of the stream to record from
            record_id: ID of the record to control
            action: Action to perform on the record (start, stop, pause, resume, get_status)
        Returns:
            RecordingResponse: Information about the recording status
            
        Raises:
            ValueError: If stream not found
            Exception: For other recording-related errors
        """
        try:
            handler = self.action_recordings.get(action)
            if not handler:
                raise ValueError(f"Invalid action: {action}")
            
            handler_params = {
                'stream_id': stream_id,
                'record_id': record_id,
                'record_code': record_code,
                'ai_model__code': ai_model__code,
                'record_url': record_url
            }
            return await handler(handler_params)
                
        except ValueError as e:
            logger.warning(f"Recording validation error for stream {stream_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error toggling recording for stream {stream_id}: {e}")
            raise Exception(f"Failed to toggle recording: {str(e)}")
    
    async def get_recording_status(self, stream_id: str) -> RecordingResponse:
        """
        Get the current recording status for a stream.
        
        Args:
            stream_id: ID of the stream to check
            
        Returns:
            RecordingResponse: Current recording status
            
        Raises:
            ValueError: If stream not found
        """
        try:
            is_recording = self._is_recording(stream_id)
            
            return RecordingResponse(
                stream_id=stream_id,
                is_recording=is_recording,
                object_path=None,
                message=f"Recording {'active' if is_recording else 'inactive'} for stream {stream_id}",
                success=True
            )
            
        except ValueError as e:
            logger.warning(f"Recording status validation error for stream {stream_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting recording status for stream {stream_id}: {e}")
            raise Exception(f"Failed to get recording status: {str(e)}")
    
    async def get_recording_status_by_code(self, record_code: str) -> RecordingStatusResponse:
        """
        Get the recording status by record_code from Redis.
        
        Args:
            record_code: The record code to look up
            
        Returns:
            RecordingStatusResponse: Recording status from Redis
        """
        try:
            status_data = redis_client.get_recording_status(record_code)
            
            if not status_data:
                return RecordingStatusResponse(
                    record_code=record_code,
                    status="not_found",
                    is_recording=False,
                    message="Recording not found",
                    success=False
                )
            
            return RecordingStatusResponse(
                record_code=record_code,
                stream_id=status_data.get('stream_id'),
                record_id=status_data.get('record_id'),
                status=status_data.get('status', 'unknown'),
                is_recording=status_data.get('is_recording', False),
                object_path=status_data.get('object_path'),
                message=status_data.get('message'),
                error=status_data.get('error'),
                created_at=status_data.get('created_at'),
                started_at=status_data.get('started_at'),
                stopped_at=status_data.get('stopped_at'),
                completed_at=status_data.get('completed_at'),
                updated_at=status_data.get('updated_at'),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error getting recording status for record_code {record_code}: {e}")
            return RecordingStatusResponse(
                record_code=record_code,
                status="error",
                is_recording=False,
                error=str(e),
                success=False
            )
    
    async def _start_recording(self, params: Dict[str, str]) -> RecordingResponse:
        """Start recording for a stream."""
        try:
            recording_task = await RecordingTask.create(params['stream_id'], params['record_id'], params['record_code'], params['ai_model__code'], params['record_url'], )
            started = recording_task.start_recording()
            
            if started:
                self.active_recordings[params['stream_id']] = recording_task
                print(f"Recording started for stream {params['stream_id']}")
                logger.info(f"Recording started for stream {params['stream_id']}")
                
                # Add a small delay to let the recording loop start
                await asyncio.sleep(0.1)
                
                # Check if recording is still active after starting
                if recording_task.is_recording:
                    logger.info(f"Recording confirmed active for stream {params['stream_id']}")
                else:
                    logger.warning(f"Recording stopped immediately after starting for stream {params['stream_id']}")
                
                return RecordingResponse(
                    stream_id=params['stream_id'],
                    is_recording=True,
                    object_path=None,
                    message="Recording started successfully",
                    success=True
                )
            else:
                logger.warning(f"Failed to start recording for stream {params['stream_id']}")
                return RecordingResponse(
                    stream_id=params['stream_id'],
                    is_recording=False,
                    object_path=None,
                    message="Failed to start recording",
                    success=False
                )
                
        except Exception as e:
            logger.error(f"Error starting recording for stream {params['stream_id']}: {e}")
            raise
    
    async def _stop_recording(self, params: Dict[str, str]) -> RecordingResponse:
        """Stop recording for a stream and save the video."""
        try:
            recording_task = self.active_recordings[params['stream_id']]
            object_path = await recording_task.stop_recording()
            
            # Remove from active recordings
            del self.active_recordings[params['stream_id']]
            
            if object_path:
                logger.info(f"Recording stopped for stream {params['stream_id']}, video will be saved to: {object_path}")
                return RecordingResponse(
                    stream_id=params['stream_id'],
                    is_recording=False,
                    object_path=object_path,
                    message="Recording stopped successfully. Video is being saved in the background.",
                    success=True
                )
            else:
                logger.warning(f"Recording stopped but video could not be saved for stream {params['stream_id']}")
                return RecordingResponse(
                    stream_id=params['stream_id'],
                    is_recording=False,
                    object_path=None,
                    message="Recording stopped but video could not be saved",
                    success=False
                )
                
        except Exception as e:
            logger.error(f"Error stopping recording for stream {params['stream_id']}: {e}")
            # Clean up the recording task even if there was an error
            if params['stream_id'] in self.active_recordings:
                del self.active_recordings[params['stream_id']]
            raise
    
    async def _resume_recording(self, params: Dict[str, str]) -> RecordingResponse:
        """Resume recording for a stream."""
        try:
            recording_task = self.active_recordings[params['stream_id']]
            
            # Check if the task is currently recording
            if recording_task.is_recording:
                logger.warning(f"Recording already active for stream {params['stream_id']}")
                return RecordingResponse(
                    stream_id=params['stream_id'],
                    is_recording=True,
                    object_path=None,
                    message="Recording already active",
                    success=True
                )
            
            # Resume the recording
            started = recording_task.start_recording(is_new_record=False)
            
            if started:
                logger.info(f"Recording resumed for stream {params['stream_id']}")
                return RecordingResponse(
                    stream_id=params['stream_id'],
                    is_recording=True,
                    object_path=None,
                    message="Recording resumed successfully",
                    success=True
                )
            else:
                logger.warning(f"Failed to resume recording for stream {params['stream_id']}")
                return RecordingResponse(
                    stream_id=params['stream_id'],
                    is_recording=False,
                    object_path=None,
                    message="Failed to resume recording",
                    success=False
                )
                
        except Exception as e:
            logger.error(f"Error resuming recording for stream {params['stream_id']}: {e}")
            raise
        
    async def _pause_recording(self, params: Dict[str, str]) -> RecordingResponse:
        """Pause recording for a stream."""
        try:
            recording_task = self.active_recordings[params['stream_id']]
            await recording_task.stop_recording(is_pause=True)
            return RecordingResponse(
                stream_id=params['stream_id'],
                is_recording=False,
                object_path=None,
                message="Recording paused successfully",
                success=True
            )
        except Exception as e:
            logger.error(f"Error pausing recording for stream {params['stream_id']}: {e}")
            raise
        
    def _is_recording(self, stream_id: str) -> bool:
        """Check if a stream is currently being recorded."""
        return (stream_id in self.active_recordings and 
                self.active_recordings[stream_id].is_recording)
        
        
record_service = RecordService()
