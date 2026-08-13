"""
Helper functions for handover operations
"""
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


def _send_handover_download_notification(username: str, download_type: str, status: str, message: str, task_id: str = None, data: dict = None):
    """
    Send WebSocket notification to user about handover download status
    Format giống logic cũ: {status, url, name_file, result_id, page}
    
    Args:
        username: Username of the user to notify
        download_type: 'handover_management', 'notice', hoặc 'completed_notice'
        status: 'pending', 'processing', 'DONE', or 'failed'
        message: Notification message
        task_id: Optional task ID for tracking
        data: Additional data (download_url, filename, file_id, etc.)
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("Channel layer not configured - notifications disabled")
            return
        
        # Map status to format cũ: 'success' -> 'DONE'
        status_mapped = 'DONE' if status == 'success' else status.upper()
        
        # Xác định page name dựa vào download_type
        # download_type có thể là: 'handover_management', 'notice', 'completed_notice'
        if download_type == 'handover_management':
            page_name = 'handover_management'
        elif download_type == 'completed_notice':
            page_name = 'completed_notice'
        else:  # 'notice'
            page_name = 'handover_notice'
        
        # Build event theo format cũ
        event = {
            'type': 'handover_download_notification',
            'status': status_mapped,
            'page': page_name,
        }
        
        # Nếu có data (success case), thêm các field theo format cũ
        if data:
            # url: relative path từ file_url (không có protocol và endpoint)
            file_url = data.get('download_url', '')
            if file_url:
                # Extract relative path từ full URL
                # Ví dụ: http://192.168.0.200:30090/media/exports/file.csv -> /media/exports/file.csv
                from django.conf import settings
                protocol = 'https' if settings.MINIO_USE_HTTPS else 'http'
                full_prefix = f'{protocol}://{settings.MINIO_ENDPOINT}'
                if file_url.startswith(full_prefix):
                    event['url'] = file_url[len(full_prefix):]
                else:
                    # Nếu không match, lấy từ file_url của uploaded_file
                    event['url'] = data.get('file_url', file_url)
            else:
                event['url'] = data.get('file_url', '')
            
            # name_file: filename
            event['name_file'] = data.get('filename', '')
            
            # result_id: file_id
            event['result_id'] = data.get('file_id', None)
        else:
            # Pending/processing/failed case
            event['url'] = ''
            event['name_file'] = ''
            event['result_id'] = None
        
        # Thêm các field khác để backward compatibility
        event['notification_type'] = f'handover_{download_type}_download'
        event['download_type'] = download_type
        event['message'] = message
        event['timestamp'] = timezone.now().isoformat()
        
        if task_id:
            event['task_id'] = task_id
        
        async_to_sync(channel_layer.group_send)(f'handover_{username}', event)
        logger.info(f"📤 Sent handover download notification to user {username}: {status_mapped}")
        
    except Exception as e:
        logger.error(f"❌ Error sending handover download notification: {str(e)}")

