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

    # ── OPS-15 맥박 (2026-09-04 · 차선 Q) ────────────────────────────────
    #
    # 왜 칸 하나가 필요한가 — **「조용함」과 「죽음」은 다른 사실이다**
    # ---------------------------------------------------------------
    # D-415 의 `cameras_silent_24h` 는 「이벤트가 안 온 카메라」를 센다. 그런데 아무 일도
    # 안 일어난 카메라와 케이블이 끊긴 카메라는 그 수에서 **같은 모양**이다
    # (온보딩 U1 #3 에 그렇게 적혀 있다 · 실측). 이 칸이 그 둘을 가른다:
    # 프레임은 사건이 없어도 온다. 프레임이 끊긴 것은 **장비의 사실**이다.
    #
    # ★ `null` 은 **「아직 한 장도 안 왔다」**이지 **「죽었다」가 아니다** (D-290).
    #   판정기는 이 값을 두절로 세지 않는다 — 세면 시드 직후의 새 카메라가 전부
    #   군집 두절이 되고, 그러면 이 신호는 태어나자마자 소음이 된다.
    #
    # ⚠ **이 칸은 등급을 만들지 않는다.** 두절 판정과 군집 규칙은
    #   `stream_monitors/services/camera_pulse.py` 한 곳에 있다 — 판단은 한 곳에서만(D-212).
    last_frame_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="마지막 프레임 수신 시각(맥박). null 은 '아직 안 왔다'이지 '죽었다'가 "
                  "아니다. 군집 두절 판정은 camera_pulse.py 가 한다 (OPS-15)",
    )

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

    # ─────────────────────────────────────────────────────────────────────
    # 설치 주소 — **밖에서 사 오려던 것을 우리는 이미 알고 있었다** (D-330)
    # ─────────────────────────────────────────────────────────────────────
    #
    # 종전 설계는 이벤트 좌표 → 외부 역지오코딩 API → 주소 였다. 외부 의존 · 타임아웃 ·
    # 저하 운전 · 비용, 그리고 **자원이 없어서 잠김**(FX-5).
    # 그런데 **카메라는 고정 설치물이다.** 설치할 때 주소를 안다 — 적어 두지 않았을 뿐이다.
    #
    # ★ 결과가 더 좋다. 역지오코딩은 「서울시 …로 12」만 준다.
    #   우리는 **「정문 (서울시 …로 12)」**를 준다 — 새벽 당직자에게 이 차이가 결정적이다.
    #
    # 계층: L3 Platform. 카메라 속성이므로 카메라와 같은 층·같은 앱이다 (Zone 과 같은 판단 · D-299).
    class AddressSource(models.TextChoices):
        #: ★ 기본값. **"아직 안 적음"** 이지 "주소가 없는 카메라" 가 아니다 (D-290).
        #:   이 값이면 알림은 종전대로 좌표 1줄로 나간다 — **발송을 지연시키지 않는다.**
        UNSET = "unset", "미입력"
        #: 사람이 적었다. 지금 있는 유일한 출처다. 팝업 API 로 채워도 출처는 사람이다(D-331).
        MANUAL = "manual", "수기 입력"

    #: 도로명주소. 팝업 API(D-331)로 채우면 정규화된 값이 들어온다 —
    #: 손으로 치면 오타가 나고, 오타 난 주소는 **알림에 그대로 나가 사람을 엉뚱한 곳으로 보낸다.**
    install_address = models.CharField(max_length=255, null=True, blank=True)
    #: "정문" · "3층 복도" — 현장 사람이 쓰는 표현. 도로명주소가 답하지 못하는 것을 답한다.
    install_address_detail = models.CharField(max_length=255, null=True, blank=True)
    address_source = models.CharField(
        max_length=16, choices=AddressSource.choices,
        default=AddressSource.UNSET, db_index=True,
        help_text="unset = 아직 안 적음. 알림은 좌표 1줄로 나가고 지연되지 않는다 (D-330)",
    )

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
        #: ★ D-294 로 신설. F-02(침수·수위)는 계약 M 기능이고, 전용 타입이 **없던 것은
        #:   설계 선택이 아니라 누락**이었다. 기존 타입에 실어 보내면 그 타입의
        #:   오탐률 분모가 오염되고 **아무도 그 사실을 모른다**.
        #:   계약 문서(docs/contracts/detection-event.md §열거값)와 W2-3 색 규칙을
        #:   같은 커밋에서 함께 고쳤다 — 문서와 코드가 갈리면 어느 쪽이 계약인지 모른다.
        FLOOD = "flood", "침수"
        #: ★ P-20 ③ 으로 신설 (2026-09-22). **탐지가 아니라 시스템의 상태**다.
        #:   죽은 카메라·저장 용량은 `scripts/ops_monitor.py` 안에만 있었고
        #:   (온보딩 U1 #3 · U2 #19 · U5 #15 — 셋 다 「화면 없는 신호」), 운영 감시는
        #:   크론이 읽는 자리이지 사람이 보는 화면이 아니다. 같은 신호를 이벤트로 내면
        #:   W1 「시스템」 프리셋에서 **새 화면 없이** U5 가 본다.
        #:
        #:   ⚠ 이 둘은 AI 라벨에서 오지 않는다 — `LABEL_TO_EVENT_TYPE` 에 넣지 않는다.
        #:     넣으면 AI 가 「카메라가 죽었다」를 검출했다고 말할 수 있게 된다.
        #:   ⚠ 오탐률(U1)의 분모는 `event_type` 별로 갈리므로(D-294), 이 둘이 섞여
        #:     탐지 유형의 오탐률을 흐리지 않는다 — 그것이 전용 타입을 만든 이유다.
        CAMERA_DOWN = "camera_down", "카메라 무응답"
        STORAGE_HIGH = "storage_high", "저장 용량 임계"
        #: ★ OPS-15 로 신설 (2026-09-04 · 차선 Q). **`camera_down` 과 다른 화면에 간다.**
        #:
        #:   한 대가 죽은 것은 운영의 일이다 — 사람이 가서 본다(시스템 이벤트).
        #:   같은 구역 여러 대가 **동시에** 죽은 것은 그 구역에 무슨 일이 생겼다는 뜻이다
        #:   (재난 징후). 하천이 넘치면 하천변 카메라가 함께 죽고, 그것을 알기 위해
        #:   SDN 링크 상태(F-08)가 필요하지 않다 — 우리 수집기가 이미 안다.
        #:
        #:   ⚠ 정직 고지: 이것은 **F-08 을 구현으로 바꾸지 않는다.** F-08 은 SDN 링크
        #:     상태를 말하고 그 절은 손 밖에 그대로 있다. 이것은 새 절(OPS-15)이고,
        #:     F-08 이 열리면 같은 규칙의 **두 번째 입력**이 된다 — 규칙은 안 바뀌고
        #:     입력만 는다.
        #:   ⚠ AI 라벨에서 오지 않는다 — `LABEL_TO_EVENT_TYPE` 에 넣지 않는다.
        CAMERA_CLUSTER_DOWN = "camera_cluster_down", "카메라 군집 두절"

    class Severity(models.TextChoices):
        INFO = "info", "정보"
        WARNING = "warning", "경고"
        CRITICAL = "critical", "위험"   # ISA-101: 빨강은 이 등급 전용

    class Status(models.TextChoices):
        NEW = "new", "신규"
        CONFIRMED = "confirmed", "확인"
        REJECTED = "rejected", "기각"
        CLOSED = "closed", "종료"

    #: ★ D-399 — **대응 진행 축.** `status` 와 **다른 축이다**. 섞지 않는다.
    #:
    #: 왜 세 번째 칸인가. 지시서는 「이벤트를 4값으로 바꾸라」고 했고 실측하니
    #: `status` 는 **이미 4값**이었다. 그런데 두 4값은 **묻는 것이 다르다**:
    #:
    #:     status         「이 탐지가 진짜인가」   신규 → 확인/기각 → 종료
    #:     response_state 「사람이 어디까지 했나」 발생 → 확인 → 조치중 → 종결
    #:
    #: 지시서의 값을 `status` 에 밀어 넣으면 **판정과 대응이 한 칸에 섞인다.**
    #: 그것은 D-293 이 `status` 와 `verdict` 를 가른 것과 **같은 실수**다 —
    #: 그때 섞여 있던 탓에 종료가 쌓일수록 오탐률이 저절로 좋아졌다.
    #: 한 칸에 두 뜻을 넣으면 마지막에 쓴 사람이 앞사람의 뜻을 덮는다.
    #:
    #: ⚠ 이 칸은 **who·when·reason 을 들지 않는다.** 전이 기록은 `logger.AuditLogs` 에
    #:   `common/audit_writer.py` 로 남긴다 — 새 표를 만들지 않는다(D-333).
    #:   현재 값만 여기 있고, **어떻게 왔는지는 감사가 안다.**
    class ResponseState(models.TextChoices):
        OCCURRED = "occurred", "발생"
        ACKNOWLEDGED = "acknowledged", "접수 확인"
        IN_PROGRESS = "in_progress", "조치중"
        CLOSED = "closed", "종결"

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
    #: ★ D-399 대응 진행 축. 전이 규칙과 감사는 `apps/dsm/response_flow.py` 한 곳에 있다 —
    #:   이 칸을 직접 대입하는 코드를 만들지 마라. 규칙이 두 벌이 되면 반드시 어긋난다(D-212).
    response_state = models.CharField(
        max_length=16, choices=ResponseState.choices,
        default=ResponseState.OCCURRED, db_index=True,
        help_text="대응 진행(발생→접수확인→조치중→종결). status(탐지 판정)와 다른 축이다 (D-399)",
    )
    #: ★ 사람의 판정 그 자체 — **종료되어도 지워지지 않는다** (D-293).
    #:
    #: 왜 `status` 와 따로 두나. `status` 는 수명주기(new→confirmed/rejected→closed)이고
    #: 마지막 칸이 앞 칸을 **덮는다**. 그래서 판정된 이벤트가 종료되는 순간 오탐률의
    #: 분모·분자에서 조용히 빠졌다 — 종료가 쌓일수록 오탐률이 **저절로 좋아지는** 구조다.
    #: 개선된 것이 아니라 나쁜 데이터가 사라진 것이고, D-293 이 그것을 금지했다.
    #:
    #: 집계 표를 새로 만드는 것이 아니다(DA-04 K6 "별도 집계 테이블 금지"). 같은 행에
    #: **덮이지 않는 칸 하나**를 둘 뿐이고, 오탐률은 이제 이 칸 하나에서 나온다 —
    #: 집계 경로는 여전히 하나다.
    #:
    #: null 은 "아직 아무도 판정하지 않았다" 이고, `status="closed"` 와 무관하다.
    #: 열거는 `Status` 전체가 아니라 **판정 둘뿐**이다. `new`·`closed` 는 판정이 아니라
    #: 수명주기 칸이고, 그것이 여기 들어오면 다시 두 뜻이 한 칸에 섞인다.
    VERDICT_CHOICES = [
        (Status.CONFIRMED, Status.CONFIRMED.label),
        (Status.REJECTED, Status.REJECTED.label),
    ]
    verdict = models.CharField(
        max_length=16, choices=VERDICT_CHOICES, null=True, blank=True, db_index=True,
        help_text="사람의 판정(confirmed/rejected). 종료해도 덮이지 않는다 (D-293)",
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

    # ── FX-5 주소 자동 변환 (D-298 예외 승인분) ──────────────────────────
    #
    # 왜 좌표 옆에 주소를 두나 — **새벽 당직자에게 이 차이가 크다.**
    # 지금 알림에는 좌표만 나가고, 받는 사람은 지도를 따로 연다. 도로명 주소가 함께
    # 나가면 그 한 단계가 사라진다. F-10 알림 본문과 F-11 보고서 위치란이 쓴다.
    #
    # ★ 주소는 **보조 정보다.** 주소 조회가 죽어도 이벤트는 정상 생성된다(저하 운전).
    #   이 두 필드가 null 이거나 disabled 인 것은 실패가 아니다.
    address = models.CharField(
        max_length=512, null=True, blank=True,
        help_text="도로명 주소 (FX-5). 조회 전·불가 시 null — 빈 문자열과 구별한다",
    )

    class AddressStatus(models.TextChoices):
        #: 아직 조회하지 않았다. **재시도 대상이다.**
        PENDING = "pending", "조회 대기"
        #: 조회해서 주소를 받았다. `address` 에 값이 있다.
        RESOLVED = "resolved", "조회 완료"
        #: 조회했는데 실패했다. **재시도 대상이지만 알림에는 "주소 확인 불가"로 나간다.**
        FAILED = "failed", "조회 실패"
        #: 조회 대상이 아니다 — 어댑터가 꽂혀 있지 않거나 좌표가 없다. **재시도하지 않는다.**
        DISABLED = "disabled", "조회 안 함"

    #: ★ D-290 적용 — **"아직 조회 안 함"과 "조회했는데 실패"를 같은 값으로 두지 않는다.**
    #:
    #:   한 칸으로 두면(예: address 가 null 인지로 판정) 둘이 구별되지 않고, 구별되지
    #:   않으면 재시도 대상 목록이 만들어지지 않는다 — 실패한 것들이 영원히 pending 인
    #:   척하거나, 아직 안 한 것들이 실패로 세어진다. 둘 다 조용한 유실이다.
    #:
    #:   'failed'   → 알림 본문은 "주소 확인 불가(좌표: …)" 로 나간다. 사람이 좌표를 본다.
    #:   'pending'  → 재시도 대상.
    #:   'disabled' → 재시도하지 않는다. **두 사유가 여기 모인다**(어댑터 미설정 · 좌표 없음).
    #:                둘을 갈라야 할 이유가 생기면 그것은 결정 사안이지 조용한 변경이 아니다.
    address_status = models.CharField(
        max_length=16, choices=AddressStatus.choices,
        default=AddressStatus.PENDING, db_index=True,
        help_text="주소 조회 상태 (FX-5 · D-290). pending 과 failed 를 합치지 않는다",
    )

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
            # ★ 오탐률 코호트 집계(D-293): 발생 기간 × 판정. `status` 가 아니라
            #   `verdict` 로 센다 — 종료가 판정을 덮지 않는 칸이 이것이기 때문이다.
            models.Index(fields=["verdict", "-occurred_at"]),
            # ★ 타입별 분리 집계(D-294): 오탐률이 타입별로 갈라져야 침수가 화재의
            #   분모를 오염시키지 않는다.
            models.Index(fields=["event_type", "verdict", "-occurred_at"]),
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


class Zone(BaseModel):
    """구역 — **카메라 묶음(지금) + 폴리곤 자리(계약 F-03, 비워 둠)** (D-299).

    왜 두 가지를 한 모델에 두나
    ---------------------------
    계약 F-03 의 AC 는 *"지정 위험구역(**폴리곤**) 내 사람·차량 진입"* 이다. 최종적으로
    폴리곤이 필요하다 — 카메라 묶음은 계약보다 약하다. 그러나 지금 폴리곤 전체를 만드는
    것은 크고(GIS 의존·구역 편집 화면), 안 만들면 E2E-2 의 3단계가 계속 잠긴다.

    그래서 **같은 모델에 둘 다 자리를 두고, 지금은 카메라 묶음만 채운다.**
    나중에 폴리곤을 채우는 것이 재작업이 아니라 **빈칸 채우기**가 되게 하는 것이 요점이다.
    다른 모델을 새로 만들면 그때 `Zone` 이 둘이 되고, 둘이 되면 어느 쪽이 계약인지 모른다
    (D-227 이 만든 상태가 그것이었다).

    ★ 추측을 계약으로 만들지 않는다 — **선언된 미완성**으로 만든다
    -------------------------------------------------------------
    `geometry` 를 지금 채우면 그 필드 모양이 곧 F-03 의 계약이 된다(D-280).
    그래서 비워 두되 **비어 있다는 사실을 모델이 말하게** 했다: `geometry_status` 가
    `not_implemented` 인 동안 판정 함수는 조용히 False 를 돌려주지 않고
    `NotImplementedError` 로 멈춘다(D-284). 없는 것은 없다고 말한다.

    계층 — **L3 Platform** (D-299)
    ------------------------------
    구역은 재난안전 전용 개념이 아니다(산업안전·시설물 App 도 쓴다). 카메라를 묶는 일이므로
    카메라와 같은 층·같은 앱에 둔다 — `DetectionEvent` 를 stream_monitors 안에 둔 것과
    같은 이유이고, 신규 앱을 만들지 않는다.

    기저는 `BaseModel` 이다 — 실행 중인 dj-core 가 `group` FK 를 자동으로 준다(D-292 실측).
    `BaseModelWithGroup` 은 DEPRECATED 이고 신규 상속이 게이트로 막혀 있다(D-295).
    """

    class Kind(models.TextChoices):
        #: 지금 채우는 것. "같은 구역" = 같은 묶음에 속한 카메라.
        CAMERA_GROUP = "camera_group", "카메라 묶음"
        #: 계약 F-03 의 최종형. 자리만 있고 판정은 미구현이다.
        POLYGON = "polygon", "폴리곤"

    class GeometryStatus(models.TextChoices):
        #: ★ 기본값. **"아직 안 만들었다"** 이지 "폴리곤이 없는 구역" 이 아니다.
        NOT_IMPLEMENTED = "not_implemented", "미구현"
        #: 폴리곤 판정이 실제로 서면 이 값이 된다. 이 값을 가진 행이 하나라도 생기면
        #: `ZONE_POLYGON_READY` 가 True 여야 한다 — 아니면 게이트가 exit 1 (D-299).
        READY = "ready", "가동"

    name = models.CharField(max_length=255)
    kind = models.CharField(
        max_length=16, choices=Kind.choices, default=Kind.CAMERA_GROUP, db_index=True
    )
    #: 지금 채우는 것 — 이 구역에 속한 카메라들.
    #: M2M 인 이유: 카메라 하나가 두 구역에 걸칠 수 있다(하천 합류부·교차로).
    #: FK 로 두면 그 현장을 표현할 수 없고, 표현할 수 없는 것은 조용히 한쪽으로 몰린다.
    cameras = models.ManyToManyField(
        StreamMonitor, blank=True, related_name="zones",
        help_text="이 구역에 속한 카메라. kind='camera_group' 일 때 판정의 근거다",
    )
    #: 계약 F-03 의 폴리곤이 들어올 자리. **지금은 비운다.**
    #: 좌표 표현(GeoJSON 인지 좌표쌍 배열인지)·좌표계(WGS84/TM)는 아직 정해지지 않았고,
    #: 여기서 정하면 그 선택이 곧 계약이 된다 — 정해지는 자리는 F-03 설계이지 이 필드가 아니다.
    geometry = models.JSONField(
        null=True, blank=True,
        help_text="F-03 폴리곤. 표현·좌표계 미확정이므로 비워 둔다 (D-280)",
    )
    geometry_status = models.CharField(
        max_length=20, choices=GeometryStatus.choices,
        default=GeometryStatus.NOT_IMPLEMENTED, db_index=True,
        help_text="폴리곤 판정이 실제로 도는가. ready 가 하나라도 있으면 "
                  "ZONE_POLYGON_READY 가 True 여야 한다 (D-299)",
    )
    is_active = models.BooleanField(default=True)

    TRANSLATABLE_FIELDS = ["name"]

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            # "이 구역이 지금 판정에 쓰이는가" — 활성 구역을 종류별로 훑는다
            models.Index(fields=["kind", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name}({self.kind})"


class EventClip(BaseModel):
    """이벤트 ↔ 영상 **구간 참조** (D-306). 새 인코딩 0건 — "어디를 보라"만 적는다.

    왜 `clip_path` 가 아니라 새 표인가
    ----------------------------------
    `DetectionEvent.clip_path` 는 **정의 1건 · 읽기 2곳 · 쓰기 0곳**이었다. 읽는 코드가
    있으니 살아 있어 보였고 시험은 읽기만 지나가며 초록이었다 — D-304 가 착시 ⑥
    (스키마의 착시)으로 이름 붙인 모양이다. 그 칸을 그대로 채우면 **한 칸이 두 뜻**을
    갖는다: "추출된 파일 경로" 인지 "원본 녹화의 어느 구간" 인지.

    구간 참조는 셋(객체 · 시작 · 길이)이 함께여야 뜻이 있으므로 칸 하나로는 표현되지 않는다.
    그래서 표를 나누고, 옛 칸은 쓰지 않는다는 사실을
    `scripts/verify_dead_fields.py` 의 `DECLARED_UNWIRED` 에 사유와 함께 등재했다.

    ★ 무엇을 만들지 않았나 (D-300 부작위)
    -------------------------------------
    **새 파일을 만들지 않는다.** 이 표는 이미 MinIO 에 있는 녹화 객체(`/start-record` 의
    산출물)를 가리킬 뿐이고, 실제 구간 추출·트랜스코딩은
    `stream_monitors.services.clips.CLIP_EXTRACTION_READY` 가 잠근다.

    ★ 쓰기 지점은 **이벤트 생성 경로 안 한 곳**이다 (D-306)
    ------------------------------------------------------
    밖에서 나중에 채우는 배치를 만들지 않는다 — 그것이 `clip_path` 가 죽은 필드가 된
    경로다. 이벤트가 나면 참조도 함께 난다. 녹화가 없었으면 행이 없는 것이 아니라
    `unavailable` + 사유로 **행이 남는다**: "없다" 와 "아직 안 봤다" 를 구별하기 위해서다(D-290).
    """

    class ClipStatus(models.TextChoices):
        #: 그 시각에 녹화가 없었다. **사유가 함께 남는다.** 재시도 대상이 아니다.
        UNAVAILABLE = "unavailable", "녹화 없음"
        #: 원본 녹화의 어느 구간인지 안다. **지금 만드는 것이 여기까지다.**
        REFERENCED = "referenced", "구간 참조"
        #: 그 구간이 실제로 잘려 나왔다. 이 값을 쓰려면 CLIP_EXTRACTION_READY 가 True 여야 한다.
        EXTRACTED = "extracted", "구간 추출"

    event = models.ForeignKey(
        DetectionEvent, on_delete=models.CASCADE, related_name="clips")
    #: 이미 MinIO 에 있는 녹화 객체. **우리가 만든 것이 아니다.**
    object_key = models.CharField(max_length=512, blank=True, default="")
    #: 녹화 시작점에서 몇 초 뒤부터인가 (이벤트 시각 − PRE_ROLL, 0 미만이면 0).
    start_offset = models.FloatField(null=True, blank=True)
    #: 몇 초짜리 구간인가 (PRE_ROLL + POST_ROLL).
    duration = models.FloatField(null=True, blank=True)
    clip_status = models.CharField(
        max_length=16, choices=ClipStatus.choices,
        default=ClipStatus.UNAVAILABLE, db_index=True)
    #: ★ `unavailable` 일 때 **반드시 채워진다.** 사유 없는 부재는 "없다" 인지
    #:   "못 찾았다" 인지 구별되지 않고, 구별되지 않는 것은 잊힌다 (D-264 · D-290).
    unavailable_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-id"]
        indexes = [
            # 이벤트 클릭 → 참조 조회 (F-09 의 3초를 재는 경로)
            models.Index(fields=["event", "-id"]),
            # 잠금 대조: extracted 인 행이 있는데 상수가 False 인가
            models.Index(fields=["clip_status"]),
        ]

    def __str__(self):
        return f"clip({self.clip_status})@event{self.event_id}"


# ═══════════════════════════════════════════════════════════════════════════
# K5 표 ① 임계값 — **한 번 만들어 네 절을 갚는 표 둘 중 첫째** (D-325)
# ═══════════════════════════════════════════════════════════════════════════
#
# 정의(항목·기본값·단위·적용 범위)는 코드에 있다 — `kernels/k5_trust/thresholds.py`.
# **여기 있는 것은 그 정의를 덮어쓴 값과 그 내력**이다. 둘을 나눈 이유:
#
#   · 정의는 개발이 정한다(무엇이 임계값인가·단위가 무엇인가). 커밋으로 바뀐다.
#   · 값은 운영이 정한다(F-12 관리자 설정). 화면으로 바뀐다.
#   한 표에 두면 운영이 정의를 지울 수 있고, 지워진 정의는 코드가 부를 때 터진다.


class ThresholdSetting(BaseModel):
    """임계값 **덮어쓴 값** 한 줄. 정의는 여기 없다 (D-325 표 ①).

    적용 범위 세 층 — **좁은 것이 이긴다**
    --------------------------------------
        camera  특정 카메라(`camera` FK)   ← F-02 「지점별 기준선 설정」이 요구하는 층
        tenant  특정 테넌트(`group` FK)
        global  전역 기본 덮어쓰기(둘 다 null)

    ★ 지금 채우는 것은 **전역 기본뿐**이다(D-325). tenant·camera 는 **자리이지 데이터가
      아니다** — 행이 하나도 없고, 없는 것이 정상이다. Zone 의 폴리곤 자리와 같은 대칭이다.
      자리를 지금 만드는 이유: 나중에 채우는 것이 재작업이 아니라 **빈칸 채우기**가 되게 한다.

    ★ 왜 `scope_ref` 정수 칸이 아니라 `camera` FK 인가
    --------------------------------------------------
    정수 한 칸에 "테넌트 id 또는 카메라 id" 를 담으면 **한 칸이 두 뜻**을 갖는다(D-290).
    그러면 카메라가 지워져도 행이 남고, 남은 행이 다른 카메라의 id 와 겹친다.
    테넌트는 기저(`BaseModel`)가 주는 `group` FK 로, 카메라는 제 이름의 FK 로 적는다.

    ★ 값을 문자열로 두는 이유
    -------------------------
    임계값은 초·분·cm·비율이 섞인다. 숫자 칸 하나로 두면 단위가 값에서 사라지고,
    단위가 사라진 숫자는 **다음 사람이 반드시 잘못 읽는다.** 단위는 정의(코드)에 있고
    여기 있는 것은 그 단위로 읽을 문자열이다. 파싱은 커널이 한다 — 한 곳에서만.

    기저는 `BaseModel` 이다 — 실행 중인 dj-core 가 `group` FK 를 자동으로 준다(D-292 실측).
    `BaseModelWithGroup` 은 DEPRECATED 이고 신규 상속이 게이트로 막혀 있다(D-295).
    """

    class ScopeLevel(models.TextChoices):
        GLOBAL = "global", "전역"
        TENANT = "tenant", "테넌트"
        CAMERA = "camera", "카메라"

    #: `kernels/k5_trust/thresholds.py` 의 정의 키. 정의에 없는 키는 커널이 거부한다 —
    #: 표에 남은 고아 행이 설정 화면에 나타나는 것을 막는다.
    key = models.CharField(max_length=64, db_index=True)
    scope_level = models.CharField(
        max_length=8, choices=ScopeLevel.choices, default=ScopeLevel.GLOBAL, db_index=True)
    #: `scope_level='camera'` 일 때만 채워진다. 카메라가 지워지면 이 행도 함께 간다 —
    #: 없는 지점의 기준선이 남아 있으면 그것이 다음 사고의 근거가 된다.
    camera = models.ForeignKey(
        StreamMonitor, on_delete=models.CASCADE, null=True, blank=True,
        related_name="threshold_settings")
    value = models.CharField(max_length=64)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="threshold_settings")

    class Meta:
        db_table = "k5_threshold_setting"
        constraints = [
            # 같은 자리에 두 값이 있으면 어느 쪽이 유효한지 아무도 모른다.
            # 층마다 따로 거는 이유: NULL 은 서로 다르게 취급되므로 한 제약으로는
            # 전역 행의 중복을 막지 못한다 (Postgres 실측 규칙).
            models.UniqueConstraint(
                fields=["key"], condition=models.Q(scope_level="global"),
                name="uniq_threshold_global"),
            models.UniqueConstraint(
                fields=["key", "group"], condition=models.Q(scope_level="tenant"),
                name="uniq_threshold_tenant"),
            models.UniqueConstraint(
                fields=["key", "camera"], condition=models.Q(scope_level="camera"),
                name="uniq_threshold_camera"),
        ]
        indexes = [models.Index(fields=["key", "scope_level"])]

    def __str__(self):
        return f"{self.key}@{self.scope_level}={self.value}"


class ThresholdChange(BaseModel):
    """**변경 이력** (D-325 표 ① 구조의 다섯째 칸).

    왜 별도 표인가 — `updated_at` 한 칸으로는 "언제 바뀌었나" 만 답한다.
    임계값 사고에서 실제로 필요한 질문은 **"무엇에서 무엇으로, 누가, 왜"** 다.
    그 넷이 없으면 사후에 되돌릴 값을 아무도 모른다.

    ★ 설정 행이 지워져도 이력은 남는다 — 지워진 설정이야말로 사고 조사에서 찾는 것이다
      (D-290: 없는 것과 지워진 것은 다르다). 그래서 카메라 참조는 `SET_NULL` 이고,
      어느 카메라였는지는 `camera_label` 에 문자열로 박아 둔다.
    """

    key = models.CharField(max_length=64, db_index=True)
    scope_level = models.CharField(max_length=8, db_index=True)
    camera = models.ForeignKey(
        StreamMonitor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="threshold_changes")
    #: 카메라가 지워진 뒤에도 "어느 지점이었나" 가 남는다. FK 하나로는 그것이 사라진다.
    camera_label = models.CharField(max_length=255, blank=True, default="")
    #: null = 그전에는 정의 기본값이었다 (덮어쓴 적이 없다).
    old_value = models.CharField(max_length=64, null=True, blank=True)
    #: null = 덮어쓰기를 지웠다 (정의 기본값으로 돌아갔다).
    new_value = models.CharField(max_length=64, null=True, blank=True)
    #: ★ 비울 수 없다. 사유 없는 임계값 변경은 다음 사람에게 사고로만 보인다.
    reason = models.CharField(max_length=255)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="threshold_changes")

    class Meta:
        db_table = "k5_threshold_change"
        ordering = ["-changed_at", "-id"]

    def __str__(self):
        return f"{self.key}: {self.old_value}→{self.new_value}"


# ═══════════════════════════════════════════════════════════════════════════
# 표 ③ 등급규칙 — F-12 「등급규칙」 · F-04 「JSON 무재기동 반영」 (D-368)
# ═══════════════════════════════════════════════════════════════════════════
#
# 표 ①(임계값)과 **같은 모양**이다: 정의는 코드에, 값은 DB 에. 같은 모양으로 두는 이유는
# 하나다 — 운영자가 설정 화면 두 곳에서 다른 규칙을 배우지 않아도 된다.
#
#   정의(코드)  `detection_event_bridge.EVENT_TYPE_TO_SEVERITY` — 잠정 기본값과 그 근거
#   값(DB)      아래 `GradeRule` — 운영이 덮어쓴 값 · 사유 · 누가 · 언제
#
# ★ 「무재기동 반영」이 무엇을 요구하나 (계약 F-04)
# ------------------------------------------------
# 코드의 사전은 **import 시점에 한 번** 읽힌다. 그것만 있으면 규칙을 바꾸려면 재기동해야
# 하고, 재기동은 재난 상황 중에 **하면 안 되는 일**이다. 그래서 판정이 매번 DB 를 본다.
# 그것이 이 표의 존재 이유이고, 그 성질을 `test_grade_rules.py` 가 잰다.


class GradeRule(BaseModel):
    """등급규칙 한 줄 — `event_type` 을 어느 `severity` 로 읽을 것인가 (D-368).

    ★ **행이 없는 것이 정상이다.** 없으면 코드의 잠정 기본값을 쓴다 — 표 ①에서
      "덮어쓴 적이 없다" 를 `null` 로 둔 것과 같은 뜻이다(D-290). 행을 만들어 두고
      기본값을 복사해 넣으면, 코드의 기본값이 바뀌는 날 **복사본만 옛말**이 된다.

    ★ 테넌트별로 다를 수 있다 — 하천 지자체와 산업단지는 같은 `person` 검출을 다르게
      읽는다. 기저(`BaseModel`)의 `group` FK 가 그 층이다.

    ★ 삭제하지 않는다 — 끄는 것은 `is_active=False` 다. 지우면 "그 규칙이 언제까지
      살아 있었나" 가 사라지고, 사고 조사에서 찾는 것이 정확히 그것이다.
    """

    #: `detection_event_bridge.EVENT_TYPE_TO_SEVERITY` 의 키. 정의에 없는 타입은
    #: 커널이 거부한다 — 오타가 새 이벤트 타입이 되지 않게(표 ①과 같은 규약).
    event_type = models.CharField(max_length=32, db_index=True)
    #: 계약 열거 그대로: info | warning | critical. 커널이 열거를 검사한다.
    severity = models.CharField(max_length=16)
    #: ★ 비울 수 없다. 등급을 낮추는 변경은 **경보를 끄는 것**이고,
    #:   사유 없는 하향은 사후에 사고로만 보인다.
    reason = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "k5_grade_rule"
        ordering = ["event_type", "-id"]
        indexes = [
            # 판정 경로가 매번 타는 길 — 「무재기동 반영」의 값이 여기서 나온다
            models.Index(fields=["event_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.event_type}→{self.severity}"


class GradeRuleChange(BaseModel):
    """등급규칙 **변경 이력** — 표 ①의 `ThresholdChange` 와 같은 이유로 별도 표다.

    `updated_at` 한 칸은 "언제" 만 답한다. 사고 뒤에 필요한 질문은
    **"무엇에서 무엇으로, 누가, 왜"** 이고, 특히 등급 **하향**은 그 넷이 없으면
    "왜 경보가 안 왔나" 에 아무도 답하지 못한다.
    """

    event_type = models.CharField(max_length=32, db_index=True)
    #: null = 그전에는 코드의 잠정 기본값이었다 (덮어쓴 적이 없다).
    old_severity = models.CharField(max_length=16, null=True, blank=True)
    #: null = 덮어쓰기를 껐다 (기본값으로 돌아갔다).
    new_severity = models.CharField(max_length=16, null=True, blank=True)
    reason = models.CharField(max_length=255)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="grade_rule_changes")

    class Meta:
        db_table = "k5_grade_rule_change"
        ordering = ["-changed_at", "-id"]

    def __str__(self):
        return f"{self.event_type}: {self.old_severity}→{self.new_severity}"


# ═══════════════════════════════════════════════════════════════════════════
# K5 표 ② 자격증명 저장처 — **값이 아니라 「있는가」의 사실** (D-325 · D-328)
# ═══════════════════════════════════════════════════════════════════════════


class CredentialRecord(BaseModel):
    """외부 자격증명 하나에 대해 **우리가 아는 사실**. 값은 여기 없다.

    ★ 값을 담는 칸이 없다 — 실수로도 담을 수 없다 (D-204 · D-319)
    ---------------------------------------------------------------
    "마스킹해서 저장" 은 저장이다. 칸이 있으면 언젠가 채워지고, 채워진 값은 덤프·백업·
    화면·로그로 흘러나간다. 그래서 **칸 자체를 만들지 않는다.** 값은 환경변수에만 있다.

    ★ 상태 5값 — `present` 와 `typed` 사이의 간격이 하루였다 (D-328)
    ----------------------------------------------------------------
        absent   → 이 환경에 없다
        present  → 파일에 있다                    ← 여기까지만 알면 juso 사건이 반복된다
        typed    → **무슨 API 인지 안다**          ← 놓쳤던 칸
        verified → 호출해서 확인했다
        rotated  → 재발급됐다 (옛 값은 더 이상 유효하지 않다)

    2026-09-06 실측: 대표께서 juso 승인키 2건을 발급하셨고, 우리는 「키가 있는가」만
    물었다. 「어떤 키인가」를 묻지 않아서 **팝업 API(브라우저 UI 위젯)** 인 것을 하루 뒤에
    알았다. 그 하루가 `present` 와 `typed` 사이다.

    ★ 소유 테넌트는 기저의 `group` FK 다 — null 이면 **우리 계정 키**(모든 테넌트 공용).
      정수 칸을 따로 두지 않는 이유는 격리 판정이 `group` 하나만 보게 하기 위해서다(D-212).

    ★ 이 표가 서면 `blockers.yaml` 의 `verified_at`/`verified_by`(D-323)가
      **손으로 적는 칸이 아니라 조회 결과**가 된다.
    """

    class Status(models.TextChoices):
        ABSENT = "absent", "이 환경에 없다"
        PRESENT = "present", "파일에 있다"
        TYPED = "typed", "무슨 API 인지 안다"
        VERIFIED = "verified", "호출해서 확인했다"
        ROTATED = "rotated", "재발급됨"

    #: `kernels/k5_trust/credentials.py` 의 선언 이름. 선언에 없는 이름은 커널이 거부한다.
    name = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ABSENT, db_index=True)
    #: ★ 발급처가 부르는 그 이름 그대로 (D-328). "도로명주소 팝업 API".
    #:   우리 말로 바꿔 적으면 그 순간 신청 화면과 대조할 수 없게 된다.
    api_type = models.CharField(max_length=128, blank=True, default="")
    #: ★ 이 키로 **할 수 있는 일**. 비어 있으면 기능 코드가 이 키를 읽을 수 없다
    #:   (scripts/verify_credential_store.py 가 exit 1).
    capability = models.TextField(blank=True, default="")
    #: 이 환경에서 마지막으로 확인한 시각. **진술이 아니라 확인 행위가 남긴다**(D-323).
    verified_at = models.DateTimeField(null=True, blank=True)
    #: 무엇으로 확인했는가 — 파일·호출·화면. 비면 위 시각은 근거가 없다.
    verified_by = models.CharField(max_length=255, blank=True, default="")
    note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "k5_credential_record"
        ordering = ["name"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.name}[{self.status}]"


class WebhookSubscription(BaseModel):
    """UX-19 — **나가는 웹훅의 구독 한 줄.** 누가 · 어디로 · 무엇을 · 어떤 키로.

    왜 새 표를 만들었나 [판정 2026-09-05 · 차선 S]
    ---------------------------------------------
    현장 회신(D-차선 D)은 새 표를 피해 감사 표로 갔다. 여기서는 그럴 수 없다:
    구독은 **바뀌는 상태**(켜고 끄고 지운다)이고, 감사 표는 **바뀌지 않는 사실**의
    자리다. 바뀌는 것을 감사에 넣으면 「지금 켜져 있는가」를 감사 행을 되짚어
    계산해야 하고, 그 계산은 곧 두 벌이 된다.
    `NotificationRule` 에 얹는 것도 아니다 — 그 표는 **역할**을 가리키고 사람에게
    간다. 구독은 기관의 URL 로 간다. 한 표에 두 뜻을 넣으면 마지막에 쓴 사람이
    앞사람의 뜻을 덮는다(`status`/`response_state` 를 가른 D-399 와 같은 이유).

    ★ **서명키 값은 여기 없다** (D-204 · `CredentialRecord` 와 같은 규약)
    ---------------------------------------------------------------------
    `signing_key_ref` 는 **이름**이다. 값은 환경변수에만 있고, 이 표에는 그것을
    담을 칸 자체가 없다. 칸이 있으면 언젠가 채워지고, 채워진 값은 덤프·백업·화면·
    로그로 흘러나간다. 웹훅 서명키가 새면 **누구나 우리 이름으로 경보를 낼 수 있다.**

    ★ 소유 테넌트는 기저의 `group` FK 다 (`BaseModel` 이 준다 · D-292 실측).
      `BaseModelWithGroup` 은 DEPRECATED 이고 신규 상속은 게이트가 막는다(D-295).

    ★ **무계정 구독이 없다** (세종 §4-4 · P-37). `created_by` 없이 태어나는 행이
      없다 — 구독은 로그인한 계정이 등록하고, 그 계정의 테넌트가 곧 구독의 테넌트다.
      URL 하나가 계정이 되는 순간, 그것은 우리가 관리하지 않는 계정이다.
    """

    class PayloadFormat(models.TextChoices):
        JSON = "json", "CAP 1.2 (JSON)"
        XML = "xml", "CAP 1.2 (XML)"

    #: 우리가 POST 하는 곳. **평문 http 는 등록 단계에서 거절한다**(SEC-10 과 같은 이유) —
    #: 서명이 있어도 본문은 평문으로 지나간다.
    endpoint_url = models.URLField(max_length=500)
    #: 서명키의 **이름**. 값이 아니다. `settings.WEBHOOK_SIGNING_KEYS` 가 이름을 값에 잇는다.
    signing_key_ref = models.CharField(max_length=64)
    #: 어떤 이벤트를 받을 것인가. **빈 목록은 「전부」다** — 「아무것도 아님」이 아니다.
    #: 그 구별을 이름으로 남기려고 `is_active` 를 따로 둔다: 끄는 것은 여기가 아니다.
    event_types = models.JSONField(default=list, blank=True)
    #: 이 등급 **이상**만 보낸다. 비면 전부.
    min_severity = models.CharField(max_length=16, blank=True, default="")
    #: API-01 구독 필터 — `{"zone": [...], "severity": [...], "type": [...]}` (부속서 A U6#5·#6 ·
    #: WO-01 §5 「데이터」). **빈 dict 는 「거르지 않는다」다** — `event_types` 의 빈 목록과 같은 뜻.
    filters = models.JSONField(default=dict, blank=True)
    payload_format = models.CharField(
        max_length=8, choices=PayloadFormat.choices, default=PayloadFormat.JSON)
    is_active = models.BooleanField(default=True, db_index=True)
    #: 마지막으로 **성공한** 발송. 비어 있으면 「한 번도 도달한 적 없다」다 —
    #: 「보낸 적 없음」과 「보내려다 실패」는 발송 이력(`DeliveryRecord`)이 가른다.
    last_delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gx_webhook_subscription"
        ordering = ["id"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self) -> str:  # pragma: no cover - 관리 화면 표시용
        return f"webhook#{self.pk}[{'on' if self.is_active else 'off'}]"


# ═══════════════════════════════════════════════════════════════════════════
# DSM v1.1 신규 테이블 6 (+ 위 `WebhookSubscription.filters`) — WO-01 §5 「데이터」
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 이 앱(stream_monitors)인가 [판정 2026-09-15 · 턴 Q 차선 F-DB]
#   `apps.dsm` 은 INSTALLED_APPS 에 없다 — models.py 도 migrations 도 없는 **라우트·서비스
#   패키지**다. DSM 의 표는 전부 여기 산다(DetectionEvent · NotificationRule · Zone ·
#   WebhookSubscription · k5_credential_record). 새 앱을 세우면 settings 를 고치고
#   마이그레이션이 두 벌이 된다. 여기 두면 **한 벌**이다(지시서가 요구한 모양).
#   표 이름은 `db_table` 로 `dsm_*` 을 박는다 — 앱 라벨이 아니라 이름이 소속을 말한다
#   (PRD v1.1 §9 「앱 테이블은 접두」).
#
# 왜 models_v11.py 로 가르지 않았나
#   `scripts/verify_dead_fields.py` 의 모수가 `backend/**/models.py` 이름 그대로다(216행).
#   다른 이름의 파일에 두면 새 필드가 그 게이트 **밖**에서 태어난다 — 초록이 아니라 안 잰 것이다.
#
# 무엇을 만들지 않았나 — 정본(PRD v1.1 §5 · 부속서 A)에 없는 칸은 없다
#   · 인계 확인 체크(`handover/{id}/ack`)는 지침 보강 DSM-U2-05 의 것이다 — v1.1 일곱 밖.
#   · 보고서 산출물 객체 키 — `render(report_run) -> bytes`(WO-01 §5 HWPX)가 실행 기록에서
#     다시 만든다. 파일을 따로 두면 기록과 파일이 두 벌이 된다.
#   · M2M 은 쓰지 않는다 — 조인 표가 생기면 「스키마 변경은 이 일곱뿐」이 깨진다.
#     여러 개를 가리키는 칸은 id 목록(JSON)이다.


class TenantModel(BaseModel):
    """지시서·설계서가 부르는 **`TenantModel`** 의 실체 — 새 v1.1 표가 전부 이것을 상속한다.

    · 테넌트: dj-core `BaseModel` 이 준다 — `group` FK + `CustomManagerGroup`(스레드의 요청자
      group 으로 `objects` 를 좁힌다) + safedelete. `BaseModelWithGroup` 은 DEPRECATED(D-295).
    · ★ `purpose_code` **필수**: 이 행을 **무슨 목적으로** 처리했는가(설계서 §3 ③ 목적 코드 ·
      예 `dsm.monitor`). 기본값이 없고 빈 문자열은 **DB 가 거절한다**(CHECK). Django 의
      `blank=False` 는 폼 검증일 뿐이라 `objects.create(...)` 는 빈 값을 그대로 넣는다 —
      필수를 말로만 두면 첫 서비스 코드가 빈 값으로 채운다.

    ⚠ 이 클래스는 **추상**이다 — 표가 없다. 공통 `common/` 로 옮기는 것은 WO-02 의 몫이다.
    """

    purpose_code = models.CharField(max_length=64)

    class Meta:
        abstract = True
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(purpose_code=""),
                name="%(app_label)s_%(class)s_purpose_code_required"),
        ]


class DsmHandover(TenantModel):
    """UX-34 — **교대 인계 메모 한 건.** 쓴 사람 = `created_by` · 시각 = `created_on`.

    자동 초안이 세 수를 본문에 넣고, 사람은 특이사항 한 줄만 쓴다(PRD §5.2 UX-34).
    다음 근무자 역할 홈 상단의 「최신 1」은 이 표의 테넌트 최신 행이다(UX-32-U2).
    세 수를 칸으로 두는 이유 — 「상태는 칸으로」(WO-01 §12). 본문 글자에서 수를 다시
    뽑으면 홈 카드와 메모가 다른 수를 말할 수 있다.
    """

    #: 자동 초안 본문 — 미처리·시스템 사건·내가 처리한 건수가 삽입된 글.
    body = models.TextField()
    #: 사람이 쓰는 특이사항 한 줄. 비어도 된다(자동 초안만으로 인계가 성립한다).
    note = models.CharField(max_length=255, blank=True, default="")
    #: ★ 세 수에는 **기본값이 없다** — 0 은 「셌더니 0」이지 「안 셌다」가 아니다.
    unresolved_count = models.PositiveIntegerField()
    system_event_count = models.PositiveIntegerField()
    handled_count = models.PositiveIntegerField()
    #: 부속서 A U1#20 「인계 메모에 미처리 목록 자동 첨부」 — DetectionEvent id 목록.
    unresolved_event_ids = models.JSONField(default=list, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "dsm_handover"

    def __str__(self) -> str:  # pragma: no cover - 관리 화면 표시용
        return f"handover#{self.pk}"


class DsmFieldPhoto(TenantModel):
    """UX-45 · UX-26 — **현장 사진 한 장**(`POST /events/{id}/field-photo`).

    파일은 여기 없다. MinIO 객체 **키**만 둔다 — `DetectionEvent.snapshot_path` ·
    `EventClip.object_key` 와 같은 모양. 올린 사람 = `created_by` · 시각 = `created_on`.
    보존은 영상·스냅샷과 같은 선언값을 따른다(PRD §9 보관·파기 · LAW-02a).
    """

    event = models.ForeignKey(
        DetectionEvent, on_delete=models.CASCADE, related_name="field_photos")
    #: MinIO 객체 키. 빈 키의 사진 행은 뜻이 없다 — DB 가 거절한다.
    object_key = models.CharField(max_length=512)
    #: 형식 — `image/jpeg` 등. 렌더가 이 값으로 응답 헤더를 낸다(UX-26 「200 image/jpeg」).
    content_type = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()

    class Meta(TenantModel.Meta):
        db_table = "dsm_field_photo"
        constraints = [
            *TenantModel.Meta.constraints,
            models.CheckConstraint(
                condition=~models.Q(object_key=""),
                name="dsm_field_photo_object_key_required"),
        ]
        indexes = [
            # 사건 상세·M2 → 그 사건의 사진 목록 (EventClip 과 같은 경로)
            models.Index(fields=["event", "-id"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - 관리 화면 표시용
        return f"field_photo#{self.pk}@event{self.event_id}"


class DsmNotifyPrefs(TenantModel):
    """UX-43-M4 — **내 알림 설정**(`GET/PUT /api/dsm/me/notify-prefs`). 계정당 살아 있는 행 1.

    이 설정은 규칙(`NotificationRule`)이 고른 수신을 **좁히기만** 한다 — 넓히지 못한다.
    그래서 비어 있는 칸의 뜻은 전부 「좁히지 않는다」다(`WebhookSubscription.event_types` 와 같은 규약).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dsm_notify_prefs")
    #: 근무 외 차단 시간대(KST · SET-01). 둘 다 비면 차단 없음 · **하나만 채울 수 없다**(CHECK).
    #: 끝이 시작보다 이르면 자정을 넘는 구간이다(예 22:00 → 07:00).
    quiet_start = models.TimeField(null=True, blank=True)
    quiet_end = models.TimeField(null=True, blank=True)
    #: 담당 구역 — `Zone` id 목록. **빈 목록 = 전 구역.**
    zone_ids = models.JSONField(default=list, blank=True)
    #: 받을 채널 — `email` · `sms` · `webpush` 중에서. **빈 목록 = 규칙이 정한 채널 그대로.**
    channels = models.JSONField(default=list, blank=True)

    class Meta(TenantModel.Meta):
        db_table = "dsm_notify_prefs"
        constraints = [
            *TenantModel.Meta.constraints,
            # 소프트 삭제된 옛 행은 세지 않는다 — 살아 있는 설정이 둘이면 어느 쪽이 이기는지 모른다.
            models.UniqueConstraint(
                fields=["user"], condition=models.Q(deleted__isnull=True),
                name="dsm_notify_prefs_one_live_per_user"),
            models.CheckConstraint(
                condition=(models.Q(quiet_start__isnull=True, quiet_end__isnull=True)
                           | models.Q(quiet_start__isnull=False, quiet_end__isnull=False)),
                name="dsm_notify_prefs_quiet_window_whole"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 관리 화면 표시용
        return f"notify_prefs@user{self.user_id}"


class DsmOnboardingProgress(TenantModel):
    """UX-46 — **온보딩 카드 한 장의 완료.** 행이 있으면 닫혔다 · 없으면 아직이다.

    ★ 사람이 체크하지 않는다 — 서버 기록이 닫는다(WO-01 §12 · PRD §7.1).
      그래서 `source_ref`(닫은 기록의 이름 · 예 `review#123`) 없이는 행이 태어나지 못한다.
      근거 없이 닫힌 카드는 「체크했다」와 구별되지 않는다.
    진행률 % 의 분모(역할별 카드 ≤ 7)는 코드가 정한다 — 표에 적지 않는다(분모는 손으로 적지 않는다).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="dsm_onboarding_progress")
    #: 카드 키 — 역할을 앞에 붙인다(예 `u1.handover`). PRD §7.2 의 카드 한 장.
    card_key = models.CharField(max_length=64)
    completed_at = models.DateTimeField()
    #: 이 카드를 닫은 서버 기록.
    source_ref = models.CharField(max_length=128)

    class Meta(TenantModel.Meta):
        db_table = "dsm_onboarding_progress"
        constraints = [
            *TenantModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["user", "card_key"], condition=models.Q(deleted__isnull=True),
                name="dsm_onboarding_one_live_per_card"),
            models.CheckConstraint(
                condition=~models.Q(source_ref=""),
                name="dsm_onboarding_source_ref_required"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 관리 화면 표시용
        return f"onboarding[{self.card_key}]@user{self.user_id}"


class DsmReportRun(TenantModel):
    """UX-40 — **보고서 실행 기록 한 건**(사건 1쪽 · 「이번 달 우리 센터」 · 상급기관 제출용).

    월간본은 매월 1일 03:00 배치가 이 표에 한 행을 남긴다(부속서 A 243행). 사람 손 없이
    나왔는가(PRD §7.4)는 `trigger` 칸이 말한다. 산출물은 `render(report_run) -> bytes` 가
    이 행에서 다시 만든다(WO-01 §5 HWPX 인터페이스) — 「특이사항」을 고치면 재생성된다.
    """

    class Kind(models.TextChoices):
        INCIDENT = "incident", "사건 보고서"
        MONTHLY = "monthly", "이번 달 우리 센터"
        UPPER = "upper", "상급기관 제출용"

    class Trigger(models.TextChoices):
        AUTO = "auto", "자동 생성"
        MANUAL = "manual", "사람이 요청"

    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "생성됨"
        FAILED = "failed", "생성 실패"

    #: ★ 세 칸에는 기본값이 없다 — 누가·무엇을·어떻게 끝났는지는 실행한 쪽이 말한다.
    kind = models.CharField(max_length=16, choices=Kind.choices, db_index=True)
    trigger = models.CharField(max_length=16, choices=Trigger.choices)
    status = models.CharField(max_length=16, choices=Status.choices)
    #: 사건 보고서·상급 보고의 대상 사건. 사건이 보존 기한으로 파기돼도 **실행 기록은 남는다**.
    event = models.ForeignKey(
        DetectionEvent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="report_runs")
    #: 집계 구간(월간본). 사건 보고서는 비어 있다.
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    #: 「특이사항」 — 자동본을 사람이 고치는 칸(부속서 A U2#7).
    note = models.TextField(blank=True, default="")
    #: ★ `failed` 면 **반드시 채워진다**(CHECK) — 사유 없는 실패는 「없다」와 「못 했다」를
    #:   가르지 못한다(`EventClip.unavailable_reason` 과 같은 규약).
    failure_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta(TenantModel.Meta):
        db_table = "dsm_report_run"
        constraints = [
            *TenantModel.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(status="succeeded") | ~models.Q(failure_reason=""),
                name="dsm_report_run_failure_has_reason"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 관리 화면 표시용
        return f"report_run#{self.pk}[{self.kind}/{self.status}]"


class DsmUpperReportFlag(TenantModel):
    """UX-47 — **상급기관 보고 완료 체크**(사람 · `POST /events/{id}/upper-report`). 사건당 살아 있는 행 1.

    「보고 대상」 배지(심각 + 실제)는 **규칙이지 저장값이 아니다** — 사건의 등급·판정에서 매번
    계산한다. 저장하면 재판정(UX-37) 뒤에 배지가 낡는다. 여기 남는 것은 사람의 체크뿐이다:
    누가 = `created_by` · 체크 시각 = `created_on` · 실제로 보고한 시각 = `reported_at`.
    체크 해제는 소프트 삭제다(감사가 그 전이를 남긴다).
    """

    event = models.ForeignKey(
        DetectionEvent, on_delete=models.CASCADE, related_name="upper_report_flags")
    #: 실제로 보고한 시각 — 전화로 03:10 에 보고하고 03:30 에 체크할 수 있다.
    reported_at = models.DateTimeField()

    class Meta(TenantModel.Meta):
        db_table = "dsm_upper_report_flag"
        constraints = [
            *TenantModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["event"], condition=models.Q(deleted__isnull=True),
                name="dsm_upper_report_one_live_per_event"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 관리 화면 표시용
        return f"upper_report@event{self.event_id}"
