from django.db import transaction, models
from ninja.errors import ValidationError
from orders.models import ExternalOrderStatus, OrderStatusMapping
from core.common.search.dynamic_search import apply_dynamic_filters
from core.user.models import CoreUser
from typing import List
from core.multilanguage.request_handlers import process_multilanguage_request, create_model_with_translations, update_model_with_translations, get_model_with_translations
from common.constant import MESSAGE_ENUM

class ExternalOrderStatusService:
    """
    Service class for managing ExternalOrderStatus operations.
    Follows workspace standards with transaction handling and validation.
    """
    
    @staticmethod
    @transaction.atomic
    def create(data: dict, user: CoreUser = None) -> ExternalOrderStatus:
        """
        Create a new external order status.
        
        Args:
            data: Dictionary containing external order status data
            user: User creating the status
            
        Returns:
            ExternalOrderStatus: Created external order status instance
            
        Raises:
            ValidationError: If required fields are missing or invalid
        """
        # Validate required fields
        if not data.get('name'):
            raise ValidationError("name is required")
        if not data.get('value'):
            raise ValidationError("value is required")
            
        # Check if value already exists for the same group
        if data.get('group_id'):
            existing = ExternalOrderStatus.objects.filter(
                value=data['value'], 
                group_id=data['group_id']
            ).first()
            if existing:
                raise ValidationError(f"External order status with value '{data['value']}' already exists for this group")
        
        external_status = create_model_with_translations(ExternalOrderStatus, data)
        if data.get('group_id'):
            external_status.group_id = data['group_id']
            external_status.save()
        return external_status
    
    @staticmethod
    @transaction.atomic
    def update(external_status_id: int, data: dict, user: CoreUser = None) -> ExternalOrderStatus:
        """
        Update an existing external order status.
        
        Args:
            external_status_id: ID of the external order status to update
            data: Dictionary containing updated data
            user: User updating the status
            
        Returns:
            ExternalOrderStatus: Updated external order status instance
            
        Raises:
            ValidationError: If external order status not found or validation fails
        """
        try:
            external_status = ExternalOrderStatus.objects.get(id=external_status_id)
        except ExternalOrderStatus.DoesNotExist:
            raise ValidationError("External order status not found")
        
        # Validate value uniqueness if it's being changed
        if 'value' in data and data['value'] != external_status.value:
            existing = ExternalOrderStatus.objects.filter(
                value=data['value'],
                group_id=external_status.group_id
            ).exclude(id=external_status_id).first()
            if existing:
                raise ValidationError(f"External order status with value '{data['value']}' already exists for this group")
        
        # Update fields
        for key, value in data.items():
            if hasattr(external_status, key):
                setattr(external_status, key, value)
        if data.get('group_id'):
            external_status.group_id = data['group_id']
        update_model_with_translations(external_status, data)
        return external_status
    
    @staticmethod
    @transaction.atomic
    def delete(external_status_ids: List[int], user: CoreUser = None) -> tuple[bool, str]:
        """
        Delete an external order status.
        
        Args:
            external_status_id: ID of the external order status to delete
            user: User deleting the status
            
        Returns:
            tuple: (success: bool, message: str)
        """

        
        # Check if status is being used in mappings
        if  OrderStatusMapping.objects.filter(external_order_statuses__in=external_status_ids).exists():
            return False, "Cannot delete external order status that is being used in mappings"
        
        ExternalOrderStatus.objects.filter(id__in=external_status_ids).delete() 
        return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
    
    @staticmethod
    def get_by_id(external_status_id: int) -> ExternalOrderStatus:
        """
        Get external order status by ID.
        
        Args:
            external_status_id: ID of the external order status
            
        Returns:
            ExternalOrderStatus: External order status instance
            
        Raises:
            ValidationError: If external order status not found
        """
        try:
            return ExternalOrderStatus.objects.get(id=external_status_id)
        except ExternalOrderStatus.DoesNotExist:
            raise ValidationError("External order status not found")
    
    @staticmethod
    def get_list(request=None, group_id: int = None):
        """
        Get list of external order statuses with dynamic filtering.
        
        Args:
            request: Request object for dynamic filtering
            group_id: Filter by group ID
            
        Returns:
            QuerySet: Filtered external order statuses
        """
        queryset = ExternalOrderStatus.objects.select_related('group').annotate(group__id=models.F('group_id'))
        
        # Filter by group
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # Apply dynamic filters if request is provided
        if request:
            queryset = apply_dynamic_filters(
                queryset, 
                request, 
                [], 
                request.GET.get('sort_obj', None)
            )
        
        return queryset.order_by('group', 'name')
    
    @staticmethod
    def get_data(external_status_id: int) -> dict:
        """
        Get formatted data for external order status.
        
        Args:
            external_status_id: ID of the external order status
            
        Returns:
            dict: Formatted external order status data
        """
        external_status = ExternalOrderStatusService.get_by_id(external_status_id)
        
        return {
            'id': external_status.id,
            'name': external_status.name,
            'value': external_status.value,
            'description': external_status.description,
            'is_active': external_status.is_active,
            'group_id': external_status.group_id,
            'group_name': external_status.group.name if external_status.group else None,
            'created_on': external_status.created_on,
            'modified_on': external_status.modified_on
        } 