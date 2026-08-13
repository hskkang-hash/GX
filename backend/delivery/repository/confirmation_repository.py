from devices.models import Device, DeviceStatus
from delivery.models import DeliveryOperation, DeliveryOperationItem, DeliveryStatus
from orders.models import OrderHistory, OrderStatus
from django.db.models import QuerySet
from typing import Optional
from django.utils import timezone
from core.multilanguage.request_handlers import update_model_with_translations, create_model_with_translations

class ConfirmationRepository:
    @staticmethod
    def get_delivery_operation_item_by_id(package_id: int) -> Optional[DeliveryOperationItem]:
        """Get DeliveryOperationItem by ID with related objects"""
        try:
            return DeliveryOperationItem.objects.select_related(
                'drone',
                'delivery_operation',
                'delivery_operation__order',
                'order_item'
            ).get(id=package_id)
        except DeliveryOperationItem.DoesNotExist:
            return None

    @staticmethod
    def get_delivery_status_by_code(code: str) -> Optional[DeliveryStatus]:
        """Get DeliveryStatus by code"""
        try:
            return DeliveryStatus._base_manager.get(code=code)
        except DeliveryStatus.DoesNotExist:
            return None
        
    @staticmethod
    def get_order_status_by_code(code: str) -> Optional[OrderStatus]:
        """Get OrderStatus by code"""
        try:
            return OrderStatus._base_manager.get(code=code)
        except OrderStatus.DoesNotExist:
            return None
        
    @staticmethod
    def update_package_arrival_by_drone_status(package: DeliveryOperationItem, is_arrived_by_drone: bool) -> None:
        """Update package arrival by drone status"""
        package.is_delivered_by_drone = is_arrived_by_drone
        if is_arrived_by_drone:
            package.drone_arrived_at = timezone.now()
            # update drone status to available
            if package.drone:
                package.drone.status = DeviceStatus._base_manager.get(code="available")
                package.drone.save()
        package.save()
        
    @staticmethod
    def update_package_arrival_all_status(package: DeliveryOperationItem, is_arrived_by_drone: bool, is_arrived: bool) -> None:
        """Update package arrival by drone status"""
        package.is_delivered_by_drone = is_arrived_by_drone
        package.is_arrived = is_arrived
        if is_arrived:
            package.arrived_at = timezone.now()
            
        if is_arrived_by_drone:
            package.drone_arrived_at = timezone.now()
        package.save()

    @staticmethod
    def update_package_arrival_status(package: DeliveryOperationItem, is_arrived: bool) -> None:
        """Update package arrival status"""
        package.is_arrived = is_arrived
        if is_arrived:
            package.arrived_at = timezone.now()
        package.save()

    @staticmethod
    def update_package_delivery_status(package: DeliveryOperationItem, is_delivered: bool) -> None:
        """Update package delivery status"""
        package.is_delivered = is_delivered
        if is_delivered:
            package.delivered_at = timezone.now()
        package.save()

    @staticmethod
    def update_delivery_operation_status(delivery_operation: DeliveryOperation, status: DeliveryStatus) -> None:
        """Update delivery operation status"""
        delivery_operation.current_status = status
        delivery_operation.save()

    @staticmethod
    def update_order_status(delivery_operation: DeliveryOperation, status: OrderStatus) -> None:
        """Update order status"""
        delivery_operation.order.status = status
        delivery_operation.order.save()

    @staticmethod
    def get_all_items_for_operation(delivery_operation: DeliveryOperation) -> QuerySet[DeliveryOperationItem]:
        """Get all items for a delivery operation"""
        return delivery_operation.items.all()

    @staticmethod
    def check_all_packages_arrived(delivery_operation: DeliveryOperation) -> bool:
        """Check if all packages in the operation have arrived"""
        return all(item.is_arrived for item in delivery_operation.items.all())

    @staticmethod
    def check_all_packages_delivered(delivery_operation: DeliveryOperation) -> bool:
        """Check if all packages in the operation have been delivered"""
        return all(item.is_delivered for item in delivery_operation.items.all())
    
    @staticmethod
    def check_all_packages_delivered_by_drone(delivery_operation: DeliveryOperation, drone: Device) -> bool:
        """Check if all packages in the operation have been delivered by drone"""
        all_delivery = DeliveryOperationItem._base_manager.filter(delivery_operation=delivery_operation)
        try:
            return all(item.is_delivered_by_drone for item in all_delivery)
        except Exception as e:
            return False
    
    @staticmethod
    def check_all_packages_delivered_in_operation(delivery_operation: DeliveryOperation) -> bool:
        """Check if ALL packages in the delivery operation have been delivered (across all drones)"""
        try:
            return all(item.is_delivered_by_drone for item in delivery_operation.items.all())
        except Exception as e:
            return False
    
    @staticmethod
    def check_if_only_one_package_is_not_delivered(delivery_operation: DeliveryOperation) -> bool:
        """Check if all packages in the operation have been delivered by drone"""
        delivered_packages_count = DeliveryOperationItem._base_manager.filter(delivery_operation=delivery_operation, is_delivered_by_drone=True).count()
        if delivered_packages_count == len(delivery_operation.items.all()) - 1:
            return True
        return False
    
    @staticmethod
    def add_arrived_order_delivery_history(delivery_operation: DeliveryOperation) -> None:
        """Add arrived order delivery history"""
        history = {
            "order": delivery_operation.order,
            "action": "arrived",
            "description": {
                "en": f"Order {delivery_operation.order.order_code} arrived to {delivery_operation.order.delivery_terminal.name}" if delivery_operation.order.delivery_terminal else f"Order {delivery_operation.order.order_code} arrived",
                "ko": f"주문 {delivery_operation.order.order_code} 이(가) {delivery_operation.order.delivery_terminal.name}에 도착했습니다" if delivery_operation.order.delivery_terminal else f"주문 {delivery_operation.order.order_code} 도착 완료"
            }
        }
        create_model_with_translations(OrderHistory, history)

    @staticmethod
    def add_delivered_order_delivery_history(delivery_operation: DeliveryOperation) -> None:
        """Add delivered order delivery history (with duplicate prevention)"""
        from orders.models import OrderHistory
        
        # Check if delivered history already exists for this order
        existing_history = OrderHistory._base_manager.filter(
            order=delivery_operation.order,
            action="delivered"
        ).exists()
        
        if existing_history:
            print(f"✅ [HISTORY] Delivered history already exists for order {delivery_operation.order.order_code}")
            return
            
        history = {
            "order": delivery_operation.order,
            "action": "delivered",
            "description": {
                "en": f"Order {delivery_operation.order.order_code} delivered to {delivery_operation.order.delivery_terminal.name}" if delivery_operation.order.delivery_terminal else f"Order {delivery_operation.order.order_code} delivered",
                "ko": f"주문 {delivery_operation.order.order_code} 이(가) {delivery_operation.order.delivery_terminal.name}에 배송되었습니다" if delivery_operation.order.delivery_terminal else f"주문 {delivery_operation.order.order_code} 배송 완료",
                "th": f"คำสั่งซื้อ {delivery_operation.order.order_code} ถูกจัดส่งไปยัง {delivery_operation.order.delivery_terminal.name}" if delivery_operation.order.delivery_terminal else f"คำสั่งซื้อ {delivery_operation.order.order_code} จัดส่งสำเร็จ"
            }
        }
        create_model_with_translations(OrderHistory, history)

    @staticmethod
    def add_arrived_package_delivery_history(package: DeliveryOperationItem) -> None:
        """Add arrived package delivery history"""
        history = {
            "order": package.delivery_operation.order,
            "action": "arrived",
            "description": {
                "en": f"Package {package.order_item.code} arrived to {package.delivery_operation.order.delivery_terminal.name}" if package.delivery_operation.order.delivery_terminal else f"Package {package.order_item.code} arrived",
                "ko": f"패키지 {package.order_item.code} 이(가) {package.delivery_operation.order.delivery_terminal.name}에 도착했습니다" if package.delivery_operation.order.delivery_terminal else f"패키지 {package.order_item.code} 도착 완료",
                "th": f"พัสดุ {package.order_item.code} ถูกจัดส่งไปยัง {package.delivery_operation.order.delivery_terminal.name}" if package.delivery_operation.order.delivery_terminal else f"พัสดุ {package.order_item.code} จัดส่งสำเร็จ"
            }
        }
        create_model_with_translations(OrderHistory, history)

    @staticmethod
    def add_delivered_package_delivery_history(package: DeliveryOperationItem) -> None:
        """Add delivered package delivery history"""
        history = {
            "order": package.delivery_operation.order,
            "action": "delivered",
            "description": {
                "en": f"Package {package.order_item.code} delivered to {package.delivery_operation.order.delivery_terminal.name}" if package.delivery_operation.order.delivery_terminal else f"Package {package.order_item.code} delivered",
                "ko": f"패키지 {package.order_item.code} 이(가) {package.delivery_operation.order.delivery_terminal.name}에 배송되었습니다" if package.delivery_operation.order.delivery_terminal else f"패키지 {package.order_item.code} 배송 완료",
                "th": f"พัสดุ {package.order_item.code} ถูกจัดส่งไปยัง {package.delivery_operation.order.delivery_terminal.name}" if package.delivery_operation.order.delivery_terminal else f"พัสดุ {package.order_item.code} จัดส่งสำเร็จ"
            }
        }
        create_model_with_translations(OrderHistory, history)

