import hashlib
from core.file_management.models import UserMediaFile
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.base import BaseModel, BaseModelWithGroup
from common.utils import generate_unique_code
from common.measurable_model import MeasurableModelWithGroup
from devices.models import Device, MeasurableModel
from core.user.models import CoreUser
from checklist_setting.models import ChecklistSetting


class SurveillanceStatus(BaseModel):
    """Status cho Surveillance Profile."""

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    color_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Hex color code (e.g. #FF5733)",
    )

    TRANSLATABLE_FIELDS = ["name", "description"]

    class Meta:
        ordering = ["id"]
        verbose_name = "Surveillance Status"
        verbose_name_plural = "Surveillance Statuses"
        indexes = [models.Index(fields=["code"])]

    def __str__(self) -> str:  # pragma: no cover - debug-friendly representation
        return f"{self.name} ({self.code})"

class MissionPurpose(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description']


class SurveillanceProfileRepeatType(BaseModel):
    """Danh mục loại lặp cho Surveillance Profile."""

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)

    TRANSLATABLE_FIELDS = ["name", "description"]

    class Meta:
        ordering = ["id"]
        verbose_name = "Surveillance Profile Repeat Type"
        verbose_name_plural = "Surveillance Profile Repeat Types"
        indexes = [models.Index(fields=["code"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.code})"


class SurveillanceProfileRepeatUntilType(BaseModel):
    """Danh mục điều kiện dừng lặp cho Surveillance Profile."""

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)

    TRANSLATABLE_FIELDS = ["name", "description"]

    class Meta:
        ordering = ["id"]
        verbose_name = "Surveillance Profile Repeat Until Type"
        verbose_name_plural = "Surveillance Profile Repeat Until Types"
        indexes = [models.Index(fields=["code"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.code})"

class SurveyMissionStatus(BaseModel):
    """
    Status cho Survey Mission: pending_approval, approved, rejected, active, inactive
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    color_code = models.CharField(max_length=20, null=True, blank=True, help_text="Hex color code (e.g. #FF5733)")
    
    TRANSLATABLE_FIELDS = ['name', 'description']
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Survey Mission Status'
        verbose_name_plural = 'Survey Mission Statuses'
        indexes = [
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class MissionWaypoint(MeasurableModel):
    """
    Waypoint for Survey Mission (similar to RouteTerminal but for missions)
    Stores takeoff, land, and other critical waypoints for display on map
    Note: Survey grid waypoints are stored in qgc_mission_data, not here
    """
    mission = models.ForeignKey(
        'SurveyMission',
        on_delete=models.CASCADE,
        related_name='waypoints',
        db_index=True
    )
    terminal = models.ForeignKey(
        'terminals.Terminal',
        on_delete=models.SET_NULL,
        related_name='mission_waypoints',
        null=True,
        blank=True
    )
    
    # Waypoint details
    order = models.IntegerField(help_text="Order in mission (1=takeoff, last=land)")
    name = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.CharField()
    longitude = models.CharField()
    
    # MAVLink command data
    command_line = models.JSONField(
        null=True, 
        blank=True,
        help_text="MAVLink command: {command, frame, params}"
    )
    frame = models.JSONField(
        null=True, 
        blank=True,
        help_text="MAVLink command: {command, frame, params}"
    )
    note = models.TextField(null=True, blank=True)
    MEASUREMENT_TYPES = {
        'operating_altitude': {'type': 'simple', 'default_unit': 'm'},
        'cruise_speed': {'type': 'simple', 'default_unit': 'm/s'},
    }
    class Meta:
        ordering = ['order']
        verbose_name = 'Mission Waypoint'
        verbose_name_plural = 'Mission Waypoints'
        indexes = [
            models.Index(fields=['mission', 'order']),
        ]
    


class SurveyMission(MeasurableModelWithGroup):
    """
    Survey Mission for AI Detection
    Tạo survey route từ polygon với waypoints tự động
    Workflow: Draft → Pending Approval → Approved/Rejected → Active
    """
    code = models.CharField(max_length=255, unique=True, db_index=True, null=True, blank=True)
    name = models.CharField(max_length=255, db_index=True)
    maximum_drones = models.IntegerField(help_text="Maximum number of drones for this mission")
    purpose = models.ForeignKey(
        MissionPurpose,
        on_delete=models.PROTECT,
        related_name='survey_missions',
        db_index=True
    )
    polygon = models.JSONField(help_text="Survey area polygon [[lat,lon],...]", null=True, blank=True)
    qgc_mission_data = models.JSONField(
        null=True, 
        blank=True, 
        help_text="QGroundControl mission data for survey export"
    )
    total_waypoints = models.IntegerField(
        default=0,
        help_text="Total waypoints (takeoff + land, not including survey grid)"
    )
    log_collection = models.BooleanField(default=False, help_text="Enable log collection", null=True, blank=True)
    video_recording = models.BooleanField(default=False, help_text="Enable video recording", null=True, blank=True)
    video_analysis = models.BooleanField(default=False, help_text="Enable video analysis", null=True, blank=True)
    return_to_home = models.BooleanField(default=True, help_text="Return to home after mission", null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    # Status and workflow
    status = models.ForeignKey(
        SurveyMissionStatus,
        on_delete=models.PROTECT,
        related_name='survey_missions',
        db_index=True
    )
    approved_by = models.ForeignKey(
        'user.CoreUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_survey_missions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    rejected_by = models.ForeignKey(
        'user.CoreUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_survey_missions'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)  
    is_active = models.BooleanField(db_index=True, help_text="Mission is currently active", null=True)
    from_route = models.BooleanField(default=False, help_text="Mission is created from route", null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    hover_and_capture = models.BooleanField(default=False, help_text="Hover and capture", null=True, blank=True)
    # Drone segments information (for imported missions with pre-divided segments)
    drone_segments = models.JSONField(
        null=True,
        blank=True,
        help_text="List of drone mission segments with their waypoint ranges and QGC data. Format: [{'area_index': 0, 'drone_id': None, 'start_waypoint_order': 1, 'end_waypoint_order': 10, 'qgc_mission': {...}, ...}]"
    )
    MEASUREMENT_TYPES = {
        'altitude': {'type': 'simple', 'default_unit': 'm'},
        'trigger_distance': {'type': 'simple', 'default_unit': 'm'},
        'spacing': {'type': 'simple', 'default_unit': 'm'},
        'turnaround_distance': {'type': 'simple', 'default_unit': 'm'},
        # 'cruise_speed': {'type': 'simple', 'default_unit': 'm/s'},
        # 'hover_speed': {'type': 'simple', 'default_unit': 'm/s'},
        'survey_angle': {'type': 'simple', 'default_unit': '°'},
        'frontal_overlap': {'type': 'simple', 'default_unit': '%'},
        'side_overlap': {'type': 'simple', 'default_unit': '%'},
        'total_distance': {'type': 'simple', 'default_unit': 'km'},
        'estimated_time': {'type': 'simple', 'default_unit': 'mins'},
        # 'estimated_coverage': {'type': 'simple', 'default_unit': 'km²'},
        'altitude_separation': {'type': 'simple', 'default_unit': 'm'},
        'takeoff_altitude': {'type': 'simple', 'default_unit': 'm'},
    }
    class Meta:
        verbose_name = 'Survey Mission'
        verbose_name_plural = 'Survey Missions'
        indexes = [
            models.Index(fields=['-created_on']),
            models.Index(fields=['status']),
            models.Index(fields=['group', 'status']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name}"
    
    def can_edit(self) -> bool:
        """Check if mission can be edited (not approved and not active)"""
        return self.status.code not in ['approved', 'active']
    
    def can_approve(self) -> bool:
        """Check if mission can be approved (pending_approval status)"""
        return self.status.code == 'pending_approval'
    
    def can_activate(self) -> bool:
        """Check if mission can be activated (approved status)"""
        return self.status.code == 'approved' and not self.is_active
    
    


class SurveillanceProfile(MeasurableModelWithGroup):
    """정찰 프로파일 (Surveillance Profile)."""

    name = models.CharField(max_length=255, db_index=True)
    code = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)
    mission = models.ForeignKey(
        "SurveyMission",
        on_delete=models.PROTECT,
        related_name="surveillance_profiles",
        db_index=True,
    )
    status = models.ForeignKey(
        SurveillanceStatus,
        on_delete=models.PROTECT,
        related_name="surveillance_profiles",
        null=True,
        blank=True,
        db_index=True,
    )
    operator = models.ForeignKey(
        "user.CoreUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operated_surveillance_profiles",
    )
    reject_reason = models.TextField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        "user.CoreUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_surveillance_profiles",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(db_index=True)
    actual_start_time = models.DateTimeField(null=True, blank=True)
    estimated_end_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    repeat_type = models.ForeignKey(
        SurveillanceProfileRepeatType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
    )
    repeat_until_type = models.ForeignKey(
        SurveillanceProfileRepeatUntilType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
    )
    repeat_until_date = models.DateField(null=True, blank=True)
    repeat_occurrences = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    repeat_parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recurring_children",
    )
    repeat_metadata = models.JSONField(null=True, blank=True)
    color_code = models.CharField(max_length=20, default="#1D9BE2")
    note = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    not_yet = models.BooleanField(
        default=False,
        help_text="Profile start time has not been reached",
        db_index=True,
    )
    devices = models.ManyToManyField(
        Device,
        through="SurveillanceProfileDrone",
        related_name="surveillance_profiles",
        blank=True,
    )
    device_count = models.PositiveIntegerField(default=0)
    approved_by = models.ForeignKey(
        "user.CoreUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_surveillance_profiles",
    )
    cancel_reason = models.TextField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        "user.CoreUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_surveillance_profiles",
    )
    
    MEASUREMENT_TYPES = {
        "total_distance": {"type": "simple", "default_unit": "km"},
        "estimated_time": {"type": "simple", "default_unit": "mins"},
        "total_flight_time": {"type": "simple", "default_unit": "mins"},
        "takeoff_altitude": {"type": "simple", "default_unit": "m"},
        "altitude_separation": {"type": "simple", "default_unit": "m"},
        "actual_distance": {"type": "simple", "default_unit": "km"},
    }


    class Meta:
        ordering = ["-created_on"]
        verbose_name = "Surveillance Profile"
        verbose_name_plural = "Surveillance Profiles"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["mission", "status"]),
            models.Index(fields=["status", "start_time"]),
            models.Index(fields=["repeat_type"]),
            models.Index(fields=["repeat_until_type"]),
            models.Index(fields=["-created_on"]),
            models.Index(fields=["approved_by"]),
            models.Index(fields=["cancelled_by"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} - {self.code or 'N/A'}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_unique_code("SPF")

        super().save(*args, **kwargs)

        if self.pk:
            assignment_count = self.drone_assignments.count()
            if assignment_count != self.device_count:
                SurveillanceProfile.objects.filter(pk=self.pk).update(device_count=assignment_count)


class SurveillanceProfileDrone(MeasurableModel):
    """Assignment chi tiết cho từng drone trong profile."""

    profile = models.ForeignKey(
        SurveillanceProfile,
        on_delete=models.CASCADE,
        related_name="drone_assignments",
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="surveillance_profile_assignments",
    )
    order = models.PositiveIntegerField(default=1)
    scheduled_start_time = models.DateTimeField(null=True, blank=True)
    start_waypoint = models.ForeignKey(
        "MissionWaypoint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_start_assignments",
    )
    end_waypoint = models.ForeignKey(
        "MissionWaypoint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_end_assignments",
    )
    log_collection = models.BooleanField(default=True)
    video_recording = models.BooleanField(default=True)
    video_analysis = models.BooleanField(default=True)
    note = models.TextField(null=True, blank=True)
    log_path = models.CharField(max_length=255, null=True, blank=True)
    video_path = models.CharField(max_length=255, null=True, blank=True)
    analysis_path = models.CharField(max_length=255, null=True, blank=True)
    waiting_coordinates = models.JSONField(null=True, blank=True)
    MEASUREMENT_TYPES = {
        "estimated_distance": {"type": "simple", "default_unit": "km"},
        "estimated_time": {"type": "simple", "default_unit": "mins"},
        "actual_distance": {"type": "simple", "default_unit": "km"},
        "flight_time": {"type": "simple", "default_unit": "mins"},
    }
    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Surveillance Profile Drone"
        verbose_name_plural = "Surveillance Profile Drones"
        indexes = [
            models.Index(fields=["profile", "order"]),
            models.Index(fields=["device"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["profile", "order"], name="unique_profile_drone_order"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        device_name = self.device.name if self.device else "Unassigned"
        profile_code = self.profile.code if self.profile else "N/A"
        return f"{profile_code} - {device_name}"


class SurveillanceProfileChecklist(BaseModelWithGroup):
    """Checklist state for a specific drone assignment within a profile."""

    profile = models.ForeignKey(
        SurveillanceProfile,
        on_delete=models.CASCADE,
        related_name="device_checklists",
    )
    profile_drone = models.ForeignKey(
        SurveillanceProfileDrone,
        on_delete=models.CASCADE,
        related_name="checklists",
    )
    checked_by = models.ForeignKey(
        CoreUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="surveillance_profile_checks",
    )
    auto_check_data = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Surveillance Profile Checklist"
        verbose_name_plural = "Surveillance Profile Checklists"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "profile_drone"],
                name="unique_profile_checklist_per_drone",
            )
        ]
        indexes = [
            models.Index(fields=["profile", "profile_drone"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        profile_code = self.profile.code if self.profile else "N/A"
        device_name = self.device.name if self.device else "Unassigned"
        return f"Checklist for {profile_code} - {device_name}"


class SurveillanceProfileChecklistItem(BaseModel):
    """Manual checklist items selected during device checks."""

    checklist = models.ForeignKey(
        SurveillanceProfileChecklist,
        on_delete=models.CASCADE,
        related_name="items",
    )
    checklist_setting = models.ForeignKey(
        ChecklistSetting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="surveillance_profile_items",
    )
    item_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    category_code_snapshot = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Surveillance Profile Checklist Item"
        verbose_name_plural = "Surveillance Profile Checklist Items"
        constraints = [
            models.UniqueConstraint(
                fields=["checklist", "checklist_setting"],
                name="unique_profile_checklist_item",
            )
        ]

    def __str__(self) -> str:  # pragma: no cover
        if self.checklist_setting:
            return f"{self.checklist_setting.item_name}"
        return f"Checklist Item {self.id}"


class VideoAnalysis(BaseModelWithGroup):
    profile_device = models.ForeignKey(SurveillanceProfileDrone, on_delete=models.CASCADE, null=True, blank=True)
    stream_monitor = models.ForeignKey('stream_monitors.StreamMonitor', on_delete=models.CASCADE, null=True, blank=True)

    video_path = models.CharField(max_length=255, null=True, blank=True)
    analysis_path = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    drone_name = models.CharField(max_length=255, null=True, blank=True)
    operator_name = models.CharField(max_length=255, null=True, blank=True)
    register_number = models.CharField(max_length=255, null=True, blank=True)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    flight_distance = models.FloatField(null=True, blank=True)
    flight_time = models.IntegerField(null=True, blank=True)
    flight_altitude = models.FloatField(null=True, blank=True)
    start_point_x = models.CharField(max_length=255, null=True, blank=True)
    start_point_y = models.CharField(max_length=255, null=True, blank=True)
    end_point_x = models.CharField(max_length=255, null=True, blank=True)
    end_point_y = models.CharField(max_length=255, null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    remark = models.TextField(null=True, blank=True)
    deleted = models.DateField(null=True, blank=True)
    video_file = models.ForeignKey(UserMediaFile, on_delete=models.CASCADE, null=True, blank=True)