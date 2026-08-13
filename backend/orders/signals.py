"""
Django signals for order status change notifications
"""
import json
import logging
from datetime import datetime
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from terminals.models import Terminal
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Order
from core.middleware.refresh_token import get_current_request

logger = logging.getLogger(__name__)

class OrderNotificationService:
    """Service class for sending order notifications via WebSocket"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def send_notification(self, event_type, order, **kwargs):
        """Send notification to appropriate WebSocket groups"""
        if not self.channel_layer:
            logger.warning("Channel layer not configured - notifications disabled")
            return
        
        try:
            # Prepare order data for notification
            order_data = self._prepare_order_data(order)
            
            # Prepare notification event
            event = {
                'type': event_type,
                'order': order_data,
                'timestamp': datetime.now().isoformat(),
                **kwargs
            }
            
            # Send to different groups based on event type
            self._send_to_groups(event, order)
            
        except Exception as e:
            logger.error(f"Error sending order notification: {e}")
    
    def _prepare_order_data(self, order):
        """Prepare order data for WebSocket notification"""
        pickup_location = Terminal._base_manager.get(id=order.pickup_location_id)
        return {
            'status.name': order.status.name if order.status else None,
            'pickup_location.city_county_district': pickup_location.city_county_district,
            'recipient_address.city': self._get_recipient_city(order) if self._get_recipient_city(order) else self._get_recipient_full_address(order),
            'modified_on': order.updated_on.isoformat() if hasattr(order, 'updated_on') and order.updated_on else None,
            'order_code': order.order_code,
            'recipient_name': order.recipient_name,
        }
    
    def _get_pickup_location_address(self, order):
        """Get pickup location address in city_county_district format"""
        if not order.pickup_location:
            return None
        
        # Assuming pickup_location has address fields
        try:
            pickup_location = order.pickup_location
            address_parts = []
            
            # Build address from available fields
            if hasattr(pickup_location, 'city') and pickup_location.city:
                address_parts.append(pickup_location.city)
            if hasattr(pickup_location, 'county') and pickup_location.county:
                address_parts.append(pickup_location.county)
            if hasattr(pickup_location, 'district') and pickup_location.district:
                address_parts.append(pickup_location.district)
            
            return '_'.join(address_parts) if address_parts else None
        except Exception as e:
            logger.error(f"Error getting pickup location address: {e}")
            return None
    
    def _get_recipient_city(self, order):
        """Get recipient address city"""
        try:
            if order.recipient_address and hasattr(order.recipient_address, 'city'):
                return order.recipient_address.city
            return None
        except Exception as e:
            logger.error(f"Error getting recipient city: {e}")
            return None
        
    def _get_recipient_full_address(self, order):
        """Get recipient address full address"""
        try:
            if order.recipient_address and hasattr(order.recipient_address, 'full_address'):
                return order.recipient_address.full_address
            return None
        except Exception as e:
            logger.error(f"Error getting recipient full address: {e}")
            return None
    
    def _send_to_groups(self, event, order):
        """Send event to appropriate WebSocket groups"""
        try:
            # # Send to global admin group
            # async_to_sync(self.channel_layer.group_send)('order_global', event)
            
            # Send to user-specific group (order creator)
            if order.created_by_id:
                user_group = order.created_by.userprofilelink.group.code
                async_to_sync(self.channel_layer.group_send)(user_group, event)

                current_user = get_current_request().user.username
                current_user_group = get_current_request().user.userprofilelink.group.code
                if current_user_group != user_group:
                    async_to_sync(self.channel_layer.group_send)(f'{current_user_group}_{current_user}', event)
            
            # # Send to order-specific group
            # order_group = f'order_{order.id}'
            # async_to_sync(self.channel_layer.group_send)(order_group, event)
            
            # Send to order tracking group (public tracking)
            # tracking_group = f'track_order_{order.order_code}'
            # async_to_sync(self.channel_layer.group_send)(tracking_group, event)
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")

# Global notification service instance
notification_service = OrderNotificationService()

@receiver(pre_save, sender=Order)
def capture_order_changes(sender, instance, **kwargs):
    """Capture order changes before saving"""
    if instance.pk:  # Existing order
        try:
            # Get the current state from database
            old_instance = Order.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
            instance._old_data = {
                'recipient_name': old_instance.recipient_name,
                'recipient_phone': old_instance.recipient_phone,
                'sender_name': old_instance.sender_name,
                'total_amount': str(old_instance.total_amount) if old_instance.total_amount else None,
            }
        except Order.DoesNotExist:
            instance._old_status = None
            instance._old_data = {}
        except Exception as e:
            logger.error(f"Error capturing order changes: {e}")
            instance._old_status = None
            instance._old_data = {}
    else:  # New order
        instance._old_status = None
        instance._old_data = {}

@receiver(post_save, sender=Order)
def order_saved(sender, instance, created, **kwargs):
    """Handle order save events"""
    try:
        if created:
            # New order created
            logger.info(f"New order created: {instance.order_code}")
            notification_service.send_notification(
                'order_created',
                instance,
                created_by=instance.created_by.username if instance.created_by else None
            )
        else:
            # Existing order updated
            logger.info(f"Order updated: {instance.order_code}")
            
            # Check if status changed
            old_status = getattr(instance, '_old_status', None)
            if old_status != instance.status:
                logger.info(f"Order {instance.order_code} status changed from {old_status} to {instance.status}")
                notification_service.send_notification(
                    'order_status_changed',
                    instance,
                    old_status={
                        'id': old_status.id if old_status else None,
                        'name': old_status.name if old_status else None,
                        'code': old_status.code if old_status else None,
                    } if old_status else None,
                    new_status={
                        'id': instance.status.id if instance.status else None,
                        'name': instance.status.name if instance.status else None,
                        'code': instance.status.code if instance.status else None,
                    } if instance.status else None,
                    changed_by=getattr(instance, '_changed_by', None)
                )
            
            # Check for other significant changes
            old_data = getattr(instance, '_old_data', {})
            current_data = {
                'recipient_name': instance.recipient_name,
                'recipient_phone': instance.recipient_phone,
                'sender_name': instance.sender_name,
                'total_amount': str(instance.total_amount) if instance.total_amount else None,
            }
            
            changes = {}
            for key, old_value in old_data.items():
                new_value = current_data.get(key)
                if old_value != new_value:
                    changes[key] = {
                        'old': old_value,
                        'new': new_value
                    }
            
            if changes:
                logger.info(f"Order {instance.order_code} data changed: {changes}")
                notification_service.send_notification(
                    'order_updated',
                    instance,
                    changes=changes,
                    updated_by=getattr(instance, '_updated_by', None)
                )
        
        # Clean up temporary attributes
        if hasattr(instance, '_old_status'):
            delattr(instance, '_old_status')
        if hasattr(instance, '_old_data'):
            delattr(instance, '_old_data')
            
    except Exception as e:
        logger.error(f"Error in order_saved signal: {e}")

# Helper function to track who made changes (can be called from views)
def set_order_change_user(order, user):
    """Set the user who made changes to the order"""
    if user and hasattr(user, 'username'):
        order._changed_by = user.username
        order._updated_by = user.username
    return order
