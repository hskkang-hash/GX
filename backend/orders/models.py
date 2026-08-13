from django.db import models
from devices.models import Device
from delivery.models import Address
from core.base import BaseModel
from terminals.models import Routes, Terminal
from core.user.models import CoreUser
from devices.models import PackagingSpecification
# from common.base_model import BaseModelWithGroup
from core.base import BaseModelWithGroup
from core.fields.money import EnhancedMoneyField
# Create your models here.
class PaymentType(BaseModel):
    """
    Model representing payment methods and providers.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=100, null=True, blank=True)
    method = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    note = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name']
     
    def __str__(self):
        return f"{self.name} ({self.provider})"


class Sender(BaseModel):
    """
    Model representing a sender of a delivery.
    """
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='sender_address')
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='sender_user', null=True, blank=True)


class Recipient(BaseModel):
    """
    Model representing a recipient of a delivery.
    """
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='recipient_address')
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='recipient_user', null=True, blank=True)


class GuessUser(BaseModel):
    """
    Model representing a guess user of a delivery.
    """
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='guess_users')


class DeliveryOption(BaseModel):
    """
    Model representing delivery options.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description']


class OrderStatus(BaseModel):
    """
    Model representing the status of an order.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)


class ExternalOrderStatus(BaseModelWithGroup):
    """
    Model for storing order statuses received from external APIs.
    Each group can define their own set of external order statuses for mapping.
    """
    name = models.CharField(max_length=100, help_text="Display name for this external order status")
    value = models.CharField(max_length=100, help_text="Value/code received from external API")
    description = models.TextField(null=True, blank=True, help_text="Description of this status")
    is_active = models.BooleanField(default=True, help_text="Whether this status is active")
    text_color = models.CharField(max_length=20, null=True, blank=True, help_text="Text color for this status")
    background_color = models.CharField(max_length=20, null=True, blank=True, help_text="Background color for this status")
    border_color = models.CharField(max_length=20, null=True, blank=True, help_text="Border color for this status")
    TRANSLATABLE_FIELDS = ['name', 'description']
    
    def __str__(self):
        return f"{self.name} ({self.value}) - {self.group.name if self.group else 'Global'}"
    
    class Meta:
        ordering = ['group', 'name']
        verbose_name = 'External Order Status'
        verbose_name_plural = 'External Order Statuses'
        unique_together = [['value', 'group']]  # One value per group


class OrderStatusMapping(BaseModelWithGroup):
    """
    Model for mapping delivery status with external order statuses for different groups/organizations.
    Allows mapping one delivery status to multiple external order statuses.
    One delivery status can map to multiple external order status values to handle different external APIs.
    """
    name = models.CharField(max_length=255, null=True, blank=True)
    delivery_status = models.ForeignKey('delivery.DeliveryStatus', on_delete=models.CASCADE, related_name='order_status_mappings')
    external_order_statuses = models.ManyToManyField(ExternalOrderStatus, related_name='delivery_mappings', help_text="External order statuses that map to this delivery status")
    is_active = models.BooleanField(default=True, help_text="Whether this mapping is active")
    
    def __str__(self):
        external_values = ", ".join([ext.value for ext in self.external_order_statuses.all()[:3]])
        if self.external_order_statuses.count() > 3:
            external_values += "..."
        prefix = f"{self.name} - " if self.name else ""
        return f"{prefix}{self.delivery_status.name} <- [{external_values}] ({self.group.name if self.group else 'Global'})"
    
    class Meta:
        ordering = ['group', 'delivery_status']
        verbose_name = 'Order Status Mapping'
        verbose_name_plural = 'Order Status Mappings'
        unique_together = [['delivery_status', 'group']]  # One mapping per delivery_status + group combination


class Order(BaseModel):
    """
    Model representing an order to be delivered.
    """
    order_code = models.CharField(max_length=100, unique=True)
    sender_name = models.CharField(max_length=255, null=True, blank=True)
    sender_phone = models.CharField(max_length=20, null=True, blank=True)
    sender_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='sender_orders', null=True, blank=True)
    recipient_name = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=20)
    recipient_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='received_orders')
    pickup_location = models.ForeignKey(Terminal, on_delete=models.PROTECT, related_name='pickup_orders', null=True, blank=True)
    status = models.ForeignKey(OrderStatus, on_delete=models.SET_NULL, null=True, related_name='orders')
    delivery_option = models.ForeignKey(DeliveryOption, on_delete=models.SET_NULL, null=True, related_name='orders')
    delivery_terminal = models.ForeignKey(Terminal, on_delete=models.SET_NULL, null=True, related_name='orders')
    created_by = models.ForeignKey(CoreUser, on_delete=models.SET_NULL, null=True, related_name='created_orders')
    created_by_guess = models.ForeignKey(GuessUser, on_delete=models.SET_NULL, null=True, related_name='created_orders')
    created_on = models.DateTimeField(auto_now_add=True)
    sender_note = models.TextField(null=True, blank=True)
    recipient_note = models.TextField(null=True, blank=True)
    cancel_reason = models.TextField(null=True, blank=True)
    another_info = models.JSONField(null=True, blank=True)
    
    # External API status tracking
    external_status_code = models.CharField(max_length=100, null=True, blank=True, 
                                           help_text="Status code/ID received from external API")
    
    # Money Fields using AdminConfig base currency
    subtotal = EnhancedMoneyField(null=True, blank=True, help_text="Subtotal of all order items")
    delivery_fee = EnhancedMoneyField(null=True, blank=True, help_text="Delivery/shipping fee")
    tax_amount = EnhancedMoneyField(null=True, blank=True, help_text="Tax amount")
    discount_amount = EnhancedMoneyField(null=True, blank=True, help_text="Discount amount")
    total_amount = EnhancedMoneyField(null=True, blank=True, help_text="Total amount to be paid")
    
    def __str__(self):
        return f"Order {self.order_code}"
    
    def calculate_totals(self):
        """Calculate order totals from items"""
        from core.fields.money import Money
        from decimal import Decimal
        
        # Calculate subtotal from items using Money objects
        subtotal = Money(Decimal('0'), None)  # Start with zero Money object
        
        for item in self.items.all():
            if item.amount and not item.amount.is_null:
                # Use Money addition operator
                subtotal = subtotal + item.amount
        
        # Only update if different from current value
        if not self.subtotal or self.subtotal.raw_amount != subtotal.raw_amount:
            self.subtotal = subtotal.raw_amount
        
        # Calculate total using Money operations
        total = subtotal
        
        # Add delivery fee if exists
        if self.delivery_fee and not self.delivery_fee.is_null:
            total = total + self.delivery_fee
        
        # Add tax amount if exists  
        if self.tax_amount and not self.tax_amount.is_null:
            total = total + self.tax_amount
        
        # Subtract discount if exists
        if self.discount_amount and not self.discount_amount.is_null:
            total = total - self.discount_amount
            
        # Only update if different from current value
        if not self.total_amount or self.total_amount.raw_amount != total.raw_amount:
            self.total_amount = total.raw_amount
        
        return total.raw_amount
    
    class Meta:
        ordering = ['-created_on']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'


class OrderItemType(BaseModel):
    """
    Model representing types of items in an order.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    TRANSLATABLE_FIELDS = ['name']


class OrderItem(BaseModel):
    """
    Model representing items in an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, null=True, blank=True, unique=True)
    weight = models.JSONField(null=True, blank=True)  # Changed to JSONField with {"value": float_value, "unit": "kg"}
    dimension_l = models.JSONField(null=True, blank=True)  # JSONField with {"value": float_value, "unit": "mm"}
    dimension_w = models.JSONField(null=True, blank=True)  # JSONField with {"value": float_value, "unit": "mm"}
    dimension_h = models.JSONField(null=True, blank=True)  # JSONField with {"value": float_value, "unit": "mm"}
    is_waterproof = models.BooleanField(default=False)
    is_fragile = models.BooleanField(default=False)
    item_type = models.ForeignKey(OrderItemType, on_delete=models.SET_NULL, null=True, related_name='order_items')
    package_id = models.ForeignKey(PackagingSpecification, on_delete=models.SET_NULL, null=True, related_name='order_items')
    amount = EnhancedMoneyField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.order.order_code}"
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'


class ProductItem(BaseModel):
    """
    Model representing individual products within an OrderItem.
    One OrderItem can contain multiple ProductItems.
    This aligns with Anyang API requirements where one package can contain multiple products.
    """
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255, help_text="Product name")
    description = models.TextField(null=True, blank=True, help_text="Product description")
    quantity = models.PositiveIntegerField(default=1, help_text="Quantity of this product")
    unit_weight = models.JSONField(null=True, blank=True, help_text='Weight per unit: {"value": float, "unit": "kg"}')
    unit_price = EnhancedMoneyField(null=True, blank=True, help_text="Price per unit")
    total_price = EnhancedMoneyField(null=True, blank=True, help_text="Total price (unit_price * quantity)")
    
    # Product characteristics for Anyang API
    product_type = models.CharField(max_length=100, null=True, blank=True, help_text="Product type classification")
    is_dangerous = models.BooleanField(default=False, help_text="Whether product is dangerous goods")
    is_temperature_sensitive = models.BooleanField(default=False, help_text="Requires temperature control")
    manufacturer = models.CharField(max_length=255, null=True, blank=True, help_text="Product manufacturer")
    model_number = models.CharField(max_length=100, null=True, blank=True, help_text="Product model/SKU")
    
    # Tracking and compliance
    customs_code = models.CharField(max_length=50, null=True, blank=True, help_text="Customs classification code")
    origin_country = models.CharField(max_length=100, null=True, blank=True, help_text="Country of origin")
    
    # Additional metadata
    another_info = models.JSONField(null=True, blank=True, help_text="Additional product information")
    
    def save(self, *args, **kwargs):
        # Auto-calculate total_price when saving
        if self.unit_price and not self.unit_price.is_null and self.quantity:
            from core.fields.money import Money
            from decimal import Decimal
            # Use Money multiplication operation
            total_money = self.unit_price * Decimal(str(self.quantity))
            self.total_price = total_money.raw_amount
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} (x{self.quantity}) - {self.order_item.name}"
    
    class Meta:
        ordering = ['order_item', 'id']
        verbose_name = 'Product Item'
        verbose_name_plural = 'Product Items'


class Payment(BaseModel):
    """
    Model representing payment for an order.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = EnhancedMoneyField()
    payment_type = models.ForeignKey(PaymentType, on_delete=models.PROTECT, related_name='payments')
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_order_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway_status_code = models.CharField(max_length=50, null=True, blank=True)
    gateway_response = models.TextField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    receipt_url = models.CharField(max_length=500, null=True, blank=True)
    receipt_issued = models.BooleanField(default=False)
    payer_phone = models.CharField(max_length=20, null=True, blank=True)
    
    
    def __str__(self):
        return f"{self.order.order_code} - {self.amount}"
    
    class Meta:
        ordering = ['-created_on']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'


class PaymentCallback(BaseModel):
    """
    Model representing callbacks from payment providers.
    """
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='callbacks')
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.payment.order.order_code} - {self.event_type}"
    
    class Meta:
        ordering = ['-received_at']
        verbose_name = 'Payment Callback'
        verbose_name_plural = 'Payment Callbacks'


class OrderAssignment(BaseModel):
    """
    Model representing assignment of an order to a device for delivery.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    )
    
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='assignments', default=None)
    route_id = models.ForeignKey(Routes, on_delete=models.CASCADE, related_name='assignments', default=None)  # Optional reference to a route
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='order_assignments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_on']
        verbose_name = 'Order Assignment'
        verbose_name_plural = 'Order Assignments'


class OrderAssignmentProcess(BaseModel):
    """
    Model representing steps in an order assignment process.
    """
    order_assignment = models.ForeignKey(OrderAssignment, on_delete=models.CASCADE, related_name='processes')
    step_name = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.order_assignment.order.order_code} - {self.step_name}"
    
    class Meta:
        ordering = ['order_assignment', 'started_at']
        verbose_name = 'Order Assignment Process'
        verbose_name_plural = 'Order Assignment Processes'

    
class DeliveryEvent(BaseModel):
    """
    Model representing events during delivery.
    """
    order_assignment = models.ForeignKey(OrderAssignment, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    terminal_stop = models.ForeignKey(Terminal, on_delete=models.SET_NULL, null=True, related_name='delivery_events')
    altitude = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    speed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    event_time = models.DateTimeField()
    
    class Meta:
        ordering = ['-event_time']
        verbose_name = 'Delivery Event'
        verbose_name_plural = 'Delivery Events'


class DeliveryProof(BaseModel):
    """
    Model representing proof of delivery.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='proofs')
    proof_type = models.CharField(max_length=50)  # e.g., signature, photo
    file_url = models.CharField(max_length=500, null=True, blank=True)
    received_by = models.CharField(max_length=255, null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.order.order_code} - {self.proof_type}"
    
    class Meta:
        ordering = ['-created_on']
        verbose_name = 'Delivery Proof'
        verbose_name_plural = 'Delivery Proofs'


class Invoice(BaseModel):
    """
    Model representing an invoice for a payment.
    """
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=100, unique=True)
    issued_at = models.DateTimeField()
    total_amount = EnhancedMoneyField(help_text="Total invoice amount")
    payment_status = models.CharField(max_length=20)
    pdf_url = models.CharField(max_length=500, null=True, blank=True)
    
    def __str__(self):
        return f"{self.invoice_number} - {self.payment.order.order_code}"
    
    class Meta:
        ordering = ['-issued_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'


class OrderComment(BaseModel):
    """
    Model representing a comment on an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='order_comments')
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', null=True, blank=True)


class OrderHistory(BaseModel):
    """
    Model representing the history of an order.
    """
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('cancelled', 'Cancelled'),
        ('paid', 'Paid'),
        ('verified', 'Verified'),
        ('arrived', 'Arrived'),
        ('shipped', 'Shipped'),
        ('completed', 'Completed'),
        ('returned', 'Returned'),
        ('refunded', 'Refunded'),
        ('started_delivery', 'Started Delivery'),
        ('arrived_at_terminal', 'Arrived at Terminal'),
        ('overdue', 'Overdue'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='histories')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    TRANSLATABLE_FIELDS = ['description']

    def __str__(self):
        return f"{self.order.order_code} "
    
    class Meta:
        ordering = ['-created_on']


class ReturnOrder(BaseModel):
    """
    Model representing a return order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_orders')
    return_terminal = models.ForeignKey(Terminal, on_delete=models.SET_NULL, null=True, related_name='return_orders')
    return_time_period = models.CharField(max_length=255, null=True, blank=True)
    return_received_time = models.DateTimeField(null=True, blank=True)
    return_days = models.IntegerField(null=True, blank=True)
    return_from_date = models.DateField(null=True, blank=True)
    return_to_date = models.DateField(null=True, blank=True)
    return_available = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.order.order_code} - {self.return_terminal.name}"
    
    class Meta:
        ordering = ['-created_on']


class Bank(BaseModel):
    """
    Model representing a refund bank.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    TRANSLATABLE_FIELDS = ['name']

class RefundOrder(BaseModel):
    """
    Model representing a refund order.
    """
    REFUND_TYPE_CHOICES = [
        ('bank', 'Bank'),
        ('cash', 'Cash'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refund_orders')
    refund_type = models.CharField(max_length=255, choices=REFUND_TYPE_CHOICES)
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, related_name='refund_orders')
    account_number = models.CharField(max_length=255)
    account_holder_name = models.CharField(max_length=255)
    
    # Money field for refund amount
    refund_amount = EnhancedMoneyField(help_text="Amount to be refunded", null=True, blank=True)
    processing_fee = EnhancedMoneyField(null=True, blank=True, help_text="Processing fee for refund")
    refund_status = models.CharField(max_length=50, default='pending', help_text="Status of refund process")
    refund_processed_at = models.DateTimeField(null=True, blank=True, help_text="When refund was processed")
    refund_reference = models.CharField(max_length=100, null=True, blank=True, help_text="Reference number from bank/payment provider")
    
    def get_net_refund_amount(self):
        """Calculate net refund amount after processing fee"""
        if not self.refund_amount or self.refund_amount.is_null:
            return None
        
        # Use Money operations for calculation
        net_money = self.refund_amount
        if self.processing_fee and not self.processing_fee.is_null:
            net_money = net_money - self.processing_fee
            
        return net_money.raw_amount
