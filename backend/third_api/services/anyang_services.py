"""
Anyang API Services
Business logic services cho Anyang integration
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.conf import settings

# Import models
# from common.utils import generate_unique_code
from orders.models import Order, OrderItemType, OrderStatus, OrderItem, ProductItem
from delivery.models import DeliveryOperation, DeliveryStatus, Address
from devices.models import PackagingSpecification, Device
from terminals.models import Terminal
from .address_service import KakaoAddressService
from .anyang_order_automation import AnyangOrderAutomation

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


class PackageSelectionService:
    """
    Service for selecting appropriate packages based on item specifications.
    Used for Anyang API integration to automatically assign packages.
    """
    
    @staticmethod
    def find_suitable_package(weight: float, length: float, width: float, height: float, 
                            is_waterproof: bool = False, is_fragile: bool = False) -> Optional[PackagingSpecification]:
        """
        Find the most suitable package based on item dimensions and requirements.
        Only considers packages that are attached to at least one active device.
        
        Args:
            weight: Weight in kg
            length: Length in mm
            width: Width in mm  
            height: Height in mm
            is_waterproof: Whether item needs waterproof packaging
            is_fragile: Whether item is fragile
            
        Returns:
            PackagingSpecification or None if no suitable package found
        """
        print(f"🔍 [PACKAGE SELECTION] Starting package search")
        print(f"   📦 Requirements: {weight}kg, {length}x{width}x{height}mm, waterproof: {is_waterproof}, fragile: {is_fragile}")
        
        # Base query - only get packages that are attached to active devices
        packages = PackagingSpecification.objects.filter(
            active=True,
            options__option__devices__device__active=True,  # Package must be linked to active device
            options__option__devices__device__isnull=False  # Ensure device exists
        ).distinct()
        
        print(f"   📋 Found {packages.count()} active packages to evaluate")
        suitable_packages = []
        
        for package in packages:
            print(f"   🧪 Evaluating package: {package.name}")
            
            # Check weight capacity - Handle None values
            weight_capacity = package.get_numeric_value('max_weight')
            print(f"      ⚖️  Weight check: {weight}kg vs {weight_capacity}kg capacity")
            if weight_capacity is None or weight_capacity <= 0:
                print(f"      ❌ Skipping - no valid weight capacity")
                continue  # Skip packages without valid weight capacity
            if weight > weight_capacity:
                print(f"      ❌ Skipping - weight exceeds capacity")
                continue
                
            # Check dimensions - Handle None values safely
            pkg_length = package.get_numeric_value('dimensions','length')
            pkg_width = package.get_numeric_value('dimensions','width') 
            pkg_height = package.get_numeric_value('dimensions','height')
            
            # Set default values if None
            pkg_length = pkg_length if pkg_length is not None else 0
            pkg_width = pkg_width if pkg_width is not None else 0
            pkg_height = pkg_height if pkg_height is not None else 0
            
            print(f"      📏 Dimension check: {length}x{width}x{height}mm vs {pkg_length}x{pkg_width}x{pkg_height}mm")
            
            # Skip packages with invalid dimensions
            if pkg_length <= 0 or pkg_width <= 0 or pkg_height <= 0:
                print(f"      ❌ Skipping - invalid package dimensions")
                continue
                
            if length > pkg_length or width > pkg_width or height > pkg_height: 
                print(f"      ❌ Skipping - item dimensions exceed package")
                continue
                
            # Check special requirements
            if is_waterproof and not getattr(package, 'is_waterproof', False):
                print(f"      ❌ Skipping - waterproof required but not available")
                continue
                
            if is_fragile and not getattr(package, 'supports_fragile', True):
                print(f"      ❌ Skipping - fragile support required but not available")
                continue
                
            # Calculate efficiency
            volume_efficiency = (length * width * height) / (pkg_length * pkg_width * pkg_height) if (pkg_length * pkg_width * pkg_height) > 0 else 0
            weight_efficiency = weight / weight_capacity if weight_capacity > 0 else 0
            
            # Special handling for zero weight items
            if weight == 0:
                # For zero weight, prioritize smallest package that fits dimensions
                # Use volume ratio to find most compact package
                volume_ratio = (pkg_length * pkg_width * pkg_height) / (length * width * height) if (length * width * height) > 0 else float('inf')
                # Inverse volume ratio as efficiency (smaller package = higher efficiency)
                total_efficiency = 1 / volume_ratio if volume_ratio > 0 else 0
                print(f"      📏 Zero weight detected - using volume optimization (ratio: {volume_ratio:.2f}, efficiency: {total_efficiency:.4f})")
                print(f"      ✅ Suitable! Zero-weight efficiency: {total_efficiency:.4f} (volume ratio: {volume_ratio:.2f})")
            else:
                total_efficiency = (volume_efficiency + weight_efficiency) / 2
                print(f"      ✅ Suitable! Efficiency: {total_efficiency:.2%} (vol: {volume_efficiency:.2%}, weight: {weight_efficiency:.2%})")
            
            # Pre-compute values for sorting to avoid repeated get_numeric_value calls
            pkg_weight_capacity = package.get_numeric_value('max_weight') or 0
            pkg_volume = (pkg_length or 0) * (pkg_width or 0) * (pkg_height or 0)
            
            # Note: Package price is determined at OrderItem level, not PackagingSpecification
            # Use weight_capacity as proxy for cost optimization (smaller capacity = cheaper)
            
            suitable_packages.append({
                'package': package,
                'volume_efficiency': volume_efficiency,
                'weight_efficiency': weight_efficiency,
                'total_efficiency': total_efficiency,
                'weight_capacity': pkg_weight_capacity,
                'volume': pkg_volume,
                'dimensions': {
                    'length': pkg_length or 0,
                    'width': pkg_width or 0,
                    'height': pkg_height or 0
                }
            })
        
        if not suitable_packages:
            print(f"   ❌ No suitable packages found")
            return None
            
        # Sort by multiple criteria for optimal selection:
        # 1. Best efficiency (highest first)
        # 2. If same efficiency, prefer smallest weight capacity (cost proxy)
        # 3. If same capacity, prefer smallest volume (space optimization)
        suitable_packages.sort(key=lambda x: (
            -x['total_efficiency'],  # Negative for descending order (best efficiency first)
            x['weight_capacity'],    # Ascending order (smallest capacity first) - cost proxy
            x['volume']              # Ascending order (smallest volume first) - space optimization
        ))
        
        best_package = suitable_packages[0]['package']
        best_info = suitable_packages[0]
        print(f"   🏆 Best package selected: {best_package.name} (efficiency: {best_info['total_efficiency']:.2%}, capacity: {best_info['weight_capacity']}kg)")
        
        # Show comparison if multiple packages have same efficiency
        same_efficiency_packages = [p for p in suitable_packages if abs(p['total_efficiency'] - suitable_packages[0]['total_efficiency']) < 0.001]
        if len(same_efficiency_packages) > 1:
            print(f"   📊 Multiple packages with same efficiency ({suitable_packages[0]['total_efficiency']:.2%}):")
            for pkg_info in same_efficiency_packages:
                pkg = pkg_info['package']
                dims = pkg_info['dimensions']
                print(f"      - {pkg.name}: {pkg_info['weight_capacity']}kg capacity, {dims['length']}x{dims['width']}x{dims['height']}mm")
            print(f"   ✅ Selected smallest capacity package for cost optimization: {best_package.name} ({best_info['weight_capacity']}kg)")
        
        return best_package
    
    @staticmethod
    def get_package_price(package: PackagingSpecification, weight: float) -> Decimal:
        """
        Calculate package price based on weight and package specifications.
        
        Args:
            package: PackagingSpecification instance
            weight: Weight in kg
            
        Returns:
            Decimal price
        """
        print(f"💰 [PRICING] Calculating price for package: {package.name}")
        print(f"   ⚖️  Weight: {weight}kg")
        
        base_price = Decimal('0')
        
        if hasattr(package, 'another_info') and package.another_info:
            print(f"   📊 Using custom pricing from package another_info")
            pricing = package.another_info.get('pricing', {})
            base_price = Decimal(str(pricing.get('base_price', 0)))
            weight_rate = Decimal(str(pricing.get('weight_rate_per_kg', 5000)))
            weight_price = weight_rate * Decimal(str(weight))
            total_price = base_price + weight_price
            
            print(f"      💰 Base price: {base_price}")
            print(f"      ⚖️  Weight rate: {weight_rate}/kg")
            print(f"      🧮 Weight cost: {weight_price}")
            print(f"      💳 Total price: {total_price}")
            
            return total_price
        
        # Default pricing
        print(f"   📊 Using default pricing (no custom pricing found)")
        default_rate = Decimal('10000')  # 10,000 VND base
        weight_rate = Decimal('5000')    # 5,000 VND per kg
        total_price = default_rate + (weight_rate * Decimal(str(weight)))
        
        print(f"      💰 Default base: {default_rate}")
        print(f"      ⚖️  Default weight rate: {weight_rate}/kg")
        print(f"      💳 Total price: {total_price}")
        
        return total_price
    
    @staticmethod
    def find_suitable_package_with_validation(weight: float, length: float, width: float, height: float, 
                            is_waterproof: bool = False, is_fragile: bool = False) -> Dict:
        """
        Find suitable package with detailed validation and error reporting.
        Only considers packages that are attached to at least one active device.
        Returns dict with 'package', 'error_code', and 'error_message'
        """
        print(f"🔍 [PACKAGE VALIDATION] Starting validation search")
        print(f"   📦 Requirements: {weight}kg, {length}x{width}x{height}mm, waterproof: {is_waterproof}, fragile: {is_fragile}")
        
        # Base query - only get packages that are attached to active devices
        packages = PackagingSpecification.objects.filter(
            active=True,
            options__option__devices__device__active=True,  # Package must be linked to active device
            options__option__devices__device__isnull=False  # Ensure device exists
        ).distinct()
        
        print(f"   📋 Checking {packages.count()} packages for global limits")
        
        # Check for weight exceeded (global limits)
        max_weight_exceeded = True
        max_size_exceeded = True
        
        for package in packages:
            # Check weight capacity
            weight_capacity = package.get_numeric_value('max_weight')
            if weight_capacity and weight_capacity > 0 and weight <= weight_capacity:
                print(f"   ✅ Package {package.name}: weight within limits ({weight}kg <= {weight_capacity}kg)")
                max_weight_exceeded = False
            
            # Check dimensions
            pkg_length = package.get_numeric_value('dimensions','length') or 0
            pkg_width = package.get_numeric_value('dimensions','width') or 0
            pkg_height = package.get_numeric_value('dimensions','height') or 0
            
            if (pkg_length > 0 and pkg_width > 0 and pkg_height > 0 and
                length <= pkg_length and width <= pkg_width and height <= pkg_height):
                print(f"   ✅ Package {package.name}: dimensions within limits")
                max_size_exceeded = False
        
        # Return specific error if limits exceeded
        if max_weight_exceeded:
            print(f"   ❌ WEIGHT_EXCEEDED: {weight}kg exceeds all package capacities")
            return {
                'package': None,
                'error_code': 'WEIGHT_EXCEEDED',
                'error_message': f'Weight {weight}kg exceeds maximum capacity of all available packages'
            }
        
        if max_size_exceeded:
            print(f"   ❌ SIZE_EXCEEDED: {length}x{width}x{height}mm exceeds all package dimensions")
            return {
                'package': None,
                'error_code': 'SIZE_EXCEEDED', 
                'error_message': f'Dimensions {length}x{width}x{height}mm exceed maximum size of all available packages'
            }
        
        print(f"   ✅ Global limits check passed, finding best suitable package...")
        
        # If no global limits exceeded, try to find suitable package
        suitable_package = PackageSelectionService.find_suitable_package(
            weight, length, width, height, is_waterproof, is_fragile
        )
        
        if suitable_package:
            print(f"   ✅ Suitable package found: {suitable_package.name}")
            return {
                'package': suitable_package,
                'error_code': None,
                'error_message': None
            }
        else:
            print(f"   ❌ No suitable package found despite passing global limits")
            return {
                'package': None,
                'error_code': 'WEIGHT_EXCEEDED',
                'error_message': 'No suitable package found for the given specifications'
            }


class AnyangOrderService:
    """
    Service for creating orders from Anyang API requests.
    Handles package selection and order creation with proper pricing.
    """
    
    @staticmethod
    @transaction.atomic  # SINGLE TRANSACTION cho toàn bộ quy trình
    def create_order_from_receipt_request(request_data: Dict) -> Tuple[bool, Dict]:
        """
        Create order from Anyang order receipt request (new API specification).
        
        Args:
            request_data: Dictionary containing OrderReceiptRequestSchema data
            
        Returns:
            Tuple of (success: bool, result: Dict)
        """
        print(f"🚀 [ORDER CREATION] Starting order creation from Anyang receipt request")
        print(f"   📝 Request data keys: {list(request_data.keys())}")
        
        try:
            # Extract data from request
            item_org_id = request_data.get('itemOrgId')
            item_type = request_data.get('itemType')
            receipt_date = request_data.get('receiptDate')
            start_delivery_point = request_data.get('startDeliveryPoint')
            end_delivery_point = request_data.get('endDeliveryPoint')
            
            print(f"   🔑 Key data extracted:")
            print(f"      📦 itemOrgId: {item_org_id}")
            print(f"      🏷️  itemType: {item_type}")
            print(f"      📅 receiptDate: {receipt_date}")
            print(f"      🚁 Route: {start_delivery_point} → {end_delivery_point}")
            
            # STRICT DUPLICATE CHECK - tránh lỗi select_for_update với outer join
            print(f"   🔍 Checking for duplicate orders with itemOrgId: {item_org_id}")
            existing_order = Order.objects.filter(
                another_info__item_org_id=item_org_id
            ).first()
            if existing_order:
                print(f"   ❌ DUPLICATE FOUND: Order {existing_order.order_code} already exists")
                error_msg = f"DUPLICATE ORDER: Order with itemOrgId {item_org_id} already exists (order_code: {existing_order.order_code})"
                raise Exception(error_msg)
            print(f"   ✅ No duplicate found")
            
            # Validate and get terminals by code
            print(f"   🏢 Validating terminals...")
            try:
                pickup_terminal = Terminal.objects.get(code=start_delivery_point, active=True)
                delivery_terminal = Terminal.objects.get(code=end_delivery_point, active=True)
                print(f"   ✅ Terminals validated:")
                print(f"      📤 Pickup: {pickup_terminal.name} (ID: {pickup_terminal.id})")
                print(f"      📥 Delivery: {delivery_terminal.name} (ID: {delivery_terminal.id})")
            except Terminal.DoesNotExist:
                print(f"   ❌ Terminal validation failed")
                return False, {'error': 'Invalid terminal code - terminal not found or inactive'}
            # Extract sender/receiver info
            print(f"   👤 Extracting sender/receiver information...")
            sender_name = request_data.get('senderName')
            sender_phone = request_data.get('senderContact') 
            sender_address_str = request_data.get('senderAddress')
            sender_zipcode = request_data.get('senderZipcode')
            
            recipient_name = request_data.get('receiverName')
            recipient_phone = request_data.get('receiverContact')
            recipient_address_str = request_data.get('receiverAddress')
            recipient_zipcode = request_data.get('receiverZipcode')
            
            print(f"      📤 Sender: {sender_name} ({sender_phone})")
            print(f"         🏠 Address: {sender_address_str} ({sender_zipcode})")
            print(f"      📥 Recipient: {recipient_name} ({recipient_phone})")
            print(f"         🏠 Address: {recipient_address_str} ({recipient_zipcode})")
            
            # Extract package dimensions and weight
            print(f"   📦 Extracting package specifications...")
            weight = float(request_data.get('weight', 0))
            height = float(request_data.get('height', 0))
            depth = float(request_data.get('depth', 0))
            width = float(request_data.get('width', 0))
            
            print(f"      ⚖️  Weight: {weight}kg")
            print(f"      📏 Dimensions: {depth}×{width}×{height}cm")
            
            # Create addresses using Kakao API
            print(f"   📍 Creating addresses...")
            sender_address = AnyangOrderService._create_address_with_geocoding(
                sender_address_str, sender_zipcode, "sender"
            )
            
            recipient_address = AnyangOrderService._create_address_with_geocoding(
                recipient_address_str, recipient_zipcode, "recipient"
            )
            
            # Generate incremental order code
            print(f"   🔢 Generating order code...")
            order_code = str(Order._base_manager.order_by('-id').first().id + 1).zfill(8)
            print(f"      📋 Generated order code: {order_code}")
            
            # Get default order status
            print(f"   🏷️  Setting up order status and options...")
            order_status = OrderStatus.objects.filter(code='pending_confirmation').first()
            if not order_status:
                print(f"      ⚠️  Creating missing order status")
                order_status = OrderStatus.objects.create(
                    name='Pending Confirmation', code='pending_confirmation'
                )
            print(f"      ✅ Order status: {order_status.name}")
            
            # Get delivery option (default to collect_at_location for Anyang orders)
            from orders.models import DeliveryOption
            delivery_option = DeliveryOption.objects.filter(code='collect_at_location').first()
            if not delivery_option:
                print(f"      ⚠️  Creating missing delivery option")
                # Create default delivery option if it doesn't exist
                delivery_option = DeliveryOption.objects.create(
                    name='Collect at Location',
                    code='collect_at_location',
                    description='Collect package at delivery terminal'
                )
            print(f"      ✅ Delivery option: {delivery_option.name}")
            
            # Create order
            print(f"   🛒 Creating order in database...")
            order = Order.objects.create(
                order_code=order_code,
                sender_name=sender_name, 
                sender_phone=sender_phone, 
                sender_address=sender_address,
                recipient_name=recipient_name, 
                recipient_phone=recipient_phone, 
                recipient_address=recipient_address,
                pickup_location=pickup_terminal,
                delivery_terminal=delivery_terminal,
                delivery_option=delivery_option,
                status=order_status,
                another_info={
                    'anyang_source': True,
                    'anyang_receipt_api': True,
                    'item_org_id': item_org_id,
                    'item_type': item_type,
                    'receipt_date': receipt_date,
                    'start_delivery_point': start_delivery_point,
                    'end_delivery_point': end_delivery_point,
                    'total_ready_time': request_data.get('totalReadyTime'),
                    'original_request': request_data
                }
            )
            print(f"   ✅ Order created successfully (ID: {order.id}, Code: {order.order_code})")
            
            # Find suitable package based on actual dimensions with detailed validation
            print(f"   📦 Finding suitable package...")
            print(f"      📏 Converting dimensions: {depth}×{width}×{height}cm → {int(depth * 10)}×{int(width * 10)}×{int(height * 10)}mm")
            
            package_result = PackageSelectionService.find_suitable_package_with_validation(
                weight=weight,
                length=int(depth * 10),  # Convert cm to mm
                width=int(width * 10),   # Convert cm to mm  
                height=int(height * 10), # Convert cm to mm
                is_waterproof=False,  # Not specified in new schema
                is_fragile=False,      # Not specified in new schema
            )
            
            if package_result['error_code']:
                print(f"   ❌ Package validation failed: {package_result['error_code']}")
                print(f"      📄 Error message: {package_result['error_message']}")
                
                # Raise specific error based on validation result
                if package_result['error_code'] == 'WEIGHT_EXCEEDED':
                    raise Exception(f"WEIGHT_EXCEEDED: Weight {weight}kg exceeds maximum capacity")
                elif package_result['error_code'] == 'SIZE_EXCEEDED':
                    raise Exception(f"SIZE_EXCEEDED: Dimensions exceed maximum package size")
                else:
                    raise Exception("No suitable package found")
            
            suitable_package = package_result['package']
            print(f"   ✅ Suitable package found: {suitable_package.name} (ID: {suitable_package.id})")
            
            # Calculate total amount from orderItems first
            print(f"   💰 Calculating order items pricing...")
            order_items_array = request_data.get('orderItems', [])
            print(f"      📊 Found {len(order_items_array)} items to process")
            total_item_price = Decimal('0')
            
            for i, item_data in enumerate(order_items_array, 1):
                item_price = Decimal(str(item_data.get('price', 0)))
                quantity = int(item_data.get('quantity', 1))
                total_price = item_price * quantity
                print(f"      📦 Item {i}: {item_data.get('ItemName', 'Unknown')} - {quantity}x{item_price} = {total_price}")
                total_item_price += total_price
            
            print(f"      💰 Total items value: {total_item_price}")
            
            # Get order item type
            print(f"   🏷️  Setting up order item type...")
            try:
                order_item_type = OrderItemType.objects.get(code=item_type)
                print(f"      ✅ Found order item type: {order_item_type.name}")
            except OrderItemType.DoesNotExist:
                order_item_type = OrderItemType.objects.filter(is_active=True).first()
                print(f"      ⚠️  Item type '{item_type}' not found, using default: {order_item_type.name if order_item_type else 'None'}")
            
            # Create main order item (package container) with total amount from orderItems
            print(f"   📦 Creating main order item (package container)...")
            order_item = OrderItem.objects.create(
                order=order, 
                code=f"{item_org_id}",
                name=f"Package for {item_org_id}",
                item_type=order_item_type,
                weight={'value': weight, 'unit': 'kg'},
                dimension_l={'value': int(depth * 10), 'unit': 'mm'},
                dimension_w={'value': int(width * 10), 'unit': 'mm'},
                dimension_h={'value': int(height * 10), 'unit': 'mm'},
                package_id=suitable_package, 
                amount=total_item_price  # Use total from orderItems instead of package price
            )
            print(f"   ✅ Order item created (ID: {order_item.id}, Amount: {total_item_price})")
            
            # Create product items from orderItems array
            print(f"   📋 Creating product items from orderItems array...")
            for i, item_data in enumerate(order_items_array, 1):
                item_price = Decimal(str(item_data.get('price', 0)))
                quantity = int(item_data.get('quantity', 1))
                total_price = item_price * quantity
                item_name = item_data.get('ItemName', 'Unknown Item')
                
                product_item = ProductItem.objects.create(
                    order_item=order_item, 
                    name=item_name,
                    description=f"Item from order {item_org_id}",
                    quantity=quantity, 
                    unit_weight={'value': weight / len(order_items_array) if len(order_items_array) > 0 else weight, 'unit': 'kg'},
                    unit_price=item_price, 
                    total_price=total_price,
                    product_type='general'
                )
                print(f"      ✅ Product item {i} created: {item_name} (ID: {product_item.id})")
            
            # Calculate order totals
            print(f"   🧮 Calculating order totals...")
            order.calculate_totals()
            order.save()
            print(f"   ✅ Order totals calculated:")
            print(f"      💰 Subtotal: {order.subtotal}")
            print(f"      💰 Total amount: {order.total_amount}")
            
            # Tự động tạo delivery operation và tính deliveryETA
            # QUY TRÌNH AUTOMATION PHẢI THÀNH CÔNG HOÀN TOÀN
            print(f"   🤖 Starting automation process...")
            print(f"      🚁 Creating delivery operation and processing route...")
            automation_success, automation_result = AnyangOrderAutomation.create_and_process_delivery_operation(order)
            
            if automation_success:
                print(f"   ✅ Automation completed successfully!")
                delivery_eta_formatted = automation_result.get('delivery_eta_formatted', '')
                print(f"      📅 Delivery ETA: {delivery_eta_formatted}")
                
                # Get operation, route, and drone from automation result
                operation = automation_result.get('operation')
                # route = automation_result.get('route')
                # drone = automation_result.get('drone')
                
                print(f"      📊 Automation results:")
                print(f"         🚁 Operation ID: {operation.id if operation else 'None'}")
                # print(f"         🛣️  Route ID: {route.id if route else 'None'}")
                # print(f"         🚁 Drone ID: {drone.id if drone else 'None'}")
                
                # Validate automation result completeness
                if not operation:
                    print(f"      ❌ Missing operation in automation result")
                    raise Exception("Operation not found in automation result")
                # if not route:
                #     print(f"      ❌ Missing route in automation result")
                #     raise Exception("Route not found in automation result")
                # if not drone:
                #     print(f"      ❌ Missing drone in automation result")
                #     raise Exception("Drone not found in automation result")
                    
                print(f"🎉 [ORDER CREATION] Order creation completed successfully!")
                print(f"   📋 Order Code: {order.order_code}")
                print(f"   💰 Total Amount: {total_item_price}")
                print(f"   📅 Delivery ETA: {delivery_eta_formatted}")
                
                return True, {
                    'order': order, 
                    'order_item': order_item,
                    'suitable_package': suitable_package, 
                    'total_amount': total_item_price,
                    'pickup_terminal': pickup_terminal,
                    'delivery_terminal': delivery_terminal,
                    'total_item_price': total_item_price,
                    'delivery_eta_formatted': delivery_eta_formatted,
                    'automation_result': automation_result,
                    # Add operation, route, drone data for view
                    'operation': operation,
                    # 'route': route,
                    # 'drone': drone,
                    # Add detailed success info
                    'success_details': {
                        'order_totals_calculated': True,
                        'subtotal': str(order.subtotal) if order.subtotal else None,
                        'total_amount': str(order.total_amount) if order.total_amount else None,
                        'automation_complete': True,
                        'has_operation': operation is not None,
                        # 'has_route': route is not None,
                        # 'has_drone': drone is not None
                    }
                }
            else:
                # AUTOMATION FAILED - Raise exception để trigger transaction rollback
                print(f"   ❌ Automation failed!")
                error_msg = automation_result.get('error', 'Unknown automation error')
                step_failed = automation_result.get('step_failed', 'unknown_step')
                user_message = automation_result.get('user_message', 'Lỗi hệ thống')
                error_code = automation_result.get('error_code', 'SYSTEM_ERROR')
                error_details = automation_result.get('error_details', {})
                
                print(f"      📄 Error: {error_msg}")
                print(f"      📍 Step failed: {step_failed}")
                print(f"      💬 User message: {user_message}")
                print(f"      🔢 Error code: {error_code}")
                
                # Raise exception để Django tự động rollback toàn bộ transaction
                raise Exception(f'Order automation failed: {error_msg}')
            
        except Exception as e:
            # EXPLICIT ROLLBACK - đảm bảo transaction được rollback
            from django.db import transaction
            transaction.set_rollback(True)
            
            error_message = str(e)
            print(f"❌ [ORDER CREATION] Exception occurred: {error_message}")
            print(f"   🔄 Transaction rollback initiated")
            
            # Determine appropriate error categorization  
            if 'No suitable route found' in error_message:
                step_failed = 'route_selection'
                user_message = 'Không tìm thấy tuyến đường phù hợp'
                error_code = 'ROUTE_NOT_FOUND'
                print(f"   📍 Categorized as: Route selection error")
            elif 'No suitable drone found' in error_message:
                step_failed = 'drone_selection'
                user_message = 'Không có drone khả dụng'
                error_code = 'DRONE_NOT_AVAILABLE'
                print(f"   📍 Categorized as: Drone availability error")
            elif 'WEIGHT_EXCEEDED' in error_message:
                step_failed = 'package_validation'
                user_message = 'Trọng lượng vượt quá giới hạn cho phép'
                error_code = 'WEIGHT_EXCEEDED'
                print(f"   📍 Categorized as: Weight exceeded error")
            elif 'SIZE_EXCEEDED' in error_message:
                step_failed = 'package_validation'
                user_message = 'Kích thước vượt quá giới hạn cho phép'
                error_code = 'SIZE_EXCEEDED'
                print(f"   📍 Categorized as: Size exceeded error")
            elif 'automation failed' in error_message:
                step_failed = 'automation_workflow'
                user_message = 'Lỗi quy trình tự động hóa'
                error_code = 'AUTOMATION_FAILED'
                print(f"   📍 Categorized as: Automation workflow error")
            elif 'already exists' in error_message:
                step_failed = 'duplicate_data'
                user_message = 'Đơn hàng đã tồn tại'
                error_code = 'DUPLICATE_ORDER'
                print(f"   📍 Categorized as: Duplicate order error")
            elif 'calculate_totals' in error_message:
                step_failed = 'order_calculation'
                user_message = 'Lỗi tính toán giá tiền đơn hàng'
                error_code = 'CALCULATION_ERROR'
                print(f"   📍 Categorized as: Order calculation error")
            elif 'Terminal' in error_message:
                step_failed = 'terminal_validation'
                user_message = 'Terminal không hợp lệ'
                error_code = 'INVALID_TERMINAL'
                print(f"   📍 Categorized as: Terminal validation error")
            else:
                step_failed = 'order_creation'
                user_message = 'Lỗi tạo đơn hàng'
                error_code = 'ORDER_CREATION_ERROR'
                print(f"   📍 Categorized as: General order creation error")
                
            print(f"   📋 Error details:")
            print(f"      🔢 Error code: {error_code}")
            print(f"      📍 Step failed: {step_failed}")
            print(f"      💬 User message: {user_message}")
            print(f"      📦 Order ID: {request_data.get('itemOrgId', 'unknown')}")
            print(f"   ✅ Transaction rollback completed")
                
            return False, {
                'error': error_message,
                'step_failed': step_failed,
                'user_message': user_message,
                'error_code': error_code,
                'order_code': request_data.get('itemOrgId', 'unknown'),
                'rollback_completed': True,
               
            }
    
    @staticmethod
    def _create_address_with_geocoding(address_str: str, zipcode: str = None, address_type: str = "address") -> Address:
        """
        Create Address object using Kakao API for geocoding.
        Falls back to basic address creation if API fails.
        
        Args:
            address_str: Full address string
            zipcode: Optional postal code
            address_type: Type of address for logging (sender/recipient)
            
        Returns:
            Address object
        """
        print(f"📍 [ADDRESS CREATION] Creating {address_type} address")
        print(f"   🏠 Address: {address_str}")
        print(f"   📮 Zipcode: {zipcode}")
        
        try:
            # Try to geocode using Kakao API
            print(f"   🌐 Attempting Kakao API geocoding...")
            success, geocoded_data = KakaoAddressService.geocode_address(address_str)
            
            if success and geocoded_data:
                print(f"   ✅ Kakao geocoding successful")
                print(f"      📍 Coordinates: {geocoded_data.get('latitude')}, {geocoded_data.get('longitude')}")
                print(f"      🏘️  Parsed: {geocoded_data.get('city_province')} > {geocoded_data.get('city_county_district')} > {geocoded_data.get('ward_town_township')}")
                
                # Use geocoded data from Kakao API
                address = Address.objects.create(
                    full_address=geocoded_data.get('full_address', address_str),
                    city=geocoded_data.get('city_province'),
                    district=geocoded_data.get('city_county_district'), 
                    ward=geocoded_data.get('ward_town_township'),
                    street=geocoded_data.get('street_address', address_str),
                    postal_code=geocoded_data.get('postal_code') or zipcode,
                    lat=geocoded_data.get('latitude'),
                    lng=geocoded_data.get('longitude')
                )
                print(f"   ✅ Address created with ID: {address.id}")
                return address
            
            else:
                print(f"   ⚠️  Kakao geocoding failed, using fallback basic address")
                # Fallback to basic address creation
                address = Address.objects.create(
                    full_address=address_str,
                    city=None,
                    district=None,
                    ward=None,
                    street=address_str,
                    postal_code=zipcode,
                    lat=None,
                    lng=None
                )
                print(f"   ✅ Basic address created with ID: {address.id}")
                return address
                
        except Exception as e:
            print(f"   ❌ Address creation error: {str(e)}")
            print(f"   🔄 Using final fallback method")
            
            # Final fallback
            address = Address.objects.create(
                full_address=address_str,
                city=None,
                district=None,
                ward=None,
                street=address_str,
                postal_code=zipcode,
                lat=None,
                lng=None
            )
            print(f"   ✅ Fallback address created with ID: {address.id}")
            return address
    
    


class AnyangDeliveryService:
    """
    Service for managing delivery operations for Anyang integration.
    """
    
    @staticmethod
    def create_delivery_operation(order: Order, estimated_hours: int = 2) -> DeliveryOperation:
        """
        Create delivery operation for an order.
        
        Args:
            order: Order instance
            estimated_hours: Estimated delivery time in hours
            
        Returns:
            DeliveryOperation instance
        """
        delivery_operation = DeliveryOperation.objects.create(
            order=order,
            current_status=DeliveryStatus.objects.filter(code='unverified').first(),
        )
        
        return delivery_operation
    
    @staticmethod
    def update_delivery_status(delivery_operation: DeliveryOperation, new_status_code: str, 
                             reason: str = '', location: str = '') -> bool:
        """
        Update delivery operation status.
        
        Args:
            delivery_operation: DeliveryOperation instance
            new_status_code: New status code
            reason: Reason for status change
            location: Current location
            
        Returns:
            Success boolean
        """
        try:
            new_status = DeliveryStatus.objects.filter(code=new_status_code).first()
            if not new_status:
                return False
                
            old_status = delivery_operation.current_status.code if delivery_operation.current_status else 'unknown'
            delivery_operation.current_status = new_status
            
            # Update history
            if not delivery_operation.another_info:
                delivery_operation.another_info = {}
            
            if 'status_history' not in delivery_operation.another_info:
                delivery_operation.another_info['status_history'] = []
            
            delivery_operation.another_info['status_history'].append({
                'from_status': old_status,
                'to_status': new_status_code,
                'update_time': datetime.now().isoformat(),
                'reason': reason,
                'location': location
            })
            
            delivery_operation.save()
            return True
            
        except Exception as e:
            return False 


class AnyangCallbackService:
    """Service for sending callback notifications to Anyang delivery app"""
    
    # Status mapping từ internal delivery status sang Anyang status codes
    DELIVERY_STATUS_TO_ANYANG_MAPPING = {
        'unverified_order': 4,         # Receipt Completed (접수완료)
        'verified_order': 4,           # Receipt Completed (접수완료)
        'cancelled': 1,                # Delivery Cancelled (배송취소)
        'overdue_order': 1,            # Delivery Cancelled (배송취소)
        'returned_order': 1,           # Delivery Cancelled (배송취소)
        'processed_order': 1,          # Delivery Cancelled (배송취소)
        'order_pending_returned': 1,   # Delivery Cancelled (배송취소)
        'order_due_for_returned': 1,   # Delivery Cancelled (배송취소)
        'select_route_processing': 3,  # Waiting for Delivery (배송대기)
        'select_drone_processing': 3,  # Waiting for Delivery (배송대기)
        'in_transit_processing': 2,    # In Delivery (배송중)
        'completed_order': 0,          # Delivery Completed (배송완료)
        'arrived_order': 0,            # Delivery Completed (배송완료)
        'receipt_cancelled': 5,        # Receipt Cancelled (접수취소)
    }
    
    # Message codes for different scenarios
    MESSAGE_CODES = {
        'normal': 0,                   # Normal status
        'weather': 1,                  # Weather related cancellation
        'maintenance': 2,              # All drones under maintenance
        'loading_impossible': 3,       # Loading impossible
        'customer_cancellation': 4,    # Customer cancellation
        'store_cancellation': 5,       # Store cancellation
        'not_operating_hours': 6,      # Not operating hours
    }
    
    @staticmethod
    def get_anyang_status_code(delivery_status_code: str) -> int:
        """
        Get Anyang status code from delivery status code
        
        Args:
            delivery_status_code: Internal delivery status code
            
        Returns:
            int: Anyang status code (0-5)
        """
        return AnyangCallbackService.DELIVERY_STATUS_TO_ANYANG_MAPPING.get(
            delivery_status_code, 4  # Default to Receipt Completed
        )
    
    @staticmethod
    def get_delivery_photo_info(delivery_operation):
        """
        Get delivery photo information for completed deliveries
        FOR COMPLETED DELIVERIES, PHOTO IS MANDATORY according to API spec
        Priority: real confirmation_photo > fake generated photo

        Args:
            delivery_operation: DeliveryOperation instance

        Returns:
            dict or None: Delivery photo info if available
        """
        try:
            from datetime import datetime
            from django.conf import settings

            # PRIORITY 1: Real uploaded photo from confirmation_photo field
            if delivery_operation.confirmation_photo:
                return {
                    'url': delivery_operation.confirmation_photo.url,
                    'timestamp': delivery_operation.actual_delivery_time.strftime('%Y%m%d%H%M%S') if delivery_operation.actual_delivery_time else datetime.now().strftime('%Y%m%d%H%M%S')
                }

            if delivery_operation.current_status.code in ['completed_order', 'arrived_order']:
                fake_photo_url = f"{getattr(settings, 'SITE_URL', 'https://guardianx.com')}/api/delivery/confirmation/{delivery_operation.id}/photo/"
                return {
                    'url': fake_photo_url,
                    'timestamp': delivery_operation.actual_delivery_time.strftime('%Y%m%d%H%M%S') if delivery_operation.actual_delivery_time else datetime.now().strftime('%Y%m%d%H%M%S')
                }
            return None

        except Exception as e:
            if delivery_operation.current_status.code in ['completed_order', 'arrived_order']:
                try:
                    from datetime import datetime
                    from django.conf import settings
                    
                    fake_photo_url = f"{getattr(settings, 'SITE_URL', 'https://guardianx.com')}/api/delivery/confirmation/{delivery_operation.id}/photo/"
                    return {
                        'url': fake_photo_url,
                        'timestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                    }
                except:
                    return None
            return None
    
    @staticmethod
    def get_message_code(status_code: str, cancellation_reason: str = None, order=None) -> int:
        """
        Get appropriate message code based on status and cancellation reason
        Enhanced to better match cancellation reasons with proper codes
        
        Args:
            status_code: Internal delivery status code
            cancellation_reason: Cancellation reason if applicable
            order: Order instance for additional context
            
        Returns:
            int: Message code (0-6)
        """
        # For normal completed deliveries
        if status_code in ['completed_order', 'arrived_order', 'in_transit_processing', 
                          'select_route_processing', 'select_drone_processing', 
                          'unverified_order', 'verified_order']:
            return AnyangCallbackService.MESSAGE_CODES['normal']
        
        # For cancelled statuses, determine specific reason based on multiple sources
        if status_code in ['cancelled', 'overdue_order', 'returned_order', 
                          'processed_order', 'order_pending_returned', 
                          'order_due_for_returned']:
            
            # Collect all possible reason sources
            reasons_to_check = []
            
            # 1. Explicit cancellation_reason parameter
            if cancellation_reason:
                reasons_to_check.append(cancellation_reason.lower())
            
            # 2. Order cancel_reason field
            if order and hasattr(order, 'cancel_reason') and order.cancel_reason:
                reasons_to_check.append(order.cancel_reason.lower())
            
            # 3. Order another_info for cancellation details
            if order and order.another_info:
                cancel_info = order.another_info.get('cancellation', {})
                if cancel_info.get('reason'):
                    reasons_to_check.append(cancel_info['reason'].lower())
                if cancel_info.get('category'):
                    reasons_to_check.append(cancel_info['category'].lower())
            
            # Check all reason sources for keywords
            all_reasons = ' '.join(reasons_to_check)
            
            # Weather related (Code 1)
            weather_keywords = ['weather', 'rain', 'wind', 'storm', 'fog', '날씨', '비', '바람', '폭풍', '안개']
            if any(keyword in all_reasons for keyword in weather_keywords):
                return AnyangCallbackService.MESSAGE_CODES['weather']
            
            # Maintenance related (Code 2)
            maintenance_keywords = ['maintenance', 'repair', 'service', 'drone', 'technical', '정비', '수리', '드론', '기술적']
            if any(keyword in all_reasons for keyword in maintenance_keywords):
                return AnyangCallbackService.MESSAGE_CODES['maintenance']
            
            # Loading impossible (Code 3)
            loading_keywords = ['loading', 'load', 'weight', 'size', 'packaging', 'impossible', '적재', '무게', '크기', '포장', '불가']
            if any(keyword in all_reasons for keyword in loading_keywords):
                return AnyangCallbackService.MESSAGE_CODES['loading_impossible']
            
            # Customer cancellation (Code 4)
            customer_keywords = ['customer', 'client', 'buyer', 'user', 'requester', '고객', '주문자', '구매자', '사용자']
            if any(keyword in all_reasons for keyword in customer_keywords):
                return AnyangCallbackService.MESSAGE_CODES['customer_cancellation']
            
            # Store cancellation (Code 5)
            store_keywords = ['store', 'shop', 'merchant', 'vendor', 'seller', '상점', '판매자', '매장', '상인']
            if any(keyword in all_reasons for keyword in store_keywords):
                return AnyangCallbackService.MESSAGE_CODES['store_cancellation']
            
            # Operating hours (Code 6)
            hours_keywords = ['hours', 'time', 'closed', 'operating', 'business', '시간', '운영', '영업', '마감']
            if any(keyword in all_reasons for keyword in hours_keywords):
                return AnyangCallbackService.MESSAGE_CODES['not_operating_hours']
            
            # Default for cancelled orders without specific reason
            return AnyangCallbackService.MESSAGE_CODES['customer_cancellation']
        
        # For receipt cancelled - typically customer or system cancellation
        if status_code == 'receipt_cancelled':
            # Check if it's a system/store cancellation vs customer cancellation
            if cancellation_reason:
                system_keywords = ['system', 'automatic', 'validation', 'error', '시스템', '자동', '검증', '오류']
                if any(keyword in cancellation_reason.lower() for keyword in system_keywords):
                    return AnyangCallbackService.MESSAGE_CODES['store_cancellation']
            
            return AnyangCallbackService.MESSAGE_CODES['customer_cancellation']
            
        # Default to normal for any other status
        return AnyangCallbackService.MESSAGE_CODES['normal']
    
    @staticmethod
    def set_delivery_photo(delivery_operation, photo_url: str, timestamp: str = None):
        """
        Set delivery photo information for a delivery operation
        
        Args:
            delivery_operation: DeliveryOperation instance
            photo_url: URL of the delivery photo
            timestamp: Photo capture timestamp (YYYYMMDDHHmmss format)
        """
        try:
            from datetime import datetime
            
            if not timestamp:
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Update another_info with photo information
            another_info = delivery_operation.another_info or {}
            if 'anyang' not in another_info:
                another_info['anyang'] = {}
            
            another_info['anyang']['delivery_photo_url'] = photo_url
            another_info['anyang']['delivery_photo_timestamp'] = timestamp
            another_info['anyang']['photo_set_at'] = datetime.now().isoformat()
            
            delivery_operation.another_info = another_info
            delivery_operation.save()
            
            logger.info(f"✅ Set delivery photo for operation {delivery_operation.id}: {photo_url}")
            
        except Exception as e:
            logger.error(f"Error setting delivery photo for operation {delivery_operation.id}: {str(e)}")
            return False
    
    @staticmethod
    def trigger_completion_callback(delivery_operation, photo_url: str = None):
        """
        Manually trigger completion callback with optional photo
        
        Args:
            delivery_operation: DeliveryOperation instance
            photo_url: Optional delivery photo URL
            
        Returns:
            bool: True if callback sent successfully
        """
        try:
            # Set photo if provided
            if photo_url:
                AnyangCallbackService.set_delivery_photo(delivery_operation, photo_url)
            
            # Send callback
            return AnyangCallbackService.send_status_callback(delivery_operation)
            
        except Exception as e:
            return False
    
    @staticmethod
    def should_send_callback(delivery_operation) -> bool:
        """
        Determine if callback should be sent for this delivery operation
        
        Args:
            delivery_operation: DeliveryOperation instance
            
        Returns:
            bool: True if callback should be sent
        """
        try:
            # Check if this is an Anyang order
            another_info = delivery_operation.another_info or {}
            anyang_info = another_info.get('anyang', {})
            # Must have Anyang order information
            if not anyang_info.get('itemOrgId'):
                return False
                
            # Must have service key (indicates this is Anyang integration)
            if not anyang_info.get('serviceKey'):
                return False
                
            return True
            
        except Exception as e:
            return False
    
    @staticmethod
    def send_status_callback(delivery_operation, old_status_code=None):
        """
        Send status change callback to Anyang delivery app
        Authentication is done via serviceKey in request body (not API-key headers)
        
        Args:
            delivery_operation: DeliveryOperation instance
            old_status_code: Previous status code for comparison
            
        Returns:
            bool: True if callback sent successfully
        """
        try:
            from datetime import datetime
            from ..schemas.anyang_schemas_in import OrderDeliveryStatusCallbackSchema, DeliveryPhotoSchema
            import requests
            from ..common.utils import get_anyang_target_url
            import os
            
            # Check if callback should be sent
            if not AnyangCallbackService.should_send_callback(delivery_operation):
                return False
                
            # Get Anyang order information
            another_info = delivery_operation.another_info or {}
            anyang_info = another_info.get('anyang', {})
            
            item_org_id = anyang_info.get('itemOrgId')
            
            # Use ANYANG_SERVICE_KEY from environment for all requests
            service_key = os.getenv('ANYANG_SERVICE_KEY')
            if not service_key:
                return False
            
            if not item_org_id:
                return False
            
            # Get status codes
            current_status_code = delivery_operation.current_status.code
            anyang_status_code = AnyangCallbackService.get_anyang_status_code(current_status_code)
            
            # Get message code
            cancellation_reason = getattr(delivery_operation.order, 'cancel_reason', None)
            message_code = AnyangCallbackService.get_message_code(current_status_code, cancellation_reason, delivery_operation.order)
            
            # Get delivery photo if applicable
            delivery_photo = None
            photo_info = AnyangCallbackService.get_delivery_photo_info(delivery_operation)
            
            # For completed deliveries, photo is MANDATORY according to API spec
            if current_status_code in ['completed_order', 'arrived_order']:
                if not photo_info:
                    return False
                    
                delivery_photo = DeliveryPhotoSchema(**photo_info)
                logger.info(f"📷 Sending completion callback with photo: {photo_info['url']}")
            elif photo_info:
                # Optional photo for other statuses
                delivery_photo = DeliveryPhotoSchema(**photo_info)
            
            # Create callback data with serviceKey authentication
            # According to Anyang spec: deliveryPhoto should be {} when no photo
            photo_data = {}
            if delivery_photo:
                photo_data = delivery_photo
            
            callback_data = OrderDeliveryStatusCallbackSchema(
                serviceKey=service_key,  # Use env ANYANG_SERVICE_KEY
                itemOrgId=item_org_id,
                deliveryStatus=anyang_status_code,
                message=message_code,
                deliveryPhoto=photo_data,  # Empty dict {} when no photo, per Anyang spec
                updateTime=datetime.now().strftime('%Y%m%d%H%M%S')
            )
            
            # Get target URL
            target_url = get_anyang_target_url()
            if not target_url:
                return False
            
            # Prepare request data
            request_data = callback_data.model_dump()
            # Send HTTP request with serviceKey in body (no Authorization header)
            try:
                response = requests.post(
                    f"{target_url}/Callback",
                    json=request_data,
                    headers={
                        'Content-Type': 'application/json',
                        # No Authorization header - authentication via serviceKey in body
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    logger.info(f"✅ Anyang callback sent successfully for order {item_org_id}")
                    logger.info(f"   → Status: {current_status_code} -> {anyang_status_code}")
                    logger.info(f"   → Message Code: {message_code}")
                    logger.info(f"   → ServiceKey authentication: ✅")
                    
                    # Store callback result in another_info
                    if 'anyang' not in another_info:
                        another_info['anyang'] = {}
                    if 'callbacks' not in another_info['anyang']:
                        another_info['anyang']['callbacks'] = []
                        
                    another_info['anyang']['callbacks'].append({
                        'timestamp': datetime.now().isoformat(),
                        'status_code': anyang_status_code,
                        'message_code': message_code,
                        'response_status': response.status_code,
                        'success': True,
                        'method': 'http_request'
                    })
                    
                    delivery_operation.another_info = another_info
                    delivery_operation.save()
                    
                    return True
                else:
                    
                    # Store failure in another_info
                    if 'anyang' not in another_info:
                        another_info['anyang'] = {}
                    if 'callbacks' not in another_info['anyang']:
                        another_info['anyang']['callbacks'] = []
                        
                    another_info['anyang']['callbacks'].append({
                        'timestamp': datetime.now().isoformat(),
                        'status_code': anyang_status_code,
                        'message_code': message_code,
                        'response_status': response.status_code,
                        'success': False,
                        'error': f"HTTP {response.status_code}",
                        'method': 'http_request'
                    })
                    
                    delivery_operation.another_info = another_info
                    delivery_operation.save()
                    
                    return False
                    
            except requests.exceptions.RequestException as e:
                print("e", e)
                # Store failure in another_info
                if 'anyang' not in another_info:
                    another_info['anyang'] = {}
                if 'callbacks' not in another_info['anyang']:
                    another_info['anyang']['callbacks'] = []
                    
                another_info['anyang']['callbacks'].append({
                    'timestamp': datetime.now().isoformat(),
                    'status_code': anyang_status_code,
                    'message_code': message_code,
                    'success': False,
                    'error': str(e),
                    'method': 'http_request'
                })
                
                delivery_operation.another_info = another_info
                delivery_operation.save()
                
                return False
                
        except Exception as e:
            print(e)
            return False 