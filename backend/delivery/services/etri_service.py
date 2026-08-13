import requests
import json
import random
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings
from orders.models import OrderStatus
from delivery.repository.confirmation_repository import ConfirmationRepository
from orders.services.order_service import OrderService
from delivery.models import DeliveryOperation, DeliveryStatus
from delivery.config.etri_config import ETRI_API_ENDPOINTS, LOGISTICS_TYPE_MAPPING, ETRI_STATUS_MAPPING, ETRI_REQUEST_CONFIG
from django.db import transaction
import logging
from core.middleware.refresh_token import get_current_request
logger = logging.getLogger(__name__)

class EtriService:
    """Service for ETRI system integration"""
    
    @staticmethod
    def _get_etri_url() -> str:
        """Get ETRI API URL based on environment"""
        environment = getattr(settings, 'ETRI_ENVIRONMENT', 'development')
        base_url = ETRI_API_ENDPOINTS.get(environment, ETRI_API_ENDPOINTS['development'])
        request = get_current_request()
        user = request.user
        host = 'http://localhost:8000'
        api_endpoint = 'api/delivery/etri-mock/receive-delivery'
        if user:
            group = user.userprofilelink.group if getattr(user, 'userprofilelink', None) else None
            if group:
                group_settings = group.settings.get('send_url')
                if group_settings and group_settings.get('host') != '' and group_settings.get('api_endpoint') != '':
                    host = group_settings.get('host')
                    api_endpoint = group_settings.get('api_endpoint') 
                else:
                    host = 'http://localhost:8000'
                    api_endpoint = 'api/delivery/etri-mock/receive-delivery'
            else:
                pass
        else:
            pass
        return base_url.format(host=host, api_endpoint=api_endpoint)
    
    @staticmethod
    def send_delivery_to_etri(delivery_operation: DeliveryOperation, request) -> Dict[str, Any]:
        # """
        # Send delivery operation data to ETRI system
        # API 7: GAION 운영 시스템 -> ETRI 관제 시스템 송신 API
        # """
        try:
            # Prepare data for ETRI
            etri_data = EtriService._prepare_etri_data(delivery_operation, request)
            # Get ETRI API endpoint from config
            etri_url = EtriService._get_etri_url()
            print(etri_url) 
            # Send data to ETRI
            response = requests.post(
                etri_url,
                json=etri_data,
                headers=ETRI_REQUEST_CONFIG['headers'],
                timeout=ETRI_REQUEST_CONFIG['timeout']
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent delivery {delivery_operation.id} to ETRI")
                # Initialize another_info as dict if it's empty or not a dict
                if not delivery_operation.another_info or not isinstance(delivery_operation.another_info, dict):
                    delivery_operation.another_info = {}
                
                # Merge ETRI send data (preserve existing data with organized structure)
                etri_info = delivery_operation.another_info.get('etri', {})
                user = delivery_operation.order.created_by
                group_code = user.userprofilelink.group.code if user.userprofilelink.group else None
                tracking_number = f"ms_{group_code}_{str(delivery_operation.order.id).zfill(6)}"
                etri_info.update({
                    'receipt_id': etri_data['RECEIPT_ID'],
                    'mission_id': etri_data['MISSION_ID'],
                    'tracking_number': tracking_number,
                    'sent_to_etri_at': datetime.now().isoformat(),
                    'send_data': etri_data,
                    'last_send_status': 'success'
                })
                delivery_operation.another_info['etri'] = etri_info

                delivery_operation.current_status = DeliveryStatus.objects.get(code='select_route_processing')
                OrderService.create_order_history(delivery_operation.order.id, "", "verified")
                delivery_operation.save()

                delivery_operation.order.another_info['etri'] = etri_info
                delivery_operation.order.save()

                return {
                    'success': True,
                    'message': 'Delivery data sent to ETRI successfully',
                    'etri_response': response.json()
                }
            else:
                logger.error(f"Failed to send delivery {delivery_operation.id} to ETRI: {response.status_code}")
                return {
                    'success': False,
                    'message': f'ETRI API returned status {response.status_code}',
                    'error': response.text
                }
                 
        except requests.RequestException as e:
            logger.error(f"Network error sending delivery {delivery_operation.id} to ETRI: {str(e)}")
            return {
                'success': False,
                'message': 'Network error communicating with ETRI',
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error sending delivery {delivery_operation.id} to ETRI: {str(e)}")
            return {
                'success': False,
                'message': 'Unexpected error occurred',
                'error': str(e)
            }
    @staticmethod
    def _get_receiver_coordinates(order) -> str:
        try:
            """Get receiver coordinates"""
            if order.recipient_address and order.recipient_address.lat and order.recipient_address.lng:
                return f"[{order.recipient_address.lat}, {order.recipient_address.lng}]"
            else:
                logger.error(f"Order recipient address is missing coordinates: {order.recipient_address}")
                return "[]"
        except Exception as e:
            logger.error(f"Error getting receiver coordinates: {str(e)}")
            return "[]"
    

    @staticmethod
    def _prepare_etri_data(delivery_operation: DeliveryOperation, request) -> Dict[str, Any]:
        """Prepare delivery operation data for ETRI format"""
        order = delivery_operation.order
        
        # Get logistics type mapping
        logistics_type = EtriService._get_logistics_type(order)
        
        # Calculate total weight
        total_weight = EtriService._calculate_total_weight(order)
        
        # Get delivery address based on delivery option
        receiver_address, receiver_zipcode = EtriService._get_delivery_address_info(order)
        
        # Ensure receiver_zipcode is always a string
        if receiver_zipcode is None:
            receiver_zipcode = ''
        else:
            receiver_zipcode = str(receiver_zipcode)
        
        # Log for debugging
        logger.info(f"Delivery operation {delivery_operation.id}: receiver_zipcode = {receiver_zipcode} (type: {type(receiver_zipcode)})")
        
        user = request.user
        order_items = []
        for item in order.items.all():
            order_items.append({
                'ITEM_NAME': item.item_type.name,
                'ITEM_WEIGHT': item.weight.get('value', 0),
                'ITEM_UNIT': item.weight.get('unit', 'kg'),
                'ITEM_AMOUNT': float(item.amount.raw_amount) if item.amount and not item.amount.is_null else 0,
                'ITEM_CURRENCY': str(item.amount.currency_symbol) if item.amount else '',
                'ITEM_DESCRIPTION': item.note,
                'ITEM_TYPE': item.item_type.name if item.item_type else '', 
            })
        
        # Generate guaranteed unique ID: YYMMDD + delivery_operation_id(3 digits) + microseconds(3 digits)
        id = delivery_operation.order.another_info.get('etri', {}).get('receipt_id', '')
        if not id:
            now = datetime.now()
            microseconds = str(now.microsecond).zfill(6)[:3]  # Take first 3 digits of microseconds
            id = f"{now.strftime('%y%m%d')}{delivery_operation.id:03d}{microseconds}"
        
        # Safely get user profile information
        org_id = 'default'
        org_name = 'default'
        
        try:
            if user and hasattr(user, 'userprofilelink') and user.userprofilelink:
                profile = user.userprofilelink
                if hasattr(profile, 'group') and profile.group:
                    org_id = str(profile.group.code)
                    org_name = profile.group.name
        except (AttributeError, Exception):
            # Keep default values if any error occurs
            pass
        
        # Ensure all address fields are strings
        sender_address = EtriService._get_pickup_address(order) or ''
        sender_zipcode = EtriService._get_pickup_zipcode(order) or ''
        sender_terminal_id = str(order.pickup_location.id) if order.pickup_location else ''
        sender_terminal_name = order.pickup_location.name if order.pickup_location else ''
        sender_terminal_address = EtriService._get_pickup_full_address(order) or ''
        receiver_name = order.recipient_name or ''
        receiver_address = receiver_address or ''
        receiver_coordinates = EtriService._get_receiver_coordinates(order) or '[]'
        return {
            'USER_ID': str(user.id) if user else 'system',
            'ORG_ID': org_id,
            'RECEIPT_ID': id,
            'MISSION_ID': f"ms_{org_id}_{delivery_operation.order.id}",
            'RECEIPT_DATE': delivery_operation.created_on.strftime('%Y-%m-%d %H:%M:%S'),
            'SENDER_NAME': order.sender_name or '',
            'SENDER_ADDRESS': sender_address,
            'SENDER_ZIPCODE': sender_zipcode,
            'SENDER_TERMINAL_ID': sender_terminal_id,
            'SENDER_TERMINAL_NAME': sender_terminal_name,
            'SENDER_TERMINAL_ADDRESS': sender_terminal_address,
            'RECEIVER_NAME': receiver_name,
            'RECEIVER_ADDRESS': receiver_address,
            'RECEIVER_ZIPCODE': receiver_zipcode,
            'LOGISTICS_TYPE': logistics_type,
            'WEIGHT': total_weight,
            'RECEIVER_COORDINATES': receiver_coordinates,
            "RECEIVER_LAT": str(order.recipient_address.lat if order.recipient_address.lat else '') if order.recipient_address else '',
            "RECEIVER_LON": str(order.recipient_address.lng if order.recipient_address.lng else '') if order.recipient_address else '',
        }
        
    
    @staticmethod
    def _get_logistics_type(order) -> str:
        """Map order items to ETRI logistics type using config mapping"""
        # Get item types from order
        item_types = []
        for item in order.items.all():
            if item.item_type:
                item_types.append(item.item_type.name.lower())
        
        # Map using LOGISTICS_TYPE_MAPPING from config
        for etri_type, keywords in LOGISTICS_TYPE_MAPPING.items():
            for keyword in keywords:
                if any(keyword.lower() in item_type for item_type in item_types):
                    return etri_type
        
        # Default to 기타 if no match found
        return '기타'
    
    @staticmethod
    def _calculate_total_weight(order) -> int:
        """Calculate total weight of order items in grams"""
        total_weight = 0
        for item in order.items.all():
            if item.weight and isinstance(item.weight, dict):
                weight_value = item.weight.get('value', 0)
                weight_unit = item.weight.get('unit', 'kg')
                
                # Convert to grams
                if weight_unit == 'lb':
                    weight_value *= 453.592
                
                total_weight += int(weight_value)
        
        return total_weight or 100  # Default minimum weight if not specified
    
    @staticmethod
    def _get_pickup_address(order) -> str:
        """Get pickup location address"""
        if order.sender_address:
            return order.sender_address.full_address or ''
        return ''
    
    @staticmethod
    def _get_pickup_zipcode(order) -> str:
        """Get pickup location zipcode"""
        if order.sender_address:
            # Ensure postal_code is always a string
            postal_code = order.sender_address.postal_code
            return str(postal_code) if postal_code is not None else ''
        return ''
    
    @staticmethod
    def _get_pickup_full_address(order) -> str:
        """Get pickup location full address formatted"""
        if order.pickup_location:
            terminal = order.pickup_location
            # Combine address fields similar to terminal_views.py logic
            address_parts = []
            if terminal.street_address:
                address_parts.append(terminal.street_address)
            if terminal.ward_town_township:
                address_parts.append(terminal.ward_town_township)
            if terminal.city_county_district:
                address_parts.append(terminal.city_county_district)
            if terminal.city_province:
                address_parts.append(terminal.city_province)
            
            return ', '.join(address_parts) if address_parts else ''
        return ''
    
    @staticmethod
    def _get_delivery_address_info(order) -> tuple:
        """
        Get delivery address and zipcode based on delivery option
        Returns (address, zipcode) tuple
        
        Two mapping conditions based on order_views.py logic:
        1. collect_at_location: Use delivery_terminal address 
           Format: "Terminal Name (street, ward, district, province)"
        2. delivery_to_door: Use recipient_address.full_address
        """
        if not order.delivery_option:
            # Fallback to recipient address if no delivery option
            if order.recipient_address:
                postal_code = order.recipient_address.postal_code
                return (
                    order.recipient_address.full_address or '',
                    str(postal_code) if postal_code is not None else ''
                )
            else:
                return ('', '')
        
        if order.delivery_option.code == 'collect_at_location':
            # Use delivery terminal address
            if order.delivery_terminal:
                terminal = order.delivery_terminal
                # Format address similar to order_views.py
                address_parts = []
                if terminal.street_address:
                    address_parts.append(terminal.street_address)
                if terminal.ward_town_township:
                    address_parts.append(terminal.ward_town_township)
                if terminal.city_county_district:
                    address_parts.append(terminal.city_county_district)
                if terminal.city_province:
                    address_parts.append(terminal.city_province)
                
                full_address = f"{terminal.name} ({', '.join(address_parts)})" if address_parts else terminal.name
                # Terminal model doesn't have postal_code, use empty string or city_province as fallback
                postal_code = terminal.postal_code
                zipcode = str(postal_code) if postal_code is not None else ''
                
                return (full_address, zipcode)
            else:
                # If delivery_terminal is None, fallback to recipient address
                if order.recipient_address:
                    postal_code = order.recipient_address.postal_code
                    return (
                        order.recipient_address.full_address or '',
                        str(postal_code) if postal_code is not None else ''
                    )
                else:
                    return ('', '')
            
        elif order.delivery_option.code == 'delivery_to_door':
            # Use recipient address
            if order.recipient_address:
                postal_code = order.recipient_address.postal_code
                return (
                    order.recipient_address.full_address or '',
                    str(postal_code) if postal_code is not None else ''
                )
        
        # Fallback to recipient address
        if order.recipient_address:
            postal_code = order.recipient_address.postal_code
            return (
                order.recipient_address.full_address or '',
                str(postal_code) if postal_code is not None else ''
            )
        else:
            return ('', '')
    
    @staticmethod
    @transaction.atomic
    def receive_status_from_etri(etri_data: Dict[str, Any], request) -> Dict[str, Any]:
        """
        Receive delivery status update from ETRI system
        API 8: ETRI 관제 시스템 -> GAION 운영 시스템 송신 API
        """
        try:
            receipt_id = etri_data.get('RECEIPT_ID')
            mission_status = etri_data.get('MISSION_STATUS')
            if not receipt_id:
                return {
                    'success': False,
                    'message': 'RECEIPT_ID is required'
                }
            
            # Find delivery operation
            try:
               
                delivery_operation = DeliveryOperation.objects.get(another_info__etri__receipt_id=receipt_id)
                
            except DeliveryOperation.DoesNotExist:
                return {
                    'success': False,
                    'message': f'Delivery operation with ID {receipt_id} not found'
                }
            
            # Update delivery operation based on ETRI status
            success = EtriService._update_delivery_status(delivery_operation, etri_data, request)
            
            if success:
                logger.info(f"Successfully updated delivery {receipt_id} from ETRI status {mission_status}")
                return {
                    'success': True,
                    'message': 'Delivery status updated successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to update delivery status'
                }
                
        except Exception as e:
            logger.error(f"Error processing ETRI status update: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing status update',
                'error': str(e)
            }
    
    @staticmethod
    def _update_delivery_status(delivery_operation: DeliveryOperation, etri_data: Dict[str, Any], request) -> bool:
        """Update delivery operation status based on ETRI data using updated status mapping"""
        try:
            mission_status = etri_data.get('MISSION_STATUS')
            
            from delivery.models import DeliveryStatus
            
            # Map ETRI status to delivery status using updated config
            if mission_status in ETRI_STATUS_MAPPING:
                status_code = ETRI_STATUS_MAPPING[mission_status]
                try:
                    new_status = DeliveryStatus.objects.get(code=status_code)
                except DeliveryStatus.DoesNotExist:
                    print(status_code)
                    logger.error(f"DeliveryStatus with code '{status_code}' not found")
                    return False
            else:
                logger.warning(f"Unknown ETRI mission status: {mission_status}")
                return False
            
            # Update delivery operation
            delivery_operation.current_status = new_status
            
            # Handle different status updates with proper order history
            if delivery_operation.current_status.code == 'completed_order':
                # ETRI Status 0: 배송완료 - Delivery Completed
                ConfirmationRepository.add_delivered_order_delivery_history(delivery_operation)
                OrderService.create_order_history(delivery_operation.order.id, "Delivery completed by ETRI system", "delivered")
            
            elif delivery_operation.current_status.code == 'cancelled':
                # ETRI Status 1: 배송취소 - Delivery Cancelled 
                cancellation_reason = etri_data.get('CANCELLATION_REASON', 'No reason provided')
                delivery_operation.order.cancel_reason = cancellation_reason
                delivery_operation.order.status = OrderStatus.objects.get(code='cancelled')
                delivery_operation.order.save()
                logger.info(f"Delivery {delivery_operation.id} cancelled. Reason: {cancellation_reason}")
                OrderService.create_order_history(delivery_operation.order.id, f"Delivery cancelled by ETRI system. Reason: {cancellation_reason}", "cancelled")
                
            
                
            elif delivery_operation.current_status.code == 'receipt_cancelled':
                # ETRI Status 5: 접수취소 - Receipt Cancelled
                logger.info(f"Receipt for delivery {delivery_operation.id} was cancelled")
                OrderService.create_order_history(delivery_operation.order.id, "Receipt cancelled by ETRI system", "receipt_cancelled")
            
            delivery_operation.save()
            # Store ETRI data in another_info (preserve existing data with organized structure)
            if not delivery_operation.another_info or not isinstance(delivery_operation.another_info, dict):
                delivery_operation.another_info = {}
            
            # Get or create etri section
            etri_info = delivery_operation.another_info.get('etri', {})
            
            # Merge ETRI receive data (preserve existing data)
            etri_info.update({
                'receive_data': etri_data,
                'last_receive_at': datetime.now().isoformat(),
                'mission_status': mission_status,
                'last_receive_status': 'success'
            })
            
            delivery_operation.another_info['etri'] = etri_info
            delivery_operation.order.another_info['etri'] = etri_info
            delivery_operation.order.save()
            delivery_operation.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating delivery status: {str(e)}")
            return False 