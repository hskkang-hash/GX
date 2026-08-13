"""
Partner Celery Tasks
Tasks để gửi callback events đến các partner đã đăng ký
"""

import json
import logging
import requests
from typing import Dict, Any, List
from celery import shared_task
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_delivery_status_callback_to_partner(self, event_data: Dict[str, Any], partner_id: int):
    """
    Task gửi delivery status callback đến 1 partner cụ thể (partner tạo ra order)
    
    Args:
        event_data: {
            'itemOrgId': str,
            'deliveryStatus': str, 
            'message': str,
            'updateTime': str,
            'deliveryPhoto': dict (optional)
        }
        partner_id: ID của partner cần gửi callback
    """
    try:
        from partner.models import Partner
        from partner.services.partner_callback_service import PartnerCallbackService
        
        logger.info(f"🚀 [PARTNER TASK] Starting delivery status callback task for item: {event_data.get('itemOrgId')} to partner_id: {partner_id}")
        
        # Lấy partner cụ thể
        try:
            partner = Partner.objects.get(id=partner_id, is_active=True, deleted__isnull=True)
        except Partner.DoesNotExist:
            logger.warning(f"⚠️ [PARTNER TASK] Partner {partner_id} not found or inactive")
            return {"status": "partner_not_found", "partner_id": partner_id}
        
        # Kiểm tra xem partner có callback URL cho DeliveryStatusCallback không
        callback_url = partner.api_callback_url.get("DeliveryStatusCallback", "") if partner.api_callback_url else ""
        if not callback_url or not callback_url.strip():
            logger.info(f"📭 [PARTNER TASK] Partner {partner.name} has no DeliveryStatusCallback URL configured")
            return {"status": "no_callback_url", "partner_id": partner_id, "partner_name": partner.name}
        
        # Gửi callback đến partner
        result = PartnerCallbackService.send_delivery_status_callback(partner, event_data)
        
        if result["success"]:
            logger.info(f"✅ [PARTNER TASK] Successfully sent callback to partner {partner.name}")
        else:
            logger.warning(f"⚠️ [PARTNER TASK] Failed to send callback to partner {partner.name}: {result.get('message', '')}")
        
        return {
            "status": "completed",
            "partner_id": partner.id,
            "partner_name": partner.name,
            "success": result["success"],
            "message": result.get("message", "")
        }
        
    except Exception as e:
        logger.error(f"❌ [PARTNER TASK] Error in delivery status callback task: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_delivery_status_callback_to_partners(self, event_data: Dict[str, Any], group_id: int = None):
    """
    Task gửi delivery status callback đến tất cả partner đã đăng ký sự kiện này
    
    Args:
        event_data: {
            'itemOrgId': str,
            'deliveryStatus': str, 
            'message': str,
            'updateTime': str,
            'deliveryPhoto': dict (optional)
        }
    """
    try:
        from partner.services.partner_callback_service import PartnerCallbackService
        
        logger.info(f"🚀 [PARTNER TASK] Starting delivery status callback task for item: {event_data.get('itemOrgId')}")
        
        # Tìm tất cả partner có callback URL cho DeliveryStatusCallback
        partners = PartnerCallbackService.get_partners_with_callback("DeliveryStatusCallback", group_id)
        
        if not partners:
            logger.info("📭 [PARTNER TASK] No partners registered for DeliveryStatusCallback")
            return {"status": "no_partners", "partner_count": 0}
        
        logger.info(f"📤 [PARTNER TASK] Found {len(partners)} partners for DeliveryStatusCallback")
        
        results = []
        for partner in partners:
            try:
                result = PartnerCallbackService.send_delivery_status_callback(partner, event_data)
                results.append({
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "success": result["success"],
                    "message": result.get("message", "")
                })
                logger.info(f"✅ [PARTNER TASK] Sent callback to partner {partner.name}: {result['success']}")
                
            except Exception as e:
                logger.error(f"❌ [PARTNER TASK] Failed to send callback to partner {partner.name}: {str(e)}")
                results.append({
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "success": False,
                    "message": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"📊 [PARTNER TASK] Delivery status callback completed: {success_count}/{len(results)} successful")
        
        return {
            "status": "completed",
            "partner_count": len(partners),
            "success_count": success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ [PARTNER TASK] Error in delivery status callback task: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_drone_base_status_callback_to_partners(self, event_data: Dict[str, Any], group_id: int = None):
    """
    Task gửi drone base status callback đến tất cả partner đã đăng ký sự kiện này
    
    Args:
        event_data: {
            'startDeliveryPoint': str,
            'status': str,
            'message': str,
            'updateTime': str
        }
    """
    try:
        from partner.services.partner_callback_service import PartnerCallbackService
        
        logger.info(f"🚀 [PARTNER TASK] Starting drone base status callback task for point: {event_data.get('startDeliveryPoint')}")
        
        # Tìm tất cả partner có callback URL cho DroneBaseStation
        partners = PartnerCallbackService.get_partners_with_callback("DroneBaseStation", group_id)
        
        if not partners:
            logger.info("📭 [PARTNER TASK] No partners registered for DroneBaseStation")
            return {"status": "no_partners", "partner_count": 0}
        
        logger.info(f"📤 [PARTNER TASK] Found {len(partners)} partners for DroneBaseStation")
        
        results = []
        for partner in partners:
            try:
                result = PartnerCallbackService.send_drone_base_status_callback(partner, event_data)
                results.append({
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "success": result["success"],
                    "message": result.get("message", ""),
                    "response_data": result.get("response_data", "")
                })
                logger.info(f"✅ [PARTNER TASK] Sent callback to partner {partner.name}: {result['success']}")
                
            except Exception as e:
                logger.error(f"❌ [PARTNER TASK] Failed to send callback to partner {partner.name}: {str(e)}")
                results.append({
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "success": False,
                    "message": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"📊 [PARTNER TASK] Drone base status callback completed: {success_count}/{len(results)} successful")
        
        return {
            "status": "completed",
            "partner_count": len(partners),
            "success_count": success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ [PARTNER TASK] Error in drone base status callback task: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_user_notice_callback_to_partners(self, event_data: Dict[str, Any], group_id: int = None):
    """
    Task gửi user notice callback đến tất cả partner đã đăng ký sự kiện này
    
    Args:
        event_data: {
            'BCode': str,
            'IsNotice': int,
            'Html1': str,
            'Html2': str,
            'Html3': str (optional)
        }
    """
    try:
        from partner.services.partner_callback_service import PartnerCallbackService
        
        logger.info(f"🚀 [PARTNER TASK] Starting user notice callback task for BCode: {event_data.get('BCode')}")
        
        # Tìm tất cả partner có callback URL cho DroneUserNotice
        partners = PartnerCallbackService.get_partners_with_callback("DroneUserNotice", group_id)
        
        if not partners:
            logger.info("📭 [PARTNER TASK] No partners registered for DroneUserNotice")
            return {"status": "no_partners", "partner_count": 0}
        
        logger.info(f"📤 [PARTNER TASK] Found {len(partners)} partners for DroneUserNotice")
        
        results = []
        for partner in partners:
            try:
                result = PartnerCallbackService.send_user_notice_callback(partner, event_data)
                results.append({
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "success": result["success"],
                    "message": result.get("message", ""),
                    "response_data": result.get("response_data", "")
                })
                logger.info(f"✅ [PARTNER TASK] Sent callback to partner {partner.name}: {result['success']}")
                
            except Exception as e:
                logger.error(f"❌ [PARTNER TASK] Failed to send callback to partner {partner.name}: {str(e)}")
                results.append({
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "success": False,
                    "message": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"📊 [PARTNER TASK] User notice callback completed: {success_count}/{len(results)} successful")
        
        return {
            "status": "completed",
            "partner_count": len(partners),
            "success_count": success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ [PARTNER TASK] Error in user notice callback task: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_callback_to_all_partners(self, callback_type: str, event_data: Dict[str, Any], group_id: int = None):
    """
    Universal task để gửi bất kỳ loại callback nào đến tất cả partner đã đăng ký
    
    Args:
        callback_type: "DeliveryStatusCallback", "DroneBaseStation", hoặc "DroneUserNotice"
        event_data: Data của event cần gửi
    """
    try:
        from partner.services.partner_callback_service import PartnerCallbackService
        
        logger.info(f"🚀 [PARTNER TASK] Starting universal callback task: {callback_type}")
        
        # Tìm tất cả partner có callback URL cho loại callback này
        partners = PartnerCallbackService.get_partners_with_callback(callback_type, group_id)
        
        if not partners:
            logger.info(f"📭 [PARTNER TASK] No partners registered for {callback_type}")
            return {"status": "no_partners", "partner_count": 0}
        
        logger.info(f"📤 [PARTNER TASK] Found {len(partners)} partners for {callback_type}")
        
        results = []
        for partner in partners:
            try:
                result = PartnerCallbackService.send_universal_callback(partner, callback_type, event_data)
                results.append({
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "success": result["success"],
                    "message": result.get("message", ""),
                    "response_data": result.get("response_data", "")
                })
                logger.info(f"✅ [PARTNER TASK] Sent callback to partner {partner.name}: {result['success']}")
                
            except Exception as e:
                logger.error(f"❌ [PARTNER TASK] Failed to send callback to partner {partner.name}: {str(e)}")
                results.append({
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "success": False,
                    "message": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"📊 [PARTNER TASK] {callback_type} callback completed: {success_count}/{len(results)} successful")
        
        return {
            "status": "completed",
            "callback_type": callback_type,
            "partner_count": len(partners),
            "success_count": success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ [PARTNER TASK] Error in universal callback task: {str(e)}")
        raise self.retry(exc=e)
