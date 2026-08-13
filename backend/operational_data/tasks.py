from celery import shared_task
from typing import List
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
import logging
from core.middleware.refresh_token import get_current_request
from core.user.models import CoreUser

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_upload_queue_task(self, upload_type: str, device_type: str):
    """
    Background task to process upload queue sequentially
    
    Args:
        upload_type: Type of upload ('video', 'log')
        device_type: Device type ('drone', 'robot')
    """
    try:
        from operational_data.services.operational_data_service import OperationalDataService
        
        logger.info(f"🔄 Starting queue processor task for {device_type} {upload_type} uploads - Task ID: {self.request.id}")
        
        # Process the queue
        OperationalDataService.process_upload_queue(upload_type, device_type)
        
        logger.info(f"✅ Queue processor task completed for {device_type} {upload_type} uploads")
        
        return {'status': 'completed', 'upload_type': upload_type, 'device_type': device_type}
        
    except Exception as e:
        logger.error(f"❌ Error in queue processor task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


def _send_upload_notification(username: str, order_item_id: int, device_type: str, status: str, message: str, task_id: str, data: dict = None):
    """
    Send WebSocket notification to user about upload status
    
    Args:
        user_id: ID of the user to notify
        order_item_id: ID of the order item
        device_type: 'drone' or 'robot'
        status: 'success', 'failed', or 'partial_success'
        message: Notification message
        data: Additional data to include in notification
    """
    try:
        print(f"Sending upload notification to user {username} for order item {order_item_id} with device type {device_type} and status {status}")
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("Channel layer not configured - notifications disabled")
            return
        
        # Prepare notification event
        event = {
            'type': 'operational_video_upload_notification',
            'notification_type': 'operational_video_upload',
            'order_item_id': order_item_id,
            'device_type': device_type,
            'status': status,
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'task_id': task_id,
            'data': data or {}
        }
        
        # Send to operational data user-specific group
        async_to_sync(channel_layer.group_send)(f'operational_data_{username}', event)
    
    except Exception as e:
        logger.error(f"❌ Error get channel layer: {str(e)}")


# Import timezone for notifications
from django.utils import timezone


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def upload_operational_log_drone_task(self, order_item_id: int, file_data_list: List[dict], user_id: int):
    """
    Background task to upload drone operational log files to S3
    
    Args:
        order_item_id: ID of the order item
        file_data_list: List of file data dictionaries containing file content and metadata
        user_id: ID of the user who initiated the upload
    """
    try:
        from operational_data.models import OperationalData
        from delivery.models import DeliveryOperationItem
        from orders.models import OrderItem
        from core.file_management.helper import FileHelper
        from ninja.files import UploadedFile
        from django.core.files.uploadedfile import InMemoryUploadedFile
        from io import BytesIO
        
        logger.info(f"🔄 Starting drone log upload task for order_item {order_item_id} - Task ID: {self.request.id}")
        
        # Get user and order item
        try:
            user = CoreUser._base_manager.get(id=user_id)
            order_item = OrderItem.objects.get(id=order_item_id)
            delivery_operation_item = DeliveryOperationItem.objects.filter(order_item=order_item).first()
            
            if not delivery_operation_item:
                raise Exception("Delivery operation item not found")
                
        except (CoreUser.DoesNotExist, OrderItem.DoesNotExist) as e:
            logger.error(f"❌ Error getting user or order item: {str(e)}")
            # Try to get username for notification, but don't fail if we can't
            try:
                user = CoreUser._base_manager.get(id=user_id)
                _send_upload_log_notification(user.username, order_item_id, 'drone', 'failed', str(e))
            except:
                logger.error(f"❌ Could not send notification - user {user_id} not found")
            return
        
        # Delete old operational data
        OperationalData.objects.filter(
            operation_item=delivery_operation_item, 
            operation_item_type='log', 
            device_type='drone'
        ).delete()
        
        uploaded_files = []
        failed_files = []
        
        # Process each file
        for file_data in file_data_list:
            try:
                # Recreate file object from data
                file_content = file_data['content']
                file_name = file_data['name']
                content_type = file_data.get('content_type', 'text/plain')
                
                # Create InMemoryUploadedFile object
                file_obj = InMemoryUploadedFile(
                    file=BytesIO(file_content),
                    field_name='file',
                    name=file_name,
                    content_type=content_type,
                    size=len(file_content),
                    charset=None
                )
                
                # Upload to S3
                uploaded_file = FileHelper.user_upload_s3(user, file_obj, is_avatar=False, only_image=False)
                
                # Create operational data record
                operational_data = OperationalData.objects.create(
                    operation_item=delivery_operation_item,
                    operation_item_type='log',
                    device_type='drone',
                    media_file=uploaded_file
                )
                
                uploaded_files.append({
                    'file_name': file_name,
                    'file_id': uploaded_file.id,
                    'operational_data_id': operational_data.id
                })
                
                logger.info(f"✅ Successfully uploaded drone log file: {file_name}")
                
            except Exception as e:
                logger.error(f"❌ Error uploading file {file_data.get('name', 'unknown')}: {str(e)}")
                failed_files.append({
                    'file_name': file_data.get('name', 'unknown'),
                    'error': str(e)
                })
        
        # Send notification
        if failed_files:
            message = f"Log upload completed with {len(uploaded_files)} successful and {len(failed_files)} failed files"
            _send_upload_log_notification(user.username, order_item_id, 'drone', 'partial_success', message)
        else:
            message = f"Successfully uploaded {len(uploaded_files)} drone log files"
            _send_upload_log_notification(user.username, order_item_id, 'drone', 'success', message)
        
        logger.info(f"✅ Drone log upload task completed for order_item {order_item_id}")
        return {
            'status': 'completed',
            'uploaded_files': len(uploaded_files),
            'failed_files': len(failed_files)
        }
        
    except Exception as e:
        logger.error(f"❌ Error in drone log upload task for order_item {order_item_id}: {str(e)}")
        try:
            user = CoreUser._base_manager.get(id=user_id)
            _send_upload_log_notification(user.username, order_item_id, 'drone', 'failed', str(e))
        except:
            pass
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {'status': 'failed', 'error': str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def upload_operational_log_robot_task(self, order_item_id: int, file_data_list: List[dict], user_id: int):
    """
    Background task to upload robot operational log files to S3
    
    Args:
        order_item_id: ID of the order item
        file_data_list: List of file data dictionaries containing file content and metadata
        user_id: ID of the user who initiated the upload
    """
    try:
        from operational_data.models import OperationalData
        from delivery.models import DeliveryOperationItem
        from orders.models import OrderItem
        from core.file_management.helper import FileHelper
        from ninja.files import UploadedFile
        from django.core.files.uploadedfile import InMemoryUploadedFile
        from io import BytesIO
        
        logger.info(f"🔄 Starting robot log upload task for order_item {order_item_id} - Task ID: {self.request.id}")
        
        # Get user and order item
        try:
            user = CoreUser._base_manager.get(id=user_id)
            order_item = OrderItem.objects.get(id=order_item_id)
            delivery_operation_item = DeliveryOperationItem.objects.filter(order_item=order_item).first()
            
            if not delivery_operation_item:
                raise Exception("Delivery operation item not found")
                
        except (CoreUser.DoesNotExist, OrderItem.DoesNotExist) as e:
            logger.error(f"❌ Error getting user or order item: {str(e)}")
            # Try to get username for notification, but don't fail if we can't
            try:
                user = CoreUser._base_manager.get(id=user_id)
                _send_upload_log_notification(user.username, order_item_id, 'robot', 'failed', str(e))
            except:
                logger.error(f"❌ Could not send notification - user {user_id} not found")
            return
        
        # Delete old operational data
        OperationalData.objects.filter(
            operation_item=delivery_operation_item, 
            operation_item_type='log', 
            device_type='robot'
        ).delete()
        
        uploaded_files = []
        failed_files = []
        
        # Process each file
        for file_data in file_data_list:
            try:
                # Recreate file object from data
                file_content = file_data['content']
                file_name = file_data['name']
                content_type = file_data.get('content_type', 'text/plain')
                
                # Create InMemoryUploadedFile object
                file_obj = InMemoryUploadedFile(
                    file=BytesIO(file_content),
                    field_name='file',
                    name=file_name,
                    content_type=content_type,
                    size=len(file_content),
                    charset=None
                )
                
                # Upload to S3
                uploaded_file = FileHelper.user_upload_s3(user, file_obj, is_avatar=False, only_image=False)
                
                # Create operational data record
                operational_data = OperationalData.objects.create(
                    operation_item=delivery_operation_item,
                    operation_item_type='log',
                    device_type='robot',
                    media_file=uploaded_file
                )
                
                uploaded_files.append({
                    'file_name': file_name,
                    'file_id': uploaded_file.id,
                    'operational_data_id': operational_data.id
                })
                
                logger.info(f"✅ Successfully uploaded robot log file: {file_name}")
                
            except Exception as e:
                logger.error(f"❌ Error uploading file {file_data.get('name', 'unknown')}: {str(e)}")
                failed_files.append({
                    'file_name': file_data.get('name', 'unknown'),
                    'error': str(e)
                })
        
        # Send notification
        if failed_files:
            message = f"Log upload completed with {len(uploaded_files)} successful and {len(failed_files)} failed files"
            _send_upload_log_notification(user.username, order_item_id, 'robot', 'partial_success', message, {
                'uploaded_files': uploaded_files,
                'failed_files': failed_files
            })
        else:
            message = f"Successfully uploaded {len(uploaded_files)} robot log files"
            _send_upload_log_notification(user.username, order_item_id, 'robot', 'success', message, {
                'uploaded_files': uploaded_files
            })
        
        logger.info(f"✅ Robot log upload task completed for order_item {order_item_id}")
        return {
            'status': 'completed',
            'uploaded_files': len(uploaded_files),
            'failed_files': len(failed_files)
        }
        
    except Exception as e:
        logger.error(f"❌ Error in robot log upload task for order_item {order_item_id}: {str(e)}")
        try:
            user = CoreUser._base_manager.get(id=user_id)
            _send_upload_log_notification(user.username, order_item_id, 'robot', 'failed', str(e))
        except:
            pass
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {'status': 'failed', 'error': str(e)}


def _send_upload_log_notification(username: str, order_item_id: int, device_type: str, status: str, message: str, data: dict = None):
    """
    Send WebSocket notification to user about log upload status
    
    Args:
        username: Username of the user to notify
        order_item_id: ID of the order item
        device_type: 'drone' or 'robot'
        status: 'success', 'failed', or 'partial_success'
        message: Notification message
        data: Additional data to include in notification
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("Channel layer not configured - notifications disabled")
            return
        
        # Prepare notification event
        event = {
            'type': 'operational_log_upload_notification',
            'notification_type': 'operational_log_upload',
            'order_item_id': order_item_id,
            'device_type': device_type,
            'status': status,
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'data': data or {}
        }
        
        # Send to operational data user-specific group
        async_to_sync(channel_layer.group_send)(f'operational_data_{username}', event)
        
    except Exception as e:
        logger.error(f"❌ Error sending log upload notification: {str(e)}")
