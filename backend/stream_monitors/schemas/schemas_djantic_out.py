from django.conf import settings
from django.db.models import Value, CharField
import requests
from stream_monitors.models import AIModel, StreamMonitor, StreamMonitorAIModel, DrawingSession, DrawingElement, DrawingParticipant
from stream_monitors.utils.stream_utils import get_stream_url
from common.external_http import AVAILABLE, UNAVAILABLE, fetch_json
from core.common.schema_utils import DynamicSchema
from ninja import Schema
from typing import Optional, List
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class StreamMonitorOutSchema(DynamicSchema):
    class Meta:
        model = StreamMonitor
        model_fields = ['id', 'name', 'code', 'drone', 'ip_source', 'is_active', 'is_visualize', 'stream_url', 'is_use_webrtc', 'rtsp_url', 'stream_link']

    @classmethod
    def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
        result = super().from_queryset(queryset_or_instance, many=many, **kwargs)
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        # W0-17 ① — 스트리밍 서버 상태조회는 **부수 정보**다.
        # 예전에는 이 호출이 실패하면 예외가 그대로 올라가 목록 API 가 통째로 500 이었다.
        # 드론 목록은 스트리밍 서버와 무관하게 보여야 한다. 이제 실패는 값으로 온다.
        stream_url = f"{settings.STREAM_URL}/manage/v3/paths/list"
        response_data, streams_ok = fetch_json(
            stream_url, headers=headers, verify=False, default={}
        )
        stream_items = [item['name'] for item in (response_data or {}).get('items', [])]
        stream_status = AVAILABLE if streams_ok else UNAVAILABLE
        if many:
            # For queryset (many=True), process each item in the result
            for item in result:
                if 'id' in item:
                    # Get the specific instance and its related ai_models
                    try:
                        instance = StreamMonitor.objects.prefetch_related('streammonitoraimodel_set__ai_model').get(id=item['id'])
                        ai_models_queryset = instance.streammonitoraimodel_set.filter(in_use=True).annotate(stream_path=Value(f"stream/{instance.code}", output_field=CharField()),
                        ai_model__code=Value(instance.streammonitoraimodel_set.first().ai_model.code if instance.streammonitoraimodel_set.first() else None, output_field=CharField()))
                        item['ai_models'] = StreamMonitorAIModelOutSchema.from_queryset(
                            ai_models_queryset, many=True
                        )
                        is_ai_model = True if StreamMonitorAIModel.objects.filter(stream_monitor=instance, in_use=True).exists() else False
                        # item['stream_url'] = get_stream_url(instance, is_ai_model=is_ai_model)
                        # item['stream_url'] = ""
                        # item['rtsp_url'] = f"{settings.RTSP_PATH_AI if is_ai_model else settings.RTSP_PATH}/{instance.code}"
                        item['ip_source'] = f"{settings.RTSP_PATH_AI if is_ai_model else settings.RTSP_PATH}/{instance.code}"
                        item['is_use_webrtc'] = settings.IS_USE_WEBRTC
                        item['is_external'] = instance.is_external
                        # 스트리밍 서버가 죽어도 목록은 나온다. 다만 그 사실을 숨기지 않는다.
                        item['stream_status'] = stream_status
                        check_stream = f"stream/{instance.code}"
                        if check_stream:
                            item['rtsp_url'] = f"{settings.RTSP_URL}/{check_stream}"
                            item['stream_path'] = check_stream
                            item['stream_url'] = f"{settings.STREAM_URL}/hls/{check_stream}/index.m3u8"
                        else:
                            item['rtsp_url'] = ""
                            item['stream_path'] = ""
                            item['stream_url'] = ""
                        if instance.is_external:
                            item['rtsp_url'] = instance.ip_source
                            item['stream_path'] = instance.code
                            item['stream_url'] = instance.ip_source
                    except StreamMonitor.DoesNotExist:
                        item['ai_models'] = []
        else:
            # For single instance (many=False)
            if hasattr(queryset_or_instance, 'streammonitoraimodel_set'):
                ai_models_queryset = queryset_or_instance.streammonitoraimodel_set.all().annotate(stream_path=Value(f"stream/{queryset_or_instance.code}", output_field=CharField()))
                result['ai_models'] = StreamMonitorAIModelOutSchema.from_queryset(
                    ai_models_queryset, many=True
                )
            else:
                result['ai_models'] = []
            # 단건도 같은 규약을 따른다 — 목록만 상태를 알고 상세는 모르면
            # 화면이 서로 다른 이야기를 하게 된다.
            result['stream_status'] = stream_status

        return result

class StreamMonitorAIModelOutSchema(DynamicSchema):
    stream_path: Optional[str] = None

    class Meta:
        model = StreamMonitorAIModel
        model_fields = ['id', 'stream_monitor', 'ai_model', 'is_active', 'ai_stream_url', 'in_use']

    @classmethod
    def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
        result = super().from_queryset(queryset_or_instance, many=many, **kwargs)
        for item in result:
            if 'ai_stream_url' in item:
                item['ai_stream_url'] = f"{item['ai_stream_url']}"
        return result


class UserInfoOutSchema(Schema):
    id: int
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class DrawingSessionOutSchema(DynamicSchema):
    created_by: UserInfoOutSchema
    participant_count: Optional[int] = None

    class Meta:
        model = DrawingSession
        model_fields = ['id', 'name', 'stream_monitor', 'created_at', 'updated_at', 'is_active']


class DrawingElementOutSchema(DynamicSchema):
    created_by: UserInfoOutSchema

    class Meta:
        model = DrawingElement
        model_fields = ['id', 'element_type', 'data', 'created_at', 'updated_at']


class DrawingParticipantOutSchema(DynamicSchema):
    user: UserInfoOutSchema

    class Meta:
        model = DrawingParticipant
        model_fields = ['joined_at', 'last_activity', 'is_online']


class DrawingSessionDetailOutSchema(Schema):
    session: DrawingSessionOutSchema
    elements: List[DrawingElementOutSchema]
    participants: List[DrawingParticipantOutSchema]

class AIModelOutSchema(DynamicSchema):
    class Meta:
        model = AIModel
        model_fields = ['id', 'name', 'code', 'description', 'created_on', 'updated_on']

class CaptureResponse(BaseModel):
    """Response model for capture operations."""
    stream_id: str
    object_path: Optional[str] = None
    message: str
    success: bool = True
