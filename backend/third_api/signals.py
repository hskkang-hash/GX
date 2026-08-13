import logging
import json
import os
import requests
from datetime import datetime
from typing import Dict, Any

from django.db.models.signals import post_save, pre_save
from django.db import transaction
from django.dispatch import receiver

from django.conf import settings
from delivery.models import (
    DeliveryOperation,

)

from delivery.tasks import send_anyang_status_callback_task, send_anyang_terminal_callback_task, send_anyang_notification_callback_task
from .common.utils import get_anyang_target_url

logger = logging.getLogger(__name__)

def validate_service_key(service_key: str) -> tuple[bool, str]:
    """
    Validate serviceKey against environment variable
    Returns: (is_valid, error_message)
    """
    print(f"🔐 [AUTH] Validating service key...")
    print(f"   🔑 Provided key: {service_key[:10] + '...' if service_key and len(service_key) > 10 else service_key}")
    
    expected_service_key = os.getenv('ANYANG_SERVICE_KEY')
    
    if not service_key:
        print(f"   ❌ Service key is missing")
        return False, 'serviceKey is required'
    
    if not expected_service_key:
        print(f"   ❌ Expected service key not configured in environment")
        return False, 'Service configuration error'
        
    if service_key != expected_service_key:
        print(f"   ❌ Service key mismatch")
        print(f"      📝 Expected: {expected_service_key[:10] + '...' if len(expected_service_key) > 10 else expected_service_key}")
        return False, 'Invalid serviceKey'
    
    print(f"   ✅ Service key validation successful")
    return True, ''
@receiver(post_save, sender=DeliveryOperation)
def send_anyang_status_callback(sender, instance, created, **kwargs):
    """
    Send status change callback to Anyang delivery app when DeliveryOperation status changes
    """

    try:
        # Skip callback for newly created operations (no status change yet)
        if created:
            logger.debug(
                f"Skipping Anyang callback for newly created operation {instance.id}"
            )
            return
        if not instance.another_info.get("anyang", {}):
            return
        # Get old and new status codes
        old_status_code = getattr(instance, "_old_status_code", None)
        new_status_code = (
            instance.current_status.code if instance.current_status else None
        )

        # Skip if status hasn't changed (but allow bulk updates where old_status_code is None)
        if old_status_code is not None and old_status_code == new_status_code:
            logger.debug(
                f"Status unchanged for operation {instance.id}, skipping Anyang callback"
            )
            return

        # Skip if no new status
        if not new_status_code:
            logger.debug(
                f"No new status for operation {instance.id}, skipping Anyang callback"
            )
            return

        print(
            f"📞 [ANYANG CALLBACK] Delivery operation {instance.id} status changed: {old_status_code} → {new_status_code}"
        )

        # Schedule callback task to run after current transaction commits
        # This ensures the database changes are saved before sending the callback
        transaction.on_commit(
            lambda: send_anyang_status_callback_task.delay(instance.id, old_status_code)
        )

    except Exception as e:
        print(f"❌ [ANYANG CALLBACK] Unexpected error in signal handler: {str(e)}")
        # Don't re-raise the exception to avoid breaking the main operation



def send_anyang_callback(endpoint: str, data: Dict[str, Any]) -> bool:
    """
    Send callback to Anyang endpoint using existing AnyangCallbackService
    
    Args:
        endpoint: Endpoint path (e.g., '/Callback')
        data: Data to send
        
    Returns:
        bool: True if successful
    """
    try:
        # Validate service key first
        service_key = getattr(settings, 'ANYANG_SERVICE_KEY', None)
        if not service_key:
            logger.error("❌ [ANYANG CALLBACK] ANYANG_SERVICE_KEY not configured")
            return False
        
        # Validate service key using existing function
        is_valid, error_message = validate_service_key(service_key)
        if not is_valid:
            logger.error(f"❌ [ANYANG CALLBACK] Service key validation failed: {error_message}")
            return False
        
        target_url = get_anyang_target_url()
        full_url = f"{target_url}{endpoint}"
            
        data['serviceKey'] = service_key
        
        logger.info(f"📞 [ANYANG CALLBACK] Sending to {full_url}")
        logger.debug(f"📞 [ANYANG CALLBACK] Data: {json.dumps(data, indent=2)}")
        
        response = requests.post(
            full_url,
            json=data,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            logger.info(f"✅ [ANYANG CALLBACK] Successfully sent to {endpoint}")
            return True
        else:
            logger.error(f"❌ [ANYANG CALLBACK] Failed to send to {endpoint}: HTTP {response.status_code}")
            logger.error(f"❌ [ANYANG CALLBACK] Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ [ANYANG CALLBACK] Error sending to {endpoint}: {str(e)}")
        return False


@receiver(post_save, sender='terminals.Terminal')  
def trigger_terminal_anyang_callback(sender, instance, created, **kwargs):
    """
    Signal cho Terminal → Anyang DroneBaseStation URLs
    Gửi callback cố định vào endpoint Anyang khi Terminal thay đổi
    """
    try:
        logger.info(f"🔄 [ANYANG SIGNAL] Terminal {instance.id} {'created' if created else 'updated'}, triggering drone base status event")
        
        # Format data theo chuẩn DroneBaseStation cho Anyang
        event_data = {
            'startDeliveryPoint': getattr(instance, 'code', ''),
            'status': "1" if instance.active else "0",
            'message': "0",
            'updateTime': datetime.now().isoformat()
        }
        
        # Thêm thông tin bổ sung từ previous data nếu có
        if hasattr(instance, '_previous_data') and instance._previous_data:
            previous_status = "Active" if instance._previous_data.get('active', '') else "Inactive"
            current_status = "Active" if instance.active else "Inactive"
            if previous_status and previous_status != current_status:
                event_data['message'] = f'Terminal {instance.name or instance.id} status changed from {previous_status} to {current_status}'
        
        def trigger_event():
            try:
                # Schedule callback task to run after current transaction commits
                transaction.on_commit(
                    lambda: send_anyang_terminal_callback_task.delay(instance.id, event_data)
                )
            except Exception as e:
                logger.error(f"❌ [ANYANG SIGNAL] Error scheduling terminal callback task: {str(e)}")
        
        # Trigger sau khi transaction commit
        transaction.on_commit(trigger_event)
        
    except Exception as e:
        logger.error(f"❌ [ANYANG SIGNAL] Error in terminal signal: {str(e)}")


# =====================================
# ANYANG NOTIFICATION SIGNAL  
# =====================================

@receiver(post_save, sender='operational_data.OperationalNotice')
def trigger_notification_anyang_callback(sender, instance, created, **kwargs):
    """
    Signal cho OperationalNotice → Anyang DroneUserNotice URLs
    Gửi callback cố định vào endpoint Anyang khi OperationalNotice thay đổi
    """
    try:
        # if instance.active:
            logger.info(f"🔄 [ANYANG SIGNAL] OperationalNotice {instance.id} {'created' if created else 'updated'}, triggering user notice event")
            
            # Format data theo chuẩn DroneUserNotice cho Anyang
            event_data = {
                'BCode': getattr(instance, 'area_code', '') or getattr(instance, 'location_code', '') or '4117',
                'IsNotice': "1" if getattr(instance, 'is_active', True) else "0",
                'Html1': getattr(instance, 'content1', ''),
                'Html2': getattr(instance, 'content2', ''),
                'Html3': getattr(instance, 'content3', ''),
            }
            
            def trigger_event():
                try:
                    # Schedule callback task to run after current transaction commits
                    transaction.on_commit(
                        lambda: send_anyang_notification_callback_task.delay(instance.id, event_data)
                    )
                except Exception as e:
                    logger.error(f"❌ [ANYANG SIGNAL] Error scheduling notification callback task: {str(e)}")
            
            # Trigger sau khi transaction commit
            transaction.on_commit(trigger_event)
        
    except Exception as e:
        logger.error(f"❌ [ANYANG SIGNAL] Error in operational notice signal: {str(e)}")
