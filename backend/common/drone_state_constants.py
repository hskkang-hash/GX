from enum import Enum
from typing import Dict, Any
from django.utils.translation import gettext_lazy as _

class DroneSystemStatus(str, Enum):
    """Các trạng thái hệ thống của drone"""
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    NORMAL = "NORMAL"

class DroneFlightMode(str, Enum):
    """Các chế độ bay của drone"""
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    RTH = "RTH"  # Return to Home

class DroneState(str, Enum):
    """Các trạng thái hoạt động của drone"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class DroneStatusCode(str, Enum):
    """Mã trạng thái của drone trong database"""
    AVAILABLE = "available"
    ON_MISSION = "on_mission"
    OPERATIONAL = "operational"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"
    RETIRED = "retired"

# Messages for drone states
DRONE_STATE_MESSAGES = {
    DroneStatusCode.AVAILABLE: {
        "en": _("Drone is available for missions"),
        "ko": _("드론이 임무 수행 가능합니다"),
        "vi": _("Drone sẵn sàng nhận nhiệm vụ")
    },
    DroneStatusCode.ON_MISSION: {
        "en": _("Drone is currently on a mission"),
        "ko": _("드론이 현재 임무 수행 중입니다"),
        "vi": _("Drone đang thực hiện nhiệm vụ")
    },
    DroneStatusCode.OPERATIONAL: {
        "en": _("Drone is operational but not ready for missions"),
        "ko": _("드론이 작동 중이지만 임무 수행 준비가 되지 않았습니다"),
        "vi": _("Drone đang hoạt động nhưng chưa sẵn sàng nhận nhiệm vụ")
    },
    DroneStatusCode.MAINTENANCE: {
        "en": _("Drone requires maintenance"),
        "ko": _("드론 정비가 필요합니다"),
        "vi": _("Drone cần bảo trì")
    },
    DroneStatusCode.INACTIVE: {
        "en": _("Drone is inactive"),
        "ko": _("드론이 비활성 상태입니다"),
        "vi": _("Drone không hoạt động")
    },
    DroneStatusCode.RETIRED: {
        "en": _("Drone has been retired"),
        "ko": _("드론이 퇴역했습니다"),
        "vi": _("Drone đã ngừng sử dụng")
    }
}

# Các ngưỡng và điều kiện để xác định trạng thái drone
DRONE_STATE_THRESHOLDS: Dict[str, Any] = {
    # Thời gian
    "INACTIVE_TIMEOUT_MINUTES": 10,  # Thời gian không hoạt động để xem là inactive (minutes)
    "ANALYSIS_WINDOW_HOURS": 1,     # Cửa sổ thời gian phân tích log
    
    # Pin và Năng lượng
    "LOW_BATTERY_THRESHOLD": 20.0,      # Ngưỡng pin thấp (%)
    "CRITICAL_BATTERY_THRESHOLD": 10.0,  # Ngưỡng pin nguy hiểm (%)
    
    # Cảm biến và Độ rung
    "MAX_VIBRATION_THRESHOLD": 30.0,     # Ngưỡng độ rung tối đa
    "IMU_ANOMALY_THRESHOLD": 1000,       # Ngưỡng bất thường của cảm biến IMU
    
    # Điều kiện nghỉ hưu
    "MAX_FLIGHT_HOURS": 500,                    # Số giờ bay tối đa trước khi nghỉ hưu
    "HIGH_ERROR_COUNT_PER_DAY": 5,             # Số lỗi tối đa mỗi ngày
    "HIGH_ERROR_DAYS_FOR_RETIREMENT": 7,        # Số ngày có nhiều lỗi để xem xét nghỉ hưu
    "ERROR_ANALYSIS_WINDOW_DAYS": 30,           # Số ngày phân tích lỗi
    
    # Điều kiện bảo trì
    "MAINTENANCE_CHECK_WINDOW_HOURS": 24,       # Cửa sổ thời gian kiểm tra bảo trì
    "MAX_CONSECUTIVE_ERRORS": 3,                # Số lỗi liên tiếp tối đa
    "HIGH_TEMP_THRESHOLD": 60,                  # Nhiệt độ cao bất thường (°C)
    
    # Điều kiện sẵn sàng
    "MIN_BATTERY_FOR_MISSION": 30.0,           # Pin tối thiểu để thực hiện nhiệm vụ (%)
    "MAX_WIND_SPEED": 15.0,                    # Tốc độ gió tối đa cho phép (m/s)
    "MIN_GPS_SATELLITES": 0,                   # Số vệ tinh GPS tối thiểu
    "MIN_GPS_ACCURACY": 2.0,                   # Độ chính xác GPS tối thiểu (m)
}

# Các trường dữ liệu cần kiểm tra trong log
REQUIRED_LOG_FIELDS = {
    "BASIC": [
        "timestamp",
        "uniqueId",
        "msgType",
        "sysId",
        "compId"
    ],
    "SENSORS": [
        "vibrationX",
        "vibrationY",
        "vibrationZ",
        "xacc",
        "yacc",
        "zacc",
        "temperature"
    ],
    "POSITION": [
        "latitude",
        "longitude",
        "altitude",
        "relativeAltitude",
        "heading",
        "groundSpeed",
        "airSpeed",
        "climbRate"
    ],
    "IMU": [
        "xgyro",
        "ygyro",
        "zgyro",
        "xmag",
        "ymag",
        "zmag"
    ],
    "STATE": [
        "batteryLevel",
        "systemStatus",
        "droneState",
        "flightMode",
        "currentMissionId",
        "gpsSatellites",
        "gpsAccuracy",
        "windSpeed"
    ]
}

# Các điều kiện để xác định trạng thái
STATE_CONDITIONS = {
    DroneStatusCode.RETIRED: {
        "description": _("Điều kiện để drone nghỉ hưu"),
        "conditions": [
            _("Tổng số giờ bay vượt quá MAX_FLIGHT_HOURS"),
            _("Số ngày có lỗi nhiều vượt quá HIGH_ERROR_DAYS_FOR_RETIREMENT")
        ]
    },
    DroneStatusCode.MAINTENANCE: {
        "description": _("Điều kiện cần bảo trì"),
        "conditions": [
            _("Pin dưới LOW_BATTERY_THRESHOLD"),
            _("Độ rung vượt MAX_VIBRATION_THRESHOLD"),
            _("Trạng thái hệ thống là ERROR hoặc CRITICAL"),
            _("IMU bất thường vượt IMU_ANOMALY_THRESHOLD"),
            _("Nhiệt độ vượt HIGH_TEMP_THRESHOLD"),
            _("Số lỗi liên tiếp vượt MAX_CONSECUTIVE_ERRORS")
        ]
    },
    DroneStatusCode.INACTIVE: {
        "description": _("Điều kiện không hoạt động"),
        "conditions": [
            _("Không có log trong INACTIVE_TIMEOUT_MINUTES phút"),
            _("Không có tín hiệu GPS"),
            _("Pin dưới CRITICAL_BATTERY_THRESHOLD")
        ]
    },
    DroneStatusCode.ON_MISSION: {
        "description": _("Điều kiện đang trong nhiệm vụ"),
        "conditions": [
            _("Có CurrentMissionId"),
            _("DroneState là ACTIVE hoặc FlightMode là AUTO")
        ]
    },
    DroneStatusCode.AVAILABLE: {
        "description": _("Điều kiện sẵn sàng nhận nhiệm vụ"),
        "conditions": [
            _("Pin trên MIN_BATTERY_FOR_MISSION"),
            _("Không có nhiệm vụ hiện tại"),
            _("Hệ thống không có lỗi"),
            _("Số vệ tinh GPS đủ MIN_GPS_SATELLITES"),
            _("Độ chính xác GPS tốt hơn MIN_GPS_ACCURACY"),
            _("Tốc độ gió dưới MAX_WIND_SPEED")
        ]
    },
    DroneStatusCode.OPERATIONAL: {
        "description": _("Trạng thái mặc định khi hoạt động bình thường"),
        "conditions": [
            _("Không thỏa mãn các điều kiện của các trạng thái khác"),
            _("Hệ thống vẫn hoạt động bình thường")
        ]
    }
}

# Error messages
DRONE_ERROR_MESSAGES = {
    "VALIDATION_ERROR": {
        "en": _("Invalid drone log data: missing required fields"),
        "ko": _("잘못된 드론 로그 데이터: 필수 필드 누락"),
        "vi": _("Dữ liệu log drone không hợp lệ: thiếu trường bắt buộc")
    },
    "DEVICE_NOT_FOUND": {
        "en": _("Device with specified ID not found"),
        "ko": _("지정된 ID의 장치를 찾을 수 없습니다"),
        "vi": _("Không tìm thấy thiết bị với ID đã chỉ định")
    },
    "OPENSEARCH_ERROR": {
        "en": _("Error connecting to OpenSearch"),
        "ko": _("OpenSearch 연결 오류"),
        "vi": _("Lỗi kết nối đến OpenSearch")
    },
    "STATE_UPDATE_ERROR": {
        "en": _("Error updating drone state"),
        "ko": _("드론 상태 업데이트 오류"),
        "vi": _("Lỗi cập nhật trạng thái drone")
    }
} 