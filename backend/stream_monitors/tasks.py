from celery import shared_task
from django.utils import timezone
import logging
import asyncio

logger = logging.getLogger(__name__)

@shared_task
def auto_stop_record(stream_monitor_id: str, record_id: str):
    """
    Celery task to automatically stop a recording after timeout.
    This task is scheduled when start_record is called and cancelled if stop_record is called manually.
    """
    try:
        from stream_monitors.models import StreamMonitorRecord
        from stream_monitors.services.stream_monitor_services import StreamMonitorService
        
        logger.info(f"🔄 Auto-stop task triggered for record {record_id}")
        
        # Check if record still exists and is still running
        try:
            record_instance = StreamMonitorRecord.objects.get(id=record_id)
        except StreamMonitorRecord.DoesNotExist:
            logger.warning(f"⚠️ Record {record_id} not found, auto-stop task cancelled")
            return {"status": "cancelled", "reason": "record_not_found"}
        
        # Only auto-stop if record is still in running status
        if record_instance.status != 'running':
            logger.info(f"📋 Record {record_id} is no longer running (status: {record_instance.status}), auto-stop task cancelled")
            return {"status": "cancelled", "reason": f"record_status_{record_instance.status}"}
        
        logger.info(f"⏰ Auto-stopping record {record_id} after timeout")
        
        # Call the stop_record method (async)
        result = asyncio.run(StreamMonitorService.stop_record(stream_monitor_id, record_id))
        
        if result:
            logger.info(f"✅ Successfully auto-stopped record {record_id}")
            return {"status": "success", "object_path": result}
        else:
            logger.error(f"❌ Failed to auto-stop record {record_id}")
            return {"status": "error", "reason": "stop_failed"}
            
    except Exception as e:
        logger.error(f"❌ Error in auto-stop task for record {record_id}: {str(e)}")
        return {"status": "error", "reason": str(e)}
