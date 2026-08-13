"""
Partner Django Signals
Sử dụng PartnerCallbackService triggers để gửi formatted data đến partner URLs
"""

import json
import logging
import requests
from typing import Dict, Any, List
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from datetime import datetime

from partner.models import Partner

logger = logging.getLogger(__name__)




def get_item_org_id(instance) -> str:
    """
    Lấy itemOrgId từ 3 nguồn theo thứ tự ưu tiên:
    1. another_info["anyang"]["itemOrgId"]
    2. another_info["etri"]["receipt_id"] 
    3. str(instance.id)
    
    Args:
        instance: DeliveryOperation instance
        
    Returns:
        str: itemOrgId hoặc fallback value
    """
    try:
        # Kiểm tra another_info field
        another_info = getattr(instance, 'another_info', {}) or {}
        
        # 1. Thử lấy từ anyang.itemOrgId
        if isinstance(another_info, dict):
            anyang_data = another_info.get('anyang', {})
            if isinstance(anyang_data, dict):
                item_org_id = anyang_data.get('itemOrgId', '')
                if item_org_id and item_org_id.strip():
                    return str(item_org_id)
            
            # 2. Thử lấy từ etri.receipt_id
            etri_data = another_info.get('etri', {})
            if isinstance(etri_data, dict):
                receipt_id = etri_data.get('receipt_id', '')
                if receipt_id and receipt_id.strip():
                    return str(receipt_id)
        
        # 3. Fallback về instance.id
        return str(instance.id)
        
    except Exception as e:
        logger.warning(f"⚠️ [PARTNER SIGNAL] Error getting itemOrgId: {str(e)}, using instance.id")
        return str(instance.id)


def get_delivery_status_mapped(instance) -> str:
    """
    Lấy deliveryStatus theo external status mapping
    Sử dụng StatusMappingService để lấy external status value
    
    Args:
        instance: DeliveryOperation instance
        
    Returns:
        str: External status value hoặc fallback value
    """
    try:
        from delivery.services.status_mapping_service import StatusMappingService
        
        # Sử dụng mapping service để lấy external status value
        external_status = StatusMappingService.get_external_status_mapping_with_fallback(instance)
        
        if external_status:
            return external_status
            
        # Fallback về status_code nếu không có mapping
        return getattr(instance, 'status_code', '') or 'unknown'
        
    except Exception as e:
        logger.warning(f"⚠️ [PARTNER SIGNAL] Error getting mapped delivery status: {str(e)}, using fallback")
        return getattr(instance, 'status_code', '') or 'unknown'


def extract_model_data(instance, exclude_foreign_keys: bool = True) -> Dict[str, Any]:
    """
    Extract data từ model instance, loại bỏ foreign keys
    
    Args:
        instance: Model instance
        exclude_foreign_keys: Có loại bỏ foreign keys không
        
    Returns:
        Dict: Model data
    """
    data = {}
    
    for field in instance._meta.fields:
        field_name = field.name
        field_value = getattr(instance, field_name, None)
        
        # Skip foreign keys nếu exclude_foreign_keys=True
        if exclude_foreign_keys and field.is_relation:
            continue
            
        # Convert datetime to string
        if hasattr(field_value, 'isoformat'):
            field_value = field_value.isoformat()
        
        elif field_value is not None and not isinstance(field_value, (str, int, float, bool, list, dict)):
            field_value = str(field_value)
            
        data[field_name] = field_value
    
    return data




@receiver(pre_save, sender='delivery.DeliveryOperation')
def store_previous_delivery_operation_data(sender, instance, **kwargs):
    """Lưu data cũ để so sánh trong post_save"""
    try:
        if instance.pk:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._previous_data = extract_model_data(old_instance)
        else:
            instance._previous_data = None
    except sender.DoesNotExist:
        instance._previous_data = None


@receiver(post_save, sender='delivery.DeliveryOperation')
def trigger_delivery_operation_partner_callback(sender, instance, created, **kwargs):
    """
    Signal cho DeliveryOperation → DeliveryStatusCallback URLs
    Chỉ gửi đến partner tạo ra order (qua order.created_by.partner_profile)
    """
    try:
        # Skip nếu vừa tạo mới
        if created:
            return
            
        logger.info(f"🔄 [PARTNER SIGNAL] DeliveryOperation {instance.id} changed, triggering delivery status event")
        
        # Lấy partner_id từ order.created_by
        partner_id = None
        try:
            if instance.order and instance.order.created_by:
                # Kiểm tra xem created_by có partner_profile không
                if hasattr(instance.order.created_by, 'partner_profile'):
                    partner_id = instance.order.created_by.partner_profile.id
                    logger.info(f"✅ [PARTNER SIGNAL] Found partner_id: {partner_id} for order created_by")
        except Exception as e:
            logger.warning(f"⚠️ [PARTNER SIGNAL] Could not get partner from order.created_by: {str(e)}")
        
        # Nếu không có partner_id, skip
        if not partner_id:
            logger.info(f"⏭️ [PARTNER SIGNAL] No partner found for DeliveryOperation {instance.id}, skipping callback")
            return
        
        # Format data theo chuẩn DeliveryStatusCallback
        event_data = {
            'itemOrgId': get_item_org_id(instance),
            'deliveryStatus': get_delivery_status_mapped(instance),
            'message': 0,
            'updateTime': datetime.now().isoformat(),
            'deliveryPhoto': {}
        }
        
        # Thêm thông tin bổ sung nếu có
        if hasattr(instance, 'photo_url') and instance.photo_url:
            event_data['deliveryPhoto'] = {'url': instance.photo_url}
        
        def trigger_event():
            try:
                from partner.services.partner_callback_service import PartnerCallbackService
                PartnerCallbackService.trigger_delivery_status_event(event_data, partner_id)
            except Exception as e:
                logger.error(f"❌ [PARTNER SIGNAL] Error triggering delivery status event: {str(e)}")
        
        # Trigger sau khi transaction commit
        transaction.on_commit(trigger_event)
        
    except Exception as e:
        logger.error(f"❌ [PARTNER SIGNAL] Error in delivery operation signal: {str(e)}")


# =====================================
# TERMINAL SIGNAL  
# =====================================

@receiver(pre_save, sender='terminals.Terminal')
def store_previous_terminal_data(sender, instance, **kwargs):
    """Lưu data cũ để so sánh trong post_save"""
    try:
        if instance.pk:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._previous_data = extract_model_data(old_instance)
        else:
            instance._previous_data = None
    except sender.DoesNotExist:
        instance._previous_data = None


@receiver(post_save, sender='terminals.Terminal')  
def trigger_terminal_partner_callback(sender, instance, created, **kwargs):
    """
    Signal cho Terminal → DroneBaseStation URLs
    Sử dụng PartnerCallbackService.trigger_drone_base_status_event với format chuẩn
    """
    try:
        logger.info(f"🔄 [PARTNER SIGNAL] Terminal {instance.id} {'created' if created else 'updated'}, triggering drone base status event")
        
        # Format data theo chuẩn DroneBaseStation
        event_data = {
            'startDeliveryPoint': getattr(instance, 'code', '') or getattr(instance, 'name', '') or f'Terminal-{instance.id}',
            'status':  1 if instance.active else 0,
            'message': "",
            'updateTime': datetime.now().isoformat()
        }
        if instance.terminal_types.filter(code='TEMP').exists():
            return
        # Thêm thông tin bổ sung từ previous data nếu có
        if hasattr(instance, '_previous_data') and instance._previous_data:
            previous_status = "Active" if instance._previous_data.get('active', '') else "Inactive"
            current_status = "Active" if instance.active else "Inactive"
            if previous_status and previous_status != current_status:
                event_data['message'] = f'Terminal {instance.name or instance.id} status changed from {previous_status} to {current_status}'
        
        def trigger_event():
            try:
                from partner.services.partner_callback_service import PartnerCallbackService
                PartnerCallbackService.trigger_drone_base_status_event(event_data, instance.created_by.userprofilelink.group.id if instance.created_by.userprofilelink.group else None)
            except Exception as e:
                logger.error(f"❌ [PARTNER SIGNAL] Error triggering drone base status event: {str(e)}")
        
        # Trigger sau khi transaction commit
        transaction.on_commit(trigger_event)
        
    except Exception as e:
        logger.error(f"❌ [PARTNER SIGNAL] Error in terminal signal: {str(e)}")




@receiver(post_save, sender='operational_data.OperationalNotice')
def trigger_notification_partner_callback(sender, instance, created, **kwargs):
    """
    Signal cho OperationalNotice → DroneUserNotice URLs
    Sử dụng PartnerCallbackService.trigger_user_notice_event với format chuẩn
    """
    try:
        # if instance.active:
        logger.info(f"🔄 [PARTNER SIGNAL] OperationalNotice {instance.id} {'created' if created else 'updated'}, triggering user notice event")
        
        # Format data theo chuẩn DroneUserNotice
        event_data = {
            'BCode': getattr(instance, 'area_code', '') or getattr(instance, 'location_code', '') or '4117',
            'IsNotice': 1 if getattr(instance, 'is_active', True) else 0,
            'Html1': getattr(instance, 'content1', ''),
            'Html2': getattr(instance, 'content2', ''),
            'Html3': getattr(instance, 'content3', ''),
        }
        
        # # Thêm thông tin về việc tạo mới hay cập nhật
        # if created:
        #     event_data['Html3'] = f'New notice created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        # else:
        #     event_data['Html3'] = f'Notice updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        
        def trigger_event():
            try:
                from partner.services.partner_callback_service import PartnerCallbackService
                PartnerCallbackService.trigger_user_notice_event(event_data, instance.created_by.userprofilelink.group.id if instance.created_by.userprofilelink.group else None)
            except Exception as e:
                logger.error(f"❌ [PARTNER SIGNAL] Error triggering user notice event: {str(e)}")
        
        # Trigger sau khi transaction commit
        transaction.on_commit(trigger_event)
        
    except Exception as e:
        logger.error(f"❌ [PARTNER SIGNAL] Error in operational notice signal: {str(e)}")
