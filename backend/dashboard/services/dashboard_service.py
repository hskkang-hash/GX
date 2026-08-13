from dashboard.repository.dashboard_repository import DashboardRepository
from dashboard.shemas.schemas_djantic_out import DashboardOutSchema
from devices.models import Device
from common.utils import get_gcs_api_headers
import os
import requests
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    @staticmethod
    def get_dashboard_by_code(dashboard_code: str, request=None, user_latitude=None, user_longitude=None, location_source=None, location_accuracy=None, user_country=None, user_city=None, user_ip=None):
        dashboard = DashboardRepository.refresh_delivery_dashboard_data(
            request=request,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            location_source=location_source,
            location_accuracy=location_accuracy,
            user_country=user_country,
            user_city=user_city,
            user_ip=user_ip
        )

        return dashboard
    
    @staticmethod
    def get_anyang_dashboard(start_date=None, end_date=None):
        dashboard = DashboardRepository.refresh_anyang_dashboard_data(
            start_date=start_date,
            end_date=end_date
        )

        return dashboard
    
    @staticmethod
    def get_dashboard_by_id(dashboard_id: int, request=None, user_latitude=None, user_longitude=None, location_source=None, location_accuracy=None, user_country=None, user_city=None, user_ip=None):
        dashboard = DashboardRepository.get_dashboard_by_id(dashboard_id)
        # Format it using from_queryset
        dashboard = DashboardOutSchema.from_queryset_with_weather(
            dashboard,
            request=request,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            location_source=location_source,
            location_accuracy=location_accuracy,
            user_country=user_country,
            user_city=user_city,
            user_ip=user_ip
        )
        return dashboard
    
    @staticmethod
    def refresh_delivery_dashboard_data(request=None, user_latitude=None, user_longitude=None, location_source=None, location_accuracy=None, user_country=None, user_city=None, user_ip=None):
        return DashboardRepository.refresh_delivery_dashboard_data(
            request=request,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            location_source=location_source,
            location_accuracy=location_accuracy,
            user_country=user_country,
            user_city=user_city,
            user_ip=user_ip
        )
    
    @staticmethod
    def refresh_delivery_dashboard_data_default(request=None, user_latitude=None, user_longitude=None, location_source=None, location_accuracy=None, user_country=None, user_city=None, user_ip=None):
        return DashboardRepository.refresh_delivery_dashboard_data_default(
            request=request,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            location_source=location_source,
            location_accuracy=location_accuracy,
            user_country=user_country,
            user_city=user_city,
            user_ip=user_ip
        )
    
    @staticmethod
    def create_weather_setting(latitude, longitude, address, is_surveillance_dashboard=False):
        return DashboardRepository.create_weather_setting(latitude, longitude, address, is_surveillance_dashboard)

    @staticmethod
    def get_devices_location():
        return DashboardRepository.get_devices_location()
    
    @staticmethod
    def check_drone_health(drone_id: int):
        """
        Check drone health by calling Flightbird API.
        
        Args:
            drone_id: The ID of the drone device
            
        Returns:
            Dictionary containing health sensor data from Flightbird API
        """
        try:
            # Get the device by ID
            device = Device.objects.get(id=drone_id)
            
            # Check if device has unit_id
            if not device.unit_id:
                return {
                    'error': 'Device does not have unit_id',
                    'success': False
                }
            
            # Get Flightbird URL from environment
            flightbird_url = os.getenv('FLIGHTBRID_URL')
            if not flightbird_url:
                logger.error("FLIGHTBRID_URL not configured")
                return {
                    'error': 'FLIGHTBRID_URL not configured',
                    'success': False
                }
            
            # Ensure URL ends with slash
            if not flightbird_url.endswith('/'):
                flightbird_url += '/'
            
            # Call Flightbird API
            api_url = f"{flightbird_url}api/drone/health/hover-sensors/{device.unit_id}"
            
            headers = get_gcs_api_headers()
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                logger.warning(f"Failed to get drone health from Flightbird. Status code: {response.status_code}")
                return {
                    'success': False,
                    'error': f'Flightbird API returned status code {response.status_code}',
                    'status_code': response.status_code
                }
                
        except Device.DoesNotExist:
            logger.error(f"Device with id {drone_id} not found")
            return {
                'success': False,
                'error': f'Device with id {drone_id} not found'
            }
        except requests.exceptions.Timeout:
            logger.error("Request timeout to Flightbird API")
            return {
                'success': False,
                'error': 'Request timeout to Flightbird API'
            }
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Flightbird API")
            return {
                'success': False,
                'error': 'Cannot connect to Flightbird API'
            }
        except Exception as e:
            logger.error(f"Unexpected error checking drone health: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }