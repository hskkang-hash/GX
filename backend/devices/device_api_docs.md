# Device API Documentation

## Create Device

```
POST /devices-management
```

Tạo mới thiết bị với avatar và các file đính kèm.

### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| data | Form (JSON string) | Dữ liệu thiết bị theo format DeviceCreateSchema |
| avatar | File | Hình ảnh đại diện (không bắt buộc) |
| files | List[File] | Các file đính kèm (không bắt buộc) |

### Schema dữ liệu (DeviceCreateSchema)

Gửi dữ liệu trong trường `data` theo định dạng JSON với cấu trúc sau:

```json
{
  "name": "string",                     // Tên thiết bị (bắt buộc)
  "model": "string",                    // Model của thiết bị (bắt buộc)
  "serial_number": "string",            // Số serial (bắt buộc)
  "status": "operational",              // Trạng thái (mặc định: "operational")
  "active": true,                       // Trạng thái hoạt động (mặc định: true)
  "main_type_id": 1,                    // ID của main_type (không bắt buộc)
  "sub_type": "standard",               // Loại phụ (mặc định: "standard")
  "created_by_id": null,                // ID người tạo (không bắt buộc)
  
  "dimensions": {                       // Kích thước và trọng lượng (không bắt buộc)
    "frame_size": "100 x 50 x 30 mm",   // Kích thước khung
    "maximum_takeoff_weight": "5 kg",   // Trọng lượng cất cánh tối đa
    "payload_capacity": "2 kg",         // Khả năng chở hàng
    "empty_weight": "3 kg"              // Trọng lượng rỗng
  },
  
  "propulsion_system": {                // Hệ thống đẩy (không bắt buộc)
    "number_of_motors": 4,              // Số lượng động cơ
    "motor_type_id": 1,                 // ID loại động cơ
    "battery_type_id": 1,               // ID loại pin
    "flight_time": "30 min",            // Thời gian bay
    "charging_time": "60 min",          // Thời gian sạc
    "motor_power": "2.5 kW",            // Công suất động cơ
    "propeller_size": "10 inch",        // Kích thước cánh quạt
    "battery_capacity": "5000 mAh"      // Dung lượng pin
  },
  
  "flight_performance": {               // Hiệu suất bay (không bắt buộc)
    "maximum_speed": "60 km/h",         // Tốc độ tối đa
    "cruise_speed": "40 km/h",          // Tốc độ hành trình
    "maximum_altitude": "500 m",        // Độ cao tối đa
    "operating_altitude": "100-300 m",  // Độ cao hoạt động
    "maximum_range": "10 km",           // Phạm vi tối đa
    "wind_resistance": "20 km/h"        // Khả năng chống gió
  },
  
  "navigation_control": {               // Điều hướng và kiểm soát (không bắt buộc)
    "barometric_altimeter": true,       // Có đo độ cao khí áp
    "imu_id": 1,                        // ID của IMU
    "gps_accuracy": "2.5 m"             // Độ chính xác GPS
  },
  
  "radio_communication": {              // Liên lạc vô tuyến (không bắt buộc)
    "frequency": "2.4 GHz",             // Tần số
    "range": "5 km"                     // Phạm vi
  },
  
  "telemetry": {                        // Telemetry (không bắt buộc)
    "realtime_tracking": true,          // Theo dõi thời gian thực
    "data_transmission_rate": 10,       // Tốc độ truyền dữ liệu
    "encryption": true                  // Mã hóa
  },
  
  "sensor_suite": {                     // Bộ cảm biến (không bắt buộc)
    "obstacle_detection": true,         // Phát hiện chướng ngại vật
    "collision_avoidance": true,        // Tránh va chạm
    "visual_positioning": true          // Định vị hình ảnh
  },
  
  "manufacturer_information": {         // Thông tin nhà sản xuất (không bắt buộc)
    "manufacturer_name": "DJI",         // Tên nhà sản xuất
    "country_of_origin": "China",       // Quốc gia xuất xứ
    "contact_information": "contact@dji.com" // Thông tin liên hệ
  },
  
  "insurance_information": {            // Thông tin bảo hiểm (không bắt buộc)
    "insurer": "InsureCo",              // Công ty bảo hiểm
    "policy_number": "POL-12345",       // Số hợp đồng
    "coverage_amount": 10000,           // Số tiền bảo hiểm
    "valid_from": "2023-01-01",         // Có hiệu lực từ
    "valid_until": "2024-01-01"         // Có hiệu lực đến
  },
  
  "environmental_specification": {      // Thông số môi trường (không bắt buộc)
    "temperature_range": "-10°C to 40°C", // Phạm vi nhiệt độ
    "humidity": "10-90%",               // Độ ẩm
    "precipitation": "Light rain",       // Lượng mưa
    "wind_speed": "up to 20 km/h",      // Tốc độ gió
    "noise_takeoff": "70 dB",           // Tiếng ồn khi cất cánh
    "noise_cruise": "65 dB",            // Tiếng ồn khi bay
    "noise_landing": "68 dB"            // Tiếng ồn khi hạ cánh
  },
  
  "safety_feature": {                   // Tính năng an toàn (không bắt buộc)
    "geofencing": true,                 // Hàng rào địa lý
    "return_to_home": true,             // Trở về nhà
    "low_battery_warning": true,        // Cảnh báo pin yếu
    "emergency_shutdown": true          // Tắt khẩn cấp
  },
  
  "device_protocol": {                 // Giao thức thiết bị (không bắt buộc)
    "protocol_id": 1,                  // ID giao thức
    "version": "v1.0"                  // Phiên bản
  },
  
  "cargo_compartments": {              // Khoang hàng (không bắt buộc)
    "compartment_number": 1,           // Số khoang
    "name": "Main Cargo",              // Tên khoang
    "secure_locking": true,            // Khóa an toàn
    "quick_release": true,             // Nhả nhanh
    "temperature_control": false,      // Kiểm soát nhiệt độ
    "status": "operational",           // Trạng thái
    "dimensions": "30 x 20 x 15 cm",   // Kích thước
    "weight_capacity": "1.5 kg"        // Khả năng chịu trọng lượng
  },
  
  "cameras": [                         // Danh sách camera (không bắt buộc)
    {
      "name": "Main Camera",           // Tên camera
      "model": "HD-1080p",             // Model camera
      "type": "RGB",                   // Loại camera
      "image_stabilization_id": 1,     // ID của ổn định hình ảnh
      "night_vision": false,           // Tầm nhìn đêm
      "thermal_imaging": false,        // Hình ảnh nhiệt
      "status": "operational",         // Trạng thái
      "resolution": "1920x1080",       // Độ phân giải
      "field_of_view": "120°",         // Góc nhìn
      "frame_rate": "30 fps",          // Tốc độ khung hình
      "weight": "100 g",               // Trọng lượng
      "zoom_capability": "5x"          // Khả năng zoom
    }
  ]
}
```

### Example Request

```
POST /devices-management
Content-Type: multipart/form-data

data: {
  "name": "Drone XYZ",
  "model": "Model-123",
  "serial_number": "SN123456",
  "status": "operational",
  "active": true,
  "main_type_id": 1,
  "sub_type": "standard",
  "dimensions": {
    "frame_size": "100 x 50 x 30 mm"
  }
}
avatar: [file]
files: [file1, file2]
```

### Response

```json
{
  "success": true,
  "status_code": 200,
  "message": "Create device successfully",
  "data": { /* Device data */ }
}
```

## Update Device

```
PUT /devices-management/{id}
```

Cập nhật thiết bị với avatar và file đính kèm.

### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | Path | ID của thiết bị cần cập nhật |
| data | Form (JSON string) | Dữ liệu thiết bị theo format DeviceUpdateSchema |
| avatar | File | Hình ảnh đại diện mới (không bắt buộc) |
| files | List[File] | Các file đính kèm mới (không bắt buộc) |

### Schema dữ liệu (DeviceUpdateSchema)

Gửi dữ liệu trong trường `data` theo định dạng JSON với cấu trúc sau:

```json
{
  "name": "string",                     // Tên thiết bị (không bắt buộc)
  "model": "string",                    // Model của thiết bị (không bắt buộc)
  "status": "maintenance",              // Trạng thái mới (không bắt buộc)
  "active": true,                       // Trạng thái hoạt động (không bắt buộc)
  "main_type_id": 2,                    // ID của main_type (không bắt buộc)
  "sub_type": "special",                // Loại phụ (không bắt buộc)
  "modified_by_id": 1,                  // ID người chỉnh sửa (không bắt buộc)
  
  "dimensions": {                       // Kích thước và trọng lượng (không bắt buộc)
    "frame_size": "100 x 50 x 30 mm",   // Kích thước khung
    "maximum_takeoff_weight": "5 kg",   // Trọng lượng cất cánh tối đa
    "payload_capacity": "2 kg",         // Khả năng chở hàng
    "empty_weight": "3 kg"              // Trọng lượng rỗng
  },
  
  "propulsion_system": {                // Hệ thống đẩy (không bắt buộc)
    "number_of_motors": 4,              // Số lượng động cơ
    "motor_type_id": 1,                 // ID loại động cơ
    "battery_type_id": 1,               // ID loại pin
    "flight_time": "30 min",            // Thời gian bay
    "charging_time": "60 min",          // Thời gian sạc
    "motor_power": "2.5 kW",            // Công suất động cơ
    "propeller_size": "10 inch",        // Kích thước cánh quạt
    "battery_capacity": "5000 mAh"      // Dung lượng pin
  },
  
  "flight_performance": {               // Hiệu suất bay (không bắt buộc)
    "maximum_speed": "60 km/h",         // Tốc độ tối đa
    "cruise_speed": "40 km/h",          // Tốc độ hành trình
    "maximum_altitude": "500 m",        // Độ cao tối đa
    "operating_altitude": "100-300 m",  // Độ cao hoạt động
    "maximum_range": "10 km",           // Phạm vi tối đa
    "wind_resistance": "20 km/h"        // Khả năng chống gió
  },
  
  "navigation_control": {               // Điều hướng và kiểm soát (không bắt buộc)
    "barometric_altimeter": true,       // Có đo độ cao khí áp
    "imu_id": 1,                        // ID của IMU
    "gps_accuracy": "2.5 m"             // Độ chính xác GPS
  },
  
  "radio_communication": {              // Liên lạc vô tuyến (không bắt buộc)
    "frequency": "2.4 GHz",             // Tần số
    "range": "5 km"                     // Phạm vi
  },
  
  "telemetry": {                        // Telemetry (không bắt buộc)
    "realtime_tracking": true,          // Theo dõi thời gian thực
    "data_transmission_rate": 10,       // Tốc độ truyền dữ liệu
    "encryption": true                  // Mã hóa
  },
  
  "sensor_suite": {                     // Bộ cảm biến (không bắt buộc)
    "obstacle_detection": true,         // Phát hiện chướng ngại vật
    "collision_avoidance": true,        // Tránh va chạm
    "visual_positioning": true          // Định vị hình ảnh
  },
  
  "manufacturer_information": {         // Thông tin nhà sản xuất (không bắt buộc)
    "manufacturer_name": "DJI",         // Tên nhà sản xuất
    "country_of_origin": "China",       // Quốc gia xuất xứ
    "contact_information": "contact@dji.com" // Thông tin liên hệ
  },
  
  "insurance_information": {            // Thông tin bảo hiểm (không bắt buộc)
    "insurer": "InsureCo",              // Công ty bảo hiểm
    "policy_number": "POL-12345",       // Số hợp đồng
    "coverage_amount": 10000,           // Số tiền bảo hiểm
    "valid_from": "2023-01-01",         // Có hiệu lực từ
    "valid_until": "2024-01-01"         // Có hiệu lực đến
  },
  
  "environmental_specification": {      // Thông số môi trường (không bắt buộc)
    "temperature_range": "-10°C to 40°C", // Phạm vi nhiệt độ
    "humidity": "10-90%",               // Độ ẩm
    "precipitation": "Light rain",       // Lượng mưa
    "wind_speed": "up to 20 km/h",      // Tốc độ gió
    "noise_takeoff": "70 dB",           // Tiếng ồn khi cất cánh
    "noise_cruise": "65 dB",            // Tiếng ồn khi bay
    "noise_landing": "68 dB"            // Tiếng ồn khi hạ cánh
  },
  
  "safety_feature": {                   // Tính năng an toàn (không bắt buộc)
    "geofencing": true,                 // Hàng rào địa lý
    "return_to_home": true,             // Trở về nhà
    "low_battery_warning": true,        // Cảnh báo pin yếu
    "emergency_shutdown": true          // Tắt khẩn cấp
  },
  
  "device_protocol": {                 // Giao thức thiết bị (không bắt buộc)
    "protocol_id": 1,                  // ID giao thức
    "version": "v1.0"                  // Phiên bản
  },
  
  "cargo_compartments": [              // Danh sách khoang hàng (không bắt buộc)
    {
      "compartment_number": 1,         // Số khoang
      "name": "Main Cargo",            // Tên khoang
      "secure_locking": true,          // Khóa an toàn
      "quick_release": true,           // Nhả nhanh
      "temperature_control": false,    // Kiểm soát nhiệt độ
      "status": "operational",         // Trạng thái
      "dimensions": "30 x 20 x 15 cm", // Kích thước
      "weight_capacity": "1.5 kg"      // Khả năng chịu trọng lượng
    }
  ],
  
  "cameras": [                         // Danh sách camera (không bắt buộc)
    {
      "name": "Main Camera",           // Tên camera
      "model": "HD-1080p",             // Model camera
      "type": "RGB",                   // Loại camera
      "image_stabilization_id": 1,     // ID của ổn định hình ảnh
      "night_vision": false,           // Tầm nhìn đêm
      "thermal_imaging": false,        // Hình ảnh nhiệt
      "status": "operational",         // Trạng thái
      "resolution": "1920x1080",       // Độ phân giải
      "field_of_view": "120°",         // Góc nhìn
      "frame_rate": "30 fps",          // Tốc độ khung hình
      "weight": "100 g",               // Trọng lượng
      "zoom_capability": "5x"          // Khả năng zoom
    }
  ]
}
```

### Additional Info

- `avatar`: Hình đại diện mới (sẽ thay thế hình cũ)
- `files`: File đính kèm mới (sẽ được thêm vào, không xóa file cũ)

### Example Request

```
PUT /devices-management/1
Content-Type: multipart/form-data

data: {
  "name": "Updated Drone",
  "model": "Model-456",
  "status": "maintenance",
  "active": true,
  "main_type_id": 2
}
avatar: [file]
files: [file1]
```

### Response

```json
{
  "success": true,
  "status_code": 200,
  "message": "Update device successfully",
  "data": { /* Updated device data */ }
}
```