from typing import Optional
from ninja import Schema

class WeatherSettingCreateSchema(Schema):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    is_surveillance_dashboard: Optional[bool] = False