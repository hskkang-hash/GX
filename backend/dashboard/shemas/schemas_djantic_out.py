from typing import List, Optional, Dict, Any
import re
from core.common.schema_utils import DynamicSchema
from core.configuration.models import AdminConfig
from core.middleware.refresh_token import get_current_request
from dashboard.models import Dashboard, DashboardPanel, WeatherSetting
import requests
from terminals.models import Routes, RouteTerminal
from django.db.models import F, Value, CharField, Prefetch
from django.db.models.functions import Concat, Coalesce

# Import annotation functions cho đa ngôn ngữ
from terminals.services.terminal_service import get_type_name_annotation, get_function_names_annotation

def get_weather_by_coordinates(latitude: float, longitude: float, country: str = None, city: str = None):
    """
    Get weather data using coordinates
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        meteo_response = requests.get(url)
        weather_data = meteo_response.json()
        
        if not country or not city:
            reverse_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
            location_response = requests.get(reverse_url, headers={'User-Agent': 'GuardianX/1.0'})
            location_data = location_response.json()
            country = country or location_data.get('address', {}).get('country', 'Unknown')
            city = city or location_data.get('address', {}).get('city', location_data.get('address', {}).get('town', 'Unknown'))
        
        return {
            'temperature': weather_data.get('current_weather', {}).get('temperature'),
            'wind_speed': weather_data.get('current_weather', {}).get('windspeed'),
            'country': country,
            'city': city,
            'coordinates': f"{latitude}, {longitude}",
        }
    except Exception:
        return None

class DashboardPanelOutSchema(DynamicSchema):
    class Meta:
        model = DashboardPanel
        exclude = []

    @classmethod
    def from_queryset(cls, obj):
        data = {
            'id': obj.id,
            'panel_title': obj.panel_title,
            'panel_type': obj.panel_type,
            'panel_config': obj.panel_config,
            'panel_data': obj.panel_data,
        }
        return data

class DashboardOutSchema(DynamicSchema):
    panels: Optional[List[DashboardPanelOutSchema]] = None
    
    class Meta:
        model = Dashboard
        exclude = []

    @classmethod
    def from_queryset_with_weather(cls, obj, request, user_latitude=None, user_longitude=None, location_source=None, location_accuracy=None, user_country=None, user_city=None, user_ip=None):
        base_data = super().from_queryset(obj)
        panels = [DashboardPanelOutSchema.from_queryset(panel) for panel in obj.panels.all()] 
        
        weather_data = {
            'temperature': "sunny",
            'wind_speed': "10",
            'country': "Vietnam",
            'city': "Hanoi",
            'coordinates': f"{10.8230}, {106.7780}",
        }
        
        if location_source == 'browser_geolocation' and user_latitude and user_longitude:
            if weather_data:
                weather_data['location_source'] = 'browser_geolocation'
                weather_data['location_accuracy'] = location_accuracy or 50
        
        elif location_source == 'ip_geolocation' and user_latitude and user_longitude:
            if weather_data:
                weather_data['location_source'] = 'ip_geolocation'
                weather_data['location_accuracy'] = location_accuracy or 50000
                weather_data['ip'] = user_ip
        
        else:
            weather_data = {
                'temperature': None,
                'wind_speed': None,
                'country': None,
                'city': None,
                'coordinates': None,
                'location_source': 'none',
                'location_accuracy': None,
            }
        
        data = {
            'id': base_data['id'],
            'name': base_data['name'],
            'code': base_data['code'],
            'layout_config': base_data['layout_config'],
            'created_on': base_data['created_on'],
            'data_updated_at': base_data['data_updated_at'],
            'panels': panels,
            'region': weather_data.get('country') if weather_data else None,
            'city': weather_data.get('city') if weather_data else None,
            'temperature': weather_data.get('temperature') if weather_data else None,
            'wind_speed': weather_data.get('wind_speed') if weather_data else None,
            'location_source': weather_data.get('location_source') if weather_data else 'none',
            'location_accuracy': weather_data.get('location_accuracy') if weather_data else None,
            'coordinates': weather_data.get('coordinates') if weather_data else None,
        }
        
        if weather_data and weather_data.get('ip'):
            data['ip'] = weather_data['ip']
        
        return data
    
class DashboardWithoutWeatherOutSchema(DynamicSchema):
    panels: Optional[List[DashboardPanelOutSchema]] = None
    
    class Meta:
        model = Dashboard
        exclude = []

    @classmethod
    def get_routes_with_terminals_data(cls):
        """
        Lấy dữ liệu routes với terminals - không có measurements, có đa ngôn ngữ
        Tối ưu với prefetch_related để tránh N+1 queries
        """
        # Tạo queryset cho route_terminals với annotations và select_related
        # Sử dụng Concat để build address ở database level
        route_terminals_queryset = RouteTerminal.objects.select_related('terminal').annotate(
            # Sử dụng 2 field annotate để lấy data đa ngôn ngữ
            terminal_type_names=get_type_name_annotation(),
            function_names=get_function_names_annotation(),
            # Build address ở database level để tối ưu
            address=Concat(
                Coalesce(F('terminal__city_province'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('terminal__city_county_district'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('terminal__ward_town_township'), Value(''), output_field=CharField()),
                Value(', '),
                Coalesce(F('terminal__street_address'), Value(''), output_field=CharField()),
                output_field=CharField()
            )
        ).order_by('order')
        
        # Prefetch route_terminals với queryset đã tối ưu
        route_terminals_prefetch = Prefetch(
            'route_terminals',
            queryset=route_terminals_queryset
        )
        
        # Lấy tất cả routes với prefetch_related để tránh N+1 queries
        # Chỉ lấy các fields cần thiết từ Routes model để tối ưu
        routes = Routes.objects.filter(
            deleted__isnull=True, is_active=True
        ).prefetch_related(
            route_terminals_prefetch
        ).only(
            'id', 'name', 'code', 'description', 'status', 'is_active', 
            'total_stops', 'note', 'two_way', 'created_on', 'modified_on'
        ).order_by('name')
        
        routes_data = []
        
        # Convert to list để tránh multiple queries khi iterate
        routes_list = list(routes)
        
        for route in routes_list:
            # Tối ưu: chỉ lấy các fields cần thiết từ route thay vì gọi from_queryset đầy đủ
            # Tránh load measurements và các fields không cần thiết
            data = {
                'id': route.id,
                'name': route.name,
                'code': route.code,
                'description': route.description,
                'status': route.status,
                'is_active': route.is_active,
                'total_stops': route.total_stops,
                'note': route.note,
                'two_way': route.two_way,
                'created_on': route.created_on.isoformat() if route.created_on else None,
                'modified_on': route.modified_on.isoformat() if route.modified_on else None,
            }
            
            # Lấy route terminals đã được prefetch (không cần query thêm)
            route_terminals = []
            for route_terminal in route.route_terminals.all():
                # Clean address: loại bỏ trailing commas, spaces và empty parts
                address = route_terminal.address if route_terminal.address else ""
                if address:
                    # Loại bỏ multiple consecutive commas và spaces, sau đó trim
                    address = re.sub(r',\s*,+', ',', address)  # Loại bỏ multiple commas
                    address = address.strip(', ').strip()  # Trim trailing commas và spaces
                
                route_terminals.append({
                    "terminal_id": route_terminal.terminal.id,
                    "name": route_terminal.terminal.name,
                    "terminal_type__name": route_terminal.terminal_type_names,  # Từ annotate đa ngôn ngữ
                    "function_names": route_terminal.function_names,  # Từ annotate đa ngôn ngữ
                    "address": address,
                    "latitude": route_terminal.terminal.latitude,
                    "longitude": route_terminal.terminal.longitude,
                    "note": route_terminal.terminal.note,
                    "stop": route_terminal.stop,
                    "order": route_terminal.order,
                    "for_robot": route_terminal.for_robot,
                    "command_line": route_terminal.command_line,
                    "frame": route_terminal.frame
                })
            
            # Cập nhật route data với route_terminals
            data['route_terminals'] = route_terminals
            routes_data.append(data)
        
        return routes_data

    @classmethod
    def from_queryset(cls, obj):
        base_data = super().from_queryset(obj)
        
        # Tối ưu: sử dụng prefetched panels nếu có, nếu không thì query một lần
        # Kiểm tra xem panels đã được prefetch chưa
        if hasattr(obj, '_prefetched_objects_cache') and 'panels' in obj._prefetched_objects_cache:
            panels_queryset = obj._prefetched_objects_cache['panels']
        else:
            # Nếu chưa prefetch, query một lần với select_related nếu cần
            panels_queryset = obj.panels.all()
        
        panels = [DashboardPanelOutSchema.from_queryset(panel) for panel in panels_queryset] 

        # Tối ưu: cache dashboard_refresh_interval query
        dashboard_refresh_interval = cls.get_dashboard_refresh_interval()
        
        # Tối ưu: chỉ query weather_setting nếu user tồn tại
        request = get_current_request()
        weather_setting_data = {
            'latitude': None,
            'longitude': None,
            'address': None,
        }
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Sử dụng select_related nếu có foreign key, và chỉ query một lần
            weather_setting = WeatherSetting.objects.filter(created_by=request.user).first()
            if weather_setting:
                weather_setting_data['latitude'] = weather_setting.latitude
                weather_setting_data['longitude'] = weather_setting.longitude
                weather_setting_data['address'] = weather_setting.address
        
        # Sử dụng method mới để lấy routes data với ORM tối ưu
        routes_data = cls.get_routes_with_terminals_data()
        
        data = {
            'id': base_data['id'],
            'name': base_data['name'],
            'code': base_data['code'],
            'layout_config': base_data['layout_config'],
            'created_on': base_data['created_on'],
            'data_updated_at': base_data['data_updated_at'],
            'panels': panels,
            'dashboard_refresh_interval': dashboard_refresh_interval,
            'weather_setting': weather_setting_data,
            'routes': routes_data,
        }
        
        return data

    @classmethod
    def get_dashboard_refresh_interval(cls):
        try:
            dashboard_refresh_interval = AdminConfig.objects.get(name='Dashboard', settings__dashboard_refresh_interval__isnull=False).settings['dashboard_refresh_interval']
        except:
            dashboard_refresh_interval = 300
        return dashboard_refresh_interval

