from django.db import transaction
from core.user.models import UserGroup
from ninja.errors import ValidationError
from delivery.models import DeliveryStatus
from orders.models import OrderStatusMapping as DeliveryStatusMapping  # Using alias for compatibility
from typing import List, Optional, Dict, Any
from core.middleware.refresh_token import get_current_request

 
class StatusMappingService:
    """Service class for handling delivery status mapping operations"""

    @staticmethod
    def get_all_delivery_statuses() -> List[DeliveryStatus]:
        """
        Get all delivery statuses
        
        Returns:
            List[DeliveryStatus]: List of all delivery statuses
        """
        return DeliveryStatus.objects.filter(deleted__isnull=True).order_by('id')

    @staticmethod
    def get_status_mappings_by_group(group_id: Optional[int] = None) -> List[DeliveryStatusMapping]:
        """
        Get status mappings - CustomManagerGroup automatically filters by user's group
        
        Args:
            group_id: Optional group ID (for admin override)
            
        Returns:
            List[DeliveryStatusMapping]: List of status mappings
        """
        queryset = DeliveryStatusMapping.objects.filter(
            deleted__isnull=True, 
            is_active=True
        ).select_related('status', 'group').order_by('status__id')
        
        # If specific group_id is provided (admin override), filter by that group
        if group_id is not None:
            queryset = queryset.filter(group_id=group_id)
            
        return queryset

    @staticmethod
    @transaction.atomic
    def create_status_mapping(status_id: int, custom_name: str, custom_code: Optional[str] = None,
                            text_color: Optional[str] = None, background_color: Optional[str] = None,
                            border_color: Optional[str] = None, is_active: bool = True,
                            group_id: Optional[int] = None) -> DeliveryStatusMapping:
        """
        Create a new status mapping
        BaseModelWithGroup automatically assigns current user's group
        
        Args:
            status_id: ID of the delivery status to map
            custom_name: Custom display name
            custom_code: Custom code (optional)
            text_color: Text color (optional)
            background_color: Background color (optional)
            border_color: Border color (optional)
            is_active: Whether mapping is active
            group_id: Group ID (optional, for admin override)
            
        Returns:
            DeliveryStatusMapping: Created status mapping
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Get the delivery status
            status = DeliveryStatus.objects.get(id=status_id, deleted__isnull=True)
        except DeliveryStatus.DoesNotExist:
            raise ValidationError("Delivery status not found")

        # Validate custom_name
        if not custom_name or not custom_name.strip():
            raise ValidationError("Custom name is required")

        # Check if mapping already exists for this status
        # CustomManagerGroup will automatically filter by user's group
        existing_mapping = DeliveryStatusMapping.objects.filter(
            status=status,
            deleted__isnull=True
        ).first()
        
        if existing_mapping:
            raise ValidationError(f"Status mapping already exists for this status")

        # Create the mapping - BaseModelWithGroup will auto-assign current user's group
        mapping = DeliveryStatusMapping(
            status=status,
            custom_name=custom_name.strip(),
            custom_code=custom_code.strip() if custom_code else None,
            text_color=text_color,
            background_color=background_color,
            border_color=border_color,
            is_active=is_active
        )

        # Override group if admin provides specific group_id
        if group_id is not None:
            from core.user.models import UserGroup
            try:
                group = UserGroup.objects.get(id=group_id)
                mapping.group = group
            except UserGroup.DoesNotExist:
                raise ValidationError("Group not found")

        # Save - BaseModelWithGroup handles group assignment
        mapping.save()
        return mapping

    @staticmethod
    @transaction.atomic
    def update_status_mapping(mapping_id: int, custom_name: Optional[str] = None,
                            custom_code: Optional[str] = None, text_color: Optional[str] = None,
                            background_color: Optional[str] = None, border_color: Optional[str] = None,
                            is_active: Optional[bool] = None) -> DeliveryStatusMapping:
        """
        Update an existing status mapping
        CustomManagerGroup ensures user can only update mappings they have access to
        
        Args:
            mapping_id: ID of the mapping to update
            custom_name: New custom name (optional)
            custom_code: New custom code (optional)
            text_color: New text color (optional)
            background_color: New background color (optional)
            border_color: New border color (optional)
            is_active: New active status (optional)
            
        Returns:
            DeliveryStatusMapping: Updated status mapping
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # CustomManagerGroup will automatically filter by accessible mappings
            mapping = DeliveryStatusMapping.objects.get(id=mapping_id, deleted__isnull=True)
        except DeliveryStatusMapping.DoesNotExist:
            raise ValidationError("Status mapping not found or access denied")

        # Update fields if provided
        if custom_name is not None:
            if not custom_name.strip():
                raise ValidationError("Custom name cannot be empty")
            mapping.custom_name = custom_name.strip()

        if custom_code is not None:
            mapping.custom_code = custom_code.strip() if custom_code else None

        if text_color is not None:
            mapping.text_color = text_color

        if background_color is not None:
            mapping.background_color = background_color

        if border_color is not None:
            mapping.border_color = border_color

        if is_active is not None:
            mapping.is_active = is_active

        mapping.save()
        return mapping

    @staticmethod
    @transaction.atomic
    def delete_status_mapping(mapping_id: int) -> bool:
        """
        Delete a status mapping (soft delete)
        CustomManagerGroup ensures user can only delete mappings they have access to
        
        Args:
            mapping_id: ID of the mapping to delete
            
        Returns:
            bool: True if deleted successfully
            
        Raises:
            ValidationError: If mapping not found
        """
        try:
            # CustomManagerGroup will automatically filter by accessible mappings
            mapping = DeliveryStatusMapping.objects.get(id=mapping_id, deleted__isnull=True)
            mapping.delete()  # Soft delete through BaseModel
            return True
        except DeliveryStatusMapping.DoesNotExist:
            raise ValidationError("Status mapping not found or access denied")

    @staticmethod
    def get_status_mapping_by_id(mapping_id: int) -> Optional[DeliveryStatusMapping]:
        """
        Get status mapping by ID
        CustomManagerGroup ensures user can only access mappings they have permission to
        
        Args:
            mapping_id: ID of the mapping
            
        Returns:
            Optional[DeliveryStatusMapping]: Status mapping if found and accessible
        """
        try:
            # CustomManagerGroup handles group filtering automatically
            return DeliveryStatusMapping.objects.select_related('status', 'group').get(
                id=mapping_id, deleted__isnull=True
            )
        except DeliveryStatusMapping.DoesNotExist:
            return None

    @staticmethod
    def get_mapping_for_status(status_code: str, group_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get mapping data for a specific status code
        Uses CustomManagerGroup for automatic group filtering
        
        Args:
            status_code: Status code to look for
            group_id: Group ID (optional, for admin override)
            
        Returns:
            Optional[Dict]: Mapping data if found
        """
        try:
            queryset = DeliveryStatusMapping.objects.select_related('status').filter(
                status__code=status_code, 
                deleted__isnull=True, 
                is_active=True
            )
            
            # If specific group_id provided, override manager filtering
            if group_id is not None:
                queryset = queryset.filter(group_id=group_id)
            
            mapping = queryset.first()
            
            if mapping:
                return {
                    'custom_name': mapping.custom_name,
                    'custom_code': mapping.custom_code,
                    'text_color': mapping.text_color,
                    'background_color': mapping.background_color,
                    'border_color': mapping.border_color,
                }
        except Exception:
            pass
        return None

    @staticmethod
    def build_annotate_with_mapping( context: str = 'delivery_operation') -> Dict[str, Any]:
        """
        Build annotation dict for QuerySet to include list of mapped external statuses for the current delivery status.
        
        Changes:
        - Return a list of all ExternalOrderStatus mapped to the current delivery status (scoped by group)
        - No longer filter by external_order_statuses__value (external status code)
        - Keep backward-compatible single-value fields using the current internal status values
        
        Args:
            context: Context for field paths - 'delivery_operation' or 'order'
            
        Returns:
            Dict[str, Any]: Annotation dict with a 'mapped_status_list' JSON array and legacy fields
        """
        from django.db.models import Subquery, OuterRef, F, Value
        from django.db.models.functions import Coalesce, JSONObject
        from django.contrib.postgres.aggregates import ArrayAgg
        from django.contrib.postgres.fields import ArrayField
        from django.db.models import JSONField
        from orders.models import ExternalOrderStatus
        from core.middleware.refresh_token import get_current_request
        # Define field paths based on context
        if context == 'order':
            # When querying from Order model directly
            current_status_id_field = 'delivery_operation__current_status_id'
            current_status_name_field = 'delivery_operation__current_status__name'
            current_status_code_field = 'delivery_operation__current_status__code'
            current_status_color_field = 'delivery_operation__current_status__color_code'
        else:
            # When querying from DeliveryOperation model (default)
            current_status_id_field = 'current_status_id'
            current_status_name_field = 'current_status__name'
            current_status_code_field = 'current_status__code'
            current_status_color_field = 'current_status__color_code'
        group = get_current_request().user.userprofilelink.group if hasattr(get_current_request().user, 'userprofilelink') and get_current_request().user.userprofilelink else None
        # Subquery to aggregate all external statuses mapped to the current delivery status
        # We intentionally do NOT filter by external status value; we collect all for that status
        external_status_list_subquery = (
            ExternalOrderStatus.objects.filter(
                delivery_mappings__delivery_status_id=OuterRef(current_status_id_field),
                delivery_mappings__is_active=True,
                delivery_mappings__deleted__isnull=True,
                is_active=True,
                deleted__isnull=True,
                group=group,
            )
            .annotate(
                obj=JSONObject(
                    name=F('name'),
                    code=F('value'),
                    text_color=F('text_color'),
                    background_color=F('background_color'),
                    border_color=F('border_color'),
                )
            )
            .values('delivery_mappings__delivery_status_id')
            .annotate(status_list=ArrayAgg('obj', distinct=True))
            .values('status_list')[:1]
        )
        annotations = {
            'mapped_status_list': Coalesce(
                Subquery(external_status_list_subquery),
                Value([], output_field=ArrayField(base_field=JSONField()))
            ),
            # Legacy single-value fields (fallback to current internal status fields)
            'mapped_status': F(current_status_name_field),
            'mapped_status_code': F(current_status_code_field),
            'mapped_status_text_color': F(current_status_color_field),
            'mapped_status_background_color': F(current_status_color_field),
            'mapped_status_border_color': F(current_status_color_field),
        }
        return annotations
    
    @staticmethod
    def get_external_status_mapping_for_delivery_operation(delivery_operation) -> Optional[str]:
        """
        Get external status mapping for a specific delivery operation instance
        Used in signals and other contexts where we have the instance
        
        Args:
            delivery_operation: DeliveryOperation instance
            
        Returns:
            Optional[str]: External status code or None if no mapping found
        """
        try:
            from orders.models import ExternalOrderStatus
            from core.middleware.refresh_token import get_current_request
            
            if not delivery_operation.current_status:
                return None
                
            # Get current user's group 
            request = get_current_request()
            group = None
            if request and hasattr(request, 'user') and hasattr(request.user, 'userprofilelink'):
                group = request.user.userprofilelink.group if request.user.userprofilelink else None
            
            # Query for external status mapping
            external_status = ExternalOrderStatus.objects.filter(
                delivery_mappings__delivery_status_id=delivery_operation.current_status.id,
                delivery_mappings__is_active=True,
                delivery_mappings__deleted__isnull=True,
                is_active=True,
                deleted__isnull=True,
                group=group,
            ).first()
            
            if external_status:
                return external_status.value  # Return external status code
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting external status mapping: {str(e)}")
            
        return None
    
    @staticmethod 
    def get_external_status_mapping_with_fallback(delivery_operation) -> str:
        """
        Get external status mapping with fallback to default mapping
        
        Args:
            delivery_operation: DeliveryOperation instance
            
        Returns:
            str: External status code (mapped or fallback)
        """
        # Try to get dynamic mapping first
        external_status = StatusMappingService.get_external_status_mapping_for_delivery_operation(delivery_operation)
        
        if external_status:
            return external_status
            
        # Fallback to default mapping if no dynamic mapping found
        status_code = delivery_operation.current_status.code if delivery_operation.current_status else None
        
        default_mapping = {
            'pending': 'PENDING',
            'in_progress': 'IN_TRANSIT',
            'completed_order': 'DELIVERED',
            'cancelled': 'CANCELLED',
            'failed': 'FAILED'
        }
        
        return default_mapping.get(status_code, 'UNKNOWN')