from orders.services.order_service import OrderService
from delivery.repository.returned_repository import ReturnedRepository
from delivery.constants import (
    ARRIVED_ORDER_TIMEOUT_NO_PICKUP_DEFAULT,
    PENDING_ORDER_TIMEOUT_NO_PICKUP_DEFAULT
)
from django.utils import timezone
from datetime import timedelta
from core.configuration.models import AdminConfig

class ReturnedService:
    @staticmethod
    def get_due_for_return_operations():
        return ReturnedRepository.get_due_for_return_operations()
    
    @staticmethod
    def get_pending_return_operations():
        return ReturnedRepository.get_pending_return_operations()
    
    @staticmethod
    def get_overdue_operations():
        return ReturnedRepository.get_overdue_operations()
    
    @staticmethod
    def get_returned_operations():
        return ReturnedRepository.get_returned_operations()
    
    @staticmethod
    def get_processed_return_operations():
        return ReturnedRepository.get_processed_return_operations()
    
    @staticmethod
    def get_arrived_order_timeout_no_pickup() -> int:
        try:
            config = AdminConfig.objects.get(name='Operation').settings 
            order_timeout = config.get('order_arrived_timeout_no_pickup', ARRIVED_ORDER_TIMEOUT_NO_PICKUP_DEFAULT)
            return order_timeout
        except AdminConfig.DoesNotExist:
            return ARRIVED_ORDER_TIMEOUT_NO_PICKUP_DEFAULT
    
    @staticmethod
    def get_pending_order_timeout_no_pickup() -> int:
        try:
            config = AdminConfig.objects.get(name='Operation').settings 
            order_timeout = config.get('order_pending_timeout_no_pickup', PENDING_ORDER_TIMEOUT_NO_PICKUP_DEFAULT)
            return order_timeout
        except AdminConfig.DoesNotExist:
            return PENDING_ORDER_TIMEOUT_NO_PICKUP_DEFAULT
        
    @staticmethod
    def check_arrived_order_timeout_no_pickup(operation_id: int):
        # system auto check order timeout no pickup
        order_timeout = ReturnedService.get_arrived_order_timeout_no_pickup()
        if order_timeout:
            operation = ReturnedRepository.get_operation_by_id(operation_id)
            if operation.current_status.code == "arrived_order":
                latest_history = operation.status_history.first()
                if latest_history:
                    changed_time = latest_history.changed_at
                    now = timezone.now()
                    if now - changed_time > timedelta(days=order_timeout):
                        ReturnedRepository.execute_order_due_for_return(operation.id)
                        OrderService.create_order_history(operation.order.id, "", "returned")
                        return True
        return False
    
    @staticmethod
    def check_pending_order_timeout_no_pickup(operation_id: int):
        # system auto check order timeout no pickup
        order_timeout = ReturnedService.get_pending_order_timeout_no_pickup()
        if order_timeout:
            operation = ReturnedRepository.get_operation_by_id(operation_id)
            if operation.current_status.code == "order_pending_returned":
                latest_history = operation.status_history.first()
                if latest_history:
                    changed_time = latest_history.changed_at
                    now = timezone.now()
                    if now - changed_time > timedelta(days=order_timeout):
                        ReturnedRepository.execute_overdue_order(operation.id)
                        return True
        return False
    
    @staticmethod
    def execute_pending_order_timeout_no_pickup(operation_ids: list, terminal_id: int):
        ReturnedRepository.execute_multi_order_pending_return(operation_ids, terminal_id)
        
    @staticmethod
    def execute_returned_order(operation_ids: list):
        ReturnedRepository.execute_multi_returned_order(operation_ids)
    
    @staticmethod
    def execute_processed_order(operation_ids: list):
        ReturnedRepository.execute_multi_processed_order(operation_ids)
