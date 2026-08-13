import math

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách giữa hai điểm địa lý sử dụng công thức Haversine
    
    Args:
        lat1, lon1: Tọa độ điểm đầu (độ)
        lat2, lon2: Tọa độ điểm cuối (độ)
    
    Returns:
        float: Khoảng cách theo km
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0
    
    try:
        # Chuyển đổi từ độ sang radian
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        
        # Công thức Haversine
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Bán kính Trái Đất (km)
        r = 6371
        
        # Tính khoảng cách
        distance = c * r
        
        return round(distance, 2)
    except (ValueError, TypeError):
        return 0 