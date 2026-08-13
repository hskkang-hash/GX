from delivery.repository.cancelled_repository import CancelledRepository

class CancelledService:
    
    @staticmethod
    def get_cancelled_operations():
        return CancelledRepository.get_cancelled_operations()
    
    @staticmethod
    def cancel_order_by_user(operation_id: int, reason_note: str):
        order_operation = CancelledRepository.get_cancelled_operation_by_id(operation_id)
        if order_operation:
            order_operation = CancelledRepository.cancel_operation_order_by_user(order_operation, reason_note)
            return order_operation
        return None
    
    @staticmethod
    def cancel_order_by_system(operation_id: int):
        order_operation = CancelledRepository.get_cancelled_operation_by_id(operation_id)
        if order_operation:
            order_operation = CancelledRepository.cancel_operation_order_by_system(order_operation)
            return order_operation
        return None
    
    @staticmethod
    def cancel_order(operation_id: int, 
                     reason_note: str = None, 
                     is_system: bool = False):
        if is_system:
            return CancelledService.cancel_order_by_system(operation_id)
        else:
            if reason_note:
                return CancelledService.cancel_order_by_user(operation_id, reason_note)
            else:
                return None
    

    
    