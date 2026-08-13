import json
from stream_monitors.services.stream_monitor_services import StreamMonitorService
from stream_monitors.services.capture_service import CaptureService
from devices.schemas.schemas_djantic_out import DeviceOutSchema
from delivery.schemas.schemas_djantic_out import SelectDroneRowOutSchema
from orders.services.order_service import OrderService
from orders.models import OrderItem
from delivery.repository.confirmation_repository import ConfirmationRepository
from delivery.models import DeliveryOperation, DeliveryOperationItem
from delivery.models import DeliveryOperationApproval, DeliveryOperationApprovalChecklist 
from checklist_setting.models import ChecklistSetting, ChecklistSettingCategory
from collections import defaultdict
from delivery.schemas.schemas_djantic_in import AssignPackagesToDroneSchema, CancelAwaitingOrderInSchema
from devices.services.cargo_service import CargoCompartmentsService
from delivery.repository.processing_repository import ProcessingRepository
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet, Count, F, Value, CharField, Subquery, OuterRef, Q
from django.db.models.expressions import RawSQL
from django.contrib.contenttypes.models import ContentType
from django.db.models.functions import Concat, Coalesce
from django.contrib.postgres.aggregates import StringAgg
from delivery.utils.queryset_to_json import queryset_to_json
from delivery.services.opensearch_data import OpenSearchDataService
from typing import Dict, List, Any, Optional, Tuple
import datetime, time
from core.common.search.dynamic_search import apply_dynamic_filters
from common.utils import get_gcs_api_headers
import requests
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from django.utils import timezone
from django.db import connection
import logging
from devices.models import Device, DeviceStatus, Measurement, PropulsionSystem, DimensionsAndWeight, DeviceType
import math
from devices.utils import convert_unit
logger = logging.getLogger(__name__)
from terminals.models import Routes, Terminal, RouteTerminal
from delivery.schemas.schemas_djantic_in import AssignPackagesToDronesInSchema
from delivery.schemas.schemas_djantic_in import (
    CancelFlightInSchema,
    ChangeDroneInSchema,
    ApproveFlightInSchema,
    UploadMissionToGcsInSchema,
    StartMissionToGcsInSchema
)
from delivery.models import DeliveryStatus
from orders.models import Order, OrderAssignment
from devices.utils import convert_unit
from flight_log.services.flight_log_service import FlightLogService
from delivery.models import TerminalSequence
from common.constant import MESSAGE_ENUM
from core.common.constant import Language

opensearch_service = OpenSearchDataService()
INDEX_OPENSEARCH_NAME = os.environ.get('OPENSEARCH_INDEX', 'drone_logs_stg')

def get_drone_api_url():
    """Get the appropriate drone API URL for the current environment"""
    # First try the environment variable
    if 'FLIGHTBRID_URL' in os.environ:
        return os.environ['FLIGHTBRID_URL']
    
    return 'http://localhost:5000'

# Use the smart URL detection
DRONE_API_URL = get_drone_api_url()

class ProcessingService:
    
    @staticmethod
    def cancel_awaiting_order(data: CancelAwaitingOrderInSchema):
        return ProcessingRepository.cancel_awaiting_order(data)
    
    @staticmethod
    def get_list_of_routes(operation: DeliveryOperation) -> QuerySet:
        return ProcessingRepository.get_list_of_routes(operation)
    
    @staticmethod
    def get_list_of_drones() -> QuerySet:
        return ProcessingRepository.get_list_of_drones()
    
    @staticmethod
    def get_items_by_processing(operation_id: int) -> list:
        return ProcessingRepository.get_items_by_processing(operation_id)
    
    @staticmethod
    def get_operation_select_route_processing() -> list:
        operations = ProcessingRepository.get_operation_select_route_processing()
        if operations.exists():
            return queryset_to_json(operations)
        return []
    
    @staticmethod
    def get_operation_select_drone_processing() -> list:
        operations = ProcessingRepository.get_operation_select_drone_processing()
        if operations.exists():
            return queryset_to_json(operations)
        return []
    
    @staticmethod
    def get_operation_in_transit_processing() -> list:
        operations = ProcessingRepository.get_operation_in_transit_processing()
        if operations.exists():
            return queryset_to_json(operations)
        return []
    
    @staticmethod
    def get_data_tab_select_route_processing() -> list:
        operations = ProcessingRepository.get_operation_select_route_processing()
        # routes = ProcessingRepository.get_list_of_routes()
        return operations
    
    @staticmethod
    def get_data_tab_select_drone_processing() -> list:
        operations = ProcessingRepository.get_operation_select_drone_processing()
        drones = ProcessingRepository.get_list_of_drones()
        return operations, drones
    
    @staticmethod
    def get_data_tab_select_drone_processing_with_suitable_drones() -> list:
        """
        Get operations in select drone processing phase with suitable drones for each operation
        """
        return ProcessingRepository.get_operation_select_drone_processing_with_suitable_drones()
    
    @staticmethod
    def get_data_tab_in_transit_processing() -> list:
        operations = ProcessingRepository.get_operation_in_transit_processing()
        
        # Process streaming data for each operation
        processed_operations = []
        for operation in operations:
            # Convert drone IDs to StreamMonitor codes and then to stream URLs
            stream_urls = []
            webrtc_urls = []
            stream_paths = []
            if hasattr(operation, 'streamming_data') and operation.streamming_data:
                from stream_monitors.models import StreamMonitor
                
                # Get drone IDs from the annotation
                drone_ids = operation.streamming_data or []
                print("drone_ids: ", drone_ids)
                # Get StreamMonitor codes for these drones
                if drone_ids:
                    stream_monitors = StreamMonitor._base_manager.filter(
                        drone_id__in=drone_ids,
                        is_active=True
                    ).values_list('name', 'code')
                    # Convert codes to stream URLs
                    for name, code in stream_monitors:
                        if name:  # Skip None values
                            try:
                                stream_url = f"{settings.STREAM_URL}/hls/stream/{code}/index.m3u8"
                                webrtc_url = f"{settings.RTSP_PATH}/{code}"
                                stream_path = f"stream/{code}"
                                if stream_url:
                                    stream_urls.append(stream_url)
                                if webrtc_url:
                                    webrtc_urls.append(webrtc_url)
                                if stream_path:
                                    stream_paths.append(stream_path)
                            except Exception as e:
                                # Log the error but continue processing other streams
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"Failed to get stream for code {code}: {str(e)}")
                                continue
            print("stream_urls: ", stream_urls)
            # Replace the drone IDs with actual stream URLs
            operation.streamming_data = stream_urls
            operation.webrtc_data = webrtc_urls
            operation.stream_path = stream_paths
            processed_operations.append(operation)
            operation.is_use_webrtc = settings.IS_USE_WEBRTC
        
        return processed_operations
    
    @staticmethod
    def get_data_tab_in_transit_processing_with_delivery_device() -> QuerySet:
        """
        Get operations in transit processing with delivery device information as QuerySet
        """
        return ProcessingRepository.get_operation_in_transit_processing_with_delivery_device()
    
    @staticmethod
    def get_data_tab_in_transit_processing_with_delivery_items() -> list:
        """
        Get operations in transit processing with their delivery items and associated drones
        """
        return ProcessingRepository.get_operation_in_transit_processing_with_delivery_items()
        
    @staticmethod
    def update_route_to_operation(operation_id: int, 
                                  route_id: int) -> None:
        ProcessingRepository.update_route_to_operation(operation_id, 
                                                       route_id)
        
    @staticmethod
    def update_drone_to_operation_item(operation_item_id: int, 
                                       drone_id: int) -> None:
        ProcessingRepository.update_drone_to_operation_item(operation_item_id, 
                                                            drone_id)
        
    @staticmethod
    def update_drone_to_operation_items(operation_item_ids: list, 
                                        drone_id: int) -> None:
        ProcessingRepository.update_drone_to_operation_items(operation_item_ids, 
                                                            drone_id)
        ProcessingRepository.update_drone_status(drone_id, 'on_mission')
        
    @staticmethod
    def update_status_to_operation(operation_id: int, 
                                   status_code: str) -> None:
        ProcessingRepository.update_status_to_operation(operation_id, 
                                                        status_code)
        
    @staticmethod
    def update_is_arrived_to_operation_item(operation_item_id: int, 
                                            is_arrived: bool) -> None:
        ProcessingRepository.update_is_arrived_to_operation_item(operation_item_id, 
                                                                 is_arrived)
    
    @staticmethod
    def update_is_delivered_by_drone_to_operation_item(operation_item_id: int, 
                                                       is_delivered_by_drone: bool) -> None:
        ProcessingRepository.update_is_delivered_by_drone_to_operation_item(operation_item_id, 
                                                                           is_delivered_by_drone)
    
    @staticmethod
    def get_opensearch_data_service(unique_id: str, 
                                    msg_type: str=None, 
                                    time_from: str=None, 
                                    time_to: str=None, 
                                    size: int = 100, 
                                    sort_order: str = "desc"):
        
        search_results = opensearch_service.search_drone_logs_by_unique_id(unique_id=unique_id,
                                                                           msg_type=msg_type,
                                                                           time_from=time_from,
                                                                           time_to=time_to,
                                                                           size=size,
                                                                           sort_order=sort_order)
        return search_results
    
    @staticmethod
    def _get_all_telemetry_data_optimized(unique_id: str, time_from: str) -> Dict[str, Any]:
        """
        Optimized method to get all telemetry data in a single query.
        
        Args:
            unique_id: Unique ID of the drone
            time_from: Time from which to get historical data
            
        Returns:
            Dictionary containing all telemetry data organized by message type
        """
        # Build a single query to get all message types at once
        # Use the same structure as the working individual queries
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"uniqueId": unique_id}}
                    ],
                    "should": [
                        {"term": {"msgType": "RAW_IMU"}},
                        {"term": {"msgType": "VIBRATION"}},
                        {"term": {"msgType": "SYS_STATUS"}},
                        {"term": {"msgType": "WIND"}},
                        {"term": {"msgType": "DISTANCE_TRAVELED"}},
                        {"term": {"msgType": "HIGHRES_IMU"}},
                        {"term": {"msgType": "SCALED_PRESSURE"}},
                        {"term": {"msgType": "SCALED_PRESSURE2"}},
                        {"term": {"msgType": "TEMPERATURE"}},
                        {"term": {"msgType": "GLOBAL_POSITION_INT"}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 100,  # Get more data to cover all message types
            "sort": [
                {"timestamp": {"order": "desc"}}
            ]
        }
        
        # Execute the single query using the working method
        # Try to get all data by querying without msg_type filter
        response = opensearch_service.search_drone_logs_by_unique_id(
            unique_id=unique_id,
            size=200,
            sort_order="desc"
        )
        
        # Try with default index first
        position_data = opensearch_service.search_drone_logs_by_unique_id(
            unique_id=unique_id,
            msg_type="GLOBAL_POSITION_INT",
            size=1,
            sort_order="desc"
        )
        
        global_position_int_data ={
            'latitude': 0,
            'longitude': 0,
            'altitude': 0,
            'relativeAltitude': 0,
            'heading': 0,
            'groundSpeed': 0,
            'airSpeed': 0,
            'climbRate': 0,
            'gpsCount': 0,
            'gpsAccuracy': 0,
            'gpsStatus': 0,
            'gpsType': 0,
            'gpsTime': 0,
            'gpsTimeUsec': 0,
            'gpsTimeUnix': 0,
            'gpsTimeUnixNsec': 0,
        }
        global_position_int= position_data.get('hits', {}).get('hits', [])
        if global_position_int:
             global_position_int_data = global_position_int[0]['_source']
        
        
        # Debug logging removed for production
        
        if not response or not response.get('hits', {}).get('hits', []):
            return {
                'RAW_IMU': {},
                'VIBRATION': {},
                'RAW_IMU_HISTORY': {},
                'VIBRATION_HISTORY': {},
                'POSITION': {},
                'RC_CHANNELS': {},
                'SERVO_OUTPUT_RAW': {},
                'temperature': 0,
                'battery_percent': 0,
                'wind_speed': 0,
                'distance_traveled': 0.0
            }
        
        # Organize data by message type
        organized_data = {
            'RAW_IMU': {},
            'VIBRATION': {},
            'RAW_IMU_HISTORY': {'hits': {'hits': []}},
            'VIBRATION_HISTORY': {'hits': {'hits': []}},
            'POSITION': {},
            'RC_CHANNELS': {},
            'SERVO_OUTPUT_RAW': {},
            'temperature': 0,
            'battery_percent': 0,
            'wind_speed': 0,
            'distance_traveled': 0.0,
            'gps_satellites': 0
        }
        
        # Process all hits and organize by message type
        latest_by_type = {}
        historical_data = {'RAW_IMU': [], 'VIBRATION': [], 'GLOBAL_POSITION_INT': []}
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            msg_type = source.get('msgType')
            timestamp = source.get('timestamp')
            
            # Store latest data for each message type
            if msg_type not in latest_by_type:
                latest_by_type[msg_type] = source
            else:
                if timestamp > latest_by_type[msg_type].get('timestamp', ''):
                    latest_by_type[msg_type] = source
            
            # Store historical data for charts
            if msg_type in ['RAW_IMU', 'VIBRATION', 'GLOBAL_POSITION_INT']:
                historical_data[msg_type].append(hit)
        
        # Set latest data in the expected format
        if 'RAW_IMU' in latest_by_type:
            organized_data['RAW_IMU'] = {'hits': {'hits': [{'_source': latest_by_type['RAW_IMU']}]}}
        else:
            organized_data['RAW_IMU'] = {}
            
        if 'VIBRATION' in latest_by_type:
            organized_data['VIBRATION'] = {'hits': {'hits': [{'_source': latest_by_type['VIBRATION']}]}}
        else:
            organized_data['VIBRATION'] = {}
            
            
        organized_data['POSITION'] = global_position_int_data
        organized_data['gps_satellites'] = global_position_int_data.get('gpsCount', 0)

        
        # Set RC_CHANNELS data
        if 'RC_CHANNELS' in latest_by_type:
            organized_data['RC_CHANNELS'] = {'hits': {'hits': [{'_source': latest_by_type['RC_CHANNELS']}]}}
        else:
            organized_data['RC_CHANNELS'] = {}
        
        # Set SERVO_OUTPUT_RAW data
        if 'SERVO_OUTPUT_RAW' in latest_by_type:
            organized_data['SERVO_OUTPUT_RAW'] = {'hits': {'hits': [{'_source': latest_by_type['SERVO_OUTPUT_RAW']}]}}
        else:
            organized_data['SERVO_OUTPUT_RAW'] = {}
        
        # Set historical data
        organized_data['RAW_IMU_HISTORY'] = {'hits': {'hits': historical_data['RAW_IMU']}}
        organized_data['VIBRATION_HISTORY'] = {'hits': {'hits': historical_data['VIBRATION']}}
        
        # Extract telemetry values
        # Temperature from multiple sources
        temperature_sources = ["HIGHRES_IMU", "SCALED_PRESSURE", "SCALED_PRESSURE2", "TEMPERATURE"]
        for msg_type in temperature_sources:
            if msg_type in latest_by_type:
                temp_value = latest_by_type[msg_type].get('temperature', 0)
                if temp_value is not None and temp_value != 0:
                    organized_data['temperature'] = round(temp_value, 1)
                    break
        
        # Battery from SYS_STATUS
        if 'SYS_STATUS' in latest_by_type:
            organized_data['battery_percent'] = latest_by_type['SYS_STATUS'].get('batteryLevel', 0)
        
        # Wind speed from WIND
        if 'WIND' in latest_by_type:
            wind_speed_ms = latest_by_type['WIND'].get('windSpeed', 0)
            organized_data['wind_speed'] = round(wind_speed_ms * 3.6, 1)  # Convert m/s to km/h
        
        # Distance from DISTANCE_TRAVELED
        if 'DISTANCE_TRAVELED' in latest_by_type:
            distance_meters = latest_by_type['DISTANCE_TRAVELED'].get('distanceTraveled', 0.0)
            organized_data['distance_traveled'] = round(distance_meters / 1000, 1)  # Convert m to km
        
        return organized_data

    @staticmethod
    def get_drone_telemetry_by_unique_id(unique_id: str, time_window_minutes: int = 15) -> Dict[str, Any]:
        """
        Get aggregated telemetry data for a drone by its unique ID.
        
        Args:
            unique_id: Unique ID of the drone
            time_window_minutes: Time window (in minutes) for retrieving historical data for charts

        Returns:
            Dictionary containing organized telemetry data of the drone
        """
        # Calculate the time range for historical data
        now = datetime.datetime.utcnow()
        time_from = (now - datetime.timedelta(minutes=time_window_minutes)).isoformat() + "Z"

        # Single optimized query to get all telemetry data at once
        all_telemetry_data = ProcessingService._get_all_telemetry_data_optimized(unique_id, time_from)
        
        # Extract data from the single query result
        raw_imu_data = all_telemetry_data.get('RAW_IMU', {})
        vibration_data = all_telemetry_data.get('VIBRATION', {})
        rc_channels_data = all_telemetry_data.get('RC_CHANNELS', {})
        servo_output_data = all_telemetry_data.get('SERVO_OUTPUT_RAW', {})
        historical_imu = all_telemetry_data.get('RAW_IMU_HISTORY', {})
        historical_vibration = all_telemetry_data.get('VIBRATION_HISTORY', {})
        historical_position = all_telemetry_data.get('POSITION', {})
        
        # Extract telemetry values
        temperature = all_telemetry_data.get('temperature', 0)
        battery_percent = all_telemetry_data.get('battery_percent', 0)
        wind_speed = all_telemetry_data.get('wind_speed', 0)
        distance_traveled = all_telemetry_data.get('distance_traveled', 0.0)
        gps_satellites = all_telemetry_data.get('gps_satellites', 0)
        x_axis = 0
        y_axis = 0
        z_axis = 0
        vib_x = 0
        vib_y = 0
        vib_z = 0
        sys_id = 0
        
        # Initialize RC channels and servo output data
        rc_channels = {}
        servo_output = {}

        # Conversion functions
        def normalize_acceleration(value, min_range=-2000, max_range=2000):
            """
            Convert raw acceleration to 0-100 scale for display.
            Maps acceleration values from [min_range, max_range] to [0, 100].
            Typical MAVLink RAW_IMU acceleration values range from -2000 to 2000.
            """
            if value is None:
                return 0
            # Clamp value to range
            clamped_value = max(min_range, min(max_range, value))
            # Normalize to 0-100: map [min_range, max_range] to [0, 100]
            # Formula: ((value - min_range) / (max_range - min_range)) * 100
            normalized = ((clamped_value - min_range) / (max_range - min_range)) * 100
            # Round and ensure it's between 0 and 100
            return max(0, min(100, round(normalized)))
        
        def normalize_vibration(value, scale_factor=10000):
            """Convert raw vibration to 0-100 scale for display"""
            if value is None:
                return 0
            # Vibration values are typically very small (0.001-0.01)
            # Multiply by scale_factor to get to 0-100 range
            return min(round(value * scale_factor), 100)

        # Extract latest temperature and acceleration values
        if raw_imu_data.get('hits', {}).get('hits', []):
            source = raw_imu_data['hits']['hits'][0]['_source']
            timestamp = source.get('timestamp')
            
            # Store raw values for reference
            raw_xacc = source.get('xacc', 0)
            raw_yacc = source.get('yacc', 0)
            raw_zacc = source.get('zacc', 0)
            
            # Normalize for display
            x_axis = normalize_acceleration(raw_xacc)
            y_axis = normalize_acceleration(raw_yacc)
            z_axis = normalize_acceleration(raw_zacc)
            sys_id = source.get('sysId', 0)
        
        # Extract latest vibration values
        if vibration_data.get('hits', {}).get('hits', []):
            source = vibration_data['hits']['hits'][0]['_source']
            
            # Store raw values
            raw_vibx = source.get('vibrationX', 0)
            raw_viby = source.get('vibrationY', 0)
            raw_vibz = source.get('vibrationZ', 0)
            
            # Normalize for display
            vib_x = normalize_vibration(raw_vibx)
            vib_y = normalize_vibration(raw_viby)
            vib_z = normalize_vibration(raw_vibz)
        
        # Extract RC channels data
        if rc_channels_data.get('hits', {}).get('hits', []):
            source = rc_channels_data['hits']['hits'][0]['_source']
            rc_channels = {
                'chancount': source.get('chancount', 0),
                'rssi': source.get('rssi', 0),
                'channels': {}
            }
            # Extract all channel values (chan1 through chan18)
            for i in range(1, 19):
                channel_key = f'chan{i}'
                rc_channels['channels'][channel_key] = source.get(channel_key, 0)
        
        # Extract servo output data
        if servo_output_data.get('hits', {}).get('hits', []):
            source = servo_output_data['hits']['hits'][0]['_source']
            servo_output = {
                'port': source.get('port', 0),
                'time_usec': source.get('time_usec', 0),
                'servos': {}
            }
            # Extract all servo values (servo1 through servo16)
            for i in range(1, 17):
                servo_key = f'servo{i}'
                servo_output['servos'][servo_key] = source.get(servo_key, 0)

        # Process historical data for charts
        timestamps = []
        timestamps_vibration = []
        temp_history = []
        x_acc_history = []
        y_acc_history = []
        z_acc_history = []
        vib_x_history = []
        vib_y_history = []
        vib_z_history = []
        
        # Raw data for reference (if needed)
        raw_x_acc_history = []
        raw_y_acc_history = []
        raw_z_acc_history = []
        raw_vib_x_history = []
        raw_vib_y_history = []
        raw_vib_z_history = []

        # Process IMU historical data
        if historical_imu.get('hits', {}).get('hits', []):
            for hit in historical_imu['hits']['hits']:
                source = hit.get('_source', {})
                temp = source.get('temperature')
                timestamp = source.get('timestamp')
                xacc = source.get('xacc', 0)
                yacc = source.get('yacc', 0)
                zacc = source.get('zacc', 0)

                if timestamp:
                    try:
                        # Fix the timestamp format before parsing
                        simplified_timestamp = timestamp
                        if '.' in timestamp:
                            # Handle microseconds by removing them completely
                            parts = timestamp.split('.')
                            # Keep only the part before the decimal point
                            if '+' in parts[1]:
                                # Handle format like: 2025-05-28T06:46:26.0058499+00:00
                                timezone_parts = parts[1].split('+')
                                simplified_timestamp = f"{parts[0]}+{timezone_parts[1]}"
                            elif 'Z' in parts[1]:
                                # Handle format with Z timezone
                                simplified_timestamp = f"{parts[0]}Z"
                            else:
                                simplified_timestamp = parts[0]
                        
                        # Replace Z with +00:00 if present
                        if 'Z' in simplified_timestamp:
                            simplified_timestamp = simplified_timestamp.replace('Z', '+00:00')
                            
                        dt = datetime.datetime.fromisoformat(simplified_timestamp)
                        # Use timestamps in seconds since epoch for better time series display
                        timestamp_seconds = dt.timestamp()
                        timestamps.append(timestamp_seconds)
                        
                        if temp is not None:
                            temp_history.append(temp)
                        
                        # Store raw values
                        raw_x_acc_history.append(xacc)
                        raw_y_acc_history.append(yacc)
                        raw_z_acc_history.append(zacc)
                        
                        # Normalize for display (using the same normalize function)
                        x_acc_history.append(normalize_acceleration(xacc))
                        y_acc_history.append(normalize_acceleration(yacc))
                        z_acc_history.append(normalize_acceleration(zacc))
                    except ValueError as e:
                        # Log the error but continue processing
                        print(f"Error parsing timestamp '{timestamp}': {str(e)}")
                        continue
        
        # Process vibration historical data
        if historical_vibration.get('hits', {}).get('hits', []):
            for hit in historical_vibration['hits']['hits']:
                source = hit.get('_source', {})
                timestamp = source.get('timestamp')
                vibx = source.get('vibrationX', 0)
                viby = source.get('vibrationY', 0)
                vibz = source.get('vibrationZ', 0)

                if timestamp:
                    try:
                        # Fix the timestamp format before parsing
                        simplified_timestamp = timestamp
                        if '.' in timestamp:
                            # Handle microseconds by removing them completely
                            parts = timestamp.split('.')
                            # Keep only the part before the decimal point
                            if '+' in parts[1]:
                                timezone_parts = parts[1].split('+')
                                simplified_timestamp = f"{parts[0]}+{timezone_parts[1]}"
                            elif 'Z' in parts[1]:
                                simplified_timestamp = f"{parts[0]}Z"
                            else:
                                simplified_timestamp = parts[0]
                        
                        # Replace Z with +00:00 if present
                        if 'Z' in simplified_timestamp:
                            simplified_timestamp = simplified_timestamp.replace('Z', '+00:00')
                            
                        dt = datetime.datetime.fromisoformat(simplified_timestamp)
                        # Use timestamps in seconds since epoch for better time series display
                        timestamp_seconds = dt.timestamp()
                        timestamps_vibration.append(timestamp_seconds)
                        
                        # Store raw values
                        raw_vib_x_history.append(vibx)
                        raw_vib_y_history.append(viby)
                        raw_vib_z_history.append(vibz)
                        
                        # Normalize for display
                        vib_x_history.append(normalize_vibration(vibx))
                        vib_y_history.append(normalize_vibration(viby))
                        vib_z_history.append(normalize_vibration(vibz))
                    except ValueError as e:
                        # Log the error but continue processing
                        print(f"Error parsing timestamp '{timestamp}': {str(e)}")
                        continue

        # Limit history to last points for better visualization
        max_points = 48  # More points for better visualization (will show full chart)
        timestamps = timestamps[-max_points:] if len(timestamps) > max_points else timestamps
        temp_history = temp_history[-max_points:] if len(temp_history) > max_points else temp_history
        
        # Truncate normalized histories
        x_acc_history = x_acc_history[-max_points:] if len(x_acc_history) > max_points else x_acc_history
        y_acc_history = y_acc_history[-max_points:] if len(y_acc_history) > max_points else y_acc_history
        z_acc_history = z_acc_history[-max_points:] if len(z_acc_history) > max_points else z_acc_history
        
        timestamps_vibration = timestamps_vibration[-max_points:] if len(timestamps_vibration) > max_points else timestamps_vibration
        vib_x_history = vib_x_history[-max_points:] if len(vib_x_history) > max_points else vib_x_history
        vib_y_history = vib_y_history[-max_points:] if len(vib_y_history) > max_points else vib_y_history
        vib_z_history = vib_z_history[-max_points:] if len(vib_z_history) > max_points else vib_z_history
        
        # Truncate raw histories
        raw_x_acc_history = raw_x_acc_history[-max_points:] if len(raw_x_acc_history) > max_points else raw_x_acc_history
        raw_y_acc_history = raw_y_acc_history[-max_points:] if len(raw_y_acc_history) > max_points else raw_y_acc_history
        raw_z_acc_history = raw_z_acc_history[-max_points:] if len(raw_z_acc_history) > max_points else raw_z_acc_history
        raw_vib_x_history = raw_vib_x_history[-max_points:] if len(raw_vib_x_history) > max_points else raw_vib_x_history
        raw_vib_y_history = raw_vib_y_history[-max_points:] if len(raw_vib_y_history) > max_points else raw_vib_y_history
        raw_vib_z_history = raw_vib_z_history[-max_points:] if len(raw_vib_z_history) > max_points else raw_vib_z_history

        # Extract position data from historical_position (GLOBAL_POSITION_INT)
        position_data = {
            "latitude": 0,
            "longitude": 0,
            "alt": 0
        }
        if historical_position and isinstance(historical_position, dict):
            position_data["latitude"] = historical_position.get('latitude', 0)
            position_data["longitude"] = historical_position.get('longitude', 0)
            position_data["alt"] = historical_position.get('altitude', 0) or historical_position.get('relativeAltitude', 0)
        
        # Extract GPS count from GLOBAL_POSITION_INT (use latest position data)
        if historical_position and isinstance(historical_position, dict):
            gps_satellites = historical_position.get('gpsCount', 0)
        else:
            gps_satellites = all_telemetry_data.get('gps_satellites', 0)
        
        # Build the response
        response = {
            "drone_id": sys_id,
            "unique_id": unique_id,
            "position": historical_position,
            "telemetry": {
                "temperature": temperature,
                "battery_percent": battery_percent,
                "distance_traveled": distance_traveled,
                "wind_speed": wind_speed,
                "axes": {
                    "x": x_axis,
                    "y": y_axis,
                    "z": z_axis
                },
                "axes_raw": {
                    "x": raw_xacc if 'raw_xacc' in locals() else 0,
                    "y": raw_yacc if 'raw_yacc' in locals() else 0,
                    "z": raw_zacc if 'raw_zacc' in locals() else 0
                },
                "vibration": {
                    "x": vib_x,
                    "y": vib_y,
                    "z": vib_z
                },
                "vibration_raw": {
                    "x": raw_vibx if 'raw_vibx' in locals() else 0,
                    "y": raw_viby if 'raw_viby' in locals() else 0,
                    "z": raw_vibz if 'raw_vibz' in locals() else 0
                },
                "position": position_data,
                "gps_satellites": gps_satellites if 'gps_satellites' in locals() else 0,
                "rc_channels": rc_channels if rc_channels else {},
                "servo_output": servo_output if servo_output else {}
            },
            "history": {
                "timestamps": timestamps,
                "temperature": temp_history,
                "acceleration": {
                    "x": x_acc_history,
                    "y": y_acc_history,
                    "z": z_acc_history
                },
                "acceleration_raw": {
                    "x": raw_x_acc_history,
                    "y": raw_y_acc_history,
                    "z": raw_z_acc_history
                },
                "timestamps_vibration": timestamps_vibration,
                "vibration": {
                    "x": vib_x_history,
                    "y": vib_y_history,
                    "z": vib_z_history
                },
                "vibration_raw": {
                    "x": raw_vib_x_history,
                    "y": raw_vib_y_history,
                    "z": raw_vib_z_history
                }
            },
            "status": {
                "is_moving": True,
                "arrived_at_base": False,
                "system_status": "normal"
            }
        }

        return response

    @staticmethod
    def get_drone_telemetry_by_unique_id_filtered(unique_id: str, monitoring_items: Optional[List[str]] = None, time_window_minutes: int = 15) -> Dict[str, Any]:
        """
        Get filtered telemetry data for a drone based on selected monitoring items.
        
        Args:
            unique_id: Unique ID of the drone
            monitoring_items: List of items to include (e.g., ['x-axis', 'y-axis', 'ch1in', 'ch2out'])
            time_window_minutes: Time window for historical data
            
        Returns:
            Dictionary containing filtered telemetry data
        """
        # Get full telemetry data
        full_data = ProcessingService.get_drone_telemetry_by_unique_id(unique_id, time_window_minutes)
        
        # If no items specified, return all data (default behavior)
        if not monitoring_items or len(monitoring_items) == 0:
            return {
                "active_drone": full_data,
                "all_drones": ProcessingService.get_all_drones_in_db()
            }
        
        # Filter data based on selected items
        filtered_telemetry = {}
        filtered_history = {}
        
        # Always include basic info
        filtered_telemetry['temperature'] = full_data.get('telemetry', {}).get('temperature', 0)
        filtered_telemetry['battery_percent'] = full_data.get('telemetry', {}).get('battery_percent', 0)
        filtered_telemetry['distance_traveled'] = full_data.get('telemetry', {}).get('distance_traveled', 0.0)
        filtered_telemetry['wind_speed'] = full_data.get('telemetry', {}).get('wind_speed', 0)
        filtered_telemetry['position'] = full_data.get('telemetry', {}).get('position', {})
        
        # Filter axes data
        if any(item in monitoring_items for item in ['x-axis', 'y-axis', 'z-axis']):
            axes = {}
            axes_raw = {}
            axes_history = {}
            axes_history_raw = {}
            
            if 'x-axis' in monitoring_items:
                axes['x'] = full_data.get('telemetry', {}).get('axes', {}).get('x', 0)
                axes_raw['x'] = full_data.get('telemetry', {}).get('axes_raw', {}).get('x', 0)
                axes_history['x'] = full_data.get('history', {}).get('acceleration', {}).get('x', [])
                axes_history_raw['x'] = full_data.get('history', {}).get('acceleration_raw', {}).get('x', [])
            
            if 'y-axis' in monitoring_items:
                axes['y'] = full_data.get('telemetry', {}).get('axes', {}).get('y', 0)
                axes_raw['y'] = full_data.get('telemetry', {}).get('axes_raw', {}).get('y', 0)
                axes_history['y'] = full_data.get('history', {}).get('acceleration', {}).get('y', [])
                axes_history_raw['y'] = full_data.get('history', {}).get('acceleration_raw', {}).get('y', [])
            
            if 'z-axis' in monitoring_items:
                axes['z'] = full_data.get('telemetry', {}).get('axes', {}).get('z', 0)
                axes_raw['z'] = full_data.get('telemetry', {}).get('axes_raw', {}).get('z', 0)
                axes_history['z'] = full_data.get('history', {}).get('acceleration', {}).get('z', [])
                axes_history_raw['z'] = full_data.get('history', {}).get('acceleration_raw', {}).get('z', [])
            
            filtered_telemetry['axes'] = axes
            filtered_telemetry['axes_raw'] = axes_raw
            filtered_history['acceleration'] = axes_history
            filtered_history['acceleration_raw'] = axes_history_raw
        
        # Filter vibration data (support vibe-x, vibe-y, vibe-z)
        vibe_items = [item for item in monitoring_items if item.startswith('vibe-')]
        if vibe_items:
            vibration = {}
            vibration_raw = {}
            vibration_history = {}
            vibration_history_raw = {}
            
            full_vibration = full_data.get('telemetry', {}).get('vibration', {})
            full_vibration_raw = full_data.get('telemetry', {}).get('vibration_raw', {})
            full_vibration_history = full_data.get('history', {}).get('vibration', {})
            full_vibration_history_raw = full_data.get('history', {}).get('vibration_raw', {})
            
            for item in vibe_items:
                axis = item.replace('vibe-', '')  # 'x', 'y', or 'z'
                if axis in ['x', 'y', 'z']:
                    if axis in full_vibration:
                        vibration[axis] = full_vibration[axis]
                    if axis in full_vibration_raw:
                        vibration_raw[axis] = full_vibration_raw[axis]
                    if axis in full_vibration_history:
                        vibration_history[axis] = full_vibration_history[axis]
                    if axis in full_vibration_history_raw:
                        vibration_history_raw[axis] = full_vibration_history_raw[axis]
            
            if vibration:
                filtered_telemetry['vibration'] = vibration
                filtered_telemetry['vibration_raw'] = vibration_raw
                filtered_history['vibration'] = vibration_history
                filtered_history['vibration_raw'] = vibration_history_raw
                filtered_history['timestamps_vibration'] = full_data.get('history', {}).get('timestamps_vibration', [])
        
        # Filter RC channels
        rc_channels_needed = [item for item in monitoring_items if item.startswith('ch') and item.endswith('in')]
        if rc_channels_needed:
            rc_channels_data = full_data.get('telemetry', {}).get('rc_channels', {})
            if rc_channels_data:
                filtered_channels = {}
                for item in rc_channels_needed:
                    # Extract channel number from 'ch1in' -> 1
                    channel_num = int(item.replace('ch', '').replace('in', ''))
                    channel_key = f'chan{channel_num}'
                    if rc_channels_data.get('channels', {}).get(channel_key) is not None:
                        filtered_channels[channel_key] = rc_channels_data['channels'][channel_key]
                
                if filtered_channels:
                    filtered_telemetry['rc_channels'] = {
                        'chancount': rc_channels_data.get('chancount', 0),
                        'rssi': rc_channels_data.get('rssi', 0),
                        'channels': filtered_channels
                    }
        
        # Filter servo outputs
        servo_outputs_needed = [item for item in monitoring_items if item.startswith('ch') and item.endswith('out')]
        if servo_outputs_needed:
            servo_output_data = full_data.get('telemetry', {}).get('servo_output', {})
            if servo_output_data:
                filtered_servos = {}
                for item in servo_outputs_needed:
                    # Extract servo number from 'ch1out' -> 1
                    servo_num = int(item.replace('ch', '').replace('out', ''))
                    servo_key = f'servo{servo_num}'
                    if servo_output_data.get('servos', {}).get(servo_key) is not None:
                        filtered_servos[servo_key] = servo_output_data['servos'][servo_key]
                
                if filtered_servos:
                    filtered_telemetry['servo_output'] = {
                        'port': servo_output_data.get('port', 0),
                        'time_usec': servo_output_data.get('time_usec', 0),
                        'servos': filtered_servos
                    }
        
        # Filter GPS data (GPS satellites count)
        if 'gps' in monitoring_items:
            # Include GPS satellites count
            gps_satellites = full_data.get('telemetry', {}).get('gps_satellites', 0)
            filtered_telemetry['gps_satellites'] = gps_satellites
        
        # Build filtered response
        filtered_response = {
            "drone_id": full_data.get('drone_id', 0),
            "unique_id": unique_id,
            "position": full_data.get('position', {}),
            "telemetry": filtered_telemetry,
            "history": {
                **filtered_history,
                "timestamps": full_data.get('history', {}).get('timestamps', []),
                "temperature": full_data.get('history', {}).get('temperature', [])
            },
            "status": full_data.get('status', {})
        }
        
        return {
            "active_drone": filtered_response,
            "all_drones": ProcessingService.get_all_drones_in_db()
        }

    @staticmethod
    def get_drone_location_by_unique_id(unique_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve drone location by unique ID.

        Returns:
            Dictionary containing drone location
        """    
        return ProcessingService.get_lat_long_drone(unique_id)
    
    @staticmethod
    def get_all_active_drones_unique_ids() -> List[Dict[str, Any]]:
        """
        Retrieve status information for all active drones.

        Returns:
            List of dictionaries containing drone status
        """
        # Get recent unique IDs from drone logs
        now = datetime.datetime.utcnow()
        time_from = (now - datetime.timedelta(minutes=5)).isoformat() + "Z"

        # Use a simple query to extract uniqueId from recent logs
        query = {
            "size": 0,
            "query": {
                "range": {
                    "timestamp": {
                        "gte": time_from
                    }
                }
            },
            "aggs": {
                "unique_drones": {
                    "terms": {
                        "field": "uniqueId.keyword",
                        "size": 500
                    }
                }
            }
        }

        results = opensearch_service.search_dsl(INDEX_OPENSEARCH_NAME, query)

        # Extract uniqueId and collect telemetry
        active_drones = []
        if 'aggregations' in results and 'unique_drones' in results['aggregations']:
            buckets = results['aggregations']['unique_drones']['buckets']
            for bucket in buckets:
                unique_id = bucket['key']
                drone_data = ProcessingService.get_drone_telemetry_by_unique_id(unique_id)
                active_drones.append(drone_data)

        return active_drones
    
    @staticmethod
    def get_all_drone_active_unique_ids() -> List[Dict[str, Any]]:
        """
        Retrieve status information for all active drones.

        Returns:
            List of dictionaries containing drone status
        """
        # Get recent unique IDs from drone logs
        active_drones = []

        devices = Device._base_manager.filter(unit_id__isnull=False, active=True)
        for device in devices:
            unique_id = device.unit_id
            if unique_id:
                drone_data = ProcessingService.get_drone_telemetry_by_unique_id(unique_id)
                active_drones.append(drone_data)
        return active_drones


    @staticmethod
    def get_all_drones_in_db() -> List[Dict[str, Any]]:
        """
        Retrieve all drones from the database.

        Returns:
            List of dictionaries containing drone data
        """
        drones = ProcessingRepository.get_list_of_drones()
        if drones.exists():
            return queryset_to_json(drones)
        return []
    
    @staticmethod
    def get_drone_status_dashboard(unique_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve data for the drone status dashboard.
        If a unique_id is provided, returns detailed data for that specific drone.
        If not, returns summarized data for all active drones.

        Args:
            unique_id: Unique ID of a specific drone for detailed telemetry

        Returns:
            Dictionary containing dashboard telemetry data
        """
        if unique_id:
            return {
                "active_drone": ProcessingService.get_drone_telemetry_by_unique_id(unique_id),
                "all_drones": ProcessingService.get_all_drones_in_db()
            }
        else:
            return {
                "all_drones": ProcessingService.get_all_drone_active_unique_ids()
            }

    @staticmethod
    def calculate_distance_traveled(unique_id: str) -> float:
        """
        Calculate total distance traveled by drone from GPS history.
        
        Args:
            unique_id: Unique ID of the drone
            
        Returns:
            Total distance traveled in kilometers
        """
        try:
            # Get GPS position history for the last 24 hours
            now = datetime.datetime.utcnow()
            time_from = (now - datetime.timedelta(hours=24)).isoformat() + "Z"
            
            position_data = opensearch_service.search_drone_logs_by_unique_id(
                unique_id=unique_id,
                msg_type="GLOBAL_POSITION_INT",
                time_from=time_from,
                size=1000,
                sort_order="asc"
            )
            
            if not position_data.get('hits', {}).get('hits', []):
                return 0.0
            
            total_distance = 0.0
            previous_lat = None
            previous_lon = None
            
            for hit in position_data['hits']['hits']:
                source = hit.get('_source', {})
                lat = source.get('latitude', 0)
                lon = source.get('longitude', 0)
                
                # Skip invalid coordinates
                if lat == 0 and lon == 0:
                    continue
                
                if previous_lat is not None and previous_lon is not None:
                    # Calculate distance between two GPS points using Haversine formula
                    distance = ProcessingService.haversine_distance(
                        previous_lat, previous_lon, lat, lon
                    )
                    total_distance += distance
                
                previous_lat = lat
                previous_lon = lon
            
            return round(total_distance, 2)  # Return in kilometers
            
        except Exception as e:
            logger.error(f"Error calculating distance for drone {unique_id}: {str(e)}")
            return 0.0
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        
        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point
            
        Returns:
            Distance in kilometers
        """
        import math
        
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r

    @staticmethod
    def get_lat_long_drone(unique_id: str) -> Dict[str, Any]:
        """
        Retrieve latitude and longitude of a drone by its unique ID.

        Args:
            unique_id: Unique ID of the drone

        Returns:
            Dictionary containing latitude and longitude of the drone
        """
        # Get the latest drone log for the given unique_id
        position_data = opensearch_service.search_drone_logs_by_unique_id(
            unique_id=unique_id,
            msg_type="GLOBAL_POSITION_INT",
            size=1,
            sort_order="desc"
        )
        if position_data.get('hits', {}).get('hits', []):
            source = position_data['hits']['hits'][0]['_source']
            return {
                "latitude": source.get('latitude', 0),
                "longitude": source.get('longitude', 0)
            }
        return {
            "latitude": 0,
            "longitude": 0
        }


    @staticmethod
    def get_drone_payload(unique_id: str) -> float:
        """
        Get the payload of a drone based on its telemetry data.

        Args:
            unique_id: Unique ID of the drone

        Returns:
            Float containing the payload of the drone
        """
        drone_weight_capacity, drone_dimensions = ProcessingRepository.get_drone_payload(unique_id)
        return drone_weight_capacity, drone_dimensions
    
    @staticmethod
    def check_drone_can_delivery_packages(unique_id: str, package_ids: list) -> Dict[str, Any]:
        """
        Check if a drone can deliver packages based on its maximum payload and the weight of the packages.

        Args:
            unique_id: Unique ID of the drone
            packages: List of packages to be delivered

        Returns:
            Dictionary containing the result of the check
        """
        drone_weight_capacity, drone_dimensions = ProcessingService.get_drone_payload(unique_id)
        
        total_package_weight = 0
        for package_id in package_ids:
            weight_measurement, length_measurement, width_measurement, height_measurement = ProcessingRepository.get_package_weight_dimensions(package_id)
            total_package_weight += weight_measurement["value"]
        
        # Extract the actual weight capacity value
        drone_max_weight = drone_weight_capacity["value"] if isinstance(drone_weight_capacity, dict) else drone_weight_capacity
        
        return {
            "can_deliver": drone_max_weight >= total_package_weight,
            "drone_weight_capacity": drone_max_weight,
            "total_package_weight": total_package_weight
        }
    
    
    @staticmethod
    def _check_order_packages_completeness(package_ids: List[int]) -> Tuple[bool, List[int], List[int]]:
        """
        Check if all packages of each order are included in the provided package_ids.
        
        Args:
            package_ids: List of package IDs to check
            
        Returns:
            Tuple of (is_valid, valid_package_ids, removed_order_ids)
        """
        from delivery.models import DeliveryOperationItem
        from orders.models import Order
        
        # Group packages by order
        order_to_packages: Dict[int, List[int]] = defaultdict(list)
        package_to_order: Dict[int, int] = {}
        
        # Get order for each package
        for package_id in package_ids:
            try:
                delivery_item = DeliveryOperationItem.objects.get(id=package_id)
                order_id = delivery_item.order_item.order.id
                order_to_packages[order_id].append(package_id)
                package_to_order[package_id] = order_id
            except DeliveryOperationItem.DoesNotExist:
                continue
        
        valid_package_ids = []
        removed_order_ids = []
        
        # Check completeness for each order
        for order_id, assigned_packages in order_to_packages.items():
            try:
                order = Order.objects.get(id=order_id)
                # Get all packages for this order
                all_order_packages = list(order.items.values_list('id', flat=True))
                
                # Check if all packages of this order are included
                if set(assigned_packages) == set(all_order_packages) and len(all_order_packages) > 0:
                    # Order is complete, add all packages to valid list
                    valid_package_ids.extend(assigned_packages)
                else:
                    # Order is incomplete, remove it
                    removed_order_ids.append(order_id)
                    print(f"⚠️ [PACKAGE_VALIDATION] Order {order_id} incomplete: {len(assigned_packages)}/{len(all_order_packages)} packages assigned")
            except Order.DoesNotExist:
                # Order not found, remove packages
                removed_order_ids.append(order_id)
                print(f"❌ [PACKAGE_VALIDATION] Order {order_id} not found")
        
        is_valid = len(valid_package_ids) > 0
        
        if removed_order_ids:
            print(f"🗑️ [PACKAGE_VALIDATION] Removed {len(removed_order_ids)} incomplete orders: {removed_order_ids}")
            print(f"✅ [PACKAGE_VALIDATION] Valid packages: {len(valid_package_ids)}")
        
        return is_valid, valid_package_ids, removed_order_ids

    @staticmethod
    def assign_packages_to_drone(data: List[AssignPackagesToDroneSchema]) -> List[Dict[str, Any]]:
        """Group packages by drone_id and validate order completeness."""
        grouped: Dict[int, List[int]] = defaultdict(list)

        for item in data:
            grouped[item.drone_id].append(item.package_id)

        # Convert to list of dicts
        packages_drone = [
            {"drone_id": drone_id, "packages": packages}
            for drone_id, packages in grouped.items()
        ]
        
        # Flatten all package IDs for validation
        all_package_ids = [item.package_id for item in data]
        
        # Check order packages completeness
        is_valid, valid_package_ids, removed_order_ids = ProcessingService._check_order_packages_completeness(all_package_ids)
        
        if not is_valid:
            print(f"❌ [PACKAGE_VALIDATION] No valid orders found after completeness check")
            return False
        
        # Filter packages_drone to only include valid packages
        valid_packages_drone = []
        for item in packages_drone:
            valid_packages = [pid for pid in item["packages"] if pid in valid_package_ids]
            if valid_packages:
                valid_packages_drone.append({
                    "drone_id": item["drone_id"],
                    "packages": valid_packages
                })
        
        if not valid_packages_drone:
            print(f"❌ [PACKAGE_VALIDATION] No valid packages remaining after filtering")
            return False
        
        # Check if drone can deliver packages
        for item in valid_packages_drone:
            check_result = ProcessingService.check_drone_can_delivery_packages(item["drone_id"], item["packages"])
            if not check_result["can_deliver"]:
                print(f"❌ [DRONE_CAPACITY] Drone {item['drone_id']} cannot deliver packages: {check_result}")
                return False
        
        # Update drone assignments for valid packages
        for item in valid_packages_drone:
            ProcessingService.update_drone_to_operation_items(item["packages"], item["drone_id"])

        # Update status to operation (use first valid package)
        if valid_package_ids:
            operation_id = ProcessingRepository.get_operation_id_by_package_id(valid_package_ids[0])
            ProcessingRepository.update_status_to_operation(operation_id, "in_transit_processing")
            # Start drones mission
            ProcessingService.start_drone_delivery(operation_id)
        
        return True
 
         
    @staticmethod
    @transaction.atomic
    def assign_packages_to_drones(payload: AssignPackagesToDronesInSchema) -> Dict[str, Any]:
        """
        Assign packages to multiple drones with the rule:
        - For each order, ALL packages of that order must be assigned across drones.
        - If an order is only partially assigned, drop ALL its packages from the assignment.
        - After filtering, create DeliveryOperationItem per package and link to the drone.
        - Update each corresponding operation to use the provided route.
        """
        route_id = payload.route_id
        valid_assignments: List[Dict[str, int]] = []  
        removed_orders: List[int] = []


        assigned_by_order: Dict[int, List[int]] = defaultdict(list)
        for drone_data in payload.drone_ids:
            for order_data in drone_data.orders:
                assigned_by_order[order_data.order_id].extend(order_data.package_ids)


        fully_assigned_orders: set[int] = set()
        for order_id, assigned_packages in assigned_by_order.items():
            all_package_ids = list(DeliveryOperationItem._base_manager.filter(order_item__order_id=order_id).values_list('id', flat=True)) 
            if set(assigned_packages) == set(all_package_ids) and len(all_package_ids) > 0:
                fully_assigned_orders.add(order_id)
            else:
                removed_orders.append(order_id)

        # Flatten only valid assignments
        for drone_data in payload.drone_ids:
            for order_data in drone_data.orders:
                if order_data.order_id in fully_assigned_orders:
                    for pid in order_data.package_ids:
                        valid_assignments.append({
                            "drone_id": drone_data.drone_id,
                            "order_id": order_data.order_id,
                            "package_id": pid,
                        })

        # --- Validation: per-drone capacity (weight), dimensions, and slot count ---
        def get_orderitem_weight_kg(order_item: OrderItem) -> float:
            try:
                if order_item.weight:
                    val = float(order_item.weight.get('value', 0))
                    unit = (order_item.weight.get('unit') or 'kg')
                    return float(convert_unit(val, unit, 'kg'))
                # fallback to packaging spec alternative
                alt = ProcessingRepository.get_package_weight_dimensions_alternative(order_item.id)
                if isinstance(alt, dict) and 'weight' in alt:
                    w = alt['weight'] or {}
                    val = float((w.get('value') or 0))
                    unit = (w.get('unit') or 'kg')
                    return float(convert_unit(val, unit, 'kg'))
            except Exception:
                pass
            return 0.0

        def get_orderitem_dimensions_mm(order_item: OrderItem) -> Tuple[float, float, float]:
            try:
                alt = ProcessingRepository.get_package_weight_dimensions_alternative(order_item.id)
                if isinstance(alt, dict):
                    l = alt.get('length'); w = alt.get('width'); h = alt.get('height')
                    if l and w and h:
                        l_val = float(l if isinstance(l, (int, float)) else l.get('value', 0))
                        w_val = float(w if isinstance(w, (int, float)) else w.get('value', 0))
                        h_val = float(h if isinstance(h, (int, float)) else h.get('value', 0))
                        l_unit = 'mm' if isinstance(l, (int, float)) else (l.get('unit') or 'mm')
                        w_unit = 'mm' if isinstance(w, (int, float)) else (w.get('unit') or 'mm')
                        h_unit = 'mm' if isinstance(h, (int, float)) else (h.get('unit') or 'mm')
                        l_mm = float(convert_unit(l_val, l_unit, 'mm'))
                        w_mm = float(convert_unit(w_val, w_unit, 'mm'))
                        h_mm = float(convert_unit(h_val, h_unit, 'mm'))
                        return l_mm, w_mm, h_mm
            except Exception:
                pass
            return 0.0, 0.0, 0.0

        def get_drone_payload(drone: Device) -> Tuple[float, Tuple[float, float, float]]:
            weight_cap, dims = ProcessingRepository.get_drone_payload(drone.id)
            cap_kg = float(weight_cap.get('value', 0)) if isinstance(weight_cap, dict) else float(weight_cap or 0)
            unit = (dims.get('unit') if isinstance(dims, dict) else 'mm') or 'mm'
            dl = float((dims or {}).get('length', 0) or 0)
            dw = float((dims or {}).get('width', 0) or 0)
            dh = float((dims or {}).get('height', 0) or 0)
            if unit != 'mm':
                dl = float(convert_unit(dl, unit, 'mm'))
                dw = float(convert_unit(dw, unit, 'mm'))
                dh = float(convert_unit(dh, unit, 'mm'))
            return cap_kg, (dl, dw, dh)

        def get_drone_current_load_weight_kg(drone_id: int) -> float:
            total = 0.0
            items = DeliveryOperationItem.objects.filter(drone_id=drone_id, delivery_operation__current_status__code__in=["in_transit_processing", "select_drone_processing"]).select_related('order_item')
            for di in items:
                if di.order_item:
                    total += get_orderitem_weight_kg(di.order_item)
            return total

        def get_drone_remaining_slots(drone: Device) -> Optional[int]:
            cargo = getattr(drone, 'cargo_compartments', None)
            cargo = cargo.first() if cargo else None
            if not cargo:
                return None
            slot_m = cargo.measurements.filter(measurement_type='max_packages').first()
            if not slot_m:
                return None
            max_slots = slot_m.get_numeric_value(user_units=None)
            current = DeliveryOperationItem.objects.filter(drone=drone).count()
            return int(max_slots) - int(current)

        # Build per-drone assignments map of OrderItem objects
        drone_to_items: Dict[int, List[OrderItem]] = defaultdict(list)
        for a in valid_assignments:
            drone_id = a['drone_id']
            order_id = a['order_id']
            pkg_id = a['package_id']
            # Try fetch OrderItem by id; if not, fallback by (order, packaging spec)
            oi = OrderItem._base_manager.filter(order_id=order_id).first()
            if not oi:
                oi = OrderItem._base_manager.filter(order_id=order_id, package_id=pkg_id).first()
            if oi:
                drone_to_items[drone_id].append(oi)

        # Validate for each drone
        for drone_id, items in drone_to_items.items():
            drone = Device._base_manager.get(id=drone_id)
            cap_kg, (dl, dw, dh) = get_drone_payload(drone)
            required_kg = sum(get_orderitem_weight_kg(oi) for oi in items)
            remaining_kg = cap_kg - get_drone_current_load_weight_kg(drone_id)
            
            # Check if total weight of packages exceeds drone capacity
            if required_kg > cap_kg:
                return False, {
                    "success": False,
                    "error": "ORDER_WEIGHT_EXCEEDS_DRONE_CAPACITY",
                    "message": f"Total weight of packages ({required_kg}kg) exceeds drone {drone_id} capacity ({cap_kg}kg)",
                    "drone_id": drone_id,
                    "required_kg": required_kg,
                    "drone_capacity_kg": cap_kg,
                }
            
            if remaining_kg < required_kg or cap_kg <= 0:
                return False, {
                    "success": False,
                    "error": "INSUFFICIENT_WEIGHT_CAPACITY",
                    "message": f"Drone {drone_id} does not have enough remaining weight capacity",
                    "drone_id": drone_id,
                    "required_kg": required_kg,
                    "remaining_kg": remaining_kg,
                    "drone_capacity_kg": cap_kg,
                }
            # slot check if defined
            rem_slots = get_drone_remaining_slots(drone)
            if rem_slots is not None and rem_slots < len(items):
                return False, {
                    "success": False,
                    "error": "INSUFFICIENT_PACKAGE_SLOTS",
                    "message": f"Drone {drone_id} does not have enough available package slots",
                    "drone_id": drone_id,
                    "required_slots": len(items),
                    "remaining_slots": rem_slots,
                }
            # dimensions per item
            for oi in items:
                l, w, h = get_orderitem_dimensions_mm(oi)
                if all(x > 0 for x in (dl, dw, dh, l, w, h)):
                    if not (dl >= l and dw >= w and dh >= h):
                        return False, {
                            "success": False,
                            "error": "DIMENSION_NOT_FIT",
                            "message": f"OrderItem {oi.id} does not fit in drone {drone_id} cargo dimensions",
                            "drone_id": drone_id,
                            "order_item_id": oi.id,
                            "drone_dimensions_mm": {"length": dl, "width": dw, "height": dh},
                            "item_dimensions_mm": {"length": l, "width": w, "height": h},
                        }

        created_count = 0
        # Create DeliveryOperationItem entries and set route on operations
        for item in valid_assignments:
            drone_id = item["drone_id"]
            order_id = item["order_id"]
            package_id = item["package_id"]

            # Fetch models
            # Treat package_id primarily as OrderItem id, fallback by packaging spec within order
            order_item = OrderItem._base_manager.filter(order_id=order_id).first()
            if not order_item:
                order_item = OrderItem._base_manager.filter(order_id=order_id, package_id=package_id).first()
            order = order_item.order
            operation = ProcessingRepository.get_operation_by_order(order)
            if not operation:
                # Create operation if missing with minimal fields
                status = ProcessingRepository.get_processing_statuses().filter(code="select_drone_processing").first()
                operation = DeliveryOperation.objects.create(order=order, current_status=status)

            # Ensure route assignment for this operation
            try:
                ProcessingRepository.update_route_to_operation(operation.id, route_id)
            except Exception as e:
                print(e)
                # If update fails, continue creation but don't crash
                pass

            # Create or update DeliveryOperationItem for this package
            delivery_item, created = DeliveryOperationItem.objects.get_or_create(
                order_item=order_item,
                defaults={
                    "delivery_operation": operation,
                    "drone_id": drone_id,
                },
            )

            # If existed, make sure delivery_operation and drone are set accordingly
            if delivery_item.delivery_operation_id != operation.id or delivery_item.drone_id != drone_id:
                delivery_item.delivery_operation = operation
                delivery_item.drone_id = drone_id
                delivery_item.save()

            if created:
                created_count += 1

        return True,{
            "success": True,
            "created_items": created_count,
            "removed_orders": removed_orders,
            "assigned_orders": list(fully_assigned_orders),
        } 

    @staticmethod
    @transaction.atomic
    def cancel_flight(data: CancelFlightInSchema) -> Dict[str, Any]:
        """
        Cancel all orders associated with the given drone_id.
        Rule: For each order that has any item on this drone, clear the entire order from ALL drones
        (delete DeliveryOperationItem and OrderAssignment), reset route and status to select_route_processing.
        Orders on other drones that are not linked to any of these orders remain untouched.
        """
        try:
            drone = Device._base_manager.get(id=data.drone_id)
        except Device.DoesNotExist:
            return {"success": False, "error": "Drone not found", "updated_operations": 0}

        # Find all operations (orders) that have at least one item on this drone
        op_ids = list(DeliveryOperationItem.objects.filter(drone_id=drone.id,delivery_operation__order_id__in=data.order_ids).values_list('delivery_operation_id', flat=True).distinct())
        updated_ops = 0
        for op_id in op_ids:
            try:
                operation = DeliveryOperation.objects.get(id=op_id)
            except DeliveryOperation.DoesNotExist:
                continue
            order = operation.order
            # Delete all items for this operation (across all drones)
            items_qs = DeliveryOperationItem.objects.filter(delivery_operation=operation)
            for it in items_qs:
                it.drone = None
                it.save()
                OrderAssignment._base_manager.filter(order_item=it.order_item).delete()
            # Clear route and set status
            select_route_status = DeliveryStatus._base_manager.filter(code="select_route_processing").first()
            operation.route = None
            if select_route_status:
                operation.current_status = select_route_status
            operation.save()
            updated_ops += 1
        return {"success": True, "updated_operations": updated_ops, "affected_operations": op_ids}

    @staticmethod
    @transaction.atomic
    def change_drone(data: ChangeDroneInSchema) -> Dict[str, Any]:
 
        result: Dict[str, Any] = {"success": True}
        suitable: Dict[int, List[Dict[str, Any]]] = {}

        def get_item_weight_kg(op_item: DeliveryOperationItem) -> float:
            # Prefer explicit OrderItem.weight if present
            try:
                if op_item.order_item and op_item.order_item.weight:
                    data = op_item.order_item.weight or {}
                    value = float(data.get("value", 0))
                    unit = (data.get("unit") or "kg")
                    return float(convert_unit(value, unit, "kg"))
                # Else fallback to packaging specification measurements using the delivery operation item id
                w, *_ = ProcessingRepository.get_package_weight_dimensions(op_item.id)
                value = float(w.get("value", 0))
                unit = (w.get("unit") or "kg") if isinstance(w, dict) else "kg"
                return float(convert_unit(value, unit, "kg"))
            except Exception:
                return 0.0

        def get_drone_max_capacity_kg(drone: Device) -> float:
            try:
                weight_cap, _ = ProcessingRepository.get_drone_payload(drone.id)
                return float(weight_cap.get("value", 0)) if isinstance(weight_cap, dict) else float(weight_cap or 0)
            except Exception:
                return 0.0
 
        def get_drone_max_dimensions_mm(drone: Device) -> Tuple[float, float, float]:
            try:
                _, dims = ProcessingRepository.get_drone_payload(drone.id)
                # dims may come with unit, default mm
                unit = (dims.get('unit') if isinstance(dims, dict) else 'mm') or 'mm'
                length = float((dims or {}).get('length', 0) or 0)
                width = float((dims or {}).get('width', 0) or 0)
                height = float((dims or {}).get('height', 0) or 0)
                # Convert to mm if needed
                if unit != 'mm':
                    length = float(convert_unit(length, unit, 'mm'))
                    width = float(convert_unit(width, unit, 'mm'))
                    height = float(convert_unit(height, unit, 'mm'))
                return length, width, height
            except Exception:
                return 0.0, 0.0, 0.0

        def get_item_dimensions_mm(op_item: DeliveryOperationItem) -> Tuple[float, float, float]:
            try:
                # Try packaging spec dimensions via repo
                _, l, w, h = ProcessingRepository.get_package_weight_dimensions(op_item.id)
                l_val = float(l.get('value', 0) or 0); l_unit = (l.get('unit') or 'mm')
                w_val = float(w.get('value', 0) or 0); w_unit = (w.get('unit') or 'mm')
                h_val = float(h.get('value', 0) or 0); h_unit = (h.get('unit') or 'mm')
                l_mm = float(convert_unit(l_val, l_unit, 'mm'))
                w_mm = float(convert_unit(w_val, w_unit, 'mm'))
                h_mm = float(convert_unit(h_val, h_unit, 'mm'))
                return l_mm, w_mm, h_mm
            except Exception:
                return 0.0, 0.0, 0.0

        def drone_has_slots_for_packages(drone: Device, required_count: int) -> bool:
            # If drone cargo compartment has max_packages measurement, enforce. Else allow.
            try:
                cargo = getattr(drone, 'cargo_compartments', None)
                cargo = cargo.first() if cargo else None
                if not cargo:
                    return True
                slot_m = cargo.measurements.filter(measurement_type='max_packages').first()
                if not slot_m:
                    return True
                max_slots = slot_m.get_numeric_value(user_units=None)
                current = DeliveryOperationItem.objects.filter(drone=drone).count()
                return (max_slots - current) >= required_count
            except Exception:
                return True

        def items_fit_dimensions(drone: Device, items: List[DeliveryOperationItem]) -> bool:
            dl, dw, dh = get_drone_max_dimensions_mm(drone)
            if dl <= 0 or dw <= 0 or dh <= 0:
                return True  # no dimension constraint data
            for it in items:
                l, w, h = get_item_dimensions_mm(it)
                if any(x <= 0 for x in (l, w, h)):
                    # no item dims data: treat as unknown but allow
                    continue
                if not (dl >= l and dw >= w and dh >= h):
                    return False
            return True

        def get_drone_current_load_kg(drone_id: int) -> float:
            load = 0.0
            items = DeliveryOperationItem.objects.filter(drone_id=drone_id).select_related('order_item')
            for it in items:
                load += get_item_weight_kg(it)
            return load

        # Collect packages for the given orders that are currently on from_drone
        src_drone_id = data.from_drone
        required_items: List[DeliveryOperationItem] = []
        related_operations: List[int] = []
        for order_id in data.order_ids:
            try:
                order = Order._base_manager.get(id=order_id)
            except Order.DoesNotExist:
                continue
            operation = ProcessingRepository.get_operation_by_order(order)
            if not operation:
                continue
            related_operations.append(operation.id)
            items = DeliveryOperationItem.objects.filter(delivery_operation=operation, drone_id=src_drone_id).select_related('order_item')
            required_items.extend(list(items))

        required_kg = sum(get_item_weight_kg(it) for it in required_items)
        
        if data.to_drone is None:
            # Suggest available drones that have enough remaining capacity
            avail_status = DeviceStatus.objects.filter(code='available').first()
            candidates = Device.objects.filter(status=avail_status, active=True).exclude(id=src_drone_id)
            suitable_ids: List[int] = []
            for dr in candidates:
                max_kg = get_drone_max_capacity_kg(dr)
                current_kg = get_drone_current_load_kg(dr.id)
                if (max_kg - current_kg) >= required_kg and max_kg > 0 and drone_has_slots_for_packages(dr, len(required_items)) and items_fit_dimensions(dr, required_items):
                    suitable_ids.append(dr.id)
            # Exclude devices that are used in delivery operations with select_drone_processing status
            # but with different route_id than the one provided in data
            select_drone_status = DeliveryStatus.objects.filter(code='select_drone_processing').first()
            if select_drone_status:
                # Get device IDs that are used in delivery operations with select_drone_processing status
                # and route_id different from data.route_id
                excluded_device_ids = DeliveryOperationItem.objects.filter(
                    delivery_operation__current_status=select_drone_status,
                    delivery_operation__route__isnull=False
                ).exclude(
                    delivery_operation__route_id=data.route_id
                ).values_list('drone_id', flat=True).distinct()
                
                # Filter out None values (devices that don't have drone assigned)
                excluded_device_ids = [did for did in excluded_device_ids if did is not None]
                
                # Remove excluded devices from suitable_ids
                suitable_ids = [did for did in suitable_ids if did not in excluded_device_ids]
            
            # Get the first terminal of the route
            first_terminal = RouteTerminal.objects.filter(
                route_id=data.route_id
            ).order_by('order').first()
            
            # Filter devices to only include those at the first terminal of the route
            devices_query = Device.objects.filter(id__in=suitable_ids)
            if first_terminal and first_terminal.terminal_id:
                devices_query = devices_query.filter(terminal_id=first_terminal.terminal_id)
            
            devices = devices_query.annotate(
                battery_capacity=Subquery(
                    Measurement.objects.filter(
                        content_type=ContentType.objects.get_for_model(PropulsionSystem),
                        object_id=OuterRef('propulsion_system__id'),
                        measurement_type='battery_capacity'
                    ).annotate(
                        full_battery=Concat(
                            F('data__value'),
                            Value(' '),
                            RawSQL("(data ->> 'unit')", []),
                            output_field=CharField()
                        )
                    ).values('full_battery')[:1]
                ),
                payload_capacity=Subquery(
                    Measurement.objects.filter(
                        content_type=ContentType.objects.get_for_model(DimensionsAndWeight),
                        object_id=OuterRef('dimensions_and_weight__id'),
                        measurement_type='payload_capacity'
                    ).annotate(
                        full_payload=Concat(
                            F('data__value'),
                            Value(' '),
                            RawSQL("(data ->> 'unit')", []),
                            output_field=CharField()
                        )
                    ).values('full_payload')[:1]
                ),
                model=F('manufacturer_information__model_number'),
            )
            return {"success": True, "devices": devices}

        # Reassign all items of the given orders from from_drone to to_drone
        to_drone_id = data.to_drone
        for order_id in data.order_ids:
            try:
                order = Order._base_manager.get(id=order_id)
            except Order.DoesNotExist:
                    continue
            operation = ProcessingRepository.get_operation_by_order(order)
            if not operation:
                    continue
            DeliveryOperationItem.objects.filter(delivery_operation=operation, drone_id=src_drone_id).update(drone_id=to_drone_id)
        return {"success": True}

    @staticmethod
    @transaction.atomic
    def approve_flight(data: ApproveFlightInSchema) -> Dict[str, Any]:
        try:
            started_operations: List[int] = []
            # Resolve drone unique id from provided drone_id in schema
            try:
                device = Device._base_manager.get(id=data.drone_id)
                device.on_approve_flight = True
                device.status = DeviceStatus._base_manager.get(code="on_mission")
                device.save()
                drone_uid = device.unit_id
            except Device.DoesNotExist:
                return {"success": False, "error": "Drone not found", "started_operations": []}

            # 1) Mark this drone as approved for each given order's operation (partial approve flag)
            affected_operations: Dict[int, DeliveryOperation] = {}
            for order_id in data.order_ids:
                try:
                    order = Order._base_manager.get(id=order_id)
                except Order.DoesNotExist:
                    continue
                operation = ProcessingRepository.get_operation_by_order(order)
                if not operation:
                    continue
                # Update new flags
                operation.is_partial_approved = True
                operation.save()
                # Store approval row (idempotent)
                doa, _ = DeliveryOperationApproval.objects.get_or_create(
                    delivery_operation=operation,
                    drone_id=data.drone_id,
                    defaults={"approved": True}
                )
                # Save checklist selections if provided (no validation required)
                if getattr(data, 'check_lists', None):
                    # Create relational rows with snapshots; idempotent per (approval, checklist)
                    checklist_ids = sorted(list(set(list(data.check_lists))))
                    existing = set(DeliveryOperationApprovalChecklist.objects.filter(
                        approval=doa,
                        checklist_id__in=checklist_ids
                    ).values_list('checklist_id', flat=True))
                    to_create = [cid for cid in checklist_ids if cid not in existing]
                    if to_create:
                        # Fetch checklist and category for snapshots
                        items = list(ChecklistSetting.objects.select_related('category').filter(id__in=to_create, is_active=True))
                        payload = []
                        for it in items:
                            payload.append(DeliveryOperationApprovalChecklist(
                                approval=doa,
                                checklist=it,
                                item_name_snapshot=it.item_name,
                                category_code_snapshot=(it.category.code if it.category else None)
                            ))
                        if payload:
                            DeliveryOperationApprovalChecklist.objects.bulk_create(payload, ignore_conflicts=True)
                # save auto checklist
                if getattr(data, 'auto_checklist', None):
                    # Đảm bảo another_info không phải None và cập nhật an toàn
                    if operation.another_info is None:
                        operation.another_info = {}
                    operation.another_info['auto_checklist'] = data.auto_checklist
                    operation.save()
                    
                        
                affected_operations[operation.id] = operation
                # Mark all items of this operation assigned to this drone as approved
                DeliveryOperationItem.objects.filter(
                    delivery_operation=operation,
                    drone_id=data.drone_id
                ).update(is_drone_approved=True)

            # 2) Build order-drone bipartite graph from current assignments
            # Get ALL current active assignments, not just approved ones
            # This is crucial to identify all connected components correctly
            edges = list(
                DeliveryOperationItem.objects.filter(
                    delivery_operation__current_status__code__in=['select_drone_processing'],
                    drone_id__isnull=False  # Only consider items with assigned drones
                ).values_list(
                    'delivery_operation__order_id', 'drone_id'
                ).distinct()
            )
            order_to_drones: Dict[int, set] = defaultdict(set)
            drone_to_orders: Dict[int, set] = defaultdict(set)
            for order_id, drone_id in edges:
                if order_id is None or drone_id is None:
                    continue
                order_to_drones[order_id].add(drone_id)
                drone_to_orders[drone_id].add(order_id)

            def bfs_component(start_order_id: int) -> Tuple[set, set]:
                visited_orders: set = set()
                visited_drones: set = set()
                queue = [start_order_id]
                while queue:
                    oid = queue.pop(0)
                    if oid in visited_orders:
                        continue
                    visited_orders.add(oid)
                    for did in order_to_drones.get(oid, set()):
                        if did not in visited_drones:
                            visited_drones.add(did)
                            for next_order in drone_to_orders.get(did, set()):
                                if next_order not in visited_orders:
                                    queue.append(next_order)
                return visited_orders, visited_drones

            def get_component_operations(order_ids: set) -> List[DeliveryOperation]:
                ops = DeliveryOperation.objects.filter(order_id__in=list(order_ids))
                return list(ops)

            def get_approved_drone_ids_from_ops(ops: List[DeliveryOperation]) -> set:
                approved: set = set()
                from delivery.models import DeliveryOperationApproval as DOA
                op_ids = [op.id for op in ops]
                for did in DOA.objects.filter(delivery_operation_id__in=op_ids, approved=True).values_list('drone_id', flat=True).distinct():
                    approved.add(int(did))
                return approved

            def check_if_drone_fully_approved_for_operation(drone_id: int, operation_id: int) -> bool:
                """
                Check if a drone is fully approved for all its items in a specific operation
                """
                items = DeliveryOperationItem.objects.filter(
                    delivery_operation_id=operation_id,
                    drone_id=drone_id
                )
                if not items.exists():
                    return False
                
                # Check if all items for this drone in this operation are approved
                return all(item.is_drone_approved for item in items)

            def get_fully_approved_drones_for_component(component_drones: set, component_orders: set) -> set:
                """
                Get drones that are fully approved for ALL their operations in the component
                """
                fully_approved_drones = set()
                
                for drone_id in component_drones:
                    # Check if this drone is approved for ALL operations it's involved in
                    drone_operations = set()
                    for order_id in component_orders:
                        if drone_id in order_to_drones.get(order_id, set()):
                            try:
                                order = Order._base_manager.get(id=order_id)
                                operation = ProcessingRepository.get_operation_by_order(order)
                                if operation:
                                    drone_operations.add(operation.id)
                            except Order.DoesNotExist:
                                continue
                    
                    # Check if drone is approved for all its operations
                    if drone_operations:
                        is_fully_approved = True
                        for op_id in drone_operations:
                            if not check_if_drone_fully_approved_for_operation(drone_id, op_id):
                                is_fully_approved = False
                                break
                        
                        if is_fully_approved:
                            fully_approved_drones.add(drone_id)
                
                return fully_approved_drones

            started_drones_uids: List[str] = []
            processed_components: set = set()
            components_info: List[Dict[str, Any]] = []
            partial_operation_ids: List[int] = []

            check_if_all_others_package_are_approved = ProcessingService.check_if_all_others_package_are_approved(data.drone_id, data.order_ids)

            for order_id in data.order_ids:
                component_orders, component_drones = bfs_component(order_id)
                comp_key = (tuple(sorted(component_orders)), tuple(sorted(component_drones)))
                if comp_key in processed_components:
                    continue
                processed_components.add(comp_key)

                comp_ops = get_component_operations(component_orders)
                
                # Use the new logic to check if all drones in the component are fully approved
                fully_approved_drones = get_fully_approved_drones_for_component(component_drones, component_orders)
                # fully_approved = component_drones.issubset(fully_approved_drones)
                fully_approved = True
                
                print(f"Component: orders={component_orders}, drones={component_drones}")
                print(f"Fully approved drones: {fully_approved_drones}")
                print(f"Fully approved: {fully_approved}")

                comp_started_ops: List[int] = []
                comp_started_drones: List[str] = []
                pending_drone_ids: List[int] = sorted(list(component_drones - fully_approved_drones))

                if fully_approved:
                    # Update status and clear partial flags
                    for op in comp_ops:
                        if check_if_all_others_package_are_approved:
                            ProcessingRepository.update_status_to_operation(op.id, "in_transit_processing")
                            op.is_partial_approved = False
                            op.save(update_fields=['is_partial_approved'])
                            device.approve_flight_now = False
                            device.on_approve_flight = False
                            device.save()
                            # find all packages in the same operation
                            all_packages = DeliveryOperationItem._base_manager.filter(delivery_operation=op)
                            for package in all_packages:
                                drone = package.drone
                                if drone:
                                    drone.approve_flight_now = False
                                    drone.on_approve_flight = False
                                    drone.save()

                        comp_started_ops.append(op.id)
                        started_operations.append(op.id)

                    # Start missions per drone using terminals aggregated across component
                    drone_to_terminals: Dict[int, List[Any]] = defaultdict(list)
                    op_id_to_terminals: Dict[int, List[Any]] = {}
                    drone_to_items: Dict[int, List[Any]] = defaultdict(list)
                    for op in comp_ops:
                        try:
                            route_id = ProcessingRepository.get_route_by_operation_id(op.id)
                            if route_id:
                                terminals = ProcessingRepository.get_route_terminals_by_route_id(route_id)
                            else:
                                terminals = []
                        except Exception:
                            terminals = []
                        op_id_to_terminals[op.id] = terminals

                    items = DeliveryOperationItem.objects.filter(delivery_operation__in=comp_ops).select_related('drone', 'delivery_operation')
                    for item in items:
                        if not item.drone_id:
                            continue
                        terminals = op_id_to_terminals.get(item.delivery_operation_id, [])
                        if terminals:
                            drone_to_terminals[item.drone_id].extend(terminals)
                        drone_to_items[item.drone_id].append(item.id)

                    if drone_to_terminals:
                        drone_map: Dict[int, Device] = {d.id: d for d in Device.objects.filter(id__in=list(drone_to_terminals.keys()))}
                        # Collect all drones that need to start mission
                        drones_to_start: List[Tuple[Device, List[int]]] = []
                        for did, terminals in drone_to_terminals.items():
                            print(f"Did: {did}, Terminals: {terminals}")
                            seen = set()
                            uniq: List[Any] = []
                            for t in terminals:
                                try:
                                    tid = t[2] if isinstance(t, (list, tuple)) and len(t) > 2 else None
                                except Exception:
                                    tid = None
                                key = ("id", tid) if tid is not None else ("pos", t[0] if isinstance(t, (list, tuple)) and len(t) > 0 else None, t[1] if isinstance(t, (list, tuple)) and len(t) > 1 else None)
                                if key in seen:
                                    continue
                                seen.add(key)
                                uniq.append(t)
                            device_obj = drone_map.get(did)
                            if device_obj and device_obj.unit_id and uniq:
                                print(f"Device obj: {device_obj}")
                                print(f"Uniq: {uniq}")
                                drones_to_start.append((device_obj, drone_to_items[did]))
                        
                        # First, perform all database changes (create flight logs, update status)
                        for device_obj, item_ids in drones_to_start:
                            try:
                                # create flight log
                                for item_id in item_ids:
                                    order_item = DeliveryOperationItem.objects.get(id=item_id).order_item
                                    FlightLogService.create_flight_log(order_item)
                                # update drone status to in_transit
                                device_obj.status = DeviceStatus.objects.filter(code="on_mission").first()
                                device_obj.save()
                                comp_started_drones.append(device_obj.unit_id)
                                started_drones_uids.append(device_obj.unit_id)
                            except Exception as e:
                                print(f"❌ [DRONE_MISSION] Error preparing drone mission: {str(e)}")
                                raise
                        
                        # Then, call all Flightbird APIs
                        # If any API call fails, transaction will rollback all database changes
                        failed_drones: List[str] = []
                        for device_obj, item_ids in drones_to_start:
                            try:
                                result = ProcessingService.gx_start_mission_to_gcs(
                                    StartMissionToGcsInSchema(drone_unique_id=device_obj.unit_id),
                                    with_thread=False
                                )
                                if not result:
                                    failed_drones.append(device_obj.unit_id)
                                    logger.error(f"Failed to start mission for drone {device_obj.unit_id} via Flightbird")
                            except Exception as e:
                                failed_drones.append(device_obj.unit_id)
                                logger.error(f"Exception when starting mission for drone {device_obj.unit_id} via Flightbird: {str(e)}")
                        
                        # If any Flightbird API call failed, raise exception to rollback transaction
                        if failed_drones:
                            error_msg = f"Failed to start mission via Flightbird for drones: {', '.join(failed_drones)}"
                            logger.error(f"[APPROVE_FLIGHT] {error_msg}")
                            raise Exception(error_msg)
                else:
                    # Track partial operations in this component
                    comp_started_ops = []
                    comp_started_drones = []
                    partial_operation_ids.extend([op.id for op in comp_ops])

                components_info.append({
                    "orders": sorted(list(component_orders)),
                    "drones": sorted(list(component_drones)),
                    "approved_drone_ids": sorted(list(fully_approved_drones)),
                    "pending_drone_ids": pending_drone_ids,
                    "fully_approved": fully_approved,
                    "status_changed_operations": comp_started_ops,
                    "missions_started_for_drones": comp_started_drones,
                })

            overall_success = all(c.get("fully_approved", False) for c in components_info) if components_info else False

            response = {
                "success": True,
                "status_code": "success",
                "started_operations": started_operations,
                "started_drones": started_drones_uids,
                "components": components_info,
                "partial_operations": sorted(list(set(partial_operation_ids))),
            }
            if not overall_success:
                pending = []
                pending_orders = []
                for comp in components_info:
                    pending_orders.append(comp.get("orders", []))
                    if not comp.get("fully_approved"):
                        pending.append({
                            "orders": comp.get("orders", []),
                            "pending_drone_ids": comp.get("pending_drone_ids", []),
                        })
                response.update({
                    "error": "PENDING_APPROVALS",
                    "status_code": "warning",
                    "message": {
                        "en": f"This drone contains the package of Orders: {pending_orders}",
                        "kr": f"드론에 다음 주문 패키지가 포함되어 있습니다: {pending_orders}",
                    },
                    "pending_components": pending,
                })
            else:
                response.update({
                    "message": {
                        "en": "The drone has started its flight",
                        "kr": "드론이 비행을 시작했습니다",
                    },
                })
            
            # Note: Transaction will be automatically committed by @transaction.atomic decorator
            # when function returns successfully, or rolled back if exception is raised
            
            return response
        except Exception as e:
            # Check if error is related to Flightbird API failure
            error_str = str(e)
            if "Flightbird" in error_str or "Failed to start mission" in error_str:
                return {
                    "success": False,
                    "status_code": "error",
                    "message": {
                        Language.EN: MESSAGE_ENUM.APPROVE_FLIGHT_FLIGHTBIRD_ERROR[Language.EN],
                        Language.KR: MESSAGE_ENUM.APPROVE_FLIGHT_FLIGHTBIRD_ERROR[Language.KR],
                        Language.TH: MESSAGE_ENUM.APPROVE_FLIGHT_FLIGHTBIRD_ERROR[Language.TH],
                    },
                }
            else:
                return {
                    "success": False,
                    "status_code": "error",
                    "message": {
                        Language.EN: f"Error in approve_flight: {error_str}",
                        Language.KR: f"드론 승인 오류: {error_str}",
                        Language.TH: f"เกิดข้อผิดพลาดในการอนุมัติการบิน: {error_str}",
                    },
                }
        
    @staticmethod
    @transaction.atomic
    def approve_flight_not_yet(data: ApproveFlightInSchema) -> QuerySet:
        """
        Approve flight for not yet approved operations
        """
        try:
            device = Device._base_manager.get(id=data.drone_id)
            device.approve_flight_now = True
            device.on_approve_flight = True
            device.save()
            # Save checklist selections if provided (no validation required)
            if getattr(data, 'check_lists', None):
                checklist_ids = sorted(list(set(list(data.check_lists))))
                for order_id in data.order_ids:
                    operation = ProcessingRepository.get_operation_by_order(order_id)
                    # Create relational rows with snapshots; idempotent per (approval, checklist)
                    doa, _ = DeliveryOperationApproval.objects.get_or_create(
                        delivery_operation=operation,
                        drone_id=data.drone_id,
                        defaults={"approved": True}
                    )
                    existing = set(DeliveryOperationApprovalChecklist.objects.filter(
                        approval=doa,
                        checklist_id__in=checklist_ids
                    ).values_list('checklist_id', flat=True))
                    to_create = [cid for cid in checklist_ids if cid not in existing]
                    if to_create:
                        # Fetch checklist and category for snapshots
                        items = list(ChecklistSetting.objects.select_related('category').filter(id__in=to_create, is_active=True))
                        payload = []
                        for it in items:
                            payload.append(DeliveryOperationApprovalChecklist(
                                approval=doa,
                                checklist=it,
                                item_name_snapshot=it.item_name,
                                category_code_snapshot=(it.category.code if it.category else None)
                            ))
                        if payload:
                            DeliveryOperationApprovalChecklist.objects.bulk_create(payload, ignore_conflicts=True)
            device_operations = ProcessingRepository.get_operation_select_drone_processing()
            return device_operations
        except Exception as e:
            # Return empty QuerySet instead of empty list
            return DeliveryOperation.objects.none()
        

    @staticmethod
    def check_if_all_others_package_are_approved(device_id: int, order_ids: List[int]) -> bool:
        """
        Approve flight for not yet approved operations by order ids
        """
        # 1) Mark this drone as approved for each given order's operation (partial approve flag)
        for order_id in order_ids:
            delivery_operation_items = DeliveryOperationItem._base_manager.filter(order_item__order_id=order_id)
            for delivery_operation_item in delivery_operation_items:
                if not delivery_operation_item.drone_id:
                    return False
                else:
                    if delivery_operation_item.drone_id == device_id:
                        continue
                    if not delivery_operation_item.is_drone_approved:
                        return False
        return True
    
    def check_is_approved_by_drone(device_id: int, order_ids: List[int]) -> bool:
        """
        Check if the drone is approved by the drone
        """
        for order_id in order_ids:
            delivery_operation_items = DeliveryOperationItem._base_manager.filter(order_item__order_id=order_id, drone_id=device_id)
            for delivery_operation_item in delivery_operation_items:
                if not delivery_operation_item.is_drone_approved:
                    return False
        return True

    @staticmethod
    def get_delivery_items_with_suitable_drones_by_operation_id(operation_id: int) -> list:
        """
        Get delivery operation items by operation ID with suitable drones for each item
        """
        return ProcessingRepository.get_delivery_items_with_suitable_drones_by_operation_id(operation_id)
        
    @staticmethod
    def get_delivery_items_with_suitable_drones_by_operation_item_id(operation_item_id: int) -> list:
        """
        Get delivery operation items by operation item ID with suitable drones for each item
        """
        return ProcessingRepository.get_delivery_items_with_suitable_drones_by_operation_item_id(operation_item_id)

    @staticmethod
    def start_drone_delivery(operation_id: int) -> bool:
        """
        Start the drone delivery process for an operation
        """
        try:
            print(f"🚁 [DRONE_DELIVERY] Starting drone delivery for operation {operation_id}")
            
            # get route and terminals
            print(f"🗺️ [DRONE_DELIVERY] Getting route for operation {operation_id}")
            route = ProcessingRepository.get_route_by_operation_id(operation_id)
            print(f"✅ [DRONE_DELIVERY] Route ID: {route}")
            
            print(f"🏢 [DRONE_DELIVERY] Getting terminals for route {route}")
            terminals = ProcessingRepository.get_route_terminals_by_route_id(route)
            print(f"📊 [DRONE_DELIVERY] Found {len(terminals)} terminals: {terminals}")
            
            print(f"🚁 [DRONE_DELIVERY] Getting devices for operation {operation_id}")
            devices = ProcessingRepository.get_devices_by_operation_id(operation_id)
            drones_unique_ids = [device.unit_id for device in devices]
            print(f"📊 [DRONE_DELIVERY] Found {len(devices)} devices with IDs: {drones_unique_ids}")
            
            print(f"🚀 [DRONE_DELIVERY] Starting missions for {len(drones_unique_ids)} drones")
            ProcessingService.start_drones_mission(drones_unique_ids, terminals, route)
            print(f"✅ [DRONE_DELIVERY] All drone missions initiated successfully")

            # create flight log
            for item in DeliveryOperationItem.objects.filter(delivery_operation_id=operation_id):
                order_item = item.order_item
                FlightLogService.create_flight_log(order_item)
            
            return True
            
        except Exception as e:
            print(f"❌ [DRONE_DELIVERY] Error starting drone delivery: {str(e)}")
            return False
    

    @staticmethod
    def start_drones_mission(drones_unique_ids: list, terminals: list, route: int) -> bool:
        """
        Start the drones mission asynchronously using ThreadPoolExecutor
        """
        try:
            print(f"🚁 [DRONES_MISSION] Starting missions for {len(drones_unique_ids)} drones")
            print(f"📍 [DRONES_MISSION] Target terminals: {len(terminals)} locations")
            
            def start_single_drone_mission(drone_unique_id):
                print(f"🚁 [DRONE_MISSION] Starting individual mission for drone: {drone_unique_id}")
                result = ProcessingService.gx_start_mission_to_gcs(StartMissionToGcsInSchema(drone_unique_id=drone_unique_id), 
                                                                   with_thread=True)
                print(f"✅ [DRONE_MISSION] Mission start result for {drone_unique_id}: {result}")
                return result
            
            # Use ThreadPoolExecutor for better thread management
            with ThreadPoolExecutor(max_workers=5) as executor:
                print(f"🔧 [DRONES_MISSION] ThreadPoolExecutor created with max_workers=5")
                # Submit all drone missions concurrently
                futures = [executor.submit(start_single_drone_mission, drone_id) 
                          for drone_id in drones_unique_ids]
                print(f"📤 [DRONES_MISSION] Submitted {len(futures)} mission tasks to executor")
            
            print(f"✅ [DRONES_MISSION] All drone missions submitted successfully")
            return True
            
        except Exception as e:
            print(f"❌ [DRONES_MISSION] Error in drones mission start: {str(e)}")
            return False

    @staticmethod
    def check_drone_upload_mission_by_order_ids(order_ids: list, drone: Device) -> bool:
        """
        Check if drone upload mission by order ids
        """
        return ProcessingRepository.check_drone_upload_mission_by_order_ids(order_ids, drone)
    
    @staticmethod
    @transaction.atomic
    def gx_upload_mission_to_gcs(data: UploadMissionToGcsInSchema):
        """
        Upload mission to GCS
        """
        def validate_all_orders_same_route(data: UploadMissionToGcsInSchema):
            """Function to validate all orders have the same route"""
            route_ids = []
            for order_id in data.order_ids:
                route_id = ProcessingRepository.get_route_by_order_id(order_id)
                route_ids.append(route_id)
            return len(set(route_ids)) == 1, route_ids[0] if route_ids else None
            
        def get_route_terminals(route_id: int):
            """Function to get terminals"""
            return ProcessingRepository.get_route_terminals_queryset_by_route_id(route_id)
        
        def make_drone_request():
            """Function to run in separate thread"""
            is_valid, route_id = validate_all_orders_same_route(data)
            if not is_valid:
                raise ValueError("All orders must have the same route")
            
            route_terminals = get_route_terminals(route_id)
            waypoints = []
            for route_terminal in route_terminals:
                # Use the route_terminal directly from the loop, no need to query again
                command_data = route_terminal.command_line
                frame_data = route_terminal.frame
                speed = 0
                altitude = 0
                hold = 0
                
                # Extract command ID from command_data
                command_id = 0
                if command_data and isinstance(command_data, dict):
                    command_id = int(list(command_data.keys())[0]) if command_data else 0
                
                # Extract frame ID from frame_data
                frame_id = 0
                if frame_data and isinstance(frame_data, dict):
                    frame_id = int(list(frame_data.keys())[0]) if frame_data else 0
                
                # Extract params from command_data
                params = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                if command_data and isinstance(command_data, dict):
                    print(f"🔍 [DEBUG] command_data structure: {command_data}")
                    command_values = list(command_data.values())[0]
                    print(f"🔍 [DEBUG] command_values: {command_values}")
                    print(f"🔍 [DEBUG] command_values type: {type(command_values)}")
                    
                    # command_values is already the dict containing command_name and params
                    # So we need to get the params array directly
                    if isinstance(command_values, dict):
                        params = list(command_values.values())[0]
                        print(f"🔍 [DEBUG] params from dict: {params}")
                    else:
                        params = command_values
                        print(f"🔍 [DEBUG] params from direct: {params}")
                    
                    # Convert all params to float
                    try:
                        print(f"🔍 [DEBUG] params before conversion: {params}")
                        print(f"🔍 [DEBUG] params type: {type(params)}")
                        if isinstance(params, list):
                            params = [float(param) for param in params]
                        else:
                            print(f"⚠️ [CONVERSION] params is not a list: {type(params)}")
                            params = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                        print(f"params (converted to float): {params}")
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ [CONVERSION] Error converting params to float: {e}")
                        params = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                    print(f"params: {params}")
                    
                        
                # Validate latitude (param 5) and longitude (param 6)
                if len(params) >= 6:
                    lat = params[4]  # Latitude
                    lng = params[5]  # Longitude
                    
                    print(f"🔍 [DEBUG] Validating coordinates - Lat: {lat}, Lng: {lng}")
                    
                    # Validate latitude: must be between -90 and 90
                    if not (-90 <= lat <= 90):
                        print(f"⚠️ [VALIDATION] Invalid latitude: {lat}. Must be between -90 and 90")
                        params[4] = 0.0  # Set default value
                        raise ValueError("Invalid latitude")
                    
                    # Validate longitude: must be between -180 and 180
                    if not (-180 <= lng <= 180):
                        print(f"⚠️ [VALIDATION] Invalid longitude: {lng}. Must be between -180 and 180")
                        params[5] = 0.0  # Set default value
                        raise ValueError("Invalid longitude")
                    
                    print(f"✅ [VALIDATION] Valid coordinates - Lat: {params[4]}, Lng: {params[5]}")
                else:
                    print(f"⚠️ [VALIDATION] Params array too short: {len(params)}. Expected at least 7 elements")
                    raise ValueError("Params array too short")
                    
                if route_terminal:
                    # Get measurements from RouteTerminal, not Terminal
                    terminal_speed = route_terminal.measurements.filter(measurement_type="cruise_speed").first()
                    terminal_altitude = route_terminal.measurements.filter(measurement_type="operating_altitude").first()
                    hold_measurement = route_terminal.measurements.filter(measurement_type="time_stops").first()
                    
                    if terminal_speed:
                        speed = terminal_speed.get_numeric_value(user_units=None) or 0
                    
                    if terminal_altitude:
                        altitude = terminal_altitude.get_numeric_value(user_units=None) or 0
                        
                    if hold_measurement:    
                        hold = convert_unit(hold_measurement.data.get('value'), hold_measurement.data.get('unit'), 's') or 0
                        
                
                waypoint = {
                    "command": command_id,
                    "frame": frame_id,
                    "altitude": altitude,
                    "speed": speed,
                    "hold": hold,
                    "params": params,
                }
                
                print(f"🔍 [DEBUG] Final waypoint: {waypoint}")
                
                waypoints.append(waypoint)
            payload = {
                "UniqueId": data.drone_unique_id,
                "twoway": ProcessingRepository.get_route_twoway_by_operation_id(route_id) if route_id else False,
                "waypoints": waypoints
            }
            
            print(f"📤 [API_REQUEST] Sending mission to {DRONE_API_URL}/api/drone/mission-v2/upload")
            print(f"📋 [API_REQUEST] Payload: {payload}")
            print(f"🔍 [DEBUG] Number of waypoints: {len(waypoints)}")
            
            try:
                headers = get_gcs_api_headers()
                response = requests.post(f"{DRONE_API_URL}/api/drone/mission-v2/upload", json=payload, headers=headers, timeout=30)
                response.raise_for_status()  # Raise an exception for bad status codes
            except requests.exceptions.HTTPError as e:
                print(f"❌ [API_REQUEST] HTTP Error: {e}")
                print(f"📊 [API_REQUEST] Response status: {response.status_code}")
                print(f"📊 [API_REQUEST] Response content: {response.text}")
                raise ValueError(f"{response.text}")
            
            response_data = response.json()
            print(f"✅ [API_REQUEST] Mission API success for {data.drone_unique_id}")
            print(f"📊 [API_REQUEST] Response: {response_data}")
            return True
        
        try:
            print(f"🧵 [UPLOAD_MISSION] Uploading mission to drone {data.drone_unique_id}")
            result = make_drone_request()
            # update flag upload mission on operation items
            drone = ProcessingRepository.get_drone_by_unique_id(data.drone_unique_id)
            
            # Check if drone exists before updating
            if drone is None:
                print(f"⚠️ [UPLOAD_MISSION] Drone with unique_id {data.drone_unique_id} not found in database")
                raise ValueError(f"Drone with unique_id {data.drone_unique_id} not found")
            
            ProcessingRepository.update_upload_mission_to_operation_item_by_order_ids_and_drone(data.order_ids, 
                                                                                                drone, 
                                                                                                True)
            
            print(f"✅ [UPLOAD_MISSION] Mission uploaded to drone {data.drone_unique_id}")
            return result
                
        except Exception as e:
            msg_err = f" Error uploading mission to drone: {str(e)}"
            print(msg_err)
            raise ValueError(e)
    
    
    @staticmethod
    @transaction.atomic
    def reset_terminal_sequences_for_drone(drone_unique_id: str):
        """
        Reset all terminal sequences (is_visited=False) for all delivery operations 
        associated with the given drone when restarting a mission.
        If terminal sequences don't exist, create them.
        
        Args:
            drone_unique_id: Unique ID of the drone
            
        Returns:
            Number of terminal sequences reset or created
        """
        from delivery.models import TerminalSequence, DeliveryOperationItem
        from devices.models import Device
        
        try:
            # Get drone by unique_id
            drone = ProcessingRepository.get_drone_by_unique_id(drone_unique_id)
            if not drone:
                print(f"⚠️ [RESET_SEQUENCES] Drone with unique_id {drone_unique_id} not found")
                return 0
            
            # Get all delivery operations for this drone from DeliveryOperationItem
            delivery_operation_ids = DeliveryOperationItem.objects.filter(
                drone=drone
            ).values_list('delivery_operation_id', flat=True).distinct()
            
            if not delivery_operation_ids:
                print(f"⚠️ [RESET_SEQUENCES] No delivery operations found for drone {drone_unique_id}")
                return 0
            
            from delivery.models import DeliveryOperation
            total_count = 0
            
            # Process each delivery operation
            for delivery_operation_id in delivery_operation_ids:
                try:
                    delivery_operation = DeliveryOperation.objects.get(id=delivery_operation_id)
                    
                    # Check if terminal sequences exist for this delivery operation and drone
                    existing_sequences = TerminalSequence.objects.filter(
                        delivery_operation=delivery_operation,
                        drone=drone
                    )
                    
                    if existing_sequences.exists():
                        # Reset existing terminal sequences
                        updated_count = existing_sequences.filter(
                            is_visited=True
                        ).update(
                            is_visited=False,
                            visited_at=None
                        )
                        print(f"✅ [RESET_SEQUENCES] Reset {updated_count} terminal sequences for delivery {delivery_operation.order.order_code}")
                        total_count += updated_count
                    else:
                        # Create new terminal sequences
                        created_sequences = ProcessingService.create_terminal_sequence_for_delivery(
                            delivery_operation, drone
                        )
                        created_count = len(created_sequences)
                        print(f"✅ [RESET_SEQUENCES] Created {created_count} terminal sequences for delivery {delivery_operation.order.order_code}")
                        total_count += created_count
                        
                except DeliveryOperation.DoesNotExist:
                    print(f"⚠️ [RESET_SEQUENCES] Delivery operation {delivery_operation_id} not found")
                    continue
                except Exception as e:
                    print(f"❌ [RESET_SEQUENCES] Error processing delivery operation {delivery_operation_id}: {str(e)}")
                    continue
            
            print(f"✅ [RESET_SEQUENCES] Total {total_count} terminal sequences processed for drone {drone_unique_id}")
            return total_count
            
        except Exception as e:
            print(f"❌ [RESET_SEQUENCES] Error resetting terminal sequences: {str(e)}")
            return 0
    
    @staticmethod
    def gx_start_mission_to_gcs(data: StartMissionToGcsInSchema, 
                                with_thread: bool = False):
        """
        Start mission to GCS
        Reset terminal sequences before starting to ensure all waypoints are visited
        """
        # Reset terminal sequences before starting mission
        ProcessingService.reset_terminal_sequences_for_drone(data.drone_unique_id)

        # Start stream recording (record-only, no detect/video_analysis)
        try:
            from asgiref.sync import async_to_sync
            from stream_monitors.services.stream_monitor_services import StreamMonitorService
            async_to_sync(StreamMonitorService.start_record)(
                data.drone_unique_id,
                None,
                enable_detection=False,
                from_fe=False,
            )
        except Exception as rec_exc:
            # Do not block mission start if recording fails
            print(f"⚠️ [RECORDING] Failed to start recording for drone {data.drone_unique_id}: {rec_exc}")
        
        def make_drone_request():
            """Function to run in separate thread"""
            try:
                # Convert schema to dict for JSON serialization
                payload = {
                    "UniqueId": data.drone_unique_id
                }
                
                print(f"📤 [API_REQUEST] Sending mission to {DRONE_API_URL}/api/drone/mission-v2/start")
                print(f"📋 [API_REQUEST] Payload: {payload}")
                
                try:
                    headers = get_gcs_api_headers()
                    response = requests.post(f"{DRONE_API_URL}/api/drone/mission-v2/start", json=payload, headers=headers, timeout=30)
                    response.raise_for_status()  # Raise an exception for bad status codes
                except requests.exceptions.ConnectionError as e:
                    print(f"🔌 [API_REQUEST] Connection error for {data.drone_unique_id}: {str(e)}")
                    print(f"⚠️ [API_REQUEST] Cannot connect to drone API server at {DRONE_API_URL}")
                    print(f"📝 [API_REQUEST] Drone mission start command logged but not sent to physical drone")
                    return False
                except requests.exceptions.Timeout as e:
                    print(f"⏰ [API_REQUEST] Timeout error for {data.drone_unique_id}: {str(e)}")
                    print(f"⚠️ [API_REQUEST] Drone API server at {DRONE_API_URL} is not responding")
                    return False
                except requests.exceptions.HTTPError as e:
                    print(f"❌ [API_REQUEST] HTTP error for {data.drone_unique_id}: {str(e)}")
                    print(f"📊 [API_REQUEST] Response status: {response.status_code}")
                    print(f"📊 [API_REQUEST] Response content: {response.text}")
                    return False
                response_data = response.json()
                print(f"✅ [API_REQUEST] Mission API success for {data.drone_unique_id}")
                print(f"📊 [API_REQUEST] Response: {response_data}")
                return True
                 
            except requests.exceptions.ConnectionError as e:
                print(f"🔌 [API_REQUEST] Connection error for {data.drone_unique_id}: {str(e)}")
                print(f"⚠️ [API_REQUEST] Cannot connect to drone API server at {DRONE_API_URL}")
                print(f"📝 [API_REQUEST] Drone mission command logged but not sent to physical drone")
                return False
            except requests.exceptions.Timeout as e:
                print(f"⏰ [API_REQUEST] Timeout error for {data.drone_unique_id}: {str(e)}")
                print(f"⚠️ [API_REQUEST] Request timed out after 30 seconds")
                return False
            except requests.exceptions.RequestException as e:
                print(f"❌ [API_REQUEST] Request error for {data.drone_unique_id}: {str(e)}")
                print(f"💥 [API_REQUEST] Failed to start drone mission")
                return False
            except Exception as e:
                print(f"💥 [API_REQUEST] Unexpected error for {data.drone_unique_id}: {str(e)}")
                return False
        
        try:
            if with_thread:
                print(f"🧵 [START_MISSION] Starting mission to drone {data.drone_unique_id}")
                drone_thread = threading.Thread(target=make_drone_request, daemon=True)
                drone_thread.start()
                print(f"🚀 [START_MISSION] Drone mission for {data.drone_unique_id} started in background thread")
                return True
            else:
                print(f"🧵 [START_MISSION] Starting mission to drone {data.drone_unique_id}")
                result = make_drone_request()
                print(f"✅ [START_MISSION] Mission started to drone {data.drone_unique_id}")
                return result
            return result
             
        except Exception as e:
            print(f"❌ [START_MISSION] Error starting mission to drone {data.drone_unique_id}: {str(e)}")
            return False
        
    @staticmethod
    def check_operation_is_completed(in_transit_operation: DeliveryOperation) -> bool:
        """
        Check if operation is completed
        """
        return in_transit_operation.current_status.code == "completed_order"
    
    @staticmethod
    def check_terminalseq_exists(delivery_operation: DeliveryOperation, drone: Device) -> bool:
        """
        Check if terminal sequence exists for a delivery operation
        """
        return TerminalSequence._base_manager.filter(delivery_operation=delivery_operation, drone=drone).exists()
        
    @staticmethod
    def capture_image_for_terminal_set_servo(terminal_sequence: TerminalSequence):
        """
        Capture image for a terminal sequence that has set servo command id 183
        """
        try:
            if terminal_sequence.is_special_case:
                print(f"✅ [CAPTURE_IMAGE] Terminal sequence is special case")
                # capture image
                capture_service = CaptureService()
                capture_response = capture_service.capture_image(terminal_sequence.drone.unit_id, 
                                                                 None, 
                                                                 group_code=terminal_sequence.routeterminal.group.code)
                if capture_response.success:
                    print(f"✅ [CAPTURE_IMAGE] Captured image for terminal {terminal_sequence.routeterminal.terminal.name} save to minio: {capture_response.object_path}")
                    return True
                else:
                    print(f"❌ [CAPTURE_IMAGE] Captured image for terminal {terminal_sequence.routeterminal.terminal.name} failed")
                    return False
            else:
                print(f"❌ [CAPTURE_IMAGE] Terminal sequence is not special case or command line is not found")
                return False
        except Exception as e:
            print(f"❌ [CAPTURE_IMAGE] Error capturing image for terminal {terminal_sequence.routeterminal.terminal.name}: {str(e)}")
            return False
        
    @staticmethod
    def check_seq_terminal_and_update_drone_status_is_available(in_transit_operation, 
                                                                match_terminal: Terminal, 
                                                                drone: Device,
                                                                consecutive_terminals=None):
        """
        Check if sequence terminal and update drone status is available
        """
        terminal_sequences = TerminalSequence.get_all_terminals_in_sequence(in_transit_operation, drone).order_by('sequence_order')
        
        is_complete = match_terminal == terminal_sequences.last().routeterminal.terminal
        print("🔍 [TERMINAL_MATCH] last terminal sequence id: ", terminal_sequences.last().id)
        
        if consecutive_terminals:
            for terminal_sequence in consecutive_terminals:
                if terminal_sequences.last().id == terminal_sequence.id:
                    is_complete = True
                
        if is_complete:
            # Update this drone's status to available
            drone.status = DeviceStatus._base_manager.get(code="available")
            drone.save()
            
    
    @staticmethod
    @transaction.atomic
    def update_delivery_operation_status_by_drone(in_transit_operation: DeliveryOperation, 
                                                  drone: Device, 
                                                  lat_float: float, 
                                                  long_float: float):
        # get in transit operation route
        route = in_transit_operation.route
        order_items = ProcessingRepository.get_order_items_by_order(in_transit_operation.order)
        
        print(f"🔧 [ORDER_ASSIGNMENT] Route: {route.id if route else 'None'}")
        print(f"🔧 [ORDER_ASSIGNMENT] Order items count: {len(order_items)}")
        print(f"🔧 [ORDER_ASSIGNMENT] Order items: {[item.code for item in order_items]}")
        
        # Check order assignment by each item
        for order_item in order_items:
            order_assignment = ProcessingRepository.get_order_assignments_by_order_item(order_item)
            if order_assignment is None:
                print(f"🔧 [ORDER_ASSIGNMENT] Creating assignment for {order_item.code} with drone {drone.unit_id}")
                order_assignment = ProcessingRepository.create_order_assignment(order_item, drone, route)
                print(f"✅ [ORDER_ASSIGNMENT] Created assignment ID: {order_assignment.id}")
            else:
                print(f"✅ [ORDER_ASSIGNMENT] Found existing assignment for {order_item.code}: ID {order_assignment.id}, drone: {order_assignment.device.unit_id if order_assignment.device else 'None'}")
        
        # Ensure terminal sequence exists for this delivery operation
        # create_terminal_sequence_for_delivery uses get_or_create internally, so it's safe to call multiple times
        # This prevents race conditions when multiple requests arrive simultaneously
        print(f"🚨 [TERMINAL_SEQUENCE] Ensuring sequence exists for operation: {in_transit_operation.id}")
        from delivery.models import TerminalSequence
        # Quick check to avoid unnecessary call if sequence already exists
        terminal_sequence_exists = TerminalSequence._base_manager.filter(
            delivery_operation=in_transit_operation, 
            drone=drone
        ).exists()
        if not terminal_sequence_exists:
            print(f"🚨 [TERMINAL_SEQUENCE] Creating new sequence for drone {drone.unit_id}")
            ProcessingService.create_terminal_sequence_for_delivery(in_transit_operation, drone)   
            print(f"✅ [TERMINAL_SEQUENCE] Created sequence for drone {drone.unit_id}")
        else:
            print(f"✅ [TERMINAL_SEQUENCE] Using existing sequence for drone {drone.unit_id}")
        
        
        # get all terminals of route
        terminals = ProcessingRepository.get_terminals_by_route_id(route)
        print(f"🗺️ [ROUTE_TERMINALS] Loading terminals for route {route.id}")
        print(f"🗺️ [ROUTE_TERMINALS] Found {len(terminals)} terminals:")
        for i, terminal in enumerate(terminals):
            print(f"🗺️ [ROUTE_TERMINALS] [{i+1}] {terminal.name} (ID:{terminal.id}) - ({terminal.latitude}, {terminal.longitude})")
            
        # Debug input data
        print(f"📍 [DRONE_POSITION] Drone {drone.unit_id} coordinates: ({lat_float}, {long_float})")
        print(f"📍 [DRONE_POSITION] Looking for terminal match within 8m radius")
        
        # Validate terminals data
        validation_result = ProcessingService.validate_terminals_data(terminals)
        print(f"🔍 [TERMINAL_MATCH] Terminal validation: {validation_result['valid_terminals']}/{validation_result['total_terminals']} valid")
        if validation_result['invalid_terminals'] > 0:
            print(f"⚠️ [TERMINAL_MATCH] Found {validation_result['invalid_terminals']} invalid terminals!")
            for terminal_info in validation_result['terminal_details']:
                if not terminal_info['is_valid']:
                    print(f"⚠️ [TERMINAL_MATCH] Terminal {terminal_info['terminal_id']}: lat={terminal_info['latitude']}, lon={terminal_info['longitude']}")
        
        # Use the new sequence-based terminal matching
        print(f"🎯 [SEQUENCE_MATCH] Starting sequence-based terminal matching...")
        terminal_sequence, match_terminal, distance, consecutive_terminals = ProcessingService.find_correct_terminal_by_sequence(
            lat_float, long_float, in_transit_operation, drone, max_distance_meters=8.0
        )
        
        if terminal_sequence:
            print(f"🎯 [SEQUENCE_MATCH] Found sequence: order={terminal_sequence.sequence_order}, terminal={terminal_sequence.routeterminal.terminal.name}")
            print(f"🎯 [SEQUENCE_MATCH] Sequence visited: {terminal_sequence.is_visited}")
        else:
            print(f"🎯 [SEQUENCE_MATCH] No terminal sequence found")
        
        print(f"🚨 [TERMINAL_MATCH] Order: {in_transit_operation.order.order_code}")
        print(f"🚨 [TERMINAL_MATCH] Drone: {drone.unit_id}")
        print(f"🚨 [TERMINAL_MATCH] Terminal matching: {match_terminal}, distance: {distance}")
        print(f"🚨 [TERMINAL_MATCH] Drone packages: {[item.order_item.code for item in ProcessingRepository.get_operation_items_by_operation_and_drone(in_transit_operation, drone)]}")
        
        if match_terminal:
            # check if operation is completed
            is_operation_completed = ProcessingService.check_operation_is_completed(in_transit_operation)
            if is_operation_completed:
                print(f"🔍 [TERMINAL_MATCH] Operation is completed")
                ProcessingService.check_seq_terminal_and_update_drone_status_is_available(in_transit_operation, 
                                                                                          match_terminal, 
                                                                                          drone,
                                                                                          consecutive_terminals)
                print(f"✅ [TERMINAL_MATCH] Drone status set to 'available'")
                return None
                
            print(f"✅ [TERMINAL_MATCH] Drone is {distance:.2f}m from terminal {match_terminal} (Sequence: {terminal_sequence.sequence_order}) - ACCEPTED")
            
            # Note: Terminal already marked as visited in find_correct_terminal_by_sequence
            print(f"✅ [TERMINAL_MATCH] Terminal {match_terminal} already marked as visited in sequence")
            
            operation_items = ProcessingRepository.get_operation_items_by_operation_and_drone(in_transit_operation, drone)
            
            print(f"🔍 [TERMINAL_MATCH] operation_items: {operation_items.count()}")
            
            # Update operation items status for ALL consecutive terminals that were visited
            if consecutive_terminals:
                print(f"📦 [BATCH_UPDATE] Updating operation items for {len(consecutive_terminals)} consecutive terminals")
                for terminal_seq in consecutive_terminals:
                    terminal = terminal_seq.routeterminal.terminal
                    print(f"📦 [BATCH_UPDATE] Processing terminal {terminal.id} (Order: {terminal_seq.sequence_order})")
                    ProcessingService._update_operation_items_status(operation_items, terminal, terminal_seq, lat_float, long_float)
            else:
                # Fallback: Update for the first terminal only
                print(f"📦 [BATCH_UPDATE] No consecutive terminals found, updating for first terminal only")
                ProcessingService._update_operation_items_status(operation_items, match_terminal, terminal_sequence, lat_float, long_float)
            
            print(f"🔍 [TERMINAL_MATCH] updated operation_items")
            
            # Check if delivery is complete based on terminal type
            is_delivery_complete = ProcessingService._check_delivery_completion(
                in_transit_operation,
                match_terminal,
                terminals,
                consecutive_terminals
            )
            print(f"🔍 [TERMINAL_MATCH] is_delivery_complete: {is_delivery_complete}")
            if is_delivery_complete:
                is_drone_available = ProcessingService.check_is_delivery_to_door(match_terminal, 
                                                                                 terminals,
                                                                                 consecutive_terminals)
                
                print(f"🔍 [TERMINAL_MATCH] completing delivery operation")
                print(f"🔍 [TERMINAL_MATCH] is_drone_available: {is_drone_available}")
                ProcessingService._complete_delivery_operation(in_transit_operation, 
                                                               operation_items, 
                                                               drone,
                                                               is_drone_available)
                print(f"🔍 [TERMINAL_MATCH] completed delivery operation")
                        
            return None
        else:
            # Drone is not near any terminal or not the correct terminal in sequence - no action needed
            print(f"❌ [TERMINAL_MATCH] Drone {drone.unit_id} not near correct terminal in sequence")
            print(f"❌ [TERMINAL_MATCH] Drone coordinates: {lat_float}, {long_float}")
            print(f"❌ [TERMINAL_MATCH] Available terminals: {[f'{t.name}({t.latitude},{t.longitude})' for t in terminals[:3]]}")  # Show first 3 terminals
            return None

    
    @staticmethod
    def get_completed_last_terminal_of_order(in_transit_operation: DeliveryOperation, 
                                             terminals: List[Terminal]):
        order = in_transit_operation.order
        delivery_point_terminal = order.delivery_terminal
        if delivery_point_terminal:
            return delivery_point_terminal
        else:
            return terminals[-1]
        
    @staticmethod
    def check_is_delivery_to_door(match_terminal: Terminal, 
                                  terminals: List[Terminal],
                                  consecutive_terminals=None):
        
        if consecutive_terminals:
            for terminal_sequence in consecutive_terminals:
                route_terminal = terminal_sequence.routeterminal
                if route_terminal and route_terminal.terminal_id == terminals[-1].id:
                    print(f"🔍 [TERMINAL_MATCH] consecutive_terminals: {terminal_sequence.routeterminal.terminal.id}")
                    print(f"🔍 [TERMINAL_MATCH] terminals: {terminals[-1].id}")
                    return True
                
        print(f"🔍 [TERMINAL_MATCH] match_terminal: {match_terminal.id}")
        print(f"🔍 [TERMINAL_MATCH] terminals: {terminals[-1].id}")
        if match_terminal == terminals[-1]:
            return True
        else:
            return False
        
    
    @staticmethod
    @transaction.atomic
    def update_delivery_status(drone_uid: str, lat: float, long: float):
        """
        Update the delivery status of a drone
        """
        # call api f"{DRONE_API_URL}/api/drone/update-delivery-status" to update delivery status
        drone = ProcessingRepository.get_drone_by_unique_id(drone_uid)
        
        # Check if drone exists
        if drone is None:
            raise ValueError(f"Drone with unique ID {drone_uid} not found")
        
        print(f"lat: {lat}, long: {long}")
        try:
            lat_float = float(lat)
            long_float = float(long)
        except (ValueError, TypeError):
            print(f"Invalid lat/long values: lat={lat}, long={long}")
            return None
        print(f"lat_float: {lat_float}, long_float: {long_float}")

        # get in transit operation by drone uid
        all_in_transit_operation = ProcessingRepository.get_in_transit_operation_by_drone_uid(drone_uid)
        
        print(f"📡 [API_CALL] Drone {drone_uid} at coordinates ({lat_float}, {long_float})")
        print(f"📡 [API_CALL] Found {len(all_in_transit_operation)} in-transit operations")
        
        for in_transit_operation in all_in_transit_operation:
            print(f"📡 [API_CALL] Processing operation: {in_transit_operation.order.order_code}")
            ProcessingService.update_delivery_operation_status_by_drone(in_transit_operation, drone, lat_float, long_float)
            
        return None
        


    @staticmethod
    def get_delivery_for_etri():
        """
        Get delivery operations QuerySet for ETRI with mapped status names
        Returns QuerySet to support dynamic search and sorting
        Uses dynamic status mapping if available, otherwise falls back to ETRI-specific mapping
        
        Searchable fields:
        - order__order_code: Order code
        - order__recipient_name: Recipient name
        - order__recipient_phone: Recipient phone
        - current_status__name: Status name
        - mapped_status: Mapped status for ETRI
        - order__recipient_address__full_address: Delivery address
        """
        from django.db.models import Case, When, CharField, Value, Count
        from core.middleware.refresh_token import get_current_request
        from delivery.services.status_mapping_service import StatusMappingService
        
        request = get_current_request()
        language = request.user.language.code if request.user.language else 'en'
        
        # Get dynamic mapping annotations from StatusMappingService for DeliveryOperation context
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')
        
        # ETRI-specific fallback mapping dictionary for when no custom mapping exists
        STATUS_MAPPING = {
            # Primary status mappings using existing codes
            'delivered': 'Delivery Completed' if language == 'en' else '배송완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',  # Status 0
            'cancelled': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',  # Status 1  
            'in_transit_processing': 'In Delivery' if language == 'en' else '배송중' if language == 'ko' else 'กำลังจัดส่ง',  # Status 2
            'receipt_cancelled': 'Receipt Cancelled' if language == 'en' else '접수취소' if language == 'ko' else 'การรับถูกยกเลิก',  # Status 5
            
            # Legacy mappings for backward compatibility
            'unverified_order': 'Receipt Completed' if language == 'en' else '접수완료' if language == 'ko' else 'ใบเสร็จสมบูรณ์',  # Maps to Status 4
            'verified_order': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',  # Maps to Status 3
            'select_route_processing': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',  # Maps to Status 3
            'select_drone_processing': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',  # Maps to Status 3
            'completed_order': 'Delivery Completed' if language == 'en' else '배송완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',  # Maps to Status 0
            'arrived_order': 'Delivery Completed' if language == 'en' else '배송완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',  # Maps to Status 0
            'returned': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',  # Maps to Status 1
        }
        
        
        # Status color mapping dictionary
        STATUS_COLOR_MAPPING = {
            'unverified_order': '#9C9D9D',
            'verified_order': '#1D9BE2',
            'select_route_processing': '#1E90FF',
            'select_drone_processing': '#4682B4',
            'in_transit_processing': '#6495ED',
            'arrived_order': '#EB7509',
            'completed_order': '#0CBA47',
            'order_due_for_returned': '#414DAD',
            'order_pending_returned': '#F0C418',
            'overdue_order': '#683DE2',
            'returned_order': '#1D9BE2',
            'processed_order': '#9C9D9D',
            'cancelled': '#EE533D',
            
        } 
        
        # Return QuerySet with comprehensive annotations for search/sort support
        return DeliveryOperation.objects.filter( 
            another_info__isnull=False,
            another_info__etri__receipt_id__isnull=False
        ).select_related(
            'order', 
            'current_status',
            'route',
            'order__recipient_address',
            'order__pickup_location',
            'order__delivery_terminal',
            'order__delivery_option'
        ).annotate(
            # Mapped status for ETRI display and search
            mapped_status=Case(
                *[When(current_status__code=code, then=Value(mapped_name)) 
                  for code, mapped_name in STATUS_MAPPING.items()],
                default=Value('Unknown'),
                output_field=CharField()
            ),
            # Mapped status color for ETRI display
            mapped_status_color=Case(
                *[When(current_status__code=code, then=Value(color)) 
                  for code, color in STATUS_COLOR_MAPPING.items()],
                default=Value('gray'),
                output_field=CharField()
            ),
            # Additional annotations for search optimization
            item_count=Count('order__items'),
            recipient_info=Case(
                When(order__recipient_name__isnull=False, 
                     then=Value('')),
                default=Value(''),
                output_field=CharField()
            ),
            order__another_info=F('order__another_info'),
            order__created_on = F('order__created_on'),
            order__sender_name=F('order__sender_name'),
            order__recipient_name=F('order__recipient_name'),
            modified_by__first_name=F('modified_by__first_name'),
            modified_by__last_name=F('modified_by__last_name'),
            order__id = F('order__id'),
        ).order_by('-modified_on')
        
    @staticmethod
    def get_etri_status_value(internal_status_code: str) -> int:
        """
        Map internal status code to ETRI status value (0-5)
        
        Args:
            internal_status_code: Internal system status code
            
        Returns:
            int: ETRI status value (0-5)
        """
        # Mapping from internal status codes to ETRI status values - Using existing codes
        STATUS_TO_ETRI_VALUE = {
            # Primary status mappings using existing codes
            'delivered': 0,             # 배송완료 - Delivery Completed
            'cancelled': 1,             # 배송취소 - Delivery Cancelled
            'in_transit_processing': 2, # 배송중 - In Delivery
            'awaiting_shipment': 3,     # 배송대기 - Waiting for Delivery
            'pending_confirmation': 4,  # 접수완료 - Receipt Completed
            'receipt_cancelled': 5,     # 접수취소 - Receipt Cancelled
            
            # Legacy status mappings
            'completed_order': 0,       # Maps to Delivery Completed
            'arrived_order': 0,         # Maps to Delivery Completed
            'returned': 1,              # Maps to Delivery Cancelled
            'select_route_processing': 3, # Maps to Waiting for Delivery
            'select_drone_processing': 3, # Maps to Waiting for Delivery
            'verified_order': 3,        # Maps to Waiting for Delivery
            'unverified_order': 4,      # Maps to Receipt Completed
        }
        
        return STATUS_TO_ETRI_VALUE.get(internal_status_code, 4)  # Default to Receipt Completed
    
    @staticmethod
    def get_etri_status_display(internal_status_code: str, language: str = 'en') -> dict:
        """
        Get ETRI status display information
        
        Args:
            internal_status_code: Internal system status code
            language: Language code ('en' or 'ko')
            
        Returns:
            dict: Contains status_value, status_name, and description
        """
        status_value = ProcessingService.get_etri_status_value(internal_status_code)
        
        # ETRI Status definitions with descriptions
        ETRI_STATUS_INFO = {
            0: {
                'name_en': 'Delivery Completed',
                'name_kr': '배송완료',
                'description_en': 'Delivery is complete (when the control system receives information that delivery is complete)',
                'description_kr': '배송이 완료된 상태 (관제시스템에서 배송을 완료했다는 정보를 받았을 때)'
            },
            1: {
                'name_en': 'Delivery Cancelled',
                'name_kr': '배송취소',
                'description_en': 'Delivery is rejected or delivery failed (reason for cancellation must also be indicated: abnormal product condition, weather, aircraft failure)',
                'description_kr': '배송이 거절된 상태 또는 배송이 실패한 상태 (취소된 이유도 같이 표시해야 함: 물품상태 이상, 날씨, 기체고장)'
            },
            2: {
                'name_en': 'In Delivery',
                'name_kr': '배송중',
                'description_en': 'Delivery is in progress (when the control system receives information that delivery has started)',
                'description_kr': '배송 중인 상태 (관제시스템에서 배송을 시작했다는 정보를 받았을 때)'
            },
            3: {
                'name_en': 'Waiting for Delivery',
                'name_kr': '배송대기',
                'description_en': 'The operator has completed the delivery acceptance process, but delivery has not yet started',
                'description_kr': '운영자가 배송 접수처리를 완료한 상태지만 아직 배송을 시작하지 않은 상태'
            },
            4: {
                'name_en': 'Receipt Completed',
                'name_kr': '접수완료',
                'description_en': 'The acceptance has been completed, but the operator has not confirmed it',
                'description_kr': '접수된 상태지만 운영자가 확인하지 않은 상태'
            },
            5: {
                'name_en': 'Receipt Cancelled',
                'name_kr': '접수취소',
                'description_en': 'The operator or the orderer cancellation of application',
                'description_kr': '운영자 또는 주문자가 접수를 취소한 상태'
            }
        }
        
        status_info = ETRI_STATUS_INFO.get(status_value, ETRI_STATUS_INFO[4])  # Default to Receipt Completed
        
        return {
            'status_value': status_value,
            'status_name': status_info[f'name_{language}'] if language == 'ko' else status_info['name_en'],
            'description': status_info[f'description_{language}'] if language == 'ko' else status_info['description_en']
        }
    
    @staticmethod
    def get_drone_position_only(unique_id: str) -> Dict[str, Any]:
        """
        Get ONLY drone position (GPS coordinates) for performance optimization.
        This is much faster than get_drone_telemetry_by_unique_id() which fetches
        all telemetry data including IMU, vibration, temperature, etc.
        
        Args:
            unique_id: Unique ID of the drone

        Returns:
            Dictionary containing ONLY position data: {"latitude": float, "longitude": float}
        """
        try:
            # OPTIMIZATION: Add timeout and connection pooling for faster response
            import time
            start_time = time.time()
            
            # Get the latest drone log for the given unique_id
            position_data = opensearch_service.search_drone_logs_by_unique_id(
                unique_id=unique_id,
                msg_type="GLOBAL_POSITION_INT",
                size=1,
                sort_order="desc"
            )
            
            api_time = (time.time() - start_time) * 1000
            if api_time > 500:  # Log slow API calls
                logger.warning(f"Slow API call for drone {unique_id}: {api_time:.2f}ms")
            
            if position_data.get('hits', {}).get('hits', []):
                source = position_data['hits']['hits'][0]['_source']
                return {
                    "latitude": source.get('latitude', 0),
                    "longitude": source.get('longitude', 0)
                }
            return {
                "latitude": 0,
                "longitude": 0
            }
        except Exception as e:
            logger.error(f"Failed to get drone position for {unique_id}: {str(e)}")
            return {
                "latitude": 0,
                "longitude": 0
            }

    @staticmethod
    def calculate_distance_between_coordinates(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the distance between two GPS coordinates using Haversine formula.
        
        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point  
            lat2: Latitude of second point
            lon2: Longitude of second point
            
        Returns:
            Distance in meters between the two points
        """
        # Earth's radius in meters
        R = 6371000
        
        # Convert to radians
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        # Haversine formula
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def is_drone_near_terminal(drone_lat: float, drone_lon: float, terminal_lat: float, terminal_lon: float, max_distance_meters: float = 2.0) -> bool:
        """
        Check if drone position is within specified distance of terminal position.
        
        Args:
            drone_lat: Drone latitude
            drone_lon: Drone longitude
            terminal_lat: Terminal latitude
            terminal_lon: Terminal longitude
            max_distance_meters: Maximum acceptable distance in meters (default: 2.0)
            
        Returns:
            True if drone is within max_distance_meters of terminal, False otherwise
        """
        try:
            # Use the improved radius check method
            is_near = ProcessingService.is_within_radius(
                terminal_lat, terminal_lon, drone_lat, drone_lon, max_distance_meters
            )
            
            # Calculate distance for logging
            distance = ProcessingService.calculate_distance_between_coordinates(
                drone_lat, drone_lon, terminal_lat, terminal_lon
            )
            
            # Log for debugging
            if is_near:
                logger.info(f"Drone at ({drone_lat}, {drone_lon}) is {distance:.2f}m from terminal at ({terminal_lat}, {terminal_lon}) - ACCEPTED")
            else:
                logger.debug(f"Drone at ({drone_lat}, {drone_lon}) is {distance:.2f}m from terminal at ({terminal_lat}, {terminal_lon}) - REJECTED")
            
            return is_near
            
        except Exception as e:
            logger.error(f"Error calculating distance between drone and terminal: {str(e)}")
            return False

    @staticmethod
    def find_nearest_terminal(drone_lat: float, drone_lon: float, terminals: list, max_distance_meters: float = 2.0) -> tuple:
        """
        Find the nearest terminal within specified distance from drone position.
        If multiple terminals are at the same distance, returns the first one found.
        
        Args:
            drone_lat: Drone latitude
            drone_lon: Drone longitude
            terminals: List of terminal objects with latitude and longitude attributes
            max_distance_meters: Maximum acceptable distance in meters (default: 2.0)
            
        Returns:
            Tuple of (terminal_object, distance_meters) if found, (None, None) if not found
        """
        nearest_terminal = None
        min_distance = float('inf')
        
        print(f"🔍 [FIND_NEAREST] Drone position: ({drone_lat}, {drone_lon})")
        print(f"🔍 [FIND_NEAREST] Max distance: {max_distance_meters}m")
        print(f"🔍 [FIND_NEAREST] Number of terminals: {len(terminals)}")
        
        for i, terminal in enumerate(terminals):
            try:
                # Extract terminal coordinates
                terminal_lat = float(terminal.latitude) if hasattr(terminal, 'latitude') else None
                terminal_lon = float(terminal.longitude) if hasattr(terminal, 'longitude') else None
                
                print(f"🔍 [FIND_NEAREST] Terminal {i+1}: lat={terminal_lat}, lon={terminal_lon}")
                
                if terminal_lat is None or terminal_lon is None:
                    print(f"⚠️ [FIND_NEAREST] Terminal {i+1} has invalid coordinates")
                    continue
                
                # Calculate distance
                distance = ProcessingService.calculate_distance_between_coordinates(
                    drone_lat, drone_lon, terminal_lat, terminal_lon
                )
                
                print(f"🔍 [FIND_NEAREST] Terminal {i+1} distance: {distance:.2f}m")
                
                # Check if this terminal is closer and within acceptable range
                if distance <= max_distance_meters and distance < min_distance:
                    min_distance = distance
                    nearest_terminal = terminal
                    print(f"✅ [FIND_NEAREST] Terminal {i+1} is new nearest: {distance:.2f}m")
                    
            except Exception as e:
                logger.error(f"Error processing terminal {terminal}: {str(e)}")
                print(f"❌ [FIND_NEAREST] Error processing terminal {i+1}: {str(e)}")
                continue
        
        if nearest_terminal:
            logger.info(f"Found nearest terminal at distance {min_distance:.2f}m")
            print(f"✅ [FIND_NEAREST] Found nearest terminal at distance {min_distance:.2f}m")
            return nearest_terminal, min_distance
        else:
            logger.debug(f"No terminal found within {max_distance_meters}m of drone position ({drone_lat}, {drone_lon})")
            print(f"❌ [FIND_NEAREST] No terminal found within {max_distance_meters}m")
            return None, None


    @staticmethod
    def find_correct_terminal_by_sequence(drone_lat: float, 
                                          drone_lon: float, 
                                          delivery_operation, 
                                          drone,
                                          max_distance_meters: float = 8.0) -> tuple:
        """
        Find the correct terminal based on sequence order and drone position.
        This handles cases where multiple terminals have the same coordinates.
        IMPROVED: Handles round trip routes with consecutive terminals at same coordinates.
        
        Args:
            drone_lat: Drone latitude
            drone_lon: Drone longitude
            delivery_operation: DeliveryOperation instance
            max_distance_meters: Maximum acceptable distance in meters (default: 8.0)
            
        Returns:
            Tuple of (terminal_sequence_object, distance_meters) if found, (None, None) if not found
        """
        from delivery.models import TerminalSequence
        
        print(f"🔍 [ROUND_TRIP_BATCH] Drone position: ({drone_lat}, {drone_lon})")
        print(f"🔍 [ROUND_TRIP_BATCH] Delivery operation: {delivery_operation.order.order_code}")
        
        # Get all terminals in sequence for this delivery operation (both visited and unvisited)
        # Use select_for_update to lock rows and prevent race conditions when multiple requests process simultaneously
        all_terminal_sequences = TerminalSequence.get_all_terminals_in_sequence(delivery_operation, drone).select_for_update().order_by('sequence_order')
        
        # Get all unvisited terminals in sequence
        unvisited_terminal_sequences = all_terminal_sequences.filter(is_visited=False)
        
        if not unvisited_terminal_sequences.exists():
            print(f"❌ [ROUND_TRIP_BATCH] No unvisited terminals in sequence")
            return None, None, None, None
        
        print(f"🔍 [ROUND_TRIP_BATCH] Found {unvisited_terminal_sequences.count()} unvisited terminals in sequence")
        
        # Get the last visited terminal to determine what the "next" terminal should be
        last_visited_sequence = all_terminal_sequences.filter(is_visited=True).order_by('-sequence_order').first()
        
        # CRITICAL FIX: Only process the NEXT terminal in sequence (first unvisited terminal)
        # This prevents marking terminals at the same coordinates when drone returns to start point
        next_terminal_sequence = unvisited_terminal_sequences.first()
        next_terminal = next_terminal_sequence.routeterminal.terminal
        next_terminal_lat = float(next_terminal.latitude)
        next_terminal_lon = float(next_terminal.longitude)
        
        # Calculate distance to the next terminal
        distance = ProcessingService.calculate_distance_between_coordinates(
            drone_lat, drone_lon, next_terminal_lat, next_terminal_lon
        )
        
        # Check if the next terminal is within max_distance_meters
        if distance > max_distance_meters:
            print(f"❌ [ROUND_TRIP_BATCH] Next terminal {next_terminal.id} (Order: {next_terminal_sequence.sequence_order}) too far: {distance:.2f}m > {max_distance_meters}m")
            return None, None, None, None
        
        print(f"✅ [ROUND_TRIP_BATCH] Next terminal {next_terminal.id} (Order: {next_terminal_sequence.sequence_order}) matches at distance {distance:.2f}m")
        
        # CRITICAL FIX: Check if there are any visited terminals with the same coordinates
        # If drone returns to a previously visited location (same coordinates), do not mark unvisited terminals
        # unless they are the actual next terminal in sequence after the last visited terminal
        if last_visited_sequence:
            # Check visited terminals with same coordinates (using float comparison for accuracy)
            visited_with_same_coords = []
            for seq in all_terminal_sequences.filter(is_visited=True):
                seq_lat = float(seq.coordinates_lat) if seq.coordinates_lat else None
                seq_lon = float(seq.coordinates_lon) if seq.coordinates_lon else None
                if seq_lat is not None and seq_lon is not None:
                    # Compare with small tolerance (0.000001 degrees ≈ 0.1 meters)
                    if abs(seq_lat - next_terminal_lat) < 0.000001 and abs(seq_lon - next_terminal_lon) < 0.000001:
                        visited_with_same_coords.append(seq)
            
            if visited_with_same_coords:
                # Check if the next terminal is actually the next one after the last visited
                expected_next_order = last_visited_sequence.sequence_order + 1
                
                if next_terminal_sequence.sequence_order != expected_next_order:
                    visited_seq_orders = [seq.sequence_order for seq in visited_with_same_coords]
                    print(f"⚠️ [ROUND_TRIP_BATCH] Found {len(visited_with_same_coords)} visited terminal(s) with same coordinates at orders: {visited_seq_orders}")
                    print(f"⚠️ [ROUND_TRIP_BATCH] Last visited order: {last_visited_sequence.sequence_order}, Expected next: {expected_next_order}")
                    print(f"⚠️ [ROUND_TRIP_BATCH] Next terminal order: {next_terminal_sequence.sequence_order}")
                    print(f"⚠️ [ROUND_TRIP_BATCH] Drone appears to have returned to previous coordinates. Rejecting to prevent false marking of terminal {next_terminal.id}.")
                    return None, None, None, None
                else:
                    print(f"✅ [ROUND_TRIP_BATCH] Next terminal is correctly sequenced (order {next_terminal_sequence.sequence_order} = expected {expected_next_order})")
        
        # Find consecutive terminals from the next terminal
        # Start with the next terminal
        consecutive_terminals = [next_terminal_sequence]
        current_sequence_order = next_terminal_sequence.sequence_order
        
        # Calculate distance to next terminal
        first_distance = distance
        print(f"🎯 [ROUND_TRIP_BATCH] Added next terminal {next_terminal.id} (Order: {next_terminal_sequence.sequence_order}) at distance {first_distance:.2f}m")
        
        # Continue from the next terminal in sequence to find consecutive terminals at same coordinates
        for terminal_seq in unvisited_terminal_sequences:
            # Skip terminals before or equal to the next terminal
            if terminal_seq.sequence_order <= current_sequence_order:
                continue
                
            terminal = terminal_seq.routeterminal.terminal
            terminal_lat = float(terminal.latitude)
            terminal_lon = float(terminal.longitude)
            
            # Calculate distance to terminal
            terminal_distance = ProcessingService.calculate_distance_between_coordinates(
                drone_lat, drone_lon, terminal_lat, terminal_lon
            )
            
            # Check if terminal is within max_distance_meters and is consecutive
            if terminal_distance <= max_distance_meters:
                # Check for consecutiveness - must be exactly next in sequence
                if terminal_seq.sequence_order == current_sequence_order + 1:
                    consecutive_terminals.append(terminal_seq)
                    current_sequence_order = terminal_seq.sequence_order
                    print(f"🎯 [ROUND_TRIP_BATCH] Added consecutive terminal {terminal.id} (Order: {terminal_seq.sequence_order}) at distance {terminal_distance:.2f}m")
                else:
                    # Not consecutive → stop
                    print(f"🛑 [ROUND_TRIP_BATCH] Terminal {terminal.id} not consecutive (Order: {terminal_seq.sequence_order}, Expected: {current_sequence_order + 1}), stopping")
                    break
            else:
                # Too far → stop
                print(f"🛑 [ROUND_TRIP_BATCH] Terminal {terminal.id} too far ({terminal_distance:.2f}m > {max_distance_meters}m), stopping")
                break
        
        # Process terminals - always mark at least the first matching terminal
        if consecutive_terminals:
            first_terminal_sequence = consecutive_terminals[0]
            
            print(f"🎯 [ROUND_TRIP_BATCH] Found {len(consecutive_terminals)} consecutive terminals")
            print(f"🎯 [ROUND_TRIP_BATCH] Terminal range: {consecutive_terminals[0].sequence_order} → {consecutive_terminals[-1].sequence_order}")
            
            # Mark ALL consecutive terminals as visited
            for terminal_seq in consecutive_terminals:
                terminal = terminal_seq.routeterminal.terminal
                terminal_seq.mark_as_visited(drone)
                print(f"✅ [ROUND_TRIP_BATCH] Marked terminal {terminal.id} (Order: {terminal_seq.sequence_order}) as visited")
                print(f"🎯 [ROUND_TRIP_BATCH] Found RouteTerminal: {terminal_seq.routeterminal.id}")
                print(f"🎯 [ROUND_TRIP_BATCH] Found Sequence: {terminal_seq.id}")
                # check if terminal sequence has set servo command id 183
                if ProcessingService.capture_image_for_terminal_set_servo(terminal_seq):
                    print(f"✅ [ROUND_TRIP_BATCH] Captured image for terminal {terminal.id}")
                else:
                    print(f"❌ [ROUND_TRIP_BATCH] Failed to capture image for terminal {terminal.id}")
            
            # Calculate distance for the first terminal
            distance = ProcessingService.calculate_distance_between_coordinates(
                drone_lat, drone_lon, 
                float(first_terminal_sequence.routeterminal.terminal.latitude),
                float(first_terminal_sequence.routeterminal.terminal.longitude)
            )
            
            return first_terminal_sequence, first_terminal_sequence.routeterminal.terminal, distance, consecutive_terminals
        
        print(f"❌ [ROUND_TRIP_BATCH] No consecutive terminals found")
        return None, None, None, None
    
    @staticmethod
    @transaction.atomic
    def mark_terminal_as_visited(terminal_sequence, drone=None, visited_terminals=None):
        """
        Mark a terminal sequence as visited by the drone.
        IMPROVED: Skip if already visited to prevent duplicate processing.
        
        Args:
            terminal_sequence: TerminalSequence instance to mark as visited
            drone: Optional drone device that visited the terminal
            visited_terminals: Set to track visited terminals to prevent infinite loops
        """
        from django.utils import timezone
        from django.db import transaction
        
        # Check if terminal is already visited
        if terminal_sequence.is_visited:
            print(f"⚠️ [VISIT_MARK] Terminal {terminal_sequence.routeterminal.terminal.id} (Order: {terminal_sequence.sequence_order}) already visited, skipping")
            return True
        
        # Initialize visited_terminals set to prevent infinite loops
        if visited_terminals is None:
            visited_terminals = set()
        
        # Prevent infinite loop by checking if terminal already processed
        terminal_id = terminal_sequence.id
        if terminal_id in visited_terminals:
            print(f"⚠️ [VISIT_MARK] Terminal {terminal_sequence.routeterminal.terminal.id} already processed, skipping to prevent infinite loop")
            return True
        
        try:
            with transaction.atomic():
                # Mark current terminal as visited
                terminal_sequence.is_visited = True
                terminal_sequence.visited_at = timezone.now()
                if drone:
                    terminal_sequence.drone = drone
                terminal_sequence.save()
                
                # Add to visited set
                visited_terminals.add(terminal_id)
                
                print(f"✅ [VISIT_MARK] Terminal {terminal_sequence.routeterminal.terminal.id} (Order: {terminal_sequence.sequence_order}) marked as visited")
                
                # Check and update next terminal sequence (special case)
                next_seq = terminal_sequence.sequence_order + 1 
                delivery_operation = terminal_sequence.delivery_operation
                
                # Get next terminal sequence
                next_terminal_sequence = ProcessingRepository.get_netx_terminal_seq_by_current_terminal_seq(next_seq, delivery_operation,drone)
                
                if next_terminal_sequence and next_terminal_sequence.is_special_case:
                    print(f"🔍 [SPECIAL_CASE] Auto-marking next special case terminal {next_terminal_sequence.routeterminal.terminal.id}")
                    # Recursive call with visited_terminals to prevent infinite loops
                    return ProcessingService.mark_terminal_as_visited(next_terminal_sequence, drone, visited_terminals)
                
                return True
                
        except Exception as e:
            print(f"❌ [VISIT_MARK] Failed to mark terminal as visited: {str(e)}")
            return False

    @staticmethod
    @transaction.atomic
    def create_terminal_sequence_for_delivery(delivery_operation, drone):
        """
        Create terminal sequence for a delivery operation based on its route.
        Uses RouteTerminal.order to determine the correct sequence.
        
        Args:
            delivery_operation: DeliveryOperation instance
            
        Returns:
            List of created TerminalSequence objects
        """
        from delivery.models import TerminalSequence
        from terminals.models import RouteTerminal
        from django.db import transaction, IntegrityError
        
        print(f"🔧 [CREATE_SEQUENCE] Creating terminal sequence for delivery: {delivery_operation.order.order_code}")
        
        try:
            with transaction.atomic():
                # Get route
                route = delivery_operation.route
                if not route:
                    print(f"❌ [CREATE_SEQUENCE] No route found for delivery operation")
                    return []
                
                # Get terminals in correct order from RouteTerminal
                route_terminals = RouteTerminal._base_manager.filter(route_id=route.id).order_by('order')
                
                if not route_terminals.exists():
                    print(f"❌ [CREATE_SEQUENCE] No terminals found for route")
                    return []
                
                print(f"🔧 [CREATE_SEQUENCE] Found {route_terminals.count()} terminals in route")
                
                # Create new sequences based on RouteTerminal order using get_or_create
                sequences = []
                # List of special case IDs that need to be marked
                special_case_ids = [183] # Set Servo command id
                
                for route_terminal in route_terminals:
                    # Check if this route terminal has special case command_line
                    is_special_case = False
                    if route_terminal.command_line:
                        # Check if any command ID in command_line matches special case IDs
                        for command_id in route_terminal.command_line.keys():
                            try:
                                if int(command_id) in special_case_ids:
                                    is_special_case = True
                                    print(f"  🔍 [SPECIAL_CASE] Found special case ID {command_id} in terminal {route_terminal.terminal.id}")
                                    break
                            except (ValueError, TypeError):
                                # Skip invalid command IDs
                                continue
                    # Use get_or_create to avoid race conditions
                    sequence, created = TerminalSequence._base_manager.get_or_create(
                        delivery_operation=delivery_operation,
                        sequence_order=route_terminal.order,
                        drone=drone,
                        routeterminal=route_terminal,
                        defaults={
                            'coordinates_lat': route_terminal.terminal.latitude,
                            'coordinates_lon': route_terminal.terminal.longitude,
                            'is_special_case': is_special_case,
                        }
                    )
                    
                    if created:
                        special_marker = " [SPECIAL CASE]" if is_special_case else ""
                        print(f"  📍 Order {route_terminal.order}: Terminal {route_terminal.terminal.id} ({route_terminal.terminal.name}) - CREATED{special_marker}")
                    else:
                        special_marker = " [SPECIAL CASE]" if is_special_case else ""
                        print(f"  📍 Order {route_terminal.order}: Terminal {route_terminal.terminal.id} ({route_terminal.terminal.name}) - ALREADY EXISTS{special_marker}")
                    
                    sequences.append(sequence)
                
                print(f"✅ [CREATE_SEQUENCE] Created {len(sequences)} terminal sequences")
                return sequences
                
        except IntegrityError as e:
            print(f"❌ [CREATE_SEQUENCE] IntegrityError: {str(e)}")
            # Try to get existing sequences if creation failed
            existing_sequences = TerminalSequence.objects.filter(delivery_operation=delivery_operation)
            if existing_sequences.exists():
                print(f"🔄 [CREATE_SEQUENCE] Using existing sequences: {existing_sequences.count()}")
                return list(existing_sequences)
            else:
                print(f"❌ [CREATE_SEQUENCE] No existing sequences found, returning empty list")
                return []
        except Exception as e:
            print(f"❌ [CREATE_SEQUENCE] Unexpected error: {str(e)}")
            return []

    
    @staticmethod
    def get_drone_positions_batch(unique_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        PERFORMANCE OPTIMIZATION: Get positions for multiple drones in a single batch query.
        This is much faster than calling get_drone_position_only() multiple times.
        """
        try:
            from delivery.services.opensearch_data import OpenSearchDataService
            opensearch_service = OpenSearchDataService()
            return opensearch_service.search_drone_positions_batch(unique_ids)
        except Exception as e:
            logger.error(f"Failed to get batch drone positions: {str(e)}")
            return {uid: {"latitude": 0, "longitude": 0} for uid in unique_ids}

    @staticmethod
    async def get_drone_positions_batch_async(unique_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        ULTIMATE PERFORMANCE: Async batch query for maximum speed.
        This uses async/await to handle multiple OpenSearch requests concurrently.
        
        Args:
            unique_ids: List of drone unique IDs
            
        Returns:
            Dictionary mapping unique_id to position data
        """
        try:
            import asyncio
            import aiohttp
            from delivery.services.opensearch_data import OpenSearchDataService
            
            # Create async OpenSearch client
            opensearch_service = OpenSearchDataService()
            
            # Execute async batch query
            start_time = time.time()
            result = await opensearch_service.search_drone_positions_batch(unique_ids)
            batch_time = (time.time() - start_time) * 1000
            
            if batch_time > 200:  # Log slow async queries
                logger.warning(f"Slow async batch query for {len(unique_ids)} drones: {batch_time:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get async batch drone positions: {str(e)}")
            # Fallback: return empty positions
            return {uid: {"latitude": 0, "longitude": 0} for uid in unique_ids}

    @staticmethod
    def check_route_terminal_set_servo(route_terminal):
        """
        Check if route terminal has set servo command id 183
        """
        if route_terminal.command_line:
            for command_id in route_terminal.command_line.keys():
                if int(command_id) == 183:
                    return True
        return False
        

    @staticmethod
    def _update_operation_items_status(operation_items, match_terminal, terminal_seq, lat_float, long_float):
        """
        Update status for operation items when drone arrives at terminal
        Only creates delivery events for packages of the current drone
        """
        print(f"📦 [DELIVERY_EVENT] Processing {len(operation_items)} packages for terminal {match_terminal.name}")
        
        for operation_item in operation_items:
            print(f"📦 [DELIVERY_EVENT] Processing package: {operation_item.order_item.code}")
            order_assignment = ProcessingRepository.get_order_assignments_by_order_item(operation_item.order_item)
            
            if order_assignment:
                print(f"📦 [DELIVERY_EVENT] Found assignment ID: {order_assignment.id}")
                try:
                    delivery_event = ProcessingRepository.create_delivery_event(order_assignment, match_terminal, terminal_seq, lat_float, long_float)
                    print(f"✅ [DELIVERY_EVENT] Created event ID: {delivery_event.id} for package {operation_item.order_item.code}")
                    print(f"✅ [DELIVERY_EVENT] Event details: terminal={match_terminal.name}, drone={operation_item.drone.unit_id if operation_item.drone else 'unknown'}")
                except Exception as e:
                    print(f"❌ [DELIVERY_EVENT] Failed to create event for {operation_item.order_item.code}: {str(e)}")
            else:
                print(f"❌ [DELIVERY_EVENT] No order assignment found for package {operation_item.order_item.code}")
                print(f"❌ [DELIVERY_EVENT] Package drone: {operation_item.drone.unit_id if operation_item.drone else 'None'}")

    @staticmethod
    def _check_delivery_completion(
        in_transit_operation,
        match_terminal,
        terminals,
        consecutive_terminal_sequences=None
    ):
        """
        Determine whether the delivery should be marked completed.
        Handles cases where multiple terminals share the same coordinates and
        the delivery terminal sits mid-route. When consecutive terminals are
        auto-marked (due to overlapping coordinates), this ensures the actual
        delivery terminal is still considered for completion.
        """
        completed_last_terminal = ProcessingService.get_completed_last_terminal_of_order(
            in_transit_operation,
            terminals
        )
        if not completed_last_terminal:
            return False
        
        # Primary check: direct match with the terminal that triggered the update
        if match_terminal and match_terminal.id == completed_last_terminal.id:
            return True
        
        # Fallback: the delivery terminal may be part of a consecutive batch that
        # shares identical coordinates. Verify if any of those terminals is the
        # actual delivery point.
        if consecutive_terminal_sequences:
            for terminal_sequence in consecutive_terminal_sequences:
                route_terminal = terminal_sequence.routeterminal
                if route_terminal and route_terminal.terminal_id == completed_last_terminal.id:
                    return True
        
        # Final fallback: check if the delivery terminal sequence has already been
        # marked visited (e.g., from previous coordinate batches) even though the
        # current matching terminal differs.
        delivery_terminal_sequence = (
            TerminalSequence.objects.filter(
                delivery_operation=in_transit_operation,
                routeterminal__terminal=completed_last_terminal
            )
            .order_by('sequence_order')
            .first()
        )
        if delivery_terminal_sequence and delivery_terminal_sequence.is_visited:
            return True
        
        return False

    @staticmethod
    def _send_data_to_ai_analysis(device, item_code):
        """
        Send data to AI analysis
        """
        if device is None:
            raise ValueError("Device is required for AI analysis but is None")
        if not hasattr(device, 'serial_number') or device.serial_number is None:
            raise ValueError(f"Device {device} does not have a valid serial_number")
        if not hasattr(device, 'unit_id') or device.unit_id is None:
            raise ValueError(f"Device {device} does not have a valid unit_id")
        
        log_code = f"{device.serial_number}_{item_code}"
        print(f"✅ [AI_ANALYSIS] Log code: {log_code}")
        ai_analysis_link = f"{settings.AI_ANALYSIS_URL}/ingest/batch"
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        drone_telemetry = ProcessingService.get_drone_telemetry_by_unique_id(device.unit_id)
        # print(f"✅ [AI_ANALYSIS] Drone telemetry: {drone_telemetry}")
        payload = {
            "items": [
                {
                    "id": log_code,
                    "xacc_RAW_IMU": drone_telemetry.get('telemetry').get('axes').get('x'),
                    "yacc_RAW_IMU": drone_telemetry.get('telemetry').get('axes').get('y'),
                    "zacc_RAW_IMU": drone_telemetry.get('telemetry').get('axes').get('z'),
                    "vx_GLOBAL_POSITION_INT": drone_telemetry.get('position').get('latitude'),
                    "vy_GLOBAL_POSITION_INT": drone_telemetry.get('position').get('longitude'),
                    "vibration_x_VIBRATION": drone_telemetry.get('telemetry').get('vibration').get('x'),
                    "vibration_y_VIBRATION": drone_telemetry.get('telemetry').get('vibration').get('y'),
                    "vibration_z_VIBRATION": drone_telemetry.get('telemetry').get('vibration').get('z'),
                    "airspeed_VFR_HUD": drone_telemetry.get('telemetry').get('wind_speed'),
                    "voltages1_BATTERY_STATUS": drone_telemetry.get('telemetry').get('battery_percent')
                }
            ]
        }
        print(f"✅ [AI_ANALYSIS] Payload: {payload}")
        response = requests.post(
            ai_analysis_link, 
            data=json.dumps(payload),
            headers=headers,
        )
        print(f"✅ [AI_ANALYSIS] Response: {response}")

        drone_payload = {
            "items": [
                {
                    "id": device.serial_number,
                    "xacc_RAW_IMU": drone_telemetry.get('telemetry').get('axes').get('x'),
                    "yacc_RAW_IMU": drone_telemetry.get('telemetry').get('axes').get('y'),
                    "zacc_RAW_IMU": drone_telemetry.get('telemetry').get('axes').get('z'),
                    "vx_GLOBAL_POSITION_INT": drone_telemetry.get('position').get('latitude'),
                    "vy_GLOBAL_POSITION_INT": drone_telemetry.get('position').get('longitude'),
                    "vibration_x_VIBRATION": drone_telemetry.get('telemetry').get('vibration').get('x'),
                    "vibration_y_VIBRATION": drone_telemetry.get('telemetry').get('vibration').get('y'),
                    "vibration_z_VIBRATION": drone_telemetry.get('telemetry').get('vibration').get('z'),
                    "airspeed_VFR_HUD": drone_telemetry.get('telemetry').get('wind_speed'),
                    "voltages1_BATTERY_STATUS": drone_telemetry.get('telemetry').get('battery_percent')
                }
            ]
        }
        print(f"✅ [AI_ANALYSIS] Drone payload: {drone_payload}")
        drone_response = requests.post(
            ai_analysis_link, 
            data=json.dumps(drone_payload),
            headers=headers,
        )
        print(f"✅ [AI_ANALYSIS] Drone Response: {drone_response}")
        anomaly_prediction = FlightLogService.get_flight_log_with_anomaly_prediction(log_code)
        return anomaly_prediction

    @staticmethod
    @transaction.atomic
    def _complete_delivery_operation(in_transit_operation, 
                                     operation_items, 
                                     drone, 
                                     is_confirmed: bool = False):
        """
        Complete the delivery operation by updating all statuses and creating history
        """
        try: 
            # Validate drone is not None before proceeding
            if drone is None:
                raise ValueError("Drone is required to complete delivery operation but is None")
            
            # Update all operation items arrival status
            for operation_item in operation_items:
                ConfirmationRepository.update_package_arrival_all_status(operation_item, True, True)
                ConfirmationRepository.add_arrived_package_delivery_history(operation_item)
                # create flight log
                order_item = operation_item.order_item
                FlightLogService.update_flight_log(order_item)
                # send data to AI analysis (only if drone is available)
                try:
                    anomaly_prediction = ProcessingService._send_data_to_ai_analysis(drone, order_item.code)
                    # update flight log with anomaly prediction
                    if anomaly_prediction:
                        FlightLogService.update_flight_log_with_anomaly_prediction(order_item, anomaly_prediction)
                except Exception as ai_exc:
                    # Log AI analysis error but don't fail the entire operation
                    logger.warning(f"Failed to send data to AI analysis: {str(ai_exc)}")
            
            # Check if all packages delivered
            is_all_packages_delivered = (
                # ConfirmationRepository.check_if_only_one_package_is_not_delivered(in_transit_operation) or
                ConfirmationRepository.check_all_packages_delivered_by_drone(in_transit_operation, drone)
            )
            
            if is_all_packages_delivered:
                # Add order history
                OrderService.create_order_history(in_transit_operation.order.id, "", "delivered")
                
                # Update delivery operation status to completed
                completed_status = ConfirmationRepository.get_delivery_status_by_code("completed_order")
                delivered_status = ConfirmationRepository.get_order_status_by_code("delivered")
                
                if completed_status:
                    ConfirmationRepository.update_delivery_operation_status(in_transit_operation, completed_status)
                    ConfirmationRepository.update_order_status(in_transit_operation, delivered_status)
                    ConfirmationRepository.add_delivered_order_delivery_history(in_transit_operation)
                    
                    if is_confirmed:
                        # Stop stream recording (record-only) BEFORE setting drone back to available
                        try:
                            from asgiref.sync import async_to_sync
                            from stream_monitors.models import StreamMonitorRecord
                            from stream_monitors.services.stream_monitor_services import StreamMonitorService

                            # Resolve group_code (required by public stop endpoint contract)
                            group_code = "default"
                            try:
                                created_by = getattr(in_transit_operation.order, "created_by", None)
                                group = getattr(getattr(created_by, "userprofilelink", None), "group", None)
                                if group and getattr(group, "code", None):
                                    group_code = group.code
                            except Exception:
                                pass

                            record = (
                                StreamMonitorRecord.objects.filter(stream_id=drone.unit_id, status="running")
                                .order_by("-created_at", "-id")
                                .first()
                            )
                            if record:
                                async_to_sync(StreamMonitorService.stop_record)(
                                    drone.unit_id,
                                    str(record.id),
                                    user=None,
                                    enable_detection=False,
                                    group_code=group_code,
                                )
                        except Exception as stop_exc:
                            print(f"⚠️ [RECORDING] Failed to stop recording for drone {drone.unit_id}: {stop_exc}")

                        # Update drone status to available after completing delivery
                        available_status = DeviceStatus._base_manager.filter(code="available").first()
                        if available_status:
                            drone.status = available_status
                            drone.save()
                            print(f"✅ [DRONE_STATUS] Delivery completed. Drone {drone.unit_id} status set to 'available'")
                        else:
                            logger.warning(f"DeviceStatus with code 'available' not found. Please run create_default_drone_status command.")
                    else:
                        # Update drone status to return after completing delivery
                        return_status = DeviceStatus._base_manager.filter(code="return").first()
                        if return_status:
                            drone.status = return_status
                            drone.save()
                            print(f"✅ [DRONE_STATUS] Delivery completed. Drone {drone.unit_id} status set to 'return' - returning to base")
                        else:
                            logger.warning(f"DeviceStatus with code 'return' not found. Please run create_default_drone_status command.")
            
        except Exception as e:
            logger.error(f"Error completing delivery operation: {str(e)}")
            # Re-raise exception so calling code can handle it properly
            raise

    @staticmethod
    def is_within_radius(lat1: float, lon1: float, lat2: float, lon2: float, radius_m: float = 2.0) -> bool:
        """
        Check if coordinates (lat2, lon2) are within radius_m meters around (lat1, lon1).
        
        Args:
            lat1: Center latitude
            lon1: Center longitude
            lat2: Target latitude
            lon2: Target longitude
            radius_m: Radius in meters (default: 2.0)
            
        Returns:
            True if target coordinates are within the specified radius
        """
        distance = ProcessingService.calculate_distance_between_coordinates(lat1, lon1, lat2, lon2)
        return distance <= radius_m

    @staticmethod
    def test_distance_calculation():
        """
        Test method to validate distance calculation logic
        """
        # Test coordinates from the provided example
        terminal_lat, terminal_lon = 37.3786112, 126.9049984
        
        # Coordinates at 2m and 3m distance
        coord_2m = (37.37862916, 126.9049984)  # Should be within 2m
        coord_3m = (37.37863814, 126.9049984)  # Should be outside 2m
        
        print("=== Testing Distance Calculation ===")
        
        # Test 2m coordinate
        distance_2m = ProcessingService.calculate_distance_between_coordinates(
            terminal_lat, terminal_lon, coord_2m[0], coord_2m[1]
        )
        is_within_2m = ProcessingService.is_within_radius(
            terminal_lat, terminal_lon, coord_2m[0], coord_2m[1], 2.0
        )
        print(f"2m coordinate: distance={distance_2m:.2f}m, within_2m={is_within_2m}")
        
        # Test 3m coordinate
        distance_3m = ProcessingService.calculate_distance_between_coordinates(
            terminal_lat, terminal_lon, coord_3m[0], coord_3m[1]
        )
        is_within_3m = ProcessingService.is_within_radius(
            terminal_lat, terminal_lon, coord_3m[0], coord_3m[1], 2.0
        )
        print(f"3m coordinate: distance={distance_3m:.2f}m, within_2m={is_within_3m}")
        
        # Test exact match
        exact_match = ProcessingService.is_within_radius(
            terminal_lat, terminal_lon, terminal_lat, terminal_lon, 2.0
        )
        print(f"Exact match: within_2m={exact_match}")
        
        print("=== Test Complete ===")

    @staticmethod
    def validate_terminals_data(terminals: list) -> dict:
        """
        Validate terminal data and return detailed information for debugging
        
        Args:
            terminals: List of terminal objects
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'total_terminals': len(terminals),
            'valid_terminals': 0,
            'invalid_terminals': 0,
            'terminals_with_coordinates': 0,
            'terminals_without_coordinates': 0,
            'terminal_details': []
        }
        
        for i, terminal in enumerate(terminals):
            terminal_info = {
                'index': i,
                'terminal_id': getattr(terminal, 'id', 'Unknown'),
                'has_latitude': hasattr(terminal, 'latitude'),
                'has_longitude': hasattr(terminal, 'longitude'),
                'latitude': getattr(terminal, 'latitude', None),
                'longitude': getattr(terminal, 'longitude', None),
                'is_valid': True
            }
            
            # Check if terminal has coordinates
            if terminal_info['has_latitude'] and terminal_info['has_longitude']:
                terminal_info['has_coordinates'] = True
                validation_result['terminals_with_coordinates'] += 1
                
                # Check if coordinates are valid numbers
                try:
                    lat = float(terminal_info['latitude'])
                    lon = float(terminal_info['longitude'])
                    terminal_info['coordinates_valid'] = True
                    validation_result['valid_terminals'] += 1
                except (ValueError, TypeError):
                    terminal_info['coordinates_valid'] = False
                    terminal_info['is_valid'] = False
                    validation_result['invalid_terminals'] += 1
            else:
                terminal_info['has_coordinates'] = False
                terminal_info['coordinates_valid'] = False
                terminal_info['is_valid'] = False
                validation_result['terminals_without_coordinates'] += 1
                validation_result['invalid_terminals'] += 1
            
            validation_result['terminal_details'].append(terminal_info)
        
        return validation_result
