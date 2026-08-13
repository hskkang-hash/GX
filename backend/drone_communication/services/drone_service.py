from typing import List, Dict, Any, Optional
import logging
import os
import requests
from requests.exceptions import RequestException
from common.utils import get_gcs_api_headers
# from common.signalr.client import signalr_client
from devices.models import Device, DeviceStatus

logger = logging.getLogger(__name__)

class DroneComunicationService:
    @staticmethod
    def get_online_drones(page: int = 1, 
                          page_size: int = 10, 
                          search_field: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a paginated list of online drones from the SignalR hub.
        
        Args:
            page (int): Page number to retrieve (default: 1)
            page_size (int): Number of items per page (default: 10)
            search_field (Optional[str]): Search string for DRONE_UNIQUE_ID filtering
            
        Returns:
            Dict[str, Any]: Dictionary containing paginated drone data and metadata
        """
        try:
            # Get online drones from SignalR hub with pagination and search
            # online_drones = signalr_client.get_online_drones_from_api()
            # online_drones = DroneComunicationService.get_online_drones_from_api(
            #     page=page, 
            #     page_size=page_size, 
            #     search_field=search_field
            # )
            online_drones = DroneComunicationService.get_all_online_drones_not_in_device(
                page=page, 
                page_size=page_size, 
                search_field=search_field
            )
            
            return online_drones
                
        except Exception as e:
            logger.error(f"Error getting online drones: {str(e)}")
            return {
                "pagination":{
                    "total_items":0,
                    "total_pages":0,
                    "current_page":0,
                    "page_size":0,
                    "has_next_page":False,
                    "has_previous_page":False
                },
                "drones":[]
            }
    
    @staticmethod
    def get_online_drones_from_api(page: int = 1, page_size: int = 10, search_field: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a list of online drones from the REST API endpoint /api/db/drone/online with pagination and search support.
        
        Args:
            page (int): Page number to retrieve (default: 1)
            page_size (int): Number of items per page (default: 10)
            search_field (Optional[str]): Search string for DRONE_UNIQUE_ID filtering
            
        Returns:
            Dict[str, Any]: Dictionary containing paginated drone data and metadata
        """
        response_data = {
            "pagination":{
                "total_items":0,
                "total_pages":0,
                "current_page":0,
                "page_size":0,
                "has_next_page":False,
                "has_previous_page":False
            },
            "drones":[]
        }
        try:
            
            # Get the FlightBird URL from environment variable
            flightbird_url = os.environ.get('FLIGHTBRID_URL', 'http://localhost:5000/')
            
            # Ensure the URL ends with a slash
            if not flightbird_url.endswith('/'):
                flightbird_url += '/'
            
            # Create the full API endpoint URL with query parameters
            api_url = f"{flightbird_url}api/drone/db/online"
            
            # Prepare query parameters
            params = {
                'page': page,
                'pageSize': page_size
            }
            
            # Add search parameter if provided
            if search_field:
                params['searchField'] = search_field
            
            # Make the HTTP request with parameters
            headers = get_gcs_api_headers()
            response = requests.get(api_url, params=params, headers=headers, timeout=10)
            
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                result = response.json()
                    
                logger.info(f"Successfully retrieved drones from API with pagination")
                return result
            else:
                logger.warning(f"Failed to get online drones from API. Status code: {response.status_code}")
                return response_data
                
        except RequestException as e:
            logger.error(f"Network error while getting online drones from API: {str(e)}")
            return response_data
        except ValueError as e:
            logger.error(f"Invalid JSON response from drone API: {str(e)}")
            return response_data
        except Exception as e:
            logger.error(f"Unexpected error getting online drones from API: {str(e)}")
            return response_data
    
    @staticmethod
    def get_all_online_drones_not_in_device(page: int = 1, page_size: int = 10, search_field: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all online drones without pagination, filter out those whose UniqueId
        doesn't match any unit_id in the Device table, and then paginate the results.
        
        Args:
            page (int): Page number to retrieve (default: 1)
            page_size (int): Number of items per page (default: 10)
            search_field (Optional[str]): Search string for filtering drones by UniqueId
            
        Returns:
            Dict[str, Any]: Dictionary containing paginated drone data and metadata
        """
        # Default empty response
        response_data = {
            "pagination": {
                "total_items": 0,
                "total_pages": 0,
                "current_page": page,
                "page_size": page_size,
                "has_next_page": False,
                "has_previous_page": False
            },
            "drones": []
        }
        
        try:
            # Get the FlightBird URL from environment variable
            flightbird_url = os.environ.get('FLIGHTBRID_URL', 'http://localhost:5000/')
            
            # Ensure the URL ends with a slash
            if not flightbird_url.endswith('/'):
                flightbird_url += '/'
            
            # Create the full API endpoint URL
            api_url = f"{flightbird_url}api/drone/db/online"
            
            # Prepare query parameters to get all data without pagination
            params = {
                'getAllWithoutPagination': True
            }
            
            # Add search parameter if provided
            if search_field:
                params['searchField'] = search_field
                
            
            # Make the HTTP request with parameters
            headers = get_gcs_api_headers()
            response = requests.get(api_url, params=params, headers=headers, timeout=30)
            
            
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                result = response.json()
                
                # Get all drones from the response
                all_drones = result.get("drones", [])
                
                
                # Get all unit_ids from Device table
                device_unit_ids = set(Device._base_manager.filter(unit_id__isnull=False).values_list('unit_id', flat=True))
                
                # Filter drones that are not in the Device table
                unregistered_drones = [
                    drone for drone in all_drones 
                    if drone.get("UniqueId") and drone.get("UniqueId") not in device_unit_ids
                ]
                
                # Apply additional search filter if provided but not already handled by API
                if search_field and not params.get('searchField'):
                    search_field = search_field.lower()
                    unregistered_drones = [
                        drone for drone in unregistered_drones
                        if drone.get("UniqueId") and search_field in drone.get("UniqueId").lower()
                    ]
                
                # Total number of unregistered drones
                total_items = len(unregistered_drones)
                
                # Calculate total pages
                total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
                
                # Calculate start and end indices for pagination
                start_idx = (page - 1) * page_size
                end_idx = min(start_idx + page_size, total_items)
                
                # Get the drones for the current page
                paged_drones = unregistered_drones[start_idx:end_idx] if start_idx < total_items else []
                
                # Build the response
                response_data = {
                    "pagination": {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "page_size": page_size,
                        "has_next_page": page < total_pages,
                        "has_previous_page": page > 1
                    },
                    "drones": paged_drones
                }
                
                logger.info(f"Found {total_items} online drones not registered in Device table, returning page {page} of {total_pages}")
                return response_data
                
            else:
                logger.warning(f"Failed to get all online drones from API. Status code: {response.status_code}")
                return response_data
                
        except RequestException as e:
            logger.error(f"Network error while getting all online drones from API: {str(e)}")
            return response_data
        except ValueError as e:
            logger.error(f"Invalid JSON response from drone API: {str(e)}")
            return response_data
        except Exception as e:
            logger.error(f"Unexpected error getting all online drones: {str(e)}")
            return response_data
    
    @staticmethod
    def change_status(drone_uid: str, status: str, active: bool) -> Dict[str, Any]:
        """
        Change the status of a drone.
        """
        try:
            device = Device._base_manager.filter(unit_id=drone_uid).first()
            if not device:
                logger.error(f"Device with unit_id {drone_uid} not found")
                raise Exception(f"Device with unit_id {drone_uid} not found")
            device.active = active
            device.status = DeviceStatus._base_manager.filter(code=status).first()
            device.save()
            return {
                "success": True,
                "message": f"Status changed successfully for device {drone_uid}"
            }
        except Exception as e:
            logger.error(f"Error changing status: {str(e)}")
            return {
                "success": False,
                "message": f"Error changing status: {str(e)}"
            }