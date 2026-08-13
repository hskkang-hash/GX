from delivery.repository.verification_repository import (
    VerificationRepository
)
from delivery.repository.cancelled_repository import (
    CancelledRepository
)
from orders.services.order_service import OrderService

class VerificationService:
    @staticmethod
    def get_unverified_operations():
        return VerificationRepository.get_unverified_operations()
    
    @staticmethod
    def get_verified_operations():
        return VerificationRepository.get_verified_operations()
    
    @staticmethod
    def verify_order(operation_id: int):
        order_operation = VerificationRepository.get_unverified_operation_by_id(operation_id)
        if order_operation:
            order_operation = VerificationRepository.verify_operation(order_operation)
            OrderService.create_order_history(order_operation.order.id, "", "verified")
            OrderService.update_order_status(order_operation.order.id, "awaiting_shipment")
            return order_operation
        return None

    @staticmethod
    def verify_orders(operation_ids: list):
        operations = VerificationRepository.get_operations_by_operation_ids(operation_ids)
        order_ids = list(operations.values_list('order_id', flat=True))
        if operations.exists():
            operations = VerificationRepository.verify_operations(operations)
            OrderService.create_orders_history(order_ids, "", "verified")
            OrderService.update_orders_status(order_ids, "awaiting_shipment")
            return operations
        return None
    
    @staticmethod
    def cancel_order_by_user(operation_id: int, reason_note: str):
        order_operation = VerificationRepository.get_unverified_operation_by_id(operation_id)
        if order_operation:
            order_operation = CancelledRepository.cancel_operation_order_by_user(order_operation, 
                                                                                 reason_note)
            OrderService.create_order_history(order_operation.order.id, "", "receipt_cancelled")
            return order_operation  
        return None
    
    @staticmethod
    def cancel_order_by_system(operation_id: int, reason_note: str):
        order_operation = VerificationRepository.get_unverified_operation_by_id(operation_id)
        if order_operation:
            order_operation = CancelledRepository.cancel_operation_order_by_system(order_operation, 
                                                                                   reason_note)
            return order_operation
        
    @staticmethod
    def cancel_order(operation_id: int, reason_note: str, is_system: bool = False):
        if is_system:
            return VerificationService.cancel_order_by_system(operation_id, reason_note)
        else:
            return VerificationService.cancel_order_by_user(operation_id, reason_note)
        
    
    @staticmethod
    def print_waybill(operation_id: int, template_id: int):
        # TODO: handle save waybill template
        return VerificationRepository.execute_processing_order(operation_id, template_id)

    # TODO: handle QR code waybill => status arrived package => status arrived order
    