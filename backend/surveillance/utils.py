from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

def get_location_from_latlng(latitude: float, longitude: float) -> dict:
    try:
        geolocator = Nominatim(user_agent="geo_lookup_app")  # required by Nominatim
        reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1)  # avoid throttling

        location = reverse((latitude, longitude), exactly_one=True)
        if not location:
            return {
                "full_address": "",
                "city": "",
            }
        return {
            "full_address": location.address,
            "city": location.raw.get("address", {}).get("city", ""),
        }
    except Exception as e:
        return {
            "full_address": "",
            "city": "",
        }