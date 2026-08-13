from django.db import models
from django.utils import timezone
from terminals.models import Terminal, Routes, RouteTerminal
from core.base import BaseModel
from devices.models import Device, PackagingSpecification
from core.user.models import CoreUser
from core.base import BaseModelWithGroup
class Address(BaseModel):
    """
    Model representing a physical address (pickup, delivery, sender/recipient).
    """
    city = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    ward = models.CharField(max_length=100, null=True, blank=True)
    street = models.CharField(max_length=255, null=True, blank=True)
    province_name = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    full_address = models.CharField(max_length=500, null=True, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.full_address or f"{self.street}, {self.ward}, {self.district}, {self.city}"

    class Meta:
        ordering = ['-created_on']
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'


class DeliveryStatus(BaseModel):
    """
    Model representing the status of a delivery.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    color_code = models.CharField(max_length=20, null=True, blank=True, help_text="Hex color code (e.g. #FF5733)")
    TRANSLATABLE_FIELDS = ['name', 'description']
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']
        verbose_name = 'Delivery Status'
        verbose_name_plural = 'Delivery Statuses'


class DeliveryOperation(BaseModel):
    """
    Model representing a delivery operation associated with an order.
    """
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='delivery_operation')
    current_status = models.ForeignKey(DeliveryStatus, on_delete=models.PROTECT, related_name='delivery_operations')
    route = models.ForeignKey(Routes, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivery_operations', db_index=True)
    another_info = models.JSONField(null=True, blank=True)
    confirmation_photo = models.ImageField(upload_to='delivery_confirmations/', null=True, blank=True)
    is_partial_approved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Delivery for Order {self.order_id}"

    class Meta:
        ordering = ['id']
        verbose_name = 'Delivery Operation'
        verbose_name_plural = 'Delivery Operations'
        indexes = [
            models.Index(fields=['route']),
        ]


class DeliveryOperationItem(BaseModel):
    """
    Model representing items/packages handled in a delivery operation.
    """
    delivery_operation = models.ForeignKey(DeliveryOperation, on_delete=models.CASCADE, related_name='items', db_index=True)
    order_item = models.OneToOneField('orders.OrderItem', on_delete=models.PROTECT, related_name='delivery_item', null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    drone = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivery_items')

    is_drone_approved = models.BooleanField(default=False)

    is_delivered_by_drone = models.BooleanField(default=False)
    drone_arrived_at = models.DateTimeField(null=True, blank=True)

    is_arrived = models.BooleanField(default=False)
    arrived_at = models.DateTimeField(null=True, blank=True)

    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    upload_mission = models.BooleanField(default=False)

    def __str__(self):
        return f"Item {self.id}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Delivery Operation Item'
        verbose_name_plural = 'Delivery Operation Items'
        indexes = [
            models.Index(fields=['delivery_operation']),
            models.Index(fields=['delivery_operation', 'order_item']),
        ]

# History of returned deliveries
class DeliveryReturn(BaseModel):
    """
    Model to handle returned deliveries.
    """
    delivery_operation = models.ForeignKey(DeliveryOperation, on_delete=models.CASCADE, related_name='returns')
    status_return = models.ForeignKey(DeliveryStatus, on_delete=models.PROTECT, 
                                      null=True, blank=True, related_name='delivery_returns')
    returned_at = models.DateTimeField(auto_now_add=True)
    return_terminal = models.ForeignKey(Terminal, on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='delivery_returns')

    def __str__(self):
        return f"Return of {self.delivery_operation}"

    class Meta:
        ordering = ['-returned_at']
        verbose_name = 'Delivery Return'
        verbose_name_plural = 'Delivery Returns'


class DeliveryCancellationType(BaseModel):
    """
    Model representing types of cancellation reasons.
    """
    code = models.CharField(max_length=50, unique=True)
    reason_default = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.code

    class Meta:
        ordering = ['id']
        verbose_name = 'Cancellation Reason Type'
        verbose_name_plural = 'Cancellation Reason Types'


# History of cancelled deliveries
class DeliveryCancellation(BaseModel):
    """
    Model for handling canceled deliveries.
    """
    delivery_operation = models.ForeignKey(DeliveryOperation, on_delete=models.CASCADE, related_name='cancellations')
    reason_type = models.ForeignKey(DeliveryCancellationType, on_delete=models.PROTECT, related_name='cancellations',null=True, 
    blank=True)
    reason = models.TextField(null=True, blank=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)
    cancelled_by = models.ForeignKey(CoreUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_deliveries')

    def __str__(self):
        return f"Cancellation of {self.delivery_operation}"

    class Meta:
        ordering = ['-cancelled_at']
        verbose_name = 'Delivery Cancellation'
        verbose_name_plural = 'Delivery Cancellations'


class DeliveryOperationHistory(BaseModel):
    """
    Model for tracking the history of status changes for delivery operations.
    """
    delivery_operation = models.ForeignKey(DeliveryOperation, on_delete=models.CASCADE, related_name='status_history')
    status = models.ForeignKey(DeliveryStatus, on_delete=models.PROTECT, related_name='status_history_entries')
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(CoreUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivery_status_changes')
    
    def __str__(self):
        return f"Status change to {self.status.name} for {self.delivery_operation}"
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Delivery Operation History'
        verbose_name_plural = 'Delivery Operation Histories'


class DeliveryOperationApproval(BaseModel):
    """Per-drone approval state for a delivery operation."""
    delivery_operation = models.ForeignKey(DeliveryOperation, on_delete=models.CASCADE, related_name='approvals')
    drone = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='operation_approvals')
    approved = models.BooleanField(default=True)
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (( 'delivery_operation', 'drone' ),)
        verbose_name = 'Delivery Operation Approval'
        verbose_name_plural = 'Delivery Operation Approvals'


class DeliveryOperationApprovalChecklist(BaseModel):
    """Checklist selections linked to an approval, with snapshots to preserve history."""
    approval = models.ForeignKey(DeliveryOperationApproval, on_delete=models.CASCADE, related_name='checklists')
    checklist = models.ForeignKey('checklist_setting.ChecklistSetting', on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_links')
    item_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    category_code_snapshot = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = (( 'approval', 'checklist' ),)
        verbose_name = 'Delivery Operation Approval Checklist'
        verbose_name_plural = 'Delivery Operation Approval Checklists'


class TerminalSequence(BaseModel):
    """
    Model to track the sequence of terminals that a drone must visit for a delivery operation.
    This helps handle cases where multiple terminals have the same coordinates.
    """
    delivery_operation = models.ForeignKey(
        'DeliveryOperation', 
        on_delete=models.CASCADE,
        related_name='terminal_sequences',
        help_text="The delivery operation this sequence belongs to"
    )
    routeterminal = models.ForeignKey(
        RouteTerminal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The route terminal in the sequence"
    )
    sequence_order = models.PositiveIntegerField(
        help_text="The order in which this terminal should be visited (1, 2, 3, ...)"
    )
    is_visited = models.BooleanField(
        default=False,
        help_text="Whether the drone has already visited this terminal"
    )
    visited_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When the drone visited this terminal"
    )
    drone = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The drone that visited this terminal"
    )
    coordinates_lat = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        help_text="Terminal latitude at time of sequence creation"
    )
    coordinates_lon = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        help_text="Terminal longitude at time of sequence creation"
    )
    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Additional notes about this terminal sequence"
    )
    is_special_case = models.BooleanField(
        default=False,
        help_text="Whether this terminal sequence is marked as special case based on command_line ID"
    )

    def __str__(self):
        return f"{self.delivery_operation.order.order_code} - Terminal {self.routeterminal.terminal.name} (Order: {self.sequence_order})"

    class Meta:
        ordering = ['delivery_operation', 'sequence_order']
        # unique_together = (('delivery_operation', 'routeterminal'), ('delivery_operation', 'sequence_order'))
        verbose_name = 'Terminal Sequence'
        verbose_name_plural = 'Terminal Sequences'
        indexes = [
            models.Index(fields=['delivery_operation', 'sequence_order']),
            models.Index(fields=['delivery_operation', 'is_visited']),
            models.Index(fields=['routeterminal', 'is_visited']),
        ]

    def mark_as_visited(self, drone=None):
        """Mark this terminal sequence as visited by a drone"""
        self.is_visited = True
        self.visited_at = timezone.now()
        if drone:
            self.drone = drone
        self.save()

    @classmethod
    def get_next_unvisited_terminal(cls, delivery_operation):
        """Get the next unvisited terminal in sequence for a delivery operation"""
        return cls._base_manager.filter(
            delivery_operation=delivery_operation,
            is_visited=False
        ).order_by('sequence_order').first()

    @classmethod
    def get_visited_terminals(cls, delivery_operation):
        """Get all visited terminals for a delivery operation"""
        return cls._base_manager.filter(
            delivery_operation=delivery_operation,
            is_visited=True
        ).order_by('sequence_order')

    @classmethod
    def get_all_terminals_in_sequence(cls, delivery_operation, drone):
        """Get all terminals in sequence for a delivery operation"""
        return cls._base_manager.filter(
            delivery_operation=delivery_operation,
            drone=drone
        ).order_by('sequence_order')

    @classmethod
    def create_sequence_from_route(cls, delivery_operation, route_terminals):
        """
        Create terminal sequence from route terminals.
        DEPRECATED: Use ProcessingService.create_terminal_sequence_for_delivery() instead.
        This method is kept for backward compatibility.
        """
        sequences = []
        for index, terminal in enumerate(route_terminals, 1):
            sequence = cls.objects.create(
                delivery_operation=delivery_operation,
                terminal=terminal,
                sequence_order=index,
                coordinates_lat=terminal.latitude,
                coordinates_lon=terminal.longitude
            )
            sequences.append(sequence)
        return sequences


