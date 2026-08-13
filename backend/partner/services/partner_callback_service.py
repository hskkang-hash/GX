"""
Partner Callback Service
Service để xử lý việc gửi callback đến partner systems
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.db.models import QuerySet

from partner.models import Partner

logger = logging.getLogger(__name__)


class PartnerCallbackService:
    """
    Service để xử lý việc gửi callback đến các partner đã đăng ký sự kiện
    """
    
    @staticmethod
    def get_partners_with_callback(callback_type: str, group_id: int = None) -> QuerySet[Partner]:
        """
        Tìm tất cả partner có callback URL cho loại sự kiện cụ thể
        
        Args:
            callback_type: "DeliveryStatusCallback", "DroneBaseStation", hoặc "DroneUserNotice"
            group_id: ID của group
        Returns:
            QuerySet[Partner]: Danh sách partner có callback URL được cấu hình
        """
        try:
            logger.info(f"🔍 [PARTNER SERVICE] Looking for partners with {callback_type} callback")
            
            # Tìm partner active có api_callback_url được cấu hình và có URL cho callback_type
            partners = Partner.objects.filter(
                is_active=True,
                api_callback_url__isnull=False,
                group_id=group_id,
                deleted__isnull=True,
            ).exclude(api_callback_url={})
            
            # Lọc partner có callback URL cho callback_type cụ thể
            filtered_partners = []
            for partner in partners:
                callback_url = partner.api_callback_url.get(callback_type, '')
                if callback_url and callback_url.strip():
                    filtered_partners.append(partner.id)
            
            # Trả về QuerySet của các partner đã lọc
            final_partners = Partner.objects.filter(id__in=filtered_partners)
            
            logger.info(f"✅ [PARTNER SERVICE] Found {final_partners.count()} partners with {callback_type} callback")
            
            return final_partners
            
        except Exception as e:
            logger.error(f"❌ [PARTNER SERVICE] Error finding partners with {callback_type}: {str(e)}")
            return Partner.objects.none()
    
    @staticmethod
    def send_delivery_status_callback(partner: Partner, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gửi delivery status callback đến một partner cụ thể
        
        Args:
            partner: Partner instance
            event_data: Data của delivery status event
            
        Returns:
            Dict với kết quả gửi callback
        """
        try:
            callback_url = partner.api_callback_url.get("DeliveryStatusCallback", "")
            if not callback_url:
                return {"success": False, "message": "No DeliveryStatusCallback URL configured"}
            
            logger.info(f"📤 [PARTNER SERVICE] Sending delivery status callback to {partner.name}")
            
            # Chuẩn bị data cho callback (thêm serviceKey của partner)
            callback_data = {
                'serviceKey': partner.service_key,
                'itemOrgId': event_data.get('itemOrgId'),
                'deliveryStatus': event_data.get('deliveryStatus'),
                'message': event_data.get('message'),
                'updateTime': event_data.get('updateTime')
            }
            
            # Thêm deliveryPhoto nếu có
            if event_data.get('deliveryPhoto'):
                callback_data['deliveryPhoto'] = event_data['deliveryPhoto']
            else:
                callback_data['deliveryPhoto'] = {}
            
            # Gửi callback đến partner
            response = requests.post(
                callback_url,
                json=callback_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ [PARTNER SERVICE] Successfully sent delivery status callback to {partner.name}")
                return {
                    "success": True,
                    "message": "Callback sent successfully",
                    "response_data": response.text
                }
            else:
                logger.warning(f"⚠️ [PARTNER SERVICE] Failed to send callback to {partner.name}: HTTP {response.status_code}")
                return {
                    "success": False,
                    "message": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [PARTNER SERVICE] Network error sending callback to {partner.name}: {str(e)}")
            return {"success": False, "message": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ [PARTNER SERVICE] Error sending callback to {partner.name}: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    @staticmethod
    def send_drone_base_status_callback(partner: Partner, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gửi drone base status callback đến một partner cụ thể
        """
        try:
            callback_url = partner.api_callback_url.get("DroneBaseStation", "")
            if not callback_url:
                return {"success": False, "message": "No DroneBaseStation URL configured"}
            
            logger.info(f"📤 [PARTNER SERVICE] Sending drone base status callback to {partner.name}")
            
            # Chuẩn bị data cho callback
            callback_data = {
                'serviceKey': partner.service_key,
                'startDeliveryPoint': event_data.get('startDeliveryPoint'),
                'status': event_data.get('status'),
                'message': event_data.get('message'),
                'updateTime': event_data.get('updateTime')
            }
            # Gửi callback đến partner
            response = requests.post(
                callback_url,
                json=callback_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            if response.status_code == 200:
                logger.info(f"✅ [PARTNER SERVICE] Successfully sent drone base status callback to {partner.name}")
                return {
                    "success": True,
                    "message": "Callback sent successfully",
                    "response_data": response.text
                }
            else:
                logger.warning(f"⚠️ [PARTNER SERVICE] Failed to send callback to {partner.name}: HTTP {response.status_code}")
                return {
                    "success": False,
                    "message": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [PARTNER SERVICE] Network error sending callback to {partner.name}: {str(e)}")
            return {"success": False, "message": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ [PARTNER SERVICE] Error sending callback to {partner.name}: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    @staticmethod
    def send_user_notice_callback(partner: Partner, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gửi user notice callback đến một partner cụ thể
        """
        try:
            callback_url = partner.api_callback_url.get("DroneUserNotice", "")
            if not callback_url:
                return {"success": False, "message": "No DroneUserNotice URL configured"}
            
            logger.info(f"📤 [PARTNER SERVICE] Sending user notice callback to {partner.name}")
            
            # Chuẩn bị data cho callback
            callback_data = {
                'serviceKey': partner.service_key,
                'BCode': event_data.get('BCode'),
                'IsNotice': event_data.get('IsNotice'),
                'Html1': event_data.get('Html1', ''),
                'Html2': event_data.get('Html2', ''),
                'Html3': event_data.get('Html3', '')
            }
            
            # Gửi callback đến partner
            response = requests.post(
                callback_url,
                json=callback_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ [PARTNER SERVICE] Successfully sent user notice callback to {partner.name}")
                
                return {
                    "success": True,
                    "message": "Callback sent successfully",
                    "response_data": response.text
                }
            else:
                logger.warning(f"⚠️ [PARTNER SERVICE] Failed to send callback to {partner.name}: HTTP {response.status_code}")
                return {
                    "success": False,
                    "message": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [PARTNER SERVICE] Network error sending callback to {partner.name}: {str(e)}")
            return {"success": False, "message": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ [PARTNER SERVICE] Error sending callback to {partner.name}: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    @staticmethod
    def send_universal_callback(partner: Partner, callback_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Universal method để gửi bất kỳ loại callback nào đến partner
        
        Args:
            partner: Partner instance
            callback_type: Loại callback
            event_data: Data của event
            
        Returns:
            Dict với kết quả gửi callback
        """
        if callback_type == "DeliveryStatusCallback":
            return PartnerCallbackService.send_delivery_status_callback(partner, event_data)
        elif callback_type == "DroneBaseStation":
            return PartnerCallbackService.send_drone_base_status_callback(partner, event_data)
        elif callback_type == "DroneUserNotice":
            return PartnerCallbackService.send_user_notice_callback(partner, event_data)
        else:
            return {"success": False, "message": f"Unknown callback type: {callback_type}"}
    
    @staticmethod
    def trigger_delivery_status_event(event_data: Dict[str, Any], partner_id: int = None) -> None:
        """
        Trigger delivery status event - chỉ gửi đến partner cụ thể tạo ra order
        
        Args:
            event_data: Data của delivery status event
            partner_id: ID của partner cần gửi callback (bắt buộc)
        """
        try:
            from partner.tasks import send_delivery_status_callback_to_partner
            
            logger.info(f"🚀 [PARTNER SERVICE] Triggering delivery status event for item: {event_data.get('itemOrgId')} to partner: {partner_id}")
            
            if not partner_id:
                logger.warning(f"⚠️ [PARTNER SERVICE] No partner_id provided for delivery status event")
                return
            
            # Gửi task bất đồng bộ đến partner cụ thể
            task = send_delivery_status_callback_to_partner.delay(event_data, partner_id)
            
            logger.info(f"✅ [PARTNER SERVICE] Delivery status task queued with ID: {task.id}")
            
        except Exception as e:
            logger.error(f"❌ [PARTNER SERVICE] Error triggering delivery status event: {str(e)}")
    
    @staticmethod
    def trigger_drone_base_status_event(event_data: Dict[str, Any], group_id: int = None) -> None:
        """
        Trigger drone base status event - gửi đến tất cả partner đăng ký
        """
        try:
            from partner.tasks import send_drone_base_status_callback_to_partners
            
            logger.info(f"🚀 [PARTNER SERVICE] Triggering drone base status event for point: {event_data.get('startDeliveryPoint')}")
            
            # Gửi task bất đồng bộ
            task = send_drone_base_status_callback_to_partners.delay(event_data, group_id)
            
            logger.info(f"✅ [PARTNER SERVICE] Drone base status task queued with ID: {task.id}")
            
        except Exception as e:
            logger.error(f"❌ [PARTNER SERVICE] Error triggering drone base status event: {str(e)}")
    
    @staticmethod
    def trigger_user_notice_event(event_data: Dict[str, Any], group_id: int = None) -> None:
        """
        Trigger user notice event - gửi đến tất cả partner đăng ký
        """
        try:
            from partner.tasks import send_user_notice_callback_to_partners
            
            logger.info(f"🚀 [PARTNER SERVICE] Triggering user notice event for BCode: {event_data.get('BCode')}")
            
            # Gửi task bất đồng bộ
            task = send_user_notice_callback_to_partners.delay(event_data, group_id)
            
            logger.info(f"✅ [PARTNER SERVICE] User notice task queued with ID: {task.id}")
            
        except Exception as e:
            logger.error(f"❌ [PARTNER SERVICE] Error triggering user notice event: {str(e)}")
    
    @staticmethod
    def trigger_universal_event(callback_type: str, event_data: Dict[str, Any], group_id: int = None) -> None:
        """
        Universal method để trigger bất kỳ loại event nào
        """
        try:
            from partner.tasks import send_callback_to_all_partners
            
            logger.info(f"🚀 [PARTNER SERVICE] Triggering universal event: {callback_type}")
            
            # Gửi task bất đồng bộ
            task = send_callback_to_all_partners.delay(callback_type, event_data, group_id)
            
            logger.info(f"✅ [PARTNER SERVICE] Universal task queued with ID: {task.id}")
            
        except Exception as e:
            logger.error(f"❌ [PARTNER SERVICE] Error triggering universal event: {str(e)}")
