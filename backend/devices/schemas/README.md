# Hướng dẫn sử dụng Schema

## Tổng quan

Thư mục này chứa các file schema:

- `schemas_in.py`: Schema gốc dùng để nhận dữ liệu đầu vào (legacy)
- `schemas_out.py`: Schema gốc dùng để trả dữ liệu đầu ra (legacy)
- `schemas_djantic_in.py`: Schema đầu vào sử dụng Django Ninja ModelSchema
- `schemas_djantic_out.py`: Schema đầu ra sử dụng Django Ninja ModelSchema

## Cấu trúc tổ chức

Schemas được tổ chức rõ ràng theo vai trò:

1. **Schemas đầu vào (schemas_djantic_in.py)**:

   - Được sử dụng cho dữ liệu nhận từ request
   - Tập trung vào validation và chuyển đổi dữ liệu
   - Có các schema riêng cho Create và Update

2. **Schemas đầu ra (schemas_djantic_out.py)**:
   - Được sử dụng cho dữ liệu trả về response
   - Tập trung vào serialization và định dạng
   - Có schema đầy đủ, rút gọn cho các trường hợp khác nhau

## Xử lý GenericRelation Measurement

Một số model kế thừa từ `MeasurableModel` có các trường `measurements` thông qua `GenericRelation`. Đây không phải là các trường thông thường trong model mà là các bản ghi liên kết thông qua GenericForeignKey. Cách xử lý:

### Trong Schema Đầu Vào:

1. **Sử dụng Schema thay vì ModelSchema** cho các model có trường measurement:

   ```python
   class DimensionsWeightInSchema(Schema):
       # Các trường measurement định dạng string
       frame_size: Optional[str] = None  # Ví dụ: "100 x 50 x 30 mm"
       maximum_takeoff_weight: Optional[str] = None  # Ví dụ: "5 kg"
   ```

2. **Xử lý trong service layer**:

   ```python
   # Trong service
   def create_or_update(device, data):
       dimensions = DimensionsAndWeight(device=device)
       dimensions.save()

       # Xử lý measurements
       if 'frame_size' in data and data['frame_size']:
           dimensions.set_measurement('frame_size', data['frame_size'])
       # Tương tự cho các trường khác
   ```

### Trong Schema Đầu Ra:

1. **Định nghĩa rõ tất cả các trường đầu ra**:

   ```python
   class DimensionsWeightOutSchema(Schema):
       id: int
       # Các trường measurement đã được định dạng
       frame_size: Optional[str] = None
       maximum_takeoff_weight: Optional[str] = None
   ```

2. **Chuẩn bị dữ liệu trong service**:

   ```python
   def get_data(device):
       dimensions = device.dimensions_and_weight
       if not dimensions:
           return None

       return {
           'id': dimensions.id,
           'frame_size': dimensions.get_formatted_value('frame_size'),
           'maximum_takeoff_weight': dimensions.get_formatted_value('maximum_takeoff_weight')
       }
   ```

## Lợi ích của Django Ninja ModelSchema

Django Ninja ModelSchema được tích hợp sẵn trong Django Ninja, mang lại nhiều lợi ích:

1. **Không cần thư viện bổ sung**: Đã có sẵn trong django-ninja
2. **Chuyển đổi tự động**: Chuyển đổi giữa Django model và JSON
3. **Hiệu suất tốt**: Được tối ưu cho Django
4. **Tài liệu đầy đủ**: Dễ dàng tìm kiếm hỗ trợ

## Cách sử dụng

```python
# Import schemas đầu vào và đầu ra
from devices.schemas.schemas_djantic_in import DeviceCreateSchema, DeviceUpdateSchema
from devices.schemas.schemas_djantic_out import DeviceOutSchema, DeviceListOutSchema

# API tạo thiết bị
@router.post("/devices/", response_model=DeviceOutSchema)
def create_device(device_data: DeviceCreateSchema):
    device_dict = device_data.dict()
    # Xử lý logic tạo thiết bị
    device = DeviceService.create(device_dict, request)
    return device  # Tự động chuyển đổi nhờ orm_mode=True

# API lấy danh sách thiết bị
@router.get("/devices/", response_model=List[DeviceListOutSchema])
def list_devices():
    devices = Device.objects.all()
    return devices  # Tự động chuyển đổi nhờ orm_mode=True
```

## Xử lý các ForeignKey

Khi làm việc với Django ForeignKey:

1. **Schema đầu vào**: Sử dụng tên trường với hậu tố `_id`

   ```python
   main_type_id: Optional[int] = None  # Thay vì main_type
   created_by_id: Optional[int] = None  # Thay vì created_by
   ```

2. **Schema đầu ra**: Đối tượng model sẽ tự động chuyển đổi
   ```python
   main_type: str  # Hiển thị là string (tên đối tượng)
   created_by: int  # Hiển thị id của user
   ```

## Cách định nghĩa ModelSchema

```python
# Sử dụng model_fields để chỉ định các trường cần lấy
class MyModelSchema(ModelSchema):
    class Config:
        model = MyModel
        model_fields = ['id', 'name', 'description']  # Chỉ lấy các trường này

# Sử dụng model_exclude để loại bỏ các trường
class MyModelSchema(ModelSchema):
    class Config:
        model = MyModel
        model_exclude = ['created_at', 'updated_at']  # Loại bỏ các trường này

# Lấy tất cả các trường
class MyModelSchema(ModelSchema):
    class Config:
        model = MyModel
        model_fields = "__all__"  # Lấy tất cả trường
```

## Tham khảo

- [Django Ninja Documentation](https://django-ninja.rest-framework.com/)
- [Django Ninja Schema Documentation](https://django-ninja.rest-framework.com/guides/input/schema/)
