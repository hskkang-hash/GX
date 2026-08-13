"""API Views for devices management"""

from .device_views import DeviceAPI
from .protocol_views import ProtocolAPI
from .motor_type_views import MotorTypeAPI
from .battery_type_views import BatteryTypeAPI
from .imu_views import IMUAPI
from .image_stabilization_views import ImageStabilizationAPI 
from .gnss_system_views import GNSSSystemAPI
from .packaging_specification_views import PackagingSpecificationAPI
from .cameras_view import CameraAPI
from .library_views import LibraryAPI
__all__ = [
    'DeviceAPI',
    'ProtocolAPI', 
    'MotorTypeAPI',
    'BatteryTypeAPI',
    'IMUAPI',
    'ImageStabilizationAPI',
    'GNSSSystemAPI',
    'PackagingSpecificationAPI',
    'CameraAPI',
    'LibraryAPI'
]