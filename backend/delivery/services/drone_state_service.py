import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple

from django.db import transaction
from django.utils.translation import get_language
from devices.models import Device, DeviceStatus
from delivery.services.opensearch_data import OpenSearchDataService
from common.drone_state_constants import (
    DroneSystemStatus,
    DroneFlightMode,
    DroneState,
    DroneStatusCode,
    DRONE_STATE_THRESHOLDS,
    REQUIRED_LOG_FIELDS,
    STATE_CONDITIONS,
    DRONE_STATE_MESSAGES,
    DRONE_ERROR_MESSAGES
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DroneStateAnalyzer:
    """Analyzes and updates drone states based on OpenSearch data"""

    def __init__(self):
        """Initialize OpenSearch connection and required parameters"""
        self.opensearch_service = OpenSearchDataService()


    def get_localized_message(self, messages: Dict[str, Dict[str, str]], key: str = None) -> str:
        """
        Get localized message based on current language
        
        Args:
            messages: Dictionary containing messages in different languages
            key: Key for specific message (if messages is a nested dictionary)
            
        Returns:
            str: Localized message
        """
        current_lang = get_language() or 'en'
        if current_lang not in ['en', 'ko', 'vi']:
            current_lang = 'en'

        if key:
            return messages.get(key, {}).get(current_lang, messages.get(key, {}).get('en', ''))
        return messages.get(current_lang, messages.get('en', ''))

    def validate_log_data(self, log_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates the log data for required fields
        
        Args:
            log_data: Log data to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check basic required fields
        for field in REQUIRED_LOG_FIELDS["BASIC"]:
            if field not in log_data:
                error_msg = self.get_localized_message(DRONE_ERROR_MESSAGES, "VALIDATION_ERROR")
                logger.warning(f"{error_msg}: {field}")
                return False, error_msg
        return True, None

    def get_recent_logs(self, unit_id: str, hours: int = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        try:
            # First get the most recent log to use as reference
            query = {
                "bool": {
                    "filter": [
                        self.opensearch_service.create_multi_match_query("uniqueId", unit_id)
                    ]
                }
            }
            
            response = self.opensearch_service.search(
                query=query,
                size=50,  # Match the size in your query
                sort=[{"timestamp": {"order": "desc"}}]
            )
            
            hits = response.get('hits', {}).get('hits', [])
            if not hits:
                return [], None

            # Get the most recent timestamp
            latest_timestamp = hits[0]['_source'].get('timestamp')
            logger.info(f"Latest timestamp from OpenSearch (UTC): {latest_timestamp}")

            # Parse the timestamp - OpenSearch timestamps are always in UTC
            try:
                if '.' in latest_timestamp:
                    parts = latest_timestamp.split('.')
                    base = parts[0]
                    micro = parts[1].replace('Z', '')[:6]  # Ensure 6 digits microseconds
                    timestamp_str = f"{base}.{micro}Z"
                    latest_dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                else:
                    latest_dt = datetime.strptime(latest_timestamp, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            except Exception as e:
                logger.error(f"Error parsing timestamp {latest_timestamp}: {str(e)}")
                return [], None

            # Calculate time range based on the latest log timestamp (staying in UTC)
            if hours is None:
                hours = 1
            time_from = (latest_dt - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            # Now get all logs within the time range
            query = {
                "bool": {
                    "filter": [
                        self.opensearch_service.create_multi_match_query("uniqueId", unit_id),
                        {
                            "range": {
                                "timestamp": {
                                    "gte": time_from,
                                    "lte": latest_timestamp
                                }
                            }
                        }
                    ]
                }
            }
            
            logger.info(f"Querying OpenSearch for logs between {time_from} and {latest_timestamp} (UTC)")
            
            response = self.opensearch_service.search(
                query=query,
                size=50,
                sort=[{"timestamp": {"order": "desc"}}]
            )
            
            logs = [hit['_source'] for hit in response.get('hits', {}).get('hits', [])]
            if not logs:
                return [], None

            # Debug log the timestamp of first (newest) and last (oldest) record
            if logs:
                logger.info(f"Got {len(logs)} logs")
                logger.info(f"Newest log timestamp (UTC): {logs[0].get('timestamp')}")
                logger.info(f"Oldest log timestamp (UTC): {logs[-1].get('timestamp')}")

            # Initialize normalized log with default values
            normalized_log = {
                'timestamp': logs[0].get('timestamp'),
                'uniqueId': logs[0].get('uniqueId'),
                'BatteryLevel': 100,
                'SystemStatus': 'STANDBY',
                'DroneState': 'INACTIVE',
                'FlightMode': None,  # Remove default value to ensure we get the actual mode
                'CurrentMissionId': None,
                'GpsSatellites': 0,
                'GpsAccuracy': 999,
                'WindSpeed': 0,
                'VibrationX': 0,
                'VibrationY': 0,
                'VibrationZ': 0,
                'Temperature': 0,
                'Xacc': 0,
                'Yacc': 0,
                'Zacc': 0
            }

            # Process each log to update normalized data
            for log in logs:
                msg_type = log.get('msgType')
                
                if msg_type == 'SYS_STATUS':
                    normalized_log['BatteryLevel'] = log.get('batteryLevel', normalized_log['BatteryLevel'])
                
                elif msg_type == 'HEARTBEAT':
                    normalized_log['DroneState'] = log.get('droneState', normalized_log['DroneState'])
                    # Always take the flight mode from HEARTBEAT message
                    if 'flightMode' in log:
                        normalized_log['FlightMode'] = log['flightMode']
                
                elif msg_type == 'MISSION_CURRENT':
                    normalized_log['CurrentMissionId'] = log.get('currentMissionId')
                
                elif msg_type == 'GPS_RAW_INT':
                    normalized_log['GpsSatellites'] = log.get('gpsSatellites', normalized_log['GpsSatellites'])
                    normalized_log['GpsAccuracy'] = log.get('gpsAccuracy', normalized_log['GpsAccuracy'])
                
                elif msg_type == 'WIND':
                    normalized_log['WindSpeed'] = log.get('windSpeed', normalized_log['WindSpeed'])
                
                elif msg_type == 'VIBRATION':
                    normalized_log['VibrationX'] = log.get('vibrationX', normalized_log['VibrationX'])
                    normalized_log['VibrationY'] = log.get('vibrationY', normalized_log['VibrationY'])
                    normalized_log['VibrationZ'] = log.get('vibrationZ', normalized_log['VibrationZ'])
                
                elif msg_type == 'SCALED_IMU2':
                    normalized_log['Temperature'] = log.get('temperature', normalized_log['Temperature'])
                
                elif msg_type == 'RAW_IMU':
                    normalized_log['Xacc'] = log.get('xacc', normalized_log['Xacc'])
                    normalized_log['Yacc'] = log.get('yacc', normalized_log['Yacc'])
                    normalized_log['Zacc'] = log.get('zacc', normalized_log['Zacc'])

            # Set default STABILIZE mode only if no HEARTBEAT message was found
            if normalized_log['FlightMode'] is None:
                normalized_log['FlightMode'] = 'STABILIZE'

            # Debug log
            logger.info("Normalized log:")
            logger.info(f"Battery Level: {normalized_log['BatteryLevel']}%")
            logger.info(f"Current Mission: {normalized_log['CurrentMissionId']}")
            logger.info(f"Drone State: {normalized_log['DroneState']}")
            logger.info(f"Flight Mode: {normalized_log['FlightMode']}")
            logger.info(f"GPS Satellites: {normalized_log['GpsSatellites']}")
            logger.info(f"GPS Accuracy: {normalized_log['GpsAccuracy']}")
            logger.info(f"Wind Speed: {normalized_log['WindSpeed']}")

            return [normalized_log], None

        except Exception as e:
            error_msg = self.get_localized_message(DRONE_ERROR_MESSAGES, "OPENSEARCH_ERROR")
            logger.error(f"{error_msg}: {str(e)}")
            return [], error_msg

    def check_retirement_conditions(self, unit_id: str) -> bool:
        """
        Checks if a drone meets retirement conditions
        
        Args:
            unit_id: ID of the drone
            
        Returns:
            bool: True if drone should be retired
        """
        try:
            logger.info(f"🏁 Checking retirement conditions...")
            
            # Check total flight hours
            flight_hours_query = {
                "bool": {
                    "must": [
                        self.opensearch_service.create_multi_match_query("UniqueId", unit_id),
                        {"exists": {"field": "FlightHours"}}
                    ]
                }
            }
            
            aggs = {
                "total_flight_hours": {"sum": {"field": "FlightHours"}}
            }
            
            response = self.opensearch_service.search(
                query=flight_hours_query,
                size=0,
                aggs=aggs
            )
            
            total_flight_hours = response.get('aggregations', {}).get('total_flight_hours', {}).get('value', 0)
            max_flight_hours = DRONE_STATE_THRESHOLDS["MAX_FLIGHT_HOURS"]
            logger.info(f"   Total flight hours: {total_flight_hours} (max: {max_flight_hours})")
            
            if total_flight_hours > max_flight_hours:
                logger.info(f"   ❌ Flight hours exceeded: {total_flight_hours} > {max_flight_hours}")
                return True

            # Check error frequency
            error_query = {
                "bool": {
                    "must": [
                        self.opensearch_service.create_multi_match_query("UniqueId", unit_id),
                        {
                            "terms": {
                                "SystemStatus": [DroneSystemStatus.ERROR, DroneSystemStatus.CRITICAL]
                            }
                        },
                        {
                            "range": {
                                "Timestamp": {
                                    "gte": f"now-{DRONE_STATE_THRESHOLDS['ERROR_ANALYSIS_WINDOW_DAYS']}d"
                                }
                            }
                        }
                    ]
                }
            }
            
            aggs = {
                "daily_errors": {
                    "date_histogram": {
                        "field": "Timestamp",
                        "calendar_interval": "day"
                    }
                }
            }
            
            error_response = self.opensearch_service.search(
                query=error_query,
                size=0,
                aggs=aggs
            )
            
            high_error_days = sum(
                1 for bucket in error_response.get('aggregations', {}).get('daily_errors', {}).get('buckets', [])
                if bucket['doc_count'] > DRONE_STATE_THRESHOLDS["HIGH_ERROR_COUNT_PER_DAY"]
            )
            
            high_error_days_threshold = DRONE_STATE_THRESHOLDS["HIGH_ERROR_DAYS_FOR_RETIREMENT"]
            logger.info(f"   High error days: {high_error_days} (threshold: {high_error_days_threshold})")
            
            if high_error_days >= high_error_days_threshold:
                logger.info(f"   ❌ Too many high error days: {high_error_days} >= {high_error_days_threshold}")
                return True
            
            logger.info(f"   ✅ Retirement conditions not met")
            return False
            
        except Exception as e:
            logger.error(f"Error checking retirement conditions for drone {unit_id}: {str(e)}")
            return False

    def needs_maintenance(self, latest_log: Dict[str, Any], all_logs: List[Dict[str, Any]]) -> bool:
        """
        Checks if a drone needs maintenance
        
        Args:
            latest_log: Most recent log entry
            all_logs: All log entries within analysis window
            
        Returns:
            bool: True if drone needs maintenance
        """
        try:
            logger.info(f"🔧 Checking maintenance conditions...")
            
            # Check battery level
            battery_level = latest_log.get('BatteryLevel', 100)
            low_battery_threshold = DRONE_STATE_THRESHOLDS["LOW_BATTERY_THRESHOLD"]
            logger.info(f"   Battery: {battery_level}% (threshold: {low_battery_threshold}%)")
            if battery_level < low_battery_threshold:
                logger.info(f"   ❌ Battery level too low: {battery_level}% < {low_battery_threshold}%")
                return True

            # Check vibration levels
            vibration_x = latest_log.get('VibrationX', 0)
            vibration_y = latest_log.get('VibrationY', 0)
            vibration_z = latest_log.get('VibrationZ', 0)
            max_vibration = DRONE_STATE_THRESHOLDS["MAX_VIBRATION_THRESHOLD"]
            logger.info(f"   Vibration: X={vibration_x}, Y={vibration_y}, Z={vibration_z} (max: {max_vibration})")
            
            if any(v > max_vibration for v in [vibration_x, vibration_y, vibration_z]):
                logger.info(f"   ❌ Vibration levels too high")
                return True

            # Check system status
            system_status = latest_log.get('SystemStatus')
            logger.info(f"   System Status: {system_status}")
            if system_status in [DroneSystemStatus.ERROR, DroneSystemStatus.CRITICAL]:
                logger.info(f"   ❌ System status is {system_status}")
                return True

            # Check temperature
            temperature = latest_log.get('Temperature', 0)
            high_temp_threshold = DRONE_STATE_THRESHOLDS["HIGH_TEMP_THRESHOLD"]
            logger.info(f"   Temperature: {temperature}°C (threshold: {high_temp_threshold}°C)")
            if temperature > high_temp_threshold:
                logger.info(f"   ❌ Temperature too high: {temperature}°C > {high_temp_threshold}°C")
                return True

            # Check IMU anomalies
            imu_anomaly_threshold = DRONE_STATE_THRESHOLDS["IMU_ANOMALY_THRESHOLD"]
            for log in all_logs:
                if all(log.get(key) for key in ['Xacc', 'Yacc', 'Zacc']):
                    xacc, yacc, zacc = log['Xacc'], log['Yacc'], log['Zacc']
                    if any(abs(acc) > imu_anomaly_threshold for acc in [xacc, yacc, zacc]):
                        logger.info(f"   ❌ IMU anomaly detected: X={xacc}, Y={yacc}, Z={zacc}")
                        return True

            # Check consecutive errors
            consecutive_errors = 0
            max_consecutive_errors = DRONE_STATE_THRESHOLDS["MAX_CONSECUTIVE_ERRORS"]
            for log in all_logs:
                if log.get('SystemStatus') in [DroneSystemStatus.ERROR, DroneSystemStatus.CRITICAL]:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.info(f"   ❌ Too many consecutive errors: {consecutive_errors} >= {max_consecutive_errors}")
                        return True
                else:
                    consecutive_errors = 0

            logger.info(f"   ✅ All maintenance checks passed")
            return False
        except Exception as e:
            logger.error(f"Error checking maintenance needs: {str(e)}")
            return True

    def is_on_mission(self, latest_log: Dict[str, Any]) -> bool:
        """
        Checks if a drone is currently on a mission
        
        Args:
            latest_log: Most recent log entry
            
        Returns:
            bool: True if drone is on mission
        """
        logger.info(f"🎯 Checking mission status...")
        
        current_mission_id = latest_log.get('CurrentMissionId')
        drone_state = latest_log.get('DroneState')
        flight_mode = latest_log.get('FlightMode')
        
        logger.info(f"   Current Mission ID: {current_mission_id}")
        logger.info(f"   Drone State: {drone_state}")
        logger.info(f"   Flight Mode: {flight_mode}")
        
        # Check if mission ID is greater than 0 (not 0, "0", None, or empty)
        has_mission = (
            current_mission_id is not None and 
            current_mission_id != 0 and 
            current_mission_id != "0" and 
            str(current_mission_id).strip() != ""
        )
        is_active = drone_state == DroneState.ACTIVE
        is_auto_mode = flight_mode == DroneFlightMode.AUTO
        
        logger.info(f"   Has mission: {has_mission}")
        logger.info(f"   Is active: {is_active}")
        logger.info(f"   Is auto mode: {is_auto_mode}")
        
        is_on_mission = has_mission and (is_active or is_auto_mode)
        
        if is_on_mission:
            logger.info(f"   ✅ Drone is on mission")
        else:
            logger.info(f"   ❌ Drone is not on mission")
            
        return is_on_mission

    def is_available(self, latest_log: Dict[str, Any]) -> bool:
        """
        Checks if a drone is available for missions
        
        Args:
            latest_log: Most recent log entry
            
        Returns:
            bool: True if drone is available
        """
        logger.info(f"✅ Checking availability conditions...")
        
        # Check battery
        battery_level = latest_log.get('BatteryLevel', 0)
        min_battery = DRONE_STATE_THRESHOLDS["MIN_BATTERY_FOR_MISSION"]
        battery_ok = battery_level > min_battery
        logger.info(f"   Battery: {battery_level}% > {min_battery}% = {battery_ok}")

        # Check current mission
        current_mission = latest_log.get('CurrentMissionId')
        has_no_mission = not current_mission or current_mission == "0" or current_mission == 0
        logger.info(f"   Mission: No current mission = {has_no_mission} (CurrentMissionId: {current_mission})")

        # Check system status
        system_status = latest_log.get('SystemStatus')
        system_ok = system_status not in [DroneSystemStatus.ERROR, DroneSystemStatus.CRITICAL]
        logger.info(f"   System Status: {system_status} not in [ERROR, CRITICAL] = {system_ok}")

        # Check GPS satellites
        gps_sats = latest_log.get('GpsSatellites', 0)
        min_gps_sats = DRONE_STATE_THRESHOLDS["MIN_GPS_SATELLITES"]
        gps_sats_ok = gps_sats >= min_gps_sats
        logger.info(f"   GPS Satellites: {gps_sats} >= {min_gps_sats} = {gps_sats_ok}")

        # Check GPS accuracy
        gps_accuracy = latest_log.get('GpsAccuracy', 999)
        max_gps_accuracy = DRONE_STATE_THRESHOLDS["MIN_GPS_ACCURACY"]
        gps_accuracy_ok = gps_accuracy <= max_gps_accuracy
        logger.info(f"   GPS Accuracy: {gps_accuracy} <= {max_gps_accuracy} = {gps_accuracy_ok}")

        # Check wind speed
        wind_speed = latest_log.get('WindSpeed', 0)
        max_wind_speed = DRONE_STATE_THRESHOLDS["MAX_WIND_SPEED"]
        wind_ok = wind_speed <= max_wind_speed
        logger.info(f"   Wind Speed: {wind_speed} <= {max_wind_speed} = {wind_ok}")

        # Final result
        is_available = all([
            battery_ok,
            has_no_mission,
            system_ok,
            gps_sats_ok,
            gps_accuracy_ok,
            wind_ok
        ])
        
        if is_available:
            logger.info(f"   ✅ All availability conditions met")
        else:
            logger.info(f"   ❌ Availability conditions not met:")
            if not battery_ok:
                logger.info(f"      - Battery level too low: {battery_level}% <= {min_battery}%")
            if not has_no_mission:
                logger.info(f"      - Has ongoing mission: {current_mission}")
            if not system_ok:
                logger.info(f"      - System status error: {system_status}")
            if not gps_sats_ok:
                logger.info(f"      - Not enough GPS satellites: {gps_sats} < {min_gps_sats}")
            if not gps_accuracy_ok:
                logger.info(f"      - GPS accuracy not good enough: {gps_accuracy} > {max_gps_accuracy}")
            if not wind_ok:
                logger.info(f"      - Wind speed too high: {wind_speed} > {max_wind_speed}")

        return is_available

    @transaction.atomic
    def analyze_and_update_drone_state(self, unit_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Analyzes and updates drone state
        
        Args:
            unit_id: ID of the drone to analyze
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (state_code, status_message)
        """
        try:
            logger.info(f"=== Starting drone state analysis for {unit_id} ===")
            
            # Get device from database
            try:
                device = Device.objects.get(unit_id=unit_id)
            except Device.DoesNotExist:
                error_msg = self.get_localized_message(DRONE_ERROR_MESSAGES, "DEVICE_NOT_FOUND")
                logger.error(f"{error_msg}: {unit_id}")
                return None, error_msg

            # Get recent logs
            logs, error_msg = self.get_recent_logs(unit_id)
            if error_msg:
                return None, error_msg
            if not logs:
                # Update to inactive if no logs
                logger.info(f"❌ No logs found for drone {unit_id} - Setting to INACTIVE")
                inactive_status = DeviceStatus.objects.get(code=DroneStatusCode.INACTIVE)
                device.status = inactive_status
                device.save()
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.INACTIVE])
                logger.info(f"=== Drone {unit_id} state analysis completed: INACTIVE (no logs) ===")
                return DroneStatusCode.INACTIVE, status_msg

            latest_log = logs[0]
            
            # Parse timestamp with error handling - Always work in UTC
            try:
                timestamp_str = latest_log['timestamp']
                if '.' in timestamp_str:
                    parts = timestamp_str.split('.')
                    base = parts[0]
                    micro = parts[1].replace('Z', '')[:6]  # Ensure 6 digits microseconds
                    timestamp_str = f"{base}.{micro}Z"
                    last_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                else:
                    last_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                
                # Get current time in UTC
                current_time = datetime.now(timezone.utc)
                
                logger.info(f"📅 Last log timestamp (UTC): {last_timestamp}")
                logger.info(f"🕐 Current time (UTC): {current_time}")
                
            except Exception as e:
                logger.error(f"Error parsing timestamp {latest_log.get('timestamp')}: {str(e)}")
                # Use current time as fallback, ensuring UTC
                current_time = datetime.now(timezone.utc)
                last_timestamp = current_time

            # Log current drone data for analysis
            logger.info(f"📊 Current drone data:")
            logger.info(f"   Battery: {latest_log.get('BatteryLevel', 'N/A')}%")
            logger.info(f"   System Status: {latest_log.get('SystemStatus', 'N/A')}")
            logger.info(f"   Drone State: {latest_log.get('DroneState', 'N/A')}")
            logger.info(f"   Flight Mode: {latest_log.get('FlightMode', 'N/A')}")
            logger.info(f"   Current Mission: {latest_log.get('CurrentMissionId', 'N/A')}")
            logger.info(f"   GPS Satellites: {latest_log.get('GpsSatellites', 'N/A')}")
            logger.info(f"   GPS Accuracy: {latest_log.get('GpsAccuracy', 'N/A')}")
            logger.info(f"   Wind Speed: {latest_log.get('WindSpeed', 'N/A')}")

            # Check conditions in priority order
            logger.info(f"🔍 Checking conditions in priority order...")
            
            # 1. Check retirement conditions
            logger.info(f"1️⃣ Checking retirement conditions...")
            if self.check_retirement_conditions(unit_id):
                logger.info(f"❌ Drone {unit_id} meets retirement conditions - Setting to RETIRED")
                retired_status = DeviceStatus.objects.get(code=DroneStatusCode.RETIRED)
                device.status = retired_status
                device.save()
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.RETIRED])
                logger.info(f"=== Drone {unit_id} state analysis completed: RETIRED ===")
                return DroneStatusCode.RETIRED, status_msg
            else:
                logger.info(f"✅ Drone {unit_id} does not meet retirement conditions")

            # 2. Check inactivity
            logger.info(f"2️⃣ Checking inactivity...")
            time_diff = (current_time - last_timestamp).total_seconds()
            timeout_seconds = DRONE_STATE_THRESHOLDS["INACTIVE_TIMEOUT_MINUTES"] * 60
            logger.info(f"   Time since last update: {time_diff:.1f} seconds")
            logger.info(f"   Inactivity threshold: {timeout_seconds} seconds")
            
            if time_diff > timeout_seconds:
                logger.info(f"❌ Drone {unit_id} inactive for {time_diff:.1f} seconds - Setting to INACTIVE")
                inactive_status = DeviceStatus.objects.get(code=DroneStatusCode.INACTIVE)
                device.status = inactive_status
                device.save()
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.INACTIVE])
                logger.info(f"=== Drone {unit_id} state analysis completed: INACTIVE ===")
                return DroneStatusCode.INACTIVE, status_msg
            else:
                logger.info(f"✅ Drone {unit_id} is active (within timeout period)")

            # 3. Check maintenance
            logger.info(f"3️⃣ Checking maintenance needs...")
            maintenance_needed = self.needs_maintenance(latest_log, logs)
            if maintenance_needed:
                logger.info(f"❌ Drone {unit_id} needs maintenance - Setting to MAINTENANCE")
                maintenance_status = DeviceStatus.objects.get(code=DroneStatusCode.MAINTENANCE)
                device.status = maintenance_status
                device.save()
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.MAINTENANCE])
                logger.info(f"=== Drone {unit_id} state analysis completed: MAINTENANCE ===")
                return DroneStatusCode.MAINTENANCE, status_msg
            else:
                logger.info(f"✅ Drone {unit_id} does not need maintenance")

            # 4. Check mission status
            logger.info(f"4️⃣ Checking mission status...")
            on_mission = self.is_on_mission(latest_log)
            if on_mission:
                logger.info(f"❌ Drone {unit_id} is on mission - Setting to ON_MISSION")
                on_mission_status = DeviceStatus.objects.get(code=DroneStatusCode.ON_MISSION)
                device.status = on_mission_status
                device.save()
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.ON_MISSION])
                logger.info(f"=== Drone {unit_id} state analysis completed: ON_MISSION ===")
                return DroneStatusCode.ON_MISSION, status_msg
            else:
                logger.info(f"✅ Drone {unit_id} is not on mission")

            # 5. Check availability
            logger.info(f"5️⃣ Checking availability...")
            is_available = self.is_available(latest_log)
            if is_available:
                logger.info(f"✅ Drone {unit_id} is available - Setting to AVAILABLE")
                available_status = DeviceStatus.objects.get(code=DroneStatusCode.AVAILABLE)
                device.status = available_status
                device.save()
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.AVAILABLE])
                logger.info(f"=== Drone {unit_id} state analysis completed: AVAILABLE ===")
                return DroneStatusCode.AVAILABLE, status_msg
            else:
                logger.info(f"❌ Drone {unit_id} is not available")

            # 6. Default to operational
            logger.info(f"6️⃣ Default condition - Setting to OPERATIONAL")
            operational_status = DeviceStatus.objects.get(code=DroneStatusCode.OPERATIONAL)
            device.status = operational_status
            device.save()
            status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.OPERATIONAL])
            logger.info(f"=== Drone {unit_id} state analysis completed: OPERATIONAL ===")
            return DroneStatusCode.OPERATIONAL, status_msg

        except Exception as e:
            error_msg = self.get_localized_message(DRONE_ERROR_MESSAGES, "STATE_UPDATE_ERROR")
            logger.error(f"{error_msg}: {str(e)}")
            return None, error_msg 

    def check_all_drones_state(self) -> Dict[str, List[str]]:
        """
        Periodically checks the state of all drones in the system.
        This method is designed to be called by Celery Beat.
        
        Returns:
            Dict[str, List[str]]: Dictionary containing lists of drone IDs grouped by their states
            Example: {
                "success": ["drone1", "drone2"],
                "error": ["drone3"],
                "not_found": ["drone4"]
            }
        """
        results = {
            "success": [],
            "error": [],
            "not_found": [],
            "processed_drones": set(),  # Track processed drones to avoid duplication
            "total_drones": 0
        }
        
        try:
            # Get all devices from database with optimized query
            devices = Device.objects.filter(active=True).select_related('status')
            total_devices = devices.count()
            results["total_drones"] = total_devices
            
            logger.info(f"Starting state check for {total_devices} drones")
            
            # Pre-fetch all device statuses to avoid N+1 queries
            device_statuses = {
                status.code: status 
                for status in DeviceStatus.objects.all()
            }
            
            # For small number of drones, process directly without batching
            if total_devices <= 10:
                batch_results = self._process_drone_batch(devices, device_statuses, results["processed_drones"])
                results["success"].extend(batch_results["success"])
                results["error"].extend(batch_results["error"])
                results["not_found"].extend(batch_results["not_found"])
                logger.info(f"Processed {total_devices} drones directly (unique: {len(results['processed_drones'])})")
            else:
                # Process devices in batches for large numbers
                batch_size = 20
                for i in range(0, total_devices, batch_size):
                    batch_devices = devices[i:i + batch_size]
                    batch_results = self._process_drone_batch(batch_devices, device_statuses, results["processed_drones"])
                    
                    # Merge results
                    results["success"].extend(batch_results["success"])
                    results["error"].extend(batch_results["error"])
                    results["not_found"].extend(batch_results["not_found"])
                    
                    logger.info(f"Processed batch {i//batch_size + 1}/{(total_devices + batch_size - 1)//batch_size} (unique: {len(results['processed_drones'])})")
                    
            # Verify no duplication
            total_processed = len(results["success"]) + len(results["error"]) + len(results["not_found"])
            if total_processed != len(results["processed_drones"]):
                logger.warning(f"⚠️  Potential duplication detected: processed {total_processed} results but only {len(results['processed_drones'])} unique drones")
                    
        except Exception as e:
            logger.error(f"Error in check_all_drones_state: {str(e)}")
            
        # Log summary
        logger.info("Drone state check summary:")
        logger.info(f"Total drones in DB: {results['total_drones']}")
        logger.info(f"Unique drones processed: {len(results['processed_drones'])}")
        logger.info(f"Success: {len(results['success'])} drones")
        logger.info(f"Error: {len(results['error'])} drones")
        logger.info(f"Not found: {len(results['not_found'])} drones")
        
        return results

    def _process_drone_batch(self, devices, device_statuses, processed_drones: set) -> Dict[str, List[str]]:
        """
        Process a batch of drones to update their states
        
        Args:
            devices: QuerySet of devices to process
            device_statuses: Dictionary of pre-fetched device statuses
            processed_drones: Set to track processed drones and avoid duplication
            
        Returns:
            Dict[str, List[str]]: Results for this batch
        """
        batch_results = {
            "success": [],
            "error": [],
            "not_found": []
        }
        
        # Collect devices that need status updates
        devices_to_update = []
        
        for device in devices:
            try:
                # Get the unit_id
                unit_id = device.unit_id
                if not unit_id:
                    logger.warning(f"Device {device.id} has no unit_id")
                    batch_results["error"].append(f"device_{device.id}")
                    continue
                    
                # Check for duplication
                if unit_id in processed_drones:
                    logger.warning(f"⚠️  Duplicate drone detected: {unit_id} already processed, skipping")
                    continue
                    
                # Mark as processed
                processed_drones.add(unit_id)
                    
                # Analyze state without updating database yet
                state_code, status_message = self._analyze_drone_state_without_update(unit_id, device_statuses)
                
                if state_code is None:
                    logger.error(f"Failed to analyze state for drone {unit_id}: {status_message}")
                    batch_results["error"].append(unit_id)
                else:
                    # Mark device for bulk update
                    device.status = device_statuses.get(state_code)
                    if device.status:
                        devices_to_update.append(device)
                        batch_results["success"].append(unit_id)
                        # Reduce logging for batch processing
                        if len(devices) <= 5:  # Only log details for small batches
                            logger.info(f"Successfully analyzed state for drone {unit_id} to {state_code}: {status_message}")
                    else:
                        logger.error(f"Status code {state_code} not found in device_statuses")
                        batch_results["error"].append(unit_id)
                        
            except Exception as e:
                logger.error(f"Error processing device {device.id}: {str(e)}")
                batch_results["error"].append(f"device_{device.id}")
        
        # Bulk update all devices that need status changes
        if devices_to_update:
            try:
                with transaction.atomic():
                    Device.objects.bulk_update(devices_to_update, ['status'])
                logger.info(f"Bulk updated {len(devices_to_update)} devices")
            except Exception as e:
                logger.error(f"Error in bulk update: {str(e)}")
                # Mark all devices in this batch as error
                for device in devices_to_update:
                    if device.unit_id:
                        batch_results["error"].append(device.unit_id)
                    else:
                        batch_results["error"].append(f"device_{device.id}")
        
        return batch_results

    def _analyze_drone_state_without_update(self, unit_id: str, device_statuses: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Analyzes drone state without updating database (for batch processing)
        
        Args:
            unit_id: ID of the drone to analyze
            device_statuses: Dictionary of pre-fetched device statuses
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (state_code, status_message)
        """
        try:
            # Get recent logs
            logs, error_msg = self.get_recent_logs(unit_id)
            if error_msg:
                return None, error_msg
            if not logs:
                # Return inactive if no logs
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.INACTIVE])
                return DroneStatusCode.INACTIVE, status_msg

            latest_log = logs[0]
            
            # Parse timestamp with error handling - Always work in UTC
            try:
                timestamp_str = latest_log['timestamp']
                if '.' in timestamp_str:
                    parts = timestamp_str.split('.')
                    base = parts[0]
                    micro = parts[1].replace('Z', '')[:6]  # Ensure 6 digits microseconds
                    timestamp_str = f"{base}.{micro}Z"
                    last_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                else:
                    last_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                
                # Get current time in UTC
                current_time = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"Error parsing timestamp {latest_log.get('timestamp')}: {str(e)}")
                # Use current time as fallback, ensuring UTC
                current_time = datetime.now(timezone.utc)
                last_timestamp = current_time

            # Check conditions in priority order
            # 1. Check retirement conditions
            if self.check_retirement_conditions(unit_id):
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.RETIRED])
                return DroneStatusCode.RETIRED, status_msg

            # 2. Check inactivity
            time_diff = (current_time - last_timestamp).total_seconds()
            if time_diff > DRONE_STATE_THRESHOLDS["INACTIVE_TIMEOUT_MINUTES"] * 60:
                logger.info(f"Drone inactive: {time_diff} seconds since last update")
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.INACTIVE])
                return DroneStatusCode.INACTIVE, status_msg

            # Continue with other checks...
            # 3. Check maintenance
            if self.needs_maintenance(latest_log, logs):
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.MAINTENANCE])
                return DroneStatusCode.MAINTENANCE, status_msg

            # 4. Check mission status
            if self.is_on_mission(latest_log):
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.ON_MISSION])
                return DroneStatusCode.ON_MISSION, status_msg

            # 5. Check availability
            if self.is_available(latest_log):
                status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.AVAILABLE])
                return DroneStatusCode.AVAILABLE, status_msg

            # 6. Default to operational
            status_msg = self.get_localized_message(DRONE_STATE_MESSAGES[DroneStatusCode.OPERATIONAL])
            return DroneStatusCode.OPERATIONAL, status_msg

        except Exception as e:
            error_msg = self.get_localized_message(DRONE_ERROR_MESSAGES, "STATE_UPDATE_ERROR")
            logger.error(f"{error_msg}: {str(e)}")
            return None, error_msg 