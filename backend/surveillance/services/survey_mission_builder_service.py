"""
Survey Mission Builder Service
Core algorithm to generate QGC survey missions from polygon
Optimized for performance using shapely + pyproj for thousands of waypoints
"""

import math
from typing import List, Dict, Tuple, Optional
from geopy.distance import geodesic
from geographiclib.geodesic import Geodesic
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import transform, unary_union
from pyproj import Transformer
import numpy as np
from common.utils import get_waypoint_speed


# Default camera settings (generic values for QGC file validity)
DEFAULT_CAMERA = {
    "camera_name": "Manual (no camera specs)",
    "focal_length": 3.0,
    "sensor_width": 6.17,
    "sensor_height": 4.55,
    "image_width": 4000,
    "image_height": 3000,
}


class SurveyMissionBuilderService:
    """
    Generate QGC Survey Mission from polygon + simple parameters
    No camera dependency - uses spacing from altitude + overlap
    """
    
    def build_survey_preview(
        self,
        polygon: List[List[float]],
        altitude: float,
        survey_angle: float = 0,
        trigger_distance: float = None,
        spacing: float = None,
        turnaround_distance: float = 60.96,
        frontal_overlap: float = 70,
        side_overlap: float = 70,
        entry_location: int = 1,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        return_to_home: bool = True,
        # QGC Survey Options
        hover_and_capture: bool = False,
        refly_90_degrees: bool = False,
        camera_trigger_in_turnaround: bool = False,
        polygon_components: Optional[List[List[List[float]]]] = None,
    ) -> Dict:
        """
        Fast preview generation - Only calculates waypoints and estimates
        Skips full QGC structure generation for performance
        
        Performance: ~10-50x faster than build_survey_mission
        Use this for /review-mission API endpoint
        
        NOTE: Must have EXACT same parameters as build_survey_mission 
        (except review and terminals) to ensure consistent behavior!
        """
        cruise_speed_value = cruise_speed if cruise_speed else get_waypoint_speed()
        # Calculate spacing
        manual_trigger_distance = trigger_distance if trigger_distance and trigger_distance > 0 else None
        manual_spacing = spacing if spacing and spacing > 0 else None

        if manual_trigger_distance is not None:
            # MODE 1: Priority - use provided trigger_distance
            photo_spacing = manual_trigger_distance
            transect_spacing = manual_spacing if manual_spacing is not None else manual_trigger_distance * 2
        elif manual_spacing is not None:
            # MODE 2: Use only transect spacing (no photo trigger)
            footprint = self._calculate_footprint_from_altitude(altitude)
            photo_spacing = footprint['height']
            transect_spacing = manual_spacing  # use provided spacing
        else:
            # MODE 3: Fallback - calculate from altitude-based defaults when no spacing provided
            footprint = self._calculate_footprint_from_altitude(altitude)
            photo_spacing = footprint['height']
            transect_spacing = footprint['width']
        
        # Generate transects (QGC logic for both modes)
        transects = self._generate_qgc_transects(
            polygon=polygon,
            angle=survey_angle,
            spacing_m=transect_spacing,
            entry_location=entry_location,
            turnaround_distance_m=turnaround_distance,
            hover_and_capture=hover_and_capture,
            trigger_distance=photo_spacing,
            refly_90_degrees=refly_90_degrees,
            altitude=altitude,
            polygon_components=polygon_components,
        )
        
        # Calculate takeoff point
        if transects and len(transects) > 0:
            first_coord = transects[0]['coord_infos'][0]
            takeoff_point = [first_coord['lat'], first_coord['lon']]
        else:
            takeoff_point = polygon[0]
        
        # Generate waypoints and visuals
        waypoints = self._extract_base_waypoints_from_transects(transects)
        visual_points = [
            [coord['lat'], coord['lon']]
            for transect in transects
            for coord in transect['coord_infos']
        ]
        total_distance_in_polygon = sum(transect.get('length_inside', 0.0) for transect in transects)
        
        # Calculate lightweight statistics
        coverage_km2 = self._calculate_polygon_area_multi(polygon_components, polygon)
        total_distance_km = self._calculate_total_distance(waypoints)
        if hover_and_capture:
            camera_shots = self._camera_shots_hover(transects, photo_spacing)
        else:
            camera_shots = self._camera_shots_continuous(transects, photo_spacing)
        
        # Build complete waypoint list for frontend (QGC compatible format)
        # Include ALL waypoints and action commands exactly as in real mission
        # NOTE: Do NOT include MAV_CMD_SET_CAMERA_MODE (530) as it's not extracted by _extract_terminals_from_plan
        preview_waypoints = []
        order = 1
        
        # Takeoff waypoint (MAV_CMD_NAV_TAKEOFF)
        # MAV_CMD_NAV_TAKEOFF params: [pitch, empty, empty, yaw, lat, lon, alt]
        preview_waypoints.append({
            'order': order,
            'latitude': takeoff_point[0],
            'longitude': takeoff_point[1],
            'altitude': altitude,
            'command': {'id': 22, 'name': 'MAV_CMD_NAV_TAKEOFF'},
            'frame': {'id': 3, 'name': 'GLOBAL_RELATIVE_ALT'},
            'params': [0, 0, 0, None, takeoff_point[0], takeoff_point[1], altitude],
            'type': 'simple'
        })
        order += 1
        
        # Survey waypoints - Build based on mode (HoverAndCapture vs Continuous)
        if hover_and_capture:
            # MODE: HoverAndCapture - build preview directly from transects coord_infos.
            # This avoids re-generating dense points (heavy) and ensures preview matches real mission:
            # for each capture point: WAYPOINT(16) -> CAMERA_TRIGGER(203,param5=1)
            hover_delay = 4  # seconds - matches QGC _hoverAndCaptureDelaySeconds

            for transect in transects:
                coord_list = transect.get('coord_infos', []) if isinstance(transect, dict) else []
                if not transect.get('forward', True):
                    coord_list = list(reversed(coord_list))

                for coord in coord_list:
                    coord_type = coord.get('type')
                    lat = coord.get('lat')
                    lon = coord.get('lon')
                    alt = coord.get('alt')
                    if lat is None or lon is None or alt is None:
                        continue

                    is_turnaround = coord_type in ('turnaround_start', 'turnaround_end')
                    hold_s = hover_delay if coord_type in ('entry', 'interior_hover', 'exit') else 0
                    hold_s = 0 if is_turnaround else hold_s

                    # Navigation waypoint (always)
                    preview_waypoints.append({
                        'order': order,
                        'latitude': lat,
                        'longitude': lon,
                        'altitude': alt,
                        'command': {'id': 16, 'name': 'MAV_CMD_NAV_WAYPOINT'},
                        'frame': {'id': 3, 'name': 'GLOBAL_RELATIVE_ALT'},
                        'params': [hold_s, 0, 0, None, lat, lon, alt],
                        'type': 'turnaround' if is_turnaround else 'survey'
                    })
                    order += 1

                    # Camera trigger only at mission capture points (not at turnaround)
                    if coord_type in ('entry', 'interior_hover', 'exit'):
                        preview_waypoints.append({
                            'order': order,
                            'latitude': lat,
                            'longitude': lon,
                            'altitude': alt,
                            'command': {'id': 203, 'name': 'MAV_CMD_DO_DIGICAM_CONTROL'},
                            'frame': {'id': 2, 'name': 'MISSION'},
                            'params': [0, 0, 0, 0, 1, 0, 0],  # param5=1 trigger capture
                            'type': 'action'
                        })
                        order += 1
        else:
            # MODE: Continuous Trigger (default) - Sparse waypoints with distance-based trigger
            for wp in waypoints:
                wp_type = wp['type']
                wp_lat = wp['lat']
                wp_lon = wp['lon']
                wp_alt = wp['alt']
                
                # Add navigation waypoint
                preview_waypoints.append({
                    'order': order,
                    'latitude': wp_lat,
                    'longitude': wp_lon,
                    'altitude': wp_alt,
                    'command': {'id': 16, 'name': 'MAV_CMD_NAV_WAYPOINT'},
                    'frame': {'id': 3, 'name': 'GLOBAL_RELATIVE_ALT'},
                    'params': [0, 0, 0, None, wp_lat, wp_lon, wp_alt],
                    'type': 'turnaround' if wp_type in ('turnaround_start', 'turnaround_end') else 'survey'
                })
                order += 1
                
                # Add camera trigger commands
                if wp_type == 'entry':
                    # START continuous triggering
                    preview_waypoints.append({
                        'order': order,
                        'latitude': wp_lat,
                        'longitude': wp_lon,
                        'altitude': wp_alt,
                        'command': {'id': 206, 'name': 'MAV_CMD_DO_SET_CAM_TRIGG_DIST'},
                        'frame': {'id': 2, 'name': 'MISSION'},
                        'params': [photo_spacing, 0, 1, 0, wp_lat, wp_lon, wp_alt],
                        'type': 'action'
                    })
                    order += 1
                elif wp_type == 'exit':
                    # STOP triggering
                    preview_waypoints.append({
                        'order': order,
                        'latitude': wp_lat,
                        'longitude': wp_lon,
                        'altitude': wp_alt,
                        'command': {'id': 206, 'name': 'MAV_CMD_DO_SET_CAM_TRIGG_DIST'},
                        'frame': {'id': 2, 'name': 'MISSION'},
                        'params': [0, 0, 1, 0, wp_lat, wp_lon, wp_alt],
                        'type': 'action'
                    })
                    order += 1
        
        # RTL waypoint
        # MAV_CMD_NAV_RETURN_TO_LAUNCH params: all zeros
        if return_to_home:
            preview_waypoints.append({
                'order': order,
                'latitude': takeoff_point[0],
                'longitude': takeoff_point[1],
                'altitude': altitude,
                'command': {'id': 20, 'name': 'MAV_CMD_NAV_RETURN_TO_LAUNCH'},
                'frame': {'id': 2, 'name': 'MISSION'},
                'params': [0, 0, 0, 0, 0, 0, altitude],
                'type': 'simple'
            })
        else:
            # LAND at the last navigation waypoint location
            landing_lat = takeoff_point[0]
            landing_lon = takeoff_point[1]
            try:
                for item in reversed(preview_waypoints):
                    cmd = item.get('command')
                    cmd_id = cmd.get('id') if isinstance(cmd, dict) else cmd
                    if cmd_id == 16:
                        landing_lat = item.get('latitude', landing_lat)
                        landing_lon = item.get('longitude', landing_lon)
                        break
            except Exception:
                pass
            preview_waypoints.append({
                'order': order,
                'latitude': landing_lat,
                'longitude': landing_lon,
                'altitude': 0,
                'command': {'id': 21, 'name': 'MAV_CMD_NAV_LAND'},
                'frame': {'id': 3, 'name': 'GLOBAL_RELATIVE_ALT'},
                'params': [0, 0, 0, None, landing_lat, landing_lon, 0],
                'type': 'simple'
            })
        
        # Build survey item preview (for accurate counts)
        if hover_and_capture:
            survey_items_preview = self._build_hover_and_capture_items(
                transects,
                altitude,
                do_jump_id=3,
                review=True,
                camera_trigger_in_turnaround=camera_trigger_in_turnaround,
            )
        else:
            survey_items_preview = self._build_continuous_trigger_items(
                waypoints,
                photo_spacing,
                altitude,
                do_jump_id=3,
                camera_trigger_in_turnaround=camera_trigger_in_turnaround,
                review=True,
            )

        command_counts = {}
        for item in survey_items_preview:
            cmd = item.get('command')
            cmd_id = cmd.get('id') if isinstance(cmd, dict) else cmd
            if cmd_id is None:
                continue
            command_counts[cmd_id] = command_counts.get(cmd_id, 0) + 1

        # Estimates
        estimates = {
            'waypoints': len(survey_items_preview),
            'preview_points': len(preview_waypoints),
            'distance_km': round(total_distance_km, 2),
            'time_minutes': int((total_distance_km * 1000) / cruise_speed_value / 60) if cruise_speed_value else 0,
            'coverage_km2': round(coverage_km2, 2),
            'transects': len(transects),
            'camera_shots': camera_shots,
            'command_counts': command_counts,
        }
        
        return {
            'waypoints': preview_waypoints,
            'estimates': estimates,
            'visual_transect_points': visual_points,
        }
    
    def build_survey_mission(
        self,
        polygon: List[List[float]],
        altitude: float,
        survey_angle: float = 0,
        trigger_distance: float = None,  # Photo spacing in meters (required)
        spacing: float = None,  # Transect spacing in meters (required)
        turnaround_distance: float = 60.96,  # Default 200 ft
        frontal_overlap: float = 70,  # Only for CameraCalc display
        side_overlap: float = 70,  # Only for CameraCalc display
        entry_location: int = 1,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        return_to_home: bool = True,  # Create RTL waypoint at end
        review: bool = False,
        # QGC Survey Options
        hover_and_capture: bool = False,  # Hover at each waypoint to capture
        refly_90_degrees: bool = False,  # Add cross-hatch pattern (90° transects)
        camera_trigger_in_turnaround: bool = False,  # Continue triggering in turnaround
        terminals: list = None,
        polygon_components: Optional[List[List[List[float]]]] = None,
    ) -> Dict:
        """
        Main entry point - Generate complete QGC mission structure
        
        Args:
            polygon: Survey area [[lat, lon], ...]
            altitude: Survey altitude in meters
            survey_angle: Grid rotation (0-360 degrees)
            trigger_distance: Photo spacing in meters (AdjustedFootprintFrontal)
            spacing: Transect spacing in meters (AdjustedFootprintSide)
            turnaround_distance: Distance outside polygon for turnaround in meters
            frontal_overlap: Photo overlap % (display only)
            side_overlap: Transect spacing overlap % (display only)
            entry_location: 0=BL, 1=TL, 2=TR, 3=BR
            cruise_speed: Speed in m/s
            hover_speed: Hover speed in m/s
            return_to_home: Create RTL waypoint at end (default True)
        
        Returns:
            Complete QGC mission structure
        """
        
        cruise_speed_value = cruise_speed if cruise_speed else get_waypoint_speed()

        manual_trigger_distance = trigger_distance if trigger_distance and trigger_distance > 0 else None
        manual_spacing = spacing if spacing and spacing > 0 else None
        
        # Use provided spacing values directly (NOT calculated from overlap)
        if manual_trigger_distance is not None:
            # MODE 1: Priority - use provided trigger_distance
            photo_spacing = manual_trigger_distance
            transect_spacing = manual_spacing if manual_spacing is not None else manual_trigger_distance * 2
        elif manual_spacing is not None:
            # MODE 2: Use only transect spacing (no photo trigger)
            footprint = self._calculate_footprint_from_altitude(altitude)
            photo_spacing = footprint['height']
            transect_spacing = manual_spacing  # use provided spacing
        else:
            # MODE 3: Fallback - calculate from altitude-based defaults when no spacing provided
            footprint = self._calculate_footprint_from_altitude(altitude)
            photo_spacing = footprint['height']
            transect_spacing = footprint['width']
        
        # 3. Generate transects (QGC algorithm)
        transects = self._generate_qgc_transects(
            polygon=polygon,
            angle=survey_angle,
            spacing_m=transect_spacing,
            entry_location=entry_location,
            turnaround_distance_m=turnaround_distance,
            hover_and_capture=hover_and_capture,
            trigger_distance=photo_spacing,
            refly_90_degrees=refly_90_degrees,
            altitude=altitude,
            polygon_components=polygon_components,
        )
        
        # 4. Calculate takeoff point from first transect entry point
        # Takeoff = start point of first transect (not polygon[0])
        if transects and len(transects) > 0:
            first_coord = transects[0]['coord_infos'][0]
            takeoff_point = [first_coord['lat'], first_coord['lon']]
        else:
            # Fallback if no transects generated
            takeoff_point = polygon[0]
        
        # 4. Generate waypoints on transects
        waypoints = self._extract_base_waypoints_from_transects(transects)
        visual_points = [
            [coord['lat'], coord['lon']]
            for transect in transects
            for coord in transect['coord_infos']
        ]
        total_distance_in_polygon = sum(transect.get('length_inside', 0.0) for transect in transects)
        
        # 5. Calculate coverage and stats
        coverage_km2 = self._calculate_polygon_area_multi(polygon_components, polygon)
        total_distance_km = self._calculate_total_distance(waypoints)
        
        # 6. Calculate CameraShots (for no-camera mode)
        # CameraShots = total distance inside polygon / trigger_distance
        if hover_and_capture:
            camera_shots = self._camera_shots_hover(transects, photo_spacing)
        else:
            camera_shots = self._camera_shots_continuous(transects, photo_spacing)
        
        # 6. Build QGC mission structure
        # Footprint for CameraCalc (use actual spacing values)
        footprint = {
            'frontal': photo_spacing,  # AdjustedFootprintFrontal
            'side': transect_spacing,  # AdjustedFootprintSide
        }
        
        qgc_mission = self._build_qgc_structure(
            waypoints,
            polygon,
            takeoff_point,
            altitude,
            cruise_speed_value,
            hover_speed,
            survey_angle,
            frontal_overlap,
            side_overlap,
            entry_location,
            footprint,
            photo_spacing,
            visual_points,
            turnaround_distance,
            camera_shots,
            return_to_home,
            review=review,
            hover_and_capture=hover_and_capture,
            camera_trigger_in_turnaround=camera_trigger_in_turnaround,
            refly_90_degrees=refly_90_degrees,
            transects_hover=transects if hover_and_capture else None,
        )
        
        # 7. Calculate estimates
        # Count total mission items correctly:
        # - Top level items (takeoff + ComplexItem + RTL)
        # - Survey items inside ComplexItem
        mission_items = qgc_mission['mission']['items']
        total_mission_items = 0
        
        for item in mission_items:
            if item.get('type') == 'ComplexItem':
                # Count survey items inside ComplexItem
                survey_items = item.get('TransectStyleComplexItem', {}).get('Items', [])
                total_mission_items += len(survey_items)
            else:
                # Simple items (Takeoff, RTL, etc.)
                total_mission_items += 1
        
        estimates = {
            'waypoints': total_mission_items,
            'distance_km': round(total_distance_km, 2),
            'time_minutes': int((total_distance_km * 1000) / cruise_speed_value / 60) if cruise_speed_value else 0,
            'coverage_km2': round(coverage_km2, 2),
            'transects': len(transects),
            'camera_shots': camera_shots,
        }
        
        return {
            'qgc_mission': qgc_mission,
            'estimates': estimates,
            'waypoints_visualization': waypoints,
            'transects_visualization': transects,
        }
    
    def build_survey_mission_with_drone_division(
        self,
        polygon: List[List[float]],
        altitude: float,
        maximum_drones: int = 1,
        survey_angle: float = 0,
        trigger_distance: float = None,
        spacing: float = None,
        turnaround_distance: float = 60.96,
        frontal_overlap: float = 70,
        side_overlap: float = 70,
        entry_location: int = 1,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        return_to_home: bool = True,
        available_devices: List[Dict] = None,
    ) -> Dict:
        """
        Tạo survey mission và chia cho nhiều drone
        
        Args:
            polygon: Survey area [[lat, lon], ...]
            altitude: Survey altitude in meters
            maximum_drones: Số drone tối đa để chia mission
            survey_angle: Grid rotation (0-360 degrees)
            trigger_distance: Photo spacing in meters
            spacing: Transect spacing in meters
            turnaround_distance: Distance outside polygon for turnaround in meters
            frontal_overlap: Photo overlap % (display only)
            side_overlap: Transect spacing overlap % (display only)
            entry_location: 0=BL, 1=TL, 2=TR, 3=BR
            cruise_speed: Speed in m/s
            hover_speed: Hover speed in m/s
            return_to_home: Create RTL waypoint at end
            available_devices: Danh sách device active từ database
        
        Returns:
            Dict với thông tin mission và phân chia drone
        """
        
        cruise_speed_value = cruise_speed if cruise_speed else get_waypoint_speed()

        # 1. Tạo mission cơ bản
        basic_mission = self.build_survey_mission(
            polygon=polygon,
            altitude=altitude,
            survey_angle=survey_angle,
            trigger_distance=trigger_distance,
            spacing=spacing,
            turnaround_distance=turnaround_distance,
            frontal_overlap=frontal_overlap,
            side_overlap=side_overlap,
            entry_location=entry_location,
            cruise_speed=cruise_speed_value,
            hover_speed=hover_speed,
            return_to_home=return_to_home,
        )
        
        # 2. Lấy dữ liệu từ mission cơ bản
        waypoints = basic_mission['waypoints_visualization']
        transects = basic_mission['transects_visualization']
        total_distance_km = basic_mission['estimates']['distance_km']
        qgc_mission_data = basic_mission.get('qgc_mission', {})
        
        # 3. Chia mission cho nhiều drone
        drone_missions = self.divide_mission_for_multiple_drones(
            waypoints=waypoints,
            total_distance_km=total_distance_km,
            maximum_drones=maximum_drones,
            transects=transects,
            available_devices=available_devices,
            cruise_speed=cruise_speed_value,
            hover_speed=hover_speed,
            qgc_mission_data=qgc_mission_data
        )
        
        # 4. Tính toán thống kê tổng hợp
        total_waypoints = len(waypoints)
        total_transects = len(transects)
        average_distance_per_drone = total_distance_km / maximum_drones
        
        # 5. Tạo QGC mission cho từng drone
        drone_qgc_missions = []
        for drone_mission in drone_missions:
            drone_qgc = self._build_qgc_structure_for_drone(
                drone_mission=drone_mission,
                polygon=polygon,
                altitude=altitude,
                cruise_speed=cruise_speed_value,
                hover_speed=hover_speed,
                survey_angle=survey_angle,
                frontal_overlap=frontal_overlap,
                side_overlap=side_overlap,
                entry_location=entry_location,
                turnaround_distance=turnaround_distance,
                return_to_home=return_to_home,
            )
            drone_qgc_missions.append(drone_qgc)
        
        return {
            'basic_mission': basic_mission,
            'drone_missions': drone_missions,
            'drone_qgc_missions': drone_qgc_missions,
            'summary': {
                'total_distance_km': total_distance_km,
                'total_waypoints': total_waypoints,
                'total_transects': total_transects,
                'maximum_drones': maximum_drones,
                'average_distance_per_drone': round(average_distance_per_drone, 2),
                'distance_per_drone_km': round(total_distance_km / maximum_drones, 2),
            }
        }
    
    def _build_qgc_structure_for_drone(
        self,
        drone_mission: Dict,
        polygon: List[List[float]],
        altitude: float,
        cruise_speed: float,
        hover_speed: float,
        survey_angle: float,
        frontal_overlap: float,
        side_overlap: float,
        entry_location: int,
        turnaround_distance: float,
        return_to_home: bool,
    ) -> Dict:
        """
        Tạo QGC mission structure cho một drone cụ thể
        """
        waypoints = drone_mission['waypoints']
        takeoff_point = drone_mission['takeoff_point']
        
        # Build mission items
        items = []
        do_jump_id = 1
        
        # 1. Add Camera Mode command
        items.append({
            "autoContinue": True,
            "command": 530,  # MAV_CMD_SET_CAMERA_MODE
            "doJumpId": do_jump_id,
            "frame": 2,
            "params": [0, 2, None, None, None, None, None],
            "type": "SimpleItem"
        })
        do_jump_id += 1
        
        # 2. Takeoff
        items.append({
            "AMSLAltAboveTerrain": None,
            "Altitude": altitude,
            "AltitudeMode": 1,
            "autoContinue": True,
            "command": 22,  # MAV_CMD_NAV_TAKEOFF
            "doJumpId": do_jump_id,
            "frame": 3,
            "params": [0, 0, 0, None, takeoff_point[0], takeoff_point[1], altitude],
            "type": "SimpleItem"
        })
        do_jump_id += 1
        
        # 3. Survey waypoints (simplified for drone)
        for wp in waypoints:
            items.append({
                "autoContinue": True,
                "command": 16,  # MAV_CMD_NAV_WAYPOINT
                "doJumpId": do_jump_id,
                "frame": 3,
                "params": [0, 0, 0, None, wp['lat'], wp['lon'], wp['alt']],
                "type": "SimpleItem"
            })
            do_jump_id += 1
        
        # 4. End mission command (RTL or LAND)
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
            landing_lat = takeoff_point[0]
            landing_lon = takeoff_point[1]
            if waypoints:
                try:
                    landing_lat = waypoints[-1].get('lat', landing_lat)
                    landing_lon = waypoints[-1].get('lon', landing_lon)
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
                "hoverSpeed": hover_speed,
                "items": items,
                "plannedHomePosition": [takeoff_point[0], takeoff_point[1], 11],
                "vehicleType": 2,
                "version": 2
            },
            "rallyPoints": {"points": [], "version": 2},
            "version": 1,
            "drone_info": {
                "drone_id": drone_mission['drone_id'],
                "start_transect": drone_mission['start_transect'],
                "end_transect": drone_mission['end_transect'],
                "distance_km": drone_mission['distance_km'],
                "waypoint_count": len(waypoints),
            }
        }
    
    def _calculate_footprint_from_altitude(self, altitude: float) -> Dict:
        """
        Calculate camera footprint based on altitude
        Uses generic assumptions (not real camera specs)
        """
        # Default heuristic derived from original QGC behaviour:
        # - Convert altitude to meters if user provides feet (common input)
        # - Use altitude (in meters) as base transect spacing
        # - Use half of altitude as photo spacing baseline

        altitude_m = altitude
        # If altitude likely provided in feet (value unusually large for meters), convert to meters
        if altitude_m > 120:  # 120m ≈ 394ft, typical upper bound for survey altitude in meters
            altitude_m = altitude_m * 0.3048
        
        return {
            'width': altitude_m,
            'height': altitude_m / 2.0,
        }
    
    # === QGC-specific helpers for advanced options ==========================

    _WGS84_A = 6378137.0
    _EPSILON = 1e-12

    def _geo_to_local(self, lat: float, lon: float, origin_lat: float, origin_lon: float) -> Tuple[float, float]:
        if lat == origin_lat and lon == origin_lon:
            return 0.0, 0.0

        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        ref_lat_rad = math.radians(origin_lat)
        ref_lon_rad = math.radians(origin_lon)

        sin_lat = math.sin(lat_rad)
        cos_lat = math.cos(lat_rad)
        sin_ref_lat = math.sin(ref_lat_rad)
        cos_ref_lat = math.cos(ref_lat_rad)
        cos_d_lon = math.cos(lon_rad - ref_lon_rad)

        c = math.acos(sin_ref_lat * sin_lat + cos_ref_lat * cos_lat * cos_d_lon)
        k = 1.0 if abs(c) < self._EPSILON else c / math.sin(c)

        north = k * (cos_ref_lat * sin_lat - sin_ref_lat * cos_lat * cos_d_lon) * self._WGS84_A
        east = k * cos_lat * math.sin(lon_rad - ref_lon_rad) * self._WGS84_A

        return east, north

    def _local_to_geo(self, east: float, north: float, origin_lat: float, origin_lon: float) -> Tuple[float, float]:
        x_rad = north / self._WGS84_A
        y_rad = east / self._WGS84_A
        c = math.sqrt(x_rad * x_rad + y_rad * y_rad)
        sin_c = math.sin(c)
        cos_c = math.cos(c)

        ref_lat_rad = math.radians(origin_lat)
        ref_lon_rad = math.radians(origin_lon)
        sin_ref_lat = math.sin(ref_lat_rad)
        cos_ref_lat = math.cos(ref_lat_rad)

        if abs(c) > self._EPSILON:
            lat_rad = math.asin(cos_c * sin_ref_lat + (x_rad * sin_c * cos_ref_lat) / c)
            lon_rad = ref_lon_rad + math.atan2(y_rad * sin_c,
                                               c * cos_ref_lat * cos_c - x_rad * sin_ref_lat * sin_c)
        else:
            lat_rad = ref_lat_rad
            lon_rad = ref_lon_rad

        return math.degrees(lat_rad), math.degrees(lon_rad)

    def _rotate_point_xy(self, x: float, y: float, cx: float, cy: float, angle_deg: float) -> Tuple[float, float]:
        radians = math.radians(-angle_deg)
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        dx = x - cx
        dy = y - cy
        rotated_x = dx * cos_a - dy * sin_a
        rotated_y = dx * sin_a + dy * cos_a
        return rotated_x + cx, rotated_y + cy

    def _qt_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        if lat1 == lat2 and lon1 == lon2:
            return 0.0

        inv = Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)
        return inv['s12']

    def _qt_at_distance_azimuth(self, lat: float, lon: float, distance: float, azimuth_deg: float) -> Tuple[float, float]:
        radius = self._WGS84_A
        if distance < 0:
            distance = -distance
            azimuth_deg = (azimuth_deg + 180.0) % 360.0

        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        azimuth_rad = math.radians(azimuth_deg)

        angular_distance = distance / radius

        sin_lat = math.sin(lat_rad)
        cos_lat = math.cos(lat_rad)
        sin_ad = math.sin(angular_distance)
        cos_ad = math.cos(angular_distance)

        sin_lat2 = sin_lat * cos_ad + cos_lat * sin_ad * math.cos(azimuth_rad)
        lat2_rad = math.asin(max(-1.0, min(1.0, sin_lat2)))

        y = math.sin(azimuth_rad) * sin_ad * cos_lat
        x = cos_ad - sin_lat * sin_lat2
        lon2_rad = lon_rad + math.atan2(y, x)

        lat2 = math.degrees(lat2_rad)
        lon2 = (math.degrees(lon2_rad) + 540.0) % 360.0 - 180.0
        return lat2, lon2

    def _qt_azimuth(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        if lat1 == lat2 and lon1 == lon2:
            return 0.0

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)

        y = math.sin(delta_lon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
        azimuth = math.degrees(math.atan2(y, x))
        return (azimuth + 360.0) % 360.0

    def _generate_qgc_transects(
        self,
        polygon: List[List[float]],
        angle: float,
        spacing_m: float,
        entry_location: int,
        turnaround_distance_m: float,
        hover_and_capture: bool,
        trigger_distance: float,
        refly_90_degrees: bool,
        altitude: float,
        polygon_components: Optional[List[List[List[float]]]] = None,
    ) -> List[Dict]:
        if not polygon or len(polygon) < 3:
            return []

        origin_lat, origin_lon = polygon[0]

        polygon_local: List[Tuple[float, float]] = []
        for index, (lat, lon) in enumerate(polygon):
            if index == 0:
                polygon_local.append((0.0, 0.0))
            else:
                polygon_local.append(self._geo_to_local(lat, lon, origin_lat, origin_lon))
        polygon_local.append(polygon_local[0])

        polygon_local_loops: List[List[Tuple[float, float]]] = []
        if polygon_components:
            for comp in polygon_components:
                if not comp or len(comp) < 3:
                    continue
                local_loop = [self._geo_to_local(lat, lon, origin_lat, origin_lon) for lat, lon in comp]
                if len(local_loop) < 3:
                    continue
                polygon_local_loops.append(local_loop + [local_loop[0]])

        if not polygon_local_loops:
            polygon_local_loops = [polygon_local]

        xs = [pt[0] for pt in polygon_local[:-1]]
        ys = [pt[1] for pt in polygon_local[:-1]]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        bounding_center_x = (min_x + max_x) / 2.0
        bounding_center_y = (min_y + max_y) / 2.0
        max_width = max(max_x - min_x, max_y - min_y) + 2000.0
        half_width = max_width / 2.0

        grid_spacing = spacing_m if spacing_m and spacing_m >= 0.5 else 100000.0
        trigger = trigger_distance if trigger_distance and trigger_distance > 0 else None

        pass_angles: List[float] = [self._clamp_grid_angle90(angle)]
        if refly_90_degrees:
            pass_angles.append(self._clamp_grid_angle90(angle + 90.0))

        all_transects: List[Dict] = []
        previous_terminal_coord: Optional[Tuple[float, float]] = None

        for pass_index, grid_angle in enumerate(pass_angles):
            line_list: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
            transect_x = bounding_center_x - half_width
            transect_x_max = transect_x + max_width

            while transect_x < transect_x_max:
                transect_y_top = bounding_center_y - half_width
                transect_y_bottom = bounding_center_y + half_width

                rotated_top = self._rotate_point_xy(transect_x, transect_y_top, bounding_center_x, bounding_center_y, grid_angle)
                rotated_bottom = self._rotate_point_xy(transect_x, transect_y_bottom, bounding_center_x, bounding_center_y, grid_angle)
                line_list.append((rotated_top, rotated_bottom))
                transect_x += grid_spacing

            intersect_lines = self._intersect_lines_with_polygon(line_list, polygon_local_loops)

            if len(intersect_lines) < 2 and line_list:
                first_line = line_list[0]
                mid_x = (first_line[0][0] + first_line[1][0]) / 2.0
                mid_y = (first_line[0][1] + first_line[1][1]) / 2.0
                offset_x = bounding_center_x - mid_x
                offset_y = bounding_center_y - mid_y
                translated_line = (
                    (first_line[0][0] + offset_x, first_line[0][1] + offset_y),
                    (first_line[1][0] + offset_x, first_line[1][1] + offset_y),
                )
                intersect_lines = self._intersect_lines_with_polygon([translated_line], polygon_local_loops)

            if not intersect_lines:
                continue

            result_lines = self._adjust_line_direction(intersect_lines)

            transects_geo = []
            transects_local = []
            for start, end in result_lines:
                line_vec_x = end[0] - start[0]
                line_vec_y = end[1] - start[1]
                line_length = math.sqrt(line_vec_x * line_vec_x + line_vec_y * line_vec_y)

                min_intersection_threshold = spacing_m * 0.01
                if trigger_distance and trigger_distance > 0:
                    trigger_threshold = trigger_distance * 0.05
                    if trigger_threshold > min_intersection_threshold:
                        min_intersection_threshold = trigger_threshold

                if line_length <= 0 or line_length < min_intersection_threshold:
                    continue

                lat1, lon1 = self._local_to_geo(start[0], start[1], origin_lat, origin_lon)
                lat2, lon2 = self._local_to_geo(end[0], end[1], origin_lat, origin_lon)

                transects_geo.append([(lat1, lon1), (lat2, lon2)])
                transects_local.append([tuple(start), tuple(end)])

            if not transects_geo:
                continue

            transects_geo = self._adjust_transects_to_entry_point(transects_geo, entry_location)
            transects_local = self._adjust_transects_to_entry_point(transects_local, entry_location)

            if pass_index > 0 and previous_terminal_coord is not None:
                optimized_geo = self._optimize_transects_for_shortest_distance(previous_terminal_coord, transects_geo)
                transects_geo = optimized_geo
                # Rebuild transects_local từ optimized_geo để đảm bảo sync
                # Vì optimize có thể reverse hoặc reorder transects, không thể lookup trong map cũ
                transects_local = []
                for geo in optimized_geo:
                    start_lat, start_lon = geo[0]
                    end_lat, end_lon = geo[-1]
                    start_local = self._geo_to_local(start_lat, start_lon, origin_lat, origin_lon)
                    end_local = self._geo_to_local(end_lat, end_lon, origin_lat, origin_lon)
                    transects_local.append([tuple(start_local), tuple(end_local)])

            transects_geo = self._apply_lawnmower_pattern(transects_geo)
            transects_local = self._apply_lawnmower_pattern(transects_local)

            pass_transects = self._build_coord_infos_from_transects(
                transects_geo=transects_geo,
                transects_local=transects_local,
                altitude=altitude,
                turnaround_distance=turnaround_distance_m,
                trigger_distance=trigger,
                include_hover_points=hover_and_capture,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            )

            if pass_transects:
                terminal_coord = pass_transects[-1]['coord_infos'][-1]
                previous_terminal_coord = (terminal_coord['lat'], terminal_coord['lon'])
                all_transects.extend(pass_transects)

        return all_transects

    def _clamp_grid_angle90(self, grid_angle: float) -> float:
        if grid_angle > 90.0:
            grid_angle -= 180.0
        elif grid_angle < -90.0:
            grid_angle += 180.0
        return grid_angle

    def _intersect_lines_with_polygon(
        self,
        line_list: List[Tuple[Tuple[float, float], Tuple[float, float]]],
        polygon: List,
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        result_lines: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        duplicate_tol = 1e-9
        denom_tol = 1e-12
        boundary_epsilon = 1e-9

        if not polygon:
            return result_lines

        if polygon and isinstance(polygon[0], tuple):
            loops = [polygon]
        else:
            loops = [loop for loop in polygon if loop]

        for start, end in line_list:
            x1, y1 = start
            x2, y2 = end
            intersections: List[Tuple[float, float]] = []

            for loop in loops:
                loop_len = len(loop)
                if loop_len < 2:
                    continue

                for idx in range(loop_len - 1):
                    x3, y3 = loop[idx]
                    x4, y4 = loop[idx + 1]

                    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
                    if abs(denom) < denom_tol:
                        continue

                    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
                    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / denom

                    if -boundary_epsilon <= t <= 1 + boundary_epsilon and -boundary_epsilon <= u <= 1 + boundary_epsilon:
                        ix = x1 + t * (x2 - x1)
                        iy = y1 + t * (y2 - y1)

                        is_duplicate = any(
                            (abs(ix - px) <= duplicate_tol and abs(iy - py) <= duplicate_tol)
                            for px, py in intersections
                        )
                        if not is_duplicate:
                            intersections.append((ix, iy))

            if len(intersections) > 1:
                first_point = None
                second_point = None
                max_dist_sq = -1.0

                for i in range(len(intersections)):
                    for j in range(i + 1, len(intersections)):
                        px1, py1 = intersections[i]
                        px2, py2 = intersections[j]
                        dx = px2 - px1
                        dy = py2 - py1
                        dist_sq = dx * dx + dy * dy
                        if dist_sq > max_dist_sq:
                            max_dist_sq = dist_sq
                            first_point = (px1, py1)
                            second_point = (px2, py2)

                if first_point and second_point and max_dist_sq > 0:
                    result_lines.append((first_point, second_point))

        return result_lines

    def _adjust_line_direction(
        self,
        line_list: List[Tuple[Tuple[float, float], Tuple[float, float]]]
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        if not line_list:
            return []

        result: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        first_angle = None

        for start, end in line_list:
            angle_deg = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))
            if first_angle is None:
                first_angle = angle_deg
                result.append((start, end))
            else:
                diff = abs(angle_deg - first_angle)
                if diff > 180:
                    diff = 360 - diff
                if diff > 1.0:
                    result.append((end, start))
                else:
                    result.append((start, end))

        return result

    def _adjust_transects_to_entry_point(
        self,
        transects: List[List[Tuple[float, float]]],
        entry_location: int,
    ) -> List[List[Tuple[float, float]]]:
        if not transects:
            return transects

        adjusted = transects
        if entry_location in (2, 3):  # Bottom entries
            adjusted = [list(reversed(coords)) for coords in adjusted]
        if entry_location in (1, 3):  # Start from right
            adjusted = list(reversed(adjusted))
        return adjusted

    def _apply_lawnmower_pattern(
        self,
        transects: List[List[Tuple[float, float]]],
    ) -> List[List[Tuple[float, float]]]:
        result: List[List[Tuple[float, float]]] = []
        reverse_vertices = False
        for coords in transects:
            if reverse_vertices:
                result.append(list(reversed(coords)))
            else:
                result.append(list(coords))
            reverse_vertices = not reverse_vertices
        return result

    def _optimize_transects_for_shortest_distance(
        self,
        reference_coord: Optional[Tuple[float, float]],
        transects: List[List[Tuple[float, float]]],
    ) -> List[List[Tuple[float, float]]]:
        if not reference_coord or not transects:
            return transects

        lat_ref, lon_ref = reference_coord
        combos = [
            transects[0][0],
            transects[0][-1],
            transects[-1][0],
            transects[-1][-1],
        ]

        distances = []
        for lat, lon in combos:
            distances.append(self._qt_distance(lat_ref, lon_ref, lat, lon))

        shortest_index = min(range(len(distances)), key=lambda idx: distances[idx])

        if shortest_index > 1:
            transects = list(reversed(transects))

        if shortest_index % 2 == 1:
            transects = [list(reversed(coords)) for coords in transects]

        return transects

    def _calculate_hover_point_count(
        self,
        transect_length_geo: float,
        transect_length_local: float,
        trigger_distance: float,
    ) -> int:
        if trigger_distance <= 0:
            return 0

        ratio_geo = transect_length_geo / trigger_distance
        base_count = int(math.floor(ratio_geo + 1e-9))

        if base_count <= 0:
            return 0

        diff_len = transect_length_local - transect_length_geo
        closeness = math.ceil(ratio_geo) - ratio_geo

        if diff_len > 2.0 and closeness < 0.08:
            base_count = int(math.ceil(ratio_geo - 1e-9))

        return base_count

    def _build_coord_infos_from_transects(
        self,
        transects_geo: List[List[Tuple[float, float]]],
        transects_local: List[List[Tuple[float, float]]],
        altitude: float,
        turnaround_distance: float,
        trigger_distance: float,
        include_hover_points: bool,
        origin_lat: float,
        origin_lon: float,
    ) -> List[Dict]:
        results: List[Dict] = []

        for coords_geo, coords_local in zip(transects_geo, transects_local):
            entry_lat, entry_lon = coords_geo[0]
            exit_lat, exit_lon = coords_geo[-1]

            entry_east, entry_north = coords_local[0]
            exit_east, exit_north = coords_local[-1]
            delta_east = exit_east - entry_east
            delta_north = exit_north - entry_north
            transect_length_local = math.hypot(delta_east, delta_north)
            transect_length_geo = self._qt_distance(entry_lat, entry_lon, exit_lat, exit_lon)

            if transect_length_geo <= 0.0:
                continue

            unit_east = delta_east / transect_length_local if transect_length_local != 0 else 0.0
            unit_north = delta_north / transect_length_local if transect_length_local != 0 else 0.0
            transect_azimuth = self._qt_azimuth(entry_lat, entry_lon, exit_lat, exit_lon)

            coord_infos: List[Dict] = []

            if turnaround_distance and turnaround_distance > 0:
                before_east = entry_east - unit_east * turnaround_distance
                before_north = entry_north - unit_north * turnaround_distance
                before_lat, before_lon = self._local_to_geo(before_east, before_north, origin_lat, origin_lon)
                coord_infos.append({
                    'lat': before_lat,
                    'lon': before_lon,
                    'alt': altitude,
                    'type': 'turnaround_start'
                })

            coord_infos.append({
                'lat': entry_lat,
                'lon': entry_lon,
                'alt': altitude,
                'type': 'entry'
            })

            if include_hover_points and trigger_distance and trigger_distance > 0 and transect_length_geo > trigger_distance:
                base_count = self._calculate_hover_point_count(
                    transect_length_geo,
                    transect_length_local,
                    trigger_distance,
                )

                for i in range(base_count):
                    distance_from_entry = trigger_distance * (i + 1)
                    if distance_from_entry > transect_length_geo:
                        distance_from_entry = transect_length_geo

                    inner_lat, inner_lon = self._qt_at_distance_azimuth(
                        entry_lat,
                        entry_lon,
                        distance_from_entry,
                        transect_azimuth,
                    )
                    coord_infos.append({
                        'lat': inner_lat,
                        'lon': inner_lon,
                        'alt': altitude,
                        'type': 'interior_hover'
                    })

            coord_infos.append({
                'lat': exit_lat,
                'lon': exit_lon,
                'alt': altitude,
                'type': 'exit'
            })

            length_total = transect_length_local
            if turnaround_distance and turnaround_distance > 0:
                after_east = exit_east + unit_east * turnaround_distance
                after_north = exit_north + unit_north * turnaround_distance
                after_lat, after_lon = self._local_to_geo(after_east, after_north, origin_lat, origin_lon)
                coord_infos.append({
                    'lat': after_lat,
                    'lon': after_lon,
                    'alt': altitude,
                    'type': 'turnaround_end'
                })

            length_inside = transect_length_geo

            if coord_infos:
                start_coord = coord_infos[0]
                end_coord = coord_infos[-1]
                start_east, start_north = self._geo_to_local(start_coord['lat'], start_coord['lon'], origin_lat, origin_lon)
                end_east, end_north = self._geo_to_local(end_coord['lat'], end_coord['lon'], origin_lat, origin_lon)
                length_total = math.hypot(end_east - start_east, end_north - start_north)

            results.append({
                'coord_infos': coord_infos,
                'entry': {'lat': entry_lat, 'lon': entry_lon},
                'exit': {'lat': exit_lat, 'lon': exit_lon},
                'length_inside': length_inside,
                'length_total': length_total,
            })

        return results

    def _extract_base_waypoints_from_transects(self, transects: List[Dict]) -> List[Dict]:
        waypoints = []
        for transect in transects:
            coord_list = transect['coord_infos']
            if not transect.get('forward', True):
                coord_list = list(reversed(coord_list))

            for coord in coord_list:
                if coord['type'] in ('turnaround_start', 'entry', 'exit', 'turnaround_end'):
                    waypoints.append({
                        'lat': coord['lat'],
                        'lon': coord['lon'],
                        'alt': coord['alt'],
                        'type': coord['type'],
                    })
        return waypoints

    def _camera_shots_hover(self, transects: List[Dict], trigger_distance: float) -> int:
        if not trigger_distance or trigger_distance <= 0:
            return sum(
                1
                for transect in transects
                for coord in transect['coord_infos']
                if coord['type'] in ('interior_hover', 'exit')
            )

        total_shots = 0
        for transect in transects:
            coords = transect.get('coord_infos', [])
            if not coords:
                continue

            start = coords[0]
            end = coords[-1]
            length_total = self._qt_distance(start['lat'], start['lon'], end['lat'], end['lon'])

            if length_total > 0:
                total_shots += int(math.ceil(length_total / trigger_distance))
        return total_shots

    def _camera_shots_continuous(self, transects: List[Dict], trigger_distance: float) -> int:
        if not trigger_distance or trigger_distance <= 0:
            return 0

        total_shots = 0
        for transect in transects:
            coords = transect.get('coord_infos', [])
            if not coords:
                continue

            entry_coord = None
            exit_coord = None

            for coord in coords:
                if coord.get('type') == 'entry':
                    entry_coord = coord
                    break

            for coord in reversed(coords):
                if coord.get('type') == 'exit':
                    exit_coord = coord
                    break

            if not entry_coord or not exit_coord:
                continue

            length_inside = self._qt_distance(
                entry_coord['lat'], entry_coord['lon'], exit_coord['lat'], exit_coord['lon']
            )
            if length_inside > 0:
                total_shots += int(math.ceil(length_inside / trigger_distance))

        return total_shots
    
    def _generate_transects(
        self,
        polygon: List[List[float]],
        angle: float,
        spacing_m: float,
        entry_location: int,
        turnaround_distance_m: float,
    ) -> List[Dict]:
        """
        Generate parallel transect lines across polygon using shapely
        Includes turnaround distance outside polygon for smooth turns
        
        Returns: List of transects [{'start': [lat,lon], 'end': [lat,lon]}, ...]
        """
        # Create shapely polygon (lon, lat order for shapely)
        poly_coords = [(p[1], p[0]) for p in polygon]  # Convert to (lon, lat)
        shapely_poly = Polygon(poly_coords)
        
        # Fix invalid polygons (self-intersecting, etc.) using buffer(0)
        if not shapely_poly.is_valid:
            shapely_poly = shapely_poly.buffer(0)
        
        # Get bounds
        minx, miny, maxx, maxy = shapely_poly.bounds
        center_lon, center_lat = shapely_poly.centroid.x, shapely_poly.centroid.y
        center = [center_lat, center_lon]
        
        # QGC uses NED (North-East-Down) with tangent origin = first vertex
        # Exact implementation from QGCGeo.cc lines 36-63
        # Uses Azimuthal Equidistant Projection
        
        tangent_origin = polygon[0]  # [lat, lon]
        ref_lat = tangent_origin[0]
        ref_lon = tangent_origin[1]
        
        # WGS84 Earth's equatorial radius
        WGS84_a = 6378137.0  # meters
        epsilon = 1e-10
        
        # Convert polygon to local NED coordinates (meters from origin)
        poly_coords_local = []
        
        for i, vertex in enumerate(polygon):
            if i == 0:
                # First vertex at origin (QGC line 38-42)
                poly_coords_local.append([0.0, 0.0])
            else:
                # QGC convertGeoToNed implementation (lines 44-62)
                lat = vertex[0]
                lon = vertex[1]
                
                lat_rad = math.radians(lat)
                lon_rad = math.radians(lon)
                ref_lon_rad = math.radians(ref_lon)
                ref_lat_rad = math.radians(ref_lat)
                
                sin_lat = math.sin(lat_rad)
                cos_lat = math.cos(lat_rad)
                cos_d_lon = math.cos(lon_rad - ref_lon_rad)
                
                ref_sin_lat = math.sin(ref_lat_rad)
                ref_cos_lat = math.cos(ref_lat_rad)
                
                # Azimuthal equidistant projection
                # Clamp to avoid domain errors in acos
                cos_c_val = ref_sin_lat * sin_lat + ref_cos_lat * cos_lat * cos_d_lon
                cos_c_val = max(-1.0, min(1.0, cos_c_val))  # Clamp to [-1, 1]
                c = math.acos(cos_c_val)
                k = 1.0 if abs(c) < epsilon else (c / math.sin(c))
                
                # NED coordinates (x=North, y=East in QGC's convention)
                x_ned = k * (ref_cos_lat * sin_lat - ref_sin_lat * cos_lat * cos_d_lon) * WGS84_a
                y_ned = k * cos_lat * math.sin(lon_rad - ref_lon_rad) * WGS84_a
                
                # QGC stores as (x, y) = (East, North) in QPointF
                # But variable names are swapped in their code
                poly_coords_local.append([y_ned, x_ned])  # [East, North]
        
        poly_utm = Polygon(poly_coords_local)
        
        # Store for later conversion back
        self._tangent_origin_lat = ref_lat
        self._tangent_origin_lon = ref_lon
        self._WGS84_a = WGS84_a
        self._epsilon = epsilon
        
        # Create transformers for later use (keep UTM for backward compatibility)
        utm_zone = int((center_lon + 180) / 6) + 1
        utm_crs = f"+proj=utm +zone={utm_zone} +datum=WGS84 +units=m +no_defs"
        wgs84_crs = "+proj=longlat +datum=WGS84 +no_defs"
        to_utm = Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)
        to_wgs84 = Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
        
        # QGC Algorithm (EXACT MATCH with SurveyComplexItem.cc):
        # 1. Get bounding rect of ORIGINAL polygon (no rotation yet)
        minx_orig, miny_orig, maxx_orig, maxy_orig = poly_utm.bounds
        orig_width = maxx_orig - minx_orig
        orig_height = maxy_orig - miny_orig
        bounding_center_x = (minx_orig + maxx_orig) / 2
        bounding_center_y = (miny_orig + maxy_orig) / 2
        
        # 2. maxWidth = max(boundingRect.width(), boundingRect.height()) + 2000.0
        max_dimension = max(orig_width, orig_height)
        fudge_factor = 2000.0  # QGC constant from line 711
        max_width = max_dimension + fudge_factor
        half_width = max_width / 2.0
        
        # 3. Clamp grid angle to [-90, 90] (QGC _clampGridAngle90, line 598-607)
        # This prevents transects from being rotated to a reversed order
        clamped_angle = angle
        if clamped_angle > 90.0:
            clamped_angle -= 180.0
        elif clamped_angle < -90.0:
            clamped_angle += 180.0
        
        # 4. Generate transects W-E, THEN rotate each point
        # QGC line 713-721:
        # transectX = boundingCenter.x() - halfWidth
        # transectXMax = transectX + maxWidth
        # while (transectX < transectXMax) {
        #     lineList += QLineF(_rotatePoint(QPointF(transectX, transectYTop), boundingCenter, gridAngle),
        #                        _rotatePoint(QPointF(transectX, transectYBottom), boundingCenter, gridAngle));
        #     transectX += gridSpacing;
        # }
        
        from shapely import affinity
        transects = []
        transect_x = bounding_center_x - half_width
        transect_x_max = transect_x + max_width
        
        # IMPORTANT: QGC rotates CLOCKWISE (negative angle), but standard rotation is CCW
        # To match QGC, we need to negate the angle
        angle_rad = math.radians(-clamped_angle)  # Negate to match QGC's direction
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        while transect_x < transect_x_max:
            # Create vertical line points (W-E direction, N-S within transect)
            transect_y_top = bounding_center_y - half_width
            transect_y_bottom = bounding_center_y + half_width
            
            # Rotate points around bounding center (QGC _rotatePoint)
            # Rotation formula: (x', y') = (cx + (x-cx)*cos - (y-cy)*sin, cy + (x-cx)*sin + (y-cy)*cos)
            dx_top = transect_x - bounding_center_x
            dy_top = transect_y_top - bounding_center_y
            rotated_x_top = bounding_center_x + dx_top * cos_a - dy_top * sin_a
            rotated_y_top = bounding_center_y + dx_top * sin_a + dy_top * cos_a
            
            dx_bottom = transect_x - bounding_center_x
            dy_bottom = transect_y_bottom - bounding_center_y
            rotated_x_bottom = bounding_center_x + dx_bottom * cos_a - dy_bottom * sin_a
            rotated_y_bottom = bounding_center_y + dx_bottom * sin_a + dy_bottom * cos_a
            
            # Create rotated line
            line = LineString([(rotated_x_top, rotated_y_top), (rotated_x_bottom, rotated_y_bottom)])
            
            # QGC _intersectLinesWithPolygon: Intersect line with EACH polygon edge
            # and keep only transects with >= 2 intersection points
            intersection_points = []
            polygon_coords = list(poly_utm.exterior.coords)
            
            for j in range(len(polygon_coords) - 1):
                # QGC uses Qt's QLineF::intersects with BoundedIntersection
                # Implement same logic as Qt to match exactly
                p1 = polygon_coords[j]
                p2 = polygon_coords[j+1]
                
                # Line-line intersection (parametric form)
                # Line 1: line (rotated_x_top, rotated_y_top) -> (rotated_x_bottom, rotated_y_bottom)
                # Line 2: edge p1 -> p2
                x1, y1 = rotated_x_top, rotated_y_top
                x2, y2 = rotated_x_bottom, rotated_y_bottom
                x3, y3 = p1[0], p1[1]
                x4, y4 = p2[0], p2[1]
                
                denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
                
                # Improved tolerance for nearly-parallel lines (to match Qt behavior)
                PARALLEL_TOLERANCE = 1e-12  # More sensitive than 1e-10
                if abs(denom) > PARALLEL_TOLERANCE:
                    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
                    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
                    
                    # BoundedIntersection with epsilon for boundary cases (mimics Qt's fuzzy comparison)
                    # This catches intersections very close to line endpoints
                    BOUNDARY_EPSILON = 1e-9  # Small tolerance for boundary intersections
                    if (-BOUNDARY_EPSILON <= t <= 1 + BOUNDARY_EPSILON and 
                        -BOUNDARY_EPSILON <= u <= 1 + BOUNDARY_EPSILON):
                        # Calculate intersection point
                        intersect_x = x1 + t * (x2 - x1)
                        intersect_y = y1 + t * (y2 - y1)
                        
                        # Check for duplicates with geometric tolerance (mimics Qt's fuzzy point comparison)
                        # Qt's QPointF::operator== has built-in fuzzy comparison
                        DUPLICATE_TOLERANCE = 1e-9  # Points closer than this are considered same
                        is_duplicate = False
                        for existing in intersection_points:
                            dx = existing[0] - intersect_x
                            dy = existing[1] - intersect_y
                            dist_sq = dx * dx + dy * dy
                            if dist_sq < DUPLICATE_TOLERANCE * DUPLICATE_TOLERANCE:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            intersection_points.append((intersect_x, intersect_y))
            
            # QGC: if (intersections.count() > 1)
            if len(intersection_points) >= 2:
                # Find the two furthest points to form the transect (QGC line 553-568)
                max_distance = 0
                first_point = None
                second_point = None
                
                for i in range(len(intersection_points)):
                    for j in range(len(intersection_points)):
                        dx = intersection_points[j][0] - intersection_points[i][0]
                        dy = intersection_points[j][1] - intersection_points[i][1]
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance > max_distance:
                            max_distance = distance
                            first_point = intersection_points[i]
                            second_point = intersection_points[j]
                
                if first_point and second_point and max_distance > 0:
                    # Use the two furthest points as entry and exit
                    entry_utm = first_point
                    exit_utm = second_point
                    
                    # Calculate line direction for turnaround extension
                    line_vec_x = exit_utm[0] - entry_utm[0]
                    line_vec_y = exit_utm[1] - entry_utm[1]
                    line_length = math.sqrt(line_vec_x**2 + line_vec_y**2)
                    
                    # QGC FILTERING LOGIC for irregular polygons:
                    # Filter out transects with very short intersection length
                    # This matches QGC behavior for non-regular polygons
                    # Threshold: Keep transects with length >= spacing * 0.05
                    # Note: Reduced from 0.1 to 0.05 to match triangles and complex shapes
                    # Testing shows 0.05 achieves better accuracy for triangular polygons
                    min_intersection_threshold = spacing_m * 0.05
                    
                    if line_length >= min_intersection_threshold:
                        # Normalize vector
                        unit_x = line_vec_x / line_length
                        unit_y = line_vec_y / line_length
                        
                        # Extend beyond entry and exit for turnaround
                        start_extended = (
                            entry_utm[0] - unit_x * turnaround_distance_m,
                            entry_utm[1] - unit_y * turnaround_distance_m
                        )
                        end_extended = (
                            exit_utm[0] + unit_x * turnaround_distance_m,
                            exit_utm[1] + unit_y * turnaround_distance_m
                        )
                        
                        transects.append({
                            'start_utm': start_extended,
                            'end_utm': end_extended,
                            'intersection_length': line_length,  # For debugging
                            'x_position': transect_x,  # Track original position
                        })
            
            # Increment transect_x (QGC: transectX += gridSpacing)
            transect_x += spacing_m
        
        # QGC _adjustLineDirection (line 576-596):
        # Adjust line segments to all go the same direction
        if len(transects) > 0:
            # Get angle of first transect as reference
            first_start = transects[0]['start_utm']
            first_end = transects[0]['end_utm']
            dx = first_end[0] - first_start[0]
            dy = first_end[1] - first_start[1]
            first_angle = math.degrees(math.atan2(dy, dx))
            
            # Adjust other transects to match direction
            for i, transect in enumerate(transects):
                if i == 0:
                    continue
                
                start = transect['start_utm']
                end = transect['end_utm']
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                current_angle = math.degrees(math.atan2(dy, dx))
                
                # QGC: if (qAbs(line.angle() - firstAngle) > 1.0)
                # Handle angle wrapping [-180, 180]
                angle_diff = abs(current_angle - first_angle)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                
                if angle_diff > 1.0:
                    # Reverse this transect
                    transect['start_utm'] = end
                    transect['end_utm'] = start
        
        # Transform transects from local NED to WGS84
        # QGC convertNedToGeo implementation (QGCGeo.cc lines 65-93)
        for transect in transects:
            # transect coordinates are (East, North) in meters
            start_east, start_north = transect['start_utm']
            end_east, end_north = transect['end_utm']
            
            # Convert start point
            x_rad = start_north / self._WGS84_a  # x is North
            y_rad = start_east / self._WGS84_a   # y is East
            c = math.sqrt(x_rad * x_rad + y_rad * y_rad)
            sin_c = math.sin(c)
            cos_c = math.cos(c)
            
            ref_lon_rad = math.radians(self._tangent_origin_lon)
            ref_lat_rad = math.radians(self._tangent_origin_lat)
            ref_sin_lat = math.sin(ref_lat_rad)
            ref_cos_lat = math.cos(ref_lat_rad)
            
            if abs(c) > self._epsilon:
                lat_rad = math.asin(cos_c * ref_sin_lat + (x_rad * sin_c * ref_cos_lat) / c)
                lon_rad = ref_lon_rad + math.atan2(y_rad * sin_c, c * ref_cos_lat * cos_c - x_rad * ref_sin_lat * sin_c)
            else:
                lat_rad = ref_lat_rad
                lon_rad = ref_lon_rad
            
            start_lat = math.degrees(lat_rad)
            start_lon = math.degrees(lon_rad)
            
            # Convert end point
            x_rad = end_north / self._WGS84_a
            y_rad = end_east / self._WGS84_a
            c = math.sqrt(x_rad * x_rad + y_rad * y_rad)
            sin_c = math.sin(c)
            cos_c = math.cos(c)
            
            if abs(c) > self._epsilon:
                lat_rad = math.asin(cos_c * ref_sin_lat + (x_rad * sin_c * ref_cos_lat) / c)
                lon_rad = ref_lon_rad + math.atan2(y_rad * sin_c, c * ref_cos_lat * cos_c - x_rad * ref_sin_lat * sin_c)
            else:
                lat_rad = ref_lat_rad
                lon_rad = ref_lon_rad
            
            end_lat = math.degrees(lat_rad)
            end_lon = math.degrees(lon_rad)
            
            transect['start'] = [start_lat, start_lon]
            transect['end'] = [end_lat, end_lon]
        
        # Apply entry location and alternating pattern
        transects = self._apply_entry_and_alternating(transects, entry_location)
        
        return transects
    
    def _generate_waypoints_on_transects(
        self,
        transects: List[Dict],
        spacing_m: float,
        altitude: float,
        polygon: List[List[float]],
        polygon_components: Optional[List[List[List[float]]]] = None,
    ) -> Tuple[List[Dict], List[List[float]], float]:
        """
        QGC-style waypoint generation using local projected CRS (AEQD).
        Prevents longitude wrapping artifacts and matches QGC geometry behavior.
        """

        # ------------------------------------------------------------------
        # 1️⃣ Choose local origin (polygon centroid – QGC style)
        # ------------------------------------------------------------------
        ref_lat = sum(p[0] for p in polygon) / len(polygon)
        ref_lon = sum(p[1] for p in polygon) / len(polygon)

        to_xy = Transformer.from_crs(
            "EPSG:4326",
            f"+proj=aeqd +lat_0={ref_lat} +lon_0={ref_lon}",
            always_xy=True,
        ).transform

        to_ll = Transformer.from_crs(
            f"+proj=aeqd +lat_0={ref_lat} +lon_0={ref_lon}",
            "EPSG:4326",
            always_xy=True,
        ).transform

        # ------------------------------------------------------------------
        # 2️⃣ Build polygon geometry in XY (meters)
        # ------------------------------------------------------------------
        polygon_loops = polygon_components if polygon_components else [polygon]
        polygon_geoms = []

        for loop in polygon_loops:
            if not loop or len(loop) < 3:
                continue

            coords_xy = [to_xy(pt[1], pt[0]) for pt in loop]
            poly = Polygon(coords_xy)

            if not poly.is_valid:
                poly = poly.buffer(0)

            if not poly.is_empty:
                polygon_geoms.append(poly)

        if not polygon_geoms:
            return [], [], 0.0

        shapely_poly = unary_union(polygon_geoms)


        all_waypoints = []
        visual_points = []
        total_distance_in_polygon = 0.0

        for transect in transects:
            start = transect["start"]  # [lat, lon]
            end = transect["end"]
            forward = transect.get("forward", True)

            start_xy = to_xy(start[1], start[0])
            end_xy = to_xy(end[1], end[0])

            line = LineString([start_xy, end_xy])
            intersection = line.intersection(shapely_poly)

            if intersection.is_empty:
                continue

            if intersection.geom_type == "MultiLineString":
                segment = max(intersection.geoms, key=lambda g: g.length)
            elif intersection.geom_type == "LineString":
                segment = intersection
            else:
                continue

            coords = list(segment.coords)
            if len(coords) < 2:
                continue

            entry_x, entry_y = coords[0]
            exit_x, exit_y = coords[-1]

            entry_lon, entry_lat = to_ll(entry_x, entry_y)
            exit_lon, exit_lat = to_ll(exit_x, exit_y)


            dist_in_polygon = geodesic(
                (entry_lat, entry_lon),
                (exit_lat, exit_lon),
            ).meters

            total_distance_in_polygon += dist_in_polygon

            if forward:
                wp = [
                    {"lat": start[0], "lon": start[1], "alt": altitude, "type": "turnaround_start"},
                    {"lat": entry_lat, "lon": entry_lon, "alt": altitude, "type": "entry"},
                    {"lat": exit_lat, "lon": exit_lon, "alt": altitude, "type": "exit"},
                    {"lat": end[0], "lon": end[1], "alt": altitude, "type": "turnaround_end"},
                ]
                visual_points.extend([
                    [start[0], start[1]],
                    [entry_lat, entry_lon],
                    [exit_lat, exit_lon],
                    [end[0], end[1]],
                ])
            else:
                wp = [
                    {"lat": end[0], "lon": end[1], "alt": altitude, "type": "turnaround_start"},
                    {"lat": exit_lat, "lon": exit_lon, "alt": altitude, "type": "entry"},
                    {"lat": entry_lat, "lon": entry_lon, "alt": altitude, "type": "exit"},
                    {"lat": start[0], "lon": start[1], "alt": altitude, "type": "turnaround_end"},
                ]
                visual_points.extend([
                    [end[0], end[1]],
                    [exit_lat, exit_lon],
                    [entry_lat, entry_lon],
                    [start[0], start[1]],
                ])

            all_waypoints.extend(wp)

        return all_waypoints, visual_points, total_distance_in_polygon
    
    def _build_qgc_structure(
        self,
        waypoints: List[Dict],
        polygon: List[List[float]],
        takeoff_point: List[float],
        altitude: float,
        cruise_speed: float,
        hover_speed: float,
        angle: float,
        frontal_overlap: float,
        side_overlap: float,
        entry_location: int,
        footprint: Dict,
        photo_spacing: float,
        visual_points: List[List[float]],
        turnaround_distance: float,
        camera_shots: int,
        return_to_home: bool,
        review=False,
        hover_and_capture: bool = False,
        camera_trigger_in_turnaround: bool = False,
        refly_90_degrees: bool = False,
        transects_hover: List[Dict] = None,
    ) -> Dict:
        """Build complete QGC mission structure matching QGC format"""
        
        # Build mission items
        items = []
        do_jump_id = 1
        
        # 1. Add Camera Mode command (MAV_CMD_SET_CAMERA_MODE)
        if not review:
            items.append({
                "autoContinue": True,
                "command": 530,  # MAV_CMD_SET_CAMERA_MODE
                "doJumpId": do_jump_id,
                "frame": 2,
                "params": [0, 2, None, None, None, None, None],  # Camera mode = 2 (photo)
                "type": "SimpleItem"
            })
            do_jump_id += 1
        else:
            items.append({
                "autoContinue": True,
                "command": {"id": 530, "name": "MAV_CMD_SET_CAMERA_MODE"},  # MAV_CMD_SET_CAMERA_MODE
                "doJumpId": do_jump_id,
                "frame": {"id": 2, "name": "MISSION"},
                "params": [0, 2, None, None, None, None, None],  # Camera mode = 2 (photo)
                "type": "SimpleItem"
            })
            do_jump_id += 1
        # 2. Takeoff with user-selected position
        takeoff_lat, takeoff_lon = takeoff_point[0], takeoff_point[1]
        if not review:
            items.append({
                "AMSLAltAboveTerrain": None,
                "Altitude": altitude,
                "AltitudeMode": 1,
                "autoContinue": True,
                "command": 22,  # MAV_CMD_NAV_TAKEOFF
                "doJumpId": do_jump_id,
                "frame": 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                "params": [0, 0, 0, None, takeoff_lat, takeoff_lon, altitude],
                "type": "SimpleItem"
            })
            do_jump_id += 1
        else:
            items.append({
                "AMSLAltAboveTerrain": None,
                "Altitude": altitude,
                "AltitudeMode": 1,
                "autoContinue": True,
                "command": {"id": 22, "name": "MAV_CMD_NAV_TAKEOFF"},  # MAV_CMD_NAV_TAKEOFF
                "doJumpId": do_jump_id,
                "frame": {"id": 3, "name": "GLOBAL_RELATIVE_ALT"},
                "params": [0, 0, 0, None, takeoff_lat, takeoff_lon, altitude],
                "type": "SimpleItem"
            })
            do_jump_id += 1
        
        # 2. Build survey items based on mode
        # HoverAndCapture vs Continuous Trigger are COMPLETELY DIFFERENT patterns
        if hover_and_capture:
            # MODE: HoverAndCapture - Dense waypoints with individual photo captures
            survey_items = self._build_hover_and_capture_items(
                transects_hover or [], altitude, do_jump_id, review, camera_trigger_in_turnaround
            )
        else:
            # MODE: Continuous Trigger (default) - Sparse waypoints with distance-based trigger
            survey_items = self._build_continuous_trigger_items(
                waypoints, photo_spacing, altitude, do_jump_id, camera_trigger_in_turnaround, review
            )
        
        # Update do_jump_id (helper functions manage their own IDs internally, but we need final count)
        # Note: We don't need to update do_jump_id here as it's passed by value
        
        # 3. Complex item wrapper (use calculated camera_shots, not counted from items)
        items.append({
            "TransectStyleComplexItem": {
                "CameraCalc": {
                    "AdjustedFootprintFrontal": footprint['frontal'],
                    "AdjustedFootprintSide": footprint['side'],
                    "CameraName": DEFAULT_CAMERA['camera_name'],
                    "DistanceMode": 1,
                    "DistanceToSurface": altitude,
                    "version": 2
                },
                "CameraShots": camera_shots,  
                "CameraTriggerInTurnAround": camera_trigger_in_turnaround,  # Apply option
                "HoverAndCapture": hover_and_capture,  # Apply option
                "Items": survey_items,
                "Refly90Degrees": refly_90_degrees,  # Apply option
                "TurnAroundDistance": turnaround_distance,
                "VisualTransectPoints": visual_points,
                "version": 2
            },
            "angle": int(angle),
            "complexItemType": "survey",
            "entryLocation": entry_location,
            "flyAlternateTransects": False,
            "polygon": polygon,
            "splitConcavePolygons": False,
            "type": "ComplexItem",
            "version": 5
        })
        
        # 4. End mission command (RTL or LAND)
        if return_to_home:
            if not review:
                items.append({
                    "autoContinue": True,
                    "command": 20,  # MAV_CMD_NAV_RETURN_TO_LAUNCH
                    "doJumpId": do_jump_id,
                    "frame": 2,
                    "params": [0, 0, 0, 0, 0, 0, 0],
                    "type": "SimpleItem"
                })
            else:
                items.append({
                    "autoContinue": True,
                    "command": {"id": 20, "name": "MAV_CMD_NAV_RETURN_TO_LAUNCH"},
                    "doJumpId": do_jump_id,
                    "frame": {"id": 2, "name": "MISSION"},
                    "params": [0, 0, 0, 0, 0, 0, 0],
                    "type": "SimpleItem"
                })
        else:
            # LAND at the last navigation waypoint location (scan survey_items backwards)
            landing_lat = takeoff_lat
            landing_lon = takeoff_lon
            try:
                for si in reversed(survey_items or []):
                    cmd = si.get('command')
                    cmd_id = cmd.get('id') if isinstance(cmd, dict) else cmd
                    if cmd_id != 16:
                        continue
                    params = si.get('params', [])
                    if isinstance(params, list) and len(params) >= 6:
                        landing_lat = params[4]
                        landing_lon = params[5]
                    break
            except Exception:
                pass

            if not review:
                items.append({
                    "autoContinue": True,
                    "command": 21,  # MAV_CMD_NAV_LAND
                    "doJumpId": do_jump_id,
                    "frame": 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                    "params": [0, 0, 0, None, landing_lat, landing_lon, 0],
                    "type": "SimpleItem"
                })
            else:
                items.append({
                    "autoContinue": True,
                    "command": {"id": 21, "name": "MAV_CMD_NAV_LAND"},
                    "doJumpId": do_jump_id,
                    "frame": {"id": 3, "name": "GLOBAL_RELATIVE_ALT"},
                    "params": [0, 0, 0, None, landing_lat, landing_lon, 0],
                    "type": "SimpleItem"
                })
        return {
            "fileType": "Plan",
            "geoFence": {"circles": [], "polygons": [], "version": 2},
            "groundStation": "QGroundControl",
            "mission": {
                "cruiseSpeed": cruise_speed,
                "firmwareType": 12,  # ArduPilotMega (was 3 = PX4)
                "globalPlanAltitudeMode": 1,
                "hoverSpeed": hover_speed,
                "items": items,
                "plannedHomePosition": [takeoff_point[0], takeoff_point[1], 11],  # Same as takeoff for return
                "vehicleType": 2,  # Copter
                "version": 2
            },
            "rallyPoints": {"points": [], "version": 2},
            "version": 1
        }
    
    # ========== HELPER METHODS ==========
    
    def _apply_entry_and_alternating(
        self, transects: List[Dict], entry_location: int
    ) -> List[Dict]:
        """Apply entry location and alternating pattern"""
        if not transects:
            return transects
        
        # Reverse if entry is on right (2, 3)
        if entry_location in [2, 3]:
            transects = list(reversed(transects))
        
        # Apply alternating pattern (zigzag)
        for i, transect in enumerate(transects):
            transect['forward'] = (i % 2 == 0)
        
        return transects
    
    def _calculate_polygon_area(self, polygon: List[List[float]]) -> float:
        """Calculate polygon area in km² using Shoelace formula"""
        if len(polygon) < 3:
            return 0.0
        
        # Convert to radians
        coords = [(math.radians(p[0]), math.radians(p[1])) for p in polygon]
        
        # Shoelace formula
        area = 0.0
        for i in range(len(coords)):
            j = (i + 1) % len(coords)
            area += coords[i][1] * coords[j][0]
            area -= coords[j][1] * coords[i][0]
        
        area = abs(area) / 2.0
        
        # Convert to km² (approximate)
        earth_radius_km = 6371
        area_km2 = area * (earth_radius_km ** 2)
        
        return area_km2

    def _calculate_polygon_area_multi(
        self,
        polygons: Optional[List[List[List[float]]]],
        fallback_polygon: List[List[float]],
    ) -> float:
        total_area = 0.0
        if polygons:
            for loop in polygons:
                if loop and len(loop) >= 3:
                    total_area += self._calculate_polygon_area(loop)

        if total_area > 0:
            return total_area

        return self._calculate_polygon_area(fallback_polygon)
    
    def _calculate_total_distance(self, waypoints: List[Dict]) -> float:
        """Calculate total distance in km"""
        if len(waypoints) < 2:
            return 0.0
        
        total_km = 0.0
        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]
            total_km += geodesic((wp1['lat'], wp1['lon']), (wp2['lat'], wp2['lon'])).kilometers
        
        return total_km
    
    def divide_mission_for_multiple_drones(
        self,
        waypoints: List[Dict],
        total_distance_km: float,
        maximum_drones: int,
        transects: List[Dict],
        available_devices: List[Dict] = None,
        cruise_speed: Optional[float] = None,
        hover_speed: float = 5.0,
        qgc_mission_data: Dict = None
    ) -> List[Dict]:
        """
        Chia mission thành nhiều phần cho nhiều drone
        
        Args:
            waypoints: Danh sách tất cả waypoints
            total_distance_km: Tổng khoảng cách bay
            maximum_drones: Số drone tối đa
            transects: Danh sách transects
            available_devices: Danh sách device active từ database
            cruise_speed: Tốc độ bay cruise (m/s)
            hover_speed: Tốc độ hover (m/s)
            qgc_mission_data: Dữ liệu QGC mission gốc để lấy command và frame
            
        Returns:
            List[Dict]: Mỗi dict chứa thông tin cho 1 drone
            {
                'drone_id': int,
                'device_id': int,      # ID của device thực tế
                'device_name': str,    # Tên device
                'device_serial': str,  # Serial number của device
                'start_waypoint': int,  # Index của waypoint bắt đầu
                'end_waypoint': int,   # Index của waypoint kết thúc
                'start_transect': int, # Index của transect bắt đầu
                'end_transect': int,   # Index của transect kết thúc
                'distance_km': float,  # Khoảng cách drone này phải bay
                'waypoints': List[Dict], # Waypoints cho drone này
                'takeoff_point': [lat, lon], # Điểm cất cánh
                'landing_point': [lat, lon], # Điểm hạ cánh
            }
        """
        # Lấy danh sách device active từ database nếu không có sẵn
        if available_devices is None:
            from devices.models import Device
            available_devices = list(Device.objects.filter(
                active=True,
                main_type__name__icontains='drone'  # Chỉ lấy device có type là drone
            ).values('id', 'name', 'serial_number')[:maximum_drones])
        
        # Đảm bảo có đủ device cho số drone yêu cầu
        actual_drone_count = min(len(available_devices), maximum_drones)
        if actual_drone_count == 0:
            # Nếu không có device nào, tạo device giả
            available_devices = [{'id': i, 'name': f'Drone {i}', 'serial_number': f'DRONE-{i:03d}'} for i in range(1, maximum_drones + 1)]
            actual_drone_count = maximum_drones
        
        if actual_drone_count <= 1:
            # Chỉ có 1 drone, trả về toàn bộ mission
            device = available_devices[0] if available_devices else {'id': 1, 'name': 'Drone 1', 'serial_number': 'DRONE-001'}
            return [{
                'drone_id': 1,
                'device_id': device['id'],
                'device_name': device['name'],
                'device_serial': device['serial_number'],
                'start_waypoint': 0,
                'end_waypoint': len(waypoints) - 1,
                'start_transect': 0,
                'end_transect': len(transects) - 1,
                'distance_km': total_distance_km,
                'waypoints': waypoints,
                'takeoff_point': [waypoints[0]['lat'], waypoints[0]['lon']] if waypoints else [0, 0],
                'landing_point': [waypoints[-1]['lat'], waypoints[-1]['lon']] if waypoints else [0, 0],
            }]
        
        # Tính số transects mỗi drone phải bay
        total_transects = len(transects)
        transects_per_drone = total_transects // actual_drone_count
        remaining_transects = total_transects % actual_drone_count
        
        # Mỗi transect có 4 waypoints: turnaround_start, entry, exit, turnaround_end
        waypoints_per_transect = 4
        
        drone_missions = []
        current_transect_index = 0
        current_waypoint_index = 0
        
        for drone_id in range(1, actual_drone_count + 1):
            # Tính số transects cho drone này
            if drone_id <= remaining_transects:
                # Drone đầu tiên sẽ bay thêm 1 transect nếu có dư
                drone_transect_count = transects_per_drone + 1
            else:
                drone_transect_count = transects_per_drone
            
            # Tính chỉ số transect kết thúc
            end_transect_index = current_transect_index + drone_transect_count - 1
            
            # Đảm bảo không vượt quá số transects có sẵn
            if end_transect_index >= total_transects:
                end_transect_index = total_transects - 1
            
            # Tính chỉ số waypoint kết thúc
            end_waypoint_index = current_waypoint_index + (drone_transect_count * waypoints_per_transect) - 1
            
            # Đảm bảo không vượt quá số waypoints có sẵn
            if end_waypoint_index >= len(waypoints):
                end_waypoint_index = len(waypoints) - 1
            
            # Tính khoảng cách thực tế cho drone này
            drone_distance = 0.0
            for i in range(current_waypoint_index, end_waypoint_index):
                if i < len(waypoints) - 1:
                    wp1 = waypoints[i]
                    wp2 = waypoints[i + 1]
                    drone_distance += geodesic((wp1['lat'], wp1['lon']), (wp2['lat'], wp2['lon'])).kilometers
            
            # Lấy waypoints cho drone này
            drone_waypoints_raw = waypoints[current_waypoint_index:end_waypoint_index + 1]
            
            # Lấy QGC items từ mission data để lấy command và frame
            qgc_items = qgc_mission_data.get('mission', {}).get('items', []) if qgc_mission_data else []
            
            # Chuyển đổi waypoints sang format QGC
            drone_waypoints = []
            for i, wp in enumerate(drone_waypoints_raw):
                # Tìm QGC item tương ứng với waypoint này
                qgc_item = None
                if i < len(qgc_items):
                    qgc_item = qgc_items[i]
                
                # Lấy command và frame từ QGC item hoặc dùng default
                command = qgc_item.get('command', 16) if qgc_item else 16  # MAV_CMD_NAV_WAYPOINT
                frame = qgc_item.get('frame', 3) if qgc_item else 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                auto_continue = qgc_item.get('autoContinue', True) if qgc_item else True
                
                drone_waypoints.append({
                    "autoContinue": auto_continue,
                    "command": command,
                    "doJumpId": current_waypoint_index + i + 1,
                    "frame": frame,
                    "params": [
                        0,  # Hold time
                        0,  # Acceptance radius
                        0,  # Pass radius
                        None,  # Yaw angle
                        wp['lat'],  # Latitude
                        wp['lon'],  # Longitude
                        wp['alt']   # Altitude
                    ],
                    "type": "SimpleItem",
                    "waypoint_type": wp['type'],  # Giữ lại thông tin loại waypoint
                    "lat": wp['lat'],
                    "lon": wp['lon'],
                    "alt": wp['alt']
                })
            
            # Xác định điểm cất cánh và hạ cánh
            takeoff_point = [drone_waypoints_raw[0]['lat'], drone_waypoints_raw[0]['lon']] if drone_waypoints_raw else [0, 0]
            landing_point = [drone_waypoints_raw[-1]['lat'], drone_waypoints_raw[-1]['lon']] if drone_waypoints_raw else [0, 0]
            
            # Lấy thông tin device cho drone này
            device = available_devices[drone_id - 1] if drone_id <= len(available_devices) else {'id': drone_id, 'name': f'Drone {drone_id}', 'serial_number': f'DRONE-{drone_id:03d}'}
            
            # Lấy thông tin transects cho drone này
            drone_transects = transects[current_transect_index:end_transect_index + 1] if end_transect_index < len(transects) else transects[current_transect_index:]
            
            # Tính toán thống kê chi tiết
            total_transect_count = len(drone_transects)
            total_waypoint_count = len(drone_waypoints)
            
            # Tạo route path chi tiết
            route_path = []
            for i, wp in enumerate(drone_waypoints_raw):
                route_path.append({
                    'order': i + 1,
                    'waypoint_index': current_waypoint_index + i,
                    'lat': wp['lat'],
                    'lon': wp['lon'],
                    'alt': wp['alt'],
                    'type': wp['type'],
                    'description': self._get_waypoint_description(wp['type'], i, total_waypoint_count)
                })
            
            # Tạo QGC command items cho drone này
            qgc_command_items = self._create_qgc_command_items_for_drone(
                drone_waypoints_raw, 
                drone_id, 
                current_waypoint_index,
                qgc_mission_data
            )
            
            # Tạo transect path chi tiết
            transect_path = []
            for i, transect in enumerate(drone_transects):
                transect_path.append({
                    'transect_index': current_transect_index + i,
                    'order': i + 1,
                    'entry_point': transect.get('entry', {}),
                    'exit_point': transect.get('exit', {}),
                    'turnaround_start': transect.get('turnaround_start', {}),
                    'turnaround_end': transect.get('turnaround_end', {}),
                    'length_km': transect.get('length_km', 0),
                    'description': f"Transect {current_transect_index + i + 1} - {transect.get('description', 'Survey line')}"
                })
            
            drone_missions.append({
                'drone_id': drone_id,
                'device_id': device['id'],
                'device_name': device['name'],
                'device_serial': device['serial_number'],
                'start_waypoint': current_waypoint_index,
                'end_waypoint': end_waypoint_index,
                'start_transect': current_transect_index,
                'end_transect': end_transect_index,
                'distance_km': round(drone_distance, 2),
                'waypoints': drone_waypoints,
                'takeoff_point': takeoff_point,
                'landing_point': landing_point,
                # Thông tin chi tiết mới
                'route_path': route_path,
                'transect_path': transect_path,
                'qgc_command_items': qgc_command_items,
                'statistics': {
                    'total_transects': total_transect_count,
                    'total_waypoints': total_waypoint_count,
                    'average_transect_length_km': round(drone_distance / total_transect_count, 2) if total_transect_count > 0 else 0,
                    'waypoints_per_transect': round(total_waypoint_count / total_transect_count, 1) if total_transect_count > 0 else 0
                }
            })
            
            # Cập nhật cho drone tiếp theo
            current_transect_index = end_transect_index + 1
            current_waypoint_index = end_waypoint_index + 1
        
        return drone_missions
    
    def _get_waypoint_description(self, waypoint_type: str, order: int, total_waypoints: int) -> str:
        """
        Tạo mô tả cho waypoint dựa trên loại và thứ tự
        
        Args:
            waypoint_type: Loại waypoint (turnaround_start, entry, exit, turnaround_end)
            order: Thứ tự trong danh sách waypoints của drone
            total_waypoints: Tổng số waypoints của drone
            
        Returns:
            str: Mô tả chi tiết của waypoint
        """
        descriptions = {
            'turnaround_start': 'Bắt đầu quay đầu',
            'entry': 'Điểm vào transect',
            'exit': 'Điểm ra khỏi transect', 
            'turnaround_end': 'Kết thúc quay đầu',
            'takeoff': 'Điểm cất cánh',
            'landing': 'Điểm hạ cánh',
            'rtl': 'Trở về nhà'
        }
        
        base_description = descriptions.get(waypoint_type, 'Waypoint')
        
        # Thêm thông tin về thứ tự
        if order == 0:
            return f"{base_description} - Điểm bắt đầu"
        elif order == total_waypoints - 1:
            return f"{base_description} - Điểm kết thúc"
        else:
            return f"{base_description} - Điểm thứ {order + 1}"
    
    def _create_qgc_command_items_for_drone(
        self, 
        drone_waypoints: List[Dict], 
        drone_id: int, 
        start_waypoint_index: int,
        qgc_mission_data: Dict = None
    ) -> List[Dict]:
        """
        Tạo QGC command items cho drone để điều khiển
        
        Args:
            drone_waypoints: Danh sách waypoints của drone
            drone_id: ID của drone
            start_waypoint_index: Index bắt đầu của waypoint trong mission tổng
            qgc_mission_data: Dữ liệu QGC mission gốc để lấy command và frame
            
        Returns:
            List[Dict]: Danh sách QGC command items
        """
        # Lấy QGC items từ mission data
        qgc_items = qgc_mission_data.get('mission', {}).get('items', []) if qgc_mission_data else []
        
        command_items = []
        do_jump_id = start_waypoint_index + 1  # Bắt đầu từ 1
        
        # 1. Takeoff command
        if drone_waypoints:
            first_wp = drone_waypoints[0]
            # Tìm QGC item tương ứng với takeoff command
            takeoff_item = None
            for item in qgc_items:
                if item.get('command') == 22:  # MAV_CMD_NAV_TAKEOFF
                    takeoff_item = item
                    break
            
            command_items.append({
                "autoContinue": takeoff_item.get('autoContinue', True) if takeoff_item else True,
                "command": 22,  # MAV_CMD_NAV_TAKEOFF
                "doJumpId": do_jump_id,
                "frame": takeoff_item.get('frame', 3) if takeoff_item else 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                "params": [
                    0,  # Minimum pitch
                    0,  # Empty
                    0,  # Empty
                    None,  # Yaw angle
                    first_wp['lat'],  # Latitude
                    first_wp['lon'],  # Longitude
                    first_wp['alt']   # Altitude
                ],
                "type": "SimpleItem"
            })
            do_jump_id += 1
        
        # 2. Waypoint commands
        for i, wp in enumerate(drone_waypoints):
            # Tìm QGC item tương ứng với waypoint này
            qgc_item = None
            if i < len(qgc_items):
                qgc_item = qgc_items[i]
            
            # Lấy command và frame từ QGC item hoặc dùng default
            command = qgc_item.get('command', 16) if qgc_item else 16  # MAV_CMD_NAV_WAYPOINT
            frame = qgc_item.get('frame', 3) if qgc_item else 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT
            auto_continue = qgc_item.get('autoContinue', True) if qgc_item else True
            
            command_items.append({
                "autoContinue": auto_continue,
                "command": command,
                "doJumpId": do_jump_id,
                "frame": frame,
                "params": [
                    0,  # Hold time
                    0,  # Acceptance radius
                    0,  # Pass radius
                    None,  # Yaw angle
                    wp['lat'],  # Latitude
                    wp['lon'],  # Longitude
                    wp['alt']   # Altitude
                ],
                "type": "SimpleItem"
            })
            do_jump_id += 1
        
        # 3. End mission command (RTL or LAND) - inferred from qgc_mission_data
        if drone_waypoints:
            end_item = None
            end_cmd = None
            try:
                for item in reversed(qgc_items):
                    cmd = item.get('command')
                    if cmd in (20, 21):  # RTL or LAND
                        end_item = item
                        end_cmd = cmd
                        break
            except Exception:
                end_item = None
                end_cmd = None

            if end_cmd == 21:
                # LAND
                landing_lat = drone_waypoints[-1].get('lat', 0)
                landing_lon = drone_waypoints[-1].get('lon', 0)
                try:
                    params = end_item.get('params', []) if isinstance(end_item, dict) else []
                    if isinstance(params, list) and len(params) >= 6:
                        landing_lat = params[4] if params[4] not in (None, 0, 0.0) else landing_lat
                        landing_lon = params[5] if params[5] not in (None, 0, 0.0) else landing_lon
                except Exception:
                    pass

                command_items.append({
                    "autoContinue": end_item.get('autoContinue', True) if end_item else True,
                    "command": 21,  # MAV_CMD_NAV_LAND
                    "doJumpId": do_jump_id,
                    "frame": end_item.get('frame', 3) if end_item else 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                    "params": [0, 0, 0, None, landing_lat, landing_lon, 0],
                    "type": "SimpleItem"
                })
            else:
                # Default to RTL
                rtl_item = end_item if end_cmd == 20 else None
                command_items.append({
                    "autoContinue": rtl_item.get('autoContinue', True) if rtl_item else True,
                    "command": 20,  # MAV_CMD_NAV_RETURN_TO_LAUNCH
                    "doJumpId": do_jump_id,
                    "frame": rtl_item.get('frame', 3) if rtl_item else 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                    "params": [0, 0, 0, None, 0, 0, 0],
                    "type": "SimpleItem"
                })
        
        return command_items
    
    def _generate_dense_waypoints_along_transect(self, entry_coord, exit_coord, spacing, altitude):
        """
        Generate dense waypoints along a transect for HoverAndCapture mode
        Based on QGC logic: SurveyComplexItem.cc line 817-829
        
        For HoverAndCapture, we need a waypoint every `spacing` meters along the transect
        to trigger individual photo captures
        
        Args:
            entry_coord: (lat, lon) of transect entry point
            exit_coord: (lat, lon) of transect exit point
            spacing: Distance between waypoints in meters (triggerDistance)
            altitude: Flight altitude
            
        Returns:
            List of dense waypoint dicts with 'lat', 'lon', 'alt', 'type'='interior_hover'
        """
        import math
        
        transect_length = self._qt_distance(entry_coord[0], entry_coord[1], exit_coord[0], exit_coord[1])
        azimuth = self._qt_azimuth(entry_coord[0], entry_coord[1], exit_coord[0], exit_coord[1])
        
        # Generate dense waypoints along transect
        dense_waypoints = []
        
        if spacing > 0 and spacing < transect_length:
            # QGC logic: Generate points at spacing intervals until we reach/exceed transect length
            # This ensures we don't miss points near the exit
            num_inner_points = int(math.ceil(transect_length / spacing))
            
            for i in range(num_inner_points):
                distance_from_entry = spacing * (i + 1)
                
                # Stop if we've exceeded transect length (safety check)
                if distance_from_entry > transect_length:
                    break
                
                # Calculate new coordinate at distance and azimuth from entry
                lat, lon = self._qt_at_distance_azimuth(
                    entry_coord[0], entry_coord[1], distance_from_entry, azimuth
                )
                
                dense_waypoints.append({
                    'lat': lat,
                    'lon': lon,
                    'alt': altitude,
                    'type': 'interior_hover'  # Special type for HoverAndCapture waypoints
                })
        
        return dense_waypoints
    
    def _build_hover_and_capture_items(self, transects, altitude, do_jump_id, review, camera_trigger_in_turnaround=True):
        """Build survey items for HoverAndCapture mode (dense waypoints with image capture)."""
        survey_items = []
        hover_delay = 4  # seconds - matches QGC _hoverAndCaptureDelaySeconds

        for transect in transects:
            coord_list = transect.get('coord_infos', [])
            if not transect.get('forward', True):
                coord_list = list(reversed(coord_list))

            for coord in coord_list:
                coord_type = coord.get('type')
                is_turnaround = coord_type in ('turnaround_start', 'turnaround_end')

                lat = coord['lat']
                lon = coord['lon']
                alt = coord['alt']

                delay = hover_delay if coord_type in ('entry', 'interior_hover', 'exit') else 0
                params = [delay if not is_turnaround else 0, 0, 0, None, lat, lon, alt]

                payload = {
                    "autoContinue": True,
                    "doJumpId": do_jump_id,
                    "params": params,
                    "type": "SimpleItem",
                }
                if not review:
                    payload.update({"command": 16, "frame": 3})
                else:
                    payload.update({
                        "command": {"id": 16, "name": "MAV_CMD_NAV_WAYPOINT"},
                        "frame": {"id": 3, "name": "GLOBAL_RELATIVE_ALT"},
                    })
                survey_items.append(payload)
                do_jump_id += 1

                if coord_type in ('entry', 'interior_hover', 'exit'):
                    capture_payload = {
                        "autoContinue": True,
                        "doJumpId": do_jump_id,
                        # MAV_CMD_DO_DIGICAM_CONTROL params:
                        # [session, zoom, step, focus_lock, command, id, unused]
                        # Use param5=1 to trigger capture.
                        "params": [0, 0, 0, 0, 1, 0, 0],
                        "type": "SimpleItem",
                    }
                    if not review:
                        capture_payload.update({"command": 203, "frame": 2})
                    else:
                        capture_payload.update({
                            "command": {"id": 203, "name": "MAV_CMD_DO_DIGICAM_CONTROL"},
                            "frame": {"id": 2, "name": "MISSION"},
                        })
                    survey_items.append(capture_payload)
                    do_jump_id += 1

        return survey_items
    
    def _build_continuous_trigger_items(self, waypoints, photo_spacing, altitude, do_jump_id, camera_trigger_in_turnaround, review):
        """
        Build survey items for Continuous Trigger mode (default)
        Based on QGC logic: TransectStyleComplexItem.cc line 1268-1270, 1286-1288
        
        Continuous mode:
        - Use only entry/exit waypoints (sparse)
        - Start continuous trigger (206) at entry with distance
        - Stop continuous trigger (206) at exit with distance=0
        - Optionally include turnaround waypoints
        
        Args:
            waypoints: List of transect waypoints
            photo_spacing: Distance between photos (triggerDistance)
            altitude: Flight altitude
            do_jump_id: Starting doJumpId
            camera_trigger_in_turnaround: Whether to trigger in turnarounds
            review: Whether this is for review/preview mode
            
        Returns:
            List of QGC mission items (SimpleItem format)
        """
        survey_items = []
        last_coord = None
        
        for wp in waypoints:
            wp_type = wp.get('type')
            
            # Add waypoint
            if not review:
                survey_items.append({
                    "autoContinue": True,
                    "command": 16,
                    "doJumpId": do_jump_id,
                    "frame": 3,
                    "params": [0, 0, 0, None, wp['lat'], wp['lon'], wp['alt']],
                    "type": "SimpleItem"
                })
            else:
                survey_items.append({
                    "autoContinue": True,
                    "command": {"id": 16, "name": "MAV_CMD_NAV_WAYPOINT"},
                    "doJumpId": do_jump_id,
                    "frame": {"id": 3, "name": "GLOBAL_RELATIVE_ALT"},
                    "params": [0, 0, 0, None, wp['lat'], wp['lon'], wp['alt']],
                    "type": "SimpleItem"
                })
            do_jump_id += 1
            last_coord = (wp['lat'], wp['lon'], wp['alt'])
            
            # Add camera trigger commands
            if wp_type == 'entry':
                # START continuous triggering
                lat_param, lon_param, alt_param = last_coord if last_coord else (wp['lat'], wp['lon'], wp['alt'])
                if not review:
                    survey_items.append({
                        "autoContinue": True,
                        "command": 206,  # MAV_CMD_DO_SET_CAM_TRIGG_DIST
                        "doJumpId": do_jump_id,
                        "frame": 2,
                        "params": [photo_spacing, 0, 1, 0, lat_param, lon_param, alt_param],
                        "type": "SimpleItem"
                    })
                else:
                    survey_items.append({
                        "autoContinue": True,
                        "command": {"id": 206, "name": "MAV_CMD_DO_SET_CAM_TRIGG_DIST"},
                        "doJumpId": do_jump_id,
                        "frame": {"id": 2, "name": "MISSION"},
                        "params": [photo_spacing, 0, 1, 0, lat_param, lon_param, alt_param],
                        "type": "SimpleItem"
                    })
                do_jump_id += 1
            elif wp_type == 'exit':
                # STOP continuous triggering
                lat_param, lon_param, alt_param = last_coord if last_coord else (wp['lat'], wp['lon'], wp['alt'])
                if not review:
                    survey_items.append({
                        "autoContinue": True,
                        "command": 206,
                        "doJumpId": do_jump_id,
                        "frame": 2,
                        "params": [0, 0, 1, 0, lat_param, lon_param, alt_param],  # distance=0 = stop (strings in QGC format!)
                        "type": "SimpleItem"
                    })
                else:
                    survey_items.append({
                        "autoContinue": True,
                        "command": {"id": 206, "name": "MAV_CMD_DO_SET_CAM_TRIGG_DIST"},
                        "doJumpId": do_jump_id,
                        "frame": {"id": 2, "name": "MISSION"},
                        "params": [0, 0, 1, 0, lat_param, lon_param, alt_param],  # Stop trigger uses string format
                        "type": "SimpleItem"
                    })
                do_jump_id += 1
        
        return survey_items

