from ninja_extra import api_controller, route
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from common.constant import MESSAGE_ENUM
from dashboard.services.dashboard_service import DashboardService
from dashboard.shemas.schemas_djantic_in import WeatherSettingCreateSchema
from core.role.permission import path_permission

@api_controller('/dashboard', tags=['Dashboard'])
class DashboardAPI:
    @route.get('/', url_name='get_dashboard', auth=CustomJWTAuth())
    @path_permission("read", path_override='/dashboard')
    def get_dashboard(self, request):
        user_latitude = request.GET.get('user_latitude')
        user_longitude = request.GET.get('user_longitude')
        location_source = request.GET.get('location_source', 'unknown')
        location_accuracy = request.GET.get('location_accuracy')
        user_country = request.GET.get('user_country')
        user_city = request.GET.get('user_city')
        user_ip = request.GET.get('user_ip')    
        
        if user_latitude:
            try:
                user_latitude = float(user_latitude)
            except (ValueError, TypeError):
                user_latitude = None
                
        if user_longitude:
            try:
                user_longitude = float(user_longitude)
            except (ValueError, TypeError):
                user_longitude = None

        dashboard = DashboardService.get_dashboard_by_code(
            'delivery_dashboard',
            request=request,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            location_source=location_source,
            location_accuracy=location_accuracy,
            user_country=user_country,
            user_city=user_city,
            user_ip=user_ip
        )
        return BaseResponse(
            status_code=200, 
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DASHBOARD_DATA_SUCCESS), 
            data=dashboard,
        )
    
    @route.post('/refresh', url_name='refresh_dashboard', auth=CustomJWTAuth())
    @path_permission("update", path_override='/dashboard')
    def refresh_dashboard(self, request):
        user_latitude = request.GET.get('user_latitude')
        user_longitude = request.GET.get('user_longitude')
        location_source = request.GET.get('location_source', 'unknown')
        location_accuracy = request.GET.get('location_accuracy')
        user_country = request.GET.get('user_country')
        user_city = request.GET.get('user_city')
        user_ip = request.GET.get('user_ip')
        
        if user_latitude:
            try:
                user_latitude = float(user_latitude)
            except (ValueError, TypeError):
                user_latitude = None
                
        if user_longitude:
            try:
                user_longitude = float(user_longitude)
            except (ValueError, TypeError):
                user_longitude = None

        dashboard = DashboardService.refresh_delivery_dashboard_data(
            request=request,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            location_source=location_source,
            location_accuracy=location_accuracy,
            user_country=user_country,
            user_city=user_city,
            user_ip=user_ip
        )
        return BaseResponse(
            status_code=200, 
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.REFRESH_DASHBOARD_DATA_SUCCESS), 
            data=dashboard,
        )
    
    @route.post('/refresh-default', url_name='refresh_dashboard_default', auth=CustomJWTAuth())
    @path_permission("update", path_override='/dashboard')
    def refresh_dashboard_default(self, request):
        dashboard = DashboardService.refresh_delivery_dashboard_data_default(request=request)
        return BaseResponse(
            status_code=200, 
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.REFRESH_DASHBOARD_DATA_SUCCESS), 
            data=dashboard,
        )

    @route.get('/anyang', url_name='get_anyang_dashboard', auth=CustomJWTAuth())
    @path_permission("read", path_override='/dashboard')
    def get_anyang_dashboard(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        dashboard = DashboardService.get_anyang_dashboard(
            start_date=start_date,
            end_date=end_date
        )
        return BaseResponse(
            status_code=200, 
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DASHBOARD_DATA_SUCCESS), 
            data=dashboard,
        )
    
    @route.post('/weather-setting', url_name='create_weather_setting', auth=CustomJWTAuth())
    @path_permission("create", path_override='/dashboard')
    def create_weather_setting(self, request, data: WeatherSettingCreateSchema):
        weather_setting = DashboardService.create_weather_setting(data.latitude, data.longitude, data.address, is_surveillance_dashboard=data.is_surveillance_dashboard)
        weather_setting_data = {
            'id': weather_setting.id,
            'latitude': weather_setting.latitude,
            'longitude': weather_setting.longitude,
            'address': weather_setting.address,
            'is_surveillance_dashboard': weather_setting.is_surveillance_dashboard,
        }
        return BaseResponse(
            status_code=200, 
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_WEATHER_SETTING_SUCCESS), 
            data=weather_setting_data,
        )

    @route.get('/devices-location', url_name='get_devices_location', auth=CustomJWTAuth())
    @path_permission("read", path_override='/dashboard')
    def get_devices_location(self, request):
        devices_location = DashboardService.get_devices_location()
        return BaseResponse(
            status_code=200, 
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DASHBOARD_DATA_SUCCESS), 
            data=devices_location,
        )
    
    @route.get('/check-health/{drone_id}', url_name='check_drone_health', auth=CustomJWTAuth())
    @path_permission("read", path_override='/dashboard')
    def check_drone_health(self, request, drone_id: int):
        """
        Check drone health by calling Flightbird API.
        
        Args:
            drone_id: The ID of the drone device
            
        Returns:
            BaseResponse with health sensor data from Flightbird API
        """
        result = DashboardService.check_drone_health(drone_id)
        
        if result.get('success'):
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DRONE_HEALTH_SUCCESS),
                data=result.get('data'),
            )
        else:
            return BaseResponse(
                status_code=400,
                message=result.get('error', 'Failed to check drone health'),
                success=False,
            )
    