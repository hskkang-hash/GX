import json
import logging
import random
import asyncio
import os
import io
import shutil
import time
from typing import Any, Dict, Tuple, Optional
import uuid
from core.middleware.refresh_token import get_current_request
from core.user.models import CoreUser, UserGroup
import requests
import subprocess
import threading
from datetime import datetime
from django.db import transaction
from django.db.models import Value, CharField, Q, F
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from ninja.errors import ValidationError

from common.constant import MESSAGE_ENUM
from common.tenant_filters import filter_by_group_field
from stream_monitors.utils.constants import VALID_STREAMS_URL
from stream_monitors.utils.minio_client import minio_client
from devices.models import Device
from stream_monitors.schemas.schemas_djantic_in import ExternalStreamMonitorInSchema, StreamMonitorsInSchema
from config import settings
from stream_monitors.models import AIModel, DrawingSession, StreamMonitor, StreamMonitorAIModel, StreamMonitorRecord
from safedelete.models import (
    SafeDeleteModel,
    SOFT_DELETE,
    SOFT_DELETE_CASCADE,
    HARD_DELETE,
    HARD_DELETE_NOCASCADE,
    NO_DELETE,
)
logger = logging.getLogger(__name__)
valid_streams = VALID_STREAMS_URL

class StreamMonitorService:
    # Class variable to track running ffmpeg processes
    _running_processes = {}  # {stream_monitor_code: process}

    @classmethod
    def _get_group_id_from_user(cls, request_user: Optional[CoreUser]) -> Optional[str]:
        try:
            if request_user and hasattr(request_user, 'userprofilelink') and request_user.userprofilelink and request_user.userprofilelink.group:
                return str(request_user.userprofilelink.group.id)
        except Exception:
            return None
        return None

    @classmethod
    def _set_active_and_sync(
        cls,
        stream_monitor: StreamMonitor,
        is_active: bool,
        request_user: Optional[CoreUser],
        stream_monitor_in: Optional[Any] = None,
    ):
        """Toggle StreamMonitor.is_active and synchronize AI + recording/detection.

        - OFF: stop AI dual stream, stop recording/detection, mark AI rows in_use false
        - ON: restore AI model (prefer payload.ai_models[0], else last known), start AI dual stream
        """
        stream_code = stream_monitor.code
        group_id = cls._get_group_id_from_user(request_user)

        if not is_active:
            # Persist OFF
            stream_monitor.is_active = False
            stream_monitor.save()

            # Stop AI stream best-effort
            try:
                cls.stop_ai_dual_stream_optimized(stream_code, stream_code)
            except Exception as e:
                logger.warning(f"Failed stopping AI dual stream for {stream_code}: {e}")

            # Stop any running recording/detection (best-effort)
            try:
                running = StreamMonitorRecord._base_manager.filter(stream_id=stream_code, status__in=['running', 'paused']).order_by('-created_at', '-id').first()
                if running:
                    from asgiref.sync import async_to_sync
                    async_to_sync(cls.stop_record)(stream_code, str(running.id), request_user, enable_detection=True, group_id=group_id)
            except Exception as e:
                logger.warning(f"Failed stopping record/detection for {stream_code}: {e}")

            # Disable AI model rows
            try:
                StreamMonitorAIModel._base_manager.filter(stream_monitor=stream_monitor).update(
                    in_use=False,
                    ai_stream_url=None,
                    is_active=False,
                )
            except Exception as e:
                logger.warning(f"Failed updating StreamMonitorAIModel OFF for {stream_code}: {e}")

            return

        # ON
        stream_monitor.is_active = True
        stream_monitor.save()

        # Choose AI model to restore
        selected_ai_model = None
        try:
            ai_ids = None
            if stream_monitor_in is not None and getattr(stream_monitor_in, 'ai_models', None):
                ai_ids = list(stream_monitor_in.ai_models)
            if ai_ids:
                selected_ai_model = AIModel.objects.filter(id__in=ai_ids).first()
            if not selected_ai_model:
                # restore last known model on StreamMonitorAIModel
                qs = StreamMonitorAIModel._base_manager.filter(stream_monitor=stream_monitor).exclude(ai_model__isnull=True)
                try:
                    selected_ai_model = qs.order_by('-modified_at', '-id').first().ai_model  # type: ignore
                except Exception:
                    row = qs.order_by('-id').first()
                    selected_ai_model = row.ai_model if row else None
        except Exception:
            selected_ai_model = None

        if not selected_ai_model:
            # No AI configured; leave AI off
            return

        # Start AI dual stream
        try:
            res = cls.start_ai_dual_stream_optimized(stream_code, stream_code, stream_monitor.is_external, selected_ai_model.code.lower())
            if not res.get('success'):
                return
        except Exception as e:
            logger.warning(f"Failed starting AI dual stream for {stream_code}: {e}")
            return

        # Persist selected AI model row in_use
        try:
            row = StreamMonitorAIModel._base_manager.filter(stream_monitor=stream_monitor, ai_model=selected_ai_model).first()
            if row:
                row.in_use = True
                row.is_active = True
                row.ai_stream_url = f"stream/ai_{stream_code}"
                row.save()
            else:
                StreamMonitorAIModel.objects.create(
                    stream_monitor=stream_monitor,
                    ai_model=selected_ai_model,
                    in_use=True,
                    is_active=True,
                    ai_stream_url=f"stream/ai_{stream_code}",
                )
        except Exception as e:
            logger.warning(f"Failed updating StreamMonitorAIModel ON for {stream_code}: {e}")

    @classmethod
    def update_external_stream_monitor(cls, stream_monitor_in: ExternalStreamMonitorInSchema):
        try:
            stream_monitor = StreamMonitor.objects.get(id=stream_monitor_in.id)
            stream_monitor.external_drone_name = stream_monitor_in.external_drone_name
            stream_monitor.external_operation_name = stream_monitor_in.external_operation_name
            stream_monitor.external_registration_number = stream_monitor_in.external_registration_number
            stream_monitor.external_manufacturer = stream_monitor_in.external_manufacturer
            stream_monitor.external_flight_distance = stream_monitor_in.external_flight_distance
            stream_monitor.external_flight_time = stream_monitor_in.external_flight_time
            stream_monitor.external_flight_altitude = stream_monitor_in.external_flight_altitude
            stream_monitor.external_start_point_x = stream_monitor_in.external_start_point_x
            stream_monitor.external_start_point_y = stream_monitor_in.external_start_point_y
            stream_monitor.external_end_point_x = stream_monitor_in.external_end_point_x
            stream_monitor.external_end_point_y = stream_monitor_in.external_end_point_y
            stream_monitor.external_start_time = stream_monitor_in.external_start_time
            stream_monitor.external_end_time = stream_monitor_in.external_end_time
            stream_monitor.external_remark = stream_monitor_in.remark
            stream_monitor.save()
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_EXTERNAL_STREAM_MONITOR_SUCCESS)
        except Exception as e:
            logger.error(f"Error updating external stream monitor: {e}")
            return False, MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_EXTERNAL_STREAM_MONITOR_FAILED)

    @classmethod
    def _cancel_auto_stop_task(cls, record_instance):
        """Helper method to cancel auto-stop task"""
        if record_instance.auto_stop_task_id:
            try:
                from celery import current_app
                current_app.control.revoke(record_instance.auto_stop_task_id, terminate=True)
                logger.info(f"🚫 Cancelled auto-stop task {record_instance.auto_stop_task_id} for record {record_instance.id}")

                # Clear the task ID since it's been cancelled
                record_instance.auto_stop_task_id = None
                record_instance.save()
                return True

            except Exception as cancel_error:
                logger.warning(f"⚠️ Failed to cancel auto-stop task {record_instance.auto_stop_task_id}: {str(cancel_error)}")
                return False
        return True

    @classmethod
    def _schedule_auto_stop_task(cls, stream_monitor_id: str, record_instance):
        """Helper method to schedule auto-stop task"""
        try:
            from stream_monitors.tasks import auto_stop_record

            timeout_seconds = 5

            # Schedule the auto-stop task
            auto_stop_task = auto_stop_record.apply_async(
                args=[stream_monitor_id, str(record_instance.id)],
                countdown=timeout_seconds
            )

            # Store the task ID
            record_instance.auto_stop_task_id = auto_stop_task.id
            record_instance.save()

            logger.info(f"📅 Scheduled auto-stop task {auto_stop_task.id} for record {record_instance.id} in {timeout_seconds} seconds")
            return True

        except Exception as task_error:
            logger.error(f"⚠️ Failed to schedule auto-stop task for record {record_instance.id}: {str(task_error)}")
            return False

    @staticmethod
    def get_list_available_streams():
        """
        Get list of available streams
        """
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        stream_url = f"{settings.STREAM_URL}/manage/v3/paths/list"
        response = requests.get(
            stream_url,
            headers=headers,
            timeout=5,
            verify=False
        )
        response_data = response.json()
        stream_items = [item['name'] for item in response_data.get('items', [])]
        return stream_items

    @classmethod
    @transaction.atomic
    def get_stream_monitors(cls, user=None):
        """스트림 모니터 목록.

        W0-14 (파일럿 1개) — `user` 를 주면 **요청자의 테넌트로 좁힌다.**
        주지 않으면 예전과 같다(내부 호출·배치용).

        왜 여기서 좁히나 (D-207)
            `StreamMonitor.objects` 는 dj-core `CustomManagerGroup` 이고, 그 필터는
            ① `superuser` 역할 통과 ② `Q(created_by__isnull=True)` OR 로 뚫려 있다.
            둘 다 §0.4 라 고칠 수 없다. 그래서 **뷰·서비스가 주 통제**다.
            이 경로가 프로브가 누출을 실측한 그 경로다
            (evidence/W0-14/http_leak_probe.md · W0-16/http_role_split_test.md).

        ⚠ `group` 이 비어 있는 레코드는 이 필터에서 **빠진다.** 소유 테넌트를
          말할 수 없는 것을 모두에게 보이는 것이 곧 누출이었다. 귀속은 W0-13
          (created_by/group 백필)이 하고, 그 전까지는 닫는 쪽이 기본값이다.
        """
        # Check all devices and create StreamMonitor records if they don't exist
        devices = Device.objects.filter(active=True, deleted=None)
        if devices.count() > 0:
            for device in devices:
                if device.unit_id:  # Only process devices with unit_id
                    # Check if StreamMonitor with this code already exists
                    stream_monitor_exists = StreamMonitor._base_manager.filter(drone=device).exists()
                    if not stream_monitor_exists:
                        # Create new StreamMonitor record
                        StreamMonitor.objects.create(
                            name=device.name,
                            code=device.unit_id,
                            ip_source="192.169.1.100",
                            is_active=True,
                            is_visualize=True,
                            drone=device,
                            order=0,
                            is_external=False,
                            created_by=device.created_by,
                            modified_by=device.created_by,
                            group=device.group
                        )
            # # check DrawingSession with id=1 exist
            # drawing_session = DrawingSession.objects.filter(id=1).exists()
            # if not drawing_session:
            #     # Create new DrawingSession record
            #     User = get_user_model()
            #     DrawingSession.objects.create(
            #         id=1,
            #         name="Drawing Session 1",
            #         stream_monitor=StreamMonitor.objects.first(),
            #         created_by=User.objects.first()
            #     )

        # get all stream monitors and ai models for each stream monitor
        # check ai setting for each stream monitor
        stream_monitors = StreamMonitor.objects.annotate(drone_color=F('drone__color')).filter(
            Q(drone__active=True, drone__in=devices) | Q(is_external=True)
        ).filter(deleted__isnull=True).order_by('order', 'id')

        if user is not None:
            stream_monitors = filter_by_group_field(stream_monitors, user)

        return stream_monitors

    @classmethod
    def _validate_stream_monitor_data(cls, stream_monitors_in: StreamMonitorsInSchema):
        """Validate stream monitor data before processing"""
        for stream_monitor_in in stream_monitors_in.stream_monitors:
            # Check if StreamMonitor exists
            if not StreamMonitor._base_manager.filter(id=stream_monitor_in.id).exists():
                logger.error(f"StreamMonitor with id {stream_monitor_in.id} does not exist")
                raise ValidationError(f"StreamMonitor with id {stream_monitor_in.id} does not exist")

            # Check if Device exists
            if not Device._base_manager.filter(id=stream_monitor_in.drone_id).exists():
                logger.error(f"Device with id {stream_monitor_in.drone_id} does not exist")
                raise ValidationError(f"Device with id {stream_monitor_in.drone_id} does not exist")

        logger.info(f"Validation passed for {len(stream_monitors_in.stream_monitors)} stream monitors")

    @classmethod
    def _handle_ai_stream_request(cls, stream_monitor, stream_monitor_in, ai_stream_url, headers):
        """Handle AI stream request with proper error handling"""
        try:
            ai_model = AIModel.objects.filter(id__in=stream_monitor_in.ai_models).first()
            if not ai_model:
                logger.warning(f"No AI model found for stream {stream_monitor.code}")
                return None

            request_payload = {
                'stream_rtsp': f"{settings.RTSP_PATH_AI}/{stream_monitor.code}",
                'enabled': stream_monitor_in.in_use,
                'category': ai_model.code
            }

            response = requests.post(
                ai_stream_url,
                json=request_payload,
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for AI stream {stream_monitor.code}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for AI stream {stream_monitor.code}: {str(e)}")
            return None

    @classmethod
    def _update_ai_model_status(cls, ai_model_instance, response_data, stream_monitor, stream_monitor_in):
        """Update AI model status based on response"""
        if response_data and response_data.get('output', {}).get('hls_url'):
            ai_model_instance.in_use = True
            ai_model_instance.ai_stream_url = response_data.get('output', {}).get('hls_url')
            ai_model_instance.ai_model = AIModel.objects.filter(id__in=stream_monitor_in.ai_models).first()
            logger.info(f"AI stream started for {stream_monitor.code}: {ai_model_instance.ai_stream_url}")
        else:
            ai_model_instance.in_use = True
            ai_model_instance.ai_stream_url = None
            ai_model_instance.ai_model = AIModel.objects.filter(id__in=stream_monitor_in.ai_models).first()
            logger.warning(f"AI stream failed to start for {stream_monitor.code}")

        ai_model_instance.save()

    @classmethod
    def get_ai_stream_url(cls, stream_monitor_id: str) -> Dict[str, Any]:
        """Get AI stream URL for a stream monitor"""
        return {
            'success': True,
            'input_url': f"{settings.RTSP_URL}/stream/{stream_monitor_id}",
            'output_url': f"{settings.RTSP_URL}/stream/ai_{stream_monitor_id}"
        }

    @classmethod
    @transaction.atomic
    def update_stream_monitors(cls, stream_monitors_in: StreamMonitorsInSchema):
        """Update stream monitors.

        Enterprise toggle behavior:
        - per-stream `is_active` is the source of truth
        - turning OFF stops AI stream + stops recording/detection
        - turning ON restores last AI model (or one provided) and restarts AI stream
        """
        for stream_monitor_in in stream_monitors_in.stream_monitors:
            # Data already validated; map missing IDs to a 400 (ValidationError) instead of 500
            try:
                stream_monitor = StreamMonitor._base_manager.select_for_update().get(id=stream_monitor_in.id)
            except StreamMonitor.DoesNotExist:
                raise ValidationError([{
                    "loc": ["body", "stream_monitors", "id"],
                    "msg": f"StreamMonitor id={stream_monitor_in.id} not found",
                    "type": "value_error.not_found",
                }])



            # Handle is_active toggle first (so other updates can't accidentally start AI while off)
            if stream_monitor_in.is_active is not None and stream_monitor_in.is_active != stream_monitor.is_active:
                cls._set_active_and_sync(stream_monitor, bool(stream_monitor_in.is_active), request_user=get_current_request().user, stream_monitor_in=stream_monitor_in)

            # Update other fields
            if stream_monitor_in.is_visualize is not None:
                stream_monitor.is_visualize = stream_monitor_in.is_visualize
            if stream_monitor_in.order is not None:
                stream_monitor.order = stream_monitor_in.order
            stream_monitor.save()

            # If stream is inactive, do not mutate AI models here (avoid re-starting AI while OFF)
            if stream_monitor.is_active is False:
                continue

            # logger.info(f"Updated StreamMonitor {stream_monitor.id} with Device {drone.id}")
            stream_monitor_ai_models = StreamMonitorAIModel._base_manager.filter(stream_monitor=stream_monitor, in_use=True)
            logger.info(f"Found {stream_monitor_ai_models.count()} existing AI models for stream {stream_monitor.code}")

            for ai_model_id in (stream_monitor_in.ai_models or []):
                ai_model = AIModel.objects.get(id=ai_model_id)
                if StreamMonitorAIModel.objects.filter(stream_monitor=stream_monitor, ai_model=ai_model, in_use=True).exists():
                    # delete the stream monitor ai model
                    print(f"Deleting stream monitor ai model for {stream_monitor.code} and ai model {ai_model.id}")
                    cls.stop_ai_dual_stream_optimized(stream_monitor.code, stream_monitor.code)
                    stream_monitor_ai_model = StreamMonitorAIModel.objects.get(stream_monitor=stream_monitor, ai_model=ai_model)
                    stream_monitor_ai_model.in_use = False
                    stream_monitor_ai_model.ai_stream_url = None
                    stream_monitor_ai_model.save()
                elif StreamMonitorAIModel.objects.filter(stream_monitor=stream_monitor, in_use=False).exists():
                    # delete the stream monitor ai model
                    print(f"Restarting stream monitor ai model for {stream_monitor.code} and ai model {ai_model.id}")
                    result = cls.start_ai_dual_stream_optimized(stream_monitor.code, stream_monitor.code, stream_monitor.is_external, ai_model.code.lower())
                    if result['success']:
                        stream_monitor_ai_model = StreamMonitorAIModel.objects.get(stream_monitor=stream_monitor)
                        stream_monitor_ai_model.ai_model = ai_model
                        stream_monitor_ai_model.in_use = True
                        stream_monitor_ai_model.ai_stream_url = f"stream/ai_{stream_monitor.code}"
                        stream_monitor_ai_model.save()
                elif StreamMonitorAIModel.objects.filter(stream_monitor=stream_monitor).exists():
                    print(f"Updating stream monitor ai model for {stream_monitor.code} and ai model {ai_model.id}")
                    cls.stop_ai_dual_stream_optimized(stream_monitor.code, stream_monitor.code)
                    result = cls.start_ai_dual_stream_optimized(stream_monitor.code, stream_monitor.code, stream_monitor.is_external, ai_model.code.lower())
                    # if result['success']:
                    stream_monitor_ai_model = StreamMonitorAIModel.objects.get(stream_monitor=stream_monitor)
                    stream_monitor_ai_model.ai_model = ai_model
                    stream_monitor_ai_model.save()
                else:
                    print(f"Creating stream monitor ai model for {stream_monitor.code} and ai model {ai_model.id}")
                    result = cls.start_ai_dual_stream_optimized(stream_monitor.code, stream_monitor.code, stream_monitor.is_external, ai_model.code.lower())
                    if result['success']:
                        stream_monitor_ai_model = StreamMonitorAIModel.objects.create(stream_monitor=stream_monitor, ai_model=ai_model, in_use=True, ai_stream_url = f"stream/ai_{stream_monitor.code}")
                        stream_monitor_ai_model.save()

        return StreamMonitor.objects.filter(id__in=[stream_monitor_in.id for stream_monitor_in in stream_monitors_in.stream_monitors])

    @classmethod
    @transaction.atomic
    def stream_monitor_start(cls, stream_monitor_code: str, is_ai_model: bool = False):
        try:
            stream_monitor = StreamMonitor.objects.filter(name=stream_monitor_code).first()

            # Call API to get stream
            api_url = f"{settings.STREAM_URL}/stream/api/streams/{stream_monitor.code}/hls"
            headers = {
                'accept': 'application/json'
            }

            response = requests.get(
                api_url,
                headers=headers,
                timeout=10,
                verify=False
            )

            # response.raise_for_status()  # Raise exception for bad status codes
            response_data = response.json()
            # Return the stream_url from response
            stream_hls_endpoint = response_data.get('stream_hls_endpoint', None)
            if stream_hls_endpoint:
                if is_ai_model:
                    stream_hls_endpoint = stream_hls_endpoint.replace(".m3u8", "_ai.m3u8")
                return f"{settings.STREAM_URL}/hls/{stream_hls_endpoint}"
            else:
                return ""

        except StreamMonitor.DoesNotExist:
            logger.error(f"StreamMonitor with code {stream_monitor_code} not found")
            return ""
        except requests.RequestException as e:
            # raise Exception(f"Failed to register stream: {str(e)}")
            return ""
        except Exception as e:
            logger.error(f"Failed to start stream monitor {stream_monitor_code}: {str(e)}")
            return ""


    @classmethod
    @transaction.atomic
    def get_stream_monitor_record(cls, stream_monitor_id: str):
        try:
            record_url = settings.RECORD_URL
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
            response = requests.post(
                record_url,
                json={'stream_id': stream_monitor_id},
                headers=headers,
                timeout=5,  # Add timeout
                verify=False
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get stream monitor record for {stream_monitor_id}: {str(e)}")
            return {"error": "Failed to get record"}
        except Exception as e:
            logger.error(f"Unexpected error getting stream monitor record for {stream_monitor_id}: {str(e)}")
            return {"error": "Unexpected error"}

    @classmethod
    @transaction.atomic
    def get_ai_models(cls):
        return AIModel.objects.all()

    @classmethod
    @transaction.atomic
    def get_stream_monitor_capture(cls, stream_monitor_id: str):
        try:
            record_url = settings.CAPTURE_URL
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }

            # Prepare request body payload
            request_payload = {
                'stream_id': stream_monitor_id
            }
            response = requests.post(
                record_url,
                data=json.dumps(request_payload),
                headers=headers,
                verify=False
            )
            object_path = response.json().get('object_path', None)
            if object_path:
                return object_path
            else:
                return None
        except Exception as e:
            logger.error(f"Unexpected error getting stream monitor capture for {stream_monitor_id}: {str(e)}")
            return None

    @classmethod
    def find_stream_monitor(cls, stream_monitor_id: str, group_id: Optional[str] = None):
        logger.info(f"🔍 [FIND_STREAM_MONITOR] Looking for stream_monitor_id={stream_monitor_id}, group_id={group_id}")

        # Check if stream_monitor already exists
        stream_monitor = StreamMonitor._base_manager.filter(code=stream_monitor_id).first()

        if stream_monitor:
            # Stream monitor exists
            logger.info(f"✅ [FIND_STREAM_MONITOR] Found existing stream_monitor: id={stream_monitor.id}, is_external={stream_monitor.is_external}")

            # If it's an external stream, return immediately (no Device needed)
            if stream_monitor.is_external:
                logger.info(f"✅ [FIND_STREAM_MONITOR] Returning external stream_monitor: {stream_monitor.code}")
                return stream_monitor

            # For regular streams, verify Device exists
            if not stream_monitor.drone:
                logger.error(f"❌ [FIND_STREAM_MONITOR] Stream monitor {stream_monitor_id} exists but has no drone/device")
                raise Exception(f"Stream monitor {stream_monitor_id} exists but has no drone/device")

            logger.info(f"✅ [FIND_STREAM_MONITOR] Returning regular stream_monitor with device: {stream_monitor.drone.name}")
            return stream_monitor

        # Stream monitor doesn't exist, need to create it
        logger.info(f"🔍 [FIND_STREAM_MONITOR] Stream monitor not found, checking if external stream...")

        # Check if this is an external stream (code starts with "external_")
        is_external = stream_monitor_id.startswith("external_")

        if is_external:
            # External streams must be created via add_external_stream_monitor API first
            error_msg = f"External stream monitor with code {stream_monitor_id} not found. Please create it first via add_external_stream_monitor API."
            logger.error(f"❌ [FIND_STREAM_MONITOR] {error_msg}")
            raise Exception(error_msg)

        # For regular streams, find Device and create StreamMonitor
        logger.info(f"🔍 [FIND_STREAM_MONITOR] Creating new regular stream monitor, looking for Device...")

        device = Device._base_manager.filter(unit_id=stream_monitor_id).first()
        if not device:
            error_msg = f"Device with unit_id {stream_monitor_id} not found"
            logger.error(f"❌ [FIND_STREAM_MONITOR] {error_msg}")
            raise Exception(error_msg)

        user = CoreUser._base_manager.filter(userprofilelink__group_id=group_id).first()
        if not user:
            error_msg = f"User with group_id {group_id} not found"
            logger.error(f"❌ [FIND_STREAM_MONITOR] {error_msg}")
            raise Exception(error_msg)

        # Create new stream monitor
        logger.info(f"🔍 [FIND_STREAM_MONITOR] Creating new stream monitor for device: {device.name}")
        stream_monitor = StreamMonitor.objects.create(
            code=stream_monitor_id,
            name=device.name,
            ip_source="192.169.1.100",
            is_active=True,
            is_visualize=True,
            is_external=False,
            drone=device,
            order=0,
            group_id=group_id,
            created_by=user,
            modified_by=user,
        )
        logger.info(f"✅ [FIND_STREAM_MONITOR] Created new stream_monitor: id={stream_monitor.id}, device={device.name}")
        return stream_monitor

    @classmethod
    async def start_record(cls, stream_monitor_id: str, ai_model__code: str, enable_detection: bool = True, group_id: Optional[str] = None, from_fe = True):
        try:
            logger.info(f"🔍 [START_RECORD] ===== ENTRY POINT =====")
            logger.info(f"🔍 [START_RECORD] stream_monitor_id: {stream_monitor_id}, ai_model__code: {ai_model__code}, enable_detection: {enable_detection}")
            # Get stream monitor to determine RTSP URL
            stream_monitor = await sync_to_async(cls.find_stream_monitor)(stream_monitor_id, group_id)
            if not stream_monitor:
                error_msg = f"Stream monitor with id {stream_monitor_id} not found"
                logger.error(f"❌ [START_RECORD] {error_msg}")
                raise Exception(error_msg)
            logger.info(f"✅ [START_RECORD] Found stream monitor: {stream_monitor.code}, is_external: {stream_monitor.is_external}")
            rtsp_url = f"{settings.RTSP_URL}/stream/{stream_monitor_id}"
            # Only switch to AI stream when we actually enable detection/analysis
            if enable_detection and ai_model__code and from_fe:
                rtsp_url = f"{settings.RTSP_URL}/stream/ai_{stream_monitor_id}"
            if stream_monitor.is_external:
                rtsp_url = stream_monitor.ip_source

            logger.info(f"🔍 [START_RECORD] RTSP URL: {rtsp_url}")
            # Create database record first to get record_id
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            record_code = f"{timestamp}{stream_monitor_id}"
            if enable_detection and ai_model__code and from_fe:
                record_code = f"{timestamp}{stream_monitor_id}_{ai_model__code}"

            logger.info(f"🔍 [START_RECORD] Creating record instance with code: {record_code}")
            record_instance = await sync_to_async(StreamMonitorRecord._base_manager.create)(
                stream_id=stream_monitor_id,
                code=record_code,
                status='running'
            )
            logger.info(f"✅ [START_RECORD] Record instance created with ID: {record_instance.id}")

            # Call external start_record API
            logger.info(f"🔍 [START_RECORD] About to call AI_GRPC service...")
            try:
                # Ensure URL has protocol
                ai_grpc_url = settings.AI_GRPC_URL.strip()
                if not ai_grpc_url.startswith(('http://', 'https://')):
                    ai_grpc_url = f"http://{ai_grpc_url}"

                record_url = f"{ai_grpc_url}/start_record"
                headers = {
                    'Content-Type': 'application/json',
                    'accept': 'application/json'
                }
                body_data = {
                    'rtsp_url': rtsp_url,
                    'bucket_name': settings.MINIO_STORAGE_MEDIA_BUCKET_NAME,
                    'record_id': str(record_instance.id),
                    'stream_id': stream_monitor_id
                }

                # Debug logging
                logger.info(f"🔍 [START_RECORD] Calling AI_GRPC_URL: {record_url}")
                logger.info(f"🔍 [START_RECORD] Request body: {json.dumps(body_data, indent=2)}")
                logger.info(f"🔍 [START_RECORD] Stream monitor ID: {stream_monitor_id}, Record ID: {record_instance.id}")

                response = requests.post(
                    record_url,
                    json=body_data,
                    headers=headers,
                    timeout=30,
                    verify=False
                )

                # Log response details
                logger.info(f"🔍 [START_RECORD] Response status code: {response.status_code}")
                logger.info(f"🔍 [START_RECORD] Response headers: {dict(response.headers)}")

                try:
                    result = response.json()
                    logger.info(f"🔍 [START_RECORD] Response body: {json.dumps(result, indent=2)}")
                except ValueError:
                    error_msg = f"Invalid JSON response from AI_GRPC service: {response.text}"
                    logger.error(f"❌ [START_RECORD] Response is not JSON. Response text: {response.text}")
                    raise Exception(error_msg)

                if result.get('status') != 'success':
                    error_msg = result.get('message', 'Unknown error')
                    logger.error(f"❌ [START_RECORD] Failed to start recording: {error_msg}")
                    logger.error(f"❌ [START_RECORD] Full response: {json.dumps(result, indent=2)}")
                    await sync_to_async(record_instance.delete)()
                    return None, None

                logger.info(f"✅ [START_RECORD] Recording started successfully with record_id: {record_instance.id}")

            except requests.exceptions.RequestException as record_err:
                logger.error(f"❌ [START_RECORD] Request exception: {type(record_err).__name__}: {str(record_err)}")
                logger.error(f"❌ [START_RECORD] URL attempted: {record_url}")
                await sync_to_async(record_instance.delete)()
                return None, None
            except Exception as record_err:
                logger.error(f"❌ [START_RECORD] Unexpected error: {type(record_err).__name__}: {str(record_err)}")
                await sync_to_async(record_instance.delete)()
                return None, None

            try:
                detection_url = f"{settings.AI_GRPC_URL}/start_detect"
                url_callback = f"{settings.BACKEND_URL}/api/media-data/detect-callback"
                headers = {
                    'Content-Type': 'application/json',
                    'accept': 'application/json'
                }
                body_data = {
                    'detection_id': str(record_instance.id),
                    'detection_type': ai_model__code if ai_model__code else "person",
                    'input_rtsp': stream_monitor.ip_source if stream_monitor.is_external else f"{settings.RTSP_URL}/stream/{stream_monitor_id}",
                    'url_callback': url_callback,
                    'stream_id': stream_monitor_id
                }
                logger.info(f"🔍 [START_DETECT] Detection URL: {detection_url} with body: {body_data} {enable_detection} {url_callback}")
                if enable_detection:
                    response = requests.post(
                        detection_url,
                        json=body_data,
                        headers=headers,
                        timeout=5,
                        verify=False
                    )
                    detection_result = response.json()
                    logger.info(f"🔍 [START_DETECT] Detection result: {detection_result}")
            except Exception as detect_err:
                logger.warning(f"Detection API call failed: {detect_err}")

            logger.info(f"✅ [START_RECORD] Returning record_id={record_instance.id}, record_code={record_code}")
            return record_instance.id, record_code

        except Exception as e:
            logger.error(f"❌ [START_RECORD] Error: {type(e).__name__}: {str(e)}")
            return None, None

    @classmethod
    async def _stop_detection_background(
        cls,
        record_id: str,
        stream_monitor_id: str,
        object_path: str,
        user: CoreUser,
        profile_drone_id: Optional[int] = None,
        group_id: Optional[str] = None,
        **_kwargs,
    ):
        """Background task to call stop detection API and create video analysis."""
        from surveillance.services.video_analysis_service import VideoAnalysisService
        from surveillance.services.surveillance_profile_media_service import SurveillanceProfileMediaService

        try:
            detection_url = f"{settings.AI_GRPC_URL}/stop_detect"
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
            body_data = {
                'detection_id': str(record_id)
            }

            logger.info(f"🔍 [STOP_DETECTION] Calling stop_detect API: record_id={record_id}, stream_monitor_id={stream_monitor_id}")

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

            # Check response status code
            if response.status_code != 200:
                error_msg = f"stop_detect API returned status {response.status_code}: {response.text}"
                logger.error(f"❌ [STOP_DETECTION] {error_msg}")
                raise Exception(error_msg)

            try:
                detection_result = response.json()
            except ValueError as json_err:
                error_msg = f"Failed to parse JSON response: {json_err}, response text: {response.text[:500]}"
                logger.error(f"❌ [STOP_DETECTION] {error_msg}")
                raise Exception(error_msg)

            logger.info(f"🔍 [STOP_DETECTION] Detection result received: {detection_result}")

            # Extract detections data
            detections_data = detection_result.get('detections', [])
            if not isinstance(detections_data, list):
                logger.warning(f"⚠️ [STOP_DETECTION] detections is not a list, got {type(detections_data)}, using empty list")
                detections_data = []

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_path = minio_client.save_json(
                detections_data,
                stream_monitor_id,
                f"{timestamp}_{stream_monitor_id}.json"
            )

            # Validate analysis_path was created
            if not analysis_path:
                error_msg = f"Failed to save analysis JSON to MinIO: save_json returned None (storage may be unavailable)"
                logger.error(f"❌ [STOP_DETECTION] {error_msg}")
                raise Exception(error_msg)

            logger.info(f"✅ [STOP_DETECTION] Analysis path created successfully: {analysis_path}")

            # Validate object_path before creating VideoAnalysis
            if not object_path:
                error_msg = f"object_path is None or empty, cannot create VideoAnalysis for stream_monitor_id={stream_monitor_id}, record_id={record_id}"
                logger.error(f"❌ [STOP_DETECTION] {error_msg}")
                raise Exception(error_msg)

            logger.info(f"🔍 [STOP_DETECTION] object_path={object_path}, analysis_path={analysis_path}, group_id={group_id}")

            # Create video analysis with object_path and analysis_path
            try:
                if profile_drone_id:
                    logger.info(f"🎬 [STOP_DETECTION] Creating VideoAnalysis with profile_drone_id={profile_drone_id}, group_id={group_id}")
                    await VideoAnalysisService.create_video_analysis_from_profile_drone(
                        int(profile_drone_id),
                        stream_monitor_id,
                        object_path,
                        analysis_path,
                        user,
                        group_id=group_id,
                    )
                else:
                    logger.info(f"🎬 [STOP_DETECTION] Creating VideoAnalysis without profile_drone, group_id={group_id}")
                    video_analysis = await VideoAnalysisService.create_video_analysis_from_stream_monitor(
                        stream_monitor_id, object_path, analysis_path, user, group_id
                    )
                    if not video_analysis:
                        logger.warning(f"⚠️ [STOP_DETECTION] VideoAnalysisService returned None for stream_monitor_id={stream_monitor_id}")
                logger.info(f"✅ [STOP_DETECTION] VideoAnalysis created successfully: stream_monitor_id={stream_monitor_id}, object_path={object_path}, analysis_path={analysis_path}")
            except Exception as va_exc:
                logger.exception(f"❌ [STOP_DETECTION] Failed to create VideoAnalysis: {type(va_exc).__name__}: {str(va_exc)}")
                # Continue to persist analysis_path even if VideoAnalysis creation fails
                raise  # Re-raise to ensure error is logged

            # Persist analysis_path (and optionally video_path) onto the in-progress assignment.
            try:
                # IMPORTANT: This function uses Django ORM (sync), so it must run in a thread when called
                # from this async background task; otherwise Django raises SynchronousOnlyOperation.
                if profile_drone_id:
                    await sync_to_async(
                        SurveillanceProfileMediaService.save_detection_result_for_profile_drone,
                        thread_sensitive=True,
                    )(
                        int(profile_drone_id),
                        object_path=object_path,
                        analysis_path=analysis_path,
                    )
                else:
                    await sync_to_async(
                        SurveillanceProfileMediaService.save_detection_result_for_stream_monitor,
                        thread_sensitive=True,
                    )(
                        stream_monitor_id,
                        object_path=object_path,
                        analysis_path=analysis_path,
                    )
                logger.info(f"✅ [STOP_DETECTION] Media paths persisted successfully: stream_monitor_id={stream_monitor_id}, analysis_path={analysis_path}")
            except Exception as persist_exc:
                logger.error(f"❌ [STOP_DETECTION] Failed to persist media paths for stream {stream_monitor_id}: {type(persist_exc).__name__}: {str(persist_exc)}")
                # Log but don't raise - analysis_path is already created and VideoAnalysis may have been created

        except Exception as detect_err:
            logger.exception(
                f"❌ [STOP_DETECTION] Detection API call failed for record_id={record_id}, stream_monitor_id={stream_monitor_id}: {type(detect_err).__name__}: {str(detect_err)}"
            )
            # Re-raise to ensure the error is logged in the thread wrapper
            raise

    @classmethod
    async def stop_record(
        cls,
        stream_monitor_id: str,
        record_id: str,
        user: CoreUser = None,
        enable_detection: bool = True,
        group_id: Optional[str] = None,
        profile_drone_id: Optional[int] = None,
        **_kwargs,
    ):
        logger.info(f"🛑 [STOP_RECORD] ===== START =====")
        logger.info(f"🛑 [STOP_RECORD] stream_monitor_id={stream_monitor_id}, record_id={record_id}, user={user.username if user else None}, enable_detection={enable_detection}, group_id={group_id}")
        try:
            # Get the record instance to update status
            try:
                logger.info(f"🛑 [STOP_RECORD] Fetching record_instance with id={record_id}")
                record_instance = await sync_to_async(StreamMonitorRecord._base_manager.get)(id=record_id)
                logger.info(f"✅ [STOP_RECORD] Found record_instance: id={record_instance.id}, status={record_instance.status}")
            except StreamMonitorRecord.DoesNotExist:
                logger.error(f"❌ [STOP_RECORD] StreamMonitorRecord with id {record_id} not found")
                return None
            except Exception as e:
                logger.error(f"❌ [STOP_RECORD] Error fetching record_instance: {type(e).__name__}: {str(e)}")
                raise

            # Call external stop_record API
            record_url = f"{settings.AI_GRPC_URL}/stop_record"
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
            logger.info(f"🛑 [STOP_RECORD] Preparing to call external API: {record_url}")

            # Get group_code using sync_to_async to avoid SynchronousOnlyOperation error
            def get_group_code_from_user():
                if user and hasattr(user, 'userprofilelink') and user.userprofilelink and user.userprofilelink.group:
                    return user.userprofilelink.group.code
                return "default"

            def get_group_code_from_id(group_id):
                try:
                    return UserGroup._base_manager.get(id=group_id).code
                except UserGroup.DoesNotExist:
                    return None

            logger.info(f"🛑 [STOP_RECORD] Getting group_code: group_id={group_id}")
            group_code = None
            try:
                if group_id:
                    logger.info(f"🛑 [STOP_RECORD] Getting group_code from group_id={group_id}")
                    group_code = await sync_to_async(get_group_code_from_id)(group_id)
                    logger.info(f"✅ [STOP_RECORD] Got group_code from group_id: {group_code}")
                else:
                    logger.info(f"🛑 [STOP_RECORD] Getting group_code from user")
                    group_code = await sync_to_async(get_group_code_from_user)()
                    logger.info(f"✅ [STOP_RECORD] Got group_code from user: {group_code}")
            except Exception as e:
                logger.error(f"❌ [STOP_RECORD] Error getting group_code: {type(e).__name__}: {str(e)}")
                raise

            resolved_group_code = group_code or await sync_to_async(get_group_code_from_user)()
            logger.info(f"✅ [STOP_RECORD] Resolved group_code: {resolved_group_code}")

            body_data = {
                'bucket_name': settings.MINIO_STORAGE_MEDIA_BUCKET_NAME,
                'record_id': str(record_id),
                'stream_id': stream_monitor_id,
                'username': user.username if user else "public",
                'group_code': resolved_group_code
            }
            logger.info(f"🛑 [STOP_RECORD] Request body: {body_data}")

            try:
                logger.info(f"🛑 [STOP_RECORD] Calling external API: POST {record_url}")
                response = requests.post(
                    record_url,
                    json=body_data,
                    headers=headers,
                    timeout=60,
                    verify=False
                )
                logger.info(f"✅ [STOP_RECORD] API response status: {response.status_code}")
                result = response.json()
                logger.info(f"✅ [STOP_RECORD] API response result: {result}")
            except Exception as e:
                logger.error(f"❌ [STOP_RECORD] Error calling external API: {type(e).__name__}: {str(e)}")
                raise

            # Check if stop was successful or processing
            if result.get('status') in ('success', 'processing'):
                object_path = result.get('object_path')
                logger.info(f"✅ [STOP_RECORD] API returned success/processing, object_path={object_path}")

                # Update record status to stopped
                try:
                    logger.info(f"🛑 [STOP_RECORD] Updating record_instance: id={record_id}, status='stopped', object_path={object_path}")
                    record_instance.status = 'stopped'
                    if object_path:
                        record_instance.object_path = object_path
                        logger.info(f"🛑 [STOP_RECORD] Set record_instance.object_path = {object_path}")
                    await sync_to_async(record_instance.save)()
                    logger.info(f"✅ [STOP_RECORD] Successfully saved record_instance: id={record_id}, status='stopped', object_path={record_instance.object_path}")
                except Exception as e:
                    logger.error(f"❌ [STOP_RECORD] Error updating record_instance: {type(e).__name__}: {str(e)}")
                    # Continue even if save fails

                logger.info(f"✅ [STOP_RECORD] Recording stopped successfully for record_id: {record_id}, object_path: {object_path}")

                # Call stop detection API in background (non-blocking) only when detection/analysis was enabled
                if enable_detection:
                    logger.info(f"🛑 [STOP_RECORD] Creating background task for stop_detection")
                    # IMPORTANT:
                    # stop_record is often called via async_to_sync(...) from sync code paths.
                    # In that case, the event loop created by async_to_sync can be closed immediately
                    # after this coroutine returns, cancelling any pending asyncio.create_task(...).
                    # To make stop_detect + analysis persistence reliable, run the background work
                    # in a dedicated thread with its own event loop.
                    # Use daemon=False to ensure the thread completes and analysis_path is created
                    # before the process exits, preventing race conditions with record creation.
                    def _run_stop_detect_background():
                        try:
                            logger.info(f"🛑 [STOP_DETECTION_BG] Starting background thread for stop_detection: record_id={record_id}, stream_monitor_id={stream_monitor_id}, group_id={group_id}")
                            asyncio.run(
                                cls._stop_detection_background(
                                    record_id,
                                    stream_monitor_id,
                                    object_path,
                                    user,
                                    profile_drone_id=profile_drone_id,
                                    group_id=group_id,
                                )
                            )
                            logger.info(f"✅ [STOP_DETECTION_BG] Background thread completed successfully: record_id={record_id}")
                        except Exception as bg_exc:
                            logger.exception(
                                "❌ [STOP_DETECTION_BG] Failed background stop_detect for stream_monitor_id=%s record_id=%s: %s",
                                stream_monitor_id,
                                record_id,
                                bg_exc,
                            )

                    threading.Thread(target=_run_stop_detect_background, daemon=False).start()
                else:
                    # For public endpoints (enable_detection=False), still create VideoAnalysis without detection
                    logger.info(f"🛑 [STOP_RECORD] enable_detection=False, creating VideoAnalysis without detection")
                    try:
                        from surveillance.services.video_analysis_service import VideoAnalysisService
                        logger.info(f"🛑 [STOP_RECORD] Calling VideoAnalysisService.create_video_analysis_from_stream_monitor")
                        video_analysis = await VideoAnalysisService.create_video_analysis_from_stream_monitor(
                            stream_monitor_id, object_path, None, user, group_id
                        )
                        if video_analysis:
                            logger.info(f"✅ [STOP_RECORD] VideoAnalysis created successfully: id={video_analysis.id}")
                        else:
                            logger.warning(f"⚠️ [STOP_RECORD] VideoAnalysisService returned None (stream_monitor not found or no profile)")
                    except Exception as e:
                        logger.exception(f"❌ [STOP_RECORD] Error creating VideoAnalysis: {type(e).__name__}: {str(e)}")
                        # Don't fail the whole operation if VideoAnalysis creation fails

                return object_path
            else:
                error_message = result.get('message', 'Unknown error')
                logger.error(f"❌ [STOP_RECORD] API returned failure status: {result.get('status')}, message: {error_message}")
                try:
                    record_instance.status = 'error'
                    await sync_to_async(record_instance.save)()
                except Exception as e:
                    logger.error(f"❌ [STOP_RECORD] Error updating record_instance status to 'error': {type(e).__name__}: {str(e)}")
                return None

        except Exception as record_err:
            logger.exception(f"❌ [STOP_RECORD] Exception in stop_record: {type(record_err).__name__}: {str(record_err)}")
            try:
                if 'record_instance' in locals():
                    record_instance.status = 'error'
                    await sync_to_async(record_instance.save)()
            except Exception as save_err:
                logger.error(f"❌ [STOP_RECORD] Error saving record_instance after exception: {type(save_err).__name__}: {str(save_err)}")
            return None

    @classmethod
    async def pause_record(cls, stream_monitor_id: str, record_id: str, ai_model__code: str):
        try:
            # Get the record instance to update status
            try:
                record_instance = await sync_to_async(StreamMonitorRecord.objects.get)(id=record_id)
            except StreamMonitorRecord.DoesNotExist:
                logger.error(f"StreamMonitorRecord with id {record_id} not found")
                return None

            # Call external pause_record API
            try:
                record_url = f"{settings.AI_GRPC_URL}/pause_record"
                headers = {
                    'Content-Type': 'application/json',
                    'accept': 'application/json'
                }
                body_data = {
                    'bucket_name': settings.MINIO_STORAGE_MEDIA_BUCKET_NAME,
                    'record_id': str(record_id),
                    'stream_id': stream_monitor_id
                }

                response = requests.post(
                    record_url,
                    json=body_data,
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                result = response.json()

                if result.get('status') == 'success':
                    # Update record status to paused
                    record_instance.status = 'paused'
                    await sync_to_async(record_instance.save)()
                    logger.info(f"⏸️ Recording paused for record_id: {record_id}")
                    return True
                else:
                    logger.error(f"Failed to pause recording: {result.get('message')}")
                    record_instance.status = 'error'
                    await sync_to_async(record_instance.save)()
                    return None

            except Exception as record_err:
                logger.error(f"Pause record API call failed: {record_err}")
                record_instance.status = 'error'
                await sync_to_async(record_instance.save)()
                return None

        except Exception as e:
            logger.error(f"Error pausing record: {str(e)}")
            return None

    @classmethod
    async def resume_record(cls, stream_monitor_id: str, record_id: str, ai_model__code: str):
        try:
            # Get the record instance to update status
            try:
                record_instance = await sync_to_async(StreamMonitorRecord._base_manager.get)(id=record_id)
            except StreamMonitorRecord.DoesNotExist:
                logger.error(f"StreamMonitorRecord with id {record_id} not found")
                return None

            # Call external resume_record API
            try:
                record_url = f"{settings.AI_GRPC_URL}/resume_record"
                headers = {
                    'Content-Type': 'application/json',
                    'accept': 'application/json'
                }
                body_data = {
                    'bucket_name': settings.MINIO_STORAGE_MEDIA_BUCKET_NAME,
                    'record_id': str(record_id),
                    'stream_id': stream_monitor_id
                }

                response = requests.post(
                    record_url,
                    json=body_data,
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                result = response.json()

                if result.get('status') == 'success':
                    # Update record status to running
                    record_instance.status = 'running'
                    await sync_to_async(record_instance.save)()
                    logger.info(f"▶️ Recording resumed for record_id: {record_id}")
                    return True
                else:
                    logger.error(f"Failed to resume recording: {result.get('message')}")
                    record_instance.status = 'error'
                    await sync_to_async(record_instance.save)()
                    return None

            except Exception as record_err:
                logger.error(f"Resume record API call failed: {record_err}")
                record_instance.status = 'error'
                await sync_to_async(record_instance.save)()
                return None
        except Exception as e:
            logger.error(f"Error resuming record: {str(e)}")
            return None

    @classmethod
    def start_ai_dual_stream_optimized(cls, stream_monitor_id: str, stream_id: str, is_external: bool = False, detection_type: str = "person") -> Dict[str, Any]:
        """
        Start AI dual stream with optimized processing by calling external API.

        Args:
            stream_monitor_id: ID of the stream monitor

        Returns:
            dict: Process information and status
        """
        try:
            # Get AI stream URLs
            url_result = cls.get_ai_stream_url(stream_monitor_id)
            if not url_result.get('success'):
                return url_result

            input_url = url_result.get('input_url')
            if is_external:
                monitor = StreamMonitor.objects.get(code=stream_monitor_id)
                input_url = monitor.ip_source
            output_url = url_result.get('output_url')

            if not input_url or not output_url:
                return {
                    'success': False,
                    'error': 'Missing input_url or output_url',
                    'stream_monitor_id': stream_monitor_id
                }

            # Construct API endpoint URL
            # AI_GRPC_URL might be just "host:port" or full URL
            # Force HTTP protocol to avoid SSL errors
            api_base_url = settings.AI_GRPC_URL.strip()
            # # Remove any existing protocol
            # if api_base_url.startswith('https://'):
            #     api_base_url = api_base_url.replace('https://', '', 1)
            # elif api_base_url.startswith('http://'):
            #     api_base_url = api_base_url.replace('http://', '', 1)
            # # Always use HTTP (not HTTPS) for this API
            # api_base_url = f"http://{api_base_url}"

            api_url = f"{api_base_url}/start_stream"

            # Prepare request payload
            payload = {
                "input_url": input_url,
                "output_url": output_url,
                "stream_id": stream_id,
                "detection_type": detection_type,
            }
            print('payload: ', payload)
            # Make API call
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }

            logger.info(f"🚀 Calling AI stream API: {api_url} with payload: {payload}")
            logger.debug(f"🔍 Original AI_GRPC_URL setting: {settings.AI_GRPC_URL}, Final URL: {api_url}")
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=10,
                verify=False
            )
            print('response: ', response.text)
            # Check response
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    result = {
                        'success': True,
                        'stream_monitor_id': stream_monitor_id,
                        'input_url': input_url,
                        'output_url': output_url,
                        'api_response': response_data
                    }
                    logger.info(f"✅ AI dual stream started successfully: {result}")
                    return result
                except ValueError:
                    # Response is not JSON
                    result = {
                        'success': True,
                        'stream_monitor_id': stream_monitor_id,
                        'input_url': input_url,
                        'output_url': output_url,
                        'api_response': response.text
                    }
                    logger.info(f"✅ AI dual stream started successfully (non-JSON response): {result}")
                    return result
            else:
                error_msg = f"API returned status {response.status_code}: {response.text}"
                logger.error(f"❌ Failed to start AI dual stream: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'stream_monitor_id': stream_monitor_id,
                    'status_code': response.status_code
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error starting AI dual stream: {str(e)}")
            return {
                'success': False,
                'error': f"Request error: {str(e)}",
                'stream_monitor_id': stream_monitor_id
            }
        except Exception as e:
            logger.error(f"❌ Error starting AI dual stream optimized: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stream_monitor_id': stream_monitor_id
            }

    @classmethod
    def stop_ai_dual_stream_optimized(cls, stream_id: str, stream_monitor_id: str) -> Dict[str, Any]:
        """
        Stop AI dual stream by calling external API.

        Args:
            stream_monitor_id: ID of the stream monitor (used as stream_id)

        Returns:
            dict: Stop status information
        """
        try:
            # Construct API endpoint URL
            # AI_GRPC_URL might be just "host:port" or full URL
            # Force HTTP protocol to avoid SSL errors
            api_base_url = settings.AI_GRPC_URL.strip()
            # # Remove any existing protocol
            # if api_base_url.startswith('https://'):
            #     api_base_url = api_base_url.replace('https://', '', 1)
            # elif api_base_url.startswith('http://'):
            #     api_base_url = api_base_url.replace('http://', '', 1)
            # # Always use HTTP (not HTTPS) for this API
            # api_base_url = f"http://{api_base_url}"

            api_url = f"{api_base_url}/stop_stream"

            # Prepare request payload
            # Using stream_monitor_id as stream_id, but could also use output_url identifier
            payload = {
                "stream_id": stream_id
            }

            # Make API call
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }

            logger.info(f"🛑 Calling AI stream stop API: {api_url} with payload: {payload}")
            logger.debug(f"🔍 Original AI_GRPC_URL setting: {settings.AI_GRPC_URL}, Final URL: {api_url}")
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=10,
                verify=False
            )

            # Check response
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    result = {
                        'success': True,
                        'stream_monitor_id': stream_monitor_id,
                        'status': 'stopped',
                        'api_response': response_data
                    }
                    logger.info(f"✅ AI dual stream stopped successfully")
                    return result
                except ValueError:
                    # Response is not JSON
                    result = {
                        'success': True,
                        'stream_monitor_id': stream_monitor_id,
                        'status': 'stopped',
                        'api_response': response.text
                    }
                    logger.info(f"✅ AI dual stream stopped successfully (non-JSON response)")
                    return result
            else:
                error_msg = f"API returned status {response.status_code}: {response.text}"
                logger.error(f"❌ Failed to stop AI dual stream: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'stream_monitor_id': stream_monitor_id,
                    'status_code': response.status_code
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error stopping AI dual stream: {str(e)}")
            return {
                'success': False,
                'error': f"Request error: {str(e)}",
                'stream_monitor_id': stream_monitor_id
            }
        except Exception as e:
            logger.error(f"❌ Error stopping AI dual stream optimized: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stream_monitor_id': stream_monitor_id
            }

    @classmethod
    async def start_record_optimize(cls, stream_monitor_id: str, ai_model_code: str = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Start video recording optimized (no pause/resume support).

        Args:
            stream_monitor_id: ID of the stream monitor
            ai_model_code: AI model code (e.g., "fire_smoke") - if provided, records from AI stream

        Returns:
            Tuple[Optional[str], Optional[str]]: (record_code, rtsp_url) or (None, None) on failure
        """
        try:
            import uuid
            from datetime import datetime

            # Generate record code
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = uuid.uuid4().hex[:6]
            record_code = f"{timestamp}{stream_monitor_id}_{unique_id}"
            if ai_model_code and ai_model_code != "":
                record_code = f"{timestamp}{stream_monitor_id}_{ai_model_code}_{unique_id}"

            # Determine RTSP URL
            rtsp_url = f"{settings.RTSP_URL}/stream/{stream_monitor_id}"
            if ai_model_code and ai_model_code != "":
                rtsp_url = f"{settings.RTSP_URL}/stream/ai_{stream_monitor_id}"

            # Create record directory
            record_dir = os.path.join(settings.RECORD_DIR, record_code)
            os.makedirs(record_dir, exist_ok=True)

            # Store recording info in a simple way (we'll use a dict to track active recordings)
            if not hasattr(cls, '_active_recordings_optimize'):
                cls._active_recordings_optimize = {}

            cls._active_recordings_optimize[stream_monitor_id] = {
                'record_code': record_code,
                'rtsp_url': rtsp_url,
                'record_dir': record_dir,
                'output_path': os.path.join(record_dir, f"{stream_monitor_id}_{int(time.time())}.mp4"),
                'ffmpeg_process': None,
                'started_at': time.time()
            }

            # Start ffmpeg recording process
            output_path = cls._active_recordings_optimize[stream_monitor_id]['output_path']
            cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", rtsp_url,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "28",  # higher = lower quality
                "-vf", "scale=1280:-1",  # reduce resolution (ex: 720p)
                "-an",
                "-f", "mp4",
                "-movflags", "+faststart+frag_keyframe+empty_moov",
                "-frag_duration", "1000000",
                "-reset_timestamps", "1",
                "-y",
                str(output_path),
            ]

            logger.info(f"Starting optimized recording for stream {stream_monitor_id}, output: {output_path}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            # Create subprocess with stdin available for graceful shutdown
            ffmpeg_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            cls._active_recordings_optimize[stream_monitor_id]['ffmpeg_process'] = ffmpeg_process

            logger.info(f"Started optimized recording for stream {stream_monitor_id}, record_code: {record_code}")
            return record_code, rtsp_url

        except Exception as e:
            logger.error(f"Error starting optimized recording for stream {stream_monitor_id}: {str(e)}")
            return None, None

    @classmethod
    async def stop_record_optimize(cls, stream_monitor_id: str, record_code: str) -> Optional[str]:
        """
        Stop video recording optimized and save to MinIO.

        Args:
            stream_monitor_id: ID of the stream monitor
            record_code: Record code returned from start_record_optimize

        Returns:
            Optional[str]: MinIO object path or None on failure
        """
        try:
            if not hasattr(cls, '_active_recordings_optimize') or stream_monitor_id not in cls._active_recordings_optimize:
                logger.warning(f"No active recording found for stream {stream_monitor_id}")
                return None

            recording_info = cls._active_recordings_optimize[stream_monitor_id]
            ffmpeg_process = recording_info.get('ffmpeg_process')
            output_path = recording_info.get('output_path')
            record_dir = recording_info.get('record_dir')

            # Stop ffmpeg process gracefully
            if ffmpeg_process:
                try:
                    if ffmpeg_process.returncode is None:
                        # Try to send 'q' to stdin to quit gracefully
                        try:
                            if ffmpeg_process.stdin:
                                ffmpeg_process.stdin.write(b'q\n')
                                await ffmpeg_process.stdin.drain()
                                ffmpeg_process.stdin.close()
                                logger.debug("Sent 'q' to ffmpeg stdin for graceful shutdown")
                        except Exception as stdin_err:
                            logger.debug(f"Could not send 'q' to stdin: {stdin_err}")

                        # Wait for process to finish gracefully
                        try:
                            await asyncio.wait_for(ffmpeg_process.wait(), timeout=5.0)
                            logger.debug("FFmpeg process finished gracefully")
                        except asyncio.TimeoutError:
                            # If graceful quit didn't work, terminate
                            logger.warning(f"FFmpeg didn't quit gracefully, terminating...")
                            ffmpeg_process.terminate()
                            try:
                                await asyncio.wait_for(ffmpeg_process.wait(), timeout=3.0)
                                logger.debug("FFmpeg process terminated")
                            except asyncio.TimeoutError:
                                # Last resort: kill
                                logger.warning(f"FFmpeg didn't terminate, killing...")
                                ffmpeg_process.kill()
                                await asyncio.wait_for(ffmpeg_process.wait(), timeout=2.0)
                                logger.debug("FFmpeg process killed")

                        # Check for errors in stderr
                        if ffmpeg_process.stderr:
                            try:
                                stderr_output = await asyncio.wait_for(ffmpeg_process.stderr.read(), timeout=1.0)
                                if stderr_output:
                                    stderr_text = stderr_output.decode('utf-8', errors='ignore')
                                    logger.debug(f"FFmpeg stderr (last 500 chars): {stderr_text[-500:]}")
                                    # Log errors if any
                                    if 'error' in stderr_text.lower() or 'failed' in stderr_text.lower():
                                        logger.warning(f"FFmpeg reported errors: {stderr_text[-1000:]}")
                            except Exception as stderr_err:
                                logger.debug(f"Could not read stderr: {stderr_err}")

                except Exception as e:
                    logger.warning(f"Error stopping ffmpeg process: {e}")

            # Wait for file to be finalized (longer wait)
            await asyncio.sleep(1.0)

            # Retry checking file existence (sometimes file system needs time)
            max_retries = 5
            file_ready = False
            for i in range(max_retries):
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    if file_size > 0:
                        file_ready = True
                        break
                await asyncio.sleep(0.5)

            if not file_ready:
                logger.warning(f"Output video file does not exist or is empty after {max_retries} retries: {output_path}")
                # Check if directory exists and list files for debugging
                if os.path.exists(record_dir):
                    try:
                        files = os.listdir(record_dir)
                        logger.warning(f"Files in record directory: {files}")
                    except:
                        pass
                # Clean up
                del cls._active_recordings_optimize[stream_monitor_id]
                if os.path.exists(record_dir):
                    try:
                        shutil.rmtree(record_dir)
                    except:
                        pass
                return None

            # Read video file and save to MinIO with retry logic
            logger.info(f"Reading video file from {output_path}")
            file_size = os.path.getsize(output_path)
            logger.info(f"Video file size: {file_size} bytes")

            def read_and_save():
                with open(output_path, 'rb') as f:
                    video_data = io.BytesIO(f.read())
                return minio_client.save_video(video_data, stream_monitor_id, record_code)

            # Retry upload to MinIO up to 3 times
            loop = asyncio.get_event_loop()
            object_path = None
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Attempting to upload video to MinIO (attempt {attempt}/{max_retries})")
                    object_path = await loop.run_in_executor(None, read_and_save)
                    if object_path:
                        logger.info(f"Successfully uploaded video to MinIO on attempt {attempt}")
                        break
                    else:
                        logger.warning(f"Upload attempt {attempt} returned None")
                except Exception as e:
                    logger.warning(f"Upload attempt {attempt} failed with error: {str(e)}")

                # Sleep 1 second before retry (except on last attempt)
                if attempt < max_retries:
                    await asyncio.sleep(1.0)

            # Clean up - only remove directory if upload to MinIO was successful
            del cls._active_recordings_optimize[stream_monitor_id]
            if object_path:
                # Only remove temporary directory if video was successfully uploaded to MinIO
                if os.path.exists(record_dir):
                    try:
                        shutil.rmtree(record_dir)
                        logger.info(f"Removed temporary record directory {record_dir}")
                    except Exception as e:
                        logger.warning(f"Failed to remove temporary record directory: {e}")
                logger.info(f"Stopped optimized recording for stream {stream_monitor_id}, saved to {object_path}")
            else:
                # Keep directory if all upload attempts failed
                logger.warning(f"Video recorded but not saved to MinIO for stream {stream_monitor_id} after {max_retries} attempts, keeping temporary directory {record_dir}")

            return object_path

        except Exception as e:
            logger.error(f"Error stopping optimized recording for stream {stream_monitor_id}: {str(e)}")
            # Clean up on error
            if hasattr(cls, '_active_recordings_optimize') and stream_monitor_id in cls._active_recordings_optimize:
                recording_info = cls._active_recordings_optimize[stream_monitor_id]
                record_dir = recording_info.get('record_dir')
                del cls._active_recordings_optimize[stream_monitor_id]
                if record_dir and os.path.exists(record_dir):
                    try:
                        shutil.rmtree(record_dir)
                    except:
                        pass
            return None

    @classmethod
    def add_external_stream_monitor(cls, stream_monitor_in: ExternalStreamMonitorInSchema):
        # push stream in medianMTX server
        external_stream_code = f"external_{uuid.uuid4().hex[:6]}"
        service_url = f"{settings.STREAM_URL}/manage/v3/config/paths/add/{external_stream_code}"
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        data = {
            "source": stream_monitor_in.ip_source,
            "sourceOnDemand": True,
            "sourceProtocol": "tcp"
        }
        response = requests.post(service_url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(f"Failed to push stream in medianMTX server: {response.text}")
        stream_monitor = StreamMonitor.objects.create(
            name=stream_monitor_in.name,
            code=external_stream_code,
            ip_source=stream_monitor_in.ip_source,
            is_external=True,
            is_active=True,
            is_visualize=True,
            external_drone_name=stream_monitor_in.external_drone_name,
            external_operation_name=stream_monitor_in.external_operation_name,
            external_registration_number=stream_monitor_in.external_registration_number,
            external_manufacturer=stream_monitor_in.external_manufacturer,
            external_flight_distance=stream_monitor_in.external_flight_distance,
            external_flight_time=stream_monitor_in.external_flight_time,
            external_flight_altitude=stream_monitor_in.external_flight_altitude,
            external_start_point_x=stream_monitor_in.external_start_point_x,
            external_start_point_y=stream_monitor_in.external_start_point_y,
            external_end_point_x=stream_monitor_in.external_end_point_x,
            external_end_point_y=stream_monitor_in.external_end_point_y,
            external_start_time=stream_monitor_in.external_start_time,
            external_end_time=stream_monitor_in.external_end_time,
            external_remark=stream_monitor_in.remark
        )
        return stream_monitor


    def delete_external_stream_monitor(stream_monitor_id: str):
        # pull stream in medianMTX server
        stream_monitor = StreamMonitor.objects.get(id=stream_monitor_id)
        try:
            path_exist = f"{settings.STREAM_URL}/manage/v3/config/paths/get/{stream_monitor.code}"
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
            response = requests.get(path_exist, headers=headers)
            path_exist = response.json()['exists']
            if not path_exist:
                logger.error(f"Path does not exist: {path_exist}")
        except Exception as e:
            logger.error(f"Error checking path exist: {e}")
            pass
        try:
            service_url = f"{settings.STREAM_URL}/manage/v3/config/paths/delete/{stream_monitor.code}"
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
            response = requests.delete(service_url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error deleting stream monitor: {response.text}")
        except Exception as e:
            logger.error(f"Error deleting stream monitor: {e}")
            pass
        stream_monitor.delete(force_policy=SOFT_DELETE_CASCADE)
        return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
