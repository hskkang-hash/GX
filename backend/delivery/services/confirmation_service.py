from delivery.services.processing_service import ProcessingService
from orders.services.order_service import OrderService
from delivery.repository.processing_repository import ProcessingRepository
from delivery.repository.confirmation_repository import ConfirmationRepository
from django.db import transaction
from typing import Dict, Any
from devices.models import DeviceStatus
from delivery.models import DeliveryOperationItem


class ConfirmationService:
    @staticmethod
    @transaction.atomic
    def confirm_order(package_id: int) -> Dict[str, Any]:
        """
        Confirm order by updating package status and checking delivery operation completion.
        
        Args:
            package_id: ID of the package to confirm
            
        Returns:
            Dict containing confirmation result and status information
        """
        # Get the package
        package = ConfirmationRepository.get_delivery_operation_item_by_id(package_id)
        if not package:
            return {
                "status": "error",
                "message": "Package not found"
            }

        delivery_operation = package.delivery_operation
        try:
            ProcessingService._complete_delivery_operation(delivery_operation, 
                                                           delivery_operation.items.filter(id=package_id), 
                                                           package.drone,
                                                           is_confirmed=True)
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
        return {
                "status": "success",
                "all_packages_arrived": True,
                "all_packages_delivered": True,
                "message": "All packages have been delivered (single package order completed)"
            }
        # Check current delivery operation status to determine what action to take
        # current_status_code = delivery_operation.current_status.code

        # # Check package delivery by drone status is False or None
        # if package.is_delivered_by_drone == False or package.is_delivered_by_drone is None:
        #     # update package delivery by drone status
        #     ConfirmationRepository.update_package_arrival_by_drone_status(package, True)
        #     # add delivery event
        #     order_assignment = ProcessingRepository.get_order_assignment_by_package(package)
        #     # Check if order assignment exists before accessing route_id
        #     if order_assignment and order_assignment.route_id:
        #         # get last terminal of route by order
        #         last_terminal = ProcessingRepository.get_last_terminal_of_route_by_order(order_assignment.route_id)
        #         ProcessingRepository.create_delivery_event(order_assignment, last_terminal, None, None)
        #     # add order history
        #     ConfirmationRepository.add_arrived_package_delivery_history(package)
        
        # # Case 1: Operation is not yet arrived - mark package as arrived
        # if current_status_code not in ["arrived_order", "completed_order"]:
        #     ConfirmationRepository.update_package_arrival_status(package, True)
        #     ConfirmationRepository.add_arrived_package_delivery_history(package)

        #     # Check if all packages in the operation have arrived
        #     if ConfirmationRepository.check_all_packages_arrived(delivery_operation):
        #         # Update delivery operation status to arrived
        #         arrived_status = ConfirmationRepository.get_delivery_status_by_code("arrived_order")
        #         if arrived_status:
        #             # Update drone status to available
        #             ConfirmationService._update_drone_status_to_available(package)
        #             ConfirmationRepository.update_delivery_operation_status(delivery_operation, arrived_status)
        #             ConfirmationRepository.add_arrived_order_delivery_history(delivery_operation)
                
        #         # For single package orders, mark as delivered immediately
        #         ConfirmationRepository.update_package_delivery_status(package, True)
                
        #         # Check if all packages have been delivered (should be true for single package)
        #         if ConfirmationRepository.check_all_packages_delivered(delivery_operation):
        #             # Update delivery operation status to completed
        #             completed_status = ConfirmationRepository.get_delivery_status_by_code("completed_order")
        #             delivered_status = ConfirmationRepository.get_order_status_by_code("delivered")
        #             if completed_status:
        #                 # Update drone status to available
        #                 ConfirmationService._update_drone_status_to_available(package)
        #                 ConfirmationRepository.update_delivery_operation_status(delivery_operation, completed_status)
        #                 ConfirmationRepository.update_order_status(delivery_operation, delivered_status)
        #                 ConfirmationRepository.add_delivered_order_delivery_history(delivery_operation)
        #                 # add order history
        #                 OrderService.create_order_history(delivery_operation.order.id, "", "delivered")

        #             return {
        #                 "status": "success",
        #                 "all_packages_arrived": True,
        #                 "all_packages_delivered": True,
        #                 "message": "All packages have been delivered (single package order completed)"
        #             }
        #         else:
        #             return {
        #                 "status": "success",
        #                 "all_packages_arrived": True,
        #                 "all_packages_delivered": False,
        #                 "message": "All packages have arrived"
        #             }
        #     else:
        #         return {
        #             "status": "success",
        #             "all_packages_arrived": False,
        #             "all_packages_delivered": False,
        #             "message": "Package marked as arrived, but not all packages have arrived yet"
        #         }
        
        # # Case 2: Operation has arrived but not completed - mark package as delivered by drone
        # elif current_status_code == "arrived_order":
        #     ConfirmationRepository.update_package_delivery_status(package, True)
        #     ConfirmationRepository.add_arrived_package_delivery_history(package)

        #     # Check if all packages in the operation have been delivered by drone
        #     if ConfirmationRepository.check_all_packages_delivered(delivery_operation):
        #         # Update delivery operation status to completed
        #         completed_status = ConfirmationRepository.get_delivery_status_by_code("completed_order")
        #         delivered_status = ConfirmationRepository.get_order_status_by_code("delivered")
        #         if completed_status:
        #             # Update drone status to available
        #             ConfirmationService._update_drone_status_to_available(package)
        #             ConfirmationRepository.update_delivery_operation_status(delivery_operation, completed_status)
        #             ConfirmationRepository.update_order_status(delivery_operation, delivered_status)
        #             ConfirmationRepository.add_delivered_order_delivery_history(delivery_operation)
        #             # add order history
        #             OrderService.create_order_history(delivery_operation.order.id, "", "delivered")

        #         return {
        #             "status": "success",
        #             "all_packages_arrived": True,
        #             "all_packages_delivered": True,
        #             "message": "All packages have been delivered"
        #         }
        #     else:
        #         return {
        #             "status": "success",
        #             "all_packages_arrived": True,
        #             "all_packages_delivered": False,
        #             "message": "Package marked as delivered, but not all packages have been delivered yet"
        #         }
        
        # # Case 3: Operation is already completed
        # else:
        #     return {
        #         "status": "success",
        #         "all_packages_arrived": True,
        #         "all_packages_delivered": True,
        #         "message": "All packages have already been delivered"
        #     }

    @staticmethod
    def _update_drone_status_to_available(package: DeliveryOperationItem) -> None:
        """Update drone status to available"""
        package.drone.status = DeviceStatus._base_manager.get(code="available")
        package.drone.save()