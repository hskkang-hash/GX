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


class NotificationRule(BaseModelWithGroup):
    """K2 알림 커널 — **등급 × 역할 → 누가 받는가** (DA-04 §2 K2 · DA2-21 (1)).

    왜 새 앱을 만들지 않았나
        `DetectionEvent`(W2-1)와 같은 이유다. 신규 앱은 `INSTALLED_APPS` 를 건드리고,
        그것은 설정 변경이며 되돌리기가 더 크다(4원칙 ②·④). 이 두 표는 이벤트와
        같은 수명·같은 테넌트 경계를 갖는다 — 이벤트가 사는 앱에 둔다.
        ※ 전용 앱으로 옮길지는 **P-K2-1 로 적재**했다. 옮기는 것은 마이그레이션 하나이고,
          지금 나누면 K2 착수 자체가 설정 변경 승인 대기가 된다.

    ⚠ BaseModelWithGroup 상속 필수 (group 격리).
      수신 규칙이 테넌트를 넘으면 **남의 재난 알림이 우리에게 온다** — 격리 실패 중에서도
      가장 눈에 띄는 종류다.

    ★ 규칙은 **역할**을 가리키고 사람을 가리키지 않는다.
      사람을 직접 넣으면 인사이동마다 규칙을 고쳐야 하고, 고치지 않은 규칙은
      **퇴사자에게 재난 알림을 보내는 상태**로 남는다.
    """

    #: 어느 등급에서 발동하는가. `DetectionEvent.Severity` 와 **같은 열거를 쓴다** —
    #: 등급을 두 벌로 두면 규칙이 가리키는 등급과 이벤트의 등급이 갈린다.
    severity = models.CharField(
        max_length=16, choices=DetectionEvent.Severity.choices, db_index=True
    )
    role = models.ForeignKey(
        "role.Role", on_delete=models.CASCADE, related_name="notification_rules"
    )
    #: 구역 라벨. **분류 체계가 아니라 라벨이다** — 이 저장소에 zone 모델이 없다(실측).
    #: 비어 있으면 모든 구역에 적용된다. 체계는 P-K2-2 로 적재했다 (추정 금지 · D-280).
    zone = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    #: 발송 채널 목록 (`["email"]`). 업체 미정이므로 **어댑터 자리만 비워 둔다**(D4-1).
    #: 문자열 하나가 아니라 목록인 이유: 같은 등급을 메일과 SMS 로 동시에 보내는 것이
    #: F-10 의 기본 요구이고, 하나로 두면 규칙을 채널 수만큼 복제하게 된다.
    channels = models.JSONField(default=list)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["severity", "id"]
        indexes = [
            # 발동 조회: 등급 + 활성 (구역은 선택이라 뒤에 온다)
            models.Index(fields=["severity", "is_active"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - 관리 화면 표시용
        return f"{self.severity}/{self.role_id}/{self.zone or '*'}"


class DeliveryRecord(BaseModelWithGroup):
    """K2 발송 이력 — **AC 판정의 유일한 근거** (DA-04 §2 K2 · DA2-21 (3)).

    DA-04: *"`occurred_at → sent_at` 이 F-10 의 30초 AC 를 재는 두 점이다."*
    그래서 두 점이 **한 행에서 읽혀야** 한다 — 이벤트를 따라가 시각을 찾아야 하면
    그 조회가 곧 AC 측정의 비용이 되고, 비용이 큰 측정은 안 하게 된다.

    ★ 이 표가 곧 K4 보고서의 "조치 이력" 행이다 (DA-04 K2 이중 AC).
      알림용·보고서용 두 벌로 적재하지 않는다 — 두 벌이면 보고서와 알림이 다른 말을 한다.

    ★ 실패도 **행으로 남는다.** 실패를 남기지 않으면 "보낸 적 없음"과 "보내려다 실패"가
      같은 상태(행 없음)가 되고, 그것이 D-290 이 금지한 모양이다.
    """

    class Channel(models.TextChoices):
        EMAIL = "email", "이메일"
        SMS = "sms", "SMS"
        PUSH = "push", "앱 푸시"
        WEBHOOK = "webhook", "Webhook"

    event = models.ForeignKey(
        DetectionEvent, on_delete=models.CASCADE, related_name="deliveries"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="detection_deliveries",
    )
    #: 수신 주소의 **사본**. 사람이 지워져도(SET_NULL) 어디로 보냈는지는 남아야 한다 —
    #: 감사에서 "누구에게 갔나"에 답하지 못하면 이력이 아니다.
    recipient_address = models.CharField(max_length=255, blank=True, default="")
    channel = models.CharField(max_length=16, choices=Channel.choices, db_index=True)

    #: 이벤트 발생 시각의 **사본**. F-10 의 두 점 중 하나 — 조인 없이 재게 한다.
    occurred_at = models.DateTimeField(db_index=True)
    #: 발송을 마친 시각. 실패면 `None` 이다 — 실패에 시각을 넣으면 30초 AC 가
    #: **실패한 발송으로도 달성된다.**
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)

    succeeded = models.BooleanField(default=False, db_index=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-occurred_at", "id"]
        indexes = [
            # F-10 판정: 이벤트별 발송 이력
            models.Index(fields=["event", "-occurred_at"]),
            # 5분 알림 억제 조회 (K2.suppress)
            models.Index(fields=["succeeded", "-occurred_at"]),
        ]

    @property
    def latency_seconds(self) -> float | None:
        """`occurred_at → sent_at`. **F-10 의 30초를 재는 두 점** (DA-04).

        실패면 `None` 이다 — 0 이 아니다. 실패를 0초로 세면 평균이 좋아진다.
        """
        if self.sent_at is None:
            return None
        return (self.sent_at - self.occurred_at).total_seconds()
