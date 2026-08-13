import math
import logging
from core.base import models
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.db.models import Subquery, OuterRef
from django.db.models.functions import Coalesce, Concat, Cast
from django.db.models import Value
from django.db.models.fields import CharField
from django.contrib.contenttypes.models import ContentType
from common.constant import MESSAGE_ENUM
from stream_monitors.utils.minio_client import minio_client
from flight_log.models import DroneAnomalyPrediction, FlightLog
from django.utils import timezone
from devices.models import Device, DeviceStatus, Measurement
from delivery.models import DeliveryOperation, DeliveryOperationItem
from terminals.models import Terminal, Routes, RouteTerminal
from surveillance.models import SurveyMission
from math import atan2, degrees
from datetime import datetime
import pandas as pd
import numpy as np
from django.conf import settings
import requests
from safedelete.models import (
    SafeDeleteModel,
    SOFT_DELETE,
    SOFT_DELETE_CASCADE,
    HARD_DELETE,
    HARD_DELETE_NOCASCADE,
    NO_DELETE,
)

logger = logging.getLogger(__name__)

class FlightLogService:
    @staticmethod
    def get_flight_logs_queryset():
        """
        Returns optimized queryset for flight logs listing.
        Does NOT iterate or modify records - pure read operation.
        """
        flight_log_content_type = ContentType.objects.get_for_model(FlightLog)
        total_distance_subquery = Measurement.objects.filter(
            content_type=flight_log_content_type,
            object_id=OuterRef('id'),
            measurement_type='total_distance'
        ).annotate(
            formatted=Concat(
                Cast('data__value', output_field=CharField()),
                Value(' '),
                Cast('data__unit', output_field=CharField()),
                output_field=CharField()
            )
        ).values('formatted')[:1]
        return FlightLog.objects.select_related(
            'order_item__delivery_item__delivery_operation__route',
            'order_item__order',
            'order_item__delivery_item__drone',
            'start_point',
            'end_point',
            'drone',
            'drone_state_prediction',
            'drone_anomaly_prediction',
            'profile_drone__device',
            'profile_drone__profile__mission',
            'profile_drone__start_waypoint',
            'profile_drone__end_waypoint',
        ).annotate(
            route=models.F('order_item__delivery_item__delivery_operation__route'),
            route_name=models.F('order_item__delivery_item__delivery_operation__route__name'),
            route_code=models.F('order_item__delivery_item__delivery_operation__route__code'),
            # drone_name: fallback from drone -> profile_drone.device -> order_item.delivery_item.drone
            drone_name=Coalesce(
                models.F('drone__name'),
                models.F('profile_drone__device__name'),
                models.F('order_item__delivery_item__drone__name'),
            ),
            # mission_id and mission_name from profile_drone
            mission_id=models.F('profile_drone__profile__mission__id'),
            mission_name=models.F('profile_drone__profile__mission__name'),
            # order_code from order_item
            order_code=models.F('order_item__order__order_code'),
            # start_point__name: fallback from start_point -> profile_drone.start_waypoint.terminal
            start_point__name=Coalesce(
                models.F('start_point__name'),
                models.F('profile_drone__start_waypoint__name'),
            ),
            # end_point__name: fallback from end_point -> profile_drone.end_waypoint.terminal
            end_point__name=Coalesce(
                models.F('end_point__name'),
                models.F('profile_drone__end_waypoint__name'),
            ),
            drone_anomaly_prediction__name=models.F('drone_anomaly_prediction__name'),
            drone_anomaly_prediction__code=models.F('drone_anomaly_prediction__code'),
            total_distance=Subquery(total_distance_subquery, output_field=CharField()),
            profile_drone__profile=models.F('profile_drone__profile__name'),

        ).order_by('-id')

    @staticmethod
    def get_flight_logs():
        """
        Legacy method - calls get_flight_logs_queryset for backward compatibility.
        """
        return FlightLogService.get_flight_logs_queryset()

    @staticmethod
    @transaction.atomic
    def update_pending_anomaly_predictions(limit=10):
        """
        Background task to update pending anomaly predictions.
        Should be called via Celery task or management command, NOT in GET request.
        """
        # Cache anomaly prediction codes to avoid repeated queries
        normal_prediction = DroneAnomalyPrediction.objects.get(code="NORMAL")
        warning_prediction = DroneAnomalyPrediction.objects.get(code="WARNING")
        
        # Fetch all flight logs that need processing
        flight_logs = FlightLog.objects.filter(
            fetch_anomaly_status="pending"
        ).select_related(
            'order_item__delivery_item__drone',
            'order_item',
            'profile_drone__device',
            'profile_drone__profile',
            'drone_anomaly_prediction',
        )[:limit]
        
        for flight in flight_logs:
            # If drone_anomaly_prediction is None and still has fetch attempts
            if flight.drone_anomaly_prediction is None and flight.fetch_anomaly_count < 3 and flight.fetch_anomaly_status != "done":
                log_code = None
                
                if flight.order_item:
                    device = getattr(getattr(flight.order_item, 'delivery_item', None), 'drone', None)
                    if device:
                        log_code = f"{device.serial_number}_{flight.order_item.code}"
                elif flight.profile_drone:
                    profile_drone = flight.profile_drone
                    if profile_drone and profile_drone.device:
                        log_code = f"{profile_drone.device.serial_number}_{profile_drone.profile.code}"
                
                if log_code:
                    anomaly_prediction = FlightLogService.get_flight_log_with_anomaly_prediction(log_code)
                    if anomaly_prediction:
                        if anomaly_prediction == "NORMAL":
                            flight.drone_anomaly_prediction = normal_prediction
                        elif anomaly_prediction == "WARNING":
                            flight.drone_anomaly_prediction = warning_prediction
                        flight.fetch_data_status = "done"
                    else:
                        flight.fetch_anomaly_count += 1
                    flight.save(update_fields=['drone_anomaly_prediction', 'fetch_data_status', 'fetch_anomaly_count'])
            elif flight.drone_anomaly_prediction is None and flight.fetch_anomaly_count >= 3 and flight.fetch_anomaly_status != "done":
                flight.fetch_anomaly_status = "done"
                flight.drone_anomaly_prediction = normal_prediction
                flight.save(update_fields=['fetch_anomaly_status', 'drone_anomaly_prediction'])

    @staticmethod
    def get_drone_log_raw_data(unique_id, start_time, end_time, msg_type="RAW_IMU"):
        # Import inside method to avoid circular import
        from delivery.services.processing_service import opensearch_service
        try:
            # Retrieve historical IMU data for acceleration charts
            time_from = start_time.isoformat() + "Z"
            time_to = end_time.isoformat() + "Z"
            historical_imu = opensearch_service.search_drone_logs_by_unique_id_updated(
                unique_id=unique_id,
                msg_type=msg_type,
                time_from=time_from,
                time_to=time_to,
                size=1000,
                sort_order="desc"
            )
            # print("historical_imu: ", historical_imu.get('hits', {}).get('hits', []))
            return historical_imu.get('hits', {}).get('hits', [])
        except Exception as e:
            print(f"❌ [AI_ANALYSIS] Error: {str(e)}")
            return []


    @staticmethod
    def get_log_data(unit_id, start_time, end_time):
        """
        Get flight log analysis data for a specific device.
        
        Args:
            unit_id: Device unit ID
            start_time: Start time of the flight
            end_time: End time of the flight
            
        Returns:
            Dictionary containing roll_analysis, pitch_analysis, yaw_analysis,
            rollspeed_analysis, pitchspeed_analysis, yawspeed_analysis
        """
        # Get full telemetry history
        flight_log_attitude_data = FlightLogService.get_drone_log_raw_data(unit_id, start_time, end_time, msg_type="ATTITUDE")
        flight_log_nav_data = FlightLogService.get_drone_log_raw_data(unit_id, start_time, end_time, msg_type="NAV_CONTROLLER_OUTPUT")
        print(f"Drone unit id: {unit_id}")
        
        # Calculate roll analysis from raw IMU data
        roll_analysis = []
        rollspeed_analysis = []
        pitch_analysis = []
        pitchspeed_analysis = []
        yaw_analysis = []
        yawspeed_analysis = []
        desired_roll_analysis = []
        desired_pitch_analysis = []
        
        for entry in flight_log_attitude_data:
            src = entry["_source"]
            ts = pd.to_datetime(src["timestamp"])
            roll = src["roll"]
            roll_analysis.append({
                "timestamp": ts.isoformat(),
                "roll": roll,
            })
            rollspeed = src["rollspeed"]
            rollspeed_analysis.append({
                "timestamp": ts.isoformat(),
                "rollspeed": rollspeed
            })
            pitch = src["pitch"]
            pitch_analysis.append({
                "timestamp": ts.isoformat(),
                "pitch": pitch
            })
            pitchspeed = src["pitchspeed"]
            pitchspeed_analysis.append({
                "timestamp": ts.isoformat(),
                "pitchspeed": pitchspeed
            })
            yaw = src["yaw"]
            yaw_analysis.append({
                "timestamp": ts.isoformat(),
                "yaw": yaw
            })
            yawspeed = src["yawspeed"]
            yawspeed_analysis.append({
                "timestamp": ts.isoformat(),
                "yawspeed": yawspeed
            })
        
        for entry in flight_log_nav_data:
            src = entry["_source"]
            ts = pd.to_datetime(src["timestamp"])
            desired_roll = src["navRoll"]
            desired_roll_analysis.append({
                "timestamp": ts.isoformat(),
                "desired_roll": desired_roll
            })
            desired_pitch = src["navPitch"]
            desired_pitch_analysis.append({
                "timestamp": ts.isoformat(),
                "desired_pitch": desired_pitch
            })
        
        # Helper function to round timestamp to seconds
        def round_timestamp_to_second(ts_str):
            """Round ISO timestamp string to second precision"""
            try:
                ts = pd.to_datetime(ts_str)
                # Round to nearest second
                ts_rounded = ts.replace(microsecond=0)
                return ts_rounded.isoformat()
            except Exception:
                return ts_str
        
        # Round timestamps in existing roll_analysis records to seconds for consistency
        for roll in roll_analysis:
            roll["timestamp"] = round_timestamp_to_second(roll["timestamp"])
        
        # Round timestamps in desired_roll_analysis to seconds for consistency
        desired_roll_analysis_dict = {}
        for desired_roll in desired_roll_analysis:
            timestamp = desired_roll["timestamp"]
            rounded_timestamp = round_timestamp_to_second(timestamp)
            desired_roll_analysis_dict[rounded_timestamp] = desired_roll["desired_roll"]
        
        # Map desired_roll to existing roll_analysis records
        for roll in roll_analysis:
            timestamp = roll["timestamp"]
            if timestamp in desired_roll_analysis_dict:
                roll["desired_roll"] = desired_roll_analysis_dict[timestamp]
            else:
                roll["desired_roll"] = None
        
        # Add any desired_roll records that don't have matching roll_analysis timestamps
        for desired_timestamp, desired_roll_value in desired_roll_analysis_dict.items():
            if not any(roll["timestamp"] == desired_timestamp for roll in roll_analysis):
                roll_analysis.append({
                    "timestamp": desired_timestamp,
                    "roll": None,
                    "desired_roll": desired_roll_value
                })
        
        # Sort roll_analysis by timestamp
        roll_analysis.sort(key=lambda x: x["timestamp"])
        
        # Find the first index where roll has a value (not None)
        first_roll_index = None
        for i, roll in enumerate(roll_analysis):
            if roll.get("roll") is not None:
                first_roll_index = i
                break
        
        # Forward-fill roll and desired_roll starting from first_roll_index
        if first_roll_index is not None:
            previous_roll = roll_analysis[first_roll_index]["roll"]
            previous_desired_roll = roll_analysis[first_roll_index].get("desired_roll")
            
            for i in range(first_roll_index + 1, len(roll_analysis)):
                roll_record = roll_analysis[i]
                if roll_record.get("roll") is None:
                    roll_record["roll"] = previous_roll
                else:
                    previous_roll = roll_record["roll"]
                
                if roll_record.get("desired_roll") is None and previous_desired_roll is not None:
                    roll_record["desired_roll"] = previous_desired_roll
                elif roll_record.get("desired_roll") is not None:
                    previous_desired_roll = roll_record["desired_roll"]
        
        # Round timestamps in existing pitch_analysis records to seconds for consistency
        for pitch in pitch_analysis:
            pitch["timestamp"] = round_timestamp_to_second(pitch["timestamp"])
        
        # Round timestamps in desired_pitch_analysis to seconds for consistency
        desired_pitch_analysis_dict = {}
        for desired_pitch in desired_pitch_analysis:
            timestamp = desired_pitch["timestamp"]
            rounded_timestamp = round_timestamp_to_second(timestamp)
            desired_pitch_analysis_dict[rounded_timestamp] = desired_pitch["desired_pitch"]
        
        # Map desired_pitch to existing pitch_analysis records
        for pitch in pitch_analysis:
            timestamp = pitch["timestamp"]
            if timestamp in desired_pitch_analysis_dict:
                pitch["desired_pitch"] = desired_pitch_analysis_dict[timestamp]
            else:
                pitch["desired_pitch"] = None
        
        # Add any desired_pitch records that don't have matching pitch_analysis timestamps
        for desired_timestamp, desired_pitch_value in desired_pitch_analysis_dict.items():
            if not any(pitch["timestamp"] == desired_timestamp for pitch in pitch_analysis):
                pitch_analysis.append({
                    "timestamp": desired_timestamp,
                    "pitch": None,
                    "desired_pitch": desired_pitch_value
                })
        
        # Sort pitch_analysis by timestamp
        pitch_analysis.sort(key=lambda x: x["timestamp"])
        
        # Find the first index where pitch has a value (not None)
        first_pitch_index = None
        for i, pitch in enumerate(pitch_analysis):
            if pitch.get("pitch") is not None:
                first_pitch_index = i
                break
        
        # Forward-fill pitch and desired_pitch starting from first_pitch_index
        if first_pitch_index is not None:
            previous_pitch = pitch_analysis[first_pitch_index]["pitch"]
            previous_desired_pitch = pitch_analysis[first_pitch_index].get("desired_pitch")
            
            for i in range(first_pitch_index + 1, len(pitch_analysis)):
                pitch_record = pitch_analysis[i]
                if pitch_record.get("pitch") is None:
                    pitch_record["pitch"] = previous_pitch
                else:
                    previous_pitch = pitch_record["pitch"]
                
                if pitch_record.get("desired_pitch") is None and previous_desired_pitch is not None:
                    pitch_record["desired_pitch"] = previous_desired_pitch
                elif pitch_record.get("desired_pitch") is not None:
                    previous_desired_pitch = pitch_record["desired_pitch"]
        
        # Remove elements where both roll and desired_roll are None
        roll_analysis = [
            roll for roll in roll_analysis
            if roll.get("roll") is not None and roll.get("desired_roll") is not None
        ]
        # Remove elements where both pitch and desired_pitch are None
        pitch_analysis = [
            pitch for pitch in pitch_analysis
            if pitch.get("pitch") is not None and pitch.get("desired_pitch") is not None
        ]
        
        return {
            'roll_analysis': roll_analysis,
            'pitch_analysis': pitch_analysis,
            'yaw_analysis': yaw_analysis,
            'rollspeed_analysis': rollspeed_analysis,
            'pitchspeed_analysis': pitchspeed_analysis,
            'yawspeed_analysis': yawspeed_analysis
        }

    @staticmethod
    def get_flight_log_detail(id):
        """
        Get flight log detail by ID.
        
        Args:
            id: FlightLog ID
            
        Returns:
            Dictionary containing flight log analysis data
        """
        try:
            # Optimize query with select_related to avoid multiple database hits
            flight_log = FlightLog._base_manager.select_related(
                'order_item__delivery_item__delivery_operation__route'
            ).get(id=id)
            
            # Get the device from the route
            if flight_log.order_item:
                device = flight_log.order_item.delivery_item.drone
                if not device:
                    return {
                        "roll_analysis": [],
                        "pitch_analysis": [],
                        "yaw_analysis": [],
                        "rollspeed_analysis": [],
                        "pitchspeed_analysis": [],
                        "yawspeed_analysis": [],
                    }
            elif flight_log.profile_drone:
                device = flight_log.profile_drone.device
                if not device:
                    return {
                        "roll_analysis": [],
                        "pitch_analysis": [],
                        "yaw_analysis": [],
                        "rollspeed_analysis": [],
                        "pitchspeed_analysis": [],
                        "yawspeed_analysis": [],
                    }
                
            start_time = flight_log.start_time
            end_time = flight_log.end_time

            # first check if log_file_path is not None
            if flight_log.log_file_path is not None:
                # parse log file to json data
                # if get_json is None, then get flight log data and save as json file to minio
                log_file = minio_client.get_json(flight_log.log_file_path)
                if log_file is None:
                    log_data = FlightLogService.get_log_data(device.unit_id, start_time, end_time)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{device.unit_id}.json"
                    log_path = minio_client.save_json(log_data, device.unit_id, filename)
                    flight_log.log_file_path = log_path
                    flight_log.save()
                    return log_data
                else:
                    return log_file
            else:
                # get flight log data and save as json file to minio
                log_data = FlightLogService.get_log_data(device.unit_id, start_time, end_time)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{device.unit_id}.json"
                log_path = minio_client.save_json(log_data, device.unit_id, filename)
                flight_log.log_file_path = log_path
                flight_log.save()
                return log_data
            
        except FlightLog.DoesNotExist:
            raise ValidationError(f"FlightLog with id {id} does not exist")
        except Exception as e:
            raise ValidationError(f"Error retrieving flight log detail: {str(e)}")
    
    @staticmethod
    def _filter_telemetry_by_time_range(telemetry_data, start_time, end_time):
        """
        Filter telemetry data by time range.
        
        Args:
            telemetry_data: Dictionary containing telemetry data with timestamps
            start_time: datetime object for flight start
            end_time: datetime object for flight end
            
        Returns:
            Filtered telemetry data dictionary
        """
        from datetime import datetime
        
        # Convert datetime objects to timestamps
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        
        filtered_data = {}
        
        # Filter main timestamps and related data
        if 'timestamps' in telemetry_data:
            timestamps = telemetry_data['timestamps']
            
            # Find indices within time range
            valid_indices = [
                i for i, ts in enumerate(timestamps) 
                if start_timestamp <= ts <= end_timestamp
            ]
            
            # Filter timestamps
            filtered_data['timestamps'] = [timestamps[i] for i in valid_indices]
            
            # Filter temperature data if exists
            if 'temperature' in telemetry_data and telemetry_data['temperature']:
                filtered_data['temperature'] = [
                    telemetry_data['temperature'][i] for i in valid_indices
                    if i < len(telemetry_data['temperature'])
                ]
            else:
                filtered_data['temperature'] = []
            
            # Filter acceleration data
            if 'acceleration' in telemetry_data:
                filtered_data['acceleration'] = {}
                for axis in ['x', 'y', 'z']:
                    if axis in telemetry_data['acceleration']:
                        filtered_data['acceleration'][axis] = [
                            telemetry_data['acceleration'][axis][i] for i in valid_indices
                            if i < len(telemetry_data['acceleration'][axis])
                        ]
            
            # Filter acceleration_raw data
            if 'acceleration_raw' in telemetry_data:
                filtered_data['acceleration_raw'] = {}
                for axis in ['x', 'y', 'z']:
                    if axis in telemetry_data['acceleration_raw']:
                        filtered_data['acceleration_raw'][axis] = [
                            telemetry_data['acceleration_raw'][axis][i] for i in valid_indices
                            if i < len(telemetry_data['acceleration_raw'][axis])
                        ]
        
        # Filter vibration timestamps and related data
        if 'timestamps_vibration' in telemetry_data:
            vibration_timestamps = telemetry_data['timestamps_vibration']
            
            # Find indices within time range for vibration data
            vibration_valid_indices = [
                i for i, ts in enumerate(vibration_timestamps) 
                if start_timestamp <= ts <= end_timestamp
            ]
            
            # Filter vibration timestamps
            filtered_data['timestamps_vibration'] = [
                vibration_timestamps[i] for i in vibration_valid_indices
            ]
            
            # Filter vibration data
            if 'vibration' in telemetry_data:
                filtered_data['vibration'] = {}
                for axis in ['x', 'y', 'z']:
                    if axis in telemetry_data['vibration']:
                        filtered_data['vibration'][axis] = [
                            telemetry_data['vibration'][axis][i] for i in vibration_valid_indices
                            if i < len(telemetry_data['vibration'][axis])
                        ]
            
            # Filter vibration_raw data
            if 'vibration_raw' in telemetry_data:
                filtered_data['vibration_raw'] = {}
                for axis in ['x', 'y', 'z']:
                    if axis in telemetry_data['vibration_raw']:
                        filtered_data['vibration_raw'][axis] = [
                            telemetry_data['vibration_raw'][axis][i] for i in vibration_valid_indices
                            if i < len(telemetry_data['vibration_raw'][axis])
                        ]
        
        return filtered_data

    @staticmethod
    def create_flight_log(order_item):
        route = DeliveryOperationItem.objects.filter(order_item=order_item).first().delivery_operation.route
        start_point = RouteTerminal.objects.filter(route=route).order_by('order').first().terminal
        data = {
            "order_item": order_item,
            "start_time": timezone.now(),
            "end_time": None,
            "start_point": start_point,
            "end_point": None,
            "drone_state_prediction": None,
            "service_name": "Delivery",
            "fetch_count": 0,
            "fetch_anomaly_count": 0,
            "fetch_data_status": "pending",
            "fetch_anomaly_status": "pending",
        }
        flight_log = FlightLog.objects.create(**data)
        try:
            total_distance = route.measurements.filter(measurement_type="total_distance").first()
            flight_log.set_measurement('total_distance', total_distance.get_formatted_value(None))
            flight_log.save()
        except Exception as e:
            print(f"Error setting total distance in create_flight_log: {str(e)}")
        return flight_log

    @staticmethod
    def create_flight_log_from_profile(drone_assignment):
        print(f"Creating flight log from profile: {drone_assignment.profile.id}")
        try:
            # get log data from opensearch
            log_data = FlightLogService.get_log_data(drone_assignment.device.unit_id, drone_assignment.profile.actual_start_time, drone_assignment.profile.actual_end_time)
            # save log_data as json file to minio
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{drone_assignment.device.unit_id}.json"
            log_path = minio_client.save_json(log_data, drone_assignment.device.unit_id, filename)
            full_log_path = f"https://{settings.MINIO_ENDPOINT}/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{log_path}"
            data = {
                "order_item": None,
                "drone": drone_assignment.device,
                "profile_drone": drone_assignment,
                "start_time": drone_assignment.profile.actual_start_time,
                "end_time": drone_assignment.profile.actual_end_time,
                "start_point": drone_assignment.start_waypoint.terminal,
                "end_point": drone_assignment.end_waypoint.terminal,
                "drone_state_prediction": None,
                "log_file_path": full_log_path,
                "service_name": "Surveillance",
                "group": drone_assignment.group,
                "created_by": drone_assignment.profile.created_by,
                "modified_by": drone_assignment.profile.created_by,
                "fetch_count": 0,
                "fetch_anomaly_count": 0,
                "fetch_data_status": "pending",
                "fetch_anomaly_status": "pending",
            }
            flight_log = FlightLog.objects.create(**data)
            mission = drone_assignment.profile.mission
            total_distance = mission.measurements.filter(measurement_type='total_distance').first()
            flight_log.set_measurement('total_distance', total_distance.get_formatted_value(None))
            flight_log.save()
            return flight_log
        except Exception as e:
            print(f"Error creating flight log from profile: {str(e)}")
            return None

    @staticmethod
    def update_flight_log(order_item):
        if FlightLog._base_manager.filter(order_item=order_item).exists():
            flight_log = FlightLog._base_manager.filter(order_item=order_item).first()
            # check if DeliveryOperationItem exists
            if DeliveryOperationItem._base_manager.filter(order_item=order_item).exists():
                route = DeliveryOperationItem._base_manager.filter(order_item=order_item).first().delivery_operation.route
                flight_log.end_time = timezone.now()
                flight_log.end_point = RouteTerminal._base_manager.filter(route=route).order_by('-order').first().terminal
                flight_log.save()
            return flight_log
        else:
            return None

    @staticmethod
    def update_flight_log_with_anomaly_prediction(order_item, anomaly_prediction):
        flight_log = FlightLog.objects.filter(order_item=order_item).first()
        if not flight_log:
            logger.warning(f"Flight log not found for order_item {order_item.id}, cannot update anomaly prediction")
            return None
        anomaly_prediction_obj = DroneAnomalyPrediction._base_manager.filter(code=anomaly_prediction).first()
        if anomaly_prediction_obj:
            flight_log.drone_anomaly_prediction = anomaly_prediction_obj
        flight_log.fetch_data_status = "done"
        flight_log.save()
        return flight_log

    @staticmethod
    def update_flight_log_surveillance_with_anomaly_prediction(profile_drone_assignment, anomaly_prediction):
        flight_log = FlightLog.objects.filter(profile_drone=profile_drone_assignment).first()
        if not flight_log:
            logger.warning(f"Flight log not found for profile_drone_assignment {profile_drone_assignment.id}, cannot update anomaly prediction")
            return None
        anomaly_prediction_obj = DroneAnomalyPrediction._base_manager.filter(code=anomaly_prediction).first()
        if anomaly_prediction_obj:
            flight_log.drone_anomaly_prediction = anomaly_prediction_obj
        flight_log.fetch_data_status = "done"
        flight_log.save()
        return flight_log

    @staticmethod
    def get_flight_log_with_anomaly_prediction(log_code):
        ai_analysis_result_link = f"{settings.AI_ANALYSIS_URL}/result/{log_code}"
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        response_result = requests.get(
            ai_analysis_result_link,
            headers=headers
        )
        print(f"Response result: {response_result}")
        if not response_result.ok or not response_result.text:
            return None

        try:
            response_data = response_result.json()
        except requests.exceptions.JSONDecodeError:
            return None

        if response_data.get('status') == 'success':
            result = int(response_data.get('result').get('result'))
            if result == 0:
                return "NORMAL"
            elif result == 1:
                return "WARNING"
            else:
                return None
        return None

    def save_log_file_to_minio(log_file_data):
        pass

    @staticmethod
    def download_log_file_from_minio(log_file_path):
        response = minio_client.client.get_object(minio_client.bucket_name, log_file_path)
        return response.read()

    @staticmethod
    def delete_flight_log(ids):
        ids = ids.split(',')
        flight_logs = FlightLog.objects.filter(id__in=ids)
        if flight_logs.exists():
            for flight_log in flight_logs:
                flight_log.delete(force_policy=SOFT_DELETE_CASCADE)
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
        else:
            return False, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED)