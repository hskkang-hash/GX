from typing import List
from django.db import transaction, models
from ninja.errors import ValidationError
from orders.models import OrderStatusMapping, ExternalOrderStatus
from delivery.models import DeliveryStatus
from core.common.search.dynamic_search import apply_dynamic_filters
from core.user.models import CoreUser
from core.user.models import UserGroup
from common.constant import MESSAGE_ENUM


class OrderStatusMappingService:
    """
    Service class for managing OrderStatusMapping operations.
    Handles mapping between delivery statuses and external order statuses.
    """
    
    @staticmethod
    def _build_group_record(group_id: int, mappings: List[OrderStatusMapping]) -> dict:
        """Aggregate multiple OrderStatusMapping rows of a group into a single record."""
        if not mappings:
            return {}
        group = mappings[0].group
        name = None
        created_on = None
        modified_on = None
        mapping_items: List[dict] = []
        for m in mappings:
            if not name and m.name:
                name = m.name
            if created_on is None or (m.created_on and m.created_on < created_on):
                created_on = m.created_on
            if modified_on is None or (m.modified_on and m.modified_on > modified_on):
                modified_on = m.modified_on
            mapping_items.append({
                'delivery_status_id': m.delivery_status_id,
                'delivery_status_name': m.delivery_status.name if m.delivery_status else None,
                'external_order_statuses': [
                    {
                        'id': ext.id,
                        'name': ext.name,
                        'value': ext.value,
                        'description': ext.description,
                        'is_active': ext.is_active,
                    }
                    for ext in m.external_order_statuses.all()
                ]
            })
        if not name and group is not None:
            name = f"Status mapping for {group.name}"
        return {
            'id': group_id,  # represent group record by group_id
            'group_id': group_id,
            'group_name': group.name if group else None,
            'name': name,
            'created_on': created_on,
            'modified_on': modified_on,
            'mappings': mapping_items,
        }

    @staticmethod
    @transaction.atomic
    def create(data: dict, user: CoreUser = None) -> OrderStatusMapping:
        """
        Create a new order status mapping with ManyToMany external order statuses.
        
        Args:
            data: Dictionary containing mapping data
            user: User creating the mapping
            
        Returns:
            OrderStatusMapping: Created mapping instance
            
        Raises:
            ValidationError: If required fields are missing or invalid
        """
        # Validate required fields
        if not data.get('delivery_status_id'):
            raise ValidationError("delivery_status_id is required")
        # Support both keys from UI/schema
        external_status_ids = data.get('external_order_status_ids') or data.get('external_order_statuses')
        if not external_status_ids or not isinstance(external_status_ids, list):
            raise ValidationError("external_order_status_ids is required and must be a list")
        
        # Validate delivery status exists
        try:
            delivery_status = DeliveryStatus.objects.get(id=data['delivery_status_id'])
        except DeliveryStatus.DoesNotExist:
            raise ValidationError("Delivery status not found")
        
        # Validate external order statuses exist
        external_statuses = ExternalOrderStatus.objects.filter(id__in=external_status_ids)
        if external_statuses.count() != len(external_status_ids):
            raise ValidationError("Some external order statuses not found")
        
        # Determine group id from either group or group_id
        group_id = data.get('group_id') or (getattr(data.get('group'), 'id', None) if data.get('group') else None)
        
        # Check if mapping already exists for the same delivery_status and group
        if group_id is not None:
            existing = OrderStatusMapping.objects.filter(
                delivery_status=delivery_status,
                group_id=group_id
            ).first()
            if existing:
                raise ValidationError("Mapping already exists for this delivery_status and group combination")
        
        # Create mapping without external_order_status_ids field
        mapping_data = data.copy()
        # Normalize keys for creation
        mapping_data.pop('external_order_status_ids', None)
        mapping_data.pop('external_order_statuses', None)
        # Ensure we set group by id to avoid passing a model instance
        if group_id is not None:
            mapping_data['group_id'] = group_id
            # Remove potential 'group' instance key to avoid conflicts
            mapping_data.pop('group', None)
        # Default name if not provided
        if not mapping_data.get('name') and group_id is not None:
            try:
                group = UserGroup.objects.get(id=group_id)
                mapping_data['name'] = f"Status mapping for {group.name}"
            except UserGroup.DoesNotExist:
                pass
        
        mapping = OrderStatusMapping.objects.create(**mapping_data)
        
        # Add the ManyToMany relationships
        mapping.external_order_statuses.set(external_statuses)
        
        return mapping
    
    @staticmethod
    @transaction.atomic
    def update(mapping_id: int, data: dict, user: CoreUser = None) -> OrderStatusMapping:
        """
        Update an existing order status mapping.
        
        Args:
            mapping_id: ID of the mapping to update
            data: Dictionary containing updated data
            user: User updating the mapping
            
        Returns:
            OrderStatusMapping: Updated mapping instance
            
        Raises:
            ValidationError: If mapping not found or validation fails
        """
        try:
            mapping = OrderStatusMapping.objects.get(id=mapping_id)
        except OrderStatusMapping.DoesNotExist:
            raise ValidationError("Order status mapping not found")
        
        # Validate delivery status if it's being changed
        if 'delivery_status_id' in data:
            try:
                DeliveryStatus.objects.get(id=data['delivery_status_id'])
            except DeliveryStatus.DoesNotExist:
                raise ValidationError("Delivery status not found")
        
        # Validate external order statuses if they're being changed
        external_statuses = None
        if 'external_order_status_ids' in data or 'external_order_statuses' in data:
            external_status_ids = data.get('external_order_status_ids') or data.get('external_order_statuses')
            if not isinstance(external_status_ids, list):
                raise ValidationError("external_order_status_ids must be a list")
            
            external_statuses = ExternalOrderStatus.objects.filter(id__in=external_status_ids)
            if external_statuses.count() != len(external_status_ids):
                raise ValidationError("Some external order statuses not found")
        
        # Check for duplicate mapping if delivery_status is being changed
        if 'delivery_status_id' in data:
            delivery_status_id = data['delivery_status_id']
            
            existing = OrderStatusMapping.objects.filter(
                delivery_status_id=delivery_status_id,
                group_id=mapping.group_id
            ).exclude(id=mapping_id).first()
            
            if existing:
                raise ValidationError("Mapping already exists for this delivery_status and group combination")
        
        # Update fields (excluding external_order_status_ids which needs special handling)
        update_data = data.copy()
        update_data.pop('external_order_status_ids', None)
        update_data.pop('external_order_statuses', None)
        # Ensure we never set raw 'group' instance from payload
        for key, value in update_data.items():
            if hasattr(mapping, key):
                setattr(mapping, key, value)
        
        mapping.save()
        # Update ManyToMany relationship if provided
        if external_statuses is not None:
            mapping.external_order_statuses.set(external_statuses)
        
        return mapping
    
    @staticmethod
    @transaction.atomic
    def upsert_bulk(
        group_id: int,
        mappings: List[dict],
        prune_missing: bool = False,
        default_is_active: bool | None = None,
        user: CoreUser = None,
    ) -> List[OrderStatusMapping]:
        """Create/update mappings per delivery_status in a group.
        - If prune_missing=True: delete mappings in the group whose delivery_status_id is not present
          among items with non-None external list.
        - external_order_status_ids semantics:
          None  -> skip this delivery_status (do not create/update; considered missing → pruned if enabled)
          []    -> clear mapping's externals (create mapping if not exists)
          [ids] -> replace with given externals
        """
        provided_ids: List[int] = []
        results: List[OrderStatusMapping] = []
        for item in mappings:
         
            delivery_status_id = item.get('delivery_status_id')
            if not delivery_status_id:
                raise ValidationError("delivery_status_id is required for each mapping item")

            ext_ids = item.get('external_order_status_ids') or item.get('external_order_statuses')
           
            if ext_ids is None:
                # skip touching this status; let prune handle deletion if enabled
                continue

            if not isinstance(ext_ids, list) or ext_ids is None: 
                # also accept 'external_order_statuses'
                ext_ids = item.get('external_order_statuses')
                if ext_ids is None:
                    continue
                if not isinstance(ext_ids, list):
                    raise ValidationError("external_order_status_ids must be a list for each mapping item")

            # Validate existence
            try:
                DeliveryStatus.objects.get(id=delivery_status_id)
            except DeliveryStatus.DoesNotExist:
                raise ValidationError(f"Delivery status not found: {delivery_status_id}")

            external_statuses = ExternalOrderStatus.objects.filter(id__in=ext_ids)
            if ext_ids and external_statuses.count() != len(ext_ids):
                raise ValidationError("Some external order statuses not found")

            # Upsert mapping
            mapping = OrderStatusMapping.objects.filter(
                delivery_status_id=delivery_status_id,
                group_id=group_id
            ).first()
            if not mapping:
                mapping = OrderStatusMapping.objects.create(
                    delivery_status_id=delivery_status_id,
                    group_id=group_id,
                    is_active=True,
                    name=item.get('name') or (
                        f"Status mapping for {UserGroup.objects.get(id=group_id).name}"
                        if UserGroup.objects.filter(id=group_id).exists() else None
                    ),
                )
            is_active = item.get('is_active')
            if is_active is None:
                is_active = default_is_active if default_is_active is not None else True

            if mapping is None:
                mapping = OrderStatusMapping.objects.create(
                    delivery_status_id=delivery_status_id,
                    group_id=group_id,
                    is_active=is_active,
                    name=item.get('name') or (
                        f"Status mapping for {UserGroup.objects.get(id=group_id).name}"
                        if UserGroup.objects.filter(id=group_id).exists() else None
                    ),
                )
            else:
                mapping.is_active = is_active
                if 'name' in item and item['name'] is not None:
                    mapping.name = item['name']
                mapping.save()

            # Replace M2M with list (can be empty to clear)
            mapping.external_order_statuses.set(external_statuses)
            results.append(mapping)
            provided_ids.append(delivery_status_id)

        if prune_missing:
            OrderStatusMapping.objects.filter(group_id=group_id).exclude(
                delivery_status_id__in=provided_ids
            ).delete()
        
        return results
    
    @staticmethod
    @transaction.atomic
    def delete(group_ids: List[int], user: CoreUser = None) -> tuple[bool, str]:
        """
        Delete an order status mapping.
        
        Args:
            mapping_id: ID of the mapping to delete
            user: User deleting the mapping
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            mapping = OrderStatusMapping.objects.filter(group_id__in=group_ids)
        except OrderStatusMapping.DoesNotExist:
            return False, "Order status mapping not found"
        
        mapping.delete()
        return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
    
    @staticmethod
    def get_by_id(mapping_id: int) -> OrderStatusMapping:
        """
        Get order status mapping by ID.
        
        Args:
            mapping_id: ID of the mapping
            
        Returns:
            OrderStatusMapping: Mapping instance
            
        Raises:
            ValidationError: If mapping not found
        """
        try:
            return OrderStatusMapping.objects.select_related(
                'delivery_status',  'group'
            ).get(id=mapping_id)
        except OrderStatusMapping.DoesNotExist:
            raise ValidationError("Order status mapping not found")
    
    @staticmethod
    def get_list(request=None, group_id: int = None):
        """
        Get list of order status mappings with dynamic filtering.
        
        Args:
            request: Request object for dynamic filtering
            group_id: Filter by group ID
            
        Returns:
            QuerySet: Filtered mappings
        """
        queryset = OrderStatusMapping.objects.select_related(
            'delivery_status','group'
        ).annotate(group__id=models.F('group_id'))
        
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
        if group_id:
            return queryset.order_by('-id') 
        else:
            return queryset.order_by('group','-id').distinct('group')
    
    @staticmethod
    def get_available_statuses_for_group(group_id: int) -> dict:
        """
        Get available delivery statuses and external order statuses for a group.
        
        Args:
            group_id: Group ID to get statuses for
            
        Returns:
            dict: Dictionary containing delivery_statuses and external_order_statuses
        """
        # Get all delivery statuses (system-wide)
        delivery_statuses = DeliveryStatus.objects.all().order_by('name')
        
        # Get external order statuses for the specific group
        external_statuses = ExternalOrderStatus.objects.filter(
            group_id=group_id, is_active=True
        ).order_by('name')
        
        return {
            'delivery_statuses': delivery_statuses,
            'external_order_statuses': external_statuses
        }
    
    @staticmethod
    def get_mapped_delivery_status(external_status_code: str, group_id: int) -> DeliveryStatus:
        """
        Get the mapped delivery status for an external status code.
        
        Args:
            external_status_code: External status code/value from API
            group_id: Group ID for the mapping
            
        Returns:
            DeliveryStatus: Mapped delivery status or None
        """
        try:
            # Find external order status by value and group
            external_status = ExternalOrderStatus.objects.get(
                value=external_status_code,
                group_id=group_id,
                is_active=True
            )
            
            # Find the mapping with highest priority
            mapping = OrderStatusMapping.objects.filter(
                group_id=group_id,
                is_active=True
            ).order_by('-id').first()
            
            if mapping:
                return mapping.delivery_status
            
        except ExternalOrderStatus.DoesNotExist:
            pass
        
        return None
    
    @staticmethod
    def get_data(mapping_id: int) -> dict:
        """
        Get formatted data for order status mapping.
        
        Args:
            mapping_id: ID of the mapping
            
        Returns:
            dict: Formatted mapping data
        """
        mapping = OrderStatusMappingService.get_by_id(mapping_id)
        
        return {
            'id': mapping.id,
            'delivery_status_id': mapping.delivery_status_id,
            'delivery_status_name': mapping.delivery_status.name,
            'external_order_status_ids': mapping.external_order_statuses.values_list('id', flat=True),
            'is_active': mapping.is_active,
            'group_id': mapping.group_id,
            'group_name': mapping.group.name if mapping.group else None,
            'created_on': mapping.created_on,
            'modified_on': mapping.modified_on
        } 