from core.base import BaseModel, BaseModelWithGroup
from django.db import models
from django.conf import settings

from devices.models import Device

class AIModel(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    code = models.CharField(max_length=255)
    link = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    TRANSLATABLE_FIELDS = ['name', 'description']

# Create your models here.
class StreamMonitor(BaseModelWithGroup):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    drone = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, blank=True)
    ip_source = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_visualize = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    is_external = models.BooleanField(default=False)
    external_drone_name = models.CharField(max_length=255, null=True, blank=True)
    external_operation_name = models.CharField(max_length=255, null=True, blank=True)
    external_registration_number = models.CharField(max_length=255, null=True, blank=True)
    external_manufacturer = models.CharField(max_length=255, null=True, blank=True)
    external_flight_distance = models.FloatField(null=True, blank=True)
    external_flight_time = models.IntegerField(null=True, blank=True)
    external_flight_altitude = models.FloatField(null=True, blank=True)
    external_start_point_x = models.CharField(max_length=255, null=True, blank=True)
    external_start_point_y = models.CharField(max_length=255, null=True, blank=True)
    external_end_point_x = models.CharField(max_length=255, null=True, blank=True)
    external_end_point_y = models.CharField(max_length=255, null=True, blank=True)
    external_start_time = models.DateTimeField(null=True, blank=True)
    external_end_time = models.DateTimeField(null=True, blank=True)
    external_remark = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name']

    def __str__(self):
        return self.name

class StreamMonitorAIModel(BaseModel):
    stream_monitor = models.ForeignKey(StreamMonitor, on_delete=models.CASCADE)
    ai_model = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    in_use = models.BooleanField(default=True)
    ai_stream_url = models.CharField(max_length=255, null=True, blank=True)
    def __str__(self):
        return self.stream_monitor.name


class DrawingSession(BaseModel):
    """Model for managing drawing sessions"""
    name = models.CharField(max_length=255)
    stream_monitor = models.ForeignKey(StreamMonitor, on_delete=models.CASCADE, related_name='drawing_sessions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.stream_monitor.name}"


class DrawingElement(models.Model):
    """Model for storing individual drawing elements"""
    ELEMENT_TYPES = [
        ('line', 'Line'),
        ('rectangle', 'Rectangle'),
        ('circle', 'Circle'),
        ('polygon', 'Polygon'),
        ('text', 'Text'),
        ('arrow', 'Arrow'),
    ]

    session = models.ForeignKey(DrawingSession, on_delete=models.CASCADE, related_name='elements')
    element_type = models.CharField(max_length=20, choices=ELEMENT_TYPES)
    data = models.JSONField()  # Store drawing data (coordinates, style, etc.)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.element_type} - {self.session.name}"


class DrawingParticipant(models.Model):
    """Model for tracking users participating in drawing sessions"""
    session = models.ForeignKey(DrawingSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=True)

    class Meta:
        unique_together = ['session', 'user']

    def __str__(self):
        return f"{self.user.username} - {self.session.name}"

class StreamMonitorRecord(models.Model):
    stream_id = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    status = models.CharField(max_length=255, default='running')
    object_path = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    # Auto-stop functionality fields
    auto_stop_task_id = models.CharField(max_length=255, null=True, blank=True, help_text="Celery task ID for auto-stop")

    def __str__(self):
        return str(self.id)


class DetectionEvent(BaseModelWithGroup):
    """AI 탐지 이벤트 — W2-1.

    계약: docs/contracts/detection-event.md (W6-2 에서 고정)
    이 스키마는 파이프라인 구현이 바뀌어도 동일하다. R2 의 DeepStream 전환이
    W2(이벤트 센터)·W3(대시보드)·W1(리포트)를 깨뜨리지 않게 하는 경계다.

    ⚠ BaseModelWithGroup 상속 필수 (group 격리).
      backend/tests/test_tenant_isolation.py 의 MODELS 레지스트리에 등록되어 있다.
      신규 앱을 만들지 않고 stream_monitors 안에 둔다.
    """

    class EventType(models.TextChoices):
        PERSON = "person", "사람"
        VEHICLE = "vehicle", "차량"
        FIRE = "fire", "화재"
        SMOKE = "smoke", "연기"
        INTRUSION = "intrusion", "침입"
        SOS = "sos", "구조요청"

    class Severity(models.TextChoices):
        INFO = "info", "정보"
        WARNING = "warning", "경고"
        CRITICAL = "critical", "위험"   # ISA-101: 빨강은 이 등급 전용

    class Status(models.TextChoices):
        NEW = "new", "신규"
        CONFIRMED = "confirmed", "확인"
        REJECTED = "rejected", "기각"
        CLOSED = "closed", "종료"

    stream_monitor = models.ForeignKey(
        StreamMonitor, on_delete=models.CASCADE, related_name="detection_events"
    )
    ai_model = models.ForeignKey(
        AIModel, on_delete=models.SET_NULL, null=True, blank=True
    )

    event_type = models.CharField(max_length=32, choices=EventType.choices, db_index=True)
    severity = models.CharField(
        max_length=16, choices=Severity.choices, default=Severity.INFO, db_index=True
    )
    occurred_at = models.DateTimeField(db_index=True)
    # 중복 억제(W2-2): 같은 stream+type 이 N초 내 재발하면 이 값만 갱신한다
    last_seen_at = models.DateTimeField(null=True, blank=True)

    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    alt = models.FloatField(null=True, blank=True)

    confidence = models.FloatField(null=True, blank=True, help_text="0.0 ~ 1.0")
    # 정규화 좌표 {"x","y","w","h"} 0.0~1.0. 픽셀 좌표를 쓰지 않는다 —
    # 파이프라인 교체 시 입력 해상도가 달라진다.
    bbox = models.JSONField(null=True, blank=True)
    track_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    snapshot_path = models.CharField(max_length=512, help_text="MinIO object path")
    clip_path = models.CharField(max_length=512, null=True, blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NEW, db_index=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_detection_events",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.CharField(max_length=255, null=True, blank=True)

    # 리포트 연결용 (W1-1 MissionReportService 가 임무별 이벤트를 모은다)
    mission = models.ForeignKey(
        "surveillance.SurveyMission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detection_events",
    )

    class Meta:
        # 화면 정렬(W2-3)은 최신순이되 critical+new 를 최상단 고정한다.
        # 기본 정렬은 최신순만 제공하고 고정은 뷰에서 처리한다.
        ordering = ["-occurred_at"]
        indexes = [
            # 이벤트 센터 타임라인: 스트림별 최신순
            models.Index(fields=["stream_monitor", "-occurred_at"]),
            # 미처리 우선 표출
            models.Index(fields=["status", "severity", "-occurred_at"]),
            # 중복 억제 조회(W2-2): 같은 스트림+타입의 최근 이벤트
            models.Index(fields=["stream_monitor", "event_type", "-occurred_at"]),
            # 임무 리포트 집계(W1-1)
            models.Index(fields=["mission", "-occurred_at"]),
        ]

    def __str__(self):
        return f"{self.event_type}@{self.stream_monitor_id} {self.occurred_at:%Y-%m-%d %H:%M:%S}"
