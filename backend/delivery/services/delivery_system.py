from delivery.repository.processing_repository import ProcessingRepository
from delivery.models import DeliveryOperation
from delivery.services.verification_service import VerificationService
from delivery.services.processing_service import ProcessingService
from delivery.services.returned_service import ReturnedService
from delivery.services.completed_service import CompletedService
from delivery.services.cancelled_service import CancelledService
from delivery.services.etri_service import EtriService

class DeliverySystem:
    """Logic for Verification
    - Get unverified operations
    - Get verified operations
    - Verify orders
    - Cancel order
    - Print waybill
    """
    @staticmethod
    def get_unverified_operations():
        return VerificationService.get_unverified_operations()
    
    @staticmethod
    def get_verified_operations():
        return VerificationService.get_verified_operations()
    
    @staticmethod
    def verify_orders(operation_ids: list):
        return VerificationService.verify_orders(operation_ids)
    
    @staticmethod
    def cancel_order(operation_id: int, 
                     reason_note: str, 
                     is_system: bool = False):
        return VerificationService.cancel_order(operation_id, 
                                                reason_note, 
                                                is_system)
    
    @staticmethod
    def print_waybill(operation_id: int, template_id: int):
        return VerificationService.print_waybill(operation_id, template_id)
    
    """Logic for Processing
    - Get list of routes
    - Get list of drones
    - Get items by processing
    - Get tab operation select route processing
    - Get tab operation select drone processing
    - Get tab operation in transit processing
    - Update route to operation
    - Update drone to operation item
    - Update status to operation
    - Update is arrived to operation item
    - Update is delivered by drone to operation item
    """
    @staticmethod
    def get_list_of_routes(operation: DeliveryOperation):
        return ProcessingService.get_list_of_routes(operation)
    
    @staticmethod
    def get_list_of_drones():
        return ProcessingService.get_list_of_drones()
    
    @staticmethod
    def get_items_by_processing(operation_id: int):
        return ProcessingService.get_items_by_processing(operation_id)
    
    @staticmethod
    def get_tab_operation_select_route_processing():
        return ProcessingService.get_data_tab_select_route_processing()
    
    @staticmethod
    def get_tab_operation_select_drone_processing():
        return ProcessingService.get_data_tab_select_drone_processing()
    
    @staticmethod
    def get_tab_operation_select_drone_processing_with_suitable_drones():
        return ProcessingService.get_data_tab_select_drone_processing_with_suitable_drones()
    
    @staticmethod
    def get_tab_operation_in_transit_processing():
        return ProcessingService.get_data_tab_in_transit_processing()
    
    @staticmethod
    def get_tab_operation_in_transit_processing_with_delivery_device():
        return ProcessingService.get_data_tab_in_transit_processing_with_delivery_device()
    
    @staticmethod
    def get_tab_operation_in_transit_processing_with_delivery_items():
        return ProcessingService.get_data_tab_in_transit_processing_with_delivery_items()
    
    @staticmethod
    def update_route_to_operation(operation_id: int, 
                                  route_id: int):
        return ProcessingService.update_route_to_operation(operation_id, 
                                                           route_id)
    
    @staticmethod
    def update_drone_to_operation_item(operation_item_id: int, 
                                       drone_id: int):
        return ProcessingService.update_drone_to_operation_item(operation_item_id, 
                                                                drone_id)
        
    @staticmethod
    def update_status_to_operation(operation_id: int, 
                                   status_code: str):
        return ProcessingService.update_status_to_operation(operation_id, 
                                                            status_code)
        
    @staticmethod
    def update_is_arrived_to_operation_item(operation_item_id: int, 
                                            is_arrived: bool):
        return ProcessingService.update_is_arrived_to_operation_item(operation_item_id, 
                                                                     is_arrived)
        
    @staticmethod
    def update_is_delivered_by_drone_to_operation_item(operation_item_id: int, 
                                                       is_delivered_by_drone: bool):
        return ProcessingService.update_is_delivered_by_drone_to_operation_item(operation_item_id, 
                                                                           is_delivered_by_drone)
    
    @staticmethod
    def get_delivery_items_with_suitable_drones_by_operation_id(operation_id: int):
        """Get delivery items with suitable drones for a specific operation"""
        from delivery.repository.processing_repository import ProcessingRepository
        # Use optimized method to reduce database queries
        return ProcessingRepository.get_delivery_items_with_suitable_drones_by_operation_id_optimized(operation_id)
    
    @staticmethod
    def get_delivery_items_with_suitable_drones_by_operation_item_id(operation_item_id: int, route_id: int = None):
        """Get suitable drones for a specific operation item"""
        from delivery.repository.processing_repository import ProcessingRepository
        return ProcessingRepository.get_delivery_items_with_suitable_drones_by_operation_item_id(operation_item_id, route_id)
    
    @staticmethod
    def get_drones_by_package_and_route_optimized(package_id: int, route_id: int):
        """Get suitable drones for a package and route with optimization."""
        try:
            print(f"🚁 [DeliverySystem] Getting drones for package {package_id}, route {route_id}")
            
            suitable_drones = ProcessingRepository.get_drones_by_operation_and_route_optimized(package_id, route_id)
            
            print(f"🚁 [DeliverySystem] Found {len(suitable_drones)} suitable drones")
            return suitable_drones
            
        except Exception as e:
            print(f"❌ [DeliverySystem] Error: {str(e)}")
            raise

    @staticmethod
    def get_lat_long_drone(unique_id: str):
        return ProcessingService.get_lat_long_drone(unique_id)
    
    """Logic for Returned
    - Get due for return operations
    - Get pending return operations
    - Get overdue operations
    - Get returned operations
    - Get processed return operations
    - Check arrived order timeout no pickup
    - Check pending order timeout no pickup
    - Execute pending order timeout no pickup
    - Execute returned order
    - Execute processed order
    """
    @staticmethod
    def get_due_for_return_operations():
        return ReturnedService.get_due_for_return_operations()
    
    @staticmethod
    def get_pending_return_operations():
        return ReturnedService.get_pending_return_operations()
    
    @staticmethod
    def get_overdue_operations():
        return ReturnedService.get_overdue_operations()
    
    @staticmethod
    def get_returned_operations():
        return ReturnedService.get_returned_operations()
    
    @staticmethod
    def get_processed_return_operations():
        return ReturnedService.get_processed_return_operations()
    
    @staticmethod
    def check_arrived_order_timeout_no_pickup(operation_id: int):
        return ReturnedService.check_arrived_order_timeout_no_pickup(operation_id)
    
    @staticmethod
    def check_pending_order_timeout_no_pickup(operation_id: int):
        return ReturnedService.check_pending_order_timeout_no_pickup(operation_id)
    
    @staticmethod
    def execute_pending_order_timeout_no_pickup(operation_ids: list, 
                                                terminal_id: int):
        return ReturnedService.execute_pending_order_timeout_no_pickup(operation_ids, 
                                                                       terminal_id)
    
    @staticmethod
    def execute_returned_order(operation_ids: list):
        return ReturnedService.execute_returned_order(operation_ids)
    
    @staticmethod
    def execute_processed_order(operation_ids: list):
        return ReturnedService.execute_processed_order(operation_ids)
    
    """Logic for Completed
    - Complete order
    - Complete orders
    - Arrived order
    - Get Arrived operations
    - Get Completed operations
    """
    @staticmethod
    def complete_order(operation_id: int):
        return CompletedService.complete_order(operation_id)
    
    @staticmethod
    def complete_orders(operation_ids: list):
        return CompletedService.complete_orders(operation_ids)
    
    @staticmethod
    def arrived_order(operation_id: int):
        return CompletedService.arrived_order(operation_id)
    
    @staticmethod
    def get_arrived_operations():
        return CompletedService.get_arrived_operations()
    
    @staticmethod
    def get_completed_operations():
        return CompletedService.get_completed_operations()
    
    
    """Logic for Cancelled
    - Get cancelled operations
    """
        
    @staticmethod
    def get_cancelled_operations():
        return CancelledService.get_cancelled_operations()
    
    @staticmethod
    def start_drone_delivery(operation_id: int):
        return ProcessingService.start_drone_delivery(operation_id)
    
    @staticmethod
    def update_delivery_status(drone_uid: str, lat: float, long: float):
        return ProcessingService.update_delivery_status(drone_uid, lat, long)

    
    @staticmethod
    def get_delivery_for_etri():
        return ProcessingService.get_delivery_for_etri()
    
    """Logic for ETRI Integration
    - Send delivery to ETRI system
    - Receive status from ETRI system
    """
    @staticmethod
    def send_delivery_to_etri(delivery_operation, request):
        return EtriService.send_delivery_to_etri(delivery_operation, request)
    
    @staticmethod
    def receive_status_from_etri(etri_data, request):
        return EtriService.receive_status_from_etri(etri_data, request)
    
    @staticmethod
    def download_report(operation_id: int):
        return CompletedService.download_report(operation_id)