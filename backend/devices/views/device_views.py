import logging
import json
from django.forms import Form
from ninja_extra import api_controller, route
from ninja import Schema, Path, Query, Form, File
from typing import List, Optional, Dict, Any
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator
from django.utils.translation import gettext as _
from delivery.models import DeliveryOperationItem
from common.utils import SchemaUtils
from common.tenant_filters import assert_scoped
from devices.models import Device, DimensionsAndWeight, Measurement, DeviceStatus, Library
from devices.schemas.schemas_djantic_in import DeviceCreateSchema, DeviceUpdateSchema, AddToGroupsSchema
from devices.schemas.schemas_djantic_out import DeviceDetailOutSchema, DeviceListOutSchema, DeviceOutSchema, AddToGroupsResponse
from devices.services import devices_service
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import build_dynamic_query_from_queryset
from common.constant import MESSAGE_ENUM, get_message
from ninja.files import UploadedFile
from django.contrib.contenttypes.models import ContentType
from core.file_management.helper import FileHelper
from core.file_management.models import UserMediaFileItem, UserMediaFile
from core.role.permission import path_permission
import time
from core.common.search.dynamic_search import apply_dynamic_filters
from django.db.models import Q, Func, OuterRef, Subquery, Count, Max, F, Case, When, BooleanField, Exists, CharField, Sum, Value
from django.db.models.functions import Concat, Coalesce
from django.db.models.expressions import RawSQL
from django.db import connection, reset_queries
from django.conf import settings
from common.utils import add_records_to_groups

logger = logging.getLogger(__name__)

# Schema examples cho swagger UI
DEVICE_CREATE_EXAMPLE = {
    "name": "Drone XYZ",
    "serial_number": "SN123456",
    "library_id": 1,  # Optional template reference
    "status": "operational",
    "active": True,
    "main_type_id": 1,
    "sub_type": "standard",
    "dimensions": {
        "frame_size": "100 x 50 x 30 mm"
    }
}

DEVICE_UPDATE_EXAMPLE = {
    "name": "Updated Drone",
    "library_id": 2,  # Optional template reference
    "status": "maintenance",
    "active": True,
    "main_type_id": 2
}

@api_controller('/devices-management', tags=['Devices Management'])
class DeviceAPI:
    @route.get('', auth=CustomJWTAuth())
    @path_permission("read", path_override="/device")
    def list_devices(self):


        request = self.context.request
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))



        exclude_fields = []


        devices = Device.objects.all()\
            .prefetch_related('file_attachments',
                             'device_protocols',
                             'device_gnss',
                             'packaging_specification_device',
                             'device_cameras',
                             'cargo_compartments',
                             'delivery_items',
                             'operation_approvals',
                             'order_assignments')\
            .order_by('-id')

        dims_content_type = ContentType.objects.get_for_model(DimensionsAndWeight)

        unit_subquery = Measurement.objects.filter(
            content_type=dims_content_type,
            object_id=OuterRef('dimensions_and_weight__id'),
            measurement_type='payload_capacity'
        ).annotate(
            clean_unit=RawSQL(
                "(data ->> 'unit')",
                []
            )
        ).values('clean_unit')[:1]

        value_subquery = Measurement.objects.filter(
            content_type=dims_content_type,
            object_id=OuterRef('dimensions_and_weight__id'),
            measurement_type='payload_capacity'
        ).values('data__value')[:1]

        devices = devices.annotate(
            model=F('manufacturer_information__model_number'),
            manufacturer=F('manufacturer_information__manufacturer'),
            production_date=F('manufacturer_information__production_date'),
            communication=Value("", output_field=CharField()),
            rtsp=Value(settings.STREAM_URL, output_field=CharField()),
            payload_capacity=Coalesce(
                Concat(
                    Subquery(value_subquery),
                    Value(' '),
                    Subquery(unit_subquery),
                    output_field=CharField()
                ),
                Value('N/A'),
                output_field=CharField()
            ),
            in_use=Exists(
                DeliveryOperationItem.objects.filter(
                    drone_id=OuterRef('pk')
                )
            ),
            main_type__name = F('main_type__name'),
            status__name = F('status__name'),
            terminal__name = F('terminal__name'),
            avatar__file_url=F('avatar__file_url'),
        )

        devices = apply_dynamic_filters(devices, request, exclude_fields, request.GET.get('sort_obj'))
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(devices, page_size)
        pages = paginator.page(current_page)
        data = DeviceListOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(status_code=200,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_DEVICE_SUCCESS),
                            data = data,
                            total_pages=paginator.num_pages,
                            total_items=paginator.count,
                            current_page=current_page,
                            )

    @route.get('/{id}', auth=CustomJWTAuth())
    @path_permission("read", path_override="/device")
    def detail_device(self, id: int, edit: bool=False):
        try:

            device = Device.objects.get(id=id)
            data = devices_service.DeviceService.get_complete_data(device=device,
                                                                   user_units=None,
                                                                   edit=edit)

            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DEVICE_DETAIL_SUCCESS),
                data=data  # Đã sẵn sàng để trả về, không cần chuyển đổi
            )
        except Device.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Device"),
                data=None
            )

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/device")
    def create_device(self,
                     request,
                     data: str = Form(..., description="JSON string của DeviceCreateSchema"),
                     avatar: Optional[UploadedFile] = File(None),
                     files: Optional[List[UploadedFile]] = File(None)):
        """
        Tạo mới thiết bị với avatar và các file đính kèm.

        ## Request Parameters

        | Parameter | Type | Description |
        |-----------|------|-------------|
        | data | Form (JSON string) | Dữ liệu thiết bị theo format DeviceCreateSchema |
        | avatar | File | Hình ảnh đại diện (không bắt buộc) |
        | files | List[File] | Các file đính kèm (không bắt buộc) |

        ## Schema dữ liệu (DeviceCreateSchema)

        Gửi dữ liệu trong trường `data` theo định dạng JSON với cấu trúc sau:

        ```json
        {
          "name": "string",                     // Tên thiết bị (bắt buộc)
          "serial_number": "string",            // Số serial (bắt buộc)
          "library_id": 1,                      // ID của template (không bắt buộc)
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
            "realtime_flight_data": true,          // Theo dõi thời gian thực
            "video_streaming": true,           // Streaming video
            "battery_status_monitoring": true, // Theo dõi trạng thái pin
            "gps_position_tracking": true,     // Theo dõi vị trí GPS
            "system_health_monitoring": true   // Theo dõi trạng thái hệ thống
          },

          "sensor_suite": {                     // Bộ cảm biến (không bắt buộc)
            "optical_flow_sensor": true,         // Phát hiện chướng ngại vật
            "ultrasonic_sensors": true,        // Tránh va chạm
            "lidar": true,          // Định vị hình ảnh
            "ais": true,
            "ads_b_receiver": true,
            "rf_signal_detector": true,
            "chemical_sensor_array": true,
            "radiation_detector": true,
            "weather_sensors": true
          },

          "manufacturer_information": {         // Thông tin nhà sản xuất (không bắt buộc)
            "manufacturer_name": "DJI",         // Tên nhà sản xuất
            "country_of_origin": "China",       // Quốc gia xuất xứ
            "contact_information": "contact@dji.com",
            "insurance_type": "type",
            "insurance_provider": "provider",
            "policy_number": "POL-12345",
            "validity_period": "2023-01-01",
            "current_status": "status"
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
            "dual_imu": true,                 //
            "dual_gps": true,             //
            "dual_battery": true,        //
            "emergency_parachute": true,         //
            "return_to_home": true,         //
            "obstacle_detection_360": true,         //
            "stereo_cameras": true,             // Camera stereo
            "lidar_mapping": true,              // Định vị hình ảnh
            "emergency_braking": true           // Phanh khẩn cấp
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

        ## Response

        ```json
        {
          "success": true,
          "status_code": 200,
          "message": "Create device successfully",
          "data": { /* Device data */ }
        }
        ```
        """

        try:
            # Parse JSON data
            data_dict = json.loads(data)

            # Validate với schema
            try:
                schema = DeviceCreateSchema(**data_dict)
                validated_data = schema.dict(exclude_unset=True)
            except Exception as e:
                return BaseResponse(success=False, status_code=422, message=str(e))

            # # check registration number is unique (check both Device and Library)
            # manufacturer_info = validated_data.get('manufacturer_information')
            # if manufacturer_info and isinstance(manufacturer_info, dict):
            #     registration_number = manufacturer_info.get('registration_number')
            #     if registration_number:
            #         # Check if registration_number exists in Device
            #         device_exists = Device.objects.filter(manufacturer_information__registration_number=registration_number).exists()
            #         # Check if registration_number exists in Library
            #         library_exists = Library.objects.filter(manufacturer_information__registration_number=registration_number).exists()
            #         if device_exists or library_exists:
            #             return BaseResponse(success=False, status_code=400, message=MESSAGE_ENUM.get(MESSAGE_ENUM.LIBRARY_REGISTRATION_NUMBER_ALREADY_EXISTS))

            # Create device with basic data
            device = devices_service.DeviceService.create(validated_data, request)

            # Handle avatar upload if provided
            if avatar:
                try:
                    avatar_file = FileHelper.user_upload_s3(request.user, avatar, is_avatar=True, only_image=True)
                    if avatar_file:
                        device.avatar = avatar_file
                    device.save()
                except Exception as e:
                    return BaseResponse(success=False, status_code=400, message=str(e))

            # Handle files upload if provided
            if files and len(files) > 0:
                try:
                    device_content_type = ContentType.objects.get_for_model(device)
                    for file in files:
                        media_file = FileHelper.user_upload_s3(request.user, file)
                        if media_file:
                            # Create file attachment
                            UserMediaFileItem.objects.create(
                                user_media_file=media_file,
                                content_type=device_content_type,
                                object_id=device.id
                            )
                except Exception as e:
                    return BaseResponse(success=False, status_code=400, message=str(e))

            # Get complete data with files
            response_data = devices_service.DeviceService.get_complete_data(device)

            # Trigger GCS to fetch data
            devices_service.DeviceService.event_trigger_gcs_fetch_data()

            return BaseResponse(status_code=200, message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_DEVICE_SUCCESS), data=response_data)
        except ValidationError as e:
            # In chi tiết lỗi
            print("Validation error:", e)
            print("Error details:", e.errors())
            # Trả về response lỗi
            return {"success": False, "errors": e.errors()}
        except json.JSONDecodeError:
            return BaseResponse(success=False, status_code=400, message=str(_("Invalid JSON data")))

    @route.post("/{id}", auth=CustomJWTAuth())
    @path_permission("update", path_override="/device")
    def update_device(self,
                     id: int,
                     request,
                     data: str = Form(None),
                     avatar: Optional[UploadedFile] = File(None),
                     delete_avatar: bool = Form(False, description="Xóa avatar cũ"),
                     files: Optional[List[UploadedFile]] = File(None),
                     replace_files: bool = Form(False, description="Nếu xóa tất cả file cũ để tải mới thì True"),
                     files_to_remove: str = Form(None, description="Danh sách ID file cần xóa, định dạng array: 1,2,3, sử dụng khi xóa 1 phần của file cũ")):
        """
        {
          "recipient_name": "John Doe",
          "recipient_phone": "0987654321",
          "pickup_location_id": 4,
          "delivery_option_code": "delivery_to_door",
          "delivery_terminal_id": 5,
          "payment_method_code": "cash",
          "recipient_address": {
            "city": "Ho Chi Minh City",
            "district": "District 1",
            "ward": "Ben Nghe",
            "street": "123 Nguyen Hue",
            "full_address": "123 Nguyen Hue, Ben Nghe, District 1, Ho Chi Minh City",
            "lat": 10.773502,
            "lng": 106.704056
          },
          "delivery_address": {
            "city": "Ho Chi Minh City",
            "district": "District 7",
            "ward": "Tan Phong",
            "street": "456 Nguyen Luong Bang",
            "full_address": "456 Nguyen Luong Bang, Tan Phong, District 7, Ho Chi Minh City",
            "lat": 10.729039,
            "lng": 106.722672
          },
          "created_by_guess": {
            "name": "Guest User",
            "phone": "0123456789",
            "address": {
              "city": "Ho Chi Minh City",
              "district": "District 3",
              "ward": "Ward 7",
              "street": "789 Dien Bien Phu",
              "full_address": "789 Dien Bien Phu, Ward 7, District 3, Ho Chi Minh City",
              "lat": 10.782656,
              "lng": 106.683674
            }
          },
          "sender_note": "Please handle with care",
          "recipient_note": "Call before delivery",
          "items": [
            {
              "name": "Electronics Package",
              "weight": 2.5,
              "dimension_l": 300,
              "dimension_w": 200,
              "dimension_h": 150,
              "is_waterproof": true,
              "is_fragile": true,
              "item_type_id": 1,
              "package_id": 37,
              "note": "Contains a laptop"
            },
            {
              "name": "Documents",
              "weight": 0.5,
              "dimension_l": 320,
              "dimension_w": 230,
              "dimension_h": 10,
              "is_waterproof": false,
              "is_fragile": false,
              "item_type_id": 2,
              "package_id": 36,
              "note": "Important documents"
            }
          ]
        }
        """
        # W0-14c — 남의 테넌트 장비면 여기서 404. **try 밖**이다 — 이 핸들러의 except 가
        # 예외를 삼켜 HTTP 200 으로 바꾸기 때문이다 (W0-18 대상).
        assert_scoped(Device, id, request.user)
        try:
            # Parse JSON data
            data_dict = json.loads(data) if data else {}

            # Validate với schema
            try:
                schema = DeviceUpdateSchema(**data_dict)
                validated_data = schema.dict(exclude_unset=True, exclude_none=True)
            except Exception as e:
                return BaseResponse(success=False, status_code=422, message=str(e))
            print(f"validated_data: {validated_data}")

            # # check registration number is unique (check both Device and Library, excluding current device)
            # manufacturer_info = validated_data.get('manufacturer_information')
            # if manufacturer_info and isinstance(manufacturer_info, dict):
            #     registration_number = manufacturer_info.get('registration_number')
            #     if registration_number:
            #         # Check if registration_number exists in Device (excluding current device)
            #         device_exists = Device.objects.filter(manufacturer_information__registration_number=registration_number).exclude(id=id).exists()
            #         # Check if registration_number exists in Library
            #         library_exists = Library.objects.filter(manufacturer_information__registration_number=registration_number).exists()
            #         if device_exists or library_exists:
            #             return BaseResponse(success=False, status_code=400, message=MESSAGE_ENUM.get(MESSAGE_ENUM.DEVICE_REGISTRATION_NUMBER_ALREADY_EXISTS))

            # Update device with basic data
            device = devices_service.DeviceService.update(id, validated_data)

            # Handle avatar upload if provided
            if avatar:
                # Remove old avatar if exists
                if device.avatar:
                    device.avatar.delete()
                    device.save()

                # Upload new avatar
                avatar_file = FileHelper.user_upload_s3(request.user, avatar, is_avatar=True, only_image=True)
                if avatar_file:
                    device.avatar = avatar_file
                    device.save()
            if delete_avatar:
                device.avatar.delete()
                device.avatar = None
                device.save()
            # Xử lý xóa tất cả file đính kèm cũ nếu replace_files=True
            device_content_type = ContentType.objects.get_for_model(device)

            if replace_files:
                # Xóa tất cả file đính kèm cũ
                UserMediaFileItem.objects.filter(
                    content_type=device_content_type,
                    object_id=device.id
                ).delete()
            # Xử lý xóa các file cụ thể nếu có files_to_remove và replace_files=False
            elif files_to_remove:
                try:
                    # Chuyển đổi chuỗi JSON thành list (nếu là chuỗi) hoặc sử dụng trực tiếp (nếu đã là list)
                    file_ids = files_to_remove
                    if isinstance(file_ids, str):
                        file_ids = file_ids.split(',')

                    if isinstance(file_ids, list) and len(file_ids) > 0:
                        # Xóa các file đính kèm cụ thể
                        UserMediaFileItem.objects.filter(
                            content_type=device_content_type,
                            object_id=device.id,
                            user_media_file_id__in=file_ids
                        ).delete()
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    # Log lỗi nhưng không làm gián đoạn quá trình cập nhật
                    print(f"Error processing files_to_remove: {str(e)}")
                    pass

            # Handle files upload if provided
            if files and len(files) > 0:
                for file in files:
                    media_file = FileHelper.user_upload_s3(request.user, file)
                    if media_file:
                        # Create file attachment
                        UserMediaFileItem.objects.create(
                            user_media_file=media_file,
                            content_type=device_content_type,
                            object_id=device.id
                        )

            # Get complete data with files
            response_data = devices_service.DeviceService.get_complete_data(device)

            # Trigger GCS to fetch data
            devices_service.DeviceService.event_trigger_gcs_fetch_data()

            return BaseResponse(status_code=200, message=MESSAGE_ENUM.get(MESSAGE_ENUM.EDIT_DEVICE_SUCCESS), data=response_data)
        except Device.DoesNotExist:
            return BaseResponse(status_code=404, message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Device"), data=None)
        except ValidationError as e:
            print("Validation error:", e)
            print("Error details:", e.errors())
            return {"success": False, "errors": e.errors()}
        except json.JSONDecodeError:
            return BaseResponse(success=False, status_code=400, message=str(_("Invalid JSON data")))

    @route.delete("delete/{ids}", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/device")
    def delete_device(self, request, ids: str):
        # W0-14c — 문지기는 try 밖. request 인자는 그것을 위해 받는다.
        assert_scoped(Device, ids, request.user)
        try:
            devices_service.DeviceService.delete(ids)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None,
            )
        except ValidationError as e:
            return BaseResponse(status_code=400, message=str(e), data=None)
        except Device.DoesNotExist:
            return BaseResponse(status_code=404, message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Device"), data=None)
        except Exception as e:
            print(f"Error deleting device: {str(e)}")
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None,
            )

    @route.delete("/{id}/detach-file/{file_id}", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/device")
    def detach_file(self, id: int, file_id: int):


        try:
            # Check if device exists
            device = Device.objects.get(id=id)

            # Check if file exists and is attached to this device
            device_content_type = ContentType.objects.get_for_model(device)
            attachment = UserMediaFileItem.objects.filter(
                user_media_file_id=file_id,
                content_type=device_content_type,
                object_id=device.id
            ).first()

            if not attachment:
                return BaseResponse(
                    status_code=404,
                    message=str(_("Attachment not found")),
                    data=None
                )

            # Delete the attachment (not the file itself)
            attachment.delete()

            return BaseResponse(
                status_code=200,
                message=str(_("File detached successfully")),
                data=None
            )
        except Device.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Device"),
                data=None
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=str(_("Failed to detach file: ")) + str(e)
            )


    @route.put("/{ids}/change-status", auth=CustomJWTAuth())
    @path_permission("update", path_override="/device")
    def change_status(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
        except ValueError:
            return BaseResponse.with_message(
                success=False,
                status_code=400,
                message="Invalid ID format. Please provide comma-separated integers."
            )
        devices = Device.objects.filter(id__in=id_list)
        available_status = DeviceStatus.objects.get(code='available')
        inactive_status = DeviceStatus.objects.get(code='inactive')
        message_key = None
        for device in devices:
            # check if device is in a mission
            if DeliveryOperationItem.objects.filter(drone=device,
                                                    is_arrived=False,
                                                    is_delivered=False,
                                                    is_delivered_by_drone=False,
                                                    delivery_operation__current_status__code="select_drone_processing",
                                                    arrived_at__isnull=True).exists() and device.active:
                continue
            if device.status:
                if device.status.code == "on_mission" and device.active:
                    return BaseResponse(
                        success=False,
                        status_code=400,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.DEVICE_IN_MISSION)
                    )
            device.active = not device.active
            device.status = available_status if device.active else inactive_status
            device.save()
            if message_key is None:
                message_key = (
                    MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS
                    if device.active
                    else MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS
                )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(message_key or MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
        )

    @route.post("common/add-to-groups", auth=CustomJWTAuth())
    def add_to_groups(self,  data: AddToGroupsSchema):
        success = add_records_to_groups(
            model_name=data.model_name,
            record_ids=data.record_ids,
            group_ids=data.group_ids
        )
        if success:
            return BaseResponse(
                success=True,
                message=get_message(MESSAGE_ENUM.ADD_RECORD_TO_GROUP_SUCCESS),
            )
        else:
            return BaseResponse(
                success=False,
                message=get_message(MESSAGE_ENUM.ADD_RECORD_TO_GROUP_FAILED),
            )

    @route.post("/{id}/active", auth=CustomJWTAuth())
    @path_permission("update", path_override="/device")
    def active_device(self, id: int):
        try:
            device = Device.objects.get(id=id)
            message_key = MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS

            if device.active:
                # check if device is in a mission
                if device.status:
                    if device.status.code == "on_mission":
                        return BaseResponse(
                            success=False,
                            status_code=400,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.DEVICE_IN_MISSION)
                        )
                device.active = False
                message_key = MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS
            else:
                device.active = True
            device.save()
            return BaseResponse(
                success=True,
                status_code=200,
                message=MESSAGE_ENUM.get(message_key)
            )
        except Device.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.DEVICE_NOT_FOUND)
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_DEVICE_FAILED)
            )

    @route.put('/{ids}/activate', auth=CustomJWTAuth())
    # @path_permission("update", path_override='/terminals')
    def activate(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
            available_status = DeviceStatus.objects.get(code='available')
        except ValueError:
            return BaseResponse.with_message(
                success=False,
                status_code=400,
                message="Invalid ID format. Please provide comma-separated integers."
            )
        devices = Device.objects.filter(id__in=id_list)
        for device in devices:
            device.active = True
            device.status = available_status
            device.save()
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
        )

    @route.put('/{ids}/deactivate', auth=CustomJWTAuth())
    # @path_permission("update", path_override='/terminals')
    def deactivate(self, ids: str):
        try:
            id_list = [int(id.strip()) for id in ids.split(",")]
            inactive_status = DeviceStatus.objects.get(code='inactive')
        except ValueError:
            return BaseResponse.with_message(
                success=False,
                status_code=400,
                message="Invalid ID format. Please provide comma-separated integers."
            )
        devices = Device.objects.filter(id__in=id_list)
        for device in devices:
            if DeliveryOperationItem.objects.filter(drone=device,
                                                    is_arrived=False,
                                                    is_delivered=False,
                                                    is_delivered_by_drone=False,
                                                    delivery_operation__current_status__code="select_drone_processing",
                                                    arrived_at__isnull=True).exists():
                continue
            # check if device is in a mission
            if device.status:
                if device.status.code == "on_mission":
                    return BaseResponse(
                        success=False,
                        status_code=400,
                        message=MESSAGE_ENUM.get(MESSAGE_ENUM.DEVICE_IN_MISSION)
                    )
            device.active = False
            device.status = inactive_status
            device.save()
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS),
        )
