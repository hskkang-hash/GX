import logging
from typing import Optional

from core.base import get_current_request
from django.contrib.auth import get_user
from asgiref.sync import async_to_sync, sync_to_async
from surveillance.models import VideoAnalysis
from surveillance.services.video_analysis_service import VideoAnalysisService
from stream_monitors.services.capture_service import CaptureService
from stream_monitors.schemas.schemas_djantic_in import (
    AIStreamUrlInSchema,
    ExternalStreamMonitorInSchema,
    StartRecordingInSchema,
    StopRecordingInSchema,
    StreamMonitorCaptureInSchema,
    StreamMonitorsInSchema,
)
from stream_monitors.schemas.schemas_djantic_out import AIModelOutSchema, StreamMonitorOutSchema
from stream_monitors.services.stream_monitor_services import StreamMonitorService
from stream_monitors.models import StreamMonitorRecord
from ninja_extra import api_controller, route
from ninja.errors import ValidationError
from core.role.permission import path_permission
from core.common.base_response import BaseResponse
from common.constant import MESSAGE_ENUM
from core.api.v1.auth import CustomJWTAuth
from ninja_jwt.authentication import JWTAuth

logger = logging.getLogger(__name__)


@api_controller('/stream-monitors', tags=['Stream Monitors'])
class StreamMonitorsAPI:
    @route.get('', auth=CustomJWTAuth())
    def get_stream_monitors(self, request, ):
        stream_monitors = StreamMonitorService.get_stream_monitors()
        stream_monitors_out = StreamMonitorOutSchema.from_queryset(stream_monitors, many=True)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_STREAM_MONITORS_SUCCESS, "Stream monitors retrieved successfully"),
            data=stream_monitors_out
        )

    @route.post('')
    def update_stream_monitor(self, request, stream_monitors_in: StreamMonitorsInSchema):
        try:
            stream_monitors = StreamMonitorService.update_stream_monitors(stream_monitors_in)
            stream_monitors_out = StreamMonitorOutSchema.from_queryset(stream_monitors, many=True)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_STREAM_MONITOR_SUCCESS, "Stream monitor updated successfully"),
                data=stream_monitors_out
            )
        except ValidationError as e:
            logger.error(f"Validation error in update_stream_monitor: {str(e)}")
            return BaseResponse(
                status_code=400,
                message=f"Validation error: {str(e)}",
                data=None
            )
        except Exception as e:
            logger.error(f"Unexpected error in update_stream_monitor: {str(e)}")
            return BaseResponse(
                status_code=500,
                message="An unexpected error occurred while updating stream monitor",
                data=None
            )

    @route.post('/capture', auth=CustomJWTAuth())
    def get_stream_monitor_capture(self, request, data: StreamMonitorCaptureInSchema):
        try:
            capture_service = CaptureService()
            capture_response = capture_service.capture_image(data.stream_monitor_code, data.ai_model__code)
            object_path = capture_response.object_path
            if object_path:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_STREAM_MONITOR_CAPTURE_SUCCESS, "Stream monitor capture retrieved successfully"),
                    data={
                        "object_path": object_path
                    }
                )
            else:
                return BaseResponse(
                    status_code=404,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_STREAM_MONITOR_CAPTURE_FAILED, "Stream monitor capture failed"),
                    data={
                        "object_path": object_path
                    }
                )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_STREAM_MONITOR_CAPTURE_FAILED, "Stream monitor capture failed"),
                data=[]
        )
    
    @route.post('/start-record', auth=CustomJWTAuth())
    def start_record(self, request, stream_monitor_code: str, ai_model__code: Optional[str] = None):
        record_id, record_code = async_to_sync(StreamMonitorService.start_record)(
            stream_monitor_code, 
            ai_model__code,
            enable_detection=True,
            from_fe=True,
        )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.START_RECORD_SUCCESS, "Stream monitor record started successfully"),
            data={
                "record_id": record_id,
                "record_code": record_code
            }
        )
    
    @route.post('/stop-record', auth=CustomJWTAuth())
    def stop_record(self, request, stream_monitor_code: str, record_id: str, ai_model__code: Optional[str] = None):
        request_user = get_current_request().user
        # Get group_id from user profile
        group_id = None
        if request_user and hasattr(request_user, 'userprofilelink') and request_user.userprofilelink and request_user.userprofilelink.group:
            group_id = str(request_user.userprofilelink.group.id)
        
        object_path = async_to_sync(StreamMonitorService.stop_record)(
            stream_monitor_code,
            record_id,
            request_user,
            enable_detection=False,
            group_id=group_id,
        )

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(
                MESSAGE_ENUM.STOP_RECORD_SUCCESS,
                "Stream monitor record stopped successfully",
            ),
            data={"object_path": object_path},
        )

    # Public endpoints for 3rd parties (no auth): record-only (no detect / no video_analysis)
    @route.post("/{drone_uid}/start-recording")
    def start_recording_public(self, request, drone_uid: str, data: StartRecordingInSchema):
        logger.info(f"🔍 [START_RECORDING_PUBLIC] ===== API CALLED =====")
        logger.info(f"🔍 [START_RECORDING_PUBLIC] Starting recording for drone_uid: {drone_uid}")
        try:
            logger.info(f"🔍 [START_RECORDING_PUBLIC] Calling StreamMonitorService.start_record...")
            record_id, stream_monitor_id = async_to_sync(StreamMonitorService.start_record)(
                drone_uid,
                None,
                enable_detection=False,
                group_id=data.group if data.group else None,
                from_fe=False,
            )
            logger.info(f"🔍 [START_RECORDING_PUBLIC] start_record returned: record_id={record_id}, stream_monitor_id={stream_monitor_id}")
            
            # Check if recording actually started (record_id should not be None)
            if record_id is None:
                logger.error(f"❌ [START_RECORDING_PUBLIC] Failed to start recording for drone_uid: {drone_uid}. Record ID is None.")
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message="Failed to start recording. API call to AI_GRPC service may have failed. Check server logs for details.",
                    data=None,
                )
            
            logger.info(f"✅ [START_RECORDING_PUBLIC] Recording started successfully for drone_uid: {drone_uid}, record_id: {record_id}")
            return BaseResponse(
                status_code=200,
                success=True,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.START_RECORD_SUCCESS, "Stream monitor record started successfully"),
                data={"record_id": record_id},
            )
        except Exception as exc:
            print(f"❌ [START_RECORDING_PUBLIC] Error: {type(exc).__name__}: {str(exc)}")
            logger.error(f"❌ [START_RECORDING_PUBLIC] Error starting public recording for drone_uid={drone_uid}: {str(exc)}")
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )

    @route.post("/{drone_uid}/stop-recording")
    def stop_recording_public(self, request, drone_uid: str, data: StopRecordingInSchema):
        logger.info(f"🛑 [STOP_RECORDING_PUBLIC] ===== API CALLED =====")
        logger.info(f"🛑 [STOP_RECORDING_PUBLIC] drone_uid={drone_uid}, data={data}")
        try:
            logger.info(f"🛑 [STOP_RECORDING_PUBLIC] Searching for running record with stream_id={drone_uid}")
            record = (
                StreamMonitorRecord._base_manager.filter(stream_id=drone_uid, status="running")
                .order_by("-created_at", "-id")
                .first()
            )
            if not record:
                logger.warning(f"⚠️ [STOP_RECORDING_PUBLIC] No running recording found for drone_uid={drone_uid}")
                return BaseResponse(
                    status_code=404,
                    success=False,
                    message="No running recording found",
                    data=None,
                )
            
            logger.info(f"✅ [STOP_RECORDING_PUBLIC] Found record: id={record.id}, status={record.status}, created_at={record.created_at}")
            logger.info(f"🛑 [STOP_RECORDING_PUBLIC] Calling StreamMonitorService.stop_record with: drone_uid={drone_uid}, record_id={record.id}, group_id={data.group}")

            object_path = async_to_sync(StreamMonitorService.stop_record)(
                drone_uid,
                str(record.id),
                user=None,
                enable_detection=False,
                group_id=data.group,
            )
            
            logger.info(f"🛑 [STOP_RECORDING_PUBLIC] stop_record returned: object_path={object_path}")
            
            # Check if stop_record failed (returned None)
            if object_path is None:
                logger.error(f"❌ [STOP_RECORDING_PUBLIC] Failed to stop recording for drone_uid={drone_uid}, record_id={record.id}")
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message="Failed to stop recording. Check server logs for details.",
                    data=None,
                )
            
            logger.info(f"✅ [STOP_RECORDING_PUBLIC] Recording stopped successfully for drone_uid={drone_uid}, object_path={object_path}")
            return BaseResponse(
                status_code=200,
                success=True,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.STOP_RECORD_SUCCESS, "Stream monitor record stopped successfully"),
                data={"object_path": object_path},
            )
        except Exception as exc:
            logger.exception(f"❌ [STOP_RECORDING_PUBLIC] Exception stopping public recording for drone_uid={drone_uid}: {exc}")
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
    
    @route.post('/pause-record', auth=CustomJWTAuth())
    def pause_record(self, request, stream_monitor_code: str, record_id: str, ai_model__code: Optional[str] = None):
        object_path = async_to_sync(StreamMonitorService.pause_record)(
            stream_monitor_code, 
            record_id, 
            ai_model__code
        )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.PAUSE_RECORD_SUCCESS, "Stream monitor record paused successfully"),
            data={
                "object_path": object_path
            }
        )
    
    @route.post('/resume-record', auth=CustomJWTAuth())
    def resume_record(self, request, stream_monitor_code: str, record_id: str, ai_model__code: Optional[str] = None):
        object_path = async_to_sync(StreamMonitorService.resume_record)(
            stream_monitor_code, 
            record_id, 
            ai_model__code
        )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.RESUME_RECORD_SUCCESS, "Stream monitor record resumed successfully"),
            data={
                "object_path": object_path
            }
        )

    @route.get('/ai-models', auth=CustomJWTAuth())
    def get_ai_models(self, request):
        ai_models_queryset = StreamMonitorService.get_ai_models()
        
        # Get language code
        language_code = request.user.language.code if (request.user.language and hasattr(request.user, 'language')) else 'en'
        # Convert queryset to list to avoid multiple evaluations
        ai_models_list = list(ai_models_queryset)
        
        # Create schema output
        ai_models_out = AIModelOutSchema.from_queryset(ai_models_list, many=True)
        
        # Create a mapping of id to model instance for efficient lookup
        ai_models_dict = {model.id: model for model in ai_models_list}
        
        # Update each dict with translated name
        for ai_model_dict in ai_models_out:
            if 'id' in ai_model_dict:
                model_instance = ai_models_dict.get(ai_model_dict['id'])
                ai_model_dict['name'] = model_instance.get_translation('name', language_code)
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_AI_MODELS_SUCCESS, "AI models retrieved successfully"),
            data=ai_models_out
        )

    @route.get('/ai-stream-url', auth=CustomJWTAuth())
    def get_ai_stream_url(self, request, stream_monitor_id: str):
        ai_stream_url = StreamMonitorService.get_ai_stream_url(stream_monitor_id)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_AI_STREAM_URL_SUCCESS, "AI stream URL retrieved successfully"),
            data=ai_stream_url
        )

    @route.post('/start-ai-dual-stream')
    def start_ai_dual_stream(self, request, stream_monitor_id: str, output_file: str = None, fps: int = 25, stream_width: int = 1280, stream_height: int = 720):
        stream_resolution = (stream_width, stream_height)
        # result = StreamMonitorService.start_ai_dual_stream(stream_monitor_id, output_file, fps, stream_resolution)
        result = StreamMonitorService.start_ai_dual_stream_optimized(stream_monitor_id, stream_monitor_id)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.START_AI_DUAL_STREAM_SUCCESS, "AI dual stream started successfully"),
            data=result
        )

    @route.post('/stop-ai-dual-stream')
    def stop_ai_dual_stream(self, request, stream_monitor_id: str, stream_id: str):
        result = StreamMonitorService.stop_ai_dual_stream_optimized(stream_id, stream_monitor_id)
        if result.get('object_path'):
            stream_monitor = async_to_sync(VideoAnalysisService.create_video_analysis_from_stream_monitor)(stream_monitor_id, result.get('object_path'))
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.STOP_AI_DUAL_STREAM_SUCCESS, "AI dual stream stopped successfully"),
            data=result
        )

    @route.get('/ai-dual-stream-status')
    def get_ai_dual_stream_status(self, request, stream_monitor_id: str):
        result = StreamMonitorService.get_ai_dual_stream_status(stream_monitor_id)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_AI_DUAL_STREAM_STATUS_SUCCESS, "AI dual stream status retrieved successfully"),
            data=result
        )

    @route.post('/external-stream-monitors')
    def add_external_stream_monitor(self, request, stream_monitor_in: ExternalStreamMonitorInSchema):
        try:
            stream_monitor = StreamMonitorService.add_external_stream_monitor(stream_monitor_in)
            stream_monitor_out = StreamMonitorOutSchema.from_queryset(stream_monitor)
            return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ADD_EXTERNAL_STREAM_MONITOR_SUCCESS, "External stream monitor added successfully"),
                    data=stream_monitor_out
                )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ADD_EXTERNAL_STREAM_MONITOR_FAILED, "External stream monitor added failed"),
                data=None
            )

    @route.delete('/external-stream-monitors/{stream_monitor_id}')
    def delete_external_stream_monitor(self, request, stream_monitor_id: str):
        try:
            success, message = StreamMonitorService.delete_external_stream_monitor(stream_monitor_id)
            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                    data=message
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                    data=message
                )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=e
            )

    @route.put('/external-stream-monitors')
    def update_external_stream_monitor(self, request, stream_monitor_in: ExternalStreamMonitorInSchema):
        try:
            success, message = StreamMonitorService.update_external_stream_monitor(stream_monitor_in)
            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_EXTERNAL_STREAM_MONITOR_SUCCESS, "External stream monitor updated successfully"),
                    data=message
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_EXTERNAL_STREAM_MONITOR_FAILED, "External stream monitor updated failed"),
                    data=message
                )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_EXTERNAL_STREAM_MONITOR_FAILED, "External stream monitor updated failed"),
                data=e
            )