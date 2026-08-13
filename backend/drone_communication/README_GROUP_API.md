# Group Management API

API này cung cấp các endpoint để lấy thông tin groups và drones cho GCS (Ground Control Station).

## Endpoints

### 1. Lấy tất cả groups với drones
**GET** `/group-management/groups-with-drones`

Lấy tất cả groups và danh sách drones thuộc mỗi group.

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "groups": [
      {
        "id": 1,
        "name": "Group A",
        "drones": [
          {
            "id": 1,
            "name": "Drone 1",
            "serial_number": "SN001",
            "unit_id": "UNIT001",
            "status": {
              "id": 1,
              "name": "Active",
              "code": "ACTIVE"
            },
            "active": true,
            "main_type": {
              "id": 1,
              "name": "Quadcopter"
            },
            "sub_type": "Standard",
            "terminal": {
              "id": 1,
              "name": "Terminal A"
            },
            "color": "#FF0000",
            "approve_flight_now": true,
            "on_approve_flight": false,
            "created_on": "2024-01-01T00:00:00Z",
            "modified_on": "2024-01-01T00:00:00Z"
          }
        ],
        "drone_count": 1
      }
    ]
  }
}
```

### 2. Lấy drones của một group cụ thể
**GET** `/group-management/group/{group_id}/drones`

Lấy danh sách drones của một group cụ thể.

**Parameters:**
- `group_id` (int): ID của group

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Success",
  "data": {
    "group": {
      "id": 1,
      "name": "Group A"
    },
    "drones": [
      {
        "id": 1,
        "name": "Drone 1",
        "serial_number": "SN001",
        "unit_id": "UNIT001",
        "status": {
          "id": 1,
          "name": "Active",
          "code": "ACTIVE"
        },
        "active": true,
        "main_type": {
          "id": 1,
          "name": "Quadcopter"
        },
        "sub_type": "Standard",
        "terminal": {
          "id": 1,
          "name": "Terminal A"
        },
        "color": "#FF0000",
        "approve_flight_now": true,
        "on_approve_flight": false,
        "created_on": "2024-01-01T00:00:00Z",
        "modified_on": "2024-01-01T00:00:00Z"
      }
    ],
    "drone_count": 1
  }
}
```

## Cách sử dụng

### Lấy tất cả groups với drones
```bash
curl -X GET "http://localhost:8000/api/dronehw/group-management/groups-with-drones"
```

### Lấy drones của group cụ thể
```bash
curl -X GET "http://localhost:8000/api/dronehw/group-management/group/1/drones"
```

## Lưu ý

- API này được thiết kế cho GCS để fetch thông tin groups và drones
- Drones được lấy dựa trên mối quan hệ giữa user tạo device và group của user đó
- Tất cả devices không có creator cũng sẽ được bao gồm
- Response format tuân theo chuẩn BaseResponse của hệ thống
