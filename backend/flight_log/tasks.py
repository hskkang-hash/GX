import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from flight_log.models import FlightLog
from stream_monitors.utils.minio_client import minio_client

logger = logging.getLogger(__name__)


@shared_task
def fetch_flight_log_data_from_opensearch():
    """
    Scheduled task to fetch flight log data from OpenSearch, save as JSON file,
    upload to MinIO, and update FlightLog records.
    
    Only processes FlightLog records with fetch_data_status='pending'.
    """
    try:
        logger.info("🔄 Starting scheduled flight log data fetch from OpenSearch...")
        
        # Get all FlightLog records with pending status
        pending_flight_logs = FlightLog.objects.filter(
            fetch_data_status='pending',
            log_file_path__isnull=True
        ).select_related(
            'order_item__delivery_item__drone'
        )
        
        if not pending_flight_logs.exists():
            logger.info("✅ No pending flight logs to process")
            return {"status": "success", "message": "No pending flight logs", "processed": 0}
        
        processed_count = 0
        success_count = 0
        failed_count = 0
        
        for flight_log in pending_flight_logs:
            if flight_log.fetch_count >=3:
                flight_log.fetch_data_status = 'done'
                flight_log.save()
                continue
            try:
                processed_count += 1
                logger.info(f"📋 Processing flight log ID: {flight_log.id}")
                
                # Check if flight log has required data
                if not flight_log.start_time or not flight_log.end_time:
                    logger.warning(f"⚠️ Flight log {flight_log.id} missing start_time or end_time, skipping")
                    continue

                if flight_log.order_item:
                    device = flight_log.order_item.delivery_item.drone
                elif flight_log.profile_drone:
                    device = flight_log.profile_drone.device
                
                
                if not device or not device.unit_id:
                    logger.warning(f"⚠️ Flight log {flight_log.id} has no drone or unit_id, skipping")
                    continue
                
                # Fetch all log data from OpenSearch
                log_data = _fetch_all_log_data_from_opensearch(
                    device.unit_id,
                    flight_log.start_time,
                    flight_log.end_time
                )
                
                # Check if data is empty
                is_empty = False
                if not log_data:
                    is_empty = True
                elif isinstance(log_data, dict):
                    # Check if any of the data arrays (excluding flight_info) have data
                    has_data = any(
                        len(log_data[key]) > 0 
                        for key in log_data.keys() 
                        if key != "flight_info" and isinstance(log_data.get(key), list)
                    )
                    is_empty = not has_data
                elif isinstance(log_data, list):
                    is_empty = len(log_data) == 0
                
                if is_empty:
                    logger.warning(f"⚠️ Flight log {flight_log.id} returned empty data from OpenSearch")
                else:
                    logger.info(f"✅ Flight log {flight_log.id} fetched {len(log_data) if isinstance(log_data, (list, dict)) else 'data'} records")
                
                # Increment fetch_count (handle None as 0, but respect existing values)
                flight_log.fetch_count += 1
                
                # Save data to JSON and upload to MinIO if data is not empty
                if not is_empty:
                    # Save JSON file and upload to MinIO
                    file_path = _save_log_data_to_minio(flight_log.id, log_data)
                    
                    if file_path:
                        # Update flight log with file path
                        with transaction.atomic():
                            flight_log.log_file_path = file_path
                            flight_log.fetch_data_status = 'done'
                            flight_log.save()
                        logger.info(f"✅ Flight log {flight_log.id} data saved to MinIO: {file_path}")
                        success_count += 1
                    else:
                        # Failed to upload, but increment count
                        with transaction.atomic():
                            flight_log.save()
                        logger.error(f"❌ Failed to upload flight log {flight_log.id} data to MinIO")
                        failed_count += 1
                else:
                    # Data is empty, check if fetch_count reached 3
                    if flight_log.fetch_count >= 3:
                        with transaction.atomic():
                            flight_log.fetch_data_status = 'done'
                            flight_log.save()
                        logger.info(f"✅ Flight log {flight_log.id} marked as done after 3 attempts with empty data")
                        success_count += 1
                    else:
                        # Just save the incremented count
                        with transaction.atomic():
                            flight_log.save()
                        logger.info(f"📊 Flight log {flight_log.id} fetch_count incremented to {flight_log.fetch_count}")
                        failed_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing flight log {flight_log.id}: {str(e)}", exc_info=True)
                failed_count += 1
                # Increment fetch_count even on error
                try:
                    with transaction.atomic():
                        flight_log.fetch_count += 1
                        if flight_log.fetch_count >= 3:
                            flight_log.fetch_data_status = 'done'
                        flight_log.save()
                except Exception as save_error:
                    logger.error(f"❌ Error saving flight log {flight_log.id} after error: {str(save_error)}")
        
        result = {
            "status": "success",
            "processed": processed_count,
            "success": success_count,
            "failed": failed_count
        }
        logger.info(f"✅ Flight log data fetch completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in scheduled flight log data fetch: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


def _fetch_all_log_data_from_opensearch(unique_id, start_time, end_time):
    """
    Fetch all log data from OpenSearch for a given time range.
    
    Args:
        unique_id: Device unit ID
        start_time: Flight start time
        end_time: Flight end time
        
    Returns:
        Dictionary containing all log data organized by message type
    """
    try:
        from delivery.services.processing_service import opensearch_service
        
        # Convert times to ISO format with Z suffix
        time_from = start_time.isoformat() + "Z"
        time_to = end_time.isoformat() + "Z"
        
        # Fetch data for different message types
        # Based on get_flight_log_detail, we fetch ATTITUDE and NAV_CONTROLLER_OUTPUT
        # But for comprehensive data, let's fetch all available types
        
        log_data = {
            "flight_info": {
                "unique_id": unique_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "fetched_at": timezone.now().isoformat()
            },
            "attitude": [],
            "nav_controller_output": [],
            "raw_imu": [],
            "global_position_int": [],
            "vibration": [],
            "sys_status": []
        }
        
        # Fetch ATTITUDE data
        attitude_data = opensearch_service.search_drone_logs_by_unique_id_updated(
            unique_id=unique_id,
            msg_type="ATTITUDE",
            time_from=time_from,
            time_to=time_to,
            size=10000,
            sort_order="asc"
        )
        log_data["attitude"] = attitude_data.get('hits', {}).get('hits', [])
        
        # Fetch NAV_CONTROLLER_OUTPUT data
        nav_data = opensearch_service.search_drone_logs_by_unique_id_updated(
            unique_id=unique_id,
            msg_type="NAV_CONTROLLER_OUTPUT",
            time_from=time_from,
            time_to=time_to,
            size=10000,
            sort_order="asc"
        )
        log_data["nav_controller_output"] = nav_data.get('hits', {}).get('hits', [])
        
        # Fetch RAW_IMU data
        raw_imu_data = opensearch_service.search_drone_logs_by_unique_id_updated(
            unique_id=unique_id,
            msg_type="RAW_IMU",
            time_from=time_from,
            time_to=time_to,
            size=10000,
            sort_order="asc"
        )
        log_data["raw_imu"] = raw_imu_data.get('hits', {}).get('hits', [])
        
        # Fetch GLOBAL_POSITION_INT data
        position_data = opensearch_service.search_drone_logs_by_unique_id_updated(
            unique_id=unique_id,
            msg_type="GLOBAL_POSITION_INT",
            time_from=time_from,
            time_to=time_to,
            size=10000,
            sort_order="asc"
        )
        log_data["global_position_int"] = position_data.get('hits', {}).get('hits', [])
        
        # Fetch VIBRATION data
        vibration_data = opensearch_service.search_drone_logs_by_unique_id_updated(
            unique_id=unique_id,
            msg_type="VIBRATION",
            time_from=time_from,
            time_to=time_to,
            size=10000,
            sort_order="asc"
        )
        log_data["vibration"] = vibration_data.get('hits', {}).get('hits', [])
        
        # Fetch SYS_STATUS data
        sys_status_data = opensearch_service.search_drone_logs_by_unique_id_updated(
            unique_id=unique_id,
            msg_type="SYS_STATUS",
            time_from=time_from,
            time_to=time_to,
            size=10000,
            sort_order="asc"
        )
        log_data["sys_status"] = sys_status_data.get('hits', {}).get('hits', [])
        
        # Check if any data was fetched
        has_data = any(
            len(log_data[key]) > 0 
            for key in log_data.keys() 
            if key != "flight_info"
        )
        
        if not has_data:
            return None
        
        return log_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching log data from OpenSearch for {unique_id}: {str(e)}", exc_info=True)
        return None


def _save_log_data_to_minio(flight_log_id, log_data):
    """
    Save log data as JSON file and upload to MinIO.
    
    Args:
        flight_log_id: Flight log ID
        log_data: Log data dictionary to save
        
    Returns:
        str: Object path in MinIO, or None if failed
    """
    try:
        if not log_data:
            logger.warning(f"⚠️ No log data to save for flight log {flight_log_id}")
            return None
        
        # Generate filename with flight log ID and timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"flight_log_{flight_log_id}_{timestamp}"
        
        # Use MinIO client to save JSON
        object_path = minio_client.save_json(
            json_data=log_data,
            stream_id=f"flight_logs",
            filename=filename
        )
        
        if object_path:
            logger.info(f"✅ Successfully saved flight log {flight_log_id} data to MinIO: {object_path}")
            return object_path
        else:
            logger.error(f"❌ Failed to save flight log {flight_log_id} data to MinIO")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error saving flight log {flight_log_id} data to MinIO: {str(e)}", exc_info=True)
        return None


@shared_task
def task_update_pending_anomaly_predictions(limit=10):
    """
    Scheduled task to fetch and update anomaly predictions for pending flight logs.
    
    This task:
    - Fetches flight logs with fetch_data_status='pending'
    - Calls AI analysis service to get anomaly predictions
    - Updates flight logs with predictions or decrements fetch_count
    - Sets remaining flights to NORMAL when fetch_count is exhausted
    
    Args:
        limit: Maximum number of flight logs to process per run (default: 10)
    
    Returns:
        dict: Status and count of processed records
    """
    try:
        from flight_log.services.flight_log_service import FlightLogService
        
        logger.info("🔄 Starting anomaly prediction update task...")
        
        # Count pending before processing
        pending_count = FlightLog.objects.filter(fetch_anomaly_status='pending').count()
        
        if pending_count == 0:
            logger.info("✅ No pending flight logs to process for anomaly predictions")
            return {"status": "success", "message": "No pending flight logs", "processed": 0}
        
        logger.info(f"📋 Found {pending_count} pending flight logs, processing up to {limit}")
        
        # Call the service method
        FlightLogService.update_pending_anomaly_predictions(limit=limit)
        
        # Count remaining pending
        remaining_count = FlightLog.objects.filter(fetch_anomaly_status='pending').count()
        processed = pending_count - remaining_count
        
        logger.info(f"✅ Anomaly prediction update complete. Processed: {processed}, Remaining: {remaining_count}")
        
        return {
            "status": "success",
            "processed": processed,
            "remaining": remaining_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error in anomaly prediction update task: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
