"""
API mockup controller để nhận partner callbacks và gửi socket notifications
Dùng để test các signals partner callbacks
"""
import logging
from typing import Dict, Any
from datetime import datetime
from ninja_extra import api_controller, route
from ninja.errors import ValidationError
from django.http import HttpRequest
from core.middleware.refresh_token import get_current_request
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from common.constant import MESSAGE_ENUM, get_message
from partner.schemas.schemas_djantic_in import (
    DeliveryStatusCallbackInSchema,
    DroneBaseStationCallbackInSchema, 
    DroneUserNoticeCallbackInSchema
)

logger = logging.getLogger(__name__)


@api_controller("/partner-callback-mockup", tags=["Partner Callback Mockup APIs (Development Only)"])
class PartnerCallbackMockupController:
    """Controller for partner callback mockup APIs - for testing partner signals"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def send_websocket_notification(self, callback_type: str, data: Dict[str, Any], 
                                   partner_info: Dict[str, Any] = None, 
                                   success: bool = True, message: str = "", 
                                   target_group_id: str = None):
        """Helper method để gửi WebSocket notification"""
        try:
            # Determine WebSocket event type based on callback type
            if callback_type == "DeliveryStatusCallback":
                event_type = 'delivery_status_callback'
            elif callback_type == "DroneBaseStation":
                event_type = 'drone_base_station_callback'
            elif callback_type == "DroneUserNotice":
                event_type = 'drone_user_notice_callback'
            else:
                event_type = 'partner_callback_error'
            
            # Determine target room - prioritize specific group, fallback to global
            if target_group_id:
                target_room = f'partner_callbacks_{target_group_id}'
            else:
                target_room = 'partner_callbacks_global'
            
            message_data = {
                'type': event_type,
                'timestamp': datetime.now().isoformat(),
                'data': data,
                'partner_info': partner_info or {},
                'success': success,
                'message': message
            }
            
            # Send to target room only
            async_to_sync(self.channel_layer.group_send)(target_room, message_data)
            
            logger.info(f"✅ [PARTNER MOCKUP] Sent WebSocket notification for {callback_type} to room: {target_room}")
            
        except Exception as e:
            logger.error(f"❌ [PARTNER MOCKUP] Error sending WebSocket notification: {str(e)}")
    
    @route.post("/delivery-status-callback")
    def receive_delivery_status_callback(self, request: HttpRequest, data: DeliveryStatusCallbackInSchema):
        """
        API mockup nhận DeliveryStatusCallback từ partner signals
        Mô phỏng partner system nhận callback về delivery status
        """
        try:
            request = get_current_request()
            logger.info(f"📥 [PARTNER MOCKUP] Received DeliveryStatusCallback for itemOrgId: {data.itemOrgId}")
            
            # Validate serviceKey (optional - for realistic testing)
            if not data.serviceKey or data.serviceKey.strip() == "":
                logger.warning(f"⚠️ [PARTNER MOCKUP] Empty serviceKey in delivery status callback")
            
            # Prepare response data
            callback_data = {
                'serviceKey': data.serviceKey,
                'itemOrgId': data.itemOrgId,
                'deliveryStatus': data.deliveryStatus,
                'message': data.message,
                'updateTime': data.updateTime,
                'deliveryPhoto': data.deliveryPhoto or {}
            }
            
            # Partner info for notification
            partner_info = {
                'callback_type': 'DeliveryStatusCallback',
                'serviceKey_prefix': data.serviceKey[:8] + "..." if len(data.serviceKey) > 8 else data.serviceKey,
                'received_at': datetime.now().isoformat()
            }
            
            # Send WebSocket notification - gửi đến group 6 (user anyang11)
            self.send_websocket_notification(
                callback_type="DeliveryStatusCallback",
                data=callback_data,
                partner_info=partner_info,
                success=True,
                message=f"Delivery status callback received for item {data.itemOrgId}",
                target_group_id=request.user.userprofilelink.group.id if request.user.userprofilelink.group else None
            )
            
            # Mock partner processing response
            response_data = {
                "status": "success",
                "message": "Delivery status callback received and processed",
                "data": {
                    "itemOrgId": data.itemOrgId,
                    "deliveryStatus": data.deliveryStatus,
                    "processed_at": datetime.now().isoformat(),
                    "partner_tracking_id": f"MOCKPARTNER_{data.itemOrgId}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "next_action": "Notification sent to customer"
                }
            }
            
            logger.info(f"✅ [PARTNER MOCKUP] Successfully processed delivery status callback for {data.itemOrgId}")
            
            return BaseResponse(
                status_code=200,
                message="Delivery status callback received successfully",
                data=response_data
            )
            
        except Exception as e:
            error_msg = f"Error processing delivery status callback: {str(e)}"
            logger.error(f"❌ [PARTNER MOCKUP] {error_msg}")
            
            # Send error notification
            self.send_websocket_notification(
                callback_type="DeliveryStatusCallback",
                data={'error': str(e), 'input_data': dict(data)},
                success=False,
                message=error_msg,
                target_group_id=request.user.userprofilelink.group.id if request.user.userprofilelink.group else None
            )
            
            return BaseResponse(
                status_code=500,
                message=error_msg,
                data={"error": str(e)}
            )
    
    @route.post("/drone-base-station-callback")
    def receive_drone_base_station_callback(self, request: HttpRequest, data: DroneBaseStationCallbackInSchema):
        """
        API mockup nhận DroneBaseStation callback từ partner signals
        Mô phỏng partner system nhận callback về drone base station status
        """
        try:
            request = get_current_request()
            logger.info(f"📥 [PARTNER MOCKUP] Received DroneBaseStation callback for point: {data.startDeliveryPoint}")
            
            # Validate serviceKey
            if not data.serviceKey or data.serviceKey.strip() == "":
                logger.warning(f"⚠️ [PARTNER MOCKUP] Empty serviceKey in drone base station callback")
            
            # Prepare response data  
            callback_data = {
                'serviceKey': data.serviceKey,
                'startDeliveryPoint': data.startDeliveryPoint,
                'status': data.status,
                'message': data.message,
                'updateTime': data.updateTime
            }
            
            # Partner info for notification
            partner_info = {
                'callback_type': 'DroneBaseStation',
                'serviceKey_prefix': data.serviceKey[:8] + "..." if len(data.serviceKey) > 8 else data.serviceKey,
                'received_at': datetime.now().isoformat()
            }
            
            # Send WebSocket notification
            self.send_websocket_notification(
                callback_type="DroneBaseStation",
                data=callback_data,
                partner_info=partner_info,
                success=True,
                message=f"Drone base station callback received for {data.startDeliveryPoint}",
                target_group_id=request.user.userprofilelink.group.id if request.user.userprofilelink.group else None
            )
            
            # Mock partner processing response
            response_data = {
                "status": "success",
                "message": "Drone base station callback received and processed",
                "data": {
                    "startDeliveryPoint": data.startDeliveryPoint,
                    "status": data.status,
                    "processed_at": datetime.now().isoformat(),
                    "partner_station_id": f"MOCKSTATION_{data.startDeliveryPoint}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "next_action": "Station status updated in partner system"
                }
            }
            
            logger.info(f"✅ [PARTNER MOCKUP] Successfully processed drone base station callback for {data.startDeliveryPoint}")
            
            return BaseResponse(
                status_code=200,
                message="Drone base station callback received successfully",
                data=response_data
            )
            
        except Exception as e:
            error_msg = f"Error processing drone base station callback: {str(e)}"
            logger.error(f"❌ [PARTNER MOCKUP] {error_msg}")
            
            # Send error notification
            self.send_websocket_notification(
                callback_type="DroneBaseStation",
                data={'error': str(e), 'input_data': dict(data)},
                success=False,
                message=error_msg,
                target_group_id="6"
            )
            
            return BaseResponse(
                status_code=500,
                message=error_msg,
                data={"error": str(e)}
            )
    
    @route.post("/drone-user-notice-callback")
    def receive_drone_user_notice_callback(self, request: HttpRequest, data: DroneUserNoticeCallbackInSchema):
        """
        API mockup nhận DroneUserNotice callback từ partner signals
        Mô phỏng partner system nhận callback về user notices
        """
        try:
            request = get_current_request()
            logger.info(f"📥 [PARTNER MOCKUP] Received DroneUserNotice callback for BCode: {data.BCode}")
            
            # Validate serviceKey
            if not data.serviceKey or data.serviceKey.strip() == "":
                logger.warning(f"⚠️ [PARTNER MOCKUP] Empty serviceKey in user notice callback")
            
            # Prepare response data
            callback_data = {
                'serviceKey': data.serviceKey,
                'BCode': data.BCode,
                'IsNotice': data.IsNotice,
                'Html1': data.Html1,
                'Html2': data.Html2 or "",
                'Html3': data.Html3 or ""
            }
            
            # Partner info for notification
            partner_info = {
                'callback_type': 'DroneUserNotice',
                'serviceKey_prefix': data.serviceKey[:8] + "..." if len(data.serviceKey) > 8 else data.serviceKey,
                'received_at': datetime.now().isoformat()
            }
            
            # Send WebSocket notification
            self.send_websocket_notification(
                callback_type="DroneUserNotice",
                data=callback_data,
                partner_info=partner_info,
                success=True,
                message=f"User notice callback received for BCode {data.BCode}",
                target_group_id=request.user.userprofilelink.group.id if request.user.userprofilelink.group else None
            )
            
            # Mock partner processing response
            response_data = {
                "status": "success",
                "message": "User notice callback received and processed",
                "data": {
                    "BCode": data.BCode,
                    "IsNotice": data.IsNotice,
                    "processed_at": datetime.now().isoformat(),
                    "partner_notice_id": f"MOCKNOTICE_{data.BCode}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "next_action": "Notice displayed to users in partner system"
                }
            }
            
            logger.info(f"✅ [PARTNER MOCKUP] Successfully processed user notice callback for BCode {data.BCode}")
            
            return BaseResponse(
                status_code=200,
                message="User notice callback received successfully",
                data=response_data
            )
            
        except Exception as e:
            error_msg = f"Error processing user notice callback: {str(e)}"
            logger.error(f"❌ [PARTNER MOCKUP] {error_msg}")
            
            # Send error notification
            self.send_websocket_notification(
                callback_type="DroneUserNotice",
                data={'error': str(e), 'input_data': dict(data)},
                success=False,
                message=error_msg,
                target_group_id="6"
            )
            
            return BaseResponse(
                status_code=500,
                message=error_msg,
                data={"error": str(e)}
            )
    
    @route.get("/test-websocket-connection")
    def test_websocket_connection(self, request: HttpRequest):
        """
        Test endpoint để kiểm tra WebSocket connection
        """
        try:
            request = get_current_request()
            # Send test notification
            test_data = {
                'test': True,
                'message': 'WebSocket connection test',
                'timestamp': datetime.now().isoformat()
            }
            
            self.send_websocket_notification(
                callback_type="test",
                data=test_data,
                partner_info={'test': True},
                success=True,
                message="WebSocket connection test successful",
                target_group_id=request.user.userprofilelink.group.id if request.user.userprofilelink.group else None
            )
            
            return BaseResponse(
                status_code=200,
                message="WebSocket test notification sent",
                data=test_data
            )
            
        except Exception as e:
            logger.error(f"❌ [PARTNER MOCKUP] Error testing WebSocket: {str(e)}")
            return BaseResponse(
                status_code=500,
                message=f"WebSocket test failed: {str(e)}",
                data={"error": str(e)}
            )


controllers = [
    PartnerCallbackMockupController,
]
