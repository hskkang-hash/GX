import os
import tempfile
import zipfile
import pandas as pd
import threading
import uuid
import base64
import logging
import json
from django.http import HttpResponse
from django.conf import settings
import re
from datetime import datetime
from typing import List
from ninja.files import UploadedFile
from django.db import transaction
from django.db.models import F, OuterRef, Subquery, Value, CharField, Case, When, DateTimeField, ExpressionWrapper, Max
from django.db.models.functions import Coalesce, Concat, Cast, LPad, Replace
from django.contrib.postgres.fields import JSONField
from django.db.models import JSONField as DjangoJSONField
import requests

from operational_data.models import OperationalData
from delivery.models import DeliveryOperation, DeliveryOperationItem
from operational_data.models import OperationalDataUploadStatus
from orders.models import OrderHistory, OrderItem
from core.file_management.helper import FileHelper
from core.middleware.refresh_token import get_current_request
from operational_data.services.operational_helper import JSONExtractText, JSONExtractDateTime
from operational_data.tasks import upload_operational_log_drone_task
from operational_data.tasks import upload_operational_log_robot_task
from operational_data.tasks import process_upload_queue_task

from core.user.models import CoreUser
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
from operational_data.tasks import _send_upload_notification, _send_upload_log_notification
from common.constant import MESSAGE_ENUM, get_message


class OperationalDataService:
    @staticmethod
    @transaction.atomic
    def get_operational_data():
        try:
            operations = DeliveryOperation.objects.filter(current_status__code__in=["delivered", "completed_order", "arrived_order"], created_by__userprofilelink__group__code__in=["group_etri", "etri"])
            order_items = OrderItem.objects.filter(order__delivery_operation__in=operations)
            # for each order_item, if not exist in DeliveryOperationItem, create a new DeliveryOperationItem
            for order_item in order_items:
                if not DeliveryOperationItem._base_manager.filter(order_item=order_item).exists():
                    operation = DeliveryOperation.objects.filter(order=order_item.order).first()
                    DeliveryOperationItem.objects.create(order_item=order_item, delivery_operation=operation, created_by=operation.created_by, is_arrived=True)
            operation_data = order_items.select_related(
                'order__recipient_address',
                'order',
                'item_type'
            ).annotate(
                # Try different JSON access methods
                delivery_operation_code=Cast(
                    JSONExtractText(F("order__another_info__etri"), "tracking_number"),
                    output_field=CharField(),
                ),
                delivery_point=Cast(
                    JSONExtractText(F("order__another_info__etri__send_data"), "RECEIVER_ADDRESS"),
                    output_field=CharField(),
                ),
                # item_type=F('item_type__name'),
                item_type_code=F('item_type__code'),
                # Add the raw weight field for processing in the schema
                item_weight=Case(
                    When(
                        weight__isnull=False,
                        then=Replace(
                            Concat(
                                Coalesce(Cast(F('weight__value'), CharField()), Value('0')),
                                Value(' '),
                                Coalesce(Cast(F('weight__unit'), CharField()), Value('kg')),
                                output_field=CharField()
                            ),
                            Value('"'),
                            Value(''),
                            output_field=CharField()
                        )
                    ),
                    default=Value('N/A'),
                    output_field=CharField()
                ),
                # Add another_info for receipt_id access - using proper JSON field syntax
                route=Cast(
                    JSONExtractText(F("order__another_info__etri__receive_data"), "ROUTE_NAME"),
                    output_field=CharField(),
                ),
                delivered_at=Subquery(
                    OrderHistory._base_manager.filter(
                        order_id=OuterRef('order_id'),
                        action='delivered'
                    ).values('created_on')[:1]
                ),
                delivery_operation__created_on=JSONExtractDateTime(F("order__another_info__etri"), "sent_to_etri_at"),
            )
            
            return operation_data
        except OrderItem.DoesNotExist:
            return None
        
    @staticmethod
    @transaction.atomic
    def get_operational_data_detail(order_item_id: int):
        try:
            operation_data = OrderItem.objects.select_related(
                'order__recipient_address',
                'order',
                'item_type'
            ).annotate(
                delivery_operation_code=Cast(
                    JSONExtractText(F("order__another_info__etri"), "tracking_number"),
                    output_field=CharField(),
                ),
                delivery_point=F('order__another_info__etri__send_data__RECEIVER_ADDRESS'),
                # Format weight using database annotations
                item_weight=Case(
                    When(
                        weight__isnull=False,
                        then=Replace(
                            Concat(
                                Coalesce(Cast(F('weight__value'), CharField()), Value('0')),
                                Value(' '),
                                Coalesce(Cast(F('weight__unit'), CharField()), Value('kg')),
                                output_field=CharField()
                            ),
                            Value('"'),
                            Value(''),
                            output_field=CharField()
                        )
                    ),
                    default=Value('N/A'),
                    output_field=CharField()
                ),
                # Add another_info for receipt_id access - using proper JSON field syntax
                route=Cast(
                    JSONExtractText(F("order__another_info__etri__receive_data"), "ROUTE_NAME"),
                    output_field=CharField(),
                ),
                delivered_at=Subquery(
                    OrderHistory._base_manager.filter(
                        order_id=OuterRef('order_id'),
                        action='delivered'
                    ).values('created_on')[:1]
                ),
                receipt_id=F('order__another_info__etri__receive_data__RECEIPT_ID'),
                route_terminals_drone=F('order__another_info__etri__receive_data__DRONE_PATH'),
                route_terminals_robot=F('order__another_info__etri__receive_data__ROBOT_PATH'),
                delivery_operation__created_on=JSONExtractDateTime(F("order__another_info__etri"), "sent_to_etri_at"),
            ).get(id=order_item_id)
            
            return operation_data
        except OrderItem.DoesNotExist:
            return None
        
    @staticmethod
    def upload_operational_log_drone(order_item_id: int, files: List[UploadedFile]):
        """
        Add drone log upload to queue for sequential processing
        Returns immediately with task ID and upload status record
        """
        try:
            # Get current user and order item
            request = get_current_request()
            user = request.user
            order_item = OrderItem.objects.get(id=order_item_id)
            
            # Prepare file data for queue storage
            file_data_list = []
            for file in files:
                # Read file content into memory and encode as base64 for JSON storage
                file_content = file.read()
                file_data = {
                    'content': base64.b64encode(file_content).decode('utf-8'),
                    'name': file.name,
                    'content_type': getattr(file, 'content_type', 'text/plain'),
                    'size': len(file_content)
                }
                file_data_list.append(file_data)
            
            # Generate unique task ID
            task_id = str(uuid.uuid4())
            
            # Get next queue position
            max_position = OperationalDataUploadStatus.objects.filter(
                upload_type='log',
                device_type='drone',
                status='queued'
            ).aggregate(Max('queue_position'))['queue_position__max'] or 0
            
            # Create upload status record in queue
            upload_status = OperationalDataUploadStatus.objects.create(
                order_item=order_item,
                user=user,
                task_id=task_id,
                upload_type='log',
                device_type='drone',
                status='queued',
                total_files=len(file_data_list),
                queue_position=max_position + 1,
                file_data=file_data_list,
                message='Log upload added to queue'
            )
            
            # Start queue processor if no active uploads
            OperationalDataService._start_queue_processor_if_needed('log', 'drone')
            
            return {
                'success': True,
                'task_id': task_id,
                'upload_status_id': upload_status.id,
                'message': f'Log upload added to queue at position {upload_status.queue_position}',
                'total_files': len(file_data_list),
                'queue_position': upload_status.queue_position
            }
            
        except OrderItem.DoesNotExist:
            return {
                'success': False,
                'error': 'Order item not found',
                'message': 'Failed to queue log upload task - order item not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to queue log upload task'
            }
        
    @staticmethod
    def upload_operational_log_robot(order_item_id: int, files: List[UploadedFile]):
        """
        Add robot log upload to queue for sequential processing
        Returns immediately with task ID and upload status record
        """
        try:            
            # Get current user and order item
            request = get_current_request()
            user = request.user
            order_item = OrderItem.objects.get(id=order_item_id)
            
            # Prepare file data for queue storage
            file_data_list = []
            for file in files:
                # Read file content into memory and encode as base64 for JSON storage
                file_content = file.read()
                file_data = {
                    'content': base64.b64encode(file_content).decode('utf-8'),
                    'name': file.name,
                    'content_type': getattr(file, 'content_type', 'text/plain'),
                    'size': len(file_content)
                }
                file_data_list.append(file_data)
            
            # Generate unique task ID
            task_id = str(uuid.uuid4())
            
            # Get next queue position
            max_position = OperationalDataUploadStatus.objects.filter(
                upload_type='log',
                device_type='robot',
                status='queued'
            ).aggregate(Max('queue_position'))['queue_position__max'] or 0
            
            # Create upload status record in queue
            upload_status = OperationalDataUploadStatus.objects.create(
                order_item=order_item,
                user=user,
                task_id=task_id,
                upload_type='log',
                device_type='robot',
                status='queued',
                total_files=len(file_data_list),
                queue_position=max_position + 1,
                file_data=file_data_list,
                message='Log upload added to queue'
            )
            
            # Start queue processor if no active uploads
            OperationalDataService._start_queue_processor_if_needed('log', 'robot')
            
            return {
                'success': True,
                'task_id': task_id,
                'upload_status_id': upload_status.id,
                'message': f'Log upload added to queue at position {upload_status.queue_position}',
                'total_files': len(file_data_list),
                'queue_position': upload_status.queue_position
            }
            
        except OrderItem.DoesNotExist:
            return {
                'success': False,
                'error': 'Order item not found',
                'message': 'Failed to queue log upload task - order item not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to queue log upload task'
            }
        
    @staticmethod
    def upload_operational_video_drone(order_item_id: int, files: List[UploadedFile]):
        """
        Add drone video upload to queue for sequential processing
        Returns immediately with task ID and upload status record
        """
        try:            
            # Get current user and order item
            request = get_current_request()
            user = request.user
            order_item = OrderItem.objects.get(id=order_item_id)
            
            # Prepare file data for queue storage
            file_data_list = []
            for file in files:
                # Read file content into memory and encode as base64 for JSON storage
                file_content = file.read()
                file_data = {
                    'content': base64.b64encode(file_content).decode('utf-8'),
                    'name': file.name,
                    'content_type': getattr(file, 'content_type', 'video/mp4'),
                    'size': len(file_content)
                }
                file_data_list.append(file_data)
            
            # Generate unique task ID
            task_id = str(uuid.uuid4())
            
            # Get next queue position
            max_position = OperationalDataUploadStatus.objects.filter(
                upload_type='video',
                device_type='drone',
                status='queued'
            ).aggregate(Max('queue_position'))['queue_position__max'] or 0
            
            # Create upload status record in queue
            upload_status = OperationalDataUploadStatus.objects.create(
                order_item=order_item,
                user=user,
                task_id=task_id,
                upload_type='video',
                device_type='drone',
                status='queued',
                total_files=len(file_data_list),
                queue_position=max_position + 1,
                file_data=file_data_list,
                message='Video upload added to queue'
            )
            
            # Start queue processor if no active uploads
            OperationalDataService._start_queue_processor_if_needed('video', 'drone')
            
            return {
                'success': True,
                'task_id': task_id,
                'upload_status_id': upload_status.id,
                'message': f'Video upload added to queue at position {upload_status.queue_position}',
                'total_files': len(file_data_list),
                'queue_position': upload_status.queue_position
            }
            
        except OrderItem.DoesNotExist:
            return {
                'success': False,
                'error': 'Order item not found',
                'message': 'Failed to queue video upload task - order item not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to queue video upload task'
            }
        
    @staticmethod
    def upload_operational_video_robot(order_item_id: int, files: List[UploadedFile]):
        """
        Add robot video upload to queue for sequential processing
        Returns immediately with task ID and upload status record
        """
        try:
            # Get current user and order item
            request = get_current_request()
            user = request.user
            order_item = OrderItem.objects.get(id=order_item_id)
            
            # Prepare file data for queue storage
            file_data_list = []
            for file in files:
                # Read file content into memory and encode as base64 for JSON storage
                file_content = file.read()
                file_data = {
                    'content': base64.b64encode(file_content).decode('utf-8'),
                    'name': file.name,
                    'content_type': getattr(file, 'content_type', 'video/mp4'),
                    'size': len(file_content)
                }
                file_data_list.append(file_data)
            
            # Generate unique task ID
            task_id = str(uuid.uuid4())
            
            # Get next queue position
            max_position = OperationalDataUploadStatus.objects.filter(
                upload_type='video',
                device_type='robot',
                status='queued'
            ).aggregate(Max('queue_position'))['queue_position__max'] or 0
            
            # Create upload status record in queue
            upload_status = OperationalDataUploadStatus.objects.create(
                order_item=order_item,
                user=user,
                task_id=task_id,
                upload_type='video',
                device_type='robot',
                status='queued',
                total_files=len(file_data_list),
                queue_position=max_position + 1,
                file_data=file_data_list,
                message='Video upload added to queue'
            )
            
            # Start queue processor if no active uploads
            OperationalDataService._start_queue_processor_if_needed('video', 'robot')
            
            return {
                'success': True,
                'task_id': task_id,
                'upload_status_id': upload_status.id,
                'message': f'Video upload added to queue at position {upload_status.queue_position}',
                'total_files': len(file_data_list),
                'queue_position': upload_status.queue_position
            }
            
        except OrderItem.DoesNotExist:
            return {
                'success': False,
                'error': 'Order item not found',
                'message': 'Failed to queue video upload task - order item not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to queue video upload task'
            }
        
    @staticmethod
    def download_operational_log(order_item_id: int, device_type: str):
        """
        Queue operational log download as background thread with WebSocket notifications
        Returns immediately with download status information
        """
        try:
            # Get current user
            request = get_current_request()
            user = request.user
            
            # Get order item and validate
            order_item = OrderItem._base_manager.get(id=order_item_id)
            delivery_operation_item = DeliveryOperationItem._base_manager.filter(order_item=order_item).first()
            
            # Validate that operational log data exists
            if not OperationalData.objects.filter(
                operation_item_id=delivery_operation_item, 
                operation_item_type='log', 
                device_type=device_type
            ).exists():
                return {
                    'success': False,
                    'error': 'No operational log data found',
                    'message': f'No {device_type} log data found for the specified order item'
                }
            
            # Generate unique task ID for download tracking
            download_task_id = str(uuid.uuid4())
            
            # Create download status record
            download_status = OperationalDataUploadStatus.objects.create(
                order_item=order_item,
                user=user,
                task_id=download_task_id,
                upload_type='log_download',  # Specific type for log downloads
                device_type=device_type,     # drone or robot
                status='pending',
                total_files=1,  # Single log download
                message=f'{device_type.title()} log download queued for background processing'
            )
            
            # Send initial notification
            OperationalDataService._send_log_download_notification(
                user.username, 
                order_item_id, 
                device_type,
                'pending', 
                f'{device_type.title()} log download request received and queued for processing'
            )
            
            # Start background thread for download processing
            download_thread = threading.Thread(
                target=OperationalDataService._process_log_download_in_thread,
                args=(order_item_id, device_type, download_task_id, user.id),
                daemon=True
            )
            download_thread.start()
            
            return {
                'success': True,
                'download_task_id': download_task_id,
                'download_status_id': download_status.id,
                'message': f'{device_type.title()} log download queued for background processing',
                'device_type': device_type,
                'order_item_id': order_item_id
            }
            
        except OrderItem.DoesNotExist:
            return {
                'success': False,
                'error': 'Order item not found',
                'message': 'Failed to queue log download task - order item not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to queue log download task'
            }

    @staticmethod
    def _process_log_download_in_thread(order_item_id: int, device_type: str, download_task_id: str, user_id: int):
        """
        Process log download in background thread with WebSocket notifications
        """
        download_status = None
        temp_files_to_cleanup = []
        
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"🔄 Starting {device_type} log download processing for task {download_task_id}")
            
            # Get download status record and user
            download_status = OperationalDataUploadStatus.objects.get(task_id=download_task_id)
            user = CoreUser.objects.get(id=user_id)
            
            # Update status to processing and send notification
            download_status.status = 'processing'
            download_status.message = f'Processing {device_type} log download...'
            download_status.save()
            
            OperationalDataService._send_log_download_notification(
                user.username, 
                order_item_id, 
                device_type,
                'processing', 
                f'{device_type.title()} log download processing started...'
            )
            
            # Get delivery operation item for naming
            order_item = OrderItem.objects.get(id=order_item_id)
            delivery_operation_item = DeliveryOperationItem.objects.filter(order_item=order_item).first()
            
            # Get all operational data files
            operational_data_list = OperationalData.objects.filter(
                operation_item_id=delivery_operation_item, 
                operation_item_type='log', 
                device_type=device_type
            ).select_related('media_file')
            
            if not operational_data_list.exists():
                raise Exception(f"No {device_type} log data found")
            
            # Create a temporary zip file
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_files_to_cleanup = [temp_zip.name]
            files_added = 0
            
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for operational_data in operational_data_list:
                    media_file = operational_data.media_file
                    if media_file:
                        try:
                            # Get the file content from the file field or URL
                            file_content = None
                            file_extension = getattr(media_file, 'file_extension', '')
                            original_filename = getattr(media_file, 'file_name', None) or f"operational_log_{operational_data.id}{file_extension}"
                            
                            # If direct file access failed, try URL approach
                            if hasattr(media_file, 'file_url') and media_file.file_url:
                                try:
                                    response = requests.get(media_file.file_url, timeout=30)
                                    if response.status_code == 200:
                                        file_content = response.content
                                except Exception as e:
                                    logger.error(f"Error fetching file from URL: {str(e)}")
                            
                            # Add file to zip if we got content
                            if file_content:
                                # Convert .log files to CSV
                                if file_extension.lower() == '.log':
                                    try:
                                        # Convert log content to CSV
                                        csv_content, csv_filename = OperationalDataService._convert_log_to_csv(
                                            file_content, original_filename
                                        )
                                        zip_file.writestr(csv_filename, csv_content)
                                        files_added += 1
                                    except Exception as e:
                                        logger.error(f"Error converting log file to CSV: {str(e)}")
                                        # Fall back to original file if conversion fails
                                        zip_file.writestr(original_filename, file_content)
                                        files_added += 1
                                else:
                                    # Add original file for non-log files
                                    zip_file.writestr(original_filename, file_content)
                                    files_added += 1
                            else:
                                logger.warning(f"Could not retrieve content for file {media_file.id}")
                                
                        except Exception as e:
                            # Log error but continue with other files
                            logger.error(f"Error adding file {media_file.id} to zip: {str(e)}")
                            continue
            
            # Check if any files were added to the zip
            if files_added == 0:
                raise Exception(f"No {device_type} log files could be retrieved")
            
            # Generate zip filename
            operation_code = f"operational_logs_{device_type}_{order_item_id}"
            if hasattr(delivery_operation_item, 'delivery_operation') and delivery_operation_item.delivery_operation:
                if hasattr(delivery_operation_item.delivery_operation, 'order') and delivery_operation_item.delivery_operation.order:
                    operation_code = f"operational_logs_{device_type}_{delivery_operation_item.delivery_operation.order.order_code}"
            
            zip_filename = f"{operation_code}.zip"
            
            # Upload the zip file to S3 for download
            with open(temp_zip.name, 'rb') as zip_file_content:
                zip_content = zip_file_content.read()
                
                file_obj = InMemoryUploadedFile(
                    file=BytesIO(zip_content),
                    field_name='file',
                    name=zip_filename,
                    content_type='application/zip',
                    size=len(zip_content),
                    charset=None
                )
                
                # Upload to S3
                uploaded_file = FileHelper.user_upload_s3(user, file_obj, is_avatar=False, only_image=False)
                
                # Update download status with success
                success_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS)
                download_status.status = 'success'
                download_status.message = success_message
                download_status.uploaded_files = 1  # Mark as completed
                download_status.completed_at = timezone.now()
                download_status.error_details = {
                    'download_url': uploaded_file.file_url if hasattr(uploaded_file, 'file_url') else None,
                    'file_id': uploaded_file.id,
                    'filename': zip_filename,
                    'files_count': files_added
                }
                download_status.donwload_url = f'https://{settings.MINIO_ENDPOINT}{uploaded_file.file_url}' if hasattr(uploaded_file, 'file_url') else None
                download_status.save()
                
                # Send success notification with download URL
                OperationalDataService._send_log_download_notification(
                    user.username, 
                    order_item_id, 
                    device_type,
                    'success', 
                    success_message,
                    {
                        'download_url': f'https://{settings.MINIO_ENDPOINT}{uploaded_file.file_url}' if hasattr(uploaded_file, 'file_url') else None,
                        'filename': zip_filename,
                        'file_id': uploaded_file.id,
                        'files_count': files_added
                    }
                )
                
                logger.info(f"✅ {device_type.title()} log download processing completed for task {download_task_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in {device_type} log download processing for task {download_task_id}: {str(e)}")
            
            # Update download status on error
            if download_status:
                error_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED)
                download_status.status = 'failed'
                download_status.message = error_message
                download_status.error_details = {'error': str(e)}
                download_status.completed_at = timezone.now()
                download_status.save()
                
                # Send failure notification
                try:
                    user = CoreUser.objects.get(id=user_id)
                    OperationalDataService._send_log_download_notification(
                        user.username, 
                        order_item_id, 
                        device_type,
                        'failed', 
                        error_message,
                        {'error': str(e)}
                    )
                except:
                    pass
        
        finally:
            # Clean up all temporary files
            for temp_file in temp_files_to_cleanup:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except Exception as e:
                        logger.error(f"Error cleaning up temp file {temp_file}: {str(e)}")
        
    @staticmethod
    def download_operational_data(list_order_item_id: List[int]):
        """
        Queue operational data download as background thread with WebSocket notifications
        Returns immediately with download status information
        """
        try:
            # Get current user
            request = get_current_request()
            user = request.user
            
            # Validate that at least one order item has operational data
            if not OperationalData.objects.filter(operation_item__order_item_id__in=list_order_item_id).exists():
                return {
                    'success': False,
                    'error': 'No operational data found',
                    'message': 'No operational data found for the specified order items'
                }
            
            # Generate unique task ID for download tracking
            download_task_id = str(uuid.uuid4())
            
            # Create download status record (using first order item for reference)
            first_order_item = OrderItem.objects.filter(id__in=list_order_item_id).first()
            download_status = OperationalDataUploadStatus.objects.create(
                order_item=first_order_item,
                user=user,
                task_id=download_task_id,
                upload_type='download',  # We'll use this for download tracking
                device_type='bulk',     # Indicate this is a bulk operation
                status='pending',
                total_files=len(list_order_item_id),  # Number of order items to process
                message='Download queued for background processing'
            )
            
            # Send initial notification
            OperationalDataService._send_download_notification(
                user.username, 
                list_order_item_id, 
                'pending', 
                'Download request received and queued for processing'
            )
            
            # Start background thread for download processing
            download_thread = threading.Thread(
                target=OperationalDataService._process_download_in_thread,
                args=(list_order_item_id, download_task_id, user.id),
                daemon=True
            )
            download_thread.start()
            
            return {
                'success': True,
                'download_task_id': download_task_id,
                'download_status_id': download_status.id,
                'message': 'Download queued for background processing',
                'total_order_items': len(list_order_item_id)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to queue download task'
            }

    @staticmethod
    def _process_download_in_thread(list_order_item_id: List[int], download_task_id: str, user_id: int):
        """
        Process download in background thread with WebSocket notifications
        """
        download_status = None
        temp_files_to_cleanup = []
        
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"🔄 Starting download processing for task {download_task_id}")
            
            # Get download status record and user
            download_status = OperationalDataUploadStatus.objects.get(task_id=download_task_id)
            user = CoreUser.objects.get(id=user_id)
            
            # Update status to processing and send notification
            download_status.status = 'processing'
            download_status.message = 'Processing download request...'
            download_status.save()
            
            OperationalDataService._send_download_notification(
                user.username, 
                list_order_item_id, 
                'processing', 
                'Download processing started...'
            )
            
            # Create main zip file to contain all individual zip files
            main_temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_files_to_cleanup = [main_temp_zip.name]
            processed_items = 0
            
            with zipfile.ZipFile(main_temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as main_zip_file:
                for order_item_id in list_order_item_id:
                    try:
                        # Update progress and send notification
                        progress_message = f'Processing order item {processed_items + 1} of {len(list_order_item_id)}'
                        download_status.message = progress_message
                        download_status.save()
                        
                        OperationalDataService._send_download_notification(
                            user.username, 
                            list_order_item_id, 
                            'processing', 
                            progress_message,
                            {'progress': (processed_items + 1) / len(list_order_item_id) * 100}
                        )
                        
                        # Get delivery operation item for naming
                        order_item = OrderItem.objects.get(id=order_item_id)
                        delivery_operation_item = DeliveryOperationItem.objects.filter(order_item=order_item).first()
                        
                        # Get all operational data files
                        operational_data_list = OperationalData.objects.filter(
                            operation_item_id=delivery_operation_item
                        ).select_related('media_file')
                        
                        if not operational_data_list.exists():
                            logger.info(f"No operational data found for delivery operation item {order_item_id}")
                            continue
                        
                        # Create a temporary zip file for this delivery operation item
                        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
                        temp_files_to_cleanup.append(temp_zip.name)
                        files_added = 0
                        
                        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for operational_data in operational_data_list:
                                media_file = operational_data.media_file
                                if media_file:
                                    try:
                                        # Get the file content from the file field or URL
                                        file_content = None
                                        file_extension = getattr(media_file, 'file_extension', '')
                                        original_filename = getattr(media_file, 'file_name', None) or f"operational_log_{operational_data.id}{file_extension}"
                                        
                                        # If direct file access failed, try URL approach
                                        if hasattr(media_file, 'file_url') and media_file.file_url:
                                            try:
                                                response = requests.get(media_file.file_url, timeout=30)
                                                if response.status_code == 200:
                                                    file_content = response.content
                                            except Exception as e:
                                                logger.error(f"Error fetching file from URL: {str(e)}")
                                        
                                        # Add file to zip if we got content
                                        if file_content:
                                            # Convert .log files to CSV
                                            if file_extension.lower() == '.log':
                                                try:
                                                    # Convert log content to CSV
                                                    csv_content, csv_filename = OperationalDataService._convert_log_to_csv(
                                                        file_content, original_filename
                                                    )
                                                    zip_file.writestr(csv_filename, csv_content)
                                                    files_added += 1
                                                except Exception as e:
                                                    logger.error(f"Error converting log file to CSV: {str(e)}")
                                                    # Fall back to original file if conversion fails
                                                    zip_file.writestr(original_filename, file_content)
                                                    files_added += 1
                                            else:
                                                # Add original file for non-log files
                                                zip_file.writestr(original_filename, file_content)
                                                files_added += 1
                                        else:
                                            logger.warning(f"Could not retrieve content for file {media_file.id}")
                                            
                                    except Exception as e:
                                        # Log error but continue with other files
                                        logger.error(f"Error adding file {media_file.id} to zip: {str(e)}")
                                        continue
                        
                        # Only add to main zip if files were added
                        if files_added > 0:
                            # Generate zip filename for this delivery operation item
                            operation_code = f"operational_logs_{order_item_id}"
                            if hasattr(delivery_operation_item, 'delivery_operation') and delivery_operation_item.delivery_operation:
                                if hasattr(delivery_operation_item.delivery_operation, 'order') and delivery_operation_item.delivery_operation.order:
                                    operation_code = f"operational_logs_{delivery_operation_item.delivery_operation.order.order_code}"
                            
                            child_zip_filename = f"{operation_code}.zip"
                            
                            # Read the individual zip file content and add to main zip
                            with open(temp_zip.name, 'rb') as zip_content:
                                main_zip_file.writestr(child_zip_filename, zip_content.read())
                        
                        processed_items += 1
                        download_status.uploaded_files = processed_items  # Reuse this field for processed items
                        download_status.save()
                        
                    except OrderItem.DoesNotExist:
                        logger.error(f"Order item {order_item_id} not found")
                        download_status.failed_files += 1
                        download_status.save()
                        continue
                    except Exception as e:
                        logger.error(f"Error processing order item {order_item_id}: {str(e)}")
                        download_status.failed_files += 1
                        download_status.save()
                        continue
            
            # Upload the zip file to S3 for download
            with open(main_temp_zip.name, 'rb') as zip_file:
                zip_content = zip_file.read()
                zip_filename = "operational_data_bulk_download.zip"
                
                file_obj = InMemoryUploadedFile(
                    file=BytesIO(zip_content),
                    field_name='file',
                    name=zip_filename,
                    content_type='application/zip',
                    size=len(zip_content),
                    charset=None
                )
                
                # Upload to S3
                uploaded_file = FileHelper.user_upload_s3(user, file_obj, is_avatar=False, only_image=False)
                
                # Update download status with success
                success_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS)
                download_status.status = 'success'
                download_status.message = success_message
                download_status.completed_at = timezone.now()
                download_status.error_details = {
                    'download_url': uploaded_file.file_url if hasattr(uploaded_file, 'file_url') else None,
                    'file_id': uploaded_file.id,
                    'filename': zip_filename
                }
                download_status.donwload_url = f'https://{settings.MINIO_ENDPOINT}{uploaded_file.file_url}' if hasattr(uploaded_file, 'file_url') else None
                download_status.save()
                
                # Send success notification with download URL
                OperationalDataService._send_download_notification(
                    user.username, 
                    list_order_item_id, 
                    'success', 
                    success_message,
                    {
                        'download_url': f'https://{settings.MINIO_ENDPOINT}{uploaded_file.file_url}' if hasattr(uploaded_file, 'file_url') else None,
                        'filename': zip_filename,
                        'file_id': uploaded_file.id,
                        'processed_items': processed_items,
                        'total_items': len(list_order_item_id)
                    }
                )
                
                logger.info(f"✅ Download processing completed for task {download_task_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in download processing for task {download_task_id}: {str(e)}")
            
            # Update download status on error
            if download_status:
                error_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED)
                download_status.status = 'failed'
                download_status.message = error_message
                download_status.error_details = {'error': str(e)}
                download_status.completed_at = timezone.now()
                download_status.save()
                
                # Send failure notification
                try:
                    user = CoreUser.objects.get(id=user_id)
                    OperationalDataService._send_download_notification(
                        user.username, 
                        list_order_item_id, 
                        'failed', 
                        error_message,
                        {'error': str(e)}
                    )
                except:
                    pass
        
        finally:
            # Clean up all temporary files
            for temp_file in temp_files_to_cleanup:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except Exception as e:
                        logger.error(f"Error cleaning up temp file {temp_file}: {str(e)}")

    @staticmethod
    @transaction.atomic
    def download_operational_data_sync(list_order_item_id: List[int]):
        try:
            # check not exist any OperationalData has order_item in list_order_item_id
            if not OperationalData.objects.filter(operation_item__order_item_id__in=list_order_item_id).exists():
                return None
            
            # Create main zip file to contain all individual zip files
            main_temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_files_to_cleanup = [main_temp_zip.name]
            
            with zipfile.ZipFile(main_temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as main_zip_file:
                for order_item_id in list_order_item_id:
                    try:
                        # Get delivery operation item for naming
                        order_item = OrderItem.objects.get(id=order_item_id)
                        delivery_operation_item = DeliveryOperationItem.objects.filter(order_item=order_item).first()
                        
                        # Get all operational data files
                        operational_data_list = OperationalData.objects.filter(
                            operation_item_id=delivery_operation_item
                        ).select_related('media_file')
                        print(f"operational_data_list for item {order_item_id}: ", operational_data_list)
                        
                        if not operational_data_list.exists():
                            print(f"No operational data found for delivery operation item {order_item_id}")
                            continue
                        
                        # Create a temporary zip file for this delivery operation item
                        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
                        temp_files_to_cleanup.append(temp_zip.name)
                        files_added = 0
                        
                        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for operational_data in operational_data_list:
                                media_file = operational_data.media_file
                                if media_file:
                                    try:
                                        # Get the file content from the file field or URL
                                        file_content = None
                                        file_extension = getattr(media_file, 'file_extension', '')
                                        original_filename = getattr(media_file, 'file_name', None) or f"operational_log_{operational_data.id}{file_extension}"
                                        
                                        # If direct file access failed, try URL approach
                                        if hasattr(media_file, 'file_url') and media_file.file_url:
                                            try:
                                                response = requests.get(media_file.file_url, timeout=30)
                                                if response.status_code == 200:
                                                    file_content = response.content
                                            except Exception as e:
                                                print(f"Error fetching file from URL: {str(e)}")
                                        
                                        # Add file to zip if we got content
                                        if file_content:
                                            # Convert .log files to CSV
                                            if file_extension.lower() == '.log':
                                                try:
                                                    # Convert log content to CSV
                                                    csv_content, csv_filename = OperationalDataService._convert_log_to_csv(
                                                        file_content, original_filename
                                                    )
                                                    zip_file.writestr(csv_filename, csv_content)
                                                    files_added += 1
                                                except Exception as e:
                                                    print(f"Error converting log file to CSV: {str(e)}")
                                                    # Fall back to original file if conversion fails
                                                    zip_file.writestr(original_filename, file_content)
                                                    files_added += 1
                                            else:
                                                # Add original file for non-log files
                                                zip_file.writestr(original_filename, file_content)
                                                files_added += 1
                                        else:
                                            print(f"Could not retrieve content for file {media_file.id}")
                                            
                                    except Exception as e:
                                        # Log error but continue with other files
                                        print(f"Error adding file {media_file.id} to zip: {str(e)}")
                                        continue
                        
                        # Only add to main zip if files were added
                        if files_added > 0:
                            # Generate zip filename for this delivery operation item
                            operation_code = f"operational_logs_{order_item_id}"
                            if hasattr(delivery_operation_item, 'delivery_operation') and delivery_operation_item.delivery_operation:
                                if hasattr(delivery_operation_item.delivery_operation, 'order') and delivery_operation_item.delivery_operation.order:
                                    operation_code = f"operational_logs_{delivery_operation_item.delivery_operation.order.order_code}"
                            
                            child_zip_filename = f"{operation_code}.zip"
                            
                            # Read the individual zip file content and add to main zip
                            with open(temp_zip.name, 'rb') as zip_content:
                                main_zip_file.writestr(child_zip_filename, zip_content.read())
                        else:
                            print(f"No files added for delivery operation item {order_item_id}")
                            
                    except OrderItem.DoesNotExist:
                        print(f"Delivery operation item {order_item_id} not found")
                        continue
                    except Exception as e:
                        print(f"Error processing delivery operation item {order_item_id}: {str(e)}")
                        continue
            
            # Generate main zip filename
            main_zip_filename = "operational_data_bulk_download.zip"
            
            # Read the main zip file content
            with open(main_temp_zip.name, 'rb') as main_zip_content:
                main_zip_data = main_zip_content.read()
            
            # Clean up all temporary files
            for temp_file in temp_files_to_cleanup:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            # Create HTTP response with main zip file
            response = HttpResponse(main_zip_data, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{main_zip_filename}"'
            response['Content-Length'] = len(main_zip_data)
            
            return response
            
        except Exception as e:
            # Clean up temp files if they exist
            if 'temp_files_to_cleanup' in locals():
                for temp_file in temp_files_to_cleanup:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
            raise e
    
    @staticmethod
    def _convert_log_to_csv(file_content: bytes, original_filename: str) -> tuple:
        """
        Convert log file content to CSV format.
        Returns tuple of (csv_content_bytes, csv_filename)
        """
        try:
            # Decode bytes to string
            log_text = file_content.decode('utf-8', errors='ignore')
            
            # Split into lines
            lines = log_text.strip().split('\n')
            
            # Create CSV data
            csv_data = []
            
            # Try to detect log format and parse accordingly
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Try to parse common log formats
                parsed_row = OperationalDataService._parse_log_line(line, line_num)
                csv_data.append(parsed_row)
            
            # Create DataFrame
            if csv_data:
                df = pd.DataFrame(csv_data)
            else:
                # If no data parsed, create simple line-by-line CSV
                df = pd.DataFrame({
                    'line_number': range(1, len(lines) + 1),
                    'content': lines
                })
            
            # Convert to CSV string
            csv_string = df.to_csv(index=False, encoding='utf-8')
            csv_content = csv_string.encode('utf-8')
            
            # Generate CSV filename
            csv_filename = original_filename.replace('.log', '.csv')
            if not csv_filename.endswith('.csv'):
                csv_filename += '.csv'
            
            return csv_content, csv_filename
            
        except Exception as e:
            print(f"Error in log to CSV conversion: {str(e)}")
            # Return original content with CSV extension as fallback
            csv_filename = original_filename.replace('.log', '.csv')
            if not csv_filename.endswith('.csv'):
                csv_filename += '.csv'
            return file_content, csv_filename
    
    @staticmethod
    def _parse_log_line(line: str, line_num: int) -> dict:
        """
        Parse a single log line into structured data.
        This method tries to detect common log formats and extract relevant fields.
        """
        
        # Common log patterns
        patterns = [
            # Standard log format: [TIMESTAMP] LEVEL: MESSAGE
            r'^\[([^\]]+)\]\s+(\w+):\s*(.+)$',
            # Apache/Nginx format: IP - - [TIMESTAMP] "REQUEST" STATUS SIZE
            r'^(\S+)\s+-\s+-\s+\[([^\]]+)\]\s+"([^"]+)"\s+(\d+)\s+(\d+)$',
            # Syslog format: TIMESTAMP HOSTNAME PROCESS: MESSAGE
            r'^(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+([^:]+):\s*(.+)$',
            # Simple timestamp format: YYYY-MM-DD HH:MM:SS LEVEL MESSAGE
            r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)$',
            # JSON-like format detection
            r'^\{.*\}$'
        ]
        
        parsed_data = {
            'line_number': line_num,
            'timestamp': '',
            'level': '',
            'message': line,
            'raw_line': line
        }
        
        # Try each pattern
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) >= 3 and '[' in pattern and ']' in pattern:
                    # Standard log format
                    parsed_data.update({
                        'timestamp': groups[0],
                        'level': groups[1],
                        'message': groups[2]
                    })
                elif len(groups) >= 5 and 'REQUEST' in pattern:
                    # Apache/Nginx format
                    parsed_data.update({
                        'ip_address': groups[0],
                        'timestamp': groups[1],
                        'request': groups[2],
                        'status_code': groups[3],
                        'response_size': groups[4],
                        'message': f"{groups[2]} - {groups[3]} - {groups[4]}"
                    })
                elif len(groups) >= 4 and 'HOSTNAME' in pattern:
                    # Syslog format
                    parsed_data.update({
                        'timestamp': groups[0],
                        'hostname': groups[1],
                        'process': groups[2],
                        'message': groups[3]
                    })
                elif len(groups) >= 3 and 'YYYY-MM-DD' in pattern:
                    # Simple timestamp format
                    parsed_data.update({
                        'timestamp': groups[0],
                        'level': groups[1],
                        'message': groups[2]
                    })
                break
        
        # Try to parse JSON if it looks like JSON
        if line.strip().startswith('{') and line.strip().endswith('}'):
            try:
                json_data = json.loads(line)
                # Flatten JSON data
                for key, value in json_data.items():
                    if isinstance(value, (str, int, float, bool)):
                        parsed_data[key] = str(value)
                    else:
                        parsed_data[key] = json.dumps(value)
            except json.JSONDecodeError:
                pass
        
        return parsed_data
    
    @staticmethod
    def get_upload_status(task_id: str = None, upload_status_id: int = None):
        """
        Get upload status by task_id or upload_status_id
        """
        try:            
            if task_id:
                upload_status = OperationalDataUploadStatus.objects.get(task_id=task_id)
            elif upload_status_id:
                upload_status = OperationalDataUploadStatus.objects.get(id=upload_status_id)
            else:
                raise ValueError("Either task_id or upload_status_id must be provided")
            
            return {
                'success': True,
                'data': {
                    'id': upload_status.id,
                    'task_id': upload_status.task_id,
                    'order_item_id': upload_status.order_item.id,
                    'upload_type': upload_status.upload_type,
                    'device_type': upload_status.device_type,
                    'status': upload_status.status,
                    'total_files': upload_status.total_files,
                    'uploaded_files': upload_status.uploaded_files,
                    'failed_files': upload_status.failed_files,
                    'progress_percentage': upload_status.progress_percentage,
                    'message': upload_status.message,
                    'error_details': upload_status.error_details,
                    'failed_file_details': upload_status.failed_file_details,
                    'started_at': upload_status.started_at,
                    'completed_at': upload_status.completed_at,
                    'is_completed': upload_status.is_completed,
                    'download_url': upload_status.donwload_url,
                }
            }
            
        except OperationalDataUploadStatus.DoesNotExist:
            return {
                'success': False,
                'error': 'Upload status not found',
                'message': 'Upload status record not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get upload status'
            }
    
    @staticmethod
    def _send_download_notification(username: str, order_item_ids: List[int], status: str, message: str, data: dict = None):
        """
        Send WebSocket notification to user about download status
        
        Args:
            username: Username of the user to notify
            order_item_ids: List of order item IDs being downloaded
            status: 'success', 'failed', 'processing', or 'pending'
            message: Notification message
            data: Additional data to include in notification (download_url, etc.)
        """
        try:
            logger = logging.getLogger(__name__)
            
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.warning("Channel layer not configured - notifications disabled")
                return
            
            # Prepare notification event
            event = {
                'type': 'operational_data_download_notification',
                'notification_type': 'operational_data_download',
                'order_item_ids': order_item_ids,
                'status': status,
                'message': message,
                'timestamp': timezone.now().isoformat(),
                'data': data or {}
            }
            
            # Send to operational data user-specific group
            async_to_sync(channel_layer.group_send)(f'operational_data_{username}', event)
            logger.info(f"📤 Sent download notification to user {username}: {status}")
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error sending download notification: {str(e)}")
    
    @staticmethod
    def _send_log_download_notification(username: str, order_item_id: int, device_type: str, status: str, message: str, data: dict = None):
        """
        Send WebSocket notification to user about log download status
        
        Args:
            username: Username of the user to notify
            order_item_id: Order item ID being downloaded
            device_type: 'drone' or 'robot'
            status: 'success', 'failed', 'processing', or 'pending'
            message: Notification message
            data: Additional data to include in notification (download_url, etc.)
        """
        try:
            logger = logging.getLogger(__name__)
            
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.warning("Channel layer not configured - notifications disabled")
                return
            
            # Prepare notification event
            event = {
                'type': 'operational_log_download_notification',
                'notification_type': 'operational_log_download',
                'order_item_id': order_item_id,
                'device_type': device_type,
                'status': status,
                'message': message,
                'timestamp': timezone.now().isoformat(),
                'data': data or {}
            }
            
            # Send to operational data user-specific group
            async_to_sync(channel_layer.group_send)(f'operational_data_{username}', event)
            logger.info(f"📤 Sent {device_type} log download notification to user {username}: {status}")
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error sending log download notification: {str(e)}")
    
    @staticmethod
    def _start_queue_processor_if_needed(upload_type: str, device_type: str):
        """
        Start queue processor if no active uploads are running
        """
        try:            
            # Check if there are any active uploads
            active_uploads = OperationalDataUploadStatus.objects.filter(
                upload_type=upload_type,
                device_type=device_type,
                status__in=['pending', 'processing']
            ).exists()
            
            if not active_uploads:
                # Start processing the queue
                process_upload_queue_task.delay(upload_type, device_type)
                
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error starting queue processor: {str(e)}")
    
    @staticmethod
    def process_upload_queue(upload_type: str, device_type: str):
        """
        Process the upload queue sequentially
        """
        try:            
            logger = logging.getLogger(__name__)
            logger.info(f"🔄 Starting queue processor for {device_type} {upload_type} uploads")
            
            while True:
                # Get next queued upload
                next_upload = OperationalDataUploadStatus.objects.filter(
                    upload_type=upload_type,
                    device_type=device_type,
                    status='queued'
                ).order_by('queue_position', 'queued_at').first()
                
                if not next_upload:
                    logger.info(f"✅ Queue processor finished - no more {device_type} {upload_type} uploads in queue")
                    break
                
                logger.info(f"🎯 Processing queued upload: {next_upload.task_id}")
                
                # Update status to pending
                next_upload.status = 'pending'
                next_upload.message = 'Upload started from queue'
                next_upload.save()
                
                # Decode file data from base64
                file_data_list = []
                for file_data in next_upload.file_data:
                    decoded_content = base64.b64decode(file_data['content'])
                    file_data_decoded = {
                        'content': decoded_content,
                        'name': file_data['name'],
                        'content_type': file_data['content_type'],
                        'size': file_data['size']
                    }
                    file_data_list.append(file_data_decoded)
                
                # Process the upload synchronously
                try:
                    if upload_type == 'video' and device_type in ['drone', 'robot']:
                        # Call the actual upload processing logic
                        result = OperationalDataService._process_video_upload_sync(
                            next_upload.order_item.id,
                            file_data_list,
                            next_upload.user.id,
                            next_upload.task_id,
                            device_type
                        )
                        
                        if result['success']:
                            next_upload.status = 'success'
                            next_upload.message = result['message']
                            next_upload.uploaded_files = result.get('uploaded_files', len(file_data_list))
                            # send notification
                            _send_upload_notification(next_upload.user.username, next_upload.order_item.id, device_type, 'success', result['message'], next_upload.task_id)
                        else:
                            next_upload.status = 'failed'
                            next_upload.message = result['message']
                            next_upload.error_details = {'error': result.get('error', 'Unknown error')}
                            # send notification
                            _send_upload_notification(next_upload.user.username, next_upload.order_item.id, device_type, 'failed', result['message'], next_upload.task_id)
                    
                    elif upload_type == 'log' and device_type in ['drone', 'robot']:
                        # Call the actual log upload processing logic
                        result = OperationalDataService._process_log_upload_sync(
                            next_upload.order_item.id,
                            file_data_list,
                            next_upload.user.id,
                            next_upload.task_id,
                            device_type
                        )
                        
                        if result['success']:
                            next_upload.status = 'success'
                            next_upload.message = result['message']
                            next_upload.uploaded_files = result.get('uploaded_files', len(file_data_list))
                            # send notification
                            _send_upload_log_notification(next_upload.user.username, next_upload.order_item.id, device_type, 'success', result['message'], next_upload.task_id)
                        else:
                            next_upload.status = 'failed'
                            next_upload.message = result['message']
                            next_upload.error_details = {'error': result.get('error', 'Unknown error')}
                            # send notification
                            _send_upload_log_notification(next_upload.user.username, next_upload.order_item.id, device_type, 'failed', result['message'], next_upload.task_id)
                    
                    # Clear file data to save space
                    next_upload.file_data = None
                    next_upload.completed_at = timezone.now()
                    next_upload.save()
                    
                    logger.info(f"✅ Completed queued upload: {next_upload.task_id} - Status: {next_upload.status}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing queued upload {next_upload.task_id}: {str(e)}")
                    next_upload.status = 'failed'
                    next_upload.message = f'Upload failed: {str(e)}'
                    next_upload.error_details = {'error': str(e)}
                    next_upload.file_data = None
                    next_upload.completed_at = timezone.now()
                    next_upload.save()
                
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error in queue processor: {str(e)}")
    
    @staticmethod
    def _process_video_upload_sync(order_item_id: int, file_data_list: List[dict], user_id: int, task_id: str, device_type: str = 'drone'):
        """
        Synchronously process video upload (extracted from the async task logic)
        """
        try:
            logger = logging.getLogger(__name__)
            
            # Get required objects
            order_item = OrderItem.objects.get(id=order_item_id)
            user = CoreUser.objects.get(id=user_id)
            delivery_operation_item = DeliveryOperationItem.objects.filter(order_item=order_item).first()
            
            if not delivery_operation_item:
                return {
                    'success': False,
                    'error': 'Delivery operation item not found',
                    'message': 'No delivery operation item found for this order'
                }
            
            uploaded_files = []
            failed_files = []
            
            for i, file_data in enumerate(file_data_list):
                try:
                    # Create InMemoryUploadedFile from file data
                    file_obj = InMemoryUploadedFile(
                        file=BytesIO(file_data['content']),
                        field_name='file',
                        name=file_data['name'],
                        content_type=file_data['content_type'],
                        size=file_data['size'],
                        charset=None
                    )
                    
                    # Upload to S3
                    uploaded_file = FileHelper.user_upload_s3(user, file_obj, is_avatar=False, only_image=False)
                    
                    # Create OperationalData record
                    operational_data = OperationalData.objects.create(
                        operation_item=delivery_operation_item,
                        operation_item_type='video',
                        device_type=device_type,
                        media_file=uploaded_file
                    )
                    
                    uploaded_files.append({
                        'file_name': file_data['name'],
                        'operational_data_id': operational_data.id,
                        'media_file_id': uploaded_file.id
                    })
                    
                    logger.info(f"✅ Uploaded file {i+1}/{len(file_data_list)}: {file_data['name']}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to upload file {file_data['name']}: {str(e)}")
                    failed_files.append({
                        'file_name': file_data['name'],
                        'error': str(e)
                    })
            
            # Determine final status
            if len(uploaded_files) == len(file_data_list):
                status = 'success'
                message = f'All {len(uploaded_files)} video files uploaded successfully'
            elif len(uploaded_files) > 0:
                status = 'partial_success'
                message = f'{len(uploaded_files)} of {len(file_data_list)} files uploaded successfully'
            else:
                status = 'failed'
                message = 'All file uploads failed'
            
            return {
                'success': status in ['success', 'partial_success'],
                'message': message,
                'uploaded_files': len(uploaded_files),
                'failed_files': len(failed_files),
                'uploaded_file_details': uploaded_files,
                'failed_file_details': failed_files
            }
            
        except Exception as e:
            logger.error(f"❌ Error in sync video upload processing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Upload processing failed: {str(e)}'
            }
    
    @staticmethod
    def _process_log_upload_sync(order_item_id: int, file_data_list: List[dict], user_id: int, task_id: str, device_type: str = 'drone'):
        """
        Synchronously process log upload (similar to video upload but for log files)
        """
        try:
            logger = logging.getLogger(__name__)
            
            # Get required objects
            order_item = OrderItem.objects.get(id=order_item_id)
            user = CoreUser.objects.get(id=user_id)
            delivery_operation_item = DeliveryOperationItem.objects.filter(order_item=order_item).first()
            
            if not delivery_operation_item:
                return {
                    'success': False,
                    'error': 'Delivery operation item not found',
                    'message': 'No delivery operation item found for this order'
                }
            
            # Delete old operational log data for this device type
            OperationalData.objects.filter(
                operation_item=delivery_operation_item,
                operation_item_type='log',
                device_type=device_type
            ).delete()
            
            uploaded_files = []
            failed_files = []
            
            for i, file_data in enumerate(file_data_list):
                try:
                    # Create InMemoryUploadedFile from file data
                    file_obj = InMemoryUploadedFile(
                        file=BytesIO(file_data['content']),
                        field_name='file',
                        name=file_data['name'],
                        content_type=file_data['content_type'],
                        size=file_data['size'],
                        charset=None
                    )
                    
                    # Upload to S3
                    uploaded_file = FileHelper.user_upload_s3(user, file_obj, is_avatar=False, only_image=False)
                    
                    # Create OperationalData record
                    operational_data = OperationalData.objects.create(
                        operation_item=delivery_operation_item,
                        operation_item_type='log',
                        device_type=device_type,
                        media_file=uploaded_file
                    )
                    
                    uploaded_files.append({
                        'file_name': file_data['name'],
                        'operational_data_id': operational_data.id,
                        'media_file_id': uploaded_file.id
                    })
                    
                    logger.info(f"✅ Uploaded log file {i+1}/{len(file_data_list)}: {file_data['name']}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to upload log file {file_data['name']}: {str(e)}")
                    failed_files.append({
                        'file_name': file_data['name'],
                        'error': str(e)
                    })
            
            # Determine final status
            if len(uploaded_files) == len(file_data_list):
                status = 'success'
                message = f'All {len(uploaded_files)} {device_type} log files uploaded successfully'
            elif len(uploaded_files) > 0:
                status = 'partial_success'
                message = f'{len(uploaded_files)} of {len(file_data_list)} {device_type} log files uploaded successfully'
            else:
                status = 'failed'
                message = f'All {device_type} log file uploads failed'
            
            return {
                'success': status in ['success', 'partial_success'],
                'message': message,
                'uploaded_files': len(uploaded_files),
                'failed_files': len(failed_files),
                'uploaded_file_details': uploaded_files,
                'failed_file_details': failed_files
            }
            
        except Exception as e:
            logger.error(f"❌ Error in sync log upload processing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Log upload processing failed: {str(e)}'
            }
        