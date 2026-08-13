"""
Centralized views module for devices app
All API controllers are imported from their respective modules
"""

# Import các API từ thư mục views mới
from devices.views import (
    DeviceAPI,
    ProtocolAPI,
    MotorTypeAPI,
    BatteryTypeAPI,
    IMUAPI, 
    ImageStabilizationAPI,
    GNSSSystemAPI,
    PackagingSpecificationAPI,
    CameraAPI
)

# Những API classes này giờ đã có sẵn để sử dụng trong hệ thống routing của Django Ninja