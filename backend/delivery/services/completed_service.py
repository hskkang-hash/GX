from delivery.repository.confirmation_repository import ConfirmationRepository
from delivery.repository.completed_repository import CompletedRepository

class CompletedService:
    @staticmethod
    def complete_order(operation_id: int):
        order_operation = CompletedRepository.get_completed_operation_by_id(operation_id)
        if order_operation:
            order_operation = CompletedRepository.execute_complete_operation(order_operation)
            # update order status to completed
            delivered_status = ConfirmationRepository.get_order_status_by_code("delivered")
            ConfirmationRepository.update_order_status(order_operation, delivered_status)
            ConfirmationRepository.add_delivered_order_delivery_history(order_operation)
            return order_operation
        return None
    
    @staticmethod
    def complete_orders(operation_ids: list):
        operations = CompletedRepository.get_completed_operations_by_ids(operation_ids)
        if operations.exists():
            CompletedRepository.execute_complete_operations(operations)
            # update order status to completed
            delivered_status = ConfirmationRepository.get_order_status_by_code("delivered")
            for operation in operations:
                ConfirmationRepository.update_order_status(operation, delivered_status)
                ConfirmationRepository.add_delivered_order_delivery_history(operation)
            return operations
        return None
    
    @staticmethod
    def arrived_order(operation_id: int):
        order_operation = CompletedRepository.get_arrived_operation_by_id(operation_id)
        if order_operation:
            order_operation = CompletedRepository.execute_arrived_operation(order_operation)
            return order_operation
        return None
    
    @staticmethod
    def get_arrived_operations():
        return CompletedRepository.get_arrived_operations()
    
    @staticmethod
    def get_completed_operations():
        return CompletedRepository.get_completed_operations()

    @staticmethod
    def download_report(operation_id: int, template_type="pdf"):
        """
        Download report for a completed operation.
        If report doesn't exist, create it first.
        
        Args:
            operation_id: ID of the delivery operation
            template_type: Type of report (pdf or docx)
            
        Returns:
            dict: Dictionary containing file URL and success status
        """
        return CompletedRepository.download_report(operation_id, template_type)