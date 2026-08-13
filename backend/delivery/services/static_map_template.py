from typing import Dict, List, Optional
import json
import logging
import os

logger = logging.getLogger(__name__)

class StaticMapTemplate:
    """
    Tạo static HTML template với Kakao Map SDK để hiển thị route động
    """
    
    @staticmethod
    def generate_static_map_html(
        markers: List[Dict],
        polyline_path: List[Dict],
        center: Dict[str, float],
        zoom: int = 12,
        width: int = 600,
        height: int = 400,
        kakao_api_key: str = None
    ) -> str:
        """
        Generate static HTML với Kakao Map SDK
        
        Args:
            markers: List các marker với lat, lng, name, for_robot
            polyline_path: List các điểm tạo polyline
            center: Center của map {lat, lng}
            zoom: Zoom level
            width: Width của map
            height: Height của map
            kakao_api_key: Kakao Map API key (optional)
            
        Returns:
            Static HTML string với embedded Kakao Map
        """
        
        # Get API key from settings if not provided
        if not kakao_api_key:
            try:
                from django.conf import settings
                kakao_api_key = os.environ.get('KAKAO_API_KEY')
            except:
                kakao_api_key = 'YOUR_KAKAO_API_KEY'
        
        # Convert Python data to JavaScript
        markers_js = json.dumps(markers, ensure_ascii=False)
        polyline_js = json.dumps(polyline_path, ensure_ascii=False)
        center_js = json.dumps(center, ensure_ascii=False)
        
        # W0-0: Kakao JS 키를 환경변수에서 읽는다 (§0.4 예외 승인 — 시크릿 제거만)
        _kakao_js_key = os.environ.get("KAKAO_JS_API_KEY", "")
        html_template = f"""

    <script
      type="text/javascript"
      src="//dapi.kakao.com/v2/maps/sdk.js?appkey={_kakao_js_key}&libraries=services,clusterer,drawing,geometry"
    ></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        
        .map-container {{
            position: relative;
            width: 100%;
            max-width: {width}px;
            height: {height}px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 0 auto;
            background: #f8f8f8;
        }}
        
        #map {{
            width: 100%;
            height: 100%;
            border-radius: 8px;
        }}
        
     
        @media (max-width: 768px) {{
            .map-container {{
                height: 300px;
                border-radius: 4px;
            }}
            
            .map-legend {{
                bottom: 8px;
                right: 8px;
                padding: 8px;
                font-size: 10px;
            }}
        }}
        
      
        
        .map-legend {{
            position: absolute;
            bottom: 16px;
            right: 16px;
            background: white;
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-size: 12px;
            z-index: 1000;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 4px;
        }}
        
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        
        .robot-marker {{ background-color: #4CAF50; }}
        .drone-marker {{ background-color: #F44336; }}
        .polyline-color {{ background-color: #2196F3; width: 20px; height: 3px; border-radius: 1px; }}
    </style>
    <div class="map-container">
        <!-- Map -->
        <div id="map"></div>
        
        <!-- Legend -->
        <div class="map-legend">
            <div class="legend-item">
                <div class="legend-color robot-marker"></div>
                <span>Robot Route</span>
            </div>
            <div class="legend-item">
                <div class="legend-color drone-marker"></div>
                <span>Drone Route</span>
            </div>
            <div class="legend-item">
                <div class="legend-color polyline-color"></div>
                <span>Route Path</span>
            </div>
        </div>
    </div>

    <script>
        function initializeMap() {{
            
            if (typeof kakao === 'undefined' || typeof kakao.maps === 'undefined' || typeof kakao.maps.LatLng === 'undefined') {{
                console.log('Kakao Maps SDK not ready, retrying...');
                setTimeout(initializeMap, 100);
                return;
            }}

            try {{
                const markers = {markers_js};
                const polylinePath = {polyline_js};
                const centerPoint = {center_js};
                const zoomLevel = {zoom};
                
                console.log('Initializing map with center:', centerPoint);
                
                const mapContainer = document.getElementById('map');
                const mapOption = {{
                    center: new kakao.maps.LatLng(centerPoint.lat, centerPoint.lng),
                    level: 15 - zoomLevel 
                }};
                
                const map = new kakao.maps.Map(mapContainer, mapOption);
                
                console.log('Map created successfully');
                
               
                markers.forEach((markerData, index) => {{
                    const position = new kakao.maps.LatLng(markerData.lat, markerData.lng);
                    
                    
                    const imageSrc = markerData.for_robot 
                        ? 'data:image/svg+xml;utf8,<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%234CAF50" opacity="0.85"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>'
                        : 'data:image/svg+xml;utf8,<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23fd0000" opacity="0.85"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>';
                    
                    const imageSize = new kakao.maps.Size(32, 32);
                    const imageOffset = new kakao.maps.Point(16, 28);
                    const markerImage = new kakao.maps.MarkerImage(imageSrc, imageSize, {{ offset: imageOffset }});
                    
                    const marker = new kakao.maps.Marker({{
                        position: position,
                        image: markerImage,
                        title: markerData.name || `Waypoint ${{index + 1}}`
                    }});
                    
                    marker.setMap(map);
                    
                
                    const infoWindow = new kakao.maps.InfoWindow({{
                        content: `<div style="padding:5px; font-size:12px; white-space:nowrap;">
                            <strong>${{markerData.name || `Waypoint ${{index + 1}}`}}</strong><br>
                            ${{markerData.for_robot ? 'Robot' : 'Drone'}} Route<br>
                            <small>${{markerData.lat.toFixed(6)}}, ${{markerData.lng.toFixed(6)}}</small>
                        </div>`
                    }});
                    
                    kakao.maps.event.addListener(marker, 'click', function() {{
                        infoWindow.open(map, marker);
                    }});
                }});
                
             
                if (polylinePath.length > 1) {{
                    const path = polylinePath.map(point => new kakao.maps.LatLng(point.lat, point.lng));
                    
                    const polyline = new kakao.maps.Polyline({{
                        path: path,
                        strokeWeight: 4,
                        strokeColor: '#E74C3C',
                        strokeOpacity: 0.7,
                        strokeStyle: 'solid'
                    }});
                    
                    polyline.setMap(map);
                }}
                
              
                if (markers.length > 1) {{
                    const bounds = new kakao.maps.LatLngBounds();
                    markers.forEach(marker => {{
                        bounds.extend(new kakao.maps.LatLng(marker.lat, marker.lng));
                    }});
                    map.setBounds(bounds);
                }}
                
                console.log('Map initialization completed successfully');
                
            }} catch (error) {{
                console.error('Error initializing map:', error);
                document.getElementById('map').innerHTML = 
                    '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #999; flex-direction: column;">' +
                    '<svg width="64" height="64" viewBox="0 0 24 24" fill="#ccc"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>' +
                    '<p>Map initialization failed</p>' +
                    '<small>Error: ' + error.message + '</small>' +
                    '</div>';
            }}
        }}
        

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initializeMap);
        }} else {{
            initializeMap();
        }}
    </script>

        """
        
        return html_template.strip()
    
    @staticmethod
    def format_static_map_for_template(delivery_operation) -> Dict:
        """
        Format static map HTML cho template
        """
        try:
            from .map_service import MapService
            
            # Get coordinates from delivery operation
            coordinates = MapService._get_coordinates_from_delivery_operation(delivery_operation)
            
            if not coordinates:
                return {
                    'map_delivery_html': None,
                    'map_status': 'no_data',
                    'map_message': 'No route data available'
                }
            
            markers = []
            polyline_path = []
            
            for coord in coordinates:
                marker_data = {
                    'lat': coord['lat'],
                    'lng': coord['lng'],
                    'name': coord.get('name', f"Waypoint {len(markers) + 1}"),
                    'for_robot': coord.get('for_robot', False)
                }
                markers.append(marker_data)
                polyline_path.append({'lat': coord['lat'], 'lng': coord['lng']})
            
            if not markers:
                return {
                    'map_delivery_html': None,
                    'map_status': 'no_markers',
                    'map_message': 'No valid markers found'
                }
            
            # Calculate center and zoom
            center, zoom = MapService._calculate_optimal_center_and_zoom(markers)
            
            # Generate static HTML
            static_html = StaticMapTemplate.generate_static_map_html(
                markers=markers,
                polyline_path=polyline_path,
                center=center,
                zoom=zoom,
                width=600,
                height=400
            )
            
            return {
                'map_delivery_html': static_html,
                'map_status': 'success',
                'map_message': 'Static map HTML generated successfully',
                'markers_count': len(markers),
                'center': center,
                'zoom': zoom
            }
            
        except Exception as e:
            logger.error(f"Error generating static map HTML: {str(e)}")
            return {
                'map_delivery_html': None,
                'map_status': 'error',
                'map_message': f'Error generating static map: {str(e)}'
            }
