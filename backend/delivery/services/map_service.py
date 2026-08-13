import logging
from typing import Dict, List, Optional, Tuple
import math

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 400
DEFAULT_ZOOM = 12

class MapService:
    """
    Service để tạo static HTML map với Kakao Maps SDK cho delivery operations
    """
    
    
    @staticmethod
    def _calculate_optimal_center_and_zoom(markers: List[Dict]) -> Tuple[Dict[str, float], int]:
        """
        Tính toán center và zoom level tối ưu từ danh sách markers
        
        Args:
            markers: List các markers với lat, lng
            
        Returns:
            Tuple (center, zoom_level)
        """
        if not markers:
            return {'lat': 37.5665, 'lng': 126.978}, MapService.DEFAULT_ZOOM
        
        if len(markers) == 1:
            return {
                'lat': markers[0]['lat'],
                'lng': markers[0]['lng']
            }, 12
        
        # Calculate bounds
        lats = [marker['lat'] for marker in markers]
        lngs = [marker['lng'] for marker in markers]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        
        # Calculate center
        center_lat = (min_lat + max_lat) / 2
        center_lng = (min_lng + max_lng) / 2
        
        # Calculate zoom level based on bounds
        lat_diff = max_lat - min_lat
        lng_diff = max_lng - min_lng
        max_diff = max(lat_diff, lng_diff)
        
        # Zoom calculation (approximate)
        if max_diff > 1.0:
            zoom = 8
        elif max_diff > 0.5:
            zoom = 9
        elif max_diff > 0.1:
            zoom = 10
        elif max_diff > 0.05:
            zoom = 11
        elif max_diff > 0.01:
            zoom = 12
        else:
            zoom = 13
        
        return {'lat': center_lat, 'lng': center_lng}, zoom
    
    @staticmethod
    def _get_coordinates_from_delivery_operation(delivery_operation) -> List[Dict]:
        """
        Lấy coordinates từ delivery operation để tạo markers
        
        Args:
            delivery_operation: Instance của DeliveryOperation
            
        Returns:
            List các coordinates với thông tin marker
        """
        try:
            if not delivery_operation.route:
                logger.warning(f"No route found for delivery operation {delivery_operation.id}")
                return []
                
            route_terminals = delivery_operation.route.route_terminals.all().order_by('order')
            
            if not route_terminals:
                logger.warning(f"No route terminals found for delivery operation {delivery_operation.id}")
                return []
            
            coordinates = []
            
            for terminal in route_terminals:
                if terminal.terminal and terminal.terminal.latitude and terminal.terminal.longitude:
                    try:
                        lat = float(terminal.terminal.latitude)
                        lng = float(terminal.terminal.longitude)
                        
                        coordinate_data = {
                            'lat': lat,
                            'lng': lng,
                            'name': terminal.terminal.name or f'Terminal {terminal.order}',
                            'code': terminal.terminal.code or f'T{terminal.order}',
                            'for_robot': terminal.for_robot,
                            'order': terminal.order
                        }
                        coordinates.append(coordinate_data)
                        
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid coordinates for terminal {terminal.terminal.id}: {e}")
                        continue
            
            return coordinates
            
        except Exception as e:
            logger.error(f"Error getting coordinates from delivery operation {delivery_operation.id}: {str(e)}")
            return []
    
    @staticmethod
    def format_map_data_for_template(delivery_operation) -> Dict:
        """
        Format map data để sử dụng trong template
        
        Args:
            delivery_operation: Instance của DeliveryOperation
            
        Returns:
            Dict chứa map data formatted cho template
        """
        try:
            from .static_map_template import StaticMapTemplate
            
            # Generate static HTML map với Kakao SDK
            static_html_data = StaticMapTemplate.format_static_map_for_template(delivery_operation)
            
            if not static_html_data.get('map_delivery_html'):
                return {
                    'map_delivery': None,
                    'map_delivery_html': None,
                    'map_status': static_html_data.get('map_status', 'no_data'),
                    'map_message': static_html_data.get('map_message', 'No route data available')
                }
            
            # Lấy thông tin bổ sung về route
            route_info = MapService._get_route_info(delivery_operation)
            
            return {
                'map_delivery':  static_html_data.get('map_delivery_html'),  
                'map_status': static_html_data.get('map_status', 'success'),
                'map_message': static_html_data.get('map_message', 'Interactive map generated successfully'),
                'route_info': route_info,
                'markers_count': static_html_data.get('markers_count', 0),
                'center': static_html_data.get('center'),
                'zoom': static_html_data.get('zoom')
            }
            
        except Exception as e:
            logger.error(f"Error formatting map data for template: {str(e)}")
            return {
                'map_delivery': None,
                'map_delivery_html': None,
                'map_url': None,
                'map_status': 'error',
                'map_message': f'Error generating map: {str(e)}'
            }
    
    @staticmethod
    def _get_route_info(delivery_operation) -> Dict:
        """
        Lấy thông tin chi tiết về route
        """
        try:
            if not delivery_operation.route:
                return {}
            
            route = delivery_operation.route
            route_terminals = route.route_terminals.all().order_by('order')
            
            total_stops = route_terminals.count()
            robot_stops = route_terminals.filter(for_robot=True).count()
            drone_stops = total_stops - robot_stops
            
            return {
                'route_name': route.name,
                'route_code': route.code,
                'total_stops': total_stops,
                'robot_stops': robot_stops,
                'drone_stops': drone_stops,
                'route_description': route.description or '',
                'terminals': [
                    {
                        'name': terminal.terminal.name if terminal.terminal else f'Stop {terminal.order}',
                        'code': terminal.terminal.code if terminal.terminal else '',
                        'order': terminal.order,
                        'for_robot': terminal.for_robot,
                        'coordinates': f"{terminal.terminal.latitude},{terminal.terminal.longitude}" if terminal.terminal and terminal.terminal.latitude and terminal.terminal.longitude else 'N/A'
                    }
                    for terminal in route_terminals
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting route info: {str(e)}")
            return {}
