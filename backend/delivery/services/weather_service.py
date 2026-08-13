import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from django.utils import timezone
import logging
import pytz

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service để lấy thông tin thời tiết từ Open-Meteo API
    """
    
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
    
    @staticmethod
    def get_weather_at_time(latitude: float, longitude: float, target_datetime: datetime) -> Optional[Dict]:
        """
        Lấy thông tin thời tiết tại tọa độ và thời điểm cụ thể
        
        Args:
            latitude: Vĩ độ
            longitude: Kinh độ  
            target_datetime: Thời điểm cần lấy thông tin thời tiết
            
        Returns:
            Dict chứa thông tin thời tiết hoặc None nếu lỗi
        """
        try:
            # Chuyển đổi thời gian về UTC nếu cần
            if timezone.is_aware(target_datetime):
                target_datetime_utc = target_datetime.astimezone(pytz.UTC)
            else:
                target_datetime_utc = timezone.make_aware(target_datetime, pytz.UTC)
            
            # Kiểm tra nếu là thời gian trong quá khứ (cần dùng historical API)
            now = timezone.now()
            
            if target_datetime_utc < now - timedelta(days=1):
                # Sử dụng Historical Weather API
                return WeatherService._get_historical_weather(latitude, longitude, target_datetime_utc)
            else:
                # Sử dụng Forecast API cho thời gian hiện tại hoặc tương lai
                return WeatherService._get_current_weather(latitude, longitude)
                
        except Exception as e:
            logger.error(f"Error getting weather data: {str(e)}")
            return None
    
    @staticmethod
    def _get_current_weather(latitude: float, longitude: float) -> Optional[Dict]:
        """
        Lấy thông tin thời tiết hiện tại từ Forecast API
        """
        try:
            url = WeatherService.FORECAST_URL
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'current_weather': 'true',
                'hourly': 'temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m',
                'timezone': 'auto'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            current_weather = data.get('current_weather', {})
            
            # Lấy thông tin chi tiết từ hourly data nếu có
            hourly_data = data.get('hourly', {})
            humidity = None
            precipitation = None
            
            if hourly_data and len(hourly_data.get('time', [])) > 0:
                # Lấy dữ liệu của giờ đầu tiên (hiện tại)
                humidity = hourly_data.get('relative_humidity_2m', [None])[0]
                precipitation = hourly_data.get('precipitation', [None])[0]
            
            weather_info = {
                'temperature': current_weather.get('temperature'),
                'wind_speed': current_weather.get('windspeed'),
                'wind_direction': current_weather.get('winddirection'),
                'weather_code': current_weather.get('weathercode'),
                'humidity': humidity,
                'precipitation': precipitation,
                'coordinates': f"{latitude}, {longitude}",
                'timestamp': current_weather.get('time'),
                'weather_description': {
                    'en': WeatherService._get_weather_description(current_weather.get('weathercode', 0), 'en'),
                    'ko': WeatherService._get_weather_description(current_weather.get('weathercode', 0), 'ko')
                }
            }
            
            return weather_info
            
        except Exception as e:
            logger.error(f"Error getting current weather: {str(e)}")
            return None
    
    @staticmethod
    def _get_historical_weather(latitude: float, longitude: float, target_datetime: datetime) -> Optional[Dict]:
        """
        Lấy thông tin thời tiết lịch sử từ Historical Weather API
        """
        try:
            # Format ngày cho API (YYYY-MM-DD)
            date_str = target_datetime.strftime('%Y-%m-%d')
            
            url = WeatherService.HISTORICAL_URL
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'start_date': date_str,
                'end_date': date_str,
                'hourly': 'temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m',
                'timezone': 'auto'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            hourly_data = data.get('hourly', {})
            
            if not hourly_data or not hourly_data.get('time'):
                return None
            
            # Tìm giờ gần nhất với target_datetime
            target_hour = target_datetime.hour
            time_list = hourly_data.get('time', [])
            
            # Tìm index của giờ gần nhất
            target_index = None
            for i, time_str in enumerate(time_list):
                if target_hour <= int(time_str.split('T')[1].split(':')[0]):
                    target_index = i
                    break
            
            if target_index is None:
                target_index = len(time_list) - 1  # Lấy giờ cuối cùng trong ngày
            
            weather_info = {
                'temperature': hourly_data.get('temperature_2m', [None])[target_index],
                'wind_speed': hourly_data.get('wind_speed_10m', [None])[target_index],
                'wind_direction': hourly_data.get('wind_direction_10m', [None])[target_index],
                'weather_code': hourly_data.get('weather_code', [None])[target_index],
                'humidity': hourly_data.get('relative_humidity_2m', [None])[target_index],
                'precipitation': hourly_data.get('precipitation', [None])[target_index],
                'coordinates': f"{latitude}, {longitude}",
                'timestamp': time_list[target_index] if target_index < len(time_list) else None,
                'weather_description': {
                    'en': WeatherService._get_weather_description(
                        hourly_data.get('weather_code', [0])[target_index] if target_index < len(hourly_data.get('weather_code', [])) else 0, 'en'
                    ),
                    'ko': WeatherService._get_weather_description(
                        hourly_data.get('weather_code', [0])[target_index] if target_index < len(hourly_data.get('weather_code', [])) else 0, 'ko'
                    )
                }
            }
            
            return weather_info
            
        except Exception as e:
            logger.error(f"Error getting historical weather: {str(e)}")
            return None
    
    @staticmethod
    def _get_weather_description(weather_code: int, language: str = 'en') -> str:
        """
        Chuyển đổi WMO weather code thành mô tả thời tiết
        
        Args:
            weather_code: WMO weather code
            language: Ngôn ngữ ('en' cho English, 'ko' cho Korean)
            
        Returns:
            Mô tả thời tiết theo ngôn ngữ được chọn
        """
        weather_descriptions = {
            0: {"en": "Clear sky", "ko": "맑음"},
            1: {"en": "Mainly clear", "ko": "대체로 맑음"},
            2: {"en": "Partly cloudy", "ko": "부분적으로 흐림"},
            3: {"en": "Overcast", "ko": "흐림"},
            45: {"en": "Fog", "ko": "안개"},
            48: {"en": "Depositing rime fog", "ko": "서리 안개"},
            51: {"en": "Light drizzle", "ko": "가벼운 이슬비"},
            53: {"en": "Moderate drizzle", "ko": "보통 이슬비"},
            55: {"en": "Dense drizzle", "ko": "짙은 이슬비"},
            56: {"en": "Light freezing drizzle", "ko": "가벼운 얼어붙는 이슬비"},
            57: {"en": "Dense freezing drizzle", "ko": "짙은 얼어붙는 이슬비"},
            61: {"en": "Slight rain", "ko": "약한 비"},
            63: {"en": "Moderate rain", "ko": "보통 비"},
            65: {"en": "Heavy rain", "ko": "폭우"},
            66: {"en": "Light freezing rain", "ko": "가벼운 얼어붙는 비"},
            67: {"en": "Heavy freezing rain", "ko": "심한 얼어붙는 비"},
            71: {"en": "Slight snow", "ko": "약한 눈"},
            73: {"en": "Moderate snow", "ko": "보통 눈"},
            75: {"en": "Heavy snow", "ko": "폭설"},
            77: {"en": "Snow grains", "ko": "눈알갱이"},
            80: {"en": "Slight rain shower", "ko": "약한 소나기"},
            81: {"en": "Moderate rain shower", "ko": "보통 소나기"},
            82: {"en": "Violent rain shower", "ko": "격렬한 소나기"},
            85: {"en": "Slight snow shower", "ko": "약한 눈보라"},
            86: {"en": "Heavy snow shower", "ko": "심한 눈보라"},
            95: {"en": "Thunderstorm", "ko": "뇌우"},
            96: {"en": "Thunderstorm with light hail", "ko": "가벼운 우박을 동반한 뇌우"},
            99: {"en": "Thunderstorm with heavy hail", "ko": "심한 우박을 동반한 뇌우"}
        }
        
        if weather_code in weather_descriptions:
            return weather_descriptions[weather_code].get(language, weather_descriptions[weather_code]['en'])
        
        # Fallback descriptions
        fallback = {
            'en': f"Unknown (code: {weather_code})",
            'ko': f"알 수 없음 (코드: {weather_code})"
        }
        return fallback.get(language, fallback['en'])
    
    @staticmethod
    def get_coordinates_from_delivery_operation(delivery_operation) -> Optional[Tuple[float, float]]:
        """
        Lấy tọa độ từ delivery operation thông qua route terminals
        
        Args:
            delivery_operation: Instance của DeliveryOperation
            
        Returns:
            Tuple (latitude, longitude) hoặc None nếu không tìm thấy
        """
        try:
            # Thử lấy từ route terminals
            if delivery_operation.route:
                # Lấy terminal đích (terminal cuối cùng trong route)
                route_terminals = delivery_operation.route.route_terminals.all().order_by('order')
                
                if route_terminals:
                    # Lấy terminal cuối cùng làm điểm đích
                    last_terminal = route_terminals.last().terminal
                    
                    if last_terminal and last_terminal.latitude and last_terminal.longitude:
                        try:
                            lat = float(last_terminal.latitude)
                            lon = float(last_terminal.longitude)
                            return (lat, lon)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid coordinates in terminal {last_terminal.id}")
            
            # Thử lấy từ terminal sequences nếu có
            terminal_sequences = getattr(delivery_operation, 'terminal_sequences', None)
            if terminal_sequences:
                last_sequence = terminal_sequences.all().order_by('sequence_order').last()
                if last_sequence:
                    try:
                        lat = float(last_sequence.coordinates_lat)
                        lon = float(last_sequence.coordinates_lon)
                        return (lat, lon)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid coordinates in terminal sequence {last_sequence.id}")
            
            logger.warning(f"No valid coordinates found for delivery operation {delivery_operation.id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting coordinates from delivery operation: {str(e)}")
            return None

    @staticmethod
    def format_weather_for_display(weather_data: Dict, language: str = 'en') -> Dict:
        """
        Format weather data để hiển thị trong print format
        
        Args:
            weather_data: Raw weather data từ API
            language: Ngôn ngữ ('en' hoặc 'ko')
            
        Returns:
            Dict với format phù hợp cho hiển thị theo ngôn ngữ
        """
        if not weather_data:
            no_data_msg = {
                'en': 'No weather data available',
                'ko': '기상 데이터가 없습니다'
            }
            return {
                'weather_conditions': no_data_msg.get(language, no_data_msg['en']),
                'temperature': 'N/A',
                'humidity': 'N/A', 
                'wind_speed': 'N/A',
                'weather_description': 'N/A'
            }
        
        # Format temperature
        temp = weather_data.get('temperature')
        temperature_str = f"{temp}°C" if temp is not None else "N/A"
        
        # Format humidity
        humidity = weather_data.get('humidity')
        humidity_str = f"{humidity}%" if humidity is not None else "N/A"
        
        # Format wind speed
        wind_speed = weather_data.get('wind_speed')
        wind_speed_str = f"{wind_speed} km/h" if wind_speed is not None else "N/A"
        
        # Get weather description in requested language
        weather_descriptions = weather_data.get('weather_description', {})
        if isinstance(weather_descriptions, dict):
            weather_desc = weather_descriptions.get(language, weather_descriptions.get('en', 'N/A'))
        else:
            weather_desc = weather_descriptions or 'N/A'
        
        # Format weather conditions with wind info
        wind_labels = {
            'en': 'Wind',
            'ko': '바람'
        }
        wind_label = wind_labels.get(language, 'Wind')
        wind_info = f"{wind_label}: {wind_speed_str}" if wind_speed is not None else ""
        
        weather_conditions = f"{weather_desc}"
        if wind_info:
            weather_conditions += f", {wind_info}"
        
        return {
            'weather_conditions': weather_conditions,
            'temperature': temperature_str,
            'humidity': humidity_str,
            'wind_speed': wind_speed_str,
            'weather_description': weather_desc,
            'coordinates': weather_data.get('coordinates', 'N/A'),
            'weather_description_multilang': weather_descriptions
        }
