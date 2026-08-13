"""
Survey Mission Service
Business logic for survey mission CRUD and management with approval workflow
"""

from datetime import datetime
import json
import logging
import io
import zipfile
from typing import Tuple, Any, List, Dict, Optional
from core.api.v1.auth import CoreUser
from django.db import transaction
from django.db.models.functions import Concat
from django.utils import timezone
from django.db.models import Q
from surveillance.models import MissionPurpose, SurveyMission, SurveyMissionStatus, MissionWaypoint
from terminals.models import RouteTerminal, Routes, Terminal, TerminalType
from terminals.services.qground_control_service import QGroundControlService
from surveillance.services.survey_mission_builder_service import SurveyMissionBuilderService
from ninja.errors import ValidationError
from shapely.geometry import Polygon, LineString
from shapely.ops import polygonize, unary_union
from shapely.geometry.base import BaseGeometry
from common.utils import get_waypoint_speed, get_return_to_home_default
from common.constant import MESSAGE_ENUM

try:
    from shapely.validation import make_valid
except ImportError:  # Shapely < 2.0
    make_valid = None
from django.db.models import Q, Func, OuterRef, Subquery, Count, Max, F, Case, When, BooleanField, Exists, CharField, Sum, Value, TextField, Prefetch
from django.db.models.functions import Cast

logger = logging.getLogger(__name__)
MAXIMUM_ITEMS_PER_MISSION = 1000

class SurveyMissionService:
    """Service for managing survey missions"""
    
    # Create a shared QGroundControlService instance for API calls
    _qgc_service = None
    
    # Cache for command names to avoid repeated API calls
    _command_name_cache = {}
    _frame_name_cache = {}
    
    @classmethod
    def _get_qgc_service(cls):
        """Get or create QGroundControlService instance (for caching)"""
        if cls._qgc_service is None:
            cls._qgc_service = QGroundControlService()
        return cls._qgc_service
    
    @staticmethod
    def _collect_polygon_components(geometry: BaseGeometry) -> List[Polygon]:
        if geometry.is_empty:
            return []

        if isinstance(geometry, Polygon):
            return [geometry]

        if hasattr(geometry, "geoms"):
            return [geom for geom in geometry.geoms if isinstance(geom, Polygon) and not geom.is_empty]

        return []

    @staticmethod
    def _sanitize_polygon_points(polygon: List[List[float]]) -> Tuple[List[List[List[float]]], bool]:
        """Ensure polygon is valid for geometric operations, mimicking QGC behaviour."""
        if not polygon or len(polygon) < 3:
            return [polygon], False

        lon_lat_coords = [(point[1], point[0]) for point in polygon]

        # Use polygonize to split self-intersections similar to QGC's even-odd rule
        line = LineString(lon_lat_coords + [lon_lat_coords[0]])
        polygons = list(polygonize(line))

        changed = False

        if polygons:
            processed_geometry = unary_union(polygons)
            if len(polygons) > 1:
                changed = True
        else:
            processed_geometry = Polygon(lon_lat_coords)
            if not processed_geometry.is_valid:
                changed = True
                if make_valid:
                    processed_geometry = make_valid(processed_geometry)
                else:
                    processed_geometry = processed_geometry.buffer(0)

        if processed_geometry.is_empty:
            raise ValidationError("Polygon geometry is invalid after sanitization")

        components = []
        for geom in SurveyMissionService._collect_polygon_components(processed_geometry):
            coords = list(geom.exterior.coords)
            if len(coords) < 4:
                continue
            latlon = [[lat, lon] for lon, lat in coords[:-1]]
            if len(latlon) >= 3:
                components.append(latlon)

        if not components:
            raise ValidationError("Polygon geometry produced no valid components")

        if not changed:
            if len(components) != 1 or len(components[0]) != len(polygon):
                changed = True
            else:
                for original, sanitized in zip(polygon, components[0]):
                    if abs(original[0] - sanitized[0]) > 1e-9 or abs(original[1] - sanitized[1]) > 1e-9:
                        changed = True
                        break

        return components, changed

    @staticmethod
    def _insert_action_commands(qgc_mission_data: dict, action_commands: list) -> dict:
        """
        Insert action commands after specific waypoints in QGC mission data
        and recalculate all doJumpId values
        
        Time Complexity: O(n + m) where n = waypoints, m = action_commands
        Space Complexity: O(n + m)
        
        Args:
            qgc_mission_data: Original QGC mission data
            action_commands: List of action commands to insert
            
        Returns:
            Modified QGC mission data with action commands inserted and doJumpId recalculated
            
        Example action_command:
        {
            "insert_after_order": 4,  # Insert after waypoint with doJumpId = 4
            "command": 183,  # MAV_CMD_DO_DIGICAM_CONTROL
            "params": [10, 1100, 1, 0, 0, 0, 0],
            "frame": 2,  # MISSION frame
            "auto_continue": True
        }
        """
        if not action_commands or not qgc_mission_data:
            return qgc_mission_data
        
        # Shallow copy top-level dict to avoid modifying original
        # but share nested structures for performance
        modified_qgc_data = {
            'fileType': qgc_mission_data.get('fileType'),
            'geoFence': qgc_mission_data.get('geoFence'),
            'groundStation': qgc_mission_data.get('groundStation'),
            'mission': {},  # Will be rebuilt
            'rallyPoints': qgc_mission_data.get('rallyPoints'),
            'version': qgc_mission_data.get('version')
        }
        
        # Get mission items
        if 'mission' not in qgc_mission_data or 'items' not in qgc_mission_data['mission']:
            return qgc_mission_data
        
        original_mission = qgc_mission_data['mission']
        items = original_mission.get('items', [])
        
        # Copy mission metadata (shallow copy is fine for primitives)
        modified_qgc_data['mission'] = {
            'cruiseSpeed': original_mission.get('cruiseSpeed'),
            'firmwareType': original_mission.get('firmwareType'),
            'globalPlanAltitudeMode': original_mission.get('globalPlanAltitudeMode'),
            'hoverSpeed': original_mission.get('hoverSpeed'),
            'plannedHomePosition': original_mission.get('plannedHomePosition'),
            'vehicleType': original_mission.get('vehicleType'),
            'version': original_mission.get('version'),
            'items': []  # Will be rebuilt
        }
        
        # O(m) - Group action commands by insert position using dict (hash map)
        actions_by_position = {}
        for action in action_commands:
            insert_after = action.get('insert_after_order')
            if insert_after is not None:
                if insert_after not in actions_by_position:
                    actions_by_position[insert_after] = []
                actions_by_position[insert_after].append(action)
        
        # O(n) - Process items and insert action commands in single pass
        new_items = []
        navigation_commands = {16, 22, 20}  # Use set for O(1) lookup
        
        for item in items:
            item_type = item.get('type')
            
            if item_type == 'ComplexItem':
                # Need to copy ComplexItem structure to avoid modifying original
                new_item = dict(item)  # Shallow copy item
                transect_item = item.get('TransectStyleComplexItem')
                
                if transect_item and 'Items' in transect_item:
                    # Copy TransectStyleComplexItem
                    new_transect = dict(transect_item)
                    survey_items = transect_item['Items']
                    new_survey_items = []
                    
                    for survey_item in survey_items:
                        new_survey_items.append(survey_item)
                        
                        # O(1) lookup in hash map and set
                        do_jump_id = survey_item.get('doJumpId')
                        command = survey_item.get('command', {})
                        command_id = command.get('id') if isinstance(command, dict) else command
                        
                        # Only insert after navigation commands
                        if do_jump_id and command_id in navigation_commands and do_jump_id in actions_by_position:
                            # Append all actions for this position
                            for action in actions_by_position[do_jump_id]:
                                new_survey_items.append({
                                    "autoContinue": action.get('auto_continue', True),
                                    "command": action['command'],
                                    "doJumpId": 0,  # Will be recalculated later
                                    "frame": action['frame'],
                                    "params": action['params'],
                                    "type": action.get('type', 'SimpleItem')
                                })
                    
                    # Update survey items
                    new_transect['Items'] = new_survey_items
                    new_item['TransectStyleComplexItem'] = new_transect
                
                new_items.append(new_item)
                
            elif item_type == 'SimpleItem':
                new_items.append(item)
                
                # O(1) lookup in hash map and set
                do_jump_id = item.get('doJumpId')
                command = item.get('command', {})
                command_id = command.get('id') if isinstance(command, dict) else command
                
                # Only insert after navigation commands
                if do_jump_id and command_id in navigation_commands and do_jump_id in actions_by_position:
                    # Append all actions for this position
                    for action in actions_by_position[do_jump_id]:
                        new_items.append({
                            "autoContinue": action.get('auto_continue', True),
                            "command": action['command'],
                            "doJumpId": 0,  # Will be recalculated later
                            "frame": action['frame'],
                            "params": action['params'],
                            "type": action.get('type', 'SimpleItem')
                        })
            else:
                new_items.append(item)
        
        # Update items
        modified_qgc_data['mission']['items'] = new_items
        
        # O(n) - Recalculate all doJumpId values
        SurveyMissionService._recalculate_do_jump_ids(modified_qgc_data)
        
        return modified_qgc_data
    
    @staticmethod
    def _recalculate_do_jump_ids(qgc_mission_data: dict) -> dict:
        """
        Recalculate all doJumpId values in QGC mission data sequentially
        
        Time Complexity: O(n) where n = total number of items
        Space Complexity: O(1) - modifies in-place
        
        Args:
            qgc_mission_data: QGC mission data with potentially incorrect doJumpId
            
        Returns:
            QGC mission data with correct doJumpId values (modified in-place)
        """
        if 'mission' not in qgc_mission_data or 'items' not in qgc_mission_data['mission']:
            return qgc_mission_data
        
        items = qgc_mission_data['mission']['items']
        current_id = 1
        
        # O(n) - Single pass through all items
        for item in items:
            item_type = item.get('type')
            
            if item_type == 'ComplexItem':
                # Handle ComplexItem (Survey) - O(k) where k = survey items
                transect_item = item.get('TransectStyleComplexItem')
                if transect_item and 'Items' in transect_item:
                    survey_items = transect_item['Items']
                    for survey_item in survey_items:
                        if 'doJumpId' in survey_item:
                            survey_item['doJumpId'] = current_id
                            current_id += 1
                            
            elif item_type == 'SimpleItem':
                # Handle SimpleItem - O(1)
                if 'doJumpId' in item:
                    item['doJumpId'] = current_id
                    current_id += 1
        
        return qgc_mission_data
    
    @staticmethod
    def _build_command_line(command: int, params: List) -> Dict:
        """
        Build command_line theo format: {"16": {"WAYPOINT": ["0", "0", ...]}}
        Same format as qground_control_service.py
        
        Example:
        {
          "16": {
            "WAYPOINT": ["0", "0", "0", "0", "37.412028", "126.950878", "0"]
          }
        }
        """
        # Ensure params has 7 elements and convert to strings
        params_array = []
        for i in range(7):
            if i < len(params) and params[i] is not None:
                try:
                    # Convert to string (as per user requirement)
                    params_array.append(str(float(params[i])))
                except (ValueError, TypeError):
                    params_array.append("0")
            else:
                params_array.append("0")
        
        # Get command name from cache or API (only once per command type)
        if command not in SurveyMissionService._command_name_cache:
            # Mapping cụ thể cho các command navigation và action phổ biến
            command_name_mapping = {
                # Navigation commands
                16: "MAV_CMD_NAV_WAYPOINT",            # NAV_WAYPOINT
                20: "MAV_CMD_NAV_RETURN_TO_LAUNCH",    # NAV_RETURN_TO_LAUNCH
                21: "MAV_CMD_NAV_LAND",                # NAV_LAND
                22: "MAV_CMD_NAV_TAKEOFF",             # NAV_TAKEOFF
                # Action commands
                206: "MAV_CMD_DO_SET_CAM_TRIGG_DIST",  # DO_SET_CAMERA_TRIGG_DIST
                211: "MAV_CMD_DO_GRIPPER",             # DO_GRIPPER
                200: "MAV_CMD_DO_CONTROL_VIDEO",        # DO_CONTROL_VIDEO
                183: "MAV_CMD_DO_DIGICAM_CONTROL",      # DO_DIGICAM_CONTROL
                203: "MAV_CMD_DO_DIGICAM_CONTROL",      # DO_DIGICAM_CONTROL (standard ID)
                2000: "MAV_CMD_IMAGE_START_CAPTURE",    # IMAGE_START_CAPTURE
                2001: "MAV_CMD_IMAGE_STOP_CAPTURE",     # IMAGE_STOP_CAPTURE
            }
            
            if command in command_name_mapping:
                command_name = command_name_mapping[command]
            else:
                qgc_service = SurveyMissionService._get_qgc_service()
                command_name = qgc_service._get_command_name_from_api(command)
            
            if command_name.startswith("MAV_CMD_"):
                command_name = command_name.replace("MAV_CMD_", "").replace("_", " ").title()
            SurveyMissionService._command_name_cache[command] = command_name
        
        command_name = SurveyMissionService._command_name_cache[command]
        # Build command_line dict
        return {
            str(command): {
                command_name: params_array
            }
        }
    
    @staticmethod
    def _build_frame_data(frame_id: int) -> Dict:
        """
        Build frame data theo format: {"3": "GLOBAL_RELATIVE_ALT"}
        Same format as qground_control_service.py
        
        Example:
        {
          "3": "GLOBAL_RELATIVE_ALT"
        }
        """
        # Get frame name from cache or API (only once per frame type)
        if frame_id not in SurveyMissionService._frame_name_cache:
            qgc_service = SurveyMissionService._get_qgc_service()
            frame_name = qgc_service._get_frame_name_by_id(frame_id)
            SurveyMissionService._frame_name_cache[frame_id] = frame_name
        
        frame_name = SurveyMissionService._frame_name_cache[frame_id]
        
        # Build frame dict
        return {
            str(frame_id): frame_name
        }
    
    @staticmethod
    def _parse_command_line_from_terminal_data(command_line_raw) -> Dict:
        """
        Parse command_line from terminal data (from FE for LINE mission)
        Handles multiple formats:
        1. String JSON → parse it
        2. Dict with correct format {"16": {"WAYPOINT": [...]}} → use directly
        3. Dict with old format {"command": 16, "frame": 3, "params": [...]} → convert
        4. None/Empty → return empty dict
        
        Same logic as routes_service.py
        """
        if not command_line_raw:
            return {}
        
        # If string, parse JSON
        if isinstance(command_line_raw, str):
            try:
                command_line = json.loads(command_line_raw)
            except (json.JSONDecodeError, TypeError):
                return {}
        else:
            command_line = command_line_raw
        
        # If dict, check format
        if isinstance(command_line, dict):
            # Check if already in correct format (has string keys like "16", "22")
            if any(isinstance(k, str) and k.isdigit() for k in command_line.keys()):
                return command_line
            
            # Check if old format {"command": 16, "frame": 3, "params": [...]}
            if 'command' in command_line and 'params' in command_line:
                cmd = command_line['command']
                params = command_line['params']
                return SurveyMissionService._build_command_line(cmd, params)
        
        return {}
    
    @staticmethod
    def _parse_frame_from_terminal_data(frame_raw) -> Dict:
        """
        Parse frame from terminal data (from FE for LINE mission)
        Handles multiple formats:
        1. String JSON → parse it
        2. Dict with correct format {"3": "GLOBAL_RELATIVE_ALT"} → use directly
        3. Int → convert to correct format
        4. None/Empty → return default (GLOBAL_RELATIVE_ALT)
        """
        if not frame_raw:
            # Default: GLOBAL_RELATIVE_ALT
            return SurveyMissionService._build_frame_data(3)
        
        # If string, parse JSON
        if isinstance(frame_raw, str):
            try:
                frame_data = json.loads(frame_raw)
                if isinstance(frame_data, dict):
                    # Check if already in correct format
                    if any(isinstance(k, str) and k.isdigit() for k in frame_data.keys()):
                        return frame_data
            except (json.JSONDecodeError, TypeError):
                pass
        
        # If int, convert
        if isinstance(frame_raw, int):
            return SurveyMissionService._build_frame_data(frame_raw)
        
        # If dict, check format
        if isinstance(frame_raw, dict):
            # Check if already in correct format
            if any(isinstance(k, str) and k.isdigit() for k in frame_raw.keys()):
                return frame_raw
        
        # Default
        return SurveyMissionService._build_frame_data(3)
    
    @staticmethod
    def _extract_altitude_from_command_line(command_line: Dict) -> Optional[float]:
        """
        Extract altitude from command_line params[6] (following QGroundControlService pattern)
        Returns altitude in meters
        """
        try:
            if not command_line:
                return None
            
            # Check if already in correct format (has string keys like "16", "22")
            for command_id_str, command_data in command_line.items():
                if isinstance(command_data, dict):
                    params_array = list(command_data.values())[0]
                    if len(params_array) >= 7 and params_array[6] is not None:
                        altitude_value = float(params_array[6])
                        logger.debug(f"Extracted altitude from params[6]: {altitude_value}")
                        return altitude_value
            
            # Fallback: check params[2] if params[6] not available
            for command_id_str, command_data in command_line.items():
                if isinstance(command_data, dict):
                    params_array = list(command_data.values())[0]
                    if len(params_array) >= 3 and params_array[2] is not None:
                        altitude_value = float(params_array[2])
                        logger.debug(f"Extracted altitude from params[2]: {altitude_value}")
                        return altitude_value
            
            return None
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Error extracting altitude from command_line: {e}")
            return None
    
    @staticmethod
    def get_queryset_optimized():
        """
        Get optimized queryset with select_related and prefetch_related
        For use with apply_dynamic_filters
        Defer polygon and qgc_mission_data to reduce data size
        """
        return SurveyMission.objects.defer('polygon', 'qgc_mission_data').select_related(
            'status',
            'group',
            'approved_by',
            'rejected_by'
        ).prefetch_related('waypoints', 'measurements').annotate(
            created_by_full_name=Concat('created_by__first_name', Value(' '), 'created_by__last_name'),
            start_point=Concat(
                Cast(
                    Subquery(
                        MissionWaypoint.objects.filter(
                            mission=OuterRef('pk')
                        ).order_by('order').values('latitude')[:1]
                    ),
                    TextField()
                ),
                Value(', '),
                Cast(
                    Subquery(
                        MissionWaypoint.objects.filter(
                            mission=OuterRef('pk')
                        ).order_by('order').values('longitude')[:1]
                    ),
                    TextField()
                ),
                output_field=CharField()
            ),
            end_point=Concat(
                Cast(
                    Subquery(
                        MissionWaypoint.objects.filter(
                            mission=OuterRef('pk')
                        ).order_by('-order').values('latitude')[:1]
                    ),
                    TextField()
                ),
                Value(', '),
                Cast(
                    Subquery(
                        MissionWaypoint.objects.filter(
                            mission=OuterRef('pk')
                        ).order_by('-order').values('longitude')[:1]
                    ),
                    TextField()
                ),
                output_field=CharField()
            ),
            status__name = F('status__name'),
            status__code = F('status__code'),
            status__color_code = F('status__color_code'),

        ).all().order_by('-id')
    
    @staticmethod
    def preview(
        polygon: list,
        altitude: float,
        survey_angle: float = 0,
        frontal_overlap: float = 70,
        side_overlap: float = 70,
        entry_location: int = 1,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        return_to_home: bool = True,
        spacing: float = None,
        trigger_distance: float = None,
        turnaround_distance:float=60.96
    ) -> Tuple[bool, Any]:
        """
        Preview survey mission without saving
        Returns estimates and visualization data
        """
        try:
            builder = SurveyMissionBuilderService()
            default_cruise_speed = get_waypoint_speed()
            cruise_speed_value = cruise_speed if cruise_speed is not None and cruise_speed > 0 else default_cruise_speed
            effective_polygons, polygon_adjusted = SurveyMissionService._sanitize_polygon_points(polygon) if polygon else ([polygon], False)
            result = builder.build_survey_mission(
                polygon=polygon,
                altitude=altitude,
                survey_angle=survey_angle,
                frontal_overlap=frontal_overlap,
                side_overlap=side_overlap,
                entry_location=entry_location,
                cruise_speed=cruise_speed_value,
                hover_speed=hover_speed,
                return_to_home=return_to_home,
                spacing=spacing,
                trigger_distance=trigger_distance,
                turnaround_distance=turnaround_distance,
                polygon_components=effective_polygons,
                review=True
            )
            
            # Calculate start/end points
            start_point, end_point = SurveyMissionService._calculate_start_end_points(
                polygon, return_to_home
            )
            
            effective_polygons_output = effective_polygons or []
            effective_polygon_value = (
                effective_polygons_output[0]
                if len(effective_polygons_output) == 1
                else effective_polygons_output
            )

            return True, {
                'waypoints': result['estimates']['waypoints'],
                'distance_km': result['estimates']['distance_km'],
                'time_minutes': result['estimates']['time_minutes'],
                'coverage_km2': result['estimates']['coverage_km2'],
                'transects': result['estimates']['transects'],
                'waypoints_visualization': result['waypoints_visualization'],
                'transects_visualization': result['transects_visualization'],
                'start_point': start_point,
                'end_point': end_point,
                'effective_polygon': effective_polygon_value,
                'effective_polygons': effective_polygons_output,
                'polygon_adjusted': polygon_adjusted,
            }
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def _extract_waypoints_for_preview(qgc_mission_data: dict) -> list:
        """
        Extract simplified waypoint data for preview/mapping
        Only returns essential data needed for frontend visualization
        
        Time Complexity: O(n) where n = total waypoints
        Space Complexity: O(k) where k = navigation waypoints only
        
        Args:
            qgc_mission_data: Full QGC mission data
            
        Returns:
            List of waypoints with QGC-compatible format
        """
        if not qgc_mission_data or 'mission' not in qgc_mission_data:
            return []
        
        items = qgc_mission_data.get('mission', {}).get('items', [])
        waypoints = []
        
        # Pre-define navigation commands as set for O(1) lookup
        navigation_commands = {16, 22, 20}  # WAYPOINT, TAKEOFF, RTL
        
        # Command name mapping for quick lookup
        command_names = {
            16: "MAV_CMD_NAV_WAYPOINT",
            22: "MAV_CMD_NAV_TAKEOFF",
            20: "MAV_CMD_NAV_RETURN_TO_LAUNCH"
        }
        
        # Frame name mapping for quick lookup
        frame_names = {
            2: "MISSION",
            3: "GLOBAL_RELATIVE_ALT"
        }
        
        # O(n) - Single pass through all items
        for item in items:
            item_type = item.get('type')
            
            if item_type == 'ComplexItem':
                # Extract waypoints from survey (ComplexItem)
                transect_item = item.get('TransectStyleComplexItem')
                if not transect_item or 'Items' not in transect_item:
                    continue
                    
                survey_items = transect_item['Items']
                
                for survey_item in survey_items:
                    command = survey_item.get('command', {})
                    command_id = command.get('id') if isinstance(command, dict) else command
                    
                    # O(1) lookup in set
                    if command_id in navigation_commands:
                        params = survey_item.get('params')
                        frame = survey_item.get('frame', {})
                        frame_id = frame.get('id') if isinstance(frame, dict) else frame
                        
                        if params and len(params) >= 7:
                            waypoints.append({
                                'order': survey_item.get('doJumpId'),
                                'latitude': params[4],
                                'longitude': params[5],
                                'altitude': params[6],
                                'command': {
                                    'id': command_id,
                                    'name': command_names.get(command_id, f'MAV_CMD_{command_id}')
                                },
                                'frame': {
                                    'id': frame_id if frame_id else 3,
                                    'name': frame_names.get(frame_id if frame_id else 3, 'GLOBAL_RELATIVE_ALT')
                                },
                                'type': 'survey'
                            })
                            
            elif item_type == 'SimpleItem':
                # Extract simple waypoints
                command = item.get('command', {})
                command_id = command.get('id') if isinstance(command, dict) else command
                
                # O(1) lookup in set
                if command_id in navigation_commands:
                    params = item.get('params')
                    frame = item.get('frame', {})
                    frame_id = frame.get('id') if isinstance(frame, dict) else frame
                    
                    if params and len(params) >= 7:
                        waypoints.append({
                            'order': item.get('doJumpId'),
                            'latitude': params[4],
                            'longitude': params[5],
                            'altitude': params[6],
                            'command': {
                                'id': command_id,
                                'name': command_names.get(command_id, f'MAV_CMD_{command_id}')
                            },
                            'frame': {
                                'id': frame_id if frame_id else 3,
                                'name': frame_names.get(frame_id if frame_id else 3, 'GLOBAL_RELATIVE_ALT')
                            },
                            'type': 'simple'
                        })
        
        return waypoints
    
    @staticmethod
    def review(
        polygon: list,
        altitude: float,
        survey_angle: float = 0,
        frontal_overlap: float = 70,
        side_overlap: float = 70,
        entry_location: int = 1,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        spacing: float = None,
        trigger_distance: float = None,
        turnaround_distance:float=60.96, 
        review: bool = False,
        # QGC Survey Options
        hover_and_capture: bool = False,
        refly_90_degrees: bool = False,
        camera_trigger_in_turnaround: bool = False,
    ) -> Tuple[bool, Any]:
        """
        FAST review for mission preview without saving
        Uses optimized preview builder (10-50x faster than full build)
        
        Returns:
        - waypoints: List of navigation waypoints for mapping (lat, lon, alt, order)
        - estimates: Mission statistics (distance, time, coverage, etc.)
        - polygon: Original polygon for reference
        - terminals: List of terminals extracted from QGC plan (for custom parameters)
        
        Performance: ~50-200ms for typical polygon (vs 2000ms+ for full build)
        """
        try:
            builder = SurveyMissionBuilderService()
            return_to_home = get_return_to_home_default(default=True)
            
            # Use fast preview builder instead of full build
            effective_polygons, polygon_adjusted = SurveyMissionService._sanitize_polygon_points(polygon) if polygon else ([polygon], False)
            default_cruise_speed = get_waypoint_speed()
            # Nếu cruise_speed = None hoặc = 0 thì lấy từ config
            cruise_speed_value = cruise_speed if cruise_speed is not None and cruise_speed > 0 else default_cruise_speed

            result = builder.build_survey_preview(
                polygon=polygon,
                altitude=altitude,
                survey_angle=survey_angle,
                frontal_overlap=frontal_overlap,
                side_overlap=side_overlap,
                entry_location=entry_location,
                cruise_speed=cruise_speed_value,
                hover_speed=hover_speed,
                return_to_home=return_to_home,
                spacing=spacing,
                trigger_distance=trigger_distance,
                turnaround_distance=turnaround_distance,
                # QGC Survey Options
                hover_and_capture=hover_and_capture,
                refly_90_degrees=refly_90_degrees,
                camera_trigger_in_turnaround=camera_trigger_in_turnaround,
                polygon_components=effective_polygons,
            )
            if len(result['waypoints']) > MAXIMUM_ITEMS_PER_MISSION:
                return False, "Maximum number of items per mission exceeded"
            # Result already contains lightweight waypoints and estimates
            effective_polygons_output = effective_polygons or []
            effective_polygon_value = (
                effective_polygons_output[0]
                if len(effective_polygons_output) == 1
                else effective_polygons_output
            )
            return True, {
                'waypoints': result['waypoints'],
                'estimates': result['estimates'],
                'polygon': polygon,
                'effective_polygon': effective_polygon_value,
                'effective_polygons': effective_polygons_output,
                'polygon_adjusted': polygon_adjusted,
                'visual_transect_points': result['visual_transect_points'],
                'survey_params': {
                    'altitude': altitude,
                    'survey_angle': survey_angle,
                    'frontal_overlap': frontal_overlap,
                    'side_overlap': side_overlap,
                    'entry_location': entry_location,
                }
            }
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def _build_qgc_structure_from_waypoints(
        terminals_data: List[Dict],
        polygon: List[List[float]],
        altitude: float,
        cruise_speed: float,
        return_to_home: bool = True,
    ) -> Dict:
        """
        Build QGC mission structure from simple waypoints (no survey grid).
        Used for import routes simple feature.
        
        Args:
            terminals_data: List of terminal data with lat, lon, alt, command_line, frame
            polygon: Polygon coordinates for display
            altitude: Flight altitude
            cruise_speed: Cruise speed
            return_to_home: Whether to add RTL command
            
        Returns:
            QGC mission data structure
        """
        if not terminals_data:
            raise ValidationError("No waypoints provided")
        
        items = []
        do_jump_id = 1
        
        # 1. Camera Mode command
        items.append({
            "autoContinue": True,
            "command": 530,  # MAV_CMD_SET_CAMERA_MODE
            "doJumpId": do_jump_id,
            "frame": 2,
            "params": [0, 2, None, None, None, None, None],
            "type": "SimpleItem"
        })
        do_jump_id += 1
        
        # 2. Takeoff from first waypoint
        first_wp = terminals_data[0]
        takeoff_lat = float(first_wp.get('latitude', 0))
        takeoff_lon = float(first_wp.get('longitude', 0))
        takeoff_alt = float(first_wp.get('altitude', altitude))
        
        items.append({
            "AMSLAltAboveTerrain": None,
            "Altitude": takeoff_alt,
            "AltitudeMode": 1,
            "autoContinue": True,
            "command": 22,  # MAV_CMD_NAV_TAKEOFF
            "doJumpId": do_jump_id,
            "frame": 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
            "params": [0, 0, 0, None, takeoff_lat, takeoff_lon, takeoff_alt],
            "type": "SimpleItem"
        })
        do_jump_id += 1
        
        # 3. Build waypoint items from terminals_data
        visual_points = []
        survey_items = []
        
        for terminal_data in terminals_data:
            lat = float(terminal_data.get('latitude', 0))
            lon = float(terminal_data.get('longitude', 0))
            alt = float(terminal_data.get('altitude', altitude))
            
            # Parse command_line and frame if available
            command_line = terminal_data.get('command_line')
            frame_data = terminal_data.get('frame')
            
            # Extract command and frame
            if isinstance(command_line, dict):
                command = command_line.get('command', {}).get('value', 16) if isinstance(command_line.get('command'), dict) else command_line.get('command', 16)
            else:
                command = 16  # MAV_CMD_NAV_WAYPOINT
            
            if isinstance(frame_data, dict):
                frame = frame_data.get('frame', {}).get('value', 3) if isinstance(frame_data.get('frame'), dict) else frame_data.get('frame', 3)
            else:
                frame = 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT
            
            # Add waypoint item
            survey_items.append({
                "autoContinue": True,
                "command": command,
                "doJumpId": do_jump_id,
                "frame": frame,
                "params": [0, 0, 0, None, lat, lon, alt],
                "type": "SimpleItem"
            })
            do_jump_id += 1
            
            # Add to visual points
            visual_points.append([lat, lon])
        
        # 4. Complex item wrapper (for VisualTransectPoints)
        items.append({
            "TransectStyleComplexItem": {
                "CameraCalc": {
                    "AdjustedFootprintFrontal": 0,
                    "AdjustedFootprintSide": 0,
                    "CameraName": "Manual (no camera specs)",
                    "DistanceMode": 1,
                    "DistanceToSurface": altitude,
                    "version": 2
                },
                "CameraShots": 0,
                "CameraTriggerInTurnaround": False,
                "HoverAndCapture": False,
                "Items": survey_items,
                "Refly90Degrees": False,
                "TurnAroundDistance": 60.96,
                "VisualTransectPoints": visual_points,  # Points for frontend visualization
                "version": 2
            },
            "angle": 0,
            "complexItemType": "survey",
            "entryLocation": 1,
            "flyAlternateTransects": False,
            "polygon": polygon,
            "splitConcavePolygons": False,
            "type": "ComplexItem",
            "version": 5
        })
        
        # 5. End mission command (RTL or LAND)
        if return_to_home:
            items.append({
                "autoContinue": True,
                "command": 20,  # MAV_CMD_NAV_RETURN_TO_LAUNCH
                "doJumpId": do_jump_id,
                "frame": 2,
                "params": [0, 0, 0, 0, 0, 0, 0],
                "type": "SimpleItem"
            })
        else:
            landing_lat = takeoff_lat
            landing_lon = takeoff_lon
            try:
                if terminals_data:
                    landing_lat = float(terminals_data[-1].get('latitude', landing_lat))
                    landing_lon = float(terminals_data[-1].get('longitude', landing_lon))
            except Exception:
                pass
            items.append({
                "autoContinue": True,
                "command": 21,  # MAV_CMD_NAV_LAND
                "doJumpId": do_jump_id,
                "frame": 3,
                "params": [0, 0, 0, None, landing_lat, landing_lon, 0],
                "type": "SimpleItem"
            })
        
        return {
            "fileType": "Plan",
            "geoFence": {"circles": [], "polygons": [], "version": 2},
            "groundStation": "QGroundControl",
            "mission": {
                "cruiseSpeed": cruise_speed,
                "firmwareType": 12,
                "globalPlanAltitudeMode": 1,
                "hoverSpeed": 5.0,
                "items": items,
                "plannedHomePosition": [takeoff_lat, takeoff_lon, takeoff_alt],
                "vehicleType": 2,
                "version": 2
            },
            "rallyPoints": {"points": [], "version": 2},
            "version": 1
        }
    
    @staticmethod
    def _calculate_start_end_points(polygon: list, return_to_home: bool) -> Tuple[dict, dict]:
        """Calculate start and end points from polygon"""
        if not polygon or len(polygon) == 0:
            return {'lat': 0, 'lon': 0}, {'lat': 0, 'lon': 0}
        
        start_point = {'lat': polygon[0][0], 'lon': polygon[0][1]}
        
        if return_to_home:
            end_point = {'lat': polygon[0][0], 'lon': polygon[0][1]}
        else:
            end_point = {'lat': polygon[-1][0], 'lon': polygon[-1][1]}
        
        return start_point, end_point
    
    @staticmethod
    def _parse_qgc_items_to_waypoints(mission: SurveyMission, qgc_mission_data: dict, name: str):
        """
        Parse QGC mission items to MissionWaypoint
        For POLYGON/CIRCULAR/TRACE missions with survey data
        Uses bulk_create for performance
        Raises exception on any validation error (will trigger transaction rollback)
        """
        from ninja.errors import ValidationError
        
        if not qgc_mission_data:
            raise ValidationError("QGC mission data is required")
        
        if 'mission' not in qgc_mission_data:
            raise ValidationError("Invalid QGC mission data: missing 'mission' key")
        
        items = qgc_mission_data['mission'].get('items', [])
        if not items:
            raise ValidationError("QGC mission must contain at least one item")
        
        waypoints_to_create = []
        waypoint_altitudes = []
        order = 1
        
        for item_idx, item in enumerate(items):
            item_type = item.get('type')
            
            # Handle ComplexItem (Survey)
            if item_type == 'ComplexItem':
                transect_item = item.get('TransectStyleComplexItem')
                if not transect_item:
                    raise ValidationError(f"ComplexItem at index {item_idx} missing TransectStyleComplexItem")
                
                survey_items = transect_item.get('Items', [])
                
                # Parse each survey item (waypoints inside survey)
                for survey_idx, survey_item in enumerate(survey_items):
                    cmd = survey_item.get('command')
                    
                    # Only create waypoint for MAV_CMD_NAV_WAYPOINT (16)
                    if cmd == 16:
                        params = survey_item.get('params', [])
                        if len(params) < 7:
                            raise ValidationError(
                                f"Survey item {survey_idx} in ComplexItem {item_idx}: "
                                f"params must have at least 7 elements, got {len(params)}"
                            )
                        
                        lat = params[4]
                        lon = params[5]
                        alt = params[6]
                        
                        # Validate coordinates
                        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                            raise ValidationError(
                                f"Survey item {survey_idx}: invalid coordinate types (lat={type(lat)}, lon={type(lon)})"
                            )
                        
                        if not (-90 <= lat <= 90):
                            raise ValidationError(
                                f"Survey item {survey_idx}: latitude {lat} out of range (-90 to 90)"
                            )
                        
                        if not (-180 <= lon <= 180):
                            raise ValidationError(
                                f"Survey item {survey_idx}: longitude {lon} out of range (-180 to 180)"
                            )
                        
                        # Get frame from survey_item
                        frame_id = survey_item.get('frame', 3)  # Default: GLOBAL_RELATIVE_ALT
                        
                        waypoints_to_create.append(MissionWaypoint(
                            mission=mission,
                            order=order,
                            name=f"{name} - WP{order}",
                            latitude=lat,
                            longitude=lon,
                            command_line=SurveyMissionService._build_command_line(cmd, params),
                            frame=SurveyMissionService._build_frame_data(frame_id)
                        ))
                        waypoint_altitudes.append(alt if isinstance(alt, (int, float)) and alt > 0 else None)
                        order += 1
            
            # Handle SimpleItem (Takeoff, RTL, etc.)
            elif item_type == 'SimpleItem':
                cmd = item.get('command')
                params = item.get('params', [])
                
                # Only create waypoint for navigation commands
                # 22 = Takeoff, 20 = RTL, 16 = Waypoint
                if cmd in [22, 20, 16]:
                    if len(params) < 7:
                        raise ValidationError(
                            f"SimpleItem at index {item_idx} (command={cmd}): "
                            f"params must have at least 7 elements, got {len(params)}"
                        )
                    
                    lat = params[4]
                    lon = params[5]
                    alt = params[6]
                    
                    # Validate coordinates
                    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                        raise ValidationError(
                            f"SimpleItem {item_idx}: invalid coordinate types (lat={type(lat)}, lon={type(lon)})"
                        )
                    
                    if not (-90 <= lat <= 90):
                        raise ValidationError(
                            f"SimpleItem {item_idx}: latitude {lat} out of range (-90 to 90)"
                        )
                    
                    if not (-180 <= lon <= 180):
                        raise ValidationError(
                            f"SimpleItem {item_idx}: longitude {lon} out of range (-180 to 180)"
                        )
                    
                    # Determine name based on command
                    if cmd == 22:
                        wp_name = f"{name} - Takeoff"
                    elif cmd == 20:
                        wp_name = f"{name} - RTL"
                    else:
                        wp_name = f"{name} - WP{order}"
                    
                    # Get frame from item
                    frame_id = item.get('frame', 3)  # Default: GLOBAL_RELATIVE_ALT
                    
                    waypoints_to_create.append(MissionWaypoint(
                        mission=mission,
                        order=order,
                        name=wp_name,
                        latitude=lat,
                        longitude=lon,
                        command_line=SurveyMissionService._build_command_line(cmd, params),
                        frame=SurveyMissionService._build_frame_data(frame_id)
                    ))
                    waypoint_altitudes.append(alt if isinstance(alt, (int, float)) and alt > 0 else None)
                    order += 1
        
        if waypoints_to_create:
            MissionWaypoint.objects.bulk_create(waypoints_to_create, batch_size=500)
        
        mission.total_waypoints = order - 1
        mission.save(update_fields=['total_waypoints'])
        
        default_cruise_speed = get_waypoint_speed()
        mission_cruise_speed_measurement = mission.get_measurement('cruise_speed')
        mission_cruise_speed_value = default_cruise_speed
        if mission_cruise_speed_measurement:
            try:
                mission_cruise_speed_value = float(mission_cruise_speed_measurement.data.get('value', 0))
                if mission_cruise_speed_value <= 0:
                    mission_cruise_speed_value = default_cruise_speed
            except (ValueError, TypeError):
                mission_cruise_speed_value = default_cruise_speed
        
        mission_altitude_measurement = mission.get_measurement('altitude')
        mission_altitude_value = None
        if mission_altitude_measurement:
            try:
                mission_altitude_value = float(mission_altitude_measurement.data.get('value', 0))
                if mission_altitude_value <= 0:
                    mission_altitude_value = None
            except (ValueError, TypeError):
                mission_altitude_value = None
        
        qgc_cruise_speed = qgc_mission_data.get('mission', {}).get('cruiseSpeed')
        if qgc_cruise_speed:
            try:
                qgc_cruise_speed_float = float(qgc_cruise_speed)
                if qgc_cruise_speed_float > 0:
                    mission_cruise_speed_value = qgc_cruise_speed_float
            except (ValueError, TypeError):
                pass
        
        from devices.models import Measurement
        from django.contrib.contenttypes.models import ContentType
        
        created_waypoints = MissionWaypoint.objects.filter(
            mission=mission
        ).order_by('order')
        
        measurement_objects = []
        waypoint_content_type = ContentType.objects.get_for_model(MissionWaypoint)
        
        for idx, waypoint in enumerate(created_waypoints):
            operating_altitude_from_params = None
            if idx < len(waypoint_altitudes):
                operating_altitude_from_params = waypoint_altitudes[idx]
            
            operating_altitude_value = operating_altitude_from_params if operating_altitude_from_params else mission_altitude_value
            
            measurement_objects.append(
                Measurement(
                    content_type=waypoint_content_type,
                    object_id=waypoint.id,
                    measurement_type='cruise_speed',
                    data={
                        'type': 'simple',
                        'value': float(mission_cruise_speed_value),
                        'unit': 'm/s'
                    }
                )
            )
            
            if operating_altitude_value is not None and operating_altitude_value > 0:
                measurement_objects.append(
                    Measurement(
                        content_type=waypoint_content_type,
                        object_id=waypoint.id,
                        measurement_type='operating_altitude',
                        data={
                            'type': 'simple',
                            'value': float(operating_altitude_value),
                            'unit': 'm'
                        }
                    )
                )
        
        # Bulk create measurements
        if measurement_objects:
            Measurement.objects.bulk_create(measurement_objects, batch_size=500, ignore_conflicts=True)
    
    @staticmethod
    def _create_takeoff_land_waypoints(
        mission: SurveyMission,
        name: str,
        start_point: dict,
        end_point: dict,
        altitude: float,
        return_to_home: bool
    ):
        """
        Create Takeoff and Land waypoints for survey mission (optimized with bulk_create)
        - Takeoff: điểm đầu tiên của polygon
        - Land: điểm đầu (nếu return_to_home) hoặc điểm cuối
        """
        # 1. Create Terminal(s)
        terminals_to_create = []
        takeoff_terminal = Terminal(
            name=f"{name} - Takeoff",
            latitude=start_point['lat'],
            longitude=start_point['lon'],
        )
        terminals_to_create.append(takeoff_terminal)
        
        # Check if need separate land terminal
        need_separate_land = not return_to_home and (
            start_point['lat'] != end_point['lat'] or start_point['lon'] != end_point['lon']
        )
        
        if need_separate_land:
            land_terminal = Terminal(
                name=f"{name} - Land",
                latitude=end_point['lat'],
                longitude=end_point['lon'],
            )
            terminals_to_create.append(land_terminal)
        else:
            land_terminal = takeoff_terminal
        
        # Bulk create terminals
        Terminal.objects.bulk_create(terminals_to_create, batch_size=10)
        
        # Bulk add TEMP type to terminals (M2M relationship)
        temp_type = TerminalType.objects.get(code='TEMP')
        TerminalTerminalTypes = Terminal.terminal_types.through
        m2m_relationships = [
            TerminalTerminalTypes(terminal=term, terminaltype=temp_type)
            for term in terminals_to_create
        ]
        TerminalTerminalTypes.objects.bulk_create(m2m_relationships, batch_size=10)
        
        # 2. Bulk create waypoints
        takeoff_params = [0, 0, 0, 0, start_point['lat'], start_point['lon'], altitude]
        land_params = [0, 0, 0, 0, end_point['lat'], end_point['lon'], 0]
        
        # Default frame: GLOBAL_RELATIVE_ALT (3)
        default_frame = SurveyMissionService._build_frame_data(3)
        
        waypoints = [
            # Takeoff waypoint
            MissionWaypoint(
                mission=mission,
                terminal=takeoff_terminal,
                order=1,
                name=f"{name} - Takeoff",
                latitude=start_point['lat'],
                longitude=start_point['lon'],
                command_line=SurveyMissionService._build_command_line(22, takeoff_params),  # MAV_CMD_NAV_TAKEOFF
                frame=default_frame
            ),
            # Land waypoint
            MissionWaypoint(
                mission=mission,
                terminal=land_terminal,
                order=2,
                name=f"{name} - Land",
                latitude=end_point['lat'],
                longitude=end_point['lon'],
                command_line=SurveyMissionService._build_command_line(21, land_params),  # MAV_CMD_NAV_LAND
                frame=default_frame
            )
        ]
        
        MissionWaypoint.objects.bulk_create(waypoints, batch_size=10)
        
        # 3. Update mission total_waypoints
        mission.total_waypoints = 2
        mission.save(update_fields=['total_waypoints'])
    
    @staticmethod
    def _extract_measurements_from_terminals(terminals: List[Dict]) -> Dict[str, Optional[float]]:
        """
        Extract measurements từ terminal list
        Trả về dict với các measurements: altitude, cruise_speed, operating_altitude, hover_speed
        Nếu không có trong terminal thì trả về None
        """
        if not terminals or len(terminals) == 0:
            return {}
        
        measurements = {
            'altitude': None,
            'cruise_speed': None,
            'operating_altitude': None,
            'hover_speed': None,
        }
        
        # Collect all values from terminals
        altitude_values = []
        cruise_speed_values = []
        operating_altitude_values = []
        hover_speed_values = []
        
        for terminal in terminals:
            terminal_altitude = terminal.get('altitude')
            if terminal_altitude is not None:
                try:
                    alt_value = float(terminal_altitude)
                    if alt_value > 0:
                        altitude_values.append(alt_value)
                except (ValueError, TypeError):
                    pass
            
            terminal_operating_altitude = terminal.get('operating_altitude')
            if terminal_operating_altitude is not None:
                try:
                    op_alt_value = float(terminal_operating_altitude)
                    if op_alt_value > 0:
                        operating_altitude_values.append(op_alt_value)
                except (ValueError, TypeError):
                    pass
            
            terminal_cruise_speed = terminal.get('cruise_speed')
            if terminal_cruise_speed is not None:
                try:
                    cruise_value = float(terminal_cruise_speed)
                    if cruise_value > 0:
                        cruise_speed_values.append(cruise_value)
                except (ValueError, TypeError):
                    pass
            
            terminal_hover_speed = terminal.get('hover_speed')
            if terminal_hover_speed is not None:
                try:
                    hover_value = float(terminal_hover_speed)
                    if hover_value > 0:
                        hover_speed_values.append(hover_value)
                except (ValueError, TypeError):
                    pass
        
        if altitude_values:
            measurements['altitude'] = sum(altitude_values) / len(altitude_values)
        
        if operating_altitude_values:
            measurements['operating_altitude'] = sum(operating_altitude_values) / len(operating_altitude_values)
        elif altitude_values:
            measurements['operating_altitude'] = measurements['altitude']
        
        if cruise_speed_values:
            measurements['cruise_speed'] = sum(cruise_speed_values) / len(cruise_speed_values)
        
        if hover_speed_values:
            measurements['hover_speed'] = sum(hover_speed_values) / len(hover_speed_values)
        
        return measurements
    
    @staticmethod
    @transaction.atomic
    def create(
        name: str,
        maximum_drones: int,
        purpose_id: int,
        polygon: list = None,  # For SURVEY mission
        region: str = None,
        altitude: float = 150.0,
        takeoff_altitude: Optional[float] = None,
        altitude_separation: Optional[float] = None,
        terminals: list = None,  # For LINE mission (if provided, it's LINE)
        survey_angle: float = 0,
        frontal_overlap: float = 70,
        side_overlap: float = 70,
        entry_location: int = 1,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        log_collection: bool = False,
        video_recording: bool = False,
        video_analysis: bool = False,
        note: str = None,
        spacing: float = None,
        trigger_distance: float = None,
        turnaround_distance:float=60.96,
        # QGC Survey Options (only used for SURVEY missions with polygon)
        hover_and_capture: bool = False,
        refly_90_degrees: bool = False,
        camera_trigger_in_turnaround: bool = False,
        action_commands: list = None,  # Action commands to insert after waypoints
        from_route: bool = False,  # Flag to indicate mission is created from route
        total_distance: Optional[float] = None,  # Total distance in km (for LINE mission)
        estimated_time: Optional[float] = None,  # Estimated time in minutes (for LINE mission)
        created_by_user: Optional[CoreUser] = None  # User object for created_by
    ) -> Tuple[bool, Any]:
        """
        Create survey mission
        
        Các case tạo mission:
        1. Chỉ có terminals (LINE mission):
           - Tạo MissionWaypoint từ terminals với các thông số từ terminal
           - Không tạo QGC mission data
        
        2. Có cả terminals và polygon:
           - Dùng polygon để build QGC file (qgc_mission_data)
           - MissionWaypoint vẫn được tạo từ list terminals (KHÔNG parse từ QGC)
           - Terminals chứa các tham số custom của người dùng
        
        3. Import từ route (luôn có cả polygon và terminal):
           - Logic tương tự case 2
        
        Luồng xử lý:
        - polygon: Dùng để vẽ và tạo QGC control (QGC mission data) - chỉ khi có polygon
        - terminals: List terminal chứa các tham số custom, luôn được dùng để tạo MissionWaypoint
        
        Action commands can be added after specific waypoints (e.g., camera triggers, digicam control)
        - action_commands: List of action commands to insert after navigation waypoints
        - Each action command is inserted after the waypoint with matching doJumpId
        
        Status = pending_approval by default
        """
        try:
            return_to_home = get_return_to_home_default(default=True)
            has_polygon = polygon and len(polygon) > 0
            has_terminals = terminals and len(terminals) > 0
            
            if not has_polygon and not has_terminals:
                return False, "Either polygon (for SURVEY mission) or terminals (for LINE mission) must be provided"
            
            try:
                pending_status = SurveyMissionStatus.objects.get(code='pending_approval')
            except SurveyMissionStatus.DoesNotExist:
                return False, "Survey mission status 'pending_approval' not found. Please run migrations and init data."

            default_cruise_speed = get_waypoint_speed()
            
            terminal_measurements = {}
            if has_terminals:
                terminal_measurements = SurveyMissionService._extract_measurements_from_terminals(terminals)
            
            final_altitude = altitude
            if terminal_measurements.get('altitude'):
                final_altitude = terminal_measurements['altitude']
            elif not altitude or altitude <= 0:
                final_altitude = 150.0
            
            cruise_speed_value = cruise_speed if cruise_speed and cruise_speed > 0 else None
            if terminal_measurements.get('cruise_speed'):
                cruise_speed_value = terminal_measurements['cruise_speed']
            elif not cruise_speed_value or cruise_speed_value <= 0:
                cruise_speed_value = default_cruise_speed
            
            final_hover_speed = hover_speed
            if terminal_measurements.get('hover_speed'):
                final_hover_speed = terminal_measurements['hover_speed']
            elif not hover_speed or hover_speed <= 0:
                final_hover_speed = 5.0
            
            takeoff_altitude_value = takeoff_altitude if takeoff_altitude is not None else 100.0
            altitude_separation_value = altitude_separation if altitude_separation is not None else 10.0

            qgc_mission_data = None
            estimates = None
            effective_polygons = None
            polygon_adjusted = False
            if has_polygon:
                effective_polygons, polygon_adjusted = SurveyMissionService._sanitize_polygon_points(polygon)

            if polygon and len(polygon) > 0:
                builder = SurveyMissionBuilderService()
                result = builder.build_survey_mission(
                    polygon=polygon,
                    altitude=final_altitude,
                    survey_angle=survey_angle,
                    frontal_overlap=frontal_overlap,
                    side_overlap=side_overlap,
                    entry_location=entry_location,
                    cruise_speed=cruise_speed_value,
                    hover_speed=final_hover_speed,
                    return_to_home=return_to_home,
                    spacing=spacing,
                    trigger_distance=trigger_distance,
                    turnaround_distance=turnaround_distance,
                    review=False,
                    hover_and_capture=hover_and_capture,
                    refly_90_degrees=refly_90_degrees,
                    camera_trigger_in_turnaround=camera_trigger_in_turnaround,
                    polygon_components=effective_polygons,
                    terminals = terminals
                )
                
                qgc_mission_data = result['qgc_mission']
                if polygon_adjusted:
                    qgc_mission_data.setdefault('metadata', {})
                    effective_polygons_output = effective_polygons or []
                    effective_polygon_value = (
                        effective_polygons_output[0]
                        if len(effective_polygons_output) == 1
                        else effective_polygons_output
                    )
                    qgc_mission_data['metadata']['effective_polygon'] = effective_polygon_value
                    qgc_mission_data['metadata']['effective_polygons'] = effective_polygons_output
                estimates = result['estimates']
                
                if action_commands:
                    qgc_mission_data = SurveyMissionService._insert_action_commands(
                        qgc_mission_data, action_commands
                    )
            create_kwargs = {
                'name': name,
                'maximum_drones': maximum_drones,
                'polygon': polygon,
                'region': region,
                'log_collection': log_collection,
                'video_recording': video_recording,
                'video_analysis': video_analysis,
                'return_to_home': return_to_home,
                'status': pending_status,
                'qgc_mission_data': qgc_mission_data,
                'total_waypoints': 0,  # Will be updated after creating waypoints
                'note': note,
                'purpose_id': purpose_id,
                'from_route': from_route,
                'hover_and_capture': hover_and_capture,
            }
            
            if created_by_user:
                create_kwargs['created_by'] = created_by_user
                create_kwargs['modified_by'] = created_by_user
            
            survey_mission = SurveyMission.objects.create(**create_kwargs)
            
            if created_by_user and hasattr(created_by_user, 'userprofilelink'):
                try:
                    profile = created_by_user.userprofilelink
                    if profile and profile.group:
                        survey_mission.groups.add(profile.group)
                except Exception as e:
                    logger.warning(f"Failed to assign group to survey mission: {str(e)}")
            
            survey_mission.set_measurement('altitude', f"{final_altitude} m")
            survey_mission.set_measurement('takeoff_altitude', f"{takeoff_altitude_value} m")
            survey_mission.set_measurement('altitude_separation', f"{altitude_separation_value} m")
            survey_mission.set_measurement('cruise_speed', f"{cruise_speed_value} m/s")
            survey_mission.set_measurement('hover_speed', f"{final_hover_speed} m/s")
            
            if survey_angle is not None:
                survey_mission.set_measurement('survey_angle', f"{survey_angle} °")
            if frontal_overlap is not None:
                survey_mission.set_measurement('frontal_overlap', f"{frontal_overlap} %")
            if side_overlap is not None:
                survey_mission.set_measurement('side_overlap', f"{side_overlap} %")
            if spacing:
                survey_mission.set_measurement('spacing', f"{spacing} m")
            if trigger_distance:
                survey_mission.set_measurement('trigger_distance', f"{trigger_distance} m")
            if turnaround_distance:
                survey_mission.set_measurement('turnaround_distance', f"{turnaround_distance} m")
            
            if polygon and len(polygon) > 0 and estimates:
                survey_mission.set_measurement('total_distance', f"{estimates['distance_km']} km")
                survey_mission.set_measurement('estimated_time', f"{estimates['time_minutes']} mins")
            elif total_distance is not None:
                survey_mission.set_measurement('total_distance', f"{total_distance} km")
            if estimated_time is not None:
                survey_mission.set_measurement('estimated_time', f"{estimated_time} mins")
            
            if has_polygon and qgc_mission_data and has_terminals:
                validated_terminals = SurveyMissionService._validate_and_prepare_terminals(
                    terminals=terminals,
                    mission_name=name,
                    create_terminal_objects=False
                )
                
                SurveyMissionService._create_mission_waypoints_from_terminals(
                    survey_mission, 
                    validated_terminals, 
                    cruise_speed_value
                )
                
                survey_mission.total_waypoints = len(validated_terminals)
                survey_mission.save(update_fields=['total_waypoints'])
            elif has_polygon and qgc_mission_data and not has_terminals:
                SurveyMissionService._parse_qgc_items_to_waypoints(
                    survey_mission,
                    qgc_mission_data,
                    name
                )
            elif terminals and len(terminals) > 0:
                validated_terminals = SurveyMissionService._validate_and_prepare_terminals(
                    terminals=terminals,
                    mission_name=name,
                    create_terminal_objects=len(terminals) > 0
                )
                
                SurveyMissionService._create_mission_waypoints_from_terminals(
                    survey_mission, 
                    validated_terminals, 
                    cruise_speed_value
                )
                
                survey_mission.total_waypoints = len(validated_terminals)
                survey_mission.save(update_fields=['total_waypoints'])
                
                if has_terminals and not has_polygon:
                    if total_distance is None:
                        from geopy.distance import geodesic
                        total_distance_m = 0.0
                        if len(validated_terminals) > 1:
                            for i in range(len(validated_terminals) - 1):
                                point1 = (validated_terminals[i]['latitude'], validated_terminals[i]['longitude'])
                                point2 = (validated_terminals[i + 1]['latitude'], validated_terminals[i + 1]['longitude'])
                                total_distance_m += geodesic(point1, point2).meters
                            
                            total_distance_km = total_distance_m / 1000.0
                            survey_mission.set_measurement('total_distance', f"{total_distance_km:.2f} km")
                            
                            if estimated_time is None and cruise_speed_value > 0:
                                estimated_time_seconds = total_distance_m / cruise_speed_value
                                estimated_time_minutes = estimated_time_seconds / 60.0
                                survey_mission.set_measurement('estimated_time', f"{estimated_time_minutes:.2f} mins")
            else:
                # No terminals and no polygon waypoints
                survey_mission.total_waypoints = 0
                survey_mission.save(update_fields=['total_waypoints'])
            
            return True, survey_mission
            
        except Exception as e:
            return False, str(e)


    @staticmethod
    @transaction.atomic
    def update(
        survey_mission_id: int,
        **kwargs
    ) -> Tuple[bool, Any]:
        survey_mission = SurveyMission.objects.select_related('status').get(id=survey_mission_id)
        
        if not survey_mission.can_edit():
            return False, f"Cannot edit mission with status '{survey_mission.status.name}'"
        
        default_cruise_speed = get_waypoint_speed()

        needs_regeneration = False
        regeneration_params = [
            'polygon', 'altitude', 'survey_angle', 'frontal_overlap',
            'side_overlap', 'cruise_speed', 'hover_speed'
        ]
        
        terminals = kwargs.pop('terminals', None)
        terminals_provided = bool(terminals and len(terminals) > 0)
        
        if terminals_provided:
            is_line_mission = not (survey_mission.polygon and len(survey_mission.polygon) > 0)
            if is_line_mission:
                survey_mission.qgc_mission_data = None
            
            action_commands = kwargs.pop('action_commands', None)
            
            hover_and_capture = kwargs.get('hover_and_capture', False)
            refly_90_degrees = kwargs.pop('refly_90_degrees', False)
            camera_trigger_in_turnaround = kwargs.pop('camera_trigger_in_turnaround', False)
            
            altitude = kwargs.pop('altitude', None)
            takeoff_altitude = kwargs.pop('takeoff_altitude', None)
            altitude_separation = kwargs.pop('altitude_separation', None)
            cruise_speed = kwargs.pop('cruise_speed', None)
            hover_speed = kwargs.pop('hover_speed', None)
            survey_angle = kwargs.pop('survey_angle', None)
            frontal_overlap = kwargs.pop('frontal_overlap', None)
            side_overlap = kwargs.pop('side_overlap', None)
            spacing = kwargs.pop('spacing', None)
            trigger_distance = kwargs.pop('trigger_distance', None)
            turnaround_distance = kwargs.pop('turnaround_distance', None)
            total_distance = kwargs.pop('total_distance', None)
            estimated_time = kwargs.pop('estimated_time', None)
            if altitude is not None:
                survey_mission.set_measurement('altitude', f"{altitude} m")
                needs_regeneration = True
            if takeoff_altitude is not None:
                survey_mission.set_measurement('takeoff_altitude', f"{takeoff_altitude} m")
            elif survey_mission.get_measurement('takeoff_altitude') is None:
                survey_mission.set_measurement('takeoff_altitude', "100.0 m")
            if altitude_separation is not None:
                survey_mission.set_measurement('altitude_separation', f"{altitude_separation} m")
            elif survey_mission.get_measurement('altitude_separation') is None:
                survey_mission.set_measurement('altitude_separation', "10.0 m")
            if cruise_speed is not None:
                survey_mission.set_measurement('cruise_speed', f"{cruise_speed} m/s")
                needs_regeneration = True
            if hover_speed is not None:
                survey_mission.set_measurement('hover_speed', f"{hover_speed} m/s")
                needs_regeneration = True
            if survey_angle is not None:
                survey_mission.set_measurement('survey_angle', f"{survey_angle} °")
                needs_regeneration = True
            if frontal_overlap is not None:
                survey_mission.set_measurement('frontal_overlap', f"{frontal_overlap} %")
                needs_regeneration = True
            if side_overlap is not None:
                survey_mission.set_measurement('side_overlap', f"{side_overlap} %")
                needs_regeneration = True
            if spacing is not None:
                survey_mission.set_measurement('spacing', f"{spacing} m")
                needs_regeneration = True
            if trigger_distance is not None:
                survey_mission.set_measurement('trigger_distance', f"{trigger_distance} m")
                needs_regeneration = True
            if turnaround_distance is not None:
                survey_mission.set_measurement('turnaround_distance', f"{turnaround_distance} m")
                needs_regeneration = True
            if total_distance is not None:
                survey_mission.set_measurement('total_distance', f"{total_distance} km")
                needs_regeneration = True
            if estimated_time is not None:
                survey_mission.set_measurement('estimated_time', f"{estimated_time} mins")
                needs_regeneration = True
            # Update simple fields
            for field, value in kwargs.items():
                if value is not None and hasattr(survey_mission, field):
                    setattr(survey_mission, field, value)
                    if field in regeneration_params:
                        needs_regeneration = True
            
            should_reset_status = needs_regeneration or terminals_provided

            has_polygon = survey_mission.polygon and len(survey_mission.polygon) > 0
            should_regenerate_qgc = needs_regeneration and (not terminals_provided or has_polygon)
            
            if should_regenerate_qgc:
                altitude_measurement = survey_mission.get_measurement('altitude')
                cruise_speed_measurement = survey_mission.get_measurement('cruise_speed')
                hover_speed_measurement = survey_mission.get_measurement('hover_speed')
                survey_angle_measurement = survey_mission.get_measurement('survey_angle')
                frontal_overlap_measurement = survey_mission.get_measurement('frontal_overlap')
                side_overlap_measurement = survey_mission.get_measurement('side_overlap')
                trigger_distance_measurement = survey_mission.get_measurement('trigger_distance')
                spacing_measurement = survey_mission.get_measurement('spacing')
                turnaround_distance_measurement = survey_mission.get_measurement('turnaround_distance') 
               
                if survey_mission.polygon and len(survey_mission.polygon) > 0 and not survey_mission.from_route:
                    builder = SurveyMissionBuilderService()
                    result = builder.build_survey_mission(
                        polygon=survey_mission.polygon,
                        altitude=float(altitude_measurement.data['value']) if altitude_measurement else 200.0,
                        survey_angle=float(survey_angle_measurement.data['value']) if survey_angle_measurement else 0.0,
                        frontal_overlap=float(frontal_overlap_measurement.data['value']) if frontal_overlap_measurement else 70.0,
                        side_overlap=float(side_overlap_measurement.data['value']) if side_overlap_measurement else 70.0,
                        entry_location=kwargs.get('entry_location',1),
                        cruise_speed=float(cruise_speed_measurement.data['value']) if cruise_speed_measurement and float(cruise_speed_measurement.data['value']) > 0 else default_cruise_speed,
                        hover_speed=float(hover_speed_measurement.data['value']) if hover_speed_measurement else 5.0,
                        return_to_home=survey_mission.return_to_home,
                        spacing=float(spacing_measurement.data['value']) if spacing_measurement else None,
                        trigger_distance=float(trigger_distance_measurement.data['value']) if trigger_distance_measurement else None,
                        turnaround_distance=float(turnaround_distance_measurement.data['value']) if turnaround_distance_measurement else 60.96,
                        review=False,
                        # QGC Survey Options - use provided values or keep existing from qgc_mission_data
                        hover_and_capture=hover_and_capture if hover_and_capture is not None else survey_mission.qgc_mission_data.get('mission', {}).get('items', [{}])[0].get('TransectStyleComplexItem', {}).get('HoverAndCapture', False),
                        refly_90_degrees=refly_90_degrees if refly_90_degrees is not None else survey_mission.qgc_mission_data.get('mission', {}).get('items', [{}])[0].get('TransectStyleComplexItem', {}).get('Refly90Degrees', False),
                        camera_trigger_in_turnaround=camera_trigger_in_turnaround if camera_trigger_in_turnaround is not None else survey_mission.qgc_mission_data.get('mission', {}).get('items', [{}])[0].get('TransectStyleComplexItem', {}).get('CameraTriggerInTurnAround', False),
                        terminals = terminals,
                    )
                    
                    survey_mission.qgc_mission_data = result['qgc_mission']
                    
                    if action_commands:
                        survey_mission.qgc_mission_data = SurveyMissionService._insert_action_commands(
                            survey_mission.qgc_mission_data, action_commands
                        )
                    
                    survey_mission.set_measurement('total_distance', f"{result['estimates']['distance_km']} km")
                    survey_mission.set_measurement('estimated_time', f"{result['estimates']['time_minutes']} mins")
            
            if should_reset_status:
                try:
                    pending_status = SurveyMissionStatus.objects.get(code='pending_approval')
                    survey_mission.status = pending_status
                    # Clear approval/rejection data
                    survey_mission.approved_by = None
                    survey_mission.approved_at = None
                    survey_mission.rejected_by = None
                    survey_mission.rejected_at = None
                    survey_mission.rejection_reason = None
                except SurveyMissionStatus.DoesNotExist:
                    pass
            
            # Always delete existing MissionWaypoints to ensure clean data
            MissionWaypoint.objects.filter(mission=survey_mission).delete()
            
            if needs_regeneration and survey_mission.qgc_mission_data and not terminals_provided:
                if terminals and len(terminals) > 0:
                    cruise_speed_measurement = survey_mission.get_measurement('cruise_speed')
                    cruise_speed_value = float(cruise_speed_measurement.data['value']) if cruise_speed_measurement and float(cruise_speed_measurement.data['value']) > 0 else default_cruise_speed
                    
                    SurveyMissionService._create_mission_waypoints_from_terminals(
                        survey_mission, 
                        terminals, 
                        cruise_speed_value
                    )
                    survey_mission.total_waypoints = len(terminals)
                else:
                    extracted_terminals = SurveyMissionService._extract_terminals_from_plan(survey_mission.qgc_mission_data)
                    if extracted_terminals:
                        cruise_speed_measurement = survey_mission.get_measurement('cruise_speed')
                        cruise_speed_value = float(cruise_speed_measurement.data['value']) if cruise_speed_measurement else default_cruise_speed
                        
                        SurveyMissionService._create_mission_waypoints_from_terminals(
                            survey_mission, 
                            extracted_terminals, 
                            cruise_speed_value
                        )
                        survey_mission.total_waypoints = len(extracted_terminals)
                    else:
                        survey_mission.total_waypoints = 0
                    
            elif terminals and len(terminals) > 0:
                is_line_mission = not (survey_mission.polygon and len(survey_mission.polygon) > 0)
                
                validated_terminals = SurveyMissionService._validate_and_prepare_terminals(
                    terminals=terminals,
                    mission_name=survey_mission.name,
                    create_terminal_objects=is_line_mission
                )
                
                cruise_speed_measurement = survey_mission.get_measurement('cruise_speed')
                cruise_speed_value = float(cruise_speed_measurement.data['value']) if cruise_speed_measurement and float(cruise_speed_measurement.data['value']) > 0 else default_cruise_speed
                
                SurveyMissionService._create_mission_waypoints_from_terminals(
                    survey_mission, 
                    validated_terminals, 
                    cruise_speed_value
                )
                
                survey_mission.total_waypoints = len(validated_terminals)
            else:
                if terminals and len(terminals) > 0:
                    cruise_speed_measurement = survey_mission.get_measurement('cruise_speed')
                    cruise_speed_value = float(cruise_speed_measurement.data['value']) if cruise_speed_measurement and float(cruise_speed_measurement.data['value']) > 0 else default_cruise_speed
                    
                    SurveyMissionService._create_mission_waypoints_from_terminals(
                        survey_mission, 
                        terminals, 
                        cruise_speed_value
                    )
                    survey_mission.total_waypoints = len(terminals)
                elif survey_mission.qgc_mission_data and 'mission' in survey_mission.qgc_mission_data:
                    extracted_terminals = SurveyMissionService._extract_terminals_from_plan(survey_mission.qgc_mission_data)
                    if extracted_terminals:
                        cruise_speed_measurement = survey_mission.get_measurement('cruise_speed')
                        cruise_speed_value = float(cruise_speed_measurement.data['value']) if cruise_speed_measurement else default_cruise_speed
                        
                        SurveyMissionService._create_mission_waypoints_from_terminals(
                            survey_mission, 
                            extracted_terminals, 
                            cruise_speed_value
                        )
                        survey_mission.total_waypoints = len(extracted_terminals)
                    else:
                        survey_mission.total_waypoints = 0
                else:
                    survey_mission.total_waypoints = 0
            
            survey_mission.save()
            
            return True, survey_mission
    
    @staticmethod
    @transaction.atomic
    def approve(survey_mission_id: int, user, note: str = None) -> Tuple[bool, Any]:
        """Approve survey mission"""
        try:
            survey_mission = SurveyMission.objects.select_related('status').get(id=survey_mission_id)
            
            if not survey_mission.can_approve():
                return False, f"Cannot approve mission with status '{survey_mission.status.name}'"
            
            # Get approved status
            approved_status = SurveyMissionStatus.objects.get(code='approved')
            
            survey_mission.status = approved_status
            survey_mission.approved_by = user
            survey_mission.approved_at = timezone.now()
            # Clear rejection data if any
            survey_mission.rejected_by = None
            survey_mission.rejected_at = None
            survey_mission.rejection_reason = None
            survey_mission.is_active = True
            if note:
                existing_note = survey_mission.note or None
                survey_mission.note = existing_note
            
            survey_mission.save()
            
            return True, survey_mission
            
        except SurveyMission.DoesNotExist:
            return False, "Survey mission not found"
        except SurveyMissionStatus.DoesNotExist:
            return False, "Survey mission status 'approved' not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def reject(survey_mission_id: int, user, reason: str) -> Tuple[bool, Any]:
        """Reject survey mission with reason"""
        try:
            survey_mission = SurveyMission.objects.select_related('status').get(id=survey_mission_id)
            
            if survey_mission.status.code != 'pending_approval':
                return False, f"Can only reject missions with 'pending_approval' status"
            
            # Get rejected status
            rejected_status = SurveyMissionStatus.objects.get(code='rejected')
            
            survey_mission.status = rejected_status
            survey_mission.rejected_by = user
            survey_mission.rejected_at = timezone.now()
            survey_mission.rejection_reason = reason
            # Clear approval data if any
            survey_mission.approved_by = None
            survey_mission.approved_at = None
            survey_mission.save()
            
            return True, survey_mission
            
        except SurveyMission.DoesNotExist:
            return False, "Survey mission not found"
        except SurveyMissionStatus.DoesNotExist:
            return False, "Survey mission status 'rejected' not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def activate_missions(mission_ids: str) -> Tuple[bool, Any]:
        """Activate multiple missions (bulk action)"""
        try:
            mission_ids = mission_ids.split(",")
            missions = SurveyMission.objects.filter(
                id__in=mission_ids,
                is_active=False                
            )
            
            if not missions.exists():
                return False, "No eligible missions found for activation"
            
            for mission in missions:
                mission.is_active = True
                mission.save()
            
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS)
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def deactivate_missions(mission_ids:str) -> Tuple[bool, Any]:
        """Deactivate multiple missions (bulk action)"""
        try:
            mission_ids = mission_ids.split(",")
            missions = SurveyMission.objects.filter(
                id__in=mission_ids,
                is_active=True
            )
            
            if not missions.exists():
                return False, "No active missions found for deactivation"
            for mission in missions:
                mission.is_active = False
                mission.save()
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS)
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def delete(survey_mission_ids: List[int]) -> Tuple[bool, Any]:
        """Delete survey mission and its waypoints"""
        try:
            survey_missions = SurveyMission.objects.select_related('status').filter(id__in=survey_mission_ids)

            # Cannot delete active missions
            if survey_missions.filter(Q(is_active=True) | Q(status__code='approved')).exists():
                return False, "Cannot delete active or approved mission. Please deactivate or approve first."
            
            # Delete mission (will cascade delete MissionWaypoints)
            for survey_mission in survey_missions:
                MissionWaypoint.objects.filter(mission=survey_mission).delete()
                survey_mission.delete()
            
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
            
        except SurveyMission.DoesNotExist:
            return False, "Survey mission not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_detail(survey_mission_id: int) -> Tuple[bool, Any]:
        """Get survey mission detail"""
        try:
            waypoint_queryset = MissionWaypoint.objects.only(
                'id',
                'mission_id',
                'terminal_id',
                'order',
                'name',
                'latitude',
                'longitude',
                'command_line',
                'frame',
                'note',
                'created_on',
                'modified_on'
            ).prefetch_related('measurements').order_by('order')

            survey_mission = SurveyMission.objects.select_related(
                'status', 'group', 'approved_by', 'rejected_by'
            ).prefetch_related(
                Prefetch('waypoints', queryset=waypoint_queryset)
            ).filter(id=survey_mission_id)
            return True, survey_mission
        except SurveyMission.DoesNotExist:
            return False, "Survey mission not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def export_survey_missions_to_plans(mission_ids: List[int], create_zip: bool = True) -> Tuple[bool, Any]:
        """
        Export multiple survey missions thành danh sách file .plan hoặc ZIP file
        Giống như export_routes_to_plans
        
        Args:
            mission_ids: List ID của survey missions cần export
            create_zip: Nếu True, tạo ZIP file. Nếu False, trả về list files
            
        Returns:
            Nếu create_zip=True: (success, zip_buffer)
            Nếu create_zip=False: (success, list_of_files)
        """
        plans = []
        mission_ids = mission_ids.split(",")
        for mission_id in mission_ids:
            try:
                survey_mission = SurveyMission.objects.get(id=mission_id)
                
                # Check if mission has QGC data
                if not survey_mission.qgc_mission_data:
                    continue  # Skip mission without QGC data
                
                # Create filename
                filename = f"survey_mission_{mission_id}_{survey_mission.name.replace(' ', '_')}.plan"
                
                # Export QGC data as JSON
                file_content = json.dumps(survey_mission.qgc_mission_data, indent=2)
                
                plans.append((filename, file_content))
                
            except SurveyMission.DoesNotExist:
                continue
            except Exception as e:
                logging.error(f"Error exporting mission {mission_id}: {e}")
                continue
        
        if not plans:
            return False, "No valid missions found to export"
        
        if create_zip:
            # Create ZIP file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename, content in plans:
                    zip_file.writestr(filename, content)
            
            zip_buffer.seek(0)
            return True, zip_buffer
        else:
            # Return list of files
            return True, plans
    
    @staticmethod
    def export_single_mission_to_zip(survey_mission_id: int) -> Tuple[bool, Any]:
        """
        Export single survey mission thành ZIP file (chứa 1 file .plan)
        Useful khi cần ZIP format cho single mission
        """
        return SurveyMissionService.export_survey_missions_to_plans([survey_mission_id], create_zip=True)
    
    @staticmethod
    @transaction.atomic
    def import_plan_file(plan_file, group_id: int = None) -> Tuple[bool, Any]:
        """
        Import file .plan và tạo SurveyMission (Complex Mission only)
        
        Note: Simple Plans are NOT supported for SurveyMission import.
        Use Routes feature to create simple missions.
        
        - Complex Mission (Survey, Corridor Scan) → Tạo SurveyMission
        - Simple Plan → Return error (use Routes instead)
        
        Args:
            plan_file: File .plan được upload
            file_name: Tên file (optional, để đặt tên mission)
            group_id: Group ID để tạo mission
            
        Returns:
            Tuple (success, result) với result là SurveyMission được tạo hoặc error message
        """
        try:
            # Parse file .plan
            plan_data = SurveyMissionService._parse_plan_file(plan_file)
            
            # Validate dữ liệu
            SurveyMissionService._validate_plan_data(plan_data)
            
            # Detect plan type
            mission_items = plan_data.get('mission', {}).get('items', [])
            is_complex_mission = SurveyMissionService._is_complex_mission(mission_items)
            
            if not is_complex_mission:
                # Simple Plan NOT supported for SurveyMission
                logger.warning("⚠️ Simple Plan detected - NOT supported for SurveyMission import")
                return False, "Simple Plans are not supported for SurveyMission. Please use Routes feature to create simple missions."
            
            logger.info("📍 Detected Complex Mission - creating SurveyMission")
            file_name = f"survey_mission_{group_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.plan"
            mission_info = SurveyMissionService._extract_mission_info(plan_data, file_name)
            
            # Create SurveyMission
            survey_mission = SurveyMissionService._create_survey_mission_from_plan(
                plan_data, mission_info, group_id
            )
            
            return True, survey_mission
            
        except Exception as e:
            logger.error(f"❌ Error importing plan file: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def _parse_plan_file(plan_file) -> Dict[str, Any]:
        """Parse file .plan JSON"""
        try:
            content = plan_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValidationError(f"Error reading file: {e}")
    
    @staticmethod
    def _validate_plan_data(plan_data: Dict[str, Any]) -> None:
        """Validate plan data structure"""
        if not isinstance(plan_data, dict):
            raise ValidationError("Plan data must be a dictionary")
        
        if 'mission' not in plan_data:
            raise ValidationError("Plan data must contain 'mission' key")
        
        mission = plan_data['mission']
        if not isinstance(mission, dict):
            raise ValidationError("Mission must be a dictionary")
        
        if 'items' not in mission:
            raise ValidationError("Mission must contain 'items' key")
        
        items = mission['items']
        if not isinstance(items, list):
            raise ValidationError("Items must be a list")
        
        if not items:
            raise ValidationError("Mission must contain at least one item")
    
    @staticmethod
    def _is_complex_mission(mission_items: List[Dict]) -> bool:
        """Check if mission is complex (Survey, Corridor Scan)"""
        for item in mission_items:
            if item.get('type') == 'ComplexItem':
                return True
        return False
    
    @staticmethod
    def _extract_mission_info(plan_data: Dict[str, Any], file_name: str = None) -> Dict[str, Any]:
        """Extract mission information from plan data"""
        mission = plan_data.get('mission', {})
        purpose = MissionPurpose.objects.get(code='surveillance')
        # Extract basic info
        mission_info = {
            'name': file_name or 'Imported Mission',
            'maximum_drones': 1,
            'purpose_id': purpose.id,
            'log_collection': False,
            'video_recording': False,
            'video_analysis': False,
            'return_to_home': True,
            'note': f'Imported from {file_name or "plan file"}',
            'frontal_overlap': 70,
            'side_overlap': 70,
            'entry_location': 1,
            'hover_and_capture': False,
            'refly_90_degrees': False,
            'camera_trigger_in_turnaround': False,
        }
        
        default_cruise_speed = get_waypoint_speed()
        cruise_speed_raw = mission.get('cruiseSpeed', default_cruise_speed)
        try:
            mission_info['cruise_speed'] = float(cruise_speed_raw)
        except (TypeError, ValueError):
            mission_info['cruise_speed'] = default_cruise_speed
        mission_info['hover_speed'] = mission.get('hoverSpeed', 5.0)
        
        transect_data = SurveyMissionService._extract_transect_data_from_plan(plan_data)
        if transect_data:
            mission_info.update(transect_data)
        return mission_info
    
    @staticmethod
    def _extract_transect_data_from_plan(plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract polygon and survey parameters from TransectStyleComplexItem including QGC options"""
        mission_items = plan_data.get('mission', {}).get('items', [])
        
        for item in mission_items:
            if item.get('type') == 'ComplexItem':
                transect_item = item.get('TransectStyleComplexItem')
                if transect_item:
                    transect_data = {}
                    
                    if 'polygon' in item:
                        transect_data['polygon'] = item['polygon']
                    
                    camera_calc = transect_item.get('CameraCalc', {})
                    if camera_calc:
                        if 'DistanceToSurface' in camera_calc:
                            transect_data['altitude'] = float(camera_calc['DistanceToSurface'])
                        
                        # Extract spacing values (in meters) from QGC footprints
                        # Note: QGC stores SPACING (meters), not overlap (%)
                        if 'AdjustedFootprintFrontal' in camera_calc:
                            transect_data['trigger_distance'] = float(camera_calc['AdjustedFootprintFrontal'])
                        
                        if 'AdjustedFootprintSide' in camera_calc:
                            transect_data['spacing'] = float(camera_calc['AdjustedFootprintSide'])
                    
                    if 'angle' in item:
                        transect_data['survey_angle'] = float(item['angle'])
                    
                    if 'entryLocation' in item:
                        transect_data['entry_location'] = int(item['entryLocation'])
                    
                    # Extract QGC Survey Options from TransectStyleComplexItem
                    if 'HoverAndCapture' in transect_item:
                        transect_data['hover_and_capture'] = bool(transect_item['HoverAndCapture'])
                    
                    if 'Refly90Degrees' in transect_item:
                        transect_data['refly_90_degrees'] = bool(transect_item['Refly90Degrees'])
                    
                    if 'CameraTriggerInTurnAround' in transect_item:
                        transect_data['camera_trigger_in_turnaround'] = bool(transect_item['CameraTriggerInTurnAround'])
                    
                    # Set defaults nếu không tìm thấy
                    transect_data.setdefault('altitude', 200.0)
                    transect_data.setdefault('survey_angle', 0.0)
                    transect_data.setdefault('entry_location', 1)
                    # trigger_distance and spacing will be extracted from QGC file
                    # If not found, will be calculated from overlap in build_survey_mission
                    transect_data.setdefault('hover_and_capture', False)
                    transect_data.setdefault('refly_90_degrees', False)
                    transect_data.setdefault('camera_trigger_in_turnaround', False)
                    
                    return transect_data
        
        # Return defaults nếu không tìm thấy TransectStyleComplexItem
        return {
            'altitude': 200.0,
            'survey_angle': 0.0,
            'entry_location': 1,
            'hover_and_capture': False,
            'refly_90_degrees': False,
            'camera_trigger_in_turnaround': False
        }
    
    @staticmethod
    def _create_survey_mission_from_plan(plan_data: Dict[str, Any], mission_info: Dict[str, Any], group_id: int) -> SurveyMission:
        """Create SurveyMission from plan data với đầy đủ logic như hàm create"""
        
        # Get pending_approval status
        try:
            pending_status = SurveyMissionStatus.objects.get(code='pending_approval')
        except SurveyMissionStatus.DoesNotExist:
            raise ValidationError("Survey mission status 'pending_approval' not found. Please run migrations and init data.")
        
        # Extract terminals từ TransectStyleComplexItem (giống logic create)
        terminals = SurveyMissionService._extract_terminals_from_plan(plan_data)
        
        if not terminals:
            raise ValidationError("No waypoints found in plan file")

        default_cruise_speed = get_waypoint_speed()
        
        # Create SurveyMission
        survey_mission = SurveyMission.objects.create(
            name=mission_info['name'],
            group_id=group_id,
            maximum_drones=mission_info['maximum_drones'],
            purpose_id=mission_info['purpose_id'],
            polygon=mission_info.get('polygon'),
            log_collection=mission_info['log_collection'],
            video_recording=mission_info['video_recording'],
            video_analysis=mission_info['video_analysis'],
            return_to_home=mission_info['return_to_home'],
            status=pending_status,
            qgc_mission_data=plan_data,  # Store original QGC data
            total_waypoints=len(terminals),  # Count from terminals
            note=mission_info['note'],
        )
        # Set measurements (giống logic create)
        survey_mission.set_measurement('altitude', f"{mission_info['altitude']} m")
        survey_mission.set_measurement('cruise_speed', f"{mission_info['cruise_speed']} m/s")
        survey_mission.set_measurement('hover_speed', f"{mission_info['hover_speed']} m/s")
        survey_mission.set_measurement('survey_angle', f"{mission_info['survey_angle']} °")
        survey_mission.set_measurement('frontal_overlap', f"{mission_info['frontal_overlap']} %")
        survey_mission.set_measurement('side_overlap', f"{mission_info['side_overlap']} %")
        
        # Calculate total_distance and estimated_time from terminals
        total_distance_km = 0.0
        if len(terminals) > 1:
            from geopy.distance import geodesic
            for i in range(len(terminals) - 1):
                current = terminals[i]
                next_terminal = terminals[i + 1]
                
                # Extract lat/lon from terminal
                current_lat = current.get('latitude')
                current_lon = current.get('longitude')
                next_lat = next_terminal.get('latitude')
                next_lon = next_terminal.get('longitude')
                
                if all([current_lat, current_lon, next_lat, next_lon]):
                    distance = geodesic((current_lat, current_lon), (next_lat, next_lon)).km
                    total_distance_km += distance
        
        # Calculate estimated time (distance_km * 1000 / cruise_speed / 60)
        cruise_speed_value = mission_info.get('cruise_speed', default_cruise_speed)
        try:
            cruise_speed_value = float(cruise_speed_value)
            if cruise_speed_value <= 0:
                cruise_speed_value = default_cruise_speed
        except (TypeError, ValueError):
            cruise_speed_value = default_cruise_speed

        estimated_time_minutes = int((total_distance_km * 1000) / cruise_speed_value / 60) if cruise_speed_value > 0 else 0

        if total_distance_km > 0:
            survey_mission.set_measurement('total_distance', f"{round(total_distance_km, 2)} km")
        if estimated_time_minutes > 0:
            survey_mission.set_measurement('estimated_time', f"{estimated_time_minutes} mins")
       
        SurveyMissionService._create_mission_waypoints_from_terminals(survey_mission, terminals, float(cruise_speed_value))
        
        survey_mission.save()
        
        return survey_mission
    
    @staticmethod
    def _extract_terminals_from_plan(plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract terminals từ plan data bao gồm takeoff, land và tất cả waypoints trong TransectStyleComplexItem"""
        terminals = []
        last_lat = None
        last_lon = None
        last_alt = None
        
        mission_items = plan_data.get('mission', {}).get('items', [])
        
        all_waypoints = []
        for item in mission_items:
            if item.get('type') == 'SimpleItem':
                all_waypoints.append(item)
            elif item.get('type') == 'ComplexItem':
                transect_item = item.get('TransectStyleComplexItem')
                if transect_item and 'Items' in transect_item:
                    all_waypoints.extend(transect_item['Items'])
        
        for item in mission_items:
            if item.get('type') == 'SimpleItem':
                command = item.get('command')
                if command in [22, 20]:
                    command_line = SurveyMissionService._build_command_line(command, item.get('params', []))
                    frame_data = SurveyMissionService._build_frame_data(item.get('frame', 3))
                    
                    if len(item['params']) > 4 and item['params'][4] is not None and item['params'][4] != 0:
                        lat = item['params'][4]
                        lon = item['params'][5] if len(item['params']) > 5 else last_lon
                        alt = item['params'][6] if len(item['params']) > 6 else last_alt
                    else:
                        found_lat = None
                        found_lon = None
                        found_alt = None
                        
                        for wp in reversed(all_waypoints):
                            wp_params = wp.get('params', [])
                            if (len(wp_params) > 4 and 
                                wp_params[4] is not None and 
                                wp_params[4] != 0 and 
                                wp_params[5] is not None and 
                                wp_params[5] != 0):
                                found_lat = wp_params[4]
                                found_lon = wp_params[5]
                                found_alt = wp_params[6] if len(wp_params) > 6 and wp_params[6] is not None else 0
                                break
                        
                        lat = found_lat if found_lat is not None else last_lat
                        lon = found_lon if found_lon is not None else last_lon
                        alt = found_alt if found_alt is not None else last_alt
                    
                    terminal = {
                        'latitude': lat,
                        'longitude': lon,
                        'altitude': alt,
                        'command': command,
                        'frame': item['frame'],
                        'command_line': command_line,  
                        'frame_data': frame_data,  
                    }
                    terminals.append(terminal)
                    
                    if lat is not None:
                        last_lat = lat
                        last_lon = lon
                        last_alt = alt
            
            elif item.get('type') == 'ComplexItem':
                transect_item = item.get('TransectStyleComplexItem')
                if transect_item and 'Items' in transect_item:
                    for waypoint_item in transect_item['Items']:
                        if waypoint_item.get('type') == 'SimpleItem':
                            command_line = SurveyMissionService._build_command_line(
                                waypoint_item['command'], 
                                waypoint_item.get('params', [])
                            )
                            frame_data = SurveyMissionService._build_frame_data(waypoint_item.get('frame', 3))
                            
                            command = waypoint_item['command']
                            
                            if command in [16]:
                                lat = waypoint_item['params'][4]
                                lon = waypoint_item['params'][5]
                                alt = waypoint_item['params'][6]
                            elif command in [206]:
                                lat = last_lat
                                lon = last_lon
                                alt = last_alt
                            else:
                                lat = waypoint_item['params'][4] if len(waypoint_item['params']) > 4 else last_lat
                                lon = waypoint_item['params'][5] if len(waypoint_item['params']) > 5 else last_lon
                                alt = waypoint_item['params'][6] if len(waypoint_item['params']) > 6 else last_alt
                            
                            terminal = {
                                'latitude': lat,
                                'longitude': lon,
                                'altitude': alt,
                                'command': command,
                                'frame': waypoint_item['frame'],
                                'command_line': command_line,
                                'frame_data': frame_data,
                            }
                            terminals.append(terminal)
                            
                            if lat is not None:
                                last_lat = lat
                                last_lon = lon
                                last_alt = alt
        
        return terminals
    
    @staticmethod
    def _get_temp_terminal_type_id() -> int:
        """Get TEMP terminal type ID"""
        try:
            temp_type = TerminalType.objects.get(code='TEMP')
            return temp_type.id
        except TerminalType.DoesNotExist:
            return 1
    
    @staticmethod
    def _get_terminal_type_from_command(command: int) -> int:
        """Get terminal type ID from MAVLink command"""
        try:
            takeoff_type = TerminalType.objects.get(code='takeoff')
            waypoint_type = TerminalType.objects.get(code='waypoint')
            return_type = TerminalType.objects.get(code='return')
            
            if command == 22:
                return takeoff_type.id
            elif command == 20:
                return return_type.id
            elif command == 16:
                return waypoint_type.id
            else:
                return waypoint_type.id
                
        except TerminalType.DoesNotExist:
            # Fallback nếu không tìm thấy terminal types
            return 1  # Assume waypoint type ID = 1
    
    @staticmethod
    def _validate_and_prepare_terminals(
        terminals: List[Dict[str, Any]],
        mission_name: str,
        create_terminal_objects: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Validate và prepare terminals cho cả LINE và POLYGON missions
        Nếu create_terminal_objects=True (LINE mission), sẽ tạo Terminal objects
        
        Args:
            terminals: List of terminal data từ FE
            mission_name: Tên mission để đặt tên terminal nếu cần
            create_terminal_objects: Có tạo Terminal objects không (LINE mission cần)
            
        Returns:
            List of validated terminals với terminal_id mapping nếu cần
        """
        from ninja.errors import ValidationError
        from terminals.models import Terminal, TerminalType
        
        if not terminals:
            return []
        
        validated_terminals = []
        terminal_mapping = {}  # Map index to terminal object (cho LINE mission)
        
        # Step 1: Collect existing terminals (cho LINE mission)
        existing_terminal_ids = [t.get('terminal_id') for t in terminals if t.get('terminal_id')]
        existing_terminals = {}
        if create_terminal_objects and existing_terminal_ids:
            for term in Terminal.objects.filter(id__in=existing_terminal_ids):
                existing_terminals[term.id] = term
        
        # Step 2: Validate và prepare terminals
        terminals_to_create = []
        for idx, terminal_data in enumerate(terminals, start=1):
            # Validate terminal data
            lat = terminal_data.get('latitude')
            lon = terminal_data.get('longitude')
            
            if lat is None:
                raise ValidationError(f"Terminal {idx}: latitude is required")
            if lon is None:
                raise ValidationError(f"Terminal {idx}: longitude is required")
            
            # # Validate coordinate types
            # if not isinstance(lat, (int, float)):
            #     raise ValidationError(f"Terminal {idx}: latitude must be a number, got {type(lat)}")
            # if not isinstance(lon, (int, float)):
            #     raise ValidationError(f"Terminal {idx}: longitude must be a number, got {type(lon)}")
            # Validate coordinate ranges
            if float(lat) is not None and not (-90 <= float(lat) <= 90):
                raise ValidationError(f"Terminal {idx}: latitude {lat} out of range (-90 to 90)")
            if float(lon) is not None and not (-180 <= float(lon) <= 180):
                raise ValidationError(f"Terminal {idx}: longitude {lon} out of range (-180 to 180)")
            
            # Prepare terminal data
            validated_terminal = terminal_data.copy()
            
            # Cho LINE mission: tạo Terminal objects
            if create_terminal_objects:
                terminal_id = terminal_data.get('terminal_id')
                if terminal_id and terminal_id in existing_terminals:
                    existing_terminal = existing_terminals[terminal_id]
                    terminal_mapping[idx] = existing_terminal
                    validated_terminal['_terminal_object'] = existing_terminal
                    validated_terminal['terminal_id'] = existing_terminal.id
                else:
                    # Will create new terminal
                    new_terminal = Terminal(
                        name=terminal_data.get('name', f"{mission_name} - WP{idx}"),
                        latitude=str(lat),
                        longitude=str(lon),
                        note=terminal_data.get('note'),
                    )
                    terminals_to_create.append((idx, new_terminal))
                    validated_terminal['_terminal_object'] = new_terminal
                    # terminal_id sẽ được gán sau khi bulk_create
            
            validated_terminals.append(validated_terminal)
        
        # Step 3: Bulk create Terminal objects nếu cần (cho LINE mission)
        if create_terminal_objects and terminals_to_create:
            new_terminal_objects = [t[1] for t in terminals_to_create]
            Terminal.objects.bulk_create(new_terminal_objects, batch_size=100)
            
            # Query lại để lấy các terminal đã tạo với IDs
            # Map dựa trên name, latitude, longitude để lấy đúng IDs
            terminal_names = [t[1].name for t in terminals_to_create]
            created_terminals_map = {}
            for terminal in Terminal.objects.filter(name__in=terminal_names).order_by('-id'):
                # Tạo key dựa trên name, latitude, longitude để map chính xác
                key = (terminal.name, terminal.latitude, terminal.longitude)
                # Chỉ lấy terminal đầu tiên (mới nhất) nếu có duplicate
                if key not in created_terminals_map:
                    created_terminals_map[key] = terminal
            
            # Bulk add TEMP type to new terminals
            temp_type = TerminalType.objects.get(code='TEMP')
            TerminalTerminalTypes = Terminal.terminal_types.through
            m2m_relationships = []
            # Map index trong validated_terminals với index trong terminals_to_create
            validated_idx_map = {}  # Map từ terminal data key đến index trong validated_terminals
            for v_idx, validated_terminal in enumerate(validated_terminals):
                if validated_terminal.get('_terminal_object'):
                    # Tạo key từ dữ liệu terminal để map
                    key = (
                        validated_terminal.get('name'),
                        str(validated_terminal.get('latitude')),
                        str(validated_terminal.get('longitude'))
                    )
                    validated_idx_map[key] = v_idx
            
            for idx, terminal_obj in terminals_to_create:
                # Tìm terminal đã tạo với ID
                key = (terminal_obj.name, terminal_obj.latitude, terminal_obj.longitude)
                created_terminal = created_terminals_map.get(key)
                if created_terminal:
                    terminal_mapping[idx] = created_terminal
                    m2m_relationships.append(
                        TerminalTerminalTypes(terminal=created_terminal, terminaltype=temp_type)
                    )
                    # Cập nhật terminal_id vào validated_terminal dựa trên key
                    validated_idx = validated_idx_map.get(key)
                    if validated_idx is not None:
                        validated_terminals[validated_idx]['terminal_id'] = created_terminal.id
                        validated_terminals[validated_idx]['_terminal_object'] = created_terminal
            
            if m2m_relationships:
                TerminalTerminalTypes.objects.bulk_create(m2m_relationships, batch_size=100)
        return validated_terminals
    
    @staticmethod
    def _create_mission_waypoints_from_terminals(
        survey_mission: SurveyMission,
        terminals: List[Dict[str, Any]],
        cruise_speed: Optional[float] = None
    ) -> None:
        """Create MissionWaypoint objects từ terminals với bulk operations tối ưu"""
        
        if not terminals:
            return
        
        default_cruise_speed = get_waypoint_speed()
        # Nếu cruise_speed = None hoặc = 0 thì lấy từ config
        cruise_speed_value = cruise_speed if cruise_speed and cruise_speed > 0 else default_cruise_speed
        
        # Tối ưu: Tạo MissionWaypoint trực tiếp mà không cần Terminal objects
        # Vì MissionWaypoint có thể hoạt động độc lập với Terminal
        mission_waypoint_objects = []
        
        for i, terminal_data in enumerate(terminals):
            # Parse command_line (handle multiple formats)
            command_line = SurveyMissionService._parse_command_line_from_terminal_data(
                terminal_data.get('command_line')
            )
            
            # Parse frame (handle multiple formats)
            frame_data = SurveyMissionService._parse_frame_from_terminal_data(
                terminal_data.get('frame')
            )
            
            # Nếu không có frame_data, tạo default frame
            if not frame_data:
                frame_data = SurveyMissionService._build_frame_data(3)  # Default: GLOBAL_RELATIVE_ALT
            
            # Get terminal object nếu có (cho LINE mission)
            terminal_obj = terminal_data.get('_terminal_object')
            
            mission_waypoint = MissionWaypoint(
                name=terminal_data.get('name', f"Waypoint {i + 1}"),
                mission=survey_mission,
                terminal=terminal_obj,  # Có thể None cho POLYGON mission
                order=i + 1,
                latitude=str(terminal_data['latitude']) if terminal_data.get('latitude') else "0.0",
                longitude=str(terminal_data['longitude']) if terminal_data.get('longitude') else "0.0",  
                command_line=command_line,
                frame=frame_data,
                note=terminal_data.get('note'),
            )
            mission_waypoint_objects.append(mission_waypoint)
        
        # Bulk create MissionWaypoint objects with batching for large datasets
        if mission_waypoint_objects:
            # Use batch_size to prevent timeout with large datasets
            # For hover_and_capture missions, waypoints can reach 10,000+
            batch_size = 1000
            MissionWaypoint.objects.bulk_create(mission_waypoint_objects, batch_size=batch_size)
            
            created_waypoints = MissionWaypoint.objects.filter(
                mission=survey_mission
            ).order_by('order')
            
            from devices.models import Measurement
            from django.contrib.contenttypes.models import ContentType
            
            measurement_objects = []
            waypoint_content_type = ContentType.objects.get_for_model(MissionWaypoint)
            
            mission_altitude_measurement = survey_mission.get_measurement('altitude')
            mission_altitude_value = None
            if mission_altitude_measurement:
                try:
                    mission_altitude_value = float(mission_altitude_measurement.data.get('value', 0))
                except (ValueError, TypeError):
                    mission_altitude_value = None
            
            for waypoint, terminal_data in zip(created_waypoints, terminals):
                terminal_cruise_speed = terminal_data.get('cruise_speed')
                if terminal_cruise_speed is not None:
                    try:
                        if isinstance(terminal_cruise_speed, str):
                            terminal_cruise_speed = terminal_cruise_speed.strip()
                        cruise_speed_for_waypoint = float(terminal_cruise_speed)
                        if cruise_speed_for_waypoint <= 0:
                            cruise_speed_for_waypoint = cruise_speed_value
                    except (ValueError, TypeError):
                        cruise_speed_for_waypoint = cruise_speed_value
                else:
                    cruise_speed_for_waypoint = cruise_speed_value
                
                terminal_operating_altitude = terminal_data.get('operating_altitude')
                terminal_altitude = terminal_data.get('altitude')
                
                if terminal_operating_altitude is not None:
                    try:
                        if isinstance(terminal_operating_altitude, str):
                            terminal_operating_altitude = terminal_operating_altitude.strip()
                        operating_altitude_value = float(terminal_operating_altitude)
                        if operating_altitude_value <= 0:
                            operating_altitude_value = None
                    except (ValueError, TypeError):
                        operating_altitude_value = None
                else:
                    operating_altitude_value = None
                
                if operating_altitude_value is None or operating_altitude_value <= 0:
                    if terminal_altitude is not None:
                        try:
                            if isinstance(terminal_altitude, str):
                                terminal_altitude = terminal_altitude.strip()
                            operating_altitude_value = float(terminal_altitude)
                            if operating_altitude_value <= 0:
                                operating_altitude_value = None
                        except (ValueError, TypeError):
                            operating_altitude_value = None
                
                if operating_altitude_value is None or operating_altitude_value <= 0:
                    operating_altitude_value = mission_altitude_value if mission_altitude_value and mission_altitude_value > 0 else None
                
                if cruise_speed_for_waypoint is None or cruise_speed_for_waypoint <= 0:
                    cruise_speed_for_waypoint = cruise_speed_value
                
                measurement_objects.append(
                    Measurement(
                        content_type=waypoint_content_type,
                        object_id=waypoint.id,
                        measurement_type='cruise_speed',
                        data={
                            'type': 'simple',
                            'value': float(cruise_speed_for_waypoint),
                            'unit': 'm/s'
                        }
                    )
                )
                
                if operating_altitude_value is not None and operating_altitude_value > 0:
                    measurement_objects.append(
                        Measurement(
                            content_type=waypoint_content_type,
                            object_id=waypoint.id,
                            measurement_type='operating_altitude',
                            data={
                                'type': 'simple',
                                'value': float(operating_altitude_value),
                                'unit': 'm'
                            }
                        )
                    )
            
            if measurement_objects:
                Measurement.objects.bulk_create(measurement_objects, batch_size=batch_size, ignore_conflicts=True)

    @staticmethod
    def _detect_polygon_from_route_terminals(route_terminals, single_route: bool = False) -> List[List[float]]:
        """
        Detect polygon from list RouteTerminal
        
        Args:
            route_terminals: QuerySet or List of RouteTerminal objects
            single_route: True if only 1 route, False if multiple routes
            
        Returns:
            List[List[float]]: Polygon format [[lat, lon], ...]
        """
        points = []
        for route_terminal in route_terminals:
            terminal = route_terminal.terminal
            if not terminal:
                continue
            
            try:
                lat = float(terminal.latitude) if terminal.latitude else None
                lon = float(terminal.longitude) if terminal.longitude else None
                
                if lat is None or lon is None:
                    continue
                
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    continue
                
                points.append([lat, lon])
            except (ValueError, TypeError):
                continue
        
        if len(points) < 3:
            # Nếu không đủ điểm, trả về empty polygon
            return []
        
        # Luôn tính convex hull từ tất cả điểm (cho cả single_route và multiple routes)
        # Để đảm bảo polygon chỉ có vài điểm bao bọc tối ưu, không phải tất cả các điểm
        from shapely.geometry import MultiPoint
        
        try:
            # Chuyển sang format (lon, lat) cho shapely
            shapely_points = [(lon, lat) for lat, lon in points]
            multipoint = MultiPoint(shapely_points)
            convex_hull = multipoint.convex_hull
            
            # Lấy các điểm trên convex hull
            if hasattr(convex_hull, 'exterior'):
                # Polygon
                hull_coords = list(convex_hull.exterior.coords)
            else:
                # LineString (ít điểm)
                hull_coords = list(convex_hull.coords)
            
            # Chuyển về dạng list [[lat, lon], ...]
            polygon = [[float(lat), float(lon)] for lon, lat in hull_coords]
            
            # Đảm bảo polygon đóng (điểm đầu = điểm cuối)
            if polygon and polygon[0] != polygon[-1]:
                polygon.append(polygon[0])
            
            return polygon
        except Exception as e:
            logger.error(f"Error calculating convex hull: {e}")
            # Fallback: trả về bounding box (4 điểm)
            if len(points) >= 2:
                lats = [p[0] for p in points]
                lons = [p[1] for p in points]
                return [
                    [min(lats), min(lons)],
                    [max(lats), min(lons)],
                    [max(lats), max(lons)],
                    [min(lats), max(lons)],
                    [min(lats), min(lons)]  # Đóng polygon
                ]
            return []
    
    @staticmethod
    def _create_mission_from_imported_routes(
        name: str,
        purpose_id: int,
        route_ids: List[int],
        routes: List[Routes],
        route_terminals_map: Dict[int, List[RouteTerminal]],
        polygon: List[List[float]],
        terminals_data: List[Dict[str, Any]],
        altitude: float = 150.0,
        takeoff_altitude: Optional[float] = None,
        altitude_separation: Optional[float] = None,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        log_collection: bool = False,
        video_recording: bool = False,
        video_analysis: bool = False,
        return_to_home: bool = True,
        note: str = None,
        total_distance: Optional[float] = None,
        estimated_time: Optional[float] = None,
        group_id: Optional[int] = None,
        created_by_user: Optional[CoreUser] = None
    ) -> SurveyMission:
        """
        Tạo mission từ imported routes - Logic hoàn toàn tách biệt với create method
        Lưu trữ thông tin về các route được import vào drone_segments để giữ nguyên đường bay khi tạo profile
        """
        from terminals.models import Routes, RouteTerminal
        from surveillance.models import MissionWaypoint
        
        try:
            pending_status = SurveyMissionStatus.objects.get(code='pending_approval')
        except SurveyMissionStatus.DoesNotExist:
            raise ValidationError("Survey mission status 'pending_approval' not found. Please run migrations and init data.")
        
        # 1. Tạo SurveyMission object
        survey_mission = SurveyMission(
            name=name,
            created_by=created_by_user,
            maximum_drones=len(route_ids),
            purpose_id=purpose_id,
            polygon=polygon,
            status=pending_status,
            log_collection=log_collection,
            video_recording=video_recording,
            video_analysis=video_analysis,
            return_to_home=return_to_home,
            note=note,
            from_route=True,
            group_id=group_id,
        )
        
        
        survey_mission.save()
        
        # 2. Tạo MissionWaypoint objects trước để có waypoint_order
        # Tạo route_order_map trước khi sử dụng
        route_order_map = {route_id: idx + 1 for idx, route_id in enumerate(route_ids)}
        
        # Tạo map từ route_terminal_id -> terminal_data để lookup nhanh
        terminal_data_map = {td.get('_route_terminal_id'): td for td in terminals_data}
        
        default_cruise_speed = get_waypoint_speed()
        cruise_speed_value = cruise_speed if cruise_speed and cruise_speed > 0 else default_cruise_speed
        
        mission_waypoint_objects = []
        waypoint_order = 1
        route_waypoint_ranges = {}  # route_id -> (start_order, end_order)
        
        # Tạo waypoints theo thứ tự route_ids và order trong mỗi route
        for route_id in route_ids:
            route_terminals = route_terminals_map.get(route_id, [])
            route_order = route_order_map[route_id]
            
            # Sort route_terminals theo order
            route_terminals = sorted(route_terminals, key=lambda rt: rt.order)
            
            segment_start_order = waypoint_order
            
            for route_terminal in route_terminals:
                terminal_data = terminal_data_map.get(route_terminal.id)
                if not terminal_data:
                    continue
                
                # Parse command_line và frame
                command_line = SurveyMissionService._parse_command_line_from_terminal_data(
                    terminal_data.get('command_line')
                )
                frame_data = SurveyMissionService._parse_frame_from_terminal_data(
                    terminal_data.get('frame')
                )
                if not frame_data:
                    frame_data = SurveyMissionService._build_frame_data(3)
                
                # Get terminal object
                terminal_obj = terminal_data.get('_terminal_object')
                
                mission_waypoint = MissionWaypoint(
                    name=terminal_data.get('name', f"Waypoint {waypoint_order}"),
                    mission=survey_mission,
                    terminal=terminal_obj,
                    order=waypoint_order,
                    latitude=str(terminal_data['latitude']) if terminal_data.get('latitude') else "0.0",
                    longitude=str(terminal_data['longitude']) if terminal_data.get('longitude') else "0.0",
                    command_line=command_line,
                    frame=frame_data,
                    note=terminal_data.get('note'),
                )
                mission_waypoint_objects.append(mission_waypoint)
                waypoint_order += 1
            
            segment_end_order = waypoint_order - 1
            route_waypoint_ranges[route_id] = (segment_start_order, segment_end_order)
        
        # Bulk create waypoints
        if mission_waypoint_objects:
            batch_size = 1000
            MissionWaypoint.objects.bulk_create(mission_waypoint_objects, batch_size=batch_size)
        
        # 3. Build drone_segments từ routes với start_waypoint_order và end_waypoint_order
        route_order_map = {route_id: idx + 1 for idx, route_id in enumerate(route_ids)}
        drone_segments = []
        
        for route in routes:
            route_order = route_order_map[route.id]
            route_terminals = route_terminals_map.get(route.id, [])
            
            # Lấy terminals_data cho route này
            route_terminals_data = [td for td in terminals_data if td.get('_route_id') == route.id]
            
            # Lấy waypoint range cho route này
            start_order, end_order = route_waypoint_ranges.get(route.id, (None, None))
            
            # Tính distance và estimated_time từ route measurements
            route_distance = 0.0
            route_time = 0.0
            try:
                distance_measurement = route.get_measurement('total_distance')
                if distance_measurement:
                    route_distance = distance_measurement.get_numeric_value(user_units='km') or 0.0
                
                time_measurement = route.get_measurement('estimated_time')
                if time_measurement:
                    route_time = time_measurement.get_numeric_value(user_units='mins') or 0.0
            except Exception:
                pass
            
            # Build QGC mission từ route terminals
            route_qgc_mission = None
            if route_terminals_data:
                route_qgc_mission = SurveyMissionService._build_qgc_structure_from_waypoints(
                    terminals_data=route_terminals_data,
                    polygon=polygon,
                    altitude=altitude,
                    cruise_speed=cruise_speed if cruise_speed and cruise_speed > 0 else get_waypoint_speed(),
                    return_to_home=return_to_home,
                )
            
            segment_data = {
                'area_index': route_order - 1,  # area_index bắt đầu từ 0
                'route_id': route.id,
                'route_name': route.name,
                'altitude': altitude,
                'estimated_duration': route_time,
                'distance_km': route_distance,
                'start_waypoint_order': start_order,
                'end_waypoint_order': end_order,
            }
            drone_segments.append(segment_data)
        
        survey_mission.drone_segments = drone_segments
        survey_mission.save()  # Save để lưu drone_segments
        
        # 4. Create measurements cho waypoints
        if mission_waypoint_objects:
            created_waypoints = MissionWaypoint.objects.filter(
                mission=survey_mission
            ).order_by('order')
            
            from devices.models import Measurement
            from django.contrib.contenttypes.models import ContentType
            
            measurement_objects = []
            waypoint_content_type = ContentType.objects.get_for_model(MissionWaypoint)
            
            for waypoint, terminal_data in zip(created_waypoints, terminals_data):
                # Extract cruise_speed
                terminal_cruise_speed = terminal_data.get('cruise_speed')
                if terminal_cruise_speed is not None:
                    try:
                        if isinstance(terminal_cruise_speed, str):
                            terminal_cruise_speed = terminal_cruise_speed.strip()
                        cruise_speed_for_waypoint = float(terminal_cruise_speed)
                        if cruise_speed_for_waypoint <= 0:
                            cruise_speed_for_waypoint = cruise_speed_value
                    except (ValueError, TypeError):
                        cruise_speed_for_waypoint = cruise_speed_value
                else:
                    cruise_speed_for_waypoint = cruise_speed_value
                
                # Extract operating_altitude
                terminal_operating_altitude = terminal_data.get('operating_altitude')
                terminal_altitude = terminal_data.get('altitude')
                
                operating_altitude_value = None
                if terminal_operating_altitude is not None:
                    try:
                        if isinstance(terminal_operating_altitude, str):
                            terminal_operating_altitude = terminal_operating_altitude.strip()
                        operating_altitude_value = float(terminal_operating_altitude)
                        if operating_altitude_value <= 0:
                            operating_altitude_value = None
                    except (ValueError, TypeError):
                        operating_altitude_value = None
                
                if operating_altitude_value is None or operating_altitude_value <= 0:
                    if terminal_altitude is not None:
                        try:
                            if isinstance(terminal_altitude, str):
                                terminal_altitude = terminal_altitude.strip()
                            operating_altitude_value = float(terminal_altitude)
                            if operating_altitude_value <= 0:
                                operating_altitude_value = None
                        except (ValueError, TypeError):
                            operating_altitude_value = None
                
                if operating_altitude_value is None or operating_altitude_value <= 0:
                    operating_altitude_value = altitude
                
                # Create measurements
                measurement_objects.append(
                    Measurement(
                        content_type=waypoint_content_type,
                        object_id=waypoint.id,
                        measurement_type='cruise_speed',
                        data={
                            'type': 'simple',
                            'value': float(cruise_speed_for_waypoint),
                            'unit': 'm/s'
                        }
                    )
                )
                
                if operating_altitude_value and operating_altitude_value > 0:
                    measurement_objects.append(
                        Measurement(
                            content_type=waypoint_content_type,
                            object_id=waypoint.id,
                            measurement_type='operating_altitude',
                            data={
                                'type': 'simple',
                                'value': float(operating_altitude_value),
                                'unit': 'm'
                            }
                        )
                    )
            
            if measurement_objects:
                Measurement.objects.bulk_create(measurement_objects, batch_size=batch_size, ignore_conflicts=True)
        
        # 4. Set mission-level measurements
        survey_mission.set_measurement('altitude', f"{altitude} m")
        if takeoff_altitude:
            survey_mission.set_measurement('takeoff_altitude', f"{takeoff_altitude} m")
        if altitude_separation:
            survey_mission.set_measurement('altitude_separation', f"{altitude_separation} m")
        if total_distance:
            survey_mission.set_measurement('total_distance', f"{total_distance} km")
        if estimated_time:
            survey_mission.set_measurement('estimated_time', f"{estimated_time} mins")
        
        # 5. Build QGC structure từ waypoints
        qgc_mission_data = SurveyMissionService._build_qgc_structure_from_waypoints(
            terminals_data=terminals_data,
            polygon=polygon,
            altitude=altitude,
            cruise_speed=cruise_speed_value,
            return_to_home=return_to_home,
        )
        survey_mission.qgc_mission_data = qgc_mission_data
        survey_mission.total_waypoints = len(terminals_data)
        survey_mission.save()
        
        return survey_mission

    
    @staticmethod
    @transaction.atomic
    def import_routes_to_mission(
        name: str,
        purpose_id: int,
        route_ids: List[int],
        altitude: float = 150.0,
        takeoff_altitude: Optional[float] = None,
        altitude_separation: Optional[float] = None,
        survey_angle: float = 0.0,
        frontal_overlap: float = 70.0,
        side_overlap: float = 70.0,
        entry_location: int = 1,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        log_collection: bool = False,
        video_recording: bool = False,
        video_analysis: bool = False,
        note: str = None,
        spacing: float = None,
        trigger_distance: float = None,
        turnaround_distance: float = 60.96,
        hover_and_capture: bool = False,
        refly_90_degrees: bool = False,
        camera_trigger_in_turnaround: bool = False,
        action_commands: list = None,
        total_distance: Optional[float] = None,
        estimated_time: Optional[float] = None,
        group_id: Optional[int] = None,
        created_by_user: Optional[CoreUser] = None
    ) -> Tuple[bool, Any]:
        """
        Import nhiều route thành 1 mission
        Tất cả RouteTerminal từ các route sẽ được chuyển thành MissionWaypoint
        Polygon sẽ được detect tự động từ RouteTerminal:
        - Nếu chỉ có 1 route: giữ nguyên polygon từ các điểm RouteTerminal theo thứ tự
        - Nếu có nhiều route: tính convex hull từ tất cả điểm
        
        maximum_drones sẽ tự động = số lượng route import vào
        
        Tất cả logic được bọc trong transaction, nếu có lỗi sẽ tự động rollback.
        
        Args:
            name: Tên mission
            purpose_id: ID của purpose
            route_ids: Danh sách route IDs để import
            ... (các tham số khác giống create method)
            
        Returns:
            Tuple[bool, Any]: (success, result)
            
        Raises:
            ValidationError: Nếu có lỗi validation, sẽ trigger rollback
        """
        from terminals.models import Routes, RouteTerminal
        return_to_home = get_return_to_home_default(default=True)
        
        # Get default cruise_speed từ config
        default_cruise_speed = get_waypoint_speed()
        
        # 1. Validate routes tồn tại và active
        routes = Routes.objects.filter(id__in=route_ids, is_active=True)
        if routes.count() != len(route_ids):
            missing_ids = set(route_ids) - set(routes.values_list('id', flat=True))
            raise ValidationError(f"Some routes not found or not active: {missing_ids}")
        
        # 2. maximum_drones = số lượng route import vào
        maximum_drones = len(route_ids)
        
        # 3. Lấy tất cả RouteTerminal từ các route, sắp xếp theo route và order
        route_terminals = RouteTerminal.objects.filter(
            route_id__in=route_ids
        ).select_related('terminal').order_by('route_id', 'order')
        
        if not route_terminals.exists():
            raise ValidationError("No route terminals found in the selected routes")
        
        # 4. Detect polygon từ RouteTerminal
        # Nếu chỉ có 1 route, giữ nguyên polygon từ các điểm theo thứ tự
        # Nếu có nhiều route, tính convex hull
        single_route = len(route_ids) == 1
        polygon = SurveyMissionService._detect_polygon_from_route_terminals(
            route_terminals, 
            single_route=single_route
        )
        
        if not polygon:
            raise ValidationError("Cannot create polygon from route terminals")
        
        # 5. Convert RouteTerminal thành terminals format và group theo route
        terminals_data = []
        route_terminals_map = {}  # Map route_id -> list of RouteTerminal
        
        for route_terminal in route_terminals:
            route_id = route_terminal.route_id
            if route_id not in route_terminals_map:
                route_terminals_map[route_id] = []
            route_terminals_map[route_id].append(route_terminal)
            
            terminal = route_terminal.terminal
            if not terminal:
                logger.warning(f"RouteTerminal {route_terminal.id} has no terminal, skipping")
                continue
            
            # Validate terminal coordinates
            try:
                lat = float(terminal.latitude) if terminal.latitude else None
                lon = float(terminal.longitude) if terminal.longitude else None
                
                if lat is None or lon is None:
                    logger.warning(f"Terminal {terminal.id} has invalid coordinates, skipping")
                    continue
                
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    logger.warning(f"Terminal {terminal.id} has coordinates out of range, skipping")
                    continue
            except (ValueError, TypeError) as e:
                logger.warning(f"Terminal {terminal.id} has invalid coordinate format: {e}, skipping")
                continue
            
            # Extract measurements từ RouteTerminal
            cruise_speed_value = None
            operating_altitude_value = None
            
            try:
                cruise_speed_measurement = route_terminal.measurements.filter(measurement_type="cruise_speed").first()
                if cruise_speed_measurement:
                    cruise_speed_value = cruise_speed_measurement.get_numeric_value(user_units='m/s')
                    if not cruise_speed_value or cruise_speed_value <= 0:
                        cruise_speed_value = default_cruise_speed
                
                operating_altitude_measurement = route_terminal.measurements.filter(measurement_type="operating_altitude").first()
                if operating_altitude_measurement:
                    operating_altitude_value = operating_altitude_measurement.get_numeric_value(user_units='m')
            except Exception as e:
                logger.warning(f"Error extracting measurements from RouteTerminal {route_terminal.id}: {e}")
            
            terminal_data = {
                'terminal_id': terminal.id,
                'latitude': lat,
                'longitude': lon,
                'name': terminal.name or f"Waypoint {len(terminals_data) + 1}",
                'order': len(terminals_data) + 1,
                'command_line': route_terminal.command_line,
                'frame': route_terminal.frame,
                'cruise_speed': cruise_speed_value,
                'altitude': operating_altitude_value,
                'operating_altitude': operating_altitude_value,
                'note': terminal.note,
                '_route_terminal_id': route_terminal.id,
                '_route_id': route_id,
                '_terminal_object': terminal,
            }
            
            terminals_data.append(terminal_data)
        
        if not terminals_data:
            raise ValidationError("No valid terminals with coordinates found in the selected routes")
        
        # 6. Xử lý cruise_speed: nếu = None hoặc = 0 thì lấy từ config
        cruise_speed_to_use = cruise_speed if cruise_speed and cruise_speed > 0 else default_cruise_speed
        
        # 7. Tạo mission bằng method riêng cho import routes (hoàn toàn tách biệt với create)
        try:
            result = SurveyMissionService._create_mission_from_imported_routes(
                name=name,
                purpose_id=purpose_id,
                route_ids=route_ids,
                routes=list(routes),
                route_terminals_map=route_terminals_map,
                polygon=polygon,
                terminals_data=terminals_data,
                altitude=altitude,
                takeoff_altitude=takeoff_altitude,
                altitude_separation=altitude_separation,
                cruise_speed=cruise_speed_to_use,
                hover_speed=hover_speed,
                log_collection=log_collection,
                video_recording=video_recording,
                video_analysis=video_analysis,
                return_to_home=return_to_home,
                note=note,
                total_distance=total_distance,
                estimated_time=estimated_time,
                group_id=group_id,
                created_by_user=created_by_user
            )
            return True, result
        except Exception as e:
            logger.error(f"Error creating mission from imported routes: {e}")
            raise ValidationError(f"Failed to create mission from imported routes: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def import_routes_to_mission_simple(
        name: str,
        purpose_id: int,
        route_ids: List[int],
        altitude: float = 150.0,
        takeoff_altitude: Optional[float] = None,
        altitude_separation: Optional[float] = None,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        log_collection: bool = False,
        video_recording: bool = False,
        video_analysis: bool = False,
        note: str = None,
        total_distance: Optional[float] = None,
        estimated_time: Optional[float] = None,
        created_by_user: Optional[CoreUser] = None  # User object for created_by
    ) -> Tuple[bool, Any]:
        """
        Import môt hoặc nhiều route thành 1 mission (Simple mode)
        - Chỉ tạo polygon bao bọc các route (không tính toán survey grid)
        - Số lượng MissionWaypoint = số lượng RouteTerminal
        - Vị trí và thứ tự theo route_ids truyền vào (ví dụ: [102, 103, 101] → bay từ 102 → 103 → 101)
        - Tất cả thông số waypoint lấy từ RouteTerminal
        - Chỉ thông số mission level lấy từ schema hoặc default
        
        Tất cả logic được bọc trong transaction, nếu có lỗi sẽ tự động rollback.
        
        Args:
            name: Tên mission
            purpose_id: ID của purpose
            route_ids: Danh sách route IDs để import (thứ tự quyết định thứ tự đường bay)
            ... (các tham số khác giống create method)
            
        Returns:
            Tuple[bool, Any]: (success, result)
            
        Raises:
            ValidationError: Nếu có lỗi validation, sẽ trigger rollback
        """
        from terminals.models import Routes, RouteTerminal
        return_to_home = get_return_to_home_default(default=True)
        

        default_cruise_speed = get_waypoint_speed()
        
      
        routes = Routes.objects.filter(id__in=route_ids, is_active=True).prefetch_related('measurements')
        if routes.count() != len(route_ids):
            missing_ids = set(route_ids) - set(routes.values_list('id', flat=True))
            raise ValidationError(f"Some routes not found or not active: {missing_ids}")
        

        total_distance_sum = 0.0  # km
        estimated_time_sum = 0.0  # mins
        
        for route in routes:

            total_distance_measurement = route.get_measurement('total_distance')
            if total_distance_measurement:
                try:
                    distance_value = total_distance_measurement.get_numeric_value(user_units='km')
                    if distance_value and distance_value > 0:
                        total_distance_sum += distance_value
                except Exception as e:
                    logger.warning(f"Error extracting total_distance from route {route.id}: {e}")

            estimated_time_measurement = route.get_measurement('estimated_time')
            if estimated_time_measurement:
                try:
                    time_value = estimated_time_measurement.get_numeric_value(user_units='mins')
                    if time_value and time_value > 0:
                        estimated_time_sum += time_value
                except Exception as e:
                    logger.warning(f"Error extracting estimated_time from route {route.id}: {e}")

        maximum_drones = len(route_ids)
        

        from django.db.models import Case, When, IntegerField
        
        route_order_map = {route_id: idx for idx, route_id in enumerate(route_ids)}
        route_order_case = Case(
            *[When(route_id=route_id, then=idx) for route_id, idx in route_order_map.items()],
            default=9999,
            output_field=IntegerField()
        )
        
        route_terminals = RouteTerminal.objects.filter(
            route_id__in=route_ids
        ).select_related('terminal').annotate(
            route_order=route_order_case
        ).order_by('route_order', 'order') 
        
        if not route_terminals.exists():
            raise ValidationError("No route terminals found in the selected routes")
        
   
        polygon = SurveyMissionService._detect_polygon_from_route_terminals(
            route_terminals, 
            single_route=len(route_ids) == 1
        )
        if not polygon:
            raise ValidationError("Cannot create polygon from route terminals")
        

        terminals_data = []
        for route_terminal in route_terminals:
            terminal = route_terminal.terminal
            if not terminal:
                logger.warning(f"RouteTerminal {route_terminal.id} has no terminal, skipping")
                continue
            
    
            try:
                lat = float(terminal.latitude) if terminal.latitude else None
                lon = float(terminal.longitude) if terminal.longitude else None
                
                if lat is None or lon is None:
                    logger.warning(f"Terminal {terminal.id} has invalid coordinates, skipping")
                    continue
                
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    logger.warning(f"Terminal {terminal.id} has coordinates out of range, skipping")
                    continue
            except (ValueError, TypeError) as e:
                logger.warning(f"Terminal {terminal.id} has invalid coordinate format: {e}, skipping")
                continue
            

            cruise_speed_value = None
            operating_altitude_value = None
            
            try:
                cruise_speed_measurement = route_terminal.measurements.filter(measurement_type="cruise_speed").first()
                if cruise_speed_measurement:
                    cruise_speed_value = cruise_speed_measurement.get_numeric_value(user_units='m/s')
                    if not cruise_speed_value or cruise_speed_value <= 0:
                        cruise_speed_value = default_cruise_speed
                
                operating_altitude_measurement = route_terminal.measurements.filter(measurement_type="operating_altitude").first()
                if operating_altitude_measurement:
                    operating_altitude_value = operating_altitude_measurement.get_numeric_value(user_units='m')
            except Exception as e:
                logger.warning(f"Error extracting measurements from RouteTerminal {route_terminal.id}: {e}")
            

            terminal_data = {
                'terminal_id': None, 
                'latitude': lat,
                'longitude': lon,
                'name': terminal.name or f"Waypoint {len(terminals_data) + 1}",
                'order': len(terminals_data) + 1,  # Reorder từ 1 theo thứ tự route_ids
                'command_line': route_terminal.command_line,
                'frame': route_terminal.frame,
                'cruise_speed': cruise_speed_value if cruise_speed_value else default_cruise_speed,
                'altitude': operating_altitude_value,
                'operating_altitude': operating_altitude_value,
                'note': terminal.note,
                '_route_terminal_id': route_terminal.id,
                '_route_id': route_terminal.route_id,
                '_terminal_object': terminal,
            }
            
            terminals_data.append(terminal_data)
        
        if not terminals_data:
            raise ValidationError("No valid terminals with coordinates found in the selected routes")
        
        cruise_speed_to_use = cruise_speed if cruise_speed and cruise_speed > 0 else default_cruise_speed
        
        # Group terminals_data theo route_id để build route_terminals_map
        route_terminals_map = {}
        for terminal_data in terminals_data:
            route_id = terminal_data.get('_route_id')
            if route_id:
                if route_id not in route_terminals_map:
                    route_terminals_map[route_id] = []
                # Tìm RouteTerminal object từ route_terminal_id
                route_terminal_id = terminal_data.get('_route_terminal_id')
                if route_terminal_id:
                    try:
                        route_terminal = RouteTerminal.objects.select_related('terminal').get(id=route_terminal_id)
                        route_terminals_map[route_id].append(route_terminal)
                    except RouteTerminal.DoesNotExist:
                        logger.warning(f"RouteTerminal {route_terminal_id} not found")
        
        # Gọi _create_mission_from_imported_routes để build drone_segments
        try:
            result = SurveyMissionService._create_mission_from_imported_routes(
                name=name,
                purpose_id=purpose_id,
                route_ids=route_ids,
                routes=list(routes),
                route_terminals_map=route_terminals_map,
                polygon=polygon,
                terminals_data=terminals_data,
                altitude=altitude,
                takeoff_altitude=takeoff_altitude,
                altitude_separation=altitude_separation,
                cruise_speed=cruise_speed_to_use,
                hover_speed=hover_speed,
                log_collection=log_collection,
                video_recording=video_recording,
                video_analysis=video_analysis,
                return_to_home=return_to_home,
                note=note,
                total_distance=total_distance if total_distance else total_distance_sum,
                estimated_time=estimated_time if estimated_time else estimated_time_sum,
                created_by_user=created_by_user,
                group_id=created_by_user.userprofilelink.group.id if created_by_user and created_by_user.userprofilelink and created_by_user.userprofilelink.group else None
            )
            return True, result
        except Exception as e:
            logger.error(f"Error creating mission from imported routes (simple): {e}")
            raise ValidationError(f"Failed to create mission from imported routes: {str(e)}")
        

    @staticmethod
    @transaction.atomic
    def import_from_qgc_calculated_data(
        name: str,
        purpose_id: int,
        polygon: List[List[float]],
        drone_missions: List[Dict],
        maximum_drones: int,
        survey_config: Optional[Dict] = None,
        survey_id: Optional[str] = None,
        color: Optional[str] = None,
        total_distance: Optional[str] = None,
        total_distance_km: Optional[str] = None,
        estimated_time: Optional[str] = None,
        log_collection: bool = False,
        video_recording: bool = False,
        video_analysis: bool = False,
        from_route: bool = False,
        note: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> Tuple[bool, Any]:
        """
        Import survey mission từ QGC calculated data với drone_missions
        
        Args:
            name: Tên mission
            purpose_id: ID của purpose
            polygon: Polygon coordinates
            drone_missions: List các drone mission với QGC data
            maximum_drones: Số lượng drone tối đa
            survey_config: Config của survey
            ... (các tham số khác)
            
        Returns:
            Tuple[bool, Any]: (success, result)
        """
        from surveillance.models import SurveyMissionStatus
        
        try:
            return_to_home = get_return_to_home_default(default=True)
            # 1. Validate data
            if not drone_missions:
                raise ValidationError("drone_missions không được để trống")
            
            if not polygon or len(polygon) < 3:
                raise ValidationError("polygon phải có ít nhất 3 điểm")
            
            # 2. Get default status
            default_status = SurveyMissionStatus._base_manager.filter(code='pending_approval').first()
            if not default_status:
                raise ValidationError("Không tìm thấy status 'draft'")
            
            # 3. Parse measurements từ strings
            altitude_value = None
            if survey_config:
                altitude_value = survey_config.get('altitude')
                if altitude_value:
                    try:
                        altitude_value = float(altitude_value)
                    except (ValueError, TypeError):
                        altitude_value = None
            
            if not altitude_value or altitude_value <= 0:
                # Lấy từ drone_missions đầu tiên
                if drone_missions and len(drone_missions) > 0:
                    first_drone_mission = drone_missions[0]
                    altitude_value = first_drone_mission.get('altitude')
                    if altitude_value:
                        try:
                            altitude_value = float(altitude_value)
                        except (ValueError, TypeError):
                            altitude_value = 50.0  # Default
                    else:
                        altitude_value = 50.0
                else:
                    altitude_value = 50.0
            
            # Không parse total_distance và estimated_time từ input
            # Sẽ tính lại từ dữ liệu waypoints thực tế
            
            # 4. Create SurveyMission
            polygon = [[lat, lon] for lon, lat in polygon]
            user = CoreUser._base_manager.filter(userprofilelink__group_id=group_id).first()
            if not user:
                raise ValidationError("User not found")
            survey_mission = SurveyMission(
                name=name,
                maximum_drones=maximum_drones,
                purpose_id=purpose_id,
                polygon=polygon,
                status=default_status,
                log_collection=log_collection,
                video_recording=video_recording,
                video_analysis=video_analysis,
                return_to_home=return_to_home,
                from_route=from_route,
                note=note or "",
                created_by = user,
                modified_by = user
            )
            
            # Set group_id nếu có
            if group_id:
                try:
                    survey_mission.group_id = int(group_id)
                except (ValueError, TypeError):
                    pass
            
            survey_mission.save()
            
            # 5. Parse QGC items từ drone_missions và tạo waypoints
            all_waypoints = []
            drone_segments = []
            current_order = 1
            
            for idx, drone_mission in enumerate(drone_missions):
                qgc_mission = drone_mission.get('qgc_mission', {})
                if not qgc_mission:
                    continue
                
                mission_items = qgc_mission.get('mission', {}).get('items', [])
                if not mission_items:
                    continue
                
                # Tính số lượng waypoint từ items (tất cả items có coordinate)
                waypoint_count = 0
                start_order = current_order
                
                # Parse và tạo waypoints cho TẤT CẢ items
                # LƯU Ý quan trọng:
                # - QGC SimpleItem "params" KHÔNG phải lúc nào cũng chứa (lat, lon) ở [4],[5].
                #   Ví dụ MAV_CMD_DO_DIGICAM_CONTROL (203): params[4] = 1 là trigger (param5),
                #   nên nếu đọc như latitude sẽ tạo ra point "lat=1, lon=0" => vẽ map sai.
                # - Vì vậy chỉ các NAV command mới được đọc lat/lon từ params; action commands
                #   sẽ kế thừa lat/lon từ waypoint NAV gần nhất.
                total_items = 0
                skipped_items = []
                last_valid_lat = None
                last_valid_lon = None
                last_valid_alt = None

                # Navigation commands which actually define a geographic waypoint in params[4], params[5]
                # (Takeoff/Waypoint/Land). RTL often uses zeros and should inherit last valid.
                nav_commands_with_coord = {16, 21, 22}
                nav_commands_without_coord = {20}  # RTL
                
                for item_idx, item in enumerate(mission_items):
                    item_type = item.get('type')
                    
                    # Chỉ xử lý SimpleItem
                    if item_type == 'SimpleItem':
                        # Parse command - giống logic review mission
                        command_raw = item.get('command')
                        if isinstance(command_raw, dict):
                            command = command_raw.get('id') or command_raw.get('value', 16)
                        elif isinstance(command_raw, (int, str)):
                            try:
                                command = int(command_raw)
                            except (ValueError, TypeError):
                                command = 16
                        else:
                            command = 16
                        
                        # Parse frame - giống logic review mission
                        frame_raw = item.get('frame', 3)
                        if isinstance(frame_raw, dict):
                            frame_id = frame_raw.get('id') or frame_raw.get('value', 3)
                        elif isinstance(frame_raw, (int, str)):
                            try:
                                frame_id = int(frame_raw)
                            except (ValueError, TypeError):
                                frame_id = 3
                        else:
                            frame_id = 3
                        
                        params = item.get('params', [])
                        
                        if len(params) < 7:
                            skipped_items.append(f"item {item_idx} (command {command}): params length < 7")
                            continue
                        
                        raw_lat = params[4]
                        raw_lon = params[5]
                        raw_alt = params[6]

                        use_lat = None
                        use_lon = None
                        use_alt = None

                        # 1) NAV commands with real coordinates in params
                        if command in nav_commands_with_coord:
                            if not isinstance(raw_lat, (int, float)) or not isinstance(raw_lon, (int, float)):
                                skipped_items.append(f"item {item_idx} (command {command}): invalid coordinate types")
                                continue

                            # Some NAV items might still have (0,0) - fall back to last valid
                            if raw_lat == 0 and raw_lon == 0:
                                if last_valid_lat is None or last_valid_lon is None:
                                    skipped_items.append(
                                        f"item {item_idx} (command {command}): NAV item has (0,0) but no previous coordinate"
                                    )
                                    continue
                                use_lat, use_lon = last_valid_lat, last_valid_lon
                                use_alt = last_valid_alt if last_valid_alt is not None else raw_alt
                            # Validate range for real coordinates
                            elif -90 <= raw_lat <= 90 and -180 <= raw_lon <= 180:
                                use_lat, use_lon = raw_lat, raw_lon
                                use_alt = raw_alt
                                last_valid_lat, last_valid_lon, last_valid_alt = use_lat, use_lon, use_alt
                            else:
                                skipped_items.append(
                                    f"item {item_idx} (command {command}): coordinates out of range (lat={raw_lat}, lon={raw_lon})"
                                )
                                continue

                        # 2) NAV commands without coordinates (e.g., RTL) OR any action command (DO_* etc.)
                        else:
                            if last_valid_lat is None or last_valid_lon is None:
                                skipped_items.append(
                                    f"item {item_idx} (command {command}): non-NAV item but no previous coordinate to inherit"
                                )
                                continue
                            use_lat, use_lon = last_valid_lat, last_valid_lon
                            # keep altitude stable as well
                            use_alt = last_valid_alt if last_valid_alt is not None else raw_alt
                        
                        # Tạo waypoint với coordinate đã xác định
                        if use_lat is not None and use_lon is not None:
                            total_items += 1
                            
                            # Xác định tên waypoint dựa trên command
                            if command == 22:
                                wp_name = f"{name} - Takeoff"
                            elif command == 20:
                                wp_name = f"{name} - RTL"
                            elif command == 21:
                                wp_name = f"{name} - Land"
                            else:
                                wp_name = f"{name} - WP{current_order}"
                            
                            # Build command_line và frame - giống logic review mission
                            command_line = SurveyMissionService._build_command_line(command, params)
                            frame_data = SurveyMissionService._build_frame_data(frame_id)
                            
                            all_waypoints.append(MissionWaypoint(
                                mission=survey_mission,
                                order=current_order,
                                name=wp_name,
                                latitude=str(use_lat),
                                longitude=str(use_lon),
                                command_line=command_line,
                                frame=frame_data
                            ))
                            waypoint_count += 1
                            current_order += 1
                
                end_order = current_order - 1
                
                # Debug: print để kiểm tra
                print(f"\n=== DEBUG Drone mission {idx} ===")
                print(f"Tổng items đã xử lý: {total_items}")
                print(f"Số lượng waypoint đã tạo: {waypoint_count}")
                print(f"Start order: {start_order}, End order: {end_order}")
                print(f"Last valid coordinate: ({last_valid_lat}, {last_valid_lon})")
                
                if skipped_items:
                    print(f"⚠️ Đã bỏ qua {len(skipped_items)} items không hợp lệ:")
                    for skipped in skipped_items[:10]:
                        print(f"  - {skipped}")
                    if len(skipped_items) > 10:
                        print(f"  ... và {len(skipped_items) - 10} items khác")
                
                # Validate: số lượng waypoint phải bằng số lượng items đã xử lý
                if waypoint_count != total_items:
                    print(f"❌ LỖI: Số lượng waypoint ({waypoint_count}) KHÔNG KHỚP với số lượng items ({total_items})")
                else:
                    print(f"✅ OK: Số lượng waypoint khớp với số lượng items")
                print("=" * 50)
                
                # Tạo drone_segment
                segment_data = {
                    'area_index': idx,
                    'drone_id': drone_mission.get('drone_id', 'None'),
                    'altitude': drone_mission.get('altitude', altitude_value),
                    'estimated_duration': drone_mission.get('estimated_duration', 0),
                    # 'qgc_mission': qgc_mission,
                    'start_waypoint_order': start_order if waypoint_count > 0 else None,
                    'end_waypoint_order': end_order if waypoint_count > 0 else None,
                }
                drone_segments.append(segment_data)
            
            # 6. Bulk create waypoints
            if all_waypoints:
                MissionWaypoint.objects.bulk_create(all_waypoints, batch_size=500)
                survey_mission.total_waypoints = len(all_waypoints)
                print(f"\n=== TỔNG KẾT ===")
                print(f"Tổng số waypoint đã tạo: {len(all_waypoints)}")
                print(f"Số lượng drone missions: {len(drone_missions)}")
                print(f"Tổng số drone_segments: {len(drone_segments)}")
                print("=" * 50)
            else:
                print("⚠️ CẢNH BÁO: Không có waypoint nào được tạo từ QGC mission items")
            
            # 7. Set drone_segments
            survey_mission.drone_segments = drone_segments
            survey_mission.save()
            
            # 8. Build QGC mission data từ tất cả waypoints (cho mission tổng)
            # Lấy cruise_speed từ survey_config hoặc từ drone_missions đầu tiên
            cruise_speed = 15.0  # Default
            if survey_config:
                # Không có cruise_speed trong survey_config, lấy từ QGC
                pass
            
            # Lấy từ QGC mission đầu tiên
            if drone_missions and len(drone_missions) > 0:
                first_qgc = drone_missions[0].get('qgc_mission', {})
                if first_qgc:
                    cruise_speed = first_qgc.get('mission', {}).get('cruiseSpeed', 15.0)
            
            # Build QGC structure từ waypoints
            terminals_data = []
            for wp in all_waypoints:
                terminals_data.append({
                    'latitude': float(wp.latitude),
                    'longitude': float(wp.longitude),
                    'altitude': altitude_value,
                })
            
            qgc_mission_data = SurveyMissionService._build_qgc_structure_from_waypoints(
                terminals_data=terminals_data,
                polygon=polygon,
                altitude=altitude_value,
                cruise_speed=cruise_speed,
                return_to_home=return_to_home,
            )
            survey_mission.qgc_mission_data = qgc_mission_data
            survey_mission.save()
            
            # 9. Set measurements
            survey_mission.set_measurement('altitude', f"{altitude_value} m")
            
            if survey_config:
                takeoff_altitude = survey_config.get('takeoff_altitude')
                if takeoff_altitude:
                    try:
                        takeoff_altitude_value = float(takeoff_altitude)
                        survey_mission.set_measurement('takeoff_altitude', f"{takeoff_altitude_value} m")
                    except (ValueError, TypeError):
                        pass
                
                altitude_separation = survey_config.get('takeoff_altitude_separation')
                if altitude_separation:
                    try:
                        altitude_separation_value = float(altitude_separation)
                        survey_mission.set_measurement('altitude_separation', f"{altitude_separation_value} m")
                    except (ValueError, TypeError):
                        pass
                
                trigger_dist = survey_config.get('trigger_dist')
                if trigger_dist:
                    try:
                        trigger_dist_value = float(trigger_dist)
                        survey_mission.set_measurement('trigger_distance', f"{trigger_dist_value} m")
                    except (ValueError, TypeError):
                        pass
                
                spacing = survey_config.get('spacing')
                if spacing:
                    try:
                        spacing_value = float(spacing)
                        survey_mission.set_measurement('spacing', f"{spacing_value} m")
                    except (ValueError, TypeError):
                        pass
                
                overlap = survey_config.get('overlap')
                if overlap:
                    try:
                        overlap_value = float(overlap)
                        survey_mission.set_measurement('frontal_overlap', f"{overlap_value} %")
                        survey_mission.set_measurement('side_overlap', f"{overlap_value} %")
                    except (ValueError, TypeError):
                        pass
                
                angle = survey_config.get('angle')
                if angle is not None:
                    try:
                        angle_value = float(angle)
                        survey_mission.set_measurement('survey_angle', f"{angle_value} °")
                    except (ValueError, TypeError):
                        pass
            
            # 9.1. Tính total_distance từ waypoints thực tế
            from terminals.utils import calculate_distance_km
            
            created_waypoints = MissionWaypoint._base_manager.filter(
                mission=survey_mission
            ).order_by('order')
            
            total_distance_km = 0.0
            if created_waypoints.count() > 1:
                waypoints_list = list(created_waypoints)
                for i in range(len(waypoints_list) - 1):
                    wp1 = waypoints_list[i]
                    wp2 = waypoints_list[i + 1]
                    try:
                        lat1 = float(wp1.latitude)
                        lon1 = float(wp1.longitude)
                        lat2 = float(wp2.latitude)
                        lon2 = float(wp2.longitude)
                        distance = calculate_distance_km(lat1, lon1, lat2, lon2)
                        total_distance_km += distance
                    except (ValueError, TypeError) as e:
                        print(f"Lỗi tính distance giữa waypoint {wp1.order} và {wp2.order}: {e}")
                        continue
            
            print(f"Tổng khoảng cách tính từ waypoints: {total_distance_km:.4f} km")
            
            if total_distance_km > 0:
                survey_mission.set_measurement('total_distance', f"{total_distance_km:.4f} km")
            
            # 9.2. Tính estimated_time từ total_distance và cruise_speed
            estimated_time_minutes = 0.0
            if total_distance_km > 0 and cruise_speed > 0:
                # Tính từ total_distance (km) và cruise_speed (m/s)
                total_distance_m = total_distance_km * 1000  # Convert km to m
                estimated_time_seconds = total_distance_m / cruise_speed
                estimated_time_minutes = estimated_time_seconds / 60.0
                print(f"Tính estimated_time: {total_distance_km:.4f} km / {cruise_speed} m/s = {estimated_time_minutes:.2f} mins")
            
            if estimated_time_minutes > 0:
                survey_mission.set_measurement('estimated_time', f"{estimated_time_minutes:.2f} mins")
            
            # 10. Create measurements cho waypoints
            from devices.models import Measurement
            from django.contrib.contenttypes.models import ContentType
            
            # created_waypoints đã được query ở trên
            
            measurement_objects = []
            waypoint_content_type = ContentType.objects.get_for_model(MissionWaypoint)
            
            for waypoint in created_waypoints:
                measurement_objects.append(
                    Measurement(
                        content_type=waypoint_content_type,
                        object_id=waypoint.id,
                        measurement_type='cruise_speed',
                        data={
                            'type': 'simple',
                            'value': float(cruise_speed),
                            'unit': 'm/s'
                        }
                    )
                )
                
                measurement_objects.append(
                    Measurement(
                        content_type=waypoint_content_type,
                        object_id=waypoint.id,
                        measurement_type='operating_altitude',
                        data={
                            'type': 'simple',
                            'value': float(altitude_value),
                            'unit': 'm'
                        }
                    )
                )
            
            if measurement_objects:
                Measurement.objects.bulk_create(measurement_objects, batch_size=500, ignore_conflicts=True)
            
            return True, survey_mission
            
        except Exception as e:
            logger.exception(f"Error importing QGC calculated data: {str(e)}")
            raise ValidationError(f"Lỗi khi import QGC data: {str(e)}")