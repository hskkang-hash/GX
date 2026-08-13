from delivery.models import DeliveryOperationItem
from operational_data.models import OperationalData, OperationalDataUploadStatus, OperationalNotice
from orders.models import OrderItem
from core.common.schema_utils import DynamicSchema
from typing import Optional, List, Dict, Any
from datetime import datetime

class OperationalDataListOutSchema(DynamicSchema):
    item_weight: Optional[str] = None
    
    class Meta:
        model = OrderItem
        model_fields = ['id', 'delivery_operation_code', 'delivery_point', 'item_weight', 'delivered_at', 'delivery_operation__created_on', 'route']
    
    @classmethod
    def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
        # Use DynamicSchema's from_queryset and then enhance with formatted weight
        result = super().from_queryset(queryset_or_instance, many=many, **kwargs)
        
        if not many:
            # Get the first (and only) instance from the queryset
            instance = queryset_or_instance.first() if hasattr(queryset_or_instance, 'first') else queryset_or_instance
            cls._get_drone_video_path(result, instance)
            cls._get_robot_video_path(result, instance)
        
        return result
    
    @classmethod
    def _get_drone_video_path(cls, item_data: dict, obj):
        """Get drone video path from operational data"""
        operation_item = DeliveryOperationItem.objects.filter(order_item=obj).first()
        drone_video = OperationalData.objects.filter(
            operation_item=operation_item, 
            operation_item_type='video', 
            device_type='drone'
        ).first()
        
        if drone_video and drone_video.media_file:
            try:
                # Try to get the URL first (for S3 or web-accessible files)
                if hasattr(drone_video.media_file, 'file_url'):
                    item_data['drone_video_path'] = drone_video.media_file.file_url
                # Fallback to file path if URL is not available
                # elif hasattr(drone_video.media_file, 'file_content') and drone_video.media_file.file_content:
                #     item_data['drone_video_path'] = drone_video.media_file.file_content
                else:
                    item_data['drone_video_path'] = 'N/A'
            except Exception:
                item_data['drone_video_path'] = 'N/A'
        else:
            item_data['drone_video_path'] = 'N/A'

    @classmethod
    def _get_robot_video_path(cls, item_data: dict, obj):
        """Get robot video path from operational data"""
        operation_item = DeliveryOperationItem.objects.filter(order_item=obj).first()
        robot_video = OperationalData.objects.filter(
            operation_item=operation_item, 
            operation_item_type='video', 
            device_type='robot'
        ).first()
        
        if robot_video and robot_video.media_file:
            try:
                if hasattr(robot_video.media_file, 'file_url') and robot_video.media_file.file_url:
                    item_data['robot_video_path'] = robot_video.media_file.file_url
                elif hasattr(robot_video.media_file, 'file_content') and robot_video.media_file.file_content:
                    item_data['robot_video_path'] = robot_video.media_file.file_content
                else:
                    item_data['robot_video_path'] = 'N/A'
            except Exception:
                item_data['robot_video_path'] = 'N/A'
        else:
            item_data['robot_video_path'] = 'N/A'


class OperationalDataUploadStatusOutSchema(DynamicSchema):
    order_item_id: int
    user_id: int
    task_id: str
    upload_type: str
    device_type: str
    status: str
    total_files: int
    uploaded_files: int
    failed_files: int
    progress_percentage: float
    message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    failed_file_details: Optional[List[Dict[str, Any]]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    is_completed: bool
    
    class Meta:
        model = OperationalDataUploadStatus
        model_fields = [
            'id', 'order_item_id', 'user_id', 'task_id', 'upload_type', 
            'device_type', 'status', 'total_files', 'uploaded_files', 
            'failed_files', 'message', 'error_details', 
            'failed_file_details', 'started_at', 'completed_at'
        ]
    
    @classmethod
    def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
        result = super().from_queryset(queryset_or_instance, many=many, **kwargs)
        
        if many:
            for i, item in enumerate(result):
                if hasattr(queryset_or_instance, '__iter__'):
                    instance = list(queryset_or_instance)[i]
                    item['progress_percentage'] = instance.progress_percentage
                    item['is_completed'] = instance.is_completed
                    item['order_item_id'] = instance.order_item.id
                    item['user_id'] = instance.user.id
        else:
            instance = queryset_or_instance.first() if hasattr(queryset_or_instance, 'first') else queryset_or_instance
            if instance:
                result['progress_percentage'] = instance.progress_percentage
                result['is_completed'] = instance.is_completed
                result['order_item_id'] = instance.order_item.id
                result['user_id'] = instance.user.id
        
        return result


class OperationalNoticeOutSchema(DynamicSchema):
    """Schema đầu ra cho OperationalNotice"""
    
    class Meta:
        model = OperationalNotice
        model_fields = ['id', 'name', 'content', 'active', 'created_on', 'modified_on']
