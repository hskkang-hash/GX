from datetime import datetime
from typing import Any, Dict, List, Optional

from ninja import Schema

from core.common.schema_utils import DynamicSchema
from devices.models import Device
from stream_monitors.models import StreamMonitor
from surveillance.models import (
    MissionWaypoint,
    SurveillanceProfile,
    SurveillanceProfileDrone,
    SurveillanceStatus,
    SurveyMission,
    SurveyMissionStatus,
    VideoAnalysis,
)

from common.schema_measurable import MeasurableDynamicSchema

class DeviceSimpleOutSchema(Schema):
    """Simple device output schema for nested display"""

    id: int
    name: str
    serial_number: str
    unit_id: Optional[str] = None
    color: Optional[str] = None
    status_id: Optional[int] = None


class MissionDroneOutSchema(Schema):
    """Drone info within a mission for daily region view."""

    device_id: int
    device_name: str
    serial_number: str
    unit_id: Optional[str] = None
    color: Optional[str] = None
    status_code: Optional[str] = None
    status_name: Optional[str] = None


class RegionMissionOutSchema(Schema):
    """Mission data grouped under a region."""

    mission_id: int
    mission_name: str
    mission_code: Optional[str] = None
    profile_id: int
    profile_name: str
    profile_code: Optional[str] = None
    drones: List[MissionDroneOutSchema]


class RegionDronesOutSchema(Schema):
    """Region with its missions and drones for today."""

    region: str
    missions: List[RegionMissionOutSchema]


class SurveillanceProfileChangeDroneOptionOutSchema(Schema):
    """Output schema for available drones when changing assignments."""

    device_id: int
    serial_number: Optional[str] = None
    model: Optional[str] = None
    battery: Optional[str] = None


class RouteSimpleOutSchema(Schema):
    """Simple route output schema for nested display"""

    id: int
    name: str
    code: Optional[str] = None


class SurveillanceStatusOutSchema(DynamicSchema):
    """Output schema for surveillance status."""

    class Meta:
        model = SurveillanceStatus
        model_fields = ["id", "name", "code", "description", "color_code"]


class SurveillanceProfileDroneOutSchema(DynamicSchema):
    """Output schema for profile drone assignments."""
    class Meta:
        model = SurveillanceProfileDrone
        exclude_field = ['*group','*profile', '*modified']

class SurveillanceProfileOutSchema(MeasurableDynamicSchema):

    class Meta:
        depth=2
        model = SurveillanceProfile
        exclude_field = ['*qgc_mission_data']

class SurveillanceProfileSelectedOutSchema(DynamicSchema):
    """Output schema for surveillance profile"""
    class Meta:
        model = SurveillanceProfile
        exclude_field = ['*qgc_mission_data']

class SurveillanceProfileWithMapOutSchema(Schema):
    """Output schema for surveillance profile with map data."""

    profile: SurveillanceProfileOutSchema
    route_waypoints: Optional[List[Dict[str, Any]]] = None
    devices_positions: Optional[List[Dict[str, Any]]] = None


class SurveillanceProfileTimelineProfileOutSchema(Schema):
    """Timeline item when grouping theo profile."""

    profile_id: int
    profile_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    color_code: Optional[str] = None



class SurveillanceProfileTimelineDroneOutSchema(Schema):
    """Timeline item when grouping theo drone/assignment."""

    assignment_id: int
    profile_id: int
    profile_name: str
    device_id: Optional[int] = None
    device_serial: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    color_code: Optional[str] = None


class SurveillanceProfileTimelineOutSchema(Schema):
    """Wrapper schema cho dữ liệu timeline."""

    by_profile: List[SurveillanceProfileTimelineProfileOutSchema]
    by_drone: List[SurveillanceProfileTimelineDroneOutSchema]


class SurveyMissionStatusOutSchema(DynamicSchema):
    """Output schema for survey mission status"""
    class Meta:
        model = SurveyMissionStatus
        model_fields = ['id', 'name', 'code', 'description', 'color_code']


class GroupSimpleOutSchema(Schema):
    """Simple group output schema"""
    id: int
    name: str


class UserSimpleOutSchema(Schema):
    """Simple user output schema"""
    id: int
    username: str
    full_name: Optional[str] = None


class SurveyMissionOutSchema(MeasurableDynamicSchema):

    
    class Meta:
        model = SurveyMission
        
        exclude_field = ['polygon', 'qgc_mission_data']

class SurveyMissionDetailOutSchema(MeasurableDynamicSchema):
    """Output schema for survey mission"""
    route_data: Optional[RouteSimpleOutSchema] = None
    status_data: Optional[SurveyMissionStatusOutSchema] = None
    group_data: Optional[GroupSimpleOutSchema] = None
    approved_by_data: Optional[UserSimpleOutSchema] = None
    rejected_by_data: Optional[UserSimpleOutSchema] = None
    cancelled_by_data: Optional[UserSimpleOutSchema] = None
    has_approve_permission: Optional[bool] = None  # Added dynamically in view based on user permissions
    
    class Meta:
        model = SurveyMission
        model_fields = [
            'id', 'name', 'group_id', 'maximum_drones', 'purpose',
            'polygon', 'altitude', 'survey_angle',
            'frontal_overlap', 'side_overlap', 'entry_location',
            'cruise_speed', 'hover_speed',
            'log_collection', 'video_recording', 'video_analysis', 'return_to_home',
            'start_point_lat', 'start_point_lon', 'end_point_lat', 'end_point_lon',
            'status_id', 'start_time', 'end_time',
            'estimated_waypoints', 'estimated_distance_km', 
            'estimated_time_minutes', 'estimated_coverage_km2',
            'approved_by_id', 'approved_at', 'approval_note', 'cancelled_by_id',
            'rejected_by_id', 'rejected_at', 'rejection_reason',
            'is_active', 'note', 'created_on', 'modified_on'
        ]
class SurveyMissionPreviewOutSchema(Schema):
    """Output schema for survey mission preview (before creation)"""
    waypoints: int
    distance_km: float
    time_minutes: int
    coverage_km2: float
    transects: int
    waypoints_visualization: List[Dict]
    transects_visualization: List[List[Dict]]
    visual_transect_points: List[List[float]]
    start_point: Optional[List[float]] = None
    end_point: Optional[List[float]] = None
    effective_polygon: Optional[Any] = None
    effective_polygons: Optional[List[List[List[float]]]] = None
    polygon_adjusted: bool = False

class MissionWaypointOutSchema(MeasurableDynamicSchema):
    """Output schema for mission waypoint"""
    class Meta:
        model = MissionWaypoint
        model_fields = ['id', 'order', 'name', 'latitude', 'longitude', 'command_line', 'frame', 'note', 'created_on', 'modified_on']


class WaypointDetailSchema(Schema):
    """Schema for detailed waypoint information"""
    order: int
    waypoint_index: int
    lat: float
    lon: float
    alt: float
    type: str
    description: str


class TransectDetailSchema(Schema):
    """Schema for detailed transect information"""
    transect_index: int
    order: int
    entry_point: Dict
    exit_point: Dict
    turnaround_start: Dict
    turnaround_end: Dict
    length_km: float
    description: str


class DroneStatisticsSchema(Schema):
    """Schema for drone mission statistics"""
    total_transects: int
    total_waypoints: int
    average_transect_length_km: float
    waypoints_per_transect: float


class DroneMissionOutSchema(Schema):
    """Output schema for individual drone mission"""
    drone_id: int
    device_id: int
    device_name: str
    device_serial: str
    start_waypoint: int
    end_waypoint: int
    start_transect: int
    end_transect: int
    distance_km: float
    waypoints: List[Dict]
    takeoff_point: List[float]
    landing_point: List[float]
    # Thông tin chi tiết mới
    route_path: List[WaypointDetailSchema]
    transect_path: List[TransectDetailSchema]
    qgc_command_items: List[Dict]
    statistics: DroneStatisticsSchema


class DroneQgcMissionOutSchema(Schema):
    """Output schema for drone QGC mission"""
    fileType: str
    geoFence: Dict
    groundStation: str
    mission: Dict
    rallyPoints: Dict
    version: int
    drone_info: Dict


class SurveyMissionDroneDivisionOutSchema(Schema):
    """Output schema for survey mission drone division"""
    basic_mission: Dict
    drone_missions: List[DroneMissionOutSchema]
    drone_qgc_missions: List[DroneQgcMissionOutSchema]
    summary: Dict

class VideoAnalysisOutSchema(DynamicSchema):
    """Output schema for video analysis"""
    video_size: Optional[int] = None
    profile_name: Optional[str] = None
    
    class Meta:
        model = VideoAnalysis
        model_fields = [
            'id', 
            'profile_device_id', 
            'stream_monitor_id', 
            'video_path', 
            'analysis_path', 
            'created_at', 
            'updated_at', 
            'drone_name', 
            'operator_name', 
            'register_number', 
            'manufacturer', 
            'flight_distance', 
            'flight_time', 
            'flight_altitude', 
            'start_point_x', 
            'start_point_y', 
            'end_point_x', 
            'end_point_y', 
            'start_time', 
            'end_time', 
            'remark'
        ]
    
    @classmethod
    def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
        """Override to add video_size from video_path and profile_name"""
        from stream_monitors.utils.minio_client import minio_client
        from surveillance.models import SurveillanceProfileDrone
        result = None
        if many:
            result = super().from_queryset(queryset_or_instance, many=many)
        else:
            result = super().from_queryset(queryset_or_instance, many=False)
      
        from surveillance.utils import get_location_from_latlng
        # Handle both single instance and queryset
        if many:
            # result is a list
            # Convert queryset to list to access instances by index
            from django.db.models import QuerySet
            if isinstance(queryset_or_instance, QuerySet):
                instances = list(queryset_or_instance)
            elif hasattr(queryset_or_instance, '__iter__') and not isinstance(queryset_or_instance, (str, dict)):
                instances = list(queryset_or_instance)
            else:
                instances = [queryset_or_instance]

            # Bulk fetch profile_drones + prefetched measurements to avoid N+1
            profile_drone_map = {}
            try:
                profile_drone_ids = list(
                    {
                        int(getattr(inst, "profile_device_id"))
                        for inst in instances
                        if getattr(inst, "profile_device_id", None)
                    }
                )
                if profile_drone_ids:
                    profile_drones = (
                        SurveillanceProfileDrone.objects.filter(id__in=profile_drone_ids)
                        .prefetch_related("measurements")
                    )
                    profile_drone_map = {pd.id: pd for pd in profile_drones}
            except Exception:
                profile_drone_map = {}

            def _get_prefetched_measurement_formatted(profile_drone, measurement_type: str):
                try:
                    cached = getattr(profile_drone, "_prefetched_objects_cache", {}).get("measurements")
                    measurements = cached if cached is not None else list(profile_drone.measurements.all())
                    for m in measurements:
                        if getattr(m, "measurement_type", None) == measurement_type:
                            return m.get_formatted_value()
                except Exception:
                    pass
                # Fallback to model helper (may query)
                try:
                    return profile_drone.get_formatted_value(measurement_type)
                except Exception:
                    return None
            
            for idx, item in enumerate(result):
                instance = instances[idx] if idx < len(instances) else None
                
                if item.get('video_path'):
                    # Check if video_file.file_size exists first
                    if instance and hasattr(instance, 'video_file') and instance.video_file and instance.video_file.file_size:
                        item['video_size'] = instance.video_file.file_size
                    else:
                        # Get from minio and save to video_file.file_size
                        video_size = minio_client.get_file_size(item['video_path'])
                        item['video_size'] = video_size
                        # Save to instance.video_file.file_size if video_file exists
                        if instance and hasattr(instance, 'video_file') and instance.video_file and video_size:
                            instance.video_file.file_size = video_size
                            instance.video_file.save(update_fields=['file_size'])
                
                # Get profile_name from model instance
                try:
                    if instance:
                        print(hasattr(instance, 'stream_monitor'), instance.stream_monitor)
                        if hasattr(instance, 'profile_device') and instance.profile_device and hasattr(instance.profile_device, 'profile'):
                            item['profile_name'] = instance.profile_device.profile.name
                        elif hasattr(instance, 'stream_monitor') and instance.stream_monitor:
                            item['profile_name'] = instance.stream_monitor.name
                        else:
                            item['profile_name'] = None
                    else:
                        item['profile_name'] = None
                except (IndexError, AttributeError):
                    item['profile_name'] = None
                if item.get('drone_name') is None or item.get('drone_name') == '':
                    item['drone_name'] = item.get('stream_monitor__name') if item.get('stream_monitor__name') else None

                # Override flight_time / flight_distance from SurveillanceProfileDrone measurements if available
                try:
                    if instance and getattr(instance, "profile_device_id", None):
                        pd = profile_drone_map.get(int(instance.profile_device_id))
                        if pd:
                            ft = _get_prefetched_measurement_formatted(pd, "flight_time")
                            dist = _get_prefetched_measurement_formatted(pd, "actual_distance")
                            if ft is not None:
                                item["flight_time"] = ft
                            if dist is not None:
                                item["flight_distance"] = dist
                except Exception:
                    pass

        else:
            # result is a dict
            # Get the actual model instance
            instance = queryset_or_instance.first() if hasattr(queryset_or_instance, 'first') else queryset_or_instance
            
            if result and result.get('video_path'):
                # Check if video_file.file_size exists first
                if instance and hasattr(instance, 'video_file') and instance.video_file and instance.video_file.file_size:
                    result['video_size'] = instance.video_file.file_size
                else:
                    # Get from minio and save to video_file.file_size
                    video_size = minio_client.get_file_size(result['video_path'])
                    result['video_size'] = video_size
                    # Save to instance.video_file.file_size if video_file exists
                    if instance and hasattr(instance, 'video_file') and instance.video_file and video_size:
                        instance.video_file.file_size = video_size
                        instance.video_file.save(update_fields=['file_size'])
            
            # Get profile_name from model instance
            try:
                if hasattr(instance, 'profile_device') and instance.profile_device and hasattr(instance.profile_device, 'profile'):
                    result['profile_name'] = instance.profile_device.profile.name
                elif hasattr(instance, 'stream_monitor') and instance.stream_monitor :
                    result['profile_name'] = instance.stream_monitor.name
                else:
                    result['profile_name'] = None
            except AttributeError:
                result['profile_name'] = None

            # Override flight_time / flight_distance from SurveillanceProfileDrone measurements if available
            try:
                profile_device_id = getattr(instance, "profile_device_id", None)
                if profile_device_id:
                    pd = (
                        SurveillanceProfileDrone.objects.filter(id=profile_device_id)
                        .prefetch_related("measurements")
                        .first()
                    )
                    if pd:
                        cached = getattr(pd, "_prefetched_objects_cache", {}).get("measurements")
                        measurements = cached if cached is not None else list(pd.measurements.all())
                        m_map = {getattr(m, "measurement_type", None): m for m in measurements}
                        m_ft = m_map.get("flight_time")
                        m_dist = m_map.get("actual_distance")
                        ft_val = m_ft.get_formatted_value() if m_ft else None
                        dist_val = m_dist.get_formatted_value() if m_dist else None
                        if ft_val is not None:
                            result["flight_time"] = ft_val
                        if dist_val is not None:
                            result["flight_distance"] = dist_val
                elif hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_flight_time') and hasattr(instance.stream_monitor, 'external_flight_distance'):
                    result['flight_time'] = instance.stream_monitor.external_flight_time
                    result['flight_distance'] = instance.stream_monitor.external_flight_distance
            except Exception:
                pass

            if result['drone_name'] is None or result['drone_name'] == '':
                try:
                    if result['stream_monitor__id']:
                        stream_monitor = StreamMonitor.objects.get(id=result['stream_monitor__id'])
                        result['drone_name'] = stream_monitor.external_drone_name if stream_monitor.external_drone_name else stream_monitor.drone.name
                except Exception as e:
                    pass

            if result['register_number'] is None or result['register_number'] == '':
                try:
                    if result['stream_monitor__id'] and not result.get('stream_monitor__is_external', False):
                        stream_monitor = StreamMonitor.objects.get(id=result['stream_monitor__id'])
                        drone = Device.objects.get(id=stream_monitor.drone_id)
                        manufacturer_information = drone.manufacturer_information
                        result['register_number'] = manufacturer_information.registration_number
                    elif hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_registration_number'):
                        result['register_number'] = instance.stream_monitor.external_registration_number
                except Exception as e:
                    pass

            if result['manufacturer'] is None or result['manufacturer'] == '':
                try:
                    if result['stream_monitor__id'] and not result.get('stream_monitor__is_external', False):
                        stream_monitor = StreamMonitor.objects.get(id=result['stream_monitor__id'])
                        drone = Device.objects.get(id=stream_monitor.drone_id)
                        manufacturer_information = drone.manufacturer_information
                        result['manufacturer'] = manufacturer_information.manufacturer
                    elif hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_manufacturer'):
                        result['manufacturer'] = instance.stream_monitor.external_manufacturer
                except Exception as e:
                    pass

            # get mission location by api
            try:
                if hasattr(instance, 'profile_device') and instance.profile_device and hasattr(instance.profile_device, 'profile') and hasattr(instance.profile_device.profile, 'mission'):
                    result['mission_location'] = instance.profile_device.profile.mission.region if instance.profile_device.profile.mission.region else None
                
                elif result['start_point_x'] and result['start_point_y']:
                    result['mission_location'] = get_location_from_latlng(result['start_point_x'], result['start_point_y']).get('city', None) if get_location_from_latlng(result['start_point_x'], result['start_point_y']) else None
                elif hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_start_point_x') and hasattr(instance.stream_monitor, 'external_start_point_y'):
                    result['start_point_x'] = instance.stream_monitor.external_start_point_x if instance.stream_monitor and instance.stream_monitor.external_start_point_x else None
                    result['start_point_y'] = instance.stream_monitor.external_start_point_y if instance.stream_monitor and instance.stream_monitor.external_start_point_y else None
                    result['mission_location'] = get_location_from_latlng(result['start_point_x'], result['start_point_y']).get('city', None) if get_location_from_latlng(result['start_point_x'], result['start_point_y']) else None
                else:
                    result['mission_location'] = None
            except Exception as e:
                result['mission_location'] = None
            try:
                if not result.get('end_point_x') and hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_end_point_x'):
                    result['end_point_x'] = instance.stream_monitor.external_end_point_x if instance.stream_monitor and instance.stream_monitor.external_end_point_x else None
                if not result.get('end_point_y') and hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_end_point_y'):
                    result['end_point_y'] = instance.stream_monitor.external_end_point_y if instance.stream_monitor and instance.stream_monitor.external_end_point_y else None
            except Exception as e:
                pass

            try:
                if not result.get('start_time') and hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_start_time'):
                    result['start_time'] = instance.stream_monitor.external_start_time if instance.stream_monitor and instance.stream_monitor.external_start_time else None
                if not result.get('end_time') and hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_end_time'):
                    result['end_time'] = instance.stream_monitor.external_end_time if instance.stream_monitor and instance.stream_monitor.external_end_time else None
            except Exception as e:
                pass

            try:
                if not result.get('remark') and hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_remark'):
                    result['remark'] = instance.stream_monitor.external_remark if instance.stream_monitor and instance.stream_monitor.external_remark else None
            except Exception as e:
                pass

            try:
                if not result.get('operator_name') and hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_operation_name'):
                    result['operator_name'] = instance.stream_monitor.external_operation_name if instance.stream_monitor and instance.stream_monitor.external_operation_name else None
            except Exception as e:
                pass

            try:
                if not result.get('flight_altitude') and hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_flight_altitude'):
                    result['flight_altitude'] = instance.stream_monitor.external_flight_altitude if instance.stream_monitor and instance.stream_monitor.external_flight_altitude else None
            except Exception as e:
                pass

            try:
                if not result.get('capture_altitude') and hasattr(instance, 'stream_monitor') and instance.stream_monitor and hasattr(instance.stream_monitor, 'external_flight_altitude'):
                    result['capture_altitude'] = instance.stream_monitor.external_flight_altitude if instance.stream_monitor and instance.stream_monitor.external_flight_altitude else None
            except Exception as e:
                pass

            try:
                if not result.get('profile_device__created_on') :
                    result['profile_device__created_on'] = instance.created_at if instance and instance.created_at else None
            except Exception as e:
                pass
        return result